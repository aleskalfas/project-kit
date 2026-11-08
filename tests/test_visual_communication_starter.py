"""The starter, the component library the capability ships to start from (visual-communication
DEC-007): `pkit visual add starter` copies and lists it; every role of its own ends, along
its defaults, at a shared role (DEC-008 point 2); each pattern declares a component field
for each list it repeats (DEC-010, Implications); it holds no raw value; and each
component's reference renders, under the test brand, pass the check and draw each word of
each option and of each field of runs (DEC-007 point 3). A run that reads a colour family
lies on that family's fill (`components.md`, *Values, states and colour*). A connector's
line reaches 3:1 against what it lies on in every mode, and crosses no item but its ends;
a strong run keeps the body's size and line height. The README names what the components
declare. A network's ties reach, by key path, the items its groups draw (DEC-011 point 3);
no part passes a field of runs on (DEC-012 point 8); a pattern placed inside another draws
within it with no overflow; a panel's span gives its share of the row (DEC-010 point 4);
the panels of a row end on one edge where one holds panels of its own; a code block's
lines stand as written; and a row of cards keeps its heads at one height, whichever bar
each has, each clear of a top bar.

The reference renders are the pieces under `tests/fixtures/visual-communication/starter/`,
one for each component, drawn in English and in German. Run in this process
(`tests/in_process.py`); it starts no `pkit`."""

from __future__ import annotations

import itertools
import json
import math
import re
import shutil
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load, run_main
from tests.visual_communication_project import (
    CAPABILITY,
    FIXTURES,
    FOUNDATIONS,
    TEST_BRAND,
    TEST_NOTATION,
    bound,
    copy_library,
    hold_shipped,
    project,
    taken,
    version_folder,
    write_list,
)

add, checks, pl, reading, tokens = load(
    "visual-communication", "add.py", "checks", "pipeline", "reading", "tokens"
)

STARTER = CAPABILITY / "libraries" / "starter"
PIECES = FIXTURES / "starter" / "pieces"
README = STARTER / "README.md"
LANGUAGES = ["en", "de"]
UNRELEASED = {"1.0.0": {"released": False}}

#: The keys of a part, and of its kind's mapping, that paint with a colour role.
PAINTS = ("fill", "stroke")
#: The members of a colour family a paint `:colour.<member>` names (DEC-004 point 10).
MEMBERS = ("fill", "line", "text")
ALIAS = re.compile(r"^\{([A-Za-z0-9_.-]+)\}$")
REFERENCE = re.compile(r"@([A-Za-z0-9_.-]*[A-Za-z0-9_-])")
FAMILY_TEXT = re.compile(r"^family\.([a-z]+)\.text$")


def read(path: Path) -> Any:
    return reading.read_yaml(path)


def roles(folder: Path) -> dict[str, Mapping[str, Any]]:
    return dict(read(folder / "roles.yaml")["roles"])


SHARED = roles(FOUNDATIONS)
OWN = roles(STARTER)
DECLARED = {**SHARED, **OWN}
COMPONENTS = {path.stem: read(path) for path in sorted((STARTER / "components").glob("*.yaml"))}


def options(component: Mapping[str, Any]) -> dict[str, list[str]]:
    return {name: list(words) for name, words in (component.get("options") or {}).items()}


def run_words(component: Mapping[str, Any]) -> dict[str, list[str]]:
    """Each field of runs of `component`, with the words of its run styles."""
    fields = (component.get("fields") or {}).get("properties") or {}
    return {
        name: list(schema["x-pkit-runs"])
        for name, schema in fields.items()
        if "x-pkit-runs" in schema
    }


def leaves(value: Any) -> Iterator[Any]:
    """Each value `value` gives, through the branches of each switch (`by`)."""
    if isinstance(value, Mapping) and "by" in value:
        for word, branch in value.items():
            if word != "by":
                yield from leaves(branch)
    else:
        yield value


def scalars(value: Any) -> Iterator[Any]:
    """Every scalar within `value`."""
    if isinstance(value, Mapping):
        for each in value.values():
            yield from scalars(each)
    elif isinstance(value, list):
        for each in value:
            yield from scalars(each)
    else:
        yield value


def paints(part: Mapping[str, Any]) -> Iterator[Any]:
    """Each paint of a part, through every switch."""
    for kind in ("box", "ellipse", "text", "line"):
        drawing = part.get(kind)
        if isinstance(drawing, Mapping):
            for key in PAINTS:
                if key in drawing:
                    yield from leaves(drawing[key])


# --- the copy ---------------------------------------------------------------------------------


