"""Tests for `review-work` wrapper (DEC-026)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.pm_composed_move_support import FakeEngine, MoveIssueInProcess, status_at

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts" / "review-work.py"


@pytest.fixture(scope="module")
def rw():
    lib_dir = SCRIPT.parent
    sys.path.insert(0, str(lib_dir))
    spec = importlib.util.spec_from_file_location("pm_review_work_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_review_work_under_test"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(lib_dir))


# ---- _derive_branch_prefix --------------------------------------------
#
# review-work's derivation is the verbatim twin of start-work's: kit type value
# through the ADR-026 read seam (label OR title-prefix), mapped via
# classification.yaml's `pr_type_mapping`. Same fixture, same two arms.

_CLASSIFICATION = {
    "axes": {
        "type": {
            "title_prefix_by_value": {
                "feature": "Task",
                "bug": "Bug",
                "docs": "Docs",
                "test": "Test",
                "refactor": "Refactor",
                "maintenance": "Chore",
            },
        },
    },
    "pr_type_mapping": [
        {"issue_label_value": "feature", "pr_conv_type": "feat"},
        {"issue_label_value": "bug", "pr_conv_type": "fix"},
        {"issue_label_value": "docs", "pr_conv_type": "docs"},
        {"issue_label_value": "test", "pr_conv_type": "test"},
        {"issue_label_value": "refactor", "pr_conv_type": "refactor"},
        {"issue_label_value": "maintenance", "pr_conv_type": "chore"},
    ],
}


def test_derive_branch_prefix_returns_expected(rw) -> None:
    assert rw._derive_branch_prefix(["type:feature"], "[Task] x", _CLASSIFICATION, None) == "feat"
    assert rw._derive_branch_prefix(["type:bug"], "[Bug] x", _CLASSIFICATION, None) == "fix"
    assert rw._derive_branch_prefix(["type:docs"], "[Docs] x", _CLASSIFICATION, None) == "docs"


def test_derive_branch_prefix_missing_returns_none(rw) -> None:
    assert rw._derive_branch_prefix(["priority:High"], "no prefix", _CLASSIFICATION, None) is None


def test_derive_branch_prefix_brownfield_bug_title_no_label(rw) -> None:
    """DEC-013 cross-check must resolve `fix` for a brownfield `[Bug]`-titled Task
    that carries NO type:* label — via the title-prefix arm of the seam."""
    assert rw._derive_branch_prefix([], "[Bug] hostname mismatch", _CLASSIFICATION, None) == "fix"


def test_derive_branch_prefix_greenfield_label_still_wins(rw) -> None:
    """Greenfield stays byte-identical: the `type:bug` label resolves `fix`."""
    assert (
        rw._derive_branch_prefix(["type:bug"], "no bracket prefix", _CLASSIFICATION, None) == "fix"
    )


# ---- adopter label-remap arm (#910) ------------------------------------


def _type_remap_map(module):
    """A substrate map binding `type` to the adopter's own `kind/*` labels."""
    return module.axis_labels.SubstrateMap(
        axes={"type": {"label": {"remap": {"bug": "kind/bug", "docs": "kind/docs"}}}}
    )


def test_branch_prefix_reads_a_remapped_type_label(rw) -> None:
    """The adopter's `kind/bug` label is their type substrate: it resolves `fix`
    through the map, where the bare `type:` prefix scan found nothing (#910)."""
    assert (
        rw._derive_branch_prefix(
            ["kind/bug"], "no bracket prefix", _CLASSIFICATION, _type_remap_map(rw)
        )
        == "fix"
    )


def test_branch_prefix_ignores_kit_type_label_under_a_remap(rw) -> None:
    """Under a `type` label remap the kit's `type:*` labels are not the
    substrate, so a leftover `type:docs` does not decide the prefix."""
    assert (
        rw._derive_branch_prefix(
            ["type:docs", "kind/bug"],
            "no bracket prefix",
            _CLASSIFICATION,
            _type_remap_map(rw),
        )
        == "fix"
    )


# ---- _derive_pr_title --------------------------------------------------


def test_pr_title_strips_issue_prefix(rw) -> None:
    assert rw._derive_pr_title({"title": "[Feature] add foo"}, "feat/42-add-foo") == "feat: add foo"


def test_pr_title_default_prefix_when_branch_malformed(rw) -> None:
    assert rw._derive_pr_title({"title": "x"}, "weird") == "feat: x"


