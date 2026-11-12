"""The checks of signs (visual-communication DEC-036 point 8, DEC-002 point 7).

- **A sign that cannot hold fails.** An icon in a notation, or a shape in the foundations,
  that is no closed outline within its square fails where it lies (`sign-outline`), and
  still draws. A shape the foundations do not declare fails in the notation, as before.
- **A sign drawn too faint fails at the piece** (`contrast-drawn`): a sign part's path holds
  where its fill or its stroke reaches WCAG's contrast for other marks against the fill
  under it, and a run's sign is measured in the run's paint where it lies on other fills
  than its text. A sign over a picture is not measured.
- **A concept left to its colour asks for attention**, never failing: once for each version
  of the component that draws it so, naming its owner, for an instance (`sign-missing`) and
  for a run (`run-sign-missing`); in the notation, for a concept that maps no sign
  (`concept-unsigned`); and at the piece, in each language, for two concepts whose signs
  are one outline (`sign-shared`). No finding judges two concepts that share a family.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load
from tests.test_visual_communication_run_signs import SAYS, said
from tests.test_visual_communication_signs import (
    CONCEPTS,
    FAMILIES,
    MARK,
    RING,
    SIGNS,
    lab,
    notation,
    outline,
    roles_file,
)
from tests.visual_communication_project import FOUNDATIONS
from tests.visual_engine import block, draw, top

outlines, tokens, checks, signs, findings = load(
    "visual-communication", "outlines", "tokens", "checks", "signs", "findings"
)


# --- an outline that cannot hold ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("d", "fault"),
    [
        ("M 0 0 H 10 V 10 H 0 Z", None),
        ("M 0 0 H 4 V 4 Z M 6 6", None),
        ("M 0 5 C 0 -1 10 -1 10 5 Z", None),
        ("M 0 0 H 10.005 V 10 H 0 Z", None),
        ("M 0 0 H 10 V 10 H 0", "does not close its part 1: it ends with no `Z`"),
        ("M 0 0 H 4 V 4 Z M 5 5 H 9 V 9", "does not close its part 2: it ends with no `Z`"),
        (
            "M 0 0 H 12 V 10 H 0 Z",
            "reaches outside its square of 10: it spans 0 to 12 across, 0 to 10 down",
        ),
        (
            "M 0 5 C 0 -5 10 -5 10 5 Z",
            "reaches outside its square of 10: it spans 0 to 10 across, -2.5 to 5 down",
        ),
    ],
    ids=[
        "closed",
        "a-move-that-draws-nothing",
        "control-points-outside-a-sweep-within",
        "within-what-rounding-adds",
        "open",
        "second-part-open",
        "a-line-outside",
        "a-curve-s-sweep-outside",
    ],
)
def test_an_outline_holds_where_each_part_closes_and_every_point_it_draws_lies_in_its_square(
    d: str, fault: str | None
) -> None:
    assert outline(d).fault() == fault


def test_an_arc_and_the_foundations_shapes_hold() -> None:
    assert outlines.read_outline(RING).fault() is None
    declared = tokens.read_declarations(FOUNDATIONS / "roles.yaml", library="foundations@1.1.0")
    assert declared.findings == ()


def test_two_outlines_are_one_where_they_draw_alike_fitted_into_one_square() -> None:
    small = outline("M 0 0 H 10 V 10 H 0 Z")
    large = outline("M 0 0 H 20 V 20 H 0 Z", square=20)
    assert small.form() == large.form()
    assert small.form() != outline("M 0 0 H 10 V 10 H 0 Z", fill_rule="evenodd").form()
    assert small.form() != outline("M 5 0 L 10 10 H 0 Z").form()


# --- in the notation and in the foundations -----------------------------------------------------


def test_an_icon_that_cannot_hold_fails_in_the_notation_and_still_draws(tmp_path: Path) -> None:
    opened = {"d": "M 0 0 H 10 V 10 H 0", "fill-rule": "nonzero", "square": 10}
    read = notation(tmp_path, user={"colour": "red", "icon": opened})

    [found] = read.findings
    assert (found.code, found.level, found.file, found.where, found.library) == (
        "sign-outline",
        "fails",
        "notation.yaml",
        "concepts.user.icon",
        "sys@1.0.0",
    )
    assert found.message == (
        "the icon of the concept `user` does not close its part 1: it ends with no `Z`"
    )
    assert found.fix == outlines.CLOSE_IT
    assert read.sign("user") == outline(opened["d"])


def test_a_concept_that_maps_no_sign_asks_its_owner_and_one_whose_shape_is_unknown_fails(
    tmp_path: Path,
) -> None:
    read = notation(
        tmp_path,
        plain={"colour": "blue"},
        store={"colour": "blue", "shape": "circle"},
    )

    unsigned, unknown = read.findings
    assert (unsigned.code, unsigned.level, unsigned.where, unsigned.who) == (
        "concept-unsigned",
        "attention",
        "concepts.plain",
        "the owner of `sys`",
    )
    assert unsigned.message == (
        "the concept `plain` maps no sign, neither an `icon` nor a `shape`, so a piece tells "
        "it apart by its colour alone"
    )
    assert (unknown.code, unknown.level, unknown.where) == (
        "concept-shape",
        "fails",
        "concepts.store.shape",
    )


@pytest.mark.parametrize(
    ("d", "said"),
    [
        ("M 0 0 H 24 V 24", "the shape `blob` does not close its part 1: it ends with no `Z`"),
        (
            "M 0 0 H 30 V 24 H 0 Z",
            "the shape `blob` reaches outside its square of 24: it spans 0 to 30 across, 0 to 24 "
            "down",
        ),
    ],
    ids=["open", "outside"],
)
def test_a_shape_that_cannot_hold_fails_in_the_foundations_and_refuses_nothing(
    tmp_path: Path, d: str, said: str
) -> None:
    shapes = {"blob": {"d": d, "fill-rule": "nonzero", "square": 24}}
    path = roles_file(tmp_path, shapes=shapes)

    declared = tokens.read_declarations(path, library="foundations@1.2.0", shown="roles.yaml")

    [found] = declared.findings
    assert (found.code, found.level, found.file, found.where, found.message) == (
        "sign-outline",
        "fails",
        "roles.yaml",
        "shapes.blob",
        said,
    )
    assert found.fix == outlines.CLOSE_IT
    assert "blob" in declared.shapes


# --- a sign drawn too faint ---------------------------------------------------------------------


def grey(level: float) -> dict[str, Any]:
    return {"colorSpace": "srgb", "components": [level, level, level], "alpha": 1}


#: The colour roles of these scenes: `paper` under everything, `faint` too light on it for a
#: sign, and `ink` dark enough.
COLOURS = {
    "paper": {"default": grey(1)},
    "faint": {"default": grey(0.8)},
    "ink": {"default": grey(0)},
    "shade": {"default": grey(0.4)},
    "border": {"default": grey(0.5)},
    "surface": {"default": grey(0.55)},
}


def box(name: str, width: float, height: float) -> dict[str, Any]:
    return {"type": "box", "id": f"top/{name}", "x": 0, "y": 0, "width": width, "height": height}


def under(scene: dict[str, Any], *elements: dict[str, Any]) -> dict[str, Any]:
    """`scene` with `elements` drawn first on its page, under everything else."""
    page = scene["children"][0]
    page["children"][:0] = list(elements)
    return scene


def card_scene(**sign: Any) -> dict[str, Any]:
    """A card's sign on paper, its paints as `sign` says."""
    result = draw(
        {"items": [{"id": "store", "concept": "sys/store"}]},
        components=lab(
            top=top(
                {"items": {"repeat": "items", "draw": "lab/card", "column": {}}},
                fields={"items": {"type": "array", "items": {"type": "object"}}},
            ),
            card=block({**MARK, "mark": {**MARK["mark"], "sign": sign}}),
        ),
        families=FAMILIES,
        concepts=CONCEPTS,
        signs=SIGNS,
    )
    assert result.findings == []
    return under(result.scene.to_dict(), {**box("back", 640, 200), "fill": "paper"})


