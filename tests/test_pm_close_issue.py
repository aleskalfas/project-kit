"""Tests for project-management's close-issue script's pure logic.

Covers checkbox gate detection (`_unticked_boxes`, and the gate's `all_boxes_ticked`),
structural-type inference, parent-chain walking, — per issue #60 — the
label-reconciliation helper that close-issue shares with move-issue, — per
issue #1936 — the person's authorisation a won't-do close and a container's
close need, and — per issue #1937 — the closure cascade's report on a parent,
which reads the engine's fold over the parent's children.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from tests import pm_lifecycle_world as lw

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts" / "close-issue.py"
)
LIB_PATH = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"

sys.path.insert(0, str(LIB_PATH))
from _lib import axis_labels, checkbox_gate  # noqa: E402
from _lib.labels import (  # noqa: E402
    NON_TERMINAL_STATE_VALUES,
    TERMINAL_STATE_VALUE,
    _resolve_state_labels,
    reconcile_state_labels_to_done,
)


@pytest.fixture(scope="module")
def ci():
    module_name = "pm_close_issue_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def issue_types() -> dict:
    return {
        "types": {
            "epic": {"title_prefix": "EPIC", "title_case": "upper"},
            "feature": {"title_prefix": "Feature", "title_case": "title"},
            "umbrella": {"title_prefix": "Umbrella", "title_case": "title"},
            "task": {"title_prefix": "Task", "title_case": "title"},
        },
    }


# --- checkbox gate ---------------------------------------------------


def test_unticked_boxes_detects_unticked(ci) -> None:
    body = (
        "Feature: #1\n\n"
        "## Acceptance criteria\n"
        "- [ ] First criterion\n"
        "- [x] Second criterion\n"
        "- [ ] Third criterion\n"
    )
    unticked = ci._unticked_boxes(body)
    assert len(unticked) == 2
    assert any("First criterion" in line for line in unticked)
    assert any("Third criterion" in line for line in unticked)


def test_unticked_boxes_handles_indentation(ci) -> None:
    body = "  - [ ] indented box\n    - [ ] more indented\n- [x] ticked\n"
    unticked = ci._unticked_boxes(body)
    assert len(unticked) == 2


def test_unticked_boxes_recognises_asterisk_lists(ci) -> None:
    body = "* [ ] asterisk-style box\n* [x] ticked\n"
    unticked = ci._unticked_boxes(body)
    assert len(unticked) == 1


def test_unticked_boxes_returns_empty_for_no_boxes(ci) -> None:
    body = "## What\nplain prose, no boxes."
    assert ci._unticked_boxes(body) == []


def test_unticked_boxes_returns_empty_for_all_ticked(ci) -> None:
    body = "- [x] First\n- [x] Second\n- [x] Third\n"
    assert ci._unticked_boxes(body) == []


def test_unticked_boxes_ignores_non_checkbox_dash_lines(ci) -> None:
    body = "- not a checkbox\n- [ ] a real one\n- [ ] another\n"
    assert len(ci._unticked_boxes(body)) == 2


def test_all_boxes_ticked_true_when_all_ticked(ci) -> None:
    body = "- [x] First\n- [x] Second\n"
    assert checkbox_gate.all_boxes_ticked(body) is True


def test_all_boxes_ticked_false_when_any_unticked(ci) -> None:
    body = "- [ ] First\n- [x] Second\n"
    assert checkbox_gate.all_boxes_ticked(body) is False


def test_all_boxes_ticked_true_when_no_boxes_at_all(ci) -> None:
    # An issue with no checkboxes can close per DEC-007 (gate applies only
    # when boxes exist).
    body = "## What\nplain prose."
    assert checkbox_gate.all_boxes_ticked(body) is True


# --- structural type inference ---------------------------------------


def test_infer_structural_type_recognises_task(ci, issue_types) -> None:
    assert ci.infer_structural_type("[Task] x", issue_types) == "task"


def test_infer_structural_type_returns_none_for_unknown(ci, issue_types) -> None:
    assert ci.infer_structural_type("Plain", issue_types) is None


# ---- _find_open_children (cascade-eligibility, issue #118) -----------------


def _fake_gh_list(ci, monkeypatch, rows, *, returncode=0, complete=True) -> None:
    """Stub the corpus at the containment seam, which now owns acquisition.

    `returncode=1` models a failed query (the seam returns None); `complete=False`
    models a struck ceiling — which `_find_open_children` must not answer from,
    since a child may sit in the rows it never fetched.
    """
    containment = ci.containment
    monkeypatch.setattr(
        containment,
        "fetch_issue_corpus",
        lambda _c, **_kw: (
            None
            if returncode != 0
            else containment.IssueCorpus(rows=tuple(rows), complete=complete)
        ),
    )
    # No native substrate in these offline tests: a determinate textual-only read.
    monkeypatch.setattr(
        containment,
        "read_native_children",
        lambda _config, *, parent_number: containment.NativeRead(
            numbers=set(), outcome=containment.NativeReadOutcome.UNSUPPORTED
        ),
    )


def test_find_open_children_returns_only_open_children_of_parent(ci, monkeypatch) -> None:
    rows = [
        {"number": 10, "state": "OPEN", "body": "Feature: #5\n\n## What"},
        {"number": 11, "state": "CLOSED", "body": "Feature: #5\n\n## What"},
        {"number": 12, "state": "OPEN", "body": "Feature: #99\n\n## What"},
        {"number": 5, "state": "OPEN", "body": "no parent ref"},
        {"number": 13, "state": "OPEN", "body": "## What\nno ref"},
    ]
    _fake_gh_list(ci, monkeypatch, rows)
    children = ci._find_open_children(5, {})
    assert [child.ref for child in children.open] == ["#10"]
    assert (children.unread, children.incomplete) == ((), None)


def test_find_open_children_empty_when_all_children_closed(ci, monkeypatch) -> None:
    rows = [
        {"number": 10, "state": "CLOSED", "body": "Feature: #5"},
        {"number": 11, "state": "CLOSED", "body": "Feature: #5"},
    ]
    _fake_gh_list(ci, monkeypatch, rows)
    children = ci._find_open_children(5, {})
    assert (children.open, children.unread, children.incomplete) == ((), (), None)


def test_find_open_children_says_the_list_failed_on_gh_failure(ci, monkeypatch) -> None:
    _fake_gh_list(ci, monkeypatch, [], returncode=1)
    children = ci._find_open_children(5, {})
    assert children.open == ()
    assert children.incomplete == "the issue list could not be read (gh failure)"


def test_find_open_children_refuses_a_truncated_corpus(ci, monkeypatch) -> None:
    """A truncated corpus yields no hint rather than a misleadingly short one.

    This is diagnostic output, not a gate: the sole caller runs it after the
    engine fold has already refused the close, to list what the user must close
    first. Before #846 it fetched 500 rows with no truncation check, so past 500
    issues it could omit still-open children — or show none — while reading as
    the complete set. Naming no child, and saying the set was not read in full,
    is the honest answer.
    """
    rows = [{"number": 10, "state": "OPEN", "body": "Feature: #5\n\n## What"}]
    _fake_gh_list(ci, monkeypatch, rows, complete=False)
    children = ci._find_open_children(5, {})
    assert children.open == ()
    assert "not enumerated to exhaustion" in children.incomplete


# ---- regression #60 — label reconciliation on close --------------------
#
# close-issue previously closed the GitHub issue but did not reconcile
# state:* labels.  Closing EPIC #52 left it CLOSED carrying both
# state:in-progress AND state:done; a separate move-issue was needed.
# The fix: both close paths call reconcile_state_labels_to_done() from
# _lib.labels, which is the same routine reused from move-issue's logic.
#
# Tests below verify the reconcile helper's contract (pure unit) and the
# regression scenario (issue closed from in-progress ends with exactly
# state:done, no stale label).


def test_reconcile_state_values_are_correct() -> None:
    """The state-value set matches the workflow states (the per-call resolver
    turns these into concrete labels through the seam)."""
    assert TERMINAL_STATE_VALUE == "done"
    assert set(NON_TERMINAL_STATE_VALUES) == {
        "todo",
        "backlog",
        "in-progress",
        "review",
    }


def test_resolve_state_labels_greenfield_identity() -> None:
    """No map ⇒ the resolver returns the kit's own `state:*` labels — the
    byte-identical greenfield behaviour the eager constants used to hold."""
    terminal, non_terminal = _resolve_state_labels(None)
    assert terminal == "state:done"
    assert set(non_terminal) == {
        "state:todo",
        "state:backlog",
        "state:in-progress",
        "state:review",
    }


def test_resolve_state_labels_derive_bound_degrades_to_none() -> None:
    """A present map binding `state` to a derive predicate ⇒ no kit `state:*`
    label is written or removed (the RF-1 fix): the resolver returns
    `(None, ())`, so reconcile becomes a no-op on the label substrate."""
    derive_map = axis_labels.SubstrateMap(axes={"state": {"derive": {"from": "open-closed"}}})
    terminal, non_terminal = _resolve_state_labels(derive_map)
    assert terminal is None
    assert non_terminal == ()


def test_resolve_state_labels_unsupported_degrades_to_none() -> None:
    """A present map marking `state` unsupported (or omitting it) ⇒ degrade."""
    unsupported_map = axis_labels.SubstrateMap(axes={"state": {"unsupported": True}})
    assert _resolve_state_labels(unsupported_map) == (None, ())
    absent_map = axis_labels.SubstrateMap(axes={"priority": {"unsupported": True}})
    assert _resolve_state_labels(absent_map) == (None, ())


def test_resolve_state_labels_label_bound_uses_adopter_substrate() -> None:
    """A present map binding `state` to an adopter label set resolves the
    terminal + non-terminal targets to the adopter's OWN labels, never the
    kit's `state:*`."""
    label_map = axis_labels.SubstrateMap(
        axes={
            "state": {
                "label": {
                    "remap": {
                        "todo": "Status/Todo",
                        "in-progress": "Status/Doing",
                        "done": "Status/Done",
                    }
                }
            }
        }
    )
    terminal, non_terminal = _resolve_state_labels(label_map)
    assert terminal == "Status/Done"
    # Only the two non-terminal values WITH a remap entry resolve; the rest
    # value-degrade and are dropped from the removal set (never kit-written).
    assert set(non_terminal) == {"Status/Todo", "Status/Doing"}


