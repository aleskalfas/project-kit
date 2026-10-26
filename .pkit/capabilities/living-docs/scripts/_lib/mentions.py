"""What a page mentions and does not anchor (DEC-001 point 6; RS-LDOC-001).

Only what a page anchors grounds a statement (RS-LDOC-001), and a change flags a
page only through its anchors (COR-050 point 5). A page that names a file, a
record, a rule or a command and anchors nothing of it is never asked when that
thing changes. This module reads what a page mentions and which of its mentions
the page's anchors stand on. Validation reports each one they do not, with an
anchor that would cover it, and never fails on one: a name that gives none of
the named thing's facts states nothing that rests on it (DEC-001 point 3). The
page may mark such a mention in its text, with the reason, and the report
passes that mention over.

**What a mention is.** A thing the page could anchor whose name has a form the
methodology fixes, so a check finds it without guessing. It is read from the
page's body below its front matter, outside fenced code, HTML comments and
strikethrough (`formats.prose`):

- **A path**: the text of an inline code span that holds a `/` and no white
  space, or the target of a link, naming a file the repository holds. A code
  span is read from the repository's root, and failing that from the page's
  folder; a link from the page's folder, or from the root where it opens with
  `/`. A span that holds a placeholder (`<name>`), braces, a glob or an ellipsis
  names no path, and nor does a URL, a folder or an image. A link's fragment
  names a section of the file.
- **A record**: a decision record's id, with the points written after it (`#5`,
  `point 5`, `points 2 and 5`). The ids are `COR-NNN`, `PRJ-NNN` and `ADR-NNN`, a
  capability's decision as `<capability>:DEC-NNN` with its slug or without, as
  `<capability> DEC-NNN` where the capability is installed, and as a bare
  `DEC-NNN` on a page in that capability's folder. A link to a record's file
  mentions the record.
- **A rule**: a rule's id, `RS-<SET>-NNN`, bare or after its component and a
  colon.
- **A command**: an inline code span that opens with `pkit` and a word, after
  `uv run` where it is written. Its words run to the first that is not a word of
  lowercase letters, digits and hyphens. The command is a capability's where its
  first word is an installed capability's name or alias, and the backbone's
  otherwise.

A record is mentioned only where the backbone's resolver of records resolves it
(`pkit refs lookup --json`, its first path where `resolved` is true), and a rule
only where the backbone's discovery reads it among the artefacts (`artefacts`).
A page's own file is no mention.

**What stands on each**, among the page's anchors as the backbone resolves them
in `pkit friction artefacts --json` (`artefacts`): the files each path anchor
stands on, its `path_anchors`, and each part an anchor names, its
`part_anchors`. A file is anchored whole by a path anchor standing on it, an
artefact anchor on the whole document, or a record anchor on the whole record
whose file it is; a part by an anchor on a section, the lead, a point or a rule.
A finding names an artefact anchor for a document of the places, and a path
anchor for any other file, such as the CLI reference in most projects.

- A path is covered by an anchor on its file, or, where a link names a section,
  on the whole file or that section.
- A record is covered by an anchor on the whole record, or on each point the
  mention names. A mention that names no point is covered by an anchor on any
  part of the record.
- A rule is covered by an anchor on the rule, or on its rule set's whole file.
- A command is covered by an anchor on what implements it, or on what documents
  it: the whole file, or the section that names it. A capability's command is
  implemented by the script its package metadata registers. Its section is the
  heading whose code span opens with the most of the command's words: in the
  CLI reference for a backbone command, in its capability's README for a
  capability's, where the span may leave out `pkit` and the capability's name or
  alias, and in any page where the span opens with `pkit`. Where no
  heading names it, a section the page anchors whose text names it covers it. On
  the page that documents it only the script does, and where no script is known
  it is no mention there.

**A mark.** An HTML comment `<!-- unanchored: <reason> -->` written after a
mention, on its line, passes over the mention it follows: the last name before
it there, after any earlier comment, written in one of the forms above. It marks
that one passage, so a later passage that rests on the same thing is still
read. A mark passes nothing over, and is reported, where it follows no mention:
where no such name comes before it, or the name is no mention, such as a path to
no file, an id nothing resolves or the page's own file. So does a mark that
follows a mention the page's anchors cover, or that gives no reason. A mark never
falls back to an earlier mention, so one left behind when what it named was
renamed or removed is reported, never moved.
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote

from _lib import formats
from _lib.artefacts import Artefact
from _lib.declarations import CAPABILITIES_DIR, load_yaml, mapping, normalise

#: The shared method's rule on grounding, which the report serves (DEC-001 point 6).
GROUNDING_RULE = "RS-LDOC-001"

PATH, RECORD, RULE, COMMAND = "path", "record", "rule", "command"

#: The backbone's reference of its commands.
CLI_REFERENCE = ".pkit/cli/README.md"

#: The backbone's reading command that resolves a record's or a rule's id to its file.
LOOKUP = ("pkit", "refs", "lookup", "--json")
LOOKUP_VERSION = 1

#: How a mark is written: an HTML comment opening with this word and a colon.
MARK_WORD = "unanchored"

_CAPABILITY = r"[a-z][a-z0-9-]*[a-z0-9]"
_POINT = r"[0-9]+[a-z]?"
_POINTS = re.compile(
    rf"^\]?(?:#(?P<hash>{_POINT})|,?[ \t]+points?[ \t]+"
    rf"(?P<list>{_POINT}(?:(?:[ \t]*,[ \t]*|,?[ \t]+and[ \t]+){_POINT})*))(?![\w-])"
)
_RECORD = re.compile(
    rf"(?<![\w:/.-])(?:"
    rf"(?P<qualified>{_CAPABILITY}):(?P<qdec>DEC-[0-9]{{3,}})(?:-[a-z0-9]+)*"
    rf"|(?P<named>{_CAPABILITY})[ \t]+(?P<ndec>DEC-[0-9]{{3,}})"
    rf"|(?P<core>(?:COR|PRJ|ADR)-[0-9]{{3,}})"
    rf"|(?P<bare>DEC-[0-9]{{3,}})"
    rf")(?![\w])"
)
_RULE = re.compile(
    rf"(?<![\w/.-])(?:(?P<component>{_CAPABILITY}):)?"
    rf"(?P<rule>RS-[A-Z][A-Z0-9]*-(?:[0-9]{{3}}|[1-9][0-9]{{3,}}))(?![\w-])"
)
_RECORD_FILE = re.compile(r"^((?:COR|PRJ|ADR)-[0-9]{3,})(?:-[^/]*)?\.md$")
_DECISION_FILE = re.compile(
    rf"^{re.escape(CAPABILITIES_DIR)}/({_CAPABILITY})/decisions/(DEC-[0-9]{{3,}})(?:-[^/]*)?\.md$"
)
_CODE = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")
_LINK = re.compile(r"(!?)\[([^\]]*)\]\(\s*<?([^)\s>]*)>?(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)")
_COMMENT = re.compile(r"<!--(.*?)-->")
_MARK = re.compile(rf"^\s*{MARK_WORD}\b\s*(?::(?P<reason>.*))?$", re.DOTALL)
_STRUCK = re.compile(r"~~[^~\n]+~~")
_NOT_A_PATH = re.compile(r"[<>{}*?\[\]\s]|\.\.\.|^[a-z][a-z0-9+.-]*://|^mailto:")
_LINE_SUFFIX = re.compile(r":[0-9]+(?::[0-9]+)?$")
_WORD = re.compile(r"^[a-z][a-z0-9-]*$")


class Unreadable(Exception):
    """The backbone gave no answer to read: the records cannot be resolved."""


@dataclass(frozen=True)
class Mention:
    """One passage of a page that mentions a thing: its kind, how the report names
    it, its line and where on the line it starts.

    `file` is the file it resolves to; `section` a link's fragment; `record` the
    record's or the rule's id as written for the backbone to resolve; `points` a
    record's points; `words` a command's words after `pkit`. `mark` is the reason
    a mark after it gives, `""` for a mark that gives none, `None` for no mark."""

    kind: str
    name: str
    line: int
    start: int = 0
    file: str | None = None
    section: str | None = None
    record: str | None = None
    points: tuple[str, ...] = ()
    words: tuple[str, ...] = ()
    mark: str | None = None


@dataclass(frozen=True)
class Unanchored:
    """A mention the page's anchors do not cover: the page, the line, the mention as
    named, and an anchor that would cover it, as a writer reads it."""

    page: str
    line: int
    kind: str
    name: str
    grounding: str


@dataclass(frozen=True)
class Idle:
    """A mark that passes nothing over: the page, its line and why."""

    page: str
    line: int
    why: str


@dataclass
class Report:
    """What the report found over the pages it read."""

    pages: int = 0
    mentions: int = 0
    unanchored: list[Unanchored] = field(default_factory=list)
    marked: int = 0
    idle: list[Idle] = field(default_factory=list)


@dataclass(frozen=True)
class Command:
    """An installed capability's commands: its names, and each command's script."""

    capability: str
    names: frozenset[str]
    scripts: Mapping[str, str]


@dataclass(frozen=True)
class Documents:
    """The artefacts the places hold, as discovery reads them: each document's file, a
    document's file by its id, and each rule's file by the rule's id."""

    paths: frozenset[str] = frozenset()
    ids: Mapping[str, str] = field(default_factory=dict)
    rules: Mapping[str, str] = field(default_factory=dict)

    @classmethod
    def of(cls, artefacts: Iterable[Artefact]) -> Documents:
        listed = list(artefacts)
        documents = [a for a in listed if not a.entry]
        return cls(
            frozenset(a.path for a in documents),
            {a.id: a.path for a in documents},
            {a.id: a.path for a in listed if a.rule},
        )


