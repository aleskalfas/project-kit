"""The designer's grant: the paths the agents overlay gives `graphic-designer` through the
capability's category `visual-communication.work` (DEC-030 point 5, COR-073).

- **Read as the deploy reads it.** The overlay, `.pkit/agents/project/overlay.yaml`, gives
  the category a value at its top level, and the designer's own block under `overrides:`
  replaces it, never merged with it. A list gives each of its items, any other value
  gives itself, and an item with no value gives nothing. A key that is absent, or holds no
  value, gives the category no value: the deploy then skips the designer. Copied in
  substance from the backbone's `agents_overlay.OverlayValues.resolve`, which the deploy's
  resolver is pinned to: a capability cannot import the backbone (ADR-057 point 1). A test
  pins the two to one answer.
- **Paths read as written.** A path is relative to the repository's top, with `/`; a
  leading `./`, a trailing `/` and a `..` within it are read away. A path *covers* a
  location where it is the location or a folder that holds it, as the check of owners reads
  two paths (ADR-051 point 3), so a pattern such as `visual/**` covers no folder. A path
  lies inside the methodology's folder where it is `.pkit` or lies under it.
- **The line to change.** Moving the location names the overlay line a person changes
  with it (`moved_with`). The capability writes nothing in the agents' area: the overlay's
  writers are the backbone's (COR-073 point 4).

Reads only, and needs no network.
"""

from __future__ import annotations

import posixpath
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from _lib.reading import ReadError, read_yaml

#: The overlay category the capability declares for its designer's writes, in
#: `package.yaml`'s `write_categories`.
CATEGORY = "visual-communication.work"

#: The one agent that owns the category.
OWNER = "graphic-designer"

#: The agents overlay, relative to the project root (COR-013 point 5).
OVERLAY = ".pkit/agents/project/overlay.yaml"

#: The overlay's block of per-agent values.
OVERRIDES = "overrides"

#: The methodology's own folder, where the visual work never lies (DEC-002 point 1).
METHODOLOGY = ".pkit"

#: The overlay's top-level line of the category, in words.
TOP_LINE = f"the `{CATEGORY}:` line of {OVERLAY}"


@dataclass(frozen=True)
class Grant:
    """What the overlay gives the designer's category: the key that gives it, and its
    paths as written, or None where that key holds no value."""

    key: str
    paths: tuple[str, ...] | None

    @property
    def overridden(self) -> bool:
        """Whether the designer's own block gives the value."""
        return self.key != CATEGORY

    @property
    def line(self) -> str:
        """The overlay line that gives the value, in words."""
        if self.overridden:
            return f"`{CATEGORY}` under `{OVERRIDES}.{OWNER}` in {OVERLAY}"
        return TOP_LINE


def granted(root: Path) -> Grant | None:
    """What the overlay at `root` gives the designer's category, or None where no key gives
    it. Raises ReadError where the overlay cannot be read."""
    path = root / OVERLAY
    if not path.is_file() or path.stat().st_size == 0:
        return None
    data = read_yaml(path)
    if not isinstance(data, Mapping):
        return None
    overrides = data.get(OVERRIDES)
    block = overrides.get(OWNER) if isinstance(overrides, Mapping) else None
    if isinstance(block, Mapping) and CATEGORY in block:
        return Grant(f"{OVERRIDES}.{OWNER}.{CATEGORY}", _paths(block[CATEGORY]))
    if CATEGORY in data:
        return Grant(CATEGORY, _paths(data[CATEGORY]))
    return None


def _paths(value: object) -> tuple[str, ...] | None:
    if value is None:
        return None
    items = value if isinstance(value, list) else [value]
    return tuple(str(item) for item in items if item is not None)


def moved_with(root: Path) -> str:
    """The designer's grant at `root` in words, as what a person moves with the location:
    its overlay line, and for the top-level line, the command that moves it while it stays
    as written (COR-073 point 5). The top-level line where the overlay cannot be read."""
    try:
        given = granted(root)
    except (ReadError, OSError):
        given = None
    if given is not None and given.overridden:
        return f"the designer's grant, {given.line}"
    return (
        f"the designer's grant, {TOP_LINE}, which `pkit agents reconcile --write` moves while "
        f"it stays as pkit wrote it"
    )


def relative(root: Path, path: str) -> str | None:
    """`path`, an entry of the grant, relative to the repository's top at `root`: `.` for
    the top itself, None for an empty entry or one outside the repository."""
    text = path.strip()
    if not text:
        return None
    given = PurePosixPath(text)
    if given.is_absolute():
        tops = {PurePosixPath(root.as_posix()), PurePosixPath(root.resolve().as_posix())}
        within = [given.relative_to(top) for top in tops if given.is_relative_to(top)]
        if not within:
            return None
        text = within[0].as_posix()
    found = posixpath.normpath(text)
    if found == ".." or found.startswith("../"):
        return None
    return found


def covers(rel: str, location: str) -> bool:
    """Whether the repository-relative path `rel` is the location or a folder that holds
    it."""
    return rel in (".", location) or location.startswith(f"{rel}/")


def in_methodology(rel: str) -> bool:
    """Whether the repository-relative path `rel` is the methodology's folder or lies under
    it."""
    return rel == METHODOLOGY or rel.startswith(f"{METHODOLOGY}/")
