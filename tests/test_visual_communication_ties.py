"""Ties: a pattern's list of ties, each joining two items its end fields name by their key
paths, drawn with the connector tool (visual-communication DEC-011, DEC-005 point 2;
#2561).

Each rule is drawn from components written as mappings in memory and read through an
in-memory `Env` (`tests/visual_engine.py`):

- ties between items of the pattern's own lists, straight and with corners, with an
  arrowhead at either end; the scene's line, its points, the elements it meets and the
  sources of its ends;
- a tie into a list that a nested component draws, two levels deep, through a component
  that renames the list: the key path keeps the content file's keys;
- the engine's walk of a key path and the check of the content's, alike on the same paths;
- an end at a picture's point, a point the item does not expose, and one whose place
  cannot be read;
- an end drawn twice, drawn nowhere, and on another page: each tie left out and reported,
  the rest of its list drawn;
- three ends on one side of an item, spread evenly;
- a loop through the frames of the ends, refused; a connector whose route cannot be
  computed is left out, and its page drawn;
- a top whose layout holds a list of ties beside a list whose component field and
  weights it declares;
- what a component that takes ends, a connector and a list of ties may not declare;
- the SVG renderer's polyline and arrowheads, and the same file from the same scene;
- every file format 1 accepted draws as before: a line with no arrowhead draws the same
  bytes.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.in_process import load
from tests.visual_engine import (
    FakeEnv,
    block,
    codes,
    draw,
    env,
    frame,
    layout,
    square,
    top,
)

checks, svg = load("visual-communication", "checks", "plugins.svg")

LISTED = {"type": "array", "items": {"type": "object"}}
SHAPE = "component-shape"

#: The colours the roles the tests draw with take, where a test renders its scene.
BLACK = {"components": [0, 0, 0], "alpha": 1}
COLOURS = {"surface": BLACK, "line": BLACK}


def lab(**components: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {f"lab/{name}": component for name, component in components.items()}


def card(size: str = "=@space.4") -> dict[str, Any]:
    """A square card, as large as `size`."""
    return block(
        {"b": {"box": {"fill": "surface"}, "width": "=:width", "height": "=:height"}},
        preferred={"width": size, "height": size},
    )


def arrow(connect: Any = "straight", **line: Any) -> dict[str, Any]:
    """A component that takes ends and draws a connector between them."""
    props = {"stroke": "line", **line}
    return block({"l": {"line": props, "connect": connect}}, ends=True)


def tied(**keys: Any) -> dict[str, Any]:
    """A top that lays its `steps` out in a row, 32 px apart, and draws each tie of its
    `links` with `lab/arrow`, from its `from` to its `to`."""
    parts = keys.pop(
        "parts",
        {
            "steps": {"repeat": "steps", "draw": "lab/card", "row": {"gap": "=@space.4"}},
            "links": {"repeat": "links", "draw": "lab/arrow"},
        },
    )
    return top(
        parts,
        fields=keys.pop("fields", {"steps": LISTED, "links": LISTED}),
        lists=keys.pop("lists", {"links": {"ends": ["from", "to"]}}),
        **keys,
    )


def components(**more: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return lab(**{"top": tied(), "card": card(), "arrow": arrow(), **more})


def link(key: str, start: str, end: str, **more: Any) -> dict[str, Any]:
    return {"id": key, "from": {"item": start}, "to": {"item": end}, **more}


STEPS = [{"id": "a"}, {"id": "b"}, {"id": "c"}]


def line(result: Any, trace: str) -> dict[str, Any]:
    element = result.scene.find(trace)
    assert element is not None, f"no element {trace}"
    return element.properties


def ends(result: Any, trace: str) -> tuple[float, float, float, float]:
    props = line(result, trace)
    return props["x1"], props["y1"], props["x2"], props["y2"]


def finding(result: Any, code: str) -> Any:
    found = [f for f in result.findings if f.code == code]
    assert found, f"no finding {code} in {codes(result)}"
    return found[0]


def rendered(result: Any) -> Any:
    """The scene of `result` drawn by the SVG renderer: its pages and its losses."""
    return svg.render(
        result.scene.to_dict(),
        key="default",
        colours=COLOURS,
        font_file=lambda family: pytest.fail(f"no text is drawn, and {family} is asked for"),
        pictures={},
    )


# --- ties between items of the pattern's own lists ---------------------------------------------


def test_a_tie_joins_two_items_of_the_patterns_own_list_side_to_side() -> None:
    content = {"steps": STEPS, "links": [link("ab", "steps[a]", "steps[b]")]}

    result = draw(content, components=components())

    assert result.findings == []
    # The cards lie at 0, 64 and 128, 32 px square: the tie leaves `a` by its right side
    # and meets `b` by its left, at the middle of each.
    assert ends(result, "top/links[ab]/l") == (32, 16, 64, 16)
    element = result.scene.find("top/links[ab]/l")
    assert element is not None
    assert element.type == "line"
    assert element.sources["x1"] == element.sources["y1"] == "content:links[ab].from"
    assert element.sources["x2"] == element.sources["y2"] == "content:links[ab].to"
    assert element.properties["attached"] == {
        "start": {"id": "top/steps[a]", "side": "right"},
        "end": {"id": "top/steps[b]", "side": "left"},
    }
    assert element.sources["attached.start"] == "content:links[ab].from"
    assert "points" not in element.properties
    # The tie is a group drawn in the part's whole frame.
    assert frame(result, "top/links[ab]") == (0, 0, 640, 32)


def test_a_tie_with_corners_leaves_and_meets_each_end_square_to_its_side() -> None:
    steps = {"repeat": "steps", "draw": "lab/card", "row": {"gap": "=@space.4"}}
    low = {"repeat": "lows", "draw": "lab/card", "row": {}, "y": "=@space.4 * 2"}
    parts = {"steps": steps, "lows": low, "links": {"repeat": "links", "draw": "lab/arrow"}}
    fields = {"steps": LISTED, "lows": LISTED, "links": LISTED}
    found = lab(
        top=tied(
            parts=parts,
            fields=fields,
            preferred={"width": "=@size.figure", "height": "=@space.4 * 3"},
        ),
        card=card(),
        arrow=arrow("corners", **{"marker-end": "arrow"}),
    )
    content = {
        "steps": STEPS,
        "lows": [{"id": "z"}],
        "links": [link("cz", "steps[c]", "lows[z]")],
    }

    result = draw(content, components=found)

    assert result.findings == []
    props = line(result, "top/links[cz]/l")
    # `c` lies at 128..160 across, 0..32 down; `z` at 0..32 across, 64..96 down. They lie
    # further apart across (96) than down (32), so the tie leaves `c` by its left side
    # and meets `z` by its right, turning at the middle between them.
    assert props["points"] == [
        {"x": 128, "y": 16},
        {"x": 80, "y": 16},
        {"x": 80, "y": 80},
        {"x": 32, "y": 80},
    ]
    assert (props["x1"], props["y1"], props["x2"], props["y2"]) == (128, 16, 32, 80)
    assert (props["x"], props["y"], props["width"], props["height"]) == (32, 16, 96, 64)
    assert props["marker-end"] == "arrow"
    assert "marker-start" not in props
    element = result.scene.find("top/links[cz]/l")
    assert element is not None
    assert element.sources["marker-end"] == "default:lab/arrow"


def test_ties_that_meet_one_side_of_an_item_spread_evenly_along_it() -> None:
    # Three cards in a column at the right, each tied to one large card at the left.
    found = lab(
        top=tied(
            parts={
                "hub": {"repeat": "hubs", "draw": "lab/big", "row": {}},
                "steps": {
                    "repeat": "steps",
                    "draw": "lab/card",
                    "column": {"gap": "=@space.4"},
                    "x": "=@space.4 * 8",
                },
                "links": {"repeat": "links", "draw": "lab/arrow"},
            },
            fields={"hubs": LISTED, "steps": LISTED, "links": LISTED},
            preferred={"width": "=@size.figure", "height": "=@space.4 * 5"},
        ),
        big=card("=@space.4 * 4"),
        card=card(),
        arrow=arrow(),
    )
    content = {
        "hubs": [{"id": "h"}],
        "steps": STEPS,
        # Listed out of order: the ties spread by where their other ends lie.
        "links": [
            link("hc", "hubs[h]", "steps[c]"),
            link("ha", "hubs[h]", "steps[a]"),
            link("hb", "hubs[h]", "steps[b]"),
        ],
    }

    result = draw(content, components=found)

    assert result.findings == []
    # The hub is 128 px square at 0, 0; its right side takes the three ties at a quarter,
    # a half and three quarters of its height, ordered by their other ends.
    starts = {key: ends(result, f"top/links[{key}]/l")[:2] for key in ("ha", "hb", "hc")}
    assert starts == {"ha": (128, 32), "hb": (128, 64), "hc": (128, 96)}
    # Each card meets its one tie at the middle of its left side.
    assert ends(result, "top/links[hc]/l")[2:] == (256, 144)


def test_a_tie_takes_its_colour_as_every_item_does_from_neither_end() -> None:
    families = {"blue": {"edge": "line"}, "red": {"edge": "accent"}}
    found = components(arrow=arrow(stroke=":colour.edge"))
    found["lab/top"]["parts"]["links"]["colour"] = "blue"
    content = {
        "steps": [{"id": "a", "concept": "sys/store"}, {"id": "b", "concept": "sys/store"}],
        "links": [
            link("ab", "steps[a]", "steps[b]"),
            link("ba", "steps[b]", "steps[a]", concept="sys/store"),
        ],
    }

    result = draw(content, components=found, families=families, concepts={"sys/store": "red"})

    assert result.findings == []
    # Its place's family, though both its ends take another; then its own concept's.
    assert line(result, "top/links[ab]/l")["stroke"] == "line"
    assert line(result, "top/links[ba]/l")["stroke"] == "accent"


# --- a tie into a list a nested component draws --------------------------------------------------


def renaming() -> dict[str, dict[str, Any]]:
    """A top whose list `groups` a pattern draws, each group a component that passes its
    list `members` on to a pattern of cards as `entries`: a tie from the top's own `steps`
    to a card two levels down."""
    groups = block(
        {"g": {"repeat": "groups", "draw": "lab/group", "row": {}}},
        fields={"groups": LISTED},
        preferred={"width": "=@space.4 * 2", "height": "=@space.4 * 2"},
    )
    group = block(
        {"p": {"use": "lab/column", "fields": {"entries": "members"}}},
        fields={"members": LISTED},
        preferred={"width": "=@space.4", "height": "=@space.4 * 2"},
    )
    column = block(
        {"e": {"repeat": "entries", "draw": "lab/card", "column": {}}},
        fields={"entries": LISTED},
    )
    parts = {
        "steps": {"repeat": "steps", "draw": "lab/card", "row": {}},
        "right": {"use": "lab/groups", "fields": {"groups": "groups"}, "x": "=@space.4 * 10"},
        "links": {"repeat": "links", "draw": "lab/arrow"},
    }
    fields = {"steps": LISTED, "groups": LISTED, "links": LISTED}
    return lab(
        top=tied(
            parts=parts,
            fields=fields,
            preferred={"width": "=@size.figure", "height": "=@space.4 * 2"},
        ),
        groups=groups,
        group=group,
        column=column,
        card=card(),
        arrow=arrow(),
    )


def test_a_tie_reaches_an_item_two_levels_down_through_a_component_that_renames_its_list() -> None:
    content = {
        "steps": [{"id": "a"}],
        "groups": [{"id": "g1", "members": [{"id": "w"}, {"id": "z"}]}],
        "links": [link("az", "steps[a]", "groups[g1].members[z]")],
    }

    result = draw(content, components=renaming())

    assert result.findings == []
    # The card `z` lies at 320 across and 32 down: the second of its group's column.
    assert ends(result, "top/links[az]/l") == (32, 16, 320, 48)
    attached = line(result, "top/links[az]/l")["attached"]
    assert attached["end"] == {"id": "top/right/g[g1]/p/e[z]", "side": "left"}


def test_a_key_path_through_a_part_s_own_name_reaches_nothing() -> None:
    # `entries` is the name the group's part gives the list, not the content file's key.
    content = {
        "steps": [{"id": "a"}],
        "groups": [{"id": "g1", "members": [{"id": "z"}]}],
        "links": [link("az", "steps[a]", "groups[g1].entries[z]")],
    }

    result = draw(content, components=renaming())

    # Left out, and the check of the content reports the path (`tie-path`).
    assert result.scene.find("top/links[az]") is None
    assert "end-not-found" not in codes(result)


def test_the_engine_and_the_check_of_the_content_walk_a_key_path_alike() -> None:
    """The engine leaves out unreported a tie whose path the check of the content refuses
    (`Instance._held`), and the check reports it (`_Fields._end_path`). Each walks a path
    by its own code, so both run here on the same paths: one reaches an item exactly where
    the other does, or a tie would be left out with no finding."""
    found = renaming()
    pattern = found["lab/top"]
    pattern["parts"]["side"] = {"slot": "side", "x": "=@space.4 * 15"}
    pattern["fields"]["properties"] |= {
        "side": {"type": "object"},
        "hidden": LISTED,
        "meta": {"type": "object"},
    }
    content = {
        "steps": [{"id": "a"}],
        "groups": [{"id": "g1", "members": [{"id": "z"}]}],
        "side": {"use": "lab/column", "entries": [{"id": "q"}]},
        "hidden": [{"id": "h"}],
        "meta": {"things": [{"id": "t"}]},
        "links": [link("az", "steps[a]", "groups[g1].members[z]")],
    }
    reaches = {
        "steps[a]": True,
        "groups[g1]": True,
        "groups[g1].members[z]": True,
        "side.entries[q]": True,
        "hidden[h]": True,  # an item the content holds, which no part draws
        "meta.things[t]": True,  # through a mapping no component draws, by its keys alone
        "groups[g1].entries[z]": False,  # a part's own name
        "side.items[q]": False,
        "side[q]": False,
        "steps[q]": False,
        "stepz[a]": False,
        "steps": False,
        "steps[a].head": False,
        "links[az]": False,  # a tie
        "steps[a]..x": False,
    }

    root = layout.place_top(layout.Context(FakeEnv(components=found), "en"), "lab/top", content)
    assert root is not None
    index = root.by_path()
    fields = checks._Fields(FakeEnv(components=found), "content.en.yaml", [])
    reader = checks._Reader(
        frozenset(pattern["fields"]["properties"]), fields._repeats(pattern, ("lab/top",))
    )

    engine = {path: root._held(path, index) is not None for path in reaches}
    check = {path: fields._end_path(path, content, reader) is False for path in reaches}
    assert engine == check == reaches


# --- an end at a picture's point ----------------------------------------------------------------


def pictured() -> dict[str, dict[str, Any]]:
    """A top that lays out its `steps` and, 200 px across, its `pics`, each a 100 px square
    that exposes its picture, and ties them with `lab/arrow`."""
    picture = block(
        {"pic": {"image": {"produced": "art"}, "width": "=:width", "height": "=:height"}},
        fields={"art": {"type": "string"}},
        exposes=["pic"],
        preferred={"width": "=@space.1 * 25", "height": "=@space.1 * 25"},
    )
    parts = {
        "steps": {"repeat": "steps", "draw": "lab/card", "row": {}},
        "pics": {"repeat": "pics", "draw": "lab/pictured", "row": {}, "x": "=@space.2 * 25"},
        "links": {"repeat": "links", "draw": "lab/arrow"},
    }
    fields = {"steps": LISTED, "pics": LISTED, "links": LISTED}
    return lab(
        top=tied(
            parts=parts,
            fields=fields,
            preferred={"width": "=@size.figure", "height": "=@space.1 * 25"},
        ),
        pictured=picture,
        card=card(),
        arrow=arrow(),
    )


def to_a_point(point: str = "tip") -> dict[str, Any]:
    """Content that ties the step `a` to the point `point` of the picture `p`."""
    return {
        "steps": [{"id": "a"}],
        "pics": [{"id": "p", "art": "square"}],
        "links": [
            {"id": "ap", "from": {"item": "steps[a]"}, "to": {"item": "pics[p]", "point": point}}
        ],
    }


def test_a_tie_ends_at_a_point_the_items_picture_exposes() -> None:
    found = pictured()

    result = draw(to_a_point(), components=found, pictures={"square": square()})

    assert result.findings == []
    # The picture's tip lies at 75, 25 of its 100 px square, which lies at 200 across.
    assert ends(result, "top/links[ap]/l")[2:] == (275, 25)
    assert line(result, "top/links[ap]/l")["attached"]["end"] == {
        "id": "top/pics[p]/pic",
        "point": "tip",
    }

    lost = draw(to_a_point("heel"), components=found, pictures={"square": square()})

    assert lost.scene.find("top/links[ap]") is None
    point = finding(lost, "end-point")
    assert point.where == "links[ap].to.point"
    assert "`heel`" in point.message


def test_a_point_that_cannot_be_read_leaves_the_connector_out_and_the_page_drawn() -> None:
    # The picture's record places `tip` in its dark variant alone, and the scene reads the
    # default's: the tie names a point the picture exposes, whose place cannot be read.
    held = square()
    dark = {"colour-scheme.dark": held.points["tip"]["colour-scheme.dark"]}
    unread = env.PictureInfo(variants=held.variants, points={"tip": dark})

    result = draw(to_a_point(), components=pictured(), pictures={"square": unread})

    assert finding(result, "missing-exposed").message == (
        "top/links[ap]: the picture of `pic` exposes no point `tip`"
    )
    assert result.scene.find("top/links[ap]/l") is None
    assert result.scene.find("top/pics[p]/pic") is not None
    # The page is drawn; the one loss is the picture, which the test gives no file.
    drawn = rendered(result)
    assert [loss.what for loss in drawn.losses] == ["top/pics[p]/pic"]
    [page] = drawn.pages
    assert "top/links[ap]/l" not in page.svg


# --- an end not found -------------------------------------------------------------------------


def test_an_end_drawn_twice_or_nowhere_leaves_its_tie_out_and_the_rest_of_its_list_drawn() -> None:
    twice = {
        "steps": {"repeat": "steps", "draw": "lab/card", "row": {}},
        "again": {"repeat": "steps", "draw": "lab/card", "row": {}, "y": "=@space.2 * 5"},
        "links": {"repeat": "links", "draw": "lab/arrow"},
    }
    content = {
        "steps": STEPS,
        "hidden": [{"id": "h"}],
        "links": [
            link("ab", "steps[a]", "steps[b]"),
            link("ah", "steps[a]", "hidden[h]"),
            link("bc", "steps[b]", "steps[c]"),
        ],
    }
    fields = {"steps": LISTED, "hidden": LISTED, "links": LISTED}
    nowhere = lab(top=tied(fields=fields), card=card(), arrow=arrow())

    result = draw(content, components=nowhere)

    assert result.scene.find("top/links[ah]") is None
    assert result.scene.find("top/links[ab]/l") is not None
    assert result.scene.find("top/links[bc]/l") is not None
    lost = finding(result, "end-not-found")
    assert lost.where == "links[ah].to"
    assert "drawn nowhere" in lost.message
    assert lost.file == "" and lost.library == ""  # in the content
    assert "lock" in lost.fix

    drawn_twice = lab(top=tied(parts=twice), card=card(), arrow=arrow())
    content = {"steps": STEPS, "links": [link("ab", "steps[a]", "steps[b]")]}
    result = draw(content, components=drawn_twice)

    assert result.scene.find("top/links[ab]") is None
    assert "drawn 2 times" in finding(result, "end-not-found").message


def test_a_tie_off_its_ends_page_is_left_out_and_reported() -> None:
    # A top of format 1 with a slot of pages draws its ties above its pages, on none.
    page = top(
        {"steps": {"repeat": "steps", "draw": "lab/card", "row": {}}},
        fields={"steps": LISTED},
    )
    pager = top(
        {"body": {"slot": "body"}, "links": {"repeat": "links", "draw": "lab/arrow"}},
        fields={"body": {"type": "object"}, "links": LISTED},
        layouts={"frame": {"slots": {"body": {"pages": True}}}},
        lists={"links": {"ends": ["from", "to"]}},
    )
    content = {
        "body": {"use": "lab/page", "steps": STEPS},
        "links": [link("ab", "body.steps[a]", "body.steps[b]")],
    }

    result = draw(content, components=lab(top=pager, page=page, card=card(), arrow=arrow()))

    assert result.scene.find("top/links[ab]") is None
    off = finding(result, "tie-page")
    assert off.where == "links[ab]"
    assert "on no page" in off.message


# --- what is refused -----------------------------------------------------------------------------


def test_a_loop_through_the_frames_of_the_ends_is_refused() -> None:
    # The card `b` lies where the tie from `a` to `c` ends, which is where `c` lies.
    parts = {
        "steps": {"repeat": "steps", "draw": "lab/card", "row": {"gap": "=@space.4"}},
        "follow": {
            "box": {"fill": "surface"},
            "x": "=links[ac].l.right",
            "width": "=@space.4",
            "height": "=@space.4",
        },
        "links": {"repeat": "links", "draw": "lab/arrow"},
    }
    # The arrow exposes its connector, so the pattern may read it.
    exposing = {**arrow(), "exposes": ["l"]}
    found = lab(top=tied(parts=parts), card=card(), arrow=exposing)
    content = {"steps": STEPS, "links": [link("ac", "steps[a]", "steps[c]")]}

    result = draw(content, components=found)

    # Not a loop: the box reads the tie, and nothing the tie reads reads the box.
    assert result.findings == []
    assert frame(result, "top/follow")[0] == 128

    looped = dict(parts)
    looped["steps"] = {**parts["steps"], "x": "=follow.x"}
    result = draw(content, components={**found, **lab(top=tied(parts=looped))})

    loop = finding(result, "loop")
    assert "top ties → top/links[ac] {start} → top/steps.x" in loop.message
    # Its connector is left out, never drawn to a guessed place; the tie's group stays.
    assert result.scene.find("top/links[ac]/l") is None
    assert result.scene.find("top/links[ac]") is not None
    # The page is drawn, the cards in it, and nothing is lost.
    drawn = rendered(result)
    assert drawn.losses == []
    [page] = drawn.pages
    assert 'data-id="top/steps[a]/b"' in page.svg
    assert "top/links[ac]/l" not in page.svg


def test_a_component_that_takes_ends_reads_its_ends_frames_by_start_and_end() -> None:
    marked = block(
        {
            "l": {"line": {"stroke": "line"}, "connect": "straight"},
            "dot": {
                "ellipse": {"fill": "surface"},
                "x": "={start}.right",
                "y": "={start}.y",
                "width": "=@space.1",
                "height": "=@space.1",
            },
        },
        ends=True,
    )
    content = {"steps": STEPS, "links": [link("ab", "steps[a]", "steps[b]")]}

    result = draw(content, components=components(arrow=marked))

    assert result.findings == []
    assert frame(result, "top/links[ab]/dot")[:2] == (32, 0)


def issues(data: dict[str, Any]) -> list[tuple[str, str]]:
    """What the engine finds in a component's shape, by code and key path."""
    component = layout.Component("lab/x", data, layout.Context(FakeEnv(), "en"))
    return [(code, where) for code, where, _ in component.issues]


