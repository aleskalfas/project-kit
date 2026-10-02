"""Tests for `done-work` wrapper (DEC-026) — focused on the human-mode
three-way OR approval gate and the PR-body placeholder gate (DEC-031)."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest

from tests import pull_request_backbone

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts" / "done-work.py"


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


def _mark_bootstrapped(cap_root: Path) -> None:
    """Make a staged tree look like the bootstrapped project it stands in for.

    Every pm verb except the five setup/diagnosis ones refuses a project with no
    bootstrap stamp or no adopter config (the #747 prerequisite gate); a staged
    tree standing in for a live project is a bootstrapped one. The config is
    seeded only when absent, so a test that stages its own keeps it, and the
    stamp is left unbound (`repo:` null) so no git remote is needed in a tmp tree.
    """
    project = cap_root / "project"
    project.mkdir(parents=True, exist_ok=True)
    config = project / "config.yaml"
    if not config.is_file():
        config.write_text(
            "schema_version: 1\ndefault_branch: main\nworkstreams: []\n",
            encoding="utf-8",
        )
    (project / "bootstrap-stamp.yaml").write_text(
        "schema_version: 1\n"
        "bootstrap:\n"
        "  completed_at: '2026-01-01T00:00:00+00:00'\n"
        "  capability_version: 0.0.0-test\n"
        "  by: bootstrap\n"
        "  repo:\n",
        encoding="utf-8",
    )


def _stub_pr_view(reviews, comments, author_login="author"):
    def fake_gh_run(args, config, **kwargs):
        import subprocess

        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=json.dumps(
                {
                    "author": {"login": author_login},
                    "reviews": reviews,
                    "comments": comments,
                }
            ),
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
    monkeypatch.setattr(dw, "gh_run", _stub_pr_view(reviews=[{"state": "APPROVED"}], comments=[]))
    result = dw._check_approval_gate(99, {}, None, {})
    assert result.passed is True
    assert "APPROVED" in result.passed_via


def test_gate_uses_latest_review_state(dw, monkeypatch) -> None:
    """Earlier APPROVED, then CHANGES_REQUESTED → refused."""
    monkeypatch.setattr(
        dw,
        "gh_run",
        _stub_pr_view(reviews=[{"state": "APPROVED"}, {"state": "CHANGES_REQUESTED"}], comments=[]),
    )
    result = dw._check_approval_gate(99, {}, None, {})
    assert result.passed is False
    assert "CHANGES_REQUESTED" in result.refusal_message


def test_gate_ignores_commented_state(dw, monkeypatch) -> None:
    """COMMENTED-only reviews don't count as APPROVED."""
    monkeypatch.setattr(dw, "gh_run", _stub_pr_view(reviews=[{"state": "COMMENTED"}], comments=[]))
    result = dw._check_approval_gate(99, {}, None, {})
    assert result.passed is False


def test_gate_passes_with_approved_comment_from_non_author(dw, monkeypatch) -> None:
    monkeypatch.setattr(
        dw,
        "gh_run",
        _stub_pr_view(
            reviews=[],
            comments=[
                {"author": {"login": "reviewer"}, "body": "Approved — looks good"},
            ],
            author_login="author",
        ),
    )
    result = dw._check_approval_gate(99, {}, None, {})
    assert result.passed is True
    assert "Approved" in result.passed_via
    assert "reviewer" in result.passed_via


def test_gate_refuses_approved_comment_from_author(dw, monkeypatch) -> None:
    """Author can't self-approve via comment."""
    monkeypatch.setattr(
        dw,
        "gh_run",
        _stub_pr_view(
            reviews=[],
            comments=[
                {"author": {"login": "author"}, "body": "Approved"},
            ],
            author_login="author",
        ),
    )
    result = dw._check_approval_gate(99, {}, None, {})
    assert result.passed is False


def test_gate_case_sensitive_approved_prefix(dw, monkeypatch) -> None:
    """`approved` (lowercase) doesn't count — case-sensitive `Approved`."""
    monkeypatch.setattr(
        dw,
        "gh_run",
        _stub_pr_view(
            reviews=[],
            comments=[
                {"author": {"login": "reviewer"}, "body": "approved lgtm"},
            ],
        ),
    )
    result = dw._check_approval_gate(99, {}, None, {})
    assert result.passed is False


def test_gate_uses_last_qualifying_comment(dw, monkeypatch) -> None:
    """If a later non-author comment doesn't start with Approved, earlier one stands."""
    monkeypatch.setattr(
        dw,
        "gh_run",
        _stub_pr_view(
            reviews=[],
            comments=[
                {"author": {"login": "reviewer"}, "body": "Approved"},
                {"author": {"login": "reviewer"}, "body": "Actually wait..."},
            ],
            author_login="author",
        ),
    )
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
    monkeypatch.setattr(
        dw,
        "gh_run",
        _stub_pr_view(
            reviews=[{"state": "COMMENTED"}],
            comments=[{"author": {"login": "reviewer"}, "body": "Looks fine"}],
        ),
    )
    result = dw._check_approval_gate(99, {}, None, {})
    assert result.passed is False
    assert "approval gate not satisfied" in result.refusal_message


def test_gate_handles_gh_failure(dw, monkeypatch) -> None:
    def fake_gh_run(args, config, **kwargs):
        import subprocess

        return subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="",
            stderr="not found",
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


def test_invoke_move_issue_exits_zero_when_issue_already_done(dw, tmp_path, monkeypatch) -> None:
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
    _mark_bootstrapped(cap_root)

    # Copy the real schema files that move-issue.py reads.
    import shutil

    real_cap = (
        Path(__file__).resolve().parent.parent / ".pkit" / "capabilities" / "project-management"
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
        "        'body': '## What\\nfix\\n## Acceptance criteria\\n- [x] done\\n## Doc "
        "impact\\nNone',\n"
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
        [
            sys.executable,
            str(move_issue_script),
            "42",
            "--to",
            "done",
            "--yes",
            "--capability-root",
            str(cap_root),
        ],
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
CAPABILITY_ROOT_DW = REPO_ROOT_DW / ".pkit" / "capabilities" / "project-management"


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
    return "Closes #42\n\n## Summary\n\nfoo\n\n## Test plan\n\n- [ ]\n\n## Doc impact\n\nnone.\n"


def test_check_pr_placeholder_authored_body_clean(dw) -> None:
    """An authored PR body produces no findings from _check_pr_placeholder."""
    findings = dw._check_pr_placeholder(_authored_pr_body_dw(), 42, CAPABILITY_ROOT_DW)
    hard_rejects = [f for f in findings if f[0] == "hard-reject"]
    assert hard_rejects == [], f"unexpected hard-reject on authored PR body: {hard_rejects}"


def test_check_pr_placeholder_skeleton_body_hard_rejects(dw) -> None:
    """A skeleton PR body (bare - [ ] in ## Test plan) produces a hard-reject."""
    findings = dw._check_pr_placeholder(_skeleton_pr_body_dw(), 42, CAPABILITY_ROOT_DW)
    hard_rejects = [f for f in findings if f[0] == "hard-reject"]
    assert hard_rejects, "expected hard-reject for skeleton PR body at merge gate"
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
        f
        for f in findings
        if f[0] == "hard-reject" and f[1] == "body.placeholder.empty-checkbox-section"
    ]
    assert hard_rejects == [], (
        f"authored-but-unticked PR body falsely flagged as skeleton: {hard_rejects}"
    )


def test_gh_get_pr_body_returns_none_on_failure(dw, monkeypatch) -> None:
    """_gh_get_pr_body returns None when `gh` fails."""
    import subprocess

    def fake_gh_run(args, config, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="",
            stderr="not found",
        )

    monkeypatch.setattr(dw, "gh_run", fake_gh_run)
    result = dw._gh_get_pr_body(99, {})
    assert result is None


def test_gh_get_pr_body_extracts_body(dw, monkeypatch) -> None:
    """_gh_get_pr_body returns the body string from the JSON response."""
    import subprocess

    def fake_gh_run(args, config, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=json.dumps({"body": "Closes #1\n## Test plan\n- [x] done.\n"}),
            stderr="",
        )

    monkeypatch.setattr(dw, "gh_run", fake_gh_run)
    result = dw._gh_get_pr_body(99, {})
    assert result == "Closes #1\n## Test plan\n- [x] done.\n"


# ---- squash-merge subject regression (issue #33) ---------------------
#
# The merge command — `--squash --subject <PR title>`, no `--delete-branch` —
# is `_lib.pr_merge.squash_merge`, shared with merge-pr; its #33 subject
# regression lives in test_pm_pr_merge_lib.py. Here: done-work hands the
# gate-validated PR title (not any commit subject) through to it.


def test_main_hands_pr_title_to_the_shared_merge(dw, monkeypatch) -> None:
    """The landed squash subject is the PR title done-work validated, so a
    single-commit PR whose commit subject differs still lands under the title
    (DEC-013; #33)."""
    calls = _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP)
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    assert rc == 0
    assert calls["merge_kwargs"] == {"pr_title": "fix: x", "admin": False}


@pytest.mark.parametrize(
    ("passed", "flag", "passed_on"),
    [
        ("flag", True, True),
        ("terminal", False, True),
        ("same-repo", True, True),
        ("same-repo", False, False),
        ("undetermined", False, False),
    ],
)
def test_the_merge_carries_the_confirmation_the_guard_got_and_no_other(
    dw, monkeypatch, passed, flag, passed_on
) -> None:
    """The backbone runs its own cross-repository guard on the merge, with no
    terminal: done-work tells it the operator confirmed exactly when they did
    at done-work — the flag on its command line, whatever its own comparison
    found, or a yes at its prompt (#1254)."""
    calls = _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP)
    passage = dw.session_guard.Passage(True, passed, flag=flag)
    monkeypatch.setattr(dw.session_guard, "enforce", lambda **kw: passage)
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    assert rc == 0
    assert calls["merge_allow_foreign_repo"] is passed_on


@pytest.mark.parametrize(
    ("how", "flag", "confirmed"),
    [
        ("flag", True, True),
        ("terminal", False, True),
        ("same-repo", True, True),
        ("same-repo", False, False),
        ("undetermined", False, False),
    ],
    ids=["flag", "yes-at-the-prompt", "flag-same-repo", "same-repo", "undetermined"],
)
def test_the_verbs_it_starts_carry_the_confirmation_and_no_other(
    dw, monkeypatch, how, flag, confirmed
) -> None:
    """A confirmed landing is whole: the move-issue and close-issue runs that
    follow the merge are handed --allow-foreign-repo when the operator
    confirmed at done-work — the flag, or a yes at its prompt — so their own
    guards neither refuse nor ask again; and never otherwise (#1254)."""
    real_move, real_close = dw._invoke_move_issue, dw._invoke_close_issue
    _wire_main_seams(
        dw,
        monkeypatch,
        rollup=_GREEN_ROLLUP,
        pr_body=_TWO_ISSUE_PR_BODY,
        issues={42: _open_issue(_TICKED_BODY), 43: _open_issue(_TICKED_BODY)},
    )
    monkeypatch.setattr(dw, "_invoke_move_issue", real_move)
    monkeypatch.setattr(dw, "_invoke_close_issue", real_close)
    passage = dw.session_guard.Passage(True, how, flag=flag)
    monkeypatch.setattr(dw.session_guard, "enforce", lambda **kw: passage)
    started: list[list[str]] = []

    def run_sibling(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        started.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(dw.subprocess, "run", run_sibling)
    assert _run_main(dw, monkeypatch, ["42", "--yes"]) == 0
    assert sorted(Path(argv[1]).name for argv in started) == [
        "close-issue.py",
        "close-issue.py",
        "move-issue.py",
    ]
    assert [("--allow-foreign-repo" in argv) for argv in started] == [confirmed] * len(started)


def test_the_merge_is_pinned_to_the_head_the_agent_gate_checked(dw, monkeypatch) -> None:
    """A push between the gate and the merge must fail the merge, not land
    commits no verdict was judged against (#1179)."""
    gate = dw._GateResult(passed=True, passed_via="stub", head_oid="sha-gate")
    calls = _wire_main_seams(
        dw,
        monkeypatch,
        rollup=_GREEN_ROLLUP,
        mode="agent",
        agent_gate_result=gate,
    )
    assert _run_main(dw, monkeypatch, ["42", "--yes"]) == 0
    assert calls["merge_head"] == "sha-gate"


def test_without_an_agent_gate_the_merge_is_pinned_to_the_runs_head(dw, monkeypatch) -> None:
    calls = _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP)
    assert _run_main(dw, monkeypatch, ["42", "--yes"]) == 0
    assert calls["merge_head"] == "sha-head"


# ---- `run`, for a verb that composes done-work (`land-work`, #1203) ------
# A composing verb hands done-work the head it waited for the checks on and
# had reviewed — done-work lands that head or nothing — or asks it only to
# complete a PR that has merged. It decides on the kind of end `run` returns,
# never on the exit code, which one code covers several ends of.

_OPEN_PR = {"number": 496, "title": "fix: x", "isDraft": False, "headRefOid": "sha-head"}


def _lookups(dw, monkeypatch, **answers: Any) -> list[str]:
    """Stub the composed run's PR lookups: each state ("open", "merged") is
    answered with a `_PrLookup`; returns the states looked up, in order."""
    asked: list[str] = []

    def lookup(branch: str, state: str, fields: str, config: dict) -> Any:
        asked.append(state)
        return answers.get(state, dw._PrLookup())

    monkeypatch.setattr(dw, "_lookup_prs", lookup)
    return asked


def test_a_pinned_head_that_is_the_prs_head_merges_it(dw, monkeypatch) -> None:
    calls = _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP)
    _lookups(dw, monkeypatch, open=dw._PrLookup((_OPEN_PR,)))
    run = dw.run(["42", "--yes"], pinned_head="sha-head")
    assert (run.kind, run.exit_code) == (dw.MERGED, 0)
    assert calls["merge_head"] == "sha-head"


