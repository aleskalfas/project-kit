"""Tests for the sanctioned release-PR merge path (`pkit release merge`, #475).

The gate is split into pure logic (`summarize_checks`, `parse_release_pr`,
`evaluate_release_pr`) and the landing, which is the backbone's one merge
mechanic (`pull_request_landing`, #1200). The pure logic is tested directly;
`merge_release_pr` runs on a fake GitHub (`_Host`) with and without a merge
queue — no real merge, no network, no hardcoded repo. The post-merge branch
deletion (`_gh_delete_remote_branch` / `_git_cleanup_local`, #897) is tested
with `subprocess.run` stubbed.
"""

from __future__ import annotations

import inspect
import json
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import click
import pytest

from project_kit import release

# --- check-rollup summarisation --------------------------------------


def test_summarize_checks_all_green() -> None:
    rollup = [
        {"name": "lint", "status": "COMPLETED", "conclusion": "SUCCESS"},
        {"name": "skipped-job", "status": "COMPLETED", "conclusion": "SKIPPED"},
        {"context": "legacy-status", "state": "SUCCESS"},
    ]
    passing, failing = release.summarize_checks(rollup)
    assert passing is True
    assert failing == ()


def test_summarize_checks_flags_failure_and_pending() -> None:
    rollup = [
        {"name": "tests", "status": "COMPLETED", "conclusion": "FAILURE"},
        {"name": "build", "status": "IN_PROGRESS", "conclusion": ""},
        {"context": "legacy", "state": "PENDING"},
        {"name": "ok", "status": "COMPLETED", "conclusion": "SUCCESS"},
    ]
    passing, failing = release.summarize_checks(rollup)
    assert passing is False
    assert failing == ("tests (FAILURE)", "build (IN_PROGRESS)", "legacy (PENDING)")


def test_summarize_checks_empty_is_passing() -> None:
    assert release.summarize_checks([]) == (True, ())
    assert release.summarize_checks(None) == (True, ())


# --- stale-run dedupe (#504): latest run per check wins --------------


def test_summarize_checks_latest_success_beats_stale_failure() -> None:
    # A check that failed (16:34) then re-ran green (16:39) — the merge must not
    # be blocked by the retained stale FAILURE. Latest wins.
    rollup = [
        {
            "name": "checks",
            "status": "COMPLETED",
            "conclusion": "FAILURE",
            "startedAt": "2026-06-01T16:30:00Z",
            "completedAt": "2026-06-01T16:34:00Z",
        },
        {
            "name": "checks",
            "status": "COMPLETED",
            "conclusion": "SUCCESS",
            "startedAt": "2026-06-01T16:35:00Z",
            "completedAt": "2026-06-01T16:39:00Z",
        },
    ]
    assert release.summarize_checks(rollup) == (True, ())


def test_summarize_checks_latest_failure_beats_stale_success() -> None:
    # Reverse ordering: an older SUCCESS, a newer FAILURE — the latest run
    # (FAILURE) must block.
    rollup = [
        {
            "name": "checks",
            "status": "COMPLETED",
            "conclusion": "SUCCESS",
            "completedAt": "2026-06-01T16:30:00Z",
        },
        {
            "name": "checks",
            "status": "COMPLETED",
            "conclusion": "FAILURE",
            "completedAt": "2026-06-01T16:39:00Z",
        },
    ]
    assert release.summarize_checks(rollup) == (False, ("checks (FAILURE)",))


def test_summarize_checks_single_genuine_failure_still_blocks() -> None:
    rollup = [
        {
            "name": "checks",
            "status": "COMPLETED",
            "conclusion": "FAILURE",
            "completedAt": "2026-06-01T16:39:00Z",
        },
    ]
    assert release.summarize_checks(rollup) == (False, ("checks (FAILURE)",))


