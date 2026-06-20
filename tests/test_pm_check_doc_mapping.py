"""Tests for project-management's check-doc-mapping pure logic (DEC-015 + ADR-019).

Covers the bug-prone parts: the gitignore-style glob matcher (recursive `**`
semantics) and the `## Doc impact` override-section parser. The main() flow
(git diff + gh + config) is integration-shaped and exercised via the script's
own exit-code contract; here we pin the matching/parsing units.
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
    / "check-doc-mapping.py"
)
LIB_PATH = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
sys.path.insert(0, str(LIB_PATH))


@pytest.fixture(scope="module")
def cdm():
    spec = importlib.util.spec_from_file_location(
        "pm_check_doc_mapping_under_test", SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_check_doc_mapping_under_test"] = module
    spec.loader.exec_module(module)
    return module


# --- glob matching (_matches) ----------------------------------------------


def test_matches_exact_file(cdm) -> None:
    assert cdm._matches("a/b.py", "a/b.py")
    assert not cdm._matches("a/b.py", "a/c.py")


def test_matches_recursive_double_star(cdm) -> None:
    # ** must recurse across directory separators (the fnmatch trap).
    assert cdm._matches("src/**", "src/a/b/c.py")
    assert cdm._matches("src/**", "src/x.py")
    assert not cdm._matches("src/**", "other/x.py")


def test_matches_single_star_is_one_segment(cdm) -> None:
    assert cdm._matches("src/*.py", "src/a.py")
    assert not cdm._matches("src/*.py", "src/a/b.py")


def test_matches_nested_tree_glob(cdm) -> None:
    assert cdm._matches(
        ".pkit/capabilities/project-management/**",
        ".pkit/capabilities/project-management/scripts/x.py",
    )
    assert not cdm._matches(
        ".pkit/capabilities/project-management/**",
        ".pkit/capabilities/evidence/x.py",
    )


# --- doc-impact override parsing (_doc_impact_section) ----------------------


def test_doc_impact_section_extracts_bounded_lowercased(cdm) -> None:
    body = (
        "## Summary\nstuff\n\n"
        "## Doc impact\n- registry.ts: internal reorder, no command added\n\n"
        "## Test plan\n- [x] ok"
    )
    section = cdm._doc_impact_section(body)
    assert "registry.ts: internal reorder" in section
    assert "summary" not in section  # bounded — earlier section excluded
    assert "test plan" not in section  # bounded — later section excluded


def test_doc_impact_section_empty_when_heading_absent(cdm) -> None:
    assert cdm._doc_impact_section("## Summary\nno doc-impact heading here") == ""


def test_doc_impact_section_empty_for_empty_body(cdm) -> None:
    assert cdm._doc_impact_section("") == ""


def test_doc_impact_section_carries_path_for_override_match(cdm) -> None:
    # The override check in main() asks whether a triggering path appears in the
    # (lowercased) section; verify a path survives extraction.
    body = "## Doc impact\n- packages/cli/src/commands/registry.ts: internal only"
    section = cdm._doc_impact_section(body)
    assert "packages/cli/src/commands/registry.ts" in section
