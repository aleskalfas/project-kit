"""Stamping the analysis artefacts (DEC-001 points 2 to 4).

A stamp writes one artefact from its kind's template in `templates/`, where
the capability's places put it under the analysis location:

- a **use case** or a **journey** is a new file, `UC-NNN-<slug>.md` or
  `JRN-NNN-<slug>.md`, numbered with the next free number — one past the
  highest the working tree and the default branch hold, withdrawn ones
  included, and past every number the default branch's history ever gave a
  file of its place, deleted since or not, since a number is never used
  again; a note names the file when the history's number is the one it
  follows. A file's number is read from its front matter and from its name,
  so a file whose id cannot be read still holds its number. Numbers two
  branches take in parallel are `pkit analysis check-numbers`' to report
  (point 3);
- an **actor** or a **term** is a new entry, `ACT-<slug>` or `TERM-<slug>`, of
  its collection file — added to its front matter, and its section to the
  body, each where its id sorts, every other byte left as it was — the file
  created from the template the first time.

It writes the anchors DEC-001 point 4 asks for: a use case's actor, and a
journey's use cases from its steps, beside the paths and records it is given.
An actor or a term nothing embodies is stamped with the reason instead, its
`unanchored-because` (point 9), written in its friction block: the key is the
core's, which the unanchored measure reads (COR-050 points 1 and 8). A
revalidation record is not an artefact and
is stamped by `_lib/revalidation.py`.
What only a person can write the stamp leaves as the template's placeholders —
an actor's need, a term's definition, a body's goal and steps — which the
check fails until each is filled; a title, a name or a reason given to it
still holding one the templates or the skill's commands shipped it refuses
(`_lib/placeholder.py`).
While the analysis location is not recorded yet, the stamp records it through
the backbone (COR-049 point 5) once the artefact is written — so a write that
fails leaves the recorded locations untouched, and a recording that fails puts
the file back as it was: a refused stamp writes nothing (`write_and_record`); a
stamp that needs no recording never runs it. A path reached through a link is
refused: the discovery never reads one. Every file is written whole, to a
temporary file beside it then moved over it, keeping its mode; a
collection file keeps every byte but the entry and section it gains, its line
endings too: one whose every line ends CRLF, as a checkout with
`core.autocrlf` writes it, is edited as LF and written back CRLF, and one
with mixed line endings is refused. Where the analysis is, and what it holds, is
read through the backbone's discovery — the working tree's and the default
branch's tip — never by walking the places. The default branch's history is
read for a use case or journey alone, as the tree is (`_lib/history.py`): one
`git log` of the paths ever added under the kind's place, each number read
from the file's name, counted when the discovery at the commit that added it
held it as a file of the place, not excluded — asked only of a number past
the tree's and the tip's. A shallow clone's history stops early, and the
stamp says so.
"""

from __future__ import annotations

import contextlib
import io
import os
import re
import stat
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from _lib import backbone, history, markdown, schemas
from _lib.model import (
    ACTOR,
    COLLECTIONS,
    CONTAINER,
    JOURNEY,
    NOUN,
    NUMBERED,
    PREFIX,
    TERM,
    UNANCHORED_BECAUSE,
    USE_CASE,
    Analysis,
    Unreadable,
    identity,
    number_of,
    with_article,
)
from _lib.placeholder import left_in

#: Each kind's template, in the capability's own tree.
TEMPLATES = Path(__file__).resolve().parents[2] / "templates"
TEMPLATE_OF = {
    USE_CASE: "use-case.md",
    JOURNEY: "journey.md",
    ACTOR: "actors.md",
    TERM: "glossary.md",
}

#: The placeholder a document template's title is written as.
TITLE = "<Title>"

#: A journey template's step and seam lines, rewritten from the steps.
_STEP_LINE = re.compile(r"^\d+\. UC-\d+ — (?P<rest>.*)$")
_SEAM_LINE = re.compile(r"^- \*\*UC-\d+ → UC-\d+:\*\* (?P<rest>.*)$")

