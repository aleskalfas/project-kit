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
from tests.pm_ownership_support import FakeGitHub, clone_with

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
PR_NUMBER = 77
#: The head the description's list was derived at, and the PR's head by default.
LISTED = "a" * 40
#: A later head of the PR, after a fix round the list was not derived again for.
MOVED = "c" * 40
#: Where the head the list was derived at left its base, as its marker names it.
LEFT = "b" * 40
#: Where the PR's head left another base, after the PR was retargeted.
RETARGETED = "d" * 40
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
    return {"number": PR_NUMBER, "state": "OPEN", "isDraft": draft, "headRefName": BRANCH}


def _pr_writes(gh_calls: list[list[str]]) -> list[list[str]]:
    """The `gh pr` calls that change a PR: every one but a list or a view."""
    return [c for c in gh_calls if c[:2] == ["gh", "pr"] and c[2] not in PR_READS]


def _last_failure(err: str) -> str:
    return err[err.rindex("[failed]") :]


@pytest.fixture
def run_main(rw, monkeypatch):
    """Returns `run(issue, *, pr=None, body="filled", head=LISTED, derived=None,
    derives=None, sources=None, fork=False, move_rc=0, reviewer=None, engine=None,
    config=None, move=None, dry_run=False, instance=None, github=None, extra=())` →
    `(rc, gh_calls, moves)`. `pr` is the open PR on the branch (None: none yet), `body`
    its description, None for one gh cannot read, and `head` its head. The body
    validator finds nothing in the description, and the author's
    sentences are read from it as they stand. `derived` is what deriving the list at
    the PR's head gives,
    `derives` records each (head, base) it is derived for, and `sources` where
    each was to fetch the head from; without `derived`, a derivation gives no
    list. `fork` says the PR comes from a fork. `engine` is the process engine,
    a `FakeEngine` (by default one that gives no answer); `config` the adopter
    config. `move` runs the
    composed move-issue in process; without it the move is recorded and answers
    `move_rc`. `instance` is this clone's instance id (none by default), and
    `github` the in-memory GitHub its ownership calls reach; each ownership
    write is recorded in `gh_calls` too, in its place among the PR calls.
    `extra` adds to the command line."""

    def run(
        issue: dict,
        *,
        pr: dict | None = None,
        body: str | None = "filled",
        head: str = LISTED,
        derived: object | None = None,
        derives: list[tuple[str, str]] | None = None,
        sources: list[object] | None = None,
        fork: bool = False,
        move_rc: int = 0,
        reviewer: str | None = None,
        engine: FakeEngine | None = None,
        config: dict | None = None,
        move: MoveIssueInProcess | None = None,
        dry_run: bool = False,
        instance: int | None = None,
        github: FakeGitHub | None = None,
        extra: tuple[str, ...] = (),
    ):
        gh_calls: list[list[str]] = []
        moves: list[str] = []
        fake = github if github is not None else FakeGitHub()

        def ownership_gh(args: list[str], _config: dict):
            if args[1:3] != ["issue", "view"]:
                gh_calls.append([str(a) for a in args])
            return fake(args)

        clone_with(rw.instance_claims, monkeypatch, instance)
        monkeypatch.setattr(rw.instance_claims, "_gh", ownership_gh)

        def fake_gh_run(args, config, **kwargs):
            gh_calls.append(list(args))
            stdout = ""
            if args[:3] == ["gh", "pr", "list"]:
                stdout = json.dumps([pr] if pr else [])
            elif args[:3] == ["gh", "pr", "view"]:
                if body is None:
                    return subprocess.CompletedProcess(
                        args=args, returncode=1, stdout="", stderr="HTTP 502: Bad Gateway"
                    )
                stdout = json.dumps(
                    {
                        "body": body,
                        "headRefOid": head,
                        "baseRefName": "main",
                        "headRefName": BRANCH,
                        "isCrossRepository": fork,
                    }
                )
            elif args[:3] == ["gh", "pr", "create"]:
                stdout = PR_URL
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=stdout, stderr="")

        def move_issue(n, target, **_kw):
            moves.append(target)
            return move_rc

        def checked(at: str, base: str, *, source: object = None):
            (derives if derives is not None else []).append((at, base))
            (sources if sources is not None else []).append(source)
            if derived is not None:
                return derived
            return rw.friction_answers.Derivation(at, problem="no list was stood in")

        argv = ["review-work", "42", "--yes", "--base", "main"]
        if reviewer is not None:
            argv += ["--reviewer", reviewer]
        if dry_run:
            argv.append("--dry-run")
        argv += list(extra)
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
        monkeypatch.setattr(rw.issue_branch, "_local_branches", lambda: (BRANCH,))
        monkeypatch.setattr(rw.pr_validation, "validate_pr", lambda **k: [])
        monkeypatch.setattr(rw, "gh_run", fake_gh_run)
        monkeypatch.setattr(rw.friction_answers, "checked", checked)
        # The PR's base is fetched from `upstream`; the branch tracks no remote here.
        monkeypatch.setattr(rw.friction_answers, "base_remote", lambda _base: "upstream")
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


