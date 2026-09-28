"""Documentation roots: resolution, derivation, and record-on-first-use (COR-049).

A project declares two documentation roots in its backbone configuration —
`docs.user` and `docs.internal`, both defaulting to `docs/` (COR-049 point 1).
Whatever in the methodology has to *choose* a documentation location derives
it from the right root plus a conventional sub-path, unless an explicit value
already exists (points 3 and 4):

    explicit  >  derived from the root  >  conventional default

The backbone owns one list of conventional sub-paths for the overlay's
folder-locating categories (`CONVENTIONAL_SUBPATHS`); a capability declares
the sub-paths of its own documents in its package metadata (`docs.locations`),
each an object `{path, root?}` naming the root it lies under. A location that
was derived is **recorded as an explicit value the first time it is used**
(point 5) — into the overlay for a backbone category, into the capability's
project namespace for a capability's document — so a later root change moves
nothing already chosen (point 6). Recording happens only where a location is
chosen, never on read.

A capability's locations are read one way, by `read_capability_locations`:
each name it declares lies at its recorded location when one exists, else at
its declared sub-path under the root it names. That function is pure — it takes
the parsed files — so this module's disk readers and friction discovery, which
also reads other states of the repository, call the same reading.

Reading is forgiving throughout (COR-048 point 4): an unreadable configuration
yields the defaults; `pkit validate` reports the file separately.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.error import YAMLError

from project_kit.project_config import read_config

#: Both roots' default, relative to the repository root (COR-049 point 1).
DEFAULT_ROOT = "docs"

#: The configuration key the roots live under, and its two audiences.
DOCS_KEY = "docs"
USER_KEY = "user"
INTERNAL_KEY = "internal"

#: The component name under which the backbone's own locations are recorded.
BACKBONE = "backbone"

#: The one list the backbone owns of conventional sub-paths, relative to the
#: internal root, for the overlay categories that locate a *folder* of
#: documents (COR-049 point 4). Categories listing individual files (the
#: project-root documents) do not derive and are not here.
CONVENTIONAL_SUBPATHS: dict[str, str] = {
    "architecture-docs": "architecture",
    "adr-records": "architecture/decisions",
}

#: Where a capability declares the sub-paths of its own documents, in its
#: package metadata: `docs: {locations: {<name>: {path, root?}}}` — the package
#: schema's `doc-location`, `root` naming one of the two roots and internal
#: when absent.
PACKAGE_DOCS_KEY = "docs"
PACKAGE_LOCATIONS_KEY = "locations"
LOCATION_PATH_KEY = "path"
LOCATION_ROOT_KEY = "root"

#: The two audiences a root serves, and so the values a location's `root` takes.
AUDIENCES: tuple[str, ...] = (INTERNAL_KEY, USER_KEY)

#: Where a capability's chosen locations are recorded (COR-049 point 5): a
#: backbone-owned file in the capability's project namespace, kept apart from
#: the capability's own `config.yaml` so a strict capability schema is never
#: broken by a key it did not declare.
CAPABILITY_LOCATIONS_FILENAME = "docs-locations.yaml"
CAPABILITY_LOCATIONS_KEY = "locations"

_OVERLAY_RELPATH = Path(".pkit") / "agents" / "project" / "overlay.yaml"
_CAPABILITIES_RELPATH = PurePosixPath(".pkit") / "capabilities"


class Source(StrEnum):
    """Where a resolved root or location came from."""

    EXPLICIT = "explicit"
    DERIVED = "derived"
    DEFAULT = "default"


@dataclass(frozen=True)
class Roots:
    """The two resolved documentation roots, each with its source."""

    user: Path
    internal: Path
    user_source: Source
    internal_source: Source

    def for_audience(self, audience: str) -> tuple[Path, Source]:
        if audience == USER_KEY:
            return self.user, self.user_source
        if audience == INTERNAL_KEY:
            return self.internal, self.internal_source
        raise ValueError(f"unknown documentation audience {audience!r}")


@dataclass(frozen=True)
class Location:
    """A resolved documentation location (relative to the repository root) and its source."""

    path: Path
    source: Source


@dataclass(frozen=True)
class DeclaredLocation:
    """One `docs.locations` entry in the package schema's shape `{path, root?}`."""

    path: str  # the sub-path as written, relative to the root
    root: str  # the audience whose root it lies under: `internal` or `user`


@dataclass(frozen=True)
class UnreadableLocation:
    """A declared location the reading cannot place, and why: a clause a finding
    quotes after "whose `docs.locations` entry"."""

    reason: str


