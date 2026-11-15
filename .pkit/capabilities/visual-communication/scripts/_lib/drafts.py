"""The makers' record of drafts, in a piece's brief (visual-communication DEC-042 point 7,
DEC-029 points 2 to 4): for each lead, title or takeaway the designer drafted and the asker
has not seen, an entry naming its page, its kind and the language of its text, with a digest
of that text, never the text.

- **The digest** is `sha256:` and the hex of SHA-256 over the text *normalised*: Unicode
  normalisation form C, then each run of white space, a line break among them, made one
  space, then the ends trimmed. So a reflowed or re-indented text keeps its digest, and a
  changed word, case or mark changes it. Where the text is a takeaway it is the brief's own;
  where a lead or a title, it is the content's field of the language, named by its key path
  from the page, or, on a piece whose top is a page alone, from the content's top.
- **Which part an entry lies in.** An entry lies in its page's part, or in the part for the
  whole piece on a piece whose top is a page alone, such as a figure (DEC-029 point 3). So
  a lead, a title or a takeaway named by no page is the whole piece's only on such a piece.
  On a piece whose top holds pages, such as a deck or a site, even of one page, it is
  refused, never read as the whole piece's, and so it is where the piece's top cannot be
  read, since whether it holds pages cannot then be told.
- **Where a page is.** The piece's top component declares where its pages lie
  (`briefs.pages_of`), and is read as the check reads it, under the piece's lock
  (`checks.top_of`). Where the piece has no lock yet, it is read under the versions the
  piece's first render would lock (`libraries.move_lock`, DEC-003 point 8). So a draft is
  digested as the designer writes it, before that render (DEC-042 point 7), and what that
  render's search refuses, such as a pinned draft with no lock, refuses the draft.
- **What the record tells.** A text *matches* the digest recorded for its page, kind and
  language, *differs* from it, or has *no entry*. Only a match leaves the text the
  designer's; a text that differs, or that the record lists nothing for, is the asker's.
- **It writes nothing.** No command changes what a brief says (DEC-029 point 4), so the
  entry is given for whoever designs the piece to write into the brief.
"""

from __future__ import annotations

import hashlib
import unicodedata
from collections.abc import Mapping
from typing import Any

from _lib import briefs, checks, layout, libraries, names
from _lib import pipeline as pl

#: The kinds of text a draft is of, and the brief's field a part keeps its entries in.
LEAD, TITLE, TAKEAWAY = "lead", "title", "takeaway"
KINDS = (LEAD, TITLE, TAKEAWAY)
FIELD = "drafts"

#: What a digest begins with: the algorithm that made it.
PREFIX = "sha256:"

#: How a text stands to the record.
MATCHES, DIFFERS, NO_ENTRY = "matches", "differs", "no-entry"


class DraftRefused(Exception):
    """The text asked about cannot be found."""


def normalised(text: str) -> str:
    """`text` as the digest reads it: form C, each run of white space one space, trimmed."""
    return " ".join(unicodedata.normalize("NFC", text).split())


def digest(text: str) -> str:
    """The digest of `text` under the normalisation of `normalised`."""
    return PREFIX + hashlib.sha256(normalised(text).encode("utf-8")).hexdigest()


def entry(kind: str, language: str, text: str) -> dict[str, str]:
    """The entry of the record for `text`, as the brief's part holds it: its kind, its
    language and its digest. The page is the part it lies in."""
    return {"kind": kind, "language": language, "digest": digest(text)}


def part_of(brief: Mapping[str, Any] | None, page: str | None) -> Mapping[str, Any]:
    """The part of the brief for `page`, or for the whole piece where `page` is None;
    empty where the brief has none."""
    if not isinstance(brief, Mapping):
        return {}
    held = brief.get(briefs.PIECE) if page is None else (brief.get(briefs.PAGES) or {}).get(page)
    return held if isinstance(held, Mapping) else {}


def state(part: Mapping[str, Any], kind: str, language: str, text: str) -> str:
    """How `text` stands to the entry `part` records for its kind and language: `matches`,
    `differs`, or `no-entry`."""
    recorded = [
        each
        for each in part.get(FIELD) or []
        if isinstance(each, Mapping)
        and each.get("kind") == kind
        and each.get("language") == language
    ]
    if not recorded:
        return NO_ENTRY
    return MATCHES if any(each.get("digest") == digest(text) for each in recorded) else DIFFERS


