"""Unit tests for landscape models."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from regplan.models.landscape import (
    Application,
    Disposition,
    Interface,
    Landscape,
    ScenarioConfig,
    Vendor,
)


def test_application_valid() -> None:
    app = Application(id="APP-01", name="CRM", owner="sales", business_value=0.8, technical_health=0.5)
    assert app.id == "APP-01"
    assert app.disposition is None


def test_application_business_value_out_of_range() -> None:
    with pytest.raises(ValidationError):
        Application(id="APP-01", name="X", owner="y", business_value=1.5, technical_health=0.5)


def test_disposition_enum() -> None:
    assert Disposition.retire == "retire"
    assert Disposition("rehost") == Disposition.rehost


def test_vendor_tier_range() -> None:
    v = Vendor(id="V-01", name="Acme", tier=1)
    assert v.tier == 1
    with pytest.raises(ValidationError):
        Vendor(id="V-02", name="Bad", tier=4)


def test_landscape_empty_interfaces() -> None:
    app = Application(id="APP-01", name="CRM", owner="sales", business_value=0.5, technical_health=0.5)
    landscape = Landscape(applications=[app])
    assert landscape.interfaces == []


def test_scenario_config_defaults() -> None:
    sc = ScenarioConfig(name="progressive")
    assert sc.capacity_multiplier == 1.0
    assert sc.deadline_extension_days == 0
