"""Tests for the milestone resolution helper at `_lib/milestone.py`.

The resolver accepts either a milestone number (string of digits) or
an exact title and returns the matched `Milestone` dataclass.
Introduced in #217 to give `create-issue.py` and `promote-issue.py`
a single symmetric path for `--milestone` arg parsing — both scripts
previously only accepted one form each.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
LIB_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts" / "_lib"
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
    concatenated = '[{"number": 6, "title": "M1"}]\n[{"number": 7, "title": "M2"}]'
    with patch.object(milestone_mod, "gh_run", _stub_gh_run(concatenated)):
        m6 = milestone_mod.resolve_milestone("6", {})
        m7 = milestone_mod.resolve_milestone("7", {})
    assert m6 is not None and m6.title == "M1"
    assert m7 is not None and m7.title == "M2"


def test_the_titles_of_every_milestone_are_read_by_number_in_one_read(milestone_mod) -> None:
    """DEC-059 point 2: `seats` shows each milestone a scope names beside its
    title, read from every milestone, open and closed, page by page."""
    calls: list[list[str]] = []
    pages = '[{"number": 6, "title": "M1"}, {"title": "no number"}]\n[{"number": 9, "title": "M9"}]'

    def gh(argv: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, pages, "")

    assert milestone_mod.read_titles(gh) == {6: "M1", 9: "M9"}
    assert calls == [
        ["gh", "api", "repos/{owner}/{repo}/milestones?state=all&per_page=100", "--paginate"]
    ]


def test_a_failed_read_of_the_milestones_gives_no_titles(milestone_mod) -> None:
    def failing(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 1, "", "HTTP 502: Bad Gateway")

    def missing(_argv: list[str]) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("gh")

    assert milestone_mod.read_titles(failing) is None
    assert milestone_mod.read_titles(missing) is None


def test_a_state_issue_is_never_a_milestone_child(milestone_mod, monkeypatch) -> None:
    """#2139: the children are read through the one read of issues, which leaves
    a state issue out (DEC-058 point 3), even one carrying the Milestone both ways."""
    native = {"number": 6, "title": "M1"}
    rows = [
        {"number": 10, "title": "[Task] work", "state": "OPEN", "body": "", "milestone": native},
        {
            "number": 11,
            "title": "Seat planner",
            "state": "OPEN",
            "body": "Milestone: [#6](../milestone/6)\n"
            "<!-- pkit:state-issue v=1 key=seat-planner -->\n",
            "milestone": native,
        },
    ]

    def fake_gh(args, config):
        return subprocess.CompletedProcess(args, 0, stdout=json.dumps(rows), stderr="")

    monkeypatch.setattr(milestone_mod.containment, "_gh_call", fake_gh)
    children = milestone_mod.list_milestone_children(6, "M1", {}, {"types": {}})
    assert [child["number"] for child in children] == [10]
