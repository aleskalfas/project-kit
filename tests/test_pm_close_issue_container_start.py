"""close-issue --mode=cascade-eligibility-close checks where the container starts (#3248).

DEC-006's table starts a container's cascade-eligibility close at In Progress.
The close once checked no starting state, so a container behind the work under
it, or one whose card placed it nowhere, was closed and journaled from wherever
it stood. It now goes on only from In Progress: a container in Todo or Backlog is
refused, naming the moves of its own that bring it level
([project-management:DEC-075-cascade-unread-ancestor]); one at Review, or at
Done while open, is refused as a state set outside the lifecycle; and, where the
board holds the state, one whose card places it nowhere is refused, nothing
guessed (DEC-051 point 6). Where the project keeps no position for the state,
nothing is checked. Every `gh` call is faked; the journal entry against the real
engine is test_pm_close_issue_journal's.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CAP_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPT_PATH = CAP_ROOT / "scripts" / "close-issue.py"

CLOSE = ["42", "--mode", "cascade-eligibility-close", "--yes"]

#: What every refusal of a container's start says.
STARTS_AT_IN_PROGRESS = "DEC-006's table starts a container's close at In Progress"

#: A map that puts the state on the board.
ON_THE_BOARD: dict[str, Any] = {"state": {"board": True}}

#: Maps under which the project keeps no position for the state.
NO_POSITION = [
    pytest.param({"state": {"derive": {"from": "open-closed"}}}, id="derive-bound"),
    pytest.param({"state": {"unsupported": True}}, id="unsupported"),
    pytest.param({"type": {"kit-label": True}}, id="left-out"),
]


@pytest.fixture(scope="module")
def ci() -> ModuleType:
    module_name = "pm_close_issue_container_start_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _container(*labels: str, milestone: dict[str, Any] | None = None) -> dict[str, Any]:
    """Feature #42, under EPIC #10, every criterion ticked, carrying ``labels``."""
    return {
        "title": "[Feature] Ship the widgets",
        "body": "EPIC: #10\n\n## What\nx\n\n## Acceptance criteria\n\n- [x] shipped\n",
        "state": "OPEN",
        "labels": [{"name": n} for n in labels],
        "milestone": milestone,
    }


def _run(
    ci: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    issue: dict[str, Any],
    *,
    axes: dict[str, Any] | None = None,
    card: Any = None,
    argv: list[str] | None = None,
) -> SimpleNamespace:
    """Run main() on ``issue`` with every gate passed and every child closed;
    record each `gh` write and each move handed to the engine. ``axes`` is the
    substrate map, none by default; with ``card``, a `StatusRead`, the open
    container's card reads as ``card``."""
    monkeypatch.setattr(sys, "argv", ["close-issue", *(argv or CLOSE)])
    monkeypatch.setattr(ci, "resolve_capability_root", lambda _explicit: CAP_ROOT)
    monkeypatch.setattr(ci.bootstrap_gate, "enforce", lambda *a, **k: True)
    monkeypatch.setattr(ci.session_guard, "enforce", lambda **k: True)
    monkeypatch.setattr(ci, "load_adopter_config", lambda _root: {})
    monkeypatch.setattr(ci, "_read_members", lambda *a: [])
    monkeypatch.setattr(
        ci,
        "resolve_invoker_identity",
        lambda **k: SimpleNamespace(github_login="me", unresolved_cause=None),
    )
    monkeypatch.setattr(ci, "check_membership", lambda *a: SimpleNamespace(allowed=True))
    substrate_map = None if axes is None else ci.axis_labels.SubstrateMap(axes=axes)
    monkeypatch.setattr(ci.axis_labels, "load_substrate_map", lambda *_a, **_k: substrate_map)
    if card is not None:
        monkeypatch.setattr(ci.issue_position, "read_status", lambda *_a, **_k: card)
    monkeypatch.setattr(ci, "fire_hooks", lambda *a, **k: None)
    journaled: list[tuple[Any, ...]] = []
    monkeypatch.setattr(ci, "journal_move", lambda *a, **k: journaled.append(a))
    issues = {42: issue}
    monkeypatch.setattr(ci, "_gh_get_issue", lambda n, _config: issues.get(n))
    monkeypatch.setattr(ci, "_engine_cascade_fold", lambda _n: {"opened": True})
    monkeypatch.setattr(ci, "_report_parents", lambda *a, **k: None)
    writes: list[list[str]] = []

    def fake_gh_run(cmd: list[str], config: dict[str, Any], **kwargs: Any):
        if cmd[:3] != ["gh", "issue", "view"]:
            writes.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(ci, "gh_run", fake_gh_run)
    rc = ci.main()
    return SimpleNamespace(rc=rc, writes=writes, journaled=journaled)


def _closed(rec: SimpleNamespace) -> bool:
    return ["gh", "issue", "close", "42", "--reason", "completed"] in rec.writes


# --- where the labels carry the state ---------------------------------------------


def test_a_container_in_progress_closes(ci, monkeypatch) -> None:
    rec = _run(ci, monkeypatch, _container("state:in-progress"))
    assert rec.rc == 0
    assert _closed(rec)
    assert [move[:3] for move in rec.journaled] == [(42, "in-progress", "done")]


