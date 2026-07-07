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

import json
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
from project_kit.migrations import _VERSION_DIR_RE, parse_version_tuple

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


# The Keep-a-Changelog category set, in its canonical display order. This is
# the universal KaC grouping — hardcoded here because it is a fixed, shared
# convention, not a project-specific list. `Changed` is the default when a
# changeset declares no category.
CHANGELOG_CATEGORIES: tuple[str, ...] = (
    "Added",
    "Changed",
    "Deprecated",
    "Removed",
    "Fixed",
    "Security",
)
DEFAULT_CATEGORY = "Changed"

# Extracts the trailing number from a `pr` value so a bare number (`465`) or a
# full URL (`.../pull/465`) both yield the `[#465]` link label.
_PR_NUMBER_RE = re.compile(r"(\d+)\D*$")


@dataclass(frozen=True)
class ComponentRelease:
    """A single tier's computed bump within a release."""

    component: Component
    segment: str  # the highest non-`none` segment across the tier's changesets
    old_version: str
    new_version: str
    changesets: list[Changeset]  # the source changesets (carry notes + categories)

    @property
    def notes(self) -> list[str]:
        """The non-empty changelog notes, in changeset order."""
        return [cs.note for cs in self.changesets if cs.note]


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
                changesets=group,
            )
        )

    return ReleasePlan(releases=releases, consumed=changesets)


