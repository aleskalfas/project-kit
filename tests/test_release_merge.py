"""Tests for the sanctioned release-PR merge path (`pkit release merge`, #475).

The gate is split into pure logic (`summarize_checks`, `parse_release_pr`,
`evaluate_release_pr`) and thin `gh` wrappers (`_gh_pr_view` / `_gh_pr_merge`).
The pure logic is tested directly; `merge_release_pr` is tested with the `gh`
wrappers monkeypatched — no real merge, no network, no hardcoded repo. The
post-merge branch deletion (`_gh_delete_remote_branch` / `_git_cleanup_local`,
#897) is tested with `subprocess.run` stubbed.
"""

from __future__ import annotations

import inspect
import subprocess
from pathlib import Path

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
        {"name": "checks", "status": "COMPLETED", "conclusion": "FAILURE",
         "startedAt": "2026-06-01T16:30:00Z", "completedAt": "2026-06-01T16:34:00Z"},
        {"name": "checks", "status": "COMPLETED", "conclusion": "SUCCESS",
         "startedAt": "2026-06-01T16:35:00Z", "completedAt": "2026-06-01T16:39:00Z"},
    ]
    assert release.summarize_checks(rollup) == (True, ())


def test_summarize_checks_latest_failure_beats_stale_success() -> None:
    # Reverse ordering: an older SUCCESS, a newer FAILURE — the latest run
    # (FAILURE) must block.
    rollup = [
        {"name": "checks", "status": "COMPLETED", "conclusion": "SUCCESS",
         "completedAt": "2026-06-01T16:30:00Z"},
        {"name": "checks", "status": "COMPLETED", "conclusion": "FAILURE",
         "completedAt": "2026-06-01T16:39:00Z"},
    ]
    assert release.summarize_checks(rollup) == (False, ("checks (FAILURE)",))


def test_summarize_checks_single_genuine_failure_still_blocks() -> None:
    rollup = [
        {"name": "checks", "status": "COMPLETED", "conclusion": "FAILURE",
         "completedAt": "2026-06-01T16:39:00Z"},
    ]
    assert release.summarize_checks(rollup) == (False, ("checks (FAILURE)",))


def test_summarize_checks_latest_pending_blocks() -> None:
    # An older green run superseded by a fresh in-progress re-run must block.
    rollup = [
        {"name": "checks", "status": "COMPLETED", "conclusion": "SUCCESS",
         "completedAt": "2026-06-01T16:30:00Z"},
        {"name": "checks", "status": "IN_PROGRESS", "conclusion": "",
         "startedAt": "2026-06-01T16:40:00Z"},
    ]
    assert release.summarize_checks(rollup) == (False, ("checks (IN_PROGRESS)",))


