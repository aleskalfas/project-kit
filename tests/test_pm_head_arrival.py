"""Tests for when a pull request's head arrived on the host (#2930).

A verdict that names no reviewed head is fresh only when it was posted after
the PR's head arrived (DEC-028 "Stale-verdict handling"). The arrival is read
from GitHub's record of the head branch's moves (`_lib.head_arrival`), never
from the head commit's own dates: a commit made before a verdict and pushed
after it carries dates from before the verdict.

`gh_run` is injected, so these are pure-logic tests with no live GitHub.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"

HEAD = "b" * 40
OTHER = "c" * 40
BRANCH = "fix/1-a-branch"
VIEW = {
    "headRefOid": HEAD,
    "headRefName": BRANCH,
    "headRepository": {"name": "project", "nameWithOwner": "owner/project"},
    # The commit was made on 06-01 and pushed on 06-05: its dates say nothing
    # of when it arrived.
    "commits": [{"oid": HEAD, "committedDate": "2026-06-01T00:00:00Z"}],
}


@pytest.fixture(scope="module")
def lib():
    """The modules, imported as the pm scripts import them."""
    inserted = str(SCRIPTS_DIR) not in sys.path
    if inserted:
        sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        yield (
            importlib.import_module("_lib.head_arrival"),
            importlib.import_module("_lib.agent_verdicts"),
            importlib.import_module("_lib.verdict_freshness"),
            importlib.import_module("_lib.required_reviewers"),
        )
    finally:
        if inserted:
            sys.path.remove(str(SCRIPTS_DIR))


@pytest.fixture
def ha(lib):
    return lib[0]


def _activity(*entries):
    return json.dumps(
        [
            {"after": after, "timestamp": ts, "activity_type": kind, "ref": f"refs/heads/{BRANCH}"}
            for after, ts, kind in entries
        ]
    )


def _gh(stdout="", returncode=0, stderr="", calls=None):
    def run(args, config, **kwargs):
        if calls is not None:
            calls.append(args)
        return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)

    return run


def test_the_arrival_is_the_branch_s_latest_move_to_the_head(ha) -> None:
    calls: list = []
    gh = _gh(
        _activity(
            (HEAD, "2026-06-05T00:00:00Z", "force_push"),
            (OTHER, "2026-06-03T00:00:00Z", "push"),
            (HEAD, "2026-06-02T00:00:00Z", "push"),
        ),
        calls=calls,
    )
    arrival = ha.read_head_arrival(VIEW, HEAD, {}, gh_run=gh)
    assert arrival == ha.HeadArrival(timestamp="2026-06-05T00:00:00Z")
    assert arrival.ok
    # One call, on the head branch of the repository it lives in.
    assert calls == [
        [
            "gh",
            "api",
            "repos/owner/project/activity?ref=refs%2Fheads%2Ffix%2F1-a-branch&per_page=30",
        ]
    ]


@pytest.mark.parametrize(
    ("view", "head", "why"),
    [
        (VIEW, "", "the pull request's head is unknown"),
        ({**VIEW, "headRefName": ""}, HEAD, "names no head branch"),
        ({**VIEW, "headRepository": None}, HEAD, "names no head branch"),
        ({**VIEW, "headRepository": {"nameWithOwner": "../.."}}, HEAD, "names no head branch"),
    ],
)
def test_an_arrival_without_its_head_or_branch_cannot_be_read(ha, view, head, why) -> None:
    arrival = ha.read_head_arrival(
        view, head, {}, gh_run=lambda *a, **k: pytest.fail("nothing to ask")
    )
    assert not arrival.ok
    assert why in arrival.error


@pytest.mark.parametrize(
    ("gh", "why"),
    [
        (
            _gh(returncode=1, stderr="HTTP 404: Not Found"),
            "gh api repos/owner/project/activity failed: HTTP 404: Not Found",
        ),
        (_gh("not json"), "does not read as a list"),
        (_gh('{"message": "Moved"}'), "does not read as a list"),
        (_gh(_activity((OTHER, "2026-06-05T00:00:00Z", "push"))), "records no move to bbbbbbb"),
        (_gh(_activity((HEAD, "2026-06-05", "push"))), "records no move to bbbbbbb"),
        (_gh("[]"), "records no move to bbbbbbb"),
    ],
)
def test_an_arrival_the_host_does_not_answer_cannot_be_read(ha, gh, why) -> None:
    arrival = ha.read_head_arrival(VIEW, HEAD, {}, gh_run=gh)
    assert not arrival.ok
    assert arrival.timestamp == ""
    assert why in arrival.error


def test_gh_that_cannot_run_reads_no_arrival(ha) -> None:
    def missing(*args, **kwargs):
        raise FileNotFoundError("gh")

    arrival = ha.read_head_arrival(VIEW, HEAD, {}, gh_run=missing)
    assert not arrival.ok
    assert "`gh` could not be run" in arrival.error


# ---- the freshness rule reads the arrival ----------------------------------


def _verdict(av, timestamp):
    return av.Verdict(
        reviewer="pm-reviewer", token=av.APPROVED, path=av.PATH_LOCAL, body="", timestamp=timestamp
    )


def _rule(lib, gh):
    ha, _av, vf, rr = lib
    return vf.rule_for_pr(
        VIEW,
        rr.Resolution(),
        author_delta=lambda *a, **k: pytest.fail("no head is named"),
        base_kept=lambda *a, **k: pytest.fail("no base is named"),
        head_arrival=lambda view, head: ha.read_head_arrival(view, head, {}, gh_run=gh),
    )


def test_a_commit_dated_before_a_verdict_and_pushed_after_it_holds_the_verdict_stale(
    lib,
) -> None:
    """The commit was made on 06-01, the verdict posted on 06-03, the commit
    pushed on 06-05: the verdict never saw it."""
    av = lib[1]
    rule = _rule(lib, _gh(_activity((HEAD, "2026-06-05T00:00:00Z", "push"))))
    assessed = rule.assess(_verdict(av, "2026-06-03T00:00:00Z"))
    assert assessed == lib[2].Freshness(
        False,
        "no reviewed head recorded; posted before the head bbbbbbb arrived at 2026-06-05T00:00:00Z",
    )


def test_a_verdict_posted_after_the_head_arrived_is_fresh(lib) -> None:
    av = lib[1]
    rule = _rule(lib, _gh(_activity((HEAD, "2026-06-05T00:00:00Z", "push"))))
    assert rule.assess(_verdict(av, "2026-06-06T00:00:00Z")) == lib[2].Freshness(
        True, "no reviewed head recorded; posted after the head bbbbbbb arrived"
    )
    # Posted the same second the head arrived: not after it.
    assert not rule.is_fresh(_verdict(av, "2026-06-05T00:00:00Z"))


def test_an_arrival_that_cannot_be_read_holds_the_verdict_stale_with_why(lib) -> None:
    av = lib[1]
    rule = _rule(lib, _gh(returncode=1, stderr="HTTP 403: Forbidden"))
    assessed = rule.assess(_verdict(av, "2026-06-06T00:00:00Z"))
    assert assessed == lib[2].Freshness(
        False,
        "no reviewed head recorded; when the head bbbbbbb arrived cannot be read: "
        "gh api repos/owner/project/activity failed: HTTP 403: Forbidden",
    )


def test_the_arrival_is_asked_once_and_only_for_a_verdict_naming_no_head(lib) -> None:
    av = lib[1]
    calls: list = []
    gh = _gh(_activity((HEAD, "2026-06-05T00:00:00Z", "push")), calls=calls)
    rule = _rule(lib, gh)
    named = av.Verdict(
        reviewer="pm-reviewer",
        token=av.APPROVED,
        path=av.PATH_LOCAL,
        body="",
        timestamp="2026-06-01T00:00:00Z",
        sha=HEAD,
    )
    assert rule.is_fresh(named)
    assert calls == []
    rule.is_fresh(_verdict(av, "2026-06-06T00:00:00Z"))
    rule.is_fresh(_verdict(av, "2026-06-07T00:00:00Z"))
    assert len(calls) == 1
