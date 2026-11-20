"""The ids a command gives (lean-business DEC-002 point 7; DEC-001 point 3).

A command gives each id it writes, from the person's `--id` or from the text of what it
names:

- **From the text** (`from_text`): accents stripped, the ASCII letters and digits kept, the
  first words joined in kebab case, a leading digit given a letter before it, and the kind's
  own word where nothing is left.
- **Qualified** by what holds it (`ids.qualify`): an entry and an assumption by its variant,
  a variant, an experiment and a cycle by its idea.
- **Unique, and never given again** (`in_use`, `given`). An id is unique across its canvas
  or its idea, and is never one a reference or an assumption's source still names, even
  where nothing holds it any more: a reference that names nothing, or an assumption whose
  entry was removed, would then name the new subject. An id taken from the text is told
  apart by a number after it; one the person typed is refused instead.
- **Kept.** An id never changes when the text it was taken from does.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping
from typing import Any

from _lib import ids, layout, listing
from _lib.reading import ReadError, load_yaml
from _lib.writes import Files, Refused

#: How many of the text's words an id takes.
WORDS = 5

#: The letter a leading digit is given before it, so the id begins with a letter.
LEADING = "n"

_WORD = re.compile(r"[a-z0-9]+")
_APOSTROPHES = re.compile("['\u2019]")
_REFERENCE = re.compile(r"^\[[a-z]+:(.+)\]$")


def from_text(text: str, fallback: str) -> str:
    """The id segment the text `text` gives, or `fallback` where it gives none."""
    folded = unicodedata.normalize("NFKD", _APOSTROPHES.sub("", text))
    plain = folded.encode("ascii", "ignore").decode("ascii").lower()
    words = _WORD.findall(plain)[:WORDS]
    if not words:
        return fallback
    if words[0][0].isdigit():
        words[0] = LEADING + words[0]
    return "-".join(words)


def in_use(files: Files, idea: str) -> set[str]:
    """Every id the idea's files hold or name, as the write `files` leaves them so far: each
    subject's and each entry's id, and each id a reference, a link or an assumption's source
    names."""
    try:
        contents = layout.read(files.root, files.location, idea)
    except (listing.ListingFailed, layout.IdRefused) as exc:
        raise Refused(f"the idea's files cannot be read: {exc}") from exc
    held = contents.ideas.get(idea)
    found: set[str] = set()
    read: dict[str, Any] = {}
    if held is not None:
        every = [held.goal, *held.experiments.values(), *held.cycles.values()]
        for variant in held.variants.values():
            every.extend((variant.canvas, variant.assumptions))
        read = {file.rel: file.data for file in every if file is not None}
    for rel, text in files.texts.items():
        if text is None:
            read.pop(rel, None)
            continue
        try:
            read[rel] = load_yaml(text, rel)
        except ReadError:
            continue
    for data in read.values():
        found.update(_named(data))
    return found


def _named(value: object) -> Iterable[str]:
    if isinstance(value, Mapping):
        for item in value.values():
            yield from _named(item)
    elif isinstance(value, list):
        for item in value:
            yield from _named(item)
    elif isinstance(value, str):
        reference = _REFERENCE.match(value)
        found = reference.group(1) if reference else value
        if ids.is_idea_qualified(found) or ids.is_variant_qualified(found):
            yield found


def given(qualifier: str, *, typed: str | None, text: str, fallback: str, taken: set[str]) -> str:
    """The qualified id a command gives a subject held by `qualifier`: the one `typed`,
    refused where it is taken; else one taken from `text`, numbered where that is taken.
    Raises Refused for a typed id that is no id, or that is taken."""
    if typed is not None:
        own = typed.rsplit(ids.JOIN, 1)[-1] if typed.startswith(qualifier + ids.JOIN) else typed
        if not ids.is_segment(own):
            raise Refused(
                f"`{typed}` is no id: an id is words of lower-case letters and digits, the "
                f"first beginning with a letter, joined by single hyphens"
            )
        qualified = ids.qualify(qualifier, own)
        if qualified in taken:
            raise Refused(
                f"the id `{qualified}` is taken: something holds it, or a reference or an "
                f"assumption's source still names it, and an id named is never given again"
            )
        return qualified
    base = from_text(text, fallback)
    qualified = ids.qualify(qualifier, base)
    number = 2
    while qualified in taken:
        qualified = ids.qualify(qualifier, f"{base}-{number}")
        number += 1
    return qualified
