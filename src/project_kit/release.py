"""The release step — the sole main-only writer of version state (PRJ-002 D3).

A *release* consumes the pending changesets under `.changes/unreleased/`,
computes each tier's new version from the current state on `main`, writes
the version numbers, broadens kit-shipped components' `requires_backbone`
(the broaden moves here per PRJ-002 D4), raises the `requires_backbone` floor
of each component a changeset declares needs a backbone — the one the release
ships, or an already-shipped one the changeset names (also PRJ-002 D4) —
generates the changelog, which states each raised floor, deletes the consumed
changesets, and (for a backbone bump) cuts the tag via the existing
`tag_version` (PRJ-004). The files it writes are one list, `release_writes`,
which the changeset guard recognises a release diff by.

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
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import click

from project_kit import pull_request_landing, session_guard, versioning
from project_kit.changesets import (
    BACKBONE,
    FLOOR_FIELD,
    FLOOR_RELEASE,
    Changeset,
    Component,
    discover_components,
    load_changesets,
    parse_changeset_text,
    segment_rank,
    unreleased_dir,
)
from project_kit.migrations import _VERSION_DIR_RE, parse_version_tuple

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

# The two shapes a changeset's `pr` takes (`.pkit/release/README.md`): the pull
# request's number, which links the entry to that pull request of the repository
# `origin` names, and a full URL, which links it as written. `release lint`
# refuses any other.
_PR_BARE_NUMBER_RE = re.compile(r"[1-9]\d*")
_PR_URL_RE = re.compile(r"https?://\S+")
# The trailing number of a `pr` URL (`.../pull/465`, `.../pull/465/files`),
# which labels the entry `[#465]`.
_PR_NUMBER_RE = re.compile(r"(\d+)\D*$")

# A GitHub `origin` in each form git records one — `https://github.com/o/r.git`,
# `git@github.com:o/r.git`, `ssh://git@github.com/o/r` — read for the owner and
# name that locate the repository's pull requests and nothing else: credentials
# the URL carries are matched past, never written into a link.
_GITHUB_REMOTE_RE = re.compile(
    r"^(?:[a-z][a-z0-9+.-]*://)?(?:[^@/]+@)?(?i:github\.com)(?::\d+)?[:/]"
    r"(?P<owner>[\w.-]+)/(?P<name>[\w.-]+?)(?:\.git)?/?$"
)
_GITHUB_URL = "https://github.com"

# What ends a changelog note as a sentence, and a Markdown list item (`- x`,
# `* x`, `+ x`, `1. x`, `1) x`) — the shapes `_with_sentence` punctuates around.
_SENTENCE_ENDS = (".", "!", "?")
_LIST_ITEM_RE = re.compile(r"^[ \t]*(?:[-*+]|\d+[.)])[ \t]+\S")


# --- What a release writes: one list, shared by the release step and the guard
#
# `pkit release apply` writes the files `release_writes` names and nothing else,
# and the changeset guard recognises a release diff as those files and nothing
# else (`is_release_diff`). The list is made of what the writers write through:
# the version files `discover_components` finds, the self-host manifest, the
# changelog and the changesets directory, and the pattern of each line rewritten
# in place — the version and manifest lines below, and versioning.py's
# `requires_backbone` lines, each the pattern its writer rewrites the line
# through — which the guard admits a changed line by. A write the release step
# gains joins the list in the same change, or the guard reads every release
# making it as an ordinary surface change (#1161).

# A component's `version:` line in its package.yaml, which the release rewrites.
# Anchored to a leading indent so top-level `schema_version:` is never matched;
# regex (not a YAML round-trip) to preserve quoting, key order, and trailing
# comments — same discipline as versioning.py's requires_backbone rewrite.
_PACKAGE_VERSION_LINE_RE = re.compile(r"(?m)^(\s+version:\s*)(\d+\.\d+\.\d+)")
# The self-host manifest's `backbone_version:` line, which a backbone release
# rewrites (PRJ-007), under the source kit.
_MANIFEST_BACKBONE_LINE_RE = re.compile(r"(?m)^(backbone_version:[ \t]*)(\S+)")
SELF_HOST_MANIFEST_NAME = "manifest.yaml"


@dataclass(frozen=True)
class ReleaseWrite:
    """One file `pkit release apply` writes, as the release's diff shows it."""

    path: str  # repo-root-relative, git's path form; ending in `/`, every file under it
    statuses: str  # the `git diff --name-status` letters the write leaves
    # The patterns of the only lines the write changes; empty when the release
    # writes the whole file. A changed line matching none is an edit riding
    # along, so the diff is not the release.
    lines: tuple[re.Pattern[str], ...] = ()
    # False for a write every release makes that is no release on its own: a
    # diff that only deletes changesets.
    marks_release: bool = True

    def covers(self, status: str, path: str) -> bool:
        """Whether a diff entry — its status letter and path — is this write."""
        named = path.startswith(self.path) if self.path.endswith("/") else path == self.path
        return named and status in self.statuses


def release_writes(source_kit: Path) -> tuple[ReleaseWrite, ...]:
    """The files `pkit release apply` writes in `source_kit`'s repo, and how:

    - each component's version file — the backbone's `VERSION` whole, a
      `package.yaml` only in its `version:` line and a `requires_backbone:` line
      of the shapes the broaden and a declared floor rewrite;
    - the self-host manifest's `backbone_version:` line, on a backbone release
      (`_sync_self_host_manifest_backbone`, PRJ-007);
    - `CHANGELOG.md`, created or prepended;
    - the consumed changesets, deleted — in every release, but a diff deleting
      only changesets is none.
    """
    repo_root = source_kit.parent
    package_lines = (_PACKAGE_VERSION_LINE_RE, *versioning.REQUIRES_BACKBONE_RELEASE_LINES)
    versions = [
        ReleaseWrite(
            _repo_rel(repo_root, component.version_path),
            "M",
            () if component.name == BACKBONE else package_lines,
        )
        for component in discover_components(source_kit)
    ]
    return (
        *versions,
        ReleaseWrite(
            _repo_rel(repo_root, source_kit / SELF_HOST_MANIFEST_NAME),
            "M",
            (_MANIFEST_BACKBONE_LINE_RE,),
        ),
        ReleaseWrite(CHANGELOG_NAME, "AM"),
        ReleaseWrite(
            _repo_rel(repo_root, unreleased_dir(repo_root)) + "/", "D", marks_release=False
        ),
    )


@dataclass(frozen=True)
class FloorRaise:
    """What a declared floor raise does to one component's `requires_backbone`."""

    old_floor: str  # the floor the package declares
    new_floor: str  # the declared floor, or the old floor when that is already higher
    declared: str  # the highest backbone the component's changesets name (`declared_floor`)
    backbone: str  # the backbone the release ships, which `release` names
    # False when the release does not move the backbone: `release` then names the
    # current one, which may predate the change the component needs.
    backbone_moves: bool
    # The changeset whose declaration sets the floor: the first naming `declared`,
    # an explicit version before `release` when both name it (`_floor_raise`).
    setter: Changeset
    release_declared: bool  # some changeset of the component says `release`

    @property
    def names_release(self) -> bool:
        """Whether the declaration that sets the floor says `release`, rather than
        naming an explicit version."""
        return self.setter.names_release

    @property
    def raises(self) -> bool:
        """Whether the raise changes the range (it is raise-only)."""
        return self.new_floor != self.old_floor

    @property
    def lines(self) -> list[str]:
        """What `release plan` prints under the component's bump, and its `--json`
        carries for the release PR's body. The notice that the backbone does not
        move follows any `release` declaration, even one an explicit version ties:
        the need behind it may still postdate the current backbone."""
        lines = [
            f"requires_backbone floor raised to >={self.new_floor}"
            if self.raises
            else f"requires_backbone floor stays >={self.old_floor} "
            f"(already at or above {self.declared})"
        ]
        if self.release_declared and not self.backbone_moves:
            resolved = "floor raised to" if self.raises else "the declared floor resolves to"
            lines.append(
                f"backbone does not move this release; {resolved} current {self.backbone} "
                f"— confirm the needed surface shipped in {self.backbone}"
            )
        return lines

    @property
    def changelog_sentence(self) -> str | None:
        """What the component's changelog entry says of the raise; None when the
        range does not change."""
        return f"Requires backbone >={self.new_floor}." if self.raises else None


@dataclass(frozen=True)
class ComponentRelease:
    """A single tier's computed bump within a release."""

    component: Component
    segment: str  # the highest non-`none` segment across the tier's changesets
    old_version: str
    new_version: str
    changesets: list[Changeset]  # the source changesets (carry notes + categories)
    floor_raise: FloorRaise | None = None  # set when a changeset declares the floor field

    @property
    def notes(self) -> list[str]:
        """The non-empty changelog notes, in changeset order."""
        return [cs.note for cs in self.changesets if cs.note]

    @property
    def raises_floor(self) -> bool:
        """Whether a changeset declares this component needs a backbone."""
        return self.floor_raise is not None

    @property
    def floor_entry(self) -> Changeset | None:
        """The changeset whose changelog entry states the raised floor: the one
        whose declaration sets it (`FloorRaise.setter`). None when the release
        leaves the floor as it is."""
        floor = self.floor_raise
        if floor is None or not floor.raises:
            return None
        return floor.setter


@dataclass(frozen=True)
class ReleasePlan:
    """The full computed release: which tiers bump, and what to consume."""

    releases: list[ComponentRelease]  # tiers that actually move (segment != none)
    consumed: list[Changeset]  # every pending changeset (incl. `none`) to delete
    # The backbone version this release ships (`shipped_backbone`). A floor
    # declared `release` is raised to it.
    shipped_backbone: str

    @property
    def backbone(self) -> ComponentRelease | None:
        return next((r for r in self.releases if r.component.name == BACKBONE), None)

    @property
    def is_empty(self) -> bool:
        return not self.releases

    @property
    def floor_raises(self) -> list[ComponentRelease]:
        """The moving components a changeset declares need a backbone."""
        return [r for r in self.releases if r.raises_floor]


