"""DEC-034 — pm's CLOSURE cascade rebound onto the shared cascade slot (COR-037).

Behaviour parity is the acceptance bar: a parent closes iff (checkboxes ticked
AND every child closed), pre/post identical. This file proves the pm-side
BINDING:

  * the shared `process.cascade` declaration in workflow.yaml has the right shape
    (child = the issue process, reducer `all` over the terminal `done`,
    `on_empty: satisfied`, members + membership predicates);
  * `cascade-members` lists a parent's children through the containment seam
    (native sub-issues and first-line parent-refs), and `cascade-membership`
    answers "member" for every candidate it can read — never a determinate
    "not a member" — so no listed child is dropped (#1304);
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
import subprocess
import sys
from pathlib import Path

import pytest
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parents[1]
CAP = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
CAP_SCRIPTS = CAP / "scripts"
sys.path.insert(0, str(CAP_SCRIPTS))

from _lib import lifecycle_predicates as predicates  # noqa: E402

# --- the binding shape (workflow.yaml process.cascade) --------------------


def _load_workflow() -> dict:
    yaml = YAML(typ="safe")
    return yaml.load((CAP / "schemas" / "workflow.yaml").read_text(encoding="utf-8"))


def test_workflow_bumped_to_schema_v4() -> None:
    wf = _load_workflow()
    assert wf["schema_version"] == 4
    # The definition's own version moves with edits to its states (COR-044
    # point 3): 5 since the states detect with one classifier (DEC-033 D2),
    # while the file's shape, and so `schema_version`, stayed.
    assert wf["process"]["version"] == 5


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
    """The candidate set is EVERY child (open and closed), resolved through the
    containment seam close-issue's `_find_open_children` uses — native sub-issues
    and first-line parent-refs together (stubbed textual-only here). The full set
    is intentional: the engine resolves each member's outcome and the `all`-over-
    `done` fold treats an open child as unresolved (holds the fold)."""
    issues = [
        {"number": 10, "state": "open", "body": "Feature: #5\n\n## What"},
        {"number": 11, "state": "closed", "body": "Feature: #5\n\n## What"},
        {"number": 12, "state": "open", "body": "Feature: #99\n"},  # other parent
        {"number": 5, "state": "open", "body": "no parent ref"},  # the parent itself
        {"number": 13, "state": "open", "body": "## What\nno ref"},  # no ref
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


def _stub_corpus(monkeypatch, corpus, *, native_outcome=None):
    """Stub the seam's acquisition + native read. `corpus=None` = query failed."""
    containment = predicates.containment
    monkeypatch.setattr(predicates, "_capability_root", lambda: REPO_ROOT)
    monkeypatch.setattr(predicates, "_config", lambda _root: {})
    monkeypatch.setattr(containment, "fetch_issue_corpus", lambda _c, **_kw: corpus)
    outcome = native_outcome or containment.NativeReadOutcome.UNSUPPORTED
    monkeypatch.setattr(
        containment,
        "read_native_children",
        lambda _config, *, parent_number: containment.NativeRead(numbers=set(), outcome=outcome),
    )


def test_members_indeterminate_on_gh_failure(monkeypatch) -> None:
    # A broken members read is INDETERMINATE — the engine holds the whole fold
    # fail-closed (never a confident "no members" that satisfied could fail-open).
    _stub_corpus(monkeypatch, None)
    out = predicates.cascade_members(5)
    assert out.get(predicates.INDETERMINATE_KEY) is True


def test_members_indeterminate_when_the_corpus_was_truncated(monkeypatch) -> None:
    """The bug #846 was filed for: past the acquisition ceiling a child may sit in
    rows never fetched, so the member set must not be served as the whole one."""
    containment = predicates.containment
    _stub_corpus(
        monkeypatch,
        containment.IssueCorpus(
            rows=({"number": 9, "state": "open", "body": "Feature: #5\n"},),
            complete=False,
        ),
    )
    out = predicates.cascade_members(5)
    assert out.get(predicates.INDETERMINATE_KEY) is True
    assert "incomplete" in out["reason"]


