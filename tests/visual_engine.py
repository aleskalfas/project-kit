"""The visual-communication engine in the test's own process, and the in-memory `Env` its
tests read through (#2428).

The engine reads every component, role, colour family, concept, font and produced picture
through one protocol, `Env` (`_lib/env.py`). Its tests stand in for it with `FakeEnv`,
never with the data layer's modules: components come from the test library's and the
foundations' files (read with ruamel's safe loader) or from mappings a test writes, roles
from a mapping of resolved DTCG values, colour families and concepts from mappings a test
writes, the font from the test brand's committed Source Sans Pro, and produced pictures
from `PictureInfo`s. A component a test needs broken is a mapping in
memory, never a file: the repository's validation reads every bound YAML file under
`tests/`.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from tests.in_process import REPO, load

env, formula, layout, text, scene = load(
    "visual-communication", "env", "formula", "layout", "text", "scene"
)

FIXTURES = REPO / "tests" / "fixtures" / "visual-communication" / "libraries"
TESTS_LIBRARY = FIXTURES / "tests" / "1.0.0"
FOUNDATIONS = REPO / ".pkit" / "capabilities" / "visual-communication" / "libraries" / "foundations"
FONT = FIXTURES / "test-brand" / "1.0.0" / "fonts" / "SourceSansPro-Regular.otf"
FAMILY = "Source Sans Pro"

#: The library versions a fake lock names.
VERSIONS = {"foundations": "1.0.0", "tests": "1.0.0", "lab": "1.0.0"}


def _px(value: float) -> dict[str, Any]:
    return {"value": value, "unit": "px"}


#: The roles the test brand resolves, at the scene's size combination.
ROLES: dict[str, Any] = {
    "space.1": _px(4),
    "space.2": _px(8),
    "space.3": _px(16),
    "space.4": _px(32),
    "stroke.thin": _px(1),
    "size.figure": _px(640),
    "size.slide": _px(1280),
    "font.body": [FAMILY],
    "type.body": {
        "fontFamily": [FAMILY],
        "fontSize": _px(16),
        "fontWeight": 400,
        "letterSpacing": _px(0),
        "lineHeight": 1.4,
    },
    # Measured with the body's one file, which measures every weight of its family.
    "type.heading": {
        "fontFamily": [FAMILY],
        "fontSize": _px(24),
        "fontWeight": 600,
        "letterSpacing": _px(0),
        "lineHeight": 1.2,
    },
}


def read_components() -> dict[str, dict[str, Any]]:
    """The test library's components and the foundations', by their use."""
    reader = YAML(typ="safe", pure=True)
    found = {}
    for library, folder in (("tests", TESTS_LIBRARY), ("foundations", FOUNDATIONS)):
        for path in sorted((folder / "components").glob("*.yaml")):
            found[f"{library}/{path.stem}"] = reader.load(path.read_text(encoding="utf-8"))
    return found


COMPONENTS = read_components()


def square(tip: tuple[float, float] = (75, 25), size: int = 100) -> Any:
    """A produced output in two variants of one pixel size, with one exposed point."""
    keys = ("colour-scheme.dark", "default")
    return env.PictureInfo(
        variants={
            key: {"file": f"{key}.png", "pixels": {"width": size, "height": size}} for key in keys
        },
        points={"tip": {key: {"x": tip[0], "y": tip[1]} for key in keys}},
    )


class FakeEnv:
    """An `Env` in memory. Each argument adds to, or replaces, the defaults. Its colour
    families are none unless `families` gives them, and its concepts none unless
    `concepts` gives them: each `<notation>/<concept>` mapped to its family, or to None for
    a concept its notation cannot read. A notation the piece names is one a concept of
    `concepts` comes from."""

    def __init__(
        self,
        components: Mapping[str, Any] | None = None,
        roles: Mapping[str, Any] | None = None,
        fonts: Mapping[str, Path] | None = None,
        pictures: Mapping[str, Any] | None = None,
        families: Mapping[str, Mapping[str, str]] | None = None,
        concepts: Mapping[str, str | None] | None = None,
    ) -> None:
        self.components = {**COMPONENTS, **(components or {})}
        self.roles = {**ROLES, **(roles or {})}
        self.fonts = {FAMILY: FONT} if fonts is None else dict(fonts)
        self.pictures = {"square": square()} if pictures is None else dict(pictures)
        self.families = {name: dict(members) for name, members in (families or {}).items()}
        self.concepts = dict(concepts or {})
        self.asked: list[str] = []

    def component(self, use: str) -> dict:
        self.asked.append(f"component {use}")
        return self.components[use]

    def role(self, token_path: str) -> dict:
        self.asked.append(f"role {token_path}")
        return self.roles[token_path]

    def font_file(self, family: str) -> Path:
        self.asked.append(f"font {family}")
        if family not in self.fonts:
            raise env.MissingFont(f"the font family {family!r} has no committed file")
        return self.fonts[family]

    def picture(self, output: str) -> Any:
        self.asked.append(f"picture {output}")
        return self.pictures[output]

    def family(self, name: str) -> dict[str, str]:
        self.asked.append(f"family {name}")
        return self.families[name]

    def concept(self, name: str) -> str | None:
        self.asked.append(f"concept {name}")
        if name in self.concepts:
            return self.concepts[name]
        notation, _, concept = name.partition("/")
        if any(known.partition("/")[0] == notation for known in self.concepts):
            raise env.UnknownConcept(
                name, f"the notation `{notation}` holds no concept `{concept}`"
            )
        raise env.UnknownConcept(name, f"the piece names no notation `{notation}`")

    def library_version(self, library: str) -> str:
        return VERSIONS[library]


def top(parts: Mapping[str, Any], **keys: Any) -> dict[str, Any]:
    """A top component of one page drawing `parts`, as wide as the figure role; `keys`
    add to it or replace its defaults."""
    return {
        "status": "experimental",
        "about": "A top component a test draws.",
        "fields": {"type": "object", "properties": keys.pop("fields", {})},
        "layouts": {"frame": {"slots": {}}},
        "parts": dict(parts),
        "preferred": {"width": "=@size.figure", "height": "=@space.4"},
        **keys,
    }


def block(parts: Mapping[str, Any], **keys: Any) -> dict[str, Any]:
    """A component that is no top component."""
    component = top(parts, **keys)
    del component["layouts"]
    return component


def draw(
    content: Mapping[str, Any] | None = None,
    *,
    use: str = "lab/top",
    language: str = "en",
    **environment: Any,
) -> Any:
    """The scene of a piece whose top is `use`, and its findings."""
    return scene.compute_scene(
        piece="test-piece",
        top=use,
        content=dict(content or {}),
        language=language,
        lock=dict(VERSIONS),
        size_key="default",
        seam_version=1,
        env=FakeEnv(**environment),
    )


def frame(result: Any, trace: str) -> tuple[float, float, float, float]:
    """An element's frame in a scene: x, y, width, height."""
    element = result.scene.find(trace)
    assert element is not None, f"no element {trace}"
    props = element.properties
    return props["x"], props["y"], props["width"], props["height"]


def codes(result: Any) -> list[str]:
    """The codes of a scene's findings, in the order found."""
    return [finding.code for finding in result.findings]