def test_reconcile_noop_when_already_correct() -> None:
    """reconcile_state_labels_to_done is a no-op when state:done is present
    and no non-terminal label is present."""
    mock_gh_run = MagicMock()
    result = reconcile_state_labels_to_done(
        42,
        ["state:done", "type:task", "priority:High"],
        config={},
        gh_run=mock_gh_run,
    )
    assert result is True
    mock_gh_run.assert_not_called()


def test_reconcile_regression_60_in_progress_to_done(tmp_path) -> None:
    """Regression #60 — issue closed from in-progress (won't-do) ends with
    exactly state:done; stale state:in-progress label is removed.

    Simulates the exact scenario: the issue had state:in-progress on it,
    close-issue closed it, then reconcile_state_labels_to_done must issue
    an edit that removes state:in-progress and adds state:done.
    """
    captured_cmds: list[list[str]] = []

    def fake_gh_run(cmd, config, *, check=True, **kwargs):
        captured_cmds.append(cmd)
        proc = MagicMock()
        proc.returncode = 0
        proc.stderr = ""
        return proc

    result = reconcile_state_labels_to_done(
        42,
        ["state:in-progress", "type:bug", "priority:Medium"],
        config={},
        gh_run=fake_gh_run,
    )

    assert result is True
    assert len(captured_cmds) == 1
    cmd = captured_cmds[0]
    # Must add state:done
    assert "--add-label" in cmd
    add_idx = cmd.index("--add-label")
    assert cmd[add_idx + 1] == "state:done"
    # Must remove state:in-progress
    assert "--remove-label" in cmd
    remove_idx = cmd.index("--remove-label")
    assert cmd[remove_idx + 1] == "state:in-progress"
    # Must NOT include state:done in any --remove-label position
    remove_labels = [cmd[i + 1] for i, arg in enumerate(cmd) if arg == "--remove-label"]
    assert "state:done" not in remove_labels


