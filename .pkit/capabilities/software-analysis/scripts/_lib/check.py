"""software-analysis' check of the analysis (DEC-001 points 2 to 6).

What is checked, each against the record's words:

- **Shape** (points 1 and 2). Every file in one of the places holds artefacts of
  that place's kind: the glossary and the actors are collection files, one
  entry per artefact keyed by its id; a use case and a journey are a document
  each. A file without front matter, a collection file that is not one, or a
  use-case or journey file holding entries, is an error.
- **Missing required parts** (points 1 and 3). Each artefact's own fields
  against its kind's companion schema — its id, its title, its status, its
  actor, its steps, its needs, its definition — and an entry's id against its
  kind's id. Unknown fields are refused, so a misspelt one is never silently
  ignored.
- **A use case's and a journey's heading** is its id and its front matter's
  title, `# UC-NNN — <title>`: what a reader of the front matter alone sees —
  a data point publishing `{id, title, status}`, say — is what the page shows.
  The heading is read from the file discovery names.
- **Duplicate ids** (point 3). No two artefacts in the analysis share an id,
  a number spelt with other zeros included — as the stamp counts it held.
- **What a use case or journey names** (points 1 and 3): its actor, and a
  journey's steps, are an actor and use cases of the analysis; and one in
  force names none withdrawn. The stamp refuses the same (`Analysis.unfit`),
  so the check never accepts what the stamp would not write; a withdrawn
  artefact may name withdrawn ones.
- **A use case anchors to its actor** (point 4), as an artefact anchor, so a
  changed actor flags it.
- **A journey's anchors match its steps** (point 4): the use cases among its
  artefact anchors are exactly those `steps` lists, so the friction check sees
  every use case it passes through, and the two cannot drift apart.
- **Revalidation records** (points 5 and 6): each record's front matter
  against its schema, and the artefacts its outcomes cite are artefacts of the
  analysis, withdrawn ones included. The records are not anchored artefacts
  and lie in no place, so they are read from their folder under the analysis
  location.
- **Evidence a record cites** (point 7) supports an outcome and never replaces
  one: evidence for an artefact the record gives no outcome is an error, read
  from the record alone. Whether the evidence point holds each cited id is
  read from the point as it resolves (`_lib/evidence.py`), only when some
  record cites evidence; the evidence advises, so a citation the point does
  not hold, or a point that does not resolve, is a warning and never fails.

It reads the working tree alone — and, when a record cites evidence, the
evidence point — so the same tree always answers the same.

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

from _lib import backbone, evidence, markdown, schemas
from _lib.findings import ERROR, WARNING, Finding, Outcome, at
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
    identity,
    with_article,
)

#: Where in an artefact its artefact anchors sit.
ARTEFACT_ANCHORS = "/pkit/friction/anchors/artefact"

#: One evidence citation of a record: where it is written, and the evidence id.
Citation = tuple[str, str]


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
    outcome.findings += _headings(root, analysis)
    outcome.findings += _duplicates(analysis)
    outcome.findings += _references(analysis)
    outcome.findings += _actor_anchors(analysis)
    outcome.findings += _journey_anchors(analysis)
    record_findings, citations = _record_findings(root, records, analysis)
    outcome.findings += record_findings
    if citations:
        summary, held = _evidence_held(root, citations)
        outcome.summary.append(summary)
        outcome.findings += held
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


def _headings(root: Path, analysis: Analysis) -> list[Finding]:
    """A use case's and a journey's heading reads `<id> — <title>`, as its front matter
    gives them."""
    found: list[Finding] = []
    for artefact in analysis.artefacts:
        title = artefact.fields.get("title")
        if (
            artefact.entry
            or artefact.id is None
            or not schemas.id_pattern(artefact.kind).match(artefact.id)
            or not isinstance(title, str)
            or not title
        ):
            continue  # an entry has no heading of its own; the schema reports the rest
        try:
            _front, body = markdown.split((root / artefact.path).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue  # the core reports a file it cannot read
        wanted = f"{artefact.id} — {title}"
        written = markdown.heading(body)
        if written == wanted:
            continue
        what = (
            "has no heading"
            if written is None
            else f"its heading, `# {written}`, is not its id and its front matter's title"
        )
        found.append(
            Finding(
                ERROR,
                artefact.location,
                f"{what}: {with_article(artefact.kind)} opens with `# {wanted}`, so what a "
                f"reader of its front matter sees is what the page shows — write the heading, "
                f"or change `title`",
            )
        )
    return found


# --- ids -----------------------------------------------------------------------------------


def _duplicates(analysis: Analysis) -> list[Finding]:
    """Two artefacts holding one id — compared by what each stands for (`identity`), as
    the stamp compares them, so `UC-0007` and `UC-007` share one."""
    holders: dict[str, list[Artefact]] = defaultdict(list)
    for artefact in analysis.artefacts:
        if artefact.id is not None:
            holders[identity(artefact.id)].append(artefact)
    found: list[Finding] = []
    for artefact_id, group in holders.items():
        # The holder spelling the id the one way first, so the finding lands on another.
        first, *later = sorted(group, key=lambda a: a.id != artefact_id)
        for other in later:
            written = (
                other.id if other.id == first.id else f"{other.id}, {first.id} spelt otherwise,"
            )
            found.append(
                Finding(
                    ERROR,
                    other.location,
                    f"the id {written} is also held by {first.location}: no two artefacts in "
                    f"the analysis share an id, and an id is never used again (DEC-001 point 3)",
                )
            )
    return found


# --- what an artefact names ----------------------------------------------------------------


def _references(analysis: Analysis) -> list[Finding]:
    """A use case's and a journey's actor, and a journey's steps: artefacts of the
    analysis, and in force for one in force — what the stamp refuses otherwise."""
    found: list[Finding] = []
    for artefact in analysis.artefacts:
        if artefact.kind not in (USE_CASE, JOURNEY):
            continue
        named: list[tuple[str, object, str]] = [("/actor", artefact.fields.get("actor"), ACTOR)]
        steps = artefact.fields.get("steps") if artefact.kind == JOURNEY else None
        if isinstance(steps, list):
            named += [(f"/steps/{i}", step, USE_CASE) for i, step in enumerate(steps)]
        in_force = not artefact.withdrawn
        for pointer, value, kind in named:
            if not isinstance(value, str) or not schemas.id_pattern(kind).match(value):
                continue  # the schema reports it
            problem = analysis.unfit(value, kind, in_force=in_force)
            if problem is None:
                continue
            if analysis.of(value, kind) is None:
                rule = f"what {with_article(artefact.kind)} names is in the analysis"
            else:
                rule = (
                    f"{with_article(artefact.kind)} in force rests only on artefacts in force, "
                    f"as the stamp requires — withdraw it too, or name another"
                )
            found.append(
                Finding(
                    ERROR, at(artefact.location, pointer), f"{problem}: {rule} (DEC-001 point 3)"
                )
            )
    return found


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


def _record_findings(
    root: Path, records: list[Path], analysis: Analysis
) -> tuple[list[Finding], list[Citation]]:
    """What the records' front matter breaks, and the evidence they cite, each id
    well-formed."""
    found: list[Finding] = []
    citations: list[Citation] = []
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
        found += _cited(rel, data.get("outcomes"), analysis)
        cited = _evidence_cited(rel, data.get("evidence"))
        found += _evidence_without_outcome(cited, data.get("outcomes"))
        citations += cited
    return found, citations


def _cited(rel: str, outcomes: object, analysis: Analysis) -> list[Finding]:
    """Each artefact a record's outcomes cite is one of the analysis — withdrawn ones
    included, since a record cites them too (DEC-001 point 6)."""
    if not isinstance(outcomes, dict):
        return []  # the schema reports it
    return [
        Finding(
            ERROR,
            at(rel, f"/outcomes/{cited}"),
            f"no artefact {cited} in the analysis: a record's outcomes cite artefacts of the "
            f"analysis by id, withdrawn ones included (DEC-001 point 6)",
        )
        for cited in outcomes
        if isinstance(cited, str)
        and any(schemas.id_pattern(kind).match(cited) for kind in KINDS)
        and analysis.find(cited) is None
    ]


# --- evidence a record cites (DEC-001 point 7) ---------------------------------------------


def _evidence_cited(rel: str, cited: object) -> list[Citation]:
    """The well-formed evidence ids a record cites, each where it is written; the
    schema reports the rest."""
    if not isinstance(cited, list):
        return []
    pattern = schemas.evidence_id_pattern()
    return [
        (at(rel, f"/evidence/{index}"), evidence_id)
        for index, evidence_id in enumerate(cited)
        if isinstance(evidence_id, str) and pattern.match(evidence_id)
    ]


def _evidence_without_outcome(cited: list[Citation], outcomes: object) -> list[Finding]:
    """Evidence supports an artefact's outcome and never replaces it: each artefact a
    record cites evidence for has its outcome in the record."""
    if not isinstance(outcomes, dict):
        return []  # the schema reports it
    found: list[Finding] = []
    for location, evidence_id in cited:
        artefact = evidence.artefact_of(evidence_id)
        if artefact in outcomes:
            continue
        found.append(
            Finding(
                ERROR,
                location,
                f"cites evidence {evidence_id} for {artefact}, to which it gives no outcome: "
                f"evidence supports a revalidation's outcome and never replaces it — give "
                f"{artefact} its outcome, or drop the citation (DEC-001 point 7)",
            )
        )
    return found


def _evidence_held(root: Path, cited: list[Citation]) -> tuple[str, list[Finding]]:
    """Whether the evidence point holds each cited id: a summary line, and a warning
    for each it does not — or one, when the point does not resolve. The evidence
    advises (DEC-001 point 7), so nothing here fails."""
    held = evidence.read_evidence(root)
    if not held.resolved:
        why = held.why.rstrip(".")
        return (
            f"evidence ({evidence.POINT}) unresolved: {len(cited)} citation(s) not checked.",
            [
                Finding(
                    WARNING,
                    evidence.POINT,
                    f"evidence unresolved — {why}{_inert(held)}. No record's citation can be "
                    f"checked until the point resolves; evidence advises, so nothing fails on "
                    f"it (DEC-001 point 7)",
                )
            ],
        )
    found = [
        Finding(
            WARNING,
            location,
            f"cites evidence {evidence_id}, which {evidence.POINT} does not hold"
            f"{_inert(held)}: cite an entry the point holds, by its `<artefact>@<commit>` "
            f"id, or drop the citation (DEC-001 point 7)",
        )
        for location, evidence_id in cited
        if evidence_id not in held.ids
    ]
    return (
        f"evidence ({evidence.POINT}): {len(held.ids)} held; {len(cited)} citation(s) checked.",
        found,
    )


def _inert(held: evidence.Evidence) -> str:
    """The fillers that went inert, whose entries the point lacks."""
    return f" — inert: {'; '.join(held.inert)}" if held.inert else ""