def test_a_pattern_and_a_component_that_takes_ends_read_with_no_issue() -> None:
    assert issues(tied()) == []
    assert issues(arrow()) == []
    assert issues(arrow({"by": "shape", "flat": "straight", "bent": "corners"})) == [
        (SHAPE, "parts.l.connect")
    ]
    switched = arrow({"by": "shape", "flat": "straight", "bent": "corners"})
    switched["options"] = {"shape": ["flat", "bent"]}
    assert issues(switched) == []


def test_what_a_list_of_ties_may_not_declare() -> None:
    def ends(value: Any) -> list[tuple[str, str]]:
        return issues(tied(lists={"links": {"ends": value}}))

    assert ends(["from"]) == [(SHAPE, "lists.links.ends")]
    assert ends(["from", "to", "via"]) == [(SHAPE, "lists.links.ends")]
    assert ends(["from", "from"]) == [(SHAPE, "lists.links.ends")]
    assert ends(["from", "use"]) == [(SHAPE, "lists.links.ends")]
    assert ends(["from", "To"]) == [(SHAPE, "lists.links.ends")]
    arranged = {"ends": ["from", "kind"], "arrangement": {"kind": {"words": ["a", "b"]}}}
    assert issues(tied(lists={"links": arranged})) == [(SHAPE, "lists.links.ends")]
    # End fields for a list no part repeats over.
    unrepeated = tied(lists={"links": {"ends": ["from", "to"]}, "steps": {"ends": ["a", "b"]}})
    parts = unrepeated["parts"]
    del parts["steps"]
    assert issues(unrepeated) == [(SHAPE, "lists.steps")]
    # A part over ties lays nothing along a row or a column.
    rowed = tied()
    rowed["parts"]["links"]["row"] = {}
    assert issues(rowed) == [(SHAPE, "parts.links.row")]


