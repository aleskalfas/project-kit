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

The same walk reads the `## Doc impact` section when given its heading set
(`DOC_IMPACT_HEADINGS`, #1015): its boxes are addressed with
`--section doc-impact` and numbered within that section, and
`checkbox_addresses` / `tick_hints` say which command reaches a given box.

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

# The two checkbox sections check-criterion / uncheck-criterion address (#1015).
# `criteria` is the schema-resolved criteria section (the default); `doc-impact`
# is the `## Doc impact` section, whose checkbox shape the DEC-007 close-gate
# counts like any other box. Its heading is not schema-marked as a checkbox
# section — a Doc impact section may equally be one line of prose — so it is
# named here, the way `pr_validation` names it on the PR side.
SECTION_CRITERIA = "criteria"
SECTION_DOC_IMPACT = "doc-impact"
SECTIONS = (SECTION_CRITERIA, SECTION_DOC_IMPACT)
DOC_IMPACT_HEADINGS = frozenset({"doc impact"})


def section_headings(section: str, body_format: dict) -> frozenset[str]:
    """The heading set that opens ``section`` — schema-resolved for the
    criteria, the `## Doc impact` literal for the Doc impact section."""
    if section == SECTION_DOC_IMPACT:
        return DOC_IMPACT_HEADINGS
    return checkbox_headings(body_format)


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


def extract_criteria(body: str, headings: frozenset[str] | None = None) -> list[Criterion]:
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


def checkbox_addresses(
    body: str, criteria_headings: frozenset[str] | None = None
) -> dict[int, tuple[str, int]]:
    """Where check-criterion can reach each checkbox: body line → (section, index).

    Covers the criteria section (``criteria_headings``, as from
    :func:`checkbox_headings`) and the Doc impact section, numbered exactly as
    :func:`extract_criteria` numbers them — so a line found here is ticked by
    ``check-criterion <issue> [--section doc-impact] <index>``. A checkbox in any
    other section has no address and is absent.
    """
    addresses: dict[int, tuple[str, int]] = {}
    for section, headings in (
        (SECTION_CRITERIA, criteria_headings),
        (SECTION_DOC_IMPACT, DOC_IMPACT_HEADINGS),
    ):
        for item in extract_criteria(body, headings):
            if item.is_checkbox:
                addresses.setdefault(item.line_no, (section, item.index))
    return addresses


def tick_command(issue_number: int, section: str, index: int) -> str:
    """The `check-criterion` invocation that ticks box ``index`` of ``section``."""
    flag = "" if section == SECTION_CRITERIA else f" --section {section}"
    return f"pkit pm check-criterion {issue_number}{flag} {index}"


def tick_hints(
    issue_number: int,
    body: str,
    line_numbers: list[int],
    criteria_headings: frozenset[str] | None = None,
) -> list[str]:
    """The command that ticks the box on each of ``line_numbers``, in order.

    `check-criterion` where the box has an address; a box in any other section
    has none, and the hint says the body is edited instead.
    """
    addresses = checkbox_addresses(body, criteria_headings)
    hints: list[str] = []
    for line_no in line_numbers:
        where = addresses.get(line_no)
        if where is not None:
            hints.append(tick_command(issue_number, *where))
        else:
            hints.append(
                "outside the criteria and Doc impact sections — edit the body: "
                f"pkit pm edit-issue {issue_number} --body-file <file>"
            )
    return hints


def set_checkbox_state(line: str, *, checked: bool) -> str:
    """Return `line` with its checkbox marker flipped to `checked`, preserving layout.

    Rewrites only the marker character inside the first `[ ]` / `[x]` on the
    line, leaving the bullet's leading whitespace, bullet character, spacing,
    and item text untouched — a narrow edit, never a re-render of the line.
    The caller guarantees `line` is a checkbox line (via `Criterion.is_checkbox`).
    """
    return re.sub(r"\[[ xX]\]", "[x]" if checked else "[ ]", line, count=1)