def test_a_container_in_backlog_is_refused_and_named_the_move_that_brings_it_level(
    ci, monkeypatch, capsys
) -> None:
    rec = _run(ci, monkeypatch, _container("state:backlog"))
    assert rec.rc == 1
    assert rec.writes == [] and rec.journaled == []
    err = capsys.readouterr().err
    assert (
        f"[refused] close-issue #42: the container stands in Backlog, and {STARTS_AT_IN_PROGRESS}"
        in err
    )
    assert "It stands behind the work under it. Nothing was changed" in err
    assert (
        "→ Bring it level by a move of its own, then close it: move-issue 42 --to in-progress."
    ) in err
    assert 'close it as won\'t do: close-issue 42 --reason "<R>".' in err


def test_a_container_in_todo_is_named_its_scheduling_first(ci, monkeypatch, capsys) -> None:
    """A container in Todo needs scheduling of its own, which the person holds,
    though the scheduling given on the work under it covered it (DEC-006)."""
    rec = _run(ci, monkeypatch, _container())
    assert rec.rc == 1
    assert rec.writes == []
    err = capsys.readouterr().err
    assert "the container stands in Todo" in err
    assert (
        "→ Bring it level by moves of its own, then close it: promote-issue 42, the "
        "scheduling the person authorises, then move-issue 42 --to in-progress."
    ) in err


def test_a_container_in_a_milestone_with_no_label_stands_in_backlog(
    ci, monkeypatch, capsys
) -> None:
    rec = _run(ci, monkeypatch, _container(milestone={"number": 6, "title": "Widgets"}))
    assert rec.rc == 1
    assert "the container stands in Backlog" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("label", "name"),
    [
        pytest.param("state:review", "Review", id="review"),
        pytest.param("state:done", "Done", id="done"),
    ],
)
def test_an_open_container_past_in_progress_is_refused_as_set_outside_the_lifecycle(
    ci, monkeypatch, capsys, label: str, name: str
) -> None:
    rec = _run(ci, monkeypatch, _container(label))
    assert rec.rc == 1
    assert rec.writes == [] and rec.journaled == []
    err = capsys.readouterr().err
    assert f"the container stands in {name}, and {STARTS_AT_IN_PROGRESS}" in err
    assert "its state was set outside the lifecycle" in err
    assert "→ Set its state to In Progress by hand" in err


def test_a_dry_run_is_refused_the_same_way(ci, monkeypatch, capsys) -> None:
    argv = ["42", "--mode", "cascade-eligibility-close", "--dry-run"]
    rec = _run(ci, monkeypatch, _container("state:backlog"), argv=argv)
    assert rec.rc == 1
    assert rec.writes == []
    assert "[dry-run]" not in capsys.readouterr().out


# --- where the board holds the state ------------------------------------------------


def test_a_card_in_progress_closes_whatever_the_label_says(ci, monkeypatch) -> None:
    card = ci.infer.StatusRead("placed", state="in-progress")
    rec = _run(ci, monkeypatch, _container("state:todo"), axes=ON_THE_BOARD, card=card)
    assert rec.rc == 0
    assert _closed(rec)
    assert [move[:3] for move in rec.journaled] == [(42, "in-progress", "done")]


def test_a_card_in_backlog_is_refused(ci, monkeypatch, capsys) -> None:
    card = ci.infer.StatusRead("placed", state="backlog")
    rec = _run(ci, monkeypatch, _container("state:in-progress"), axes=ON_THE_BOARD, card=card)
    assert rec.rc == 1
    assert rec.writes == []
    assert "the container stands in Backlog" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("outcome", "said", "rc", "finding"),
    [
        pytest.param(
            "unreadable",
            "gh: timeout",
            3,
            "the board's Status of #42 could not be read",
            id="unread",
        ),
        pytest.param("no-card", "", 1, "#42 has no card on the board", id="no-card"),
        pytest.param("unset", "", 1, "#42's card on the board has no Status", id="unset"),
        pytest.param(
            "not-open", "Done", 1, "has the Status 'Done', which names no open state", id="not-open"
        ),
    ],
)
def test_a_card_that_places_the_container_nowhere_refuses_the_close(
    ci, monkeypatch, capsys, outcome: str, said: str, rc: int, finding: str
) -> None:
    """Nothing tells whether the container is In Progress then, so nothing is
    guessed: no write, no move journaled (DEC-051 point 6)."""
    card = ci.infer.StatusRead(outcome, said=said)
    rec = _run(ci, monkeypatch, _container("state:in-progress"), axes=ON_THE_BOARD, card=card)
    assert rec.rc == rc
    assert rec.writes == [] and rec.journaled == []
    err = capsys.readouterr().err
    assert "[refused] close-issue #42: " in err
    assert finding in err
    assert "Nothing was changed (the container is still open)" in err


# --- where the project keeps no position for the state ---------------------------


@pytest.mark.parametrize("axes", NO_POSITION)
def test_with_no_position_kept_the_close_checks_none(ci, monkeypatch, axes) -> None:
    """Open is then the only position a container has, so its close goes on."""
    rec = _run(ci, monkeypatch, _container(milestone={"number": 6, "title": "Widgets"}), axes=axes)
    assert rec.rc == 0
    assert _closed(rec)
