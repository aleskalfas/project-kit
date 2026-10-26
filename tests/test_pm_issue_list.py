"""The one read of project-management's issues leaves state issues out (#2139).

DEC-058 point 3: the capability's one read of its issues leaves state issues
out by their marker, so every listing, check and plan of work gets the issues of
work alone. `_lib/issue_list` is that read. These tests pin what marks a state
issue, and what the read gives back: the issues of work in the fields asked
for, and the count of what `gh` returned, against which a limit is measured.
No test reaches GitHub: the runner is a fake.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _lib import issue_list  # noqa: E402

STATE_BODY = f"{issue_list.marker('seat-planner')}\n\n## Current state\n\nfree\n"


def _work(number: int, **fields) -> dict:
    return {"number": number, "title": f"[Task] work {number}", "body": "## What\n", **fields}


def _state(number: int) -> dict:
    return {"number": number, "title": "Seat planner", "body": STATE_BODY}


class _Runner:
    """A fake `gh` runner: returns `rows` (or `stdout`) and records each call."""

    def __init__(self, rows=None, *, stdout=None, returncode=0, stderr="") -> None:
        self.stdout = json.dumps(rows) if stdout is None else stdout
        self.returncode = returncode
        self.stderr = stderr
        self.calls: list[tuple[list[str], dict, dict]] = []

    def __call__(self, argv, config, **kwargs):
        self.calls.append((list(argv), config, kwargs))
        return subprocess.CompletedProcess(argv, self.returncode, self.stdout, self.stderr)


# --- the marker ---------------------------------------------------------------


def test_the_marker_names_its_key_and_marks_a_state_issue() -> None:
    line = issue_list.marker("seat-planner")
    assert line == "<!-- pkit:state-issue v=1 key=seat-planner -->"
    assert issue_list.is_state_issue(f"{line}\n## Current state\n")
    assert issue_list.is_state_issue(f"## Current state\n\nfree\n\n  {line}  \n")


def test_a_later_version_of_the_marker_still_marks_one() -> None:
    assert issue_list.is_state_issue("<!-- pkit:state-issue v=2 key=x kind=seat -->")
    assert issue_list.is_state_issue("<!--pkit:state-issue-->")


@pytest.mark.parametrize(
    "body",
    [
        "## What\n\nNo marker here.\n",
        "",
        # quoted in a sentence, as a work issue about state issues would
        "A state issue opens with `<!-- pkit:state-issue v=1 key=x -->`.\n",
        # quoted in a fenced code block
        "## What\n\n```\n<!-- pkit:state-issue v=1 key=x -->\n```\n",
        "~~~markdown\n<!-- pkit:state-issue v=1 key=x -->\n~~~\n",
        # another stamp of the capability
        "<!-- pkit:instance-owner v=1 event=claim instance=2 ts=2026-01-01T00:00:00+00:00 -->",
        "<!-- pkit:state-issues v=1 -->",
    ],
)
def test_a_body_without_the_marker_on_a_line_of_its_own_is_work(body: str) -> None:
    assert not issue_list.is_state_issue(body)


@pytest.mark.parametrize("key", ["", "two words", "a>b"])
def test_a_key_that_would_break_the_marker_is_refused(key: str) -> None:
    with pytest.raises(ValueError):
        issue_list.marker(key)


# --- the read -----------------------------------------------------------------


def test_the_read_leaves_state_issues_out_and_counts_what_gh_returned() -> None:
    runner = _Runner([_work(1), _state(2), _work(3)])
    listing = issue_list.list_issues({}, ["--state", "all"], fields="number,body", gh_call=runner)
    assert [row["number"] for row in listing.rows] == [1, 3]
    assert listing.returned == 3


def test_a_work_issue_comes_back_in_the_fields_asked_for() -> None:
    """The read asks `gh` for the body it needs, and gives none back unasked,
    so a work issue reads as it did before."""
    runner = _Runner([_work(1), _state(2)])
    listing = issue_list.list_issues(
        {"gh": {"host": "h"}},
        ["--state", "open", "--limit", "50"],
        fields="number,title",
        gh_call=runner,
        check=False,
    )
    assert listing.rows == ({"number": 1, "title": "[Task] work 1"},)
    argv, config, kwargs = runner.calls[0]
    assert argv == [
        "gh",
        "issue",
        "list",
        "--state",
        "open",
        "--limit",
        "50",
        "--json",
        "number,title,body",
    ]
    assert config == {"gh": {"host": "h"}}
    assert kwargs == {"check": False}


def test_a_body_asked_for_is_asked_once_and_kept() -> None:
    runner = _Runner([_work(1)])
    listing = issue_list.list_issues({}, [], fields="number,body,state", gh_call=runner)
    assert runner.calls[0][0][-2:] == ["--json", "number,body,state"]
    assert listing.rows == (_work(1),)


def test_a_failed_listing_carries_gh_s_words() -> None:
    runner = _Runner(stdout="", returncode=1, stderr="HTTP 502\n")
    listing = issue_list.list_issues({}, [], fields="number", gh_call=runner)
    assert listing.rows is None
    assert (listing.returncode, listing.stderr) == (1, "HTTP 502\n")


@pytest.mark.parametrize("stdout", ["not json", '{"number": 1}'])
def test_an_answer_that_is_no_json_list_has_no_rows(stdout: str) -> None:
    listing = issue_list.list_issues({}, [], fields="number", gh_call=_Runner(stdout=stdout))
    assert listing.rows is None
    assert listing.returncode == 0


def test_an_empty_answer_is_an_empty_listing() -> None:
    listing = issue_list.list_issues({}, [], fields="number", gh_call=_Runner(stdout=""))
    assert (listing.rows, listing.returned) == ((), 0)


def test_a_row_that_is_no_issue_passes_through_for_its_caller_to_judge() -> None:
    listing = issue_list.list_issues({}, [], fields="number", gh_call=_Runner([1, _work(2)]))
    assert listing.rows == (1, {"number": 2, "title": "[Task] work 2"})


def test_a_missing_gh_raises_as_the_runner_raises() -> None:
    def missing(argv, config, **kwargs):
        raise FileNotFoundError("gh")

    with pytest.raises(FileNotFoundError):
        issue_list.list_issues({}, [], fields="number", gh_call=missing)


def test_the_default_runner_is_gh_run_without_check(monkeypatch) -> None:
    runner = _Runner([_state(1)])
    monkeypatch.setattr(issue_list, "gh_run", runner)
    listing = issue_list.list_issues({"gh": {}}, ["--limit", "1"], fields="number")
    assert listing.rows == ()
    assert listing.returned == 1
    assert runner.calls[0][2] == {"check": False}
