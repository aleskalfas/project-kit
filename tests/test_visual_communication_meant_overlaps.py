"""A part names the parts it lies over on purpose (visual-communication DEC-066).

- **The word** (point 1). A part names, under `lies-over`, parts written before it in the
  same `parts`. The reading of the component refuses a name that is no part of them, the
  part's own, one of a part written after it, and a name's second writing, each a finding at
  the level its file takes, and a name refused says nothing.
- **The scene carries it** (point 2) on the element the part draws, a `repeat`'s group
  among them: the trace ids of what the named parts draw, and the library version that
  holds the part, none for a piece's own component. It is no property an element draws, so
  no renderer the capability ships loses it, and the frames the viewing step writes hold
  none of it.
- **Validation alone states the fact.** An overlap the word names in a version the list
  marks released, still as released, is `box-overlap-meant`, from the scenes or from the
  findings record; for a copy of a library the capability ships, only where the list keeps
  the hash the capability records. Anywhere else it is `box-overlap`, with the message of a
  pair no one named. The viewing step's report gives every overlap as `box-overlap`.
- **Only the pair named** (points 2 and 3): an overlap the part does not name still asks for
  attention, and the check of edges that nearly line up compares the pair as before.

The card the tests draw is written in `tmp_path`, in the `tests` library, in a copy of the
foundations or as the piece's own: the repository's validation reads every bound file under
`tests/`, and a file a test refuses must not be one of them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from tests import test_visual_communication_drawings as drawings
from tests.in_process import load
from tests.test_visual_communication_boxes import STEP, element, scene
from tests.test_visual_communication_checks import LOCAL, local
from tests.test_visual_communication_look import (  # noqa: F401
    folder_of,
    plugins,
    report_of,
    reports_hold_their_schema,
    run_look,
)
from tests.test_visual_communication_pipeline import (
    LONG,
    PIECE,
    PIECE_FOLDER,
    drawing_project,
    lay_out_drawing,
    released_entry,
)
from tests.test_visual_communication_pipeline import write_content as write_body
from tests.visual_communication_project import bound, project, write, write_list, yaml_text
from tests.visual_engine import block, draw, top

boxes, checks, findings, layout, rendering, svg_declaration, pdf_declaration, html_declaration = (
    load(
        "visual-communication",
        "boxes",
        "checks",
        "findings",
        "layout",
        "rendering",
        "plugins.svg_declaration",
        "plugins.pdf_declaration",
        "plugins.html_declaration",
    )
)

LIST = "visual/libraries/libraries.yaml"
#: The holder of a piece's own component, as a part's `use` names it.
OWN = "piece"
#: The card's group in the figure, and its parts.
CARD = "figure/body"
BOX, MARK, BADGE = f"{CARD}/box", f"{CARD}/mark", f"{CARD}/badge"
#: What a meant overlap's message adds, in the `tests` library's version.
MEANT = (
    "; the part on top names the one beneath under `lies-over` in tests@1.0.0, released, "
    "which says the overlap is meant"
)
OVERLAPS = (boxes.BOX_OVERLAP, boxes.BOX_OVERLAP_MEANT)
#: A source of a library from another repository.
ELSEWHERE = {"kind": "repository", "url": "https://example.org/tests.git", "ref": "v1"}


def badged(**words: Any) -> str:
    """A card whose badge lies over the right edge of its box, and whose mark the box holds
    beside the badge's column, below it: a title of one line leaves the badge above the
    mark, and a long one pushes it down over the mark. Each of `words` gives a part's
    `lies-over`, the badge's `[box]` unless they say otherwise."""
    parts: dict[str, dict[str, Any]] = {
        "box": {"box": {"fill": "surface"}, "width": "=:width - @space.3", "height": "=:height"},
        "title": {
            "text": {"content": "title", "style": "type.body", "fill": "text-primary"},
            "x": "=@space.2",
            "y": "=@space.2",
            "width": "=box.width - @space.4 - @space.2",
        },
        "mark": {
            "box": {"fill": "surface"},
            "x": "=box.right - @space.4",
            "y": "=@space.4 * 2 + @space.2",
            "width": "=@space.4",
            "height": "=@space.3",
        },
        "badge": {
            "box": {"fill": "accent"},
            "x": "=box.right - @space.3",
            "y": "=min(title.bottom, @space.4 + @space.3 + @space.2)",
            "width": "=@space.4",
            "height": "=@space.4",
        },
    }
    for name, said in (words or {"badge": ["box"]}).items():
        if said is not None:
            parts[name] = {"lies-over": said, **parts[name]}
    return local(
        about="A card whose badge lies over its box's right edge.",
        fields={
            "type": "object",
            "required": ["title"],
            "properties": {"title": {"type": "string"}},
        },
        parts=parts,
        preferred={"height": "=max(title.bottom, mark.bottom) + @space.2"},
    )


