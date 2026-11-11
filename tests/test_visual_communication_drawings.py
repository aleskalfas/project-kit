"""A brand's drawing of a layout (visual-communication DEC-034 points 1, 2, 4, 5 and 6,
DEC-009 points 2 to 6): a component of the brand whose file names, under `draws`, the top
and the layout it draws.

- **The declaration.** It declares nothing the content gives, reads none of its top's
  component tokens, and only a brand's component declares one (point 1). Content, or a
  component, that places one by `use` fails (DEC-009 point 5).
- **Sizes.** A drawing of a page's form writes its page's height alone, and writes it where
  the top asks for none; a drawing of a top whose one layout is the whole top writes its
  own `preferred` (point 2).
- **Trace ids.** The instance keeps its id, and what a field shows keeps the same trace id,
  under every drawing; the instance's group names the drawing and its brand's version. A
  brand's drawing that shows a field by no part named after it fails; a top's own asks
  for attention (point 5).
- **Fit.** A brand's drawing draws an instance where it fits it in every language and at
  every key, and the top's own drawing draws it in all of them where it does not, which
  the piece states (point 6). A preview in one language takes the drawing chosen for the
  whole piece.
- **Along a chain of brands.** A brand built on a base draws a top its base does not serve.
  The brand nearest the root that serves a top keeps its form, so a brand's drawing of a
  top its base serves draws nothing, which the piece states (DEC-009 point 4, DEC-034
  point 8).
- **A top a brand holds.** It is drawn by its own drawing under that brand and every brand
  built on it, and no drawing of it draws, which the check fails. Under any other brand it
  is drawn by its own drawing too, and the check asks the piece's author for attention
  (DEC-034 point 4).

The engine's rules are drawn from components written as mappings in memory (`FakeEnv`);
the deck under the test brand from a project in a temporary folder, its drawing of the
cover the committed fixture `drawings/cover.yaml`. A chain of brands is the test edition
built on the test brand.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load
from tests.visual_communication_project import (
    FIXTURES,
    TEST_EDITION,
    bound,
    copy_library,
    hold_shipped,
    project,
    write,
    write_list,
    write_piece,
    yaml_text,
)
from tests.visual_engine import COMPONENTS, FakeEnv, block, draw, layout, top

pl, checks, reading, findings, files, libraries, full_read = load(
    "visual-communication",
    "pipeline",
    "checks",
    "reading",
    "findings",
    "files",
    "libraries",
    "full_read",
)

#: The test brand that gives the sizes of `device`, built on the foundations being built.
SIZED_BRAND = FIXTURES / "libraries" / "test-brand" / "1.1.0"
#: The test brand's drawing of the deck's cover.
DRAWING = FIXTURES / "drawings" / "cover.yaml"
PIECE = "talk"
BRAND_COMPONENTS = "visual/libraries/test-brand/1.1.0/components"
#: The brand the tests build on the test brand, and its folder of components.
EDITION = "test-edition"
EDITION_COMPONENTS = "visual/libraries/test-edition/1.0.0/components"
#: The list's entry for a version of the project's own that is not released.
UNRELEASED = {"released": False}

#: The deck's pages a piece's content gives, unless a test gives others.
SLIDES = [
    {"id": "opening", "layout": "cover", "title": "The flow", "author": "Ada"},
    {"id": "first", "layout": "slide", "title": "It works"},
]


# --- a project of a deck under the test brand ---------------------------------------------------


def cover(**changes: Any) -> dict[str, Any]:
    """The fixture's drawing of the cover, each of `changes` set at its dotted key path, or
    removed where it is None."""
    data = copy.deepcopy(dict(reading.read_yaml(DRAWING)))
    for path, value in changes.items():
        *parents, last = path.split("__")
        at = data
        for key in parents:
            at = at[key]
        if value is None:
            at.pop(last, None)
        else:
            at[last] = value
    return data


def hold(
    root: Path, data: dict[str, Any], name: str = "cover", into: str = BRAND_COMPONENTS
) -> Path:
    """A component a brand holds, the test brand unless `into` names another's folder of
    components, written as `components/<name>.yaml`."""
    return write(root / into / f"{name}.yaml", yaml_text(data))


def write_slides(
    root: Path, language: str = "en", slides: list[dict[str, Any]] | None = None
) -> None:
    write(
        root / "visual" / "pieces" / PIECE / f"content.{language}.yaml",
        yaml_text(bound("content", slides=list(SLIDES if slides is None else slides))),
    )


def brands(tmp_path: Path, *, edition: bool = False) -> tuple[Path, str]:
    """A project that holds the foundations being built and the test brand that gives sizes,
    and with `edition` the test edition built on it, neither brand released; and the
    foundations' version."""
    root = project(tmp_path)
    copy_library(root, SIZED_BRAND, "test-brand", "1.1.0")
    listed = {"test-brand": {"source": {"kind": "project"}, "versions": {"1.1.0": UNRELEASED}}}
    if edition:
        copy_library(root, TEST_EDITION, EDITION, "1.0.0")
        listed[EDITION] = {"source": {"kind": "project"}, "versions": {"1.0.0": UNRELEASED}}
    write_list(root, listed)
    return root, hold_shipped(root, "foundations").version


