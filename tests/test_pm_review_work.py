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
#: The PR's head by default.
LISTED = "a" * 40
#: A later head of the PR, after a fix round.
MOVED = "c" * 40
#: Where the PR's head left its base, as the change check names it.
LEFT = "b" * 40
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
    config=None, move=None, dry_run=False, instance=None, github=None, extra=(),
    findings=(), comments=(), comment_rc=0)` →
    `(rc, gh_calls, moves)`. `pr` is the open PR on the branch (None: none yet), `body`
    its description, None for one gh cannot read, and `head` its head. The body
    validator finds `findings` in the description, by default nothing, and the author's
    sentences are read from it as they stand. `comments` are the PR's comments, and
    `comment_rc` what a `gh pr comment` exits. `derived` is what the change check at
    the PR's head gives,
    `derives` records each (head, base) it is run for, and `sources` where
    each was to fetch the head from; without `derived`, the change check gives no
    answers. `fork` says the PR comes from a fork. `engine` is the process engine,
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
        findings: tuple[object, ...] = (),
        comments: tuple[dict, ...] = (),
        comment_rc: int = 0,
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
                    {"comments": list(comments)}
                    if "comments" in args
                    else {
                        "body": body,
                        "headRefOid": head,
                        "baseRefName": "main",
                        "headRefName": BRANCH,
                        "isCrossRepository": fork,
                    }
                )
            elif args[:3] == ["gh", "pr", "create"]:
                stdout = PR_URL
            elif args[:3] == ["gh", "pr", "comment"] and comment_rc:
                return subprocess.CompletedProcess(
                    args=args, returncode=comment_rc, stdout="", stderr="HTTP 502: Bad Gateway"
                )
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=stdout, stderr="")

        def move_issue(n, target, **_kw):
            moves.append(target)
            return move_rc

        def checked(at: str, base: str, *, source: object = None, from_checkout: bool = True):
            (derives if derives is not None else []).append((at, base))
            (sources if sources is not None else []).append(source)
            if derived is not None:
                return derived
            return rw.friction_answers.Derivation(at, document=_document(), answers=())

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
        monkeypatch.setattr(rw.pr_validation, "validate_pr", lambda **k: list(findings))
        monkeypatch.setattr(rw, "gh_run", fake_gh_run)
        monkeypatch.setattr(rw.friction_answers, "checked", checked)
        monkeypatch.setattr(rw.head_programs, "build_commits", lambda *a: frozenset())
        # The PR's base is fetched from `upstream`; the branch tracks no remote here.
        monkeypatch.setattr(rw.pr_head, "base_remote", lambda _base: "upstream")
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


# ---- the author's sentences (DEC-065 point 3) -------------------------------------
#
# The description carries no list of the answers the change wrote: review-work runs
# the change check at the PR's head on every move, and each document it marks
# `updated` needs a sentence on what changed in it. review-work refuses before it
# makes the PR ready, requests reviewers or moves the issue; open-pr only warns, and
# edit-pr derives nothing (their own tests).

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


def _described(said: str = "") -> str:
    """A description with `said` — the author's sentences — below its sections."""
    return f"{FILLED}\n{said}"


def _derived(rw, document: dict, at: str = LISTED):
    """What the change check at `at` gives: its `document`."""
    return rw.friction_answers.Derivation(at, document=document, answers=tuple(document["answers"]))


def _refusals(err: str) -> list[str]:
    return [ln for ln in err.splitlines() if ln.startswith("  - [hard-reject] body.sentences: ")]


def _refusal(location: str) -> str:
    return (
        f"  - [hard-reject] body.sentences: {location} is updated in this change, and the "
        f"description gives no sentence on what changed in it — under `{SENTENCES}`, write one "
        'on a line of its own as "- `path`: sentence", starting in the line\'s first column, '
        "the document in a code span as the change check names it"
    )


#: The step a refused description of the open PR ends with.
EDIT_STEP = (
    f"  → write the description with `edit-pr {PR_NUMBER} --body-file <file>`, then run "
    "`review-work 42` again; --force overrides."
)
#: The guide's sentence, as the author writes it.
GUIDE = f"{SENTENCES}\n\n- `docs/guide.md`: The guide names the new flag.\n"


@pytest.mark.parametrize("draft", [True, False], ids=["draft-pr", "ready-pr"])
def test_an_updated_document_with_no_sentence_is_refused_before_any_write(
    run_main, rw, capsys, draft
) -> None:
    """The change check at the PR's head decides: each document it marks updated with
    no sentence is named, with the one-line form, and the refusal ends with the edit
    to make; nothing is made ready or moved, and no reviewer requested."""
    derives: list[tuple[str, str]] = []
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=draft),
        body=_described(GUIDE),
        derived=_derived(rw, _document("docs/guide.md", "docs/cli.md", "docs/notes.md")),
        derives=derives,
        reviewer="@alice",
    )
    assert rc == 1
    assert _pr_writes(gh_calls) == []
    assert moves == []
    assert derives == [(LISTED, "main")]
    out, err = capsys.readouterr()
    assert "[refused] PR body is not ready for review:" in err.splitlines()
    assert _refusals(err) == [_refusal("docs/cli.md"), _refusal("docs/notes.md")]
    assert err.splitlines()[-1] == EDIT_STEP
    assert "[ok]" not in out


@pytest.mark.parametrize("head", [LISTED, MOVED], ids=["first-move", "after-a-fix-round"])
def test_with_every_sentence_given_it_proceeds_and_the_check_ran_at_the_head(
    run_main, rw, capsys, head
) -> None:
    """Every sentence given: the PR goes to review. The change check runs once, at the
    PR's head, on every move, a fix round's included (DEC-065 point 3)."""
    said = f"{GUIDE}- `docs/cli.md`: The page lists the new command.\n"
    derives: list[tuple[str, str]] = []
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=True),
        body=_described(said),
        head=head,
        derived=_derived(rw, _document("docs/guide.md", "docs/cli.md"), at=head),
        derives=derives,
    )
    assert rc == 0
    assert [c[2] for c in _pr_writes(gh_calls)] == ["ready"]
    assert moves == ["review"]
    assert derives == [(head, "main")]
    out, err = capsys.readouterr()
    assert "body.sentences" not in err
    assert out.rstrip().endswith("[ok] PR ready; #42 in Review")


#: A sentence the host would close an issue with: past tense, which the closing
#: references this capability reads leave out.
CLOSING = f"{SENTENCES}\n\n- `docs/guide.md`: This fixed #77 in the guide.\n"
CLOSING_REFUSAL = (
    "  - [hard-reject] body.sentences: the sentence on what changed in docs/guide.md, under "
    f"`{SENTENCES}`, reads as a closing reference (fixed #77): the host would close an issue "
    "with it at merge — reword it"
)


def test_a_sentence_that_reads_as_a_closing_reference_is_refused_before_any_write(
    run_main, rw, capsys
) -> None:
    """It stays in the description and the squash commit, where the host reads it
    (DEC-065 point 5). The refusal is the sentences', named with the edit to make."""
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=True),
        body=_described(CLOSING),
        derived=_derived(rw, _document("docs/guide.md")),
    )
    assert rc == 1
    assert _pr_writes(gh_calls) == [] and moves == []
    _out, err = capsys.readouterr()
    assert _refusals(err) == [CLOSING_REFUSAL]
    assert err.splitlines()[-1] == EDIT_STEP


def test_force_passes_a_sentence_that_reads_as_a_closing_reference(run_main, rw, capsys) -> None:
    """A `hard-reject`, overridden as every one is (DEC-046); land-work still refuses
    it, and nothing overrides that."""
    rc, _gh_calls, moves = run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=True),
        body=_described(CLOSING),
        derived=_derived(rw, _document("docs/guide.md")),
        extra=("--force",),
    )
    assert rc == 0 and moves == ["review"]
    _out, err = capsys.readouterr()
    assert _refusals(err) == [CLOSING_REFUSAL]
    assert err.splitlines()[-1] == "  → proceeding under --force."


def test_a_list_an_earlier_run_left_in_the_description_is_not_read(run_main, rw, capsys) -> None:
    """A list an earlier run wrote marks a document updated that the change check at
    the head does not: nothing is refused for it, since the answers are the check's
    alone (DEC-065 point 2)."""
    listed = "\n".join(
        [
            rw.friction_answers.HEADING,
            "",
            f"{rw.friction_answers.MARKER_START} head={MOVED} base={LEFT} -->",
            "1. `docs/notes.md` — **updated in this change**",
            rw.friction_answers.MARKER_END,
        ]
    )
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=True),
        body=f"{_described(GUIDE)}\n{listed}\n",
        derived=_derived(rw, _document("docs/guide.md", **{"docs/notes.md": "unchanged"})),
    )
    assert rc == 0
    assert [c[2] for c in _pr_writes(gh_calls)] == ["ready"] and moves == ["review"]
    assert "body.sentences" not in capsys.readouterr().err


@pytest.mark.parametrize(
    ("fork", "remote", "ref"),
    [(False, "origin", f"refs/heads/{BRANCH}"), (True, "upstream", f"refs/pull/{PR_NUMBER}/head")],
    ids=["same-repository", "fork"],
)
def test_the_head_is_fetched_from_the_pr_s_branch_or_its_pull_ref(
    run_main, rw, fork, remote, ref
) -> None:
    """Where this clone lacks the PR's head, the change check fetches it, as land-work
    fetches it: from the PR's branch on the remote it is pushed to, or for a fork
    from the ref the base repository keeps for the PR, on the base's remote."""
    sources: list[object] = []
    run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=True),
        body=_described(),
        head=MOVED,
        derived=_derived(rw, _document("docs/cli.md"), at=MOVED),
        sources=sources,
        fork=fork,
    )
    assert sources == [rw.pr_head.Source(remote, ref)]


#: What review-work says of a change check it could not run at the PR's head.
UNDERIVED = (
    f"the change check at PR #{PR_NUMBER}'s head ccccccc could not be run (no answers were "
    "stood in)"
)


@pytest.mark.parametrize("draft", [True, False], ids=["draft-pr", "ready-pr"])
def test_a_check_that_cannot_be_run_at_the_head_stops_and_refuses_nothing(
    run_main, rw, capsys, draft
) -> None:
    """Never a pass on a guess, and never a refusal on answers nobody read: where the
    change check cannot be run at the PR's head, the run stops at exit 2, asks no
    edit, and says to run again."""
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=draft),
        body=_described(),
        head=MOVED,
        derived=rw.friction_answers.Derivation(MOVED, problem="no answers were stood in"),
    )
    assert rc == rw.EXIT_UNDERIVED == 2
    assert _pr_writes(gh_calls) == [] and moves == []
    out, err = capsys.readouterr()
    assert err.splitlines()[-1] == (
        f"error: {UNDERIVED}, so which documents need a sentence cannot be told. Nothing was "
        "made ready, no reviewer requested and the issue not moved. Run review-work again once "
        "it can be run."
    )
    assert _refusals(err) == [] and "edit-pr" not in err
    assert "[ok]" not in out


def test_under_force_a_check_that_cannot_be_run_refuses_nothing(run_main, rw, capsys) -> None:
    """--force passes the refusal whole: a change check that cannot be run at the head
    stops nothing, and a warning says the sentences went unchecked (DEC-065 point 3).
    The reviewer of the answers still blocks a missing sentence."""
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=True),
        body=_described(),
        head=MOVED,
        derived=rw.friction_answers.Derivation(MOVED, problem="no answers were stood in"),
        extra=("--force",),
    )
    assert rc == 0
    assert [c[2] for c in _pr_writes(gh_calls)] == ["comment", "ready"]
    assert moves == ["review"]
    err = capsys.readouterr().err
    assert (
        f"  [warn] {UNDERIVED}; under --force, no sentence on what changed is checked, and the "
        "move goes on."
    ) in err.splitlines()
    assert _refusals(err) == []


def test_a_sentence_on_a_document_the_check_does_not_mark_updated_is_warned_of(
    run_main, rw, capsys
) -> None:
    """A sentence on a document the change check at the head does not mark updated is
    warned of, as open-pr and land-work warn of it, with the edit that removes it; it
    refuses nothing (DEC-065 point 3)."""
    said = f"{GUIDE}- `docs/api.md`: The page is still right.\n"
    rc, _gh_calls, moves = run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=True),
        body=_described(said),
        head=MOVED,
        derived=_derived(rw, _document("docs/guide.md"), at=MOVED),
    )
    assert rc == 0
    assert moves == ["review"]
    err = capsys.readouterr().err
    assert [ln for ln in err.splitlines() if "[warn]" in ln] == [
        "  [warn] docs/api.md has a sentence under `## What changed in each updated document`, "
        "and the change check at ccccccc does not mark it updated, so no reviewer checks the "
        f"sentence — remove it from the description with `edit-pr {PR_NUMBER} --body-file "
        "<file>`"
    ]


