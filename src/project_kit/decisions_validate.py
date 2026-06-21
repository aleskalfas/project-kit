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

Each record's id is read from the YAML frontmatter `id:` field. As a cheap
secondary check, the frontmatter id is compared against the number encoded
in the filename (`<PREFIX>-NNN-<slug>.md`); a mismatch is reported as an
issue too — but the duplicate-id detection is the required behaviour.

The ADR path is resolved best-effort: if the overlay is absent or
misconfigured, ADR records simply aren't scanned (this check is not the
place to enforce overlay setup — `pkit new decision adr` already does, and
an adopter may legitimately have no ADRs). Collision detection over the
spaces that *do* resolve is unaffected.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import click

from project_kit import cli_render
from project_kit.decisions import resolve_adr_records_dir


# Frontmatter `id:` line, e.g. `id: COR-001`. Captures prefix + number so the
# id can be checked against the filename and grouped into an id-space.
_FRONTMATTER_ID_RE = re.compile(r"^id:\s*([A-Z]+)-(\d+)\s*$", re.MULTILINE)

# Filename shape `<PREFIX>-NNN-<slug>.md`. Captures prefix + number for the
# id-matches-filename sanity check.
_FILENAME_RE = re.compile(r"^([A-Z]+)-(\d+)-.+\.md$")


@dataclass(frozen=True)
class DecisionRecord:
    """One decision record located on disk, with its parsed id."""

    path: Path
    id_space: str  # "core" | "project" | "adr" | "capability:<cap>"
    record_id: str | None  # the frontmatter id (e.g. "COR-001"), or None if unparseable


@dataclass(frozen=True)
class DecisionIssue:
    """One finding — a duplicate id or an id/filename mismatch."""

    location: str  # path relative to target, or "<id-space> :: <id>" for a duplicate
    message: str


@dataclass(frozen=True)
class DecisionValidationReport:
    """Outcome of a decision-id validation run."""

    records_checked: int = 0
    issues: tuple[DecisionIssue, ...] = field(default_factory=tuple)

    @property
    def is_clean(self) -> bool:
        return not self.issues


def validate_decision_ids(target_root: Path) -> DecisionValidationReport:
    """Scan every decision record and report id collisions + id/filename mismatches.

    Walks all four id-spaces, parses each record's frontmatter id, and
    flags any id claimed by more than one file *within the same id-space*
    (cross-id-space duplicates — same number in two capabilities, or a
    `COR-001` alongside a `PRJ-001` — are not collisions). Also flags any
    record whose frontmatter id disagrees with its filename number.
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

    return DecisionValidationReport(
        records_checked=len(records), issues=tuple(issues)
    )


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


def print_report(report: DecisionValidationReport) -> None:
    """Render the report to stdout, mirroring `pkit schemas validate`'s style."""
    if report.is_clean:
        if report.records_checked == 0:
            click.echo("  No decision records found to validate.")
        else:
            click.echo(
                "  "
                + cli_render.style(
                    "strong",
                    f"Validated {report.records_checked} decision record(s). "
                    "No id collisions found.",
                )
            )
        return

    click.echo(
        "  "
        + cli_render.style(
            "strong",
            f"{len(report.issues)} issue(s) found across "
            f"{report.records_checked} decision record(s):",
        )
    )
    for issue in report.issues:
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
    rest = text[len("---"):]
    end = rest.find("\n---")
    if end == -1:
        return None
    return rest[:end]


def _filename_consistency_issues(
    record: DecisionRecord, target_root: Path
) -> list[DecisionIssue]:
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