def deck(
    tmp_path: Path,
    *,
    languages: tuple[str, ...] = ("en",),
    devices: tuple[str, ...] = ("desktop",),
    drawing: dict[str, Any] | None = None,
) -> Path:
    """A project that holds the foundations being built and the test brand that gives sizes,
    and the deck `talk` under it in `languages`, drawn on `devices`. The brand holds the
    fixture's cover, or `drawing`."""
    root, built = brands(tmp_path)
    write_piece(
        root,
        PIECE,
        top="foundations/deck",
        languages=list(languages),
        modes={"device": list(devices)},
        lock={"foundations": built, "test-brand": "1.1.0"},
    )
    for language in languages:
        write_slides(root, language)
    hold(root, cover() if drawing is None else drawing)
    return root


def project_of(root: Path) -> Any:
    piece = pl.read_piece(root, "visual", PIECE)
    return pl.Project(piece, piece.lock, pl.Held(root, "visual"))


def scenes(root: Path, **given: Any) -> list[tuple[str, Any]]:
    drawn = project_of(root)
    return list(drawn.scenes(facts=drawn.piece.stand_ins, **given))


def group(result: Any, trace: str) -> dict[str, Any]:
    element = result.scene.find(trace)
    assert element is not None, f"no element {trace}"
    return dict(element.properties)


def traces(result: Any, below: str) -> set[str]:
    """The trace id of each element at or below `below`."""
    found, stack = set(), list(result.scene.children)
    while stack:
        element = stack.pop()
        if element.id == below or element.id.startswith(f"{below}/"):
            found.add(element.id)
        stack.extend(element.children)
    return found


def misfits(result: Any) -> list[Any]:
    return [f for f in result.findings if f.code == layout.DRAWING_MISFIT]


COVER = "deck/slides[opening]"


# --- the brand's drawing draws the cover ---------------------------------------------------------


def test_the_brands_drawing_draws_the_cover_and_its_group_names_it_with_its_version(
    tmp_path: Path,
) -> None:
    [(_, result)] = scenes(deck(tmp_path))
    page = group(result, COVER)
    assert (page["component"], page["version"], page["page"]) == ("test-brand/cover", "1.1.0", True)
    assert group(result, f"{COVER}/title")["text"] == "The flow"
    assert f"{COVER}/band" in traces(result, COVER)
    # The slide's layout the brand does not draw is drawn by the deck's own drawing.
    assert group(result, "deck/slides[first]")["component"] == "foundations/deck"
    assert misfits(result) == []


def test_what_a_field_shows_keeps_its_trace_id_under_either_drawing(tmp_path: Path) -> None:
    """The instance keeps its id, and each field the cover shows keeps the id of the
    instance and the field's name (DEC-034 point 5). The drawing's other parts take ids of
    their own."""
    [(_, brand)] = scenes(deck(tmp_path / "brand"))
    root = deck(tmp_path / "own")
    (root / BRAND_COMPONENTS / "cover.yaml").unlink()
    [(_, own)] = scenes(root)
    fields = {f"{COVER}/title", f"{COVER}/author"}
    assert fields <= traces(brand, COVER) & traces(own, COVER)
    assert group(own, COVER)["component"] == "foundations/deck"
    assert group(brand, f"{COVER}/author")["text"] == group(own, f"{COVER}/author")["text"]
    assert f"{COVER}/rule" in traces(own, COVER) - traces(brand, COVER)


def test_a_drawing_of_a_page_takes_the_decks_width_and_height(tmp_path: Path) -> None:
    """The deck writes what each page gets, so a drawing changes neither (DEC-034 point 2)."""
    [(_, result)] = scenes(deck(tmp_path))
    top_group = result.scene.children[0].properties
    page = group(result, COVER)
    assert (page["width"], page["height"]) == (top_group["width"], top_group["height"])


def test_two_drawings_of_one_layout_draw_neither(tmp_path: Path) -> None:
    root = deck(tmp_path)
    hold(root, cover(), "second-cover")
    [(_, result)] = scenes(root)
    assert group(result, COVER)["component"] == "foundations/deck"


# --- fit, in every language and at every key -----------------------------------------------------


def without_link() -> dict[str, Any]:
    return cover(parts__link=None)


