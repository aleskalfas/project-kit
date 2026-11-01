"""A requirement's `obligation`: a fingerprint of its statement, its measure and its scope
(software-analysis DEC-006 points 6 and 7).

Each requirement, of each of the three kinds and withdrawn or not, carries `obligation`,
an own field of its front matter. Its value names the version of the form its texts are
read in and the hash it uses, then the digest, `v1:sha256:<64 hex digits>`, as the
overview's fingerprint names its version (DEC-003 point 8). `pkit analysis obligation`
writes it, and the stamp writes it on a requirement it stamps. The check holds it equal to
the texts, whatever any rule's status, and fails a requirement without it (`findings`).

**The texts** (`texts`), each by its part's permanent id, in one order: `statement`,
`measure`, `applies-to`. A text is read where it lives: a front-matter field's value as
the front matter parses it, else the part of the body that holds it, found by its
permanent id as the check finds a part (`structure.part_of`), its kind as the project's
own structures relabel it (`links.parted`). A text in neither home reads as absent, which
differs from `None.` and from an empty text, so the fingerprint is always defined and a
part removed changes it. A field the front matter gives as no text, and a body that
cannot be read where it holds a text, give no fingerprint (`NoText`), never a partial one.

**One reading of both homes.** A field's text is read as the part it would be after its
label on the label's line (`structure.as_part`), and a part as the check reads it: the text
after its label, then each line to the part's end, its comments left out and a fenced line
whole. So a text moved word for word from one home to the other gives one fingerprint.

**Version 1 of the form** (`_read_v1`), what it sets aside and how it finds it:

- **Comments**, as the check finds one (`structure.py`): from `<!--` to the next `-->`,
  outside fenced code and outside a code span that closes on its line.
- **Fenced code** counts as written, line for line, as the check finds it.
- **A paragraph** is read as one run of inline text: it ends at a blank line and at fenced
  code, and a heading, or a line that opens a list item, starts one of its own. The text
  after a label, the first line, is inline text whatever it opens with.
- **Derived links**, as friction reads one (COR-050 point 5; the backbone's
  `document_parts.links_set_aside`): an inline link `[words](target)`, never an image,
  its words holding no bracket and its target no space and no parenthesis, outside a code
  span and a heading, whose target matches whole a form each requirement's place
  declares (`LINK_FORMS`). It reads as its words alone. The forms are those `pkit
  analysis link` writes and its check holds, which the places declare, never this
  version's.
- **The marks of emphasis and strong emphasis**, `*` and `_`, found by CommonMark's rules
  for delimiter runs within each paragraph: left- and right-flanking runs, the rules for
  `_` within a word, and the rule of three, a link's words read apart from the text around
  them. Each mark that pairs is set aside, and a mark that pairs with none counts.
- **Wrapping:** each run of white space, line breaks included, reads as one space, and
  none at either end. White space is a tab, a line feed, a form feed, a carriage return,
  and each space separator of Unicode.

Everything else counts as written: every word with its case and its punctuation, a code
span as friction finds one, an escape, an entity, inline HTML, an autolink, strikethrough,
a list's marker, and a link of a form no place declares. Tests of example texts pin the
version in both homes.

**The value.** The three texts as read, under their permanent ids, the version beside
them, as compact JSON with its keys sorted, hashed with SHA-256. A value names the version
it was read in, and the check verifies it under that version (`READERS`), so every version
the capability shipped stays here: a later version is added, and an earlier one never
changed. The command writes the current version (`VERSION`) only where the value a
requirement holds is missing or no longer verifies.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ruamel.yaml.error import YAMLError

from _lib import citations, forms, id_links, links, markdown, structure
from _lib.findings import ERROR, Finding, at
from _lib.model import REQUIREMENTS, Analysis, Artefact

#: The field, its texts by their parts' permanent ids in the order the form reads them, and
#: the command that writes it (DEC-006 points 6 and 7).
FIELD = "obligation"
TEXTS = ("statement", "measure", "applies-to")
COMMAND = "pkit analysis obligation"

#: The version of the form the command writes, and the hash every value of it uses.
VERSION = 1
HASH = "sha256"

#: A value as the field holds it: the form's version, the hash, the digest.
_VALUE = re.compile(r"^v(?P<version>[1-9][0-9]*):(?P<hash>[a-z0-9-]+):(?P<digest>[0-9a-f]+)$")
SHAPE = "v<version>:sha256:<digest>"

#: The forms of derived link each requirement's place declares, at the location's top and
#: one folder down: a link to a glossary entry by a path, a citation's and an id's (DEC-004
#: point 7, DEC-001 points 13 and 14). They are the targets `pkit analysis link` writes and
#: its check holds, which the package declares at each place, as a test holds. So a release
#: that adds a form adds it at both, and no version of the form fixes one (DEC-006 point 7).
#: A script reads no place's declaration itself (ADR-057 point 2).
LINK_FORMS = (links.ENTRY_BY_PATH, citations.TARGET, id_links.TARGET)

#: Where a text lives, as a message names it.
FRONT_MATTER, BODY = "front matter", "body"


class NoText(Exception):
    """A text the fingerprint cannot read, so it gives none; the message says why."""


@dataclass(frozen=True)
class Written:
    """A value as the field holds it: the version of the form, the hash and the digest."""

    version: int
    algorithm: str
    digest: str


def written(value: object) -> Written | None:
    """The value `value` gives, or `None` for one that is no fingerprint's shape."""
    found = _VALUE.match(value) if isinstance(value, str) else None
    if found is None:
        return None
    return Written(int(found["version"]), found["hash"], found["digest"])


