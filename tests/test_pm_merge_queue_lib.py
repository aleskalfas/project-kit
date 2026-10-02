"""Tests for `_lib/merge_queue.py` — pm's reader of the backbone's pull-request
noun (#1011, #1200).

The reading, the squash-commit defaults and the wait are the backbone's
(`pkit pull-request`, `src/project_kit/pull_request_landing.py`, tested in
`test_pull_request_landing.py`); pm asks for them by subprocess and reads the
JSON documents. These tests run the real subprocess against a fake `pkit` on
PATH: what pm asks, with the `gh` environment its config pins; how each
document reads, and that a reading without a field a decision rests on is no
reading; a wait's stream handed on reading by reading; warnings on standard
error passed on; each call bounded, and ended with what it started; and every
way the backbone can fail to answer, each an `Unreadable` with its cause. One
round trip runs the backbone's real command under a fake `gh`. And pm's
statement of the backbone's wait limits is held equal to the backbone's.
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections.abc import Iterator
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


@pytest.fixture(autouse=True)
def _fresh_warnings(mq, monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test passes warnings on as a run of its own would."""
    monkeypatch.setattr(mq, "_passed_on", set())


# A `pkit` that logs how it was asked and answers what the test put in
# FAKE_PKIT_ANSWER: its `stderr`, then its `stdout`, and exit `code` — after
# starting a `grandchild` that writes its pid to the file named, and sleeping
# `sleep` seconds, when asked to.
_FAKE_PKIT = """\
import json, os, subprocess, sys, time
with open(os.environ["FAKE_PKIT_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps({"argv": sys.argv[1:], "gh_host": os.environ.get("GH_HOST")}) + "\\n")
with open(os.environ["FAKE_PKIT_ANSWER"], encoding="utf-8") as fh:
    answer = json.load(fh)
if answer.get("grandchild"):
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    with open(answer["grandchild"], "w", encoding="utf-8") as out:
        out.write(str(child.pid))
sys.stderr.write(answer.get("stderr", ""))
sys.stderr.flush()
sys.stdout.write(answer.get("stdout", ""))
sys.stdout.flush()
time.sleep(answer.get("sleep", 0))
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
            "this project's backbone is older than project-management needs",
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


def test_a_pkit_without_the_command_is_named(mq, pkit, tmp_path) -> None:
    """The `pkit` that ran is named, and why its lack matters: the project's
    backbone is older than project-management needs — not only `pkit upgrade`."""
    pkit.answers(stdout="", stderr="Error: No such command 'pull-request'.\n", code=2)
    with pytest.raises(mq.Unreadable) as raised:
        mq.read(496, {})
    message = str(raised.value)
    assert f"the `pkit` that ran — {tmp_path / 'bin' / 'pkit'} — has no such command" in message
    assert "older than project-management needs" in message
    assert "`pkit upgrade`" in message


# --- a reading without what a decision rests on -------------------------------


_DECIDING = ["has_queue", "merged", "queued", "dropped_head", "head_oid"]


@pytest.mark.parametrize("key", _DECIDING)
def test_a_reading_without_a_deciding_field_is_unreadable(mq, pkit, key) -> None:
    """Read as false or empty, a missing field would fail open — no queue, so
    a merge around it; no dropped head, so a dropped head enqueued again."""
    document = _read_document(_QUEUED)
    del document["reading"][key]
    pkit.answers(document)
    with pytest.raises(mq.Unreadable, match=f"the backbone's reading has no `{key}`"):
        mq.read(496, {})


@pytest.mark.parametrize("key", _DECIDING)
def test_a_reading_with_a_deciding_field_of_another_type_is_unreadable(mq, pkit, key) -> None:
    document = _read_document(_QUEUED)
    document["reading"][key] = 1 if key == "head_oid" else "yes"
    pkit.answers(document)
    with pytest.raises(mq.Unreadable, match=f"has a `{key}` that is not a"):
        mq.read(496, {})


@pytest.mark.parametrize("ended", [None, 3, "gone"], ids=["missing", "not-text", "unknown"])
def test_a_wait_that_does_not_say_how_it_ended_is_unreadable(mq, pkit, ended) -> None:
    end = _end("merged", _MERGED)
    if ended is None:
        del end["ended"]
    else:
        end["ended"] = ended
    pkit.answers(end)
    with pytest.raises(mq.Unreadable, match="says no way the wait ended"):
        mq.wait_for_merge(496, {}, timeout_seconds=60, on_change=lambda r: None)


def test_a_wait_reading_without_a_deciding_field_is_unreadable(mq, pkit) -> None:
    event = _event(_QUEUED)
    del event["reading"]["queued"]
    pkit.answers(event, _end("merged", _MERGED))
    with pytest.raises(mq.Unreadable, match="has no `queued`"):
        mq.wait_for_merge(496, {}, timeout_seconds=60, on_change=lambda r: None)


@pytest.mark.parametrize("accepted", [None, "yes"], ids=["missing", "not-a-bool"])
def test_a_request_that_does_not_say_whether_it_was_accepted_is_unreadable(
    mq, pkit, accepted
) -> None:
    """Not knowing whether gh took a merge is not a refusal: the caller reads
    the PR before it decides (`pr_merge.land`)."""
    document: dict[str, Any] = {"schema_version": 1, "pull_request": 42, "exit_code": 0}
    if accepted is not None:
        document["accepted"] = accepted
    pkit.answers(document)
    with pytest.raises(mq.Unreadable, match="does not say whether the request was accepted"):
        mq.request(["merge", "42", "--subject", "fix: x"], {})


# --- how the backbone's run is read ----------------------------------------------


def test_a_warning_on_standard_error_is_passed_on_with_the_answer(mq, pkit, capsys) -> None:
    """The router's notice that it ran another `pkit` than the project's is not
    discarded because a document came back — and is said once per run."""
    notice = "pkit: this project pins project-kit 1.150.0 but the running binary is 1.149.0"
    pkit.answers(_read_document(_QUEUED), stderr=f"{notice}\nsome chatter\n")
    mq.read(496, {})
    mq.read(496, {})
    assert capsys.readouterr().err == f"{notice}\n"


def test_standard_error_is_read_while_standard_output_is_awaited(mq, pkit, monkeypatch) -> None:
    """A run that fills its standard error before it answers is still read:
    the two streams are read as they come, never one to its end first."""
    monkeypatch.setitem(mq.TIMEOUT_SECONDS, "read", 20.0)
    pkit.answers(_read_document(_QUEUED), stderr="x" * 1_000_000 + "\n")
    assert mq.read(496, {}).queued


def test_a_run_past_its_bound_is_stopped_with_what_it_started(
    mq, pkit, monkeypatch, tmp_path
) -> None:
    """A `gh` request still running when pm stops waiting would go on after pm
    read the PR to decide: the run is ended with everything it started."""
    monkeypatch.setitem(mq.TIMEOUT_SECONDS, "merge", 1.0)
    pidfile = tmp_path / "grandchild.pid"
    pkit.answers(stdout="", sleep=30, grandchild=str(pidfile))
    started = time.monotonic()
    with pytest.raises(mq.Unreadable, match="gave no answer within 1 s, and was stopped"):
        mq.request(["merge", "42", "--subject", "fix: x"], {})
    assert time.monotonic() - started < 15
    grandchild = int(pidfile.read_text(encoding="utf-8"))
    assert _ends_within(grandchild, seconds=10), "the run's grandchild outlived it"


def _ends_within(pid: int, *, seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.05)
    return False


@pytest.mark.parametrize(
    ("seconds", "bound"),
    [(60, 60 + 300.0), (None, 30 * 60.0 + 300.0)],
    ids=["asked-for", "the-queues-estimate"],
)
def test_a_wait_is_bounded_by_its_own_limit_plus_a_margin(mq, monkeypatch, seconds, bound):
    asked: list[float | None] = []

    def answers(
        args: list[str], config: dict[str, Any], *, timeout_seconds: float | None = None
    ) -> Iterator[dict[str, Any]]:
        asked.append(timeout_seconds)
        yield _end("merged", _MERGED)

    monkeypatch.setattr(mq, "_answers", answers)
    mq.wait_for_merge(496, {}, timeout_seconds=seconds, on_change=lambda r: None)
    assert asked == [bound]


@pytest.mark.parametrize(
    ("call", "argv"),
    [
        (
            lambda mq, config: mq.request(["merge", "42", "--subject", "fix: x"], config),
            ["pull-request", "merge", "42", "--subject", "fix: x", "--json"],
        ),
        (
            lambda mq, config: mq.request(["enqueue", "42", "--head", "sha"], config),
            ["pull-request", "enqueue", "42", "--head", "sha", "--json"],
        ),
        (
            lambda mq, config: mq.request(["dequeue", "42"], config),
            ["pull-request", "dequeue", "42", "--json"],
        ),
        (
            lambda mq, config: mq.wait_for_merge(
                42, config, timeout_seconds=0, on_change=lambda r: None
            ),
            ["pull-request", "wait", "42", "--seconds", "0.0", "--json"],
        ),
    ],
    ids=["merge", "enqueue", "dequeue", "wait"],
)
def test_every_call_that_acts_runs_with_the_pinned_gh_host(mq, pkit, call, argv) -> None:
    """Not only the reading: each request, and the wait, reach the host the
    adopter's config pins (DEC-023)."""
    pkit.answers(
        {"schema_version": 1, "pull_request": 42, "accepted": True, "exit_code": 0, "reason": ""}
        if argv[1] != "wait"
        else _end("merged", _MERGED)
    )
    call(mq, {"gh": {"host": "ghe.example"}})
    assert pkit.asked() == [{"argv": argv, "gh_host": "ghe.example"}]


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