def test_reconcile_removes_multiple_stale_labels() -> None:
    """If an issue somehow carries both state:in-progress and state:review,
    both are removed in a single gh call alongside the state:done add."""
    captured_cmds: list[list[str]] = []

    def fake_gh_run(cmd, config, *, check=True, **kwargs):
        captured_cmds.append(cmd)
        proc = MagicMock()
        proc.returncode = 0
        proc.stderr = ""
        return proc

    result = reconcile_state_labels_to_done(
        52,
        ["state:in-progress", "state:review"],
        config={},
        gh_run=fake_gh_run,
    )

    assert result is True
    assert len(captured_cmds) == 1
    cmd = captured_cmds[0]
    remove_labels = {cmd[i + 1] for i, arg in enumerate(cmd) if arg == "--remove-label"}
    assert remove_labels == {"state:in-progress", "state:review"}


def test_reconcile_returns_false_on_gh_failure() -> None:
    """reconcile_state_labels_to_done returns False when gh exits non-zero."""

    def fake_gh_run(cmd, config, *, check=True, **kwargs):
        proc = MagicMock()
        proc.returncode = 1
        proc.stderr = "some gh error"
        return proc

    result = reconcile_state_labels_to_done(
        99,
        ["state:in-progress"],
        config={},
        gh_run=fake_gh_run,
    )
    assert result is False


