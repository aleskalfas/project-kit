"""The links between an analysis's terms and its views (DEC-004 point 7).

Where an analysis keeps a domain model — its `domain-model/` folder holds a view
(`keeps_domain_model`) — its terms and its views link to each other. The term's
link to the section that explains it is `_lib/views.py`'s. This module writes, and
reads back, the two others:

- **A section's link to its term.** Each section of a view in force opens with an
  unlabelled line, `Defined in [<term id>](<glossary>#<anchor>).` (`defined`), right
  below its heading. The k-th section links the k-th term `explains` lists. The line
  read back as one is only the section's first line that is not blank, written in
  that form, its link a link to a glossary entry from the section's own term
  (`defined_at`). Any other line of a view in that form, outside fenced code, is a
  link written by hand where the command writes none: it is extra, and the command
  takes it out. A line in another form, or in fenced code, is the writer's, and is
  left as written.
- **A mention's link to its term.** In a view's opening and each of its sections,
  in each glossary entry's section below its heading, and in each part of the body
  of an actor, a use case, a journey and a requirement in force (`document`), the
  first mention of a term is linked to its entry, `[<mention>](<glossary>#<anchor>)`.

**A part of the four kinds** (`PARTED`) opens at each heading and at each label its
kind declares, and runs to the next, as the structure finds its marks
(`structure.marks`). The kind is read as `parted` gives it, whatever any rule's status:
as shipped, relabelled by the project's own structures, each label their groups add
opening a part too, and a part found by its shipped label as well. What says a datum
again is read for no mention, so it stays plain as the datum does, and the form that
holds it to the datum still holds (`_quiet`):

- a use case's and a journey's goal, the part whose id is `goal`, which states a need
- each step's line in a journey's steps, the part whose id is `steps`, which gives a
  use case's title, its hand-overs read as any text
- the first sentence of an actor's opening, which gives its `summary` where the
  front matter gives one (`forms.first_sentence_end`)

A link to a glossary entry written there by hand is extra, and the command takes it out.

**The entry's anchor** is the slug of its heading, `## <id> — <name>`, as COR-050
point 2 makes it (`Term.anchor`), so it changes only when the term is renamed. A
link's target is a path from the folder of the file that holds it, or the anchor
alone in the glossary itself (`Term.target`).

**What a mention is** (`Vocabulary`): a term's name, or one of its declared `noun-forms`, as
running text writes it, its first letter in either case. The terms are those in
force of the analysis, and those its glossary's head lists from an analysis the
repository holds, read from that analysis's own front matter. A name two of them
share is no mention of either, so nothing is linked by it: validation refuses the
pair (DEC-001 points 1 and 2). The safeguards:

- **Whole words:** no letter, digit, hyphen, slash or underscore joins a mention on
  either side. An apostrophe is no joiner, so "order's" holds a mention of "order".
- **The longest first:** of mentions that overlap, the one that starts first is
  taken, and of two that start together the longer (`_chosen`). A mention of the
  section's own term is taken too, so a shorter term never links inside it, and it
  takes no link.
- **What is skipped** (`_skipped`): fenced code, headings, the lines that link a
  term and its section, reference definitions, comments, code spans, links,
  autolinks, HTML tags, bare URLs, and a bold run that opens a line or a list
  item, a label.
- **Another sense:** a phrase a term lists in `other-senses` is never a mention of
  that term. Another term inside the phrase may still be mentioned.
- **An actor's name:** the name of an actor in force of the analysis, or of one its
  glossary's head lists, holds no mention of a term whose name is only part of it,
  such as "component" in "component author". An actor named by its name uses no
  concept. A term whose name is the actor's whole name is still mentioned by it.
- **The escape:** `<!-- pkit:not-the-term -->`, with nothing but spaces after it,
  marks the mention that follows as no mention: it takes no link, and the next
  mention counts as the first.

**Once in each section:** only a term's first mention is linked, and a term is
never linked in its own section or its own entry. The command's links are read
back by their target: a Markdown link to a glossary entry, `glossary.md#term-…` by
a path with no scheme, or `#term-…` alone (`_TERM_LINK`). Each such link, whoever
wrote it, is unwritten first and then written again where it belongs, so a link
written by hand is held as the command's. Another link is the writer's, and its
text is skipped.

**A view's closing section** (`closing`). Each view in force ends with a section headed
`What is built on these concepts`, which opens with one sentence that says what it lists
(`CLOSING_OPENING`). Under each concept it explains, labelled by its section's heading,
it lists each use case, journey and requirement in force of its analysis that links the
concept's term: the use cases first, then the journeys, then
the requirements, each in the order of their numbers, linked by its id and its title as
the overview links it. A concept nothing links reads `None.` An artefact links a term
where its body, as the command writes it, holds a link to the term's entry
(`terms_linked`). An analysis that builds on this one is never read, since dependencies
run one way. The section is no part of the view's structure: its heading, outside fenced
code, opens it, and it runs to the next heading of its level or the file's end
(`closing_spans`). The command writes it last, in place of any it held, and reads none
of it for a mention.

The rewrite reads a body only to place its links, and the links back from each view
to what uses its terms, and takes its data from front matter and the declared
structures alone: each term's id, name, noun forms and other senses, each view's
`explains`, whether an actor gives a `summary`, and the labels that open each part
(DEC-001 point 1). It never changes the number of a body's lines, but where it adds a
section's link to its term, takes out a line in that form, or writes a view's closing
section.
"""

from __future__ import annotations

import dataclasses
import functools
import posixpath
import re
from collections import Counter
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from _lib import analyses, citations, forms, project_structure, structure, views
from _lib.model import (
    ACTOR,
    EXPLAINS,
    JOURNEY,
    KINDS,
    REQUIREMENTS,
    TERM,
    USE_CASE,
    VIEW,
    Analysis,
    Artefact,
    number_in,
)

#: The kinds whose bodies take the mentions' links one part at a time, beside the glossary
#: and the views (DEC-004 point 7).
PARTED = (ACTOR, USE_CASE, JOURNEY, *REQUIREMENTS)

#: The permanent ids of the parts that say a datum again: a goal states a need, and a
#: journey's steps give each use case's title. An actor's opening gives its summary.
GOAL, STEPS, SUMMARY = "goal", "steps", "summary"

#: A term's other noun forms, and the phrases in which its name has another sense (DEC-001
#: point 1).
NOUN_FORMS, OTHER_SENSES = "noun-forms", "other-senses"

#: The comment that marks the mention right after it as no mention of a term.
ESCAPE = "<!-- pkit:not-the-term -->"

#: What a section's link to its term opens with.
DEFINED = "Defined in"

#: The heading of a view's closing section, which links what uses its concepts (DEC-004
#: point 7), and the kinds it lists under each concept, in their order.
CLOSING = "What is built on these concepts"
LISTED: tuple[str, ...] = (USE_CASE, JOURNEY, *REQUIREMENTS)

#: The sentence that opens a view's closing section, before its concepts' lists.
CLOSING_OPENING = (
    "Each concept below lists the use cases, journeys and requirements whose text links its term."
)

#: A line that heads a view's closing section, its spaces as any.
_CLOSING_LINE = re.compile(rf"^##[ \t]+{re.escape(CLOSING)}[ \t]*$")

#: The target of each link a view's closing section writes, a path from the view's folder
#: to a use case's, a journey's or a requirement's file: the form the views' places
#: declare, so friction reads each such link as its words alone (COR-050 point 5).
CLOSING_TARGET = (
    r"(?:\.\./)+(?:use-case-model/(?:use-cases|journeys)|requirements/"
    r"(?:quality|functional|constraints))/[^()\s:#]*\.md"
)

#: How a written link departs from what the command writes, and a citation that takes no
#: link since it resolves to nothing (DEC-001 point 13).
MISSING, EXTRA, STALE, UNRESOLVED = "missing", "extra", "stale", "unresolved"

