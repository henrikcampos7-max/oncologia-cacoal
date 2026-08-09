from __future__ import annotations

import json
import logging
import re
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET


NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL_DOC = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_REL_PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"m": NS_MAIN, "r": NS_REL_DOC, "p": NS_REL_PKG}

HEADER_TERMS = {
    "paciente", "beneficiario", "beneficiário", "medicamento", "produto",
    "data", "dose", "quantidade", "qtde", "estoque", "status", "situacao",
    "situação", "apresentacao", "apresentação", "lote", "validade", "ciclo",
    "protocolo", "unidade", "nome", "codigo", "código", "compra", "saldo",
    "transferencia", "transferência", "pedido", "valor", "fabricante",
}


LOGGER = logging.getLogger("inspect_xlsx_structure")


class ValidationError(ValueError):
    pass


def qname(ns: str, name: str) -> str:
    return f"{{{ns}}}{name}"


def normalize_target(base: str, target: str) -> str:
    target_path = PurePosixPath(target.replace("\\", "/"))
    if target_path.is_absolute():
        return str(target_path).lstrip("/")
    base_dir = PurePosixPath(base).parent
    combined = base_dir / target_path
    parts: list[str] = []
    for part in combined.parts:
        if part == "..":
            if parts:
                parts.pop()
        elif part not in (".", ""):
            parts.append(part)
    return "/".join(parts)


def read_relationships(zf: zipfile.ZipFile, rel_path: str, owner_path: str) -> dict[str, dict[str, str]]:
    if rel_path not in zf.namelist():
        return {}
    root = ET.fromstring(zf.read(rel_path))
    result: dict[str, dict[str, str]] = {}
    for rel in root.findall("p:Relationship", NS):
        rid = rel.attrib.get("Id", "")
        result[rid] = {
            "type": rel.attrib.get("Type", ""),
            "target": normalize_target(owner_path, rel.attrib.get("Target", "")),
            "target_mode": rel.attrib.get("TargetMode", ""),
        }
    return result


def shared_strings(zf: zipfile.ZipFile) -> list[str]:
    path = "xl/sharedStrings.xml"
    if path not in zf.namelist():
        return []
    values: list[str] = []
    for event, elem in ET.iterparse(zf.open(path), events=("end",)):
        if elem.tag == qname(NS_MAIN, "si"):
            text = "".join(t.text or "" for t in elem.iter(qname(NS_MAIN, "t")))
            values.append(text)
            elem.clear()
    return values


def decode_cell(cell: ET.Element, strings: list[str]) -> tuple[str | None, str | None, str | None]:
    cell_type = cell.attrib.get("t")
    formula_el = cell.find("m:f", NS)
    value_el = cell.find("m:v", NS)
    inline_el = cell.find("m:is", NS)
    formula = formula_el.text if formula_el is not None else None
    raw = value_el.text if value_el is not None else None
    display: str | None = None
    if cell_type == "s" and raw is not None:
        try:
            display = strings[int(raw)]
        except (ValueError, IndexError):
            display = None
    elif cell_type == "inlineStr" and inline_el is not None:
        display = "".join(t.text or "" for t in inline_el.iter(qname(NS_MAIN, "t")))
    elif cell_type == "str":
        display = raw
    elif cell_type == "b":
        display = "TRUE" if raw == "1" else "FALSE"
    elif cell_type == "e":
        display = raw
    return formula, raw, display


def formula_features(formula: str) -> tuple[list[str], list[str]]:
    functions = re.findall(r"\b([A-Za-z][A-Za-z0-9_.]*)\s*\(", formula)
    refs: list[str] = []
    for quoted, plain in re.findall(r"(?:'([^']+)'|([A-Za-z0-9_ .À-ÿ-]+))!", formula):
        refs.append((quoted or plain).strip())
    return functions, refs


def likely_headers(rows: dict[int, list[tuple[str, str]]]) -> tuple[int | None, list[str]]:
    candidates: list[tuple[int, int, list[str]]] = []
    for row_num, cells in rows.items():
        values = [value.strip() for _, value in cells if value and value.strip()]
        if len(values) < 2:
            continue
        normalized = " ".join(values).lower()
        matches = sum(1 for term in HEADER_TERMS if term in normalized)
        if matches >= 2:
            candidates.append((matches, len(values), values[:40]))
    if not candidates:
        return None, []
    best_score, best_len, best_values = max(candidates, key=lambda item: (item[0], item[1]))
    for row_num, cells in rows.items():
        values = [value.strip() for _, value in cells if value and value.strip()]
        if values[:40] == best_values:
            return row_num, best_values
    return None, []


