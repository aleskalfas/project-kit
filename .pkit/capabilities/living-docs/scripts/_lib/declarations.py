"""What a project declares that living-docs reads, read as the backbone reads it.

A capability script runs in its own environment and never imports the backbone
(the lifecycle README, "Reading one point from a script"), so this module reads
the same declarations the backbone reads, by the rules its references state:

- the **documentation roots**, `docs.user` and `docs.internal` in the backbone
  configuration, both `docs/` by default (COR-049 point 1);
- the **project's places**, `friction.places` in the same file, and its
  excluded paths, `friction.exclude` (COR-050 point 14);
- each installed capability's **places**, `friction.places` in its package
  metadata, each `{path, location?}` with the location resolved as every
  reader of a capability's locations resolves it: recorded in the
  capability's `project/docs-locations.yaml`, else its declared `{path,
  root?}` under the root it names (COR-049 points 4 and 5; the lifecycle
  README, "Field layout and casing");
- living-docs' own **project configuration**: each space's entry point and
  definition, and the space each place is assigned to (DEC-001 point 1);
- the **working tree's listing** — the files git sees, tracked and untracked
  but not ignored, every file where git gives no view — and the Markdown
  documents in it, links never read (the schemas README, "Where artefacts are
  looked for").

Paths and globs are matched by the backbone's one reading: a glob as pathlib
reads it on Python 3.13, `**` spanning folders; a path without glob characters
a file, or a folder and everything beneath it; `.` the whole repository.

Reading is forgiving (COR-048 point 4): a missing or malformed value reads as
absent. Judging the shape of these files is the backbone's configuration,
packages and data passes; the checks living-docs owns are in `spaces`.
"""

from __future__ import annotations

import io
import os
import re
import stat
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

#: This capability's name, as installed under `.pkit/capabilities/`.
CAPABILITY = "living-docs"

#: Where the declarations live, relative to the project root.
BACKBONE_CONFIG = ".pkit/project/config.yaml"
BACKBONE_MANIFEST = ".pkit/manifest.yaml"
CAPABILITIES_DIR = ".pkit/capabilities"
LIVING_DOCS_CONFIG = f"{CAPABILITIES_DIR}/{CAPABILITY}/project/config.yaml"

#: Where a capability records the locations it has chosen (COR-049 point 5).
RECORDED_LOCATIONS = "project/docs-locations.yaml"

#: Both roots' default (COR-049 point 1).
DEFAULT_ROOT = "docs"

#: The two audiences a root serves, as `docs` in the configuration names them.
USER_ROOT = "user"
INTERNAL_ROOT = "internal"

#: The location this capability's package declares for the spaces' definitions
#: (DEC-001 point 2).
DEFINITIONS_LOCATION = "definitions"

#: Only Markdown files are documents (ADR-056 point 2).
DOCUMENT_SUFFIX = ".md"

_GLOB_CHARS = frozenset("*?[")
_FENCE = re.compile(r"^---[ \t]*$", re.MULTILINE)

_yaml = YAML(typ="safe")


# --- paths -------------------------------------------------------------------


def normalise(path: str) -> str:
    """A repository-relative path as POSIX text, without `./`, `.` segments or a
    trailing slash; `.` for the repository itself. The join between the
    backbone configuration and this capability's is a path normalised this way
    (DEC-001 point 1)."""
    text = str(path).strip().replace("\\", "/")
    parts = [part for part in text.split("/") if part and part != "."]
    return "/".join(parts) if parts else "."


def is_within(path: str, folder: str) -> bool:
    """Whether `path` is `folder` or lies beneath it (both repository-relative)."""
    p, f = normalise(path), normalise(folder)
    return f == "." or p == f or p.startswith(f + "/")


def is_glob(pattern: str) -> bool:
    return any(char in _GLOB_CHARS for char in pattern)


def literal_prefix(pattern: str) -> str:
    """The leading segments of `pattern` that carry no glob character, as a path."""
    kept: list[str] = []
    for segment in normalise(pattern).split("/"):
        if is_glob(segment):
            break
        kept.append(segment)
    return normalise("/".join(kept))


def literal_text_prefix(pattern: str) -> str:
    """The text of `pattern` before its first glob character — what "the longer
    literal prefix before the first wildcard" measures (DEC-001 point 1)."""
    text = normalise(pattern)
    for index, char in enumerate(text):
        if char in _GLOB_CHARS:
            return text[:index]
    return text


@lru_cache(maxsize=1024)
def pattern_matcher(pattern: str) -> Callable[[str], bool]:
    """A predicate over repository-relative file paths for a place `pattern`:
    the backbone's one reading (`friction_discovery.pattern_matcher`)."""
    normalised = normalise(pattern)
    if normalised == ".":
        return lambda _path: True
    if is_glob(normalised):
        regex = _compile_glob(normalised)
        return lambda path: regex.fullmatch(path) is not None
    prefix = normalised + "/"
    return lambda path: path == normalised or path.startswith(prefix)


