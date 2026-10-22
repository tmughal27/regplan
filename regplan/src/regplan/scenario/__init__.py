"""Scenario stage: built-in scenarios and comparison engine."""
from regplan.scenario.engine import (
    BUILTIN_SCENARIOS,
    BIG_BANG,
    PROGRESSIVE,
    MINIMUM_COMPLIANCE,
    apply_scenario,
    compare_scenarios,
    ComparisonReport,
    TransformedInputs,
)

__all__ = [
    "BUILTIN_SCENARIOS",
    "BIG_BANG",
    "PROGRESSIVE",
    "MINIMUM_COMPLIANCE",
    "apply_scenario",
    "compare_scenarios",
    "ComparisonReport",
    "TransformedInputs",
]
