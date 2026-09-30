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
- `declared_held` — the folders of **held documents** a capability declares
  (`friction.held`, COR-050 point 1): files it owns that are not artefacts,
  such as the record of an act. A held folder is written and resolved as a
  place is, and matched as a place is, but nothing in it is walked as an
  artefact: no place — a root, another component's or the project's — reads a
  held file, so neither measure counts it. Held folders are a component's
  alone; a project leaves files out with `exclude`.
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
  A file a declared place matches that is a synced copy is not walked — a
  place is never a synced tree (COR-050 point 14) — and is kept as a
  `SyncedMatch` for the validation pass to report; the question is the tree's
  own ownership predicate's (`synced_copy_test`), never re-derived here. A
  held file is not walked by any place either: it is kept as a `HeldFile`,
  with its owner and the places that match it, and read only for its front
  matter — a friction block in it is a validation finding (COR-050 point 12).
- `FrictionSettings.exclusion` — the one decision of what `friction.exclude`
  leaves out (COR-050 point 7). The walk records it on every file and
  artefact it reads (`excluded_by`), so the measures read it from the
  artefact; the checks ask it of any other path, never matching the
  patterns themselves.
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
  every artefact with its anchors, and every held file with its owner — of the
  working tree, or of a commit.
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
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, Protocol

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from project_kit import docs_roots, lifecycle_ownership
from project_kit.backbone_schemas import CONTAINER_KEY, as_written
from project_kit.manifest import read_backbone_manifest
from project_kit.report_context import project_config_path
from project_kit.working_tree import WorkingTree, working_tree

# The key this functionality owns in the backbone configuration and in a
# capability's package metadata — the same word as the block and the command
# group (COR-050 point 1, COR-053 point 10).
FRICTION_KEY = "friction"

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
    `exclusion` is the one decision of what `exclude` leaves out. `held` are
    the capabilities' folders of held documents, resolved as their places are;
    a project declares none.
    """

    mode: Any
    places: tuple[SettingsPath, ...]
    surface: tuple[SettingsPath, ...]
    exclude: tuple[SettingsPath, ...]
    internal_root: str  # the documentation root a location resolves under by default
    malformed_places: tuple[MalformedDeclaration, ...] = ()
    malformed_surface: tuple[MalformedDeclaration, ...] = ()
    held: tuple[SettingsPath, ...] = ()
    malformed_held: tuple[MalformedDeclaration, ...] = ()

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
    config = load(config_rel)
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
        malformed_places=tuple(malformed_places),
        malformed_surface=tuple(malformed_surface),
        held=tuple(held),
        malformed_held=tuple(malformed_held),
    )


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
        resolved = _resolve_capability_place(entry, locations, noun)
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
    noun: str = _ENTRY_NOUN[PLACES_KEY],
) -> tuple[str, str, tuple[str, str] | None] | _Unresolved:
    """`(path, pattern, location)` for a place — or a held folder, the `noun` a
    finding calls it — in the schema's shape, else why it is not.

    `path` is the entry's own, `pattern` the repository-relative form the walk
    follows, and `location` the `(name, where it lies)` of the location it
    names, or `None`. Whether the pattern stays inside the repository is left
    to the validation pass, which follows links on disk; here only the shape
    is judged.
    """
    if not isinstance(entry, Mapping):
        return _Unresolved(f"the {noun} is {_shape(entry)}, not an object `{{path, location?}}`")
    written = entry.get(PATH_KEY)
    path = _text_or_none(written)
    if path is None:
        if written is None:
            return _Unresolved(f"the {noun} has no `path`")
        return _Unresolved(f"the {noun}'s `path` is {_shape(written)}, not a path or glob")
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
    return path, _join_posix(folder, path), (location, folder)


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
    if tree is None:
        return lambda rel: _load_mapping(target_root / rel)

    def load(rel: str) -> dict[str, Any]:
        raw = tree.read_bytes([rel]).get(rel)
        if raw is None:
            return {}
        try:
            return _parse_mapping(raw.decode("utf-8"))
        except UnicodeDecodeError:
            return {}

    return load


def _load_mapping(path: Path) -> dict[str, Any]:
    """A YAML file as a mapping with text keys; `{}` when absent, unparsable or not a mapping."""
    if not path.is_file():
        return {}
    try:
        return _parse_mapping(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return {}


def _parse_mapping(text: str) -> dict[str, Any]:
    """YAML text as a mapping with text keys; `{}` when unparsable or not a mapping."""
    try:
        data = _yaml.load(text)
    except YAMLError:
        return {}
    if not isinstance(data, Mapping):
        return {}
    return {str(k): v for k, v in data.items()}


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


def declared_held(settings: FrictionSettings) -> tuple[Place, ...]:
    """The folders of held documents, each capability's by name in written order.

    A held folder is declared, resolved and matched as a place is — so it is
    carried as one — but it is not a place: what it matches is never walked as
    an artefact (COR-050 point 1).
    """
    return tuple(Place(pattern=h.resolved, declaration=h) for h in settings.held)


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

    No place walks it — a root, another component's or the project's — so it
    is never an artefact, and neither measure counts it. `folder` is the held
    folder holding it: the first declaration matching it, whose `source` names
    its owner. `places` are the places that match it and so left it out, in
    walk order. It is read for its front matter alone: `front_matter` as
    written when that is a mapping, `unreadable` why the file or its front
    matter could not be read, and `blocks` the location — `path`, or `path#id`
    for an entry — of every friction block in it, which validation refuses
    (COR-050 point 12).
    """

    path: str
    folder: Place
    places: tuple[Place, ...]
    front_matter: Mapping[str, Any] | None
    unreadable: str | None
    blocks: tuple[str, ...]

    @property
    def owner(self) -> str:
        return self.folder.source


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


