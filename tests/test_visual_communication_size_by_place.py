"""A row or a column that sizes each item across its line by a formula on the item's place,
its `cross-size` (visual-communication DEC-038 points 1 to 8; #3095).

Each point is drawn from components written as mappings in memory and read through an
in-memory `Env` (`tests/visual_engine.py`):

- `cross-size` gives each item its size across the line at its place, a switch's branch
  may give none, and a list of pages takes none (point 1);
- it alone reads `:place` and `:places`, and reads what the pattern's other formulas read
  (point 2);
- a sized item is placed as one of set size, a `stretch` drawn as `start`, and what its
  list gives it past what it asks for passes on to the last part it draws (point 3);
- the part asks across its line for the greatest size the formula gives, or zero (point 4);
- a sized item that gets less than it asks for, or zero, is short of it, and its frame never
  inverts (point 5);
- its size names its source as a part's formula does, and references and ties meet its
  frame (point 6);
- what the check finds when it reads the component, for each set of options that hold
  together, and what it finds when the scene is computed (point 7);
- a list that gives no `cross-size` draws as before (point 8);
- beside an order's steps, a list gives each place its step and its size by the same count,
  and the check judges both under each word of the option that switches them
  (visual-communication DEC-032 points 3 and 4).
"""

from __future__ import annotations

from typing import Any

from tests.visual_engine import Order, block, codes, draw, frame, top

LISTED = {"type": "array", "items": {"type": "object"}}

#: Three items, each by its id.
ITEMS = {"items": [{"id": "a"}, {"id": "b"}, {"id": "c"}]}

#: A step that narrows by place: three fifths, four fifths and the whole of the list's width.
STEPPED = "=items.width * (2 + :place) / (2 + :places)"

#: The list's width in `listed`: 128 px.
WIDTH = "=@space.4 * 4"


