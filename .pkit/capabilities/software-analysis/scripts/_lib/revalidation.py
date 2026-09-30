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
named by date and subject, never numbered, so parallel work cannot collide —
from `templates/revalidation-record.md`: its front matter names the change that
carried it, the trigger, the day (UTC, as a revalidation's `at` is — COR-050
point 3), who performed it, who confirmed an agent's outcomes, and each
artefact's outcome; its body gives each outcome's justification and each gap
with what resolved it. Every text is the person's: an outcome with no
justification is refused rather than written with the template's placeholder,
and a text still holding a placeholder (`_lib/placeholder.py`) is refused too.
An agent that performed it (`by_agent`) is named only beside the person who
confirmed it. The artefacts it cites are artefacts of the analysis, withdrawn
ones included, as the check holds a record (`_lib/check.py`); the front matter
is held to its schema before anything is written. It is written as an
artefact is (`stamp.write_and_record`): whole, and before the analysis location is
recorded, so a refused record leaves nothing written.
"""

from __future__ import annotations

import datetime
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from _lib import backbone, markdown, schemas
from _lib.model import REVALIDATIONS, Unreadable
from _lib.placeholder import unfilled
from _lib.stamp import TEMPLATES, Recorder, Refused, Stamped, dump, write_and_record

TEMPLATE = TEMPLATES / "revalidation-record.md"

#: The outcomes that are something to say (DEC-001 point 6), and the trigger that
#: always is: a regression or a gap found, or a revalidation planned before code.
FINDINGS = frozenset({"code-regressed", "gap-found"})
PLANNED = "planned"

#: The outcome that is something to say once a person decided it (DEC-001 point 5).
STALE = "analysis-stale"

#: The template's heading, an outcome's line and a gap's line, rewritten from the request.
_HEADING = "# <Date> — <Subject>"
_OUTCOME_LINE = re.compile(r"^- \*\*\S+ — [a-z-]+\.\*\* .*$")
_GAP_LINE = re.compile(r"^- <[^>]*> — \*\*resolved:\*\* .*$")


def utc_today() -> str:
    """Today in UTC, `YYYY-MM-DD`: the day a revalidation's `at` falls on."""
    # `timezone.utc` rather than `datetime.UTC`: the scripts run on Python 3.10 (their header).
    return datetime.datetime.now(datetime.timezone.utc).date().isoformat()  # noqa: UP017


@dataclass(frozen=True)
class RecordRequest:
    """What a record says: its subject, the change and trigger, who performed it —
    a person (`by`), or an agent (`by_agent`) beside the person who confirmed it —
    each artefact's outcome with its justification, and each gap with what
    resolved it."""

    slug: str
    change: str
    trigger: str
    outcomes: tuple[tuple[str, str], ...]  # (artefact id, outcome), in the order given
    by: str | None = None
    by_agent: str | None = None
    confirmed_by: str | None = None
    title: str | None = None
    because: tuple[tuple[str, str], ...] = ()  # (artefact id, justification)
    gaps: tuple[tuple[str, str], ...] = ()  # (gap, what resolved it)
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

    data: dict[str, object] = {
        "change": request.change,
        "trigger": request.trigger,
        "date": request.date,
        "by": by,
    }
    if request.confirmed_by:
        data["confirmed-by"] = request.confirmed_by
    data["outcomes"] = outcomes
    problems = schemas.errors(schemas.RECORD, data)
    if problems:
        pointer, message = problems[0]
        raise Refused(f"the record would not fit its schema at {pointer or '/'}: {message}")

    location = f"{analysis.location}/{REVALIDATIONS}/{request.date}-{request.slug}.md"
    target = root / location
    if target.exists():
        raise Refused(f"{location} exists already: name the subject with another slug")
    text = f"---\n{dump(data)}---\n\n{_body(request, outcomes, because)}"

    recorded = write_and_record(root, target, location, text, record)
    notes = (recorded,) if recorded else ()
    return Stamped(id=f"{request.date}-{request.slug}", location=location, notes=notes)


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
    gives is what it is, so none is written as the template's placeholder."""
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
            f'--gap "<gap> => <what resolved it>" — the defect reported, or the artefact '
            f"written (DEC-001 point 6)"
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
    texts += [("--gap", f"{gap} => {resolved}") for gap, resolved in request.gaps]
    for flag, text in texts:
        placeholder = unfilled(text or "")
        if placeholder is not None:
            raise Refused(
                f"{flag} still holds the placeholder {placeholder!r}: write in its place what "
                f"it asks for — the record's words are the person's"
            )


# --- rendering -------------------------------------------------------------------------------


def _body(request: RecordRequest, outcomes: Mapping[str, str], because: Mapping[str, str]) -> str:
    """The template's body: its heading the date and subject, one outcome line per
    artefact with its justification, one gap line per gap — or none found."""
    _front, body = markdown.split(TEMPLATE.read_text(encoding="utf-8"))
    subject = request.title or request.slug.replace("-", " ").capitalize()
    lines: list[str] = []
    for line in body.replace(_HEADING, f"# {request.date} — {subject}").split("\n"):
        if _OUTCOME_LINE.match(line) is not None:
            lines += [f"- **{i} — {outcome}.** {because[i]}" for i, outcome in outcomes.items()]
        elif _GAP_LINE.match(line):
            lines += [f"- {gap} — **resolved:** {resolved}" for gap, resolved in request.gaps]
            lines += [] if request.gaps else ["None found."]
        else:
            lines.append(line)
    return "\n".join(lines)
