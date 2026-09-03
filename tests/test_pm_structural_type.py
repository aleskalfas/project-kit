"""The shared structural-type resolver (#793).

Before this module the resolver existed nine times across seven divergent
bodies, so the same title resolved differently depending on which command you
asked. These tests pin the union of behaviours the variants collectively had,
plus the defect that motivated the extraction: a kind-prefixed Task
(`[Docs] …`) resolved under `move-issue` and returned nothing under
`show-issue`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parents[1]
CAPABILITY_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
sys.path.insert(0, str(CAPABILITY_ROOT / "scripts"))

from _lib.structural_type import (  # noqa: E402
    infer_structural_type,
    structural_type_from_kind_label,
)


def _schema(name: str) -> dict:
    return YAML(typ="safe").load((CAPABILITY_ROOT / "schemas" / name).read_text())


@pytest.fixture(scope="module")
def issue_types() -> dict:
    return _schema("issue-types.yaml")


@pytest.fixture(scope="module")
def classification() -> dict:
    return _schema("classification.yaml")


# ---- structural prefixes (every variant had these) -------------------------


@pytest.mark.parametrize(
    "title,expected",
    [
        ("[EPIC] Modularity, configuration and extension", "epic"),
        ("[Feature] Third-party content packaging", "feature"),
        ("[Umbrella] Extract duplicated helpers", "umbrella"),
        ("[Task] Re-parent an issue", "task"),
    ],
)
def test_kit_structural_prefixes_resolve(title, expected, issue_types) -> None:
    assert infer_structural_type(title, issue_types) == expected


def test_unprefixed_title_resolves_to_nothing(issue_types) -> None:
    assert infer_structural_type("Plain title", issue_types) is None


# ---- kind prefixes — the defect #793 was filed for -------------------------


@pytest.mark.parametrize(
    "title",
    [
        "[Bug] Title guidance misleads and its declared checks never run",
        "[Docs] Explore pkit's minimum install surface",
        "[Test] Add coverage for the resolver",
        "[Refactor] Extract the shared helper",
        "[Chore] Register methodology-reviewer as a baseline local reviewer",
    ],
)
def test_kind_prefixed_tasks_resolve_when_classification_is_supplied(
    title, issue_types, classification
) -> None:
    """The regression: these read as `<unrecognised prefix>` before #793."""
    assert (
        infer_structural_type(title, issue_types, classification=classification)
        == "task"
    )


@pytest.mark.parametrize("title", ["[Bug] x", "[Docs] y", "[Chore] z"])
def test_kind_prefixes_are_opt_in_so_extraction_preserved_behaviour(
    title, issue_types
) -> None:
    """Omitting `classification` reproduces the prefix-only variants exactly.

    This is what made wiring nine call sites through one implementation
    behaviour-preserving: a caller that passes nothing extra gets what it had.
    """
    assert infer_structural_type(title, issue_types) is None


# ---- label fallback --------------------------------------------------------


def test_label_recovers_task_when_the_prefix_was_edited_away(
    issue_types, classification
) -> None:
    assert (
        infer_structural_type(
            "prefix removed by hand",
            issue_types,
            classification=classification,
            labels=["type:bug"],
        )
        == "task"
    )


def test_prefix_wins_over_a_contradicting_label(issue_types, classification) -> None:
    assert (
        infer_structural_type(
            "[EPIC] Big thesis",
            issue_types,
            classification=classification,
            labels=["type:bug"],
        )
        == "epic"
    )


def test_feature_kind_is_ambiguous_so_recovers_nothing(classification) -> None:
    """`feature` maps to several structural types, so it cannot disambiguate."""
    assert structural_type_from_kind_label(["type:feature"], classification) is None


def test_label_fallback_needs_both_labels_and_classification(issue_types) -> None:
    assert infer_structural_type("no prefix", issue_types, labels=["type:bug"]) is None


# ---- brownfield: the substrate map short-circuits --------------------------


def test_substrate_map_binding_type_elsewhere_yields_nothing(issue_types) -> None:
    """A map binding `type` to labels means the type is not title-carried.

    It must NOT fall through to the kit vocabulary — that was `validate-issue`'s
    deliberate strictness, and collapsing it would have been a silent
    behaviour change during extraction.
    """

    class _Map:
        pass

    import _lib.axis_labels as axis_labels

    original = axis_labels.axis_title_prefix_remap
    axis_labels.axis_title_prefix_remap = lambda axis, m: None
    try:
        assert infer_structural_type("[EPIC] x", issue_types, substrate_map=_Map()) is None
    finally:
        axis_labels.axis_title_prefix_remap = original
