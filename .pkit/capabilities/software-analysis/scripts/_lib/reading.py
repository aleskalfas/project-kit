"""Reading a flagged artefact's change, as `_lib/resolve.py` classifies it.

The evidence comes from two places:

- **the backbone** — `pkit friction explain <artefact> --json` (COR-050 point
  13): the artefact's state, each anchor and its state, the commits behind each
  changed anchor, and its revalidation point;
- **git, at HEAD and at the revalidation point** — the artefact's text; for
  each changed path anchor, which pieces of code the artefact quotes (what it
  writes in backticks) the anchor's files held at the point, and which of those
  they no longer hold at HEAD; and, where the anchor resolves to nothing or its
  quoted code is gone from it, where that went.

Three things the backbone computes are worked out again here, because it does
not expose them to a capability yet, and each can disagree with it:

- **which files an anchor names** — git's glob pathspec reads the anchor, not
  the backbone's matcher, and it knows nothing of the project's
  `friction.exclude`: a quote held only by an excluded file still counts as
  held, and one that moved into an excluded file as moved;
- **the commits behind a dead anchor** — the explanation names none for an
  anchor that resolves to nothing, so `git log` over the anchor since the
  point names them;
- **a collection entry's section** — the body section headed by the entry's
  id, `## <id>`, which the backbone counts as part of the entry's content;
  here it is found by that heading alone.

And one thing only this reading derives: **where lost code went**. The quoted
code an anchor no longer holds moved when one file outside it, of a kind (by
its extension) the anchor's files are, now holds every piece of it and held
none of it at the point — a file renamed, or the code carried into another
file. An anchor the artefact quotes nothing from, gone because its files are,
moved where git's rename detection says they went. Anything else is not a
move: more than one such file, a quote found only in a file of another kind,
a quote the file already held.

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
from _lib.resolve import DEAD, Anchor, Commit

#: A piece of code quoted in Markdown, and a template placeholder that is none.
_QUOTE = re.compile(r"`([^`\n]+)`")
_PLACEHOLDER = re.compile(r"^<[^>]*>$")


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
            lost = anchor.state == DEAD or bool(gone)
            moved_to = _moved_to(root, point, value, gone) if lost else ()
            anchor = Anchor(kind, value, anchor.state, behind, quoted, gone, moved_to)
        anchors.append(anchor)
    return Reading(
        artefact=_text(document.get("artefact")) or artefact,
        location=location,
        state=state,
        head=head,
        point=point,
        anchors=tuple(anchors),
    )


def _moved_to(root: Path, point: str, anchor: str, gone: tuple[str, ...]) -> tuple[str, ...]:
    """Where the code a path anchor lost since `point` went, or `()` when the reading
    cannot name one place: the one file outside the anchor, of a kind its files are,
    that holds every piece of `gone` at HEAD and held none of it at `point` — or,
    with nothing quoted from it, where git says the anchor's files were renamed."""
    if not gone:
        return tuple(backbone.renamed(root, point, anchor))
    arrived: set[str] | None = None
    kinds: set[str] = set()
    for quote in gone:
        kinds |= {_kind(path) for path in backbone.files_holding(root, point, quote, anchor)}
        fresh = backbone.files_holding(root, "HEAD", quote) - backbone.files_holding(
            root, point, quote
        )
        arrived = fresh if arrived is None else arrived & fresh
        if not arrived:
            return ()
    found = sorted(path for path in arrived or () if _kind(path) in kinds)
    return tuple(found) if len(found) == 1 else ()


def _kind(path: str) -> str:
    """A file's kind, as far as a move goes: its extension."""
    return Path(path).suffix


def _quotes(root: Path, location: str) -> tuple[str, ...]:
    """What the artefact quotes at HEAD: the backticked code of its body — for a
    collection entry, of the body section headed by its id — placeholders left out."""
    path, _sep, entry = location.partition("#")
    text = backbone.show(root, "HEAD", path)
    if text is None:
        return ()
    _front, body = markdown.split(text)
    if entry:
        body = markdown.section(body, entry)
    return tuple(
        dict.fromkeys(
            quote.strip()
            for quote in _QUOTE.findall(body)
            if quote.strip() and not _PLACEHOLDER.match(quote.strip())
        )
    )


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
