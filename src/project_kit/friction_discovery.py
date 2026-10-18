"""Artefact discovery for the friction functionality (COR-050 point 1).

The backbone looks for anchored artefacts only in the **places declared to
hold them**, so unrelated front matter elsewhere is never misread. This module
is the one reader of those declarations and the one walker of the places:

- `read_friction_settings` — the project's `friction` key in the backbone
  configuration (COR-050 point 14: mode, places, surface, exclude) and each
  installed capability's `friction.places` / `friction.held` /
  `friction.surface`, read *forgivingly* (COR-048 point 4): a missing or oddly
  shaped value reads as absent here, and the strict judgment of its shape
  belongs to the configuration and package schemas (Tasks #981, #982). A
  capability place, held folder or surface entry the reader cannot read in the
  package schema's shape is not dropped, though: it is kept as a
  `MalformedDeclaration`, which the validation pass reports, so a declaration
  the walk cannot follow is never silence (COR-050 point 7). A capability's
  `friction.surface` is a list of repository-relative paths or globs, read as
  written. What this module does judge — because COR-050 point 12 assigns it
  to validation — is done in `friction_validate`.
- `declared_places` — the resolved places, project first (in declaration
  order) then capabilities by name. A capability's place is an object
  `{path, location?, type?, description?}` (the package schema's
  `friction-place`): with `location`, inside that entry of the document
  locations it declares — where
  `docs_roots.read_capability_locations`, the one reading of a capability's
  locations, puts it: its recorded location, else its declared sub-path under
  the root it names (COR-049 points 4 and 5; COR-050 point 1); without one,
  repository-relative.
- `held_folders` — the folders of **held documents** a capability declares
  (`friction.held`, COR-050 point 1): files that belong to it but are not
  artefacts, such as a log of reviews it carried out. A held folder is written
  as a place is, with a `location` it lies within and a folder — never a glob
  — as its `path`, and matched as a place is, but nothing in it is walked as
  an artefact: no place — a root, another component's or the project's, its
  own or a rule-set folder — reads a held file, so neither measure counts it.
  It is bounded: one that equals or encloses a documentation root or another
  declaration's place, or shares a file with another held folder, its own
  component's place or a rule-set folder, holds nothing and says why
  (`HeldFolder.skipped`) — one holder per file, and rules stay artefacts
  (COR-051 point 2). A project declares none: it narrows its own places, and
  keeps what must not count out of the measures with `exclude` (COR-050
  point 14).
- `rule_set_places` / `rule_set_files` — the location rule for rule-set files
  (COR-051 point 2, ADR-056 point 2): the places declared to hold rule sets,
  each with the component that owns the sets in it, and the Markdown files
  they claim. Rules are artefacts found where artefacts are found, so the
  walk below covers these places too.
- `discover_artefacts` — every artefact in the places, in a deterministic
  order: a Markdown document with front matter, or one keyed entry of a
  collection file (a Markdown file whose front matter maps ids to entries;
  an entry's content is its data plus the body section headed by its id).
  A rule-set file is the collection whose entries are the values of its
  `rules` map, one artefact per rule. An entry's section is cut by the one
  reading of where a part of a document lies (`document_parts`), from the
  headings outside fenced code. The rule-set pass lists a file's sections by
  the same reading, so the two find the same sections. A plain YAML file in a
  place is not a document (ADR-056 point 2). `parse_artefacts` is the reading
  of one file's text this walk applies; the whole-repository check applies it
  to a file's earlier versions too, so history is read by the same rule as the
  present. A text is read whatever its line endings (`universal_newlines`, in
  `document_parts.split_front_matter`), so a clone that checks files out with
  `\\r\\n` finds the blocks and the content one with `\\n` finds; a file
  mixing them is recorded (`DiscoveredFile.mixed_line_endings`) for the
  validation pass.
  A file a declared place matches that is a synced copy is not walked — a
  place is never a synced tree (COR-050 point 14) — and is kept as a
  `SyncedMatch` for the validation pass to report; the question is the tree's
  own ownership predicate's (`synced_copy_test`), never re-derived here. A
  held file is not walked by any place either: it is kept as a `HeldFile`,
  with the folder holding it and the places that match it, and read only for
  its front matter — a friction block anywhere in it is a validation finding
  (COR-050 point 12).
- `FrictionSettings.exclusion` — the one decision of what `friction.exclude`
  leaves out (COR-050 point 7). The walk records it on every file, artefact
  and held file it reads (`excluded_by`), so the measures read it from the
  artefact; the checks ask it of any other path, never matching the
  patterns themselves — each state's of its own paths, as discovery over
  that state reads its settings (`excludes_as` says whether two states
  leave out the same).
- `RepositoryTree` — the seam through which discovery lists and reads one
  state of the repository, matching every listing by one rule
  (`listed_files_in_place`, `compile_glob`, `pattern_matches`). Without a
  tree, discovery reads the working tree's one listing (`working_tree`):
  the files git sees, the same listing the change check (COR-050 point 6)
  reads as its head beside its base commit — so validation, the writers and
  the change check find the same artefacts in the same working tree
  (ADR-057 point 2). A link is a file of any listing, never followed and never
  read as a document.
- `artefacts_document` — the one walk's answer as a stable document: the
  declared places with the files each matches and the skips validation
  applies, every file read with its place and its front matter's own fields,
  every artefact with its anchors, an entry's section span, the span each of
  its part anchors resolves to, its type and the rule sets whose scope covers
  it, every declared type, and the held folders,
  declared as places are, with every file each holds — of the working tree, or
  of a commit.
  `pkit friction artefacts --json` prints it, and a capability's script reads
  where artefacts are through it, at head or at another state, never by
  walking the places or listing a commit itself (ADR-057 points 1 and 2).
- `Artefact.body` and `Artefact.span` — a collection entry's section, the
  text both checks compare as its body, and the lines of its file that text
  spans: one reading of where the section lies gives both (`_entry_body`,
  over `document_parts.Body`), so a reader of the span reads exactly what
  friction compares (COR-050 point 1).
- `Discovery.types` (`resolve_types`) — every artefact's type (COR-056): the
  backbone's own types and the installed components' type registries
  (`FrictionSettings.type_registry`), the type each place names, and the order
  of the places matching a file (`place_specificity`). Every rule is
  `backbone:rule`, a project place yields to a component's place that is not
  root-wide, a root-wide place comes last, and otherwise the more specific
  place wins. A kind field gates a type, and a tie counts as each type in
  contention. The type findings are raised here, once, and one table names the
  member that reports each and its severity (`TYPE_FINDINGS`; ADR-057 point 2).
- `covering_rule_sets` — the rule sets whose scope covers each artefact
  (COR-051 point 2): its `paths` and `exclude` are each read as a place is
  (`listed_files_in_place`), and its `types` select by the one resolution of
  types. A plain list is its `paths`.
- `content`, `parsed_at`, `deferral_reason` — what one artefact's block and
  fields say, read the same way by both checks and by the walk through an
  artefact's history (`friction_history`): its content, never the container
  (COR-050 point 5); the parsed instant of `at`, so writing the same instant
  differently is no change (point 3); and a deferral's reason, whitespace
  folded (point 4).
- `record_content` — what a whole record anchor stands on (COR-050 point 5):
  a record's content, read from its file's bytes by the one reading that
  gives an artefact's content (`document_content`), whether or not a place
  holds the record, so nothing in the methodology's container counts. A
  record whose front matter does not parse to a mapping is its whole file,
  line endings read universally. Both checks call it, at each state they
  compare (ADR-057 point 2); the home of a record's points does not compute
  it.

Nothing here computes friction: the checks (`friction_check`,
`friction_repository`) and the history walk read the model this module
produces. The listing of the working tree has its home in `working_tree`; the
git plumbing behind a commit in `friction_git`.
"""

from __future__ import annotations

import functools
import json
import os
import re
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, Protocol, cast

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from project_kit import command_runner, docs_roots, lifecycle_ownership, validators
from project_kit.backbone_schemas import CONTAINER_KEY
from project_kit.document_parts import (
    Body,
    SectionSpan,
    body_first_line,
    parse_front_matter,
    yaml_reason,
)
from project_kit.line_breaks import line_break, universal_newlines
from project_kit.manifest import read_backbone_manifest
from project_kit.record_points import PointState, RecordPoints, read_points_bytes, split_anchor
from project_kit.report_context import project_config_path
from project_kit.working_tree import WorkingTree, working_tree

# The key this functionality owns in the backbone configuration and in a
# capability's package metadata — the same word as the block and the command
# group (COR-050 point 1, COR-053 point 10).
FRICTION_KEY = "friction"

# The key of the block an artefact with nothing to anchor to carries instead of
# anchors: the reason a person accepted it with none (COR-050 point 1).
UNANCHORED_BECAUSE_KEY = "unanchored-because"

# The package schema's shape a capability place is read in:
# `{path, location?, type?, description?}`, `location` naming an entry of the
# capability's `docs.locations`, which `docs_roots.read_capability_locations`
# resolves.
PATH_KEY = "path"
LOCATION_KEY = "location"

# The lists of a capability's `friction` block written in that shape, and what
# a finding calls one entry of each: its places, and its folders of held
# documents (COR-050 point 1).
PLACES_KEY = "places"
HELD_KEY = "held"
_ENTRY_NOUN = {PLACES_KEY: "place", HELD_KEY: "held folder"}

# The package schema's shape of one entry of each list, as a finding names it:
# `friction-place` and `friction-held`.
_ENTRY_SHAPE = {
    PLACES_KEY: "{path, location?, type?, description?}",
    HELD_KEY: "{location, path, description?}",
}

# A type (COR-056 points 1 and 2): the key of a component's type registry in
# its `friction` block, the keys of a registry entry, and the key of the type a
# place names — a component's place in its package metadata, a project's place
# written `{path, type}` in the backbone configuration.
TYPES_KEY = "types"
TYPE_KEY = "type"
TYPE_DESCRIPTION_KEY = "description"
KIND_FIELD_KEY = "kind-field"
PROJECT_PLACES_KEY = "project-places"

#: A type's name within its owner, and the whole of a bare project type: a word
#: of lower-case letters and digits, joined by single hyphens, so it holds no
#: `:` and no `/` (COR-056 point 1).
TYPE_NAME_PATTERN = r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*"
_TYPE_NAME = re.compile(TYPE_NAME_PATTERN)
#: A type as a place or a scope writes it: `<owner>:<name>`, or a bare `<name>`.
_TYPE = re.compile(rf"(?:(?P<owner>[a-z](?:[a-z0-9-]*[a-z0-9])?):)?(?P<name>{TYPE_NAME_PATTERN})")

# Who declares a place the project's configuration declares.
PROJECT_SOURCE = "project"

# The friction modes COR-050 point 12 names; `warning` is the default (point 14).
FRICTION_MODES: tuple[str, ...] = ("warning", "enforcing")
DEFAULT_FRICTION_MODE = "warning"

# Where installed capabilities live, relative to the project root.
CAPABILITIES_DIR = Path(".pkit") / "capabilities"

# The backbone manifest, relative to the project root: the installed
# capabilities are read from it (on disk through `manifest.read_backbone_manifest`).
BACKBONE_MANIFEST = Path(".pkit") / "manifest.yaml"

# Only Markdown files can be documents or collections (ADR-056 point 2).
DOCUMENT_SUFFIX = ".md"

# The location rule for rule-set files (COR-051 points 2 and 6; the schemas
# README, "Rule-set files"): a folder of this name holds rule sets. A method
# rule set ships in its component's own folder — the backbone's directly under
# `.pkit/`, a capability's in its subtree; a project rule set lives in the one
# under the internal documentation root, or in a declared place whose path has
# this segment. Nothing in the file itself binds it.
RULE_SETS_SEGMENT = "rule-sets"
BACKBONE_RULE_SETS_DIR = Path(".pkit") / RULE_SETS_SEGMENT

# The component name a backbone-shipped rule set is cited with.
BACKBONE_COMPONENT = "backbone"

# The front-matter key of a rule-set file whose values are its entries.
RULES_KEY = "rules"

# The front-matter key of a rule-set file that gives its scope: which artefacts
# its rules apply to, as places (COR-051 point 2).
SCOPE_KEY = "scope"

# A signpost in a rule-set folder describes the folder; it is not a rule set,
# as a README in a decision-record folder is not a record.
RULE_SETS_SIGNPOST = "README.md"

# Directories a glob never descends into: git's own store.
_SKIPPED_TOP_LEVEL = frozenset({".git"})

_GLOB_CHARS = frozenset("*?[")

_yaml = YAML(typ="safe")


# --- repository trees ---------------------------------------------------


class RepositoryTree(Protocol):
    """A read-only view of the repository's files at one state.

    The working tree and a commit are the two a caller needs side by side
    (the change check, COR-050 point 6). Discovery through a tree lists the
    tree's files and never follows a link: a link is a file the tree holds,
    matched like any other, but never read as a document.
    """

    def files(self) -> Sequence[str]:
        """Every file the state holds, links included: repository-relative POSIX paths, sorted."""
        ...

    def read_bytes(self, paths: Sequence[str]) -> Mapping[str, bytes | None]:
        """Each path's content, read in one pass; `None` for a link or a path the state lacks."""
        ...


# --- settings -----------------------------------------------------------


@dataclass(frozen=True)
class PlaceLocation:
    """The documentation location a capability place lies inside (COR-049 point 4).

    `name` is its entry in the capability's `docs.locations`, `path` where it
    lies — repository-relative, recorded or derived, as
    `docs_roots.read_capability_locations` reads it — and `root` the root its
    declaration names (`internal` or `user`), or `None` when only a recorded
    location stands for a declaration the reading cannot place.
    """

    name: str
    path: str
    root: str | None


@dataclass(frozen=True)
class SettingsPath:
    """One path or glob a setting declares, with where it was written.

    `value` is the text as written; `resolved` the repository-relative form
    discovery walks (for a capability's place, the location prefix is already
    joined). `file` is the declaring file relative to the project root and
    `pointer` a JSON Pointer to the value in it, so a finding can name both.
    `location` is the documentation location a capability place names, if any.
    `type` is the type a place names, in full (COR-056 point 2): for a
    project's place as written, for a capability's place `<capability>:<name>`
    — `None` when it names none, or a value its schema refuses. Whether the
    place gives that type is the type resolution's to judge (`Types`).
    """

    value: str
    resolved: str
    file: str
    pointer: str
    source: str  # "project" or "capability:<name>"
    location: PlaceLocation | None = None
    type: str | None = None

    @property
    def is_capability(self) -> bool:
        """Declared in a capability's package metadata, not the project's configuration."""
        return self.source.startswith("capability:")


@dataclass(frozen=True)
class MalformedDeclaration:
    """A capability place, held folder or surface entry the reader could not
    read, and why (COR-050 point 7).

    It is not among the places, the held folders or the surface, so nothing
    under it is walked or held and nothing is measured against it; the
    validation pass reports it. `file` is the package metadata relative to the
    project root and `pointer` a JSON Pointer to the entry — or to
    `friction.places`, `friction.held` or `friction.surface` itself when that is
    not a list.
    """

    file: str
    pointer: str
    source: str  # "capability:<name>"
    reason: str


@dataclass(frozen=True)
class DeclaredType:
    """One type its owner declares (COR-056 point 2): an entry of a component's
    type registry, or one of the backbone's own types.

    `owner` is the component, or `backbone`, and `name` the type's name within
    it. `kind_field` is the artefact's own field in which an artefact of the
    type declares its kind (point 4), or `None`. `project_places` is whether a
    project may give the type to its own places: an entry that does not say
    admits none, and the backbone's types admit none.
    """

    owner: str
    name: str
    description: str | None = None
    kind_field: str | None = None
    project_places: bool = False

    @property
    def type(self) -> str:
        """The type's full name, `<owner>:<name>`."""
        return f"{self.owner}:{self.name}"


#: The backbone's type for rules: every rule takes it, whatever place matches its
#: file (COR-056 point 3).
RULE_TYPE = f"{BACKBONE_COMPONENT}:rule"

#: The backbone's own types (COR-056 point 2). The backbone gives them without
#: any place, and no place may name one.
BACKBONE_TYPES: tuple[DeclaredType, ...] = (
    DeclaredType(
        owner=BACKBONE_COMPONENT,
        name="rule",
        description="A rule: one entry of a rule-set file (COR-051 point 2).",
    ),
)


@dataclass(frozen=True)
class FrictionSettings:
    """The `friction` settings discovery reads (COR-050 points 1 and 14).

    `mode` is the raw value as written — `None` when absent; the configuration
    pass judges it against the schema — and `mode_or_default` is what a reader
    uses, falling back to the default for anything it does not recognise.
    `exclusion` is the one decision of what `exclude` leaves out;
    `exclude_unreadable` says why `exclude` could not be read in full — the
    configuration file does not parse, or the key or an entry of it has the
    wrong shape — so a check comparing two states never reads a state whose
    exclusions it could not read as one that excludes nothing (COR-050 point
    7). `held` are the capabilities' folders of held documents, resolved as
    their places are; a project declares none. `internal_root` and
    `user_root` are the documentation roots, read from the same state.
    `types` are the installed capabilities' type registries, each by name in
    written order, and `installed` the installed capabilities' names (COR-056
    point 2). `refused_types` are the project's places whose `type` the
    configuration's schema refuses, each with that value as written in
    `value`: they give no type, and a reader warns (`refused_type_warnings`).
    """

    mode: Any
    places: tuple[SettingsPath, ...]
    surface: tuple[SettingsPath, ...]
    exclude: tuple[SettingsPath, ...]
    internal_root: str  # the documentation root a location resolves under by default
    user_root: str
    malformed_places: tuple[MalformedDeclaration, ...] = ()
    malformed_surface: tuple[MalformedDeclaration, ...] = ()
    held: tuple[SettingsPath, ...] = ()
    malformed_held: tuple[MalformedDeclaration, ...] = ()
    exclude_unreadable: str | None = None
    types: tuple[DeclaredType, ...] = ()
    installed: tuple[str, ...] = ()
    refused_types: tuple[SettingsPath, ...] = ()

    @property
    def roots(self) -> dict[str, str]:
        """The documentation roots by audience, repository-relative (COR-049 point 1)."""
        return {docs_roots.INTERNAL_KEY: self.internal_root, docs_roots.USER_KEY: self.user_root}

    @property
    def type_registry(self) -> dict[str, DeclaredType]:
        """Every declared type by its full name: the backbone's own, then each
        installed capability's registry (COR-056 points 2 and 6)."""
        return {declared.type: declared for declared in (*BACKBONE_TYPES, *self.types)}

    @property
    def project_types(self) -> frozenset[str]:
        """The bare types the project's places give: a project declares its own
        type by giving it on one of its places (COR-056 point 2)."""
        return frozenset(
            place.type
            for place in self.places
            if place.source == PROJECT_SOURCE and place.type is not None and ":" not in place.type
        )

    @property
    def mode_or_default(self) -> str:
        if isinstance(self.mode, str) and self.mode in FRICTION_MODES:
            return self.mode
        return DEFAULT_FRICTION_MODE

    def exclusion(self, path: str) -> SettingsPath | None:
        """The `exclude` entry that leaves the repository-relative file `path` out, or None.

        The one decision of what is excluded (COR-050 point 7; ADR-057 point 2):
        the first entry, in written order, whose pattern covers `path` as every
        friction path is read (`pattern_matcher`). Discovery records it on each
        file and artefact it finds, so the measures read it from there; the
        checks ask it of any other path — an anchor's match, the surface.
        """
        return next((e for e in self.exclude if pattern_matcher(e.resolved)(path)), None)

    def excluded(self, path: str) -> bool:
        """Whether `exclude` leaves the repository-relative file `path` out (`exclusion`)."""
        return self.exclusion(path) is not None

    def excludes_as(self, other: FrictionSettings) -> bool:
        """Whether `other` leaves out exactly what this does: the same `exclude` patterns,
        so no path reads differently under the two (COR-050 point 7)."""
        return {e.resolved for e in self.exclude} == {e.resolved for e in other.exclude}


