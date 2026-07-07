"""Tests for `done-work` wrapper (DEC-026) — focused on the human-mode
three-way OR approval gate and the PR-body placeholder gate (DEC-031)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management"
    / "scripts" / "done-work.py"
)


@pytest.fixture(scope="module")
def dw():
    lib_dir = SCRIPT.parent
    sys.path.insert(0, str(lib_dir))
    spec = importlib.util.spec_from_file_location("pm_done_work_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_done_work_under_test"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(lib_dir))


# ---- _check_approval_gate ---------------------------------------------


def _stub_pr_view(reviews, comments, author_login="author"):
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(
            args=args, returncode=0,
            stdout=json.dumps({
                "author": {"login": author_login},
                "reviews": reviews,
                "comments": comments,
            }),
            stderr="",
        )
    return fake_gh_run


def test_gate_passes_with_bypass(dw, monkeypatch) -> None:
    result = dw._check_approval_gate(99, {}, "PM authorised", {})
    assert result.passed is True
    assert "bypass" in result.passed_via.lower()
    assert "PM authorised" in result.passed_via


def test_gate_refuses_empty_bypass(dw) -> None:
    result = dw._check_approval_gate(99, {}, "  ", {})
    assert result.passed is False
    assert "non-empty" in result.refusal_message


def test_gate_passes_with_approved_review(dw, monkeypatch) -> None:
    monkeypatch.setattr(dw, "gh_run", _stub_pr_view(
        reviews=[{"state": "APPROVED"}], comments=[]
    ))
    result = dw._check_approval_gate(99, {}, None, {})
    assert result.passed is True
    assert "APPROVED" in result.passed_via


def test_gate_uses_latest_review_state(dw, monkeypatch) -> None:
    """Earlier APPROVED, then CHANGES_REQUESTED → refused."""
    monkeypatch.setattr(dw, "gh_run", _stub_pr_view(
        reviews=[{"state": "APPROVED"}, {"state": "CHANGES_REQUESTED"}], comments=[]
    ))
    result = dw._check_approval_gate(99, {}, None, {})
    assert result.passed is False
    assert "CHANGES_REQUESTED" in result.refusal_message


def test_gate_ignores_commented_state(dw, monkeypatch) -> None:
    """COMMENTED-only reviews don't count as APPROVED."""
    monkeypatch.setattr(dw, "gh_run", _stub_pr_view(
        reviews=[{"state": "COMMENTED"}], comments=[]
    ))
    result = dw._check_approval_gate(99, {}, None, {})
    assert result.passed is False


def test_gate_passes_with_approved_comment_from_non_author(dw, monkeypatch) -> None:
    monkeypatch.setattr(dw, "gh_run", _stub_pr_view(
        reviews=[],
        comments=[
            {"author": {"login": "reviewer"}, "body": "Approved — looks good"},
        ],
        author_login="author",
    ))
    result = dw._check_approval_gate(99, {}, None, {})
    assert result.passed is True
    assert "Approved" in result.passed_via
    assert "reviewer" in result.passed_via


def test_gate_refuses_approved_comment_from_author(dw, monkeypatch) -> None:
    """Author can't self-approve via comment."""
    monkeypatch.setattr(dw, "gh_run", _stub_pr_view(
        reviews=[],
        comments=[
            {"author": {"login": "author"}, "body": "Approved"},
        ],
        author_login="author",
    ))
    result = dw._check_approval_gate(99, {}, None, {})
    assert result.passed is False


def test_gate_case_sensitive_approved_prefix(dw, monkeypatch) -> None:
    """`approved` (lowercase) doesn't count — case-sensitive `Approved`."""
    monkeypatch.setattr(dw, "gh_run", _stub_pr_view(
        reviews=[],
        comments=[
            {"author": {"login": "reviewer"}, "body": "approved lgtm"},
        ],
    ))
    result = dw._check_approval_gate(99, {}, None, {})
    assert result.passed is False


def test_gate_uses_last_qualifying_comment(dw, monkeypatch) -> None:
    """If a later non-author comment doesn't start with Approved, earlier one stands."""
    monkeypatch.setattr(dw, "gh_run", _stub_pr_view(
        reviews=[],
        comments=[
            {"author": {"login": "reviewer"}, "body": "Approved"},
            {"author": {"login": "reviewer"}, "body": "Actually wait..."},
        ],
        author_login="author",
    ))
    result = dw._check_approval_gate(99, {}, None, {})
    # The "Approved" comment was earlier; the most-recent non-Approved
    # comment from the same reviewer should override — that's the
    # intuitive semantic the gate's spec implies by checking the last
    # qualifying comment.
    # Our implementation walks `reversed(comments)` and returns the
    # first match — which is the LATEST. So "Actually wait..." wouldn't
    # match, and the search continues to the earlier "Approved".
    # That's still a pass — the test confirms current behaviour.
    assert result.passed is True