@dataclass(frozen=True)
class Texts:
    """A requirement's three texts, each by its part's permanent id: the part it reads as,
    or `None` where it is absent, and the home it was read in."""

    parts: Mapping[str, forms.Part | None]
    homes: Mapping[str, str] = field(default_factory=dict)

    @property
    def absent(self) -> tuple[str, ...]:
        return tuple(text for text in TEXTS if self.parts.get(text) is None)


def texts(
    fields: Mapping[str, Any],
    body: Callable[[], Sequence[structure.Line]],
    kind: structure.Kind | None,
) -> Texts:
    """A requirement's texts: each from its front-matter field, else from the part of its
    body with the text's permanent id, as `kind` declares its parts. `body` gives the
    body's lines, and is asked only where a field is missing. Raises `NoText` where a field
    holds no text, or where the body or its kind cannot be read and a text may lie there."""
    parts: dict[str, forms.Part | None] = {}
    homes: dict[str, str] = {}
    lines: Sequence[structure.Line] | None = None
    for text in TEXTS:
        if text in fields:
            value = fields[text]
            if not isinstance(value, str):
                raise NoText(f"its `{text}` is no text, so the fingerprint cannot read it")
            parts[text], homes[text] = structure.as_part(value), FRONT_MATTER
            continue
        if kind is None:
            raise NoText(
                f"it gives no `{text}` field, and the kinds' declared structure, which says "
                f"where its body holds that text, cannot be read"
            )
        if lines is None:
            lines = body()
        part = structure.part_of(lines, kind, text)
        parts[text] = part
        if part is not None:
            homes[text] = BODY
    return Texts(parts, homes)


def value(read: Texts, link_forms: Sequence[str], version: int = VERSION) -> str:
    """The fingerprint of `read` under the form's `version`, as the field holds it.
    Raises `KeyError` for a version the capability does not know."""
    reader = READERS[version]
    data = {
        "form": version,
        "texts": [
            [text, None if part is None else reader(part, link_forms)]
            for text, part in ((t, read.parts.get(t)) for t in TEXTS)
        ],
    }
    dumped = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return f"v{version}:{HASH}:{hashlib.sha256(dumped.encode('utf-8')).hexdigest()}"


def canonical(
    part: forms.Part | None, link_forms: Sequence[str], version: int = VERSION
) -> str | None:
    """One text as the form's `version` reads it; `None` for an absent one."""
    return None if part is None else READERS[version](part, link_forms)


# --- what a value says of its texts ------------------------------------------------------------

#: How a requirement's `obligation` stands against its texts.
HOLDS, MISSING, MISSHAPEN, UNKNOWN, STALE = "holds", "missing", "misshapen", "unknown", "stale"


