"""Tests for project-management's merge-pr script.

Covers closing-issue extraction, checkbox detection, PR-title pattern
lookup, the CI-status gate, and the post-merge sequence (merge → hooks →
best-effort branch cleanup through the shared `_lib.pr_merge` mechanic).
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from tests import pull_request_backbone

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts" / "merge-pr.py"
)


@pytest.fixture(scope="module")
def mp():
    module_name = "pm_merge_pr_under_test"
    # merge-pr imports its `_lib.*` siblings; make the scripts dir importable.
    sys.path.insert(0, str(SCRIPT_PATH.parent))
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def titles() -> dict:
    return {
        "formats": {
            "pr": {
                "pattern": r"^(feat|fix|docs|test|refactor|chore|ci)(\([^)]+\))?: .+$",
            },
        },
    }


# --- closing-issue extraction ---------------------------------------


def test_extract_closes_single(mp) -> None:
    body = "Closes #42\n\n## Summary"
    assert mp._extract_closing_issues(body) == [42]


def test_extract_fixes_single(mp) -> None:
    body = "Fixes #99"
    assert mp._extract_closing_issues(body) == [99]


def test_extract_resolves_single(mp) -> None:
    body = "Resolves #100"
    assert mp._extract_closing_issues(body) == [100]


def test_extract_multiple_keywords(mp) -> None:
    body = "Closes #42, closes #43\nFixes #44"
    result = mp._extract_closing_issues(body)
    assert sorted(result) == [42, 43, 44]


def test_extract_dedupes_repeated_numbers(mp) -> None:
    body = "Closes #42\nFixes #42\nResolves #42"
    assert mp._extract_closing_issues(body) == [42]


def test_extract_returns_empty_when_no_keyword(mp) -> None:
    assert mp._extract_closing_issues("body without keyword") == []


def test_extract_handles_empty_body(mp) -> None:
    assert mp._extract_closing_issues("") == []


def test_extract_case_insensitive(mp) -> None:
    body = "CLOSES #1\nfixes #2\nResolves #3"
    assert sorted(mp._extract_closing_issues(body)) == [1, 2, 3]


# --- unticked-box detection ------------------------------------------


def test_unticked_boxes_detects_dash_style(mp) -> None:
    body = "- [ ] First\n- [x] Second\n- [ ] Third"
    assert len(mp._unticked_boxes(body)) == 2


def test_unticked_boxes_handles_indentation(mp) -> None:
    body = "  - [ ] one\n    - [ ] two\n- [x] three"
    assert len(mp._unticked_boxes(body)) == 2


def test_unticked_boxes_returns_empty_for_ticked(mp) -> None:
    body = "- [x] Done\n- [x] Also done"
    assert mp._unticked_boxes(body) == []


def test_unticked_boxes_returns_empty_for_no_boxes(mp) -> None:
    body = "## Plain prose section with no checkboxes."
    assert mp._unticked_boxes(body) == []


# --- pr title pattern ------------------------------------------------


def test_pr_title_pattern_returns_declared(mp, titles) -> None:
    p = mp._pr_title_pattern(titles)
    assert p == r"^(feat|fix|docs|test|refactor|chore|ci)(\([^)]+\))?: .+$"


def test_pr_title_pattern_returns_none_when_missing(mp) -> None:
    assert mp._pr_title_pattern({}) is None


def test_pr_title_pattern_matches_valid_titles(mp, titles) -> None:
    import re

    pattern = mp._pr_title_pattern(titles)
    assert re.match(pattern, "feat(cli): add new dispatcher")
    assert re.match(pattern, "fix: address regression")
    assert re.match(pattern, "docs(readme): update install")


def test_pr_title_pattern_rejects_invalid_titles(mp, titles) -> None:
    import re

    pattern = mp._pr_title_pattern(titles)
    assert re.match(pattern, "Sandbox: install CLI") is None
    assert re.match(pattern, "[Task] add CLI") is None


# --- squash-merge subject regression (issue #33) ---------------------
#
# The merge command itself — `--squash --subject <PR title>`, no
# `--delete-branch` — is `_lib.pr_merge.squash_merge`, shared with done-work;
# its #33 subject regression lives in test_pm_pr_merge_lib.py. Here: merge-pr
# hands the gate-validated PR title through to it (see the sequencing tests).


# --- CI-status gate (#498) -------------------------------------------


def test_gh_get_pr_requests_status_rollup(mp, monkeypatch) -> None:
    """The PR fetch must request `statusCheckRollup` so the CI gate can read it."""
    import subprocess

    captured: list[list[str]] = []

    def fake_gh_run(args, config, **kwargs):
        captured.append(list(args))
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="{}",
            stderr="",
        )

    monkeypatch.setattr(mp, "gh_run", fake_gh_run)
    mp._gh_get_pr(496, {})
    argv = captured[0]
    json_idx = argv.index("--json")
    assert "statusCheckRollup" in argv[json_idx + 1], (
        "the PR view must fetch statusCheckRollup for the #498 CI gate"
    )


def _identity(mp):
    return mp.Identity(github_login="octocat", email="octo@example.com")


def test_ci_bypass_audit_body_follows_schema_template(mp) -> None:
    """Audit body matches validation-severity.yaml's `Bypassed by <name> <<email>>: <reason>`."""
    key = mp._ci_bypass_audit_key("advisory changeset guard", "sha1")
    body = mp._ci_bypass_audit_body(
        _identity(mp),
        "advisory changeset guard on a decision-only PR",
        ("changeset-guard (FAILURE)",),
        key,
    )
    assert body.startswith(mp.CI_BYPASS_AUDIT_MARKER)
    assert body.splitlines()[-1] == key
    assert "Bypassed by octocat <octo@example.com>: " in body
    assert "advisory changeset guard on a decision-only PR" in body
    assert "changeset-guard (FAILURE)" in body


