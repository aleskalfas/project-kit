"""The seam between the engine and its plugins (visual-communication DEC-005 points 8, 9 and 12).

What the engine hands its plugins and takes back: the scene or the values
document, each plugin's declaration, and the loss report. The seam's version
rises only when a plugin must read something differently; the engine refuses a
plugin that does not read the version it writes.

Three kinds of plugin meet here: a *renderer* draws a scene in one medium, a
*producer* makes a picture while a piece is prepared, and a *code writer* writes
a brand's resolved values as code. Each has a version of its own, apart from the
capability's, which rises when the same input could give another output.

A declaration is plain data, read with the standard library alone, so the check
knows what each plugin takes without importing it (or its dependencies). The
implementation is imported only when the plugin runs. Every plugin is the
capability's (DEC-005 point 12): the registry holds the shipped plugins, and a
test may add one in its own process through `register`; no file, setting or
environment variable adds one.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: 2 since a scene's text holds paragraphs of runs, each with its own role, paint and fonts,
#: and each line its own baseline and spans (visual-communication DEC-012). 3 since a line
#: may hold arrowheads, and a tie's connector the points of its route and the elements its
#: ends meet (visual-communication DEC-011). 4 since a renderer of a format that holds modes
#: is handed every key of one file in one call, and its loss in one of them names that key
#: (visual-communication DEC-023 point 2). 5 since an image shows a produced output, a
#: picture file or a picture role, and a renderer is handed the picture each image shows
#: in each combination, a PNG or a JPEG, by the image's trace id (`Shown`,
#: visual-communication DEC-025 point 7). 6 since the scene's root holds the physical size of
#: the piece's top, which a renderer whose format has a physical page maps each page onto
#: (visual-communication DEC-034 point 3).
SEAM_VERSION = 6

RENDERER = "renderer"
PRODUCER = "producer"
CODE_WRITER = "code-writer"
KINDS = (RENDERER, PRODUCER, CODE_WRITER)

# What a plugin did with what it could not take as given (DEC-005 point 9).
APPROXIMATED = "approximated"
PICTURE = "picture"
LEFT_OUT = "left-out"
REFUSED = "refused"
OUTCOMES = (APPROXIMATED, PICTURE, LEFT_OUT, REFUSED)


@dataclass(frozen=True)
class Loss:
    """One loss, in the one form every plugin reports.

    - `plugin`: the plugin's name.
    - `what`: what was lost, by trace id or token path.
    - `did`: what the plugin did instead, one of `OUTCOMES`.
    - `why`: why, in plain words.
    - `key`: the key of the one combination it holds in, where a renderer's file holds
      several (DEC-023 point 8); None for every other loss, which no field adds.
    """

    plugin: str
    what: str
    did: str
    why: str
    key: str | None = None

    def __post_init__(self) -> None:
        if self.did not in OUTCOMES:
            raise ValueError(f"unknown outcome {self.did!r}")

    def as_dict(self) -> dict[str, str]:
        held = {"plugin": self.plugin, "what": self.what, "did": self.did, "why": self.why}
        return held if self.key is None else {**held, "key": self.key}


#: The kinds of picture a renderer is handed, as the picture reader names them.
PNG = "png"
JPEG = "jpeg"
PICTURE_KINDS = (PNG, JPEG)


@dataclass(frozen=True)
class Shown:
    """The picture an image shows in one combination, as a renderer is handed it (DEC-025
    point 7): the file to draw, and its kind, `png` or `jpeg`. The engine resolves every image
    to one, whatever its source, so a renderer draws each alike and reads nothing else for
    it: a produced output's variant that serves the combination, a picture file of the piece
    or of a library's version, or the file a brand gives a picture role there.

    A renderer is handed them by the image's trace id. One handed none draws the image as
    missing, and reports the loss. The file's bytes are drawn as they are, so a colour
    profile the file carries stays with the picture."""

    file: Path
    kind: str

    def __post_init__(self) -> None:
        if self.kind not in PICTURE_KINDS:
            raise ValueError(f"unknown kind of picture {self.kind!r}")


class PluginError(Exception):
    """A plugin the seam cannot run: unknown, of another seam version, or of the wrong kind."""


# The shipped plugins' declarations. Each names the module under `_lib.plugins`
# that holds its implementation, imported only when it runs. The renderers and
# code writers add their entries here as they ship.
_SHIPPED: dict[str, dict[str, Any]] = {}

# Plugins a test registers in its own process, with their implementation object.
_REGISTERED: dict[str, tuple[dict[str, Any], Any]] = {}


def ship(declaration: dict[str, Any]) -> None:
    """Add a shipped plugin's declaration (called by `_lib.plugins.__init__` only)."""
    _check(declaration)
    _SHIPPED[declaration["name"]] = declaration


def register(declaration: dict[str, Any], implementation: Any) -> None:
    """Add a plugin in this process alone, as the capability's tests do."""
    _check(declaration)
    _REGISTERED[declaration["name"]] = (declaration, implementation)


def unregister(name: str) -> None:
    """Take back a plugin a test registered."""
    _REGISTERED.pop(name, None)


def declaration(name: str, kind: str | None = None) -> dict[str, Any]:
    """The declaration of the plugin `name`, of `kind` when given; raises PluginError."""
    if name in _REGISTERED:
        found = _REGISTERED[name][0]
    elif name in _SHIPPED:
        found = _SHIPPED[name]
    else:
        raise PluginError(
            f"no plugin named {name!r}; the capability ships "
            f"{', '.join(sorted(_SHIPPED)) or 'none'}"
        )
    if kind is not None and found["kind"] != kind:
        raise PluginError(f"plugin {name!r} is a {found['kind']}, not a {kind}")
    return found


def implementation(name: str) -> Any:
    """The plugin's implementation, imported now; raises PluginError."""
    if name in _REGISTERED:
        return _REGISTERED[name][1]
    found = declaration(name)
    return importlib.import_module(f"_lib.plugins.{found['module']}")


def names(kind: str | None = None) -> list[str]:
    """The plugins known in this process, of `kind` when given, sorted."""
    every = {**_SHIPPED, **{n: d for n, (d, _) in _REGISTERED.items()}}
    return sorted(n for n, d in every.items() if kind is None or d["kind"] == kind)


def _check(found: dict[str, Any]) -> None:
    for key in ("name", "kind", "version", "seam"):
        if key not in found:
            raise PluginError(f"a plugin's declaration lacks {key!r}")
    if found["kind"] not in KINDS:
        raise PluginError(f"plugin {found['name']!r} has an unknown kind {found['kind']!r}")
    if found["seam"] != SEAM_VERSION:
        raise PluginError(
            f"plugin {found['name']!r} reads seam version {found['seam']}; "
            f"the engine writes {SEAM_VERSION}"
        )
