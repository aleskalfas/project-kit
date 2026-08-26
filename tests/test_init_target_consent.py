"""Tests for `pkit init`'s announce/confirm/guide gate (issues #780, #787).

`pkit init` used to install silently at whatever `find_target_root` resolved —
a git root or install-marked ancestor that could be far above the operator's
current directory (the F11 footgun). #780 added a reason-returning resolver, an
always-on announcement, a confirm before installing anywhere other than CWD, a
non-interactive-stdin refusal, a split-brain refusal, and an already-installed
refusal that points to `pkit sync` (init is one-shot, not idempotent — COR-004).

#787 hardens the resolver itself: the walk-up now structurally *validates* each
`.git` candidate, so a broken/vestigial `.git` on a workspace folder (the F12
bug) is skipped rather than offered as a root; a real repository git *refused*
(dubious ownership) is detected and guided rather than shadowed; the old
"offer to install into the bare-`.git` ancestor" (WALKUP_GIT) is gone; a bare
`--yes` no longer installs at a resolved parent (use `--root` for that,
non-interactively).

The pure resolver (`resolve_init_target` / `find_target_root` /
`scan_pkit_installs`) is tested directly; the CLI gate is tested through
`CliRunner` with `install_kit` stubbed to a spy (the gate is the unit under
test — the install itself is covered by `test_install.py`) and `_stdin_is_tty`
monkeypatched for the interactive paths. The dubious-ownership branch cannot be
provoked with real file ownership in a unit test, so it is driven by stubbing
`install._git_toplevel` / `install._git_accepts` to git's refusal signature.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import cli, install
from project_kit.cli import main
from project_kit.install import (
    InitTargetReason,
    find_target_root,
    resolve_init_target,
    scan_pkit_installs,
)


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


def test_resolve_git_absent_valid_git_file_ancestor_is_subfolder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Git binary absent + a structurally-valid `.git` *file* worktree marker in an
    ancestor folds into GIT_SUBFOLDER (the old WALKUP_GIT reason is gone, #787):
    cwd is inside a real worktree, below its root, so the target is that root."""
    worktree = tmp_path / "wt"
    nested = worktree / "deep"
    nested.mkdir(parents=True)
    (worktree / ".git").write_text("gitdir: /elsewhere/.git/worktrees/foo\n", encoding="utf-8")
    monkeypatch.setenv("PATH", "/nonexistent")
    target, reason = resolve_init_target(nested)
    assert reason == InitTargetReason.GIT_SUBFOLDER
    assert target == worktree.resolve()


