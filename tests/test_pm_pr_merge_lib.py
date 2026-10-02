"""Tests for `_lib/pr_merge.py` — the merge convention's shared mechanic.

One implementation per rule (#882): `done-work` and `merge-pr` both compose
these three steps rather than carrying a copy. Covers the squash-merge
command (subject = PR title, no `--delete-branch`), the head branch's deletion
on GitHub, asked of the backbone at the head that merged and said in one line
whatever it comes to (#1255), and the best-effort local cleanup (the default
branch the backbone declares, COR-054; every failure a warning).
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tests import pull_request_backbone

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
        for stale in (
            "_gh_merge",
            "_gh_pr_merge",
            "_gh_delete_remote_branch",
            "_git_cleanup_local",
            "_branch_checked_out_worktree",
        ):
            assert not hasattr(mod, stale), f"{mod.__name__} still carries {stale}"


# --- squash_merge ---------------------------------------------------------


def _backbone_gh(monkeypatch, lib, fake_gh_run) -> None:
    """The merge requests are the backbone's (`pkit pull-request`): run it in this
    process, its `gh` answered by `fake_gh_run(args, config)`."""
    pull_request_backbone.in_process(
        monkeypatch, lib.merge_queue, gh=lambda argv: fake_gh_run(list(argv), {})
    )


def test_squash_merge_has_no_local_delete_branch_half(lib, monkeypatch) -> None:
    """The merge command carries no `--delete-branch`, so gh never needs the
    working tree's current branch and the remote merge cannot be failed by a
    local checkout problem (#878, #587)."""
    captured: list[list[str]] = []

    def fake_gh_run(args, config, **kwargs):
        captured.append(list(args))
        return _ok(args)

    _backbone_gh(monkeypatch, lib, fake_gh_run)
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

    _backbone_gh(monkeypatch, lib, fake_gh_run)
    lib.squash_merge(32, pr_title=pr_title, admin=False, config={})
    argv = captured[0]
    assert "--subject" in argv
    landed = argv[argv.index("--subject") + 1]
    assert landed == pr_title
    assert landed != commit_subject


def test_squash_merge_pins_the_checked_head(lib, monkeypatch) -> None:
    """A caller that names the head its gate checked has the merge pinned to
    it, so a push in between fails the merge; without one nothing is pinned."""
    captured: list[list[str]] = []

    def fake_gh_run(args, config, **kwargs):
        captured.append(list(args))
        return _ok(args)

    _backbone_gh(monkeypatch, lib, fake_gh_run)
    lib.squash_merge(42, pr_title="fix: x", admin=False, config={}, head_oid="a" * 40)
    lib.squash_merge(42, pr_title="fix: x", admin=False, config={})
    pinned, unpinned = captured
    assert pinned[pinned.index("--match-head-commit") + 1] == "a" * 40
    assert "--match-head-commit" not in unpinned


def test_squash_merge_passes_admin(lib, monkeypatch) -> None:
    captured: list[list[str]] = []

    def fake_gh_run(args, config, **kwargs):
        captured.append(list(args))
        return _ok(args)

    _backbone_gh(monkeypatch, lib, fake_gh_run)
    lib.squash_merge(42, pr_title="fix: x", admin=True, config={})
    assert captured[0][-1] == "--admin"


# --- enqueue (#1011) -------------------------------------------------------


def test_enqueue_is_auto_pinned_to_the_checked_head_and_nothing_else(lib, monkeypatch) -> None:
    """The queue gets the PR pinned to the head the gate checked, with `--auto`.
    No `--squash` and no `--subject`: GitHub ignores a merge method, subject and
    body passed with a queued merge, so the queue's method and the repository's
    squash-commit defaults are checked instead (`queue_refusal`). Never
    `--admin`, which on a queued base merges around the queue."""
    captured: list[list[str]] = []

    def fake_gh_run(args, config, **kwargs):
        captured.append(list(args))
        return _ok(args)

    _backbone_gh(monkeypatch, lib, fake_gh_run)
    assert lib.enqueue(42, config={}, head_oid="a" * 40) is True
    assert captured[0] == ["gh", "pr", "merge", "42", "--auto", "--match-head-commit", "a" * 40]


_HEAD_MODIFIED = (
    "GraphQL: Head branch was modified. Review and try the merge again. (mergePullRequest)"
)


def test_a_refused_enqueue_reports_gh_and_returns_false(lib, monkeypatch, capsys) -> None:
    def refusing(args, config, **kwargs):
        return subprocess.CompletedProcess(args, 1, stdout="", stderr=_HEAD_MODIFIED)

    _backbone_gh(monkeypatch, lib, refusing)
    assert lib.enqueue(42, config={}) is False
    assert _HEAD_MODIFIED in capsys.readouterr().err


def test_squash_merge_threads_config_to_the_backbone(lib, monkeypatch) -> None:
    """The adopter config reaches the backbone's request, which runs `pkit
    pull-request` in the `gh` environment the config pins (DEC-023)."""
    seen: list[dict] = []

    def request(args, config):
        seen.append(config)
        return lib.merge_queue.Outcome(True, 0, "")

    monkeypatch.setattr(lib.merge_queue, "request", request)
    lib.squash_merge(42, pr_title="fix: x", admin=False, config={"gh": {"host": "ghe.example"}})
    assert seen == [{"gh": {"host": "ghe.example"}}]


def test_squash_merge_reports_gh_failure(lib, monkeypatch, capsys) -> None:
    _backbone_gh(
        monkeypatch,
        lib,
        lambda args, config, **kw: subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="",
            stderr="GraphQL: Pull request is not mergeable (mergePullRequest)",
        ),
    )
    assert lib.squash_merge(42, pr_title="fix: x", admin=False, config={}) is False
    err = capsys.readouterr().err
    assert (
        "error: gh pr merge failed (exit 1): GraphQL: Pull request is not mergeable "
        "(mergePullRequest)"
    ) in err


def test_squash_merge_without_pr_number_is_a_failure(lib, monkeypatch, capsys) -> None:
    _backbone_gh(monkeypatch, lib, lambda *a, **k: pytest.fail("gh must not run"))
    assert lib.squash_merge(None, pr_title="fix: x", admin=False, config={}) is False
    assert "no PR number" in capsys.readouterr().err


def test_squash_merge_reports_gh_missing(lib, monkeypatch, capsys) -> None:
    def missing(*a, **k):
        raise FileNotFoundError("gh")

    _backbone_gh(monkeypatch, lib, missing)
    assert lib.squash_merge(42, pr_title="fix: x", admin=False, config={}) is False
    assert "`gh` not on PATH" in capsys.readouterr().err


# --- delete_branch: the backbone's deletion (#1255) ----------------------


