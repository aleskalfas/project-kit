"""software-analysis' check of the analysis (DEC-001 points 2 to 6).

What is checked, each against the record's words:

- **Shape** (points 1 and 2). Every file in one of the places holds artefacts of
  that place's kind: the glossary and the actors are collection files, one
  entry per artefact keyed by its id; a use case and a journey are a document
  each. A file without front matter, one whose front matter does not parse, a
  collection file that is not one, or a use-case or journey file holding
  entries, is an error: what it holds cannot be read, its ids included, and
  an id is never used again (point 3) — the stamp then counts the number the
  file's name carries.
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
- **An id in a name alone** (point 3). A use case or journey whose file's name
  carries its number (`UC-007-<slug>.md`) and whose front matter gives no id:
  the stamp counts the number its name carries, so the front matter says it.
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
- **Evidence a record copies** (point 7). A record keeps each evidence entry
  it draws on whole, in the evidence point's entry shape: the record is
  history, and the point holds only what its fillers report now. From the
  record alone: an entry whose `id` is not its own `<artefact>@<commit>` is an
  error, and so is evidence for an artefact the record gives no outcome, since
  evidence supports an outcome and never replaces one; a `failed` result under
  `holds`, or a `passed` one under `code-regressed`, is a warning, since point
  7 pairs a passing result with holds and a failing one with a regression.
  Against the point as it resolves now (`_lib/evidence.py`), read only when
  some record copies evidence: a copy that differs from the entry the point
  holds under its id is a warning. The evidence advises, so an id the point no
  longer holds, or a point that does not resolve, says nothing: the record's
  copy is the evidence.

And two findings that never fail:

- **An open regression** (point 5), a report: a record's `code-regressed`
  artefact not revalidated since the record — its `at` on no later day (UTC)
  than the record's date, or no `at` at all. The defect the record names is
  still open, or its fix was never revalidated against the artefact. Derived
  from the records and the artefacts in the working tree each time, never
  kept in a ledger (COR-050 point 9).
- **`unanchored-because` beside anchors** (point 9), a warning: the reason
  says why an artefact has no anchors, so one with anchors carrying it says
  two things at once. The stamp refuses the pair; this catches a hand edit.

It reads the working tree — and, when a record copies evidence, the evidence
point — so the same tree gets the same answer as long as the evidence fillers
read the tree alone.

**Not here.** A number two branches took (point 3) is `pkit analysis
check-numbers`' (`_lib/numbers.py`): it reads the default branch, so it answers
about a change rather than the tree, and is not a validator (ADR-058 point 7).
The friction block — its shape, dead anchors, cycles, friction itself — is the
core's (`pkit validate`'s `friction` member and `pkit friction check`), which
also reports a front matter that does not parse, as this check does for a file
in its places. An unanchored artefact is the core's measure, never an error.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from ruamel.yaml.error import YAMLError

from _lib import backbone, evidence, markdown, schemas
from _lib.findings import ERROR, REPORT, WARNING, Finding, Outcome, at
from _lib.model import (
    ACTOR,
    COLLECTIONS,
    CONTAINER,
    ID_SHAPE,
    JOURNEY,
    KINDS,
    NOUN,
    NUMBERED,
    REVALIDATED_AT,
    REVALIDATIONS,
    UNANCHORED_BECAUSE,
    USE_CASE,
    Analysis,
    Artefact,
    Unreadable,
    id_in_name,
    identity,
    with_article,
)

#: Where in an artefact its artefact anchors sit.
ARTEFACT_ANCHORS = f"/{CONTAINER}/friction/anchors/artefact"

#: The outcome whose record stays open until the artefact is revalidated again.
REGRESSED = "code-regressed"

#: One evidence entry a record copies: where it is written, and the entry.
Copy = tuple[str, Mapping[str, Any]]

#: One record whose front matter was read: where it is, and its front matter.
Record = tuple[str, dict[str, object]]

#: The result each outcome is at odds with: DEC-001 point 7 pairs a passing
#: result with `holds` and a failing one with a regression.
AT_ODDS = {"holds": "failed", "code-regressed": "passed"}


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
    outcome.findings += _unreadable(analysis)
    outcome.findings += _own_fields(analysis)
    outcome.findings += _headings(root, analysis)
    outcome.findings += _duplicates(analysis)
    outcome.findings += _named_alone(analysis)
    outcome.findings += _references(analysis)
    outcome.findings += _actor_anchors(analysis)
    outcome.findings += _journey_anchors(analysis)
    outcome.findings += _unanchored_beside_anchors(analysis)
    record_findings, copies, read = _record_findings(root, records, analysis)
    outcome.findings += record_findings
    if copies:
        summary, compared = _copies_against_the_point(root, copies)
        outcome.summary.append(summary)
        outcome.findings += compared
    outcome.findings += _open_regressions(root, read, analysis)
    return outcome


def _counts(analysis: Analysis, records: int) -> str:
    kinds = ", ".join(f"{len(analysis.of_kind(k))} {NOUN[k]}(s)" for k in KINDS)
    return f"analysis at {analysis.location}: {kinds}; {records} revalidation record(s)."


# --- shape and required parts --------------------------------------------------------------


def _unreadable(analysis: Analysis) -> list[Finding]:
    """A file in one of the places whose front matter does not parse: nothing it holds
    can be read, its ids included (DEC-001 point 3)."""
    found: list[Finding] = []
    for path, reason in sorted(analysis.unreadable.items()):
        kind = analysis.files.get(path)
        holds = f"the {NOUN[kind]}s it holds" if kind in COLLECTIONS else "what it holds"
        named = id_in_name(path) if kind in NUMBERED else None
        counted = (
            f"; the stamp counts {named}, the number its name carries, as held" if named else ""
        )
        why = f" ({reason})" if reason else ""
        found.append(
            Finding(
                ERROR,
                path,
                f"its front matter does not parse{why}: {holds} cannot be read, ids included, "
                f"and an id is never used again (DEC-001 point 3){counted} — fix the front matter",
            )
        )
    return found


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


def _named_alone(analysis: Analysis) -> list[Finding]:
    """A use case or journey whose file's name carries its number and whose front matter
    gives no id: the stamp counts the number the name carries, so the front matter
    says the same (DEC-001 point 3)."""
    found: list[Finding] = []
    for artefact in analysis.artefacts:
        named = id_in_name(artefact.path)
        if artefact.entry or artefact.kind not in NUMBERED or artefact.id or named is None:
            continue
        found.append(
            Finding(
                ERROR,
                artefact.location,
                f"its name carries {named}, its front matter no id: the stamp counts {named} "
                f"as held, and an id is never used again — write `id: {named}` (DEC-001 point 3)",
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


def _unanchored_beside_anchors(analysis: Analysis) -> list[Finding]:
    """An artefact carrying the reason it has no anchors, and anchors (DEC-001 point 9)."""
    return [
        Finding(
            WARNING,
            at(artefact.location, f"/{UNANCHORED_BECAUSE}"),
            f"carries `{UNANCHORED_BECAUSE}` beside anchors: the reason says why it has none — "
            f"drop the reason, or the anchors (DEC-001 point 9)",
        )
        for artefact in analysis.artefacts
        if UNANCHORED_BECAUSE in artefact.fields and any(artefact.anchors.values())
    ]


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
) -> tuple[list[Finding], list[Copy], list[Record]]:
    """What the records' front matter breaks, the evidence entries they copy that
    are fit to compare with the point, and the records whose front matter was read."""
    found: list[Finding] = []
    copies: list[Copy] = []
    read: list[Record] = []
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
        record_found, record_copies = _evidence_in_record(
            rel, data.get("evidence"), data.get("outcomes")
        )
        found += record_found
        copies += record_copies
        read.append((rel, data))
    return found, copies, read


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


def _open_regressions(root: Path, records: list[Record], analysis: Analysis) -> list[Finding]:
    """Each `code-regressed` outcome whose artefact was not revalidated on a later day
    than its record: reported, never failed (DEC-001 point 5)."""
    found: list[Finding] = []
    for rel, data in records:
        day, outcomes = data.get("date"), data.get("outcomes")
        if not isinstance(day, str) or not isinstance(outcomes, dict):
            continue  # the schema reports it
        for cited, outcome in outcomes.items():
            artefact = analysis.find(cited) if isinstance(cited, str) else None
            if outcome != REGRESSED or artefact is None:
                continue
            last = _revalidated_on(root, artefact)
            if last is not None and last > day[:10]:
                continue
            since = f"last revalidated {last}" if last else "never revalidated"
            found.append(
                Finding(
                    REPORT,
                    at(rel, f"/outcomes/{cited}"),
                    f"{cited}'s regression is open: {since}, not since this record of "
                    f"{day[:10]}. Once the defect is fixed, revalidate {cited} against the fix "
                    f"— until then, what it describes is not what the code does (DEC-001 "
                    f"point 5)",
                )
            )
    return found


def _revalidated_on(root: Path, artefact: Artefact) -> str | None:
    """The day, `YYYY-MM-DD` in UTC, of the artefact's revalidation marker as the
    working tree holds it; `None` without one. The marker is inside the container,
    which the backbone's reading leaves out of an artefact's own fields, so it is
    read from the file."""
    try:
        front, _body = markdown.split((root / artefact.path).read_text(encoding="utf-8"))
        data = markdown.load(front) if front is not None else None
    except (OSError, UnicodeDecodeError, YAMLError):
        return None  # the core reports a file it cannot read
    node: object = data.get(artefact.id) if artefact.entry and isinstance(data, dict) else data
    for key in (CONTAINER, *REVALIDATED_AT):
        node = node.get(key) if isinstance(node, dict) else None
    return node[:10] if isinstance(node, str) and len(node) >= 10 else None


# --- evidence a record copies (DEC-001 point 7) --------------------------------------------


def _evidence_in_record(
    rel: str, copied: object, outcomes: object
) -> tuple[list[Finding], list[Copy]]:
    """What the record alone says of the evidence entries it copies — an entry whose id
    is not its own `<artefact>@<commit>`, evidence for an artefact without an outcome,
    a result the outcome is at odds with — and the copies fit to compare with the
    point: each in the entry's shape, its id its own pair. The schema reports an
    entry of another shape."""
    if not isinstance(copied, list):
        return [], []
    found: list[Finding] = []
    copies: list[Copy] = []
    for index, entry in enumerate(copied):
        if not schemas.is_evidence(entry):
            continue  # the schema reports it
        location = at(rel, f"/evidence/{index}")
        pair = f"{entry['artefact']}@{entry['commit']}"
        if entry["id"] != pair:
            found.append(
                Finding(
                    ERROR,
                    location,
                    f"the evidence entry {entry['id']} is for {pair} by its own `artefact` "
                    f"and `commit`: an entry's id is the pair it is for, `<artefact>@<commit>` "
                    f"— write `id: {pair}`, or correct the fields (DEC-001 point 7)",
                )
            )
            continue  # which of the two is meant is unknown, so nothing more is read from it
        copies.append((location, entry))
        if isinstance(outcomes, dict):
            found += _against_the_outcome(location, entry, outcomes)
    return found, copies


def _against_the_outcome(
    location: str, entry: Mapping[str, Any], outcomes: Mapping[Any, Any]
) -> list[Finding]:
    """Evidence supports an artefact's outcome and never replaces it: the artefact has
    its outcome in the record — an error otherwise — and a result the outcome is at
    odds with asks for attention."""
    artefact, result = entry["artefact"], entry["result"]
    if artefact not in outcomes:
        return [
            Finding(
                ERROR,
                location,
                f"cites evidence {entry['id']} for {artefact}, to which it gives no outcome: "
                f"evidence supports a revalidation's outcome and never replaces it — give "
                f"{artefact} its outcome, or drop the evidence (DEC-001 point 7)",
            )
        ]
    outcome = outcomes[artefact]
    if not isinstance(outcome, str) or AT_ODDS.get(outcome) != result:
        return []
    return [
        Finding(
            WARNING,
            location,
            f"cites a {result} result, {entry['id']}, for {artefact}, whose outcome is "
            f"{outcome}: a passing result supports holds and a failing one is a "
            f"regression's proof (DEC-001 point 7) — check {artefact}'s outcome against the "
            f"evidence",
        )
    ]


def _copies_against_the_point(root: Path, copies: list[Copy]) -> tuple[str, list[Finding]]:
    """Each copy against the entry the evidence point now holds under its id: a summary
    line, and a warning for each that differs. A record's copy is history and the
    evidence advises (DEC-001 point 7), so an id the point no longer holds, or a
    point that does not resolve, says nothing."""
    point = evidence.read_evidence(root)
    if not point.resolved:
        return (
            f"evidence ({evidence.POINT}) unresolved — {point.why.rstrip('.')}; "
            f"{len(copies)} copied entry(ies) not compared.",
            [],
        )
    found: list[Finding] = []
    for location, copy in copies:
        held = point.entries.get(str(copy["id"]))
        if held is None:
            continue
        differs = sorted(key for key in {*copy, *held} if copy.get(key) != held.get(key))
        if not differs:
            continue
        found.append(
            Finding(
                WARNING,
                location,
                f"its copy of {copy['id']} differs from the entry {evidence.POINT} now holds "
                f"under that id, in {', '.join(differs)}: the record keeps the evidence it "
                f"drew on, so either the copy strayed from its source — correct it — or the "
                f"result at that commit was reported again otherwise — revalidate "
                f"{copy['artefact']} against it (DEC-001 point 7)",
            )
        )
    return (
        f"evidence ({evidence.POINT}): {len(point.entries)} held; "
        f"{len(copies)} copied entry(ies) compared with it.",
        found,
    )
