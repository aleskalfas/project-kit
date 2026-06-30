"""Tests for the foreign-repo mutation self-guard (COR-039 / ADR-034).

The guard lives at
`.pkit/capabilities/project-management/scripts/_lib/session_guard.py` —
capability-internal — and is loaded via `importlib` so the kit's pytest run
catches regressions in the anchor-vs-target comparison every mutating pm
script invokes before it writes.

The safety-relevant cases proven here:
  * same-repo (cwd inside the anchor) → clean pass, no friction;
  * cross-repo (the incident shape: cwd in a DIFFERENT repo than the anchor)
    → the guard fires before the mutation;
  * the override path → a confirmed cross-repo mutation proceeds (operator-
    gated, not a hard wall);
  * residual-gap honesty (`unset CLAUDE_PROJECT_DIR`, non-git cwd) → the guard
    falls back to a documented no-fire, NOT a false "blocked".
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GUARD_PY = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "scripts"
    / "_lib"
    / "session_guard.py"
)


@pytest.fixture(scope="module")
def guard():
    """Load the capability-internal session_guard library by file path."""
    module_name = "pm_session_guard_under_test"
    spec = importlib.util.spec_from_file_location(module_name, GUARD_PY)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )


def _git_init(path: Path) -> None:
    """Make `path` a git repo (just enough for `rev-parse --show-toplevel`)."""
    path.mkdir(parents=True, exist_ok=True)
    _git(["init", "-q"], cwd=path)


def _git_init_with_origin(path: Path, origin_url: str) -> None:
    """A git repo with an `origin` remote set to `origin_url`."""
    _git_init(path)
    _git(["remote", "add", "origin", origin_url], cwd=path)


def _add_worktree(repo: Path, dest: Path) -> None:
    """Add a linked worktree of `repo` at `dest` (needs a commit to branch from)."""
    # A worktree needs at least one commit on the repo to attach to.
    _git(["-c", "user.email=t@t", "-c", "user.name=t", "commit",
          "--allow-empty", "-q", "-m", "init"], cwd=repo)
    _git(["worktree", "add", "-q", str(dest)], cwd=repo)


@pytest.fixture(autouse=True)
def _clear_override_env(monkeypatch):
    """Each test starts with the env override and CI-identity signals cleared."""
    monkeypatch.delenv("PKIT_ALLOW_FOREIGN_REPO", raising=False)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.delenv("PM_INVOKER_LOGIN", raising=False)


# --- evaluate(): the pure anchor-vs-target comparison ----------------------


def test_same_repo_passes_clean(guard, tmp_path):
    """cwd inside the anchor's repo → SAME_REPO, no friction."""
    repo = tmp_path / "A"
    _git_init(repo)
    sub = repo / "nested" / "dir"
    sub.mkdir(parents=True)
    outcome = guard.evaluate(anchor_dir=str(repo), target_cwd=str(sub))
    assert outcome.verdict == guard.SAME_REPO
    assert not outcome.blocks
    assert outcome.anchor_repo == outcome.target_repo


def test_cross_repo_diverges_and_fires(guard, tmp_path):
    """The incident shape: cwd in a DIFFERENT repo than the anchor → DIVERGED.

    `cd /B && <mutate>` leaves the anchor at A; the guard sees A-vs-B and fires
    BEFORE the mutation. This is the original-incident reproduction.
    """
    repo_a = tmp_path / "A"
    repo_b = tmp_path / "B"
    _git_init(repo_a)
    _git_init(repo_b)
    outcome = guard.evaluate(anchor_dir=str(repo_a), target_cwd=str(repo_b))
    assert outcome.verdict == guard.DIVERGED
    assert outcome.blocks
    assert outcome.anchor_repo != outcome.target_repo


def test_override_lets_cross_repo_proceed(guard, tmp_path):
    """The override path: a confirmed cross-repo mutation is OVERRIDDEN, not blocked."""
    repo_a = tmp_path / "A"
    repo_b = tmp_path / "B"
    _git_init(repo_a)
    _git_init(repo_b)
    outcome = guard.evaluate(
        anchor_dir=str(repo_a), target_cwd=str(repo_b), override=True
    )
    assert outcome.verdict == guard.OVERRIDDEN
    assert not outcome.blocks


# --- RF-1: repo IDENTITY, not work-tree path -------------------------------
# These are the disconfirming cases the original path-equality comparison got
# wrong. The fix compares (git-common-dir OR normalised origin URL).


