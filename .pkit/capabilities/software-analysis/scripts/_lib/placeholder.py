"""A placeholder a person fills: words in angle brackets.

A command shown for a person to run writes what only they can supply in angle
brackets — `<the defect reference>`, `<your name>`. Run as shown, it would write
the placeholder as though it were their words. The backbone's friction writers
refuse a justification or a reason still holding one; the record stamp refuses
its texts by the same shape, so a command run as shown writes nothing until its
placeholders are filled. A bracket with no space inside, or opening in
capitals, is code (`Vec<u8>`, `Map<String, int>`), not a placeholder.
"""

from __future__ import annotations

import re

#: The shape both the backbone's writers and this capability's stamp refuse.
PLACEHOLDER = re.compile(r"<[a-z][^<>\n]*\s[^<>\n]*>")


def unfilled(text: str) -> str | None:
    """The first placeholder `text` still holds, or `None`."""
    found = PLACEHOLDER.search(text)
    return None if found is None else found.group(0)
