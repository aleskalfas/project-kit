"""Tests for the answer reader, `project_kit.answer_files` (COR-062; ADR-068; #1870).

The reader is dormant until the move: nothing writes an answer file yet, so
every answer file here is written by hand. The pure tests judge one artefact's
entries (`liveness`); the rest stand up a real adopter repository with dated
commits and run the whole-repository check, the debt listing, `explain` and
validation over it.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, cast

import pytest
from click.testing import CliRunner

from project_kit import answer_files as af
from project_kit import friction_report as frep
from project_kit import friction_repository as fr
from project_kit import friction_validate as fv
from project_kit.cli import main
from project_kit.friction_discovery import Anchor
from tests.adopter_repo import MakeAdopterRepo
from tests.friction_documents import (
    CONFIG,
    T1,
    T2,
    Timeline,
    document,
    friction_config,
)

GUIDE = "docs/guide.md"
CLI = Anchor("path", "src/cli/**")
CORE = Anchor("path", "src/core/**")
T3 = "2026-10-03T10:00:00Z"
FOLDER = ".pkit/project/friction/answers"


def answer_path(name: str) -> str:
    return f"{FOLDER}/{name}.yaml"


def bare_guide(**fields: Any) -> str:
    """`guide`, anchored to the CLI and the engine, its block holding no answer: it is
    read from the answer files."""
    return document("guide", anchors={"path": ["src/cli/**", "src/core/**"]}, **fields)


def entry(
    location: str = GUIDE,
    *,
    at: str | None = None,
    outcome: str = "unchanged",
    because: str = "the CLI still holds",
    read: Sequence[str] = (),
    deferred: Sequence[tuple[Anchor, str]] = (),
    revisited: Sequence[tuple[Anchor, str, str]] = (),
) -> dict[str, Any]:
    """One artefact's answers in an answer file (COR-062 point 1)."""
    found: dict[str, Any] = {"artefact": location}
    if read:
        found["read"] = [f"{name}.yaml" for name in read]
    revalidated: dict[str, Any] = {}
    if at is not None:
        revalidated["at"] = at
        revalidated["outcome"] = outcome
        if outcome == "unchanged":
            revalidated["unchanged-because"] = because
    if deferred:
        revalidated["deferred"] = [
            {"anchor": {"kind": a.kind, "value": a.value}, "reason": reason}
            for a, reason in deferred
        ]
    if revalidated:
        found["revalidated"] = revalidated
    if revisited:
        found["revisited"] = [
            {"anchor": {"kind": a.kind, "value": a.value}, "outcome": outcome, "reason": reason}
            for a, outcome, reason in revisited
        ]
    return found


def answers(*entries: dict[str, Any]) -> str:
    """An answer file holding `entries`, as JSON: valid YAML, exact about strings."""
    return json.dumps({"answers": list(entries)}, indent=2) + "\n"


@pytest.fixture
def timeline(make_adopter_repo: MakeAdopterRepo) -> Timeline:
    return Timeline(make_adopter_repo())


def _check(timeline: Timeline) -> fr.RepositoryCheck:
    return fr.run_repository_check(timeline.adopter.root)


def _report(result: fr.RepositoryCheck, location: str = GUIDE) -> fr.ArtefactReport:
    (report,) = [r for r in result.artefact_reports if r.location == location]
    return report


def _points(result: fr.RepositoryCheck, location: str = GUIDE) -> list[str]:
    return [c.sha for c in _report(result, location).revalidation_points]


def _answers(result: fr.RepositoryCheck, location: str = GUIDE) -> Mapping[str, Any]:
    """The artefact's live answers, as the check's machine-readable output gives them."""
    found = _report(result, location).answers
    assert found is not None
    return found


def _kinds(result: fr.RepositoryCheck) -> list[tuple[str, str | None]]:
    return [(f.kind.value, None if f.anchor is None else f.anchor.value) for f in result.findings]


# --- the folder ---------------------------------------------------------------------


