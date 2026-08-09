from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from math import isfinite
from typing import Any, Iterable, Mapping, Sequence


class CalculationValidationError(ValueError):
    pass


@dataclass(frozen=True)
class DemandRecord:
    medication: str
    month: str
    amount: float


@dataclass(frozen=True)
class MonthlyProjection:
    medication: str
    month: str
    opening_stock: float
    demand: float
    suggested_purchase: float
    closing_stock: float


def _require_non_empty_text(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise CalculationValidationError(f"{field_name} is required")
    return cleaned


def _require_number(value: Any, field_name: str, *, min_value: float = 0.0) -> float:
    if isinstance(value, bool):
        raise CalculationValidationError(f"{field_name} must be a number")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise CalculationValidationError(f"{field_name} must be a number") from exc
    if not isfinite(parsed):
        raise CalculationValidationError(f"{field_name} must be finite")
    if parsed < min_value:
        raise CalculationValidationError(f"{field_name} must be >= {min_value}")
    return parsed


def _validate_month(value: str) -> str:
    _require_non_empty_text(value, "month")
    try:
        datetime.strptime(value, "%Y-%m")
    except ValueError as exc:
        raise CalculationValidationError("month must be in YYYY-MM format") from exc
    return value


def _parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError as exc:
            raise CalculationValidationError("planned_date must be YYYY-MM-DD") from exc
    raise CalculationValidationError("planned_date must be a date or YYYY-MM-DD string")


def aggregate_monthly_demand(
    applications: Sequence[Mapping[str, Any]],
    *,
    active_statuses: Iterable[str] = ("ativo", "active"),
) -> list[DemandRecord]:
    statuses = {s.strip().lower() for s in active_statuses if s and s.strip()}
    if not statuses:
        raise CalculationValidationError("active_statuses must not be empty")

    aggregated: dict[tuple[str, str], float] = defaultdict(float)
    for index, item in enumerate(applications):
        medication = _require_non_empty_text(str(item.get("medication", "")), f"applications[{index}].medication")
        status = _require_non_empty_text(str(item.get("status", "")), f"applications[{index}].status").lower()
        if status not in statuses:
            continue
        planned_date = _parse_date(item.get("planned_date"))
        dose_total = _require_number(item.get("dose_total"), f"applications[{index}].dose_total", min_value=0.0)
        month = planned_date.strftime("%Y-%m")
        aggregated[(medication, month)] += dose_total

    return [
        DemandRecord(medication=medication, month=month, amount=amount)
        for (medication, month), amount in sorted(aggregated.items())
    ]


def calculate_purchase_plan(
    initial_stock: Mapping[str, Any],
    monthly_demand: Sequence[DemandRecord],
) -> list[MonthlyProjection]:
    stock_by_medication: dict[str, float] = {}
    for medication, amount in initial_stock.items():
        name = _require_non_empty_text(str(medication), "initial_stock.medication")
        stock_by_medication[name] = _require_number(amount, f"initial_stock[{name}]", min_value=0.0)

    grouped_demand: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for index, row in enumerate(monthly_demand):
        name = _require_non_empty_text(str(row.medication), f"monthly_demand[{index}].medication")
        month = _validate_month(str(row.month))
        amount = _require_number(row.amount, f"monthly_demand[{index}].amount", min_value=0.0)
        grouped_demand[name][month] += amount

    projections: list[MonthlyProjection] = []
    for medication, by_month in sorted(grouped_demand.items()):
        running_stock = stock_by_medication.get(medication, 0.0)
        for month in sorted(by_month):
            demand = by_month[month]
            suggested_purchase = max(0.0, demand - running_stock)
            closing_stock = max(0.0, running_stock - demand)
            projections.append(
                MonthlyProjection(
                    medication=medication,
                    month=month,
                    opening_stock=running_stock,
                    demand=demand,
                    suggested_purchase=suggested_purchase,
                    closing_stock=closing_stock,
                )
            )
            running_stock = closing_stock

    return projections
