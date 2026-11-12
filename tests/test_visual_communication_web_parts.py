"""The starter's web parts (visual-communication DEC-022 points 4 to 6): each frame they draw
lies inside its page at each size, under the test brand and under the neutral brand. Their
widths come from the width they get and from what their text measures, never from a number
of their own. Each part's form changes where a size leaves it too little room: a navigation
is a row or a column, a header moves its navigation under its title, and a section stands
its picture beside its text or under it. A row of links given too little room is reported at
that size. A section shows the picture file its content names, sections lie in order, and a
table's text breaks within its cells. A form holds no action, and a field in error and a
button that cannot be pressed take their colour family. A line's length is capped by a
shared role with a default, a brand restyles a button through a role of the starter's, and
a header shows the brand's logo where the brand gives one. A site that draws every part
draws under both brands from one set of content files.

The pieces are the web parts' reference pieces under `tests/fixtures/visual-communication/
starter/`, and the site of every part under `tests/fixtures/visual-communication/web/`. The
test of frames is the capability's own, and adds no check to validation (DEC-022 point 5).
Run in this process (`tests/in_process.py`); it starts no `pkit`."""

from __future__ import annotations

import itertools
import json
import re
import shutil
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from tests import test_visual_communication_neutral as neutral
from tests import test_visual_communication_starter as starter
from tests import visual_communication_logo as logo
from tests.visual_communication_project import (
    FIXTURES,
    bound,
    locked_at,
    project,
    taken,
    version_folder,
    write,
    write_piece,
    yaml_text,
)

checks, keys, pl = starter.checks, starter.keys, starter.pl

#: The web parts: the components whose reference piece is drawn at the sizes of `device`.
WEB = sorted(set(starter.COMPONENTS) - set(starter.UNSIZED))
#: The site that draws every web part.
SITE = FIXTURES / "web" / "pieces" / "site"
#: The brands each piece is drawn under, and the width of a phone's page under each.
BRANDS = ("test-brand", "neutral")
#: How far a place on the page, summed from frames each rounded to 1/100 px, may stray.
ROUNDING = 0.02
#: The keys over the size axis, the desktop's first.
PHONE, TABLET = "device.phone", "device.tablet"


def read(path: Path) -> Any:
    return YAML(typ="safe").load(path.read_text(encoding="utf-8"))


def built(*names: str) -> dict[str, str]:
    """The version being built of each library the capability ships, by its name."""
    return {name: taken(name, being_built=True).version for name in names}


def location_under(brand: str, root: Path) -> Path:
    """The starter's reference location under `brand`, the test brand or the neutral brand,
    laid out in the project at `root`, with the site of every part beside its pieces."""
    if brand == "test-brand":
        starter.reference_location(root)
    else:
        neutral.reference_location(root)
    folder = root / "visual" / "pieces" / "site"
    shutil.copytree(SITE, folder, ignore=shutil.ignore_patterns("__pycache__"))
    if brand == "neutral":
        neutral.pinned_with_neutral(folder)
    locked_at(folder, built("foundations", "starter", "neutral"))
    return root


def drawn_piece(root: Path, name: str, **lock: str) -> Any:
    """The piece `name` of the location at `root`, under its lock, `lock` changing it."""
    piece = pl.read_piece(root, "visual", name)
    return pl.Project(piece, {**piece.lock, **lock}, pl.Held(root, "visual"))


def scenes_of(drawn: Any) -> dict[tuple[str, str], Mapping[str, Any]]:
    """The scene of a piece in each language at each size, by language and size key, each
    drawn with no finding."""
    found = {}
    for language, result in drawn.scenes(facts=drawn.piece.stand_ins):
        assert result.findings == [], (drawn.piece.name, language, result.findings)
        found[(language, result.scene.size_key)] = result.scene.to_dict()
    return found


