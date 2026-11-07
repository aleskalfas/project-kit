"""What to search for when a term changes: the names a reader looks for in the analysis
when the term is renamed, merged into another or withdrawn (DEC-001 point 12).

Each artefact names a concept by the one term that defines it, and whoever changes a term
finds its uses and mends them in the same change (DEC-001 point 12). This gives the names
to search for, read from front matter alone, since a tool takes data from front matter
and reads no body's other text (DEC-001 point 1; DEC-006 point 3). The search is the
reader's.

- **Its names.** The term's name as the analysis reads it, as the links match it: the name
  its entry gives it, or the name the glossary's head lists for a term of an analysis it
  builds on, and its noun forms (`links.vocabulary`).
- **The names it replaces,** as its entry's `replaces` lists them, but one of its names.
- **A name another term holds.** A name or a noun form of another term the analysis reads
  is that term's (DEC-001 point 1). So it is listed apart, as no name to search for this
  one.
- **Where else it is listed.** Each analysis the project lists whose glossary's head lists
  the term, by the name it lists, read from that glossary's front matter (DEC-001
  point 2).
- **A withdrawn term** gives its names alike, since a withdrawal leaves its uses to mend.
- **One analysis:** the one `--analysis` names, as the diagrams take it (DEC-001 point 2).
- **A glossary that cannot be read.** Where a glossary of the analyses the project keeps
  cannot be read, the names cannot be told, so nothing is answered.

The analysis is read through the backbone's reading, `pkit friction artefacts --json`
(`backbone.read_analysis`), of the working tree. Nothing is written.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from _lib import analyses, links, schemas
from _lib.model import TERM, Analysis, Artefact

#: The version of the document `--json` prints.
SCHEMA_VERSION = 1


class NoAnswer(Exception):
    """The names to search for cannot be told; the message says why."""


@dataclass(frozen=True)
class Listed:
    """An analysis whose glossary's head lists the term: its component, and the name it
    lists the term by."""

    analysis: str
    name: str


@dataclass(frozen=True)
class Searched:
    """The term asked for, as the analysis reads it, and what to search for: its id, its
    name, its glossary entry, the component of the analysis whose glossary holds that entry
    where it is another's, its names (`own`), the names it replaces (`replaced`), each name
    of either that another term holds, with that term's id (`held`), left out of both, and
    each analysis whose glossary's head lists it (`listed_in`)."""

    id: str
    name: str
    entry: Artefact
    listed_from: str | None
    own: tuple[str, ...]
    replaced: tuple[str, ...]
    held: tuple[tuple[str, str], ...]
    listed_in: tuple[Listed, ...]


def searched(
    analysis: Analysis, listing: analyses.Listing, folder: str | None, term_id: str
) -> Searched:
    """The term `term_id` as the analysis in `folder` reads it, and the names to search for
    it by. Raises NoAnswer where `term_id` is no term's id, where a glossary of the
    analyses the project keeps cannot be read, or where it names no term the analysis
    holds, in force or withdrawn, or its glossary's head lists from an analysis the
    repository holds."""
    if schemas.id_pattern(TERM).match(term_id) is None:
        raise NoAnswer(f"{term_id} is no term's id, which has the shape TERM-<slug>")
    _readable(analysis, listing)
    words = links.vocabulary(analysis, listing, folder)
    term, entry = _term(analysis, listing, folder, term_id, words)
    holders: dict[str, str] = {}
    for other in words.terms:
        if other.id != term.id:
            for name in (other.name, *other.noun_forms):
                holders.setdefault(name.casefold(), other.id)
    own = _once((term.name, *term.noun_forms))
    taken = {name.casefold() for name in own}
    replaced = [n for n in _once(links.replaced(entry)) if n.strip() and n.casefold() not in taken]
    held = tuple(
        (name, holders[name.casefold()]) for name in (*own, *replaced) if name.casefold() in holders
    )
    left = {name for name, _holder in held}
    home = _component(listing, entry.folder)
    return Searched(
        term.id,
        term.name,
        entry,
        home if entry.folder != folder else None,
        tuple(n for n in own if n not in left),
        tuple(n for n in replaced if n not in left),
        held,
        _listed_in(analysis, listing, term.id, home),
    )


def _readable(analysis: Analysis, listing: analyses.Listing) -> None:
    """Raises NoAnswer where a glossary of an analysis the project keeps cannot be read as
    one, since the terms it holds, and the names its head lists, could not be told."""
    kept = set(listing.kept())
    unread = sorted(
        {
            *(
                s.path
                for s in analysis.strays
                if s.kind == TERM and analysis.folders.get(s.path) in kept
            ),
            *(
                p
                for p in analysis.unreadable
                if analysis.files.get(p) == TERM and analysis.folders.get(p) in kept
            ),
        }
    )
    if unread:
        raise NoAnswer(
            f"{', '.join(unread)} cannot be read as a glossary, so the names of the terms "
            f"it holds cannot be told; `pkit analysis validate` says why"
        )