def test_an_answer_file_is_a_yaml_file_directly_in_the_folder() -> None:
    assert af.FOLDER == FOLDER
    assert af.is_answer_file(f"{FOLDER}/20261021T093000Z-3f9a2c1d.yaml")
    assert af.is_answer_file(f"{FOLDER}/moved-0123456789ab.yaml")
    assert not af.is_answer_file(f"{FOLDER}/notes.md")
    assert not af.is_answer_file(f"{FOLDER}/deeper/one.yaml")
    assert not af.is_answer_file(".pkit/project/friction/one.yaml")
    assert af.in_folder(f"{FOLDER}/notes.md") and not af.in_folder("docs/guide.md")


# --- one file -----------------------------------------------------------------------


def test_a_file_is_read_with_its_entries_and_its_names() -> None:
    read = af.read_answer_file(
        "b.yaml",
        answers(
            entry(at=T1, read=("a",), deferred=((CLI, "  waits   for #12 "),)),
            entry("docs/notes.md#n1", revisited=((CORE, "unchanged", "still stands"),)),
        ).encode(),
    )
    assert read.problem is None
    first, second = read.entries
    assert (first.file, first.index, first.location, first.read) == (
        "b.yaml",
        0,
        GUIDE,
        ("a.yaml",),
    )
    assert first.revalidation is not None and first.revalidation.written == T1
    assert first.revalidation.because == "the CLI still holds"
    assert [(d.anchor, d.reason) for d in first.deferrals] == [(CLI, "waits for #12")]
    assert second.location == "docs/notes.md#n1" and second.revalidation is None
    assert [(r.anchor, r.outcome) for r in second.revisits] == [(CORE, "unchanged")]


@pytest.mark.parametrize(
    ("raw", "problem"),
    [
        (b"answers: [unclosed\n", "does not parse as YAML"),
        (b"- one\n", "is no mapping"),
        (b"answers: none\n", "holds no `answers` list"),
        (b"\xff\xfe", "is not UTF-8 text"),
    ],
)
def test_a_file_that_does_not_read_says_why(raw: bytes, problem: str) -> None:
    read = af.read_answer_file("x.yaml", raw)
    assert read.entries == () and read.problem is not None and read.problem.startswith(problem)


# --- which answers are live ---------------------------------------------------------


def _entry(file: str, **kwargs: Any) -> af.Entry:
    (found,) = af.read_answer_file(f"{file}.yaml", answers(entry(**kwargs)).encode()).entries
    return found


def _live(
    entries: Sequence[af.Entry],
    *,
    void: Sequence[tuple[str, str]] = (),
    declared: Sequence[Anchor] = (CLI, CORE),
    targets: Sequence[Anchor] | None = None,
) -> af.Liveness:
    present = {e.file for e in entries}
    voided = {(f"{r}.yaml", f"{n}.yaml") for r, n in void}
    return af.liveness(
        entries,
        present,
        lambda reader, named: (reader, named) not in voided,
        declared=declared,
        targets=targets,
    )


def _files(found: Sequence[af.Entry]) -> list[str]:
    return [e.file.removesuffix(".yaml") for e in found]


def test_a_revalidation_replaces_the_revalidations_it_read() -> None:
    x = _entry("x", at=T1)
    y = _entry("y", at=T2, read=("x",))
    judged = _live([x, y])
    assert _files(judged.revalidations) == ["y"] and judged.apart == ()


def test_a_deferral_replaces_no_revalidation_and_only_the_deferral_of_its_anchor() -> None:
    x = _entry("x", at=T1, deferred=((CORE, "until #7"),))
    y = _entry("y", read=("x",), deferred=((CLI, "until #9"),))
    judged = _live([x, y])
    assert _files(judged.revalidations) == ["x"]
    assert [(e.file, d.anchor) for e, d in judged.deferrals] == [
        ("x.yaml", CORE),
        ("y.yaml", CLI),
    ]
    z = _entry("z", read=("x", "y"), deferred=((CORE, "until #8"),))
    judged = _live([x, y, z])
    assert [(e.file, d.anchor) for e, d in judged.deferrals] == [
        ("y.yaml", CLI),
        ("z.yaml", CORE),
    ]


