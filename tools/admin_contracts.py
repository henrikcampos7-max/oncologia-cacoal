from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from uuid import uuid4


ADMIN_SNAPSHOT_SCHEMA_VERSION = "admin-snapshot.v1"


class AdminContractValidationError(ValueError):
    pass


@dataclass(frozen=True)
class SnapshotMeta:
    schema_version: str
    snapshot_id: str
    clinic_id: str
    generated_at: str
    review_required: bool


@dataclass(frozen=True)
class PatientRecord:
    patient_id: str
    clinic_id: str
    display_name: str


@dataclass(frozen=True)
class MedicationRecord:
    medication_id: str
    clinic_id: str
    name: str
    clinical_unit: str
    stock_unit: str


@dataclass(frozen=True)
class TreatmentRecord:
    treatment_id: str
    clinic_id: str
    patient_id: str
    medication_id: str
    start_date: str
    status: str


@dataclass(frozen=True)
class PlannedApplicationRecord:
    application_id: str
    clinic_id: str
    treatment_id: str
    planned_date: str
    dose: float
    unit: str
    status: str
    source: str


@dataclass(frozen=True)
class StockPositionRecord:
    position_id: str
    clinic_id: str
    medication_id: str
    reference_date: str
    quantity: float
    unit: str


@dataclass(frozen=True)
class ImportSessionRecord:
    import_id: str
    clinic_id: str
    source_kind: str
    reference_date: str
    status: str


@dataclass(frozen=True)
class AdministrativeSnapshot:
    meta: SnapshotMeta
    patients: tuple[PatientRecord, ...]
    medications: tuple[MedicationRecord, ...]
    treatments: tuple[TreatmentRecord, ...]
    planned_applications: tuple[PlannedApplicationRecord, ...]
    stock_positions: tuple[StockPositionRecord, ...]
    imports: tuple[ImportSessionRecord, ...]