def test_linked_worktree_of_anchor_is_same_repo(guard, tmp_path):
    """A `git worktree` of the session's repo → SAME_REPO (no false DIVERGED).

    Path-equality wrongly DIVERGED here: the worktree has a different toplevel
    path. Identity collapses them on the shared git-common-dir, so the guard
    does NOT fire on legit same-repo work in a linked worktree."""
    repo = tmp_path / "A"
    _git_init(repo)
    worktree = tmp_path / "A-wt"
    _add_worktree(repo, worktree)
    outcome = guard.evaluate(anchor_dir=str(repo), target_cwd=str(worktree))
    assert outcome.verdict == guard.SAME_REPO
    assert not outcome.blocks


def test_second_clone_of_same_remote_is_same_repo(guard, tmp_path):
    """Two clones of the same remote (same origin URL) → SAME_REPO.

    Different common-dirs AND different toplevel paths, so neither path-equality
    nor common-dir alone matches — the normalised origin URL collapses them."""
    repo_a = tmp_path / "A"
    repo_b = tmp_path / "B"
    _git_init_with_origin(repo_a, "https://example.test/org/repo.git")
    # The .git/ trailing-slash variant must normalise to the same identity.
    _git_init_with_origin(repo_b, "https://example.test/org/repo/")
    outcome = guard.evaluate(anchor_dir=str(repo_a), target_cwd=str(repo_b))
    assert outcome.verdict == guard.SAME_REPO
    assert not outcome.blocks


def test_two_different_remotes_diverge(guard, tmp_path):
    """The inverse: two genuinely different remotes → DIVERGED (the real catch)."""
    repo_a = tmp_path / "A"
    repo_b = tmp_path / "B"
    _git_init_with_origin(repo_a, "https://example.test/org/repo-a.git")
    _git_init_with_origin(repo_b, "https://example.test/org/repo-b.git")
    outcome = guard.evaluate(anchor_dir=str(repo_a), target_cwd=str(repo_b))
    assert outcome.verdict == guard.DIVERGED
    assert outcome.blocks


def test_ssh_and_https_clones_of_one_repo_are_same_repo(guard, tmp_path):
    """Transport canonicalisation: the SAME repo fetched over ssh vs https →
    SAME_REPO, not a false DIVERGED.

    The scp-like ssh form `git@github.com:org/repo.git` and the https form
    `https://github.com/org/repo.git` name ONE repo; before transport
    canonicalisation they normalised to different strings and false-DIVERGEd.
    `_normalize_origin_url` now collapses both to `github.com/org/repo`."""
    repo_a = tmp_path / "A"
    repo_b = tmp_path / "B"
    _git_init_with_origin(repo_a, "git@github.com:org/repo.git")
    _git_init_with_origin(repo_b, "https://github.com/org/repo.git")
    outcome = guard.evaluate(anchor_dir=str(repo_a), target_cwd=str(repo_b))
    assert outcome.verdict == guard.SAME_REPO
    assert not outcome.blocks


def test_ssh_vs_https_different_repos_still_diverge(guard, tmp_path):
    """The negative for transport canonicalisation: ssh `org/repo-a` vs https
    `org/repo-b` are DIFFERENT repos and must still DIVERGE (the collapse must
    not over-match across distinct repos sharing a host/owner)."""
    repo_a = tmp_path / "A"
    repo_b = tmp_path / "B"
    _git_init_with_origin(repo_a, "git@github.com:org/repo-a.git")
    _git_init_with_origin(repo_b, "https://github.com/org/repo-b.git")
    outcome = guard.evaluate(anchor_dir=str(repo_a), target_cwd=str(repo_b))
    assert outcome.verdict == guard.DIVERGED
    assert outcome.blocks


def test_normalize_origin_url_canonicalises_transports(guard):
    """Unit-level: the three common remote forms of ONE repo collapse to a
    single `host/owner/repo` identity, while an unrecognised form (a local
    filesystem path) falls back to the conservative strip+casefold."""
    forms = [
        "git@github.com:org/repo.git",         # scp-like ssh
        "ssh://git@github.com/org/repo.git",   # ssh URL
        "https://github.com/org/repo.git",     # https
        "https://github.com/org/repo",         # https, no .git
        "git@github.com:Org/Repo.git",         # casing not significant
    ]
    normalised = {guard._normalize_origin_url(f) for f in forms}
    assert normalised == {"github.com/org/repo"}, normalised

    # Unrecognised forms fall back to strip+casefold (never crash, never less
    # strict) and stay DISTINCT from the canonical transport identity.
    local = guard._normalize_origin_url("/var/git/org/repo.git")
    assert local == "/var/git/org/repo"
    assert local != "github.com/org/repo"


