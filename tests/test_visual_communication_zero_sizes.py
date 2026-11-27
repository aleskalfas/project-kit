"""A component given a size of zero or less, whatever gives it, gets less than it asks for,
and no frame the engine computes has a size below zero (visual-communication DEC-073
points 1 to 4; #3113).

Each point is drawn from components written as mappings in memory and read through an
in-memory `Env` (`tests/visual_engine.py`):

- a component that asks for no size along an axis needs more than zero of it, whether a
  list that shares its line among more gaps than it holds gives the size, a stretch, or a
  part's formula, and one that asks for a size is judged by what it asks (point 1);
- one that lies in a component with no size there is not reported, nor is a component that
  asks for zero and gets it (point 2);
- every size is held at zero, what a formula reads of it included, and a list that shares
  its line is reported by its items alone (point 3);
- the finding lies at the content, so it fails wherever the components come from (point 4).
"""

from __future__ import annotations

from typing import Any

from tests.visual_engine import block, draw, findings, frame, top

LISTED = {"type": "array", "items": {"type": "object"}}

#: Three items, each by its id.
ITEMS = {"items": [{"id": "a"}, {"id": "b"}, {"id": "c"}]}
ITEM_TRACES = ("top/items[a]", "top/items[b]", "top/items[c]")

#: A gap of 16 px: in a row 16 px wide, three items share -32 px, -5.33 px each.
GAP = "=@space.3"

#: A box that fills the component that draws it.
FILLING = {"box": {"fill": "surface"}, "width": "=:width", "height": "=:height"}


