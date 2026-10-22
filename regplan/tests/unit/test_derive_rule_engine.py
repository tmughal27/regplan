"""Unit tests for regplan.derive.rule_engine."""
from __future__ import annotations

import pytest

from regplan.derive.rule_engine import evaluate
from regplan.errors import TriggerEvalError
from regplan.models.landscape import Application
from regplan.models.regulation import TriggerCondition


def _app(**kwargs: object) -> Application:
    defaults: dict[str, object] = {
        "id": "APP-01",
        "name": "Test",
        "owner": "test",
        "business_value": 0.5,
        "technical_health": 0.5,
        "attributes": {},
    }
    defaults.update(kwargs)
    return Application(**defaults)  # type: ignore[arg-type]


def _leaf(attribute: str, operator: str, value: object) -> TriggerCondition:
    return TriggerCondition(attribute=attribute, operator=operator, value=value)


# --- Leaf comparisons ---

def test_eq_true() -> None:
    app = _app(ai_enabled=True)
    cond = _leaf("ai_enabled", "eq", True)
    assert evaluate(cond, app) is True


def test_eq_false() -> None:
    app = _app(ai_enabled=False)
    cond = _leaf("ai_enabled", "eq", True)
    assert evaluate(cond, app) is False


def test_neq() -> None:
    app = _app(data_classification="PII")
    cond = _leaf("data_classification", "neq", "public")
    assert evaluate(cond, app) is True


def test_gt() -> None:
    app = _app(business_value=0.8)
    assert evaluate(_leaf("business_value", "gt", 0.5), app) is True
    assert evaluate(_leaf("business_value", "gt", 0.9), app) is False


def test_gte() -> None:
    app = _app(business_value=0.5)
    assert evaluate(_leaf("business_value", "gte", 0.5), app) is True


def test_lt_lte() -> None:
    app = _app(technical_health=0.3)
    assert evaluate(_leaf("technical_health", "lt", 0.5), app) is True
    assert evaluate(_leaf("technical_health", "lte", 0.3), app) is True


def test_in_operator() -> None:
    app = _app(data_classification="PII")
    cond = _leaf("data_classification", "in", ["PII", "financial"])
    assert evaluate(cond, app) is True


def test_attributes_dict_lookup() -> None:
    app = _app(attributes={"criticality": "high", "uses_ml": True})
    cond = _leaf("criticality", "eq", "high")
    assert evaluate(cond, app) is True


# --- Combinators ---

def test_all_both_true() -> None:
    app = _app(ai_enabled=True, data_residency=True)
    cond = TriggerCondition(all=[
        _leaf("ai_enabled", "eq", True),
        _leaf("data_residency", "eq", True),
    ])
    assert evaluate(cond, app) is True


def test_all_one_false() -> None:
    app = _app(ai_enabled=True, data_residency=False)
    cond = TriggerCondition(all=[
        _leaf("ai_enabled", "eq", True),
        _leaf("data_residency", "eq", True),
    ])
    assert evaluate(cond, app) is False


def test_any_one_true() -> None:
    app = _app(ai_enabled=False, data_residency=True)
    cond = TriggerCondition(any=[
        _leaf("ai_enabled", "eq", True),
        _leaf("data_residency", "eq", True),
    ])
    assert evaluate(cond, app) is True


def test_not_inverts() -> None:
    app = _app(ai_enabled=False)
    cond = TriggerCondition(**{"not": _leaf("ai_enabled", "eq", True)})
    assert evaluate(cond, app) is True


# --- Error handling ---

def test_unknown_attribute_raises() -> None:
    app = _app()
    cond = _leaf("nonexistent_field", "eq", "x")
    with pytest.raises(TriggerEvalError) as exc_info:
        evaluate(cond, app, rule_id="R-TEST")
    assert "nonexistent_field" in str(exc_info.value)
    assert "R-TEST" in str(exc_info.value)


# --- Determinism ---

def test_determinism() -> None:
    app = _app(business_value=0.7, data_residency=True)
    cond = TriggerCondition(all=[
        _leaf("business_value", "gt", 0.5),
        _leaf("data_residency", "eq", True),
    ])
    assert evaluate(cond, app) == evaluate(cond, app)