def compute_release(source_kit: Path) -> ReleasePlan:
    """Compute the release from the current state + pending changesets.

    Groups changesets by component, takes the highest segment per component,
    and computes each moving tier's new version from its current version.
    `none`-only components are consumed but do not move. Raises
    `click.ClickException` if a changeset names an unknown component, or
    carries a floor field it cannot carry (`floor_problems`) — a declared floor
    is never dropped silently, and a release that would write part of one is
    refused before `apply` writes anything.
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

    shipped = shipped_backbone(components, changesets)
    released = (
        recorded_backbone_releases(source_kit.parent, components)
        if any(cs.requires_backbone is not None for cs in changesets)
        else frozenset[str]()
    )
    refused = [
        f"changeset {cs.path.name}: {problem}"
        for cs in changesets
        for problem in floor_problems(cs, components, shipped, released)
    ]
    if refused:
        raise click.ClickException(
            "cannot raise a requires_backbone floor:\n  " + "\n  ".join(refused)
        )

    backbone_top = _top_segment(grouped.get(BACKBONE, []))
    backbone_moves = backbone_top is not None and backbone_top != "none"
    releases: list[ComponentRelease] = []
    for name in sorted(grouped, key=lambda n: (n != BACKBONE, n)):
        group = grouped[name]
        top = _top_segment(group)
        if top is None or top == "none":
            continue  # declared no-bump; consumed only
        component = components[name]
        releases.append(
            ComponentRelease(
                component=component,
                segment=top,
                old_version=component.version,
                new_version=versioning.next_version(component.version, top),
                changesets=group,
                floor_raise=_floor_raise(component, group, shipped, backbone_moves),
            )
        )

    return ReleasePlan(releases=releases, consumed=changesets, shipped_backbone=shipped)


def shipped_backbone(components: Mapping[str, Component], changesets: Sequence[Changeset]) -> str:
    """The backbone version a release of `changesets` ships: the new one when a
    changeset moves the backbone, else the current `.pkit/VERSION` (empty when the
    tree has none). A floor declared `release` is raised to it. One reader for the
    release, which raises to it, and the lint, which checks it can be raised to."""
    current = components.get(BACKBONE)
    if current is None:
        return ""
    top = _top_segment([cs for cs in changesets if cs.component == BACKBONE])
    if top is None or top == "none":
        return current.version
    return versioning.next_version(current.version, top)


def _top_segment(group: Sequence[Changeset]) -> str | None:
    """The highest segment among a tier's changesets; None when there are none."""
    if not group:
        return None
    return max(group, key=lambda cs: segment_rank(cs.segment)).segment


def declared_floor(cs: Changeset, shipped: str) -> str | None:
    """The backbone `cs`'s floor field names: `shipped`, the backbone the release
    ships, for `release`, else the version the field gives. None when the
    changeset carries no floor field."""
    if cs.requires_backbone is None:
        return None
    return shipped if cs.names_release else cs.requires_backbone


def _floor_raise(
    component: Component, group: Sequence[Changeset], shipped: str, backbone_moves: bool
) -> FloorRaise | None:
    """The floor raise a moving component's changesets declare, or None when none
    does: to the highest backbone they name. Read before anything is written;
    `floor_problems` has already refused a component without a floor to raise and
    any name that is not a release version.

    The declaration naming that backbone sets the floor, and its changelog entry
    says so. When an explicit version and `release` name the same backbone, the
    explicit one sets it — it vouches that backbone has shipped — and among equal
    declarations the first in filename order does, so the choice never depends on
    anything but the changesets."""
    declarations = [
        (cs, floor) for cs in group if (floor := declared_floor(cs, shipped)) is not None
    ]
    if not declarations:
        return None
    setter, declared = max(
        declarations, key=lambda d: (parse_version_tuple(d[1]), not d[0].names_release)
    )
    floor = versioning.requires_backbone_floor(component.version_path.read_text(encoding="utf-8"))
    if floor is None:
        raise click.ClickException(
            f"{component.name}: requires_backbone has no floor the release can raise"
        )
    raised = parse_version_tuple(floor) < parse_version_tuple(declared)
    return FloorRaise(
        old_floor=floor,
        new_floor=declared if raised else floor,
        declared=declared,
        backbone=shipped,
        backbone_moves=backbone_moves,
        setter=setter,
        release_declared=any(cs.names_release for cs, _ in declarations),
    )


def floor_problems(
    cs: Changeset, components: Mapping[str, Component], shipped: str, released: Collection[str]
) -> list[str]:
    """Why `cs`'s floor field cannot raise a floor; empty when it can, or when the
    changeset carries none.

    The field names the backbone the component needs: `release`, the backbone
    the release ships (`shipped`, from `shipped_backbone`), which must then be a
    release version; or an explicit release version the tree records as
    released (`released`, from `recorded_backbone_releases`) at or below the
    backbone the tree carries — one that has shipped, so the branch states a
    fact rather than predicting the release (PRJ-002 D4). It raises the floor of
    a capability or adapter whose `requires_backbone` is a range the release
    raises (`versioning.requires_backbone_floor`, the same locator the raise
    rewrites through), on a changeset that moves the component's version — a
    raised floor changes what the component requires, which is surface and is
    never shipped under an unchanged version. One reader for the release step,
    which refuses, and the lint, which reports.
    """
    if cs.requires_backbone is None:
        return []
    problems: list[str] = []
    if not cs.names_release:
        problems.extend(
            _explicit_floor_problems(cs.requires_backbone, components.get(BACKBONE), released)
        )
    if cs.component == BACKBONE:
        problems.append(
            f"`{FLOOR_FIELD}` is a component's field: the backbone has no "
            f"`requires_backbone` to raise."
        )
        return problems
    if cs.segment == "none":
        problems.append(
            f"a `none` changeset moves no version, and raising the floor of "
            f"{cs.component!r} changes what it requires — declare patch, minor or major."
        )
    component = components.get(cs.component)
    if component is None:
        problems.append(
            f"names unknown component {cs.component!r}, so there is no floor to raise. "
            f"Known: {', '.join(sorted(components))}."
        )
    elif (
        component.kind not in ("capability", "adapter")
        or versioning.requires_backbone_floor(component.version_path.read_text(encoding="utf-8"))
        is None
    ):
        problems.append(
            f"{cs.component!r} is not a capability or adapter whose `requires_backbone` "
            'has a floor the release can raise (a range of the form ">=X.Y.Z,<A.B.C" '
            'or ">=X.Y.Z").'
        )
    if cs.names_release and not versioning.is_release_version(shipped):
        problems.append(
            f"the release ships backbone {shipped!r} — the current `.pkit/VERSION`, since "
            "no changeset moves the backbone — which is not a release version "
            "(major.minor.patch), so no floor can be raised to it. Declare a backbone "
            "change in this release, name the already-shipped backbone the component "
            "needs, or release once `.pkit/VERSION` is a release version."
        )
    return problems


def _explicit_floor_problems(
    value: str, current: Component | None, released: Collection[str]
) -> list[str]:
    """Why an explicit floor value names no backbone the release can raise to; empty
    when it names a release the tree records (`recorded_backbone_releases`) at or
    below `current`, the backbone the tree carries — one that has shipped.

    The bound is the tree's own backbone: on a branch, the backbone `main` had
    when the branch was cut; in an adopter's repo, the installed one, which a pin
    or a downgrade can lower below a floor already declared. Either way the
    release is refused until the two agree, and the message says how."""
    if not versioning.is_release_version(value):
        return [_explicit_form_problem(value)]
    if current is None:
        return [
            f"names backbone {value}, but the tree has no current backbone "
            "(`.pkit/VERSION`) for it to be at or below."
        ]
    problem = backbone_version_problem(current)
    if problem is not None:
        return [f"names backbone {value}, but {problem}"]
    if not versioning.is_at_or_below(value, current.version):
        return [
            f"names backbone {value}, above the backbone this tree carries "
            f"({current.version}, its `.pkit/VERSION`): an explicit version names a "
            "backbone that has shipped, and the release is refused until the tree "
            f"carries {value} or later. If main has released {value} since this branch "
            "was cut, update the branch from main; if this tree's backbone is pinned or "
            "downgraded below it, upgrade the backbone or lower the floor. For the "
            f"backbone this release ships, say `{FLOOR_RELEASE}`."
        ]
    if value not in released:
        later = sorted(
            (r for r in released if parse_version_tuple(r) > parse_version_tuple(value)),
            key=parse_version_tuple,
        )
        hint = (
            f"the lowest release it records above {value} is {later[0]}"
            if later
            else "name one it records"
        )
        return [
            f"names backbone {value}, which this tree records no release of — the "
            f"releases it records are its {CHANGELOG_NAME} release headings and the "
            f"backbone it carries ({current.version}); {hint}."
        ]
    return []


def _explicit_form_problem(value: str) -> str:
    """The problem with an explicit floor value that is not a release version, with
    a hint for the two slips YAML and habit make likely: an unquoted
    `major.minor`, which YAML reads as a number, and a part padded with a zero."""
    problem = (
        f"`{FLOOR_FIELD}` takes `{FLOOR_RELEASE}` (the backbone this release ships) or "
        "an already-shipped release version, major.minor.patch with no pre-release "
        f"suffix or leading zero; got {value!r}."
    )
    if re.fullmatch(r"\d+(?:\.\d+)?", value):
        full = value + ".0" * (2 - value.count("."))
        return (
            f"{problem} A version has three parts, and YAML reads an unquoted "
            f"major.minor such as {value} as a number: write it in full and quoted, "
            f'`{FLOOR_FIELD}: "{full}"`.'
        )
    if re.fullmatch(r"\d+\.\d+\.\d+", value):
        canonical = ".".join(str(int(part)) for part in value.split("."))
        return f"{problem} Write it without the leading zero: {canonical}."
    return problem


