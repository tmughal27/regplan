"""Optimize stage: CP-SAT scheduler and infeasibility reporting."""
from __future__ import annotations

from dataclasses import dataclass

from regplan.derive import DeriveResult
from regplan.models.assumptions import Assumptions
from regplan.models.report import InfeasibilityReport
from regplan.models.work import Schedule
from regplan.optimize.infeasibility import build_infeasibility_report
from regplan.optimize.scheduler import schedule as _schedule


@dataclass
class OptimizeResult:
    """Typed output of the Optimize stage."""
    schedule: Schedule | None
    infeasibility: InfeasibilityReport | None

    @property
    def is_feasible(self) -> bool:
        return self.schedule is not None


def optimize(derive_result: DeriveResult, assumptions: Assumptions) -> OptimizeResult:
    """Run the CP-SAT scheduler. Returns a Schedule or an InfeasibilityReport."""
    sched = _schedule(derive_result.work_items, assumptions)
    if sched is None:
        report = build_infeasibility_report(derive_result.work_items, assumptions)
        return OptimizeResult(schedule=None, infeasibility=report)
    return OptimizeResult(schedule=sched, infeasibility=None)