def test_what_a_component_that_takes_ends_may_not_declare() -> None:
    assert issues(arrow() | {"ends": "yes"}) == [(SHAPE, "ends")]
    assert issues(arrow() | {"options": {"start": ["a", "b"]}}) == [(SHAPE, "options.start")]
    # A connector in a component that takes none, or with ends of its own.
    plain = arrow()
    del plain["ends"]
    assert issues(plain) == [(SHAPE, "parts.l.connect")]
    pinned = arrow()
    pinned["parts"]["l"]["x1"] = "=@space.1"
    assert issues(pinned) == [(SHAPE, "parts.l.x1")]
    worded = arrow("bent")
    assert issues(worded) == [(SHAPE, "parts.l.connect")]
    # Below an end is nothing to read.
    below = arrow()
    below["parts"]["dot"] = {
        "box": {},
        "x": "={start}.b.x",
        "width": "=@space.1",
        "height": "=@space.1",
    }
    assert issues(below) == [("formula-reach", "parts.dot.x")]


def test_a_component_field_that_names_a_field_of_runs_is_refused() -> None:
    """A component field holds a mapping that places a component, never runs, in a pattern
    and in a top's layout (DEC-012 point 1). An end field names a key on a tie, no field of
    the pattern's, so no end field can name one."""
    said = {"type": "string", "x-pkit-runs": ["plain"]}
    pattern = tied(
        fields={"steps": LISTED, "links": LISTED, "say": said},
        lists={"links": {"ends": ["from", "to"]}, "steps": {"component": "say"}},
    )
    assert issues(pattern) == [(SHAPE, "lists.steps.component")]
    board = {
        "slots": {"steps": LISTED, "say": said},
        "lists": {"steps": {"component": "say"}},
        "parts": {"steps": {"repeat": "steps", "draw": "lab/card", "row": {}}},
    }
    deck = {
        "status": "experimental",
        "about": "A deck whose layout names a field of runs as a component field.",
        "fields": {
            "type": "object",
            "properties": {
                "pages": {"type": "array", "items": {"type": "object"}, "x-pkit-pages": True}
            },
        },
        "layouts": {"board": board},
        "preferred": {"width": "=@size.figure", "height": "=@space.4"},
    }
    assert issues(deck) == [(SHAPE, "layouts.board.lists.steps.component")]


