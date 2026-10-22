"""Hypothesis property-based tests for regplan algorithmic invariants."""
from __future__ import annotations

from datetime import date

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from regplan.derive.rule_engine import evaluate
from regplan.models.landscape import Application
from regplan.models.regulation import TriggerCondition


# ── Property 1: Trigger Condition Determinism ─────────────────────────────────

_attr_names = st.sampled_from(["ai_enabled", "data_residency", "business_value", "technical_health"])

_leaf_condition = st.builds(
    lambda attr, val: TriggerCondition(attribute=attr, operator="eq", value=val),
    attr=_attr_names,
    val=st.one_of(st.booleans(), st.floats(min_value=0.0, max_value=1.0, allow_nan=False)),
)


def _build_app(ai_enabled: bool, data_residency: bool, bv: float, th: float) -> Application:
    return Application(
        id="APP-PROP",
        name="PropTest",
        owner="test",
        business_value=max(0.0, min(1.0, bv)),
        technical_health=max(0.0, min(1.0, th)),
        ai_enabled=ai_enabled,
        data_residency=data_residency,
        attributes={},
    )


@given(
    ai=st.booleans(),
    dr=st.booleans(),
    bv=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    th=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    attr=_attr_names,
)
@settings(max_examples=200)
def test_property1_trigger_condition_determinism(
    ai: bool, dr: bool, bv: float, th: float, attr: str
) -> None:
    """Property 1: evaluate(cond, app) == evaluate(cond, app) for all valid inputs."""
    app = _build_app(ai, dr, bv, th)
    # Pick a value matching the attribute type
    val_map = {
        "ai_enabled": ai,
        "data_residency": dr,
        "business_value": bv,
        "technical_health": th,
    }
    val = val_map[attr]
    cond = TriggerCondition(attribute=attr, operator="eq", value=val)
    result_1 = evaluate(cond, app)
    result_2 = evaluate(cond, app)
    assert result_1 == result_2


# ── Property 5: Pipeline Result Round-Trip Serialisation ─────────────────────

def test_property5_pipeline_result_round_trip() -> None:
    """Property 5: PipelineResult → JSON → PipelineResult == original."""
    from datetime import datetime, timezone
    from regplan.models.manifest import RunManifest
    from regplan.models.report import PipelineResult

    manifest = RunManifest(
        created_at=datetime.now(tz=timezone.utc),
        regplan_version="0.1.0",
        python_version="3.11",
        git_commit="abc1234",
        git_dirty=False,
        input_file_hashes={},
        installed_packages={},
        scheduler_seed=42,
        simulation_seed=42,
    )
    result = PipelineResult(
        landscape_id="L-TEST",
        scenario_name="base",
        schedule=None,
        infeasibility=None,
        financial=None,
        simulation=None,
        manifest=manifest,
    )
    json_str = result.model_dump_json()
    restored = PipelineResult.model_validate_json(json_str)
    assert restored == result
