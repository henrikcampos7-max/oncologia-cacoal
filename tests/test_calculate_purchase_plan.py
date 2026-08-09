import unittest

from tools.calculate_purchase_plan import (
    CalculationValidationError,
    DemandRecord,
    PURCHASE_PLAN_SCHEMA_VERSION,
    aggregate_monthly_demand,
    build_purchase_plan_snapshot,
    calculate_purchase_plan,
    purchase_plan_snapshot_from_dict,
    purchase_plan_snapshot_to_dict,
)


class PurchasePlanTests(unittest.TestCase):
    def test_calculate_purchase_plan_projects_balance_with_carry_over(self) -> None:
        plan = calculate_purchase_plan(
            initial_stock={"Medicamento A": 120},
            monthly_demand=[
                DemandRecord("Medicamento A", "2026-08", 100),
                DemandRecord("Medicamento A", "2026-09", 70),
            ],
        )

        self.assertEqual(len(plan), 2)
        self.assertEqual(plan[0].suggested_purchase, 0)
        self.assertEqual(plan[0].closing_stock, 20)
        self.assertEqual(plan[1].opening_stock, 20)
        self.assertEqual(plan[1].suggested_purchase, 50)
        self.assertEqual(plan[1].closing_stock, 0)

    def test_aggregate_monthly_demand_uses_only_active_statuses(self) -> None:
        aggregated = aggregate_monthly_demand(
            applications=[
                {"medication": "Medicamento B", "planned_date": "2026-08-10", "dose_total": 25, "status": "ativo"},
                {"medication": "Medicamento B", "planned_date": "2026-08-20", "dose_total": 5, "status": "suspenso"},
                {"medication": "Medicamento B", "planned_date": "2026-08-25", "dose_total": 10, "status": "active"},
            ]
        )

        self.assertEqual(len(aggregated), 1)
        self.assertEqual(aggregated[0].medication, "Medicamento B")
        self.assertEqual(aggregated[0].month, "2026-08")
        self.assertEqual(aggregated[0].amount, 35)

    def test_calculate_purchase_plan_rejects_invalid_month(self) -> None:
        with self.assertRaises(CalculationValidationError):
            calculate_purchase_plan(
                initial_stock={},
                monthly_demand=[DemandRecord("Medicamento C", "08-2026", 10)],
            )

    def test_aggregate_monthly_demand_requires_valid_date(self) -> None:
        with self.assertRaises(CalculationValidationError):
            aggregate_monthly_demand(
                applications=[
                    {"medication": "Medicamento D", "planned_date": "10/08/2026", "dose_total": 10, "status": "ativo"}
                ]
            )

    def test_purchase_plan_snapshot_round_trip_preserves_contract(self) -> None:
        snapshot = build_purchase_plan_snapshot(
            initial_stock={"Medicamento A": 120},
            monthly_demand=[
                DemandRecord("Medicamento A", "2026-08", 100),
                DemandRecord("Medicamento A", "2026-09", 70),
            ],
        )

        payload = purchase_plan_snapshot_to_dict(snapshot)
        restored = purchase_plan_snapshot_from_dict(payload)

        self.assertEqual(payload["meta"]["schema_version"], PURCHASE_PLAN_SCHEMA_VERSION)
        self.assertEqual(restored, snapshot)

    def test_purchase_plan_snapshot_rejects_inconsistent_projection(self) -> None:
        snapshot = build_purchase_plan_snapshot(
            initial_stock={"Medicamento A": 120},
            monthly_demand=[
                DemandRecord("Medicamento A", "2026-08", 100),
                DemandRecord("Medicamento A", "2026-09", 70),
            ],
        )
        payload = purchase_plan_snapshot_to_dict(snapshot)
        payload["projections"][1]["opening_stock"] = 999

        with self.assertRaises(CalculationValidationError):
            purchase_plan_snapshot_from_dict(payload)

    def test_purchase_plan_snapshot_rejects_duplicate_monthly_demand(self) -> None:
        snapshot = build_purchase_plan_snapshot(
            initial_stock={"Medicamento A": 120},
            monthly_demand=[DemandRecord("Medicamento A", "2026-08", 100)],
        )
        payload = purchase_plan_snapshot_to_dict(snapshot)
        payload["monthly_demand"].append(
            {"medication": "Medicamento A", "month": "2026-08", "amount": 100}
        )

        with self.assertRaises(CalculationValidationError):
            purchase_plan_snapshot_from_dict(payload)


if __name__ == "__main__":
    unittest.main()