# ---- _find_pr_for_branch ----------------------------------------------


def test_find_pr_only_returns_open_state(rw, monkeypatch) -> None:
    """Closed/merged PRs for the same branch shouldn't be returned."""

    def fake_gh_run(args, config, **kwargs):
        import subprocess

        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=json.dumps(
                [
                    {
                        "number": 1,
                        "state": "CLOSED",
                        "isDraft": False,
                        "headRefName": "feat/42-foo",
                    },
                    {"number": 2, "state": "OPEN", "isDraft": True, "headRefName": "feat/42-foo"},
                ]
            ),
            stderr="",
        )

    monkeypatch.setattr(rw, "gh_run", fake_gh_run)
    pr = rw._find_pr_for_branch("feat/42-foo", {})
    assert pr is not None
    assert pr["number"] == 2  # The OPEN one


def test_find_pr_returns_none_when_no_open(rw, monkeypatch) -> None:
    def fake_gh_run(args, config, **kwargs):
        import subprocess

        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=json.dumps(
                [
                    {"number": 1, "state": "CLOSED", "headRefName": "feat/42-foo"},
                ]
            ),
            stderr="",
        )

    monkeypatch.setattr(rw, "gh_run", fake_gh_run)
    assert rw._find_pr_for_branch("feat/42-foo", {}) is None


# ---- _gh_pr_add_reviewers --------------------------------------------


def test_pr_add_reviewers_strips_at_prefix(rw, monkeypatch) -> None:
    captured = {}

    def fake_gh_run(args, config, **kwargs):
        import subprocess

        captured["args"] = args
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(rw, "gh_run", fake_gh_run)
    rw._gh_pr_add_reviewers(99, ["@alice", "bob"], {})
    args = captured["args"]
    # The args list has --add-reviewer pairs
    assert "alice" in args
    assert "bob" in args
    assert "@alice" not in args  # @ stripped
    # Verify --add-reviewer appears twice
    assert args.count("--add-reviewer") == 2


def test_pr_add_reviewers_propagates_failure(rw, monkeypatch, capsys) -> None:
    def fake_gh_run(args, config, **kwargs):
        import subprocess

        return subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="",
            stderr="not authorised",
        )

    monkeypatch.setattr(rw, "gh_run", fake_gh_run)
    assert rw._gh_pr_add_reviewers(99, ["@alice"], {}) is False
    assert "not authorised" in capsys.readouterr().err


# ---- _gh_pr_ready -----------------------------------------------------


def test_pr_ready_handles_none_pr_number(rw, capsys) -> None:
    assert rw._gh_pr_ready(None, {}) is False
    assert "no PR number resolved" in capsys.readouterr().err


def test_pr_ready_propagates_gh_failure(rw, monkeypatch, capsys) -> None:
    def fake_gh_run(args, config, **kwargs):
        import subprocess

        return subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="",
            stderr="already ready",
        )

    monkeypatch.setattr(rw, "gh_run", fake_gh_run)
    assert rw._gh_pr_ready(99, {}) is False


def test_pr_ready_returns_true_on_success(rw, monkeypatch) -> None:
    def fake_gh_run(args, config, **kwargs):
        import subprocess

        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(rw, "gh_run", fake_gh_run)
    assert rw._gh_pr_ready(99, {}) is True


# ---- transition gate + late failure (#947) -----------------------------
#
# Drive the real `main()` against the shipped workflow.yaml / issue-types.yaml,
# with its gates stubbed and every gh call answered by a fake that records it,
# so a test can say which PR writes were made.

CAP_ROOT = SCRIPT.parent.parent
BRANCH = "fix/42-do-the-thing"
PR_URL = "https://github.com/o/r/pull/77"
PR_READS = {"list", "view"}
# The variable an earlier revision of #1242 handed the engine's answer down in.
HAND_DOWN_ENV = "PKIT_PM_ISSUE_STATUS"


def _task(labels: list[str]) -> dict:
    """A bug Task (the `fix/` branch's type) carrying `labels` besides its type."""
    return {
        "title": "[Task] do the thing",
        "labels": ["type:bug", *labels],
        "state": "OPEN",
        "body": "Feature: #1\n\n## What\nx",
        "milestone": None,
    }