def unstroked(scene: dict[str, Any]) -> dict[str, Any]:
    """`scene` with its sign's stroke 0 wide."""
    elements = list(scene["children"])
    while elements:
        element = elements.pop()
        if element.get("type") == "path":
            element["stroke-width"] = 0
        elements.extend(element.get("children", []))
    return scene


def drawn(scene: dict[str, Any]) -> list[tuple[str, str, str]]:
    return [
        (each.code, each.where, each.message)
        for each in checks.drawn_contrast(scene, COLOURS, ["default"])
    ]


def test_a_sign_holds_where_its_fill_or_its_stroke_reaches_the_contrast_for_marks() -> None:
    held = card_scene(fill="faint", stroke="ink", **{"stroke-width": "=@stroke.thin"})
    faint = card_scene(fill="faint", stroke="faint", **{"stroke-width": "=@stroke.thin"})
    thin = unstroked(card_scene(fill="faint", stroke="ink", **{"stroke-width": "=@stroke.thin"}))

    assert drawn(held) == []
    assert drawn(faint) == [
        (
            "contrast-drawn",
            "top/items[store]/mark",
            "the sign paints `faint` (1.61) and `faint` (1.61) on `paper` in the combination "
            "`default`, and none reaches the 3.0 a sign needs (`marks`)",
        )
    ]
    assert [message for _, _, message in drawn(thin)] == [
        "the sign paints `faint` (1.61) on `paper` in the combination `default`, and none "
        "reaches the 3.0 a sign needs (`marks`)"
    ]


