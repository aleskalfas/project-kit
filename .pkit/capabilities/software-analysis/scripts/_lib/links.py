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
  (`defined_at`). Any other line that opens with `Defined in` is the writer's, and is
  left as written.
- **A mention's link to its term.** In a view's opening and each of its sections,
  and in each glossary entry's section below its heading, the first mention of a
  term is linked to its entry, `[<mention>](<glossary>#<anchor>)`.

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

The rewrite reads a body only to place its links, and takes its data from front
matter alone: each term's id, name, noun forms and other senses, and each view's
`explains` (DEC-001 point 1). It never changes the number of a body's lines, but
where it adds a section's link to its term.
"""

from __future__ import annotations

import dataclasses
import posixpath
import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from _lib import analyses, forms
from _lib.model import EXPLAINS, TERM, VIEW, Analysis, Artefact

#: A term's other noun forms, and the phrases in which its name has another sense (DEC-001
#: point 1).
NOUN_FORMS, OTHER_SENSES = "noun-forms", "other-senses"

#: The comment that marks the mention right after it as no mention of a term.
ESCAPE = "<!-- pkit:not-the-term -->"

#: What a section's link to its term opens with.
DEFINED = "Defined in"

#: How a written link departs from what the command writes.
MISSING, EXTRA, STALE = "missing", "extra", "stale"

#: The target of a link to a glossary entry: a path with no scheme to a `glossary.md`, or
#: the anchor alone, `#term-…`.
_ENTRY = r"(?:[^()\s:#]*/)?glossary\.md#term-[^()\s]*|#term-[^()\s]*"

#: A Markdown link to a glossary entry, as the command writes one: its text, and its
#: target.
_TERM_LINK = re.compile(rf"(?<!!)\[(?P<text>[^\[\]]+)\]\((?P<target>{_ENTRY})\)")

#: A line in the form of a section's link to its term, on its own: the term's id, and its
#: link to a glossary entry. Neither it nor a line that links a term to its section is
#: read for mentions.
DEFINED_LINE = re.compile(rf"^{DEFINED} \[(?P<id>[^\[\]\s]+)\]\((?P<target>{_ENTRY})\)\.\s*$")
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
        rel = posixpath.relpath(self.glossary, posixpath.dirname(from_path) or ".")
        return f"{rel}#{self.anchor}"


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

    def term(self, term_id: str) -> Term | None:
        return next((t for t in self.terms if t.id == term_id), None)


def vocabulary(analysis: Analysis, listing: analyses.Listing, folder: str | None) -> Vocabulary:
    """The terms whose mentions the analysis in `folder` links: its own terms in force, and
    each term its glossary's head lists from an analysis the repository holds, while it is
    in force there. A listed term is mentioned by the name the head lists, and by the
    noun forms and the other senses its own entry declares, and links to that entry by the
    name the entry gives it (DEC-004 point 7)."""
    found: list[Term] = []
    for artefact in analysis.of_kind(TERM):
        if artefact.folder == folder and not artefact.withdrawn:
            term = term_of(artefact)
            if term is not None:
                found.append(term)
    head = analyses.head(analysis, folder) if listing.several else None
    for taken in head.taken if head is not None else ():
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
    return Vocabulary(tuple(found), matched(found))


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
    on, counted from 1 in the file, the mention's text, the target written and the
    target wanted, and the term wanted, each `None` where there is none."""

    how: str
    line: int
    text: str
    written: str | None
    wanted: str | None
    term: str | None


@dataclass(frozen=True)
class _Found:
    start: int
    end: int
    target: str


@dataclass(frozen=True)
class _Wanted:
    start: int
    end: int
    target: str
    term: str


def _pattern(phrase: str) -> re.Pattern[str]:
    """A phrase as a mention matches it: its words as written, any white space between
    them, its first letter in either case and an apostrophe of either kind, whole."""
    words = phrase.split()
    parts: list[str] = []
    for i, word in enumerate(words):
        parts.append("".join(_char(ch, first=(i == 0 and k == 0)) for k, ch in enumerate(word)))
    body = _SPACE.join(parts)
    return re.compile(f"(?<!{_JOINER}){body}(?!{_JOINER})")


def mentions(text: str, name: str) -> bool:
    """Whether `text` holds `name` as a mention reads it: whole, its first letter in either
    case."""
    return _pattern(name).search(text) is not None


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