def read_friction_settings(
    target_root: Path, tree: RepositoryTree | None = None
) -> FrictionSettings:
    """Read the project's and every installed capability's friction settings.

    Forgiving throughout (COR-048 point 4): an absent file, an unparsable
    file, a key of the wrong shape, or a list entry that is not text is read
    as absent. The schema passes of the configuration file and of package
    metadata refuse those; this reader only has to keep working next to them.
    A capability's places, held folders and surface are the exception: an
    entry it cannot read in the package schema's shape is kept in
    `malformed_places`, `malformed_held` or `malformed_surface` for the
    validation pass (`_capability_places`, `_capability_surface`). The roots and
    each capability's locations are read by `docs_roots`, from the same state.
    With a `tree`, the files are read from that state rather than from disk.
    """
    load = _mapping_loader(target_root, tree)
    config_rel = project_config_path(target_root).relative_to(target_root).as_posix()
    config, unparsed = _yaml_reader(target_root, tree)(config_rel)
    roots = docs_roots.roots_from(config.get(docs_roots.DOCS_KEY))

    friction = _mapping_or_empty(config.get(FRICTION_KEY))
    mode = friction.get("mode")

    def project_paths(key: str) -> tuple[SettingsPath, ...]:
        return tuple(
            SettingsPath(
                value=text,
                resolved=text,
                file=config_rel,
                pointer=f"/{FRICTION_KEY}/{key}/{index}",
                source="project",
            )
            for index, text in _texts(friction.get(key))
        )

    refused_types: list[SettingsPath] = []
    places = list(_project_places(friction.get(PLACES_KEY), config_rel, refused_types))
    surface = list(project_paths("surface"))
    exclude = list(project_paths("exclude"))
    held: list[SettingsPath] = []
    malformed_places: list[MalformedDeclaration] = []
    malformed_surface: list[MalformedDeclaration] = []
    malformed_held: list[MalformedDeclaration] = []
    types: list[DeclaredType] = []
    installed = installed_capability_names(target_root, tree)

    for name in installed:
        package_rel = (CAPABILITIES_DIR / name / "package.yaml").as_posix()
        package = load(package_rel)
        recorded = load(docs_roots.capability_locations_relpath(name).as_posix())
        locations = docs_roots.read_capability_locations(package, recorded, roots)
        found, malformed = _capability_places(name, package, package_rel, locations)
        places.extend(found)
        malformed_places.extend(malformed)
        found, malformed = _capability_places(name, package, package_rel, locations, HELD_KEY)
        held.extend(found)
        malformed_held.extend(malformed)
        found, malformed = _capability_surface(name, package, package_rel)
        surface.extend(found)
        malformed_surface.extend(malformed)
        types.extend(declared_types(name, package))

    return FrictionSettings(
        mode=mode,
        places=tuple(places),
        surface=tuple(surface),
        exclude=tuple(exclude),
        internal_root=roots.internal.as_posix(),
        user_root=roots.user.as_posix(),
        malformed_places=tuple(malformed_places),
        malformed_surface=tuple(malformed_surface),
        held=tuple(held),
        malformed_held=tuple(malformed_held),
        exclude_unreadable=_exclude_unreadable(config, unparsed),
        types=tuple(types),
        installed=tuple(installed),
        refused_types=tuple(refused_types),
    )


def _project_places(
    value: Any, config_rel: str, refused_types: list[SettingsPath]
) -> Iterator[SettingsPath]:
    """The project's `friction.places`, each a bare path or `{path, type}` (COR-056
    point 2), read forgivingly: an entry in neither shape, or with no path, is
    passed over, and the configuration pass refuses it. A lone text counts as one
    entry. A `type` the configuration's schema refuses gives no type (point 3),
    and is kept in `refused_types`, its pointer at the `type`, so a reader warns.
    """
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, Sequence):
        return
    for index, item in enumerate(cast(Sequence[Any], value)):
        type_: str | None = None
        pointer = f"/{FRICTION_KEY}/{PLACES_KEY}/{index}"
        if isinstance(item, Mapping):
            entry = _mapping_or_empty(item)
            path = _text_or_none(entry.get(PATH_KEY))
            type_ = project_place_type(entry.get(TYPE_KEY))
            if path is not None and type_ is None and TYPE_KEY in entry:
                refused_types.append(
                    SettingsPath(
                        value=repr(entry.get(TYPE_KEY)),
                        resolved=path,
                        file=config_rel,
                        pointer=f"{pointer}/{TYPE_KEY}",
                        source=PROJECT_SOURCE,
                    )
                )
        else:
            path = _text_or_none(item)
        if path is None:
            continue
        yield SettingsPath(
            value=path,
            resolved=path,
            file=config_rel,
            pointer=pointer,
            source=PROJECT_SOURCE,
            type=type_,
        )


def refused_type_warnings(settings: FrictionSettings) -> list[str]:
    """A warning for each project place whose `type` the configuration's schema
    refuses: a reader reads it as no type and says so (COR-056 point 3, COR-048
    point 4), and `pkit validate` refuses it."""
    return [
        f"warning: the place {refused.resolved!r} ({refused.file}:{refused.pointer}) names "
        f"the type {refused.value}, which is not a type a place may give, so it gives no "
        f"type (COR-056 point 3). `pkit validate` reports it."
        for refused in settings.refused_types
    ]


def project_place_type(value: Any) -> str | None:
    """The type a project's place names, when the configuration's schema admits the
    value: a bare type of the project's own, or `<component>:<name>` — never one of
    the backbone's, which no place may name (COR-056 point 2). Any other value gives
    no type (point 3)."""
    if not isinstance(value, str):
        return None
    match = _TYPE.fullmatch(value)
    if match is None or match["owner"] == BACKBONE_COMPONENT:
        return None
    return value


def declared_types(name: str, package: Mapping[str, Any]) -> list[DeclaredType]:
    """A component's type registry, `friction.types` (COR-056 point 2), in written order.

    Read forgivingly: a name that is not a type's name, an entry that is not a
    mapping, or a `kind-field` that is not text, or is the methodology's
    container, declares nothing, and the package schema refuses it. A type read
    without the kind field its entry names would type every document of its
    places, the reach the kind field exists to prevent.
    """
    registry = _mapping_or_empty(_mapping_or_empty(package.get(FRICTION_KEY)).get(TYPES_KEY))
    found: list[DeclaredType] = []
    for type_name, raw in registry.items():
        if not _TYPE_NAME.fullmatch(type_name) or not isinstance(raw, Mapping):
            continue
        entry = _mapping_or_empty(raw)
        kind_field = entry.get(KIND_FIELD_KEY)
        if kind_field is not None and _text_or_none(kind_field) in (None, CONTAINER_KEY):
            continue
        found.append(
            DeclaredType(
                owner=name,
                name=type_name,
                description=_text_or_none(entry.get(TYPE_DESCRIPTION_KEY)),
                kind_field=_text_or_none(kind_field),
                project_places=entry.get(PROJECT_PLACES_KEY) is True,
            )
        )
    return found


def _exclude_unreadable(config: Mapping[str, Any], unparsed: str | None) -> str | None:
    """Why the configuration's `friction.exclude` cannot be read in full, else `None`.

    An absent file, key or list excludes nothing, which is a reading; a file
    that does not parse, a `friction` or `exclude` of the wrong shape, or an
    entry that is no path is not one — the forgiving reader would see nothing
    excluded where the state excluded something.
    """
    if unparsed is not None:
        return f"the configuration file {unparsed}"
    friction = config.get(FRICTION_KEY)
    if friction is None:
        return None
    if not isinstance(friction, Mapping):
        return f"`{FRICTION_KEY}` is {_shape(friction)}, not a mapping"
    exclude = cast(Mapping[str, Any], friction).get("exclude")
    if exclude is None or isinstance(exclude, str):
        return None
    if not isinstance(exclude, list):
        return f"`{FRICTION_KEY}.exclude` is {_shape(exclude)}, not a list"
    if any(not (isinstance(item, str) and item.strip()) for item in cast(list[Any], exclude)):
        return f"`{FRICTION_KEY}.exclude` holds an entry that is not a path"
    return None


def installed_packages_at(
    target_root: Path, tree: RepositoryTree
) -> list[tuple[str, Path, dict[str, Any]]]:
    """`(name, component_dir, package)` for each capability and adapter the manifest of the
    state `tree` holds installs, in manifest order, with the package metadata that state
    holds — read forgivingly, as `installed_capability_names` reads the manifest. A
    component whose package file the state lacks is left out, as
    `package_validate.installed_package_files` leaves it out of the working tree."""
    manifest = _mapping_loader(target_root, tree)(BACKBONE_MANIFEST.as_posix())
    components: Any = manifest.get("components")
    if not isinstance(components, list):
        return []
    areas = {"capability": "capabilities", "adapter": "adapters"}
    found: list[tuple[str, Path, dict[str, Any]]] = []
    for entry in _mappings(cast(list[Any], components)):
        name, area = entry.get("name"), areas.get(str(entry.get("kind")))
        if not isinstance(name, str) or area is None:
            continue
        component = Path(".pkit") / area / name
        package_file = (component / command_runner.PACKAGE_FILE).as_posix()
        raw = tree.read_bytes([package_file]).get(package_file)
        if raw is None:
            continue
        try:
            package, _problem = _parse_mapping(raw.decode("utf-8"))
        except UnicodeDecodeError:
            package = {}
        found.append((name, target_root / component, package))
    return found


def installed_capability_names(target_root: Path, tree: RepositoryTree | None = None) -> list[str]:
    """Installed capabilities by name, sorted, from the backbone manifest.

    With a `tree`, the manifest that state holds is read, forgivingly: an
    entry that is not a mapping with a text name is skipped.
    """
    if tree is not None:
        manifest = _mapping_loader(target_root, tree)(BACKBONE_MANIFEST.as_posix())
        components: Any = manifest.get("components")
        if not isinstance(components, list):
            return []
        names: list[str] = []
        for entry in _mappings(components):
            name = entry.get("name")
            if entry.get("kind") == "capability" and isinstance(name, str):
                names.append(name)
        return sorted(names)
    backbone = read_backbone_manifest(target_root)
    if backbone is None:
        return []
    return sorted(c.name for c in backbone.components if c.kind == "capability")


@dataclass(frozen=True)
class _Unresolved:
    """Why a capability place cannot be resolved: a clause the finding quotes."""

    reason: str


def _capability_places(
    name: str,
    package: Mapping[str, Any],
    package_file: str,
    locations: Mapping[str, docs_roots.Location | docs_roots.UnreadableLocation],
    key: str = PLACES_KEY,
) -> tuple[list[SettingsPath], list[MalformedDeclaration]]:
    """A capability's `friction.places` — or, with `key`, its `friction.held` —
    read in the package schema's shape (COR-050 point 1).

    A place is an object `{path, location?, type?, description?}`, and a held
    folder `{location, path, description?}`. With `location`, `path` lies
    inside that entry of the capability's `docs.locations`, where `locations`
    — the one reading, `docs_roots.read_capability_locations` — puts it: its
    recorded location, else its declared `{path, root?}` under the root it
    names (COR-049 points 4 and 5). Without one, `path` is repository-relative.
    A held folder lies within one of the capability's locations, so it names
    one, and its `path` is a folder inside it (`_resolve_capability_place`).
    A place may also name a type of the capability's own registry, `type`,
    kept in full as `<capability>:<name>` (COR-056 point 2). A name the
    package schema refuses names no type.
    Only that shape is read: an entry written as plain text or in any other
    shape, or naming a location the capability does not declare or that the
    reading cannot place, gives the walk nothing it could follow, so it is
    returned as malformed — never dropped — for the validation pass to report
    (COR-050 point 7). Both lists keep the written order.
    """
    source = f"capability:{name}"
    pointer = f"/{FRICTION_KEY}/{key}"
    noun = _ENTRY_NOUN[key]
    raw = _mapping_or_empty(package.get(FRICTION_KEY)).get(key)
    if raw is None:
        return [], []
    if not isinstance(raw, list):
        reason = f"`{FRICTION_KEY}.{key}` is {_shape(raw)}, not a list of {noun}s"
        whole = MalformedDeclaration(
            file=package_file, pointer=pointer, source=source, reason=reason
        )
        return [], [whole]
    places: list[SettingsPath] = []
    malformed: list[MalformedDeclaration] = []
    location_roots = docs_roots.declared_location_roots(package)
    for index, entry in enumerate(raw):
        entry_pointer = f"{pointer}/{index}"
        resolved = _resolve_capability_place(entry, locations, key)
        if isinstance(resolved, _Unresolved):
            malformed.append(
                MalformedDeclaration(
                    file=package_file, pointer=entry_pointer, source=source, reason=resolved.reason
                )
            )
            continue
        path, pattern, location = resolved
        written_type = _mapping_or_empty(entry).get(TYPE_KEY) if key == PLACES_KEY else None
        places.append(
            SettingsPath(
                value=path,
                resolved=pattern,
                file=package_file,
                pointer=entry_pointer,
                source=source,
                location=(
                    PlaceLocation(
                        name=location[0], path=location[1], root=location_roots.get(location[0])
                    )
                    if location is not None
                    else None
                ),
                type=(
                    f"{name}:{written_type}"
                    if isinstance(written_type, str) and _TYPE_NAME.fullmatch(written_type)
                    else None
                ),
            )
        )
    return places, malformed


def _resolve_capability_place(
    entry: Any,
    locations: Mapping[str, docs_roots.Location | docs_roots.UnreadableLocation],
    key: str = PLACES_KEY,
) -> tuple[str, str, tuple[str, str] | None] | _Unresolved:
    """`(path, pattern, location)` for an entry of the `key` list — a place, or a
    held folder — in the schema's shape, else why it is not.

    `path` is the entry's own, `pattern` the repository-relative form the walk
    follows, and `location` the `(name, where it lies)` of the location it
    names, or `None`. A held folder lies within one of the capability's
    locations (COR-050 point 1): it names one, and its `path` is a folder there
    — no glob, nothing absolute, no `..` segment. Whether the pattern stays
    inside the repository is left to the validation pass, which follows links
    on disk; here only the shape is judged.
    """
    noun = _ENTRY_NOUN[key]
    if not isinstance(entry, Mapping):
        return _Unresolved(f"the {noun} is {_shape(entry)}, not an object `{_ENTRY_SHAPE[key]}`")
    written = entry.get(PATH_KEY)
    path = _text_or_none(written)
    if path is None:
        if written is None:
            return _Unresolved(f"the {noun} has no `path`")
        return _Unresolved(f"the {noun}'s `path` is {_shape(written)}, not a path or glob")
    if key == HELD_KEY:
        outside = _held_path_problem(path)
        if outside is not None:
            return _Unresolved(f"the held folder's `path` {path!r} {outside}")
        if LOCATION_KEY not in entry:
            return _Unresolved(
                "the held folder names no `location`: a held folder lies within one of the "
                "component's `docs.locations`"
            )
    if LOCATION_KEY not in entry:
        return path, _join_posix(path), None
    location = entry.get(LOCATION_KEY)
    if not isinstance(location, str):
        return _Unresolved(
            f"the {noun}'s `location` is {_shape(location)}, not a name from `docs.locations`"
        )
    where = locations.get(location)
    if where is None:
        declared = f" (declared: {sorted(locations)})" if locations else ""
        return _Unresolved(
            f"the {noun} names location {location!r}, which `docs.locations` does not "
            f"declare{declared}"
        )
    if isinstance(where, docs_roots.UnreadableLocation):
        return _Unresolved(
            f"the {noun} names location {location!r}, whose `docs.locations` entry {where.reason}"
        )
    folder = where.path.as_posix()
    pattern = _join_posix(folder, path)
    if key == HELD_KEY:  # a folder, with no `..` of its own: its normal form is the folder
        pattern = os.path.normpath(pattern).replace(os.sep, "/")
    return path, pattern, (location, folder)


def _held_path_problem(path: str) -> str | None:
    """Why a held folder's `path` is not a folder within its location, or `None`."""
    if any(ch in _GLOB_CHARS for ch in path):
        return "is a glob, not a folder"
    parts = PurePosixPath(path).parts
    if PurePosixPath(path).is_absolute() or ".." in parts:
        return "leaves its location (absolute, or with a `..` segment)"
    return None


def _capability_surface(
    name: str, package: Mapping[str, Any], package_file: str
) -> tuple[list[SettingsPath], list[MalformedDeclaration]]:
    """A capability's `friction.surface`, read in the package schema's shape (COR-050 point 8).

    The surface is a list of repository-relative paths or globs, each taken as
    written — never under a documentation location. Anything else — a surface
    that is not a list, an entry that is not a path — declares nothing the
    uncovered-surface measure could read, so it is returned as malformed,
    never dropped, as a place is (COR-050 point 7). Both lists keep the
    written order.
    """
    source = f"capability:{name}"
    pointer = f"/{FRICTION_KEY}/surface"
    raw = _mapping_or_empty(package.get(FRICTION_KEY)).get("surface")
    if raw is None:
        return [], []
    if not isinstance(raw, list):
        reason = f"`friction.surface` is {_shape(raw)}, not a list of paths"
        whole = MalformedDeclaration(
            file=package_file, pointer=pointer, source=source, reason=reason
        )
        return [], [whole]
    surface: list[SettingsPath] = []
    malformed: list[MalformedDeclaration] = []
    for index, entry in enumerate(raw):
        entry_pointer = f"{pointer}/{index}"
        text = _text_or_none(entry)
        if text is None:
            reason = f"the surface entry is {_shape(entry)}, not a path or glob"
            malformed.append(
                MalformedDeclaration(
                    file=package_file, pointer=entry_pointer, source=source, reason=reason
                )
            )
            continue
        surface.append(
            SettingsPath(
                value=text, resolved=text, file=package_file, pointer=entry_pointer, source=source
            )
        )
    return surface, malformed


def _shape(value: Any) -> str:
    """How a parsed YAML value reads, for a finding: `text ('x')`, `a mapping`, `a list`, ..."""
    if value is None:
        return "empty"
    if isinstance(value, str):
        return f"text ({value!r})"
    if isinstance(value, Mapping):
        return "a mapping"
    if isinstance(value, list):
        return "a list"
    return f"{type(value).__name__} ({value!r})"


def _join_posix(*segments: str) -> str:
    """Join path segments, dropping empty ones, without normalising `..` away.

    An absolute segment is returned as written, so the outside-repository
    check sees it rather than a silently relativised form.
    """
    for segment in segments:
        if segment.startswith("/"):
            return segment
    parts = [s.strip("/") for s in segments if s and s.strip("/")]
    return "/".join(parts) if parts else "."


def _mapping_loader(
    target_root: Path, tree: RepositoryTree | None
) -> Callable[[str], dict[str, Any]]:
    """A reader of repository-relative YAML files as mappings: from disk, or from `tree`."""
    read = _yaml_reader(target_root, tree)
    return lambda rel: read(rel)[0]