Lookup = Callable[[Sequence[str]], Mapping[str, str | None]]
Runner = Callable[..., subprocess.CompletedProcess[str]]


def look_up(root: Path, run: Runner = subprocess.run) -> Lookup:
    """The backbone's resolver of records' ids, through `pkit refs lookup --json`:
    each id the file it resolves to, or `None`. Raises Unreadable when there is no
    answer to read."""

    def lookup(ids: Sequence[str]) -> Mapping[str, str | None]:
        if not ids:
            return {}
        try:
            proc = run([*LOOKUP, *ids], cwd=root, capture_output=True, text=True, check=False)
        except OSError as exc:
            raise Unreadable(f"`pkit` could not be run ({exc})") from exc
        try:
            document = json.loads(proc.stdout or "") if proc.returncode == 0 else None
        except ValueError:
            document = None
        if not isinstance(document, Mapping) or document.get("schema_version") != LOOKUP_VERSION:
            detail = (proc.stderr or "").strip().splitlines()
            raise Unreadable(
                f"`{' '.join(LOOKUP)}` exited {proc.returncode} without a document this "
                f"capability reads" + (f": {detail[-1]}" if detail else "")
            )
        found: dict[str, str | None] = {}
        for entry in document.get("lookups") or []:
            if not isinstance(entry, Mapping) or not isinstance(entry.get("id"), str):
                continue
            paths = entry.get("paths")
            first = paths[0] if isinstance(paths, list) and paths else None
            resolved = entry.get("resolved") is True and isinstance(first, str)
            found[entry["id"]] = first if resolved and isinstance(first, str) else None
        return found

    return lookup


