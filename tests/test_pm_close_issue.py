"""Tests for project-management's close-issue script's pure logic.

Covers checkbox gate detection (`_unticked_boxes`, `_all_boxes_ticked`),
structural-type inference, and parent-chain walking.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

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
