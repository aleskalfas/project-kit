"""The warning on a whole anchor beside anchors on its parts, `pkit friction check --all`
(ADR-080 point 5; #2659).

An artefact may anchor a record or a document whole and parts of it too. Whatever flags a
part anchor then flags the whole anchor, so the part anchors ask nothing it does not. The
check names each such whole anchor, with the anchors on parts beside it, from HEAD alone.
Every test lays down a real history on an adopter whose install is committed once per
session (`committed_adopter`).

Held to: a whole document beside its sections or its lead, and a whole record beside its
points; each named by its id or by its path, by any of the anchors that name it whole, a
path anchor on its one file among them; each whole anchor a finding of its own, naming only
its own parts; its message giving both moves, the safe one first. Not named: parts alone, a
whole anchor alone, a part of something else, a glob and a folder, a section beside its own
sub-section, a dead or retired part, a collection entry and an artefact that owes no answer.
It reads HEAD alone: no history and no number, one commit enough, and the commits after it
moving nothing. It owes nothing: no state, no debt, no failure in enforcing mode, and no
finding of the change check. And the finding as the views show it: its row, its count and
its legend in the human view, the `parts` key of both JSON documents, and what clears it in
the explanation. That a registered value is on neither side is `test_friction_anchor_kinds`'s,
and the tracking issue's `test_friction_report_body`'s.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from project_kit import friction_check as fc
from project_kit import friction_report as frep
from project_kit import friction_repository as fr
from project_kit.friction_discovery import Anchor
from tests.adopter_repo import AdopterRepo
from tests.friction_documents import (
    ADR,
    ADR_OVERLAY,
    MANUAL,
    POINTED,
    T1,
    Timeline,
    adr,
    document,
    friction_config,
    guide,
    manual,
    pointed_record,
)

#: The documents here say each artefact's answers beside its anchors, and each write
#: takes them into answer files, as a change writes them (COR-062 point 1).
pytestmark = pytest.mark.usefixtures("answers_in_files")

GUIDE = "docs/guide.md"
KIND = fr.RepositoryFindingKind.WHOLE_AND_PARTS
WHOLE = Anchor("artefact", MANUAL)
USING = Anchor("artefact", f"{MANUAL}#using")
LEAD = Anchor("artefact", f"{MANUAL}#")
RECORD = Anchor("record", "PRJ-900")
POINT = Anchor("record", "PRJ-900#2")


@pytest.fixture
def timeline(committed_adopter: AdopterRepo) -> Timeline:
    return Timeline(committed_adopter)


def _start(timeline: Timeline, anchors: dict[str, list[str]], config: str | None = None) -> str:
    """One commit: the manual, the pointed record, and `guide` anchored by `anchors`."""
    files = {MANUAL: manual(), POINTED: pointed_record(), GUIDE: guide(anchors=anchors)}
    return timeline.start(files, config)


def _named(timeline: Timeline) -> dict[Anchor | None, tuple[Anchor, ...]]:
    """Each whole-and-parts finding's whole anchor, with the anchors on parts it names."""
    result = fr.run_repository_check(timeline.adopter.root)
    return {f.anchor: f.parts for f in result.findings if f.kind is KIND}


def _json(root: Path) -> dict[str, Any]:
    return json.loads(fr.render_json(fr.run_repository_check(root)))


# --- what it names ------------------------------------------------------------------------


def test_a_whole_document_beside_its_sections_and_lead_is_named_with_both_anchors(
    timeline: Timeline,
) -> None:
    _start(timeline, {"artefact": [MANUAL, USING.value, LEAD.value]})

    (finding,) = [
        f for f in fr.run_repository_check(timeline.adopter.root).findings if f.kind is KIND
    ]
    assert (finding.artefact, finding.location) == ("guide", GUIDE)
    assert (finding.anchor, finding.parts) == (WHOLE, (USING, LEAD))
    assert f"artefact {USING.value}, artefact {LEAD.value}" in finding.message
    assert finding.message.startswith(
        "anchors a record or document whole beside 2 anchors on its parts"
    )


def test_a_whole_record_beside_its_points_is_named(timeline: Timeline) -> None:
    _start(timeline, {"record": [RECORD.value, POINT.value]})
    assert _named(timeline) == {RECORD: (POINT,)}