# ---- the clash guard (DEC-035 point 6) ------------------------------------------
#
# With an instance id set, review-work reads the issue's owner before it opens a
# PR, makes one ready or requests reviewers. The in-memory GitHub holds issue #42
# with a claim of instance 3, and this clone is instance 2.


def _owned_by_instance_3(rw) -> FakeGitHub:
    github = FakeGitHub()
    github.add(42, assignees=("me",))
    github.post(42, rw.instance_claims.ownership.format_event_comment(event="claim", instance=3))
    return github


def test_the_clash_guard_refuses_before_any_pr_write(run_main, rw, capsys) -> None:
    github = _owned_by_instance_3(rw)
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]), reviewer="@alice", instance=2, github=github
    )
    assert rc == 1
    assert gh_calls == []  # no PR read, opened, made ready or given reviewers
    assert moves == []
    assert github.writes() == []
    err = capsys.readouterr().err
    assert (
        "[refused] review-work #42: #42 is owned by instance 3, and this clone is instance 2" in err
    )
    assert 'pass --bypass-owner "<reason>"' in err


def test_bypass_owner_posts_its_reason_first_and_once(run_main, rw, monkeypatch, capsys) -> None:
    """The audit comment comes before the PR is opened, and the composed
    move-issue, run in process, is handed the reason and posts no second one."""
    github = _owned_by_instance_3(rw)
    move = MoveIssueInProcess(monkeypatch, _task(["state:review"]))
    # The child runs as the same person as review-work, as a real child does.
    me = SimpleNamespace(github_login="me")
    monkeypatch.setattr(move.module, "resolve_invoker_identity", lambda config=None: me)
    rc, gh_calls, _moves = run_main(
        _task(["state:in-progress"]),
        reviewer="@alice",
        engine=FakeEngine(status_at("review")),
        move=move,
        instance=2,
        github=github,
        extra=("--bypass-owner", "instance 3's session is gone"),
    )
    assert rc == 0
    writes = [c[1:3] for c in gh_calls if c[2] not in PR_READS]
    assert writes == [["issue", "comment"], ["pr", "create"], ["pr", "edit"]]
    assert move.runs[0][-2:] == ["--bypass-owner", "instance 3's session is gone"]
    audits = [c["body"] for c in github.issues[42].comments if "pkit-audit-key" in c["body"]]
    assert len(audits) == 1
    assert "Bypassed by me: instance 3's session is gone" in audits[0]
    captured = capsys.readouterr()
    assert "--bypass-owner let this clone, instance 2, act on it" in captured.err
    assert "audit comment already present; idempotent skip" in captured.out
    assert captured.out.rstrip().endswith("[ok] PR ready; #42 in Review")


# ---- the author's sentences (DEC-055 point 3) -------------------------------------
#
# Where the description carries the list of the answers the change wrote, each
# document it marks `updated` needs a sentence on what changed in it. review-work
# refuses before it makes the PR ready, requests reviewers or moves the issue;
# open-pr and edit-pr only warn (their own tests). Where the list is for another
# head than the PR's, it derives the list at the PR's head and refuses exactly
# what that list marks `updated` with no sentence; a document only the
# description's list marks gets an information line instead.

SENTENCES = "## What changed in each updated document"
FILLED = "Closes #42\n\n## Summary\nwork\n\n## Doc impact\n- [x] the guide\n"


