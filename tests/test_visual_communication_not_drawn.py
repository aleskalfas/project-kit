"""What no element draws is kept in one list, and no renderer declares it drawn
(visual-communication DEC-078).

- **One list** (points 1 and 2). The comparison that finds a renderer's losses before it
  runs holds each property no element draws, with the types it may stand on, and passes
  over each on an element of those types. It passes over the tree, an element's type and a
  group's children, as no property. A drawn property a declaration does not name, `page`
  among them, is still a loss, and a primitive it does not name is still refused.
- **No declaration says it draws one** (point 2), read from what each declaration the
  capability ships says of the property, not from whether it names it.
- **The page on components** names exactly the list's properties, each with its types.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from tests.in_process import load

checks, svg_declaration, pdf_declaration, html_declaration = load(
    "visual-communication",
    "checks",
    "plugins.svg_declaration",
    "plugins.pdf_declaration",
    "plugins.html_declaration",
)

CAPABILITY = Path(__file__).parents[1] / ".pkit" / "capabilities" / "visual-communication"

#: Each renderer's declaration the capability ships.
SHIPPED = (svg_declaration, pdf_declaration, html_declaration)

#: What a renderer declares of a property it draws (DEC-005 point 9).
DRAWS = "draws"

#: The frame every element holds, which every shipped declaration names for each type.
FRAME = {"x": 0, "y": 0, "width": 10, "height": 10}

#: A part's word that it lies over another on purpose, as the scene holds it (DEC-066
#: point 2).
LIES_OVER = {"ids": ["figure/a"], "library": "tests@1.0.0"}

#: What a placed component's group holds that no element draws, beside its trace id, its
#: sources and its word that it lies over another.
GROUP_ONLY = {
    "component": "tests/card",
    "version": "1.0.0",
    "options": {"tone": "calm"},
}


def element(kind: str, trace: str, **held: Any) -> dict[str, Any]:
    """An element of the type `kind` that holds its frame, its sources and `held`."""
    return {"type": kind, "id": trace, **FRAME, **held, "sources": {"x": "engine"}}


def scene(*children: dict[str, Any]) -> dict[str, Any]:
    """A scene of one page, the figure's group, holding `children`."""
    page = element("group", "figure", page=True, **GROUP_ONLY, children=list(children))
    return {"pages": ["figure"], "children": [page]}


def drops(declaration: dict[str, Any], **gone: tuple[str, ...]) -> dict[str, Any]:
    """`declaration` without the properties `gone` names for each type, an empty tuple
    taking the type's whole entry away."""
    draws = {
        kind: {prop: said for prop, said in props.items() if prop not in gone.get(kind, ())}
        for kind, props in declaration["draws"].items()
        if gone.get(kind) != ()
    }
    return {**declaration, "draws": draws}


# --- one list -----------------------------------------------------------------------------------


def test_what_no_element_draws_on_a_group_and_on_each_type_gives_no_loss() -> None:
    """A group that holds a component, its version and its options, and an element of each
    type that holds `lies-over`, give no loss under any renderer the capability ships."""
    for declared in SHIPPED:
        kinds = declared.DECLARATION["draws"]
        children = [element(kind, f"figure/{kind}", **{"lies-over": LIES_OVER}) for kind in kinds]
        held = scene(*children)
        held["children"][0]["lies-over"] = LIES_OVER
        assert checks.losses(held, declared.DECLARATION) == [], declared.DECLARATION["name"]


def test_a_drawn_property_left_unnamed_is_still_lost_and_a_primitive_still_refused() -> None:
    """Taken out of a declaration, a group's `page` and a box's `fill` are each left out,
    and an ellipse is refused. What no element draws gives no loss beside them."""
    for declared in SHIPPED:
        name = declared.DECLARATION["name"]
        narrowed = drops(declared.DECLARATION, group=("page",), box=("fill",), ellipse=())
        held = scene(
            element("box", "figure/back", fill="paper", **{"lies-over": LIES_OVER}),
            element("ellipse", "figure/dot"),
        )
        lost = [loss.as_dict() for loss in checks.losses(held, narrowed)]
        assert lost == [
            {
                "plugin": name,
                "what": "figure",
                "did": "left-out",
                "why": f"the {name} renderer draws no `page` of a group",
            },
            {
                "plugin": name,
                "what": "figure/back",
                "did": "left-out",
                "why": f"the {name} renderer draws no `fill` of a box",
            },
            {
                "plugin": name,
                "what": "figure/dot",
                "did": "refused",
                "why": f"the {name} renderer draws no `ellipse`",
            },
        ]


def test_a_name_the_list_holds_for_a_group_alone_is_a_drawn_property_of_another_type() -> None:
    """The list names types, so `version` on a box is compared as any drawn property."""
    held = scene(element("box", "figure/back", version="2"))
    [lost] = checks.losses(held, svg_declaration.DECLARATION)
    assert (lost.what, lost.did) == ("figure/back", "left-out")
    assert lost.why == "the svg renderer draws no `version` of a box"


def test_the_tree_is_read_and_judged_as_no_property() -> None:
    """An element's type and a group's children are the tree, which the list does not
    hold, and no declaration names them, yet neither is a loss."""
    assert "type" not in checks.NOT_DRAWN
    assert "children" not in checks.NOT_DRAWN
    framed = dict.fromkeys(FRAME, DRAWS)
    flat = {"name": "flat", "draws": {"group": framed, "box": framed}}
    held = scene(element("box", "figure/back"))
    held["children"][0].pop("page")
    assert checks.losses(held, flat) == []


# --- no declaration says it draws one -----------------------------------------------------------


def test_no_shipped_declaration_declares_that_its_renderer_draws_what_no_element_draws() -> None:
    """Read from what each declaration says of the property: it may name one as updated in
    place, recreated or read back, never as drawn (DEC-078 point 2)."""
    for declared in SHIPPED:
        for kind, props in declared.DECLARATION["draws"].items():
            for prop in checks.NOT_DRAWN:
                if checks.not_drawn(prop, kind):
                    assert props.get(prop) != DRAWS, (declared.DECLARATION["name"], kind, prop)


def test_each_shipped_declaration_draws_a_groups_page() -> None:
    for declared in SHIPPED:
        assert declared.DECLARATION["draws"]["group"]["page"] == DRAWS


# --- the page on components ---------------------------------------------------------------------

#: The header of the table of what no element draws, on the page on components.
_HEADER = "| Property | The types it may stand on |"

#: How the table names a property that may stand on every type.
_EVERY = "any type"


def _listed() -> dict[str, frozenset[str] | None]:
    """Each property the page on components lists as one no element draws, with the types
    it may stand on, `None` for every type."""
    lines = (CAPABILITY / "components.md").read_text(encoding="utf-8").splitlines()
    start = lines.index(_HEADER) + 2  # past the header and its rule
    found: dict[str, frozenset[str] | None] = {}
    for row in lines[start:]:
        if not row.startswith("|"):
            break
        prop, types = (cell.strip() for cell in row.strip("|").split("|"))
        name = prop.strip("`")
        assert name not in found, name
        found[name] = None if types == _EVERY else frozenset(re.findall(r"`([a-z]+)`", types))
    return found


def test_the_page_on_components_names_exactly_what_no_element_draws() -> None:
    assert _listed() == dict(checks.NOT_DRAWN)