def commands(root: Path) -> list[Command]:
    """Each capability the repository holds, with the names its commands go by — its
    own and its aliases — and the script each command runs, from its package
    metadata. Read forgivingly: what does not read registers nothing."""
    found: list[Command] = []
    folder = root / CAPABILITIES_DIR
    try:
        names = sorted(entry.name for entry in folder.iterdir() if entry.is_dir())
    except OSError:
        return found
    for name in names:
        package = mapping(load_yaml(folder / name / "package.yaml"))
        if not package:
            continue
        aliases = [a for a in package.get("aliases") or [] if isinstance(a, str)]
        scripts = {
            str(command): normalise(f"{CAPABILITIES_DIR}/{name}/{entry['script']}")
            for command, entry in mapping(package.get("commands")).items()
            if isinstance(entry, Mapping) and isinstance(entry.get("script"), str)
        }
        found.append(Command(name, frozenset([name, *aliases]), scripts))
    return found


def read(
    root: Path,
    pages: Mapping[str, Artefact | None],
    documents: Documents,
    lookup: Lookup,
    every_page: Collection[str] = (),
) -> Report:
    """The report over `pages`, each with its artefact as the backbone reads it, or
    `None` where it lists none. `documents` are the document artefacts, `lookup`
    resolves records and rules, and `every_page` is each page of the spaces, whose
    headings may document a command. A page that cannot be read is passed over.
    Raises Unreadable when the records cannot be resolved."""
    report = Report()
    installed = commands(root)
    homes = _Homes(root, {*pages, *every_page}, installed)
    read_pages: dict[str, tuple[list[Mention], list[Idle]]] = {}
    ids: set[str] = set()
    for rel in sorted(pages):
        text = _text(root, rel)
        if text is None:
            continue
        found, idle = _mentions(root, rel, text, installed)
        read_pages[rel] = (found, idle)
        ids.update(m.record for m in found if m.kind == RECORD and m.record is not None)
        artefact = pages[rel]
        if artefact is not None and artefact.anchors is not None:
            ids.update(value.split("#", 1)[0] for value in artefact.anchors.get(RECORD, ()))
    resolved = {
        id: location.split("#", 1)[0] if location is not None else None
        for id, location in lookup(sorted(ids)).items()
    }
    for rel, (found, idle) in read_pages.items():
        report.pages += 1
        report.idle.extend(idle)
        grounds = _grounds(pages[rel], resolved, documents)
        seen: set[tuple[Any, ...]] = set()
        named: set[str] = set()
        kept, dropped = _resolved(rel, found, resolved, documents.rules)
        report.idle.extend(dropped)
        for mention in kept:
            key = (mention.kind, mention.name, mention.file, mention.section, mention.points)
            if key not in seen:
                seen.add(key)
                report.mentions += 1
            unanchored = _unanchored(rel, mention, grounds, documents, installed, homes)
            if unanchored is None:
                if mention.mark is not None:
                    report.idle.append(Idle(rel, mention.line, _COVERED))
                continue
            if mention.mark:
                report.marked += 1
                continue
            if mention.mark is not None:
                report.idle.append(Idle(rel, mention.line, _NO_REASON))
            if unanchored.name not in named:
                named.add(unanchored.name)
                report.unanchored.append(unanchored)
    report.idle.sort(key=lambda idle: (idle.page, idle.line))
    return report


