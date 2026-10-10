"""Financial domain models: CashFlow, FinancialResult."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CashFlow(BaseModel):
    """Quarterly cash flow breakdown."""

    quarter: int = Field(ge=0)
    capex: float = 0.0
    opex: float = 0.0
    run_cost_savings: float = 0.0
    migration_cost: float = 0.0
    net: float = 0.0


class FinancialResult(BaseModel):
    """Output of the Finance Engine."""

    cash_flows: list[CashFlow]
    tco: float
    npv: float
    payback_quarter: Optional[int] = None  # None if never achieved
    cost_of_delay: dict[str, float] = Field(default_factory=dict)  # WorkItem id → £/quarter
    assumption_ids: list[str] = Field(default_factory=list)         # traceability
