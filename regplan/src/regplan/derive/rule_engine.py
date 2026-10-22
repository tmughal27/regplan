"""Declarative trigger-condition interpreter — no eval/exec."""
from __future__ import annotations

from typing import Any

from regplan.errors import TriggerEvalError
from regplan.models.landscape import Application
from regplan.models.regulation import TriggerCondition


def _get_attribute(app: Application, attribute: str, rule_id: str) -> Any:
    if attribute in Application.model_fields:
        return getattr(app, attribute)
    if attribute in app.attributes:
        return app.attributes[attribute]
    raise TriggerEvalError(rule_id=rule_id, attribute_name=attribute)


def _apply_operator(operator: str, actual: Any, expected: Any) -> bool:
    if operator == "eq":
        return bool(actual == expected)
    if operator == "neq":
        return bool(actual != expected)
    if operator == "gt":
        return bool(actual > expected)
    if operator == "gte":
        return bool(actual >= expected)
    if operator == "lt":
        return bool(actual < expected)
    if operator == "lte":
        return bool(actual <= expected)
    if operator == "in":
        return bool(actual in expected)
    raise ValueError(f"Unknown operator: {operator!r}")


def evaluate(condition: TriggerCondition, app: Application, rule_id: str = "") -> bool:
    """Recursively evaluate a TriggerCondition against an Application.

    Raises TriggerEvalError when a referenced attribute does not exist on the
    Application model fields or attributes dict.
    """
    if condition.all is not None:
        return all(evaluate(c, app, rule_id) for c in condition.all)
    if condition.any is not None:
        return any(evaluate(c, app, rule_id) for c in condition.any)
    if condition.not_ is not None:
        return not evaluate(condition.not_, app, rule_id)
    # Leaf comparison
    actual = _get_attribute(app, condition.attribute, rule_id)  # type: ignore[arg-type]
    return _apply_operator(condition.operator, actual, condition.value)  # type: ignore[arg-type]