_FOLLOWS_NOTHING = "it follows no mention on its line"
_COVERED = "the mention it follows is one the page's anchors cover"
_NO_REASON = "it gives no reason after `unanchored:`"
#: Why a name a mark follows is no mention, by what it is written as.
_NO_FILE = "names no file the repository holds"
_UNRESOLVED = "names no {kind} the backbone resolves"
_ITSELF = "is the page's own file"


def _no_mention(mention: Mention, what: str) -> str:
    """Why a mark after `mention`, a name that is no mention, passes nothing over."""
    return f"the name it follows, `{mention.name}`, {what}"


# --- what a page mentions -----------------------------------------------------


def _mentions(
    root: Path, page: str, text: str, installed: Sequence[Command]
) -> tuple[list[Mention], list[Idle]]:
    """Every name of the page at `page` written as a mention is, in the order of its
    lines, each with the mark after it, and the marks that follow no such name. A
    record's or a rule's id is the one written, and a path the one a span or a link
    names, which `_resolved` keeps only where it is a mention."""
    found: list[Mention] = []
    idle: list[Idle] = []
    capability = _capability_of(page)
    known = {c.capability for c in installed}
    for line, raw in formats.prose(text):
        comments = list(_COMMENT.finditer(raw))
        body = _blank(_STRUCK.sub(lambda m: " " * len(m.group(0)), raw), comments)
        spans = list(_CODE.finditer(body))
        outside = _blank(body, spans)
        readable = body.replace("`", " ")
        on_line: list[Mention] = []
        for link in _LINK.finditer(outside):
            image, target = link.group(1), link.group(3)
            label = readable[link.start(2) : link.end(2)]
            if not image:
                path = _link_path(root, page, target)
                if path is not None:
                    on_line.append(_path_mention(*path, line, link.start()))
            # The link reads as its label, so a point written after it follows the id.
            readable = (
                readable[: link.start()]
                + " "
                + label
                + " " * (link.end() - link.start() - len(label) - 1)
                + readable[link.end() :]
            )
        for span in spans:
            content = span.group(2).strip()
            command = _command(content, line, span.start())
            if command is not None:
                on_line.append(command)
                continue
            path = _span_path(root, page, content)
            if path is not None:
                on_line.append(_path_mention(*path, line, span.start()))
        on_line.extend(_records(readable, line, capability, known))
        on_line.extend(_rules(readable, line))
        on_line.sort(key=lambda m: m.start)
        found.extend(_marked(page, line, on_line, comments, idle))
    return found, idle


def _blank(text: str, matches: Iterable[re.Match[str]]) -> str:
    """`text` with each match's characters made spaces, so every offset is kept."""
    for match in matches:
        text = text[: match.start()] + " " * (match.end() - match.start()) + text[match.end() :]
    return text