def test_a_request_the_backbones_guard_refused_says_so(mq, pkit) -> None:
    """The backbone runs the cross-repository guard before the request; a
    refusal reads as not accepted, its `reason_kind` naming the guard, with
    what the guard compared (#1254)."""
    guard = {
        "verdict": "diverged",
        "undetermined_kind": None,
        "anchor": "/work/project",
        "target": "/work/other",
        "cleared": None,
    }
    pkit.answers(
        {
            "schema_version": 1,
            "pull_request": 42,
            "accepted": False,
            "exit_code": None,
            "reason": "the cross-repository guard refused: …",
            "reason_kind": "foreign-repository",
            "guard": guard,
        },
        code=1,
    )
    outcome = mq.request(["merge", "42", "--subject", "fix: x"], {})
    assert (outcome.accepted, outcome.reason_kind) == (False, mq.FOREIGN_REPOSITORY)
    assert outcome.guard == guard


# --- the head branch's deletion (#1255) -------------------------------------------


def _deletion_document(outcome: str, **fields: Any) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "pull_request": 42,
        "expected": "sha-merged",
        "outcome": outcome,
        "branch": "fix/42-x",
        "tip": None,
        "reason_kind": None,
        "reason": None,
        "guard": {"verdict": "undetermined", "cleared": "undetermined"},
        **fields,
    }


