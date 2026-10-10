"""Verify all example YAML files pass schema and semantic validation."""
from __future__ import annotations

from importlib import resources
from pathlib import Path

import pytest

from regplan.ingest.loader import ingest
from regplan.ingest.validator import collect_errors


def _examples_dir() -> Path:
    """Return path to the examples directory inside the installed package."""
    # Works whether installed as editable or wheel
    pkg_root = Path(__file__).parent.parent.parent / "src" / "regplan" / "examples"
    return pkg_root


ASSUMPTIONS = _examples_dir() / "assumptions.yaml"
LANDSCAPES_DIR = _examples_dir() / "landscapes"
PACKS_DIR = _examples_dir() / "packs"

ALL_PACKS = sorted(PACKS_DIR.glob("*.yaml"))
ALL_LANDSCAPES = sorted(LANDSCAPES_DIR.glob("*.yaml"))


@pytest.mark.parametrize("landscape_path", ALL_LANDSCAPES, ids=lambda p: p.stem)
def test_example_landscape_schema_valid(landscape_path: Path) -> None:
    """Each example landscape must pass schema validation."""
    result = ingest(landscape_path, ALL_PACKS, ASSUMPTIONS)
    assert result.landscape is not None
    assert len(result.landscape.applications) >= 5


@pytest.mark.parametrize("landscape_path", ALL_LANDSCAPES, ids=lambda p: p.stem)
def test_example_landscape_semantic_valid(landscape_path: Path) -> None:
    """Each example landscape must pass semantic validation."""
    result = ingest(landscape_path, ALL_PACKS, ASSUMPTIONS)
    errors = collect_errors(result)
    assert errors == [], f"Semantic errors in {landscape_path.name}: {errors}"


@pytest.mark.parametrize("pack_path", ALL_PACKS, ids=lambda p: p.stem)
def test_example_pack_has_rules(pack_path: Path) -> None:
    """Each regulation pack must load and contain >= 3 rules."""
    # Use a minimal landscape and assumptions to satisfy ingest signature
    landscape_path = LANDSCAPES_DIR / "cloud_native.yaml"
    result = ingest(landscape_path, [pack_path], ASSUMPTIONS)
    assert len(result.packs) == 1
    assert len(result.packs[0].rules) >= 3