@dataclass(frozen=True)
class Verdict:
    """How a requirement's `obligation` stands (`how`), the value the command writes under
    the current version, and the texts read as absent, which a message names first."""

    how: str
    wanted: str
    absent: tuple[str, ...] = ()
    held: object = None


def judged(fields: Mapping[str, Any], read: Texts, link_forms: Sequence[str]) -> Verdict:
    """How the `obligation` in `fields` stands against `read`: missing; misshapen, no
    fingerprint's shape; unknown, a version or a hash this release does not read; stale, no
    longer the texts' fingerprint under the version it names; or holding."""
    wanted = value(read, link_forms)
    if FIELD not in fields:
        return Verdict(MISSING, wanted, read.absent)
    held = fields[FIELD]
    parsed = written(held)
    if parsed is None:
        return Verdict(MISSHAPEN, wanted, read.absent, held)
    if parsed.version not in READERS or parsed.algorithm != HASH:
        return Verdict(UNKNOWN, wanted, read.absent, held)
    if value(read, link_forms, parsed.version) != held:
        return Verdict(STALE, wanted, read.absent, held)
    return Verdict(HOLDS, wanted, read.absent, held)


# --- one requirement in the working tree ------------------------------------------------------


@dataclass(frozen=True)
class Kinds:
    """The requirement kinds' parts as the fingerprint finds them, whatever any rule's
    status (`links.parted`), or why the declared structure cannot be read."""

    of: Mapping[str, structure.Kind]
    problem: str | None = None


def kinds(root: Path) -> Kinds:
    """The kinds' parts at `root`, as the project's own structures relabel them."""
    try:
        return Kinds(links.parted(root))
    except structure.Unreadable as exc:
        return Kinds({}, f"the kinds' declared structure cannot be read: {exc}")