def _document(*updated: str, **others: str) -> dict:
    """The change check's document for a change that revalidated each of `updated`
    as updated, each of `others` with the answer given, and `docs/api.md` as
    unchanged."""
    entries = [{"location": location, "answer": "updated", "changed": []} for location in updated]
    for location, answer in others.items():
        entries.append({"location": location, "answer": answer, "reason": "Holds."})
    entries.append({"location": "docs/api.md", "answer": "unchanged", "reason": "Holds."})
    return {"base": {"commit": LEFT}, "answers": entries, "unreadable": []}


def _described(rw, said: str = "", *updated: str) -> str:
    """A description whose list, derived at `LISTED`, marks each of `updated` as
    updated in the change and holds `docs/api.md`, with `said` — the author's
    sentences — above it."""
    section = rw.friction_answers.render(_document(*updated), LISTED)
    assert section is not None
    return f"{FILLED}\n{said}\n{section}\n"


def _derived_at_moved(rw, document: dict):
    """What deriving the list at `MOVED` gives: the change check's `document`."""
    return rw.friction_answers.Derivation(
        MOVED, document=document, answers=tuple(document["answers"])
    )


def _refusals(err: str) -> list[str]:
    return [ln for ln in err.splitlines() if ln.startswith("  - [hard-reject] body.sentences: ")]


def _refusal(location: str) -> str:
    return (
        f"  - [hard-reject] body.sentences: {location} is marked updated in the description's "
        f"list, and the description gives no sentence on what changed in it — under "
        f'`{SENTENCES}`, write one on a line of its own as "- `path`: sentence", starting in '
        "the line's first column, the document in a code span as the list names it"
    )


def _out_of_date(location: str) -> str:
    """The information line for `location`, which the list for `LISTED` marks
    updated and the list at `MOVED` does not."""
    return (
        f"  [info] {location} is marked updated in the description's list, for aaaaaaa, and "
        f"not in the list at PR #{PR_NUMBER}'s head ccccccc: the description's list is out of "
        "date for it, and it needs no sentence. land-work writes the list again before it "
        "merges; a merge through done-work or merge-pr run directly keeps the list as written."
    )


#: The step a refused description of the open PR ends with.
EDIT_STEP = (
    f"  → write the description with `edit-pr {PR_NUMBER} --body-file <file>`, then run "
    "`review-work 42` again; --force overrides."
)


@pytest.mark.parametrize("draft", [True, False], ids=["draft-pr", "ready-pr"])
def test_an_updated_document_with_no_sentence_is_refused_before_any_write(
    run_main, rw, capsys, draft
) -> None:
    """The list is for the PR's head: each document it marks updated with no
    sentence is named, with the one-line form, and the refusal ends with the edit
    to make; nothing is derived, made ready or moved, and no reviewer requested."""
    said = f"{SENTENCES}\n\n- `docs/guide.md`: The guide names the new flag.\n"
    body = _described(rw, said, "docs/guide.md", "docs/cli.md", "docs/notes.md")
    derives: list[tuple[str, str]] = []
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=draft),
        body=body,
        derives=derives,
        reviewer="@alice",
    )
    assert rc == 1
    assert _pr_writes(gh_calls) == []
    assert moves == []
    assert derives == []
    out, err = capsys.readouterr()
    assert "[refused] PR body is not ready for review:" in err.splitlines()
    assert _refusals(err) == [_refusal("docs/cli.md"), _refusal("docs/notes.md")]
    assert err.splitlines()[-1] == EDIT_STEP
    assert "[info]" not in out and "[ok]" not in out


def test_a_list_for_an_earlier_head_refuses_a_document_the_head_still_marks_updated(
    run_main, rw, capsys
) -> None:
    """A fix round moved the head and left the document updated: the list derived
    at the PR's head marks it too, so it is refused as before, and no line calls
    the description's list out of date."""
    body = _described(rw, "", "docs/cli.md")
    derives: list[tuple[str, str]] = []
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=True),
        body=body,
        head=MOVED,
        derived=_derived_at_moved(rw, _document("docs/cli.md")),
        derives=derives,
    )
    assert rc == 1
    assert _pr_writes(gh_calls) == [] and moves == []
    assert derives == [(MOVED, "main")]
    out, err = capsys.readouterr()
    assert _refusals(err) == [_refusal("docs/cli.md")]
    assert err.splitlines()[-1] == EDIT_STEP
    assert "[info]" not in out


