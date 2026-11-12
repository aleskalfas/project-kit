"""What the SVG renderer draws: its declaration, plain data (visual-communication DEC-005
points 9 and 10, DEC-018 points 1 and 4).

A renderer declares, for each primitive and each property of the scene, whether it draws
it, updates it in place, recreates it, or reads it back. The SVG renderer writes files, so
it draws, and only draws: it updates nothing in place and reads nothing back. A primitive
or a property it does not name here is a loss the capability knows before it runs: a
primitive it refuses, a property it leaves out. It draws in the default font profile,
from the brand's committed font files, calls no outside program and reaches no service.

It draws two formats. `svg` is a file for each page, language and combination, read as one
chosen mode. `svg-modes` is a *switching file* for each page, language and set of
combinations that share one, which a page shows as any image (DEC-018 point 1).

- `holds-modes`: the format that holds several modes in one file, with the signal pairs it
  reads (DEC-018 point 4, DEC-023 point 5): the colour scheme's alone, since what a browser
  tells an image carries `prefers-color-scheme`, and a test saw `prefers-contrast` reach none.
  Each mode of the axis has its pair, the default's first, so a rule can name any of them.
  What hands the renderer its keys groups them by these pairs, and the check and an export
  read them to refuse a piece whose combinations differ in a value axis's mode of no pair.
- `physical-size`: its format has no physical page. An SVG file is a picture, drawn at the
  size whatever shows it gives, so it loses nothing of a top's physical size (DEC-034
  point 3).

Standard library only: the check reads it without importing the renderer.
"""

from __future__ import annotations

#: What a renderer may do with a property (DEC-005 point 9).
DRAWS = "draws"

#: The properties each element of the scene holds whatever its type.
_FRAME = ("x", "y", "width", "height")

#: The properties of an image of every source (DEC-025 point 7): a produced output, with its
#: variants and its points; a picture file, by its name and where it lies; a picture role.
#: The renderer draws each from the picture it is handed, whatever its source.
IMAGE = ("preserveAspectRatio", "output", "variants", "points", "file", "library", "role")

#: The format of the renderer that holds several modes in one file: a switching file.
SWITCHING = "svg-modes"

#: That format, with the signal pairs it reads.
HOLDS_MODES = {
    SWITCHING: {
        "colour-scheme": {
            "signal": "prefers-color-scheme",
            "pairs": {"light": "light", "dark": "dark"},
        },
    },
}

DECLARATION = {
    "name": "svg",
    "kind": "renderer",
    "version": "1.2.0",
    "seam": 7,
    "module": "svg",
    "about": (
        "An SVG file for each page, language and combination of modes, or, as `svg-modes`, "
        "one for each page, language and set of combinations a reader's signal parts."
    ),
    "profile": "default",
    "programs": [],
    "services": [],
    "holds-modes": HOLDS_MODES,
    "physical-size": {"page": False, "maps": False},
    "draws": {
        "group": dict.fromkeys(
            (*_FRAME, "component", "version", "options", "page"),
            DRAWS,
        ),
        "box": dict.fromkeys((*_FRAME, "fill", "stroke", "stroke-width", "rx"), DRAWS),
        "ellipse": dict.fromkeys((*_FRAME, "fill", "stroke", "stroke-width"), DRAWS),
        "line": dict.fromkeys(
            (
                *_FRAME,
                "x1",
                "y1",
                "x2",
                "y2",
                "stroke",
                "stroke-width",
                "marker-start",
                "marker-end",
                "points",
                "attached",
            ),
            DRAWS,
        ),
        "text": dict.fromkeys(
            (
                *_FRAME,
                "text-anchor",
                "line-height",
                "text",
                "paragraphs",
                "lines",
                "measured-height",
                "overflow",
            ),
            DRAWS,
        ),
        "image": dict.fromkeys((*_FRAME, *IMAGE), DRAWS),
        "path": dict.fromkeys(
            (*_FRAME, "d", "fill-rule", "fill", "stroke", "stroke-width"),
            DRAWS,
        ),
    },
}
