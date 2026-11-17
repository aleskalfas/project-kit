"""What a project records of its installed capabilities (COR-017, ADR-087 point 1).

The one reader of three records, for the agents area's picker of an agent's
definition (`.pkit/agents/definition_source.py`) and for the `pkit` command's
reading of skips and choices:

- **The component registry,** the backbone manifest's `components` list: each
  capability it records is installed, whatever its folder holds on disk
  (COR-017, "Collision prevention").
- **Each capability's skips,** the artefacts the project chose to leave out at
  a collision, in `backend_state.skipped` of the capability's own manifest. A
  capability with no manifest records no skip.
- **The project's choices between capabilities,** one for each agent's name, in
  the backbone manifest beside the registry, under `agent_choices`: a mapping
  from an agent's name to the capability chosen.

**An unreadable record is answered as unreadable,** never as recording nothing,
and each caller decides what that means for it. A backbone manifest that does
not parse leaves the registry and the choices unreadable. One whose
`agent_choices` does not read as that mapping leaves only the choices
unreadable. A project with no backbone manifest records no capability.

Propagated neutral code at the root of the lifecycle area, beside the
ownership module, and kept as it is: only the standard library at module level,
and the YAML library imported inside the function that reads. So a caller
with only the standard library can load the module, and the records are read
by the library that writes them. A caller loads it from its file, without
adding the area to Python's import path and without writing bytecode into the
tree. A function keeps its name and its answer: one whose answer changes takes
a new name (ADR-087 point 5).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, NamedTuple

#: The backbone manifest, relative to the project root.
BACKBONE_MANIFEST = (".pkit", "manifest.yaml")

#: The backbone manifest's key of the project's choices between capabilities
#: (COR-017, ADR-087 point 1).
CHOICES_KEY = "agent_choices"

#: The registry's key, and the kind of an entry that records a capability.
COMPONENTS_KEY = "components"
CAPABILITY_KIND = "capability"

#: Where a capability's manifest records the project's skips.
STATE_KEY = "backend_state"
SKIPPED_KEY = "skipped"

#: A capability's manifest's file name: at the capability's root, where one
#: written before it moved still sits, else under its `project/` (ADR-065
#: point 2). The root one wins where both are there.
MANIFEST_NAME = "manifest.yaml"

#: The origin the registry gives a capability whose entry names none (COR-031).
DEFAULT_ORIGIN = "kit-shipped"


class Registered(NamedTuple):
    """One capability the registry records, with its origin."""

    name: str
    origin: str


class Skips(NamedTuple):
    """The artefacts the project skipped for one capability, as `(kind, name)`
    pairs in the order its manifest lists them, or why its manifest cannot be read.

    `unreadable` is None where the manifest reads, or is absent, and `skipped`
    then holds what it records. Where it does not read, `skipped` is empty and
    records nothing.
    """

    skipped: tuple[tuple[str, str], ...] = ()
    unreadable: str | None = None

    def skips_agent(self, name: str) -> bool:
        """True where the project skipped the capability's agent *name*."""
        return ("agent", name) in self.skipped


class Records(NamedTuple):
    """What the project records of its installed capabilities.

    `capabilities` are the registered ones in the registry's order, and `skips`
    each one's skips. `choices` maps an agent's name to the capability the
    project chose for it. Where the backbone manifest cannot be read,
    `registry_unreadable` says why, and `capabilities`, `skips` and `choices`
    are empty, since none can be read. Where only the choices cannot be read,
    `choices_unreadable` says why, and `choices` is empty.
    """

    capabilities: tuple[Registered, ...] = ()
    skips: Mapping[str, Skips] = {}
    choices: Mapping[str, str] = {}
    registry_unreadable: str | None = None
    choices_unreadable: str | None = None

    @property
    def installed(self) -> frozenset[str]:
        """The names of the registered capabilities."""
        return frozenset(capability.name for capability in self.capabilities)