def test_a_page_the_drawing_does_not_fit_is_drawn_by_the_decks_own_and_stated(
    tmp_path: Path,
) -> None:
    root = deck(tmp_path, drawing=without_link())
    slides = [
        {"id": "opening", "layout": "cover", "title": "The flow", "link": "example.org"},
        {"id": "closing", "layout": "cover", "title": "Thanks"},
    ]
    write_slides(root, slides=slides)
    [(_, result)] = scenes(root)
    assert group(result, COVER)["component"] == "foundations/deck"
    assert group(result, f"{COVER}/link")["text"] == "example.org"
    assert group(result, "deck/slides[closing]")["component"] == "test-brand/cover"
    [stated] = misfits(result)
    assert (stated.level, stated.where, stated.extra) == (findings.FACT, COVER, {"piece": True})
    assert "`test-brand/cover` does not take the field `link`, in `en` at `default`" in (
        stated.message
    )


def test_a_drawing_that_does_not_fit_in_one_language_draws_that_page_in_none(
    tmp_path: Path,
) -> None:
    root = deck(tmp_path, languages=("en", "cs"), drawing=without_link())
    write_slides(root, "cs", [{**SLIDES[0], "link": "example.cz"}, SLIDES[1]])
    found = scenes(root)
    assert [language for language, _ in found] == ["en", "cs"]
    for _, result in found:
        assert group(result, COVER)["component"] == "foundations/deck"
        [stated] = misfits(result)
        assert "in `cs` at `default`" in stated.message


def test_a_preview_in_one_language_takes_the_drawing_chosen_for_the_whole_piece(
    tmp_path: Path,
) -> None:
    root = deck(tmp_path, languages=("en", "cs"), drawing=without_link())
    write_slides(root, "cs", [{**SLIDES[0], "link": "example.cz"}, SLIDES[1]])
    [(language, result)] = scenes(root, languages=["en"])
    assert language == "en"
    assert group(result, COVER)["component"] == "foundations/deck"


def test_a_drawing_that_does_not_fit_at_one_key_draws_that_page_at_none(tmp_path: Path) -> None:
    """A part a size hides takes nothing at that size."""
    hidden = {"by": ":device", "desktop": "author", "phone": False}
    root = deck(tmp_path, devices=("desktop", "phone"), drawing=cover(parts__author__when=hidden))
    found = scenes(root)
    assert sorted(result.scene.size_key for _, result in found) == ["default", "device.phone"]
    for _, result in found:
        assert group(result, COVER)["component"] == "foundations/deck"
    [stated] = misfits(found[0][1])
    assert "does not take the field `author`, in `en` at `device.phone`" in stated.message


def test_a_brand_that_draws_no_layout_draws_as_before(tmp_path: Path) -> None:
    root = deck(tmp_path)
    (root / BRAND_COMPONENTS / "cover.yaml").unlink()
    drawn = project_of(root)
    assert drawn.drawings == {}
    choice = drawn.choice()
    assert (dict(choice.drawings), dict(choice.refused)) == ({}, {})


# --- the check ---------------------------------------------------------------------------------


def judged(root: Path, code: str) -> list[tuple[str, str, str]]:
    return [
        (level, finding.file, finding.where)
        for finding, level in checks.check(root).judged
        if finding.code == code
    ]


def test_the_brand_checked_alone_judges_each_drawing_it_holds(tmp_path: Path) -> None:
    """A drawing that holds what the content gives fails in the brand's version, though no
    piece draws it."""
    root = deck(tmp_path)
    hold(root, cover(fields={"type": "object"}, draws={"top": "foundations/deck", "layout": "end"}))
    found = judged(root, layout.DRAWING_SHAPE)
    file = f"{BRAND_COMPONENTS}/cover.yaml"
    assert ("fails", file, "fields") in found
    assert ("fails", file, "draws") in found


def test_the_check_states_at_the_piece_each_page_left_to_the_decks_own_drawing(
    tmp_path: Path,
) -> None:
    root = deck(tmp_path, drawing=without_link())
    write_slides(root, slides=[{**SLIDES[0], "link": "example.org"}, SLIDES[1]])
    assert judged(root, layout.DRAWING_MISFIT) == [
        ("fact", f"visual/pieces/{PIECE}/piece.yaml", COVER)
    ]


def test_a_component_library_whose_component_declares_draws_fails(tmp_path: Path) -> None:
    root = deck(tmp_path)
    data = {**cover(), "status": "experimental"}
    write(
        root
        / "visual/libraries/foundations"
        / str(project_of(root).lock["foundations"])
        / "components"
        / "cover.yaml",
        yaml_text(data),
    )
    found = judged(root, layout.DRAWING_SHAPE)
    assert any(where == "draws" and "foundations" in file for _, file, where in found)


# --- the format ------------------------------------------------------------------------------


def test_the_fixtures_drawing_holds_the_schema() -> None:
    assert files.shape_problems(cover(), "component") == []


