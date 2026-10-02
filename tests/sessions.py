"""Sessions and repositories for the tests of the backbone's cross-repository
guard (`project_kit.session_guard`), on real git.

A command that changes the hosting service compares the session's anchor with
the repository it acts in; these build the two: a git repository with an
`origin`, and a session rooted in one repository while the command runs in
another.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from project_kit import session_guard


def repository(path: Path, origin: str) -> Path:
    """A git repository at `path` whose `origin` is `origin`."""
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", origin], cwd=path, check=True, capture_output=True
    )
    return path


def rooted_elsewhere(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """A session rooted in one repository, and another repository a command
    runs in: (anchor, target). The anchor is set; where the command runs is
    the caller's to say."""
    anchor = repository(tmp_path / "anchor", "https://github.com/octo/project.git")
    target = repository(tmp_path / "target", "https://github.com/octo/other.git")
    monkeypatch.setenv(session_guard.CLAUDE_CODE_ANCHOR, str(anchor))
    return anchor, target
