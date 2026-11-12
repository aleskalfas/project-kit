"""A concept's sign on an item (visual-communication DEC-036 points 1, 2, 4, 5 and 7): the
outline a sign is, the shapes the foundations declare and the icons a notation holds, the
sign part a component places, the path the scene holds, and how each renderer draws it.

- **An outline** is read from SVG's path data whole, every command absolute or relative,
  and held as moves, lines, cubic curves and closes, which the engine maps into a frame by
  its square, whole, centred and as large as the frame allows. What is no outline is said.
- **The foundations** declare each shape by its name; another library declares none.
- **A notation** holds each concept's icon, or maps it to a shape. Its sign is its icon,
  else its shape. A sign that cannot be read is a finding in the notation, and the concept
  keeps its colour family.
- **A sign part** draws the sign of the concept whose family its instance takes: its own,
  or the one of the instance it sits in where it takes its family from that. Where there is
  none, it is not drawn, at zero size. A state changes its paint, never its sign, and an
  override reaches its fill.
- **The path** each renderer draws: SVG and HTML as a `<path>`, PDF from its outline, each
  filled by its rule. Under forced colours the HTML page gives it what any shape takes, and
  it holds no text, so it takes no place in what a reader's tools read.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import pytest

from tests.in_process import load
from tests.test_visual_communication_html import draw as draw_html
from tests.test_visual_communication_html import forced, marked
from tests.test_visual_communication_pdf import OPENING, page_of
from tests.test_visual_communication_pdf import draw as draw_pdf
from tests.test_visual_communication_svg import draw as draw_svg
from tests.test_visual_communication_svg import element, scene
from tests.visual_communication_project import FOUNDATIONS, bound, write, yaml_text
from tests.visual_engine import FakeEnv, block, codes, draw, frame, layout, top

outlines, tokens, notations, files, checks, seam = load(
    "visual-communication", "outlines", "tokens", "notations", "files", "checks", "plugins.seam"
)
svg_declaration, html_declaration, pdf_declaration = load(
    "visual-communication",
    "plugins.svg_declaration",
    "plugins.html_declaration",
    "plugins.pdf_declaration",
)


def outline(d: str, fill_rule: str = "nonzero", square: float = 10) -> Any:
    """The outline `d` gives, read; the test fails where it gives none."""
    read = outlines.read_outline({"d": d, "fill-rule": fill_rule, "square": square})
    assert isinstance(read, outlines.Outline), read
    return read


def as_written(d: str, square: float = 10) -> str:
    """The path data `d` gives, mapped onto its own square: as the engine holds it."""
    return outline(d, square=square).mapped(0, 0, square, square)


# --- an outline ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("given", "held"),
    [
        ("M0 0L10 0 10 10z", "M 0 0 L 10 0 L 10 10 Z"),
        ("m1 1h4v4h-4z", "M 1 1 L 5 1 L 5 5 L 1 5 Z"),
        ("M1,1 L2,2 l1-1.5", "M 1 1 L 2 2 L 3 0.5"),
        ("M0 0 1 1 2 0", "M 0 0 L 1 1 L 2 0"),
        ("m1 1 1 1", "M 1 1 L 2 2"),
        ("M0 0C1 1 2 2 3 3S5 5 6 6", "M 0 0 C 1 1 2 2 3 3 C 4 4 5 5 6 6"),
        ("M0 0S2 2 3 3", "M 0 0 C 0 0 2 2 3 3"),
        ("M0 0c1 1 2 2 3 3s2 2 3 3", "M 0 0 C 1 1 2 2 3 3 C 4 4 5 5 6 6"),
        ("M0 0Q3 6 6 0T12 0", "M 0 0 C 2 4 4 4 6 0 C 8 -4 10 -4 12 0"),
        ("M0 0q3 6 6 0t6 0", "M 0 0 C 2 4 4 4 6 0 C 8 -4 10 -4 12 0"),
        ("M0 5a5 5 0 0 1 10 0", "M 0 5 C 0 2.24 2.24 0 5 0 C 7.76 0 10 2.24 10 5"),
        ("M0 5a5 5 0 0110 0", "M 0 5 C 0 2.24 2.24 0 5 0 C 7.76 0 10 2.24 10 5"),
        ("M0 5A5 5 0 0 0 10 5", "M 0 5 C 0 7.76 2.24 10 5 10 C 7.76 10 10 7.76 10 5"),
        ("M0 5A1 1 0 0 1 10 5", "M 0 5 C 0 2.24 2.24 0 5 0 C 7.76 0 10 2.24 10 5"),
        ("M0 0A0 5 0 0 1 10 0", "M 0 0 L 10 0"),
        ("M0 0A5 5 0 0 1 0 0", "M 0 0"),
        ("M0 0H5V5ZL5 0", "M 0 0 L 5 0 L 5 5 Z M 0 0 L 5 0"),
        ("M1 1H5Zm1 1h1z", "M 1 1 L 5 1 Z M 2 2 L 3 2 Z"),
        (" M 0 0 L .5e1 1E0 ", "M 0 0 L 5 1"),
    ],
)
def test_path_data_is_read_whole_as_moves_lines_cubic_curves_and_closes(
    given: str, held: str
) -> None:
    assert as_written(given) == held


@pytest.mark.parametrize(
    ("raw", "said"),
    [
        ("M 0 0", "is not `{d: <path data>, fill-rule: nonzero | evenodd, square: <side>}`"),
        ({"d": "M 0 0", "square": 10}, "is not `{d: <path data>"),
        ({"d": "M 0 0", "fill-rule": "nonzero", "square": 10, "x": 1}, "is not `{d:"),
        ({"d": "M 0 0", "fill-rule": "winding", "square": 10}, "the fill rule `winding`"),
        ({"d": "M 0 0", "fill-rule": "evenodd", "square": 0}, "the square `0`"),
        ({"d": "M 0 0", "fill-rule": "evenodd", "square": True}, "the square `True`"),
        ({"d": 12, "fill-rule": "evenodd", "square": 10}, "no text of path data"),
        ({"d": "", "fill-rule": "nonzero", "square": 10}, "it is empty"),
        ({"d": "L 0 0", "fill-rule": "nonzero", "square": 10}, "does not start with a move"),
        ({"d": "M 0 0 X 1 1", "fill-rule": "nonzero", "square": 10}, "no command at character 7"),
        ({"d": "M 0 0 L 1", "fill-rule": "nonzero", "square": 10}, "no number at character 10"),
        ({"d": "M 0 0 L, 1 1", "fill-rule": "nonzero", "square": 10}, "no number at character 8"),
        ({"d": "M 0 0 Z 1 1", "fill-rule": "nonzero", "square": 10}, "no command at character 9"),
        (
            {"d": "M 0 0 A 1 1 0 2 0 5 5", "fill-rule": "nonzero", "square": 10},
            "no flag, 0 or 1, at character 15",
        ),
    ],
)
def test_what_is_no_outline_is_said(raw: Any, said: str) -> None:
    problem = outlines.read_outline(raw)
    assert isinstance(problem, str)
    assert said in problem


def test_an_outline_is_fitted_by_its_square_whole_centred_and_as_large_as_its_frame_allows() -> (
    None
):
    square = outline("M 0 0 H 10 V 10 H 0 Z")
    assert square.mapped(4, 4, 16, 8) == "M 8 4 L 16 4 L 16 12 L 8 12 Z"
    assert square.mapped(0, 10, 8, 16) == "M 0 14 L 8 14 L 8 22 L 0 22 Z"
    assert square.mapped(0, 0, 3, 3) == "M 0 0 L 3 0 L 3 3 L 0 3 Z"
    # Rounded as every length of the scene is, to 1/100 px, half away from zero.
    third = outline("M 0 0 L 1 1", square=3)
    assert third.mapped(0, 0, 1, 1) == "M 0 0 L 0.33 0.33"
    assert outline("M -1 0 L 0 0").mapped(0, 0, 0.001, 0.001) == "M 0 0 L 0 0"


# --- the foundations' shapes --------------------------------------------------------------------

#: The shapes the foundations being built declare.
SHAPES = ("circle", "square", "triangle", "diamond", "hexagon", "star")


def test_the_foundations_declare_each_shape_by_its_name_as_a_closed_outline_in_its_square() -> None:
    declared = tokens.read_declarations(FOUNDATIONS / "roles.yaml", library="foundations@1.1.0")
    assert tuple(declared.shapes) == SHAPES
    for name, shape in declared.shapes.items():
        assert shape.fill_rule == "nonzero", name
        assert shape.segments[0][0] == "M" and shape.segments[-1] == ("Z", ()), name
        numbers = [value for _, points in shape.segments for value in points]
        assert all(0 <= value <= shape.square for value in numbers), name
    assert tokens.Scope(declared).shapes == declared.shapes


def roles_file(tmp_path: Path, **declared: Any) -> Path:
    """A `roles.yaml` of one colour role, with `declared` beside it."""
    data = bound("roles", roles={"background": {"type": "color"}}, **declared)
    return write(tmp_path / "roles.yaml", yaml_text(data))


@pytest.mark.parametrize(
    ("shapes", "code", "where"),
    [
        ([], "shapes-shape", "shapes"),
        ({"blob": {"d": "L 0 0", "fill-rule": "nonzero", "square": 24}}, "shape-shape", "blob"),
        ({"blob": {"d": "M 0 0 Z", "square": 24}}, "shape-shape", "blob"),
        ({"Blob": {"d": "M 0 0 Z", "fill-rule": "nonzero", "square": 24}}, "shape-shape", "Blob"),
    ],
    ids=["no-mapping", "no-path-data", "no-fill-rule", "no-name"],
)
def test_a_shape_that_is_no_outline_refuses_the_foundations(
    tmp_path: Path, shapes: Any, code: str, where: str
) -> None:
    with pytest.raises(tokens.TokenError) as refused:
        tokens.read_declarations(roles_file(tmp_path, shapes=shapes))
    [found] = refused.value.findings
    assert (found.code, found.where.removeprefix("shapes.")) == (code, where)


def test_only_the_foundations_declare_shapes(tmp_path: Path) -> None:
    square = {"d": "M 0 0 H 1 V 1 Z", "fill-rule": "nonzero", "square": 1}
    data = bound("roles", roles={"parts.ink": {"type": "color"}}, shapes={"box": square})
    path = write(tmp_path / "roles.yaml", yaml_text(data))

    own = tokens.read_own_roles(path, name="parts")

    assert [(f.code, f.where) for f in own.findings] == [("roles-declaration", "shapes")]
    assert "only the foundations declare the shapes" in own.findings[0].message
    assert own.shapes == {}


# --- a notation's icons and the shapes it maps a concept to -------------------------------------

#: The shapes the foundations declare in these tests.
DECLARED = {"square": outline("M 0 0 H 10 V 10 H 0 Z"), "star": outline("M 5 0 L 10 10 H 0 Z")}

#: An icon a notation holds: a ring, filled by the even-odd rule.
RING = {
    "d": "M 0 5 A 5 5 0 1 0 10 5 A 5 5 0 1 0 0 5 Z M 3 5 A 2 2 0 1 0 7 5 A 2 2 0 1 0 3 5 Z",
    "fill-rule": "evenodd",
    "square": 10,
}


def notation(tmp_path: Path, **concepts: Any) -> Any:
    """The notation `sys@1.0.0` holding `concepts`, read against the families `blue` and
    `red` and the shapes `DECLARED`."""
    folder = tmp_path / "sys" / "1.0.0"
    library = bound("library", name="sys", version="1.0.0", kind="notation")
    write(folder / "library.yaml", yaml_text(library))
    write(folder / "notation.yaml", yaml_text(bound("notation", concepts=concepts)))
    return notations.read_notation(folder, ("blue", "red"), shapes=DECLARED)


def test_a_concept_s_sign_is_its_icon_else_its_shape_and_none_where_it_maps_neither(
    tmp_path: Path,
) -> None:
    read = notation(
        tmp_path,
        user={"colour": "red", "icon": RING},
        store={"colour": "blue", "shape": "square"},
        both={"colour": "blue", "icon": RING, "shape": "star"},
        plain={"colour": "blue"},
    )

    assert [(f.code, f.level, f.where) for f in read.findings] == [
        ("concept-unsigned", "attention", "concepts.plain")
    ]
    ring = outlines.read_outline(RING)
    assert read.sign("user") == ring
    assert read.sign("store") == DECLARED["square"]
    assert read.sign("both") == ring
    assert read.sign("plain") is None
    assert read.family("both") == "blue"
    with pytest.raises(KeyError):
        read.sign("queue")


def test_a_sign_that_cannot_be_read_fails_in_the_notation_and_the_concept_keeps_its_colour(
    tmp_path: Path,
) -> None:
    read = notation(
        tmp_path,
        user={"colour": "red", "icon": {**RING, "fill-rule": "winding"}},
        store={"colour": "blue", "shape": "circle"},
        other={"colour": "blue", "label": "Other"},
    )

    found = [(f.code, f.where, f.message) for f in read.findings]
    assert found == [
        (
            "concept-shape",
            "concepts.user.icon",
            "the icon of the concept `user` has the fill rule `winding`, which is neither "
            "`nonzero` nor `evenodd`",
        ),
        (
            "concept-shape",
            "concepts.store.shape",
            "the concept `store` maps to the shape `circle`, which the foundations do not "
            "declare: `square`, `star`",
        ),
        (
            "concept-shape",
            "concepts.other",
            "the concept `other` is not `{colour: <family>}`, with its `icon` or a `shape` "
            "beside: a concept maps to a colour family the foundations declare, never to a "
            "value",
        ),
    ]
    assert (read.family("user"), read.sign("user")) == ("red", None)
    assert (read.family("store"), read.sign("store")) == ("blue", None)
    assert read.family("other") is None and read.sign("other") is None


# --- the sign part ------------------------------------------------------------------------------

#: The families of these tests: each member to a colour role.
FAMILIES = {
    "blue": {"fill": "surface", "line": "border"},
    "red": {"fill": "accent", "line": "ink"},
}

#: The concepts the piece's notations hold, each to its family, or to None where its
#: notation cannot read it, and the sign of each that has one.
CONCEPTS = {"sys/store": "blue", "sys/user": "red", "sys/plain": "blue", "sys/lost": None}
SIGNS = {"sys/store": DECLARED["square"], "sys/user": outlines.read_outline(RING)}

#: A sign in a card's corner, painted from its family's line, and a box placed after it.
MARK = {
    "mark": {
        "sign": {"fill": ":colour.line", "stroke": "shade", "stroke-width": "=@stroke.thin"},
        "x": "=@space.1",
        "y": "=@space.1",
        "width": "=@space.3",
        "height": "=@space.2",
    },
    "after": {
        "box": {"fill": "surface"},
        "x": "=mark.right",
        "y": "=mark.bottom",
        "width": "=@space.1",
        "height": "=@space.1",
    },
}

#: The square's path in the mark's frame, 16 by 8 at 4, 4: 8 px a side, in its middle.
SQUARE_IN_MARK = "M 8 4 L 16 4 L 16 12 L 8 12 Z"


def lab(**components: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {f"lab/{name}": component for name, component in components.items()}


def cards(*items: dict[str, Any]) -> Any:
    """The scene of cards a `repeat` part of colour `blue` draws over `items`, each card's
    sign in its corner."""
    parts = {"items": {"repeat": "items", "draw": "lab/card", "colour": "blue", "column": {}}}
    fields = {"items": {"type": "array", "items": {"type": "object"}}}
    card = block(MARK, states={"marked": {"colour": "red"}, "quiet": {}})
    components = lab(top=top(parts, fields=fields), card=card)
    return draw(
        {"items": list(items)},
        components=components,
        families=FAMILIES,
        concepts=CONCEPTS,
        signs=SIGNS,
    )


def path_of(result: Any, trace: str) -> tuple[dict[str, Any], dict[str, str]]:
    found = result.scene.find(trace)
    assert found is not None, f"no element {trace}"
    assert found.type == "path"
    return found.properties, found.sources


def test_a_sign_part_draws_the_sign_of_the_concept_its_instance_names_as_a_path() -> None:
    result = cards({"id": "store", "concept": "sys/store"}, {"id": "user", "concept": "sys/user"})

    assert result.findings == []
    store, sources = path_of(result, "top/items[store]/mark")
    assert store == {
        "x": 4,
        "y": 4,
        "width": 16,
        "height": 8,
        "d": SQUARE_IN_MARK,
        "fill-rule": "nonzero",
        "fill": "border",
        "stroke": "shade",
        "stroke-width": 1,
    }
    concept = "content:items[store].concept"
    assert (sources["d"], sources["fill-rule"], sources["fill"]) == (concept, concept, concept)
    user, _ = path_of(result, "top/items[user]/mark")
    assert (user["fill"], user["fill-rule"]) == ("ink", "evenodd")
    assert user["d"].startswith("M 8 8 C 8 10.21 9.79 12 12 12 C ")


def test_where_there_is_no_sign_the_part_is_not_drawn_and_has_zero_size_at_its_place() -> None:
    """A card whose family comes from its place in the list, one whose concept maps no sign,
    and one whose concept its notation cannot read."""
    result = cards(
        {"id": "placed"},
        {"id": "plain", "concept": "sys/plain"},
        {"id": "lost", "concept": "sys/lost"},
    )

    assert result.findings == []
    for item in ("placed", "plain", "lost"):
        assert result.scene.find(f"top/items[{item}]/mark") is None
        assert frame(result, f"top/items[{item}]/after")[:2] == (4, 4)


def test_a_state_changes_the_sign_s_paint_and_never_its_sign_and_an_override_reaches_it() -> None:
    result = cards(
        {"id": "marked", "concept": "sys/store", "state": "marked"},
        {"id": "quiet", "concept": "sys/store", "state": "quiet"},
        {"id": "pointed", "concept": "sys/store", "override": {"mark": "accent"}},
    )

    assert result.findings == []
    marked_, sources = path_of(result, "top/items[marked]/mark")
    assert (marked_["d"], marked_["fill"]) == (SQUARE_IN_MARK, "ink")
    assert (sources["d"], sources["fill"]) == (
        "content:items[marked].concept",
        "content:items[marked].state",
    )
    quiet, _ = path_of(result, "top/items[quiet]/mark")
    assert (quiet["d"], quiet["fill"]) == (SQUARE_IN_MARK, "border")
    pointed, sources = path_of(result, "top/items[pointed]/mark")
    assert (pointed["fill"], sources["fill"]) == ("accent", "content:items[pointed].override.mark")
    assert pointed["stroke"] == "shade"


def nested(badge: dict[str, Any], body: dict[str, Any]) -> Any:
    """The scene of a holder the content places, which places `badge`, drawing its sign."""
    holder = block({"badge": {"use": "lab/badge"}})
    slot = top({"s": {"slot": "body"}}, fields={"body": {"type": "object"}})
    components = lab(top=slot, holder=holder, badge=badge)
    return draw(
        {"body": body}, components=components, families=FAMILIES, concepts=CONCEPTS, signs=SIGNS
    )


def test_a_sign_part_draws_the_sign_of_the_instance_it_sits_in_where_it_takes_its_family() -> None:
    inherited = nested(block(MARK), {"use": "lab/holder", "concept": "sys/store"})
    own_colour = nested(block(MARK, colour="red"), {"use": "lab/holder", "concept": "sys/store"})

    assert inherited.findings == own_colour.findings == []
    drawn, sources = path_of(inherited, "top/s/badge/mark")
    assert (drawn["d"], drawn["fill"]) == (SQUARE_IN_MARK, "border")
    assert sources["d"] == "content:body.concept"
    assert own_colour.scene.find("top/s/badge/mark") is None


def test_a_sign_part_takes_a_box_s_paints_and_size_and_exposes_nothing() -> None:
    def issues(part: dict[str, Any], **parts: Any) -> list[str]:
        component = block({"mark": part, **parts})
        found = layout.Component("lab/x", component, layout.Context(FakeEnv(), "en")).issues
        return [message.removeprefix("lab/x: ") for _, _, message in found]

    sized = {"width": "=@space.1", "height": "=@space.1"}
    assert issues({"sign": {"fill": "surface"}, **sized}) == []
    assert issues({"sign": {"rx": 2}, **sized}) == ["the sign `mark` takes no property `rx`"]
    assert issues({"sign": {}, "width": "=@space.1"}) == ["the sign `mark` needs `height`"]
    reader = {"box": {"fill": "surface"}, "width": "=mark.dot.width", "height": "=@space.1"}
    said = issues({"sign": {}, **sized}, reader=reader)
    assert any("the sign `mark` exposes nothing" in each for each in said)


def test_a_component_with_a_sign_part_holds_the_schema() -> None:
    part = {"sign": {"fill": ":colour.line"}, "width": "=@space.1", "height": "=@space.1"}
    component = bound("component", **block({"mark": part}))
    assert files.shape_problems(component, "component") == []
    wrong = bound("component", **block({"mark": {**part, "sign": {"rx": 1}}}))
    assert files.shape_problems(wrong, "component") != []


def test_a_concept_the_notations_do_not_hold_is_one_finding_and_draws_no_sign() -> None:
    """A concept the notations do not hold is the content's finding, once, at the item: the
    sign part adds none, and draws nothing."""
    result = cards({"id": "a", "concept": "other/store"})

    assert codes(result) == ["unknown-concept"]
    assert result.scene.find("top/items[a]/mark") is None


# --- the path each renderer draws ---------------------------------------------------------------

#: A path the engine mapped: a square, 8 px a side, filled and stroked.
PATH = element(
    "path",
    "figure/sign",
    x=4,
    y=4,
    width=16,
    height=8,
    d=SQUARE_IN_MARK,
    **{"fill-rule": "nonzero", "stroke-width": 2},
    fill="surface",
    stroke="border",
)

#: The same path, filled by the even-odd rule, with no stroke.
EVEN_ODD = element(
    "path", "figure/ring", x=4, y=4, width=16, height=8, d=SQUARE_IN_MARK, fill="surface",
    **{"fill-rule": "evenodd"},
)  # fmt: skip

#: A path that holds no outline, which no engine writes.
EMPTY = element("path", "figure/empty", x=0, y=0, width=8, height=8, fill="surface")


def test_each_renderer_declares_the_path_and_every_property_the_scene_holds() -> None:
    held = {"x", "y", "width", "height", "d", "fill-rule", "fill", "stroke", "stroke-width"}
    for declaration in (svg_declaration, html_declaration, pdf_declaration):
        drawn = declaration.DECLARATION
        assert set(drawn["draws"]["path"]) == held
        assert drawn["seam"] == seam.SEAM_VERSION == 8
        assert checks.losses(scene(PATH, EVEN_ODD), drawn) == []


def test_the_svg_renderer_draws_a_path_filled_by_its_rule_and_refuses_one_with_no_outline() -> None:
    drawn = draw_svg(scene(PATH, EVEN_ODD, EMPTY))

    [page] = drawn.pages
    assert (
        '<path data-id="figure/sign" d="M 8 4 L 16 4 L 16 12 L 8 12 Z" fill="#ffffff" '
        'stroke="#808080" stroke-width="2"/>'
        '<path data-id="figure/ring" d="M 8 4 L 16 4 L 16 12 L 8 12 Z" fill-rule="evenodd" '
        'fill="#ffffff"/>'
        "</g>"
    ) in page.svg
    assert [(loss.what, loss.did, loss.why) for loss in drawn.losses] == [
        ("figure/empty", seam.REFUSED, "the path holds no outline, `d`")
    ]


def test_the_pdf_renderer_draws_a_path_from_its_outline_filled_by_its_rule() -> None:
    drawn = draw_pdf(scene(PATH, EVEN_ODD, EMPTY))

    file, page = page_of(drawn)
    square = "8 4 m\n16 4 l\n16 12 l\n8 12 l\nh\n"
    assert file.content(page) == (
        OPENING + f"q 1 1 1 rg 0.5 0.5 0.5 RG 2 w\n{square}B\nQ\n" + f"q 1 1 1 rg\n{square}f*\nQ\n"
    )
    assert [(loss.what, loss.did) for loss in drawn.losses] == [("figure/empty", seam.REFUSED)]


def test_the_html_page_draws_a_path_in_a_layer_and_forced_colours_reach_its_paints() -> None:
    """A path is a shape like any other: it lies in a layer, holds no text, and under forced
    colours its fill takes the ground, with an edge where it has no stroke, and its stroke
    the text colour, as the declaration names (DEC-036 points 4 and 5)."""
    root = ElementTree.fromstring(draw_html(scene(EVEN_ODD, PATH)).document)

    [layer] = marked(root, "layer")
    drawn = [node for node in layer.iter() if node.tag.endswith("path")]
    assert [node.get("data-id") for node in drawn] == ["figure/ring", "figure/sign"]
    assert (drawn[0].get("fill-rule"), drawn[0].get("fill")) == ("evenodd", "var(--surface)")
    assert drawn[1].get("stroke") == "var(--border)"
    assert marked(root, "text") == []
    assert forced(root) == (
        "[data-layer] [stroke]{stroke:CanvasText}"
        "marker path{fill:CanvasText}"
        '[data-layer] [fill="var(--surface)"]{fill:Canvas}'
        '[data-layer] [fill="var(--surface)"]:not([stroke]){stroke:CanvasText;stroke-width:1px}'
    )
