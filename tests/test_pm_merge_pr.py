"""Tests for project-management's merge-pr script.

Covers closing-issue extraction, checkbox detection, PR-title pattern
lookup, the CI-status gate, and the post-merge sequence (merge → hooks →
best-effort branch cleanup through the shared `_lib.pr_merge` mechanic).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "scripts"
    / "merge-pr.py"
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
            args=args, returncode=0, stdout="{}", stderr="",
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
    body = mp._ci_bypass_audit_body(
        _identity(mp), "advisory changeset guard on a decision-only PR",
        ("changeset-guard (FAILURE)",),
    )
    assert mp.CI_BYPASS_AUDIT_STAMP in body
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
                args=args, returncode=0,
                stdout='{"comments": []}', stderr="",
            )
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mp, "gh_run", fake_gh_run)
    ok = mp._post_ci_bypass_audit(
        496, "deliberate override", _identity(mp), ("x (FAILURE)",), {},
    )
    assert ok is True
    comment_calls = [c for c in captured if "comment" in c]
    assert comment_calls, "expected a `gh pr comment` call posting the audit"
    argv = comment_calls[0]
    body_idx = argv.index("--body")
    assert "Bypassed by octocat" in argv[body_idx + 1]


def test_post_ci_bypass_audit_idempotent_skip(mp, monkeypatch) -> None:
    """An already-present audit comment (by stamp) is not re-posted."""
    import subprocess

    captured: list[list[str]] = []

    def fake_gh_run(args, config, **kwargs):
        captured.append(list(args))
        if "view" in args:
            existing = f'{{"comments": [{{"body": "{mp.CI_BYPASS_AUDIT_STAMP}\\n\\nprior"}}]}}'
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout=existing, stderr="",
            )
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mp, "gh_run", fake_gh_run)
    ok = mp._post_ci_bypass_audit(
        496, "override", _identity(mp), ("x (FAILURE)",), {},
    )
    assert ok is True
    assert not [c for c in captured if "comment" in c], (
        "must not re-post when the stamped audit comment already exists"
    )


def test_post_ci_bypass_audit_reports_gh_failure(mp, monkeypatch) -> None:
    """A gh failure posting the comment returns False (caller aborts before merge)."""
    import subprocess

    def fake_gh_run(args, config, **kwargs):
        if "view" in args:
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout='{"comments": []}', stderr="",
            )
        return subprocess.CompletedProcess(
            args=args, returncode=1, stdout="", stderr="boom",
        )

    monkeypatch.setattr(mp, "gh_run", fake_gh_run)
    ok = mp._post_ci_bypass_audit(
        496, "override", _identity(mp), ("x (FAILURE)",), {},
    )
    assert ok is False


# ---- CI override is the dedicated --bypass-ci flag (#498) ------------
#
# main()-level: the CI gate is overridable ONLY by --bypass-ci. merge-pr
# has no bare --bypass for the CI gate — a red check with no --bypass-ci
# hard-refuses; --bypass-ci clears it, posts the audit, and merges.


def _wire_merge_seams(mp, monkeypatch, *, rollup, head_branch="fix/42-slug"):
    """Stub merge-pr's heavy seams so main() reaches the CI gate on *rollup*.

    `calls["order"]` records the post-merge side-effects (merge, hooks, remote
    ref delete, local cleanup) so a test can assert their sequence; the merge
    mechanic is stubbed on `_lib.pr_merge`, the module merge-pr calls through.
    """
    calls = {"merged": False, "ci_audit": False, "order": [], "merge_kwargs": {}}

    monkeypatch.setattr(mp, "resolve_capability_root", lambda arg: Path("/cap"))
    monkeypatch.setattr(mp, "load_adopter_config", lambda root: {})
    monkeypatch.setattr(mp, "_read_members", lambda root, loader: [])
    monkeypatch.setattr(
        mp, "resolve_invoker_identity",
        lambda config=None: mp.Identity(github_login="octocat", email="o@e.com"),
    )
    monkeypatch.setattr(
        mp, "check_membership",
        lambda members, invoker: type(
            "MR", (), {"allowed": True, "refusal_message": None},
        )(),
    )
    monkeypatch.setattr(mp.session_guard, "enforce", lambda **kw: True)
    # This file targets merge-pr's CI / checkbox gates, not the #747 prerequisite gate (covered in
    # test_pm_bootstrap_gate*.py); the fake capability root above has no tree
    # to stamp, so neutralise the gate here.
    monkeypatch.setattr(mp.bootstrap_gate, "enforce", lambda *a, **kw: True)
    monkeypatch.setattr(
        mp, "_read_yaml",
        lambda path, loader: {"formats": {"pr": {"pattern": r"^fix: .+$"}}},
    )
    monkeypatch.setattr(
        mp, "_gh_get_pr",
        lambda pr_number, config: {
            "title": "fix: a thing", "body": "Closes #42\n## Test plan\n- [x] ok",
            "state": "open", "url": "http://pr/99", "headRefName": head_branch,
            "statusCheckRollup": rollup,
        },
    )
    monkeypatch.setattr(
        mp, "_gather_unticked_findings",
        lambda pr_number, pr_body, closing, config: {},
    )

    def _stub_ci_audit(pr_number, reason, invoker, checks, config):
        calls["ci_audit"] = True
        return True

    def _stub_merge(pr_number, *, pr_title, admin, config):
        calls["merged"] = True
        calls["merge_kwargs"] = {"pr_title": pr_title, "admin": admin}
        calls["order"].append(("merged", pr_number))
        return True

    def _stub_hooks(name, **kwargs):
        calls["order"].append(("hooks", name))

    def _stub_delete_remote(branch, config):
        calls["order"].append(("remote_delete", branch))

    def _stub_cleanup_local(branch, config):
        calls["order"].append(("local_cleanup", branch))

    monkeypatch.setattr(mp, "_post_ci_bypass_audit", _stub_ci_audit)
    monkeypatch.setattr(mp.pr_merge, "squash_merge", _stub_merge)
    monkeypatch.setattr(mp.pr_merge, "delete_remote_branch", _stub_delete_remote)
    monkeypatch.setattr(mp.pr_merge, "cleanup_local", _stub_cleanup_local)
    monkeypatch.setattr(mp, "fire_hooks", _stub_hooks)
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
# without `--delete-branch`, fire the after-merge hooks, then delete the remote
# head ref through the API and tidy the local checkout as warnings that never
# fail the verb. That structurally retires the #587 special case (a head
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
        ("remote_delete", "fix/42-slug"),
        ("local_cleanup", "fix/42-slug"),
    ]
    assert calls["merge_kwargs"] == {"pr_title": "fix: a thing", "admin": False}


def test_merge_passes_admin_through(mp, monkeypatch):
    calls = _wire_merge_seams(mp, monkeypatch, rollup=_MP_GREEN)
    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes", "--admin"])
    assert rc == 0
    assert calls["merge_kwargs"]["admin"] is True


def test_merge_failure_exits_3_and_skips_hooks_and_cleanup(mp, monkeypatch):
    """A failed remote merge is a gh failure (exit 3); nothing after it runs."""
    calls = _wire_merge_seams(mp, monkeypatch, rollup=_MP_GREEN)

    def failing_merge(pr_number, *, pr_title, admin, config):
        calls["order"].append(("merged", pr_number))
        return False

    monkeypatch.setattr(mp.pr_merge, "squash_merge", failing_merge)
    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes"])
    assert rc == 3
    assert calls["order"] == [("merged", 99)]


def test_head_branch_checked_out_in_worktree_is_a_warning_not_a_failure(
    mp, monkeypatch, capsys,
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
        if argv[:3] == ["git", "branch", "-D"]:
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr=branch_err)
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(mp.pr_merge.subprocess, "run", fake_run)
    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes"])

    err = capsys.readouterr().err
    assert rc == 0
    assert calls["merged"] is True
    assert ("hooks", "after_merge_pr") in calls["order"]
    assert ("remote_delete", "fix/42-slug") in calls["order"]
    assert ["git", "branch", "-D", "fix/42-slug"] in seen
    assert f"[warn] git branch -D fix/42-slug failed: {branch_err}" in err
    assert not [ln for ln in err.splitlines() if ln.lower().startswith("error:")]


def test_missing_head_branch_skips_cleanup_with_a_warning(mp, monkeypatch, capsys):
    """No `headRefName` on the PR ⇒ the merge and hooks still run; cleanup is
    skipped with a warning rather than deleting an empty ref."""
    calls = _wire_merge_seams(mp, monkeypatch, rollup=_MP_GREEN, head_branch="")
    rc = _run_merge_main(mp, monkeypatch, ["99", "--yes"])
    assert rc == 0
    assert [kind for kind, _ in calls["order"]] == ["merged", "hooks"]
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
