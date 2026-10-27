"""The state-issue seam (DEC-058, ADR-071), against a GitHub held in memory.

`_lib/state_issues` does every read and write of a state issue. These tests pin
the marker and its one reader, the read by number and by marker, who may write,
the fold where the first claim on a free state holds, each write and its frame,
the rewrite of the description's region, and the guard ADR-071 point 1 sets: a
construction test of the seam's writes and a scan of the scripts. Every `gh`
call is a fake; no test reaches GitHub.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import TypeVar

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
TESTS = Path(__file__).resolve().parent
for path in (SCRIPTS, TESTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from _lib import audit_log, issue_list, provenance  # noqa: E402
from _lib import state_issues as si  # noqa: E402

from pm_state_issue_fakes import FakeRepo  # noqa: E402

VERSIONS = provenance.Versions(tree="1.2.3", capability="0.9.0", cli="1.2.3")
ME = si.Clone(account="me", key="key-me", place="laptop:/work/repo")
OTHER = si.Clone(account="me", key="key-other", place="sandbox-2:/repo")
BOB = si.Clone(account="bob", key="key-bob", place="bob-box:/repo")

T = TypeVar("T")


def _some(value: T | None) -> T:
    """``value``, which the test expects the seam to have returned."""
    assert value is not None
    return value


def _holder(read: si.StateRead) -> si.Holder:
    """The holder of the state a read folded, which the test expects there."""
    return _some(_some(read.fold).holder)


def _run(repo: FakeRepo, writers: si.Writers | None = None) -> si.StateRun:
    return si.StateRun(repo, writers or si.Writers.closed(["me", "bob"]), VERSIONS)


def _state_issue(repo: FakeRepo, number: int = 5, key: str = "planner", author: str = "me"):
    """A finished state issue for the seat ``key``: its description and its
    marker's comment."""
    repo.add(number, si.description("seat", key, si.Fold(None), VERSIONS), title=f"Seat {key}")
    repo.post(number, si.marker_comment("seat", key, VERSIONS), author=author)
    return repo.issues[number]


def _event(repo: FakeRepo, number: int, type_name: str, clone: si.Clone, **extra) -> None:
    ev = audit_log.event(type_name, key="planner", clone=clone.key, place=clone.place, **extra)
    repo.post(number, audit_log.build(ev, versions=VERSIONS), author=clone.account)


# ---- the marker -------------------------------------------------------------------


def test_the_marker_round_trips_whatever_the_key_holds() -> None:
    for key in ("planner", "Planner", "two words", "a-->b", "x--y", "50%"):
        marker = _some(si.read_marker(si.marker_line("seat", key)))
        assert marker == si.Marker("seat", key, si.MARKER_VERSION)
        assert marker.names("seat", key)
    planner = _some(si.read_marker(si.marker_line("seat", "planner")))
    assert not planner.names("seat", "Planner")
    assert not planner.names("lock", "planner")


def test_the_marker_takes_the_form_the_one_read_of_issues_looks_for() -> None:
    """#2139 tells a state issue by a line `<!-- pkit:state-issue ... -->` whose
    attributes hold no space and no `>`. The marker keeps that form."""
    placeholder = re.compile(r"<!--\s*pkit:state-issue(?:\s+[^\s>]+)*\s*-->")
    for key in ("planner", "two words", "a > b"):
        assert placeholder.fullmatch(si.marker_line("seat", key))


def test_a_quoted_marker_marks_nothing_and_any_version_marks_a_state_issue() -> None:
    line = si.marker_line("seat", "planner")
    assert si.read_marker(f"```\n{line}\n```") is None
    assert si.read_marker(f"we write {line} in a sentence") is None
    later = si.read_marker("<!-- pkit:state-issue v=2 kind=seat key=planner -->")
    assert later is not None and not later.names("seat", "planner")
    assert si.is_state_issue("<!-- pkit:state-issue v=1 key=planner -->")
    assert not si.is_state_issue("## What\n\nA task.\n")


