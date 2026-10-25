"""The body rules an issue body is checked against (DEC-010), as `body-format.yaml` carries them.

The one reader of these rules for every command that writes or checks an issue
body: `create-issue` before it files, `edit-issue` on a body edit, and
`validate-issue`, the command the `validate-body` procedure runs. Two parts:

- **The required sections** (`required_sections`): each section the type's entry
  under `bodies` lists and the body lacks, at the severity that entry gives it.
- **The universal rules** (`universal`): a heading of the first level, a
  `file:line` reference, and a `## Implementation` or `## How` section. Each is
  reported under its label, at the severity of the `universal_body_rules` entry
  whose `id` is that label. A schema with no such entry gives the rule's
  default. A line inside a fenced code block is no heading.

`check` gives both. `blocking` picks the findings that refuse: a command refuses
on any of them, and reports the rest.

What this module does not check is checked elsewhere: each command checks the
parent-ref first line itself, `placeholder_detection` checks the template's
leftovers, `use_case_citations` checks the use cases a body cites, and
`decision_ids` checks the decision ids it cites, through the backbone. Each of
those that reads a universal rule's severity reads it through `rule_severity`.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from typing import Any

#: One finding: its severity, its label, and what is wrong.
Finding = tuple[str, str, str]

REQUIRED_SECTION = "body.required-section"
H1 = "body.h1"
FILE_LINE = "body.file-line-refs"
RECIPE = "body.implementation-recipe"

#: The severities that refuse, as `validation-severity.yaml` names them.
BLOCKING = ("hard-reject", "bypassable-with-audit")

#: The severity of a universal rule the schema carries no entry for.
_DEFAULTS = {H1: "hard-reject", FILE_LINE: "warning", RECIPE: "warning"}

_SEVERITY = re.compile(r"\[validation-severity:([a-z-]+)\]")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_H1 = re.compile(r"^# [^#]")
#: A match starts where no character of a path does, so a long run of them with
#: no `:digits` after it is read once rather than from each of its characters.
_FILE_LINE = re.compile(r"(?<![A-Za-z0-9_/.\-])[A-Za-z0-9_/.\-]+\.[a-z]+:\d+\b")
_RECIPE = re.compile(r"^## (Implementation|How)\s*$")


def check(body: str, structural_type: str | None, body_format: Mapping[str, Any]) -> list[Finding]:
    """Every finding on *body*: its required sections, then the universal rules."""
    return required_sections(body, structural_type, body_format) + universal(body, body_format)


def blocking(findings: list[Finding]) -> list[Finding]:
    """The findings that refuse."""
    return [finding for finding in findings if finding[0] in BLOCKING]


def required_sections(
    body: str, structural_type: str | None, body_format: Mapping[str, Any]
) -> list[Finding]:
    """Each section *structural_type*'s entry under `bodies` requires and *body* lacks."""
    if structural_type is None:
        return []
    bodies = body_format.get("bodies") or {}
    type_body = bodies.get(structural_type) if isinstance(bodies, Mapping) else None
    if not isinstance(type_body, Mapping):
        return []
    findings: list[Finding] = []
    for section in type_body.get("required_sections") or []:
        if not isinstance(section, Mapping):
            continue
        heading = str(section.get("heading", ""))
        if heading and heading not in body:
            findings.append(
                (
                    _severity(section.get("severity")) or "warning",
                    REQUIRED_SECTION,
                    f"missing required section {heading!r} ({structural_type} body).",
                )
            )
    return findings


def universal(body: str, body_format: Mapping[str, Any]) -> list[Finding]:
    """The universal rules *body* breaks, each at its severity in *body_format*."""
    findings: list[Finding] = []
    headings = list(lines_outside_fences(body))
    if any(_H1.match(line) for line in headings):
        findings.append(
            (
                rule_severity(body_format, H1),
                H1,
                "body contains an h1 (`# ...`) heading; the issue title "
                "is the h1. Use `## Title` for sections.",
            )
        )
    if _FILE_LINE.search(body):
        findings.append(
            (
                rule_severity(body_format, FILE_LINE),
                FILE_LINE,
                "body contains file:line references; line numbers go stale.",
            )
        )
    recipes = [line.strip() for line in headings if _RECIPE.match(line)]
    if recipes:
        findings.append(
            (
                rule_severity(body_format, RECIPE),
                RECIPE,
                f"body holds a {recipes[0]!r} section: a body describes the outcome, "
                "and how to build it belongs in the PR or a design doc.",
            )
        )
    return findings


def rule_severity(body_format: Mapping[str, Any], rule_id: str, default: str | None = None) -> str:
    """The severity of the universal rule whose `id` is *rule_id*, as its entry in
    *body_format* gives it; else *default*, else this module's default for the rule."""
    for rule in body_format.get("universal_body_rules") or []:
        if isinstance(rule, Mapping) and rule.get("id") == rule_id:
            severity = _severity(rule.get("severity"))
            if severity is not None:
                return severity
    return default if default is not None else _DEFAULTS[rule_id]


def _severity(token: Any) -> str | None:
    """The severity a `[validation-severity:<sev>]` token names, or None."""
    match = _SEVERITY.match(token) if isinstance(token, str) else None
    return match.group(1) if match else None


def lines_outside_fences(body: str) -> Iterator[str]:
    """The lines of *body* outside fenced code blocks, fences' own lines left out.

    A fence closes on a line of the same character, at least as long, with
    nothing after it. A backtick fence's opening line holds no other backtick.
    The lines of a fence never closed are read, so a fence this reader takes
    wrongly, such as one opened in a list item, hides no heading.
    """
    fence = ""
    held: list[str] = []
    for line in body.splitlines():
        match = _FENCE.match(line)
        if fence:
            if (
                match
                and match.group(1)[0] == fence[0]
                and len(match.group(1)) >= len(fence)
                and not line[match.end() :].strip()
            ):
                fence, held = "", []
            else:
                held.append(line)
            continue
        if match and not (match.group(1)[0] == "`" and "`" in line[match.end() :]):
            fence = match.group(1)
            continue
        yield line
    yield from held
