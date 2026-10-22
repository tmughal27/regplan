"""Application scoring and disposition assignment."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from regplan.models.assumptions import Assumptions
from regplan.models.landscape import Application, Disposition, Landscape

logger = logging.getLogger(__name__)


def _min_max_normalise(values: list[float]) -> list[float]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.5] * len(values)
    return [(v - lo) / (hi - lo) for v in values]


@dataclass
class ScoredApplication:
    """Application enriched with normalised scores and assigned disposition."""
    application: Application
    norm_business_value: float = 0.0
    norm_technical_health: float = 0.0
    norm_regulatory_exposure: float = 0.0
    norm_vendor_dependence: float = 0.0
    disposition: Disposition = field(default_factory=lambda: Disposition.retain)
    matched_rule_id: str = "default"
    score_warnings: list[str] = field(default_factory=list)


def _reg_exposure(app: Application) -> float:
    score = 0.0
    if app.data_residency:
        score += 0.4
    if app.data_classification.lower() in ("pii", "financial"):
        score += 0.4
    if app.ai_enabled:
        score += 0.2
    return min(score, 1.0)


def _vendor_dep(app: Application) -> float:
    return 0.8 if app.vendor_id else 0.1


def score_applications(landscape: Landscape, assumptions: Assumptions) -> list[ScoredApplication]:
    """Normalise scores and assign Dispositions to all Applications in *landscape*."""
    apps = landscape.applications

    bv_norms = _min_max_normalise([a.business_value for a in apps])
    th_norms = _min_max_normalise([a.technical_health for a in apps])
    re_norms = _min_max_normalise([_reg_exposure(a) for a in apps])
    vd_norms = _min_max_normalise([_vendor_dep(a) for a in apps])

    scored: list[ScoredApplication] = []
    for i, app in enumerate(apps):
        sa = ScoredApplication(
            application=app,
            norm_business_value=bv_norms[i],
            norm_technical_health=th_norms[i],
            norm_regulatory_exposure=re_norms[i],
            norm_vendor_dependence=vd_norms[i],
        )
        matched = False
        for rule in assumptions.decision_table:
            if (
                rule.min_business_value <= sa.norm_business_value <= rule.max_business_value
                and rule.min_technical_health <= sa.norm_technical_health <= rule.max_technical_health
                and rule.min_regulatory_exposure <= sa.norm_regulatory_exposure <= rule.max_regulatory_exposure
                and rule.min_vendor_dependence <= sa.norm_vendor_dependence <= rule.max_vendor_dependence
            ):
                sa.disposition = Disposition(rule.disposition)
                sa.matched_rule_id = rule.rule_id
                matched = True
                break
        if not matched:
            sa.disposition = Disposition.retain
            sa.matched_rule_id = "default"
            msg = f"No decision_table rule matched for app '{app.id}'; defaulting to 'retain'"
            sa.score_warnings.append(msg)
            logger.warning(msg)
        scored.append(sa)
    return scored
