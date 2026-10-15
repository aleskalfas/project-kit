"""Stamping a revalidation record (DEC-001 points 5 and 6).

A revalidation record is kept only when there is something to say. Point 6
names when one is: the revalidation was **planned**, or found a
**regression** or a **gap**. And it names when none is: a routine
revalidation, whose artefacts hold or were updated because the change was
meant, is recorded by each artefact's own revalidation block, which `pkit
friction revalidate` writes. One more case says something that no block
holds: an artefact found **stale** where a person decided the change was
meant — `--confirmed-by` names them, as point 5 asks a person to decide stale
against regressed where the two are ambiguous. So the stamp refuses a record
with nothing to say, and refuses a regression or a gap whose gap it is not
told, with what resolved it.

The record is `revalidations/<date>-<slug>.md` under the analysis location —
named by date and subject, never numbered, so parallel work cannot collide.
Its front matter names the change that carried it, the trigger, a planned
revalidation's sources, the day (UTC, as a revalidation's `at` is — COR-050
point 3), who performed it, who confirmed an agent's outcomes, and each
artefact's outcome. Its body is rendered from the record's declared structure
(`_lib/render.py`) with no hints, since the stamp writes every part: each
outcome with its justification, and each gap with its resolution, or `None.`.

- **A planned record's sources** (point 6). `--reviewed-against` names one
  source each time it is given: `<title> @ <version>` for a source in this
  repository, and `<title> @ <version> @ <link>` for one outside it. A link is
  told from a version by its `://`, so a title may hold ` @ `. Only a planned
  record takes the flag, and a planned record takes it at least once. Each
  source is held to the record's schema before anything is written.
- **A commit off the default branch.** A source in this repository whose
  commit the default branch does not hold is written all the same, and the
  stamp warns: `pkit analysis check-pointers` fails the change that adds the
  record until the source names a commit the default branch holds, or `this
  change`. Refusing would leave no way to write the record while the design's
  pull request is open. The stamp places each commit as that command does
  (`_lib/pointers.py`), and says nothing of a commit it cannot place.
- **Each gap names the artefacts it affects** (point 6): `--gap "<ids>: <gap>
  => <resolution>"`, the ids separated by commas. The stamp writes the ids as
  the gap's bold label, then the gap and its `**Resolution:**`, each ended with
  a full stop where it has none. It refuses what the form `gaps-match-outcomes`
  refuses (`_lib/forms.py`): an id the record gives no outcome, or a
  regression or a gap that no gap names.

Every text is the person's: an outcome with no justification is refused rather
than written with a placeholder, and a text still holding a placeholder
(`_lib/placeholder.py`) is refused too. An agent that performed it
(`by_agent`) is named only beside the person who confirmed it. The artefacts it
cites are artefacts of the analysis, withdrawn ones included, as the check
holds a record (`_lib/check.py`); the front matter is held to its schema before
anything is written. It is written as an artefact is
(`stamp.write_and_record`): whole, and before the analysis location is
recorded, so a refused record leaves nothing written.
"""

from __future__ import annotations

import datetime
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from _lib import backbone, forms, pointers, render, schemas, structure
from _lib.model import PLANNED, REVALIDATIONS, Unreadable
from _lib.placeholder import unfilled
from _lib.stamp import Recorder, Refused, Stamped, declared, dump, write_and_record

#: The outcomes that are something to say (DEC-001 point 6): a regression or a gap
#: found. A planned revalidation always is (`PLANNED`).
FINDINGS = frozenset({"code-regressed", "gap-found"})

#: The outcome that is something to say once a person decided it (DEC-001 point 5).
STALE = "analysis-stale"

#: What parts a source's title, version and link in `--reviewed-against`.
SOURCE_SEPARATOR = " @ "

#: The front-matter field a planned record names its sources in.
REVIEWED = "reviewed-against"

#: How a source is written on the command line, for the messages.
SOURCE_FORMS = (
    '"<title> @ <version>" for a source in this repository, and "<title> @ <version> @ <link>" '
    "for one outside it"
)


def utc_today() -> str:
    """Today in UTC, `YYYY-MM-DD`: the day a revalidation's `at` falls on."""
    # `timezone.utc` rather than `datetime.UTC`: the scripts run on Python 3.10 (their header).
    return datetime.datetime.now(datetime.timezone.utc).date().isoformat()


@dataclass(frozen=True)
class Gap:
    """A gap found: the ids of the artefacts it affects, what was found, and what resolved
    it or carries its fix."""

    ids: tuple[str, ...]
    found: str
    resolution: str

    @property
    def given(self) -> str:
        """The gap as `--gap` takes it."""
        return f"{', '.join(self.ids)}: {self.found} => {self.resolution}"


