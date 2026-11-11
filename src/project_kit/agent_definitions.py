"""The command's one loader of the picker of an agent's definition and of the
lifecycle's reader of capability records (ADR-087).

Which definition of a name is the agent is answered by one module,
`.pkit/agents/definition_source.py`, which learns which capabilities are
installed, their skips and the project's choices from one reader,
`.pkit/lifecycle/capability_records.py`. Both are propagated neutral code, which
the adapters' scripts load in the project's tree, where this package is not
importable, so the command loads the same files rather than keeping a pick of
its own (ADR-003).

**Which tree's copy.** A command loads both from the project's tree, as it loads
the reader of tool access, but for a command that changes which capabilities are
installed: an install, a registration, an uninstall and a version transition
load them from the release the command brings, its source tree (`release=`), so
a project that predates the modules can still move to the release that ships
them (ADR-087 point 2). Sync, which its guard runs only at the release the
project records, loads them from that release too, so the sync that a refusal
names can restore them. Either way the records read are the project's.

**A command that cannot reach either module** refuses that step: `Unreachable`,
a `click.ClickException`, names the side to bring up to date, by the comparison
of backbone versions the reader of tool access uses (ADR-087 point 5). A check
that reports rather than refuses, such as the validator, catches it.
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

import click

from project_kit import agent_tool_access

#: Where each module lies, relative to a `.pkit/` tree.
PICKER = Path("agents") / "definition_source.py"
RECORDS = Path("lifecycle") / "capability_records.py"

#: How the picker writes a capability's place: this, then the capability's name.
CAPABILITY_PLACE = "capability:"

#: The functions of each module the command calls.
PICKER_FUNCTIONS = ("pick", "digest", "capability_place", "place_capability", "place_folder")
RECORDS_FUNCTIONS = ("read_records", "read_skips")

_MODULE_NAMES = {
    PICKER: "pkit_agents_definition_source",
    RECORDS: "pkit_lifecycle_capability_records",
}


class Unreachable(click.ClickException):
    """A module the command calls cannot be reached; the message names the fix."""


def answer(target_root: Path, *, release: Path | None = None) -> Any:
    """The picker's answer for the project at *target_root*: which definition of
    every name some place ships is the agent (ADR-087 point 2).

    *release* is the `.pkit/` tree of the release the command brings, for a
    command that changes which capabilities are installed; otherwise both modules
    are the project's. Raises `Unreachable` where either cannot be reached.
    """
    picker = load_picker(target_root, release=release)
    try:
        return picker.pick(target_root)
    except picker.RecordsUnreachable as exc:
        raise Unreachable(
            f"the picker of an agent's definition cannot read the records: {exc}; "
            f"{_fix(target_root, release)}"
        ) from None


def agents(picked: Any) -> dict[str, tuple[str, Path]]:
    """Each name of the picker's answer *picked* whose agent has one text, with the
    agent's place and its file.

    Left out: a name whose agent is refused before its text is read, since its
    place holds both layouts; one with no agent; and one the picker cannot tell.
    The validator reports each (ADR-087 point 3).
    """
    return {
        name: (pick.agent.place, pick.file)
        for name, pick in sorted(picked.picks.items())
        if pick.file is not None
    }


def place_owner(place: str) -> str:
    """Who ships the definitions of the picker's *place*: `project`, `core`, or the
    capability's name, from its place `capability:<name>`."""
    return place.removeprefix(CAPABILITY_PLACE)


def records(target_root: Path, *, release: Path | None = None) -> Any:
    """What the project at *target_root* records of its installed capabilities
    (ADR-087 point 1). Raises `Unreachable` where the reader cannot be reached."""
    return load_records_reader(target_root, release=release).read_records(target_root)


def skips(
    target_root: Path, capability: str, *, release: Path | None = None
) -> tuple[tuple[str, str], ...]:
    """The skips capability *capability*'s manifest records, as `(kind, name)` pairs.

    A manifest that cannot be read records nothing here: a refresh's restamp then
    writes the skips it is given, which project-kit#2958 takes up. Raises
    `Unreachable` where the reader cannot be reached.
    """
    reader = load_records_reader(target_root, release=release)
    return tuple(reader.read_skips(target_root, capability).skipped)


def load_picker(target_root: Path, *, release: Path | None = None) -> ModuleType:
    """The picker, from *release* where given, else from the project's tree.

    The lifecycle's reader beside it is checked too, since the picker loads it
    from its own tree.
    """
    load_records_reader(target_root, release=release)
    return _load(PICKER, (*PICKER_FUNCTIONS, "RecordsUnreachable"), target_root, release)


def load_records_reader(target_root: Path, *, release: Path | None = None) -> ModuleType:
    """The lifecycle's reader of capability records, from *release* where given,
    else from the project's tree."""
    return _load(RECORDS, RECORDS_FUNCTIONS, target_root, release)


def _load(
    module: Path, functions: Sequence[str], target_root: Path, release: Path | None
) -> ModuleType:
    """The module at *module* in the `.pkit/` tree the caller names, holding each of
    *functions*, loaded without writing bytecode into the tree."""
    tree = release if release is not None else target_root / ".pkit"
    path = tree / module
    shown = path.as_posix() if release is not None else (Path(".pkit") / module).as_posix()
    if not path.is_file():
        raise Unreachable(f"{shown} is not there; {_fix(target_root, release)}")
    spec = importlib.util.spec_from_file_location(_MODULE_NAMES[module], path)
    if spec is None or spec.loader is None:
        raise Unreachable(f"{shown} cannot be loaded; {_fix(target_root, release)}")
    loaded = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(loaded)
    except Exception as exc:
        raise Unreachable(
            f"{shown} cannot be loaded ({exc}); {_fix(target_root, release)}"
        ) from None
    finally:
        sys.dont_write_bytecode = previous
    missing = [name for name in functions if getattr(loaded, name, None) is None]
    if missing:
        raise Unreachable(
            f"{shown} has no {', '.join(missing)}, which this command calls; "
            f"{_fix(target_root, release)}"
        )
    return loaded


def _fix(target_root: Path, release: Path | None) -> str:
    """Which side to bring up to date: the project's tree or this command."""
    if release is not None:
        return "the running pkit's own tree lacks it: reinstall or upgrade pkit"
    return agent_tool_access.behind(target_root)