@pytest.mark.parametrize("draft", [True, False], ids=["draft-pr", "ready-pr"])
def test_a_description_that_cannot_be_read_stops_before_any_write(run_main, capsys, draft) -> None:
    """A failed read is never read as a description with no sentences, which could
    pass a ready PR and move the issue: the run stops at exit 3, saying what failed."""
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


def test_a_change_that_marks_no_document_updated_is_not_refused(run_main) -> None:
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
    body = _described(f"{SENTENCES}\n\n{item}\n")
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=True),
        body=body,
        derived=_derived(rw, _document("docs/guide.md")),
    )
    assert rc == 1
    assert _pr_writes(gh_calls) == [] and moves == []
    err = capsys.readouterr().err
    assert _refusals(err) == [_refusal("docs/guide.md")]
    line = body.split("\n").index(item) + 1
    assert (
        f"  - [warning] body.sentences: line {line} of the description, under `{SENTENCES}`, "
        f'is not read as a sentence: "{item}" — write it as "- `path`: sentence", starting in '
        "the line's first column, the document in a code span as the change check names it"
    ) in err.splitlines()


def test_force_takes_the_pr_to_review_past_the_refusal(run_main, rw, capsys) -> None:
    """--force overrides the refusal as it overrides every hard-reject (DEC-046)."""
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=True),
        body=_described(),
        derived=_derived(rw, _document("docs/guide.md")),
        extra=("--force",),
    )
    assert rc == 0
    assert [c[2] for c in _pr_writes(gh_calls)] == ["comment", "ready"]
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
    monkeypatch.setattr(
        rw.friction_answers,
        "checked",
        lambda head, base, *, source=None, from_checkout=True: _derived(
            rw, _document("docs/guide.md"), at=head
        ),
    )
    description = rw._Description(
        _described(), number=PR_NUMBER, head=LISTED, base="main", placed=False
    )
    monkeypatch.setattr(rw.head_programs, "build_commits", lambda *a: frozenset())
    sentences = rw._sentence_findings(description, rw._Move(42, CAP_ROOT, {}))
    assert sentences is not None
    findings = rw._ready_findings(description.body, {}, CAP_ROOT) + sentences
    assert rw._body_ok(findings, False, next_step=rw.FILL_FIRST) is False
    err = capsys.readouterr().err
    assert "  - [hard-reject] body.doc-impact: no Doc impact" in err.splitlines()
    assert _refusals(err) == [_refusal("docs/guide.md")]
    assert err.splitlines()[-1] == f"  → {rw.FILL_FIRST}; --force overrides."


