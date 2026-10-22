"""Scenario engine: transformations and scenario comparison."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from regplan.models.assumptions import Assumptions
from regplan.models.landscape import Landscape, ScenarioConfig
from regplan.models.finance import FinancialResult
from regplan.models.simulation import SimulationResult
from regplan.models.work import Schedule


# Built-in scenario configs
BIG_BANG = ScenarioConfig(
    name="big_bang",
    capacity_multiplier=2.0,
    budget_multiplier=2.0,
    scope_filter=None,
    deadline_extension_days=0,
)

PROGRESSIVE = ScenarioConfig(
    name="progressive",
    capacity_multiplier=1.0,
    budget_multiplier=1.0,
    scope_filter=None,
    deadline_extension_days=90,
)

MINIMUM_COMPLIANCE = ScenarioConfig(
    name="minimum_compliance",
    capacity_multiplier=0.6,
    budget_multiplier=0.5,
    scope_filter=None,
    deadline_extension_days=0,
)

BUILTIN_SCENARIOS: dict[str, ScenarioConfig] = {
    "big_bang": BIG_BANG,
    "progressive": PROGRESSIVE,
    "minimum_compliance": MINIMUM_COMPLIANCE,
}


@dataclass
class TransformedInputs:
    landscape: Landscape
    assumptions: Assumptions
    scenario_name: str


@dataclass
class ComparisonReport:
    scenario_a: str
    scenario_b: str
    tco_a: float
    tco_b: float
    npv_a: float
    npv_b: float
    payback_a: int | None
    payback_b: int | None
    deadline_miss_prob_a: dict[str, float]
    deadline_miss_prob_b: dict[str, float]
    wave_plan_a: list[dict[str, object]]
    wave_plan_b: list[dict[str, object]]


def apply_scenario(
    landscape: Landscape,
    assumptions: Assumptions,
    scenario_config: ScenarioConfig,
) -> TransformedInputs:
    """Apply a ScenarioConfig transformation to base inputs."""
    # Transform assumptions
    from copy import deepcopy
    new_assumptions = Assumptions(
        planning_start=assumptions.planning_start,
        horizon_quarters=assumptions.horizon_quarters,
        discount_rate=assumptions.discount_rate,
        daily_rate_gbp=assumptions.daily_rate_gbp,
        quarterly_capacity_days=assumptions.quarterly_capacity_days * scenario_config.capacity_multiplier,
        cumulative_budget_gbp=assumptions.cumulative_budget_gbp * scenario_config.budget_multiplier,
        cost_overrun_dist=assumptions.cost_overrun_dist,
        duration_slip_dist=assumptions.duration_slip_dist,
        benefit_realization_dist=assumptions.benefit_realization_dist,
        overrun_correlation=assumptions.overrun_correlation,
        ramp_up_quarters=assumptions.ramp_up_quarters,
        decision_table=assumptions.decision_table,
        simulation_seed=assumptions.simulation_seed,
    )

    # Filter landscape applications if scope_filter is set
    if scenario_config.scope_filter:
        allowed = set(scenario_config.scope_filter)
        filtered_apps = [a for a in landscape.applications if a.id in allowed]
        filtered_interfaces = [
            i for i in landscape.interfaces
            if i.source_id in allowed and i.target_id in allowed
        ]
        new_landscape = Landscape(
            id=landscape.id,
            applications=filtered_apps,
            interfaces=filtered_interfaces,
            vendors=landscape.vendors,
            scenarios=landscape.scenarios,
        )
    else:
        new_landscape = landscape

    return TransformedInputs(
        landscape=new_landscape,
        assumptions=new_assumptions,
        scenario_name=scenario_config.name,
    )


def compare_scenarios(
    name_a: str,
    financial_a: FinancialResult,
    simulation_a: SimulationResult | None,
    schedule_a: Schedule,
    name_b: str,
    financial_b: FinancialResult,
    simulation_b: SimulationResult | None,
    schedule_b: Schedule,
) -> ComparisonReport:
    """Produce a side-by-side comparison of two scenario results."""
    wave_a = [{"quarter": w.quarter, "items": w.work_item_ids} for w in schedule_a.waves]
    wave_b = [{"quarter": w.quarter, "items": w.work_item_ids} for w in schedule_b.waves]

    return ComparisonReport(
        scenario_a=name_a,
        scenario_b=name_b,
        tco_a=financial_a.tco,
        tco_b=financial_b.tco,
        npv_a=financial_a.npv,
        npv_b=financial_b.npv,
        payback_a=financial_a.payback_quarter,
        payback_b=financial_b.payback_quarter,
        deadline_miss_prob_a=simulation_a.deadline_miss_probabilities if simulation_a else {},
        deadline_miss_prob_b=simulation_b.deadline_miss_probabilities if simulation_b else {},
        wave_plan_a=wave_a,
        wave_plan_b=wave_b,
    )