def test_a_document_updated_since_the_list_was_written_is_refused_too(run_main, rw, capsys) -> None:
    """The list at the PR's head decides: a document a fix round updated after the
    description's list was written, with no sentence, is refused beside the rest."""
    said = f"{SENTENCES}\n\n- `docs/guide.md`: The guide names the new flag.\n"
    body = _described(rw, said, "docs/guide.md")
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=True),
        body=body,
        head=MOVED,
        derived=_derived_at_moved(rw, _document("docs/guide.md", "docs/new.md")),
    )
    assert rc == 1
    assert _pr_writes(gh_calls) == [] and moves == []
    out, err = capsys.readouterr()
    assert _refusals(err) == [_refusal("docs/new.md")]
    assert "[info]" not in out


@pytest.mark.parametrize(
    ("fork", "remote", "ref"),
    [(False, "origin", f"refs/heads/{BRANCH}"), (True, "upstream", f"refs/pull/{PR_NUMBER}/head")],
    ids=["same-repository", "fork"],
)
def test_the_head_is_fetched_from_the_pr_s_branch_or_its_pull_ref(
    run_main, rw, fork, remote, ref
) -> None:
    """Where this clone lacks the PR's head, the derivation fetches it, as land-work
    fetches it: from the PR's branch on the remote it is pushed to, or for a fork
    from the ref the base repository keeps for the PR, on the base's remote."""
    sources: list[object] = []
    run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=True),
        body=_described(rw, "", "docs/cli.md"),
        head=MOVED,
        derived=_derived_at_moved(rw, _document("docs/cli.md")),
        sources=sources,
        fork=fork,
    )
    assert sources == [rw.friction_answers.Source(remote, ref)]


@pytest.mark.parametrize(
    "now",
    [{"docs/notes.md": "unchanged"}, {"docs/notes.md": "deferred"}, {}],
    ids=["answered-unchanged", "deferred", "revalidation-dropped"],
)
def test_a_document_the_head_no_longer_marks_updated_is_told_and_not_refused(
    run_main, rw, capsys, now
) -> None:
    """A fix round answered the document otherwise, or dropped its revalidation,
    and edit-pr carried the list as it was: one information line names both heads
    and says the list is out of date for it, and the PR goes to review."""
    said = f"{SENTENCES}\n\n- `docs/guide.md`: The guide names the new flag.\n"
    body = _described(rw, said, "docs/guide.md", "docs/notes.md")
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=True),
        body=body,
        head=MOVED,
        derived=_derived_at_moved(rw, _document("docs/guide.md", **now)),
    )
    assert rc == 0
    assert [c[2] for c in _pr_writes(gh_calls)] == ["ready"]
    assert moves == ["review"]
    out, err = capsys.readouterr()
    assert "body.sentences" not in err and "[refused]" not in err
    assert [ln for ln in out.splitlines() if "[info]" in ln] == [_out_of_date("docs/notes.md")]
    assert out.rstrip().endswith("[ok] PR ready; #42 in Review")


@pytest.mark.parametrize("draft", [True, False], ids=["draft-pr", "ready-pr"])
def test_a_list_that_cannot_be_derived_at_the_head_stops_and_refuses_nothing(
    run_main, rw, capsys, draft
) -> None:
    """Never a pass on a guess, and never a refusal on a list nobody read: where the
    list cannot be derived at the PR's head, the run stops at exit 2, asks no edit,
    and says to run again."""
    body = _described(rw, "", "docs/notes.md")
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]), pr=_open_pr(draft=draft), body=body, head=MOVED
    )
    assert rc == rw.EXIT_UNDERIVED == 2
    assert _pr_writes(gh_calls) == [] and moves == []
    out, err = capsys.readouterr()
    assert err.splitlines()[-1] == (
        f"error: the list of answers at PR #{PR_NUMBER}'s head ccccccc could not be derived "
        "(no list was stood in), and the description's list is for aaaaaaa, so which "
        "documents need a sentence cannot be told. Nothing was made ready, no reviewer "
        "requested and the issue not moved. Run review-work again once it can be derived."
    )
    assert _refusals(err) == [] and "edit-pr" not in err
    assert "[info]" not in out