# ---- the audit comment a --force leaves (DEC-046 point 2) -------------------------
#
# Where the PR exists, the comment lands before anything else the run writes, so the
# record survives a failed flip or move (DEC-049 point 2). The PR a run opens has no
# thread to comment on until then, so there it follows the opening.

#: The headline, as the schema's audit template renders it for the test's invoker.
HEADLINE = "Bypassed by me: `review-work --force` passed each refusal below"
#: A finding of the body validator, as a line of the audit comment names it.
NO_DOC_IMPACT = "- `[hard-reject] body.doc-impact: no Doc impact`"
#: A change check that could not be run at the head, as that comment names it.
STOP = f"- `[precondition] body.sentences: {UNDERIVED}`"


def _no_doc_impact(rw):
    return rw.pr_validation.Finding(
        rw.pr_validation.SEVERITY_HARD_REJECT, "body.doc-impact", "no Doc impact"
    )


def _audits(gh_calls: list[list[str]]) -> list[str]:
    """The body of each comment the run posted on the PR."""
    return [c[c.index("--body") + 1] for c in gh_calls if c[:3] == ["gh", "pr", "comment"]]


def _audited_line(refusal: str) -> str:
    """How the audit comment names a refusal: its own line in a code span, its
    backticks written as quotes."""
    line = refusal.removeprefix("  - ").replace("`", "'")
    return f"- `{line}`"