def _open_pr(*, draft: bool) -> dict:
    return {"number": 77, "state": "OPEN", "isDraft": draft, "headRefName": BRANCH}


def _pr_writes(gh_calls: list[list[str]]) -> list[list[str]]:
    """The `gh pr` calls that change a PR: every one but a list or a view."""
    return [c for c in gh_calls if c[:2] == ["gh", "pr"] and c[2] not in PR_READS]


def _last_failure(err: str) -> str:
    return err[err.rindex("[failed]") :]


@pytest.fixture
def run_main(rw, monkeypatch):
    """Returns `run(issue, *, pr=None, move_rc=0, reviewer=None, engine=None,
    config=None, move=None, dry_run=False)` → `(rc, gh_calls, moves)`. `pr` is
    the open PR on the branch (None: none yet); `engine` the process engine, a
    `FakeEngine` (by default one that gives no answer); `config` the adopter
    config. `move` runs the composed move-issue in process; without it the
    move is recorded and answers `move_rc`."""

    def run(
        issue: dict,
        *,
        pr: dict | None = None,
        move_rc: int = 0,
        reviewer: str | None = None,
        engine: FakeEngine | None = None,
        config: dict | None = None,
        move: MoveIssueInProcess | None = None,
        dry_run: bool = False,
    ):
        gh_calls: list[list[str]] = []
        moves: list[str] = []

        def fake_gh_run(args, config, **kwargs):
            gh_calls.append(list(args))
            stdout = ""
            if args[:3] == ["gh", "pr", "list"]:
                stdout = json.dumps([pr] if pr else [])
            elif args[:3] == ["gh", "pr", "view"]:
                stdout = json.dumps({"body": "filled"})
            elif args[:3] == ["gh", "pr", "create"]:
                stdout = PR_URL
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=stdout, stderr="")

        def move_issue(n, target, **_kw):
            moves.append(target)
            return move_rc

        argv = ["review-work", "42", "--yes", "--base", "main"]
        if reviewer is not None:
            argv += ["--reviewer", reviewer]
        if dry_run:
            argv.append("--dry-run")
        monkeypatch.setattr(sys, "argv", argv)
        monkeypatch.setattr(rw, "resolve_capability_root", lambda _e: CAP_ROOT)
        monkeypatch.setattr(rw.bootstrap_gate, "enforce", lambda *a, **k: True)
        monkeypatch.setattr(rw.session_guard, "enforce", lambda **k: True)
        monkeypatch.setattr(rw, "load_adopter_config", lambda _r: dict(config or {}))
        (engine or FakeEngine()).install(monkeypatch)
        monkeypatch.setattr(rw, "_read_members", lambda *a: [])
        monkeypatch.setattr(
            rw, "resolve_invoker_identity", lambda **k: SimpleNamespace(github_login="me")
        )
        monkeypatch.setattr(rw, "check_membership", lambda *a: SimpleNamespace(allowed=True))
        monkeypatch.setattr(rw.axis_labels, "load_substrate_map", lambda _r: None)
        monkeypatch.setattr(rw, "_gh_get_issue", lambda _n, _c: issue)
        monkeypatch.setattr(rw, "_find_issue_branch", lambda _n: BRANCH)
        monkeypatch.setattr(rw, "_ready_body_ok", lambda *a: True)
        monkeypatch.setattr(rw, "gh_run", fake_gh_run)
        if move is None:
            monkeypatch.setattr(rw.composed_move, "invoke_move_issue", move_issue)
        else:
            monkeypatch.setattr(rw.composed_move, "subprocess", SimpleNamespace(run=move.run))
        return rw.main(), gh_calls, moves

    return run


@pytest.mark.parametrize("pr", [None, _open_pr(draft=True)], ids=["no-pr-yet", "draft-pr"])
def test_refuses_from_backlog_before_any_pr_mutation(run_main, capsys, pr) -> None:
    rc, gh_calls, moves = run_main(_task(["state:backlog"]), pr=pr, reviewer="@alice")
    assert rc == 2
    assert _pr_writes(gh_calls) == []  # no PR opened, flipped or given reviewers
    assert moves == []
    err = capsys.readouterr().err
    assert "the issue is in 'backlog'" in err
    assert "move it first: `move-issue 42 --to in-progress`" in err
    assert "re-run `review-work 42`" in err


