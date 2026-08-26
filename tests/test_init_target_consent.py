"""Tests for `pkit init`'s announce-and-confirm gate (issue #780).

`pkit init` used to install silently at whatever `find_target_root` resolved —
a git root or install-marked ancestor that could be far above the operator's
current directory (the F11 footgun). These tests cover the hardened behaviour:
a reason-returning target resolver, an always-on announcement, a confirm before
installing anywhere other than CWD, a hard refusal on a non-interactive stdin,
a split-brain refusal, an already-installed refusal that points to `pkit sync`
(init is one-shot, not idempotent — COR-004), and the `--here` / `--yes`
overrides.

The pure resolver (`resolve_init_target` / `scan_pkit_installs`) is tested
directly; the CLI gate is tested through `CliRunner` with `install_kit` stubbed
to a spy (the gate is the unit under test — the install itself is covered by
`test_install.py`) and `_stdin_is_tty` monkeypatched for the interactive paths.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import cli
from project_kit.cli import main
from project_kit.install import InitTargetReason, resolve_init_target, scan_pkit_installs


def _git_init(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)


def _mark_install(path: Path) -> None:
    """Make `path/.pkit/` a real install per `looks_like_pkit_install`."""
    pkit = path / ".pkit"
    pkit.mkdir(parents=True, exist_ok=True)
    (pkit / "manifest.yaml").write_text("backbone_version: 1.0.0\n", encoding="utf-8")


@pytest.fixture
def spy_install(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Path, bool]]:
    """Replace `cli.install_kit` with a recorder of (target, dry_run) calls."""
    calls: list[tuple[Path, bool]] = []

    def _spy(target: Path, dry_run: bool = False) -> None:
        calls.append((Path(target), dry_run))

    monkeypatch.setattr(cli, "install_kit", _spy)
    return calls


@pytest.fixture
def set_tty(monkeypatch: pytest.MonkeyPatch):
    """Control what `pkit init` sees for `sys.stdin.isatty()`."""

    def _apply(value: bool) -> None:
        monkeypatch.setattr(cli, "_stdin_is_tty", lambda: value)

    return _apply


# ---- resolve_init_target: classification ------------------------------------


def test_resolve_git_root(tmp_path: Path) -> None:
    _git_init(tmp_path)
    target, reason = resolve_init_target(tmp_path)
    assert reason == InitTargetReason.GIT_ROOT
    assert target == tmp_path.resolve()


def test_resolve_git_subfolder(tmp_path: Path) -> None:
    _git_init(tmp_path)
    sub = tmp_path / "pkg" / "deep"
    sub.mkdir(parents=True)
    target, reason = resolve_init_target(sub)
    assert reason == InitTargetReason.GIT_SUBFOLDER
    assert target == tmp_path.resolve()  # the git root, not the subfolder


def test_resolve_none_when_no_repo_and_no_git_binary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATH", "/nonexistent")  # force git to be unresolvable
    target, reason = resolve_init_target(tmp_path)
    assert reason == InitTargetReason.NONE
    assert target == tmp_path.resolve()  # target is CWD, not None (#780 case d)


def test_resolve_walkup_git_recognises_worktree_git_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A `.git` *file* worktree marker counts in the git-less walk-up."""
    worktree = tmp_path / "wt"
    nested = worktree / "deep"
    nested.mkdir(parents=True)
    (worktree / ".git").write_text("gitdir: /elsewhere/.git/worktrees/foo\n", encoding="utf-8")
    monkeypatch.setenv("PATH", "/nonexistent")
    target, reason = resolve_init_target(nested)
    assert reason == InitTargetReason.WALKUP_GIT
    assert target == worktree.resolve()


