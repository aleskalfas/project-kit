"""Tests for project-management's `promote-issue` workflow wrapper (DEC-026).

Focused on the wrapper-specific gates and helpers — the state-transition
mechanics live in `move-issue.py` and are tested separately.

Regression tests for #61 (optional --milestone, DEC-026 amendment):
  - milestone-omitted happy path (promote on --reason alone)
  - milestone-given happy path (resolve + attach, unchanged)
  - given-but-unresolvable milestone (still an error, never silently downgraded)
  - missing --reason (argparse error)
"""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "scripts"
    / "promote-issue.py"
)


@pytest.fixture(scope="module")
def pi():
    """Load promote-issue.py via importlib."""
    lib_dir = SCRIPT.parent
    sys.path.insert(0, str(lib_dir))
    spec = importlib.util.spec_from_file_location("pm_promote_issue_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_promote_issue_under_test"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(lib_dir))


# ---- milestone resolution (moved to _lib/milestone.py in #217) ---------
#
# `_parse_concatenated_json_arrays` and `_milestone_exists_open` were
# extracted to `_lib/milestone.py` as part of #217's symmetry fix
# (both create-issue and promote-issue now use the lib resolver).
# Direct coverage lives in `tests/test_pm_milestone.py`; the
# tests that previously sat here were dropped along with the
# wrapper-local functions.


# ---- _detect_state_from_labels (idempotency path, #219) ----------------


def test_detect_state_from_labels_returns_bare_state(pi, monkeypatch) -> None:
    """Issue with `state:backlog` label → returns `"backlog"`."""
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(
            args=args, returncode=0,
            stdout=json.dumps({
                "labels": [
                    {"name": "type:bug"},
                    {"name": "state:backlog"},
                    {"name": "priority:Medium"},
                ],
            }),
            stderr="",
        )
    monkeypatch.setattr(pi, "gh_run", fake_gh_run)
    assert pi._detect_state_from_labels(42, {}) == "backlog"


def test_detect_state_from_labels_none_when_no_state_label(pi, monkeypatch) -> None:
    """No `state:*` label → returns None (the issue is at the implicit Todo state)."""
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(
            args=args, returncode=0,
            stdout=json.dumps({"labels": [{"name": "type:bug"}]}),
            stderr="",
        )
    monkeypatch.setattr(pi, "gh_run", fake_gh_run)
    assert pi._detect_state_from_labels(42, {}) is None


def test_detect_state_from_labels_gh_failure_returns_none(pi, monkeypatch) -> None:
    """gh view failure → None (caller treats as "unknown state, proceed to transition")."""
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(
            args=args, returncode=1, stdout="", stderr="boom",
        )
    monkeypatch.setattr(pi, "gh_run", fake_gh_run)
    assert pi._detect_state_from_labels(42, {}) is None


def test_detect_state_from_labels_recognises_in_progress(pi, monkeypatch) -> None:
    """All four post-Todo states are recognised — promote-issue exits cleanly on any of them."""
    for state in ("backlog", "in-progress", "review", "done"):
        def fake_gh_run(args, config, _state=state, **kwargs):
            import subprocess
            return subprocess.CompletedProcess(
                args=args, returncode=0,
                stdout=json.dumps({"labels": [{"name": f"state:{_state}"}]}),
                stderr="",
            )
        monkeypatch.setattr(pi, "gh_run", fake_gh_run)
        assert pi._detect_state_from_labels(42, {}) == state, (
            f"state:{state} label not recognised"
        )


# ---- _post_audit_comment_idempotent -----------------------------------