def _term(
    analysis: Analysis,
    listing: analyses.Listing,
    folder: str | None,
    term_id: str,
    words: links.Vocabulary,
) -> tuple[links.Term, Artefact]:
    """The term `term_id` as the analysis in `folder` reads it, and its glossary entry: one
    the links read (`words`), else a withdrawn one of its own, else a withdrawn one its
    glossary's head lists, by the name the head lists."""
    entry = analysis.of(term_id, TERM)
    read = words.term(term_id)
    if read is not None and entry is not None:
        return read, entry
    if entry is not None and entry.folder == folder:
        return _named(entry), entry
    head = analyses.head(analysis, folder) if listing.several else None
    for taken in head.taken if head is not None else ():
        other = listing.of_component(taken.analysis)
        for listed_id, listed_name in taken.terms:
            if listed_id != term_id or other is None:
                continue
            if entry is not None and entry.folder == other.folder:
                term = _named(entry)
                return dataclasses.replace(term, name=listed_name, entry_name=term.name), entry
    raise NoAnswer(
        f"no term {term_id} in {listing.named(folder)}, in force or withdrawn, nor one its "
        f"glossary's head lists from an analysis the repository holds"
    )


def _named(entry: Artefact) -> links.Term:
    term = links.term_of(entry)
    if term is None:
        raise NoAnswer(
            f"{entry.location} gives no name, so its names cannot be told; "
            f"`pkit analysis validate` says why"
        )
    return term


def _once(names: Iterable[str]) -> tuple[str, ...]:
    """`names` in their order, each once, ignoring case."""
    found: dict[str, str] = {}
    for name in names:
        found.setdefault(name.casefold(), name)
    return tuple(found.values())


def _component(listing: analyses.Listing, folder: str | None) -> str | None:
    listed = listing.of_folder(folder)
    return listed.component if listed is not None else None


def _listed_in(
    analysis: Analysis, listing: analyses.Listing, term_id: str, home: str | None
) -> tuple[Listed, ...]:
    """Each analysis the project lists whose glossary's head lists `term_id` from `home`,
    the analysis whose glossary holds its entry, in the order the project lists them."""
    if home is None:
        return ()
    found: list[Listed] = []
    for listed in listing.analyses:
        head = analyses.head(analysis, listed.folder)
        taken = head.of(home) if head is not None else None
        for listed_id, listed_name in taken.terms if taken is not None else ():
            if listed_id == term_id:
                found.append(Listed(listed.component, listed_name))
                break
    return tuple(found)


def document(found: Searched, component: str | None) -> dict[str, Any]:
    """The `--json` document: `{schema_version, term, names, replaces, not_searched,
    listed_in}`. The term is `{id, name, status, location, analysis, listed_from}`, each
    entry of `not_searched` `{name, held_by}`, and each entry of `listed_in` `{analysis,
    name}`."""
    return {
        "schema_version": SCHEMA_VERSION,
        "term": {
            "id": found.id,
            "name": found.name,
            "status": found.entry.fields.get("status"),
            "location": found.entry.location,
            "analysis": component,
            "listed_from": found.listed_from,
        },
        "names": list(found.own),
        "replaces": list(found.replaced),
        "not_searched": [{"name": name, "held_by": holder} for name, holder in found.held],
        "listed_in": [{"analysis": item.analysis, "name": item.name} for item in found.listed_in],
    }


def lines(found: Searched, where: str) -> Sequence[str]:
    """The answer for a person: the term, in `where`, the analysis read, then its names,
    the names it replaces, each name another term holds and each analysis whose
    glossary's head lists it, one line each."""
    heading = f"{found.id} — {found.name}"
    heading += " (withdrawn)" if found.entry.withdrawn else ""
    heading += f", in {where}"
    heading += f", listed from {found.listed_from}" if found.listed_from else ""
    said = [
        heading,
        f"  Its names: {', '.join(found.own) or 'none'}",
        f"  The names it replaces: {', '.join(found.replaced) or 'none'}",
    ]
    said += [f"  Not searched for it: {name}, a name of {holder}" for name, holder in found.held]
    said += [
        f"  Listed in the glossary's head of {item.analysis}, as {item.name}"
        for item in found.listed_in
    ]
    return said