def test_two_no_remote_repos_diverge_on_common_dir(guard, tmp_path):
    """No-origin fallback: two distinct fresh `git init` repos (no origin) →
    DIVERGED on the common-dir comparison alone (no crash on missing remote)."""
    repo_a = tmp_path / "A"
    repo_b = tmp_path / "B"
    _git_init(repo_a)
    _git_init(repo_b)
    outcome = guard.evaluate(anchor_dir=str(repo_a), target_cwd=str(repo_b))
    assert outcome.verdict == guard.DIVERGED


def test_no_remote_repo_worktree_is_same_repo(guard, tmp_path):
    """No-origin fallback, inverse: a worktree of a no-remote repo still matches
    on the common-dir → SAME_REPO (the fallback doesn't over-diverge)."""
    repo = tmp_path / "A"
    _git_init(repo)
    worktree = tmp_path / "A-wt"
    _add_worktree(repo, worktree)
    outcome = guard.evaluate(anchor_dir=str(repo), target_cwd=str(worktree))
    assert outcome.verdict == guard.SAME_REPO


def test_env_override_is_not_honoured(guard, tmp_path, monkeypatch):
    """PKIT_ALLOW_FOREIGN_REPO is NOT honoured (G-2): the session-sticky env
    switch was removed. Only the per-invocation flag confirms — a stale env var
    must NOT silently authorise a cross-repo mutation, so this still DIVERGES."""
    repo_a = tmp_path / "A"
    repo_b = tmp_path / "B"
    _git_init(repo_a)
    _git_init(repo_b)
    monkeypatch.setenv("PKIT_ALLOW_FOREIGN_REPO", "1")
    outcome = guard.evaluate(anchor_dir=str(repo_a), target_cwd=str(repo_b))
    assert outcome.verdict == guard.DIVERGED


# --- residual-gap honesty (ADR-034 point 5) --------------------------------


def test_unset_anchor_is_undetermined_not_blocked(guard, tmp_path):
    """`unset CLAUDE_PROJECT_DIR` → UNDETERMINED (honest no-fire), NOT a block.

    The declared residual gap: with no anchor the guard cannot determine which
    repo the session is rooted in, so it must NOT pretend coverage. This asserts
    the guard does not fabricate a 'blocked' it cannot back.
    """
    repo_b = tmp_path / "B"
    _git_init(repo_b)
    # anchor_dir=None models the unset CLAUDE_PROJECT_DIR env.
    outcome = guard.evaluate(anchor_dir=None, target_cwd=str(repo_b))
    assert outcome.verdict == guard.UNDETERMINED
    assert not outcome.blocks
    assert "CLAUDE_PROJECT_DIR is unset" in outcome.reason


def test_non_git_cwd_is_undetermined(guard, tmp_path):
    """A target cwd that is not inside any git work-tree → UNDETERMINED, no fire."""
    repo_a = tmp_path / "A"
    _git_init(repo_a)
    non_git = tmp_path / "loose"
    non_git.mkdir()
    outcome = guard.evaluate(anchor_dir=str(repo_a), target_cwd=str(non_git))
    assert outcome.verdict == guard.UNDETERMINED
    assert not outcome.blocks


def test_unset_anchor_reads_from_env_when_not_passed(guard, tmp_path, monkeypatch):
    """With no anchor_dir argument, the guard reads CLAUDE_PROJECT_DIR from env."""
    repo_a = tmp_path / "A"
    repo_b = tmp_path / "B"
    _git_init(repo_a)
    _git_init(repo_b)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(repo_a))
    outcome = guard.evaluate(target_cwd=str(repo_b))
    assert outcome.verdict == guard.DIVERGED


# --- enforce(): the gate at the mutation seam ------------------------------


def test_enforce_same_repo_returns_true(guard, tmp_path, capsys):
    """SAME_REPO → proceed (True), silently."""
    repo = tmp_path / "A"
    _git_init(repo)
    assert guard.enforce(anchor_dir=str(repo), target_cwd=str(repo)) is True


