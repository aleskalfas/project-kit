"""close-issue's closure cascade says when a Milestone became closeable (#414).

When an issue closes, the cascade checks each Milestone it sits in (its native
Milestone field, or a `Milestone: [#<n>](../milestone/<n>)` body ref) the way it
checks each parent issue: a content-based or `either` Milestone whose every
child issue is closed is reported as eligible, with the `close-milestone`
command that closes it. A date-based Milestone closes on its date, and a
Milestone with an open child is not eligible. Nothing closes the Milestone.

The real close-issue runs in-process against a fake `gh` on PATH, so the
cascade's reads — the issue, the Milestone, the issue list — go through the
same `_lib` seams they use live.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Protocol

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CAP_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPT_PATH = CAP_ROOT / "scripts" / "close-issue.py"


@pytest.fixture(scope="module")
def ci() -> ModuleType:
    module_name = "pm_close_issue_milestone_eligibility_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# A `gh` that answers from a state file and keeps the closes it is told about,
# so the issue list the cascade reads after the close sees the issue closed.
_FAKE_GH = """\
import json, os, sys
args = sys.argv[1:]
with open(os.environ["FAKE_GH_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps(args) + "\\n")
path = os.environ["FAKE_GH_STATE"]
with open(path, encoding="utf-8") as fh:
    state = json.load(fh)
if args[:2] == ["issue", "list"]:
    rows = [dict(issue, number=int(n)) for n, issue in state["issues"].items()]
    print(json.dumps(rows))
    sys.exit(0)
if args[:1] == ["api"] and "/milestones/" in args[1] and "-X" not in args:
    milestone = state["milestones"].get(args[1].rsplit("/", 1)[1])
    if milestone is None:
        sys.exit(1)
    print(json.dumps(milestone))
    sys.exit(0)
if args[:1] == ["issue"] and len(args) > 2:
    issue = state["issues"].get(args[2])
    if issue is None:
        sys.exit(1)
    if args[1] == "view":
        fields = args[args.index("--json") + 1]
        print(json.dumps({"comments": []} if fields == "comments" else issue))
        sys.exit(0)
    if args[1] == "close":
        issue["state"] = "CLOSED"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(state, fh)
sys.exit(0)
"""

_Issue = dict[str, Any]

_MILESTONE_6 = {"number": 6, "title": "Milestone 6: Widgets"}
_TICKED = "\n\n## Success criteria\n\n- [x] shipped\n"


def _epic(*, state: str = "OPEN", milestone: _Issue | None = _MILESTONE_6) -> _Issue:
    """An EPIC scheduled under Milestone 6 by both substrates, criteria ticked."""
    return {
        "title": "[EPIC] Ship the widgets",
        "body": "Milestone: [#6](../milestone/6)" + _TICKED,
        "state": state,
        "labels": [],
        "milestone": milestone,
    }


def _milestone(
    description: str = "Close trigger: content-based",
    *,
    state: str = "open",
    due_on: str | None = None,
) -> _Issue:
    """Milestone 6 as `gh api repos/{owner}/{repo}/milestones/6` returns it."""
    return {
        "number": 6,
        "title": "Milestone 6: Widgets",
        "state": state,
        "description": description,
        "due_on": due_on,
    }


@dataclass(frozen=True)
class _Run:
    """What one close-issue run printed, and every `gh` call it made."""

    rc: int
    out: str
    err: str
    calls: list[list[str]]

    def milestone_writes(self) -> list[list[str]]:
        return [c for c in self.calls if c[:1] == ["api"] and "-X" in c]


def _returns(value: object) -> Callable[..., object]:
    """A stand-in for a gate or read that answers `value` whatever it is asked."""

    def stub(*_args: object, **_kwargs: object) -> object:
        return value

    return stub


class _CloseIssue(Protocol):
    def __call__(
        self, argv: list[str], *, issues: dict[int, _Issue], milestones: dict[int, _Issue]
    ) -> _Run: ...


@pytest.fixture
def close_issue(
    ci: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> _CloseIssue:
    """Run close-issue's main() with its gates passed and `gh` faked on PATH,
    answering from `issues` and `milestones`."""
    monkeypatch.setattr(ci, "resolve_capability_root", _returns(CAP_ROOT))
    monkeypatch.setattr(ci.bootstrap_gate, "enforce", _returns(True))
    monkeypatch.setattr(ci.session_guard, "enforce", _returns(True))
    monkeypatch.setattr(ci, "load_adopter_config", _returns({}))
    monkeypatch.setattr(ci, "_read_members", _returns([]))
    monkeypatch.setattr(
        ci, "resolve_invoker_identity", _returns(SimpleNamespace(github_login="me"))
    )
    monkeypatch.setattr(ci, "check_membership", _returns(SimpleNamespace(allowed=True)))
    monkeypatch.setattr(ci.axis_labels, "load_substrate_map", _returns(None))
    monkeypatch.setattr(ci, "fire_hooks", _returns(None))
    # The children-half of a container's own close is the process engine's
    # fold (a `pkit` subprocess); these tests are about what comes after it.
    monkeypatch.setattr(ci, "_engine_cascade_fold", _returns({"opened": True}))

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "gh"
    fake.write_text(f"#!{sys.executable}\n{_FAKE_GH}", encoding="utf-8")
    fake.chmod(0o755)
    state_file = tmp_path / "state.json"
    log = tmp_path / "gh.log"
    log.touch()
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("FAKE_GH_STATE", str(state_file))
    monkeypatch.setenv("FAKE_GH_LOG", str(log))

    def run(argv: list[str], *, issues: dict[int, _Issue], milestones: dict[int, _Issue]) -> _Run:
        state = {
            "issues": {str(n): issue for n, issue in issues.items()},
            "milestones": {str(n): m for n, m in milestones.items()},
        }
        state_file.write_text(json.dumps(state), encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["close-issue", *argv])
        rc: int = ci.main()
        captured = capfd.readouterr()
        lines = log.read_text(encoding="utf-8").splitlines()
        calls: list[list[str]] = [json.loads(line) for line in lines]
        return _Run(rc=rc, out=captured.out, err=captured.err, calls=calls)

    return run


_CLOSE_EPIC = ["20", "--mode", "cascade-eligibility-close", "--yes"]
_ELIGIBLE = "eligible to close: run `pkit pm close-milestone 6`"


def test_the_last_child_closing_makes_a_content_based_milestone_eligible(
    close_issue: _CloseIssue,
) -> None:
    run = close_issue(
        _CLOSE_EPIC,
        issues={20: _epic(), 21: _epic(state="CLOSED")},
        milestones={6: _milestone()},
    )
    assert run.rc == 0, run.out + run.err
    assert ["issue", "close", "20", "--reason", "completed"] in run.calls
    assert "[cascade] milestones to check for eligibility: #6" in run.out
    assert (
        "  · milestone #6 open; content-based, all 2 child issue(s) closed — " + _ELIGIBLE
    ) in run.out
    # Surfaced, never executed: the Milestone is not closed.
    assert run.milestone_writes() == []


def test_an_open_child_holds_the_milestone(close_issue: _CloseIssue) -> None:
    run = close_issue(_CLOSE_EPIC, issues={20: _epic(), 21: _epic()}, milestones={6: _milestone()})
    assert run.rc == 0, run.out + run.err
    assert "  · milestone #6 open; not eligible (1 open child issue(s))" in run.out
    assert "eligible to close: run" not in run.out


def test_a_date_based_milestone_closes_on_its_date(close_issue: _CloseIssue) -> None:
    run = close_issue(
        _CLOSE_EPIC,
        issues={20: _epic(), 21: _epic(state="CLOSED")},
        milestones={6: _milestone("Close trigger: date-based")},
    )
    assert run.rc == 0, run.out + run.err
    assert "  · milestone #6 open; date-based — it closes on its date" in run.out
    assert "eligible to close: run" not in run.out
    # Its children are not even read: the date decides.
    assert not any(c[:2] == ["issue", "list"] for c in run.calls)


def test_an_either_milestone_is_eligible_once_its_content_is_done(
    close_issue: _CloseIssue,
) -> None:
    run = close_issue(
        _CLOSE_EPIC, issues={20: _epic()}, milestones={6: _milestone("Close trigger: either")}
    )
    assert "  · milestone #6 open; either, all 1 child issue(s) closed — " + _ELIGIBLE in run.out


@pytest.mark.parametrize(
    ("due_on", "expected"),
    [
        (None, "content-based (inferred), all 1 child issue(s) closed — " + _ELIGIBLE),
        ("2026-12-31T00:00:00Z", "date-based (inferred) — it closes on its date"),
    ],
)
def test_an_unmarked_milestone_is_read_by_its_due_date(
    close_issue: _CloseIssue, due_on: str | None, expected: str
) -> None:
    run = close_issue(
        _CLOSE_EPIC, issues={20: _epic()}, milestones={6: _milestone("A theme.", due_on=due_on)}
    )
    assert f"  · milestone #6 open; {expected}" in run.out


def test_a_closed_milestone_is_reported_closed(close_issue: _CloseIssue) -> None:
    run = close_issue(_CLOSE_EPIC, issues={20: _epic()}, milestones={6: _milestone(state="closed")})
    assert "  · milestone #6 already closed" in run.out
    assert "eligible to close: run" not in run.out


def test_an_unreadable_milestone_warns_and_the_close_stands(close_issue: _CloseIssue) -> None:
    run = close_issue(_CLOSE_EPIC, issues={20: _epic()}, milestones={})
    assert run.rc == 0
    assert ["issue", "close", "20", "--reason", "completed"] in run.calls
    assert "[warn] could not fetch milestone #6" in run.err


def test_no_cascade_skips_the_milestone_too(close_issue: _CloseIssue) -> None:
    run = close_issue(
        [*_CLOSE_EPIC, "--no-cascade"], issues={20: _epic()}, milestones={6: _milestone()}
    )
    assert run.rc == 0
    assert "[cascade]" not in run.out
    assert not any(c[:1] == ["api"] for c in run.calls)


def test_an_issue_in_no_milestone_checks_none(close_issue: _CloseIssue) -> None:
    epic = _epic(milestone=None)
    epic["body"] = "## What" + _TICKED
    run = close_issue(_CLOSE_EPIC, issues={20: epic}, milestones={6: _milestone()})
    assert run.rc == 0
    assert "milestones to check" not in run.out
    assert not any(c[:1] == ["api"] for c in run.calls)


def test_the_pr_merge_cascade_surfaces_it_for_a_leaf_in_the_milestone(
    close_issue: _CloseIssue,
) -> None:
    """The path done-work runs after a merge: a Task GitHub already closed,
    scheduled into the Milestone by its native field alone, was its last open
    child. Its parent Feature is not in the Milestone."""
    task: _Issue = {
        "title": "[Task] land the widget",
        "state": "CLOSED",
        "body": "Feature: #7\n\n## What\n\nx\n\n## Acceptance criteria\n\n- [x] done\n",
        "labels": [{"name": "state:review"}],
        "milestone": _MILESTONE_6,
    }
    feature: _Issue = {
        "title": "[Feature] widgets",
        "state": "OPEN",
        "body": "## What\n\nw\n",
        "labels": [],
        "milestone": None,
    }
    run = close_issue(
        ["42", "--mode", "pr-merge", "--yes"],
        issues={42: task, 7: feature},
        milestones={6: _milestone()},
    )
    assert run.rc == 0, run.out + run.err
    assert "[cascade] parents to check for eligibility: #7" in run.out
    assert (
        "  · milestone #6 open; content-based, all 1 child issue(s) closed — " + _ELIGIBLE
    ) in run.out


# ---- which Milestones an issue sits in ----------------------------------


_REF_6 = "Milestone: [#6](../milestone/6)"


@pytest.mark.parametrize(
    ("issue", "expected"),
    [
        ({"milestone": {"number": 6}, "body": ""}, [6]),
        ({"milestone": None, "body": _REF_6}, [6]),
        # Both substrates naming the same Milestone name it once.
        ({"milestone": {"number": 6}, "body": _REF_6}, [6]),
        # Substrates that disagree name both, so neither Milestone is missed.
        ({"milestone": {"number": 7}, "body": _REF_6}, [6, 7]),
        ({"milestone": None, "body": "EPIC: #3"}, []),
        # A link whose text and target disagree is not a milestone ref.
        ({"milestone": None, "body": "Milestone: [#6](../milestone/7)"}, []),
    ],
)
def test_the_milestones_an_issue_sits_in(
    ci: ModuleType, issue: _Issue, expected: list[int]
) -> None:
    assert ci.issue_milestones(issue) == expected


def test_a_milestone_first_line_is_not_a_parent_issue(ci: ModuleType) -> None:
    """The deprecated plain `Milestone: #<n>` form names a Milestone, not
    issue #<n>, so the parent walk does not read it as one."""
    assert ci._walk_parent_chain("Milestone: #6\n\n## What\n") == []
    assert ci._walk_parent_chain("EPIC: #6\n\n## What\n") == [6]
