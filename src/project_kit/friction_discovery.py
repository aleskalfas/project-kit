"""Artefact discovery for the friction functionality (COR-050 point 1).

The backbone looks for anchored artefacts only in the **places declared to
hold them**, so unrelated front matter elsewhere is never misread. This module
is the one reader of those declarations and the one walker of the places:

- `read_friction_settings` — the project's `friction` key in the backbone
  configuration (COR-050 point 14: mode, places, surface, exclude) and each
  installed capability's `friction.places` / `friction.surface`, read
  *forgivingly* (COR-048 point 4): a missing or oddly shaped value reads as
  absent here, and the strict judgment of its shape belongs to the
  configuration and package schemas (Tasks #981, #982). What this module does
  judge — because COR-050 point 12 assigns it to validation — is done in
  `friction_validate`.
- `declared_places` — the resolved places, project first (in declaration
  order) then capabilities by name. A capability's place is relative to the
  document locations it declares under the internal documentation root
  (COR-049 point 4; COR-050 point 1).
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
  document (ADR-056 point 2).

Nothing here computes friction or touches git: the change check and the
whole-repository check (COR-050 point 6) are later Tasks that read the model
this module produces.
"""

from __future__ import annotations

import io
import os
import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from project_kit.backbone_schemas import CONTAINER_KEY, as_written
from project_kit.manifest import read_backbone_manifest
from project_kit.report_context import project_config_path

# The key this functionality owns in the backbone configuration and in a
# capability's package metadata — the same word as the block and the command
# group (COR-050 point 1, COR-053 point 10).
FRICTION_KEY = "friction"

# The documentation key of the backbone configuration (COR-049 point 1) and
# the sub-key naming the internal root. Both roots default to `docs/`.
DOCS_KEY = "docs"
INTERNAL_ROOT_KEY = "internal"
DEFAULT_INTERNAL_ROOT = "docs"

# A capability's document sub-paths under the internal root (COR-049 point 4).
LOCATIONS_KEY = "locations"

# The friction modes COR-050 point 12 names; `warning` is the default (point 14).
FRICTION_MODES: tuple[str, ...] = ("warning", "enforcing")
DEFAULT_FRICTION_MODE = "warning"

# Where installed capabilities live, relative to the project root.
CAPABILITIES_DIR = Path(".pkit") / "capabilities"

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
    internal_root: str  # the documentation root capability places resolve under

    @property
    def mode_or_default(self) -> str:
        if isinstance(self.mode, str) and self.mode in FRICTION_MODES:
            return self.mode
        return DEFAULT_FRICTION_MODE


def read_friction_settings(target_root: Path) -> FrictionSettings:
    """Read the project's and every installed capability's friction settings.

    Forgiving throughout (COR-048 point 4): an absent file, an unparsable
    file, a key of the wrong shape, or a list entry that is not text is read
    as absent. The schema passes of the configuration file and of package
    metadata refuse those; this reader only has to keep working next to them.
    """
    config_rel = str(project_config_path(target_root).relative_to(target_root))
    config = _load_mapping(project_config_path(target_root))
    docs = _mapping_or_empty(config.get(DOCS_KEY))
    internal_root = _text_or_default(docs.get(INTERNAL_ROOT_KEY), DEFAULT_INTERNAL_ROOT)

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

    for name in installed_capability_names(target_root):
        package_rel = CAPABILITIES_DIR / name / "package.yaml"
        package = _load_mapping(target_root / package_rel)
        cap_friction = _mapping_or_empty(package.get(FRICTION_KEY))
        locations = _capability_locations(package)
        for key, sink in (("places", places), ("surface", surface)):
            for index, text in _texts(cap_friction.get(key)):
                for location in locations:
                    sink.append(
                        SettingsPath(
                            value=text,
                            resolved=_join_posix(internal_root, location, text),
                            file=str(package_rel),
                            pointer=f"/{FRICTION_KEY}/{key}/{index}",
                            source=f"capability:{name}",
                        )
                    )

    return FrictionSettings(
        mode=mode,
        places=tuple(places),
        surface=tuple(surface),
        exclude=tuple(exclude),
        internal_root=internal_root,
    )


def installed_capability_names(target_root: Path) -> list[str]:
    """Installed capabilities by name, sorted, from the backbone manifest."""
    backbone = read_backbone_manifest(target_root)
    if backbone is None:
        return []
    return sorted(c.name for c in backbone.components if c.kind == "capability")