def test_post_ci_bypass_audit_posts_comment(mp, monkeypatch) -> None:
    """A bypass posts the audit comment to the PR (no existing stamp)."""
    import subprocess

    captured: list[list[str]] = []

    def fake_gh_run(args, config, **kwargs):
        captured.append(list(args))
        # `gh pr view --json comments` → no prior audit comment.
        if "view" in args:
            return subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout='{"comments": []}',
                stderr="",
            )
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mp, "gh_run", fake_gh_run)
    ok = mp._post_ci_bypass_audit(
        496,
        "deliberate override",
        _identity(mp),
        ("x (FAILURE)",),
        {},
    )
    assert ok is True
    comment_calls = [c for c in captured if "comment" in c]
    assert comment_calls, "expected a `gh pr comment` call posting the audit"
    argv = comment_calls[0]
    body_idx = argv.index("--body")
    assert "Bypassed by octocat" in argv[body_idx + 1]


def test_post_ci_bypass_audit_idempotent_skip(mp, monkeypatch) -> None:
    """The own, unedited audit comment for the same bypass (exact body) is not
    re-posted."""
    import json
    import subprocess

    captured: list[list[str]] = []
    key = mp._ci_bypass_audit_key("override", "sha1")
    prior = mp._ci_bypass_audit_body(
        _identity(mp),
        "override",
        ("x (FAILURE)",),
        key,
        "sha1",
    )

    def fake_gh_run(args, config, **kwargs):
        captured.append(list(args))
        if "view" in args:
            existing = json.dumps(
                {
                    "comments": [
                        {
                            "body": prior,
                            "viewerDidAuthor": True,
                            "includesCreatedEdit": False,
                        }
                    ]
                }
            )
            return subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout=existing,
                stderr="",
            )
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mp, "gh_run", fake_gh_run)
    ok = mp._post_ci_bypass_audit(
        496,
        "override",
        _identity(mp),
        ("x (FAILURE)",),
        {},
        head="sha1",
    )
    assert ok is True
    assert not [c for c in captured if "comment" in c], (
        "must not re-post when the exact own audit comment already exists"
    )


def test_post_ci_bypass_audit_reports_gh_failure(mp, monkeypatch) -> None:
    """A gh failure posting the comment returns False (caller aborts before merge)."""
    import subprocess

    def fake_gh_run(args, config, **kwargs):
        if "view" in args:
            return subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout='{"comments": []}',
                stderr="",
            )
        return subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="",
            stderr="boom",
        )

    monkeypatch.setattr(mp, "gh_run", fake_gh_run)
    ok = mp._post_ci_bypass_audit(
        496,
        "override",
        _identity(mp),
        ("x (FAILURE)",),
        {},
    )
    assert ok is False


# ---- CI override is the dedicated --bypass-ci flag (#498) ------------
#
# main()-level: the CI gate is overridable ONLY by --bypass-ci. merge-pr
# has no bare --bypass for the CI gate — a red check with no --bypass-ci
# hard-refuses; --bypass-ci clears it, posts the audit, and merges.