def files_of(folder: Path) -> dict[str, bytes]:
    return {
        path.relative_to(folder).as_posix(): path.read_bytes()
        for path in sorted(folder.rglob("*"))
        if path.is_file()
    }


def test_add_copies_the_starter_whole_and_lists_it_shipped(tmp_path: Path) -> None:
    """What the capability ships by default, as the tree holds it: the newest released
    version, with its record's entry, or the version being built where none is released."""
    ships = taken("starter")
    root = project(tmp_path)
    added = run_main(add, "starter", cwd=root)
    assert added.returncode == 0, added.stderr
    copy = root / "visual" / "libraries" / "starter" / ships.version
    assert files_of(copy) == files_of(ships.folder)
    listed = read(root / "visual" / "libraries" / "libraries.yaml")
    versions = {ships.version: ships.entry}
    assert listed == bound(
        "libraries", libraries={"starter": {"source": {"kind": "shipped"}, "versions": versions}}
    )


# --- its roles and its patterns ---------------------------------------------------------------


@pytest.mark.parametrize("role", sorted(OWN))
def test_each_own_role_ends_along_its_defaults_at_a_shared_role_of_its_type(role: str) -> None:
    seen = [role]
    while role not in SHARED:
        alias = ALIAS.match(str(OWN[role].get("default", "")))
        assert alias, f"`{role}` has no default that is an alias: {seen}"
        target = alias.group(1)
        assert target in DECLARED, f"`{role}` defaults to `{target}`, which no library declares"
        assert DECLARED[target]["type"] == OWN[seen[0]]["type"], seen
        assert target not in seen, f"a loop of defaults: {[*seen, target]}"
        seen.append(target)
        role = target
    assert all(name.startswith("starter.") for name in seen[:-1])


@pytest.mark.parametrize("name", sorted(COMPONENTS))
def test_each_list_a_component_repeats_has_a_component_field(name: str) -> None:
    component = COMPONENTS[name]
    fields = (component.get("fields") or {}).get("properties") or {}
    lists = component.get("lists") or {}
    for part in component["parts"].values():
        if "repeat" not in part:
            continue
        declared = lists.get(part["repeat"])
        assert declared and "component" in declared, (name, part["repeat"])
        assert fields[declared["component"]]["type"] == "object"
        drawn = COMPONENTS[part["draw"].removeprefix("starter/")]
        assert ("ends" in declared) == bool(drawn.get("ends")), (name, part["repeat"])


@pytest.mark.parametrize("name", sorted(COMPONENTS))
def test_a_component_holds_no_raw_value(name: str) -> None:
    component = COMPONENTS[name]
    for part, value in component["parts"].items():
        for paint in paints(value):
            if paint.startswith(":colour."):
                assert paint.removeprefix(":colour.") in MEMBERS, (name, part, paint)
            else:
                assert DECLARED[paint]["type"] == "color", (name, part, paint)
        style = (value.get("text") or {}).get("style")
        for each in leaves(style) if style is not None else ():
            assert DECLARED[each]["type"] == "typography", (name, part, each)
    for key in ("parts", "values", "preferred"):
        for scalar in scalars(component.get(key) or {}):
            assert not isinstance(scalar, (int, float)) or isinstance(scalar, bool), (name, key)
            for reference in REFERENCE.findall(str(scalar)):
                assert reference in DECLARED, (name, key, reference)


def test_each_default_of_its_own_roles_is_an_alias_never_a_value() -> None:
    assert [
        role for role, declared in OWN.items() if not ALIAS.match(str(declared.get("default")))
    ] == []


# --- the reference renders --------------------------------------------------------------------


