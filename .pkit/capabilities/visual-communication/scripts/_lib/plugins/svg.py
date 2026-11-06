"""The SVG renderer: a scene drawn as SVG files, one for each page, language and
combination of modes (visual-communication DEC-005 points 4, 5, 9 and 10).

- **What it draws** is its declaration (`svg_declaration.py`): every primitive of format
  1's scene but the path. It draws only what it declares, so the losses the capability
  reads from the declaration before it runs are the ones it makes.
- **How it draws** is the canvas's (`_lib/canvas.py`), with nothing replaced.

Output is fixed for a version: the same scene and values give the same bytes. A change that
could give another output, here or in the canvas, raises the version, and the reference
outputs pinned to it in the tests catch one made without it (DEC-005 point 9).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _lib.canvas import Canvas
from _lib.plugins import seam
from _lib.plugins.svg_declaration import DECLARATION

NAME: str = DECLARATION["name"]
VERSION: str = DECLARATION["version"]


@dataclass(frozen=True)
class Page:
    """One page drawn: its trace id and its SVG text."""

    id: str
    svg: str


@dataclass(frozen=True)
class Drawn:
    """What one scene drawn in one combination gives: its pages, and what the renderer
    could not draw as given."""

    pages: list[Page]
    losses: list[seam.Loss]


def render(
    scene: Mapping[str, Any],
    *,
    key: str,
    colours: Mapping[str, Mapping[str, Any]],
    font_file: Callable[[str], Path],
    pictures: Mapping[str, Path],
) -> Drawn:
    """`scene` (`Scene.to_dict()`) drawn in the combination `key`: `colours` gives each
    colour role's value there, in canonical form; `font_file` the committed file of a font
    family; `pictures` the file of each produced output's variant that serves `key`."""
    canvas = Canvas(DECLARATION, scene, key, colours, font_file, pictures)
    pages = []
    for trace in scene.get("pages", []):
        element = _find(scene.get("children", []), trace)
        if element is not None:
            pages.append(Page(trace, canvas.page(element)))
    return Drawn(pages, canvas.losses)


def _find(elements: list[Mapping[str, Any]], trace: str) -> Mapping[str, Any] | None:
    stack = list(reversed(elements))
    while stack:
        element = stack.pop()
        if element.get("id") == trace:
            return element
        stack.extend(reversed(element.get("children", [])))
    return None
