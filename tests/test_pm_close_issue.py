"""Tests for project-management's close-issue script's pure logic.

Covers checkbox gate detection (`_unticked_boxes`, `_all_boxes_ticked`),
structural-type inference, parent-chain walking, and — per issue #60 — the
label-reconciliation helper that close-issue shares with move-issue.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "scripts"
    / "close-issue.py"
)
LIB_PATH = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "scripts"
)

sys.path.insert(0, str(LIB_PATH))
from _lib.labels import (  # noqa: E402
    NON_TERMINAL_STATE_VALUES,
    TERMINAL_STATE_VALUE,
    _resolve_state_labels,
    reconcile_state_labels_to_done,
)
from _lib import axis_labels  # noqa: E402


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
    body = (
        "  - [ ] indented box\n"
        "    - [ ] more indented\n"
        "- [x] ticked\n"
    )
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
    body = (
        "- [x] First\n"
        "- [x] Second\n"
        "- [x] Third\n"
    )
    assert ci._unticked_boxes(body) == []


def test_unticked_boxes_ignores_non_checkbox_dash_lines(ci) -> None:
    body = (
        "- not a checkbox\n"
        "- [ ] a real one\n"
        "- [ ] another\n"
    )
    assert len(ci._unticked_boxes(body)) == 2


def test_all_boxes_ticked_true_when_all_ticked(ci) -> None:
    body = "- [x] First\n- [x] Second\n"
    assert ci._all_boxes_ticked(body) is True


def test_all_boxes_ticked_false_when_any_unticked(ci) -> None:
    body = "- [ ] First\n- [x] Second\n"
    assert ci._all_boxes_ticked(body) is False


def test_all_boxes_ticked_true_when_no_boxes_at_all(ci) -> None:
    # An issue with no checkboxes can close per DEC-007 (gate applies only
    # when boxes exist).
    body = "## What\nplain prose."
    assert ci._all_boxes_ticked(body) is True


# --- structural type inference ---------------------------------------


def test_infer_structural_type_recognises_task(ci, issue_types) -> None:
    assert ci._infer_structural_type("[Task] x", issue_types) == "task"


def test_infer_structural_type_returns_none_for_unknown(ci, issue_types) -> None:
    assert ci._infer_structural_type("Plain", issue_types) is None


# --- parent-chain walking --------------------------------------------


def test_walk_parent_chain_extracts_first_parent_ref(ci) -> None:
    body = "Feature: #42\n\nbody"
    assert ci._walk_parent_chain(body) == [42]


def test_walk_parent_chain_returns_empty_when_no_ref(ci) -> None:
    body = "## What\nno parent ref here."
    assert ci._walk_parent_chain(body) == []


def test_walk_parent_chain_returns_empty_for_empty_body(ci) -> None:
    assert ci._walk_parent_chain("") == []


# ---- _find_open_children (cascade-eligibility, issue #118) -----------------


def _fake_gh_list(ci, monkeypatch, rows, *, returncode=0) -> None:
    """Patch the module's gh_run so _find_open_children sees `rows`."""
    import json
    from subprocess import CompletedProcess

    def fake_gh_run(cmd, config, *, check=True, **kwargs):
        return CompletedProcess(cmd, returncode, json.dumps(rows), "")

    monkeypatch.setattr(ci, "gh_run", fake_gh_run)


def test_find_open_children_returns_only_open_children_of_parent(ci, monkeypatch) -> None:
    rows = [
        {"number": 10, "state": "OPEN", "body": "Feature: #5\n\n## What"},
        {"number": 11, "state": "CLOSED", "body": "Feature: #5\n\n## What"},
        {"number": 12, "state": "OPEN", "body": "Feature: #99\n\n## What"},
        {"number": 5, "state": "OPEN", "body": "no parent ref"},
        {"number": 13, "state": "OPEN", "body": "## What\nno ref"},
    ]
    _fake_gh_list(ci, monkeypatch, rows)
    assert ci._find_open_children(5, {}) == [10]


def test_find_open_children_empty_when_all_children_closed(ci, monkeypatch) -> None:
    rows = [
        {"number": 10, "state": "CLOSED", "body": "Feature: #5"},
        {"number": 11, "state": "CLOSED", "body": "Feature: #5"},
    ]
    _fake_gh_list(ci, monkeypatch, rows)
    assert ci._find_open_children(5, {}) == []


def test_find_open_children_returns_none_on_gh_failure(ci, monkeypatch) -> None:
    _fake_gh_list(ci, monkeypatch, [], returncode=1)
    assert ci._find_open_children(5, {}) is None


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
    derive_map = axis_labels.SubstrateMap(
        axes={"state": {"derive": {"from": "open-closed"}}}
    )
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
    remove_labels = [
        cmd[i + 1] for i, arg in enumerate(cmd) if arg == "--remove-label"
    ]
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
    remove_labels = {
        cmd[i + 1] for i, arg in enumerate(cmd) if arg == "--remove-label"
    }
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
# _gh_get_issue (monkeypatched on the module) to confirm no NameError.


def test_check_parent_eligibility_not_eligible_unticked_boxes(ci, monkeypatch) -> None:
    """Regression #65 — not-eligible branch completes without NameError.

    Parent is open with unticked checkboxes: eligibility report prints the
    'not eligible' line and returns without raising.
    """
    fake_parent = {
        "state": "open",
        "body": "- [ ] unfinished thing\n- [x] done thing\n",
    }
    monkeypatch.setattr(ci, "_gh_get_issue", lambda num, cfg: fake_parent)
    # Must not raise; return value is None (procedure).
    result = ci._check_parent_eligibility(59, config={})
    assert result is None


def test_check_parent_eligibility_eligible_all_boxes_ticked(ci, monkeypatch) -> None:
    """Regression #65 — eligible branch completes without NameError.

    Parent is open with all checkboxes ticked: eligibility report prints the
    'eligible to close' line and returns without raising.
    """
    fake_parent = {
        "state": "open",
        "body": "- [x] finished thing\n- [x] another done thing\n",
    }
    monkeypatch.setattr(ci, "_gh_get_issue", lambda num, cfg: fake_parent)
    result = ci._check_parent_eligibility(59, config={})
    assert result is None


def test_check_parent_eligibility_already_closed(ci, monkeypatch) -> None:
    """Regression #65 — already-closed parent branch completes without NameError."""
    fake_parent = {"state": "closed", "body": ""}
    monkeypatch.setattr(ci, "_gh_get_issue", lambda num, cfg: fake_parent)
    result = ci._check_parent_eligibility(59, config={})
    assert result is None