def test_the_seam_agrees_with_its_schema() -> None:
    """`state-issues.yaml` holds the marker's form, the region, the event types
    and the kinds of state; the seam holds to it."""
    from ruamel.yaml import YAML

    schema = YAML(typ="safe").load(
        (SCRIPTS.parent / "schemas" / "state-issues.yaml").read_text(encoding="utf-8")
    )
    assert schema["marker"]["prefix"] == si.MARKER_PREFIX
    assert schema["marker"]["version"] == si.MARKER_VERSION
    assert si.marker_line("seat", "k").startswith(
        f"<!-- {si.MARKER_PREFIX} v={si.MARKER_VERSION} kind=seat key="
    )
    assert (schema["view"]["begin"], schema["view"]["end"]) == (si.VIEW_BEGIN, si.VIEW_END)
    assert [e.strip("[]").split(":", 1)[1] for e in schema["events"]] == list(si.EVENTS)
    assert set(si.EVENTS) == set(audit_log.STATE_EVENTS)
    assert "seat" in schema["kinds"]


@pytest.mark.parametrize("version", ["²", "٣", "9" * 5000])
def test_no_version_a_hand_writes_makes_the_marker_reader_fail(version: str) -> None:
    marker = si.read_marker(f"<!-- pkit:state-issue v={version} kind=seat key=planner -->")
    assert marker is not None and marker.version == 0


def test_a_key_cannot_put_a_line_ahead_of_the_marker() -> None:
    planted = si.marker_line("seat", "other")
    comment = si.marker_comment("seat", f"planner\n{planted}", VERSIONS)
    assert _some(si.read_marker(comment)).key == f"planner\n{planted}"


def test_a_comment_from_anyone_cannot_break_a_read() -> None:
    repo = FakeRepo()
    _state_issue(repo)
    repo.post(5, "<!-- pkit:audit v=² event=state-claim key=planner -->", author="mallory")
    repo.post(5, "<!-- pkit:state-issue v=² kind=seat key=planner -->", author="mallory")
    _event(repo, 5, si.CLAIM, ME)
    read = si.read(5, "seat", "planner", _run(repo))
    assert read.outcome == si.READ and _holder(read).clone == "key-me"


def test_a_marker_refuses_a_kind_it_cannot_carry_or_an_empty_key() -> None:
    with pytest.raises(ValueError):
        si.marker_line("Seat Kind", "planner")
    with pytest.raises(ValueError):
        si.marker_line("seat", "")


# ---- the fold ---------------------------------------------------------------------


def _ev(type_name: str, author: str, clone: str, n: int) -> si.StateEvent:
    return si.StateEvent(comment_id=n, author=author, type=type_name, clone=clone, place="p")


def test_the_first_claim_on_a_free_state_holds_and_a_later_one_is_void() -> None:
    folded = si.fold([_ev(si.CLAIM, "me", "a", 1), _ev(si.CLAIM, "me", "b", 2)])
    assert folded.holder == si.Holder("me", "a", "p")
    assert [e.void for e in folded.events] == [False, True]


def test_a_void_claim_stays_void_after_the_holder_releases() -> None:
    folded = si.fold(
        [_ev(si.CLAIM, "me", "a", 1), _ev(si.CLAIM, "me", "b", 2), _ev(si.RELEASE, "me", "a", 3)]
    )
    assert folded.free


def test_the_holders_claim_again_changes_nothing() -> None:
    folded = si.fold([_ev(si.CLAIM, "me", "a", 1), _ev(si.CLAIM, "me", "a", 2)])
    assert folded.holder == si.Holder("me", "a", "p")
    assert not any(e.void for e in folded.events)


def test_a_release_frees_only_from_the_holders_account_and_key() -> None:
    held = [_ev(si.CLAIM, "me", "a", 1)]
    assert si.fold([*held, _ev(si.RELEASE, "me", "b", 2)]).holder is not None
    assert si.fold([*held, _ev(si.RELEASE, "bob", "a", 2)]).holder is not None
    assert si.fold([*held, _ev(si.RELEASE, "me", "a", 2)]).free


