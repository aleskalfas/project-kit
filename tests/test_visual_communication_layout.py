"""Components as data, and a scene's values computed in reference order (visual-communication
DEC-001 points 4 and 6, DEC-005 points 1 to 3; #2428).

Each rule is drawn twice, once kept and once broken, from components written as mappings
in memory and read through an in-memory `Env` (`tests/visual_engine.py`):

- parts: primitives, a nested `use`, a slot, a `repeat`; `when` for optional parts; a
  missing part with zero size at its place;
- `values`, `preferred`, `exposes`; switches on an option; options of words, of an item,
  of an item's point; list fields, which may also be null;
- the operators `row` and `column`: `gap`, `align-items`, `justify-content`, equal sizes;
  a stretch an item passes on to the part it draws last, and through it, from a stretch
  alone;
- colour families, whose members the foundations map to roles; states and `override`;
  a concept's family, ahead of a list's, a component's and a container's;
- formulas: dimensions checked when a component is read, `:index` and `:count` over the
  items drawn, steps into a list;
- pages: a diagram is a page alone, and part of the page that holds it;
- what is refused: a loop, naming every element in it; two owners of a value; division
  by zero; a component that places itself, except over its items; a page inside a page;
  a component that gets less than it asks for; a component, role, picture, colour
  family member or concept that is not there; an item option no single part repeats over;
- what cannot be drawn: a top that names no component, which lies in the piece; a
  component whose file cannot be read, a finding in that file alone;
- a list a `use` part passes on under another name, two levels deep: each item's
  sources name the keys the content file writes;
- a top whose layouts are its pages' forms, as the foundations' deck: each page drawn by
  its layout's own drawing, or by the component it names, as a page of its own; what
  its shape may not be; format 1's tops read as before;
- a list's component field and arrangement fields (DEC-010 points 1 to 4): what draws
  each item, and the keys and sources an item takes from the field; a row shared by its
  items' weights, and equal shares as equal sizes; a key both an item's component and
  its list declare, read by neither; what a pattern may not declare for its lists;
- fields of runs (DEC-012 points 1 to 3 and 8): a terminal's line in three styles, a
  sentence with one phrase set apart, a run's concept under a state, a field whose only
  run holds no text under a condition, a slot of a page's layout; each mark, switch and
  reading of a field of runs the component may not hold.
"""

from __future__ import annotations

from typing import Any

from tests.visual_engine import (
    RUN_FONTS,
    RUN_ROLES,
    SEMIBOLD,
    VERSIONS,
    FakeEnv,
    block,
    codes,
    draw,
    env,
    frame,
    layout,
    scene,
    top,
)


def box(**geometry: Any) -> dict[str, Any]:
    return {"box": {"fill": "surface"}, "width": "=@space.4", "height": "=@space.4", **geometry}


def label(field: str = "label", **geometry: Any) -> dict[str, Any]:
    return {"text": {"content": field, "style": "type.body", "fill": "text-primary"}, **geometry}


