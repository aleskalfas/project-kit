"""The first-line parent-ref parser shared by create-issue and link-parent (#1033).

`_lib/body_parent_ref` is the one reading of "which parent does this body's first
line name": create-issue's first-line check and derived native link, and
link-parent's repair, all go through it. These pin the reading against the REAL
shipped `parent_ref_form`s, so a schema edit that changes what a type may name
is caught here rather than as a wrong link.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITY = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS = CAPABILITY / "scripts"


@pytest.fixture(scope="module")
def bpr():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    from _lib import body_parent_ref

    return body_parent_ref


@pytest.fixture(scope="module")
def forms() -> dict[str, str]:
    """Each shipped type's `parent_ref_form`."""
    data = YAML(typ="safe").load(
        (CAPABILITY / "schemas" / "issue-types.yaml").read_text(encoding="utf-8")
    )
    return {name: str(entry["parent_ref_form"]) for name, entry in data["types"].items()}


@pytest.mark.parametrize(
    ("line", "label", "number"),
    [("Feature: #12", "Feature", 12), ("Umbrella: #13", "Umbrella", 13), ("EPIC: #14", "EPIC", 14)],
)
def test_an_issue_parent_is_read_with_its_number(bpr, forms, line, label, number) -> None:
    ref = bpr.parse_first_line(f"{line}\n\n## What\n", forms["task"])
    assert ref is not None
    assert (ref.label, ref.number, ref.milestone) == (label, number, False)
    assert ref.issue_number == number


def test_a_milestone_parent_names_no_issue(bpr, forms) -> None:
    ref = bpr.parse_first_line("Milestone: [#5](../milestone/5)\n", forms["task"])
    assert ref is not None
    assert ref.milestone is True
    assert ref.number == 5
    assert ref.issue_number is None


def test_a_milestone_link_whose_text_and_target_differ_is_not_a_ref(bpr, forms) -> None:
    assert bpr.parse_first_line("Milestone: [#5](../milestone/6)\n", forms["task"]) is None


def test_only_the_forms_the_type_allows_are_read(bpr, forms) -> None:
    """An EPIC's only parent form is a milestone, so a `Feature:` first line is
    not a parent-ref for an EPIC — it must never become an EPIC-under-Feature link."""
    assert bpr.parse_first_line("Feature: #12\n", forms["epic"]) is None
    assert bpr.parse_first_line("Feature: #12\n", forms["feature"]) is None
    assert bpr.parse_first_line("EPIC: #14\n", forms["feature"]).number == 14


def test_the_first_line_skips_blank_lines_and_the_integration_marker(bpr, forms) -> None:
    body = "\n\nIntegration: integration/big-change\nFeature: #12\n\n## What\n"
    assert bpr.first_line(body) == "Feature: #12"
    assert bpr.parse_first_line(body, forms["task"]).number == 12


@pytest.mark.parametrize(
    "body",
    [
        "",
        "## What\n\nFeature: #12\n",  # a ref below the first line is not the parent-ref
        "Feature: 12\n",  # the `#` is part of the form
        "Feature: #12 and more\n",
        "Blocked by: #12\n",  # not a label any type's form uses
    ],
)
def test_anything_else_is_no_parent_ref(bpr, forms, body) -> None:
    assert bpr.parse_first_line(body, forms["task"]) is None


def test_form_matchers_accept_exactly_what_parse_reads(bpr, forms) -> None:
    """The filing check (matchers) and the link (parse) agree line for line."""
    matchers = bpr.form_matchers(forms["task"])
    for line in ("Feature: #1", "Umbrella: #2", "EPIC: #3", "Milestone: [#4](../milestone/4)",
                 "Feature: 1", "prose"):
        accepted = any(m.match(line) for m in matchers)
        assert accepted == (bpr.parse_first_line(line, forms["task"]) is not None), line


# --- a milestone first line follows a milestone move (#1049) -------------


@pytest.mark.parametrize(
    "body,expected",
    [
        ("Milestone: [#5](../milestone/5)\n\n## What\n", 5),
        ("Milestone: #5\n\n## What\n", 5),  # the deprecated plain form
        ("Integration: integration/big-thing\nMilestone: [#5](../milestone/5)\n", 5),
        ("EPIC: #10\n\n## What\n", None),
        ("## What\nMilestone: [#5](../milestone/5)\n", None),  # not the first line
    ],
)
def test_first_line_milestone(bpr, body, expected) -> None:
    assert bpr.first_line_milestone(body) == expected


def test_set_first_line_milestone_retargets_in_place(bpr) -> None:
    body = "Milestone: #5\n\n## What\nx\n"
    assert bpr.set_first_line_milestone(body, 6) == "Milestone: [#6](../milestone/6)\n\n## What\nx\n"


def test_set_first_line_milestone_keeps_the_integration_marker(bpr) -> None:
    body = "Integration: integration/big-thing\nMilestone: [#5](../milestone/5)\n\n## What\n"
    assert bpr.set_first_line_milestone(body, 6) == (
        "Integration: integration/big-thing\nMilestone: [#6](../milestone/6)\n\n## What\n"
    )


def test_set_first_line_milestone_removes_the_line_and_its_blank(bpr) -> None:
    assert bpr.set_first_line_milestone("Milestone: [#5](../milestone/5)\n\n## Thesis\n", None) == (
        "## Thesis\n"
    )


def test_set_first_line_milestone_leaves_an_issue_parent_alone(bpr) -> None:
    body = "EPIC: #10\n\n## What\n"
    assert bpr.set_first_line_milestone(body, 6) == body
    assert bpr.set_first_line_milestone(body, None) == body