def release(root: Path, name: str, version: str = "1.0.0", **source: str) -> None:
    """The list marks the version released, its hash over its folder as it is, from the
    source `source` gives where it gives one, every other entry kept."""
    path = root / LIST
    listed = dict(YAML(typ="safe").load(path.read_text(encoding="utf-8"))["libraries"])
    entry = dict(listed[name])
    if source:
        entry["source"] = dict(source)
    folder = root / "visual" / "libraries" / name / version
    entry["versions"] = {**entry["versions"], version: released_entry(folder, name)}
    listed[name] = entry
    write_list(root, listed)


def card(
    tmp_path: Path,
    *,
    holder: str = "tests",
    released: bool = True,
    title: str = "Plan the work.",
    **words: Any,
) -> Path:
    """The piece `flow`, its body the card `badged` written in `holder`'s folder of
    components, and, where `released`, that version marked released once it holds it. The
    piece's own component is never released."""
    root = drawing_project(tmp_path, picture=False)
    folder = LOCAL if holder == OWN else f"visual/libraries/{holder}/1.0.0/components"
    write(root / folder / "badged.yaml", badged(**words))
    if released and holder != OWN:
        release(root, holder)
    write_body(root, body={"use": f"{holder}/badged", "title": title})
    return root


def drawn_of(root: Path) -> Any:
    """The piece `flow` as the check's own modules read it, so the versions it holds are
    found under the lock."""
    piece = checks.pl.read_piece(root, "visual", PIECE)
    return checks.pl.Project(piece, piece.lock, checks.Held(root, "visual"))


def overlaps(root: Path, piece: str = PIECE) -> list[tuple[str, str, str, str]]:
    """Each overlap validation reads in the piece: its label, its level, where it lies and
    its message."""
    report = checks.check(root, only=piece)
    return sorted(
        (finding.code, level, finding.where, finding.message)
        for finding, level in report.judged
        if finding.code in OVERLAPS
    )


def unnamed(tmp_path: Path, **given: Any) -> list[tuple[str, str, str, str]]:
    """The overlaps of the card no part of which names another, in a project of its own."""
    return overlaps(card(tmp_path / "unnamed", badge=None, **given))


# --- validation ---------------------------------------------------------------------------------


def test_a_pair_a_released_version_names_is_a_fact_and_the_same_pair_unnamed_asks_for_attention(
    tmp_path: Path,
) -> None:
    [plain] = unnamed(tmp_path)
    assert plain[:3] == (boxes.BOX_OVERLAP, findings.ATTENTION, BOX)
    assert plain[3].endswith(f"`{BADGE}` is drawn over `{BOX}`")
    assert overlaps(card(tmp_path / "named")) == [
        (boxes.BOX_OVERLAP_MEANT, findings.FACT, BOX, plain[3] + MEANT)
    ]


@pytest.mark.parametrize(
    ("holder", "released"),
    [(OWN, False), ("tests", False)],
    ids=["a-pieces-own-component", "a-version-not-yet-released"],
)
def test_a_word_no_released_version_holds_gives_the_check_nothing(
    tmp_path: Path, holder: str, released: bool
) -> None:
    named = overlaps(card(tmp_path / "named", holder=holder, released=released))
    assert named == unnamed(tmp_path, holder=holder, released=released)
    [(label, level, _, message)] = named
    assert (label, level) == (boxes.BOX_OVERLAP, findings.ATTENTION)
    assert "lies-over" not in message


