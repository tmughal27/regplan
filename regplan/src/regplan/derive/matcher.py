"""Obligation matcher and modernisation WorkItem generator for the Derive stage."""
from __future__ import annotations

import math
from datetime import date

from regplan.derive.rule_engine import evaluate
from regplan.derive.scorer import ScoredApplication
from regplan.models.assumptions import Assumptions
from regplan.models.landscape import Disposition
from regplan.models.regulation import RegulationPack
from regplan.models.work import WorkItem

_MODERNISATION_QUARTERS: dict[str, int] = {
    "retire": 1,
    "rehost": 2,
    "replatform": 3,
    "refactor": 2,
    "replace": 4,
}

_MODERNISATION_EFFORT_DAYS: dict[str, float] = {
    "retire": 20.0,
    "rehost": 60.0,
    "replatform": 120.0,
    "refactor": 80.0,
    "replace": 180.0,
}


def _date_to_quarter(d: date, planning_start: date) -> int:
    """Return the 0-based quarter index containing date *d*."""
    days = max(0, (d - planning_start).days)
    return days // 91


def build_work_items(
    scored_apps: list[ScoredApplication],
    packs: list[RegulationPack],
    assumptions: Assumptions,
    node_to_scc: dict[str, int],
    condensed_predecessors: dict[int, list[int]],
    app_id_to_mod_wi: dict[str, str] | None = None,
) -> list[WorkItem]:
    """Create compliance WorkItems and modernisation WorkItems.

    *condensed_predecessors* maps SCC index → list of predecessor SCC indices.
    """
    work_items: list[WorkItem] = []
    compliance_by_app: dict[str, list[str]] = {}

    # --- Compliance WorkItems ---
    for sa in scored_apps:
        app = sa.application
        for pack in packs:
            for rule in pack.rules:
                if evaluate(rule.trigger, app, rule.id):
                    wi_id = f"{app.id}:{rule.id}"
                    cost = rule.effort_person_days * assumptions.daily_rate_gbp
                    duration = max(1, math.ceil(rule.effort_person_days / 60))
                    wi = WorkItem(
                        id=wi_id,
                        application_id=app.id,
                        rule_id=rule.id,
                        duration_quarters=duration,
                        cost_gbp=cost,
                        capacity_demand_days=rule.effort_person_days,
                        benefit_profile=[],
                        predecessors=[],
                        deadline=rule.deadline,
                        source_requirement=f"{rule.regulation}/{rule.id}",
                    )
                    work_items.append(wi)
                    compliance_by_app.setdefault(app.id, []).append(wi_id)

    # --- Modernisation WorkItems ---
    mod_ids_by_app: dict[str, str] = {}
    for sa in scored_apps:
        app = sa.application
        disp = sa.disposition
        if disp == Disposition.retain or disp.value not in _MODERNISATION_QUARTERS:
            continue
        effort_days = _MODERNISATION_EFFORT_DAYS[disp.value]
        duration = _MODERNISATION_QUARTERS[disp.value]
        cost = effort_days * assumptions.daily_rate_gbp
        wi_id = f"{app.id}:modernise"
        # Predecessors: compliance WIs for this app must complete first
        preds: list[str] = list(compliance_by_app.get(app.id, []))
        # capacity_demand_days is per-quarter (spread effort over duration)
        per_quarter_demand = effort_days / max(duration, 1)
        wi = WorkItem(
            id=wi_id,
            application_id=app.id,
            rule_id=None,
            disposition=disp,
            duration_quarters=duration,
            cost_gbp=cost,
            capacity_demand_days=per_quarter_demand,
            benefit_profile=[cost * 0.05] * 8,
            predecessors=preds,
            deadline=None,
            source_requirement=f"disposition/{disp.value}",
        )
        work_items.append(wi)
        mod_ids_by_app[app.id] = wi_id

    # --- Cross-app predecessor relationships for modernisation items ---
    # If app_a's SCC has a predecessor SCC containing app_b, then app_a's
    # modernisation WorkItem depends on app_b's modernisation WorkItem.
    for sa in scored_apps:
        app = sa.application
        mod_id = mod_ids_by_app.get(app.id)
        if mod_id is None:
            continue
        scc = node_to_scc.get(app.id, -1)
        for pred_scc in condensed_predecessors.get(scc, []):
            for other_app_id in _scc_apps_for_index(scored_apps, node_to_scc, pred_scc):
                dep_mod = mod_ids_by_app.get(other_app_id)
                if dep_mod and dep_mod not in mod_id:
                    # Find the WorkItem and add predecessor
                    for wi in work_items:
                        if wi.id == mod_id and dep_mod not in wi.predecessors:
                            wi.predecessors.append(dep_mod)

    return work_items


def _scc_apps_for_index(
    scored_apps: list[ScoredApplication],
    node_to_scc: dict[str, int],
    scc_idx: int,
) -> list[str]:
    return [sa.application.id for sa in scored_apps if node_to_scc.get(sa.application.id) == scc_idx]
