"""Write and check the contents list of project-kit's pages (#2053).

A page a reader moves around in, such as a long guide or a reference, holds a
contents list of its second-level sections near its top. This script writes each
list, and fails where one is stale, so nobody keeps a list by hand.

- **Which pages:** every artefact of living-docs' page type, `living-docs:page`, as
  the backbone's discovery types it, wherever it lies, as the console fences' run
  chooses them (`scripts/console_fences.py`).
- **How a page opts in:** it holds the two markers, `<!-- pkit:contents -->` and
  below it `<!-- /pkit:contents -->`, each alone on its line, outside fenced code.
  Both are HTML comments, which a host renders as nothing. A page holds one pair
  at most, and a page without them is left alone.
- **Where the markers stand:** in the page's lead, or under a second-level heading
  of their own, such as `## Contents`. Under their own heading, a section renamed
  changes only that section, and the lead stays still.
- **What the list holds:** one item for each second-level heading of the page, in
  the page's order, `- [<text>](#<address>)`, but the one whose section holds the
  markers: the nearest heading of level one or two above the opening marker, when
  it is of level two. A heading is read as the backbone
  reads one (`project_kit.document_parts.body_headings`): an ATX heading outside
  fenced code. Where the host reads a page otherwise, as it does a heading in a
  block quote, or a fence's line with an info string, the list follows the backbone.
  The item's text is the heading's, with a link read as its words, an image and an
  HTML tag dropped, and white space runs read as one space.
- **The address:** the one the host renders for the heading, as GitHub makes it.
  The heading's text is rendered first: a code span's text is kept, a link's words
  and an autolink's text are kept, an image, an HTML tag and the underscores of
  emphasis are dropped, and an entity or an escape is read as the character it
  stands for. The text, without the spaces that open and end it, then takes the
  backbone's slug (`document_parts.heading_slug`, COR-050 point 2), with its
  underscores kept: lower case, each space a hyphen, every other character but
  letters, digits and hyphens dropped. A second heading of any level with the same
  address takes `-1`, a third `-2`, and so on, skipping an address an earlier
  heading took.
- **Where the host differs from the backbone:** a section anchor's slug drops
  underscores and numbers no repeated heading (COR-050 point 2). So a section anchor
  and a contents list's link name a heading alike, but where the heading holds an
  underscore, markup, or the title of an earlier heading.
- **An explicit anchor:** an HTML anchor a page keeps for a section's old address,
  such as `<a id="old-address"></a>` on the line before the heading, changes no
  item. The item links the heading's own address.
- **`--update`:** writes each stale list between its markers, and nothing else of
  the page. It writes no list in a page whose markers do not make one pair.

From the repository root:

    uv run python scripts/page_contents.py               # check every page
    uv run python scripts/page_contents.py README.md     # check one page
    uv run python scripts/page_contents.py --update      # write the lists

Exit 0 when every list is fresh, or no page holds one, or `--update` wrote every
stale list. Exit 1 on a stale list, or on markers that make no one pair, and 2 when
the run cannot start: the configuration or a page cannot be read, or a path named
is no page.
"""

from __future__ import annotations

import argparse
import difflib
import html
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from project_kit import friction_discovery, validators
from project_kit.document_parts import (
    Body,
    Heading,
    body_first_line,
    heading_slug,
    split_front_matter,
)

ROOT = Path(__file__).resolve().parents[1]

#: living-docs' page type (COR-056): the pages this script reads.
PAGE_TYPE = "living-docs:page"
#: The markers a page holds its contents list between, each alone on its line.
OPENING = "<!-- pkit:contents -->"
CLOSING = "<!-- /pkit:contents -->"
#: The level of the headings a contents list names.
LEVEL = 2
#: How to refresh a stale list.
UPDATE = "uv run python scripts/page_contents.py --update"


class CannotRun(Exception):
    """The run cannot start: the configuration or a page cannot be read, or a path
    named is no page."""


