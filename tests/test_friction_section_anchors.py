"""Tests for anchors on one section of a document, or on its lead (Task #1423; COR-050
points 2, 5 to 7, 9, 11 to 13).

An anchor `docs/manual.md#using` stands on the section headed `Using`, its heading
and its text, and on the document's own fields; `docs/manual.md#` stands on its
lead, the body before its first heading, a first-level title that opens it
included. The change check, the whole-repository check and the debt listing read
it through one reading (`artefact_parts`), so they agree: a changed section flags
its dependants, a change elsewhere flags none, a move holds, and a renamed
heading leaves a dead anchor the change owns. A slug two headings share is
ambiguous. A section or the lead of a collection file, a collection entry, an
extension point or a record is refused, each with its reason and the anchor to
use, and validation fails every dead, ambiguous or refused part anchor. An
anchor on a part of its own artefact is a cycle.

The checks' tests stand up a real adopter repository, commit a base on `main`
with the manual and a guide anchored to its section, revalidated there, branch
`feature` off it and commit one change.
"""

from __future__ import annotations

from typing import Any

import pytest

from project_kit import artefact_parts as ap
from project_kit import friction_check as fc
from project_kit import friction_discovery as fd
from project_kit import friction_report as frep
from project_kit import friction_repository as fr
from project_kit import friction_validate as fv
from project_kit.document_parts import heading_slug
from project_kit.friction_check import record_naming
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.friction_documents import (
    CONFIG,
    MANUAL,
    POINTED,
    SECTIONS,
    T2,
    Timeline,
    document,
    friction_config,
    guide,
    manual,
    pointed_record,
)

ON_SECTION = {"artefact": ["docs/manual.md#using"]}
ON_LEAD = {"artefact": ["docs/manual.md#"]}


@pytest.fixture
def timeline(make_adopter_repo: MakeAdopterRepo) -> Timeline:
    return Timeline(make_adopter_repo())


def _start(timeline: Timeline, anchors: dict[str, list[str]] | None = None, **kept: Any) -> str:
    """The base on `main`: the manual, and `guide` anchored to its `Using` section and
    revalidated there; then the branch `feature` off it."""
    base = timeline.start(
        {MANUAL: manual(**kept), "docs/guide.md": guide(anchors=anchors or ON_SECTION)}
    )
    timeline.adopter.checkout("feature", create=True)
    return base


def _change(timeline: Timeline, **changed: Any) -> str:
    return timeline.commit("change the manual", {MANUAL: manual(**changed)})


def _edited(heading: str, text: str) -> tuple[tuple[str, str], ...]:
    return tuple((name, text if name == heading else words) for name, words in SECTIONS)


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


# --- a section's dependants, read alike by the change check, the whole-repository check
# --- and debt


def test_a_changed_section_flags_its_dependants_in_every_check(timeline: Timeline) -> None:
    _start(timeline)
    changed = _change(timeline, sections=_edited("Using", "Run the tool with care."))
    assert _change_check(timeline) == [("friction", "docs/manual.md#using")]
    assert _repository(timeline) == [("stale", "docs/manual.md#using", changed)]
    assert _debt(timeline) == [("stale", "docs/manual.md#using", changed)]


@pytest.mark.parametrize(
    "changed",
    [
        pytest.param({"sections": _edited("Installing", "Run the new installer.")}, id="section"),
        pytest.param({"lead": "What the manual is for, and for whom."}, id="lead"),
        pytest.param({"sections": (*SECTIONS, ("Appendix", "More."))}, id="added-section"),
    ],
)
def test_a_change_elsewhere_in_the_page_flags_none_in_any_check(
    timeline: Timeline, changed: dict[str, Any]
) -> None:
    _start(timeline)
    _change(timeline, **changed)
    assert _change_check(timeline) == []
    assert _repository(timeline) == []
    assert _debt(timeline) == []


def test_a_change_to_the_document_s_own_fields_flags_the_dependants_of_its_parts(
    timeline: Timeline,
) -> None:
    _start(timeline)
    changed = _change(timeline, title="A retitled manual")
    assert _change_check(timeline) == [("friction", "docs/manual.md#using")]
    assert _repository(timeline) == [("stale", "docs/manual.md#using", changed)]


def test_a_moved_section_holds_in_every_check(timeline: Timeline) -> None:
    _start(timeline)
    _change(timeline, sections=(SECTIONS[1], SECTIONS[0], SECTIONS[2]))
    assert _change_check(timeline) == []
    assert _repository(timeline) == []
    assert _debt(timeline) == []