def test_a_release_by_force_frees_whoever_holds_and_the_next_claim_holds() -> None:
    folded = si.fold(
        [
            _ev(si.CLAIM, "me", "a", 1),
            _ev(si.FORCE_RELEASE, "bob", "z", 2),
            _ev(si.CLAIM, "me", "b", 3),
        ]
    )
    assert folded.holder == si.Holder("me", "b", "p")
    assert si.fold([_ev(si.FORCE_RELEASE, "bob", "z", 1)]).events[0].void


def test_the_fold_names_the_comment_of_the_holders_take() -> None:
    """The take is the claim that made the holder hold the state: the holder's
    claim again moves it not, and the same clone's claim after a release by
    force is a take of its own (#2182)."""
    assert si.fold([]).take is None
    held = [_ev(si.CLAIM, "me", "a", 1), _ev(si.CLAIM, "me", "a", 2), _ev(si.CLAIM, "me", "b", 3)]
    assert si.fold(held).take == 1
    again = [*held, _ev(si.FORCE_RELEASE, "bob", "z", 4), _ev(si.CLAIM, "me", "a", 5)]
    assert si.fold(again).holder == si.Holder("me", "a", "p")
    assert si.fold(again).take == 5
    assert si.fold([*held, _ev(si.RELEASE, "me", "a", 4)]).take is None


# ---- create and finish --------------------------------------------------------------


def test_create_makes_the_issue_then_its_marker_comment_then_the_filing_comment() -> None:
    repo = FakeRepo()
    out = si.create("seat", "planner", "Seat planner", _run(repo))
    assert out.outcome == si.CREATED
    number = _some(out.number)
    issue = repo.issues[number]
    assert _some(si.read_marker(issue.body)).names("seat", "planner")
    assert si.VIEW_BEGIN in issue.body and "**Free.**" in issue.body
    assert provenance.MARKER_START in issue.body
    first, second = repo.bodies(number)
    assert _some(si.read_marker(first)).names("seat", "planner")
    assert "<!-- pkit-state-marker -->" in first
    assert first.startswith("📌 state-marker — this issue holds the seat `planner`")
    assert provenance.FILING_MARKER in second
    # No type, parent, label, assignee or milestone.
    assert not {"--label", "--assignee", "--milestone", "--type"} & set(issue.args)


def test_create_locks_the_conversation_to_collaborators_before_its_first_comment() -> None:
    """A new state issue is locked before any read or comment, so GitHub lets
    fewer accounts comment on it (#2149). The seam still judges every author."""
    repo = FakeRepo()
    out = si.create("seat", "planner", "Seat planner", _run(repo))
    number = _some(out.number)
    assert out.outcome == si.CREATED and out.cause is None
    assert repo.issues[number].locked
    verbs = [argv[2] for argv in repo.writes()]
    assert verbs == ["create", "lock", "comment", "comment"]
    assert repo.calls[1] == si.lock_args(number)  # right after the create


def test_a_lock_that_fails_is_said_and_the_creation_goes_on() -> None:
    """The lock narrows who can comment, and is no security boundary (DEC-058
    point 5), so a failed lock stops nothing."""
    repo = FakeRepo(failing={"lock"})
    out = si.create("seat", "planner", "Seat planner", _run(repo))
    number = _some(out.number)
    assert out.outcome == si.CREATED and "the lock failed" in (out.cause or "")
    assert f"lock #{number} on GitHub" in (out.cause or "")
    assert not repo.issues[number].locked
    assert si.read(number, "seat", "planner", _run(repo)).outcome == si.READ


def test_a_creation_left_half_done_is_finished_by_running_it_again() -> None:
    repo = FakeRepo()
    repo.add(9, si.description("seat", "planner", si.Fold(None), VERSIONS))
    assert si.read(9, "seat", "planner", _run(repo)).outcome == si.NO_STATE_ISSUE
    out = si.finish(9, "seat", "planner", _run(repo))
    assert out.outcome == si.FINISHED
    assert repo.issues[9].locked
    assert si.read(9, "seat", "planner", _run(repo)).outcome == si.READ
    writes = len(repo.writes())
    assert si.finish(9, "seat", "planner", _run(repo)).outcome == si.FINISHED
    assert len(repo.bodies(9)) == 2  # the second run posts nothing
    assert len(repo.writes()) == writes  # and locks nothing again


