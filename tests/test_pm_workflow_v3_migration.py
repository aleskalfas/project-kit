"""Idempotency + warn-on-override tests for the workflow.yaml v2->v3 migration
(DEC-033 D6). The migration NEVER rewrites the kit-shipped file and NEVER
auto-edits a project-owned override — it only warns when an adopter override is
stale.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "migrations"
    / "0.24.0"
    / "001-workflow-yaml-schema-v3.sh"
)


def _make_adopter(tmp_path: Path, *, kit_version: str, override_version: str | None) -> Path:
    """Build a minimal adopter tree: kit-shipped workflow.yaml + optional
    project-owned override."""
    root = tmp_path / "adopter"
    cap = root / ".pkit" / "capabilities" / "project-management"
    schemas = cap / "schemas"
    schemas.mkdir(parents=True)
    (schemas / "workflow.yaml").write_text(
        f"schema_version: {kit_version}\nprocess:\n  id: issue-lifecycle\n",
        encoding="utf-8",
    )
    if override_version is not None:
        overrides = cap / "project" / "schema-overrides"
        overrides.mkdir(parents=True)
        (overrides / "workflow.yaml").write_text(
            f"schema_version: {override_version}\n", encoding="utf-8"
        )
    return root


def _run(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(MIGRATION)],
        env={"ROOT": str(root), "PATH": "/usr/bin:/bin:/usr/local/bin"},
        capture_output=True,
        text=True,
        check=False,
    )


def test_no_override_is_clean(tmp_path: Path) -> None:
    root = _make_adopter(tmp_path, kit_version="3", override_version=None)
    result = _run(root)
    assert result.returncode == 0, result.stderr
    assert "no adopter override" in result.stdout


def test_stale_override_warns(tmp_path: Path) -> None:
    root = _make_adopter(tmp_path, kit_version="3", override_version="2")
    result = _run(root)
    assert result.returncode == 0, result.stderr
    assert "[warn]" in result.stdout
    assert "schema_version: 3" in result.stdout
    # The override file is NOT rewritten (still schema_version 2).
    override = (
        root
        / ".pkit"
        / "capabilities"
        / "project-management"
        / "project"
        / "schema-overrides"
        / "workflow.yaml"
    )
    assert "schema_version: 2" in override.read_text(encoding="utf-8")


def test_current_override_is_noop(tmp_path: Path) -> None:
    root = _make_adopter(tmp_path, kit_version="3", override_version="3")
    result = _run(root)
    assert result.returncode == 0, result.stderr
    assert "already at schema_version 3" in result.stdout


def test_idempotent_rerun(tmp_path: Path) -> None:
    root = _make_adopter(tmp_path, kit_version="3", override_version="3")
    first = _run(root)
    second = _run(root)
    assert first.returncode == second.returncode == 0
    assert first.stdout == second.stdout


def test_capability_absent_skips(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    result = _run(root)
    assert result.returncode == 0
    assert "[skip]" in result.stdout
