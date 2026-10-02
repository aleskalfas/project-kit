"""Tests for the sanctioned release-PR merge path (`pkit release merge`, #475).

The gate is split into pure logic (`summarize_checks`, `parse_release_pr`,
`evaluate_release_pr`) and the landing, which is the backbone's one merge
mechanic (`pull_request_landing`, #1200). The pure logic is tested directly;
`merge_release_pr` runs on a fake GitHub (`_Host`) with and without a merge
queue — no real merge, no network, no hardcoded repo. After the merge, the
head branch is deleted on the fake GitHub by the backbone's deletion
(`pull_request_landing.delete_branch`, #1255), and locally by
`_git_cleanup_local` (#897), with `subprocess.run` stubbed. The
cross-repository guard `pkit release merge` runs at its entry (#1254) is
tested on real repositories. A request that gets no answer runs on the shared
fake (`tests.hosting_fake`), ended at its bound and settled by reading (#1256).
Release lands through the backbone's landing sequence (`pull_request_landing.land`,
#1258), planned first as a dry run, and holds no copy of its steps.
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import json
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import click
import pytest
from click.testing import CliRunner

from project_kit import cli, release, session_guard
from tests import hosting_fake as fake
from tests import sessions

#: The release PR's heads, as full commit ids — the only form the landing
#: takes its head in — each named by the shared fake (`hosting_fake.oid`).
HEAD = fake.HEAD
PUSHED = fake.oid("pushed")
MERGED = fake.oid("merged")
OTHER = fake.oid("other")
LATER = fake.oid("later")

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
        "headRefOid": HEAD,
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
# with or without a merge queue, which also holds the PR's head branch the
# backbone deletes; the local git clean-up runs through a stubbed
# `subprocess.run` (`_fake_run`), whose argvs say what was deleted here.


def _fake_run(
    monkeypatch: pytest.MonkeyPatch,
    *,
    checkout_stderr: str = "",
    pull_stderr: str = "",
    branch_d_stderr: str = "",
    local_branch_exists: bool = True,
    unmerged: str = "0",
) -> list[list[str]]:
    """Stub `subprocess.run` for the local clean-up; a non-empty stderr makes
    that step fail. The local head, when it exists, is at `HEAD`, and holds
    `unmerged` commits past the merged head ("" — this clone cannot tell).
    Returns the argvs seen."""
    seen: list[list[str]] = []

    def fake(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen.append(list(argv))
        failing = (
            (argv[:2] == ["git", "checkout"] and checkout_stderr)
            or (argv[:2] == ["git", "pull"] and pull_stderr)
            or (argv[:3] == ["git", "branch", "-D"] and branch_d_stderr)
        )
        if failing:
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr=failing)
        if argv[:2] == ["git", "rev-parse"]:
            if not local_branch_exists:
                return subprocess.CompletedProcess(argv, 1, stdout="", stderr="")
            return subprocess.CompletedProcess(argv, 0, stdout=f"{HEAD}\n", stderr="")
        if argv[:2] == ["git", "rev-list"]:
            if not unmerged:
                return subprocess.CompletedProcess(argv, 128, stdout="", stderr="bad revision")
            return subprocess.CompletedProcess(argv, 0, stdout=f"{unmerged}\n", stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(release.subprocess, "run", fake)
    return seen


def _entry(position: int, state: str = "AWAITING_CHECKS", **fields: Any) -> dict[str, Any]:
    entry = {"position": position, "state": state, "estimatedTimeToMerge": 300}
    return {"isInMergeQueue": True, "mergeQueueEntry": entry, **fields}


_MERGED_AT = "2026-10-01T10:12:00Z"
_LANDED = {
    "isInMergeQueue": False,
    "mergeQueueEntry": None,
    "state": "MERGED",
    "mergedAt": _MERGED_AT,
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
                "beforeCommit": {"oid": HEAD},
            },
        ]
    },
}


#: The head branch's tip on `_Host` follows the PR's head until it is told
#: otherwise.
_AT_THE_HEAD = "<at the PR's head>"


class _Host:
    """GitHub as the landing's `gh` reaches it: one PR whose base merges
    through a queue or not. Enqueueing takes the PR in; each later reading of a
    queued PR moves it on by the next entry of `progress`. A direct squash
    merge lands at once on a base without a queue — or, with `enqueues`, gh
    only enqueues, and without `lands` gh accepts it and nothing changes — and
    `unreadable_after` makes every reading after the first `n` fail.

    The PR's head branch is at `tip` — the PR's head unless told otherwise;
    None, gone — and the open PRs `based_on` merge into it. The backbone's
    deletion reads it (`headRef`), then the PRs based on it, and deletes it
    with `updateRefs` only while it is at the commit named, all-or-nothing as
    GitHub does, answering a refusal with an error that says only that
    something went wrong; `refuse_deletion` makes the service refuse it
    whatever the tip, with those words; `lose_deletion` makes it apply the
    deletion and gh fail with no answer (a 502), and `unread_after_deletion`
    makes the branch unreadable once a deletion was asked for. Each deletion
    asked for is recorded in `deletions` as the ref and the commit it was
    asked to be at."""

    def __init__(
        self,
        *,
        queue: bool,
        progress: list[dict[str, Any]] | None = None,
        method: str = "SQUASH",
        defaults: tuple[str, str] = ("PR_TITLE", "PR_BODY"),
        enqueues: bool = False,
        lands: bool = True,
        unreadable_after: int | None = None,
        tip: str | None = _AT_THE_HEAD,
        refuse_deletion: str = "",
        lose_deletion: bool = False,
        unread_after_deletion: bool = False,
        based_on: tuple[int, ...] = (),
        **pr: Any,
    ) -> None:
        self.pr: dict[str, Any] = {
            "id": "PR_node",
            "state": "OPEN",
            "mergedAt": None,
            "headRefOid": HEAD,
            "headRefName": "release/v1.141.0",
            "isCrossRepository": False,
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
        self.lands = lands
        self.unreadable_after = unreadable_after
        self.tip = tip
        self.refuse_deletion = refuse_deletion
        self.lose_deletion = lose_deletion
        self.unread_after_deletion = unread_after_deletion
        self.based_on = based_on
        self.reads = 0
        self.commands: list[list[str]] = []
        self.deletions: list[tuple[str, str]] = []

    def branch_tip(self) -> str | None:
        """Where the PR's head branch is now; None once it is gone."""
        return str(self.pr["headRefOid"]) if self.tip == _AT_THE_HEAD else self.tip

    def __call__(self, argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        args = list(argv)
        self.commands.append(args)
        query = next((a for a in args if a.startswith("query=")), "")
        if "updateRefs" in query:
            return self._delete(args)
        if "headRef {" in query:
            return self._read_the_branch(args)
        if "baseRefName:" in query:
            based = {
                "totalCount": len(self.based_on),
                "nodes": [{"number": number} for number in self.based_on],
            }
            answer = {"data": {"repository": {"pullRequests": based}}}
            return subprocess.CompletedProcess(args, 0, stdout=json.dumps(answer), stderr="")
        if args[:3] == ["gh", "pr", "merge"]:
            if "--auto" in args or (self.enqueues and "--squash" in args):
                self.pr["isInMergeQueue"] = True
            elif "--disable-auto" in args:
                self.pr["autoMergeRequest"] = None
            elif "--squash" in args and self.lands:
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

    def _read_the_branch(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        if self.unread_after_deletion and self.deletions:
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="HTTP 502")
        tip = self.branch_tip()
        ref = None
        if tip is not None and not self.pr["isCrossRepository"]:
            ref = {
                "target": {"oid": tip},
                "associatedPullRequests": {"totalCount": 0, "nodes": []},
            }
        node = {**self.pr, "repository": {"id": "R_repo"}, "headRef": ref}
        answer = {"data": {"repository": {"pullRequest": node}}}
        return subprocess.CompletedProcess(args, 0, stdout=json.dumps(answer), stderr="")

    def _delete(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        fields = dict(a.split("=", 1) for a in args if "=" in a and not a.startswith("query="))
        self.deletions.append((fields["name"], fields["before"]))
        if self.refuse_deletion:
            return _graphql_error(args, self.refuse_deletion)
        if self.branch_tip() is None or self.branch_tip() != fields["before"]:
            return _graphql_error(args, "Something went wrong")
        self.tip = None
        if self.lose_deletion:
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="HTTP 502: Bad Gateway")
        answer = {"data": {"updateRefs": {"clientMutationId": None}}}
        return subprocess.CompletedProcess(args, 0, stdout=json.dumps(answer), stderr="")


def _graphql_error(args: list[str], message: str) -> subprocess.CompletedProcess[str]:
    """gh's answer to a mutation GitHub answers with an error: the answer, its
    `errors` naming `message`, gh's own line on standard error, and exit 1."""
    answer = {"data": {"updateRefs": None}, "errors": [{"message": message}]}
    return subprocess.CompletedProcess(args, 1, stdout=json.dumps(answer), stderr=f"gh: {message}")


def _land(
    monkeypatch: pytest.MonkeyPatch,
    host: release.pull_request_landing.GhRunner,
    *,
    wait_seconds: float | None = None,
    dry_run: bool = False,
    force: bool = False,
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
    return release.merge_release_pr(
        Path("/repo"),
        42,
        clearance=_cleared(Path("/repo")),
        wait_seconds=wait_seconds,
        dry_run=dry_run,
        force=force,
    )


def _cleared(repo_root: Path) -> session_guard.Clearance:
    """The cross-repository guard's clearance for `repo_root`, outside any session."""
    cleared = session_guard.clear(repo_root, confirmed=False, interactive=False)
    assert isinstance(cleared, session_guard.Clearance)
    return cleared


def _merge_green(monkeypatch: pytest.MonkeyPatch, host: _Host | None = None, **raw: Any) -> str:
    """A green release PR merged directly, on a base without a queue — `host`'s,
    else a fresh one."""
    return _land(monkeypatch, host if host is not None else _Host(queue=False), **raw).text


#: The release PR's head branch, deleted at the head it merged at.
_DELETED_AT_THE_HEAD = [("refs/heads/release/v1.141.0", HEAD)]


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
            HEAD,
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
    how a run that returned while the queue held the PR is completed. Its
    clean-up keys on the head the PR merged at, on GitHub and here."""
    host = _Host(queue=True, state="MERGED", mergedAt=_MERGED_AT, headRefOid=MERGED)
    seen = _fake_run(monkeypatch)
    report = _land(monkeypatch, host, state="MERGED", headRefOid=MERGED)
    assert host.merges() == []
    assert report.exit_code == 0
    assert report.text.startswith("PR #42 is already merged.")
    assert host.deletions == [("refs/heads/release/v1.141.0", MERGED)]
    assert ["git", "rev-list", "--count", f"{MERGED}..{HEAD}"] in seen


def test_a_closed_release_pr_merges_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Closed is taken from the landing's plan, not from release's own view
    (#1258): one reading, and nothing asked of GitHub but it."""
    host = _Host(queue=False, state="CLOSED")
    seen = _fake_run(monkeypatch)
    report = _land(monkeypatch, host, state="CLOSED")
    assert [command[:3] for command in host.commands] == [["gh", "api", "graphql"]]
    assert seen == []
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
    assert host.merges() == [["gh", "pr", "merge", "42", "--auto", "--match-head-commit", HEAD]]
    assert report.exit_code == 0
    assert report.text.startswith("Merged release PR #42 (https://github.com/owner/repo/pull/42) ")
    assert host.deletions == _DELETED_AT_THE_HEAD
    assert seen[0] == ["git", "checkout", "main"]
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
    assert seen == [] and host.deletions == []
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
    assert host.deletions == _DELETED_AT_THE_HEAD
    assert "  PR #42 is already in the merge queue for main" in capsys.readouterr().out

    # Merged by then: the later run only completes it.
    merged = _Host(queue=True, state="MERGED", mergedAt=_MERGED_AT)
    report = _land(monkeypatch, merged, state="MERGED")
    assert report.exit_code == 0
    assert merged.merges() == [] and merged.deletions == _DELETED_AT_THE_HEAD


def test_a_wait_that_runs_out_keeps_the_head(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host(queue=True, progress=[_entry(3, "QUEUED")])
    seen = _fake_run(monkeypatch)
    report = _land(monkeypatch, host, wait_seconds=60)
    assert report.exit_code == 4
    assert seen == [] and host.deletions == []


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
    assert seen == [] and host.deletions == []


def test_a_push_after_the_enqueue_takes_the_pr_out_and_deletes_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _Host(queue=True, progress=[_entry(2), _entry(1, headRefOid=PUSHED)])
    seen = _fake_run(monkeypatch)
    with pytest.raises(release.ReleaseNotMerged) as exc:
        _land(monkeypatch, host)
    assert f"head moved from {HEAD[:7]} to {PUSHED[:7]}" in str(exc.value)
    assert "it was taken out of the merge queue" in str(exc.value)
    assert any("dequeuePullRequest" in a for c in host.commands for a in c)
    assert seen == [] and host.deletions == []


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
    assert "cannot tell how main merges: HTTP 502. This run asked nothing." in str(exc.value)
    assert host.merges() == []


def test_a_head_the_queue_dropped_is_not_enqueued_again_without_force(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The queue dropped this very head — its checks failed on the merge it was
    about to make, or a maintainer took it out on purpose: it is not enqueued
    again unchanged unless `--force`, the rule project-management's merge
    verbs keep."""
    host = _Host(queue=True, timelineItems=_DROPPED["timelineItems"])
    with pytest.raises(click.ClickException) as exc:
        _land(monkeypatch, host)
    message = str(exc.value)
    assert (
        f"the merge queue on main dropped the PR at its current head {HEAD[:7]} at "
        "2026-10-01T10:05:00Z (GitHub says: failed checks); the same head is not enqueued "
        "again unchanged"
    ) in message
    assert "pass --force to enqueue this head again. Nothing was enqueued." in message
    assert host.merges() == []

    host.progress = [_entry(1), _LANDED]
    _fake_run(monkeypatch)
    report = _land(monkeypatch, host, force=True)
    assert report.exit_code == 0
    assert host.merges() == [["gh", "pr", "merge", "42", "--auto", "--match-head-commit", HEAD]]
    assert (
        "  the merge queue dropped PR #42 at this head at 2026-10-01T10:05:00Z: failed checks; "
        "enqueuing it again (--force)"
    ) in capsys.readouterr().out


@pytest.mark.parametrize(
    ("host", "problem"),
    [
        (
            _Host(queue=True, method="MERGE", isInMergeQueue=True, progress=[_entry(1), _LANDED]),
            "the merge queue on main merges by MERGE",
        ),
        (
            _Host(
                queue=True,
                defaults=("COMMIT_OR_PR_TITLE", "PR_BODY"),
                isInMergeQueue=True,
                progress=[_entry(1), _LANDED],
            ),
            "title COMMIT_OR_PR_TITLE and message PR_BODY",
        ),
    ],
    ids=["not-squash", "defaults"],
)
def test_a_pr_already_queued_where_the_queue_would_not_make_the_release_commit_is_warned(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], host: _Host, problem: str
) -> None:
    """Already in the queue, the PR lands as the queue composes it: the run
    waits for it as before, and warns that the commit will not be a release's,
    with how to land it as one."""
    _fake_run(monkeypatch)
    report = _land(monkeypatch, host)
    assert report.exit_code == 0
    assert host.merges() == []
    err = capsys.readouterr().err
    assert "[warn] release PR #42 is already in the merge queue for main, but " in err
    assert problem in err
    assert "take it out of the queue (in the PR's merge box)" in err


def test_a_merge_at_a_head_whose_checks_were_not_read_is_warned(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    host = _Host(
        queue=True,
        isInMergeQueue=True,
        progress=[_entry(1), {**_LANDED, "headRefOid": OTHER}],
    )
    seen = _fake_run(monkeypatch)
    report = _land(monkeypatch, host)
    assert report.exit_code == 0
    assert (
        f"[warn] release PR #42 merged at head {OTHER[:7]}, not at {HEAD[:7]}, the head whose "
        "checks were read."
    ) in capsys.readouterr().err
    assert ["git", "rev-list", "--count", f"{OTHER}..{HEAD}"] in seen
    assert host.deletions == [("refs/heads/release/v1.141.0", OTHER)]


# --- a direct merge is counted only once GitHub reports it --------------


def test_an_unconfirmed_direct_merge_deletes_nothing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """gh accepts the direct merge and GitHub cannot be read since: the PR may
    have merged or been enqueued, so nothing is deleted and a re-run completes.
    The plan's reading and the landing's own come before the merge (#1258)."""
    host = _Host(queue=False, unreadable_after=2)
    seen = _fake_run(monkeypatch)
    report = _land(monkeypatch, host)
    assert report.exit_code == 4
    assert report.text.startswith("[unconfirmed] gh accepted the merge of release PR #42")
    assert seen == [] and host.deletions == []
    assert "could not confirm that PR #42 merged: HTTP 502" in capsys.readouterr().err


def _no_answer(*, queue: bool, ends: str) -> tuple[fake.HostingService, Any]:
    """The shared fake GitHub holding the release PR, whose merge — or, with a
    `queue`, enqueue — never gets an answer, as the landing's `gh` reaches it
    through its bounded start: ended at its bound. Since, the PR reads open
    (`not-made`) or cannot be read (`unconfirmed`)."""
    host = fake.HostingService(
        number=42,
        title="chore(release): v1.141.0",
        head_ref="release/v1.141.0",
        head_oid=HEAD,
    )
    if queue:
        host.set_base(fake.Base(queue=True))
    kind = fake.ENQUEUE if queue else fake.MERGE
    host.never_receive(kind)
    if ends == "unconfirmed":
        host.before(kind, lambda service: service.fail(fake.READ, count=None))

    def bounded(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        try:
            return host(argv)
        except fake.NoAnswer:
            raise subprocess.TimeoutExpired(list(argv), 30.0) from None

    return host, bounded


@pytest.mark.parametrize("queue", [False, True], ids=["merge", "enqueue"])
def test_a_request_with_no_answer_github_cannot_settle_is_reported_unconfirmed(
    monkeypatch: pytest.MonkeyPatch, queue: bool
) -> None:
    """The run does not hang on a `gh` that never answers: its bound ends it.
    With GitHub unreadable since, the report says what was asked and that
    whether it was made is not known, names the reading that tells, claims
    neither that the release merged nor that it did not, deletes nothing, and
    exits 4 as an unconfirmed direct merge does (#1256)."""
    host, bounded = _no_answer(queue=queue, ends="unconfirmed")
    seen = _fake_run(monkeypatch)
    report = _land(monkeypatch, bounded)
    asked = "enqueue" if queue else "merge"
    assert report.exit_code == release.EXIT_ACCEPTED == 4
    assert report.text == (
        f"[unconfirmed] the {asked} of PR #42 got no usable answer (`gh` did not answer within "
        f"30 s, and was ended), and PR #42 could not be read since (HTTP 502: Bad Gateway): "
        f"whether the {asked} was made is not known. Whether release PR #42 merged into main, or "
        "entered its merge queue, is not known, and nothing was deleted. Read where it stands "
        "with `pkit pull-request read 42`, then run `pkit release merge 42` again: it reads "
        "the PR first, lands it if it has not, and deletes the head branch once it has merged."
    )
    assert fake.BRANCH not in host.kinds() and fake.DELETE_REF not in host.kinds()
    assert seen == []


@pytest.mark.parametrize("queue", [False, True], ids=["merge", "enqueue"])
def test_a_request_with_no_answer_read_open_twice_is_not_seen_made_and_says_only_that(
    monkeypatch: pytest.MonkeyPatch, queue: bool
) -> None:
    """Two readings find the PR neither merged nor queued: the run refuses,
    exit 1, saying what the readings saw and that this run saw nothing merged
    — never that nothing merged, since the service may still apply the
    request — and naming the reading and the re-run, as its unconfirmed
    report does."""
    host, bounded = _no_answer(queue=queue, ends="not-made")
    _fake_run(monkeypatch)
    with pytest.raises(click.ClickException) as exc:
        _land(monkeypatch, bounded)
    asked = "enqueue" if queue else "merge"
    found = "neither queued nor merged" if queue else "neither merged nor queued"
    assert exc.value.exit_code == 1
    assert exc.value.message == (
        f"the {asked} of PR #42 got no usable answer (`gh` did not answer within 30 s, and was "
        f"ended), and was not seen made on two readings 40 s apart, the second 40 s after it "
        f"was sent: PR #42 reads {found} (not in the queue). This run saw nothing merged, and "
        "nothing was deleted. Read where release PR #42 stands with `pkit pull-request read "
        "42`, then run `pkit release merge 42` again: it reads the PR first, lands it if it "
        "has not, and deletes the head branch once it has merged."
    )
    assert "Nothing was merged" not in exc.value.message
    assert host.kinds()[-3:] == [fake.ENQUEUE if queue else fake.MERGE, fake.READ, fake.READ]


def test_the_release_prs_own_reading_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    """`gh pr view` runs through the command runner's one bounded start, as the
    landing's readings do; past its bound the run ends, having asked nothing."""
    started: list[tuple[list[str], Path | None, float]] = []

    def hung(argv: Sequence[str], *, cwd: Path | None, seconds: float) -> Any:
        started.append((list(argv)[:3], cwd, seconds))
        raise subprocess.TimeoutExpired(list(argv), seconds)

    monkeypatch.setattr(release.command_runner, "run_bounded", hung)
    with pytest.raises(
        click.ClickException,
        match=r"did not answer within 15 s, and was ended\. This run asked nothing\.",
    ):
        release._gh_pr_view(42, Path("/repo"))
    assert started == [
        (["gh", "pr", "view"], Path("/repo"), release.pull_request_landing.GH_READ_SECONDS)
    ]


def test_a_dequeue_whose_end_is_not_known_after_a_head_moved_says_so(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The head moved while the PR was queued, and taking it out got no answer
    GitHub could settle: the run says whether it left the queue is not known,
    never that taking it out failed, and names the reading that tells."""
    host = fake.HostingService(
        number=42,
        title="chore(release): v1.141.0",
        head_ref="release/v1.141.0",
        head_oid=HEAD,
    )
    host.set_base(fake.Base(queue=True))
    host.progress = [fake.at(1), fake.pushes(PUSHED)]
    host.never_receive(fake.DEQUEUE)
    host.before(fake.DEQUEUE, lambda service: service.fail(fake.READ, count=None))

    def bounded(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        try:
            return host(argv)
        except fake.NoAnswer:
            raise subprocess.TimeoutExpired(list(argv), 30.0) from None

    _fake_run(monkeypatch)
    with pytest.raises(release.ReleaseNotMerged) as exc:
        _land(monkeypatch, bounded)
    message = str(exc.value)
    assert "whether taking it out of the merge queue worked is not known" in message
    assert "Read where it stands with `pkit pull-request read 42`" in message
    assert "failed" not in message


def test_a_head_that_moved_on_a_pr_the_queue_merged_meanwhile_says_it_merged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The head moved while the PR was queued, and the queue merged it before
    it could be taken out: the run says it merged, at which head — never "it
    may still merge… take it out yourself", which is no longer true — and that
    a re-run deletes the head branch."""
    host = fake.HostingService(
        number=42,
        title="chore(release): v1.141.0",
        head_ref="release/v1.141.0",
        head_oid=HEAD,
    )
    host.set_base(fake.Base(queue=True))
    host.progress = [fake.at(1), fake.pushes(PUSHED)]
    # The dequeue's own first reading: after the plan's, the landing's, and
    # the wait's two (#1258).
    host.before(fake.READ, lambda service: service.merge_now(), nth=5)
    _fake_run(monkeypatch)
    with pytest.raises(release.ReleaseNotMerged) as exc:
        _land(monkeypatch, host)
    message = str(exc.value)
    assert message.startswith(
        f"release PR #42's head moved from {HEAD[:7]} to {PUSHED[:7]} after its checks were "
        "read, and it merged before it could be taken out of the merge queue: PR #42 has merged "
        f"at head {PUSHED[:7]} (merged at "
    )
    assert "take it out yourself" not in message
    assert "run `pkit release merge 42` again to delete the head branch" in message
    assert fake.DEQUEUE not in host.kinds()


def test_a_direct_merge_never_seen_merged_on_a_base_without_a_queue_names_no_queue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """gh accepted the direct merge, and GitHub never reports it merged: on a
    base with no queue, the report does not say a queue dropped the PR."""
    host = _Host(queue=False, lands=False)
    seen = _fake_run(monkeypatch)
    with pytest.raises(release.ReleaseNotMerged) as exc:
        _land(monkeypatch, host)
    assert str(exc.value) == (
        "gh accepted the merge of release PR #42 into main, but GitHub reports it still "
        "open. Nothing was deleted; look at the PR, then run `pkit release merge 42` again."
    )
    assert seen == []


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
    assert host.deletions == _DELETED_AT_THE_HEAD
    assert seen[0] == ["git", "checkout", "main"]


def test_the_cli_returns_the_reports_exit_and_takes_the_queue_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked: list[tuple[float | None, bool]] = []

    def merge(
        repo_root: Path,
        pr: int,
        *,
        clearance: session_guard.Clearance,
        dry_run: bool,
        wait_seconds: float | None,
        force: bool,
    ) -> Any:
        asked.append((wait_seconds, force))
        return release.ReleaseMergeReport("[queued] held", 4)

    monkeypatch.setattr(cli, "_target_kit", lambda: Path("/repo/.pkit"))
    monkeypatch.setattr(cli, "merge_release_pr", merge)
    runner = CliRunner()
    result = runner.invoke(cli.main, ["release", "merge", "42", "--no-wait"])
    assert (result.exit_code, result.stdout) == (4, "[queued] held\n")
    runner.invoke(cli.main, ["release", "merge", "42", "--wait-minutes", "5"])
    runner.invoke(cli.main, ["release", "merge", "42", "--force"])
    assert asked == [(0.0, False), (300.0, False), (None, True)]
    both = runner.invoke(cli.main, ["release", "merge", "42", "--no-wait", "--wait-minutes", "5"])
    assert both.exit_code == 2


# --- the cross-repository guard (#1254) -------------------------------


def test_a_clearance_for_another_repository_merges_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The clearance covers the repository the guard looked at: one for
    another stops the run before it reads the PR."""
    host = _Host(queue=False)
    monkeypatch.setattr(release.pull_request_landing, "gh_runner", lambda cwd: host)
    with pytest.raises(ValueError, match="the clearance is for"):
        release.merge_release_pr(Path("/repo"), 42, clearance=_cleared(Path("/elsewhere")))
    assert host.commands == []


@pytest.fixture
def cleared_merges(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Path, str, bool]]:
    """`merge_release_pr` stubbed: each run's repository, how its clearance
    passed, and whether it was a dry run."""
    runs: list[tuple[Path, str, bool]] = []

    def merge(
        repo_root: Path, pr: int, *, clearance: session_guard.Clearance, dry_run: bool, **_: Any
    ) -> release.ReleaseMergeReport:
        runs.append((repo_root, clearance.passed, dry_run))
        return release.ReleaseMergeReport(f"Merged release PR #{pr}.")

    monkeypatch.setattr(cli, "merge_release_pr", merge)
    return runs


@pytest.fixture
def foreign(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A session rooted in one repository, and `release merge` run in another."""
    _, target = sessions.rooted_elsewhere(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "_target_kit", lambda: target / ".pkit")
    return target


def test_in_another_repository_with_no_terminal_and_no_flag_nothing_merges(
    foreign: Path, cleared_merges: list[tuple[Path, str, bool]]
) -> None:
    result = CliRunner().invoke(cli.main, ["release", "merge", "42"])
    assert result.exit_code == 1
    assert "the cross-repository guard refused" in result.stderr
    assert "--allow-foreign-repo" in result.stderr and "Nothing was merged" in result.stderr
    assert cleared_merges == []


def test_the_flag_confirms_a_release_merge_in_another_repository(
    foreign: Path, cleared_merges: list[tuple[Path, str, bool]]
) -> None:
    result = CliRunner().invoke(cli.main, ["release", "merge", "42", "--allow-foreign-repo"])
    assert result.exit_code == 0
    assert cleared_merges == [(foreign, "flag", False)]


def test_in_a_pipeline_with_no_anchor_it_needs_no_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cleared_merges: list[tuple[Path, str, bool]],
) -> None:
    target = sessions.repository(tmp_path / "target", "https://github.com/octo/project.git")
    monkeypatch.setattr(cli, "_target_kit", lambda: target / ".pkit")
    result = CliRunner().invoke(cli.main, ["release", "merge", "42"])
    assert result.exit_code == 0
    assert cleared_merges == [(target, "undetermined", False)]


def test_a_dry_run_reports_the_verdict_and_asks_nothing(
    foreign: Path, cleared_merges: list[tuple[Path, str, bool]]
) -> None:
    """A dry run never asks: in another repository without the flag it ends
    refused, as a run with nobody to ask would, saying what a real run would
    do; with it, it reports how the guard passed."""
    refused = CliRunner().invoke(cli.main, ["release", "merge", "42", "--dry-run"])
    assert refused.exit_code == 1
    assert "A dry run does not ask; a run at a terminal would ask" in refused.stderr
    assert "no terminal to ask" not in refused.stderr
    assert cleared_merges == []
    flagged = CliRunner().invoke(
        cli.main, ["release", "merge", "42", "--dry-run", "--allow-foreign-repo"]
    )
    assert flagged.exit_code == 0
    assert "cross-repository guard: another repository than the session's anchor" in (
        flagged.stdout
    )
    assert cleared_merges == [(foreign, "flag", True)]


# --- post-merge branch deletion (#897, #1255) ----------------------------


def test_merge_deletes_the_remote_head_at_the_merged_head_then_cleans_up_locally(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The remote head branch is the backbone's to delete — one compare-and-
    delete at the head that merged, in the repository release merge cleared
    — then the local clean-up runs here."""
    host = _Host(queue=False)
    seen = _fake_run(monkeypatch)
    message = _merge_green(monkeypatch, host, baseRefName="develop")
    assert host.deletions == _DELETED_AT_THE_HEAD
    assert host.branch_tip() is None
    assert seen == [
        ["git", "checkout", "develop"],  # the PR's own base, not a hardcoded main
        ["git", "pull", "--ff-only"],
        ["git", "rev-parse", "--verify", "--quiet", "refs/heads/release/v1.141.0"],
        ["git", "rev-list", "--count", f"{HEAD}..{HEAD}"],  # nothing past the merged head
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


def test_remote_head_already_gone_is_said_in_one_line_and_not_asked_again(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A repository that deletes head branches as PRs merge: the reading finds
    the branch gone, and no deletion is asked for."""
    host = _Host(queue=False, tip=None)
    _fake_run(monkeypatch)
    message = _merge_green(monkeypatch, host)
    assert "  remote branch 'release/v1.141.0' is not there; nothing to delete." in message
    assert host.deletions == []
    assert "[warn]" not in capsys.readouterr().err


def test_a_push_to_the_head_after_the_merge_keeps_the_remote_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The fifth obligation (ADR-061 point 5): the branch is deleted only at
    the head that merged, so a push since is not lost — and the landing is
    not failed for it. The line names the command that deletes it later, and
    the local branch is kept with it."""
    host = _Host(queue=False, tip=LATER)
    seen = _fake_run(monkeypatch)
    report = _land(monkeypatch, host)
    assert report.exit_code == 0
    assert "Merged release PR #42" in report.text
    assert (
        f"  kept remote branch 'release/v1.141.0': its tip is {LATER[:7]}, not {HEAD[:7]}, the "
        "head PR #42 merged at: a push since the merge, or a branch of that name made since, is "
        f"not deleted. To delete it later: `pkit pull-request delete-branch 42 --expect {HEAD}`."
    ) in report.text
    assert (
        "  kept local branch 'release/v1.141.0': its branch on GitHub was not deleted (kept), "
        "and the local one goes only with it (`git branch -D release/v1.141.0` once it has)."
    ) in report.text
    assert host.deletions == [] and host.branch_tip() == LATER
    assert not any(argv[:3] == ["git", "branch", "-D"] for argv in seen)


def test_a_deletion_the_service_refuses_keeps_the_branch_in_its_words(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A branch protected from deletion: the service answers the
    compare-and-delete with an error that says only that something went
    wrong, the run says so in one line, with what the service said, and the
    landing stands."""
    said = "Something went wrong while executing your query."
    host = _Host(queue=False, refuse_deletion=said)
    seen = _fake_run(monkeypatch)
    report = _land(monkeypatch, host)
    assert report.exit_code == 0
    assert (
        "  kept remote branch 'release/v1.141.0': the service did not delete it: Something went "
        "wrong while executing your query. To delete it later: `pkit pull-request "
        f"delete-branch 42 --expect {HEAD}`."
    ) in report.text
    assert host.deletions == _DELETED_AT_THE_HEAD and host.branch_tip() == HEAD
    assert not any(argv[:3] == ["git", "branch", "-D"] for argv in seen)
    assert "[warn]" not in capsys.readouterr().err


def test_a_deletion_with_no_answer_and_no_reading_since_is_said_not_known(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The deletion made and its answer lost, and the branch unreadable since:
    whether it was deleted is not known, one line says so and names the
    command to run again, the local branch stays, and the landing stands."""
    host = _Host(queue=False, lose_deletion=True, unread_after_deletion=True)
    seen = _fake_run(monkeypatch)
    report = _land(monkeypatch, host)
    assert report.exit_code == 0
    assert (
        "  whether remote branch 'release/v1.141.0' was deleted is not known: the deletion got "
        "no usable answer (HTTP 502: Bad Gateway), and the branch could not be read since "
        "(HTTP 502). To delete it later: `pkit pull-request delete-branch 42 --expect "
        f"{HEAD}`."
    ) in report.text
    assert "kept local branch 'release/v1.141.0'" in report.text
    assert not any(argv[:3] == ["git", "branch", "-D"] for argv in seen)


def test_a_direct_merge_at_another_head_deletes_at_the_head_that_merged_with_a_warning(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Should the PR have merged at another head than the one whose checks
    were read — someone else merging it, at a head pushed since — the landing
    ends merged at another head, and release deletes the branch at the head
    that merged (`merged_head`), as its wait path always did (#1258): the
    fifth obligation, that the branch goes only at the head that merged,
    holds. The merge at another head is warned about."""

    class _MergedElsewhere(_Host):
        def __call__(self, argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
            done = super().__call__(argv)
            if list(argv)[:3] == ["gh", "pr", "merge"]:
                self.pr["headRefOid"] = OTHER
            return done

    host = _MergedElsewhere(queue=False)
    seen = _fake_run(monkeypatch)
    report = _land(monkeypatch, host)
    assert report.exit_code == 0
    assert "  deleted remote branch 'release/v1.141.0'." in report.text
    assert host.deletions == [("refs/heads/release/v1.141.0", OTHER)]
    assert host.branch_tip() is None
    assert (
        f"[warn] release PR #42 merged at head {OTHER[:7]}, not at {HEAD[:7]}, the head whose "
        "checks were read."
    ) in capsys.readouterr().err
    assert ["git", "rev-list", "--count", f"{OTHER}..{HEAD}"] in seen


def test_a_branch_other_open_prs_are_based_on_is_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    host = _Host(queue=False, based_on=(77,))
    _fake_run(monkeypatch)
    report = _land(monkeypatch, host)
    assert report.exit_code == 0
    assert (
        "  kept remote branch 'release/v1.141.0': another open pull request is based on this "
        "branch (#77), and a branch an open pull request merges into is kept."
    ) in report.text
    assert host.deletions == []


def test_fork_release_pr_never_deletes_a_base_repo_or_local_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Security (PR #896 review): a fork author chooses the head name —
    `release/*` included, so the head guard does not cover it. The backbone
    refuses to delete it, asking nothing more than its reading, and no local
    `branch -D` runs."""
    host = _Host(queue=False, isCrossRepository=True)
    seen = _fake_run(monkeypatch)
    message = _merge_green(monkeypatch, host, isCrossRepository=True)
    assert host.deletions == []
    assert not any(argv[:3] == ["git", "branch", "-D"] for argv in seen)
    assert seen[0] == ["git", "checkout", "main"]
    assert "  remote branch 'release/v1.141.0' not deleted: PR #42's head is in another" in message


@pytest.mark.parametrize("unmerged", ["2", ""], ids=["work-since", "cannot-tell"])
def test_a_local_head_holding_commits_past_the_merge_is_kept(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], unmerged: str
) -> None:
    """The local head is deleted only when everything on it merged: work since
    the merged head — or a clone that cannot tell — keeps it, with a warning."""
    seen = _fake_run(monkeypatch, unmerged=unmerged)
    message = _merge_green(monkeypatch)
    assert ["git", "branch", "-D", "release/v1.141.0"] not in seen
    assert "deleted local branch" not in message
    assert (
        f"[warn] local branch release/v1.141.0 (at {HEAD[:7]}) holds commits the merge at "
        f"{HEAD[:7]} does not, or this clone cannot tell; it is kept."
    ) in capsys.readouterr().err


def test_the_merged_head_is_a_required_keyword_of_the_local_clean_up() -> None:
    p = inspect.signature(release._git_cleanup_local).parameters["merged_head"]
    assert p.kind is inspect.Parameter.KEYWORD_ONLY
    assert p.default is inspect.Parameter.empty


def test_what_became_of_the_remote_branch_is_a_required_keyword_of_the_local_clean_up() -> None:
    """The local branch goes only with the remote one, so the local clean-up's
    caller must say what became of that one."""
    p = inspect.signature(release._git_cleanup_local).parameters["remote"]
    assert p.kind is inspect.Parameter.KEYWORD_ONLY
    assert p.default is inspect.Parameter.empty


def test_cross_repository_is_a_required_keyword() -> None:
    """No default: the local clean-up's caller must state whether the PR is
    cross-repository, so a later caller cannot silently reintroduce the
    fork-PR deletion hole."""
    p = inspect.signature(release._git_cleanup_local).parameters["cross_repository"]
    assert p.kind is inspect.Parameter.KEYWORD_ONLY
    assert p.default is inspect.Parameter.empty


def test_release_keeps_no_copy_of_the_remote_deletion() -> None:
    """The head branch on GitHub is deleted only by the backbone's deletion
    (ADR-061 point 1): release holds no deletion of its own."""
    assert not hasattr(release, "_gh_delete_remote_branch")
    source = inspect.getsource(release)
    assert "git/refs/heads" not in source and "updateRefs" not in source


# --- landing through the backbone's sequence (#1258) ------------------------------

#: The landing's own steps, which release reaches only through `land`.
_THE_LANDINGS_STEPS = (
    "read",
    "squash_commit_defaults",
    "squash_merge",
    "enqueue",
    "wait_for_merge",
    "dequeue",
)


def test_release_holds_no_copy_of_the_landing_sequence() -> None:
    """`pkit release merge` lands through `pull_request_landing.land` and
    references none of the steps it composes (ADR-061 point 5)."""
    tree = ast.parse(inspect.getsource(release))
    used = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "pull_request_landing"
    }
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and (node.module or "").endswith("pull_request_landing")
        for alias in node.names
    }
    assert "land" in used
    assert not (used | imported) & set(_THE_LANDINGS_STEPS)


def test_release_plans_then_lands_through_land_with_its_own_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The plan first — a dry run — then the landing, both pinned to the head
    release's gates read, with `--force` as `allow_dropped_head` and a bad
    shape on a queued PR waited for with a warning."""
    calls: list[tuple[bool, Any]] = []
    land = release.pull_request_landing.land

    def recording(*args: Any, **kwargs: Any) -> Any:
        calls.append((kwargs["dry_run"], kwargs["options"]))
        assert kwargs["head"] == HEAD and kwargs["subject"] == "chore(release): v1.141.0"
        return land(*args, **kwargs)

    monkeypatch.setattr(release.pull_request_landing, "land", recording)
    _fake_run(monkeypatch)
    report = _land(monkeypatch, _Host(queue=False), force=True, wait_seconds=60)
    assert report.exit_code == 0
    options = release.pull_request_landing.LandOptions(
        seconds=60, allow_dropped_head=True, queued_bad_shape="warn"
    )
    assert calls == [(True, options), (False, options)]


def test_no_caller_decides_on_the_landings_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    """Release reads how the landing ended from its end, never from the
    command's exit: with every exit the command would give taken away,
    release ends as it did."""
    monkeypatch.setattr(cli, "_LAND_EXITS", {})
    _fake_run(monkeypatch)
    assert _land(monkeypatch, _Host(queue=False)).exit_code == 0
    queued = _land(monkeypatch, _Host(queue=True, progress=[_entry(1)]), wait_seconds=0)
    assert queued.exit_code == release.EXIT_ACCEPTED
    with pytest.raises(release.ReleaseNotMerged):
        _land(monkeypatch, _Host(queue=True, progress=[_entry(1), _DROPPED]))
    assert "_LAND_EXITS" not in inspect.getsource(release)


def test_a_view_gh_answers_with_no_json_object_ends_the_run_having_asked_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def answered(argv: Sequence[str], *, cwd: Path | None, seconds: float) -> Any:
        return subprocess.CompletedProcess(list(argv), 0, stdout="<html>busy</html>", stderr="")

    monkeypatch.setattr(release.command_runner, "run_bounded", answered)
    with pytest.raises(click.ClickException) as exc:
        release._gh_pr_view(42, Path("/repo"))
    assert exc.value.message == (
        "`gh pr view 42` answered with something that is not a JSON object ('<html>busy</html>'). "
        "This run asked nothing."
    )


def test_a_head_that_moved_between_the_view_and_the_landing_exits_3_with_nothing_sent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Release's gates read one head, the landing's reading finds another:
    nothing is sent — before #1258 the pinned request failed, exit 1 — and the
    run exits 3, as release's exit 3 says of a head that moved."""
    host = _Host(queue=False, headRefOid=PUSHED)
    seen = _fake_run(monkeypatch)
    with pytest.raises(release.ReleaseNotMerged) as exc:
        _land(monkeypatch, host)
    assert exc.value.exit_code == 3
    assert str(exc.value) == (
        f"release PR #42's head moved from {HEAD[:7]} to {PUSHED[:7]} after its checks were "
        "read; it is in no merge queue, and nothing was merged or deleted. Run `pkit release "
        "merge 42` again once the new head is green."
    )
    assert host.merges() == [] and seen == []


@pytest.mark.parametrize("queued_at", [HEAD, PUSHED], ids=["the-head", "another-head"])
def test_a_pr_already_queued_skips_the_gates(
    monkeypatch: pytest.MonkeyPatch, queued_at: str
) -> None:
    """A plan that waits, or takes the PR out of the queue, runs no gate:
    red checks do not stop it."""
    progress = [_entry(1), _LANDED] if queued_at == HEAD else []
    host = _Host(queue=True, isInMergeQueue=True, headRefOid=queued_at, progress=progress)
    _fake_run(monkeypatch)
    red = [{"name": "tests", "status": "COMPLETED", "conclusion": "FAILURE"}]
    if queued_at == HEAD:
        assert _land(monkeypatch, host, statusCheckRollup=red).exit_code == 0
    else:
        with pytest.raises(release.ReleaseNotMerged, match="taken out of the merge queue"):
            _land(monkeypatch, host, statusCheckRollup=red)


def test_a_dry_run_on_a_pr_queued_at_another_head_says_it_would_take_it_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _Host(queue=True, isInMergeQueue=True, headRefOid=PUSHED)
    report = _land(monkeypatch, host, dry_run=True)
    assert report.text == (
        f"[dry-run] PR #42 is in the merge queue for main at head {PUSHED[:7]}, not at "
        f"{HEAD[:7]}, the head whose checks were read; would take it out of the queue; nothing "
        "changed."
    )
    assert not any("dequeuePullRequest" in arg for command in host.commands for arg in command)


def test_a_dequeue_that_could_not_read_the_pr_says_whether_it_left_is_not_known(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Taking the PR out could not read it before sending anything: not a
    dequeue that failed — whether it is still queued is not known."""
    host = fake.HostingService(
        number=42,
        title="chore(release): v1.141.0",
        head_ref="release/v1.141.0",
        head_oid=HEAD,
    )
    host.set_base(fake.Base(queue=True))
    host.progress = [fake.at(1), fake.pushes(PUSHED)]
    host.after(fake.READ, lambda service: service.fail(fake.READ, count=None), nth=4)
    _fake_run(monkeypatch)
    with pytest.raises(release.ReleaseNotMerged) as exc:
        _land(monkeypatch, host)
    message = str(exc.value)
    assert "whether taking it out of the merge queue worked is not known" in message
    assert "failed" not in message
    assert fake.DEQUEUE not in host.kinds()


@pytest.mark.parametrize("head", [HEAD[:7], "sha-head"], ids=["abbreviated", "not-a-commit-id"])
def test_a_head_the_landing_refuses_ends_the_run_having_asked_nothing(
    monkeypatch: pytest.MonkeyPatch, head: str
) -> None:
    """The landing takes its head as a full commit id, and refuses any other
    form before it reads, imported as by command (ADR-061 point 5): a view
    that names the head otherwise ends release's run, exit 1, never a
    traceback, with nothing read."""
    host = _Host(queue=False, headRefOid=head)
    with pytest.raises(click.ClickException) as exc:
        _land(monkeypatch, host, headRefOid=head)
    assert exc.value.exit_code == 1
    assert exc.value.message == (
        f"the landing refuses the head `gh pr view 42` names for PR #42: a landing is pinned to "
        f"the head the caller checked, named as a full commit id (40 or 64 hexadecimal "
        f"characters), and {head!r} is not one. This run asked nothing."
    )
    assert host.commands == []


def test_a_refused_merge_of_a_pr_auto_merge_holds_warns_that_it_is_still_armed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """On a base without a queue, auto-merge holds the release PR for
    requirements that are not met, so gh refuses the plain merge: exit 1,
    with the landing's warning that auto-merge will merge it, unpinned, and
    how to turn it off."""
    host = fake.HostingService(
        number=42, title="chore(release): v1.141.0", head_ref="release/v1.141.0"
    )
    host.auto_merge, host.requirements_met = True, False
    _fake_run(monkeypatch)
    with pytest.raises(click.ClickException) as exc:
        _land(monkeypatch, host)
    assert exc.value.exit_code == 1
    assert exc.value.message.startswith("`gh pr merge 42` failed: X Pull request #42 is not")
    assert (
        "[warn] auto-merge is still enabled on PR #42: GitHub merges it on its own once the "
        "base's requirements are met, at whatever head it has then — not pinned to "
        f"{HEAD[:7]}, the head that was checked. To keep release PR #42 from merging so, turn "
        "auto-merge off in its merge box, or run `gh pr merge 42 --disable-auto`."
    ) in capsys.readouterr().err


def test_release_decides_on_the_decoded_end_document(monkeypatch: pytest.MonkeyPatch) -> None:
    """The plan and the landing each reach release as their end document
    states them, decoded strictly — never as the landing's in-memory end."""
    decoded: list[str] = []
    decode = release.pull_request_landing.decode_end

    def recording(document: object) -> dict[str, Any]:
        end = decode(document)
        decoded.append(end["ended"])
        return end

    monkeypatch.setattr(release.pull_request_landing, "decode_end", recording)
    _fake_run(monkeypatch)
    assert _land(monkeypatch, _Host(queue=False)).exit_code == 0
    assert decoded == ["planned", "merged"]


def test_release_acts_on_no_end_its_document_cannot_carry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A merged end whose reading names no head — the state release once
    fell back on its own view's head for — is one the document cannot
    carry: should a landing state it, the run ends, exit 1, and nothing is
    deleted at a head nobody read."""
    land = release.pull_request_landing.land

    def merged_naming_no_head(*args: Any, **kwargs: Any) -> Any:
        end = land(*args, **kwargs)
        if kwargs["dry_run"] or end.reading is None:
            return end
        return dataclasses.replace(end, reading=dataclasses.replace(end.reading, head_oid=""))

    monkeypatch.setattr(release.pull_request_landing, "land", merged_naming_no_head)
    host = _Host(queue=False)
    seen = _fake_run(monkeypatch)
    with pytest.raises(click.ClickException) as exc:
        _land(monkeypatch, host)
    assert exc.value.exit_code == 1
    assert exc.value.message.startswith(
        "the landing of release PR #42 ended in a document that states no end (a landing that "
        "ends merged cannot name `merged_head` None). Nothing was deleted."
    )
    assert host.deletions == [] and seen == []


# --- no request no gate saw, after a plan that skipped the gates (#1258) ----------


def _release_pr(*, queued: bool = True, held: bool = False) -> fake.HostingService:
    """The release PR on the shared fake, on a base that merges through a
    queue: in the queue at the checked head, or — `held` — held by auto-merge
    until it may enter."""
    host = fake.HostingService(
        number=42,
        title="chore(release): v1.141.0",
        head_ref="release/v1.141.0",
    )
    host.set_base(fake.Base(queue=True))
    if held:
        host.auto_merge = True
    elif queued:
        host.enter_queue()
        host.entry = (1, "MERGEABLE")
    return host


def _switch_the_queue_off(host: fake.HostingService) -> None:
    host.set_base(fake.Base())
    host.in_queue, host.entry = False, None


@pytest.mark.parametrize(
    ("held", "leaves", "force"),
    [
        (False, lambda host: host.drop(), True),
        (True, lambda host: setattr(host, "auto_merge", False), False),
        (False, _switch_the_queue_off, False),
    ],
    ids=["dropped-with-force", "auto-merge-switched-off", "queue-switched-off"],
)
def test_a_pr_that_left_the_queue_after_a_gateless_plan_gets_no_request(
    monkeypatch: pytest.MonkeyPatch,
    held: bool,
    leaves: Callable[[fake.HostingService], None],
    force: bool,
) -> None:
    """The plan finds the PR queued at the checked head and skips the gates;
    it leaves the queue before the landing reads it. The landing allows no
    request, so nothing is merged or enqueued that no gate of this run saw:
    exit 1, saying so, and that a re-run plans afresh and gates."""
    host = _release_pr(held=held)
    host.after(fake.READ, leaves)
    seen = _fake_run(monkeypatch)
    with pytest.raises(click.ClickException) as exc:
        _land(monkeypatch, host, force=force)
    assert exc.value.exit_code == 1
    assert not isinstance(exc.value, release.ReleaseNotMerged)
    message = exc.value.message
    assert message.startswith(
        "release PR #42 left the merge queue for main between this run's plan and its landing"
    )
    assert "the landing sent nothing" in message
    assert "Run `pkit release merge 42` again: it plans afresh, and runs its gates" in message
    assert not {fake.MERGE, fake.MERGE_ADMIN, fake.ENQUEUE} & set(host.kinds())
    assert seen == []


def test_a_pr_still_queued_at_the_landing_is_waited_for_as_before(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _release_pr()
    host.progress = [fake.at(1, "MERGEABLE"), fake.lands()]
    _fake_run(monkeypatch)
    report = _land(monkeypatch, host)
    assert report.exit_code == 0
    assert not {fake.MERGE, fake.MERGE_ADMIN, fake.ENQUEUE} & set(host.kinds())
    assert host.remote_deletion() == "deleted"


def test_a_landing_after_a_gateless_plan_allows_no_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The landing that follows a plan of a wait asks `land` for no request;
    one that follows a gated plan allows them."""
    asked: list[tuple[bool, bool]] = []
    land = release.pull_request_landing.land

    def recording(*args: Any, **kwargs: Any) -> Any:
        asked.append((kwargs["dry_run"], kwargs["options"].no_request))
        return land(*args, **kwargs)

    monkeypatch.setattr(release.pull_request_landing, "land", recording)
    _fake_run(monkeypatch)
    queued = _release_pr()
    queued.progress = [fake.at(1, "MERGEABLE"), fake.lands()]
    _land(monkeypatch, queued)
    assert asked == [(True, False), (False, True)]
    asked.clear()
    _land(monkeypatch, _Host(queue=False))
    assert asked == [(True, False), (False, False)]
