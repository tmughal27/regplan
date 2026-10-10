"""Regulation domain models: TriggerCondition, RegulationRule, RegulationPack."""
from __future__ import annotations

from datetime import date
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, model_validator


class TriggerCondition(BaseModel):
    """Recursive declarative trigger condition tree node.

    A leaf node has `attribute`, `operator`, and `value` set.
    A combinator node has `all`, `any`, or `not_` set (mutually exclusive).
    """

    # Combinators
    all: Optional[list[TriggerCondition]] = None
    any: Optional[list[TriggerCondition]] = None
    not_: Optional[TriggerCondition] = Field(None, alias="not")

    # Leaf comparison fields
    attribute: Optional[str] = None
    operator: Optional[Literal["eq", "neq", "gt", "gte", "lt", "lte", "in"]] = None
    value: Optional[Any] = None

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def validate_structure(self) -> TriggerCondition:
        combinators = [x for x in (self.all, self.any, self.not_) if x is not None]
        is_combinator = len(combinators) > 0
        is_leaf = self.attribute is not None

        if is_combinator and is_leaf:
            raise ValueError("TriggerCondition cannot be both a combinator and a leaf node")
        if not is_combinator and not is_leaf:
            raise ValueError(
                "TriggerCondition must be either a combinator (all/any/not) or a leaf "
                "(attribute + operator + value)"
            )
        if is_leaf and (self.operator is None or self.value is None):
            raise ValueError("Leaf TriggerCondition requires both 'operator' and 'value'")
        return self


class RegulationRule(BaseModel):
    id: str
    regulation: str
    title: str
    trigger: TriggerCondition
    deadline: date
    effort_person_days: float = Field(gt=0.0)
    source_url: HttpUrl
    last_verified: date


class RegulationPack(BaseModel):
    regulation: str
    version: str
    rules: list[RegulationRule]


TriggerCondition.model_rebuild()