def _yaml_reader(
    target_root: Path, tree: RepositoryTree | None
) -> Callable[[str], tuple[dict[str, Any], str | None]]:
    """A reader of repository-relative YAML files as mappings, with why one does not
    read: `({}, None)` for an absent file, `({}, <why>)` for one that is there but is
    no YAML mapping. From disk, or from `tree`."""
    if tree is None:
        return lambda rel: _load_mapping(target_root / rel)

    def load(rel: str) -> tuple[dict[str, Any], str | None]:
        raw = tree.read_bytes([rel]).get(rel)
        if raw is None:
            return {}, None
        try:
            return _parse_mapping(raw.decode("utf-8"))
        except UnicodeDecodeError:
            return {}, "is not UTF-8 text"

    return load


def _load_mapping(path: Path) -> tuple[dict[str, Any], str | None]:
    """A YAML file as a mapping with text keys, and why it does not read (`_yaml_reader`)."""
    if not path.is_file():
        return {}, None
    try:
        return _parse_mapping(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return {}, f"cannot be read ({exc.strerror or exc})"
    except UnicodeDecodeError:
        return {}, "is not UTF-8 text"


def _parse_mapping(text: str) -> tuple[dict[str, Any], str | None]:
    """YAML text as a mapping with text keys, and why it is none: it does not parse,
    or it is no mapping. Empty text is an empty mapping."""
    try:
        data = _yaml.load(text)
    except YAMLError:
        return {}, "does not parse as YAML"
    if data is None:
        return {}, None
    if not isinstance(data, Mapping):
        return {}, f"is {_shape(data)}, not a mapping"
    return {str(k): v for k, v in cast(Mapping[Any, Any], data).items()}, None


def _mappings(items: list[Any]) -> Iterator[Mapping[str, Any]]:
    """The entries of a parsed YAML list that are mappings, with text keys."""
    for item in items:
        if isinstance(item, Mapping):
            yield _mapping_or_empty(item)


def _mapping_or_empty(value: Any) -> Mapping[str, Any]:
    return {str(k): v for k, v in value.items()} if isinstance(value, Mapping) else {}


def _text_or_none(value: Any) -> str | None:
    """A non-empty text, stripped; `None` for anything else."""
    return value.strip() if isinstance(value, str) and value.strip() else None


def _texts(value: Any) -> Iterator[tuple[int, str]]:
    """(index, text) for each non-empty text in a list; a lone text counts as one entry."""
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, Sequence):
        return
    for index, item in enumerate(value):
        if isinstance(item, str) and item.strip():
            yield index, item.strip()


# --- places -------------------------------------------------------------


@dataclass(frozen=True)
class Place:
    """One declared place: a repository-relative path or glob, and its declaration."""

    pattern: str  # repository-relative, as discovery walks it
    declaration: SettingsPath

    @property
    def source(self) -> str:
        return self.declaration.source


def declared_places(settings: FrictionSettings) -> tuple[Place, ...]:
    """The places in walk order: the project's in declaration order, then each capability's."""
    return tuple(Place(pattern=p.resolved, declaration=p) for p in settings.places)


def capability_name(source: str) -> str:
    """The component a declaration's `source` names: `capability:<name>` gives
    `<name>`; any other source is returned as it is."""
    prefix = "capability:"
    return source[len(prefix) :] if source.startswith(prefix) else source


@dataclass(frozen=True)
class Skip:
    """Why a declaration holds nothing: a `reason` a reader can tell apart
    (`SKIP_MALFORMED`, `SKIP_OUTSIDE`, `SKIP_OVERLAP`) and its `detail`."""

    reason: str
    detail: str


@dataclass(frozen=True)
class HeldFolder:
    """A folder of held documents a capability declares (COR-050 point 1).

    `place` carries it as a place is carried — its resolved pattern and its
    declaration — because it is written, resolved and matched as one; it is not
    a place, and no place walks what it holds. `skipped` is `None` for a folder
    that holds its files, else why it holds nothing: it leaves the repository
    (`SKIP_OUTSIDE`), or it overlaps what another declaration reaches
    (`SKIP_OVERLAP`, `held_folders`). A folder that holds nothing leaves its
    files to the places matching them, and its declaration carries the finding.
    """

    place: Place
    skipped: Skip | None = None

    @property
    def pattern(self) -> str:
        """The repository-relative folder, as the walk matches it."""
        return self.place.pattern

    @property
    def declaration(self) -> SettingsPath:
        return self.place.declaration

    @property
    def component(self) -> str:
        """The capability that declares it."""
        return capability_name(self.place.source)


def held_folders(
    target_root: Path,
    settings: FrictionSettings,
    rule_sets: Sequence[RuleSetPlace] | None = None,
) -> tuple[HeldFolder, ...]:
    """The folders of held documents, each capability's by name in written order,
    each with why it holds nothing, if it does (COR-050 point 1).

    A held folder is bounded, so that every held file has one holder and no
    declaration empties what another declares. One that leaves the repository —
    through its location or a link — holds nothing (`SKIP_OUTSIDE`), and so
    does one that equals or encloses a documentation root or another
    declaration's place, or shares files with its own component's place,
    another held folder or a rule-set folder, whose files the location rule
    reads as rules (`SKIP_OVERLAP`; COR-051 point 2). Lying inside another
    declaration's place — a root's, say — is what a held folder is for: that
    place leaves its files out. Judged on the declarations, never on which files
    exist, so a folder empty today is judged as it will be read. `rule_sets` are
    the rule-set places, when the caller has them (`rule_set_places`).
    """
    if not settings.held:
        return ()
    if rule_sets is None:
        rule_sets = rule_set_places(target_root, settings)
    inside = [h for h in settings.held if is_inside_repository(target_root, h.resolved)]
    folders: list[HeldFolder] = []
    for held in settings.held:
        place = Place(pattern=held.resolved, declaration=held)
        if held not in inside:
            detail = (
                f"{held.resolved!r} leaves the repository — its location lies outside it, or "
                f"it resolves outside it through a link — so nothing under it is held"
            )
            folders.append(HeldFolder(place, Skip(SKIP_OUTSIDE, detail)))
            continue
        clauses = _held_overlaps(place, settings, rule_sets, [h for h in inside if h != held])
        skipped = Skip(SKIP_OVERLAP, "; ".join(clauses)) if clauses else None
        folders.append(HeldFolder(place, skipped))
    return tuple(folders)


def _held_overlaps(
    held: Place,
    settings: FrictionSettings,
    rule_sets: Sequence[RuleSetPlace],
    others: Sequence[SettingsPath],
) -> list[str]:
    """How a held folder inside the repository oversteps its bounds, one clause
    each (`held_folders`); none when it keeps them.

    The roots are judged as the document's `encloses` judges them (`_encloses`).
    Another declaration's place is refused only when it lies within the folder,
    which would empty it (`_lies_within`); its own component's place, another
    held folder and a rule-set folder whenever they could share a file
    (`_could_share`).
    """
    folder = _normal(held.pattern)
    clauses = [
        f"equals or encloses the {audience} documentation root {root!r}"
        for audience, root in settings.roots.items()
        if _encloses(held, root)
    ]
    rule_set_patterns = {_normal(r.pattern) for r in rule_sets}
    for place in declared_places(settings):
        shown = _normal(place.pattern)
        if shown in rule_set_patterns:
            continue  # a rule-set folder, judged as one below
        if place.source == held.source:
            if _could_share(place.pattern, folder):
                clauses.append(f"overlaps its own place {shown!r}")
        elif _lies_within(place.pattern, folder):
            clauses.append(f"equals or encloses {_declarer(place.source)}'s place {shown!r}")
    clauses += [
        f"overlaps the rule-set folder {_normal(r.pattern)!r}, whose files are rules "
        f"(COR-051 point 2)"
        for r in rule_sets
        if _could_share(r.pattern, folder)
    ]
    clauses += [
        f"overlaps {_declarer(other.source)}'s held folder {other.resolved!r}"
        if other.source != held.source
        else f"overlaps its own held folder {other.resolved!r}"
        for other in others
        if _could_share(other.resolved, folder)
    ]
    return clauses


def _normal(pattern: str) -> str:
    """A declared path or glob in its normal form, with `/` separators."""
    return os.path.normpath(pattern).replace(os.sep, "/")


def _declarer(source: str) -> str:
    """Who a declaration's `source` is, for a message: `the project`, or the component."""
    return "the project" if source == "project" else capability_name(source)


def _lies_within(pattern: str, folder: str) -> bool:
    """Whether every file `pattern` could match lies at or beneath the literal `folder`."""
    normalised = _normal(pattern)
    return folder == "." or normalised == folder or normalised.startswith(folder + "/")


def _could_share(pattern: str, folder: str) -> bool:
    """Whether `pattern` — a path or a glob, read as a place reads it — could match
    a file at or beneath the literal `folder`.

    A path without glob characters shares files with the folder when one of the
    two lies within the other. A glob is walked segment by segment against the
    folder's segments — `**` spanning any number of them — and could match
    beneath it when it has segments left once the folder's are consumed.
    """
    normalised = _normal(pattern)
    if "." in (normalised, folder):
        return True
    if not any(ch in _GLOB_CHARS for ch in normalised):
        return _lies_within(normalised, folder) or folder.startswith(normalised + "/")
    segments = normalised.split("/")

    def spanned(states: set[int]) -> set[int]:
        """`states` with every state a `**` may skip past, matching no segment."""
        pending = list(states)
        while pending:
            index = pending.pop()
            if index < len(segments) and segments[index] == "**" and index + 1 not in states:
                states.add(index + 1)
                pending.append(index + 1)
        return states

    states = spanned({0})
    for part in folder.split("/"):
        following: set[int] = set()
        for index in states:
            if index >= len(segments):
                continue
            segment = segments[index]
            if segment == "**":
                following.add(index)
            elif re.fullmatch(_segment_regex(segment), part):
                following.add(index + 1)
        states = spanned(following)
        if not states:
            return False
    return any(index < len(segments) for index in states)


@dataclass(frozen=True)
class SyncedMatch:
    """A file a declared place matches that is a synced copy, so it is not walked.

    A place is never a synced tree (COR-050 point 14): a tree the methodology's
    sync writes into the project, where every refresh would otherwise show up
    as friction in the project's own history. The validation pass reports it at
    the place's declaration.
    """

    place: Place
    path: str  # repository-relative


@dataclass(frozen=True)
class HeldFile:
    """A Markdown file a component holds, which is not an artefact (COR-050 point 1).

    No place walks it — a root, another component's or the project's, its own
    or a rule-set folder — so it is never an artefact, and neither measure
    counts it. `folder` is the held folder holding it — the one, since held
    folders never share a file (`held_folders`) — whose declaration names its
    owner. `places` are the places that match it and so left it out, in walk
    order. It is read for its front matter alone: `front_matter` as written
    when that is a mapping, `unreadable` why the file or its front matter could
    not be read, and `blocks` the JSON Pointer, in the front matter, of every
    friction block anywhere in it — the document's own, an entry's, a rule's
    under `rules`, or deeper — which validation refuses (COR-050 point 12).
    `excluded_by` is the `friction.exclude` entry it lies under, else `None` —
    the decision a walked file carries: an excluded held document is still
    held and read, and its owner leaves it out as the measures leave out an
    excluded artefact (point 7).
    """

    path: str
    folder: HeldFolder
    places: tuple[Place, ...]
    front_matter: Mapping[str, Any] | None
    unreadable: str | None
    blocks: tuple[str, ...]
    excluded_by: SettingsPath | None = None

    @property
    def owner(self) -> str:
        """The declaration's `source`: `capability:<name>`."""
        return self.folder.place.source

    @property
    def component(self) -> str:
        """The capability holding it."""
        return self.folder.component


def held_message(held: HeldFile) -> str:
    """What a command that reads artefacts says of a held document it was asked
    about: whose it is, where that is declared, and that it is no artefact."""
    declaration = held.folder.declaration
    return (
        f"{held.path} is held by {held.component} — in its held folder {declaration.value!r}, "
        f"{declaration.file}:{declaration.pointer} — and is not an artefact: a held document "
        f"carries no friction block (COR-050 point 1)."
    )


def synced_copy_test(target_root: Path) -> Callable[[str], bool] | None:
    """Whether a repository-relative path arrives here as a synced copy, or None.

    The tree's own predicate, `is_synced_copy` of `.pkit/lifecycle/ownership.py`,
    loaded through the backbone's one loader of it: keyed on the capability's
    recorded origin (COR-031) and on whether this repository is the one the
    methodology is authored in, never on the path — so the same `.pkit/` README
    is a place in that repository and a synced copy everywhere else (living-docs
    DEC-001 point 1). It reads the working tree's install state. None when the
    tree carries no ownership module, which the validation pass reports.
    """
    ownership = lifecycle_ownership.load_ownership(target_root)
    if ownership is None:
        return None
    return functools.partial(ownership.is_synced_copy, target_root)


def is_inside_repository(target_root: Path, pattern: str) -> bool:
    """Whether a declared path or glob stays inside the repository (COR-050 point 14).

    Judged on the text first — an absolute path, or one whose normalised form
    climbs above the root, is outside — and then, for the literal prefix
    before any glob character, on where it resolves after following links
    (COR-049 point 1). The resolution is of the nearest existing ancestor:
    `docs/linked/sub/**` with `docs/linked` a link out of the repository is
    outside even while `sub` does not exist yet.
    """
    if not _textually_inside(pattern):
        return False
    prefix = _literal_prefix(os.path.normpath(pattern))
    candidate = target_root / prefix if prefix else target_root
    return _resolves_inside(target_root, candidate)


def _textually_inside(pattern: str) -> bool:
    """The text half of `is_inside_repository`: not absolute, not climbing above the root."""
    if not pattern or PurePosixPath(pattern).is_absolute() or os.path.isabs(pattern):
        return False
    normalised = os.path.normpath(pattern)
    return not (
        normalised == ".." or normalised.startswith("../") or normalised.startswith(".." + os.sep)
    )


def _resolves_inside(target_root: Path, candidate: Path) -> bool:
    """Whether `candidate` lies under the root once links are followed.

    A non-strict `resolve` follows links through the components that exist
    and keeps the rest as written, which is exactly the nearest-existing-
    ancestor judgment a not-yet-created path needs.
    """
    try:
        candidate.resolve().relative_to(target_root.resolve())
    except (OSError, RuntimeError, ValueError):
        return False
    return True


def _literal_prefix(pattern: str) -> str:
    """The leading path segments of `pattern` that carry no glob character."""
    kept: list[str] = []
    for segment in PurePosixPath(pattern).parts:
        if any(ch in _GLOB_CHARS for ch in segment):
            break
        kept.append(segment)
    return "/".join(kept)


def files_in_place(target_root: Path, place: Place, tree: WorkingTree | None = None) -> list[Path]:
    """The Markdown files a place matches in the working tree, sorted by repository-relative path.

    `listed_files_in_place` over the working tree's one listing (`tree`, by
    default `working_tree`), so every reader of the working tree finds the
    same files: the files git sees. A link is a file of the listing but is
    never read as a document, so it is left out; nothing beneath a link to a
    folder is listed at all. A pattern outside the repository matches nothing
    here; the configuration pass reports it.
    """
    listing = tree if tree is not None else working_tree(target_root)
    return [
        target_root / rel
        for rel in listed_files_in_place(place, listing.files())
        if not (target_root / rel).is_symlink()
    ]


def _under_skipped(rel: Path | PurePosixPath) -> bool:
    return bool(rel.parts) and rel.parts[0] in _SKIPPED_TOP_LEVEL


def listed_files_in_place(place: Place, files: Sequence[str]) -> list[str]:
    """The Markdown files of a listing — a tree's files — that a place matches, sorted.

    The one reading of a place, whichever state the listing is of: a glob
    matches files, a glob ending in `**` means every Markdown file beneath, a
    directory means every Markdown file beneath it, a file means that file,
    and only Markdown files are documents (ADR-056 point 2) — plain YAML in a
    place is left alone. A pattern outside the repository matches nothing.
    Globs follow pathlib's reading on Python 3.13 (`compile_glob`) on every
    interpreter.
    """
    if not _textually_inside(place.pattern):
        return []
    pattern = os.path.normpath(place.pattern).replace(os.sep, "/")
    documents = [
        f
        for f in files
        if PurePosixPath(f).suffix == DOCUMENT_SUFFIX and not _under_skipped(PurePosixPath(f))
    ]
    if pattern == ".":
        matched = documents
    elif any(ch in _GLOB_CHARS for ch in pattern):
        if PurePosixPath(pattern).name == "**":
            pattern = f"{pattern}/*{DOCUMENT_SUFFIX}"
        regex = compile_glob(pattern)
        matched = [f for f in documents if regex.fullmatch(f)]
    else:
        prefix = pattern + "/"
        matched = [f for f in documents if f == pattern or f.startswith(prefix)]
    return sorted(matched)


def pattern_matches(pattern: str, path: str) -> bool:
    """Whether a settings or anchor `pattern` covers the repository-relative file `path`."""
    return pattern_matcher(pattern)(path)


def pattern_matches_any(pattern: str, files: Iterable[str]) -> bool:
    """Whether a settings `pattern` covers at least one file of a listing.

    The reading the checks apply (`pattern_matcher`), so a pattern said to
    match something covers a file the checks can see — not merely a folder, or
    a file git ignores. `.`, the repository itself, always does.
    """
    if os.path.normpath(pattern) == ".":
        return True
    match = pattern_matcher(pattern)
    return any(match(path) for path in files)


@functools.lru_cache(maxsize=1024)
def pattern_matcher(pattern: str) -> Callable[[str], bool]:
    """A predicate over repository-relative file paths for a settings or anchor `pattern`.

    One reading for every path the friction functionality names (COR-050
    points 2 and 14): a glob matches files as `compile_glob` reads it, `**`
    spanning folders; a path without glob characters names a file, or a
    directory and so every file beneath it; `.` is the whole repository.
    """
    normalised = os.path.normpath(pattern).replace(os.sep, "/")
    if normalised == ".":
        return lambda _path: True
    if any(ch in _GLOB_CHARS for ch in normalised):
        regex = compile_glob(normalised)
        return lambda path: regex.fullmatch(path) is not None
    prefix = normalised + "/"
    return lambda path: path == normalised or path.startswith(prefix)


@functools.lru_cache(maxsize=1024)
def compile_glob(pattern: str) -> re.Pattern[str]:
    """A repository-relative glob as a regular expression over POSIX file paths.

    pathlib's reading (Python 3.13): `**` as a whole segment spans any number
    of folders, none included; `*` matches within one segment, and so does a
    `**` mixed into a segment; `?` is one character; `[...]` a class, `[!...]`
    its negation. Dot-files are not special.
    """
    segments = pattern.split("/")
    parts: list[str] = []
    for index, segment in enumerate(segments):
        last = index == len(segments) - 1
        if segment == "**":
            parts.append(".*" if last else "(?:[^/]+/)*")
            continue
        parts.append(_segment_regex(segment))
        if not last:
            parts.append("/")
    return re.compile("".join(parts), re.DOTALL)


