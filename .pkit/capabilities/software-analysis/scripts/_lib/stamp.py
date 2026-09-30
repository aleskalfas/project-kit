"""Stamping the analysis artefacts (DEC-001 points 2 to 4).

A stamp writes one artefact from its kind's template in `templates/`, where
the capability's places put it under the analysis location:

- a **use case** or a **journey** is a new file, `UC-NNN-<slug>.md` or
  `JRN-NNN-<slug>.md`, numbered with the next free number — one past the
  highest the working tree and the default branch hold, withdrawn ones
  included, and past every number the default branch's history ever gave a
  file, deleted since or not, since a number is never used again. A file's
  number is read from its front matter and from its name, so a file whose id
  cannot be read still holds its number. Numbers two branches take in
  parallel are `pkit analysis check-numbers`' to report (point 3);
- an **actor** or a **term** is a new entry, `ACT-<slug>` or `TERM-<slug>`, of
  its collection file — added to its front matter, and its section to the
  body, each where its id sorts, every other byte left as it was — the file
  created from the template the first time.

It writes the anchors DEC-001 point 4 asks for: a use case's actor, and a
journey's use cases from its steps, beside the paths and records it is given.
An actor or a term nothing embodies is stamped with the reason instead, its
`unanchored-because` (point 9). A revalidation record is not an artefact and
is stamped by `_lib/revalidation.py`.
What only a person can write the stamp leaves as the template's placeholders —
an actor's need, a term's definition, a body's goal and steps — which the
check fails until each is filled (`left_to_fill`); a title, a name or a reason
given to it still holding a placeholder it refuses.
Before the first artefact is placed it records the analysis location through
the backbone (COR-049 point 5). Where the analysis is, and what it holds, is
read through the backbone's discovery — the working tree's and the default
branch's tip — never by walking the places. The default branch's history is
one `git log` of the paths ever added under the use-case and journey places
the discovery names (`backbone.added_paths`), each number read from the file's
name, as the stamp names every file: one computation, where reading the
discovery at each of the history's commits would be one per commit. A file
never named after its number, and deleted since, is the one it cannot count.
"""

from __future__ import annotations

import functools
import io
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from _lib import backbone, markdown, schemas
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
    id_in_name,
    identity,
    with_article,
)
from _lib.placeholder import unfilled

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

#: A text in angle brackets, as a template writes what a person fills.
_BRACKETED = re.compile(r"<[^<>\n]+>")


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
    new_id = _new_id(kind, request.slug, _held(root, analysis, base, notes), base)

    if kind in COLLECTIONS:
        target = root / place
        text = _added_entry(target, place, kind, new_id, request)
        location = f"{place}#{new_id}"
    else:
        folder = f"{place}/{request.area}" if request.area else place
        location = f"{folder}/{new_id}-{request.slug}.md"
        target = root / location
        if target.exists():
            raise Refused(f"{location} exists already")
        text = _document(kind, new_id, request)

    try:
        recorded = record(root)
    except Unreadable as exc:
        raise Refused(f"the analysis location could not be recorded: {exc}") from exc
    if recorded:
        notes.insert(0, recorded)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return Stamped(id=new_id, location=location, notes=tuple(notes))


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
    """The words given are the person's: one still holding a placeholder is refused,
    as the record stamp and the backbone's writers refuse one — the check fails an
    artefact's field holding one (`_lib/check.py`)."""
    flag = "--name" if request.kind in COLLECTIONS else "--title"
    for option, text in (
        (flag, request.title),
        ("--unanchored-because", request.unanchored_because),
    ):
        placeholder = unfilled(text or "")
        if placeholder is not None:
            raise Refused(
                f"{option} still holds the placeholder {placeholder!r}: write in its place what "
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


def _held(root: Path, analysis: Analysis, base: str, notes: list[str]) -> set[str]:
    """Every id held, as `identity` spells it: in the working tree, and on the default
    branch — at its tip, and every number its history ever gave a file, whose file
    may be gone since (DEC-001 point 3). A file's number is read from its name too,
    whatever it holds (`Analysis.held`). Without the default branch, the working
    tree's alone, with a note saying why."""
    held = analysis.held()
    tip = backbone.commit_of(root, base)
    if tip is None:
        notes.append(
            f"{base} names no commit here, so ids were taken from the working tree alone; "
            f"`pkit analysis check-numbers` compares them once it resolves"
        )
        return held
    try:
        on_base = backbone.read_analysis(root, at=tip)
    except Unreadable as exc:
        notes.append(f"{base} could not be read ({exc}); ids were taken from the working tree")
        return held
    folders = {a.places[k] for a in (analysis, on_base) for k in NUMBERED if k in a.places}
    in_history = {id_in_name(path) for path in backbone.added_paths(root, tip, folders)}
    return held | on_base.held() | {i for i in in_history if i is not None}


def _new_id(kind: str, slug: str, held: set[str], base: str) -> str:
    """The next free number for a use case or journey; `<PREFIX>-<slug>` for the rest,
    refused when the working tree or the default branch holds it already. Ids are
    compared by what they stand for (`identity`), as the check compares them: a
    number spelt `UC-0007` is held as `UC-007` is."""
    pattern = schemas.id_pattern(kind)
    if kind in NUMBERED:
        numbers = [int(i.split("-", 1)[1]) for i in held if pattern.match(i)]
        return identity(f"{PREFIX[kind]}-{max(numbers, default=0) + 1}")
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
    if request.unanchored_because:
        entry[UNANCHORED_BECAUSE] = request.unanchored_because
    entry[CONTAINER] = _container(request, [])
    heading = body.find(f"## {template_id}")
    preamble, section = body[:heading], body[heading:]
    section = section.replace(template_id, new_id).replace(str(example["name"]), name)
    added = dump({new_id: entry})
    if not target.exists():
        return f"---\n{added}---\n\n{preamble}{section}"

    text = target.read_text(encoding="utf-8")
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
        updated = text[:entry_at] + added + text[entry_at:]
        updated = updated.rstrip("\n") + "\n\n" + section
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
    knows, in the core schema's order; an empty block when it knows none."""
    anchors = {
        kind: list(dict.fromkeys(values))
        for kind, values in (
            ("path", request.paths),
            ("record", request.records),
            ("artefact", artefacts),
        )
        if values
    }
    return {"friction": {"anchors": anchors} if anchors else {}}


def _title(request: Request) -> str:
    return request.title or request.slug.replace("-", " ").capitalize()


@functools.cache
def left_to_fill() -> frozenset[str]:
    """The placeholders a stamp leaves in an artefact's body for a person to fill: each
    text in angle brackets of the artefact templates' bodies, but the title and the
    name the stamp writes in their place. The check fails a body still holding one,
    matched exactly, so code a body quotes is never taken for one."""
    written = {TITLE}
    left: set[str] = set()
    for kind in TEMPLATE_OF:
        front, body = _template(kind)
        if kind in COLLECTIONS:
            ((_example_id, example),) = dict(markdown.load(front)).items()
            written.add(str(example["name"]))
        left |= set(_BRACKETED.findall(body))
    return frozenset(left - written)


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