def matches(pattern: str, path: str) -> bool:
    return pattern_matcher(pattern)(path)


def _compile_glob(pattern: str) -> re.Pattern[str]:
    """pathlib's reading of a glob (Python 3.13): `**` as a whole segment spans
    any number of folders, none included; `*` and `?` stay within a segment;
    `[...]` is a class, `[!...]` its negation."""
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
                out.append(re.escape(char))
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


def pointer_token(segment: Any) -> str:
    """One JSON Pointer reference token (RFC 6901 escaping)."""
    return str(segment).replace("~", "~0").replace("/", "~1")


# --- files -------------------------------------------------------------------


def load_yaml(path: Path) -> Any:
    """A YAML file's value; `None` when absent or unparsable."""
    try:
        return _yaml.load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, YAMLError):
        return None


def mapping(value: Any) -> Mapping[str, Any]:
    return {str(k): v for k, v in value.items()} if isinstance(value, Mapping) else {}


def texts(value: Any) -> list[tuple[int, str]]:
    """(index, text) for each non-empty text of a list, as written."""
    if not isinstance(value, list):
        return []
    return [(i, v.strip()) for i, v in enumerate(value) if isinstance(v, str) and v.strip()]


class Unparsable(Exception):
    """A document's front matter that does not parse as YAML."""


def front_matter(text: str) -> Mapping[str, Any] | None:
    """A Markdown text's front matter as a mapping; `None` when it has none, or
    none that is a mapping. Raises `Unparsable` when it does not parse."""
    if "\r" in text:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.startswith("---"):
        return None
    first_line_end = text.find("\n")
    if first_line_end == -1 or text[:first_line_end].rstrip() != "---":
        return None
    closing = _FENCE.search(text, first_line_end + 1)
    if closing is None:
        return None
    try:
        data = _yaml.load(io.StringIO(text[first_line_end + 1 : closing.start()]))
    except YAMLError as exc:
        raise Unparsable(str(exc).splitlines()[0]) from exc
    return mapping(data) if isinstance(data, Mapping) else None


def read_front_matter(root: Path, rel: str) -> Mapping[str, Any] | None:
    """A document's front matter, read forgivingly: `None` when it has none, does
    not parse, or cannot be read — the friction pass reports what does not parse
    in a place, so it is not reported twice."""
    try:
        return front_matter((root / rel).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, Unparsable):
        return None


def markdown_listing(root: Path) -> list[str]:
    """The Markdown documents of the working tree's one listing, sorted: the files
    git sees, tracked and untracked but not ignored — every file where git gives
    no view — and never a link, which is listed but never read as a document."""
    try:
        completed = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=root,
            capture_output=True,
            check=False,
        )
        listed = (
            {
                item.decode("utf-8", "surrogateescape")
                for item in completed.stdout.split(b"\0")
                if item
            }
            if completed.returncode == 0
            else None
        )
    except OSError:
        listed = None
    if listed is None:
        listed = set(_walk(root))
    return sorted(
        rel
        for rel in listed
        if rel.endswith(DOCUMENT_SUFFIX) and not rel.startswith(".git/") and _regular(root, rel)
    )


def _walk(root: Path) -> list[str]:
    found: list[str] = []
    for directory, folders, names in os.walk(root):
        folders[:] = [f for f in folders if f != ".git" and not (Path(directory) / f).is_symlink()]
        found.extend((Path(directory) / name).relative_to(root).as_posix() for name in names)
    return found


def _regular(root: Path, rel: str) -> bool:
    try:
        return stat.S_ISREG(os.lstat(root / rel).st_mode)
    except OSError:
        return False


# --- the declarations ----------------------------------------------------------


@dataclass(frozen=True)
class ProjectPlace:
    """One entry of the backbone configuration's `friction.places`."""

    index: int  # its position in the list, for the pointer
    written: str  # as written
    path: str  # normalised

    @property
    def pointer(self) -> str:
        return f"/friction/places/{self.index}"


@dataclass(frozen=True)
class ComponentPlace:
    """A place another installed component declares in its package metadata."""

    component: str
    pattern: str  # repository-relative, its location joined


@dataclass(frozen=True)
class Assignment:
    """One entry of living-docs' `places`: a place, as written and normalised, and its space."""

    written: str
    path: str
    space: str


@dataclass(frozen=True)
class SpaceConfig:
    """One space of living-docs' project configuration: its entry point and definition."""

    entry_point: str | None
    definition: str | None


@dataclass(frozen=True)
class Declarations:
    """Everything living-docs reads from one state of the repository."""

    user_root: str
    internal_root: str
    project_places: tuple[ProjectPlace, ...]
    exclude: tuple[str, ...]
    component_places: tuple[ComponentPlace, ...]
    definitions: str | None  # this capability's definitions location, when it declares one
    spaces: Mapping[str, SpaceConfig]
    assignments: tuple[Assignment, ...]  # as written, in order
    config_exists: bool  # whether living-docs' project configuration is there

    def roots(self) -> dict[str, str]:
        """Each root by the audience it serves."""
        return {USER_ROOT: self.user_root, INTERNAL_ROOT: self.internal_root}

    def assigned(self, path: str) -> str | None:
        """The space a place is assigned to — the first assignment of it, when two
        spellings name one place (the checks report that)."""
        for assignment in self.assignments:
            if assignment.path == path:
                return assignment.space
        return None


