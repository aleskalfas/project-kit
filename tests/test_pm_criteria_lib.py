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
    # EPIC shape: checkboxes live under `## Success criteria` (body-format.yaml)
    "EPIC: #1\n\n## Outcome\nthesis\n\n## Success criteria\n"
    "- [ ] proven\n- [x] shipped\n",
]

# The schema-resolved heading set both sides must share for index parity.
SCHEMA_HEADINGS = frozenset({"acceptance criteria", "success criteria"})


@pytest.mark.parametrize("body", PARITY_BODIES)
def test_text_sequence_matches_show_issue(crit, show_issue, body) -> None:
    mine = [c.text for c in crit.extract_criteria(body, SCHEMA_HEADINGS)]
    theirs = show_issue._extract_criteria(body, SCHEMA_HEADINGS)
    assert mine == theirs


@pytest.mark.parametrize("body", PARITY_BODIES)
def test_text_sequence_matches_show_issue_on_fallback(crit, show_issue, body) -> None:
    # Bare calls (no heading set) keep the historical acceptance-criteria walk
    # on both sides (the EPIC body yields [] on both — parity still holds).
    mine = [c.text for c in crit.extract_criteria(body)]
    theirs = show_issue._extract_criteria(body)
    assert mine == theirs


# --- schema-driven heading resolution --------------------------------------


def test_checkbox_headings_collects_has_checkboxes_sections(crit) -> None:
    body_format = {
        "bodies": {
            "epic": {
                "required_sections": [
                    {"heading": "## Outcome", "has_checkboxes": False},
                    {"heading": "## Success criteria", "has_checkboxes": True},
                ],
            },
            "feature": {
                "required_sections": [
                    {"heading": "## What", "has_checkboxes": False},
                    {"heading": "## Acceptance criteria", "has_checkboxes": True},
                ],
            },
        },
    }
    assert crit.checkbox_headings(body_format) == SCHEMA_HEADINGS


def test_checkbox_headings_from_real_schema(crit) -> None:
    # body-format.yaml is the source of truth; the shipped schema must yield
    # both the EPIC and the Feature/Task criteria headings.
    from ruamel.yaml import YAML

    path = (
        REPO_ROOT
        / ".pkit"
        / "capabilities"
        / "project-management"
        / "schemas"
        / "body-format.yaml"
    )
    body_format = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    headings = crit.checkbox_headings(body_format)
    assert "success criteria" in headings
    assert "acceptance criteria" in headings


@pytest.mark.parametrize("body_format", [{}, {"bodies": {}}, {"bodies": None}])
def test_checkbox_headings_falls_back_when_schema_empty(crit, body_format) -> None:
    # Unreadable/missing schema reaches the resolver as an empty mapping
    # (the callers' loaders fail-open to {}); the fallback is the historical
    # hardcoded literal, so the primitives never get worse than before.
    assert crit.checkbox_headings(body_format) == crit.FALLBACK_HEADINGS
    assert frozenset({"acceptance criteria"}) == crit.FALLBACK_HEADINGS


def test_epic_success_criteria_extracted_with_schema_headings(crit) -> None:
    body = "EPIC: #1\n\n## Outcome\nthesis\n\n## Success criteria\n- [ ] a\n- [x] b\n"
    items = crit.extract_criteria(body, SCHEMA_HEADINGS)
    assert [(c.index, c.text, c.checked) for c in items] == [
        (1, "a", False),
        (2, "b", True),
    ]


def test_epic_success_criteria_invisible_on_fallback(crit) -> None:
    # Without the schema-resolved set the historical behaviour holds: only
    # `## Acceptance criteria` is scanned.
    body = "## Success criteria\n- [ ] a\n"
    assert crit.extract_criteria(body) == []


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
