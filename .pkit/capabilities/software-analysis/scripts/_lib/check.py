"""software-analysis' check of the analysis (DEC-001 points 2 to 6).

What is checked, each against the record's words:

- **Shape** (points 1 and 2). Every file in one of the places holds artefacts of
  that place's kind: the glossary is a collection file, one entry per term
  keyed by its id; an actor, a use case and a journey are a document each. A
  file without front matter, one whose front matter does not parse, a glossary
  that is no collection, or an actor, use-case or journey file holding
  entries, is an error: what it holds cannot be read, its ids included, and
  an id is never used again (point 3) — the stamp then counts the number a
  use case's or journey's file name carries.
- **Missing required parts** (points 1 and 3). Each artefact's own fields
  against its kind's companion schema — its id, its title or name, its
  status, its actor, its steps, its needs, its definition — and an entry's id
  against its kind's id. Unknown fields are refused, so a misspelt one is
  never silently ignored.
- **A placeholder left** (point 1). What the stamp leaves a person to write —
  an actor's need, a term's definition, a use case's goal and steps — is no
  part of the analysis until written: an own field — or the reason an actor
  or a term has no anchors, `unanchored-because` in its friction block —
  still holding a placeholder the templates or the skill's commands ever
  shipped, or a body — a collection entry's section, heading included —
  still holding one of the templates', is an error. Matched exactly against those texts
  (`_lib/placeholder.py`), so a capitalised one (`<Title>`) is caught and
  words of the artefact's own in angle brackets — code a body quotes — never
  are. A hint the stamp wrote as a placeholder, still in an own field, a body
  or a section, is an error too: a comment that opens with its mark, `<!--
  pkit:hint`, outside fenced code and code spans (`structure.hints`). The
  stamp writes one as the text of each field it leaves to fill, an actor's
  need and a term's definition, and as each body part. The message repeats
  the hint. Neither needs a rule.
- **A document's heading** is its id and its front matter's title — an
  actor's name — `# UC-NNN — <title>`, `# ACT-<slug> — <name>`: what a reader
  of the front matter alone sees — a data point publishing `{id, title,
  status}`, say — is what the page shows. The heading is read from the file
  discovery names.
- **Duplicate ids** (point 3). No two artefacts in the analysis share an id,
  a number spelt with other zeros included — as the stamp counts it held.
- **A name the id disagrees with** (point 3). A use case or journey whose
  file's name carries a number (`UC-007-<slug>.md`) its front matter does not
  give — no id, or another: the stamp counts the number its name carries, so
  the front matter says the same. An actor whose file is not named
  `<id>.md`: an actor's id names its file.
- **What a use case or journey names** (points 1, 3 and 4): its actor, a use
  case's other actors, and a journey's steps and the use cases outside it that
  a step relies on, are actors and use cases of the analysis; and one in force
  names none withdrawn. The stamp refuses the same (`Analysis.unfit`), so the
  check never accepts what the stamp would not write; a withdrawn artefact may
  name withdrawn ones. A use case's other actors leave out its own actor, and
  what a journey relies on leaves out its steps.
- **One actor's journey** (point 1): each step of a journey in force is a use
  case of the journey's actor, since a journey is one actor's path across use
  cases. The stamp refuses the same (`Analysis.another_actor`). A withdrawn
  journey is history, so its steps are not compared.
- **A use case anchors to each actor it involves** (point 4), as artefact
  anchors: its actor and each of its `other-actors`, so a changed actor flags
  it. A journey anchors to its actor the same way.
- **A journey's anchors match its steps and what it relies on** (point 4): the
  use cases among its artefact anchors are exactly those `steps` and
  `relies-on` list, so the friction check sees every use case it passes
  through or relies on, and the anchors and the lists cannot drift apart.
- **Revalidation records** (points 5 and 6): each record's front matter
  against its schema, and the artefacts its outcomes cite are artefacts of the
  analysis, withdrawn ones included. The records are not anchored artefacts:
  their folder is the capability's folder of held documents (COR-050 point 1),
  so the records are the files the backbone's reading says that folder holds —
  every Markdown file beneath it, from the working tree's one listing, so a
  draft git ignores is not checked. When the folder holds nothing because the
  backbone skipped it, the summary says so and leaves the finding to
  `pkit validate`.
- **Evidence a record copies** (point 7). A record keeps each evidence entry
  it draws on whole, in the evidence point's entry shape: the record is
  history, and the point holds only what its fillers report now. From the
  record alone: an entry whose `id` is not its own `<artefact>@<commit>#<check>`
  is an error, and so is evidence for an artefact the record gives no outcome,
  since evidence supports an outcome and never replaces one; so is a journey's
  entry naming as a step no use case of the analysis — withdrawn ones count,
  and the journey's steps as they stand now are never compared, since the
  record is history; a `failed` result under `holds`, or a `passed` one under
  `code-regressed`, is a warning, since point 7 pairs a passing result with
  holds and a failing one with a regression. Against the point as it resolves
  now (`_lib/evidence.py`), read only when some record copies evidence: a copy
  that differs from the entry the point holds under its id is a warning. The
  evidence advises, so an id the point no longer holds, or a point that does
  not resolve, says nothing: the record's copy is the evidence.
- **The point's own entries** (point 7), wherever the point is read: a
  capability's entry whose check opens with another name than the
  capability's, and any entry whose `id` is not its own three fields, are
  warnings. The opening name is a convention and never refused: the project
  replaces a capability's entry by writing one under that capability's check,
  so the project's entries are exempt from it. A project with no record that
  copies evidence never reads the point, and sees neither warning.

And a finding that never fails:

- **An open regression** (point 5), a report: a record's `code-regressed`
  artefact not revalidated since the record — its `at` on no later day (UTC)
  than the record's date, or no `at` at all. The defect the record names is
  still open, or its fix was never revalidated against the artefact. Derived
  from the records and the artefacts in the working tree each time, never
  kept in a ledger (COR-050 point 9).

Always, whatever any rule's status:

- **Each record's body against the record's structure** (point 1): a record
  is a held document, which no route leads from, so no rule binds on it, and
  the capability holds it to its structure itself, as its schema holds its
  front matter. The structure is the record kind's as the project's
  `project/structures.yaml` relabels it, and a record may predate a relabel,
  so a part is found by its shipped label too. A record is held to the
  structure declared now, the only one declared so far: holding it to the
  structure in force on its day comes with the first change to a structure
  (DEC-001's Implications). Its outcomes and gaps are read against its front
  matter.

And where the format rule binds, at its status:

- **Each artefact's body against its kind's structure** (point 1;
  RS-SAN-001): an artefact's body — a collection entry's section, as the
  backbone's reading spans it — against the structure its kind declares
  (`_lib/structure.py`): a declared part missing, out of order or empty,
  `None.` where the part may not read it, and a part or a front-matter field
  that does not hold the form its element names (`_lib/forms.py`), text of
  the `sentence` form in each item of a list too. A journey's steps read each
  use case's title. A part or a
  label a writer adds is never reported, though what it holds is content of
  the part it falls in, and a list form judges only the part's list items. A
  withdrawn artefact is never failed for a part it lacks or for a form, since
  either may have come after its withdrawal. A document's missing title
  heading is the heading check's, above, which holds it whatever the rule's
  status.
- **Where the rule binds.** `SAN` takes no scope, so its rules bind only
  through a set of the project's own that inherits it, as the backbone's one
  reading of where rules bind says (`pkit rule-sets reach`, COR-051 point 7).
  An artefact that reading leaves out is not checked. A glossary's head
  belongs to no term but is part of the term kind's structure, so it is held
  where the rule binds on a term of its file. The structure binds at the
  rule's status (COR-051 point 4): accepted, each departure is an error;
  under any other status the check reports none of it. On request
  (`preview`), a proposed rule is previewed as accepted, where `pkit
  rule-sets reach --preview` says it would bind: each departure is a report,
  its message opening `preview:`, so the exit is the normal check's. A
  superseded or withdrawn rule binds nothing in a preview either.
- **Never silent** (point 1): the summary counts the artefacts no rule of
  `SAN` binds on. Where it binds on none of the analysis, a finding says so,
  and why: a report while no rule of `SAN` is accepted, since none could
  bind, and a warning once one is.
- **A project's own structures** (point 1): the structure is the kind's as the
  project's `project/structures.yaml` relabels it, tightened by each of the
  project's groups that binds on the body (`_lib/project_structure.py`). A
  group binds on each artefact its rule binds on, as the backbone's reading
  of where a rule binds says (`pkit rule-sets reach`), which judges the
  rule's chain of fills too. A preview also reads where it would bind if
  every proposed rule were accepted (`--preview`), and takes from that
  reading only what holds under the preview alone: what a group finds there
  is a preview's report, and what binds still comes from the reading
  without the preview. A rule that binds on no artefact of its group's kind
  is reported. A withdrawn artefact may predate the project's changes: a
  relabelled part is found by its shipped label too, a closed list reports
  nothing, and a part a group adds is never missing from it. The record's
  kind takes no group: its schema refuses one, since no rule binds on a
  record.

And whatever any rule's status, the project's own structures themselves: a file
its schema or the shipped structure refuses, a tightening of the record's kind
among them, and a group naming no rule of the project's own rule sets, are
errors, the project mending its own file (COR-055 point 1). A group whose rule
is superseded or withdrawn binds nothing, and is reported.

It reads the working tree — and, when a record copies evidence, the evidence
point — so the same tree gets the same answer as long as the evidence fillers
read the tree alone.

**Not here.** A number two branches took (point 3) is `pkit analysis
check-numbers`' (`_lib/numbers.py`), and so is a use case's step or variant
renumbered or removed (`_lib/append_only.py`): each reads the default branch, so
it answers about a change rather than the tree, and is not a validator (ADR-058
point 7).
The friction block — its shape, dead anchors, cycles, friction itself — is the
core's (`pkit validate`'s `friction` member and `pkit friction check`), which
also reports a front matter that does not parse, as this check does for a file
in its places. An unanchored artefact is the core's measure, never an error,
and so is the reason an actor or a term is accepted with none: the block's
`unanchored-because`, which the measure lists apart and the core's validation
refuses beside anchors (COR-050 points 1, 8 and 12; DEC-001 point 9).
"""

