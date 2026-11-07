"""What the HTML renderer draws: its declaration, plain data (visual-communication DEC-005
points 9 and 10, DEC-020 points 1 to 4, DEC-023 points 2, 5 and 7).

The HTML renderer writes one page file for each language and each key over the size axes,
its pages in order, holding the modes a reader's signal names. So it draws, and only draws:
it updates nothing in place and reads nothing back. A primitive or a property it does not
name here is a loss the capability knows before it runs: a primitive it refuses, a property
it leaves out. It draws in the default font profile, from the brand's committed font files,
calls no outside program and reaches no service. Writing a page file takes no browser.

- `holds-modes`: each format of the renderer that holds several modes in one file, with the
  signal pairs it reads (DEC-023 point 5). For each value axis, the reader's signal that names
  its modes, a CSS media feature, and the value of that signal each of its modes pairs with.
  The first pair of each is the signal's value for a reader who names no preference. What
  hands the renderer its keys groups them by these pairs, and holds none of its own.
- `forced-colours`: what the file gives its shapes where a reader forces their own colours
  (DEC-023 point 7). Each line, stroke and arrowhead takes the reader's text colour. A fill
  opaque in every key the file holds takes the reader's background colour, with an edge of
  the width named, in px of the page, and the text colour, where it has no stroke of its own.
  A translucent fill stays as it is drawn. Each colour is a system colour of CSS, the
  reader's, so the file adds none of its own.
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

#: The format of the renderer that holds several modes in one file, and its signal pairs.
HOLDS_MODES = {
    "html": {
        "colour-scheme": {
            "signal": "prefers-color-scheme",
            "pairs": {"light": "light", "dark": "dark"},
        },
        "contrast": {
            "signal": "prefers-contrast",
            "pairs": {"standard": "no-preference", "high": "more"},
        },
    },
}

DECLARATION = {
    "name": "html",
    "kind": "renderer",
    "version": "1.1.0",
    "seam": 4,
    "module": "html",
    "about": (
        "A page file for each language and each key over the size axes, holding the modes a "
        "reader's signal names: real text over SVG shapes."
    ),
    "profile": "default",
    "programs": [],
    "services": [],
    "holds-modes": HOLDS_MODES,
    "forced-colours": {
        "lines": "CanvasText",
        "opaque-fills": "Canvas",
        "edge": {"colour": "CanvasText", "width": 1},
        "translucent-fills": "as drawn",
    },
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