def test_members_indeterminate_when_the_native_read_failed(monkeypatch) -> None:
    """An UNREADABLE native read is not an unsupported one.

    Before ADR-035 §5 both collapsed to "textual-only", so a transient error
    silently dropped any natively-linked child whose body carries no parent-ref
    line — a fail-open on a close gate. A complete corpus does not rescue it.
    """
    containment = predicates.containment
    _stub_corpus(
        monkeypatch,
        containment.IssueCorpus(
            rows=({"number": 9, "state": "open", "body": "Feature: #5\n"},),
            complete=True,
        ),
        native_outcome=containment.NativeReadOutcome.UNREADABLE,
    )
    out = predicates.cascade_members(5)
    assert out.get(predicates.INDETERMINATE_KEY) is True
    assert "native" in out["reason"]


# --- cascade-membership: the per-subject confirmation ---------------------


def test_membership_true_when_child_declares_a_parent(monkeypatch) -> None:
    _stub_record(monkeypatch, "Feature: #5\n\n## What")
    out = predicates.cascade_membership(10)
    assert out["result"] is True
    assert out["detail"] == {"parent_ref": 5, "parent_kind": "textual-only"}


@pytest.mark.parametrize(
    "body",
    [
        pytest.param("## What\nno parent ref here.", id="no-first-line-ref"),
        pytest.param("Milestone: [#7](../milestone/7)\n\n## What\n", id="milestone-first-line"),
    ],
)
def test_membership_true_when_the_first_line_names_no_issue(monkeypatch, body: str) -> None:
    """A candidate the members list returned is a member whatever its first line
    says (#1304): a native child may name no issue there, and a determinate "not
    a member" would make the engine drop it and let its container close while it
    is open. What the first line names stays in `detail`, as an account."""
    _stub_record(monkeypatch, body, native=5)
    out = predicates.cascade_membership(10)
    assert out["result"] is True
    assert predicates.INDETERMINATE_KEY not in out
    assert out["detail"] == {"parent_ref": None, "parent_kind": "native-only"}
    assert "names no issue, its native parent is #5" in out["reason"]


def test_membership_names_both_parents_of_a_disagreeing_child(monkeypatch) -> None:
    _stub_record(monkeypatch, "Feature: #5\n\n## What", native=7)
    out = predicates.cascade_membership(10)
    assert out["result"] is True
    assert out["detail"] == {"parent_ref": 5, "parent_kind": "disagree"}
    assert "its first line names #5, its native parent is #7" in out["reason"]


def test_membership_indeterminate_on_gh_failure(monkeypatch) -> None:
    # A broken membership read is INDETERMINATE — held fail-closed, never a
    # silent drop (which could let an `all` vacuously satisfy). This is the
    # broken-read-HOLDS bullet at the predicate level.
    monkeypatch.setattr(predicates, "_capability_root", lambda: REPO_ROOT)
    monkeypatch.setattr(predicates, "_config", lambda _root: {})
    monkeypatch.setattr(
        predicates.containment,
        "read_issue_record",
        lambda _config, *, issue_number: predicates.containment.UnreadIssue("gh exited 1"),
    )
    out = predicates.cascade_membership(10)
    assert out.get(predicates.INDETERMINATE_KEY) is True


def test_membership_reads_the_candidate_once_through_its_record(monkeypatch) -> None:
    """The membership step's one read is the containment seam's record read,
    which carries the native parent — it replaces the `gh issue view --json body`
    the step made before, one for one (#1281)."""
    monkeypatch.setattr(predicates, "_capability_root", lambda: REPO_ROOT)
    monkeypatch.setattr(predicates, "_config", lambda _root: {})
    calls: list[list[str]] = []

    def fake_gh(args, _config, **_kwargs):
        calls.append(list(args))
        record = {
            "number": 10,
            "body": "Feature: #5\n",
            "parent_issue_url": "https://api.github.com/repos/o/r/issues/5",
            "repository_url": "https://api.github.com/repos/o/r",
        }
        return subprocess.CompletedProcess(args, 0, stdout=json.dumps(record), stderr="")

    monkeypatch.setattr(predicates.containment, "gh_run", fake_gh)
    monkeypatch.setattr(predicates, "gh_run", fake_gh)
    out = predicates.cascade_membership(10)
    assert calls == [["gh", "api", "repos/{owner}/{repo}/issues/10"]]
    assert out["detail"] == {"parent_ref": 5, "parent_kind": "agreed"}