def _segment_regex(segment: str) -> str:
    """One path segment of a glob as a regular expression that never crosses a `/`."""
    out: list[str] = []
    index = 0
    while index < len(segment):
        char = segment[index]
        if char == "*":
            while index < len(segment) and segment[index] == "*":
                index += 1
            out.append("[^/]*")
            continue
        if char == "?":
            out.append("[^/]")
        elif char == "[":
            end = index + 1
            if end < len(segment) and segment[end] == "!":
                end += 1
            if end < len(segment) and segment[end] == "]":
                end += 1
            while end < len(segment) and segment[end] != "]":
                end += 1
            if end >= len(segment):
                out.append(re.escape(char))  # no closing bracket: a literal `[`
            else:
                body = segment[index + 1 : end]
                negated = body.startswith("!")
                if negated:
                    body = body[1:]
                body = re.sub(r"([\\&~|\[\]^])", r"\\\1", body)
                out.append(f"[^/{body}]" if negated else f"[{body}]")
                index = end + 1
                continue
        else:
            out.append(re.escape(char))
        index += 1
    return "".join(out)


# --- rule-set places ----------------------------------------------------


@dataclass(frozen=True)
class RuleSetPlace:
    """A place declared to hold rule sets, and who owns the rule sets in it.

    `component` names the component a *method* rule set ships with — the
    backbone or a capability — and is `None` for a *project* rule set, which
    the project owns and cites bare (COR-051 point 6).
    """

    place: Place
    component: str | None

    @property
    def pattern(self) -> str:
        return self.place.pattern


def rule_set_places(
    target_root: Path, settings: FrictionSettings, tree: RepositoryTree | None = None
) -> tuple[RuleSetPlace, ...]:
    """The places declared to hold rule sets, in claim order (the location rule).

    Method rule sets first: the backbone's `.pkit/rule-sets/`, then each
    installed capability's `.pkit/capabilities/<name>/rule-sets/` by name.
    Then project rule sets: `<internal root>/rule-sets/`, and every declared
    place whose path has a `rule-sets` segment. A folder the location rule
    names is a place only while it exists inside the repository
    (`_folder_test`), so a project without rule sets declares nothing; a
    declared place is taken as written. A folder the rule names has no
    declaring file, so its declaration names the folder itself.

    With a `tree` of another state than the working tree — a commit — both are
    that state's: the folders it holds and the capabilities its manifest
    installs, so a folder a commit adds, or a capability it installs, holds rule
    sets there whichever checkout reads it. The working tree's are on disk, read
    as they are without a tree.
    """
    state = None if isinstance(tree, WorkingTree) else tree
    places: list[RuleSetPlace] = []
    exists = _folder_test(target_root, state)

    def folder(rel: str, component: str | None, source: str) -> None:
        if exists(rel):
            declaration = SettingsPath(value=rel, resolved=rel, file=rel, pointer="", source=source)
            places.append(RuleSetPlace(Place(pattern=rel, declaration=declaration), component))

    folder(BACKBONE_RULE_SETS_DIR.as_posix(), BACKBONE_COMPONENT, BACKBONE_COMPONENT)
    for name in installed_capability_names(target_root, state):
        rel = (CAPABILITIES_DIR / name / RULE_SETS_SEGMENT).as_posix()
        folder(rel, name, f"capability:{name}")
    folder(_join_posix(settings.internal_root, RULE_SETS_SEGMENT), None, "project")
    for place in declared_places(settings):
        if RULE_SETS_SEGMENT in PurePosixPath(place.pattern).parts:
            places.append(RuleSetPlace(place, None))

    unique: dict[str, RuleSetPlace] = {}
    for rule_set_place in places:
        unique.setdefault(os.path.normpath(rule_set_place.pattern), rule_set_place)
    return tuple(unique.values())


def _folder_test(target_root: Path, tree: RepositoryTree | None) -> Callable[[str], bool]:
    """Whether a folder the location rule names exists inside the repository.

    Without a `tree`, on disk, where it leads through a link judged as
    `is_inside_repository` judges it — no repository demanded, so a project
    without rule sets stays dormant outside one. With one, in that state: a
    file of it lies beneath the folder, whose path stays inside the repository
    as written — git lists no file through a link, so a file listed beneath it
    lies inside. A folder holding no file is no folder of a commit, nor of a
    clean checkout of it.
    """
    if tree is None:
        return lambda rel: is_inside_repository(target_root, rel) and (target_root / rel).is_dir()
    files = tree.files()

    def holds(rel: str) -> bool:
        if not _textually_inside(rel):
            return False
        folder = os.path.normpath(rel).replace(os.sep, "/")
        if folder == ".":
            return bool(files)
        return any(path.startswith(f"{folder}/") for path in files)

    return holds


def rule_set_files(
    target_root: Path, places: Sequence[RuleSetPlace], tree: RepositoryTree | None = None
) -> dict[str, RuleSetPlace]:
    """Every rule-set file the places claim, with the place that claimed it.

    A Markdown file a rule-set place matches is a rule-set file, whatever it
    holds — except the folder's signpost, `README.md`. A file two places match
    is claimed by the first, so a method folder always wins over a project
    place that happens to reach into it. Keyed by repository-relative path, in
    a tree's listing (`listed_files_in_place`): the state `tree` holds, else the
    working tree's one listing, like every other artefact. A link is claimed
    as a file of the listing, and never read as a document. The one claim the
    walk (`discover_artefacts`) and the rule-set reader both make, so they find
    the same rule-set files at one state.
    """
    claimed: dict[str, RuleSetPlace] = {}
    if not places:
        return claimed
    files = (tree if tree is not None else working_tree(target_root)).files()
    for rule_set_place in places:
        for rel in listed_files_in_place(rule_set_place.place, files):
            if PurePosixPath(rel).name != RULE_SETS_SIGNPOST:
                claimed.setdefault(rel, rule_set_place)
    return claimed


def is_method_rule_set_path(rel: str) -> bool:
    """Whether `rel` lies in or beneath a folder the location rule names for method
    rule sets: the backbone's `.pkit/rule-sets/`, or `.pkit/capabilities/<name>/rule-sets/`
    of any capability, installed or not (COR-051 point 6)."""
    parts = PurePosixPath(rel).parts
    if parts[:2] == BACKBONE_RULE_SETS_DIR.parts:
        return True
    return len(parts) > 3 and parts[:2] == CAPABILITIES_DIR.parts and parts[3] == RULE_SETS_SEGMENT


def rule_set_folder_left_behind(
    target_root: Path, settings: FrictionSettings, new_internal_root: str
) -> str | None:
    """The project's default rule-set folder a change of the internal root would
    leave behind, or None (COR-051 point 6).

    The folder is `rule-sets/` under the internal root `settings` read, the
    root before the change. It is left behind when a rule-set file in or
    beneath it, one the location rule claims now, would be claimed by no place
    with the internal root swapped for `new_internal_root` and every other
    place as it stands. A change of root then declares it as a place, so the
    location rule's declared places find its sets where they are. Nothing is
    left behind when the root does not change, when the folder holds no
    rule-set file, or when every file of it stays claimed: by a place the
    project declares, or by the new root's folder, beneath which it lies.
    Read in the working tree's one listing.
    """
    old = docs_roots.normalise(settings.internal_root)
    new = docs_roots.normalise(new_internal_root)
    if old == new:
        return None
    folder = (PurePosixPath(old.as_posix()) / RULE_SETS_SEGMENT).as_posix()
    listing = working_tree(target_root)
    before = rule_set_files(target_root, rule_set_places(target_root, settings), listing)
    moved = replace(settings, internal_root=new.as_posix())
    after = rule_set_files(target_root, rule_set_places(target_root, moved), listing)
    inside = [rel for rel in before if rel.startswith(f"{folder}/")]
    return folder if any(rel not in after for rel in inside) else None


# --- anchor kinds and their resolvers (ADR-057 point 3) ------------------

#: The anchor kinds the backbone resolves itself (COR-050 point 2).
CORE_ANCHOR_KINDS: tuple[str, ...] = ("path", "record", "artefact")

#: The list of a capability's `friction` block that registers anchor kinds: a
#: mapping from a kind to its entry, whose `command` names the `commands:` leaf
#: that resolves an anchor of the kind (COR-050 point 2; the lifecycle README's
#: package-metadata reference).
KINDS_KEY = "kinds"
KIND_COMMAND_KEY = "command"

#: The one key of a resolver's answer: the files the anchor stands on, in the
#: state the check reads (`resolver_answer`; the lifecycle README).
RESOLVER_PATHS_KEY = "paths"

#: What ends the options a resolver is given: the anchor value comes after it, so
#: no value is read as an option (ADR-057 point 3).
END_OF_OPTIONS = "--"

#: The states a resolver's answer is read against, as a no-answer names them: the
#: working tree's one listing — the change check's and validation's — and HEAD's
#: files, for the whole-repository check and the commands that read HEAD.
WORKING_TREE_STATE = "the working tree"
HEAD_STATE = "HEAD"


@dataclass(frozen=True)
class ResolverCommand:
    """A command a capability registers to resolve an anchor kind (COR-050 point 2).

    `query_contract` is whether the command's registry entry declares the
    query contract (COR-050 point 2; ADR-057 point 3 realises the declaration):
    bounded, deterministic, read-only and needing no network. The declaration
    grants nothing; it is a claim the backbone requires and trusts. `script`
    is the leaf's script, `None` when `command` names no leaf of the
    capability's `commands:` tree — a registration that resolves nothing
    (`refuse_resolver_naming_no_leaf`). `shared_with` names the other installed
    capabilities that register the same kind: a kind registered twice is
    refused, whichever registered it first (`unresolved_kind_reason`).
    """

    kind: str
    capability: str
    command: str
    query_contract: bool = False
    script: Path | None = None
    shared_with: tuple[str, ...] = ()

    @property
    def registrants(self) -> tuple[str, ...]:
        """Every installed capability that registers the kind, in name order."""
        return (self.capability, *self.shared_with)


def refuse_resolver_without_query_contract(resolver: ResolverCommand) -> str | None:
    """Why `resolver` may not run, or `None` when it may.

    A resolver is a query: bounded in time, needing no network, changing
    nothing in the project and deterministic (COR-050 point 2). The backbone
    admits one only when its command declares that contract — COR-050 point 2
    requires the declaration, ADR-057 point 3 realises it. The declaration is
    trusted, not enforced: nothing here confines the process it would start —
    not a boundary, as the CLI reference states.
    """
    if resolver.query_contract:
        return None
    return (
        f"the resolver `{resolver.command}` that {resolver.capability} registers for it "
        f"does not declare the query contract (bounded, deterministic, read-only, "
        f"needing no network); a resolver runs only when it declares it"
    )


def refuse_resolver_naming_no_leaf(resolver: ResolverCommand) -> str | None:
    """Why `resolver` cannot run when its `command` names no leaf of its capability's
    `commands:` tree, or `None` when it names one. Said before the declaration is
    looked for: a command that is not there declares nothing, and the fix is the
    reference, not the declaration."""
    if resolver.script is not None:
        return None
    return (
        f"the resolver `{resolver.command}` that {resolver.capability} registers for it is "
        f"not declared in the `commands:` of {resolver.capability}"
    )


def declared_anchor_kinds(package: Mapping[str, Any]) -> Iterator[tuple[str, str]]:
    """`(kind, command reference)` for each anchor kind a package registers under
    `friction.kinds`, in written order. Read forgivingly: an entry that is not a
    mapping with a text `command` registers nothing here — the packages member
    reports it."""
    kinds = _mapping_or_empty(package.get(FRICTION_KEY)).get(KINDS_KEY)
    for kind, entry in _mapping_or_empty(kinds).items():
        reference = _mapping_or_empty(entry).get(KIND_COMMAND_KEY)
        if isinstance(reference, str) and reference.strip():
            yield kind, reference


def registered_anchor_kinds(
    target_root: Path, tree: RepositoryTree | None = None
) -> dict[str, ResolverCommand]:
    """The anchor kinds installed capabilities register, by kind — the one
    registry every engine reads (ADR-057 point 2).

    Each installed capability's `friction.kinds` (`declared_anchor_kinds`),
    with the leaf its entry names in the capability's `commands:` tree and
    whether that leaf declares the query contract. A kind the backbone
    resolves itself is never registered: the backbone's own resolution stands,
    and the packages member refuses the entry. A kind two or more capabilities
    register is kept once, naming them all (`ResolverCommand.shared_with`), so
    an anchor of it reads as refused rather than as resolved by either.

    With a `tree`, the registrations that state holds — its manifest and its
    package files, read forgivingly — which say whether a kind could be
    resolved there (`unresolved_kind_reason`), as the change check asks of its
    base. No resolver is run from them: a script is the one on disk.
    """
    load = _mapping_loader(target_root, tree)
    found: dict[str, list[ResolverCommand]] = {}
    for name in installed_capability_names(target_root, tree):
        component = CAPABILITIES_DIR / name
        package = load((component / command_runner.PACKAGE_FILE).as_posix())
        component_dir = target_root / component
        commands = command_runner.commands_of(
            component_dir, package.get(command_runner.COMMANDS_KEY)
        )
        for kind, reference in declared_anchor_kinds(package):
            if kind in CORE_ANCHOR_KINDS:
                continue
            leaf = command_runner.resolve_command(commands, reference)
            found.setdefault(kind, []).append(
                ResolverCommand(
                    kind=kind,
                    capability=name,
                    command=reference,
                    query_contract=(
                        leaf is not None and leaf.entry.get(validators.QUERY_CONTRACT_KEY) is True
                    ),
                    script=None if leaf is None else leaf.script,
                )
            )
    return {
        kind: replace(first, shared_with=tuple(r.capability for r in rest))
        for kind, (first, *rest) in found.items()
    }


def unresolved_kind_reason(kind: str, registry: Mapping[str, ResolverCommand]) -> str | None:
    """`None` when an anchor of `kind` can be resolved; otherwise why nothing resolves it.

    The backbone resolves its own kinds. A registered kind can be resolved when
    one installed capability registers it, its command names a leaf of that
    capability's `commands:` tree (`refuse_resolver_naming_no_leaf`) and the
    leaf declares the query contract (`refuse_resolver_without_query_contract`):
    a kind two capabilities register is refused for both, and a resolver that
    names no leaf, or one without the declaration, is refused before it could
    run. Whether one anchor of a kind that can be resolved does resolve is its
    resolver's answer (`AnchorKinds.resolve`), which fails closed (COR-050
    point 2).
    """
    if kind in CORE_ANCHOR_KINDS:
        return None
    resolver = registry.get(kind)
    if resolver is None:
        return "no installed component registers a resolver for it"
    if resolver.shared_with:
        return (
            f"the capabilities {', '.join(resolver.registrants)} each register it, and a kind "
            f"registered more than once is refused: none of their resolvers runs"
        )
    return refuse_resolver_naming_no_leaf(resolver) or refuse_resolver_without_query_contract(
        resolver
    )


@dataclass(frozen=True)
class AnchorResolution:
    """What a resolver answered for one anchor value (COR-050 point 2).

    `paths` are the files the anchor stands on in the state the check reads,
    sorted — none when it denotes nothing, which makes the anchor dead.
    `no_answer` says why the resolver gave no answer, when it gave none: the
    anchor is then unresolved, never resolved — whether what it denotes changed
    cannot be told. `overran` is whether it gave none because it overran its
    bound: such a resolver is not started again in the same check
    (`AnchorKinds.resolve`).
    """

    paths: tuple[str, ...] = ()
    no_answer: str | None = None
    overran: bool = False


def resolver_answer(
    document: Any, reference: str, files: Collection[str], state: str = WORKING_TREE_STATE
) -> AnchorResolution:
    """A resolver's answer, read failing closed (COR-050 point 2; ADR-057 point 3).

    The answer is exactly `{"paths": [...]}`: every entry a repository-relative
    POSIX path naming a file of the state the check reads — `files`, which
    `state` names in a no-answer — a path named twice counted once. Anything
    else — another document, another key, an entry that is not text or names
    no file that state holds (an absolute path, one climbing with `..`, a
    folder, a file git ignores, for HEAD a file not committed) — is no answer,
    never a partial one.
    """
    expected = f'expected exactly `{{"{RESOLVER_PATHS_KEY}": [...]}}`'
    if not isinstance(document, Mapping) or set(cast(Mapping[Any, Any], document)) != {
        RESOLVER_PATHS_KEY
    }:
        return AnchorResolution(
            no_answer=f"command {reference!r} printed no resolver answer: {expected}"
        )
    listed = cast(Mapping[str, Any], document)[RESOLVER_PATHS_KEY]
    if not isinstance(listed, list):
        return AnchorResolution(
            no_answer=(
                f"command {reference!r} answered `{RESOLVER_PATHS_KEY}` that is not a list: "
                f"{expected}"
            )
        )
    paths: set[str] = set()
    for item in cast(list[Any], listed):
        if not isinstance(item, str) or item not in files:
            return AnchorResolution(
                no_answer=(
                    f"command {reference!r} answered {item!r}, which is not a file of "
                    f"{state}: every path a resolver answers is repository-relative and "
                    f"names a file that state holds"
                )
            )
        paths.add(item)
    return AnchorResolution(paths=tuple(sorted(paths)))


def run_resolver(
    target_root: Path,
    resolver: ResolverCommand,
    value: str,
    files: Collection[str],
    state: str = WORKING_TREE_STATE,
) -> AnchorResolution:
    """Run `resolver` for one anchor value under the query policy, and read its answer
    against `files`, the files of the state the check reads, which `state` names
    (`resolver_answer`).

    The policy every query command the backbone runs is under (ADR-057 point
    3; the lifecycle README, "How a registered command is run"): the command
    must name a leaf that declares the query contract, or it is not started;
    the script runs from the project root with `--json`, the end-of-options
    marker and then the anchor value — its one subject (COR-052 point 6), last
    so that no value is read as an option — the offline marker set and the
    base override removed, in its own process group, bounded by the backbone's
    one command bound and killed as a group when it overruns (inside another
    run, by the time that run has left, in the outermost run's group). An
    abnormal exit, a timeout, a value the system cannot pass as an argument, an
    environment not provisioned or an answer `resolver_answer` cannot read is
    no answer (`AnchorResolution.no_answer`).
    """
    refusal = refuse_resolver_naming_no_leaf(resolver) or refuse_resolver_without_query_contract(
        resolver
    )
    if refusal is not None or resolver.script is None:
        return AnchorResolution(no_answer=refusal)
    if not resolver.script.is_file():
        return AnchorResolution(
            no_answer=f"command {resolver.command!r} names a script that does not exist"
        )
    run = command_runner.run_command(
        resolver.script,
        [validators.QUERY_FLAG, END_OF_OPTIONS, value],
        cwd=target_root,
        extra_env=validators.OFFLINE_MARKER,
        drop_env=validators.QUERY_DROPPED_ENV,
    )
    if run.ending is not command_runner.Ending.ANSWERED:
        return AnchorResolution(
            no_answer=validators.why_no_answer(run, resolver.command).rstrip("."),
            overran=run.ending is command_runner.Ending.TIMED_OUT,
        )
    return resolver_answer(run.document, resolver.command, files, state)