@pytest.mark.parametrize(
    ("whole", "part"),
    [
        pytest.param(Anchor("artefact", "manual"), USING, id="the-whole-by-its-id"),
        pytest.param(WHOLE, Anchor("artefact", "manual#using"), id="the-part-by-its-id"),
        pytest.param(Anchor("path", MANUAL), USING, id="a-path-anchor-on-the-document"),
        pytest.param(Anchor("path", POINTED), POINT, id="a-path-anchor-on-the-record"),
    ],
)
def test_any_anchor_that_stands_on_the_file_whole_is_named(
    timeline: Timeline, whole: Anchor, part: Anchor
) -> None:
    anchors: dict[str, list[str]] = {}
    for anchor in (whole, part):
        anchors.setdefault(anchor.kind, []).append(anchor.value)
    _start(timeline, anchors)
    assert _named(timeline) == {whole: (part,)}


def test_an_artefact_anchor_on_a_record_is_whole_beside_a_record_anchor_on_its_point(
    timeline: Timeline,
) -> None:
    """A record a place holds keeps both anchors whole (COR-050 point 2), and its parts are
    its points, which only a record anchor names."""
    point = Anchor("record", "ADR-007#3")
    anchors = {"artefact": [ADR], "record": [point.value]}
    timeline.start({**ADR_OVERLAY, ADR: adr(), GUIDE: guide(anchors=anchors)})
    assert _named(timeline) == {Anchor("artefact", ADR): (point,)}


def test_each_whole_anchor_is_a_finding_naming_only_its_own_parts(
    timeline: Timeline,
) -> None:
    second = "docs/second.md"
    other = Anchor("artefact", f"{second}#installing")
    anchors = {
        "artefact": [MANUAL, USING.value, second, other.value],
        "record": [RECORD.value, POINT.value],
    }
    timeline.start(
        {
            MANUAL: manual(),
            second: manual().replace('"manual"', '"second"'),
            POINTED: pointed_record(),
            GUIDE: guide(anchors=anchors),
        }
    )
    assert _named(timeline) == {
        WHOLE: (USING,),
        Anchor("artefact", second): (other,),
        RECORD: (POINT,),
    }


def test_two_anchors_on_one_document_whole_are_each_named(timeline: Timeline) -> None:
    _start(timeline, {"path": [MANUAL], "artefact": [MANUAL, USING.value]})
    assert _named(timeline) == {Anchor("path", MANUAL): (USING,), WHOLE: (USING,)}


def test_the_message_gives_both_moves_the_safe_one_first(timeline: Timeline) -> None:
    """Removing the part anchors loses no ask, so it stands first. Removing the whole anchor
    misses a change outside those parts, and either way the anchor list has changed."""
    _start(timeline, {"artefact": [MANUAL, USING.value]})
    (finding,) = [
        f for f in fr.run_repository_check(timeline.adopter.root).findings if f.kind is KIND
    ]
    safe = finding.message.index("removing them loses no flag and no ask")
    assert safe < finding.message.index("removing this one misses a change outside those parts")
    assert "a changed anchor list needs a revalidation" in finding.message


# --- what it does not name ----------------------------------------------------------------


@pytest.mark.parametrize(
    "anchors",
    [
        pytest.param({"artefact": [USING.value, LEAD.value]}, id="parts-alone"),
        pytest.param({"artefact": [MANUAL]}, id="a-whole-anchor-alone"),
        pytest.param({"record": [POINT.value], "artefact": [MANUAL]}, id="a-part-of-another"),
        pytest.param({"path": ["src/cli/**"], "artefact": [USING.value]}, id="a-path-beside-it"),
    ],
)
def test_nothing_is_named_without_a_whole_anchor_beside_its_own_parts(
    timeline: Timeline, anchors: dict[str, list[str]]
) -> None:
    _start(timeline, anchors)
    assert _named(timeline) == {}


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("docs/*.md", id="a-glob-over-several-files"),
        pytest.param("docs/man*.md", id="a-glob-over-the-one-file"),
        pytest.param("docs", id="a-folder"),
    ],
)
def test_a_path_anchor_is_whole_only_where_it_names_the_one_file(
    timeline: Timeline, path: str
) -> None:
    """COR-050 point 2's whole is a record or a document, and a glob or a folder names
    neither, however many files it stands on."""
    _start(timeline, {"path": [path], "artefact": [USING.value]})
    assert _named(timeline) == {}