def test_post_audit_comment_skips_when_stamp_exists(pi, monkeypatch, capsys) -> None:
    calls: list = []

    def fake_gh_run(args, config, **kwargs):
        import subprocess
        calls.append(args)
        if "view" in args:
            return subprocess.CompletedProcess(
                args=args, returncode=0,
                stdout=json.dumps({
                    "comments": [
                        {"body": "Random comment"},
                        {"body": f"{pi.AUDIT_STAMP}\n\nPromoted Todo → Backlog ..."},
                    ]
                }),
                stderr="",
            )
        # `gh issue comment` — should NOT be called if stamp exists
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(pi, "gh_run", fake_gh_run)
    result = pi._post_audit_comment_idempotent(42, "ignored", {})
    assert result is True
    # `gh issue comment` shouldn't have been called.
    assert not any("comment" in args and "view" not in args for args in calls)


def test_post_audit_comment_posts_when_absent(pi, monkeypatch) -> None:
    calls: list = []

    def fake_gh_run(args, config, **kwargs):
        import subprocess
        calls.append(args)
        if "view" in args:
            return subprocess.CompletedProcess(
                args=args, returncode=0,
                stdout=json.dumps({"comments": []}), stderr="",
            )
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(pi, "gh_run", fake_gh_run)
    result = pi._post_audit_comment_idempotent(42, "test body", {})
    assert result is True
    # `gh issue comment` was called.
    assert any(args[1:3] == ["issue", "comment"] for args in calls)


def test_post_audit_comment_propagates_failure(pi, monkeypatch, capsys) -> None:
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        if "view" in args:
            return subprocess.CompletedProcess(
                args=args, returncode=0,
                stdout=json.dumps({"comments": []}), stderr="",
            )
        return subprocess.CompletedProcess(
            args=args, returncode=1, stdout="", stderr="comment failed"
        )

    monkeypatch.setattr(pi, "gh_run", fake_gh_run)
    result = pi._post_audit_comment_idempotent(42, "test", {})
    assert result is False
    assert "gh issue comment failed" in capsys.readouterr().err


# ---- _attach_milestone -------------------------------------------------


def _substrate_writes_module(pi):
    """The substrate-writes primitive `promote-issue` routes its milestone write
    through (ADR-031). `_attach_milestone` now constructs + executes the write via
    this module, so the `gh` call lands on the primitive's `_gh_call`, not on
    `pi.gh_run` — patch it there."""
    return sys.modules[pi.write_milestone.__module__]


def test_attach_milestone_success(pi, monkeypatch) -> None:
    def fake_gh_call(args, config):
        import subprocess
        assert args[1:5] == ["issue", "edit", "42", "--milestone"]
        assert args[5] == "v1.0"
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(_substrate_writes_module(pi), "_gh_call", fake_gh_call)
    assert pi._attach_milestone(42, "v1.0", {}) is True


def test_attach_milestone_failure(pi, monkeypatch, capsys) -> None:
    def fake_gh_call(args, config):
        import subprocess
        return subprocess.CompletedProcess(
            args=args, returncode=1, stdout="", stderr="cannot attach"
        )

    monkeypatch.setattr(_substrate_writes_module(pi), "_gh_call", fake_gh_call)
    assert pi._attach_milestone(42, "v1.0", {}) is False
    assert "cannot attach" in capsys.readouterr().err


# ---- main() integration: #61 regression suite -------------------------
#
# Tests exercise main() end-to-end, mocking out all I/O and subprocess
# calls so no gh access is required. This covers the two-path contract:
#   - --milestone omitted  → reason-only path (no milestone resolution, no attach)
#   - --milestone given    → resolve + attach (unchanged from pre-#61)
#   - bad milestone given  → error exit, never silently downgraded
#   - --reason missing     → argparse error (exit 2)


@dataclass
class _FakeMembership:
    allowed: bool = True
    refusal_message: str | None = None


@dataclass
class _FakeMilestone:
    number: int
    title: str