def _deletion(
    outcome: str,
    *,
    branch: str | None = "fix/42-slug",
    tip: str | None = None,
    reason_kind: str | None = None,
    reason: str | None = None,
    merged_head: str | None = "sha-merged",
) -> dict[str, Any]:
    """`pkit pull-request delete-branch`'s document."""
    return {
        "schema_version": 1,
        "pull_request": 42,
        "expected": "sha-merged",
        "outcome": outcome,
        "branch": branch,
        "tip": tip,
        "reason_kind": reason_kind,
        "reason": reason,
        "merged_head": merged_head,
        "guard": {
            "verdict": "same-repo",
            "undetermined_kind": None,
            "anchor": "/work/project",
            "target": "/work/project",
            "cleared": "same-repo",
        },
    }


def _backbone_answers(monkeypatch, lib, *documents: dict[str, Any]) -> list[list[str]]:
    """The backbone's seam (`merge_queue._answers`) answering each call with
    `documents`; the subcommands asked, in order."""
    asked: list[list[str]] = []

    def answers(args, config, *, timeout_seconds=None):
        asked.append(list(args))
        yield from documents

    monkeypatch.setattr(lib.merge_queue, "_answers", answers)
    return asked


_LATER = "To delete it later: `pkit pull-request delete-branch 42 --expect sha-merged`."


@pytest.mark.parametrize("confirmed", [False, True], ids=["unconfirmed", "allow-foreign-repo"])
def test_the_head_branch_is_deleted_by_the_backbone_at_the_head_that_merged(
    lib, monkeypatch, capsys, confirmed
) -> None:
    """The deletion is the backbone's (`pkit pull-request delete-branch`),
    asked for at the head the PR merged at, with the operator's confirmation
    passed on as the merge's is; nothing here asks GitHub itself. What it
    came to is answered, for the local clean-up."""
    asked = _backbone_answers(monkeypatch, lib, _deletion("deleted"))
    assert lib.delete_branch(42, "sha-merged", {}, allow_foreign_repo=confirmed) == "deleted"
    assert asked == [
        ["delete-branch", "42", "--expect", "sha-merged", *(["--allow-foreign-repo"] * confirmed)]
    ]
    assert capsys.readouterr().out == "  deleted remote branch fix/42-slug\n"


@pytest.mark.parametrize(
    ("document", "said"),
    [
        (_deletion("gone"), "  remote branch fix/42-slug is not there; nothing to delete\n"),
        (
            _deletion(
                "kept",
                tip="sha-later",
                reason_kind="tip-moved",
                reason="its tip is sha-lat, not sha-mer, the head PR #42 merged at",
            ),
            "  kept remote branch fix/42-slug: its tip is sha-lat, not sha-mer, the head PR #42 "
            f"merged at. {_LATER}\n",
        ),
        (
            _deletion(
                "kept",
                tip="sha-merged",
                reason_kind="open-pull-request",
                reason="another open pull request uses this branch as its head (#501)",
            ),
            "  kept remote branch fix/42-slug: another open pull request uses this branch as its "
            f"head (#501). {_LATER}\n",
        ),
        (
            _deletion(
                "refused",
                reason_kind="cross-repository",
                reason="PR #42's head is in another repository, a fork",
            ),
            "  remote branch fix/42-slug not deleted: PR #42's head is in another repository, a "
            "fork\n",
        ),
    ],
    ids=["gone", "tip-moved", "open-pull-request", "fork"],
)
def test_a_branch_kept_gone_or_a_forks_is_said_in_one_line_and_never_fails(
    lib, monkeypatch, capsys, document, said
) -> None:
    """One line on standard output; a branch not deleted names the command
    that deletes it later — but a fork's, which is its owner's to delete."""
    _backbone_answers(monkeypatch, lib, document)
    assert lib.delete_branch(42, "sha-merged", {}, allow_foreign_repo=False) == document["outcome"]
    out = capsys.readouterr()
    assert out.out == said
    assert out.err == ""


def test_a_deletion_the_backbone_refused_is_a_warning_naming_the_command(
    lib, monkeypatch, capsys
) -> None:
    """Refused by the backbone's guard, say — the comparisons disagree and the
    operator confirmed nothing: a warning in the backbone's words, never an
    error; the merge stands, and the command that deletes the branch later is
    named, with the flag where the landing was confirmed."""
    refused = _deletion(
        "refused",
        branch=None,
        reason_kind="foreign-repository",
        reason="the cross-repository guard refused: …",
        merged_head=None,
    )
    _backbone_answers(monkeypatch, lib, refused)
    assert lib.delete_branch(42, "sha-merged", {}, allow_foreign_repo=False) == "refused"
    assert capsys.readouterr().err == (
        "[warn] the remote head branch not deleted: the cross-repository guard refused: …. "
        f"{_LATER}\n"
    )
    _backbone_answers(monkeypatch, lib, refused)
    lib.delete_branch(42, "sha-merged", {}, allow_foreign_repo=True)
    assert capsys.readouterr().err.endswith(
        "`pkit pull-request delete-branch 42 --expect sha-merged --allow-foreign-repo`.\n"
    )


def test_a_head_other_than_the_merged_one_names_the_head_that_merged(
    lib, monkeypatch, capsys
) -> None:
    """The backbone checks the head against the PR's own: refused, the line
    names the command at the head the PR merged at, as the backbone read it."""
    _backbone_answers(
        monkeypatch,
        lib,
        _deletion(
            "refused",
            reason_kind="expect-mismatch",
            reason="the head named, sha-merged, is not the head PR #42 merged at, sha-actual",
            merged_head="sha-actual",
        ),
    )
    assert lib.delete_branch(42, "sha-merged", {}, allow_foreign_repo=False) == "refused"
    assert capsys.readouterr().err.endswith(
        "To delete it later: `pkit pull-request delete-branch 42 --expect sha-actual`.\n"
    )


def test_an_unconfirmed_deletion_is_one_warning_naming_the_command(
    lib, monkeypatch, capsys
) -> None:
    """Whether the branch was deleted is not known: one line says so and names
    the command to run again, with what the verb's own re-run does about it;
    the merge stands."""
    _backbone_answers(
        monkeypatch,
        lib,
        _deletion(
            "unconfirmed",
            reason_kind="unanswered",
            reason="the deletion got no usable answer (HTTP 502), and the branch could not be "
            "read since (HTTP 502)",
        ),
    )
    ended = lib.delete_branch(
        42, "sha-merged", {}, allow_foreign_repo=False, rerun_note="A re-run does not retry it."
    )
    assert ended == "unconfirmed"
    out = capsys.readouterr()
    assert out.out == ""
    assert out.err == (
        "[warn] whether remote branch fix/42-slug was deleted is not known: the deletion got no "
        "usable answer (HTTP 502), and the branch could not be read since (HTTP 502). "
        f"{_LATER} A re-run does not retry it.\n"
    )