def test_reconcile_adds_done_when_missing_and_no_stale_labels() -> None:
    """If no non-terminal label is present but state:done is also absent
    (e.g. no state label at all), state:done is still added."""
    captured_cmds: list[list[str]] = []

    def fake_gh_run(cmd, config, *, check=True, **kwargs):
        captured_cmds.append(cmd)
        proc = MagicMock()
        proc.returncode = 0
        proc.stderr = ""
        return proc

    result = reconcile_state_labels_to_done(
        7,
        ["type:task", "priority:Low"],
        config={},
        gh_run=fake_gh_run,
    )
    assert result is True
    assert len(captured_cmds) == 1
    cmd = captured_cmds[0]
    add_idx = cmd.index("--add-label")
    assert cmd[add_idx + 1] == "state:done"
    # No --remove-label args since no stale labels present
    assert "--remove-label" not in cmd


# ---- RF-1 (#265) — brownfield close must NOT write a kit state:done label ---
#
# `close-issue` calls `reconcile_state_labels_to_done` on all three close modes.
# Before the RF-1 fix the helper built its write target from an import-time
# eager `axis_labels.label("state","done")` (the map-blind greenfield-identity
# constructor), so a present-map adopter whose `state` axis is derive-bound or
# unsupported got `state:done` written onto a brownfield issue — a constraint-1
# ("never write an unmanaged label") violation. The fix threads the substrate
# map and resolves through `resolve_write`, skipping the add on DEGRADE.

DERIVE_STATE_MAP = axis_labels.SubstrateMap(
    axes={
        "state": {
            "derive": {
                "from": "open-closed",
                "states": {"open": "open", "done": "closed"},
            }
        }
    }
)


def test_reconcile_derive_bound_writes_no_state_label() -> None:
    """A derive-bound `state` map ⇒ reconcile issues NO gh edit (no kit
    `state:done` add, no removal): the open/closed substrate carries state."""
    mock_gh_run = MagicMock()
    result = reconcile_state_labels_to_done(
        42,
        ["state:in-progress", "type:bug"],  # a stale kit label present
        config={},
        gh_run=mock_gh_run,
        substrate_map=DERIVE_STATE_MAP,
    )
    assert result is True
    mock_gh_run.assert_not_called()


def test_reconcile_unsupported_state_writes_no_state_label() -> None:
    """An `unsupported` (or absent) `state` axis under a present map ⇒ reconcile
    is a no-op on the label substrate (no kit `state:done`)."""
    mock_gh_run = MagicMock()
    result = reconcile_state_labels_to_done(
        42,
        ["state:review"],
        config={},
        gh_run=mock_gh_run,
        substrate_map=axis_labels.SubstrateMap(axes={"state": {"unsupported": True}}),
    )
    assert result is True
    mock_gh_run.assert_not_called()


def test_mutation_brownfield_close_coerced_eager_label_leak_is_caught() -> None:
    """MUTATION-PROOF (RF-1): model the pre-fix bug — an eager
    `axis_labels.label("state","done")` write target that ignores the map — and
    confirm the fail-closed assertion catches the kit `state:done` leaking onto
    a brownfield (derive-bound) issue; then confirm the real reconcile does NOT
    issue any gh edit under that map."""
    # The pre-fix construction: map-blind eager identity constructor.
    buggy_terminal = axis_labels.label("state", "done")
    assert buggy_terminal == "state:done"  # the kit's own label, ignoring the map

    def assert_no_kit_state_write(cmds: list[list[str]]) -> None:
        for cmd in cmds:
            for i, arg in enumerate(cmd):
                if arg == "--add-label":
                    assert not cmd[i + 1].startswith("state:"), cmd[i + 1]

    # Model what the buggy helper WOULD have emitted under the derive map.
    buggy_cmds = [["gh", "issue", "edit", "42", "--add-label", buggy_terminal]]
    with pytest.raises(AssertionError):
        assert_no_kit_state_write(buggy_cmds)

    # The real helper fails closed: no gh edit at all under the derive map.
    captured: list[list[str]] = []

    def fake_gh_run(cmd, config, *, check=True, **kwargs):
        captured.append(cmd)
        proc = MagicMock()
        proc.returncode = 0
        proc.stderr = ""
        return proc

    result = reconcile_state_labels_to_done(
        42,
        ["state:in-progress"],
        config={},
        gh_run=fake_gh_run,
        substrate_map=DERIVE_STATE_MAP,
    )
    assert result is True
    assert captured == []  # no gh edit issued
    assert_no_kit_state_write(captured)


