"""The guidance migration for `pkit sync --force`, ignored for one release (#1460).

ADR-065 point 10: sync accepts `--force`, ignores it and says so, and a later
release removes it. A flag whose meaning changes is one of COR-010's triggers, so
`2.0.0/001-sync-force-ignored` names each project file that runs the flag. It
edits nothing and exits clean, over any state.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION = REPO_ROOT / ".pkit" / "migrations" / "backbone" / "2.0.0" / "001-sync-force-ignored.sh"


def _run(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(MIGRATION)],
        env={"ROOT": str(root), "PATH": "/usr/bin:/bin:/usr/local/bin"},
        capture_output=True,
        text=True,
        check=False,
    )


def _project(tmp_path: Path, *, git: bool, files: dict[str, str]) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    if git:
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    return root


_WORKFLOW = ".github/workflows/checks.yml"
_FORCED = "jobs:\n  sync:\n    steps:\n      - run: pkit sync --dry-run --force\n"


@pytest.mark.parametrize("git", [True, False], ids=["git", "no-git"])
def test_names_each_project_file_that_runs_sync_with_force_and_edits_nothing(
    tmp_path: Path, git: bool
) -> None:
    root = _project(tmp_path, git=git, files={_WORKFLOW: _FORCED, "README.md": "pkit sync\n"})

    result = _run(root)

    assert result.returncode == 0, result.stderr
    assert "[warn] these files run `pkit sync --force`" in result.stderr
    assert _WORKFLOW in result.stderr
    assert "README.md" not in result.stderr
    assert "Drop `--force` from these lines." in result.stderr
    assert (root / _WORKFLOW).read_text(encoding="utf-8") == _FORCED


@pytest.mark.parametrize("git", [True, False], ids=["git", "no-git"])
def test_is_clean_where_no_project_file_runs_the_flag(tmp_path: Path, git: bool) -> None:
    """The methodology's own tree names the flag in its documentation, and is left out."""
    root = _project(
        tmp_path,
        git=git,
        files={
            _WORKFLOW: "steps:\n  - run: pkit sync\n",
            ".pkit/cli/README.md": "`pkit sync --force` is ignored.\n",
        },
    )

    first, second = _run(root), _run(root)

    for result in (first, second):
        assert result.returncode == 0, result.stderr
        assert "[skip] no project file runs `pkit sync --force`" in result.stdout
        assert result.stderr == ""