def _marked(
    page: str,
    line: int,
    on_line: Sequence[Mention],
    comments: Sequence[re.Match[str]],
    idle: list[Idle],
) -> list[Mention]:
    """The line's names, each mark given to the last name before it and after any
    earlier comment, whether or not that name proves a mention; a mark that follows
    none is idle."""
    marked = list(on_line)
    after = 0
    for comment in comments:
        written = _MARK.match(comment.group(1))
        if written is None:
            after = comment.end()
            continue
        reason = (written.group("reason") or "").strip()
        before = [i for i, m in enumerate(marked) if after <= m.start < comment.start()]
        if before:
            marked[before[-1]] = replace(marked[before[-1]], mark=reason)
        else:
            idle.append(Idle(page, line, _FOLLOWS_NOTHING))
        after = comment.end()
    return marked


def _capability_of(page: str) -> str | None:
    """The capability whose folder holds the page, where one does."""
    parts = PurePosixPath(page).parts
    prefix = PurePosixPath(CAPABILITIES_DIR).parts
    if len(parts) > len(prefix) + 1 and parts[: len(prefix)] == prefix:
        return parts[len(prefix)]
    return None


def _path_mention(
    written: str, file: str | None, section: str | None, line: int, start: int
) -> Mention:
    """A path, or the record whose file it is, read from the file's own name. A path
    written to no file the repository holds is a name `_resolved` drops."""
    if file is None:
        return Mention(PATH, written, line, start, section=section)
    core = _RECORD_FILE.match(PurePosixPath(file).name)
    decision = _DECISION_FILE.match(file)
    if core is not None:
        record = core.group(1)
    elif decision is not None:
        record = f"{decision.group(1)}:{decision.group(2)}"
    else:
        return Mention(PATH, file, line, start, file=file, section=section)
    return Mention(RECORD, record, line, start, file=file, record=record)


def _span_path(root: Path, page: str, text: str) -> tuple[str, str | None, str | None] | None:
    """The path a code span is written as, the file it names, read from the root and
    failing that from the page's folder, or `None` where the repository holds none,
    and the section; `None` where the span is written as no path."""
    if "/" not in text or text.endswith("/") or _NOT_A_PATH.search(text):
        return None
    target, _, section = text.partition("#")
    target = _LINE_SUFFIX.sub("", target)
    if target.startswith("/"):
        file = _held(root, target.lstrip("/"))
    else:
        file = _held(root, target) or _held(root, f"{PurePosixPath(page).parent}/{target}")
    return target, file, section or None


def _link_path(root: Path, page: str, target: str) -> tuple[str, str | None, str | None] | None:
    """The path a link's target is written as, the file it names, read from the page's
    folder, or from the root where it opens with `/`, or `None` where the repository
    holds none, and the section; `None` for a URL or a link within the page."""
    if not target or target.startswith("#") or _NOT_A_PATH.search(target.split("#")[0]):
        return None
    path, _, section = unquote(target).partition("#")
    path = path.split("?")[0]
    if not path:
        return None
    if path.startswith("/"):
        file = _held(root, path.lstrip("/"))
    else:
        file = _held(root, f"{PurePosixPath(page).parent}/{path}")
    return path, file, section or None


def _held(root: Path, path: str) -> str | None:
    """`path` as a repository-relative file the repository holds — a regular file
    inside it, never a link nor in `.git`; `None` otherwise."""
    rel = os.path.normpath(path).replace(os.sep, "/")
    if rel in (".", "..") or rel.startswith(("../", "/")):
        return None
    if rel == ".git" or rel.startswith(".git/"):
        return None
    try:
        mode = os.lstat(root / rel).st_mode
    except OSError:
        return None
    if not stat.S_ISREG(mode):
        return None
    return rel


def _command(text: str, line: int, start: int) -> Mention | None:
    """The command an inline code span names, where it opens with `pkit` and a word."""
    words = text.split()
    if words[:2] == ["uv", "run"]:
        words = words[2:]
    if not words or words[0] != "pkit":
        return None
    named = _command_words(words[1:])
    if not named:
        return None
    return Mention(COMMAND, " ".join(["pkit", *named]), line, start, words=named)