def lab(**components: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {f"lab/{name}": component for name, component in components.items()}


def fill(**preferred: str) -> dict[str, Any]:
    """A component that fills what it gets, as a card as wide as it is given does, and asks
    for the sizes `preferred` gives: by default a height of 16 px and no width."""
    return block({"b": FILLING}, preferred={"height": "=@space.3", **preferred})


def row(settings: dict[str, Any], *, item: dict[str, Any] | None = None, **part: Any) -> Any:
    """A top that lays its `items` in a row 16 px wide by `settings`, each drawn by a `fill`
    or by `item`; `part` adds to or replaces the list part's keys."""
    listed = {"repeat": "items", "draw": "lab/fill", "width": "=@space.3", "row": settings}
    return lab(
        top=top({"items": {**listed, **part}}, fields={"items": LISTED}),
        fill=item if item is not None else fill(),
    )


def card(width: str, inner: str = "lab/fill") -> dict[str, Any]:
    """A component that asks for no width, whose part `inner` places `inner` as wide as
    `width`."""
    return block({"inner": {"use": inner, "width": width}}, preferred={"height": "=@space.3"})


def placed(width: str, *, inner: dict[str, Any] | None = None) -> Any:
    """A top that places a `card` 32 px wide, whose part `inner` places a `fill`, or
    `inner`, as wide as `width`."""
    return lab(
        top=top({"card": {"use": "lab/card", "width": "=@space.4"}}),
        card=card(width),
        fill=inner if inner is not None else fill(),
    )


def short(result: Any) -> list[Any]:
    return [finding for finding in result.findings if finding.code == "gets-less"]


def widths(result: Any, *traces: str) -> list[float]:
    return [frame(result, trace)[2] for trace in traces]


# --- point 1: a component that asks for no size needs more than zero of it ----------------------


def test_items_a_list_shares_equally_among_more_gaps_than_it_holds_are_short() -> None:
    result = draw(ITEMS, components=row({"gap": GAP, "sizes": "equal"}))

    found = short(result)
    assert [f.where for f in found] == list(ITEM_TRACES)
    assert found[0].message == (
        "top/items[a] gets 0.0 px of width and asks for more than 0, "
        "as it takes the width it is given"
    )
    assert widths(result, *ITEM_TRACES) == [0.0, 0.0, 0.0]


def test_items_a_list_shares_by_their_weights_among_too_many_gaps_are_short() -> None:
    span = {"words": ["one", "two"], "shares": {"one": 1, "two": 2}}
    components = row({"gap": GAP, "sizes": "shares"})
    components["lab/top"]["lists"] = {"items": {"arrangement": {"span": span}}}
    content = {"items": [{"id": "a"}, {"id": "b", "span": "two"}, {"id": "c"}]}

    result = draw(content, components=components)

    assert [f.where for f in short(result)] == list(ITEM_TRACES)
    assert widths(result, *ITEM_TRACES) == [0.0, 0.0, 0.0]


def test_items_a_stretch_gives_no_height_are_short() -> None:
    # A row given no height stretches its items to none; each asks for no height of its own.
    tall = block({"b": FILLING}, preferred={"width": "=@space.3"})
    components = row(
        {"align-items": "stretch"}, item=tall, width="=@space.4 * 3", height="=@space.1 - @space.1"
    )

    result = draw(ITEMS, components=components)

    found = short(result)
    assert [f.where for f in found] == list(ITEM_TRACES)
    assert "gets 0.0 px of height and asks for more than 0" in found[0].message


def test_a_component_a_parts_formula_gives_less_than_zero_is_short() -> None:
    result = draw({}, components=placed("=:width - 2 * @space.4"))

    found = short(result)
    assert [f.where for f in found] == ["top/card/inner"]
    assert found[0].message == (
        "top/card/inner gets 0.0 px of width and asks for more than 0, "
        "as it takes the width it is given"
    )
    assert widths(result, "top/card/inner", "top/card/inner/b") == [0.0, 0.0]


def test_a_component_a_parts_formula_gives_zero_is_short() -> None:
    result = draw({}, components=placed("=:width - @space.4"))

    assert [f.where for f in short(result)] == ["top/card/inner"]


def test_a_component_given_more_than_zero_is_not_short() -> None:
    result = draw({}, components=placed("=:width - @space.3"))

    assert result.findings == []
    assert widths(result, "top/card/inner") == [16.0]


def test_a_component_that_asks_for_a_size_is_judged_by_what_it_asks() -> None:
    result = draw({}, components=placed("=:width - 2 * @space.4", inner=fill(width="=@space.1")))

    found = short(result)
    assert [f.where for f in found] == ["top/card/inner"]
    assert "top/card/inner gets 0.0 px of width and asks for 4.0" in found[0].message


# --- point 2: not where the component it lies in has no size there ------------------------------


def test_a_component_inside_one_given_no_room_is_not_reported() -> None:
    # The card's `inner` gets nothing, and the `fill` inside it takes all of that.
    components = lab(
        top=top({"card": {"use": "lab/card", "width": "=@space.4"}}),
        card=card("=:width - 2 * @space.4", inner="lab/holder"),
        holder=card("=:width"),
        fill=fill(),
    )

    result = draw({}, components=components)

    assert [f.where for f in short(result)] == ["top/card/inner"]
    assert widths(result, "top/card/inner", "top/card/inner/inner") == [0.0, 0.0]


def test_a_component_that_asks_for_zero_and_gets_it_is_not_short() -> None:
    # A list that holds nothing asks for no width, so the component around it asks for
    # none, and what fills that component gets none: nothing is short.
    empty = block(
        {
            "items": {"repeat": "items", "draw": "lab/fill", "row": {}},
            "under": {"use": "lab/fill", "width": "=:width"},
        },
        fields={"items": LISTED},
        preferred={"width": "=items.width", "height": "=@space.3"},
    )
    components = lab(top=top({"empty": {"use": "lab/empty"}}), empty=empty, fill=fill())

    result = draw({}, components=components)

    assert short(result) == []
    assert widths(result, "top/empty", "top/empty/under") == [0.0, 0.0]


# --- point 3: no frame has a size below zero -----------------------------------------------------


def test_a_parts_size_below_zero_is_held_at_zero_and_read_so() -> None:
    small = {"box": {"fill": "surface"}, "width": "=@space.1 - @space.2", "height": "=@space.1"}
    after = {"box": {"fill": "surface"}, "x": "=small.right", "height": "=@space.1"}
    after["width"] = "=small.width + @space.1"

    result = draw({}, components=lab(top=top({"small": small, "after": after})))

    # A part that draws a primitive takes no finding of its size (DEC-073, Rationale).
    assert result.findings == []
    assert frame(result, "top/small") == (0.0, 0.0, 0.0, 4.0)
    assert frame(result, "top/after") == (0.0, 0.0, 4.0, 4.0)


def test_a_list_that_shares_its_line_is_reported_by_its_items_alone() -> None:
    result = draw(ITEMS, components=row({"gap": GAP, "sizes": "equal"}))

    assert {f.where for f in short(result)} == set(ITEM_TRACES)
    # Each item is held at zero at its place along the line, a gap after the one before.
    assert [frame(result, trace)[0] for trace in ITEM_TRACES] == [0.0, 16.0, 32.0]


# --- point 4: the finding lies at the content ----------------------------------------------------


def test_the_finding_lies_at_the_content_and_fails() -> None:
    result = draw({}, components=placed("=:width - 2 * @space.4"))

    (found,) = short(result)
    assert found.level == findings.FAILS
    assert found.library == ""
    assert "component" not in found.extra