@pytest.mark.parametrize(
    "key", ["fields", "options", "states", "colour", "lists", "layouts", "ends"]
)
def test_the_schema_refuses_a_drawing_that_declares_what_the_content_gives(key: str) -> None:
    assert files.shape_problems(cover(**{key: True}), "component") != []


def test_the_schema_refuses_a_drawing_that_names_no_layout() -> None:
    assert files.shape_problems(cover(draws={"top": "foundations/deck"}), "component") != []


# --- the engine: what a drawing declares and writes ------------------------------------------


def look(parts: dict[str, Any], **keys: Any) -> dict[str, Any]:
    """A brand's drawing of `lab/top`'s layout `frame`."""
    return {
        "status": "experimental",
        "about": "A drawing a test draws.",
        "draws": {"top": "lab/top", "layout": "frame"},
        "parts": dict(parts),
        "preferred": {"width": "=@space.4 * 10", "height": "=@space.4"},
        **keys,
    }


CAPTION = {"text": {"content": "caption", "style": "type.body", "fill": "text-primary"}}
CHOICE = layout.Choice({("lab/top", "frame"): "brand/look"})


def lab_top(**keys: Any) -> dict[str, Any]:
    fields = {"caption": {"type": "string"}, "note": {"type": "string"}, **keys.pop("fields", {})}
    parts = keys.pop(
        "parts",
        {"caption": CAPTION, "note": {**CAPTION, "text": {**CAPTION["text"], "content": "note"}}},
    )
    return top(parts, fields=fields, **keys)


def issues(
    drawing: dict[str, Any], *, use: str = "brand/look", **more: Any
) -> list[tuple[str, str]]:
    env = FakeEnv(components={"lab/top": lab_top(), use: drawing, **more})
    component = layout.Context(env, "en").component(use)
    assert component is not None
    return [(code, where) for code, where, _ in component.issues]


@pytest.mark.parametrize("key", layout.GIVEN_BY_TOP)
def test_a_drawing_that_declares_what_the_content_gives_fails(key: str) -> None:
    assert (layout.DRAWING_SHAPE, key) in issues(look({"caption": CAPTION}, **{key: {}}))


def test_a_piece_s_own_component_declares_no_drawing() -> None:
    found = issues(look({"caption": CAPTION}), use="piece/look")
    assert (layout.DRAWING_SHAPE, layout.DRAWS) in found


def test_a_drawing_of_a_layout_the_top_does_not_declare_draws_nothing() -> None:
    drawing = look({"caption": CAPTION}, draws={"top": "lab/top", "layout": "cover"})
    assert (layout.DRAWING_SHAPE, layout.DRAWS) in issues(drawing)
    env = FakeEnv(components={"lab/top": lab_top(), "brand/look": drawing})
    choice = layout.Choice({("lab/top", "cover"): "brand/look"})
    root = layout.place_top(layout.Context(env, "en", choice=choice), "lab/top", {})
    assert root is not None and root.component.use == "lab/top"


def test_a_drawing_that_reads_a_token_of_its_top_fails() -> None:
    reading_token = {**CAPTION, "text": {**CAPTION["text"], "fill": "component.lab.top.ink"}}
    env = FakeEnv(components={"lab/top": lab_top(), "brand/look": look({"caption": reading_token})})
    component = layout.Context(env, "en").component("brand/look")
    assert component is not None
    [(code, where, message)] = component.issues
    assert (code, where) == (layout.TOKEN_UNDECLARED, "parts.caption.text.fill")
    assert "a drawing reads none of its top's tokens" in message


def page_look(preferred: dict[str, Any] | None) -> dict[str, Any]:
    drawing = {
        "status": "experimental",
        "about": "A brand's cover.",
        "draws": {"top": "foundations/deck", "layout": "cover"},
        "parts": {
            "title": {"text": {"content": "title", "style": "type.heading", "fill": "text-primary"}}
        },
    }
    return drawing if preferred is None else {**drawing, "preferred": preferred}


def test_a_drawing_of_a_page_writes_no_width() -> None:
    found = issues(page_look({"width": "=@size.slide", "height": "=title.bottom"}))
    assert found == [(layout.DRAWING_SIZE, "preferred.width")]


def test_a_drawing_of_a_page_writes_its_height_where_the_top_asks_for_none() -> None:
    deck_data = copy.deepcopy(COMPONENTS["foundations/deck"])
    del deck_data["preferred"]["height"]
    deck_data["layouts"]["cover"]["preferred"] = {"height": "=title.bottom"}
    deck_data["layouts"]["slide"]["preferred"] = {"height": "=title.bottom"}
    env = FakeEnv(components={"foundations/deck": deck_data, "brand/look": page_look(None)})
    component = layout.Context(env, "en").component("brand/look")
    assert component is not None
    assert [(c, w) for c, w, _ in component.issues] == [(layout.DRAWING_SIZE, "preferred")]
    assert issues(page_look(None)) == []


