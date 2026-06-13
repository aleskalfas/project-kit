"""Tests for `review-pr` (DEC-028 local-agent invocation)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management"
    / "scripts" / "review-pr.py"
)


@pytest.fixture(scope="module")
def rpr():
    lib_dir = SCRIPT.parent
    sys.path.insert(0, str(lib_dir))
    spec = importlib.util.spec_from_file_location("pm_review_pr_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_review_pr_under_test"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(lib_dir))


# ---- _get_local_registered ----------------------------------------


def test_local_registered_returns_list(rpr) -> None:
    config = {"review": {"agents": {"local_registered": [
        {"name": "critic"},
        {"name": "security-review"},
    ]}}}
    result = rpr._get_local_registered(config)
    assert len(result) == 2
    assert result[0]["name"] == "critic"


def test_local_registered_empty_when_absent(rpr) -> None:
    assert rpr._get_local_registered({}) == []
    assert rpr._get_local_registered({"review": {}}) == []
    assert rpr._get_local_registered({"review": {"agents": {}}}) == []


def test_local_registered_filters_entries_without_name(rpr) -> None:
    config = {"review": {"agents": {"local_registered": [
        {"name": "critic"},
        {"other_field": "x"},  # no name
        {"name": ""},  # empty name
        {"name": "code-review"},
    ]}}}
    result = rpr._get_local_registered(config)
    assert [e["name"] for e in result] == ["critic", "code-review"]


def test_local_registered_handles_non_dict_review(rpr) -> None:
    assert rpr._get_local_registered({"review": "lol"}) == []


# ---- _format_verdict_comment ------------------------------------


def test_format_verdict_approved(rpr) -> None:
    out = rpr._format_verdict_comment("critic", "APPROVED", "")
    assert out == "Reviewer agent (local, critic): APPROVED"


def test_format_verdict_with_body(rpr) -> None:
    out = rpr._format_verdict_comment(
        "critic", "CHANGES_REQUESTED", "Three findings:\n1. fix X\n2. fix Y",
    )
    assert out.startswith("Reviewer agent (local, critic): CHANGES_REQUESTED\n\n")
    assert "Three findings" in out


def test_format_verdict_strips_blank_body(rpr) -> None:
    """Whitespace-only body is omitted."""
    out = rpr._format_verdict_comment("critic", "APPROVED", "  \n  \n")
    assert out == "Reviewer agent (local, critic): APPROVED"


# ---- _post_comment ----------------------------------------------


def test_post_comment_returns_false_on_none_pr(rpr) -> None:
    assert rpr._post_comment(None, "body", {}) is False


def test_post_comment_propagates_gh_failure(rpr, monkeypatch, capsys) -> None:
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(
            args=args, returncode=1, stdout="", stderr="not authorised",
        )
    monkeypatch.setattr(rpr, "gh_run", fake_gh_run)
    assert rpr._post_comment(99, "body", {}) is False
    assert "not authorised" in capsys.readouterr().err


def test_post_comment_success(rpr, monkeypatch) -> None:
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
    monkeypatch.setattr(rpr, "gh_run", fake_gh_run)
    assert rpr._post_comment(99, "body", {}) is True