#: The target of a link to a glossary entry: a path with no scheme to a `glossary.md`, or
#: the anchor alone, `#term-…`.
_ENTRY = r"(?:[^()\s:#]*/)?glossary\.md#term-[^()\s]*|#term-[^()\s]*"

#: A Markdown link to a glossary entry, as the command writes one: its text, and its
#: target.
_TERM_LINK = re.compile(rf"(?<!!)\[(?P<text>[^\[\]]+)\]\((?P<target>{_ENTRY})\)")

#: An inline Markdown link, its text holding brackets one deep: its text, and its target.
#: The links of citations the command writes are those `citations.is_cited_link` reads so.
_ANY_LINK = re.compile(r"(?<!!)\[(?P<text>(?:[^\[\]]|\[[^\[\]]*\])+)\]\((?P<target>[^()\s]+)\)")

#: A line in the form of a section's link to its term, on its own: the term's id, and its
#: link to a glossary entry. In a view, outside fenced code, it is read for no mention:
#: it is the section's link, or one the command takes out (`with_definitions`).
DEFINED_LINE = re.compile(rf"^{DEFINED} \[(?P<id>[^\[\]\s]+)\]\((?P<target>{_ENTRY})\)\.\s*$")

#: A line that links a term to its section, read for no mention.
_EXPLAINED_LINE = re.compile(r"^[ \t]*Explained in \[")

#: What hides a whole line from the mentions: the opening of fenced code, a heading,
#: and a reference definition.
_FENCE = re.compile(
    r"^[ \t]*(?:>[ \t]*)*(?:(?:[-+*]|[0-9]{1,9}[.)])[ \t]+(?:>[ \t]*)*)*(`{3,}|~{3,})(.*)$"
)
_HEADING = re.compile(r"^#{1,6}(?:[ \t]|$)")
_REFERENCE = re.compile(r"^[ \t]{0,3}\[[^\]\n]+\]:")

#: What hides a part of a line: a bold run that opens a line or a list item, a label.
_LABEL = re.compile(
    r"^[ \t]*(?:>[ \t]*)*(?:(?:[-+*]|[0-9]{1,9}[.)])[ \t]+)?(\*\*[^*\n]+?\*\*)", re.M
)

#: What hides a run of text, a line's end included: a comment, a code span, a link or
#: an image, an autolink, an HTML tag and a bare URL.
_INLINE = (
    re.compile(r"<!--.*?-->", re.S),
    re.compile(r"(?<!`)(`+)(?!`).+?(?<!`)\1(?!`)", re.S),
    re.compile(r"!?\[(?:[^\[\]]|\[[^\[\]]*\])*\](?:\([^()]*(?:\([^()]*\)[^()]*)*\)|\[[^\[\]]*\])"),
    re.compile(r"<[A-Za-z][A-Za-z0-9+.-]*:[^<>\s]*>"),
    re.compile(r"</?[A-Za-z][A-Za-z0-9-]*(?:\s[^<>]*)?/?>"),
    re.compile(r"\b(?:https?|ftp)://[^\s<>()]+"),
)

#: The escape, its spaces as any.
_ESCAPE = re.compile(r"<!--\s*pkit:not-the-term\s*-->")

#: What joins a mention to the text beside it, so that it is no whole word.
_JOINER = r"[\w/-]"


# --- the terms ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class Term:
    """A term whose mentions are linked: its id, its name, the path of the glossary that
    holds its entry, the other noun forms it declares, and the phrases in which its name
    has another sense (DEC-001 point 1)."""

    id: str
    name: str
    glossary: str
    noun_forms: tuple[str, ...] = ()
    other_senses: tuple[str, ...] = ()
    entry_name: str | None = None  # the name its entry gives it, where it is mentioned by another

    @property
    def anchor(self) -> str:
        """The slug of its entry's heading, `<id> — <name>`, by the name its entry gives it
        (COR-050 point 2)."""
        return forms.heading_slug(f"{self.id} — {self.entry_name or self.name}")

    def target(self, from_path: str) -> str:
        """Where a link to its entry leads from the file at `from_path`."""
        if from_path == self.glossary:
            return f"#{self.anchor}"
        return f"{_relative(self.glossary, posixpath.dirname(from_path) or '.')}#{self.anchor}"


@functools.cache
def _relative(path: str, start: str) -> str:
    """`path` from the folder `start`, both in the repository, worked out once for each
    pair: the answer does not depend on the working directory."""
    return posixpath.relpath(path, start)


def names(artefact: Artefact) -> list[tuple[str, str]]:
    """A term's names, each with the JSON Pointer of the field that gives it: its `name`,
    then each of its `noun-forms`, a form left out where it repeats an earlier name,
    ignoring case."""
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    name = artefact.fields.get("name")
    if isinstance(name, str) and name.strip():
        found.append(("name", name))
        seen.add(name.casefold())
    for index, form in enumerate(_listed(artefact, NOUN_FORMS)):
        if form is not None and form.casefold() not in seen:
            found.append((f"{NOUN_FORMS}/{index}", form))
            seen.add(form.casefold())
    return found


def _listed(artefact: Artefact, field: str) -> list[str | None]:
    """A list field's entries in their places, `None` for one that is no text."""
    listed = artefact.fields.get(field)
    if not isinstance(listed, list):
        return []
    return [v if isinstance(v, str) and v.strip() else None for v in listed]


def replaced(artefact: Artefact) -> list[str]:
    """The names a term replaces, as its `replaces` lists them."""
    listed = artefact.fields.get("replaces")
    return [n for n in listed if isinstance(n, str)] if isinstance(listed, list) else []


def other_senses(artefact: Artefact) -> list[str]:
    """The phrases a term lists in `other-senses`, as written."""
    listed = artefact.fields.get(OTHER_SENSES)
    return (
        [p for p in listed if isinstance(p, str) and p.strip()] if isinstance(listed, list) else []
    )


def term_of(artefact: Artefact) -> Term | None:
    """The term an entry of a glossary holds, `None` where it has no id or no name."""
    name = artefact.fields.get("name")
    if artefact.id is None or not isinstance(name, str) or not name.strip():
        return None
    return Term(
        artefact.id,
        name,
        artefact.path,
        tuple(f for f in _listed(artefact, NOUN_FORMS) if f is not None),
        tuple(other_senses(artefact)),
    )


def keeps_domain_model(analysis: Analysis, folder: str | None) -> bool:
    """Whether the analysis in `folder` keeps a domain model: its folder of views holds a
    view, in force or withdrawn (DEC-004 point 7)."""
    return any(view.folder == folder for view in analysis.of_kind(VIEW))


@dataclass(frozen=True)
class Vocabulary:
    """The terms whose mentions an analysis links, and the names each is matched by: its
    name and its noun forms, but a name two of them share."""

    terms: tuple[Term, ...]
    matched: Mapping[str, tuple[str, ...]]
    actors: tuple[str, ...] = ()  # the actors' names, which hold no mention of a term

    def term(self, term_id: str) -> Term | None:
        return next((t for t in self.terms if t.id == term_id), None)

    @functools.cached_property
    def searched(self) -> tuple[tuple[str, str, str], ...]:
        """Each name a term is matched by, with the term's id and the name's needle
        (`_needle`), the terms in their order and each term's names in theirs: listed once
        for every text the vocabulary reads."""
        return tuple(
            (term.id, name, _needle(name))
            for term in self.terms
            for name in self.matched.get(term.id, ())
        )


