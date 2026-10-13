"""Tests for anchors on one point of a record (Task #1419; COR-050 points 2, 5 to 7, 9 and 12).

An anchor `PRJ-900#2` stands on point 2 of the record, and on what makes the
record bind: its status, supersession and title fields, its preamble and
Summary, and the Decision's text outside every point and stub. The change
check, the whole-repository check and the debt listing read it through one
reading (`record_points`), so they agree on the five cases: a changed point
flags its dependants, a change elsewhere flags none, a move holds, a removed
point is a dead anchor, and an anchor on a retired point stands on nothing
until it is re-pointed. The explanation shows the point's diff alone, and a
whole-record anchor works as before.

Every test stands up a real adopter repository, commits a base on `main`
with the record and an artefact anchored to its point, revalidated there,
branches `feature` off it and commits one change.
"""

from __future__ import annotations

from typing import Any

import pytest

from project_kit import friction_check as fc
from project_kit import friction_report as frep
from project_kit import friction_repository as fr
from tests.adopter_repo import MakeAdopterRepo
from tests.friction_documents import (
    POINTED,
    POINTS,
    T2,
    Timeline,
    guide,
    pointed_record,
)

ON_POINT = {"record": ["PRJ-900#2"]}


@pytest.fixture
def timeline(make_adopter_repo: MakeAdopterRepo) -> Timeline:
    return Timeline(make_adopter_repo())


def _start(timeline: Timeline, anchors: dict[str, list[str]] | None = None, **record: Any) -> str:
    """The base on `main`: the record, and `guide` anchored to its point 2 and revalidated
    there; then the branch `feature` off it."""
    base = timeline.start(
        {
            POINTED: pointed_record(**record),
            "docs/guide.md": guide(anchors=anchors or ON_POINT),
        }
    )
    timeline.adopter.checkout("feature", create=True)
    return base


def _change(timeline: Timeline, **record: Any) -> str:
    return timeline.commit("change the record", {POINTED: pointed_record(**record)})


def _change_check(timeline: Timeline) -> list[tuple[str, str | None]]:
    result = fc.run_change_check(timeline.adopter.root, "main")
    return [(f.kind.value, None if f.anchor is None else f.anchor.value) for f in result.findings]


def _repository(timeline: Timeline) -> list[tuple[str, str | None, str | None]]:
    result = fr.run_repository_check(timeline.adopter.root)
    return [
        (f.kind.value, None if f.anchor is None else f.anchor.value, f.origin and f.origin.sha)
        for f in result.findings
    ]


def _debt(timeline: Timeline) -> list[tuple[str, str | None, str]]:
    listing = frep.run_debt(timeline.adopter.root)
    return [
        (
            e.finding.kind.value,
            None if e.finding.anchor is None else e.finding.anchor.value,
            e.origin.sha,
        )
        for e in listing.entries
    ]


def _edited(point: str, text: str) -> tuple[tuple[str, str, str], ...]:
    return tuple((pid, name, text if pid == point else words) for pid, name, words in POINTS)


# --- the five cases, read alike by the change check, the whole-repository check and debt ---


def test_a_changed_point_flags_its_dependants_in_every_check(timeline: Timeline) -> None:
    _start(timeline)
    changed = _change(timeline, points=_edited("2", "The second point, rewritten."))
    assert _change_check(timeline) == [("friction", "PRJ-900#2")]
    assert _repository(timeline) == [("stale", "PRJ-900#2", changed)]
    assert _debt(timeline) == [("stale", "PRJ-900#2", changed)]


@pytest.mark.parametrize(
    "record",
    [
        pytest.param({"points": _edited("3", "The third point, rewritten.")}, id="another-point"),
        pytest.param({"context": "Another reason it came up."}, id="context"),
        pytest.param({"rationale": "Another reason this way."}, id="rationale"),
    ],
)
def test_a_change_elsewhere_flags_none_in_any_check(
    timeline: Timeline, record: dict[str, Any]
) -> None:
    _start(timeline)
    _change(timeline, **record)
    assert _change_check(timeline) == []
    assert _repository(timeline) == []
    assert _debt(timeline) == []