def test_a_pinned_head_the_pr_moved_from_stops_before_any_gate(dw, monkeypatch, capsys) -> None:
    calls = _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP)
    _lookups(dw, monkeypatch, open=dw._PrLookup((_OPEN_PR,)))
    run = dw.run(["42", "--yes"], pinned_head="sha-pinned")
    assert (run.kind, run.exit_code) == (dw.HEAD_MOVED, 3)
    assert calls["merged"] is False
    assert calls["order"] == []
    err = capsys.readouterr().err
    assert (
        "error: PR #496's head is sha-hea, not sha-pin, the head this run was asked to land"
    ) in err
    assert "Nothing was posted or merged, and #42 stays where it is." in err
    assert run.reason.startswith("error: PR #496's head is sha-hea, not sha-pin")


def test_a_pinned_head_the_agent_gate_did_not_judge_stops_before_the_merge(
    dw, monkeypatch, capsys
) -> None:
    """The PR moved between done-work's lookup and its gate's read: the
    verdicts were judged against a head nobody pinned, so nothing lands."""
    gate = dw._GateResult(passed=True, passed_via="stub", head_oid="sha-newer")
    calls = _wire_main_seams(
        dw,
        monkeypatch,
        rollup=_GREEN_ROLLUP,
        mode="agent",
        agent_gate_result=gate,
    )
    _lookups(dw, monkeypatch, open=dw._PrLookup((_OPEN_PR,)))
    run = dw.run(["42", "--yes"], pinned_head="sha-head")
    assert (run.kind, run.exit_code) == (dw.HEAD_MOVED, 3)
    assert calls["merged"] is False
    assert calls["moved"] is False
    assert "PR #496's head is sha-new, not sha-hea" in capsys.readouterr().err


def test_an_open_pr_lookup_gh_did_not_answer_changes_nothing(dw, monkeypatch, capsys) -> None:
    """No answer is not "no open PR": the composed run stops, and does not go
    looking for a merged PR to complete (#1203)."""
    calls = _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP)
    asked = _lookups(dw, monkeypatch, open=dw._PrLookup(problem="HTTP 502"))
    run = dw.run(["42", "--yes"], pinned_head="sha-head")
    assert (run.kind, run.exit_code) == (dw.UNREADABLE, 2)
    assert asked == ["open"]
    assert calls["merged"] is False
    assert "whether 'fix/42-slug' has an open PR could not be read: HTTP 502" in (
        capsys.readouterr().err
    )


def test_merged_only_refuses_an_open_pr_it_was_not_handed(dw, monkeypatch) -> None:
    """The composing verb found no open PR; one open now is a PR nobody
    checked, so nothing is gated, merged or completed — and a re-run, which
    pins it, can help."""
    calls = _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP)
    _lookups(dw, monkeypatch, open=dw._PrLookup((_OPEN_PR,)))
    run = dw.run(["42", "--yes"], merged_only=True)
    assert (run.kind, run.retry) == (dw.REFUSED, True)
    assert "PR #496 for 'fix/42-slug' is open" in run.reason
    assert calls["merged"] is False
    assert calls["order"] == []


def test_merged_only_with_no_answer_from_gh_changes_nothing(dw, monkeypatch) -> None:
    calls = _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP)
    _lookups(dw, monkeypatch, open=dw._PrLookup(problem="HTTP 502"))
    run = dw.run(["42", "--yes"], merged_only=True)
    assert run.kind == dw.UNREADABLE
    assert calls["order"] == []


def test_merged_only_with_a_merged_pr_lookup_unanswered_changes_nothing(dw, monkeypatch) -> None:
    _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP)
    monkeypatch.setattr(dw, "_read_issue_merges", lambda n, config: dw._IssueMerges([]))
    _lookups(dw, monkeypatch, merged=dw._PrLookup(problem="HTTP 502"))
    run = dw.run(["42", "--yes"], merged_only=True)
    assert run.kind == dw.UNREADABLE
    assert "whether 'fix/42-slug' has a merged PR could not be read" in run.reason


def test_merged_only_with_the_issue_unreadable_and_no_merged_pr_changes_nothing(
    dw, monkeypatch
) -> None:
    _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP)
    monkeypatch.setattr(
        dw, "_read_issue_merges", lambda n, config: dw._IssueMerges([], problem="HTTP 502")
    )
    _lookups(dw, monkeypatch)
    run = dw.run(["42", "--yes"], merged_only=True)
    assert run.kind == dw.UNREADABLE
    assert "whether a merged PR closes it could not be read: HTTP 502" in run.reason


def test_a_direct_run_still_reads_an_unanswered_lookup_as_no_open_pr(dw, monkeypatch) -> None:
    """A direct run's behaviour is unchanged: `_find_pr_for_branch` answers None
    when gh fails, as it always has."""
    monkeypatch.setattr(
        dw, "gh_run", lambda args, config, **k: subprocess.CompletedProcess(args, 1, "", "HTTP 502")
    )
    assert dw._find_pr_for_branch("fix/42-slug", {}) is None
    assert dw._lookup_prs("fix/42-slug", "open", "number", {}).problem == "HTTP 502"


def test_run_refuses_a_pinned_head_that_names_no_head(dw) -> None:
    with pytest.raises(ValueError):
        dw.run(["42"], pinned_head="")


@pytest.mark.parametrize(
    ("rollup", "retry"),
    [
        ([{"name": "tests", "status": "IN_PROGRESS"}], True),
        ([{"name": "tests", "status": "COMPLETED", "conclusion": "FAILURE"}], False),
    ],
)
def test_a_ci_refusal_says_whether_a_rerun_can_help(dw, monkeypatch, rollup, retry) -> None:
    """Checks still running are outlasted by a re-run; a failed check needs a
    change. Both exit 1, as before."""
    _wire_main_seams(dw, monkeypatch, rollup=rollup)
    run = dw.run(["42", "--yes"])
    assert (run.kind, run.exit_code, run.retry) == (dw.REFUSED, 1, retry)
    assert run.reason.startswith("[refused] CI-status gate for PR #496")


def test_a_gate_refusal_is_refused_with_its_first_line(dw, monkeypatch) -> None:
    _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP, gate_passed=False)
    run = dw.run(["42", "--yes"])
    assert (run.kind, run.exit_code, run.retry) == (dw.REFUSED, 1, False)
    assert run.reason == "[refused] approval gate"


def test_a_dry_run_and_a_declined_prompt_both_exit_0_and_are_told_apart(dw, monkeypatch) -> None:
    calls = _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP)
    planned = dw.run(["42", "--dry-run"])
    assert (planned.kind, planned.exit_code) == (dw.PLANNED, 0)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr("builtins.input", lambda prompt="": "n")
    declined = dw.run(["42"])
    assert (declined.kind, declined.exit_code) == (dw.DECLINED, 0)
    assert calls["merged"] is False


def test_a_step_after_the_merge_failing_is_owed_not_refused(dw, monkeypatch) -> None:
    """The merge stands; what failed after it is owed to a re-run."""
    calls = _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP)
    monkeypatch.setattr(dw, "_invoke_move_issue", lambda *a, **k: 1)
    run = dw.run(["42", "--yes"])
    assert (run.kind, run.exit_code) == (dw.FOLLOW_UP_OWED, 1)
    assert run.reason.startswith("[warn] PR merged but move-issue exited 1")
    assert calls["merged"] is True


def test_a_merge_request_gh_refused_can_be_retried(dw, monkeypatch) -> None:
    """The request failed and nothing merged — a push since, say, which the
    composing verb reads for itself. Exit 3, as before."""
    _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP)
    monkeypatch.setattr(dw.pr_merge, "squash_merge", lambda *a, **k: False)
    run = dw.run(["42", "--yes"])
    assert (run.kind, run.exit_code, run.retry) == (dw.REFUSED, 3, True)
    assert "the merge request for PR #496 did not go through" in run.reason


def test_a_queued_pr_is_queued(dw, monkeypatch) -> None:
    _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP)
    monkeypatch.setattr(
        dw.pr_merge, "land", lambda request, config: dw.pr_merge.Landing(dw.pr_merge.STILL_QUEUED)
    )
    run = dw.run(["42", "--yes"])
    assert (run.kind, run.exit_code) == (dw.QUEUED, dw.EXIT_ACCEPTED)
    assert run.reason.startswith("[queued] PR #496 was handed to the merge queue")


def test_main_reads_the_argv_it_is_given(dw, monkeypatch, capsys) -> None:
    """`main(argv)` parses `argv`, not the command line it was started with."""
    _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP)
    monkeypatch.setattr(sys, "argv", ["land-work.py", "42", "--bypass-reason", "x"])
    assert dw.main(["42", "--yes"]) == 0
    assert "DEPRECATED" not in capsys.readouterr().err


# ---- CI-status gate (#498) -------------------------------------------


def test_gh_get_status_rollup_returns_list(dw, monkeypatch) -> None:
    """_gh_get_status_rollup returns the rollup list from the JSON response."""
    import subprocess

    rollup = [{"name": "tests", "status": "COMPLETED", "conclusion": "FAILURE"}]

    def fake_gh_run(args, config, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=json.dumps({"statusCheckRollup": rollup}),
            stderr="",
        )

    monkeypatch.setattr(dw, "gh_run", fake_gh_run)
    assert dw._gh_get_status_rollup(496, {}) == rollup


def test_gh_get_status_rollup_none_on_failure(dw, monkeypatch) -> None:
    """A gh failure yields None (treated as check-free / passing by the gate)."""
    import subprocess

    def fake_gh_run(args, config, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="",
            stderr="not found",
        )

    monkeypatch.setattr(dw, "gh_run", fake_gh_run)
    assert dw._gh_get_status_rollup(496, {}) is None


def test_ci_gate_refuses_failing_and_pending(dw) -> None:
    """The shared gate wired into done-work refuses red and pending rollups."""
    failing = dw.evaluate_ci_gate(
        [{"name": "tests", "status": "COMPLETED", "conclusion": "FAILURE"}]
    )
    assert failing.passing is False
    pending = dw.evaluate_ci_gate([{"name": "build", "status": "IN_PROGRESS", "conclusion": ""}])
    assert pending.passing is False
    green = dw.evaluate_ci_gate([{"name": "ok", "status": "COMPLETED", "conclusion": "SUCCESS"}])
    assert green.passing is True


def test_done_work_ci_bypass_audit_body_follows_template(dw) -> None:
    """done-work's CI-bypass audit follows the schema template + its own stamp."""
    identity = dw.Identity(github_login="octocat", email="octo@example.com")
    key = dw._bypass_audit_key(dw.CI_BYPASS_AUDIT_WRITER, "advisory guard", "sha1")
    body = dw._ci_bypass_audit_body(
        identity,
        "advisory guard on a decision-only PR",
        ("guard (FAILURE)",),
        key,
    )
    assert body.startswith(dw.CI_BYPASS_AUDIT_MARKER)
    assert body.splitlines()[-1] == key
    assert "Bypassed by octocat <octo@example.com>: " in body
    assert "guard (FAILURE)" in body


def test_done_work_post_ci_bypass_audit_idempotent(dw, monkeypatch) -> None:
    """The own, unedited CI-bypass comment for the same bypass is not re-posted."""
    import subprocess

    captured: list[list[str]] = []
    key = dw._bypass_audit_key(dw.CI_BYPASS_AUDIT_WRITER, "override", "sha1")
    identity = dw.Identity(github_login="octocat", email="octo@example.com")
    prior = dw._ci_bypass_audit_body(identity, "override", ("x (FAILURE)",), key, "sha1")

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

    monkeypatch.setattr(dw, "gh_run", fake_gh_run)
    ok = dw._post_ci_bypass_audit(
        496,
        "override",
        identity,
        ("x (FAILURE)",),
        {},
        head="sha1",
    )
    assert ok is True
    assert not [c for c in captured if "comment" in c]


# A sentinel distinguishing "caller said nothing about the issue" (use the
# benign default) from "caller passed None" (simulate a failed fetch).
_UNSET_ISSUE = object()


# ---- flag split: --bypass vs --bypass-ci (#498) ----------------------
#
# `--bypass` clears ONLY the approval gate; the CI gate is overridable
# ONLY by the dedicated `--bypass-ci`. These are `main()`-level tests: a
# bypassing operator must never silently land a red CI (#498's footgun),
# so the split is exercised end-to-end at the gate wiring, not just at
# the helpers.


