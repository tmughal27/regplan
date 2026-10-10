"""Assumptions and disposition-rule models."""
from __future__ import annotations

from datetime import date
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class DistributionSpec(BaseModel):
    """Declares a probability distribution for Monte Carlo sampling."""

    type: Literal["triangular", "lognormal"]
    # Triangular parameters
    low: Optional[float] = None
    mode: Optional[float] = None
    high: Optional[float] = None
    # Lognormal parameters
    mu: Optional[float] = None
    sigma: Optional[float] = None


class DispositionRule(BaseModel):
    """One row in the configurable decision table for Application disposition assignment."""

    # Each field is an optional range test on normalised scores [0.0, 1.0]
    min_business_value: float = Field(default=0.0, ge=0.0, le=1.0)
    max_business_value: float = Field(default=1.0, ge=0.0, le=1.0)
    min_technical_health: float = Field(default=0.0, ge=0.0, le=1.0)
    max_technical_health: float = Field(default=1.0, ge=0.0, le=1.0)
    min_regulatory_exposure: float = Field(default=0.0, ge=0.0, le=1.0)
    max_regulatory_exposure: float = Field(default=1.0, ge=0.0, le=1.0)
    min_vendor_dependence: float = Field(default=0.0, ge=0.0, le=1.0)
    max_vendor_dependence: float = Field(default=1.0, ge=0.0, le=1.0)
    disposition: str   # one of: retire, rehost, replatform, refactor, replace, retain
    rule_id: str = Field(default="default")


class Assumptions(BaseModel):
    """Financial and operational assumptions driving evaluation and simulation."""

    planning_start: date
    horizon_quarters: int = Field(ge=1, le=40)
    discount_rate: float = Field(ge=0.0, le=1.0)
    daily_rate_gbp: float = Field(gt=0.0)
    quarterly_capacity_days: float = Field(gt=0.0)
    cumulative_budget_gbp: float = Field(gt=0.0)
    cost_overrun_dist: DistributionSpec
    duration_slip_dist: DistributionSpec
    benefit_realization_dist: DistributionSpec
    overrun_correlation: float = Field(default=0.3, ge=0.0, le=1.0)
    ramp_up_quarters: int = Field(default=2, ge=0)
    decision_table: list[DispositionRule] = Field(default_factory=list)
    simulation_seed: int = Field(default=42)