def files_in_place(
    target_root: Path, place: Place, tree: WorkingTree | None = None
) -> list[Path]:
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


def rule_set_places(target_root: Path, settings: FrictionSettings) -> tuple[RuleSetPlace, ...]:
    """The places declared to hold rule sets, in claim order (the location rule).

    Method rule sets first: the backbone's `.pkit/rule-sets/`, then each
    installed capability's `.pkit/capabilities/<name>/rule-sets/` by name.
    Then project rule sets: `<internal root>/rule-sets/`, and every declared
    place whose path has a `rule-sets` segment. A folder the location rule
    names is a place only while it exists inside the repository, so a project
    without rule sets declares nothing; a declared place is taken as written.
    A folder the rule names has no declaring file, so its declaration names
    the folder itself.
    """
    places: list[RuleSetPlace] = []

    def folder(rel: str, component: str | None, source: str) -> None:
        if is_inside_repository(target_root, rel) and (target_root / rel).is_dir():
            declaration = SettingsPath(value=rel, resolved=rel, file=rel, pointer="", source=source)
            places.append(RuleSetPlace(Place(pattern=rel, declaration=declaration), component))

    folder(BACKBONE_RULE_SETS_DIR.as_posix(), BACKBONE_COMPONENT, BACKBONE_COMPONENT)
    for name in installed_capability_names(target_root):
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


@dataclass(frozen=True)
class ResolverCommand:
    """A command a capability registers to resolve an anchor kind (COR-050 point 2).

    `query_contract` is whether the command's registry entry declares the
    query contract (ADR-057 point 3): bounded, deterministic, read-only and
    needing no network. The declaration grants nothing; it is a claim the
    backbone requires and trusts.
    """

    kind: str
    capability: str
    command: str
    query_contract: bool = False


def refuse_resolver_without_query_contract(resolver: ResolverCommand) -> str | None:
    """Why `resolver` may not run, or `None` when it may.

    A resolver is a query: bounded, deterministic and needing no network
    (COR-050 point 2), and read-only (ADR-057 point 3 adds it). The backbone
    admits one only when its command declares that contract (ADR-057 point 3). The declaration is trusted, not enforced:
    nothing here confines the process it would start — the residual gap the CLI
    reference states.
    """
    if resolver.query_contract:
        return None
    return (
        f"the resolver `{resolver.command}` that {resolver.capability} registers for it "
        f"does not declare the query contract (bounded, deterministic, read-only, "
        f"needing no network); a resolver runs only when it declares it"
    )


