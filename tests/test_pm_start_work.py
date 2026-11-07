"""Tests for `start-work` wrapper (DEC-026)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from tests.pm_composed_move_support import FakeEngine, MoveIssueInProcess, status_at
from tests.pm_ownership_support import FakeGitHub, clone_with, topology_with

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts" / "start-work.py"


@pytest.fixture(scope="module")
def sw():
    lib_dir = SCRIPT.parent
    sys.path.insert(0, str(lib_dir))
    spec = importlib.util.spec_from_file_location("pm_start_work_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_start_work_under_test"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(lib_dir))


# ---- _slug_from_title --------------------------------------------------


def test_slug_strips_type_prefix(sw) -> None:
    assert sw._slug_from_title("[Feature] add gh helper") == "add-gh-helper"


def test_slug_strips_punctuation(sw) -> None:
    assert sw._slug_from_title("[Bug] fix: hostname mismatch!") == "fix-hostname-mismatch"


def test_slug_caps_at_five_words(sw) -> None:
    assert (
        sw._slug_from_title("[Feature] one two three four five six seven")
        == "one-two-three-four-five"
    )


def test_slug_handles_empty_after_prefix(sw) -> None:
    assert sw._slug_from_title("[EPIC]") == "untitled"


def test_slug_lowercases(sw) -> None:
    assert sw._slug_from_title("[Task] MIXED Case Title") == "mixed-case-title"


# ---- _derive_branch_prefix ---------------------------------------------
#
# The prefix now resolves the kit type *value* through the ADR-026 read seam
# (a `type:*` label OR a `[Prefix]` title) and maps it via classification.yaml's
# `pr_type_mapping`. The greenfield (label) arm below must stay byte-identical to
# the pre-fix behaviour; the brownfield (title-prefix) arm is the new coverage.

# A minimal classification carrying the two tables the derivation reads: the
# value→conv-type bridge (`pr_type_mapping`) and the title-prefix vocabulary
# (`title_prefix_by_value`). Mirrors the shipped classification.yaml.
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


def test_branch_prefix_feature(sw) -> None:
    assert (
        sw._derive_branch_prefix(
            ["type:feature", "priority:Medium"], "[Task] add x", _CLASSIFICATION, None
        )
        == "feat"
    )


def test_branch_prefix_bug(sw) -> None:
    assert sw._derive_branch_prefix(["type:bug"], "[Bug] fix x", _CLASSIFICATION, None) == "fix"


def test_branch_prefix_docs(sw) -> None:
    assert (
        sw._derive_branch_prefix(
            ["workstream:cli", "type:docs"], "[Docs] doc x", _CLASSIFICATION, None
        )
        == "docs"
    )


def test_branch_prefix_missing_returns_none(sw) -> None:
    # No type:* label AND no recognised [Prefix] title ⇒ underivable.
    assert (
        sw._derive_branch_prefix(["priority:High"], "no bracket prefix", _CLASSIFICATION, None)
        is None
    )
    assert sw._derive_branch_prefix([], "", _CLASSIFICATION, None) is None


def test_branch_prefix_picks_first_match(sw) -> None:
    """Defensive: if labels somehow have both type:bug and type:feature, take the first."""
    result = sw._derive_branch_prefix(
        ["type:bug", "type:feature"], "[Bug] x", _CLASSIFICATION, None
    )
    # Order-dependent — accept either as long as it's recognised
    assert result in ("fix", "feat")


# ---- brownfield title-prefix arm (Task #442) ---------------------------


def test_branch_prefix_brownfield_bug_title_no_label(sw) -> None:
    """A brownfield `[Bug]`-titled Task with NO type:* label resolves `fix` —
    the read routes through the title-prefix arm of the seam, not a raw label."""
    assert sw._derive_branch_prefix([], "[Bug] hostname mismatch", _CLASSIFICATION, None) == "fix"


def test_branch_prefix_greenfield_label_still_wins(sw) -> None:
    """Greenfield stays byte-identical: `type:bug` label resolves `fix` even
    when the title carries a different (or no) bracket prefix."""
    assert (
        sw._derive_branch_prefix(["type:bug"], "no bracket prefix at all", _CLASSIFICATION, None)
        == "fix"
    )


# ---- adopter label-remap arm (#910) ------------------------------------


def _type_remap_map(module):
    """A substrate map binding `type` to the adopter's own `kind/*` labels."""
    return module.axis_labels.SubstrateMap(
        axes={"type": {"label": {"remap": {"bug": "kind/bug", "docs": "kind/docs"}}}}
    )


def test_branch_prefix_reads_a_remapped_type_label(sw) -> None:
    """The adopter's `kind/bug` label is their type substrate: it resolves `fix`
    through the map, where the bare `type:` prefix scan found nothing (#910)."""
    assert (
        sw._derive_branch_prefix(
            ["kind/bug"], "no bracket prefix", _CLASSIFICATION, _type_remap_map(sw)
        )
        == "fix"
    )


def test_branch_prefix_ignores_kit_type_label_under_a_remap(sw) -> None:
    """Under a `type` label remap the kit's `type:*` labels are not the
    substrate, so a leftover `type:docs` does not decide the prefix."""
    assert (
        sw._derive_branch_prefix(
            ["type:docs", "kind/bug"],
            "no bracket prefix",
            _CLASSIFICATION,
            _type_remap_map(sw),
        )
        == "fix"
    )