def vocabulary(analysis: Analysis, listing: analyses.Listing, folder: str | None) -> Vocabulary:
    """The terms whose mentions the analysis in `folder` links: its own terms in force, and
    each term its glossary's head lists from an analysis the repository holds, while it is
    in force there. A listed term is mentioned by the name the head lists, and by the
    noun forms and the other senses its own entry declares, and links to that entry by the
    name the entry gives it (DEC-004 point 7). The actors' names are those of its actors
    in force, and those its glossary's head lists."""
    found: list[Term] = []
    actors: list[str] = []
    for actor in analysis.of_kind(ACTOR):
        name = actor.fields.get("name")
        if actor.folder == folder and not actor.withdrawn and isinstance(name, str):
            actors.append(name)
    for artefact in analysis.of_kind(TERM):
        if artefact.folder == folder and not artefact.withdrawn:
            term = term_of(artefact)
            if term is not None:
                found.append(term)
    head = analyses.head(analysis, folder) if listing.several else None
    for taken in head.taken if head is not None else ():
        actors += [actor.name for actor in taken.actors]
        other = listing.of_component(taken.analysis)
        if other is None:
            continue  # an analysis in another repository: no data says where its entry lies
        for term_id, listed_name in taken.terms:
            artefact = analysis.of(term_id, TERM)
            if artefact is None or artefact.folder != other.folder or artefact.withdrawn:
                continue
            term = term_of(artefact)
            if term is not None and all(t.id != term.id for t in found):
                found.append(dataclasses.replace(term, name=listed_name, entry_name=term.name))
    named = tuple(dict.fromkeys(a for a in actors if a.strip()))
    return Vocabulary(tuple(found), matched(found), named)


def matched(terms: Sequence[Term]) -> dict[str, tuple[str, ...]]:
    """The names each of `terms` is matched by, by its id: its name and its noun forms, but
    a name another of them holds too, ignoring case, which names neither."""
    counted = Counter(n.casefold() for t in terms for n in _forms(t))
    return {t.id: tuple(n for n in _forms(t) if counted[n.casefold()] == 1) for t in terms}


def _forms(term: Term) -> tuple[str, ...]:
    """A term's name and its noun forms, each once, ignoring case."""
    found: dict[str, str] = {}
    for name in (term.name, *term.noun_forms):
        found.setdefault(name.casefold(), name)
    return tuple(found.values())


# --- one section -------------------------------------------------------------------------------


@dataclass(frozen=True)
class Difference:
    """How one written link departs from what the command writes: `how`, the line it is
    on, counted from 1 in the file, the mention's or the citation's text, the target
    written and the target wanted, and the term wanted, each `None` where there is none.
    `cited` marks a citation's link, or a citation that takes none (`UNRESOLVED`), whose
    `wanted` then says why (DEC-001 point 13); `received`, a link wanted into a file the
    project receives as a synced copy, which the check only warns of."""

    how: str
    line: int
    text: str
    written: str | None
    wanted: str | None
    term: str | None
    cited: bool = False
    received: bool = False


@dataclass(frozen=True)
class _Found:
    start: int
    end: int
    target: str
    cited: bool = False


@dataclass(frozen=True)
class Cites:
    """What the citations of one analysis resolve against (DEC-001 point 13): what the
    lookup answered, by what it was asked, and the analysis's component, whose decisions a
    bare `DEC-NNN` names. `asked` gathers what the citations ask, so a first pass with no
    answers says what to look up."""

    lookups: Mapping[str, citations.Found]
    component: str | None
    asked: set[str] = dataclasses.field(default_factory=set)


@dataclass(frozen=True)
class _Wanted:
    start: int
    end: int
    target: str
    term: str


@functools.cache
def _pattern(phrase: str) -> re.Pattern[str]:
    """A phrase as a mention matches it: its words as written, any white space between
    them, its first letter in either case and an apostrophe of either kind, whole. Built
    once for each phrase."""
    words = phrase.split()
    parts: list[str] = []
    for i, word in enumerate(words):
        parts.append("".join(_char(ch, first=(i == 0 and k == 0)) for k, ch in enumerate(word)))
    body = _SPACE.join(parts)
    return re.compile(f"(?<!{_JOINER}){body}(?!{_JOINER})")


@functools.cache
def _needle(phrase: str) -> str:
    """The longest run of a phrase's characters that its pattern matches only as written:
    within one word, past the phrase's first letter, and holding no apostrophe. Text that
    lacks it holds no mention of the phrase, so it is not searched."""
    runs: list[str] = []
    for i, word in enumerate(phrase.split()):
        written = word[1:] if i == 0 else word
        runs += re.split(f"[{_APOSTROPHES}]", written)
    return max(runs, key=len, default="")


def _found(phrase: str, text: str) -> Iterator[re.Match[str]]:
    """Each mention of `phrase` in `text`, as its pattern finds them: none, read at the
    cost of one substring test, where `text` lacks its needle."""
    if _needle(phrase) not in text:
        return iter(())
    return _pattern(phrase).finditer(text)


def mentions(text: str, name: str) -> bool:
    """Whether `text` holds `name` as a mention reads it: whole, its first letter in either
    case."""
    return next(_found(name, text), None) is not None


#: Any white space between a phrase's words; and an apostrophe of either kind, the
#: typewriter's and the typographer's, U+2019.
_SPACE = r"\s+"
_APOSTROPHES = "'" + chr(0x2019)


def _char(ch: str, *, first: bool) -> str:
    if ch in _APOSTROPHES:
        return f"[{_APOSTROPHES}]"
    lower, upper = ch.lower(), ch.upper()
    if first and lower != upper and len(lower) == 1 and len(upper) == 1:
        return f"[{re.escape(lower)}{re.escape(upper)}]"
    return re.escape(ch)


def _strip(
    text: str, hide: Collection[int], *, terms: bool = True, cited: bool = False
) -> tuple[str, list[_Found]]:
    """`text` with each link the command writes outside code and comments unwritten, its
    text kept, and each such link, by where its text lies in what is left; the lines
    `hide` gives are kept as written. With `terms`, a link to a glossary entry is the
    command's; with `cited`, a link of a citation (`citations.is_cited_link`)."""
    hidden = _hidden_lines(text, hide)
    code = [
        (m.start(), m.end())
        for pattern in (_INLINE[0], _INLINE[1])
        for m in pattern.finditer(_masked(text, hidden))
    ] + hidden
    out: list[str] = []
    found: list[_Found] = []
    at = 0
    for match in _ANY_LINK.finditer(text):
        if match.start() < at or _overlaps(match.start(), match.end(), code):
            continue
        link, target = match["text"], match["target"]
        term = terms and _TERM_LINK.fullmatch(match.group(0)) is not None
        record = not term and cited and citations.is_cited_link(link, target)
        if not term and not record:
            continue
        out.append(text[at : match.start()])
        start = sum(len(part) for part in out)
        out.append(link)
        found.append(_Found(start, start + len(link), target, record))
        at = match.end()
    out.append(text[at:])
    return "".join(out), found


def _hidden_lines(text: str, hide: Collection[int]) -> list[tuple[int, int]]:
    """The spans of the whole lines no mention is read on: fenced code with its fences,
    headings, a term's link to its section, reference definitions, and the lines of
    `text` `hide` gives, counted from 0."""
    spans: list[tuple[int, int]] = []
    lines = text.split("\n")
    at = 0
    for index, (line, fenced) in enumerate(zip(lines, _fenced(lines), strict=True)):
        end = at + len(line)
        if (
            fenced
            or index in hide
            or any(p.match(line) for p in (_HEADING, _EXPLAINED_LINE, _REFERENCE))
        ):
            spans.append((at, end))
        at = end + 1
    return spans


def _fenced(lines: Sequence[str]) -> list[bool]:
    """Whether each of `lines` lies in fenced code, its fences included."""
    found: list[bool] = []
    fence: tuple[str, int] | None = None
    for line in lines:
        if fence is not None:
            found.append(True)
            stripped = line.strip()
            if stripped and set(stripped) == {fence[0]} and len(stripped) >= fence[1]:
                fence = None
            continue
        opening = _FENCE.match(line)
        if opening is not None and not (
            opening.group(1).startswith("`") and "`" in opening.group(2)
        ):
            fence = (opening.group(1)[0], len(opening.group(1)))
        found.append(fence is not None)
    return found