def lab(**components: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {f"lab/{name}": component for name, component in components.items()}


def tile(**preferred: str) -> dict[str, Any]:
    """An item that fills what it gets, and asks for the sizes `preferred` gives: by default a
    height of 16 px and no width."""
    return block(
        {"b": {"box": {"fill": "surface"}, "width": "=:width", "height": "=:height"}},
        preferred={"height": "=@space.3", **preferred},
    )


def listed(settings: dict[str, Any], *, item: dict[str, Any] | None = None, **keys: Any) -> Any:
    """A top that lays its `items` in a column 128 px wide, by `settings`, each drawn by a
    `tile` or by `item`; `keys` add to or replace the top's, a part's `width` under
    `width`."""
    part = {"repeat": "items", "draw": "lab/tile", "column": settings}
    width = keys.pop("width", WIDTH)
    if width is not None:
        part["width"] = width
    parts = {"items": part, **keys.pop("parts", {})}
    return lab(
        top=top(parts, fields={"items": LISTED, **keys.pop("fields", {})}, **keys),
        tile=item if item is not None else tile(),
    )


def across(result: Any, *keys: str) -> list[tuple[float, float]]:
    """Each item's place and size across the column: x and width."""
    found = []
    for key in keys or ("a", "b", "c"):
        x, _, width, _ = frame(result, f"top/items[{key}]")
        found.append((x, width))
    return found


def sources(result: Any, trace: str) -> dict[str, str]:
    element = result.scene.find(trace)
    assert element is not None, f"no element {trace}"
    return dict(element.sources)


def found(result: Any, code: str) -> list[Any]:
    return [finding for finding in result.findings if finding.code == code]


# --- point 1: `cross-size` gives each item its size across the line -----------------------------


def test_cross_size_gives_each_item_its_size_across_the_line_at_its_place() -> None:
    result = draw(ITEMS, components=listed({"cross-size": STEPPED, "align-items": "center"}))

    assert result.findings == []
    assert across(result) == [(25.6, 76.8), (12.8, 102.4), (0.0, 128.0)]
    # Along the column each item keeps the height it asks for.
    assert [frame(result, f"top/items[{key}]")[1] for key in "abc"] == [0.0, 16.0, 32.0]


def test_a_branch_that_gives_none_leaves_the_list_without_cross_size() -> None:
    switched = {"by": "shape", "stack": None, "steps": STEPPED}
    settings = {
        "cross-size": switched,
        "align-items": {"by": "shape", "stack": "stretch", "steps": "center"},
    }
    components = listed(settings, options={"shape": ["stack", "steps"]})

    stacked = draw(ITEMS, components=components)
    stepped = draw({**ITEMS, "shape": "steps"}, components=components)

    assert stacked.findings == stepped.findings == []
    assert across(stacked) == [(0.0, 128.0)] * 3
    assert across(stepped) == [(25.6, 76.8), (12.8, 102.4), (0.0, 128.0)]


def test_a_list_whose_items_are_pages_takes_no_cross_size() -> None:
    component = top(
        {"pages": {"repeat": "pages", "draw": "lab/tile", "column": {"cross-size": "=@space.4"}}},
        fields={"pages": LISTED},
        layouts={"frame": {"slots": {"pages": {"pages": True}}}},
    )

    result = draw({"pages": [{"id": "a"}]}, components=lab(top=component, tile=tile()))

    shape = [f for f in found(result, "component-shape") if "pages" in f.message]
    assert [f.where for f in shape] == ["parts.pages.column.cross-size"]


# --- point 2: it reads the item's place by names of its own -------------------------------------


def test_only_cross_size_reads_place_and_places() -> None:
    in_a_part = listed(
        {},
        parts={
            "mark": {
                "box": {"fill": "surface"},
                "width": "=@space.1 * :place",
                "height": "=@space.1",
            }
        },
    )
    in_a_value = listed({"cross-size": "=step * 2"}, values={"step": "=@space.3 * :places"})
    in_the_item = listed({}, item=tile(width="=@space.3 * :place"))

    for components, where in (
        (in_a_part, "parts.mark.width"),
        (in_a_value, "values.step"),
        (in_the_item, "preferred.width"),
    ):
        reach = found(draw(ITEMS, components=components), "formula-reach")
        assert [f.where for f in reach] == [where], where
        assert "only the `cross-size` of a row or a column reads" in reach[0].message


def test_cross_size_reads_roles_named_values_and_the_patterns_own_size() -> None:
    settings = {"cross-size": "=step * :place + :width - :width", "align-items": "end"}

    result = draw(ITEMS, components=listed(settings, values={"step": "=@space.3"}))

    assert result.findings == []
    assert across(result) == [(112.0, 16.0), (96.0, 32.0), (80.0, 48.0)]


# --- point 3: a sized item is placed as one of set size ----------------------------------------


def test_a_sized_item_is_placed_by_align_items_an_unnamed_one_at_the_start() -> None:
    def xs(**align: str) -> list[float]:
        settings = {"cross-size": STEPPED, **align}
        return [x for x, _ in across(draw(ITEMS, components=listed(settings)))]

    assert xs() == [0.0, 0.0, 0.0]
    assert xs(**{"align-items": "start"}) == [0.0, 0.0, 0.0]
    assert xs(**{"align-items": "center"}) == [25.6, 12.8, 0.0]
    assert xs(**{"align-items": "end"}) == [51.2, 25.6, 0.0]


def test_a_stretch_written_beside_cross_size_has_two_owners_and_draws_as_start() -> None:
    result = draw(ITEMS, components=listed({"cross-size": STEPPED, "align-items": "stretch"}))

    owners = found(result, "two-owners")
    assert [(f.where, f.library) for f in owners] == [
        ("parts.items.column.align-items", "lab@1.0.0")
    ]
    assert "`cross-size` gives it, and `align-items: stretch` stretches it" in owners[0].message
    assert across(result) == [(0.0, 76.8), (0.0, 102.4), (0.0, 128.0)]


def stacking() -> dict[str, dict[str, Any]]:
    """A column whose items are stacks: each asks for a width of 16 px, and holds a tile then a
    slot `foot` under it, which gives no width."""
    stack = block(
        {
            "head": {"use": "lab/inner", "width": "=@space.3"},
            "foot": {"slot": "foot", "y": "=head.bottom"},
        },
        fields={"foot": {"type": "object"}},
        preferred={"width": "=@space.3", "height": "=foot.bottom"},
    )
    components = listed({"cross-size": "=@space.4 * :place"}, item=stack)
    components["lab/inner"] = tile(width="=@space.3")
    return components


def test_what_cross_size_gives_past_what_an_item_asks_passes_to_the_part_it_draws_last() -> None:
    content = {
        "items": [
            {"id": "a", "foot": {"use": "lab/inner"}},
            {"id": "b", "foot": {"use": "lab/inner"}},
        ]
    }

    result = draw(content, components=stacking())

    # The second stack asks for 16 px and gets 64: its foot takes the other 48.
    assert result.findings == []
    assert frame(result, "top/items[b]")[2] == 64.0
    assert frame(result, "top/items[b]/head")[2] == 16.0
    assert frame(result, "top/items[b]/foot")[2] == 64.0
    assert sources(result, "top/items[b]/foot")["width"] == "engine"
    assert frame(result, "top/items[a]/foot")[2] == 32.0


def test_an_item_that_asks_for_no_size_across_passes_nothing_on() -> None:
    stack = block(
        {"foot": {"slot": "foot"}},
        fields={"foot": {"type": "object"}},
        preferred={"height": "=foot.bottom"},
    )
    components = listed({"cross-size": "=@space.4 * :place"}, item=stack)
    components["lab/inner"] = tile(width="=@space.3")

    result = draw({"items": [{"id": "a", "foot": {"use": "lab/inner"}}]}, components=components)

    assert result.findings == []
    assert frame(result, "top/items[a]")[2] == 32.0
    assert frame(result, "top/items[a]/foot")[2] == 16.0


# --- point 4: the part asks for the greatest size `cross-size` gives ----------------------------


def test_a_part_that_gives_no_size_across_is_the_greatest_size_cross_size_gives() -> None:
    components = listed({"cross-size": "=@space.3 * (4 - :place)"}, width=None)

    result = draw(ITEMS, components=components)
    empty = draw({"items": []}, components=components)

    assert result.findings == []
    assert frame(result, "top/items")[2] == 48.0
    assert across(result) == [(0.0, 48.0), (0.0, 32.0), (0.0, 16.0)]
    assert frame(empty, "top/items")[2] == 0.0


def test_a_part_that_gives_less_than_cross_size_asks_gets_less() -> None:
    result = draw(ITEMS, components=listed({"cross-size": "=@space.4 * :place"}, width="=@space.4"))

    short = found(result, "gets-less")
    assert [f.where for f in short] == ["top/items"]
    assert "gets 32.0 px of width and asks for 96.0" in short[0].message


# --- point 5: what an item asks for stays its own, and a sized item needs more than zero --------


def test_a_sized_item_given_less_than_it_asks_for_gets_less_in_the_content() -> None:
    wide = tile(width="=@space.4 + @space.1")
    components = listed({"cross-size": "=@space.3 * :place"}, item=wide)

    result = draw(ITEMS, components=components)

    # Each asks for 36 px, and the first two get 16 and 32.
    short = found(result, "gets-less")
    assert [(f.where, f.library) for f in short] == [("top/items[a]", ""), ("top/items[b]", "")]
    assert "gets 16.0 px of width and asks for 36.0" in short[0].message
    # It keeps the size it was given, and grows no wider.
    assert across(result) == [(0.0, 16.0), (0.0, 32.0), (0.0, 48.0)]


def test_a_sized_item_given_zero_or_less_is_held_at_zero_and_gets_less() -> None:
    result = draw(ITEMS, components=listed({"cross-size": "=@space.3 * (2 - :place)"}))

    short = found(result, "gets-less")
    assert [f.where for f in short] == ["top/items[b]", "top/items[c]"]
    assert "gets 0.0 px of width and asks for more than 0" in short[0].message
    assert across(result) == [(0.0, 16.0), (0.0, 0.0), (0.0, 0.0)]


def test_a_sized_item_that_asks_for_no_width_takes_what_it_is_given() -> None:
    result = draw(ITEMS, components=listed({"cross-size": "=@space.1 * :place"}))

    assert result.findings == []
    assert across(result) == [(0.0, 4.0), (0.0, 8.0), (0.0, 12.0)]


# --- point 6: every reader of frames meets the sized frame unchanged ----------------------------


def test_a_sized_items_size_names_the_source_a_parts_formula_names() -> None:
    def source(settings: dict[str, Any], **keys: Any) -> dict[str, str]:
        result = draw({**ITEMS, **keys.pop("content", {})}, components=listed(settings, **keys))
        return sources(result, "top/items[a]")

    switched = {"by": "shape", "stack": None, "steps": STEPPED}
    options = {"shape": ["stack", "steps"]}

    assert source({"cross-size": STEPPED}) == {
        "x": "engine",
        "y": "engine",
        "width": "default:lab/top",
        "height": "engine",
    }
    assert source({"cross-size": "=@space.4"})["width"] == "role:space.4"
    assert (
        source({"cross-size": switched}, options=options, content={"shape": "steps"})["width"]
        == "option:shape"
    )
    assert source({"cross-size": switched}, options=options)["width"] == "engine"


def test_a_reference_to_a_sized_item_reads_its_frame() -> None:
    mark = {
        "box": {"fill": "surface"},
        "x": "=items[a].x",
        "width": "=items[a].width",
        "height": "=@space.1",
    }

    result = draw(
        ITEMS,
        components=listed({"cross-size": STEPPED, "align-items": "center"}, parts={"mark": mark}),
    )

    assert result.findings == []
    assert frame(result, "top/mark")[0::2] == (25.6, 76.8)


def tied() -> dict[str, dict[str, Any]]:
    """A stepped column of levels, a note to its right, and ties between them, each drawn by
    an arrow from where it starts to where it ends."""
    parts = {
        "levels": {
            "repeat": "levels",
            "draw": "lab/tile",
            "width": "=@space.4 * 4",
            "column": {
                "gap": "=@space.2",
                "cross-size": "=levels.width * (2 + :place) / (2 + :places)",
                "align-items": "center",
            },
        },
        "notes": {
            "repeat": "notes",
            "draw": "lab/tile",
            "x": "=levels.right + @space.4",
            "width": "=@space.4",
            "column": {},
        },
        "ties": {"repeat": "ties", "draw": "lab/arrow"},
    }
    component = top(
        parts,
        fields={"levels": LISTED, "notes": LISTED, "ties": LISTED},
        lists={"ties": {"ends": ["from", "to"]}},
    )
    arrow = block({"l": {"line": {"stroke": "line"}, "connect": "straight"}}, ends=True)
    return lab(top=component, tile=tile(), arrow=arrow)


def test_a_tie_into_a_sized_item_ends_at_its_drawn_edge() -> None:
    content = {
        "levels": [{"id": "top"}, {"id": "middle"}, {"id": "foot"}],
        "notes": [{"id": "start"}],
        "ties": [{"id": "in", "from": {"item": "notes[start]"}, "to": {"item": "levels[top]"}}],
    }

    result = draw(content, components=tied())

    assert result.findings == []
    level = frame(result, "top/levels[top]")
    # The top level is three fifths of the column's 128 px, centred in it.
    assert level == (25.6, 0.0, 76.8, 16.0)
    line = result.scene.find("top/ties[in]/l")
    assert line is not None
    props = line.properties
    assert props["attached"]["end"] == {"id": "top/levels[top]", "side": "right"}
    # The tie ends at the level's right edge, not at the column's.
    assert (props["x2"], props["y2"]) == (25.6 + 76.8, 8.0)


# --- point 7: what the check finds when it reads the component, and when it computes the scene --


def test_cross_size_that_reads_its_parts_size_where_the_part_gives_none_is_a_loop() -> None:
    direct = draw(ITEMS, components=listed({"cross-size": "=items.width / 2"}, width=None))
    named = draw(
        ITEMS,
        components=listed({"cross-size": "=half"}, width=None, values={"half": "=items.right / 2"}),
    )

    for result in (direct, named):
        loops = found(result, "loop")
        assert [(f.where, f.library) for f in loops] == [
            ("parts.items.column.cross-size", "lab@1.0.0")
        ]
        assert "the `cross-size` of the list `items` reads the list's width" in loops[0].message
    # The empty list hides nothing: the component is read before its items.
    assert found(
        draw({"items": []}, components=listed({"cross-size": "=items.width / 2"}, width=None)),
        "loop",
    )


def test_the_loop_and_the_two_owners_are_judged_for_the_options_that_hold_together() -> None:
    options = {"shape": ["stack", "steps"]}
    # At `stack` the list gives no `cross-size`, so neither its stretch nor its read of its
    # own width counts; at `steps` it reads a role, beside `center`.
    apart = {
        "cross-size": {"by": "shape", "stack": None, "steps": "=wide"},
        "align-items": {"by": "shape", "stack": "stretch", "steps": "center"},
    }
    values = {"wide": {"by": "shape", "stack": "=items.width", "steps": "=@space.4"}}
    together = {
        "cross-size": {"by": "shape", "stack": None, "steps": "=wide"},
        "align-items": "stretch",
    }
    loops = {"wide": {"by": "shape", "stack": "=@space.4", "steps": "=items.width"}}

    narrow = tile(width="=@space.3")
    kept = draw(
        ITEMS, components=listed(apart, width=None, item=narrow, options=options, values=values)
    )
    broken = draw(
        ITEMS, components=listed(together, width=None, item=narrow, options=options, values=loops)
    )

    assert kept.findings == []
    assert [(f.code, f.where) for f in broken.findings if f.code in ("loop", "two-owners")] == [
        ("loop", "parts.items.column.cross-size.steps"),
        ("two-owners", "parts.items.column.align-items"),
    ]
    assert all("where `shape` is `steps`" in f.message for f in found(broken, "loop"))


def test_a_loop_found_when_the_component_is_read_is_not_found_again_in_the_scene() -> None:
    result = draw(ITEMS, components=listed({"cross-size": "=items.width / 2"}, width=None))

    assert codes(result).count("loop") == 1


def test_a_loop_through_its_parts_size_along_the_line_is_found_when_computed() -> None:
    # An item as tall as it is wide: the column's height reads each item's width.
    square = block(
        {"b": {"box": {"fill": "surface"}, "width": "=:width", "height": "=:height"}},
        preferred={"height": "=:width"},
    )

    result = draw(ITEMS, components=listed({"cross-size": "=items.height / 4"}, item=square))

    loops = found(result, "loop")
    assert loops and loops[0].where == "top"
    assert "a loop of references:" in loops[0].message


# --- point 8: an addition to format 1 -----------------------------------------------------------


def test_a_list_that_gives_no_cross_size_draws_as_before() -> None:
    switched = {"by": "shape", "stack": None, "steps": STEPPED}
    with_it = draw(
        ITEMS, components=listed({"cross-size": switched}, options={"shape": ["stack", "steps"]})
    )
    without = draw(ITEMS, components=listed({}, options={"shape": ["stack", "steps"]}))

    assert with_it.findings == without.findings == []
    assert with_it.scene.to_dict() == without.scene.to_dict()


# --- beside an order's steps (visual-communication DEC-032 points 3 and 4) -----------------------

#: An option whose word `steps` gives a list both its sizes and an order's steps by place.
SHAPES = {"shape": ["stack", "steps"]}

#: The places' families by `shape`: none from the pattern under `stack`, the steps under `steps`.
STEPS_BY_SHAPE = {"by": "shape", "stack": None, "steps": ":steps"}

#: The family a `painted` tile takes where its place takes none.
GREY = {"grey": {member: f"family.grey.{member}" for member in ("fill", "line", "text")}}


def painted() -> dict[str, Any]:
    """A `tile` that fills its box from its family, grey where its place gives none."""
    return block(
        {"b": {"box": {"fill": ":colour.fill"}, "width": "=:width", "height": "=:height"}},
        preferred={"height": "=@space.3"},
        colour="grey",
    )


def step(share: str) -> str:
    """The name of the order's step at `share`, as the scene names it."""
    return f"step({Order().first},{Order().last},{share})"


def fills(result: Any, *keys: str) -> list[Any]:
    found = []
    for key in keys:
        box = result.scene.find(f"top/items[{key}]/b")
        assert box is not None, f"no element top/items[{key}]/b"
        found.append(box.properties.get("fill"))
    return found


def shaped(content: dict[str, Any], components: Any, shape: str) -> Any:
    return draw({**content, "shape": shape}, components=components, families=GREY, order=Order())


def test_one_list_takes_its_step_and_its_size_at_the_same_place() -> None:
    """Both count the places the list draws: the item that is no mapping is left out of
    both, and the one that names its own component counts in both."""
    settings = {
        "cross-size": {"by": "shape", "stack": None, "steps": STEPPED},
        "align-items": {"by": "shape", "stack": "stretch", "steps": "center"},
    }
    components = listed(settings, item=painted(), options=SHAPES)
    components["lab/top"]["parts"]["items"]["colour"] = STEPS_BY_SHAPE
    content = {"items": [{"id": "a"}, "no item", {"id": "b", "use": "lab/tile"}, {"id": "c"}]}

    stepped = shaped(content, components, "steps")
    stacked = shaped(content, components, "stack")

    assert codes(stepped) == codes(stacked) == ["content-shape"]
    assert across(stepped) == [(25.6, 76.8), (12.8, 102.4), (0.0, 128.0)]
    assert fills(stepped, "a", "b", "c") == [step("0"), step("1/2"), step("1")]
    assert across(stacked) == [(0.0, 128.0)] * 3
    assert fills(stacked, "a", "b", "c") == ["family.grey.fill"] * 3


def test_the_steps_and_cross_size_are_judged_together_for_each_word() -> None:
    """One option switches a list's steps and its `cross-size`. A `stretch` written beside
    them breaks only where `shape` is `steps`, and the steps still draw there. Two parts
    over one list, each drawn under one word, are judged each under its own: neither names
    a family where the other gives the steps, nor stretches where it gives `cross-size`."""
    written = listed(
        {"cross-size": {"by": "shape", "stack": None, "steps": STEPPED}, "align-items": "stretch"},
        item=painted(),
        options=SHAPES,
    )
    written["lab/top"]["parts"]["items"]["colour"] = STEPS_BY_SHAPE
    apart = listed(
        {"cross-size": STEPPED, "align-items": "center"},
        item=painted(),
        options=SHAPES,
        parts={
            "stacked": {
                "repeat": "items",
                "draw": "lab/tile",
                "when": {"shape": ["stack"]},
                "colour": "grey",
                "width": WIDTH,
                "column": {"align-items": "stretch"},
            }
        },
    )
    stepped_part = apart["lab/top"]["parts"]["items"]
    stepped_part.update(when={"shape": ["steps"]}, colour=STEPS_BY_SHAPE)

    broken = shaped(ITEMS, written, "steps")
    kept = [shaped(ITEMS, apart, shape) for shape in SHAPES["shape"]]

    owners = found(broken, "two-owners")
    assert [f.where for f in owners] == ["parts.items.column.align-items"]
    assert "where `shape` is `steps`" in owners[0].message
    assert fills(broken, "a", "b", "c") == [step("0"), step("1/2"), step("1")]
    assert across(broken) == [(0.0, 76.8), (0.0, 102.4), (0.0, 128.0)]
    assert [result.findings for result in kept] == [[], []]
    assert fills(kept[1], "a", "b", "c") == [step("0"), step("1/2"), step("1")]