def test_a_section_edited_and_put_back_is_no_change(timeline: Timeline) -> None:
    _start(timeline)
    _change(timeline, sections=_edited("Using", "Run the tool with care."))
    _change(timeline)
    assert _change_check(timeline) == []
    assert _repository(timeline) == []


def test_the_origin_is_where_the_section_changed_not_the_page_s_last_edit(
    timeline: Timeline,
) -> None:
    _start(timeline)
    changed = _change(timeline, sections=_edited("Using", "Run the tool with care."))
    later = tuple(
        (name, "Ask the team." if name == "Troubleshooting" else words)
        for name, words in _edited("Using", "Run the tool with care.")
    )
    _change(timeline, sections=later)
    assert _repository(timeline) == [("stale", "docs/manual.md#using", changed)]


def test_an_anchor_on_the_lead_changes_only_with_the_lead(timeline: Timeline) -> None:
    _start(timeline, anchors=ON_LEAD)
    _change(timeline, sections=_edited("Using", "Run the tool with care."))
    assert _change_check(timeline) == []
    changed = _change(
        timeline,
        sections=_edited("Using", "Run the tool with care."),
        lead="What the manual is for, and for whom.",
    )
    assert _change_check(timeline) == [("friction", "docs/manual.md#")]
    assert _repository(timeline) == [("stale", "docs/manual.md#", changed)]


def test_a_section_named_through_the_document_s_id_follows_it_across_a_rename(
    timeline: Timeline,
) -> None:
    _start(timeline, anchors={"artefact": ["manual#using"]})
    timeline.rename(MANUAL, "docs/handbook.md")
    assert _change_check(timeline) == []
    assert _repository(timeline) == []


def test_a_whole_artefact_anchor_still_changes_with_any_edit(timeline: Timeline) -> None:
    _start(timeline, anchors={"artefact": ["docs/manual.md", "docs/manual.md#using"]})
    changed = _change(timeline, sections=_edited("Installing", "Run the new installer."))
    assert _change_check(timeline) == [("friction", "docs/manual.md")]
    assert _repository(timeline) == [("stale", "docs/manual.md", changed)]


# --- a renamed heading, a shared slug -------------------------------------------------


def test_a_renamed_heading_leaves_a_dead_anchor_the_change_owns(timeline: Timeline) -> None:
    _start(timeline)
    renamed = tuple(("Running" if name == "Using" else name, words) for name, words in SECTIONS)
    _change(timeline, sections=renamed)
    result = fc.run_change_check(timeline.adopter.root, "main")
    (dead,) = result.findings
    assert (dead.kind, dead.anchor and dead.anchor.value) == (
        fc.FindingKind.DEAD_ANCHOR,
        "docs/manual.md#using",
    )
    assert dead.message == (
        "docs/manual.md has no heading whose slug is using; the diff renamed or removed its heading"
    )
    assert _repository(timeline) == [("dead-anchor", "docs/manual.md#using", None)]
    (error,) = fv.validate_friction(timeline.adopter.root).errors
    assert error.kind is fv.FrictionFindingKind.DEAD_SECTION_ANCHOR
    assert error.pointer == "/pkit/friction/anchors/artefact/0"
    assert "re-point the anchor" in error.message


def test_an_anchor_made_ambiguous_is_the_change_s(timeline: Timeline) -> None:
    _start(timeline)
    _change(timeline, sections=(*SECTIONS, ("Using", "Using it again.")))
    (ambiguous,) = fc.run_change_check(timeline.adopter.root, "main").findings
    assert ambiguous.kind is fc.FindingKind.DEAD_ANCHOR
    assert ambiguous.message == (
        "is ambiguous: 2 headings of docs/manual.md have the slug using; the diff gave another "
        "heading its slug"
    )
    ((kind, value, _origin),) = _repository(timeline)
    assert (kind, value) == ("dead-anchor", "docs/manual.md#using")
    (error,) = fv.validate_friction(timeline.adopter.root).errors
    assert error.kind is fv.FrictionFindingKind.AMBIGUOUS_SECTION_ANCHOR


def test_an_anchor_added_on_a_missing_section_is_the_change_s(timeline: Timeline) -> None:
    _start(timeline)
    timeline.commit(
        "anchor a section the manual lacks",
        {
            "docs/guide.md": guide(
                anchors={"artefact": ["docs/manual.md#using", "docs/manual.md#upgrading"]},
                at=T2,
                because="anchored one more section",
            )
        },
    )
    findings = fc.run_change_check(timeline.adopter.root, "main").findings
    (dead,) = [f for f in findings if f.kind is fc.FindingKind.DEAD_ANCHOR]
    assert dead.message == (
        "docs/manual.md has no heading whose slug is upgrading; the anchor was added in this diff"
    )


