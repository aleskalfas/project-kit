"""Reading a flagged artefact's change, as `_lib/resolve.py` classifies it.

The evidence comes from two places, and nothing is recomputed:

- **the backbone** — `pkit friction explain <artefact> --json` (COR-050 point
  13): the artefact's state, each anchor and its state, the commits behind each
  changed anchor, and its revalidation point;
- **git, at HEAD and at the revalidation point** — the artefact's text, and for
  each changed path anchor which pieces of code the artefact quotes (what it
  writes in backticks) the anchor's files held at the point, and which of those
  they no longer hold at HEAD; and, for an anchor whose files are gone — a dead
  anchor, which the explanation names no commits for — the commits that touched
  them since the point. The anchor is handed to git as a glob pathspec, so no
  file list is computed here.

Both read HEAD, as the explanation does: uncommitted work is not read.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _lib import backbone, markdown
from _lib.model import Unreadable
from _lib.resolve import Anchor, Commit

#: A piece of code quoted in Markdown, and a template placeholder that is none.
_QUOTE = re.compile(r"`([^`\n]+)`")
_PLACEHOLDER = re.compile(r"^<[^>]*>$")

#: A collection entry's section heading, and the next section's.
_SECTION = re.compile(r"^## (?P<id>\S+)")


@dataclass(frozen=True)
class Reading:
    """What the evidence says of one artefact: its id and location, its state, HEAD
    and its revalidation point, and each of its anchors."""

    artefact: str
    location: str
    state: str
    head: str | None
    point: str | None
    anchors: tuple[Anchor, ...]


def read(root: Path, artefact: str) -> Reading:
    """The evidence on `artefact`. Raises Unreadable when the backbone cannot explain it."""
    document = backbone.explain(root, artefact)
    state = _text(document.get("state")) or "unknown"
    if state == "unreachable":
        raise Unreadable(
            f"{artefact}'s revalidation point lies beyond this shallow clone's history: "
            f"`git fetch --unshallow`, then ask again"
        )
    location = _text(document.get("location")) or artefact
    point = _text(_mapping(document.get("revalidation_point")).get("commit"))
    head = _text(_mapping(document.get("head")).get("commit"))
    commits = _commits_by_anchor(document.get("findings"))
    quotes = _quotes(root, location)
    anchors: list[Anchor] = []
    for entry in _mappings(document.get("anchors")):
        kind, value = _text(entry.get("kind")), _text(entry.get("value"))
        if kind is None or value is None:
            continue
        anchor = Anchor(
            kind=kind,
            value=value,
            state=_text(entry.get("state")) or "unknown",
            commits=commits.get((kind, value), ()),
        )
        if anchor.changed and kind == "path" and point is not None:
            quoted = tuple(q for q in quotes if backbone.holds(root, point, value, q))
            gone = tuple(q for q in quoted if not backbone.holds(root, "HEAD", value, q))
            behind = anchor.commits or tuple(
                Commit(sha, subject) for sha, subject in backbone.touched(root, point, value)
            )
            anchor = Anchor(kind, value, anchor.state, behind, quoted, gone)
        anchors.append(anchor)
    return Reading(
        artefact=_text(document.get("artefact")) or artefact,
        location=location,
        state=state,
        head=head,
        point=point,
        anchors=tuple(anchors),
    )


def _quotes(root: Path, location: str) -> tuple[str, ...]:
    """What the artefact quotes at HEAD: the backticked code of its body — for a
    collection entry, of the body section headed by its id — placeholders left out."""
    path, _sep, entry = location.partition("#")
    text = backbone.show(root, "HEAD", path)
    if text is None:
        return ()
    _front, body = markdown.split(text)
    if entry:
        body = _section(body, entry)
    return tuple(
        dict.fromkeys(
            quote.strip()
            for quote in _QUOTE.findall(body)
            if quote.strip() and not _PLACEHOLDER.match(quote.strip())
        )
    )


def _section(body: str, entry: str) -> str:
    """The body section headed by `entry`'s id, up to the next section."""
    lines: list[str] = []
    inside = False
    for line in body.splitlines():
        heading = _SECTION.match(line)
        if heading is not None:
            inside = heading["id"] == entry
            continue
        if inside:
            lines.append(line)
    return "\n".join(lines)


def _commits_by_anchor(findings: Any) -> dict[tuple[str, str], tuple[Commit, ...]]:
    """The commits behind each anchor's findings, oldest first, each once."""
    found: dict[tuple[str, str], dict[str, Commit]] = {}
    for finding in _mappings(findings):
        anchor = _mapping(finding.get("anchor"))
        kind, value = _text(anchor.get("kind")), _text(anchor.get("value"))
        if kind is None or value is None:
            continue
        seen = found.setdefault((kind, value), {})
        for commit in _mappings(finding.get("commits")):
            sha = _text(commit.get("commit"))
            if sha is not None and sha not in seen:
                seen[sha] = Commit(sha, _text(commit.get("change")) or "")
    return {key: tuple(commits.values()) for key, commits in found.items()}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _mappings(value: Any) -> Sequence[Mapping[str, Any]]:
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None
