"""Parity tests between the bash dispatcher and the Python CLI.

The kit is in Phase 1 of the build roadmap: the bash dispatcher at
`.pkit/cli/pkit` stays as the self-sufficiency fallback while Python
graduates to canonical for each command in turn. Every command that has
graduated must produce identical output through both invocation paths.
This file's tests grow as Phase 2 / 3 ports more commands.

Today, only `version` (no subcommand — the print-version case) is
covered. `bump`, `init`, `status`, `new decision`, etc. land in
subsequent PRs and gain their own parity tests there.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BASH_DISPATCHER = REPO_ROOT / ".pkit" / "cli" / "pkit"


def _run(args: list[str]) -> str:
    result = subprocess.run(args, capture_output=True, text=True, check=True, cwd=REPO_ROOT)
    return result.stdout.strip()


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv not on PATH")
def test_version_parity_bash_vs_python() -> None:
    """`.pkit/cli/pkit version` and `uv run pkit version` print the same line."""
    bash_output = _run([str(BASH_DISPATCHER), "version"])
    python_output = _run(["uv", "run", "--quiet", "pkit", "version"])
    assert bash_output == python_output
    # Sanity: both should match the canonical pkit form.
    assert bash_output.startswith("pkit ")


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv not on PATH")
def test_init_via_bash_shim_resolves_users_cwd_not_source_repo(tmp_path: Path) -> None:
    """Regression: the init bash shim must not change cwd before invoking Python.

    Earlier the shim did `cd "$source_repo" && exec uv run python -m project_kit init`,
    which made Python's `Path.cwd()` resolve to the source repo and consequently
    `find_target_root` returned the source repo (which has `.pkit/`), so init refused
    to run with "already exists" — even when the user invoked the dispatcher from
    a fresh tmp dir. The fix uses `uv run --project <source_repo>` to point uv at
    pyproject.toml without changing cwd. This test asserts the user's cwd flows
    through to target-root resolution.
    """
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    result = subprocess.run(
        [str(BASH_DISPATCHER), "init", "--dry-run"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=True,
    )
    # The dry-run banner names the resolved target. macOS aliases /tmp -> /private/tmp,
    # so use a substring that matches the realpath of `tmp_path`.
    assert f"Installing project-kit into {tmp_path.resolve()}" in result.stdout
