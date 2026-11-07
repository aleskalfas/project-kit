"""A size changes a component's shape (visual-communication DEC-021 points 3 to 5 and 7; #2798).

Each rule is drawn at two sizes or more, from components written as mappings in memory and
read through the in-memory `Env` (`tests/visual_engine.py`). Each scene is given the size
axes a piece can name and the mode of each at its key (`layout.Sizes`), as the pipeline
gives them from the foundations:

- a list that lies along a row on a desktop and down a column on a phone, from one file:
  two `repeat` parts over one list, each with a `when` by the size;
- a part a size hides, with zero size at its place, so a formula that reads its frame
  holds at both sizes; and what must find an item a size hides, which fails there;
- a switch by a size on a part's `x` and `width`, on a `repeat`'s settings and on a placed
  component's option, at any depth, each value naming the axis as its source;
- a mode a component does not name, which takes its default's branch, so a new mode
  breaks no component, and no list on two parts vanishes at it;
- what is refused when a component is read: a marked name that reads no size axis a piece
  can name, a mode the axis lacks, a switch that leaves out the default, a `when` by a
  size that switches again, and two parts over one list that do not draw each item once.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import pytest

from tests.visual_engine import VERSIONS, FakeEnv, block, frame, layout, scene, top


@dataclass(frozen=True)
class Axis:
    """A size axis as the foundations declare it: its modes and its default."""

    modes: tuple[str, ...]
    default: str


#: The size axis the tests read, as the foundations' `device` will declare it.
DEVICE = Axis(("desktop", "tablet", "phone"), "desktop")

#: The size axis before its mode `tablet` is added: a component written then names its
#: default and `phone`.
TWO_DEVICES = Axis(("desktop", "phone"), "desktop")

#: Yes on a desktop, no on a phone, and the other way round. A mode neither names takes
#: the desktop's branch.
ON_DESKTOP = {"by": ":device", "desktop": True, "phone": False}
ON_PHONE = {"by": ":device", "desktop": False, "phone": True}


def drawn(
    content: Mapping[str, Any] | None = None,
    *,
    mode: str = "desktop",
    axes: Mapping[str, Any] | None = None,
    components: Mapping[str, Any] | None = None,
    use: str = "lab/top",
) -> Any:
    """The scene of a piece whose top is `use`, at `mode` of the size axis `device`, the
    axes a piece can name being `axes`, by default `device` alone."""
    axes = {"device": DEVICE} if axes is None else axes
    modes = {"device": mode} if "device" in axes else {}
    key = "default" if mode == "desktop" else f"device.{mode}"
    return scene.compute_scene(
        piece="test-piece",
        top=use,
        content=dict(content or {}),
        language="en",
        lock=dict(VERSIONS),
        size_key=key,
        seam_version=3,
        env=FakeEnv(components=dict(components or {})),
        facts=layout.stand_ins("draft"),
        sizes=layout.Sizes(axes, modes),
    )


def box(**geometry: Any) -> dict[str, Any]:
    return {"box": {"fill": "surface"}, "width": "=@space.4", "height": "=@space.4", **geometry}


def lab(**components: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {f"lab/{name}": component for name, component in components.items()}


def issues(result: Any, code: str) -> list[str]:
    """The messages of the findings of `code` a scene holds, in the order found."""
    return [finding.message for finding in result.findings if finding.code == code]


def item() -> dict[str, Any]:
    """A block one space wide and tall, that each list below draws for each item."""
    return block({"b": box()}, preferred={"width": "=@space.4", "height": "=@space.4"})


#: Three items, each with an id.
ITEMS = {"items": [{"id": "a"}, {"id": "b"}, {"id": "c"}]}

LISTED = {"items": {"type": "array", "items": {"type": "object"}}}


def flipping(**rows: Any) -> dict[str, dict[str, Any]]:
    """A top that lays its items along a row on a desktop and down a column on a phone,
    both parts over one list: `rows` adds to the parts or replaces them."""
    parts = {
        "across": {"repeat": "items", "draw": "lab/item", "when": ON_DESKTOP, "row": {}},
        "down": {"repeat": "items", "draw": "lab/item", "when": ON_PHONE, "column": {}},
        **rows,
    }
    return lab(top=top(parts, fields=LISTED), item=item())


# --- a list changes direction on two parts (point 4) --------------------------------------


def test_a_list_lies_along_a_row_on_a_desktop_and_down_a_column_on_a_phone() -> None:
    desktop = drawn(ITEMS, components=flipping())
    phone = drawn(ITEMS, mode="phone", components=flipping())

    assert desktop.findings == phone.findings == []
    assert [frame(desktop, f"top/across[{i}]")[:2] for i in "abc"] == [
        (0.0, 0.0),
        (32.0, 0.0),
        (64.0, 0.0),
    ]
    assert [frame(phone, f"top/down[{i}]")[:2] for i in "abc"] == [
        (0.0, 0.0),
        (0.0, 32.0),
        (0.0, 64.0),
    ]
    # An item's trace id differs by size, since another part draws it.
    assert desktop.scene.find("top/down") is None
    assert phone.scene.find("top/across") is None
    item_b = phone.scene.find("top/down[b]")
    assert item_b is not None and item_b.properties["component"] == "lab/item"


def test_a_formula_that_reads_the_lists_frame_reads_both_parts() -> None:
    """The part a size hides has zero size at its place, so a sum of both parts' frames is
    the frame of the part drawn."""
    rule = box(y="=across.height + down.height", width="=across.width + down.width")
    desktop = drawn(ITEMS, components=flipping(rule=rule))
    phone = drawn(ITEMS, mode="phone", components=flipping(rule=rule))

    assert desktop.findings == phone.findings == []
    assert frame(desktop, "top/rule")[1:3] == (32.0, 96.0)
    assert frame(phone, "top/rule")[1:3] == (96.0, 32.0)


def test_a_mode_no_part_names_takes_the_defaults_branch_and_no_list_vanishes_at_it() -> None:
    """Adding `tablet` to an axis whose component names `desktop` and `phone` breaks no
    component: a tablet draws the desktop's row."""
    before = drawn(ITEMS, mode="phone", axes={"device": TWO_DEVICES}, components=flipping())
    tablet = drawn(ITEMS, mode="tablet", components=flipping())

    assert before.findings == tablet.findings == []
    assert [frame(tablet, f"top/across[{i}]")[:2] for i in "abc"] == [
        (0.0, 0.0),
        (32.0, 0.0),
        (64.0, 0.0),
    ]
    assert tablet.scene.find("top/down") is None


