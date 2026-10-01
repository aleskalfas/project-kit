"""Tests for `_lib/merge_queue.py` — pm's reader of the backbone's pull-request
noun (#1011, #1200).

The reading, the squash-commit defaults and the wait are the backbone's
(`pkit pull-request`, `src/project_kit/pull_request_landing.py`, tested in
`test_pull_request_landing.py`); pm asks for them by subprocess and reads the
JSON documents. These tests run the real subprocess against a fake `pkit` on
PATH: what pm asks, with the `gh` environment its config pins; how each
document reads; a wait's stream handed on reading by reading; and every way the
backbone can fail to answer, each an `Unreadable` with its cause. And pm's
statement of the backbone's wait limits is held equal to the backbone's.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

from project_kit import pull_request_landing as landing

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"


@pytest.fixture(scope="module")
def mq():
    sys.path.insert(0, str(SCRIPTS_DIR))
    from _lib import merge_queue

    return merge_queue


# A `pkit` that logs how it was asked and answers what the test put in
# FAKE_PKIT_ANSWER: its `stdout`, `stderr` and exit `code`.
_FAKE_PKIT = """\
import json, os, sys
with open(os.environ["FAKE_PKIT_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps({"argv": sys.argv[1:], "gh_host": os.environ.get("GH_HOST")}) + "\\n")
with open(os.environ["FAKE_PKIT_ANSWER"], encoding="utf-8") as fh:
    answer = json.load(fh)
sys.stdout.write(answer.get("stdout", ""))
sys.stderr.write(answer.get("stderr", ""))
sys.exit(answer.get("code", 0))
"""


class _Pkit:
    """The fake `pkit` on PATH: what it answers, and how it was asked."""

    def __init__(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        script = bin_dir / "pkit"
        script.write_text(f"#!{sys.executable}\n{_FAKE_PKIT}", encoding="utf-8")
        script.chmod(0o755)
        self.answer_file = tmp_path / "answer.json"
        self.log = tmp_path / "pkit.log"
        self.log.touch()
        monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
        monkeypatch.setenv("FAKE_PKIT_ANSWER", str(self.answer_file))
        monkeypatch.setenv("FAKE_PKIT_LOG", str(self.log))
        monkeypatch.delenv("GH_HOST", raising=False)
        self.answers(stdout="")

    def answers(self, *documents: dict[str, Any], stdout: str | None = None, **rest: Any) -> None:
        text = stdout if stdout is not None else "".join(json.dumps(d) + "\n" for d in documents)
        self.answer_file.write_text(json.dumps({"stdout": text, **rest}), encoding="utf-8")

    def asked(self) -> list[dict[str, Any]]:
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]


@pytest.fixture
def pkit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> _Pkit:
    return _Pkit(tmp_path, monkeypatch)


_QUEUED = landing.Reading(
    has_queue=True,
    merge_method="SQUASH",
    pr_id="PR_node",
    pr_state="OPEN",
    head_oid="sha-head",
    in_queue=True,
    position=2,
    entry_state="AWAITING_CHECKS",
    eta_seconds=250,
    waiting_to_enter=True,
    ever_queued=True,
)
_MERGED = landing.Reading(
    has_queue=True, merge_method="SQUASH", pr_state="MERGED", merged_at="t", head_oid="sha-head"
)


def _read_document(reading: landing.Reading | None, unreadable: str | None = None) -> Any:
    return {
        "schema_version": 1,
        "pull_request": 496,
        "reading": reading.as_json() if reading is not None else None,
        "unreadable": unreadable,
    }


# --- the reading -------------------------------------------------------------


def test_the_reading_asks_the_backbone_with_the_pinned_gh_host(mq, pkit) -> None:
    """pm asks `pkit pull-request read` for the PR, with the `gh` environment
    the adopter's config pins (DEC-023), so the backbone's `gh` reaches the
    configured host."""
    pkit.answers(_read_document(_QUEUED))
    mq.read(496, {"gh": {"host": "ghe.example"}})
    assert pkit.asked() == [
        {"argv": ["pull-request", "read", "496", "--json"], "gh_host": "ghe.example"}
    ]


def test_the_reading_is_what_the_backbone_concludes(mq, pkit) -> None:
    """Every field and every conclusion — merged, queued, the phrase — is read
    from the backbone's document; pm derives none of it again."""
    pkit.answers(_read_document(_QUEUED))
    reading = mq.read(496, {})
    assert reading.has_queue and reading.squashes and reading.queued and not reading.merged
    assert (reading.position, reading.entry_state, reading.eta_seconds) == (
        2,
        "AWAITING_CHECKS",
        250,
    )
    assert (reading.pr_id, reading.head_oid) == ("PR_node", "sha-head")
    assert reading.ever_queued and reading.removal is None and not reading.dropped_head
    assert reading.describe() == _QUEUED.describe()


def test_a_dropped_head_and_its_removal_are_read(mq, pkit) -> None:
    dropped = landing.Reading(
        has_queue=True,
        merge_method="SQUASH",
        pr_state="OPEN",
        head_oid="sha-head",
        ever_queued=True,
        removal=landing.Removal("2026-10-01T10:05:00Z", "failed checks", "sha-head"),
    )
    pkit.answers(_read_document(dropped))
    reading = mq.read(496, {})
    assert reading.dropped_head
    assert reading.removal == mq.Removal("2026-10-01T10:05:00Z", "failed checks", "sha-head")


def test_github_unreadable_is_unreadable_with_the_backbones_reason(mq, pkit) -> None:
    pkit.answers(_read_document(None, "HTTP 502: Bad Gateway"), code=1)
    with pytest.raises(mq.Unreadable, match="HTTP 502: Bad Gateway"):
        mq.read(496, {})


def test_the_squash_commit_defaults_are_the_backbones(mq, pkit) -> None:
    pkit.answers(
        {"schema_version": 1, "title": "PR_TITLE", "message": "PR_BODY", "unreadable": None}
    )
    assert mq.squash_commit_defaults({}) == ("PR_TITLE", "PR_BODY")
    assert pkit.asked()[0]["argv"] == ["pull-request", "squash-defaults", "--json"]


def test_squash_commit_defaults_that_cannot_be_read_are_unreadable(mq, pkit) -> None:
    pkit.answers(
        {"schema_version": 1, "title": None, "message": None, "unreadable": "not in the answer"},
        code=1,
    )
    with pytest.raises(mq.Unreadable, match="not in the answer"):
        mq.squash_commit_defaults({})


# --- when the backbone does not answer ------------------------------------------


@pytest.mark.parametrize(
    ("answer", "cause"),
    [
        (
            {"stdout": "", "stderr": "Error: No such command 'pull-request'.\n", "code": 2},
            "the installed backbone predates it — upgrade it",
        ),
        ({"stdout": "not json\n"}, "its answer is not JSON"),
        (
            {"stdout": json.dumps({"schema_version": 2}) + "\n"},
            "answered schema_version 2; pm reads 1",
        ),
        (
            {"stdout": "", "stderr": "boom\nTraceback: it broke\n", "code": 1},
            "exited 1: Traceback: it broke",
        ),
    ],
    ids=["predates", "not-json", "other-version", "failed"],
)
def test_a_backbone_that_does_not_answer_is_unreadable_with_the_cause(
    mq, pkit, answer, cause
) -> None:
    """Nothing merges on a guess: a backbone that cannot answer makes the
    reading unreadable, naming why."""
    pkit.answers(**answer)
    with pytest.raises(mq.Unreadable, match=cause):
        mq.read(496, {})


def test_no_pkit_on_path_is_unreadable(mq, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(mq.Unreadable, match="`pkit` is not on PATH"):
        mq.read(496, {})


# --- the merge requests -----------------------------------------------------------


def test_a_request_reads_what_it_came_to(mq, pkit) -> None:
    pkit.answers(
        {
            "schema_version": 1,
            "pull_request": 42,
            "accepted": False,
            "exit_code": 1,
            "reason": "Head sha didn't match",
        },
        code=1,
    )
    outcome = mq.request(["enqueue", "42", "--head", "sha"], {})
    assert outcome == mq.Outcome(False, 1, "Head sha didn't match")
    assert pkit.asked()[0]["argv"] == ["pull-request", "enqueue", "42", "--head", "sha", "--json"]


# --- the wait -------------------------------------------------------------------------


def _event(reading: landing.Reading) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "pull_request": 496,
        "event": "reading",
        "reading": reading.as_json(),
    }


def _end(ended: str | None, reading: landing.Reading | None, unreadable: str | None = None) -> Any:
    return {
        "schema_version": 1,
        "pull_request": 496,
        "event": "end",
        "ended": ended,
        "reading": reading.as_json() if reading is not None else None,
        "unreadable": unreadable,
    }


def test_the_wait_hands_on_each_reading_and_ends_as_the_backbone_says(mq, pkit) -> None:
    pkit.answers(_event(_QUEUED), _event(_MERGED), _end("merged", _MERGED))
    seen: list[str] = []
    wait = mq.wait_for_merge(
        496,
        {},
        timeout_seconds=1200,
        on_change=lambda r: seen.append(r.describe()),
        head_oid="sha-head",
    )
    assert wait.ended == mq.MERGED and wait.reading.merged
    assert seen == [_QUEUED.describe(), "merged at t"]
    assert pkit.asked()[0]["argv"] == [
        "pull-request",
        "wait",
        "496",
        "--head",
        "sha-head",
        "--seconds",
        "1200.0",
        "--json",
    ]


def test_a_wait_on_the_queues_estimate_names_no_time(mq, pkit) -> None:
    pkit.answers(_end("queued", _QUEUED), code=4)
    wait = mq.wait_for_merge(496, {}, timeout_seconds=None, on_change=lambda r: None)
    assert wait.ended == mq.STILL_QUEUED
    assert pkit.asked()[0]["argv"] == ["pull-request", "wait", "496", "--json"]


def test_a_reading_that_fails_mid_wait_is_unreadable(mq, pkit) -> None:
    pkit.answers(_event(_QUEUED), _end(None, None, "HTTP 502"), code=1)
    seen: list[str] = []
    with pytest.raises(mq.Unreadable, match="HTTP 502"):
        mq.wait_for_merge(496, {}, timeout_seconds=60, on_change=lambda r: seen.append("x"))
    assert seen == ["x"]


def test_a_wait_that_ends_without_saying_how_is_unreadable(mq, pkit) -> None:
    pkit.answers(_event(_QUEUED), code=1)
    with pytest.raises(mq.Unreadable, match="ended without saying how"):
        mq.wait_for_merge(496, {}, timeout_seconds=60, on_change=lambda r: None)


# --- one statement of the backbone's terms -----------------------------------------


def test_pm_states_the_backbones_wait_limits_and_endings(mq) -> None:
    """pm's messages state the backbone's wait limits; held equal here, so a
    change to the backbone's is a change pm's messages make too."""
    assert (mq.ETA_MARGIN_SECONDS, mq.MAX_WAIT_SECONDS) == (
        landing.ETA_MARGIN_SECONDS,
        landing.MAX_WAIT_SECONDS,
    )
    assert (mq.MERGED, mq.STILL_QUEUED, mq.LEFT, mq.HEAD_MOVED) == (
        landing.MERGED,
        landing.STILL_QUEUED,
        landing.LEFT,
        landing.HEAD_MOVED,
    )
    assert (mq.SQUASH, mq.PR_TITLE, mq.PR_BODY, mq.VERSION) == (
        landing.SQUASH,
        landing.PR_TITLE,
        landing.PR_BODY,
        landing.SCHEMA_VERSION,
    )