def _require_text(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise AdminContractValidationError(f"{field_name} is required")
    return text


def _require_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise AdminContractValidationError(f"{field_name} must be a boolean")
    return value


def _require_number(value: Any, field_name: str, *, min_value: float = 0.0) -> float:
    if isinstance(value, bool):
        raise AdminContractValidationError(f"{field_name} must be a number")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise AdminContractValidationError(f"{field_name} must be a number") from exc
    if parsed < min_value:
        raise AdminContractValidationError(f"{field_name} must be >= {min_value}")
    return parsed


def _require_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AdminContractValidationError(f"{field_name} must be an object")
    return value


def _require_sequence(value: Any, field_name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise AdminContractValidationError(f"{field_name} must be a list")
    return value


def _validate_clinic_id(record_clinic_id: str, expected_clinic_id: str, field_name: str) -> str:
    clinic_id = _require_text(record_clinic_id, field_name)
    if clinic_id != expected_clinic_id:
        raise AdminContractValidationError(f"{field_name} must match snapshot clinic_id")
    return clinic_id


def _validate_snapshot(snapshot: AdministrativeSnapshot) -> None:
    clinic_id = _require_text(snapshot.meta.clinic_id, "meta.clinic_id")
    for index, row in enumerate(snapshot.patients):
        _validate_clinic_id(row.clinic_id, clinic_id, f"patients[{index}].clinic_id")
    for index, row in enumerate(snapshot.medications):
        _validate_clinic_id(row.clinic_id, clinic_id, f"medications[{index}].clinic_id")
    for index, row in enumerate(snapshot.treatments):
        _validate_clinic_id(row.clinic_id, clinic_id, f"treatments[{index}].clinic_id")
    for index, row in enumerate(snapshot.planned_applications):
        _validate_clinic_id(row.clinic_id, clinic_id, f"planned_applications[{index}].clinic_id")
    for index, row in enumerate(snapshot.stock_positions):
        _validate_clinic_id(row.clinic_id, clinic_id, f"stock_positions[{index}].clinic_id")
    for index, row in enumerate(snapshot.imports):
        _validate_clinic_id(row.clinic_id, clinic_id, f"imports[{index}].clinic_id")


def build_administrative_snapshot(
    *,
    clinic_id: str,
    patients: Sequence[PatientRecord] = (),
    medications: Sequence[MedicationRecord] = (),
    treatments: Sequence[TreatmentRecord] = (),
    planned_applications: Sequence[PlannedApplicationRecord] = (),
    stock_positions: Sequence[StockPositionRecord] = (),
    imports: Sequence[ImportSessionRecord] = (),
) -> AdministrativeSnapshot:
    normalized_clinic_id = _require_text(clinic_id, "clinic_id")
    snapshot = AdministrativeSnapshot(
        meta=SnapshotMeta(
            schema_version=ADMIN_SNAPSHOT_SCHEMA_VERSION,
            snapshot_id=str(uuid4()),
            clinic_id=normalized_clinic_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
            review_required=True,
        ),
        patients=tuple(patients),
        medications=tuple(medications),
        treatments=tuple(treatments),
        planned_applications=tuple(planned_applications),
        stock_positions=tuple(stock_positions),
        imports=tuple(imports),
    )
    _validate_snapshot(snapshot)
    return snapshot


def administrative_snapshot_to_dict(snapshot: AdministrativeSnapshot) -> dict[str, Any]:
    clinic_id = _require_text(snapshot.meta.clinic_id, "meta.clinic_id")
    _validate_snapshot(snapshot)

    return {
        "meta": {
            "schema_version": _require_text(snapshot.meta.schema_version, "meta.schema_version"),
            "snapshot_id": _require_text(snapshot.meta.snapshot_id, "meta.snapshot_id"),
            "clinic_id": clinic_id,
            "generated_at": _require_text(snapshot.meta.generated_at, "meta.generated_at"),
            "review_required": _require_bool(snapshot.meta.review_required, "meta.review_required"),
        },
        "patients": [
            {
                "patient_id": _require_text(row.patient_id, f"patients[{index}].patient_id"),
                "clinic_id": row.clinic_id,
                "display_name": _require_text(row.display_name, f"patients[{index}].display_name"),
            }
            for index, row in enumerate(snapshot.patients)
        ],
        "medications": [
            {
                "medication_id": _require_text(row.medication_id, f"medications[{index}].medication_id"),
                "clinic_id": row.clinic_id,
                "name": _require_text(row.name, f"medications[{index}].name"),
                "clinical_unit": _require_text(row.clinical_unit, f"medications[{index}].clinical_unit"),
                "stock_unit": _require_text(row.stock_unit, f"medications[{index}].stock_unit"),
            }
            for index, row in enumerate(snapshot.medications)
        ],
        "treatments": [
            {
                "treatment_id": _require_text(row.treatment_id, f"treatments[{index}].treatment_id"),
                "clinic_id": row.clinic_id,
                "patient_id": _require_text(row.patient_id, f"treatments[{index}].patient_id"),
                "medication_id": _require_text(row.medication_id, f"treatments[{index}].medication_id"),
                "start_date": _require_text(row.start_date, f"treatments[{index}].start_date"),
                "status": _require_text(row.status, f"treatments[{index}].status"),
            }
            for index, row in enumerate(snapshot.treatments)
        ],
        "planned_applications": [
            {
                "application_id": _require_text(
                    row.application_id,
                    f"planned_applications[{index}].application_id",
                ),
                "clinic_id": row.clinic_id,
                "treatment_id": _require_text(
                    row.treatment_id,
                    f"planned_applications[{index}].treatment_id",
                ),
                "planned_date": _require_text(
                    row.planned_date,
                    f"planned_applications[{index}].planned_date",
                ),
                "dose": _require_number(row.dose, f"planned_applications[{index}].dose", min_value=0.0),
                "unit": _require_text(row.unit, f"planned_applications[{index}].unit"),
                "status": _require_text(row.status, f"planned_applications[{index}].status"),
                "source": _require_text(row.source, f"planned_applications[{index}].source"),
            }
            for index, row in enumerate(snapshot.planned_applications)
        ],
        "stock_positions": [
            {
                "position_id": _require_text(row.position_id, f"stock_positions[{index}].position_id"),
                "clinic_id": row.clinic_id,
                "medication_id": _require_text(
                    row.medication_id,
                    f"stock_positions[{index}].medication_id",
                ),
                "reference_date": _require_text(
                    row.reference_date,
                    f"stock_positions[{index}].reference_date",
                ),
                "quantity": _require_number(row.quantity, f"stock_positions[{index}].quantity", min_value=0.0),
                "unit": _require_text(row.unit, f"stock_positions[{index}].unit"),
            }
            for index, row in enumerate(snapshot.stock_positions)
        ],
        "imports": [
            {
                "import_id": _require_text(row.import_id, f"imports[{index}].import_id"),
                "clinic_id": row.clinic_id,
                "source_kind": _require_text(row.source_kind, f"imports[{index}].source_kind"),
                "reference_date": _require_text(row.reference_date, f"imports[{index}].reference_date"),
                "status": _require_text(row.status, f"imports[{index}].status"),
            }
            for index, row in enumerate(snapshot.imports)
        ],
    }


def administrative_snapshot_from_dict(payload: Mapping[str, Any]) -> AdministrativeSnapshot:
    document = _require_mapping(payload, "snapshot")
    meta_payload = _require_mapping(document.get("meta"), "meta")
    schema_version = _require_text(meta_payload.get("schema_version"), "meta.schema_version")
    if schema_version != ADMIN_SNAPSHOT_SCHEMA_VERSION:
        raise AdminContractValidationError("meta.schema_version is not supported")
    clinic_id = _require_text(meta_payload.get("clinic_id"), "meta.clinic_id")
    snapshot = AdministrativeSnapshot(
        meta=SnapshotMeta(
            schema_version=schema_version,
            snapshot_id=_require_text(meta_payload.get("snapshot_id"), "meta.snapshot_id"),
            clinic_id=clinic_id,
            generated_at=_require_text(meta_payload.get("generated_at"), "meta.generated_at"),
            review_required=_require_bool(meta_payload.get("review_required"), "meta.review_required"),
        ),
        patients=tuple(
            PatientRecord(
                patient_id=_require_text(item.get("patient_id"), f"patients[{index}].patient_id"),
                clinic_id=_validate_clinic_id(item.get("clinic_id"), clinic_id, f"patients[{index}].clinic_id"),
                display_name=_require_text(item.get("display_name"), f"patients[{index}].display_name"),
            )
            for index, item in enumerate(
                _require_mapping(row, "patients[]")
                for row in _require_sequence(document.get("patients"), "patients")
            )
        ),
        medications=tuple(
            MedicationRecord(
                medication_id=_require_text(item.get("medication_id"), f"medications[{index}].medication_id"),
                clinic_id=_validate_clinic_id(item.get("clinic_id"), clinic_id, f"medications[{index}].clinic_id"),
                name=_require_text(item.get("name"), f"medications[{index}].name"),
                clinical_unit=_require_text(item.get("clinical_unit"), f"medications[{index}].clinical_unit"),
                stock_unit=_require_text(item.get("stock_unit"), f"medications[{index}].stock_unit"),
            )
            for index, item in enumerate(
                _require_mapping(row, "medications[]")
                for row in _require_sequence(document.get("medications"), "medications")
            )
        ),
        treatments=tuple(
            TreatmentRecord(
                treatment_id=_require_text(item.get("treatment_id"), f"treatments[{index}].treatment_id"),
                clinic_id=_validate_clinic_id(item.get("clinic_id"), clinic_id, f"treatments[{index}].clinic_id"),
                patient_id=_require_text(item.get("patient_id"), f"treatments[{index}].patient_id"),
                medication_id=_require_text(item.get("medication_id"), f"treatments[{index}].medication_id"),
                start_date=_require_text(item.get("start_date"), f"treatments[{index}].start_date"),
                status=_require_text(item.get("status"), f"treatments[{index}].status"),
            )
            for index, item in enumerate(
                _require_mapping(row, "treatments[]")
                for row in _require_sequence(document.get("treatments"), "treatments")
            )
        ),
        planned_applications=tuple(
            PlannedApplicationRecord(
                application_id=_require_text(
                    item.get("application_id"),
                    f"planned_applications[{index}].application_id",
                ),
                clinic_id=_validate_clinic_id(
                    item.get("clinic_id"),
                    clinic_id,
                    f"planned_applications[{index}].clinic_id",
                ),
                treatment_id=_require_text(
                    item.get("treatment_id"),
                    f"planned_applications[{index}].treatment_id",
                ),
                planned_date=_require_text(
                    item.get("planned_date"),
                    f"planned_applications[{index}].planned_date",
                ),
                dose=_require_number(item.get("dose"), f"planned_applications[{index}].dose", min_value=0.0),
                unit=_require_text(item.get("unit"), f"planned_applications[{index}].unit"),
                status=_require_text(item.get("status"), f"planned_applications[{index}].status"),
                source=_require_text(item.get("source"), f"planned_applications[{index}].source"),
            )
            for index, item in enumerate(
                _require_mapping(row, "planned_applications[]")
                for row in _require_sequence(document.get("planned_applications"), "planned_applications")
            )
        ),
        stock_positions=tuple(
            StockPositionRecord(
                position_id=_require_text(item.get("position_id"), f"stock_positions[{index}].position_id"),
                clinic_id=_validate_clinic_id(
                    item.get("clinic_id"),
                    clinic_id,
                    f"stock_positions[{index}].clinic_id",
                ),
                medication_id=_require_text(
                    item.get("medication_id"),
                    f"stock_positions[{index}].medication_id",
                ),
                reference_date=_require_text(
                    item.get("reference_date"),
                    f"stock_positions[{index}].reference_date",
                ),
                quantity=_require_number(item.get("quantity"), f"stock_positions[{index}].quantity", min_value=0.0),
                unit=_require_text(item.get("unit"), f"stock_positions[{index}].unit"),
            )
            for index, item in enumerate(
                _require_mapping(row, "stock_positions[]")
                for row in _require_sequence(document.get("stock_positions"), "stock_positions")
            )
        ),
        imports=tuple(
            ImportSessionRecord(
                import_id=_require_text(item.get("import_id"), f"imports[{index}].import_id"),
                clinic_id=_validate_clinic_id(item.get("clinic_id"), clinic_id, f"imports[{index}].clinic_id"),
                source_kind=_require_text(item.get("source_kind"), f"imports[{index}].source_kind"),
                reference_date=_require_text(item.get("reference_date"), f"imports[{index}].reference_date"),
                status=_require_text(item.get("status"), f"imports[{index}].status"),
            )
            for index, item in enumerate(
                _require_mapping(row, "imports[]")
                for row in _require_sequence(document.get("imports"), "imports")
            )
        ),
    )
    administrative_snapshot_to_dict(snapshot)
    return snapshot
