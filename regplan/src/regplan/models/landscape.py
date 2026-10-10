"""Landscape domain models: Application, Interface, Vendor, ScenarioConfig, Landscape."""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Disposition(str, Enum):
    retire = "retire"
    rehost = "rehost"
    replatform = "replatform"
    refactor = "refactor"
    replace = "replace"
    retain = "retain"


class Application(BaseModel):
    id: str
    name: str
    owner: str
    business_value: float = Field(ge=0.0, le=1.0)
    technical_health: float = Field(ge=0.0, le=1.0)
    data_residency: bool = False
    data_classification: str = "public"  # e.g. "PII", "financial", "public"
    ai_enabled: bool = False
    vendor_id: Optional[str] = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    disposition: Optional[Disposition] = None


class Interface(BaseModel):
    id: str
    source_id: str
    target_id: str
    protocol: str
    data_classification: str = "public"


class Vendor(BaseModel):
    id: str
    name: str
    tier: int = Field(ge=1, le=3)  # 1=critical, 2=important, 3=standard


class ScenarioConfig(BaseModel):
    name: str
    capacity_multiplier: float = Field(default=1.0, gt=0.0)
    budget_multiplier: float = Field(default=1.0, gt=0.0)
    scope_filter: Optional[list[str]] = None  # Application id allow-list; None = all
    deadline_extension_days: int = Field(default=0, ge=0)


class Landscape(BaseModel):
    id: str = Field(default="default")
    applications: list[Application]
    interfaces: list[Interface] = Field(default_factory=list)
    vendors: list[Vendor] = Field(default_factory=list)
    scenarios: list[ScenarioConfig] = Field(default_factory=list)