def registered_anchor_kinds(target_root: Path) -> dict[str, ResolverCommand]:
    """The anchor kinds installed capabilities register, by kind.

    Where registered kinds are looked up. No package metadata declares an
    anchor kind yet — the kind registry arrives with its own change — so this
    is empty and every kind outside `CORE_ANCHOR_KINDS` is unresolved.
    """
    del target_root  # read from each capability's package metadata once kinds are declared
    return {}


def unresolved_kind_reason(kind: str, registry: Mapping[str, ResolverCommand]) -> str | None:
    """`None` when the backbone resolves `kind`; otherwise why nothing does.

    A registered kind passes `refuse_resolver_without_query_contract` before its
    resolver could run; one that passes is still unresolved, since registered
    resolvers are not run yet — failing closed (COR-050 point 2).
    """
    if kind in CORE_ANCHOR_KINDS:
        return None
    resolver = registry.get(kind)
    if resolver is None:
        return "no installed component registers a resolver for it"
    refusal = refuse_resolver_without_query_contract(resolver)
    if refusal is not None:
        return refusal
    return (
        f"the resolver `{resolver.command}` that {resolver.capability} registers for it "
        f"is not run yet"
    )


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
    the same decision its artefacts carry.
    """

    path: str
    places: tuple[Place, ...]
    rule_set: RuleSetPlace | None
    front_matter: Mapping[str, Any] | None
    unreadable: str | None = None
    excluded_by: SettingsPath | None = None


@dataclass(frozen=True)
class Discovery:
    """What a walk of the declared places found, in deterministic order.

    `places` are the declared places followed by the rule-set places not
    already among them; `rule_set_places` every place the location rule names
    (some of them declared places). `synced` holds the files a declared place
    matched that are synced copies, which were not walked (COR-050 point 14).
    `files` holds every file the walk read, by path — a link is never read, so
    never one of them. `held` holds every file a held folder holds, by path,
    whether or not a place matches it; none of them is walked (COR-050 point 1).
    """

    settings: FrictionSettings
    places: tuple[Place, ...]
    artefacts: tuple[Artefact, ...]
    unreadable: tuple[UnreadableFile, ...]
    synced: tuple[SyncedMatch, ...] = ()
    files: tuple[DiscoveredFile, ...] = ()
    rule_set_places: tuple[RuleSetPlace, ...] = ()
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

    A file a declared place matches that is a synced copy is never walked
    under that place, whichever state is walked (`synced_copy_test`, read on
    the working tree's install state): it is recorded in `synced` for the
    validation pass, and the place's other matches are walked. A rule-set place
    is not a declared place, so a method rule set that arrives by sync is still
    read as the location rule says (COR-051 point 2).

    A file a held folder holds is walked by no place, whichever state is walked
    (COR-050 point 1): it is recorded in `held` with the folder holding it — the
    first in declaration order — and the places that match it, and read for its
    front matter alone. A link is never held, as it is never read.
    """
    settings = settings if settings is not None else read_friction_settings(target_root, tree)
    # Which rule-set folders are places is read from the working tree even when
    # `tree` names another state: a folder that exists only at that state (one
    # the change deleted outright) is not walked there. The folders are
    # existence-gated so that a project without rule sets stays dormant
    # without a repository being demanded.
    rule_set_places_found = rule_set_places(target_root, settings)
    places = declared_places(settings)
    declared = frozenset(places)
    places += tuple(r.place for r in rule_set_places_found if r.place not in places)
    held_folders = declared_held(settings)
    if not places and not held_folders:
        return Discovery(settings=settings, places=places, artefacts=(), unreadable=())
    listing = tree if tree is not None else working_tree(target_root)
    files = listing.files()
    claimed: dict[str, RuleSetPlace] = {}
    for rule_set_place in rule_set_places_found:
        for rel in listed_files_in_place(rule_set_place.place, files):
            if PurePosixPath(rel).name != RULE_SETS_SIGNPOST:
                claimed.setdefault(rel, rule_set_place)
    holder: dict[str, Place] = {}  # each held file: the folder holding it
    for folder in held_folders:
        for rel in listed_files_in_place(folder, files):
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
        if isinstance(text, _ReadFailure):
            reason: str | None = text.reason
        else:
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
            )
        )
    held = [
        _held_file(rel, holder[rel], tuple(left_out.get(rel, ())), text)
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
        held=tuple(held),
    )


