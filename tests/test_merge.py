"""Tests for `pkit merge` (PR-I of the build roadmap)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import click
import pytest

from project_kit import install, merge


@pytest.fixture
def installed_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A git repo with the kit installed; ready for merge."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)

    def _noop(_script: Path, _ctx: install.InstallContext) -> None:
        return None

    monkeypatch.setattr(install, "_run_adapter_primitive", _noop)
    install.install_kit(tmp_path)
    return tmp_path


def test_merge_refuses_when_pkit_dir_missing(tmp_path: Path) -> None:
    with pytest.raises(click.ClickException, match=r"\.pkit/ does not exist"):
        merge.run_merge(tmp_path)


def test_merge_dry_run_reports_without_invoking(installed_target: Path) -> None:
    """A dry-run merge prints `would run` lines and never executes the primitive."""
    invocations: list[Path] = []

    def _spy(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
        invocations.append(Path(args[0]))
        return subprocess.CompletedProcess(args, 0, b"", b"")

    # Patch subprocess.run *inside the merge module*; the spy lets us
    # assert no real shell-out happened in dry-run mode.
    import unittest.mock

    with unittest.mock.patch.object(merge.subprocess, "run", _spy):
        merge.run_merge(installed_target, dry_run=True)

    assert invocations == [], f"dry-run shelled out: {invocations}"


def test_merge_invokes_claude_code_merge_primitive(installed_target: Path) -> None:
    """A real merge invokes the claude-code adapter's merge-settings.sh."""
    invocations: list[Path] = []

    def _spy(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
        invocations.append(Path(args[0]))
        return subprocess.CompletedProcess(args, 0, b"", b"")

    import unittest.mock

    with unittest.mock.patch.object(merge.subprocess, "run", _spy):
        merge.run_merge(installed_target)

    assert len(invocations) == 1
    assert invocations[0].name == "merge-settings.sh"
    assert "claude-code" in str(invocations[0])


def test_merge_with_unknown_target_errors(installed_target: Path) -> None:
    with pytest.raises(click.ClickException, match="no installed adapter matches"):
        merge.run_merge(installed_target, targets=("nonexistent-adapter",))


def test_merge_with_matching_target_runs(installed_target: Path) -> None:
    """Filtering to `claude-code` matches the installed adapter."""
    invocations: list[Path] = []

    def _spy(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
        invocations.append(Path(args[0]))
        return subprocess.CompletedProcess(args, 0, b"", b"")

    import unittest.mock

    with unittest.mock.patch.object(merge.subprocess, "run", _spy):
        merge.run_merge(installed_target, targets=("claude-code",))

    assert len(invocations) == 1
    assert invocations[0].name == "merge-settings.sh"