from __future__ import annotations

import dataclasses
import re
from collections import defaultdict
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml.error import YAMLError

from _lib import backbone, evidence, markdown, project_structure, schemas, structure
from _lib.findings import ERROR, REPORT, WARNING, Finding, Outcome, at
from _lib.model import (
    ACTOR,
    CAPABILITY,
    COLLECTIONS,
    CONTAINER,
    FORMAT_RULE,
    ID_SHAPE,
    JOURNEY,
    KINDS,
    METHOD_SET,
    NOUN,
    NUMBERED,
    OTHER_ACTORS,
    RELIES_ON,
    REVALIDATED_AT,
    TERM,
    UNANCHORED_BECAUSE,
    USE_CASE,
    Analysis,
    Artefact,
    Unreadable,
    id_in_name,
    identity,
    one_actor,
    with_article,
)
from _lib.placeholder import IN_TEMPLATES, left_in

#: Where in an artefact its artefact anchors sit.
ARTEFACT_ANCHORS = f"/{CONTAINER}/friction/anchors/artefact"

#: Where in an artefact the reason it has no anchors sits: the core's key, in its
#: friction block (COR-050 point 1), which the stamp writes from a person's words.
REASON_POINTER = f"/{CONTAINER}/friction/{UNANCHORED_BECAUSE}"

#: The front-matter field a document's heading repeats after its id: an actor's name,
#: a use case's or journey's title. A term is an entry, with no heading of its own.
TITLED = {ACTOR: "name", TERM: "name", USE_CASE: "title", JOURNEY: "title"}

#: The outcome whose record stays open until the artefact is revalidated again.
REGRESSED = "code-regressed"

#: One evidence entry a record copies: where it is written, and the entry.
Copy = tuple[str, Mapping[str, Any]]

#: One record whose front matter was read: where it is, and its front matter.
Record = tuple[str, dict[str, object]]

#: The result each outcome is at odds with: DEC-001 point 7 pairs a passing
#: result with `holds` and a failing one with a regression.
AT_ODDS = {"holds": "failed", "code-regressed": "passed"}


def check(root: Path, *, preview: bool = False) -> Outcome:
    """Check the analysis in the working tree at `root` — with `preview`, a proposed
    format rule's structure too, as reports that never fail."""
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

    records = list(analysis.records)
    outcome.summary.append(_counts(analysis, len(records)))
    outcome.findings += [Finding(ERROR, s.path, s.why) for s in analysis.strays]
    outcome.findings += _unreadable(analysis)
    outcome.findings += _own_fields(analysis)
    outcome.findings += _placeholders(root, analysis)
    outcome.findings += _headings(root, analysis)
    outcome.findings += _duplicates(analysis)
    outcome.findings += _named_otherwise(analysis)
    outcome.findings += _references(analysis)
    outcome.findings += _lists_apart(analysis)
    outcome.findings += _journeys_of_one_actor(analysis)
    outcome.findings += _actor_anchors(analysis)
    outcome.findings += _journey_anchors(analysis)
    record_findings, copies, read = _record_findings(root, records, analysis)
    outcome.findings += record_findings
    if copies:
        summary, compared = _copies_against_the_point(root, copies)
        outcome.summary.append(summary)
        outcome.findings += compared
    outcome.findings += _open_regressions(root, read, analysis)
    own = _own(root)
    outcome.findings += _own_findings(analysis, own)
    summary, departing = _structure(root, analysis, preview=preview, own=own)
    outcome.summary.append(summary)
    outcome.findings += departing
    said, departing = _record_structure(root, read, own)
    outcome.summary += [said] if said else []
    outcome.findings += departing
    return outcome


def _counts(analysis: Analysis, records: int) -> str:
    kinds = ", ".join(f"{len(analysis.of_kind(k))} {NOUN[k]}(s)" for k in KINDS)
    line = f"analysis at {analysis.location}: {kinds}; {records} revalidation record(s)."
    if analysis.records_unheld is not None:
        line += (
            f" The records' folder holds nothing — {analysis.records_unheld}; `pkit validate` "
            f"says why."
        )
    return line


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


def _placeholders(root: Path, analysis: Analysis) -> list[Finding]:
    """What a person was left to write and has not (DEC-001 point 1): a placeholder the
    templates or the skill's commands shipped, still in an artefact's own fields or its
    block's reason for having no anchors, and one of the templates' still in its body —
    or its section of a collection file, heading included. Matched exactly
    (`_lib/placeholder.py`), so words of the
    artefact's own in angle brackets — `maps <user id> to a session`, code a body
    quotes — are never taken for one. A hint left in a field, a body or a section is one
    too, found by its mark (`structure.hint_in`, `_hints_left`), the message repeating
    it."""
    texts: dict[str, str | None] = {}
    found: list[Finding] = []
    for artefact in analysis.artefacts:
        written = list(_strings(artefact.fields))
        if artefact.unanchored_because is not None:
            written.append((REASON_POINTER, artefact.unanchored_because))
        for pointer, text in written:
            said = structure.hint_in(text)
            if said is not None:
                found.append(
                    Finding(
                        ERROR,
                        at(artefact.location, pointer),
                        f"still holds its hint: write in its place what it asks for, and delete "
                        f"the hint (DEC-001 point 1). The hint: {said}",
                    )
                )
                continue
            held = left_in(text)
            if held:
                found.append(
                    Finding(
                        ERROR,
                        at(artefact.location, pointer),
                        f"still holds the placeholder {held[0]!r}: write in its place what "
                        f"it asks for — until then it says nothing of the {NOUN[artefact.kind]} "
                        f"(DEC-001 point 1)",
                    )
                )
        if artefact.path not in texts:
            texts[artefact.path] = _read(root / artefact.path)
        text = texts[artefact.path]
        if text is None:
            continue  # the core reports a file it cannot read
        where = "its section" if artefact.entry else "its body"
        found += _hints_left(text, artefact, where)
        _front, body = markdown.split(text)
        if artefact.entry and artefact.id is not None:
            body = markdown.section(body, artefact.id)
        held = left_in(body, IN_TEMPLATES)
        if not held:
            continue
        more = f" and {len(held) - 1} more" if len(held) > 1 else ""
        found.append(
            Finding(
                ERROR,
                artefact.location,
                f"{where} still holds the template's placeholder {held[0]!r}{more}: write in "
                f"each one's place what it asks for, or remove it (DEC-001 point 1)",
            )
        )
    return found