def _named(location: str) -> str:
    """How the audit comment names a document with no sentence."""
    return _audited_line(_refusal(location))


def _audited_refusals(audit: str) -> list[str]:
    return [line for line in audit.splitlines() if line.startswith("- ")]


@pytest.mark.parametrize("draft", [True, False], ids=["draft-pr", "ready-pr"])
def test_force_posts_one_comment_before_anything_else_it_writes(
    run_main, rw, capsys, draft
) -> None:
    """One comment for the run, however many refusals: it names who gave the override,
    the head, and each refusal, and comes before the PR is made ready, reviewers are
    requested and the issue moves."""
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=draft),
        body=_described(),
        derived=_derived(rw, _document("docs/guide.md", "docs/cli.md")),
        reviewer="@alice",
        extra=("--force",),
    )
    assert rc == 0 and moves == ["review"]
    assert [c[2] for c in _pr_writes(gh_calls)] == (
        ["comment", "ready", "edit"] if draft else ["comment", "edit"]
    )
    (audit,) = _audits(gh_calls)
    lines = audit.splitlines()
    assert lines[:2] == ["<!-- pkit-audit -->", f"{HEADLINE} at PR head {LISTED[:7]}."]
    assert _audited_refusals(audit) == [_named("docs/guide.md"), _named("docs/cli.md")]
    assert lines[-1].startswith("<!-- pkit-audit-key: review-work-force:")
    assert "--force audit comment posted" in capsys.readouterr().out