class AnchorKinds:
    """The anchor kinds one run resolves, and what each anchor of a registered kind
    resolved to: each resolver run at most once per anchor value for the length of
    the run (COR-050 point 2), and never again in it once it overran its bound.

    One per check or validation pass, over the one registry
    (`registered_anchor_kinds`), or a registry a caller hands in. `files` are
    the files of the state the pass reads, which every answer is read against,
    and `state` names it (`resolver_answer`): the working tree's one listing
    for the change check and for validation, HEAD's files for the
    whole-repository check and the commands that read HEAD — so a path that
    state does not hold is no answer, whatever the resolver saw on disk.
    """

    def __init__(
        self,
        target_root: Path,
        registry: Mapping[str, ResolverCommand],
        files: Collection[str],
        state: str = WORKING_TREE_STATE,
    ) -> None:
        self.target_root = target_root
        self.registry = registry
        self._files = files
        self._state = state
        self._resolved: dict[tuple[str, str], AnchorResolution] = {}
        self._overran: dict[str, str] = {}
        """The kinds whose resolver overran its bound in this run, each with the
        value it overran on: not started again (ADR-057 point 3)."""

    def unresolved(self, kind: str) -> str | None:
        """Why nothing resolves an anchor of `kind` (`unresolved_kind_reason`), or `None`."""
        return unresolved_kind_reason(kind, self.registry)

    def resolve(self, anchor: Anchor) -> AnchorResolution:
        """What the resolver `anchor`'s kind registers answered for its value.

        Meaningful for a registered kind that can be resolved (`unresolved` is
        `None`); any other kind gives no answer, saying why. A resolver that
        overran its bound is not started again in this run: the values it had
        left have no answer, so a resolver that hangs costs one bound, not one
        per value.
        """
        key = (anchor.kind, anchor.value)
        if key not in self._resolved:
            reason = self.unresolved(anchor.kind)
            resolver = self.registry.get(anchor.kind)
            if anchor.kind in CORE_ANCHOR_KINDS:
                resolution = AnchorResolution(no_answer="the backbone resolves it itself")
            elif reason is not None or resolver is None:
                resolution = AnchorResolution(no_answer=reason)
            elif anchor.kind in self._overran:
                resolution = AnchorResolution(
                    no_answer=(
                        f"command {resolver.command!r} was not started again: it overran its "
                        f"bound for {self._overran[anchor.kind]!r} earlier in this check"
                    )
                )
            else:
                resolution = run_resolver(
                    self.target_root, resolver, anchor.value, self._files, self._state
                )
                if resolution.overran:
                    self._overran[anchor.kind] = anchor.value
            self._resolved[key] = resolution
        return self._resolved[key]

    def files(self, anchor: Anchor) -> tuple[str, ...]:
        """The files an anchor of a registered kind stands on — its resolver's answer —
        or none: for a core kind, a kind nothing resolves, or a resolver that gave no
        answer."""
        if anchor.kind in CORE_ANCHOR_KINDS or self.unresolved(anchor.kind) is not None:
            return ()
        return self.resolve(anchor).paths


# --- artefacts ----------------------------------------------------------


class ArtefactKind(Enum):
    DOCUMENT = "document"  # a Markdown document with front matter
    ENTRY = "entry"  # one keyed entry of a collection file


@dataclass(frozen=True)
class Anchor:
    """An anchor written as its kind and value (COR-050 points 2 and 4)."""

    kind: str
    value: str


@dataclass(frozen=True)
class Deferral:
    """One well-formed `deferred[]` entry: the anchor it postpones and where it was written.

    `index` is the entry's position in the list as written — malformed
    entries before it count — so a finding's JSON Pointer names the right one.
    """

    index: int
    anchor: Anchor


@dataclass(frozen=True)
class Artefact:
    """One artefact found in a declared place, with its container parsed.

    - `id`: for an entry, the key it sits under; for a document, its own
      `id` field when it has one, else its repository-relative path.
    - `path`: the file, relative to the project root, POSIX-separated.
    - `carrier`: the object that carries the container — the document's whole
      front matter, or the entry mapping — with YAML dates and non-text keys
      rendered back to their written form (`backbone_schemas.as_written`).
    - `body`: the document's body, or the entry's section headed by its id
      (empty when the collection has no such section). Content, per COR-050,
      is this together with the carrier's own fields; later checks compare it.
    - `span`: for an entry, the lines of its file its section spans — exactly
      the text `body` holds — else `None`: for a document, and for an entry
      with no section.
    - `body_line`: for a document, the line of its file its body opens on
      (`document_parts.body_first_line`), from which the lines its section or
      its lead spans are counted (`artefact_parts`); `1` for an entry, whose
      own `span` is counted already.
    - `container` / `friction`: the `pkit` value and its `friction` block, or
      `None` when absent; either may be a non-mapping when malformed — the
      block validator says so.
    - `anchors`: by kind, in written order, from a well-formed `anchors`
      mapping; `revalidated`: the block as written, when a mapping.
    - `rule_set`: for a rule, the rule-set place that claimed its file, else
      `None`. The rule-set file is claimed before the container rule
      (ADR-056 point 2), so the rule-set pass validates a rule's container.
    - `excluded_by`: the `friction.exclude` entry its file lies under, as the
      walk decided it (`FrictionSettings.exclusion`), else `None`. Such an
      artefact is left out of the measures (COR-050 point 7); an artefact read
      from history, never walked, carries `None`.
    """

    id: str
    path: str
    kind: ArtefactKind
    place: Place
    carrier: Mapping[str, Any]
    body: str
    container: Any
    friction: Any
    anchors: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    revalidated: Mapping[str, Any] | None = None
    rule_set: RuleSetPlace | None = None
    excluded_by: SettingsPath | None = None
    span: SectionSpan | None = None
    body_line: int = 1

    @property
    def excluded(self) -> bool:
        """Whether `friction.exclude` leaves it out (`excluded_by`)."""
        return self.excluded_by is not None

    @property
    def location(self) -> str:
        """`path` for a document, `path#id` for an entry — how findings name it."""
        return self.path if self.kind is ArtefactKind.DOCUMENT else f"{self.path}#{self.id}"

    @property
    def has_container(self) -> bool:
        return CONTAINER_KEY in self.carrier

    @property
    def has_friction_block(self) -> bool:
        return isinstance(self.container, Mapping) and FRICTION_KEY in self.container

    @property
    def unanchored_because(self) -> str | None:
        """The reason its block gives for having no anchors (COR-050 point 1), whitespace
        folded; `None` when it gives none, or no text. Whether it stands beside anchors
        is validation's to judge, and whether it counts is the unanchored measure's."""
        reason = _mapping_or_empty(self.friction).get(UNANCHORED_BECAUSE_KEY)
        folded = " ".join(reason.split()) if isinstance(reason, str) else ""
        return folded or None

    @property
    def identifiers(self) -> frozenset[str]:
        """What an `anchors.artefact` value may name to reach this artefact.

        A rule of a method rule set may also be named the way it is cited,
        with its component in front (COR-051 point 6).
        """
        names = {self.id}
        if self.kind is ArtefactKind.DOCUMENT:
            names.add(self.path)
        if self.rule_set is not None and self.rule_set.component is not None:
            names.add(f"{self.rule_set.component}:{self.id}")
        return frozenset(names)

    @property
    def deferrals(self) -> tuple[Deferral, ...]:
        """The well-formed `deferred[]` entries, in written order, each with its written index."""
        if not isinstance(self.revalidated, Mapping):
            return ()
        deferred = self.revalidated.get("deferred")
        if not isinstance(deferred, Sequence) or isinstance(deferred, str):
            return ()
        found: list[Deferral] = []
        for index, entry in enumerate(deferred):
            anchor = entry.get("anchor") if isinstance(entry, Mapping) else None
            if not isinstance(anchor, Mapping):
                continue
            kind, value = anchor.get("kind"), anchor.get("value")
            if isinstance(kind, str) and isinstance(value, str):
                found.append(Deferral(index=index, anchor=Anchor(kind=kind, value=value)))
        return tuple(found)

    def anchors_of_kind(self, kind: str) -> tuple[str, ...]:
        return self.anchors.get(kind, ())


# --- what an artefact's block says -------------------------------------------
#
# The readings both checks and the history walk make of one artefact (ADR-057
# point 2): its content, the parsed marker, and the reason a deferral gives.


#: A record's content (COR-050 point 5), as both checks compare it: `(body, own fields)`
#: where its front matter parses to a mapping, read as a document artefact's content is;
#: otherwise `(whole file, None)` — its text with `\\n` line breaks, or its bytes where it
#: is no UTF-8 text.
RecordContent = tuple[str | bytes, dict[str, Any] | None]


def document_content(carrier: Mapping[str, Any], body: str) -> tuple[str, dict[str, Any]]:
    """The content of what carries a container, and its body (COR-050 point 5): the body
    as text and the carrier's own fields, never the container."""
    return body, {k: v for k, v in carrier.items() if k != CONTAINER_KEY}


def content(artefact: Artefact) -> tuple[str, dict[str, Any]]:
    """An artefact's content (COR-050): its body text and its own fields, never the container."""
    return document_content(artefact.carrier, artefact.body)


def record_content(raw: bytes) -> RecordContent:
    """A record's content (COR-050 point 5), from its file's bytes, whether or not a place
    holds the record.

    Where its front matter parses to a mapping, the record is read as a document
    artefact is (`parse_front_matter`, `document_content`): its body as text and its
    own fields, so nothing in the methodology's container counts, whichever block it
    is. Otherwise its whole file, line endings read universally, with `None` for
    the fields, so a record without such front matter is still compared, never
    skipped, and never equals one with it.
    """
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw, None
    front_matter, body, _reason = parse_front_matter(text)
    if front_matter is None:
        return universal_newlines(text), None
    return document_content(front_matter, body)


def revalidated_field(artefact: Artefact, key: str) -> Any:
    """One key of the artefact's `revalidated` block as written, `None` when absent."""
    revalidated = artefact.revalidated
    return revalidated.get(key) if isinstance(revalidated, Mapping) else None


def parsed_at(artefact: Artefact) -> Any:
    """The parsed value of `at`: the instant, so a quoting or formatting change is no change."""
    value = revalidated_field(artefact, "at")
    if not isinstance(value, str):
        return value
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return value.strip()
    return parsed.astimezone(UTC) if parsed.tzinfo is not None else value.strip()


def entry_reason(artefact: Artefact, deferral: Deferral) -> str | None:
    """The reason one deferral entry carries, whitespace folded; `None` when it carries
    no text."""
    deferred: Any = revalidated_field(artefact, "deferred")
    if not isinstance(deferred, list):
        return None
    entry = cast(list[Any], deferred)[deferral.index]
    reason = cast(Mapping[str, Any], entry).get("reason") if isinstance(entry, Mapping) else None
    return " ".join(reason.split()) if isinstance(reason, str) else None


def deferral_reason(artefact: Artefact, anchor: Anchor) -> str:
    """The reason written on the deferral of `anchor`, whitespace folded; `""` when none.
    An anchor deferred twice — a validation error (COR-050 point 4) — reads as its first
    entry carrying text."""
    for deferral in artefact.deferrals:
        if deferral.anchor == anchor:
            reason = entry_reason(artefact, deferral)
            if reason is not None:
                return reason
    return ""


@dataclass(frozen=True)
class UnreadableFile:
    """A Markdown file in a place whose front matter does not parse as YAML.

    `rule_set` is the rule-set place that claimed it, when it is a rule-set
    file; the rule-set pass reports such a file, the friction pass does not.
    """

    path: str
    place: Place
    reason: str
    rule_set: RuleSetPlace | None = None


@dataclass(frozen=True)
class DiscoveredFile:
    """One Markdown file the walk read, and where it stands among the places.

    `places` are every place that matches it, in walk order — the first is the
    one it was read under; a place for which it is a synced copy is not among
    them. `rule_set` is the rule-set place that claims it (the location rule),
    or `None`. `front_matter` is its front matter as written
    (`backbone_schemas.as_written`) when that is a mapping, else `None`;
    `unreadable` says why the file or its front matter could not be read.
    `excluded_by` is the `friction.exclude` entry it lies under, else `None` —
    the same decision its artefacts carry. `mixed_line_endings` is whether its
    text is written with more than one line break (`line_break`): it is read
    with every one as `\\n`, and the validation pass reports it.
    """

    path: str
    places: tuple[Place, ...]
    rule_set: RuleSetPlace | None
    front_matter: Mapping[str, Any] | None
    unreadable: str | None = None
    excluded_by: SettingsPath | None = None
    mixed_line_endings: bool = False


@dataclass(frozen=True)
class Discovery:
    """What a walk of the declared places found, in deterministic order.

    `places` are the declared places followed by the rule-set places not
    already among them; `rule_set_places` every place the location rule names
    (some of them declared places). `synced` holds the files a declared place
    matched that are synced copies, which were not walked (COR-050 point 14).
    `files` holds every file the walk read, by path — a link is never read, so
    never one of them. `held_folders` are the folders of held documents, each
    with why it holds nothing, if it does; `held` every file one holds, by
    path, whether or not a place matches it — none of them is walked (COR-050
    point 1).
    """

    settings: FrictionSettings
    places: tuple[Place, ...]
    artefacts: tuple[Artefact, ...]
    unreadable: tuple[UnreadableFile, ...]
    synced: tuple[SyncedMatch, ...] = ()
    files: tuple[DiscoveredFile, ...] = ()
    rule_set_places: tuple[RuleSetPlace, ...] = ()
    held_folders: tuple[HeldFolder, ...] = ()
    held: tuple[HeldFile, ...] = ()

    @property
    def with_container(self) -> tuple[Artefact, ...]:
        return tuple(a for a in self.artefacts if a.has_container)

    @functools.cached_property
    def types(self) -> Types:
        """Every artefact's type and the type findings (COR-056), resolved once for
        this discovery (`resolve_types`). Friction never reads them."""
        return resolve_types(self)

    @property
    def is_dormant(self) -> bool:
        """No places declared, or nothing in them to judge (COR-050 point 15).

        A place holding a file whose front matter does not parse keeps the pass
        awake: that file may be the one carrying the container, and a typo must
        never switch the check off silently.
        """
        return not self.places or (not self.with_container and not self.unreadable)

    def find(self, reference: str) -> Artefact | None:
        """The artefact an `anchors.artefact` value names, or None; first in walk order wins."""
        for artefact in self.artefacts:
            if reference in artefact.identifiers:
                return artefact
        return None

    def holding(self, path: str) -> HeldFile | None:
        """The held file at the repository-relative `path`, or None."""
        return next((held for held in self.held if held.path == path), None)


def discover_artefacts(
    target_root: Path,
    settings: FrictionSettings | None = None,
    tree: RepositoryTree | None = None,
) -> Discovery:
    """Walk the declared places and parse every artefact's container.

    The places are the declared ones followed by the rule-set places not
    already among them: rules are artefacts found where artefacts are found
    (COR-051 point 2). A file matched by more than one place is read once,
    under the first place that matched it; whether it is a rule-set file
    depends only on the location rule, not on which place met it. Order:
    places in that order, files within a place by path, entries within a
    collection in written order. The files are a listing's
    (`listed_files_in_place`): with a `tree`, the settings, the listing and
    every file are that state's; without one, the settings are read from disk
    and the listing is the working tree's one listing (`working_tree`) — the
    one the change check reads as its head. A link is never read as a document.

    Which folders hold rule sets is that state's too (`rule_set_places`).
    A file a declared place matches that is a synced copy is never walked
    under that place, whichever state is walked (`synced_copy_test`, read on
    the working tree's install state): it is recorded in `synced` for the
    validation pass, and the place's other matches are walked. A rule-set place
    is not a declared place, so a method rule set that arrives by sync is still
    read as the location rule says (COR-051 point 2).

    A file a held folder holds is walked by no place, whichever state is walked
    (COR-050 point 1): it is recorded in `held` with the folder holding it and
    the places that match it, and read for its front matter alone. A folder
    that holds nothing (`held_folders`) leaves its files to the places. A link
    is never held, as it is never read.
    """
    settings = settings if settings is not None else read_friction_settings(target_root, tree)
    # Which rule-set folders are places is read from the state walked — a
    # commit's own listing, or the disk for the working tree: a folder that
    # exists only at a commit — one a change adds, or deletes outright — is
    # walked there, whichever checkout reads it. The working tree's folders are
    # existence-gated on disk so that a project without rule sets stays dormant
    # without a repository being demanded.
    rule_set_places_found = rule_set_places(target_root, settings, tree)
    places = declared_places(settings)
    declared = frozenset(places)
    places += tuple(r.place for r in rule_set_places_found if r.place not in places)
    if not places and not settings.held:
        return Discovery(settings=settings, places=places, artefacts=(), unreadable=())
    folders = held_folders(target_root, settings, rule_set_places_found)
    listing = tree if tree is not None else working_tree(target_root)
    files = listing.files()
    claimed = rule_set_files(target_root, rule_set_places_found, listing)
    holder: dict[str, HeldFolder] = {}  # each held file: the folder holding it
    for folder in folders:
        if folder.skipped is None:
            for rel in listed_files_in_place(folder.place, files):
                holder.setdefault(rel, folder)
    is_synced_copy = synced_copy_test(target_root) if declared else None
    matched: list[tuple[Place, str]] = []
    synced: list[SyncedMatch] = []
    matching: dict[str, list[Place]] = {}  # each walked file: every place matching it
    left_out: dict[str, list[Place]] = {}  # each held file: every place matching it
    for place in places:
        for rel in listed_files_in_place(place, files):
            if rel in matching:
                matching[rel].append(place)
                continue
            if place in declared and is_synced_copy is not None and is_synced_copy(rel):
                synced.append(SyncedMatch(place=place, path=rel))
                continue
            if rel in holder:
                left_out.setdefault(rel, []).append(place)
                continue
            matching[rel] = [place]
            matched.append((place, rel))

    artefacts: list[Artefact] = []
    unreadable: list[UnreadableFile] = []
    read: list[DiscoveredFile] = []
    texts = document_texts(listing, [rel for _place, rel in matched] + sorted(holder))
    for place, rel in matched:
        rule_set = claimed.get(rel)
        text = texts[rel]
        if text is None:
            continue  # a link: never read as a document
        excluded_by = settings.exclusion(rel)
        front_matter: Mapping[str, Any] | None = None
        mixed = False
        if isinstance(text, ReadFailure):
            reason: str | None = text.reason
        else:
            mixed = line_break(text) is None
            front_matter, found, reason = _read_artefacts(rel, place, text, rule_set=rule_set)
            artefacts.extend(replace(a, excluded_by=excluded_by) for a in found)
        if reason is not None:
            unreadable.append(
                UnreadableFile(path=rel, place=place, reason=reason, rule_set=rule_set)
            )
        read.append(
            DiscoveredFile(
                path=rel,
                places=tuple(matching[rel]),
                rule_set=rule_set,
                front_matter=front_matter,
                unreadable=reason,
                excluded_by=excluded_by,
                mixed_line_endings=mixed,
            )
        )
    held = [
        replace(
            _held_file(rel, holder[rel], tuple(left_out.get(rel, ())), text),
            excluded_by=settings.exclusion(rel),
        )
        for rel in sorted(holder)
        if (text := texts[rel]) is not None  # a link: never read, so never held
    ]
    return Discovery(
        settings=settings,
        places=places,
        artefacts=tuple(artefacts),
        unreadable=tuple(unreadable),
        synced=tuple(synced),
        files=tuple(sorted(read, key=lambda f: f.path)),
        rule_set_places=rule_set_places_found,
        held_folders=folders,
        held=tuple(held),
    )


