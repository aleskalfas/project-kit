"""A brand's drawing of a layout (visual-communication DEC-034 points 1, 2, 3, 5 and 6, DEC-009
points 2, 5 and 6): a component of the brand whose file names, under `draws`, the top and
the layout it draws.

- **The declaration.** It declares nothing the content gives, reads none of its top's
  component tokens, and only a brand's component declares one (point 1). Content, or a
  component, that places one by `use` fails (DEC-009 point 5).
- **Sizes.** A drawing of a page's form writes its page's height alone, and writes it where
  the top asks for none, by a formula or through its physical size; a drawing of a top
  whose one layout is the whole top writes its own `preferred`, but for a height its top's
  physical size sets; and a drawing declares no physical size (points 2 and 3).
- **Trace ids.** The instance keeps its id, and what a field shows keeps the same trace id,
  under every drawing; the instance's group names the drawing and its brand's version. A
  brand's drawing that shows a field by no part named after it fails; a top's own asks
  for attention (point 5).
- **Fit.** A brand's drawing draws an instance where it fits it in every language and at
  every key, and the top's own drawing draws it in all of them where it does not, which
  the piece states (point 6). A preview in one language takes the drawing chosen for the
  whole piece.

The engine's rules are drawn from components written as mappings in memory (`FakeEnv`);
the deck under the test brand from a project in a temporary folder, its drawing of the
cover the committed fixture `drawings/cover.yaml`.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load
from tests.visual_communication_project import (
    FIXTURES,
    bound,
    copy_library,
    hold_shipped,
    project,
    write,
    write_list,
    write_piece,
    yaml_text,
)
from tests.visual_engine import COMPONENTS, FakeEnv, block, codes, draw, layout, top

pl, checks, reading, findings, files = load(
    "visual-communication", "pipeline", "checks", "reading", "findings", "files"
)

#: The test brand that gives the sizes of `device`, built on the foundations being built.
SIZED_BRAND = FIXTURES / "libraries" / "test-brand" / "1.1.0"
#: The test brand's drawing of the deck's cover.
DRAWING = FIXTURES / "drawings" / "cover.yaml"
PIECE = "talk"
BRAND_COMPONENTS = "visual/libraries/test-brand/1.1.0/components"

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


def hold(root: Path, data: dict[str, Any], name: str = "cover") -> Path:
    """A component the test brand holds, written as `components/<name>.yaml`."""
    return write(root / BRAND_COMPONENTS / f"{name}.yaml", yaml_text(data))


def write_slides(
    root: Path, language: str = "en", slides: list[dict[str, Any]] | None = None
) -> None:
    write(
        root / "visual" / "pieces" / PIECE / f"content.{language}.yaml",
        yaml_text(bound("content", slides=list(SLIDES if slides is None else slides))),
    )


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
    root = project(tmp_path)
    copy_library(root, SIZED_BRAND, "test-brand", "1.1.0")
    unreleased = {"1.1.0": {"released": False}}
    write_list(root, {"test-brand": {"source": {"kind": "project"}, "versions": unreleased}})
    built = hold_shipped(root, "foundations").version
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
    """A drawing that holds what the content gives, or carries a status, fails in the
    brand's version, though no piece draws it."""
    root = deck(tmp_path)
    drawn = {"top": "foundations/deck", "layout": "end"}
    hold(root, cover(fields={"type": "object"}, status="stable", draws=drawn))
    found = judged(root, layout.DRAWING_SHAPE)
    file = f"{BRAND_COMPONENTS}/cover.yaml"
    assert ("fails", file, "fields") in found
    assert ("fails", file, "status") in found
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
    data = cover()
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


def test_the_schema_asks_a_status_of_every_component_but_a_drawing() -> None:
    """Every component but a drawing carries a status (DEC-034 point 8)."""
    assert files.shape_problems(cover(status="experimental"), "component") != []
    no_drawing = cover(draws=None, status=None)
    assert files.shape_problems(no_drawing, "component") != []
    assert files.shape_problems({**no_drawing, "status": "stable"}, "component") == []


