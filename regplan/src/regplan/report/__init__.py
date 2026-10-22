"""Report stage: serialiser, memo renderer, and chart generators."""
from __future__ import annotations

from pathlib import Path

from regplan.models.report import PipelineResult
from regplan.report.charts import generate_all_charts
from regplan.report.renderer import render_memo
from regplan.report.serializer import serialise


def report(pipeline_result: PipelineResult, out_dir: Path) -> None:
    """Serialise result to JSON, render memo, and generate all charts."""
    result_path = serialise(pipeline_result, out_dir)
    render_memo(result_path, out_dir / "memo.md")
    generate_all_charts(pipeline_result, out_dir)