#: A collection entry's section heading, `## <id> — <name>`.
_SECTION = re.compile(r"^## (?P<id>\S+)")


class Refused(Exception):
    """The stamp cannot be made; the message says why and what to do."""


@dataclass(frozen=True)
class Request:
    """What to stamp: a kind and a slug, the title or name, and what it rests on."""

    kind: str
    slug: str
    title: str | None = None  # a document's title, or an entry's name
    actor: str | None = None
    steps: tuple[str, ...] = ()
    area: str | None = None
    paths: tuple[str, ...] = ()
    records: tuple[str, ...] = ()
    unanchored_because: str | None = None  # an actor's or a term's reason for no anchors


@dataclass(frozen=True)
class Stamped:
    """What was written: the new id, where, and what else the stamp has to say."""

    id: str
    location: str  # the file, or `file#id` for an entry
    notes: tuple[str, ...]


Recorder = Callable[[Path], str | None]


def stamp(
    root: Path, request: Request, base: str, *, record: Recorder = backbone.record_location
) -> Stamped:
    """Stamp `request` in the project at `root`, numbering against the default branch `base`."""
    try:
        analysis = backbone.read_analysis(root)
    except Unreadable as exc:
        raise Refused(f"the analysis could not be read: {exc}") from exc
    kind = request.kind
    place = analysis.places.get(kind)
    if place is None:
        raise Refused(
            "the backbone's reading holds no place of software-analysis for "
            f"{NOUN[kind]}s; `pkit validate` says why"
        )
    _check_words(request)
    _check_placeholders(request)
    _check_unanchored(request)
    _check_references(analysis, request)

    notes: list[str] = []
    held, past = _held(root, analysis, kind, base, notes)
    new_id = _new_id(kind, request.slug, held, base)
    if past is not None:
        notes.append(
            f"{new_id} follows {past.id}, the number {base}'s history gave {past.path} (commit "
            f"{past.commit[: backbone.SHORT]}), which neither {base} nor the working tree holds "
            f"now: a number is never used again (DEC-001 point 3)"
        )

    if kind in COLLECTIONS:
        target = root / place
        refuse_links(root, target, place)
        text = _added_entry(target, place, kind, new_id, request)
        location = f"{place}#{new_id}"
    else:
        folder = f"{place}/{request.area}" if request.area else place
        location = f"{folder}/{new_id}-{request.slug}.md"
        target = root / location
        refuse_links(root, target, location)
        if target.exists():
            raise Refused(f"{location} exists already")
        text = _document(kind, new_id, request)

    recorded = write_and_record(root, target, location, text, record)
    if recorded:
        notes.insert(0, recorded)
    return Stamped(id=new_id, location=location, notes=tuple(notes))


def write_and_record(
    root: Path, target: Path, location: str, text: str, record: Recorder
) -> str | None:
    """Write `text` to `target` whole, then — when it is not recorded yet — record the
    analysis location (COR-049 point 5), returning the line the recording printed. A
    write that fails is refused before anything is recorded; a recording that fails
    puts `target`, and any folder made for it, back as they were: a refused stamp
    leaves nothing written. A stamp that needs no recording never runs it, so never
    fails on one. A path reached through a link is refused (`refuse_links`)."""
    refuse_links(root, target, location)
    recording = not backbone.location_recorded(root)
    before = target.read_bytes() if target.is_file() else None
    made = [folder for folder in (target.parent, *target.parent.parents) if not folder.exists()]
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        write_whole(target, text.encode("utf-8"))
    except OSError as exc:
        _put_back(target, before, made)
        raise Refused(f"{location} could not be written: {exc}") from exc
    if not recording:
        return None
    try:
        return record(root)
    except Unreadable as exc:
        _put_back(target, before, made)
        raise Refused(
            f"the analysis location could not be recorded: {exc}; {location} was not written"
        ) from exc