def test_members_and_find_open_children_share_one_hierarchy_source() -> None:
    """`cascade_members` and close-issue's `_find_open_children` must agree on
    the member set — both resolve the parent's children through the containment
    seam (`resolve_children`), whose textual side reads each first line through
    `body_parent_ref.named_issue`, the reading `cascade_membership`'s account
    takes too. Pin that it names the parent in any form."""
    containment = predicates.containment
    for line in ("EPIC: #42", "Epic: #42", "EPIC:#42", "Feature: #42 — auth"):
        body = f"{line}\n\n## What\nx"
        assert containment._body_names_parent(body, 42) is True, line
        assert predicates.body_parent_ref.named_issue(body) == 42, line
    # A milestone's number is never an issue's.
    assert containment._body_names_parent("Milestone: #42\n", 42) is False


# --- the close-issue wrapper reads the engine fold (children-half) --------


@pytest.fixture(scope="module")
def ci():
    module_name = "pm_close_issue_cascade_under_test"
    spec = importlib.util.spec_from_file_location(module_name, CAP_SCRIPTS / "close-issue.py")
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
    payload = json.dumps(
        {
            "cascade": {
                "opened": True,
                "indeterminate": False,
                "reached": 2,
                "total": 2,
                "reason": "all 2",
            }
        }
    )
    _stub_process_cascade(ci, monkeypatch, stdout=payload, returncode=0)
    fold = ci._engine_cascade_fold(5)
    assert fold["opened"] is True
    assert fold["indeterminate"] is False


def test_engine_fold_parses_opened_false_even_on_nonzero_exit(ci, monkeypatch) -> None:
    # The command exits non-zero when the fold is NOT open (by design); the JSON
    # on stdout is authoritative regardless of exit code.
    payload = json.dumps(
        {
            "cascade": {
                "opened": False,
                "indeterminate": False,
                "reached": 1,
                "total": 2,
                "reason": "1/2",
            }
        }
    )
    _stub_process_cascade(ci, monkeypatch, stdout=payload, returncode=1)
    fold = ci._engine_cascade_fold(5)
    assert fold["opened"] is False
    assert fold["indeterminate"] is False


def test_engine_fold_parses_indeterminate(ci, monkeypatch) -> None:
    payload = json.dumps(
        {"cascade": {"opened": False, "indeterminate": True, "reason": "membership unresolved"}}
    )
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


def _stub_record(monkeypatch, body: str, *, native: int | None = None) -> None:
    """The candidate's record as the containment seam reads it: `body`, under
    native parent `native` (none by default)."""
    containment = predicates.containment
    monkeypatch.setattr(predicates, "_capability_root", lambda: REPO_ROOT)
    monkeypatch.setattr(predicates, "_config", lambda _root: {})
    parent = containment.NativeParent(native) if native is not None else None
    monkeypatch.setattr(
        containment,
        "read_issue_record",
        lambda _config, *, issue_number: containment.IssueRecord(
            issue={"body": body}, parent=parent
        ),
    )


def _stub_list_issues(monkeypatch, issues: list[dict], *, native: set[int] | None = None) -> None:
    monkeypatch.setattr(predicates, "_capability_root", lambda: REPO_ROOT)
    monkeypatch.setattr(predicates, "_config", lambda _root: {})
    # Acquisition now belongs to the seam (ADR-035 §5), so the corpus is stubbed
    # there rather than in the predicate. `complete=True` says the stub IS the
    # whole tracker — these tests assert child sets, not truncation behaviour.
    containment = predicates.containment
    monkeypatch.setattr(
        containment,
        "fetch_issue_corpus",
        lambda _config, **_kw: containment.IssueCorpus(rows=tuple(issues), complete=True),
    )
    # The native `…/sub_issues` read is stubbed so these (offline) tests never
    # touch the network: `native=None` means the instance has no native substrate
    # → textual-only, which is a DETERMINATE answer (the member set is then
    # exactly the body parent-ref walk these tests assert).
    monkeypatch.setattr(
        containment,
        "read_native_children",
        lambda _config, *, parent_number: containment.NativeRead(
            numbers=native or set(),
            outcome=(
                containment.NativeReadOutcome.UNSUPPORTED
                if native is None
                else containment.NativeReadOutcome.READ
            ),
        ),
    )
