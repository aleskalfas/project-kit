"""Tests for project-management's close-milestone script.

Covers the pure close-trigger resolution + decision policy, the audit-note
composition, milestone→child resolution (native field + textual ref union),
and — mirroring the AC — content-based close with all children closed
(succeeds), with an open child (refuses), --dry-run previews without
mutating, the audit note is written on a real close, and the gh mutation
routes through the validated `_lib.gh` seam (monkeypatched).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
)
SCRIPT_PATH = SCRIPTS_DIR / "close-milestone.py"

# The script does `sys.path.insert(0, <scripts dir>)` and `from _lib...`; make
# the same dir importable here so loading the module by file path resolves it.
sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture(scope="module")
def cm():
    """Load close-milestone.py as a module via importlib."""
    module_name = "pm_close_milestone_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


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


def test_parse_close_trigger_reads_marker(cm) -> None:
    assert cm._parse_close_trigger("Close trigger: content-based\n\nbody") == "content-based"
    assert cm._parse_close_trigger("Close trigger: date-based") == "date-based"
    assert cm._parse_close_trigger("Close trigger: either\n") == "either"


def test_parse_close_trigger_absent_returns_none(cm) -> None:
    assert cm._parse_close_trigger("Just a plain description") is None
    assert cm._parse_close_trigger("") is None
    # A non-first-line marker does not count (DEC-016: first line).
    assert cm._parse_close_trigger("intro\nClose trigger: date-based") is None


def test_infer_close_trigger_uses_due_date(cm) -> None:
    assert cm._infer_close_trigger("2026-07-01T23:59:59Z") == "date-based"
    assert cm._infer_close_trigger(None) == "content-based"
    assert cm._infer_close_trigger("") == "content-based"


def test_resolve_close_trigger_marker_wins_over_inference(cm) -> None:
    due = "2026-07-01T00:00:00Z"
    # Marker present → not inferred, even with a due date.
    assert cm._resolve_close_trigger("Close trigger: content-based", due) == (
        "content-based", False,
    )
    # No marker → inferred from the due date.
    assert cm._resolve_close_trigger("no marker here", due) == ("date-based", True)


# --- decision policy -------------------------------------------------


def test_decide_content_based_all_closed_proceeds(cm) -> None:
    d = cm._decide_close("content-based", has_open_children=False, force=False)
    assert d.proceed is True
    assert d.rollforward_warning is False


def test_decide_content_based_open_child_refuses(cm) -> None:
    d = cm._decide_close("content-based", has_open_children=True, force=False)
    assert d.proceed is False
    assert d.exit_code == 1


def test_decide_content_based_force_overrides(cm) -> None:
    d = cm._decide_close("content-based", has_open_children=True, force=True)
    assert d.proceed is True
    assert d.rollforward_warning is True


def test_decide_either_open_child_refuses_unless_forced(cm) -> None:
    assert cm._decide_close("either", has_open_children=True, force=False).proceed is False
    assert cm._decide_close("either", has_open_children=True, force=True).proceed is True


def test_decide_date_based_open_child_warns_and_proceeds(cm) -> None:
    d = cm._decide_close("date-based", has_open_children=True, force=False)
    assert d.proceed is True
    assert d.rollforward_warning is True


def test_decide_no_open_children_always_proceeds(cm) -> None:
    for trigger in ("content-based", "date-based", "either"):
        assert cm._decide_close(trigger, has_open_children=False, force=False).proceed is True


# --- audit note ------------------------------------------------------


def test_compose_close_description_appends_audit_line(cm) -> None:
    out = cm._compose_close_description(
        "Close trigger: content-based\n\nSprint 6",
        close_trigger="content-based",
        closed_count=3,
        open_count=0,
    )
    assert "Close trigger: content-based" in out
    assert cm._AUDIT_MARKER in out
    assert "3 child issue(s) closed" in out


def test_compose_close_description_notes_rolled_forward(cm) -> None:
    out = cm._compose_close_description(
        "",
        close_trigger="date-based",
        closed_count=2,
        open_count=1,
    )
    assert cm._AUDIT_MARKER in out
    assert "1 rolled forward" in out


def test_compose_close_description_is_idempotent(cm) -> None:
    once = cm._compose_close_description(
        "desc", close_trigger="content-based", closed_count=1, open_count=0
    )
    twice = cm._compose_close_description(
        once, close_trigger="content-based", closed_count=1, open_count=0
    )
    assert once == twice
    assert once.count(cm._AUDIT_MARKER) == 1


# --- milestone → child resolution (native + textual union) -----------


def _patch_issue_list(monkeypatch, cm, rows) -> None:
    """Stub gh_run so _gh_list_milestone_children sees a fixed issue list."""
    proc = MagicMock()
    proc.returncode = 0
    proc.stdout = __import__("json").dumps(rows)
    monkeypatch.setattr(cm, "gh_run", lambda *a, **k: proc)


def _row(number, state, *, title="[EPIC] X", body="", milestone=None):
    return {
        "number": number,
        "title": title,
        "state": state,
        "body": body,
        "milestone": milestone,
    }


def test_children_resolved_via_native_field(cm, monkeypatch, issue_types) -> None:
    _patch_issue_list(monkeypatch, cm, [
        _row(10, "CLOSED", milestone={"number": 6}),
        _row(11, "OPEN", milestone={"number": 99}),
    ])
    children = cm._gh_list_milestone_children(6, "Milestone 6: Sprint", {}, issue_types)
    assert [c["number"] for c in children] == [10]
    assert children[0]["type"] == "epic"
    assert children[0]["state"] == "closed"


def test_children_resolved_via_textual_ref(cm, monkeypatch, issue_types) -> None:
    body = "Milestone: [#6](../milestone/6)\n\n## Acceptance criteria\n"
    _patch_issue_list(monkeypatch, cm, [
        _row(20, "OPEN", body=body),
        _row(21, "OPEN", body="Milestone: [#7](../milestone/7)"),
    ])
    children = cm._gh_list_milestone_children(6, "Milestone 6: Sprint", {}, issue_types)
    assert [c["number"] for c in children] == [20]


def test_children_union_dedups_and_sorts(cm, monkeypatch, issue_types) -> None:
    body = "Milestone: [#6](../milestone/6)"
    _patch_issue_list(monkeypatch, cm, [
        _row(30, "CLOSED", body=body, milestone={"number": 6}),
        _row(12, "CLOSED", milestone={"number": 6}),
    ])
    children = cm._gh_list_milestone_children(6, "Milestone 6: Sprint", {}, issue_types)
    # Present in both substrates → counted once; sorted by number.
    assert [c["number"] for c in children] == [12, 30]


def test_children_gh_failure_returns_none(cm, monkeypatch, issue_types) -> None:
    proc = MagicMock()
    proc.returncode = 1
    proc.stderr = "boom"
    monkeypatch.setattr(cm, "gh_run", lambda *a, **k: proc)
    assert cm._gh_list_milestone_children(6, "t", {}, issue_types) is None


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
    monkeypatch.setattr(cm, "resolve_capability_root", lambda p: REPO_ROOT)
    monkeypatch.setattr(cm, "load_adopter_config", lambda root: {})
    monkeypatch.setattr(cm, "_read_members", lambda root, loader: [])
    monkeypatch.setattr(cm, "resolve_invoker_identity", lambda config=None: "tester")
    monkeypatch.setattr(cm, "check_membership", lambda members, invoker: MagicMock(allowed=True))
    monkeypatch.setattr(cm.session_guard, "enforce", lambda override=False: True)
    monkeypatch.setattr(cm, "_read_yaml", lambda path, loader: {
        "types": {"epic": {"title_prefix": "EPIC", "title_case": "upper"}}
    })
    monkeypatch.setattr(cm, "_gh_get_milestone", lambda n, config: milestone)
    monkeypatch.setattr(cm, "_gh_list_milestone_children", lambda n, t, config, types: children)
    close_mock = MagicMock(return_value=True)
    monkeypatch.setattr(cm, "_gh_close_milestone", close_mock)
    return close_mock


def _args(**over):
    base = dict(
        milestone="6",
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