def test_a_drawing_of_a_whole_top_writes_its_own_size() -> None:
    result = draw(
        {"caption": "A caption."},
        components={"lab/top": lab_top(), "brand/look": look({"caption": CAPTION})},
        choice=CHOICE,
    )
    root = result.scene.children[0].properties
    assert (root["component"], root["width"], root["height"]) == ("brand/look", 320.0, 32.0)
    assert result.scene.find("top/caption") is not None


# --- the engine: fields named after the field --------------------------------------------------


def test_a_field_shown_by_no_part_named_after_it_fails() -> None:
    assert issues(look({"heading": CAPTION})) == [(layout.FIELD_PART, "parts")]


def test_a_part_named_after_a_field_that_shows_another_fails() -> None:
    other = {**CAPTION, "text": {**CAPTION["text"], "content": "note"}}
    found = issues(look({"caption": other, "note": other}))
    assert found == [(layout.FIELD_PART, "parts.caption")]


def test_a_field_shown_only_through_a_placed_component_fails() -> None:
    passed = {"use": "lab/label", "fields": {"text": "caption"}}
    label = block(
        {"text": {**CAPTION, "text": {**CAPTION["text"], "content": "text"}}},
        fields={"text": {"type": "string"}},
    )
    env = FakeEnv(
        components={"lab/top": lab_top(), "lab/label": label, "brand/look": look({"band": passed})}
    )
    component = layout.Context(env, "en").component("brand/look")
    assert component is not None
    [(code, where, message)] = component.issues
    assert (code, where) == (layout.FIELD_PART, "parts")
    assert "passes `caption` on to a component it places" in message


def test_a_tops_own_drawing_that_breaks_the_rule_asks_for_attention() -> None:
    own = lab_top(parts={"heading": CAPTION})
    component = layout.Context(FakeEnv(components={"lab/top": own}), "en").component("lab/top")
    assert component is not None and component.issues == []
    [finding] = layout.own_drawing_findings(component, file="top.yaml", library="lab@1.0.0")
    assert (finding.code, finding.level, finding.who) == (
        layout.FIELD_PART,
        findings.ATTENTION,
        "the top's owner",
    )


# --- the engine: what a drawing takes ---------------------------------------------------------


def placed(
    drawing: dict[str, Any], content: dict[str, Any], **more: Any
) -> tuple[Any, dict[str, str]]:
    """The piece's top, `lab/top` or `use`, placed with `content`, `lab/top` under `drawing`,
    and what did not fit."""
    use, lab = more.pop("use", "lab/top"), more.pop("top", lab_top())
    env = FakeEnv(components={"lab/top": lab, "brand/look": drawing, **more})
    ctx = layout.Context(env, "en", choice=CHOICE)
    root = layout.place_top(ctx, use, content)
    return root, ctx.misfits


def test_a_drawing_takes_each_field_it_shows() -> None:
    _, found = placed(look({"caption": CAPTION}), {"caption": "Shown."})
    assert found == {}
    _, found = placed(look({"caption": CAPTION}), {"caption": "Shown.", "note": "Not."})
    assert found == {"top": "`brand/look` does not take the field `note`"}


TONE = {"tone": ["plain", "loud"]}


def test_a_drawing_takes_the_word_the_content_chose_where_it_reads_it() -> None:
    toned = lab_top(options=TONE)
    _, found = placed(look({"caption": CAPTION}), {"tone": "loud"}, top=toned)
    assert found == {"top": "`brand/look` does not take the word `loud` of the option `tone`"}
    reads = look({"caption": {**CAPTION, "when": {"tone": ["loud"]}}})
    assert placed(reads, {"tone": "loud"}, top=toned)[1] == {}


def test_a_drawing_takes_a_part_the_content_points_at_another_role_where_it_paints_it() -> None:
    content = {"override": {"frame": "accent"}}
    _, found = placed(look({"caption": CAPTION}), content)
    assert found == {
        "top": "`brand/look` does not take the part `frame`, which `override` "
        "points at another role"
    }
    framed = look(
        {
            "caption": CAPTION,
            "frame": {"box": {"fill": "surface"}, "width": "=:width", "height": "=:height"},
        }
    )
    assert placed(framed, content)[1] == {}


RUNS = {"type": "string", "x-pkit-runs": ["plain", "strong"]}
CHOOSING = {
    "text": {
        "content": "note",
        "style": {"by": "note", "plain": "type.body", "strong": "type.heading"},
        "fill": "text-primary",
    }
}