def _wire_main_seams(
    dw,
    monkeypatch,
    *,
    rollup,
    gate_passed=True,
    issue=_UNSET_ISSUE,
    mode="human",
    agent_gate_result=None,
    pr_body: str | None = "## Test plan\n- [x] ok\n",
    issues=None,
):
    """Monkeypatch done-work's heavy seams so main() reaches the CI gate.

    Membership/session-guard/branch/PR resolution and the approval gate are
    all stubbed to succeed; `_gh_get_status_rollup` returns *rollup* so the
    real `evaluate_ci_gate` decides. Returns a dict recording the merge and
    audit side-effects the CI-gate outcome drives (so a test can assert the
    red-CI-under-`--bypass`-only path never reaches the merge).

    *issue* is what `_gh_get_issue` returns — the labels drive mode resolution
    and the body drives the DEC-007 checkbox pre-flight. It defaults to a
    label-less, checkbox-free issue, i.e. both are non-events; pass `None` to
    simulate a failed fetch. The REAL checkbox gate runs in every case, so a
    regression that lets an unticked box through shows up here.

    `mode` sets what `resolve_mode` reports ("human" or "agent"). When
    `agent_gate_result` is supplied, `_check_agent_gate` is stubbed to return
    it — letting a test drive the full agent-mode path (including a
    per-reviewer override's audit posting) without a live gate resolution.
    `calls["order"]` records the sequence of override-audit and merge
    side-effects so a test can assert the audit lands BEFORE the merge.

    *pr_body* is the PR body done-work reads its closing references from
    (#1086); the default names none, so only issue 42 closes. *issues*, when
    given, maps each issue number to what `_gh_get_issue` returns for it (a
    missing number reads as a failed fetch) and replaces *issue*. The post-merge
    `close-issue` run is stubbed: `calls["closed"]` lists each
    `(issue, pr, skip_checkbox_gate)` it was invoked with.
    """
    calls = {
        "merged": False,
        "ci_audit": False,
        "approval_audit": False,
        "moved": False,
        "override_audits": [],
        "order": [],
        "merge_kwargs": {},
        "closed": [],
    }

    monkeypatch.setattr(dw, "resolve_capability_root", lambda arg: Path("/cap"))
    monkeypatch.setattr(dw, "load_adopter_config", lambda root: {})
    monkeypatch.setattr(dw, "_read_members", lambda root, loader: [])
    monkeypatch.setattr(
        dw,
        "resolve_invoker_identity",
        lambda config=None: dw.Identity(github_login="octocat", email="o@e.com"),
    )
    monkeypatch.setattr(
        dw,
        "check_membership",
        lambda members, invoker: type(
            "MR",
            (),
            {"allowed": True, "refusal_message": None},
        )(),
    )
    monkeypatch.setattr(dw.session_guard, "enforce", lambda **kw: True)
    # This file targets done-work's approval / CI / checkbox gates, not the
    # #747 prerequisite gate (covered in test_pm_bootstrap_gate*.py); the fake
    # capability root above has no tree to stamp, so neutralise it here — the
    # same treatment the foreign-repo guard gets on the line above.
    monkeypatch.setattr(dw.bootstrap_gate, "enforce", lambda *a, **kw: True)
    monkeypatch.setattr(dw, "_find_issue_branch", lambda n: "fix/42-slug")
    monkeypatch.setattr(
        dw,
        "_find_pr_for_branch",
        lambda branch, config: {
            "number": 496,
            "title": "fix: x",
            "isDraft": False,
            "headRefOid": "sha-head",
        },
    )
    resolved_issue = {"labels": [], "body": ""} if issue is _UNSET_ISSUE else issue
    if issues is None:
        monkeypatch.setattr(dw, "_gh_get_issue", lambda n, config: resolved_issue)
    else:
        monkeypatch.setattr(dw, "_gh_get_issue", lambda n, config: issues.get(n))
    monkeypatch.setattr(
        dw,
        "resolve_mode",
        lambda config, issue_labels=None: type(
            "M",
            (),
            {"mode": mode, "source": "default"},
        )(),
    )
    monkeypatch.setattr(
        dw,
        "_check_approval_gate",
        lambda pr_number, pr, bypass_reason, config: dw._GateResult(
            passed=gate_passed,
            passed_via="stub",
            refusal_message="" if gate_passed else "[refused] approval gate",
        ),
    )
    if agent_gate_result is not None:
        monkeypatch.setattr(
            dw,
            "_check_agent_gate",
            lambda *a, **k: agent_gate_result,
        )

    def _stub_reviewer_override_audit(
        pr_number,
        audit,
        reason,
        invoker,
        config,
        **kwargs,
    ):
        calls["override_audits"].append(audit.reviewer)
        calls["order"].append(("override_audit", audit.reviewer))
        return True

    monkeypatch.setattr(
        dw,
        "_post_reviewer_override_audit",
        _stub_reviewer_override_audit,
    )
    monkeypatch.setattr(dw, "_gh_get_pr_body", lambda pr_number, config: pr_body)
    monkeypatch.setattr(
        dw,
        "_check_pr_placeholder",
        lambda body, pr_number, cap_root: [],
    )
    monkeypatch.setattr(dw, "_gh_get_status_rollup", lambda pr_number, config: rollup)

    def _stub_ci_audit(pr_number, reason, invoker, checks, config, *, head=""):
        calls["ci_audit"] = True
        calls["ci_audit_head"] = head
        return True

    def _stub_approval_audit(issue_number, reason, config, *, head=""):
        calls["approval_audit"] = True
        calls["approval_audit_head"] = head
        return True

    def _stub_merge(pr_number, *, pr_title, admin, config, head_oid="", allow_foreign_repo=False):
        calls["merged"] = True
        calls["merge_kwargs"] = {"pr_title": pr_title, "admin": admin}
        calls["merge_head"] = head_oid
        calls["merge_allow_foreign_repo"] = allow_foreign_repo
        calls["order"].append(("merged", None))
        return True

    def _stub_move(issue_number, target, cap_root_arg, *, confirmed):
        calls["moved"] = True
        calls["order"].append(("moved", None))
        return 0

    def _stub_close(issue_number, pr_number, cap_root_arg, *, skip_checkbox_gate, confirmed):
        calls["closed"].append((issue_number, pr_number, skip_checkbox_gate))
        calls["order"].append(("closed", issue_number))
        return 0

    def _stub_delete_remote(branch, config, **kwargs):
        calls.setdefault("cross", []).append(kwargs.get("cross_repository"))
        calls["order"].append(("remote_delete", branch))

    def _stub_cleanup_local(branch, config, **kwargs):
        calls.setdefault("merged_heads", []).append(kwargs.get("merged_head"))
        calls["order"].append(("local_cleanup", branch))

    monkeypatch.setattr(dw, "_post_ci_bypass_audit", _stub_ci_audit)
    monkeypatch.setattr(dw, "_post_bypass_audit_idempotent", _stub_approval_audit)
    # The merge mechanic is `_lib.pr_merge`'s (shared with merge-pr); stub it
    # on the module done-work calls through.
    monkeypatch.setattr(dw.pr_merge, "squash_merge", _stub_merge)
    monkeypatch.setattr(dw.pr_merge, "delete_remote_branch", _stub_delete_remote)
    monkeypatch.setattr(dw.pr_merge, "cleanup_local", _stub_cleanup_local)
    monkeypatch.setattr(dw, "_invoke_move_issue", _stub_move)
    monkeypatch.setattr(dw, "_invoke_close_issue", _stub_close)

    # The base merges directly — the merge-queue path (#1011) has its own tests
    # at the end of this file — and GitHub reports the PR merged once the
    # stubbed merge has run: done-work counts a merge only when it does.
    def no_queue(pr_number: int, config: dict[str, Any]) -> Any:
        state = "MERGED" if calls["merged"] else "OPEN"
        return pull_request_backbone.reading(dw.merge_queue, has_queue=False, pr_state=state)

    monkeypatch.setattr(dw.merge_queue, "read", no_queue)
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
        dw,
        monkeypatch,
        ["42", "--bypass-ci", "advisory guard", "--yes"],
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
        dw,
        monkeypatch,
        ["42", "--bypass", "appr reason", "--bypass-ci", "ci reason", "--yes"],
    )
    assert rc == 0
    assert calls["approval_audit"] is True
    assert calls["ci_audit"] is True
    assert calls["merged"] is True
    # Both bypasses are keyed on the PR's head commit (#902).
    assert calls["approval_audit_head"] == "sha-head"
    assert calls["ci_audit_head"] == "sha-head"


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


# ---- checkbox close-gate pre-flight (DEC-007, #734) ------------------
#
# The gate has to bite BEFORE the squash-merge: `Closes #N` auto-closes the
# issue *on* merge, so a check afterwards reports a gate it already let
# through. Every refusal test therefore asserts `calls["merged"] is False`
# — that assertion, not the exit code, is what pins "before the merge".

_UNTICKED_BODY = (
    "## What\n\nFix the widget.\n\n"
    "## Acceptance criteria\n\n"
    "- [x] The widget stops wobbling.\n"
    "- [ ] The regression test covers the wobble.\n"
)
_TICKED_BODY = (
    "## What\n\nFix the widget.\n\n"
    "## Acceptance criteria\n\n"
    "- [x] The widget stops wobbling.\n"
    "- [x] The regression test covers the wobble.\n"
)
_NO_BOXES_BODY = "## What\n\nBump a pinned dependency. No criteria to track.\n"


def _issue(body: str) -> dict:
    return {"labels": [], "body": body}


def test_unticked_checkbox_refuses_before_the_merge(dw, monkeypatch, capsys):
    """An unticked box refuses, names the box, and never reaches the merge."""
    calls = _wire_main_seams(
        dw,
        monkeypatch,
        rollup=_GREEN_ROLLUP,
        issue=_issue(_UNTICKED_BODY),
    )
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    assert rc == 1
    assert calls["merged"] is False, (
        "the checkbox gate must refuse BEFORE the squash-merge — GitHub's "
        "`Closes #N` auto-closes the issue on merge, so a post-merge check "
        "gates nothing (DEC-007)"
    )
    assert calls["moved"] is False
    err = capsys.readouterr().err
    assert "DEC-007 checkbox close-gate" in err
    assert "The regression test covers the wobble" in err, (
        "the refusal must list each unticked line"
    )
    assert "--skip-checkbox-gate" in err, "the refusal must name the remedy"
    # The ticked box is not reported as outstanding.
    assert "stops wobbling" not in err


def test_the_refusal_names_the_verb_that_ticks_each_box(dw, monkeypatch, capsys):
    """#1015: each unticked box is followed by the command that ticks it —
    `check-criterion` for a criterion and for a Doc impact box, a body edit
    for a box no verb can address."""
    body = (
        "## What\n\nFix the widget.\n\n"
        "## Acceptance criteria\n\n"
        "- [x] The widget stops wobbling.\n"
        "- [ ] The regression test covers the wobble.\n\n"
        "## Doc impact\n\n"
        "- [ ] The README documents the wobble.\n\n"
        "## Notes\n\n"
        "- [ ] Tell the widget team.\n"
    )
    calls = _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP, issue=_issue(body))
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    assert rc == 1
    assert calls["merged"] is False
    err = capsys.readouterr().err
    assert "→ pkit pm check-criterion 42 2" in err
    assert "→ pkit pm check-criterion 42 --section doc-impact 1" in err
    assert "pkit pm edit-issue 42 --body-file" in err


def test_all_boxes_ticked_merges(dw, monkeypatch):
    """An issue with every box ticked merges exactly as before."""
    calls = _wire_main_seams(
        dw,
        monkeypatch,
        rollup=_GREEN_ROLLUP,
        issue=_issue(_TICKED_BODY),
    )
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    assert rc == 0
    assert calls["merged"] is True
    assert calls["moved"] is True


def test_body_with_no_checkboxes_merges(dw, monkeypatch):
    """DEC-007's rule applies only when boxes exist — a box-free body merges."""
    calls = _wire_main_seams(
        dw,
        monkeypatch,
        rollup=_GREEN_ROLLUP,
        issue=_issue(_NO_BOXES_BODY),
    )
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    assert rc == 0
    assert calls["merged"] is True


def test_skip_checkbox_gate_overrides_the_refusal(dw, monkeypatch):
    """`--skip-checkbox-gate` merges an issue that would otherwise refuse."""
    calls = _wire_main_seams(
        dw,
        monkeypatch,
        rollup=_GREEN_ROLLUP,
        issue=_issue(_UNTICKED_BODY),
    )
    rc = _run_main(dw, monkeypatch, ["42", "--skip-checkbox-gate", "--yes"])
    assert rc == 0
    assert calls["merged"] is True


def test_bypass_alone_does_not_clear_an_unticked_box(dw, monkeypatch, capsys):
    """`--bypass` clears the approval gate only — it is not a checkbox skip.

    Same posture as `--bypass` vs a red CI (#498): each gate has its own
    deliberate override.
    """
    calls = _wire_main_seams(
        dw,
        monkeypatch,
        rollup=_GREEN_ROLLUP,
        issue=_issue(_UNTICKED_BODY),
    )
    rc = _run_main(dw, monkeypatch, ["42", "--bypass", "reviewer away", "--yes"])
    assert rc == 1
    assert calls["merged"] is False
    assert "--skip-checkbox-gate" in capsys.readouterr().err


def test_unreadable_issue_body_fails_closed(dw, monkeypatch, capsys):
    """A failed issue fetch refuses: an unverified gate is not a satisfied one."""
    calls = _wire_main_seams(
        dw,
        monkeypatch,
        rollup=_GREEN_ROLLUP,
        issue=None,
    )
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    assert rc == 1
    assert calls["merged"] is False
    err = capsys.readouterr().err
    assert "could not be read" in err
    assert "--skip-checkbox-gate" in err


def test_checkbox_gate_outcome_is_reported_when_it_passes(dw, monkeypatch, capsys):
    """A passing gate still prints its outcome — a silent gate is invisible.

    Both passing paths are named, so a skipped gate shows in the transcript
    rather than looking like a satisfied one.
    """
    _wire_main_seams(
        dw,
        monkeypatch,
        rollup=_GREEN_ROLLUP,
        issue=_issue(_TICKED_BODY),
    )
    assert _run_main(dw, monkeypatch, ["42", "--yes"]) == 0
    assert "checkbox-gate: all checkboxes ticked" in capsys.readouterr().out

    _wire_main_seams(
        dw,
        monkeypatch,
        rollup=_GREEN_ROLLUP,
        issue=_issue(_UNTICKED_BODY),
    )
    assert _run_main(dw, monkeypatch, ["42", "--skip-checkbox-gate", "--yes"]) == 0
    assert "checkbox-gate: --skip-checkbox-gate" in capsys.readouterr().out


def test_done_work_fetches_the_issue_body_for_the_gate(dw, monkeypatch):
    """The pre-flight rides the EXISTING issue fetch — no extra round-trip.

    Mode resolution already reads the issue's labels; the gate needs its body.
    Both come from one `gh_get_issue` call, so the gate costs no extra request.
    """
    captured: list[str] = []

    def fake_gh_get_issue(issue_number, config, *, fields):
        captured.append(fields)
        return {"labels": [], "body": ""}

    monkeypatch.setattr(dw, "gh_get_issue", fake_gh_get_issue)
    dw._gh_get_issue(42, {})
    assert len(captured) == 1, "the gate must not add a second issue fetch"
    requested = set(captured[0].split(","))
    assert {"labels", "body"} <= requested


# ---- per-reviewer override guards (main()-level, DEC-050) -------------


def test_bypass_reviewer_requires_reason(dw, monkeypatch, capsys):
    """`--bypass-reviewer` without `--bypass-reviewer-reason` is refused before
    any gate work — a per-reviewer override is audited, reason-required
    (DEC-050)."""
    calls = _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP)
    rc = _run_main(dw, monkeypatch, ["42", "--bypass-reviewer", "design-reviewer", "--yes"])
    assert rc == 1
    assert calls["merged"] is False
    assert "--bypass-reviewer-reason" in capsys.readouterr().err


