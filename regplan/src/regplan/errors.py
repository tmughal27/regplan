"""regplan custom exception hierarchy."""
from __future__ import annotations


class RegplanError(Exception):
    """Base exception for all regplan errors."""


class IngestError(RegplanError):
    """Raised when YAML loading or schema validation fails."""

    def __init__(self, file_path: str, field_path: str, message: str) -> None:
        self.file_path = file_path
        self.field_path = field_path
        super().__init__(f"{file_path} [{field_path}]: {message}")


class SemanticError(RegplanError):
    """Raised when semantic validation fails."""

    def __init__(self, entity_id: str, rule_name: str, suggestion: str) -> None:
        self.entity_id = entity_id
        self.rule_name = rule_name
        self.suggestion = suggestion
        super().__init__(f"Semantic error on '{entity_id}' ({rule_name}): {suggestion}")


class TriggerEvalError(RegplanError):
    """Raised when a trigger condition references an unknown Application attribute."""

    def __init__(self, rule_id: str, attribute_name: str) -> None:
        self.rule_id = rule_id
        self.attribute_name = attribute_name
        super().__init__(f"Rule '{rule_id}' references unknown attribute '{attribute_name}'")


class MissingAssumptionError(RegplanError):
    """Raised when a required Assumptions value is missing."""

    def __init__(self, assumption_name: str) -> None:
        self.assumption_name = assumption_name
        super().__init__(f"Missing required assumption: '{assumption_name}'")
