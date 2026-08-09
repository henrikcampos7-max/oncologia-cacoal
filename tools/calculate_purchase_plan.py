from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from math import isfinite
from typing import Any, Iterable, Mapping, Sequence
from uuid import uuid4


PURCHASE_PLAN_SCHEMA_VERSION = "purchase-plan.v1"
FLOAT_TOLERANCE = 1e-9


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


@dataclass(frozen=True)
class StockRecord:
    medication: str
    amount: float


@dataclass(frozen=True)
class PurchasePlanMeta:
    schema_version: str
    calculation_id: str
    generated_at: str
    status: str
    review_required: bool


@dataclass(frozen=True)
class PurchasePlanSnapshot:
    meta: PurchasePlanMeta
    initial_stock: tuple[StockRecord, ...]
    monthly_demand: tuple[DemandRecord, ...]
    projections: tuple[MonthlyProjection, ...]


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


def _require_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CalculationValidationError(f"{field_name} must be an object")
    return value


def _require_sequence(value: Any, field_name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise CalculationValidationError(f"{field_name} must be a list")
    return value


def _numbers_match(left: float, right: float) -> bool:
    return abs(left - right) <= FLOAT_TOLERANCE


def _require_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise CalculationValidationError(f"{field_name} must be a boolean")
    return value


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


def _normalize_initial_stock(initial_stock: Mapping[str, Any]) -> dict[str, float]:
    stock_by_medication: dict[str, float] = {}
    for medication, amount in initial_stock.items():
        name = _require_non_empty_text(str(medication), "initial_stock.medication")
        stock_by_medication[name] = _require_number(amount, f"initial_stock[{name}]", min_value=0.0)
    return stock_by_medication


def _normalize_monthly_demand(monthly_demand: Sequence[DemandRecord]) -> dict[str, dict[str, float]]:
    grouped_demand: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for index, row in enumerate(monthly_demand):
        name = _require_non_empty_text(str(row.medication), f"monthly_demand[{index}].medication")
        month = _validate_month(str(row.month))
        amount = _require_number(row.amount, f"monthly_demand[{index}].amount", min_value=0.0)
        grouped_demand[name][month] += amount
    return grouped_demand


def _stock_records_to_mapping(records: Sequence[StockRecord]) -> dict[str, float]:
    stock_by_medication: dict[str, float] = {}
    for index, record in enumerate(records):
        medication = _require_non_empty_text(str(record.medication), f"initial_stock[{index}].medication")
        if medication in stock_by_medication:
            raise CalculationValidationError(f"initial_stock[{index}].medication is duplicated")
        stock_by_medication[medication] = _require_number(
            record.amount,
            f"initial_stock[{index}].amount",
            min_value=0.0,
        )
    return stock_by_medication


def _monthly_demand_records_to_sequence(records: Sequence[DemandRecord]) -> list[DemandRecord]:
    normalized: list[DemandRecord] = []
    seen_keys: set[tuple[str, str]] = set()
    for index, record in enumerate(records):
        medication = _require_non_empty_text(str(record.medication), f"monthly_demand[{index}].medication")
        month = _validate_month(str(record.month))
        key = (medication, month)
        if key in seen_keys:
            raise CalculationValidationError(f"monthly_demand[{index}] is duplicated")
        seen_keys.add(key)
        normalized.append(
            DemandRecord(
                medication=medication,
                month=month,
                amount=_require_number(record.amount, f"monthly_demand[{index}].amount", min_value=0.0),
            )
        )
    return normalized


def _projection_records_to_sequence(records: Sequence[MonthlyProjection]) -> list[MonthlyProjection]:
    normalized: list[MonthlyProjection] = []
    seen_keys: set[tuple[str, str]] = set()
    previous_closing_by_medication: dict[str, float] = {}
    previous_month_by_medication: dict[str, str] = {}
    for index, record in enumerate(records):
        medication = _require_non_empty_text(str(record.medication), f"projections[{index}].medication")
        month = _validate_month(str(record.month))
        key = (medication, month)
        if key in seen_keys:
            raise CalculationValidationError(f"projections[{index}] is duplicated")
        seen_keys.add(key)

        opening_stock = _require_number(record.opening_stock, f"projections[{index}].opening_stock", min_value=0.0)
        demand = _require_number(record.demand, f"projections[{index}].demand", min_value=0.0)
        suggested_purchase = _require_number(
            record.suggested_purchase,
            f"projections[{index}].suggested_purchase",
            min_value=0.0,
        )
        closing_stock = _require_number(record.closing_stock, f"projections[{index}].closing_stock", min_value=0.0)

        expected_purchase = max(0.0, demand - opening_stock)
        if not _numbers_match(suggested_purchase, expected_purchase):
            raise CalculationValidationError(f"projections[{index}].suggested_purchase is inconsistent")
        expected_closing = max(0.0, opening_stock - demand)
        if not _numbers_match(closing_stock, expected_closing):
            raise CalculationValidationError(f"projections[{index}].closing_stock is inconsistent")

        previous_closing = previous_closing_by_medication.get(medication)
        if previous_closing is not None and not _numbers_match(opening_stock, previous_closing):
            previous_month = previous_month_by_medication[medication]
            raise CalculationValidationError(
                f"projections[{index}].opening_stock must match prior closing_stock for {medication} after {previous_month}"
            )
        previous_closing_by_medication[medication] = expected_closing
        previous_month_by_medication[medication] = month
        normalized.append(
            MonthlyProjection(
                medication=medication,
                month=month,
                opening_stock=opening_stock,
                demand=demand,
                suggested_purchase=suggested_purchase,
                closing_stock=closing_stock,
            )
        )
    return normalized


def build_purchase_plan_snapshot(
    initial_stock: Mapping[str, Any],
    monthly_demand: Sequence[DemandRecord],
) -> PurchasePlanSnapshot:
    normalized_stock = _normalize_initial_stock(initial_stock)
    normalized_demand = tuple(_monthly_demand_records_to_sequence(monthly_demand))
    projections = calculate_purchase_plan(initial_stock=normalized_stock, monthly_demand=normalized_demand)
    stock_records = tuple(
        StockRecord(medication=medication, amount=amount)
        for medication, amount in sorted(normalized_stock.items())
    )
    return PurchasePlanSnapshot(
        meta=PurchasePlanMeta(
            schema_version=PURCHASE_PLAN_SCHEMA_VERSION,
            calculation_id=str(uuid4()),
            generated_at=datetime.now(timezone.utc).isoformat(),
            status="draft",
            review_required=True,
        ),
        initial_stock=stock_records,
        monthly_demand=normalized_demand,
        projections=tuple(projections),
    )


def purchase_plan_snapshot_to_dict(snapshot: PurchasePlanSnapshot) -> dict[str, Any]:
    return {
        "meta": {
            "schema_version": snapshot.meta.schema_version,
            "calculation_id": snapshot.meta.calculation_id,
            "generated_at": snapshot.meta.generated_at,
            "status": snapshot.meta.status,
            "review_required": snapshot.meta.review_required,
        },
        "initial_stock": [
            {"medication": row.medication, "amount": row.amount}
            for row in snapshot.initial_stock
        ],
        "monthly_demand": [
            {"medication": row.medication, "month": row.month, "amount": row.amount}
            for row in snapshot.monthly_demand
        ],
        "projections": [
            {
                "medication": row.medication,
                "month": row.month,
                "opening_stock": row.opening_stock,
                "demand": row.demand,
                "suggested_purchase": row.suggested_purchase,
                "closing_stock": row.closing_stock,
            }
            for row in snapshot.projections
        ],
    }


def purchase_plan_snapshot_from_dict(payload: Mapping[str, Any]) -> PurchasePlanSnapshot:
    document = _require_mapping(payload, "snapshot")
    meta_payload = _require_mapping(document.get("meta"), "meta")
    schema_version = _require_non_empty_text(str(meta_payload.get("schema_version", "")), "meta.schema_version")
    if schema_version != PURCHASE_PLAN_SCHEMA_VERSION:
        raise CalculationValidationError("meta.schema_version is not supported")

    meta = PurchasePlanMeta(
        schema_version=schema_version,
        calculation_id=_require_non_empty_text(str(meta_payload.get("calculation_id", "")), "meta.calculation_id"),
        generated_at=_require_non_empty_text(str(meta_payload.get("generated_at", "")), "meta.generated_at"),
        status=_require_non_empty_text(str(meta_payload.get("status", "")), "meta.status"),
        review_required=_require_bool(meta_payload.get("review_required"), "meta.review_required"),
    )

    stock_rows = _require_sequence(document.get("initial_stock"), "initial_stock")
    demand_rows = _require_sequence(document.get("monthly_demand"), "monthly_demand")
    projection_rows = _require_sequence(document.get("projections"), "projections")

    stock_records_list: list[StockRecord] = []
    for index, row in enumerate(stock_rows):
        item = _require_mapping(row, f"initial_stock[{index}]")
        stock_records_list.append(
            StockRecord(
                medication=_require_non_empty_text(
                    str(item.get("medication", "")),
                    f"initial_stock[{index}].medication",
                ),
                amount=_require_number(
                    item.get("amount"),
                    f"initial_stock[{index}].amount",
                    min_value=0.0,
                ),
            )
        )
    stock_records = tuple(stock_records_list)

    demand_records_list: list[DemandRecord] = []
    for index, row in enumerate(demand_rows):
        item = _require_mapping(row, f"monthly_demand[{index}]")
        demand_records_list.append(
            DemandRecord(
                medication=_require_non_empty_text(
                    str(item.get("medication", "")),
                    f"monthly_demand[{index}].medication",
                ),
                month=_validate_month(str(item.get("month", ""))),
                amount=_require_number(
                    item.get("amount"),
                    f"monthly_demand[{index}].amount",
                    min_value=0.0,
                ),
            )
        )
    demand_records = tuple(demand_records_list)

    projection_records_list: list[MonthlyProjection] = []
    for index, row in enumerate(projection_rows):
        item = _require_mapping(row, f"projections[{index}]")
        projection_records_list.append(
            MonthlyProjection(
                medication=_require_non_empty_text(
                    str(item.get("medication", "")),
                    f"projections[{index}].medication",
                ),
                month=_validate_month(str(item.get("month", ""))),
                opening_stock=_require_number(
                    item.get("opening_stock"),
                    f"projections[{index}].opening_stock",
                    min_value=0.0,
                ),
                demand=_require_number(
                    item.get("demand"),
                    f"projections[{index}].demand",
                    min_value=0.0,
                ),
                suggested_purchase=_require_number(
                    item.get("suggested_purchase"),
                    f"projections[{index}].suggested_purchase",
                    min_value=0.0,
                ),
                closing_stock=_require_number(
                    item.get("closing_stock"),
                    f"projections[{index}].closing_stock",
                    min_value=0.0,
                ),
            )
        )
    projection_records = tuple(projection_records_list)

    normalized_stock = _stock_records_to_mapping(stock_records)
    normalized_demand = tuple(_monthly_demand_records_to_sequence(demand_records))
    normalized_projections = tuple(_projection_records_to_sequence(projection_records))
    recalculated_projections = tuple(
        calculate_purchase_plan(initial_stock=normalized_stock, monthly_demand=normalized_demand)
    )
    if normalized_projections != recalculated_projections:
        raise CalculationValidationError("projections are inconsistent with initial_stock and monthly_demand")

    return PurchasePlanSnapshot(
        meta=meta,
        initial_stock=tuple(
            StockRecord(medication=medication, amount=amount)
            for medication, amount in sorted(normalized_stock.items())
        ),
        monthly_demand=normalized_demand,
        projections=normalized_projections,
    )


def calculate_purchase_plan(
    initial_stock: Mapping[str, Any],
    monthly_demand: Sequence[DemandRecord],
) -> list[MonthlyProjection]:
    stock_by_medication = _normalize_initial_stock(initial_stock)
    grouped_demand = _normalize_monthly_demand(monthly_demand)

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
