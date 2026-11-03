"""The starter, the component library the capability ships to start from (visual-communication
DEC-007): `pkit visual add starter` copies and lists it; every role of its own ends, along
its defaults, at a shared role (DEC-008 point 2); each pattern declares a component field
for each list it repeats (DEC-010, Implications); it holds no raw value; and each
component's reference renders, under the test brand, pass the check and draw each word of
each option and of each field of runs (DEC-007 point 3). A run that reads a colour family
lies on that family's fill (`components.md`, *Values, states and colour*). The README
names what the components declare.

The reference renders are the pieces under `tests/fixtures/visual-communication/starter/`,
one for each component, drawn in English and in German. Run in this process
(`tests/in_process.py`); it starts no `pkit`."""

from __future__ import annotations

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
    project,
    write_list,
)

add, checks, pl, reading = load("visual-communication", "add.py", "checks", "pipeline", "reading")

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
    root = project(tmp_path)
    added = run_main(add, "starter", cwd=root)
    assert added.returncode == 0, added.stderr
    assert files_of(root / "visual" / "libraries" / "starter" / "1.0.0") == files_of(STARTER)
    listed = read(root / "visual" / "libraries" / "libraries.yaml")
    assert listed == bound(
        "libraries",
        libraries={"starter": {"source": {"kind": "shipped"}, "versions": UNRELEASED}},
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
    """A location that holds the foundations and the starter as the capability ships them,
    the test brand and the test notation, and the starter's reference pieces."""
    root = project(tmp_path_factory.mktemp("starter"))
    copy_library(root, FOUNDATIONS, "foundations", "1.0.0")
    copy_library(root, STARTER, "starter", "1.0.0")
    copy_library(root, TEST_BRAND, "test-brand", "1.0.0")
    copy_library(root, TEST_NOTATION, "test-notation", "1.0.0")
    write_list(
        root,
        {
            "foundations": {"source": {"kind": "shipped"}, "versions": UNRELEASED},
            "starter": {"source": {"kind": "shipped"}, "versions": UNRELEASED},
            "test-brand": {"source": {"kind": "project"}, "versions": UNRELEASED},
            "test-notation": {"source": {"kind": "project"}, "versions": UNRELEASED},
        },
    )
    shutil.copytree(PIECES, root / "visual" / "pieces")
    return root


@pytest.fixture(scope="module")
def scenes(location: Path) -> dict[tuple[str, str], Mapping[str, Any]]:
    """The scene of each reference piece in each language, by piece and language."""
    computed = {}
    for piece_folder in sorted(PIECES.iterdir()):
        piece = pl.read_piece(location, "visual", piece_folder.name)
        drawn = pl.Project(piece, piece.lock, pl.Held(location, "visual"))
        for language, result in drawn.scenes():
            assert result.findings == [], (piece_folder.name, language, result.findings)
            computed[(piece_folder.name, language)] = result.scene.to_dict()
    return computed


def test_each_component_has_its_reference_piece_pinned_with_the_test_brand() -> None:
    assert sorted(path.name for path in PIECES.iterdir()) == sorted(COMPONENTS)
    for folder in PIECES.iterdir():
        piece = read(folder / "piece.yaml")
        assert piece["brand"] == "test-brand"
        assert piece["pinned"] is True
        assert piece["languages"] == LANGUAGES
        assert piece["lock"]["starter"] == "1.0.0"


def test_every_reference_piece_passes_the_check_under_the_test_brand(location: Path) -> None:
    report = checks.check(location)
    found = [
        (level, finding.code, finding.file, finding.message)
        for finding, level in report.judged
        if finding.code != "component-experimental"
    ]
    assert found == []
    assert not report.failed()
    assert report.summary == [
        f"{len(COMPONENTS)} piece(s) in `visual`: the scenes of 0 read from their findings "
        f"record, of {len(COMPONENTS)} computed now, of 0 not checked."
    ]


def elements(element: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    yield element
    for child in element.get("children", []):
        yield from elements(child)


def drawn_words(
    scenes: Mapping[tuple[str, str], Mapping[str, Any]], language: str
) -> dict[tuple[str, str], set[str]]:
    """The words each option, and each field of runs, of each starter component took in
    the scenes of `language`. A run's word is read from the role its style took."""
    words: dict[tuple[str, str], set[str]] = {}
    for (_, lang), scene in scenes.items():
        if lang != language:
            continue
        for element in elements(scene):
            component = str(element.get("component", ""))
            if not component.startswith("starter/"):
                continue
            name = component.removeprefix("starter/")
            for option, word in (element.get("options") or {}).items():
                words.setdefault((name, option), set()).add(word)
            for field, by_style in styled_runs(COMPONENTS[name]).items():
                for child in element.get("children", []):
                    if child["id"] != f"{element['id']}/{field}":
                        continue
                    for paragraph in child["paragraphs"]:
                        for run in paragraph:
                            words.setdefault((name, field), set()).add(by_style[run["style"]])
    return words


def styled_runs(component: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    """For each field of runs, the run word each typography role its text part's style
    switch gives stands for. Each word takes a role of its own."""
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
        assert expected <= named, (name, sorted(expected - named))
    assert set(OWN) <= named, sorted(set(OWN) - named)