def apply_release(
    source_kit: Path,
    plan: ReleasePlan,
    *,
    tag: bool = False,
    push: bool = False,
    broaden: bool = True,
    today: date | None = None,
) -> None:
    """Write the release: versions, broaden, changelog, delete.

    The order matters — versions and the requires_backbone broaden land
    first, then the changelog is prepended, then the consumed changesets are
    deleted. Idempotent inputs only: re-running with an empty plan is a no-op.

    The broaden step has two shapes, keyed on what moved:

    - **Backbone release** — widen *every* kit-shipped component's upper bound
      to cover the new backbone minor (the long-standing PRJ-002 D4 broaden).
    - **Component release** — widen each *released* component's own upper bound
      to cover the repo's **current** backbone (`.pkit/VERSION`), i.e. the
      backbone the author is releasing under / tested against. This is #494's
      author-side auto-broaden: a component released under backbone X asserts
      compatibility with X (COR-041). Keyed on "a component moved under backbone
      X", not on being project-kit, so it fires in any adopter's repo.

    Both are **widen-only** (never narrow a wider existing bound) and
    reuse `versioning`'s regex rewrite. `broaden=False` (the `--no-broaden`
    flag) skips the step for an author who deliberately does not want to claim
    the current backbone.

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

    if broaden:
        _broaden_at_release(source_kit, plan)

    _write_changelog(source_kit.parent, plan, today or date.today())
    _delete_changesets(plan.consumed)

    if tag and backbone is not None:
        versioning.tag_version(source_kit, push=push)
    elif backbone is not None:
        click.echo(
            "Next: commit the release, then `pkit version tag --push` on main "
            f"to cut v{backbone.new_version} (PRJ-004)."
        )


def _broaden_at_release(source_kit: Path, plan: ReleasePlan) -> None:
    """Broaden `requires_backbone` for the moving tiers (PRJ-002 D4 + #494).

    A backbone release widens every kit-shipped component to the new backbone
    minor (the original D4 broaden). A component release widens each released
    component's own bound to cover the repo's current backbone — the version
    the author releases under (#494 / COR-041). The two are complementary, not
    exclusive: a mixed release (backbone + a component in one plan) runs the
    backbone broaden, which already covers every component including the moved
    one, so the per-component step is only reached for a component release with
    no backbone move.
    """
    backbone = plan.backbone
    if backbone is not None:
        # Backbone moved — widen every component to the new backbone minor.
        major, minor = (int(p) for p in backbone.new_version.split(".")[:2])
        versioning._broaden_kit_components_requires_backbone(source_kit, major, minor)
        return

    # Component-only release — widen each released component's own bound to the
    # repo's current backbone (the version being released under / tested with).
    current_backbone = (source_kit / "VERSION").read_text(encoding="utf-8").strip()
    for rel in plan.releases:
        if rel.component.name == BACKBONE:
            continue  # unreachable here (backbone is None), but keep the guard explicit
        rel_path = rel.component.version_path.relative_to(source_kit)
        changed = versioning.broaden_component_requires_backbone(
            rel.component.version_path, current_backbone
        )
        if changed is not None:
            click.echo(f"  broadened {rel_path}: {changed} (covers backbone {current_backbone})")


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
    """Render the Keep-a-Changelog block for this release.

    The section is keyed by the backbone's new version + date when the
    backbone moved, else by date alone (a component-only release has no
    backbone tag to key on). Entries are grouped under Keep-a-Changelog
    category headings; a component that is *not* the backbone is tagged inline
    with its name + new version so a date-keyed section still surfaces which
    component moved. `pr` references become reference-style `([#N])` links,
    resolved in a block at the foot of the section (omitted when absent).
    """
    backbone = plan.backbone
    if backbone is not None:
        lines = [f"## {backbone.new_version} — {when.isoformat()}", ""]
    else:
        lines = [f"## {when.isoformat()}", ""]

    grouped: dict[str, list[str]] = {}
    refs: dict[str, str] = {}  # link label -> target, for the trailing block
    for rel in plan.releases:
        is_backbone = rel.component.name == BACKBONE
        for cs in rel.changesets:
            if not cs.note:
                continue
            text = cs.note
            if not is_backbone:
                text = f"**{rel.component.name} {rel.new_version}** — {text}"
            if cs.pr:
                label = _pr_label(cs.pr)
                if label is not None:
                    text = f"{text} ([#{label}])"
                    refs.setdefault(label, cs.pr)
            grouped.setdefault(cs.category or DEFAULT_CATEGORY, []).append(text)

    # Canonical KaC order first; any unrecognised category is preserved after,
    # so a typo is visible in the output rather than silently dropped.
    ordered = list(CHANGELOG_CATEGORIES) + [c for c in grouped if c not in CHANGELOG_CATEGORIES]
    for category in ordered:
        entries = grouped.get(category)
        if not entries:
            continue
        lines.append(f"### {category}")
        lines.extend(f"- {entry}" for entry in entries)
        lines.append("")

    if refs:
        lines.extend(f"[#{label}]: {refs[label]}" for label in sorted(refs, key=int))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _pr_label(pr: str) -> str | None:
    """The `#N` link label for a `pr` value (a bare number or a PR URL)."""
    match = _PR_NUMBER_RE.search(pr)
    return match.group(1) if match else None


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


# --- Automation-facing summary + migration-dir alignment -----------------


def release_summary(source_kit: Path, plan: ReleasePlan) -> dict[str, object]:
    """A machine-readable summary of a computed release, for automation.

    Emitted as JSON by `pkit release plan --json` so the release-PR workflow
    can decide whether to open a release PR (`empty`), name the branch/tag
    (`backbone_version`), render the PR body (`releases`), and surface the
    migration-dir prediction warnings (`migration_warnings`).
    """
    backbone = plan.backbone
    return {
        "empty": plan.is_empty,
        "backbone_version": backbone.new_version if backbone is not None else None,
        "releases": [
            {
                "component": rel.component.name,
                "old_version": rel.old_version,
                "new_version": rel.new_version,
                "segment": rel.segment,
                "notes": list(rel.notes),
            }
            for rel in plan.releases
        ],
        "changesets_consumed": len(plan.consumed),
        "migration_warnings": migration_dir_mismatches(source_kit, plan),
    }


def migration_dir_mismatches(source_kit: Path, plan: ReleasePlan) -> list[str]:
    """Backbone migration dirs whose predicted version the release won't cut.

    Migration dirs are named `<X.Y.0>` and authored in the same change-set as
    the surface change they migrate (COR-010) — so their name *predicts* the
    release version before the release step computes it. A dir naming a version
    above the current `.pkit/VERSION` that the computed release will NOT produce
    is an orphaned prediction (the migration-dir-prediction coupling flagged on
    #465). Returns human-readable warnings; empty when aligned.

    Non-fatal by design: surface is a human judgment (PRJ-002 D2) and a dir may
    legitimately target a later release, so this only warns — it never blocks.
    Backbone-only: per-component tags/dirs are out of scope (PRJ-004).
    """
    root = source_kit / "migrations" / "backbone"
    if not root.is_dir():
        return []

    current = (source_kit / "VERSION").read_text(encoding="utf-8").strip()
    current_minor = parse_version_tuple(current)[:2]
    backbone = plan.backbone
    computed_minor = parse_version_tuple(backbone.new_version)[:2] if backbone is not None else None

    warnings: list[str] = []
    for entry in sorted(root.iterdir()):
        if not (entry.is_dir() and _VERSION_DIR_RE.match(entry.name)):
            continue
        dir_minor = parse_version_tuple(entry.name)[:2]
        if dir_minor <= current_minor:
            continue  # at/below the released version — history, not a prediction
        if computed_minor is None:
            warnings.append(
                f"migration dir backbone/{entry.name} predicts a backbone release, but "
                f"the computed release moves no backbone version (stale prediction? see #465)."
            )
        elif dir_minor != computed_minor:
            warnings.append(
                f"migration dir backbone/{entry.name} does not match the computed backbone "
                f"release {backbone.new_version} (stale version prediction? see #465)."
            )
    return warnings


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


# --- The changeset + changelog format lint (the OBJECTIVE subset) ---------
#
# A *format* lint distinct from the surface guard above: the guard asks
# "does a surface change carry a changeset?"; this asks "is the changeset /
# changelog *well-formed*?". It validates only the mechanically-checkable
# subset — category enum, body shape, changelog heading structure — and makes
# no attempt at the plain-language / no-jargon discipline, which is human
# judgment left to the guide (`.pkit/release/README.md`) and review. Same
# honest stance as the guard: a **reminder, not a proof**, with an escape
# hatch for the cases an objective rule necessarily mis-fires on.

# A body that is *only* one of these bare references is the objective proxy for
# the "no in-body jargon / references" rule — an entry that says nothing to a
# reader who cannot resolve the reference. Full-match (whole stripped body).
_BARE_REF_RE = re.compile(r"(?:#\d+|ADR-\d+|DEC-\d+|COR-\d+|https?://\S+)", re.IGNORECASE)

# Accepted release-section (`## `) heading shapes. Two forms the generator
# emits (see `render_changelog_entry`): a version optionally dated, or a
# date-only section (a component-only release with no backbone key). The `—`
# em-dash is what the generator writes; a plain `-` and the canonical KaC
# `[version]` brackets are also accepted so a hand-edit in either idiom passes.
_CHANGELOG_VERSION_HEADING_RE = re.compile(
    r"^## \[?\d+\.\d+\.\d+\]?(?: [—-] \d{4}-\d{2}-\d{2})?$"
)
_CHANGELOG_DATE_HEADING_RE = re.compile(r"^## \d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class FormatViolation:
    """One objective format problem the lint found."""

    source: str  # where it is, e.g. `changeset foo.yaml` or `CHANGELOG.md:12`
    message: str  # what is wrong (and, where useful, how to fix)


@dataclass(frozen=True)
class LintResult:
    """Outcome of the format lint across all changesets + the changelog."""

    violations: list[FormatViolation]
    skipped: bool  # the escape hatch was active

    @property
    def ok(self) -> bool:
        return self.skipped or not self.violations


def lint_changeset(cs: Changeset) -> list[FormatViolation]:
    """Objective format checks for one changeset.

    Category (when present) must be a Keep-a-Changelog group. Body checks only
    apply to changesets that move a version (`segment != "none"`) — a `none`
    changeset never produces a changelog line, so its body carries no
    changelog-format obligation. A body that does become a changelog line must
    be non-empty, not *solely* a bare reference, capitalized, and end with a
    period.
    """
    where = f"changeset {cs.path.name}"
    violations: list[FormatViolation] = []

    if cs.category is not None and cs.category not in CHANGELOG_CATEGORIES:
        violations.append(
            FormatViolation(
                where,
                f"unknown category {cs.category!r} — expected one of "
                f"{', '.join(CHANGELOG_CATEGORIES)}.",
            )
        )

    if cs.segment == "none":
        return violations  # no changelog line ⇒ no body-format obligation

    body = cs.note
    if not body:
        violations.append(FormatViolation(where, "body is empty."))
        return violations  # the remaining body checks are moot without a body

    if _BARE_REF_RE.fullmatch(body):
        violations.append(
            FormatViolation(
                where,
                f"body is only the bare reference {body!r} — write a plain, "
                "user-facing sentence describing the change.",
            )
        )
    if body[0].islower():
        violations.append(
            FormatViolation(where, f"body should start capitalized: {body!r}.")
        )
    if not body.endswith("."):
        violations.append(FormatViolation(where, f"body should end with a period: {body!r}."))

    return violations


def lint_changelog(text: str) -> list[FormatViolation]:
    """Objective structural checks for `CHANGELOG.md`.

    Only the heading *structure* is checked — release-section (`## `) headings
    must match the generator's shape, and category (`### `) headings must be a
    known Keep-a-Changelog group. The entry text itself is not linted (its
    plain-language quality is human judgment, per the guide).
    """
    violations: list[FormatViolation] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip()
        where = f"{CHANGELOG_NAME}:{lineno}"
        if line.startswith("### "):
            category = line[4:].strip()
            if category not in CHANGELOG_CATEGORIES:
                violations.append(
                    FormatViolation(
                        where,
                        f"unknown category heading {category!r} — expected one of "
                        f"{', '.join(CHANGELOG_CATEGORIES)}.",
                    )
                )
        elif line.startswith("## "):
            if not (
                _CHANGELOG_VERSION_HEADING_RE.match(line)
                or _CHANGELOG_DATE_HEADING_RE.match(line)
            ):
                violations.append(
                    FormatViolation(
                        where,
                        f"malformed release heading {line!r} — expected "
                        "`## <version> — <date>` or `## <date>`.",
                    )
                )
    return violations


def lint_release_format(source_kit: Path, *, skip: bool = False) -> LintResult:
    """Run the objective format lint over pending changesets + `CHANGELOG.md`.

    Passes (ok) when every changeset and the changelog are well-formed, or when
    the escape hatch is active (`skip=True`, wired from a `--skip` flag / the
    `PKIT_CHANGELOG_LINT_SKIP` env var). Reads committed files only; it needs
    no PR context, so it runs in the shared check aggregator.
    """
    repo_root = source_kit.parent
    violations: list[FormatViolation] = []
    for cs in load_changesets(repo_root):
        violations.extend(lint_changeset(cs))

    changelog = repo_root / CHANGELOG_NAME
    if changelog.is_file():
        violations.extend(lint_changelog(changelog.read_text(encoding="utf-8")))

    return LintResult(violations=violations, skipped=skip)


# --- The sanctioned release-PR merge path (#475) -------------------------
#
# A release PR (`chore(release): vX` on a `release/*` head) closes no issue, so
# the pm capability's issue-PR merge gate — which *requires* a `Closes #N`
# reference — legitimately refuses it. That gate is universal (adopters install
# it) and must stay project-neutral: a "release PR" is project-kit's own
# release-flow concept and does not belong in it (COR-014). This is the release
# flow's own merge verb — it already owns the release-PR lifecycle
# (the release flow opens the PR and tags it post-merge). It is
# guarded to `release/*` heads so it is not a general issue-PR-gate bypass, and
# it is project-neutral: it merges a PR *by number*, deriving the repo from the
# ambient `gh` context (the git remote), with no hardcoded owner/repo.

# The head-branch prefix `release-pr.yml` uses for the release branch, and the
# Conventional-Commits title prefix it commits under — the two markers that
# identify a release PR. Both are project-kit's release-flow convention.
RELEASE_BRANCH_PREFIX = "release/"
RELEASE_TITLE_PREFIX = "chore(release):"

# CheckRun conclusions / StatusContext states that count as "not blocking a
# merge". SKIPPED and NEUTRAL are non-failures; everything else that is not
# SUCCESS (a failure, or a still-running/pending check) blocks the merge.
_CHECK_PASSING_OUTCOMES = frozenset({"SUCCESS", "NEUTRAL", "SKIPPED"})


@dataclass(frozen=True)
class ReleasePrState:
    """The GitHub PR fields the release-merge gate reads (parsed from `gh`)."""

    number: int
    title: str
    state: str  # OPEN / MERGED / CLOSED (normalised upper-case)
    head_ref: str  # the PR's head branch (headRefName)
    url: str
    mergeable: str  # MERGEABLE / CONFLICTING / UNKNOWN (normalised upper-case)
    checks_passing: bool
    failing_checks: tuple[str, ...]  # names (+ outcome) of non-passing checks


@dataclass(frozen=True)
class ReleaseMergeDecision:
    """The gate's verdict on a release PR."""

    action: str  # "merge" | "already-done" | "refuse"
    message: str


def summarize_checks(rollup: list[dict] | None) -> tuple[bool, tuple[str, ...]]:
    """Reduce a `statusCheckRollup` to (all-passing, non-passing-check-labels).

    Handles both node shapes GitHub returns: a CheckRun carries `status`
    (COMPLETED / IN_PROGRESS / QUEUED) + `conclusion` (SUCCESS / FAILURE / …);
    a StatusContext carries `state` (SUCCESS / FAILURE / PENDING / ERROR). A
    check passes only when its outcome is a non-failing terminal one; a
    still-running check blocks (a release PR must be green before merging). An
    empty rollup (no checks configured) is treated as passing.
    """
    failing: list[str] = []
    for check in rollup or []:
        name = check.get("name") or check.get("context") or "check"
        state = str(check.get("state") or "").upper()
        status = str(check.get("status") or "").upper()
        conclusion = str(check.get("conclusion") or "").upper()
        if state:  # StatusContext
            outcome = state
        elif status and status != "COMPLETED":  # CheckRun still running/queued
            outcome = status
        else:  # completed CheckRun
            outcome = conclusion or "PENDING"
        if outcome not in _CHECK_PASSING_OUTCOMES:
            failing.append(f"{name} ({outcome})")
    return (not failing, tuple(failing))


def parse_release_pr(raw: dict) -> ReleasePrState:
    """Build a `ReleasePrState` from the JSON `gh pr view --json …` returns."""
    passing, failing = summarize_checks(raw.get("statusCheckRollup"))
    return ReleasePrState(
        number=int(raw.get("number", 0)),
        title=str(raw.get("title", "")),
        state=str(raw.get("state", "")).upper(),
        head_ref=str(raw.get("headRefName", "")),
        url=str(raw.get("url", "")),
        mergeable=str(raw.get("mergeable", "")).upper(),
        checks_passing=passing,
        failing_checks=failing,
    )


def evaluate_release_pr(pr: ReleasePrState) -> ReleaseMergeDecision:
    """Decide whether a release PR may be merged — pure, no I/O.

    Guards first that the PR *is* a release PR (a `release/*` head under a
    `chore(release):` title); a non-release PR is refused with a pointer to the
    issue-PR gate. An already-merged or closed PR reports cleanly (idempotent —
    not an error). An open release PR merges only when GitHub reports it
    mergeable and every required check is green.
    """
    if not pr.head_ref.startswith(RELEASE_BRANCH_PREFIX):
        return ReleaseMergeDecision(
            "refuse",
            f"PR #{pr.number} head branch {pr.head_ref!r} is not a release branch "
            f"({RELEASE_BRANCH_PREFIX}*). `pkit release merge` only merges release PRs; "
            f"use `pkit project-management merge-pr {pr.number}` for an issue PR.",
        )
    if not pr.title.startswith(RELEASE_TITLE_PREFIX):
        return ReleaseMergeDecision(
            "refuse",
            f"PR #{pr.number} title {pr.title!r} is not a release title (expected a "
            f"{RELEASE_TITLE_PREFIX!r} prefix). Refusing to merge a non-release PR "
            f"through `pkit release merge`.",
        )
    if pr.state == "MERGED":
        return ReleaseMergeDecision(
            "already-done", f"PR #{pr.number} is already merged — nothing to do."
        )
    if pr.state == "CLOSED":
        return ReleaseMergeDecision(
            "already-done", f"PR #{pr.number} is closed (not merged) — nothing to merge."
        )
    if pr.state != "OPEN":
        return ReleaseMergeDecision(
            "refuse", f"PR #{pr.number} is in an unexpected state {pr.state!r}."
        )
    if pr.mergeable == "CONFLICTING":
        return ReleaseMergeDecision(
            "refuse",
            f"PR #{pr.number} has merge conflicts — resolve them before merging.",
        )
    if pr.mergeable != "MERGEABLE":
        return ReleaseMergeDecision(
            "refuse",
            f"PR #{pr.number} mergeability is {pr.mergeable or 'UNKNOWN'!r} (GitHub may "
            "still be computing it) — retry shortly.",
        )
    if not pr.checks_passing:
        return ReleaseMergeDecision(
            "refuse",
            f"PR #{pr.number} required checks are not all green: "
            f"{', '.join(pr.failing_checks)}. Not merging a red or in-progress release PR.",
        )
    return ReleaseMergeDecision(
        "merge", f"PR #{pr.number} is a mergeable release PR with green checks."
    )


def merge_release_pr(repo_root: Path, pr_number: int, *, dry_run: bool = False) -> str:
    """Merge a release PR through the sanctioned path — returns a status line.

    Fetches the PR (repo derived from the ambient `gh` context — no hardcoded
    owner/repo), evaluates the gate, and squash-merges + deletes the branch when
    it passes. Does **not** tag: the flow's post-merge tag step cuts the backbone
    tag on the resulting push to `main` (VERSION-driven). Raises
    `click.ClickException` on a refusal; reports cleanly for an already
    merged/closed PR.
    """
    pr = parse_release_pr(_gh_pr_view(pr_number, repo_root))
    decision = evaluate_release_pr(pr)
    if decision.action == "refuse":
        raise click.ClickException(decision.message)
    if decision.action == "already-done":
        return decision.message

    if dry_run:
        return (
            f"[dry-run] would squash-merge PR #{pr.number} ({pr.title!r}) and delete "
            f"branch {pr.head_ref!r}; nothing merged."
        )
    _gh_pr_merge(pr.number, pr.title, repo_root)
    return (
        f"Merged release PR #{pr.number} ({pr.url}); deleted branch {pr.head_ref!r}.\n"
        "  Not tagged here: the post-merge tag step cuts the backbone tag on the push "
        "to main (VERSION-driven)."
    )


def _gh_pr_view(pr_number: int, repo_root: Path) -> dict:
    """`gh pr view <n> --json …` from `repo_root`, parsed to a dict."""
    fields = "number,title,state,headRefName,mergeable,url,statusCheckRollup"
    try:
        result = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--json", fields],
            capture_output=True,
            text=True,
            cwd=repo_root,
            check=False,
        )
    except FileNotFoundError as exc:
        raise click.ClickException(
            "`gh` is not on PATH — install the GitHub CLI to merge a release PR."
        ) from exc
    if result.returncode != 0:
        raise click.ClickException(
            f"`gh pr view {pr_number}` failed: {result.stderr.strip()}"
        )
    return json.loads(result.stdout)


def _gh_pr_merge(pr_number: int, subject: str, repo_root: Path) -> None:
    """Squash-merge PR `pr_number` and delete its branch, from `repo_root`.

    Forces the squash-commit subject to the PR title (`--subject`) so a
    single-commit release PR still lands under the `chore(release):` title
    rather than the commit message — the same discipline the issue-PR merge
    applies.
    """
    try:
        result = subprocess.run(
            ["gh", "pr", "merge", str(pr_number), "--squash", "--delete-branch",
             "--subject", subject],
            capture_output=True,
            text=True,
            cwd=repo_root,
            check=False,
        )
    except FileNotFoundError as exc:
        raise click.ClickException(
            "`gh` is not on PATH — install the GitHub CLI to merge a release PR."
        ) from exc
    if result.returncode != 0:
        raise click.ClickException(
            f"`gh pr merge {pr_number}` failed: {result.stderr.strip()}"
        )


# --- The shareability check (#494) ---------------------------------------
#
# A pre-sharing lint: is a capability ready to be consumed externally-sourced
# (COR-041)? A consumer pulls the capability whole at a pin, reads its
# manifest, and gates compatibility on the declared `requires_backbone` range
# against the consumer's backbone (ADR-040 point 4) — so the capability MUST
# declare a version, a well-formed manifest, and a parseable requires_backbone
# range before it is safe to share. This checks that objective, mechanically
# verifiable subset and reports pass / the specific gaps. It is project-neutral:
# it checks any component by name, with no project-kit-specific assumptions.

# requires_backbone must be a bounded range `>=LOW,<HIGH` — an unbounded or
# open form (`*`, `>=X` with no upper bound) cannot gate a consumer's backbone,
# so it is flagged. Mirrors the bound shape versioning.py's broaden rewrites.
_REQUIRES_BACKBONE_RANGE_RE = re.compile(r'^>=\d+\.\d+\.\d+,<\d+\.\d+\.\d+$')

# Cheaply-detectable local-only assumptions: an absolute filesystem path or a
# `file://` URL in the manifest points at something a consumer will not have.
# A heuristic reminder, not a proof — matched against the raw manifest text.
_LOCAL_PATH_RE = re.compile(r'(?m)(?:^|\s|["\':=])(/(?:Users|home|tmp|var|opt|private)/\S+|file://\S+)')


@dataclass(frozen=True)
class ShareabilityReport:
    """Outcome of the pre-sharing shareability check for one component."""

    component: str
    gaps: list[str]  # each an actionable "what is missing / malformed"
    warnings: list[str]  # non-blocking heuristics (e.g. local-path smells)

    @property
    def ok(self) -> bool:
        return not self.gaps


def check_shareable(source_kit: Path, component_name: str) -> ShareabilityReport:
    """Check that a capability is ready to be consumed externally-sourced.

    Per COR-041 a consumer pulls the capability whole, reads its manifest, and
    gates on the declared `requires_backbone` range against its own backbone
    (ADR-040). This verifies the objective preconditions for that to work:

    - the named component **exists** and carries a `package.yaml` manifest;
    - the manifest is a **well-formed** mapping with a `component` block;
    - it declares a non-empty **`version`**;
    - it declares a **bounded `requires_backbone` range** (`>=LOW,<HIGH`) the
      consumer's gate can evaluate.

    Cheaply-detectable **local-only assumptions** (absolute paths, `file://`
    URLs in the manifest) are surfaced as non-blocking *warnings* — a heuristic
    reminder, not a proof. The backbone tier is not a shareable component and is
    refused. Returns a `ShareabilityReport`; raises `click.ClickException` only
    when the named component is unknown (a usage error, not a gap).
    """
    if component_name == BACKBONE:
        raise click.ClickException(
            f"{BACKBONE!r} is the backbone tier, not a shareable component. "
            "Pass an adapter or capability name."
        )

    components = {c.name: c for c in discover_components(source_kit)}
    component = components.get(component_name)
    if component is None:
        known = [n for n in sorted(components) if n != BACKBONE]
        raise click.ClickException(
            f"unknown component {component_name!r}. "
            f"Known: {', '.join(known) if known else '(none)'}."
        )

    gaps: list[str] = []
    warnings: list[str] = []

    manifest = component.version_path
    text = manifest.read_text(encoding="utf-8")
    data = _load_yaml_mapping(text)
    if data is None:
        gaps.append(f"manifest {manifest.name} is not a well-formed YAML mapping.")
        return ShareabilityReport(component_name, gaps, warnings)

    comp_block = data.get("component")
    if not isinstance(comp_block, dict):
        gaps.append(f"manifest {manifest.name} has no `component:` mapping.")
        comp_block = {}

    version = comp_block.get("version")
    if not version or not str(version).strip():
        gaps.append("no `component.version` declared — a consumer pins by version.")

    requires_backbone = data.get("requires_backbone")
    if not requires_backbone or not str(requires_backbone).strip():
        gaps.append(
            "no `requires_backbone` declared — a consumer cannot gate compatibility "
            "against its backbone (COR-041)."
        )
    elif not _REQUIRES_BACKBONE_RANGE_RE.match(str(requires_backbone).strip()):
        gaps.append(
            f"`requires_backbone: {str(requires_backbone).strip()!r}` is not a bounded "
            "range `>=LOW,<HIGH` — the consumer's compatibility gate cannot evaluate it."
        )

    for match in _LOCAL_PATH_RE.finditer(text):
        warnings.append(
            f"manifest references what looks like a local-only path ({match.group(1)!r}) — "
            "a consumer will not have it."
        )

    return ShareabilityReport(component_name, gaps, warnings)


def _load_yaml_mapping(text: str) -> dict | None:
    """Parse `text` as YAML; return the mapping, or None if it is not one."""
    from ruamel.yaml import YAML
    from ruamel.yaml.error import YAMLError

    try:
        data = YAML(typ="safe").load(text)
    except YAMLError:
        return None
    return data if isinstance(data, dict) else None


# --- The notes-only GitHub Release (#485) --------------------------------
#
# The verb is neutral: publish a tag's CHANGELOG.md section as a Release
# body, carrying NO artifact — no file, tarball, or wheel, and no
# `--generate-notes`. "Publish notes, attach nothing" is definitional to
# publishing *notes*, not a project-specific gesture; the repo is derived
# from the ambient `gh` context (no hardcoded owner/repo), like the #475
# release-merge wrappers.
#
# The no-artifact *posture* is project-kit's own distribution choice
# (PRJ-004: install stays the git tag, an artifact channel is rejected) and
# carries no force in an adopter's repo — an adopter is free to attach
# artifacts. For project-kit the Release stays a notes overlay on the tag,
# which PRJ-004 explicitly foresaw ("release notes can land later as a
# GitHub Releases overlay without changing the install path").


def extract_changelog_section(text: str, version: str) -> str:
    """Extract one version's section from `CHANGELOG.md` text.

    Returns the lines from that version's `## <version> …` / `## [<version>] …`
    release heading up to (not including) the next release-section (`## `)
    heading — which naturally includes the section's trailing `[#N]:`
    reference-link block, so the notes' links resolve standalone. Reuses
    `_CHANGELOG_VERSION_HEADING_RE` to recognise a well-formed version heading.
    Raises `click.ClickException` when no section matches `version`.
    """
    lines = text.splitlines()
    start = next(
        (i for i, raw in enumerate(lines) if _heading_version(raw.rstrip()) == version),
        None,
    )
    if start is None:
        raise click.ClickException(
            f"{CHANGELOG_NAME} has no section for version {version!r} — expected a "
            f"`## {version}` (or `## [{version}]`) heading. Run `pkit release apply` "
            "first, or check the version."
        )
    end = next(
        (j for j in range(start + 1, len(lines)) if lines[j].rstrip().startswith("## ")),
        len(lines),
    )
    return "\n".join(lines[start:end]).rstrip() + "\n"


def _heading_version(line: str) -> str | None:
    """The version token of a well-formed `## <version> …` heading, else None.

    A date-only section (`## <date>`) has no version and yields None — it never
    matches a requested version. Brackets are stripped so the canonical KaC
    `## [<version>]` idiom matches the same version as the generator's plain form.
    """
    if not _CHANGELOG_VERSION_HEADING_RE.match(line):
        return None
    return line[3:].lstrip().split()[0].strip("[]")


def publish_release_notes(repo_root: Path, version: str, *, dry_run: bool = False) -> str:
    """Publish (or update) a notes-only GitHub Release for tag `v<version>`.

    Extracts the version's `CHANGELOG.md` section as the Release body and
    creates the Release for tag `v<version>` — or updates its notes when the
    Release already exists (idempotent: re-running edits rather than errors).
    The Release carries **no artifact** (no file / tarball / wheel and no
    `--generate-notes`): it is a notes overlay on the git-tag install path
    (PRJ-004), never an artifact channel. Repo is derived from the ambient
    `gh` context (no hardcoded owner/repo). `--dry-run` returns the notes it
    would publish without calling `gh`. Raises `click.ClickException` when the
    version has no changelog section or (via `--verify-tag`) the tag is missing.
    """
    changelog = repo_root / CHANGELOG_NAME
    if not changelog.is_file():
        raise click.ClickException(
            f"no {CHANGELOG_NAME} at {changelog} — run `pkit release apply` first."
        )
    notes = extract_changelog_section(changelog.read_text(encoding="utf-8"), version)
    tag = f"v{version}"

    if dry_run:
        return (
            f"[dry-run] would publish notes-only GitHub Release {tag} "
            f"(no artifact) with these notes:\n\n{notes}"
        )

    if _gh_release_exists(tag, repo_root):
        _gh_release_edit_notes(tag, notes, repo_root)
        return f"Updated notes-only GitHub Release {tag} (notes only — no artifact)."
    _gh_release_create_notes(tag, notes, repo_root)
    return f"Published notes-only GitHub Release {tag} (notes only — no artifact)."


def _gh_release_exists(tag: str, repo_root: Path) -> bool:
    """True when a GitHub Release for `tag` already exists (drives idempotency).

    A non-zero `gh release view` is read as "no such Release" so the caller
    falls to the create path; a genuinely broken `gh` (missing binary) is a
    clear error rather than a silent "does not exist".
    """
    try:
        result = subprocess.run(
            ["gh", "release", "view", tag],
            capture_output=True,
            text=True,
            cwd=repo_root,
            check=False,
        )
    except FileNotFoundError as exc:
        raise click.ClickException(
            "`gh` is not on PATH — install the GitHub CLI to publish release notes."
        ) from exc
    return result.returncode == 0


def _gh_release_create_notes(tag: str, notes: str, repo_root: Path) -> None:
    """Create a notes-only Release for `tag` — notes body, NO artifact.

    `--verify-tag` makes `gh` refuse when the git tag does not exist (the clear
    missing-tag error). Deliberately no positional file argument and no
    `--generate-notes`: the Release is a pure notes overlay on the tag install
    path (PRJ-004), never an artifact channel. Title is the tag.
    """
    try:
        result = subprocess.run(
            ["gh", "release", "create", tag, "--title", tag, "--notes", notes,
             "--verify-tag"],
            capture_output=True,
            text=True,
            cwd=repo_root,
            check=False,
        )
    except FileNotFoundError as exc:
        raise click.ClickException(
            "`gh` is not on PATH — install the GitHub CLI to publish release notes."
        ) from exc
    if result.returncode != 0:
        raise click.ClickException(
            f"`gh release create {tag}` failed: {result.stderr.strip()}"
        )


def _gh_release_edit_notes(tag: str, notes: str, repo_root: Path) -> None:
    """Update an existing Release's notes for `tag` — notes only, NO artifact.

    Edits only the notes body (the idempotent re-run path); title and the
    no-artifact posture are unchanged.
    """
    try:
        result = subprocess.run(
            ["gh", "release", "edit", tag, "--notes", notes],
            capture_output=True,
            text=True,
            cwd=repo_root,
            check=False,
        )
    except FileNotFoundError as exc:
        raise click.ClickException(
            "`gh` is not on PATH — install the GitHub CLI to publish release notes."
        ) from exc
    if result.returncode != 0:
        raise click.ClickException(
            f"`gh release edit {tag}` failed: {result.stderr.strip()}"
        )
