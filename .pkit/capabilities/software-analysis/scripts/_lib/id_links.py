"""The links of each mention of an analysis artefact by its id (DEC-001 point 13).

**What a mention is** (`MENTION`): an artefact's id, whole, in running text — a use
case's, a journey's or a requirement's, `UC-082`, `JRN-004`, `REQ-012`, in any spelling of
its number, or an actor's, a view's or a term's, `ACT-developer`, `VIEW-orders`,
`TERM-change`. No letter, digit, hyphen, slash, underscore or `#` joins it on either
side, and a full stop after it joins it where a letter or a digit follows, as in a file's
name. So `UC-082-setup.md` and `TERM-change-check` hold no mention of `UC-082` or
`TERM-change`. An analysis's component may stand before the id, with a colon:
`core:UC-021` (DEC-001 point 2).

**What it names** (`Named`): an id alone names an artefact of the analysis whose artefact
holds the text; an id written with an analysis's component names an artefact of that
analysis, where the text's analysis builds on it, as the settings list it. Any other
names nothing, and takes no link. A withdrawn artefact is named too, since an id names
one artefact for good (DEC-001 point 3).

**What it links to** (`Target.link`): the artefact's file, by a path from the folder of
the file that holds the mention; a term's entry in its glossary, by the entry's anchor,
the slug of its heading `<id> — <name>`, as the links to terms lead (`_lib/links.py`).

**Where** (`wanted`): the first mention of each artefact in a section, never one of the
artefact that holds the text, nor one in a span the caller keeps plain. A journey's step
line links its use case's id whatever stands before it, and counts first in its part. The
sections, and what is skipped, are the links to terms' (`_lib/links.py`), but a bold
label: a seam's `**Needs from UC-064 (outside this journey):**` and a precondition's
`**From UC-003:**` name artefacts, so their ids take links. An id in code is no mention.

**Held by the check** (`is_held`): a Markdown link whose words are a mention whole and
whose target is a file's path in the repository, with no scheme and no heading but a
term's entry, is the command's, whoever wrote it. A link to a web address, or to another
heading, such as a view's section on one concept, is the writer's own.

**Set aside by friction** (`TARGET`): each place of the capability declares the form of
the targets the command writes, a path to a file named by an artefact's id or to a view's
file by its number, so the core's friction reads each such link as its words alone
(COR-050 point 5). A term's id links in the form of a link to a term, which the places
declare already.
"""

from __future__ import annotations

import posixpath
import re
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass

from _lib import analyses, forms
from _lib.model import NUMBERED, PREFIX, QUALIFIER, TERM, Analysis, identity

#: The prefixes of the ids that are numbers, and of those that are slugs (DEC-001 point 3).
_NUMBERED = "|".join(sorted({PREFIX[kind] for kind in NUMBERED}))
_SLUGGED = "|".join(sorted({p for kind, p in PREFIX.items() if kind not in NUMBERED}))

#: An analysis's component, as a reference across analyses names it (DEC-001 point 2).
_COMPONENT = r"[a-z](?:[a-z0-9-]*[a-z0-9])?"

#: A mention of an artefact's id: the analysis's component and a colon, or none, then the
#: id, whole.
MENTION = re.compile(
    rf"(?<![\w/#-])(?:(?P<analysis>{_COMPONENT}){re.escape(QUALIFIER)})?"
    rf"(?P<id>(?:{_NUMBERED})-[0-9]+|(?:{_SLUGGED})-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)"
    r"(?![\w-]|\.[A-Za-z0-9])"
)

#: A link's target with a scheme, such as a web address: the writer's own.
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")

#: The target of a link the command writes on an id, the form each place of the capability
#: declares as a derived link (COR-050 point 5): a path with no scheme to a file named by a
#: use case's, a journey's, a requirement's or an actor's id; or to a view's file, named by
#: its number, in the folder of views or beside the file. A term's id links to its entry,
#: in the form of a link to a term.
TARGET = (
    r"(?:[^()\s:#]*/)?(?:(?:UC|JRN|REQ)-[0-9]+(?:-[^()\s:#/]*)?|ACT-[^()\s:#/]+)\.md"
    r"|(?:(?:[^()\s:#]*/)?domain-model/)?[0-9]+-[^()\s:#/]*\.md"
)


@dataclass(frozen=True)
class Target:
    """An artefact a mention names: its id, its file, and, for a term, its entry's anchor
    in that file."""

    id: str
    path: str
    anchor: str | None = None

    def link(self, from_path: str) -> str:
        """Where a link to it leads from the file at `from_path`."""
        if self.anchor is not None and from_path == self.path:
            return f"#{self.anchor}"
        rel = posixpath.relpath(self.path, posixpath.dirname(from_path) or ".")
        return f"{rel}#{self.anchor}" if self.anchor is not None else rel