def backbone_version_problem(current: Component) -> str | None:
    """Why the backbone the tree carries cannot bound a declared floor — its
    `.pkit/VERSION` holds no version — or None when it can."""
    if versioning.is_version(current.version):
        return None
    return (
        f"the backbone this tree carries, {current.version!r} in `.pkit/VERSION`, is not a "
        "version (major.minor.patch[(a|b|rc)N]), so no floor can be checked against it."
    )


def recorded_backbone_releases(
    repo_root: Path, components: Mapping[str, Component]
) -> frozenset[str]:
    """The backbone releases the tree records: each version its `CHANGELOG.md`
    keys a release section on (`## X.Y.Z — date`, the heading a backbone release
    writes), and the backbone it carries (`.pkit/VERSION`) when that is a release
    version. An explicit floor must name one of them (PRJ-002 D4).

    A tree whose changelog keys no section on a version — an adopter's, whose
    releases are its own components', dated — records only the backbone it
    carries."""
    recorded: set[str] = set()
    current = components.get(BACKBONE)
    if current is not None and versioning.is_release_version(current.version):
        recorded.add(current.version)
    changelog = repo_root / CHANGELOG_NAME
    if changelog.is_file():
        for line in changelog.read_text(encoding="utf-8").splitlines():
            match = _CHANGELOG_VERSION_HEADING_RE.match(line.rstrip())
            if match is not None and versioning.is_release_version(match.group(1)):
                recorded.add(match.group(1))
    return frozenset(recorded)


def apply_release(
    source_kit: Path,
    plan: ReleasePlan,
    *,
    tag: bool = False,
    push: bool = False,
    clearance: session_guard.Clearance | None = None,
    broaden: bool = True,
    today: date | None = None,
) -> None:
    """Write the release: versions, broaden, declared floors, changelog, delete.

    The order matters — versions and the requires_backbone broaden land
    first, then the declared floors are raised (after the broaden, so a raised
    floor always sits under an upper bound that admits it), then the changelog
    is prepended, then the consumed changesets are deleted. Idempotent inputs
    only: re-running with an empty plan is a no-op.

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

    The floor raise is never automatic: it raises the lower bound of each
    moving component a changeset declares needs a backbone to the highest one
    its changesets name (`FloorRaise.declared`) — `plan.shipped_backbone` for
    `requires_backbone: release`, else the already-shipped version given —
    **raise-only**, and the changelog entry of the changeset that set it says
    so. `--no-broaden` does not skip it — the need was declared. Before
    anything is written, every raised range is computed in memory as it will be
    written — broadened first when the broaden runs, then raised — and a range
    that would admit no backbone refuses the release
    (`check_raised_ranges`).

    Tagging is **off by default** and deliberately a separate step, matching
    the codebase's anchoring principle (bump writes; `pkit version tag` tags —
    per COR-004). PRJ-004 tags the *committed* `.pkit/VERSION`, so the tag must
    point at the release commit — which does not exist yet when `apply` runs.
    The intended sequence is: `apply` → commit the release → merge to `main` →
    `pkit version tag --push` on `main`. Pass `tag=True` only when HEAD is
    already the release commit (e.g. re-running on `main` post-merge). A tag
    pushed with `push=True` changes the hosting service, so it needs
    `clearance`, the cross-repository guard's for the repository, cleared at
    the entry (ADR-061 point 6): it is required before anything is written.
    """
    if tag and push:
        session_guard.require(clearance, source_kit.parent)
    if plan.is_empty:
        click.echo("No pending changesets move a version — nothing to release.")
        # Still consume any `none`-only changesets so the tree is clean.
        _delete_changesets(plan.consumed)
        return

    check_raised_ranges(plan, broaden=broaden)  # the CLI prints its warnings before confirming

    backbone = plan.backbone
    for rel in plan.releases:
        if rel.component.name == BACKBONE:
            rel.component.version_path.write_text(f"{rel.new_version}\n", encoding="utf-8")
            click.echo(f"Backbone: {rel.old_version} -> {rel.new_version}")
            _sync_self_host_manifest_backbone(source_kit, rel.new_version)
        else:
            _write_component_version(rel)

    if broaden:
        _broaden_at_release(source_kit, plan)
    _raise_declared_floors(source_kit, plan)

    _write_changelog(source_kit.parent, plan, today or date.today())
    _delete_changesets(plan.consumed)

    if tag and backbone is not None:
        versioning.tag_version(source_kit, push=push, clearance=clearance)
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
    no backbone move. Either way the target is `plan.shipped_backbone` — the new
    backbone, or the current one — which `check_raised_ranges` broadens
    to in memory first.
    """
    backbone = plan.backbone
    if backbone is not None:
        # Backbone moved — widen every component to the new backbone minor.
        major, minor = (int(p) for p in backbone.new_version.split(".")[:2])
        versioning._broaden_kit_components_requires_backbone(source_kit, major, minor)
        return

    # Component-only release — widen each released component's own bound to the
    # repo's current backbone (the version being released under / tested with).
    current_backbone = plan.shipped_backbone
    for rel in plan.releases:
        if rel.component.name == BACKBONE:
            continue  # unreachable here (backbone is None), but keep the guard explicit
        rel_path = rel.component.version_path.relative_to(source_kit)
        changed = versioning.broaden_component_requires_backbone(
            rel.component.version_path, current_backbone
        )
        if changed is not None:
            click.echo(f"  broadened {rel_path}: {changed} (covers backbone {current_backbone})")


def _raise_declared_floors(source_kit: Path, plan: ReleasePlan) -> None:
    """Raise the `requires_backbone` floor of each component a changeset declares
    needs a backbone to the one declared (PRJ-002 D4). Raise-only; a floor
    already at or above it is reported and left."""
    for rel in plan.releases:
        floor = rel.floor_raise
        if floor is None:
            continue
        rel_path = rel.component.version_path.relative_to(source_kit)
        changed = versioning.raise_component_requires_backbone_floor(
            rel.component.version_path, floor.declared
        )
        if changed is None:
            click.echo(
                f"  floor of {rel_path} already admits no backbone older than {floor.declared}"
            )
        else:
            click.echo(f"  raised floor {rel_path}: {changed} (declared by a changeset)")


def check_raised_ranges(plan: ReleasePlan, *, broaden: bool) -> list[str]:
    """Refuse, before anything is written, a floor raise that would leave a range
    admitting no backbone; return a warning for each raised range that admits its
    floor but not the backbone the release ships.

    Each raised range is computed in memory as `apply` writes it, through the
    same rewrites: broadened first when the broaden runs — to the shipped
    backbone, the target of both its shapes — then raised to the declared
    floor. The raised range must admit that floor, the lowest backbone it now
    names: a range admitting its own floor admits a backbone, and one that does
    not admits none. So the guarantee holds on every raise, with the broaden or
    without, and whatever else the package file holds. A floor already at or
    above the declared one is not raised, so its range is not the release's to
    refuse.

    One that admits its floor but not the shipped backbone is written as it is
    — an upper bound `--no-broaden` keeps as authored may exclude the newest
    backbone on purpose — but the component then ships beside a backbone its
    range refuses, which the warning says. With the broaden that cannot happen.
    """
    from project_kit.connections import range_admits

    shipped = plan.shipped_backbone
    warnings: list[str] = []
    for rel in plan.releases:
        floor = rel.floor_raise
        if floor is None:
            continue
        text = rel.component.version_path.read_text(encoding="utf-8")
        if broaden:
            broadened = versioning.broaden_requires_backbone(text, shipped)
            text = broadened[0] if broadened is not None else text
        try:
            raised = versioning.raise_requires_backbone_floor(text, floor.declared)
        except click.ClickException as exc:
            raise click.ClickException(f"{rel.component.name}: {exc.message}") from None
        if raised is None:
            continue
        written = versioning.requires_backbone_range(raised[0])
        if range_admits(written, floor.declared) is not True:
            remedy = (
                "widen the range's upper bound"
                if broaden
                else "drop --no-broaden, or widen the range's upper bound"
            )
            raise click.ClickException(
                f"{rel.component.name}: a changeset raises its requires_backbone floor to "
                f"{floor.declared}, but the range the release would write, {written!r}, "
                f"does not admit {floor.declared} — it would admit no backbone. Nothing was "
                f"written; {remedy}."
            )
        if range_admits(written, shipped) is not True:
            warnings.append(
                f"{rel.component.name}: the range the release writes, {written!r}, admits "
                f"the declared floor {floor.declared} but not the backbone this release "
                f"ships, {shipped}; the upper bound stays as authored"
                + (" (--no-broaden)." if not broaden else ".")
            )
    return warnings


def _write_component_version(rel: ComponentRelease) -> None:
    path = rel.component.version_path
    original = path.read_text(encoding="utf-8")
    updated, count = _PACKAGE_VERSION_LINE_RE.subn(rf"\g<1>{rel.new_version}", original, count=1)
    if count == 0:
        raise click.ClickException(
            f"could not find a `version:` line to rewrite in {path} "
            f"(component {rel.component.name!r})"
        )
    path.write_text(updated, encoding="utf-8")
    click.echo(f"{rel.component.name}: {rel.old_version} -> {rel.new_version}")


def _sync_self_host_manifest_backbone(source_kit: Path, new_version: str) -> None:
    """Keep the source repo's own `.pkit/manifest.yaml` backbone_version current.

    project-kit self-hosts: its `.pkit/` is both the methodology *source* and a
    notional *install*, but the source repo never runs install/sync/upgrade on
    itself — so its manifest's `backbone_version` froze at genesis while
    `.pkit/VERSION` advanced, leaving `pkit status` permanently misreporting the
    self-host backbone. On a backbone bump the release is the exact moment the
    source repo's backbone moves, so it records the new value here too (PRJ-007).

    Keyed to the backbone-bump branch: a capability-only release never reaches
    this, so `backbone_version` is untouched when the backbone did not move. Only
    the `backbone_version:` line is rewritten, in place, through the pattern the
    changeset guard admits it by (`release_writes`): the components registry,
    schema version, and comments keep every byte, so the release's manifest diff
    is that one line. A no-op when no manifest exists (an adopter repo running
    `apply` has no self-host manifest to maintain — this is source-repo-only
    mechanics).
    """
    path = source_kit / SELF_HOST_MANIFEST_NAME
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    match = _MANIFEST_BACKBONE_LINE_RE.search(text)
    if match is None:
        raise click.ClickException(
            f"could not find a `backbone_version:` line to rewrite in {path}"
        )
    if match.group(2) == new_version:
        return
    updated = f"{text[: match.start(2)]}{new_version}{text[match.end(2) :]}"
    path.write_text(updated, encoding="utf-8")
    click.echo(f"Self-host manifest backbone_version -> {new_version}")


def render_changelog_entry(
    plan: ReleasePlan, when: date, *, repository_url: str | None = None
) -> str:
    """Render the Keep-a-Changelog block for this release.

    The section is keyed by the backbone's new version + date when the
    backbone moved, else by date alone (a component-only release has no
    backbone tag to key on). Entries are grouped under Keep-a-Changelog
    category headings; a component that is *not* the backbone is tagged inline
    with its name + new version so a date-keyed section still surfaces which
    component moved. A raised `requires_backbone` floor is stated once per
    component, at the end of the entry of the changeset that set it
    (`ComponentRelease.floor_entry`), so an adopter reads what the component now
    needs. `pr` references become reference-style `([#N])` links, resolved in a
    block at the foot of the section (omitted when absent): a URL links as
    written, and a pull request's number links to that pull request of
    `repository_url` (`https://github.com/<owner>/<name>`, which
    `origin_repository_url` reads). Without a repository a number still labels
    its entry but no reference is written for it, so the label links nowhere
    rather than to a broken target.
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
        floor_entry = rel.floor_entry
        floor_sentence = rel.floor_raise.changelog_sentence if rel.floor_raise else None
        for cs in rel.changesets:
            text = cs.note
            if cs is floor_entry and floor_sentence:
                text = _with_sentence(text, floor_sentence)
            if not text:
                continue
            if not is_backbone:
                text = f"**{rel.component.name} {rel.new_version}** — {text}"
            link = _pr_link(cs.pr, repository_url) if cs.pr else None
            if link is not None:
                label, target = link
                text = f"{text} ([#{label}])"
                if target is not None:
                    refs.setdefault(label, target)
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


