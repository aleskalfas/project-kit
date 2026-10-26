"""project-management's migrate: a label-delete refuses while an issue of work uses the label.

A `label-delete` change with `refuse_if_used` (its default) lists the issues that
carry the label first. The listing runs through the one read of issues, which
leaves a state issue out by its marker (DEC-058 point 3, #2139), so a label
that only state issues carry is not in use. `gh` is stood in for at
`subprocess.run`, so no test reaches GitHub.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts" / "migrate.py"

MARKER = "<!-- pkit:state-issue v=1 key=seat-planner -->"


@pytest.fixture(scope="module")
def mg():
    module_name = "pm_migrate_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _gh(mg, monkeypatch, *, listed=None, list_code: int = 0) -> list[list[str]]:
    """Answer `gh issue list` with `listed` and `gh label delete` with success;
    return every call made."""
    calls: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(list(cmd))
        if list(cmd[:3]) == ["gh", "issue", "list"]:
            limit = int(cmd[cmd.index("--limit") + 1])
            rows = (listed or [])[:limit]
            return subprocess.CompletedProcess(cmd, list_code, stdout=json.dumps(rows), stderr="")
        if list(cmd[:3]) == ["gh", "label", "delete"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected call: {cmd}")

    monkeypatch.setattr(mg.subprocess, "run", fake_run)
    return calls


def _deleted(calls: list[list[str]]) -> bool:
    return any(call[:3] == ["gh", "label", "delete"] for call in calls)


CHANGE = {"kind": "label-delete", "label": "old-label"}


def test_a_label_an_issue_of_work_uses_is_not_deleted(mg, monkeypatch) -> None:
    calls = _gh(mg, monkeypatch, listed=[{"number": 7, "body": "## What\n"}])
    result = mg._execute_label_delete(dict(CHANGE))
    assert result.status == "failed"
    assert "still used by at least one issue" in result.detail
    assert not _deleted(calls)


def test_a_label_only_a_state_issue_carries_is_deleted(mg, monkeypatch) -> None:
    calls = _gh(mg, monkeypatch, listed=[{"number": 512, "body": f"{MARKER}\n"}])
    result = mg._execute_label_delete(dict(CHANGE))
    assert result.status == "applied"
    assert _deleted(calls)


def test_an_issue_of_work_behind_a_state_issue_still_holds_the_label(mg, monkeypatch) -> None:
    calls = _gh(
        mg,
        monkeypatch,
        listed=[{"number": 512, "body": f"{MARKER}\n"}, {"number": 7, "body": ""}],
    )
    assert mg._execute_label_delete(dict(CHANGE)).status == "failed"
    assert not _deleted(calls)


def test_a_full_page_of_state_issues_still_holds_the_label(mg, monkeypatch) -> None:
    """The issues past a full page were never read, so one of work may be there."""
    states = [{"number": n, "body": f"{MARKER}\n"} for n in range(1, mg._LABEL_USE_PAGE + 2)]
    calls = _gh(mg, monkeypatch, listed=states)
    assert mg._execute_label_delete(dict(CHANGE)).status == "failed"
    assert not _deleted(calls)


def test_an_unused_label_is_deleted(mg, monkeypatch) -> None:
    calls = _gh(mg, monkeypatch, listed=[])
    assert mg._execute_label_delete(dict(CHANGE)).status == "applied"
    assert _deleted(calls)
    assert calls[0][-2:] == ["--json", "number,body"]


def test_a_failed_listing_does_not_hold_the_delete(mg, monkeypatch) -> None:
    """As before: the check refuses only on a listing that answered."""
    calls = _gh(mg, monkeypatch, listed=[{"number": 7, "body": ""}], list_code=1)
    assert mg._execute_label_delete(dict(CHANGE)).status == "applied"
    assert _deleted(calls)


def test_no_listing_when_the_change_allows_a_used_label(mg, monkeypatch) -> None:
    calls = _gh(mg, monkeypatch, listed=[{"number": 7, "body": ""}])
    result = mg._execute_label_delete({**CHANGE, "refuse_if_used": False})
    assert result.status == "applied"
    assert [call[:3] for call in calls] == [["gh", "label", "delete"]]
