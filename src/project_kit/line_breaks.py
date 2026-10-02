"""The line breaks a text file is written with, for writers that keep its other bytes.

A file is read whatever its line endings and edited with `\\n` line breaks
(`universal_newlines`); a writer that keeps every byte it does not change
writes the edited text back in the one line break the file is written with
(`line_break`). A file that mixes them has no such line break, so it cannot be
written back unchanged outside the edit, and a writer refuses it.
"""

from __future__ import annotations

import re


def universal_newlines(text: str) -> str:
    """`text` with every line break read as `\\n` — `\\r\\n`, then a lone `\\r` —
    as a text file is read."""
    if "\r" not in text:
        return text
    return text.replace("\r\n", "\n").replace("\r", "\n")


# A line break in any of the three ways a text may write one (`universal_newlines`).
_LINE_BREAK = re.compile(r"\r\n|\r|\n")


def line_break(text: str) -> str | None:
    """The one line break `text` is written with — `\\n`, `\\r\\n` or `\\r` — or
    `None` when it mixes them. A text with no line break reads as written with `\\n`.

    A text written with one is read universally and written back with it
    unchanged; one that mixes them cannot be, and reads a carriage return that
    is part of a value as a line break.
    """
    found = set(_LINE_BREAK.findall(text))
    if len(found) > 1:
        return None
    return found.pop() if found else "\n"


def written_with(text: str, newline: str) -> str:
    """`text`, edited with `\\n` line breaks, in the line break `newline`."""
    return text if newline == "\n" else text.replace("\n", newline)
