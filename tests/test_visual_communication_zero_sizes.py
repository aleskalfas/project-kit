"""A component placed below the top needs more than zero along each axis, whatever gives it
the size, and no frame the engine computes has a size below zero (visual-communication
DEC-073 points 1 to 4; #3113).

Each point is drawn from components written as mappings in memory and read through an
in-memory `Env` (`tests/visual_engine.py`):

- a component that asks for no size along an axis needs more than zero of it, whether a
  list that shares its line among more gaps than it holds gives the size, a stretch, a
  part's formula or a top's slot of pages; one that asks for a size is judged by what it
  asks, and one that asks for less than zero is short where it gets none; the top is not
  judged (point 1);
- one that lies in a component with no size there is not reported, nor is a component that
  asks for zero and gets it, but an item its list sizes by place is, wherever it lies
  (point 2);
- every size is held at zero, what a formula reads of it included, each held item's place
  advances by its held size and the gap, and a list asks for what its held items come to,
  or, sharing its line, for the line it is given (point 3);
- the finding lies at the content where the size rests on what the content placed, and
  else in the component that gave it, where a released version only asks for attention
  (point 4).
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.visual_engine import block, draw, findings, frame, top

LISTED = {"type": "array", "items": {"type": "object"}}

#: Three items, each by its id.
ITEMS = {"items": [{"id": "a"}, {"id": "b"}, {"id": "c"}]}
ITEM_TRACES = ("top/items[a]", "top/items[b]", "top/items[c]")

#: A gap of 16 px: in a row 16 px wide, three items share 16 - 32 = -16 px, -5.33 px each.
GAP = "=@space.3"

#: A box that fills the component that draws it.
FILLING = {"box": {"fill": "surface"}, "width": "=:width", "height": "=:height"}

#: A width below zero from roles alone, 4 - 8 = -4 px.
BELOW_ZERO = "=@space.1 - @space.2"


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


def lies_in(finding: Any) -> str:
    """The component whose file a finding lies in, empty where it lies at the content."""
    return str(finding.extra.get("component", ""))


# --- point 1: a component placed below the top needs more than zero -----------------------------


def test_items_a_list_shares_equally_among_more_gaps_than_it_holds_are_short() -> None:
    result = draw(ITEMS, components=row({"gap": GAP, "sizes": "equal"}))

    found = short(result)
    assert [f.where for f in found] == list(ITEM_TRACES)
    assert found[0].message == (
        "top/items[a] gets 0.0 px of width and asks for more than 0, "
        "as it takes the width it is given, by its list `items`, "
        "which shares 16 px less 32 px of gaps among 3 items"
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
    assert found[0].message == (
        "top/items[a] gets 0.0 px of height and asks for more than 0, "
        "as it takes the height it is given, by its list `items`, "
        "which stretches it across its line of 0 px"
    )


def test_a_component_a_parts_formula_gives_less_than_zero_is_short() -> None:
    result = draw({}, components=placed("=:width - 2 * @space.4"))

    found = short(result)
    assert [f.where for f in found] == ["top/card/inner"]
    assert found[0].message == (
        "top/card/inner gets 0.0 px of width and asks for more than 0, "
        "as it takes the width it is given, by the part `inner` of `lab/card`, "
        "`=:width - 2 * @space.4`"
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
    assert found[0].message == "top/card/inner gets 0.0 px of width and asks for 4.0"


def test_a_page_a_tops_slot_gives_no_width_is_short() -> None:
    book = top(
        {"body": {"slot": "body", "width": "=:width - 2 * @size.figure"}},
        fields={"body": {}},
        layouts={"frame": {"slots": {"body": {"pages": True}}}},
    )

    result = draw({"body": {"use": "lab/fill"}}, components=lab(top=book, fill=fill()))

    found = short(result)
    assert [f.where for f in found] == ["top/body"]
    assert found[0].message == (
        "top/body gets 0.0 px of width and asks for more than 0, "
        "as it takes the width it is given, by the part `body` of `lab/top`, "
        "`=:width - 2 * @size.figure`"
    )
    assert widths(result, "top/body") == [0.0]


def test_a_component_that_asks_for_less_than_zero_is_short_where_it_gets_none() -> None:
    components = lab(top=top({"low": {"use": "lab/low"}}), low=fill(width=BELOW_ZERO))

    result = draw({}, components=components)

    (found,) = short(result)
    assert found.where == "top/low"
    assert found.message == (
        "top/low gets 0.0 px of width and asks for -4.0, less than 0, "
        "by `preferred.width` of `lab/low`, `=@space.1 - @space.2`"
    )
    assert widths(result, "top/low") == [0.0]


def test_a_component_that_asks_for_less_than_zero_and_is_given_room_is_not_short() -> None:
    low = {"use": "lab/low", "width": "=@space.3"}
    components = lab(top=top({"low": low}), low=fill(width=BELOW_ZERO))

    result = draw({}, components=components)

    assert short(result) == []
    assert widths(result, "top/low") == [16.0]


def test_the_top_is_not_judged() -> None:
    lowest = top({"b": FILLING}, preferred={"width": BELOW_ZERO, "height": "=@space.4"})

    result = draw({}, components=lab(top=lowest))

    assert short(result) == []
    assert widths(result, "top") == [0.0]


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


def test_a_component_inside_one_that_asks_for_less_than_zero_is_not_reported() -> None:
    # The one that asks for less than zero carries the finding; the `fill` it holds takes its
    # width and gets none.
    low = block(
        {"inner": {"use": "lab/fill", "width": "=:width"}},
        preferred={"width": BELOW_ZERO, "height": "=@space.3"},
    )
    components = lab(top=top({"low": {"use": "lab/low"}}), low=low, fill=fill())

    result = draw({}, components=components)

    assert [f.where for f in short(result)] == ["top/low"]
    assert widths(result, "top/low", "top/low/inner") == [0.0, 0.0]


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


def test_an_item_its_list_sizes_by_place_is_short_inside_one_of_no_size() -> None:
    # The holder gets no width, and its column sizes each item across it by place, to none.
    across = {"cross-size": "=items.width * :place / :places"}
    listed = {"repeat": "items", "draw": "lab/fill", "width": "=:width", "column": across}
    holder = block(
        {"items": listed}, fields={"items": LISTED}, preferred={"height": "=items.height"}
    )
    placing = {"use": "lab/holder", "fields": {"items": "items"}, "width": BELOW_ZERO}
    components = lab(
        top=top({"holder": placing}, fields={"items": LISTED}), holder=holder, fill=fill()
    )

    result = draw(ITEMS, components=components)

    found = {f.where: f for f in short(result)}
    sized = [f"top/holder/items[{each}]" for each in "abc"]
    assert sorted(found) == ["top/holder", *sized]
    assert found[sized[0]].message == (
        "top/holder/items[a] gets 0.0 px of width and asks for more than 0, "
        "as its list sizes it by place"
    )
    assert all(lies_in(found[trace]) == "" for trace in sized)


# --- point 3: no frame has a size below zero -----------------------------------------------------


def test_a_parts_size_below_zero_is_held_at_zero_and_read_so() -> None:
    small = {"box": {"fill": "surface"}, "width": BELOW_ZERO, "height": "=@space.1"}
    after = {"box": {"fill": "surface"}, "x": "=small.right", "height": "=@space.1"}
    after["width"] = "=small.width + @space.1"

    result = draw({}, components=lab(top=top({"small": small, "after": after})))

    # A part that draws a primitive takes no finding of its size (DEC-073 point 1).
    assert result.findings == []
    assert frame(result, "top/small") == (0.0, 0.0, 0.0, 4.0)
    assert frame(result, "top/after") == (0.0, 0.0, 4.0, 4.0)


def test_a_list_that_shares_its_line_is_reported_by_its_items_alone() -> None:
    result = draw(ITEMS, components=row({"gap": GAP, "sizes": "equal"}))

    assert {f.where for f in short(result)} == set(ITEM_TRACES)
    # The list asks for the line it is given, and each item, held at zero, lies at its
    # place, a gap after the one before, so the last lies past the line's end.
    assert widths(result, "top/items") == [16.0]
    assert [frame(result, trace)[0] for trace in ITEM_TRACES] == [0.0, 16.0, 32.0]


def test_a_list_of_its_items_own_sizes_asks_for_what_their_held_sizes_come_to() -> None:
    # Each item asks for 16 - 8 * 3 = -8 px, held at zero, and the gaps take 8 px.
    low = fill(width="=@space.3 - @space.2 * :count")
    listed = {"repeat": "items", "draw": "lab/low", "row": {"gap": "=@space.1"}}
    components = lab(top=top({"items": listed}, fields={"items": LISTED}), low=low)

    result = draw(ITEMS, components=components)

    assert [f.where for f in short(result)] == list(ITEM_TRACES)
    assert widths(result, "top/items", *ITEM_TRACES) == [8.0, 0.0, 0.0, 0.0]
    assert [frame(result, trace)[0] for trace in ITEM_TRACES] == [0.0, 4.0, 8.0]


# --- point 4: where the finding lies -------------------------------------------------------------


def test_a_size_that_rests_on_where_its_component_is_placed_lies_at_the_content() -> None:
    # The card takes its width from where it is placed, and `inner` reads it.
    result = draw({}, components=placed("=:width - 2 * @space.4"))

    (found,) = short(result)
    assert found.level == findings.FAILS
    assert (found.library, lies_in(found)) == ("", "")
    assert findings.level_where(found, True) == findings.FAILS


#: A card whose `inner` reads the width the card takes from where it is placed through a named
#: value, and one that reads it through a part of its own.
THROUGH = {
    "a named value": block(
        {"inner": {"use": "lab/fill", "width": "=room"}},
        values={"room": "=:width - 2 * @space.4"},
        preferred={"height": "=@space.3"},
    ),
    "a part": block(
        {
            "back": {"box": {"fill": "surface"}, "width": "=:width", "height": "=@space.1"},
            "inner": {"use": "lab/fill", "width": "=back.width - 2 * @space.4"},
        },
        preferred={"height": "=@space.3"},
    ),
}


@pytest.mark.parametrize("through", sorted(THROUGH))
def test_a_formula_rests_on_where_its_component_is_placed_through_a_value_or_a_part(
    through: str,
) -> None:
    components = lab(
        top=top({"card": {"use": "lab/card", "width": "=@space.4"}}),
        card=THROUGH[through],
        fill=fill(),
    )

    (found,) = short(draw({}, components=components))
    assert (found.where, lies_in(found)) == ("top/card/inner", "")


def test_a_size_a_list_shares_among_more_items_than_its_line_holds_lies_at_the_content() -> None:
    result = draw(ITEMS, components=row({"gap": GAP, "sizes": "equal"}))

    assert {lies_in(f) for f in short(result)} == {""}


def test_a_size_from_roles_alone_lies_in_the_component_that_gave_it() -> None:
    result = draw({}, components=placed(BELOW_ZERO))

    (found,) = short(result)
    assert found.where == "top/card/inner"
    assert (found.library, lies_in(found)) == ("lab@1.0.0", "lab/card")
    assert found.level == findings.FAILS
    # In a released version it asks for attention instead (DEC-002 point 7).
    assert findings.level_where(found, True) == findings.ATTENTION


def test_a_size_from_the_tops_own_width_lies_in_the_top() -> None:
    # The top asks for its width, so a formula that reads it rests on the top's own roles.
    book = top({"card": {"use": "lab/fill", "width": "=:width - 2 * @size.figure"}})

    result = draw({}, components=lab(top=book, fill=fill()))

    (found,) = short(result)
    assert (found.where, lies_in(found)) == ("top/card", "lab/top")


def test_a_component_that_asks_for_less_than_zero_by_roles_lies_in_its_own_file() -> None:
    components = lab(top=top({"low": {"use": "lab/low"}}), low=fill(width=BELOW_ZERO))

    (found,) = short(draw({}, components=components))
    assert lies_in(found) == "lab/low"
    assert findings.level_where(found, True) == findings.ATTENTION


def test_one_that_asks_for_less_than_zero_by_what_the_content_gives_lies_at_the_content() -> None:
    low = fill(width="=@space.3 - @space.2 * :count")
    listed = {"repeat": "items", "draw": "lab/low", "row": {}}
    components = lab(top=top({"items": listed}, fields={"items": LISTED}), low=low)

    found = short(draw(ITEMS, components=components))

    assert [f.where for f in found] == list(ITEM_TRACES)
    assert {lies_in(f) for f in found} == {""}
    assert found[0].message == (
        "top/items[a] gets 0.0 px of width and asks for -8.0, less than 0, "
        "by `preferred.width` of `lab/low`, `=@space.3 - @space.2 * :count`"
    )
