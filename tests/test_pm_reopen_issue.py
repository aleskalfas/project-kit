"""reopen-issue puts the issue back into the lifecycle (#1049).

`done` is terminal in workflow.yaml, so a reopen does not transition out of it:
it removes the state label(s) and the issue is read again as any open issue
without one — `backlog` with a milestone, `todo` without. An open issue still
labelled done (the stuck case met on #1065) is repaired the same way. Every
`gh` call is faked.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CAP_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPT_PATH = CAP_ROOT / "scripts" / "reopen-issue.py"


@pytest.fixture(scope="module")
def ri():
    module_name = "pm_reopen_issue_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _issue(*, state="CLOSED", labels=("state:done", "type:bug"), milestone=None) -> dict:
    return {
        "title": "[Bug] came back",
        "state": state,
        "labels": [{"name": n} for n in labels],
        "milestone": milestone,
    }


def _run(ri, monkeypatch, argv: list[str], issue: dict, *, config=None, substrate_map=None,
         fail_label_edit=False) -> SimpleNamespace:
    monkeypatch.setattr(sys, "argv", ["reopen-issue", *argv])
    monkeypatch.setattr(ri, "resolve_capability_root", lambda _explicit: CAP_ROOT)
    monkeypatch.setattr(ri.bootstrap_gate, "enforce", lambda *a, **k: True)
    monkeypatch.setattr(ri.session_guard, "enforce", lambda **k: True)
    monkeypatch.setattr(ri, "load_adopter_config", lambda _root: config or {})
    monkeypatch.setattr(ri, "_read_members", lambda *a: [])
    monkeypatch.setattr(ri, "resolve_invoker_identity", lambda **k: SimpleNamespace(github_login="me"))
    monkeypatch.setattr(ri, "check_membership", lambda *a: SimpleNamespace(allowed=True))
    monkeypatch.setattr(ri.axis_labels, "load_substrate_map", lambda *_a, **_k: substrate_map)
    monkeypatch.setattr(ri, "_gh_get_issue", lambda _n, _config: issue)
    calls: list[list[str]] = []

    def fake_gh_run(cmd, config, **kwargs):
        calls.append(cmd)
        rc = 1 if (fail_label_edit and cmd[:3] == ["gh", "issue", "edit"]) else 0
        return subprocess.CompletedProcess(cmd, rc, stdout="", stderr="")

    monkeypatch.setattr(ri, "gh_run", fake_gh_run)
    return SimpleNamespace(rc=ri.main(), calls=calls)


def test_reopen_without_milestone_resets_to_todo(ri, monkeypatch, capsys) -> None:
    rec = _run(ri, monkeypatch, ["42", "--yes"], _issue())
    assert rec.rc == 0
    assert ["gh", "issue", "reopen", "42"] in rec.calls
    assert ["gh", "issue", "edit", "42", "--remove-label", "state:done"] in rec.calls
    # The reopen happens before the reset: a reset without a reopen would leave
    # a closed issue reading done anyway.
    assert rec.calls.index(["gh", "issue", "reopen", "42"]) < rec.calls.index(
        ["gh", "issue", "edit", "42", "--remove-label", "state:done"]
    )
    assert "its state is now todo" in capsys.readouterr().out


def test_reopen_with_milestone_resets_to_backlog(ri, monkeypatch, capsys) -> None:
    rec = _run(ri, monkeypatch, ["42", "--yes"], _issue(milestone={"number": 5, "title": "M5"}))
    assert rec.rc == 0
    assert "its state is now backlog" in capsys.readouterr().out


def test_every_state_label_is_removed(ri, monkeypatch) -> None:
    """A stale non-terminal label left beside done would otherwise win the
    position read once the issue is open."""
    rec = _run(ri, monkeypatch, ["42", "--yes"], _issue(labels=("state:review", "state:done")))
    assert ["gh", "issue", "edit", "42", "--remove-label", "state:review",
            "--remove-label", "state:done"] in rec.calls


def test_an_open_issue_stuck_at_done_is_repaired(ri, monkeypatch, capsys) -> None:
    rec = _run(ri, monkeypatch, ["42", "--yes"], _issue(state="OPEN"))
    assert rec.rc == 0
    assert ["gh", "issue", "reopen", "42"] not in rec.calls
    assert ["gh", "issue", "edit", "42", "--remove-label", "state:done"] in rec.calls
    assert "repaired #42" in capsys.readouterr().out


def test_an_open_issue_in_work_is_a_noop(ri, monkeypatch, capsys) -> None:
    rec = _run(ri, monkeypatch, ["42", "--yes"], _issue(state="OPEN", labels=("state:in-progress",)))
    assert rec.rc == 0
    assert rec.calls == []
    assert "[noop]" in capsys.readouterr().out


def test_a_failed_reset_says_how_to_finish(ri, monkeypatch, capsys) -> None:
    rec = _run(ri, monkeypatch, ["42", "--yes"], _issue(), fail_label_edit=True)
    assert rec.rc == 3
    assert "re-run reopen-issue to finish" in capsys.readouterr().err


def test_dry_run_writes_nothing(ri, monkeypatch) -> None:
    rec = _run(ri, monkeypatch, ["42", "--dry-run"], _issue())
    assert rec.rc == 0
    assert rec.calls == []


def test_derived_state_strips_no_label(ri, monkeypatch) -> None:
    """Under a derive-bound state, open/closed carries it: reopening is the
    whole reset, and no label is touched."""
    smap = ri.axis_labels.SubstrateMap(
        axes={"state": {"derive": {"from": "open-closed", "states": {"done": "closed"}}}}
    )
    rec = _run(ri, monkeypatch, ["42", "--yes"], _issue(), substrate_map=smap)
    assert rec.rc == 0
    assert ["gh", "issue", "reopen", "42"] in rec.calls
    assert not any(c[:3] == ["gh", "issue", "edit"] for c in rec.calls)


def test_board_state_is_left_with_a_note(ri, monkeypatch, capsys) -> None:
    rec = _run(ri, monkeypatch, ["42", "--yes"], _issue(), config={"has_projects_v2_board": True})
    assert rec.rc == 0
    assert not any(c[:3] == ["gh", "issue", "edit"] for c in rec.calls)
    assert "Projects-v2 board" in capsys.readouterr().out


def test_the_reason_comment_still_precedes_the_reopen(ri, monkeypatch) -> None:
    rec = _run(ri, monkeypatch, ["42", "--reason", "regressed", "--yes"], _issue())
    assert rec.calls[0][:3] == ["gh", "issue", "comment"]
    assert rec.calls[1] == ["gh", "issue", "reopen", "42"]
