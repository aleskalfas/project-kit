"""Tests for the backbone's one reader of a GitHub issue's state (`github_issues`):
read live through `gh`, stored nowhere, and unknown with its reason when it cannot be
read, never blocking (COR-043 point 5)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from project_kit import github_issues
from project_kit.github_issues import IssueReading


def _ran(
    monkeypatch: pytest.MonkeyPatch, *, returncode: int = 0, stdout: str = "", stderr: str = ""
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append({"args": args, **kwargs})
        return subprocess.CompletedProcess(args, returncode, stdout, stderr)

    monkeypatch.setattr(github_issues.subprocess, "run", run)
    return calls


@pytest.mark.parametrize(("given", "state"), [("CLOSED", "closed"), ("OPEN", "open")])
def test_an_issue_is_read_with_its_title_and_url_in_one_gh_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, given: str, state: str
) -> None:
    calls = _ran(
        monkeypatch,
        stdout=f'{{"state": "{given}", "title": "the fix", "url": "https://x/issues/795"}}',
    )

    reading = github_issues.read_issue("795", cwd=tmp_path)

    assert reading == IssueReading(state, title="the fix", url="https://x/issues/795")
    [call] = calls
    assert call["args"] == ["gh", "issue", "view", "795", "--json", "state,title,url"]
    assert call["cwd"] == tmp_path
    assert call["timeout"] == github_issues.GH_TIMEOUT_SECONDS


def test_an_issue_of_another_repository_names_it(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _ran(monkeypatch, stdout='{"state": "OPEN"}')

    reading = github_issues.read_issue("owner/repo#12")

    assert reading == IssueReading("open")
    assert calls[0]["args"] == [
        *("gh", "issue", "view", "12", "--json", "state,title,url"),
        *("--repo", "owner/repo"),
    ]
    assert calls[0]["cwd"] is None


@pytest.mark.parametrize("given", ["", "#12", "0", "x#12", "-o/repo#12", "owner/repo#--web"])
def test_a_value_that_names_no_issue_is_never_passed_to_gh(
    monkeypatch: pytest.MonkeyPatch, given: str
) -> None:
    calls = _ran(monkeypatch, stdout='{"state": "OPEN"}')

    reading = github_issues.read_issue(given)

    assert reading.state == github_issues.UNKNOWN
    assert "names no issue" in reading.reason
    assert calls == []


def test_gh_that_fails_gives_its_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    _ran(monkeypatch, returncode=1, stderr="\nerror connecting to api.github.com\nmore\n")

    assert github_issues.read_issue("795") == IssueReading(
        "unknown", "`gh` exited 1: error connecting to api.github.com"
    )


def test_gh_that_fails_silently_gives_its_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    _ran(monkeypatch, returncode=4)

    assert github_issues.read_issue("795") == IssueReading("unknown", "`gh` exited 4")


@pytest.mark.parametrize("stdout", ["not json", "", "[]", '{"state": "MERGED"}', '{"title": "x"}'])
def test_gh_that_gives_no_state_is_unknown(monkeypatch: pytest.MonkeyPatch, stdout: str) -> None:
    _ran(monkeypatch, stdout=stdout)

    assert github_issues.read_issue("795") == IssueReading("unknown", "`gh` gave no state for it")


@pytest.mark.parametrize(
    ("raised", "says"),
    [
        (FileNotFoundError("gh"), "`gh`, the GitHub client, is not installed"),
        (subprocess.TimeoutExpired("gh", 30), "`gh` gave no answer in 30 seconds"),
        (PermissionError("denied"), "`gh` could not run: denied"),
    ],
)
def test_gh_that_cannot_run_is_unknown_and_never_raises(
    monkeypatch: pytest.MonkeyPatch, raised: Exception, says: str
) -> None:
    def run(*_args: Any, **_kwargs: Any) -> None:
        raise raised

    monkeypatch.setattr(github_issues.subprocess, "run", run)

    assert github_issues.read_issue("795") == IssueReading("unknown", says)


def test_each_ask_reads_again_and_nothing_is_stored(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _ran(monkeypatch, stdout='{"state": "OPEN"}')

    github_issues.read_issue("795")
    github_issues.read_issue("795")

    assert len(calls) == 2