def test_a_moved_point_holds_in_every_check(timeline: Timeline) -> None:
    _start(timeline)
    _change(timeline, points=(POINTS[1], POINTS[0], POINTS[2]))
    assert _change_check(timeline) == []
    assert _repository(timeline) == []
    assert _debt(timeline) == []


def test_a_removed_point_is_a_dead_anchor_in_every_check(timeline: Timeline) -> None:
    _start(timeline)
    _change(timeline, points=(POINTS[0], POINTS[2]))
    result = fc.run_change_check(timeline.adopter.root, "main")
    (dead,) = result.findings
    assert (dead.kind, dead.anchor and dead.anchor.value) == (
        fc.FindingKind.DEAD_ANCHOR,
        "PRJ-900#2",
    )
    assert dead.message == "PRJ-900 holds no point 2; the diff removed or moved its target"
    assert not result.failed  # warning mode reports it
    assert _repository(timeline) == [("dead-anchor", "PRJ-900#2", None)]
    assert _debt(timeline) == []


def test_an_anchor_on_a_retired_point_stands_on_nothing_in_every_check(
    timeline: Timeline,
) -> None:
    _start(timeline)
    retiring = (
        POINTS[0],
        ("2", "Retired", "Its content is in point 4."),
        ("4", "Second, split", "The second point, carried on."),
        POINTS[2],
    )
    retired = _change(timeline, points=retiring, retired={"2": ["4"]})

    (friction,) = fc.run_change_check(timeline.adopter.root, "main").findings
    assert friction.kind is fc.FindingKind.FRICTION
    assert "PRJ-900 retires point 2, its content in point 4: re-point the anchor" in (
        friction.message
    )
    assert _repository(timeline) == [("stale", "PRJ-900#2", retired)]
    assert _debt(timeline) == [("stale", "PRJ-900#2", retired)]

    # Answered once, it stands on nothing at both states, and is not flagged again.
    timeline.commit(
        "answer the retirement",
        {"docs/guide.md": guide(anchors=ON_POINT, at=T2, because="re-pointing waits")},
    )
    assert _repository(timeline) == []
    assert _debt(timeline) == []


# --- what a point stands on -------------------------------------------------------


@pytest.mark.parametrize(
    "record",
    [
        pytest.param({"status": "superseded"}, id="status"),
        pytest.param({"title": "A retitled record"}, id="title"),
        pytest.param({"lead": "The record decides three things, and one more."}, id="lead"),
        pytest.param({"preamble": "Partially superseded by PRJ-901."}, id="preamble"),
    ],
)
def test_what_makes_the_record_bind_flags_the_dependants_of_its_points(
    timeline: Timeline, record: dict[str, Any]
) -> None:
    _start(timeline)
    changed = _change(timeline, **record)
    assert _change_check(timeline) == [("friction", "PRJ-900#2")]
    assert _repository(timeline) == [("stale", "PRJ-900#2", changed)]


def test_the_origin_is_where_the_point_changed_not_the_record_s_last_edit(
    timeline: Timeline,
) -> None:
    _start(timeline)
    changed = _change(timeline, points=_edited("2", "The second point, rewritten."))
    rewritten = _edited("2", "The second point, rewritten.")
    later = tuple(
        (pid, name, "The third point, rewritten." if pid == "3" else words)
        for pid, name, words in rewritten
    )
    _change(timeline, points=later)
    assert _repository(timeline) == [("stale", "PRJ-900#2", changed)]


def test_a_point_edited_and_put_back_is_no_change(timeline: Timeline) -> None:
    _start(timeline)
    _change(timeline, points=_edited("2", "The second point, rewritten."))
    _change(timeline)
    assert _change_check(timeline) == []
    assert _repository(timeline) == []


def test_a_point_anchor_follows_its_record_across_a_rename(timeline: Timeline) -> None:
    _start(timeline)
    timeline.rename(POINTED, ".pkit/decisions/project/PRJ-900-renamed.md")
    assert _change_check(timeline) == []
    assert _repository(timeline) == []


