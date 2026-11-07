"""What the HTML renderer draws: its declaration, plain data (visual-communication DEC-005
points 9 and 10, DEC-020 points 1 to 4).

The HTML renderer writes one page file for each language, at one key, its pages in order,
so it draws, and only draws: it updates nothing in place and reads nothing back. A
primitive or a property it does not name here is a loss the capability knows before it
runs: a primitive it refuses, a property it leaves out. It draws in the default font
profile, from the brand's committed font files, calls no outside program and reaches no
service. Writing a page file takes no browser.

- `pages`: each choice a scene leaves open that the medium needs (DEC-001 point 2): how
  pages lie, the gap between two of them, in px of the window, and how a page scales.
- `not-carried`: what the file does not carry yet. What a reader who does not see the page
  gets (DEC-005 point 5) comes with a later version.
- `marks`: the attribute that marks each thing the file holds (`MARKS`), so the viewing
  step reads the words the renderer writes. A page and a text hold their trace id. A shape
  keeps the canvas's `data-id`, so a text takes a mark of its own.

Standard library only: the check and the viewing step read it without importing the
renderer.
"""

from __future__ import annotations

#: What a renderer may do with a property (DEC-005 point 9).
DRAWS = "draws"

#: The properties each element of the scene holds whatever its type.
_FRAME = ("x", "y", "width", "height")

#: The attribute that marks each thing a page file holds.
MARKS = {
    "page": "data-page",
    "layer": "data-layer",
    "text": "data-text",
    "line": "data-line",
    "strut": "data-strut",
    "span": "data-span",
}

DECLARATION = {
    "name": "html",
    "kind": "renderer",
    "version": "1.0.0",
    "seam": 3,
    "module": "html",
    "about": "A page file for each language, at one key: real text over SVG shapes.",
    "profile": "default",
    "programs": [],
    "services": [],
    "pages": {
        "lie": "one under another, each in the middle of the window",
        "gap": 24,
        "scale": "shrinks with a narrower window and never grows",
    },
    "not-carried": ["alternative text", "reading order", "structure"],
    "marks": MARKS,
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
        "image": dict.fromkeys(
            (*_FRAME, "output", "preserveAspectRatio", "variants", "points"),
            DRAWS,
        ),
    },
}
