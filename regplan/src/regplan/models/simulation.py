"""Simulation domain models: SimulationRun, TornadoEntry, SimulationResult."""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class SimulationRun(BaseModel):
    """Results of one Monte Carlo run."""

    run_index: int = Field(ge=0)
    total_cost: float
    npv: float
    completion_dates: dict[str, date] = Field(default_factory=dict)  # WorkItem id → simulated completion


class TornadoEntry(BaseModel):
    """One row in the tornado sensitivity ranking."""

    assumption_name: str
    npv_variance_contribution: float


class SimulationResult(BaseModel):
    """Aggregate output of the Monte Carlo Simulator."""

    runs: list[SimulationRun]
    p50_cost: float
    p80_cost: float
    p95_cost: float
    p50_npv: float
    p80_npv: float
    p95_npv: float
    deadline_miss_probabilities: dict[str, float] = Field(default_factory=dict)  # rule_id → probability
    tornado: list[TornadoEntry] = Field(default_factory=list)
    seed: int = 42