def _wire_merge_seams(
    mp, monkeypatch, *, rollup, head_branch="fix/42-slug", cross_repository=False, state="open"
):
    """Stub merge-pr's heavy seams so main() reaches the CI gate on *rollup*.

    `calls["order"]` records the post-merge side-effects (merge, hooks, remote
    ref delete, local cleanup) so a test can assert their sequence; the merge
    mechanic is stubbed on `_lib.pr_merge`, the module merge-pr calls through.
    The base merges directly — the merge-queue tests (#1011) rewire the
    reading — and GitHub reports the PR merged once the stubbed merge has run.
    The clone's record of what follows a merge is `calls["records"]`, kept in
    memory across the runs of one test and never written to the real clone.
    """
    calls = {"merged": False, "ci_audit": False, "order": [], "merge_kwargs": {}, "records": {}}

    monkeypatch.setattr(mp, "resolve_capability_root", lambda arg: Path("/cap"))
    monkeypatch.setattr(mp, "load_adopter_config", lambda root: {})
    monkeypatch.setattr(mp, "_read_members", lambda root, loader: [])
    monkeypatch.setattr(
        mp,
        "resolve_invoker_identity",
        lambda config=None: mp.Identity(github_login="octocat", email="o@e.com"),
    )
    monkeypatch.setattr(
        mp,
        "check_membership",
        lambda members, invoker: type(
            "MR",
            (),
            {"allowed": True, "refusal_message": None},
        )(),
    )
    monkeypatch.setattr(mp.session_guard, "enforce", lambda **kw: True)
    # This file targets merge-pr's CI / checkbox gates, not the #747 prerequisite gate (covered in
    # test_pm_bootstrap_gate*.py); the fake capability root above has no tree
    # to stamp, so neutralise the gate here.
    monkeypatch.setattr(mp.bootstrap_gate, "enforce", lambda *a, **kw: True)
    monkeypatch.setattr(
        mp,
        "_read_yaml",
        lambda path, loader: {"formats": {"pr": {"pattern": r"^fix: .+$"}}},
    )
    monkeypatch.setattr(
        mp,
        "_gh_get_pr",
        lambda pr_number, config: {
            "title": "fix: a thing",
            "body": "Closes #42\n## Test plan\n- [x] ok",
            "state": state,
            "url": "http://pr/99",
            "headRefName": head_branch,
            "headRefOid": "sha-head",
            "statusCheckRollup": rollup,
            "isCrossRepository": cross_repository,
        },
    )
    monkeypatch.setattr(
        mp,
        "_gather_unticked_findings",
        lambda pr_number, pr_body, closing, config: {},
    )

    def _stub_ci_audit(pr_number, reason, invoker, checks, config, *, head=""):
        calls["ci_audit"] = True
        calls["ci_audit_head"] = head
        return True

    def _stub_merge(pr_number, *, pr_title, admin, config, head_oid="", allow_foreign_repo=False):
        calls["merged"] = True
        calls["merge_kwargs"] = {"pr_title": pr_title, "admin": admin}
        calls["merge_head"] = head_oid
        calls["order"].append(("merged", pr_number))
        return True

    def _stub_hooks(name, **kwargs):
        calls["order"].append(("hooks", name))

    def _stub_delete_branch(pr_number, merged_head, config, *, allow_foreign_repo, **kwargs):
        calls.setdefault("deletions", []).append((pr_number, merged_head, allow_foreign_repo))
        calls.setdefault("rerun_notes", []).append(kwargs.get("rerun_note", ""))
        calls["order"].append(("remote_delete", merged_head))
        # What became of the branch on GitHub: deleted, unless a test says.
        return calls.get("remote_outcome", "deleted")

    def _stub_cleanup_local(branch, config, **kwargs):
        calls.setdefault("cross", []).append(kwargs.get("cross_repository"))
        calls["merged_head"] = kwargs.get("merged_head")
        calls["remote"] = kwargs.get("remote")
        calls["order"].append(("local_cleanup", branch))

    monkeypatch.setattr(mp, "_post_ci_bypass_audit", _stub_ci_audit)
    monkeypatch.setattr(mp.pr_merge, "squash_merge", _stub_merge)
    monkeypatch.setattr(mp.pr_merge, "delete_branch", _stub_delete_branch)
    monkeypatch.setattr(mp.pr_merge, "cleanup_local", _stub_cleanup_local)
    monkeypatch.setattr(mp, "fire_hooks", _stub_hooks)

    def write_record(pr_number, state, head_oid):
        calls["records"][pr_number] = mp._Record(state, head_oid, "2026-10-01T12:00:00+00:00")

    monkeypatch.setattr(mp, "_read_record", lambda pr_number: calls["records"].get(pr_number))
    monkeypatch.setattr(mp, "_write_record", write_record)

    def no_queue(pr_number, config):
        return pull_request_backbone.reading(
            mp.merge_queue, has_queue=False, pr_state="MERGED" if calls["merged"] else "OPEN"
        )

    monkeypatch.setattr(mp.merge_queue, "read", no_queue)
    return calls


_MP_RED = [{"name": "tests", "status": "COMPLETED", "conclusion": "FAILURE"}]
_MP_GREEN = [{"name": "tests", "status": "COMPLETED", "conclusion": "SUCCESS"}]


def _run_merge_main(mp, monkeypatch, argv):
    import sys

    monkeypatch.setattr(sys, "argv", ["merge-pr.py", *argv])
    return mp.main()


def test_merge_red_ci_no_bypass_ci_refuses(mp, monkeypatch, capsys):
    """A red CI with no --bypass-ci hard-refuses and does not merge."""
    calls = _wire_merge_seams(mp, monkeypatch, rollup=_MP_RED)
    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes"])
    assert rc == 1
    assert calls["merged"] is False
    err = capsys.readouterr().err
    assert "CI-status gate" in err
    assert "--bypass-ci" in err


def test_merge_bypass_ci_clears_red_ci_and_posts_audit(mp, monkeypatch):
    """--bypass-ci overrides the CI gate, posts the audit, then merges."""
    calls = _wire_merge_seams(mp, monkeypatch, rollup=_MP_RED)
    rc = _run_merge_main(mp, monkeypatch, ["99", "--bypass-ci", "advisory", "--yes"])
    assert rc == 0
    assert calls["ci_audit"] is True
    assert calls["ci_audit_head"] == "sha-head", "keyed on the PR head (#902)"
    assert calls["merged"] is True


def test_merge_bypass_ci_empty_reason_refused(mp, monkeypatch, capsys):
    """--bypass-ci with a whitespace-only reason is refused before merge."""
    calls = _wire_merge_seams(mp, monkeypatch, rollup=_MP_RED)
    rc = _run_merge_main(mp, monkeypatch, ["99", "--bypass-ci", "   ", "--yes"])
    assert rc == 1
    assert calls["merged"] is False
    assert "non-empty reason" in capsys.readouterr().err


def test_merge_help_shows_bypass_ci_not_bare_bypass(mp, monkeypatch, capsys):
    """merge-pr's --help lists --bypass-ci as the CI override; no bare --bypass."""
    import sys

    monkeypatch.setattr(sys, "argv", ["merge-pr.py", "--help"])
    with pytest.raises(SystemExit):
        mp.main()
    out = capsys.readouterr().out
    assert "--bypass-ci" in out, "merge-pr must expose --bypass-ci"
    assert "--bypass " not in out and "--bypass\n" not in out, (
        "merge-pr must not carry a bare --bypass for the CI gate"
    )


