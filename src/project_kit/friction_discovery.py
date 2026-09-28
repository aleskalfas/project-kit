"""Artefact discovery for the friction functionality (COR-050 point 1).

The backbone looks for anchored artefacts only in the **places declared to
hold them**, so unrelated front matter elsewhere is never misread. This module
is the one reader of those declarations and the one walker of the places:

- `read_friction_settings` — the project's `friction` key in the backbone
  configuration (COR-050 point 14: mode, places, surface, exclude) and each
  installed capability's `friction.places` / `friction.surface`, read
  *forgivingly* (COR-048 point 4): a missing or oddly shaped value reads as
  absent here, and the strict judgment of its shape belongs to the
  configuration and package schemas (Tasks #981, #982). A capability place
  the reader cannot resolve is not dropped, though: it is kept as a
  `MalformedPlace`, which the validation pass reports, so a declaration the
  walk cannot follow is never silence (COR-050 point 7). What this module
  does judge — because COR-050 point 12 assigns it to validation — is done in
  `friction_validate`.
- `declared_places` — the resolved places, project first (in declaration
  order) then capabilities by name. A capability's place is an object
  `{path, location?}` (the package schema's `friction-place`): with
  `location`, inside that entry of the document locations it declares, under
  a documentation root (COR-049 point 4; COR-050 point 1); without one,
  repository-relative.
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
- `RepositoryTree` — the seam through which discovery lists and reads one
  state of the repository, matching every listing by one rule
  (`listed_files_in_place`, `compile_glob`, `pattern_matches`). Without a
  tree, discovery reads the working tree's one listing (`working_tree`):
  the files git sees, the same listing the change check (COR-050 point 6)
  reads as its head beside its base commit — so validation, the writers and
  the change check find the same artefacts in the same working tree
  (ADR-057 point 2). A link is a file of any listing, never followed and never
  read as a document.

Nothing here computes friction: the checks (`friction_check`) read the model
this module produces. The listing of the working tree has its home in
`working_tree`; the git plumbing behind a commit lives with the checks.
"""

from __future__ import annotations

import functools
import io
import os
import re
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, Protocol

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from project_kit.backbone_schemas import CONTAINER_KEY, as_written
from project_kit.manifest import read_backbone_manifest
from project_kit.report_context import project_config_path
from project_kit.working_tree import WorkingTree, working_tree

# The key this functionality owns in the backbone configuration and in a
# capability's package metadata — the same word as the block and the command
# group (COR-050 point 1, COR-053 point 10).
FRICTION_KEY = "friction"

# The documentation key of the backbone configuration (COR-049 point 1) and
# the sub-keys naming its two roots. Both roots default to `docs/`.
DOCS_KEY = "docs"
INTERNAL_ROOT_KEY = "internal"
USER_ROOT_KEY = "user"
DEFAULT_INTERNAL_ROOT = "docs"
DEFAULT_USER_ROOT = "docs"

# A capability's document sub-paths under a documentation root (COR-049 point 4).
LOCATIONS_KEY = "locations"

# The package schema's shapes a capability place is read in: a place is
# `{path, location?}`, and the `docs.locations` entry it names is
# `{path, root?}`, with `root` one of the two roots and internal when absent.
PATH_KEY = "path"
LOCATION_KEY = "location"
LOCATION_ROOT_KEY = "root"

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
class SettingsPath:
    """One path or glob a setting declares, with where it was written.

    `value` is the text as written; `resolved` the repository-relative form
    discovery walks (for a capability's place, the location prefix is already
    joined). `file` is the declaring file relative to the project root and
    `pointer` a JSON Pointer to the value in it, so a finding can name both.
    """

    value: str
    resolved: str
    file: str
    pointer: str
    source: str  # "project" or "capability:<name>"

    @property
    def is_capability(self) -> bool:
        """Declared in a capability's package metadata, not the project's configuration."""
        return self.source.startswith("capability:")


@dataclass(frozen=True)
class MalformedPlace:
    """A capability place the reader could not resolve, and why (COR-050 point 7).

    It is not among the places, so nothing under it is walked; the validation
    pass reports it. `file` is the package metadata relative to the project
    root and `pointer` a JSON Pointer to the entry — or to `friction.places`
    itself when that is not a list.
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
    """

    mode: Any
    places: tuple[SettingsPath, ...]
    surface: tuple[SettingsPath, ...]
    exclude: tuple[SettingsPath, ...]
    internal_root: str  # the documentation root a location resolves under by default
    malformed_places: tuple[MalformedPlace, ...] = ()

    @property
    def mode_or_default(self) -> str:
        if isinstance(self.mode, str) and self.mode in FRICTION_MODES:
            return self.mode
        return DEFAULT_FRICTION_MODE