def test_a_list_for_the_head_is_read_from_the_description_whatever_base_it_names(
    run_main, rw, capsys
) -> None:
    """The marker's head alone decides whether to derive, since where a head left its
    base is the backbone's to compute (COR-054 point 5): a PR retargeted with its head
    unmoved keeps the description's list, and the refusal rests on it (DEC-055 point
    3). The reviewer backs it, and land-work writes the list again before it merges."""
    body = _described(rw, "", "docs/notes.md").replace(f" base={LEFT}", f" base={RETARGETED}")
    assert f" base={RETARGETED}" in body
    derives: list[tuple[str, str]] = []
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=True),
        body=body,
        derived=rw.friction_answers.Derivation(LISTED, document=_document(), answers=()),
        derives=derives,
    )
    assert rc == 1
    assert derives == []
    assert _pr_writes(gh_calls) == [] and moves == []
    out, err = capsys.readouterr()
    assert _refusals(err) == [_refusal("docs/notes.md")]
    assert "[info]" not in out


def test_under_force_a_list_that_cannot_be_derived_gives_way_to_the_description_s(
    run_main, rw, capsys
) -> None:
    """--force passes the refusal, so a list that cannot be derived at the head does
    not stop the run: the description's list is read as it stands, a warning says
    so, and its findings are printed and overridden (DEC-055 point 3)."""
    body = _described(rw, "", "docs/notes.md")
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=True),
        body=body,
        head=MOVED,
        extra=("--force",),
    )
    assert rc == 0
    assert [c[2] for c in _pr_writes(gh_calls)] == ["ready"]
    assert moves == ["review"]
    err = capsys.readouterr().err
    assert (
        f"  [warn] the list of answers at PR #{PR_NUMBER}'s head ccccccc could not be derived "
        "(no list was stood in), and the description's list is for aaaaaaa; under --force, "
        "the description's list is read as it stands, and its findings are overridden."
    ) in err.splitlines()
    assert _refusals(err) == [_refusal("docs/notes.md")]
    assert err.splitlines()[-1] == "  → proceeding under --force."


def test_a_sentence_the_list_at_the_head_does_not_show_is_warned_of(run_main, rw, capsys) -> None:
    """Where the list is derived at the PR's head, a sentence on a document it does
    not mark updated is warned of, as open-pr and land-work warn of it, with the edit
    that removes it; it refuses nothing (DEC-055 point 3)."""
    said = (
        f"{SENTENCES}\n\n- `docs/guide.md`: The guide names the new flag.\n"
        "- `docs/api.md`: The page is still right.\n"
    )
    body = _described(rw, said, "docs/guide.md")
    rc, _gh_calls, moves = run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=True),
        body=body,
        head=MOVED,
        derived=_derived_at_moved(rw, _document("docs/guide.md")),
    )
    assert rc == 0
    assert moves == ["review"]
    err = capsys.readouterr().err
    assert [ln for ln in err.splitlines() if "[warn]" in ln] == [
        "  [warn] docs/api.md has a sentence under `## What changed in each updated document`, "
        "and the list at ccccccc does not mark it updated, so the list does not show the "
        f"sentence — remove it from the description with `edit-pr {PR_NUMBER} --body-file "
        "<file>`"
    ]


@pytest.mark.parametrize("draft", [True, False], ids=["draft-pr", "ready-pr"])
def test_a_description_that_cannot_be_read_stops_before_any_write(run_main, capsys, draft) -> None:
    """A failed read is never read as a description with no list, which would pass
    a ready PR and move the issue: the run stops at exit 3, saying what failed."""
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]), pr=_open_pr(draft=draft), body=None, reviewer="@alice"
    )
    assert rc == 3
    assert _pr_writes(gh_calls) == []
    assert moves == []
    err = capsys.readouterr().err
    assert (
        f"error: PR #{PR_NUMBER}'s description could not be read (HTTP 502: Bad Gateway); "
        "nothing was made ready, no reviewer requested and the issue not moved. Run "
        "review-work again once it can be read."
    ) in err.splitlines()


