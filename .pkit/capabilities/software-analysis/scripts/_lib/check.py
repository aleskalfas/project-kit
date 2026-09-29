"""software-analysis' check of the analysis (DEC-001 points 2 to 6).

What is checked, each against the record's words:

- **Shape** (points 1 and 2). Every file in one of the places holds artefacts of
  that place's kind: the glossary and the actors are collection files, one
  entry per artefact keyed by its id; a use case and a journey are a document
  each. A file without front matter, a collection file that is not one, or a
  use-case or journey file holding entries, is an error.
- **Missing required parts** (points 1 and 3). Each artefact's own fields
  against its kind's companion schema — its id, its status, its actor, its
  steps, its needs, its definition — and an entry's id against its kind's id.
  Unknown fields are refused, so a misspelt one is never silently ignored.
- **Duplicate ids** (point 3). No two artefacts in the analysis share an id.
- **A use case anchors to its actor** (point 4), as an artefact anchor, so a
  changed actor flags it.
- **A journey's anchors match its steps** (point 4): the use cases among its
  artefact anchors are exactly those `steps` lists, so the friction check sees
  every use case it passes through, and the two cannot drift apart.
- **Revalidation records** (points 5 and 6): each record's front matter
  against its schema. The records are not anchored artefacts and lie in no
  place, so they are read from their folder under the analysis location.

It reads the working tree alone, so the same tree always answers the same.

**Not here.** A number two branches took (point 3) is `pkit analysis
check-numbers`' (`_lib/numbers.py`): it reads the default branch, so it answers
about a change rather than the tree, and is not a validator (ADR-058 point 7).
The friction block — its shape, dead anchors, cycles, friction itself — is the
core's (`pkit validate`'s `friction` member and `pkit friction check`); so is a
front matter that does not parse, which this check counts and leaves to it. An
unanchored artefact is the core's measure, never an error.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from ruamel.yaml.error import YAMLError

from _lib import backbone, markdown, schemas
from _lib.findings import ERROR, Finding, Outcome, at
from _lib.model import (
    ACTOR,
    ID_SHAPE,
    JOURNEY,
    KINDS,
    NOUN,
    REVALIDATIONS,
    USE_CASE,
    Analysis,
    Artefact,
    Unreadable,
    with_article,
)

#: Where in an artefact its artefact anchors sit.
ARTEFACT_ANCHORS = "/pkit/friction/anchors/artefact"


def check(root: Path) -> Outcome:
    """Check the analysis in the working tree at `root`."""
    outcome = Outcome()
    try:
        analysis = backbone.read_analysis(root)
    except Unreadable as exc:
        outcome.summary.append("the analysis could not be read; nothing checked.")
        outcome.findings.append(Finding(ERROR, ".", f"the places could not be read: {exc}"))
        return outcome
    if analysis.location is None:
        outcome.summary.append(
            "no place of this capability is in the backbone's reading; nothing checked "
            "(`pkit validate`'s friction member says why)."
        )
        return outcome

    records = _records(root, analysis.location)
    outcome.summary.append(_counts(analysis, len(records)))
    outcome.findings += [Finding(ERROR, s.path, s.why) for s in analysis.strays]
    outcome.findings += _own_fields(analysis)
    outcome.findings += _duplicates(analysis)
    outcome.findings += _actor_anchors(analysis)
    outcome.findings += _journey_anchors(analysis)
    outcome.findings += _record_findings(root, records)
    return outcome


def _counts(analysis: Analysis, records: int) -> str:
    kinds = ", ".join(f"{len(analysis.of_kind(k))} {NOUN[k]}(s)" for k in KINDS)
    line = f"analysis at {analysis.location}: {kinds}; {records} revalidation record(s)."
    if analysis.unreadable:
        line += f" {len(analysis.unreadable)} file(s) whose front matter does not parse, left to "
        line += "`pkit validate`'s friction member."
    return line


# --- shape and required parts --------------------------------------------------------------


def _own_fields(analysis: Analysis) -> list[Finding]:
    found: list[Finding] = []
    for artefact in analysis.artefacts:
        if artefact.entry and not schemas.id_pattern(artefact.kind).match(artefact.id or ""):
            found.append(
                Finding(
                    ERROR,
                    artefact.location,
                    f"the entry's key {artefact.id!r} is not {with_article(artefact.kind)} id, "
                    f"`{ID_SHAPE[artefact.kind]}` (DEC-001 point 3)",
                )
            )
        for pointer, message in schemas.errors(artefact.kind, artefact.fields):
            found.append(Finding(ERROR, at(artefact.location, pointer), message))
    return found


# --- ids -----------------------------------------------------------------------------------


def _duplicates(analysis: Analysis) -> list[Finding]:
    holders: dict[str, list[Artefact]] = defaultdict(list)
    for artefact in analysis.artefacts:
        if artefact.id is not None:
            holders[artefact.id].append(artefact)
    return [
        Finding(
            ERROR,
            later.location,
            f"the id {artefact_id} is also held by {group[0].location}: no two artefacts in the "
            f"analysis share an id, and an id is never used again (DEC-001 point 3)",
        )
        for artefact_id, group in holders.items()
        for later in group[1:]
    ]


# --- anchors -------------------------------------------------------------------------------


def _actor_anchors(analysis: Analysis) -> list[Finding]:
    found: list[Finding] = []
    for use_case in analysis.of_kind(USE_CASE):
        actor = use_case.fields.get("actor")
        if not isinstance(actor, str) or not schemas.id_pattern(ACTOR).match(actor):
            continue  # the schema reports it
        if actor not in use_case.anchored_to("artefact"):
            found.append(
                Finding(
                    ERROR,
                    at(use_case.location, ARTEFACT_ANCHORS),
                    f"a use case anchors to its actor, so a changed actor flags it: add {actor} "
                    f"to its artefact anchors (DEC-001 point 4)",
                )
            )
    return found


def _journey_anchors(analysis: Analysis) -> list[Finding]:
    pattern = schemas.id_pattern(USE_CASE)
    found: list[Finding] = []
    for journey in analysis.of_kind(JOURNEY):
        steps = journey.fields.get("steps")
        if not isinstance(steps, list):
            continue  # the schema reports it
        expected = _unique(s for s in steps if isinstance(s, str) and pattern.match(s))
        anchored = _unique(a for a in journey.anchored_to("artefact") if pattern.match(a))
        if expected and set(expected) != set(anchored):
            found.append(
                Finding(
                    ERROR,
                    at(journey.location, ARTEFACT_ANCHORS),
                    f"its use-case anchors ({', '.join(anchored) or 'none'}) do not match its "
                    f"steps ({', '.join(expected)}): the anchors are written from `steps`, so "
                    f"the friction check sees every use case it passes through — anchor exactly "
                    f"[{', '.join(expected)}] (DEC-001 point 4)",
                )
            )
    return found


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))


# --- revalidation records ------------------------------------------------------------------


def _records(root: Path, location: str) -> list[Path]:
    """The revalidation records: the Markdown files directly in their folder."""
    folder = root / location / REVALIDATIONS
    if not folder.is_dir() or folder.is_symlink():
        return []
    return sorted(
        p for p in folder.iterdir() if p.suffix == ".md" and p.is_file() and not p.is_symlink()
    )


def _record_findings(root: Path, records: list[Path]) -> list[Finding]:
    found: list[Finding] = []
    for path in records:
        rel = path.relative_to(root).as_posix()
        try:
            front, _body = markdown.split(path.read_text(encoding="utf-8"))
            data = markdown.load(front) if front is not None else None
        except (OSError, UnicodeDecodeError) as exc:
            found.append(Finding(ERROR, rel, f"cannot be read: {exc}"))
            continue
        except YAMLError as exc:
            reason = str(exc).splitlines()[0] if str(exc) else type(exc).__name__
            found.append(Finding(ERROR, rel, f"its front matter does not parse: {reason}"))
            continue
        if not isinstance(data, dict):
            found.append(
                Finding(
                    ERROR,
                    rel,
                    "has no front matter mapping: a revalidation record names the change, the "
                    "trigger, the date, who performed it and each artefact's outcome (DEC-001 "
                    "point 6)",
                )
            )
            continue
        for pointer, message in schemas.errors(schemas.RECORD, data):
            found.append(Finding(ERROR, at(rel, pointer), message))
    return found