def test_a_revalidation_replaces_each_deferral_it_read_that_it_does_not_restate() -> None:
    x = _entry("x", deferred=((CLI, "until #7"), (CORE, "until #8")))
    y = _entry("y", at=T2, read=("x",), deferred=((CORE, "until #8, still"),))
    judged = _live([x, y])
    assert [(e.file, d.anchor) for e, d in judged.deferrals] == [("y.yaml", CORE)]
    # The re-stated deferral is kept by its revalidation, and keeps the point of the one
    # it replaced.
    assert {(e.file, d.anchor) for e, d in judged.kept} == {("y.yaml", CORE)}
    (restated,) = [d for e, d in judged.deferrals]
    assert [(e.file, d.anchor) for e, d in judged.inherited(y, restated)] == [("x.yaml", CORE)]


def test_a_deferral_keeps_no_point_of_one_another_answer_replaced_before_it() -> None:
    x = _entry("x", deferred=((CLI, "until #7"),))
    y = _entry("y", at=T2, read=("x",))
    z = _entry("z", read=("x", "y"), deferred=((CLI, "until #9"),))
    judged = _live([x, y, z])
    (later,) = [d for e, d in judged.deferrals]
    assert judged.inherited(z, later) == ()


def test_a_revisit_entry_replaces_only_the_entry_for_its_own_target() -> None:
    x = _entry("x", revisited=((CLI, "unchanged", "a"), (CORE, "unchanged", "b")))
    y = _entry("y", read=("x",), revisited=((CLI, "deferred", "until #3"),))
    judged = _live([x, y], targets=(CLI, CORE))
    assert [(e.file, r.anchor) for e, r in judged.revisits] == [
        ("x.yaml", CORE),
        ("y.yaml", CLI),
    ]


def test_an_answer_on_what_is_gone_is_not_live() -> None:
    x = _entry("x", deferred=((Anchor("path", "src/gone/**"), "until #7"),))
    y = _entry("y", revisited=((Anchor("record", "COR-001"), "unchanged", "still"),))
    judged = _live([x, y], targets=(CLI,))
    assert judged.deferrals == () and judged.revisits == ()


def test_a_void_name_replaces_nothing_and_the_two_were_made_apart() -> None:
    x = _entry("x", at=T1)
    y = _entry("y", at=T2, read=("x",))
    judged = _live([x, y], void=(("y", "x"),))
    assert _files(judged.revalidations) == ["x", "y"]
    assert [(a.file, b.file) for a, b in judged.apart] == [("x.yaml", "y.yaml")]


def test_two_answers_that_name_each_other_read_neither() -> None:
    x = _entry("x", at=T1, read=("y",))
    y = _entry("y", at=T2, read=("x",))
    judged = _live([x, y])
    assert _files(judged.revalidations) == ["x", "y"] and len(judged.apart) == 1


def test_a_name_of_a_file_the_state_does_not_hold_names_nothing() -> None:
    y = _entry("y", at=T2, read=("x",))
    assert _live([y]).reads[y] == frozenset()


def test_an_answer_stays_replaced_while_one_that_read_it_is_present() -> None:
    x = _entry("x", at=T1)
    y = _entry("y", at=T2, read=("x",))
    w = _entry("w", at=T3, read=("x", "y"))
    assert _files(_live([x, y, w]).revalidations) == ["w"]
    # With Y gone, W still read X: X stays replaced.
    assert _files(_live([x, w]).revalidations) == ["w"]
    # Had W named only Y, removing Y would bring X back beside W: made apart.
    w_only = _entry("w", at=T3, read=("y",))
    judged = _live([x, w_only])
    assert _files(judged.revalidations) == ["w", "x"] and len(judged.apart) == 1


def test_an_uncommitted_entry_honours_a_name_of_a_file_head_holds() -> None:
    head = {"x.yaml": af.read_answer_file("x.yaml", answers(entry(at=T1)).encode())}
    names = af.WorkingNames(head, None)
    assert names.honoured("y.yaml", "x.yaml")
    assert not names.honoured("y.yaml", "z.yaml")


# --- the whole-repository check reads answer files -----------------------------------