@pytest.mark.parametrize(
    ("opener", "writers"),
    [
        ("mallory", si.Writers.closed(["me", "bob"])),
        ("reader", si.Writers.open()),
        ("", si.Writers.open()),
    ],
    ids=["no-member", "read-access", "account-gone"],
)
def test_finish_adopts_no_issue_an_author_who_may_not_write_opened(
    opener: str, writers: si.Writers
) -> None:
    """An issue whose description carries the marker, opened by an account that
    may not write, is taken for no state issue, and nothing is written to it
    (#2149)."""
    repo = FakeRepo(access={"me": "write", "reader": "read"})
    repo.add(9, si.description("seat", "planner", si.Fold(None), VERSIONS), opener=opener)
    out = si.finish(9, "seat", "planner", _run(repo, writers))
    assert out.outcome == si.NO_STATE_ISSUE
    assert "may not write" in (out.cause or "")
    assert repo.writes() == [] and not repo.issues[9].locked


def test_finish_adopts_a_half_done_issue_a_writer_opened_with_the_gate_open() -> None:
    repo = FakeRepo(access={"me": "write", "bob": "maintain"})
    repo.add(9, si.description("seat", "planner", si.Fold(None), VERSIONS), opener="bob")
    out = si.finish(9, "seat", "planner", _run(repo, si.Writers.open()))
    assert out.outcome == si.FINISHED and repo.issues[9].locked


@pytest.mark.parametrize(
    ("failing", "outcome", "said"),
    [("issue", si.FAILED, "502"), ("access", si.INCOMPLETE, "403")],
)
def test_finish_that_cannot_tell_who_opened_the_issue_writes_nothing(
    failing: str, outcome: str, said: str
) -> None:
    repo = FakeRepo(access={"me": "write"}, failing={failing})
    repo.add(9, si.description("seat", "planner", si.Fold(None), VERSIONS))
    out = si.finish(9, "seat", "planner", _run(repo, si.Writers.open()))
    assert out.outcome == outcome and said in (out.cause or "")
    assert repo.writes() == []


def test_finish_locks_nothing_on_an_issue_that_holds_another_state() -> None:
    repo = FakeRepo()
    _state_issue(repo, number=9, key="worker")
    out = si.finish(9, "seat", "planner", _run(repo))
    assert out.outcome == si.NO_STATE_ISSUE
    assert repo.writes() == [] and not repo.issues[9].locked


def test_a_failed_create_says_so() -> None:
    repo = FakeRepo(failing={"create"})
    out = si.create("seat", "planner", "Seat planner", _run(repo))
    assert out.outcome == si.FAILED and "502" in (out.cause or "")


# ---- reads ----------------------------------------------------------------------------


def test_a_read_accepts_the_earliest_marker_comment_from_an_author_who_may_write() -> None:
    repo = FakeRepo()
    repo.add(5, si.description("seat", "planner", si.Fold(None), VERSIONS))
    repo.post(5, si.marker_comment("seat", "worker", VERSIONS), author="mallory")
    repo.post(5, si.marker_comment("seat", "planner", VERSIONS), author="me")
    read = si.read(5, "seat", "planner", _run(repo))
    assert read.outcome == si.READ and _some(read.fold).free


def test_a_read_refuses_an_issue_whose_first_writers_marker_names_another_key() -> None:
    repo = FakeRepo()
    _state_issue(repo, key="worker")
    repo.post(5, si.marker_comment("seat", "planner", VERSIONS), author="me")
    read = si.read(5, "seat", "planner", _run(repo))
    assert read.outcome == si.NO_STATE_ISSUE


def test_only_the_comments_of_an_author_who_may_write_count() -> None:
    repo = FakeRepo()
    _state_issue(repo)
    _event(repo, 5, si.CLAIM, si.Clone("mallory", "k-m", "x"))
    _event(repo, 5, si.CLAIM, ME)
    read = si.read(5, "seat", "planner", _run(repo))
    assert _holder(read) == si.Holder("me", "key-me", ME.place)
    assert [e.author for e in _some(read.fold).events] == ["me"]
    # The take is the id GitHub gave the counted claim's comment (#2182).
    assert _some(read.fold).take == repo.issues[5].comments[-1]["id"]