def test_a_released_version_whose_folder_changed_since_it_was_listed_gives_no_fact(
    tmp_path: Path,
) -> None:
    root = card(tmp_path / "named")
    held = root / "visual/libraries/tests/1.0.0/components/badged.yaml"
    held.write_text(held.read_text(encoding="utf-8").replace("A card whose", "A new card whose"))
    [(label, level, where, message)] = overlaps(root)
    assert (label, level, where) == (boxes.BOX_OVERLAP, findings.ATTENTION, BOX)
    [(_, _, _, plain)] = unnamed(tmp_path)
    assert message == plain


def test_a_shipped_copy_listed_released_with_a_hash_the_capability_does_not_record_gives_no_fact(
    tmp_path: Path,
) -> None:
    """A copy of the foundations that holds a card the capability never shipped, listed
    released with a hash over its folder as it is: the folder matches the list, and the
    list's hash is none the capability records for that version."""
    root = card(tmp_path, holder="foundations")
    [(label, level, where, message)] = overlaps(root)
    assert (label, level, where) == (boxes.BOX_OVERLAP, findings.ATTENTION, BOX)
    assert "lies-over" not in message
    assert not checks.Reading(checks.Held(root, "visual")).word_given("foundations@1.0.0")


def test_a_shipped_copy_listed_with_the_hash_the_capability_records_reads_as_released(
    tmp_path: Path,
) -> None:
    """A copy as the capability ships it, listed released with the hash it records, gives
    a word in it the fact; once the folder changes, it no longer does."""
    root = drawing_project(tmp_path, picture=False, released=True)
    assert checks.Reading(checks.Held(root, "visual")).word_given("foundations@1.0.0")
    write(root / "visual/libraries/foundations/1.0.0/components/badged.yaml", badged())
    assert not checks.Reading(checks.Held(root, "visual")).word_given("foundations@1.0.0")


def test_a_version_from_another_repository_listed_released_and_matching_gives_the_fact(
    tmp_path: Path,
) -> None:
    root = card(tmp_path, released=False)
    release(root, "tests", **ELSEWHERE)
    [(label, level, where, _)] = overlaps(root)
    assert (label, level, where) == (boxes.BOX_OVERLAP_MEANT, findings.FACT, BOX)


def test_a_release_turns_the_recorded_overlap_into_the_fact_and_the_record_still_verifies(
    tmp_path: Path,
) -> None:
    """The record keeps the word's version and no mark of release, and its key covers no
    list, so a release that leaves the version's folder as it was changes the label at
    once (DEC-066 point 2)."""
    root = card(tmp_path, released=False)
    drawn = drawn_of(root)
    record = rendering.record_text(rendering.record(drawn, checks.computed(drawn), None))
    (root / PIECE_FOLDER / "findings.yaml").write_bytes(record)
    assert "lies-over-in: tests@1.0.0" in record.decode("utf-8")
    [(label, _, _, _)] = overlaps(root)
    assert label == boxes.BOX_OVERLAP
    assert "of 1 read from their findings record" in checks.check(root, only=PIECE).summary[0]
    release(root, "tests")
    report = checks.check(root, only=PIECE)
    assert "of 1 read from their findings record, of 0 computed now" in report.summary[0]
    [(label, level, where, _)] = overlaps(root)
    assert (label, level, where) == (boxes.BOX_OVERLAP_MEANT, findings.FACT, BOX)


def test_an_overlap_the_badge_does_not_name_still_asks_for_attention(tmp_path: Path) -> None:
    """A long title pushes the badge down over the mark, which it does not name."""
    found = {
        where: (label, level, message)
        for label, level, where, message in overlaps(card(tmp_path, title=LONG))
    }
    assert set(found) == {BOX, MARK}
    assert found[BOX][:2] == (boxes.BOX_OVERLAP_MEANT, findings.FACT)
    assert found[MARK][:2] == (boxes.BOX_OVERLAP, findings.ATTENTION)
    assert found[MARK][2].endswith(f"`{BADGE}` is drawn over `{MARK}`")