def _records(text: str, line: int, capability: str | None, known: Collection[str]) -> list[Mention]:
    """The records a line names, each with the points written after it."""
    found: list[Mention] = []
    for match in _RECORD.finditer(text):
        if match.group("qualified"):
            record = f"{match.group('qualified')}:{match.group('qdec')}"
        elif match.group("named"):
            if match.group("named") in known:
                record = f"{match.group('named')}:{match.group('ndec')}"
            elif capability is not None:
                record = f"{capability}:{match.group('ndec')}"
            else:
                continue
        elif match.group("core"):
            record = match.group("core")
        elif capability is not None:
            record = f"{capability}:{match.group('bare')}"
        else:
            continue
        points = _points(text[match.end() :])
        found.append(Mention(RECORD, record, line, match.start(), record=record, points=points))
    return found


def _rules(text: str, line: int) -> list[Mention]:
    """The rules a line names, bare or after their component."""
    found: list[Mention] = []
    for match in _RULE.finditer(text):
        written = match.group(0)
        found.append(Mention(RULE, match.group("rule"), line, match.start(), record=written))
    return found


def _points(after: str) -> tuple[str, ...]:
    """The points written right after a record's id: `#5`, `point 5`, `points 2 and 5`."""
    match = _POINTS.match(after)
    if match is None:
        return ()
    if match.group("hash"):
        return (match.group("hash"),)
    return tuple(re.findall(_POINT, match.group("list")))


def _resolved(
    page: str,
    found: Iterable[Mention],
    resolved: Mapping[str, str | None],
    rules: Mapping[str, str],
) -> tuple[list[Mention], list[Idle]]:
    """The mentions of the page at `page` among the names `found`, each record's and
    rule's with its file, as the backbone resolves it: a record through its
    resolver, a rule as its discovery reads it among the artefacts. A path to no
    file, a record or a rule it does not resolve, and the page's own file are no
    mention, and a link to a file no record resolves to is a path again. Each mark
    such a name carries passes nothing over: the second list."""
    kept: list[Mention] = []
    idle: list[Idle] = []

    def drop(mention: Mention, what: str) -> None:
        if mention.mark is not None:
            idle.append(Idle(page, mention.line, _no_mention(mention, what)))

    for mention in found:
        if mention.kind == PATH and mention.file is None:
            drop(mention, _NO_FILE)
            continue
        if mention.kind in (RECORD, RULE):
            if mention.kind == RULE:
                file = rules.get(mention.name)
            else:
                file = resolved.get(mention.record or "")
            if file is None and mention.file is None:
                drop(mention, _UNRESOLVED.format(kind=mention.kind))
                continue
            if file is None or (mention.file is not None and mention.file != file):
                mention = replace(
                    mention, kind=PATH, name=mention.file or mention.name, record=None
                )
            else:
                mention = replace(mention, file=file)
        if mention.file == page:
            drop(mention, _ITSELF)
            continue
        kept.append(mention)
    return kept, idle


# --- what stands on a mention ---------------------------------------------------


@dataclass(frozen=True)
class _Grounds:
    """What a page's anchors stand on: the files anchored whole, and each file's
    anchored parts — the sections, points and rules by name, and the lines each
    spans."""

    whole: frozenset[str]
    named: Mapping[str, frozenset[str]]
    spans: Mapping[str, tuple[tuple[int, int], ...]]

    def any_part(self, path: str) -> bool:
        return path in self.named or path in self.spans


def _grounds(
    artefact: Artefact | None, resolved: Mapping[str, str | None], documents: Documents
) -> _Grounds:
    """What the page's anchors stand on, as the backbone resolves them."""
    if artefact is None or artefact.anchors is None:
        return _Grounds(frozenset(), {}, {})
    whole: set[str] = set()
    named: dict[str, set[str]] = {}
    spans: dict[str, list[tuple[int, int]]] = {}
    for files in (artefact.standing or {}).values():
        whole.update(files)
    for value in artefact.anchors.get("artefact", ()):
        path, mark, part = value.partition("#")
        if mark and path in documents.paths:
            named.setdefault(path, set()).add(part)
        elif not mark and path in documents.paths:
            whole.add(path)
        elif not mark and value in documents.ids:
            whole.add(documents.ids[value])
    for value in artefact.anchors.get(RECORD, ()):
        record, mark, point = value.partition("#")
        location = resolved.get(record)
        if location is None:
            continue
        if mark:
            named.setdefault(location, set()).add(point)
        else:
            whole.add(location)
    for part in artefact.parts:
        if part.span is not None:
            spans.setdefault(part.path, []).append(part.span)
        if part.kind == "artefact" and "#" not in part.value:
            # An entry, such as a rule: a part of its file, named by its id.
            named.setdefault(part.path, set()).add(part.value.rsplit(":", 1)[-1])
    return _Grounds(
        frozenset(whole),
        {path: frozenset(parts) for path, parts in named.items()},
        {path: tuple(found) for path, found in spans.items()},
    )