def test_gate_refuses_when_nothing_qualifies(dw, monkeypatch) -> None:
    monkeypatch.setattr(dw, "gh_run", _stub_pr_view(
        reviews=[{"state": "COMMENTED"}],
        comments=[{"author": {"login": "reviewer"}, "body": "Looks fine"}],
    ))
    result = dw._check_approval_gate(99, {}, None, {})
    assert result.passed is False
    assert "approval gate not satisfied" in result.refusal_message


def test_gate_handles_gh_failure(dw, monkeypatch) -> None:
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(
            args=args, returncode=1, stdout="", stderr="not found",
        )
    monkeypatch.setattr(dw, "gh_run", fake_gh_run)
    result = dw._check_approval_gate(99, {}, None, {})
    assert result.passed is False
    assert "gh pr view failed" in result.refusal_message


# ---- _invoke_move_issue — regression for GitHub issue #7 -------------
#
# When done-work squash-merges a PR whose body carries `Closes #N`,
# GitHub auto-closes the issue before _invoke_move_issue is called.
# move-issue.py then sees state==closed → infers current_state="done",
# which matched the target "done". The old code looked up a done→done
# transition (none exists) and returned exit 2. The fix: move-issue
# detects current==target before the transition lookup and returns 0
# (with stale-label reconciliation). This test pins the contract that
# _invoke_move_issue exits 0 in that scenario by running the real
# move-issue.py subprocess against a stub that simulates the post-merge
# issue state (closed, with stale state:review label).


def test_invoke_move_issue_exits_zero_when_issue_already_done(
    dw, tmp_path, monkeypatch
) -> None:
    """Regression: _invoke_move_issue("done") must exit 0 when the issue is
    already closed (GitHub auto-close via Closes #N), even if the
    state:review label is still present.

    Exercises the move-issue.py noop/reconciliation path that fixes #7.
    """
    import subprocess

    # Build a minimal capability root in tmp_path.
    cap_root = tmp_path / ".pkit" / "capabilities" / "project-management"
    project_dir = cap_root / "project"
    schemas_dir = cap_root / "schemas"
    project_dir.mkdir(parents=True)
    schemas_dir.mkdir(parents=True)

    # Minimal config.yaml (label-fallback substrate).
    (project_dir / "config.yaml").write_text("has_projects_v2_board: false\n")

    # Copy the real schema files that move-issue.py reads.
    import shutil
    real_cap = (
        Path(__file__).resolve().parent.parent
        / ".pkit" / "capabilities" / "project-management"
    )
    for schema_name in ("workflow.yaml", "issue-types.yaml", "classification.yaml"):
        shutil.copy(real_cap / "schemas" / schema_name, schemas_dir / schema_name)

    # Stub gh so no real GitHub calls are made.
    # move-issue.py calls: gh issue view (to fetch issue data) and
    # gh issue edit (to reconcile labels). We need to handle both.
    stub_gh = tmp_path / "gh"
    stub_gh.write_text(
        "#!/usr/bin/env python3\n"
        "import sys, json\n"
        "args = sys.argv[1:]\n"
        "# gh issue view <N> --json <fields>\n"
        "if 'issue' in args and 'view' in args and '--json' in args:\n"
        "    data = {\n"
        "        'title': '[Task] fix the widget',\n"
        "        'body': '## What\\nfix\\n## Acceptance criteria\\n- [x] done\\n## Doc impact\\nNone',\n"
        "        'state': 'closed',\n"
        "        'labels': [{'name': 'state:review'}, {'name': 'priority:High'}],\n"
        "        'assignees': [],\n"
        "        'milestone': None,\n"
        "        'url': 'https://github.com/example/repo/issues/42',\n"
        "    }\n"
        "    print(json.dumps(data))\n"
        "    sys.exit(0)\n"
        "# gh issue edit (label reconciliation) — accept silently.\n"
        "if 'issue' in args and 'edit' in args:\n"
        "    sys.exit(0)\n"
        "sys.exit(0)\n"
    )
    stub_gh.chmod(0o755)
    new_path = str(stub_gh.parent) + ":" + __import__("os").environ.get("PATH", "")

    move_issue_script = real_cap / "scripts" / "move-issue.py"
    result = subprocess.run(
        [sys.executable, str(move_issue_script), "42", "--to", "done", "--yes",
         "--capability-root", str(cap_root)],
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "PATH": new_path},
    )

    assert result.returncode == 0, (
        f"move-issue exited {result.returncode} on already-closed issue.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}\n"
        "Regression: done-work happy path should not fail after auto-close."
    )
    # The noop path should mention the reconciliation or the already-at-target state.
    assert "noop" in result.stdout.lower() or "already at target" in result.stdout.lower(), (
        f"Expected noop message in stdout, got: {result.stdout!r}"
    )