def test_bypass_reviewer_refused_in_human_mode(dw, monkeypatch, capsys):
    """`--bypass-reviewer` in human mode is refused — it targets the agent-mode
    reviewer set, which human mode has no equivalent of (DEC-050)."""
    calls = _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP)
    rc = _run_main(
        dw,
        monkeypatch,
        [
            "42",
            "--bypass-reviewer",
            "design-reviewer",
            "--bypass-reviewer-reason",
            "false block",
            "--yes",
        ],
    )
    assert rc == 1
    assert calls["merged"] is False
    err = capsys.readouterr().err
    assert "agent-mode" in err
    assert "human mode" in err


def test_bypass_and_bypass_reviewer_together_refused(dw, monkeypatch, capsys):
    """`--bypass` must not silently swallow `--bypass-reviewer`.

    The whole-gate branch used to short-circuit with both flags supplied: the
    reviewer name was never validated and no per-reviewer audit was posted, so a
    typo'd (or reclassified-away) name was silently accepted — precisely the
    no-op DEC-050 Decision 5 forbids. The combination is incoherent — a whole-gate
    bypass already subsumes waiving one slot — so it refuses, before the merge.
    """
    calls = _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP)
    rc = _run_main(
        dw,
        monkeypatch,
        [
            "42",
            "--bypass",
            "whole gate",
            "--bypass-reviewer",
            "typo-reviewer",
            "--bypass-reviewer-reason",
            "false block",
            "--yes",
        ],
    )
    assert rc == 1
    assert calls["merged"] is False, "the refusal must land before the merge"
    assert calls["approval_audit"] is False, "no whole-gate audit on a refusal"
    assert calls["override_audits"] == [], "no per-reviewer audit on a refusal"
    err = capsys.readouterr().err
    assert "cannot be combined" in err
    # The refusal names both flags and the reviewer whose waiver was dropped.
    assert "--bypass-reviewer" in err
    assert "typo-reviewer" in err


def test_bypass_reviewer_name_is_stripped(dw, monkeypatch):
    """A shell-quoting space around a name must not hard-error as unknown.

    `--bypass-reviewer " design-reviewer "` reaches the gate as
    `design-reviewer`; a whitespace-only value drops out entirely rather than
    becoming an unnameable required reviewer.
    """
    seen: dict = {}

    def fake_agent_gate(pr_number, pr, config, mode_source, cap_root, **kwargs):
        seen["override_reviewers"] = kwargs.get("override_reviewers")
        return dw._GateResult(passed=True, passed_via="stub")

    _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP, mode="agent")
    monkeypatch.setattr(dw, "_check_agent_gate", fake_agent_gate)
    rc = _run_main(
        dw,
        monkeypatch,
        [
            "42",
            "--bypass-reviewer",
            " design-reviewer ",
            "--bypass-reviewer",
            "   ",
            "--bypass-reviewer-reason",
            "false block",
            "--yes",
        ],
    )
    assert rc == 0
    assert seen["override_reviewers"] == ("design-reviewer",)


def test_agent_mode_override_happy_path_merges_after_audit(dw, monkeypatch):
    """Full agent-mode happy path across the main() seam: --bypass-reviewer with
    --bypass-reviewer-reason drives main() → _check_agent_gate (passing WITH an
    override)
    → the override audit posts → the merge proceeds. The audit lands BEFORE the
    merge (DEC-050 — the trail survives a partial failure)."""
    gate = dw._GateResult(
        passed=True,
        passed_via=("reviewer APPROVED; design-reviewer satisfied-by-override"),
        override_audits=[
            dw._OverrideAudit(
                reviewer="design-reviewer",
                capability="ux-ui-design",
                state="a fresh CHANGES_REQUESTED (an active block)",
                block_comment_url="https://example.test/c/design-reviewer",
                head="deadbeef",
                others_approved=("local agent (reviewer)",),
            )
        ],
    )
    calls = _wire_main_seams(
        dw,
        monkeypatch,
        rollup=_GREEN_ROLLUP,
        mode="agent",
        agent_gate_result=gate,
    )
    rc = _run_main(
        dw,
        monkeypatch,
        [
            "42",
            "--bypass-reviewer",
            "design-reviewer",
            "--bypass-reviewer-reason",
            "flaky false block",
            "--yes",
        ],
    )
    assert rc == 0
    assert calls["merged"] is True
    # Exactly the one expected override audit posted...
    assert calls["override_audits"] == ["design-reviewer"]
    # ...and it posted BEFORE the merge (the post-merge transition + cleanup
    # entries follow; only the audit/merge ordering is under test here).
    assert calls["order"][:2] == [
        ("override_audit", "design-reviewer"),
        ("merged", None),
    ]


# ---- the deprecated `--bypass-reason` alias (DEC-050, released in pm 0.54.0) ---
#
# `--bypass-reason` shipped on done-work in project-management 0.54.0, so
# renaming it outright would be a breaking CLI signature change owing a
# migration (COR-010). It stays accepted as a deprecated ALIAS — emphatically
# not a second implementation: both spellings write the single
# `bypass_reviewer_reason` destination, so exactly one code path consumes the
# reason. Because they share a dest, argparse cannot report which was typed;
# the deprecation notice and the both-spellings refusal read argv instead,
# which is what these tests pin.

_ALIAS_BODY = "## What\n\nA change.\n"


def test_deprecated_reason_alias_still_works_and_warns(dw, monkeypatch, capsys):
    """The released spelling keeps working, and says it is deprecated."""
    _wire_main_seams(
        dw,
        monkeypatch,
        rollup=_GREEN_ROLLUP,
        issue=_issue(_ALIAS_BODY),
    )
    rc = _run_main(dw, monkeypatch, ["42", "--bypass-reason", "still fine", "--yes"])
    err = capsys.readouterr().err
    assert "DEPRECATED" in err, "the old spelling must announce its deprecation"
    assert "--bypass-reviewer-reason" in err, "and name the canonical spelling"
    # Without --bypass-reviewer the reason is inert, so the merge proceeds
    # exactly as an unadorned run would: the alias changes no behaviour.
    assert rc == 0


def test_canonical_reason_flag_does_not_warn(dw, monkeypatch, capsys):
    _wire_main_seams(
        dw,
        monkeypatch,
        rollup=_GREEN_ROLLUP,
        issue=_issue(_ALIAS_BODY),
    )
    rc = _run_main(
        dw,
        monkeypatch,
        ["42", "--bypass-reviewer-reason", "fine", "--yes"],
    )
    assert "DEPRECATED" not in capsys.readouterr().err
    assert rc == 0


def test_both_reason_spellings_are_refused_as_ambiguous(dw, monkeypatch, capsys):
    """Two spellings of one option is ambiguous — refuse, don't let argparse
    silently resolve it by last-wins."""
    calls = _wire_main_seams(
        dw,
        monkeypatch,
        rollup=_GREEN_ROLLUP,
        issue=_issue(_ALIAS_BODY),
    )
    rc = _run_main(
        dw,
        monkeypatch,
        [
            "42",
            "--bypass-reviewer",
            "code-reviewer",
            "--bypass-reviewer-reason",
            "a",
            "--bypass-reason",
            "b",
            "--yes",
        ],
    )
    assert rc == 1
    assert calls["merged"] is False, "an ambiguous invocation must not merge"
    assert "ambiguous" in capsys.readouterr().err


def test_abbreviated_canonical_flag_cannot_evade_the_ambiguity_refusal(
    dw,
    monkeypatch,
    capsys,
):
    """`--bypass-reviewer-reas` must not bind the canonical flag.

    The alias detection reads argv literally (two spellings share one dest, so
    argparse cannot report which was typed). With prefix abbreviation enabled,
    an abbreviated canonical flag paired with the deprecated spelling would
    satisfy neither literal, evading both the deprecation notice and the
    both-spellings refusal — landing in argparse's silent last-wins, which is
    the outcome the refusal exists to prevent. `allow_abbrev=False` closes it,
    so an abbreviation is now rejected outright by argparse.
    """
    _wire_main_seams(
        dw,
        monkeypatch,
        rollup=_GREEN_ROLLUP,
        issue=_issue(_ALIAS_BODY),
    )
    with pytest.raises(SystemExit) as exc:
        _run_main(
            dw,
            monkeypatch,
            [
                "42",
                "--bypass-reviewer",
                "code-reviewer",
                "--bypass-reviewer-reas",
                "a",
                "--bypass-reason",
                "b",
                "--yes",
            ],
        )
    assert exc.value.code == 2, "argparse must reject the abbreviation, not bind it"


# ---- post-merge sequence: transition before best-effort cleanup (#878) ---
#
# `gh pr merge --delete-branch` checks out the default branch locally and
# deletes the local head; from a worktree that is on a detached HEAD, or one
# whose `main` is checked out elsewhere, that local half fails AFTER the remote
# merge has landed — and the script used to abort there, never calling
# move-issue, so GitHub showed the issue closed while pm state said Review.
# The fix: merge without `--delete-branch`, transition immediately, then clean
# up (remote ref via the API, local steps) as warnings that never abort. The
# mechanic itself (`_lib.pr_merge`) is unit-tested in test_pm_pr_merge_lib.py;
# these tests cover done-work's sequencing of it.

_DETACHED_HEAD_ERR = "could not determine current branch: failed to run git: not on any branch"
_MAIN_HELD_ELSEWHERE_ERR = "fatal: 'main' is already used by worktree at '/repo/wt-main'"


def test_transition_runs_immediately_after_merge_before_cleanup(dw, monkeypatch):
    """merge → move-issue → close-issue → remote delete → local cleanup, in
    that order: closing the issue (#1086) is lifecycle work, so it too lands
    before any best-effort step."""
    calls = _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP)
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    assert rc == 0
    assert calls["order"] == [
        ("merged", None),
        ("moved", None),
        ("closed", 42),
        ("remote_delete", "fix/42-slug"),
        ("local_cleanup", "fix/42-slug"),
    ]


def _fake_git(monkeypatch, dw, *, checkout_stderr="", branch_d_stderr=""):
    """Stub `subprocess.run` for the local git steps: `checkout main` and
    `branch -D` fail with the given stderr (empty = succeed); `pull` succeeds,
    and the local head is the head that merged (`rev-parse` answers it, and
    nothing on it is unmerged). Returns the list of git argvs seen."""
    import subprocess

    seen: list[list[str]] = []

    def fake_run(argv, **kwargs):
        seen.append(list(argv))
        if argv[:2] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(argv, 0, stdout="sha-head\n", stderr="")
        if argv[:2] == ["git", "rev-list"]:
            return subprocess.CompletedProcess(argv, 0, stdout="0\n", stderr="")
        if argv[:3] == ["git", "checkout", "main"] and checkout_stderr:
            return subprocess.CompletedProcess(argv, 128, stdout="", stderr=checkout_stderr)
        if argv[:3] == ["git", "branch", "-D"] and branch_d_stderr:
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr=branch_d_stderr)
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(dw.subprocess, "run", fake_run)
    return seen


def _script_error_lines(stderr: str) -> list[str]:
    return [ln for ln in stderr.splitlines() if ln.lower().startswith("error:")]


def test_detached_head_worktree_completes_merge_and_transition(
    dw,
    monkeypatch,
    capsys,
):
    """Trigger 1 (#878): the working tree is on a detached HEAD. The local step
    reports it as a warning; the merge and the transition both complete."""
    real_cleanup = dw.pr_merge.cleanup_local
    calls = _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP)
    monkeypatch.setattr(dw.pr_merge, "cleanup_local", real_cleanup)
    seen = _fake_git(monkeypatch, dw, checkout_stderr=_DETACHED_HEAD_ERR)

    rc = _run_main(dw, monkeypatch, ["42", "--yes"])

    err = capsys.readouterr().err
    assert rc == 0
    assert calls["merged"] is True
    assert calls["moved"] is True
    assert ("remote_delete", "fix/42-slug") in calls["order"]
    assert f"[warn] git checkout main failed: {_DETACHED_HEAD_ERR}" in err
    assert _script_error_lines(err) == []
    # The pull is skipped when main could not be checked out; the local head
    # is not checked out on a detached HEAD, so its delete is still attempted.
    assert ["git", "pull", "--ff-only"] not in seen
    assert ["git", "branch", "-D", "fix/42-slug"] in seen


def test_main_held_by_other_worktree_completes_merge_and_transition(
    dw,
    monkeypatch,
    capsys,
):
    """Trigger 2 (#878): `main` is checked out in a different worktree, so the
    local checkout is refused and the head branch (the one checked out here)
    cannot be deleted. Both are warnings; merge and transition complete."""
    real_cleanup = dw.pr_merge.cleanup_local
    calls = _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP)
    monkeypatch.setattr(dw.pr_merge, "cleanup_local", real_cleanup)
    branch_err = "error: cannot delete branch 'fix/42-slug' used by worktree at '/repo/wt-42'"
    seen = _fake_git(
        monkeypatch,
        dw,
        checkout_stderr=_MAIN_HELD_ELSEWHERE_ERR,
        branch_d_stderr=branch_err,
    )

    rc = _run_main(dw, monkeypatch, ["42", "--yes"])

    err = capsys.readouterr().err
    assert rc == 0
    assert calls["merged"] is True
    assert calls["moved"] is True
    assert ("remote_delete", "fix/42-slug") in calls["order"]
    assert f"[warn] git checkout main failed: {_MAIN_HELD_ELSEWHERE_ERR}" in err
    assert f"[warn] git branch -D fix/42-slug failed: {branch_err}" in err
    assert _script_error_lines(err) == []
    assert ["git", "pull", "--ff-only"] not in seen


def test_cleanup_still_runs_when_move_issue_fails(dw, monkeypatch, capsys):
    """A move-issue failure is reported and returned, but does not skip the
    branch cleanup — the two are independent after the merge."""
    calls = _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP)

    def failing_move(issue_number, target, cap_root_arg, *, confirmed):
        calls["order"].append(("moved", None))
        return 1

    monkeypatch.setattr(dw, "_invoke_move_issue", failing_move)
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    assert rc == 1
    assert "[warn] PR merged but move-issue exited 1" in capsys.readouterr().err
    assert [kind for kind, _ in calls["order"]] == [
        "merged",
        "moved",
        "closed",
        "remote_delete",
        "local_cleanup",
    ]


