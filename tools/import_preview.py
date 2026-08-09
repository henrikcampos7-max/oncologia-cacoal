from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Iterable, Mapping, Sequence
from unicodedata import normalize
from uuid import uuid4


IMPORT_PREVIEW_SCHEMA_VERSION = "import-preview.v1"

FORECAST_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "plan": ("plano", "convenio", "convênio"),
    "patient": ("paciente", "beneficiario", "beneficiário"),
    "medication": ("medicamento", "produto"),
    "treatment_start": ("inicio do tratamento", "início do tratamento", "data inicio", "data início"),
    "cycle_interval_days": ("intervalo do ciclo em dias", "intervalo ciclo dias", "intervalo"),
    "dose_per_cycle": ("dose por ciclo", "dose"),
    "unit": ("unidade",),
    "cycles_planned": ("quantidade de ciclos previstos", "ciclos previstos", "quantidade ciclos"),
    "applications_per_cycle": ("aplicacoes por ciclo", "aplicações por ciclo"),
    "status": ("status", "situacao", "situação"),
}

STOCK_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "medication": ("medicamento", "produto"),
    "current_stock": ("estoque atual", "saldo atual", "estoque"),
    "unit": ("unidade",),
    "notes": ("observacoes", "observações", "justificativa", "observacao", "observação"),
}

FORECAST_REQUIRED_FIELDS = (
    "patient",
    "medication",
    "treatment_start",
    "cycle_interval_days",
    "dose_per_cycle",
    "unit",
    "cycles_planned",
    "applications_per_cycle",
    "status",
)
STOCK_REQUIRED_FIELDS = ("medication", "current_stock", "unit")

ACTIVE_STATUSES = {"ativo", "active"}
REVIEW_STATUSES = {"suspenso", "suspended", "inativo", "inactive"}
REJECTED_STATUSES = {"cancelado", "cancelled"}
STOCK_IMPORT_MODES = {"snapshot", "movement"}


class ImportValidationError(ValueError):
    pass


@dataclass(frozen=True)
class MappingModelMeta:
    schema_version: str
    model_id: str
    model_name: str
    source_kind: str
    created_at: str


@dataclass(frozen=True)
class ImportMappingModel:
    meta: MappingModelMeta
    field_mapping: dict[str, str]


def _normalize_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    ascii_text = normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_text.lower().split())