def test_a_drawing_takes_a_runs_word_where_its_text_chooses_by_the_words() -> None:
    runs_top = lab_top(fields={"note": RUNS}, parts={"note": CHOOSING})
    content = {"note": [{"text": "Bold", "style": "strong"}]}
    fixed = look({"note": {**CAPTION, "text": {**CAPTION["text"], "content": "note"}}})
    _, found = placed(fixed, content, top=runs_top)
    assert found == {"top": "`brand/look` does not take the word `strong` of the runs of `note`"}
    assert placed(look({"note": CHOOSING}), content, top=runs_top)[1] == {}
    assert placed(fixed, {"note": "Plain text."}, top=runs_top)[1] == {}


LISTED = {"type": "array", "items": {"type": "object"}}
CARD = block(
    {"b": {"box": {"fill": "surface"}, "width": "=:width", "height": "=:height"}},
    preferred={"width": "=@space.4", "height": "=@space.4"},
)
ARROW = block({"l": {"line": {"stroke": "line"}, "connect": "straight"}}, ends=True)


def test_a_drawing_takes_each_end_of_its_ties_where_it_is_found_under_it() -> None:
    """An end drawn twice under the drawing is not found, so the drawing does not fit
    (DEC-011 point 5)."""
    steps = {"repeat": "steps", "draw": "lab/card", "row": {"gap": "=@space.4"}}
    links = {"repeat": "links", "draw": "lab/arrow"}
    tied = top(
        {"steps": steps, "links": links},
        fields={"steps": LISTED, "links": LISTED},
        lists={"links": {"ends": ["from", "to"]}},
    )
    content = {
        "steps": [{"id": "a"}, {"id": "b"}],
        "links": [{"id": "ab", "from": {"item": "steps[a]"}, "to": {"item": "steps[b]"}}],
    }
    parts = {"lab/card": CARD, "lab/arrow": ARROW}
    twice = look({"steps": steps, "again": steps, "links": links})
    _, found = placed(twice, content, top=tied, **parts)
    assert found == {"top": "`brand/look` does not take an end of the tie `top/links[ab]`"}
    _, fits = placed(look({"steps": steps, "links": links}), content, top=tied, **parts)
    assert fits == {}


def test_a_drawing_takes_each_part_its_top_exposes_where_a_component_places_the_top() -> None:
    exposing = lab_top(exposes=["caption"])
    holder = block(
        {"slot": {"slot": "body", "width": "=:width"}}, fields={"body": {"type": "object"}}
    )
    content = {"body": {"use": "lab/top", "caption": "Placed."}}
    _, found = placed(
        look({"caption": CAPTION}),
        content,
        top=exposing,
        **{"lab/holder": holder, "use": "lab/holder"},
    )
    assert found == {"holder/slot": "`brand/look` does not take the exposed part `caption`"}
    _, alone = placed(look({"caption": CAPTION}), {"caption": "Alone."}, top=exposing)
    assert alone == {}


# --- placing a drawing -------------------------------------------------------------------------


def test_content_that_places_a_drawing_by_use_fails() -> None:
    holder = block(
        {"slot": {"slot": "body", "width": "=:width"}}, fields={"body": {"type": "object"}}
    )
    result = draw(
        {"body": {"use": "brand/look"}},
        use="lab/holder",
        components={
            "lab/holder": holder,
            "lab/top": lab_top(),
            "brand/look": look({"caption": CAPTION}),
        },
    )
    [finding] = [f for f in result.findings if f.code == layout.DRAWING_PLACED]
    assert finding.extra == {}
    assert result.scene.find("holder/slot") is None


def test_a_component_that_places_a_drawing_by_use_fails() -> None:
    holder = block({"inner": {"use": "brand/look", "width": "=:width"}})
    result = draw(
        use="lab/holder",
        components={
            "lab/holder": holder,
            "lab/top": lab_top(),
            "brand/look": look({"caption": CAPTION}),
        },
    )
    [finding] = [f for f in result.findings if f.code == layout.DRAWING_PLACED]
    assert finding.extra["component"] == "lab/holder"


def test_a_piece_whose_top_is_a_drawing_fails_at_the_piece() -> None:
    result = draw(
        use="brand/look",
        components={"lab/top": lab_top(), "brand/look": look({"caption": CAPTION})},
    )
    [finding] = [f for f in result.findings if f.code == layout.DRAWING_PLACED]
    assert finding.extra == {"piece": True}
    assert result.scene.children == []


def test_a_drawing_never_draws_where_no_choice_names_it() -> None:
    """Every file format 1 accepted draws as before: with no choice, the top draws."""
    result = draw(
        {"caption": "A caption."},
        components={"lab/top": lab_top(), "brand/look": look({"caption": CAPTION})},
    )
    assert result.scene.children[0].properties["component"] == "lab/top"


# --- along a chain of brands -------------------------------------------------------------------


PIECE_FILE = f"visual/pieces/{PIECE}/piece.yaml"


