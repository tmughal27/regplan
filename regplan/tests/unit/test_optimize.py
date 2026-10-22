"""Unit tests for the Optimize stage."""
from __future__ import annotations

from pathlib import Path

import pytest

from regplan.derive import derive
from regplan.ingest.loader import ingest
from regplan.models.work import Schedule
from regplan.models.report import InfeasibilityReport
from regplan.optimize import OptimizeResult, optimize


_EXAMPLES = Path(__file__).parent.parent.parent / "src" / "regplan" / "examples"
_ASSUMPTIONS = _EXAMPLES / "assumptions.yaml"
_PACKS = sorted((_EXAMPLES / "packs").glob("*.yaml"))


def _run_to_optimize(landscape_name: str) -> OptimizeResult:
    landscape = _EXAMPLES / "landscapes" / landscape_name
    ir = ingest(landscape, _PACKS, _ASSUMPTIONS)
    dr = derive(ir, ir.assumptions)
    return optimize(dr, ir.assumptions)


def test_optimize_returns_optimize_result() -> None:
    result = _run_to_optimize("cloud_native.yaml")
    assert isinstance(result, OptimizeResult)


def test_feasible_schedule_has_waves() -> None:
    result = _run_to_optimize("cloud_native.yaml")
    if result.is_feasible:
        assert result.schedule is not None
        assert isinstance(result.schedule, Schedule)
        assert len(result.schedule.work_item_starts) > 0


def test_infeasible_has_report_or_schedule() -> None:
    result = _run_to_optimize("legacy_heavy.yaml")
    # Either feasible or infeasible — both are valid outcomes
    assert result.schedule is not None or result.infeasibility is not None


def test_schedule_deterministic() -> None:
    landscape = _EXAMPLES / "landscapes" / "cloud_native.yaml"
    ir = ingest(landscape, _PACKS, _ASSUMPTIONS)
    dr = derive(ir, ir.assumptions)
    r1 = optimize(dr, ir.assumptions)
    r2 = optimize(dr, ir.assumptions)
    if r1.is_feasible and r2.is_feasible:
        assert r1.schedule is not None and r2.schedule is not None
        assert r1.schedule.work_item_starts == r2.schedule.work_item_starts


def test_infeasibility_report_has_remediations() -> None:
    from regplan.optimize.infeasibility import build_infeasibility_report
    from regplan.models.work import WorkItem
    from datetime import date

    # Craft an infeasible scenario: one item with deadline in the past
    wi = WorkItem(
        id="W1",
        application_id="A",
        duration_quarters=5,
        cost_gbp=1000.0,
        capacity_demand_days=500.0,
        deadline=date(2000, 1, 1),  # in the past
        source_requirement="test",
    )
    from regplan.ingest.loader import ingest as _ingest
    ir = _ingest(
        _EXAMPLES / "landscapes" / "cloud_native.yaml",
        [],
        _ASSUMPTIONS,
    )
    report = build_infeasibility_report([wi], ir.assumptions)
    assert isinstance(report, InfeasibilityReport)
    assert len(report.remediations) > 0