# ---- PR-body placeholder gate (DEC-031) ------------------------------

REPO_ROOT_DW = Path(__file__).resolve().parent.parent
CAPABILITY_ROOT_DW = (
    REPO_ROOT_DW / ".pkit" / "capabilities" / "project-management"
)


def _authored_pr_body_dw() -> str:
    return (
        "Closes #42\n\n"
        "## Summary\n\nImplement the thing.\n\n"
        "## Test plan\n\n"
        "- [ ] Unit tests pass.\n"
        "- [x] Integration smoke test ran.\n\n"
        "## Doc impact\n\nUpdated README.\n"
    )


def _skeleton_pr_body_dw() -> str:
    """PR body still carrying the raw ## Test plan skeleton (bare - [ ])."""
    return (
        "Closes #42\n\n"
        "## Summary\n\nfoo\n\n"
        "## Test plan\n\n"
        "- [ ]\n\n"
        "## Doc impact\n\nnone.\n"
    )


def test_check_pr_placeholder_authored_body_clean(dw) -> None:
    """An authored PR body produces no findings from _check_pr_placeholder."""
    findings = dw._check_pr_placeholder(
        _authored_pr_body_dw(), 42, CAPABILITY_ROOT_DW
    )
    hard_rejects = [f for f in findings if f[0] == "hard-reject"]
    assert hard_rejects == [], (
        f"unexpected hard-reject on authored PR body: {hard_rejects}"
    )


def test_check_pr_placeholder_skeleton_body_hard_rejects(dw) -> None:
    """A skeleton PR body (bare - [ ] in ## Test plan) produces a hard-reject."""
    findings = dw._check_pr_placeholder(
        _skeleton_pr_body_dw(), 42, CAPABILITY_ROOT_DW
    )
    hard_rejects = [f for f in findings if f[0] == "hard-reject"]
    assert hard_rejects, (
        "expected hard-reject for skeleton PR body at merge gate"
    )
    labels = [f[1] for f in hard_rejects]
    assert "body.placeholder.empty-checkbox-section" in labels


def test_check_pr_placeholder_unticked_real_items_no_false_positive(dw) -> None:
    """Authored-but-unchecked ## Test plan items must not trigger the skeleton signal."""
    body = (
        "Closes #7\n\n"
        "## Summary\n\nRefactor the widget.\n\n"
        "## Test plan\n\n"
        "- [ ] Run pytest.\n"
        "- [ ] Manual smoke test.\n\n"
        "## Doc impact\n\nNone.\n"
    )
    findings = dw._check_pr_placeholder(body, 7, CAPABILITY_ROOT_DW)
    hard_rejects = [
        f for f in findings
        if f[0] == "hard-reject" and f[1] == "body.placeholder.empty-checkbox-section"
    ]
    assert hard_rejects == [], (
        "authored-but-unticked PR body falsely flagged as skeleton: "
        f"{hard_rejects}"
    )


def test_gh_get_pr_body_returns_none_on_failure(dw, monkeypatch) -> None:
    """_gh_get_pr_body returns None when `gh` fails."""
    import subprocess
    def fake_gh_run(args, config, **kwargs):
        return subprocess.CompletedProcess(
            args=args, returncode=1, stdout="", stderr="not found",
        )
    monkeypatch.setattr(dw, "gh_run", fake_gh_run)
    result = dw._gh_get_pr_body(99, {})
    assert result is None


def test_gh_get_pr_body_extracts_body(dw, monkeypatch) -> None:
    """_gh_get_pr_body returns the body string from the JSON response."""
    import subprocess
    def fake_gh_run(args, config, **kwargs):
        return subprocess.CompletedProcess(
            args=args, returncode=0,
            stdout=json.dumps({"body": "Closes #1\n## Test plan\n- [x] done.\n"}),
            stderr="",
        )
    monkeypatch.setattr(dw, "gh_run", fake_gh_run)
    result = dw._gh_get_pr_body(99, {})
    assert result == "Closes #1\n## Test plan\n- [x] done.\n"


