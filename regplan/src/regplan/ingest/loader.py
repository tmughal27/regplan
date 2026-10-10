"""YAML loading and Pydantic model construction for the Ingest stage."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from regplan.errors import IngestError
from regplan.models.assumptions import Assumptions
from regplan.models.landscape import Landscape
from regplan.models.regulation import RegulationPack


@dataclass
class IngestResult:
    """Typed output of the Ingest stage."""

    landscape: Landscape
    packs: list[RegulationPack]
    assumptions: Assumptions


def _load_yaml(path: Path) -> Any:
    """Load a YAML file and return the raw Python object.

    Raises IngestError on IO or parse errors.
    """
    try:
        with path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except FileNotFoundError:
        raise IngestError(str(path), "", f"file not found: {path}")
    except yaml.YAMLError as exc:
        raise IngestError(str(path), "", f"YAML parse error: {exc}")


def _parse_landscape(path: Path) -> Landscape:
    """Load and validate a Landscape YAML file."""
    raw = _load_yaml(path)
    try:
        return Landscape.model_validate(raw)
    except ValidationError as exc:
        errors = "; ".join(
            f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}"
            for e in exc.errors()
        )
        raise IngestError(str(path), "landscape", errors)


def _parse_regulation_pack(path: Path) -> RegulationPack:
    """Load and validate a RegulationPack YAML file."""
    raw = _load_yaml(path)
    try:
        return RegulationPack.model_validate(raw)
    except ValidationError as exc:
        errors = "; ".join(
            f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}"
            for e in exc.errors()
        )
        raise IngestError(str(path), "regulation_pack", errors)


def _parse_assumptions(path: Path) -> Assumptions:
    """Load and validate an Assumptions YAML file."""
    raw = _load_yaml(path)
    try:
        return Assumptions.model_validate(raw)
    except ValidationError as exc:
        errors = "; ".join(
            f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}"
            for e in exc.errors()
        )
        raise IngestError(str(path), "assumptions", errors)


def ingest(
    landscape_path: Path,
    packs_paths: list[Path],
    assumptions_path: Path,
) -> IngestResult:
    """Load and schema-validate all YAML inputs. Returns an IngestResult.

    Raises IngestError on any parse or schema validation failure.
    No side effects: does not write files, print to stdout, or access the network.
    """
    landscape = _parse_landscape(landscape_path)
    packs = [_parse_regulation_pack(p) for p in packs_paths]
    assumptions = _parse_assumptions(assumptions_path)
    return IngestResult(landscape=landscape, packs=packs, assumptions=assumptions)
