"""Tests for the `pkit report` composition logic (PRJ-008 / ADR-047)."""

from __future__ import annotations

import urllib.parse
from pathlib import Path

import pytest

from project_kit.report import (
    KINDS,
    REPORT_TARGET,
    build_new_issue_url,
    compose_report,
    compose_report_body,
)


def test_compose_report_body_includes_prose_and_env() -> None:
    body = compose_report_body(
        "Something broke on upgrade.",
        "## Environment\n\n```\nbackbone:      1.143.1\n```\n",
    )
    assert "Something broke on upgrade." in body
    assert "## Environment" in body
    assert "backbone:      1.143.1" in body
    assert "Reported for" not in body


def test_compose_report_body_attribution_normalizes_handle() -> None:
    body = compose_report_body("prose", "## Environment\n", on_behalf_of="@mike")
    assert "Reported for @mike" in body
    assert "@@mike" not in body  # leading @ stripped, not doubled


def test_build_new_issue_url_encodes_params() -> None:
    url = build_new_issue_url(
        "owner/repo", title="Bug: sandbox", body="line1\nline2", label="bug"
    )
    assert url.startswith("https://github.com/owner/repo/issues/new?")
    q = urllib.parse.parse_qs(url.split("?", 1)[1])
    assert q["title"] == ["Bug: sandbox"]
    assert q["body"] == ["line1\nline2"]
    assert q["labels"] == ["bug"]


def test_compose_report_ties_env_and_url(tmp_path: Path) -> None:
    (tmp_path / ".pkit").mkdir()
    body, url = compose_report("bug", title="T", prose="P", target_root=tmp_path)
    assert "## Environment" in body
    assert "P" in body
    assert REPORT_TARGET in url
    assert "issues/new?" in url


def test_compose_report_feedback_kind_labels_feedback(tmp_path: Path) -> None:
    (tmp_path / ".pkit").mkdir()
    _, url = compose_report("feedback", title="T", prose="P", target_root=tmp_path)
    q = urllib.parse.parse_qs(url.split("?", 1)[1])
    assert q["labels"] == ["feedback"]


def test_compose_report_unknown_kind_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        compose_report("nope", title="T", prose="P", target_root=tmp_path)


def test_kinds_are_bug_and_feedback() -> None:
    assert set(KINDS) == {"bug", "feedback"}


# --- CLI (URL-first path) --------------------------------------------

from click.testing import CliRunner  # noqa: E402

from project_kit.cli import main  # noqa: E402


def test_cli_report_bug_prints_prefilled_url() -> None:
    res = CliRunner().invoke(
        main, ["report", "bug", "--title", "sandbox bug", "--body", "it broke"]
    )
    assert res.exit_code == 0, res.output
    assert f"issues/new?" in res.output
    assert REPORT_TARGET in res.output
    assert "labels=bug" in res.output
    assert "environment block" in res.output.lower()


def test_cli_report_feedback_labels_feedback() -> None:
    res = CliRunner().invoke(
        main, ["report", "feedback", "--title", "t", "--body", "some thoughts"]
    )
    assert res.exit_code == 0, res.output
    assert "labels=feedback" in res.output


def test_cli_report_no_subcommand_shows_usage() -> None:
    res = CliRunner().invoke(main, ["report"])
    assert res.exit_code == 0
    assert "report bug|feedback" in res.output
