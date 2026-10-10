"""Work domain models: WorkItem, Wave, Schedule."""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from regplan.models.landscape import Disposition


class WorkItem(BaseModel):
    """A single schedulable unit — either a compliance obligation or a modernisation task."""

    id: str
    application_id: str
    rule_id: Optional[str] = None           # None for modernisation items
    disposition: Optional[Disposition] = None
    duration_quarters: int = Field(ge=1)
    cost_gbp: float = Field(ge=0.0)
    capacity_demand_days: float = Field(ge=0.0)
    benefit_profile: list[float] = Field(default_factory=list)  # quarterly savings post-completion
    predecessors: list[str] = Field(default_factory=list)       # WorkItem ids
    deadline: Optional[date] = None
    source_requirement: str = ""   # traceability: "req-id / assumption-id"


class Wave(BaseModel):
    """A cohort of WorkItems scheduled in the same quarter."""

    quarter: int = Field(ge=0)
    work_item_ids: list[str]


class Schedule(BaseModel):
    """Output of the Optimizer — ordered assignment of WorkItems to quarters."""

    waves: list[Wave]
    work_item_starts: dict[str, int]    # WorkItem id → quarter index (0-based)
    objective_value: float
    solver_wall_time_s: float = 0.0
    seed: int = 42