def test_summarize_checks_latest_pending_blocks() -> None:
    # An older green run superseded by a fresh in-progress re-run must block.
    rollup = [
        {
            "name": "checks",
            "status": "COMPLETED",
            "conclusion": "SUCCESS",
            "completedAt": "2026-06-01T16:30:00Z",
        },
        {
            "name": "checks",
            "status": "IN_PROGRESS",
            "conclusion": "",
            "startedAt": "2026-06-01T16:40:00Z",
        },
    ]
    assert release.summarize_checks(rollup) == (False, ("checks (IN_PROGRESS)",))


def test_summarize_checks_distinct_checks_dedupe_independently() -> None:
    # Two distinct checks, each with a stale then latest run; each is reduced on
    # its own latest — `lint` ends green, `tests` ends red.
    rollup = [
        {
            "name": "lint",
            "status": "COMPLETED",
            "conclusion": "FAILURE",
            "completedAt": "2026-06-01T16:30:00Z",
        },
        {
            "name": "lint",
            "status": "COMPLETED",
            "conclusion": "SUCCESS",
            "completedAt": "2026-06-01T16:39:00Z",
        },
        {
            "name": "tests",
            "status": "COMPLETED",
            "conclusion": "SUCCESS",
            "completedAt": "2026-06-01T16:31:00Z",
        },
        {
            "name": "tests",
            "status": "COMPLETED",
            "conclusion": "FAILURE",
            "completedAt": "2026-06-01T16:40:00Z",
        },
    ]
    assert release.summarize_checks(rollup) == (False, ("tests (FAILURE)",))


def test_summarize_checks_statuscontext_dedupes_on_createdat() -> None:
    # Legacy StatusContext nodes dedupe on `context` + `createdAt`; latest wins.
    rollup = [
        {"context": "legacy", "state": "FAILURE", "createdAt": "2026-06-01T16:30:00Z"},
        {"context": "legacy", "state": "SUCCESS", "createdAt": "2026-06-01T16:39:00Z"},
    ]
    assert release.summarize_checks(rollup) == (True, ())


def test_summarize_checks_untimed_ties_prefer_last_listed() -> None:
    # No timestamps at all — fall through to GitHub's chronological order and
    # keep the last-listed run (the green re-run).
    rollup = [
        {"name": "checks", "status": "COMPLETED", "conclusion": "FAILURE"},
        {"name": "checks", "status": "COMPLETED", "conclusion": "SUCCESS"},
    ]
    assert release.summarize_checks(rollup) == (True, ())


# --- parsing ---------------------------------------------------------


def _raw(**overrides: object) -> dict:
    base = {
        "number": 42,
        "title": "chore(release): v1.141.0",
        "state": "OPEN",
        "headRefName": "release/v1.141.0",
        "headRefOid": "sha-head",
        "baseRefName": "main",
        "isCrossRepository": False,
        "url": "https://github.com/owner/repo/pull/42",
        "mergeable": "MERGEABLE",
        "statusCheckRollup": [{"name": "checks", "status": "COMPLETED", "conclusion": "SUCCESS"}],
    }
    base.update(overrides)
    return base


def test_parse_release_pr_normalises_case() -> None:
    pr = release.parse_release_pr(_raw(state="open", mergeable="mergeable"))
    assert pr.state == "OPEN"
    assert pr.mergeable == "MERGEABLE"
    assert pr.checks_passing is True


def test_parse_release_pr_reads_base_and_fork_fields() -> None:
    pr = release.parse_release_pr(_raw(baseRefName="develop", isCrossRepository=True))
    assert pr.base_ref == "develop"
    assert pr.cross_repository is True


def test_parse_release_pr_missing_fork_field_reads_as_a_fork() -> None:
    """Fail safe: without `isCrossRepository` the head is treated as a fork's,
    so nothing in the base repo is deleted on an unknown answer."""
    raw = _raw()
    del raw["isCrossRepository"]
    assert release.parse_release_pr(raw).cross_repository is True


