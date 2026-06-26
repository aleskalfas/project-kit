"""Acceptance-criterion extraction with body-line + checkbox metadata.

The `check-criterion` / `uncheck-criterion` verbs (per [project-management:
DEC-038-criterion-addressing]) address a checkbox by its **1-based index** into
the acceptance-criteria list, with an optional **expected-text guard**. The
index numbering MUST match what `show-issue --field criteria` shows — that
consistency is a correctness property the guard depends on (DEC-038 D1 / the
"reuses existing criterion extraction" implication).

`show-issue.py`'s `_extract_criteria(body)` is the canonical text projection.
This module re-implements the SAME enumeration walk line-for-line, but yields
each item enriched with the source body-line index and checkbox state so a
narrow tick can rewrite exactly that line. The two stay in lock-step by sharing
one walk shape; `tests/test_pm_criteria_lib.py` asserts that the text sequence
this module produces equals `show-issue._extract_criteria(body)` for the same
body, so a future divergence is caught.

A `Criterion` carries:

  index        — 1-based position in the acceptance-criteria item list (the
                 number a caller passes to `check-criterion`).
  text         — the item text with the leading bullet and any checkbox marker
                 stripped and trimmed (identical to `_extract_criteria`'s value).
  line_no      — 0-based index into `body.splitlines()` of the source line.
  is_checkbox  — True when the item is a `- [ ]` / `- [x]` checkbox line (only
                 these can be ticked); False for a plain `- text` bullet, which
                 `_extract_criteria` also enumerates but cannot be ticked.
  checked      — True when the checkbox is `- [x]` / `- [X]`; False for `- [ ]`.
                 Meaningless (and False) when `is_checkbox` is False.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Mirror show-issue._extract_criteria's two patterns exactly so the item
# enumeration cannot drift. The first matches any `-`/`*` bullet; the second
# recognises (and strips) a leading checkbox marker, capturing the checked
# state in the marker character.
_BULLET_RE = re.compile(r"^[-*]\s+(.*)$")
_CHECKBOX_RE = re.compile(r"^\[([ xX])\]\s*(.*)$")


@dataclass(frozen=True)
class Criterion:
    index: int
    text: str
    line_no: int
    is_checkbox: bool
    checked: bool


def extract_criteria(body: str) -> list[Criterion]:
    """Enumerate the acceptance-criteria items with line + checkbox metadata.

    Walks the body exactly as `show-issue._extract_criteria` does: collection
    starts at the `## Acceptance criteria` heading, stops at the next level-2
    heading, includes only bullets with non-whitespace text after the marker
    (a bare `- [ ]` skeleton is excluded — it carries no authored content), and
    strips the bullet + any checkbox marker from the text. The resulting `text`
    sequence is byte-identical to `_extract_criteria`'s, so the 1-based `index`
    here matches `show-issue --field criteria`'s line numbering.
    """
    items: list[Criterion] = []
    in_section = False
    for line_no, raw in enumerate(body.splitlines()):
        stripped = raw.strip()
        if stripped.startswith("## "):
            in_section = "acceptance criteria" in stripped.lower()
            continue
        if not in_section:
            continue
        bullet = _BULLET_RE.match(stripped)
        if not bullet:
            continue
        text = bullet.group(1)
        checkbox = _CHECKBOX_RE.match(text)
        is_checkbox = checkbox is not None
        checked = False
        if checkbox:
            checked = checkbox.group(1) in ("x", "X")
            text = checkbox.group(2)
        text = text.strip()
        if not text:
            continue
        items.append(
            Criterion(
                index=len(items) + 1,
                text=text,
                line_no=line_no,
                is_checkbox=is_checkbox,
                checked=checked,
            )
        )
    return items


def set_checkbox_state(line: str, *, checked: bool) -> str:
    """Return `line` with its checkbox marker flipped to `checked`, preserving layout.

    Rewrites only the marker character inside the first `[ ]` / `[x]` on the
    line, leaving the bullet's leading whitespace, bullet character, spacing,
    and item text untouched — a narrow edit, never a re-render of the line.
    The caller guarantees `line` is a checkbox line (via `Criterion.is_checkbox`).
    """
    return re.sub(r"\[[ xX]\]", "[x]" if checked else "[ ]", line, count=1)