def test_no_option_names_an_item_of_a_list_two_parts_repeat_over() -> None:
    components = flipping(
        mark=box(x="={at}.x", width="=@space.1"),
    )
    components["lab/top"]["options"] = {"at": {"item": "items"}}

    result = drawn({**ITEMS, "at": {"item": "a"}}, components=components)

    assert any(
        "names an item of `items`, over which not exactly one part repeats" in message
        for message in issues(result, "component-shape")
    )
    assert any(
        "not exactly one part repeats" in message for message in issues(result, "formula-reach")
    )


# --- a size hides a part as an option hides one (point 5) ---------------------------------


def noted(**below: Any) -> dict[str, dict[str, Any]]:
    """A top whose note is drawn on a desktop alone, and a rule placed below it."""
    parts = {
        "note": {**box(height="=@space.3"), "when": ON_DESKTOP},
        "rule": box(y="=note.bottom", width="=@space.1", **below),
    }
    return lab(top=top(parts))


def test_a_part_a_size_hides_is_not_drawn_and_has_zero_size_at_its_place() -> None:
    desktop = drawn(components=noted())
    phone = drawn(mode="phone", components=noted())

    assert desktop.findings == phone.findings == []
    assert frame(desktop, "top/note") == (0.0, 0.0, 32.0, 16.0)
    assert phone.scene.find("top/note") is None
    assert frame(desktop, "top/rule")[1] == 16.0
    assert frame(phone, "top/rule")[1] == 0.0


def test_a_when_by_a_size_may_give_a_when_of_its_own_in_a_branch() -> None:
    parts = {
        "head": {
            "text": {"content": "head", "style": "type.body", "fill": "text-primary"},
            "when": {"by": ":device", "desktop": "head", "phone": False},
        }
    }
    components = lab(top=top(parts, fields={"head": {"type": "string"}}))

    assert drawn({"head": "Hi"}, components=components).scene.find("top/head") is not None
    assert drawn({}, components=components).scene.find("top/head") is None
    assert drawn({"head": "Hi"}, mode="phone", components=components).scene.find("top/head") is None