def test_with_the_gate_open_each_author_is_asked_about_once_in_a_run() -> None:
    repo = FakeRepo(access={"me": "write", "bob": "admin", "reader": "read"})
    _state_issue(repo)
    _event(repo, 5, si.CLAIM, si.Clone("reader", "k-r", "x"))
    _event(repo, 5, si.CLAIM, ME)
    _event(repo, 5, si.RELEASE, ME)
    _event(repo, 5, si.CLAIM, BOB)
    run = _run(repo, si.Writers.open())
    read = si.read(5, "seat", "planner", run)
    assert _holder(read) == si.Holder("bob", "key-bob", BOB.place)
    si.read(5, "seat", "planner", run)
    asked = [argv[2] for argv in repo.calls if "/collaborators/" in argv[-1]]
    assert sorted(asked) == sorted(set(asked))  # each author once, in both reads
    assert len(asked) == 3


def test_an_author_github_does_not_know_counts_as_one_who_may_not_write() -> None:
    repo = FakeRepo(access={"me": "write"})
    _state_issue(repo)
    _event(repo, 5, si.CLAIM, si.Clone("gone", "k-g", "x"))
    ghost = audit_log.event(si.CLAIM, key="planner", clone="k", place="p")
    repo.post(5, audit_log.build(ghost), author="")
    _event(repo, 5, si.CLAIM, ME)
    read = si.read(5, "seat", "planner", _run(repo, si.Writers.open()))
    assert read.outcome == si.READ
    assert _holder(read).clone == "key-me"


def test_a_failed_access_call_makes_the_read_incomplete_and_drops_nothing() -> None:
    repo = FakeRepo(access={"me": "write"}, failing={"access"})
    _state_issue(repo)
    read = si.read(5, "seat", "planner", _run(repo, si.Writers.open()))
    assert read.outcome == si.INCOMPLETE and "403" in (read.cause or "")


def test_a_log_read_in_part_makes_the_read_incomplete(monkeypatch) -> None:
    from _lib import comment_log

    monkeypatch.setattr(comment_log, "PAGE_SIZE", 1)
    repo = FakeRepo()
    _state_issue(repo)
    _event(repo, 5, si.CLAIM, ME)
    repo.failing.add("page")
    read = si.read(5, "seat", "planner", _run(repo))
    assert read.outcome == si.INCOMPLETE


def test_a_long_log_is_read_whole(monkeypatch) -> None:
    from _lib import comment_log

    monkeypatch.setattr(comment_log, "PAGE_SIZE", 2)
    repo = FakeRepo()
    _state_issue(repo)
    for _ in range(3):
        _event(repo, 5, si.CLAIM, ME)
        _event(repo, 5, si.RELEASE, ME)
    _event(repo, 5, si.CLAIM, BOB)
    assert _holder(si.read(5, "seat", "planner", _run(repo))).account == "bob"


def test_a_read_restores_a_marker_a_hand_removed_from_the_description() -> None:
    repo = FakeRepo()
    issue = _state_issue(repo)
    _event(repo, 5, si.CLAIM, ME)
    issue.body = "Someone tidied this description."
    read = si.read(5, "seat", "planner", _run(repo))
    assert read.outcome == si.READ and read.restored == si.WROTE
    assert _some(si.read_marker(issue.body)).names("seat", "planner")
    assert "key-me" in issue.body
    assert si.read(5, "seat", "planner", _run(repo)).restored is None


def test_a_read_writes_nothing_where_the_marker_stands() -> None:
    repo = FakeRepo()
    _state_issue(repo)
    si.read(5, "seat", "planner", _run(repo))
    assert repo.writes() == []


def test_find_takes_the_issue_github_numbered_first_and_names_the_rest() -> None:
    repo = FakeRepo()
    _state_issue(repo, number=12)
    _state_issue(repo, number=8)
    repo.add(10, si.description("seat", "planner", si.Fold(None), VERSIONS))  # half done
    repo.add(3, "## What\n\nA task.\n")
    rows = [{"number": n, "body": i.body} for n, i in repo.issues.items()]
    found = si.find("seat", "planner", rows, _run(repo))
    assert found.outcome == si.READ and _some(found.read).number == 8
    assert found.duplicates == (12,)
    assert found.half_done == (10,)