def _masked(text: str, spans: Sequence[tuple[int, int]]) -> str:
    """`text` with each of `spans` written over in spaces, its line ends kept."""
    chars = list(text)
    for start, end in spans:
        for k in range(start, end):
            if chars[k] != "\n":
                chars[k] = " "
    return "".join(chars)


def _skipped(text: str, hide: Collection[int]) -> tuple[list[tuple[int, int]], list[int]]:
    """The spans of `text` no mention is read in, and where each escape ends."""
    hidden = _hidden_lines(text, hide)
    masked = _masked(text, hidden)
    spans = list(hidden)
    for pattern in _INLINE:
        spans += [(m.start(), m.end()) for m in pattern.finditer(masked)]
    spans += [(m.start(1), m.end(1)) for m in _LABEL.finditer(masked)]
    escapes = [m.end() for m in _ESCAPE.finditer(masked)]
    return spans, escapes


def _overlaps(start: int, end: int, spans: Iterable[tuple[int, int]]) -> bool:
    return any(start < s_end and s_start < end for s_start, s_end in spans)


@dataclass(frozen=True)
class _Mention:
    start: int
    end: int
    term: str


def _chosen(
    text: str,
    vocabulary: Vocabulary,
    hide: Collection[int],
    cited: Sequence[tuple[int, int]] = (),
) -> tuple[list[_Mention], list[int]]:
    """The mentions in `text`, the longest first, and where each escape ends. A citation,
    each span of `cited`, holds no mention (DEC-001 point 13)."""
    skipped, escapes = _skipped(text, hide)
    skipped += list(cited)
    blocked: dict[str, list[tuple[int, int]]] = {}
    for term in vocabulary.terms:
        for phrase in term.other_senses:
            blocked.setdefault(term.id, []).extend(
                (m.start(), m.end()) for m in _found(phrase, text)
            )
    named = [(m.start(), m.end()) for a in vocabulary.actors for m in _found(a, text)]
    candidates: list[_Mention] = []
    for term_id, name, needle in vocabulary.searched:
        if needle not in text:
            continue  # no mention of the name, as `_found` reads it
        for m in _pattern(name).finditer(text):
            if _overlaps(m.start(), m.end(), skipped):
                continue
            if any(s <= m.start() and m.end() <= e for s, e in blocked.get(term_id, ())):
                continue
            if any(
                s <= m.start() and m.end() <= e and m.end() - m.start() < e - s for s, e in named
            ):
                continue
            candidates.append(_Mention(m.start(), m.end(), term_id))
    candidates.sort(key=lambda c: (c.start, -(c.end - c.start), c.term))
    chosen: list[_Mention] = []
    reached = 0
    for candidate in candidates:
        if candidate.start >= reached:
            chosen.append(candidate)
            reached = candidate.end
    return chosen, escapes


def _wanted(
    text: str,
    own: str | None,
    vocabulary: Vocabulary,
    path: str,
    hide: Collection[int],
    plain: Sequence[tuple[int, int]] = (),
    cited: Sequence[tuple[int, int]] = (),
) -> list[_Wanted]:
    """The links the command writes in one section's `text`: the first mention of each term
    that is not the section's own, no escape marks, and lies outside each span of `plain`,
    text that stays plain, and outside the spans of `cited`, the citations."""
    mentions, escapes = _chosen(text, vocabulary, hide, cited)
    linked: set[str] = set()
    wanted: list[_Wanted] = []
    for mention in mentions:
        if any(
            text[end : mention.start].strip(" \t") == "" for end in escapes if end <= mention.start
        ):
            continue
        if _overlaps(mention.start, mention.end, plain):
            continue
        if mention.term == own or mention.term in linked:
            continue
        term = vocabulary.term(mention.term)
        if term is None:
            continue
        linked.add(mention.term)
        wanted.append(_Wanted(mention.start, mention.end, term.target(path), term.id))
    return wanted


def _render(text: str, wanted: Sequence[tuple[int, int, str]]) -> str:
    out = text
    for start, end, target in sorted(wanted, key=lambda w: w[0], reverse=True):
        out = f"{out[:start]}[{out[start:end]}]({target}){out[end:]}"
    return out


def section(
    text: str,
    own: str | None,
    vocabulary: Vocabulary | None,
    path: str,
    first_line: int,
    hide: Collection[int] = (),
    cites: Cites | None = None,
    quiet: Callable[[str], Sequence[tuple[int, int]]] | None = None,
    cuts: Collection[int] = (),
) -> tuple[str, list[Difference]]:
    """One section's `text`, its links written as the command writes them, and how the
    links it holds depart from those; `first_line` is the line `text` starts on in the
    file at `path`, `own` the id of the section's own term, and `hide` the lines of
    `text`, counted from 0, that link a view's section to a term, which are neither read
    nor rewritten here (`with_definitions`).

    With a `vocabulary`, the first mention of each term takes its link (DEC-004 point 7).
    `quiet` gives the spans of the text, its links unwritten, that say a datum again:
    they are read for no mention, and a link written in them is extra (`_quiet`). With
    `cites`, the first citation of each record, point or rule takes its link, and a
    citation that resolves to nothing is noted (DEC-001 point 13). Each line of `cuts`,
    counted from 0, opens a new section of the citations. A citation holds no mention.
    Without one of them, the links of its kind are the writer's, left as written."""
    plain, found = _strip(text, hide, terms=vocabulary is not None, cited=cites is not None)
    placed = citations.Placed((), (), ())
    if cites is not None:
        skipped, _escapes = _skipped(plain, hide)
        hidden = _hidden_lines(plain, hide)
        cites.asked.update(citations.keys(citations.found(plain, skipped, cites.component)))
        starts = [0, *(m.end() for m in re.finditer("\n", plain))]
        opens = [starts[k] for k in sorted(cuts) if 0 < k < len(starts)]
        placed = citations.placed(
            plain, skipped, hidden, cites.component, cites.lookups, path, opens
        )
    terms: list[_Wanted] = []
    if vocabulary is not None:
        still = quiet(plain) if quiet is not None else ()
        terms = _wanted(plain, own, vocabulary, path, hide, still, placed.spans)

    def line(offset: int) -> int:
        return first_line + plain.count("\n", 0, offset)

    # Each link wanted, by its span: its target, its term, whether a citation's, and
    # whether into a file the project receives.
    wanted: dict[tuple[int, int], tuple[str, str | None, bool, bool]] = {
        (w.start, w.end): (w.target, w.term, False, False) for w in terms
    }
    wanted.update({(w.start, w.end): (w.target, None, True, w.received) for w in placed.links})
    held = {(f.start, f.end): f for f in found}
    differences: list[Difference] = []
    for key, link in sorted(held.items()):
        want = wanted.get(key)
        text_of = plain[link.start : link.end]
        if want is None or want[2] != link.cited:
            differences.append(
                Difference(EXTRA, line(link.start), text_of, link.target, None, None, link.cited)
            )
        elif want[0] != link.target:
            differences.append(
                Difference(
                    STALE,
                    line(link.start),
                    text_of,
                    link.target,
                    want[0],
                    want[1],
                    link.cited,
                    want[3],
                )
            )
    for key, (target, term, cited, received) in sorted(wanted.items()):
        link = held.get(key)
        if link is None or link.cited != cited:
            text_of = plain[key[0] : key[1]]
            differences.append(
                Difference(MISSING, line(key[0]), text_of, None, target, term, cited, received)
            )
    for note in placed.notes:
        differences.append(
            Difference(
                UNRESOLVED,
                line(note.start),
                plain[note.start : note.end],
                None,
                note.why,
                None,
                True,
            )
        )
    differences.sort(key=lambda d: d.line)
    return _render(plain, [(s, e, w[0]) for (s, e), w in wanted.items()]), differences


