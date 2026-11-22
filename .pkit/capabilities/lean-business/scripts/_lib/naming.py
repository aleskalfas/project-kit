"""The ids a command gives, and the ids the names a person gives read as (lean-business
DEC-002 point 7; DEC-001 point 3).

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

Every command that names an assumption or a cycle reads the name one way (`named`):

- **Whole, or a part.** A name is the id whole, or its last parts: an assumption's the part
  after its idea, `<variant>--<assumption>`, or its own part, and a cycle's its own part.
- **A part completed.** Where the variant or the idea the command names holds the parts a
  name lacks, they complete it, as a rank's variant completes an assumption's own part.
- **A part looked for.** Otherwise the name reads as the one id of its kind that ends with
  it, among the idea's, or the location's where the command names no idea, as the files
  stand. It is refused where none ends so, or more than one.
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
    """The qualified id a command gives a subject held by `qualifier`: the one `typed`, its
    own part or the whole id, refused where it is taken; else one taken from `text`, numbered
    where that is taken. Raises Refused for a typed id that is no id, or that is taken."""
    if typed is not None:
        own = typed.removeprefix(qualifier + ids.JOIN)
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


# --- the id a name reads as -------------------------------------------------------------------

ASSUMPTION = "assumption"
CYCLE = "cycle"

#: The kinds a name reads as, each with the parts of its id and the form a refusal gives it.
_NAMED = {
    ASSUMPTION: (3, "`<idea>--<variant>--<assumption>`"),
    CYCLE: (2, "`<idea>--<cycle>`"),
}


def named(files: Files, kind: str, given: str, within: str | None = None) -> str:
    """The id of the `kind`, `ASSUMPTION` or `CYCLE`, that the name `given` reads as: the id
    whole; or its last parts, completed by `within`, the variant or the idea the command
    names, where that holds the parts they lack; or else the one id of the kind that ends
    with them, among those of `within`'s idea, or of the location where `within` is None.
    Raises Refused for a name that is no id's last parts, or that no id or more than one
    ends with."""
    parts, written = _NAMED[kind]
    words = given.split(ids.JOIN)
    if len(words) > parts or not all(ids.is_segment(word) for word in words):
        raise Refused(
            f"`{given}` names no {kind}: give its id, {written}, or the last parts of its id"
        )
    lacking = parts - len(words)
    if lacking == 0:
        return given
    scope = within.split(ids.JOIN) if within is not None else []
    if len(scope) >= lacking:
        return ids.qualify(*scope[:lacking], given)
    idea = scope[0] if scope else None
    where = f"of `{idea}`" if idea is not None else "in the location"
    ending = sorted({held for held in _held(files, kind, idea) if held.endswith(ids.JOIN + given)})
    if len(ending) == 1:
        return ending[0]
    if not ending:
        raise Refused(f"`{given}` names no {kind} {where}: no {kind}'s id there ends with it")
    raise Refused(
        f"`{given}` names {len(ending)} {kind}s {where}, {', '.join(f'`{e}`' for e in ending)}: "
        f"give the id of the one you mean"
    )


def _held(files: Files, kind: str, idea: str | None) -> list[str]:
    """The ids of the `kind` that the idea `idea` holds, or the location where it is None,
    as the files stand."""
    try:
        contents = layout.read(files.root, files.location, idea)
    except (listing.ListingFailed, layout.IdRefused) as exc:
        raise Refused(f"the ideas' files cannot be read: {exc}") from exc
    found: list[str] = []
    for name, held in contents.ideas.items():
        if kind == CYCLE:
            found.extend(ids.qualify(name, own) for own in held.cycles)
            continue
        for variant in held.variants.values():
            data = variant.assumptions.data if variant.assumptions is not None else None
            listed = data.get("assumptions") if data is not None else None
            if isinstance(listed, list):
                found.extend(
                    str(item["id"])
                    for item in listed
                    if isinstance(item, Mapping) and isinstance(item.get("id"), str)
                )
    return found