def test_what_must_find_an_item_a_size_hides_fails_at_that_size() -> None:
    parts = {
        "across": {"repeat": "items", "draw": "lab/item", "when": ON_DESKTOP, "row": {}},
        "mark": box(x="=across[b].x", width="=@space.1"),
    }
    components = lab(top=top(parts, fields=LISTED), item=item())

    desktop = drawn(ITEMS, components=components)
    phone = drawn(ITEMS, mode="phone", components=components)

    assert desktop.findings == []
    assert frame(desktop, "top/mark")[0] == 32.0
    [missing] = issues(phone, "missing-exposed")
    assert "the list `across` draws no item across[b]" in missing


# --- a switch by a size, at any depth (point 3) ---------------------------------------------


def test_a_part_with_no_list_moves_and_widens_by_a_size_and_names_the_axis_as_its_source() -> None:
    parts = {
        "b": box(
            x={"by": ":device", "desktop": "=@space.4", "phone": "=@space.1"},
            width={"by": ":device", "desktop": "=:width * 0.5", "phone": "=:width"},
        )
    }
    components = lab(top=top(parts))

    desktop = drawn(components=components)
    phone = drawn(mode="phone", components=components)

    assert desktop.findings == phone.findings == []
    assert frame(desktop, "top/b")[:3] == (32.0, 0.0, 320.0)
    assert frame(phone, "top/b")[:3] == (4.0, 0.0, 640.0)
    element = phone.scene.find("top/b")
    assert element is not None
    assert element.sources["x"] == element.sources["width"] == "size:device"


def test_a_lists_settings_follow_a_size() -> None:
    settings = {
        "gap": {"by": ":device", "desktop": "=@space.2", "phone": "=@space.1"},
        "justify-content": {"by": ":device", "desktop": "end", "phone": "start"},
    }
    parts = {"across": {"repeat": "items", "draw": "lab/item", "width": "=:width", "row": settings}}
    components = lab(top=top(parts, fields=LISTED), item=item())

    desktop = drawn(ITEMS, components=components)
    phone = drawn(ITEMS, mode="phone", components=components)

    assert desktop.findings == phone.findings == []
    # Three items of 32 px: on a desktop at the row's end, 8 px apart; on a phone at its
    # start, 4 px apart.
    assert [frame(desktop, f"top/across[{i}]")[0] for i in "abc"] == [528.0, 568.0, 608.0]
    assert [frame(phone, f"top/across[{i}]")[0] for i in "abc"] == [0.0, 36.0, 72.0]


def test_a_size_reaches_a_component_placed_by_another_at_any_depth() -> None:
    deep = block(
        {
            "b": box(x={"by": ":device", "desktop": "=@space.4", "phone": "=@space.1"}),
            "tag": {
                "text": {
                    "content": "tag",
                    "style": "type.body",
                    "fill": {"by": "tone", "plain": "text-primary", "loud": "accent"},
                    "text-anchor": {"by": ":device", "desktop": "end", "phone": "start"},
                },
                "width": "=:width",
            },
        },
        fields={"tag": {"type": "string"}},
        options={"tone": ["plain", "loud"]},
    )
    inner = block(
        {
            "deep": {
                "use": "lab/deep",
                "fields": {"tag": "tag"},
                "options": {"tone": {"by": ":device", "desktop": "plain", "phone": "loud"}},
                "width": "=:width",
            }
        },
        fields={"tag": {"type": "string"}},
    )
    outer = top(
        {"inner": {"use": "lab/inner", "fields": {"tag": "tag"}, "width": "=:width"}},
        fields={"tag": {"type": "string"}},
    )
    components = lab(top=outer, inner=inner, deep=deep)

    desktop = drawn({"tag": "Hi"}, components=components)
    phone = drawn({"tag": "Hi"}, mode="phone", components=components)

    assert desktop.findings == phone.findings == []
    assert frame(desktop, "top/inner/deep/b")[0] == 32.0
    assert frame(phone, "top/inner/deep/b")[0] == 4.0
    group = phone.scene.find("top/inner/deep")
    assert group is not None
    assert group.properties["options"] == {"tone": "loud"}
    assert group.sources["options.tone"] == "size:device"
    tag = phone.scene.find("top/inner/deep/tag")
    assert tag is not None
    assert tag.properties["text-anchor"] == "start"
    assert tag.sources["text-anchor"] == "size:device"
    [[run]] = tag.properties["paragraphs"]
    assert run["fill"] == "accent"