# --- a section's link to its term --------------------------------------------------------------


def defined(term: Term, path: str) -> str:
    """The line that links a view's section, in the file at `path`, to its term's entry."""
    return f"{DEFINED} [{term.id}]({term.target(path)})."


def view_sections(lines: Sequence[str], start: int) -> list[tuple[int, int]]:
    """Where each part of a view's body lies among `lines`, the body starting at index
    `start`: its opening, from the body's start to its first section, then each section,
    from its heading to the next one, each as the index of its first line and the index
    past its last. A heading inside fenced code opens no section."""
    body = lines[start:]
    starts = [
        start + index
        for index, (line, fenced) in enumerate(zip(body, _fenced(body), strict=True))
        if not fenced and re.match(r"^##(?:[ \t]|$)", line)
    ]
    bounds = [start, *starts, len(lines)]
    return [(bounds[k], bounds[k + 1]) for k in range(len(bounds) - 1)]


def defined_at(lines: Sequence[str], first: int, past: int, own: str | None) -> int | None:
    """The index of a section's link to its term among `lines`, the section's heading at
    index `first`: its first line below the heading that is not blank, where that line
    has the form of the link and leads from `own`, the section's own term; `None` where
    it has none. A heading opens no fenced code, so the line lies outside any."""
    if own is None:
        return None
    for index in range(first + 1, past):
        if lines[index].strip():
            match = DEFINED_LINE.match(lines[index])
            return index if match is not None and match["id"] == own else None
    return None


def definition_lines(lines: Sequence[str], first: int, past: int) -> list[int]:
    """The indices of the lines of a part of a view, from index `first` to `past`, in the
    form of a section's link to its term, outside fenced code: the section's own link
    (`defined_at`), and each line the command takes out. A part opens outside any fence."""
    part = lines[first:past]
    return [
        first + index
        for index, (line, fenced) in enumerate(zip(part, _fenced(part), strict=True))
        if not fenced and DEFINED_LINE.match(line)
    ]


def with_definitions(
    lines: list[str],
    sections: Sequence[tuple[int, int]],
    owners: Sequence[str | None],
    wanted: Sequence[str | None],
) -> tuple[list[str], list[tuple[str, int, str | None, str | None]]]:
    """A view's `lines` with each section's link to its term as `wanted` gives it, the
    k-th section's the k-th, its own term `owners`' k-th: the link the section holds
    (`defined_at`) rewritten to it, or taken out where none is wanted, and one written
    right below the heading where the section holds none. Any other line of a section in
    the form of the link, outside fenced code (`definition_lines`), is a link written by
    hand where the command writes none: it is extra, and taken out. No other line is
    touched, but a blank line beside one taken out. Returns the lines, and how the
    section's links departed: `(how, line number, written, wanted)`, each line counted in
    the lines as given."""
    out = list(lines)
    differences: list[tuple[str, int, str | None, str | None]] = []
    for k, (first, past) in reversed(list(enumerate(sections))):
        want = wanted[k] if k < len(wanted) else None
        held = defined_at(lines, first, past, owners[k] if k < len(owners) else None)
        for index in reversed(definition_lines(lines, first, past)):
            if index != held:
                differences.append((EXTRA, index + 1, lines[index].strip(), None))
                _take_out(out, index)
        if held is not None:
            line = lines[held].strip()
            if want is None:
                differences.append((EXTRA, held + 1, line, None))
                _take_out(out, held)
            elif line != want:
                differences.append((STALE, held + 1, line, want))
                out[held] = want
        elif want is not None:
            differences.append((MISSING, first + 1, None, want))
            out[first + 1 : first + 1] = ["", want]
    differences.sort(key=lambda d: d[1])
    return out, differences


def _take_out(lines: list[str], index: int) -> None:
    """Take the line at `index` out of `lines`, and the blank line after it where a blank
    line stands on either side, so no two blank lines are left where one stood."""
    del lines[index]
    if 0 < index < len(lines) and not lines[index - 1].strip() and not lines[index].strip():
        del lines[index]


# --- a file ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Departure:
    """A link in a file that departs from what the command writes, at the location of the
    artefact that holds it, or a citation that takes none since it resolves to nothing
    (`UNRESOLVED`, `cited`), its `wanted` saying why. `received` marks a link wanted into
    a file the project receives as a synced copy (DEC-001 point 13)."""

    location: str
    how: str
    line: int
    text: str
    written: str | None
    wanted: str | None
    term: str | None
    defined: bool = False
    cited: bool = False
    received: bool = False
    closing: bool = False  # the view's closing section, missing or stale


@dataclass(frozen=True)
class Linked:
    """A file the links reach: its path, its text as read, LF line ends, its text as the
    command writes it, and how its links depart from that."""

    path: str
    text: str
    linked: str
    departures: tuple[Departure, ...]


def glossary(
    path: str,
    text: str,
    entries: Sequence[Artefact],
    vocabulary: Vocabulary | None,
    cites: Cites | None = None,
) -> Linked:
    """The glossary at `path`, LF `text`, with the links of each of `entries`, the terms
    in force it holds, written: each entry's section as the backbone spans it, below its
    heading. Its head takes none."""
    lines = text.split("\n")
    departures: list[Departure] = []
    for entry in sorted(entries, key=lambda e: e.span or (0, 0), reverse=True):
        if entry.span is None:
            continue
        first, last = entry.span
        body = lines[first : min(last, len(lines))]
        if not body:
            continue
        rewritten, found = section(
            "\n".join(body), entry.id, vocabulary, path, first + 1, cites=cites
        )
        lines[first : first + len(body)] = rewritten.split("\n")
        departures += [_departure(entry.location, d) for d in found]
    departures.sort(key=lambda d: (d.line, d.location))
    return Linked(path, text, "\n".join(lines), tuple(departures))


def view(
    artefact: Artefact,
    text: str,
    vocabulary: Vocabulary,
    cites: Cites | None = None,
    closing: Sequence[str] | None = None,
) -> Linked:
    """A view in force, LF `text`, with each section's link to its term and the links of
    its mentions and its citations written: its opening and each section below its
    heading. A line in the form of a section's link to its term in the opening is taken
    out, as one below a section's own link is. Its closing section is written last, as
    `closing` gives its lines, in place of any it holds, and read for no mention and no
    citation; where `closing` is `None`, what is built on its concepts is not known here,
    and the section it holds is kept as written."""
    path = artefact.path
    whole = text.split("\n")
    start = body_start(whole)
    spans = closing_spans(whole, start)
    # The concepts' sections are read with each closing section blank, so each departure
    # gives its line in the text as written, and rewritten with each one taken out.
    written = _blanked(whole, spans)
    bare = [line for index, line in enumerate(whole) if not _within(index, spans)]
    explains = artefact.fields.get(EXPLAINS)
    listed = [t for t in explains if isinstance(t, str)] if isinstance(explains, list) else []
    wanted_lines: list[str | None] = []
    for k in range(len(view_sections(bare, start)) - 1):
        term_id = listed[k] if k < len(listed) else None
        term = vocabulary.term(term_id) if term_id is not None else None
        wanted_lines.append(defined(term, path) if term is not None else None)
    owners: list[str | None] = [None, *(listed[: len(wanted_lines)])]
    _lines, held = with_definitions(
        written, view_sections(written, start), owners, [None, *wanted_lines]
    )
    departures = [
        Departure(artefact.location, how, number, line or "", line, want, None, True)
        for how, number, line, want in held
    ]
    # The links are compared on the text as written, so each departure gives its line
    # there, and written on the text with each section's link to its term in place.
    departures += [
        _departure(artefact.location, d)
        for _rewritten, found in _parts(
            written, view_sections(written, start), owners, vocabulary, path, cites
        )
        for d in found
    ]
    lines = with_definitions(bare, view_sections(bare, start), owners, [None, *wanted_lines])[0]
    pieces = _parts(lines, view_sections(lines, start), owners, vocabulary, path, cites)
    linked: list[str] = list(lines[:start])
    for rewritten, _found in pieces:
        linked += rewritten.split("\n")
    held_closing = [whole[first:past] for first, past in spans]
    want = list(closing) if closing is not None else _trimmed(held_closing[0] if spans else [])
    if closing is not None:
        departures += _closing_departures(artefact.location, whole, spans, want)
    departures.sort(key=lambda d: (d.line, d.how))
    return Linked(path, text, "\n".join(_closed(linked, want, whole, spans)), tuple(departures))