def test_an_anchor_refused_because_the_change_made_a_collection_file_is_the_change_s(
    timeline: Timeline,
) -> None:
    """COR-050 point 12: a refused anchor is the change's when the change made what it
    names a collection file, whose entries are named by their ids."""
    _start(timeline)
    collection = (
        '---\n{"using": {"meaning": "how to use it", "pkit": {"friction": {"anchors": '
        '{"path": ["src/**"]}}}}}\n---\n\n# Manual\n\n## using\n\nRun the tool.\n'
    )
    timeline.commit("make the manual a collection", {MANUAL: collection})
    findings = fc.run_change_check(timeline.adopter.root, "main").findings
    (refused,) = [f for f in findings if f.kind is fc.FindingKind.DEAD_ANCHOR]
    assert refused.message == (
        "is refused: docs/manual.md is a collection file, whose entries are artefacts, each "
        "named by its id — use the artefact anchor using; the diff made docs/manual.md a "
        "collection file"
    )


# --- the explanation ----------------------------------------------------------------


def test_the_explanation_shows_the_section_s_diff_alone(timeline: Timeline) -> None:
    base = _start(timeline)
    both = tuple(
        (name, "Run the new installer." if name == "Installing" else words)
        for name, words in _edited("Using", "Run the tool with care.")
    )
    _change(timeline, sections=both)
    explanation = frep.run_explain(timeline.adopter.root, "docs/guide.md")
    (anchor,) = explanation.anchors
    assert anchor.state == "stale" and anchor.diff is not None
    assert anchor.diff[:2] == (
        f"--- docs/manual.md#using at {base[:12]}",
        "+++ docs/manual.md#using at HEAD",
    )
    changed = [line for line in anchor.diff if line[:1] in "+-" and line[:3] not in ("---", "+++")]
    assert changed == ["-Run the tool.", "+Run the tool with care."]
    human = frep.render_explain_human(explanation)
    assert "what the section stands on, from its revalidation point to HEAD:" in human
    assert "Run the new installer." not in human


def test_a_deferral_covers_a_section_as_it_stood(timeline: Timeline) -> None:
    _start(timeline)
    changed = timeline.commit(
        "change Using, and defer the guide",
        {
            MANUAL: manual(sections=_edited("Using", "Run the tool with care.")),
            "docs/guide.md": guide(
                anchors=ON_SECTION,
                deferred=[("artefact", "docs/manual.md#using", "rewrite after #1")],
            ),
        },
    )
    assert _change_check(timeline) == [("answered", "docs/manual.md#using")]
    assert _repository(timeline) == [("deferred", "docs/manual.md#using", changed)]


# --- validation, and what the reading refuses -----------------------------------------


