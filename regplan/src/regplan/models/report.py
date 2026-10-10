"""Pipeline result models: InfeasibilityReport, PipelineResult."""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from regplan.models.work import Schedule
from regplan.models.finance import FinancialResult
from regplan.models.simulation import SimulationResult
from regplan.models.manifest import RunManifest


class InfeasibilityReport(BaseModel):
    """Explanation produced when no feasible schedule exists."""

    conflicting_work_item_ids: list[str] = Field(default_factory=list)
    conflicting_deadline_dates: list[date] = Field(default_factory=list)
    conflicting_capacity_limits: list[tuple[int, float]] = Field(default_factory=list)
    conflicting_budget_limits: list[tuple[int, float]] = Field(default_factory=list)
    remediations: list[str] = Field(default_factory=list)


class PipelineResult(BaseModel):
    """Complete output of one regplan pipeline run."""

    landscape_id: str
    scenario_name: str = "base"
    schedule: Optional[Schedule] = None
    infeasibility: Optional[InfeasibilityReport] = None
    financial: Optional[FinancialResult] = None
    simulation: Optional[SimulationResult] = None
    manifest: RunManifest
