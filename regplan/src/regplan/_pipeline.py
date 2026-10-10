"""Placeholder pipeline stage functions — replaced by real implementations incrementally."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from regplan.ingest.loader import IngestResult
from regplan.ingest.loader import ingest as _ingest


def ingest(landscape_path: Path, packs_paths: list[Path], assumptions_path: Path) -> IngestResult:
    """Load and schema-validate all YAML inputs."""
    return _ingest(landscape_path, packs_paths, assumptions_path)


def derive(ingest_result: Any, assumptions: Any) -> Any:
    raise NotImplementedError("derive stage not yet implemented")


def optimize(derive_result: Any, assumptions: Any) -> Any:
    raise NotImplementedError("optimize stage not yet implemented")


def evaluate(schedule: Any, derive_result: Any, assumptions: Any) -> Any:
    raise NotImplementedError("evaluate stage not yet implemented")


def simulate(
    schedule: Any, financial_result: Any, assumptions: Any, n_runs: int, seed: int
) -> Any:
    raise NotImplementedError("simulate stage not yet implemented")


def report(pipeline_result: Any, out_dir: Path) -> None:
    raise NotImplementedError("report stage not yet implemented")