# --- the gate decision -----------------------------------------------


def test_evaluate_merges_a_green_release_pr() -> None:
    decision = release.evaluate_release_pr(release.parse_release_pr(_raw()))
    assert decision.action == "merge"


def test_evaluate_refuses_non_release_head_branch() -> None:
    decision = release.evaluate_release_pr(
        release.parse_release_pr(_raw(headRefName="fix/123-a-bug"))
    )
    assert decision.action == "refuse"
    # Points at the issue-PR gate rather than silently bypassing it.
    assert "merge-pr" in decision.message


def test_evaluate_refuses_non_release_title() -> None:
    decision = release.evaluate_release_pr(release.parse_release_pr(_raw(title="feat: something")))
    assert decision.action == "refuse"
    assert "not a release title" in decision.message


def test_evaluate_reports_already_merged() -> None:
    decision = release.evaluate_release_pr(release.parse_release_pr(_raw(state="MERGED")))
    assert decision.action == "already-done"
    assert "already merged" in decision.message


def test_evaluate_reports_closed() -> None:
    decision = release.evaluate_release_pr(release.parse_release_pr(_raw(state="CLOSED")))
    assert decision.action == "already-done"
    assert "closed" in decision.message


def test_evaluate_refuses_conflicting() -> None:
    decision = release.evaluate_release_pr(release.parse_release_pr(_raw(mergeable="CONFLICTING")))
    assert decision.action == "refuse"
    assert "conflict" in decision.message


def test_evaluate_refuses_unknown_mergeability() -> None:
    decision = release.evaluate_release_pr(release.parse_release_pr(_raw(mergeable="UNKNOWN")))
    assert decision.action == "refuse"


def test_evaluate_refuses_red_checks() -> None:
    decision = release.evaluate_release_pr(
        release.parse_release_pr(
            _raw(
                statusCheckRollup=[
                    {"name": "tests", "status": "COMPLETED", "conclusion": "FAILURE"}
                ]
            )
        )
    )
    assert decision.action == "refuse"
    assert "tests (FAILURE)" in decision.message


# --- the orchestrator (gh monkeypatched) ------------------------------
#
# `_gh_pr_view` answers the PR; the landing's `gh` is `_Host`, a fake GitHub
# with or without a merge queue; the post-merge steps (`gh api -X DELETE`, the
# local git clean-up) run through a stubbed `subprocess.run` (`_fake_run`),
# whose argvs say what was deleted.


def _fake_run(
    monkeypatch: pytest.MonkeyPatch,
    *,
    api_stderr: str = "",
    checkout_stderr: str = "",
    pull_stderr: str = "",
    branch_d_stderr: str = "",
    local_branch_exists: bool = True,
) -> list[list[str]]:
    """Stub `subprocess.run` for the post-merge steps; a non-empty stderr makes
    that step fail. Returns the argvs seen."""
    seen: list[list[str]] = []

    def fake(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen.append(list(argv))
        failing = (
            (argv[:3] == ["gh", "api", "-X"] and api_stderr)
            or (argv[:2] == ["git", "checkout"] and checkout_stderr)
            or (argv[:2] == ["git", "pull"] and pull_stderr)
            or (argv[:3] == ["git", "branch", "-D"] and branch_d_stderr)
        )
        if failing:
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr=failing)
        if argv[:2] == ["git", "rev-parse"] and not local_branch_exists:
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(release.subprocess, "run", fake)
    return seen


def _entry(position: int, state: str = "AWAITING_CHECKS", **fields: Any) -> dict[str, Any]:
    entry = {"position": position, "state": state, "estimatedTimeToMerge": 300}
    return {"isInMergeQueue": True, "mergeQueueEntry": entry, **fields}