def _strip(text: str) -> tuple[str, list[_Found]]:
    """`text` with each link to a glossary entry outside code and comments unwritten, its
    text kept, and each such link, by where its text lies in what is left."""
    hidden = _hidden_lines(text)
    code = [
        (m.start(), m.end())
        for pattern in (_INLINE[0], _INLINE[1])
        for m in pattern.finditer(_masked(text, hidden))
    ] + hidden
    out: list[str] = []
    found: list[_Found] = []
    at = 0
    for match in _TERM_LINK.finditer(text):
        if _overlaps(match.start(), match.end(), code):
            continue
        out.append(text[at : match.start()])
        start = sum(len(part) for part in out)
        out.append(match["text"])
        found.append(_Found(start, start + len(match["text"]), match["target"]))
        at = match.end()
    out.append(text[at:])
    return "".join(out), found


def _hidden_lines(text: str) -> list[tuple[int, int]]:
    """The spans of the whole lines no mention is read on: fenced code with its fences,
    headings, the lines that link a term and its section, and reference definitions."""
    spans: list[tuple[int, int]] = []
    fence: tuple[str, int] | None = None
    at = 0
    for line in text.split("\n"):
        end = at + len(line)
        if fence is not None:
            spans.append((at, end))
            stripped = line.strip()
            if stripped and set(stripped) == {fence[0]} and len(stripped) >= fence[1]:
                fence = None
        else:
            opening = _FENCE.match(line)
            if opening is not None and not (
                opening.group(1).startswith("`") and "`" in opening.group(2)
            ):
                fence = (opening.group(1)[0], len(opening.group(1)))
                spans.append((at, end))
            elif any(p.match(line) for p in (_HEADING, _EXPLAINED_LINE, DEFINED_LINE, _REFERENCE)):
                spans.append((at, end))
        at = end + 1
    return spans


def _masked(text: str, spans: Sequence[tuple[int, int]]) -> str:
    """`text` with each of `spans` written over in spaces, its line ends kept."""
    chars = list(text)
    for start, end in spans:
        for k in range(start, end):
            if chars[k] != "\n":
                chars[k] = " "
    return "".join(chars)


def _skipped(text: str) -> tuple[list[tuple[int, int]], list[int]]:
    """The spans of `text` no mention is read in, and where each escape ends."""
    hidden = _hidden_lines(text)
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


def _chosen(text: str, vocabulary: Vocabulary) -> tuple[list[_Mention], list[int]]:
    """The mentions in `text`, the longest first, and where each escape ends."""
    skipped, escapes = _skipped(text)
    blocked: dict[str, list[tuple[int, int]]] = {}
    for term in vocabulary.terms:
        for phrase in term.other_senses:
            blocked.setdefault(term.id, []).extend(
                (m.start(), m.end()) for m in _pattern(phrase).finditer(text)
            )
    candidates: list[_Mention] = []
    for term in vocabulary.terms:
        for name in vocabulary.matched.get(term.id, ()):
            for m in _pattern(name).finditer(text):
                if _overlaps(m.start(), m.end(), skipped):
                    continue
                if any(s <= m.start() and m.end() <= e for s, e in blocked.get(term.id, ())):
                    continue
                candidates.append(_Mention(m.start(), m.end(), term.id))
    candidates.sort(key=lambda c: (c.start, -(c.end - c.start), c.term))
    chosen: list[_Mention] = []
    reached = 0
    for candidate in candidates:
        if candidate.start >= reached:
            chosen.append(candidate)
            reached = candidate.end
    return chosen, escapes


def _wanted(text: str, own: str | None, vocabulary: Vocabulary, path: str) -> list[_Wanted]:
    """The links the command writes in one section's `text`: the first mention of each term
    that is not the section's own and no escape marks."""
    mentions, escapes = _chosen(text, vocabulary)
    linked: set[str] = set()
    wanted: list[_Wanted] = []
    for mention in mentions:
        if any(
            text[end : mention.start].strip(" \t") == "" for end in escapes if end <= mention.start
        ):
            continue
        if mention.term == own or mention.term in linked:
            continue
        term = vocabulary.term(mention.term)
        if term is None:
            continue
        linked.add(mention.term)
        wanted.append(_Wanted(mention.start, mention.end, term.target(path), term.id))
    return wanted


def _render(text: str, wanted: Sequence[_Wanted]) -> str:
    out = text
    for link in sorted(wanted, key=lambda w: w.start, reverse=True):
        out = f"{out[: link.start]}[{out[link.start : link.end]}]({link.target}){out[link.end :]}"
    return out


