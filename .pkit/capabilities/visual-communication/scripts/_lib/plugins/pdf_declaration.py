"""What the PDF renderer draws: its declaration, plain data (visual-communication DEC-005
points 9 and 10, DEC-006 point 7).

The PDF renderer writes one file for each language and combination of modes, its pages in
order, so it draws, and only draws: it updates nothing in place and reads nothing back. A
primitive or a property it does not name here is a loss the capability knows before it
runs: a primitive it refuses, a property it leaves out. It refuses the image for now. It
draws in the default font profile, from the brand's committed font files, calls no
outside program and reaches no service.

- `unit`: how it maps the scene's unit onto a page (DEC-001 point 2). Each px of the scene
  is 0.75 pt of the page, CSS's 96 px to the inch, since format 1's top components declare
  no physical size.
- `not-carried`: what the PDF does not carry yet. A tagged PDF carries alternative text, a
  reading order and structure (DEC-005 point 5), which a later version adds.

Standard library only: the check reads it without importing the renderer.
"""

from __future__ import annotations

#: What a renderer may do with a property (DEC-005 point 9).
DRAWS = "draws"

#: The properties each element of the scene holds whatever its type.
_FRAME = ("x", "y", "width", "height")

DECLARATION = {
    "name": "pdf",
    "kind": "renderer",
    "version": "1.0.0",
    "seam": 4,
    "module": "pdf",
    "about": "A PDF file for each language and combination of modes, its pages in order.",
    "profile": "default",
    "programs": [],
    "services": [],
    "unit": {"scene": "px", "page": "pt", "scale": 0.75},
    "not-carried": ["alternative text", "reading order", "structure"],
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
    },
}