def test_find_finds_nothing_where_no_description_names_the_key() -> None:
    repo = FakeRepo()
    _state_issue(repo, key="worker")
    rows = [{"number": 5, "body": repo.issues[5].body}]
    assert si.find("seat", "planner", rows, _run(repo)).outcome == si.NO_STATE_ISSUE


def test_find_takes_the_state_issues_the_one_read_of_issues_left_out() -> None:
    """The seam finds a state issue by its marker through the one read of
    issues, never GitHub's search (ADR-071 point 2)."""
    repo = FakeRepo()
    _state_issue(repo, number=8)
    repo.add(3, "## What\n\nA task.\n")

    def listing(argv, config, **kwargs):
        rows = [{"number": n, "body": i.body} for n, i in repo.issues.items()]
        return subprocess.CompletedProcess(argv, 0, json.dumps(rows), "")

    listed = issue_list.list_issues({}, ["--state", "open"], fields="number", gh_call=listing)
    assert listed.rows == ({"number": 3},)
    found = si.find("seat", "planner", listed.state_rows, _run(repo))
    assert found.outcome == si.READ and _some(found.read).number == 8


def test_the_seam_asks_the_one_read_of_issues_for_the_open_state_issues() -> None:
    """`list_open` lists the open issues through the one read of issues, and
    keeps the state issues it left out (ADR-071 point 2)."""
    repo = FakeRepo()
    _state_issue(repo, number=8)
    _state_issue(repo, number=9, key="worker")
    repo.issues[9].state = "CLOSED"
    repo.add(3, "## What\n\nA task.\n")
    listed = si.list_open(_run(repo))
    assert [row["number"] for row in _some(listed.rows)] == [8] and not listed.cut
    (argv,) = [a for a in repo.calls if a[1:3] == ["issue", "list"]]
    assert argv[argv.index("--state") + 1] == "open" and "--search" not in argv
    found = si.find("seat", "planner", _some(listed.rows), _run(repo))
    assert found.outcome == si.READ and _some(found.read).number == 8


def test_a_listing_of_state_issues_says_when_it_failed_or_reached_its_limit() -> None:
    repo = FakeRepo(failing={"list"})
    failed = si.list_open(_run(repo))
    assert failed.rows is None and "502" in (failed.cause or "")
    repo = FakeRepo()
    _state_issue(repo, number=8)
    repo.add(3, "## What\n\nA task.\n")
    assert si.list_open(_run(repo), limit=2).cut
    assert not si.list_open(_run(repo), limit=3).cut


# ---- claim, release, release by force -----------------------------------------------


def test_a_claim_on_a_free_state_holds_and_the_region_shows_it() -> None:
    repo = FakeRepo()
    issue = _state_issue(repo)
    out = si.claim(5, "seat", "planner", ME, _run(repo))
    assert out.outcome == si.CLAIMED and _some(out.holder).is_clone("me", "key-me")
    assert out.view == si.WROTE
    assert "**Held** by the account `me`, clone `key-me`" in issue.body
    claim = _some(audit_log.parse(repo.bodies(5)[-1]))
    assert (claim.type, claim.get("key"), claim.get("clone"), claim.get("place")) == (
        si.CLAIM,
        "planner",
        "key-me",
        ME.place,
    )


def test_a_claim_on_a_held_state_writes_nothing() -> None:
    repo = FakeRepo()
    _state_issue(repo)
    _event(repo, 5, si.CLAIM, ME)
    run = _run(repo)
    assert si.claim(5, "seat", "planner", ME, run).outcome == si.HELD
    assert si.claim(5, "seat", "planner", OTHER, run).outcome == si.HELD_ELSEWHERE
    assert repo.writes() == []


