"""Tests for project-management's show-pr script's pure logic.

Covers the Conventional Commits parser, closing-issue extraction,
summary builder.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "scripts"
    / "show-pr.py"
)


@pytest.fixture(scope="module")
def sp():
    module_name = "pm_show_pr_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# --- Conventional Commits parser -------------------------------------


def test_parse_cc_with_scope(sp) -> None:
    out = sp._parse_conventional_commits("feat(cli): add new dispatcher")
    assert out["matched"] is True
    assert out["type"] == "feat"
    assert out["scope"] == "cli"
    assert out["summary"] == "add new dispatcher"


def test_parse_cc_without_scope(sp) -> None:
    out = sp._parse_conventional_commits("fix: correct off-by-one")
    assert out["matched"] is True
    assert out["type"] == "fix"
    assert out["scope"] is None
    assert out["summary"] == "correct off-by-one"


def test_parse_cc_returns_unmatched_for_non_cc(sp) -> None:
    out = sp._parse_conventional_commits("Random title")
    assert out["matched"] is False


def test_parse_cc_unmatched_for_capital_type(sp) -> None:
    # CC types are lowercase by convention; capital fails.
    out = sp._parse_conventional_commits("Feat: thing")
    assert out["matched"] is False


# --- closing-issue extraction ---------------------------------------


def test_extract_closes_simple(sp) -> None:
    assert sp._extract_closing_issues("Closes #42") == [42]


def test_extract_multiple(sp) -> None:
    out = sp._extract_closing_issues("Closes #1, fixes #2\nResolves #3")
    assert sorted(out) == [1, 2, 3]


def test_extract_dedupes(sp) -> None:
    assert sp._extract_closing_issues("Closes #1\nFixes #1\nResolves #1") == [1]


def test_extract_empty_for_no_keyword(sp) -> None:
    assert sp._extract_closing_issues("body without keyword") == []


# --- summary builder -------------------------------------------------


def test_summarise_picks_up_fields(sp) -> None:
    pr = {
        "title": "feat(cli): add new dispatcher",
        "body": "Closes #42\n\n## Doc impact\nupdated README.",
        "state": "OPEN",
        "isDraft": False,
        "headRefName": "feat/42-add-dispatcher",
        "baseRefName": "main",
        "mergedAt": None,
        "url": "https://github.com/owner/repo/pull/99",
        "reviewRequests": [{"login": "alice"}, {"login": "bob"}],
    }
    s = sp._summarise(pr)
    assert s["title"] == "feat(cli): add new dispatcher"
    assert s["state"] == "open"
    assert s["is_draft"] is False
    assert s["head"] == "feat/42-add-dispatcher"
    assert s["base"] == "main"
    assert s["conventional_commits"]["type"] == "feat"
    assert s["conventional_commits"]["scope"] == "cli"
    assert s["closes"] == [42]
    assert s["reviewers"] == ["alice", "bob"]
    assert s["has_doc_impact_section"] is True


def test_summarise_handles_missing_optional_fields(sp) -> None:
    pr = {
        "title": "plain title",
        "body": "no closes here",
        "state": "MERGED",
    }
    s = sp._summarise(pr)
    assert s["state"] == "merged"
    assert s["is_draft"] is False
    assert s["closes"] == []
    assert s["reviewers"] == []
    assert s["has_doc_impact_section"] is False


def test_summarise_detects_doc_impact_anywhere_in_body(sp) -> None:
    pr = {
        "title": "feat: x",
        "body": "Closes #1\n\nintro\n\n## Doc impact\n\n- updated foo",
        "state": "OPEN",
    }
    s = sp._summarise(pr)
    assert s["has_doc_impact_section"] is True


# --- --field projection ----------------------------------------------


@pytest.fixture
def sample_summary(sp) -> dict:
    pr = {
        "title": "feat(cli): add new dispatcher",
        "body": "Closes #42\nfixes #43\n\n## Doc impact\nupdated README.",
        "state": "OPEN",
        "isDraft": True,
        "headRefName": "feat/42-add-dispatcher",
        "baseRefName": "main",
        "mergedAt": None,
        "url": "https://github.com/owner/repo/pull/99",
        "reviewRequests": [{"login": "alice"}, {"login": "bob"}],
    }
    return sp._summarise(pr)


def test_field_names_match_resolver_keys(sp, sample_summary) -> None:
    assert tuple(sp._field_lines_for(sample_summary)) == sp.PR_FIELD_NAMES


def test_field_scalar_is_bare_value(sp, sample_summary) -> None:
    fields = sp._field_lines_for(sample_summary)
    # A scalar field renders as exactly one bare line: no banner, no label.
    assert fields["state"] == ["open"]
    assert fields["base"] == ["main"]
    assert fields["cc-type"] == ["feat(cli)"]
    for line in fields["state"]:
        assert "PR #" not in line
        assert "state:" not in line


def test_field_bool_renders_true_false(sp, sample_summary) -> None:
    assert sp._field_lines_for(sample_summary)["draft"] == ["true"]
    assert sp._field_lines_for(sample_summary)["doc-impact"] == ["true"]


def test_field_list_is_one_item_per_line(sp, sample_summary) -> None:
    fields = sp._field_lines_for(sample_summary)
    assert fields["closes"] == ["#42", "#43"]
    assert fields["reviewers"] == ["alice", "bob"]


def test_field_absent_scalar_renders_no_lines(sp) -> None:
    summary = sp._summarise(
        {"title": "plain title", "body": "x", "state": "MERGED"}
    )
    # Non-Conventional-Commits title -> cc-type yields no output.
    assert sp._field_lines_for(summary)["cc-type"] == []


def test_unknown_field_exits_nonzero_and_lists_valid_fields() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "1", "--field", "not-a-field"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert "unknown field" in result.stderr.lower()
    assert "reviewers" in result.stderr
    assert "state" in result.stderr


def test_field_and_json_are_mutually_exclusive() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "1", "--field", "state", "--json"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert "not allowed with" in result.stderr.lower()


# --- review field (DEC-028 verdict read surface, #544) ---------------


def _local_verdict_comment(name, verdict, ts="2026-06-02T00:00:00Z",
                           reasons="because reasons"):
    return {
        "author": {"login": name},
        "body": f"Reviewer agent (local, {name}): {verdict}\n\n{reasons}",
        "createdAt": ts,
    }


def test_review_field_in_valid_fields_list(sp) -> None:
    assert "review" in sp.PR_FIELD_NAMES


def test_review_field_in_json_output(sp) -> None:
    # The summary the --json path serialises carries a `review` key.
    s = sp._summarise({"title": "x", "body": "y", "state": "OPEN"})
    assert "review" in s


def test_review_field_single_verdict_shows_token_and_reasons(sp) -> None:
    s = sp._summarise({
        "title": "feat: x",
        "body": "body",
        "state": "OPEN",
        "comments": [
            _local_verdict_comment("critic", "CHANGES_REQUESTED",
                                   reasons="the abstraction is premature")
        ],
    })
    lines = sp._field_lines_for(s)["review"]
    blob = "\n".join(lines)
    assert "CHANGES_REQUESTED" in blob
    assert "critic" in blob
    assert "the abstraction is premature" in blob


def test_review_field_multi_reviewer_latest_per_reviewer(sp) -> None:
    s = sp._summarise({
        "title": "feat: x",
        "body": "body",
        "state": "OPEN",
        "comments": [
            # critic flips to APPROVED later; the later verdict must win.
            _local_verdict_comment("critic", "CHANGES_REQUESTED",
                                   ts="2026-06-02T00:00:00Z"),
            _local_verdict_comment("critic", "APPROVED",
                                   ts="2026-06-03T00:00:00Z"),
            _local_verdict_comment("architect", "APPROVED"),
        ],
    })
    review = s["review"]
    by_name = {e["reviewer"]: e["verdict"] for e in review}
    assert by_name == {"critic": "APPROVED", "architect": "APPROVED"}
    blob = "\n".join(sp._field_lines_for(s)["review"])
    # Both reviewers surfaced.
    assert "critic" in blob
    assert "architect" in blob


def test_review_field_absent_shows_clear_message(sp) -> None:
    s = sp._summarise({
        "title": "feat: x",
        "body": "body",
        "state": "OPEN",
        "comments": [
            {"author": {"login": "someone"}, "body": "a normal comment",
             "createdAt": "2026-06-02T00:00:00Z"}
        ],
    })
    lines = sp._field_lines_for(s)["review"]
    assert lines == [sp.NO_VERDICT_MESSAGE]


def test_review_field_no_comments_shows_clear_message(sp) -> None:
    s = sp._summarise({"title": "x", "body": "y", "state": "MERGED"})
    assert sp._field_lines_for(s)["review"] == [sp.NO_VERDICT_MESSAGE]


# --- staleness annotation (Fix 3) + read-surface semantics (Fix 2) ------


def _commit(ts):
    return {"committedDate": ts}


def test_review_field_marks_verdict_stale_when_predates_latest_commit(sp) -> None:
    # Verdict at 06-02, latest commit at 06-05 -> verdict is stale; the gate
    # would not count it, so the read surface flags it.
    s = sp._summarise({
        "title": "feat: x",
        "body": "body",
        "state": "OPEN",
        "comments": [
            _local_verdict_comment("critic", "APPROVED",
                                   ts="2026-06-02T00:00:00Z"),
        ],
        "commits": [_commit("2026-06-05T00:00:00Z")],
    })
    assert s["review"][0]["stale"] is True
    blob = "\n".join(sp._field_lines_for(s)["review"])
    assert sp.STALE_MARKER.strip() in blob
    assert "will not count it" in blob


def test_review_field_fresh_verdict_unmarked(sp) -> None:
    # Verdict at 06-06 is strictly after the latest commit at 06-05 -> fresh.
    s = sp._summarise({
        "title": "feat: x",
        "body": "body",
        "state": "OPEN",
        "comments": [
            _local_verdict_comment("critic", "APPROVED",
                                   ts="2026-06-06T00:00:00Z"),
        ],
        "commits": [_commit("2026-06-05T00:00:00Z")],
    })
    assert s["review"][0]["stale"] is False
    blob = "\n".join(sp._field_lines_for(s)["review"])
    assert sp.STALE_MARKER.strip() not in blob


def test_review_field_verdict_at_exact_commit_ts_is_stale(sp) -> None:
    # Freshness is strict (verdict must be AFTER the commit); an equal
    # timestamp is stale, matching the gate's `timestamp <= min_timestamp` drop.
    s = sp._summarise({
        "title": "feat: x",
        "body": "body",
        "state": "OPEN",
        "comments": [
            _local_verdict_comment("critic", "APPROVED",
                                   ts="2026-06-05T00:00:00Z"),
        ],
        "commits": [_commit("2026-06-05T00:00:00Z")],
    })
    assert s["review"][0]["stale"] is True


def test_review_field_no_commits_renders_without_marker(sp) -> None:
    # No resolvable commit timestamp -> nothing is marked stale (render, don't
    # error). The verdict is still shown.
    s = sp._summarise({
        "title": "feat: x",
        "body": "body",
        "state": "OPEN",
        "comments": [
            _local_verdict_comment("critic", "APPROVED",
                                   ts="2026-06-02T00:00:00Z"),
        ],
        # no "commits" key at all
    })
    assert s["review"][0]["stale"] is False
    blob = "\n".join(sp._field_lines_for(s)["review"])
    assert "APPROVED" in blob
    assert sp.STALE_MARKER.strip() not in blob


def test_review_field_commit_without_timestamp_renders_without_marker(sp) -> None:
    # A commit entry with neither committedDate nor authoredDate yields no
    # anchor -> no stale marking rather than an error.
    s = sp._summarise({
        "title": "feat: x",
        "body": "body",
        "state": "OPEN",
        "comments": [
            _local_verdict_comment("critic", "APPROVED",
                                   ts="2026-06-02T00:00:00Z"),
        ],
        "commits": [{"oid": "abc123"}],
    })
    assert s["review"][0]["stale"] is False


def test_latest_commit_timestamp_prefers_committed_then_authored(sp) -> None:
    assert sp._latest_commit_timestamp([]) == ""
    assert sp._latest_commit_timestamp(
        [{"authoredDate": "2026-06-01T00:00:00Z"}]
    ) == "2026-06-01T00:00:00Z"
    assert sp._latest_commit_timestamp([
        {"committedDate": "2026-06-01T00:00:00Z"},
        {"committedDate": "2026-06-05T00:00:00Z",
         "authoredDate": "2026-06-04T00:00:00Z"},
    ]) == "2026-06-05T00:00:00Z"


def test_review_read_surface_is_superset_of_gate_set(sp) -> None:
    # The read surface shows verdicts the gate excludes: a stale one and one
    # from a reviewer the gate's membership filter would drop. Both appear here
    # (show-pr applies no freshness/membership filter) — the corrected
    # semantics: read surface = superset, gate = filtered subset.
    s = sp._summarise({
        "title": "feat: x",
        "body": "body",
        "state": "OPEN",
        "comments": [
            # stale (predates latest commit) — gate drops, read surface shows
            _local_verdict_comment("critic", "APPROVED",
                                   ts="2026-06-02T00:00:00Z"),
            # a reviewer the gate might not require — read surface still shows
            _local_verdict_comment("passer-by", "CHANGES_REQUESTED",
                                   ts="2026-06-06T00:00:00Z"),
        ],
        "commits": [_commit("2026-06-05T00:00:00Z")],
    })
    by_name = {e["reviewer"]: e for e in s["review"]}
    assert set(by_name) == {"critic", "passer-by"}
    assert by_name["critic"]["stale"] is True
    assert by_name["passer-by"]["stale"] is False