def test_a_sign_that_paints_nothing_fails_and_one_over_a_picture_is_not_measured() -> None:
    bare = card_scene()
    pictured = card_scene(fill="faint")
    pictured["children"][0]["children"].insert(1, {**box("picture", 640, 200), "type": "image"})

    assert drawn(bare) == [
        (
            "contrast-drawn",
            "top/items[store]/mark",
            "the sign paints neither a fill nor a stroke, so it shows nothing",
        )
    ]
    assert drawn(pictured) == []


#: A text part that draws a run's sign, and no ground, so the sign lies on what lies under it.
UNGROUNDED = {key: value for key, value in SAYS.items() if key != "ground"}


def run_scene(*elements: dict[str, Any]) -> dict[str, Any]:
    """A run of `sys/store` with its sign, on paper with `elements` over it."""
    result = said({"text": "store", "style": "named", "concept": "sys/store"}, part=UNGROUNDED)
    assert result.findings == []
    scene = result.scene.to_dict()
    return under(scene, {**box("back", 640, 200), "fill": "paper"}, *elements)


def test_a_runs_sign_on_other_fills_than_its_text_is_measured_in_the_runs_paint() -> None:
    """The run paints `border`, which holds on `paper` as a text and fails on `shade` as a
    sign."""
    plain = run_scene()
    patched = run_scene({**box("patch", 20, 200), "fill": "shade"})
    pictured = run_scene({**box("picture", 20, 200), "type": "image"})

    assert drawn(plain) == drawn(pictured) == []
    assert drawn(patched) == [
        (
            "contrast-drawn",
            "top/says",
            "`border` on `shade` has the contrast 1.44 in the combination `default`, below the "
            "3.0 the sign of a run needs (`marks`)",
        )
    ]


# --- a concept left to its colour ---------------------------------------------------------------

#: A card painted from its family's fill, which draws no sign; and one that draws it.
BACKED = {"back": {"box": {"fill": ":colour.fill"}, "width": "=@space.1", "height": "=@space.1"}}
PAINTED = block(BACKED, states={"marked": {"colour": "red"}, "quiet": {}})
SIGNED = block({**BACKED, **MARK})


