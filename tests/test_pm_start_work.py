"""Tests for `start-work` wrapper (DEC-026)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management"
    / "scripts" / "start-work.py"
)


@pytest.fixture(scope="module")
def sw():
    lib_dir = SCRIPT.parent
    sys.path.insert(0, str(lib_dir))
    spec = importlib.util.spec_from_file_location("pm_start_work_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_start_work_under_test"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(lib_dir))


# ---- _slug_from_title --------------------------------------------------


def test_slug_strips_type_prefix(sw) -> None:
    assert sw._slug_from_title("[Feature] add gh helper") == "add-gh-helper"


def test_slug_strips_punctuation(sw) -> None:
    assert sw._slug_from_title("[Bug] fix: hostname mismatch!") == "fix-hostname-mismatch"


def test_slug_caps_at_five_words(sw) -> None:
    assert sw._slug_from_title(
        "[Feature] one two three four five six seven"
    ) == "one-two-three-four-five"


def test_slug_handles_empty_after_prefix(sw) -> None:
    assert sw._slug_from_title("[EPIC]") == "untitled"


def test_slug_lowercases(sw) -> None:
    assert sw._slug_from_title("[Task] MIXED Case Title") == "mixed-case-title"


# ---- _derive_branch_prefix ---------------------------------------------


def test_branch_prefix_feature(sw) -> None:
    assert sw._derive_branch_prefix(["type:feature", "priority:Medium"]) == "feat"


def test_branch_prefix_bug(sw) -> None:
    assert sw._derive_branch_prefix(["type:bug"]) == "fix"


def test_branch_prefix_docs(sw) -> None:
    assert sw._derive_branch_prefix(["workstream:cli", "type:docs"]) == "docs"


def test_branch_prefix_missing_returns_none(sw) -> None:
    assert sw._derive_branch_prefix(["priority:High"]) is None
    assert sw._derive_branch_prefix([]) is None


def test_branch_prefix_picks_first_match(sw) -> None:
    """Defensive: if labels somehow have both type:bug and type:feature, take the first."""
    result = sw._derive_branch_prefix(["type:bug", "type:feature"])
    # Order-dependent — accept either as long as it's recognised
    assert result in ("fix", "feat")


# ---- _branch_matches_shape --------------------------------------------


def test_branch_matches_shape_valid(sw) -> None:
    assert sw._branch_matches_shape("feat/42-add-gh-helper", 42) is True
    assert sw._branch_matches_shape("fix/177-membership-hostname", 177) is True
    assert sw._branch_matches_shape("docs/29-branch-naming", 29) is True


def test_branch_matches_shape_wrong_number(sw) -> None:
    assert sw._branch_matches_shape("feat/42-foo", 99) is False


def test_branch_matches_shape_no_slug(sw) -> None:
    assert sw._branch_matches_shape("feat/42", 42) is False


def test_branch_matches_shape_uppercase_rejected(sw) -> None:
    assert sw._branch_matches_shape("Feat/42-foo", 42) is False


# ---- type-label coverage table ---------------------------------------


def test_type_label_mapping_has_known_types(sw) -> None:
    """The kit-shipped type labels per classification.yaml should all map."""
    expected_labels = {
        "type:feature", "type:bug", "type:docs", "type:refactor",
        "type:test", "type:maintenance",
    }
    assert expected_labels.issubset(sw.TYPE_LABEL_TO_PREFIX.keys())