def asker_owns(found: str) -> bool:
    """Whether a text in this state is the asker's: every state but a match (DEC-042
    point 7)."""
    return found != MATCHES


def top_of(piece: pl.Piece) -> Mapping[str, Any] | None:
    """The data of the piece's top component, which declares where its pages lie: read under
    the piece's lock, or, where it has none yet, under the versions its first render would
    lock. None where it cannot be read. Raises DraftRefused where the search for those
    versions refuses."""
    if piece.lock or piece.top.partition("/")[0] == names.PIECE:
        return checks.top_of(piece)
    held = libraries.Held(piece.root, piece.location)
    try:
        first = libraries.move_lock(held, pl.needed(piece), pinned=piece.pinned)
    except libraries.LockRefused as exc:
        raise DraftRefused(
            f"the piece has no lock yet to find its pages by, and no first one is found: {exc}"
        ) from exc
    return checks.top_of(piece, first.lock)


def holds_pages(top: Mapping[str, Any]) -> bool:
    """Whether the top `top` holds pages, as a deck's or a site's does, even of one page: its
    layouts are its pages' forms, or a slot of one of its layouts holds pages (DEC-010 point
    5). A top that holds none, such as a figure, is a page alone (DEC-005 point 5)."""
    if layout.page_forms(top) is not None:
        return True
    layouts = top.get("layouts")
    return isinstance(layouts, Mapping) and any(
        isinstance(slot, Mapping) and slot.get("pages") is True
        for decl in layouts.values()
        if isinstance(decl, Mapping) and isinstance(decl.get("slots"), Mapping)
        for slot in decl["slots"].values()
    )


def whole_piece(piece: pl.Piece, kind: str) -> None:
    """Refuses a draft of `kind` named by no page, and so the whole piece's, where the
    piece's top is not a page alone: where it holds pages, even of one page, since each
    entry of such a piece lies in its page's part (DEC-029 point 3), or where it cannot be
    read, so whether it holds pages cannot be told. Raises DraftRefused."""
    top = top_of(piece)
    if top is None:
        raise DraftRefused(
            "the piece's top cannot be read, so whether it holds pages cannot be told: "
            "`pkit visual check` says why"
        )
    if holds_pages(top):
        raise DraftRefused(
            f"a {kind} of a piece whose top holds pages, such as a deck or a site, even of "
            "one page, lies in its page's part: name its page with `--page <id>`"
        )


def text_of(
    piece: pl.Piece,
    brief: Mapping[str, Any] | None,
    page: str | None,
    kind: str,
    language: str,
    at: str | None,
) -> str:
    """The text of the draft: the takeaway the brief's part holds, or the field of the
    content in `language` that the key path `at` names from the page, the page found through
    the top (`top_of`), or from the content's top where `page` is None. Raises DraftRefused
    where it names no text, and where `page` is None on a piece whose top is not a page
    alone (`whole_piece`)."""
    if page is None:
        whole_piece(piece, kind)
    if kind == TAKEAWAY:
        held = part_of(brief, page).get(TAKEAWAY)
        if not isinstance(held, str):
            raise DraftRefused("the brief holds no takeaway there")
        return held
    if at is None:
        raise DraftRefused(f"a {kind} is named by the key path of its field, `--at`")
    content = piece.contents.get(language)
    if not isinstance(content, Mapping):
        raise DraftRefused(f"the piece has no content in `{language}`")
    start: Any = content
    if page is not None:
        top = top_of(piece)
        pages = briefs.pages_of(top, content) if top is not None else None
        if pages is None or page not in pages:
            raise DraftRefused(f"the content in `{language}` holds no page `{page}`")
        start = pages[page]
    why = briefs.named(at, start)
    if why is not None:
        raise DraftRefused(f"`{at}` {why}")
    steps = layout.key_path(at) or []
    for key, item in steps:
        start = start[key]
        if item is not None:
            start = next(e for e in start if isinstance(e, Mapping) and e.get("id") == item)
    if not isinstance(start, str):
        raise DraftRefused(f"`{at}` names no text")
    return start