# --- a heading's text and address ----------------------------------------------------

# A run of backticks: a code span opens on one and closes on the next run of the same
# length.
_TICKS = re.compile(r"`+")
# The ASCII punctuation a backslash escapes.
_PUNCTUATION = frozenset("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")
# Where a code span or an escaped character stands while the rest of a text is read:
# characters of a private-use plane, which no page holds.
_HELD = 0xF0000
_ESCAPED = 0xF8000

_ATTRIBUTE = r"""\s+[A-Za-z_:][A-Za-z0-9_.:-]*(?:\s*=\s*(?:[^\s"'=<>`]+|'[^']*'|"[^"]*"))?"""
# A raw HTML tag, as CommonMark reads one: an opening or a closing tag, a comment, a
# processing instruction, a declaration or a CDATA section.
_HTML_TAG = re.compile(
    rf"<[A-Za-z][A-Za-z0-9-]*(?:{_ATTRIBUTE})*\s*/?>"
    r"|</[A-Za-z][A-Za-z0-9-]*\s*>"
    r"|<!--.*?-->"
    r"|<\?.*?\?>"
    r"|<![A-Za-z][^>]*>"
    r"|<!\[CDATA\[.*?\]\]>",
    re.S,
)
# An autolink, a URL or an email address between angle brackets.
_AUTOLINK = re.compile(
    r"<([A-Za-z][A-Za-z0-9+.-]{1,31}:[^\s<>]*"
    r"|[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)*)>"
)
# An image, `![alt](target)` or `![alt][ref]`.
_IMAGE = re.compile(r"!\[[^\[\]]*\](?:\([^()]*\)|\[[^\[\]]*\])")
# A link, `[words](target)`, `[words][ref]` or `[words][]`: its words.
_LINK = re.compile(r"\[([^\[\]]*)\](?:\([^()]*\)|\[[^\[\]]*\])")
# An HTML entity: named, decimal or hexadecimal.
_ENTITY = re.compile(r"&(?:[A-Za-z][A-Za-z0-9]{0,31}|#[0-9]{1,7}|#[xX][0-9A-Fa-f]{1,6});")
_UNDERSCORES = re.compile(r"_+")


@dataclass(frozen=True)
class _Read:
    """A heading's text with each code span held by one character and each escaped
    character by another. `spans` gives each code span by the character that holds it."""

    text: str
    spans: dict[str, tuple[str, str]]  # character -> (the span as written, its text)


def _read(title: str) -> _Read:
    """A heading's text, read left to right as CommonMark reads it: a backslash before
    ASCII punctuation escapes it, so an escaped backtick opens no code span, and a run of
    backticks opens a code span that the next run of the same length closes."""
    out: list[str] = []
    spans: dict[str, tuple[str, str]] = {}
    at = 0
    while at < len(title):
        char = title[at]
        if char == "\\" and at + 1 < len(title) and title[at + 1] in _PUNCTUATION:
            out.append(chr(_ESCAPED + ord(title[at + 1])))
            at += 2
            continue
        ticks = _TICKS.match(title, at)
        if ticks is None:
            out.append(char)
            at += 1
            continue
        run = ticks.group()
        closing = next(
            (m for m in _TICKS.finditer(title, ticks.end()) if m.group() == run),
            None,
        )
        if closing is None:
            out.append(run)
            at = ticks.end()
            continue
        inner = title[ticks.end() : closing.start()]
        if inner.startswith(" ") and inner.endswith(" ") and inner.strip(" "):
            inner = inner[1:-1]
        held = chr(_HELD + len(spans))
        spans[held] = (title[at : closing.end()], inner)
        out.append(held)
        at = closing.end()
    return _Read("".join(out), spans)


def _escaped(text: str, *, as_written: bool) -> str:
    """`text` with each escaped character given back: as written, its backslash before
    it, or as the character it stands for."""
    return "".join(
        ("\\" if as_written else "") + chr(ord(ch) - _ESCAPED)
        if _ESCAPED <= ord(ch) < _ESCAPED + 128
        else ch
        for ch in text
    )


