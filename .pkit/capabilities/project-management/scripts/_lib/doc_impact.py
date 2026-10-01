"""Rendering a pull request's `## Doc impact` section from the artefacts' answers.

A change's anchored pages answer it on the page itself — updated, unchanged
with its justification, deferred with its reason (COR-050) — and the core
change check reports those answers machine-readably: `pkit friction check
--json`. The `## Doc impact` section may *render* them (DEC-053 point 2), so
the author starts from what the pages already say instead of retyping it.

Rendering only: the section is never read back as an answer. The doc-check
point's obligations are met by the pages in the diff, and the section stays
DEC-015's "did you think about documentation?" step, whatever it holds.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

HEADING = "## Doc impact"

# The version of `pkit friction check --json` this rendering reads. A document
# without `schema_version` comes from a backbone that predates the key: version 1.
SCHEMA_VERSION = 1

# The finding kinds of the change check that carry an answer.
ANSWER_KINDS = ("answered", "revalidated")
FRICTION_KIND = "friction"

# What the template leaves in an unwritten section.
_PLACEHOLDERS = {"", "-", "- [ ]"}
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def _findings(document: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    findings = document.get("findings")
    if not isinstance(findings, list):
        return []
    return [f for f in findings if isinstance(f, Mapping)]


def _where(finding: Mapping[str, Any]) -> str:
    location = f"`{finding.get('location') or finding.get('artefact') or '?'}`"
    anchor = finding.get("anchor")
    if isinstance(anchor, Mapping) and anchor.get("kind"):
        location += f" (anchor `{anchor.get('kind')}:{anchor.get('value')}`)"
    return location


def unread_version(document: Mapping[str, Any]) -> str | None:
    """Why this rendering does not read `document` — a `schema_version` other than
    the one it reads — or None when it reads it."""
    version = document.get("schema_version", SCHEMA_VERSION)
    if version == SCHEMA_VERSION:
        return None
    return (
        f"`pkit friction check --json` answered schema_version {version!r}; "
        f"this capability reads {SCHEMA_VERSION}"
    )


def answer_lines(document: Mapping[str, Any]) -> list[str]:
    """One bullet per answer the change check found, in its order."""
    return [
        f"- {_where(f)}: {f.get('message', '')}"
        for f in _findings(document)
        if f.get("kind") in ANSWER_KINDS
    ]


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
