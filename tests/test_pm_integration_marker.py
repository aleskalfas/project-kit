"""DEC-013 integration-marker read-side (#763).

The `Integration: integration/<slug>` marker is, per DEC-013, the FIRST body
line on a marked issue — above the parent-ref, with no blank line between. Every
parent-ref recognizer in the capability must therefore skip that marker before
reading the parent-ref off the first content line, or a marked descendant would
fail parent-ref recognition (the bug this file guards against).

The recognizers, all backed by `lifecycle_inference.strip_integration_marker`:
  - infer.parent_ref               (lifecycle_inference.py)
  - containment._body_names_parent (containment.py)
  - move-issue._walk_parent_chain  (exercised in test_pm_move_issue.py)
  - close-issue._walk_parent_chain (same helper)
  - validate-issue first_line      (exercised in test_pm_validate_issue.py)
  - create-issue first_line        (same helper)
  - show-tree._first_parent_ref    (same helper)
"""

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
LIB = SCRIPTS / "_lib"

MARKER = "Integration: integration/508-multi-instance-ownership"


def _load(name: str, path: Path):
    if str(LIB) not in sys.path:
        sys.path.insert(0, str(LIB))
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def infer():
    return _load("pm_lifecycle_inference_marker_ut", LIB / "lifecycle_inference.py")


@pytest.fixture(scope="module")
def containment():
    return _load("pm_containment_marker_ut", LIB / "containment.py")


# --- strip_integration_marker ----------------------------------------------


def test_strip_removes_the_marker_when_it_is_the_first_line(infer) -> None:
    body = f"{MARKER}\nEPIC: #508\n\n## What\nx"
    assert infer.strip_integration_marker(body).splitlines()[0] == "EPIC: #508"


def test_strip_leaves_an_unmarked_body_unchanged(infer) -> None:
    body = "EPIC: #508\n\n## What\nx"
    assert infer.strip_integration_marker(body) == body


def test_strip_only_touches_the_first_content_line(infer) -> None:
    """A marker-shaped line further down the body is not the DEC-013 marker."""
    body = f"EPIC: #508\n\n{MARKER}\n"
    assert infer.strip_integration_marker(body) == body


def test_strip_skips_leading_blank_lines_before_the_marker(infer) -> None:
    body = f"\n\n{MARKER}\nFeature: #42\n"
    assert infer.strip_integration_marker(body).strip().splitlines()[0] == "Feature: #42"


def test_strip_tolerates_empty_body(infer) -> None:
    assert infer.strip_integration_marker("") == ""


# --- infer.parent_ref ------------------------------------------------------


def test_parent_ref_reads_through_the_marker(infer) -> None:
    body = f"{MARKER}\nEPIC: #508\n\n## What\nx"
    assert infer.parent_ref(body) == 508


def test_parent_ref_unaffected_without_marker(infer) -> None:
    assert infer.parent_ref("EPIC: #508\n\n## What\nx") == 508


def test_parent_ref_none_when_no_parent(infer) -> None:
    assert infer.parent_ref("## What\nno parent") is None


# --- containment._body_names_parent ----------------------------------------


def test_containment_names_parent_through_the_marker(containment) -> None:
    body = f"{MARKER}\nEPIC: #508\n\n## What\nx"
    assert containment._body_names_parent(body, 508) is True


def test_containment_still_rejects_a_wrong_parent_with_marker(containment) -> None:
    body = f"{MARKER}\nEPIC: #508\n\n## What\nx"
    assert containment._body_names_parent(body, 999) is False


# --- show-tree._first_parent_ref -------------------------------------------


def test_show_tree_extracts_parent_through_the_marker() -> None:
    st = _load("pm_show_tree_marker_ut", SCRIPTS / "show-tree.py")
    body = f"{MARKER}\nEPIC: #508\n\n## What\nx"
    assert st._first_parent_ref(body) == 508
