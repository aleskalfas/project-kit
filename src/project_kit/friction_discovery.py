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
  `{path, location?}` (the package schema's `friction-place`): with
  `location`, inside that entry of the document locations it declares — where
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
  `rules` map, one artefact per rule. A plain YAML file in a place is not a
  document (ADR-056 point 2). `parse_artefacts` is the reading of one file's
  text this walk applies; the whole-repository check applies it to a file's
  earlier versions too, so history is read by the same rule as the present.
  A text is read whatever its line endings (`universal_newlines`, in
  `split_front_matter`), so a clone that checks files out with `\\r\\n` finds
  the blocks and the content one with `\\n` finds; a file mixing them is
  recorded (`DiscoveredFile.mixed_line_endings`) for the validation pass.
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
  every artefact with its anchors, and the held folders, declared as places
  are, with every file each holds — of the working tree, or of a commit.
  `pkit friction artefacts --json` prints it, and a capability's script reads
  where artefacts are through it, at head or at another state, never by
  walking the places or listing a commit itself (ADR-057 points 1 and 2).

Nothing here computes friction: the checks (`friction_check`) read the model
this module produces. The listing of the working tree has its home in
`working_tree`; the git plumbing behind a commit lives with the checks.
"""

from __future__ import annotations

import functools
import io
import json
import os
import re
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, Protocol, cast

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from project_kit import command_runner, docs_roots, lifecycle_ownership, validators
from project_kit.backbone_schemas import CONTAINER_KEY, as_written
from project_kit.line_breaks import line_break, universal_newlines
from project_kit.manifest import read_backbone_manifest
from project_kit.report_context import project_config_path
from project_kit.working_tree import WorkingTree, working_tree

# The key this functionality owns in the backbone configuration and in a
# capability's package metadata — the same word as the block and the command
# group (COR-050 point 1, COR-053 point 10).
FRICTION_KEY = "friction"

# The key of the block an artefact with nothing to anchor to carries instead of
# anchors: the reason a person accepted it with none (COR-050 point 1).
UNANCHORED_BECAUSE_KEY = "unanchored-because"

# The package schema's shape a capability place is read in: `{path, location?}`,
# `location` naming an entry of the capability's `docs.locations`, which
# `docs_roots.read_capability_locations` resolves.
PATH_KEY = "path"
LOCATION_KEY = "location"

# The lists of a capability's `friction` block written in that shape, and what
# a finding calls one entry of each: its places, and its folders of held
# documents (COR-050 point 1).
PLACES_KEY = "places"
HELD_KEY = "held"
_ENTRY_NOUN = {PLACES_KEY: "place", HELD_KEY: "held folder"}

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

# A signpost in a rule-set folder describes the folder; it is not a rule set,
# as a README in a decision-record folder is not a record.
RULE_SETS_SIGNPOST = "README.md"

# Directories a glob never descends into: git's own store.
_SKIPPED_TOP_LEVEL = frozenset({".git"})

_GLOB_CHARS = frozenset("*?[")

_FRONT_MATTER_FENCE = re.compile(r"^---[ \t]*$", re.MULTILINE)
_HEADING = re.compile(r"^(#{1,6})[ \t]+(.*?)[ \t]*#*[ \t]*$", re.MULTILINE)
# What continues an id past a heading's opening characters: a word character, or a hyphen or
# a dot joined to one — so `uc-login` is not the id opening `uc-login-sso` or `uc-login.v2`.
_ID_CONTINUES = re.compile(r"\w|[-.]\w")

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
    """

    value: str
    resolved: str
    file: str
    pointer: str
    source: str  # "project" or "capability:<name>"
    location: PlaceLocation | None = None

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

    @property
    def roots(self) -> dict[str, str]:
        """The documentation roots by audience, repository-relative (COR-049 point 1)."""
        return {docs_roots.INTERNAL_KEY: self.internal_root, docs_roots.USER_KEY: self.user_root}

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

    places = list(project_paths(PLACES_KEY))
    surface = list(project_paths("surface"))
    exclude = list(project_paths("exclude"))
    held: list[SettingsPath] = []
    malformed_places: list[MalformedDeclaration] = []
    malformed_surface: list[MalformedDeclaration] = []
    malformed_held: list[MalformedDeclaration] = []

    for name in installed_capability_names(target_root, tree):
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
    )


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

    Each entry is an object `{path, location?}`. With `location`, `path` lies
    inside that entry of the capability's `docs.locations`, where `locations`
    — the one reading, `docs_roots.read_capability_locations` — puts it: its
    recorded location, else its declared `{path, root?}` under the root it
    names (COR-049 points 4 and 5). Without one, `path` is repository-relative.
    A held folder lies within one of the capability's locations, so it names
    one, and its `path` is a folder inside it (`_resolve_capability_place`).
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
        return _Unresolved(f"the {noun} is {_shape(entry)}, not an object `{{path, location?}}`")
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


