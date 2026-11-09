"""What the SVG renderer draws: its declaration, plain data (visual-communication DEC-005
points 9 and 10).

A renderer declares, for each primitive and each property of the scene, whether it draws
it, updates it in place, recreates it, or reads it back. The SVG renderer writes files, so
it draws, and only draws: it updates nothing in place and reads nothing back. A primitive
or a property it does not name here is a loss the capability knows before it runs: a
primitive it refuses, a property it leaves out. It draws in the default font profile,
from the brand's committed font files, calls no outside program and reaches no service.

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

DECLARATION = {
    "name": "svg",
    "kind": "renderer",
    "version": "1.1.0",
    "seam": 5,
    "module": "svg",
    "about": "An SVG file for each page, language and combination of modes.",
    "profile": "default",
    "programs": [],
    "services": [],
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
    },
}