def test_resolve_git_absent_valid_git_dir_at_cwd_is_git_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Git binary absent + cwd carries a structurally-valid `.git/` dir → GIT_ROOT.
    Structure alone is authoritative when git cannot arbitrate (#787)."""
    (tmp_path / ".git" / "objects").mkdir(parents=True)
    (tmp_path / ".git" / "refs").mkdir()
    monkeypatch.setenv("PATH", "/nonexistent")
    target, reason = resolve_init_target(tmp_path)
    assert reason == InitTargetReason.GIT_ROOT
    assert target == tmp_path.resolve()


def test_resolve_pkit_install_ancestor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An install-marked `.pkit/` ancestor with no `.git` classifies as PKIT_INSTALL
    (renamed from WALKUP_PKIT, #787)."""
    _mark_install(tmp_path)
    nested = tmp_path / "deep"
    nested.mkdir()
    monkeypatch.setenv("PATH", "/nonexistent")
    target, reason = resolve_init_target(nested)
    assert reason == InitTargetReason.PKIT_INSTALL
    assert target == tmp_path.resolve()


# ---- resolve_init_target: #787 structural validation ------------------------


def _break_git(path: Path) -> None:
    """Give `path` a broken/vestigial `.git` — an empty directory missing the
    `objects/` and `refs/` a real repository carries. Structurally implausible,
    so the validated walk-up skips it (the F12 bug scenario)."""
    (path / ".git").mkdir(parents=True)


def test_resolve_broken_git_workspace_is_skipped_f12(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The F12 bug: a non-git subfolder of a *workspace folder* carrying a
    broken/vestigial `.git` (and no `.pkit/`) must resolve to NONE — install here —
    never to the workspace folder mislabelled a git repository (#787). Git is
    present but declines the broken `.git`; `GIT_CEILING_DIRECTORIES` bounds git's
    own walk so the test is deterministic regardless of TMPDIR's ancestry."""
    workspace = tmp_path / "workspace"
    sub = workspace / "sub"
    sub.mkdir(parents=True)
    _break_git(workspace)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    target, reason = resolve_init_target(sub)
    assert reason == InitTargetReason.NONE
    assert target == sub.resolve()  # install here, NOT the broken-.git workspace


def test_resolve_broken_git_skipped_reaches_valid_pkit_ancestor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A broken `.git` between cwd and a real `.pkit/` install does not shadow it:
    the walk skips the broken marker and resolves the install (#787)."""
    _mark_install(tmp_path)
    workspace = tmp_path / "workspace"
    sub = workspace / "sub"
    sub.mkdir(parents=True)
    _break_git(workspace)
    monkeypatch.setenv("PATH", "/nonexistent")  # force the walk-up
    target, reason = resolve_init_target(sub)
    assert reason == InitTargetReason.PKIT_INSTALL
    assert target == tmp_path.resolve()


def test_resolve_dubious_ownership(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A structurally-real repository git refuses to verify (dubious ownership):
    both `rev-parse` from cwd and the per-candidate `git -C` return non-zero, but
    the `.git` is structurally valid → DUBIOUS_OWNERSHIP, not NONE (#787). Real
    file-ownership refusal cannot be provoked in a unit test, so git's refusal
    signature is stubbed."""
    _git_init(tmp_path)  # a structurally-real .git
    monkeypatch.setattr(install, "_git_toplevel", lambda cwd: None)  # git declines from cwd
    monkeypatch.setattr(install, "_git_accepts", lambda cand: False)  # and refuses the candidate
    target, reason = resolve_init_target(tmp_path)
    assert reason == InitTargetReason.DUBIOUS_OWNERSHIP
    assert target == tmp_path.resolve()


# ---- find_target_root: the shared correctness floor (#787) -------------------


def test_find_target_root_rejects_broken_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The floor fix: `find_target_root` no longer resolves a broken/vestigial
    `.git` — a workspace folder that git cannot vouch for is not a project root
    (#787). Read-only callers get None (not a project tree) rather than a bogus
    root."""
    workspace = tmp_path / "workspace"
    sub = workspace / "sub"
    sub.mkdir(parents=True)
    _break_git(workspace)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    assert find_target_root(sub) is None


def test_find_target_root_resolves_pkit_install_no_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A `.pkit/`-marked no-git project still resolves — that path never depended
    on `.git` (#787 preserves it)."""
    _mark_install(tmp_path)
    nested = tmp_path / "deep"
    nested.mkdir()
    monkeypatch.setenv("PATH", "/nonexistent")
    assert find_target_root(nested) == tmp_path.resolve()


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
    """A piped `yes | pkit init` must NOT auto-confirm an off-CWD target. The
    refusal now points at --root (the sanctioned non-interactive install-at-parent
    path) and --here, not at --yes (which no longer installs off-cwd, #787)."""
    _git_init(tmp_path)
    sub = tmp_path / "sub"
    sub.mkdir()
    monkeypatch.chdir(sub)
    set_tty(False)  # piped / non-interactive stdin
    result = CliRunner().invoke(main, ["init"], input="y\n")
    assert result.exit_code != 0
    assert "--root" in result.output and "--here" in result.output
    assert spy_install == []


# ---- CLI gate: already installed → refuse, point to sync (#5) ---------------


def test_init_pkit_install_already_installed_refuses_pointing_to_sync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spy_install
) -> None:
    # `init` is one-shot, not idempotent (COR-004): a second run on an already-
    # installed target refuses (non-zero) with a message pointing at `pkit sync`.
    # This is the PKIT_INSTALL-ancestor redirect (#787) when the ancestor is cwd.
    _mark_install(tmp_path)  # target already a pkit project
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", "/nonexistent")  # force the PKIT_INSTALL reason
    result = CliRunner().invoke(main, ["init"])
    assert result.exit_code != 0
    assert "already a project-kit project" in result.output
    assert "pkit sync" in result.output
    assert spy_install == []  # refused before any install or confirm


def test_init_pkit_install_ancestor_below_refuses_pointing_to_sync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spy_install
) -> None:
    """From a subfolder of an already-adopted (no-git) project, init refuses and
    redirects to `pkit sync` rather than offering a nested create (#787)."""
    _mark_install(tmp_path)
    sub = tmp_path / "sub"
    sub.mkdir()
    monkeypatch.chdir(sub)
    monkeypatch.setenv("PATH", "/nonexistent")  # force the walk-up to the PKIT_INSTALL ancestor
    result = CliRunner().invoke(main, ["init"])
    assert result.exit_code != 0
    assert "already a project-kit project" in result.output
    assert "pkit sync" in result.output
    assert spy_install == []


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


def test_init_off_target_split_brain_yes_alone_still_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spy_install
) -> None:
    """A bare --yes no longer overrides the split-brain refusal — the override is
    now the explicit --root, which never installs off-cwd silently (#787)."""
    _git_init(tmp_path)
    mid = tmp_path / "mid"
    deep = mid / "deep"
    deep.mkdir(parents=True)
    _mark_install(mid)
    monkeypatch.chdir(deep)
    result = CliRunner().invoke(main, ["init", "--yes"])
    assert result.exit_code != 0
    assert "split-brain" in result.output
    assert "--root" in result.output
    assert spy_install == []


def test_init_off_target_install_honoured_with_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spy_install
) -> None:
    """An explicit --root naming the git root installs there, overriding the
    split-brain guard (the operator named the target unambiguously, #787)."""
    _git_init(tmp_path)
    mid = tmp_path / "mid"
    deep = mid / "deep"
    deep.mkdir(parents=True)
    _mark_install(mid)
    monkeypatch.chdir(deep)
    result = CliRunner().invoke(main, ["init", "--root", str(tmp_path)])
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


def test_init_here_in_pkit_install_ancestor_targets_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spy_install
) -> None:
    """--here is an explicit operator instruction, so it is honored even under a
    PKIT_INSTALL ancestor (no git repo, an install-marked ancestor above CWD): with
    no git-root-wins precedence, a .pkit/ at CWD is reachable, so --here installs a
    standalone at CWD. The refuse-and-redirect for PKIT_INSTALL governs the *default*
    guided flow, not this explicit --here (#787)."""
    _mark_install(tmp_path)  # install-marked ancestor, no .git
    nested = tmp_path / "deep"
    nested.mkdir()
    monkeypatch.chdir(nested)
    monkeypatch.setenv("PATH", "/nonexistent")  # force the PKIT_INSTALL reason
    # Precondition: resolver classifies this as PKIT_INSTALL (not git-subfolder).
    _, reason = resolve_init_target(nested)
    assert reason == InitTargetReason.PKIT_INSTALL
    result = CliRunner().invoke(main, ["init", "--here"])
    assert result.exit_code == 0, result.output
    assert "--here refused" not in result.output
    assert spy_install == [(nested.resolve(), False)]  # standalone install at CWD


# ---- CLI gate: --yes / --dry-run overrides (#7) -----------------------------


def test_init_yes_in_subfolder_refuses_off_cwd_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spy_install, set_tty
) -> None:
    """A bare --yes must NEVER install at a resolved parent (the CI footgun #787
    closes): from a git subfolder it refuses and points at --root, rather than
    silently installing at the git root."""
    _git_init(tmp_path)
    sub = tmp_path / "sub"
    sub.mkdir()
    monkeypatch.chdir(sub)
    set_tty(False)
    result = CliRunner().invoke(main, ["init", "--yes"])
    assert result.exit_code != 0
    assert "--yes will not install" in result.output
    assert "--root" in result.output
    assert spy_install == []


def test_init_root_installs_at_explicit_target_non_interactively(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spy_install, set_tty
) -> None:
    """--root is the sanctioned non-interactive install-at-parent path: from a git
    subfolder it installs at the named git root with no prompt (#787)."""
    _git_init(tmp_path)
    sub = tmp_path / "sub"
    sub.mkdir()
    monkeypatch.chdir(sub)
    set_tty(False)  # non-interactive: --root carries it through
    result = CliRunner().invoke(main, ["init", "--root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "Install project-kit into" not in result.output  # no confirm
    assert "--root" in result.output  # announced as an explicit target
    assert spy_install == [(tmp_path.resolve(), False)]


def test_init_yes_accepts_non_git_offer_at_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spy_install, set_tty
) -> None:
    """--yes still accepts the install-here offer for a target that IS the current
    directory (a fresh non-git folder) — that is never off-cwd, so it is safe."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", "/nonexistent")  # non-git folder (NONE)
    set_tty(False)
    result = CliRunner().invoke(main, ["init", "--yes"])
    assert result.exit_code == 0, result.output
    assert "Install project-kit into" not in result.output  # skipped the confirm
    assert spy_install == [(tmp_path.resolve(), False)]


def test_init_here_and_root_are_mutually_exclusive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spy_install
) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["init", "--here", "--root", str(tmp_path)])
    assert result.exit_code != 0
    assert "not both" in result.output
    assert spy_install == []


def test_init_root_at_already_installed_redirects_to_sync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spy_install
) -> None:
    """--root pointing at an existing install redirects to `pkit sync`, not a
    re-init (COR-004 one-shot)."""
    _mark_install(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["init", "--root", str(tmp_path)])
    assert result.exit_code != 0
    assert "already a project-kit project" in result.output
    assert "pkit sync" in result.output
    assert spy_install == []


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


# ---- CLI gate: #787 broken-.git (F12) and dubious ownership ------------------


def test_init_broken_git_workspace_installs_here_not_parent_f12(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spy_install, set_tty
) -> None:
    """The F12 incident, end to end: from a non-git subfolder of a workspace folder
    whose `.git` is broken/vestigial, init offers to install HERE — never at the
    workspace folder, and never calling it a "git repository" (#787)."""
    workspace = tmp_path / "workspace"
    sub = workspace / "sub"
    sub.mkdir(parents=True)
    (workspace / ".git").mkdir()  # broken/vestigial — no objects/ or refs/
    monkeypatch.chdir(sub)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    set_tty(True)
    result = CliRunner().invoke(main, ["init"], input="y\n")
    assert result.exit_code == 0, result.output
    assert spy_install == [(sub.resolve(), False)]  # HERE, not the workspace folder
    # The announced target is the subfolder itself, not the broken-.git parent
    # (workspace is a path *prefix* of sub, so assert the exact resolved-target line).
    assert f"pkit init -> {sub.resolve()}" in result.output
    # The correct NONE phrasing ("no git repository found above it") stands; the old
    # bug's mislabel ("nearest git repository above your current directory") is gone.
    assert "no git repository found above it" in result.output
    assert "above your current directory" not in result.output


def test_init_dubious_ownership_guides_without_installing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spy_install, set_tty
) -> None:
    """A structurally-real repo git refused (dubious ownership) is guided, never
    shadowed: init refuses, names the safe.directory remedy and the --root escape,
    and installs nothing (#787). Git's refusal signature is stubbed (real ownership
    refusal is not reproducible in a unit test)."""
    _git_init(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(install, "_git_toplevel", lambda cwd: None)
    monkeypatch.setattr(install, "_git_accepts", lambda cand: False)
    set_tty(True)
    result = CliRunner().invoke(main, ["init"], input="y\n")
    assert result.exit_code != 0
    assert "safe.directory" in result.output
    assert "--root" in result.output
    assert spy_install == []