def _held_file(
    rel: str, folder: HeldFolder, places: tuple[Place, ...], text: str | ReadFailure
) -> HeldFile:
    """A held file, read for its front matter and every friction block in it.

    Its front matter is parsed as a file in a place is (`document_parts.parse_front_matter`),
    and searched whole for a friction block (`_friction_blocks`): no reading of
    it as an artefact is assumed, so a block is found wherever it is written —
    as a document's, an entry's, a rule's, or deeper.
    """
    if isinstance(text, ReadFailure):
        return HeldFile(rel, folder, places, front_matter=None, unreadable=text.reason, blocks=())
    front_matter, _body, reason = parse_front_matter(text)
    blocks = tuple(_friction_blocks(front_matter, "")) if front_matter is not None else ()
    return HeldFile(rel, folder, places, front_matter, unreadable=reason, blocks=blocks)


def _friction_blocks(value: Any, pointer: str) -> Iterator[str]:
    """The JSON Pointer of every friction block in a parsed value, in written order:
    each mapping whose container holds the `friction` key, and within it, deeper."""
    if isinstance(value, Mapping):
        mapping = cast("Mapping[Any, Any]", value)
        container = mapping.get(CONTAINER_KEY)
        if isinstance(container, Mapping) and FRICTION_KEY in container:
            yield f"{pointer}/{CONTAINER_KEY}/{FRICTION_KEY}"
        for key, item in mapping.items():
            yield from _friction_blocks(item, f"{pointer}/{_pointer_token(key)}")
    elif isinstance(value, list):
        for index, item in enumerate(cast("list[Any]", value)):
            yield from _friction_blocks(item, f"{pointer}/{index}")


def _pointer_token(key: Any) -> str:
    """One JSON Pointer reference token (RFC 6901 escaping)."""
    return str(key).replace("~", "~0").replace("/", "~1")


@dataclass(frozen=True)
class ReadFailure:
    """Why a file of a tree could not be read as text: it would not open, or is not UTF-8."""

    reason: str


def document_texts(
    tree: RepositoryTree, rels: Sequence[str]
) -> dict[str, str | ReadFailure | None]:
    """Each matched file's text, or why it could not be read; `None` for a link.

    The one reading of a tree's files as text, for the walk here and for the
    rule-set reader (`rule_sets.discover_rule_sets`) alike, whichever state the
    tree is of (ADR-057 point 2).

    The working tree is read file by file, so a file that will not open is
    reported as unreadable, whichever reader asked; a commit is read in one pass.
    """
    contents: Mapping[str, bytes | None | ReadFailure]
    if isinstance(tree, WorkingTree):
        contents = {rel: _read_working_file(tree, rel) for rel in rels}
    else:
        contents = tree.read_bytes(rels)
    texts: dict[str, str | ReadFailure | None] = {}
    for rel in rels:
        raw = contents.get(rel)
        if raw is None or isinstance(raw, ReadFailure):
            texts[rel] = raw
            continue
        try:
            texts[rel] = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            texts[rel] = ReadFailure(str(exc))
    return texts


def _read_working_file(tree: WorkingTree, rel: str) -> bytes | None | ReadFailure:
    try:
        return tree.read_file(rel)
    except OSError as exc:
        return ReadFailure(str(exc))


def parse_artefacts(
    rel: str, place: Place, text: str, *, rule_set: RuleSetPlace | None = None
) -> tuple[list[Artefact], str | None]:
    """The artefacts one Markdown text holds, or why its front matter could not be read.

    The one reading of a file's text as artefacts (COR-050 point 1), whichever
    state of the repository the text comes from: the walk of the places above
    and the history walk of the whole-repository check both call it. Returns
    `(artefacts, None)` — empty when the text carries no front matter, or front
    matter that is not a mapping, since neither makes an artefact — or
    `([], reason)` when the front matter does not parse as YAML. Line endings
    are read universally (`\\r\\n` and `\\r` as `\\n`,
    `document_parts.split_front_matter`), as a text file is read, whether the
    text came from disk or from git — so an artefact whose line endings changed
    while its text did not has the same content (COR-050 point 5).
    """
    _front_matter, found, reason = _read_artefacts(rel, place, text, rule_set=rule_set)
    return found, reason


def _read_artefacts(
    rel: str, place: Place, text: str, *, rule_set: RuleSetPlace | None = None
) -> tuple[Mapping[str, Any] | None, list[Artefact], str | None]:
    """`parse_artefacts`, with the file's front matter as written when it is a
    mapping: `(front_matter, artefacts, reason)`."""
    written, body, reason = parse_front_matter(text)
    if written is None:
        return None, [], reason
    body_line = body_first_line(text, body)
    found = _artefacts_of_file(rel, place, written, body, body_line, rule_set=rule_set)
    return written, found, None


def _artefacts_of_file(
    rel: str,
    place: Place,
    front_matter: Mapping[str, Any],
    body: str,
    body_line: int,
    *,
    rule_set: RuleSetPlace | None = None,
) -> list[Artefact]:
    """One document, or one artefact per entry of a collection file.

    `body_line` is the line of the file the body opens on, from which an
    entry's span is counted. A rule-set file (`rule_set` given) is a
    collection whose entries are the values of its `rules` map, each a rule
    (COR-051 point 2); its other keys are the set's own data, never entries.

    Otherwise, a file is a collection when its front matter does not itself
    carry the container but at least one of its top-level mapping values does
    (COR-050 point 1: "a collection file whose front matter maps entries by
    id"). Every top-level mapping value is then an entry — including those
    without a container, which are unanchored artefacts. Otherwise the file is
    one document.
    """
    if rule_set is not None:
        return _rules_of_file(rel, place, front_matter, body, body_line, rule_set)
    entries = {k: v for k, v in front_matter.items() if isinstance(v, Mapping)}
    is_collection = CONTAINER_KEY not in front_matter and any(
        CONTAINER_KEY in entry for entry in entries.values()
    )
    if not is_collection:
        doc_id = front_matter.get("id")
        return [
            _artefact(
                artefact_id=doc_id if isinstance(doc_id, str) and doc_id else rel,
                rel=rel,
                kind=ArtefactKind.DOCUMENT,
                place=place,
                carrier=front_matter,
                body=body,
                body_line=body_line,
            )
        ]
    found: list[Artefact] = []
    read = Body.read(body)
    for entry_id, entry in entries.items():
        section, span = _entry_body(read, entry_id, body_line)
        found.append(
            _artefact(
                artefact_id=entry_id,
                rel=rel,
                kind=ArtefactKind.ENTRY,
                place=place,
                carrier=entry,
                body=section,
                span=span,
            )
        )
    return found


def _rules_of_file(
    rel: str,
    place: Place,
    front_matter: Mapping[str, Any],
    body: str,
    body_line: int,
    rule_set: RuleSetPlace,
) -> list[Artefact]:
    """One artefact per rule of a rule-set file, in written order.

    A rule's content is its data entry together with the body section headed
    by its id (COR-051 point 2). An entry that is not a mapping carries no
    fields to read; the rule-set pass reports its shape.
    """
    rules = front_matter.get(RULES_KEY)
    if not isinstance(rules, Mapping):
        return []
    found: list[Artefact] = []
    read = Body.read(body)
    for rule_id, entry in rules.items():
        if not isinstance(entry, Mapping):
            continue
        section, span = _entry_body(read, rule_id, body_line)
        found.append(
            _artefact(
                artefact_id=rule_id,
                rel=rel,
                kind=ArtefactKind.ENTRY,
                place=place,
                carrier=entry,
                body=section,
                span=span,
                rule_set=rule_set,
            )
        )
    return found


def _artefact(
    *,
    artefact_id: str,
    rel: str,
    kind: ArtefactKind,
    place: Place,
    carrier: Mapping[str, Any],
    body: str,
    span: SectionSpan | None = None,
    rule_set: RuleSetPlace | None = None,
    body_line: int = 1,
) -> Artefact:
    container = carrier.get(CONTAINER_KEY)
    friction = container.get(FRICTION_KEY) if isinstance(container, Mapping) else None
    anchors: dict[str, tuple[str, ...]] = {}
    revalidated: Mapping[str, Any] | None = None
    if isinstance(friction, Mapping):
        raw_anchors = friction.get("anchors")
        if isinstance(raw_anchors, Mapping):
            for anchor_kind, values in raw_anchors.items():
                if isinstance(values, Sequence) and not isinstance(values, str):
                    anchors[str(anchor_kind)] = tuple(v for v in values if isinstance(v, str))
        raw_revalidated = friction.get("revalidated")
        if isinstance(raw_revalidated, Mapping):
            revalidated = raw_revalidated
    return Artefact(
        id=artefact_id,
        path=rel,
        kind=kind,
        place=place,
        carrier=carrier,
        body=body,
        container=container,
        friction=friction,
        anchors=anchors,
        revalidated=revalidated,
        rule_set=rule_set,
        span=span,
        body_line=body_line,
    )


# --- an entry's section -----------------------------------------------------


def _entry_body(read: Body, entry_id: str, body_line: int) -> tuple[str, SectionSpan | None]:
    """An entry's section (COR-050 point 1), and the lines of its file it spans.

    The section is the one the reading of where a part lies finds by the
    entry's id (`document_parts.Body.section_by_id`), so the span covers exactly
    the text friction compares as the entry's body. `body_line` is the line of
    the file the body opens on. Without a section, `("", None)`.
    """
    extent = read.section_by_id(entry_id)
    if extent is None:
        return "", None
    return read.text_of(extent), read.span_of(extent, body_line)


# --- artefact types (COR-056) ---------------------------------------------------
#
# An artefact may have one type: a declared name for what it is. A component
# declares its types in a type registry and names them on its places, and the
# project names types on its own places. Discovery resolves every artefact's type
# here, from the places that match its file, in the order the types record sets
# (COR-056 point 3). It is the one home of that resolution, and of the findings
# about it (ADR-057 point 2): every reader takes an artefact's type from it, and
# none ranks places itself. Friction never reads a type.

# How a place reads against a file it matches (COR-056 point 3): at equal length
# of literal part, an exact file before a glob, and a glob before a folder.
_FILE, _GLOB, _FOLDER = 0, 1, 2


def place_specificity(pattern: str, path: str) -> tuple[int, int]:
    """`(length of its literal part, form)` of a place matching the file `path`
    (COR-056 point 3), the form `0` for an exact file, `1` for a glob, `2` for a
    folder.

    A place's literal part is its path up to its first wildcard, counted in
    characters. A folder's is its path followed by `/`. A glob that is a folder
    followed by `/**` alone is read as that folder, so one place spelt two ways
    ranks the same. A path without wildcards is the exact file when it is `path`
    itself, else the folder holding it. The whole repository, `.` or `**`, is a
    folder whose literal part is empty.
    """
    normal = _normal(pattern)
    if normal in (".", "**"):
        return 0, _FOLDER
    if any(ch in _GLOB_CHARS for ch in normal):
        folder, _, last = normal.rpartition("/")
        if last == "**" and folder and not any(ch in _GLOB_CHARS for ch in folder):
            return len(folder) + 1, _FOLDER
        return min(normal.index(ch) for ch in _GLOB_CHARS if ch in normal), _GLOB
    if normal == path:
        return len(normal), _FILE
    return len(normal) + 1, _FOLDER


@dataclass(frozen=True)
class RankedPlace:
    """A place that matches an artefact's file, with its rank among them: `1` for
    the first, and places that rank equal share one (COR-056 point 3)."""

    place: Place
    rank: int


@dataclass(frozen=True)
class ArtefactType:
    """An artefact's type, as discovery resolves it (COR-056 points 3, 4 and 6).

    - `type`: its full name, or `None`. A rule's is `backbone:rule`. An
      artefact has none when no typed place types it, when it declines the
      kind the winning type asks for, or while a tie stands.
    - `place`: the place that gave it. `None` for a rule, whose type the
      backbone gives, and for an artefact with no type.
    - `conflict`: in a tie, each tied type the artefact counts as, with the
      place giving it. A type with a kind field counts only where the artefact
      declares its kind. Empty when there is no tie, and when the artefact
      declares the kind of no tied type: it then has no type.
    - `places`: every place that matches its file, in COR-056 point 3's order,
      each with its rank.
    """

    type: str | None = None
    place: Place | None = None
    conflict: tuple[tuple[str, Place], ...] = ()
    places: tuple[RankedPlace, ...] = ()

    @property
    def counts_as(self) -> frozenset[str]:
        """The types the artefact counts as, which a scope's `types` selects by: its
        type, or each type in contention while a tie stands (COR-056 point 3)."""
        if self.type is not None:
            return frozenset({self.type})
        return frozenset(type_ for type_, _place in self.conflict)


class TypeFindingKind(Enum):
    """What a type finding is about: one of the findings COR-056 points 2 and 3 list."""

    NOT_ADMITTED = "type-not-admitted"  # a project place giving a component's type it may not give
    NAME_TAKEN = "type-name-taken"  # a bare project type taking a declared type's name
    TIE = "type-tie"  # typed places, one the project's, ranking equal with different types
    YIELDS = "type-yields"  # a typed project place yielding to a component's place
    COMPONENT_TIE = "type-tie-components"  # a tie between places only components declare
    OUTRANKS = "type-outranks"  # one component's typed place typing another's file
    UNDECLARED = "type-undeclared"  # a component's place naming a type its registry lacks
    SCOPE_UNKNOWN = "scope-unknown-type"  # a scope naming a type nobody declares


CONFIGURATION_MEMBER = "configuration"
PACKAGES_MEMBER = "packages"
RULE_SETS_MEMBER = "rule-sets"

#: The one table that names, for each type finding, the validation member that
#: reports it and its severity (ADR-057 point 2). COR-056 decides the severity:
#: what it fails is an `error`, and what it reports without failing is a
#: `report`. A finding is reported by the member that validates the declaration
#: it is about: the project's places, a component's places, or a rule set's scope.
TYPE_FINDINGS: Mapping[TypeFindingKind, tuple[str, validators.Severity]] = {
    TypeFindingKind.NOT_ADMITTED: (CONFIGURATION_MEMBER, validators.Severity.ERROR),
    TypeFindingKind.NAME_TAKEN: (CONFIGURATION_MEMBER, validators.Severity.ERROR),
    TypeFindingKind.TIE: (CONFIGURATION_MEMBER, validators.Severity.ERROR),
    TypeFindingKind.YIELDS: (CONFIGURATION_MEMBER, validators.Severity.REPORT),
    TypeFindingKind.COMPONENT_TIE: (PACKAGES_MEMBER, validators.Severity.REPORT),
    TypeFindingKind.OUTRANKS: (PACKAGES_MEMBER, validators.Severity.REPORT),
    TypeFindingKind.UNDECLARED: (PACKAGES_MEMBER, validators.Severity.REPORT),
    TypeFindingKind.SCOPE_UNKNOWN: (RULE_SETS_MEMBER, validators.Severity.ERROR),
}


@dataclass(frozen=True)
class TypeFinding:
    """One type finding, located at the declaration it is about: `file`, relative to
    the project root, and `pointer`, a JSON Pointer into it. `source` is who
    declares it: `project`, `capability:<name>`, or a rule set's owner. Its member
    and severity are the table's (`TYPE_FINDINGS`)."""

    kind: TypeFindingKind
    file: str
    pointer: str
    source: str
    message: str

    @property
    def member(self) -> str:
        return TYPE_FINDINGS[self.kind][0]

    @property
    def severity(self) -> validators.Severity:
        return TYPE_FINDINGS[self.kind][1]


@dataclass(frozen=True)
class Types:
    """Every artefact's type, and the findings about types, of one discovery.

    `registry` holds every declared type by its full name: the backbone's own,
    then each installed component's. `places` holds the type each typed place
    gives. `artefacts` holds each artefact's type, by its location. `findings`
    are the type findings, in a deterministic order.
    """

    registry: Mapping[str, DeclaredType]
    places: Mapping[Place, str]
    artefacts: Mapping[str, ArtefactType]
    findings: tuple[TypeFinding, ...] = ()

    def of(self, artefact: Artefact) -> ArtefactType:
        """`artefact`'s type: no type for one discovery did not walk."""
        return self.artefacts.get(artefact.location, ArtefactType())

    def reported_by(self, member: str) -> tuple[TypeFinding, ...]:
        """The type findings the table names `member` to report."""
        return tuple(finding for finding in self.findings if finding.member == member)


def declares_kind(declared: DeclaredType | None, carrier: Mapping[str, Any]) -> bool:
    """Whether an artefact may take `declared` as its kind field asks (COR-056 point 4).

    A type with no kind field asks nothing. Otherwise the artefact's own field —
    a document's front-matter field, an entry's own field — must be present and
    not empty. Which kind it names is the type owner's, never read here.
    """
    if declared is None or declared.kind_field is None:
        return True
    value = carrier.get(declared.kind_field)
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping | list):
        return bool(cast("Mapping[Any, Any] | list[Any]", value))
    return True


def unknown_type(named: str, settings: FrictionSettings) -> str | None:
    """Why the type `named` is one no owner declares, or `None` when one does.

    A component's type is declared by its installed component's type registry,
    the backbone's by the backbone, and a bare type by a project place that gives
    it (COR-056 point 2). The reason says which owner is missing, or which owner
    lacks the type.
    """
    owner, sep, name = named.partition(":")
    if not sep:
        if named in settings.project_types:
            return None
        return (
            "and no place of the project gives it: a project declares its own type by "
            "giving it on one of its places, `{path, type}` in `friction.places`"
        )
    registry = settings.type_registry
    if named in registry:
        return None
    if owner == BACKBONE_COMPONENT:
        known = ", ".join(t.type for t in BACKBONE_TYPES)
        return f"and the backbone declares no type {name!r} (its types: {known})"
    if owner not in settings.installed:
        return f"and no installed component is named {owner!r}"
    declared = sorted(t.name for t in settings.types if t.owner == owner)
    listed = f" (it declares: {', '.join(declared)})" if declared else ""
    return f"and {owner}'s type registry declares no type {name!r}{listed}"


def bare_type_collisions(
    declared: Iterable[DeclaredType], places: Iterable[SettingsPath]
) -> list[tuple[SettingsPath, DeclaredType]]:
    """Each project place whose bare type takes the name of a `declared` type, with
    that type: the place in written order, then each type it collides with
    (COR-056 point 2).

    The one comparison of a bare project type with a declared type's name. Validation
    refuses a collision with a type the backbone or an installed component declares,
    and the install plan reports one with a type the component would bring.
    """
    types = list(declared)
    return [
        (place, declared_type)
        for place in places
        if place.source == PROJECT_SOURCE and place.type is not None and ":" not in place.type
        for declared_type in types
        if declared_type.name == place.type
    ]