def _without_markup(text: str) -> str:
    """`text` with each image and HTML tag dropped, each link read as its words and each
    autolink as its text."""
    text = _AUTOLINK.sub(lambda m: m.group(1), text)
    text = _HTML_TAG.sub("", text)
    text = _IMAGE.sub("", text)
    while True:
        unlinked = _LINK.sub(lambda m: m.group(1), text)
        if unlinked == text:
            return text
        text = unlinked


def _punctuation(ch: str | None) -> bool:
    return ch is not None and not ch.isalnum() and not ch.isspace() and ord(ch) < _HELD


def _space(ch: str | None) -> bool:
    return ch is None or ch.isspace()


def _without_emphasis(text: str) -> str:
    """`text` with the underscores that open or close emphasis dropped, as CommonMark
    pairs them: a run that may open is closed by the next run that may close. A run
    inside a word, as in `depends_on`, and a run left unpaired stay as written."""
    runs: list[tuple[int, int, bool, bool]] = []
    for match in _UNDERSCORES.finditer(text):
        start, end = match.span()
        before = text[start - 1] if start else None
        after = text[end] if end < len(text) else None
        left = not _space(after) and (
            not _punctuation(after) or _space(before) or _punctuation(before)
        )
        right = not _space(before) and (
            not _punctuation(before) or _space(after) or _punctuation(after)
        )
        opens = left and (not right or _punctuation(before))
        closes = right and (not left or _punctuation(after))
        runs.append((start, end, opens, closes))
    dropped: set[int] = set()
    # Each opener's underscores not yet paired, `[start, end]`: an opener gives up those
    # at its end, and a closer those at its start, the ones beside the emphasised text.
    openers: list[list[int]] = []
    for start, end, opens, closes in runs:
        while closes and start < end and openers:
            opener = openers[-1]
            taken = min(opener[1] - opener[0], end - start)
            dropped.update(range(opener[1] - taken, opener[1]))
            dropped.update(range(start, start + taken))
            opener[1] -= taken
            start += taken
            if opener[0] == opener[1]:
                openers.pop()
        if opens and start < end:
            openers.append([start, end])
    return "".join(ch for index, ch in enumerate(text) if index not in dropped)


def rendered(title: str) -> str:
    """A heading's text as the host renders it: a code span's text kept, each link read
    as its words, an image, an HTML tag and the underscores of emphasis dropped, and each
    entity and escape read as the character it stands for."""
    read = _read(title)
    text = _without_emphasis(_without_markup(read.text))
    text = _ENTITY.sub(lambda m: html.unescape(m.group()), text)
    for held, (_written, inner) in read.spans.items():
        text = text.replace(held, inner)
    return _escaped(text, as_written=False)


def shown(title: str) -> str:
    """A heading's text as its item shows it: as written, but each link read as its
    words, an image and an HTML tag dropped, and white space runs read as one space."""
    read = _read(title)
    text = " ".join(_without_markup(read.text).split())
    for held, (written, _inner) in read.spans.items():
        text = text.replace(held, written)
    return _escaped(text, as_written=True)


def address(title: str) -> str:
    """A heading's address before numbering: its rendered text, without the spaces that
    open and end it, in the backbone's slug with underscores kept (`heading_slug`)."""
    return "_".join(heading_slug(part) for part in rendered(title).strip().split("_"))


def addresses(titles: Sequence[str]) -> list[str]:
    """The address of each heading of a page, in order: a second heading with the same
    address takes `-1`, a third `-2`, and so on, skipping an address an earlier heading
    took."""
    taken: set[str] = set()
    repeats: dict[str, int] = {}
    found: list[str] = []
    for title in titles:
        base = unique = address(title)
        while unique in taken:
            repeats[base] = repeats.get(base, 0) + 1
            unique = f"{base}-{repeats[base]}"
        taken.add(unique)
        found.append(unique)
    return found


