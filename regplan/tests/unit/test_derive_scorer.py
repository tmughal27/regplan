"""Unit tests for regplan.derive.scorer."""
from __future__ import annotations

from regplan.derive.scorer import score_applications
from regplan.models.assumptions import Assumptions, DistributionSpec, DispositionRule
from regplan.models.landscape import Application, Disposition, Landscape


def _dist() -> DistributionSpec:
    return DistributionSpec(type="triangular", low=0.8, mode=1.0, high=1.3)


def _assumptions(rules: list[DispositionRule] | None = None) -> Assumptions:
    return Assumptions(
        planning_start="2026-01-01",  # type: ignore[arg-type]
        horizon_quarters=8,
        discount_rate=0.08,
        daily_rate_gbp=700.0,
        quarterly_capacity_days=120.0,
        cumulative_budget_gbp=5_000_000.0,
        cost_overrun_dist=_dist(),
        duration_slip_dist=_dist(),
        benefit_realization_dist=_dist(),
        decision_table=rules or [],
    )


def _landscape(apps: list[Application]) -> Landscape:
    return Landscape(id="L-TEST", applications=apps, interfaces=[], vendors=[])


def _app(id: str, bv: float, th: float, **kwargs: object) -> Application:
    return Application(
        id=id, name=id, owner="test",
        business_value=bv, technical_health=th, **kwargs  # type: ignore[arg-type]
    )


def test_scores_normalised_to_range() -> None:
    apps = [_app("A", 0.2, 0.8), _app("B", 0.8, 0.2)]
    landscape = _landscape(apps)
    scored = score_applications(landscape, _assumptions())
    for sa in scored:
        assert 0.0 <= sa.norm_business_value <= 1.0
        assert 0.0 <= sa.norm_technical_health <= 1.0


def test_disposition_assigned_from_decision_table() -> None:
    rule = DispositionRule(
        rule_id="replace-low-health",
        min_technical_health=0.0,
        max_technical_health=0.3,
        disposition="replace",
    )
    apps = [_app("A", 0.5, 0.1), _app("B", 0.5, 0.9)]
    landscape = _landscape(apps)
    scored = score_applications(landscape, _assumptions([rule]))
    dispositions = {sa.application.id: sa.disposition for sa in scored}
    assert dispositions["A"] == Disposition.replace
    assert dispositions["B"] == Disposition.retain  # no rule matched → default retain


def test_no_rule_defaults_to_retain() -> None:
    apps = [_app("A", 0.5, 0.5)]
    landscape = _landscape(apps)
    scored = score_applications(landscape, _assumptions())
    assert scored[0].disposition == Disposition.retain
    assert scored[0].matched_rule_id == "default"
    assert len(scored[0].score_warnings) == 1


def test_single_app_normalisation() -> None:
    apps = [_app("A", 0.7, 0.3)]
    landscape = _landscape(apps)
    scored = score_applications(landscape, _assumptions())
    # Single app → min==max → normalise to 0.5
    assert scored[0].norm_business_value == 0.5
    assert scored[0].norm_technical_health == 0.5
