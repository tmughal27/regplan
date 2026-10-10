"""Unit tests for regplan.ingest.validator."""
from __future__ import annotations

import textwrap
from datetime import date
from pathlib import Path

import pytest

from regplan.errors import SemanticError
from regplan.ingest.loader import ingest
from regplan.ingest.validator import collect_errors, validate


# ── Shared YAML helpers ───────────────────────────────────────────────────────

ASSUMPTIONS_YAML = textwrap.dedent("""\
    planning_start: "2026-01-01"
    horizon_quarters: 12
    discount_rate: 0.08
    daily_rate_gbp: 700.0
    quarterly_capacity_days: 120.0
    cumulative_budget_gbp: 5000000.0
    cost_overrun_dist:
      type: triangular
      low: 0.8
      mode: 1.0
      high: 1.3
    duration_slip_dist:
      type: triangular
      low: 0.0
      mode: 0.1
      high: 0.3
    benefit_realization_dist:
      type: triangular
      low: 0.7
      mode: 0.9
      high: 1.0
""")

VALID_PACK_YAML = textwrap.dedent("""\
    regulation: GDPR
    version: "2024-01"
    rules:
      - id: R-GDPR-01
        regulation: GDPR
        title: DPO appointment
        trigger:
          attribute: data_residency
          operator: eq
          value: true
        deadline: "2027-06-01"
        effort_person_days: 10.0
        source_url: "https://gdpr-info.eu/art-37-gdpr/"
        last_verified: "2024-01-01"
""")

STALE_PACK_YAML = textwrap.dedent("""\
    regulation: GDPR
    version: "2024-01"
    rules:
      - id: R-GDPR-01
        regulation: GDPR
        title: DPO appointment
        trigger:
          attribute: data_residency
          operator: eq
          value: true
        deadline: "2020-01-01"
        effort_person_days: 10.0
        source_url: "https://gdpr-info.eu/art-37-gdpr/"
        last_verified: "2019-01-01"
""")


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def _make_result(tmp_path: Path, landscape_yaml: str, pack_yaml: str = VALID_PACK_YAML) -> object:
    lp = _write(tmp_path, "landscape.yaml", landscape_yaml)
    ap = _write(tmp_path, "assumptions.yaml", ASSUMPTIONS_YAML)
    pp = _write(tmp_path, "pack.yaml", pack_yaml)
    return ingest(lp, [pp], ap)


# ── Interface reference checks ────────────────────────────────────────────────

def test_valid_landscape_no_errors(tmp_path: Path) -> None:
    landscape_yaml = textwrap.dedent("""\
        id: L-TEST
        applications:
          - id: APP-01
            name: CRM
            owner: sales
            business_value: 0.8
            technical_health: 0.6
          - id: APP-02
            name: ERP
            owner: finance
            business_value: 0.7
            technical_health: 0.5
        interfaces:
          - id: IF-01
            source_id: APP-01
            target_id: APP-02
            protocol: REST
    """)
    result = _make_result(tmp_path, landscape_yaml)
    assert collect_errors(result) == []  # type: ignore[arg-type]


def test_interface_unknown_source_raises(tmp_path: Path) -> None:
    landscape_yaml = textwrap.dedent("""\
        id: L-TEST
        applications:
          - id: APP-01
            name: CRM
            owner: sales
            business_value: 0.5
            technical_health: 0.5
        interfaces:
          - id: IF-01
            source_id: UNKNOWN
            target_id: APP-01
            protocol: REST
    """)
    result = _make_result(tmp_path, landscape_yaml)
    errors = collect_errors(result)  # type: ignore[arg-type]
    assert any("UNKNOWN" in e.suggestion for e in errors)


def test_interface_unknown_target_raises(tmp_path: Path) -> None:
    landscape_yaml = textwrap.dedent("""\
        id: L-TEST
        applications:
          - id: APP-01
            name: CRM
            owner: sales
            business_value: 0.5
            technical_health: 0.5
        interfaces:
          - id: IF-01
            source_id: APP-01
            target_id: GHOST
            protocol: REST
    """)
    result = _make_result(tmp_path, landscape_yaml)
    errors = collect_errors(result)  # type: ignore[arg-type]
    assert any("GHOST" in e.suggestion for e in errors)


# ── Uniqueness checks ─────────────────────────────────────────────────────────

def test_duplicate_application_id_raises(tmp_path: Path) -> None:
    landscape_yaml = textwrap.dedent("""\
        id: L-TEST
        applications:
          - id: APP-01
            name: CRM
            owner: sales
            business_value: 0.5
            technical_health: 0.5
          - id: APP-01
            name: Duplicate
            owner: it
            business_value: 0.3
            technical_health: 0.3
    """)
    result = _make_result(tmp_path, landscape_yaml)
    errors = collect_errors(result)  # type: ignore[arg-type]
    assert any(e.rule_name == "id_uniqueness" for e in errors)


# ── Deadline checks ───────────────────────────────────────────────────────────

def test_past_deadline_raises(tmp_path: Path) -> None:
    landscape_yaml = textwrap.dedent("""\
        id: L-TEST
        applications:
          - id: APP-01
            name: CRM
            owner: sales
            business_value: 0.5
            technical_health: 0.5
    """)
    result = _make_result(tmp_path, landscape_yaml, pack_yaml=STALE_PACK_YAML)
    errors = collect_errors(result)  # type: ignore[arg-type]
    assert any(e.rule_name == "deadline_plausibility" for e in errors)


# ── validate() raises on first error ─────────────────────────────────────────

def test_validate_raises_semantic_error(tmp_path: Path) -> None:
    landscape_yaml = textwrap.dedent("""\
        id: L-TEST
        applications:
          - id: APP-01
            name: CRM
            owner: sales
            business_value: 0.5
            technical_health: 0.5
        interfaces:
          - id: IF-01
            source_id: MISSING
            target_id: APP-01
            protocol: REST
    """)
    result = _make_result(tmp_path, landscape_yaml)
    with pytest.raises(SemanticError):
        validate(result)  # type: ignore[arg-type]