def test_enforce_diverged_autonomous_refuses(guard, tmp_path, capsys):
    """Under autonomy (interactive=False), a DIVERGED mutation is refused (False)
    with an explanation — never a silent proceed."""
    repo_a = tmp_path / "A"
    repo_b = tmp_path / "B"
    _git_init(repo_a)
    _git_init(repo_b)
    proceed = guard.enforce(
        anchor_dir=str(repo_a), target_cwd=str(repo_b), interactive=False
    )
    assert proceed is False
    err = capsys.readouterr().err
    assert "cross-repo mutation interlock" in err
    # Honest framing: names it an interlock, not a wall, and offers the two ways out.
    assert "not a security boundary" in err
    assert "--allow-foreign-repo" in err
    assert "COR-039" in err


def test_enforce_diverged_with_override_proceeds(guard, tmp_path, capsys):
    """A confirmed override proceeds (True) with an advisory — operator-gated, not a wall."""
    repo_a = tmp_path / "A"
    repo_b = tmp_path / "B"
    _git_init(repo_a)
    _git_init(repo_b)
    proceed = guard.enforce(
        anchor_dir=str(repo_a),
        target_cwd=str(repo_b),
        override=True,
        interactive=False,
    )
    assert proceed is True
    assert "operator override" in capsys.readouterr().err


def test_enforce_undetermined_proceeds_without_pretending(guard, tmp_path, capsys):
    """UNDETERMINED (unset anchor) → proceed (True). The honest residual-gap
    fallback: the guard does NOT block what it cannot evaluate, and does NOT
    print a false 'blocked'."""
    repo_b = tmp_path / "B"
    _git_init(repo_b)
    proceed = guard.enforce(anchor_dir=None, target_cwd=str(repo_b), interactive=False)
    assert proceed is True
    err = capsys.readouterr().err
    assert "interlock" not in err  # no false refusal printed.


# --- G-1: fault vs honest non-coverage -------------------------------------


def test_fault_classified_undetermined_fault(guard, tmp_path, monkeypatch):
    """A git invocation that fails unexpectedly (anchor set + would-be git cwd)
    → UNDETERMINED with the FAULT flavour, distinct from honest non-coverage."""
    repo_a = tmp_path / "A"
    repo_b = tmp_path / "B"
    _git_init(repo_a)
    _git_init(repo_b)

    def _boom(*a, **k):
        raise guard._GitFault("git rev-parse could not run: simulated")

    monkeypatch.setattr(guard, "_run_git", _boom)
    outcome = guard.evaluate(anchor_dir=str(repo_a), target_cwd=str(repo_b))
    assert outcome.verdict == guard.UNDETERMINED
    assert outcome.undetermined_kind == guard.FAULT
    assert not outcome.blocks


def test_unset_anchor_classified_noncoverage(guard, tmp_path):
    """Unset anchor → UNDETERMINED with the NONCOVERAGE flavour (declared gap)."""
    repo_b = tmp_path / "B"
    _git_init(repo_b)
    outcome = guard.evaluate(anchor_dir=None, target_cwd=str(repo_b))
    assert outcome.verdict == guard.UNDETERMINED
    assert outcome.undetermined_kind == guard.NONCOVERAGE


def test_non_git_cwd_classified_noncoverage(guard, tmp_path):
    """Non-git cwd (clean git non-zero exit, not a fault) → NONCOVERAGE."""
    repo_a = tmp_path / "A"
    _git_init(repo_a)
    non_git = tmp_path / "loose"
    non_git.mkdir()
    outcome = guard.evaluate(anchor_dir=str(repo_a), target_cwd=str(non_git))
    assert outcome.verdict == guard.UNDETERMINED
    assert outcome.undetermined_kind == guard.NONCOVERAGE


def test_enforce_fault_proceeds_and_warns(guard, tmp_path, monkeypatch, capsys):
    """G-1: a FAULT proceeds (True) AND prints a [warning] — a flaky-git failure
    that loses the interlock on a possible cross-repo mutation leaves a trace."""
    repo_a = tmp_path / "A"
    repo_b = tmp_path / "B"
    _git_init(repo_a)
    _git_init(repo_b)

    def _boom(*a, **k):
        raise guard._GitFault("git rev-parse could not run: simulated")

    monkeypatch.setattr(guard, "_run_git", _boom)
    proceed = guard.enforce(
        anchor_dir=str(repo_a), target_cwd=str(repo_b), interactive=False
    )
    assert proceed is True
    err = capsys.readouterr().err
    assert "[warning]" in err
    # It warned, but did NOT print a refusal — the guard proceeded, not blocked.
    assert "[refused]" not in err


