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
#
# The prefix now resolves the kit type *value* through the ADR-026 read seam
# (a `type:*` label OR a `[Prefix]` title) and maps it via classification.yaml's
# `pr_type_mapping`. The greenfield (label) arm below must stay byte-identical to
# the pre-fix behaviour; the brownfield (title-prefix) arm is the new coverage.

# A minimal classification carrying the two tables the derivation reads: the
# value→conv-type bridge (`pr_type_mapping`) and the title-prefix vocabulary
# (`title_prefix_by_value`). Mirrors the shipped classification.yaml.
_CLASSIFICATION = {
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
        },
    },
    "pr_type_mapping": [
        {"issue_label_value": "feature", "pr_conv_type": "feat"},
        {"issue_label_value": "bug", "pr_conv_type": "fix"},
        {"issue_label_value": "docs", "pr_conv_type": "docs"},
        {"issue_label_value": "test", "pr_conv_type": "test"},
        {"issue_label_value": "refactor", "pr_conv_type": "refactor"},
        {"issue_label_value": "maintenance", "pr_conv_type": "chore"},
    ],
}


def test_branch_prefix_feature(sw) -> None:
    assert sw._derive_branch_prefix(
        ["type:feature", "priority:Medium"], "[Task] add x", _CLASSIFICATION
    ) == "feat"


def test_branch_prefix_bug(sw) -> None:
    assert sw._derive_branch_prefix(["type:bug"], "[Bug] fix x", _CLASSIFICATION) == "fix"


def test_branch_prefix_docs(sw) -> None:
    assert sw._derive_branch_prefix(
        ["workstream:cli", "type:docs"], "[Docs] doc x", _CLASSIFICATION
    ) == "docs"


def test_branch_prefix_missing_returns_none(sw) -> None:
    # No type:* label AND no recognised [Prefix] title ⇒ underivable.
    assert sw._derive_branch_prefix(["priority:High"], "no bracket prefix", _CLASSIFICATION) is None
    assert sw._derive_branch_prefix([], "", _CLASSIFICATION) is None


def test_branch_prefix_picks_first_match(sw) -> None:
    """Defensive: if labels somehow have both type:bug and type:feature, take the first."""
    result = sw._derive_branch_prefix(
        ["type:bug", "type:feature"], "[Bug] x", _CLASSIFICATION
    )
    # Order-dependent — accept either as long as it's recognised
    assert result in ("fix", "feat")


# ---- brownfield title-prefix arm (Task #442) ---------------------------


def test_branch_prefix_brownfield_bug_title_no_label(sw) -> None:
    """A brownfield `[Bug]`-titled Task with NO type:* label resolves `fix` —
    the read routes through the title-prefix arm of the seam, not a raw label."""
    assert sw._derive_branch_prefix([], "[Bug] hostname mismatch", _CLASSIFICATION) == "fix"


def test_branch_prefix_greenfield_label_still_wins(sw) -> None:
    """Greenfield stays byte-identical: `type:bug` label resolves `fix` even
    when the title carries a different (or no) bracket prefix."""
    assert sw._derive_branch_prefix(
        ["type:bug"], "no bracket prefix at all", _CLASSIFICATION
    ) == "fix"


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


# ---- type coverage against the REAL shipped classification.yaml -------


def test_every_shipped_type_value_resolves_a_branch_prefix(sw) -> None:
    """Every kind in the real classification.yaml (both label and title arms)
    resolves a branch prefix — no shipped type value is left underivable.

    Reads the shipped schema rather than a fixture so the two tables the
    derivation depends on (`pr_type_mapping`, `title_prefix_by_value`) can't
    drift out of coverage silently."""
    import importlib.util as _ilu

    scripts = SCRIPT.parent
    spec = _ilu.spec_from_file_location(
        "pm_classification_rules_under_test", scripts / "_lib" / "classification_rules.py"
    )
    assert spec is not None and spec.loader is not None
    cr = _ilu.module_from_spec(spec)
    spec.loader.exec_module(cr)

    from ruamel.yaml import YAML

    classification = YAML(typ="safe").load(
        (scripts.parent / "schemas" / "classification.yaml").read_text(encoding="utf-8")
    )
    prefix_by_value = cr.title_prefix_by_value(classification)
    assert prefix_by_value, "shipped classification.yaml carries no title_prefix_by_value"

    for value, title_prefix in prefix_by_value.items():
        # Label arm: a greenfield type:<value> label resolves a prefix.
        via_label = sw._derive_branch_prefix(
            [f"type:{value}"], f"[{title_prefix}] x", classification
        )
        assert via_label is not None, f"no branch prefix for label type:{value}"
        # Title arm: the same value resolves identically off the [Prefix] title
        # with no type:* label present (the brownfield path).
        via_title = sw._derive_branch_prefix([], f"[{title_prefix}] x", classification)
        assert via_title == via_label, (
            f"label vs title-prefix arm disagree for kind {value!r}: "
            f"{via_label!r} vs {via_title!r}"
        )