def _wire_main_mocks(
    pi,
    monkeypatch,
    *,
    sys_argv: list[str],
    milestone_obj=None,      # None → resolve_milestone returns None (unresolvable)
    milestone_resolve_called: list | None = None,
    attach_called: list | None = None,
    comment_result: bool = True,
    move_issue_rc: int = 0,
    current_state: str | None = None,
) -> None:
    """Wire all main() dependencies with controllable fakes."""
    monkeypatch.setattr(sys, "argv", sys_argv)
    monkeypatch.setattr(pi, "resolve_capability_root", lambda _: Path("/fake/cap"))
    monkeypatch.setattr(pi, "load_adopter_config", lambda _: {})
    monkeypatch.setattr(pi, "_read_members", lambda *_a, **_k: [])
    monkeypatch.setattr(pi, "resolve_invoker_identity", lambda **_k: MagicMock())
    monkeypatch.setattr(pi, "check_membership", lambda *_a: _FakeMembership(allowed=True))

    def fake_resolve_milestone(arg, config):
        if milestone_resolve_called is not None:
            milestone_resolve_called.append(arg)
        return milestone_obj

    monkeypatch.setattr(pi, "resolve_milestone", fake_resolve_milestone)

    def fake_attach(issue_number, title, config):
        if attach_called is not None:
            attach_called.append(title)
        return True

    monkeypatch.setattr(pi, "_attach_milestone", fake_attach)
    monkeypatch.setattr(pi, "_post_audit_comment_idempotent", lambda *_a, **_k: comment_result)
    monkeypatch.setattr(pi, "_detect_state_from_labels", lambda *_a: current_state)
    monkeypatch.setattr(pi, "_invoke_move_issue", lambda *_a, **_k: move_issue_rc)


# --- milestone-omitted happy path (acceptance criterion 1) ---


def test_main_milestone_omitted_promotes_exit_zero(pi, monkeypatch) -> None:
    """promote-issue <n> --reason '...' (no --milestone) exits 0."""
    _wire_main_mocks(
        pi, monkeypatch,
        sys_argv=["promote-issue", "42", "--reason", "PM triage", "--yes"],
    )
    assert pi.main() == 0


def test_main_milestone_omitted_skips_resolve(pi, monkeypatch) -> None:
    """resolve_milestone must NOT be called when --milestone is omitted."""
    resolve_calls: list = []
    _wire_main_mocks(
        pi, monkeypatch,
        sys_argv=["promote-issue", "42", "--reason", "triage", "--yes"],
        milestone_resolve_called=resolve_calls,
    )
    pi.main()
    assert resolve_calls == [], "resolve_milestone must not be called when --milestone is absent"


def test_main_milestone_omitted_skips_attach(pi, monkeypatch) -> None:
    """_attach_milestone must NOT be called when --milestone is omitted."""
    attached: list = []
    _wire_main_mocks(
        pi, monkeypatch,
        sys_argv=["promote-issue", "42", "--reason", "triage", "--yes"],
        attach_called=attached,
    )
    pi.main()
    assert attached == [], "_attach_milestone must not be called when --milestone is absent"


def test_main_milestone_omitted_calls_move_issue(pi, monkeypatch, capsys) -> None:
    """move-issue --to backlog is still called on the reason-only path."""
    move_calls: list = []
    original_invoke = pi._invoke_move_issue

    def capturing_invoke(issue_number, target, cap_root):
        move_calls.append((issue_number, target))
        return 0

    _wire_main_mocks(
        pi, monkeypatch,
        sys_argv=["promote-issue", "42", "--reason", "triage", "--yes"],
    )
    monkeypatch.setattr(pi, "_invoke_move_issue", capturing_invoke)
    rc = pi.main()
    assert rc == 0
    assert move_calls == [(42, "backlog")]


def test_main_milestone_omitted_ok_line_says_no_milestone(pi, monkeypatch, capsys) -> None:
    """The [ok] line must not claim a milestone when none was given."""
    _wire_main_mocks(
        pi, monkeypatch,
        sys_argv=["promote-issue", "42", "--reason", "triage", "--yes"],
    )
    pi.main()
    out = capsys.readouterr().out
    assert "no milestone" in out
    # Must not mention a specific milestone title
    assert "milestone:" not in out or "(none" in out


