"""Pipeline stage functions — public API wrappers."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from regplan.ingest.loader import IngestResult
from regplan.ingest.loader import ingest as _ingest


def ingest(landscape_path: Path, packs_paths: list[Path], assumptions_path: Path) -> IngestResult:
    """Load and schema-validate all YAML inputs."""
    return _ingest(landscape_path, packs_paths, assumptions_path)


def derive(ingest_result: Any, assumptions: Any) -> Any:
    """Run the Derive stage: score applications, match obligations, build graphs."""
    from regplan.derive import derive as _derive
    return _derive(ingest_result, assumptions)


def optimize(derive_result: Any, assumptions: Any) -> Any:
    """Run the Optimize stage: produce a Schedule or InfeasibilityReport."""
    from regplan.optimize import optimize as _optimize
    return _optimize(derive_result, assumptions)


def evaluate(schedule: Any, derive_result: Any, assumptions: Any) -> Any:
    """Run the Evaluate stage: compute TCO, NPV, payback, and cost-of-delay."""
    from regplan.evaluate import evaluate as _evaluate
    return _evaluate(schedule, derive_result, assumptions)


def simulate(
    schedule: Any, financial_result: Any, assumptions: Any, n_runs: int, seed: int
) -> Any:
    """Run the Simulate stage: Monte Carlo simulation."""
    from regplan.simulate import simulate as _simulate
    return _simulate(schedule, financial_result, assumptions, n_runs, seed)


def report(pipeline_result: Any, out_dir: Path) -> None:
    """Run the Report stage: serialise JSON, render memo, generate charts."""
    from regplan.report import report as _report
    _report(pipeline_result, out_dir)