def section(
    text: str, own: str | None, vocabulary: Vocabulary, path: str, first_line: int
) -> tuple[str, list[Difference]]:
    """One section's `text`, its links to terms written as the command writes them, and how
    the links it holds depart from those; `first_line` is the line `text` starts on in
    the file at `path`, and `own` the id of the section's own term."""
    plain, found = _strip(text)
    wanted = _wanted(plain, own, vocabulary, path)

    def line(offset: int) -> int:
        return first_line + plain.count("\n", 0, offset)

    differences: list[Difference] = []
    by_span = {(w.start, w.end): w for w in wanted}
    held = {(f.start, f.end): f for f in found}
    for key, link in sorted(held.items()):
        want = by_span.get(key)
        mention = plain[link.start : link.end]
        if want is None:
            differences.append(
                Difference(EXTRA, line(link.start), mention, link.target, None, None)
            )
        elif want.target != link.target:
            differences.append(
                Difference(STALE, line(link.start), mention, link.target, want.target, want.term)
            )
    for key, want in sorted(by_span.items()):
        if key not in held:
            mention = plain[want.start : want.end]
            differences.append(
                Difference(MISSING, line(want.start), mention, None, want.target, want.term)
            )
    differences.sort(key=lambda d: d.line)
    return _render(plain, wanted), differences


# --- a section's link to its term --------------------------------------------------------------


def defined(term: Term, path: str) -> str:
    """The line that links a view's section, in the file at `path`, to its term's entry."""
    return f"{DEFINED} [{term.id}]({term.target(path)})."


def view_sections(lines: Sequence[str], start: int) -> list[tuple[int, int]]:
    """Where each part of a view's body lies among `lines`, the body starting at index
    `start`: its opening, from the body's start to its first section, then each section,
    from its heading to the next one, each as the index of its first line and the index
    past its last. A heading inside fenced code opens no section."""
    starts: list[int] = []
    fence: tuple[str, int] | None = None
    for index in range(start, len(lines)):
        line = lines[index]
        if fence is not None:
            stripped = line.strip()
            if stripped and set(stripped) == {fence[0]} and len(stripped) >= fence[1]:
                fence = None
            continue
        opening = _FENCE.match(line)
        if opening is not None and not (
            opening.group(1).startswith("`") and "`" in opening.group(2)
        ):
            fence = (opening.group(1)[0], len(opening.group(1)))
            continue
        if re.match(r"^##(?:[ \t]|$)", line):
            starts.append(index)
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


def with_definitions(
    lines: list[str],
    sections: Sequence[tuple[int, int]],
    owners: Sequence[str | None],
    wanted: Sequence[str | None],
) -> tuple[list[str], list[tuple[str, int, str | None, str | None]]]:
    """A view's `lines` with each section's link to its term as `wanted` gives it, the
    k-th section's the k-th, its own term `owners`' k-th: the link the section holds
    (`defined_at`) rewritten to it, or taken out where none is wanted, and one written
    right below the heading where the section holds none. No other line is touched.
    Returns the lines, and how the section's links departed: `(how, line number,
    written, wanted)`, each line counted in the lines as given."""
    out = list(lines)
    differences: list[tuple[str, int, str | None, str | None]] = []
    for k, (first, past) in reversed(list(enumerate(sections))):
        want = wanted[k] if k < len(wanted) else None
        held = defined_at(lines, first, past, owners[k] if k < len(owners) else None)
        if held is not None:
            line = lines[held].strip()
            if want is None:
                differences.append((EXTRA, held + 1, line, None))
                del out[held]
            elif line != want:
                differences.append((STALE, held + 1, line, want))
                out[held] = want
        elif want is not None:
            differences.append((MISSING, first + 1, None, want))
            out[first + 1 : first + 1] = ["", want]
    differences.sort(key=lambda d: d[1])
    return out, differences


# --- a file ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Departure:
    """A link in a file that departs from what the command writes, at the location of the
    artefact that holds it."""

    location: str
    how: str
    line: int
    text: str
    written: str | None
    wanted: str | None
    term: str | None
    defined: bool = False


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
    vocabulary: Vocabulary,
) -> Linked:
    """The glossary at `path`, LF `text`, with the mentions' links of each of `entries`, the
    terms in force it holds, written: each entry's section as the backbone spans it,
    below its heading."""
    lines = text.split("\n")
    departures: list[Departure] = []
    for entry in sorted(entries, key=lambda e: e.span or (0, 0), reverse=True):
        if entry.span is None:
            continue
        first, last = entry.span
        body = lines[first : min(last, len(lines))]
        if not body:
            continue
        rewritten, found = section("\n".join(body), entry.id, vocabulary, path, first + 1)
        lines[first : first + len(body)] = rewritten.split("\n")
        departures += [_departure(entry.location, d) for d in found]
    departures.sort(key=lambda d: (d.line, d.location))
    return Linked(path, text, "\n".join(lines), tuple(departures))