def _unanchored(
    page: str,
    mention: Mention,
    grounds: _Grounds,
    documents: Documents,
    installed: Sequence[Command],
    homes: _Homes,
) -> Unanchored | None:
    """The mention as the report names it, where the page's anchors do not cover it;
    `None` where they do, or where nothing is known to cover it."""
    if mention.kind == PATH:
        return _unanchored_path(page, mention, grounds, documents)
    if mention.kind == RECORD:
        return _unanchored_record(page, mention, grounds)
    if mention.kind == RULE:
        return _unanchored_rule(page, mention, grounds)
    return _unanchored_command(page, mention, grounds, documents, installed, homes)


def _unanchored_path(
    page: str, mention: Mention, grounds: _Grounds, documents: Documents
) -> Unanchored | None:
    file = mention.file or mention.name
    section = mention.section
    if file in grounds.whole:
        return None
    if section is None and grounds.any_part(file):
        return None
    if section is not None and section in grounds.named.get(file, frozenset()):
        return None
    if file in documents.paths:
        value = f"{file}#{section}" if section is not None else file
        return Unanchored(page, mention.line, PATH, file, f"artefact: [{value}]")
    return Unanchored(page, mention.line, PATH, file, f"path: [{file}]")


def _unanchored_record(page: str, mention: Mention, grounds: _Grounds) -> Unanchored | None:
    file = mention.file or ""
    record = mention.record or mention.name
    if file in grounds.whole:
        return None
    if not mention.points:
        if grounds.any_part(file):
            return None
        return Unanchored(page, mention.line, RECORD, record, f"record: [{record}]")
    anchored = grounds.named.get(file, frozenset())
    missing = [point for point in mention.points if point not in anchored]
    if not missing:
        return None
    values = ", ".join(f"{record}#{point}" for point in missing)
    return Unanchored(page, mention.line, RECORD, f"{record}#{missing[0]}", f"record: [{values}]")


def _unanchored_rule(page: str, mention: Mention, grounds: _Grounds) -> Unanchored | None:
    file = mention.file or ""
    if file in grounds.whole or mention.name in grounds.named.get(file, frozenset()):
        return None
    return Unanchored(page, mention.line, RULE, mention.name, f"artefact: [{mention.name}]")


@dataclass(frozen=True)
class _Home:
    """A heading that names a command: its file, its line, its text, the command words
    one of its code spans names, and the capability whose command it is, or `None`
    for the backbone's."""

    path: str
    line: int
    text: str
    words: tuple[str, ...]
    capability: str | None