def test_a_size_reaches_a_value_and_the_size_a_component_asks_for() -> None:
    component = top(
        {"b": box(width="=pad")},
        values={"pad": {"by": ":device", "desktop": "=@space.4", "phone": "=@space.1"}},
        preferred={
            "width": {"by": ":device", "desktop": "=@size.figure", "phone": "=@space.4 * 10"},
            "height": "=@space.4",
        },
    )

    desktop = drawn(components=lab(top=component))
    phone = drawn(mode="phone", components=lab(top=component))

    assert desktop.findings == phone.findings == []
    assert frame(desktop, "top/b")[2] == 32.0
    assert frame(phone, "top/b")[2] == 4.0
    root = phone.scene.find("top")
    assert root is not None
    assert root.properties["width"] == 320.0
    assert root.sources["width"] == "size:device"


# --- what is refused when a component is read (point 7) -------------------------------------


@pytest.mark.parametrize(
    ("value", "said"),
    [
        pytest.param(
            {"by": ":colour-scheme", "light": "=@space.1", "dark": "=@space.2"},
            "switches on `:colour-scheme`, which reads no size axis a piece can name "
            "(the size axes: `:device`)",
            id="a-value-axis",
        ),
        pytest.param(
            {"by": ":width", "desktop": "=@space.1"},
            "switches on `:width`, which reads no size axis a piece can name",
            id="a-name-the-engine-holds",
        ),
        pytest.param(
            {"by": ":device", "phone": "=@space.1"},
            "the switch on `:device` names no branch for `desktop`, the axis's default",
            id="no-default",
        ),
        pytest.param(
            {"by": ":device", "desktop": "=@space.1", "watch": "=@space.2"},
            "the switch on `:device` names `watch`, which is no mode of the axis (its modes: "
            "desktop, tablet, phone)",
            id="a-mode-the-axis-lacks",
        ),
    ],
)
def test_a_switch_by_a_marked_name_reads_a_size_axis_and_names_its_modes(
    value: dict[str, Any], said: str
) -> None:
    result = drawn(components=lab(top=top({"b": box(width=value)})))

    [found] = [f for f in result.findings if f.code == "size-switch"]
    assert said in found.message
    assert found.extra == {"component": "lab/top"}
    assert found.where.startswith("parts.b.width")


def test_a_context_that_knows_no_size_axis_refuses_a_switch_by_a_size() -> None:
    result = drawn(
        axes={}, components=lab(top=top({"b": box(x={"by": ":device", "desktop": "=@space.1"})}))
    )

    [message] = issues(result, "size-switch")
    assert "(the size axes: none)" in message
    assert frame(result, "top/b")[0] == 0.0


@pytest.mark.parametrize(
    ("when", "code", "said"),
    [
        pytest.param(
            {"by": ":device", "phone": True},
            "size-switch",
            "names no branch for `desktop`",
            id="no-default",
        ),
        pytest.param(
            {"by": ":device", "desktop": {"by": ":device", "desktop": True}},
            "component-shape",
            "a branch of a `when` by a size takes `true`, `false`, a field, or",
            id="a-switch-again",
        ),
        pytest.param(
            {"by": ":contrast", "standard": True},
            "size-switch",
            "`when` switches on `:contrast`, which reads no size axis",
            id="a-value-axis",
        ),
    ],
)
def test_a_when_by_a_size_names_the_default_and_switches_no_further(
    when: dict[str, Any], code: str, said: str
) -> None:
    result = drawn(components=lab(top=top({"b": {**box(), "when": when}})))

    assert any(said in message for message in issues(result, code)), result.findings