@dataclass(frozen=True)
class RecordRequest:
    """What a record says: its subject, the change and trigger, a planned revalidation's
    sources, who performed it — a person (`by`), or an agent (`by_agent`) beside the
    person who confirmed it — each artefact's outcome with its justification, and each
    gap with the artefacts it affects and what resolved it."""

    slug: str
    change: str
    trigger: str
    outcomes: tuple[tuple[str, str], ...]  # (artefact id, outcome), in the order given
    by: str | None = None
    by_agent: str | None = None
    confirmed_by: str | None = None
    title: str | None = None
    because: tuple[tuple[str, str], ...] = ()  # (artefact id, justification)
    gaps: tuple[Gap, ...] = ()
    reviewed_against: tuple[str, ...] = ()  # each as `--reviewed-against` takes it
    date: str = field(default_factory=utc_today)


def stamp_record(
    root: Path, request: RecordRequest, *, record: Recorder = backbone.record_location
) -> Stamped:
    """Write the revalidation record `request` asks for, in the project at `root`."""
    try:
        analysis = backbone.read_analysis(root)
    except Unreadable as exc:
        raise Refused(f"the analysis could not be read: {exc}") from exc
    if analysis.location is None:
        raise Refused(
            "the backbone's reading holds no place of software-analysis; `pkit validate` says why"
        )
    if not schemas.slug_pattern().match(request.slug):
        raise Refused(
            f"the slug {request.slug!r} is not a word: a lowercase letter, then lowercase "
            f"letters, digits and hyphens"
        )
    outcomes = _outcomes(request.outcomes)
    for artefact_id in outcomes:
        if analysis.find(artefact_id) is None:
            raise Refused(
                f"no artefact {artefact_id} in the analysis: a record cites artefacts of the "
                f"analysis by id, withdrawn ones included (DEC-001 point 6)"
            )
    _something_to_say(request, outcomes)
    because = _because(request.because, outcomes)
    _no_placeholder(request)
    if request.by and request.by_agent:
        raise Refused("name who performed it once: --by for a person, or --by-agent for an agent")
    if request.by_agent and not request.confirmed_by:
        raise Refused(
            f"{request.by_agent} is an agent: name the person who confirmed its outcomes with "
            f"--confirmed-by — an agent proposes, a person decides (DEC-001 point 5)"
        )
    by = request.by_agent or request.by or backbone.user_name(root)
    if not by:
        raise Refused("name who performed the revalidation with --by: a person, or an agent")
    sources = _sources(request)

    data: dict[str, object] = {"change": request.change, "trigger": request.trigger}
    if sources:
        data[REVIEWED] = sources
    data |= {"date": request.date, "by": by}
    if request.confirmed_by:
        data["confirmed-by"] = request.confirmed_by
    data["outcomes"] = outcomes
    problems = schemas.errors(schemas.RECORD, data)
    if problems:
        pointer, message = problems[0]
        raise Refused(f"the record would not fit its schema at {pointer or '/'}: {message}")

    kind = declared(structure.RECORD)
    text = f"---\n{dump(data)}---\n\n{_body(request, outcomes, because, kind)}"
    _gaps_hold(text, kind, data, request.gaps)
    location = f"{analysis.location}/{REVALIDATIONS}/{request.date}-{request.slug}.md"
    target = root / location
    if target.exists():
        raise Refused(f"{location} exists already: name the subject with another slug")
    warnings = _off_the_default_branch(root, sources)

    recorded = write_and_record(root, target, location, text, record)
    notes = (recorded,) if recorded else ()
    return Stamped(
        id=f"{request.date}-{request.slug}", location=location, notes=notes, warnings=warnings
    )


# --- what the request says -------------------------------------------------------------------


def _outcomes(given: Sequence[tuple[str, str]]) -> dict[str, str]:
    """Each artefact's outcome, once each, from the schema's words."""
    if not given:
        raise Refused(
            "a record names each artefact it covered and its outcome: --outcome <id>=<outcome>"
        )
    allowed = schemas.record_outcomes()
    outcomes: dict[str, str] = {}
    for artefact_id, outcome in given:
        if outcome not in allowed:
            raise Refused(
                f"{artefact_id}'s outcome {outcome!r} is not one of {', '.join(allowed)} "
                f"(DEC-001 point 5)"
            )
        if artefact_id in outcomes:
            raise Refused(f"{artefact_id} is given two outcomes: a record gives each one")
        outcomes[artefact_id] = outcome
    return outcomes