def _hints_left(text: str, artefact: Artefact, where: str) -> list[Finding]:
    """A hint the stamp wrote as a part's placeholder, still in the artefact's body or its
    section, outside fenced code and code spans (`structure.hints`): an error whatever
    the format rule's status, as any placeholder is, the message repeating the first
    hint (DEC-001 point 1). An entry is read within the span the backbone gives it, and
    one with no section holds no hint."""
    if artefact.entry:
        if artefact.span is None:
            return []
        lines = structure.span_lines(text, artefact.span)
    else:
        lines = structure.body_lines(text)
    left = structure.hints(lines)
    if not left:
        return []
    (line, said), more = left[0], len(left) - 1
    others = f", and {more} more below it" if more else ""
    return [
        Finding(
            ERROR,
            artefact.location,
            f"{where} still holds a hint at line {line}{others}: write in its place what it "
            f"asks for, and delete the hint (DEC-001 point 1). The hint: {said}",
        )
    ]


def _strings(value: object, pointer: str = "") -> list[tuple[str, str]]:
    """Each text in `value`, with the JSON Pointer to it."""
    if isinstance(value, str):
        return [(pointer, value)]
    if isinstance(value, Mapping):
        items: Iterable[tuple[object, object]] = value.items()
    elif isinstance(value, list):
        items = enumerate(value)
    else:
        return []
    return [
        found
        for key, item in items
        for found in _strings(item, f"{pointer}/{str(key).replace('~', '~0').replace('/', '~1')}")
    ]


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _headings(root: Path, analysis: Analysis) -> list[Finding]:
    """A document's heading reads `<id> — <title>` — an actor's `<id> — <name>` — as its
    front matter gives them."""
    found: list[Finding] = []
    for artefact in analysis.artefacts:
        field = TITLED[artefact.kind]
        title = artefact.fields.get(field)
        if (
            artefact.entry
            or artefact.id is None
            or not schemas.id_pattern(artefact.kind).match(artefact.id)
            or not isinstance(title, str)
            or not title
        ):
            continue  # a term's entry has no heading of its own; the schema reports the rest
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
            else f"its heading, `# {written}`, is not its id and its front matter's {field}"
        )
        found.append(
            Finding(
                ERROR,
                artefact.location,
                f"{what}: {with_article(artefact.kind)} opens with `# {wanted}`, so what a "
                f"reader of its front matter sees is what the page shows — write the heading, "
                f"or change `{field}`",
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


def _named_otherwise(analysis: Analysis) -> list[Finding]:
    """A use case or journey whose file's name carries a number its front matter does
    not give — no id, or another: the stamp counts the number the name carries, and
    every number a history gave a file, so the name and the id say the same (DEC-001
    point 3). An id spelt with other zeros is the same id; the id check reports it."""
    found: list[Finding] = []
    for artefact in analysis.artefacts:
        named = id_in_name(artefact.path)
        if artefact.entry or artefact.kind not in NUMBERED or named is None:
            continue
        if artefact.id is None:
            message = (
                f"its name carries {named}, its front matter no id: the stamp counts {named} "
                f"as held, and an id is never used again — write `id: {named}` (DEC-001 point 3)"
            )
        elif identity(artefact.id) != named:
            message = (
                f"its name carries {named}, its front matter {artefact.id}: the stamp counts "
                f"both as held, and an artefact holds one id — name the file after its id, or "
                f"correct `id` (DEC-001 point 3)"
            )
        else:
            continue
        found.append(Finding(ERROR, artefact.location, message))
    return found + _actors_named_otherwise(analysis)


def _actors_named_otherwise(analysis: Analysis) -> list[Finding]:
    """An actor whose file's name is not its id: an actor's id names its file (DEC-001
    point 3), as the stamp names it, so the two say the same. An actor with no id, or
    one that is no actor id, is the schema's to report."""
    found: list[Finding] = []
    pattern = schemas.id_pattern(ACTOR)
    for artefact in analysis.of_kind(ACTOR):
        if artefact.entry or artefact.id is None or not pattern.match(artefact.id):
            continue
        name = artefact.path.rsplit("/", 1)[-1]
        if name == f"{artefact.id}.md":
            continue
        found.append(
            Finding(
                ERROR,
                artefact.location,
                f"its name is {name}, its front matter's id {artefact.id}: an actor's id names "
                f"its file — name the file {artefact.id}.md, or correct `id` (DEC-001 point 3)",
            )
        )
    return found


# --- what an artefact names ----------------------------------------------------------------


#: What each kind of artefact names in its front matter, beside its actor: each field
#: listing artefacts, and the kind it lists (DEC-001 point 4).
LISTED = {
    USE_CASE: ((OTHER_ACTORS, ACTOR),),
    JOURNEY: (("steps", USE_CASE), (RELIES_ON, USE_CASE)),
}


def _references(analysis: Analysis) -> list[Finding]:
    """A use case's and a journey's actor, a use case's other actors, and a journey's
    steps and the use cases it relies on: artefacts of the analysis, and in force for
    one in force — what the stamp refuses otherwise."""
    found: list[Finding] = []
    for artefact in analysis.artefacts:
        if artefact.kind not in (USE_CASE, JOURNEY):
            continue
        named: list[tuple[str, object, str]] = [("/actor", artefact.fields.get("actor"), ACTOR)]
        for field, kind in LISTED[artefact.kind]:
            listed = artefact.fields.get(field)
            if isinstance(listed, list):
                named += [(f"/{field}/{i}", value, kind) for i, value in enumerate(listed)]
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


def _journeys_of_one_actor(analysis: Analysis) -> list[Finding]:
    """A journey in force whose step is a use case of another actor than the journey's:
    a journey is one actor's path across use cases (DEC-001 point 1), and the stamp
    refuses the same (`Analysis.another_actor`). A withdrawn journey is history, and
    its steps' actors may have changed since. A journey whose actor is no actor of the
    analysis is `_references`' to report, and a step that is no use case of it too."""
    found: list[Finding] = []
    for journey in analysis.of_kind(JOURNEY):
        actor, steps = journey.fields.get("actor"), journey.fields.get("steps")
        if (
            journey.withdrawn
            or not isinstance(actor, str)
            or analysis.of(actor, ACTOR) is None
            or not isinstance(steps, list)
        ):
            continue
        for index, step in enumerate(steps):
            other = analysis.another_actor(step, actor) if isinstance(step, str) else None
            if other is None:
                continue
            found.append(
                Finding(
                    ERROR,
                    at(journey.location, f"/steps/{index}"),
                    f"{one_actor(index + 1, step, other, actor)} — name one of {actor}'s in "
                    f"its place, or correct the use case's actor (DEC-001 point 1)",
                )
            )
    return found


def _lists_apart(analysis: Analysis) -> list[Finding]:
    """A use case's other actors leave out its own actor, and the use cases a journey
    relies on outside it leave out its steps (DEC-001 point 4): each list names what
    the use case or journey does not name already. The stamp refuses the same."""
    found: list[Finding] = []
    for artefact in analysis.artefacts:
        if artefact.kind == USE_CASE:
            field, own = OTHER_ACTORS, [artefact.fields.get("actor")]
            what = "the use case's own actor"
            why = "the other actors are those who take part beside the actor whose goal it is"
        elif artefact.kind == JOURNEY:
            steps = artefact.fields.get("steps")
            field, own = RELIES_ON, steps if isinstance(steps, list) else []
            what = "a step of the journey"
            why = "it lists the use cases outside the journey that a step relies on"
        else:
            continue
        listed = artefact.fields.get(field)
        for index, value in enumerate(listed if isinstance(listed, list) else []):
            if isinstance(value, str) and value in own:
                found.append(
                    Finding(
                        ERROR,
                        at(artefact.location, f"/{field}/{index}"),
                        f"`{field}` names {value}, {what}: {why} "
                        f"— remove it from `{field}` (DEC-001 point 4)",
                    )
                )
    return found


# --- anchors -------------------------------------------------------------------------------


def _actor_anchors(analysis: Analysis) -> list[Finding]:
    """Each actor a use case involves, its actor and each of its other actors, and a
    journey's actor, among its artefact anchors (DEC-001 point 4), so a changed actor
    flags every use case and journey that rests on it."""
    pattern = schemas.id_pattern(ACTOR)
    found: list[Finding] = []
    for artefact in analysis.artefacts:
        if artefact.kind not in (USE_CASE, JOURNEY):
            continue
        actors: list[tuple[str, object]] = [("its actor", artefact.fields.get("actor"))]
        others = artefact.fields.get(OTHER_ACTORS) if artefact.kind == USE_CASE else None
        if isinstance(others, list):
            actors += [("each other actor it involves", other) for other in others]
        anchored = artefact.anchored_to("artefact")
        for which, actor in actors:
            if not isinstance(actor, str) or not pattern.match(actor):
                continue  # the schema reports it
            if actor not in anchored:
                found.append(
                    Finding(
                        ERROR,
                        at(artefact.location, ARTEFACT_ANCHORS),
                        f"{with_article(artefact.kind)} anchors to {which}, so a changed actor "
                        f"flags it: add {actor} to its artefact anchors (DEC-001 point 4)",
                    )
                )
    return found


def _journey_anchors(analysis: Analysis) -> list[Finding]:
    """A journey's use-case anchors are exactly the use cases of its `steps` and its
    `relies-on` (DEC-001 point 4): the two lists are the source, and the stamp writes
    the anchors from them."""
    pattern = schemas.id_pattern(USE_CASE)
    found: list[Finding] = []
    for journey in analysis.of_kind(JOURNEY):
        steps = journey.fields.get("steps")
        if not isinstance(steps, list):
            continue  # the schema reports it
        relies_on = journey.fields.get(RELIES_ON)
        listed = [*steps, *(relies_on if isinstance(relies_on, list) else [])]
        expected = _unique(s for s in listed if isinstance(s, str) and pattern.match(s))
        anchored = _unique(a for a in journey.anchored_to("artefact") if pattern.match(a))
        if expected and set(expected) != set(anchored):
            found.append(
                Finding(
                    ERROR,
                    at(journey.location, ARTEFACT_ANCHORS),
                    f"its use-case anchors ({', '.join(anchored) or 'none'}) do not match its "
                    f"steps and the use cases it relies on ({', '.join(expected)}): the anchors "
                    f"are written from `steps` and `relies-on`, so the friction check sees "
                    f"every use case it passes through or relies on — anchor exactly "
                    f"[{', '.join(expected)}] (DEC-001 point 4)",
                )
            )
    return found


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))


