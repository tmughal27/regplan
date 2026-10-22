"""Golden-file regression tests for known-good pipeline outputs."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

_GOLDEN_DIR = Path(__file__).parent
_EXAMPLES = Path(__file__).parent.parent.parent / "src" / "regplan" / "examples"
_ASSUMPTIONS = _EXAMPLES / "assumptions.yaml"
_PACKS = sorted((_EXAMPLES / "packs").glob("*.yaml"))


def _run_pipeline(landscape_path: Path) -> dict:
    from regplan.derive import derive
    from regplan.evaluate import evaluate
    from regplan.ingest.loader import ingest
    from regplan.manifest.builder import build_manifest
    from regplan.models.report import PipelineResult
    from regplan.optimize import optimize

    ir = ingest(landscape_path, _PACKS, _ASSUMPTIONS)
    dr = derive(ir, ir.assumptions)
    opt = optimize(dr, ir.assumptions)
    manifest = build_manifest(
        [landscape_path, _ASSUMPTIONS] + list(_PACKS),
        scheduler_seed=42,
        simulation_seed=42,
    )

    if opt.is_feasible and opt.schedule is not None:
        fin = evaluate(opt.schedule, dr, ir.assumptions)
        result = PipelineResult(
            landscape_id=ir.landscape.id,
            scenario_name="base",
            schedule=opt.schedule,
            infeasibility=None,
            financial=fin,
            simulation=None,
            manifest=manifest,
        )
    else:
        result = PipelineResult(
            landscape_id=ir.landscape.id,
            scenario_name="base",
            schedule=None,
            infeasibility=opt.infeasibility,
            financial=None,
            simulation=None,
            manifest=manifest,
        )
    return json.loads(result.model_dump_json())


def _stable_result(d: dict) -> dict:
    """Remove non-deterministic fields (timestamps, git hash) for comparison."""
    if "manifest" in d:
        d["manifest"] = {
            k: v for k, v in d["manifest"].items()
            if k not in ("created_at", "git_commit", "git_dirty",
                         "input_file_hashes", "installed_packages", "python_version")
        }
    if "schedule" in d and d["schedule"]:
        d["schedule"].pop("solver_wall_time_s", None)
    return d


@pytest.mark.parametrize("landscape_name,golden_file", [
    ("legacy_heavy.yaml", "legacy_heavy_expected.json"),
    ("cloud_native.yaml", "cloud_native_expected.json"),
])
def test_golden_pipeline_output(landscape_name: str, golden_file: str) -> None:
    """Re-run the pipeline and compare against stored golden output."""
    golden_path = _GOLDEN_DIR / golden_file
    landscape_path = _EXAMPLES / "landscapes" / landscape_name

    if not golden_path.exists():
        # Generate golden file on first run
        result = _run_pipeline(landscape_path)
        golden_path.write_text(json.dumps(_stable_result(result), indent=2), encoding="utf-8")
        pytest.skip(f"Golden file {golden_file} generated; re-run to validate.")

    actual = _stable_result(_run_pipeline(landscape_path))
    expected = json.loads(golden_path.read_text(encoding="utf-8"))
    assert actual == expected, (
        f"Pipeline output changed for {landscape_name}. "
        f"If intentional, delete {golden_file} to regenerate."
    )