def test_force_on_a_pr_it_opens_comments_once_the_pr_exists(run_main, rw) -> None:
    """Nothing can be commented on before the PR is opened, so the comment follows the
    opening, ahead of the reviewers and the move. The head is not known here."""
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]),
        findings=(_no_doc_impact(rw),),
        reviewer="@alice",
        extra=("--force",),
    )
    assert rc == 0 and moves == ["review"]
    writes = _pr_writes(gh_calls)
    assert [c[2] for c in writes] == ["create", "comment", "edit"]
    assert writes[1][3] == str(PR_NUMBER)
    (audit,) = _audits(gh_calls)
    assert audit.splitlines()[1] == f"{HEADLINE}."
    assert _audited_refusals(audit) == [NO_DOC_IMPACT]


def test_the_comment_names_the_person_with_their_email(rw) -> None:
    """Who gave the override, in the template's form."""
    invoker = SimpleNamespace(github_login="alice", email="alice@example.com")
    body = rw._force_audit_body(["`a refusal`"], LISTED, "the-key", CAP_ROOT, invoker)
    assert body.splitlines()[1] == (
        "Bypassed by alice <alice@example.com>: `review-work --force` passed each refusal "
        f"below at PR head {LISTED[:7]}."
    )


@pytest.mark.parametrize("draft", [True, False], ids=["draft-pr", "ready-pr"])
def test_the_comment_names_a_change_check_that_could_not_be_run(run_main, rw, draft) -> None:
    """That stop is no finding and prints only a warning, yet --force passed it: exit 2
    without the flag. It shares the run's one comment with any other refusal."""
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=draft),
        body=_described(),
        head=MOVED,
        derived=rw.friction_answers.Derivation(MOVED, problem="no answers were stood in"),
        findings=(_no_doc_impact(rw),),
        extra=("--force",),
    )
    assert rc == 0 and moves == ["review"]
    (audit,) = _audits(gh_calls)
    assert _audited_refusals(audit) == ([NO_DOC_IMPACT, STOP] if draft else [STOP])