def test_reconcile_greenfield_unchanged_with_explicit_none_map() -> None:
    """Greenfield parity: passing `substrate_map=None` (the default) keeps the
    exact pre-rewire add-`state:done` / remove-stale behaviour."""
    captured: list[list[str]] = []

    def fake_gh_run(cmd, config, *, check=True, **kwargs):
        captured.append(cmd)
        proc = MagicMock()
        proc.returncode = 0
        proc.stderr = ""
        return proc

    result = reconcile_state_labels_to_done(
        42,
        ["state:in-progress"],
        config={},
        gh_run=fake_gh_run,
        substrate_map=None,
    )
    assert result is True
    assert len(captured) == 1
    cmd = captured[0]
    assert cmd[cmd.index("--add-label") + 1] == "state:done"
    assert cmd[cmd.index("--remove-label") + 1] == "state:in-progress"


# ---- regression #65 — _check_parent_eligibility NameError on config --------
#
# _check_parent_eligibility called _gh_get_issue(parent_num, config) but
# `config` was not a parameter of the function — NameError at runtime.
# Hit live closing #62 (parent EPIC #59): close + label-reconcile succeeded,
# then the eligibility report crashed before printing.
#
# Fix: added `config: dict` parameter and threaded it from the call site.
# Tests below cover the eligible and not-eligible branches via a fake
# _gh_get_issue, a fake engine fold and a fake read of the open children
# (monkeypatched on the module) to confirm no NameError.


#: The engine's fold over a parent's children, as `pkit process cascade --json`
#: carries it: every child done; held at an open child (#12 here, the second of
#: two); and stopped on a read before it counted a member.
FOLD_OPENED = {"opened": True, "indeterminate": False, "reached": 2, "total": 2}
FOLD_HELD_OPEN = {
    "opened": False,
    "indeterminate": True,
    "reached": 1,
    "total": 2,
    "reason": "member '12' of 'project-management:issue-lifecycle' has no resolved outcome yet",
}
FOLD_STOPPED_ON_A_READ = {
    "opened": False,
    "indeterminate": True,
    "reached": 0,
    "total": 0,
    "reason": "could not read cascade members for parent '59'",
    "stderr_tail": "gh: HTTP 502",
}

TICKED_PARENT = {"state": "open", "body": "- [x] finished thing\n- [x] another done thing\n"}
UNTICKED_PARENT = {"state": "open", "body": "- [ ] unfinished thing\n- [x] done thing\n"}
ELIGIBLE = "eligible to close: run `pkit pm close-issue 59 --mode=cascade-eligibility-close`"


def _parent_report(
    ci, monkeypatch, capsys, parent: dict, fold: dict | None, open_children=()
) -> SimpleNamespace:
    """Report on parent #59 with its record, the engine's fold over its children
    and the open children the containment seam reads, each faked."""
    monkeypatch.setattr(ci, "_gh_get_issue", lambda num, cfg: parent)
    folds: list[int] = []

    def fake_fold(number: int) -> dict | None:
        folds.append(number)
        return fold

    monkeypatch.setattr(ci, "_engine_cascade_fold", fake_fold)
    reads: list[int] = []

    def fake_open_children(number: int, _config: dict):
        reads.append(number)
        children = tuple(SimpleNamespace(ref=f"#{n}", repository=None) for n in open_children)
        return ci._OpenChildren(open=children)

    monkeypatch.setattr(ci, "_find_open_children", fake_open_children)
    # Regression #65: `config` is threaded through, so the report never raises.
    assert ci._check_parent_eligibility(59, config={}) is None
    out, err = capsys.readouterr()
    return SimpleNamespace(out=out, err=err, folds=folds, reads=reads)


