"""The release step — the sole main-only writer of version state (PRJ-002 D3).

A *release* consumes the pending changesets under `.changes/unreleased/`,
computes each tier's new version from the current state on `main`, writes
the version numbers, broadens kit-shipped components' `requires_backbone`
(the broaden moves here per PRJ-002 D4), generates the changelog, deletes
the consumed changesets, and (for a backbone bump) cuts the tag via the
existing `tag_version` (PRJ-004).

Cutover note (PRJ-002 D-implications): this module *adds* the release-
authority path; it does not retire `pkit version bump`. Both broaden
`requires_backbone` today (broadening is idempotent) — retiring the
in-branch bump is a downstream step once this path is trusted.

Layering follows the house convention (thin CLI shim, logic in a module):
everything here is unit-testable without Click; `cli.py` resolves context,
calls these functions, and translates errors.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import click

from project_kit import versioning
from project_kit.changesets import (
    BACKBONE,
    Changeset,
    Component,
    discover_components,
    load_changesets,
    segment_rank,
)

# Rewrites a component's `version:` line in its package.yaml. Anchored to a
# leading indent so top-level `schema_version:` is never matched; regex (not
# a YAML round-trip) to preserve quoting, key order, and trailing comments —
# same discipline as versioning.py's requires_backbone rewrite.
_COMPONENT_VERSION_RE = re.compile(r"(?m)^(\s+version:\s*)(\d+\.\d+\.\d+)")

# Repo-root-relative path prefixes whose changes count as touching the
# backbone's surface, for the changeset guard. A heuristic — see the "Limits"
# section of `.pkit/release/README.md`. Kept as reviewable data, not buried
# in logic. Component (adapter/capability) subtrees are handled separately
# via each Component.subtree, and are excluded from these prefixes.
BACKBONE_SURFACE_PREFIXES: tuple[str, ...] = (
    "src/project_kit/",
    ".pkit/VERSION",
    ".pkit/cli/",
    ".pkit/schemas/",
    ".pkit/rules/",
    ".pkit/lifecycle/",
    ".pkit/process/",
    ".pkit/permissions/",
    ".pkit/agents/core/",
    ".pkit/decisions/core/",
    ".pkit/adapters/README.md",
    ".pkit/manifest.yaml",
)

# The changelog file the release step maintains, at the repo root.
CHANGELOG_NAME = "CHANGELOG.md"


@dataclass(frozen=True)
class ComponentRelease:
    """A single tier's computed bump within a release."""

    component: Component
    segment: str  # the highest non-`none` segment across the tier's changesets
    old_version: str
    new_version: str
    notes: list[str]


@dataclass(frozen=True)
class ReleasePlan:
    """The full computed release: which tiers bump, and what to consume."""

    releases: list[ComponentRelease]  # tiers that actually move (segment != none)
    consumed: list[Changeset]  # every pending changeset (incl. `none`) to delete

    @property
    def backbone(self) -> ComponentRelease | None:
        return next((r for r in self.releases if r.component.name == BACKBONE), None)

    @property
    def is_empty(self) -> bool:
        return not self.releases


def compute_release(source_kit: Path) -> ReleasePlan:
    """Compute the release from the current state + pending changesets.

    Groups changesets by component, takes the highest segment per component,
    and computes each moving tier's new version from its current version.
    `none`-only components are consumed but do not move. Raises
    `click.ClickException` if a changeset names an unknown component.
    """
    components = {c.name: c for c in discover_components(source_kit)}
    changesets = load_changesets(source_kit.parent)

    grouped: dict[str, list[Changeset]] = {}
    for cs in changesets:
        if cs.component not in components:
            raise click.ClickException(
                f"changeset {cs.path.name} names unknown component {cs.component!r}. "
                f"Known: {', '.join(sorted(components))}."
            )
        grouped.setdefault(cs.component, []).append(cs)

    releases: list[ComponentRelease] = []
    for name in sorted(grouped, key=lambda n: (n != BACKBONE, n)):
        group = grouped[name]
        top = max(group, key=lambda cs: segment_rank(cs.segment)).segment
        if top == "none":
            continue  # declared no-bump; consumed only
        component = components[name]
        releases.append(
            ComponentRelease(
                component=component,
                segment=top,
                old_version=component.version,
                new_version=versioning.next_version(component.version, top),  # type: ignore[arg-type]
                notes=[cs.note for cs in group if cs.note],
            )
        )

    return ReleasePlan(releases=releases, consumed=changesets)


