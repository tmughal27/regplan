"""Unit tests for regplan.errors."""
from regplan.errors import (
    RegplanError,
    IngestError,
    SemanticError,
    TriggerEvalError,
    MissingAssumptionError,
)


def test_ingest_error_is_regplan_error() -> None:
    err = IngestError("landscape.yaml", "applications[0].id", "field required")
    assert isinstance(err, RegplanError)
    assert "landscape.yaml" in str(err)


def test_semantic_error_message() -> None:
    err = SemanticError("APP-01", "interface_ref", "target APP-99 does not exist")
    assert "APP-01" in str(err)
    assert err.suggestion == "target APP-99 does not exist"


def test_trigger_eval_error() -> None:
    err = TriggerEvalError("R-GDPR-01", "processes_pii")
    assert err.rule_id == "R-GDPR-01"
    assert "processes_pii" in str(err)


def test_missing_assumption_error() -> None:
    err = MissingAssumptionError("discount_rate")
    assert "discount_rate" in str(err)
