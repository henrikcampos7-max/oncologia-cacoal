import unittest

from tools.admin_contracts import (
    ADMIN_SNAPSHOT_SCHEMA_VERSION,
    AdminContractValidationError,
    AdministrativeSnapshot,
    ImportSessionRecord,
    MedicationRecord,
    PatientRecord,
    PlannedApplicationRecord,
    SnapshotMeta,
    StockPositionRecord,
    TreatmentRecord,
    administrative_snapshot_from_dict,
    administrative_snapshot_to_dict,
    build_administrative_snapshot,
)


class AdministrativeSnapshotTests(unittest.TestCase):
    def test_snapshot_round_trip_preserves_contract(self) -> None:
        snapshot = build_administrative_snapshot(
            clinic_id="clinic-demo",
            patients=(PatientRecord("p-1", "clinic-demo", "Paciente Fictício"),),
            medications=(MedicationRecord("m-1", "clinic-demo", "Medicamento A", "mg", "frasco"),),
            treatments=(TreatmentRecord("t-1", "clinic-demo", "p-1", "m-1", "2026-08-10", "ativo"),),
            planned_applications=(
                PlannedApplicationRecord(
                    "a-1",
                    "clinic-demo",
                    "t-1",
                    "2026-08-15",
                    120.0,
                    "mg",
                    "planejada",
                    "importacao",
                ),
            ),
            stock_positions=(StockPositionRecord("s-1", "clinic-demo", "m-1", "2026-08-10", 50.0, "frasco"),),
            imports=(ImportSessionRecord("i-1", "clinic-demo", "forecast_applications", "2026-08-10", "draft"),),
        )

        payload = administrative_snapshot_to_dict(snapshot)
        restored = administrative_snapshot_from_dict(payload)

        self.assertEqual(payload["meta"]["schema_version"], ADMIN_SNAPSHOT_SCHEMA_VERSION)
        self.assertEqual(restored, snapshot)

    def test_snapshot_rejects_record_from_other_clinic(self) -> None:
        snapshot = AdministrativeSnapshot(
            meta=SnapshotMeta(
                schema_version=ADMIN_SNAPSHOT_SCHEMA_VERSION,
                snapshot_id="snap-1",
                clinic_id="clinic-demo",
                generated_at="2026-08-09T00:00:00+00:00",
                review_required=True,
            ),
            patients=(PatientRecord("p-1", "outra-clinica", "Paciente Fictício"),),
            medications=(),
            treatments=(),
            planned_applications=(),
            stock_positions=(),
            imports=(),
        )

        with self.assertRaises(AdminContractValidationError):
            administrative_snapshot_to_dict(snapshot)


if __name__ == "__main__":
    unittest.main()