# --- revalidation records ------------------------------------------------------------------


def _record_findings(
    root: Path, records: list[str], analysis: Analysis
) -> tuple[list[Finding], list[Copy], list[Record]]:
    """What the records' front matter breaks, the evidence entries they copy that
    are fit to compare with the point, and the records whose front matter was read.
    `records` are repository-relative, as the backbone lists them held."""
    found: list[Finding] = []
    copies: list[Copy] = []
    read: list[Record] = []
    for rel in records:
        try:
            front, _body = markdown.split((root / rel).read_text(encoding="utf-8"))
            data = markdown.load(front) if front is not None else None
            times = markdown.unquoted_times(front) if front is not None else {}
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
            if pointer in times:
                message = _unquoted_time(pointer, times[pointer])
            found.append(Finding(ERROR, at(rel, pointer), message))
        found += _cited(rel, data.get("outcomes"), analysis)
        record_found, record_copies = _evidence_in_record(
            rel, data.get("evidence"), data.get("outcomes"), analysis
        )
        found += record_found
        copies += record_copies
        read.append((rel, data))
    return found, copies, read


#: Where in a record a time of day is written: a source's version, the time its text
#: was read.
_A_TIME = re.compile(r"^/reviewed-against/[0-9]+/version$")


def _unquoted_time(pointer: str, read_as: str) -> str:
    """Why a time written unquoted fails its record's schema: YAML reads it as a time,
    not as the text written, and gives it back otherwise. Where the field holds a time,
    the message gives its form. Elsewhere it gives the field's form in the schema."""
    said = (
        f"YAML reads this value as a time, since it is not quoted, and gives it back as "
        f"{read_as!r}, not as written: quote it"
    )
    if _A_TIME.match(pointer):
        return (
            f"{said}, a time in UTC such as "
            f'"2026-01-05T10:00:00Z", as a revalidation\'s `at` is written '
            f"(`schemas/revalidation-record.schema.json`)"
        )
    return f"{said}, in the form the field takes (`schemas/revalidation-record.schema.json`)"


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
    rel: str, copied: object, outcomes: object, analysis: Analysis
) -> tuple[list[Finding], list[Copy]]:
    """What the record alone says of the evidence entries it copies — an entry whose id
    is not its own `<artefact>@<commit>#<check>`, evidence for an artefact without an
    outcome, a journey's step that is no use case of the analysis, a result the outcome
    is at odds with — and the copies fit to compare with the point: each in the entry's
    shape, its id its own three fields. The schema reports an entry of another shape."""
    if not isinstance(copied, list):
        return [], []
    found: list[Finding] = []
    copies: list[Copy] = []
    for index, entry in enumerate(copied):
        if not schemas.is_evidence(entry):
            continue  # the schema reports it
        location = at(rel, f"/evidence/{index}")
        own = evidence.own_id(entry)
        if entry["id"] != own:
            found.append(
                Finding(
                    ERROR,
                    location,
                    f"the evidence entry {entry['id']} is for {own} by its own `artefact`, "
                    f"`commit` and `check`: an entry's id is the three parts it is for, "
                    f"`<artefact>@<commit>#<check>` — write `id: {own}`, or correct the "
                    f"fields (DEC-001 point 7)",
                )
            )
            continue  # which of the two is meant is unknown, so nothing more is read from it
        copies.append((location, entry))
        found += _journey_steps(location, entry, analysis)
        if isinstance(outcomes, dict):
            found += _against_the_outcome(location, entry, outcomes)
    return found, copies


def _journey_steps(location: str, entry: Mapping[str, Any], analysis: Analysis) -> list[Finding]:
    """A journey's evidence names the use cases its run passed through: each a use case
    of the analysis, withdrawn ones included. A record is history, so the steps are
    never compared with the journey's as they stand now."""
    if not schemas.id_pattern(JOURNEY).match(entry["artefact"]):
        return []
    return [
        Finding(
            ERROR,
            f"{location}/steps/{index}",
            f"no use case {step} in the analysis: a journey's evidence names the use cases "
            f"its run passed through, by id, withdrawn ones included (DEC-001 points 4 and 6; "
            f"`schemas/revalidation-evidence.schema.json`)",
        )
        for index, step in enumerate(entry.get("steps") or [])
        if analysis.of(step, USE_CASE) is None
    ]


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
    """The evidence point, read now: what its own entries break (`_entries_of_the_point`),
    then each copy against the entry it now holds under its id — a summary line, and a
    warning for each that differs. A record's copy is history and the evidence advises
    (DEC-001 point 7), so an id the point no longer holds, or a point that does not
    resolve, says nothing."""
    point = evidence.read_evidence(root)
    if not point.resolved:
        return (
            f"evidence ({evidence.POINT}) unresolved — {point.why.rstrip('.')}; "
            f"{len(copies)} copied entry(ies) not compared.",
            [],
        )
    found = _entries_of_the_point(point)
    for location, copy in copies:
        entry = point.entries.get(str(copy["id"]))
        if entry is None:
            continue
        held = entry.value
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