@pytest.mark.parametrize(
    "documents",
    [(), (_deletion("landed"),), ({**_deletion("kept"), "tip": 7},)],
    ids=["no-answer", "unknown-outcome", "a-field-of-another-type"],
)
def test_a_deletion_the_backbone_gives_no_answer_to_is_unconfirmed(
    lib, monkeypatch, capsys, documents
) -> None:
    """No answer, or one that names no way the deletion ended: whether the
    branch was deleted is not known, and the verb says so, names the command,
    and goes on."""
    _backbone_answers(monkeypatch, lib, *documents)
    assert lib.delete_branch(42, "sha-merged", {}, allow_foreign_repo=False) == "unconfirmed"
    err = capsys.readouterr().err
    assert err.startswith("[warn] whether PR #42's head branch on GitHub was deleted is not known")
    assert "The merge is durable" in err and err.endswith(f"{_LATER}\n")


def test_with_no_merged_head_known_nothing_is_asked(lib, monkeypatch, capsys) -> None:
    """The deletion is asked for only at a head that merged: with none known,
    the branch is kept, and the line says how to find the head and delete it."""
    asked = _backbone_answers(monkeypatch, lib, _deletion("deleted"))
    assert lib.delete_branch(42, "", {}, allow_foreign_repo=False) == lib.NOT_ASKED
    assert asked == []
    err = capsys.readouterr().err
    assert "the head PR #42 merged at is not known" in err
    assert "`pkit pull-request read 42`" in err
    assert "`pkit pull-request delete-branch 42 --expect <that head>`" in err


def test_pm_keeps_no_copy_of_the_remote_deletion(lib) -> None:
    """The head branch on GitHub is deleted only by the backbone (ADR-061
    point 1): this library asks GitHub for no deletion itself."""
    import inspect

    source = inspect.getsource(lib)
    assert "git/refs/heads" not in source and "updateRefs" not in source
    assert not hasattr(lib, "delete_remote_branch") and not hasattr(lib, "gh_run")


# --- cleanup_local ---------------------------------------------------------