def rule_set_files(target_root: Path, places: Sequence[RuleSetPlace]) -> dict[Path, RuleSetPlace]:
    """Every rule-set file the places claim, with the place that claimed it.

    A Markdown file a rule-set place matches is a rule-set file, whatever it
    holds — except the folder's signpost, `README.md`. A file two places match
    is claimed by the first, so a method folder always wins over a project
    place that happens to reach into it. Keyed by the path the walk yields;
    found in the working tree's one listing, like every other artefact.
    """
    claimed: dict[Path, RuleSetPlace] = {}
    tree = working_tree(target_root) if places else None
    for rule_set_place in places:
        for path in files_in_place(target_root, rule_set_place.place, tree):
            if path.name != RULE_SETS_SIGNPOST:
                claimed.setdefault(path, rule_set_place)
    return claimed


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
    claimed: dict[str, RuleSetPlace] = {}
    for rule_set_place in rule_set_places_found:
        for rel in listed_files_in_place(rule_set_place.place, files):
            if PurePosixPath(rel).name != RULE_SETS_SIGNPOST:
                claimed.setdefault(rel, rule_set_place)
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
    texts = _document_texts(listing, [rel for _place, rel in matched] + sorted(holder))
    for place, rel in matched:
        rule_set = claimed.get(rel)
        text = texts[rel]
        if text is None:
            continue  # a link: never read as a document
        excluded_by = settings.exclusion(rel)
        front_matter: Mapping[str, Any] | None = None
        mixed = False
        if isinstance(text, _ReadFailure):
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
    rel: str, folder: HeldFolder, places: tuple[Place, ...], text: str | _ReadFailure
) -> HeldFile:
    """A held file, read for its front matter and every friction block in it.

    Its front matter is parsed as a file in a place is (`_parsed_front_matter`),
    and searched whole for a friction block (`_friction_blocks`): no reading of
    it as an artefact is assumed, so a block is found wherever it is written —
    as a document's, an entry's, a rule's, or deeper.
    """
    if isinstance(text, _ReadFailure):
        return HeldFile(rel, folder, places, front_matter=None, unreadable=text.reason, blocks=())
    front_matter, _body, reason = _parsed_front_matter(text)
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
class _ReadFailure:
    reason: str


def _document_texts(
    tree: RepositoryTree, rels: Sequence[str]
) -> dict[str, str | _ReadFailure | None]:
    """Each matched file's text, or why it could not be read; `None` for a link.

    The working tree is read file by file, so a file that will not open is
    reported as unreadable, whichever reader asked; a commit is read in one pass.
    """
    contents: Mapping[str, bytes | None | _ReadFailure]
    if isinstance(tree, WorkingTree):
        contents = {rel: _read_working_file(tree, rel) for rel in rels}
    else:
        contents = tree.read_bytes(rels)
    texts: dict[str, str | _ReadFailure | None] = {}
    for rel in rels:
        raw = contents.get(rel)
        if raw is None or isinstance(raw, _ReadFailure):
            texts[rel] = raw
            continue
        try:
            texts[rel] = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            texts[rel] = _ReadFailure(str(exc))
    return texts


def _read_working_file(tree: WorkingTree, rel: str) -> bytes | None | _ReadFailure:
    try:
        return tree.read_file(rel)
    except OSError as exc:
        return _ReadFailure(str(exc))


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
    are read universally (`\\r\\n` and `\\r` as `\\n`, `split_front_matter`), as
    a text file is read, whether the text came from disk or from git — so an
    artefact whose line endings changed while its text did not has the same
    content (COR-050 point 5).
    """
    _front_matter, found, reason = _read_artefacts(rel, place, text, rule_set=rule_set)
    return found, reason


def _read_artefacts(
    rel: str, place: Place, text: str, *, rule_set: RuleSetPlace | None = None
) -> tuple[Mapping[str, Any] | None, list[Artefact], str | None]:
    """`parse_artefacts`, with the file's front matter as written when it is a
    mapping: `(front_matter, artefacts, reason)`."""
    written, body, reason = _parsed_front_matter(text)
    if written is None:
        return None, [], reason
    return written, _artefacts_of_file(rel, place, written, body, rule_set=rule_set), None


def _parsed_front_matter(text: str) -> tuple[Mapping[str, Any] | None, str, str | None]:
    """A file's front matter as written when it is a mapping, its body, and why the
    front matter does not parse, if it does not: `(front_matter, body, reason)`.
    Both are read with `\\n` line breaks, whatever the file's (`split_front_matter`)."""
    front_matter, body = split_front_matter(text)
    if front_matter is None:
        return None, body, None
    try:
        data = _yaml.load(io.StringIO(front_matter))
    except YAMLError as exc:
        return None, body, _yaml_reason(exc)
    if not isinstance(data, Mapping):
        return None, body, None
    return as_written(data), body, None