def test_an_artefact_whose_block_holds_no_answer_is_read_from_its_answer_file(
    timeline: Timeline,
) -> None:
    timeline.start({GUIDE: bare_guide()})
    answered = timeline.commit("answer the guide", {answer_path("one"): answers(entry(at=T1))})
    result = _check(timeline)
    assert _points(result) == [answered]
    assert _report(result).state is fr.ArtefactState.CURRENT
    report = _report(result)
    assert report.answers is not None and report.answers["home"] == "files"
    (revalidation,) = report.answers["revalidations"]
    assert (revalidation["file"], revalidation["at"]) == ("one.yaml", T1)
    assert [p["commit"] for p in revalidation["points"]] == [answered]

    changed = timeline.commit("change the CLI", {"src/cli/main.py": "print('v2')\n"})
    result = _check(timeline)
    assert [(f.kind.value, f.origin.sha if f.origin else None) for f in result.findings] == [
        ("stale", changed)
    ]


def test_an_artefact_whose_block_holds_an_answer_is_read_from_its_block(
    timeline: Timeline,
) -> None:
    base = timeline.start(
        {GUIDE: bare_guide(at=T1, outcome="unchanged", because="the block answers")}
    )
    timeline.commit("an answer file beside", {answer_path("one"): answers(entry(at=T2))})
    result = _check(timeline)
    assert _points(result) == [base]
    report = _report(result)
    assert report.answers is not None and report.answers["home"] == "block"
    assert [r["file"] for r in report.answers["revalidations"]] == [None]


def test_a_value_moved_from_the_block_to_a_file_keeps_its_point(timeline: Timeline) -> None:
    base = timeline.start({GUIDE: bare_guide(at=T1, outcome="unchanged", because="holds")})
    timeline.commit(
        "move the answers",
        {
            GUIDE: bare_guide(),
            answer_path("moved-0123456789ab"): answers(entry(at=T1, because="holds")),
        },
    )
    assert _points(_check(timeline)) == [base]


def test_a_value_moved_to_another_file_keeps_its_point(timeline: Timeline) -> None:
    timeline.start({GUIDE: bare_guide()})
    first = timeline.commit("answer", {answer_path("one"): answers(entry(at=T1))})
    timeline.commit("answer again", {answer_path("two"): answers(entry(at=T1, read=("one",)))})
    result = _check(timeline)
    assert _points(result) == [first]
    assert [r["file"] for r in _answers(result)["revalidations"]] == ["two.yaml"]


def test_a_value_written_back_keeps_its_first_point(timeline: Timeline) -> None:
    timeline.start({GUIDE: bare_guide()})
    first = timeline.commit("answer", {answer_path("one"): answers(entry(at=T1))})
    changed = timeline.commit("change the CLI", {"src/cli/main.py": "print('v2')\n"})
    timeline.commit("answer it", {answer_path("two"): answers(entry(at=T2, read=("one",)))})
    timeline.commit(
        "write the first value back",
        {answer_path("three"): answers(entry(at=T1, read=("one", "two")))},
    )
    result = _check(timeline)
    assert _points(result) == [first]
    assert [(f.kind.value, f.origin.sha if f.origin else None) for f in result.findings] == [
        ("stale", changed)
    ]


def test_a_file_put_back_keeps_its_point(timeline: Timeline) -> None:
    timeline.start({GUIDE: bare_guide()})
    first = timeline.commit("answer", {answer_path("one"): answers(entry(at=T1))})
    timeline.commit("take it away", {answer_path("one"): None})
    timeline.commit("put it back", {answer_path("one"): answers(entry(at=T1))})
    assert _points(_check(timeline)) == [first]


def test_an_answer_follows_the_renames_of_its_artefacts_file(timeline: Timeline) -> None:
    timeline.start({"docs/old.md": bare_guide()})
    answered = timeline.commit("answer", {answer_path("one"): answers(entry("docs/old.md", at=T1))})
    timeline.rename("docs/old.md", GUIDE)
    result = _check(timeline)
    report = _report(result)
    assert report.answers is not None and report.answers["home"] == "files"
    assert [r["file"] for r in report.answers["revalidations"]] == ["one.yaml"]
    assert answered in _points(result)