def test_a_section_beside_its_own_sub_section_is_no_pair(timeline: Timeline) -> None:
    """Both are parts, and COR-050 point 2's whole anchor names neither."""
    sections = (("Using", "Run it.\n\n### Flags\n\nThe flags."),)
    anchors = {"artefact": [USING.value, f"{MANUAL}#flags"]}
    timeline.start({MANUAL: manual(sections), GUIDE: guide(anchors=anchors)})
    assert _named(timeline) == {}


def test_a_path_anchor_beside_a_broader_one_is_no_part(timeline: Timeline) -> None:
    """A path anchor names no part (COR-050 point 2), so a file beside a glob is no pair."""
    _start(timeline, {"path": ["src/cli/**", "src/cli/main.py"]})
    assert _named(timeline) == {}


def test_a_dead_part_anchor_is_reported_as_dead_and_is_no_part(timeline: Timeline) -> None:
    _start(timeline, {"artefact": [MANUAL, f"{MANUAL}#gone"]})
    result = fr.run_repository_check(timeline.adopter.root)
    assert [f.kind for f in result.findings if f.kind is KIND] == []
    assert result.count(fr.RepositoryFindingKind.DEAD_ANCHOR) == 1


def test_a_retired_point_stands_on_nothing_and_is_no_part(timeline: Timeline) -> None:
    stub = "Retired — see point 3."
    retired = pointed_record(
        (("1", "First", "One."), ("2", "Retired", stub), ("3", "Third", "Three.")),
        retired={"2": ["3"]},
    )
    anchors = {"record": [RECORD.value, POINT.value]}
    timeline.start({POINTED: retired, GUIDE: guide(anchors=anchors)})
    assert _named(timeline) == {}


def test_a_collection_entry_is_neither_whole_nor_part(timeline: Timeline) -> None:
    """An entry shares its file with other entries, and is cited whole: a path anchor on
    the file beside an anchor on an entry is no pair."""
    rules = "docs/rules.md"
    front = {"RS-1": {"pkit": {"friction": {"unanchored-because": "a test's fixture"}}}}
    collection = f"---\n{json.dumps(front)}\n---\n\n## RS-1 — One\n\nOne.\n"
    anchors = {"path": [rules], "artefact": ["RS-1"]}
    timeline.start({rules: collection, GUIDE: guide(anchors=anchors)})
    assert _named(timeline) == {}


def test_an_artefact_that_owes_no_answer_has_none(timeline: Timeline) -> None:
    """Its anchors ask for no answer, so there is nothing to narrow (COR-050 point 7)."""
    anchors = {"artefact": [MANUAL, USING.value]}
    timeline.start(
        {MANUAL: manual(), "docs/vendored/copy.md": guide(anchors=anchors)},
        friction_config(exclude=["docs/vendored"]),
    )
    assert _named(timeline) == {}


# --- it reads HEAD alone ------------------------------------------------------------------


def test_it_reads_head_alone_so_later_commits_move_nothing(timeline: Timeline) -> None:
    """One commit is enough, and it needs no flag: the finding is the same however the
    history grows, and it carries neither count nor bar."""
    _start(timeline, {"artefact": [MANUAL, USING.value]})
    root = timeline.adopter.root

    def finding() -> dict[str, Any]:
        (found,) = [f for f in _json(root)["findings"] if f["kind"] == "whole-and-parts"]
        return found

    first = finding()
    assert (first["origin"], first["bar"], first["share"]) == (None, None, None)
    for version in (2, 3, 4):
        timeline.commit("change the CLI", {"src/cli/main.py": f"print({version})\n"})
    assert finding() == first


def test_narrowing_the_block_ends_the_finding(timeline: Timeline) -> None:
    _start(timeline, {"artefact": [MANUAL, USING.value]})
    timeline.commit(
        "narrow the anchors", {GUIDE: guide(anchors={"artefact": [USING.value]}, at=T1)}
    )
    assert _named(timeline) == {}


# --- it owes nothing ----------------------------------------------------------------------