@pytest.fixture
def adopter(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    return make_adopter_repo()


TERMS = """---
title: Terms
term-a:
  meaning: the first term
  pkit:
    friction:
      anchors: {path: [src/**]}
term-b:
  meaning: the second term
---

# Terms

## term-a

The first term.

### Usage

How to use it.

## term-b

The second term.
"""

DOC_RULES = (
    "---\nrule-set: DOC\nversion: 1.0.0\nrules:\n"
    "  RS-DOC-001: {status: proposed, offers: [labels]}\n---\n\n"
    "# Documentation rules\n\n## RS-DOC-001 — Say who reads it\n\nName the reader.\n"
)


def _page(*values: str) -> str:
    return document("page", anchors={"artefact": list(values)}, body="# Page\n\nThe page.")


def _write(adopter: AdopterRepo, *values: str, **files: str) -> None:
    twice = manual(sections=(*SECTIONS, ("Using", "Using it again.")))
    adopter.write(
        {
            CONFIG: friction_config(places=("docs", ".pkit/decisions/project")),
            MANUAL: manual(),
            "docs/twice.md": twice.replace('"manual"', '"twice"'),
            "docs/terms.md": TERMS,
            "docs/rule-sets/doc.md": DOC_RULES,  # the internal root's rule sets
            POINTED: pointed_record(),
            "docs/page.md": _page(*values),
            **files,
        }
    )


def _errors(adopter: AdopterRepo) -> list[tuple[str, str, str]]:
    return [
        (f.kind.value, f.pointer.rsplit("/", 1)[-1], f.message)
        for f in fv.validate_friction(adopter.root).errors
    ]


def test_validation_fails_dead_ambiguous_and_refused_part_anchors(adopter: AdopterRepo) -> None:
    _write(
        adopter,
        "docs/manual.md#using",  # 0: a live section
        "docs/manual.md#",  # 1: the lead
        "docs/manual.md#upgrading",  # 2: no heading has the slug
        "docs/gone.md#installing",  # 3: no artefact by the name
        "docs/twice.md#using",  # 4: two headings share the slug
        "docs/terms.md#usage",  # 5: a collection file; the entry whose section holds it
        "docs/terms.md#term-b",  # 6: a collection file; the entry by its id
        "term-a#usage",  # 7: a collection entry
        "RS-DOC-001#labels",  # 8: an extension point
        "PRJ-900#2",  # 9: a record; the point by its id
        "PRJ-900#2-second",  # 10: a record; the point whose heading has the slug
        "PRJ-900#context",  # 11: a record; no point, so the whole record
        "docs/nothing.md",  # 12: a whole anchor that names nothing: the checks' finding
        "RS-DOC-001#say-who-reads-it",  # 13: a rule's section, which it offers as no point
    )
    errors = _errors(adopter)
    assert [(kind, index) for kind, index, _message in errors] == [
        ("dead-section-anchor", "2"),
        ("dead-section-anchor", "3"),
        ("ambiguous-section-anchor", "4"),
        ("refused-section-anchor", "5"),
        ("refused-section-anchor", "6"),
        ("refused-section-anchor", "7"),
        ("refused-section-anchor", "8"),
        ("refused-section-anchor", "9"),
        ("refused-section-anchor", "10"),
        ("refused-section-anchor", "11"),
        ("refused-section-anchor", "13"),
    ]
    messages = {index: message for _kind, index, message in errors}
    assert messages["2"] == (
        "artefact anchor 'docs/manual.md#upgrading' is dead: docs/manual.md has no heading whose "
        "slug is upgrading (COR-050 point 7). A renamed heading leaves its anchors dead: re-point "
        "the anchor, which a revalidation records."
    )
    assert messages["3"] == (
        "artefact anchor 'docs/gone.md#installing' is dead: names no artefact in the declared "
        "places (COR-050 point 7)."
    )
    assert messages["4"].startswith(
        "artefact anchor 'docs/twice.md#using' is ambiguous: 2 headings of docs/twice.md have the "
        "slug using"
    )
    assert messages["5"] == (
        "artefact anchor 'docs/terms.md#usage' is refused: docs/terms.md is a collection file, "
        "whose entries are artefacts, each named by its id — use the artefact anchor term-a "
        "(COR-050 point 2)."
    )
    assert "use the artefact anchor term-b" in messages["6"]
    assert messages["7"] == (
        "artefact anchor 'term-a#usage' is refused: term-a is a collection entry, cited whole by "
        "its id — use the artefact anchor term-a (COR-050 point 2)."
    )
    assert messages["8"] == (
        "artefact anchor 'RS-DOC-001#labels' is refused: #labels names an extension point of the "
        "rule RS-DOC-001, which is no anchor value (COR-051 point 3) — use the artefact anchor "
        "RS-DOC-001 (COR-050 point 2)."
    )
    assert messages["9"] == (
        "artefact anchor 'PRJ-900#2' is refused: PRJ-900 is a record, whose parts are its points "
        "— use the record anchor PRJ-900#2 (COR-050 point 2)."
    )
    assert messages["10"].endswith("— use the record anchor PRJ-900#2 (COR-050 point 2).")
    assert messages["11"].endswith("— use the record anchor PRJ-900 (COR-050 point 2).")
    assert messages["13"] == (
        "artefact anchor 'RS-DOC-001#say-who-reads-it' is refused: RS-DOC-001 is a collection "
        "entry, cited whole by its id — use the artefact anchor RS-DOC-001 (COR-050 point 2)."
    )


def test_the_lead_of_a_collection_file_is_refused_naming_no_entry(adopter: AdopterRepo) -> None:
    _write(adopter, "docs/terms.md#")
    ((kind, _index, message),) = _errors(adopter)
    assert kind == "refused-section-anchor"
    assert message.endswith("— anchor one of its entries by its id (COR-050 point 2).")


def test_an_anchor_on_a_part_of_its_own_artefact_is_a_cycle(adopter: AdopterRepo) -> None:
    _write(adopter, "docs/page.md#", "page#page")
    (cycle,) = fv.validate_friction(adopter.root).errors
    assert cycle.kind is fv.FrictionFindingKind.CYCLE
    assert cycle.message == (
        "the artefact anchors a section or the lead of itself ('docs/page.md#', 'page#page'), "
        "which is a cycle: its own edits would flag it, and so would its own revalidation — "
        "anchor what lies outside it (COR-050 point 5)."
    )


def test_an_artefact_anchoring_itself_whole_and_by_a_part_is_told_both(
    adopter: AdopterRepo,
) -> None:
    _write(adopter, "docs/page.md", "docs/page.md#")
    (cycle,) = fv.validate_friction(adopter.root).errors
    assert cycle.message.startswith(
        "the artefact anchors itself, and a section or the lead of itself ('docs/page.md', "
        "'docs/page.md#'), which is a cycle"
    )


def test_a_cycle_through_a_section_counts_as_one_through_the_artefact(
    adopter: AdopterRepo,
) -> None:
    other = document("other", anchors={"artefact": ["page#page"]}, body="# Other\n\nOther.")
    _write(adopter, "other#other", **{"docs/other.md": other})
    (cycle,) = fv.validate_friction(adopter.root).errors
    assert cycle.kind is fv.FrictionFindingKind.CYCLE
    assert "other -> page -> other" in cycle.message


# --- the one reading of an artefact anchor's part ---------------------------------------


def _read(adopter: AdopterRepo, value: str) -> ap.AnchoredPart:
    discovery = fd.discover_artefacts(adopter.root)
    return ap.anchored_part(discovery, value, lambda path: record_naming(adopter.root, path))


def test_a_section_and_the_lead_resolve_to_their_spans(adopter: AdopterRepo) -> None:
    _write(adopter)
    lines = manual().split("\n")
    section = _read(adopter, "docs/manual.md#using")
    assert section.state is ap.PartState.LIVE and section.span is not None
    assert lines[section.span.first_line - 1 : section.span.last_line] == [
        "## Using",
        "",
        "Run the tool.",
    ]
    lead = _read(adopter, "docs/manual.md#")
    assert lead.state is ap.PartState.LIVE and lead.span is not None
    assert lines[lead.span.first_line - 1 : lead.span.last_line] == [
        "# Manual",
        "",
        "What the manual is for.",
    ]
    by_id = _read(adopter, "manual#using")
    assert (by_id.state, by_id.span) == (ap.PartState.LIVE, section.span)


def test_an_empty_slug_names_no_section_and_a_bare_hash_is_the_lead(adopter: AdopterRepo) -> None:
    """A heading made only of symbols has an empty slug: no anchor names it, and a bare
    `#` never meets it, since it names the lead."""
    assert heading_slug("!!!") == ""
    assert heading_slug("!!! ???") == "-"  # a space is kept, as a hyphen
    symbols = manual(sections=(("!!!", "Only symbols."), *SECTIONS))
    _write(adopter, **{MANUAL: symbols})
    lead = _read(adopter, "docs/manual.md#")
    assert lead.state is ap.PartState.LIVE
    assert lead.standing is not None and "Only symbols." not in lead.standing.section
    assert lead.standing.section == "# Manual\n\nWhat the manual is for.\n"


def test_a_value_that_names_an_artefact_whole_is_read_whole(adopter: AdopterRepo) -> None:
    hashed = document("notes#1", body="# Notes\n\nNotes.")
    _write(adopter, **{"docs/hashed.md": hashed})
    found = _read(adopter, "notes#1")
    assert (found.state, found.names_part, found.target and found.target.path) == (
        ap.PartState.WHOLE,
        False,
        "docs/hashed.md",
    )


def test_a_part_stands_on_its_text_and_the_document_s_own_fields_only(
    adopter: AdopterRepo,
) -> None:
    _write(adopter)
    standing = _read(adopter, "docs/manual.md#using").standing
    assert standing is not None
    assert standing.section == "## Using\n\nRun the tool.\n"
    assert standing.fields == (("id", '"manual"'), ("title", '"A manual"'))
    assert standing.shared == ""


def test_truth_chain_order_follows_a_part_anchor_to_its_artefact(adopter: AdopterRepo) -> None:
    downstream = document("aaa", anchors={"artefact": ["page#"]}, body="Downstream.")
    _write(adopter, **{"docs/aaa.md": downstream})
    discovery = fd.discover_artefacts(adopter.root)
    head = fc.Side(adopter.root, fc.WorkingTree(adopter.root), discovery)
    order = [discovery.artefacts[i].id for i in fc.truth_chain_order(discovery, head.record_path)]
    assert order.index("page") < order.index("aaa")