def test_a_word_in_a_brands_released_drawing_gives_the_fact(tmp_path: Path) -> None:
    """A tab the test brand's drawing of the deck's cover places over its band."""
    tab = {
        "lies-over": ["band"],
        "box": {"fill": "surface"},
        "x": "=margin",
        "y": "=@space.1",
        "width": "=@space.4",
        "height": "=@space.3",
    }
    root = drawings.deck(tmp_path, drawing=drawings.cover(parts__tab=tab))
    assert [label for label, *_ in overlaps(root, drawings.PIECE)] == [boxes.BOX_OVERLAP]
    release(root, "test-brand", "1.1.0")
    [(label, level, where, message)] = overlaps(root, drawings.PIECE)
    assert (label, level, where) == (
        boxes.BOX_OVERLAP_MEANT,
        findings.FACT,
        f"{drawings.COVER}/band",
    )
    assert "in test-brand@1.1.0, released" in message


#: A top of the `tests` library whose one layout is a page's form, drawing a tab over a band.
SHEET = local(
    about="A top whose one layout draws a tab over a band at the top of its page.",
    fields={
        "type": "object",
        "properties": {
            "pages": {"type": "array", "items": {"type": "object"}, "x-pkit-pages": True}
        },
    },
    layouts={
        "one": {
            "slots": {"head": {"type": "string"}},
            "required": ["head"],
            "parts": {
                "band": {"box": {"fill": "accent"}, "width": "=:width", "height": "=@space.2"},
                "tab": {
                    "lies-over": ["band"],
                    "box": {"fill": "surface"},
                    "x": "=@space.4",
                    "y": "=@space.1",
                    "width": "=@space.4",
                    "height": "=@space.3",
                },
                "head": {
                    "text": {"content": "head", "style": "type.body", "fill": "text-primary"},
                    "y": "=@space.4",
                    "width": "=:width",
                },
            },
        }
    },
    preferred={"width": "=@size.figure", "height": "=@space.4 * 4"},
)


def test_a_word_in_a_tops_released_drawing_of_a_layout_gives_the_fact(tmp_path: Path) -> None:
    root = lay_out_drawing(project(tmp_path), picture=False, top="tests/sheet")
    write(root / "visual/libraries/tests/1.0.0/components/sheet.yaml", SHEET)
    pages = [{"id": "a", "layout": "one", "head": "A"}]
    write(root / PIECE_FOLDER / "content.en.yaml", yaml_text(bound("content", pages=pages)))
    release(root, "tests")
    [(label, level, where, _)] = overlaps(root)
    assert (label, level, where) == (boxes.BOX_OVERLAP_MEANT, findings.FACT, "sheet/pages[a]/band")


# --- what the reading refuses -------------------------------------------------------------------


#: Each word the reading refuses, the part that writes it, and the message of its finding.
REFUSED = {
    "no-part": (
        {"badge": ["ghost"]},
        "badge",
        "the part `badge` names `ghost` under `lies-over`, which is no part of the same "
        "`parts`: the name says nothing",
    ),
    "itself": (
        {"badge": ["badge"]},
        "badge",
        "the part `badge` names itself under `lies-over`: the name says nothing",
    ),
    "written-after": (
        {"badge": None, "box": ["badge"]},
        "box",
        "the part `box` names `badge` under `lies-over`, a part written after it, so drawn "
        "over it: the name says nothing",
    ),
}


def refusals(root: Path) -> set[tuple[str, str, str]]:
    report = checks.check(root, only=PIECE)
    return {
        (finding.where, finding.message, level)
        for finding, level in report.judged
        if finding.code == layout.LIES_OVER_REFUSED
    }