def _with_sentence(note: str, sentence: str) -> str:
    """`note` followed by `sentence`, punctuated as prose: a period closes a note
    that lacks one first, and a note ending in a list item gets the sentence as
    its own paragraph, so it does not read as part of the item."""
    if not note:
        return sentence
    if _LIST_ITEM_RE.match(note.splitlines()[-1]):
        return f"{note}\n\n{sentence}"
    if not note.endswith(_SENTENCE_ENDS):
        note += "."
    return f"{note} {sentence}"


def _pr_link(pr: str, repository_url: str | None) -> tuple[str, str | None] | None:
    """The `#N` label and the link target of a `pr` value; None when it has no
    number to label with. A pull request's number links to that pull request of
    `repository_url`, and to nothing without one; a URL links as written. A
    value of any other shape — which `release lint` refuses — is labelled by its
    trailing number and linked to nothing, so it cannot break a link either."""
    if _PR_BARE_NUMBER_RE.fullmatch(pr):
        return pr, (f"{repository_url}/pull/{pr}" if repository_url else None)
    match = _PR_NUMBER_RE.search(pr)
    if match is None:
        return None
    return match.group(1), (pr if _PR_URL_RE.fullmatch(pr) else None)


def is_pr_reference(pr: str) -> bool:
    """Whether a `pr` value has one of the two shapes the field takes: the pull
    request's number, or a full URL ending in it."""
    if _PR_BARE_NUMBER_RE.fullmatch(pr):
        return True
    return _PR_URL_RE.fullmatch(pr) is not None and _PR_NUMBER_RE.search(pr) is not None


def github_repository_url(remote: str) -> str | None:
    """The web address — `https://github.com/<owner>/<name>` — of the GitHub
    repository a git remote URL names, in any form git records one; None for a
    remote on any other host, or none. Built from the owner and name alone, so
    no credentials in the remote reach it."""
    match = _GITHUB_REMOTE_RE.match(remote.strip())
    if match is None:
        return None
    return f"{_GITHUB_URL}/{match['owner']}/{match['name']}"


def origin_repository_url(repo_root: Path) -> str | None:
    """The web address of the GitHub repository the `origin` remote of the
    repository at `repo_root` names (`github_repository_url`) — where a
    bare-number `pr` links; None when there is no `origin`, git cannot answer,
    or `origin` is not on GitHub."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            cwd=repo_root,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return github_repository_url(result.stdout)


def _write_changelog(repo_root: Path, plan: ReleasePlan, when: date) -> None:
    changelog = repo_root / CHANGELOG_NAME
    repository_url = origin_repository_url(repo_root)
    if repository_url is None:
        unlinked = sum(
            1
            for rel in plan.releases
            for cs in rel.changesets
            if cs.pr and _PR_BARE_NUMBER_RE.fullmatch(cs.pr)
        )
        if unlinked:
            _warn(
                f"`origin` names no GitHub repository, so {unlinked} pull-request "
                "number(s) label their changelog entries without a link; a full URL "
                "in a changeset's `pr` links wherever the repository lives."
            )
    entry = render_changelog_entry(plan, when, repository_url=repository_url)
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
    (`backbone_version`), render the PR body (`releases`, each with the floor
    raise a changeset declared for it, or null), and surface the migration-dir
    prediction warnings (`migration_warnings`).
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
                "requires_backbone_floor": _floor_summary(rel.floor_raise),
            }
            for rel in plan.releases
        ],
        "changesets_consumed": len(plan.consumed),
        "migration_warnings": migration_dir_mismatches(source_kit, plan),
    }


def _floor_summary(floor: FloorRaise | None) -> dict[str, object] | None:
    """One release's declared floor raise for `release_summary`: the floors before
    and after, whether the range changes, the backbone the changesets name and
    whether the declaration that set it says `release` (false: an explicit
    version), the backbone the release ships and whether it moves, the lines
    `release plan` prints for it, and the sentence the changelog entry carries
    (null when the range does not change)."""
    if floor is None:
        return None
    return {
        "from": floor.old_floor,
        "to": floor.new_floor,
        "raised": floor.raises,
        "declared": floor.declared,
        "names_release": floor.names_release,
        "backbone": floor.backbone,
        "backbone_moves": floor.backbone_moves,
        "lines": floor.lines,
        "changelog": floor.changelog_sentence,
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
    # Touched components no changeset of the diff's own names (the violations);
    # a pending changeset the diff leaves alone does not count (`diff_changesets`).
    missing: list[str]
    skipped: bool  # the escape hatch (label / --skip) was active
    release_exempt: bool = False  # the diff is only what a release writes (below)
    # Changesets whose `requires_backbone` floor this diff declares for a component
    # it neither touches nor moves (`stray_floors`).
    stray_floors: list[Changeset] = field(default_factory=lambda: [])

    @property
    def surface_ok(self) -> bool:
        """The surface check passes, or the escape hatch or the release exemption
        waives it."""
        return self.skipped or self.release_exempt or not self.missing

    @property
    def ok(self) -> bool:
        """The escape hatch and the release exemption waive the surface check
        only: a stray floor fails the guard either way. A release diff, which
        only deletes changesets, declares no floor to be stray."""
        return self.surface_ok and not self.stray_floors


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


# --- Release-PR exemption: recognise a release by what it writes ------------
#
# A release PR (opened by release-pr.yml) is `pkit release apply`'s own output:
# the version files, `requires_backbone` lines and self-host backbone_version it
# rewrites, the changelog it prepends, and the consumed `.changes/unreleased/*`
# changesets it *deletes*. That diff trips the surface guard (VERSION and
# package.yaml are surface) while the changesets it would need are exactly the
# files it just consumed — so it would fail with no `skip-changeset` label. It is
# not a *new* surface change; it is the release of already-declared ones. We
# exempt it by *content* — the change set is only what the release writes
# (`release_writes`, the list made of what the release step writes through) —
# rather than by branch name or an env signal: a content signal is
# self-contained (works locally + in CI, on any branch, in any adopter's repo),
# and naming a branch `release/*` does not produce it. The signal is
# intentionally strict: if *any* changed file or line falls outside the list
# (e.g. a stray `src/` edit), the diff is NOT the release itself and the guard
# runs normally — so the exemption can never smuggle real surface through. It
# waives the surface check only, never the floor tie (`GuardResult.ok`).


def _diff_name_status(repo_root: Path, base: str) -> list[tuple[str, str]]:
    """(`status`, path) for each change between `base` and HEAD.

    Status is git's `--name-status` letter (`A`/`M`/`D`/…). Mirrors
    `changed_files`' merge-base scoping (`base...HEAD`). A rename (`Rxxx`) yields
    its destination path — a release renames nothing (`release_writes`), so a
    rename is simply not the release and falls through to the normal guard.
    """
    result = subprocess.run(
        ["git", "diff", "--name-status", f"{base}...HEAD"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )
    entries: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        path = parts[-1]  # last field is the (destination) path
        entries.append((status[0], path))
    return entries


def _file_diff_lines(repo_root: Path, base: str, path: str) -> list[str]:
    """The content (`+`/`-`) lines of one file's diff, hunk headers stripped."""
    result = subprocess.run(
        ["git", "diff", f"{base}...HEAD", "--", path],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )
    lines: list[str] = []
    for raw in result.stdout.splitlines():
        if raw.startswith(("+++", "---")):
            continue  # file headers, not content
        if raw.startswith(("+", "-")):
            lines.append(raw[1:])
    return lines


