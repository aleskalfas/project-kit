"""`pkit validate` — read-only state check per COR-004.

Verifies:

- **Backbone manifest** is present, parseable, and at schema_version 1.
- **Component registry** — each component listed in `.pkit/manifest.yaml`
  has its per-component manifest at the declared path, with a matching
  schema_version.
- **Per-component manifests** — each has the required fields (kind,
  name, version, installed_at, requires_backbone).
- **Decision records** — each `.pkit/decisions/{core,project}/*.md`
  carries valid frontmatter (id, title, status, date, author).

Reports issues with locations + diagnosis. Makes no changes. Exits
non-zero if any issue is found, so CI can gate on it.

What's NOT checked yet (scope deferred to future PRs):

- The full no-shared-files invariant — checking every kit-owned path is
  unmodified relative to source needs source-vs-target diff machinery
  (could surface here or land in a separate `pkit diff` later).
- Per-area schema rules (per area README's own contract) — each area
  needs to surface its validation hook; today only decisions and
  manifests are checked.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import click

from project_kit import cli_render
from project_kit.manifest import (
    BackboneManifest,
    ComponentManifest,
    read_backbone_manifest,
    read_component_manifest,
)


@dataclass(frozen=True)
class Issue:
    """One validation finding. `location` is a path relative to target_root."""

    location: str
    diagnosis: str


REQUIRED_DECISION_FRONTMATTER_KEYS = ("id", "title", "status", "date", "author")
VALID_DECISION_STATUSES = ("proposed", "accepted", "superseded")


def run_validate(target_root: Path) -> list[Issue]:
    """Walk the kit's state, return all issues found. Empty list = clean."""
    if not (target_root / ".pkit").is_dir():
        raise click.ClickException(f"{target_root}/.pkit/ does not exist. Run 'pkit init' first.")

    issues: list[Issue] = []
    backbone = read_backbone_manifest(target_root)

    issues.extend(_validate_backbone_manifest(target_root, backbone))
    if backbone is not None:
        issues.extend(_validate_component_registry(target_root, backbone))
    issues.extend(_validate_decisions(target_root))

    return issues


def print_validate_report(target_root: Path, issues: list[Issue]) -> None:
    """Pretty-print validate findings. Mirrors the spec in `.pkit/cli/README.md`."""
    click.echo()
    click.echo(cli_render.style("title", f"Validating {target_root}"))
    click.echo()
    if not issues:
        click.echo("  " + cli_render.style("strong", "All checks passed."))
        click.echo()
        return

    click.echo("  " + cli_render.style("strong", f"{len(issues)} issue(s) found:"))
    for issue in issues:
        click.echo(f"    {issue.location}")
        click.echo(f"      → {issue.diagnosis}")
    click.echo()


def _validate_backbone_manifest(
    target_root: Path, backbone: BackboneManifest | None
) -> list[Issue]:
    """Check the backbone manifest exists, parses, and has the expected schema."""
    if backbone is None:
        return [
            Issue(
                location=".pkit/manifest.yaml",
                diagnosis="missing — run 'pkit init' or 'pkit sync' to seed the backbone manifest.",
            )
        ]

    issues: list[Issue] = []
    if backbone.schema_version != 1:
        issues.append(
            Issue(
                location=".pkit/manifest.yaml",
                diagnosis=f"unexpected schema_version {backbone.schema_version} "
                f"(expected 1); manifest may need a schema-migration "
                f"per the lifecycle spec.",
            )
        )
    if not backbone.backbone_version:
        issues.append(
            Issue(
                location=".pkit/manifest.yaml",
                diagnosis="missing or empty `backbone_version` field.",
            )
        )
    return issues


def _validate_component_registry(target_root: Path, backbone: BackboneManifest) -> list[Issue]:
    """Check every registered component has its per-component manifest at the declared path."""
    issues: list[Issue] = []
    for entry in backbone.components:
        manifest_path = target_root / entry.manifest
        if not manifest_path.is_file():
            # Adapters don't always have a per-component manifest yet
            # (the adapter side of COR-010 is still being built out).
            # Capabilities don't either — they propagate via sync, not via
            # an install-time stamp like the retired bundle pattern did.
            continue

        component = read_component_manifest(manifest_path)
        if component is None:
            issues.append(
                Issue(
                    location=entry.manifest,
                    diagnosis="component manifest exists but failed to parse.",
                )
            )
            continue

        issues.extend(_validate_component_manifest_fields(entry.manifest, component))
        if component.name != entry.name:
            issues.append(
                Issue(
                    location=entry.manifest,
                    diagnosis=f"component name mismatch: registry says "
                    f"'{entry.name}', manifest says '{component.name}'.",
                )
            )
        if component.kind != entry.kind:
            issues.append(
                Issue(
                    location=entry.manifest,
                    diagnosis=f"component kind mismatch: registry says "
                    f"'{entry.kind}', manifest says '{component.kind}'.",
                )
            )
    return issues


def _validate_component_manifest_fields(location: str, component: ComponentManifest) -> list[Issue]:
    issues: list[Issue] = []
    if not component.version:
        issues.append(
            Issue(location=location, diagnosis="component manifest is missing `version`.")
        )
    if not component.installed_at:
        issues.append(
            Issue(location=location, diagnosis="component manifest is missing `installed_at`.")
        )
    if not component.requires_backbone:
        issues.append(
            Issue(location=location, diagnosis="component manifest is missing `requires_backbone`.")
        )
    return issues


def _validate_decisions(target_root: Path) -> list[Issue]:
    """Walk decisions/{core,project}/ and validate each record's frontmatter."""
    issues: list[Issue] = []
    decisions_dir = target_root / ".pkit" / "decisions"
    if not decisions_dir.is_dir():
        return issues

    for namespace in ("core", "project"):
        ns_dir = decisions_dir / namespace
        if not ns_dir.is_dir():
            continue
        for record in sorted(ns_dir.glob("*.md")):
            if record.name == "README.md":
                continue
            issues.extend(_validate_decision_record(target_root, record))
    return issues


def _validate_decision_record(target_root: Path, record: Path) -> list[Issue]:
    rel = str(record.relative_to(target_root))
    text = record.read_text(encoding="utf-8")

    if not text.startswith("---"):
        return [Issue(location=rel, diagnosis="missing YAML frontmatter (no leading `---`).")]

    parts = text.split("---", 2)
    if len(parts) < 3:
        return [Issue(location=rel, diagnosis="malformed frontmatter (no closing `---`).")]

    frontmatter_text = parts[1]
    frontmatter_keys: dict[str, str] = {}
    for line in frontmatter_text.splitlines():
        match = re.match(r"^(\w+):\s*(.*)$", line)
        if match:
            frontmatter_keys[match.group(1)] = match.group(2).strip()

    issues: list[Issue] = []
    for key in REQUIRED_DECISION_FRONTMATTER_KEYS:
        if key not in frontmatter_keys or not frontmatter_keys[key]:
            issues.append(
                Issue(location=rel, diagnosis=f"frontmatter missing required key `{key}`.")
            )

    status = frontmatter_keys.get("status", "")
    if status and status not in VALID_DECISION_STATUSES:
        issues.append(
            Issue(
                location=rel,
                diagnosis=f"status `{status}` is not one of {VALID_DECISION_STATUSES}.",
            )
        )

    return issues
