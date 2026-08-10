"""Tests for project-management's context-workstream read verb (pkit ADR-050).

Covers the branch → issue → workstream-label derivation and the always-exit-0
degrade contract (nothing printed on any miss), with `git`/`gh` monkeypatched.
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
