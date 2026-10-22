"""Simulate stage: Monte Carlo simulation engine."""
from __future__ import annotations

from regplan.models.assumptions import Assumptions
from regplan.models.finance import FinancialResult
from regplan.models.simulation import SimulationResult
from regplan.models.work import Schedule, WorkItem
from regplan.simulate.monte_carlo import run_simulation


def simulate(
    schedule: Schedule,
    financial_result: FinancialResult,
    assumptions: Assumptions,
    n_runs: int,
    seed: int,
    work_items: list[WorkItem] | None = None,
) -> SimulationResult:
    """Run Monte Carlo simulation and return SimulationResult.

    *work_items* is optional; when omitted, deadline-miss probabilities are not computed.
    """
    return run_simulation(schedule, financial_result, work_items or [], assumptions, n_runs, seed)
