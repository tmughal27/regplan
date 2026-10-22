"""RunManifest builder — records provenance for a regplan run."""
from __future__ import annotations

import hashlib
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import packages_distributions, version
from pathlib import Path
from typing import Optional

from regplan.models.manifest import RunManifest


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _git_commit() -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def _git_dirty() -> bool:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5,
        )
        return bool(result.stdout.strip()) if result.returncode == 0 else False
    except Exception:
        return False


def _installed_packages() -> dict[str, str]:
    packages = ["pydantic", "pyyaml", "ortools", "networkx", "numpy",
                "typer", "jinja2", "matplotlib", "hypothesis", "pytest"]
    result: dict[str, str] = {}
    for pkg in packages:
        try:
            result[pkg] = version(pkg)
        except Exception:
            pass
    return result


def _regplan_version() -> str:
    try:
        return version("regplan")
    except Exception:
        return "0.0.0+unknown"


def build_manifest(
    input_paths: list[Path],
    scheduler_seed: int = 42,
    simulation_seed: int = 42,
) -> RunManifest:
    """Build a RunManifest recording provenance of the current run."""
    return RunManifest(
        created_at=datetime.now(tz=timezone.utc),
        regplan_version=_regplan_version(),
        python_version=sys.version,
        git_commit=_git_commit(),
        git_dirty=_git_dirty(),
        input_file_hashes={str(p): _sha256(p) for p in input_paths if p.exists()},
        installed_packages=_installed_packages(),
        scheduler_seed=scheduler_seed,
        simulation_seed=simulation_seed,
    )
