"""Tests for the shared DEC-028 verdict parser (`_lib.agent_verdicts`).

This module is the single source of truth both `done-work`'s gate and
`show-pr --field review` consume (COR-007). The tests cover the line grammar,
the latest-per-reviewer-by-timestamp selection (DEC-028 step 5), the
verdict marker and the reviewed head it names (#1179), and the injectable
freshness / membership filters the consumers scope with.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
LIB_PATH = SCRIPTS_DIR / "_lib" / "agent_verdicts.py"


@pytest.fixture(scope="module")
def av():
    sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("pm_agent_verdicts_under_test", LIB_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_agent_verdicts_under_test"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(SCRIPTS_DIR))


# Real reviewer-path verdicts carry the `<!-- pkit-verdict -->` marker (#593);
# `marked=False` simulates a bare verdict-grammar comment from some other path.
_MARKER = "<!-- pkit-verdict -->"


def _local(
    name,
    verdict,
    author="reviewer",
    ts="2026-06-02T00:00:00Z",
    reasons="because reasons",
    marked=True,
):
    tail = f"\n\n{_MARKER}" if marked else ""
    return {
        "author": {"login": author},
        "body": f"Reviewer agent (local, {name}): {verdict}\n\n{reasons}{tail}",
        "createdAt": ts,
    }


def _remote(
    verdict, author="review-bot", ts="2026-06-02T00:00:00Z", reasons="remote reasons", marked=True
):
    tail = f"\n\n{_MARKER}" if marked else ""
    return {
        "author": {"login": author},
        "body": f"Reviewer agent: {verdict}\n\n{reasons}{tail}",
        "createdAt": ts,
    }


# --- line grammar ----------------------------------------------------


def test_parse_local_line(av) -> None:
    token, path, name = av.parse_verdict_line("Reviewer agent (local, critic): APPROVED")
    assert (token, path, name) == (av.APPROVED, av.PATH_LOCAL, "critic")


def test_parse_remote_line(av) -> None:
    token, path, name = av.parse_verdict_line("Reviewer agent: CHANGES_REQUESTED")
    assert (token, path, name) == (av.CHANGES_REQUESTED, av.PATH_REMOTE, None)


def test_parse_non_verdict_line(av) -> None:
    assert av.parse_verdict_line("just a normal comment") == (None, "", None)


# --- latest-per-reviewer selection -----------------------------------


def test_single_local_verdict_body_preserved(av) -> None:
    out = av.latest_verdicts_per_reviewer(
        [_local("critic", "APPROVED", reasons="looks good to me")]
    )
    assert len(out) == 1
    assert out[0].reviewer == "critic"
    assert out[0].token == av.APPROVED
    assert out[0].path == av.PATH_LOCAL
    assert "looks good to me" in out[0].body


def test_multi_reviewer_each_kept(av) -> None:
    out = av.latest_verdicts_per_reviewer(
        [
            _local("critic", "APPROVED"),
            _local("architect", "CHANGES_REQUESTED"),
        ]
    )
    by_name = {v.reviewer: v.token for v in out}
    assert by_name == {"critic": av.APPROVED, "architect": av.CHANGES_REQUESTED}


def test_latest_by_timestamp_not_list_order(av) -> None:
    # An earlier APPROVED appears AFTER a later CHANGES_REQUESTED in the list;
    # the later timestamp must win regardless of array order (DEC-028 step 5).
    out = av.latest_verdicts_per_reviewer(
        [
            _local("critic", "CHANGES_REQUESTED", ts="2026-06-03T00:00:00Z"),
            _local("critic", "APPROVED", ts="2026-06-02T00:00:00Z"),
        ]
    )
    assert len(out) == 1
    assert out[0].token == av.CHANGES_REQUESTED


def test_remote_and_local_do_not_collide(av) -> None:
    # A remote reviewer and a local reviewer with the same identity string are
    # keyed separately by path.
    out = av.latest_verdicts_per_reviewer(
        [
            _remote("APPROVED", author="critic"),
            _local("critic", "CHANGES_REQUESTED"),
        ]
    )
    paths = {v.path for v in out}
    assert paths == {av.PATH_REMOTE, av.PATH_LOCAL}
    assert len(out) == 2


# --- injectable filters (the consumers' scoping) ---------------------


def _after(anchor):
    """A freshness predicate standing in for the rule: posted after `anchor`."""
    return lambda verdict: verdict.timestamp > anchor


def _gate_any(av, comments, is_fresh):
    return av.gate_verdicts(
        comments,
        is_fresh=is_fresh,
        local_reviewer_ok=lambda _n: True,
        remote_reviewer_ok=lambda _l: True,
    )


def test_is_fresh_drops_stale(av) -> None:
    # done-work's freshness predicate: only verdicts it holds fresh count.
    out = _gate_any(
        av,
        [_local("critic", "APPROVED", ts="2026-06-01T00:00:00Z")],
        _after("2026-06-01T00:00:00Z"),
    )
    assert out == []


def test_a_stale_latest_verdict_is_not_replaced_by_an_older_fresh_one(av) -> None:
    # The gate judges a reviewer's LATEST verdict (DEC-028 step 5, then step
    # 4): when it is stale the reviewer has no verdict that counts — the
    # APPROVED its CHANGES_REQUESTED superseded never stands in.
    approved, rejected = (
        _local("critic", "APPROVED", ts="2026-06-02T00:00:00Z", reasons="fresh"),
        _local("critic", "CHANGES_REQUESTED", ts="2026-06-03T00:00:00Z"),
    )
    out = _gate_any(av, [approved, rejected], lambda v: v.token == av.APPROVED)
    assert out == []


def test_freshness_judges_only_each_reviewers_latest_verdict(av) -> None:
    # Freshness may read the repository, so it is asked only of the verdict
    # that decides: each kept reviewer's latest.
    judged: list[tuple[str, str]] = []
    _gate_any(
        av,
        [
            _local("critic", "APPROVED", ts="2026-06-01T00:00:00Z"),
            _local("critic", "CHANGES_REQUESTED", ts="2026-06-02T00:00:00Z"),
            _local("critic", "APPROVED", ts="2026-06-03T00:00:00Z", marked=False),
        ],
        lambda v: judged.append((v.reviewer, v.timestamp)) or True,
    )
    assert judged == [("critic", "2026-06-02T00:00:00Z")]


def test_the_read_surface_judges_no_freshness(av) -> None:
    # show-pr applies no freshness filter — a "stale" verdict is still shown.
    out = av.latest_verdicts_per_reviewer([_local("critic", "APPROVED", ts="2026-06-01T00:00:00Z")])
    assert len(out) == 1


def test_reviewer_predicates_scope_the_set(av) -> None:
    out = av.latest_verdicts_per_reviewer(
        [
            _local("critic", "APPROVED"),
            _local("stranger", "CHANGES_REQUESTED"),
            _remote("APPROVED", author="bot"),
        ],
        local_reviewer_ok=lambda name: name == "critic",
        remote_reviewer_ok=lambda login: False,
    )
    assert [v.reviewer for v in out] == ["critic"]


def test_empty_comments_yields_nothing(av) -> None:
    assert av.latest_verdicts_per_reviewer([]) == []


def test_non_dict_comments_ignored(av) -> None:
    out = av.latest_verdicts_per_reviewer(["not a dict", None, _local("critic", "APPROVED")])
    assert [v.reviewer for v in out] == ["critic"]


# --- strict gate-facing wrapper (Fix 1: fail-open default unreachable) ---


def test_gate_verdicts_requires_is_fresh(av) -> None:
    # The freshness predicate is a required kwarg — omitting it is a TypeError
    # at the call site, so the gate cannot be invoked without a freshness
    # filter.
    with pytest.raises(TypeError):
        av.gate_verdicts(
            [_local("critic", "APPROVED")],
            local_reviewer_ok=lambda _n: True,
            remote_reviewer_ok=lambda _l: True,
        )


def test_gate_verdicts_requires_local_reviewer_ok(av) -> None:
    with pytest.raises(TypeError):
        av.gate_verdicts(
            [_local("critic", "APPROVED")],
            is_fresh=_after("2026-06-01T00:00:00Z"),
            remote_reviewer_ok=lambda _l: True,
        )


def test_gate_verdicts_requires_remote_reviewer_ok(av) -> None:
    with pytest.raises(TypeError):
        av.gate_verdicts(
            [_local("critic", "APPROVED")],
            is_fresh=_after("2026-06-01T00:00:00Z"),
            local_reviewer_ok=lambda _n: True,
        )


def test_gate_verdicts_cannot_be_called_with_all_defaults(av) -> None:
    # There is no permissive call path: with no kwargs at all it raises.
    with pytest.raises(TypeError):
        av.gate_verdicts([_local("critic", "APPROVED")])


def test_gate_verdicts_are_the_fresh_gate_candidates(av) -> None:
    # The strict wrapper is the gate's candidates — the latest marked verdict
    # per accepted reviewer — kept when fresh.
    comments = [
        _local("critic", "APPROVED", ts="2026-06-05T00:00:00Z"),
        _local("stranger", "CHANGES_REQUESTED", ts="2026-06-05T00:00:00Z"),
        _local("critic", "APPROVED", ts="2026-06-01T00:00:00Z"),
        _local("architect", "APPROVED", ts="2026-06-01T00:00:00Z"),
        _remote("APPROVED", author="pr-author", ts="2026-06-05T00:00:00Z"),
    ]
    fresh = _after("2026-06-02T00:00:00Z")

    def local_ok(name):
        return name != "stranger"

    def remote_ok(login):
        return login != "pr-author"

    strict = av.gate_verdicts(
        comments,
        is_fresh=fresh,
        local_reviewer_ok=local_ok,
        remote_reviewer_ok=remote_ok,
    )
    candidates = av.gate_candidates(
        comments,
        local_reviewer_ok=local_ok,
        remote_reviewer_ok=remote_ok,
    )
    assert strict == [v for v in candidates if fresh(v)]
    # And the filters actually took effect: stranger dropped (membership), the
    # remote pr-author dropped (membership), the older critic verdict
    # superseded, the stale architect verdict dropped (freshness), leaving the
    # fresh critic APPROVED.
    assert [(v.reviewer, v.timestamp) for v in candidates] == [
        ("architect", "2026-06-01T00:00:00Z"),
        ("critic", "2026-06-05T00:00:00Z"),
    ]
    assert [(v.reviewer, v.token) for v in strict] == [("critic", av.APPROVED)]


def test_gate_candidates_require_the_membership_filters(av) -> None:
    with pytest.raises(TypeError):
        av.gate_candidates([_local("critic", "APPROVED")], local_reviewer_ok=lambda _n: True)
    with pytest.raises(TypeError):
        av.gate_candidates([_local("critic", "APPROVED")], remote_reviewer_ok=lambda _l: True)


def test_gate_candidates_require_the_marker(av) -> None:
    out = av.gate_candidates(
        [_local("critic", "APPROVED", marked=False)],
        local_reviewer_ok=lambda _n: True,
        remote_reviewer_ok=lambda _l: True,
    )
    assert out == []


# --- verdict marker: gate requires it, read surface does not (#593) ---


def test_stamp_verdict_appends_marker(av) -> None:
    out = av.stamp_verdict("Reviewer agent (local, reviewer): APPROVED\n\nreasons")
    assert av.VERDICT_MARKER in out


def test_stamp_verdict_idempotent(av) -> None:
    once = av.stamp_verdict("Reviewer agent: APPROVED")
    twice = av.stamp_verdict(once)
    assert once == twice
    assert twice.count(av.VERDICT_MARKER) == 1


# --- the reviewed head and base in the marker (#1179) --------------------

_SHA = "a" * 40
_BASE = "c" * 40


def test_stamp_verdict_names_the_reviewed_head(av) -> None:
    out = av.stamp_verdict("Reviewer agent: APPROVED\n\nreasons", _SHA)
    assert out.endswith(f"\n\n<!-- pkit-verdict sha={_SHA} -->\n")
    assert av.read_marker(out) == (True, _SHA, "")


def test_stamp_verdict_names_the_reviewed_base(av) -> None:
    out = av.stamp_verdict("Reviewer agent: APPROVED\n\nreasons", _SHA, _BASE)
    assert out.endswith(f"\n\n<!-- pkit-verdict sha={_SHA} base={_BASE} -->\n")
    assert av.read_marker(out) == (True, _SHA, _BASE)


def test_stamp_verdict_replaces_a_marker_the_reviewer_wrote(av) -> None:
    # A reviewer agent is asked to end its output with the bare marker; the
    # posted body carries exactly one, naming the head review-pr showed it.
    body = f"Reviewer agent: APPROVED\n\nreasons\n\n{av.VERDICT_MARKER}"
    once = av.stamp_verdict(body, _SHA, _BASE)
    assert once.count("pkit-verdict") == 1
    assert av.stamp_verdict(once, _SHA, _BASE) == once


def test_stamp_verdict_keeps_a_malformed_object_out_of_the_marker(av) -> None:
    # A marker naming a malformed object would not be recognised, and the
    # verdict would not gate: a malformed head yields the bare marker, a
    # malformed base a marker naming the head alone.
    assert av.read_marker(av.stamp_verdict("Reviewer agent: APPROVED", "abc123")) == (
        True,
        "",
        "",
    )
    assert av.read_marker(av.stamp_verdict("Reviewer agent: APPROVED", _SHA, "abc123")) == (
        True,
        _SHA,
        "",
    )
    # A base without a head names nothing.
    assert av.verdict_marker("", _BASE) == av.VERDICT_MARKER


def test_read_marker_reads_every_marker_form(av) -> None:
    assert av.read_marker("no marker") == (False, "", "")
    assert av.read_marker(f"x\n{av.VERDICT_MARKER}") == (True, "", "")
    assert av.read_marker(f"x\n<!-- pkit-verdict sha={_SHA} -->") == (True, _SHA, "")
    assert av.read_marker(f"<!-- pkit-verdict sha={_SHA} base={_BASE} -->") == (
        True,
        _SHA,
        _BASE,
    )
    sha256 = "b" * 64
    assert av.read_marker(f"<!-- pkit-verdict sha={sha256} base={sha256} -->") == (
        True,
        sha256,
        sha256,
    )
    # An abbreviated object is no marker at all.
    assert av.read_marker("<!-- pkit-verdict sha=abc1234 -->") == (False, "", "")
    assert av.read_marker(f"<!-- pkit-verdict sha={_SHA} base=abc1234 -->") == (
        False,
        "",
        "",
    )


def test_a_verdict_carries_the_head_its_marker_names(av) -> None:
    comment = _local("critic", "APPROVED", marked=False)
    comment["body"] = av.stamp_verdict(comment["body"], _SHA)
    (marked,) = av.all_verdicts([comment], require_marker=True)
    assert (marked.sha, marked.base) == (_SHA, "")
    comment["body"] = av.stamp_verdict(comment["body"], _SHA, _BASE)
    (pinned,) = av.all_verdicts([comment], require_marker=True)
    assert (pinned.sha, pinned.base) == (_SHA, _BASE)
    (bare,) = av.all_verdicts([_local("critic", "APPROVED")])
    assert (bare.sha, bare.base) == ("", "")


def _gate(av, comments):
    return av.gate_verdicts(
        comments,
        is_fresh=_after("2026-06-01T00:00:00Z"),
        local_reviewer_ok=lambda _n: True,
        remote_reviewer_ok=lambda _l: True,
    )


def test_gate_counts_marked_verdict(av) -> None:
    got = _gate(av, [_local("reviewer", "APPROVED", marked=True)])
    assert [(v.reviewer, v.token) for v in got] == [("reviewer", av.APPROVED)]


def test_gate_drops_unmarked_verdict(av) -> None:
    # A bare verdict-grammar comment with no marker (posted by some non-reviewer
    # path) does NOT satisfy the gate — the #593 read-side spoof closure.
    assert _gate(av, [_local("reviewer", "APPROVED", marked=False)]) == []
    assert _gate(av, [_remote("APPROVED", marked=False)]) == []


def test_read_surface_shows_unmarked_verdict(av) -> None:
    # The read surface (default require_marker=False) still displays an unmarked
    # verdict-shaped comment — only the gate requires the marker.
    got = av.latest_verdicts_per_reviewer([_local("reviewer", "APPROVED", marked=False)])
    assert [(v.reviewer, v.token) for v in got] == [("reviewer", av.APPROVED)]


# --- all_verdicts: the full sequence behind the reduction (#905) --------


def test_all_verdicts_keeps_every_round_in_posting_order(av) -> None:
    # Array order is deliberately not posting order: all_verdicts sorts by
    # timestamp, so superseded rounds come back oldest first.
    comments = [
        _local("docs-reviewer", "APPROVED", ts="2026-06-04T00:00:00Z"),
        _local("docs-reviewer", "CHANGES_REQUESTED", ts="2026-06-02T00:00:00Z"),
        _local("docs-reviewer", "CHANGES_REQUESTED", ts="2026-06-03T00:00:00Z"),
    ]
    got = av.all_verdicts(comments)
    assert [(v.token, v.timestamp) for v in got] == [
        (av.CHANGES_REQUESTED, "2026-06-02T00:00:00Z"),
        (av.CHANGES_REQUESTED, "2026-06-03T00:00:00Z"),
        (av.APPROVED, "2026-06-04T00:00:00Z"),
    ]


def test_all_verdicts_applies_the_same_filters(av) -> None:
    # Marker and reviewer predicates drop exactly what they drop from the
    # latest-per-reviewer selection.
    comments = [
        _local("a", "APPROVED", ts="2026-06-01T00:00:00Z"),
        _local("a", "APPROVED", ts="2026-06-03T00:00:00Z", marked=False),
        _local("b", "APPROVED", ts="2026-06-03T00:00:00Z"),
        _local("c", "APPROVED", ts="2026-06-04T00:00:00Z"),
        {"author": {"login": "x"}, "body": "not a verdict", "createdAt": "2026-06-05T00:00:00Z"},
    ]
    got = av.all_verdicts(
        comments,
        local_reviewer_ok=lambda n: n != "c",
        require_marker=True,
    )
    assert [(v.reviewer, v.timestamp) for v in got] == [
        ("a", "2026-06-01T00:00:00Z"),
        ("b", "2026-06-03T00:00:00Z"),
    ]


def test_latest_is_the_reduction_of_all_verdicts(av) -> None:
    comments = [
        _local("critic", "CHANGES_REQUESTED", ts="2026-06-02T00:00:00Z"),
        _local("critic", "APPROVED", ts="2026-06-03T00:00:00Z"),
        _remote("CHANGES_REQUESTED", author="bot", ts="2026-06-01T00:00:00Z"),
        _local("bot", "APPROVED", ts="2026-06-01T00:00:00Z"),
    ]
    assert av.latest_verdicts_per_reviewer(comments) == (
        av.reduce_latest_per_reviewer(av.all_verdicts(comments))
    )


def test_reduction_keeps_first_seen_on_exact_tie(av) -> None:
    # The stable sort in all_verdicts preserves array order on a tie, so the
    # reduction keeps the first-seen verdict — unchanged from before #905.
    comments = [
        _local("critic", "CHANGES_REQUESTED", reasons="first"),
        _local("critic", "APPROVED", reasons="second"),
    ]
    got = av.latest_verdicts_per_reviewer(comments)
    assert [v.token for v in got] == [av.CHANGES_REQUESTED]


def test_reduction_returns_the_input_objects(av) -> None:
    history = av.all_verdicts(
        [
            _local("critic", "CHANGES_REQUESTED", ts="2026-06-02T00:00:00Z"),
            _local("critic", "APPROVED", ts="2026-06-03T00:00:00Z"),
        ]
    )
    (latest,) = av.reduce_latest_per_reviewer(history)
    assert latest is history[-1]


# ---- the commit-time anchor (DEC-028 "Stale-verdict handling") ---------
#
# One definition, read by the freshness rule (`_lib.verdict_freshness`) for a
# verdict naming no reviewed head, and by done-work's refusal when the PR's
# head cannot be read.


def test_latest_commit_timestamp_prefers_committed_then_authored(av) -> None:
    assert av.latest_commit_timestamp([]) == ""
    assert (
        av.latest_commit_timestamp([{"authoredDate": "2026-06-01T00:00:00Z"}])
        == "2026-06-01T00:00:00Z"
    )
    assert (
        av.latest_commit_timestamp(
            [
                {"committedDate": "2026-06-01T00:00:00Z"},
                {"committedDate": "2026-06-05T00:00:00Z", "authoredDate": "2026-06-04T00:00:00Z"},
            ]
        )
        == "2026-06-05T00:00:00Z"
    )


def test_latest_commit_timestamp_is_empty_without_a_readable_head(av) -> None:
    assert av.latest_commit_timestamp([{"oid": "abc123"}]) == ""
    assert av.latest_commit_timestamp(["not-a-commit"]) == ""