@dataclass(frozen=True)
class Named:
    """The artefacts the text of one analysis names by id: its own, by id, and those of
    each analysis it builds on, by that analysis's component, then by id. Each id is keyed
    as `model.identity` spells it, so `UC-82` names `UC-082`."""

    own: Mapping[str, Target]
    built_on: Mapping[str, Mapping[str, Target]]

    def of(self, analysis: str | None, artefact_id: str) -> Target | None:
        """The artefact a mention names, written with `analysis` or alone; `None` where it
        names none."""
        table = self.own if analysis is None else self.built_on.get(analysis, {})
        return table.get(identity(artefact_id))


def named(analysis: Analysis, listing: analyses.Listing, folder: str | None) -> Named:
    """What the text of the analysis in `folder` names by id: each artefact of its own, in
    force or withdrawn, and, where the settings list it, each of every analysis it builds
    on and the repository holds (DEC-001 points 2 and 14)."""
    built_on: dict[str, Mapping[str, Target]] = {}
    listed = listing.of_folder(folder) if listing.several else None
    for entry in listed.builds_on if listed is not None else ():
        other = listing.of_component(entry.analysis)
        if other is not None:
            built_on[entry.analysis] = _held(analysis, other.folder)
    return Named(_held(analysis, folder), built_on)


def _held(analysis: Analysis, folder: str | None) -> dict[str, Target]:
    """Each artefact of the analysis in `folder`, by its id: a term at its entry's anchor,
    the slug of its heading, and none that gives no name. Of two that share an id, which
    validation refuses, the first."""
    found: dict[str, Target] = {}
    for artefact in analysis.artefacts:
        if artefact.folder != folder or not artefact.id:
            continue
        anchor = None
        if artefact.kind == TERM:
            name = artefact.fields.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            anchor = forms.heading_slug(f"{artefact.id} — {name}")
        found.setdefault(identity(artefact.id), Target(artefact.id, artefact.path, anchor))
    return found


def is_held(words: str, target: str) -> bool:
    """Whether a Markdown link with `words` and `target` is one the command writes, or one
    written by hand that it holds as its own: its words a mention whole, and its target a
    file's path in the repository, with no scheme, naming no heading but a term's entry.
    A link to a web address, or to another heading, such as a view's section on one
    concept, is the writer's own."""
    if MENTION.fullmatch(words) is None or not target or _SCHEME.match(target):
        return False
    _file, mark, anchor = target.partition("#")
    return not mark or anchor.startswith(_ENTRY_ANCHOR)


#: How the anchor of a term's entry opens: the slug of its heading, `<TERM-id> — <name>`.
_ENTRY_ANCHOR = "term-"


@dataclass(frozen=True)
class Mention:
    """A mention of an id in a text: where it lies, the analysis written before it, if
    any, and the id."""

    start: int
    end: int
    analysis: str | None
    id: str


def mentions(text: str, skipped: Iterable[tuple[int, int]]) -> list[Mention]:
    """Each mention of an id in `text`, none in a span of `skipped`."""
    chars = list(text)
    for start, end in skipped:
        for k in range(start, min(end, len(chars))):
            if chars[k] != "\n":
                chars[k] = "\x00"
    return [
        Mention(m.start(), m.end(), m["analysis"], m["id"])
        for m in MENTION.finditer("".join(chars))
    ]


@dataclass(frozen=True)
class Wanted:
    """A link the command writes on a mention: its span, its target, and the artefact's
    id."""

    start: int
    end: int
    target: str
    artefact: str


def wanted(
    found: Sequence[Mention],
    plain: Collection[tuple[int, int]],
    named: Named,
    own: str | None,
    path: str,
    first: Collection[tuple[int, int]] = (),
) -> list[Wanted]:
    """The links the command writes on the mentions of one section, `found`, in the file at
    `path`: the first mention of each artefact, outside each span of `plain`, which stays
    plain, and none of `own`, the artefact that holds the text. Each mention in a span of
    `first`, a journey's step line, takes its link whatever stands before it, and counts
    first: another mention of its artefact in the section takes none."""
    leading = [m for m in found if _within(m, first)]
    seen: set[tuple[str, str | None]] = set()
    out: list[Wanted] = []
    for mention in [*leading, *(m for m in found if not _within(m, first))]:
        if _within(mention, plain):
            continue
        target = named.of(mention.analysis, mention.id)
        if target is None:
            continue
        if mention.analysis is None and own is not None and identity(own) == identity(target.id):
            continue
        key = (target.path, target.anchor)
        if key in seen and not _within(mention, first):
            continue
        seen.add(key)
        out.append(Wanted(mention.start, mention.end, target.link(path), target.id))
    return sorted(out, key=lambda w: w.start)


def _within(mention: Mention, spans: Iterable[tuple[int, int]]) -> bool:
    return any(mention.start < end and start < mention.end for start, end in spans)