@dataclass(frozen=True)
class RecordedLocation:
    """A location a component has recorded as explicit."""

    component: str  # `backbone` or a capability name
    name: str  # the overlay category, or the capability's document name
    path: Path  # relative to the repository root


# --- roots -------------------------------------------------------------------


def resolve_roots(target_root: Path) -> Roots:
    """Both roots from the configuration, defaults where absent or unusable.

    A value that is not a non-empty relative path string is treated as absent
    (forgiving read); validation reports it.
    """
    return roots_from(read_config(target_root).get(DOCS_KEY))


def roots_from(docs: Any) -> Roots:
    """Both roots from the configuration's parsed `docs` value, however it was
    read — from disk (`resolve_roots`) or from another state of the repository
    (friction discovery). Anything not a mapping reads as absent."""
    if not isinstance(docs, Mapping):
        docs = {}
    user, user_source = _root_from(docs.get(USER_KEY))
    internal, internal_source = _root_from(docs.get(INTERNAL_KEY))
    return Roots(
        user=user, internal=internal, user_source=user_source, internal_source=internal_source
    )


def _root_from(value: Any) -> tuple[Path, Source]:
    if isinstance(value, str) and value.strip() and not PurePosixPath(value).is_absolute():
        return normalise(value), Source.EXPLICIT
    return Path(DEFAULT_ROOT), Source.DEFAULT


def normalise(path: str | Path) -> Path:
    """A repository-relative path without trailing slashes or `.` segments."""
    text = str(path).strip().replace("\\", "/").strip("/")
    parts = [p for p in text.split("/") if p and p != "."]
    return Path(*parts) if parts else Path(".")


def is_within(path: str | Path, root: str | Path) -> bool:
    """Whether `path` is `root` or lies under it (both repository-relative)."""
    p, r = normalise(path), normalise(root)
    if r == Path("."):
        return not (p.parts and p.parts[0] == "..")
    return p == r or r in p.parents


# --- derivation --------------------------------------------------------------


def derive_location(
    root: Path | str | None,
    kind: str,
    *,
    explicit: str | Path | None = None,
    subpaths: Mapping[str, str] | None = None,
) -> Location | None:
    """One location by precedence: explicit > derived from `root` > conventional default.

    `kind` is an overlay category or a capability's document name; `subpaths`
    maps kinds to their conventional sub-path (the backbone's own list when
    omitted). Returns None when `kind` has no sub-path and nothing explicit —
    a location that cannot be chosen here.
    """
    if explicit is not None and str(explicit).strip():
        return Location(normalise(explicit), Source.EXPLICIT)
    table = CONVENTIONAL_SUBPATHS if subpaths is None else subpaths
    sub = table.get(kind)
    if not isinstance(sub, str) or not sub.strip():
        return None
    if root is not None:
        return Location(normalise(root) / normalise(sub), Source.DERIVED)
    return Location(Path(DEFAULT_ROOT) / normalise(sub), Source.DEFAULT)


def conventional_locations(target_root: Path) -> dict[str, str]:
    """Every backbone conventional category → its location derived from the
    project's internal root, as repository-relative text. With the default root
    these are exactly the historical literals (`docs/architecture`, ...)."""
    internal = resolve_roots(target_root).internal
    return {kind: _text(derive_location(internal, kind)) for kind in CONVENTIONAL_SUBPATHS}


def default_conventional_locations() -> dict[str, str]:
    """The conventional locations under the default root — the fallback literals."""
    return {kind: _text(derive_location(None, kind)) for kind in CONVENTIONAL_SUBPATHS}


def _text(location: Location | None) -> str:
    assert location is not None  # every kind in CONVENTIONAL_SUBPATHS derives
    return location.path.as_posix()


# --- record on first use -----------------------------------------------------


def record_location(
    target_root: Path, component: str, name: str, path: str | Path, *, by: str = "pkit"
) -> Path | None:
    """Record a chosen location as an explicit value in the owning component's
    project configuration (COR-049 point 5).

    For the backbone, `name` is an overlay category and the value is appended
    to `.pkit/agents/project/overlay.yaml` uncommented; for a capability, it is
    written under `locations` in the capability's `project/docs-locations.yaml`.
    An already-recorded (explicit) value is never overwritten. Returns the file
    written, or None when nothing was written.

    Call this only where a location is *chosen* — a first stamp or placement —
    and only from a command whose invocation is the consent to write (COR-048
    point 5); a read never records. `by` names that command in the file.
    """
    rel = normalise(path).as_posix()
    if component == BACKBONE:
        return _record_overlay_category(target_root, name, rel, by=by)
    return _record_capability_location(target_root, component, name, rel)