def test_merge_green_ci_no_bypass_needed(mp, monkeypatch):
    """A green CI merges with no --bypass-ci and posts no CI audit."""
    calls = _wire_merge_seams(mp, monkeypatch, rollup=_MP_GREEN)
    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes"])
    assert rc == 0
    assert calls["merged"] is True
    assert calls["ci_audit"] is False


# --- post-merge sequence: hooks, then best-effort cleanup (#882) --------
#
# merge-pr shares done-work's merge mechanic (`_lib.pr_merge`): squash-merge
# without `--delete-branch`, fire the after-merge hooks, then have the backbone
# delete the head branch on GitHub at the head that merged (#1255) and tidy the
# local checkout, as warnings that never fail the verb. That structurally
# retires the #587 special case (a head
# branch checked out in a worktree used to make `gh pr merge --delete-branch`
# exit non-zero after the remote merge had landed): the local delete now just
# warns.


def test_merge_sequence_is_merge_hooks_remote_delete_local_cleanup(mp, monkeypatch):
    """merge → after_merge_pr hooks → remote ref delete → local cleanup, in
    that order, with the gate-validated PR title handed to the merge."""
    calls = _wire_merge_seams(mp, monkeypatch, rollup=_MP_GREEN)
    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes"])
    assert rc == 0
    assert calls["order"] == [
        ("merged", 99),
        ("hooks", "after_merge_pr"),
        ("remote_delete", "sha-head"),
        ("local_cleanup", "fix/42-slug"),
    ]
    assert calls["merge_kwargs"] == {"pr_title": "fix: a thing", "admin": False}
    # Pinned to the head the gates read, and the clean-up keyed on it.
    assert calls["merge_head"] == calls["merged_head"] == "sha-head"
    # The clone records that the hooks fired, so no later run fires them again.
    assert calls["records"][99].state == mp._RAN
    assert calls["records"][99].head_oid == "sha-head"


@pytest.mark.parametrize("remote", ["deleted", "kept", "unconfirmed"])
def test_the_deletion_says_a_rerun_does_not_retry_it_and_hands_on_its_outcome(
    mp, monkeypatch, remote
):
    """The record that the hooks fired is written before the deletion, so a
    re-run returns before it: the line the deletion prints says the command it
    names is the only way to retry (#1255). What became of the branch on
    GitHub is handed to the local clean-up."""
    calls = _wire_merge_seams(mp, monkeypatch, rollup=_MP_GREEN)
    calls["remote_outcome"] = remote
    assert _run_merge_main(mp, monkeypatch, ["99", "--yes"]) == 0
    assert calls["rerun_notes"] == [
        "A re-run of `merge-pr 99` does not retry it: that command is the only way to."
    ]
    assert calls["remote"] == remote


def test_merge_passes_admin_through(mp, monkeypatch):
    calls = _wire_merge_seams(mp, monkeypatch, rollup=_MP_GREEN)
    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes", "--admin"])
    assert rc == 0
    assert calls["merge_kwargs"]["admin"] is True


def test_merge_failure_exits_3_and_skips_hooks_and_cleanup(mp, monkeypatch):
    """A failed remote merge is a gh failure (exit 3); nothing after it runs."""
    calls = _wire_merge_seams(mp, monkeypatch, rollup=_MP_GREEN)

    def failing_merge(pr_number, *, pr_title, admin, config, head_oid="", allow_foreign_repo=False):
        calls["order"].append(("merged", pr_number))
        return False

    monkeypatch.setattr(mp.pr_merge, "squash_merge", failing_merge)
    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes"])
    assert rc == 3
    assert calls["order"] == [("merged", 99)]


def test_head_branch_checked_out_in_worktree_is_a_warning_not_a_failure(
    mp,
    monkeypatch,
    capsys,
):
    """#587's trigger under the shared mechanic: the head branch is checked
    out in a worktree, so the local `branch -D` is refused. The merge and the
    hooks complete, the verb exits 0, and the refusal is a warning."""
    import subprocess

    real_cleanup = mp.pr_merge.cleanup_local
    calls = _wire_merge_seams(mp, monkeypatch, rollup=_MP_GREEN)
    monkeypatch.setattr(mp.pr_merge, "cleanup_local", real_cleanup)
    branch_err = "error: cannot delete branch 'fix/42-slug' used by worktree at '/repo/wt-42'"
    seen: list[list[str]] = []

    def fake_run(argv, **kwargs):
        seen.append(list(argv))
        if argv[:2] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(argv, 0, stdout="sha-head\n", stderr="")
        if argv[:2] == ["git", "rev-list"]:
            return subprocess.CompletedProcess(argv, 0, stdout="0\n", stderr="")
        if argv[:3] == ["git", "branch", "-D"]:
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr=branch_err)
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(mp.pr_merge.subprocess, "run", fake_run)
    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes"])

    err = capsys.readouterr().err
    assert rc == 0
    assert calls["merged"] is True
    assert ("hooks", "after_merge_pr") in calls["order"]
    assert ("remote_delete", "sha-head") in calls["order"]
    assert ["git", "branch", "-D", "fix/42-slug"] in seen
    assert f"[warn] git branch -D fix/42-slug failed: {branch_err}" in err
    assert not [ln for ln in err.splitlines() if ln.lower().startswith("error:")]


