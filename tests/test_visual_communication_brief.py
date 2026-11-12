"""A piece's brief, `brief.yaml` in its folder (visual-communication DEC-029, #2969).

Held here:

- **its schema**: a part for the whole piece and one for each page, keyed by the page's id;
  strict in every mapping, the methodology's container kept free in each; a reason's aspect
  one of six; a part of the content named by its key path, never its place; and nothing that
  fixes a look or a brand's value (points 2 and 3);
- **where the pages are**: the list a top whose layouts are its pages' forms marks, each slot
  of pages of another top, and none for a top that is a page alone;
- **the check of what it names** (point 5): a page or a key path that names nothing in the
  content of the source language fails, in the brief, naming the nearest; a piece with no
  brief reads as before; a final piece's brief goes unread, but for its binding;
- **no command changes it, and nothing drawn reads it** (point 4): a render leaves it as it
  is, it is no input of the findings record nor of an export, and a final piece's copy
  carries it (DEC-017 point 8).

The commands run in the test's own process (`tests/in_process.py`).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tests import visual_communication_producer as producer
from tests.in_process import load, run_main
from tests.test_visual_communication_checks import deck_project
from tests.test_visual_communication_pipeline import (
    PIECE,
    PIECE_FOLDER,
    content,
    drawing_project,
    write_picture,
)
from tests.visual_communication_project import (
    SCHEMAS,
    bound,
    importable,
    write,
    yaml_text,
)

(
    checks,
    briefs,
    files,
    fingerprint,
    reading,
    framing,
    seam,
    svg,
    render,
    export,
    mark_final,
    take_up,
) = load(
    "visual-communication",
    "checks",
    "briefs",
    "files",
    "fingerprint",
    "reading",
    "framing",
    "plugins.seam",
    "plugins.svg",
    "render.py",
    "export.py",
    "mark-final.py",
    "take-up.py",
)

BRIEF = f"{PIECE_FOLDER}/brief.yaml"

#: A principle, as a reason names it.
PRINCIPLE = {"name": "Ordered visual variables", "source": "Jacques Bertin, Semiology of Graphics"}


@pytest.fixture(autouse=True)
def plugins(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The renderer stands in for the import a command makes when it draws, and the test
    producer is registered, for the length of the test."""
    importable(monkeypatch, svg)
    producer.register(seam)
    yield
    seam.unregister(producer.NAME)


def instance() -> dict[str, Any]:
    return reading.read_yaml(SCHEMAS / "brief.yaml")


def refused(data: Any) -> list[str]:
    return files.shape_problems(data, "brief")


def write_brief(root: Path, **parts: Any) -> Path:
    return write(root / BRIEF, yaml_text(bound("brief", **parts)))


def brief_found(root: Path, piece: str = PIECE) -> list[tuple[str, str, str]]:
    """Each brief finding of the check of `piece`: its label, its place and what it says."""
    report = checks.check(root, only=piece)
    return [
        (finding.code, checks.place(finding), checks.said(finding))
        for finding, _level in report.judged
        if finding.code.startswith("brief-")
    ]


def run(script: Any, *args: str, root: Path) -> None:
    done = run_main(script, *args, cwd=root)
    assert done.returncode == 0, done.stderr


# --- its schema ---------------------------------------------------------------------------------


def test_the_reference_instance_speaks_of_the_whole_piece_and_of_pages_by_their_ids() -> None:
    data = instance()
    assert refused(data) == []
    assert set(data) == {"pkit_schema", "schema_version", "piece", "pages"}
    assert set(data["pages"]) == {"cover", "layers"}
    aspects = [reason["aspect"] for reason in data["pages"]["layers"]["reasons"]]
    assert aspects == ["structure", "form", "colour"]


def test_a_brief_of_its_binding_alone_holds_and_a_part_is_optional() -> None:
    assert refused(bound("brief")) == []
    assert refused(bound("brief", piece={"goals": ["A goal."]})) == []
    assert refused(bound("brief", pages={"cover": {"takeaway": "The point."}})) == []


@pytest.mark.parametrize(
    "path",
    [
        ["pkit"],
        ["piece", "pkit"],
        ["pages", "pkit"],
        ["pages", "layers", "pkit"],
        ["pages", "layers", "relations", 0, "pkit"],
        ["pages", "layers", "reasons", 0, "pkit"],
        ["pages", "layers", "reasons", 0, "principle", "pkit"],
    ],
    ids=lambda path: ".".join(map(str, path)),
)
def test_its_top_and_each_mapping_keep_the_container_free_and_refuse_another_key(
    path: list[Any],
) -> None:
    def setting(key: str, value: Any) -> dict[str, Any]:
        data = instance()
        held: Any = data
        for step in path[:-1]:
            held = held[step]
        held[key] = value
        return data

    assert refused(setting("pkit", {"later": "reading"})) == []
    assert refused(setting("pkit", "text")) != []
    if path[:-1] != ["pages"]:  # a key there is a page's id
        assert refused(setting("unknown", "x")) != []


