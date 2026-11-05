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


# ---- the pool (DEC-061 point 2, ADR-072 point 3) ------------------------------


def test_list_open_milestones_runs_a_callers_gh(milestone_mod) -> None:
    calls: list[list[str]] = []

    def gh(argv):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout=SAMPLE_MILESTONES, stderr="")

    rows = milestone_mod.list_open_milestones({}, gh=gh)
    assert [r["number"] for r in rows] == [6, 7]
    assert calls == [list(milestone_mod.OPEN_MILESTONES_ARGV)]


@pytest.mark.parametrize(
    ("description", "name", "reason"),
    [
        ("Close trigger: date-based\nPool: alpha", "alpha", None),
        ("Close trigger: either\n\nSome words.\n  Pool: bravo-2  \nmore", "bravo-2", None),
        ("Pool: alpha\nClose trigger: date-based", "alpha", None),
        ("Close trigger: date-based", None, "no-line"),
        ("", None, "no-line"),
        ("Pool: alpha\nPool: alpha", None, "two-lines"),
        ("Pool: alpha\nPool: Bravo", None, "two-lines"),
        ("Pool: Alpha", None, "unread"),
        ("Pool:", None, "unread"),
        ("Pool: alpha bravo", None, "unread"),
        ("The Pool: alpha is ours", None, "no-line"),
    ],
)
def test_the_pool_line_is_read_wherever_it_stands_and_every_one_counts(
    milestone_mod, description, name, reason
) -> None:
    pool = milestone_mod.parse_pool_line(description)
    assert (pool.name, pool.reason) == (name, reason)


def test_a_milestones_pool_is_one_the_topology_declares(milestone_mod) -> None:
    pool = milestone_mod.milestone_pool
    assert pool("Pool: alpha", ("alpha", "bravo")).name == "alpha"
    undeclared = pool("Pool: charlie", ("alpha",))
    assert undeclared.name is None and undeclared.reason == milestone_mod.UNDECLARED_POOL
    assert "'charlie', which the topology does not declare" in undeclared.warning(7)
    assert pool("Pool: alpha", None).name is None
    assert pool("Close trigger: either", ("alpha",)).warning(7) is None
    assert "more than one" in pool("Pool: a\nPool: b", ("a",)).warning(7)
    assert "'Pool: A'" in pool("Pool: A", ("a",)).warning(7)


def test_a_write_replaces_the_line_and_never_adds_a_second(milestone_mod) -> None:
    put = milestone_mod.with_pool_line
    assert put("Close trigger: date-based\n\nWords.", "alpha") == (
        "Close trigger: date-based\nPool: alpha\n\nWords."
    )
    assert put("Close trigger: date-based\nRollforward target: #9\n\nWords.", "alpha") == (
        "Close trigger: date-based\nRollforward target: #9\nPool: alpha\n\nWords."
    )
    assert put("Words.\nPool: alpha\nMore.", "bravo") == "Words.\nPool: bravo\nMore."
    assert put("Pool: alpha\nWords.\nPool: x y", "bravo") == "Pool: bravo\nWords."
    assert put("Words.", "alpha") == "Pool: alpha\nWords."
    assert put("", "alpha") == "Pool: alpha"
    assert (
        put("Close trigger: either\nPool: alpha\nWords.", None) == "Close trigger: either\nWords."
    )
    with pytest.raises(ValueError):
        put("", "Alpha")


def test_the_log_line_never_takes_the_pool_form(milestone_mod) -> None:
    line = milestone_mod.pool_log_line(None, "alpha", verb="set-pool", today="2026-10-28")
    assert "none → alpha" in line and "consent" in line
    described = milestone_mod.with_log_line(
        milestone_mod.with_pool_line("Close trigger: either", "alpha"), line
    )
    assert milestone_mod.parse_pool_line(described).name == "alpha"


def test_the_schema_declares_the_grammar_the_parser_reads(milestone_mod) -> None:
    from ruamel.yaml import YAML

    schema = YAML(typ="safe").load(
        (LIB_DIR.parent.parent / "schemas" / "time-containers.yaml").read_text("utf-8")
    )
    field = schema["containers"]["milestone"]["close_trigger_marker"]["pool_field"]
    assert field["opening"] == milestone_mod.POOL_OPENING
    import re

    declared = re.compile(field["pattern"])
    for line in ("Pool: alpha", "Pool: a-1", "Pool: Alpha", "Pool: a-", "Pool: a b", "Pool:"):
        read = milestone_mod.parse_pool_line(line).name is not None
        assert bool(declared.match(line)) == read, line
