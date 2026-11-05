"""The capability's plugins (visual-communication DEC-005 point 9).

Each shipped plugin's declaration is plain data in its own module,
`<name>_declaration.py`, which imports nothing beyond the standard library, and
is added to the seam here. Its implementation lives in `<name>.py` and is
imported only when it runs.
"""

from __future__ import annotations

from _lib.plugins import css_declaration, pdf_declaration, seam, svg_declaration

# The renderers.
seam.ship(svg_declaration.DECLARATION)
seam.ship(pdf_declaration.DECLARATION)

# The code writers.
seam.ship(css_declaration.DECLARATION)

__all__ = ["seam"]