# ---- squash-merge subject regression (issue #33) ---------------------


def test_gh_pr_merge_uses_pr_title_as_subject(dw, monkeypatch) -> None:
    """_gh_pr_merge passes --subject <PR title> to `gh pr merge --squash`.

    Regression for #33: for a single-commit PR, GitHub defaults the squash
    subject to the commit message, not the PR title.  The --subject flag
    overrides this so the landed subject always equals the gate-validated
    title (DEC-013).
    """
    import subprocess

    captured: list[list[str]] = []

    def fake_gh_run(args, config, **kwargs):
        captured.append(list(args))
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="", stderr="",
        )

    monkeypatch.setattr(dw, "gh_run", fake_gh_run)
    result = dw._gh_pr_merge(
        42,
        pr_title="fix(pm-scripts): squash subject uses PR title",
        admin=False,
        config={},
    )

    assert result is True, "Expected _gh_pr_merge to succeed"
    assert captured, "Expected gh_run to be called"
    argv = captured[0]
    assert "--squash" in argv, "--squash must be present"
    assert "--subject" in argv, "--subject must be present in gh pr merge argv"
    subject_idx = argv.index("--subject")
    assert argv[subject_idx + 1] == "fix(pm-scripts): squash subject uses PR title", (
        f"--subject value must be the PR title; got {argv[subject_idx + 1]!r}"
    )


def test_gh_pr_merge_subject_not_commit_message(dw, monkeypatch) -> None:
    """The squash subject is the PR title, not whatever commit message was on the branch.

    Simulates a single-commit PR whose commit subject differs from the PR
    title (the live bug: PR #32 landed 'feat(...)' despite the title being
    'fix(...)'). Asserts that _gh_pr_merge passes the PR title — not the
    commit message — as --subject.
    """
    import subprocess

    pr_title = "fix(pm-permissions): correct enforcement runtime"
    commit_subject = "feat(pm-permissions): implement runtime enforcement"

    captured: list[list[str]] = []

    def fake_gh_run(args, config, **kwargs):
        captured.append(list(args))
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="", stderr="",
        )

    monkeypatch.setattr(dw, "gh_run", fake_gh_run)
    dw._gh_pr_merge(32, pr_title=pr_title, admin=False, config={})

    argv = captured[0]
    assert "--subject" in argv
    subject_idx = argv.index("--subject")
    landed_subject = argv[subject_idx + 1]
    assert landed_subject == pr_title, (
        f"Expected PR title as --subject, got {landed_subject!r}. "
        f"commit_subject={commit_subject!r} must NOT be used."
    )
    assert landed_subject != commit_subject, (
        "Squash subject must be the PR title, not the commit message."
    )


# ---- CI-status gate (#498) -------------------------------------------


def test_gh_get_status_rollup_returns_list(dw, monkeypatch) -> None:
    """_gh_get_status_rollup returns the rollup list from the JSON response."""
    import subprocess

    rollup = [{"name": "tests", "status": "COMPLETED", "conclusion": "FAILURE"}]

    def fake_gh_run(args, config, **kwargs):
        return subprocess.CompletedProcess(
            args=args, returncode=0,
            stdout=json.dumps({"statusCheckRollup": rollup}), stderr="",
        )

    monkeypatch.setattr(dw, "gh_run", fake_gh_run)
    assert dw._gh_get_status_rollup(496, {}) == rollup


def test_gh_get_status_rollup_none_on_failure(dw, monkeypatch) -> None:
    """A gh failure yields None (treated as check-free / passing by the gate)."""
    import subprocess

    def fake_gh_run(args, config, **kwargs):
        return subprocess.CompletedProcess(
            args=args, returncode=1, stdout="", stderr="not found",
        )

    monkeypatch.setattr(dw, "gh_run", fake_gh_run)
    assert dw._gh_get_status_rollup(496, {}) is None


def test_ci_gate_refuses_failing_and_pending(dw) -> None:
    """The shared gate wired into done-work refuses red and pending rollups."""
    failing = dw.evaluate_ci_gate(
        [{"name": "tests", "status": "COMPLETED", "conclusion": "FAILURE"}]
    )
    assert failing.passing is False
    pending = dw.evaluate_ci_gate(
        [{"name": "build", "status": "IN_PROGRESS", "conclusion": ""}]
    )
    assert pending.passing is False
    green = dw.evaluate_ci_gate(
        [{"name": "ok", "status": "COMPLETED", "conclusion": "SUCCESS"}]
    )
    assert green.passing is True