# --- a view's closing section ------------------------------------------------------------------


def closing_spans(lines: Sequence[str], start: int) -> list[tuple[int, int]]:
    """Where each closing section of a view lies among `lines`, the body starting at index
    `start`: from its heading, outside fenced code, to the next heading of its level or
    the end, each as the index of its first line and the index past its last."""
    body = lines[start:]
    headings = [
        start + index
        for index, (line, fenced) in enumerate(zip(body, _fenced(body), strict=True))
        if not fenced and re.match(r"^##(?:[ \t]|$)", line)
    ]
    found: list[tuple[int, int]] = []
    for k, first in enumerate(headings):
        if _CLOSING_LINE.match(lines[first]):
            found.append((first, headings[k + 1] if k + 1 < len(headings) else len(lines)))
    return found


def closing_lines(body: Sequence[str]) -> set[int]:
    """The indices of the lines of a view's `body`, below its front matter, that lie in a
    closing section, which is no part of the view's structure (DEC-004 point 2)."""
    return {index for first, past in closing_spans(body, 0) for index in range(first, past)}


def _within(index: int, spans: Sequence[tuple[int, int]]) -> bool:
    return any(first <= index < past for first, past in spans)


def _blanked(lines: Sequence[str], spans: Sequence[tuple[int, int]]) -> list[str]:
    """`lines` with each line of `spans` blank, their number kept."""
    return ["" if _within(index, spans) else line for index, line in enumerate(lines)]


def _trimmed(lines: Sequence[str]) -> list[str]:
    """`lines` without the blank lines that end them."""
    out = list(lines)
    while out and not out[-1].strip():
        out.pop()
    return out


def ending_with(text: str, closing: Sequence[str]) -> str:
    """A new view's LF `text` ending with its closing section, `closing`: after its last
    line that is not blank, a blank line between, and a line end after it."""
    return "\n".join([*_trimmed(text.split("\n")), "", *closing, ""])


def _closed(
    linked: Sequence[str],
    closing: Sequence[str],
    whole: Sequence[str],
    spans: Sequence[tuple[int, int]],
) -> list[str]:
    """A view's `linked` lines, its closing sections taken out, with `closing` written
    last: in the place of the one it held where it held one alone, at its end, the lines
    before it kept as written; else after its last line that is not blank, a blank line
    between. No closing section is written where `closing` holds none."""
    if not closing:
        return list(linked)
    if len(spans) == 1 and spans[0][1] == len(whole):
        before = list(linked)
        if before and before[-1].strip():
            before.append("")
        return [*before, *closing, ""]
    return [*_trimmed(linked), "", *closing, ""]


def _closing_departures(
    location: str,
    whole: Sequence[str],
    spans: Sequence[tuple[int, int]],
    wanted: Sequence[str],
) -> list[Departure]:
    """How a view's closing section departs from `wanted`: missing, or stale where it is
    not the view's one closing section, at its end after a blank line, or holds other
    lines."""
    if not spans:
        at = len(_trimmed(whole)) + 1
        return [Departure(location, MISSING, at, CLOSING, None, None, None, closing=True)]
    first, past = spans[0]
    alone = len(spans) == 1 and past == len(whole)
    apart = first == 0 or not whole[first - 1].strip()
    if alone and apart and list(whole[first:past]) == [*wanted, ""]:
        return []
    return [Departure(location, STALE, first + 1, CLOSING, None, None, None, closing=True)]


def terms_linked(text: str, path: str, vocabulary: Vocabulary) -> frozenset[str]:
    """The ids of the terms the body of `text`, the file at `path`, links to, below its
    front matter, by a link to the term's entry outside code and comments, as the
    command writes one: its target from the file's folder (`Term.target`)."""
    targets = {term.target(path): term.id for term in vocabulary.terms}
    lines = text.split("\n")
    _plain, found = _strip("\n".join(lines[body_start(lines) :]), ())
    return frozenset(targets[f.target] for f in found if f.target in targets)


def listed_in_closing(analysis: Analysis, folder: str | None) -> list[Artefact]:
    """The artefacts a view's closing section may list: each use case, journey and
    requirement in force of the analysis in `folder`, the use cases first, then the
    journeys, then the requirements, each in the order of their numbers."""
    return sorted(
        (
            a
            for a in analysis.artefacts
            if a.kind in LISTED and a.folder == folder and not a.withdrawn and a.id
        ),
        key=_in_order,
    )


def _in_order(artefact: Artefact) -> tuple[int, int, str, str]:
    spelt = number_in(str(artefact.id))
    rank = min(LISTED.index(artefact.kind), LISTED.index(REQUIREMENTS[0]))
    return rank, int(spelt.split("-", 1)[1]) if spelt else 0, str(artefact.id), artefact.path


def closing(
    view_path: str,
    explains: Sequence[str],
    headings: Mapping[str, str],
    listed: Sequence[Artefact],
    used: Mapping[str, Collection[str]],
    shown_as: Mapping[str, str],
) -> list[str]:
    """The lines of the closing section of the view at `view_path`: its opening sentence,
    then, for each term of `explains`, in its order, under its section's heading as
    `headings` gives it by its id, each of `listed` whose body links it, as `used` gives
    the terms each links by its id, linked by a path from the view's folder. A requirement
    shows its kind beside its id, as `shown_as` names it. A concept nothing links reads
    `None.`"""
    out = [f"## {CLOSING}", "", CLOSING_OPENING]
    here = posixpath.dirname(view_path) or "."
    for term_id in dict.fromkeys(explains):
        users = [a for a in listed if term_id in used.get(str(a.id), ())]
        out += ["", f"**{headings.get(term_id, term_id)}:**" + ("" if users else " None.")]
        if users:
            out.append("")
            out += [f"- [{_label(a, shown_as)}]({_relative(a.path, here)})" for a in users]
    return out


def _label(artefact: Artefact, shown_as: Mapping[str, str]) -> str:
    """`<id> — <title>`, and `<id> · <kind> · <title>` for a requirement, as the overview
    and its heading show it, its brackets escaped."""
    title = artefact.fields.get("title")
    if artefact.kind in REQUIREMENTS:
        shown = f"{artefact.id} · {shown_as.get(artefact.kind, artefact.kind)}"
        label = shown + (f" · {title}" if isinstance(title, str) else "")
    else:
        label = f"{artefact.id} — {title}" if isinstance(title, str) else str(artefact.id)
    return label.replace("[", "\\[").replace("]", "\\]")


#: A line that opens a part of an artefact: a bold label that opens the line, or a list
#: item at the top level, such as `**Goal:**`, `- **Human role:**` or `- **1a.**`.
_PART = re.compile(r"^(?:(?:[-+*]|[0-9]{1,9}[.)])[ \t]+)?\*\*[^*\n]+?\*\*")