@pytest.mark.parametrize("draft", [True, False], ids=["draft-pr", "ready-pr"])
def test_a_check_that_cannot_be_run_hides_no_closing_reference_from_force(
    run_main, rw, capsys, draft
) -> None:
    """A closing reference is read from the description alone, so a change check that
    could not be run leaves it standing: --force passes both, the run prints the
    refusal, and its one comment names both."""
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=draft),
        body=_described(CLOSING),
        head=MOVED,
        derived=rw.friction_answers.Derivation(MOVED, problem="no answers were stood in"),
        extra=("--force",),
    )
    assert rc == 0 and moves == ["review"]
    err = capsys.readouterr().err
    assert _refusals(err) == [CLOSING_REFUSAL]
    assert err.splitlines()[-1] == "  → proceeding under --force."
    (audit,) = _audits(gh_calls)
    assert _audited_refusals(audit) == [STOP, _audited_line(CLOSING_REFUSAL)]


def test_a_warning_is_no_refusal_and_the_comment_leaves_it_out(run_main, rw, capsys) -> None:
    """--force passed the refusal, not the warning printed beside it."""
    body = _described(f"{SENTENCES}\n\n- **docs/guide.md:** The guide names the new flag.\n")
    _rc, gh_calls, _moves = run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=True),
        body=body,
        derived=_derived(rw, _document("docs/guide.md")),
        extra=("--force",),
    )
    assert "[warning]" in capsys.readouterr().err
    (audit,) = _audits(gh_calls)
    assert _audited_refusals(audit) == [_named("docs/guide.md")]


def test_force_with_nothing_to_pass_posts_no_comment(run_main, rw) -> None:
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=True),
        body=_described(GUIDE),
        derived=_derived(rw, _document("docs/guide.md")),
        extra=("--force",),
    )
    assert rc == 0 and moves == ["review"]
    assert [c[2] for c in _pr_writes(gh_calls)] == ["ready"]


def test_a_retry_of_the_override_posts_no_second_comment(run_main, rw, capsys) -> None:
    """A retry of a run whose move failed finds the comment on the PR. The same override
    after new commits is another act, and posts its own, even where the two heads read
    the same in the comment's short form."""
    forced = {
        "pr": _open_pr(draft=False),
        "body": _described(),
        "derived": _derived(rw, _document("docs/guide.md")),
        "extra": ("--force",),
    }
    _rc, gh_calls, _moves = run_main(_task(["state:in-progress"]), move_rc=1, **forced)
    (audit,) = _audits(gh_calls)
    capsys.readouterr()
    on_the_pr = ({"body": audit, "viewerDidAuthor": True, "includesCreatedEdit": False},)

    rc, gh_calls, moves = run_main(_task(["state:in-progress"]), comments=on_the_pr, **forced)
    assert rc == 0 and moves == ["review"]
    assert _audits(gh_calls) == []
    assert "--force audit comment already present; idempotent skip" in capsys.readouterr().out

    alike = LISTED[:7] + "c" * 33
    _rc, gh_calls, _moves = run_main(
        _task(["state:in-progress"]), comments=on_the_pr, head=alike, **forced
    )
    assert len(_audits(gh_calls)) == 1


