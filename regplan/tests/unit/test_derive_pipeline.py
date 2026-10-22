"""Integration tests for the Derive stage end-to-end."""
from __future__ import annotations

from pathlib import Path

import pytest

from regplan.derive import DeriveResult, derive
from regplan.ingest.loader import ingest


_EXAMPLES = Path(__file__).parent.parent.parent / "src" / "regplan" / "examples"
_ASSUMPTIONS = _EXAMPLES / "assumptions.yaml"
_PACKS = sorted((_EXAMPLES / "packs").glob("*.yaml"))
_LANDSCAPE = _EXAMPLES / "landscapes" / "legacy_heavy.yaml"


def test_derive_returns_derive_result() -> None:
    ir = ingest(_LANDSCAPE, _PACKS, _ASSUMPTIONS)
    result = derive(ir, ir.assumptions)
    assert isinstance(result, DeriveResult)


def test_derive_produces_work_items() -> None:
    ir = ingest(_LANDSCAPE, _PACKS, _ASSUMPTIONS)
    result = derive(ir, ir.assumptions)
    assert len(result.work_items) > 0


def test_derive_scores_all_applications() -> None:
    ir = ingest(_LANDSCAPE, _PACKS, _ASSUMPTIONS)
    result = derive(ir, ir.assumptions)
    assert len(result.scored_applications) == len(ir.landscape.applications)


def test_derive_graph_has_all_apps() -> None:
    ir = ingest(_LANDSCAPE, _PACKS, _ASSUMPTIONS)
    result = derive(ir, ir.assumptions)
    graph_nodes = set(result.graph.app_graph.nodes())
    app_ids = {a.id for a in ir.landscape.applications}
    assert app_ids == graph_nodes


def test_derive_work_items_have_source_requirements() -> None:
    ir = ingest(_LANDSCAPE, _PACKS, _ASSUMPTIONS)
    result = derive(ir, ir.assumptions)
    for wi in result.work_items:
        assert wi.source_requirement, f"WorkItem {wi.id} has no source_requirement"