def _collection(*ids: str) -> str:
    """A collection file whose entries, each anchored to the CLI, are `ids`."""
    entries = {
        entry_id: {"title": entry_id, "pkit": {"friction": {"anchors": {"path": ["src/cli/**"]}}}}
        for entry_id in ids
    }
    sections = "".join(f"## {entry_id}\n\nThe entry {entry_id}.\n\n" for entry_id in ids)
    return f"---\n{json.dumps(entries, indent=2)}\n---\n\n{sections}"


def test_an_entry_moved_between_collection_files_is_not_followed(timeline: Timeline) -> None:
    timeline.start({"docs/a.md": _collection("n1", "n2"), "docs/b.md": _collection("m1")})
    timeline.commit("answer", {answer_path("one"): answers(entry("docs/a.md#n1", at=T1))})
    timeline.commit(
        "move the entry",
        {"docs/a.md": _collection("n2"), "docs/b.md": _collection("m1", "n1")},
    )
    result = _check(timeline)
    report = _report(result, "docs/b.md#n1")
    assert report.answers is not None and report.answers["revalidations"] == []
    assert result.prunable == ("one.yaml",)


# --- answered apart --------------------------------------------------------------------


def _apart(timeline: Timeline) -> str:
    """Two lines of work answer the guide, neither reading the other; both merge."""
    repo = timeline.adopter
    timeline.start({GUIDE: bare_guide()})
    repo.checkout("one", create=True)
    timeline.commit("answer on one", {answer_path("one"): answers(entry(at=T1))})
    repo.checkout("main")
    repo.checkout("two", create=True)
    timeline.commit("answer on two", {answer_path("two"): answers(entry(at=T2))})
    repo.checkout("main")
    timeline.merge("one")
    return timeline.merge("two")


def test_two_revalidations_made_apart_are_debt_from_the_first_commit_holding_both(
    timeline: Timeline,
) -> None:
    both = _apart(timeline)
    result = _check(timeline)
    report = _report(result)
    assert report.state is fr.ArtefactState.CURRENT  # never stale
    (finding,) = [f for f in result.findings if f.kind is fr.RepositoryFindingKind.ANSWERED_APART]
    assert finding.origin is not None and finding.origin.sha == both
    assert finding.files == ("one.yaml", "two.yaml")
    assert not result.failed
    assert report.answers is not None and report.answers["answered_apart"] == [
        ["one.yaml", "two.yaml"]
    ]

    listing = frep.run_debt(timeline.adopter.root)
    assert [(e.finding.kind.value, e.origin.sha) for e in listing.entries] == [
        ("answered-apart", both)
    ]
    debt = json.loads(frep.render_debt_json(listing))
    assert debt["counts"]["answered-apart"] == 1
    assert debt["debt"][0]["files"] == ["one.yaml", "two.yaml"]


def test_a_revalidation_that_reads_both_clears_the_debt(timeline: Timeline) -> None:
    _apart(timeline)
    cleared = timeline.commit(
        "judge the combined state",
        {answer_path("three"): answers(entry(at=T3, read=("one", "two")))},
    )
    result = _check(timeline)
    assert _kinds(result) == []
    assert _points(result) == [cleared]
    assert result.prunable == ("one.yaml", "two.yaml")


def test_an_anchor_changed_since_only_one_of_two_apart_is_no_friction(
    timeline: Timeline,
) -> None:
    repo = timeline.adopter
    timeline.start({GUIDE: bare_guide()})
    repo.checkout("one", create=True)
    timeline.commit("answer on one", {answer_path("one"): answers(entry(at=T1))})
    repo.checkout("main")
    repo.checkout("two", create=True)
    timeline.commit("change the CLI", {"src/cli/main.py": "print('v2')\n"})
    timeline.commit("answer on two", {answer_path("two"): answers(entry(at=T2))})
    repo.checkout("main")
    timeline.merge("one")
    timeline.merge("two")
    result = _check(timeline)
    # The CLI differs from what it stood on at one's point, not at two's: measured as before.
    assert _kinds(result) == [("answered-apart", None)]