def _entries_of_the_point(point: evidence.Evidence) -> list[Finding]:
    """Each entry the point holds, as its fillers report it now: one whose `id` is not
    its own three fields, and a capability's whose check opens with another name than
    the capability's own. Both only warn: the evidence advises, and the opening name is
    a convention, never refused — the project replaces a capability's entry by writing
    one under that capability's check, so the project's entries are exempt from it
    (DEC-001 point 7)."""
    found: list[Finding] = []
    for entry_id, held in point.entries.items():
        location = f"{evidence.POINT}#{entry_id}"
        supplier = repr(held.origin) if held.from_capability else "the project's filler"
        own = evidence.own_id(held.value)
        if entry_id != own:
            found.append(
                Finding(
                    WARNING,
                    location,
                    f"{supplier} supplies it for {own} by its own `artefact`, `commit` and "
                    f"`check`: an entry's id is the three parts it is for, "
                    f"`<artefact>@<commit>#<check>`, and a record that copies it is held to "
                    f"that — its filler writes `id: {own}`, or corrects the fields (DEC-001 "
                    f"point 7)",
                )
            )
        check = str(held.value["check"])
        if held.from_capability and evidence.opening(check) != held.origin:
            found.append(
                Finding(
                    WARNING,
                    location,
                    f"{supplier} reports it under the check {check}, which opens with "
                    f"{evidence.opening(check)!r}: a capability's checks open with its own "
                    f"name, so two fillers' results for one artefact at one commit stand "
                    f"side by side and only a real double claim collides — {supplier} "
                    f"names its checks {held.origin}.… (DEC-001 point 7)",
                )
            )
    return found


# --- each body against its kind's structure (DEC-001 point 1; RS-SAN-001) ------------------

#: What a preview finding's message opens with: a finding of a rule not yet accepted,
#: at the severity that reports without judging (DEC-001 point 1; COR-055 point 4).
PREVIEW = "preview: "

#: The statuses that decide whether the structure binds (COR-051 point 4).
ACCEPTED, PROPOSED = "accepted", "proposed"
SUPERSEDED, WITHDRAWN = "superseded", "withdrawn"


#: The format rule and the method set as the backbone's reading of where rules bind
#: cites them: with the capability's name in front (COR-051 point 6).
CITED_FORMAT_RULE = f"{CAPABILITY}:{FORMAT_RULE}"
CITED_SET = f"{CAPABILITY}:{METHOD_SET}"


class _Reach:
    """The backbone's reading of where rules bind, read at most once with the preview and
    once without, whoever asks: the format rule, the method set's other rules and the
    project's groups all read the one answer (COR-051 point 7; ADR-057 point 2). A
    reading that fails raises Unreadable each time it is asked for. It is called as
    `backbone.reach` is, so it stands in for it, and reads at the root it was made for."""

    def __init__(self, root: Path, reach: Callable[..., Mapping[str, Mapping[str, bool]]]):
        self.root = root
        self.reach = reach
        self.answers: dict[bool, Mapping[str, Mapping[str, bool]] | Unreadable] = {}

    def __call__(self, _root: Path, *, preview: bool = False) -> Mapping[str, Mapping[str, bool]]:
        if preview not in self.answers:
            try:
                self.answers[preview] = self.reach(self.root, preview=preview)
            except Unreadable as exc:
                self.answers[preview] = exc
        answer = self.answers[preview]
        if isinstance(answer, Unreadable):
            raise answer
        return answer


def _structure(
    root: Path,
    analysis: Analysis,
    *,
    preview: bool,
    own: project_structure.Own | None = None,
    reach: Callable[..., Mapping[str, Mapping[str, bool]]] = backbone.reach,
) -> tuple[str, list[Finding]]:
    """Each artefact's body and each glossary's head against the structure its kind
    declares, where the format rule binds and at its status (DEC-001 point 1): an error
    where the rule is accepted, a report opening `preview:` where it is proposed and a
    preview is asked for, and nothing otherwise. Where the rule binds is the backbone's
    one answer (`reach`): `SAN` takes no scope, so its rules bind only through a set of
    the project's own (COR-051 point 7). A preview reads where the proposed rule would
    bind (`--preview`). A glossary's head is held where the rule binds on a term of its
    file. The structure is the kind's as the project's own structures, `own`, relabel
    it, tightened by each of the project's groups that binds on the body (`_bound`). In
    a preview, a body is also held to the groups that bind on it only under the preview,
    and what that adds to what the body breaks is a preview's report, so the findings
    are the normal check's and the exit is too.

    Never silent (`_unbound`): the summary counts the artefacts no rule of `SAN` binds
    on, and where it binds on none of the analysis, a finding says so. Returns the
    summary's line about it, and the findings."""
    reached = _Reach(root, reach)
    unbound, silence = _unbound(analysis, reached)
    rules = analysis.method_rules
    status = None if rules is None else rules.get(FORMAT_RULE)
    if status == ACCEPTED:
        severity, label = ERROR, ""
    elif status == PROPOSED and preview:
        severity, label = REPORT, PREVIEW
    else:
        return unchecked(status, rules is None, preview) + unbound, silence
    declaration = _shown(structure.KINDS_FILE, root)
    try:
        kinds = structure.read_kinds()
    except structure.Unreadable as exc:
        return (
            f"structure ({FORMAT_RULE}, {status}): not checked — the declaration cannot be "
            f"read.{unbound}",
            [
                *silence,
                Finding(
                    severity,
                    declaration,
                    f"{label}the kinds' structures cannot be read: {exc}. No artefact's body is "
                    f"checked against its structure until they can: the file is {CAPABILITY}'s "
                    f"own, never the project's to edit — restore it as the capability ships it "
                    f"(DEC-001 point 1)",
                ),
            ],
        )
    own = own if own is not None else project_structure.read(root, kinds)
    if own.problems:
        return (
            f"structure ({FORMAT_RULE}, {status}): not checked — the project's own structures, "
            f"{project_structure.FILE}, cannot be read; the findings there say why.{unbound}",
            silence,
        )
    try:
        at = reached(root, preview=status != ACCEPTED) if analysis.artefacts else {}
    except Unreadable as exc:
        # Under an accepted rule, `_unbound` may have said so already, as an error.
        told = status == ACCEPTED and any(f.severity == ERROR for f in silence)
        said = [] if told else [_unreadable_reach(exc, analysis, preview=status != ACCEPTED)]
        return (
            f"structure ({FORMAT_RULE}, {status}): not checked — where the rule binds cannot "
            f"be read.{unbound}",
            silence + said,
        )
    binding = frozenset(location for location, bound in at.items() if CITED_FORMAT_RULE in bound)
    kinds = {name: project_structure.relabelled(kind, own) for name, kind in kinds.items()}
    bound = _bound(root, analysis, own, preview=preview, reach=reached, binding=binding)
    found: list[Finding] = []
    previewing: list[Finding] = []  # a group's that binds only because of the preview
    texts: dict[str, str | None] = {}
    titles = _titles(analysis)
    checked = 0
    for artefact in analysis.artefacts:
        kind = kinds.get(artefact.kind)
        if artefact.location not in binding or kind is None:
            continue
        text = _cached(root, artefact.path, texts)
        if text is None:
            continue  # the core reports a file it cannot read
        checked += 1
        held_to = bound.kind(kind, artefact.location, as_written=artefact.withdrawn)
        departs = _artefact_structure(artefact, held_to, text, titles)
        found += [finding for finding, _key in departs]
        fuller = bound.kind(kind, artefact.location, as_written=artefact.withdrawn, preview=True)
        if fuller != held_to:
            seen = {key for _finding, key in departs}
            previewing += [
                finding
                for finding, key in _artefact_structure(
                    artefact, fuller, text, titles, fields=False
                )
                if key not in seen
            ]
    heads, headed = _heads(root, analysis, kinds, texts, binding)
    found += heads
    checked += headed
    found = [Finding(severity, f.location, label + f.message) for f in found]
    found += [Finding(REPORT, f.location, PREVIEW + f.message) for f in previewing]
    bound_found = [
        Finding(severity, f.location, label + f.message) if f.severity == ERROR else f
        for f in bound.findings
    ]
    departing = len({f.location.split(":/", 1)[0] for f in found})
    previewed = ", previewed as accepted" if label else ""
    never = ", reported and never failing" if label else ""
    where = "would bind, as `pkit rule-sets reach --preview` reads it" if label else "binds"
    return (
        f"structure ({FORMAT_RULE}, {status}{previewed}): {checked} artefact(s) and file "
        f"head(s) checked, where the rule {where}, against the structure their kind declares "
        f"in {declaration}{bound.said}; {departing} of them departing from it{never}.{unbound}",
        silence + found + bound_found,
    )


