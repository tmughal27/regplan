"""Semantic validation for Ingest stage inputs.

Schema validation (types and ranges) is handled by Pydantic in the loader.
This module checks *logical consistency* across entities after schema parsing:

- Every Interface references Application ids that exist in the same Landscape.
- All Application ids and Interface ids are unique within a Landscape.
- Every RegulationRule has a non-empty source_url and a last_verified date.
- Every RegulationRule deadline is >= the planning_start date in Assumptions.
"""
from __future__ import annotations

from datetime import date

from regplan.errors import SemanticError
from regplan.ingest.loader import IngestResult
from regplan.models.landscape import Landscape
from regplan.models.regulation import RegulationPack


# ── Individual check functions ─────────────────────────────────────────────────

def _check_interface_refs(landscape: Landscape) -> list[SemanticError]:
    """Check that every Interface source_id and target_id exist in the Landscape."""
    app_ids = {app.id for app in landscape.applications}
    errors: list[SemanticError] = []
    for iface in landscape.interfaces:
        if iface.source_id not in app_ids:
            errors.append(
                SemanticError(
                    entity_id=iface.id,
                    rule_name="interface_ref",
                    suggestion=(
                        f"source_id '{iface.source_id}' does not reference a known Application; "
                        f"known ids: {sorted(app_ids)}"
                    ),
                )
            )
        if iface.target_id not in app_ids:
            errors.append(
                SemanticError(
                    entity_id=iface.id,
                    rule_name="interface_ref",
                    suggestion=(
                        f"target_id '{iface.target_id}' does not reference a known Application; "
                        f"known ids: {sorted(app_ids)}"
                    ),
                )
            )
    return errors


def _check_id_uniqueness(landscape: Landscape) -> list[SemanticError]:
    """Check that Application ids and Interface ids are each unique within the Landscape."""
    errors: list[SemanticError] = []

    app_ids: list[str] = [app.id for app in landscape.applications]
    seen_app: set[str] = set()
    for aid in app_ids:
        if aid in seen_app:
            errors.append(
                SemanticError(
                    entity_id=aid,
                    rule_name="id_uniqueness",
                    suggestion=f"Duplicate Application id '{aid}'; all Application ids must be unique",
                )
            )
        seen_app.add(aid)

    iface_ids: list[str] = [iface.id for iface in landscape.interfaces]
    seen_iface: set[str] = set()
    for iid in iface_ids:
        if iid in seen_iface:
            errors.append(
                SemanticError(
                    entity_id=iid,
                    rule_name="id_uniqueness",
                    suggestion=f"Duplicate Interface id '{iid}'; all Interface ids must be unique",
                )
            )
        seen_iface.add(iid)

    return errors


def _check_rule_metadata(pack: RegulationPack) -> list[SemanticError]:
    """Check that every RegulationRule has source_url and last_verified."""
    errors: list[SemanticError] = []
    for rule in pack.rules:
        # Pydantic already validates source_url as HttpUrl (non-empty), but we
        # double-check for an empty string representation defensively.
        if not str(rule.source_url).strip():
            errors.append(
                SemanticError(
                    entity_id=rule.id,
                    rule_name="rule_metadata",
                    suggestion=f"Rule '{rule.id}' has an empty source_url; provide a valid URL",
                )
            )
        # last_verified is required by the Pydantic model, but confirm it is present.
        if rule.last_verified is None:
            errors.append(
                SemanticError(
                    entity_id=rule.id,
                    rule_name="rule_metadata",
                    suggestion=f"Rule '{rule.id}' is missing last_verified date",
                )
            )
    return errors


def _check_deadlines(pack: RegulationPack, planning_start: date) -> list[SemanticError]:
    """Check that every RegulationRule deadline is >= planning_start."""
    errors: list[SemanticError] = []
    for rule in pack.rules:
        if rule.deadline < planning_start:
            errors.append(
                SemanticError(
                    entity_id=rule.id,
                    rule_name="deadline_plausibility",
                    suggestion=(
                        f"Rule '{rule.id}' deadline {rule.deadline} is before the planning start "
                        f"{planning_start}; either extend the deadline or update planning_start"
                    ),
                )
            )
    return errors


# ── Public entry point ─────────────────────────────────────────────────────────

def validate(result: IngestResult) -> None:
    """Run all semantic validation checks against an IngestResult.

    Raises the *first* SemanticError encountered. To collect all errors, see
    collect_errors() below.
    """
    errors = collect_errors(result)
    if errors:
        raise errors[0]


def collect_errors(result: IngestResult) -> list[SemanticError]:
    """Return all semantic validation errors without raising."""
    errors: list[SemanticError] = []

    # Landscape checks
    errors.extend(_check_interface_refs(result.landscape))
    errors.extend(_check_id_uniqueness(result.landscape))

    # RegulationPack checks
    for pack in result.packs:
        errors.extend(_check_rule_metadata(pack))
        errors.extend(_check_deadlines(pack, result.assumptions.planning_start))

    return errors