def _fake_git(
    monkeypatch, lib, *, checkout_stderr="", pull_stderr="", branch_d_stderr="", tip="sha-head"
):
    """Stub `subprocess.run` for the local git steps; a non-empty stderr makes
    that step fail. The local head, when there is one, is at `tip`, and
    nothing on it is past the merged head. Returns the argvs seen."""
    seen: list[list[str]] = []

    def fake_run(argv, **kwargs):
        seen.append(list(argv))
        if argv[:2] == ["git", "checkout"] and checkout_stderr:
            return subprocess.CompletedProcess(argv, 128, stdout="", stderr=checkout_stderr)
        if argv[:2] == ["git", "pull"] and pull_stderr:
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr=pull_stderr)
        if argv[:3] == ["git", "branch", "-D"] and branch_d_stderr:
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr=branch_d_stderr)
        if argv[:2] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(argv, 0 if tip else 1, stdout=f"{tip}\n", stderr="")
        if argv[:2] == ["git", "rev-list"]:
            return subprocess.CompletedProcess(argv, 0, stdout="0\n", stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(lib.subprocess, "run", fake_run)
    return seen


def _cleanup(lib, branch: str = "fix/42-slug", **kwargs: Any) -> None:
    """The local clean-up after a remote deletion that ended `deleted`, at the
    merged head `sha-head`, unless told otherwise."""
    lib.cleanup_local(
        branch,
        {},
        **{"cross_repository": False, "merged_head": "sha-head", "remote": "deleted", **kwargs},
    )


@pytest.fixture(autouse=True)
def backbone(lib: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Stand in for the backbone's reading: `answer(name)` declares the default branch,
    `answer(None)` makes the backbone unable to say. `main`, undeclared, by default."""
    reading = lib.default_branch

    def answer(name: str | None, declared: bool = True) -> None:
        monkeypatch.setattr(reading, "_read", {})

        def ask(explicit: str | None, _run: Any) -> Any:
            if name is None:
                raise reading.Unanswered("no pkit here")
            branch = reading.Branch(name, declared, f"origin/{name}", "c0ffee", None)
            return reading.Reading(branch, reading.Base(f"origin/{name}", "c0ffee", "c0ffee", None))

        monkeypatch.setattr(reading, "_ask", ask)

    answer("main", declared=False)
    return answer


def test_cleanup_local_sequence_on_the_declared_default_branch(
    lib: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], backbone: Any
) -> None:
    """checkout <default branch> → pull --ff-only → branch -D <head>, once the
    head is found all merged; the default branch is the one the backbone
    declares (COR-054), not a hardcoded main."""
    backbone("develop")
    seen = _fake_git(monkeypatch, lib)
    _cleanup(lib)
    assert seen == [
        ["git", "checkout", "develop"],
        ["git", "pull", "--ff-only"],
        ["git", "rev-parse", "--verify", "--quiet", "refs/heads/fix/42-slug"],
        ["git", "rev-list", "--count", "sha-head..sha-head"],
        ["git", "branch", "-D", "fix/42-slug"],
    ]
    assert "[warn]" not in capsys.readouterr().err


def test_cleanup_local_defaults_to_main_when_config_is_silent(lib, monkeypatch):
    seen = _fake_git(monkeypatch, lib)
    _cleanup(lib)
    assert seen[0] == ["git", "checkout", "main"]


def test_cleanup_local_is_skipped_when_the_backbone_cannot_say(
    lib: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], backbone: Any
) -> None:
    """No switching to a guessed branch (COR-054 point 4): the clean-up is skipped with
    the cause, and the merge — already durable — does not fail."""
    backbone(None)
    seen = _fake_git(monkeypatch, lib)
    _cleanup(lib)
    assert seen == []
    err = capsys.readouterr().err
    assert "[warn] the local clean-up is skipped: no pkit here." in err


def test_cleanup_local_checkout_failure_skips_pull_still_deletes(lib, monkeypatch, capsys):
    """A detached HEAD (or a default branch held by another worktree) fails
    the checkout: warn, skip the pull (pulling into whatever IS checked out
    would be wrong), still attempt the branch delete."""
    err_text = "fatal: 'main' is already used by worktree at '/repo/wt-main'"
    seen = _fake_git(monkeypatch, lib, checkout_stderr=err_text)
    _cleanup(lib)
    err = capsys.readouterr().err
    assert f"[warn] git checkout main failed: {err_text}" in err
    assert ["git", "pull", "--ff-only"] not in seen
    assert ["git", "branch", "-D", "fix/42-slug"] in seen


def test_cleanup_local_pull_failure_is_a_warning(lib, monkeypatch, capsys):
    seen = _fake_git(monkeypatch, lib, pull_stderr="fatal: Not possible to fast-forward")
    _cleanup(lib)
    assert "[warn] git pull failed: fatal: Not possible to fast-forward" in capsys.readouterr().err
    assert ["git", "branch", "-D", "fix/42-slug"] in seen


def test_cleanup_local_branch_delete_failure_is_a_warning(lib, monkeypatch, capsys):
    """The head branch checked out in a worktree (#587) cannot be deleted
    locally — a warning naming git's reason, never an exception."""
    branch_err = "error: cannot delete branch 'fix/42-slug' used by worktree at '/repo/wt-42'"
    _fake_git(monkeypatch, lib, branch_d_stderr=branch_err)
    _cleanup(lib)
    assert f"[warn] git branch -D fix/42-slug failed: {branch_err}" in capsys.readouterr().err


def test_cleanup_local_never_force_deletes_a_same_named_branch_for_a_fork_pr(lib, monkeypatch):
    """A local branch sharing a fork PR's head name is not that PR's head;
    `git branch -D` would discard its unpushed work, so it is not run."""
    seen = _fake_git(monkeypatch, lib)
    _cleanup(lib, "release/1.x", cross_repository=True, remote="refused")
    assert ["git", "branch", "-D", "release/1.x"] not in seen
    assert seen[0] == ["git", "checkout", "main"]


@pytest.mark.parametrize("remote", ["deleted", "gone"])
def test_the_local_branch_goes_once_the_remote_one_is_deleted_or_gone(
    lib, monkeypatch, capsys, remote
) -> None:
    seen = _fake_git(monkeypatch, lib)
    _cleanup(lib, remote=remote)
    assert ["git", "branch", "-D", "fix/42-slug"] in seen
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("remote", ["kept", "refused", "unconfirmed", "not-asked"])
def test_the_local_branch_stays_while_the_remote_one_was_not_deleted(
    lib, monkeypatch, capsys, remote
) -> None:
    """The local branch goes only with the one on GitHub: kept there, refused,
    not known to be deleted, or not asked for, it stays here too, said in one
    line — and its commits are not even compared."""
    seen = _fake_git(monkeypatch, lib)
    _cleanup(lib, remote=remote)
    assert not any(argv[:2] in (["git", "branch"], ["git", "rev-list"]) for argv in seen)
    assert capsys.readouterr().out == (
        f"  kept local branch fix/42-slug: its branch on GitHub was not deleted ({remote}), "
        "and the local one goes only with it (`git branch -D fix/42-slug` once it has)\n"
    )


def test_the_remote_outcome_and_the_merged_head_are_required_keywords(lib):
    """No defaults: every caller of the local clean-up states what became of
    the branch on GitHub and the head the PR merged at, so none can delete the
    local branch on a guess."""
    import inspect

    parameters = inspect.signature(lib.cleanup_local).parameters
    for name in ("remote", "merged_head"):
        assert parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
        assert parameters[name].default is inspect.Parameter.empty


def test_cross_repository_is_a_required_keyword(lib):
    """No default: every caller of the local clean-up must state whether the
    PR is cross-repository, so a later caller cannot silently reintroduce the
    fork-PR deletion hole."""
    import inspect

    p = inspect.signature(lib.cleanup_local).parameters["cross_repository"]
    assert p.kind is inspect.Parameter.KEYWORD_ONLY
    assert p.default is inspect.Parameter.empty


def test_the_confirmation_is_a_required_keyword_of_the_deletion(lib):
    """No default: every caller of the backbone's deletion states whether the
    operator confirmed a change in another repository, as for the merge."""
    import inspect

    p = inspect.signature(lib.delete_branch).parameters["allow_foreign_repo"]
    assert p.kind is inspect.Parameter.KEYWORD_ONLY
    assert p.default is inspect.Parameter.empty


def _guarded_git(monkeypatch, lib, *, tip: str, unmerged: str):
    """`subprocess.run` for a clean-up told the merged head: `rev-parse` answers
    `tip` (empty when the branch is not here), `rev-list --count` the commits on
    it the merge does not hold (empty: git cannot tell). Returns the argvs seen."""
    seen: list[list[str]] = []

    def fake_run(argv, **kwargs):
        seen.append(list(argv))
        if argv[:2] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(argv, 0 if tip else 1, stdout=tip, stderr="")
        if argv[:2] == ["git", "rev-list"]:
            code = 0 if unmerged else 128
            return subprocess.CompletedProcess(argv, code, stdout=f"{unmerged}\n", stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(lib.subprocess, "run", fake_run)
    return seen


def test_with_the_merged_head_a_branch_that_all_merged_is_deleted(lib, monkeypatch, capsys):
    seen = _guarded_git(monkeypatch, lib, tip="sha-old", unmerged="0")
    _cleanup(lib)
    assert ["git", "rev-list", "--count", "sha-head..sha-old"] in seen
    assert ["git", "branch", "-D", "fix/42-slug"] in seen
    assert "[warn]" not in capsys.readouterr().err


@pytest.mark.parametrize("unmerged", ["2", ""], ids=["work-since", "cannot-tell"])
def test_with_the_merged_head_a_branch_holding_more_is_kept(lib, monkeypatch, capsys, unmerged):
    """A branch with commits the merge does not hold — work since, or a clone
    that cannot tell — is never force-deleted: `-D` would lose that work."""
    seen = _guarded_git(monkeypatch, lib, tip="sha-newer", unmerged=unmerged)
    _cleanup(lib)
    assert ["git", "branch", "-D", "fix/42-slug"] not in seen
    err = capsys.readouterr().err
    assert "local branch fix/42-slug (at sha-new) holds commits the merge at sha-hea" in err
    assert "it is kept" in err


def test_with_no_merged_head_known_the_local_branch_is_kept(lib, monkeypatch, capsys):
    """No head to compare with: the branch is kept with a warning, never
    force-deleted on a guess — as release's twin keeps it."""
    seen = _guarded_git(monkeypatch, lib, tip="sha-old", unmerged="0")
    _cleanup(lib, merged_head="", remote="gone")
    assert not any(argv[:2] in (["git", "branch"], ["git", "rev-list"]) for argv in seen)
    assert (
        "[warn] local branch fix/42-slug (at sha-old) holds commits the merge at an unknown "
        "head does not, or this clone cannot tell; it is kept."
    ) in capsys.readouterr().err


def test_with_the_merged_head_a_clone_without_the_branch_deletes_nothing(lib, monkeypatch, capsys):
    seen = _guarded_git(monkeypatch, lib, tip="", unmerged="")
    _cleanup(lib)
    assert seen[:2] == [["git", "checkout", "main"], ["git", "pull", "--ff-only"]]
    assert not any(argv[:2] in (["git", "branch"], ["git", "rev-list"]) for argv in seen)
    assert "[warn]" not in capsys.readouterr().err


# --- the queue: refusal, landing, dequeue (#1011) ----------------------------


def _reading(lib, **fields: Any) -> Any:
    base = {
        "has_queue": True,
        "merge_method": "SQUASH",
        "pr_id": "PR_node",
        "pr_state": "OPEN",
        "head_oid": "sha-head",
    }
    return pull_request_backbone.reading(lib.merge_queue, **{**base, **fields})


def _defaults(monkeypatch, lib, title="PR_TITLE", message="PR_BODY") -> list[int]:
    reads: list[int] = []

    def defaults(config):
        reads.append(1)
        return title, message

    monkeypatch.setattr(lib.merge_queue, "squash_commit_defaults", defaults)
    return reads


def _refusal(lib, reading, **flags: Any) -> str:
    kwargs = {"base": "main", "admin": False, "bypass_ci": False, "force": False, "config": {}}
    return lib.queue_refusal(reading, **{**kwargs, **flags})


def test_a_base_without_a_queue_is_never_refused(lib, monkeypatch) -> None:
    reads = _defaults(monkeypatch, lib, title="COMMIT_OR_PR_TITLE")
    assert _refusal(lib, _reading(lib, has_queue=False), admin=True, bypass_ci=True) == ""
    assert reads == []


@pytest.mark.parametrize(
    ("reading_fields", "flags", "refusal"),
    [
        ({}, {"admin": True}, "--admin would merge around the queue"),
        ({}, {"bypass_ci": True}, "--bypass-ci cannot bypass a check there"),
        ({"merge_method": "MERGE"}, {}, "the merge queue on main merges by MERGE"),
    ],
    ids=["admin", "bypass-ci", "not-squash"],
)
def test_what_would_go_around_or_against_the_queue_is_refused(
    lib, monkeypatch, reading_fields, flags, refusal
) -> None:
    _defaults(monkeypatch, lib)
    assert refusal in _refusal(lib, _reading(lib, **reading_fields), **flags)


@pytest.mark.parametrize(
    ("title", "message"),
    [("COMMIT_OR_PR_TITLE", "PR_BODY"), ("PR_TITLE", "COMMIT_MESSAGES"), ("PR_TITLE", "BLANK")],
)
def test_squash_commit_defaults_other_than_the_pr_title_and_body_are_refused(
    lib, monkeypatch, title, message
) -> None:
    """The queue composes the squash commit from the repository's defaults, so
    the convention's subject-is-the-title rule (DEC-013) is a checked
    precondition: anything else is refused, with the command that sets them."""
    _defaults(monkeypatch, lib, title=title, message=message)
    refusal = _refusal(lib, _reading(lib))
    assert f"title {title} and message {message}" in refusal
    assert (
        "gh api -X PATCH repos/{owner}/{repo} -f squash_merge_commit_title=PR_TITLE "
        "-f squash_merge_commit_message=PR_BODY"
    ) in refusal


def test_squash_commit_defaults_that_cannot_be_read_are_raised(lib, monkeypatch) -> None:
    def unreadable(config):
        raise lib.merge_queue.Unreadable("not in the answer")

    monkeypatch.setattr(lib.merge_queue, "squash_commit_defaults", unreadable)
    with pytest.raises(lib.merge_queue.Unreadable, match="not in the answer"):
        _refusal(lib, _reading(lib))


def test_a_head_the_queue_dropped_is_not_enqueued_again_without_force(lib, monkeypatch) -> None:
    _defaults(monkeypatch, lib)
    removal = lib.merge_queue.Removal(
        at="2026-10-01T10:05:00Z", reason="failed checks", head_oid="sha-head"
    )
    reading = _reading(lib, removal=removal)
    refusal = _refusal(lib, reading)
    assert "dropped the PR at its current head sha-hea at 2026-10-01T10:05:00Z" in refusal
    assert "(GitHub says: failed checks)" in refusal
    assert "--force" in refusal
    assert _refusal(lib, reading, force=True) == ""
    silent = _reading(lib, removal=lib.merge_queue.Removal(at="t", reason="", head_oid=""))
    assert "(GitHub gives no reason)" in _refusal(lib, silent)


class _Queue:
    """`merge_queue.read` answering each call with the next reading, the last
    repeated — the backbone's own readings, in the wait and the dequeue, too —
    and the backbone's `gh` recording every command."""

    def __init__(self, lib, monkeypatch, readings: list[Any], *, gh_fails: bool = False) -> None:
        self.readings = list(readings)
        self.commands: list[list[str]] = []
        self.sleeps: list[float] = []
        monkeypatch.setattr(lib.merge_queue, "read", self.read)
        _defaults(monkeypatch, lib)

        def fake_gh(args):
            self.commands.append(list(args))
            code = 1 if gh_fails else 0
            said = "GraphQL: the service refused it" if gh_fails else ""
            return subprocess.CompletedProcess(args, code, stdout="", stderr=said)

        now = [0.0]

        def sleep(seconds: float) -> None:
            self.sleeps.append(seconds)
            now[0] += seconds

        pull_request_backbone.in_process(
            monkeypatch,
            lib.merge_queue,
            gh=fake_gh,
            read=self.read,
            sleep=sleep,
            clock=lambda: now[0],
        )

    def read(self, pr_number, config):
        reading = self.readings.pop(0) if len(self.readings) > 1 else self.readings[0]
        if isinstance(reading, Exception):
            raise reading
        return reading

    def merges(self) -> list[list[str]]:
        return [c for c in self.commands if c[:2] == ["pr", "merge"] or c[1:3] == ["pr", "merge"]]


def _request(lib, **fields: Any) -> Any:
    base = {"pr_number": 42, "pr_title": "fix: x", "head_oid": "sha-head", "base": "main"}
    return lib.MergeRequest(**{**base, **fields})


def test_without_a_queue_the_merge_counts_once_github_reports_it(lib, monkeypatch, capsys):
    queue = _Queue(
        lib,
        monkeypatch,
        [_reading(lib, has_queue=False), _reading(lib, has_queue=False, pr_state="MERGED")],
    )
    landing = lib.land(_request(lib), {})
    assert landing.outcome == lib.MERGED
    assert queue.merges() == [
        [
            "gh",
            "pr",
            "merge",
            "42",
            "--squash",
            "--subject",
            "fix: x",
            "--match-head-commit",
            "sha-head",
        ]
    ]
    assert "  merged PR #42" in capsys.readouterr().out


def test_a_merge_gh_only_enqueued_is_never_taken_for_a_merge(lib, monkeypatch, capsys):
    """On a base that requires a queue `gh pr merge` enqueues and exits 0. The
    PR is read once more; anything but merged is waited for as a queued PR, so
    nothing that follows a merge runs on an unmerged one."""
    queue = _Queue(
        lib,
        monkeypatch,
        [
            _reading(lib, has_queue=False),
            _reading(lib, has_queue=True, in_queue=True, position=1),
        ],
    )
    landing = lib.land(_request(lib, wait_seconds=0), {})
    assert landing.outcome == lib.STILL_QUEUED
    assert len(queue.merges()) == 1
    assert "GitHub does not report PR #42 merged" in capsys.readouterr().out


def test_a_direct_merge_github_cannot_confirm_is_unconfirmed_not_queued(lib, monkeypatch, capsys):
    """gh accepts the direct merge and no reading can be taken since: the PR
    may have merged or been enqueued, and the landing says it is not known."""
    queue = _Queue(
        lib,
        monkeypatch,
        [_reading(lib, has_queue=False), lib.merge_queue.Unreadable("HTTP 502")],
    )
    landing = lib.land(_request(lib), {})
    assert landing.outcome == lib.UNCONFIRMED
    assert landing.reading is None
    assert landing.message == (
        "gh accepted the merge of PR #42 into main, but GitHub could not be read to "
        "confirm that it merged: HTTP 502"
    )
    assert len(queue.merges()) == 1
    assert "could not confirm that PR #42 merged: HTTP 502. Reading it again." in (
        capsys.readouterr().err
    )


def test_a_queue_lost_sight_of_after_the_enqueue_is_still_queued(lib, monkeypatch):
    _Queue(lib, monkeypatch, [_reading(lib), lib.merge_queue.Unreadable("HTTP 502")])
    landing = lib.land(_request(lib), {})
    assert landing.outcome == lib.STILL_QUEUED
    assert landing.reading is None
    assert landing.message == "lost sight of the merge queue: HTTP 502"


def test_a_queue_switched_on_while_the_gates_ran_is_seen_before_the_merge(lib, monkeypatch):
    """`land` reads the queue itself, just before deciding: a run that began on
    a base without one enqueues once it has one, and never merges directly."""
    queue = _Queue(
        lib,
        monkeypatch,
        [_reading(lib), _reading(lib, in_queue=True, position=1)],
    )
    landing = lib.land(_request(lib, wait_seconds=0), {})
    assert landing.outcome == lib.STILL_QUEUED
    assert queue.merges() == [
        ["gh", "pr", "merge", "42", "--auto", "--match-head-commit", "sha-head"]
    ]


def test_a_queue_switched_on_is_judged_again(lib, monkeypatch):
    """`--admin`, fine on a base without a queue, is refused by the time the
    base has one, and nothing is merged or enqueued."""
    queue = _Queue(lib, monkeypatch, [_reading(lib)])
    landing = lib.land(_request(lib, admin=True), {})
    assert landing.outcome == lib.REFUSED
    assert "--admin would merge around the queue" in landing.message
    assert queue.commands == []


def test_a_pr_already_in_the_queue_is_waited_for_not_enqueued_again(lib, monkeypatch, capsys):
    queue = _Queue(
        lib,
        monkeypatch,
        [_reading(lib, in_queue=True), _reading(lib, pr_state="MERGED", merged_at="t")],
    )
    landing = lib.land(_request(lib), {})
    assert landing.outcome == lib.MERGED
    assert queue.merges() == []
    out = capsys.readouterr().out
    assert "  PR #42 is already in the merge queue for main" in out
    assert "  merged PR #42 through the queue" in out


def test_an_unreadable_queue_lands_nothing(lib, monkeypatch):
    queue = _Queue(lib, monkeypatch, [lib.merge_queue.Unreadable("HTTP 502")])
    landing = lib.land(_request(lib), {})
    assert landing.outcome == lib.UNREADABLE
    assert landing.message == "cannot tell how main merges: HTTP 502"
    assert queue.commands == []


def test_a_refused_enqueue_is_a_failure(lib, monkeypatch):
    """GitHub answered the enqueue with a refusal: nothing it may yet act on
    was sent, so the landing does not count the request as sent."""
    queue = _Queue(lib, monkeypatch, [_reading(lib)], gh_fails=True)
    landing = lib.land(_request(lib), {})
    assert (landing.outcome, landing.requested) == (lib.FAILED, False)
    assert len(queue.merges()) == 1
    assert queue.sleeps == []


@pytest.mark.parametrize(
    ("queued", "command"),
    [
        ({"in_queue": True}, ["api", "graphql"]),
        ({"waiting_to_enter": True}, ["pr", "merge", "42", "--disable-auto"]),
    ],
    ids=["in-the-queue", "waiting-to-enter"],
)
def test_a_push_after_the_enqueue_takes_the_pr_out_of_the_queue(
    lib, monkeypatch, queued, command
) -> None:
    """Commits nobody checked must not merge: a head that moves while the PR
    waits takes it out of the queue — through GitHub's dequeue mutation once it
    is in (gh's `--disable-auto` answers "already queued" there and does
    nothing), else by cancelling the auto-merge that would put it in."""
    moved = _reading(lib, head_oid="sha-pushed", **queued)
    out = _reading(lib, head_oid="sha-pushed")
    # The wait sees the head move; the dequeue reads the PR before and after.
    queue = _Queue(lib, monkeypatch, [_reading(lib, **queued), moved, moved, out])
    landing = lib.land(_request(lib), {})
    assert landing.outcome == lib.HEAD_MOVED
    assert "head moved from sha-hea to sha-pus after its gates checked it" in landing.message
    assert "it was taken out of the merge queue" in landing.message
    dequeue = queue.commands[-1]
    assert dequeue[1 : 1 + len(command)] == command
    if command[0] == "api":
        assert "dequeuePullRequest" in dequeue[4] and dequeue[-1] == "id=PR_node"


def test_a_dequeue_that_does_not_take_says_so(lib, monkeypatch) -> None:
    still = _reading(lib, head_oid="sha-pushed", in_queue=True)
    _Queue(lib, monkeypatch, [_reading(lib, in_queue=True), still])
    landing = lib.land(_request(lib), {})
    assert landing.outcome == lib.HEAD_MOVED
    assert "taking it out of the merge queue failed" in landing.message


def _no_answer_back(lib, monkeypatch) -> list[list[str]]:
    """The backbone's merge requests get no answer back — its run was stopped
    past its bound, or ended without a document. Returns the requests asked."""
    asked: list[list[str]] = []

    def request(args, config):
        asked.append(list(args))
        raise lib.merge_queue.Unreadable(
            f"`pkit pull-request {args[0]}` gave no answer within 120 s, and was stopped"
        )

    monkeypatch.setattr(lib.merge_queue, "request", request)
    return asked


def test_a_merge_with_no_answer_back_that_github_reports_merged_is_the_merge(
    lib, monkeypatch, capsys
) -> None:
    """The run may have ended after gh accepted the merge: the PR is read
    before anything is decided, and merged it is the merge — what follows it
    runs, rather than a re-run finding a merge "by someone else"."""
    _Queue(
        lib,
        monkeypatch,
        [_reading(lib, has_queue=False), _reading(lib, has_queue=False, pr_state="MERGED")],
    )
    asked = _no_answer_back(lib, monkeypatch)
    landing = lib.land(_request(lib), {})
    assert landing.outcome == lib.MERGED
    assert [a[0] for a in asked] == ["merge"]
    captured = capsys.readouterr()
    assert "the merge of PR #42 got no answer back from the backbone" in captured.err
    assert "  merged PR #42, as GitHub reports it (merged)" in captured.out


def test_an_enqueue_with_no_answer_back_that_github_reports_queued_is_waited_for(
    lib, monkeypatch, capsys
) -> None:
    _Queue(
        lib,
        monkeypatch,
        [
            _reading(lib),
            _reading(lib, in_queue=True, position=1),
            _reading(lib, pr_state="MERGED", merged_at="t"),
        ],
    )
    asked = _no_answer_back(lib, monkeypatch)
    landing = lib.land(_request(lib), {})
    assert landing.outcome == lib.MERGED
    assert [a[0] for a in asked] == ["enqueue"]
    out = capsys.readouterr().out
    assert "  PR #42 is in the merge queue for main (position 1 in the queue)" in out
    assert "  merged PR #42 through the queue" in out


@pytest.mark.parametrize(
    ("first", "asked"),
    [({"has_queue": False}, "merge"), ({}, "enqueue")],
    ids=["merge", "enqueue"],
)
def test_a_request_with_no_answer_back_github_cannot_settle_is_unconfirmed(
    lib, monkeypatch, first, asked
) -> None:
    """Neither the backbone nor GitHub can say what the request came to: the
    landing is unconfirmed, never "nothing merged", so the verb records what
    follows the merge as owed and a re-run completes it."""
    _Queue(lib, monkeypatch, [_reading(lib, **first), lib.merge_queue.Unreadable("HTTP 502")])
    _no_answer_back(lib, monkeypatch)
    landing = lib.land(_request(lib), {})
    assert landing.outcome == lib.UNCONFIRMED
    assert landing.message == (
        f"the {asked} of PR #42 into main got no answer back, and GitHub could not be read "
        "since to tell whether it merged or entered the merge queue: HTTP 502. Read where "
        "PR #42 stands with `pkit pull-request read 42`"
    )


@pytest.mark.parametrize(
    ("first", "asked"),
    [({"has_queue": False}, "merge"), ({}, "enqueue")],
    ids=["merge", "enqueue"],
)
def test_a_request_with_no_answer_back_that_github_reports_open_is_unconfirmed_not_unmade(
    lib, monkeypatch, capsys, first, asked
) -> None:
    """With no answer from the backbone at all, one reading neither merged nor
    queued does not say the request was not made — that takes two readings
    running (ADR-061 point 7), which the backbone takes when it answers. The
    landing is unconfirmed, naming the reading that tells, and nothing calls
    it failed."""
    _Queue(lib, monkeypatch, [_reading(lib, **first)])
    _no_answer_back(lib, monkeypatch)
    landing = lib.land(_request(lib), {})
    assert landing.outcome == lib.UNCONFIRMED
    assert landing.message == (
        f"the {asked} of PR #42 into main got no answer back, and one reading since finds it "
        f"neither merged nor queued (not in the queue), which does not tell whether the "
        f"{asked} was made: the {asked} may still show. Read where PR #42 stands with "
        "`pkit pull-request read 42`"
    )
    assert "not made" not in capsys.readouterr().err


def _settled(lib, accepted: bool | None, kind: str) -> Any:
    """The backbone's answer to a request that got no answer, settled by
    reading: not seen made (`accepted` false), or unconfirmed (`accepted`
    null)."""
    reason = (
        "the merge of PR #42 got no usable answer (HTTP 502: Bad Gateway), and was not seen "
        "made on two readings 40 s apart, the second 40 s after it was sent: PR #42 reads "
        "neither merged nor queued (not in the queue)"
        if kind == "not-made"
        else "the merge of PR #42 got no answer (HTTP 502: Bad Gateway), and PR #42 could not "
        "be read since (HTTP 502): whether the merge was made is not known"
    )
    return lib.merge_queue.Outcome(accepted, None, reason, reason_kind=kind)


@pytest.mark.parametrize(
    ("first", "asked"), [({"has_queue": False}, "merge"), ({}, "enqueue")], ids=["merge", "enqueue"]
)
def test_a_request_the_backbone_did_not_see_made_is_a_failure_still_counted_as_sent(
    lib, monkeypatch, capsys, first, asked
) -> None:
    """Two readings did not see the request made: the landing fails, in the
    backbone's words, which say what the readings saw — and counts the
    request as sent (`requested`), since GitHub may still apply it, so a verb
    can owe what follows a merge that shows later."""
    _Queue(lib, monkeypatch, [_reading(lib, **first)])
    answered = _answering(lib, monkeypatch, _settled(lib, False, "not-made"))
    landing = lib.land(_request(lib), {})
    assert (landing.outcome, landing.requested) == (lib.FAILED, True)
    assert [args[0] for args in answered] == [asked]
    err = capsys.readouterr().err
    assert "and was not seen made on two readings 40 s apart" in err
    assert "was not made" not in err


@pytest.mark.parametrize(
    ("first", "asked"), [({"has_queue": False}, "merge"), ({}, "enqueue")], ids=["merge", "enqueue"]
)
def test_a_request_the_backbone_could_not_settle_is_unconfirmed_without_reading_again(
    lib, monkeypatch, first, asked
) -> None:
    """The backbone could not tell whether the request was made: pm takes its
    word — unconfirmed — reads nothing more, and names the reading that
    tells."""
    queue = _Queue(lib, monkeypatch, [_reading(lib, **first)])
    read = queue.read
    readings: list[int] = []

    def counted(pr_number, config):
        readings.append(pr_number)
        return read(pr_number, config)

    monkeypatch.setattr(lib.merge_queue, "read", counted)
    _answering(lib, monkeypatch, _settled(lib, None, "unanswered"))
    landing = lib.land(_request(lib), {})
    assert landing.outcome == lib.UNCONFIRMED
    assert readings == [42]  # the reading before the request, and none after
    assert landing.message == (
        "the merge of PR #42 got no answer (HTTP 502: Bad Gateway), and PR #42 could not be "
        "read since (HTTP 502): whether the merge was made is not known. Read where PR #42 "
        "stands with `pkit pull-request read 42`"
    )


@pytest.mark.parametrize(
    "answer",
    ["unconfirmed", "no-answer-back"],
)
def test_a_dequeue_whose_end_is_not_known_says_so_and_how_to_read_it(
    lib, monkeypatch, answer
) -> None:
    """Whether the PR left the queue is not known — the backbone could not
    tell, or gave no answer back: the landing says so, never that taking it
    out failed, and names the reading that tells."""
    moved = _reading(lib, head_oid="sha-pushed", in_queue=True)
    _Queue(lib, monkeypatch, [_reading(lib, in_queue=True), moved])
    if answer == "unconfirmed":
        _answering(lib, monkeypatch, _settled(lib, None, "unanswered"))
    else:
        _no_answer_back(lib, monkeypatch)
    landing = lib.land(_request(lib), {})
    assert landing.outcome == lib.HEAD_MOVED
    assert "whether taking it out of the merge queue worked is not known" in landing.message
    assert "`pkit pull-request read 42`; if it is still queued, take it out" in landing.message
    assert "failed" not in landing.message


def test_a_dequeue_the_service_answered_but_no_reading_confirms_is_not_known(
    lib, monkeypatch
) -> None:
    """The service accepted the dequeue, and the PR could not be read since:
    more evidence than no answer at all, so never "failed" — not known, as
    the backbone's `accepted: null`, `unreadable` says."""
    moved = _reading(lib, head_oid="sha-pushed", in_queue=True)
    _Queue(lib, monkeypatch, [_reading(lib, in_queue=True), moved])
    _answering(
        lib,
        monkeypatch,
        lib.merge_queue.Outcome(
            None, 0, "the service accepted the dequeue of PR #42, and …", "unreadable"
        ),
    )
    landing = lib.land(_request(lib), {})
    assert "whether taking it out of the merge queue worked is not known" in landing.message
    assert "failed" not in landing.message


def test_a_dequeue_that_finds_the_pr_merged_says_it_merged_not_to_take_it_out(
    lib, monkeypatch
) -> None:
    """The queue merged the PR before it could be taken out: the landing says
    it merged, at which head — never "it may still merge… take it out
    yourself", which is no longer true of a merged PR."""
    moved = _reading(lib, head_oid="sha-pushed", in_queue=True)
    _Queue(lib, monkeypatch, [_reading(lib, in_queue=True), moved])
    _answering(
        lib,
        monkeypatch,
        lib.merge_queue.Outcome(
            False,
            None,
            "PR #42 has merged at head sha-pus (merged at t), which no dequeue undoes",
            "merged",
        ),
    )
    landing = lib.land(_request(lib), {})
    assert landing.outcome == lib.HEAD_MOVED
    assert landing.message == (
        "PR #42's head moved from sha-hea to sha-pus after its gates checked it, and it merged "
        "before it could be taken out of the merge queue: PR #42 has merged at head sha-pus "
        "(merged at t), which no dequeue undoes. The commits pushed after its gates checked it "
        "may be in that merge; look at it."
    )
    assert "take it out yourself" not in landing.message.lower()


def test_a_merge_at_a_head_the_gates_did_not_check_is_warned(lib, monkeypatch, capsys) -> None:
    _Queue(
        lib,
        monkeypatch,
        [_reading(lib, pr_state="MERGED", merged_at="t", head_oid="sha-other")],
    )
    assert lib.land(_request(lib), {}).outcome == lib.MERGED
    assert "merged at head sha-oth, not at sha-hea" in capsys.readouterr().err


# --- the merge verbs' queue flags ------------------------------------------


def _flags(lib, argv: list[str]) -> Any:
    import argparse

    parser = argparse.ArgumentParser()
    lib.add_queue_arguments(parser)
    return parser.parse_args(argv)


@pytest.mark.parametrize(
    ("argv", "seconds", "phrase"),
    [
        ([], None, "wait for the queue to merge it, as long as the queue estimates plus 2 min"),
        (["--no-wait"], 0, "return once it is queued (--no-wait)"),
        (["--wait-minutes", "20"], 1200, "wait for the queue to merge it, up to 20 min"),
    ],
    ids=["estimate", "no-wait", "minutes"],
)
def test_the_queue_flags_set_the_wait(lib, argv, seconds, phrase) -> None:
    args = _flags(lib, argv)
    assert lib.wait_seconds(args) == seconds
    assert lib.wait_phrase(lib.wait_seconds(args)).startswith(phrase)
    assert args.force is False


@pytest.mark.parametrize(
    "argv",
    [["--no-wait", "--wait-minutes", "3"], ["--wait-minutes", "-1"], ["--wait-minutes", "nan"]],
    ids=["both", "negative", "not-finite"],
)
def test_a_wait_the_flags_cannot_mean_is_a_usage_error(lib, argv) -> None:
    with pytest.raises(SystemExit):
        _flags(lib, argv)


# --- the backbone's cross-repository guard (#1254) ------------------------------------


def _answering(lib, monkeypatch, outcome: Any) -> list[list[str]]:
    """The backbone's requests answered with `outcome`; returns those asked."""
    asked: list[list[str]] = []

    def request(args, config):
        asked.append(list(args))
        return outcome

    monkeypatch.setattr(lib.merge_queue, "request", request)
    return asked


@pytest.mark.parametrize("confirmed", [True, False])
@pytest.mark.parametrize(
    ("first", "kind"), [({"has_queue": False}, "merge"), ({}, "enqueue")], ids=["merge", "enqueue"]
)
def test_the_confirmation_is_passed_on_exactly_when_the_operator_gave_it(
    lib, monkeypatch, confirmed, first, kind
) -> None:
    """The backbone asks nobody: the verb's guard did. It is told the operator
    confirmed a change in another repository exactly when they did at the
    verb (`MergeRequest.allow_foreign_repo`, which the verb sets from its
    guard's `confirmed`) — whatever the verb's comparison found — and never
    otherwise."""
    _Queue(lib, monkeypatch, [_reading(lib, **first)])
    asked = _answering(lib, monkeypatch, lib.merge_queue.Outcome(False, 1, "stop here"))
    lib.land(_request(lib, guard_passed="same-repo", allow_foreign_repo=confirmed), {})
    assert [args[0] for args in asked] == [kind]
    assert ("--allow-foreign-repo" in asked[0]) is confirmed


@pytest.mark.parametrize("confirmed", [True, False])
def test_the_dequeue_passes_the_confirmation_on_too(lib, monkeypatch, confirmed) -> None:
    asked = _answering(lib, monkeypatch, lib.merge_queue.Outcome(True, 0, ""))
    assert lib.dequeue(42, {}, allow_foreign_repo=confirmed)
    assert asked == [["dequeue", "42", *(["--allow-foreign-repo"] if confirmed else [])]]


def _guard_refused(lib) -> Any:
    """The backbone's answer to a request its cross-repository guard refused."""
    return lib.merge_queue.Outcome(
        False,
        None,
        "the cross-repository guard refused: …",
        reason_kind="foreign-repository",
        guard={
            "verdict": "diverged",
            "undetermined_kind": None,
            "anchor": "/work/project",
            "target": "/work/other",
            "cleared": None,
        },
    )


def test_when_the_two_comparisons_disagree_the_landing_is_refused_naming_both(
    lib, monkeypatch
) -> None:
    """The verb's guard passed the target as the session's own repository, the
    operator confirmed nothing, and the backbone's reads another: the backbone
    refused, made no request, and the landing is refused — never failed,
    never retried as if gh had said no — saying how the operator confirms it."""
    _Queue(lib, monkeypatch, [_reading(lib, has_queue=False)])
    asked = _answering(lib, monkeypatch, _guard_refused(lib))
    landing = lib.land(_request(lib, guard_passed="same-repo"), {})
    assert landing.outcome == lib.REFUSED
    assert [args[0] for args in asked] == ["merge"]
    assert "its comparison reads diverged" in landing.message
    assert "the session's anchor /work/project, the target /work/other" in landing.message
    assert "this verb's own guard passed it as same-repo" in landing.message
    assert "nothing was asked of GitHub" in landing.message
    assert "run the verb again with --allow-foreign-repo, which it passes on" in landing.message


def test_a_dequeue_the_backbones_guard_refused_names_the_command_that_takes_it_out(
    lib, monkeypatch, capsys
) -> None:
    """Running the verb again does not repeat a dequeue, so the error names
    the command that takes the PR out, with the flag that confirms the change
    there — a hint the operator can follow as given."""
    _answering(lib, monkeypatch, _guard_refused(lib))
    assert lib.dequeue(42, {}) is False
    err = capsys.readouterr().err
    assert "the backbone's cross-repository guard refused to take PR #42 out" in err
    assert "its comparison reads diverged" in err
    assert f"`pkit pull-request dequeue 42 --allow-foreign-repo` from {os.getcwd()}" in err