def _held_file(
    rel: str, folder: Place, places: tuple[Place, ...], text: str | _ReadFailure
) -> HeldFile:
    """A held file, read for its front matter and any friction block in it.

    Read as a file in a place is read (`_read_artefacts`), so a friction block is
    found wherever the one reading would find an artefact's — the document's own,
    or an entry's — though none of what it reads becomes an artefact.
    """
    if isinstance(text, _ReadFailure):
        return HeldFile(rel, folder, places, front_matter=None, unreadable=text.reason, blocks=())
    front_matter, read_as, reason = _read_artefacts(rel, folder, text)
    blocks = tuple(a.location for a in read_as if a.has_friction_block)
    return HeldFile(rel, folder, places, front_matter, unreadable=reason, blocks=blocks)


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
    are read universally (`\\r\\n` and `\\r` as `\\n`), as a text file is read,
    whether the text came from disk or from git.
    """
    _front_matter, found, reason = _read_artefacts(rel, place, text, rule_set=rule_set)
    return found, reason


def _read_artefacts(
    rel: str, place: Place, text: str, *, rule_set: RuleSetPlace | None = None
) -> tuple[Mapping[str, Any] | None, list[Artefact], str | None]:
    """`parse_artefacts`, with the file's front matter as written when it is a
    mapping: `(front_matter, artefacts, reason)`."""
    if "\r" in text:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
    front_matter, body = split_front_matter(text)
    if front_matter is None:
        return None, [], None
    try:
        data = _yaml.load(io.StringIO(front_matter))
    except YAMLError as exc:
        return None, [], _yaml_reason(exc)
    if not isinstance(data, Mapping):
        return None, [], None
    written = as_written(data)
    return written, _artefacts_of_file(rel, place, written, body, rule_set=rule_set), None


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

    Front matter is a leading `---` line closed by the next `---` line. The
    YAML is returned as text so the caller can report a parse failure against
    the file.
    """
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

#: Why a declared place holds no files: a capability place discovery cannot
#: read in the package schema's shape, or a place that leaves the repository.
SKIP_MALFORMED = "malformed"
SKIP_OUTSIDE = "outside-repository"

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
    its files; what discovery reads from the working tree whichever state it
    walks (which folders hold rule sets, which files are synced copies, where a
    link leads) is read from the working tree here too. The document holds:

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
      order), and its own `fields` (its front matter or entry, as written, the
      container left out).
    - `held`: every file a component holds that is not an artefact (COR-050
      point 1), by path, with its owner — the held folder's declaration
      (`source`, `file`, `pointer`, `written`, `location`) — the `places` that
      match it and so did not walk it (indices into `places`), its front
      matter's own `fields` and why it is `unreadable`, if it is.
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
                "fields": _own_fields(artefact.carrier),
            }
            for artefact in discovery.artefacts
        ],
        "held": [
            {
                "path": held.path,
                "source": held.owner,
                "file": held.folder.declaration.file,
                "pointer": held.folder.declaration.pointer,
                "written": held.folder.declaration.value,
                "location": _location_entry(held.folder.declaration.location),
                "places": [index[place] for place in held.places],
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
    component holds any — the count of held documents, by owner."""
    places = document["places"]
    lines = [f"{len(places)} place(s):"]
    for place in places:
        where = place["path"]
        if where is None:
            where = f"{place['file']} {place['pointer']}"
        owner = place["source"] if place["declared"] else f"{place['source']}, rule sets"
        if place["location"] is not None:
            owner += f", location {place['location']['name']}"
        line = f"  {where}  ({owner})  {len(place['files'])} file(s)"
        if place["synced"]:
            line += f"; {len(place['synced'])} synced copy(ies) not walked"
        if place["skipped"] is not None:
            line += f"; skipped, {place['skipped']['reason']}: {place['skipped']['detail']}"
        lines.append(line)
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
        owners: dict[str, int] = {}
        for entry in held:
            owners[entry["source"]] = owners.get(entry["source"], 0) + 1
        by = ", ".join(f"{count} by {owner}" for owner, count in sorted(owners.items()))
        lines.append(f"{len(held)} held document(s), walked by no place: {by}.")
    return "\n".join(lines) + "\n"
