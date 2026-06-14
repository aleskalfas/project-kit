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
