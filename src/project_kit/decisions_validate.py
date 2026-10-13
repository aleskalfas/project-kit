"""Decision-id collision detection across every id-space (Feature #162).

A decision record's `id` (e.g. `COR-001`, `PRJ-007`, `ADR-003`, `DEC-012`)
must be unique within its **id-space**. Hand-authoring two records with
the same id in parallel checkouts produces a collision that only surfaces
at merge — the DEC-032 incident this check exists to prevent. This module
scans every record, groups by id-space, and reports any id claimed by more
than one file.

The id-spaces (numbering is independent per space):

- **core** — `COR-NNN` under `.pkit/decisions/core/`.
- **project** — `PRJ-NNN` under `.pkit/decisions/project/`.
- **adr** — `ADR-NNN` at the overlay-resolved `<adr-records>` path
  (`.pkit/agents/project/overlay.yaml` → `adr-records[0]`; default
  `docs/architecture/decisions/`), mirroring `pkit new decision adr`.
- **per-capability DEC** — `DEC-NNN` under
  `.pkit/capabilities/<cap>/decisions/`. Uniqueness is scoped to each
  capability: two different capabilities may both hold `DEC-001` without
  collision; only same-capability duplicates count. Each capability is its
  own id-space, labelled `capability:<cap>`.

Rules are a separate identifier family with the same guarantee (COR-051
point 3): a rule id `RS-<SET>-NNN` is unique across every rule set the
location rule finds, so the check also reports a rule id claimed twice — by
two rule sets, or twice within one (`rule_sets.rule_id_collisions`), labelled
`rules`.

Each record's id is read from the YAML frontmatter `id:` field. As a cheap
secondary check, the frontmatter id is compared against the number encoded
in the filename (`<PREFIX>-NNN-<slug>.md`); a mismatch is reported as an
issue too — but the duplicate-id detection is the required behaviour.

The ADR path is resolved best-effort: if the overlay is absent or
misconfigured, ADR records simply aren't scanned (this check is not the
place to enforce overlay setup — `pkit new decision adr` already does, and
an adopter may legitimately have no ADRs). Collision detection over the
spaces that *do* resolve is unaffected.

**Revision narration is a warning, never an error** (`revision_narration`).
A record states what is true and is refined in place; git history is its
change log (`.pkit/decisions/README.md`, "Refining an accepted record").
Every record that is not superseded is read for the shapes that narrate a
revision instead: an amendment heading, an amendment marker, a revision
stamped with an issue number or a date, and change-log phrasing about what
the record once said. Each is a warning naming the file and line. It warns
for the reason ADR-058 gives reference drift (point 6, "Why drift warns"):
the shapes are read from prose, and a gate that fails on a heuristic reading
of prose fails for the wrong reasons. It is not a `report`, which ADR-058
point 2 keeps for what an owning record says is reported rather than judged —
narration is judged, since it breaks the README's rule. The two permitted
markers — a superseded-by line and a forward refinement pointer
(`(refinement per <record>)`) — match none of the shapes. Fenced code and
inline code are quoted material and are not read. A superseded record is
preserved as it stood, so it is not read either. Nor is a record that arrives
here as a synced copy — a core record, or a kit-shipped capability's, in a
project that is not the methodology's source (`is_synced_copy` of the tree's
`.pkit/lifecycle/ownership.py`): it is refined where it is authored, and an
edit here would be overwritten by the next sync. A tree without that module
has every record read.

**A record's points are checked too** (`point_findings`, COR-058 point 7),
over the same records as narration: a synced copy and a superseded record
are left out. Each record is read once by `record_points.read_points`, and
each stub is held to its entry by `record_points.hold_stubs`, so no second
reading of points lives here. A malformed `retired-points`, a stub that
disagrees with its entry, a live point on a retired id and a successor the
record neither holds nor retires are errors. A duplicate id, a gap in the
ids and a misspelt point heading are warnings. Of the front matter, only the
field's shape is read, so a project's own fields pass.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path

import click

from project_kit import cli_render, document_parts, lifecycle_ownership, record_points, rule_sets
from project_kit.decisions import resolve_adr_records_dir
from project_kit.validators import Finding, Outcome, Severity

# Frontmatter `id:` line, e.g. `id: COR-001`. Captures prefix + number so the
# id can be checked against the filename and grouped into an id-space.
_FRONTMATTER_ID_RE = re.compile(r"^id:\s*([A-Z]+)-(\d+)\s*$", re.MULTILINE)

# Filename shape `<PREFIX>-NNN-<slug>.md`. Captures prefix + number for the
# id-matches-filename sanity check.
_FILENAME_RE = re.compile(r"^([A-Z]+)-(\d+)-.+\.md$")

# Frontmatter `status:` line. A superseded record is not read for narration.
_FRONTMATTER_STATUS_RE = re.compile(r"^status:\s*(\S+)\s*$", re.MULTILINE)

# --- the shapes of revision narration ----------------------------------------
#
# Each is (shape, pattern); a line reports the first shape it matches. The
# shape names are what a report says it found.

# What stamps a revision: an issue number or an ISO date.
_STAMP = r"(?:#\d+|\d{4}-\d{2}-\d{2})"

# The words a stamped revision leads with.
_REVISION_WORD = (
    r"(?:amend(?:ed|ment)|updated?|correct(?:ion|ed)|clarif(?:ication|ied)|closed|revis(?:ion|ed))"
)

_NARRATION_SHAPES: tuple[tuple[str, re.Pattern[str]], ...] = (
    # `## Amendment (2026-08-09)`, `### Amendments`, `## Erratum`.
    (
        "amendment heading",
        re.compile(
            r"^ {0,3}#{1,6}\s+\(?(?:amendments?|amended|addend(?:um|a)|errat(?:um|a)"
            r"|change[- ]?log|revision history)\b",
            re.IGNORECASE,
        ),
    ),
    # `**Amendment 1**`, `> **Amendment (#20) — …**`, `**(Amended 2026-08-20: …)**`,
    # `**Amended by [X].**`, `**Amended in place, not superseded**`, `(amended in place)`.
    (
        "amendment marker",
        re.compile(
            r"\*\*\(?\s*(?:amendment|amended|addendum|erratum)\b|\(\s*amend(?:ed|ment)\b",
            re.IGNORECASE,
        ),
    ),
    # `**Update (#252) — …**`, `**Correction (2026-06-25, issue #304).**`,
    # `## Closed (#823)`, and an inline `(clarified, #813)`.
    (
        "revision stamp",
        re.compile(
            rf"(?:(?:\*\*|^ {{0,3}}#{{1,6}}\s+)\(?\s*{_REVISION_WORD}\s*\(|\(\s*{_REVISION_WORD}\b)"
            rf"[^)\n]{{0,40}}?{_STAMP}",
            re.IGNORECASE,
        ),
    ),
    # The record talking about what it once said.
    (
        "change-log phrasing",
        re.compile(
            r"\b(?:this|the) record (?:originally|previously|initially|formerly)\b"
            r"|\b(?:original|earlier|previous|prior) (?:version|revision|draft|wording)"
            r" of this (?:record|decision)\b"
            r"|\bpreviously,? we (?:believed|thought|assumed)\b"
            r"|\bwe (?:previously|originally|initially|once) (?:believed|thought|assumed)\b"
            r"|\bas (?:originally|first|initially) (?:written|stated|drafted|worded)\b",
            re.IGNORECASE,
        ),
    ),
)

# Markdown fence opener/closer (``` or ~~~, indented under a list or inside a
# block quote too), and an inline code span — blanked to spaces of its own
# length before matching, so a report's position still points into the line
# as written.
_FENCE_RE = re.compile(r"^\s*(?:>\s*)*(`{3,}|~{3,})")
_INLINE_CODE_RE = re.compile(r"(`+)(?:(?!\1).)+?\1")

# How much of the matched line a report quotes.
_EXCERPT_LENGTH = 60


@dataclass(frozen=True)
class DecisionRecord:
    """One decision record located on disk, with its parsed id."""

    path: Path
    id_space: str  # "core" | "project" | "adr" | "capability:<cap>"
    record_id: str | None  # the frontmatter id (e.g. "COR-001"), or None if unparseable


@dataclass(frozen=True)
class DecisionIssue:
    """One finding — a duplicate id, an id/filename mismatch, or a line of revision narration."""

    # path relative to target; "<id-space> :: <id>" for a duplicate; "<path>:<line>" for narration
    location: str
    message: str


@dataclass(frozen=True)
class DecisionValidationReport:
    """Outcome of a decision-id validation run."""

    records_checked: int = 0
    issues: tuple[DecisionIssue, ...] = field(default_factory=tuple)
    rules_checked: int = 0  # rules across the rule sets, checked as their own id-space

    @property
    def is_clean(self) -> bool:
        return not self.issues


def validate_decision_ids(target_root: Path) -> DecisionValidationReport:
    """Scan every decision record and report id collisions + id/filename mismatches.

    Walks all four id-spaces, parses each record's frontmatter id, and
    flags any id claimed by more than one file *within the same id-space*
    (cross-id-space duplicates — same number in two capabilities, or a
    `COR-001` alongside a `PRJ-001` — are not collisions). Also flags any
    record whose frontmatter id disagrees with its filename number, and any
    rule id claimed more than once across the rule sets.
    """
    records = discover_decision_records(target_root)
    issues: list[DecisionIssue] = []

    # 1. id/filename mismatch + unparseable-id sanity checks.
    for record in records:
        issues.extend(_filename_consistency_issues(record, target_root))

    # 2. Duplicate-id detection, scoped per id-space.
    by_space_id: dict[tuple[str, str], list[Path]] = {}
    for record in records:
        if record.record_id is None:
            continue
        by_space_id.setdefault((record.id_space, record.record_id), []).append(record.path)

    for (id_space, record_id), paths in sorted(by_space_id.items()):
        if len(paths) < 2:
            continue
        rels = sorted(_rel(p, target_root) for p in paths)
        issues.append(
            DecisionIssue(
                location=f"{id_space} :: {record_id}",
                message=(
                    f"id {record_id!r} is claimed by {len(paths)} records in the "
                    f"{id_space!r} id-space: " + ", ".join(rels)
                ),
            )
        )

    # 3. Rule ids, unique across every rule set (COR-051 point 3).
    discovery = rule_sets.discover_rule_sets(target_root)
    issues.extend(_rule_id_issues(discovery))

    return DecisionValidationReport(
        records_checked=len(records),
        issues=tuple(issues),
        rules_checked=len(discovery.rules),
    )


def _rule_id_issues(discovery: rule_sets.RuleSetDiscovery) -> list[DecisionIssue]:
    """A rule id claimed more than once in the rule-set space, one issue per id."""
    issues: list[DecisionIssue] = []
    for collision in rule_sets.rule_id_collisions(discovery):
        claims: dict[str, int] = {}
        for path in collision.paths:
            claims[path] = claims.get(path, 0) + 1
        where = ", ".join(
            path if count == 1 else f"{path} ({count} times)" for path, count in claims.items()
        )
        issues.append(
            DecisionIssue(
                location=f"rules :: {collision.rule_id}",
                message=(
                    f"rule id {collision.rule_id!r} is claimed {len(collision.paths)} times "
                    f"across the rule sets: {where}; a rule id names one rule, in the set its "
                    f"id names (COR-051 point 3)."
                ),
            )
        )
    return issues


def discover_decision_records(target_root: Path) -> list[DecisionRecord]:
    """Locate every decision record across all id-spaces, parsing each id.

    Returns records in a stable order (by id-space, then path). Records
    whose id can't be parsed from frontmatter carry `record_id=None`; the
    consistency pass reports them, and they're excluded from duplicate
    grouping (a record with no readable id can't collide).
    """
    records: list[DecisionRecord] = []

    fixed_spaces = {
        "core": target_root / ".pkit" / "decisions" / "core",
        "project": target_root / ".pkit" / "decisions" / "project",
    }
    for id_space, decisions_dir in fixed_spaces.items():
        records.extend(_scan_dir(decisions_dir, id_space))

    adr_dir = _resolve_adr_dir_best_effort(target_root)
    if adr_dir is not None:
        records.extend(_scan_dir(adr_dir, "adr"))

    caps_dir = target_root / ".pkit" / "capabilities"
    if caps_dir.is_dir():
        for cap_dir in sorted(caps_dir.iterdir()):
            cap_decisions = cap_dir / "decisions"
            if cap_decisions.is_dir():
                records.extend(_scan_dir(cap_decisions, f"capability:{cap_dir.name}"))

    return records


def revision_narration(target_root: Path) -> tuple[DecisionIssue, ...]:
    """Every place a record the project refines narrates its own revision.

    One finding per line, at `<path>:<line>`, naming the shape found and quoting
    it (see the module docstring for the shapes and what is not read — a
    superseded record, and one that arrives as a synced copy). Warnings, never
    errors (ADR-058 point 6): the shapes are read from prose, so a finding asks
    a person to look rather than blocking a change.
    """
    found: list[DecisionIssue] = []
    for rel, text in _refined_records(target_root):
        found.extend(
            DecisionIssue(
                location=f"{rel}:{line}",
                message=(
                    f"{shape} {excerpt} — a record states what is true; git history is its "
                    "change log."
                ),
            )
            for line, shape, excerpt in find_revision_narration(text)
        )
    return tuple(found)


def _refined_records(target_root: Path) -> Iterator[tuple[str, str]]:
    """Each record the project refines, as `(path relative to the root, text)`.

    A synced copy is left out, since it is refined where it is authored and an
    edit here is overwritten by the next sync. So is a superseded record, whose
    body stays as it stood. An unreadable record is left to the id pass, which
    reports it.
    """
    ownership = lifecycle_ownership.load_ownership(target_root)
    for record in discover_decision_records(target_root):
        rel = _rel(record.path, target_root)
        if ownership is not None and ownership.is_synced_copy(target_root, rel):
            continue
        try:
            text = record.path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        status = _FRONTMATTER_STATUS_RE.search(_extract_frontmatter(text) or "")
        if status is not None and status.group(1) == "superseded":
            continue
        yield rel, text


def find_revision_narration(text: str) -> list[tuple[int, str, str]]:
    """The narration in one record's text: `(line number, shape, excerpt)` per line.

    Line numbers count from 1 over the whole file, front matter included. The
    front matter, fenced code and inline code spans are not read; a line
    reports the first shape it matches.
    """
    lines = text.splitlines()
    start = _body_start(lines)
    found: list[tuple[int, str, str]] = []
    fence: str | None = None
    for number, raw in enumerate(lines[start:], start=start + 1):
        fence_match = _FENCE_RE.match(raw)
        if fence_match is not None:
            marker = fence_match.group(1)
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        if fence is not None:
            continue
        prose = _INLINE_CODE_RE.sub(lambda code: " " * len(code.group(0)), raw)
        for shape, pattern in _NARRATION_SHAPES:
            match = pattern.search(prose)
            if match is not None:
                found.append((number, shape, _excerpt(raw, match.start())))
                break
    return found


def _body_start(lines: list[str]) -> int:
    """The index of the first body line — after the front matter, when there is one."""
    if not lines or lines[0].strip() != "---":
        return 0
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return index + 1
    return 0


def _excerpt(line: str, start: int) -> str:
    """The matched text, from where the shape starts, quoted and trimmed."""
    tail = line[start:].strip()
    if len(tail) > _EXCERPT_LENGTH:
        tail = tail[:_EXCERPT_LENGTH].rstrip() + "…"
    return f'"{tail}"'


# --- a record's points (COR-058 point 7) -------------------------------------


def point_findings(target_root: Path) -> tuple[Finding, ...]:
    """Every record's points, retired points and stubs, held to COR-058 point 7.

    The records read are those `revision_narration` reads: a synced copy and a
    superseded record are left out, as the point says. Each record's findings
    come from `check_points`, its errors then its warnings, records in the
    order the id pass finds them.
    """
    found: list[Finding] = []
    for rel, text in _refined_records(target_root):
        found.extend(check_points(rel, text))
    return tuple(found)


def check_points(rel: str, text: str) -> list[Finding]:
    """One record's points, retired points and stubs (COR-058 point 7), at `rel`.

    The record is read once, by `record_points.read_points`, and each stub is held
    to its entry by `record_points.hold_stubs`. Every finding names the file and
    the id: `<rel>#<id>`, or `<rel>:/retired-points` for the field's shape, its
    message naming the id. Errors come first:

    - a malformed `retired-points`: a field that cannot be read, or is not a
      mapping, is one error, and nothing that rests on the retired ids is
      checked then
    - a retired id with no stub, a stub whose id is not retired, and a stub
      whose sentence differs from the one its entry gives
    - a live point whose heading uses a retired id
    - a successor the record neither holds nor retires, and a retired id named
      as its own successor

    Then the warnings, which never fail: a duplicate id, a gap in the ids
    counting retired ones, and a heading in the Decision that opens with a
    number or a label in a form a point's heading refuses. Only the field's
    shape is read of the front matter, so a project's own fields pass. A record
    in list form has no point heading and no stub, so it fails nothing unless it
    writes `retired-points`.
    """
    points = record_points.read_points(text)
    at = _LineOf(document_parts.body_first_line(text, points.body.text), points.body.text)
    unreadable = _unreadable_retired_points(rel, text, points)
    errors: list[Finding] = []
    warnings = [*_duplicate_ids(rel, points, at), *_misspelt_headings(rel, points, at)]
    if unreadable is not None:
        errors.append(unreadable)
    else:
        errors += _malformed_entries(rel, points)
        errors += _stub_mismatches(rel, points, at)
        errors += _live_points_on_retired_ids(rel, points, at)
        errors += _foreign_successors(rel, points)
        warnings += _gaps(rel, points)
    return [*errors, *warnings]


@dataclass(frozen=True)
class _LineOf:
    """The line of the file a place in the body sits on, counted from 1."""

    first_line: int  # the line the body opens on
    body: str

    def __call__(self, start: int) -> int:
        return self.first_line + self.body.count("\n", 0, start)


# `retired-points` written as a key of the front matter, quoted or not. It is read
# from the front matter's text when that does not parse, so a field nothing can
# read still fails.
_RETIRED_KEY_LINE = re.compile(r"""^["']?retired-points["']?[ \t]*:""", re.MULTILINE)

# What a misspelt heading opens with: a number, dotted or not, or a label.
_OPENING = re.compile(r"^(?:\d+(?:\.\d+)*|[A-Za-z]+\d+)")

# A point id's series and number. Numbers and each series of labels count apart
# (COR-058 point 3); a number's series is the empty prefix.
_SERIES = re.compile(r"^([A-Za-z]*)(\d+)$")

# Where a finding on the field's shape points.
_RETIRED_POINTER = f":/{record_points.RETIRED_POINTS_KEY}"


def _unreadable_retired_points(
    rel: str, text: str, points: record_points.RecordPoints
) -> Finding | None:
    """One error when the record writes `retired-points` and it cannot be read as a
    mapping: the front matter does not parse, or the field is not a mapping. A
    field left empty retires nothing, as `record_points.read_points` reads it."""
    front_matter, _body = document_parts.split_front_matter(text)
    if front_matter is None or not _RETIRED_KEY_LINE.search(front_matter):
        return None
    value = points.front_matter.get(record_points.RETIRED_POINTS_KEY)
    if points.front_matter_problem is not None:
        why = f"the front matter does not parse ({points.front_matter_problem})"
    elif value is not None and not isinstance(value, Mapping):
        why = "it is not a mapping of retired ids to their successors"
    else:
        return None
    return Finding(
        rel + _RETIRED_POINTER,
        f"`{record_points.RETIRED_POINTS_KEY}` cannot be read: {why}. Nothing that rests on "
        f"the retired ids is checked until it can (COR-058 point 4).",
    )


def _malformed_entries(rel: str, points: record_points.RecordPoints) -> Iterator[Finding]:
    """An entry whose id is no point id, or whose successors are not a list of ids."""
    for problem in points.retired_problems:
        yield Finding(
            rel + _RETIRED_POINTER,
            f'{problem}: each entry maps a retired id to a list of ids, such as `"6": ["7", '
            f'"16"]` (COR-058 point 4).',
        )


def _stub_mismatches(
    rel: str, points: record_points.RecordPoints, at: _LineOf
) -> Iterator[Finding]:
    """Each stub held to its entry, both ways, by `record_points.hold_stubs`."""
    kind = record_points.StubMismatchKind
    for mismatch in record_points.hold_stubs(points):
        stub = mismatch.stub
        where = "" if stub is None else f" at line {at(stub.extent.start)}"
        if mismatch.kind is kind.NO_STUB:
            successors = points.retired.get(mismatch.id, ())
            heading = f"{'#' * _points_level(points)} {_heading_form(mismatch.id)}"
            message = (
                f"retired point `{mismatch.id}` has no stub. Where the point was, write the "
                f'heading `{heading}` and the sentence "'
                f'{record_points.stub_sentence(successors)}" (COR-058 point 4).'
            )
        elif mismatch.kind is kind.NOT_RETIRED:
            message = (
                f"the stub of `{mismatch.id}`{where} retires no id: `retired-points` has no "
                f"entry for `{mismatch.id}`. Add the entry, with the points that took its "
                f"text, or give a live point a title other than "
                f"`{record_points.STUB_TITLE}` (COR-058 points 1 and 4)."
            )
        else:
            found = f'reads "{mismatch.found}"' if mismatch.found else "holds no sentence"
            message = (
                f"the stub of retired point `{mismatch.id}`{where} {found}. Its entry gives "
                f'"{mismatch.expected}" (COR-058 point 4).'
            )
        yield Finding(f"{rel}#{mismatch.id}", message)


def _live_points_on_retired_ids(
    rel: str, points: record_points.RecordPoints, at: _LineOf
) -> Iterator[Finding]:
    """A live point whose heading uses an id `retired-points` retires."""
    for point in points.points:
        if point.id in points.retired:
            yield Finding(
                f"{rel}#{point.id}",
                f"point `{point.id}` at line {at(point.extent.start)} uses a retired id: "
                f"`retired-points` retires `{point.id}`, and no id is reused. A new point "
                f"takes the next unused number, `{_next_unused(points, point.id)}` (COR-058 "
                f"point 3).",
            )


def _foreign_successors(rel: str, points: record_points.RecordPoints) -> Iterator[Finding]:
    """A successor the record neither holds nor retires, and a retired id named as
    its own successor. A record in list form holds the points of its list."""
    held = {p.id for p in points.points} | {p.id for p in points.list_points}
    for retired_id, successors in points.retired.items():
        for successor in successors:
            if successor == retired_id:
                message = f"retired point `{retired_id}` names itself as its successor"
            elif successor not in held and successor not in points.retired:
                message = (
                    f"`{successor}`, a successor of retired point `{retired_id}`, is neither a "
                    f"point of this record nor a retired id"
                )
            else:
                continue
            yield Finding(
                f"{rel}#{retired_id}",
                f"{message}. Every successor is a point of the same record (COR-058 point 5).",
            )


def _duplicate_ids(rel: str, points: record_points.RecordPoints, at: _LineOf) -> Iterator[Finding]:
    """An id two live points take, or two stubs. A point that takes a retired id
    fails on its own (`_live_points_on_retired_ids`), and a stub whose id is not
    retired fails as a stub."""
    for kind, headings in (("points", points.points), ("stubs", points.stubs)):
        by_id: dict[str, list[int]] = {}
        for heading in headings:
            by_id.setdefault(heading.id, []).append(at(heading.extent.start))
        for point_id, lines in by_id.items():
            if len(lines) > 1:
                yield Finding(
                    f"{rel}#{point_id}",
                    f"{len(lines)} {kind} take the id `{point_id}`, at lines "
                    f"{_and(str(line) for line in lines)}. A record's ids are unique across "
                    f"all its groups (COR-058 point 1).",
                    severity=Severity.WARNING,
                )


def _gaps(rel: str, points: record_points.RecordPoints) -> Iterator[Finding]:
    """An id below the highest of its series that no point, retired id or stub holds.

    Only a record whose points are headings is read: a record in list form keeps
    renumbering until it is converted (COR-058 point 9). One warning per run of
    missing ids, at the first of them.
    """
    if points.level is None:
        return
    held = [p.id for p in (*points.points, *points.stubs)] + list(points.retired)
    by_series: dict[str, set[int]] = {}
    for point_id in held:
        series = _SERIES.match(point_id)
        if series is not None:
            by_series.setdefault(series.group(1), set()).add(int(series.group(2)))
    for prefix, numbers in sorted(by_series.items()):
        missing = [n for n in range(1, max(numbers)) if n not in numbers]
        for first, last in _runs(missing):
            if first == last:
                skipped, them = f"`{prefix}{first}`", "it"
            else:
                skipped, them = f"`{prefix}{first}` to `{prefix}{last}`", "them"
            yield Finding(
                f"{rel}#{prefix}{first}",
                f"the ids skip {skipped}: no point holds {them}, and `retired-points` does not "
                f"retire {them}. A dropped point keeps its id in `retired-points`, with a stub "
                f"where it was (COR-058 points 3 and 4).",
                severity=Severity.WARNING,
            )


def _misspelt_headings(
    rel: str, points: record_points.RecordPoints, at: _LineOf
) -> Iterator[Finding]:
    """A heading in the Decision that opens with a number or a label in a form a
    point's heading refuses, as `record_points.read_points` finds it."""
    for heading in points.misspelt:
        opening = _OPENING.match(heading.title)
        token = opening.group(0) if opening is not None else heading.title.split()[0]
        yield Finding(
            f"{rel}#{token}",
            f"the heading `{'#' * heading.level} {heading.title}` at line {at(heading.start)} "
            f"opens with `{token}` in a form a point's heading refuses, so it is no point. A "
            f"point's heading is `5. Title` or `D1 — Title`, and a sub-section's opens with "
            f"no number or label (COR-058 point 1).",
            severity=Severity.WARNING,
        )


def _points_level(points: record_points.RecordPoints) -> int:
    """The points' level, or one below the Decision's while it has no point heading."""
    if points.level is not None:
        return points.level
    decision = points.decision.heading if points.decision is not None else None
    return decision.level + 1 if decision is not None else 3


def _heading_form(point_id: str) -> str:
    """A stub's heading after its `#`s: `6. Retired`, or `D6 — Retired` for a label."""
    if point_id.isdigit():
        return f"{point_id}. {record_points.STUB_TITLE}"
    return f"{point_id} — {record_points.STUB_TITLE}"


def _next_unused(points: record_points.RecordPoints, point_id: str) -> str:
    """The next unused id of `point_id`'s series: one past the highest the record
    holds or retires (COR-058 point 3)."""
    series = _SERIES.match(point_id)
    if series is None:
        return point_id
    prefix = series.group(1)
    numbers = [
        int(found.group(2))
        for held in (*(p.id for p in points.points), *(s.id for s in points.stubs), *points.retired)
        if (found := _SERIES.match(held)) is not None and found.group(1) == prefix
    ]
    return f"{prefix}{max(numbers) + 1}"


def _runs(numbers: list[int]) -> Iterator[tuple[int, int]]:
    """Ascending numbers as runs of consecutive ones: `(first, last)` each."""
    start = previous = None
    for number in numbers:
        if previous is not None and number == previous + 1:
            previous = number
            continue
        if start is not None and previous is not None:
            yield start, previous
        start = previous = number
    if start is not None and previous is not None:
        yield start, previous


def _and(items: Iterable[str]) -> str:
    """`a`, `a and b`, `a, b and c`."""
    listed = list(items)
    return listed[0] if len(listed) == 1 else f"{', '.join(listed[:-1])} and {listed[-1]}"


def outcome(target_root: Path) -> Outcome:
    """The `decisions` member of `pkit validate`: every record's front matter
    (`validate.decision_frontmatter_issues`), the id spaces (`validate_decision_ids`) and
    the errors on records' points (`point_findings`), then revision narration
    (`revision_narration`) and the warnings on records' points."""
    from project_kit.validate import decision_frontmatter_issues

    front_matter = decision_frontmatter_issues(target_root)
    report = validate_decision_ids(target_root)
    narration = revision_narration(target_root)
    points = point_findings(target_root)
    errors = (
        *(Finding(issue.location, issue.diagnosis) for issue in front_matter),
        *(Finding(issue.location, issue.message) for issue in report.issues),
        *(finding for finding in points if finding.severity.fails),
    )
    warnings = (
        *(Finding(issue.location, issue.message, severity=Severity.WARNING) for issue in narration),
        *(finding for finding in points if not finding.severity.fails),
    )
    rules = f" and {report.rules_checked} rule(s)" if report.rules_checked else ""
    summary = (
        f"{report.records_checked} decision record(s){rules} checked; "
        f"{len(errors)} error(s), {len(warnings)} warning(s).",
    )
    return Outcome(summary, (*errors, *warnings))


def print_report(report: DecisionValidationReport) -> None:
    """Render the report to stdout, mirroring `pkit schemas validate`'s style."""
    rules = f" and {report.rules_checked} rule(s)" if report.rules_checked else ""
    if report.is_clean:
        if report.records_checked == 0 and report.rules_checked == 0:
            click.echo("  No decision records found to validate.")
        else:
            click.echo(
                "  "
                + cli_render.style(
                    "strong",
                    f"Validated {report.records_checked} decision record(s){rules}. "
                    "No id collisions found.",
                )
            )
        return

    click.echo(
        "  "
        + cli_render.style(
            "strong",
            f"{len(report.issues)} issue(s) found across "
            f"{report.records_checked} decision record(s){rules}:",
        )
    )
    for issue in report.issues:
        click.echo(f"    {issue.location}")
        click.echo(f"      → {issue.message}")


def print_narration(narration: tuple[DecisionIssue, ...]) -> None:
    """Render the revision-narration warnings, after the id report; nothing when there are none."""
    if not narration:
        return
    click.echo(
        "  "
        + cli_render.style(
            "strong",
            f"{len(narration)} warning(s) of revision narration, which do not fail the "
            'check (.pkit/decisions/README.md, "Refining an accepted record"):',
        )
    )
    for issue in narration:
        click.echo(f"    {issue.location}")
        click.echo(f"      → {issue.message}")


def print_points(findings: tuple[Finding, ...]) -> None:
    """Render the findings on records' points, after the narration; nothing when there
    are none. Errors fail the command, and warnings do not (COR-058 point 7)."""
    if not findings:
        return
    errors = sum(1 for finding in findings if finding.severity.fails)
    click.echo(
        "  "
        + cli_render.style(
            "strong",
            f"{errors} error(s) and {len(findings) - errors} warning(s) on records' points "
            "(COR-058 point 7):",
        )
    )
    for finding in findings:
        click.echo(f"    {finding.severity.value:<9}{finding.location}")
        click.echo(f"      → {finding.message}")


def _scan_dir(decisions_dir: Path, id_space: str) -> list[DecisionRecord]:
    """Parse every `*.md` record in one directory into a `DecisionRecord`."""
    if not decisions_dir.is_dir():
        return []
    records: list[DecisionRecord] = []
    for path in sorted(decisions_dir.glob("*.md")):
        if not path.is_file():
            continue
        if path.name == "README.md":
            continue
        records.append(
            DecisionRecord(
                path=path,
                id_space=id_space,
                record_id=_parse_frontmatter_id(path),
            )
        )
    return records


def _parse_frontmatter_id(path: Path) -> str | None:
    """Read a record's frontmatter `id:` field, returning e.g. `COR-001` or None.

    Reads only the leading frontmatter region (between the first two `---`
    fences) so a stray `id:` line deeper in the body can't be mistaken for
    the record's id.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    frontmatter = _extract_frontmatter(text)
    if frontmatter is None:
        return None
    match = _FRONTMATTER_ID_RE.search(frontmatter)
    if match is None:
        return None
    return f"{match.group(1)}-{match.group(2)}"


def _extract_frontmatter(text: str) -> str | None:
    """Return the YAML frontmatter block (without the `---` fences), or None."""
    if not text.startswith("---"):
        return None
    # Split on the fence lines. The frontmatter is the content between the
    # first `---` and the next `---` on its own line.
    rest = text[len("---") :]
    end = rest.find("\n---")
    if end == -1:
        return None
    return rest[:end]


def _filename_consistency_issues(record: DecisionRecord, target_root: Path) -> list[DecisionIssue]:
    """Check a record's frontmatter id against its filename number (cheap sanity)."""
    rel = _rel(record.path, target_root)
    if record.record_id is None:
        return [
            DecisionIssue(
                location=rel,
                message="could not parse an `id:` from the record's frontmatter.",
            )
        ]
    filename_match = _FILENAME_RE.match(record.path.name)
    if filename_match is None:
        # Not a numbered record filename; the id parsed fine, so nothing to
        # cross-check. (Unlikely given the glob, but don't false-positive.)
        return []
    # Compare the numeric portion. `COR-001` vs filename `COR-1-...` should
    # match (both → 1); zero-padding differences are not a defect.
    id_prefix, id_num = record.record_id.split("-", 1)
    file_prefix, file_num = filename_match.group(1), filename_match.group(2)
    if id_prefix != file_prefix or int(id_num) != int(file_num):
        return [
            DecisionIssue(
                location=rel,
                message=(
                    f"frontmatter id {record.record_id!r} disagrees with the "
                    f"filename ({file_prefix}-{file_num})."
                ),
            )
        ]
    return []


def _resolve_adr_dir_best_effort(target_root: Path) -> Path | None:
    """Resolve the ADR-records directory, or None if the overlay isn't set up.

    Reuses `decisions.resolve_adr_records_dir` (the same resolver
    `pkit new decision adr` uses) but swallows its refusals: a missing or
    unconfigured overlay simply means "no ADRs to scan here", which is a
    legitimate state for this check (unlike for stamping a new ADR).
    """
    try:
        return resolve_adr_records_dir(target_root)
    except click.ClickException:
        return None


def _rel(path: Path, target_root: Path) -> str:
    """Render a path relative to target_root when possible; otherwise absolute."""
    try:
        return str(path.relative_to(target_root))
    except ValueError:
        return str(path)