def _unbound(analysis: Analysis, reached: _Reach) -> tuple[str, list[Finding]]:
    """What the summary says of the artefacts no rule of `SAN` binds on, and, where it
    binds on none of the analysis, the finding that says so, and why (DEC-001 point 1):
    a report while no rule of `SAN` is accepted, since none could bind, and a warning once
    one is. Where `SAN` binds is the backbone's one answer, read only once a rule of `SAN`
    is accepted. Which sets the project lacks, or which pin holds a rule back, the
    capability never works out itself: the finding names each cause the answer cannot
    tell apart, and the fix (COR-051 point 7)."""
    total = len(analysis.artefacts)
    if not total or analysis.method_rules is None:
        return "", []
    accepted = {
        f"{CAPABILITY}:{rule}"
        for rule, status in analysis.method_rules.items()
        if status == ACCEPTED
    }
    if not accepted:
        return (
            f" No rule of {CITED_SET} binds on any of the {total} artefact(s), since none is "
            f"accepted.",
            [
                Finding(
                    REPORT,
                    analysis.location or ".",
                    f"no rule of {CITED_SET} binds on any of the analysis's {total} "
                    f"artefact(s): none is accepted, so none binds whatever the project's rule "
                    f"sets say (COR-051 point 4). Once one is, it binds only through a set of the "
                    f"project's own whose scope selects the analysis, such as by the "
                    f"capability's types, and that inherits {CITED_SET} (COR-051 point 7; "
                    f"DEC-001 point 1)",
                )
            ],
        )
    try:
        at = reached(reached.root, preview=False)
    except Unreadable as exc:
        return "", [_unreadable_reach(exc, analysis, preview=False)]
    bound = sum(
        1 for artefact in analysis.artefacts if accepted & set(at.get(artefact.location) or ())
    )
    if bound == total:
        return "", []
    said = f" No rule of {CITED_SET} binds on {total - bound} of the {total} artefact(s)."
    if bound:
        return said, []
    return said, [
        Finding(
            WARNING,
            analysis.location or ".",
            f"no rule of {CITED_SET} binds on any of the analysis's {total} artefact(s), as "
            f"`pkit rule-sets reach` reads it, so none is held to its structure: no set of the "
            f"project's own whose scope selects them inherits {CITED_SET}, or a pin behind "
            f"its set holds it back (COR-051 point 7). Write a set of your own whose scope "
            f"selects the analysis, such as by the capability's types, and that inherits "
            f"{CITED_SET} at its current major, or review the new major and update the pin "
            f"(DEC-001 point 1)",
        )
    ]


def _unreadable_reach(exc: Unreadable, analysis: Analysis, *, preview: bool) -> Finding:
    """Where `SAN`'s rules bind cannot be read, said at the analysis: an error without the
    preview, so the normal check fails as it would, and a preview's report with it, which
    never fails."""
    location = analysis.location or "."
    if preview:
        return Finding(
            REPORT,
            location,
            f"{PREVIEW}where {FORMAT_RULE} would bind cannot be read: {exc}. No artefact is "
            f"previewed against its structure until it can (COR-051 point 7)",
        )
    return Finding(
        ERROR,
        location,
        f"where the rules of {CITED_SET} bind cannot be read: {exc}. No artefact is held to "
        f"its structure until it can (COR-051 point 7)",
    )


def _record_structure(
    root: Path, records: list[Record], own: project_structure.Own | None = None
) -> tuple[str | None, list[Finding]]:
    """Each revalidation record's body and front matter against the record's structure, as
    the project's own structures relabel it, always, as its schema checks its front
    matter (DEC-001 point 1). A record is a held document, which no route leads from, so
    no rule binds on one and the capability holds it itself. A record may predate a
    relabel, so a part is found by its shipped label too. Returns the summary's line
    about it, none where there is no record, and the findings, each an error."""
    if not records:
        return None, []
    declaration = _shown(structure.KINDS_FILE, root)
    try:
        kinds = structure.read_kinds()
    except structure.Unreadable as exc:
        return (
            "records' structure: not checked — the declaration cannot be read.",
            [
                Finding(
                    ERROR,
                    declaration,
                    f"the kinds' structures cannot be read: {exc}. No revalidation record is "
                    f"checked against its structure until they can: the file is {CAPABILITY}'s "
                    f"own, never the project's to edit — restore it as the capability ships it "
                    f"(DEC-001 point 1)",
                )
            ],
        )
    shipped = kinds.get(structure.RECORD)
    if shipped is None:
        return f"records' structure: not checked — {declaration} declares no record kind.", []
    own = own if own is not None else project_structure.read(root, kinds)
    if own.problems:
        return (
            f"records' structure: not checked — the project's own structures, "
            f"{project_structure.FILE}, cannot be read; the findings there say why.",
            [],
        )
    record = dataclasses.replace(project_structure.relabelled(shipped, own), as_written=True)
    subject = "a revalidation record"
    found: list[Finding] = []
    texts: dict[str, str | None] = {}
    checked = 0
    for rel, data in records:
        text = _cached(root, rel, texts)
        if text is None:
            continue
        checked += 1
        found += [
            Finding(ERROR, rel, _departure_message(d, record.sections, subject, RECORD_POINT))
            for d in structure.departures(structure.body_lines(text), record, fields=data)
        ]
        found += _field_findings(rel, data, record, subject, RECORD_POINT)
    departing = len({f.location.split(":/", 1)[0] for f in found})
    return (
        f"records' structure, held always: {checked} revalidation record(s) checked against "
        f"the structure their kind declares in {declaration}; {departing} of them departing "
        f"from it.",
        found,
    )


#: What a record's structure is held by, cited in its findings: the record point, since
#: no rule binds on a record.
RECORD_POINT = "DEC-001 point 1"


#: Where groups bind: on the artefacts at the locations given.
_Where = Mapping[project_structure.Group, frozenset[str]]


@dataclass(frozen=True)
class _Binding:
    """Where each of the project's groups of tightenings binds (`_bound`): `where`, and
    in a preview, `previewing`, where a group binds only under the preview. A group
    neither holds binds nowhere. `standing` are the groups whose rule is the project's
    and is proposed or accepted: the labels they add mark a part wherever they do not
    bind. `findings` and `said` are what reading it found, and what the summary says
    of it."""

    own: project_structure.Own
    where: _Where
    standing: frozenset[project_structure.Group]
    findings: list[Finding]
    said: str = ""
    previewing: _Where = dataclasses.field(default_factory=dict)

    def kind(
        self,
        kind: structure.Kind,
        location: str,
        *,
        as_written: bool = False,
        preview: bool = False,
    ) -> structure.Kind:
        """`kind` tightened by the groups that bind on the artefact at `location`, and with
        `preview` by those that bind there only under the preview too. `as_written` holds a
        body that may predate the project's changes, a withdrawn artefact's
        (`Kind.as_written`)."""
        groups = self.own.of(kind.name)
        applying = [
            group
            for group in groups
            if location in self.where.get(group, ())
            or (preview and location in self.previewing.get(group, ()))
        ]
        tightened = project_structure.tightened(kind, groups, applying, self.standing)
        return dataclasses.replace(tightened, as_written=True) if as_written else tightened


def _key(departure: structure.Departure) -> tuple[object, ...]:
    """What tells one departure from another in a body, whatever structure found it: the
    element, how it departs, and the line."""
    return (departure.element.id, departure.how, departure.line)


