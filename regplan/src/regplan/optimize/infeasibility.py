"""Infeasibility report builder for the Optimize stage."""
from __future__ import annotations

from datetime import date, timedelta

from regplan.models.assumptions import Assumptions
from regplan.models.report import InfeasibilityReport
from regplan.models.work import WorkItem


def build_infeasibility_report(
    work_items: list[WorkItem],
    assumptions: Assumptions,
    conflicting_ids: list[str] | None = None,
) -> InfeasibilityReport:
    """Build an InfeasibilityReport explaining why no schedule exists.

    Uses heuristics to identify likely conflicting constraints when CP-SAT
    does not return a minimal infeasible subset directly.
    """
    items_by_id = {wi.id: wi for wi in work_items}

    # --- Identify conflicting work items ---
    if conflicting_ids:
        conflict_wis = [items_by_id[wid] for wid in conflicting_ids if wid in items_by_id]
    else:
        # Heuristic: items with deadlines that are too tight given their duration + predecessors
        conflict_wis = _find_tight_deadline_items(work_items, assumptions)

    conflicting_item_ids = [wi.id for wi in conflict_wis]
    conflicting_deadline_dates = sorted(
        {wi.deadline for wi in conflict_wis if wi.deadline is not None}
    )

    # --- Identify capacity issues ---
    conflicting_capacity: list[tuple[int, float]] = []
    total_capacity_demand = sum(wi.capacity_demand_days for wi in work_items)
    total_quarters = assumptions.horizon_quarters
    avg_demand_per_quarter = total_capacity_demand / max(total_quarters, 1)
    if avg_demand_per_quarter > assumptions.quarterly_capacity_days:
        conflicting_capacity.append((0, avg_demand_per_quarter))

    # --- Identify budget issues ---
    conflicting_budget: list[tuple[int, float]] = []
    total_cost = sum(wi.cost_gbp for wi in work_items)
    if total_cost > assumptions.cumulative_budget_gbp:
        conflicting_budget.append((0, total_cost))

    # --- Remediation suggestions ---
    remediations: list[str] = []
    if conflicting_deadline_dates:
        remediations.append(
            f"Extend the earliest conflicting deadline by at least one quarter "
            f"(currently {conflicting_deadline_dates[0]})."
        )
    if conflicting_capacity:
        excess = avg_demand_per_quarter - assumptions.quarterly_capacity_days
        remediations.append(
            f"Increase quarterly_capacity_days by at least {excess:.0f} days, "
            f"or reduce scope by removing lower-priority WorkItems."
        )
    if conflicting_budget:
        excess_cost = total_cost - assumptions.cumulative_budget_gbp
        remediations.append(
            f"Increase cumulative_budget_gbp by £{excess_cost:,.0f}, "
            f"or reduce scope by deferring optional modernisation items."
        )
    if not remediations:
        remediations.append(
            "Review predecessor chain lengths and deadline dates; consider splitting "
            "large WorkItems or increasing horizon_quarters."
        )

    return InfeasibilityReport(
        conflicting_work_item_ids=conflicting_item_ids,
        conflicting_deadline_dates=conflicting_deadline_dates,
        conflicting_capacity_limits=conflicting_capacity,
        conflicting_budget_limits=conflicting_budget,
        remediations=remediations,
    )


def _find_tight_deadline_items(
    work_items: list[WorkItem],
    assumptions: Assumptions,
) -> list[WorkItem]:
    """Identify items whose earliest possible start + duration exceeds their deadline quarter."""
    from regplan.derive.matcher import _date_to_quarter  # local import to avoid circularity

    tight: list[WorkItem] = []
    items_by_id = {wi.id: wi for wi in work_items}

    def earliest_start(wi: WorkItem, visited: set[str]) -> int:
        if wi.id in visited:
            return 0
        visited.add(wi.id)
        if not wi.predecessors:
            return 0
        return max(
            earliest_start(items_by_id[p], visited) + items_by_id[p].duration_quarters
            for p in wi.predecessors
            if p in items_by_id
        ) if wi.predecessors else 0

    for wi in work_items:
        if wi.deadline is None:
            continue
        deadline_q = _date_to_quarter(wi.deadline, assumptions.planning_start)
        es = earliest_start(wi, set())
        if es + wi.duration_quarters > deadline_q:
            tight.append(wi)
    return tight