@pytest.mark.parametrize(
    ("down", "said"),
    [
        pytest.param(ON_DESKTOP, "at `desktop` of `device` 2 of their `when`s say yes", id="twice"),
        pytest.param(
            # `down` says no at every mode, and `across` says no on a phone.
            {"by": ":device", "desktop": False},
            "at `phone` of `device` 0 of their `when`s say yes",
            id="never",
        ),
    ],
)
def test_two_parts_over_one_list_draw_each_item_once_at_every_mode(
    down: dict[str, Any], said: str
) -> None:
    """Each part is judged at every mode of the axis, a mode neither names included."""
    parts = {"down": {"repeat": "items", "draw": "lab/item", "when": down, "column": {}}}

    result = drawn(ITEMS, components=flipping(**parts))

    [message] = issues(result, "size-repeat")
    assert said in message
    assert "the parts `across`, `down` repeat over `items`" in message


def test_two_parts_over_one_list_that_each_draw_by_a_field_are_not_judged() -> None:
    """Only `when`s that say yes or no in every branch are judged: a branch that gives a
    `when` of its own depends on the content."""
    head = {"by": ":device", "desktop": "head", "phone": False}
    components = flipping(down={"repeat": "items", "draw": "lab/item", "when": head, "column": {}})
    components["lab/top"]["fields"]["properties"]["head"] = {"type": "string"}

    assert issues(drawn(ITEMS, components=components), "size-repeat") == []


def test_a_component_that_names_no_size_draws_as_it_did() -> None:
    """A size axis a component does not read changes no byte of its scene."""
    components = lab(top=top({"b": box(x="=@space.1")}, fields=LISTED))
    alone = drawn(axes={}, components=components)
    on_a_phone = drawn(mode="phone", components=components)

    assert on_a_phone.scene.to_dict() | {"size-key": "default"} == alone.scene.to_dict()
    assert on_a_phone.findings == alone.findings == []


# --- a tie whose end a size hides (points 4 and 5) --------------------------------------------


def arrow() -> dict[str, Any]:
    """A component that takes ends and draws a straight connector between them."""
    return block({"l": {"line": {"stroke": "line"}, "connect": "straight"}}, ends=True)


def tied(steps: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """A top that draws its `steps` by the parts `steps` gives, and each tie of its `links`
    from its `from` to its `to`."""
    parts = {**steps, "links": {"repeat": "links", "draw": "lab/arrow"}}
    fields = {"steps": LISTED["items"], "links": LISTED["items"]}
    lists = {"links": {"ends": ["from", "to"]}}
    return lab(top=top(parts, fields=fields, lists=lists), item=item(), arrow=arrow())


#: Two steps, and a tie from the first to the second.
TIED = {
    "steps": [{"id": "a"}, {"id": "b"}],
    "links": [{"id": "ab", "from": {"item": "steps[a]"}, "to": {"item": "steps[b]"}}],
}


def test_a_tie_between_items_two_parts_draw_is_found_at_each_size() -> None:
    steps = {
        "across": {"repeat": "steps", "draw": "lab/item", "when": ON_DESKTOP, "row": {}},
        "down": {"repeat": "steps", "draw": "lab/item", "when": ON_PHONE, "column": {}},
    }
    desktop = drawn(TIED, components=tied(steps))
    phone = drawn(TIED, mode="phone", components=tied(steps))

    assert desktop.findings == phone.findings == []
    across, down = desktop.scene.find("top/links[ab]/l"), phone.scene.find("top/links[ab]/l")
    assert across is not None and down is not None
    assert across.properties["attached"]["end"]["id"] == "top/across[b]"
    assert down.properties["attached"]["end"]["id"] == "top/down[b]"
    assert across.properties["y1"] == across.properties["y2"]
    assert down.properties["x1"] == down.properties["x2"]


def test_a_tie_whose_end_a_size_hides_is_left_out_and_reported_there() -> None:
    steps = {"across": {"repeat": "steps", "draw": "lab/item", "when": ON_DESKTOP, "row": {}}}
    desktop = drawn(TIED, components=tied(steps))
    phone = drawn(TIED, mode="phone", components=tied(steps))

    assert desktop.findings == []
    assert desktop.scene.find("top/links[ab]") is not None
    assert phone.scene.find("top/links[ab]") is None
    assert [(f.code, f.where) for f in phone.findings] == [
        ("end-not-found", "links[ab].from"),
        ("end-not-found", "links[ab].to"),
    ]
    assert "is drawn nowhere below `top`" in phone.findings[0].message