def refuse_links(root: Path, target: Path, location: str) -> None:
    """Refuse `target` when it, or a folder between it and `root`, is a link. The core's
    discovery never reads a link as a document, nor anything beneath a linked folder,
    so what the stamp wrote through one would be no part of the analysis — and a file
    written whole would replace the link it was reached by."""
    for path in (target, *target.parents):
        if path == root:
            return
        if path.is_symlink():
            raise Refused(
                f"{location} is reached through the link {path.relative_to(root).as_posix()}: "
                f"the core's discovery never reads a link as a document, nor anything beneath "
                f"a linked folder, so what the stamp wrote there would be no part of the "
                f"analysis — put the file or folder itself in the link's place, then stamp again"
            )


def write_whole(target: Path, data: bytes) -> None:
    """Write `data` to `target` whole or not at all: to a temporary file beside it, then
    moved over it, so a failure halfway never leaves it half-written. A file keeps its
    mode; a new one takes what the umask gives, as any file written here does."""
    mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else 0o666 & ~_umask()
    handle, temporary = tempfile.mkstemp(
        dir=target.parent, prefix=f".{target.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, target)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporary)
        raise


def _put_back(target: Path, before: bytes | None, made: Sequence[Path]) -> None:
    """`target` as it was — its bytes, or no file — and the folders made for it gone."""
    with contextlib.suppress(OSError):
        if before is not None:
            write_whole(target, before)
        elif target.is_file():
            target.unlink()
        for folder in made:  # the deepest first
            folder.rmdir()


def _umask() -> int:
    mask = os.umask(0)
    os.umask(mask)
    return mask


# --- what the request names ------------------------------------------------------------------


def _check_words(request: Request) -> None:
    slug = schemas.slug_pattern()
    if not slug.match(request.slug):
        raise Refused(
            f"the slug {request.slug!r} is not a word: a lowercase letter, then lowercase "
            f"letters, digits and hyphens"
        )
    if request.area is not None and not slug.match(request.area):
        raise Refused(f"the area {request.area!r} is not a word, as a slug is")


def _check_placeholders(request: Request) -> None:
    """The words given are the person's: one still holding a placeholder the templates
    or the skill's commands shipped is refused — matched exactly, as the check matches
    an artefact's fields (`_lib/placeholder.py`), so words of the person's own in angle
    brackets are theirs to write."""
    flag = "--name" if request.kind in COLLECTIONS else "--title"
    for option, text in (
        (flag, request.title),
        ("--unanchored-because", request.unanchored_because),
    ):
        held = left_in(text or "")
        if held:
            raise Refused(
                f"{option} still holds the placeholder {held[0]!r}: write in its place what "
                f"it asks for"
            )


def _check_unanchored(request: Request) -> None:
    """Only an actor or a term is kept unanchored with its reason, and never one
    given anchors: the reason says why it has none (DEC-001 points 4 and 9). A use
    case always anchors to its actor and a journey to its steps' use cases (point
    4), so neither is ever unanchored, and point 9's reason never applies to them."""
    if request.unanchored_because is None:
        return
    if request.kind not in COLLECTIONS:
        rests_on = "its actor" if request.kind == USE_CASE else "the use cases of its steps"
        raise Refused(
            f"{with_article(request.kind)} anchors to {rests_on}, so it is never unanchored"
        )
    if not request.unanchored_because.strip():
        raise Refused("--unanchored-because gives the reason it has no anchors: write it")
    if request.paths or request.records:
        raise Refused(
            f"{with_article(request.kind)} with anchors is not unanchored: give its anchors "
            f"(--path, --record) or the reason it has none (--unanchored-because), not both"
        )


def _check_references(analysis: Analysis, request: Request) -> None:
    """A use case's and a journey's actor, and a journey's steps, are artefacts in force:
    what it stamps is in force, and the check holds it to the same rule
    (`Analysis.unfit`)."""
    if request.kind in NUMBERED:
        if request.actor is None:
            raise Refused(f"{with_article(request.kind)} is one actor's: name it with --actor")
        _in_force(analysis, request.actor, ACTOR)
    if request.kind == JOURNEY:
        if len(request.steps) < 2:
            raise Refused(
                "a journey passes through several use cases: name them in order, "
                "--step <UC-id> --step <UC-id> …"
            )
        for step in request.steps:
            _in_force(analysis, step, USE_CASE)


def _in_force(analysis: Analysis, artefact_id: str, kind: str) -> None:
    problem = analysis.unfit(artefact_id, kind, in_force=True)
    if problem is None:
        return
    if analysis.of(artefact_id, kind) is None:
        problem += f": stamp it first, `pkit analysis new {kind} <slug>`"
    raise Refused(problem)


# --- the id ----------------------------------------------------------------------------------


def _held(
    root: Path, analysis: Analysis, kind: str, base: str, notes: list[str]
) -> tuple[set[str], history.Given | None]:
    """Every id held, as `identity` spells it — in the working tree, and at the default
    branch's tip, a file's number read from its name too (`Analysis.held`) — and, for
    a use case or journey, the number of its kind past all of them that the default
    branch's history gave a file gone since, which counts as held too (DEC-001 point
    3; `_lib/history.py`). An actor's or term's id is a slug a person chooses, and a
    withdrawn one stays in its collection file, so no history is read for one.
    Without the default branch, the working tree's alone, with a note saying why."""
    held = analysis.held()
    tip = backbone.commit_of(root, base)
    if tip is None:
        notes.append(
            f"{base} names no commit here, so ids were taken from the working tree alone; "
            f"`pkit analysis check-numbers` compares them once it resolves"
        )
        return held, None
    try:
        on_base = backbone.read_analysis(root, at=tip)
    except Unreadable as exc:
        notes.append(f"{base} could not be read ({exc}); ids were taken from the working tree")
        return held, None
    held |= on_base.held()
    if kind not in NUMBERED:
        return held, None
    if backbone.is_shallow(root):
        notes.append(
            f"history: shallow clone — {base}'s history was read back to where the clone "
            f"stops, so a number a file was given before it is not counted; fetch the full "
            f"history (`git fetch --unshallow`) to count every one"
        )
    folders = {state.places[kind] for state in (analysis, on_base) if kind in state.places}
    top = max(_numbers(kind, held), default=0)
    judge = history.Judge(root, (analysis, on_base))
    past = history.highest(judge, history.given(root, tip, folders), kind, above=top)
    if past is not None:
        held.add(past.id)
    return held, past


def _numbers(kind: str, held: set[str]) -> list[int]:
    """The numbers of `kind` among ids spelt as `identity` spells them."""
    pattern = schemas.id_pattern(kind)
    return [number_of(i) for i in held if pattern.match(i)]


def _new_id(kind: str, slug: str, held: set[str], base: str) -> str:
    """The next free number for a use case or journey; `<PREFIX>-<slug>` for the rest,
    refused when the working tree or the default branch holds it already. Ids are
    compared by what they stand for (`identity`), as the check compares them: a
    number spelt `UC-0007` is held as `UC-007` is."""
    if kind in NUMBERED:
        return identity(f"{PREFIX[kind]}-{max(_numbers(kind, held), default=0) + 1}")
    new_id = f"{PREFIX[kind]}-{slug}"
    if new_id in held:
        raise Refused(
            f"{new_id} is held already, in the working tree or on {base}; an id is never used "
            f"again, withdrawn or not — choose another slug"
        )
    return new_id


# --- rendering -------------------------------------------------------------------------------


def _document(kind: str, new_id: str, request: Request) -> str:
    """A use case's or a journey's file, from its template."""
    front, body = _template(kind)
    data = dict(markdown.load(front))
    template_id = str(data["id"])
    data["id"] = new_id
    data["title"] = _title(request)
    data["actor"] = request.actor
    if kind == JOURNEY:
        data["steps"] = list(request.steps)
        anchored = list(dict.fromkeys(request.steps))
    else:
        anchored = [str(request.actor)]
    data[CONTAINER] = _container(request, anchored)
    body = body.replace(template_id, new_id).replace(TITLE, _title(request))
    if kind == JOURNEY:
        body = _journey_body(body, request.steps)
    return f"---\n{dump(data)}---\n\n{body}"


def _journey_body(body: str, steps: Sequence[str]) -> str:
    """The template's step and seam lines, one per step and one per pair of steps."""

    def rewrite(lines: list[str], pattern: re.Pattern[str], make: Callable[[str], list[str]]):
        out: list[str] = []
        done = False
        for line in lines:
            match = pattern.match(line)
            if match is None:
                out.append(line)
            elif not done:
                out += make(match["rest"])
                done = True
        return out

    lines = body.split("\n")
    lines = rewrite(
        lines, _STEP_LINE, lambda rest: [f"{n}. {s} — {rest}" for n, s in enumerate(steps, 1)]
    )
    lines = rewrite(
        lines,
        _SEAM_LINE,
        lambda rest: [f"- **{a} → {b}:** {rest}" for a, b in pairwise(steps)],
    )
    return "\n".join(lines)


def _added_entry(target: Path, place: str, kind: str, new_id: str, request: Request) -> str:
    """The collection file `place` with the new entry: its front matter gains the
    entry and its body the entry's section, each where the id sorts among those
    already there, every other byte as it was; the file from the template when it
    is new. Sorted rather than appended, so two lines of work adding different
    entries write to different places of the file and merge cleanly unless their
    ids are neighbours — as the core keeps deferrals sorted (COR-050 point 4)."""
    front, body = _template(kind)
    ((template_id, example),) = dict(markdown.load(front)).items()
    name = _title(request)
    entry = {key: value for key, value in example.items() if key != CONTAINER}
    entry["name"] = name
    entry[CONTAINER] = _container(request, [])
    heading = body.find(f"## {template_id}")
    preamble, section = body[:heading], body[heading:]
    section = section.replace(template_id, new_id).replace(str(example["name"]), name)
    added = dump({new_id: entry})
    if not target.exists():
        return f"---\n{added}---\n\n{preamble}{section}"

    try:
        written = target.read_bytes().decode("utf-8")  # as written: no line ending translated
    except (OSError, UnicodeDecodeError) as exc:
        raise Refused(f"{place} could not be read: {exc}") from exc
    crlf = _crlf(written, place)
    text = written.replace("\r\n", "\n") if crlf else written
    updated = _inserted(text, place, kind, new_id, added, section)
    return updated.replace("\n", "\r\n") if crlf else updated


def _crlf(text: str, place: str) -> bool:
    """Whether every line of `text` ends CRLF, as a checkout with `core.autocrlf` writes
    one — the stamp then edits it as LF and writes it back as CRLF, so every byte but
    the entry's and the section's is kept; `False` for LF. Mixed line endings are
    refused: which ending the new lines take cannot be told."""
    if "\r" not in text:
        return False
    if text.count("\r\n") == text.count("\n") == text.count("\r"):
        return True
    raise Refused(
        f"{place} has mixed line endings — some lines end CRLF, others LF or a lone CR: the "
        f"stamp writes its lines with the file's own ending, and this file has no one ending "
        f"— make them one, then stamp again"
    )


def _inserted(text: str, place: str, kind: str, new_id: str, added: str, section: str) -> str:
    """The LF collection file `text` with the entry `added` in its front matter and its
    `section` in its body, each where `new_id` sorts; refused when it is no collection
    file, holds `new_id` already, or would not read back as it is plus the entry."""
    span = markdown.front_matter_span(text)
    if span is None:
        raise Refused(f"{place} has no front matter: it is not a collection file")
    start, end = span
    try:
        existing = markdown.load(text[start:end])
        lines = markdown.key_lines(text[start:end])
    except YAMLError as exc:
        raise Refused(f"{place}'s front matter does not parse; fix it first") from exc
    if not isinstance(existing, Mapping):
        raise Refused(f"{place}'s front matter is not a mapping of entries by id")
    if new_id in existing:
        raise Refused(f"{new_id} is held already, in {place}")
    entry_at = _entry_at(text, start, end, lines, new_id)
    closing = text.find("\n", end)
    section_at = None if closing == -1 else _section_at(text, closing + 1, kind, new_id)
    if section_at is None:
        updated = _after(text[:entry_at] + added + text[entry_at:], section)
    else:
        updated = (
            text[:entry_at]
            + added
            + text[entry_at:section_at]
            + section.rstrip("\n")
            + "\n\n"
            + text[section_at:]
        )
    new_span = markdown.front_matter_span(updated)
    assert new_span is not None
    wanted = {**existing, new_id: markdown.load(added)[new_id]}
    if markdown.load(updated[new_span[0] : new_span[1]]) != wanted:
        raise Refused(
            f"{place}'s front matter would not read back as it is plus {new_id}; "
            f"add the entry by hand"
        )
    return updated


def _after(text: str, section: str) -> str:
    """`text` with `section` after it, a blank line between them: every byte of `text`
    kept — its last line's ending, and its blank lines — and only what separates the
    two added."""
    if text.endswith("\n\n"):
        return text + section
    return text + ("\n" if text.endswith("\n") else "\n\n") + section


def _entry_at(text: str, start: int, end: int, lines: Mapping[str, int], new_id: str) -> int:
    """Where in `text` the new entry goes: at the line of the first key that sorts
    after `new_id`, or at the end of the front matter, which spans `start:end`."""
    after = [line for key, line in lines.items() if key > new_id]
    if not after:
        return end
    return start + sum(len(line) for line in text[start:end].splitlines(True)[: min(after)])


def _section_at(text: str, body: int, kind: str, new_id: str) -> int | None:
    """Where in `text` the new section goes: before the first section of the body,
    which starts at `body`, headed by an id of `kind` that sorts after `new_id`;
    `None` for the end."""
    pattern = schemas.id_pattern(kind)
    offset = body
    for line in text[body:].splitlines(True):
        found = _SECTION.match(line)
        if found is not None and pattern.match(found["id"]) and found["id"] > new_id:
            return offset
        offset += len(line)
    return None


def _container(request: Request, artefacts: Sequence[str]) -> dict[str, Any]:
    """The methodology's container: the friction block with the anchors the stamp
    knows, in the core schema's order — or, for an actor or a term nothing
    embodies, the reason it has none, `unanchored-because`, which the core reads
    and the unanchored measure lists apart (COR-050 points 1 and 8); an empty
    block when it knows neither."""
    anchors = {
        kind: list(dict.fromkeys(values))
        for kind, values in (
            ("path", request.paths),
            ("record", request.records),
            ("artefact", artefacts),
        )
        if values
    }
    block: dict[str, Any] = {"anchors": anchors} if anchors else {}
    if request.unanchored_because:
        block[UNANCHORED_BECAUSE] = request.unanchored_because
    return {"friction": block}


def _title(request: Request) -> str:
    return request.title or request.slug.replace("-", " ").capitalize()


def _template(kind: str) -> tuple[str, str]:
    front, body = markdown.split((TEMPLATES / TEMPLATE_OF[kind]).read_text(encoding="utf-8"))
    assert front is not None, f"the {kind} template has no front matter"
    return front, body


def dump(data: Mapping[str, Any]) -> str:
    """`data` as block YAML, as every stamp writes a front matter."""
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 4096
    buffer = io.StringIO()
    yaml.dump(dict(data), buffer)
    return buffer.getvalue()