def inspect_sheet(zf: zipfile.ZipFile, sheet_path: str, strings: list[str]) -> dict:
    counts = Counter()
    function_counts = Counter()
    dependency_counts = Counter()
    first_rows: dict[int, list[tuple[str, str]]] = defaultdict(list)
    formula_samples: list[dict[str, str]] = []
    error_samples: list[dict[str, str]] = []
    fragile_samples: list[dict[str, str]] = []
    dimension = None
    max_row_seen = 0
    max_col_seen = 0
    merge_count = 0
    validation_count = 0
    conditional_format_count = 0
    hyperlink_count = 0

    with zf.open(sheet_path) as stream:
        for event, elem in ET.iterparse(stream, events=("end",)):
            tag = elem.tag
            if tag == qname(NS_MAIN, "dimension"):
                dimension = elem.attrib.get("ref")
            elif tag == qname(NS_MAIN, "mergeCell"):
                merge_count += 1
            elif tag == qname(NS_MAIN, "dataValidation"):
                validation_count += 1
            elif tag == qname(NS_MAIN, "conditionalFormatting"):
                conditional_format_count += 1
            elif tag == qname(NS_MAIN, "hyperlink"):
                hyperlink_count += 1
            elif tag == qname(NS_MAIN, "c"):
                ref = elem.attrib.get("r", "")
                match = re.match(r"([A-Z]+)(\d+)", ref)
                if match:
                    col_letters, row_text = match.groups()
                    row_num = int(row_text)
                    col_num = 0
                    for ch in col_letters:
                        col_num = col_num * 26 + (ord(ch) - 64)
                    max_row_seen = max(max_row_seen, row_num)
                    max_col_seen = max(max_col_seen, col_num)
                else:
                    row_num = 0

                counts["cells"] += 1
                formula, raw, display = decode_cell(elem, strings)
                cell_type = elem.attrib.get("t")
                if formula:
                    counts["formula_cells"] += 1
                    functions, refs = formula_features(formula)
                    function_counts.update(fn.upper() for fn in functions)
                    dependency_counts.update(refs)
                    if len(formula_samples) < 20:
                        formula_samples.append({"cell": ref, "formula": formula[:300]})
                    upper = formula.upper()
                    if "#REF!" in upper or "[" in formula or any(v in upper for v in ("INDIRECT(", "OFFSET(", "TODAY(", "NOW(")):
                        counts["fragile_formula_cells"] += 1
                        if len(fragile_samples) < 20:
                            fragile_samples.append({"cell": ref, "formula": formula[:300]})
                elif raw is not None or display is not None:
                    counts["manual_value_cells"] += 1
                if cell_type == "e":
                    counts["error_cells"] += 1
                    if len(error_samples) < 20:
                        error_samples.append({
                            "cell": ref,
                            "error": display or raw or "unknown",
                            "formula": (formula or "")[:500],
                        })
                if row_num and row_num <= 20 and display is not None and len(display) <= 120:
                    first_rows[row_num].append((ref, display))
                elem.clear()

    header_row, headers = likely_headers(first_rows)
    return {
        "path": sheet_path,
        "dimension": dimension,
        "observed_max_row": max_row_seen,
        "observed_max_col": max_col_seen,
        "cell_counts": dict(counts),
        "header_row_candidate": header_row,
        "header_fields": headers,
        "top_functions": function_counts.most_common(25),
        "sheet_dependencies": dependency_counts.most_common(),
        "formula_samples": formula_samples,
        "fragile_formula_samples": fragile_samples,
        "error_samples": error_samples,
        "merge_count": merge_count,
        "data_validation_count": validation_count,
        "conditional_format_count": conditional_format_count,
        "hyperlink_count": hyperlink_count,
    }


def error_response(code: str, message: str, details: dict | None = None) -> dict:
    response = {"error": {"code": code, "message": message}}
    if details:
        response["error"]["details"] = details
    return response


def validate_inputs(argv: list[str]) -> tuple[Path, Path]:
    if len(argv) != 3:
        raise ValidationError("usage: inspect_xlsx_structure.py <input.xlsx> <output.json>")

    input_path = Path(argv[1]).resolve()
    output_path = Path(argv[2]).resolve()
    if not input_path.exists():
        raise ValidationError("input file not found")
    if input_path.suffix.lower() != ".xlsx":
        raise ValidationError("input file must be .xlsx")
    if output_path.suffix.lower() != ".json":
        raise ValidationError("output file must be .json")
    output_dir = output_path.parent
    if not output_dir.exists():
        raise ValidationError("output directory not found")
    if output_dir.is_file():
        raise ValidationError("output directory path is a file")

    return input_path, output_path