# ---- every issue the PR closes (#1086) --------------------------------
#
# One PR may close several issues (`open-pr --closes`, #1049), and GitHub's
# `Closes #N` closes each of them on merge. So done-work gates each before the
# merge — the checkbox close-gate and the state check — and closes + cascades
# each after it. Every refusal asserts `calls["merged"] is False`: that, not
# the exit code, pins "before the merge". The post-merge close is stubbed at
# `_invoke_close_issue` except in the end-to-end test, which runs the real
# close-issue against a fake `gh`.

_TWO_ISSUE_PR_BODY = (
    "Closes #42\nCloses #43\n\n"
    "## Summary\n\nLand two Tasks.\n\n"
    "## Test plan\n\n- [x] ok\n\n"
    "## Doc impact\n\nNone.\n"
)


def _open_issue(body: str) -> dict:
    return {"labels": [], "body": body, "state": "OPEN"}


def test_a_pr_closing_two_issues_gates_closes_and_cascades_both(dw, monkeypatch, capsys):
    calls = _wire_main_seams(
        dw,
        monkeypatch,
        rollup=_GREEN_ROLLUP,
        pr_body=_TWO_ISSUE_PR_BODY,
        issues={42: _open_issue(_TICKED_BODY), 43: _open_issue(_TICKED_BODY)},
    )
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "closes: #42, #43" in out
    assert "checkbox-gate: all checkboxes ticked (#42)" in out
    assert "checkbox-gate: all checkboxes ticked (#43)" in out
    assert calls["merged"] is True
    # Each goes through close-issue's pr-merge close through the merged PR —
    # closed as completed, closure cascade run — the primary first.
    assert calls["closed"] == [(42, 496, False), (43, 496, False)]
    # The issue done-work ran for is still the primary one.
    assert "done-work: #42" in out
    assert "[ok] merged + closed #42 (also closed: #43)" in out


def test_the_first_closing_issue_with_an_unticked_box_refuses_naming_it(
    dw,
    monkeypatch,
    capsys,
):
    """A second issue's unticked box refuses before the merge, with the
    existing refusal text naming that issue, its box and the verb that ticks
    it; a later failing issue is not reached."""
    calls = _wire_main_seams(
        dw,
        monkeypatch,
        rollup=_GREEN_ROLLUP,
        pr_body="Closes #42\nCloses #43\nCloses #44\n\n## Test plan\n\n- [x] ok\n",
        issues={
            42: _open_issue(_TICKED_BODY),
            43: _open_issue(_UNTICKED_BODY),
            44: _open_issue(_UNTICKED_BODY),
        },
    )
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    assert rc == 1
    assert calls["merged"] is False
    assert calls["moved"] is False
    assert calls["closed"] == []
    err = capsys.readouterr().err
    assert "[refused] DEC-007 checkbox close-gate (#43, pre-merge)" in err
    assert "The regression test covers the wobble" in err
    assert "→ pkit pm check-criterion 43 2" in err
    assert "#44" not in err


def test_a_closing_issue_already_closed_is_skipped_with_a_note(dw, monkeypatch, capsys):
    """An issue closed before the merge is not closed by it: neither gated (its
    unticked box does not refuse) nor closed again, and not an error."""
    closed = {"labels": [], "body": _UNTICKED_BODY, "state": "CLOSED"}
    calls = _wire_main_seams(
        dw,
        monkeypatch,
        rollup=_GREEN_ROLLUP,
        pr_body=_TWO_ISSUE_PR_BODY,
        issues={42: _open_issue(_TICKED_BODY), 43: closed},
    )
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    assert rc == 0
    assert calls["merged"] is True
    assert calls["closed"] == [(42, 496, False)]
    out = capsys.readouterr().out
    assert "#43: already closed, skipped (not gated, not closed again)" in out
    assert "[ok] merged + closed #42\n" in out


def test_an_unreadable_closing_issue_fails_closed(dw, monkeypatch, capsys):
    calls = _wire_main_seams(
        dw,
        monkeypatch,
        rollup=_GREEN_ROLLUP,
        pr_body=_TWO_ISSUE_PR_BODY,
        issues={42: _open_issue(_TICKED_BODY)},
    )
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    assert rc == 1
    assert calls["merged"] is False
    assert "checkbox close-gate for #43: the issue body could not be read" in (
        capsys.readouterr().err
    )


def test_an_unreadable_pr_body_fails_closed_unless_the_gate_is_skipped(
    dw,
    monkeypatch,
    capsys,
):
    """Without the PR body the issues the merge closes are unknown, so the gate
    refuses; `--skip-checkbox-gate` merges, closing only the primary, and says
    so."""
    calls = _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP, pr_body=None)
    assert _run_main(dw, monkeypatch, ["42", "--yes"]) == 1
    assert calls["merged"] is False
    assert "the PR body could not be read" in capsys.readouterr().err

    calls = _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP, pr_body=None)
    assert _run_main(dw, monkeypatch, ["42", "--skip-checkbox-gate", "--yes"]) == 0
    assert calls["closed"] == [(42, 496, True)]
    assert "[warn] PR #496's body could not be read" in capsys.readouterr().err


def test_a_failed_close_warns_with_the_rerun_and_the_rest_still_run(
    dw,
    monkeypatch,
    capsys,
):
    """The merge is durable: one close failing is reported with its re-run, the
    other closing issues are still closed, cleanup runs, and the exit is the
    failure's."""
    calls = _wire_main_seams(
        dw,
        monkeypatch,
        rollup=_GREEN_ROLLUP,
        pr_body=_TWO_ISSUE_PR_BODY,
        issues={42: _open_issue(_TICKED_BODY), 43: _open_issue(_TICKED_BODY)},
    )

    def flaky_close(issue_number, pr_number, cap_root_arg, *, skip_checkbox_gate, confirmed):
        calls["order"].append(("closed", issue_number))
        return 3 if issue_number == 42 else 0

    monkeypatch.setattr(dw, "_invoke_close_issue", flaky_close)
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    assert rc == 3
    err = capsys.readouterr().err
    assert "close-issue exited 3 for #42" in err
    assert "`close-issue 42 --mode pr-merge --pr 496`" in err
    assert calls["order"][1:] == [
        ("moved", None),
        ("closed", 42),
        ("closed", 43),
        ("remote_delete", "fix/42-slug"),
        ("local_cleanup", "fix/42-slug"),
    ]


def test_closing_issues_lead_with_the_primary_and_reuse_its_fetch(dw, monkeypatch):
    """The primary comes first even when the body names it later (or not at
    all), repeats collapse, and the primary's issue is not fetched twice."""
    fetched: list[int] = []

    def fake_get_issue(n, config):
        fetched.append(n)
        return _open_issue("")

    monkeypatch.setattr(dw, "_gh_get_issue", fake_get_issue)
    primary = _open_issue(_TICKED_BODY)
    closing = dw._read_closing_issues(
        42,
        primary,
        "Fixes #43\nCloses #42\nresolves #44\nCloses #43",
        {},
    )
    assert [c.number for c in closing] == [42, 43, 44]
    assert closing[0].issue is primary
    assert fetched == [43, 44]


def test_the_close_is_close_issue_pr_merge_through_the_merged_pr(dw, monkeypatch):
    """The post-merge close composes over `close-issue --mode pr-merge --pr`,
    the one implementation of closing a Task through a merged PR, and carries
    an operator's `--skip-checkbox-gate` through."""
    import subprocess

    seen: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        seen.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(dw.subprocess, "run", fake_run)
    assert (
        dw._invoke_close_issue(43, 496, Path("/cap"), skip_checkbox_gate=True, confirmed=False) == 0
    )
    assert dw._invoke_close_issue(44, 496, None, skip_checkbox_gate=False, confirmed=False) == 0
    assert seen[0][0] == sys.executable
    assert Path(seen[0][1]).name == "close-issue.py"
    assert seen[0][2:] == [
        "43",
        "--mode",
        "pr-merge",
        "--pr",
        "496",
        "--skip-checkbox-gate",
        "--yes",
        "--capability-root",
        "/cap",
    ]
    assert seen[1][2:] == ["44", "--mode", "pr-merge", "--pr", "496", "--yes"]


_FAKE_GH = """\
import json, os, sys
args = sys.argv[1:]
with open(os.environ["FAKE_GH_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps(args) + "\\n")
with open(os.environ["FAKE_GH_STATE"], encoding="utf-8") as fh:
    state = json.load(fh)
if args[:2] == ["issue", "view"]:
    fields = args[args.index("--json") + 1] if "--json" in args else ""
    if fields == "comments":
        print(json.dumps({"comments": []}))
        sys.exit(0)
    issue = state["issues"].get(args[2])
    if issue is None:
        sys.exit(1)
    print(json.dumps(issue))
    sys.exit(0)
if args[:2] == ["pr", "view"]:
    print(json.dumps(state["pr"]))
    sys.exit(0)
if args[:1] == ["api"]:
    print("octocat")
sys.exit(0)
"""


def test_both_closing_issues_are_closed_and_cascaded_by_the_real_close_issue(
    dw,
    tmp_path,
    monkeypatch,
    capfd,
):
    """End to end past the merge: done-work runs the real close-issue on each
    closing issue against a fake `gh`. Both issues are still open after the
    merge (a base branch GitHub does not auto-close on), so each is closed as
    completed, and each one's closure cascade visits its parent."""
    import shutil

    cap_root = tmp_path / ".pkit" / "capabilities" / "project-management"
    cap_root.mkdir(parents=True)
    _mark_bootstrapped(cap_root)
    shutil.copytree(CAPABILITY_ROOT_DW / "schemas", cap_root / "schemas")

    def task(title: str, state_label: str) -> dict:
        return {
            "title": title,
            "body": "Feature: #7\n\n## What\n\nx\n\n## Acceptance criteria\n\n- [x] done\n",
            "state": "OPEN",
            "labels": [{"name": state_label}],
            "milestone": None,
        }

    state = {
        "issues": {
            "42": task("[Task] land the widget", "state:review"),
            "43": task("[Task] land the gadget", "state:in-progress"),
            "7": {
                "title": "[Feature] widgets",
                "state": "OPEN",
                "labels": [],
                "milestone": None,
                "body": "## What\n\nw\n\n## Acceptance criteria\n\n- [x] shipped\n",
            },
        },
        "pr": {"number": 496, "state": "MERGED", "mergedAt": "2026-09-29T10:00:00Z", "url": "u"},
    }
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_gh = bin_dir / "gh"
    fake_gh.write_text(f"#!{sys.executable}\n{_FAKE_GH}", encoding="utf-8")
    fake_gh.chmod(0o755)
    (tmp_path / "state.json").write_text(json.dumps(state), encoding="utf-8")
    log = tmp_path / "gh.log"
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("FAKE_GH_STATE", str(tmp_path / "state.json"))
    monkeypatch.setenv("FAKE_GH_LOG", str(log))
    # No session anchor: the foreign-repo guard cannot evaluate and stands aside.
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)

    real_close = dw._invoke_close_issue
    _wire_main_seams(
        dw,
        monkeypatch,
        rollup=_GREEN_ROLLUP,
        pr_body=_TWO_ISSUE_PR_BODY,
        issues={42: _open_issue(_TICKED_BODY), 43: _open_issue(_TICKED_BODY)},
    )
    monkeypatch.setattr(dw, "_invoke_close_issue", real_close)

    rc = _run_main(dw, monkeypatch, ["42", "--yes", "--capability-root", str(cap_root)])

    out = capfd.readouterr().out
    assert rc == 0, out
    calls = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    for number in ("42", "43"):
        assert ["issue", "close", number, "--reason", "completed"] in calls
        assert f"[ok] closed #{number} (pr-merge through PR #496, completed)." in out
    assert out.count("[cascade] parents to check for eligibility: #7") == 2


# ---- an issue that never reached Review (#1162) -------------------------
#
# workflow.yaml declares a Task's move to done from Review — the merge's move —
# and no In Progress → Done. A Task whose PR was opened without `review-work`
# is still In Progress when done-work runs, so `move-issue --to done` after the
# merge refused, and done-work warned about a state that did not exist while
# the pr-merge close went on to set state:done. done-work now moves such an
# issue to Review just before the merge, so each move it makes is a declared
# one. The tests read the real schemas: the transition table decides.


_Issue = dict[str, Any]


def _task(state_label: str, *, state: str = "OPEN") -> _Issue:
    """A Task as `gh issue view` returns it: a parent line, ticked criteria."""
    return {
        "title": "[Task] land the widget",
        "body": (
            "Feature: #7\n\n## What\n\nLand the widget.\n\n"
            "## Acceptance criteria\n\n- [x] The widget lands.\n"
        ),
        "state": state,
        "labels": [{"name": state_label}],
        "milestone": None,
    }


_LEAD_IN_CASES: list[tuple[_Issue | None, tuple[str, str] | None]] = [
    (_task("state:in-progress"), ("in-progress", "review")),
    (_task("state:review"), None),
    (_task("state:review", state="CLOSED"), None),
    (None, None),
    ({**_task("state:in-progress"), "title": "no type prefix"}, None),
    # A container may move In Progress → Done directly; nothing leads in.
    ({**_task("state:in-progress"), "title": "[Feature] widgets"}, None),
]


@pytest.mark.parametrize(
    ("issue", "expected"),
    _LEAD_IN_CASES,
    ids=[
        "task-in-progress",
        "task-in-review",
        "closed",
        "unread",
        "untyped",
        "container-in-progress",
    ],
)
def test_the_lead_in_is_read_from_the_transition_table(
    dw: ModuleType,
    issue: _Issue | None,
    expected: tuple[str, str] | None,
) -> None:
    from ruamel.yaml import YAML

    lead_in = dw._lead_in_to_done(issue, CAPABILITY_ROOT_DW, YAML(typ="safe"))
    if expected is None:
        assert lead_in is None
    else:
        assert (lead_in.from_state, lead_in.to_state) == expected


