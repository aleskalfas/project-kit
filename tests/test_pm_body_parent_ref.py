"""The first-line parent-ref parser shared by create-issue, link-parent and the
cascades (#1033, #1230).

`_lib/body_parent_ref` is the one reading of "which parent does this body's first
line name": create-issue's first-line check and derived native link,
link-parent's repair, and the step move-issue's forward cascade and close-issue's
closure cascade take up to a parent, all go through it. These pin the reading against the REAL
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
    for line in (
        "Feature: #1",
        "Umbrella: #2",
        "EPIC: #3",
        "Milestone: [#4](../milestone/4)",
        "Feature: 1",
        "prose",
    ):
        accepted = any(m.match(line) for m in matchers)
        assert accepted == (bpr.parse_first_line(line, forms["task"]) is not None), line


def test_every_shipped_type_may_name_a_milestone(bpr, forms) -> None:
    """#1016: which types may sit under a milestone is read from the shipped
    forms — all four offer the milestone line, an EPIC's being optional."""
    assert {name for name, form in forms.items() if bpr.form_allows_milestone(form)} == {
        "epic",
        "feature",
        "umbrella",
        "task",
    }
    assert not bpr.form_allows_milestone("Feature: #<N>")


# --- the parent issue a cascade walks to (#1230) --------------------------


@pytest.fixture(scope="module")
def issue_types() -> dict:
    """The shipped `issue-types.yaml`."""
    return YAML(typ="safe").load(
        (CAPABILITY / "schemas" / "issue-types.yaml").read_text(encoding="utf-8")
    )


@pytest.mark.parametrize(
    ("structural_type", "body", "parent"),
    [
        ("task", "Feature: #42\n\n## What\nfoo", 42),
        ("task", "Umbrella: #5\n", 5),
        ("task", "\n\nEPIC: #99\n\nbody", 99),
        ("feature", "EPIC: #99\n", 99),
        ("umbrella", "Umbrella: #7\n", 7),
        ("task", "Integration: integration/508-multi-instance-ownership\nEPIC: #508\n", 508),
        ("task", "## What\nno parent ref", None),
        ("task", "", None),
        ("task", "Milestone: [#3](../milestone/3)\n", None),
    ],
)
def test_a_typed_issue_names_the_parent_its_forms_allow(
    bpr, issue_types, structural_type, body, parent
) -> None:
    assert bpr.parent_issue(body, structural_type, issue_types) == parent


@pytest.mark.parametrize(
    "body", ["Milestone: [#5](../milestone/5)\n\n## Thesis\n", "Milestone: #5\n\n## Thesis\n"]
)
def test_an_epic_under_a_milestone_is_the_top_of_the_walk(bpr, issue_types, body) -> None:
    """A milestone is not an issue: an EPIC whose first line names one, in either
    form, has no parent issue, so issue #5 is never taken for its parent."""
    assert bpr.parent_issue(body, "epic", issue_types) is None


@pytest.mark.parametrize("structural_type", ["task", "feature", "umbrella", "epic"])
@pytest.mark.parametrize("line", ["Related: #45", "Supersedes: #3", "Blocked by: #12"])
def test_a_typed_issue_does_not_follow_a_line_that_is_no_parent_ref(
    bpr, issue_types, structural_type, line
) -> None:
    assert bpr.parent_issue(f"{line}\n\n## What\n", structural_type, issue_types) is None


def test_a_line_naming_a_parent_the_type_may_not_have_is_not_followed(bpr, issue_types) -> None:
    """An EPIC's only parent is a milestone and a Feature's an EPIC."""
    assert bpr.parent_issue("Feature: #12\n", "epic", issue_types) is None
    assert bpr.parent_issue("Feature: #12\n", "feature", issue_types) is None