def _because(given: Sequence[tuple[str, str]], outcomes: Mapping[str, str]) -> dict[str, str]:
    """Each outcome's justification, once each: a record says why every outcome it
    gives is what it is, so none is written as a placeholder."""
    because: dict[str, str] = {}
    for artefact_id, text in given:
        if artefact_id not in outcomes:
            raise Refused(
                f"--because names {artefact_id}, which has no --outcome: justify the outcomes "
                f"the record gives"
            )
        if artefact_id in because:
            raise Refused(f"{artefact_id} is given two --because: a record gives each one")
        because[artefact_id] = text
    unjustified = [i for i in outcomes if i not in because]
    if unjustified:
        raise Refused(
            f"{', '.join(unjustified)} has no --because: a record says why each outcome it "
            f"gives is what it is — --because <id>=<why>"
        )
    return because


def _something_to_say(request: RecordRequest, outcomes: Mapping[str, str]) -> None:
    """A record is kept for a planned revalidation, a regression or a gap (point 6), or
    an artefact a person decided was stale (point 5); a regression or gap names what
    it found and what resolved it."""
    found = sorted(i for i, outcome in outcomes.items() if outcome in FINDINGS)
    if found and not request.gaps:
        raise Refused(
            f"{', '.join(found)} found a regression or a gap: name each with "
            f'--gap "<ids>: <gap> => <what resolved it>" — the artefacts it affects, then '
            f"the gap, then the defect reported or the artefact written (DEC-001 point 6)"
        )
    if request.trigger == PLANNED or found or request.gaps:
        return
    if request.confirmed_by and STALE in outcomes.values():
        return
    raise Refused(
        "nothing to record: a revalidation leaves a record only when it was planned, or found "
        "a gap or a regression (DEC-001 point 6), or when a person decided an artefact was "
        "stale — --confirmed-by names them (point 5). One whose artefacts hold, or were "
        "updated because the change was plainly meant, is recorded by each artefact's own "
        "revalidation — `pkit friction revalidate <artefact> --outcome …`"
    )


def _no_placeholder(request: RecordRequest) -> None:
    """Every text of the record is the person's: one still holding a placeholder is
    refused, as the backbone's writers refuse one in a justification."""
    texts: list[tuple[str, str | None]] = [
        ("--change", request.change),
        ("--title", request.title),
        ("--by", request.by),
        ("--by-agent", request.by_agent),
        ("--confirmed-by", request.confirmed_by),
    ]
    texts += [(f"--because {i}", text) for i, text in request.because]
    texts += [("--gap", gap.given) for gap in request.gaps]
    texts += [("--reviewed-against", value) for value in request.reviewed_against]
    for flag, text in texts:
        placeholder = unfilled(text or "")
        if placeholder is not None:
            raise Refused(
                f"{flag} still holds the placeholder {placeholder!r}: write in its place what "
                f"it asks for — the record's words are the person's"
            )


# --- a planned record's sources (DEC-001 point 6) ---------------------------------------------


def _sources(request: RecordRequest) -> list[dict[str, str]]:
    """A planned record's sources, one for each `--reviewed-against`: required on a planned
    record, and refused on a record of any other trigger."""
    if request.trigger != PLANNED:
        if request.reviewed_against:
            raise Refused(
                f"--reviewed-against names the sources of the design a planned revalidation "
                f"reviewed: a record triggered by {request.trigger} takes none (DEC-001 point 6)"
            )
        return []
    if not request.reviewed_against:
        raise Refused(
            f"a planned record names each source of the design it reviewed, in "
            f"`{REVIEWED}`: give --reviewed-against once for each, {SOURCE_FORMS} "
            f"(DEC-001 point 6)"
        )
    return [source(value) for value in request.reviewed_against]


def source(value: str) -> dict[str, str]:
    """One source of a planned record's design, from `--reviewed-against`: its `title`, its
    `url` where it lies outside this repository, and its `version`, held to the record's
    schema. The last part is the link when it holds `://`, and the version otherwise."""
    parts = [part.strip() for part in value.split(SOURCE_SEPARATOR)]
    linked = len(parts) >= 3 and "://" in parts[-1]
    title = SOURCE_SEPARATOR.join(parts[: -2 if linked else -1]).strip()
    version = parts[-2] if linked else parts[-1]
    if len(parts) < 2 or not title or not version:
        raise Refused(f"--reviewed-against {value!r} is not {SOURCE_FORMS}")
    found = {"title": title, **({"url": parts[-1]} if linked else {}), "version": version}
    problems = schemas.source_errors(found)
    if problems:
        read_as = ", ".join(f"{key} {text!r}" for key, text in found.items())
        raise Refused(
            f"--reviewed-against {value!r} reads as {read_as}, which the record's schema "
            f"refuses: {problems[0]}. A source in this repository names a commit's full id, or "
            f"`{schemas.this_change()}` when the design lands with the record. One outside it "
            f"names its link, and the time its text was read, such as 2026-01-05T10:00:00Z, or "
            f"a commit's full id (DEC-001 point 6)"
        )
    return found