@pytest.mark.parametrize("aspect", ["structure", "form", "hierarchy", "type", "colour", "space"])
def test_a_reason_is_about_one_of_six_aspects(aspect: str) -> None:
    data = instance()
    data["pages"]["layers"]["reasons"][0]["aspect"] = aspect
    assert refused(data) == []


@pytest.mark.parametrize(
    "reason",
    [
        {"aspect": "color", "text": "Why.", "principle": {"name": "A", "source": "B"}},
        {"aspect": "form", "principle": {"name": "A", "source": "B"}},
        {"aspect": "form", "text": "Why."},
        {"aspect": "form", "text": "Why.", "principle": "Bertin"},
        {"aspect": "form", "text": "Why.", "principle": {"name": "A"}},
        {"aspect": "form", "text": " ", "principle": {"name": "A", "source": "B"}},
    ],
    ids=["no-such-aspect", "no-text", "no-principle", "principle-no-mapping", "no-source", "blank"],
)
def test_a_reason_holds_its_aspect_its_text_and_its_principle_by_name_and_source(
    reason: dict[str, Any],
) -> None:
    assert refused(bound("brief", piece={"reasons": [reason]})) != []


@pytest.mark.parametrize(
    "path",
    ["body", "body.steps", "body.steps[plan]", "slides[cover].visual.items[a-b_c].head"],
)
def test_a_part_of_the_content_is_named_by_its_key_path(path: str) -> None:
    relation = {"text": "Each rests on the one below.", "relates": [path]}
    assert refused(bound("brief", piece={"relations": [relation]})) == []
    reason = {"aspect": "form", "about": path, "text": "Why.", "principle": PRINCIPLE}
    assert refused(bound("brief", piece={"reasons": [reason]})) == []


@pytest.mark.parametrize(
    "path",
    ["body.steps#1", "body steps", "Body", "body.[plan]", "body.steps[1x]", "", "body."],
)
def test_never_by_its_place_in_a_list_or_in_words(path: str) -> None:
    relation = {"text": "Each rests on the one below.", "relates": [path]}
    assert refused(bound("brief", piece={"relations": [relation]})) != []


def test_a_page_is_keyed_by_an_id() -> None:
    assert refused(bound("brief", pages={"slide 2": {"goals": ["A goal."]}})) != []
    assert refused(bound("brief", pages={"2": {"goals": ["A goal."]}})) != []


def _leaves(schema: Any) -> Iterator[Any]:
    """Each schema within `schema` that declares a value's type, or refers to another."""
    if isinstance(schema, dict):
        if "type" in schema or "$ref" in schema or "enum" in schema or "const" in schema:
            yield schema
        for value in schema.values():
            yield from _leaves(value)
    elif isinstance(schema, list):
        for value in schema:
            yield from _leaves(value)


def test_nothing_in_it_fixes_a_look_or_a_brands_value() -> None:
    """A brief holds words, ids and key paths: no number, no value and no role of a brand."""
    schema = json.loads((SCHEMAS / "brief.schema.json").read_text(encoding="utf-8"))
    refs = {leaf["$ref"] for leaf in _leaves(schema) if "$ref" in leaf}
    assert {ref for ref in refs if not ref.startswith("#/")} == {
        "defs.schema.json#/$defs/text",
        "defs.schema.json#/$defs/id",
    }
    numbers = [leaf for leaf in _leaves(schema) if leaf.get("type") in ("number", "integer")]
    assert numbers == [schema["properties"]["schema_version"]]


# --- where the pages are ------------------------------------------------------------------------


def test_a_top_whose_layouts_are_its_pages_forms_holds_its_pages_in_the_list_it_marks() -> None:
    top = {"fields": {"properties": {"slides": {"x-pkit-pages": True}}}, "layouts": {}}
    held = {"slides": [{"id": "cover"}, {"id": "rules"}, {"title": "no id"}]}
    assert list(briefs.pages_of(top, held)) == ["cover", "rules"]


def test_another_tops_slot_of_pages_holds_them_as_items_or_as_the_one_component_it_places() -> None:
    top = {"layouts": {"frame": {"slots": {"slides": {"pages": True}, "note": {}}}}}
    held = {"slides": [{"id": "a", "use": "x/y"}, {"id": "b"}], "note": {"id": "c"}}
    assert list(briefs.pages_of(top, held)) == ["a", "b"]
    assert list(briefs.pages_of(top, {"slides": {"id": "one", "use": "x/y"}})) == ["one"]