def test_missing_head_branch_skips_the_local_cleanup_with_a_warning(mp, monkeypatch, capsys):
    """No `headRefName` on the PR ⇒ the merge and hooks still run, and the
    backbone, which reads the head branch itself, is still asked to delete
    it; the local clean-up is skipped with a warning rather than deleting an
    empty ref."""
    calls = _wire_merge_seams(mp, monkeypatch, rollup=_MP_GREEN, head_branch="")
    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes"])
    assert rc == 0
    assert [kind for kind, _ in calls["order"]] == ["merged", "hooks", "remote_delete"]
    assert "no head branch" in capsys.readouterr().err


def test_dry_run_describes_the_outcome_not_the_flag(mp, monkeypatch, capsys):
    """`--dry-run` names the squash + subject and the head-branch deletion
    without invoking gh, and no longer advertises `--delete-branch`."""
    calls = _wire_merge_seams(mp, monkeypatch, rollup=_MP_GREEN)
    rc = _run_merge_main(mp, monkeypatch, ["99", "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0
    assert calls["order"] == []
    assert "[dry-run] gh pr merge --squash --subject 'fix: a thing'" in out
    assert "--delete-branch" not in out
    assert "remote head branch deleted" in out


def test_fork_pr_merge_passes_cross_repository_to_cleanup(mp, monkeypatch):
    """merge-pr reads isCrossRepository from the PR and hands it to the local
    clean-up, so a fork PR's head name never drives a local delete; whether
    the head branch on GitHub may be deleted is the backbone's to decide, from
    its own reading (it refuses a fork's)."""
    calls = _wire_merge_seams(mp, monkeypatch, rollup=_MP_GREEN, cross_repository=True)
    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes"])
    assert rc == 0
    assert calls["cross"] == [True]
    assert calls["deletions"] == [(99, "sha-head", False)]


@pytest.mark.parametrize(
    ("how", "flag", "passed_on"),
    [
        ("flag", True, True),
        ("terminal", False, True),
        ("same-repo", False, False),
        ("undetermined", False, False),
    ],
    ids=["flag", "yes-at-the-prompt", "same-repo", "undetermined"],
)
def test_the_head_branch_is_deleted_by_the_backbone_at_the_head_that_merged(
    mp, monkeypatch, how, flag, passed_on
):
    """After the hooks, the head branch on GitHub is the backbone's to delete,
    at the head the PR merged at; the operator's confirmation at the verb —
    the flag, or a yes at its prompt — is passed on to the backbone's guard,
    as the merge's is, and nothing else is (#1254, #1255)."""
    calls = _wire_merge_seams(mp, monkeypatch, rollup=_MP_GREEN)
    passage = mp.session_guard.Passage(True, how, flag=flag)
    monkeypatch.setattr(mp.session_guard, "enforce", lambda **kw: passage)
    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes"])
    assert rc == 0
    assert calls["deletions"] == [(99, "sha-head", passed_on)]


# --- a base that merges through a queue (#1011) -------------------------
#
# The queue is the only path to such a base. merge-pr hands the PR to it
# through the same landing done-work makes (`_lib.pr_merge.land`), waits for
# the merge, and fires its after-merge hooks only once GitHub reports the PR
# merged; a run that returns while the PR is queued exits 4, and a later run
# completes it.


def _queued(mp, **fields):
    base = {
        "has_queue": True,
        "merge_method": "SQUASH",
        "pr_id": "PR_node",
        "pr_state": "OPEN",
        "head_oid": "sha-head",
    }
    return pull_request_backbone.reading(mp.merge_queue, **{**base, **fields})


def _wire_queue(mp, monkeypatch, readings, **seams):
    """merge-pr's seams, with a base whose queue answers `readings` in turn
    (the last repeated; an exception is raised) — to merge-pr and to the
    backbone's wait alike — an enqueue that records itself, and a clock the
    wait's sleeps advance."""
    calls = _wire_merge_seams(mp, monkeypatch, rollup=_MP_GREEN, **seams)
    remaining = list(readings)

    def read(pr_number, config):
        reading = remaining.pop(0) if len(remaining) > 1 else remaining[0]
        if isinstance(reading, Exception):
            raise reading
        return reading

    def enqueue(pr_number, *, config, head_oid="", allow_foreign_repo=False):
        calls["order"].append(("enqueued", pr_number))
        calls["enqueue_head"] = head_oid
        return True

    now = [0.0]

    def sleep(seconds):
        now[0] += seconds

    monkeypatch.setattr(mp.merge_queue, "read", read)
    monkeypatch.setattr(
        mp.merge_queue, "squash_commit_defaults", lambda config: ("PR_TITLE", "PR_BODY")
    )
    monkeypatch.setattr(mp.pr_merge, "enqueue", enqueue)
    pull_request_backbone.in_process(
        monkeypatch, mp.merge_queue, read=read, sleep=sleep, clock=lambda: now[0]
    )
    return calls


_AFTER_THE_MERGE = [
    ("hooks", "after_merge_pr"),
    ("remote_delete", "sha-head"),
    ("local_cleanup", "fix/42-slug"),
]


def test_a_queued_base_enqueues_and_fires_the_hooks_once_merged(mp, monkeypatch, capsys):
    calls = _wire_queue(
        mp,
        monkeypatch,
        [
            _queued(mp),
            _queued(mp),
            _queued(mp, in_queue=True, position=1),
            _queued(mp, pr_state="MERGED", merged_at="t"),
        ],
    )
    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes"])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert calls["merged"] is False
    assert calls["order"] == [("enqueued", 99), *_AFTER_THE_MERGE]
    assert calls["enqueue_head"] == "sha-head"
    assert "  queue: the base branch merges through a queue; PR #99 not in the queue" in out
    assert "  merged PR #99 through the queue" in out
    assert "[ok] merged: http://pr/99" in out


def test_no_wait_returns_queued_and_fires_nothing(mp, monkeypatch, capsys):
    calls = _wire_queue(mp, monkeypatch, [_queued(mp), _queued(mp), _queued(mp, in_queue=True)])
    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes", "--no-wait"])
    out = capsys.readouterr().out
    assert rc == mp.EXIT_ACCEPTED == 4
    assert calls["order"] == [("enqueued", 99)]
    assert "[queued] PR #99 is in the merge queue for the base branch" in out
    assert "Run `merge-pr 99` again once it has merged" in out
    # What follows the merge is owed, at the head the gates checked.
    assert calls["records"][99] == mp._Record(mp._OWED, "sha-head", "2026-10-01T12:00:00+00:00")


def test_a_queue_lost_sight_of_says_so_rather_than_that_nothing_merged(mp, monkeypatch, capsys):
    """Enqueued, then no reading can be taken: the PR may have merged since, so
    exit 4 does not claim it has not, and the steps are owed for a re-run."""
    calls = _wire_queue(
        mp,
        monkeypatch,
        [_queued(mp), _queued(mp), mp.merge_queue.Unreadable("HTTP 502")],
    )
    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes"])
    captured = capsys.readouterr()
    assert rc == 4
    assert calls["order"] == [("enqueued", 99)]
    assert "[warn] lost sight of the merge queue: HTTP 502" in captured.err
    assert (
        "[queued] PR #99 was handed to the merge queue for the base branch, and whether it "
        "has merged since could not be read. Run `merge-pr 99` again once it has merged"
    ) in captured.out
    assert calls["records"][99].state == mp._OWED


def test_a_merge_gh_only_enqueued_fires_no_hook(mp, monkeypatch, capsys):
    """gh exits 0 having only enqueued: GitHub not reporting the PR merged, the
    after-merge hooks never fire and the branch is not deleted."""
    calls = _wire_queue(
        mp,
        monkeypatch,
        [
            _queued(mp, has_queue=False),
            _queued(mp, has_queue=False),
            _queued(mp, in_queue=True),
        ],
    )
    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes", "--no-wait"])
    assert rc == 4
    assert calls["order"] == [("merged", 99)]
    assert "GitHub does not report PR #99 merged" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("argv", "refusal"),
    [
        (["--admin"], "--admin would merge around the queue"),
        (["--bypass-ci", "flaky"], "--bypass-ci cannot bypass a check there"),
    ],
    ids=["admin", "bypass-ci"],
)
def test_what_would_go_around_the_queue_is_refused_before_any_gate(
    mp, monkeypatch, capsys, argv, refusal
):
    calls = _wire_queue(mp, monkeypatch, [_queued(mp)])
    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes", *argv])
    assert rc == 1
    assert calls["order"] == []
    assert calls["ci_audit"] is False
    assert refusal in capsys.readouterr().err


def test_the_dry_run_says_it_would_enqueue(mp, monkeypatch, capsys):
    calls = _wire_queue(mp, monkeypatch, [_queued(mp)])
    rc = _run_merge_main(mp, monkeypatch, ["99", "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0
    assert calls["order"] == []
    assert "[dry-run] gh pr merge 99 --auto --match-head-commit sha-hea would enqueue it" in out


# A later run on a merged PR (#1011): no gate runs again, and what follows the
# merge runs once — for a merge the queue made, or one a run from this clone
# left owed — keyed on the head the PR merged at. The clone's record says when
# it has run.

_QUEUE_MERGED = {"pr_state": "MERGED", "merged_at": "t", "ever_queued": True}


def test_a_later_run_completes_a_pr_the_queue_merged(mp, monkeypatch, capsys):
    calls = _wire_queue(
        mp,
        monkeypatch,
        [_queued(mp, head_oid="sha-merged", **_QUEUE_MERGED)],
        state="MERGED",
    )
    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes"])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert calls["order"] == [
        ("hooks", "after_merge_pr"),
        ("remote_delete", "sha-merged"),
        ("local_cleanup", "fix/42-slug"),
    ]
    assert "  PR #99 merged through the merge queue for the base branch (merged at t)" in out
    assert "completing what follows the merge" in out
    # Both deletions are guarded by the head the PR merged at, as GitHub says.
    assert calls["merged_head"] == "sha-merged"
    assert calls["records"][99].state == mp._RAN


def test_a_run_after_the_completion_does_nothing_and_says_so(mp, monkeypatch, capsys):
    calls = _wire_queue(mp, monkeypatch, [_queued(mp, **_QUEUE_MERGED)], state="MERGED")
    assert _run_merge_main(mp, monkeypatch, ["99", "--yes"]) == 0
    capsys.readouterr()
    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes"])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert calls["order"] == _AFTER_THE_MERGE, "the hooks and the clean-up ran once"
    assert (
        "[ok] PR #99 has merged, and its after-merge hooks already fired from this clone at "
        "2026-10-01T12:00:00+00:00; nothing is left to do."
    ) in out


def test_a_pr_someone_else_merged_without_a_queue_is_still_refused(mp, monkeypatch, capsys):
    calls = _wire_queue(
        mp,
        monkeypatch,
        [_queued(mp, has_queue=False, pr_state="MERGED", merged_at="t")],
        state="MERGED",
    )
    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes"])
    assert rc == 1
    assert calls["order"] == []
    assert calls["records"] == {}
    assert (
        "[refused] PR #99 merged without going through a merge queue, by someone else as far "
        "as this clone knows: no run from it left anything after that merge to complete. "
        "Nothing was run."
    ) in capsys.readouterr().err


def test_a_direct_merge_github_cannot_confirm_is_completed_by_a_rerun(mp, monkeypatch, capsys):
    """gh accepts the direct merge, then GitHub cannot be read: the PR may have
    merged, so the run neither calls it queued nor fires anything, records the
    steps as owed and exits 4. A re-run from this clone finds it merged — not
    through a queue — and completes it; the run after that does nothing."""
    calls = _wire_queue(
        mp,
        monkeypatch,
        [
            _queued(mp, has_queue=False),
            _queued(mp, has_queue=False),
            mp.merge_queue.Unreadable("HTTP 502"),
            mp.merge_queue.Unreadable("HTTP 502"),
            _queued(mp, has_queue=False, pr_state="MERGED", merged_at="t"),
        ],
    )
    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes"])
    captured = capsys.readouterr()
    assert rc == mp.EXIT_ACCEPTED == 4
    assert calls["order"] == [("merged", 99)]
    assert "[queued]" not in captured.out
    assert "could not confirm that PR #99 merged: HTTP 502. Reading it again." in captured.err
    assert (
        "[unconfirmed] gh accepted the merge of PR #99 into the base branch, but GitHub could "
        "not be read to confirm that it merged: HTTP 502. Nothing after the merge has run. "
        "Run `merge-pr 99` again from this clone once GitHub answers"
    ) in captured.out
    assert calls["records"][99].state == mp._OWED

    opened = mp._gh_get_pr
    monkeypatch.setattr(
        mp, "_gh_get_pr", lambda n, config: {**opened(n, config), "state": "MERGED"}
    )
    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes"])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert calls["order"] == [("merged", 99), *_AFTER_THE_MERGE]
    assert "a run from this clone returned before it saw the merge" in out
    assert calls["records"][99].state == mp._RAN

    assert _run_merge_main(mp, monkeypatch, ["99", "--yes"]) == 0
    assert calls["order"] == [("merged", 99), *_AFTER_THE_MERGE]
    assert "nothing is left to do" in capsys.readouterr().out


def test_a_merge_with_no_answer_back_that_merged_fires_the_hooks(mp, monkeypatch, capsys):
    """The backbone's run ended after gh accepted the merge, without saying so:
    GitHub reports the PR merged, so it is the merge — the hooks fire now,
    rather than a re-run refusing it as merged by someone else."""
    calls = _wire_merge_seams(mp, monkeypatch, rollup=_MP_GREEN)

    def no_answer_back(
        pr_number, *, pr_title, admin, config, head_oid="", allow_foreign_repo=False
    ):
        calls["merged"] = True
        calls["order"].append(("merged", pr_number))
        return None

    monkeypatch.setattr(mp.pr_merge, "squash_merge", no_answer_back)
    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes"])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert calls["order"] == [("merged", 99), *_AFTER_THE_MERGE]
    assert calls["records"][99].state == mp._RAN


def test_a_merge_with_no_answer_back_github_cannot_settle_is_owed(mp, monkeypatch, capsys):
    """Neither the backbone nor GitHub can say what the merge came to: the run
    exits 4, unconfirmed, with the after-merge steps recorded as owed — never
    "nothing merged", which would leave a merge without its hooks."""
    calls = _wire_merge_seams(mp, monkeypatch, rollup=_MP_GREEN)

    def no_answer_back(
        pr_number, *, pr_title, admin, config, head_oid="", allow_foreign_repo=False
    ):
        calls["order"].append(("asked", pr_number))
        return None

    def read(pr_number, config):
        if calls["order"]:
            raise mp.merge_queue.Unreadable("HTTP 502")
        return pull_request_backbone.reading(mp.merge_queue, has_queue=False, pr_state="OPEN")

    monkeypatch.setattr(mp.pr_merge, "squash_merge", no_answer_back)
    monkeypatch.setattr(mp.merge_queue, "read", read)
    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes"])
    out = capsys.readouterr().out
    assert rc == mp.EXIT_ACCEPTED == 4
    assert calls["order"] == [("asked", 99)]
    assert (
        "[unconfirmed] the merge of PR #99 into the base branch got no answer back, and "
        "GitHub could not be read since to tell whether it merged or entered the merge "
        "queue: HTTP 502. Read where PR #99 stands with `pkit pull-request read 99`. Nothing "
        "after the merge has run."
    ) in out
    assert calls["records"][99] == mp._Record(mp._OWED, "sha-head", "2026-10-01T12:00:00+00:00")


def _merge_never_answered(mp, monkeypatch, *, answered_from: int = 0):
    """merge-pr's seams, with the real merge request through the backbone in
    this process: the backbone's `gh` merge is ended at its bound — never
    answered — until the `answered_from`th one (0: never), which merges. The
    PR reads open, on a base without a queue, until `state["merged"]`. A
    clock the backbone's settling sleeps advance."""
    real_merge = mp.pr_merge.squash_merge
    calls = _wire_merge_seams(mp, monkeypatch, rollup=_MP_GREEN)
    monkeypatch.setattr(mp.pr_merge, "squash_merge", real_merge)
    state = {"merged": False, "asked": 0}

    def read(pr_number, config):
        merged = state["merged"]
        return pull_request_backbone.reading(
            mp.merge_queue,
            has_queue=False,
            pr_state="MERGED" if merged else "OPEN",
            merged_at="t" if merged else "",
            head_oid="sha-head",
        )

    def gh(argv):
        state["asked"] += 1
        if answered_from and state["asked"] >= answered_from:
            state["merged"] = True
            return subprocess.CompletedProcess(list(argv), 0, stdout="", stderr="")
        raise subprocess.TimeoutExpired(list(argv), 30.0)

    now = [0.0]

    def sleep(seconds):
        now[0] += seconds

    monkeypatch.setattr(mp.merge_queue, "read", read)
    pull_request_backbone.in_process(
        monkeypatch, mp.merge_queue, gh=gh, read=read, sleep=sleep, clock=lambda: now[0]
    )
    return calls, state


def test_a_merge_not_seen_made_that_shows_later_is_completed_by_a_rerun(mp, monkeypatch, capsys):
    """The merge got no answer, and the backbone's two readings did not see it
    made (#1256): the run exits 3, recording the after-merge steps as owed —
    the service may still apply it — and says how it ends. The service applies
    it after all: a re-run from this clone finds the PR merged, without a
    queue, and completes it — the hooks fire and the head branch is deleted at
    the head it merged at — rather than refusing it as merged by someone else."""
    calls, state = _merge_never_answered(mp, monkeypatch)
    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes"])
    captured = capsys.readouterr()
    assert rc == 3
    assert calls["order"] == []
    assert "and was not seen made on two readings" in captured.err
    assert "error: the merge of PR #99 was not seen made" in captured.err
    assert "Run `merge-pr 99` again from this clone" in captured.err
    assert calls["records"][99].state == mp._OWED

    state["merged"] = True
    opened = mp._gh_get_pr
    monkeypatch.setattr(
        mp, "_gh_get_pr", lambda n, config: {**opened(n, config), "state": "MERGED"}
    )
    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes"])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "a run from this clone returned before it saw the merge" in out
    assert calls["order"] == _AFTER_THE_MERGE
    assert calls["deletions"] == [(99, "sha-head", False)]
    assert calls["records"][99].state == mp._RAN


def test_a_retry_that_merges_replaces_what_an_earlier_run_left_owed(mp, monkeypatch, capsys):
    """The rule for a stale owed record: the run that fires the hooks records
    that it did, whichever run that is. A retry that merges the PR as a first
    run would fires them once and leaves the record `ran`, so nothing an
    earlier run left owed outlives the merge."""
    calls, _ = _merge_never_answered(mp, monkeypatch, answered_from=2)
    assert _run_merge_main(mp, monkeypatch, ["99", "--yes"]) == 3
    assert calls["records"][99].state == mp._OWED
    capsys.readouterr()

    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes"])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert calls["order"] == _AFTER_THE_MERGE
    assert calls["records"][99].state == mp._RAN


def test_a_merge_github_refused_owes_nothing(mp, monkeypatch, capsys):
    """GitHub answered the merge with a refusal: nothing it may yet act on was
    sent, so nothing is owed, and a PR someone else merges later is refused
    as before."""
    real_merge = mp.pr_merge.squash_merge
    calls = _wire_merge_seams(mp, monkeypatch, rollup=_MP_GREEN)
    monkeypatch.setattr(mp.pr_merge, "squash_merge", real_merge)

    def refusing(argv):
        return subprocess.CompletedProcess(
            list(argv), 1, stdout="", stderr="GraphQL: Pull request is not mergeable"
        )

    pull_request_backbone.in_process(monkeypatch, mp.merge_queue, gh=refusing)
    assert _run_merge_main(mp, monkeypatch, ["99", "--yes"]) == 3
    assert calls["records"] == {}


def test_the_record_is_kept_in_the_clones_git_directory(mp, tmp_path, monkeypatch):
    import subprocess

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    monkeypatch.chdir(tmp_path)
    assert mp._read_record(7) is None
    mp._write_record(7, mp._OWED, "sha-a")
    owed = mp._read_record(7)
    assert (owed.state, owed.head_oid) == (mp._OWED, "sha-a") and owed.at
    path = tmp_path / ".git" / "pkit" / "merge-pr" / "7.json"
    assert path.is_file()
    mp._write_record(7, mp._RAN, "sha-b")
    assert mp._read_record(7).state == mp._RAN
    path.write_text("{not json", encoding="utf-8")
    assert mp._read_record(7) is None, "an unreadable record is no record"


def test_outside_a_clone_there_is_no_record(mp, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    assert mp._read_record(7) is None
    with pytest.raises(mp._Unrecorded, match="not inside a git clone"):
        mp._write_record(7, mp._RAN, "sha-a")


def test_an_unreadable_queue_merges_nothing(mp, monkeypatch, capsys):
    calls = _wire_merge_seams(mp, monkeypatch, rollup=_MP_GREEN)

    def unreadable(pr_number, config):
        raise mp.merge_queue.Unreadable("HTTP 502")

    monkeypatch.setattr(mp.merge_queue, "read", unreadable)
    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes"])
    assert rc == 3
    assert calls["order"] == []
    assert "cannot tell how the base branch merges: HTTP 502. Nothing was merged." in (
        capsys.readouterr().err
    )
