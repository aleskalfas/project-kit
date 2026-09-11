"""Tests for the pm `history` command (DEC-049 — journal render + drift)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / ".pkit/capabilities/project-management/scripts/history.py"
)


@pytest.fixture(scope="module")
def hist():
    spec = importlib.util.spec_from_file_location("pm_history_under_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_history_under_test"] = module
    spec.loader.exec_module(module)
    return module


class _Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_render_entry_uses_ts_actor_move_trigger(hist) -> None:
    entry = {
        "ts": "2026-08-12T08:00:00+00:00", "actor": "alice",
        "from": "backlog", "to": "in-progress", "trigger": "start-work",
    }
    out = hist._render_entry(entry)
    assert "2026-08-12T08:00:00+00:00" in out
    assert "alice" in out and "backlog → in-progress" in out and "(start-work)" in out


def test_render_entry_shows_version_when_present(hist) -> None:
    # #697 adds `version`; render it when present.
    out = hist._render_entry({"actor": "a", "to": "done", "version": "1.147.0"})
    assert "[pkit 1.147.0]" in out


def test_read_journal_parses_process_status_json(hist, monkeypatch) -> None:
    payload = {"journal": [{"actor": "a", "to": "done"}]}

    def fake_run(cmd, **kwargs):
        assert cmd[:3] == ["pkit", "process", "status"]
        return _Proc(0, json.dumps(payload))

    monkeypatch.setattr(hist.subprocess, "run", fake_run)
    assert hist._read_journal(42) == [{"actor": "a", "to": "done"}]


def test_read_journal_none_on_failure(hist, monkeypatch) -> None:
    monkeypatch.setattr(hist.subprocess, "run", lambda cmd, **k: _Proc(1, "", "boom"))
    assert hist._read_journal(42) is None


def test_timeline_state_adds_filters_state_labels(hist, monkeypatch) -> None:
    events = [
        {"event": "labeled", "label": {"name": "state:backlog"},
         "actor": {"login": "alice"}, "created_at": "t1"},
        {"event": "labeled", "label": {"name": "type:feature"},  # not state:*
         "actor": {"login": "alice"}, "created_at": "t2"},
        {"event": "commented"},  # not a label event
    ]
    monkeypatch.setattr(hist, "gh_run", lambda *a, **k: _Proc(0, json.dumps(events)))
    out = hist._timeline_state_adds(42, {})
    assert len(out) == 1 and out[0]["label"] == "state:backlog" and out[0]["actor"] == "alice"


def test_report_drift_clean_when_journal_covers_timeline(hist, monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        hist, "_timeline_state_adds",
        lambda n, c, m=None: [{"created_at": "t", "actor": "a", "label": "state:done"}],
    )
    journal = [{"to": "done"}]  # 1 governed >= 1 observed
    rc = hist._report_drift(42, journal, {})
    assert rc == 0 and "no ungoverned state changes" in capsys.readouterr().out


def test_report_drift_flags_unmatched(hist, monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        hist, "_timeline_state_adds",
        lambda n, c, m=None: [
            {"created_at": "t1", "actor": "a", "label": "state:backlog"},
            {"created_at": "t2", "actor": "a", "label": "state:done"},
        ],
    )
    rc = hist._report_drift(42, journal=[], config={})  # 0 governed, 2 observed
    out = capsys.readouterr().out
    assert rc == 3
    assert "2 state-label change(s)" in out and "state:backlog" in out


def test_report_drift_gh_failure_returns_2(hist, monkeypatch) -> None:
    monkeypatch.setattr(hist, "_timeline_state_adds", lambda n, c, m=None: None)
    assert hist._report_drift(42, [], {}) == 2


# --- carriage-aware state labels (DEC-051 decision point 4) ---------------


def test_timeline_state_adds_reads_the_adopters_own_state_labels(
    hist, monkeypatch
) -> None:
    """THE BUG: a `label`-bound `state` carries `Ready` / `Inbox`, which the
    inline `startswith("state:")` never matched — `pkit pm history --check-drift`
    saw zero state changes on a repo full of them."""
    smap = hist.axis_labels.SubstrateMap(
        axes={"state": {"label": {"remap": {"backlog": "Ready", "todo": "Inbox"}}}}
    )
    events = [
        {"event": "labeled", "label": {"name": "Ready"},
         "actor": {"login": "alice"}, "created_at": "t1"},
        {"event": "labeled", "label": {"name": "state:done"},  # stale kit label
         "actor": {"login": "alice"}, "created_at": "t2"},
        {"event": "labeled", "label": {"name": "type:feature"},
         "actor": {"login": "alice"}, "created_at": "t3"},
    ]
    monkeypatch.setattr(hist, "gh_run", lambda *a, **k: _Proc(0, json.dumps(events)))
    out = hist._timeline_state_adds(42, {}, smap)
    # Both the adopter's own label AND a stale kit one are observed changes —
    # the seam's union rule for a repo mid-adoption.
    assert [e["label"] for e in out] == ["Ready", "state:done"]


def test_report_drift_skips_when_no_label_carries_state(hist, monkeypatch, capsys) -> None:
    """Board-carried state: the timeline's label events cannot observe it, so the
    check must SAY it did not run rather than print a clean bill of health off an
    empty scan. Exit 0 — this is a correct configuration, not a failure — and no
    `gh` call is made."""
    def must_not_run(*_a, **_k):  # pragma: no cover - must not run
        raise AssertionError("no timeline read for a non-label state substrate")

    monkeypatch.setattr(hist, "_timeline_state_adds", must_not_run)
    rc = hist._report_drift(42, [], {"has_projects_v2_board": True})
    out = capsys.readouterr().out
    assert rc == 0
    assert "SKIPPED" in out and "board" in out
    assert "no ungoverned state changes" not in out


def test_report_drift_skips_for_a_derive_bound_state(hist, monkeypatch, capsys) -> None:
    """Same for a `derive` binding — open/closed carries state, not a label."""
    smap = hist.axis_labels.SubstrateMap(
        axes={"state": {"derive": {"from": "open-closed", "states": {"done": "closed"}}}}
    )

    def must_not_run(*_a, **_k):  # pragma: no cover - must not run
        raise AssertionError("no timeline read for a derive-bound state")

    monkeypatch.setattr(hist, "_timeline_state_adds", must_not_run)
    assert hist._report_drift(42, [], {}, smap) == 0
    assert "SKIPPED" in capsys.readouterr().out