def test_an_anchor_made_ambiguous_is_the_change_s(timeline: Timeline) -> None:
    _start(timeline)
    _change(timeline, points=(*POINTS, ("2", "Again", "A second point with the id 2.")))
    (ambiguous,) = fc.run_change_check(timeline.adopter.root, "main").findings
    assert ambiguous.kind is fc.FindingKind.DEAD_ANCHOR
    assert ambiguous.message == (
        "is ambiguous: 2 points of PRJ-900 have the id 2; the diff gave another point its id"
    )
    ((kind, value, _origin),) = _repository(timeline)
    assert (kind, value) == ("dead-anchor", "PRJ-900#2")


def test_a_point_anchor_on_a_record_in_list_form_is_dead(timeline: Timeline) -> None:
    _start(timeline)
    timeline.commit(
        "anchor a point of a list-form record",
        {"docs/guide.md": guide(anchors={"record": ["COR-050#5"]}, at=T2, because="re-pointed")},
    )
    findings = fc.run_change_check(timeline.adopter.root, "main").findings
    (dead,) = [f for f in findings if f.kind is fc.FindingKind.DEAD_ANCHOR]
    assert dead.message.startswith("COR-050 writes its points as a list")
    assert dead.message.endswith("; the anchor was added in this diff")


def test_a_whole_record_anchor_still_changes_with_any_edit(timeline: Timeline) -> None:
    _start(timeline, anchors={"record": ["PRJ-900", "PRJ-900#2"]})
    changed = _change(timeline, rationale="Another reason this way.")
    assert _change_check(timeline) == [("friction", "PRJ-900")]
    assert _repository(timeline) == [("stale", "PRJ-900", changed)]


# --- the explanation ----------------------------------------------------------------


def test_the_explanation_shows_the_point_s_diff_alone(timeline: Timeline) -> None:
    base = _start(timeline)
    _change(
        timeline,
        points=_edited("2", "The second point, rewritten."),
        rationale="Another reason this way.",
    )
    explanation = frep.run_explain(timeline.adopter.root, "docs/guide.md")
    (anchor,) = explanation.anchors
    assert anchor.state == "stale" and anchor.diff is not None
    assert anchor.diff[:2] == (f"--- PRJ-900#2 at {base[:12]}", "+++ PRJ-900#2 at HEAD")
    changed = [line for line in anchor.diff if line[:1] in "+-" and line[:3] not in ("---", "+++")]
    assert changed == ["-The second point.", "+The second point, rewritten."]
    human = frep.render_explain_human(explanation)
    assert "what the point stands on, from its revalidation point to HEAD:" in human
    assert "      +The second point, rewritten." in human
    assert "Another reason this way." not in human
    assert frep.render_explain_json(explanation).count('"diff": [') == 1


def test_a_whole_record_anchor_shows_no_point_diff(timeline: Timeline) -> None:
    _start(timeline, anchors={"record": ["PRJ-900"]})
    _change(timeline, rationale="Another reason this way.")
    (anchor,) = frep.run_explain(timeline.adopter.root, "docs/guide.md").anchors
    assert (anchor.state, anchor.diff) == ("stale", None)


# --- a deferral of an anchor on a point --------------------------------------------


def test_a_deferral_covers_a_point_as_it_stood_and_lists_only_its_changes(
    timeline: Timeline,
) -> None:
    _start(timeline)
    rewritten = _edited("2", "The second point, rewritten.")
    changed = timeline.commit(
        "change point 2, and defer the guide",
        {
            POINTED: pointed_record(points=rewritten),
            "docs/guide.md": guide(
                anchors=ON_POINT, deferred=[("record", "PRJ-900#2", "rewrite after #1")]
            ),
        },
    )
    assert _change_check(timeline) == [("answered", "PRJ-900#2")]
    later = tuple(
        (pid, name, "The third point, rewritten." if pid == "3" else words)
        for pid, name, words in rewritten
    )
    _change(timeline, points=later)  # another point: the deferral still covers point 2
    assert _repository(timeline) == [("deferred", "PRJ-900#2", changed)]
    (finding,) = frep.run_explain(timeline.adopter.root, "docs/guide.md").findings
    assert finding.finding.kind is fr.RepositoryFindingKind.DEFERRED
    assert [c.commit.sha for c in finding.commits] == [changed]

    again = _change(timeline, points=_edited("2", "The second point, rewritten twice."))
    assert ("stale", "PRJ-900#2", again) in _repository(timeline)