def listed(*items: dict[str, Any], card: dict[str, Any] = PAINTED, **more: Any) -> Any:
    """The scene of cards over `items`, each card drawn as `card`."""
    parts = {"items": {"repeat": "items", "draw": "lab/card", "column": {}}}
    fields = {"items": {"type": "array", "items": {"type": "object"}}}
    components = lab(top=top(parts, fields=fields), card=card, **more)
    return draw(
        {"items": list(items)},
        components=components,
        families=FAMILIES,
        concepts=CONCEPTS,
        signs=SIGNS,
    )


def alone(result: Any) -> list[tuple[str, str, bool]]:
    return [(each.concept, each.trace, each.alone) for each in result.shown]


def test_an_instance_painted_from_its_concepts_family_with_no_sign_is_left_to_its_colour() -> None:
    painted = listed(
        {"id": "store", "concept": "sys/store"}, {"id": "plain", "concept": "sys/plain"}
    )
    signed = listed({"id": "store", "concept": "sys/store"}, card=SIGNED)

    # A concept with no sign is its notation's call: the scene shows only those with one.
    assert alone(painted) == [("sys/store", "top/items[store]", True)]
    assert alone(signed) == [("sys/store", "top/items[store]", False)]


def test_a_state_that_gives_the_family_or_an_override_leaves_no_concept_to_its_colour() -> None:
    result = listed(
        {"id": "marked", "concept": "sys/store", "state": "marked"},
        {"id": "quiet", "concept": "sys/store", "state": "quiet"},
        {"id": "pointed", "concept": "sys/store", "override": {"back": "accent"}},
    )

    assert alone(result) == [
        ("sys/store", "top/items[marked]", False),
        ("sys/store", "top/items[quiet]", True),
        ("sys/store", "top/items[pointed]", False),
    ]


def test_what_an_instance_holds_paints_and_signs_its_concept_where_it_takes_its_family() -> None:
    """A holder of `sys/store` paints nothing itself; the badge it holds paints from its
    family, and draws its sign or none."""

    def holding(badge: dict[str, Any]) -> Any:
        holder = block({"badge": {"use": "lab/badge"}})
        slot = top({"s": {"slot": "body"}}, fields={"body": {"type": "object"}})
        return draw(
            {"body": {"use": "lab/holder", "concept": "sys/store"}},
            components=lab(top=slot, holder=holder, badge=badge),
            families=FAMILIES,
            concepts=CONCEPTS,
            signs=SIGNS,
        )

    assert alone(holding(block(BACKED))) == [("sys/store", "top/s", True)]
    assert alone(holding(SIGNED)) == [("sys/store", "top/s", False)]
    assert alone(holding(block(BACKED, colour="red"))) == [("sys/store", "top/s", False)]


def test_a_concept_left_to_its_colour_asks_once_for_each_version_naming_its_owner() -> None:
    shown = listed(
        {"id": "store", "concept": "sys/store"},
        {"id": "user", "concept": "sys/user"},
    ).shown
    other = listed({"id": "store", "concept": "sys/store"}, card=block(BACKED)).shown

    found = signs.findings([("content/en.yaml", shown), ("content/de.yaml", [*shown, *other])])

    assert [(f.code, f.level, f.where, f.library, f.who, f.extra) for f in found] == [
        (
            "sign-missing",
            "attention",
            "parts",
            "lab@1.0.0",
            "the owner of `lab`",
            {"component": "lab/card"},
        )
    ]
    [missing] = found
    assert missing.message == (
        "top/items[store] names the concept `sys/store`: a part of it, or of what it holds, "
        "paints from that concept's colour family, and none draws its sign, so its colour "
        "alone tells the concept apart"
    )
    assert missing.fix == (
        "give `lab/card` a sign part, which draws the sign of its instance's concept, in a "
        "version of its own"
    )