def part_sections(lines: Sequence[str], start: int) -> list[tuple[int, int]]:
    """Where each part of a body lies among `lines`, the body starting at index `start`:
    from the body's start to the first heading or part, then from each heading, and each
    line that opens with a bold label at the top level (`_PART`), to the next, each as the
    index of its first line and the index past its last. A line inside fenced code opens
    none."""
    body = lines[start:]
    starts = [
        start + index
        for index, (line, fenced) in enumerate(zip(body, _fenced(body), strict=True))
        if not fenced and (_HEADING.match(line) or _PART.match(line))
    ]
    bounds = [start, *starts, len(lines)]
    return [(bounds[k], bounds[k + 1]) for k in range(len(bounds) - 1)]


def _parts(
    lines: Sequence[str],
    parts: Sequence[tuple[int, int]],
    owners: Sequence[str | None],
    vocabulary: Vocabulary | None,
    path: str,
    cites: Cites | None,
) -> list[tuple[str, list[Difference]]]:
    """Each of `parts` of a body among `lines`, with its links written, and how the links
    it holds depart from those. A part's own term is `owners`' entry in its place: none
    for a view's opening. Its lines in the form of a section's link to its term are
    `with_definitions`', and read for no mention and no citation."""
    found: list[tuple[str, list[Difference]]] = []
    for k, (first, past) in enumerate(parts):
        if first == past:
            continue  # a part with no line holds nothing to link
        own = owners[k] if k < len(owners) else None
        hide = [index - first for index in definition_lines(lines, first, past)]
        text = "\n".join(lines[first:past])
        found.append(section(text, own, vocabulary, path, first + 1, hide, cites))
    return found


# --- an actor, a use case, a journey and a requirement -----------------------------------------


def parted(root: Path) -> dict[str, structure.Kind]:
    """The kinds of `PARTED`, each as its parts are found whatever any rule's status: as
    shipped, relabelled by the project's own structures at `root`, each label any of their
    groups adds opening a part too, and a part found by its shipped label as well. Where
    the project's file cannot be read, the kinds are read as shipped, and the check's
    findings on that file say why. Raises `structure.Unreadable` where the declaration
    cannot be read."""
    shipped = structure.read_kinds()
    own = project_structure.read(root, shipped)
    if own.problems:
        own = project_structure.Own()
    found: dict[str, structure.Kind] = {}
    for name in PARTED:
        groups = own.of(name)
        kind = project_structure.relabelled(shipped[name], own)
        kind = project_structure.tightened(kind, groups, (), groups)
        found[name] = dataclasses.replace(kind, as_written=True)
    return found


def _texts(kind: structure.Kind, element_id: str) -> frozenset[str]:
    """The texts the label of the part whose id is `element_id` is found by, as they are
    compared: its label, and each label a project relabelled it from."""
    for element in kind.sections:
        if element.id == element_id and element.type == structure.LABEL and element.text:
            return frozenset(structure.comparable(t) for t in (element.text, *element.aliases))
    return frozenset()


#: A step's line in a journey's steps: a top-level numbered item. Its line ends at a blank
#: line, a nested item or a hand-over.
_STEP = re.compile(r"^[0-9]{1,9}[.)](?:[ \t]|$)")
_NESTED = re.compile(r"^[ \t]+(?:[-+*]|[0-9]{1,9}[.)])(?:[ \t]|$)")
_HAND_OVER = re.compile(r"^[ \t]*(?:[-+*][ \t]+)?\*\*Needs from ")


def _step_lines(text: str) -> list[tuple[int, int]]:
    """The spans of each step's line in a journey's steps, which gives a use case's
    title."""
    spans: list[tuple[int, int]] = []
    at = 0
    within = False
    for line in text.split("\n"):
        if _STEP.match(line):
            within = True
        elif not line.strip() or _NESTED.match(line) or _HAND_OVER.match(line):
            within = False
        if within:
            spans.append((at, at + len(line)))
        at += len(line) + 1
    return spans


def _first_sentence(text: str) -> list[tuple[int, int]]:
    """The span of an opening's first sentence, below the heading that opens its part."""
    at = 0
    for line in text.split("\n"):
        if line.strip() and not _HEADING.match(line):
            break
        at += len(line) + 1
    if at >= len(text):
        return []
    return [(at, at + forms.first_sentence_end(text[at:]))]


def _whole(text: str) -> list[tuple[int, int]]:
    return [(0, len(text))]


def _quiet(
    artefact: Artefact, kind: structure.Kind, marks: Sequence[tuple[int, str, int, str] | None]
) -> list[Callable[[str], Sequence[tuple[int, int]]] | None]:
    """For each part of a body, opened by the mark in its place (`None` for the text above
    the first), what in it says a datum again and stays plain: a goal whole, each step's
    line of a journey's steps, and the first sentence of an actor's opening where the
    actor gives a summary. The opening is the part its first heading opens, or the text
    above the first mark, before any label."""
    goal, steps = _texts(kind, GOAL), _texts(kind, STEPS)
    summary = artefact.fields.get(SUMMARY)
    opening: int | None = None
    if kind.name == ACTOR and isinstance(summary, str) and summary.strip():
        for k, mark in enumerate(marks):
            if mark is not None and mark[1] == structure.LABEL:
                break
            if mark is None or (mark[1] == structure.HEADING and mark[2] == 1):
                opening = k
    found: list[Callable[[str], Sequence[tuple[int, int]]] | None] = []
    for k, mark in enumerate(marks):
        label = structure.comparable(mark[3]) if mark and mark[1] == structure.LABEL else None
        if label is not None and label in goal:
            found.append(_whole)
        elif label is not None and label in steps and kind.name == JOURNEY:
            found.append(_step_lines)
        elif k == opening:
            found.append(_first_sentence)
        else:
            found.append(None)
    return found


def document(
    artefact: Artefact,
    text: str,
    vocabulary: Vocabulary | None,
    kind: structure.Kind | None,
    cites: Cites | None = None,
) -> Linked:
    """An artefact in force of a kind with a file of its own, but a view, LF `text`, with
    its links written.

    - **The mentions' links**, given a `vocabulary` and the `kind` of an actor, a use
      case, a journey or a requirement: in each part of its body, read as `kind` gives
      its parts, from each heading and each label it declares to the next, the text above
      the first a part too (`_quiet` says what stays plain; DEC-004 point 7).
    - **The citations' links**, given `cites`: in each of its sections (`part_sections`,
      DEC-001 point 13), which open at each heading and at each bold label that opens a
      line or a list item at the top level, each part of the mentions' holding one or
      more of them.
    """
    lines = text.split("\n")
    start = body_start(lines)
    sections = part_sections(lines, start)
    words = vocabulary if kind is not None else None
    if words is not None and kind is not None:
        numbered = [(index + 1, lines[index]) for index in range(start, len(lines))]
        opened = structure.marks(numbered, kind)
        bounds = [start, *(start + index for index, *_rest in opened), len(lines)]
        parts = [(bounds[k], bounds[k + 1]) for k in range(len(bounds) - 1)]
        marks: list[tuple[int, str, int, str] | None] = [None, *opened]
        quiet = _quiet(artefact, kind, marks)
    else:
        parts = sections
        quiet = [None] * len(parts)
    opens = [first for first, _past in sections]
    linked: list[str] = list(lines[:start])
    departures: list[Departure] = []
    for k, (first, past) in enumerate(parts):
        if first == past:
            continue
        rewritten, found = section(
            "\n".join(lines[first:past]),
            None,
            words,
            artefact.path,
            first + 1,
            cites=cites,
            quiet=quiet[k],
            cuts=[index - first for index in opens if first < index < past],
        )
        linked += rewritten.split("\n")
        departures += [_departure(artefact.location, d) for d in found]
    departures.sort(key=lambda d: (d.line, d.how))
    return Linked(artefact.path, text, "\n".join(linked), tuple(departures))


def body_start(lines: Sequence[str]) -> int:
    """The index of a document's first line below its front matter."""
    if lines and lines[0].rstrip() == "---":
        for index in range(1, len(lines)):
            if re.match(r"^---[ \t]*$", lines[index]):
                return index + 1
    return 0


