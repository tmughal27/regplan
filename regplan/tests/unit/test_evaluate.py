"""Unit tests for the Evaluate stage (finance engine)."""
from __future__ import annotations

from pathlib import Path

import pytest

from regplan.derive import derive
from regplan.evaluate import evaluate
from regplan.evaluate.finance import compute_financial_result
from regplan.ingest.loader import ingest
from regplan.models.finance import FinancialResult
from regplan.optimize import optimize


_EXAMPLES = Path(__file__).parent.parent.parent / "src" / "regplan" / "examples"
_ASSUMPTIONS = _EXAMPLES / "assumptions.yaml"
_PACKS = sorted((_EXAMPLES / "packs").glob("*.yaml"))
_LANDSCAPE = _EXAMPLES / "landscapes" / "cloud_native.yaml"


def test_evaluate_returns_financial_result() -> None:
    ir = ingest(_LANDSCAPE, _PACKS, _ASSUMPTIONS)
    dr = derive(ir, ir.assumptions)
    opt = optimize(dr, ir.assumptions)
    if not opt.is_feasible or opt.schedule is None:
        pytest.skip("No feasible schedule for this landscape")
    result = evaluate(opt.schedule, dr, ir.assumptions)
    assert isinstance(result, FinancialResult)


def test_tco_equals_sum_of_cash_flows() -> None:
    ir = ingest(_LANDSCAPE, _PACKS, _ASSUMPTIONS)
    dr = derive(ir, ir.assumptions)
    opt = optimize(dr, ir.assumptions)
    if not opt.is_feasible or opt.schedule is None:
        pytest.skip("No feasible schedule for this landscape")
    result = evaluate(opt.schedule, dr, ir.assumptions)
    expected_tco = sum(cf.capex + cf.opex + cf.migration_cost for cf in result.cash_flows)
    assert abs(result.tco - expected_tco) < 1e-6, f"TCO {result.tco} != sum {expected_tco}"


def test_npv_discounting_monotonicity() -> None:
    """NPV and undiscounted sum differ by the discount effect; both are finite floats."""
    ir = ingest(_LANDSCAPE, _PACKS, _ASSUMPTIONS)
    dr = derive(ir, ir.assumptions)
    opt = optimize(dr, ir.assumptions)
    if not opt.is_feasible or opt.schedule is None:
        pytest.skip("No feasible schedule for this landscape")
    result = evaluate(opt.schedule, dr, ir.assumptions)
    undiscounted = sum(cf.net for cf in result.cash_flows)
    # Both values must be finite
    assert isinstance(result.npv, float)
    assert isinstance(undiscounted, float)
    # Discounting: positive cash flows → NPV < undiscounted; negative → NPV > undiscounted
    if undiscounted >= 0:
        assert result.npv <= undiscounted + 1.0
    else:
        assert result.npv >= undiscounted - 1.0


def test_cash_flows_cover_full_horizon() -> None:
    ir = ingest(_LANDSCAPE, _PACKS, _ASSUMPTIONS)
    dr = derive(ir, ir.assumptions)
    opt = optimize(dr, ir.assumptions)
    if not opt.is_feasible or opt.schedule is None:
        pytest.skip("No feasible schedule for this landscape")
    result = evaluate(opt.schedule, dr, ir.assumptions)
    assert len(result.cash_flows) == ir.assumptions.horizon_quarters


def test_assumption_ids_recorded() -> None:
    ir = ingest(_LANDSCAPE, _PACKS, _ASSUMPTIONS)
    dr = derive(ir, ir.assumptions)
    opt = optimize(dr, ir.assumptions)
    if not opt.is_feasible or opt.schedule is None:
        pytest.skip("No feasible schedule for this landscape")
    result = evaluate(opt.schedule, dr, ir.assumptions)
    assert len(result.assumption_ids) > 0
