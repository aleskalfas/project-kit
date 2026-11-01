"""Where an analysis uses a term: each mention of its names, and of the names it replaces,
in the artefacts in force (the deterministic half of `RS-SAN-008`, DEC-001 point 12).

A term renamed, merged into another or withdrawn leaves each statement that names its
concept by a name it no longer holds to mend. This lists them, by artefact and line, so a
writer finds each one and a reviewer reads the list rather than searching by hand.

- **Read as the links read.** A mention is what `pkit analysis link` reads as one, in the
  same sections, by the same code (`links.Heard`, DEC-004 point 7): a name whole, its
  first letter in either case, the longest mention first, a phrase in another sense and
  an actor's name holding none, and the escape honoured. What the links skip is skipped:
  front matter, headings, bold labels, code, comments, a writer's own links, citations,
  ids and the glossary's head. Each mention is listed, the first or not, in the term's own
  entry too, and in text that stays plain, such as a goal. So the two commands never
  disagree on what a mention is.
- **Every analysis.** The links to terms are written only where an analysis keeps a domain
  model. Their reading holds in every analysis, as a new view's closing section reads it
  (`links.uses`).
- **The names searched.** The term's names as the analysis reads them, as the links match
  them: the name its entry gives it, or the name the glossary's head lists for a term of
  an analysis it builds on, and its noun forms. Then each name its entry's `replaces`
  lists that is not one of them. A name another term of the analysis holds is that term's
  (DEC-001 point 1), so it is not searched, and is listed apart.
- **A withdrawn term** is searched by the same names, so a withdrawal finds each use it
  leaves.
- **One analysis:** the one `--analysis` names, as the diagrams take it (DEC-001 point 2).
  An analysis that builds on it is read by naming that one.
- **Complete, or no answer.** A file in the analysis's places that cannot be read as an
  artefact of its place, or read at all, gives no answer, as the diagrams give none (DEC-003
  point 7). So does a term the analysis neither holds nor lists in its glossary's head.

The analysis is read through the backbone's reading, `pkit friction artefacts --json`
(`backbone.read_analysis`), of the working tree. Nothing is written.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _lib import analyses, citations, id_links, links, schemas, structure
from _lib.model import TERM, VIEW, Analysis, Artefact

#: The version of the document `--json` prints.
SCHEMA_VERSION = 1

#: The kinds whose artefacts in force the uses are read in: each glossary entry, each view,
#: and each kind whose body the links read part by part.
_READ = (TERM, VIEW, *links.PARTED)


class NoAnswer(Exception):
    """Where the analysis uses the term cannot be told in full; the message says why."""


@dataclass(frozen=True)
class Searched:
    """The term asked for, as the analysis reads it: its id, its name, its glossary entry,
    the component of the analysis whose glossary holds that entry where it is another's,
    and the names its uses are searched by — its own (`own`), then those it replaces
    (`replaced`). `held` gives each of its names that another term holds, with that term's
    id: it is not searched."""

    id: str
    name: str
    entry: Artefact
    listed_from: str | None
    own: tuple[str, ...]
    replaced: tuple[str, ...]
    held: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Use:
    """One mention of the term: the artefact in force that holds it, the line it starts on,
    counted from 1 in the artefact's file, its text as written, the name it matched, and
    whether that name is one the term replaces."""

    artefact: Artefact
    line: int
    text: str
    name: str
    replaced: bool


def searched(
    analysis: Analysis, listing: analyses.Listing, folder: str | None, term_id: str
) -> tuple[Searched, links.Vocabulary]:
    """The term `term_id` as the analysis in `folder` reads it, and the vocabulary its uses
    are read by: the links' own (`links.vocabulary`), the term's names its entry in it, the
    term added where it is withdrawn. Raises NoAnswer where `term_id` is no term's id, or
    names no term the analysis holds, in force or withdrawn, or its glossary's head lists
    from an analysis the repository holds."""
    if schemas.id_pattern(TERM).match(term_id) is None:
        raise NoAnswer(f"{term_id} is no term's id, which has the shape TERM-<slug>")
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
    found = Searched(
        term.id,
        term.name,
        entry,
        _component(listing, entry.folder) if entry.folder != folder else None,
        tuple(n for n in own if n not in left),
        tuple(n for n in replaced if n not in left),
        held,
    )
    terms = words.terms if words.term(term.id) is not None else (*words.terms, term)
    matched = {**words.matched, term.id: (*found.own, *found.replaced)}
    return found, links.Vocabulary(tuple(terms), matched, words.actors)


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
            f"{entry.location} gives no name, so its uses cannot be searched; "
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


def files(analysis: Analysis, folder: str | None) -> list[str]:
    """The paths the uses are read in: each file that holds an artefact in force of the
    analysis in `folder` of the kinds read (`_READ`). Raises NoAnswer where a file in the
    analysis's places cannot be read as an artefact of its place, since what it holds
    could not be read."""
    unread = sorted(
        {
            *(s.path for s in analysis.strays if analysis.folders.get(s.path) == folder),
            *(p for p in analysis.unreadable if analysis.folders.get(p) == folder),
        }
    )
    if unread:
        many = len(unread) > 1
        raise NoAnswer(
            f"{', '.join(unread)} cannot be read as "
            f"{'artefacts of their places' if many else 'an artefact of its place'}, so "
            f"the uses {'they hold' if many else 'it holds'} cannot be told; `pkit analysis "
            f"validate` says why"
        )
    return sorted({a.path for a in _in_force(analysis, folder)})


def _in_force(analysis: Analysis, folder: str | None) -> list[Artefact]:
    """The artefacts in force of the analysis in `folder` whose text the links read: each
    glossary entry, each view, and each artefact of the kinds read part by part, in the
    order of their files, then of their places in a file."""
    return sorted(
        (
            a
            for a in analysis.artefacts
            if a.folder == folder
            and not a.withdrawn
            and a.kind in _READ
            and a.entry == (a.kind == TERM)
        ),
        key=lambda a: (a.path, a.span or (0, 0)),
    )


def texts(root: Path, paths: Iterable[str]) -> dict[str, str]:
    """Each of `paths`' text, LF line ends, as the links read it. Raises NoAnswer where one
    cannot be read."""
    found: dict[str, str] = {}
    for rel in paths:
        try:
            found[rel] = (root / rel).read_bytes().decode("utf-8").replace("\r\n", "\n")
        except (OSError, UnicodeDecodeError) as exc:
            raise NoAnswer(f"{rel} could not be read: {exc}") from exc
    return found


def asked(
    analysis: Analysis,
    listing: analyses.Listing,
    folder: str | None,
    read: Mapping[str, str],
    kinds: Mapping[str, structure.Kind],
    words: links.Vocabulary,
) -> set[str]:
    """What the citations of the analysis in `folder` ask the lookup, read as the uses are:
    no mention is read inside a citation, and where a citation ends depends on where it
    leads (DEC-001 point 13)."""
    cites = links.Cites({}, links.component(listing, folder))
    _heard(analysis, listing, folder, read, kinds, words, cites)
    return set(cites.asked)


def uses(
    analysis: Analysis,
    listing: analyses.Listing,
    folder: str | None,
    read: Mapping[str, str],
    kinds: Mapping[str, structure.Kind],
    found: Searched,
    words: links.Vocabulary,
    lookups: Mapping[str, citations.Found],
) -> list[Use]:
    """Each mention of the term `found` names in the artefacts in force of the analysis in
    `folder`, read with `words` (`searched`), by the path of its artefact's file, then its
    line, then where it lies on the line. `read` gives each file's text by its path, LF
    line ends, and `lookups` what the lookup answered for its citations."""
    cites = links.Cites(lookups, links.component(listing, folder))
    replaced = {name.casefold() for name in found.replaced}
    listed = [
        Use(artefact, mention.line, mention.text, mention.name, mention.name.casefold() in replaced)
        for artefact, mention in _heard(analysis, listing, folder, read, kinds, words, cites)
        if mention.term == found.id
    ]
    # The sort is stable, so the mentions on one line keep their order.
    return sorted(listed, key=lambda u: (u.artefact.path, u.line))


def _heard(
    analysis: Analysis,
    listing: analyses.Listing,
    folder: str | None,
    read: Mapping[str, str],
    kinds: Mapping[str, structure.Kind],
    words: links.Vocabulary,
    cites: links.Cites,
) -> list[tuple[Artefact, links.Heard]]:
    """Each mention of a term in the artefacts in force of the analysis in `folder`, with
    the artefact that holds it, read by the links' own functions, each artefact as `plan`
    reads it: a glossary entry below its heading, a view's opening and each of its
    sections, and each part of another kind's body as `kinds` gives its parts."""
    named = id_links.named(analysis, listing, folder)
    found: list[tuple[Artefact, links.Heard]] = []
    for artefact in _in_force(analysis, folder):
        text = read.get(artefact.path)
        if text is None:
            continue
        heard: list[links.Heard] = []
        if artefact.kind == TERM:
            links.glossary(artefact.path, text, [artefact], words, cites, named, heard)
        elif artefact.kind == VIEW:
            links.view(artefact, text, words, cites, None, named, heard)
        else:
            kind = kinds.get(artefact.kind)
            links.document(artefact, text, words, kind, cites, named, heard)
        found += [(artefact, mention) for mention in heard]
    return found