def test_a_part_that_passes_a_field_on_to_a_list_of_ties_is_refused() -> None:
    placing = top(
        {"p": {"use": "lab/top", "fields": {"steps": "steps", "links": "links"}}},
        fields={"steps": LISTED, "links": LISTED},
    )
    content = {"steps": STEPS, "links": [link("ab", "steps[a]", "steps[b]")]}

    result = draw(content, use="lab/outer", components={**components(), **lab(outer=placing)})

    passed = finding(result, SHAPE)
    assert passed.where == "parts.p.fields.links"
    assert passed.extra["component"] == "lab/outer"
    # The rest is passed on, and the placed pattern draws no tie.
    assert result.scene.find("outer/p/steps[a]") is not None
    assert result.scene.find("outer/p/links[ab]") is None


def test_a_tie_whose_component_takes_no_ends_is_left_out() -> None:
    content = {
        "steps": STEPS,
        "links": [
            link("ab", "steps[a]", "steps[b]", use="lab/card"),
            link("bc", "steps[b]", "steps[c]"),
        ],
    }

    result = draw(content, components=components())

    assert result.scene.find("top/links[ab]") is None
    assert result.scene.find("top/links[bc]/l") is not None
    # Content names it: the check of the content reports it.
    assert result.findings == []

    # A piece's own pattern is judged where it is drawn; a library's, checked alone.
    own = tied()
    own["parts"]["links"]["draw"] = "lab/card"
    result = draw(content, use="piece/top", components={**components(), "piece/top": own})

    assert result.scene.find("top/links[bc]") is None
    default = finding(result, "tie-default")
    assert default.where == "parts.links.draw"
    assert default.extra["component"] == "piece/top"
    library = components(top=own)
    assert "tie-default" not in codes(draw(content, components=library))