def test_refusal_from_todo_names_each_move_on_the_way(run_main, capsys) -> None:
    # No state:* label and no milestone resolves Todo through the shared reader;
    # Review is two moves away from it.
    rc, gh_calls, moves = run_main(_task([]), reviewer="@alice")
    assert rc == 2
    assert _pr_writes(gh_calls) == []
    assert moves == []
    err = capsys.readouterr().err
    assert "the issue is in 'todo'" in err
    assert "`move-issue 42 --to backlog`, then `move-issue 42 --to in-progress`" in err


def test_refusal_without_a_path_lists_legal_targets(run_main, capsys) -> None:
    # Review is Task-only in workflow.yaml: an EPIC has no way there.
    epic = {**_task([]), "title": "[EPIC] a big thing", "labels": ["state:in-progress"]}
    rc, gh_calls, moves = run_main(epic)
    assert rc == 2
    assert _pr_writes(gh_calls) == []
    assert moves == []
    assert "legal targets from 'in-progress': done" in capsys.readouterr().err


def test_opens_a_ready_pr_and_moves_from_in_progress(run_main, capsys) -> None:
    rc, gh_calls, moves = run_main(_task(["state:in-progress"]), reviewer="@alice")
    assert rc == 0
    assert [c[2] for c in _pr_writes(gh_calls)] == ["create", "edit"]
    assert moves == ["review"]
    out, err = capsys.readouterr()
    assert "[ok] PR ready" in out
    assert "[failed]" not in err


def test_rerun_in_review_leaves_a_ready_pr_alone(run_main) -> None:
    # move-issue treats review → review as an idempotent no-op.
    rc, gh_calls, moves = run_main(_task(["state:review"]), pr=_open_pr(draft=False))
    assert rc == 0
    assert _pr_writes(gh_calls) == []
    assert moves == ["review"]


def test_rerun_in_review_flips_a_draft_ready_again(run_main) -> None:
    # After back-to-draft the issue stays in Review; review-work makes it ready.
    rc, gh_calls, moves = run_main(_task(["state:review"]), pr=_open_pr(draft=True))
    assert rc == 0
    assert [c[2] for c in _pr_writes(gh_calls)] == ["ready"]
    assert moves == ["review"]


def test_late_move_failure_names_the_opened_pr_and_its_reviewers(run_main, capsys) -> None:
    rc, gh_calls, moves = run_main(_task(["state:in-progress"]), move_rc=3, reviewer="@alice")
    assert rc == 3  # move-issue's exit code passes through
    assert [c[2] for c in _pr_writes(gh_calls)] == ["create", "edit"]
    assert moves == ["review"]
    out, err = capsys.readouterr()
    assert "[ok]" not in out
    last_block = _last_failure(err)
    assert err.rstrip().endswith("(it reuses the ready PR).")  # the output ends on it
    assert "the issue did not move" in last_block
    assert f"PR #77 ({PR_URL}), opened ready for review" in last_block
    assert "review requested from @alice on PR #77" in last_block


def test_late_move_failure_names_a_flipped_draft(run_main, capsys) -> None:
    rc, _gh_calls, _moves = run_main(
        _task(["state:in-progress"]), pr=_open_pr(draft=True), move_rc=3
    )
    assert rc == 3
    last_block = _last_failure(capsys.readouterr().err)
    assert "PR #77, flipped from draft to ready for review" in last_block
    assert "review requested" not in last_block


def test_late_move_failure_claims_nothing_this_run_did_not_do(run_main, capsys) -> None:
    rc, gh_calls, _moves = run_main(
        _task(["state:in-progress"]), pr=_open_pr(draft=False), move_rc=3
    )
    assert rc == 3
    assert _pr_writes(gh_calls) == []
    last_block = _last_failure(capsys.readouterr().err)
    assert "This run opened no PR, made none ready and requested no reviewers." in last_block


# ---- the closing line claims no move (#1242) ---------------------------
#
# move-issue reads the state itself when it moves, so only its own output says
# whether it moved the issue or found it in Review already.


def test_the_closing_line_says_where_the_issue_is(run_main, capsys) -> None:
    rc, _gh_calls, _moves = run_main(_task(["state:in-progress"]))
    assert rc == 0
    assert capsys.readouterr().out.rstrip().endswith("[ok] PR ready; #42 in Review")