def apply_release(
    source_kit: Path,
    plan: ReleasePlan,
    *,
    tag: bool = False,
    push: bool = False,
    today: date | None = None,
) -> None:
    """Write the release: versions, broaden, changelog, delete.

    The order matters — versions and the requires_backbone broaden land
    first, then the changelog is prepended, then the consumed changesets are
    deleted. Idempotent inputs only: re-running with an empty plan is a no-op.

    Tagging is **off by default** and deliberately a separate step, matching
    the codebase's anchoring principle (bump writes; `pkit version tag` tags —
    per COR-004). PRJ-004 tags the *committed* `.pkit/VERSION`, so the tag must
    point at the release commit — which does not exist yet when `apply` runs.
    The intended sequence is: `apply` → commit the release → merge to `main` →
    `pkit version tag --push` on `main`. Pass `tag=True` only when HEAD is
    already the release commit (e.g. re-running on `main` post-merge).
    """
    if plan.is_empty:
        click.echo("No pending changesets move a version — nothing to release.")
        # Still consume any `none`-only changesets so the tree is clean.
        _delete_changesets(plan.consumed)
        return

    backbone = plan.backbone
    for rel in plan.releases:
        if rel.component.name == BACKBONE:
            rel.component.version_path.write_text(f"{rel.new_version}\n", encoding="utf-8")
            click.echo(f"Backbone: {rel.old_version} -> {rel.new_version}")
        else:
            _write_component_version(rel)

    # Broaden kit components' requires_backbone at the release step (D4),
    # driven by the NEW backbone version — only when the backbone moved.
    if backbone is not None:
        major, minor = (int(p) for p in backbone.new_version.split(".")[:2])
        versioning._broaden_kit_components_requires_backbone(source_kit, major, minor)

    _write_changelog(source_kit.parent, plan, today or date.today())
    _delete_changesets(plan.consumed)

    if tag and backbone is not None:
        versioning.tag_version(source_kit, push=push)
    elif backbone is not None:
        click.echo(
            "Next: commit the release, then `pkit version tag --push` on main "
            f"to cut v{backbone.new_version} (PRJ-004)."
        )


def _write_component_version(rel: ComponentRelease) -> None:
    path = rel.component.version_path
    original = path.read_text(encoding="utf-8")
    updated, count = _COMPONENT_VERSION_RE.subn(rf"\g<1>{rel.new_version}", original, count=1)
    if count == 0:
        raise click.ClickException(
            f"could not find a `version:` line to rewrite in {path} "
            f"(component {rel.component.name!r})"
        )
    path.write_text(updated, encoding="utf-8")
    click.echo(f"{rel.component.name}: {rel.old_version} -> {rel.new_version}")


def render_changelog_entry(plan: ReleasePlan, when: date) -> str:
    """Render the markdown block for this release from the changeset notes.

    Keyed by the backbone's new version when the backbone moved, else by
    date (a component-only release has no backbone tag to key on).
    """
    backbone = plan.backbone
    heading = backbone.new_version if backbone is not None else when.isoformat()
    lines = [f"## {heading} — {when.isoformat()}", ""]
    for rel in plan.releases:
        lines.append(f"### {rel.component.name} ({rel.old_version} → {rel.new_version})")
        for note in rel.notes:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _write_changelog(repo_root: Path, plan: ReleasePlan, when: date) -> None:
    changelog = repo_root / CHANGELOG_NAME
    entry = render_changelog_entry(plan, when)
    title = "# Changelog\n\n"
    prior = ""
    if changelog.is_file():
        existing = changelog.read_text(encoding="utf-8")
        # Keep any existing `# ` title line; the rest is prior entries.
        if existing.startswith("# "):
            title = existing.split("\n", 1)[0] + "\n\n"
            prior = existing.split("\n", 1)[1].lstrip()
        else:
            prior = existing.lstrip()
    tail = f"\n{prior}" if prior else ""
    changelog.write_text(f"{title}{entry}{tail}", encoding="utf-8")
    click.echo(f"Updated {CHANGELOG_NAME}")


def _delete_changesets(changesets: list[Changeset]) -> None:
    for cs in changesets:
        cs.path.unlink(missing_ok=True)
    if changesets:
        click.echo(f"Consumed {len(changesets)} changeset(s).")


# --- The surface-without-changeset CI guard (PRJ-002 implications) -------


@dataclass(frozen=True)
class GuardResult:
    """Outcome of the changeset guard for one diff."""

    touched: list[str]  # components whose surface the diff touched
    missing: list[str]  # touched components with no changeset (the violations)
    skipped: bool  # the escape hatch (label / --skip) was active

    @property
    def ok(self) -> bool:
        return self.skipped or not self.missing


def changed_files(repo_root: Path, base: str) -> list[str]:
    """Repo-root-relative paths changed between `base` and HEAD.

    Uses the merge-base form (`base...HEAD`) so only the branch's own
    changes count — mirroring how the migration-coverage check scopes a PR.
    """
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def touched_components(components: list[Component], files: list[str]) -> list[str]:
    """Which components' surface the changed `files` touched (heuristic).

    A component (adapter/capability) is touched if any changed file is under
    its subtree; the backbone is touched if any changed file matches a
    `BACKBONE_SURFACE_PREFIXES` entry. This is a path heuristic — surface is
    ultimately a human judgment (PRJ-002 D2) — so it can false-positive and
    false-negative; the `none`-changeset / label escape hatch is the override.
    """
    touched: list[str] = []
    for component in components:
        if component.name == BACKBONE:
            hit = any(_matches_prefix(f, BACKBONE_SURFACE_PREFIXES) for f in files)
        else:
            subtree = f"{component.subtree}/" if component.subtree else None
            hit = subtree is not None and any(f.startswith(subtree) for f in files)
        if hit:
            touched.append(component.name)
    return touched


def _matches_prefix(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path == p or path.startswith(p) for p in prefixes)


def check_changesets(source_kit: Path, base: str, *, skip: bool = False) -> GuardResult:
    """Run the surface-without-changeset guard against the diff vs `base`.

    Passes (ok) when every surface-touched component has at least one
    changeset naming it (any kind, including `none`), or when the escape
    hatch is active (`skip=True`, wired from the `skip-changeset` PR label).
    """
    components = discover_components(source_kit)
    files = changed_files(source_kit.parent, base)
    touched = touched_components(components, files)

    declared = {cs.component for cs in load_changesets(source_kit.parent)}
    missing = [name for name in touched if name not in declared]
    return GuardResult(touched=touched, missing=missing, skipped=skip)