def test_a_void_name_keeps_the_answer_it_named_live(timeline: Timeline) -> None:
    timeline.start({GUIDE: bare_guide()})
    # A name first carried before the file it names was added: history does not agree.
    timeline.commit(
        "answer naming ahead", {answer_path("two"): answers(entry(at=T2, read=("one",)))}
    )
    timeline.commit("answer", {answer_path("one"): answers(entry(at=T1))})
    result = _check(timeline)
    assert _kinds(result) == [("answered-apart", None)]


def test_a_name_carried_on_two_lines_is_honoured_where_one_agrees(timeline: Timeline) -> None:
    repo = timeline.adopter
    timeline.start({GUIDE: bare_guide()})
    timeline.commit("answer", {answer_path("one"): answers(entry(at=T1))})
    repo.checkout("topic", create=True)
    picked = timeline.commit(
        "answer again", {answer_path("two"): answers(entry(at=T2, read=("one",)))}
    )
    repo.checkout("main")
    repo.checkout("other", create=True)
    timeline.cherry_pick(picked)
    repo.checkout("main")
    timeline.merge("topic")
    timeline.merge("other")
    result = _check(timeline)
    assert _kinds(result) == []
    assert [r["file"] for r in _answers(result)["revalidations"]] == ["two.yaml"]


# --- deferrals in answer files ---------------------------------------------------------


def test_a_deferral_in_an_answer_file_covers_its_anchor_until_it_changes_again(
    timeline: Timeline,
) -> None:
    timeline.start({GUIDE: bare_guide()})
    timeline.commit("answer", {answer_path("one"): answers(entry(at=T1))})
    timeline.commit("change the CLI", {"src/cli/main.py": "print('v2')\n"})
    deferred = timeline.commit(
        "defer the CLI",
        {answer_path("two"): answers(entry(read=("one",), deferred=((CLI, "until #12"),)))},
    )
    result = _check(timeline)
    assert [
        (f.kind.value, f.origin.sha if f.origin else None, f.reason) for f in result.findings
    ] == [("deferred", deferred, "until #12")]
    assert _report(result).state is fr.ArtefactState.DEFERRED

    again = timeline.commit("change the CLI again", {"src/cli/main.py": "print('v3')\n"})
    result = _check(timeline)
    assert [(f.kind.value, f.origin.sha if f.origin else None) for f in result.findings] == [
        ("stale", again),
        ("deferred", deferred),
    ]


def test_a_deferral_moved_out_of_the_block_keeps_its_point(timeline: Timeline) -> None:
    timeline.start({GUIDE: bare_guide(at=T1, outcome="unchanged", because="holds")})
    timeline.commit("change the CLI", {"src/cli/main.py": "print('v2')\n"})
    deferred = timeline.commit(
        "defer in the block",
        {
            GUIDE: bare_guide(
                at=T1,
                outcome="unchanged",
                because="holds",
                deferred=[("path", "src/cli/**", "until #12")],
            )
        },
    )
    timeline.commit(
        "move the answers",
        {
            GUIDE: bare_guide(),
            answer_path("moved-0123456789ab"): answers(
                entry(at=T1, because="holds", deferred=((CLI, "until #12"),))
            ),
        },
    )
    result = _check(timeline)
    assert [(f.kind.value, f.origin.sha if f.origin else None) for f in result.findings] == [
        ("deferred", deferred)
    ]


def test_a_revalidation_made_apart_does_not_reach_a_deferral(timeline: Timeline) -> None:
    repo = timeline.adopter
    timeline.start({GUIDE: bare_guide()})
    timeline.commit("answer", {answer_path("one"): answers(entry(at=T1))})
    repo.checkout("defer", create=True)
    timeline.commit("change the CLI", {"src/cli/main.py": "print('v2')\n"})
    timeline.commit(
        "defer the CLI",
        {answer_path("two"): answers(entry(read=("one",), deferred=((CLI, "until #12"),)))},
    )
    repo.checkout("main")
    repo.checkout("other", create=True)
    timeline.commit("revalidate", {answer_path("three"): answers(entry(at=T2, read=("one",)))})
    repo.checkout("main")
    timeline.merge("other")
    timeline.merge("defer")
    result = _check(timeline)
    # The revalidation read neither the deferral's file nor keeps it: the deferral is
    # not reached, so it still answers the CLI's change, which happened after one.
    (deferral,) = _answers(result)["deferrals"]
    assert (deferral["file"], deferral["kept"]) == ("two.yaml", False)
    assert [k for k, _a in _kinds(result)] == ["deferred"]


