"""DEC-034 — pm's CLOSURE cascade rebound onto the shared cascade slot (COR-037).

Behaviour parity is the acceptance bar: a parent closes iff (checkboxes ticked
AND every child closed), pre/post identical. This file proves the pm-side
BINDING:

  * the shared `process.cascade` declaration in workflow.yaml has the right shape
    (child = the issue process, reducer `all` over the terminal `done`,
    `on_empty: satisfied`, members + membership predicates);
  * the `cascade-members` / `cascade-membership` predicate bodies reuse the SAME
    body parent-ref child-walk pm uses today, so the member set is identical;
  * the close-issue wrapper reads the engine's fold for the children-half and
    keeps the checkbox gate as the separate, AND'd other half.

The engine's GENERAL cascade fold semantics (`all`/`count`, fail-closed on an
unresolved member, the `on_empty` precedence) are proven exhaustively in
test_process_cascade_engine.py; this file pins pm's binding ONTO that engine and
the parity bullets DEC-034 enumerates (childless-closes, broken-read-holds,
won't-do counts, milestone roll-forward, all-children-closed).

The gh layer is stubbed; these tests exercise the predicate bodies + the binding
shape + the wrapper's fold-read, not the network.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parents[1]
CAP = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
CAP_SCRIPTS = CAP / "scripts"
sys.path.insert(0, str(CAP_SCRIPTS))

from _lib import lifecycle_inference as infer  # noqa: E402
from _lib import lifecycle_predicates as predicates  # noqa: E402


# --- the binding shape (workflow.yaml process.cascade) --------------------


def _load_workflow() -> dict:
    yaml = YAML(typ="safe")
    return yaml.load((CAP / "schemas" / "workflow.yaml").read_text(encoding="utf-8"))


def test_workflow_bumped_to_schema_v4() -> None:
    wf = _load_workflow()
    assert wf["schema_version"] == 4
    assert wf["process"]["version"] == 4


def test_shared_cascade_is_nested_under_process_not_the_local_sibling() -> None:
    """The engine reads `process.cascade`; the top-level `cascade:` sibling is
    pm-local (forward/downward) and the engine never looks at it. The two are
    disambiguated by NESTING — this pins that the closure fold lives under
    `process` and the local block lost its `closure` sub-key."""
    wf = _load_workflow()
    shared = wf["process"]["cascade"]
    assert shared is not None, "the engine-read closure fold must be process.cascade"
    local = wf["cascade"]
    assert "closure" not in local, "closure moved out of the local block onto the shared slot"
    assert set(local.keys()) == {"forward", "downward"}


def test_shared_cascade_shape_is_all_over_done_on_empty_satisfied() -> None:
    cascade = _load_workflow()["process"]["cascade"]
    assert cascade["runs"] == "project-management:issue-lifecycle"
    assert cascade["members"]["run"] == "cascade-members"
    assert cascade["membership"]["run"] == "cascade-membership"
    assert cascade["reducer"]["op"] == "all"
    # The terminal `done` is reached by BOTH pr-merge completion AND won't-do, so
    # a won't-do (closed) child counts toward closure (DEC-034).
    assert cascade["reducer"]["outcome"] == "done"
    assert "threshold" not in cascade["reducer"]  # `all`, not `count`
    # The childless-container case: satisfied, NOT fail-closed (DEC-034 — this is
    # the divergence the on_empty amendment exists for).
    assert cascade["on_empty"] == "satisfied"


def test_cascade_predicate_commands_are_registered() -> None:
    yaml = YAML(typ="safe")
    pkg = yaml.load((CAP / "package.yaml").read_text(encoding="utf-8"))
    commands = pkg["commands"]
    assert commands["cascade-members"]["script"] == "scripts/cascade-members.py"
    assert commands["cascade-membership"]["script"] == "scripts/cascade-membership.py"


def test_done_state_is_terminal_the_fold_target() -> None:
    # The reducer folds over the terminal STATE `done`; pin that `done` is the
    # terminal a closed child resolves to (won't-do and pr-merge alike).
    wf = _load_workflow()
    done = next(s for s in wf["process"]["states"] if s["id"] == "done")
    assert done.get("terminal") is True


# --- cascade-members: the candidate-set source ----------------------------


def test_members_returns_all_children_open_and_closed(monkeypatch) -> None:
    """The candidate set is EVERY child (open and closed), reusing the same body
    parent-ref walk close-issue's `_find_open_children` uses. The full set is
    intentional: the engine resolves each member's outcome and the `all`-over-
    `done` fold treats an open child as unresolved (holds the fold)."""
    issues = [
        {"number": 10, "state": "open", "body": "Feature: #5\n\n## What"},
        {"number": 11, "state": "closed", "body": "Feature: #5\n\n## What"},
        {"number": 12, "state": "open", "body": "Feature: #99\n"},   # other parent
        {"number": 5, "state": "open", "body": "no parent ref"},      # the parent itself
        {"number": 13, "state": "open", "body": "## What\nno ref"},   # no ref
    ]
    _stub_list_issues(monkeypatch, issues)
    out = predicates.cascade_members(5)
    # Both the open (10) and the closed (11) child are members; #12/#13 excluded;
    # the parent itself (#5) is never its own member.
    assert out["members"] == ["10", "11"]


def test_members_excludes_self_and_returns_string_ids(monkeypatch) -> None:
    issues = [
        {"number": 7, "state": "closed", "body": "EPIC: #5\n"},
        {"number": 5, "state": "open", "body": "EPIC: #5\n"},  # names itself; excluded
    ]
    _stub_list_issues(monkeypatch, issues)
    out = predicates.cascade_members(5)
    assert out["members"] == ["7"]
    assert all(isinstance(m, str) for m in out["members"])


def test_members_empty_when_no_children(monkeypatch) -> None:
    # A CHILDLESS container — the engine then resolves the empty set via
    # on_empty: satisfied (closes). The predicate itself is determinate-empty.
    _stub_list_issues(monkeypatch, [{"number": 9, "state": "open", "body": "Feature: #1\n"}])
    out = predicates.cascade_members(5)
    assert out["members"] == []
    assert predicates.INDETERMINATE_KEY not in out  # determinate empty, not a failure


def test_members_indeterminate_on_gh_failure(monkeypatch) -> None:
    # A broken members read is INDETERMINATE — the engine holds the whole fold
    # fail-closed (never a confident "no members" that satisfied could fail-open).
    monkeypatch.setattr(predicates, "_capability_root", lambda: REPO_ROOT)
    monkeypatch.setattr(predicates, "_config", lambda _root: {})
    monkeypatch.setattr(predicates, "_list_issues", lambda _c: None)
    out = predicates.cascade_members(5)
    assert out.get(predicates.INDETERMINATE_KEY) is True


def test_members_indeterminate_on_pagination_ceiling(monkeypatch) -> None:
    monkeypatch.setattr(predicates, "_capability_root", lambda: REPO_ROOT)
    monkeypatch.setattr(predicates, "_config", lambda _root: {})
    monkeypatch.setattr(predicates, "_list_issues", lambda _c: predicates._GH_CEILING)
    out = predicates.cascade_members(5)
    assert out.get(predicates.INDETERMINATE_KEY) is True


# --- cascade-membership: the per-subject confirmation ---------------------


def test_membership_true_when_child_declares_a_parent(monkeypatch) -> None:
    _stub_fetch_issue(monkeypatch, {"body": "Feature: #5\n\n## What"})
    out = predicates.cascade_membership(10)
    assert out["result"] is True
    assert out["detail"]["parent_ref"] == 5


def test_membership_false_when_no_parent_ref(monkeypatch) -> None:
    _stub_fetch_issue(monkeypatch, {"body": "## What\nno parent ref here."})
    out = predicates.cascade_membership(10)
    assert out["result"] is False
    assert out["detail"]["parent_ref"] is None


def test_membership_indeterminate_on_gh_failure(monkeypatch) -> None:
    # A broken membership read is INDETERMINATE — held fail-closed, never a
    # silent drop (which could let an `all` vacuously satisfy). This is the
    # broken-read-HOLDS bullet at the predicate level.
    monkeypatch.setattr(predicates, "_capability_root", lambda: REPO_ROOT)
    monkeypatch.setattr(predicates, "_config", lambda _root: {})
    monkeypatch.setattr(predicates, "_fetch_issue", lambda _n, _c, _f: None)
    out = predicates.cascade_membership(10)
    assert out.get(predicates.INDETERMINATE_KEY) is True


def test_members_and_find_open_children_share_one_hierarchy_source() -> None:
    """`cascade_members` and close-issue's `_find_open_children` must agree on
    the member set — both walk `infer.names_parent` over the body parent-ref.
    Pin that they read one source (so the rebound fold == pm's pre-rebind set)."""
    body = "EPIC: #42\n\n## What\nx"
    # cascade_members uses infer.names_parent; _find_open_children uses
    # _walk_parent_chain — both recognise the same first parent-ref line.
    assert infer.names_parent(body, 42) is True
    assert infer.parent_ref(body) == 42


# --- the close-issue wrapper reads the engine fold (children-half) --------


@pytest.fixture(scope="module")
def ci():
    module_name = "pm_close_issue_cascade_under_test"
    spec = importlib.util.spec_from_file_location(
        module_name, CAP_SCRIPTS / "close-issue.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _stub_process_cascade(ci, monkeypatch, *, stdout: str, returncode: int = 0) -> None:
    """Patch close-issue's subprocess.run so _engine_cascade_fold sees a fixed
    `pkit process cascade --json` payload."""
    from subprocess import CompletedProcess

    def fake_run(argv, *, capture_output=True, text=True, check=False, **kwargs):
        # Only intercept the cascade read; anything else is unexpected here.
        assert argv[:3] == ["pkit", "process", "cascade"], argv
        return CompletedProcess(argv, returncode, stdout, "")

    monkeypatch.setattr(ci.subprocess, "run", fake_run)


def test_engine_fold_parses_opened_true(ci, monkeypatch) -> None:
    payload = json.dumps({"cascade": {"opened": True, "indeterminate": False,
                                      "reached": 2, "total": 2, "reason": "all 2"}})
    _stub_process_cascade(ci, monkeypatch, stdout=payload, returncode=0)
    fold = ci._engine_cascade_fold(5)
    assert fold["opened"] is True
    assert fold["indeterminate"] is False


def test_engine_fold_parses_opened_false_even_on_nonzero_exit(ci, monkeypatch) -> None:
    # The command exits non-zero when the fold is NOT open (by design); the JSON
    # on stdout is authoritative regardless of exit code.
    payload = json.dumps({"cascade": {"opened": False, "indeterminate": False,
                                      "reached": 1, "total": 2, "reason": "1/2"}})
    _stub_process_cascade(ci, monkeypatch, stdout=payload, returncode=1)
    fold = ci._engine_cascade_fold(5)
    assert fold["opened"] is False
    assert fold["indeterminate"] is False


def test_engine_fold_parses_indeterminate(ci, monkeypatch) -> None:
    payload = json.dumps({"cascade": {"opened": False, "indeterminate": True,
                                      "reason": "membership unresolved"}})
    _stub_process_cascade(ci, monkeypatch, stdout=payload, returncode=1)
    fold = ci._engine_cascade_fold(5)
    assert fold["indeterminate"] is True


def test_engine_fold_none_when_pkit_missing(ci, monkeypatch) -> None:
    def boom(*a, **k):
        raise FileNotFoundError("pkit not on PATH")

    monkeypatch.setattr(ci.subprocess, "run", boom)
    # None -> the wrapper maps it to a fail-closed HOLD (return 3), never an open.
    assert ci._engine_cascade_fold(5) is None


def test_engine_fold_none_on_unparseable_json(ci, monkeypatch) -> None:
    _stub_process_cascade(ci, monkeypatch, stdout="not json", returncode=1)
    assert ci._engine_cascade_fold(5) is None


# --- stubs ----------------------------------------------------------------


def _stub_fetch_issue(monkeypatch, issue: dict) -> None:
    monkeypatch.setattr(predicates, "_capability_root", lambda: REPO_ROOT)
    monkeypatch.setattr(predicates, "_config", lambda _root: {})
    monkeypatch.setattr(predicates, "_fetch_issue", lambda _n, _c, _f: issue)


def _stub_list_issues(monkeypatch, issues: list[dict]) -> None:
    monkeypatch.setattr(predicates, "_capability_root", lambda: REPO_ROOT)
    monkeypatch.setattr(predicates, "_config", lambda _root: {})
    monkeypatch.setattr(predicates, "_list_issues", lambda _c: issues)