def _artefacts_of_file(
    rel: str,
    place: Place,
    front_matter: Mapping[str, Any],
    body: str,
    *,
    rule_set: RuleSetPlace | None = None,
) -> list[Artefact]:
    """One document, or one artefact per entry of a collection file.

    A rule-set file (`rule_set` given) is a collection whose entries are the
    values of its `rules` map, each a rule (COR-051 point 2); its other keys
    are the set's own data, never entries.

    Otherwise, a file is a collection when its front matter does not itself
    carry the container but at least one of its top-level mapping values does
    (COR-050 point 1: "a collection file whose front matter maps entries by
    id"). Every top-level mapping value is then an entry — including those
    without a container, which are unanchored artefacts. Otherwise the file is
    one document.
    """
    if rule_set is not None:
        return _rules_of_file(rel, place, front_matter, body, rule_set)
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
            )
        ]
    return [
        _artefact(
            artefact_id=entry_id,
            rel=rel,
            kind=ArtefactKind.ENTRY,
            place=place,
            carrier=entry,
            body=entry_section(body, entry_id),
        )
        for entry_id, entry in entries.items()
    ]


def _rules_of_file(
    rel: str, place: Place, front_matter: Mapping[str, Any], body: str, rule_set: RuleSetPlace
) -> list[Artefact]:
    """One artefact per rule of a rule-set file, in written order.

    A rule's content is its data entry together with the body section headed
    by its id (COR-051 point 2). An entry that is not a mapping carries no
    fields to read; the rule-set pass reports its shape.
    """
    rules = front_matter.get(RULES_KEY)
    if not isinstance(rules, Mapping):
        return []
    return [
        _artefact(
            artefact_id=rule_id,
            rel=rel,
            kind=ArtefactKind.ENTRY,
            place=place,
            carrier=entry,
            body=entry_section(body, rule_id),
            rule_set=rule_set,
        )
        for rule_id, entry in rules.items()
        if isinstance(entry, Mapping)
    ]


def _artefact(
    *,
    artefact_id: str,
    rel: str,
    kind: ArtefactKind,
    place: Place,
    carrier: Mapping[str, Any],
    body: str,
    rule_set: RuleSetPlace | None = None,
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
    )


# --- Markdown -----------------------------------------------------------


def split_front_matter(text: str) -> tuple[str | None, str]:
    """(front-matter YAML, body) for a Markdown text; `(None, text)` when it has none.

    Front matter is a leading `---` line closed by the next `---` line. Line
    endings are read universally first (`universal_newlines`), so a text
    written with `\\r\\n` has the front matter the same text written with `\\n`
    has, and both parts — `text` too, when there is none — come back with `\\n`
    line breaks: the one reading of a file's front matter and body. The YAML
    is returned as text so the caller can report a parse failure against the
    file.
    """
    text = universal_newlines(text)
    if not text.startswith("---"):
        return None, text
    first_line_end = text.find("\n")
    if first_line_end == -1 or text[:first_line_end].rstrip() != "---":
        return None, text
    closing = _FRONT_MATTER_FENCE.search(text, first_line_end + 1)
    if closing is None:
        return None, text
    return text[first_line_end + 1 : closing.start()], text[closing.end() :].lstrip("\n")


def entry_section(body: str, entry_id: str) -> str:
    """The body section headed by `entry_id` (COR-050 point 1), or `""`.

    A heading that opens with the id as a whole token — the id, then the end
    of the heading, whitespace, or punctuation that does not continue an id
    (`_ID_CONTINUES`) — opens the section; it runs to the next heading of the
    same or a higher level.
    """
    headings = list(_HEADING.finditer(body))
    for index, match in enumerate(headings):
        title = match.group(2).strip()
        if title.startswith(entry_id) and not _ID_CONTINUES.match(title, len(entry_id)):
            level = len(match.group(1))
            end = len(body)
            for later in headings[index + 1 :]:
                if len(later.group(1)) <= level:
                    end = later.start()
                    break
            return body[match.start() : end].rstrip("\n") + "\n"
    return ""


def _yaml_reason(exc: YAMLError) -> str:
    problem = getattr(exc, "problem", None) or str(exc).splitlines()[0]
    mark = getattr(exc, "problem_mark", None)
    if mark is not None:
        return f"{problem} at line {mark.line + 1} col {mark.column + 1}"
    return str(problem)


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
        return f"the configuration {rel} does not parse as YAML: {_yaml_reason(exc)}"
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
      the `synced` copies it matches but are never walked, and `skipped` — why
      it holds nothing (`malformed`, `outside-repository`), with the detail.
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
      no anchors, whitespace folded, or `None` (COR-050 point 1) — and its own
      `fields` (its front matter or entry, as written, the container left out).
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
            }
            for artefact in discovery.artefacts
        ],
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
    """A declared place's or held folder's line: where, whose, how many files."""
    where = entry["path"]
    if where is None:
        where = f"{entry['file']} {entry['pointer']}"
    if entry["location"] is not None:
        owner += f", location {entry['location']['name']}"
    return f"  {where}  ({owner})  {len(entry['files'])} file(s)"


def _skipped(entry: Mapping[str, Any], line: str) -> str:
    """`line`, with why the declaration holds nothing, when it does not."""
    skipped = entry["skipped"]
    if skipped is None:
        return line
    return f"{line}; skipped, {skipped['reason']}: {skipped['detail']}"