class _Order:
    """The order of places COR-056 point 3 sets, over one discovery."""

    def __init__(self, discovery: Discovery) -> None:
        settings = discovery.settings
        self.registry = settings.type_registry
        self._roots = tuple(settings.roots.values())
        self._walk = {place: index for index, place in enumerate(discovery.places)}
        self._root_wide: dict[Place, bool] = {}

    def root_wide(self, place: Place) -> bool:
        """Whether `place` equals or encloses a documentation root (`_encloses`)."""
        if place not in self._root_wide:
            self._root_wide[place] = any(_encloses(place, root) for root in self._roots)
        return self._root_wide[place]

    def gives(self, place: Place) -> str | None:
        """The type `place` gives, or `None` (COR-056 points 2 and 3).

        An untyped place gives none. Neither does a component's place naming a type
        its own registry does not declare, nor a project place naming a component's
        type no installed registry declares. A bare project type gives itself, and
        any other declared type counts until its declaration is mended, though
        validation fails on it.
        """
        named = place.declaration.type
        if named is None:
            return None
        if ":" not in named:
            return named if place.source == PROJECT_SOURCE else None
        return named if named in self.registry else None

    def yielded_to(self, places: Sequence[Place]) -> Place | None:
        """The first component's place among `places` that is not root-wide: where one
        matches a file, no project place gives that file a type (COR-056 point 3)."""
        return next(
            (p for p in places if p.source != PROJECT_SOURCE and not self.root_wide(p)), None
        )

    def ranked(self, path: str, places: Sequence[Place]) -> tuple[RankedPlace, ...]:
        """`places`, all matching the file `path`, in COR-056 point 3's order.

        A project place that yields to a component's place comes after every place
        that does not. Then a place that is not root-wide comes before one that is.
        Then the longer literal part comes first, and at equal length an exact file,
        then a glob, then a folder. Places that rank equal share a rank and keep walk
        order.
        """
        yielding = self.yielded_to(places) is not None

        def key(place: Place) -> tuple[bool, bool, int, int]:
            length, form = place_specificity(place.pattern, path)
            return (
                yielding and place.source == PROJECT_SOURCE,
                self.root_wide(place),
                -length,
                form,
            )

        ordered = sorted(places, key=lambda p: (key(p), self._walk.get(p, len(self._walk))))
        ranked: list[RankedPlace] = []
        previous: tuple[bool, bool, int, int] | None = None
        rank = 0
        for place in ordered:
            current = key(place)
            if current != previous:
                rank, previous = rank + 1, current
            ranked.append(RankedPlace(place, rank))
        return tuple(ranked)

    def contenders(
        self, ranked: Sequence[RankedPlace], yielded_to: Place | None
    ) -> list[tuple[str, Place]]:
        """The typed places that rank first, each with the type it gives, in order.

        A place that gives no type takes no part, and a project place that yields
        is out of contention (COR-056 point 3).
        """
        typed = [
            (r.rank, given, r.place)
            for r in ranked
            if (given := self.gives(r.place)) is not None
            and not (yielded_to is not None and r.place.source == PROJECT_SOURCE)
        ]
        if not typed:
            return []
        first = typed[0][0]
        return [(given, place) for rank, given, place in typed if rank == first]


def resolve_types(discovery: Discovery) -> Types:
    """Every artefact's type, and the type findings, of `discovery` (COR-056).

    The one resolution (ADR-057 point 2): `Discovery.types` gives it, and the
    reading document, the scopes and the validation members read it there.
    """
    order = _Order(discovery)
    places_of = {found.path: found.places for found in discovery.files}
    artefacts = {
        artefact.location: _artefact_type(
            order, artefact, places_of.get(artefact.path, (artefact.place,))
        )
        for artefact in discovery.artefacts
    }
    findings = [
        *_declaration_findings(discovery.settings),
        *_ranking_findings(discovery, order, artefacts),
        *_scope_type_findings(discovery),
    ]
    given = {place: type_ for place in discovery.places if (type_ := order.gives(place))}
    return Types(
        registry=order.registry, places=given, artefacts=artefacts, findings=tuple(findings)
    )


def _artefact_type(order: _Order, artefact: Artefact, places: Sequence[Place]) -> ArtefactType:
    """One artefact's type (COR-056 points 3 and 4).

    Every rule is `backbone:rule`. Otherwise the typed places that rank first
    decide. One type among them is the artefact's when it declares the kind its
    type asks for, and otherwise it has none: no less specific place types it
    instead. Several types among them are a tie, and the artefact counts as each
    whose kind it declares.
    """
    ranked = order.ranked(artefact.path, places)
    if artefact.rule_set is not None:
        return ArtefactType(type=RULE_TYPE, places=ranked)
    first: dict[str, Place] = {}
    for given, place in order.contenders(ranked, order.yielded_to(places)):
        first.setdefault(given, place)
    counted = tuple(
        (given, place)
        for given, place in first.items()
        if declares_kind(order.registry.get(given), artefact.carrier)
    )
    if len(first) == 1:
        if counted:
            return ArtefactType(type=counted[0][0], place=counted[0][1], places=ranked)
        return ArtefactType(places=ranked)
    return ArtefactType(conflict=counted, places=ranked)


def _declaration_findings(settings: FrictionSettings) -> Iterator[TypeFinding]:
    """What the places' own declarations of a type get wrong (COR-056 point 2), each
    at the place's `type`, in written order: a project place giving a component's
    type it may not give, a bare project type taking a declared type's name, and a
    component's place naming a type its own registry does not declare."""
    registry = settings.type_registry
    collisions: dict[str, list[DeclaredType]] = {}
    for place, declared in bare_type_collisions(registry.values(), settings.places):
        collisions.setdefault(place.pointer, []).append(declared)
    for place in settings.places:
        named = place.type
        if named is None:
            continue
        pointer = f"{place.pointer}/{TYPE_KEY}"
        if place.source != PROJECT_SOURCE:
            if named not in registry:
                owner, _sep, name = named.partition(":")
                yield TypeFinding(
                    TypeFindingKind.UNDECLARED,
                    place.file,
                    pointer,
                    place.source,
                    f"place {place.value!r} names the type {name!r}, which {owner}'s type "
                    f"registry (`friction.types`) does not declare, so it gives no type. "
                    f"Reported, not failed: the project cannot mend a component's package "
                    f"metadata (COR-056 points 2 and 3).",
                )
            continue
        if ":" in named:
            owner = named.partition(":")[0]
            problem = unknown_type(named, settings)
            if problem is not None:
                message = (
                    f"place {place.value!r} gives the type {named!r}, {problem}. It gives no "
                    f"type until that is mended (COR-056 points 2 and 3)."
                )
            elif not registry[named].project_places:
                message = (
                    f"place {place.value!r} gives {owner}'s type {named!r}, which {owner} "
                    f"does not admit on a project's places (`project-places` in its type "
                    f"registry). The type still counts until the place is mended "
                    f"(COR-056 points 2 and 3)."
                )
            else:
                continue
            yield TypeFinding(
                TypeFindingKind.NOT_ADMITTED, place.file, pointer, place.source, message
            )
        elif place.pointer in collisions:
            taken = ", ".join(declared.type for declared in collisions[place.pointer])
            yield TypeFinding(
                TypeFindingKind.NAME_TAKEN,
                place.file,
                pointer,
                place.source,
                f"place {place.value!r} gives the bare type {named!r}, which takes the name "
                f"of {taken}. A bare project type never takes the name of a type the "
                f"backbone or an installed component declares: write that type in full, "
                f"or rename the project's own. It still counts as the project's {named!r} "
                f"until mended (COR-056 point 2).",
            )


def _ranking_findings(
    discovery: Discovery, order: _Order, artefacts: Mapping[str, ArtefactType]
) -> Iterator[TypeFinding]:
    """What the order of places makes of the files that hold artefacts (COR-056
    point 3): a typed project place that yields to a component's place, a tie, and
    one component's typed place that types another component's file. Each is
    reported once per pair or group of places, naming how many files it reaches,
    at the declaration whose owner can mend it. A rule-set file is passed over:
    every rule is `backbone:rule`.
    """
    by_path: dict[str, list[Artefact]] = {}
    for artefact in discovery.artefacts:
        if artefact.rule_set is None:
            by_path.setdefault(artefact.path, []).append(artefact)
    yields: dict[tuple[Place, Place], list[str]] = {}
    ties: dict[tuple[Place, ...], tuple[list[tuple[str, Place]], list[str]]] = {}
    outranks: dict[tuple[Place, Place], tuple[str, list[str]]] = {}
    for found in discovery.files:  # by path
        held = by_path.get(found.path)
        if not held:
            continue
        yielded_to = order.yielded_to(found.places)
        if yielded_to is not None:
            for place in found.places:
                if place.source == PROJECT_SOURCE and order.gives(place) is not None:
                    yields.setdefault((place, yielded_to), []).append(found.path)
        contenders = order.contenders(order.ranked(found.path, found.places), yielded_to)
        if len({given for given, _place in contenders}) > 1:
            group = tuple(place for _given, place in contenders)
            ties.setdefault(group, (contenders, []))[1].append(found.path)
        for artefact in held:
            resolved = artefacts[artefact.location]
            winner = resolved.place
            if winner is None or resolved.type is None or winner.source == PROJECT_SOURCE:
                continue
            for place in found.places:
                if place.source in (PROJECT_SOURCE, winner.source) or order.root_wide(place):
                    continue
                files = outranks.setdefault((winner, place), (resolved.type, []))[1]
                if found.path not in files:
                    files.append(found.path)
    for (place, component), files in yields.items():
        yield TypeFinding(
            TypeFindingKind.YIELDS,
            place.declaration.file,
            place.declaration.pointer,
            place.source,
            f"place {place.declaration.value!r} gives the type {order.gives(place)!r}, but it "
            f"yields to {_declarer(component.source)}'s place {_normal(component.pattern)!r} "
            f"on {_files(files)}: where a component's own place that is not root-wide matches "
            f"a file, no project place gives it a type. Reported, not failed "
            f"(COR-056 point 3).",
        )
    for group, (contenders, files) in ties.items():
        tied = _listed(
            [
                f"{_declarer(place.source)}'s place {_normal(place.pattern)!r} (type {given!r})"
                for given, place in contenders
            ]
        )
        projects = [place for place in group if place.source == PROJECT_SOURCE]
        kind = TypeFindingKind.TIE if projects else TypeFindingKind.COMPONENT_TIE
        closing = (
            "Narrow a place, or give the places one type: until then the artefact counts as "
            "each type in contention (COR-056 point 3)."
            if projects
            else "Reported, not failed: the project cannot mend it in its own files, and the "
            "artefact counts as each type in contention (COR-056 point 3)."
        )
        for place in projects or group:
            yield TypeFinding(
                kind,
                place.declaration.file,
                place.declaration.pointer,
                place.source,
                f"{tied} rank equal and give different types on {_files(files)}. {closing}",
            )
    for (winner, place), (given, files) in outranks.items():
        yield TypeFinding(
            TypeFindingKind.OUTRANKS,
            winner.declaration.file,
            winner.declaration.pointer,
            winner.source,
            f"place {winner.declaration.value!r} takes precedence over "
            f"{_declarer(place.source)}'s place {_normal(place.pattern)!r} and gives the type "
            f"{given!r} on {_files(files)}. Reported, and the type stands (COR-056 point 3).",
        )


def _files(files: Sequence[str]) -> str:
    """How a finding names the files it reaches: how many, and the first."""
    return f"{len(files)} file(s), such as {files[0]!r}"


def _listed(items: Sequence[str]) -> str:
    """`a`, `a and b`, `a, b and c`."""
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"


def _scope_type_findings(discovery: Discovery) -> Iterator[TypeFinding]:
    """Each type a rule set's scope names that no owner declares (COR-051 point 2,
    COR-056 point 2), at the entry, rule-set files by path. A value the rule-set
    schema refuses is that schema's finding, never judged here."""
    settings = discovery.settings
    for found in discovery.files:  # by path
        if found.rule_set is None or found.front_matter is None:
            continue
        scope = found.front_matter.get(SCOPE_KEY)
        if not isinstance(scope, Mapping):
            continue
        named = cast("Mapping[str, Any]", scope).get(TYPES_KEY)
        if not isinstance(named, list):
            continue
        for index, value in enumerate(cast("list[Any]", named)):
            if not isinstance(value, str) or _TYPE.fullmatch(value) is None:
                continue
            problem = unknown_type(value, settings)
            if problem is None:
                continue
            yield TypeFinding(
                TypeFindingKind.SCOPE_UNKNOWN,
                found.path,
                f"/{SCOPE_KEY}/{TYPES_KEY}/{index}",
                found.rule_set.place.source,
                f"the scope names the type {value!r}, {problem}, so it selects nothing by "
                f"it. A type in a scope is one its owner declares (COR-051 point 2, "
                f"COR-056 point 2).",
            )


def shared_discovery(target_root: Path) -> Discovery:
    """The working tree's discovery, walked once per validate run
    (`validators.once_per_run`): the `friction` member and the members that report
    type findings read this one walk (ADR-057 point 2)."""
    return validators.once_per_run(
        ("discovery", target_root), lambda: discover_artefacts(target_root)
    )


def shared_types(target_root: Path) -> Types:
    """The working tree's types, resolved once per validate run over the one walk
    (`shared_discovery`): each member that reports type findings reads this one
    answer (ADR-057 point 2)."""
    return shared_discovery(target_root).types


# --- rule-set scopes ----------------------------------------------------


@dataclass(frozen=True)
class Scope:
    """A rule-set file's scope as discovery reads it (COR-051 point 2).

    `paths` select by file, and `None` means every file matches. `exclude` leaves
    a selected file out. `types` select by type, and `None` means every artefact
    matches, with a type or with none. Each path is read as a place is.
    """

    paths: tuple[Place, ...] | None
    exclude: tuple[Place, ...]
    types: frozenset[str] | None


def covering_rule_sets(discovery: Discovery) -> dict[str, tuple[str, ...]]:
    """The rule sets whose scope covers each artefact (COR-051 point 2).

    Keyed by an artefact's location: the paths of the rule-set files whose scope
    covers it, in path order. An artefact no scope covers is not a key. An
    artefact is in a scope when `paths` and `types` both select it and `exclude`
    does not leave it out. Each path is read as a place is
    (`listed_files_in_place`), never matched by another rule. A type is read from
    the one resolution (`Discovery.types`): an artefact counts as its type, or
    as each type in contention while a tie stands (COR-056 point 3). A rule-set
    file is one the location rule claims, and a set without a scope covers
    nothing.
    """
    types = discovery.types
    paths = sorted({artefact.path for artefact in discovery.artefacts})
    covering: dict[str, list[str]] = {}
    for found in discovery.files:  # by path
        scope = _scope(found)
        if scope is None:
            continue
        selected = set(paths) if scope.paths is None else _matched(scope.paths, paths)
        left_out = _matched(scope.exclude, paths)
        for artefact in discovery.artefacts:
            if artefact.path not in selected or artefact.path in left_out:
                continue
            if scope.types is not None and not types.of(artefact).counts_as & scope.types:
                continue
            covering.setdefault(artefact.location, []).append(found.path)
    return {location: tuple(rule_sets) for location, rule_sets in covering.items()}


def _matched(places: Iterable[Place], paths: Sequence[str]) -> set[str]:
    """The files of `paths` one of `places` matches, each read as a place is."""
    return {path for place in places for path in listed_files_in_place(place, paths)}


def _scope(found: DiscoveredFile) -> Scope | None:
    """A rule-set file's scope, or `None` for a file that is no rule set, or a set
    without a scope.

    A plain list is the scope's `paths` (COR-051 point 2). Read forgivingly, as
    discovery reads every declaration (`_texts`): an entry that is not text is
    passed over, and a type its schema refuses too. A key whose entries are all
    passed over selects nothing, and a mapping with neither `paths` nor `types`
    covers nothing. The rule-set pass judges the shape.
    """
    if found.rule_set is None or found.front_matter is None:
        return None
    raw = found.front_matter.get(SCOPE_KEY)
    if raw is None:
        return None
    source = found.rule_set.place.source

    def places(value: Any, pointer: str) -> tuple[Place, ...]:
        return tuple(
            Place(
                pattern=entry,
                declaration=SettingsPath(
                    value=entry,
                    resolved=entry,
                    file=found.path,
                    pointer=f"{pointer}/{index}",
                    source=source,
                ),
            )
            for index, entry in _texts(value)
        )

    if not isinstance(raw, Mapping):
        return Scope(paths=places(raw, f"/{SCOPE_KEY}"), exclude=(), types=None)
    scope = cast("Mapping[str, Any]", raw)
    if "paths" not in scope and TYPES_KEY not in scope:
        return None
    return Scope(
        paths=places(scope.get("paths"), f"/{SCOPE_KEY}/paths") if "paths" in scope else None,
        exclude=places(scope.get("exclude"), f"/{SCOPE_KEY}/exclude"),
        types=(
            frozenset(
                value for _index, value in _texts(scope.get(TYPES_KEY)) if _TYPE.fullmatch(value)
            )
            if TYPES_KEY in scope
            else None
        ),
    )


# --- the reading document: `pkit friction artefacts` ---------------------

#: The version of the document `artefacts_document` returns. A change a reader
#: could break against — a key removed, renamed or given another meaning —
#: raises it; a key added does not.
ARTEFACTS_SCHEMA_VERSION = 1

#: Why a declared place or held folder holds no files: a capability declaration
#: discovery cannot read in the package schema's shape, or one that leaves the
#: repository; and, for a held folder only, one that oversteps its bounds
#: (`held_folders`, COR-050 point 1).
SKIP_MALFORMED = "malformed"
SKIP_OUTSIDE = "outside-repository"
SKIP_OVERLAP = "overlap"

#: What a place must match to enclose a documentation root: a document directly
#: in the root and one three folders beneath it, read as the place reads a
#: listing (`listed_files_in_place`).
_ENCLOSING_PROBES = ("__probe__.md", "__a__/__b__/__probe__.md")


def unreadable_configuration(target_root: Path, tree: RepositoryTree | None = None) -> str | None:
    """Why the backbone configuration cannot be read, or `None` when it can.

    Discovery reads the file forgivingly (COR-048 point 4), so one that does not
    parse reads as no places at all. The reading command refuses it instead: a
    script reading its document could not tell nothing declared from nothing
    readable. An absent or empty file is the zero-configuration state, never
    unreadable. The configuration pass reports the file whole. With a `tree`,
    the file is the one that state holds.
    """
    path = project_config_path(target_root)
    rel = path.relative_to(target_root).as_posix()
    try:
        if tree is None:
            if not path.is_file():
                return None
            text = path.read_text(encoding="utf-8")
        else:
            raw = tree.read_bytes([rel]).get(rel)
            if raw is None:
                return None
            text = raw.decode("utf-8")
        data = _yaml.load(text)
    except (OSError, UnicodeDecodeError) as exc:
        return f"the configuration {rel} cannot be read: {exc}"
    except YAMLError as exc:
        return f"the configuration {rel} does not parse as YAML: {yaml_reason(exc)}"
    if data is not None and not isinstance(data, Mapping):
        return f"the configuration {rel} is not a mapping of keys to values"
    return None