_LANDED = {
    "isInMergeQueue": False,
    "mergeQueueEntry": None,
    "state": "MERGED",
    "mergedAt": "2026-10-01T10:12:00Z",
}
_DROPPED = {
    "isInMergeQueue": False,
    "mergeQueueEntry": None,
    "timelineItems": {
        "nodes": [
            {"__typename": "AddedToMergeQueueEvent"},
            {
                "__typename": "RemovedFromMergeQueueEvent",
                "createdAt": "2026-10-01T10:05:00Z",
                "reason": "failed checks",
                "beforeCommit": {"oid": "sha-head"},
            },
        ]
    },
}


class _Host:
    """GitHub as the landing's `gh` reaches it: one PR whose base merges
    through a queue or not. Enqueueing takes the PR in; each later reading of a
    queued PR moves it on by the next entry of `progress`. A direct squash
    merge lands at once on a base without a queue — or, with `enqueues`, gh
    only enqueues — and `unreadable_after` makes every reading after the first
    `n` fail."""

    def __init__(
        self,
        *,
        queue: bool,
        progress: list[dict[str, Any]] | None = None,
        method: str = "SQUASH",
        defaults: tuple[str, str] = ("PR_TITLE", "PR_BODY"),
        enqueues: bool = False,
        unreadable_after: int | None = None,
        **pr: Any,
    ) -> None:
        self.pr: dict[str, Any] = {
            "id": "PR_node",
            "state": "OPEN",
            "mergedAt": None,
            "headRefOid": "sha-head",
            "isMergeQueueEnabled": queue,
            "isInMergeQueue": False,
            "mergeQueue": {"configuration": {"mergeMethod": method}} if queue else None,
            "mergeQueueEntry": None,
            "autoMergeRequest": None,
            "timelineItems": {"nodes": []},
            **pr,
        }
        self.progress = list(progress or [])
        self.defaults = defaults
        self.enqueues = enqueues
        self.unreadable_after = unreadable_after
        self.reads = 0
        self.commands: list[list[str]] = []

    def __call__(self, argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        args = list(argv)
        self.commands.append(args)
        query = next((a for a in args if a.startswith("query=")), "")
        if args[:3] == ["gh", "pr", "merge"]:
            if "--auto" in args or (self.enqueues and "--squash" in args):
                self.pr["isInMergeQueue"] = True
            elif "--disable-auto" in args:
                self.pr["autoMergeRequest"] = None
            elif "--squash" in args:
                self.pr.update(state="MERGED", mergedAt="2026-10-01T10:00:00Z")
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        if "dequeuePullRequest" in query:
            self.pr.update(isInMergeQueue=False, mergeQueueEntry=None)
            self.progress = []
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        if args[:3] == ["gh", "api", "graphql"]:
            self.reads += 1
            if self.unreadable_after is not None and self.reads > self.unreadable_after:
                return subprocess.CompletedProcess(args, 1, stdout="", stderr="HTTP 502")
            if self.pr["isInMergeQueue"] and self.progress:
                self.pr.update(self.progress.pop(0))
            answer = {"data": {"repository": {"pullRequest": self.pr}}}
            return subprocess.CompletedProcess(args, 0, stdout=json.dumps(answer), stderr="")
        if args[:3] == ["gh", "api", "repos/{owner}/{repo}"]:
            title, message = self.defaults
            answer = {"squash_merge_commit_title": title, "squash_merge_commit_message": message}
            return subprocess.CompletedProcess(args, 0, stdout=json.dumps(answer), stderr="")
        raise AssertionError(f"unexpected gh call: {args}")

    def merges(self) -> list[list[str]]:
        return [c for c in self.commands if c[:3] == ["gh", "pr", "merge"]]


def _land(
    monkeypatch: pytest.MonkeyPatch,
    host: _Host,
    *,
    wait_seconds: float | None = None,
    dry_run: bool = False,
    **raw: Any,
) -> release.ReleaseMergeReport:
    """`merge_release_pr` for PR 42 on `host`, with a clock the wait's sleeps advance."""
    monkeypatch.setattr(release, "_gh_pr_view", lambda n, r: _raw(number=n, **raw))
    monkeypatch.setattr(release.pull_request_landing, "gh_runner", lambda cwd: host)
    now = [0.0]

    def sleep(seconds: float) -> None:
        now[0] += seconds

    monkeypatch.setattr(release.pull_request_landing, "_sleep", sleep)
    monkeypatch.setattr(release.pull_request_landing, "_monotonic", lambda: now[0])
    return release.merge_release_pr(Path("/repo"), 42, wait_seconds=wait_seconds, dry_run=dry_run)


def _merge_green(monkeypatch: pytest.MonkeyPatch, **raw: Any) -> str:
    """A green release PR merged directly, on a base without a queue."""
    return _land(monkeypatch, _Host(queue=False), **raw).text


_DELETE_HEAD = ["gh", "api", "-X", "DELETE", "repos/{owner}/{repo}/git/refs/heads/release/v1.141.0"]


def test_merge_release_pr_squash_merges_a_green_pr(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without a queue, one squash commit under the PR title, pinned to the
    head whose checks the gate read — and never `--delete-branch`, which makes
    gh touch the local checkout and fail after the remote merge landed (#897)."""
    host = _Host(queue=False)
    _fake_run(monkeypatch)
    report = _land(monkeypatch, host)
    assert host.merges() == [
        [
            "gh",
            "pr",
            "merge",
            "42",
            "--squash",
            "--subject",
            "chore(release): v1.141.0",
            "--match-head-commit",
            "sha-head",
        ]
    ]
    assert report.exit_code == 0
    assert "Merged release PR #42" in report.text
    assert "post-merge tag step" in report.text  # tagging stays split


def test_merge_release_pr_dry_run_does_not_merge(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host(queue=False)
    seen = _fake_run(monkeypatch)
    report = _land(monkeypatch, host, dry_run=True)
    assert host.merges() == [] and seen == []
    assert report.text.startswith("[dry-run] would squash-merge PR #42")


def test_merge_release_pr_refuses_non_release(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host(queue=False)
    with pytest.raises(click.ClickException) as exc:
        _land(monkeypatch, host, headRefName="fix/1-x")
    assert "merge-pr" in str(exc.value)
    assert host.commands == []


def test_a_merged_release_pr_has_only_its_clean_up_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """A merged PR is not merged again: what follows the merge runs — which is
    how a run that returned while the queue held the PR is completed."""
    host = _Host(queue=True)
    seen = _fake_run(monkeypatch)
    report = _land(monkeypatch, host, state="MERGED")
    assert host.commands == []
    assert report.exit_code == 0
    assert report.text.startswith("PR #42 is already merged.")
    assert seen[0] == _DELETE_HEAD


def test_a_closed_release_pr_merges_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host(queue=False)
    seen = _fake_run(monkeypatch)
    report = _land(monkeypatch, host, state="CLOSED")
    assert host.commands == [] and seen == []
    assert "closed (not merged)" in report.text


def test_merge_release_pr_refuses_red_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host(queue=False)
    with pytest.raises(click.ClickException) as exc:
        _land(
            monkeypatch,
            host,
            statusCheckRollup=[{"name": "tests", "status": "COMPLETED", "conclusion": "FAILURE"}],
        )
    assert "not all green" in str(exc.value)
    assert host.merges() == []


# --- landing through a merge queue (#1200) ----------------------------


def test_with_a_queue_the_pr_is_enqueued_and_its_head_deleted_once_merged(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Enqueued pinned to the checked head, with `--auto` and nothing else — the
    queue squashes by its own method from the repository's defaults — then
    waited for; the head branch is deleted only once GitHub reports it merged."""
    host = _Host(queue=True, progress=[_entry(2), _entry(1, "MERGEABLE"), _LANDED])
    seen = _fake_run(monkeypatch)
    report = _land(monkeypatch, host)
    assert host.merges() == [
        ["gh", "pr", "merge", "42", "--auto", "--match-head-commit", "sha-head"]
    ]
    assert report.exit_code == 0
    assert report.text.startswith("Merged release PR #42 (https://github.com/owner/repo/pull/42) ")
    assert seen[0] == _DELETE_HEAD
    out = capsys.readouterr().out
    assert "  enqueued PR #42 in the merge queue for main" in out
    assert "  queue:   PR #42 position 2 in the queue, awaiting checks, about 5 min" in out
    assert "  queue:   PR #42 position 1 in the queue, mergeable" in out


def test_no_wait_returns_accepted_with_nothing_deleted_and_a_later_run_completes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    host = _Host(queue=True, progress=[_entry(1)])
    seen = _fake_run(monkeypatch)
    report = _land(monkeypatch, host, wait_seconds=0)
    assert report.exit_code == release.EXIT_ACCEPTED == 4
    assert seen == []
    assert report.text.startswith(
        "[queued] release PR #42 is in the merge queue for main (position 1 in the queue"
    )
    assert "run `pkit release merge 42` again once it has merged" in report.text
    assert "waiting for the queue" not in capsys.readouterr().out

    # Still queued: the later run waits for it, enqueues nothing again, and
    # deletes the head once it merges.
    host.progress = [_entry(1), _LANDED]
    report = _land(monkeypatch, host)
    assert report.exit_code == 0
    assert len(host.merges()) == 1
    assert seen[0] == _DELETE_HEAD
    assert "  PR #42 is already in the merge queue for main" in capsys.readouterr().out

    # Merged by then: the later run only completes it.
    seen.clear()
    report = _land(monkeypatch, _Host(queue=True), state="MERGED")
    assert report.exit_code == 0 and seen[0] == _DELETE_HEAD


def test_a_wait_that_runs_out_keeps_the_head(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host(queue=True, progress=[_entry(3, "QUEUED")])
    seen = _fake_run(monkeypatch)
    report = _land(monkeypatch, host, wait_seconds=60)
    assert report.exit_code == 4
    assert seen == []


def test_a_pr_the_queue_drops_is_reported_and_nothing_deleted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _Host(queue=True, progress=[_entry(1), _DROPPED])
    seen = _fake_run(monkeypatch)
    with pytest.raises(release.ReleaseNotMerged) as exc:
        _land(monkeypatch, host)
    assert exc.value.exit_code == 3
    assert "left the merge queue for main without merging" in str(exc.value)
    assert "GitHub says: failed checks" in str(exc.value)
    assert "Nothing was deleted" in str(exc.value)
    assert seen == []


def test_a_push_after_the_enqueue_takes_the_pr_out_and_deletes_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _Host(queue=True, progress=[_entry(2), _entry(1, headRefOid="sha-pushed")])
    seen = _fake_run(monkeypatch)
    with pytest.raises(release.ReleaseNotMerged) as exc:
        _land(monkeypatch, host)
    assert "head moved from sha-hea to sha-pus" in str(exc.value)
    assert "it was taken out of the merge queue" in str(exc.value)
    assert any("dequeuePullRequest" in a for c in host.commands for a in c)
    assert seen == []


@pytest.mark.parametrize(
    ("host", "refusal"),
    [
        (_Host(queue=True, method="MERGE"), "the merge queue on main merges by MERGE"),
        (
            _Host(queue=True, defaults=("COMMIT_OR_PR_TITLE", "PR_BODY")),
            "title COMMIT_OR_PR_TITLE and message PR_BODY",
        ),
    ],
    ids=["not-squash", "defaults"],
)
def test_a_queue_that_would_not_make_the_release_commit_is_refused(
    monkeypatch: pytest.MonkeyPatch, host: _Host, refusal: str
) -> None:
    """The queue composes the squash commit itself: unless it squashes, from the
    PR title and body, nothing is enqueued."""
    with pytest.raises(click.ClickException) as exc:
        _land(monkeypatch, host)
    assert refusal in str(exc.value)
    assert host.merges() == []


def test_a_dry_run_on_a_queued_base_says_it_would_enqueue(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host(queue=True)
    report = _land(monkeypatch, host, dry_run=True)
    assert host.merges() == []
    assert report.text.startswith(
        "[dry-run] would enqueue PR #42 ('chore(release): v1.141.0') in the merge queue for "
        "main, wait for its merge, as long as the queue estimates plus 2 min"
    )


def test_an_unreadable_queue_merges_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host(queue=True, unreadable_after=0)
    with pytest.raises(click.ClickException) as exc:
        _land(monkeypatch, host)
    assert "cannot tell how main merges: HTTP 502. Nothing was merged." in str(exc.value)
    assert host.merges() == []


# --- a direct merge is counted only once GitHub reports it --------------


def test_an_unconfirmed_direct_merge_deletes_nothing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """gh accepts the direct merge and GitHub cannot be read since: the PR may
    have merged or been enqueued, so nothing is deleted and a re-run completes."""
    host = _Host(queue=False, unreadable_after=1)
    seen = _fake_run(monkeypatch)
    report = _land(monkeypatch, host)
    assert report.exit_code == 4
    assert report.text.startswith("[unconfirmed] gh accepted the merge of release PR #42")
    assert seen == []
    assert "could not confirm that PR #42 merged: HTTP 502" in capsys.readouterr().err


def test_a_merge_gh_only_enqueued_is_waited_for_not_taken_for_a_merge(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """On a base that requires a queue, `gh pr merge --squash` enqueues and
    exits 0: the run reads the PR, sees it unmerged, and waits for it."""
    host = _Host(queue=False, enqueues=True, progress=[_entry(1), _LANDED])
    seen = _fake_run(monkeypatch)
    report = _land(monkeypatch, host)
    assert report.exit_code == 0
    assert "GitHub does not report PR #42 merged" in capsys.readouterr().out
    assert seen[0] == _DELETE_HEAD


def test_the_cli_returns_the_reports_exit_and_takes_the_queue_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from click.testing import CliRunner

    from project_kit import cli

    asked: list[float | None] = []

    def merge(repo_root: Path, pr: int, *, dry_run: bool, wait_seconds: float | None) -> Any:
        asked.append(wait_seconds)
        return release.ReleaseMergeReport("[queued] held", 4)

    monkeypatch.setattr(cli, "_target_kit", lambda: Path("/repo/.pkit"))
    monkeypatch.setattr(cli, "merge_release_pr", merge)
    runner = CliRunner()
    result = runner.invoke(cli.main, ["release", "merge", "42", "--no-wait"])
    assert (result.exit_code, result.stdout) == (4, "[queued] held\n")
    runner.invoke(cli.main, ["release", "merge", "42", "--wait-minutes", "5"])
    runner.invoke(cli.main, ["release", "merge", "42"])
    assert asked == [0.0, 300.0, None]
    both = runner.invoke(cli.main, ["release", "merge", "42", "--no-wait", "--wait-minutes", "5"])
    assert both.exit_code == 2


# --- post-merge branch deletion (#897) -------------------------------


def test_merge_deletes_remote_head_via_api_then_cleans_up_locally(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen = _fake_run(monkeypatch)
    message = _merge_green(monkeypatch, baseRefName="develop")
    assert seen == [
        ["gh", "api", "-X", "DELETE", "repos/{owner}/{repo}/git/refs/heads/release/v1.141.0"],
        ["git", "checkout", "develop"],  # the PR's own base, not a hardcoded main
        ["git", "pull", "--ff-only"],
        ["git", "rev-parse", "--verify", "--quiet", "refs/heads/release/v1.141.0"],
        ["git", "branch", "-D", "release/v1.141.0"],
    ]
    assert "deleted remote branch 'release/v1.141.0'" in message
    assert "deleted local branch 'release/v1.141.0'" in message
    assert "[warn]" not in capsys.readouterr().err


def test_merge_when_base_checkout_fails_completes_with_a_warning(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """When the base branch cannot be checked out here (it is checked out in
    another worktree), the merge and
    the remote delete still report success, the pull is skipped, and the local
    delete is still attempted."""
    err_text = "fatal: 'main' is already checked out at '/repo'"
    seen = _fake_run(monkeypatch, checkout_stderr=err_text)
    message = _merge_green(monkeypatch)
    assert "Merged release PR #42" in message
    assert "deleted remote branch" in message
    assert ["git", "pull", "--ff-only"] not in seen
    assert ["git", "branch", "-D", "release/v1.141.0"] in seen
    assert f"[warn] git checkout main failed: {err_text}" in capsys.readouterr().err


def test_merge_with_base_branch_held_by_another_worktree_completes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The base branch checked out elsewhere, and the head held here: both
    local steps warn, and the run still returns the merged report."""
    checkout_err = "fatal: 'main' is already used by worktree at '/repo/wt-main'"
    branch_err = "error: cannot delete branch 'release/v1.141.0' used by worktree at '/repo/wt'"
    _fake_run(monkeypatch, checkout_stderr=checkout_err, branch_d_stderr=branch_err)
    message = _merge_green(monkeypatch)
    assert "Merged release PR #42" in message
    err = capsys.readouterr().err
    assert f"[warn] git checkout main failed: {checkout_err}" in err
    assert f"[warn] git branch -D release/v1.141.0 failed: {branch_err}" in err


def test_merge_without_a_local_head_copy_skips_the_local_delete_quietly(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A release PR opened by CI has no local branch; that is not a warning."""
    seen = _fake_run(monkeypatch, local_branch_exists=False)
    _merge_green(monkeypatch)
    assert ["git", "branch", "-D", "release/v1.141.0"] not in seen
    assert "[warn]" not in capsys.readouterr().err


def test_remote_head_already_gone_is_not_a_warning(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _fake_run(monkeypatch, api_stderr="gh: Reference does not exist (HTTP 422)")
    message = _merge_green(monkeypatch)
    assert "remote branch 'release/v1.141.0' already deleted" in message
    assert "[warn]" not in capsys.readouterr().err


def test_remote_head_delete_failure_is_a_warning(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _fake_run(monkeypatch, api_stderr="gh: boom (HTTP 500)")
    message = _merge_green(monkeypatch)
    assert "Merged release PR #42" in message
    err = capsys.readouterr().err
    assert "[warn] could not delete remote branch release/v1.141.0: gh: boom (HTTP 500)" in err
    assert "git push origin --delete release/v1.141.0" in err


def test_fork_release_pr_never_deletes_a_base_repo_or_local_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Security (PR #896 review): the API delete targets the BASE repo, and a
    fork author chooses the head name — `release/*` included, so the head
    guard does not cover it. No ref delete, no local `branch -D`."""
    seen = _fake_run(monkeypatch)
    message = _merge_green(monkeypatch, isCrossRepository=True)
    assert not any(argv[:2] == ["gh", "api"] for argv in seen)
    assert not any(argv[:3] == ["git", "branch", "-D"] for argv in seen)
    assert seen[0] == ["git", "checkout", "main"]
    assert "lives in a fork" in message


def test_cross_repository_is_a_required_keyword() -> None:
    """No default: every caller must state whether the PR is cross-repository,
    so a later caller cannot silently reintroduce the fork-PR deletion hole."""
    for fn in (release._gh_delete_remote_branch, release._git_cleanup_local):
        p = inspect.signature(fn).parameters["cross_repository"]
        assert p.kind is inspect.Parameter.KEYWORD_ONLY
        assert p.default is inspect.Parameter.empty
