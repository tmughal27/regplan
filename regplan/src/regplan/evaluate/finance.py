"""Finance engine: TCO, NPV, payback, cost-of-delay computation."""
from __future__ import annotations

from regplan.errors import MissingAssumptionError
from regplan.models.assumptions import Assumptions
from regplan.models.finance import CashFlow, FinancialResult
from regplan.models.work import Schedule, WorkItem


def _require(value: object, name: str) -> None:
    if value is None:
        raise MissingAssumptionError(name)


def compute_financial_result(
    schedule: Schedule,
    work_items: list[WorkItem],
    assumptions: Assumptions,
) -> FinancialResult:
    """Compute quarterly cash flows, TCO, NPV, payback period, and cost-of-delay."""
    _require(assumptions.discount_rate, "discount_rate")
    _require(assumptions.daily_rate_gbp, "daily_rate_gbp")
    _require(assumptions.ramp_up_quarters, "ramp_up_quarters")
    _require(assumptions.horizon_quarters, "horizon_quarters")

    horizon = assumptions.horizon_quarters
    discount_rate = assumptions.discount_rate
    ramp_up = assumptions.ramp_up_quarters

    item_map = {wi.id: wi for wi in work_items}
    starts = schedule.work_item_starts

    # Build per-quarter aggregates
    capex_by_q: list[float] = [0.0] * horizon
    migration_by_q: list[float] = [0.0] * horizon
    savings_by_q: list[float] = [0.0] * horizon

    for wi_id, start_q in starts.items():
        wi = item_map.get(wi_id)
        if wi is None:
            continue
        end_q = start_q + wi.duration_quarters
        # Capex: distributed evenly across item's quarters
        cost_per_q = wi.cost_gbp / max(wi.duration_quarters, 1)
        for q in range(start_q, min(end_q, horizon)):
            if wi.rule_id is not None:
                migration_by_q[q] += cost_per_q
            else:
                capex_by_q[q] += cost_per_q
        # Benefit profile: applied after completion + ramp-up
        benefit_start = end_q + ramp_up
        for i, benefit in enumerate(wi.benefit_profile):
            bq = benefit_start + i
            if bq < horizon:
                savings_by_q[bq] += benefit

    cash_flows: list[CashFlow] = []
    cumulative_net = 0.0
    payback_quarter: int | None = None
    tco = 0.0
    npv = 0.0

    for q in range(horizon):
        capex = capex_by_q[q]
        migration = migration_by_q[q]
        savings = savings_by_q[q]
        opex = 0.0  # ongoing opex can be extended; kept at 0 for now
        net = savings - capex - migration - opex
        cf = CashFlow(
            quarter=q,
            capex=capex,
            opex=opex,
            run_cost_savings=savings,
            migration_cost=migration,
            net=net,
        )
        cash_flows.append(cf)

        tco += capex + opex + migration
        discount_factor = (1.0 + discount_rate) ** q
        npv += net / discount_factor

        cumulative_net += net
        if payback_quarter is None and cumulative_net >= 0.0:
            payback_quarter = q

    # Cost-of-delay: financial impact of deferring each item by one quarter
    cost_of_delay: dict[str, float] = {}
    for wi_id, start_q in starts.items():
        wi = item_map.get(wi_id)
        if wi is None:
            continue
        end_q = start_q + wi.duration_quarters
        delayed_end = end_q + 1
        # Loss = one quarter of benefit profile foregone
        if wi.benefit_profile:
            benefit_start = end_q + ramp_up
            delayed_benefit_start = delayed_end + ramp_up
            # Extra quarter of savings lost
            lost = wi.benefit_profile[0] if wi.benefit_profile else 0.0
        else:
            lost = 0.0
        cost_of_delay[wi_id] = lost

    return FinancialResult(
        cash_flows=cash_flows,
        tco=tco,
        npv=npv,
        payback_quarter=payback_quarter,
        cost_of_delay=cost_of_delay,
        assumption_ids=[
            "discount_rate",
            "daily_rate_gbp",
            "ramp_up_quarters",
            "horizon_quarters",
        ],
    )
