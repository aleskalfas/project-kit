"""Tests for `_lib.criteria` — criterion extraction parity + checkbox rewrite.

The index numbering check-criterion uses MUST match what
`show-issue --field criteria` shows (DEC-038 correctness property). These tests
pin that parity directly against `show-issue._extract_criteria`, plus the
line/checkbox metadata and the narrow checkbox-marker rewrite.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"


@pytest.fixture(scope="module", autouse=True)
def _scripts_on_path():
    sys.path.insert(0, str(SCRIPTS))
    yield
    sys.path.remove(str(SCRIPTS))


@pytest.fixture(scope="module")
def crit(_scripts_on_path):
    from _lib import criteria

    return criteria


@pytest.fixture(scope="module")
def show_issue(_scripts_on_path):
    spec = importlib.util.spec_from_file_location(
        "pm_show_issue_for_parity", SCRIPTS / "show-issue.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- parity with show-issue._extract_criteria ------------------------------

PARITY_BODIES = [
    "## Acceptance criteria\n- [ ] alpha\n- [x] beta\n",
    "## Acceptance criteria\n- [ ] alpha\n- a plain bullet\n- [x] beta\n- [ ]\n",
    "Feature: #1\n\n## What\nx\n\n## Acceptance criteria\n"
    "- [ ] one\n- [x] two\n\n## Doc impact\n- not a criterion\n",
    "## What\n- not criteria\n",  # no acceptance-criteria section
    "## Acceptance criteria\n- [ ]\n- [ ] real one\n",  # bare skeleton excluded
]


@pytest.mark.parametrize("body", PARITY_BODIES)
def test_text_sequence_matches_show_issue(crit, show_issue, body) -> None:
    mine = [c.text for c in crit.extract_criteria(body)]
    theirs = show_issue._extract_criteria(body)
    assert mine == theirs


# --- metadata --------------------------------------------------------------


def test_index_is_one_based_and_dense(crit) -> None:
    body = "## Acceptance criteria\n- [ ] a\n- [x] b\n- [ ] c\n"
    items = crit.extract_criteria(body)
    assert [c.index for c in items] == [1, 2, 3]


def test_checkbox_state_and_kind(crit) -> None:
    body = "## Acceptance criteria\n- [ ] unchecked\n- [x] checked\n- plain\n"
    items = crit.extract_criteria(body)
    assert (items[0].is_checkbox, items[0].checked) == (True, False)
    assert (items[1].is_checkbox, items[1].checked) == (True, True)
    assert (items[2].is_checkbox, items[2].checked) == (False, False)


def test_uppercase_x_reads_as_checked(crit) -> None:
    body = "## Acceptance criteria\n- [X] done\n"
    assert crit.extract_criteria(body)[0].checked is True


def test_line_no_points_at_source_line(crit) -> None:
    body = "## Acceptance criteria\n- [ ] first\n- [x] second\n"
    items = crit.extract_criteria(body)
    lines = body.splitlines()
    assert lines[items[0].line_no] == "- [ ] first"
    assert lines[items[1].line_no] == "- [x] second"


# --- set_checkbox_state ----------------------------------------------------


def test_set_checkbox_state_ticks(crit) -> None:
    assert crit.set_checkbox_state("- [ ] foo", checked=True) == "- [x] foo"


def test_set_checkbox_state_unticks(crit) -> None:
    assert crit.set_checkbox_state("- [x] foo", checked=False) == "- [ ] foo"


def test_set_checkbox_state_preserves_indentation_and_text(crit) -> None:
    assert (
        crit.set_checkbox_state("   - [ ] nested item  ", checked=True)
        == "   - [x] nested item  "
    )


def test_set_checkbox_state_only_first_marker(crit) -> None:
    # A criterion whose text mentions another `[ ]` must not have the text mutated.
    line = "- [ ] consider the [ ] placeholder"
    assert crit.set_checkbox_state(line, checked=True) == "- [x] consider the [ ] placeholder"