# ---- the branch shape, read through the shared reading (#1608) ---------


def _branch_of(sw, monkeypatch, name: str, issue: int) -> str | None:
    """The issue's branch when `name` is the clone's only local branch."""
    monkeypatch.setattr(sw.issue_branch, "_local_branches", lambda: (name,))
    return sw.issue_branch.read(issue, {}).branch


def test_branch_matches_shape_valid(sw, monkeypatch) -> None:
    assert _branch_of(sw, monkeypatch, "feat/42-add-gh-helper", 42) == "feat/42-add-gh-helper"
    assert _branch_of(sw, monkeypatch, "fix/177-membership-hostname", 177) is not None
    assert _branch_of(sw, monkeypatch, "docs/29-branch-naming", 29) is not None


def test_branch_matches_shape_wrong_number(sw, monkeypatch) -> None:
    assert _branch_of(sw, monkeypatch, "feat/42-foo", 99) is None


def test_branch_matches_shape_no_slug(sw, monkeypatch) -> None:
    assert _branch_of(sw, monkeypatch, "feat/42", 42) is None


def test_branch_matches_shape_uppercase_rejected(sw, monkeypatch) -> None:
    assert _branch_of(sw, monkeypatch, "Feat/42-foo", 42) is None


# ---- type coverage against the REAL shipped classification.yaml -------


def test_every_shipped_type_value_resolves_a_branch_prefix(sw) -> None:
    """Every kind in the real classification.yaml (both label and title arms)
    resolves a branch prefix — no shipped type value is left underivable.

    Reads the shipped schema rather than a fixture so the two tables the
    derivation depends on (`pr_type_mapping`, `title_prefix_by_value`) can't
    drift out of coverage silently."""
    import importlib.util as _ilu

    scripts = SCRIPT.parent
    spec = _ilu.spec_from_file_location(
        "pm_classification_rules_under_test", scripts / "_lib" / "classification_rules.py"
    )
    assert spec is not None and spec.loader is not None
    cr = _ilu.module_from_spec(spec)
    spec.loader.exec_module(cr)

    from ruamel.yaml import YAML

    classification = YAML(typ="safe").load(
        (scripts.parent / "schemas" / "classification.yaml").read_text(encoding="utf-8")
    )
    prefix_by_value = cr.title_prefix_by_value(classification)
    assert prefix_by_value, "shipped classification.yaml carries no title_prefix_by_value"

    for value, title_prefix in prefix_by_value.items():
        # Label arm: a greenfield type:<value> label resolves a prefix.
        via_label = sw._derive_branch_prefix(
            [f"type:{value}"], f"[{title_prefix}] x", classification, None
        )
        assert via_label is not None, f"no branch prefix for label type:{value}"
        # Title arm: the same value resolves identically off the [Prefix] title
        # with no type:* label present (the brownfield path).
        via_title = sw._derive_branch_prefix([], f"[{title_prefix}] x", classification, None)
        assert via_title == via_label, (
            f"label vs title-prefix arm disagree for kind {value!r}: {via_label!r} vs {via_title!r}"
        )


# ---- resolve_base_branch (#835, #903) ----------------------------------
#
# The shared resolver in `_lib/lifecycle_inference`; start-work and the
# PR-opening verbs all call it. End-to-end wiring per verb lives in
# test_pm_pr_base_branch.py.


