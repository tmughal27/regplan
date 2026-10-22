"""Unit tests for the Simulate stage."""
from __future__ import annotations

from pathlib import Path

import pytest

from regplan.derive import derive
from regplan.evaluate import evaluate
from regplan.ingest.loader import ingest
from regplan.models.simulation import SimulationResult
from regplan.optimize import optimize
from regplan.simulate import simulate


_EXAMPLES = Path(__file__).parent.parent.parent / "src" / "regplan" / "examples"
_ASSUMPTIONS = _EXAMPLES / "assumptions.yaml"
_PACKS = sorted((_EXAMPLES / "packs").glob("*.yaml"))
_LANDSCAPE = _EXAMPLES / "landscapes" / "cloud_native.yaml"


def _setup() -> tuple:
    ir = ingest(_LANDSCAPE, _PACKS, _ASSUMPTIONS)
    dr = derive(ir, ir.assumptions)
    opt = optimize(dr, ir.assumptions)
    if not opt.is_feasible or opt.schedule is None:
        return None, None, None, None
    fin = evaluate(opt.schedule, dr, ir.assumptions)
    return ir, dr, opt, fin


def test_simulate_returns_simulation_result() -> None:
    ir, dr, opt, fin = _setup()
    if ir is None:
        pytest.skip("No feasible schedule")
    result = simulate(opt.schedule, fin, ir.assumptions, 50, 42, work_items=dr.work_items)
    assert isinstance(result, SimulationResult)


def test_simulate_percentiles_ordered() -> None:
    ir, dr, opt, fin = _setup()
    if ir is None:
        pytest.skip("No feasible schedule")
    result = simulate(opt.schedule, fin, ir.assumptions, 100, 42, work_items=dr.work_items)
    assert result.p50_cost <= result.p80_cost <= result.p95_cost
    assert result.p50_npv <= result.p80_npv <= result.p95_npv


def test_simulate_seed_deterministic() -> None:
    ir, dr, opt, fin = _setup()
    if ir is None:
        pytest.skip("No feasible schedule")
    r1 = simulate(opt.schedule, fin, ir.assumptions, 50, 42, work_items=dr.work_items)
    r2 = simulate(opt.schedule, fin, ir.assumptions, 50, 42, work_items=dr.work_items)
    assert r1.p50_cost == r2.p50_cost
    assert r1.p50_npv == r2.p50_npv


def test_simulate_run_count_matches() -> None:
    ir, dr, opt, fin = _setup()
    if ir is None:
        pytest.skip("No feasible schedule")
    n = 30
    result = simulate(opt.schedule, fin, ir.assumptions, n, 0, work_items=dr.work_items)
    assert len(result.runs) == n


def test_simulate_seed_stored() -> None:
    ir, dr, opt, fin = _setup()
    if ir is None:
        pytest.skip("No feasible schedule")
    result = simulate(opt.schedule, fin, ir.assumptions, 10, 99, work_items=dr.work_items)
    assert result.seed == 99
