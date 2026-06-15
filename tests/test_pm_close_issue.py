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
    NON_TERMINAL_STATE_LABELS,
    TERMINAL_STATE_LABEL,
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


def test_reconcile_constants_are_correct() -> None:
    """The non-terminal set and the terminal label match the workflow states."""
    assert TERMINAL_STATE_LABEL == "state:done"
    assert set(NON_TERMINAL_STATE_LABELS) == {
        "state:todo",
        "state:backlog",
        "state:in-progress",
        "state:review",
    }


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
