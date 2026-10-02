"""Tests for project-management's close-milestone script.

Covers the pure close-trigger resolution + decision policy, the audit-note
composition, milestone→child resolution (native field + textual ref union,
read through `_lib.milestone`, the reads close-issue's cascade shares),
and — mirroring the AC — content-based close with all children closed
(succeeds), with an open child (refuses), --dry-run previews without
mutating, the audit note is written on a real close, and the gh mutation
routes through the validated `_lib.gh` seam (monkeypatched).

And the rollforward (#1175): a date-triggered close — date-based, or `either`
from its due date — moves each open child to the rollforward target through
`edit-issue --milestone`, leaves the closed ones, and records the target in the
audit line, from which a re-run finishes a rollforward a failure cut short.
These tests run against an in-memory repository behind every `gh` seam; the
end-to-end ones run the real `edit-issue` for each move.
"""

from __future__ import annotations

import datetime as dt
import importlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CAP_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS_DIR = CAP_ROOT / "scripts"
SCRIPT_PATH = SCRIPTS_DIR / "close-milestone.py"
EDIT_ISSUE_PATH = SCRIPTS_DIR / "edit-issue.py"

# The script does `sys.path.insert(0, <scripts dir>)` and `from _lib...`; make
# the same dir importable here so loading the module by file path resolves it.
sys.path.insert(0, str(SCRIPTS_DIR))
# The shared `_lib` modules the script reads a Milestone through.
containment: ModuleType = importlib.import_module("_lib.containment")
ms: ModuleType = importlib.import_module("_lib.milestone")