# --- milestone-given happy path (acceptance criterion 2, unchanged) ---


def test_main_milestone_given_resolves_and_attaches(pi, monkeypatch) -> None:
    """promote-issue <n> --milestone '<open-title>' --reason '...' → resolves + attaches."""
    resolve_calls: list = []
    attached: list = []
    _wire_main_mocks(
        pi, monkeypatch,
        sys_argv=["promote-issue", "42", "--milestone", "Sprint 1", "--reason", "PM approved", "--yes"],
        milestone_obj=_FakeMilestone(number=7, title="Sprint 1"),
        milestone_resolve_called=resolve_calls,
        attach_called=attached,
    )
    rc = pi.main()
    assert rc == 0
    assert resolve_calls == ["Sprint 1"]
    assert attached == ["Sprint 1"]


def test_main_milestone_given_ok_line_shows_milestone(pi, monkeypatch, capsys) -> None:
    """[ok] line reports the milestone title when one was attached."""
    _wire_main_mocks(
        pi, monkeypatch,
        sys_argv=["promote-issue", "42", "--milestone", "Sprint 1", "--reason", "approved", "--yes"],
        milestone_obj=_FakeMilestone(number=7, title="Sprint 1"),
    )
    pi.main()
    out = capsys.readouterr().out
    assert "Sprint 1" in out


# --- given-but-unresolvable milestone (acceptance criterion 3) ---


def test_main_bad_milestone_errors_not_silently_downgraded(pi, monkeypatch, capsys) -> None:
    """An unresolvable --milestone is an error; never silently downgraded to milestone-free."""
    _wire_main_mocks(
        pi, monkeypatch,
        sys_argv=["promote-issue", "42", "--milestone", "nonexistent", "--reason", "r", "--yes"],
        milestone_obj=None,  # resolve returns None → unresolvable
    )
    rc = pi.main()
    assert rc == 2
    err = capsys.readouterr().err
    assert "nonexistent" in err
    assert "OPEN" in err


def test_main_bad_milestone_does_not_call_attach(pi, monkeypatch) -> None:
    """When milestone resolution fails, _attach_milestone must not be called."""
    attached: list = []
    _wire_main_mocks(
        pi, monkeypatch,
        sys_argv=["promote-issue", "42", "--milestone", "bad", "--reason", "r", "--yes"],
        milestone_obj=None,
        attach_called=attached,
    )
    pi.main()
    assert attached == []


def test_main_bad_milestone_does_not_call_move_issue(pi, monkeypatch) -> None:
    """When milestone resolution fails, move-issue must not be called."""
    move_calls: list = []

    def capturing_invoke(issue_number, target, cap_root):
        move_calls.append(target)
        return 0

    _wire_main_mocks(
        pi, monkeypatch,
        sys_argv=["promote-issue", "42", "--milestone", "bad", "--reason", "r", "--yes"],
        milestone_obj=None,
    )
    monkeypatch.setattr(pi, "_invoke_move_issue", capturing_invoke)
    pi.main()
    assert move_calls == []


# --- --reason required (acceptance criterion 4) ---


def test_main_reason_required_exits_nonzero(pi, monkeypatch) -> None:
    """Omitting --reason must produce a non-zero exit (argparse SystemExit)."""
    monkeypatch.setattr(sys, "argv", ["promote-issue", "42"])
    monkeypatch.setattr(pi, "resolve_capability_root", lambda _: Path("/fake/cap"))
    monkeypatch.setattr(pi, "load_adopter_config", lambda _: {})
    monkeypatch.setattr(pi, "_read_members", lambda *_a, **_k: [])
    monkeypatch.setattr(pi, "resolve_invoker_identity", lambda **_k: MagicMock())
    monkeypatch.setattr(pi, "check_membership", lambda *_a: _FakeMembership(allowed=True))
    with pytest.raises(SystemExit) as exc_info:
        pi.main()
    assert exc_info.value.code != 0