def test_a_deletion_reads_how_it_ended_with_the_pinned_gh_host(mq, pkit) -> None:
    pkit.answers(
        _deletion_document(
            "kept", tip="sha-later", reason_kind="tip-moved", reason="its tip is sha-lat"
        )
    )
    deletion = mq.deletion(["42", "--expect", "sha-merged"], {"gh": {"host": "ghe.example"}})
    assert deletion == mq.BranchDeletion(
        mq.KEPT, "fix/42-x", "sha-later", "tip-moved", "its tip is sha-lat"
    )
    assert pkit.asked() == [
        {
            "argv": ["pull-request", "delete-branch", "42", "--expect", "sha-merged", "--json"],
            "gh_host": "ghe.example",
        }
    ]


def test_a_refused_deletion_reads_as_refused_with_why(mq, pkit) -> None:
    pkit.answers(
        _deletion_document(
            "refused", branch=None, reason_kind="foreign-repository", reason="the guard refused"
        ),
        code=1,
    )
    deletion = mq.deletion(["42", "--expect", "sha-merged"], {})
    assert (deletion.outcome, deletion.branch, deletion.reason_kind) == (
        mq.REFUSED,
        "",
        mq.FOREIGN_REPOSITORY,
    )


@pytest.mark.parametrize(
    ("document", "why"),
    [
        (_deletion_document("landed"), "says no way the deletion ended"),
        ({k: v for k, v in _deletion_document("gone").items() if k != "tip"}, "has no `tip`"),
        (_deletion_document("kept", tip=7), "a `tip` that is not text"),
    ],
    ids=["unknown-outcome", "missing-field", "field-of-another-type"],
)
def test_a_deletion_document_pm_cannot_read_is_no_answer(mq, pkit, document, why) -> None:
    """An unknown `outcome`, or a missing or mistyped field, is no answer: the
    branch may have been deleted, or not."""
    pkit.answers(document)
    with pytest.raises(mq.Unreadable, match=why):
        mq.deletion(["42", "--expect", "sha-merged"], {})


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


# --- a round trip through the backbone's own command ------------------------------