# --- the folder is never a place, an anchor's file or surface --------------------------


def test_no_anchor_stands_on_an_answer_file(timeline: Timeline) -> None:
    timeline.start(
        {
            GUIDE: document(
                "guide",
                anchors={"path": [".pkit/project/**"]},
                at=T1,
                outcome="unchanged",
                because="holds",
            ),
            "docs/folder.md": document(
                "folder", anchors={"path": [f"{FOLDER}/**"]}, at=T1, outcome="updated"
            ),
        },
        friction_config(surface=[".pkit/project"]),
    )
    timeline.commit("an answer file", {answer_path("one"): answers(entry("docs/x.md", at=T1))})
    result = _check(timeline)
    assert ("stale", ".pkit/project/**") not in _kinds(result)
    (dead,) = [f for f in result.findings if f.kind is fr.RepositoryFindingKind.DEAD_ANCHOR]
    assert dead.location == "docs/folder.md" and "only answer files" in dead.message
    # The declared surface leaves the answer files out (COR-050 point 8).
    assert result.surface == 1 and result.uncovered == ()


def test_no_place_reads_a_file_in_the_answer_folder(timeline: Timeline) -> None:
    timeline.start(
        {f"{FOLDER}/notes.md": document("notes", anchors={"path": ["src/**"]})},
        friction_config(places=("docs", ".pkit/project")),
    )
    result = _check(timeline)
    assert result.artefacts == 0


# --- validation --------------------------------------------------------------------------


def _validate(timeline: Timeline) -> list[tuple[str, str, str]]:
    result = fv.validate_friction(timeline.adopter.root)
    return [
        (f.location, f.kind.value, f.severity.value)
        for f in result.findings
        if f.kind in fv.ANSWER_KINDS
    ]


def test_validation_fails_what_cannot_be_read_and_what_departs_from_the_schema(
    timeline: Timeline,
) -> None:
    timeline.start({GUIDE: bare_guide()})
    timeline.adopter.write(
        {
            answer_path("broken"): "answers: [unclosed\n",
            answer_path("unknown"): answers({**entry(at=T1), "colour": "red"}),
            answer_path("empty"): '{"answers": []}\n',
        }
    )
    assert sorted(_validate(timeline)) == [
        (answer_path("broken"), "unreadable-answer-file", "error"),
        (answer_path("empty"), "malformed-answer-file", "error"),
        (answer_path("unknown"), "malformed-answer-file", "error"),
    ]


def test_validation_fails_repeats_and_two_answers_naming_each_other(timeline: Timeline) -> None:
    timeline.start({GUIDE: bare_guide()})
    timeline.adopter.write(
        {
            answer_path("twice"): answers(entry(at=T1), entry(at=T2)),
            answer_path("again"): answers(entry(deferred=((CLI, "until #1"), (CLI, "until #2")))),
            answer_path("x"): answers(entry(at=T1, read=("y",))),
            answer_path("y"): answers(entry(at=T2, read=("x",))),
        }
    )
    assert sorted(_validate(timeline)) == [
        (answer_path("again"), "duplicate-answer-deferral", "error"),
        (answer_path("twice"), "duplicate-answer-entry", "error"),
        (answer_path("x"), "mutual-read", "error"),
        (answer_path("y"), "mutual-read", "error"),
    ]


def test_an_answer_on_what_is_gone_is_reported_never_failed(timeline: Timeline) -> None:
    timeline.start({GUIDE: bare_guide()})
    timeline.adopter.write(
        {
            answer_path("gone"): answers(entry("docs/nothing.md", at=T1)),
            answer_path("undeclared"): answers(
                entry(deferred=((Anchor("path", "src/gone/**"), "until #3"),))
            ),
        }
    )
    assert sorted(_validate(timeline)) == [
        (answer_path("gone"), "answer-on-what-is-gone", "report"),
        (answer_path("undeclared"), "answer-on-what-is-gone", "report"),
    ]


