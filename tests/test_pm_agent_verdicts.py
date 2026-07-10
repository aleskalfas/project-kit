"""Tests for the shared DEC-028 verdict parser (`_lib.agent_verdicts`).

This module is the single source of truth both `done-work`'s gate and
`show-pr --field review` consume (COR-007). The tests cover the line grammar,
the latest-per-reviewer-by-timestamp selection (DEC-028 step 5), and the
injectable freshness / membership filters the two consumers scope with.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
)
LIB_PATH = SCRIPTS_DIR / "_lib" / "agent_verdicts.py"


@pytest.fixture(scope="module")
def av():
    sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(
        "pm_agent_verdicts_under_test", LIB_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_agent_verdicts_under_test"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(SCRIPTS_DIR))


def _local(name, verdict, author="reviewer", ts="2026-06-02T00:00:00Z",
           reasons="because reasons"):
    return {
        "author": {"login": author},
        "body": f"Reviewer agent (local, {name}): {verdict}\n\n{reasons}",
        "createdAt": ts,
    }


def _remote(verdict, author="review-bot", ts="2026-06-02T00:00:00Z",
            reasons="remote reasons"):
    return {
        "author": {"login": author},
        "body": f"Reviewer agent: {verdict}\n\n{reasons}",
        "createdAt": ts,
    }


# --- line grammar ----------------------------------------------------


def test_parse_local_line(av) -> None:
    token, path, name = av.parse_verdict_line(
        "Reviewer agent (local, critic): APPROVED"
    )
    assert (token, path, name) == (av.APPROVED, av.PATH_LOCAL, "critic")


def test_parse_remote_line(av) -> None:
    token, path, name = av.parse_verdict_line(
        "Reviewer agent: CHANGES_REQUESTED"
    )
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
    out = av.latest_verdicts_per_reviewer([
        _local("critic", "APPROVED"),
        _local("architect", "CHANGES_REQUESTED"),
    ])
    by_name = {v.reviewer: v.token for v in out}
    assert by_name == {"critic": av.APPROVED, "architect": av.CHANGES_REQUESTED}


def test_latest_by_timestamp_not_list_order(av) -> None:
    # An earlier APPROVED appears AFTER a later CHANGES_REQUESTED in the list;
    # the later timestamp must win regardless of array order (DEC-028 step 5).
    out = av.latest_verdicts_per_reviewer([
        _local("critic", "CHANGES_REQUESTED", ts="2026-06-03T00:00:00Z"),
        _local("critic", "APPROVED", ts="2026-06-02T00:00:00Z"),
    ])
    assert len(out) == 1
    assert out[0].token == av.CHANGES_REQUESTED


def test_remote_and_local_do_not_collide(av) -> None:
    # A remote reviewer and a local reviewer with the same identity string are
    # keyed separately by path.
    out = av.latest_verdicts_per_reviewer([
        _remote("APPROVED", author="critic"),
        _local("critic", "CHANGES_REQUESTED"),
    ])
    paths = {v.path for v in out}
    assert paths == {av.PATH_REMOTE, av.PATH_LOCAL}
    assert len(out) == 2


# --- injectable filters (the consumers' scoping) ---------------------


def test_min_timestamp_drops_stale(av) -> None:
    # done-work's freshness anchor: only comments strictly after it count.
    out = av.latest_verdicts_per_reviewer(
        [_local("critic", "APPROVED", ts="2026-06-01T00:00:00Z")],
        min_timestamp="2026-06-01T00:00:00Z",
    )
    assert out == []


def test_no_min_timestamp_keeps_stale(av) -> None:
    # show-pr applies no freshness filter — a "stale" verdict is still shown.
    out = av.latest_verdicts_per_reviewer(
        [_local("critic", "APPROVED", ts="2026-06-01T00:00:00Z")]
    )
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
    out = av.latest_verdicts_per_reviewer(
        ["not a dict", None, _local("critic", "APPROVED")]
    )
    assert [v.reviewer for v in out] == ["critic"]


# --- strict gate-facing wrapper (Fix 1: fail-open default unreachable) ---


def test_gate_verdicts_requires_min_timestamp(av) -> None:
    # The freshness anchor is a required kwarg — omitting it is a TypeError at
    # the call site, so the gate cannot be invoked without a freshness filter.
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
            min_timestamp="2026-06-01T00:00:00Z",
            remote_reviewer_ok=lambda _l: True,
        )


def test_gate_verdicts_requires_remote_reviewer_ok(av) -> None:
    with pytest.raises(TypeError):
        av.gate_verdicts(
            [_local("critic", "APPROVED")],
            min_timestamp="2026-06-01T00:00:00Z",
            local_reviewer_ok=lambda _n: True,
        )


def test_gate_verdicts_cannot_be_called_with_all_defaults(av) -> None:
    # There is no permissive call path: with no kwargs at all it raises.
    with pytest.raises(TypeError):
        av.gate_verdicts([_local("critic", "APPROVED")])


def test_gate_verdicts_behaviour_identical_when_filters_supplied(av) -> None:
    # With the same filters the strict wrapper returns exactly what the
    # permissive primitive returns — behaviour-preserving delegation.
    comments = [
        _local("critic", "APPROVED", ts="2026-06-05T00:00:00Z"),
        _local("stranger", "CHANGES_REQUESTED", ts="2026-06-05T00:00:00Z"),
        _local("critic", "APPROVED", ts="2026-06-01T00:00:00Z"),
        _remote("APPROVED", author="pr-author", ts="2026-06-05T00:00:00Z"),
    ]
    anchor = "2026-06-02T00:00:00Z"
    local_ok = lambda name: name == "critic"
    remote_ok = lambda login: login != "pr-author"
    strict = av.gate_verdicts(
        comments,
        min_timestamp=anchor,
        local_reviewer_ok=local_ok,
        remote_reviewer_ok=remote_ok,
    )
    permissive = av.latest_verdicts_per_reviewer(
        comments,
        min_timestamp=anchor,
        local_reviewer_ok=local_ok,
        remote_reviewer_ok=remote_ok,
    )
    assert strict == permissive
    # And the filters actually took effect: stranger dropped (membership), the
    # remote pr-author dropped (membership), the stale critic verdict dropped
    # (freshness), leaving the fresh critic APPROVED.
    assert [(v.reviewer, v.token) for v in strict] == [("critic", av.APPROVED)]