# A `gh` that keeps one PR in FAKE_GH_STATE: a GraphQL read answers it, and
# `gh pr merge --auto` takes it into the queue. It logs how it was asked.
_FAKE_GH = """\
import json, os, sys
path = os.environ["FAKE_GH_STATE"]
with open(path, encoding="utf-8") as fh:
    state = json.load(fh)
with open(os.environ["FAKE_GH_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps({"argv": sys.argv[1:], "gh_host": os.environ.get("GH_HOST")}) + "\\n")
args = sys.argv[1:]
if args[:2] == ["api", "graphql"]:
    print(json.dumps({"data": {"repository": {"pullRequest": state}}}))
elif args[:2] == ["pr", "merge"] and "--auto" in args:
    state["isInMergeQueue"] = True
    state["mergeQueueEntry"] = {"position": 1, "state": "QUEUED", "estimatedTimeToMerge": 120}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(state, fh)
else:
    sys.stderr.write(f"unexpected gh call: {args}\\n")
    sys.exit(1)
"""

# The router's notice, as a `pkit` that does not run the project's own code says it.
_NOTICE = "pkit: source checkout here but its dispatcher is not executable — running this binary"


def test_a_round_trip_through_the_backbones_command(mq, tmp_path, monkeypatch, capsys) -> None:
    """pm's real runner runs the backbone's real command, which runs `gh`: the
    reading, an enqueue and two waits — a stream of documents read as it
    comes, each of the version pm reads; a wait that exits 4 with its answer;
    the router's notice on standard error passed on, once; and the pinned
    host reaching `gh` on every call."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    pkit = bin_dir / "pkit"
    pkit.write_text(
        f'#!/bin/sh\necho "{_NOTICE}" >&2\nexec "{sys.executable}" -m project_kit "$@"\n',
        encoding="utf-8",
    )
    gh = bin_dir / "gh"
    gh.write_text(f"#!{sys.executable}\n{_FAKE_GH}", encoding="utf-8")
    for script in (pkit, gh):
        script.chmod(0o755)
    state = tmp_path / "pr.json"
    pr: dict[str, Any] = {
        "id": "PR_node",
        "state": "OPEN",
        "mergedAt": None,
        "headRefOid": "sha-head",
        "isMergeQueueEnabled": True,
        "isInMergeQueue": False,
        "mergeQueue": {"configuration": {"mergeMethod": "SQUASH"}},
        "mergeQueueEntry": None,
        "autoMergeRequest": None,
        "timelineItems": {"nodes": []},
    }
    state.write_text(json.dumps(pr), encoding="utf-8")
    log = tmp_path / "gh.log"
    log.touch()
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("FAKE_GH_STATE", str(state))
    monkeypatch.setenv("FAKE_GH_LOG", str(log))
    monkeypatch.delenv("GH_HOST", raising=False)
    monkeypatch.chdir(tmp_path)
    config = {"gh": {"host": "ghe.example"}}

    reading = mq.read(42, config)
    assert reading.has_queue and reading.squashes and not reading.queued
    assert mq.request(["enqueue", "42", "--head", "sha-head"], config).accepted

    seen: list[str] = []
    held = mq.wait_for_merge(
        42, config, timeout_seconds=0, on_change=lambda r: seen.append(r.describe())
    )
    assert held.ended == mq.STILL_QUEUED
    assert seen == ["position 1 in the queue, queued, about 2 min to merge"]

    state.write_text(
        json.dumps({**pr, "state": "MERGED", "mergedAt": "2026-10-01T10:12:00Z"}),
        encoding="utf-8",
    )
    merged = mq.wait_for_merge(42, config, timeout_seconds=0, on_change=lambda r: None)
    assert (merged.ended, merged.reading.merged) == (mq.MERGED, True)

    asked = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    assert [entry["argv"][:2] for entry in asked] == [
        ["api", "graphql"],
        ["pr", "merge"],
        ["api", "graphql"],
        ["api", "graphql"],
    ]
    assert asked[1]["argv"] == ["pr", "merge", "42", "--auto", "--match-head-commit", "sha-head"]
    assert {entry["gh_host"] for entry in asked} == {"ghe.example"}
    assert capsys.readouterr().err == f"{_NOTICE}\n"


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
    assert (mq.DELETED, mq.KEPT, mq.GONE, mq.REFUSED, mq.CROSS_REPOSITORY) == (
        landing.DELETED,
        landing.KEPT,
        landing.GONE,
        landing.REFUSED,
        landing.CROSS_REPOSITORY,
    )