def _off_the_default_branch(root: Path, sources: Sequence[Mapping[str, str]]) -> tuple[str, ...]:
    """A warning for each source in this repository whose commit the default branch does
    not hold, placed as `pkit analysis check-pointers` places it (`pointers.place`). A
    commit it cannot place, and a default branch it cannot read, say nothing: the
    pointers are provenance, and that command reports them (DEC-001 point 6)."""
    commit = schemas.commit_pattern()
    named = [
        (s["title"], s["version"]) for s in sources if "url" not in s and commit.match(s["version"])
    ]
    if not named:
        return ()
    try:
        branch = backbone.settled(root).default_branch
    except Unreadable:
        return ()
    if branch.commit is None:
        return ()
    warned: list[str] = []
    for title, version in named:
        try:
            placement = pointers.place(root, version, branch.commit)
        except backbone.GitFailed:
            continue
        if placement == pointers.NOT_HELD:
            warned.append(
                f'"{title}" names {version[: backbone.SHORT]}, which the default branch, '
                f"{branch.ref}, does not hold: `pkit analysis check-pointers` fails the change "
                f"that adds this record until the source names a commit {branch.name} holds, "
                f"or `{schemas.this_change()}` when the design lands with the record. A squash "
                f"merge leaves a branch's commits off it (DEC-001 point 6)"
            )
    return tuple(warned)


# --- rendering -------------------------------------------------------------------------------


def _body(
    request: RecordRequest,
    outcomes: Mapping[str, str],
    because: Mapping[str, str],
    kind: structure.Kind,
) -> str:
    """The record's body, rendered from its structure with no hints: its heading the date
    and subject, one outcome line per artefact with its justification, and one line per
    gap, or `None.`."""
    subject = request.title or request.slug.replace("-", " ").capitalize()
    written: dict[str, str] = {}
    for element in kind.sections:
        if element.form == forms.OUTCOMES_MATCH:
            lines = [f"- **{i} — {outcome}.** {because[i]}" for i, outcome in outcomes.items()]
            written[element.id] = "\n".join(lines)
        elif element.form == forms.GAPS_MATCH:
            written[element.id] = "\n".join(map(_gap_line, request.gaps)) or forms.NONE
    return render.body(kind, f"{request.date} — {subject}", written, hints=False)


def _gap_line(gap: Gap) -> str:
    """A gap as its item: its ids as its bold label, then the gap and its resolution."""
    label = ", ".join(gap.ids)
    return f"- **{label}:** {_ended(gap.found)} **Resolution:** {_ended(gap.resolution)}"


def _ended(text: str) -> str:
    """`text` ended with a full stop, where it ends with no mark that ends a sentence."""
    return text if text.endswith((".", "?", "!")) else f"{text}."


def _gaps_hold(
    text: str, kind: structure.Kind, data: Mapping[str, object], gaps: Sequence[Gap]
) -> None:
    """Refuse the record when its gaps break the form `gaps-match-outcomes`, as the check
    would find them (`_lib/forms.py`): a gap naming an id the record gives no outcome, or
    a regression or a gap that no gap names (DEC-001 point 6)."""
    part = next((e for e in kind.sections if e.form == forms.GAPS_MATCH), None)
    if part is None:
        return
    lines = structure.body_lines(text)
    breaches = [
        d for d in structure.departures(lines, kind, fields=data) if d.element.id == part.id
    ]
    if not breaches:
        return
    first = breaches[0]
    rendered = {line: number for number, line in lines}
    for gap in gaps:
        if rendered.get(_gap_line(gap)) == first.line:
            raise Refused(
                f"--gap {gap.given!r}: {first.detail}. A gap names the artefacts it affects, "
                f"each one the record gives an outcome (DEC-001 point 6)"
            )
    raise Refused(
        f"the gaps break the form `{forms.GAPS_MATCH}`: {first.detail or first.how}. Name each "
        f"regression and each gap found among a --gap's ids (DEC-001 point 6)"
    )