def _bound(
    root: Path,
    analysis: Analysis,
    own: project_structure.Own,
    *,
    preview: bool,
    reach: Callable[..., Mapping[str, Mapping[str, bool]]],
    binding: frozenset[str],
) -> _Binding:
    """Where each of the project's groups of tightenings binds, once the format rule binds
    or is previewed (DEC-001 point 1). A group binds on each artefact its rule binds on,
    as the backbone's reading of where a rule binds says (`pkit rule-sets reach`), and
    applies there only where the format rule binds too, at the locations in `binding`:
    the summary counts a group only where it applies. That reading judges the rule's
    chain as well: a fill binds only while the rule it fills is accepted too (COR-051
    point 7). So a proposed rule's group binds nothing, and nothing asks where. An
    accepted rule that binds on none of the analysis's artefacts of the kind is
    reported. A preview also reads where the rule would bind if every proposed rule
    were accepted (`--preview`), and takes from it only the bindings marked as holding
    only under the preview, since a preview can also lose a binding (ADR-057 point 2). A
    rule that would bind on none even then is a preview's report. A superseded or
    withdrawn rule, or none of the project's, binds nothing (`_own_findings`). No group
    binds on a record: its schema refuses a tightening of the record's kind."""
    where: dict[project_structure.Group, frozenset[str]] = {}
    previewing: dict[project_structure.Group, frozenset[str]] = {}
    findings: list[Finding] = []
    ruled: list[project_structure.Group] = []
    standing: set[project_structure.Group] = set()
    for group in own.groups:
        rule = analysis.project_rules.get(group.rule)
        if rule is None or rule.status not in (ACCEPTED, PROPOSED):
            continue
        standing.add(group)
        if preview or rule.status == ACCEPTED:
            ruled.append(group)
    accepted = [g for g in ruled if analysis.project_rules[g.rule].status == ACCEPTED]
    plain = _read_reach(root, accepted, reach, preview=False, findings=findings)
    only = _read_reach(root, ruled, reach, preview=True, findings=findings) if preview else {}
    for group in ruled:
        of_kind = {artefact.location for artefact in analysis.of_kind(group.kind)}
        if group in accepted and plain is not None:
            where[group] = frozenset(
                location
                for location, bound in plain.items()
                if group.rule in bound and location in of_kind
            )
            if not where[group] and of_kind:
                findings.append(Finding(REPORT, group.where, _bound_on_none(group, False)))
        if not preview or only is None:
            continue
        previewing[group] = frozenset(
            location
            for location, bound in only.items()
            if bound.get(group.rule) is True
            and location in of_kind
            and location not in where.get(group, ())
        )
        if not where.get(group) and not previewing[group] and of_kind and group not in accepted:
            findings.append(Finding(REPORT, group.where, PREVIEW + _bound_on_none(group, True)))
    bind = [group for group in where if where[group] & binding]
    bind += [g for g in previewing if g not in bind and previewing[g] & binding]
    said = (
        f", tightened where {len(bind)} of the project's group(s) in {project_structure.FILE} bind"
        if bind
        else ""
    )
    return _Binding(own, where, frozenset(standing), findings, said, previewing)


def _read_reach(
    root: Path,
    groups: Sequence[project_structure.Group],
    reach: Callable[..., Mapping[str, Mapping[str, bool]]],
    *,
    preview: bool,
    findings: list[Finding],
) -> Mapping[str, Mapping[str, bool]] | None:
    """The reading of where rules bind, with the preview or without, for `groups`; none
    asked where there are none. Where it cannot be read, each group's finding says so,
    and `None`: an error without the preview, so the normal check fails as it would, and
    a preview's report with it, which never fails."""
    if not groups:
        return {}
    try:
        return reach(root, preview=preview)
    except Unreadable as exc:
        findings += [
            Finding(
                REPORT if preview else ERROR,
                group.where,
                f"{PREVIEW if preview else ''}where {group.rule} "
                f"{'would bind' if preview else 'binds'} cannot be read: {exc}. Its "
                f"tightenings of the {group.kind} kind apply to no artefact "
                f"{'in the preview ' if preview else ''}until it can (COR-051 point 7)",
            )
            for group in groups
        ]
        return None


def _bound_on_none(group: project_structure.Group, preview: bool) -> str:
    """Why a group's rule binds on no artefact of its kind, as the reading of where rules
    bind, with the preview or without, reads it."""
    reading = "`pkit rule-sets reach --preview`" if preview else "`pkit rule-sets reach`"
    binds = "would bind" if preview else "binds"
    return (
        f"{group.rule} {binds} on no {NOUN[group.kind]} of the analysis, as {reading} reads "
        f"it, so its tightenings apply to none: no scope of a set that reaches the rule "
        f"selects one, a pin behind its set holds it back, a rule it fills does not bind "
        f"there, or the sets whose scopes select one bring different fills for a point it "
        f"fills (COR-051 point 7)"
    )


def _own(root: Path) -> project_structure.Own | None:
    """The project's own structures, held to the shipped kinds; `None` while the kinds'
    declaration cannot be read, which the structure's own finding reports."""
    try:
        kinds = structure.read_kinds()
    except structure.Unreadable:
        return None
    return project_structure.read(root, kinds)


def _own_findings(analysis: Analysis, own: project_structure.Own | None) -> list[Finding]:
    """What the project's own structures are refused for, as errors whatever a rule's
    status, since the project mends its own file (COR-055 point 1): each problem the
    reading found, and a group that names no rule of the project's own rule sets. A
    group whose rule is superseded or withdrawn is reported: it binds nothing, and is
    to be removed or to name the rule that replaces it (DEC-001 point 1)."""
    if own is None:
        return []
    found = [*own.problems, *own.notes]
    for group in own.groups:
        rule = analysis.project_rules.get(group.rule)
        if rule is None:
            found.append(
                Finding(
                    ERROR,
                    f"{group.where}/rule",
                    f"{group.rule} is no rule of the project's own rule sets: a tightening "
                    f"names the project rule that asks for it, and binds at that rule's status "
                    f"(DEC-001 point 1)",
                )
            )
        elif rule.status in (SUPERSEDED, WITHDRAWN):
            instead = (
                f"name {rule.successor}, which replaces it, or remove the group"
                if rule.successor
                else "remove the group, or name a rule that asks for it"
            )
            found.append(
                Finding(
                    REPORT,
                    f"{group.where}/rule",
                    f"{group.rule} is {rule.status}, so the group binds nothing and its "
                    f"tightenings of the {group.kind} kind are not applied: {instead}",
                )
            )
    return found


def unchecked(
    status: str | None,
    no_set: bool,
    preview: bool,
    *,
    subject: str = "structure",
    command: str = "pkit analysis validate",
) -> str:
    """The summary's line when the format rule binds nothing, and why (COR-051 point 4):
    of the structure, or of another `subject` checked under the rule's gate, whose
    preview `command` gives."""
    if no_set:
        return (
            f"{subject} ({FORMAT_RULE}): not checked — the backbone's reading holds no "
            f"{CAPABILITY}:{METHOD_SET}, so whether its format rule binds cannot be told."
        )
    if status is None:
        return f"{subject}: not checked — {CAPABILITY}:{METHOD_SET} holds no {FORMAT_RULE}."
    if status == PROPOSED:
        return (
            f"{subject} ({FORMAT_RULE}, proposed): not checked — the rule binds nothing until "
            f"it is accepted (COR-051 point 4); `{command} --preview` shows what it would "
            f"report."
        )
    asked = " A preview shows only a proposed rule." if preview else ""
    return (
        f"{subject} ({FORMAT_RULE}, {status}): not checked — the rule binds nothing "
        f"(COR-051 point 4).{asked}"
    )


def _titles(analysis: Analysis) -> dict[str, str]:
    """Each use case's title by its id, as a journey's steps quote it."""
    titles: dict[str, str] = {}
    for use_case in analysis.of_kind(USE_CASE):
        title = use_case.fields.get("title")
        if use_case.id and isinstance(title, str):
            titles.setdefault(use_case.id, title)
    return titles


def _artefact_structure(
    artefact: Artefact,
    kind: structure.Kind,
    text: str,
    titles: Mapping[str, str],
    *,
    fields: bool = True,
) -> list[tuple[Finding, tuple[object, ...]]]:
    """What an artefact's body — an entry's section — and, with `fields`, its front
    matter break of its kind's structure, each with what tells it from another finding
    whatever structure found it (`_key`). A withdrawn artefact is never failed for a part
    it lacks or for a form, and a document's missing title heading is `_headings`'."""
    subject = with_article(artefact.kind)
    if artefact.entry and not artefact.span_read:
        return [
            (
                Finding(
                    ERROR,
                    artefact.location,
                    "its section is not checked against its kind's structure: the installed "
                    "backbone gives no entry's `span` in `pkit friction artefacts --json` — "
                    "upgrade it (`pkit upgrade`)",
                ),
                ("span",),
            )
        ]
    if artefact.entry and artefact.span is None:
        departing = [structure.Departure(kind.sections[0], structure.MISSING)]
    else:
        lines = (
            structure.span_lines(text, artefact.span)
            if artefact.entry and artefact.span is not None
            else structure.body_lines(text)
        )
        departing = structure.departures(lines, kind, fields=artefact.fields, titles=titles)
    found: list[tuple[Finding, tuple[object, ...]]] = [
        (
            Finding(ERROR, artefact.location, _departure_message(d, kind.sections, subject)),
            _key(d),
        )
        for d in departing
        if not _exempt(d, artefact)
    ]
    if artefact.withdrawn or not fields:
        return found
    held = _field_findings(artefact.location, artefact.fields, kind, subject)
    return found + [(finding, ("field", finding.message)) for finding in held]


