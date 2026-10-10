"""Unit tests for regplan.ingest.loader."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from regplan.errors import IngestError
from regplan.ingest.loader import IngestResult, ingest, _parse_landscape, _parse_assumptions


# ── Shared YAML fixtures ──────────────────────────────────────────────────────

LANDSCAPE_YAML = textwrap.dedent("""\
    id: L-TEST
    applications:
      - id: APP-01
        name: CRM
        owner: sales
        business_value: 0.8
        technical_health: 0.6
    interfaces: []
    vendors: []
""")

ASSUMPTIONS_YAML = textwrap.dedent("""\
    planning_start: "2025-01-01"
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

PACK_YAML = textwrap.dedent("""\
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
        deadline: "2027-01-01"
        effort_person_days: 10.0
        source_url: "https://gdpr-info.eu/art-37-gdpr/"
        last_verified: "2024-01-01"
""")


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_ingest_returns_ingest_result(tmp_path: Path) -> None:
    lp = _write(tmp_path, "landscape.yaml", LANDSCAPE_YAML)
    ap = _write(tmp_path, "assumptions.yaml", ASSUMPTIONS_YAML)
    pp = _write(tmp_path, "gdpr.yaml", PACK_YAML)

    result = ingest(lp, [pp], ap)

    assert isinstance(result, IngestResult)
    assert result.landscape.id == "L-TEST"
    assert len(result.landscape.applications) == 1
    assert result.assumptions.discount_rate == 0.08
    assert len(result.packs) == 1
    assert result.packs[0].regulation == "GDPR"


def test_ingest_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(IngestError) as exc_info:
        _parse_landscape(tmp_path / "nonexistent.yaml")
    assert "file not found" in str(exc_info.value)


def test_ingest_invalid_schema_raises(tmp_path: Path) -> None:
    bad = textwrap.dedent("""\
        id: L-BAD
        applications:
          - id: APP-01
            name: X
            owner: y
            business_value: 9.9
            technical_health: 0.5
    """)
    lp = _write(tmp_path, "bad.yaml", bad)
    with pytest.raises(IngestError) as exc_info:
        _parse_landscape(lp)
    assert "landscape" in str(exc_info.value)


def test_ingest_no_packs(tmp_path: Path) -> None:
    lp = _write(tmp_path, "landscape.yaml", LANDSCAPE_YAML)
    ap = _write(tmp_path, "assumptions.yaml", ASSUMPTIONS_YAML)
    result = ingest(lp, [], ap)
    assert result.packs == []


def test_ingest_assumptions_missing_field_raises(tmp_path: Path) -> None:
    bad = "planning_start: '2025-01-01'\nhorizon_quarters: 12\n"
    ap = _write(tmp_path, "assumptions.yaml", bad)
    with pytest.raises(IngestError):
        _parse_assumptions(ap)


def test_ingest_yaml_parse_error_raises(tmp_path: Path) -> None:
    bad = "key: [\nunclosed bracket"
    lp = _write(tmp_path, "broken.yaml", bad)
    with pytest.raises(IngestError) as exc_info:
        _parse_landscape(lp)
    assert "YAML parse error" in str(exc_info.value)
