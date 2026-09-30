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

**Revision narration is reported, never failed** (`revision_narration`). A
record states what is true and is refined in place; git history is its
change log (`.pkit/decisions/README.md`, "Refining an accepted record").
Every record that is not superseded is read for the shapes that narrate a
revision instead: an amendment heading, an amendment marker, a revision
stamped with an issue number or a date, and change-log phrasing about what
the record once said. Each is a report naming the file and line. The two
permitted markers — a superseded-by line and a forward refinement pointer
(`(refinement per <record>)`) — match none of the shapes. Fenced code and
inline code are quoted material and are not read. A superseded record is
preserved as it stood, so it is not read either. Nor is a record that arrives
here as a synced copy — a core record, or a kit-shipped capability's, in a
project that is not the methodology's source (`is_synced_copy` of the tree's
`.pkit/lifecycle/ownership.py`): it is refined where it is authored, and an
edit here would be overwritten by the next sync. A tree without that module
has every record read.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import click

from project_kit import cli_render, lifecycle_ownership, rule_sets
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

    One report per line, at `<path>:<line>`, naming the shape found and quoting
    it (see the module docstring for the shapes and what is not read — a
    superseded record, and one that arrives as a synced copy). Reports, never
    errors: the shapes are read from prose, so a finding asks a person to look
    rather than blocking a change.
    """
    ownership = lifecycle_ownership.load_ownership(target_root)
    reports: list[DecisionIssue] = []
    for record in discover_decision_records(target_root):
        rel = _rel(record.path, target_root)
        if ownership is not None and ownership.is_synced_copy(target_root, rel):
            continue  # refined where it is authored; an edit here is overwritten by sync
        try:
            text = record.path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue  # the id pass reports an unreadable record
        frontmatter = _extract_frontmatter(text)
        status = _FRONTMATTER_STATUS_RE.search(frontmatter or "")
        if status is not None and status.group(1) == "superseded":
            continue
        reports.extend(
            DecisionIssue(
                location=f"{rel}:{line}",
                message=(
                    f"{shape} {excerpt} — a record states what is true; git history is its "
                    "change log."
                ),
            )
            for line, shape, excerpt in find_revision_narration(text)
        )
    return tuple(reports)


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


def outcome(target_root: Path) -> Outcome:
    """The `decisions` member of `pkit validate`: every record's front matter
    (`validate.decision_frontmatter_issues`) and the id spaces (`validate_decision_ids`),
    which are errors, then revision narration (`revision_narration`), which is reported."""
    from project_kit.validate import decision_frontmatter_issues

    front_matter = decision_frontmatter_issues(target_root)
    report = validate_decision_ids(target_root)
    narration = revision_narration(target_root)
    errors = (
        *(Finding(issue.location, issue.diagnosis) for issue in front_matter),
        *(Finding(issue.location, issue.message) for issue in report.issues),
    )
    reports = tuple(
        Finding(issue.location, issue.message, severity=Severity.REPORT) for issue in narration
    )
    rules = f" and {report.rules_checked} rule(s)" if report.rules_checked else ""
    summary = (
        f"{report.records_checked} decision record(s){rules} checked; "
        f"{len(errors)} error(s), {len(reports)} report(s).",
    )
    return Outcome(summary, (*errors, *reports))


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
    """Render the revision-narration reports, after the id report; nothing when there are none."""
    if not narration:
        return
    click.echo(
        "  "
        + cli_render.style(
            "strong",
            f"{len(narration)} report(s) of revision narration, which do not fail the "
            'check (.pkit/decisions/README.md, "Refining an accepted record"):',
        )
    )
    for issue in narration:
        click.echo(f"    {issue.location}")
        click.echo(f"      → {issue.message}")


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