def _exempt(departure: structure.Departure, artefact: Artefact) -> bool:
    """A part a withdrawn artefact lacks, or a form it breaks, either of which may have
    come since its withdrawal (DEC-001 point 1), and a document's title heading, which
    `_headings` holds whatever the format rule's status."""
    if artefact.withdrawn and departure.how in structure.FORM_BREACHES:
        return True
    if departure.how != structure.MISSING:
        return False
    if artefact.withdrawn:
        return True
    element = departure.element
    return (
        not artefact.entry
        and artefact.kind in TITLED
        and element.type == structure.HEADING
        and element.text is None
    )


def _heads(
    root: Path,
    analysis: Analysis,
    kinds: Mapping[str, structure.Kind],
    texts: dict[str, str | None],
    binding: Collection[str],
) -> tuple[list[Finding], int]:
    """Each collection file's head — its body above its first entry's section, as the
    backbone's reading spans the entries — against its kind's declared head, and how
    many heads were checked. The head belongs to no entry, but is part of the entries'
    structure, so it is held where the format rule binds on an entry of its file, one
    whose location is in `binding` (DEC-001 point 1). A file whose front matter does not
    parse, or that is no collection, is reported as such, so its head is not checked."""
    found: list[Finding] = []
    checked = 0
    failed = set(analysis.unreadable) | {stray.path for stray in analysis.strays}
    for path, kind_name in sorted(analysis.files.items()):
        kind = kinds.get(kind_name)
        if kind_name not in COLLECTIONS or kind is None or not kind.head or path in failed:
            continue
        entries = [a for a in analysis.artefacts if a.path == path and a.entry]
        if not any(a.location in binding for a in entries):
            continue
        text = _cached(root, path, texts)
        if text is None or any(not a.span_read for a in entries):
            continue  # an entry reports a backbone that gives no span
        firsts = [a.span[0] for a in entries if a.span is not None]
        lines = structure.body_lines(text)
        if firsts:
            lines = [line for line in lines if line[0] < min(firsts)]
        checked += 1
        subject = f"a file of {NOUN[kind_name]}s"
        found += [
            Finding(ERROR, path, _departure_message(d, kind.head, subject))
            for d in structure.departures(lines, kind, head=True)
        ]
    return found, checked


def _field_findings(
    location: str,
    fields: Mapping[str, Any],
    kind: structure.Kind,
    subject: str,
    because: str = FORMAT_RULE,
) -> list[Finding]:
    """Each front-matter text that does not hold its field's form, citing `because`: the
    format rule for an artefact, the record point for a record. A text that is still a
    placeholder a template shipped is the placeholder check's, so no form reports it."""
    found: list[Finding] = []
    for departure in structure.field_departures(fields, kind):
        if departure.text.strip() in IN_TEMPLATES:
            continue
        field = departure.field
        each = " in each item" if departure.pointer.count("/") > 1 else ""
        if departure.how == structure.NOT_A_SENTENCE:
            problem = (
                f"{departure.text!r} is more than one sentence: {subject}'s `{field.name}` "
                f"holds one sentence{each}, and a sentence ends at a full stop, a question mark "
                f"or an exclamation mark before a space or a line end"
            )
        else:
            problem = (
                f"{departure.text!r} is not of the form `{field.form}` that {subject}'s "
                f"`{field.name}` takes{each}: {departure.detail}"
            )
        found.append(
            Finding(
                ERROR,
                at(location, departure.pointer),
                f"{problem} ({because}). {_advice(field.hint, field.example)}",
            )
        )
    return found


def _departure_message(
    departure: structure.Departure,
    elements: Sequence[structure.Element],
    subject: str,
    because: str = FORMAT_RULE,
) -> str:
    """What a departure breaks, where, and what goes in the part: its hint and example,
    citing `because`: the format rule for an artefact, the record point for a record, on
    which no rule binds. A part a project adds, or makes required, cites the project rule
    that asks for it beside the format rule."""
    element = departure.element
    line = f", at line {departure.line}," if departure.line is not None else ""
    if departure.how == structure.UNDECLARED:
        return (
            f"`**{element.text}:**`{line} is no label the kind declares: {departure.detail} "
            f"closes its list of labels, so write the text under a declared label, or move it "
            f"into a part with a form ({departure.detail}, {because})"
        )
    named = _named(element, elements)
    cited = f"{element.rule}, {because}" if element.rule else because
    if departure.how == structure.MISSING and element.rule:
        problem = (
            f"{named} is missing, {_place(element, elements)}: the project's rule "
            f"{element.rule} requires it of {subject}"
        )
    elif departure.how == structure.MISSING:
        problem = (
            f"{named} is missing, {_place(element, elements)}: {subject} carries every part "
            f"its kind ships"
        )
    elif departure.how == structure.OUT_OF_ORDER:
        problem = (
            f"{named}{line} is out of order, {_place(element, elements)}: the parts come in "
            f"the order the kind gives"
        )
    elif departure.how == structure.EMPTY:
        none = ", or `None.` when there is nothing to say" if element.allows_none else ""
        problem = f"{named}{line} is empty: write in it what it asks for{none}"
    elif departure.how == structure.NONE_REFUSED:
        problem = (
            f"{named}{line} reads `None.`, which only a part that allows it may: {subject} "
            f"always has something to say here"
        )
    elif departure.how == structure.NOT_A_SENTENCE:
        ends = (
            "a sentence ends at a full stop, a question mark or an exclamation mark before a "
            "space or a line end, and one ends here before the text's last word"
        )
        if departure.detail:  # an item of a list in the part
            problem = (
                f"an item of {named}{line} is more than one sentence: {departure.detail}, "
                f"and {ends}"
            )
        else:
            problem = f"{named}{line} is more than one sentence: {ends}"
    else:
        problem = f"{named}{line} does not hold its form, `{element.form}`: {departure.detail}"
    return f"{problem} ({cited}). {_advice(element.hint, element.example)}".rstrip()


def _named(element: structure.Element, elements: Sequence[structure.Element]) -> str:
    """An element as a writer writes it."""
    if element.type == structure.LABEL:
        return f"`**{element.text}:**`"
    if element.type == structure.HEADING:
        marks = "#" * (element.level or 1)
        if element.text is not None:
            return f"the section `{marks} {element.text}`"
        return f"its `{marks} ` heading"
    index = list(elements).index(element)
    following = next((e for e in elements[index + 1 :] if e.type != structure.OPENING), None)
    if following is None:
        return "its opening text"
    return f"the opening text before {_named(following, elements)}"


def _place(element: structure.Element, elements: Sequence[structure.Element]) -> str:
    """Where the element goes: first, or after the element listed before it."""
    index = list(elements).index(element)
    if index == 0:
        return "and it comes first"
    previous = elements[index - 1]
    if previous.type == structure.OPENING:
        return "and it comes after its opening"
    return f"and it comes after {_named(previous, elements)}"


def _advice(hint: str | None, example: str | None) -> str:
    """A part's hint and example, as the check repeats them (DEC-001 point 1)."""
    said = [f"What goes there: {hint}"] if hint else []
    if example:
        said.append(f"Example: {example}")
    return " ".join(said)


def _cached(root: Path, rel: str, texts: dict[str, str | None]) -> str | None:
    if rel not in texts:
        texts[rel] = _read(root / rel)
    return texts[rel]


def _shown(path: Path, root: Path) -> str:
    """A path as a finding locates it: relative to the project root where it lies under it."""
    try:
        return path.relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()
