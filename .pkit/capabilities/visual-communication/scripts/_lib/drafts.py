"""The makers' record of drafts, in a piece's brief (visual-communication DEC-042 point 7,
DEC-029 points 2 to 4): for each lead, title or takeaway the designer drafted and the asker
has not seen, an entry naming its page, its kind and the language of its text, with a digest
of that text, never the text.

- **The digest** is `sha256:` and the hex of SHA-256 over the text *normalised*: Unicode
  normalisation form C, then each run of white space, a line break among them, made one
  space, then the ends trimmed. So a reflowed or re-indented text keeps its digest, and a
  changed word, case or mark changes it. Where the text is a takeaway it is the brief's own;
  where a lead or a title, it is the content's field of the language, named by its key path
  from the page, or from the content's top where the piece is one page.
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

from _lib import briefs, layout
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


def text_of(
    piece: pl.Piece,
    brief: Mapping[str, Any] | None,
    top: Mapping[str, Any] | None,
    page: str | None,
    kind: str,
    language: str,
    at: str | None,
) -> str:
    """The text of the draft: the takeaway the brief's part holds, or the field of the
    content in `language` that the key path `at` names from the page, or from the content's
    top where `page` is None. Raises DraftRefused where it names no text."""
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