# --- a page's list ---------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """What fails at a page's line. `rewritable` when `--update` writes it right: the
    list between the page's markers is stale."""

    path: str
    line: int
    message: str
    detail: tuple[str, ...] = ()
    rewritable: bool = False

    def render(self) -> str:
        return "\n".join([f"{self.path}:{self.line}: {self.message}", *self.detail])


@dataclass(frozen=True)
class Contents:
    """A page's contents list: the indices of its markers' lines in the file, the lines
    between them, and the lines the list should hold. `problem` says why the markers
    make no one pair, at `problem_line`."""

    opening: int | None = None
    closing: int | None = None
    written: tuple[str, ...] = ()
    expected: tuple[str, ...] = ()
    problem: str | None = None
    problem_line: int = 0

    @property
    def held(self) -> bool:
        """Whether the page holds a marker."""
        return self.opening is not None or self.problem is not None

    @property
    def fresh(self) -> bool:
        return self.written == self.expected


def holder(headings: Sequence[Heading], at: int | None) -> int | None:
    """The index of the second-level heading whose section holds the body's offset
    `at`: the last heading of level two or above that starts before it, when that
    heading is of level two. `None` when `at` lies in the lead or under a first-level
    heading, or is `None`."""
    if at is None:
        return None
    above = [
        index
        for index, heading in enumerate(headings)
        if heading.start < at and heading.level <= LEVEL
    ]
    if not above or headings[above[-1]].level != LEVEL:
        return None
    return above[-1]


def items(body: str, at: int | None = None) -> list[str]:
    """The items of a page body's contents list: one for each second-level heading, in
    order, linked by its address. The section that holds the body's offset `at`, where
    the list's opening marker stands, is left out: a list under its own heading names
    every other section."""
    headings = Body.read(body).headings
    found = addresses([heading.title for heading in headings])
    own = holder(headings, at)
    return [
        f"- [{shown(heading.title)}](#{where})"
        for index, (heading, where) in enumerate(zip(headings, found, strict=True))
        if heading.level == LEVEL and index != own
    ]


def contents(text: str) -> Contents:
    """A page's contents list, read from the page's whole `text`."""
    _front_matter, body = split_front_matter(text)
    first = body_first_line(text, body) - 1
    openings: list[int] = []
    closings: list[int] = []
    at: int | None = None  # where the first opening marker starts in the body
    for line in Body.read(body).lines():
        marker = line.text.strip()
        if marker in (OPENING, CLOSING):
            index = first + body.count("\n", 0, line.start)
            (openings if marker == OPENING else closings).append(index)
            if marker == OPENING and at is None:
                at = line.start
    if not openings and not closings:
        return Contents()
    opening = openings[0] if openings else None
    if len(openings) > 1:
        return Contents(
            opening,
            problem=f"a second `{OPENING}`: a page holds one contents list",
            problem_line=openings[1] + 1,
        )
    stray = next((at for at in closings if opening is None or at < opening), None)
    if stray is None and len(closings) > 1:
        stray = closings[1]
    if stray is not None:
        return Contents(
            opening,
            problem=f"`{CLOSING}` closes no contents list: no `{OPENING}` opens one above it",
            problem_line=stray + 1,
        )
    if opening is None or not closings:
        return Contents(
            opening,
            problem=f"`{OPENING}` opens a contents list that no `{CLOSING}` closes",
            problem_line=(opening or 0) + 1,
        )
    lines = text.split("\n")
    return Contents(
        opening, closings[0], tuple(lines[opening + 1 : closings[0]]), tuple(items(body, at))
    )


def updated(text: str, found: Contents) -> str:
    """`text` with the lines between its markers replaced by the list it should hold."""
    assert found.opening is not None and found.closing is not None
    lines = text.split("\n")
    return "\n".join([*lines[: found.opening + 1], *found.expected, *lines[found.closing :]])