@pytest.mark.parametrize(
    ("body", "parent"),
    [
        ("Feature: #42\n\n## What\n", 42),
        ("Related: #45\n", 45),  # read as an untyped tree always was
        ("Integration: integration/big-change\nEPIC: #8\n", 8),
        ("Milestone: [#5](../milestone/5)\n", None),
        ("Milestone: #5\n", None),
        ("## What\nEPIC: #8\n", None),
        ("", None),
    ],
)
def test_an_issue_whose_type_cannot_be_told_names_any_labelled_issue(
    bpr, issue_types, body, parent
) -> None:
    """A brownfield issue with no `[Type]` prefix and no `type:*` label: any
    `<Label>: #<N>` first line names its parent, a milestone ref in neither form."""
    assert bpr.parent_issue(body, None, issue_types) == parent
    # A type the schema declares no forms for reads the same way.
    assert bpr.parent_issue(body, "spike", {"types": {"spike": {}}}) == parent


@pytest.mark.parametrize(
    ("structural_type", "line"),
    [
        ("feature", "Epic: #5"),
        ("feature", "Feature: #12 — auth"),
        ("feature", "Task: #7"),
        ("feature", "EPIC:#5"),
        ("task", "Related: #45"),
        ("epic", "Feature: #12"),
    ],
)
def test_a_line_that_looks_like_a_parent_ref_but_is_not_an_allowed_form_is_said(
    bpr, issue_types, forms, structural_type, line
) -> None:
    """A cascade that finds no parent must not say the body names none: the
    line, and the forms the type allows, are quoted for it to say instead."""
    body = f"{line}\n\n## What\n"
    assert bpr.parent_issue(body, structural_type, issue_types) is None
    assert bpr.read_first_line(body, structural_type, issue_types).note == (
        f"first line `{line}` is not a parent-ref a {structural_type} may have: "
        f"{forms[structural_type]}"
    )


@pytest.mark.parametrize(
    ("structural_type", "body"),
    [
        ("feature", "EPIC: #5\n"),  # an allowed form
        ("feature", "Milestone: [#3](../milestone/3)\n"),
        ("epic", "Milestone: #3\n"),  # the deprecated milestone form ends the walk
        ("task", "## What\nFeature: #5\n"),  # names no parent at all
        ("task", ""),
        (None, "Epic: #5\n"),  # no type, so no forms to hold the line to
    ],
)
def test_a_line_with_nothing_to_say_about_it_is_not_said(
    bpr, issue_types, structural_type, body
) -> None:
    assert bpr.read_first_line(body, structural_type, issue_types).note is None


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
    assert (
        bpr.set_first_line_milestone(body, 6) == "Milestone: [#6](../milestone/6)\n\n## What\nx\n"
    )


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


# --- the one writer of an issue parent's first line (#1281) ---------------


@pytest.mark.parametrize(
    ("parent_type", "line"),
    [("epic", "EPIC: #9"), ("feature", "Feature: #9"), ("umbrella", "Umbrella: #9")],
)
def test_the_line_carries_the_parents_own_label(bpr, issue_types, forms, parent_type, line) -> None:
    label = bpr.type_label(issue_types, parent_type)
    assert bpr.issue_parent_line(forms["task"], 9, label) == bpr.ParentLine(line)


def test_a_feature_under_an_umbrella_names_it_an_umbrella(bpr, issue_types, forms) -> None:
    label = bpr.type_label(issue_types, "umbrella")
    assert bpr.issue_parent_line(forms["feature"], 9, label).line == "Umbrella: #9"


def test_a_parent_of_unknown_type_takes_the_first_form(bpr, forms) -> None:
    assert bpr.issue_parent_line(forms["task"], 9) == bpr.ParentLine("Feature: #9")


def test_a_parent_the_forms_do_not_offer_takes_the_first_form_with_a_warning(
    bpr, issue_types, forms
) -> None:
    written = bpr.issue_parent_line(forms["task"], 9, bpr.type_label(issue_types, "task"))
    assert written.line == "Feature: #9"
    assert written.warning == (
        f"`Task: #<N>` is not a parent-ref this type may have ({forms['task']}), so the "
        "first line names #9 as `Feature: #9`"
    )


def test_a_type_with_no_form_writes_no_line(bpr) -> None:
    assert bpr.issue_parent_line("", 9, "EPIC") == bpr.ParentLine("")


def test_an_undeclared_type_has_no_label(bpr, issue_types) -> None:
    assert bpr.type_label(issue_types, "spike") is None