def _load(module_name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def cm() -> ModuleType:
    """Load close-milestone.py as a module via importlib."""
    return _load("pm_close_milestone_under_test", SCRIPT_PATH)


@pytest.fixture(scope="module")
def ei() -> ModuleType:
    """Load edit-issue.py, the writer each rollforward move goes through."""
    return _load("pm_close_milestone_edit_issue_under_test", EDIT_ISSUE_PATH)


@pytest.fixture
def issue_types() -> dict:
    return {
        "types": {
            "epic": {"title_prefix": "EPIC", "title_case": "upper"},
            "feature": {"title_prefix": "Feature", "title_case": "title"},
            "task": {"title_prefix": "Task", "title_case": "title"},
        },
    }


# --- close-trigger resolution ----------------------------------------


def test_parse_close_trigger_reads_marker() -> None:
    assert ms.parse_close_trigger("Close trigger: content-based\n\nbody") == "content-based"
    assert ms.parse_close_trigger("Close trigger: date-based") == "date-based"
    assert ms.parse_close_trigger("Close trigger: either\n") == "either"


def test_parse_close_trigger_absent_returns_none() -> None:
    assert ms.parse_close_trigger("Just a plain description") is None
    assert ms.parse_close_trigger("") is None
    # A non-first-line marker does not count (DEC-016: first line).
    assert ms.parse_close_trigger("intro\nClose trigger: date-based") is None


def test_infer_close_trigger_uses_due_date() -> None:
    assert ms.infer_close_trigger("2026-07-01T23:59:59Z") == "date-based"
    assert ms.infer_close_trigger(None) == "content-based"
    assert ms.infer_close_trigger("") == "content-based"


def test_resolve_close_trigger_marker_wins_over_inference() -> None:
    due = "2026-07-01T00:00:00Z"
    # Marker present → not inferred, even with a due date.
    assert ms.resolve_close_trigger("Close trigger: content-based", due) == (
        "content-based",
        False,
    )
    # No marker → inferred from the due date.
    assert ms.resolve_close_trigger("no marker here", due) == ("date-based", True)


# --- whether the date trigger fired ------------------------------------

_DUE = "2026-07-01T07:00:00Z"


def test_a_date_based_close_is_always_date_triggered() -> None:
    """The date is its trigger, and an early close is the manual form of it."""
    for due_on in (None, _DUE):
        assert ms.date_trigger_fired("date-based", due_on, dt.date(2026, 6, 1))


@pytest.mark.parametrize(
    ("due_on", "today", "fired"),
    [
        pytest.param(_DUE, dt.date(2026, 6, 30), False, id="before-the-due-date"),
        pytest.param(_DUE, dt.date(2026, 7, 1), True, id="on-the-due-date"),
        pytest.param(_DUE, dt.date(2026, 7, 2), True, id="past-the-due-date"),
        pytest.param(None, dt.date(2026, 7, 2), False, id="no-due-date"),
        pytest.param("not a date", dt.date(2026, 7, 2), False, id="unreadable-due-date"),
    ],
)
def test_an_either_close_is_date_triggered_from_its_due_date(
    due_on: object, today: dt.date, fired: bool
) -> None:
    assert ms.date_trigger_fired("either", due_on, today) is fired


def test_a_content_based_close_is_never_date_triggered() -> None:
    assert not ms.date_trigger_fired("content-based", _DUE, dt.date(2030, 1, 1))


# --- the rollforward target ---------------------------------------------


@pytest.mark.parametrize(
    ("line", "argument"),
    [
        pytest.param("Rollforward target: Sprint 9: Later", "Sprint 9: Later", id="title"),
        pytest.param("Rollforward target: #9", "9", id="hash-number"),
        pytest.param("Rollforward target: 9", "9", id="number"),
        pytest.param("Rollforward target: [#9](../milestone/9)", "9", id="link"),
    ],
)
def test_parse_rollforward_target_reads_the_line(line: str, argument: str) -> None:
    description = f"Close trigger: date-based\n{line}\n\nSprint notes"
    assert ms.parse_rollforward_target(description) == argument


def test_parse_rollforward_target_absent_returns_none() -> None:
    assert ms.parse_rollforward_target("Close trigger: date-based\n\nnotes") is None
    assert ms.parse_rollforward_target("") is None


_CATEGORIES = {
    "sprint": {"title_format": "Sprint {n}: {name}", "close_trigger_default": "date-based"},
    "milestone": {"title_format": "Milestone {n}: {name}", "close_trigger_default": "either"},
}


def _open(*milestones: tuple[int, str]) -> list[dict]:
    return [{"number": n, "title": t, "state": "open"} for n, t in milestones]


def test_next_numbered_is_the_lowest_later_number_of_the_same_category() -> None:
    open_milestones = _open(
        (3, "Sprint 3: Earlier"),
        (9, "Sprint 9: Later"),
        (7, "Sprint 7: Polish"),
        (8, "Milestone 7: Other category"),
    )
    found = ms.next_numbered_milestones("Sprint 6: Ship it", open_milestones, _CATEGORIES)
    assert [(m.number, m.title) for m in found] == [(7, "Sprint 7: Polish")]


def test_next_numbered_counts_gaps_as_sort_order() -> None:
    """Numbers are a sort prefix, not a strict sequence (DEC-016): a gap is fine."""
    found = ms.next_numbered_milestones(
        "Sprint 6: Ship it", _open((9, "Sprint 9: Later")), _CATEGORIES
    )
    assert [m.number for m in found] == [9]


def test_next_numbered_names_every_milestone_sharing_the_next_number() -> None:
    open_milestones = _open((7, "Sprint 7: Polish"), (11, "Sprint 7: Other half"))
    found = ms.next_numbered_milestones("Sprint 6: Ship it", open_milestones, _CATEGORIES)
    assert [m.number for m in found] == [7, 11]


@pytest.mark.parametrize(
    ("title", "categories"),
    [
        pytest.param("Sprint 6: Ship it", {}, id="no-categories-declared"),
        pytest.param("Unnumbered window", _CATEGORIES, id="title-fits-no-category"),
        pytest.param("Sprint 9: Last", _CATEGORIES, id="nothing-later-open"),
    ],
)
def test_next_numbered_finds_no_candidate(title: str, categories: dict) -> None:
    open_milestones = _open((7, "Sprint 7: Polish"), (9, "Sprint 9: Last"))
    assert ms.next_numbered_milestones(title, open_milestones, categories) == []


# --- decision policy -------------------------------------------------


def test_decide_no_open_children_always_proceeds(cm) -> None:
    for date_triggered in (True, False):
        for force in (True, False):
            d = cm._decide_close(False, force=force, date_triggered=date_triggered)
            assert d.proceed is True
            assert d.rolls_forward is False
            assert d.leaves_open_children is False


def test_decide_a_date_triggered_close_rolls_open_children_forward(cm) -> None:
    for force in (True, False):
        d = cm._decide_close(True, force=force, date_triggered=True)
        assert d.proceed is True
        assert d.rolls_forward is True


def test_decide_open_children_hold_a_content_close(cm) -> None:
    d = cm._decide_close(True, force=False, date_triggered=False)
    assert d.proceed is False
    assert d.exit_code == 1


def test_decide_force_closes_a_content_close_leaving_open_children(cm) -> None:
    d = cm._decide_close(True, force=True, date_triggered=False)
    assert d.proceed is True
    assert d.rolls_forward is False
    assert d.leaves_open_children is True


# --- audit note ------------------------------------------------------


def _plan(cm, *, moves: int, target=(7, "Sprint 7: Polish")):
    milestone = ms.Milestone(number=target[0], title=target[1])
    return cm.RollforwardPlan(
        target=cm.RollforwardTarget(milestone, "test"),
        moves=tuple({"number": 100 + i} for i in range(moves)),
        left=(),
    )


def test_compose_close_description_appends_audit_line(cm) -> None:
    out = cm._compose_close_description(
        "Close trigger: content-based\n\nSprint 6",
        close_trigger="content-based",
        closed_count=3,
    )
    assert "Close trigger: content-based" in out
    assert cm._AUDIT_MARKER in out
    assert "3 child issue(s) closed)." in out


def test_the_audit_line_counts_the_children_rolled_forward_and_names_the_target(cm) -> None:
    out = cm._compose_close_description(
        "", close_trigger="date-based", closed_count=2, plan=_plan(cm, moves=3)
    )
    assert "2 child issue(s) closed; 3 rolled forward to #7 Sprint 7: Polish)." in out
    assert cm._recorded_target(out) == 7


def test_a_forced_content_close_counts_open_children_as_not_rolled_forward(cm) -> None:
    out = cm._compose_close_description(
        "", close_trigger="content-based", closed_count=2, left_open=1
    )
    assert "1 still open, not rolled forward" in out
    assert "rolled forward to" not in out
    assert cm._recorded_target(out) is None


def test_compose_close_description_is_idempotent(cm) -> None:
    once = cm._compose_close_description("desc", close_trigger="content-based", closed_count=1)
    twice = cm._compose_close_description(once, close_trigger="content-based", closed_count=1)
    assert once == twice
    assert once.count(cm._AUDIT_MARKER) == 1


def test_the_last_audit_line_is_the_recorded_target(cm) -> None:
    """A Milestone reopened and closed again records its new close; a re-run
    reads the target from the latest one."""
    first = cm._compose_close_description(
        "", close_trigger="date-based", closed_count=0, plan=_plan(cm, moves=1, target=(7, "A"))
    )
    second = cm._compose_close_description(
        first, close_trigger="date-based", closed_count=1, plan=_plan(cm, moves=1, target=(9, "B"))
    )
    assert second.count(cm._AUDIT_MARKER) == 2
    assert cm._recorded_target(second) == 9


# --- milestone → child resolution (native + textual union) -----------


def _patch_issue_list(
    monkeypatch: pytest.MonkeyPatch, rows: list[dict[str, Any]], *, complete: bool = True
) -> None:
    """Stub the containment seam's corpus fetch, which list_milestone_children
    reads the issues through, with a fixed issue list."""

    def fetch(_config: object, **_kwargs: object) -> object:
        return containment.IssueCorpus(rows=tuple(rows), complete=complete)

    monkeypatch.setattr(containment, "fetch_issue_corpus", fetch)


def _row(number, state, *, title="[EPIC] X", body="", milestone=None):
    return {
        "number": number,
        "title": title,
        "state": state,
        "body": body,
        "milestone": milestone,
    }


def test_children_resolved_via_native_field(
    monkeypatch: pytest.MonkeyPatch, issue_types: dict[str, Any]
) -> None:
    _patch_issue_list(
        monkeypatch,
        [
            _row(10, "CLOSED", milestone={"number": 6}),
            _row(11, "OPEN", milestone={"number": 99}),
        ],
    )
    children = ms.list_milestone_children(6, "Milestone 6: Sprint", {}, issue_types)
    assert [c["number"] for c in children] == [10]
    assert children[0]["type"] == "epic"
    assert children[0]["state"] == "closed"
    assert children[0]["milestone"] == {"number": 6}


def test_children_resolved_via_textual_ref(
    monkeypatch: pytest.MonkeyPatch, issue_types: dict[str, Any]
) -> None:
    body = "Milestone: [#6](../milestone/6)\n\n## Acceptance criteria\n"
    _patch_issue_list(
        monkeypatch,
        [
            _row(20, "OPEN", body=body),
            _row(21, "OPEN", body="Milestone: [#7](../milestone/7)"),
        ],
    )
    children = ms.list_milestone_children(6, "Milestone 6: Sprint", {}, issue_types)
    assert [c["number"] for c in children] == [20]
    assert children[0]["milestone"] is None


def test_children_union_dedups_and_sorts(
    monkeypatch: pytest.MonkeyPatch, issue_types: dict[str, Any]
) -> None:
    body = "Milestone: [#6](../milestone/6)"
    _patch_issue_list(
        monkeypatch,
        [
            _row(30, "CLOSED", body=body, milestone={"number": 6}),
            _row(12, "CLOSED", milestone={"number": 6}),
        ],
    )
    children = ms.list_milestone_children(6, "Milestone 6: Sprint", {}, issue_types)
    # Present in both substrates → counted once; sorted by number.
    assert [c["number"] for c in children] == [12, 30]


def test_children_gh_failure_returns_none(
    monkeypatch: pytest.MonkeyPatch, issue_types: dict[str, Any]
) -> None:
    def failed_fetch(_config: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(containment, "fetch_issue_corpus", failed_fetch)
    assert ms.list_milestone_children(6, "t", {}, issue_types) is None


def test_children_refuse_a_truncated_issue_list(
    monkeypatch: pytest.MonkeyPatch,
    issue_types: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A list that reached the seam's ceiling may be missing an open child, so
    it is refused rather than answered from — the list is what decides whether
    the Milestone may close."""
    _patch_issue_list(monkeypatch, [_row(10, "CLOSED", milestone={"number": 6})], complete=False)
    assert ms.list_milestone_children(6, "t", {}, issue_types) is None
    assert "ceiling" in capsys.readouterr().err


# --- gh mutation routes through the validated _lib seam ---------------


def test_close_milestone_goes_through_gh_run_with_patch(cm, monkeypatch) -> None:
    """The mutation is a PATCH state=closed routed through _lib.gh.gh_run."""
    captured = {}

    def fake_gh_run(args, config, **kwargs):
        captured["args"] = args
        captured["config"] = config
        proc = MagicMock()
        proc.returncode = 0
        return proc

    monkeypatch.setattr(cm, "gh_run", fake_gh_run)
    ok = cm._gh_close_milestone(6, "desc with audit", {"gh": {"host": "example.com"}})
    assert ok is True
    args = captured["args"]
    assert args[0] == "gh" and args[1] == "api"
    assert "-X" in args and "PATCH" in args
    assert any("milestones/6" in a for a in args)
    assert "state=closed" in args
    assert any(a == "description=desc with audit" for a in args)
    # config threaded through (host/owner pinning per DEC-023).
    assert captured["config"] == {"gh": {"host": "example.com"}}


def test_close_milestone_reports_gh_failure(cm, monkeypatch) -> None:
    proc = MagicMock()
    proc.returncode = 1
    proc.stderr = "nope"
    monkeypatch.setattr(cm, "gh_run", lambda *a, **k: proc)
    assert cm._gh_close_milestone(6, "desc", {}) is False


# --- end-to-end via main() (AC: succeeds / refuses / dry-run / audit) --


def _prime_main(monkeypatch, cm, *, milestone, children):
    """Stub main()'s environment: gate + guard pass, milestone + children fixed.

    Returns the MagicMock standing in for _gh_close_milestone so a test can
    assert whether (and with what description) the real close was attempted.
    """
    _pass_gates(monkeypatch, cm)
    monkeypatch.setattr(
        cm,
        "_read_yaml",
        lambda path, loader: {"types": {"epic": {"title_prefix": "EPIC", "title_case": "upper"}}},
    )
    monkeypatch.setattr(cm, "fetch_milestone", lambda n, config: milestone)
    monkeypatch.setattr(
        cm,
        "list_milestone_children",
        lambda n, t, config, types, classification=None: children,
    )
    close_mock = MagicMock(return_value=True)
    monkeypatch.setattr(cm, "_gh_close_milestone", close_mock)
    return close_mock


def _pass_gates(
    monkeypatch: pytest.MonkeyPatch, cm: ModuleType, capability_root: Path = REPO_ROOT
) -> None:
    """Let main() past its startup gates: membership, foreign-repo guard, bootstrap."""
    monkeypatch.setattr(cm, "resolve_capability_root", lambda p: capability_root)
    monkeypatch.setattr(cm, "load_adopter_config", lambda root: {})
    monkeypatch.setattr(cm, "_read_members", lambda root, loader: [])
    monkeypatch.setattr(cm, "resolve_invoker_identity", lambda config=None: "tester")
    monkeypatch.setattr(cm, "check_membership", lambda members, invoker: MagicMock(allowed=True))
    monkeypatch.setattr(cm.session_guard, "enforce", lambda override=False: True)
    # This file targets close-milestone's close-trigger semantics, not the #747
    # prerequisite gate (covered in test_pm_bootstrap_gate*.py); the stubbed
    # capability root is the kit repo root, which carries no adopter tree to
    # stamp, so neutralise the gate here — as the line above does for the guard.
    monkeypatch.setattr(cm.bootstrap_gate, "enforce", lambda *a, **kw: True)


def _args(**over):
    base = dict(
        milestone="6",
        target=None,
        force=False,
        capability_root=None,
        dry_run=False,
        yes=True,
        allow_foreign_repo=False,
    )
    base.update(over)
    ns = __import__("argparse").Namespace(**base)
    return ns


def _ms(**over):
    base = {
        "title": "Milestone 6",
        "state": "open",
        "description": "Close trigger: content-based",
        "due_on": None,
    }
    base.update(over)
    return base


def test_main_content_based_all_closed_succeeds(cm, monkeypatch) -> None:
    milestone = _ms()
    children = [{"number": 10, "title": "[EPIC] A", "state": "closed", "type": "epic"}]
    close_mock = _prime_main(monkeypatch, cm, milestone=milestone, children=children)
    monkeypatch.setattr(cm.argparse.ArgumentParser, "parse_args", lambda self: _args())
    rc = cm.main()
    assert rc == 0
    close_mock.assert_called_once()
    # The audit note reached the close call's description argument.
    _num, desc = close_mock.call_args.args[0], close_mock.call_args.args[1]
    assert cm._AUDIT_MARKER in desc


def test_main_content_based_open_child_refuses(cm, monkeypatch) -> None:
    milestone = _ms()
    children = [
        {"number": 10, "title": "[EPIC] A", "state": "closed", "type": "epic"},
        {"number": 11, "title": "[EPIC] B", "state": "open", "type": "epic"},
    ]
    close_mock = _prime_main(monkeypatch, cm, milestone=milestone, children=children)
    monkeypatch.setattr(cm.argparse.ArgumentParser, "parse_args", lambda self: _args())
    rc = cm.main()
    assert rc == 1
    close_mock.assert_not_called()


def test_main_dry_run_previews_without_mutating(cm, monkeypatch) -> None:
    milestone = _ms()
    children = [{"number": 10, "title": "[EPIC] A", "state": "closed", "type": "epic"}]
    close_mock = _prime_main(monkeypatch, cm, milestone=milestone, children=children)
    monkeypatch.setattr(cm.argparse.ArgumentParser, "parse_args", lambda self: _args(dry_run=True))
    rc = cm.main()
    assert rc == 0
    close_mock.assert_not_called()


def test_main_already_closed_is_noop(cm, monkeypatch) -> None:
    milestone = {"title": "Milestone 6", "state": "closed", "description": "", "due_on": None}
    close_mock = _prime_main(monkeypatch, cm, milestone=milestone, children=[])
    monkeypatch.setattr(cm.argparse.ArgumentParser, "parse_args", lambda self: _args())
    rc = cm.main()
    assert rc == 0
    close_mock.assert_not_called()


# --- the rollforward (#1175) -------------------------------------------
#
# An in-memory repository stands behind every gh seam a close and its moves go
# through, and records every call, so a test pins the whole effect of a close:
# the Milestone's PATCH, and one `edit-issue --milestone` per open child moved.

_TASK_BODY = (
    "{first}\n\n## What\nwork\n\n## Acceptance criteria\n- [ ] done\n\n## Doc impact\n- [ ] none\n"
)
_CLOSING = {
    "number": 6,
    "title": "Sprint 6: Ship it",
    "state": "open",
    "description": "Close trigger: date-based",
    "due_on": None,
}
_NEXT = {
    "number": 7,
    "title": "Sprint 7: Polish",
    "state": "open",
    "description": "",
    "due_on": None,
}
_LATER = {
    "number": 9,
    "title": "Sprint 9: Later",
    "state": "open",
    "description": "",
    "due_on": None,
}
_OTHER = {
    "number": 8,
    "title": "Milestone 1: Outcome",
    "state": "open",
    "description": "",
    "due_on": None,
}
_CONFIG = {"milestone_categories": _CATEGORIES}


def _milestone_ref(number: int) -> str:
    return f"Milestone: [#{number}](../milestone/{number})"


def _issue(
    number: int,
    state: str,
    *,
    title: str = "[Task] work",
    first: str | None = None,
    milestone: int | None = 6,
    labels: tuple[str, ...] = ("state:backlog",),
) -> dict:
    return {
        "number": number,
        "title": title,
        "state": state,
        "body": _TASK_BODY.format(first=first if first is not None else _milestone_ref(6)),
        "labels": list(labels),
        "milestone": milestone,
    }


# Milestone #6's children: #10 closed; #11 open via the native field and its
# first line; #12 open via its first line only. #13 belongs to another milestone.
def _mixed_issues() -> list[dict]:
    return [
        _issue(10, "CLOSED", title="[Task] shipped", labels=("state:done",)),
        _issue(11, "OPEN", title="[Task] in flight", labels=("state:in-progress",)),
        _issue(12, "OPEN", title="[Task] not started", milestone=None),
        _issue(13, "OPEN", title="[Task] elsewhere", first=_milestone_ref(8), milestone=8),
    ]


class FakeRepo:
    """An in-memory repository: milestones, issues and their comments, served
    through the `gh` argv shapes the scripts use, every call recorded."""

    def __init__(self, milestones: list[dict], issues: list[dict]) -> None:
        self.milestones = {m["number"]: dict(m) for m in milestones}
        self.issues = {i["number"]: dict(i) for i in issues}
        self.comments: dict[int, list[dict]] = {n: [] for n in self.issues}
        self.calls: list[list[str]] = []
        self.fail_milestone_write: set[int] = set()
        self.fail_body_write: set[int] = set()

    # -- the gh seam --

    def gh_run(
        self, args: list[str], config: object, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        args = list(args)
        self.calls.append(args)
        out: object = ""
        if args[:3] == ["gh", "issue", "list"]:
            out = [self._row(issue) for issue in self.issues.values()]
        elif args[:3] == ["gh", "issue", "view"]:
            out = {"comments": self.comments[int(args[3])]}
        elif args[:3] == ["gh", "issue", "comment"]:
            body = args[args.index("--body") + 1]
            self.comments[int(args[3])].append(
                {"body": body, "viewerDidAuthor": True, "includesCreatedEdit": False}
            )
        elif args[:2] == ["gh", "api"]:
            path = next(a for a in args if "milestones" in a)
            if path.endswith("?state=open"):
                out = [m for m in self.milestones.values() if m["state"] == "open"]
            else:
                number = int(path.rsplit("/", 1)[1])
                if "PATCH" in args:
                    for i, arg in enumerate(args):
                        if arg == "-f":
                            key, _, value = args[i + 1].partition("=")
                            self.milestones[number][key] = value
                out = self.milestones[number]
        stdout = out if isinstance(out, str) else json.dumps(out)
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

    # -- edit-issue's own seams --

    def get_issue(self, number: int, _config: object) -> dict:
        issue = self.issues[number]
        return {
            "title": issue["title"],
            "body": issue["body"],
            "state": issue["state"],
            "labels": [{"name": name} for name in issue["labels"]],
            "milestone": self._native(issue),
        }

    def write_milestone(self, _config: object, *, issue_number: int, title: str) -> object:
        if issue_number in self.fail_milestone_write:
            return SimpleNamespace(ok=False, detail="gh issue edit --milestone failed")
        (number,) = [n for n, m in self.milestones.items() if m["title"] == title]
        self.issues[issue_number]["milestone"] = number
        return SimpleNamespace(ok=True, detail="")

    def apply_edit(
        self, issue_number: int, *, title: str, body: str, current_title: str, config: object
    ) -> bool:
        if issue_number in self.fail_body_write:
            return False
        self.issues[issue_number]["title"] = title
        self.issues[issue_number]["body"] = body
        return True

    # -- reads for the assertions --

    def first_line(self, number: int) -> str:
        return self.issues[number]["body"].split("\n", 1)[0]

    def writes(self) -> list[list[str]]:
        """The PATCH calls and comments: every gh call that changes something."""
        return [c for c in self.calls if "PATCH" in c or c[:3] == ["gh", "issue", "comment"]]

    def _native(self, issue: dict) -> dict | None:
        number = issue["milestone"]
        if number is None:
            return None
        return {"number": number, "title": self.milestones[number]["title"]}

    def _row(self, issue: dict) -> dict:
        return {
            "number": issue["number"],
            "title": issue["title"],
            "state": issue["state"],
            "body": issue["body"],
            "milestone": self._native(issue),
        }


def _repo(closing: dict | None = None, issues: list[dict] | None = None, *extra: dict) -> FakeRepo:
    milestones = [closing or _CLOSING, _NEXT, _LATER, _OTHER, *extra]
    return FakeRepo(milestones, _mixed_issues() if issues is None else issues)


def _wire(
    monkeypatch: pytest.MonkeyPatch,
    cm: ModuleType,
    repo: FakeRepo,
    *,
    today: dt.date = dt.date(2026, 7, 2),
) -> list[tuple[int, int, str]]:
    """Put the repository behind close-milestone's gh seams and record each move
    it hands to edit-issue as (issue, target, reason), answering success."""
    _pass_gates(monkeypatch, cm, CAP_ROOT)
    monkeypatch.setattr(cm, "load_adopter_config", lambda root: _CONFIG)
    monkeypatch.setattr(cm, "_today", lambda: today)
    for module in (cm, ms, containment):
        monkeypatch.setattr(module, "gh_run", repo.gh_run)
    moves: list[tuple[int, int, str]] = []

    def record(issue: int, target: int, reason: str, **_kwargs: object) -> int:
        moves.append((issue, target, reason))
        return 0

    monkeypatch.setattr(cm, "_run_edit_issue", record)
    return moves


def _wire_edit_issue(
    monkeypatch: pytest.MonkeyPatch, cm: ModuleType, ei: ModuleType, repo: FakeRepo
) -> list[int]:
    """Hand each move to the real edit-issue over the same repository; record
    the issues it ran for."""
    monkeypatch.setattr(ei, "resolve_capability_root", lambda _explicit: CAP_ROOT)
    monkeypatch.setattr(ei, "load_adopter_config", lambda _root: _CONFIG)
    monkeypatch.setattr(ei, "_read_members", lambda *a: [])
    monkeypatch.setattr(
        ei, "resolve_invoker_identity", lambda **k: SimpleNamespace(github_login="me")
    )
    monkeypatch.setattr(ei, "check_membership", lambda *a: SimpleNamespace(allowed=True))
    monkeypatch.setattr(ei.axis_labels, "load_substrate_map", lambda *_a, **_k: None)
    monkeypatch.setattr(ei, "gh_run", repo.gh_run)
    monkeypatch.setattr(ei, "_gh_get_issue", repo.get_issue)
    monkeypatch.setattr(ei, "write_milestone", repo.write_milestone)
    monkeypatch.setattr(ei, "_gh_apply_edit", repo.apply_edit)
    ran: list[int] = []

    def run(issue: int, target: int, reason: str, **_kwargs: object) -> int:
        ran.append(issue)
        argv = ["edit-issue", str(issue), "--milestone", str(target), "--reason", reason, "--yes"]
        monkeypatch.setattr(sys, "argv", argv)
        return ei.main()

    monkeypatch.setattr(cm, "_run_edit_issue", run)
    return ran


def _close(monkeypatch: pytest.MonkeyPatch, cm: ModuleType, *flags: str) -> int:
    monkeypatch.setattr(sys, "argv", ["close-milestone", "6", "--yes", *flags])
    return cm.main()


def _audit(repo: FakeRepo, number: int = 6) -> str:
    (line,) = [
        line
        for line in repo.milestones[number]["description"].splitlines()
        if line.startswith("Closed via")
    ]
    return line


def test_a_date_based_close_rolls_each_open_child_forward(cm, monkeypatch) -> None:
    repo = _repo()
    moves = _wire(monkeypatch, cm, repo)

    assert _close(monkeypatch, cm) == 0

    # The close first, then one move per open child; the closed child and the
    # other milestone's issue are not touched.
    (patch,) = repo.writes()
    assert patch[4].endswith("/milestones/6") and "state=closed" in patch
    assert [(issue, target) for issue, target, _ in moves] == [(11, 7), (12, 7)]
    assert all("close-milestone 6" in reason for _, _, reason in moves)
    assert "1 child issue(s) closed; 2 rolled forward to #7 Sprint 7: Polish)." in _audit(repo)


def test_an_inferred_date_based_close_rolls_forward(cm, monkeypatch) -> None:
    """No marker and a due date: inferred date-based, so it rolls forward too."""
    repo = _repo({**_CLOSING, "description": "Sprint notes", "due_on": _DUE})
    moves = _wire(monkeypatch, cm, repo)
    assert _close(monkeypatch, cm) == 0
    assert [issue for issue, _, _ in moves] == [11, 12]


def test_the_close_happens_before_the_moves(cm, monkeypatch) -> None:
    repo = _repo()
    order: list[str] = []
    _wire(monkeypatch, cm, repo)

    def close(number, description, config):
        order.append("close")
        return True

    def move(issue, target, reason, **_kwargs):
        order.append(f"move #{issue}")
        return 0

    monkeypatch.setattr(cm, "_gh_close_milestone", close)
    monkeypatch.setattr(cm, "_run_edit_issue", move)
    assert _close(monkeypatch, cm) == 0
    assert order == ["close", "move #11", "move #12"]


@pytest.mark.parametrize(
    "line",
    [
        pytest.param("Rollforward target: #9", id="by-number"),
        pytest.param("Rollforward target: Sprint 9: Later", id="by-title"),
    ],
)
def test_the_rollforward_target_line_wins_over_the_next_numbered(cm, monkeypatch, line) -> None:
    repo = _repo({**_CLOSING, "description": f"Close trigger: date-based\n{line}"})
    moves = _wire(monkeypatch, cm, repo)
    assert _close(monkeypatch, cm) == 0
    assert {target for _, target, _ in moves} == {9}
    assert "rolled forward to #9 Sprint 9: Later" in _audit(repo)


def test_target_wins_over_the_rollforward_target_line(cm, monkeypatch) -> None:
    repo = _repo({**_CLOSING, "description": "Close trigger: date-based\nRollforward target: #9"})
    moves = _wire(monkeypatch, cm, repo)
    assert _close(monkeypatch, cm, "--target", "Milestone 1: Outcome") == 0
    assert {target for _, target, _ in moves} == {8}


@pytest.mark.parametrize(
    ("closing", "extra", "message"),
    [
        pytest.param(
            {**_CLOSING, "title": "Sprint 9: Last"},
            (),
            "no open milestone of its category is numbered after it",
            id="no-candidate",
        ),
        pytest.param(
            _CLOSING,
            ({"number": 11, "title": "Sprint 7: Other half", "state": "open"},),
            "more than one open milestone could come next: #7 Sprint 7: Polish, "
            "#11 Sprint 7: Other half",
            id="two-candidates",
        ),
        pytest.param(
            {**_CLOSING, "description": "Close trigger: date-based\nRollforward target: #99"},
            (),
            "its `Rollforward target:` line names '99', which is not another OPEN milestone",
            id="target-line-names-no-open-milestone",
        ),
    ],
)
def test_without_a_single_target_nothing_is_moved_or_closed(
    cm, monkeypatch, capsys, closing, extra, message
) -> None:
    repo = _repo(closing, None, *extra)
    moves = _wire(monkeypatch, cm, repo)

    assert _close(monkeypatch, cm) == 1

    assert repo.writes() == [] and moves == []
    assert repo.milestones[6]["state"] == "open"
    err = capsys.readouterr().err
    assert message in err
    assert "Nothing was moved or closed" in err
    assert "close-milestone 6 --target <number|title>" in err


def test_naming_the_target_lets_the_close_go_ahead(cm, monkeypatch) -> None:
    repo = _repo(None, None, {"number": 11, "title": "Sprint 7: Other half", "state": "open"})
    moves = _wire(monkeypatch, cm, repo)
    assert _close(monkeypatch, cm, "--target", "11") == 0
    assert {target for _, target, _ in moves} == {11}
    assert repo.milestones[6]["state"] == "closed"


@pytest.mark.parametrize(
    "target", [pytest.param("99", id="no-such-milestone"), pytest.param("6", id="the-closing-one")]
)
def test_a_target_that_is_not_another_open_milestone_is_a_usage_error(
    cm, monkeypatch, target
) -> None:
    repo = _repo()
    moves = _wire(monkeypatch, cm, repo)
    assert _close(monkeypatch, cm, "--target", target) == 2
    assert repo.writes() == [] and moves == []


def test_dry_run_lists_every_move_and_writes_nothing(cm, monkeypatch, capsys) -> None:
    repo = _repo()
    moves = _wire(monkeypatch, cm, repo)

    assert _close(monkeypatch, cm, "--dry-run") == 0

    assert repo.writes() == [] and moves == []
    out = capsys.readouterr().out
    assert "rollforward:   → #7 Sprint 7: Polish" in out
    assert "#11 [task] [Task] in flight: #6 → #7" in out
    assert "#12 [task] [Task] not started: #6 → #7" in out
    assert "#10" not in out.split("rollforward:")[1]
    assert "2 rolled forward to #7 Sprint 7: Polish" in out


def test_an_open_child_assigned_to_another_milestone_is_left_alone(cm, monkeypatch, capsys) -> None:
    """Its native field names #8 and only its first line names #6: it sits in
    #8, so moving it would undo that."""
    issues = [_issue(14, "OPEN", title="[Task] moved by hand", milestone=8)]
    repo = _repo(None, issues)
    moves = _wire(monkeypatch, cm, repo)

    assert _close(monkeypatch, cm) == 0

    assert moves == []
    assert "#8 Milestone 1: Outcome" in capsys.readouterr().out
    assert "0 child issue(s) closed; 1 still open, not rolled forward)." in _audit(repo)


# --- either and content-based closes -------------------------------------


def test_an_either_close_past_its_due_date_rolls_forward(cm, monkeypatch) -> None:
    repo = _repo({**_CLOSING, "description": "Close trigger: either", "due_on": _DUE})
    moves = _wire(monkeypatch, cm, repo, today=dt.date(2026, 7, 2))
    assert _close(monkeypatch, cm) == 0
    assert [(issue, target) for issue, target, _ in moves] == [(11, 7), (12, 7)]
    assert "2 rolled forward to #7" in _audit(repo)


@pytest.mark.parametrize(
    ("description", "due_on"),
    [
        pytest.param("Close trigger: either", _DUE, id="either-before-its-due-date"),
        pytest.param("Close trigger: either", None, id="either-without-a-due-date"),
        pytest.param("Close trigger: content-based", _DUE, id="content-based"),
    ],
)
def test_open_children_hold_a_content_close_and_nothing_is_written(
    cm, monkeypatch, description, due_on
) -> None:
    repo = _repo({**_CLOSING, "description": description, "due_on": due_on})
    moves = _wire(monkeypatch, cm, repo, today=dt.date(2026, 6, 30))
    assert _close(monkeypatch, cm) == 1
    assert repo.writes() == [] and moves == []


@pytest.mark.parametrize("description", ["Close trigger: either", "Close trigger: content-based"])
def test_a_forced_content_close_moves_no_child(cm, monkeypatch, capsys, description) -> None:
    """A content close is unchanged: forced, it closes the Milestone and leaves
    the open children on it."""
    repo = _repo({**_CLOSING, "description": description, "due_on": _DUE})
    moves = _wire(monkeypatch, cm, repo, today=dt.date(2026, 6, 30))

    assert _close(monkeypatch, cm, "--force") == 0

    assert moves == []
    assert len(repo.writes()) == 1
    assert "1 child issue(s) closed; 2 still open, not rolled forward)." in _audit(repo)
    assert "edit-issue <n> --milestone <next>" in capsys.readouterr().err


def test_target_on_a_close_that_rolls_nothing_forward_is_a_usage_error(cm, monkeypatch) -> None:
    repo = _repo({**_CLOSING, "description": "Close trigger: content-based"})
    moves = _wire(monkeypatch, cm, repo)
    assert _close(monkeypatch, cm, "--force", "--target", "7") == 2
    assert repo.writes() == [] and moves == []


def test_a_date_based_close_with_no_open_child_needs_no_target(cm, monkeypatch) -> None:
    """Nothing to roll forward, so no target is looked for — a Milestone with no
    successor still closes."""
    issues = [_issue(10, "CLOSED", labels=("state:done",))]
    repo = _repo({**_CLOSING, "title": "Sprint 9: Last"}, issues)
    moves = _wire(monkeypatch, cm, repo)
    assert _close(monkeypatch, cm) == 0
    assert moves == []
    assert repo.milestones[6]["state"] == "closed"


# --- a failure, and the re-run that finishes it ---------------------------


def test_a_failed_move_leaves_the_target_recorded_for_a_re_run(cm, monkeypatch, capsys) -> None:
    repo = _repo()
    _wire(monkeypatch, cm, repo)
    attempts: list[int] = []

    def flaky(issue, target, reason, **_kwargs):
        attempts.append(issue)
        return 3 if issue == 11 else 0

    monkeypatch.setattr(cm, "_run_edit_issue", flaky)
    assert _close(monkeypatch, cm) == cm.EXIT_ROLLFORWARD_INCOMPLETE

    # Every move is attempted; the milestone is closed and names the target.
    assert attempts == [11, 12]
    assert repo.milestones[6]["state"] == "closed"
    assert cm._recorded_target(repo.milestones[6]["description"]) == 7
    err = capsys.readouterr().err
    assert "1 of 2 open child issue(s) rolled forward" in err
    assert "#11 did not move" in err
    assert "re-run `pkit project-management close-milestone 6`" in err


def test_a_re_run_on_a_closed_milestone_without_a_rollforward_record_is_a_noop(
    cm, monkeypatch
) -> None:
    """Closed by hand, or by an earlier version of the command: left as it is."""
    repo = _repo({**_CLOSING, "state": "closed", "description": "Closed by hand"})
    moves = _wire(monkeypatch, cm, repo)
    assert _close(monkeypatch, cm) == 0
    assert repo.writes() == [] and moves == []


# --- end to end: each move through the real edit-issue --------------------


def test_each_move_goes_through_edit_issue_and_keeps_the_state(cm, ei, monkeypatch) -> None:
    repo = _repo()
    _wire(monkeypatch, cm, repo)
    ran = _wire_edit_issue(monkeypatch, cm, ei, repo)
    labels_before = {n: list(i["labels"]) for n, i in repo.issues.items()}

    assert _close(monkeypatch, cm) == 0

    assert ran == [11, 12]
    # One audit comment each, naming the old Milestone, the new one and the
    # close. #12 sat in #6 through its first line alone, so the comment's
    # from-side — the native field — is empty and the reason names #6.
    from_sides = {11: "#6 Sprint 6: Ship it", 12: "(none)"}
    for number, from_side in from_sides.items():
        assert repo.issues[number]["milestone"] == 7
        assert repo.first_line(number) == _milestone_ref(7)
        (comment,) = repo.comments[number]
        assert f"Milestone: {from_side} → #7 Sprint 7: Polish" in comment["body"]
        assert (
            "reason: rolled forward from #6 when "
            "`pkit project-management close-milestone 6` closed it)" in comment["body"]
        )
    # The closed child stays as the record of what shipped; no label changes,
    # so every lifecycle state is what it was.
    assert repo.issues[10]["milestone"] == 6
    assert repo.first_line(10) == _milestone_ref(6)
    assert repo.comments[10] == []
    assert {n: i["labels"] for n, i in repo.issues.items()} == labels_before
    assert repo.milestones[6]["state"] == "closed"


def test_a_parent_on_the_closing_milestone_moves_with_its_open_children(
    cm, ei, monkeypatch
) -> None:
    """Feature #20 is assigned to #6 with one open and one closed Task: it moves
    with the open one, and the closed one stays as the record of partial
    delivery."""
    issues = [
        _issue(20, "OPEN", title="[Feature] Big piece", labels=("state:in-progress",)),
        _issue(21, "OPEN", first="Feature: #20", labels=("state:in-progress",)),
        _issue(22, "CLOSED", first="Feature: #20", labels=("state:done",)),
    ]
    repo = _repo(None, issues)
    _wire(monkeypatch, cm, repo)
    _wire_edit_issue(monkeypatch, cm, ei, repo)

    assert _close(monkeypatch, cm) == 0

    assert repo.issues[20]["milestone"] == 7
    assert repo.first_line(20) == _milestone_ref(7)
    assert repo.issues[21]["milestone"] == 7
    assert repo.first_line(21) == "Feature: #20"
    assert repo.issues[22]["milestone"] == 6
    assert "1 child issue(s) closed; 2 rolled forward to #7" in _audit(repo)


def test_rolled_forward_children_do_not_count_as_closed(cm, ei, monkeypatch) -> None:
    """The closure cascade counts only actually-closed children: a move closes
    nothing, and the audit line counts the moved children apart from the closed
    ones."""
    repo = _repo()
    _wire(monkeypatch, cm, repo)
    _wire_edit_issue(monkeypatch, cm, ei, repo)

    assert _close(monkeypatch, cm) == 0

    assert [n for n, i in repo.issues.items() if i["state"] == "CLOSED"] == [10]
    assert not any(c[:3] == ["gh", "issue", "close"] for c in repo.calls)
    assert "(trigger: date-based; 1 child issue(s) closed; 2 rolled forward" in _audit(repo)


@pytest.mark.parametrize(
    "failure",
    [
        pytest.param("fail_milestone_write", id="after-the-audit-comment"),
        pytest.param("fail_body_write", id="after-the-native-field"),
    ],
)
def test_a_re_run_finishes_the_rollforward_without_repeating_a_move_or_a_comment(
    cm, ei, monkeypatch, failure
) -> None:
    repo = _repo()
    _wire(monkeypatch, cm, repo)
    ran = _wire_edit_issue(monkeypatch, cm, ei, repo)
    getattr(repo, failure).add(12)

    assert _close(monkeypatch, cm) == cm.EXIT_ROLLFORWARD_INCOMPLETE
    assert repo.milestones[6]["state"] == "closed"
    assert repo.issues[11]["milestone"] == 7
    assert len(repo.comments[12]) == 1

    getattr(repo, failure).clear()
    ran.clear()
    assert _close(monkeypatch, cm) == 0

    # Only the child still on #6 is moved; neither child gets a second comment,
    # and the close is not recorded twice.
    assert ran == [12]
    assert repo.issues[12]["milestone"] == 7
    assert repo.first_line(12) == _milestone_ref(7)
    assert [len(repo.comments[n]) for n in (11, 12)] == [1, 1]
    assert repo.milestones[6]["description"].count("Closed via") == 1

    # A third run finds the rollforward complete.
    ran.clear()
    assert _close(monkeypatch, cm) == 0
    assert ran == []