def test_it_owes_nothing_and_leaves_the_artefact_current(timeline: Timeline) -> None:
    config = friction_config(mode="enforcing")
    _start(timeline, {"artefact": [MANUAL, USING.value]}, config)
    root = timeline.adopter.root

    result = fr.run_repository_check(root)
    assert result.count(KIND) == 1
    assert result.failed is False and result.exit_code == 0
    (report,) = [r for r in result.artefact_reports if r.location == GUIDE]
    assert report.state is fr.ArtefactState.CURRENT
    assert frep.run_debt(root).entries == ()


def test_the_change_check_does_not_report_it(timeline: Timeline) -> None:
    """It is the whole-repository check's alone: a change meets no finding of it, in enforcing
    mode too."""
    _start(timeline, {"artefact": [MANUAL, USING.value]}, friction_config(mode="enforcing"))
    timeline.adopter.checkout("feature", create=True)
    timeline.commit("change the CLI", {"src/cli/main.py": "print('2')\n"})

    result = fc.run_change_check(timeline.adopter.root, "main")
    assert result.findings == ()
    assert not result.failed


# --- as the views show it -----------------------------------------------------------------


def test_the_human_view_gives_its_row_its_count_and_its_legend(timeline: Timeline) -> None:
    _start(timeline, {"artefact": [MANUAL, USING.value]})
    shown = fr.render_human(fr.run_repository_check(timeline.adopter.root))

    assert "1 whole anchor beside its parts" in shown.splitlines()[0]
    (row,) = [line for line in shown.splitlines() if line.startswith("    whole-and-parts")]
    assert f"artefact {MANUAL}  anchors a record or document whole beside 1 anchor" in row
    assert f"artefact {USING.value} — removing them loses no flag" in row
    assert row.endswith("nothing is owed")
    (legend,) = [line for line in shown.splitlines() if line.startswith("  whole-and-parts")]
    assert "reported only, nothing owed" in legend


def test_the_json_document_counts_it_and_lists_the_anchors_on_parts(timeline: Timeline) -> None:
    _start(timeline, {"artefact": [MANUAL, USING.value], "path": ["src/gone/**"]})
    document_ = _json(timeline.adopter.root)

    assert document_["schema_version"] == 1
    assert document_["counts"]["whole-and-parts"] == 1
    by_kind = {f["kind"]: f for f in document_["findings"]}
    found = by_kind["whole-and-parts"]
    assert found["anchor"] == {"kind": "artefact", "value": MANUAL}
    assert found["parts"] == [{"kind": "artefact", "value": USING.value}]
    assert by_kind["dead-anchor"]["parts"] is None  # only this finding names parts


def test_the_explanation_says_what_clears_it_and_asks_no_answer(timeline: Timeline) -> None:
    _start(timeline, {"artefact": [MANUAL, USING.value]})
    root = timeline.adopter.root
    explanation = frep.run_explain(root, "guide")
    assert explanation is not None

    (explained,) = [f for f in explanation.findings if f.finding.kind is KIND]
    assert explained.answers == () and explained.commits == ()
    assert explained.clears.startswith("nothing is owed; remove the anchors on its parts")
    assert "gives up a deferral or revisit of one part" in explained.clears
    assert f"or remove artefact:{MANUAL} where the artefact rests" in explained.clears
    assert explanation.report is not None
    assert explanation.report.state is fr.ArtefactState.CURRENT

    (found,) = [
        f
        for f in json.loads(frep.render_explain_json(explanation))["findings"]
        if f["kind"] == "whole-and-parts"
    ]
    assert found["parts"] == [{"kind": "artefact", "value": USING.value}]


def test_it_stands_before_the_second_bar_s_findings_on_its_artefact(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The second bar's findings stand together after an artefact's other findings, so the
    human views can show them as one (ADR-080 point 3)."""
    monkeypatch.setattr(fr, "OVER_BROAD_UNCHANGED_ASKS", 0)
    held = "the manual is as described"
    anchors = {"artefact": [MANUAL, USING.value]}
    _start(timeline, anchors)
    edited = manual(lead="Reworded.")
    timeline.commit("edit the manual", {MANUAL: edited})
    timeline.commit(
        "revalidate the guide",
        {GUIDE: document("guide", anchors=anchors, at="2026-10-05T00:00:00Z", because=held)},
    )

    kinds = [
        f.kind.value
        for f in fr.run_repository_check(timeline.adopter.root).findings
        if f.location == GUIDE
    ]
    assert kinds == ["whole-and-parts", "over-broad"]