@pytest.mark.parametrize(
    ("head", "derived"),
    [(LISTED, []), (MOVED, [(MOVED, "main")])],
    ids=["list-for-the-head", "earlier-list"],
)
def test_with_every_sentence_given_it_proceeds_as_before(
    run_main, rw, capsys, head, derived
) -> None:
    """Every sentence given: the PR goes to review. A list for the PR's head is read
    from the description alone; one for an earlier head is derived at the PR's head
    once, whatever it shows."""
    said = (
        f"{SENTENCES}\n\n- `docs/guide.md`: The guide names the new flag.\n"
        "- `docs/cli.md`: The page lists the new command.\n"
    )
    body = _described(rw, said, "docs/guide.md", "docs/cli.md")
    derives: list[tuple[str, str]] = []
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=True),
        body=body,
        head=head,
        derived=_derived_at_moved(rw, _document("docs/guide.md", "docs/cli.md")),
        derives=derives,
    )
    assert rc == 0
    assert [c[2] for c in _pr_writes(gh_calls)] == ["ready"]
    assert moves == ["review"]
    assert derives == derived
    out, err = capsys.readouterr()
    assert "body.sentences" not in err
    assert out.rstrip().endswith("[ok] PR ready; #42 in Review")


def test_a_description_with_no_list_is_not_refused(run_main) -> None:
    """No list, nothing marked updated: a change that wrote no answers, or a list
    open-pr left out, which land-work writes or refuses."""
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]), pr=_open_pr(draft=True), body=FILLED
    )
    assert rc == 0
    assert [c[2] for c in _pr_writes(gh_calls)] == ["ready"]
    assert moves == ["review"]


def test_an_item_not_read_as_a_sentence_is_named_beside_the_refusal(run_main, rw, capsys) -> None:
    """A sentence written in another form, the document in bold, gives none: the
    refusal names the document, and the item by its line, with the form."""
    item = "- **docs/guide.md:** The guide names the new flag."
    body = _described(rw, f"{SENTENCES}\n\n{item}\n", "docs/guide.md")
    rc, gh_calls, moves = run_main(_task(["state:in-progress"]), pr=_open_pr(draft=True), body=body)
    assert rc == 1
    assert _pr_writes(gh_calls) == [] and moves == []
    err = capsys.readouterr().err
    assert _refusals(err) == [_refusal("docs/guide.md")]
    line = body.split("\n").index(item) + 1
    assert (
        f"  - [warning] body.sentences: line {line} of the description, under `{SENTENCES}`, "
        f'is not read as a sentence: "{item}" — write it as "- `path`: sentence", starting in '
        "the line's first column, the document in a code span as the list names it"
    ) in err.splitlines()


def test_force_takes_the_pr_to_review_past_the_refusal(run_main, rw, capsys) -> None:
    """--force overrides the refusal as it overrides every hard-reject (DEC-046)."""
    body = _described(rw, "", "docs/guide.md")
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]), pr=_open_pr(draft=True), body=body, extra=("--force",)
    )
    assert rc == 0
    assert [c[2] for c in _pr_writes(gh_calls)] == ["ready"]
    assert moves == ["review"]
    err = capsys.readouterr().err
    assert _refusals(err) == [_refusal("docs/guide.md")]
    assert err.splitlines()[-1] == "  → proceeding under --force."


def test_the_refusal_joins_the_body_validator_s_findings(rw, monkeypatch, capsys) -> None:
    """One refusal names every blocking finding, the validator's and the sentences'."""
    no_doc_impact = rw.pr_validation.Finding(
        rw.pr_validation.SEVERITY_HARD_REJECT, "body.doc-impact", "no Doc impact"
    )
    monkeypatch.setattr(rw.pr_validation, "validate_pr", lambda **k: [no_doc_impact])
    description = rw._Description(
        _described(rw, "", "docs/guide.md"), number=PR_NUMBER, head=LISTED, base="main"
    )
    sentences = rw._sentence_findings(description)
    assert sentences is not None
    assert (
        rw._ready_body_ok(
            description.body, {}, CAP_ROOT, False, sentences=sentences, next_step=rw.FILL_FIRST
        )
        is False
    )
    err = capsys.readouterr().err
    assert "  - [hard-reject] body.doc-impact: no Doc impact" in err.splitlines()
    assert _refusals(err) == [_refusal("docs/guide.md")]
    assert err.splitlines()[-1] == f"  → {rw.FILL_FIRST}; --force overrides."
