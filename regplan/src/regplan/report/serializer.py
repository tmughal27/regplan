"""Pipeline result serialiser and deserialiser."""
from __future__ import annotations

import json
from pathlib import Path

from regplan.models.report import PipelineResult


def serialise(result: PipelineResult, out_dir: Path) -> Path:
    """Serialise PipelineResult to result.json in *out_dir*. Returns the path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "result.json"
    out_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return out_path


def deserialise(result_path: Path) -> PipelineResult:
    """Load a PipelineResult from a previously serialised result.json."""
    raw = result_path.read_text(encoding="utf-8")
    return PipelineResult.model_validate_json(raw)