@pytest.fixture
def backbone(sw: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Stand in for the backbone's reading (`pkit repository base --json`): `answer(name,
    declared=False)` makes it name `name` as the default branch."""
    lib = sw.infer.default_branch

    def answer(name: str, declared: bool = False) -> None:
        monkeypatch.setattr(lib, "_read", {})
        monkeypatch.setattr(lib, "_warned", set[str]())

        def ask(explicit: str | None, _run: Any) -> Any:
            branch = lib.Branch(name, declared, f"origin/{name}", "c0ffee", None)
            base = lib.Base(f"origin/{explicit or name}", "c0ffee", "c0ffee", None)
            return lib.Reading(branch, base)

        monkeypatch.setattr(lib, "_ask", ask)

    answer("main")
    return answer


def test_base_defaults_to_the_backbone_s_default_branch(sw: Any, backbone: Any) -> None:
    backbone("trunk", declared=True)
    assert sw.infer.resolve_base_branch({}, "EPIC: #1\n\n## What\nx") == "trunk"


def test_base_defaults_to_main_when_nothing_is_declared(sw: Any, backbone: Any) -> None:
    assert sw.infer.resolve_base_branch({}, "EPIC: #1\n\n## What\nx") == "main"


def test_pm_s_old_key_names_the_branch_only_until_the_upgrade(
    sw: Any, backbone: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Not yet migrated (0.55.0): a value other than the backbone's names the branch while
    the backbone declares none, with a warning; a declared value always wins."""
    assert sw.infer.resolve_base_branch({"default_branch": "trunk"}, "EPIC: #1") == "trunk"
    assert "until the upgrade carries it over" in capsys.readouterr().err
    backbone("develop", declared=True)
    assert sw.infer.resolve_base_branch({"default_branch": "trunk"}, "EPIC: #1") == "develop"


def test_base_is_integration_branch_when_marked(sw: Any, backbone: Any) -> None:
    body = "Integration: integration/508-multi-instance-ownership\nFeature: #510\n\n## What\nx"
    assert sw.infer.resolve_base_branch({"default_branch": "main"}, body) == (
        "integration/508-multi-instance-ownership"
    )


def test_base_ignores_a_malformed_marker(sw: Any, backbone: Any) -> None:
    # A malformed marker is not a valid integration branch — fall back to default.
    body = "Integration: integration/Bad_Slug!!\nFeature: #510\n\n## What\nx"
    assert sw.infer.resolve_base_branch({"default_branch": "main"}, body) == "main"


def test_explicit_base_wins_over_marker_and_default(sw: Any, backbone: Any) -> None:
    body = "Integration: integration/508-multi-instance-ownership\nFeature: #510\n"
    assert (
        sw.infer.resolve_base_branch({"default_branch": "trunk"}, body, explicit="release/2")
        == "release/2"
    )


def test_base_never_reflects_the_checked_out_branch(sw) -> None:
    # The resolver takes only (config, body, explicit) — there is no HEAD input,
    # so the currently-checked-out branch can never leak into the base (#835).
    import inspect

    sig = inspect.signature(sw.infer.resolve_base_branch)
    assert list(sig.parameters) == ["config", "body", "explicit"]


# ---- transition gate + late failure (#942) -----------------------------
#
# Drive the real `main()` with its gates and gh/git seams stubbed, against the
# shipped workflow.yaml / issue-types.yaml, and record every mutation.

CAP_ROOT = SCRIPT.parent.parent
# The variable an earlier revision of #1242 handed the engine's answer down in.
HAND_DOWN_ENV = "PKIT_PM_ISSUE_STATUS"


def _task(labels: list[str], *, assignees: list[dict] | None = None) -> dict:
    return {
        "title": "[Task] do the thing",
        "labels": labels,
        "assignees": assignees or [],
        "state": "OPEN",
        "body": "Feature: #1\n\n## What\nx",
        "milestone": None,
    }


# ---- _create_branch: cut from the commit the backbone resolves (COR-054) ----


def _git(cwd: Path, *args: str) -> str:
    import subprocess

    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def clone_ahead(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, pkit_on_path: Path) -> Path:
    """A clone of `origin` whose local `main` carries a commit nobody pushed."""
    source = tmp_path / "source"
    source.mkdir()
    _git(source, "init", "-q", "-b", "main")
    _git(source, "commit", "-q", "--allow-empty", "-m", "shared")
    work = tmp_path / "work"
    _git(tmp_path, "clone", "-q", str(source), str(work))
    _git(work, "commit", "-q", "--allow-empty", "-m", "local only")
    monkeypatch.chdir(work)
    return work


def test_start_work_cuts_from_the_remote_s_copy_not_a_local_branch_ahead(
    sw: Any, clone_ahead: Path
) -> None:
    shared = _git(clone_ahead, "rev-parse", "origin/main")
    assert shared != _git(clone_ahead, "rev-parse", "main")
    assert sw._create_branch("fix/42-thing", "main")
    assert _git(clone_ahead, "rev-parse", "fix/42-thing") == shared


def test_start_work_refuses_a_base_that_resolves_nowhere(
    sw: Any, clone_ahead: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`origin` holds no `integration/absent` and the fetch fails: no branch is cut from a
    guess — not from the local branch, not from HEAD."""
    assert not sw._create_branch("fix/42-thing", "integration/absent")
    err = capsys.readouterr().err
    assert "cannot cut 'fix/42-thing' from 'integration/absent'" in err
    assert "git fetch origin integration/absent" in err
    assert "fix/42-thing" not in _git(clone_ahead, "branch", "--list")


@pytest.fixture
def run_main(sw: Any, monkeypatch: pytest.MonkeyPatch, backbone: Any) -> Any:
    """Returns `run(issue, move_rc=0, engine=None, config=None, move=None,
    dry_run=False, instance=None, github=None, extra=()) -> (rc, mutations)`
    over stubbed seams. `engine` is the process engine, a `FakeEngine` (by
    default one that gives no answer); `config` adds to the adopter config.
    `move` runs the composed move-issue in process; without it the move is
    recorded and answers `move_rc`, and a clash-guard bypass it is handed is
    recorded as `("move-bypass", <reason>)`. `instance` is this clone's instance
    id (none by default), and `github` the in-memory GitHub its ownership calls
    reach; each ownership write is recorded as `("ownership", <gh verb>)`.
    `extra` adds to the command line."""
    from types import SimpleNamespace

    def run(
        issue: dict,
        move_rc: int = 0,
        engine: FakeEngine | None = None,
        config: dict | None = None,
        move: MoveIssueInProcess | None = None,
        dry_run: bool = False,
        instance: int | None = None,
        github: FakeGitHub | None = None,
        extra: tuple[str, ...] = (),
    ):
        mutations: list[tuple] = []
        fake = github if github is not None else FakeGitHub()

        def ownership_gh(args: list[str], _config: dict) -> Any:
            if args[1:3] != ["issue", "view"]:
                mutations.append(("ownership", args[2]))
            return fake(args)

        clone_with(sw.instance_claims, monkeypatch, instance)
        monkeypatch.setattr(sw.instance_claims, "_gh", ownership_gh)
        argv = ["start-work", "42", "--yes", *(["--dry-run"] if dry_run else []), *extra]
        monkeypatch.setattr(sys, "argv", argv)
        monkeypatch.setattr(sw, "resolve_capability_root", lambda _e: CAP_ROOT)
        monkeypatch.setattr(sw.bootstrap_gate, "enforce", lambda *a, **k: True)
        monkeypatch.setattr(sw.session_guard, "enforce", lambda **k: True)
        monkeypatch.setattr(
            sw, "load_adopter_config", lambda _r: {"default_branch": "main", **(config or {})}
        )
        (engine or FakeEngine()).install(monkeypatch)
        monkeypatch.setattr(sw, "_read_members", lambda *a: [])
        monkeypatch.setattr(
            sw, "resolve_invoker_identity", lambda **k: SimpleNamespace(github_login="me")
        )
        monkeypatch.setattr(sw, "check_membership", lambda *a: SimpleNamespace(allowed=True))
        monkeypatch.setattr(sw.axis_labels, "load_substrate_map", lambda _r: None)
        monkeypatch.setattr(sw, "_gh_get_issue", lambda _n, _c: issue)
        monkeypatch.setattr(sw.issue_branch, "_local_branches", lambda: ())

        def create_branch(name, base):
            mutations.append(("branch", name))
            return True

        def set_assignee(n, login, config):
            mutations.append(("assignee", login))
            held = fake.issues.get(n)
            if held is not None and login not in held.assignees:
                held.assignees.append(login)  # as GitHub holds the issue after the write
            return True

        def move_issue(n, target, **kw):
            mutations.append(("move", target))
            if kw.get("bypass_owner"):
                mutations.append(("move-bypass", kw["bypass_owner"]))
            return move_rc

        monkeypatch.setattr(sw, "_create_branch", create_branch)
        monkeypatch.setattr(sw, "_set_assignee", set_assignee)
        if move is None:
            monkeypatch.setattr(sw.composed_move, "invoke_move_issue", move_issue)
        else:
            monkeypatch.setattr(sw.composed_move, "subprocess", SimpleNamespace(run=move.run))
        return sw.main(), mutations

    return run


def test_refuses_from_todo_before_any_mutation(run_main, capsys) -> None:
    rc, mutations = run_main(_task(["type:bug", "state:todo"]))
    assert rc == 2
    assert mutations == []  # no branch, no assignee, no move
    err = capsys.readouterr().err
    assert "'todo'" in err
    assert "move-issue 42 --to backlog" in err


def test_refuses_from_todo_inferred_without_a_state_label(run_main, capsys) -> None:
    # No state:* label and no milestone resolves Todo through the shared reader.
    rc, mutations = run_main(_task(["type:bug"]))
    assert rc == 2
    assert mutations == []
    assert "move-issue 42 --to backlog" in capsys.readouterr().err


def test_proceeds_from_backlog(run_main) -> None:
    rc, mutations = run_main(_task(["type:bug", "state:backlog"]))
    assert rc == 0
    assert mutations == [
        ("branch", "fix/42-do-the-thing"),
        ("assignee", "me"),
        ("move", "in-progress"),
    ]


def test_proceeds_when_already_in_progress(run_main) -> None:
    # move-issue treats in-progress → in-progress as an idempotent no-op.
    rc, mutations = run_main(_task(["type:bug", "state:in-progress"]))
    assert rc == 0
    assert ("move", "in-progress") in mutations


def test_refusal_without_a_stepping_stone_lists_legal_targets(run_main, capsys) -> None:
    rc, mutations = run_main(_task(["type:bug", "state:review"]))
    assert rc == 2
    assert mutations == []
    assert "legal targets from 'review'" in capsys.readouterr().err


def test_late_move_failure_names_branch_and_assignee(run_main, capsys) -> None:
    rc, mutations = run_main(_task(["type:bug", "state:backlog"]), move_rc=3)
    assert rc == 3  # move-issue's exit code passes through
    assert [m[0] for m in mutations] == ["branch", "assignee", "move"]
    err = capsys.readouterr().err
    last_block = err[err.rindex("[failed]") :]
    assert "the issue did not move" in last_block
    assert "fix/42-do-the-thing" in last_block
    assert "@me" in last_block


def test_late_move_failure_omits_an_assignee_it_did_not_write(run_main, capsys) -> None:
    issue = _task(["type:bug", "state:backlog"], assignees=[{"login": "me"}])
    rc, mutations = run_main(issue, move_rc=3)
    assert rc == 3
    assert ("assignee", "me") not in mutations
    err = capsys.readouterr().err
    assert "fix/42-do-the-thing" in err
    assert "@me" not in err


# ---- the early check reads the issue's own fields (#1242) --------------
#
# start-work's early check reads the state from the labels and milestone of
# the issue it fetched (`_lib/issue_position`, shared with review-work), and
# starts no `pkit process` run: the engine's detectors read those same fields.
# move-issue reads the state itself when it moves. Each test's engine would
# answer otherwise than the labels, so a run that asked it would show.


def test_a_refused_check_asks_no_engine(run_main, capsys) -> None:
    engine = FakeEngine(status_at("backlog"))
    rc, mutations = run_main(_task(["type:bug", "state:todo"]), engine=engine)
    assert rc == 2
    assert mutations == []
    assert engine.asks == []
    assert "the issue is in 'todo'" in capsys.readouterr().err


def test_a_dry_run_asks_no_engine(run_main, capsys) -> None:
    engine = FakeEngine(status_at("todo"))
    rc, mutations = run_main(_task(["type:bug", "state:backlog"]), engine=engine, dry_run=True)
    assert rc == 0
    assert mutations == []
    assert engine.asks == []
    assert "(dry-run: would create branch off main" in capsys.readouterr().out


def test_a_legal_move_asks_no_engine_before_the_move(run_main) -> None:
    engine = FakeEngine(status_at("todo"))
    rc, mutations = run_main(_task(["type:bug", "state:backlog"]), engine=engine)
    assert rc == 0
    assert [m[0] for m in mutations] == ["branch", "assignee", "move"]
    assert engine.asks == []


def test_a_board_carried_state_is_read_off_the_labels_as_before(run_main) -> None:
    # Where the board carries state and the engine gives nothing, the check
    # reads the labels, as it did before #1242; nothing is newly refused.
    board = {"has_projects_v2_board": True}
    rc, mutations = run_main(_task(["type:bug", "state:backlog"]), config=board)
    assert rc == 0
    assert [m[0] for m in mutations] == ["branch", "assignee", "move"]


def test_a_state_changed_after_the_check_is_refused_by_move_issue(
    run_main, monkeypatch, capsys
) -> None:
    """The check reads Backlog; by the time move-issue reads, the issue is back
    in Todo. move-issue refuses Todo → In Progress, and start-work ends on what
    it left behind."""
    todo = _task(["type:bug", "state:todo"])
    engine = FakeEngine(status_at("todo"))
    move = MoveIssueInProcess(monkeypatch, todo)
    rc, mutations = run_main(_task(["type:bug", "state:backlog"]), engine=engine, move=move)
    assert rc == 2
    assert [m[0] for m in mutations] == ["branch", "assignee"]
    assert len(move.runs) == 1
    assert len(engine.asks) == 1  # move-issue's own read, at move time
    err = capsys.readouterr().err
    assert "no transition 'todo' → 'in-progress'" in err
    last_block = err[err.rindex("[failed]") :]
    assert last_block.startswith(
        "[failed] start-work #42: move-issue --to in-progress failed (exit 2); "
        "the issue did not move."
    )
    assert "branch 'fix/42-do-the-thing' (created and checked out)" in last_block
    assert "assignee @me" in last_block


def test_a_value_in_the_environment_does_not_stand_in_for_the_labels(
    run_main, monkeypatch, capsys
) -> None:
    # A value saying Backlog, from which the check would pass; the labels say Todo.
    monkeypatch.setenv(HAND_DOWN_ENV, json.dumps({"issue": 42, "status": status_at("backlog")}))
    rc, mutations = run_main(_task(["type:bug", "state:todo"]))
    assert rc == 2
    assert mutations == []
    assert "the issue is in 'todo'" in capsys.readouterr().err


# ---- instance ownership: the commons claim (DEC-035 points 3 and 6) -----------
#
# With an instance id set, start-work claims an issue no instance owns once the
# assignee is set, ahead of the move. The in-memory GitHub holds issue #42 with
# the assignee the run writes, as GitHub would after it.


def _assigned_42() -> FakeGitHub:
    github = FakeGitHub()
    github.add(42, assignees=("me",))
    return github


def _stamp(sw, event: str, instance: int) -> str:
    return sw.instance_claims.ownership.format_event_comment(event=event, instance=instance)


def test_with_no_instance_id_start_work_is_unchanged(run_main, capsys) -> None:
    github = _assigned_42()
    rc, mutations = run_main(_task(["type:bug", "state:backlog"]), github=github)
    assert rc == 0
    assert mutations == [
        ("branch", "fix/42-do-the-thing"),
        ("assignee", "me"),
        ("move", "in-progress"),
    ]
    assert github.calls == []
    captured = capsys.readouterr()
    assert "ownership" not in captured.out + captured.err


def test_claims_an_unowned_issue_before_the_move(run_main, capsys) -> None:
    github = _assigned_42()
    rc, mutations = run_main(_task(["type:bug", "state:backlog"]), instance=2, github=github)
    assert rc == 0
    assert mutations == [
        ("branch", "fix/42-do-the-thing"),
        ("assignee", "me"),
        ("ownership", "comment"),
        ("ownership", "edit"),
        ("move", "in-progress"),
    ]
    out = capsys.readouterr().out
    assert (
        "  ownership: claimed for instance 2 (comment substrate), where no instance owns it" in out
    )
    assert "[ok] ownership: #42 claimed for instance 2 (comment substrate)." in out


def test_the_clash_guard_refuses_an_issue_another_instance_owns(run_main, sw, capsys) -> None:
    """DEC-035 point 6: refused before any branch, assignee or move."""
    github = _assigned_42()
    github.post(42, _stamp(sw, "claim", 3))
    rc, mutations = run_main(_task(["type:bug", "state:backlog"]), instance=2, github=github)
    assert rc == 2
    assert mutations == []
    err = capsys.readouterr().err
    assert (
        "[refused] start-work #42: #42 is owned by instance 3, and this clone is instance 2" in err
    )
    assert 'pass --bypass "<reason>"' in err


def test_a_bypass_posts_its_reason_and_starts_the_work_unclaimed(run_main, sw, capsys) -> None:
    """The audit comment comes first, the issue stays the other instance's, and
    the composed move is handed the same reason, so it posts no second comment."""
    github = _assigned_42()
    github.post(42, _stamp(sw, "claim", 3))
    rc, mutations = run_main(
        _task(["type:bug", "state:backlog"]),
        instance=2,
        github=github,
        extra=("--bypass", "instance 3's session is gone"),
    )
    assert rc == 0
    assert mutations == [
        ("ownership", "comment"),
        ("branch", "fix/42-do-the-thing"),
        ("assignee", "me"),
        ("move", "in-progress"),
        ("move-bypass", "instance 3's session is gone"),
    ]
    audit = github.issues[42].comments[-1]["body"]
    assert audit.startswith("<!-- pkit-audit -->")
    assert "Bypassed by me: instance 3's session is gone" in audit
    assert "<!-- pkit-audit-key: ownership-guard:" in audit
    captured = capsys.readouterr()
    assert "--bypass let this clone, instance 2, act on it" in captured.err
    assert "  ownership: not claimed, since --bypass starts the work unclaimed" in captured.out
    assert "[note] ownership: #42 is not claimed: --bypass starts the work unclaimed." in (
        captured.out
    )


def test_a_bypass_of_another_accounts_claim_writes_no_claim(run_main, sw, capsys) -> None:
    """@alice took the issue after start-work's own read, and her instance 1
    claimed it. The run adds this clone's account as a second assignee, yet the
    bypass still starts the work unclaimed. No claim of this clone is written,
    and @alice's markers still name instance 1 as the owner."""
    github = FakeGitHub()
    github.add(42, assignees=("alice",))
    github.post(42, _stamp(sw, "claim", 1), author="alice")
    rc, mutations = run_main(
        _task(["type:bug", "state:backlog"]),
        instance=2,
        github=github,
        extra=("--bypass", "alice's session is gone"),
    )
    assert rc == 0
    assert mutations == [
        ("ownership", "comment"),
        ("branch", "fix/42-do-the-thing"),
        ("assignee", "me"),
        ("move", "in-progress"),
        ("move-bypass", "alice's session is gone"),
    ]
    assert github.issues[42].assignees == ["alice", "me"]
    ownership = sw.instance_claims.ownership
    comments = github.issues[42].comments
    mine = ownership.resolve_owner(comments=comments, labels=[], assignee_login="me")
    theirs = ownership.resolve_owner(comments=comments, labels=[], assignee_login="alice")
    assert mine.owners == frozenset()
    assert theirs.owners == frozenset({1})
    assert "#42 is not claimed: --bypass starts the work unclaimed." in capsys.readouterr().out


def test_the_composed_move_finds_the_bypass_posted(run_main, sw, monkeypatch, capsys) -> None:
    """move-issue's own guard is handed the reason, finds the audit comment it
    would post, and posts no second one."""
    github = _assigned_42()
    github.post(42, _stamp(sw, "claim", 3))
    from types import SimpleNamespace

    at_move = {**_task(["type:bug", "state:in-progress"]), "body": "## What\nx"}
    move = MoveIssueInProcess(monkeypatch, at_move)
    # The child runs as the same person as start-work, as a real child does.
    me = SimpleNamespace(github_login="me")
    monkeypatch.setattr(move.module, "resolve_invoker_identity", lambda config=None: me)
    rc, _mutations = run_main(
        _task(["type:bug", "state:backlog"]),
        engine=FakeEngine(status_at("in-progress")),
        move=move,
        instance=2,
        github=github,
        extra=("--bypass", "instance 3's session is gone"),
    )
    assert rc == 0
    assert move.runs[0][-2:] == ["--bypass-owner", "instance 3's session is gone"]
    audits = [c for c in github.issues[42].comments if "pkit-audit-key" in c["body"]]
    assert len(audits) == 1
    assert "audit comment already present; idempotent skip" in capsys.readouterr().out


def test_a_dry_run_bypass_posts_nothing(run_main, sw, capsys) -> None:
    github = _assigned_42()
    github.post(42, _stamp(sw, "claim", 3))
    rc, mutations = run_main(
        _task(["type:bug", "state:backlog"]),
        dry_run=True,
        instance=2,
        github=github,
        extra=("--bypass", "why"),
    )
    assert rc == 0
    assert mutations == []
    assert github.writes() == []
    assert "--bypass would post an audit comment first" in capsys.readouterr().out


def test_a_lost_same_instant_claim_stops_before_the_move(run_main, sw, capsys) -> None:
    """Instance 1 claims in the same instant: this clone, instance 2, withdraws
    its claim, does not move the issue, and names the branch it cut. The rival's
    claim lands before the third read: the guard's, the claim's and its re-read."""
    github = _assigned_42()

    def rival(number: int, seen: int) -> None:
        if seen == 2:
            github.post(number, _stamp(sw, "claim", 1))

    github.on_view = rival
    rc, mutations = run_main(_task(["type:bug", "state:backlog"]), instance=2, github=github)
    assert rc == sw.EXIT_CLAIM_LOST == 2
    assert ("move", "in-progress") not in mutations
    assert ("ownership", "comment") in mutations
    err = capsys.readouterr().err
    assert "this clone, instance 2, withdrew its claim" in err
    assert "[stopped] start-work #42: instance 1 claimed it in the same instant" in err
    assert "git checkout main && git branch -D fix/42-do-the-thing" in err


def test_a_lost_claim_whose_withdrawal_fails_still_stops(run_main, sw, capsys) -> None:
    """The issue is instance 1's either way, so this clone does not move it."""
    github = _assigned_42()

    def rival(number: int, seen: int) -> None:
        if seen == 2:
            github.post(number, _stamp(sw, "claim", 1))
            github.failing.add("comment")

    github.on_view = rival
    rc, mutations = run_main(_task(["type:bug", "state:backlog"]), instance=2, github=github)
    assert rc == sw.EXIT_CLAIM_LOST
    assert ("move", "in-progress") not in mutations
    err = capsys.readouterr().err
    assert "could not withdraw its own claim" in err
    assert "[stopped] start-work #42: instance 1 claimed it" in err


def test_a_claim_made_first_after_the_guard_stops_before_the_move(run_main, sw, capsys) -> None:
    """Instance 3 claims after the guard's read and before this clone's claim
    reads the issue. The first claim holds, whatever its number, so this clone,
    instance 2, writes no claim and does not move the issue (DEC-059 point 7)."""
    github = _assigned_42()

    def rival(number: int, seen: int) -> None:
        if seen == 1:
            github.post(number, _stamp(sw, "claim", 3))

    github.on_view = rival
    rc, mutations = run_main(_task(["type:bug", "state:backlog"]), instance=2, github=github)
    assert rc == sw.EXIT_CLAIM_LOST
    assert mutations == [("branch", "fix/42-do-the-thing"), ("assignee", "me")]
    captured = capsys.readouterr()
    assert "#42 is owned by instance 3, so this clone, instance 2, did not claim it" in (
        captured.out
    )
    assert "[stopped] start-work #42: instance 3 claimed it first, and the first claim holds" in (
        captured.err
    )
    assert "git checkout main && git branch -D fix/42-do-the-thing" in captured.err


def test_a_failed_claim_still_starts_the_work(run_main, capsys) -> None:
    github = _assigned_42()
    github.failing.add("comment")
    rc, mutations = run_main(_task(["type:bug", "state:backlog"]), instance=2, github=github)
    assert rc == 0
    assert ("move", "in-progress") in mutations
    assert "[warn] ownership: the claim on #42 failed" in capsys.readouterr().err


def test_a_dry_run_claims_nothing(run_main, capsys) -> None:
    github = _assigned_42()
    rc, mutations = run_main(
        _task(["type:bug", "state:backlog"]), dry_run=True, instance=2, github=github
    )
    assert rc == 0
    assert mutations == []
    assert github.writes() == []
    assert "  ownership: claimed for instance 2" in capsys.readouterr().out


# ---- a project with a topology of seats (DEC-059 points 5, 7 and 9) -----------
#
# The run's reading of the topology stands in for what #2140 and #2141 bring
# (`tests/pm_ownership_support`).


@pytest.fixture
def seats(sw, monkeypatch) -> Any:
    """Returns `seat(role="worker", holders=None)`: this clone holds `worker-2`,
    the topology's second seat, with the key `k2`, and the topology's reading
    gives each seat's holder (`worker-2` held by this clone by default)."""
    claims = sw.instance_claims
    ownership = claims.ownership

    def seat(role: str = "worker", holders: dict | None = None) -> None:
        held = {"worker-2": ownership.Holder(ownership.SEAT_HELD, "me", "k2")}
        topology = claims.Topology(claims.Seat("worker-2", 2, role), holders or held)
        topology_with(claims, monkeypatch, topology, key="k2")

    return seat


def _seat_claim(sw, seat: str, instance: int, key: str) -> str:
    return sw.instance_claims.ownership.format_event_comment(
        event="claim", instance=instance, seat=seat, seat_number=instance, clone=key
    )


def test_a_worker_claims_for_its_seat(run_main, sw, seats, capsys) -> None:
    """The claim names the seat, its number and the clone's key (DEC-059 point 9)."""
    seats()
    github = _assigned_42()
    rc, mutations = run_main(_task(["type:bug", "state:backlog"]), github=github)
    assert rc == 0
    assert ("move", "in-progress") in mutations
    claim = github.issues[42].comments[0]["body"]
    assert "event=claim instance=2 seat=worker-2 seat_number=2 clone=k2 " in claim
    assert "[ok] ownership: #42 claimed for seat worker-2, instance 2" in capsys.readouterr().out


def test_a_claim_whose_seat_was_released_is_no_claim(run_main, sw, seats, capsys) -> None:
    """Seat worker-1 is free now, so its old claim stops counting with no write to
    the issue (DEC-059 point 5): the guard passes and this clone claims."""
    ownership = sw.instance_claims.ownership
    seats(
        holders={
            "worker-1": ownership.Holder(ownership.SEAT_FREE),
            "worker-2": ownership.Holder(ownership.SEAT_HELD, "me", "k2"),
        }
    )
    github = _assigned_42()
    github.post(42, _seat_claim(sw, "worker-1", 1, "k1"))
    rc, mutations = run_main(_task(["type:bug", "state:backlog"]), github=github)
    assert rc == 0
    assert ("move", "in-progress") in mutations
    assert "#42 claimed for seat worker-2, instance 2" in capsys.readouterr().out


def test_another_seats_task_is_refused(run_main, sw, seats, capsys) -> None:
    ownership = sw.instance_claims.ownership
    seats(
        holders={
            "worker-1": ownership.Holder(ownership.SEAT_HELD, "me", "k1"),
            "worker-2": ownership.Holder(ownership.SEAT_HELD, "me", "k2"),
        }
    )
    github = _assigned_42()
    github.post(42, _seat_claim(sw, "worker-1", 1, "k1"))
    rc, mutations = run_main(_task(["type:bug", "state:backlog"]), github=github)
    assert rc == 2
    assert mutations == []
    assert (
        "#42 is owned by seat worker-1, instance 1, and this clone is seat worker-2, instance 2."
        in capsys.readouterr().err
    )


def test_a_claim_whose_seat_cannot_be_read_refuses(run_main, sw, seats, capsys) -> None:
    """No consumer treats an unjudged claim as free (ADR-041 point 5)."""
    seats()
    github = _assigned_42()
    github.post(42, _seat_claim(sw, "worker-1", 1, "k1"))
    rc, mutations = run_main(_task(["type:bug", "state:backlog"]), github=github)
    assert rc == 2
    assert mutations == []
    assert "whose claim could not be judged since its seat is not among the seats read" in (
        capsys.readouterr().err
    )


def test_code_that_cannot_read_the_topology_in_full_makes_no_claim(
    run_main, sw, monkeypatch, capsys
) -> None:
    """DEC-061 point 9, ADR-072 point 5: the claim that starts a Task refuses on
    the mark with exit 2, before anything is written."""
    claims = sw.instance_claims
    ownership = claims.ownership
    held = {"worker-2": ownership.Holder(ownership.SEAT_HELD, "me", "k2")}
    reading = claims.Topology(
        claims.Seat("worker-2", 2, "worker"), held, refusal="this code cannot read it in full."
    )
    topology_with(claims, monkeypatch, reading, key="k2")
    github = _assigned_42()
    rc, mutations = run_main(_task(["type:bug", "state:backlog"]), github=github)
    assert (rc, mutations) == (2, [])
    assert "[refused] start-work #42: this code cannot read it in full." in capsys.readouterr().err
    assert github.issues[42].comments == []


def _pooled(sw, monkeypatch, *, seat_pools: tuple[str, ...], rows: Any) -> None:
    """This clone holds `worker-2`, serving `seat_pools`, in a topology that
    declares the pools alpha and bravo; `rows` are the open milestones (None: the
    read fails)."""
    claims = sw.instance_claims
    ownership = claims.ownership
    held = {"worker-2": ownership.Holder(ownership.SEAT_HELD, "me", "k2")}
    seat = claims.Seat("worker-2", 2, "worker", None, seat_pools)
    topology_with(
        claims, monkeypatch, claims.Topology(seat, held, pools=("alpha", "bravo")), key="k2"
    )
    monkeypatch.setattr(sw.pools.milestone, "list_open_milestones", lambda _c, gh=None: rows)


def _in_milestone(number: int | None) -> dict:
    task = _task(["type:bug", "state:backlog"])
    task["milestone"] = None if number is None else {"number": number, "title": "M"}
    return task


ROWS = [{"number": 3, "description": "Pool: alpha"}, {"number": 4, "description": "Pool: bravo"}]


@pytest.mark.parametrize(
    ("milestone", "said"),
    [(4, "it is in the pool bravo, outside the pools this seat serves (alpha)"), (None, "no pool")],
)
def test_a_task_outside_the_seats_pools_warns_and_is_taken(
    run_main, sw, monkeypatch, capsys, milestone, said
) -> None:
    """DEC-061 point 5: the take's own check is a warning, never a gate."""
    _pooled(sw, monkeypatch, seat_pools=("alpha",), rows=ROWS)
    rc, mutations = run_main(_in_milestone(milestone), github=_assigned_42())
    assert rc == 0 and ("move", "in-progress") in mutations
    err = capsys.readouterr().err
    assert "[warn] start-work #42:" in err and said in err


def test_a_task_in_the_seats_pools_takes_with_no_warning(run_main, sw, monkeypatch, capsys) -> None:
    _pooled(sw, monkeypatch, seat_pools=("alpha",), rows=ROWS)
    rc, _mutations = run_main(_in_milestone(3), github=_assigned_42())
    assert rc == 0
    assert "[warn] start-work" not in capsys.readouterr().err


def test_a_milestone_that_cannot_be_read_warns_and_the_take_goes_on(
    run_main, sw, monkeypatch, capsys
) -> None:
    """ADR-072 point 6: the take's own check warns where it cannot read the Milestone."""
    _pooled(sw, monkeypatch, seat_pools=("alpha",), rows=None)
    rc, _mutations = run_main(_in_milestone(3), github=_assigned_42())
    assert rc == 0
    assert "the pool of its Milestone #3 could not be read" in capsys.readouterr().err


def test_a_clone_that_holds_no_seat_marks_nothing(run_main, sw, monkeypatch, capsys) -> None:
    """DEC-059 point 6: no seat, no instance, whatever id file the clone kept."""
    claims = sw.instance_claims
    topology_with(claims, monkeypatch, claims.Topology(None, {}), key="k9")
    github = _assigned_42()
    github.post(42, _stamp(sw, "claim", 3))
    rc, _mutations = run_main(_task(["type:bug", "state:backlog"]), instance=2, github=github)
    assert rc == 0
    assert github.calls == []
    assert "ownership" not in capsys.readouterr().out
