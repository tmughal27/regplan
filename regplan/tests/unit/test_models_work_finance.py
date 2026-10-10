"""Unit tests for work, finance, simulation, manifest, and report models."""
from __future__ import annotations

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from regplan.models.work import Schedule, Wave, WorkItem
from regplan.models.finance import CashFlow, FinancialResult
from regplan.models.simulation import SimulationResult, TornadoEntry
from regplan.models.manifest import RunManifest
from regplan.models.report import InfeasibilityReport, PipelineResult


def _make_work_item(item_id: str = "WI-01") -> WorkItem:
    return WorkItem(
        id=item_id,
        application_id="APP-01",
        duration_quarters=2,
        cost_gbp=50_000.0,
        capacity_demand_days=40.0,
    )


def test_work_item_defaults() -> None:
    wi = _make_work_item()
    assert wi.predecessors == []
    assert wi.deadline is None
    assert wi.rule_id is None


def test_work_item_negative_duration_invalid() -> None:
    with pytest.raises(ValidationError):
        WorkItem(id="WI-01", application_id="APP-01", duration_quarters=0,
                 cost_gbp=1000.0, capacity_demand_days=10.0)


def test_schedule_wave_round_trip() -> None:
    wi = _make_work_item()
    wave = Wave(quarter=0, work_item_ids=[wi.id])
    schedule = Schedule(
        waves=[wave],
        work_item_starts={wi.id: 0},
        objective_value=1000.0,
    )
    assert schedule.work_item_starts["WI-01"] == 0


def test_cash_flow_defaults() -> None:
    cf = CashFlow(quarter=0)
    assert cf.net == 0.0


def test_financial_result_no_payback() -> None:
    cf = CashFlow(quarter=0, capex=100_000.0, net=-100_000.0)
    fr = FinancialResult(cash_flows=[cf], tco=100_000.0, npv=-95_000.0)
    assert fr.payback_quarter is None


def test_simulation_result_tornado() -> None:
    entry = TornadoEntry(assumption_name="cost_overrun_dist", npv_variance_contribution=45000.0)
    result = SimulationResult(
        runs=[], p50_cost=1e6, p80_cost=1.1e6, p95_cost=1.2e6,
        p50_npv=200_000.0, p80_npv=150_000.0, p95_npv=100_000.0,
        tornado=[entry],
    )
    assert result.tornado[0].assumption_name == "cost_overrun_dist"


def test_run_manifest_fields() -> None:
    rm = RunManifest(
        created_at=datetime(2026, 1, 1),
        regplan_version="0.1.0",
        python_version="3.11.0",
    )
    assert rm.git_dirty is False
    assert rm.git_commit is None


def test_pipeline_result_json_round_trip() -> None:
    rm = RunManifest(
        created_at=datetime(2026, 1, 1),
        regplan_version="0.1.0",
        python_version="3.11.0",
    )
    pr = PipelineResult(landscape_id="L-01", manifest=rm)
    json_str = pr.model_dump_json()
    pr2 = PipelineResult.model_validate_json(json_str)
    assert pr2.landscape_id == "L-01"
    assert pr2.manifest.regplan_version == "0.1.0"


def test_infeasibility_report_defaults() -> None:
    report = InfeasibilityReport(remediations=["extend capacity"])
    assert report.conflicting_work_item_ids == []
    assert len(report.remediations) == 1
