"""Evaluate stage: financial engine and schedule explainer."""
from __future__ import annotations

from regplan.derive import DeriveResult
from regplan.evaluate.finance import compute_financial_result
from regplan.models.assumptions import Assumptions
from regplan.models.finance import FinancialResult
from regplan.models.work import Schedule


def evaluate(
    schedule: Schedule,
    derive_result: DeriveResult,
    assumptions: Assumptions,
) -> FinancialResult:
    """Run the Finance Engine to compute TCO, NPV, payback, and cost-of-delay."""
    return compute_financial_result(schedule, derive_result.work_items, assumptions)