# --- the engine: what a drawing declares and writes ------------------------------------------


def look(parts: dict[str, Any], **keys: Any) -> dict[str, Any]:
    """A brand's drawing of `lab/top`'s layout `frame`."""
    return {
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


def test_a_drawing_that_carries_a_status_fails() -> None:
    assert (layout.DRAWING_SHAPE, layout.STATUS) in issues(
        look({"caption": CAPTION}, status="stable")
    )


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


# --- the engine: a drawing of a top with a physical size ---------------------------------------

#: A poster's trim size, A1 upright, in millimetres (DEC-034 point 3), and the height it
#: gives the width `look` asks for, 320 px.
A1 = {"width": 594, "height": 841}
A1_HEIGHT = round(320 * 841 / 594, 2)


def poster() -> dict[str, Any]:
    """`lab/top` as a page alone printed at A1, which asks for its width alone."""
    return lab_top(preferred={"width": "=@size.figure"}, **{"physical-size": A1})


def test_a_drawing_of_a_page_alone_takes_the_height_its_tops_physical_size_sets() -> None:
    """The drawing writes its own width, and the engine sets the height from it in the
    size's proportion (DEC-034 points 2 and 3); the root holds the top's physical size."""
    drawing = look({"caption": CAPTION}, preferred={"width": "=@space.4 * 10"})
    result = draw(
        {"caption": "A caption."},
        components={"lab/top": poster(), "brand/look": drawing},
        choice=CHOICE,
    )
    assert codes(result) == []
    element = result.scene.find("top")
    assert element is not None
    root = element.properties
    assert (root["component"], root["width"], root["height"]) == ("brand/look", 320.0, A1_HEIGHT)
    assert element.sources["height"] == "engine"
    assert result.scene.to_dict()["physical-size"] == A1


def test_a_drawing_of_a_page_alone_that_writes_a_height_beside_a_physical_size_fails() -> None:
    """A height by a formula beside its top's physical size is refused, and not read: the
    size's proportion sets it (DEC-034 point 2, "but for a height a physical size sets")."""
    components = {"lab/top": poster(), "brand/look": look({"caption": CAPTION})}
    component = layout.Context(FakeEnv(components=components), "en").component("brand/look")
    assert component is not None
    assert [(c, w) for c, w, _ in component.issues] == [(layout.DRAWING_SIZE, "preferred.height")]
    result = draw({"caption": "A caption."}, components=components, choice=CHOICE)
    root = result.scene.children[0].properties
    assert (root["component"], root["width"], root["height"]) == ("brand/look", 320.0, A1_HEIGHT)


def test_a_drawing_of_a_page_needs_no_height_where_its_top_has_a_physical_size() -> None:
    """A top with a physical size asks for its pages' height through it, so a drawing of a
    page's form may leave its height unwritten, and its page gets that height (DEC-034
    points 2 and 3)."""
    deck_data = copy.deepcopy(COMPONENTS["foundations/deck"])
    del deck_data["preferred"]["height"]
    deck_data["physical-size"] = A1
    components = {"foundations/deck": deck_data, "brand/look": page_look(None)}
    component = layout.Context(FakeEnv(components=components), "en").component("brand/look")
    assert component is not None and component.issues == []
    result = draw(
        {"slides": [{"id": "opening", "layout": "cover", "title": "The flow"}]},
        use="foundations/deck",
        components=components,
        choice=layout.Choice({("foundations/deck", "cover"): "brand/look"}),
    )
    deck_group = result.scene.children[0].properties
    page = result.scene.find("deck/slides[opening]")
    assert page is not None
    assert page.properties["component"] == "brand/look"
    assert (page.properties["width"], page.properties["height"]) == (
        deck_group["width"],
        round(deck_group["width"] * 841 / 594, 2),
    )


def test_a_drawing_declares_no_physical_size() -> None:
    """Only its top declares the size its pages print at (DEC-034 point 3)."""
    found = issues(look({"caption": CAPTION}, **{"physical-size": A1}))
    assert (layout.PHYSICAL_SIZE, layout.PHYSICAL_SIZE) in found


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