def test_a_run_painted_from_its_concepts_family_with_no_sign_for_its_style_asks_once() -> None:
    run = {"text": "store", "style": "named", "concept": "sys/store"}
    unsigned = {**SAYS, "sign": {"by": "says", "plain": False, "named": False}}
    inked = {**unsigned, "fill": "ink", "ground": None}

    asked = said(run, run, part=unsigned)
    assert [(each.trace, each.run, each.alone) for each in asked.shown] == [
        ("top/says", "says#1", True),
        ("top/says", "says#2", True),
    ]
    assert [each.alone for each in said(run).shown] == [False]
    assert [each.alone for each in said(run, part=inked).shown] == [False]
    stated = said(
        run, part=unsigned, states={"marked": {"colour": "red"}}, given={"state": "marked"}
    )
    assert [each.alone for each in stated.shown] == [False]

    [found] = signs.findings([("content/en.yaml", asked.shown)])
    assert (found.code, found.level, found.where, found.who, found.extra) == (
        "run-sign-missing",
        "attention",
        "parts.says.text",
        "the owner of `lab`",
        {"component": "lab/top"},
    )
    assert found.message == (
        "top/says: the run says#1 names the concept `sys/store`, and the text `says` paints it "
        "from that concept's colour family in the style `named`, for which it chooses no sign, "
        "so its colour alone tells the concept apart"
    )
    assert found.fix == (
        "have the text `says` of `lab/top` choose a sign for the style `named`, in a version of "
        "its own"
    )


# --- two concepts of one sign -------------------------------------------------------------------

#: `sys/crate` draws the square of `sys/store` in a square of its own; `sys/user` shares the
#: family of `sys/store`, and a sign of its own.
ONE_SIGN = {**SIGNS, "sys/crate": outline("M 0 0 H 20 V 20 H 0 Z", square=20)}
ONE_FAMILY = {**CONCEPTS, "sys/crate": "red", "sys/user": "blue"}


def concepts_shown(*named: str) -> Any:
    items = [{"id": name.partition("/")[2], "concept": name} for name in named]
    parts = {"items": {"repeat": "items", "draw": "lab/card", "column": {}}}
    fields = {"items": {"type": "array", "items": {"type": "object"}}}
    return draw(
        {"items": items},
        components=lab(top=top(parts, fields=fields), card=SIGNED),
        families=FAMILIES,
        concepts=ONE_FAMILY,
        signs=ONE_SIGN,
    ).shown


def test_two_concepts_whose_signs_are_one_outline_ask_the_author_once_in_each_language() -> None:
    both = concepts_shown("sys/store", "sys/user", "sys/crate")

    found = signs.findings(
        [
            ("content/en.yaml", both),
            ("content/en.yaml", both),
            ("content/de.yaml", both),
            ("content/fr.yaml", concepts_shown("sys/store", "sys/user")),
        ]
    )

    assert [(f.code, f.level, f.file, f.where, f.who) for f in found] == [
        ("sign-shared", "attention", "content/en.yaml", "items[crate].concept", findings.AUTHOR),
        ("sign-shared", "attention", "content/de.yaml", "items[crate].concept", findings.AUTHOR),
    ]
    assert found[0].message == (
        "the concepts `sys/store`, of the notation sys and `sys/crate`, of the notation sys "
        "have one sign, so their signs do not tell them apart"
    )


def test_a_concept_no_content_names_is_not_compared() -> None:
    """A concept a component gives, which no key of the content names, is the component's
    to choose, and not the piece's author's: two concepts of one sign are compared only
    where the content names both."""
    store, crate = concepts_shown("sys/store", "sys/crate")
    given = replace(crate, named="")

    assert signs.findings([("content/en.yaml", [store, given])]) == []
    assert [f.code for f in signs.findings([("content/en.yaml", [store, crate])])] == [
        "sign-shared"
    ]