def _capability_locations(package: Mapping[str, Any]) -> tuple[str, ...]:
    """The sub-paths a capability's documents resolve under (COR-049 point 4).

    Read as a list of texts, or a mapping whose values are texts (#982 fixes
    the shape). A capability declaring places but no locations resolves them
    directly under the internal root.
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


def _load_mapping(path: Path) -> dict[str, Any]:
    """A YAML file as a mapping with text keys; `{}` when absent, unparsable or not a mapping."""
    if not path.is_file():
        return {}
    try:
        data = _yaml.load(path.read_text(encoding="utf-8"))
    except (OSError, YAMLError):
        return {}
    if not isinstance(data, Mapping):
        return {}
    return {str(k): v for k, v in data.items()}


def _mapping_or_empty(value: Any) -> Mapping[str, Any]:
    return {str(k): v for k, v in value.items()} if isinstance(value, Mapping) else {}


def _text_or_default(value: Any, default: str) -> str:
    return value if isinstance(value, str) and value.strip() else default


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
    if not pattern or PurePosixPath(pattern).is_absolute() or os.path.isabs(pattern):
        return False
    normalised = os.path.normpath(pattern)
    if normalised == ".." or normalised.startswith("../") or normalised.startswith(".." + os.sep):
        return False
    prefix = _literal_prefix(normalised)
    candidate = target_root / prefix if prefix else target_root
    return _resolves_inside(target_root, candidate)


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


def files_in_place(target_root: Path, place: Place) -> list[Path]:
    """The Markdown files a place matches, sorted by repository-relative path.

    A glob matches files; a glob ending in `**` means every Markdown file
    beneath what precedes it (`Path.glob` yields only directories for a
    trailing `**` before Python 3.13, so the suffix is spelled out); a path
    naming a directory means every Markdown file beneath it; a path naming a
    file means that file. Anything that is not a Markdown file — plain YAML,
    say — is not a document and is left alone (ADR-056 point 2). A pattern
    outside the repository matches nothing here, and neither does a match that
    resolves outside it through a link — the walk never reads a file the
    repository does not hold. The configuration pass reports the pattern.
    """
    if not is_inside_repository(target_root, place.pattern):
        return []
    pattern = os.path.normpath(place.pattern)
    if pattern == ".":
        candidates: Iterator[Path] = target_root.rglob(f"*{DOCUMENT_SUFFIX}")
    elif any(ch in _GLOB_CHARS for ch in pattern):
        if PurePosixPath(pattern).name == "**":
            pattern = f"{pattern}/*{DOCUMENT_SUFFIX}"
        candidates = target_root.glob(pattern)
    else:
        literal = target_root / pattern
        if literal.is_dir():
            candidates = literal.rglob(f"*{DOCUMENT_SUFFIX}")
        elif literal.is_file():
            candidates = iter([literal])
        else:
            candidates = iter([])
    # One entry per resolved file: an in-repository link to another matched
    # file is read once, under the first name the walk meets.
    matched: dict[Path, Path] = {}
    try:
        for path in candidates:
            if (
                path.is_file()
                and path.suffix == DOCUMENT_SUFFIX
                and not _under_skipped(path.relative_to(target_root))
                and _resolves_inside(target_root, path)
            ):
                matched.setdefault(path.resolve(), path)
    except (ValueError, NotImplementedError):
        # `Path.glob` before 3.13 rejects `**` mixed into a segment
        # (`docs/**.md`); the configuration pass reports the pattern as
        # matching nothing, so here it simply matches nothing.
        return []
    return sorted(matched.values(), key=lambda p: p.relative_to(target_root).as_posix())


def _under_skipped(rel: Path) -> bool:
    return bool(rel.parts) and rel.parts[0] in _SKIPPED_TOP_LEVEL


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
    place that happens to reach into it. Keyed by the path the walk yields.
    """
    claimed: dict[Path, RuleSetPlace] = {}
    for rule_set_place in places:
        for path in files_in_place(target_root, rule_set_place.place):
            if path.name != RULE_SETS_SIGNPOST:
                claimed.setdefault(path, rule_set_place)
    return claimed


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


def discover_artefacts(target_root: Path, settings: FrictionSettings | None = None) -> Discovery:
    """Walk the declared places and parse every artefact's container.

    The places are the declared ones followed by the rule-set places not
    already among them: rules are artefacts found where artefacts are found
    (COR-051 point 2). A file matched by more than one place is read once,
    under the first place that matched it; whether it is a rule-set file
    depends only on the location rule, not on which place met it. Order:
    places in that order, files within a place by path, entries within a
    collection in written order.
    """
    settings = settings if settings is not None else read_friction_settings(target_root)
    rule_set_places_found = rule_set_places(target_root, settings)
    places = declared_places(settings)
    places += tuple(r.place for r in rule_set_places_found if r.place not in places)
    claimed = rule_set_files(target_root, rule_set_places_found)
    artefacts: list[Artefact] = []
    unreadable: list[UnreadableFile] = []
    seen: set[Path] = set()
    for place in places:
        for path in files_in_place(target_root, place):
            if path in seen:
                continue
            seen.add(path)
            rel = path.relative_to(target_root).as_posix()
            rule_set = claimed.get(path)
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                unreadable.append(
                    UnreadableFile(path=rel, place=place, reason=str(exc), rule_set=rule_set)
                )
                continue
            front_matter, body = split_front_matter(text)
            if front_matter is None:
                continue  # no front matter: not an artefact (COR-050 point 1)
            try:
                data = _yaml.load(io.StringIO(front_matter))
            except YAMLError as exc:
                unreadable.append(
                    UnreadableFile(
                        path=rel, place=place, reason=_yaml_reason(exc), rule_set=rule_set
                    )
                )
                continue
            if not isinstance(data, Mapping):
                continue  # front matter that is not a mapping carries nothing
            carrier = as_written(data)
            artefacts.extend(_artefacts_of_file(rel, place, carrier, body, rule_set=rule_set))
    return Discovery(
        settings=settings,
        places=places,
        artefacts=tuple(artefacts),
        unreadable=tuple(unreadable),
    )


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