def test_summarize_checks_distinct_checks_dedupe_independently() -> None:
    # Two distinct checks, each with a stale then latest run; each is reduced on
    # its own latest — `lint` ends green, `tests` ends red.
    rollup = [
        {"name": "lint", "status": "COMPLETED", "conclusion": "FAILURE",
         "completedAt": "2026-06-01T16:30:00Z"},
        {"name": "lint", "status": "COMPLETED", "conclusion": "SUCCESS",
         "completedAt": "2026-06-01T16:39:00Z"},
        {"name": "tests", "status": "COMPLETED", "conclusion": "SUCCESS",
         "completedAt": "2026-06-01T16:31:00Z"},
        {"name": "tests", "status": "COMPLETED", "conclusion": "FAILURE",
         "completedAt": "2026-06-01T16:40:00Z"},
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
        "baseRefName": "main",
        "isCrossRepository": False,
        "url": "https://github.com/owner/repo/pull/42",
        "mergeable": "MERGEABLE",
        "statusCheckRollup": [
            {"name": "checks", "status": "COMPLETED", "conclusion": "SUCCESS"}
        ],
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
    decision = release.evaluate_release_pr(
        release.parse_release_pr(_raw(title="feat: something"))
    )
    assert decision.action == "refuse"
    assert "not a release title" in decision.message


def test_evaluate_reports_already_merged() -> None:
    decision = release.evaluate_release_pr(
        release.parse_release_pr(_raw(state="MERGED"))
    )
    assert decision.action == "already-done"
    assert "already merged" in decision.message


def test_evaluate_reports_closed() -> None:
    decision = release.evaluate_release_pr(
        release.parse_release_pr(_raw(state="CLOSED"))
    )
    assert decision.action == "already-done"
    assert "closed" in decision.message


def test_evaluate_refuses_conflicting() -> None:
    decision = release.evaluate_release_pr(
        release.parse_release_pr(_raw(mergeable="CONFLICTING"))
    )
    assert decision.action == "refuse"
    assert "conflict" in decision.message


def test_evaluate_refuses_unknown_mergeability() -> None:
    decision = release.evaluate_release_pr(
        release.parse_release_pr(_raw(mergeable="UNKNOWN"))
    )
    assert decision.action == "refuse"


def test_evaluate_refuses_red_checks() -> None:
    decision = release.evaluate_release_pr(
        release.parse_release_pr(
            _raw(statusCheckRollup=[
                {"name": "tests", "status": "COMPLETED", "conclusion": "FAILURE"}
            ])
        )
    )
    assert decision.action == "refuse"
    assert "tests (FAILURE)" in decision.message


# --- the orchestrator (gh wrappers monkeypatched) --------------------


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


def _merge_green(monkeypatch: pytest.MonkeyPatch, **raw: object) -> str:
    monkeypatch.setattr(release, "_gh_pr_view", lambda n, r: _raw(number=n, **raw))
    monkeypatch.setattr(release, "_gh_pr_merge", lambda *a, **k: None)
    return release.merge_release_pr(Path("/repo"), 42)


def test_merge_release_pr_squash_merges_a_green_pr(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}

    def fake_view(pr_number: int, repo_root: Path) -> dict:
        calls["viewed"] = (pr_number, repo_root)
        return _raw(number=pr_number)

    def fake_merge(pr_number: int, subject: str, repo_root: Path) -> None:
        calls["merged"] = (pr_number, subject, repo_root)

    monkeypatch.setattr(release, "_gh_pr_view", fake_view)
    monkeypatch.setattr(release, "_gh_pr_merge", fake_merge)
    _fake_run(monkeypatch)

    message = release.merge_release_pr(Path("/repo"), 42)

    assert calls["merged"] == (42, "chore(release): v1.141.0", Path("/repo"))
    assert "Merged release PR #42" in message
    assert "post-merge tag step" in message  # tagging stays split


def test_merge_release_pr_dry_run_does_not_merge(monkeypatch: pytest.MonkeyPatch) -> None:
    merged = False

    def fake_merge(*args: object, **kwargs: object) -> None:
        nonlocal merged
        merged = True

    monkeypatch.setattr(release, "_gh_pr_view", lambda n, r: _raw(number=n))
    monkeypatch.setattr(release, "_gh_pr_merge", fake_merge)

    message = release.merge_release_pr(Path("/repo"), 42, dry_run=True)

    assert merged is False
    assert "[dry-run]" in message


def test_merge_release_pr_refuses_non_release(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        release, "_gh_pr_view", lambda n, r: _raw(number=n, headRefName="fix/1-x")
    )
    monkeypatch.setattr(
        release, "_gh_pr_merge",
        lambda *a, **k: pytest.fail("must not merge a non-release PR"),
    )
    with pytest.raises(click.ClickException) as exc:
        release.merge_release_pr(Path("/repo"), 42)
    assert "merge-pr" in str(exc.value)


def test_merge_release_pr_already_merged_reports_clean(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        release, "_gh_pr_view", lambda n, r: _raw(number=n, state="MERGED")
    )
    monkeypatch.setattr(
        release, "_gh_pr_merge",
        lambda *a, **k: pytest.fail("must not re-merge a merged PR"),
    )
    # No exception — an already-merged PR is a clean, idempotent report.
    message = release.merge_release_pr(Path("/repo"), 42)
    assert "already merged" in message


def test_merge_release_pr_refuses_red_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        release, "_gh_pr_view",
        lambda n, r: _raw(
            number=n,
            statusCheckRollup=[
                {"name": "tests", "status": "COMPLETED", "conclusion": "FAILURE"}
            ],
        ),
    )
    monkeypatch.setattr(
        release, "_gh_pr_merge",
        lambda *a, **k: pytest.fail("must not merge a red PR"),
    )
    with pytest.raises(click.ClickException) as exc:
        release.merge_release_pr(Path("/repo"), 42)
    assert "not all green" in str(exc.value)


# --- post-merge branch deletion (#897) -------------------------------


def test_squash_merge_has_no_delete_branch_half(monkeypatch: pytest.MonkeyPatch) -> None:
    """gh's `--delete-branch` also checks out the base locally and fails a
    worktree / detached-HEAD run AFTER the merge lands — so it is not passed."""
    seen = _fake_run(monkeypatch)
    release._gh_pr_merge(42, "chore(release): v1.141.0", Path("/repo"))
    assert seen == [[
        "gh", "pr", "merge", "42", "--squash", "--subject", "chore(release): v1.141.0",
    ]]


def test_merge_deletes_remote_head_via_api_then_cleans_up_locally(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen = _fake_run(monkeypatch)
    message = _merge_green(monkeypatch, baseRefName="develop")
    assert seen == [
        ["gh", "api", "-X", "DELETE",
         "repos/{owner}/{repo}/git/refs/heads/release/v1.141.0"],
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