def _record_overlay_category(target_root: Path, category: str, rel: str, *, by: str) -> Path | None:
    overlay = target_root / _OVERLAY_RELPATH
    if not overlay.is_file():
        raise FileNotFoundError(f"overlay not found at {overlay}; run `pkit init` first.")
    existing = overlay.read_text(encoding="utf-8")
    if re.search(rf"(?m)^\s*{re.escape(category)}\s*:", existing):
        return None  # explicit already: never overwritten (COR-049 point 3)
    block = [
        "",
        f"# --- {category}: recorded by `{by}` from the documentation roots "
        f"(COR-049 point 5) ---",
        f"{category}:",
        f"  - {rel}",
    ]
    with overlay.open("a", encoding="utf-8") as fh:
        if existing and not existing.endswith("\n"):
            fh.write("\n")
        fh.write("\n".join(block) + "\n")
    return overlay


def capability_locations_relpath(capability: str) -> PurePosixPath:
    """Where a capability's recorded locations live, relative to the repository root."""
    return _CAPABILITIES_RELPATH / capability / "project" / CAPABILITY_LOCATIONS_FILENAME


def capability_locations_path(target_root: Path, capability: str) -> Path:
    return target_root / capability_locations_relpath(capability)


def _record_capability_location(
    target_root: Path, capability: str, name: str, rel: str
) -> Path | None:
    path = capability_locations_path(target_root, capability)
    yaml = YAML()
    data: CommentedMap = CommentedMap()
    if path.is_file():
        loaded = yaml.load(path.read_text(encoding="utf-8"))
        if isinstance(loaded, CommentedMap):
            data = loaded
    locations = data.get(CAPABILITY_LOCATIONS_KEY)
    if not isinstance(locations, Mapping):
        locations = CommentedMap()
        data[CAPABILITY_LOCATIONS_KEY] = locations
    if isinstance(locations.get(name), str) and locations[name].strip():
        return None
    locations[name] = rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        stream.write(
            f"# Documentation locations {capability} has chosen (COR-049 point 5).\n"
            f"# Recorded the first time each was used; a later change of the\n"
            f"# documentation roots leaves these untouched. Project-owned.\n"
        )
        yaml.dump(data, stream)
    return path


# --- a capability's locations: the one reading -------------------------------


def read_capability_locations(
    package: Any, recorded: Any, roots: Roots
) -> dict[str, Location | UnreadableLocation]:
    """Where each documentation location a capability declares lies (COR-049
    points 3 to 5) — the one reading every reader of a capability's locations
    calls, so they cannot disagree.

    `package` is the capability's parsed package metadata, `recorded` its parsed
    `docs-locations.yaml`, and `roots` the project's roots. The result has one
    entry per name `docs.locations` declares, in declaration order:

    - a location **recorded** for the name wins, as an explicit value — a
      location chosen once stays where it was chosen (point 5);
    - otherwise the declaration, read in the package schema's shape
      `{path, root?}`, lies at `path` under the root `root` names, the internal
      root when absent — derived (point 4);
    - otherwise the declaration is in another shape, and the entry says why;
      the packages pass reports the declaration, and a place naming it is a
      finding of the friction pass (COR-050 point 7).

    A recorded name the capability does not declare is not one of its
    locations. Only shape is judged here: whether a location stays inside the
    repository is for the reader that walks it. Pure, so a reader of another
    state of the repository — friction discovery reading a base commit — passes
    that state's files.
    """
    chosen = _recorded_entries(recorded)
    resolved: dict[str, Location | UnreadableLocation] = {}
    for name, declaration in _declared_locations(package).items():
        if name in chosen:
            resolved[name] = Location(normalise(chosen[name]), Source.EXPLICIT)
        elif isinstance(declaration, UnreadableLocation):
            resolved[name] = declaration
        else:
            root, _source = roots.for_audience(declaration.root)
            resolved[name] = Location(root / declaration.path, Source.DERIVED)
    return resolved


def _declared_locations(package: Any) -> dict[str, DeclaredLocation | UnreadableLocation]:
    """Every entry of a parsed package metadata's `docs.locations`, read in the
    package schema's shape `{path, root?}`; an entry in another shape says why.
    A `docs.locations` that is not a mapping declares nothing."""
    docs = package.get(PACKAGE_DOCS_KEY) if isinstance(package, Mapping) else None
    locations = docs.get(PACKAGE_LOCATIONS_KEY) if isinstance(docs, Mapping) else None
    if not isinstance(locations, Mapping):
        return {}
    return {str(name): _declared_location(value) for name, value in locations.items()}


