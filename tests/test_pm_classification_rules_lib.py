"""Tests for `_lib.classification_rules` — the single kind ↔ structural reader.

The DEC-011 hard-reject table (`allowed_structural_types_per_kind`) is read here
and only here for the consistency check; create-issue / validate-issue / set-field
all call these predicates. These pin the permit/refuse matrix, the kind-drives-
title read, the severity-token pass-through, and the permissive degrade on a thin
classification.
"""

from __future__ import annotations

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
def cr(_scripts_on_path):
    from _lib import classification_rules

    return classification_rules


@pytest.fixture
def classification() -> dict:
    return {
        "axes": {
            "type": {
                "title_prefix_by_value": {
                    "feature": "Task",
                    "bug": "Bug",
                    "docs": "Docs",
                    "test": "Test",
                    "refactor": "Refactor",
                    "maintenance": "Chore",
                },
                "structural_restriction": {
                    "allowed_structural_types_per_kind": {
                        "feature": ["task", "feature", "umbrella", "epic"],
                        "bug": ["task"],
                        "docs": ["task"],
                        "test": ["task"],
                        "refactor": ["task"],
                        "maintenance": ["task"],
                    },
                    "mismatch_severity": "[validation-severity:hard-reject]",
                },
            }
        }
    }


# --- the permit/refuse matrix ----------------------------------------------


@pytest.mark.parametrize(
    "kind,structural,expected",
    [
        # feature is permitted on every structural type (its default kind).
        ("feature", "epic", True),
        ("feature", "feature", True),
        ("feature", "umbrella", True),
        ("feature", "task", True),
        # non-feature kinds are Task-only.
        ("bug", "task", True),
        ("docs", "task", True),
        ("refactor", "task", True),
        # non-feature kind on a cluster type is the DEC-011 hard-reject.
        ("bug", "epic", False),
        ("bug", "feature", False),
        ("docs", "umbrella", False),
        ("maintenance", "epic", False),
    ],
)
def test_permit_refuse_matrix(cr, classification, kind, structural, expected) -> None:
    assert (
        cr.kind_allowed_for_structural_type(kind, structural, classification)
        is expected
    )


def test_unknown_kind_absent_from_table_is_permitted(cr, classification) -> None:
    # A kind with no entry in the table has no declared restriction ⇒ permit.
    assert cr.kind_allowed_for_structural_type("wildcard", "epic", classification) is True


def test_empty_classification_degrades_permissive(cr) -> None:
    # No table to ground a refusal ⇒ permit (the gate refuses nothing it cannot
    # ground in the schema).
    assert cr.kind_allowed_for_structural_type("bug", "epic", {}) is True
    assert cr.kind_allowed_for_structural_type("bug", "epic", {"axes": {}}) is True


# --- kind-drives-title -----------------------------------------------------


def test_kind_drives_title_true_only_for_task(cr, classification) -> None:
    assert cr.kind_drives_title("task", classification) is True
    assert cr.kind_drives_title("epic", classification) is False
    assert cr.kind_drives_title("feature", classification) is False
    assert cr.kind_drives_title("umbrella", classification) is False


def test_kind_drives_title_false_on_empty_classification(cr) -> None:
    assert cr.kind_drives_title("task", {}) is False


# --- severity token pass-through -------------------------------------------


def test_mismatch_severity_token_returned(cr, classification) -> None:
    assert (
        cr.mismatch_severity_token(classification)
        == "[validation-severity:hard-reject]"
    )


def test_mismatch_severity_token_none_when_absent(cr) -> None:
    assert cr.mismatch_severity_token({}) is None
    assert cr.mismatch_severity_token({"axes": {"type": {}}}) is None


# --- table + prefix readers ------------------------------------------------


def test_allowed_structural_types_per_kind_read(cr, classification) -> None:
    table = cr.allowed_structural_types_per_kind(classification)
    assert table["bug"] == ["task"]
    assert set(table["feature"]) == {"task", "feature", "umbrella", "epic"}


def test_allowed_structural_types_per_kind_empty_when_absent(cr) -> None:
    assert cr.allowed_structural_types_per_kind({}) == {}


def test_title_prefix_by_value_read(cr, classification) -> None:
    assert cr.title_prefix_by_value(classification)["bug"] == "Bug"
    assert cr.title_prefix_by_value({}) == {}