def test_enforce_noncoverage_proceeds_silently(guard, tmp_path, capsys):
    """G-1: honest non-coverage (unset anchor) proceeds (True) with NO warning."""
    repo_b = tmp_path / "B"
    _git_init(repo_b)
    proceed = guard.enforce(anchor_dir=None, target_cwd=str(repo_b), interactive=False)
    assert proceed is True
    assert capsys.readouterr().err == ""


def test_enforce_interactive_prompt_yes_proceeds(guard, tmp_path, monkeypatch, capsys):
    """Interactive + a 'y' at the prompt → the per-change confirm proceeds."""
    repo_a = tmp_path / "A"
    repo_b = tmp_path / "B"
    _git_init(repo_a)
    _git_init(repo_b)
    monkeypatch.setattr("builtins.input", lambda *a, **k: "y")
    proceed = guard.enforce(
        anchor_dir=str(repo_a), target_cwd=str(repo_b), interactive=True
    )
    assert proceed is True


def test_enforce_interactive_prompt_no_refuses(guard, tmp_path, monkeypatch):
    """Interactive + anything-but-yes → refused."""
    repo_a = tmp_path / "A"
    repo_b = tmp_path / "B"
    _git_init(repo_a)
    _git_init(repo_b)
    monkeypatch.setattr("builtins.input", lambda *a, **k: "")
    proceed = guard.enforce(
        anchor_dir=str(repo_a), target_cwd=str(repo_b), interactive=True
    )
    assert proceed is False


def test_autonomy_inferred_from_ci_identity(guard, monkeypatch):
    """PM_INVOKER_LOGIN (the CI/agent identity signal) marks autonomy even on a tty."""
    monkeypatch.setenv("PM_INVOKER_LOGIN", "ci-bot")
    assert guard._is_autonomous(None) is True


def test_add_override_argument_registers_flag(guard):
    """The shared argparse helper registers --allow-foreign-repo identically."""
    import argparse

    parser = argparse.ArgumentParser()
    guard.add_override_argument(parser)
    args = parser.parse_args(["--allow-foreign-repo"])
    assert args.allow_foreign_repo is True
    args = parser.parse_args([])
    assert args.allow_foreign_repo is False


# --- WR-1: structural coverage — the guard is wired EVERYWHERE it should be --

_SCRIPTS_DIR = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "scripts"
)

# The EXPLICIT exempt set: pm scripts that do NOT mutate adopter state (no local
# file write, no `gh` create/edit/close/merge/delete/label/board op) and so are
# correctly NOT gated by the foreign-repo guard. Listing them positively (rather
# than inferring "not a mutator" from the absence of a signal) makes the scan
# ASSERTED-TOTAL: any *new* script that is neither in this exempt set nor
# enforces the guard fails the test below — catching a future mutator that wires
# neither half (the gap a one-directional "registered-but-not-enforced" scan
# misses). When a genuinely read-only script is added, add it here with intent;
# when a mutator is added, wire the guard.
_READ_ONLY_EXEMPT = frozenset(
    {
        # State detectors / board-column classifiers (read gh, emit a verdict).
        "detect-backlog.py",
        "detect-done.py",
        "detect-in-progress.py",
        "detect-review.py",
        "detect-todo.py",
        # Transition gates / invariant checks (read-only predicates).
        "gate-checkboxes-ticked.py",
        "gate-pr-merged.py",
        "parent-active-descendant.py",
        "pre-check.py",
        "check-mesh.py",
        "check-doc-mapping.py",
        "validate-issue.py",
        "validate-pr.py",
        # Cascade predicates for the lifecycle fold — both declared READ-ONLY.
        "cascade-members.py",
        "cascade-membership.py",
        # Views / listings.
        "list-workstreams.py",
        "show-issue.py",
        "show-members.py",
        "show-pr.py",
        "show-tree.py",
        "show-workstream.py",
        # adopt-existing only ever writes a DRAFT to an explicit `--out` path
        # (and refuses the live map); it resolves no live write target from cwd,
        # so it sits with the explicit-redirect residual gap, not the
        # accidental-cd shape the guard covers.
        "adopt-existing.py",
    }
)


