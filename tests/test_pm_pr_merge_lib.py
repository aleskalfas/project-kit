"""Tests for `_lib/pr_merge.py` — the merge convention's shared mechanic.

One implementation per rule (#882): `done-work` and `merge-pr` both compose
these three steps rather than carrying a copy. Covers the squash-merge
command (subject = PR title, no `--delete-branch`), the remote ref delete
through the API (including the already-deleted answer), and the best-effort
local cleanup (default branch from config; every failure a warning).
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"


def _load_script(name: str, module_name: str):
    sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(module_name, SCRIPTS_DIR / name)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def lib():
    sys.path.insert(0, str(SCRIPTS_DIR))
    from _lib import pr_merge

    return pr_merge


def _ok(args, **kwargs):
    return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")


# --- one implementation, two verbs -------------------------------------


def test_both_verbs_compose_the_shared_mechanic(lib) -> None:
    """done-work and merge-pr call `_lib.pr_merge`; neither carries its own
    merge / remote-delete / local-cleanup copy."""
    dw = _load_script("done-work.py", "pm_done_work_for_pr_merge_lib")
    mp = _load_script("merge-pr.py", "pm_merge_pr_for_pr_merge_lib")
    assert dw.pr_merge is lib and mp.pr_merge is lib
    for mod in (dw, mp):
        for stale in ("_gh_merge", "_gh_pr_merge", "_gh_delete_remote_branch",
                      "_git_cleanup_local", "_branch_checked_out_worktree"):
            assert not hasattr(mod, stale), f"{mod.__name__} still carries {stale}"


# --- squash_merge ---------------------------------------------------------


def test_squash_merge_has_no_local_delete_branch_half(lib, monkeypatch) -> None:
    """The merge command carries no `--delete-branch`, so gh never needs the
    working tree's current branch and the remote merge cannot be failed by a
    local checkout problem (#878, #587)."""
    captured: list[list[str]] = []

    def fake_gh_run(args, config, **kwargs):
        captured.append(list(args))
        return _ok(args)

    monkeypatch.setattr(lib, "gh_run", fake_gh_run)
    assert lib.squash_merge(42, pr_title="fix: x", admin=False, config={}) is True
    assert captured[0][:4] == ["gh", "pr", "merge", "42"]
    assert "--squash" in captured[0]
    assert "--delete-branch" not in captured[0]
    assert "--admin" not in captured[0]


def test_squash_merge_uses_pr_title_as_subject(lib, monkeypatch) -> None:
    """Regression for #33: GitHub defaults the squash subject to the commit
    message for single-commit PRs, defeating the PR-title type-alignment gate
    (DEC-013). `--subject <PR title>` locks the landed subject to the title —
    verbatim, never a commit-derived subject."""
    pr_title = "fix(pm-permissions): correct enforcement runtime"
    commit_subject = "feat(pm-permissions): implement runtime enforcement"
    captured: list[list[str]] = []

    def fake_gh_run(args, config, **kwargs):
        captured.append(list(args))
        return _ok(args)

    monkeypatch.setattr(lib, "gh_run", fake_gh_run)
    lib.squash_merge(32, pr_title=pr_title, admin=False, config={})
    argv = captured[0]
    assert "--subject" in argv
    landed = argv[argv.index("--subject") + 1]
    assert landed == pr_title
    assert landed != commit_subject


def test_squash_merge_passes_admin(lib, monkeypatch) -> None:
    captured: list[list[str]] = []

    def fake_gh_run(args, config, **kwargs):
        captured.append(list(args))
        return _ok(args)

    monkeypatch.setattr(lib, "gh_run", fake_gh_run)
    lib.squash_merge(42, pr_title="fix: x", admin=True, config={})
    assert captured[0][-1] == "--admin"


def test_squash_merge_threads_config_to_gh_run(lib, monkeypatch) -> None:
    """The adopter config reaches gh_run so DEC-023's host pinning applies."""
    seen: list[dict] = []

    def fake_gh_run(args, config, **kwargs):
        seen.append(config)
        return _ok(args)

    monkeypatch.setattr(lib, "gh_run", fake_gh_run)
    lib.squash_merge(42, pr_title="fix: x", admin=False, config={"gh": {"host": "ghe.example"}})
    assert seen == [{"gh": {"host": "ghe.example"}}]


def test_squash_merge_reports_gh_failure(lib, monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        lib, "gh_run",
        lambda args, config, **kw: subprocess.CompletedProcess(
            args=args, returncode=1, stdout="", stderr="Pull request is not mergeable",
        ),
    )
    assert lib.squash_merge(42, pr_title="fix: x", admin=False, config={}) is False
    err = capsys.readouterr().err
    assert "error: gh pr merge failed (exit 1): Pull request is not mergeable" in err


def test_squash_merge_without_pr_number_is_a_failure(lib, monkeypatch, capsys) -> None:
    monkeypatch.setattr(lib, "gh_run", lambda *a, **k: pytest.fail("gh must not run"))
    assert lib.squash_merge(None, pr_title="fix: x", admin=False, config={}) is False
    assert "no PR number" in capsys.readouterr().err


def test_squash_merge_reports_gh_missing(lib, monkeypatch, capsys) -> None:
    def missing(*a, **k):
        raise FileNotFoundError("gh")

    monkeypatch.setattr(lib, "gh_run", missing)
    assert lib.squash_merge(42, pr_title="fix: x", admin=False, config={}) is False
    assert "`gh` not on PATH" in capsys.readouterr().err


# --- delete_remote_branch -------------------------------------------------


def test_remote_branch_deleted_via_api(lib, monkeypatch, capsys) -> None:
    """The remote head ref is deleted with `gh api -X DELETE` on the repo's
    refs endpoint — no dependency on the local checkout."""
    captured: list[list[str]] = []

    def fake_gh_run(args, config, **kwargs):
        captured.append(list(args))
        return _ok(args)

    monkeypatch.setattr(lib, "gh_run", fake_gh_run)
    lib.delete_remote_branch("fix/42-slug", {}, cross_repository=False)
    assert captured == [[
        "gh", "api", "-X", "DELETE",
        "repos/{owner}/{repo}/git/refs/heads/fix/42-slug",
    ]]
    assert "deleted remote branch fix/42-slug" in capsys.readouterr().out


def test_remote_branch_already_gone_is_not_a_warning(lib, monkeypatch, capsys) -> None:
    """A repository that auto-deletes head branches on merge answers 422
    'Reference does not exist' — reported as already deleted, not warned."""
    monkeypatch.setattr(
        lib, "gh_run",
        lambda args, config, **kw: subprocess.CompletedProcess(
            args=args, returncode=1, stdout="",
            stderr="gh: Reference does not exist (HTTP 422)",
        ),
    )
    lib.delete_remote_branch("fix/42-slug", {}, cross_repository=False)
    out = capsys.readouterr()
    assert "remote branch fix/42-slug already deleted" in out.out
    assert "[warn]" not in out.err


def test_remote_branch_delete_failure_is_a_warning(lib, monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        lib, "gh_run",
        lambda args, config, **kw: subprocess.CompletedProcess(
            args=args, returncode=1, stdout="", stderr="gh: boom (HTTP 500)",
        ),
    )
    lib.delete_remote_branch("fix/42-slug", {}, cross_repository=False)
    err = capsys.readouterr().err
    assert "[warn] could not delete remote branch fix/42-slug: gh: boom (HTTP 500)" in err
    assert "git push origin --delete fix/42-slug" in err


def test_remote_branch_delete_with_gh_missing_is_a_warning(lib, monkeypatch, capsys) -> None:
    """Best-effort in every failure mode (#920): `gh` absent from PATH warns
    and returns normally rather than raising past the already-landed merge."""
    def missing(*a, **k):
        raise FileNotFoundError("gh")

    monkeypatch.setattr(lib, "gh_run", missing)
    assert lib.delete_remote_branch("fix/42-slug", {}, cross_repository=False) is None
    err = capsys.readouterr().err
    assert "[warn] could not delete remote branch fix/42-slug" in err
    assert "`gh` not on PATH" in err
    assert "git push origin --delete fix/42-slug" in err


def test_remote_branch_delete_with_unrunnable_gh_is_a_warning(lib, monkeypatch, capsys) -> None:
    """A `gh` on PATH that cannot be run (not executable, wrong binary) warns
    too -- the helper's contract is that it never raises (#920)."""
    def unrunnable(*a, **k):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(lib, "gh_run", unrunnable)
    assert lib.delete_remote_branch("fix/42-slug", {}, cross_repository=False) is None
    err = capsys.readouterr().err
    assert "`gh` could not be run" in err
    assert "git push origin --delete fix/42-slug" in err

# --- cleanup_local ---------------------------------------------------------


def _fake_git(monkeypatch, lib, *, checkout_stderr="", pull_stderr="", branch_d_stderr=""):
    """Stub `subprocess.run` for the local git steps; a non-empty stderr makes
    that step fail. Returns the argvs seen."""
    seen: list[list[str]] = []

    def fake_run(argv, **kwargs):
        seen.append(list(argv))
        if argv[:2] == ["git", "checkout"] and checkout_stderr:
            return subprocess.CompletedProcess(argv, 128, stdout="", stderr=checkout_stderr)
        if argv[:2] == ["git", "pull"] and pull_stderr:
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr=pull_stderr)
        if argv[:3] == ["git", "branch", "-D"] and branch_d_stderr:
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr=branch_d_stderr)
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(lib.subprocess, "run", fake_run)
    return seen