def test_a_top_that_is_a_page_alone_holds_no_pages() -> None:
    top = {"layouts": {"frame": {"slots": {"body": {}, "caption": {}}}}}
    assert briefs.pages_of(top, {"body": {"id": "b"}}) == {}


# --- the check of what it names -----------------------------------------------------------------


def test_a_piece_with_no_brief_reads_as_before(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    assert brief_found(root) == []
    assert checks.brief_findings(checks.pl.read_piece(root, "visual", PIECE)) == []


def test_a_brief_whose_names_hold_raises_nothing(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    write_brief(
        root,
        piece={
            "relations": [{"text": "Planning comes first.", "relates": ["body.steps"]}],
            "takeaway": "The work flows one way.",
            "reasons": [
                {
                    "aspect": "form",
                    "about": "body.steps[plan]",
                    "text": "The first step leads.",
                    "principle": {"name": "Reading order", "source": "A book."},
                },
                {
                    "aspect": "type",
                    "about": "caption",
                    "text": "The caption is set as body text.",
                    "principle": {"name": "Hierarchy", "source": "A book."},
                },
                {
                    "aspect": "space",
                    "text": "About the whole figure.",
                    "principle": {"name": "Proximity", "source": "A book."},
                },
            ],
        },
    )
    assert brief_found(root) == []
    assert checks.check(root, only=PIECE).failed() is False


PATHS = [
    (
        "body.stepz",
        "names `stepz`, which the content does not give there; did you mean `steps`?",
    ),
    (
        "body.steps[plann]",
        "names `[plann]`, which the list `steps` does not hold; did you mean `[plan]`?",
    ),
    (
        "body.steps.head",
        "steps into the list `steps` with no id: name its item as `[<id>]`",
    ),
    ("caption[first]", "names the item `[first]` of `caption`, which is no list"),
    ("caption.text", "steps into `text` below what is no mapping"),
    (
        "body.steps#1",
        "is no key path: the content file's keys joined by `.`, each item by its id as "
        "`<list>[<id>]`",
    ),
]


@pytest.mark.parametrize(("path", "why"), PATHS, ids=[path for path, _ in PATHS])
def test_a_key_path_that_names_nothing_fails_at_its_place_in_the_brief(
    tmp_path: Path, path: str, why: str
) -> None:
    root = drawing_project(tmp_path, picture=False)
    reason = {"aspect": "form", "about": path, "text": "Why.", "principle": PRINCIPLE}
    write_brief(
        root,
        piece={
            "relations": [{"text": "One way.", "relates": ["body.steps", path]}],
            "reasons": [reason],
        },
    )
    said = f"`{path}` names nothing in `content.en.yaml`: it {why} — {briefs.PATH_FIX}"
    assert brief_found(root) == [
        ("brief-path", f"{BRIEF}#piece.relations#1.relates#2", said),
        ("brief-path", f"{BRIEF}#piece.reasons#1.about", said),
    ]
    judged = checks.check(root, only=PIECE).judged
    assert {level for f, level in judged if f.code == "brief-path"} == {"fails"}


def test_the_content_of_the_source_language_answers_for_every_language(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False, languages=["en", "cs"])
    steps = content()["body"]["steps"][:2]
    write(
        root / PIECE_FOLDER / "content.en.yaml",
        yaml_text(bound("content", body={"use": "tests/steps", "steps": steps})),
    )
    write(
        root / PIECE_FOLDER / "content.cs.yaml",
        yaml_text(bound("content", body={"use": "tests/steps", "steps": steps}, caption="Tok.")),
    )
    write_brief(root, piece={"relations": [{"text": "Below.", "relates": ["caption"]}]})
    [(code, place, said)] = brief_found(root)
    assert (code, place) == ("brief-path", f"{BRIEF}#piece.relations#1.relates#1")
    assert said.startswith("`caption` names nothing in `content.en.yaml`")


def test_a_page_of_a_piece_that_is_a_page_alone_names_nothing(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    write_brief(root, pages={"flow": {"goals": ["A goal."]}})
    assert brief_found(root) == [
        (
            "brief-page",
            f"{BRIEF}#pages.flow",
            "the brief speaks of the page `flow`, and `content.en.yaml` holds no page that "
            "carries an id — a piece of one page keeps all of its brief under `piece`; else, "
            f"{briefs.PAGE_FIX}",
        )
    ]


def test_a_decks_page_is_named_by_its_id_and_its_paths_start_at_the_page(tmp_path: Path) -> None:
    root = deck_project(tmp_path)
    write_brief(
        root,
        piece={"relations": [{"text": "A cover, then rules.", "relates": ["slides[cover].title"]}]},
        pages={
            "cover": {"takeaway": "What the talk is about."},
            "rules": {
                "relations": [{"text": "One step.", "relates": ["visual.steps[ask]", "title"]}],
                "reasons": [
                    {
                        "aspect": "hierarchy",
                        "about": "footer",
                        "text": "Last.",
                        "principle": {"name": "A", "source": "B"},
                    }
                ],
            },
        },
    )
    assert brief_found(root) == []


def test_a_page_the_content_lacks_fails_naming_its_pages_and_the_nearest(tmp_path: Path) -> None:
    root = deck_project(tmp_path)
    write_brief(
        root,
        pages={
            "rule": {"relations": [{"text": "Is not read.", "relates": ["nothing"]}]},
            "fits": {"relations": [{"text": "Read.", "relates": ["slides[fits]"]}]},
        },
    )
    assert brief_found(root) == [
        (
            "brief-page",
            f"{BRIEF}#pages.rule",
            "the brief speaks of the page `rule`, which no page of `content.en.yaml` carries "
            "as its id; its pages are `cover`, `fits`, `rules`; did you mean `rules`? — "
            f"{briefs.PAGE_FIX}",
        ),
        (
            "brief-path",
            f"{BRIEF}#pages.fits.relations#1.relates#1",
            "`slides[fits]` names nothing in `content.en.yaml`: it names `slides`, which the "
            f"content does not give there — {briefs.PATH_FIX}",
        ),
    ]


def test_a_brief_of_another_shape_is_left_to_the_data_validation(tmp_path: Path) -> None:
    root = deck_project(tmp_path)
    write_brief(root, piece=["no mapping"], pages={"cover": "text", "rules": {"reasons": "x"}})
    assert brief_found(root) == []
    assert refused(reading.read_yaml(root / BRIEF)) != []


def test_a_broken_binding_is_the_bindings_finding(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    write(root / BRIEF, yaml_text({"pkit_schema": "visual-communication:content", "piece": {}}))
    found = [(f.code, f.file) for f, _ in checks.check(root).judged if f.file == BRIEF]
    assert found == [("binding", BRIEF)]
    assert brief_found(root) == []


def test_a_final_pieces_brief_goes_unread_but_for_its_binding(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False, released=True)
    run(export, PIECE, root=root)
    run(mark_final, PIECE, "1", root=root)
    write_brief(root, pages={"nothing": {"goals": ["A goal."]}})
    assert brief_found(root) == []
    write(root / BRIEF, "pkit_schema: visual-communication:piece\nschema_version: 1\n")
    assert [f.code for f, _ in checks.check(root).judged if f.file == BRIEF] == ["binding"]


# --- no command changes it, and nothing drawn reads it ------------------------------------------


def test_a_render_leaves_the_brief_as_it_is_and_reads_it_into_no_record(tmp_path: Path) -> None:
    root = drawing_project(tmp_path)
    write_picture(root, framing)
    written = write_brief(root, pages={"nothing": {"goals": ["A goal."]}}).read_bytes()
    run(render, PIECE, root=root)
    assert (root / BRIEF).read_bytes() == written
    record = reading.read_yaml(root / PIECE_FOLDER / "findings.yaml")
    assert {entry.get("file") for entry in record["key"]["inputs"]} >= {"piece.yaml"}
    assert "brief.yaml" not in {entry.get("file") for entry in record["key"]["inputs"]}


def test_a_change_to_the_brief_leaves_the_findings_record_believed(tmp_path: Path) -> None:
    root = drawing_project(tmp_path)
    write_picture(root, framing)
    write_brief(root, piece={"goals": ["A goal."]})
    run(render, PIECE, root=root)
    write_brief(root, piece={"goals": ["Another goal."]})
    summary = checks.check(root, only=PIECE).summary[0]
    assert "the scenes of 1 read from their findings record" in summary


def test_a_change_to_the_brief_stales_no_published_copy(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, state="published", picture=False)
    write_brief(root, piece={"goals": ["A goal."]})
    run(export, PIECE, root=root)
    write_brief(root, piece={"goals": ["Another goal."]}, pages={"x": {"goals": ["More."]}})
    found = checks.check(root, only=PIECE).judged
    assert [f.code for f, _ in found if f.code.startswith(("current-copy-", "published-"))] == []
    record = reading.read_yaml(root / PIECE_FOLDER / "exports.yaml")
    (version,) = record["versions"]
    assert "brief.yaml" not in {entry.get("file") for entry in version["fingerprint"]["inputs"]}


def test_a_final_pieces_copy_carries_its_brief_as_it_is(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False, released=True)
    written = write_brief(root, piece={"goals": ["A goal."]}).read_bytes()
    run(export, PIECE, root=root)
    run(mark_final, PIECE, "1", root=root)
    run(take_up, PIECE, "talk", root=root)
    assert (root / "visual" / "pieces" / "talk" / "brief.yaml").read_bytes() == written
    assert (root / BRIEF).read_bytes() == written