def test_a_rerun_from_review_claims_no_move(run_main, capsys) -> None:
    rc, _gh_calls, _moves = run_main(_task(["state:review"]), pr=_open_pr(draft=True))
    assert rc == 0
    out = capsys.readouterr().out.rstrip()
    assert "→ Review" not in out
    assert out.endswith("[ok] PR ready; #42 in Review")


# ---- the early check reads the issue's own fields (#1242) --------------
#
# review-work's early check reads the state from the labels and milestone of
# the issue it fetched (`_lib/issue_position`, shared with start-work), and
# starts no `pkit process` run: the engine's detectors read those same fields.
# move-issue reads the state itself when it moves. Each test's engine would
# answer otherwise than the labels, so a run that asked it would show.


@pytest.mark.parametrize("pr", [None, _open_pr(draft=True)], ids=["no-pr-yet", "draft-pr"])
def test_a_refused_check_asks_no_engine(run_main, capsys, pr) -> None:
    engine = FakeEngine(status_at("in-progress"))
    rc, gh_calls, moves = run_main(
        _task(["state:backlog"]), pr=pr, engine=engine, reviewer="@alice"
    )
    assert rc == 2
    assert _pr_writes(gh_calls) == []
    assert moves == []
    assert engine.asks == []
    assert "the issue is in 'backlog'" in capsys.readouterr().err


def test_a_dry_run_asks_no_engine(run_main, capsys) -> None:
    engine = FakeEngine(status_at("backlog"))
    rc, gh_calls, moves = run_main(_task(["state:in-progress"]), engine=engine, dry_run=True)
    assert rc == 0
    assert gh_calls == []
    assert moves == []
    assert engine.asks == []
    assert "(dry-run: would open/flip-ready PR" in capsys.readouterr().out


def test_a_legal_move_asks_no_engine_before_the_move(run_main) -> None:
    engine = FakeEngine(status_at("backlog"))
    rc, gh_calls, moves = run_main(_task(["state:in-progress"]), engine=engine, reviewer="@alice")
    assert rc == 0
    assert [c[2] for c in _pr_writes(gh_calls)] == ["create", "edit"]
    assert moves == ["review"]
    assert engine.asks == []


def test_a_board_carried_state_is_read_off_the_labels_as_before(run_main) -> None:
    # Where the board carries state and the engine gives nothing, the check
    # reads the labels, as it did before #1242; nothing is newly refused.
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]), config={"has_projects_v2_board": True}, reviewer="@alice"
    )
    assert rc == 0
    assert [c[2] for c in _pr_writes(gh_calls)] == ["create", "edit"]
    assert moves == ["review"]


def test_a_state_changed_after_the_check_is_refused_by_move_issue(
    run_main, monkeypatch, capsys
) -> None:
    """The check reads In Progress; by the time move-issue reads, the issue is
    back in Backlog. move-issue refuses Backlog → Review, and review-work ends
    on the PR and reviewers it left behind."""
    engine = FakeEngine(status_at("backlog"))
    move = MoveIssueInProcess(monkeypatch, _task(["state:backlog"]))
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]), engine=engine, move=move, reviewer="@alice"
    )
    assert rc == 2
    assert [c[2] for c in _pr_writes(gh_calls)] == ["create", "edit"]
    assert moves == []  # the move ran in process, not through the recording stub
    assert len(move.runs) == 1
    assert len(engine.asks) == 1  # move-issue's own read, at move time
    out, err = capsys.readouterr()
    assert "[ok] PR ready" not in out
    assert "no transition 'backlog' → 'review'" in err
    last_block = _last_failure(err)
    assert last_block.startswith(
        "[failed] review-work #42: move-issue --to review failed (exit 2); the issue did not move."
    )
    assert f"PR #77 ({PR_URL}), opened ready for review" in last_block
    assert "review requested from @alice on PR #77" in last_block


def test_a_value_in_the_environment_does_not_stand_in_for_the_labels(
    run_main, monkeypatch, capsys
) -> None:
    # A value saying In Progress, from which the check would pass; the labels
    # say Backlog.
    monkeypatch.setenv(HAND_DOWN_ENV, json.dumps({"issue": 42, "status": status_at("in-progress")}))
    rc, gh_calls, moves = run_main(_task(["state:backlog"]), reviewer="@alice")
    assert rc == 2
    assert _pr_writes(gh_calls) == []
    assert moves == []
    assert "the issue is in 'backlog'" in capsys.readouterr().err