@pytest.fixture(scope="module")
def location(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A location that holds the foundations and the starter being built as the capability
    ships them, the released version of their number where it is released, the test brand
    and the test notation, and the starter's reference pieces."""
    root = project(tmp_path_factory.mktemp("starter"))
    copy_library(root, TEST_BRAND, "test-brand", "1.0.0")
    copy_library(root, TEST_NOTATION, "test-notation", "1.0.0")
    write_list(
        root,
        {
            "test-brand": {"source": {"kind": "project"}, "versions": UNRELEASED},
            "test-notation": {"source": {"kind": "project"}, "versions": UNRELEASED},
        },
    )
    hold_shipped(root, "foundations")
    hold_shipped(root, "starter")
    shutil.copytree(PIECES, root / "visual" / "pieces")
    return root


@pytest.fixture(scope="module")
def projects(location: Path) -> dict[str, Any]:
    """Each reference piece as the engine draws it, by the piece's name."""
    drawn = {}
    for piece_folder in sorted(PIECES.iterdir()):
        piece = pl.read_piece(location, "visual", piece_folder.name)
        drawn[piece_folder.name] = pl.Project(piece, piece.lock, pl.Held(location, "visual"))
    return drawn


@pytest.fixture(scope="module")
def scenes(projects: Mapping[str, Any]) -> dict[tuple[str, str], Mapping[str, Any]]:
    """The scene of each reference piece in each language, by piece and language."""
    computed = {}
    for name, drawn in projects.items():
        for language, result in drawn.scenes(facts=drawn.piece.stand_ins):
            assert result.findings == [], (name, language, result.findings)
            computed[(name, language)] = result.scene.to_dict()
    return computed


@pytest.fixture(scope="module")
def resolved(projects: Mapping[str, Any]) -> dict[str, tuple[dict[str, Any], list[str]]]:
    """For each reference piece, the test brand's value of each token in each combination
    of modes, by token path, and the combinations the piece is drawn in."""
    found = {}
    for name, drawn in projects.items():
        values = {path: token["values"] for path, token in drawn.values()["tokens"].items()}
        found[name] = (values, list(drawn.keys))
    return found


def test_each_component_has_its_reference_piece_pinned_with_the_test_brand() -> None:
    assert sorted(path.name for path in PIECES.iterdir()) == sorted(COMPONENTS)
    for folder in PIECES.iterdir():
        piece = read(folder / "piece.yaml")
        assert piece["brand"] == "test-brand"
        assert piece["pinned"] is True
        assert piece["languages"] == LANGUAGES
        assert piece["lock"]["starter"] == "1.0.0"


def test_every_reference_piece_passes_the_check_under_the_test_brand(location: Path) -> None:
    """The test brand's version states, once, that it gives `picture.logo` no value, and no
    piece states it (DEC-025 point 9)."""
    report = checks.check(location)
    found = [
        (level, finding.code, finding.file, finding.where)
        for finding, level in report.judged
        if finding.code != "component-experimental"
    ]
    assert found == [
        ("fact", "picture-role-unvalued", "visual/libraries/test-brand/1.0.0/", "picture.logo")
    ]
    assert not report.failed()
    assert report.summary == [
        f"{len(COMPONENTS)} piece(s) in `visual`: the scenes of 0 read from their findings "
        f"record, of {len(COMPONENTS)} computed now, of 0 not checked."
    ]


def elements(element: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    yield element
    for child in element.get("children", []):
        yield from elements(child)


#: A step of a source's field path: a key, then the item of each list it leads into, by
#: `[<id>]` or by `#<place>` from 1 (`components.md`, *Sources*).
SOURCE_STEP = re.compile(r"^([A-Za-z0-9_-]+)((?:\[[^\]]+\]|#\d+)*)$")
SOURCE_ITEM = re.compile(r"\[([^\]]+)\]|#(\d+)")


def at_source(content: Any, path: str) -> Any:
    """What a content file holds at the field path a scene's source names."""
    value = content
    for step in path.split("."):
        found = SOURCE_STEP.match(step)
        assert found, (path, step)
        value = value[found.group(1)]
        for item, place in SOURCE_ITEM.findall(found.group(2)):
            if item:
                [value] = [
                    each for each in value if isinstance(each, Mapping) and each.get("id") == item
                ]
            else:
                value = value[int(place) - 1]
    return value


def run_word(run: Mapping[str, Any], words: list[str], content: Any) -> str:
    """The word of a drawn run: the style the content names on it, read at its style's
    source, else its field's first word."""
    source = str(run["sources"]["style"])
    if not source.startswith("content:"):
        return words[0]
    return str(at_source(content, source.removeprefix("content:")))


def drawn_words(
    scenes: Mapping[tuple[str, str], Mapping[str, Any]], language: str
) -> dict[tuple[str, str], set[str]]:
    """The words each option, and each field of runs, of each starter component took in
    the scenes of `language`. A run's word is read from its content, where its style's
    source names it, since two words may take one role and one paint."""
    words: dict[tuple[str, str], set[str]] = {}
    for (piece, lang), scene in scenes.items():
        if lang != language:
            continue
        content = read(PIECES / piece / f"content.{lang}.yaml")
        for element in elements(scene):
            component = str(element.get("component", ""))
            if not component.startswith("starter/"):
                continue
            name = component.removeprefix("starter/")
            for option, word in (element.get("options") or {}).items():
                words.setdefault((name, option), set()).add(word)
            for field, declared in run_words(COMPONENTS[name]).items():
                for child in element.get("children", []):
                    if child["id"] != f"{element['id']}/{field}":
                        continue
                    for paragraph in child["paragraphs"]:
                        for run in paragraph:
                            word = run_word(run, declared, content)
                            words.setdefault((name, field), set()).add(word)
    return words


def styled_runs(component: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    """For each field of runs of a component whose every word takes a role of its own,
    such as the card, the run word each typography role its text part's style switch
    gives stands for."""
    found = {}
    for field, words in run_words(component).items():
        [part] = [
            part
            for part in component["parts"].values()
            if (part.get("text") or {}).get("content") == field
        ]
        style = part["text"]["style"]
        assert style["by"] == field
        by_style = {style[word]: word for word in words}
        assert len(by_style) == len(words)
        found[field] = by_style
    return found


@pytest.mark.parametrize("language", LANGUAGES)
def test_each_word_of_each_option_and_of_each_field_of_runs_is_drawn(
    scenes: Mapping[tuple[str, str], Mapping[str, Any]], language: str
) -> None:
    words = drawn_words(scenes, language)
    for name, component in COMPONENTS.items():
        for option, declared in {**options(component), **run_words(component)}.items():
            assert words.get((name, option), set()) == set(declared), (name, option)


def frames(
    element: Mapping[str, Any], x: float = 0.0, y: float = 0.0
) -> Iterator[tuple[Mapping[str, Any], tuple[float, float, float, float]]]:
    """Each element below `element`, in the order drawn, with its frame on its page."""
    left, top = x + element["x"], y + element["y"]
    yield element, (left, top, left + element["width"], top + element["height"])
    for child in element.get("children", []):
        yield from frames(child, left, top)


@pytest.mark.parametrize("language", LANGUAGES)
def test_a_text_in_a_familys_text_lies_on_that_familys_fill(
    scenes: Mapping[tuple[str, str], Mapping[str, Any]], language: str
) -> None:
    checked = 0
    for (piece, lang), scene in scenes.items():
        if lang != language:
            continue
        pages = [each for each in elements(scene) if each.get("page")]
        for page in pages:
            boxes: list[tuple[str, tuple[float, float, float, float]]] = []
            for element, frame in frames(page):
                if element["type"] == "box":
                    boxes.append((element.get("fill", ""), frame))
                for paragraph in element.get("paragraphs", []):
                    for run in paragraph:
                        family = FAMILY_TEXT.match(run["fill"])
                        if family is None:
                            continue
                        checked += 1
                        assert any(
                            fill == f"family.{family.group(1)}.fill"
                            and under[0] <= frame[0]
                            and under[1] <= frame[1]
                            and frame[2] <= under[2]
                            and frame[3] <= under[3]
                            for fill, under in boxes
                        ), (piece, element["id"], run["text"])
    assert checked > 0


#: Every combination of the foundations' modes: a piece drawn in each mode of each axis is
#: drawn in all of them.
COMBINATIONS = math.prod(
    len(axis["modes"]) for axis in read(FOUNDATIONS / "roles.yaml")["axes"].values()
)
#: How many points of each stretch of a connector's route are measured.
SAMPLES = 16

Point = tuple[float, float]
#: A box drawn on a page: its fill, its frame on the page, and its trace id.
Painted = tuple[str, tuple[float, float, float, float], str]


def connector_lines(
    page: Mapping[str, Any],
) -> Iterator[tuple[Mapping[str, Any], list[Point], list[Painted]]]:
    """Each line a starter connector draws on `page`, with the points of its route on the
    page, and the boxes drawn before it."""
    connectors: set[str] = set()
    boxes: list[Painted] = []
    for element, frame in frames(page):
        if element.get("component") == "starter/connector":
            connectors.add(str(element["id"]))
        if element["type"] == "box" and element.get("fill"):
            boxes.append((str(element["fill"]), frame, str(element["id"])))
        if element["type"] == "line" and str(element["id"]).rpartition("/")[0] in connectors:
            left, top = frame[0] - element["x"], frame[1] - element["y"]
            ends = element.get("points") or [
                {"x": element["x1"], "y": element["y1"]},
                {"x": element["x2"], "y": element["y2"]},
            ]
            route = [(left + point["x"], top + point["y"]) for point in ends]
            yield element, route, list(boxes)


def inside(route: list[Point]) -> Iterator[Point]:
    """Points along each stretch of a route, short of its two ends, where it meets its items."""
    for (x1, y1), (x2, y2) in itertools.pairwise(route):
        for step in range(SAMPLES):
            share = (step + 0.5) / SAMPLES
            yield x1 + (x2 - x1) * share, y1 + (y2 - y1) * share


def holding(point: Point, boxes: list[Painted]) -> list[Painted]:
    """The boxes that hold `point`, the last drawn first."""
    x, y = point
    return [
        box
        for box in reversed(boxes)
        if box[1][0] <= x <= box[1][2] and box[1][1] <= y <= box[1][3]
    ]


def under(point: Point, boxes: list[Painted]) -> list[str]:
    """The fills of the boxes that hold `point`, the last drawn first."""
    return [fill for fill, _, _ in holding(point, boxes)]


def holds(owner: str, end: str) -> bool:
    """Whether the element whose trace id is `owner` is the element `end`, or holds it:
    a trace id is the path of instances, parts and items that lead to an element."""
    return end == owner or end.startswith(f"{owner}/")


@pytest.mark.parametrize("language", LANGUAGES)
def test_a_connectors_line_reaches_3_to_1_against_what_it_lies_on_in_every_mode(
    scenes: Mapping[tuple[str, str], Mapping[str, Any]],
    resolved: Mapping[str, tuple[Mapping[str, Any], list[str]]],
    language: str,
) -> None:
    """A connector's line is a mark nothing beside it shows, so it needs WCAG's contrast
    for marks against the fill under it (WCAG 2.1, 1.4.11), in each mode of the test
    brand, at every point of its route."""
    measured = 0
    for (piece, lang), scene in scenes.items():
        if lang != language:
            continue
        values, keys = resolved[piece]
        assert len(keys) == COMBINATIONS, (piece, keys)
        for page in [each for each in elements(scene) if each.get("page")]:
            for line, route, boxes in connector_lines(page):
                assert str(line["stroke"]).startswith("family."), (piece, line["id"])
                grounds = {under(point, boxes)[0] for point in inside(route)}
                for ground in grounds:
                    for key in keys:
                        ratio = tokens.contrast_ratio(
                            values[line["stroke"]][key], values[ground][key]
                        )
                        assert ratio >= tokens.LEVELS["marks"], (
                            piece,
                            line["id"],
                            ground,
                            key,
                            round(ratio, 2),
                        )
                        measured += 1
    assert measured > 0


@pytest.mark.parametrize("language", LANGUAGES)
def test_a_connector_crosses_no_item_but_its_ends(
    scenes: Mapping[tuple[str, str], Mapping[str, Any]], language: str
) -> None:
    """The connector routes around nothing, so each reference render places its items
    where a tie's line, short of its ends, lies only on the page's background and on the
    boxes of what holds an end, such as the group whose item a tie reaches."""
    checked = 0
    for (piece, lang), scene in scenes.items():
        if lang != language:
            continue
        for page in [each for each in elements(scene) if each.get("page")]:
            for line, route, boxes in connector_lines(page):
                ends = [str(line["attached"][end]["id"]) for end in ("start", "end")]
                for point in inside(route):
                    crossed = [
                        box_id
                        for _, _, box_id in holding(point, boxes)
                        if not any(holds(box_id.rpartition("/")[0], end) for end in ends)
                    ]
                    assert crossed == [], (piece, line["id"], point)
                    assert under(point, boxes)[-1] == "background", (piece, line["id"], point)
                checked += 1
    assert checked > 0


@pytest.mark.parametrize("language", LANGUAGES)
def test_a_strong_run_keeps_the_size_and_line_height_of_a_plain_run(
    scenes: Mapping[tuple[str, str], Mapping[str, Any]],
    resolved: Mapping[str, tuple[Mapping[str, Any], list[str]]],
    language: str,
) -> None:
    """A strong run of a card's text stands out by its weight alone, so it never breaks
    the line it lies in: its size and its line height are a plain run's, in each mode."""
    roles = {word: role for role, word in styled_runs(COMPONENTS["card"])["text"].items()}
    checked = 0
    for (piece, lang), scene in scenes.items():
        if lang != language:
            continue
        values, keys = resolved[piece]
        for key in keys:
            plain, strong = values[roles["plain"]][key], values[roles["strong"]][key]
            assert strong["fontSize"] == plain["fontSize"], (piece, key)
            assert strong["lineHeight"] == plain["lineHeight"], (piece, key)
            assert strong["fontWeight"] > plain["fontWeight"], (piece, key)
        plain_size = float(values[roles["plain"]]["default"]["fontSize"]["value"])
        plain_height = plain_size * float(values[roles["plain"]]["default"]["lineHeight"])
        for element in elements(scene):
            runs = [run for paragraph in element.get("paragraphs", []) for run in paragraph]
            if not any(run["style"] == roles["strong"] for run in runs):
                continue
            for run in runs:
                assert run["font-size"] == plain_size, (piece, element["id"], run["text"])
            assert element["line-height"] == pytest.approx(plain_height), (piece, element["id"])
            checked += 1
    assert checked > 0


# --- the README --------------------------------------------------------------------------------


def test_the_readme_names_what_the_components_declare() -> None:
    text = README.read_text(encoding="utf-8")
    named = set(re.findall(r"`([^`\s]+)`", text))
    for name, component in COMPONENTS.items():
        expected = {name}
        for option, words in {**options(component), **run_words(component)}.items():
            expected |= {option, *words}
        for listed, declared in (component.get("lists") or {}).items():
            expected |= {listed, declared["component"], *declared.get("ends", [])}
            for field, arrangement in (declared.get("arrangement") or {}).items():
                expected |= {field, *arrangement["words"]}
        assert expected <= named, (name, sorted(expected - named))
    assert set(OWN) <= named, sorted(set(OWN) - named)


# --- patterns that compose, and the code block -------------------------------------------------

#: The starter's patterns, as the README heads each, by its name and the question it answers.
PATTERNS = set(re.findall(r"^### `([a-z-]+)`: ", README.read_text(encoding="utf-8"), re.MULTILINE))
#: The weight on a panel, its words and the share each gives.
SPAN = COMPONENTS["panels"]["lists"]["panels"]["arrangement"]["span"]
#: How far a drawn length may stray from what it should be, for rounding.
EPSILON = 1e-6
#: How far a place on the page, summed from frames each rounded to 1/100 px, may stray.
ROUNDING = 0.02


def by_id(scene: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    """Each element of a scene that carries a trace id, by its trace id."""
    return {str(element["id"]): element for element in elements(scene) if "id" in element}


def ancestors(trace_id: str) -> list[str]:
    """The trace ids of what holds the element `trace_id`, the outermost first."""
    steps = trace_id.split("/")
    return ["/".join(steps[:count]) for count in range(1, len(steps))]


def content_at(content: Any, trace_id: str) -> Any:
    """What a content file holds for the element `trace_id`, where each step of the trace id
    after the top's is a field of the content, or an item of a list by its id."""
    return at_source(content, ".".join(trace_id.split("/")[1:]))


def is_pattern(element: Mapping[str, Any]) -> bool:
    component = str(element.get("component", ""))
    return component.startswith("starter/") and component.removeprefix("starter/") in PATTERNS


def within(inner: tuple[float, ...], outer: tuple[float, ...]) -> bool:
    return (
        outer[0] - EPSILON <= inner[0]
        and outer[1] - EPSILON <= inner[1]
        and inner[2] <= outer[2] + EPSILON
        and inner[3] <= outer[3] + EPSILON
    )


@pytest.mark.parametrize("language", LANGUAGES)
def test_a_networks_ties_reach_the_items_its_groups_draw_by_their_key_paths(
    scenes: Mapping[tuple[str, str], Mapping[str, Any]], language: str
) -> None:
    """Each tie of a network ends at the item its end fields' key paths name (DEC-011
    point 3), among them items that a group draws inside a pattern in one of its columns."""
    in_groups = 0
    for (piece, lang), scene in scenes.items():
        if lang != language:
            continue
        content = read(PIECES / piece / f"content.{lang}.yaml")
        drawn = by_id(scene)
        for network, element in drawn.items():
            if element.get("component") != "starter/network":
                continue
            for tie in content_at(content, network).get("ties", []):
                [line] = [
                    each
                    for each in elements(drawn[f"{network}/ties[{tie['id']}]"])
                    if each.get("attached")
                ]
                for field, end in (("from", "start"), ("to", "end")):
                    reached = str(line["attached"][end]["id"])
                    named = f"{network}/{tie[field]['item'].replace('.', '/')}"
                    assert reached == named, (piece, tie["id"], field)
                    owners = [drawn[owner].get("component") for owner in ancestors(reached)]
                    in_groups += "starter/group" in owners
    assert in_groups > 0


@pytest.mark.parametrize("name", sorted(COMPONENTS))
def test_no_part_passes_a_field_of_runs_on_to_a_component_it_places(name: str) -> None:
    """A field of runs is drawn by a text part of the component that declares it (DEC-012
    point 8), as the code block shows a terminal's line with a text part of its own."""
    component = COMPONENTS[name]
    runs = set(run_words(component))
    for part, value in component["parts"].items():
        passed = set((value.get("fields") or {}).values()) & runs
        assert passed == set(), (name, part, sorted(passed))
    for field in runs:
        assert [
            part
            for part in component["parts"].values()
            if (part.get("text") or {}).get("content") == field
        ], (name, field)


@pytest.mark.parametrize("language", LANGUAGES)
def test_a_pattern_placed_inside_another_draws_within_it_with_no_overflow(
    scenes: Mapping[tuple[str, str], Mapping[str, Any]], language: str
) -> None:
    """A network holds a pattern of groups, and panels hold a network and panels of their
    own. Each is drawn with no finding (the `scenes` fixture), each of its elements within
    its frame, and each of its texts' lines within the text's own."""
    nested = 0
    for (piece, lang), scene in scenes.items():
        if lang != language:
            continue
        for page in [each for each in elements(scene) if each.get("page")]:
            placed = {str(element["id"]): (element, frame) for element, frame in frames(page)}
            for trace_id, (element, frame) in placed.items():
                outer = [
                    owner
                    for owner in ancestors(trace_id)
                    if owner in placed and is_pattern(placed[owner][0])
                ]
                if not is_pattern(element) or not outer:
                    continue
                nested += 1
                assert within(frame, placed[outer[-1]][1]), (piece, trace_id)
                left, top = frame[0] - element["x"], frame[1] - element["y"]
                for inner, inner_frame in frames(element, left, top):
                    assert within(inner_frame, frame), (piece, inner["id"])
                    for line in inner.get("lines", []):
                        assert line["width"] <= inner["width"] + EPSILON, (piece, inner["id"])
                    measured = inner.get("measured-height", 0.0)
                    assert measured <= inner["height"] + EPSILON, (piece, inner["id"])
    assert nested > 0


@pytest.mark.parametrize("language", LANGUAGES)
def test_a_panels_span_gives_it_its_share_of_the_row(
    scenes: Mapping[tuple[str, str], Mapping[str, Any]], language: str
) -> None:
    """Each panel's width is in proportion to the share its span's word gives it (DEC-010
    point 4), so a wide panel is half as wide again as a normal one. Each word is drawn."""
    spans: set[str] = set()
    for (piece, lang), scene in scenes.items():
        if lang != language:
            continue
        content = read(PIECES / piece / f"content.{lang}.yaml")
        drawn = by_id(scene)
        for trace_id, element in drawn.items():
            if element.get("component") != "starter/panels":
                continue
            widths = []
            for panel in content_at(content, trace_id)["panels"]:
                word = panel.get("span", SPAN["words"][0])
                spans.add(word)
                width = drawn[f"{trace_id}/panels[{panel['id']}]"]["width"]
                widths.append(width / SPAN["shares"][word])
            assert max(widths) == pytest.approx(min(widths)), (piece, trace_id, widths)
    assert spans == set(SPAN["words"])


@pytest.mark.parametrize("language", LANGUAGES)
def test_the_panels_of_a_row_end_on_one_edge_when_one_holds_panels_of_its_own(
    scenes: Mapping[tuple[str, str], Mapping[str, Any]], language: str
) -> None:
    """Each panel is as tall as the tallest, and one that holds panels of its own passes
    that height down to the part it draws last (`components.md`, *What an element asks
    for, and what it gets*). So in a row where a panel holds panels, the lowest box each
    panel draws ends at the row's height. In one such row, the panels within ask for less
    than the row, and their last part takes the rest, its height the engine's."""
    stretched = 0
    for (piece, lang), scene in scenes.items():
        if lang != language:
            continue
        for page in [each for each in elements(scene) if each.get("page")]:
            for element, frame in frames(page):
                if element.get("component") != "starter/panels":
                    continue
                [row] = [each for each in element["children"] if each["id"].endswith("/panels")]
                holding = [
                    each for each in row["children"] if each.get("component") == "starter/panels"
                ]
                if not holding:
                    continue
                left, top = frame[0] + row["x"], frame[1] + row["y"]
                for panel in row["children"]:
                    bottoms = [
                        box[3] for each, box in frames(panel, left, top) if each["type"] == "box"
                    ]
                    edge = top + row["height"]
                    assert max(bottoms) == pytest.approx(edge, abs=ROUNDING), (piece, panel["id"])
                for panel in holding:
                    last = panel["children"][-1]
                    stretched += "component" in last and last["sources"]["height"] == "engine"
    assert stretched > 0


@pytest.mark.parametrize("language", LANGUAGES)
def test_a_code_blocks_lines_stand_as_written(
    scenes: Mapping[tuple[str, str], Mapping[str, Any]], language: str
) -> None:
    """A code block's text takes no width, so no line of it breaks: each paragraph is one
    line, and the block is wider than its widest."""
    checked = 0
    for (piece, lang), scene in scenes.items():
        if lang != language:
            continue
        for element in elements(scene):
            if element.get("component") != "starter/code":
                continue
            [text] = [each for each in element["children"] if each["id"] == f"{element['id']}/text"]
            paragraphs = [line["paragraph"] for line in text["lines"]]
            assert paragraphs == list(range(len(text["paragraphs"]))), (piece, text["id"])
            widest = max(line["width"] for line in text["lines"])
            assert text["x"] + widest < element["width"], (piece, text["id"])
            checked += 1
    assert checked > 0


#: The bar a brand gives the starter in the test below, thicker than the starter's inset.
THICK_BAR = 24.0
#: The parts of a card that hold what its content gives.
HELD_BY_A_CARD = ("head", "tag", "text")


@pytest.fixture(scope="module")
def thick_bars(location: Path, tmp_path_factory: pytest.TempPathFactory) -> list[Mapping[str, Any]]:
    """The card's reference piece, in each language, under a copy of the test brand that
    names the starter and gives its bar a value of its own (DEC-008 point 4)."""
    root = tmp_path_factory.mktemp("thick-bars") / "project"
    shutil.copytree(location, root)
    brand = version_folder(root, "test-brand", "1.0.0")
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
    bar = {"$value": {"value": THICK_BAR, "unit": "px"}}
    given["starter"] = {"$type": "dimension", "bar": bar}
    base.write_text(json.dumps(given), encoding="utf-8")
    piece = pl.read_piece(root, "visual", "card")
    drawn = pl.Project(piece, piece.lock, pl.Held(root, "visual"))
    computed = []
    for _, result in drawn.scenes(facts=drawn.piece.stand_ins):
        assert result.findings == []
        computed.append(result.scene.to_dict())
    return computed


def space_2(drawn: Any) -> float:
    """The gap the shared role `space.2` gives, in px, under what `drawn` draws with."""
    return float(drawn.env.role("space.2")["value"])


def rows_of_cards(
    scene: Mapping[str, Any],
) -> Iterator[list[tuple[str, dict[str, tuple[float, float, float, float]]]]]:
    """Each row of cards a scene draws: for each card, its bar's word and the frame on its
    page of each of its parts, by the part's name."""
    for page in [each for each in elements(scene) if each.get("page")]:
        placed = list(frames(page))
        rows: dict[str, list[tuple[str, dict[str, tuple[float, float, float, float]]]]] = {}
        for card, _ in placed:
            if card.get("component") != "starter/card":
                continue
            prefix = f"{card['id']}/"
            parts = {
                str(element["id"]).removeprefix(prefix): frame
                for element, frame in placed
                if str(element["id"]).startswith(prefix)
            }
            row = rows.setdefault(ancestors(str(card["id"]))[-1], [])
            row.append((card["options"]["bar"], parts))
        yield from rows.values()


def assert_heads_stand_at_one_height(scene: Mapping[str, Any]) -> None:
    """That the heads of each row of `scene`'s cards share one height, and that one row
    draws every word of the card's bar."""
    words = []
    for row in rows_of_cards(scene):
        heads = [(bar, parts["head"][1]) for bar, parts in row if "head" in parts]
        assert len({top for _, top in heads}) <= 1, heads
        words.append({bar for bar, _ in heads})
    assert set(COMPONENTS["card"]["options"]["bar"]) in words


def gaps_below_top_bars(scene: Mapping[str, Any]) -> Iterator[float]:
    """For each card of `scene` with a top bar, how far below the bar what it holds starts."""
    for row in rows_of_cards(scene):
        for bar, parts in row:
            if bar == "top":
                held = [frame[1] for name, frame in parts.items() if name in HELD_BY_A_CARD]
                yield min(held) - parts["bar-top"][3]


@pytest.mark.parametrize("language", LANGUAGES)
def test_a_row_of_cards_keeps_its_heads_at_one_height_whichever_bar_each_has(
    scenes: Mapping[tuple[str, str], Mapping[str, Any]], language: str
) -> None:
    assert_heads_stand_at_one_height(scenes[("card", language)])


@pytest.mark.parametrize("language", LANGUAGES)
def test_what_a_card_holds_clears_its_top_bar(
    scenes: Mapping[tuple[str, str], Mapping[str, Any]],
    projects: Mapping[str, Any],
    language: str,
) -> None:
    """A card with no head starts its tag or its text there, as the list's cards do."""
    gaps = [
        gap
        for (_, lang), scene in scenes.items()
        if lang == language
        for gap in gaps_below_top_bars(scene)
    ]
    assert gaps and min(gaps) >= space_2(projects["card"]) - EPSILON


def test_a_bar_thicker_than_the_inset_stays_clear_of_every_head_at_one_height(
    thick_bars: list[Mapping[str, Any]], projects: Mapping[str, Any]
) -> None:
    """A brand may give the bar any value, and the heads still line up below it."""
    for scene in thick_bars:
        assert_heads_stand_at_one_height(scene)
        gaps = list(gaps_below_top_bars(scene))
        assert gaps and min(gaps) >= space_2(projects["card"]) - EPSILON