def read_friction_settings(
    target_root: Path, tree: RepositoryTree | None = None
) -> FrictionSettings:
    """Read the project's and every installed capability's friction settings.

    Forgiving throughout (COR-048 point 4): an absent file, an unparsable
    file, a key of the wrong shape, or a list entry that is not text is read
    as absent. The schema passes of the configuration file and of package
    metadata refuse those; this reader only has to keep working next to them.
    A capability place is the exception: one it cannot resolve is kept in
    `malformed_places` for the validation pass (`_capability_places`).
    With a `tree`, the files are read from that state rather than from disk.
    """
    load = _mapping_loader(target_root, tree)
    config_rel = project_config_path(target_root).relative_to(target_root).as_posix()
    config = load(config_rel)
    docs = _mapping_or_empty(config.get(DOCS_KEY))
    internal_root = _text_or_default(docs.get(INTERNAL_ROOT_KEY), DEFAULT_INTERNAL_ROOT)
    roots = {
        INTERNAL_ROOT_KEY: internal_root,
        USER_ROOT_KEY: _text_or_default(docs.get(USER_ROOT_KEY), DEFAULT_USER_ROOT),
    }

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

    places = list(project_paths("places"))
    surface = list(project_paths("surface"))
    exclude = list(project_paths("exclude"))
    malformed_places: list[MalformedPlace] = []

    for name in installed_capability_names(target_root, tree):
        package_rel = CAPABILITIES_DIR / name / "package.yaml"
        package = load(package_rel.as_posix())
        found, malformed = _capability_places(name, package, package_rel.as_posix(), roots)
        places.extend(found)
        malformed_places.extend(malformed)
        cap_friction = _mapping_or_empty(package.get(FRICTION_KEY))
        locations = _capability_locations(package)
        for index, text in _texts(cap_friction.get("surface")):
            for location in locations:
                surface.append(
                    SettingsPath(
                        value=text,
                        resolved=_join_posix(internal_root, location, text),
                        file=str(package_rel),
                        pointer=f"/{FRICTION_KEY}/surface/{index}",
                        source=f"capability:{name}",
                    )
                )

    return FrictionSettings(
        mode=mode,
        places=tuple(places),
        surface=tuple(surface),
        exclude=tuple(exclude),
        internal_root=internal_root,
        malformed_places=tuple(malformed_places),
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
    name: str, package: Mapping[str, Any], package_file: str, roots: Mapping[str, str]
) -> tuple[list[SettingsPath], list[MalformedPlace]]:
    """A capability's `friction.places`, read in the package schema's shape (COR-050 point 1).

    Each place is an object `{path, location?}`. With `location`, `path` lies
    inside that entry of the capability's `docs.locations` — itself
    `{path, root?}`, under the internal documentation root unless `root: user`
    names the user root (COR-049 point 4). Without one, `path` is
    repository-relative. Only that shape is read: a place written as plain
    text or in any other shape, or naming a location the capability does not
    declare in its shape, gives the walk nothing it could follow, so it is
    returned as malformed — never dropped — for the validation pass to report
    (COR-050 point 7). Both lists keep the written order.
    """
    source = f"capability:{name}"
    pointer = f"/{FRICTION_KEY}/places"
    raw = _mapping_or_empty(package.get(FRICTION_KEY)).get("places")
    if raw is None:
        return [], []
    if not isinstance(raw, list):
        reason = f"`friction.places` is {_shape(raw)}, not a list of places"
        whole = MalformedPlace(file=package_file, pointer=pointer, source=source, reason=reason)
        return [], [whole]
    locations = _mapping_or_empty(_mapping_or_empty(package.get(DOCS_KEY)).get(LOCATIONS_KEY))
    places: list[SettingsPath] = []
    malformed: list[MalformedPlace] = []
    for index, entry in enumerate(raw):
        entry_pointer = f"{pointer}/{index}"
        resolved = _resolve_capability_place(entry, locations, roots)
        if isinstance(resolved, _Unresolved):
            malformed.append(
                MalformedPlace(
                    file=package_file, pointer=entry_pointer, source=source, reason=resolved.reason
                )
            )
            continue
        path, pattern = resolved
        places.append(
            SettingsPath(
                value=path,
                resolved=pattern,
                file=package_file,
                pointer=entry_pointer,
                source=source,
            )
        )
    return places, malformed


def _resolve_capability_place(
    entry: Any, locations: Mapping[str, Any], roots: Mapping[str, str]
) -> tuple[str, str] | _Unresolved:
    """`(path, pattern)` for a place in the schema's shape, else why it is not.

    `path` is the place's own, `pattern` the repository-relative form the walk
    follows. Whether the pattern stays inside the repository is left to the
    validation pass, which follows links on disk; here only the shape is judged.
    """
    if not isinstance(entry, Mapping):
        return _Unresolved(f"the place is {_shape(entry)}, not an object `{{path, location?}}`")
    written = entry.get(PATH_KEY)
    path = _text_or_none(written)
    if path is None:
        if written is None:
            return _Unresolved("the place has no `path`")
        return _Unresolved(f"the place's `path` is {_shape(written)}, not a path or glob")
    if LOCATION_KEY not in entry:
        return path, _join_posix(path)
    location = entry.get(LOCATION_KEY)
    if not isinstance(location, str):
        return _Unresolved(
            f"the place's `location` is {_shape(location)}, not a name from `docs.locations`"
        )
    if location not in locations:
        declared = f" (declared: {sorted(locations)})" if locations else ""
        return _Unresolved(
            f"the place names location {location!r}, which `docs.locations` does not "
            f"declare{declared}"
        )
    directory = _location_directory(locations[location], roots)
    if directory is None:
        return _Unresolved(
            f"the place names location {location!r}, whose `docs.locations` entry is not "
            f"`{{path, root?}}` with `root` one of {sorted(roots)}"
        )
    return path, _join_posix(directory, path)