@pytest.fixture(scope="module", params=BRANDS)
def under(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The location of the web parts' pieces and the site, under each brand in turn."""
    return location_under(request.param, project(tmp_path_factory.mktemp(request.param)))


@pytest.fixture(scope="module")
def scenes(under: Path) -> dict[tuple[str, str, str], Mapping[str, Any]]:
    """The scene of each web part's piece and of the site, in each language at each size,
    by the piece, the language and the size key."""
    found = {}
    for name in [*WEB, "site"]:
        for (language, size), scene in scenes_of(drawn_piece(under, name)).items():
            found[(name, language, size)] = scene
    return found


@pytest.fixture(scope="module")
def location(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The location under the test brand alone."""
    return location_under("test-brand", project(tmp_path_factory.mktemp("web")))


def pages(scene: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [each for each in starter.elements(scene) if each.get("page")]


def framed(scene: Mapping[str, Any]) -> dict[str, tuple[float, float, float, float]]:
    """Each element of a scene's pages, by its trace id, with its frame on its page."""
    return {
        str(element["id"]): frame
        for page in pages(scene)
        for element, frame in starter.frames(page)
    }


def inside(inner: tuple[float, ...], outer: tuple[float, ...]) -> bool:
    return (
        outer[0] - ROUNDING <= inner[0]
        and outer[1] - ROUNDING <= inner[1]
        and inner[2] <= outer[2] + ROUNDING
        and inner[3] <= outer[3] + ROUNDING
    )


# --- each frame inside its page ----------------------------------------------------------------


def test_the_pieces_are_drawn_at_each_size_in_each_language(
    scenes: Mapping[tuple[str, str, str], Mapping[str, Any]],
) -> None:
    """Each web part has a piece, and each piece is drawn at the three sizes the brands give,
    in English and in German, with no finding (the `scenes` fixture)."""
    assert WEB and set(WEB) <= set(starter.COMPONENTS)
    drawn = {(name, language, size) for name, language, size in scenes}
    sizes = [keys.DEFAULT_KEY, PHONE, TABLET]
    assert drawn == set(itertools.product([*WEB, "site"], starter.LANGUAGES, sizes))


def test_each_frame_lies_inside_its_page_at_each_size(
    scenes: Mapping[tuple[str, str, str], Mapping[str, Any]],
) -> None:
    """No check finds every part that runs past a page's edge, such as a column or a text
    with no width, so this test is the guard (DEC-022 point 5). Each element's frame lies
    inside its page, and each line of a text within the text's width."""
    checked = 0
    for (name, language, size), scene in scenes.items():
        for page in pages(scene):
            edge = (0.0, 0.0, page["width"], page["height"])
            for element, frame in starter.frames(page):
                assert inside(frame, edge), (name, language, size, element["id"], frame)
                for line in element.get("lines", []):
                    assert line["width"] <= element["width"] + ROUNDING, (name, element["id"])
                checked += 1
    assert checked > 0


# --- widths from the width a part gets ---------------------------------------------------------

#: A number written in a formula: digits that start no name and follow none.
NUMBER = re.compile(r"(?<![\w.@:-])\d+(?:\.\d+)?")
#: A role a formula reads, as `@<role>`.
ROLE = re.compile(r"@[A-Za-z0-9_.-]*[A-Za-z0-9_-]")
#: What a part measures: a part's width, or one of its edges across.
MEASURE = re.compile(r"(?<![@\w.:-])[a-z][\w-]*\.(?:width|x|right)\b")


def branches(value: Any) -> list[str]:
    """Each formula a value may take: a switch's every branch."""
    if isinstance(value, Mapping):
        return [each for key, branch in value.items() if key != "by" for each in branches(branch)]
    return [str(value)]


def expanded(formula: str, values: Mapping[str, Any]) -> list[str]:
    """Each form of `formula` with each value it reads written out, for every branch of
    each, so a formula is read down to the roles and the measures it rests on."""
    forms = [formula.removeprefix("=")]
    for name in sorted(values, key=len, reverse=True):
        named = re.compile(rf"(?<![\w.:@-]){re.escape(name)}(?![\w-]|\.[a-z])")
        written = []
        for form in forms:
            if not named.search(form):
                written.append(form)
                continue
            for branch in branches(values[name]):
                for inner in expanded(branch, values):
                    written.append(named.sub(lambda _, inner=inner: f"({inner})", form))
        forms = written
    return forms


def sized(component: Mapping[str, Any]) -> Iterator[tuple[str, str, str]]:
    """Each formula of a component that sets a width, a place across or a gap, by its part
    and its key: each part's `width` and `x`, its row's or column's `gap`, and the
    component's preferred width."""
    for part, value in component["parts"].items():
        for key in ("width", "x"):
            if key in value:
                for formula in branches(value[key]):
                    yield part, key, formula
        for direction in ("row", "column"):
            if "gap" in (value.get(direction) or {}):
                for formula in branches(value[direction]["gap"]):
                    yield part, "gap", formula
    preferred = component.get("preferred") or {}
    for formula in branches(preferred["width"]) if "width" in preferred else ():
        yield "preferred", "width", formula


@pytest.mark.parametrize("name", WEB)
def test_no_width_place_or_gap_holds_a_number_of_its_own(name: str) -> None:
    """A width, a place across and a gap read roles and what the part measures, never a
    number written in the file (DEC-022 point 5). A width reads the width the part gets or
    what its text measures, so a role may adjust it, as an inset, or cap it, but never sets
    the width a part needs in order to fit."""
    component = starter.COMPONENTS[name]
    values = component.get("values") or {}
    read_any = 0
    for part, key, formula in sized(component):
        for form in expanded(formula, values):
            read_any += 1
            assert not NUMBER.search(ROLE.sub("", form)), (name, part, key, form)
            if key == "width":
                assert ":width" in form or MEASURE.search(form), (name, part, form)
    assert read_any > 0, name


def test_the_cap_on_a_lines_length_is_a_shared_role_whose_default_ends_at_a_shared_role() -> None:
    """A line of a web part's text runs no longer than `size.line`, a role the foundations
    add with a default that aliases a role every brand gives (DEC-008 point 2, DEC-004
    point 7). Each part reads it only as a cap."""
    declared = starter.SHARED["size.line"]
    assert declared["type"] == "dimension"
    alias = starter.ALIAS.match(str(declared["default"]))
    assert alias and alias.group(1) in starter.SHARED
    assert "default" not in starter.SHARED[alias.group(1)]
    capped = 0
    for name in WEB:
        text = json.dumps(starter.COMPONENTS[name])
        for found in re.finditer(r"@size\.line", text):
            assert text[: found.start()].endswith("min("), name
            capped += 1
    assert capped > 0


# --- a form that changes by the size -----------------------------------------------------------


def frame_of(scene: Mapping[str, Any], trace_id: str) -> tuple[float, float, float, float]:
    return framed(scene)[trace_id]


def test_a_navigation_is_a_row_at_one_size_and_a_column_at_another(
    scenes: Mapping[tuple[str, str, str], Mapping[str, Any]],
) -> None:
    """Two parts repeat its links, one in a row and one in a column, each drawn at the sizes
    its `when` gives, so exactly one is drawn at each (DEC-021 point 4)."""
    parts = starter.COMPONENTS["navigation"]["parts"]
    repeats = {name: part for name, part in parts.items() if part.get("repeat") == "links"}
    assert sorted(("row" in part, "column" in part) for part in repeats.values()) == [
        (False, True),
        (True, False),
    ]
    for mode in ("desktop", "tablet", "phone"):
        drawn = [
            name
            for name, part in repeats.items()
            if part["when"]["by"] == ":device" and part["when"].get(mode, part["when"]["desktop"])
        ]
        assert len(drawn) == 1, (mode, drawn)
    links = read(starter.PIECES / "navigation" / "content.en.yaml")["pages"][0]["main"]["links"]
    for size, part in ((keys.DEFAULT_KEY, "links"), (PHONE, "links-phone")):
        scene = scenes[("navigation", "en", size)]
        frames = [frame_of(scene, f"site/pages[start]/main/{part}[{link['id']}]") for link in links]
        tops, lefts = {frame[1] for frame in frames}, {frame[0] for frame in frames}
        if part == "links":
            assert len(tops) == 1 and sorted(lefts) == [frame[0] for frame in frames], size
        else:
            assert len(lefts) == 1, size
            pairs = itertools.pairwise(frames)
            assert all(upper[3] <= lower[1] + ROUNDING for upper, lower in pairs), size


def test_a_header_moves_its_navigation_under_its_title_and_the_title_takes_the_row(
    scenes: Mapping[tuple[str, str, str], Mapping[str, Any]],
) -> None:
    """On a desktop the navigation stands beside the title, in its row. At a phone's size it
    moves under the title, and the title is broken to the whole row (DEC-022 point 5)."""
    head = "site/pages[plain]/main"
    for language in starter.LANGUAGES:
        wide = framed(scenes[("header", language, keys.DEFAULT_KEY)])
        title, navigation = wide[f"{head}/title"], wide[f"{head}/navigation"]
        assert navigation[0] >= title[2] - ROUNDING and navigation[1] < title[3]
        assert f"{head}/navigation-narrow" not in wide
        scene = scenes[("header", language, PHONE)]
        narrow = framed(scene)
        title, navigation = narrow[f"{head}/title-narrow"], narrow[f"{head}/navigation-narrow"]
        assert navigation[1] >= title[3] - ROUNDING
        assert f"{head}/navigation" not in narrow and f"{head}/title" not in narrow
        [page] = [each for each in pages(scene) if each["id"] == "site/pages[plain]"]
        assert title[2] == pytest.approx(page["width"] - title[0], abs=ROUNDING)


def test_a_section_stands_its_picture_beside_its_text_at_one_size_and_under_it_at_another(
    scenes: Mapping[tuple[str, str, str], Mapping[str, Any]],
) -> None:
    """On a desktop the picture stands to the right of the text, or to its left. On a tablet
    and a phone it stands under the text, at its start."""
    for language in starter.LANGUAGES:
        wide = framed(scenes[("section", language, keys.DEFAULT_KEY)])
        for page, beside in (("right", True), ("left", False)):
            text, picture = (
                wide[f"site/pages[{page}]/main/{part}"] for part in ("text", "picture")
            )
            if beside:
                assert picture[0] >= text[2] - ROUNDING, (language, page)
            else:
                assert picture[2] <= text[0] + ROUNDING, (language, page)
            assert picture[1] < text[3] and text[1] < picture[3], (language, page)
        for size in (TABLET, PHONE):
            narrow = framed(scenes[("section", language, size)])
            for page in ("right", "left"):
                text, picture = (
                    narrow[f"site/pages[{page}]/main/{part}"] for part in ("text", "picture")
                )
                assert picture[1] >= text[3] - ROUNDING and picture[0] == text[0], (size, page)


def test_a_section_shows_the_picture_file_its_content_names_and_draws_with_none(
    scenes: Mapping[tuple[str, str, str], Mapping[str, Any]],
) -> None:
    """The picture is a file of the piece, by the bare name its content gives (DEC-025
    point 1). A section that names none draws its words alone, with no finding."""
    for size in (keys.DEFAULT_KEY, TABLET, PHONE):
        drawn = starter.by_id(scenes[("section", "en", size)])
        picture = drawn["site/pages[right]/main/picture"]
        assert (picture["type"], picture["file"], picture["library"]) == (
            "image",
            "window.png",
            "piece",
        )
        assert "site/pages[words]/main/picture" not in drawn
        words, right = (drawn[f"site/pages[{page}]/main/text"] for page in ("words", "right"))
        assert words["x"] == right["x"]


def written(root: Path, name: str, language: str, change: Any) -> Any:
    """The piece `name` of the location at `root`, its content in `language` changed by
    `change`, which takes the content and changes it in place."""
    path = root / "visual" / "pieces" / name / f"content.{language}.yaml"
    content = read(path)
    change(content)
    write(path, yaml_text(content))
    return drawn_piece(root, name)


def heights(drawn: Any) -> dict[str, dict[str, float]]:
    """The height of each page of a piece's scenes in English, by size key and page id."""
    return {
        size: {page["id"]: page["height"] for page in pages(scene)}
        for (language, size), scene in scenes_of(drawn).items()
        if language == "en"
    }


def test_sections_lie_in_their_order_and_one_more_makes_the_page_taller(
    location: Path, tmp_path: Path
) -> None:
    """The part that lays sections down a page draws each under the one before it, each the
    page's whole width (DEC-022 point 4)."""
    before = drawn_piece(location, "sections")
    for (language, size), scene in scenes_of(before).items():
        content = read(starter.PIECES / "sections" / f"content.{language}.yaml")
        ids = [each["id"] for each in content["pages"][0]["main"]["sections"]]
        frames = [frame_of(scene, f"site/pages[order]/main/sections[{each}]") for each in ids]
        assert all(
            upper[3] == pytest.approx(lower[1], abs=ROUNDING)
            for upper, lower in itertools.pairwise(frames)
        ), size
        [page] = pages(scene)
        assert all(frame[0] == 0 and frame[2] == page["width"] for frame in frames), size
    root = tmp_path / "project"
    shutil.copytree(location, root)

    def add(content: Any) -> None:
        sections = content["pages"][0]["main"]["sections"]
        sections.append({"id": "more", "head": "One more", "text": "A section more."})

    after = written(root, "sections", "en", add)
    taller = heights(after)
    for size, page in heights(before).items():
        assert taller[size]["site/pages[order]"] > page["site/pages[order]"], size


def test_a_tables_text_breaks_within_its_cells_and_one_more_row_makes_it_taller(
    scenes: Mapping[tuple[str, str, str], Mapping[str, Any]], location: Path, tmp_path: Path
) -> None:
    """Each cell's text breaks to the cell's width at each size, so a narrow page breaks it
    onto more lines, and a row more makes the page taller."""
    broken = 0
    for (name, _, size), scene in scenes.items():
        if name != "table":
            continue
        drawn = starter.by_id(scene)
        for trace_id, element in drawn.items():
            if element.get("component") != "starter/cell":
                continue
            for part in ("head", "text"):
                text = drawn.get(f"{trace_id}/{part}")
                if text is None:
                    continue
                assert text["width"] == pytest.approx(element["width"]), trace_id
                assert all(line["width"] <= text["width"] + ROUNDING for line in text["lines"])
                broken += size == PHONE and len(text["lines"]) > 1
    assert broken > 0
    root = tmp_path / "project"
    shutil.copytree(location, root)

    def add(content: Any) -> None:
        rows = content["pages"][0]["main"]["rows"]
        rows.append({"id": "third", "cells": [{"id": "version", "span": "narrow", "text": "1.2"}]})

    before = heights(drawn_piece(location, "table"))
    after = heights(written(root, "table", "en", add))
    for size, page in before.items():
        assert after[size]["site/pages[head]"] > page["site/pages[head]"], size


def test_a_form_holds_labels_fields_and_buttons_and_no_action(
    scenes: Mapping[tuple[str, str, str], Mapping[str, Any]],
) -> None:
    """A form is drawn, never sent: it declares no field for an action, and each field shows
    the text its content gives it (DEC-022 point 6)."""
    assert set(starter.COMPONENTS["form"]["fields"]["properties"]) == {
        "head",
        "fields",
        "field",
        "buttons",
        "button",
    }
    for language in starter.LANGUAGES:
        content = read(starter.PIECES / "form" / f"content.{language}.yaml")
        main = content["pages"][0]["main"]
        for size in (keys.DEFAULT_KEY, TABLET, PHONE):
            drawn = starter.by_id(scenes[("form", language, size)])
            for field in main["fields"]:
                held = f"site/pages[full]/main/fields[{field['id']}]"
                assert drawn[f"{held}/label"]["text"] == field["label"]
                assert drawn[f"{held}/value"]["text"] == field["value"]
            row = "buttons-phone" if size == PHONE else "buttons"
            for button in main["buttons"]:
                label = drawn[f"site/pages[full]/main/{row}[{button['id']}]/label"]
                assert label["text"] == button["label"]


def test_a_field_in_error_and_a_button_that_cannot_be_pressed_take_their_family(
    scenes: Mapping[tuple[str, str, str], Mapping[str, Any]],
) -> None:
    """A state is a colour family (DEC-022 point 6): the field's box and its text take the
    red family's fill and text, and the button's take the neutral family's."""
    for size in (keys.DEFAULT_KEY, TABLET, PHONE):
        drawn = starter.by_id(scenes[("field", "en", size)])
        mail = "site/pages[fields]/main/fields[mail]"
        assert drawn[f"{mail}/box"]["fill"] == "family.red.fill"
        assert {run["fill"] for run in drawn[f"{mail}/value"]["paragraphs"][0]} == {
            "family.red.text"
        }
        assert drawn["site/pages[fields]/main/fields[name]/box"]["fill"] == "family.neutral.fill"
        drawn = starter.by_id(scenes[("button", "en", size)])
        row = "buttons-phone" if size == PHONE else "buttons"
        assert drawn[f"site/pages[states]/main/{row}[send]/box"]["fill"] == "family.blue.fill"
        assert drawn[f"site/pages[states]/main/{row}[draft]/box"]["fill"] == "family.neutral.fill"


def test_each_text_of_a_state_reaches_its_contrast_in_every_combination(under: Path) -> None:
    """The field in error and the button that cannot be pressed, as each brand draws them,
    reach WCAG's level for their text in every combination of modes, at each size."""
    measured = 0
    for name in ("field", "button", "site"):
        drawn = drawn_piece(under, name)
        colours = {
            path: token["values"]
            for path, token in drawn.values()["tokens"].items()
            if token["type"] == "color"
        }
        for _, result in drawn.scenes(facts=drawn.piece.stand_ins):
            served = [key for key in drawn.keys if drawn.size_key(key) == result.scene.size_key]
            scene = result.scene.to_dict()
            assert checks.drawn_contrast(scene, colours, served) == [], name
            measured += len(served)
    assert measured > 0


# --- what the check reports --------------------------------------------------------------------

#: Links that fit a desktop's row under the test brand, and not a tablet's.
LONG_LINKS = [
    {"id": "start", "label": "Getting started with the methodology"},
    {"id": "decisions", "label": "The decisions every project keeps"},
    {"id": "capabilities", "label": "The capabilities you can install"},
    {"id": "pictures", "label": "Drawing pictures"},
]


def test_a_navigation_whose_links_ask_for_more_than_its_row_is_reported_at_that_size(
    location: Path, tmp_path: Path
) -> None:
    """A row of links whose labels ask for more than a tablet's row gives them fails the
    check at that size alone, its message naming the size (DEC-022 point 8)."""
    root = tmp_path / "project"
    shutil.copytree(location, root)
    write_piece(
        root,
        "links",
        top="foundations/site",
        modes={"device": ["desktop", "tablet", "phone"]},
        lock={**built("foundations", "starter"), "test-brand": "1.1.0"},
    )
    content = {
        "pages": [
            {
                "id": "home",
                "layout": "standard",
                "main": {"use": "starter/navigation", "links": LONG_LINKS},
            }
        ]
    }
    write(root / "visual/pieces/links/content.en.yaml", yaml_text(bound("content", **content)))
    report = checks.check(root)
    found = [
        (level, finding.where, finding.message)
        for finding, level in report.judged
        if finding.code == "gets-less"
    ]
    assert [(level, where) for level, where, _ in found] == [
        ("fails", "site/pages[home]/main/links")
    ]
    assert found[0][2].startswith(f"`{TABLET}`: ")


# --- a brand's look ----------------------------------------------------------------------------

#: The corners a brand gives its buttons in the test below.
BUTTON_CORNER = 12.0


def test_a_brand_rounds_its_buttons_through_a_role_with_no_part_changed(
    location: Path, tmp_path: Path
) -> None:
    """A brand that names the starter gives `starter.button.corner` a value of its own, and
    every button takes it, the starter's files unchanged (DEC-008 point 4)."""
    before = scenes_of(drawn_piece(location, "button"))
    root = tmp_path / "project"
    shutil.copytree(location, root)
    brand = version_folder(root, "test-brand", "1.1.0")
    library = brand / "library.yaml"
    library.write_text(
        library.read_text(encoding="utf-8").replace(
            "  - {name: foundations, major: 1}\n",
            "  - {name: foundations, major: 1}\n  - {name: starter, major: 1}\n",
        ),
        encoding="utf-8",
    )
    base = brand / "tokens" / "base.tokens.json"
    given = json.loads(base.read_text(encoding="utf-8"))
    corner = {"$value": {"value": BUTTON_CORNER, "unit": "px"}}
    given["starter"] = {"$type": "dimension", "button": {"corner": corner}}
    base.write_text(json.dumps(given), encoding="utf-8")
    after = scenes_of(drawn_piece(root, "button"))
    for key, scene in after.items():
        boxes = [
            element
            for element in starter.elements(scene)
            if str(element.get("id", "")).endswith("]/box") and "/buttons" in element["id"]
        ]
        assert boxes and all(box["rx"] == BUTTON_CORNER for box in boxes), key
        earlier = [
            element
            for element in starter.elements(before[key])
            if str(element.get("id", "")).endswith("]/box") and "/buttons" in element["id"]
        ]
        assert all(box["rx"] != BUTTON_CORNER for box in earlier), key
    assert starter.files_of(root / "visual/libraries/starter") == starter.files_of(
        location / "visual/libraries/starter"
    )


def test_a_header_shows_the_brands_logo_and_draws_with_none_where_it_gives_none(
    location: Path, tmp_path: Path
) -> None:
    """Under a brand that gives `picture.logo`, the header shows it before its title. Under
    the test brand, which gives none, it draws no logo and its title starts at the inset,
    with no finding (the `scenes` fixture; DEC-025 point 4)."""
    head = "site/pages[plain]/main"
    plain = scenes_of(drawn_piece(location, "header"))
    root = tmp_path / "project"
    shutil.copytree(location, root)
    logo.logo_brand(root, version="1.1.0", source=starter.SIZED_BRAND)
    listed = root / "visual" / "libraries" / "libraries.yaml"
    libraries = read(listed)
    libraries["libraries"][logo.NAME] = {
        "source": {"kind": "project"},
        "versions": {"1.1.0": {"released": False}},
    }
    write(listed, yaml_text(libraries))
    path = root / "visual" / "pieces" / "header" / "piece.yaml"
    piece = read(path)
    lock = {**piece["lock"], logo.NAME: piece["lock"].pop("test-brand")}
    write(path, yaml_text({**piece, "brand": logo.NAME, "lock": lock}))
    shown = scenes_of(drawn_piece(root, "header"))
    for key, scene in shown.items():
        drawn = starter.by_id(scene)
        image = drawn[f"{head}/logo"]
        assert image["type"] == "image" and image["width"] > 0, key
        title = drawn.get(f"{head}/title") or drawn[f"{head}/title-narrow"]
        assert title["x"] > image["x"] + image["width"], key
        bare = starter.by_id(plain[key])
        assert f"{head}/logo" not in bare or bare[f"{head}/logo"]["width"] == 0, key
        title = bare.get(f"{head}/title") or bare[f"{head}/title-narrow"]
        assert title["x"] == pytest.approx(drawn[f"{head}/logo"]["x"]), key


# --- the site of every part ------------------------------------------------------------------


def test_a_site_of_every_part_draws_under_both_brands_from_one_set_of_content_files(
    under: Path, scenes: Mapping[tuple[str, str, str], Mapping[str, Any]]
) -> None:
    """The site places every web part, in its header, its main parts and its footer. Each
    brand draws it at each of its sizes with no finding, from the same content files, and it
    passes the check with no finding but the brand's fact that it gives no logo, beside the
    reference pieces' calls for attention on their concepts' signs."""
    placed = {
        str(element.get("component", "")).removeprefix("starter/")
        for (name, _, _), scene in scenes.items()
        if name == "site"
        for element in starter.elements(scene)
    }
    assert set(WEB) <= placed
    for language in starter.LANGUAGES:
        held = under / "visual" / "pieces" / "site" / f"content.{language}.yaml"
        assert held.read_bytes() == (SITE / f"content.{language}.yaml").read_bytes()
    report = checks.check(under)
    found = [
        (finding.code, finding.file)
        for finding, level in report.judged
        if finding.code != "component-experimental" and finding.code not in starter.SIGN_LABELS
    ]
    assert [code for code, _ in found] == ["picture-role-unvalued"]
    assert starter.on_signs(report.judged) == starter.UNSIGNED
    assert not report.failed()