def test_check_parent_eligibility_not_eligible_unticked_boxes(ci, monkeypatch, capsys) -> None:
    """No open child left, but an unticked box: not eligible, and said so."""
    run = _parent_report(ci, monkeypatch, capsys, UNTICKED_PARENT, FOLD_OPENED)
    assert run.out == (
        "  · parent #59 open; no open child left, but not eligible (1 unticked box(es))\n"
    )
    assert run.folds == [59]


def test_check_parent_eligibility_eligible_all_boxes_ticked(ci, monkeypatch, capsys) -> None:
    """The fold opened and every box is ticked: eligible, with the close that
    asks the person to authorise it."""
    run = _parent_report(ci, monkeypatch, capsys, TICKED_PARENT, FOLD_OPENED)
    assert run.out == (
        f"  · parent #59 open; no open child left and checkboxes complete — {ELIGIBLE}\n"
    )
    assert run.reads == []


def test_check_parent_eligibility_already_closed(ci, monkeypatch, capsys) -> None:
    """A closed parent is said to be closed, and its children are not folded."""
    run = _parent_report(ci, monkeypatch, capsys, {"state": "closed", "body": ""}, FOLD_OPENED)
    assert run.out == "  · parent #59 already closed\n"
    assert run.folds == []


# ---- #1937 — a parent is eligible only once its last open child closes --------
#
# DEC-006 makes a parent eligible to close when its last open child closes, and
# DEC-034 has the eligibility check read the engine's cascade resolution. The
# report read the parent's checkboxes alone, and said "eligible to close pending
# sibling check" while a sibling was still open. It now reads the engine's fold
# first: a parent with an open child is not eligible, and the child is named.


def test_a_parent_with_an_open_child_is_not_eligible_and_the_child_is_named(
    ci, monkeypatch, capsys
) -> None:
    run = _parent_report(ci, monkeypatch, capsys, TICKED_PARENT, FOLD_HELD_OPEN, (12,))
    assert run.out == "  · parent #59 open; not eligible — open child(ren): #12\n"
    assert "eligible to close" not in run.out
    assert "pending sibling check" not in run.out
    assert run.folds == [59]
    assert run.reads == [59]


def test_a_parent_whose_fold_stopped_on_a_read_is_not_said_eligible(
    ci, monkeypatch, capsys
) -> None:
    """The fold stopped before it counted a member, so no read of the children
    can say what holds it: the engine's reason and what the predicate said."""
    run = _parent_report(ci, monkeypatch, capsys, TICKED_PARENT, FOLD_STOPPED_ON_A_READ)
    assert run.out == (
        "  · parent #59 open; not eligible — whether a child is open is not known: "
        "could not read cascade members for parent '59'\n"
        "      the predicate said:\n"
        "        gh: HTTP 502\n"
    )
    assert run.reads == []


def test_a_parent_held_with_no_open_child_found_is_not_said_eligible(
    ci, monkeypatch, capsys
) -> None:
    """The fold held, and the children read here show no open one: the
    engine's reason is said, and the parent is not eligible."""
    run = _parent_report(ci, monkeypatch, capsys, TICKED_PARENT, FOLD_HELD_OPEN)
    assert run.out == (
        "  · parent #59 open; not eligible — whether a child is open is not known: "
        f"{FOLD_HELD_OPEN['reason']}\n"
    )
    assert run.reads == [59]


def test_a_parent_whose_children_the_engine_could_not_fold_is_not_said_eligible(
    ci, monkeypatch, capsys
) -> None:
    run = _parent_report(ci, monkeypatch, capsys, TICKED_PARENT, None)
    assert run.out == (
        "  · parent #59 open; not eligible — the process engine could not fold its "
        "children, so whether one is open is not known\n"
    )
    assert run.reads == []


# ---- #1936 — a won't-do close and a container's close are the person's -------
#
# DEC-006 makes Backlog/Todo → Done (won't-do) and In Progress → Done (a
# container's cascade-eligibility close) moves the user authorises, a hard
# reject when the authorisation is missing. close-issue used to ask only at a
# terminal, so with no terminal and no --yes it closed in both modes and nobody
# was asked. It now refuses there, as move-issue refuses a user-held move, and
# writes nothing. A leaf's close through a merged PR named with --pr closed with
# no terminal and no --yes too, and is held the same way since #1968.

CAP_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"

