"""Monte Carlo simulation engine for the Simulate stage."""
from __future__ import annotations

import math
from datetime import date, timedelta

import numpy as np

from regplan.models.assumptions import Assumptions, DistributionSpec
from regplan.models.finance import FinancialResult
from regplan.models.simulation import SimulationResult, SimulationRun, TornadoEntry
from regplan.models.work import Schedule, WorkItem


def _sample_distribution(rng: np.random.Generator, spec: DistributionSpec) -> float:
    if spec.type == "triangular":
        low = spec.low if spec.low is not None else 0.8
        mode = spec.mode if spec.mode is not None else 1.0
        high = spec.high if spec.high is not None else 1.2
        return float(rng.triangular(low, mode, high))
    if spec.type == "lognormal":
        mu = spec.mu if spec.mu is not None else 0.0
        sigma = spec.sigma if spec.sigma is not None else 0.1
        return float(rng.lognormal(mu, sigma))
    return 1.0


def _compute_npv(
    costs: dict[str, float],
    starts: dict[str, int],
    work_items: list[WorkItem],
    financial_result: FinancialResult,
    discount_rate: float,
) -> float:
    """Recompute NPV given simulated per-item costs."""
    npv = 0.0
    for cf in financial_result.cash_flows:
        discount = (1.0 + discount_rate) ** cf.quarter
        npv += cf.net / discount
    return npv


def run_simulation(
    schedule: Schedule,
    financial_result: FinancialResult,
    work_items: list[WorkItem],
    assumptions: Assumptions,
    n_runs: int,
    seed: int,
) -> SimulationResult:
    """Execute Monte Carlo simulation and return SimulationResult."""
    if not (1 <= n_runs <= 100_000):
        raise ValueError(f"n_runs must be between 1 and 100,000; got {n_runs}")

    rng = np.random.default_rng(seed)
    item_map = {wi.id: wi for wi in work_items}
    starts = schedule.work_item_starts
    discount_rate = assumptions.discount_rate
    corr = assumptions.overrun_correlation

    runs: list[SimulationRun] = []
    all_costs: list[float] = []
    all_npvs: list[float] = []

    # Track deadline-miss counts per regulation rule
    rule_ids = {wi.rule_id for wi in work_items if wi.rule_id}
    deadline_misses: dict[str, int] = {rid: 0 for rid in rule_ids}

    for run_idx in range(n_runs):
        # Common overrun factor (shared across all items in this run)
        common_factor = _sample_distribution(rng, assumptions.cost_overrun_dist)

        total_cost = 0.0
        run_npv = 0.0
        completion_dates: dict[str, date] = {}
        simulated_starts: dict[str, int] = dict(starts)

        # Propagate duration slips in topological order
        for wi_id in _topological_order(work_items):
            wi = item_map.get(wi_id)
            if wi is None or wi_id not in simulated_starts:
                continue

            indiv_cost_factor = _sample_distribution(rng, assumptions.cost_overrun_dist)
            blended = (1 - corr) * indiv_cost_factor + corr * common_factor
            sim_cost = wi.cost_gbp * blended

            slip_factor = _sample_distribution(rng, assumptions.duration_slip_dist)
            slip_quarters = slip_factor  # fractional quarters of slip

            sim_start = simulated_starts[wi_id]
            # Push down predecessor ends
            for pred_id in wi.predecessors:
                pred_wi = item_map.get(pred_id)
                if pred_wi and pred_id in simulated_starts:
                    pred_end = simulated_starts[pred_id] + pred_wi.duration_quarters
                    sim_start = max(sim_start, pred_end)
            simulated_starts[wi_id] = sim_start

            sim_duration = wi.duration_quarters + slip_quarters
            sim_end_q = sim_start + sim_duration

            # Convert end quarter to approximate date
            planning_start = assumptions.planning_start
            end_days = int(sim_end_q * 91)
            sim_end_date = planning_start + timedelta(days=end_days)
            completion_dates[wi_id] = sim_end_date

            # Check deadline miss
            if wi.rule_id and wi.deadline:
                if sim_end_date > wi.deadline:
                    deadline_misses[wi.rule_id] = deadline_misses.get(wi.rule_id, 0) + 1

            total_cost += sim_cost

        # Recompute NPV using base cash flows scaled by common_factor
        base_npv = financial_result.npv
        run_npv = base_npv * common_factor

        all_costs.append(total_cost)
        all_npvs.append(run_npv)
        runs.append(
            SimulationRun(
                run_index=run_idx,
                total_cost=total_cost,
                npv=run_npv,
                completion_dates=completion_dates,
            )
        )

    costs_arr = np.array(all_costs)
    npvs_arr = np.array(all_npvs)

    # Deadline miss probabilities
    deadline_probs: dict[str, float] = {
        rid: count / n_runs for rid, count in deadline_misses.items()
    }

    # Tornado: one-at-a-time NPV variance attribution
    tornado = _compute_tornado(
        schedule, financial_result, work_items, assumptions, seed, n_runs
    )

    return SimulationResult(
        runs=runs,
        p50_cost=float(np.percentile(costs_arr, 50)),
        p80_cost=float(np.percentile(costs_arr, 80)),
        p95_cost=float(np.percentile(costs_arr, 95)),
        p50_npv=float(np.percentile(npvs_arr, 50)),
        p80_npv=float(np.percentile(npvs_arr, 80)),
        p95_npv=float(np.percentile(npvs_arr, 95)),
        deadline_miss_probabilities=deadline_probs,
        tornado=tornado,
        seed=seed,
    )


def _topological_order(work_items: list[WorkItem]) -> list[str]:
    """Return WorkItem ids in a topological order (predecessors first)."""
    item_map = {wi.id: wi for wi in work_items}
    visited: set[str] = set()
    order: list[str] = []

    def visit(wi_id: str) -> None:
        if wi_id in visited:
            return
        visited.add(wi_id)
        wi = item_map.get(wi_id)
        if wi:
            for pred in wi.predecessors:
                visit(pred)
        order.append(wi_id)

    for wi in work_items:
        visit(wi.id)
    return order


def _compute_tornado(
    schedule: Schedule,
    financial_result: FinancialResult,
    work_items: list[WorkItem],
    assumptions: Assumptions,
    seed: int,
    n_runs: int,
) -> list[TornadoEntry]:
    """Compute tornado ranking via one-at-a-time variance attribution on NPV."""
    assumption_names = ["cost_overrun_dist", "duration_slip_dist", "benefit_realization_dist"]
    base_npv = financial_result.npv
    entries: list[TornadoEntry] = []

    # For each assumption, fix others at median and vary only that one
    mini_runs = min(n_runs, 100)
    rng = np.random.default_rng(seed + 1000)

    for name in assumption_names:
        npvs: list[float] = []
        for _ in range(mini_runs):
            spec = getattr(assumptions, name)
            factor = _sample_distribution(rng, spec)
            sim_npv = base_npv * factor
            npvs.append(sim_npv)
        variance = float(np.var(npvs))
        entries.append(TornadoEntry(assumption_name=name, npv_variance_contribution=variance))

    return sorted(entries, key=lambda e: e.npv_variance_contribution, reverse=True)
