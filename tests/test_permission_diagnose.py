"""Tests for the permission-prompt diagnostic loop (PRJ-006).

Two halves under test:
  - the harness-side CAPTURE module (`.pkit/permissions/diagnose_capture.py`),
    imported the way the bare-python3 hook imports it — capture-on-deferred,
    capture-is-inert-on-failure, redaction, size-cap drop-oldest, TTL gating;
  - the CLI-side arm/disarm/status/report + classifier in
    `project_kit.permissions` — arm/disarm, TTL-expiry, classifier ordering,
    and that the report applies NOTHING (recommend-only).
"""
from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

import pytest

from project_kit import permissions as perm

REPO = Path(__file__).resolve().parent.parent
CAPTURE_SRC = REPO / ".pkit" / "permissions" / "diagnose_capture.py"


def _load_capture():
    """Import the propagated capture module the way the hook does (by path,
    bare-python3, no package context)."""
    spec = importlib.util.spec_from_file_location("diagnose_capture", CAPTURE_SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _proj(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / ".pkit" / "permissions" / "project").mkdir(parents=True)
    return root


def _arm(root: Path, **kwargs) -> None:
    perm.diagnose_on(root, **kwargs)


def _log(root: Path) -> list[dict]:
    return perm._diagnose_read_log(root)


def _bash(command: str, *, agent: str | None = None) -> dict:
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    if agent:
        payload["agent_type"] = agent
    return payload


# ---- arm / disarm / TTL-expiry (CLI side) ----------------------------------

def test_arm_writes_marker_and_status_reports_armed(tmp_path):
    root = _proj(tmp_path)
    _arm(root)
    assert perm._diagnose_marker_path(root).is_file()
    out = perm.diagnose_status(root)
    assert "ARMED" in out


def test_disarm_removes_marker(tmp_path):
    root = _proj(tmp_path)
    _arm(root)
    perm.diagnose_off(root)
    assert not perm._diagnose_marker_path(root).is_file()
    assert "OFF" in perm.diagnose_status(root)


def test_disarm_is_idempotent(tmp_path):
    root = _proj(tmp_path)
    # Off with no marker is a clean no-op.
    assert "already off" in perm.diagnose_off(root)


def test_ttl_expiry_reads_as_not_armed(tmp_path):
    root = _proj(tmp_path)
    _arm(root, ttl_seconds=1)
    marker = perm._diagnose_read_marker(root)
    # Just-armed → armed.
    assert perm._diagnose_is_armed(marker, time.time()) is True
    # A moment past the TTL window → expired.
    assert perm._diagnose_is_armed(marker, time.time() + 2) is False
    # status reflects EXPIRED when the wall clock is past the window.
    # (force an old armed_at so we don't have to sleep)
    perm._dump_yaml(perm._diagnose_marker_path(root), {
        "schema_version": 1, "armed_at": int(time.time()) - 10,
        "ttl_seconds": 1, "max_entries": 2000, "redact": True,
    })
    assert "EXPIRED" in perm.diagnose_status(root)


def test_arm_rejects_nonpositive_ttl(tmp_path):
    root = _proj(tmp_path)
    with pytest.raises(perm.PermissionsError):
        _arm(root, ttl_seconds=0)


# ---- capture on the deferred verdict (hook side) ---------------------------

def test_capture_appends_only_on_abstain(tmp_path):
    cap = _load_capture()
    root = _proj(tmp_path)
    _arm(root)
    # allow / deny are NOT captured (only the deferred/abstain verdict is).
    cap.capture(str(root), _bash("git status"), "allow", "allow grant")
    cap.capture(str(root), _bash("sudo rm x"), "deny", "guardrail")
    assert _log(root) == []
    # abstain IS captured.
    cap.capture(str(root), _bash("npm run build"), "abstain", "lenient: defer")
    log = _log(root)
    assert len(log) == 1
    assert log[0]["reason"] == "lenient: defer"
    assert log[0]["subject"] == "operator"


def test_capture_no_op_when_not_armed(tmp_path):
    cap = _load_capture()
    root = _proj(tmp_path)
    # No marker armed → nothing captured even on an abstain.
    cap.capture(str(root), _bash("npm run build"), "abstain", "lenient")
    assert _log(root) == []


def test_capture_no_op_when_expired(tmp_path):
    cap = _load_capture()
    root = _proj(tmp_path)
    perm._dump_yaml(perm._diagnose_marker_path(root), {
        "schema_version": 1, "armed_at": int(time.time()) - 100,
        "ttl_seconds": 1, "max_entries": 2000, "redact": True,
    })
    cap.capture(str(root), _bash("npm run build"), "abstain", "lenient")
    assert _log(root) == []


def test_capture_records_subagent_subject(tmp_path):
    cap = _load_capture()
    root = _proj(tmp_path)
    _arm(root)
    cap.capture(str(root), _bash("gh pr list", agent="project-manager"), "abstain", "lenient")
    assert _log(root)[0]["subject"] == "agent:project-manager"


# ---- capture-failure-is-inert ----------------------------------------------

def test_capture_failure_does_not_raise(tmp_path, monkeypatch):
    """A raised exception inside capture is swallowed — it can NEVER change a
    decision or break the hook's fail-open. We force `_append_capped` to raise
    and assert capture() returns cleanly and writes nothing."""
    cap = _load_capture()
    root = _proj(tmp_path)
    _arm(root)

    def _boom(*a, **k):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(cap, "_append_capped", _boom)
    # Must NOT raise — the whole point of the inert guard.
    cap.capture(str(root), _bash("npm run build"), "abstain", "lenient")
    # And nothing was written (the failing write left no partial state visible).
    assert _log(root) == []


def test_capture_inert_when_marker_unreadable(tmp_path, monkeypatch):
    """An unreadable/garbage marker must not raise; capture is a no-op."""
    cap = _load_capture()
    root = _proj(tmp_path)
    # Write a marker dir where the file is expected → read raises OSError-ish;
    # _read_marker returns None and capture no-ops.
    perm._diagnose_marker_path(root).mkdir()
    cap.capture(str(root), _bash("npm run build"), "abstain", "lenient")
    assert _log(root) == []


# ---- redaction --------------------------------------------------------------

def test_redaction_on_by_default_drops_command_tail(tmp_path):
    cap = _load_capture()
    root = _proj(tmp_path)
    _arm(root)  # redact defaults on
    cap.capture(str(root), _bash("curl -H token=SECRET https://api.example.com/x"),
                "abstain", "lenient")
    logged = _log(root)[0]["command"]
    assert "SECRET" not in logged
    assert "redacted" in logged
    assert logged.startswith("curl")  # head kept for classification


def test_redaction_preserves_shell_shape_signal(tmp_path):
    """Redaction must keep structural shell operators (`&&`, `|`, …) and the
    `for`/`while` keywords so the classifier can still see shell-shape — dropping
    them would silently misgroup a `cd … && …` as an allowlist-gap. Secrets/paths
    are still dropped."""
    cap = _load_capture()
    root = _proj(tmp_path)
    _arm(root)  # redact on
    cap.capture(str(root), _bash("cd foo && make build --prefix /secret/path"),
                "abstain", "lenient")
    logged = _log(root)[0]["command"]
    assert "&&" in logged, "structural operators must survive redaction"
    assert "/secret/path" not in logged
    assert perm._diagnose_classify({"command": logged}) == "shell-shape"


def test_no_redact_keeps_full_command(tmp_path):
    cap = _load_capture()
    root = _proj(tmp_path)
    _arm(root, redact=False)
    cap.capture(str(root), _bash("curl -H token=SECRET https://api.example.com/x"),
                "abstain", "lenient")
    logged = _log(root)[0]["command"]
    assert "SECRET" in logged
    assert "redacted" not in logged


# ---- size-cap drop-oldest ---------------------------------------------------

def test_size_cap_drops_oldest(tmp_path):
    cap = _load_capture()
    root = _proj(tmp_path)
    _arm(root, max_entries=3)
    for i in range(5):
        cap.capture(str(root), _bash(f"cmd{i}"), "abstain", "lenient")
    log = _log(root)
    assert len(log) == 3
    # Oldest two (cmd0, cmd1) dropped; the newest three kept in order.
    assert [r["command"] for r in log] == ["cmd2", "cmd3", "cmd4"]


# ---- classifier ordering ----------------------------------------------------

def test_classifier_groups_by_command_shape(tmp_path):
    assert perm._diagnose_classify({"command": "python3 gen.py …[redacted]"}) == "interpreter"
    assert perm._diagnose_classify({"command": "cd foo && make"}) == "shell-shape"
    assert perm._diagnose_classify({"command": "curl https://x"}) == "egress"
    assert perm._diagnose_classify({"command": "rmdir build"}) == "allowlist-gap"


def test_report_ranks_by_frequency_within_bands(tmp_path):
    cap = _load_capture()
    root = _proj(tmp_path)
    _arm(root, redact=False)
    # 3 egress (recommend band), 1 interpreter (judgement band).
    for _ in range(3):
        cap.capture(str(root), _bash("curl https://api.example.com"), "abstain", "lenient")
    cap.capture(str(root), _bash("python3 gen.py"), "abstain", "lenient")
    report = perm.diagnose_report(root)
    # The recommend band header precedes the judgement band header (band order),
    # and the top-ranked group is egress (3×).
    assert report.index("RECOMMENDED") < report.index("NEEDS YOUR JUDGEMENT")
    assert "egress" in report and "3×" in report
    assert "interpreter" in report


def test_report_states_coverage_not_a_prediction(tmp_path):
    cap = _load_capture()
    root = _proj(tmp_path)
    _arm(root)
    cap.capture(str(root), _bash("npm run build"), "abstain", "lenient")
    report = perm.diagnose_report(root)
    assert "SUPERSET" in report or "COVERAGE" in report


def test_report_empty_when_no_log(tmp_path):
    root = _proj(tmp_path)
    out = perm.diagnose_report(root)
    assert "nothing captured" in out


# ---- recommend-only: the report applies NOTHING -----------------------------

def test_report_applies_nothing(tmp_path, monkeypatch):
    """The MVP is recommend-only — `report` must not mutate the model, settings,
    grants, the sandbox, or the catalog. We assert every mutation entry point in
    `permissions` is untouched while a report runs over a populated log."""
    cap = _load_capture()
    root = _proj(tmp_path)
    _arm(root, redact=False)
    cap.capture(str(root), _bash("curl https://api.example.com"), "abstain", "lenient")
    cap.capture(str(root), _bash("python3 gen.py"), "abstain", "lenient")

    tripped: list[str] = []
    for name in ("grant", "revoke", "set_mode", "apply", "enable",
                 "sandbox_enable", "accommodate", "_apply_allowances",
                 "_write_settings", "_dump_yaml"):
        def _trip(*a, _n=name, **k):
            tripped.append(_n)

        monkeypatch.setattr(perm, name, _trip)

    perm.diagnose_report(root)
    assert tripped == [], f"recommend-only report mutated state via: {tripped}"
