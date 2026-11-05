"""The one reader of a comment log, read whole (ADR-041 point 1, ADR-071 point 3).

`_lib/comment_log.read_log` pages an issue's comments to their end, in the
order of their ids. A read that cannot reach the end says so, so no fold reads a
log cut short. Both the ownership seam and the state-issue seam read through it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
TESTS = Path(__file__).resolve().parent
for path in (SCRIPTS, TESTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from _lib import comment_log, instance_ownership  # noqa: E402

from pm_state_issue_fakes import FakeRepo  # noqa: E402


@pytest.fixture
def repo() -> FakeRepo:
    fake = FakeRepo()
    fake.add(7)
    return fake


def test_the_log_is_read_to_its_end_a_page_at_a_time(repo, monkeypatch) -> None:
    monkeypatch.setattr(comment_log, "PAGE_SIZE", 2)
    for n in range(5):
        repo.post(7, f"comment {n}", author=f"user{n}")
    log = comment_log.read_log(7, repo)
    assert log.complete
    assert [c.body for c in log.comments] == [f"comment {n}" for n in range(5)]
    assert [c.author for c in log.comments] == [f"user{n}" for n in range(5)]
    assert len(repo.calls) == 3  # two full pages and the short one that ends it


def test_a_full_last_page_asks_once_more(repo, monkeypatch) -> None:
    monkeypatch.setattr(comment_log, "PAGE_SIZE", 2)
    for n in range(4):
        repo.post(7, f"c{n}")
    assert comment_log.read_log(7, repo).complete
    assert len(repo.calls) == 3


def test_the_comments_come_in_the_order_of_their_ids(repo) -> None:
    second = repo.post(7, "second")
    first = repo.post(7, "first")
    first["id"], second["id"] = 1, 2
    log = comment_log.read_log(7, repo)
    assert [c.body for c in log.comments] == ["first", "second"]


def test_a_failed_page_makes_the_read_incomplete(repo, monkeypatch) -> None:
    monkeypatch.setattr(comment_log, "PAGE_SIZE", 1)
    repo.post(7, "a")
    repo.post(7, "b")
    repo.failing.add("page")
    log = comment_log.read_log(7, repo)
    assert not log.complete
    assert "502" in (log.cause or "")


def test_a_log_longer_than_the_reader_goes_is_incomplete(repo, monkeypatch) -> None:
    monkeypatch.setattr(comment_log, "PAGE_SIZE", 1)
    monkeypatch.setattr(comment_log, "MAX_PAGES", 2)
    for n in range(3):
        repo.post(7, f"c{n}")
    log = comment_log.read_log(7, repo)
    assert not log.complete and "not read in part" in (log.cause or "")


def test_an_entry_with_no_id_makes_the_read_incomplete(repo) -> None:
    repo.post(7, "x")["id"] = "IC_abc"
    assert not comment_log.read_log(7, repo).complete


def test_an_author_github_no_longer_has_reads_as_none(repo) -> None:
    repo.post(7, "x", author="")
    assert comment_log.read_log(7, repo).comments[0].author is None


def test_the_ownership_seam_reads_its_log_through_the_same_reader(repo) -> None:
    body = instance_ownership.format_event_comment(event="claim", instance=2)
    repo.post(7, body, author="alice")
    log = instance_ownership.read_log(7, repo)
    res = instance_ownership.resolve_owner(comments=log.comments, labels=[], assignee_login="alice")
    assert res.owners == frozenset({2})