def _departure(location: str, difference: Difference) -> Departure:
    return Departure(
        location,
        difference.how,
        difference.line,
        difference.text,
        difference.written,
        difference.wanted,
        difference.term,
        cited=difference.cited,
        received=difference.received,
    )


#: The kinds whose artefacts in force take the links of their citations, each a file of
#: its own: every kind but the term, whose glossary is a collection, and the view.
_DOCUMENT_KINDS = tuple(kind for kind in KINDS if kind not in (TERM, VIEW))


def component(listing: analyses.Listing, folder: str | None) -> str | None:
    """The component whose analysis lies in `folder`; `None` for the one analysis at the
    location's top, which names none, so a bare `DEC-NNN` there names no capability."""
    listed = listing.of_folder(folder) if listing.several else None
    return listed.component if listed is not None else None


def plan(
    analysis: Analysis,
    listing: analyses.Listing,
    read: Mapping[str, str | None],
    kinds: Mapping[str, structure.Kind] | None,
    lookups: Mapping[str, citations.Found] | None = None,
    asked: set[str] | None = None,
) -> list[Linked]:
    """Each file the links reach, as the command writes it. In every analysis, each
    artefact in force takes the links of its citations, from `lookups`, what the lookup
    answered (DEC-001 point 13). In one that keeps a domain model, the glossary and each
    view in force take the links between terms too, and so does each actor, use case,
    journey and requirement in force, read as `kinds` gives their parts (`parted`),
    save where `kinds` is `None` (DEC-004 point 7). Each view's closing section is
    written from the documents as the command writes them, and kept as written where
    `kinds` is `None`. `read` gives each file's text by its path, LF line ends, `None`
    where it cannot be read, which is left out. `asked`, where given, gathers what the
    citations ask the lookup, so a pass with no `lookups` says what to look up."""
    folders = [a.folder for a in listing.analyses] if listing.several else [None]
    found: list[Linked] = []
    for folder in folders:
        domain = keeps_domain_model(analysis, folder)
        words = vocabulary(analysis, listing, folder) if domain else None
        cites = Cites(lookups or {}, component(listing, folder))
        entries = [
            t for t in analysis.of_kind(TERM) if t.folder == folder and not t.withdrawn and t.id
        ]
        by_glossary: dict[str, list[Artefact]] = {}
        for entry in entries:
            by_glossary.setdefault(entry.path, []).append(entry)
        for path, held in sorted(by_glossary.items()):
            text = read.get(path)
            if text is not None:
                found.append(glossary(path, text, held, words, cites))
        documents = _documents(analysis, folder, read, words, kinds, cites)
        if words is not None:
            found += _views(analysis, folder, read, words, kinds, cites, documents)
        found += [linked for _artefact, linked in documents]
        if asked is not None:
            asked |= cites.asked
    return found


def _views(
    analysis: Analysis,
    folder: str | None,
    read: Mapping[str, str | None],
    words: Vocabulary,
    kinds: Mapping[str, structure.Kind] | None,
    cites: Cites,
    documents: Sequence[tuple[Artefact, Linked]],
) -> list[Linked]:
    """Each view in force of the analysis in `folder` whose text `read` gives, with its
    links as the command writes them, and its closing section written from `documents`,
    as the command writes their links; kept as written where `kinds` is `None`."""
    used = {
        str(artefact.id): terms_linked(linked.linked, artefact.path, words)
        for artefact, linked in documents
    }
    listed = listed_in_closing(analysis, folder)
    shown_as = {name: kind.shown_as or name for name, kind in (kinds or {}).items()}
    found: list[Linked] = []
    for artefact in sorted(analysis.of_kind(VIEW), key=lambda v: v.path):
        if artefact.folder != folder or artefact.withdrawn:
            continue
        text = read.get(artefact.path)
        if text is None:
            continue
        explained = _explained(artefact)
        headings = {term_id: views.heading(analysis, term_id) for term_id in explained}
        closed = (
            closing(artefact.path, explained, headings, listed, used, shown_as)
            if kinds is not None
            else None
        )
        found.append(view(artefact, text, words, cites, closed))
    return found


def _document_artefacts(analysis: Analysis, folder: str | None) -> list[Artefact]:
    """The artefacts in force of the analysis in `folder` of the kinds with a file of their
    own, but the view (`_DOCUMENT_KINDS`), in the order of their paths."""
    return sorted(
        (
            a
            for kind in _DOCUMENT_KINDS
            for a in analysis.of_kind(kind)
            if a.folder == folder and not a.withdrawn and not a.entry
        ),
        key=lambda a: a.path,
    )


def _documents(
    analysis: Analysis,
    folder: str | None,
    read: Mapping[str, str | None],
    words: Vocabulary | None,
    kinds: Mapping[str, structure.Kind] | None,
    cites: Cites | None = None,
) -> list[tuple[Artefact, Linked]]:
    """Each of `_document_artefacts` of the analysis in `folder` whose text `read` gives,
    with its links as the command writes them (`document`): the links of its citations,
    given `cites`, and, given `words`, the mentions' links of each actor, use case,
    journey and requirement, read as `kinds` gives its parts, none where `kinds` is
    `None`."""
    found: list[tuple[Artefact, Linked]] = []
    for artefact in _document_artefacts(analysis, folder):
        text = read.get(artefact.path)
        if text is not None:
            kind = (kinds or {}).get(artefact.kind)
            found.append((artefact, document(artefact, text, words, kind, cites)))
    return found


def asked(
    analysis: Analysis,
    listing: analyses.Listing,
    read: Mapping[str, str | None],
    kinds: Mapping[str, structure.Kind] | None,
) -> set[str]:
    """What the citations of every analysis ask the lookup: each record, point and rule
    they may name, read as `plan` reads them with the same `kinds`. Read with other kinds,
    a term link inside a citation, as on `point` in `PRJ-001 point 2`, cuts it short, and
    its point goes unasked."""
    gathered: set[str] = set()
    plan(analysis, listing, read, kinds, None, gathered)
    return gathered


def _explained(view_artefact: Artefact) -> list[str]:
    """The term ids a view's `explains` lists, as written."""
    explains = view_artefact.fields.get(EXPLAINS)
    return [t for t in explains if isinstance(t, str)] if isinstance(explains, list) else []


def uses(
    analysis: Analysis,
    listing: analyses.Listing,
    folder: str | None,
    read: Mapping[str, str | None],
    kinds: Mapping[str, structure.Kind],
) -> dict[str, frozenset[str]]:
    """The terms each use case, journey and requirement in force of the analysis in
    `folder` links, by its id, as the command writes its links (`terms_linked`), whether
    or not the analysis keeps a domain model yet: what a new view's closing section is
    written from. `read` gives each file's text by its path, LF line ends. The citations
    are not looked up here: a citation the command links is a link, read for no mention
    either way."""
    words = vocabulary(analysis, listing, folder)
    return {
        str(artefact.id): terms_linked(linked.linked, artefact.path, words)
        for artefact, linked in _documents(analysis, folder, read, words, kinds)
    }


def files(analysis: Analysis, listing: analyses.Listing) -> list[str]:
    """The paths `plan` reads: in every analysis, each glossary that holds a term in force
    and each artefact in force of another kind, and each view in force where it keeps a
    domain model."""
    folders = [a.folder for a in listing.analyses] if listing.several else [None]
    paths: set[str] = set()
    for folder in folders:
        paths |= {t.path for t in analysis.of_kind(TERM) if t.folder == folder and not t.withdrawn}
        if keeps_domain_model(analysis, folder):
            paths |= {
                v.path for v in analysis.of_kind(VIEW) if v.folder == folder and not v.withdrawn
            }
        paths |= {a.path for a in _document_artefacts(analysis, folder)}
    return sorted(paths)