def test_cleanup_local_sequence_on_the_configured_default_branch(lib, monkeypatch, capsys):
    """checkout <default_branch> → pull --ff-only → branch -D <head>; the
    default branch is the adopter's `default_branch`, not a hardcoded main."""
    seen = _fake_git(monkeypatch, lib)
    lib.cleanup_local("fix/42-slug", {"default_branch": "develop"}, cross_repository=False)
    assert seen == [
        ["git", "checkout", "develop"],
        ["git", "pull", "--ff-only"],
        ["git", "branch", "-D", "fix/42-slug"],
    ]
    assert "[warn]" not in capsys.readouterr().err


def test_cleanup_local_defaults_to_main_when_config_is_silent(lib, monkeypatch):
    seen = _fake_git(monkeypatch, lib)
    lib.cleanup_local("fix/42-slug", {}, cross_repository=False)
    assert seen[0] == ["git", "checkout", "main"]


def test_cleanup_local_checkout_failure_skips_pull_still_deletes(lib, monkeypatch, capsys):
    """A detached HEAD (or a default branch held by another worktree) fails
    the checkout: warn, skip the pull (pulling into whatever IS checked out
    would be wrong), still attempt the branch delete."""
    err_text = "fatal: 'main' is already used by worktree at '/repo/wt-main'"
    seen = _fake_git(monkeypatch, lib, checkout_stderr=err_text)
    lib.cleanup_local("fix/42-slug", {}, cross_repository=False)
    err = capsys.readouterr().err
    assert f"[warn] git checkout main failed: {err_text}" in err
    assert ["git", "pull", "--ff-only"] not in seen
    assert ["git", "branch", "-D", "fix/42-slug"] in seen


