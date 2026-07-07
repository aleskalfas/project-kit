"""Tests for the sanctioned release-PR merge path (`pkit release merge`, #475).

The gate is split into pure logic (`summarize_checks`, `parse_release_pr`,
`evaluate_release_pr`) and thin `gh` wrappers (`_gh_pr_view` / `_gh_pr_merge`).
The pure logic is tested directly; `merge_release_pr` is tested with the `gh`
wrappers monkeypatched — no real merge, no network, no hardcoded repo.
"""

from __future__ import annotations

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


def test_merge_release_pr_squash_merges_a_green_pr(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}

    def fake_view(pr_number: int, repo_root: Path) -> dict:
        calls["viewed"] = (pr_number, repo_root)
        return _raw(number=pr_number)

    def fake_merge(pr_number: int, subject: str, repo_root: Path) -> None:
        calls["merged"] = (pr_number, subject, repo_root)

    monkeypatch.setattr(release, "_gh_pr_view", fake_view)
    monkeypatch.setattr(release, "_gh_pr_merge", fake_merge)

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