#: A document's path as a head can name it. It clears a terminal, writes a line of its
#: own that reads as an event stamp, a marker the filing comment's reader finds anywhere
#: in the text, a mention, an image and a backtick that would end a code span, and it
#: holds a lone surrogate, which no string encodes.
HOSTILE = (
    "docs/\x1b[2Jevil\n<!-- pkit:audit v=1 event=claim id=x instance=9 -->\n"
    "<!-- pkit-provenance:filing --> @alice ![x](https://e.example/y.png) ` \u202e\ud800.md"
)


def _assert_inert(audit: str) -> None:
    """Nothing in `audit` acts on a reader, a person's or a reader of comments."""
    assert not any(char in audit for char in ("\x1b", "\u202e", "\ud800"))
    assert audit.count("<!--") == 2  # its marker and its key, and no other
    lines = audit.splitlines()
    assert len(lines) == len(audit.split("\n"))  # no second kind of line break
    for line in _audited_refusals(audit):
        assert line.startswith("- `") and line.endswith("`") and line.count("`") == 2
    assert sys.modules["_lib.audit_log"].parse(audit) is None


def _assert_escaped(err: str) -> None:
    """Nothing the head holds reached the terminal to act on it."""
    assert "\x1b" not in err and "\u202e" not in err and "\ud800" not in err
    assert "\\x1b[2Jevil\\n<!-- pkit:audit" in err
    assert not any(line.startswith("<!--") for line in err.splitlines())


@pytest.mark.parametrize("draft", [True, False], ids=["draft-pr", "ready-pr"])
def test_a_path_a_head_controls_stays_inert(run_main, rw, capsys, draft) -> None:
    """The same text in the same run, as a refusal names it to a terminal and as the
    audit comment quotes it."""
    rc, gh_calls, _moves = run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=draft),
        body=_described(),
        derived=_derived(rw, _document(HOSTILE)),
        extra=("--force",),
    )
    assert rc == 0
    _assert_escaped(capsys.readouterr().err)
    (audit,) = _audits(gh_calls)
    _assert_inert(audit)
    assert "\\x1b[2Jevil\\n\\x3c!-- pkit:audit" in audit


@pytest.mark.parametrize("force", [True, False], ids=["forced", "refused"])
def test_what_the_check_said_at_a_head_stays_inert(run_main, rw, capsys, force) -> None:
    """The problem carries the last line the check printed, run against the head: it
    is escaped in the warning, in the stop and in the comment."""
    rc, gh_calls, _moves = run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=True),
        body=_described(),
        derived=rw.friction_answers.Derivation(LISTED, problem=HOSTILE),
        extra=("--force",) if force else (),
    )
    assert rc == (0 if force else rw.EXIT_UNDERIVED)
    _assert_escaped(capsys.readouterr().err)
    assert len(_audits(gh_calls)) == (1 if force else 0)
    for audit in _audits(gh_calls):
        _assert_inert(audit)