def _enforces_guard(script: Path) -> bool:
    """True if `script` calls `session_guard.enforce` — directly OR via a `_lib`
    module it imports.

    Leaf scripts like check-criterion / uncheck-criterion delegate their whole
    body (and the guard) to a shared `_lib` runner (criterion_cli), so the call
    isn't in the leaf's own source. Following one level of `from _lib import X` /
    `from _lib.X import ...` covers that without false-flagging them."""
    src = script.read_text()
    if "session_guard.enforce" in src:
        return True
    # Follow one level of _lib imports and look for the enforce call there.
    lib_dir = _SCRIPTS_DIR / "_lib"
    for line in src.splitlines():
        line = line.strip()
        mod = None
        if line.startswith("from _lib import "):
            # e.g. `from _lib import criterion_cli  # noqa`
            mod = line[len("from _lib import "):].split("#", 1)[0].split(" as ")[0]
            mod = mod.split(",")[0].strip()
        elif line.startswith("from _lib."):
            # e.g. `from _lib.criterion_cli import run_criterion_verb`
            mod = line[len("from _lib."):].split(" import ", 1)[0].strip()
        if not mod:
            continue
        lib_file = lib_dir / f"{mod}.py"
        if lib_file.is_file() and "session_guard.enforce" in lib_file.read_text():
            return True
    return False


def test_registering_the_override_implies_enforcing_it():
    """One direction: a script that registers --allow-foreign-repo
    (`session_guard.add_override_argument`) MUST also enforce — advertising an
    override for a gate that never runs is a wiring bug."""
    offenders = []
    for script in sorted(_SCRIPTS_DIR.glob("*.py")):
        src = script.read_text()
        if "add_override_argument" in src and not _enforces_guard(script):
            offenders.append(script.name)
    assert not offenders, (
        "these scripts register --allow-foreign-repo but never call "
        f"session_guard.enforce (gate advertised but not run): {offenders}"
    )


def test_every_mutating_script_enforces_the_guard():
    """The asserted-TOTAL direction (bidirectional scan): partition every pm
    script into {read-only exempt} vs {everything else}, and require everything
    NOT in the exempt set to enforce the foreign-repo guard.

    This is the positive assertion of the mutator set, not just a
    "registered-but-not-enforced" check: a future mutating script that wires
    NEITHER the flag nor the enforce call is caught here (it is neither exempt
    nor enforcing), instead of slipping through unguarded. The exempt set
    (`_READ_ONLY_EXEMPT`) is the deliberately-listed read-only surface."""
    all_scripts = {p.name for p in _SCRIPTS_DIR.glob("*.py")}

    # Guard the guard: a stale name in the exempt set (a script renamed/removed)
    # would silently shrink coverage — fail loudly instead.
    stale = _READ_ONLY_EXEMPT - all_scripts
    assert not stale, f"_READ_ONLY_EXEMPT names scripts that no longer exist: {sorted(stale)}"

    unguarded_mutators = []
    for name in sorted(all_scripts):
        if name in _READ_ONLY_EXEMPT:
            continue
        if not _enforces_guard(_SCRIPTS_DIR / name):
            unguarded_mutators.append(name)
    assert not unguarded_mutators, (
        "these pm scripts are not in the read-only exempt set yet do not enforce "
        "the foreign-repo guard (a mutating script must call session_guard.enforce "
        "before its write — or, if genuinely read-only, be added to "
        f"_READ_ONLY_EXEMPT with intent): {unguarded_mutators}"
    )


def test_read_only_exempt_scripts_really_do_not_enforce():
    """Symmetry check: the exempt set is the genuinely read-only surface — none
    of them should be enforcing the guard (if one starts to, it has become a
    mutator and should leave the exempt set so the total scan covers it)."""
    enforcing_exempt = [
        name
        for name in sorted(_READ_ONLY_EXEMPT)
        if (_SCRIPTS_DIR / name).is_file() and _enforces_guard(_SCRIPTS_DIR / name)
    ]
    assert not enforcing_exempt, (
        "these scripts are listed read-only exempt but DO enforce the guard — "
        "they have become mutators; remove them from _READ_ONLY_EXEMPT so the "
        f"asserted-total mutator scan covers them: {enforcing_exempt}"
    )