def artefacts_document(target_root: Path, tree: RepositoryTree | None = None) -> dict[str, Any]:
    """The declared places, the files they hold and the artefacts in them, as one
    stable document — what `pkit friction artefacts --json` prints.

    One run of discovery over the working tree's one listing — the settings,
    the walk and every file's reading are this module's, never computed again —
    so a capability's script reads where artefacts are through it rather than
    re-reading the declarations or walking the places itself (ADR-057 points 1
    and 2). With a `tree` — a commit — the same run reads that state instead:
    its configuration and roots, its installed capabilities and their places,
    its files and which folders hold rule sets; what discovery reads from the
    working tree whichever state it walks (which files are synced copies, where
    a link leads) is read from the working tree here too. The document holds:

    - `roots`: the two documentation roots, by audience (COR-049 point 1).
    - `places`: every declared place in walk order — the project's, then each
      capability's by name, each in written order, a malformed capability
      declaration where it was written — then each rule-set folder the location
      rule names that no declaration already is (COR-051 point 2). Each with its
      declaration (`source`, `declared`, `file`, `pointer`), the path `written`,
      the `location` it names (`name`, `path`, `root`), the resolved `path`,
      `rule_sets` (the component owning the rule sets in it) when it holds rule
      sets, the documentation roots it `encloses`, the `files` it matches and
      the `synced` copies it matches but are never walked, `skipped` — why
      it holds nothing (`malformed`, `outside-repository`), with the detail —
      and the `type` it gives, or `None` (COR-056 point 2).
    - `files`: every Markdown file the walk read, by path, with the `places`
      that match it (indices into `places`, the first the one it was read
      under), the rule-set place that claims it (`rule_set`), whether
      `friction.exclude` leaves it out (`excluded`), its front matter's own
      `fields` (as written, the container left out; `null` without a front-matter
      mapping) and why it is `unreadable`, if it is.
    - `artefacts`: every artefact, in walk order, with its `path`, `id`, `kind`
      (`document` or `entry`), `location`, `place`, `rule_set`, whether it
      carries the `container` and a `friction` block, its `anchors` by kind as
      its friction block lists them (the values that are text, in written
      order), its `unanchored_because` — the reason its block gives for having
      no anchors, whitespace folded, or `None` (COR-050 point 1) — its own
      `fields` (its front matter or entry, as written, the container left
      out), its `span` — for an entry, the lines of its file its section
      spans, `{first_line, last_line}`, exactly the text friction compares as
      its body (`Artefact.span`), else `None` — and `in_scope_of`, the paths
      of the rule-set files whose scope covers it (`covering_rule_sets`).
      Both keys were added within version 1, and so were its type's four
      (COR-056 point 6; `Discovery.types`): its `type`, the `type_place` that
      gave it (an index into `places`, `None` for a rule and with no type),
      the `type_conflict` while a tie stands (each tied type it counts as,
      `{type, place}`), and its `ranked_places`, every place that matches its
      file in COR-056 point 3's order (`{place, rank}`, places that rank
      equal sharing a rank). Its `part_anchors`, added within version 1 too:
      each anchor that names a part of a file, with the span that part
      resolves to (`_part_anchors`): an entry's section, a document's section
      or its lead, read through the one reading of an artefact anchor's part
      (`artefact_parts`), or a record's point, read through the one reading of
      a record's points (`record_points`).
    - `types`: every declared type by its full name — the backbone's own and
      each installed component's type registry — with its `component`,
      `name`, `description`, `kind_field` and `project_places`. Added within
      version 1.
    - `held`: every folder of held documents a capability declares (COR-050
      point 1), in declaration order — each capability's by name, in written
      order, a malformed declaration where it was written — declared as a place
      is: `source`, `file`, `pointer`, the path `written`, the `location` it
      lies within, the resolved `path`, the `files` it holds (none is walked by
      any place), and `skipped` — why it holds nothing (`malformed`,
      `outside-repository`, `overlap`), with the detail. A folder holding
      nothing because nothing is in it yet is listed with no files.
    - `held_files`: every file a held folder holds, by path, with the folder
      holding it (`held`, an index into `held`), the `places` that match it and
      so did not walk it (indices into `places`), whether `friction.exclude`
      leaves it out (`excluded`) — its owner then counts it no more than the
      measures count an excluded artefact — its front matter's own `fields`
      and why it is `unreadable`, if it is.
    """
    settings = read_friction_settings(target_root, tree)
    discovery = discover_artefacts(target_root, settings, tree)
    if tree is None:
        roots = docs_roots.resolve_roots(target_root)
    else:
        config_rel = project_config_path(target_root).relative_to(target_root).as_posix()
        config = _mapping_loader(target_root, tree)(config_rel)
        roots = docs_roots.roots_from(config.get(docs_roots.DOCS_KEY))
    declared = declared_places(settings)
    in_order: list[tuple[tuple[int, str, int], Place | MalformedDeclaration]] = [
        (_declaration_order(p.source, p.declaration.pointer), p) for p in declared
    ]
    in_order += [(_declaration_order(m.source, m.pointer), m) for m in settings.malformed_places]
    in_order.sort(key=lambda item: item[0])
    entries: list[Place | MalformedDeclaration] = [entry for _order, entry in in_order]
    entries += [p for p in discovery.places if p not in frozenset(declared)]
    index = {entry: i for i, entry in enumerate(entries) if isinstance(entry, Place)}

    files_of: dict[Place, list[str]] = {}
    for found in discovery.files:
        for place in found.places:
            files_of.setdefault(place, []).append(found.path)
    synced_of: dict[Place, list[str]] = {}
    for match in discovery.synced:
        synced_of.setdefault(match.place, []).append(match.path)
    rule_sets = {r.place: r for r in discovery.rule_set_places}

    def rule_set_index(rule_set: RuleSetPlace | None) -> int | None:
        return index[rule_set.place] if rule_set is not None else None

    held_order: list[tuple[tuple[int, str, int], HeldFolder | MalformedDeclaration]] = [
        (_declaration_order(f.place.source, f.declaration.pointer), f)
        for f in discovery.held_folders
    ]
    held_order += [(_declaration_order(m.source, m.pointer), m) for m in settings.malformed_held]
    held_order.sort(key=lambda item: item[0])
    held_entries = [entry for _order, entry in held_order]
    held_index = {entry: i for i, entry in enumerate(held_entries)}
    held_of: dict[HeldFolder, list[str]] = {}
    for held in discovery.held:
        held_of.setdefault(held.folder, []).append(held.path)
    in_scope_of = covering_rule_sets(discovery)
    types = discovery.types
    anchored_points = _AnchoredPoints(target_root, tree)

    return {
        "schema_version": ARTEFACTS_SCHEMA_VERSION,
        "roots": {
            audience: roots.for_audience(audience)[0].as_posix()
            for audience in docs_roots.AUDIENCES
        },
        "places": [
            _malformed_entry(entry)
            if isinstance(entry, MalformedDeclaration)
            else _place_entry(
                target_root,
                entry,
                declared=position < len(in_order),
                rule_set=rule_sets.get(entry),
                roots=roots,
                files=files_of.get(entry, []),
                synced=synced_of.get(entry, []),
                type_=types.places.get(entry),
            )
            for position, entry in enumerate(entries)
        ],
        "files": [
            {
                "path": found.path,
                "places": [index[place] for place in found.places],
                "rule_set": rule_set_index(found.rule_set),
                "excluded": found.excluded_by is not None,
                "fields": _own_fields(found.front_matter),
                "unreadable": found.unreadable,
            }
            for found in discovery.files
        ],
        "artefacts": [
            {
                "path": artefact.path,
                "id": artefact.id,
                "kind": artefact.kind.value,
                "location": artefact.location,
                "place": index[artefact.place],
                "rule_set": rule_set_index(artefact.rule_set),
                "container": artefact.has_container,
                "friction": artefact.has_friction_block,
                "anchors": {kind: list(values) for kind, values in artefact.anchors.items()},
                "unanchored_because": artefact.unanchored_because,
                "fields": _own_fields(artefact.carrier),
                "span": _span_entry(artefact.span),
                "part_anchors": _part_anchors(discovery, artefact, anchored_points),
                "in_scope_of": list(in_scope_of.get(artefact.location, ())),
                **_type_entry(types.of(artefact), index),
            }
            for artefact in discovery.artefacts
        ],
        "types": {
            name: {
                "component": declared.owner,
                "name": declared.name,
                "description": declared.description,
                "kind_field": declared.kind_field,
                "project_places": declared.project_places,
            }
            for name, declared in types.registry.items()
        },
        "held": [
            _malformed_held_entry(entry)
            if isinstance(entry, MalformedDeclaration)
            else _held_entry(entry, held_of.get(entry, []))
            for entry in held_entries
        ],
        "held_files": [
            {
                "path": held.path,
                "held": held_index[held.folder],
                "places": [index[place] for place in held.places],
                "excluded": held.excluded_by is not None,
                "fields": _own_fields(held.front_matter),
                "unreadable": held.unreadable,
            }
            for held in discovery.held
        ],
    }


def _declaration_order(source: str, pointer: str) -> tuple[int, str, int]:
    """Where a declaration sits in walk order: the project's first, then each
    capability's by name, each in written order (its pointer's last token)."""
    last = pointer.rsplit("/", 1)[-1]
    return (0 if source == "project" else 1, source, int(last) if last.isdigit() else -1)


def _place_entry(
    target_root: Path,
    place: Place,
    *,
    declared: bool,
    rule_set: RuleSetPlace | None,
    roots: docs_roots.Roots,
    files: Sequence[str],
    synced: Sequence[str],
    type_: str | None,
) -> dict[str, Any]:
    declaration = place.declaration
    skipped = None
    if not is_inside_repository(target_root, place.pattern):
        skipped = {
            "reason": SKIP_OUTSIDE,
            "detail": (
                f"{place.pattern!r} leaves the repository — absolute, climbing above the "
                f"root, or resolving outside it through a link — so nothing under it is walked"
            ),
        }
    return {
        "source": declaration.source,
        "declared": declared,
        "file": declaration.file,
        "pointer": declaration.pointer,
        "written": declaration.value,
        "location": _location_entry(declaration.location),
        "path": place.pattern,
        "rule_sets": {"component": rule_set.component} if rule_set is not None else None,
        "encloses": [
            audience
            for audience in docs_roots.AUDIENCES
            if _encloses(place, roots.for_audience(audience)[0].as_posix())
        ],
        "files": list(files),
        "synced": list(synced),
        "skipped": skipped,
        "type": type_,
    }


def _type_entry(resolved: ArtefactType, index: Mapping[Place, int]) -> dict[str, Any]:
    """An artefact's type as the document gives it: `type`, `type_place`,
    `type_conflict` and `ranked_places` (COR-056 point 6)."""
    return {
        "type": resolved.type,
        "type_place": index[resolved.place] if resolved.place is not None else None,
        "type_conflict": [
            {"type": given, "place": index[place]} for given, place in resolved.conflict
        ],
        "ranked_places": [
            {"place": index[ranked.place], "rank": ranked.rank} for ranked in resolved.places
        ],
    }


def _held_entry(folder: HeldFolder, files: Sequence[str]) -> dict[str, Any]:
    """A folder of held documents as the document declares it, beside the places."""
    declaration = folder.declaration
    skipped = folder.skipped
    return {
        "source": declaration.source,
        "file": declaration.file,
        "pointer": declaration.pointer,
        "written": declaration.value,
        "location": _location_entry(declaration.location),
        "path": folder.place.pattern,
        "files": list(files),
        "skipped": {"reason": skipped.reason, "detail": skipped.detail} if skipped else None,
    }


def _malformed_held_entry(declaration: MalformedDeclaration) -> dict[str, Any]:
    return {
        "source": declaration.source,
        "file": declaration.file,
        "pointer": declaration.pointer,
        "written": None,
        "location": None,
        "path": None,
        "files": [],
        "skipped": {"reason": SKIP_MALFORMED, "detail": declaration.reason},
    }


def _part_anchors(
    discovery: Discovery, artefact: Artefact, points: _AnchoredPoints
) -> list[dict[str, Any]]:
    """Each anchor of `artefact` that names a part of a file, with the span that part
    resolves to: by kind name, then each kind's values in the order the block writes
    them, as the document's sorted `anchors` shows them.

    - **An `artefact` anchor** names a part when the artefact it resolves to is
      a collection entry, whose content is its data and the body section headed
      by its id (COR-050 point 1); a rule is one (COR-051 point 2). Its `span`
      is its section's lines as the entry's own `span` gives them, `None` for an
      entry with no section. It names a part too when it names one section of a
      document or its lead (COR-050 point 2). Its `span` is then the lines that
      section or lead spans, `None` for an empty lead. Either resolves as the
      friction checks resolve it (`artefact_parts.anchored_part`).
    - **A `record` anchor** names a part when it names one point of the record
      (COR-050 point 2), found as the friction checks find it (`_AnchoredPoints`).

    Each is `{kind, value, path, span}`, `path` the file the part lies in. An
    anchor on a whole document, a whole file or a whole record, a dead,
    ambiguous or refused anchor and an anchor of another kind name no part, so
    none is listed. The document lists a record's points only where an anchor
    names one.
    """
    # The change check imports this module; the reading of an anchor's part imports it too.
    from project_kit.artefact_parts import PartState, anchored_part

    found: list[dict[str, Any]] = []
    for kind in sorted(artefact.anchors):
        for value in artefact.anchors_of_kind(kind):
            if kind == "artefact":
                part = anchored_part(discovery, value, points.record_named)
                target = part.target
                if target is None or part.state not in (PartState.WHOLE, PartState.LIVE):
                    continue
                if part.state is PartState.LIVE:
                    span = _span_entry(part.span)
                elif target.kind is ArtefactKind.ENTRY:
                    span = _span_entry(target.span)
                else:
                    continue  # a whole document
                found.append({"kind": kind, "value": value, "path": target.path, "span": span})
            elif kind == "record":
                part = points.part(value)
                if part is not None:
                    found.append(part)
    return found


class _AnchoredPoints:
    """The records the point anchors of the artefacts document name, each read once from
    the state the document reads, its points through `record_points` (ADR-057 point 2).

    A record anchor's file is found by the friction checks' resolver of it
    (`friction_check.record_file`), over that state's listing, and what an anchor
    on one point finds in it by `RecordPoints.anchored` (COR-050 point 7):

    - **a live point** gives the lines of the record's file its section spans
      (`RecordPoints.span`), the section the checks compare. What else the point
      stands on, the record's fields and the parts every point shares, has no
      span here (COR-050 point 5).
    - **a retired point** gives `None`. It is no dead anchor, so it is listed,
      and it stands on nothing, so it spans no lines (COR-050 points 5 and 7).
    - **a dead anchor**, on a record or a point the state does not hold or on a
      record whose points are a list, and **an ambiguous one**, on an id two
      live points share, name no part.

    The working tree is listed only when an anchor names a point, through its
    one listing (`working_tree`), which a run shares with discovery.
    """

    def __init__(self, target_root: Path, tree: RepositoryTree | None) -> None:
        self.root = target_root
        self.tree = tree
        self._listing: RepositoryTree | None = None
        self._files: frozenset[str] | None = None
        self._records: dict[str, RecordPoints | None] = {}
        self._named: dict[str, str | None] = {}

    def record_named(self, path: str) -> str | None:
        """The record anchor that names the file at `path`, as the friction checks read it
        (`friction_check.record_naming`), read once: a section or the lead of such a file
        is refused (COR-050 point 2)."""
        from project_kit.friction_check import record_naming

        if path not in self._named:
            self._named[path] = record_naming(self.root, path)
        return self._named[path]

    def part(self, value: str) -> dict[str, Any] | None:
        """The part the record anchor `value` names, `{kind, value, path, span}`, or `None`
        when it names a whole record or no part at all."""
        record, point_id = split_anchor(value)
        if point_id is None:
            return None
        # The change check imports this module; the resolver of a record anchor's file is its.
        from project_kit.friction_check import record_file

        rel = record_file(self.root, self.files, record)
        if rel is None:
            return None
        points = self._read(rel)
        if points is None:
            return None
        found = points.anchored(point_id)
        point = points.point(point_id)
        if found.state is PointState.LIVE and point is not None:
            span = _span_entry(points.span(point))
        elif found.state is PointState.RETIRED:
            span = None
        else:
            return None
        return {"kind": "record", "value": value, "path": rel, "span": span}

    @property
    def listing(self) -> RepositoryTree:
        """The state's listing: the commit's, or the working tree's one listing."""
        if self._listing is None:
            self._listing = self.tree if self.tree is not None else working_tree(self.root)
        return self._listing

    @property
    def files(self) -> frozenset[str]:
        if self._files is None:
            self._files = frozenset(self.listing.files())
        return self._files

    def _read(self, rel: str) -> RecordPoints | None:
        """The record at `rel`, its points read once, or `None` when it is no text."""
        if rel not in self._records:
            raw = self.listing.read_bytes([rel]).get(rel)
            self._records[rel] = None if raw is None else read_points_bytes(raw)
        return self._records[rel]


def _span_entry(span: SectionSpan | None) -> dict[str, int] | None:
    """A part's span as the document gives it, or `None`."""
    if span is None:
        return None
    return {"first_line": span.first_line, "last_line": span.last_line}


def _location_entry(location: PlaceLocation | None) -> dict[str, Any] | None:
    """The documentation location a capability's place or held folder names, or `None`."""
    if location is None:
        return None
    return {"name": location.name, "path": location.path, "root": location.root}


def _malformed_entry(declaration: MalformedDeclaration) -> dict[str, Any]:
    return {
        "source": declaration.source,
        "declared": True,
        "file": declaration.file,
        "pointer": declaration.pointer,
        "written": None,
        "location": None,
        "path": None,
        "rule_sets": None,
        "encloses": [],
        "files": [],
        "synced": [],
        "skipped": {"reason": SKIP_MALFORMED, "detail": declaration.reason},
        "type": None,
    }


def _encloses(place: Place, root: str) -> bool:
    """Whether `place` reaches every document of the folder `root`: it matches a
    document directly in it and one three folders beneath it."""
    probes = [probe if root == "." else f"{root}/{probe}" for probe in _ENCLOSING_PROBES]
    return len(listed_files_in_place(place, probes)) == len(probes)


def _own_fields(carrier: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """A front matter's or an entry's own fields: everything but the container."""
    if carrier is None:
        return None
    return {key: value for key, value in carrier.items() if key != CONTAINER_KEY}


def render_artefacts_json(document: Mapping[str, Any]) -> str:
    """The document as stable JSON: keys sorted, the same bytes for the same state."""
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n"


def render_artefacts_human(document: Mapping[str, Any]) -> str:
    """One line per place, then the counts of files and artefacts, then — when a
    component declares any — one line per held folder, with the files it holds."""
    places = document["places"]
    lines = [f"{len(places)} place(s):"]
    for place in places:
        owner = place["source"] if place["declared"] else f"{place['source']}, rule sets"
        line = _declaration_line(place, owner)
        if place["synced"]:
            line += f"; {len(place['synced'])} synced copy(ies) not walked"
        lines.append(_skipped(place, line))
    files = document["files"]
    artefacts = document["artefacts"]
    lines.append(
        f"{len(files)} file(s): {sum(1 for f in files if f['excluded'])} excluded, "
        f"{sum(1 for f in files if f['unreadable'] is not None)} unreadable."
    )
    lines.append(
        f"{len(artefacts)} artefact(s): {sum(1 for a in artefacts if a['container'])} carrying "
        f"the `{CONTAINER_KEY}` container, {sum(1 for a in artefacts if a['friction'])} with a "
        f"`{FRICTION_KEY}` block."
    )
    held = document["held"]
    if held:
        lines.append(f"{len(held)} held folder(s), whose files no place walks:")
        lines += [_skipped(entry, _declaration_line(entry, entry["source"])) for entry in held]
    return "\n".join(lines) + "\n"


def _declaration_line(entry: Mapping[str, Any], owner: str) -> str:
    """A declared place's or held folder's line: where, whose, the type a place
    gives, how many files."""
    where = entry["path"]
    if where is None:
        where = f"{entry['file']} {entry['pointer']}"
    if entry["location"] is not None:
        owner += f", location {entry['location']['name']}"
    if entry.get("type") is not None:
        owner += f", type {entry['type']}"
    return f"  {where}  ({owner})  {len(entry['files'])} file(s)"


def _skipped(entry: Mapping[str, Any], line: str) -> str:
    """`line`, with why the declaration holds nothing, when it does not."""
    skipped = entry["skipped"]
    if skipped is None:
        return line
    return f"{line}; skipped, {skipped['reason']}: {skipped['detail']}"
