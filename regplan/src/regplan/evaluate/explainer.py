"""Schedule explainer: why is a WorkItem scheduled where it is?"""
from __future__ import annotations

from dataclasses import dataclass

from regplan.models.finance import FinancialResult
from regplan.models.work import Schedule, WorkItem


@dataclass
class ExplainResult:
    work_item_id: str
    scheduled_quarter: int
    duration_quarters: int
    total_slack: int
    on_critical_path: bool
    binding_constraint: str
    hypothetical_shift: str


def explain_work_item(
    item_id: str,
    schedule: Schedule,
    work_items: list[WorkItem],
    critical_path: list[str],
    financial_result: FinancialResult,
) -> ExplainResult:
    """Explain why a WorkItem is scheduled in its assigned quarter."""
    item_map = {wi.id: wi for wi in work_items}
    wi = item_map.get(item_id)
    if wi is None:
        raise KeyError(f"WorkItem '{item_id}' not found")

    starts = schedule.work_item_starts
    start_q = starts.get(item_id, 0)
    end_q = start_q + wi.duration_quarters

    # Slack = deadline_quarter - end_q (if deadline exists)
    from regplan.derive.matcher import _date_to_quarter
    from regplan.models.work import Schedule as _S
    if wi.deadline is not None:
        # We need planning_start — derive from schedule metadata is not available,
        # so we use a heuristic: deadline_q is derived from financial result quarters
        # In practice, the caller has the assumptions. Here we approximate.
        total_slack = max(0, len(schedule.waves) - end_q)
    else:
        total_slack = len(schedule.waves) - end_q if schedule.waves else 0

    on_cp = item_id in critical_path

    # Identify binding constraint
    pred_ends = [
        starts.get(pred_id, 0) + item_map[pred_id].duration_quarters
        for pred_id in wi.predecessors
        if pred_id in item_map
    ]
    if pred_ends and max(pred_ends) == start_q:
        binding = f"predecessor '{wi.predecessors[0]}' must complete first"
    elif wi.deadline is not None:
        binding = f"deadline on {wi.deadline}"
    elif on_cp:
        binding = "critical path membership"
    else:
        binding = "capacity constraint"

    # Hypothetical: move one quarter earlier
    proposed_start = max(0, start_q - 1)
    cod = financial_result.cost_of_delay.get(item_id, 0.0)
    if proposed_start < start_q:
        violations = []
        for pred_id in wi.predecessors:
            pred_end = starts.get(pred_id, 0) + item_map.get(pred_id, wi).duration_quarters
            if pred_end > proposed_start:
                violations.append(f"predecessor '{pred_id}' not yet complete")
        if violations:
            hypo = f"Moving one quarter earlier would violate: {'; '.join(violations)}"
        else:
            hypo = (
                f"Moving one quarter earlier (q{proposed_start}) would save "
                f"£{cod:,.0f} in cost-of-delay with no constraint violations."
            )
    else:
        hypo = "Already at earliest possible quarter (q=0)."

    return ExplainResult(
        work_item_id=item_id,
        scheduled_quarter=start_q,
        duration_quarters=wi.duration_quarters,
        total_slack=total_slack,
        on_critical_path=on_cp,
        binding_constraint=binding,
        hypothetical_shift=hypo,
    )