def document(found: Searched, listed: Sequence[Use], component: str | None) -> dict[str, Any]:
    """The `--json` document: `{schema_version, term, uses}`. The term is `{id, name,
    status, location, analysis, listed_from, names, replaces, not_searched}`, each entry of
    `not_searched` `{name, held_by}`, and each use `{id, kind, location, path, line, text,
    name, replaced}`."""
    return {
        "schema_version": SCHEMA_VERSION,
        "term": {
            "id": found.id,
            "name": found.name,
            "status": found.entry.fields.get("status"),
            "location": found.entry.location,
            "analysis": component,
            "listed_from": found.listed_from,
            "names": list(found.own),
            "replaces": list(found.replaced),
            "not_searched": [{"name": name, "held_by": holder} for name, holder in found.held],
        },
        "uses": [
            {
                "id": use.artefact.id,
                "kind": use.artefact.kind,
                "location": use.artefact.location,
                "path": use.artefact.path,
                "line": use.line,
                "text": use.text,
                "name": use.name,
                "replaced": use.replaced,
            }
            for use in listed
        ],
    }


def lines(found: Searched, listed: Sequence[Use], where: str) -> list[str]:
    """The answer for a person: the term, in `where`, the analysis read, and the names
    searched, then each use, one line each, as `<path>:<line>  <artefact>  <text>`, a
    name it replaces marked, or `none`."""
    heading = f"{found.id} — {found.name}"
    heading += " (withdrawn)" if found.entry.withdrawn else ""
    heading += f", in {where}"
    heading += f", listed from {found.listed_from}" if found.listed_from else ""
    said = [
        heading,
        f"  Its names: {', '.join(found.own) or 'none'}",
        f"  The names it replaces: {', '.join(found.replaced) or 'none'}",
    ]
    said += [f"  Not searched: {name}, a name of {holder}" for name, holder in found.held]
    if not listed:
        return [*said, "  Uses: none"]
    said.append("  Uses:")
    for use in listed:
        text = " ".join(use.text.split())
        mark = "  (a name it replaces)" if use.replaced else ""
        holder = use.artefact.id or use.artefact.location
        said.append(f"    {use.artefact.path}:{use.line}  {holder}  {text}{mark}")
    return said