def _require_text(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ImportValidationError(f"{field_name} is required")
    return text


def _require_number(value: Any, field_name: str, *, min_value: float = 0.0) -> float:
    if isinstance(value, bool):
        raise ImportValidationError(f"{field_name} must be a number")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ImportValidationError(f"{field_name} must be a number") from exc
    if parsed < min_value:
        raise ImportValidationError(f"{field_name} must be >= {min_value}")
    return parsed


def _parse_date(value: Any, field_name: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
    raise ImportValidationError(f"{field_name} must be a date in YYYY-MM-DD or DD/MM/YYYY format")


def _normalize_mapping(mapping: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(mapping, Mapping):
        raise ImportValidationError("mapping must be an object")
    normalized: dict[str, str] = {}
    for field_name, source_column in mapping.items():
        canonical_field = _require_text(field_name, "mapping.field")
        normalized[canonical_field] = _require_text(source_column, f"mapping[{canonical_field}]")
    return normalized


def suggest_column_mapping(
    headers: Sequence[str],
    *,
    aliases: Mapping[str, Sequence[str]] = FORECAST_FIELD_ALIASES,
) -> dict[str, str]:
    resolved: dict[str, str] = {}
    normalized_headers = {_normalize_text(header): header for header in headers if str(header).strip()}

    for canonical_field, field_aliases in aliases.items():
        for alias in field_aliases:
            matched_header = normalized_headers.get(_normalize_text(alias))
            if matched_header:
                resolved[canonical_field] = matched_header
                break
        if canonical_field in resolved:
            continue
        for normalized_header, original_header in normalized_headers.items():
            if any(_normalize_text(alias) in normalized_header for alias in field_aliases):
                resolved[canonical_field] = original_header
                break
    return resolved


def build_mapping_model(
    *,
    model_name: str,
    source_kind: str,
    field_mapping: Mapping[str, str],
) -> ImportMappingModel:
    name = _require_text(model_name, "model_name")
    kind = _require_text(source_kind, "source_kind")
    mapping = _normalize_mapping(field_mapping)
    return ImportMappingModel(
        meta=MappingModelMeta(
            schema_version=IMPORT_PREVIEW_SCHEMA_VERSION,
            model_id=str(uuid4()),
            model_name=name,
            source_kind=kind,
            created_at=datetime.now(timezone.utc).isoformat(),
        ),
        field_mapping=mapping,
    )


def mapping_model_to_dict(model: ImportMappingModel) -> dict[str, Any]:
    return {
        "meta": {
            "schema_version": model.meta.schema_version,
            "model_id": model.meta.model_id,
            "model_name": model.meta.model_name,
            "source_kind": model.meta.source_kind,
            "created_at": model.meta.created_at,
        },
        "field_mapping": dict(sorted(model.field_mapping.items())),
    }


def mapping_model_from_dict(payload: Mapping[str, Any]) -> ImportMappingModel:
    if not isinstance(payload, Mapping):
        raise ImportValidationError("model must be an object")
    meta = payload.get("meta")
    if not isinstance(meta, Mapping):
        raise ImportValidationError("meta must be an object")
    schema_version = _require_text(meta.get("schema_version"), "meta.schema_version")
    if schema_version != IMPORT_PREVIEW_SCHEMA_VERSION:
        raise ImportValidationError("meta.schema_version is not supported")
    field_mapping = _normalize_mapping(payload.get("field_mapping", {}))
    return ImportMappingModel(
        meta=MappingModelMeta(
            schema_version=schema_version,
            model_id=_require_text(meta.get("model_id"), "meta.model_id"),
            model_name=_require_text(meta.get("model_name"), "meta.model_name"),
            source_kind=_require_text(meta.get("source_kind"), "meta.source_kind"),
            created_at=_require_text(meta.get("created_at"), "meta.created_at"),
        ),
        field_mapping=field_mapping,
    )


def _classification_payload(
    *,
    row_number: int,
    classification: str,
    normalized_row: dict[str, Any],
    messages: Iterable[str],
) -> dict[str, Any]:
    return {
        "row_number": row_number,
        "classification": classification,
        "normalized_row": normalized_row,
        "messages": list(messages),
    }


def preview_forecast_import(
    rows: Sequence[Mapping[str, Any]],
    *,
    field_mapping: Mapping[str, str],
    reference_date: date | datetime | str,
    known_medications: Iterable[str] = (),
    known_patients: Iterable[str] = (),
) -> dict[str, Any]:
    mapping = _normalize_mapping(field_mapping)
    missing_required_fields = [field for field in FORECAST_REQUIRED_FIELDS if field not in mapping]
    if missing_required_fields:
        missing = ", ".join(sorted(missing_required_fields))
        raise ImportValidationError(f"field_mapping is missing required fields: {missing}")

    baseline_date = _parse_date(reference_date, "reference_date")
    medication_registry = {_normalize_text(item) for item in known_medications if _normalize_text(item)}
    patient_registry = {_normalize_text(item) for item in known_patients if _normalize_text(item)}

    classified_rows: list[dict[str, Any]] = []
    counts = {
        "valid": 0,
        "requires_review": 0,
        "error": 0,
        "duplicate": 0,
        "rejected": 0,
    }
    seen_keys: set[tuple[str, ...]] = set()

    for row_index, source_row in enumerate(rows, start=1):
        normalized_row = {
            field_name: source_row.get(source_column)
            for field_name, source_column in mapping.items()
        }
        errors: list[str] = []
        review_reasons: list[str] = []

        try:
            patient = _require_text(normalized_row.get("patient"), "patient")
            medication = _require_text(normalized_row.get("medication"), "medication")
            treatment_start = _parse_date(normalized_row.get("treatment_start"), "treatment_start")
            cycle_interval_days = _require_number(
                normalized_row.get("cycle_interval_days"),
                "cycle_interval_days",
                min_value=1.0,
            )
            dose_per_cycle = _require_number(
                normalized_row.get("dose_per_cycle"),
                "dose_per_cycle",
                min_value=0.0,
            )
            unit = _require_text(normalized_row.get("unit"), "unit")
            cycles_planned = _require_number(
                normalized_row.get("cycles_planned"),
                "cycles_planned",
                min_value=1.0,
            )
            applications_per_cycle = _require_number(
                normalized_row.get("applications_per_cycle"),
                "applications_per_cycle",
                min_value=1.0,
            )
            status = _require_text(normalized_row.get("status"), "status")
        except ImportValidationError as exc:
            errors.append(str(exc))
            classified_rows.append(
                _classification_payload(
                    row_number=row_index,
                    classification="error",
                    normalized_row=normalized_row,
                    messages=errors,
                )
            )
            counts["error"] += 1
            continue

        normalized_status = _normalize_text(status)
        normalized_patient = _normalize_text(patient)
        normalized_medication = _normalize_text(medication)
        duplicate_key = (
            normalized_patient,
            normalized_medication,
            treatment_start.isoformat(),
            str(int(cycle_interval_days)),
            str(dose_per_cycle),
        )
        normalized_row = {
            **normalized_row,
            "patient": patient,
            "medication": medication,
            "treatment_start": treatment_start.isoformat(),
            "cycle_interval_days": cycle_interval_days,
            "dose_per_cycle": dose_per_cycle,
            "unit": unit,
            "cycles_planned": cycles_planned,
            "applications_per_cycle": applications_per_cycle,
            "status": status,
        }

        if duplicate_key in seen_keys:
            classified_rows.append(
                _classification_payload(
                    row_number=row_index,
                    classification="duplicate",
                    normalized_row=normalized_row,
                    messages=["registro duplicado na prévia de importação"],
                )
            )
            counts["duplicate"] += 1
            continue
        seen_keys.add(duplicate_key)

        if normalized_status in REJECTED_STATUSES:
            classified_rows.append(
                _classification_payload(
                    row_number=row_index,
                    classification="rejected",
                    normalized_row=normalized_row,
                    messages=["registro cancelado ou equivalente"],
                )
            )
            counts["rejected"] += 1
            continue

        if treatment_start < baseline_date:
            review_reasons.append("data de início anterior à data de referência")
        if normalized_status in REVIEW_STATUSES:
            review_reasons.append("status exige revisão humana")
        if medication_registry and normalized_medication not in medication_registry:
            review_reasons.append("medicamento não localizado na base conhecida")
        if patient_registry and normalized_patient not in patient_registry:
            review_reasons.append("paciente não localizado na base conhecida")

        classification = "requires_review" if review_reasons else "valid"
        classified_rows.append(
            _classification_payload(
                row_number=row_index,
                classification=classification,
                normalized_row=normalized_row,
                messages=review_reasons or ["registro pronto para importação"],
            )
        )
        counts[classification] += 1

    return {
        "meta": {
            "schema_version": IMPORT_PREVIEW_SCHEMA_VERSION,
            "source_kind": "forecast_applications",
            "reference_date": baseline_date.isoformat(),
            "field_mapping": dict(sorted(mapping.items())),
        },
        "summary": {
            "total_rows": len(rows),
            **counts,
        },
        "rows": classified_rows,
    }


def preview_stock_import(
    rows: Sequence[Mapping[str, Any]],
    *,
    field_mapping: Mapping[str, str],
    reference_date: date | datetime | str,
    import_mode: str,
    calculated_stock_by_medication: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    mapping = _normalize_mapping(field_mapping)
    missing_required_fields = [field for field in STOCK_REQUIRED_FIELDS if field not in mapping]
    if missing_required_fields:
        missing = ", ".join(sorted(missing_required_fields))
        raise ImportValidationError(f"field_mapping is missing required fields: {missing}")

    normalized_import_mode = _normalize_text(import_mode)
    if normalized_import_mode not in STOCK_IMPORT_MODES:
        raise ImportValidationError("import_mode must be snapshot or movement")

    baseline_date = _parse_date(reference_date, "reference_date")
    calculated_stock = {
        _normalize_text(medication): _require_number(amount, f"calculated_stock_by_medication[{medication}]", min_value=0.0)
        for medication, amount in (calculated_stock_by_medication or {}).items()
    }
    classified_rows: list[dict[str, Any]] = []
    counts = {
        "valid": 0,
        "requires_review": 0,
        "error": 0,
        "duplicate": 0,
        "rejected": 0,
    }
    seen_medications: set[str] = set()

    for row_index, source_row in enumerate(rows, start=1):
        normalized_row = {
            field_name: source_row.get(source_column)
            for field_name, source_column in mapping.items()
        }
        try:
            medication = _require_text(normalized_row.get("medication"), "medication")
            current_stock = _require_number(normalized_row.get("current_stock"), "current_stock", min_value=0.0)
            unit = _require_text(normalized_row.get("unit"), "unit")
            notes = str(normalized_row.get("notes") or "").strip()
        except ImportValidationError as exc:
            classified_rows.append(
                _classification_payload(
                    row_number=row_index,
                    classification="error",
                    normalized_row=normalized_row,
                    messages=[str(exc)],
                )
            )
            counts["error"] += 1
            continue

        normalized_medication = _normalize_text(medication)
        normalized_row = {
            **normalized_row,
            "medication": medication,
            "current_stock": current_stock,
            "unit": unit,
            "notes": notes,
        }
        if normalized_medication in seen_medications:
            classified_rows.append(
                _classification_payload(
                    row_number=row_index,
                    classification="duplicate",
                    normalized_row=normalized_row,
                    messages=["medicamento repetido no mesmo arquivo de estoque"],
                )
            )
            counts["duplicate"] += 1
            continue
        seen_medications.add(normalized_medication)

        review_reasons: list[str] = []
        calculated_amount = calculated_stock.get(normalized_medication)
        if calculated_amount is not None:
            delta = round(current_stock - calculated_amount, 9)
            normalized_row["calculated_stock"] = calculated_amount
            normalized_row["discrepancy"] = delta
            if delta != 0 and not notes:
                review_reasons.append("conciliação exige justificativa para ajustar o saldo")
        if normalized_import_mode == "movement" and not notes:
            review_reasons.append("movimentação sem observação ou justificativa")

        classification = "requires_review" if review_reasons else "valid"
        classified_rows.append(
            _classification_payload(
                row_number=row_index,
                classification=classification,
                normalized_row=normalized_row,
                messages=review_reasons or ["registro pronto para importação"],
            )
        )
        counts[classification] += 1

    return {
        "meta": {
            "schema_version": IMPORT_PREVIEW_SCHEMA_VERSION,
            "source_kind": "stock_position" if normalized_import_mode == "snapshot" else "stock_movement",
            "reference_date": baseline_date.isoformat(),
            "import_mode": normalized_import_mode,
            "field_mapping": dict(sorted(mapping.items())),
        },
        "summary": {
            "total_rows": len(rows),
            **counts,
        },
        "rows": classified_rows,
    }