@pytest.mark.parametrize(("words", "part", "said"), list(REFUSED.values()), ids=list(REFUSED))
@pytest.mark.parametrize(
    ("holder", "level"),
    [(OWN, findings.FAILS), ("tests", findings.ATTENTION)],
    ids=["own-fails", "released-asks-for-attention"],
)
def test_each_refused_name_is_a_finding_at_its_level_and_leaves_the_pair_asking_for_attention(
    tmp_path: Path,
    words: dict[str, Any],
    part: str,
    said: str,
    holder: str,
    level: str,
) -> None:
    root = card(tmp_path, holder=holder, **words)
    assert refusals(root) == {(f"parts.{part}.lies-over", f"{holder}/badged: {said}", level)}
    [(label, attention, where, _)] = overlaps(root)
    assert (label, attention, where) == (boxes.BOX_OVERLAP, findings.ATTENTION, BOX)


def test_a_names_second_writing_is_refused_and_its_first_still_names_its_part(
    tmp_path: Path,
) -> None:
    root = card(tmp_path, badge=["box", "box"])
    said = "the part `badge` names `box` under `lies-over` a second time: the name says nothing"
    assert refusals(root) == {
        ("parts.badge.lies-over", f"tests/badged: {said}", findings.ATTENTION)
    }
    [(label, _, where, _)] = overlaps(root)
    assert (label, where) == (boxes.BOX_OVERLAP_MEANT, BOX)


def test_a_word_that_is_no_list_is_a_fault_of_the_components_shape(tmp_path: Path) -> None:
    root = card(tmp_path, holder=OWN, badge="box")
    report = checks.check(root, only=PIECE)
    [shape] = [
        finding
        for finding, _ in report.judged
        if finding.code == "component-shape" and "lies-over" in finding.where
    ]
    assert shape.message == "piece/badged: the part `badge` takes a list of names under `lies-over`"


# --- the scene ----------------------------------------------------------------------------------


def test_the_element_holds_what_its_part_names_and_the_version_that_holds_it() -> None:
    parts = {
        "back": {"box": {"fill": "surface"}, "width": "=@space.4 * 4", "height": "=@space.3"},
        "slot": {"slot": "body", "width": "=@space.4", "height": "=@space.4"},
        "items": {
            "lies-over": ["back", "slot"],
            "repeat": "items",
            "draw": "lab/chip",
            "y": "=@space.2",
            "row": {},
        },
    }
    chip = block(
        {"b": {"box": {"fill": "surface"}, "width": "=:width", "height": "=:height"}},
        preferred={"width": "=@space.3", "height": "=@space.3"},
    )
    fields = {"items": {"type": "array", "items": {"type": "object"}}, "body": {"type": "object"}}
    components = {"lab/top": top(parts, fields=fields), "lab/chip": chip}
    result = draw({"items": [{"id": "a"}, {"id": "b"}]}, components=components)
    assert layout.LIES_OVER_REFUSED not in [finding.code for finding in result.findings]
    items = result.scene.find("top/items")
    assert items is not None and items.type == "group"
    # The slot left empty draws nothing, so the group names the back alone.
    assert items.properties["lies-over"] == {"ids": ["top/back"], "library": "lab@1.0.0"}
    assert "lies-over" not in items.sources
    assert all("lies-over" not in child.properties for child in items.children)
    [overlap] = boxes.overlaps(result.scene.to_dict())
    assert (overlap.where, overlap.lies_over_in) == ("top/back", "lab@1.0.0")


def test_a_pieces_own_component_names_no_version(tmp_path: Path) -> None:
    drawn = drawn_of(card(tmp_path, holder=OWN))
    [(_, result)] = list(drawn.scenes(facts=drawn.piece.stand_ins))
    badge = result.scene.find(BADGE)
    assert badge is not None
    assert badge.properties["lies-over"] == {"ids": [BOX]}


def test_no_renderer_the_capability_ships_loses_the_word() -> None:
    said = {boxes.IDS: ["figure/a"], boxes.LIBRARY: "tests@1.0.0"}
    for declared in (svg_declaration, pdf_declaration, html_declaration):
        draws = declared.DECLARATION["draws"]
        kinds = [kind for kind in draws if kind != "group"]
        children = [{"type": kind, "id": f"figure/{kind}", "lies-over": said} for kind in kinds]
        page = {"type": "group", "id": "figure", "lies-over": said, "children": children}
        assert checks.losses({"children": [page]}, declared.DECLARATION) == []