def _location_directory(declaration: Any, roots: Mapping[str, str]) -> str | None:
    """Where a `docs.locations` entry lies, repository-relative; `None` unless `{path, root?}`."""
    if not isinstance(declaration, Mapping):
        return None
    sub_path = _text_or_none(declaration.get(PATH_KEY))
    root = declaration.get(LOCATION_ROOT_KEY, INTERNAL_ROOT_KEY)
    if sub_path is None or not isinstance(root, str) or root not in roots:
        return None
    return _join_posix(roots[root], sub_path)


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


def _capability_locations(package: Mapping[str, Any]) -> tuple[str, ...]:
    """The sub-paths a capability's `friction.surface` is resolved under.

    Read as a list of texts, or a mapping whose values are texts — the reading
    from before the package schema fixed `docs.locations` entries as
    `{path, root?}` objects and the surface as repository-relative; the places
    no longer use it (`_capability_places`). A capability declaring no such
    locations has its surface resolved directly under the internal root.
    """
    docs = _mapping_or_empty(package.get(DOCS_KEY))
    raw = docs.get(LOCATIONS_KEY)
    if isinstance(raw, Mapping):
        raw = list(raw.values())
    texts = tuple(text for _index, text in _texts(raw))
    return texts or ("",)


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


def _text_or_default(value: Any, default: str) -> str:
    return value if isinstance(value, str) and value.strip() else default


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
class Discovery:
    """What a walk of the declared places found, in deterministic order.

    `places` are the declared places followed by the rule-set places not
    already among them.
    """

    settings: FrictionSettings
    places: tuple[Place, ...]
    artefacts: tuple[Artefact, ...]
    unreadable: tuple[UnreadableFile, ...]

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
    """
    settings = settings if settings is not None else read_friction_settings(target_root, tree)
    # Which rule-set folders are places is read from the working tree even when
    # `tree` names another state: a folder that exists only at that state (one
    # the change deleted outright) is not walked there. The folders are
    # existence-gated so that a project without rule sets stays dormant
    # without a repository being demanded.
    rule_set_places_found = rule_set_places(target_root, settings)
    places = declared_places(settings)
    places += tuple(r.place for r in rule_set_places_found if r.place not in places)
    if not places:
        return Discovery(settings=settings, places=places, artefacts=(), unreadable=())
    listing = tree if tree is not None else working_tree(target_root)
    files = listing.files()
    claimed: dict[str, RuleSetPlace] = {}
    for rule_set_place in rule_set_places_found:
        for rel in listed_files_in_place(rule_set_place.place, files):
            if PurePosixPath(rel).name != RULE_SETS_SIGNPOST:
                claimed.setdefault(rel, rule_set_place)
    matched: list[tuple[Place, str]] = []
    seen: set[str] = set()
    for place in places:
        for rel in listed_files_in_place(place, files):
            if rel not in seen:
                seen.add(rel)
                matched.append((place, rel))

    artefacts: list[Artefact] = []
    unreadable: list[UnreadableFile] = []
    texts = _document_texts(listing, [rel for _place, rel in matched])
    for place, rel in matched:
        rule_set = claimed.get(rel)
        text = texts[rel]
        if text is None:
            continue  # a link: never read as a document
        if isinstance(text, _ReadFailure):
            unreadable.append(
                UnreadableFile(path=rel, place=place, reason=text.reason, rule_set=rule_set)
            )
            continue
        found, reason = parse_artefacts(rel, place, text, rule_set=rule_set)
        if reason is not None:
            unreadable.append(
                UnreadableFile(path=rel, place=place, reason=reason, rule_set=rule_set)
            )
            continue
        artefacts.extend(found)
    return Discovery(
        settings=settings,
        places=places,
        artefacts=tuple(artefacts),
        unreadable=tuple(unreadable),
    )


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
    if "\r" in text:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
    front_matter, body = split_front_matter(text)
    if front_matter is None:
        return [], None
    try:
        data = _yaml.load(io.StringIO(front_matter))
    except YAMLError as exc:
        return [], _yaml_reason(exc)
    if not isinstance(data, Mapping):
        return [], None
    return _artefacts_of_file(rel, place, as_written(data), body, rule_set=rule_set), None


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

    A heading whose text is the id, or starts with the id followed by a space
    or punctuation, opens the section; it runs to the next heading of the same
    or a higher level.
    """
    headings = list(_HEADING.finditer(body))
    for index, match in enumerate(headings):
        title = match.group(2).strip()
        if title == entry_id or (title.startswith(entry_id) and not title[len(entry_id)].isalnum()):
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