def _declared_location(value: Any) -> DeclaredLocation | UnreadableLocation:
    if not isinstance(value, Mapping):
        return UnreadableLocation("is not an object `{path, root?}`")
    path = value.get(LOCATION_PATH_KEY)
    if not isinstance(path, str) or not path.strip():
        return UnreadableLocation("has no `path` naming a sub-path of its root")
    root = value.get(LOCATION_ROOT_KEY, INTERNAL_KEY)
    if root not in AUDIENCES:
        return UnreadableLocation(f"names `root` {root!r}, not one of {sorted(AUDIENCES)}")
    return DeclaredLocation(path=path.strip(), root=root)


def _recorded_entries(recorded: Any) -> dict[str, str]:
    """The locations a parsed `docs-locations.yaml` records, name to text; an
    entry that is not a non-empty text is not a recorded location."""
    locations = recorded.get(CAPABILITY_LOCATIONS_KEY) if isinstance(recorded, Mapping) else None
    if not isinstance(locations, Mapping):
        return {}
    return {str(k): v for k, v in locations.items() if isinstance(v, str) and v.strip()}


def capability_subpaths(target_root: Path, capability: str) -> dict[str, DeclaredLocation]:
    """The locations a capability declares in its package metadata that are in
    the package schema's shape: each its sub-path and the root it lies under.
    Where a location lies — its recorded value winning — is `capability_location`."""
    return {
        name: declaration
        for name, declaration in _declared_locations(_load_package(target_root, capability)).items()
        if isinstance(declaration, DeclaredLocation)
    }


def recorded_capability_locations(target_root: Path, capability: str) -> dict[str, str]:
    """A capability's recorded locations, forgivingly read."""
    return _recorded_entries(_load_yaml(capability_locations_path(target_root, capability)))


def capability_location(
    target_root: Path, capability: str, name: str, *, roots: Roots | None = None
) -> Location | None:
    """Where a capability's document location lies, by the one reading
    (`read_capability_locations`): recorded (explicit) > derived from its
    declaration. `None` when the capability does not declare `name`, or
    declares it in another shape with nothing recorded."""
    roots = roots if roots is not None else resolve_roots(target_root)
    resolved = read_capability_locations(
        _load_package(target_root, capability),
        _load_yaml(capability_locations_path(target_root, capability)),
        roots,
    ).get(name)
    return resolved if isinstance(resolved, Location) else None


def _load_package(target_root: Path, capability: str) -> Any:
    return _load_yaml(target_root / _CAPABILITIES_RELPATH / capability / "package.yaml")


# --- what is recorded (for the status report) -------------------------------


def recorded_locations(target_root: Path) -> list[RecordedLocation]:
    """Every explicitly recorded documentation location: the overlay's values
    for the backbone's conventional categories, and each installed capability's
    recorded locations. Sorted by component, name, path — deterministic."""
    found: list[RecordedLocation] = []
    overlay = _load_yaml(target_root / _OVERLAY_RELPATH)
    if isinstance(overlay, Mapping):
        for category in CONVENTIONAL_SUBPATHS:
            for entry in _entries(overlay.get(category)):
                found.append(RecordedLocation(BACKBONE, category, normalise(entry)))
    for capability in _installed_capabilities(target_root):
        for name, rel in recorded_capability_locations(target_root, capability).items():
            found.append(RecordedLocation(capability, name, normalise(rel)))
    return sorted(
        found, key=lambda r: (r.component != BACKBONE, r.component, r.name, r.path.as_posix())
    )


def outside_root(target_root: Path, roots: Roots | None = None) -> list[RecordedLocation]:
    """The recorded locations lying outside the internal root (COR-049 point 6)."""
    roots = roots if roots is not None else resolve_roots(target_root)
    return [r for r in recorded_locations(target_root) if not is_within(r.path, roots.internal)]


def inside_root(target_root: Path, roots: Roots | None = None) -> list[RecordedLocation]:
    """The recorded locations lying inside the internal root — the complement of
    `outside_root`, so the two together show every recorded location (COR-049 point 7)."""
    roots = roots if roots is not None else resolve_roots(target_root)
    return [r for r in recorded_locations(target_root) if is_within(r.path, roots.internal)]


def _entries(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str) and v.strip()]
    return []


def _installed_capabilities(target_root: Path) -> list[str]:
    from project_kit.manifest import read_backbone_manifest

    manifest = read_backbone_manifest(target_root)
    if manifest is None:
        return []
    return sorted(e.name for e in manifest.components if e.kind == "capability")


def _load_yaml(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    except (OSError, YAMLError):
        return None