def test_a_claim_that_another_clone_beat_loses_and_writes_nothing_more() -> None:
    repo = FakeRepo()
    _state_issue(repo)
    repo.before_post = lambda n: (
        _event(repo, n, si.CLAIM, OTHER) if len(repo.bodies(n)) == 1 else None
    )
    out = si.claim(5, "seat", "planner", ME, _run(repo))
    assert out.outcome == si.LOST and _some(out.holder).is_clone("me", "key-other")
    comments = [c for c in repo.writes() if c[2] == "comment"]
    assert len(comments) == 1  # the claim, and no release of the lost claim


def test_a_claim_whose_post_failed_but_landed_counts() -> None:
    repo = FakeRepo(failing={"comment-landed"})
    _state_issue(repo)
    out = si.claim(5, "seat", "planner", ME, _run(repo))
    assert out.outcome == si.CLAIMED


def test_a_claim_whose_post_failed_and_did_not_land_fails() -> None:
    repo = FakeRepo(failing={"comment"})
    _state_issue(repo)
    out = si.claim(5, "seat", "planner", ME, _run(repo))
    assert out.outcome == si.FAILED


def test_a_retry_reads_the_log_first_and_posts_nothing_where_the_act_landed() -> None:
    repo = FakeRepo()
    _state_issue(repo)
    ev = audit_log.event(si.CLAIM, key="planner", clone=ME.key, place=ME.place)
    run = _run(repo)
    assert si.post_event(5, ev, run).outcome == si.WROTE
    assert si.post_event(5, ev, run, after_failure=True).outcome == si.ALREADY
    assert len(repo.bodies(5)) == 2


def test_a_write_to_a_closed_state_issue_reopens_it_first() -> None:
    repo = FakeRepo()
    issue = _state_issue(repo)
    issue.state = "CLOSED"
    out = si.claim(5, "seat", "planner", ME, _run(repo))
    assert out.outcome == si.CLAIMED and issue.state == "OPEN"
    verbs = [argv[2] for argv in repo.writes()]
    assert verbs.index("reopen") < verbs.index("comment")


def test_a_release_frees_the_state_its_clone_holds() -> None:
    repo = FakeRepo()
    issue = _state_issue(repo)
    run = _run(repo)
    si.claim(5, "seat", "planner", ME, run)
    out = si.release(5, "seat", "planner", ME, run)
    assert out.outcome == si.RELEASED and out.holder is None
    assert _some(out.freed).is_clone("me", "key-me")
    assert "**Free.**" in issue.body


def test_a_release_by_another_clone_or_of_a_free_state_writes_nothing() -> None:
    repo = FakeRepo()
    _state_issue(repo)
    run = _run(repo)
    assert si.release(5, "seat", "planner", ME, run).outcome == si.NOTHING
    _event(repo, 5, si.CLAIM, ME)
    out = si.release(5, "seat", "planner", OTHER, run)
    assert out.outcome == si.NOT_HOLDER and _some(out.holder).is_clone("me", "key-me")
    assert repo.writes() == []


def test_a_release_by_force_frees_the_holder_and_carries_its_reason() -> None:
    repo = FakeRepo()
    _state_issue(repo)
    _event(repo, 5, si.CLAIM, ME)
    out = si.force_release(5, "seat", "planner", BOB, "the sandbox was deleted", _run(repo))
    assert out.outcome == si.RELEASED and _some(out.freed).is_clone("me", "key-me")
    assert out.holder is None
    ev = _some(audit_log.parse(repo.bodies(5)[-1]))
    assert ev.type == si.FORCE_RELEASE and ev.get("reason") == "the sandbox was deleted"
    with pytest.raises(ValueError):
        si.force_release(5, "seat", "planner", BOB, "  ", _run(repo))


def test_a_release_by_force_of_a_free_state_writes_nothing() -> None:
    repo = FakeRepo()
    _state_issue(repo)
    assert si.force_release(5, "seat", "planner", BOB, "why", _run(repo)).outcome == si.NOTHING
    assert repo.writes() == []


def test_the_rewrite_says_when_it_rebuilt_a_region_a_hand_had_changed() -> None:
    repo = FakeRepo()
    issue = _state_issue(repo)
    issue.body = issue.body.replace("**Free.**", "**Free, I think.**")
    out = si.claim(5, "seat", "planner", ME, _run(repo))
    assert out.view == si.REBUILT
    assert "**Held**" in issue.body