def _wire_lead_in(
    dw: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    primary: _Issue,
    *,
    move_rc: int = 0,
) -> dict[str, Any]:
    """Wire main() with the real schemas and a move stub that records targets."""
    calls = cast(
        "dict[str, Any]",
        _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP, issues={42: primary}),
    )

    def real_capability_root(arg: Path | None) -> Path:
        return CAPABILITY_ROOT_DW

    monkeypatch.setattr(dw, "resolve_capability_root", real_capability_root)

    def recording_move(
        issue_number: int, target: str, cap_root_arg: Path | None, *, confirmed: bool
    ) -> int:
        calls["order"].append(("moved", target))
        return move_rc if target == "review" else 0

    monkeypatch.setattr(dw, "_invoke_move_issue", recording_move)
    return calls


def test_an_in_progress_issue_moves_to_review_before_the_merge(
    dw: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls = _wire_lead_in(dw, monkeypatch, _task("state:in-progress"))
    rc: int = _run_main(dw, monkeypatch, ["42", "--yes"])
    captured = capsys.readouterr()
    assert rc == 0
    assert calls["order"] == [
        ("moved", "review"),
        ("merged", None),
        ("moved", "done"),
        ("closed", 42),
        ("remote_delete", "fix/42-slug"),
        ("local_cleanup", "fix/42-slug"),
    ]
    assert "lead-in: in-progress → review before the merge" in captured.out
    assert "[warn]" not in captured.err


def test_an_issue_in_review_makes_only_the_move_to_done(
    dw: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls = _wire_lead_in(dw, monkeypatch, _task("state:review"))
    rc: int = _run_main(dw, monkeypatch, ["42", "--yes"])
    captured = capsys.readouterr()
    assert rc == 0
    assert calls["order"][:3] == [("merged", None), ("moved", "done"), ("closed", 42)]
    assert "lead-in" not in captured.out


def test_a_failed_move_to_review_stops_the_run_before_the_merge(
    dw: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls = _wire_lead_in(dw, monkeypatch, _task("state:in-progress"), move_rc=3)
    rc: int = _run_main(dw, monkeypatch, ["42", "--yes"])
    assert rc == 3
    assert calls["merged"] is False
    assert calls["closed"] == []
    assert calls["order"] == [("moved", "review")]
    err = capsys.readouterr().err
    assert "moving #42 in-progress → review ahead of the merge" in err
    assert "PR #496 was NOT merged" in err


def test_the_dry_run_names_the_move_to_review_and_makes_none(
    dw: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls = _wire_lead_in(dw, monkeypatch, _task("state:in-progress"))
    rc: int = _run_main(dw, monkeypatch, ["42", "--dry-run"])
    assert rc == 0
    assert calls["order"] == []
    assert "would post bypass audit (if any), move #42 to review, squash-merge" in (
        capsys.readouterr().out
    )


# A `gh` that keeps what it is told: label edits, closes and comments land in
# the state file, so a test reads the end state rather than the calls. Like the
# live case in #1162, the merge does not close the issue on its own.
_STATEFUL_FAKE_GH = """\
import json, os, sys
args = sys.argv[1:]
with open(os.environ["FAKE_GH_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps(args) + "\\n")
path = os.environ["FAKE_GH_STATE"]
with open(path, encoding="utf-8") as fh:
    state = json.load(fh)

def option(name):
    return args[args.index(name) + 1] if name in args else None

if args[:2] == ["issue", "list"]:
    print(json.dumps([dict(issue, number=int(n)) for n, issue in state["issues"].items()]))
    sys.exit(0)
if args[:1] == ["api"] and "/milestones/" in args[1] and "-X" not in args:
    milestone = state.get("milestones", {}).get(args[1].rsplit("/", 1)[1])
    if milestone is None:
        sys.exit(1)
    print(json.dumps(milestone))
    sys.exit(0)
if args[:1] == ["issue"] and len(args) > 2:
    issue = state["issues"].get(args[2])
    if issue is None:
        sys.exit(1)
    if args[1] == "view":
        if option("--json") == "comments":
            print(json.dumps({"comments": issue.get("comments", [])}))
        else:
            print(json.dumps(issue))
        sys.exit(0)
    if args[1] == "edit":
        names = [label["name"] for label in issue["labels"]]
        names = [n for n in names if n != option("--remove-label")]
        if option("--add-label") and option("--add-label") not in names:
            names.append(option("--add-label"))
        issue["labels"] = [{"name": n} for n in names]
    elif args[1] == "close":
        issue["state"] = "CLOSED"
    elif args[1] == "comment":
        issue.setdefault("comments", []).append({
            "body": option("--body"), "viewerDidAuthor": True,
            "lastEditedAt": None, "author": {"login": "octocat"},
        })
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(state, fh)
    sys.exit(0)
if args[:2] == ["pr", "list"]:
    print(json.dumps(state.get("merged_prs", [])))
    sys.exit(0)
if args[:2] == ["pr", "view"]:
    print(json.dumps(state["pr"]))
    sys.exit(0)
if args[:2] == ["api", "graphql"] and any("closedByPullRequestsReferences" in a for a in args):
    merged = [dict(pr, state="MERGED") for pr in state.get("merged_prs", [])]
    issue = {
        "closedByPullRequestsReferences": {"nodes": merged},
        "timelineItems": {"nodes": []},
    }
    print(json.dumps({"data": {"repository": {"issue": issue}}}))
    sys.exit(0)
if args[:1] == ["api"]:
    print("octocat")
sys.exit(0)
"""

# The process engine as a project without it sees it: its position read is
# unavailable (move-issue then reads the position itself, from the same `gh`),
# and it accepts every move it is handed.
_FAKE_PKIT = """\
import sys
sys.exit(1 if sys.argv[1:3] == ["process", "status"] else 0)
"""


@dataclass(frozen=True)
class _EndToEnd:
    """What one end-to-end done-work run left behind."""

    rc: int
    out: str
    err: str
    #: Issue #42 as the fake `gh` holds it after the run.
    end: _Issue
    #: Every `gh` call, in order, and how many had been made when the merge ran.
    calls: list[list[str]]
    calls_at_merge: int

    def state_label_edits(self) -> list[list[str]]:
        return [c for c in self.calls if c[:3] == ["issue", "edit", "42"]]

    def assert_closed_done_one_comment_no_warning(self) -> None:
        assert self.rc == 0, self.out + self.err
        assert self.end["state"] == "CLOSED"
        assert [label["name"] for label in self.end["labels"]] == ["state:done"]
        assert len(self.end["comments"]) == 1
        # The comment records the merge as what moved the issue to done.
        assert "completed by merged PR #496" in self.end["comments"][0]["body"]
        assert "[warn]" not in self.err
        assert _script_error_lines(self.err) == []


def _run_done_work_end_to_end(
    dw: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
    primary_label: str,
    *,
    milestone: dict[str, Any] | None = None,
    merged_by_queue: bool = False,
) -> _EndToEnd:
    """done-work on #42, carrying `primary_label`, with the REAL move-issue and
    close-issue run against the stateful fake `gh`. With `milestone` (a
    Milestone as `gh api` returns it), #42 is scheduled into it by its native
    field — the only issue in it. With `merged_by_queue`, the run is the one
    after a merge queue merged PR #496 (#1011): no open PR, the merged one from
    the branch, and #42 closed by GitHub as it merged."""
    import shutil

    cap_root = tmp_path / ".pkit" / "capabilities" / "project-management"
    cap_root.mkdir(parents=True)
    _mark_bootstrapped(cap_root)
    shutil.copytree(CAPABILITY_ROOT_DW / "schemas", cap_root / "schemas")

    feature = {
        "title": "[Feature] widgets",
        "state": "OPEN",
        "milestone": None,
        "labels": [{"name": "state:in-progress"}],
        "body": "## What\n\nw\n\n## Acceptance criteria\n\n- [ ] shipped\n",
    }
    task = _task(primary_label)
    milestones: dict[str, dict[str, Any]] = {}
    if milestone is not None:
        task["milestone"] = {"number": milestone["number"], "title": milestone["title"]}
        milestones[str(milestone["number"])] = milestone
    merged_at = "2026-09-30T10:00:00Z"
    if merged_by_queue:
        task = {**task, "state": "CLOSED", "closedAt": "2026-09-30T10:00:04Z"}
    state = {
        "issues": {"42": task, "7": feature},
        "milestones": milestones,
        "pr": {"number": 496, "state": "MERGED", "mergedAt": merged_at, "url": "u"},
        "merged_prs": [
            {
                "number": 496,
                "headRefName": "fix/42-slug",
                "headRefOid": "sha-head",
                "mergedAt": merged_at,
                "isCrossRepository": False,
                "body": "Closes #42\n",
            }
        ],
    }
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, script in (("gh", _STATEFUL_FAKE_GH), ("pkit", _FAKE_PKIT)):
        fake = bin_dir / name
        fake.write_text(f"#!{sys.executable}\n{script}", encoding="utf-8")
        fake.chmod(0o755)
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps(state), encoding="utf-8")
    log = tmp_path / "gh.log"
    log.touch()
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("FAKE_GH_STATE", str(state_file))
    monkeypatch.setenv("FAKE_GH_LOG", str(log))
    # No session anchor: the foreign-repo guard cannot evaluate and stands aside.
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)

    real_move, real_close = dw._invoke_move_issue, dw._invoke_close_issue
    real_get_issue = dw._gh_get_issue
    seams = _wire_main_seams(
        dw,
        monkeypatch,
        rollup=_GREEN_ROLLUP,
        issues={42: _task(primary_label)},
    )

    def staged_capability_root(arg: Path | None) -> Path:
        return cap_root

    monkeypatch.setattr(dw, "resolve_capability_root", staged_capability_root)
    monkeypatch.setattr(dw, "_invoke_move_issue", real_move)
    monkeypatch.setattr(dw, "_invoke_close_issue", real_close)
    if merged_by_queue:
        monkeypatch.setattr(dw, "_find_pr_for_branch", lambda branch, config: None)
        monkeypatch.setattr(dw, "_gh_get_issue", real_get_issue)
    calls_at_merge: list[int] = []

    def merge(
        pr_number: int,
        *,
        pr_title: str,
        admin: bool,
        config: dict[str, Any],
        head_oid: str = "",
        allow_foreign_repo: bool = False,
    ) -> bool:
        calls_at_merge.append(len(log.read_text(encoding="utf-8").splitlines()))
        seams["merged"] = True
        return True

    monkeypatch.setattr(dw.pr_merge, "squash_merge", merge)

    rc: int = _run_main(
        dw,
        monkeypatch,
        ["42", "--yes", "--capability-root", str(cap_root)],
    )

    captured = capfd.readouterr()
    return _EndToEnd(
        rc=rc,
        out=captured.out,
        err=captured.err,
        end=json.loads(state_file.read_text(encoding="utf-8"))["issues"]["42"],
        calls=[json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()],
        calls_at_merge=calls_at_merge[0] if calls_at_merge else 0,
    )


def test_an_in_progress_issue_ends_closed_and_done_with_one_comment_and_no_warning(
    dw: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    run = _run_done_work_end_to_end(dw, tmp_path, monkeypatch, capfd, "state:in-progress")
    run.assert_closed_done_one_comment_no_warning()
    edits = run.state_label_edits()
    assert [option for edit in edits for option in edit[3:]] == [
        "--add-label",
        "state:review",
        "--remove-label",
        "state:in-progress",
        "--add-label",
        "state:done",
        "--remove-label",
        "state:review",
    ]
    # In Progress → Review before the merge, Review → Done after it.
    assert run.calls.index(edits[0]) < run.calls_at_merge <= run.calls.index(edits[1])
    assert "[ok] transitioned #42: in-progress → review" in run.out
    assert "[ok] transitioned #42: review → done" in run.out


def test_an_issue_in_review_is_closed_as_before(
    dw: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    run = _run_done_work_end_to_end(dw, tmp_path, monkeypatch, capfd, "state:review")
    run.assert_closed_done_one_comment_no_warning()
    edits = run.state_label_edits()
    assert [edit[3:] for edit in edits] == [
        ["--add-label", "state:done", "--remove-label", "state:review"],
    ]
    assert run.calls.index(edits[0]) >= run.calls_at_merge
    assert "lead-in" not in run.out


# ---- a merge that finishes a Milestone (#414) ---------------------------
#
# The closure cascade the post-merge close runs checks the Milestones the
# closed issue sits in as well as its parents: a content-based Milestone whose
# last open child the merge closed is reported as closeable, with the command
# that closes it. The Milestone itself is left open — closing it is the
# operator's gesture (DEC-016).


def test_a_merge_that_closes_a_milestones_last_open_child_says_it_can_close(
    dw: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    milestone = {
        "number": 6,
        "title": "Milestone 6: Widgets",
        "state": "open",
        "description": "Close trigger: content-based",
        "due_on": None,
    }
    run = _run_done_work_end_to_end(
        dw, tmp_path, monkeypatch, capfd, "state:review", milestone=milestone
    )
    run.assert_closed_done_one_comment_no_warning()
    assert "[cascade] milestones to check for eligibility: #6" in run.out
    assert (
        "  · milestone #6 open; content-based, all 1 child issue(s) closed — "
        "eligible to close: run `pkit pm close-milestone 6`"
    ) in run.out
    assert not any(c[:1] == ["api"] and "-X" in c for c in run.calls)


def test_a_merge_into_a_date_based_milestone_surfaces_no_close(
    dw: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    milestone = {
        "number": 6,
        "title": "Sprint 6",
        "state": "open",
        "description": "Close trigger: date-based",
        "due_on": "2026-10-15T00:00:00Z",
    }
    run = _run_done_work_end_to_end(
        dw, tmp_path, monkeypatch, capfd, "state:review", milestone=milestone
    )
    run.assert_closed_done_one_comment_no_warning()
    assert "  · milestone #6 open; date-based — it closes on its date" in run.out
    assert "close-milestone" not in run.out


# ---- merging through a queue (#1011) ------------------------------------
#
# Where the PR's base merges through a queue, done-work enqueues instead of
# merging: the queue runs the required checks on the merge it is about to make
# and merges once they pass. done-work prints where the PR stands and waits for
# the merge; what follows the merge runs then — or, when the wait ends first, in
# a later run that finds the PR merged. These tests run the real enqueue and the
# real queue reading against a fake `gh` that keeps a queue, with the steps after
# the merge stubbed (`calls["order"]`) and a clock the wait's sleeps advance.

# A `gh` keeping one PR and its place in a merge queue. `pr merge` takes the PR
# in (`--disable-auto` cancels its auto-merge, the dequeue mutation takes it
# out); each later read of the PR moves it on by the next entry of
# `state["queue"]`, until none is left. It answers the repository's squash-
# commit defaults from `state["repository"]` and the issue's closing PRs and
# reopenings from `state["issue"]`.
_QUEUE_FAKE_GH = """\
import json, os, sys
args = sys.argv[1:]
with open(os.environ["FAKE_GH_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps(args) + "\\n")
path = os.environ["FAKE_GH_STATE"]
with open(path, encoding="utf-8") as fh:
    state = json.load(fh)
pr = state["pr"]
query = next((a for a in args if a.startswith("query=")), "")
if args[:2] == ["pr", "merge"] and "--disable-auto" in args:
    pr["autoMergeRequest"] = None
elif args[:2] == ["pr", "merge"]:
    pr["isInMergeQueue"] = True
elif "dequeuePullRequest" in query:
    pr.update(isInMergeQueue=False, mergeQueueEntry=None)
    state["queue"] = []
elif "closedByPullRequestsReferences" in query:
    print(json.dumps({"data": {"repository": {"issue": state["issue"]}}}))
elif args[:2] == ["api", "graphql"]:
    if pr["isInMergeQueue"] and state["queue"]:
        pr.update(state["queue"].pop(0))
    print(json.dumps({"data": {"repository": {"pullRequest": pr}}}))
elif args[:2] == ["api", "repos/{owner}/{repo}"]:
    print(json.dumps(state["repository"]))
elif args[:2] == ["pr", "list"]:
    print(json.dumps(state.get("merged_prs", [])))
with open(path, "w", encoding="utf-8") as fh:
    json.dump(state, fh)
"""

_MERGED_AT = "2026-10-01T10:12:00Z"


def _queued_at(position: int, entry_state: str, **fields: Any) -> dict[str, Any]:
    entry = {"position": position, "state": entry_state, "estimatedTimeToMerge": 300}
    return {"mergeQueueEntry": entry, **fields}


_QUEUE_MERGED = {
    "isInMergeQueue": False,
    "mergeQueueEntry": None,
    "state": "MERGED",
    "mergedAt": _MERGED_AT,
}
_QUEUE_DROPPED = {"isInMergeQueue": False, "mergeQueueEntry": None}
_PR_TITLE_AND_BODY = {
    "squash_merge_commit_title": "PR_TITLE",
    "squash_merge_commit_message": "PR_BODY",
}


@dataclass
class _QueueRun:
    """The queue a run met, and what the run did."""

    calls: dict[str, Any]
    log: Path
    state_file: Path
    sleeps: list[float]

    def gh(self) -> list[list[str]]:
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]

    def merges(self) -> list[list[str]]:
        return [c for c in self.gh() if c[:2] == ["pr", "merge"]]

    def reads_after_the_merge(self) -> int:
        calls = self.gh()
        start = next(i for i, c in enumerate(calls) if c[:2] == ["pr", "merge"])
        return sum(1 for c in calls[start:] if c[:2] == ["api", "graphql"])

    def update(self, **fields: Any) -> None:
        """Change what the fake `gh` keeps before the run."""
        state = json.loads(self.state_file.read_text(encoding="utf-8"))
        state.update(fields)
        self.state_file.write_text(json.dumps(state), encoding="utf-8")

    def update_pr(self, **fields: Any) -> None:
        state = json.loads(self.state_file.read_text(encoding="utf-8"))
        state["pr"].update(fields)
        self.state_file.write_text(json.dumps(state), encoding="utf-8")


def _wire_queue(
    dw: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    queue: list[dict[str, Any]],
    merge_method: str = "SQUASH",
    already_queued: bool = False,
) -> _QueueRun:
    """done-work's gates stubbed as for every main() test; the queue real, on a
    fake `gh` whose base `main` merges through a queue with `merge_method`,
    squashing with the PR title and body."""
    real_read = dw.merge_queue.read
    calls = _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP)
    monkeypatch.setattr(dw.merge_queue, "read", real_read)
    monkeypatch.setattr(
        dw,
        "_find_pr_for_branch",
        lambda branch, config: {
            "number": 496,
            "title": "fix: x",
            "isDraft": False,
            "headRefOid": "sha-head",
            "baseRefName": "main",
        },
    )
    now = [0.0]
    sleeps: list[float] = []

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        now[0] += seconds

    pull_request_backbone.in_process(monkeypatch, dw.merge_queue, sleep=sleep, clock=lambda: now[0])
    pr = {
        "id": "PR_node",
        "state": "OPEN",
        "mergedAt": None,
        "headRefOid": "sha-head",
        "isMergeQueueEnabled": True,
        "isInMergeQueue": already_queued,
        "mergeQueue": {"configuration": {"mergeMethod": merge_method}},
        "mergeQueueEntry": None,
        "autoMergeRequest": None,
        "timelineItems": {"nodes": []},
    }
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "gh"
    fake.write_text(f"#!{sys.executable}\n{_QUEUE_FAKE_GH}", encoding="utf-8")
    fake.chmod(0o755)
    state_file = tmp_path / "state.json"
    state = {
        "pr": pr,
        "queue": queue,
        "repository": _PR_TITLE_AND_BODY,
        "issue": {"closedByPullRequestsReferences": {"nodes": []}, "timelineItems": {"nodes": []}},
    }
    state_file.write_text(json.dumps(state), encoding="utf-8")
    log = tmp_path / "gh.log"
    log.touch()
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("FAKE_GH_STATE", str(state_file))
    monkeypatch.setenv("FAKE_GH_LOG", str(log))
    return _QueueRun(calls=calls, log=log, state_file=state_file, sleeps=sleeps)


_AFTER_THE_MERGE = [
    ("moved", None),
    ("closed", 42),
    ("remote_delete", "fix/42-slug"),
    ("local_cleanup", "fix/42-slug"),
]

_ENQUEUE = ["pr", "merge", "496", "--auto", "--match-head-commit", "sha-head"]


def test_with_a_queue_the_pr_is_enqueued_and_what_follows_runs_once_it_merges(
    dw: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run = _wire_queue(
        dw,
        tmp_path,
        monkeypatch,
        queue=[_queued_at(2, "AWAITING_CHECKS"), _queued_at(1, "MERGEABLE"), _QUEUE_MERGED],
    )
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    out = capsys.readouterr().out
    assert rc == 0, out
    # Pinned to the checked head, with --auto and nothing else: the queue makes
    # the merge, by its own method, from the repository's squash defaults.
    assert run.merges() == [_ENQUEUE]
    assert run.calls["merged"] is False
    assert run.calls["order"] == _AFTER_THE_MERGE
    assert run.calls["merged_heads"] == ["sha-head"]
    assert "  queue:   main merges through a queue; PR #496 not in the queue" in out
    assert "  enqueued PR #496 in the merge queue for main" in out
    assert (
        "  waiting for the queue to merge it, as long as the queue estimates plus 2 min, "
        "at most 30 min (--no-wait returns at once)"
    ) in out
    assert "  queue:   PR #496 position 2 in the queue, awaiting checks, about 5 min" in out
    assert "  queue:   PR #496 position 1 in the queue, mergeable" in out
    assert "  merged PR #496 through the queue" in out
    assert "[ok] merged + closed #42" in out
    assert run.sleeps == [15.0, 15.0]


def test_no_wait_returns_once_the_pr_is_queued_and_leaves_the_issue_in_review(
    dw: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run = _wire_queue(
        dw, tmp_path, monkeypatch, queue=[_queued_at(2, "AWAITING_CHECKS"), _QUEUE_MERGED]
    )
    rc = _run_main(dw, monkeypatch, ["42", "--yes", "--no-wait"])
    out = capsys.readouterr().out
    assert rc == dw.EXIT_ACCEPTED == 4
    assert len(run.merges()) == 1
    assert run.reads_after_the_merge() == 1
    assert run.sleeps == []
    assert run.calls["order"] == []
    assert "[queued] PR #496 is in the merge queue for main (position 2 in the queue" in out
    assert "#42 stays in Review until it merges. Run `done-work 42` again" in out


def test_a_wait_that_runs_out_leaves_the_pr_queued(
    dw: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run = _wire_queue(dw, tmp_path, monkeypatch, queue=[_queued_at(3, "QUEUED")])
    rc = _run_main(dw, monkeypatch, ["42", "--yes", "--wait-minutes", "1"])
    out = capsys.readouterr().out
    assert rc == 4
    assert sum(run.sleeps) == 60
    assert run.calls["order"] == []
    assert "[queued] PR #496 is in the merge queue for main (position 3 in the queue" in out


def test_a_pr_the_queue_drops_merges_nothing(
    dw: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Two readings out of the queue, and the message hedges: it reports what
    the queue says, not a certainty about why."""
    run = _wire_queue(
        dw, tmp_path, monkeypatch, queue=[_queued_at(1, "AWAITING_CHECKS"), _QUEUE_DROPPED]
    )
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    err = capsys.readouterr().err
    assert rc == 3
    assert run.calls["order"] == []
    assert (
        "PR #496 left the merge queue for main without merging, as far as the queue reports"
    ) in err
    assert "#42 stays in Review" in err


def test_a_push_after_the_enqueue_takes_the_pr_out_of_the_queue(
    dw: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Commits pushed after the gates checked the head must not merge: the run
    takes the PR out of the queue and stops, nothing merged."""
    run = _wire_queue(
        dw,
        tmp_path,
        monkeypatch,
        queue=[_queued_at(2, "AWAITING_CHECKS"), _queued_at(1, "QUEUED", headRefOid="sha-pushed")],
    )
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    err = capsys.readouterr().err
    assert rc == 3
    assert run.calls["order"] == []
    dequeue = [c for c in run.gh() if any("dequeuePullRequest" in a for a in c)]
    assert dequeue and dequeue[0][-1] == "id=PR_node"
    assert "head moved from sha-hea to sha-pus after its gates checked it" in err
    assert "it was taken out of the merge queue" in err
    assert "#42 stays in Review" in err


def test_a_pr_already_in_the_queue_is_waited_for_not_enqueued_again(
    dw: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run = _wire_queue(
        dw,
        tmp_path,
        monkeypatch,
        already_queued=True,
        queue=[_queued_at(1, "MERGEABLE"), _queued_at(1, "MERGEABLE"), _QUEUE_MERGED],
    )
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert run.merges() == []
    assert "  PR #496 is already in the merge queue for main" in out
    assert run.calls["order"] == _AFTER_THE_MERGE


_DROPPED_HERE = {
    "nodes": [
        {"__typename": "AddedToMergeQueueEvent"},
        {
            "__typename": "RemovedFromMergeQueueEvent",
            "createdAt": "2026-10-01T10:05:00Z",
            "reason": "failed checks",
            "beforeCommit": {"oid": "sha-head"},
        },
    ]
}


@pytest.mark.parametrize(
    ("argv", "state", "refusal"),
    [
        (["--admin"], {}, "--admin would merge around the queue"),
        (["--bypass-ci", "flaky"], {}, "--bypass-ci cannot bypass a check there"),
        ([], {"merge_method": "MERGE"}, "the merge queue on main merges by MERGE"),
        (
            [],
            {
                "repository": {
                    "squash_merge_commit_title": "COMMIT_OR_PR_TITLE",
                    "squash_merge_commit_message": "COMMIT_MESSAGES",
                }
            },
            "squash_merge_commit_title=PR_TITLE -f squash_merge_commit_message=PR_BODY",
        ),
        ([], {"timelineItems": _DROPPED_HERE}, "dropped the PR at its current head sha-hea"),
    ],
    ids=["admin", "bypass-ci", "not-squash", "squash-defaults", "dropped-head"],
)
def test_a_queue_the_run_may_not_go_around_or_through_refuses_before_any_gate(
    dw: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
    state: dict[str, Any],
    refusal: str,
) -> None:
    run = _wire_queue(
        dw, tmp_path, monkeypatch, queue=[], merge_method=state.get("merge_method", "SQUASH")
    )
    if "repository" in state:
        run.update(repository=state["repository"])
    if "timelineItems" in state:
        run.update_pr(timelineItems=state["timelineItems"])
    rc = _run_main(dw, monkeypatch, ["42", "--yes", *argv])
    err = capsys.readouterr().err
    assert rc == 1
    assert refusal in err
    assert run.merges() == []
    assert run.calls["merged"] is False
    assert run.calls["order"] == []
    assert run.calls["approval_audit"] is False
    assert run.calls["ci_audit"] is False


def test_force_enqueues_a_head_the_queue_dropped(
    dw: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = _wire_queue(dw, tmp_path, monkeypatch, queue=[_queued_at(1, "QUEUED")])
    run.update_pr(timelineItems=_DROPPED_HERE)
    rc = _run_main(dw, monkeypatch, ["42", "--yes", "--force", "--no-wait"])
    assert rc == 4
    assert run.merges() == [_ENQUEUE]


def test_a_queue_that_cannot_be_read_merges_nothing(
    dw: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls = _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP)

    def unreadable(pr_number: int, config: dict[str, Any]) -> Any:
        raise dw.merge_queue.Unreadable("HTTP 502")

    monkeypatch.setattr(dw.merge_queue, "read", unreadable)
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    assert rc == 2
    assert calls["merged"] is False
    assert calls["order"] == []
    err = capsys.readouterr().err
    assert "cannot tell how the base branch merges: HTTP 502. Nothing was merged" in err


def test_a_direct_merge_github_cannot_confirm_is_not_called_queued(
    dw: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """gh accepts the direct merge, then every reading fails: the PR may have
    merged, so nothing after a merge runs, the issue stays in Review, and the
    run says it could not confirm the merge rather than that the PR is queued.
    A later run finds the PR merged, or open, and finishes (exit 4)."""
    calls = _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP)

    def unreadable_after_the_merge(pr_number: int, config: dict[str, Any]) -> Any:
        if calls["merged"]:
            raise dw.merge_queue.Unreadable("HTTP 502")
        return pull_request_backbone.reading(dw.merge_queue, has_queue=False, pr_state="OPEN")

    monkeypatch.setattr(dw.merge_queue, "read", unreadable_after_the_merge)
    pull_request_backbone.in_process(monkeypatch, dw.merge_queue, read=unreadable_after_the_merge)
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    captured = capsys.readouterr()
    assert rc == dw.EXIT_ACCEPTED == 4
    assert calls["order"] == [("merged", None)]
    assert "[queued]" not in captured.out
    assert (
        "[unconfirmed] gh accepted the merge of PR #496 into the base branch, but GitHub "
        "could not be read to confirm that it merged: HTTP 502. Nothing after the merge has "
        "run, and #42 stays in Review. Run `done-work 42` again once GitHub answers"
    ) in captured.out


def test_a_merge_with_no_answer_back_that_merged_moves_the_issue(
    dw: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The backbone's run ended after gh accepted the merge, without saying so:
    GitHub reports the PR merged, so the run is the merge's and moves the issue
    to Done — never "the merge failed" over a merged PR."""
    calls = _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP)

    def no_answer_back(pr_number: int, **kwargs: Any) -> bool | None:
        calls["merged"] = True
        calls["order"].append(("merged", None))
        return None

    monkeypatch.setattr(dw.pr_merge, "squash_merge", no_answer_back)
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    assert rc == 0, capsys.readouterr()
    assert calls["moved"] is True
    assert calls["order"][:2] == [("merged", None), ("moved", None)]


def test_a_merge_with_no_answer_back_github_cannot_settle_is_unconfirmed(
    dw: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls = _wire_main_seams(dw, monkeypatch, rollup=_GREEN_ROLLUP)

    def no_answer_back(pr_number: int, **kwargs: Any) -> bool | None:
        calls["order"].append(("asked", None))
        return None

    def read(pr_number: int, config: dict[str, Any]) -> Any:
        if calls["order"]:
            raise dw.merge_queue.Unreadable("HTTP 502")
        return pull_request_backbone.reading(dw.merge_queue, has_queue=False, pr_state="OPEN")

    monkeypatch.setattr(dw.pr_merge, "squash_merge", no_answer_back)
    monkeypatch.setattr(dw.merge_queue, "read", read)
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    out = capsys.readouterr().out
    assert rc == dw.EXIT_ACCEPTED == 4
    assert calls["moved"] is False
    assert (
        "[unconfirmed] the merge of PR #496 into the base branch got no answer back, and "
        "GitHub could not be read since to tell whether it merged or entered the merge "
        "queue: HTTP 502. Nothing after the merge has run, and #42 stays in Review."
    ) in out


def _no_queue_merge(dw: ModuleType, monkeypatch: pytest.MonkeyPatch, run: _QueueRun) -> None:
    """The fake `gh`'s base has no queue, and a direct merge GitHub reports merged."""
    run.update_pr(isMergeQueueEnabled=False, mergeQueue=None)

    def merge(pr_number: int, **kwargs: Any) -> bool:
        run.calls["merged"] = True
        run.calls["order"].append(("merged", None))
        run.update_pr(state="MERGED", mergedAt=_MERGED_AT)
        return True

    monkeypatch.setattr(dw.pr_merge, "squash_merge", merge)


def test_without_a_queue_the_merge_is_direct_as_before(
    dw: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The same fake `gh`, answering that the base has no queue: done-work
    merges directly, with no `--auto` and no wait, and never reads the
    repository's squash defaults, which only a queue composes from."""
    run = _wire_queue(dw, tmp_path, monkeypatch, queue=[])
    _no_queue_merge(dw, monkeypatch, run)
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    assert rc == 0
    assert run.calls["merged"] is True
    assert run.merges() == []
    assert run.calls["order"] == [("merged", None), *_AFTER_THE_MERGE]
    assert run.sleeps == []
    assert not any(c[:2] == ["api", "repos/{owner}/{repo}"] for c in run.gh())


def test_a_merge_gh_only_enqueued_never_runs_what_follows_a_merge(
    dw: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """On a base that requires a queue, `gh pr merge` without `--admin`
    enqueues and exits 0. GitHub not reporting the PR merged, nothing that
    follows a merge runs — no move to Done, no close, no branch deleted, which
    would close the PR and drop it from the queue."""
    run = _wire_queue(dw, tmp_path, monkeypatch, queue=[])
    run.update_pr(isMergeQueueEnabled=False, mergeQueue=None)

    def gh_only_enqueues(pr_number: int, **kwargs: Any) -> bool:
        run.calls["merged"] = True
        run.update_pr(
            isInMergeQueue=True, mergeQueueEntry=_queued_at(1, "QUEUED")["mergeQueueEntry"]
        )
        return True

    monkeypatch.setattr(dw.pr_merge, "squash_merge", gh_only_enqueues)
    rc = _run_main(dw, monkeypatch, ["42", "--yes", "--no-wait"])
    out = capsys.readouterr().out
    assert rc == 4
    assert run.calls["order"] == []
    assert "GitHub does not report PR #496 merged" in out
    assert "[queued] PR #496 is in the merge queue for main" in out


def test_the_dry_run_says_it_would_enqueue_and_wait(
    dw: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run = _wire_queue(dw, tmp_path, monkeypatch, queue=[])
    rc = _run_main(dw, monkeypatch, ["42", "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0
    assert run.merges() == []
    assert (
        "enqueue (--auto, pinned to sha-hea; the queue squashes with the PR title and "
        "body) and wait for the queue to merge it, as long as the queue estimates plus "
        "2 min, at most 30 min, then call move-issue"
    ) in out


# A later run, after the queue merged the PR: no open PR is left for the
# branch, the merged one is, and only what follows the merge runs. The PR is
# found from the issue as well as the branch, so any clone completes it.


def _merged_pr(**fields: Any) -> dict[str, Any]:
    pr = {
        "number": 496,
        "headRefName": "fix/42-slug",
        "headRefOid": "sha-head",
        "mergedAt": _MERGED_AT,
        "isCrossRepository": False,
        "body": "Closes #42\nCloses #43\n",
    }
    return {**pr, **fields}


def _wire_second_run(
    dw: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    issues: dict[int, dict[str, Any]],
    branch: str | None = "fix/42-slug",
    from_the_branch: bool = True,
    from_the_issue: bool = True,
    reopened_at: str | None = None,
) -> _QueueRun:
    run = _wire_queue(dw, tmp_path, monkeypatch, queue=[])
    nodes = [{"createdAt": reopened_at}] if reopened_at else []
    linked = [{**_merged_pr(), "state": "MERGED"}] if from_the_issue else []
    run.update(
        merged_prs=[_merged_pr()] if from_the_branch else [],
        issue={
            "closedByPullRequestsReferences": {"nodes": linked},
            "timelineItems": {"nodes": nodes},
        },
    )
    monkeypatch.setattr(dw, "_find_issue_branch", lambda n: branch)
    monkeypatch.setattr(dw, "_find_pr_for_branch", lambda branch, config: None)
    monkeypatch.setattr(dw, "_gh_get_issue", lambda n, config: issues.get(n))

    def no_gate(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("a merged PR has nothing left to gate")

    monkeypatch.setattr(dw, "_check_approval_gate", no_gate)
    monkeypatch.setattr(dw, "_gh_get_status_rollup", no_gate)
    return run


_CLOSED_BY_THE_MERGE = {**_open_issue(""), "state": "CLOSED", "closedAt": _MERGED_AT}
_CLOSED_BEFORE = {**_open_issue(""), "state": "CLOSED", "closedAt": "2026-09-01T00:00:00Z"}


def test_a_later_run_finds_the_pr_merged_and_completes_what_follows(
    dw: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """#42 was closed by GitHub as the queue merged; #43 was closed before the
    merge, so the merge did not close it and it is left alone."""
    run = _wire_second_run(
        dw, tmp_path, monkeypatch, issues={42: _CLOSED_BY_THE_MERGE, 43: _CLOSED_BEFORE}
    )
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert run.merges() == []
    assert run.calls["order"] == _AFTER_THE_MERGE
    assert run.calls["merged_heads"] == ["sha-head"]
    assert f"  PR:      #496, merged at {_MERGED_AT}; completing what follows the merge" in out
    assert "  closes:  #42\n" in out
    assert "[ok] merged + closed #42" in out


@pytest.mark.parametrize(
    ("branch", "from_the_branch"),
    [(None, False), ("fix/42-slug", False)],
    ids=["no-local-branch", "a-branch-whose-pr-is-not-found-from-it"],
)
def test_a_later_run_from_any_clone_completes_it_from_the_issue(
    dw: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    branch: str | None,
    from_the_branch: bool,
) -> None:
    """A clone without the branch — deleted, or never there — finds the merged
    PR through the issue's own closing references, and cleans up the PR's head
    branch, not a local one."""
    run = _wire_second_run(
        dw,
        tmp_path,
        monkeypatch,
        issues={42: _CLOSED_BY_THE_MERGE, 43: _CLOSED_BEFORE},
        branch=branch,
        from_the_branch=from_the_branch,
    )
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert run.calls["order"] == _AFTER_THE_MERGE


def test_a_later_run_on_a_stale_local_branch_completes_it_and_keeps_the_branch(
    dw: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Whatever this clone's branch points at, the completion keys on the PR. A
    local branch holding commits the merge does not is kept by the real
    clean-up, never force-deleted: `-D` would lose that work."""
    import subprocess

    real_cleanup, real_run = dw.pr_merge.cleanup_local, subprocess.run
    run = _wire_second_run(
        dw, tmp_path, monkeypatch, issues={42: _CLOSED_BY_THE_MERGE, 43: _CLOSED_BEFORE}
    )
    seen: list[list[str]] = []

    def fake_run(argv: list[str], **kwargs: Any) -> Any:
        if argv[:1] != ["git"]:
            return real_run(argv, **kwargs)
        seen.append(list(argv))
        if argv[:2] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(argv, 0, stdout="sha-newer\n", stderr="")
        if argv[:2] == ["git", "rev-list"]:
            return subprocess.CompletedProcess(argv, 0, stdout="1\n", stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(dw.pr_merge, "cleanup_local", real_cleanup)
    monkeypatch.setattr(dw.pr_merge.default_branch, "name", lambda config: "main")
    monkeypatch.setattr(dw.subprocess, "run", fake_run)
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    err = capsys.readouterr().err
    assert rc == 0, err
    assert ["git", "rev-list", "--count", "sha-head..sha-newer"] in seen
    assert ["git", "branch", "-D", "fix/42-slug"] not in seen
    assert "local branch fix/42-slug (at sha-new) holds commits the merge at sha-hea" in err
    assert ("remote_delete", "fix/42-slug") in run.calls["order"]


def test_a_later_run_refuses_an_issue_reopened_since_the_merge(
    dw: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Work after a reopen needs a PR of its own: closing the issue through the
    old merge would be wrong."""
    run = _wire_second_run(
        dw,
        tmp_path,
        monkeypatch,
        issues={42: _open_issue("")},
        reopened_at="2026-10-02T09:00:00Z",
    )
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    err = capsys.readouterr().err
    assert rc == 2
    assert run.calls["order"] == []
    assert f"PR #496 merged at {_MERGED_AT}, but #42 was reopened at 2026-10-02T09:00:00Z" in err
    assert "`close-issue 42 --mode pr-merge --pr 496`" in err


def test_a_later_run_that_cannot_read_the_issue_changes_nothing(
    dw: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run = _wire_second_run(dw, tmp_path, monkeypatch, issues={42: _CLOSED_BY_THE_MERGE})
    run.update(issue=None)
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    err = capsys.readouterr().err
    assert rc == 2
    assert run.calls["order"] == []
    assert "whether #42 was reopened since cannot be read" in err


def test_a_later_run_moves_an_issue_still_in_progress_through_review(
    dw: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A PR merged into a base other than the default leaves its issue open,
    and one enqueued without done-work may still be In Progress: the
    completion makes the move ahead of the move to Done, as the run before the
    merge would have (#1162)."""
    run = _wire_second_run(dw, tmp_path, monkeypatch, issues={42: _open_issue("")})
    targets: list[str] = []

    def move(issue_number: int, target: str, cap_root_arg: Any, *, confirmed: bool) -> int:
        targets.append(target)
        run.calls["order"].append(("moved", target))
        return 0

    monkeypatch.setattr(dw, "_invoke_move_issue", move)
    monkeypatch.setattr(
        dw,
        "_lead_in_to_done",
        lambda issue, root, loader: dw._LeadIn(from_state="in-progress", to_state="review"),
    )
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert targets == ["review", "done"]
    assert "  lead-in: in-progress → review, then review → done" in out


def test_a_later_run_finds_nothing_without_a_branch_or_a_merged_pr(
    dw: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _wire_second_run(
        dw,
        tmp_path,
        monkeypatch,
        issues={},
        branch=None,
        from_the_branch=False,
        from_the_issue=False,
    )
    rc = _run_main(dw, monkeypatch, ["42", "--yes"])
    assert rc == 2
    assert "no local branch matching `*/42-*` found, and no merged PR closes #42" in (
        capsys.readouterr().err
    )


def test_a_later_run_closes_and_cascades_with_the_real_verbs(
    dw: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    """End to end: the issue GitHub closed as the queue merged leaves the run
    done, its parent's eligibility checked, and no comment or warning."""
    run = _run_done_work_end_to_end(
        dw, tmp_path, monkeypatch, capfd, "state:review", merged_by_queue=True
    )
    assert run.rc == 0, run.out + run.err
    assert run.end["state"] == "CLOSED"
    assert [label["name"] for label in run.end["labels"]] == ["state:done"]
    assert "completing what follows the merge" in run.out
    assert "[cascade] parents to check for eligibility: #7" in run.out
    assert "[warn]" not in run.err
    assert not any(c[:2] == ["pr", "merge"] for c in run.calls)
