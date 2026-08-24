"""Tests for project-management's context-workstream read verb (pkit ADR-050).

Covers the branch → issue → workstream-label derivation and the exit-0 degrade
contract (nothing printed on any miss), with `git`/`gh` monkeypatched.

The degrade contract is now "exit 0 on every MISS", not "exit 0 always": since
#747 the verb is gated like every other non-exempt pm verb, so an
un-bootstrapped project gets a refusal (exit 2) rather than a silently empty
answer — a workstream derived from assumed defaults would be confidently wrong.
The backbone's report-compose consumer already treats any non-zero exit as "no
workstream", so the degrade path it relies on is unchanged. `_run_main`
neutralises the gate for the derivation tests; the two tests at the bottom pin
the gated behaviour itself.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "scripts"
    / "context-workstream.py"
)


@pytest.fixture(scope="module")
def cw():
    """Load context-workstream.py as a module via importlib."""
    module_name = "pm_context_workstream_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _run_main(cw, monkeypatch, capsys, *, argv: list[str] | None = None):
    """Drive main() with the #747 prerequisite gate neutralised.

    These tests target the branch → issue → workstream derivation, which
    presupposes a bootstrapped project; the gate itself is pinned separately
    below (and in test_pm_bootstrap_gate*.py).
    """
    monkeypatch.setattr(cw.bootstrap_gate, "enforce", lambda *a, **kw: True)
    monkeypatch.setattr(sys, "argv", ["context-workstream.py", *(argv or [])])
    code = cw.main()
    out = capsys.readouterr()
    return code, out.out, out.err


# --- pure derivation helpers -----------------------------------------


def test_issue_number_from_branch_shapes(cw) -> None:
    assert cw._issue_number_from_branch("feat/644-context") == 644
    assert cw._issue_number_from_branch("fix/7-x") == 7
    assert cw._issue_number_from_branch("main") is None
    assert cw._issue_number_from_branch("feat/no-number") is None
    assert cw._issue_number_from_branch(None) is None
    assert cw._issue_number_from_branch("") is None


# --- the always-exit-0 degrade contract ------------------------------


def test_prints_workstream_on_happy_path(
    cw, monkeypatch, capsys, tmp_path: Path
) -> None:
    monkeypatch.setattr(cw, "_current_branch", lambda: "feat/644-context")
    monkeypatch.setattr(cw, "resolve_capability_root", lambda explicit: tmp_path)
    monkeypatch.setattr(cw, "load_adopter_config", lambda root: {})
    captured: dict = {}

    def fake_get_issue(number, config, *, fields):
        captured["number"] = number
        captured["fields"] = fields
        return {"labels": [{"name": "type:feature"}, {"name": "workstream:cli"}]}

    monkeypatch.setattr(cw, "gh_get_issue", fake_get_issue)
    code, out, _err = _run_main(cw, monkeypatch, capsys)
    assert code == 0
    assert out == "cli\n"  # the bare value, nothing else
    assert captured["number"] == 644
    assert captured["fields"] == "labels"


def test_silent_on_non_issue_branch(cw, monkeypatch, capsys) -> None:
    monkeypatch.setattr(cw, "_current_branch", lambda: "main")

    def explode(*a, **k):  # pragma: no cover - must not be reached
        raise AssertionError("no gh call for a non-issue-shaped branch")

    monkeypatch.setattr(cw, "gh_get_issue", explode)
    code, out, _err = _run_main(cw, monkeypatch, capsys)
    assert code == 0 and out == ""


def test_silent_when_capability_root_missing(cw, monkeypatch, capsys) -> None:
    monkeypatch.setattr(cw, "_current_branch", lambda: "feat/1-x")
    monkeypatch.setattr(cw, "resolve_capability_root", lambda explicit: None)
    code, out, _err = _run_main(cw, monkeypatch, capsys)
    assert code == 0 and out == ""


def test_silent_on_gh_failure(cw, monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cw, "_current_branch", lambda: "feat/1-x")
    monkeypatch.setattr(cw, "resolve_capability_root", lambda explicit: tmp_path)
    monkeypatch.setattr(cw, "load_adopter_config", lambda root: {})
    monkeypatch.setattr(cw, "gh_get_issue", lambda *a, **k: None)
    code, out, _err = _run_main(cw, monkeypatch, capsys)
    assert code == 0 and out == ""


def test_silent_when_issue_has_no_workstream_label(
    cw, monkeypatch, capsys, tmp_path: Path
) -> None:
    monkeypatch.setattr(cw, "_current_branch", lambda: "feat/1-x")
    monkeypatch.setattr(cw, "resolve_capability_root", lambda explicit: tmp_path)
    monkeypatch.setattr(cw, "load_adopter_config", lambda root: {})
    monkeypatch.setattr(
        cw, "gh_get_issue",
        lambda *a, **k: {"labels": [{"name": "type:feature"}]},
    )
    code, out, _err = _run_main(cw, monkeypatch, capsys)
    assert code == 0 and out == ""


def test_silent_when_git_unavailable(cw, monkeypatch, capsys) -> None:
    monkeypatch.setattr(cw, "_current_branch", lambda: None)
    code, out, _err = _run_main(cw, monkeypatch, capsys)
    assert code == 0 and out == ""


# --- the prerequisite gate (#747) ------------------------------------


def test_unbootstrapped_project_refuses_and_prints_nothing(
    cw, monkeypatch, capsys, tmp_path: Path
) -> None:
    """An un-bootstrapped project gets a REFUSAL, not an empty answer: a
    workstream read off assumed kit labels would misreport an adopter who
    remapped them (the silent-wrong-answer shape #747 closes). Nothing reaches
    stdout, so a consumer that only reads stdout still sees "no workstream"."""
    monkeypatch.setattr(cw, "_current_branch", lambda: "feat/644-context")
    monkeypatch.setattr(cw, "resolve_capability_root", lambda explicit: tmp_path)

    def explode(*a, **k):  # pragma: no cover — must not be reached
        raise AssertionError("no gh call before the prerequisite gate passes")

    monkeypatch.setattr(cw, "gh_get_issue", explode)
    monkeypatch.setattr(
        sys, "argv", ["context-workstream.py", "--capability-root", str(tmp_path)]
    )
    code = cw.main()
    captured = capsys.readouterr()
    assert code == 2
    assert captured.out == ""
    assert "prerequisites are not met" in captured.err


def test_the_gate_runs_before_the_branch_read(cw, monkeypatch, capsys) -> None:
    """The refusal precedes even the local `git branch` read, so a gated
    invocation does no work at all."""

    def explode() -> str:  # pragma: no cover — must not be reached
        raise AssertionError("no branch read before the prerequisite gate passes")

    monkeypatch.setattr(cw, "_current_branch", explode)
    monkeypatch.setattr(
        cw.bootstrap_gate, "enforce", lambda *a, **kw: False
    )
    monkeypatch.setattr(sys, "argv", ["context-workstream.py"])
    assert cw.main() == 2