def test_close_closes_the_state_issue() -> None:
    repo = FakeRepo()
    issue = _state_issue(repo)
    assert si.close(5, _run(repo)).outcome == si.WROTE and issue.state == "CLOSED"


# ---- what the seam never reads ---------------------------------------------------------


def test_the_seam_never_searches_and_reads_no_labels_or_board() -> None:
    repo = FakeRepo()
    _state_issue(repo)
    run = _run(repo)
    si.claim(5, "seat", "planner", ME, run)
    si.release(5, "seat", "planner", ME, run)
    for argv in repo.calls:
        joined = " ".join(argv)
        assert "search" not in joined and "project" not in joined
        if argv[1:3] == ["issue", "view"]:
            fields = set(argv[argv.index("--json") + 1].split(","))
            assert fields <= {"number", "state", "body"}


# ---- the guard (ADR-071 point 1) -------------------------------------------------------

_WRITE_SHAPES = {
    "comment": lambda argv: argv[:4] == si.comment_args(int(argv[3]), argv[5])[:4],
    "edit": lambda argv: (
        argv[:4] == si.description_args(int(argv[3]), argv[5])[:4] and argv[4] == "--body-file"
    ),
    "create": lambda argv: argv[:3] == ["gh", "issue", "create"],
    "lock": lambda argv: argv == si.lock_args(int(argv[3])),
    "reopen": lambda argv: argv == si.reopen_args(int(argv[3])),
    "close": lambda argv: argv == si.close_args(int(argv[3])),
}


def test_construction_every_write_comes_from_the_seams_constructors() -> None:
    """Every write the seam runs takes the shape of one of its constructors, and
    every comment it posts is an event the facility parses, the marker's comment
    or the filing comment."""
    repo = FakeRepo()
    run = _run(repo)
    number = _some(si.create("seat", "planner", "Seat planner", run).number)
    repo.issues[number].state = "CLOSED"
    si.claim(number, "seat", "planner", ME, run)
    si.release(number, "seat", "planner", ME, run)
    si.claim(number, "seat", "planner", OTHER, run)
    si.force_release(number, "seat", "planner", BOB, "stale", run)
    si.close(number, run)
    writes = repo.writes()
    assert {argv[2] for argv in writes} == set(_WRITE_SHAPES)
    for argv in writes:
        assert _WRITE_SHAPES[argv[2]](argv), argv
    for body in repo.bodies(number):
        ev = audit_log.parse(body)
        assert (
            (ev is not None and ev.type in si.EVENTS)
            or si.read_marker(body) is not None
            or provenance.FILING_MARKER in body
        ), body
        assert body.rstrip().endswith("</sub>") or provenance.FILING_MARKER in body


# Each literal names a piece of a state issue that only the seam and the shared
# builder construct: the marker, the event stamp, and the description's region.
_SIGNATURES = ("pkit:state-issue", "pkit:state-view", "pkit:audit ", "pkit:audit\\s")
_BUILDERS = {"_lib/state_issues.py", "_lib/audit_log.py"}


def _scripts() -> list[Path]:
    return [p for p in sorted(SCRIPTS.rglob("*.py")) if "__pycache__" not in p.parts]


@pytest.mark.parametrize("path", _scripts(), ids=lambda p: p.relative_to(SCRIPTS).as_posix())
def test_scan_no_script_builds_a_state_issues_marker_event_or_region(path: Path) -> None:
    """No script outside the seam and the shared builder holds the marker's,
    the event stamp's or the region's signature (ADR-071 point 1)."""
    if path.relative_to(SCRIPTS).as_posix() in _BUILDERS:
        return
    source = path.read_text(encoding="utf-8")
    found = [s for s in _SIGNATURES if s in source]
    assert not found, (
        f"{path.name} holds {found}: build a state issue's marker, event comment or "
        "description only through `_lib/state_issues` and `_lib/audit_log`."
    )


def test_scan_the_builders_do_hold_the_signatures() -> None:
    held = "".join((SCRIPTS / name).read_text(encoding="utf-8") for name in _BUILDERS)
    for signature in ("pkit:state-issue", "pkit:state-view", "pkit:audit"):
        assert signature in held
