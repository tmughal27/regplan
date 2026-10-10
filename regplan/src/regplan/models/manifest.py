"""Run provenance model: RunManifest."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RunManifest(BaseModel):
    """Provenance record for a regplan run."""

    created_at: datetime
    regplan_version: str
    python_version: str
    git_commit: Optional[str] = None
    git_dirty: bool = False
    input_file_hashes: dict[str, str] = Field(default_factory=dict)    # path → SHA-256 hex
    installed_packages: dict[str, str] = Field(default_factory=dict)   # name → version
    scheduler_seed: int = 42
    simulation_seed: int = 42