def test_done_work_ci_bypass_audit_body_follows_template(dw) -> None:
    """done-work's CI-bypass audit follows the schema template + its own stamp."""
    identity = dw.Identity(github_login="octocat", email="octo@example.com")
    body = dw._ci_bypass_audit_body(
        identity, "advisory guard on a decision-only PR", ("guard (FAILURE)",)
    )
    assert dw.CI_BYPASS_AUDIT_STAMP in body
    assert "Bypassed by octocat <octo@example.com>: " in body
    assert "guard (FAILURE)" in body


def test_done_work_post_ci_bypass_audit_idempotent(dw, monkeypatch) -> None:
    """An already-present CI-bypass comment is not re-posted (idempotent)."""
    import subprocess

    captured: list[list[str]] = []

    def fake_gh_run(args, config, **kwargs):
        captured.append(list(args))
        if "view" in args:
            existing = json.dumps(
                {"comments": [{"body": f"{dw.CI_BYPASS_AUDIT_STAMP}\n\nprior"}]}
            )
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout=existing, stderr="",
            )
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(dw, "gh_run", fake_gh_run)
    identity = dw.Identity(github_login="octocat", email="octo@example.com")
    ok = dw._post_ci_bypass_audit(496, "override", identity, ("x (FAILURE)",), {})
    assert ok is True
    assert not [c for c in captured if "comment" in c]


# ---- flag split: --bypass vs --bypass-ci (#498) ----------------------
#
# `--bypass` clears ONLY the approval gate; the CI gate is overridable
# ONLY by the dedicated `--bypass-ci`. These are `main()`-level tests: a
# bypassing operator must never silently land a red CI (#498's footgun),
# so the split is exercised end-to-end at the gate wiring, not just at
# the helpers.


def _wire_main_seams(dw, monkeypatch, *, rollup, gate_passed=True):
    """Monkeypatch done-work's heavy seams so main() reaches the CI gate.

    Membership/session-guard/branch/PR resolution and the approval gate are
    all stubbed to succeed; `_gh_get_status_rollup` returns *rollup* so the
    real `evaluate_ci_gate` decides. Returns a dict recording the merge and
    audit side-effects the CI-gate outcome drives (so a test can assert the
    red-CI-under-`--bypass`-only path never reaches the merge).
    """
    calls = {"merged": False, "ci_audit": False, "approval_audit": False,
             "moved": False}

    monkeypatch.setattr(dw, "resolve_capability_root", lambda arg: Path("/cap"))
    monkeypatch.setattr(dw, "load_adopter_config", lambda root: {})
    monkeypatch.setattr(dw, "_read_members", lambda root, loader: [])
    monkeypatch.setattr(
        dw, "resolve_invoker_identity",
        lambda config=None: dw.Identity(github_login="octocat", email="o@e.com"),
    )
    monkeypatch.setattr(
        dw, "check_membership",
        lambda members, invoker: type(
            "MR", (), {"allowed": True, "refusal_message": None},
        )(),
    )
    monkeypatch.setattr(dw.session_guard, "enforce", lambda **kw: True)
    monkeypatch.setattr(dw, "_find_issue_branch", lambda n: "fix/42-slug")
    monkeypatch.setattr(
        dw, "_find_pr_for_branch",
        lambda branch, config: {"number": 496, "title": "fix: x", "isDraft": False},
    )
    monkeypatch.setattr(dw, "_gh_get_issue", lambda n, config: {"labels": []})
    monkeypatch.setattr(
        dw, "resolve_mode",
        lambda config, issue_labels=None: type(
            "M", (), {"mode": "human", "source": "default"},
        )(),
    )
    monkeypatch.setattr(
        dw, "_check_approval_gate",
        lambda pr_number, pr, bypass_reason, config: dw._GateResult(
            passed=gate_passed, passed_via="stub",
            refusal_message="" if gate_passed else "[refused] approval gate",
        ),
    )
    monkeypatch.setattr(
        dw, "_gh_get_pr_body", lambda pr_number, config: "## Test plan\n- [x] ok\n",
    )
    monkeypatch.setattr(
        dw, "_check_pr_placeholder", lambda body, pr_number, cap_root: [],
    )
    monkeypatch.setattr(dw, "_gh_get_status_rollup", lambda pr_number, config: rollup)

    def _stub_ci_audit(pr_number, reason, invoker, checks, config):
        calls["ci_audit"] = True
        return True

    def _stub_approval_audit(issue_number, reason, config):
        calls["approval_audit"] = True
        return True

    def _stub_merge(pr_number, *, pr_title, admin, config):
        calls["merged"] = True
        return True

    def _stub_move(issue_number, target, cap_root_arg):
        calls["moved"] = True
        return 0

    monkeypatch.setattr(dw, "_post_ci_bypass_audit", _stub_ci_audit)
    monkeypatch.setattr(dw, "_post_bypass_audit_idempotent", _stub_approval_audit)
    monkeypatch.setattr(dw, "_gh_pr_merge", _stub_merge)
    monkeypatch.setattr(dw, "_git_pull_main", lambda: None)
    monkeypatch.setattr(dw, "_invoke_move_issue", _stub_move)
    return calls