def _changes_only(
    repo_root: Path, base: str, path: str, patterns: tuple[re.Pattern[str], ...]
) -> bool:
    """True when every line one file's diff adds or removes matches one of
    `patterns`. A blank changed line is tolerated (a whitespace-only hunk edge)."""
    return all(
        not line.strip() or any(pattern.match(line) for pattern in patterns)
        for line in _file_diff_lines(repo_root, base, path)
    )


def is_release_diff(source_kit: Path, base: str) -> bool:
    """True when the diff vs `base` is only what `pkit release apply` writes.

    Every changed file must be one the release writes (`release_writes`), with a
    status that write leaves, and — for a file the release rewrites in place —
    only the lines it rewrites (verified line-by-line); and the diff must write
    more than the consumed changesets it deletes.

    Any other change (a `src/` edit, a doc, a new file under a component subtree,
    a package.yaml line beside its version and floor) makes the answer False —
    the diff is then treated as an ordinary PR and the surface guard runs. An
    empty diff is not a release.
    """
    repo_root = source_kit.parent
    writes = release_writes(source_kit)
    marked = False  # a write that shows a release, not only consumed changesets
    for status, path in _diff_name_status(repo_root, base):
        write = next((w for w in writes if w.covers(status, path)), None)
        if write is None:
            return False  # anything else ⇒ not the release itself
        if write.lines and not _changes_only(repo_root, base, path, write.lines):
            return False  # an edit rode along in a file the release rewrites
        marked = marked or write.marks_release
    return marked


def _repo_rel(repo_root: Path, path: Path) -> str:
    """`path` as a POSIX repo-root-relative string (matches git's path form)."""
    return path.relative_to(repo_root).as_posix()


def check_changesets(source_kit: Path, base: str, *, skip: bool = False) -> GuardResult:
    """Run the changeset guard against the diff vs `base`: the surface check and
    the floor tie.

    The surface check passes when every surface-touched component is named by a
    changeset the diff itself adds or edits (`diff_changesets`; any kind,
    including `none`), when the escape hatch is active (`skip=True`, wired from
    the `skip-changeset` PR label), or when the diff is a **release PR** — only
    what `pkit release apply` writes (`is_release_diff`), which has legitimately
    consumed the changesets it would otherwise need. A pending changeset the diff
    leaves alone declares another pull request's change, so it satisfies nothing
    here, whatever component it names. The floor tie (`stray_floors`) is waived
    by neither: it judges only a floor this diff declares, which a release diff
    never does, and an escape hatch that could pass one would let any pull
    request raise any component's floor.
    """
    repo_root = source_kit.parent
    components = discover_components(source_kit)
    files = changed_files(repo_root, base)
    touched = touched_components(components, files)

    pending = load_changesets(repo_root)
    declared = {cs.component for cs in diff_changesets(repo_root, pending, files)}
    missing = [name for name in touched if name not in declared]
    release_exempt = bool(missing) and is_release_diff(source_kit, base)
    return GuardResult(
        touched=touched,
        missing=missing,
        skipped=skip,
        release_exempt=release_exempt,
        stray_floors=stray_floors(repo_root, base, pending, files, touched),
    )


def diff_changesets(
    repo_root: Path, pending: Sequence[Changeset], files: Sequence[str]
) -> list[Changeset]:
    """The pending changesets the diff adds or edits — the ones it declares.

    `files` is the diff's changed paths (`changed_files`). A changeset counts
    when its file is among them: added on the branch, edited (whatever the edit —
    the guard reads which files changed, not what changed in them), or renamed
    into place, which git names by its destination. A pending changeset the diff
    leaves alone is not the diff's — one an earlier pull request merged, or one
    merging the base brought onto the branch — and neither is one only on disk,
    not committed. Reading the diff rather than the directory is what keeps the
    guard from passing on another pull request's declaration.
    """
    changed = set(files)
    return [cs for cs in pending if _repo_rel(repo_root, cs.path) in changed]


def stray_floors(
    repo_root: Path,
    base: str,
    pending: Sequence[Changeset],
    files: Sequence[str],
    touched: Sequence[str],
) -> list[Changeset]:
    """The changesets whose `requires_backbone` floor the diff vs `base` declares
    for a component it neither touches nor moves (PRJ-002 D4).

    A floor says the component no longer works on an older backbone, a claim a
    change to the component makes true — or, for a need found after the
    component shipped, a release of the component carrying only the floor. So a
    declaration rides on a diff touching the component's subtree
    (`touched_components`, a path heuristic), or on a changeset that moves the
    component's version (`patch` or above); one on a `none` changeset for a
    component the diff leaves alone has neither behind it.

    The diff declares a floor when it adds or edits a changeset and the floor
    it carries differs from the one the file held at the merge base — added, or
    its value or component changed. A pending changeset an earlier pull request
    merged, or one this diff edits elsewhere (its note, say), declares nothing
    here.
    """
    candidates = [
        cs
        for cs in diff_changesets(repo_root, pending, files)
        if cs.requires_backbone is not None and cs.segment == "none" and cs.component not in touched
    ]
    if not candidates:
        return []
    merge_base = _merge_base(repo_root, base)
    return [
        cs
        for cs in candidates
        if _declaration_at(repo_root, merge_base, _repo_rel(repo_root, cs.path))
        != (cs.component, cs.requires_backbone)
    ]