def test_resolve_walkup_pkit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An install-marked `.pkit/` ancestor with no `.git` classifies as walkup-pkit."""
    _mark_install(tmp_path)
    nested = tmp_path / "deep"
    nested.mkdir()
    monkeypatch.setenv("PATH", "/nonexistent")
    target, reason = resolve_init_target(nested)
    assert reason == InitTargetReason.WALKUP_PKIT
    assert target == tmp_path.resolve()


# ---- scan_pkit_installs ------------------------------------------------------


def test_scan_finds_install_between_cwd_and_target(tmp_path: Path) -> None:
    mid = tmp_path / "mid"
    deep = mid / "deep"
    deep.mkdir(parents=True)
    _mark_install(mid)
    found = scan_pkit_installs(deep, tmp_path)
    assert [p.resolve() for p in found] == [mid.resolve()]


def test_scan_finds_install_at_target(tmp_path: Path) -> None:
    _mark_install(tmp_path)
    sub = tmp_path / "sub"
    sub.mkdir()
    found = scan_pkit_installs(sub, tmp_path)
    assert [p.resolve() for p in found] == [tmp_path.resolve()]


def test_scan_ignores_bare_pkit_dir(tmp_path: Path) -> None:
    """A bare `.pkit/` (no manifest / decisions) is junk, not an install."""
    (tmp_path / "mid" / ".pkit").mkdir(parents=True)
    deep = tmp_path / "mid" / "deep"
    deep.mkdir()
    assert scan_pkit_installs(deep, tmp_path) == []


# ---- CLI gate: git-root happy path (#8) -------------------------------------


def test_init_git_root_no_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spy_install, set_tty
) -> None:
    _git_init(tmp_path)
    monkeypatch.chdir(tmp_path)
    set_tty(True)  # even with a tty, git-root must not prompt
    result = CliRunner().invoke(main, ["init"])
    assert result.exit_code == 0, result.output
    assert spy_install == [(tmp_path.resolve(), False)]
    assert "pkit init ->" in result.output
    assert "Install project-kit into" not in result.output  # no confirm question


# ---- CLI gate: git-subfolder confirm (#4) -----------------------------------


def test_init_git_subfolder_confirm_accept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spy_install, set_tty
) -> None:
    _git_init(tmp_path)
    sub = tmp_path / "sub"
    sub.mkdir()
    monkeypatch.chdir(sub)
    set_tty(True)
    result = CliRunner().invoke(main, ["init"], input="y\n")
    assert result.exit_code == 0, result.output
    assert "Install project-kit into" in result.output
    assert spy_install == [(tmp_path.resolve(), False)]  # installs at the git root


def test_init_git_subfolder_confirm_decline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spy_install, set_tty
) -> None:
    _git_init(tmp_path)
    sub = tmp_path / "sub"
    sub.mkdir()
    monkeypatch.chdir(sub)
    set_tty(True)
    result = CliRunner().invoke(main, ["init"], input="n\n")
    assert result.exit_code == 0, result.output
    assert "Aborted." in result.output
    assert spy_install == []


def test_init_git_subfolder_non_tty_refuses_even_with_piped_yes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spy_install, set_tty
) -> None:
    """A piped `yes | pkit init` must NOT auto-confirm an off-CWD target."""
    _git_init(tmp_path)
    sub = tmp_path / "sub"
    sub.mkdir()
    monkeypatch.chdir(sub)
    set_tty(False)  # piped / non-interactive stdin
    result = CliRunner().invoke(main, ["init"], input="y\n")
    assert result.exit_code != 0
    assert "--yes" in result.output and "--here" in result.output
    assert spy_install == []


# ---- CLI gate: already installed → refuse, point to sync (#5) ---------------


def test_init_walkup_pkit_already_installed_refuses_pointing_to_sync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spy_install
) -> None:
    # `init` is one-shot, not idempotent (COR-004): a second run on an already-
    # installed target refuses (non-zero) with a message pointing at `pkit sync`.
    _mark_install(tmp_path)  # target already a pkit project
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", "/nonexistent")  # force the walkup-pkit reason
    result = CliRunner().invoke(main, ["init"])
    assert result.exit_code != 0
    assert "already a project-kit project" in result.output
    assert "pkit sync" in result.output
    assert spy_install == []  # refused before any install or confirm


# ---- CLI gate: off-target install between CWD and target → refuse (#3) -------


def test_init_off_target_install_refuses_split_brain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spy_install
) -> None:
    _git_init(tmp_path)  # git root = tmp_path, has no .pkit
    mid = tmp_path / "mid"
    deep = mid / "deep"
    deep.mkdir(parents=True)
    _mark_install(mid)  # install straddling CWD and the resolved git root
    monkeypatch.chdir(deep)
    result = CliRunner().invoke(main, ["init"])
    assert result.exit_code != 0
    assert str(mid.resolve()) in result.output  # names the found install
    assert str(tmp_path.resolve()) in result.output  # names the target
    assert spy_install == []


def test_init_off_target_install_honoured_with_yes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spy_install
) -> None:
    _git_init(tmp_path)
    mid = tmp_path / "mid"
    deep = mid / "deep"
    deep.mkdir(parents=True)
    _mark_install(mid)
    monkeypatch.chdir(deep)
    result = CliRunner().invoke(main, ["init", "--yes"])
    assert result.exit_code == 0, result.output
    assert spy_install == [(tmp_path.resolve(), False)]


# ---- CLI gate: --here (#6) ---------------------------------------------------


def test_init_here_in_git_subfolder_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spy_install
) -> None:
    _git_init(tmp_path)
    sub = tmp_path / "sub"
    sub.mkdir()
    monkeypatch.chdir(sub)
    result = CliRunner().invoke(main, ["init", "--here"])
    assert result.exit_code != 0
    assert "--here refused" in result.output
    assert str(tmp_path.resolve()) in result.output  # points at the git root
    assert spy_install == []


def test_init_here_in_non_git_dir_targets_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spy_install
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", "/nonexistent")  # not in a git repo (no git binary)
    result = CliRunner().invoke(main, ["init", "--here"])
    assert result.exit_code == 0, result.output
    assert spy_install == [(tmp_path.resolve(), False)]  # target is CWD, no prompt


def test_init_here_in_walkup_pkit_targets_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spy_install
) -> None:
    """--here is honored in a walk-up-pkit topology (no git repo, an install-marked
    ancestor above CWD): with no git-root-wins precedence, a .pkit/ at CWD is
    reachable, so --here installs a standalone at CWD rather than being refused."""
    _mark_install(tmp_path)  # install-marked ancestor, no .git
    nested = tmp_path / "deep"
    nested.mkdir()
    monkeypatch.chdir(nested)
    monkeypatch.setenv("PATH", "/nonexistent")  # force the walkup-pkit reason
    # Precondition: resolver classifies this as walkup-pkit (not git-subfolder).
    _, reason = resolve_init_target(nested)
    assert reason == InitTargetReason.WALKUP_PKIT
    result = CliRunner().invoke(main, ["init", "--here"])
    assert result.exit_code == 0, result.output
    assert "--here refused" not in result.output
    assert spy_install == [(nested.resolve(), False)]  # standalone install at CWD


# ---- CLI gate: --yes / --dry-run overrides (#7) -----------------------------


def test_init_yes_accepts_non_interactively(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spy_install, set_tty
) -> None:
    _git_init(tmp_path)
    sub = tmp_path / "sub"
    sub.mkdir()
    monkeypatch.chdir(sub)
    set_tty(False)  # non-interactive: --yes must carry it through
    result = CliRunner().invoke(main, ["init", "--yes"])
    assert result.exit_code == 0, result.output
    assert "Install project-kit into" not in result.output  # skipped the confirm
    assert spy_install == [(tmp_path.resolve(), False)]


def test_init_dry_run_skips_confirm_even_when_non_tty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spy_install, set_tty
) -> None:
    _git_init(tmp_path)
    sub = tmp_path / "sub"
    sub.mkdir()
    monkeypatch.chdir(sub)
    set_tty(False)  # would refuse if the confirm gate were reached
    result = CliRunner().invoke(main, ["init", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert spy_install == [(tmp_path.resolve(), True)]  # dry_run=True, no refusal


# ---- CLI gate: non-git folder (case d, #9) ----------------------------------


def test_init_non_git_folder_confirm_offer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spy_install, set_tty
) -> None:
    """A fresh non-git folder announces + offers to init here (behind the confirm),
    rather than hard-refusing with the old cryptic message."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", "/nonexistent")
    set_tty(True)
    result = CliRunner().invoke(main, ["init"], input="y\n")
    assert result.exit_code == 0, result.output
    assert "no git repository found above it" in result.output
    assert spy_install == [(tmp_path.resolve(), False)]