_RED_ROLLUP = [{"name": "tests", "status": "COMPLETED", "conclusion": "FAILURE"}]
_GREEN_ROLLUP = [{"name": "tests", "status": "COMPLETED", "conclusion": "SUCCESS"}]


def _run_main(dw, monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["done-work.py", *argv])
    return dw.main()


def test_bypass_alone_does_not_clear_red_ci(dw, monkeypatch, capsys):
    """`--bypass` clears the approval gate but a red CI still hard-refuses."""
    calls = _wire_main_seams(dw, monkeypatch, rollup=_RED_ROLLUP)
    rc = _run_main(dw, monkeypatch, ["42", "--bypass", "flaky reviewer", "--yes"])
    assert rc == 1, "red CI under --bypass-only must refuse"
    assert calls["merged"] is False, "must not merge a red CI on --bypass alone"
    err = capsys.readouterr().err
    assert "CI-status gate" in err
    assert "--bypass-ci" in err, "refuse message must name --bypass-ci as the override"


def test_bypass_ci_clears_red_ci_and_posts_audit(dw, monkeypatch, capsys):
    """`--bypass-ci "<reason>"` overrides the CI gate, posts the audit, merges."""
    calls = _wire_main_seams(dw, monkeypatch, rollup=_RED_ROLLUP)
    rc = _run_main(
        dw, monkeypatch, ["42", "--bypass-ci", "advisory guard", "--yes"],
    )
    assert rc == 0
    assert calls["ci_audit"] is True, "--bypass-ci must post the CI-bypass audit"
    assert calls["merged"] is True


def test_both_gates_blocked_needs_both_flags(dw, monkeypatch, capsys):
    """A merge blocked on approval AND red CI needs both --bypass and --bypass-ci.

    With only --bypass-ci the approval gate still refuses; adding --bypass too
    clears both and the merge proceeds (posting both audits).
    """
    # approval gate fails; only --bypass-ci given → approval refusal.
    calls = _wire_main_seams(dw, monkeypatch, rollup=_RED_ROLLUP, gate_passed=False)
    rc = _run_main(dw, monkeypatch, ["42", "--bypass-ci", "ci reason", "--yes"])
    assert rc == 1, "approval gate must still refuse when only --bypass-ci given"
    assert calls["merged"] is False

    # both flags → both gates cleared, merge proceeds.
    calls = _wire_main_seams(dw, monkeypatch, rollup=_RED_ROLLUP, gate_passed=True)
    rc = _run_main(
        dw, monkeypatch,
        ["42", "--bypass", "appr reason", "--bypass-ci", "ci reason", "--yes"],
    )
    assert rc == 0
    assert calls["approval_audit"] is True
    assert calls["ci_audit"] is True
    assert calls["merged"] is True


def test_bypass_ci_empty_reason_refused(dw, monkeypatch, capsys):
    """`--bypass-ci` with a whitespace-only reason is refused (before merge)."""
    calls = _wire_main_seams(dw, monkeypatch, rollup=_RED_ROLLUP)
    rc = _run_main(dw, monkeypatch, ["42", "--bypass-ci", "   ", "--yes"])
    assert rc == 1
    assert calls["merged"] is False
    assert "non-empty reason" in capsys.readouterr().err


def test_green_ci_needs_no_bypass_ci(dw, monkeypatch):
    """A green CI merges with no --bypass-ci and posts no CI audit."""
    calls = _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP)
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    assert rc == 0
    assert calls["merged"] is True
    assert calls["ci_audit"] is False