def view(
    artefact: Artefact,
    text: str,
    vocabulary: Vocabulary,
) -> Linked:
    """A view in force, LF `text`, with each section's link to its term and the mentions'
    links written: its opening and each section below its heading."""
    path = artefact.path
    written = text.split("\n")
    start = body_start(written)
    explains = artefact.fields.get(EXPLAINS)
    listed = [t for t in explains if isinstance(t, str)] if isinstance(explains, list) else []
    concept = view_sections(written, start)[1:]
    wanted_lines: list[str | None] = []
    for k in range(len(concept)):
        term_id = listed[k] if k < len(listed) else None
        term = vocabulary.term(term_id) if term_id is not None else None
        wanted_lines.append(defined(term, path) if term is not None else None)
    owners: list[str | None] = [None, *(listed[: len(concept)])]
    lines, held = with_definitions(written, concept, owners[1:], wanted_lines)
    departures = [
        Departure(artefact.location, how, number, line or "", line, want, None, True)
        for how, number, line, want in held
    ]
    # The mentions are compared on the text as written, so each departure gives its line
    # there, and written on the text with each section's link to its term in place.
    departures += [
        _departure(artefact.location, d)
        for _rewritten, found in _mentions(written, start, owners, vocabulary, path)
        for d in found
    ]
    pieces = _mentions(lines, start, owners, vocabulary, path)
    linked: list[str] = list(lines[:start])
    for rewritten, _found in pieces:
        linked += rewritten.split("\n")
    departures.sort(key=lambda d: (d.line, d.how))
    return Linked(path, text, "\n".join(linked), tuple(departures))


def _mentions(
    lines: Sequence[str],
    start: int,
    owners: Sequence[str | None],
    vocabulary: Vocabulary,
    path: str,
) -> list[tuple[str, list[Difference]]]:
    """Each part of a view's body among `lines`, its opening then each section, with its
    mentions' links written, and how the links it holds depart from those. A part's own
    term is `owners`' entry in its place: none for the opening."""
    found: list[tuple[str, list[Difference]]] = []
    for k, (first, past) in enumerate(view_sections(lines, start)):
        if first == past:
            continue  # an opening with no line holds nothing to link
        own = owners[k] if k < len(owners) else None
        found.append(section("\n".join(lines[first:past]), own, vocabulary, path, first + 1))
    return found


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
    )


def plan(
    analysis: Analysis,
    listing: analyses.Listing,
    read: Mapping[str, str | None],
) -> list[Linked]:
    """Each file the links reach in the analyses that keep a domain model, the glossary and
    each view in force of each, as the command writes it. `read` gives each file's text by
    its path, LF line ends, `None` where it cannot be read, which is left out."""
    folders = [a.folder for a in listing.analyses] if listing.several else [None]
    found: list[Linked] = []
    for folder in folders:
        if not keeps_domain_model(analysis, folder):
            continue
        words = vocabulary(analysis, listing, folder)
        entries = [
            t for t in analysis.of_kind(TERM) if t.folder == folder and not t.withdrawn and t.id
        ]
        by_glossary: dict[str, list[Artefact]] = {}
        for entry in entries:
            by_glossary.setdefault(entry.path, []).append(entry)
        for path, held in sorted(by_glossary.items()):
            text = read.get(path)
            if text is not None:
                found.append(glossary(path, text, held, words))
        for artefact in sorted(analysis.of_kind(VIEW), key=lambda v: v.path):
            if artefact.folder != folder or artefact.withdrawn:
                continue
            text = read.get(artefact.path)
            if text is not None:
                found.append(view(artefact, text, words))
    return found


def files(analysis: Analysis, listing: analyses.Listing) -> list[str]:
    """The paths `plan` reads: each glossary and each view in force of every analysis that
    keeps a domain model."""
    folders = [a.folder for a in listing.analyses] if listing.several else [None]
    paths: set[str] = set()
    for folder in folders:
        if not keeps_domain_model(analysis, folder):
            continue
        paths |= {t.path for t in analysis.of_kind(TERM) if t.folder == folder and not t.withdrawn}
        paths |= {v.path for v in analysis.of_kind(VIEW) if v.folder == folder and not v.withdrawn}
    return sorted(paths)
