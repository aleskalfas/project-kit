"""The `manifests` and `decisions` front-matter checks of `pkit validate` (COR-004).

Two of the umbrella's members (`project_kit.validators`, ADR-058) live here:

- **`manifests`** — the backbone manifest is present, parseable and at
  schema_version 1; each component listed in `.pkit/manifest.yaml` whose
  per-component manifest exists at the declared path has one that parses and
  carries the required fields (kind, name, version, installed_at,
  requires_backbone) and a matching name and kind. A missing manifest is
  skipped: adapters and capabilities propagate through sync and stamp none.
- **`decisions`**, the front-matter half — each `.pkit/decisions/{core,project}/*.md`
  carries valid front matter (id, title, status, date, author). The id-space
  half is `decisions_validate`, which composes both into the member.

Every finding is an error; the checks read only.

Not checked here: the full no-shared-files invariant — whether every kit-owned
path is unmodified relative to the source — needs source-vs-target diff
machinery (a later `pkit diff`, or a member of its own).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import click

from project_kit.manifest import (
    BackboneManifest,
    ComponentManifest,
    read_backbone_manifest,
    read_component_manifest,
)
from project_kit.validators import Finding, Outcome


@dataclass(frozen=True)
class Issue:
    """One validation finding. `location` is a path relative to target_root."""

    location: str
    diagnosis: str


REQUIRED_DECISION_FRONTMATTER_KEYS = ("id", "title", "status", "date", "author")
VALID_DECISION_STATUSES = ("proposed", "accepted", "superseded")


def run_validate(target_root: Path) -> list[Issue]:
    """The manifests and decision front-matter checks together; empty = clean.
    `pkit validate` runs them as the `manifests` and `decisions` members."""
    if not (target_root / ".pkit").is_dir():
        raise click.ClickException(f"{target_root}/.pkit/ does not exist. Run 'pkit init' first.")
    return [*manifest_issues(target_root), *decision_frontmatter_issues(target_root)]


def manifest_issues(target_root: Path) -> list[Issue]:
    """The backbone manifest and the component registry it lists."""
    backbone = read_backbone_manifest(target_root)
    issues = _validate_backbone_manifest(target_root, backbone)
    if backbone is not None:
        issues.extend(_validate_component_registry(target_root, backbone))
    return issues


def decision_frontmatter_issues(target_root: Path) -> list[Issue]:
    """Every decision record's front matter, under `.pkit/decisions/{core,project}/`."""
    return _validate_decisions(target_root)


def manifests_outcome(target_root: Path) -> Outcome:
    """The `manifests` member of `pkit validate`."""
    backbone = read_backbone_manifest(target_root)
    issues = manifest_issues(target_root)
    if backbone is None:
        state = "no backbone manifest"
    else:
        version = backbone.backbone_version or "(unversioned)"
        state = (
            f"backbone {version}, schema_version {backbone.schema_version}; "
            f"{len(backbone.components)} component(s) registered"
        )
    findings = tuple(Finding(issue.location, issue.diagnosis) for issue in issues)
    return Outcome((f"{state}; {len(findings)} error(s).",), findings)


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
    """Check each registered component's per-component manifest where one exists; skip a missing
    one."""
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