class _Homes:
    """Where the commands are documented: each heading that names one, read once.

    The CLI reference's headings name backbone commands, and a capability's README's
    name its own, each with `pkit` and, in the README, the capability's name or alias
    left to the reader. Any other page's heading names a command only where its code
    span opens with `pkit`. The CLI reference and the capabilities' READMEs come
    first."""

    def __init__(self, root: Path, pages: Collection[str], installed: Sequence[Command]) -> None:
        self.root = root
        self.installed = installed
        self.pages = sorted(pages)
        self._homes: list[_Home] | None = None
        self._lines: dict[str, tuple[str, ...] | None] = {}

    def reference(self, owner: Command | None) -> str:
        """The file that documents the owner's commands."""
        if owner is None:
            return CLI_REFERENCE
        return f"{CAPABILITIES_DIR}/{owner.capability}/README.md"

    def naming(self, owner: Command | None, words: Sequence[str]) -> _Home | None:
        """The heading that names the command: the one whose code span opens with the
        most of its words, the first of equals."""
        capability = owner.capability if owner is not None else None
        best: _Home | None = None
        for home in self._read():
            if home.capability != capability or tuple(words[: len(home.words)]) != home.words:
                continue
            if best is None or len(home.words) > len(best.words):
                best = home
        return best

    def lines(self, path: str) -> tuple[str, ...] | None:
        """The lines of the file at `path`, read once; `None` where it cannot be read."""
        if path not in self._lines:
            text = _text(self.root, path)
            self._lines[path] = None if text is None else tuple(_lines(text))
        return self._lines[path]

    def names(
        self, path: str, span: tuple[int, int], owner: Command | None, words: Sequence[str]
    ) -> bool:
        """Whether the lines `span` covers in the file at `path` hold a code span that
        names the command, read as a heading of that file is."""
        lines = self.lines(path)
        if lines is None:
            return False
        text = "\n".join(lines[span[0] - 1 : span[1]])
        capability = owner.capability if owner is not None else None
        return any(
            named_by == capability and tuple(words[: len(named)]) == named
            for named_by, named in self._spans(path, text)
        )

    def _read(self) -> list[_Home]:
        if self._homes is None:
            found: list[_Home] = []
            files = [self.reference(owner) for owner in [None, *self.installed]]
            for path in [*files, *(p for p in self.pages if p not in files)]:
                text = _text(self.root, path)
                if text is None:
                    continue
                for heading in formats.headings(text):
                    found.extend(
                        _Home(path, heading.line, heading.text, named, capability)
                        for capability, named in self._spans(path, heading.text)
                    )
            self._homes = found
        return self._homes

    def _spans(self, path: str, text: str) -> list[tuple[str | None, tuple[str, ...]]]:
        """Each code span of `text` that names a command, read as the file at `path`
        names one: the capability whose command it is, or `None`, and its words."""
        own = next((c for c in self.installed if self.reference(c) == path), None)
        found: list[tuple[str | None, tuple[str, ...]]] = []
        for span in _CODE.finditer(text):
            words = span.group(2).split()
            prefixed = words[:1] == ["pkit"]
            if prefixed:
                words = words[1:]
            owner = next((c for c in self.installed if words[:1] and words[0] in c.names), None)
            if owner is not None and (prefixed or owner is own):
                words = words[1:]
            elif own is not None and not prefixed:
                owner = own
            elif not prefixed and path == CLI_REFERENCE:
                # The reference's own headings name backbone commands alone.
                owner = None
            elif not prefixed:
                continue
            named = _command_words(words)
            if named:
                found.append((owner.capability if owner is not None else None, named))
        return found


def _unanchored_command(
    page: str,
    mention: Mention,
    grounds: _Grounds,
    documents: Documents,
    installed: Sequence[Command],
    homes: _Homes,
) -> Unanchored | None:
    """A command is covered by an anchor on the script that implements it, or on the
    section that documents it, or on the whole of that section's file. Where no
    heading names it, a section the page anchors whose text names it covers it. On
    the page that documents it only the script does."""
    words = mention.words
    owner = next((c for c in installed if words[0] in c.names), None)
    named = words[1:] if owner is not None else words
    script = owner.scripts.get(named[0]) if owner is not None and named else None
    if script is not None and script in grounds.whole:
        return None
    reference = homes.reference(owner)
    home = homes.naming(owner, named)
    name = mention.name
    if home is not None:
        name = " ".join(["pkit", *words[: len(words) - len(named) + len(home.words)]])
    if page == reference or (home is not None and home.path == page):
        if script is None:
            return None
        return Unanchored(page, mention.line, COMMAND, name, f"path: [{script}]")
    if home is not None:
        if home.path in grounds.whole:
            return None
        if any(first == home.line for first, _last in grounds.spans.get(home.path, ())):
            return None
        where, file = f"its section headed `{home.text}`", home.path
    else:
        if reference in grounds.whole:
            return None
        if any(
            homes.names(path, span, owner, named)
            for path, spans in grounds.spans.items()
            for span in spans
        ):
            return None
        if homes.lines(reference) is None:
            if script is None:
                return None
            return Unanchored(page, mention.line, COMMAND, name, f"path: [{script}]")
        where, file = "the section that documents it", reference
    if file in documents.paths:
        grounding = f"artefact: [{file}#<slug>], on {where}"
    elif home is not None:
        grounding = f"path: [{file}], which documents it in {where}"
    else:
        grounding = f"path: [{file}], which documents it"
    if script is not None:
        grounding += f", or path: [{script}]"
    return Unanchored(page, mention.line, COMMAND, name, grounding)


def _command_words(words: Sequence[str]) -> tuple[str, ...]:
    """A command's words: the leading words of lowercase letters, digits and hyphens."""
    named: list[str] = []
    for word in words:
        if not _WORD.match(word):
            break
        named.append(word)
    return tuple(named)


def _text(root: Path, path: str) -> str | None:
    """The text of a file the repository holds, or `None`."""
    if _held(root, path) is None:
        return None
    try:
        return (root / path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _lines(text: str) -> list[str]:
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