def lab(**components: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {f"lab/{name}": component for name, component in components.items()}


def finding(result: Any, code: str) -> Any:
    found = [f for f in result.findings if f.code == code]
    assert found, f"no finding {code} in {codes(result)}"
    return found[0]


# --- primitives and formulas ---------------------------------------------------------------


def test_a_box_takes_its_frame_from_formulas_over_roles_and_its_size() -> None:
    parts = {"b": box(x="=@space.1", y="=@space.2", width="=:width * 0.5")}

    result = draw(components=lab(top=top(parts)))

    assert result.findings == []
    assert frame(result, "top/b") == (4.0, 8.0, 320.0, 32.0)


def test_a_literal_length_is_refused_when_the_component_is_read() -> None:
    parts = {"b": box(width="=:width - 6")}

    result = draw(components=lab(top=top(parts)))

    refused = finding(result, "formula-dimension")
    assert "`=:width - 6`" in refused.message and "number with no unit" in refused.message
    assert (refused.where, refused.library) == ("parts.b.width", "lab@1.0.0")
    assert frame(result, "top/b")[2] == 0.0


def test_a_formula_that_cannot_be_read_is_refused_naming_it() -> None:
    parts = {"b": box(width="=:width -@space.1")}

    result = draw(components=lab(top=top(parts)))

    assert "a space on each side" in finding(result, "formula-unreadable").message


def test_a_value_is_read_by_its_name() -> None:
    parts = {"b": box(width="=half")}

    kept = draw(components=lab(top=top(parts, values={"half": "=:width / 2"})))
    broken = draw(components=lab(top=top(parts)))

    assert frame(kept, "top/b")[2] == 320.0
    assert "names no value `half`" in finding(broken, "formula-reach").message


def test_a_formula_reads_a_role_the_brand_resolves() -> None:
    result = draw(components=lab(top=top({"b": box(width="=@space.9")})))

    assert finding(result, "unknown-role").where == "@space.9"


def test_dividing_by_zero_is_a_finding_naming_the_formula() -> None:
    parts = {"b": box(width="=:width * @space.1 / (@space.1 - @space.1)")}

    result = draw(components=lab(top=top(parts)))

    divided = finding(result, "division-by-zero")
    assert "`=:width * @space.1 / (@space.1 - @space.1)`" in divided.message
    assert divided.where == "top"


def test_a_line_holds_its_ends_and_its_frame_bounds_them() -> None:
    line = {
        "line": {"stroke": "line"},
        "x1": "=@space.4",
        "y1": "=@space.1",
        "x2": "=@space.1",
        "y2": "=@space.3",
    }

    result = draw(components=lab(top=top({"l": line})))

    element = result.scene.find("top/l")
    assert element is not None
    assert [element.properties[k] for k in ("x1", "y1", "x2", "y2")] == [32.0, 4.0, 4.0, 16.0]
    assert frame(result, "top/l") == (4.0, 4.0, 28.0, 12.0)


# --- optional parts, switches, options -----------------------------------------------------


def stacked() -> dict[str, Any]:
    parts = {
        "head": label("head", y="=@space.1", width="=:width"),
        "body": box(y="=head.bottom + min(head.height, @space.2)"),
    }
    return top(parts, fields={"head": {"type": "string"}})


def test_a_missing_optional_part_has_zero_size_at_its_place() -> None:
    component = stacked()
    component["parts"]["head"]["when"] = "head"

    kept = draw({"head": "A head"}, components=lab(top=component))
    missing = draw({}, components=lab(top=component))

    assert frame(kept, "top/body")[1] == 4.0 + 22.4 + 8.0
    assert missing.scene.find("top/head") is None
    assert frame(missing, "top/body")[1] == 4.0
    assert missing.findings == []


def test_an_option_chooses_by_a_switch_and_its_first_word_is_the_default() -> None:
    parts = {"b": box(width={"by": "size", "small": "=@space.1", "large": "=@space.4"})}
    component = top(parts, options={"size": ["small", "large"]})

    default = draw({}, components=lab(top=component))
    chosen = draw({"size": "large"}, components=lab(top=component))
    wrong = draw({"size": "huge"}, components=lab(top=component))

    assert frame(default, "top/b")[2] == 4.0
    assert frame(chosen, "top/b")[2] == 32.0
    element = chosen.scene.find("top/b")
    assert element is not None and element.sources["width"] == "option:size"
    assert "takes small, large, not `huge`" in finding(wrong, "option-word").message
    assert frame(wrong, "top/b")[2] == 4.0


def test_a_switch_names_every_word_of_its_option() -> None:
    parts = {"b": box(width={"by": "size", "small": "=@space.1"})}

    result = draw(components=lab(top=top(parts, options={"size": ["small", "large"]})))

    assert "not each word of it" in finding(result, "component-shape").message


def test_when_takes_an_option_and_its_words() -> None:
    parts = {"b": box(when={"mark": ["shown"]})}
    component = top(parts, options={"mark": ["hidden", "shown"]})

    assert draw({"mark": "shown"}, components=lab(top=component)).scene.find("top/b") is not None
    assert draw({}, components=lab(top=component)).scene.find("top/b") is None


# --- nesting, exposure and slots -----------------------------------------------------------


def nested(exposes: list[str]) -> dict[str, dict[str, Any]]:
    inner = block(
        {"tag": label("tag", x="=@space.2")}, fields={"tag": {"type": "string"}}, exposes=exposes
    )
    outer = top(
        {
            "inner": {"use": "lab/inner", "fields": {"tag": "name"}, "width": "=:width"},
            "rule": box(x="=inner.tag.right", width="=@space.1"),
        },
        fields={"name": {"type": "string"}},
    )
    return lab(top=outer, inner=inner)


def test_a_formula_reads_a_part_a_placed_component_exposes() -> None:
    result = draw({"name": "Hi"}, components=nested(["tag"]))

    tag = result.scene.find("top/inner/tag")
    assert tag is not None
    assert result.findings == []
    assert tag.sources["text"] == "content:name"
    assert frame(result, "top/rule")[0] == round(8.0 + tag.properties["width"], 2)


def test_a_part_a_placed_component_keeps_private_cannot_be_read() -> None:
    result = draw({"name": "Hi"}, components=nested([]))

    assert "exposes no part or point `tag`" in finding(result, "missing-exposed").message


def test_a_slot_draws_the_component_the_content_places_and_is_optional() -> None:
    component = top({"s": {"slot": "body", "x": "=@space.1"}}, fields={"body": {"type": "object"}})
    components = lab(
        top=component,
        chip=block({"b": box()}, preferred={"width": "=@space.3", "height": "=@space.3"}),
    )

    placed = draw({"body": {"use": "lab/chip"}}, components=components)
    empty = draw({}, components=components)

    assert frame(placed, "top/s") == (4.0, 0.0, 16.0, 16.0)
    assert frame(placed, "top/s/b") == (0.0, 0.0, 32.0, 32.0)
    assert empty.scene.find("top/s") is None and empty.findings == []


def test_a_use_naming_no_component_is_a_finding() -> None:
    result = draw(components=lab(top=top({"p": {"use": "lab/nothing"}})))

    assert finding(result, "unknown-component").where == "top/p"


# --- lists and operators -------------------------------------------------------------------


def chip() -> dict[str, Any]:
    """An item as wide as @space.3 times its place, as tall as @space.3."""
    return block(
        {"b": box(width="=:width", height="=:height")},
        preferred={"width": "=@space.3 * :index", "height": "=@space.3"},
    )


def listed(operator: str, settings: dict[str, Any], **geometry: Any) -> dict[str, dict[str, Any]]:
    parts = {"items": {"repeat": "items", "draw": "lab/chip", operator: settings, **geometry}}
    fields = {"items": {"type": "array", "items": {"type": "object"}}}
    return lab(top=top(parts, fields=fields), chip=chip())


ITEMS = {"items": [{"id": "a"}, {"id": "b"}, {"id": "c"}]}


def item_frames(result: Any) -> list[tuple[float, float, float, float]]:
    return [frame(result, f"top/items[{key}]") for key in ("a", "b", "c")]


def test_a_row_lays_its_items_out_in_their_own_sizes_with_a_gap() -> None:
    result = draw(ITEMS, components=listed("row", {"gap": "=@space.1"}))

    assert item_frames(result) == [
        (0.0, 0.0, 16.0, 16.0),
        (20.0, 0.0, 32.0, 16.0),
        (56.0, 0.0, 48.0, 16.0),
    ]
    assert frame(result, "top/items")[2:] == (104.0, 16.0)


def test_a_row_justifies_its_content_within_the_width_it_is_given() -> None:
    def xs(justify: str) -> list[float]:
        components = listed("row", {"justify-content": justify}, width="=@space.4 * 4")
        return [f[0] for f in item_frames(draw(ITEMS, components=components))]

    # The items take 96 of 128 px.
    assert xs("start") == [0.0, 16.0, 48.0]
    assert xs("center") == [16.0, 32.0, 64.0]
    assert xs("end") == [32.0, 48.0, 80.0]
    assert xs("space-between") == [0.0, 32.0, 80.0]


def test_a_column_aligns_its_items_across_it() -> None:
    def xs(align: str) -> list[tuple[float, float]]:
        components = listed("column", {"align-items": align}, width="=@space.4 * 2")
        return [(f[0], f[2]) for f in item_frames(draw(ITEMS, components=components))]

    assert xs("start") == [(0.0, 16.0), (0.0, 32.0), (0.0, 48.0)]
    assert xs("center") == [(24.0, 16.0), (16.0, 32.0), (8.0, 48.0)]
    assert xs("end") == [(48.0, 16.0), (32.0, 32.0), (16.0, 48.0)]
    assert xs("stretch") == [(0.0, 64.0)] * 3


def test_equal_sizes_share_the_line_and_need_it_given() -> None:
    kept = draw(
        ITEMS,
        components=listed("row", {"sizes": "equal", "gap": "=@space.2"}, width="=@space.4 * 4"),
    )
    unsized = draw(ITEMS, components=listed("row", {"sizes": "equal"}))

    assert [f[0] for f in item_frames(kept)] == [0.0, 45.33, 90.67]
    assert {f[2] for f in item_frames(kept)} == {37.33}
    assert "shares its width equally" in finding(unsized, "no-size").message


def test_a_component_that_gets_less_than_it_asks_for_is_a_finding() -> None:
    narrow = draw(ITEMS, components=listed("row", {"sizes": "equal"}, width="=@space.4 * 2"))
    wide = draw(ITEMS, components=listed("row", {"sizes": "equal"}, width="=@space.4 * 6"))

    short = [f for f in narrow.findings if f.code == "gets-less"]
    # 64 px shared by three: each gets 21.33 px; b asks for 32 and c for 48.
    assert [f.where for f in short] == ["top/items[b]", "top/items[c]"]
    assert "gets 21.33 px of width and asks for 32.0" in short[0].message
    assert wide.findings == []


def test_a_list_given_less_than_its_items_ask_for_is_a_finding() -> None:
    result = draw(ITEMS, components=listed("row", {}, width="=@space.4"))

    assert finding(result, "gets-less").where == "top/items"


def stretching(**parts: Any) -> dict[str, dict[str, Any]]:
    """A row of items, as tall as the tallest, and a slot `body` 128 px tall. A tile is a
    box 16 px square that fills what it gets, and a tall one is 64 px tall. A stack holds a
    tile, then a slot `foot` under it, and is as tall as both; `parts` replace or add to
    its parts."""
    tile = block({"b": box(width="=:width", height="=:height")})
    tile["preferred"] = {"width": "=@space.3", "height": "=@space.3"}
    tall = block({"b": box(width="=:width", height="=:height")})
    tall["preferred"] = {"width": "=@space.3", "height": "=@space.4 * 2"}
    stack = block(
        {
            "head": {"use": "lab/tile", "width": "=:width"},
            "foot": {"slot": "foot", "y": "=head.bottom", "width": "=:width"},
            **parts,
        },
        fields={"foot": {"type": "object"}},
        preferred={"width": "=@space.3", "height": "=foot.bottom"},
    )
    row = top(
        {
            "items": {"repeat": "items", "draw": "lab/tile", "row": {"gap": "=@space.1"}},
            "body": {"slot": "body", "y": "=items.bottom", "height": "=@space.4 * 4"},
        },
        fields={
            "items": {"type": "array", "items": {"type": "object"}},
            "body": {"type": "object"},
        },
        preferred={"width": "=@size.figure", "height": "=body.bottom"},
    )
    return lab(top=row, tile=tile, tall=tall, stack=stack)


def beside_tall(stack: dict[str, Any]) -> dict[str, Any]:
    """Content that lays `stack` in the row beside a tall tile, which makes the row 64 px
    tall."""
    return {"items": [{"id": "a", "use": "lab/stack", **stack}, {"id": "b", "use": "lab/tall"}]}


TILE = {"use": "lab/tile"}


def height_source(result: Any, trace: str) -> str:
    element = result.scene.find(trace)
    assert element is not None, f"no element {trace}"
    return str(element.sources["height"])


def test_an_item_stretched_across_its_row_passes_it_on_to_the_part_it_draws_last() -> None:
    result = draw(beside_tall({"foot": TILE}), components=stretching())
    nested = draw(
        beside_tall({"foot": {"use": "lab/stack", "foot": TILE}}), components=stretching()
    )

    # The stack asks for 32 px and gets 64: its foot takes the other 32, and so ends where
    # the tall tile ends.
    assert result.findings == []
    assert frame(result, "top/items[b]")[3] == 64.0
    assert frame(result, "top/items[a]/head") == (0.0, 0.0, 16.0, 16.0)
    assert frame(result, "top/items[a]/foot") == (0.0, 16.0, 16.0, 48.0)
    assert frame(result, "top/items[a]/foot/b")[3] == 48.0
    assert height_source(result, "top/items[a]/foot") == "engine"
    # A stack in the foot takes the stretch, and passes it on to its own foot in turn.
    assert nested.findings == []
    assert frame(nested, "top/items[a]/foot") == (0.0, 16.0, 16.0, 48.0)
    assert frame(nested, "top/items[a]/foot/foot") == (0.0, 16.0, 16.0, 32.0)


def test_a_stretch_passes_only_to_the_last_part_drawn_and_only_from_a_stretch() -> None:
    def foot(result: Any) -> tuple[float, float, float, float]:
        return frame(result, "top/items[a]/foot")

    followed = draw(beside_tall({"foot": TILE}), components=stretching(mark=box()))
    sized = stretching()
    sized["lab/stack"]["parts"]["foot"]["height"] = "=@space.3"
    given = draw(beside_tall({"foot": TILE}), components=sized)
    empty = draw(beside_tall({}), components=stretching())
    alone = draw({"body": {"use": "lab/stack", "foot": TILE}}, components=stretching())

    # A part drawn after the foot, or the foot's own height, keeps the foot as it asks.
    assert foot(followed) == foot(given) == (0.0, 16.0, 16.0, 16.0)
    assert height_source(followed, "top/items[a]/foot") == "default:lab/tile"
    # With the foot empty, the head is the last part drawn, and takes the stretch.
    assert frame(empty, "top/items[a]/head") == (0.0, 0.0, 16.0, 64.0)
    # A slot that gives a stack more than it asks for stretches nothing within it.
    assert frame(alone, "top/body")[3] == 128.0
    assert frame(alone, "top/body/foot") == (0.0, 16.0, 16.0, 16.0)
    assert [r.findings for r in (followed, given, empty, alone)] == [[], [], [], []]


def test_a_formula_steps_into_a_list_by_first_last_and_id() -> None:
    components = listed("row", {})
    components["lab/top"]["parts"]["mark"] = box(
        x="=items:last.right", y="=items[b].x", width="=items:first.width"
    )

    result = draw(ITEMS, components=components)

    assert frame(result, "top/mark")[:3] == (96.0, 16.0, 16.0)
    components["lab/top"]["parts"]["mark"]["y"] = "=items[z].x"
    assert (
        "draws no item items[z]"
        in finding(draw(ITEMS, components=components), "missing-exposed").message
    )


def test_index_and_count_are_an_items_own() -> None:
    components = listed("row", {})
    components["lab/chip"]["preferred"]["height"] = "=@space.1 * :count"
    outside = lab(top=top({"b": box(width="=@space.1 * :index")}))

    assert {f[3] for f in item_frames(draw(ITEMS, components=components))} == {12.0}
    assert "is no item" in finding(draw(components=outside), "formula-reach").message


def test_index_and_count_count_only_the_items_drawn() -> None:
    components = listed("row", {})
    components["lab/chip"]["preferred"]["height"] = "=@space.1 * :count"
    # Left out: an item that is no mapping, one that repeats an id, one with no component.
    content = {
        "items": [
            {"id": "a"},
            "no mapping",
            {"id": "a"},
            {"id": "b"},
            {"id": "x", "use": "lab/nothing"},
            {"id": "c"},
        ]
    }

    result = draw(content, components=components)

    # Each chip is @space.3 (16) wide times its place, and @space.1 (4) tall times the count.
    assert item_frames(result) == [
        (0.0, 0.0, 16.0, 12.0),
        (16.0, 0.0, 32.0, 12.0),
        (48.0, 0.0, 48.0, 12.0),
    ]


def test_a_field_that_may_also_be_null_is_a_list_field() -> None:
    components = listed("row", {})
    components["lab/top"]["fields"]["properties"]["items"]["type"] = ["array", "null"]

    result = draw(ITEMS, components=components)

    assert result.findings == []
    assert item_frames(result)[2] == (48.0, 0.0, 48.0, 16.0)


def test_an_item_option_names_an_item_of_the_list_its_component_declares() -> None:
    components = listed("row", {})
    components["lab/top"]["options"] = {"pick": {"item": "items"}}
    components["lab/top"]["parts"]["mark"] = box(x="={pick}.x")

    picked = draw({**ITEMS, "pick": {"item": "c"}}, components=components)
    unknown = draw({**ITEMS, "pick": {"item": "z"}}, components=components)
    missing = draw(ITEMS, components=components)

    assert frame(picked, "top/mark")[0] == 48.0
    assert "`pick` names `z`" in finding(unknown, "unknown-item").message
    assert "needs the option `pick`" in finding(missing, "option-missing").message


def test_a_formula_reading_an_item_option_needs_exactly_one_part_repeating_over_its_list() -> None:
    """Refused when the component is read, never a crash when the scene is computed. The
    part may come before the list it reads."""
    fields = {"items": {"type": "array", "items": {"type": "object"}}}
    options = {"pick": {"item": "items"}}
    mark = box(x="={pick}.x")
    items = {"repeat": "items", "draw": "lab/chip", "row": {}}
    content = {**ITEMS, "pick": {"item": "c"}}

    def drawn(parts: dict[str, Any]) -> Any:
        component = top(parts, fields=fields, options=options)
        return draw(content, components=lab(top=component, chip=chip()))

    assert frame(drawn({"mark": mark, "items": items}), "top/mark")[0] == 48.0
    for broken in (drawn({"mark": mark}), drawn({"mark": mark, "items": items, "too": items})):
        assert "not exactly one part repeats" in finding(broken, "component-shape").message
        refused = finding(broken, "formula-reach")
        assert refused.where == "parts.mark.x" and "reads `{pick}`" in refused.message
        assert frame(broken, "top/mark")[0] == 0.0


def test_a_point_option_names_a_point_the_item_exposes() -> None:
    content = {
        "body": {
            "use": "tests/callout",
            "pictures": [{"id": "p", "output": "square"}],
            "label": "Here",
            "at": {"item": "p", "point": "nose"},
        }
    }

    result = draw(content, use="foundations/figure")

    assert "exposes no part or point `nose`" in finding(result, "missing-exposed").message


def test_items_are_mappings_with_ids_of_their_own() -> None:
    result = draw({"items": [{"id": "a"}, {"id": "a"}, "c"]}, components=listed("row", {}))

    assert [f.where for f in result.findings if f.code == "content-shape"] == [
        "top/items[a]",
        "top/items#3",
    ]
    assert result.scene.find("top/items[a]") is not None


def test_a_text_is_drawn_from_a_field_holding_text() -> None:
    component = top({"t": label(width="=:width")}, fields={"label": {"type": "string"}})

    numbered = draw({"label": 42}, components=lab(top=component))
    listed_ = draw({"label": ["no"]}, components=lab(top=component))

    assert numbered.findings == []
    element = numbered.scene.find("top/t")
    assert element is not None and element.properties["text"] == "42"
    assert "holds no text" in finding(listed_, "content-shape").message


def test_a_slot_takes_a_component_to_draw() -> None:
    component = top({"s": {"slot": "body"}}, fields={"body": {"type": "object"}})

    result = draw({"body": {"head": "no use"}}, components=lab(top=component))

    assert "takes a component" in finding(result, "content-shape").message
    assert result.scene.find("top/s") is None


def test_a_text_style_names_a_typography_role() -> None:
    component = top({"t": label(width="=:width")}, fields={"label": {"type": "string"}})

    result = draw(
        {"label": "x"}, components=lab(top=component), roles={"type.body": {"fontSize": 16}}
    )

    refused = finding(result, "role-type")
    assert (refused.where, refused.message) == (
        "top/t",
        "top/t: the role @type.body names no font family",
    )
    assert result.scene.find("top/t") is None


def test_the_variants_of_a_picture_share_its_pixels_and_points() -> None:
    moved = env.PictureInfo(
        variants={
            key: {"file": f"{key}.png", "pixels": {"width": 100, "height": 100}}
            for key in ("a", "b")
        },
        points={"tip": {"a": {"x": 1, "y": 1}, "b": {"x": 2, "y": 1}}},
    )
    content = {"body": {"use": "tests/picture", "output": "square"}}

    kept = draw(content, use="foundations/figure")
    differ = draw(content, use="foundations/figure", pictures={"square": moved})

    assert kept.findings == []
    assert "differ in pixels or points" in finding(differ, "picture-variants").message


def test_a_scene_reads_the_first_variant_in_key_order_the_default_first() -> None:
    picture = env.PictureInfo(
        variants={
            key: {"file": f"{key}.png", "pixels": {"width": 100, "height": 100}}
            for key in ("colour-scheme.dark", "default", "colour-scheme.dark+contrast.high")
        },
        points={},
    )

    assert layout.first_variant(picture) == "default"


def test_the_piece_is_drawn_from_a_top_component() -> None:
    nothing = draw(use="lab/nothing")
    block_ = draw(use="tests/card")

    assert finding(nothing, "unknown-component").where == "top"
    assert "declares no layouts" in finding(block_, "not-top").message


def test_a_picture_the_piece_lacks_is_a_finding() -> None:
    content = {
        "body": {
            "use": "tests/callout",
            "pictures": [{"id": "p", "output": "gone"}],
            "label": "x",
            "at": {"item": "p", "point": "tip"},
        }
    }

    result = draw(content, use="foundations/figure")

    assert "no produced output `gone`" in finding(result, "missing-picture").message


# --- one owner, reference order, loops ------------------------------------------------------


def test_a_parents_width_and_a_childs_measured_height_form_no_loop() -> None:
    card = block(
        {"t": label(width="=:width")},
        fields={"label": {"type": "string"}},
        preferred={"height": "=t.bottom"},
    )
    component = top(
        {"c": {"use": "lab/card", "fields": {"label": "label"}, "width": "=:width / 4"}},
        fields={"label": {"type": "string"}},
    )

    result = draw(
        {"label": "words enough to wrap onto lines"}, components=lab(top=component, card=card)
    )

    assert result.findings == []
    assert frame(result, "top/c")[2] == 160.0
    assert frame(result, "top/c")[3] == frame(result, "top/c/t")[3] > 22.4


def test_a_loop_of_references_is_refused_naming_every_element_in_it() -> None:
    parts = {"a": box(width="=b.width"), "b": box(width="=c.height"), "c": box(height="=a.width")}

    result = draw(components=lab(top=top(parts)))

    loop = finding(result, "loop")
    assert "top/a.width → top/b.width → top/c.height → top/a.width" in loop.message
    assert frame(result, "top/a")[2] == 0.0


def test_a_loop_through_values_is_refused_too() -> None:
    result = draw(
        components=lab(top=top({"b": box(width="=one")}, values={"one": "=two", "two": "=one"}))
    )

    assert "top value one → top value two → top value one" in finding(result, "loop").message


def test_a_text_whose_height_the_part_also_gives_has_two_owners() -> None:
    parts = {"t": label(width="=:width", height="=@space.1")}

    result = draw(
        {"label": "One line"}, components=lab(top=top(parts, fields={"label": {"type": "string"}}))
    )

    refused = finding(result, "two-owners")
    assert refused.where == "parts.t.height"
    assert frame(result, "top/t")[3] == 22.4  # the measured text keeps it


# --- what is refused: places itself, pages --------------------------------------------------


def test_a_component_that_places_itself_is_refused() -> None:
    again = block({"me": {"use": "lab/again"}})
    through = block({"other": {"use": "lab/back"}})
    back = block({"me": {"use": "lab/through"}})

    direct = draw(components=lab(top=top({"p": {"use": "lab/again"}}), again=again))
    indirect = draw(
        components=lab(top=top({"p": {"use": "lab/through"}}), through=through, back=back)
    )

    assert "lab/again places itself" in finding(direct, "places-itself").message
    assert "lab/through → lab/back → lab/through" in finding(indirect, "places-itself").message


def test_a_component_may_place_itself_over_the_items_of_its_content() -> None:
    tree = block(
        {"kids": {"repeat": "kids", "draw": "lab/tree", "column": {}}},
        fields={"kids": {"type": "array", "items": {"type": "object"}}},
        preferred={"width": "=@space.3", "height": "=kids.height"},
    )
    component = top({"t": {"slot": "root"}}, fields={"root": {"type": "object"}})
    content = {
        "root": {"use": "lab/tree", "kids": [{"id": "a", "kids": [{"id": "b", "kids": []}]}]}
    }

    result = draw(content, components=lab(top=component, tree=tree))

    assert result.findings == []
    assert result.scene.find("top/t/kids[a]/kids[b]") is not None


def test_a_diagram_is_a_page_alone_and_part_of_the_page_that_holds_it() -> None:
    """A top component with no slot of pages (DEC-005 point 5)."""
    diagram = top({"b": box()}, preferred={"width": "=@space.4", "height": "=@space.4"})
    slide = top({"s": {"slot": "body"}}, fields={"body": {"type": "object"}})
    deck = top(
        {"slides": {"repeat": "slides", "draw": "lab/slide", "width": "=:width", "column": {}}},
        fields={"slides": {"type": "array", "items": {"type": "object"}}},
        layouts={"slide": {"slots": {"slides": {"pages": True}}}},
    )
    components = lab(diagram=diagram, slide=slide, deck=deck)
    placed = {"use": "lab/diagram"}

    alone = draw(components=components, use="lab/diagram")
    in_a_figure = draw({"body": placed}, components=components, use="foundations/figure")
    on_a_slide = draw(
        {"slides": [{"id": "one", "body": placed}]}, components=components, use="lab/deck"
    )

    assert alone.scene.pages == ["diagram"]
    assert in_a_figure.scene.pages == ["figure"] and in_a_figure.findings == []
    assert on_a_slide.scene.pages == ["deck/slides[one]"] and on_a_slide.findings == []
    body = in_a_figure.scene.find("figure/body")
    assert body is not None and "page" not in body.properties


def test_the_items_of_a_slot_of_pages_are_pages() -> None:
    deck = top(
        {"slides": {"repeat": "slides", "draw": "tests/card", "width": "=:width", "column": {}}},
        fields={"slides": {"type": "array", "items": {"type": "object"}}},
        layouts={"slide": {"slots": {"slides": {"pages": True}}}},
    )
    content = {"slides": [{"id": "one", "head": "One"}, {"id": "two", "head": "Two"}]}

    alone = draw(content, components=lab(deck=deck), use="lab/deck")
    inside = draw(
        {"body": {"use": "lab/deck", **content}},
        components=lab(deck=deck),
        use="foundations/figure",
    )

    assert alone.scene.pages == ["deck/slides[one]", "deck/slides[two]"] and alone.findings == []
    # A slot of pages inside a page holds pages inside a page.
    assert [f.where for f in inside.findings if f.code == "page-in-page"] == [
        "figure/body/slides[one]",
        "figure/body/slides[two]",
    ]


# --- colour --------------------------------------------------------------------------------


def coloured(**keys: Any) -> dict[str, dict[str, Any]]:
    swatch = block(
        {
            "b": {
                "box": {"fill": ":colour.fill", "stroke": "line"},
                "width": "=@space.1",
                "height": "=@space.1",
            }
        },
        states={"marked": {"colour": "red"}, "quiet": {}},
        **keys,
    )
    return lab(top=top({"s": {"slot": "body"}}, fields={"body": {"type": "object"}}), swatch=swatch)


#: The colour families the foundations declare in these tests: each member to a colour role.
FAMILIES = {"blue": {"fill": "surface"}, "red": {"fill": "accent"}}


def fill(result: Any) -> tuple[str, str]:
    element = result.scene.find("top/s/b")
    assert element is not None
    return element.properties.get("fill"), element.sources.get("fill")


def swatch(body: dict[str, Any], *, families: Any = FAMILIES, **keys: Any) -> Any:
    """The scene of a swatch the content places, with `keys` added to its component."""
    return draw({"body": body}, components=coloured(**keys), families=families)


def test_a_part_paints_with_the_role_its_family_maps_the_member_to() -> None:
    assert fill(swatch({"use": "lab/swatch"}, colour="blue")) == ("surface", "default:lab/swatch")
    assert fill(swatch({"use": "lab/swatch", "state": "quiet"}, colour="blue"))[0] == "surface"
    marked = swatch({"use": "lab/swatch", "state": "marked"}, colour="blue")
    assert fill(marked) == ("accent", "content:body.state")
    unknown = swatch({"use": "lab/swatch", "state": "loud"}, colour="blue")
    assert "declares no state `loud`" in finding(unknown, "unknown-state").message


def test_a_member_with_no_family_or_one_its_family_lacks_paints_nothing() -> None:
    nameless = swatch({"use": "lab/swatch"})
    lacking = swatch({"use": "lab/swatch"}, colour="blue", families={"blue": {"edge": "line"}})
    undeclared = swatch({"use": "lab/swatch"}, colour="green")

    assert finding(nameless, "no-colour").where == "top/s/b"
    assert "the colour family `blue` has no member `fill`" in finding(lacking, "no-colour").message
    assert "`green`, which the foundations do not declare" in (
        finding(undeclared, "no-colour").message
    )
    for result in (nameless, lacking, undeclared):
        assert fill(result) == (None, None)


def test_override_points_a_part_at_another_role_never_a_value() -> None:
    pointed = swatch({"use": "lab/swatch", "override": {"b": "accent"}}, colour="blue")
    raw = swatch({"use": "lab/swatch", "override": {"b": "#ff0000"}}, colour="blue")
    nowhere = swatch({"use": "lab/swatch", "override": {"z": "accent"}}, colour="blue")

    assert fill(pointed) == ("accent", "content:body.override.b")
    assert "not a role" in finding(raw, "override").message
    assert fill(raw)[0] == "surface"
    assert "no painted part" in finding(nowhere, "override").message


# --- what a top or a part names that cannot be drawn ----------------------------------------


def test_a_top_that_names_no_component_lies_in_the_piece_at_top() -> None:
    nothing = finding(draw(use="lab/nothing"), "unknown-component")

    assert nothing.message == "the piece's top names no component `lab/nothing`"
    assert (nothing.where, nothing.library, nothing.extra) == ("top", "", {"piece": True})


class _Unreadable(FakeEnv):
    """An `Env` in memory in which the file of `lab/broken` is present and cannot be read."""

    def component(self, use: str) -> dict:
        if use == "lab/broken":
            raise env.UnreadableComponent(use, "does not parse as YAML")
        return super().component(use)


def test_a_component_whose_file_cannot_be_read_is_a_finding_in_that_file_alone() -> None:
    def drawn(use: str, **components: dict[str, Any]) -> Any:
        return scene.compute_scene(
            piece="test-piece", top=use, content={}, language="en", lock=dict(VERSIONS),
            size_key="default", seam_version=4, env=_Unreadable(components=lab(**components)),
            facts=layout.stand_ins("draft"),
        )  # fmt: skip

    placed = drawn("lab/top", top=top({"p": {"use": "lab/broken"}}))
    on_top = drawn("lab/broken")

    for result in (placed, on_top):
        unreadable = finding(result, "component-unreadable")
        assert unreadable.message == (
            "the component `lab/broken` cannot be read: does not parse as YAML"
        )
        assert (unreadable.where, unreadable.library) == ("", "lab@1.0.0")
        assert unreadable.extra == {"component": "lab/broken"}
        assert "unknown-component" not in codes(result)
    assert placed.scene.find("top/p") is None


# --- concepts ------------------------------------------------------------------------------

#: The concepts the piece's notations hold in these tests: each to its colour family, or to
#: None where its notation cannot read it.
CONCEPTS = {"sys/store": "red", "sys/user": "blue", "sys/lost": None}


def swatches(*items: dict[str, Any], **environment: Any) -> Any:
    """The scene of swatches a `repeat` part of colour `blue` draws over `items`."""
    parts = {"items": {"repeat": "items", "draw": "lab/swatch", "colour": "blue", "row": {}}}
    fields = {"items": {"type": "array", "items": {"type": "object"}}}
    components = {**coloured(), **lab(top=top(parts, fields=fields))}
    environment = {"families": FAMILIES, "concepts": CONCEPTS, **environment}
    return draw({"items": list(items)}, components=components, **environment)


def painted(result: Any, item: str) -> tuple[str, str]:
    element = result.scene.find(f"top/items[{item}]/b")
    assert element is not None
    return element.properties.get("fill"), element.sources.get("fill")


def test_an_item_takes_its_concept_s_family_else_its_place_s_and_a_state_changes_either() -> None:
    result = swatches(
        {"id": "plain"},
        {"id": "store", "concept": "sys/store"},
        {"id": "marked", "state": "marked"},
        {"id": "user", "concept": "sys/user", "state": "marked"},
        {"id": "quiet", "concept": "sys/store", "state": "quiet"},
    )

    assert result.findings == []
    assert painted(result, "plain") == ("surface", "default:lab/top")
    assert painted(result, "store") == ("accent", "content:items[store].concept")
    assert painted(result, "marked") == ("accent", "content:items[marked].state")
    assert painted(result, "user") == ("accent", "content:items[user].state")
    assert painted(result, "quiet") == ("accent", "content:items[quiet].concept")


def test_a_concept_comes_before_the_component_s_family_and_its_container_s() -> None:
    environment = {"families": FAMILIES, "concepts": CONCEPTS}
    slot = top({"s": {"slot": "body"}}, fields={"body": {"type": "object"}}, colour="blue")
    container = {**coloured(), **lab(top=slot)}
    named = {"body": {"use": "lab/swatch", "concept": "sys/store"}}

    own = draw(named, components=coloured(colour="blue"), **environment)
    contained = draw(named, components=container, **environment)
    inherited = draw({"body": {"use": "lab/swatch"}}, components=container, **environment)

    assert fill(inherited)[0] == "surface"
    for result in (own, contained):
        assert result.findings == []
        assert fill(result) == ("accent", "content:body.concept")


def test_a_concept_the_notations_do_not_hold_is_a_finding_and_the_family_falls_back() -> None:
    unnamed = swatches({"id": "a", "concept": "other/store"})
    absent = swatches({"id": "a", "concept": "sys/queue"})
    malformed = swatches({"id": "a", "concept": "store"})

    assert finding(unnamed, "unknown-concept").message == (
        "top/items[a]: the piece names no notation `other`"
    )
    assert finding(absent, "unknown-concept").message == (
        "top/items[a]: the notation `sys` holds no concept `queue`"
    )
    assert finding(malformed, "unknown-concept").message == (
        "top/items[a]: `concept` takes `<notation>/<concept>`, not `store`"
    )
    for result in (unnamed, absent, malformed):
        refused = finding(result, "unknown-concept")
        assert (refused.where, refused.library) == ("top/items[a]", "")
        assert painted(result, "a") == ("surface", "default:lab/top")


def test_a_concept_its_notation_cannot_read_takes_the_family_it_would_have_had() -> None:
    result = swatches({"id": "a", "concept": "sys/lost"})

    assert result.findings == []
    assert painted(result, "a") == ("surface", "default:lab/top")


# --- a list a part passes on under another name -------------------------------------------

LISTED = {"type": "array", "items": {"type": "object"}}


def pattern(name: str, draw: str) -> dict[str, Any]:
    """A component that draws each item of its list `name` with `draw`, in a column."""
    return block({name: {"repeat": name, "draw": draw, "column": {}}}, fields={name: LISTED})


def passing(theirs: str, ours: str, use: str) -> dict[str, Any]:
    """The part `p`, which passes the list `ours` on to `use` as `theirs`."""
    return {"p": {"use": use, "fields": {theirs: ours}}}


def renaming() -> dict[str, dict[str, Any]]:
    """A top that passes its list `steps` on to a frame as `lines`, which passes it on to
    a pattern of groups as `rows`. Each group passes its own list `subs` on to a pattern
    of swatches as `items`."""
    return {
        **coloured(),
        **lab(
            top=top(passing("lines", "steps", "lab/frame"), fields={"steps": LISTED}),
            frame=block(passing("rows", "lines", "lab/groups"), fields={"lines": LISTED}),
            groups=pattern("rows", "lab/group"),
            group=block(passing("items", "subs", "lab/swatches"), fields={"subs": LISTED}),
            swatches=pattern("items", "lab/swatch"),
        ),
    }


def test_an_item_of_a_list_passed_on_under_another_name_is_named_by_the_content_s_keys() -> None:
    content = {
        "steps": [
            {"id": "a", "subs": [{"id": "x", "concept": "sys/store"}, {"state": "marked"}]},
            {"subs": [{"override": {"b": "line"}}]},
        ]
    }

    result = draw(content, components=renaming(), families=FAMILIES, concepts=CONCEPTS)

    fills = {}
    for trace in ("rows[a]/p/items[x]", "rows[a]/p/items#2", "rows#2/p/items#1"):
        element = result.scene.find(f"top/p/p/{trace}/b")
        assert element is not None, trace
        fills[trace] = (element.properties.get("fill"), element.sources.get("fill"))
    assert fills == {
        "rows[a]/p/items[x]": ("accent", "content:steps[a].subs[x].concept"),
        "rows[a]/p/items#2": ("accent", "content:steps[a].subs#2.state"),
        "rows#2/p/items#1": ("line", "content:steps#2.subs#1.override.b"),
    }


def test_a_fact_takes_no_run_styles() -> None:
    fields = {"say": {"type": "string", "x-pkit-runs": ["plain", "strong"]}}
    style = {"by": "say", "plain": "type.body", "strong": "type.heading"}
    parts = {"t": {"text": {"fact": "state", "style": style}}}
    result = draw(components=lab(top=top(parts, fields=fields)))
    message = finding(result, "component-shape").message
    assert "chooses by the run styles of `say`" in message


def test_a_context_that_computes_no_scene_takes_the_stand_ins_and_no_state() -> None:
    placing = layout.Context(FakeEnv(), "en")
    assert [placing.fact(word) for word in layout.FACTS] == ["v88", "2088-08-28", "en", ""]


# --- a top whose layouts are its pages' forms (#2558) ------------------------------------------

#: A deck of the foundations: a cover, a slide with a picture, and a page the figure draws.
DECK = {
    "slides": [
        {
            "id": "cover",
            "layout": "cover",
            "title": "Building with AI",
            "subtitle": "The way the project decided",
            "author": "A. K.",
            "link": "example.org",
        },
        {
            "id": "rules",
            "layout": "slide",
            "title": "Where permissions come from",
            "lead": "From the rules the project keeps.",
            "visual": {"use": "tests/steps", "steps": [{"id": "a", "head": "Ask"}]},
            "limit": "A deny stops only what it can tell.",
            "footer": "In project-kit.",
        },
        {"layout": "slide", "title": "How it fits"},
    ]
}


def test_each_page_is_drawn_by_its_layouts_own_drawing_as_a_page_of_its_own() -> None:
    result = draw(DECK, use="foundations/deck")

    assert result.findings == []
    assert result.scene.pages == ["deck/slides[cover]", "deck/slides[rules]", "deck/slides#3"]
    # Each page lies at the top's origin, as large as the top: a slide's width, 16 by 9.
    for page in ("deck", *result.scene.pages):
        assert frame(result, page) == (0.0, 0.0, 1280.0, 720.0), page
    # Each part that places a slot is named after it, so a slot keeps its trace id.
    for slot in ("title", "subtitle", "author", "link"):
        assert result.scene.find(f"deck/slides[cover]/{slot}") is not None, slot
    for slot in ("title", "lead", "visual", "limit", "footer"):
        assert result.scene.find(f"deck/slides[rules]/{slot}") is not None, slot
    assert result.scene.find("deck/slides[rules]/visual/steps[a]") is not None
    # The slide leaves out what its page does not fill.
    assert result.scene.find("deck/slides#3/lead") is None


def test_a_pages_trace_id_and_its_contents_source_name_its_place_in_the_list() -> None:
    result = draw(DECK, use="foundations/deck")

    title = result.scene.find("deck/slides[rules]/title")
    untitled = result.scene.find("deck/slides#3/title")
    assert title is not None and untitled is not None
    assert title.sources["text"] == "content:slides[rules].title"
    assert untitled.sources["text"] == "content:slides#3.title"
    assert title.sources["x"] == "default:foundations/deck"


def test_a_page_that_names_its_component_is_drawn_by_it_as_a_page() -> None:
    content = {
        "slides": [
            DECK["slides"][0],
            {"id": "flow", "use": "foundations/figure", "body": {"use": "tests/steps"}},
        ]
    }

    result = draw(content, use="foundations/deck")

    assert result.findings == []
    assert result.scene.pages == ["deck/slides[cover]", "deck/slides[flow]"]
    flow = result.scene.find("deck/slides[flow]")
    assert flow is not None and flow.properties["component"] == "foundations/figure"
    assert frame(result, "deck/slides[flow]") == (0.0, 0.0, 1280.0, 720.0)


def test_a_page_that_names_no_layout_of_its_top_is_left_out_for_the_content_check() -> None:
    content = {"slides": [{"id": "a", "title": "A"}, {"id": "b", "layout": "cvoer"}]}

    result = draw(content, use="foundations/deck")

    assert result.scene.pages == []
    assert result.findings == []


def forms_top(**keys: Any) -> dict[str, Any]:
    """A top whose layouts are its pages' forms: `pages` holds its pages, and its layout
    `one` draws a page's `head` in the colour its option `tone` names. `keys` add to it
    or replace its defaults."""
    return {
        "status": "experimental",
        "about": "A top whose layouts are its pages' forms.",
        "fields": {
            "type": "object",
            "properties": keys.pop(
                "fields",
                {"pages": {"type": "array", "items": {"type": "object"}, "x-pkit-pages": True}},
            ),
        },
        "options": {"tone": ["plain", "loud"]},
        "layouts": keys.pop(
            "layouts",
            {
                "one": {
                    "slots": {"head": {"type": "string"}},
                    "required": ["head"],
                    "parts": {
                        "head": {
                            "text": {
                                "content": "head",
                                "style": "type.body",
                                "fill": {"by": "tone", "plain": "text-primary", "loud": "accent"},
                            },
                            "width": "=:width",
                        }
                    },
                }
            },
        ),
        "preferred": {"width": "=@size.figure", "height": "=@space.4"},
        **keys,
    }


def test_a_pages_drawing_takes_the_tops_options_and_its_other_fields() -> None:
    fields = {
        "pages": {"type": "array", "items": {"type": "object"}, "x-pkit-pages": True},
        "note": {"type": "string"},
    }
    layouts = forms_top()["layouts"]
    layouts["one"]["parts"]["note"] = label("note", y="=head.bottom", width="=:width")
    component = forms_top(fields=fields, layouts=layouts)
    content = {
        "tone": "loud",
        "note": "Said once.",
        "pages": [{"id": "a", "layout": "one", "head": "A"}],
    }

    result = draw(content, components=lab(top=component))

    assert result.findings == []
    head = result.scene.find("top/pages[a]/head")
    note = result.scene.find("top/pages[a]/note")
    assert head is not None and note is not None
    run = head.properties["paragraphs"][0][0]
    assert (run["fill"], run["sources"]["fill"]) == ("accent", "option:tone")
    assert result.scene.find("top/pages[a]").sources["options.tone"] == "content:tone"
    assert (note.properties["text"], note.sources["text"]) == ("Said once.", "content:note")


def issues(data: dict[str, Any]) -> list[tuple[str, str]]:
    """What the engine finds in a component's shape, by code and key path."""
    component = layout.Component("lab/x", data, layout.Context(FakeEnv(), "en"))
    return [(code, where) for code, where, _ in component.issues]


SHAPE = "component-shape"
PAGES_FIELD = {"type": "array", "items": {"type": "object"}, "x-pkit-pages": True}


def test_a_top_whose_layouts_are_its_pages_forms_reads_with_no_issue() -> None:
    assert issues(forms_top()) == []


def with_layout(**changes: Any) -> dict[str, dict[str, Any]]:
    """The layouts of `forms_top`, the layout `one` changed by `changes`, a key whose
    value is `...` removed."""
    one = {**forms_top()["layouts"]["one"], **changes}
    return {"one": {key: value for key, value in one.items() if value is not ...}}


def test_a_top_that_marks_no_field_as_holding_its_pages_or_two_is_refused() -> None:
    none = forms_top(fields={"pages": {"type": "array", "items": {"type": "object"}}})
    two = forms_top(fields={"pages": PAGES_FIELD, "more": PAGES_FIELD})
    text = forms_top(fields={"pages": {"type": "string", "x-pkit-pages": True}})

    assert issues(none) == [(SHAPE, "fields")]
    assert issues(two) == [(SHAPE, "fields")]
    assert issues(text) == [(SHAPE, "fields.properties.pages")]
    assert (
        "it marks none"
        in layout.Component("lab/x", none, layout.Context(FakeEnv(), "en")).issues[0][2]
    )


def test_a_slot_named_layout_or_a_reserved_key_or_holding_pages_is_refused() -> None:
    def slot(name: str, schema: dict[str, Any]) -> dict[str, Any]:
        return forms_top(layouts=with_layout(slots={"head": {"type": "string"}, name: schema}))

    assert issues(slot("layout", {"type": "string"})) == [(SHAPE, "layouts.one.slots.layout")]
    assert issues(slot("state", {"type": "string"})) == [(SHAPE, "layouts.one.slots.state")]
    assert issues(slot("inner", PAGES_FIELD)) == [(SHAPE, "layouts.one.slots.inner")]


def test_each_layout_has_its_own_drawing_and_the_top_draws_nothing_around_its_pages() -> None:
    layouts = {**forms_top()["layouts"], "two": {"slots": {"head": {"type": "string"}}}}

    assert issues(forms_top(layouts=layouts)) == [(SHAPE, "layouts.two")]
    assert issues(forms_top(parts={"b": box()})) == [(SHAPE, "parts")]
    assert issues(forms_top(layouts=with_layout(required=["body"]))) == [
        (SHAPE, "layouts.one.required")
    ]


def test_a_slot_that_is_also_a_field_of_the_top_is_refused() -> None:
    fields = {"pages": PAGES_FIELD, "head": {"type": "string"}}

    assert issues(forms_top(fields=fields)) == [(SHAPE, "layouts.one.slots.head")]


def test_a_layouts_drawing_is_read_as_the_tops_and_its_issues_lie_under_the_layout() -> None:
    layouts = with_layout(parts={"head": label("headline", width="=:width")})

    assert issues(forms_top(layouts=layouts)) == [(SHAPE, "layouts.one.parts.head.text.content")]


def test_a_component_that_marks_a_field_of_pages_and_declares_no_layouts_is_refused() -> None:
    data = block({"b": box()}, fields={"pages": PAGES_FIELD})

    assert issues(data) == [(SHAPE, "fields")]


def test_format_1s_tops_read_as_before_and_one_may_declare_a_field_named_layout() -> None:
    """A top with one layout has no layout a page names, so `layout` stays a field it may
    declare."""
    figure = top({"l": label("layout", width="=:width")}, fields={"layout": {"type": "string"}})

    result = draw({"layout": "Wide"}, components=lab(top=figure))

    assert result.findings == []
    assert result.scene.pages == ["top"]
    shown = result.scene.find("top/l")
    assert shown is not None and shown.properties["text"] == "Wide"


# --- a list's component field and arrangement fields (#2560) ---------------------------------

#: A weight of three words, whose shares are one, two and four.
SIZE = {"words": ["one", "two", "four"], "shares": {"one": 1, "two": 2, "four": 4}}


def toned() -> dict[str, Any]:
    """A block whose box paints in the colour its option `tone` names, as large as `chip`."""
    fill = {"by": "tone", "plain": "surface", "loud": "accent"}
    return block(
        {"b": {"box": {"fill": fill}, "width": "=:width", "height": "=:height"}},
        options={"tone": ["plain", "loud"]},
        preferred={"width": "=@space.3 * :index", "height": "=@space.3"},
    )


def chosen(**lists: Any) -> dict[str, dict[str, Any]]:
    """The top of `listed`, whose field `kind` is the component field of its list `items`
    and whose `lists` adds `lists`; its items drawn by `lab/chip` by default."""
    components = listed("row", {"gap": "=@space.2"})
    parts, fields = components["lab/top"]["parts"], {"items": LISTED, "kind": {"type": "object"}}
    declared = {"items": {"component": "kind"}, **lists}
    components["lab/top"] = top(parts, fields=fields, lists=declared)
    return {**components, **lab(toned=toned())}


def test_a_lists_component_field_draws_each_item_that_names_none_of_its_own() -> None:
    content = {
        "kind": {"use": "lab/toned", "tone": "loud"},
        "items": [{"id": "a"}, {"id": "b", "tone": "plain"}, {"id": "c", "use": "lab/chip"}],
    }

    result = draw(content, components=chosen())

    assert result.findings == []
    drawn = {key: result.scene.find(f"top/items[{key}]") for key in ("a", "b", "c")}
    assert {key: e.properties["component"] for key, e in drawn.items() if e is not None} == {
        "a": "lab/toned",
        "b": "lab/toned",
        "c": "lab/chip",
    }
    # The item's choice first: `b` gives its own `tone`, and `c` takes nothing from the field.
    assert drawn["a"] is not None and drawn["b"] is not None and drawn["c"] is not None
    assert drawn["a"].sources["options.tone"] == "content:kind.tone"
    assert drawn["b"].sources["options.tone"] == "content:items[b].tone"
    assert "options.tone" not in drawn["c"].sources
    fills = [result.scene.find(f"top/items[{key}]/b") for key in ("a", "b")]
    assert [e.properties["fill"] for e in fills if e is not None] == ["accent", "surface"]
    # The field places nothing.
    assert result.scene.find("top/kind") is None


def test_a_list_whose_component_field_is_empty_draws_its_items_by_its_default() -> None:
    result = draw(ITEMS, components=chosen())

    assert result.findings == []
    shown = result.scene.find("top/items[a]")
    assert shown is not None and shown.properties["component"] == "lab/chip"


def test_a_component_field_naming_no_component_draws_no_item_that_names_none() -> None:
    content = {
        "kind": {"use": "lab/nothing"},
        "items": [{"id": "a"}, {"id": "b", "use": "lab/chip"}],
    }

    result = draw(content, components=chosen())

    assert finding(result, "unknown-component").where == "top/items"
    assert result.scene.find("top/items[a]") is None
    assert result.scene.find("top/items[b]") is not None


def weighted(sizes: Any = "shares", **geometry: Any) -> dict[str, dict[str, Any]]:
    """`listed`'s row, its gap @space.2, which shares its length by `sizes`; its list's
    weight `size` is `SIZE`."""
    components = listed("row", {"sizes": sizes, "gap": "=@space.2"}, **geometry)
    components["lab/top"]["lists"] = {"items": {"arrangement": {"size": SIZE}}}
    return components


def test_a_row_shares_its_width_by_its_items_weights_less_the_gaps() -> None:
    content = {"items": [{"id": "a"}, {"id": "b", "size": "two"}, {"id": "c", "size": "four"}]}

    result = draw(content, components=weighted(width="=@space.4 * 4"))

    # 128 px less two gaps of 8 px, shared one to two to four.
    assert result.findings == []
    assert item_frames(result) == [
        (0.0, 0.0, 16.0, 16.0),
        (24.0, 0.0, 32.0, 16.0),
        (64.0, 0.0, 64.0, 16.0),
    ]


def test_items_of_equal_shares_are_drawn_as_equal_sizes_draws_them() -> None:
    content = {"items": [{"id": key, "size": "two"} for key in ("a", "b", "c")]}
    width = "=@space.4 * 4"

    shared = draw(content, components=weighted(width=width))
    equal = draw(content, components=weighted("equal", width=width))
    unsized = draw(content, components=weighted())

    assert item_frames(shared) == item_frames(equal)
    assert [f[0] for f in item_frames(shared)] == [0.0, 45.33, 90.67]
    assert "shares its width by its items' weights" in finding(unsized, "no-size").message


def test_a_key_both_an_item_s_component_and_its_list_declare_is_read_by_neither() -> None:
    """`lab/sized` declares `size` as a field it shows: on its item, `size` fills no field,
    and the weight takes its default share."""
    sized = block(
        {"l": label("size", width="=:width", when="size"), "b": box(width="=:width")},
        fields={"size": {"type": "string"}},
        preferred={"width": "=@space.3", "height": "=@space.3"},
    )
    components = {**weighted(width="=@space.4 * 4"), **lab(sized=sized)}
    content = {
        "items": [
            {"id": "a", "use": "lab/sized", "size": "four"},
            {"id": "b", "size": "two"},
            {"id": "c", "size": "four"},
        ]
    }

    result = draw(content, components=components)

    # One, two and four shares: `a` takes the weight's default.
    assert [f[2] for f in item_frames(result)] == [16.0, 32.0, 64.0]
    assert result.scene.find("top/items[a]/l") is None
    assert result.scene.find("top/items[a]/b") is not None


def a_pattern(**lists: Any) -> dict[str, Any]:
    """A pattern of a list `items`, drawn by `lab/chip` in a row, and a field `kind`; its
    `lists` are `lists`."""
    parts = {"items": {"repeat": "items", "draw": "lab/chip", "row": {}}}
    fields = {"items": LISTED, "kind": {"type": "object"}, "title": {"type": "string"}}
    return block(parts, fields=fields, lists=lists)


def test_a_patterns_lists_read_with_no_issue() -> None:
    declared = {
        "items": {
            "component": "kind",
            "arrangement": {"size": SIZE, "side": {"words": ["left", "right"]}},
        }
    }

    assert issues(a_pattern(**declared)) == []


def test_what_a_pattern_declares_for_its_lists_is_refused_where_it_does_not_hold() -> None:
    def refused(**lists: Any) -> list[tuple[str, str]]:
        return issues(a_pattern(**lists))

    # A list no part repeats over, and a key the entry does not take.
    assert refused(other={"component": "kind"}) == [(SHAPE, "lists.other")]
    assert refused(items={"draw": "lab/chip"}) == [(SHAPE, "lists.items.draw")]
    # A component field that is no field, or a list field.
    assert refused(items={"component": "kinds"}) == [(SHAPE, "lists.items.component")]
    assert refused(items={"component": "items"}) == [(SHAPE, "lists.items.component")]
    # An arrangement field with no word, a word twice, a word no name, or a reserved name.
    at = "lists.items.arrangement"
    assert refused(items={"arrangement": {"side": {"words": []}}}) == [(SHAPE, f"{at}.side.words")]
    twice = {"words": ["left", "left"]}
    assert refused(items={"arrangement": {"side": twice}}) == [(SHAPE, f"{at}.side.words")]
    assert refused(items={"arrangement": {"side": {"words": ["by"]}}}) == [
        (SHAPE, f"{at}.side.words")
    ]
    assert refused(items={"arrangement": {"state": {"words": ["on"]}}}) == [(SHAPE, f"{at}.state")]
    # A weight's shares: one for each word, above zero; and one weight for a list.
    lacking = {"words": ["one", "two"], "shares": {"one": 1}}
    zero = {"words": ["one", "two"], "shares": {"one": 1, "two": 0}}
    assert refused(items={"arrangement": {"size": lacking}}) == [(SHAPE, f"{at}.size.shares")]
    assert refused(items={"arrangement": {"size": zero}}) == [(SHAPE, f"{at}.size.shares")]
    assert refused(items={"arrangement": {"size": SIZE, "span": SIZE}}) == [(SHAPE, f"{at}.span")]


def test_a_component_field_that_a_part_places_or_passes_on_is_refused() -> None:
    slotted = a_pattern(items={"component": "kind"})
    slotted["parts"]["k"] = {"slot": "kind"}
    passed = a_pattern(items={"component": "kind"})
    passed["parts"]["p"] = {"use": "lab/chip", "fields": {"kind": "kind"}}

    assert issues(slotted) == [(SHAPE, "lists.items.component")]
    assert issues(passed) == [(SHAPE, "lists.items.component")]


def test_sharing_by_weights_needs_a_weight_of_the_list() -> None:
    data = a_pattern()
    data["parts"]["items"]["row"] = {"sizes": "shares"}

    assert issues(data) == [(SHAPE, "parts.items.row.sizes")]


def test_a_top_whose_layouts_are_its_pages_forms_declares_no_fields_for_its_pages() -> None:
    data = forms_top(lists={"pages": {"arrangement": {"size": SIZE}}})

    assert issues(data) == [(SHAPE, "lists.pages")]


# --- fields of runs ---------------------------------------------------------------------------

RUNS = "x-pkit-runs"

#: A terminal's line: the prompt, the command and the comment, each in its own colour, the
#: command in the heading's role.
TERMINAL = top(
    {
        "line": {
            "text": {
                "content": "line",
                "style": {
                    "by": "line",
                    "command": "type.heading",
                    "prompt": "type.body",
                    "comment": "type.body",
                },
                "fill": {
                    "by": "line",
                    "command": "text-primary",
                    "prompt": "accent",
                    "comment": "text-secondary",
                },
            },
            "width": "=:width",
        }
    },
    fields={"line": {"type": "string", RUNS: ["command", "prompt", "comment"]}},
)


def runs_drawn(content: dict[str, Any], trace: str = "top/line", **environment: Any) -> Any:
    """The scene of `content`, its findings, and the runs of the text at `trace`."""
    environment.setdefault("components", lab(top=TERMINAL))
    result = draw(content, roles=RUN_ROLES, fonts=RUN_FONTS, **environment)
    element = result.scene.find(trace)
    held = [run for paragraph in element.properties["paragraphs"] for run in paragraph]
    return result, element, held


def test_a_terminals_line_shows_each_run_in_the_role_and_paint_its_style_chooses() -> None:
    content = {
        "line": [
            {"text": "$ ", "style": "prompt"},
            "pkit visual render deck",
            {"text": "  # draws every page", "style": "comment"},
        ]
    }

    result, line, held = runs_drawn(content)

    assert result.findings == []
    assert line.properties["text"] == "$ pkit visual render deck  # draws every page"
    assert [(run["text"], run["style"], run["fill"]) for run in held] == [
        ("$ ", "type.body", "accent"),
        ("pkit visual render deck", "type.heading", "text-primary"),
        ("  # draws every page", "type.body", "text-secondary"),
    ]
    assert [run["font-family"] for run in held] == [
        ["Source Sans Pro"],
        [SEMIBOLD],
        ["Source Sans Pro"],
    ]
    assert [run["sources"]["text"] for run in held] == [f"content:line#{n}" for n in (1, 2, 3)]
    assert [run["sources"]["style"] for run in held] == [
        "content:line#1.style",
        "default:lab/top",
        "content:line#3.style",
    ]
    assert held[0]["sources"]["fill"] == "content:line#1.style"
    # The command's heading is the tallest role the text's runs take.
    assert line.properties["line-height"] == 28.8
    assert line.sources["line-height"] == "role:type.heading"


def test_a_field_of_runs_given_as_text_is_one_run_in_its_first_style() -> None:
    result, _, held = runs_drawn({"line": "pkit visual check"})

    assert result.findings == []
    assert [(run["text"], run["style"], run["fill"]) for run in held] == [
        ("pkit visual check", "type.heading", "text-primary")
    ]
    assert held[0]["sources"] == {
        "fill": "default:lab/top",
        "font-family": "role:type.heading",
        "font-size": "role:type.heading",
        "font-weight": "role:type.heading",
        "style": "default:lab/top",
        "text": "content:line",
    }


SENTENCE = top(
    {
        "say": {
            "text": {
                "content": "say",
                "style": {"by": "say", "plain": "type.body", "strong": "type.heading"},
                "fill": "text-primary",
            },
            "width": "=:width",
        }
    },
    fields={"say": {"type": "string", RUNS: ["plain", "strong"]}},
)


def test_a_sentence_sets_one_phrase_apart_and_its_lines_break_across_its_runs() -> None:
    content = {"say": ["Draw ", {"text": "every page of the deck", "style": "strong"}, " once."]}

    result, say, held = runs_drawn(content, "top/say", components=lab(top=SENTENCE))

    assert result.findings == []
    assert [run["style"] for run in held] == ["type.body", "type.heading", "type.body"]
    assert {run["fill"] for run in held} == {"text-primary"}
    assert held[1]["fonts"][0]["file"] == "SourceSansPro-Semibold.otf"
    assert " ".join(line["text"] for line in say.properties["lines"]) == say.properties["text"]
    spans = [span["run"] for line in say.properties["lines"] for span in line["spans"]]
    assert spans == sorted(spans) and set(spans) == {0, 1, 2}


def test_a_field_whose_only_run_holds_no_text_is_not_filled_under_a_condition() -> None:
    shown = top(
        {"say": {**SENTENCE["parts"]["say"], "when": "say"}},
        fields=SENTENCE["fields"]["properties"],
    )

    for empty in ([], [{"text": ""}], ["", {"text": "", "style": "strong"}]):
        result = draw({"say": empty}, components=lab(top=shown), roles=RUN_ROLES, fonts=RUN_FONTS)
        assert result.findings == [] and result.scene.find("top/say") is None, empty
    filled = draw({"say": ["", "x"]}, components=lab(top=shown), roles=RUN_ROLES, fonts=RUN_FONTS)
    assert filled.scene.find("top/say") is not None


#: A said line placed in a slot: its runs paint the strong style from the colour family, the
#: plain one with a role; a dropped one greys it.
SAID = block(
    {
        "say": {
            "text": {
                "content": "say",
                "style": "type.body",
                "fill": {"by": "say", "plain": "text-primary", "strong": ":colour.text"},
            },
            "width": "=:width",
        }
    },
    fields={"say": {"type": "string", RUNS: ["plain", "strong"]}},
    colour="blue",
    states={"dropped": {"colour": "grey"}},
)
TINTS = {"blue": {"text": "accent"}, "red": {"text": "text-secondary"}, "grey": {"text": "line"}}


def said(body: dict[str, Any]) -> Any:
    components = {
        **lab(
            top=top(
                {"s": {"slot": "body", "width": "=:width"}}, fields={"body": {"type": "object"}}
            )
        ),
        **lab(said=SAID),
    }
    return runs_drawn(
        {"body": {"use": "lab/said", **body}},
        "top/s/say",
        components=components,
        families=TINTS,
        concepts={"flow/queue": "red"},
    )


def test_a_run_that_names_a_concept_takes_its_family_and_a_state_replaces_it() -> None:
    runs = [
        "Write to ",
        {"text": "the queue", "style": "strong", "concept": "flow/queue"},
        {"text": " now", "style": "strong"},
    ]

    result, _, held = said({"say": runs})
    dropped, _, greyed = said({"say": runs, "state": "dropped"})

    assert result.findings == [] and dropped.findings == []
    assert [(run["fill"], run["sources"]["fill"]) for run in held] == [
        ("text-primary", "default:lab/said"),
        ("text-secondary", "content:body.say#2.concept"),
        ("accent", "default:lab/said"),
    ]
    assert [(run["fill"], run["sources"]["fill"]) for run in greyed] == [
        ("text-primary", "default:lab/said"),
        ("line", "content:body.state"),
        ("line", "content:body.state"),
    ]


def test_a_run_that_names_a_concept_no_notation_holds_is_a_finding_at_the_run() -> None:
    result, _, _ = said(
        {"say": ["A ", {"text": "b", "concept": "flow/nothing"}, {"text": "c", "concept": "plain"}]}
    )

    unknown = [(f.code, f.where) for f in result.findings if f.code == "unknown-concept"]
    assert unknown == [("unknown-concept", "body.say#2"), ("unknown-concept", "body.say#3")]
    assert "the notation `flow` holds no concept `nothing`" in result.findings[0].message


def test_a_slot_of_a_pages_layout_may_be_a_field_of_runs_its_drawing_chooses_by() -> None:
    layouts = with_layout(
        slots={"head": {"type": "string", RUNS: ["plain", "strong"]}},
        parts={
            "head": {
                "text": {
                    "content": "head",
                    "style": {"by": "head", "plain": "type.body", "strong": "type.heading"},
                },
                "width": "=:width",
            }
        },
    )
    component = forms_top(layouts=layouts)
    content = {
        "pages": [{"id": "a", "layout": "one", "head": ["A ", {"text": "b", "style": "strong"}]}]
    }

    assert issues(component) == []
    result, _, held = runs_drawn(content, "top/pages[a]/head", components=lab(top=component))
    assert result.findings == []
    assert [(run["style"], run["sources"]["text"]) for run in held] == [
        ("type.body", "content:pages[a].head#1"),
        ("type.heading", "content:pages[a].head#2"),
    ]


def marked(schema: dict[str, Any], **keys: Any) -> list[tuple[str, str]]:
    """What the engine finds in a component whose field `say` takes `schema`, shown by a
    text part that chooses its role by the field's words where they are `plain` and
    `strong`."""
    style = {"by": "say", "plain": "type.body", "strong": "type.heading"}
    choose = schema.get(RUNS) == ["plain", "strong"]
    parts = keys.pop(
        "parts", {"t": {"text": {"content": "say", "style": style if choose else "type.body"}}}
    )
    fields = {"say": schema, **keys.pop("fields", {})}
    return issues(top(parts, fields=fields, **keys))


def test_a_field_of_runs_reads_with_no_issue() -> None:
    assert marked({"type": "string", RUNS: ["plain", "strong"]}) == []
    assert marked({"type": ["string"], RUNS: ["one"]}) == []


def test_a_mark_lies_on_a_field_of_text_alone_with_its_words_each_once() -> None:
    at = f"fields.properties.say.{RUNS}"

    for schema in (
        {"type": ["string", "number"], RUNS: ["one", "two"]},
        {"type": "array", RUNS: ["one", "two"]},
        {RUNS: ["one", "two"]},
        {"type": "string", "enum": ["a"], RUNS: ["one", "two"]},
        {"type": "string", "const": "a", RUNS: ["one", "two"]},
        {"type": "string", RUNS: []},
        {"type": "string", RUNS: "one"},
        {"type": "string", RUNS: ["one", "by"]},
        {"type": "string", RUNS: ["one", "Two words"]},
        {"type": "string", RUNS: ["one", "one"]},
    ):
        assert marked(schema) == [(SHAPE, at)], schema


def test_a_mark_below_a_field_or_on_all_of_them_or_reached_by_a_ref_is_refused() -> None:
    below = {
        "type": "array",
        "items": {"type": "object", "properties": {"say": {"type": "string", RUNS: ["a"]}}},
    }
    component = top({}, fields={"lines": below})
    component["fields"][RUNS] = ["a"]
    referred = {"type": "string", RUNS: ["plain", "strong"]}

    assert issues(component) == [
        (SHAPE, f"fields.{RUNS}"),
        (SHAPE, f"fields.properties.lines.items.properties.say.{RUNS}"),
    ]
    assert marked(referred, fields={"other": {"$ref": "#/properties/say"}}) == [
        (SHAPE, "fields.properties.other.$ref")
    ]


def test_a_field_of_several_words_needs_a_text_part_that_chooses_by_them() -> None:
    plain = {"t": {"text": {"content": "say", "style": "type.body"}}}

    assert marked({"type": "string", RUNS: ["plain", "strong"]}, parts=plain) == [
        (SHAPE, f"fields.properties.say.{RUNS}")
    ]
    # A field of one word needs none; another text part may show the field in one look.
    assert marked({"type": "string", RUNS: ["only"]}, parts=plain) == []


def test_a_switch_on_a_fields_run_styles_names_each_of_its_words_and_no_other() -> None:
    def switching(style: dict[str, Any]) -> list[tuple[str, str]]:
        parts = {"t": {"text": {"content": "say", "style": style}}}
        return marked({"type": "string", RUNS: ["plain", "strong"]}, parts=parts)

    left_out = switching({"by": "say", "plain": "type.body"})
    foreign = switching(
        {"by": "say", "plain": "type.body", "strong": "type.body", "loud": "type.body"}
    )

    assert left_out == [(SHAPE, "parts.t.text.style")]
    assert foreign == [(SHAPE, "parts.t.text.style")]


def test_only_a_text_parts_role_and_paint_choose_by_the_run_styles_of_the_field_it_shows() -> None:
    schema = {"type": "string", RUNS: ["plain", "strong"]}
    words = {"by": "say", "plain": "start", "strong": "end"}
    anchor = {
        "content": "say",
        "style": {"by": "say", "plain": "type.body", "strong": "type.body"},
        "text-anchor": words,
    }
    boxed = {**box(), "box": {"fill": {"by": "say", "plain": "surface", "strong": "accent"}}}
    other = {
        "text": {
            "content": "note",
            "style": {"by": "say", "plain": "type.body", "strong": "type.body"},
        }
    }
    shown = {
        "text": {
            "content": "say",
            "style": {"by": "say", "plain": "type.body", "strong": "type.body"},
        }
    }

    assert marked(schema, parts={"t": {"text": anchor}}) == [(SHAPE, "parts.t.text.text-anchor")]
    assert marked(schema, parts={"t": shown, "b": boxed}) == [(SHAPE, "parts.b.box.fill")]
    assert marked(schema, parts={"t": shown, "o": other}, fields={"note": {"type": "string"}}) == [
        (SHAPE, "parts.o.text.style")
    ]
    assert marked(
        schema,
        parts={
            "t": shown,
            "w": {**box(), "width": {"by": "say", "plain": "=@space.1", "strong": "=@space.2"}},
        },
    ) == [(SHAPE, "parts.w.width")]


def test_a_field_of_runs_is_neither_passed_on_nor_read_but_by_a_text_part_or_a_condition() -> None:
    schema = {"type": "string", RUNS: ["one"]}
    shown = {"t": {"text": {"content": "say", "style": "type.body"}}}

    passed = marked(schema, parts={**shown, "p": {"use": "lab/inner", "fields": {"label": "say"}}})
    slotted = marked(schema, parts={**shown, "s": {"slot": "say"}})
    image = {"image": {"produced": "say"}, "width": "=@space.4", "height": "=@space.4"}
    pictured = marked(schema, parts={**shown, "i": image})
    conditioned = marked(schema, parts={**shown, "b": {**box(), "when": "say"}})

    assert passed == [(SHAPE, "parts.p.fields.label")]
    assert slotted == [(SHAPE, "parts.s.slot")]
    assert pictured == [(SHAPE, "parts.i.image.produced")]
    assert conditioned == []


def test_a_format_1_layouts_slot_takes_no_mark_the_field_it_names_takes_it() -> None:
    component = top(
        {"t": {"text": {"content": "say", "style": "type.body"}}},
        fields={"say": {"type": "string", RUNS: ["one"]}},
        layouts={"frame": {"slots": {"say": {RUNS: ["one"]}}}},
    )

    assert issues(component) == [(SHAPE, f"layouts.frame.slots.say.{RUNS}")]
