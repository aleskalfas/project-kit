"""Acceptance-criterion extraction with body-line + checkbox metadata.

The `check-criterion` / `uncheck-criterion` verbs (per [project-management:
DEC-038-criterion-addressing]) address a checkbox by its **1-based index** into
the criteria list, with an optional **expected-text guard**. Which section
carries the criteria is issue-type-dependent and owned by
`schemas/body-format.yaml` (`## Acceptance criteria` on Features/Tasks,
`## Success criteria` on EPICs); `checkbox_headings` resolves the
checkbox-bearing heading set from that schema, falling back to the historical
`acceptance criteria` literal only when the schema cannot supply one. The
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

  index        — 1-based position in the criteria item list (the
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

# Fail-open floor for the criteria-section heading match: the pre-schema
# hardcoded literal. Used only when the body-format schema cannot supply the
# checkbox-bearing heading set (unreadable, malformed, or empty), so the
# primitives never behave worse than they did before the schema-driven
# resolution existed.
FALLBACK_HEADINGS = frozenset({"acceptance criteria"})


def checkbox_headings(body_format: dict) -> frozenset[str]:
    """Resolve the checkbox-bearing section headings from the parsed schema.

    `body_format` is the parsed `schemas/body-format.yaml` mapping (the schema
    is the source of truth for which `## <Name>` section carries the criteria
    checkboxes per issue type — e.g. EPICs use `## Success criteria`, Features
    and Tasks `## Acceptance criteria`). Collects every `required_sections[]`
    entry with `has_checkboxes: true` across `bodies.*` and returns the
    headings normalised for matching: leading `#` marks stripped, trimmed,
    lowercased.

    Fail-open: when the collection comes up empty — schema missing, unreadable,
    malformed, or carrying no checkbox-bearing sections (the loaders used by
    the callers collapse all of these into an empty/absent mapping) — returns
    `FALLBACK_HEADINGS`, today's hardcoded behaviour.
    """
    found: set[str] = set()
    bodies = body_format.get("bodies") if isinstance(body_format, dict) else None
    for type_body in (bodies or {}).values():
        if not isinstance(type_body, dict):
            continue
        for section in type_body.get("required_sections") or []:
            if not isinstance(section, dict) or not section.get("has_checkboxes"):
                continue
            heading = str(section.get("heading", "")).lstrip("#").strip().lower()
            if heading:
                found.add(heading)
    return frozenset(found) or FALLBACK_HEADINGS


def _is_criteria_heading(stripped_line: str, headings: frozenset[str]) -> bool:
    """True when a `## ` body line opens a criteria section.

    Substring containment on the lowercased line, exactly as the original
    hardcoded `"acceptance criteria" in stripped.lower()` matched — so a
    heading with trailing decoration (e.g. `## Acceptance criteria (v2)`)
    still opens the section.
    """
    lowered = stripped_line.lower()
    return any(heading in lowered for heading in headings)


@dataclass(frozen=True)
class Criterion:
    index: int
    text: str
    line_no: int
    is_checkbox: bool
    checked: bool


def extract_criteria(
    body: str, headings: frozenset[str] | None = None
) -> list[Criterion]:
    """Enumerate the criteria items with line + checkbox metadata.

    Walks the body exactly as `show-issue._extract_criteria` does: collection
    starts at a criteria heading, stops at the next level-2 heading, includes
    only bullets with non-whitespace text after the marker (a bare `- [ ]`
    skeleton is excluded — it carries no authored content), and strips the
    bullet + any checkbox marker from the text. The resulting `text` sequence
    is byte-identical to `_extract_criteria`'s for the same `headings`, so the
    1-based `index` here matches `show-issue --field criteria`'s line numbering
    (both sides resolve the heading set via `checkbox_headings`).

    `headings` is the normalised heading set from `checkbox_headings` — the
    schema-driven set of checkbox-bearing section names (e.g. `## Success
    criteria` on an EPIC, `## Acceptance criteria` on a Feature/Task). `None`
    falls back to `FALLBACK_HEADINGS` (the pre-schema hardcoded behaviour).
    """
    if headings is None:
        headings = FALLBACK_HEADINGS
    items: list[Criterion] = []
    in_section = False
    for line_no, raw in enumerate(body.splitlines()):
        stripped = raw.strip()
        if stripped.startswith("## "):
            in_section = _is_criteria_heading(stripped, headings)
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