#: A merged PR from #42's branch, the one the pr-merge close below names.
MERGED_FROM_42 = {
    "number": 1042,
    "state": "MERGED",
    "mergedAt": "2026-10-24T10:00:00Z",
    "url": "u",
    "headRefName": "fix/42-landed",
    "body": "## Summary\n",
}

#: The closes DEC-006 holds for the person: (mode argv, issue, write it makes).
HELD_CLOSES = [
    pytest.param(
        ["--reason", "superseded by #99"],
        {"title": "[Task] not needed", "labels": [{"name": "state:backlog"}]},
        ["gh", "issue", "close", "42", "--reason", "not planned"],
        id="wont-do",
    ),
    pytest.param(
        ["--mode", "cascade-eligibility-close"],
        {"title": "[EPIC] all done", "labels": [{"name": "state:in-progress"}]},
        ["gh", "issue", "close", "42", "--reason", "completed"],
        id="cascade-eligibility-close",
    ),
    pytest.param(
        ["--mode", "pr-merge", "--pr", "1042"],
        {"title": "[Task] landed", "labels": [{"name": "state:review"}]},
        ["gh", "issue", "close", "42", "--reason", "completed"],
        id="pr-merge-through-a-pr",
    ),
]


class _Stdin:
    """A standard input that is, or is not, a terminal."""

    def __init__(self, tty: bool) -> None:
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