def chain(tmp_path: Path, *, top: str = "foundations/deck", brand: str = EDITION) -> Path:
    """A project that holds the foundations being built, the test brand and the test edition
    built on it, neither holding a component, and the piece `talk` of `top` under `brand`,
    locked at all three, with the deck's slides as its content."""
    root, built = brands(tmp_path, edition=True)
    lock = {"foundations": built, "test-brand": "1.1.0", EDITION: "1.0.0"}
    write_piece(root, PIECE, top=top, brand=brand, lock=lock)
    write_slides(root)
    return root


def stated(root: Path, code: str) -> list[tuple[Any, str]]:
    """Each finding the check makes of the code `code`, with its level."""
    return [
        (finding, level) for finding, level in checks.check(root).judged if finding.code == code
    ]


def test_a_brand_built_on_a_base_draws_each_page_of_a_top_its_base_does_not_serve_it_fits(
    tmp_path: Path,
) -> None:
    root = chain(tmp_path)
    hold(root, without_link(), into=EDITION_COMPONENTS)
    slides = [
        {"id": "opening", "layout": "cover", "title": "The flow"},
        {"id": "closing", "layout": "cover", "title": "Thanks", "link": "example.org"},
    ]
    write_slides(root, slides=slides)
    [(_, result)] = scenes(root)
    page = group(result, COVER)
    assert (page["component"], page["version"]) == ("test-edition/cover", "1.0.0")
    assert group(result, "deck/slides[closing]")["component"] == "foundations/deck"
    [stated_misfit] = misfits(result)
    assert stated_misfit.where == "deck/slides[closing]"


def test_a_bases_drawing_draws_under_a_brand_built_on_it(tmp_path: Path) -> None:
    root = chain(tmp_path)
    hold(root, cover())
    [(_, result)] = scenes(root)
    assert group(result, COVER)["component"] == "test-brand/cover"
    assert project_of(root).kept == {}


def test_where_a_base_serves_a_top_the_brand_built_on_it_draws_none_of_it_and_the_piece_says_so(
    tmp_path: Path,
) -> None:
    """The base draws the cover, so it serves the deck: its cover draws, the slide it leaves
    to the deck draws by the deck's own drawing, and the edition's drawings of either draw
    nothing (DEC-009 point 4, DEC-034 point 8)."""
    root = chain(tmp_path)
    hold(root, cover())
    hold(root, cover(), into=EDITION_COMPONENTS)
    slide = cover(draws={"top": "foundations/deck", "layout": "slide"})
    hold(root, slide, "slide", into=EDITION_COMPONENTS)
    [(_, result)] = scenes(root)
    assert group(result, COVER)["component"] == "test-brand/cover"
    assert group(result, "deck/slides[first]")["component"] == "foundations/deck"
    found = stated(root, checks.DRAWING_BASE_SERVES)
    assert [(f.file, f.where, level) for f, level in found] == [(PIECE_FILE, "lock", "fact")] * 2
    assert [f.message for f, _ in found] == [
        f"the drawing `test-edition/{name}` draws nothing under this lock: test-brand@1.1.0, "
        "which its brand builds on, serves `foundations/deck`, and keeps its form"
        for name in ("cover", "slide")
    ]


def test_a_brand_with_no_base_keeps_its_own_drawings(tmp_path: Path) -> None:
    root = deck(tmp_path)
    assert project_of(root).kept == {}
    assert stated(root, checks.DRAWING_BASE_SERVES) == []


# --- a top a brand holds -----------------------------------------------------------------------


#: A top a brand holds, a page alone: its title on its background.
POSTER = bound(
    "component",
    status="experimental",
    about="A poster a brand holds: its title on its background.",
    fields={"type": "object", "required": ["title"], "properties": {"title": {"type": "string"}}},
    layouts={"poster": {"slots": {"title": {}}}},
    parts={
        "background": {"box": {"fill": "surface"}, "width": "=:width", "height": "=:height"},
        "title": {
            "text": {"content": "title", "style": "type.heading", "fill": "text-primary"},
            "x": "=@space.3",
            "y": "=@space.3",
            "width": "=:width - 2 * @space.3",
        },
    },
    preferred={"width": "=@size.figure", "height": "=title.bottom + @space.3"},
)

COMPONENTS_OF = {"test-brand": BRAND_COMPONENTS, EDITION: EDITION_COMPONENTS}


def poster(tmp_path: Path, *, holder: str, brand: str) -> Path:
    """The piece `talk` of the poster that the brand `holder` holds, under `brand`."""
    root = chain(tmp_path, top=f"{holder}/poster", brand=brand)
    hold(root, POSTER, "poster", into=COMPONENTS_OF[holder])
    write(
        root / "visual" / "pieces" / PIECE / "content.en.yaml",
        yaml_text(bound("content", title="Come along")),
    )
    return root


def poster_look(holder: str) -> dict[str, Any]:
    """A brand's drawing of the poster that `holder` holds."""
    return bound(
        "component",
        status="experimental",
        about="A drawing of a poster a brand holds.",
        draws={"top": f"{holder}/poster", "layout": "poster"},
        parts={"title": POSTER["parts"]["title"]},
        preferred={"width": "=@size.figure", "height": "=title.bottom"},
    )