def test_cleanup_local_pull_failure_is_a_warning(lib, monkeypatch, capsys):
    seen = _fake_git(monkeypatch, lib, pull_stderr="fatal: Not possible to fast-forward")
    lib.cleanup_local("fix/42-slug", {}, cross_repository=False)
    assert "[warn] git pull failed: fatal: Not possible to fast-forward" in capsys.readouterr().err
    assert ["git", "branch", "-D", "fix/42-slug"] in seen


def test_cleanup_local_branch_delete_failure_is_a_warning(lib, monkeypatch, capsys):
    """The head branch checked out in a worktree (#587) cannot be deleted
    locally — a warning naming git's reason, never an exception."""
    branch_err = "error: cannot delete branch 'fix/42-slug' used by worktree at '/repo/wt-42'"
    _fake_git(monkeypatch, lib, branch_d_stderr=branch_err)
    lib.cleanup_local("fix/42-slug", {}, cross_repository=False)
    assert f"[warn] git branch -D fix/42-slug failed: {branch_err}" in capsys.readouterr().err


def test_delete_remote_branch_never_touches_base_repo_for_a_fork_pr(lib, monkeypatch, capsys):
    """Security (PR #896 review): a fork PR's head name is chosen by the fork's
    author and may name an unrelated base-repository branch. The API delete
    targets the BASE repo, so for a cross-repository PR no gh call is made."""
    calls: list[list[str]] = []
    monkeypatch.setattr(lib, "gh_run", lambda args, config, **kw: calls.append(list(args)) or _ok(args))
    lib.delete_remote_branch("release/1.x", {}, cross_repository=True)
    assert calls == []
    assert "lives in a fork" in capsys.readouterr().out


def test_cleanup_local_never_force_deletes_a_same_named_branch_for_a_fork_pr(lib, monkeypatch):
    """A local branch sharing a fork PR's head name is not that PR's head;
    `git branch -D` would discard its unpushed work, so it is not run."""
    import subprocess
    seen: list[list[str]] = []
    monkeypatch.setattr(lib.subprocess, "run", lambda argv, **kw: seen.append(list(argv)) or subprocess.CompletedProcess(argv, 0, stdout="", stderr=""))
    lib.cleanup_local("release/1.x", {}, cross_repository=True)
    assert ["git", "branch", "-D", "release/1.x"] not in seen
    assert seen[0] == ["git", "checkout", "main"]


def test_cross_repository_is_a_required_keyword(lib):
    """No default: every caller must state whether the PR is cross-repository,
    so a later caller cannot silently reintroduce the fork-PR deletion hole."""
    import inspect
    for fn in (lib.delete_remote_branch, lib.cleanup_local):
        p = inspect.signature(fn).parameters["cross_repository"]
        assert p.kind is inspect.Parameter.KEYWORD_ONLY
        assert p.default is inspect.Parameter.empty