# --- a top whose layout holds a list of ties ---------------------------------------------------


def test_a_tops_layout_holds_ties_beside_a_list_whose_component_and_weights_it_declares() -> None:
    weighted = {
        "component": "kind",
        "arrangement": {"size": {"words": ["one", "two"], "shares": {"one": 1, "two": 2}}},
    }
    layouts = {
        "board": {
            "slots": {"steps": LISTED, "kind": {"type": "object"}, "links": LISTED},
            "lists": {"steps": weighted, "links": {"ends": ["from", "to"]}},
            "parts": {
                "steps": {
                    "repeat": "steps",
                    "draw": "lab/card",
                    "row": {"sizes": "shares"},
                    "width": "=@space.4 * 3",
                },
                "links": {"repeat": "links", "draw": "lab/arrow"},
            },
        }
    }
    deck = {
        "status": "experimental",
        "about": "A deck whose layout ties its steps.",
        "fields": {
            "type": "object",
            "properties": {
                "pages": {"type": "array", "items": {"type": "object"}, "x-pkit-pages": True}
            },
        },
        "layouts": layouts,
        "preferred": {"width": "=@size.figure", "height": "=@space.4"},
    }
    assert issues(deck) == []
    content = {
        "pages": [
            {
                "id": "one",
                "layout": "board",
                "kind": {"use": "lab/card"},
                "steps": [{"id": "a"}, {"id": "b", "size": "two"}],
                "links": [link("ab", "steps[a]", "steps[b]")],
            }
        ]
    }

    result = draw(content, components={**components(), **lab(deck=deck)}, use="lab/deck")

    assert result.findings == []
    assert frame(result, "deck/pages[one]/steps[b]")[:3] == (32, 0, 64)
    assert ends(result, "deck/pages[one]/links[ab]/l") == (32, 16, 32, 16)
    # A drawing's issues lie in the top's file, under its layout.
    broken = {**layouts["board"], "lists": {"steps": weighted, "links": {"ends": ["from"]}}}
    assert issues({**deck, "layouts": {"board": broken}}) == [
        (SHAPE, "layouts.board.lists.links.ends")
    ]