@pytest.mark.parametrize("brand", ["test-brand", EDITION])
def test_a_top_a_brand_holds_is_drawn_by_its_own_drawing_under_it_and_a_brand_built_on_it(
    tmp_path: Path, brand: str
) -> None:
    """The holding brand serves the top by its own drawing, and lacks none of its layouts,
    so nothing is stated (DEC-034 point 4)."""
    root = poster(tmp_path, holder="test-brand", brand=brand)
    [(_, result)] = scenes(root)
    assert group(result, "poster")["component"] == "test-brand/poster"
    assert group(result, "poster/title")["text"] == "Come along"
    found = {finding.code for finding, _ in checks.check(root).judged}
    assert not found & {checks.TOP_OF_OTHER_BRAND, checks.DRAWING_BASE_SERVES}
    assert misfits(result) == []


@pytest.mark.parametrize("into", [BRAND_COMPONENTS, EDITION_COMPONENTS])
def test_no_drawing_of_a_top_a_brand_holds_draws_and_the_check_fails_it(
    tmp_path: Path, into: str
) -> None:
    """In the holding brand or in a brand built on it, the drawing draws nothing, and fails
    in its own brand's version (DEC-034 points 4 and 10)."""
    root = poster(tmp_path, holder="test-brand", brand=EDITION)
    hold(root, poster_look("test-brand"), "look", into=into)
    [(_, result)] = scenes(root)
    assert group(result, "poster")["component"] == "test-brand/poster"
    [(finding, level)] = stated(root, layout.DRAWING_HELD_TOP)
    assert (level, finding.file, finding.where) == ("fails", f"{into}/look.yaml", "draws")
    assert "a top the brand test-brand@1.1.0 holds" in finding.message
    # A release reads it as the check alone does.
    name, version = into.split("/")[2:4]
    read = full_read.read(libraries.Held(root, "visual"), name, libraries.Version.parse(version))
    assert [f.file for f in read.findings if f.code == layout.DRAWING_HELD_TOP] == [finding.file]


@pytest.mark.parametrize("named", ["nothing-here", "plain"])
def test_a_drawing_of_a_brands_component_that_is_no_top_fails_as_drawing_nothing_alone(
    tmp_path: Path, named: str
) -> None:
    """A drawing that names a component the brand does not hold, or one it holds that is no
    top, draws no layout of a top. It fails as that, and never as a drawing of a top the
    brand holds, where its brand is checked alone and where a release reads it (DEC-034
    points 1 and 4)."""
    root = poster(tmp_path, holder="test-brand", brand=EDITION)
    hold(root, {key: value for key, value in POSTER.items() if key != "layouts"}, "plain")
    draws = {"top": f"test-brand/{named}", "layout": "poster"}
    hold(root, {**poster_look("test-brand"), "draws": draws}, "look", into=EDITION_COMPONENTS)
    file = f"{EDITION_COMPONENTS}/look.yaml"
    assert ("fails", file, "draws") in judged(root, layout.DRAWING_SHAPE)
    assert judged(root, layout.DRAWING_HELD_TOP) == []
    read = full_read.read(libraries.Held(root, "visual"), EDITION, libraries.Version.parse("1.0.0"))
    codes = {finding.code for finding in read.findings}
    assert layout.DRAWING_SHAPE in codes
    assert layout.DRAWING_HELD_TOP not in codes


def test_a_top_a_brand_holds_under_another_brand_asks_its_author_for_attention(
    tmp_path: Path,
) -> None:
    """The edition holds the poster, and the test brand is neither the edition nor built
    on it: the poster is drawn by its own drawing in the test brand's values, the lock names
    the edition, and the piece's author is asked to look (DEC-034 point 4)."""
    root = poster(tmp_path, holder=EDITION, brand="test-brand")
    drawn = project_of(root)
    [(_, result)] = scenes(root)
    assert group(result, "poster")["component"] == "test-edition/poster"
    assert EDITION in pl.needed(drawn.piece)
    lock = libraries.move_lock(pl.Held(root, "visual"), pl.needed(drawn.piece)).lock
    assert lock[EDITION] == "1.0.0"
    [(finding, level)] = stated(root, checks.TOP_OF_OTHER_BRAND)
    assert (level, finding.file, finding.where, finding.who) == (
        "attention",
        PIECE_FILE,
        "top",
        "the piece's author",
    )
    assert finding.message == (
        "the top `test-edition/poster` is the form of the brand test-edition@1.0.0, and the "
        "piece's brand test-brand@1.1.0 is neither that brand nor built on it: the top is "
        "drawn by its own drawing, in the values of test-brand@1.1.0"
    )