def _merge_base(repo_root: Path, base: str) -> str:
    """The commit the diff vs `base` is taken from (`base...HEAD`)."""
    result = subprocess.run(
        ["git", "merge-base", base, "HEAD"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )
    return result.stdout.strip()


def _declaration_at(repo_root: Path, rev: str, path: str) -> tuple[str, str | None] | None:
    """The component and floor field of the changeset at `path` in `rev`; None
    when `rev` has no such file or holds no changeset there."""
    result = subprocess.run(
        ["git", "show", f"{rev}:{path}"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )
    if result.returncode != 0:
        return None
    try:
        cs = parse_changeset_text(result.stdout, repo_root / path)
    except click.ClickException:
        return None
    return cs.component, cs.requires_backbone


# --- The changeset + changelog format lint (the OBJECTIVE subset) ---------
#
# A *format* lint distinct from the surface guard above: the guard asks
# "does a surface change carry a changeset?"; this asks "is the changeset /
# changelog *well-formed*?". It validates only the mechanically-checkable
# subset — category enum, `pr` shape, body shape, the floor field's value and
# carrier, changelog heading structure — and makes no attempt at the
# plain-language / no-jargon discipline, which is human judgment left to the
# guide (`.pkit/release/README.md`) and review. Same honest stance as the
# guard: a **reminder, not a proof**, with an escape hatch for the cases an
# objective rule necessarily mis-fires on. The floor field sits outside the
# hatch: it is the release's own refusal reported early, and an invalid one
# blocks every later release on `main`.

# A body that is *only* one of these bare references is the objective proxy for
# the "no in-body jargon / references" rule — an entry that says nothing to a
# reader who cannot resolve the reference. Full-match (whole stripped body).
_BARE_REF_RE = re.compile(r"(?:#\d+|ADR-\d+|DEC-\d+|COR-\d+|https?://\S+)", re.IGNORECASE)

# Accepted release-section (`## `) heading shapes. Two forms the generator
# emits (see `render_changelog_entry`): a version optionally dated, or a
# date-only section (a component-only release with no backbone key). The `—`
# em-dash is what the generator writes; a plain `-` and the canonical KaC
# `[version]` brackets are also accepted so a hand-edit in either idiom passes.
# Group 1 is the version, a backbone release the tree records
# (`recorded_backbone_releases`).
_CHANGELOG_VERSION_HEADING_RE = re.compile(
    r"^## \[?(\d+\.\d+\.\d+)\]?(?: [—-] \d{4}-\d{2}-\d{2})?$"
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

    violations: list[FormatViolation]  # the format subset the escape hatch covers
    skipped: bool  # the escape hatch was active
    # A floor field the release refuses (`lint_floor`), which the escape hatch
    # does not cover: it is for prose rules that mis-fire, and an invalid floor
    # field blocks every later release on `main` until it is fixed.
    floor_violations: list[FormatViolation] = field(default_factory=lambda: [])

    @property
    def ok(self) -> bool:
        return not self.floor_violations and (self.skipped or not self.violations)


def lint_changeset(cs: Changeset) -> list[FormatViolation]:
    """Objective format checks for one changeset.

    Category (when present) must be a Keep-a-Changelog group, and `pr` (when
    present) the pull request's number or a full URL ending in it
    (`is_pr_reference`). Body checks only apply to changesets that move a
    version (`segment != "none"`) — a `none` changeset never produces a
    changelog line, so its body carries no changelog-format obligation. A body
    that does become a changelog line must be non-empty, not *solely* a bare
    reference, capitalized, and end with a period.
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

    if cs.pr is not None and not is_pr_reference(cs.pr):
        violations.append(
            FormatViolation(
                where,
                f"`pr` is {cs.pr!r} — give the pull request's number (`503`) or its "
                "full URL (`https://github.com/<owner>/<repo>/pull/503`).",
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
        violations.append(FormatViolation(where, f"body should start capitalized: {body!r}."))
    if not body.endswith("."):
        violations.append(FormatViolation(where, f"body should end with a period: {body!r}."))

    return violations


def lint_floor(
    cs: Changeset, components: Mapping[str, Component], shipped: str, released: Collection[str]
) -> list[FormatViolation]:
    """The floor field of one changeset: what `compute_release` would refuse
    (`floor_problems`, against `shipped`, the backbone the release ships, and
    `released`, the backbone releases the tree records), reported where the
    changeset is written."""
    where = f"changeset {cs.path.name}"
    return [
        FormatViolation(where, problem)
        for problem in floor_problems(cs, components, shipped, released)
    ]


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
                _CHANGELOG_VERSION_HEADING_RE.match(line) or _CHANGELOG_DATE_HEADING_RE.match(line)
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
    `PKIT_CHANGELOG_LINT_SKIP` env var) — except for a floor field the release
    would refuse, which fails either way (`LintResult.floor_violations`). Reads
    committed files only; it needs no PR context, so it runs in the shared check
    aggregator. A floor field is checked against the components discovered under
    `source_kit`, the backbone the release would ship and the backbone releases
    the tree records (`lint_floor`), which are read only when a changeset
    carries one. A `.pkit/VERSION` that holds no version bounds no floor: it is
    reported once, as a floor violation, instead of each floor.
    """
    repo_root = source_kit.parent
    changesets = load_changesets(repo_root)
    floor_violations: list[FormatViolation] = []
    if any(cs.requires_backbone is not None for cs in changesets):
        components = {c.name: c for c in discover_components(source_kit)}
        current = components.get(BACKBONE)
        problem = backbone_version_problem(current) if current is not None else None
        if current is not None and problem is not None:
            where = _repo_rel(repo_root, current.version_path)
            floor_violations.append(FormatViolation(where, problem))
        else:
            shipped = shipped_backbone(components, changesets)
            released = recorded_backbone_releases(repo_root, components)
            for cs in changesets:
                floor_violations.extend(lint_floor(cs, components, shipped, released))

    violations: list[FormatViolation] = []
    for cs in changesets:
        violations.extend(lint_changeset(cs))

    changelog = repo_root / CHANGELOG_NAME
    if changelog.is_file():
        violations.extend(lint_changelog(changelog.read_text(encoding="utf-8")))

    return LintResult(violations=violations, skipped=skip, floor_violations=floor_violations)


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
    head_oid: str  # the head commit the gate reads (headRefOid); the merge is pinned to it
    base_ref: str  # the branch the PR merges into (baseRefName)
    cross_repository: bool  # head lives in a fork (isCrossRepository)
    url: str
    mergeable: str  # MERGEABLE / CONFLICTING / UNKNOWN (normalised upper-case)
    checks_passing: bool
    failing_checks: tuple[str, ...]  # names (+ outcome) of non-passing checks


@dataclass(frozen=True)
class ReleaseMergeDecision:
    """The gate's verdict on a release PR."""

    action: str  # "merge" | "already-done" | "refuse"
    message: str


def _check_identity(check: dict) -> str:
    """The identity a check re-runs under — `name` (CheckRun) / `context` (StatusContext)."""
    return check.get("name") or check.get("context") or "check"


def _check_timestamp(check: dict) -> str:
    """The instant a check's latest run reports, for ordering re-runs.

    A CheckRun carries `completedAt` (terminal) / `startedAt` (running); a
    StatusContext carries `createdAt`. ISO-8601 strings sort chronologically as
    plain strings, so the raw value is enough. Missing ⇒ empty string, which
    sorts first — so a timestamped run always wins over an untimed one, and ties
    (all untimed / equal) fall through to GitHub's roughly-chronological order.
    """
    return check.get("completedAt") or check.get("startedAt") or check.get("createdAt") or ""


def dedupe_to_latest_run(rollup: list[dict]) -> list[dict]:
    """Collapse a `statusCheckRollup` to the latest run per check identity.

    GitHub retains *every* run of a check in the rollup — so a check that failed
    then re-ran green (a fix-and-repush, a label re-trigger) appears twice, and a
    naive reduction counts the stale FAILURE. This keeps only the latest run per
    identity (by timestamp; ties broken by last-listed, GitHub returning roughly
    chronological), matching how `gh pr checks` reports. Output preserves each
    identity's first-seen order so the reduced failing-check list stays stable.
    """
    latest: dict[str, dict] = {}
    for check in rollup:
        identity = _check_identity(check)
        current = latest.get(identity)
        # `>=` keeps the last-listed on a timestamp tie (chronological input).
        if current is None or _check_timestamp(check) >= _check_timestamp(current):
            latest[identity] = check
    return list(latest.values())


def summarize_checks(rollup: list[dict] | None) -> tuple[bool, tuple[str, ...]]:
    """Reduce a `statusCheckRollup` to (all-passing, non-passing-check-labels).

    Handles both node shapes GitHub returns: a CheckRun carries `status`
    (COMPLETED / IN_PROGRESS / QUEUED) + `conclusion` (SUCCESS / FAILURE / …);
    a StatusContext carries `state` (SUCCESS / FAILURE / PENDING / ERROR). A
    check passes only when its outcome is a non-failing terminal one; a
    still-running check blocks (a release PR must be green before merging). An
    empty rollup (no checks configured) is treated as passing.

    The rollup is first deduped to the latest run per check identity
    (`dedupe_to_latest_run`) — GitHub keeps stale runs, so a check that failed
    then re-ran green would otherwise wrongly block the merge (#504).
    """
    failing: list[str] = []
    for check in dedupe_to_latest_run(rollup or []):
        name = _check_identity(check)
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


def parse_release_pr(raw: Mapping[str, Any]) -> ReleasePrState:
    """Build a `ReleasePrState` from the JSON `gh pr view --json …` returns."""
    passing, failing = summarize_checks(raw.get("statusCheckRollup"))
    return ReleasePrState(
        number=int(raw.get("number", 0)),
        title=str(raw.get("title", "")),
        state=str(raw.get("state", "")).upper(),
        head_ref=str(raw.get("headRefName", "")),
        head_oid=str(raw.get("headRefOid", "")),
        base_ref=str(raw.get("baseRefName", "")),
        # Absent reads as a fork: the unsafe default for the delete guard is
        # "same repository", so a missing field must not grant it.
        cross_repository=bool(raw.get("isCrossRepository", True)),
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
    refusal = release_pr_refusal(pr)
    if refusal is not None:
        return refusal
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


@dataclass(frozen=True)
class ReleaseMergeReport:
    """What `pkit release merge` came to: the report it prints, and its exit
    code — 0 when the merge and the clean-up are done, :data:`EXIT_ACCEPTED`
    when the merge was accepted and a later run completes it."""

    text: str
    exit_code: int = 0


#: `pkit release merge`'s exit when the merge was accepted but has not been
#: seen to land — a merge queue holds the PR, or GitHub could not be read to
#: confirm a direct merge. Nothing was deleted; the same command run again once
#: the PR has merged deletes the head branch.
EXIT_ACCEPTED = 4


class ReleaseNotMerged(click.ClickException):
    """The release PR left the merge queue without merging, or its head moved
    after its checks were read: nothing merged, nothing deleted."""

    exit_code = 3


def merge_release_pr(
    repo_root: Path,
    pr_number: int,
    *,
    clearance: session_guard.Clearance,
    dry_run: bool = False,
    wait_seconds: float | None = None,
    force: bool = False,
    say: Callable[[str], None] = click.echo,
) -> ReleaseMergeReport:
    """Merge a release PR through the sanctioned path.

    Fetches the PR (repo derived from the ambient `gh` context — no hardcoded
    owner/repo) and lands it with the backbone's one merge mechanic
    (`pull_request_landing`), which project-management's merge verbs call too.
    Where the base merges through a merge queue the PR is enqueued, pinned to
    the head whose checks the gate read, and the queue makes the merge; the
    run waits for it — `wait_seconds` None as long as the queue estimates, 0
    not at all — saying through `say` where the PR stands. A head the queue
    already dropped is not enqueued again unless `force`: the queue, or a
    maintainer, took it out for a reason. Without a queue it squash-merges
    directly, pinned to the same head. Either way the head branch is deleted,
    through the API and then locally — both best-effort, so a detached-HEAD
    or worktree run still completes (#897), and the local branch only when
    nothing on it is missing from the merge — once GitHub reports the PR
    merged.

    A PR already in the queue is waited for, not gated or enqueued again, with
    a warning when the queue would not make the release's squash commit; a
    merged one has only its clean-up run, so a run that returned while the PR
    was queued is completed by running it again. Does **not** tag: the flow's
    post-merge tag step cuts the backbone tag on the resulting push to `main`
    (VERSION-driven). Raises `click.ClickException` on a refusal, and
    :class:`ReleaseNotMerged` when the queue dropped the PR or its head moved.

    `clearance` is the cross-repository guard's for `repo_root`, cleared once
    at the entry (`session_guard.clear`): it covers every change the run makes
    there — the merge or the enqueue, the dequeue, the head branch's deletion
    and the local clean-up (ADR-061 point 6).
    """
    session_guard.require(clearance, repo_root)
    pr = parse_release_pr(_gh_pr_view(pr_number, repo_root))
    refusal = release_pr_refusal(pr)
    if refusal is not None:
        raise click.ClickException(refusal.message)
    if pr.state == "MERGED":
        return _after_the_merge(
            pr,
            repo_root,
            f"PR #{pr.number} is already merged",
            merged_head=pr.head_oid,
            dry_run=dry_run,
        )
    if pr.state == "CLOSED":
        return ReleaseMergeReport(f"PR #{pr.number} is closed (not merged) — nothing to merge.")

    base = pr.base_ref or "the base branch"
    gh = pull_request_landing.gh_runner(repo_root)
    try:
        queue = pull_request_landing.read(pr.number, gh=gh)
    except pull_request_landing.Unreadable as exc:
        raise click.ClickException(
            f"cannot tell how {base} merges: {exc}. Nothing was merged."
        ) from None
    if queue.merged:
        return _after_the_merge(
            pr,
            repo_root,
            f"PR #{pr.number} has merged ({queue.describe()})",
            merged_head=queue.head_oid or pr.head_oid,
            dry_run=dry_run,
        )
    if queue.queued:
        problem, remedy = _squash_commit_problem(queue, base, gh)
        if problem:
            _warn(
                f"release PR #{pr.number} is already in the merge queue for {base}, but "
                f"{problem}; the PR lands as the queue composes it. To land it as a release "
                f"lands, take it out of the queue (in the PR's merge box), "
                f"{_lower_first(remedy) + ', ' if remedy else ''}then run "
                f"`pkit release merge {pr.number}` again."
            )
        if dry_run:
            return ReleaseMergeReport(
                f"[dry-run] PR #{pr.number} is in the merge queue for {base} "
                f"({queue.describe()}); would {_wait_phrase(wait_seconds)}, then delete branch "
                f"{pr.head_ref!r}; nothing changed."
            )
        say(f"  PR #{pr.number} is already in the merge queue for {base}")
        return _await_the_queue(pr, repo_root, gh, clearance, wait_seconds, say)

    decision = evaluate_release_pr(pr)
    if decision.action != "merge":
        raise click.ClickException(decision.message)
    if queue.has_queue:
        problem = _queue_refusal(queue, base, gh, force=force)
        if problem:
            raise click.ClickException(problem)
        if dry_run:
            return ReleaseMergeReport(
                f"[dry-run] would enqueue PR #{pr.number} ({pr.title!r}) in the merge queue "
                f"for {base}, {_wait_phrase(wait_seconds)}, then delete branch "
                f"{pr.head_ref!r}; nothing enqueued."
            )
        if queue.dropped_head and queue.removal is not None:
            why = f": {queue.removal.reason}" if queue.removal.reason else ""
            say(
                f"  the merge queue dropped PR #{pr.number} at this head at "
                f"{queue.removal.at}{why}; enqueuing it again (--force)"
            )
        enqueued = pull_request_landing.enqueue(
            pr.number, cwd=repo_root, clearance=clearance, head_oid=pr.head_oid
        )
        if not enqueued.accepted:
            raise click.ClickException(
                f"`gh pr merge {pr.number} --auto` failed: {enqueued.reason}. Nothing was merged."
            )
        say(f"  enqueued PR #{pr.number} in the merge queue for {base}")
        return _await_the_queue(pr, repo_root, gh, clearance, wait_seconds, say)

    if dry_run:
        return ReleaseMergeReport(
            f"[dry-run] would squash-merge PR #{pr.number} ({pr.title!r}) and delete "
            f"branch {pr.head_ref!r}; nothing merged."
        )
    merged = pull_request_landing.squash_merge(
        pr.number,
        subject=pr.title,
        cwd=repo_root,
        clearance=clearance,
        head_oid=pr.head_oid,
    )
    if not merged.accepted:
        raise click.ClickException(f"`gh pr merge {pr.number}` failed: {merged.reason}")
    try:
        after = pull_request_landing.read(pr.number, gh=gh)
    except pull_request_landing.Unreadable as exc:
        _warn(f"could not confirm that PR #{pr.number} merged: {exc}. Reading it again.")
        return _await_the_queue(
            pr, repo_root, gh, clearance, wait_seconds, say, merged_directly=True
        )
    if after.merged:
        return _after_the_merge(
            pr,
            repo_root,
            f"Merged release PR #{pr.number} ({pr.url}).",
            merged_head=pr.head_oid,
        )
    say(
        f"  gh pr merge returned, but GitHub does not report PR #{pr.number} merged: {base} "
        "may have begun to merge through a queue, which took the PR in. Waiting for it as "
        "for a queued PR."
    )
    return _await_the_queue(pr, repo_root, gh, clearance, wait_seconds, say, merged_directly=True)


def release_pr_refusal(pr: ReleasePrState) -> ReleaseMergeDecision | None:
    """The refusal of a PR that is not a release PR — a `release/*` head under
    a `chore(release):` title — else None. A non-release PR is pointed at the
    issue-PR gate."""
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
    return None


def _queue_refusal(
    queue: pull_request_landing.Reading,
    base: str,
    gh: pull_request_landing.GhRunner,
    *,
    force: bool,
) -> str:
    """Why the release PR may not go through `base`'s queue, or "".

    The queue must make the release's squash commit (:func:`_squash_commit_problem`);
    nothing is enqueued on a commit shape that is not, or cannot be read. A
    head the queue already dropped is not enqueued again unchanged unless
    `force`: its checks may have failed on the merge the queue was about to
    make, or a maintainer may have taken it out on purpose — the rule
    project-management's merge verbs keep.
    """
    problem, remedy = _squash_commit_problem(queue, base, gh)
    if problem:
        then = f"{remedy}, then re-run. " if remedy else ""
        return f"{problem}. {then}Nothing was enqueued."
    removal = queue.removal
    if queue.dropped_head and removal is not None and not force:
        why = f"GitHub says: {removal.reason}" if removal.reason else "GitHub gives no reason"
        return (
            f"the merge queue on {base} dropped the PR at its current head "
            f"{queue.head_oid[:7]} at {removal.at} ({why}); the same head is not enqueued "
            "again unchanged. Fix what made the queue drop it and push, then re-run; or pass "
            "--force to enqueue this head again. Nothing was enqueued."
        )
    return ""


def _squash_commit_problem(
    queue: pull_request_landing.Reading, base: str, gh: pull_request_landing.GhRunner
) -> tuple[str, str]:
    """Why the squash commit `base`'s queue makes would not be the release's,
    and what fixes it; ("", "") when it would be.

    The queue makes the squash commit itself, by its own merge method and
    composed from the repository's squash-commit defaults, ignoring what a
    merge command passes. A release lands as one squash commit whose subject
    is the PR title, so the queue must squash and the defaults must be the PR
    title and body; defaults that cannot be read are a problem too, with no
    fix to name but reading them again.
    """
    if not queue.squashes:
        method = queue.merge_method or "an unreported method"
        return (
            f"the merge queue on {base} merges by {method}, and a release lands as one "
            "squash commit whose subject is the PR title",
            "Set the queue's merge method to squash in the repository's branch rules",
        )
    try:
        title, message = pull_request_landing.squash_commit_defaults(gh=gh)
    except pull_request_landing.Unreadable as exc:
        return (
            f"the repository's squash-commit defaults, which the merge queue on {base} "
            f"composes the squash commit from, cannot be read: {exc}",
            "",
        )
    if (title, message) != (pull_request_landing.PR_TITLE, pull_request_landing.PR_BODY):
        return (
            f"the merge queue on {base} composes the squash commit from the repository's "
            f"defaults, title {title} and message {message}, and a release lands under its PR "
            "title over its PR body",
            "Set them with `gh api -X PATCH repos/{owner}/{repo} -f "
            "squash_merge_commit_title=PR_TITLE -f squash_merge_commit_message=PR_BODY`",
        )
    return "", ""


def _lower_first(text: str) -> str:
    return text[:1].lower() + text[1:]


def _await_the_queue(
    pr: ReleasePrState,
    repo_root: Path,
    gh: pull_request_landing.GhRunner,
    clearance: session_guard.Clearance,
    wait_seconds: float | None,
    say: Callable[[str], None],
    *,
    merged_directly: bool = False,
) -> ReleaseMergeReport:
    """Wait for the merge queue to merge the release PR, then delete its head.

    `merged_directly`: gh accepted a direct merge, so when GitHub cannot be read
    the PR may have merged rather than be queued, and the report says so.
    Nothing is deleted unless GitHub reports the PR merged.
    """
    base = pr.base_ref or "the base branch"
    number = pr.number
    rerun = f"`pkit release merge {number}`"
    if wait_seconds != 0:
        awaited = "GitHub to report it merged" if merged_directly else "the queue to merge it"
        say(
            f"  waiting for {awaited}, "
            f"{pull_request_landing.wait_limit(wait_seconds)} (--no-wait returns at once)"
        )

    def report(reading: pull_request_landing.Reading) -> None:
        say(f"  queue:   PR #{number} {reading.describe()}")

    try:
        wait = pull_request_landing.wait_for_merge(
            number,
            timeout_seconds=wait_seconds,
            on_change=report,
            head_oid=pr.head_oid,
            gh=gh,
        )
    except pull_request_landing.Unreadable as exc:
        if merged_directly:
            return ReleaseMergeReport(
                f"[unconfirmed] gh accepted the merge of release PR #{number} into {base}, "
                f"but GitHub could not be read to confirm that it merged: {exc}. Nothing was "
                f"deleted. Run {rerun} again once GitHub answers: it deletes the head branch "
                "once the PR has merged.",
                EXIT_ACCEPTED,
            )
        return ReleaseMergeReport(
            f"[queued] release PR #{number} was handed to the merge queue for {base}, and "
            f"whether it has merged since could not be read: {exc}. Its head branch is kept; "
            f"run {rerun} again once it has merged to delete it.",
            EXIT_ACCEPTED,
        )
    reading = wait.reading
    queue_seen = reading.has_queue or reading.ever_queued
    if wait.ended == pull_request_landing.MERGED:
        through = " through the merge queue" if queue_seen else ""
        return _after_the_merge(
            pr,
            repo_root,
            f"Merged release PR #{number} ({pr.url}){through}.",
            merged_head=reading.head_oid or pr.head_oid,
        )
    if wait.ended == pull_request_landing.STILL_QUEUED:
        return ReleaseMergeReport(
            f"[queued] release PR #{number} is in the merge queue for {base} "
            f"({reading.describe()}). Its head branch is kept until it merges: run {rerun} "
            "again once it has merged to delete it.",
            EXIT_ACCEPTED,
        )
    if wait.ended == pull_request_landing.HEAD_MOVED:
        moved = (
            f"release PR #{number}'s head moved from {pr.head_oid[:7]} to "
            f"{reading.head_oid[:7]} after its checks were read"
        )
        out = pull_request_landing.dequeue(number, cwd=repo_root, clearance=clearance)
        if out.accepted:
            raise ReleaseNotMerged(
                f"{moved}; it was taken out of the merge queue, so nothing unchecked merges. "
                f"Nothing was deleted; run {rerun} again once the new head is green."
            )
        raise ReleaseNotMerged(
            f"{moved}, and taking it out of the merge queue failed ({out.reason}): it may "
            "still merge commits nothing checked. Take it out yourself — in the PR's merge "
            f"box, or `gh pr merge {number} --disable-auto` while it waits to enter. Nothing "
            "was deleted."
        )
    if not queue_seen:
        # A direct merge gh accepted on a base with no queue, never seen merged:
        # no queue was involved, and the report does not say one dropped it.
        state = "closed without merging" if reading.pr_state == "CLOSED" else "still open"
        raise ReleaseNotMerged(
            f"gh accepted the merge of release PR #{number} into {base}, but GitHub reports "
            f"it {state}. Nothing was deleted; look at the PR, then run {rerun} again."
        )
    removal = reading.removal
    why = f" GitHub says: {removal.reason}." if removal is not None and removal.reason else ""
    raise ReleaseNotMerged(
        f"release PR #{number} left the merge queue for {base} without merging, as far as "
        f"the queue reports ({reading.describe()}).{why} Nothing was deleted. Fix what made "
        f"the queue drop it, then run {rerun} again."
    )


def _after_the_merge(
    pr: ReleasePrState,
    repo_root: Path,
    headline: str,
    *,
    merged_head: str,
    dry_run: bool = False,
) -> ReleaseMergeReport:
    """What follows the merge — the head branch deleted through the API, then the
    local clean-up — once GitHub reports the PR merged.

    `merged_head` is the head the PR merged at: the local branch is deleted
    only when nothing on it is missing from the merge, and a merge at a head
    other than the one whose checks were read is warned about.
    """
    if dry_run:
        return ReleaseMergeReport(
            f"[dry-run] {headline}; would delete branch {pr.head_ref!r}; nothing changed."
        )
    if merged_head and pr.head_oid and merged_head != pr.head_oid:
        _warn(
            f"release PR #{pr.number} merged at head {merged_head[:7]}, not at "
            f"{pr.head_oid[:7]}, the head whose checks were read."
        )
    notes = [
        _gh_delete_remote_branch(pr.head_ref, repo_root, cross_repository=pr.cross_repository),
        *_git_cleanup_local(
            pr.head_ref,
            pr.base_ref or "main",
            repo_root,
            cross_repository=pr.cross_repository,
            merged_head=merged_head,
        ),
    ]
    return ReleaseMergeReport(
        "\n".join(
            [
                headline if headline.endswith(".") else f"{headline}.",
                *(f"  {note}" for note in notes if note),
                "  Not tagged here: the post-merge tag step cuts the backbone tag on the push "
                "to main (VERSION-driven).",
            ]
        )
    )


def _wait_phrase(seconds: float | None) -> str:
    """What a run does once the PR is queued, as a phrase."""
    if seconds == 0:
        return "return once it is queued (--no-wait)"
    return f"wait for its merge, {pull_request_landing.wait_limit(seconds)}"


def _gh_pr_view(pr_number: int, repo_root: Path) -> dict:
    """`gh pr view <n> --json …` from `repo_root`, parsed to a dict."""
    fields = (
        "number,title,state,headRefName,headRefOid,baseRefName,isCrossRepository,"
        "mergeable,url,statusCheckRollup"
    )
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
        raise click.ClickException(f"`gh pr view {pr_number}` failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


# The merge itself is `pull_request_landing`'s, the one mechanic the
# project-management capability's merge verbs call too. The head-branch
# clean-up below still mirrors that capability's `scripts/_lib/pr_merge.py`
# (delete_remote_branch / cleanup_local): the capability's scripts run as
# standalone `uv run --script`s that do not import `project_kit`. Keep the two
# in step: a fix to either (the fork-PR guard, the already-deleted answer, the
# merged-head guard on the local delete) belongs in both.

_REF_ALREADY_DELETED_MARKER = "Reference does not exist"


def _warn(message: str) -> None:
    click.echo(f"[warn] {message}", err=True)


def _gh_delete_remote_branch(branch: str, repo_root: Path, *, cross_repository: bool) -> str:
    """Delete the PR's remote head ref through the API — best-effort.

    Returns a status line for the report ("" after a warning). Mirrors the
    project-management capability's `_lib/pr_merge.delete_remote_branch` (see
    the note on keeping the two in step, above `_REF_ALREADY_DELETED_MARKER`).

    `cross_repository` is required and has no default: the ref is deleted in
    the BASE repository (`{owner}/{repo}` resolves there), so for a PR whose
    head lives in a fork the head-branch name is chosen by the fork's author
    and may name an unrelated base-repo branch. Such a head is never deleted
    here. The `release/*` head guard does not cover this — a fork can name its
    branch `release/…` too.

    The API call needs nothing from the working tree. A ref that is already
    gone (a repository that auto-deletes head branches on merge) is reported,
    not warned about.
    """
    if cross_repository:
        return (
            f"head branch {branch!r} lives in a fork; not deleting a "
            "base-repository ref of that name."
        )
    try:
        result = subprocess.run(
            ["gh", "api", "-X", "DELETE", f"repos/{{owner}}/{{repo}}/git/refs/heads/{branch}"],
            capture_output=True,
            text=True,
            cwd=repo_root,
            check=False,
        )
    except FileNotFoundError:
        _warn(f"`gh` not on PATH; delete remote branch {branch} by hand.")
        return ""
    if result.returncode == 0:
        return f"deleted remote branch {branch!r}."
    stderr = result.stderr.strip()
    if _REF_ALREADY_DELETED_MARKER in stderr:
        return f"remote branch {branch!r} already deleted."
    _warn(
        f"could not delete remote branch {branch}: {stderr}. The merge is "
        f"durable; delete it by hand (`git push origin --delete {branch}`)."
    )
    return ""


def _git_cleanup_local(
    branch: str,
    base_branch: str,
    repo_root: Path,
    *,
    cross_repository: bool,
    merged_head: str,
) -> list[str]:
    """Switch to the base branch, fast-forward it, delete the local head — best-effort.

    Returns status lines for the report; every failing step warns with git's
    reason and continues, so none can fail the run. Mirrors the
    project-management capability's `_lib/pr_merge.cleanup_local` (see the
    note on keeping the two in step, above `_REF_ALREADY_DELETED_MARKER`),
    except the branch returned to is the PR's own base (`baseRefName`) — the
    backbone reads no capability config.

    When the checkout cannot happen (detached HEAD, the base branch checked out
    in another worktree) the pull is skipped — pulling into whatever IS checked
    out would be wrong — but the branch delete is still attempted. A head with
    no local copy (a release PR opened by CI) is skipped silently rather than
    warned about. `-D` (not `-d`) because a squash-merged branch is never an
    ancestor of the base.

    `merged_head` is the head the PR merged at, and is required: the local
    branch is deleted only when everything on it merged — its tip is that
    head or behind it. A branch holding commits the merge does not — work
    since, or a clone that cannot tell, as one without the merged head or
    told no head — is kept with a warning.

    `cross_repository` is required and has no default: for a fork PR the local
    delete is skipped — a local branch sharing the fork branch's name is not
    that PR's head, and `-D` would discard its unpushed work.
    """

    def _git(*argv: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *argv],
            capture_output=True,
            text=True,
            cwd=repo_root,
            check=False,
        )

    notes: list[str] = []
    result = _git("checkout", base_branch)
    if result.returncode != 0:
        _warn(f"git checkout {base_branch} failed: {result.stderr.strip()}")
    else:
        result = _git("pull", "--ff-only")
        if result.returncode != 0:
            _warn(f"git pull failed: {result.stderr.strip()}")
        else:
            notes.append(f"updated local {base_branch!r}.")
    if cross_repository:
        return notes
    tip = _git("rev-parse", "--verify", "--quiet", f"refs/heads/{branch}").stdout.strip()
    if not tip:
        return notes  # no local copy (the usual case: CI opened the release PR)
    # The commits on the branch the merged head does not hold: none, and
    # everything on it merged. A head this clone does not have fails the
    # count, which keeps the branch too.
    unmerged = _git("rev-list", "--count", f"{merged_head}..{tip}") if merged_head else None
    if unmerged is None or unmerged.returncode != 0 or unmerged.stdout.strip() != "0":
        _warn(
            f"local branch {branch} (at {tip[:7]}) holds commits the merge at "
            f"{merged_head[:7] or 'an unknown head'} does not, or this clone cannot tell; it "
            f"is kept. Delete it yourself once nothing on it is needed "
            f"(`git branch -D {branch}`)."
        )
        return notes
    result = _git("branch", "-D", branch)
    if result.returncode != 0:
        _warn(f"git branch -D {branch} failed: {result.stderr.strip()}")
    else:
        notes.append(f"deleted local branch {branch!r}.")
    return notes


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
_REQUIRES_BACKBONE_RANGE_RE = re.compile(r"^>=\d+\.\d+\.\d+,<\d+\.\d+\.\d+$")

# Cheaply-detectable local-only assumptions: an absolute filesystem path or a
# `file://` URL in the manifest points at something a consumer will not have.
# A heuristic reminder, not a proof — matched against the raw manifest text.
_LOCAL_PATH_RE = re.compile(
    r'(?m)(?:^|\s|["\':=])(/(?:Users|home|tmp|var|opt|private)/\S+|file://\S+)'
)


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


def publish_release_notes(
    repo_root: Path,
    version: str,
    *,
    clearance: session_guard.Clearance,
    dry_run: bool = False,
) -> str:
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

    `clearance` is the cross-repository guard's for `repo_root`, cleared at the
    entry (`session_guard.clear`), before `gh` is asked anything (ADR-061
    point 6).
    """
    session_guard.require(clearance, repo_root)
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
            ["gh", "release", "create", tag, "--title", tag, "--notes", notes, "--verify-tag"],
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
        raise click.ClickException(f"`gh release create {tag}` failed: {result.stderr.strip()}")


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
        raise click.ClickException(f"`gh release edit {tag}` failed: {result.stderr.strip()}")