# --- the run ---------------------------------------------------------------------------


@dataclass
class Report:
    pages: int = 0
    lists: int = 0
    findings: list[Finding] = field(default_factory=list[Finding])
    updated: list[str] = field(default_factory=list[str])


def pages(root: Path) -> list[str]:
    """The paths of every artefact living-docs' page type types, or counts as in a tie,
    as the backbone's discovery reads them. Raises CannotRun when the configuration
    cannot be read."""
    problem = friction_discovery.unreadable_configuration(root)
    if problem is not None:
        raise CannotRun(f"{problem}; `pkit validate` reports it")
    discovery = validators.as_one_run(lambda: friction_discovery.discover_artefacts(root))
    types = discovery.types
    return sorted(
        {
            artefact.path
            for artefact in discovery.artefacts
            if artefact.kind is friction_discovery.ArtefactKind.DOCUMENT
            and PAGE_TYPE in types.of(artefact).counts_as
        }
    )


def check_pages(root: Path, paths: Sequence[str], *, update: bool = False) -> Report:
    """Check the contents list of each page at `paths`, relative to `root`, and with
    `update` write each stale one, once every page has been read."""
    report = Report(pages=len(paths))
    texts: dict[str, str] = {}
    for path in paths:
        try:
            texts[path] = (root / path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise CannotRun(f"the page {path} cannot be read: {exc}") from exc
    written: dict[str, str] = {}
    for path, text in texts.items():
        found = contents(text)
        if not found.held:
            continue
        if found.problem is not None:
            report.findings.append(Finding(path, found.problem_line, found.problem))
            continue
        report.lists += 1
        if found.fresh:
            continue
        assert found.opening is not None
        diff = difflib.unified_diff(
            found.written, found.expected, "the page", "its headings", lineterm="", n=1
        )
        report.findings.append(
            Finding(
                path,
                found.opening + 1,
                f"the contents list is stale: `{UPDATE}` writes it",
                tuple(f"  {row}" for row in diff),
                rewritable=True,
            )
        )
        if update:
            written[path] = updated(text, found)
    for path, text in written.items():
        (root / path).write_text(text, encoding="utf-8")
        report.updated.append(path)
    return report


def render(report: Report) -> str:
    """The run's findings, each at its page's line, then what it updated and a summary."""
    if not report.lists and not report.findings:
        return f"No contents list in {report.pages} page(s).\n"
    findings = sorted(report.findings, key=lambda finding: (finding.path, finding.line))
    out = [finding.render() for finding in findings]
    out.extend(f"updated {path}: its contents list is written" for path in report.updated)
    out.append(
        f"{report.lists} contents list(s) in {report.pages} page(s): "
        f"{len(report.findings) or 'no'} finding(s)"
    )
    return "\n".join(out) + "\n"


def exit_status(report: Report, *, update: bool) -> int:
    """0 when nothing failed, or when `--update` wrote every stale list; 1 otherwise."""
    if update:
        return 1 if any(not finding.rewritable for finding in report.findings) else 0
    return 1 if report.findings else 0


def main(argv: Sequence[str] | None = None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(
        prog="page_contents.py",
        description="Write and check the contents list of project-kit's pages.",
    )
    parser.add_argument("pages", nargs="*", metavar="PAGE", help="check only these pages")
    parser.add_argument(
        "--update", action="store_true", help="write each stale contents list into its page"
    )
    args = parser.parse_args(argv)
    try:
        every = pages(root)
        named = [Path(page).as_posix() for page in args.pages]
        unknown = [page for page in named if page not in every]
        if unknown:
            raise CannotRun(f"no artefact typed {PAGE_TYPE}: {', '.join(unknown)}")
        report = check_pages(root, named or every, update=args.update)
    except CannotRun as exc:
        print(f"page contents: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(render(report))
    return exit_status(report, update=args.update)


if __name__ == "__main__":
    sys.exit(main())