def _close(
    ci, monkeypatch, argv: list[str], issue: dict, *, tty: bool, reply: str | None = None
) -> SimpleNamespace:
    """Run close-issue's main() on issue #42 with every other gate passed, and
    record each `gh` call and each move handed to the engine."""
    monkeypatch.setattr(sys, "argv", ["close-issue", "42", *argv, "--no-cascade"])
    monkeypatch.setattr(sys, "stdin", _Stdin(tty))
    prompts: list[str] = []

    def fake_input(prompt: str = "") -> str:
        prompts.append(prompt)
        assert reply is not None, "close-issue asked although no reply was expected"
        return reply

    monkeypatch.setattr("builtins.input", fake_input)
    monkeypatch.setattr(ci, "resolve_capability_root", lambda _explicit: CAP_ROOT)
    monkeypatch.setattr(ci.bootstrap_gate, "enforce", lambda *a, **k: True)
    monkeypatch.setattr(ci.session_guard, "enforce", lambda **k: True)
    monkeypatch.setattr(ci, "load_adopter_config", lambda _root: {})
    monkeypatch.setattr(ci, "_read_members", lambda *a: [])
    monkeypatch.setattr(
        ci, "resolve_invoker_identity", lambda **k: SimpleNamespace(github_login="me")
    )
    monkeypatch.setattr(ci, "check_membership", lambda *a: SimpleNamespace(allowed=True))
    monkeypatch.setattr(ci.axis_labels, "load_substrate_map", lambda *_a, **_k: None)
    monkeypatch.setattr(ci, "fire_hooks", lambda *a, **k: None)
    monkeypatch.setattr(ci, "_engine_cascade_fold", lambda _n: {"opened": True})
    journaled: list[tuple] = []
    monkeypatch.setattr(ci, "journal_move", lambda *a, **k: journaled.append(a))
    record = {"body": "## What\nx\n", "state": "OPEN", "milestone": None, **issue}
    monkeypatch.setattr(ci, "_gh_get_issue", lambda n, _config: record if n == 42 else None)
    monkeypatch.setattr(ci, "_gh_get_pr", lambda n, _config: MERGED_FROM_42 if n == 1042 else None)
    calls: list[list[str]] = []

    def fake_gh_run(cmd, config, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(ci, "gh_run", fake_gh_run)
    rc = ci.main()
    return SimpleNamespace(rc=rc, calls=calls, journaled=journaled, prompts=prompts)


@pytest.mark.parametrize(("argv", "issue", "close"), HELD_CLOSES)
def test_held_close_with_no_terminal_and_no_yes_is_refused(
    ci, monkeypatch, capsys, argv, issue, close
) -> None:
    run = _close(ci, monkeypatch, argv, issue, tty=False)
    assert run.rc == 1
    assert run.calls == []
    assert run.journaled == []
    err = capsys.readouterr().err
    assert "[refused]" in err
    assert "user-authorised" in err
    assert "Pass --yes to confirm the authorisation" in err


@pytest.mark.parametrize(("argv", "issue", "close"), HELD_CLOSES)
def test_held_close_with_yes_closes_without_asking(ci, monkeypatch, argv, issue, close) -> None:
    run = _close(ci, monkeypatch, [*argv, "--yes"], issue, tty=False)
    assert run.rc == 0
    assert close in run.calls
    assert run.prompts == []
    assert len(run.journaled) == 1


@pytest.mark.parametrize(("argv", "issue", "close"), HELD_CLOSES)
def test_held_close_at_a_terminal_closes_on_a_yes(ci, monkeypatch, argv, issue, close) -> None:
    run = _close(ci, monkeypatch, argv, issue, tty=True, reply="y")
    assert run.rc == 0
    assert len(run.prompts) == 1
    assert close in run.calls


@pytest.mark.parametrize(("argv", "issue", "close"), HELD_CLOSES)
def test_held_close_at_a_terminal_declined_writes_nothing(
    ci, monkeypatch, capsys, argv, issue, close
) -> None:
    run = _close(ci, monkeypatch, argv, issue, tty=True, reply="n")
    assert run.rc == 0
    assert run.calls == []
    assert run.journaled == []
    assert "aborted." in capsys.readouterr().err


@pytest.mark.parametrize(("argv", "issue", "close"), HELD_CLOSES)
def test_held_close_dry_run_needs_no_authorisation(
    ci, monkeypatch, capsys, argv, issue, close
) -> None:
    """A dry run writes nothing, so it is no close to authorise."""
    run = _close(ci, monkeypatch, [*argv, "--dry-run"], issue, tty=False)
    assert run.rc == 0
    assert run.calls == []
    assert "[dry-run]" in capsys.readouterr().out


# ---- #1937 end to end — an EPIC's two children close one after the other ------
#
# The issue's example, through the real scripts and the real engine fold against
# an in-memory GitHub (`tests/pm_lifecycle_world.py`): the EPIC has two open
# children. Closing the first reports the EPIC held by the second; closing the
# second reports it eligible to close. The harness answers the fold's members
# and membership predicates through the capability's own predicate code here.


@pytest.fixture(scope="module")
def lifecycle_scripts() -> SimpleNamespace:
    return SimpleNamespace(
        ci=lw.load_script("create-issue.py", "pm_create_issue_last_open_child"),
        pi=lw.load_script("promote-issue.py", "pm_promote_issue_last_open_child"),
        mi=lw.load_script("move-issue.py", "pm_move_issue_last_open_child"),
        hist=lw.load_script("history.py", "pm_history_last_open_child"),
        cl=lw.load_script("close-issue.py", "pm_close_issue_last_open_child"),
    )


@pytest.fixture
def world(lifecycle_scripts, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> lw.World:
    s = lifecycle_scripts
    world = lw.World(lw.Tracker(), lw.make_engine_repo(tmp_path), s.ci, s.pi, s.mi, s.hist, s.cl)
    lw.wire(world, monkeypatch)
    answer = lw._predicate_answer

    def with_the_fold(run_name: str, number: int):
        if run_name == "cascade-members":
            return lw.predicates.cascade_members(number)
        if run_name == "cascade-membership":
            return lw.predicates.cascade_membership(number)
        return answer(run_name, number)

    monkeypatch.setattr(lw, "_predicate_answer", with_the_fold)
    return world


def test_the_parent_is_eligible_only_once_its_last_open_child_closes(world, capsys) -> None:
    epic = world.file_issue(title="[EPIC] Two tasks", labels=())
    first = world.file_issue(body=f"EPIC: #{epic}\n\n{lw.AUTHORED_BODY}")
    second = world.file_issue(body=f"EPIC: #{epic}\n\n{lw.AUTHORED_BODY}")
    assert world.promote(first) == 0
    assert world.promote(second) == 0
    capsys.readouterr()

    assert world.close(first, "--reason", "superseded by #99") == 0
    out = capsys.readouterr().out
    assert f"[cascade] parents to check for eligibility: #{epic}\n" in out
    assert f"  · parent #{epic} open; not eligible — open child(ren): #{second}\n" in out
    assert "eligible to close" not in out

    assert world.close(second, "--reason", "superseded by #99") == 0
    out = capsys.readouterr().out
    assert (
        f"  · parent #{epic} open; no open child left and checkboxes complete — eligible to "
        f"close: run `pkit pm close-issue {epic} --mode=cascade-eligibility-close`\n"
    ) in out