def read_records(tree: Path) -> Records:
    """The records of the project at *tree*, the folder holding its `.pkit/`."""
    manifest = Path(tree).joinpath(*BACKBONE_MANIFEST)
    if not manifest.is_file():
        return Records()
    relative = "/".join(BACKBONE_MANIFEST)
    try:
        document = _load(manifest)
    except _Unreadable as exc:
        why = f"{relative} cannot be read: {exc}"
        return Records(registry_unreadable=why, choices_unreadable=why)
    if document is None:
        document = {}
    if not isinstance(document, dict):
        why = f"{relative} does not hold a mapping"
        return Records(registry_unreadable=why, choices_unreadable=why)
    data: dict[Any, Any] = document
    components = data.get(COMPONENTS_KEY)
    if components is None:
        components = []
    if not isinstance(components, list):
        why = f"{relative}'s `{COMPONENTS_KEY}` is not a list"
        return Records(registry_unreadable=why, choices_unreadable=why)
    capabilities: list[Registered] = []
    seen: set[str] = set()
    for entry in components:
        if not isinstance(entry, dict) or entry.get("kind") != CAPABILITY_KIND:
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not name or name in seen:
            continue
        seen.add(name)
        origin = entry.get("origin")
        capabilities.append(Registered(name, origin if isinstance(origin, str) else DEFAULT_ORIGIN))
    choices, choices_unreadable = _choices(data.get(CHOICES_KEY), relative)
    return Records(
        capabilities=tuple(capabilities),
        skips={capability.name: read_skips(tree, capability.name) for capability in capabilities},
        choices=choices,
        choices_unreadable=choices_unreadable,
    )


def read_skips(tree: Path, capability: str) -> Skips:
    """The skips capability *capability*'s manifest records, whether or not the
    registry records the capability.

    The manifest read is the one at the capability's root where one is there,
    else the one under its `project/`. A capability with neither records no skip.
    Within a list that reads, an entry that names no kind and name is left out.
    """
    manifest = manifest_path(tree, capability)
    if manifest is None:
        return Skips()
    relative = manifest.relative_to(Path(tree)).as_posix()
    try:
        document = _load(manifest)
    except _Unreadable as exc:
        return Skips(unreadable=f"{relative} cannot be read: {exc}")
    if document is None:
        return Skips()
    if not isinstance(document, dict):
        return Skips(unreadable=f"{relative} does not hold a mapping")
    state = document.get(STATE_KEY)
    if state is None:
        return Skips()
    if not isinstance(state, dict):
        return Skips(unreadable=f"{relative}'s `{STATE_KEY}` is not a mapping")
    listed = state.get(SKIPPED_KEY)
    if listed is None:
        return Skips()
    if not isinstance(listed, list):
        return Skips(unreadable=f"{relative}'s `{STATE_KEY}.{SKIPPED_KEY}` is not a list")
    skipped: list[tuple[str, str]] = []
    for item in listed:
        if not isinstance(item, dict):
            continue
        kind, name = item.get("kind"), item.get("name")
        if isinstance(kind, str) and isinstance(name, str) and (kind, name) not in skipped:
            skipped.append((kind, name))
    return Skips(skipped=tuple(skipped))


def manifest_path(tree: Path, capability: str) -> Path | None:
    """The manifest a reader of capability *capability*'s record reads, or None.

    The one at the capability's root where one is still there, else the one
    under its `project/` (ADR-065 point 2).
    """
    folder = Path(tree) / ".pkit" / "capabilities" / capability
    for path in (folder / MANIFEST_NAME, folder / "project" / MANIFEST_NAME):
        if path.is_file():
            return path
    return None


class _Unreadable(Exception):
    """A record's file that does not read; the message says why."""


def _choices(raw: object, relative: str) -> tuple[dict[str, str], str | None]:
    """The choices `agent_choices` holds, or why it does not read as a mapping from
    an agent's name to a capability's."""
    if raw is None:
        return {}, None
    why = f"{relative}'s `{CHOICES_KEY}` does not map each agent's name to a capability's name"
    if not isinstance(raw, dict):
        return {}, why
    choices: dict[str, str] = {}
    for agent, capability in raw.items():
        if not isinstance(agent, str) or not isinstance(capability, str) or not capability:
            return {}, why
        choices[agent] = capability
    return choices, None


def _load(path: Path) -> object:
    """The YAML document at *path*, or `_Unreadable` naming why it does not read.

    The YAML library is imported here, not at the module's top, so a caller with
    only the standard library can load the module.
    """
    from ruamel.yaml import YAML  # imported where it reads; see the module's docstring

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise _Unreadable(str(exc)) from None
    try:
        return YAML(typ="safe").load(text)
    except Exception as exc:  # whatever the library raises, the file does not read
        first = str(exc).strip().splitlines()
        raise _Unreadable(first[0] if first else type(exc).__name__) from None
