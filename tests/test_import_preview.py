import unittest

from tools.import_preview import (
    IMPORT_PREVIEW_SCHEMA_VERSION,
    ImportValidationError,
    build_mapping_model,
    mapping_model_from_dict,
    mapping_model_to_dict,
    preview_forecast_import,
    suggest_column_mapping,
)


class ImportPreviewTests(unittest.TestCase):
    def test_suggest_column_mapping_recognizes_initial_forecast_headers(self) -> None:
        mapping = suggest_column_mapping(
            [
                "Plano",
                "Paciente",
                "Medicamento",
                "Início do tratamento",
                "Intervalo do ciclo em dias",
                "Dose por ciclo",
                "Unidade",
                "Quantidade de ciclos previstos",
                "Aplicações por ciclo",
                "Status",
            ]
        )

        self.assertEqual(mapping["patient"], "Paciente")
        self.assertEqual(mapping["medication"], "Medicamento")
        self.assertEqual(mapping["treatment_start"], "Início do tratamento")
        self.assertEqual(mapping["applications_per_cycle"], "Aplicações por ciclo")

    def test_mapping_model_round_trip_preserves_contract(self) -> None:
        model = build_mapping_model(
            model_name="Aplicacoes padrao",
            source_kind="forecast_applications",
            field_mapping={"patient": "Paciente", "medication": "Medicamento"},
        )

        payload = mapping_model_to_dict(model)
        restored = mapping_model_from_dict(payload)

        self.assertEqual(payload["meta"]["schema_version"], IMPORT_PREVIEW_SCHEMA_VERSION)
        self.assertEqual(restored, model)

    def test_preview_forecast_import_classifies_rows(self) -> None:
        field_mapping = {
            "plan": "Plano",
            "patient": "Paciente",
            "medication": "Medicamento",
            "treatment_start": "Início do tratamento",
            "cycle_interval_days": "Intervalo do ciclo em dias",
            "dose_per_cycle": "Dose por ciclo",
            "unit": "Unidade",
            "cycles_planned": "Quantidade de ciclos previstos",
            "applications_per_cycle": "Aplicações por ciclo",
            "status": "Status",
        }
        preview = preview_forecast_import(
            [
                {
                    "Plano": "Unimed",
                    "Paciente": "Paciente 1",
                    "Medicamento": "Medicamento A",
                    "Início do tratamento": "2026-08-15",
                    "Intervalo do ciclo em dias": 21,
                    "Dose por ciclo": 100,
                    "Unidade": "mg",
                    "Quantidade de ciclos previstos": 4,
                    "Aplicações por ciclo": 1,
                    "Status": "ativo",
                },
                {
                    "Plano": "Unimed",
                    "Paciente": "Paciente 2",
                    "Medicamento": "Medicamento B",
                    "Início do tratamento": "2026-08-01",
                    "Intervalo do ciclo em dias": 14,
                    "Dose por ciclo": 80,
                    "Unidade": "mg",
                    "Quantidade de ciclos previstos": 6,
                    "Aplicações por ciclo": 1,
                    "Status": "suspenso",
                },
                {
                    "Plano": "Unimed",
                    "Paciente": "Paciente 3",
                    "Medicamento": "Medicamento C",
                    "Início do tratamento": "2026-08-18",
                    "Intervalo do ciclo em dias": 21,
                    "Dose por ciclo": 50,
                    "Unidade": "mg",
                    "Quantidade de ciclos previstos": 4,
                    "Aplicações por ciclo": 1,
                    "Status": "cancelado",
                },
                {
                    "Plano": "Unimed",
                    "Paciente": "Paciente 1",
                    "Medicamento": "Medicamento A",
                    "Início do tratamento": "2026-08-15",
                    "Intervalo do ciclo em dias": 21,
                    "Dose por ciclo": 100,
                    "Unidade": "mg",
                    "Quantidade de ciclos previstos": 4,
                    "Aplicações por ciclo": 1,
                    "Status": "ativo",
                },
                {
                    "Plano": "Unimed",
                    "Paciente": "Paciente 4",
                    "Medicamento": "Medicamento Z",
                    "Início do tratamento": "2026-08-20",
                    "Intervalo do ciclo em dias": 21,
                    "Dose por ciclo": 90,
                    "Unidade": "mg",
                    "Quantidade de ciclos previstos": 4,
                    "Aplicações por ciclo": 1,
                    "Status": "ativo",
                },
            ],
            field_mapping=field_mapping,
            reference_date="2026-08-10",
            known_medications=["Medicamento A", "Medicamento B"],
            known_patients=["Paciente 1", "Paciente 2", "Paciente 3"],
        )

        self.assertEqual(preview["summary"]["total_rows"], 5)
        self.assertEqual(preview["summary"]["valid"], 1)
        self.assertEqual(preview["summary"]["requires_review"], 2)
        self.assertEqual(preview["summary"]["rejected"], 1)
        self.assertEqual(preview["summary"]["duplicate"], 1)
        self.assertEqual(preview["rows"][1]["classification"], "requires_review")
        self.assertIn("status exige revisão humana", preview["rows"][1]["messages"])
        self.assertIn("data de início anterior à data de referência", preview["rows"][1]["messages"])
        self.assertIn("medicamento não localizado na base conhecida", preview["rows"][4]["messages"])
        self.assertIn("paciente não localizado na base conhecida", preview["rows"][4]["messages"])

    def test_preview_forecast_import_rejects_missing_required_mapping(self) -> None:
        with self.assertRaises(ImportValidationError):
            preview_forecast_import(
                rows=[],
                field_mapping={"patient": "Paciente"},
                reference_date="2026-08-10",
            )

    def test_preview_forecast_import_marks_invalid_rows_as_error(self) -> None:
        preview = preview_forecast_import(
            [
                {
                    "Paciente": "Paciente 1",
                    "Medicamento": "Medicamento A",
                    "Início do tratamento": "data-invalida",
                    "Intervalo do ciclo em dias": 21,
                    "Dose por ciclo": 100,
                    "Unidade": "mg",
                    "Quantidade de ciclos previstos": 4,
                    "Aplicações por ciclo": 1,
                    "Status": "ativo",
                }
            ],
            field_mapping={
                "patient": "Paciente",
                "medication": "Medicamento",
                "treatment_start": "Início do tratamento",
                "cycle_interval_days": "Intervalo do ciclo em dias",
                "dose_per_cycle": "Dose por ciclo",
                "unit": "Unidade",
                "cycles_planned": "Quantidade de ciclos previstos",
                "applications_per_cycle": "Aplicações por ciclo",
                "status": "Status",
            },
            reference_date="2026-08-10",
        )

        self.assertEqual(preview["summary"]["error"], 1)
        self.assertEqual(preview["rows"][0]["classification"], "error")
        self.assertIn("treatment_start must be a date", preview["rows"][0]["messages"][0])


if __name__ == "__main__":
    unittest.main()