def read_declarations(root: Path) -> Declarations:
    """Read every declaration living-docs needs from the project at `root`."""
    config = mapping(load_yaml(root / BACKBONE_CONFIG))
    docs = mapping(config.get("docs"))
    user_root = _root(docs.get(USER_ROOT))
    internal_root = _root(docs.get(INTERNAL_ROOT))
    roots = {USER_ROOT: user_root, INTERNAL_ROOT: internal_root}

    friction = mapping(config.get("friction"))
    project_places = tuple(
        ProjectPlace(index=i, written=text, path=normalise(text))
        for i, text in texts(friction.get("places"))
    )
    exclude = tuple(normalise(text) for _i, text in texts(friction.get("exclude")))

    component_places: list[ComponentPlace] = []
    definitions: str | None = None
    for name in installed_capabilities(root):
        package = mapping(load_yaml(root / CAPABILITIES_DIR / name / "package.yaml"))
        recorded = mapping(load_yaml(root / CAPABILITIES_DIR / name / RECORDED_LOCATIONS))
        locations = capability_locations(package, recorded, roots)
        if name == CAPABILITY:
            # Its own places are the roots and the definitions location, which
            # the checks read as such; they are no other component's claim.
            definitions = locations.get(DEFINITIONS_LOCATION)
        else:
            component_places.extend(
                ComponentPlace(name, pattern) for pattern in capability_places(package, locations)
            )

    own = load_yaml(root / LIVING_DOCS_CONFIG)
    own_config = mapping(own)
    spaces: dict[str, SpaceConfig] = {}
    for space_id, entry in mapping(own_config.get("spaces")).items():
        entry = mapping(entry)
        spaces[space_id] = SpaceConfig(
            entry_point=_text(entry.get("entry-point")),
            definition=_text(entry.get("definition")),
        )
    assignments = tuple(
        Assignment(written=written, path=normalise(written), space=space)
        for written, space in mapping(own_config.get("places")).items()
        if isinstance(space, str)
    )

    return Declarations(
        user_root=user_root,
        internal_root=internal_root,
        project_places=project_places,
        exclude=exclude,
        component_places=tuple(component_places),
        definitions=definitions,
        spaces=spaces,
        assignments=assignments,
        config_exists=isinstance(own, Mapping),
    )


def installed_capabilities(root: Path) -> list[str]:
    """The installed capabilities by name, sorted, from the backbone manifest."""
    manifest = mapping(load_yaml(root / BACKBONE_MANIFEST))
    components = manifest.get("components")
    if not isinstance(components, list):
        return []
    return sorted(
        str(entry["name"])
        for entry in components
        if isinstance(entry, Mapping)
        and entry.get("kind") == "capability"
        and isinstance(entry.get("name"), str)
    )


def capability_locations(
    package: Mapping[str, Any], recorded: Mapping[str, Any], roots: Mapping[str, str]
) -> dict[str, str]:
    """Where each documentation location a capability declares lies: recorded wins,
    else its declared `{path, root?}` under the root it names, internal when
    absent. A declaration in another shape places nothing (the packages pass
    reports it)."""
    chosen = mapping(recorded.get("locations"))
    declared = mapping(mapping(package.get("docs")).get("locations"))
    resolved: dict[str, str] = {}
    for name, value in declared.items():
        recorded_path = _text(chosen.get(name))
        if recorded_path is not None:
            resolved[name] = normalise(recorded_path)
            continue
        value = mapping(value)
        path = _text(value.get("path"))
        audience = value.get("root", INTERNAL_ROOT)
        if path is None or audience not in roots:
            continue
        resolved[name] = normalise(f"{roots[audience]}/{path}")
    return resolved


def capability_places(package: Mapping[str, Any], locations: Mapping[str, str]) -> list[str]:
    """A capability's `friction.places`, each resolved to a repository-relative
    pattern; a place the walk could not follow is left out (the friction pass
    reports it)."""
    places = mapping(package.get("friction")).get("places")
    found: list[str] = []
    for entry in places if isinstance(places, list) else []:
        entry = mapping(entry)
        path = _text(entry.get("path"))
        if path is None:
            continue
        if "location" not in entry:
            found.append(normalise(path))
        elif entry.get("location") in locations:
            found.append(normalise(f"{locations[entry['location']]}/{path}"))
    return found


def _root(value: Any) -> str:
    if isinstance(value, str) and value.strip() and not PurePosixPath(value).is_absolute():
        return normalise(value)
    return DEFAULT_ROOT


def _text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None