# --- the checks of boxes ------------------------------------------------------------------------


def test_the_overlap_carries_the_words_version_only_on_the_pair_it_names() -> None:
    said = {boxes.IDS: ["figure/a"], boxes.LIBRARY: "tests@1.0.0"}
    given = scene(
        element("figure/a"),
        element("figure/b", x=30, y=20),
        {**element("figure/c", x=20, y=30), "lies-over": said},
    )
    found = {(f.where, f.message.rsplit(": ", 1)[1]): f for f in boxes.overlaps(given)}
    assert found[("figure/a", "`figure/c` is drawn over `figure/a`")].lies_over_in == (
        "tests@1.0.0"
    )
    assert found[("figure/b", "`figure/c` is drawn over `figure/b`")].lies_over_in == ""
    assert found[("figure/a", "`figure/b` is drawn over `figure/a`")].lies_over_in == ""


def test_the_fact_asks_no_one_to_act_and_keeps_the_overlaps_message() -> None:
    said = {boxes.IDS: ["figure/a"], boxes.LIBRARY: "tests@1.0.0"}
    [overlap] = boxes.overlaps(
        scene(element("figure/a"), {**element("figure/b", x=30, y=20), "lies-over": said})
    )
    fact = boxes.meant(overlap)
    assert (fact.code, fact.level, fact.where, fact.fix, fact.who) == (
        boxes.BOX_OVERLAP_MEANT,
        findings.FACT,
        "figure/a",
        "",
        "",
    )
    assert fact.message == overlap.message + MEANT


def test_a_near_miss_in_a_pair_named_so_is_still_reported() -> None:
    said = {boxes.IDS: ["figure/a"], boxes.LIBRARY: "tests@1.0.0"}
    given = scene(element("figure/a"), {**element("figure/b", x=2.5, y=20), "lies-over": said})
    [near] = boxes.near_alignment(given, STEP)
    assert (near.code, near.where) == (boxes.NEAR_ALIGNMENT, "figure/a")


# --- the viewing step ---------------------------------------------------------------------------


def look_overlaps(root: Path) -> list[dict[str, Any]]:
    done = run_look(root, PIECE)
    assert done.returncode == 0, done.stderr
    [image] = report_of(root)["images"]
    return [each for each in image["findings"] if each["label"] in OVERLAPS]


@pytest.mark.parametrize(
    ("holder", "released"),
    [("tests", True), ("tests", False), (OWN, False)],
    ids=["released", "not-yet-released", "own"],
)
def test_the_report_gives_every_overlap_as_one_no_one_named(
    tmp_path: Path, holder: str, released: bool
) -> None:
    named = card(tmp_path / "named", holder=holder, released=released)
    plain = card(tmp_path / "unnamed", holder=holder, released=released, badge=None)
    [overlap] = look_overlaps(named)
    assert look_overlaps(plain) == [overlap]
    assert (overlap["label"], overlap["level"]) == (boxes.BOX_OVERLAP, findings.ATTENTION)
    for frames in folder_of(named).glob("*.frames.json"):
        assert "lies-over" not in frames.read_text(encoding="utf-8")
    assert "lies-over" not in json.dumps(report_of(named))


def test_the_report_names_the_word_only_in_the_message_of_a_refusal(tmp_path: Path) -> None:
    root = card(tmp_path, holder=OWN, badge=["ghost"])
    run_look(root, PIECE)
    report = report_of(root)
    [image] = report["images"]
    refused = [each for each in image["findings"] if each["label"] == layout.LIES_OVER_REFUSED]
    assert [each["message"] for each in refused] == [f"{OWN}/badged: {REFUSED['no-part'][2]}"]
    image["findings"] = [each for each in image["findings"] if each not in refused]
    assert "lies-over" not in json.dumps(report)
