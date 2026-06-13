"""Tests for the milestone resolution helper at `_lib/milestone.py`.

The resolver accepts either a milestone number (string of digits) or
an exact title and returns the matched `Milestone` dataclass.
Introduced in #217 to give `create-issue.py` and `promote-issue.py`
a single symmetric path for `--milestone` arg parsing — both scripts
previously only accepted one form each.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
LIB_DIR = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "scripts"
    / "_lib"
)
MODULE_PATH = LIB_DIR / "milestone.py"


@pytest.fixture(scope="module")
def milestone_mod():
    """Load `_lib/milestone.py` as a module.

    The module imports `from _lib.gh import gh_run`; we put the scripts/
    directory on sys.path so the relative import resolves the same way
    a real pm-script call would.
    """
    scripts_dir = LIB_DIR.parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    module_name = "pm_milestone_under_test"
    spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _stub_gh_run(stdout: str, returncode: int = 0):
    """Build a CompletedProcess-like stub for patching gh_run."""

    class _Proc:
        def __init__(self, stdout: str, returncode: int):
            self.stdout = stdout
            self.returncode = returncode
            self.stderr = ""

    return lambda *_a, **_k: _Proc(stdout, returncode)


SAMPLE_MILESTONES = (
    '[{"number": 6, "title": "Milestone 1: Self-host project-kit pm capability cleanly"},'
    ' {"number": 7, "title": "Milestone 2: Next outcome"}]'
)


def test_resolve_milestone_by_number(milestone_mod) -> None:
    """A numeric arg matches by milestone.number."""
    with patch.object(milestone_mod, "gh_run", _stub_gh_run(SAMPLE_MILESTONES)):
        ms = milestone_mod.resolve_milestone("6", {})
    assert ms is not None
    assert ms.number == 6
    assert ms.title.startswith("Milestone 1:")


def test_resolve_milestone_by_title(milestone_mod) -> None:
    """A title arg matches by milestone.title (exact match)."""
    with patch.object(milestone_mod, "gh_run", _stub_gh_run(SAMPLE_MILESTONES)):
        ms = milestone_mod.resolve_milestone(
            "Milestone 1: Self-host project-kit pm capability cleanly", {}
        )
    assert ms is not None
    assert ms.number == 6


def test_resolve_milestone_unknown_number_returns_none(milestone_mod) -> None:
    """A numeric arg matching no open milestone returns None."""
    with patch.object(milestone_mod, "gh_run", _stub_gh_run(SAMPLE_MILESTONES)):
        ms = milestone_mod.resolve_milestone("99", {})
    assert ms is None


def test_resolve_milestone_unknown_title_returns_none(milestone_mod) -> None:
    """A title arg matching no open milestone returns None."""
    with patch.object(milestone_mod, "gh_run", _stub_gh_run(SAMPLE_MILESTONES)):
        ms = milestone_mod.resolve_milestone("Milestone 9: Unknown", {})
    assert ms is None


def test_resolve_milestone_gh_failure_returns_none(milestone_mod) -> None:
    """When `gh api` fails (non-zero exit), resolver returns None."""
    with patch.object(milestone_mod, "gh_run", _stub_gh_run("", returncode=1)):
        ms = milestone_mod.resolve_milestone("6", {})
    assert ms is None


def test_resolve_milestone_empty_arg_returns_none(milestone_mod) -> None:
    """Empty input is treated as no match."""
    with patch.object(milestone_mod, "gh_run", _stub_gh_run(SAMPLE_MILESTONES)):
        ms = milestone_mod.resolve_milestone("", {})
    assert ms is None


def test_resolve_milestone_handles_concatenated_arrays(milestone_mod) -> None:
    """gh --paginate emits concatenated JSON arrays; the parser handles them."""
    concatenated = (
        '[{"number": 6, "title": "M1"}]\n'
        '[{"number": 7, "title": "M2"}]'
    )
    with patch.object(milestone_mod, "gh_run", _stub_gh_run(concatenated)):
        m6 = milestone_mod.resolve_milestone("6", {})
        m7 = milestone_mod.resolve_milestone("7", {})
    assert m6 is not None and m6.title == "M1"
    assert m7 is not None and m7.title == "M2"