def test_a_revisit_entry_on_an_artefact_no_link_reads_is_reported_gone(
    timeline: Timeline,
) -> None:
    """The guide declares no link, so a revisit entry on it takes no target: the reading
    of a state holds it not live, and validation reports it, as the prune counts it."""
    timeline.start({GUIDE: bare_guide()})
    timeline.adopter.write(
        {answer_path("revisit"): answers(entry(revisited=((CLI, "unchanged", "holds"),)))}
    )
    assert _validate(timeline) == [(answer_path("revisit"), "answer-on-what-is-gone", "report")]


class _NoLinks:
    """A discovery that is never asked for an artefact's links."""

    def links(self, artefact: object) -> tuple[()]:
        raise AssertionError(f"asked for the links of {artefact}")


def test_an_artefact_no_entry_names_is_judged_without_its_links() -> None:
    """An artefact no answer names has nothing to judge, so its links are not read: the
    reading costs nothing where no answer file names it (#1871)."""
    one = af.read_answer_file("one.yaml", answers(entry("docs/other.md", at=T1)).encode())
    state = af.StateAnswers(
        {"one.yaml": one},
        lambda _reader, _named: True,
        lambda artefact: (artefact.location,),
    )

    class _Guide:
        location = GUIDE
        path = GUIDE
        anchors: Mapping[str, tuple[str, ...]] = {"path": ("src/cli/**",)}

    judged = state.liveness(cast(Any, _Guide()), cast(Any, _NoLinks()))
    assert judged.entries == () and judged.revisits == ()


def test_validation_follows_a_location_through_a_rename(timeline: Timeline) -> None:
    timeline.start({"docs/old.md": bare_guide()})
    timeline.commit("answer", {answer_path("one"): answers(entry("docs/old.md", at=T1))})
    timeline.rename("docs/old.md", GUIDE)
    assert _validate(timeline) == []


def test_validation_says_nothing_without_answer_files(timeline: Timeline) -> None:
    timeline.start({GUIDE: bare_guide()})
    assert _validate(timeline) == []


# --- the machine-readable outputs --------------------------------------------------------


def test_explain_gives_the_live_answers_with_their_points(timeline: Timeline) -> None:
    timeline.start({GUIDE: bare_guide()})
    answered = timeline.commit("answer", {answer_path("one"): answers(entry(at=T1))})
    result = CliRunner().invoke(main, ["friction", "explain", "guide", "--json"])
    assert result.exit_code == 0, result.output
    doc = json.loads(result.output)
    assert doc["answers_folder"] == FOLDER
    assert doc["answers"]["home"] == "files"
    (revalidation,) = doc["answers"]["revalidations"]
    assert (revalidation["file"], revalidation["at"], revalidation["outcome"]) == (
        "one.yaml",
        T1,
        "unchanged",
    )
    assert [p["commit"] for p in revalidation["points"]] == [answered]


def test_the_check_counts_the_files_a_prune_would_remove(timeline: Timeline) -> None:
    timeline.start({GUIDE: bare_guide()})
    timeline.commit("answer", {answer_path("one"): answers(entry(at=T1))})
    timeline.commit("answer again", {answer_path("two"): answers(entry(at=T2, read=("one",)))})
    result = CliRunner().invoke(main, ["friction", "check", "--all", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["answers"] == {
        "folder": FOLDER,
        "files": 2,
        "prunable": ["one.yaml"],
    }


def test_the_data_binding_never_claims_an_answer_file(timeline: Timeline) -> None:
    from project_kit import data_validate

    timeline.start({GUIDE: bare_guide(), CONFIG: friction_config()})
    timeline.adopter.write({answer_path("one"): answers({**entry(at=T1), "colour": "red"})})
    root = timeline.adopter.root
    assert all(
        not af.is_answer_file(p.relative_to(root).as_posix())
        for p in data_validate.discover_repository_data_files(root)
    )
    report = data_validate.validate_path(root / answer_path("one"), root)
    assert report.files_checked == 1 and report.has_errors