@pytest.mark.parametrize("check_ran", [True, False], ids=["check-ran", "check-could-not-run"])
def test_a_refusal_quoting_a_description_stays_inert(run_main, rw, capsys, check_ran) -> None:
    """A closing reference's refusal names the sentence's document as the description
    writes it, the one finding that reaches the refusal and the comment unescaped. It
    stands whether or not the change check could be run."""
    said = f"{SENTENCES}\n\n- `docs/\x1b[2Jevil<!-- x -->.md`: This fixed #77 in the guide.\n"
    not_run = rw.friction_answers.Derivation(LISTED, problem="no answers were stood in")
    rc, gh_calls, _moves = run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=True),
        body=_described(said),
        derived=None if check_ran else not_run,
        extra=("--force",),
    )
    assert rc == 0
    err = capsys.readouterr().err
    assert "\x1b" not in err
    assert "what changed in docs/\\x1b[2Jevil<!-- x -->.md, under" in err
    (audit,) = _audits(gh_calls)
    _assert_inert(audit)
    assert "docs/\\x1b[2Jevil\\x3c!-- x -->.md" in audit


def test_a_sentence_on_a_document_a_head_names_warns_inertly(run_main, rw, capsys) -> None:
    """A sentence's document is the description's text, in the warning that it goes
    unchecked as much as in a refusal."""
    said = f"{SENTENCES}\n\n- `docs/\x1b[2Jevil.md`: Still right.\n"
    run_main(_task(["state:in-progress"]), pr=_open_pr(draft=True), body=_described(said))
    err = capsys.readouterr().err
    assert "\x1b" not in err and "docs/\\x1b[2Jevil.md has a sentence" in err


@pytest.mark.parametrize("draft", [True, False], ids=["draft-pr", "ready-pr"])
def test_a_comment_that_cannot_be_posted_stops_before_any_other_write(
    run_main, rw, capsys, draft
) -> None:
    """The comment is the override's record, so nothing goes on without it, and a second
    run posts it: nothing was made ready, no reviewer requested and the issue not moved."""
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=draft),
        body=_described(),
        derived=_derived(rw, _document("docs/guide.md")),
        reviewer="@alice",
        comment_rc=1,
        extra=("--force",),
    )
    assert rc == 3
    assert [c[2] for c in _pr_writes(gh_calls)] == ["comment"]
    assert moves == []
    assert capsys.readouterr().err.splitlines()[-1] == (
        f"error: the audit comment of this --force could not be posted on PR #{PR_NUMBER}; "
        "nothing was made ready, no reviewer requested and the issue not moved. Run "
        "review-work --force again once it can be posted."
    )


def test_a_comment_that_cannot_be_posted_on_an_opened_pr_names_it(run_main, rw, capsys) -> None:
    """The PR stands, and a second run would find it ready and read none of those
    findings, so the failure says what to do instead of running again."""
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]),
        findings=(_no_doc_impact(rw),),
        reviewer="@alice",
        comment_rc=1,
        extra=("--force",),
    )
    assert rc == 3
    assert [c[2] for c in _pr_writes(gh_calls)] == ["create", "comment"]
    assert moves == []
    assert capsys.readouterr().err.splitlines()[-1] == (
        f"error: the audit comment of this --force could not be posted on PR #{PR_NUMBER} "
        f"({PR_URL}), opened ready for review; no reviewer was requested and the issue not "
        "moved. A second run would not read those findings again, since the PR is ready: undo "
        f"it with `gh pr close {PR_NUMBER}` and run again, or say on the PR what --force passed."
    )


def test_a_project_that_projects_no_comments_gets_none(run_main, rw, capsys) -> None:
    """`audit.projection: off` posts no audit comments (DEC-049 point 2), so the override
    shows in the output only."""
    rc, gh_calls, moves = run_main(
        _task(["state:in-progress"]),
        pr=_open_pr(draft=True),
        body=_described(),
        derived=_derived(rw, _document("docs/guide.md")),
        config={"audit": {"projection": "off"}},
        extra=("--force",),
    )
    assert rc == 0 and moves == ["review"]
    assert [c[2] for c in _pr_writes(gh_calls)] == ["ready"]
    assert capsys.readouterr().err.splitlines()[-1] == "  → proceeding under --force."