def read(root: Path, artefact: Artefact, parted: Kinds) -> tuple[Texts, tuple[str, ...]]:
    """A requirement's texts in the working tree at `root`, and the forms of derived link
    its place declares (`LINK_FORMS`). Raises `NoText` where a text cannot be read."""

    def body() -> list[structure.Line]:
        try:
            text = (root / artefact.path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise NoText(f"its file cannot be read ({exc})") from exc
        return structure.body_lines(text)

    kind = parted.of.get(artefact.kind)
    if kind is None and parted.problem is not None and any(t not in artefact.fields for t in TEXTS):
        raise NoText(f"a text it gives no field for may lie in its body, and {parted.problem}")
    return texts(artefact.fields, body, kind), LINK_FORMS


#: How a message names each text.
SAID = {"statement": "its statement", "measure": "its measure", "applies-to": "where it holds"}


def findings(root: Path, analysis: Analysis) -> list[Finding]:
    """Each requirement whose `obligation` is missing, is no fingerprint, names a version or
    a hash this release does not read, or no longer matches its texts, whatever any rule's
    status, a withdrawn one included (DEC-006 point 6). Each names the command. A text the
    front matter gives as no text is its schema's to report, so its requirement is not
    judged here."""
    requirements = [a for a in analysis.artefacts if a.kind in REQUIREMENTS]
    if not requirements:
        return []
    parted = kinds(root)
    found: list[Finding] = []
    for artefact in requirements:
        if any(t in artefact.fields and not isinstance(artefact.fields[t], str) for t in TEXTS):
            continue
        where = at(artefact.location, f"/{FIELD}")
        try:
            read_, forms_ = read(root, artefact, parted)
        except NoText as exc:
            found.append(
                Finding(
                    ERROR,
                    where,
                    f"whether it matches the requirement's texts cannot be told: {exc}. Mend "
                    f"that, then run `{COMMAND}` where it asks (DEC-006 point 6)",
                )
            )
            continue
        verdict = judged(artefact.fields, read_, forms_)
        if verdict.how != HOLDS:
            found.append(Finding(ERROR, where, message(verdict, parted.of.get(artefact.kind))))
    return found


def message(verdict: Verdict, kind: structure.Kind | None) -> str:
    """What a finding says of `verdict`: each text read as absent first, so a writer mends
    a part's label rather than writes a new value, then what stands and the command."""
    texts_ = "its statement, its measure and where it holds"
    if verdict.how == MISSING:
        said = (
            f"it carries no `{FIELD}`, the fingerprint of {texts_}, which the check holds equal "
            f"to them: run `{COMMAND}` to write it, and commit it with the change (DEC-006 "
            f"point 6)"
        )
    elif verdict.how == MISSHAPEN:
        said = (
            f"it reads {verdict.held!r}, which is no fingerprint, `{SHAPE}`: run `{COMMAND}` to "
            f"write it anew, and commit it with the change (DEC-006 point 6)"
        )
    elif verdict.how == UNKNOWN:
        parsed = written(verdict.held)
        named = (
            f"version {parsed.version} of the form, hashed with {parsed.algorithm}"
            if parsed
            else ""
        )
        said = (
            f"it names {named}, which this release does not read, so whether it matches "
            f"{texts_} cannot be told: upgrade software-analysis, or delete the field and run "
            f"`{COMMAND}` to write it under version {VERSION} (DEC-006 point 7)"
        )
    else:
        said = (
            f"it no longer matches {texts_}: one of them changed since it was written. Run "
            f"`{COMMAND}` to write it anew, and commit it with the change (DEC-006 point 6)"
        )
    if not verdict.absent:
        return said
    return f"{_absent(verdict.absent, kind)} {said[0].upper()}{said[1:]}"


def _absent(absent: Sequence[str], kind: structure.Kind | None) -> str:
    """What a message says first of the texts read as absent: where each was looked for."""
    each = []
    for text in absent:
        label = next(
            (e.text for e in (kind.sections if kind else ()) if e.id == text and e.text), None
        )
        part = f"no part *{label}* in its body" if label else "no part of that id in its body"
        each.append(f"{SAID[text]} (no `{text}` field, and {part})")
    listed = each[0] if len(each) == 1 else ", ".join(each[:-1]) + f" and {each[-1]}"
    return (
        f"It reads {listed} as absent: where one belongs, write it, or mend its part's label, "
        f"first."
    )


# --- writing the field ------------------------------------------------------------------------


class Unwritable(Exception):
    """The field cannot be written in a file's front matter; the message says why."""


#: The fields `obligation` follows in a requirement's front matter, in their order.
_BEFORE = ("id", "title", "status", *TEXTS)

#: A comment line at the left margin, which describes the key below it.
_MARGIN_COMMENT = re.compile(r"^#")


def with_value(text: str, wanted: str) -> str:
    """A requirement's LF `text` with `obligation` reading `wanted`: its line replaced where
    the front matter holds one, else a line written after the last of its id, title,
    status and texts, above any comment at the margin that opens the next key. Every other
    line is kept as written. Raises `Unwritable` where the front matter does not parse, or
    where the result would read any other value differently."""
    span = markdown.front_matter_span(text)
    if span is None:
        raise Unwritable("it has no front matter")
    start, end = span
    yaml_text = text[start:end]
    try:
        before = markdown.load(yaml_text)
        keys = markdown.key_lines(yaml_text)
    except YAMLError as exc:
        raise Unwritable(f"its front matter does not parse ({exc})") from exc
    if not isinstance(before, dict):
        raise Unwritable("its front matter is no mapping")
    lines = yaml_text.splitlines(keepends=True)
    line = f"{FIELD}: {wanted}\n"
    if FIELD in keys:
        first = keys[FIELD]
        stop = _next_key(keys, first, len(lines))
        while stop - 1 > first and (
            not lines[stop - 1].strip() or _MARGIN_COMMENT.match(lines[stop - 1])
        ):
            stop -= 1
        lines[first:stop] = [line]
    else:
        present = [keys[k] for k in _BEFORE if k in keys]
        at_line = 0 if not present else _next_key(keys, max(present), len(lines))
        while present and at_line - 1 > max(present) and _MARGIN_COMMENT.match(lines[at_line - 1]):
            at_line -= 1
        lines[at_line:at_line] = [line]
    rewritten = "".join(lines)
    try:
        after = markdown.load(rewritten)
    except YAMLError as exc:
        raise Unwritable(f"the field could not be written in its front matter ({exc})") from exc
    if after != {**before, FIELD: wanted}:
        raise Unwritable(
            "the field could not be written without changing another value of its front matter"
        )
    return text[:start] + rewritten + text[end:]


def _next_key(keys: Mapping[str, int], line: int, past: int) -> int:
    """The line of the first key below `line`, or `past` where none is."""
    return min((n for n in keys.values() if n > line), default=past)


# --- version 1 of the form ---------------------------------------------------------------------

#: Friction's reading of a link and a code span (the backbone's `document_parts`): an inline
#: link, never an image, and a code span, which crosses a line break but never a blank line.
#: A test holds both to the backbone's.
_INLINE_LINK = re.compile(r"(?<!!)\[(?P<words>[^\[\]]+)\]\((?P<target>[^()\s]+)\)")
_CODE_SPAN = re.compile(r"(?<!`)(`+)(?!`)(?:[^\n]|\n(?![ \t]*\n))+?(?<!`)\1(?!`)")

#: A heading, and a line that opens a list item, each of which starts a paragraph of its own.
_HEADING = re.compile(r"^ {0,3}#{1,6}(?:[ \t]|$)")
_ITEM = re.compile(r"^[ \t]*(?:[-+*]|[0-9]{1,9}[.)])(?:[ \t]|$)")

#: What a backslash escapes, an autolink, and inline HTML: each counts as written, and holds
#: no mark of emphasis.
_ESCAPABLE = frozenset("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")
_AUTOLINK = re.compile(
    r"<[A-Za-z][A-Za-z0-9+.\-]{1,31}:[^\x00-\x20<>]*>"
    r"|<[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*>"
)
_ATTRIBUTE = r"""\s+[A-Za-z_:][A-Za-z0-9_.:-]*(?:\s*=\s*(?:[^\s"'=<>`]+|'[^']*'|"[^"]*"))?"""
_HTML = re.compile(
    rf"<[A-Za-z][A-Za-z0-9-]*(?:{_ATTRIBUTE})*\s*/?>|</[A-Za-z][A-Za-z0-9-]*\s*>"
    r"|<\?.*?\?>|<![A-Za-z][^>]*>|<!\[CDATA\[.*?\]\]>",
    re.S,
)

#: The characters a mark of emphasis is made of.
_MARKS = "*_"


def _read_v1(part: forms.Part, link_forms: Sequence[str]) -> str:
    """A text as version 1 of the form reads it (the module's docstring)."""
    patterns = tuple(re.compile(form) for form in link_forms)

    def aside(target: str) -> bool:
        return any(pattern.fullmatch(target) for pattern in patterns)

    rows = [*((part.lead,) if part.lead is not None else ()), *part.rows]
    blocks: list[str] = []
    run: list[str] = []

    def close() -> None:
        if run:
            blocks.append(_paragraph("\n".join(run), aside))
            run.clear()

    for index, row in enumerate(rows):
        first = index == 0 and part.lead is not None
        if row.fence:
            close()
            blocks.append(row.text)
        elif not row.text.strip():
            close()
        elif not first and _HEADING.match(row.text):
            close()
            blocks.append(_paragraph(row.text, lambda _target: False))
        else:
            if not first and _ITEM.match(row.text):
                close()
            run.append(row.text)
    close()
    return _collapsed("\n".join(blocks))


def _paragraph(text: str, aside: Callable[[str], bool]) -> str:
    """One paragraph's inline text, its derived links read as their words and the marks of
    emphasis that pair set aside."""
    spans = [m.span() for m in _CODE_SPAN.finditer(text)]
    links = {
        m.start(): m
        for m in _INLINE_LINK.finditer(text)
        if not any(m.start() < end and start < m.end() for start, end in spans)
    }
    return _inline(text, 0, len(text), dict(spans), links, aside)


@dataclass
class _Run:
    """A run of one mark of emphasis: the mark, how many of it are left, how many it had,
    and whether it may open and close emphasis."""

    mark: str
    left: int
    length: int
    opens: bool
    closes: bool


def _inline(
    text: str,
    start: int,
    end: int,
    spans: Mapping[int, int],
    links: Mapping[int, re.Match[str]],
    aside: Callable[[str], bool],
) -> str:
    """`text[start:end]` read as inline text: a code span, an escape, an autolink and inline
    HTML as written, a link's words read apart from the text around them, a derived link as
    its words alone, and the marks of emphasis that pair set aside."""
    out: list[str | _Run] = []
    runs: list[_Run] = []
    at = start
    while at < end:
        char = text[at]
        if at in spans and spans[at] <= end:
            out.append(text[at : spans[at]])
            at = spans[at]
        elif at in links and links[at].end() <= end:
            link = links[at]
            words = _inline(text, link.start("words"), link.end("words"), spans, links, aside)
            out.append(words if aside(link["target"]) else f"[{words}]({link['target']})")
            at = link.end()
        elif char == "\\" and at + 1 < end and text[at + 1] in _ESCAPABLE:
            out.append(text[at : at + 2])
            at += 2
        elif char == "<" and (tag := _AUTOLINK.match(text, at, end) or _HTML.match(text, at, end)):
            out.append(tag.group(0))
            at = tag.end()
        elif char in _MARKS:
            stop = at
            while stop < end and text[stop] == char:
                stop += 1
            run = _run(text, char, at, stop)
            out.append(run)
            runs.append(run)
            at = stop
        else:
            out.append(char)
            at += 1
    _pair(runs)
    return "".join(piece if isinstance(piece, str) else piece.mark * piece.left for piece in out)


def _run(text: str, mark: str, start: int, stop: int) -> _Run:
    """The run of `mark` at `text[start:stop]`, with whether it may open and close emphasis
    by CommonMark's flanking rules: the start and end of the paragraph read as white space."""
    before = text[start - 1] if start > 0 else "\n"
    after = text[stop] if stop < len(text) else "\n"
    left = not _space(after) and (not _punctuation(after) or _space(before) or _punctuation(before))
    right = not _space(before) and (
        not _punctuation(before) or _space(after) or _punctuation(after)
    )
    if mark == "*":
        opens, closes = left, right
    else:
        opens = left and (not right or _punctuation(before))
        closes = right and (not left or _punctuation(after))
    length = stop - start
    return _Run(mark, length, length, opens, closes)


def _pair(runs: list[_Run]) -> None:
    """CommonMark's processing of emphasis over `runs`, in order: each run that may close
    pairs with the nearest earlier one of its mark that may open, by the rule of three,
    strong emphasis taking two of each where both have two. What pairs is set aside: each
    run keeps the marks that paired with none."""
    stack = list(runs)
    i = 0
    while i < len(stack):
        closer = stack[i]
        if not closer.closes:
            i += 1
            continue
        j = next((j for j in range(i - 1, -1, -1) if _pairs(stack[j], closer)), None)
        if j is None:
            if closer.opens:
                i += 1
            else:
                del stack[i]
            continue
        opener = stack[j]
        used = 2 if opener.left >= 2 and closer.left >= 2 else 1
        opener.left -= used
        closer.left -= used
        del stack[j + 1 : i]
        i = j + 1
        if opener.left == 0:
            del stack[j]
            i = j
        if closer.left == 0:
            del stack[i]


def _pairs(opener: _Run, closer: _Run) -> bool:
    """Whether `opener` may pair with `closer`: one mark, it may open, and the rule of three,
    which a run that may both open and close keeps."""
    if opener.mark != closer.mark or not opener.opens:
        return False
    either = opener.closes or closer.opens
    both_threes = opener.length % 3 == 0 and closer.length % 3 == 0
    return not (either and (opener.length + closer.length) % 3 == 0 and not both_threes)


def _space(char: str) -> bool:
    return char in "\t\n\f\r" or unicodedata.category(char) == "Zs"


def _punctuation(char: str) -> bool:
    return unicodedata.category(char)[0] in "PS"


def _collapsed(text: str) -> str:
    """`text` with each run of white space read as one space, and none at either end."""
    out: list[str] = []
    spaced = False
    for char in text:
        if _space(char):
            spaced = True
            continue
        if spaced and out:
            out.append(" ")
        spaced = False
        out.append(char)
    return "".join(out)


#: Each version of the form the capability shipped, by its number, and how it reads a text.
#: A version is added, never changed, so every value written under one still verifies.
READERS: dict[int, Callable[[forms.Part, Sequence[str]], str]] = {1: _read_v1}
