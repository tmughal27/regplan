"""Unit tests for regulation and assumption models."""
from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from regplan.models.regulation import RegulationPack, RegulationRule, TriggerCondition
from regplan.models.assumptions import Assumptions, DistributionSpec, DispositionRule


# ── TriggerCondition ──────────────────────────────────────────────────────────

def test_trigger_condition_leaf_valid() -> None:
    tc = TriggerCondition(attribute="ai_enabled", operator="eq", value=True)
    assert tc.attribute == "ai_enabled"
    assert tc.operator == "eq"


def test_trigger_condition_all_combinator() -> None:
    leaf = TriggerCondition(attribute="ai_enabled", operator="eq", value=True)
    combined = TriggerCondition(all=[leaf])
    assert combined.all is not None
    assert len(combined.all) == 1


def test_trigger_condition_not_alias() -> None:
    leaf = TriggerCondition(attribute="data_residency", operator="eq", value=False)
    negated = TriggerCondition.model_validate({"not": leaf.model_dump()})
    assert negated.not_ is not None


def test_trigger_condition_empty_raises() -> None:
    with pytest.raises(ValidationError):
        TriggerCondition()


def test_trigger_condition_leaf_missing_operator_raises() -> None:
    with pytest.raises(ValidationError):
        TriggerCondition(attribute="ai_enabled", value=True)


# ── RegulationRule ────────────────────────────────────────────────────────────

def _make_rule(deadline: date = date(2027, 1, 1)) -> RegulationRule:
    return RegulationRule(
        id="R-GDPR-01",
        regulation="GDPR",
        title="DPO appointment",
        trigger=TriggerCondition(attribute="data_residency", operator="eq", value=True),
        deadline=deadline,
        effort_person_days=10.0,
        source_url="https://gdpr-info.eu/art-37-gdpr/",  # type: ignore[arg-type]
        last_verified=date(2024, 1, 1),
    )


def test_regulation_rule_valid() -> None:
    rule = _make_rule()
    assert rule.id == "R-GDPR-01"


# ── Assumptions ───────────────────────────────────────────────────────────────

def _make_dist() -> DistributionSpec:
    return DistributionSpec(type="triangular", low=0.8, mode=1.0, high=1.3)


def test_assumptions_valid() -> None:
    a = Assumptions(
        planning_start=date(2025, 1, 1),
        horizon_quarters=12,
        discount_rate=0.08,
        daily_rate_gbp=700.0,
        quarterly_capacity_days=120.0,
        cumulative_budget_gbp=5_000_000.0,
        cost_overrun_dist=_make_dist(),
        duration_slip_dist=_make_dist(),
        benefit_realization_dist=_make_dist(),
    )
    assert a.simulation_seed == 42
    assert a.ramp_up_quarters == 2


def test_assumptions_negative_discount_rate_invalid() -> None:
    with pytest.raises(ValidationError):
        Assumptions(
            planning_start=date(2025, 1, 1),
            horizon_quarters=12,
            discount_rate=-0.01,
            daily_rate_gbp=700.0,
            quarterly_capacity_days=120.0,
            cumulative_budget_gbp=5_000_000.0,
            cost_overrun_dist=_make_dist(),
            duration_slip_dist=_make_dist(),
            benefit_realization_dist=_make_dist(),
        )
