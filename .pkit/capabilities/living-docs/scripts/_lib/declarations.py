"""What living-docs reads about a project: the backbone's answer, and its own configuration.

Two sources, each read once:

- **where the documents are** — the documentation roots, the places the
  project and every installed capability declare, which Markdown files each
  place matches, each file's front matter, and the documents a capability
  holds that are not artefacts, with their owner — is the backbone's artefact
  discovery, read through its read command (`artefacts`, `pkit friction
  artefacts --json`). A capability script never imports the backbone, and
  never re-reads the declarations or walks the places itself: one home per
  computation (ADR-057 point 2).
- living-docs' own **project configuration**, which only this capability
  reads: each space's entry point and definition, and the space each place is
  assigned to (DEC-001 point 1).

The path helpers below read a place's *text* for DEC-001's precedence — its
wildcards and the literal prefix before the first — and never match a path
against it: which files a place matches is the backbone's answer.

Reading is forgiving (COR-048 point 4): a missing or malformed value reads as
absent. Judging the shape of these files is the backbone's configuration,
packages and data passes; the checks living-docs owns are in `spaces`.
"""

from __future__ import annotations

import os
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from _lib.artefacts import Artefact, DeclaredPlace, Document, Reading
from _lib.root import CAPABILITIES_DIR, CAPABILITY
from _lib.root import project_root as project_root  # re-exported: the commands read it here

#: Where the declarations live, relative to the project root.
BACKBONE_CONFIG = ".pkit/project/config.yaml"
LIVING_DOCS_CONFIG = f"{CAPABILITIES_DIR}/{CAPABILITY}/project/config.yaml"

#: The two audiences a root serves, as `docs` in the configuration names them.
USER_ROOT = "user"
INTERNAL_ROOT = "internal"

#: The locations this capability's package declares: each root itself, a
#: default place of its space, and the spaces' definitions (DEC-001 points 1
#: and 2). Its places name them.
ROOT_LOCATIONS = {"user-root": USER_ROOT, "internal-root": INTERNAL_ROOT}
DEFINITIONS_LOCATION = "definitions"

#: Only Markdown files are documents (ADR-056 point 2).
DOCUMENT_SUFFIX = ".md"

#: The characters that make a place's text a pattern rather than a path —
#: DEC-001's "wildcard".
WILDCARDS = frozenset("*?[")

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


def has_wildcard(text: str) -> bool:
    return any(char in WILDCARDS for char in text)


def literal_prefix(pattern: str) -> str:
    """The leading segments of `pattern` that carry no wildcard, as a path."""
    kept: list[str] = []
    for segment in normalise(pattern).split("/"):
        if has_wildcard(segment):
            break
        kept.append(segment)
    return normalise("/".join(kept))


def literal_text_prefix(pattern: str) -> str:
    """The text of `pattern` before its first wildcard — what "the longer literal
    prefix before the first wildcard" measures (DEC-001 point 1)."""
    text = normalise(pattern)
    for index, char in enumerate(text):
        if char in WILDCARDS:
            return text[:index]
    return text


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


def is_markdown_file(root: Path, rel: str) -> bool:
    """Whether `rel` names a Markdown file on disk, never a link — for a path the
    configuration names that no place matches, to tell a missing document from
    one that lies in no place."""
    try:
        mode = os.lstat(root / rel).st_mode
    except OSError:
        return False
    return rel.endswith(DOCUMENT_SUFFIX) and stat.S_ISREG(mode)


# --- the declarations ----------------------------------------------------------


@dataclass(frozen=True)
class ProjectPlace:
    """One entry of the backbone configuration's `friction.places`."""

    index: int  # its place in the backbone's reading, in declaration order
    written: str  # as written
    path: str  # normalised
    pointer: str  # into the backbone configuration
    encloses: frozenset[str]  # the audiences of the roots it reaches whole


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
    root_places: Mapping[int, str]  # this capability's places that are a root -> its audience
    component_places: Mapping[int, str]  # another capability's places -> that capability
    documents: Mapping[str, Document]  # every Markdown file a place matches or a component holds
    artefacts: tuple[Artefact, ...]  # every artefact in them, with its anchors and fields
    definitions: str | None  # this capability's definitions location, when it declares one
    ldoc_version: str | None  # the shared method's version, from its own rule-set file
    ldoc_rules: Mapping[str, Any]  # the shared method's rules by id, from the same file
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


#: The shared method's rule-set file, relative to the project root (DEC-001 point 2).
LDOC_FILE = f"{CAPABILITIES_DIR}/{CAPABILITY}/rule-sets/ldoc.md"


def read_declarations(root: Path, reading: Reading) -> Declarations:
    """Every declaration living-docs needs: the backbone's `reading` of the project
    at `root`, joined with this capability's own configuration."""
    project_places: list[ProjectPlace] = []
    root_places: dict[int, str] = {}
    component_places: dict[int, str] = {}
    definitions: str | None = None
    for place in reading.places:
        if place.is_project and place.written is not None:
            project_places.append(_project_place(place))
        elif place.declared and place.capability == CAPABILITY:
            # Its own places are the roots and the definitions location, which
            # the checks read as such; they are no other component's claim.
            if place.location in ROOT_LOCATIONS:
                root_places[place.index] = ROOT_LOCATIONS[place.location]
            elif place.location == DEFINITIONS_LOCATION and place.location_path is not None:
                definitions = normalise(place.location_path)
        elif place.declared and place.capability is not None:
            component_places[place.index] = place.capability

    ldoc = reading.documents.get(LDOC_FILE)
    ldoc_fields = mapping(ldoc.fields) if ldoc is not None else {}
    ldoc_version = ldoc_fields.get("version")

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
        user_root=normalise(reading.roots[USER_ROOT]),
        internal_root=normalise(reading.roots[INTERNAL_ROOT]),
        project_places=tuple(project_places),
        root_places=root_places,
        component_places=component_places,
        documents=reading.documents,
        artefacts=reading.artefacts,
        definitions=definitions,
        ldoc_version=ldoc_version if isinstance(ldoc_version, str) else None,
        ldoc_rules=mapping(ldoc_fields.get("rules")),
        spaces=spaces,
        assignments=assignments,
        config_exists=isinstance(own, Mapping),
    )


def _project_place(place: DeclaredPlace) -> ProjectPlace:
    written = place.written or ""
    return ProjectPlace(
        index=place.index,
        written=written,
        path=normalise(written),
        pointer=place.pointer,
        encloses=place.encloses,
    )


def _text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None