def run(argv: list[str]) -> int:
    input_path, output_path = validate_inputs(argv)
    stat = input_path.stat()

    with zipfile.ZipFile(input_path) as zf:
        names = set(zf.namelist())
        workbook_path = "xl/workbook.xml"
        workbook_root = ET.fromstring(zf.read(workbook_path))
        workbook_rels = read_relationships(zf, "xl/_rels/workbook.xml.rels", workbook_path)
        strings = shared_strings(zf)

        sheet_records: list[dict] = []
        for sheet in workbook_root.findall("m:sheets/m:sheet", NS):
            rid = sheet.attrib.get(qname(NS_REL_DOC, "id"), "")
            rel = workbook_rels.get(rid, {})
            sheet_path = rel.get("target")
            record = {
                "name": sheet.attrib.get("name"),
                "state": sheet.attrib.get("state", "visible"),
                "sheet_id": sheet.attrib.get("sheetId"),
                "relationship_id": rid,
                "path": sheet_path,
            }
            if sheet_path and sheet_path in names:
                record.update(inspect_sheet(zf, sheet_path, strings))
            else:
                record["inspection_error"] = "worksheet XML not found"
            sheet_records.append(record)

        defined_names = []
        for item in workbook_root.findall("m:definedNames/m:definedName", NS):
            defined_names.append({
                "name": item.attrib.get("name"),
                "localSheetId": item.attrib.get("localSheetId"),
                "hidden": item.attrib.get("hidden"),
                "formula": (item.text or "")[:500],
            })

        tables = []
        for table_path in sorted(name for name in names if name.startswith("xl/tables/") and name.endswith(".xml")):
            root = ET.fromstring(zf.read(table_path))
            columns = [c.attrib.get("name", "") for c in root.findall("m:tableColumns/m:tableColumn", NS)]
            tables.append({
                "path": table_path,
                "name": root.attrib.get("name"),
                "display_name": root.attrib.get("displayName"),
                "ref": root.attrib.get("ref"),
                "columns": columns[:100],
                "column_count": len(columns),
            })

        report = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "file": {
                "path": str(input_path),
                "name": input_path.name,
                "format": input_path.suffix.lower(),
                "size_bytes": stat.st_size,
                "created_local": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_local": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            },
            "package": {
                "zip_entries": len(names),
                "shared_string_count": len(strings),
                "has_calc_chain": "xl/calcChain.xml" in names,
                "external_link_files": len([n for n in names if n.startswith("xl/externalLinks/") and n.endswith(".xml")]),
                "has_connections": "xl/connections.xml" in names,
                "has_vba": "xl/vbaProject.bin" in names,
            },
            "sheet_count": len(sheet_records),
            "sheets": sheet_records,
            "defined_names": defined_names,
            "tables": tables,
        }

    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    compact = {
        "file": report["file"],
        "package": report["package"],
        "sheet_count": report["sheet_count"],
        "sheets": [
            {
                "name": s.get("name"),
                "state": s.get("state"),
                "dimension": s.get("dimension"),
                "header_row_candidate": s.get("header_row_candidate"),
                "header_fields": s.get("header_fields"),
                "cell_counts": s.get("cell_counts"),
                "top_functions": s.get("top_functions"),
                "sheet_dependencies": s.get("sheet_dependencies"),
                "data_validation_count": s.get("data_validation_count"),
                "conditional_format_count": s.get("conditional_format_count"),
            }
            for s in sheet_records
        ],
        "defined_names_count": len(defined_names),
        "table_count": len(tables),
        "tables": tables,
    }
    print(json.dumps(compact, ensure_ascii=False, indent=2))
    return 0


def main() -> None:
    logging.basicConfig(level=logging.ERROR, format="%(levelname)s %(name)s %(message)s")
    try:
        raise SystemExit(run(sys.argv))
    except ValidationError as exc:
        print(
            json.dumps(
                error_response("VALIDATION_ERROR", str(exc), {"arguments": sys.argv[1:]}),
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        raise SystemExit(2)
    except Exception as exc:  # pragma: no cover - defensive top-level handler
        LOGGER.exception(
            "internal failure while inspecting workbook",
            extra={"input_argument": sys.argv[1] if len(sys.argv) > 1 else None},
        )
        print(
            json.dumps(
                error_response("INTERNAL_ERROR", "unexpected error while processing workbook"),
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
