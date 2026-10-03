"""A pull request's `## Doc impact` section, filled where nobody wrote it.

A change's anchored pages answer it on the page itself — updated, unchanged
with its justification, deferred with its reason (COR-050) — and the answers
the change wrote are listed in the description's own `## Friction answers`
section (`_lib.friction_answers`, DEC-055). `open-pr --doc-impact-from-friction`
fills an unwritten `## Doc impact` with one line pointing there (`prefill`),
naming no path and no reason, and names the pages still carrying friction
(`unanswered`).

Rendering only: the section is never read back as an answer. The doc-check
point's obligations are met by the pages in the diff, and the section stays
DEC-015's "did you think about documentation?" step, whatever it holds.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

HEADING = "## Doc impact"

# The change check's finding kind for an artefact with no answer yet.
FRICTION_KIND = "friction"

# What the template leaves in an unwritten section.
_PLACEHOLDERS = {"", "-", "- [ ]"}
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def _findings(document: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    findings = document.get("findings")
    if not isinstance(findings, list):
        return []
    return [f for f in findings if isinstance(f, Mapping)]


def unanswered(document: Mapping[str, Any]) -> list[str]:
    """The locations still carrying friction — no answer on the page yet."""
    return sorted(
        {
            str(f.get("location") or f.get("artefact"))
            for f in _findings(document)
            if f.get("kind") == FRICTION_KIND
        }
    )


def prefill(body: str, lines: list[str]) -> tuple[str, bool]:
    """`body` with its `## Doc impact` section holding `lines`, and whether it
    changed. Only a section nobody has written — absent, empty, or the
    template's placeholder — is filled; an authored section is left as it is."""
    if not lines:
        return body, False
    block = "\n".join(lines)
    match = re.search(rf"^{re.escape(HEADING)}[ \t]*$", body, flags=re.MULTILINE)
    if match is None:
        separator = "" if body.endswith("\n") or not body else "\n"
        return f"{body}{separator}\n{HEADING}\n\n{block}\n", True
    start = match.end()
    following = re.search(r"^## ", body[start:], flags=re.MULTILINE)
    end = start + following.start() if following else len(body)
    content = _COMMENT.sub("", body[start:end]).strip()
    if content not in _PLACEHOLDERS:
        return body, False
    tail = body[end:]
    return f"{body[:start]}\n\n{block}\n" + ("\n" + tail if tail else ""), True
