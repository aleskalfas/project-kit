"""Every containment `issue-types.yaml` allows has a first-line form (#1281).

The containment graph is written three times in the shipped schema: a type's
`can_contain`, a type's `parent_issue_types`, and the options of a type's
`parent_ref_form`. The edges are what a writer of a parent is held to
(`_lib/containment_graph`, #1313), and the forms are what every reader of an
issue's parent goes by — an edge the graph allows with no form to write it on a
first line ends every walk at that issue (a Feature under an Umbrella did).
These pin the three together, from either end, and the milestone edge with
them: a form has one option per issue-parent type
and the milestone option exactly where the type's container is a milestone —
`milestone` among its parents, or no issue parent at all (an EPIC).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITY = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS = CAPABILITY / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _lib import body_parent_ref  # noqa: E402

MILESTONE = "milestone"


def _issue_types() -> dict:
    return YAML(typ="safe").load(
        (CAPABILITY / "schemas" / "issue-types.yaml").read_text(encoding="utf-8")
    )


ISSUE_TYPES = _issue_types()
TYPES: dict[str, dict] = ISSUE_TYPES["types"]


def _form_labels(child: str) -> set[str]:
    """The labels of the issue-parent options of `child`'s form."""
    return {
        ref.label
        for line in (
            option.strip().replace("#<N>", "#1")
            for option in str(TYPES[child]["parent_ref_form"]).split(" or ")
        )
        if (ref := body_parent_ref.parse_first_line(line, TYPES[child]["parent_ref_form"]))
        and not ref.milestone
    }


def _label(parent: str) -> str:
    label = body_parent_ref.type_label(ISSUE_TYPES, parent)
    assert label is not None, parent
    return label


_CONTAINS = sorted((parent, child) for parent in TYPES for child in TYPES[parent]["can_contain"])
_SITS_UNDER = sorted(
    (parent, child)
    for child in TYPES
    for parent in TYPES[child]["parent_issue_types"]
    if parent != MILESTONE
)


@pytest.mark.parametrize(("parent", "child"), _CONTAINS)
def test_a_type_a_container_may_hold_may_sit_under_it_and_name_it(parent: str, child: str) -> None:
    assert parent in TYPES[child]["parent_issue_types"], (
        f"{parent} can_contain {child}, but {child}'s parent_issue_types lacks {parent}"
    )
    assert _label(parent) in _form_labels(child), (
        f"{parent} can_contain {child}, but {child}'s parent_ref_form has no "
        f"`{_label(parent)}: #<N>` option, so no first line can name the parent"
    )


@pytest.mark.parametrize(("parent", "child"), _SITS_UNDER)
def test_a_parent_a_type_may_sit_under_may_hold_it_and_is_named_by_it(
    parent: str, child: str
) -> None:
    assert child in TYPES[parent]["can_contain"], (
        f"{child} may sit under {parent}, but {parent}'s can_contain lacks {child}"
    )
    assert _label(parent) in _form_labels(child)


@pytest.mark.parametrize("child", sorted(TYPES))
def test_every_issue_label_in_a_form_names_a_parent_the_type_may_have(child: str) -> None:
    parents = {_label(p) for p in TYPES[child]["parent_issue_types"] if p != MILESTONE}
    assert _form_labels(child) <= parents, (
        f"{child}'s parent_ref_form names {sorted(_form_labels(child) - parents)}, "
        "which its parent_issue_types do not list"
    )


def _issue_parents(child: str) -> list[str]:
    return [p for p in TYPES[child]["parent_issue_types"] if p != MILESTONE]


def _container_is_a_milestone(child: str) -> bool:
    """`milestone` among the type's parents, or no issue parent at all — the top
    of the issue hierarchy, whose scheduling parent is a Milestone (an EPIC)."""
    return MILESTONE in TYPES[child]["parent_issue_types"] or not _issue_parents(child)


@pytest.mark.parametrize("child", sorted(TYPES))
def test_a_form_offers_the_milestone_exactly_where_the_container_is_a_milestone(
    child: str,
) -> None:
    offered = body_parent_ref.form_allows_milestone(str(TYPES[child]["parent_ref_form"]))
    expected = _container_is_a_milestone(child)
    assert offered is expected, (
        f"{child}'s parent_ref_form offers the milestone option: {offered}; its "
        f"parent_issue_types say its container is a milestone: {expected}"
    )


@pytest.mark.parametrize("child", sorted(TYPES))
def test_a_form_has_one_option_per_issue_parent_and_the_milestone_and_no_other(
    child: str,
) -> None:
    """Every option of the form is accounted for: one per issue-parent type, and
    one for the milestone where the container is a milestone — so the EPIC's
    lone milestone option and its empty `parent_issue_types` agree."""
    options = [o.strip() for o in str(TYPES[child]["parent_ref_form"]).split(" or ")]
    expected = len(_issue_parents(child)) + (1 if _container_is_a_milestone(child) else 0)
    assert len(options) == expected, (child, options)
    assert len(body_parent_ref.form_matchers(str(TYPES[child]["parent_ref_form"]))) == expected


def test_an_epics_container_is_a_milestone_and_its_form_names_no_issue() -> None:
    """The edge the issue-type graph leaves out: an EPIC has no issue parent, and
    its one form is the milestone's."""
    form = str(TYPES["epic"]["parent_ref_form"])
    assert TYPES["epic"]["parent_issue_types"] == []
    assert body_parent_ref.form_allows_milestone(form)
    assert not body_parent_ref.form_names_an_issue(form)
    assert _form_labels("epic") == set()


def test_a_feature_may_sit_under_an_umbrella() -> None:
    """The one edge the graph allowed with no form: an Umbrella holds Features."""
    assert "feature" in TYPES["umbrella"]["can_contain"]
    assert body_parent_ref.parent_issue("Umbrella: #7\n", "feature", ISSUE_TYPES) == 7
