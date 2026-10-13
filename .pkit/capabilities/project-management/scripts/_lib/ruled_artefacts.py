"""Which artefacts a change altered, and which of them an accepted rule binds on (#1386).

The `touches-ruled-artefact` floor (DEC-032 D1) requires its reviewer when a
change alters an artefact on which an accepted rule binds, at the base or at
the head. The freshness rule (DEC-028) asks the same question of the author's
changes since a reviewed head. Neither computes it: the backbone answers it
once, in `pkit rule-sets altered --json --base <base> --head <head>` (COR-051
point 7). That command pairs the base's artefacts with the head's as the
change check does, so an artefact is altered when it is added, removed, or its
content differs — never by a move the pairing follows that keeps the
content, nor by a change that only writes a revalidation. A change to the
declared places alone alters the artefacts it brings in or takes out, though
it touches none of their files, so no path of a change says the question may
be skipped (DEC-032 D1). This module runs the command and reads its answer:

  * `ruled_altered(base, head)` — each altered artefact, with how it was
    altered, its file at each state that holds it, and whether an accepted
    rule binds on it at the base or at the head. A rule a pin behind its set
    holds back (the answer's `held`) binds nothing, so it makes no artefact
    ruled. Or why the answer cannot be read, which is never an answer naming
    nothing.

What it needs locally, each failing with its own reason (DEC-032 D1):

  * both commits in this checkout — one it lacks is fetched from origin by its
    object name first (`_lib.author_delta.local_commits`) — and the full
    history, since the backbone finds where the head left the base;
  * a backbone whose `pkit` has the command. One without it is named, with
    the backbone range this capability's package metadata requires.

The command runs as `_lib.friction_answers` runs the change check: the first
`pkit` on PATH, routing off (`PKIT_NO_ROUTE=1`) — the backbone serving the
command that runs this module. The runner is injectable so the consumers'
tests can stand it in.
"""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

try:
    from _lib.author_delta import local_commits
except ImportError:  # pragma: no cover - exercised via spec-loaded fallback
    from author_delta import local_commits  # type: ignore[no-redef]

#: The backbone's command, as a capability's script runs it, and the
#: environment it adds: routing off (the module docstring).
PKIT = ("pkit",)
UNROUTED = {"PKIT_NO_ROUTE": "1"}
COMMAND = ("rule-sets", "altered", "--json")
#: The version of `pkit rule-sets altered --json` this module reads; a document
#: of another is unreadable here, never misread.
SCHEMA_VERSION = 1
#: How long the command may run before its answer is given up on.
TIMEOUT = 600
#: How click refuses a command the backbone does not have.
_NO_SUCH_COMMAND = "No such command"
#: This capability's package metadata, which names the backbone it requires.
PACKAGE = Path(__file__).resolve().parents[2] / "package.yaml"
#: How the backbone says an artefact was altered.
ADDED, REMOVED, CHANGED = "added", "removed", "changed"
CHANGES = (ADDED, REMOVED, CHANGED)


@dataclass(frozen=True)
class AlteredArtefact:
    """One artefact a change altered, as the backbone lists it.

    `location` is the artefact at the head, or at the base for one removed.
    `change` is `added`, `removed` or `changed`. `paths` are its file at each
    state that holds it. `ruled` says an accepted rule binds on it at the base
    or at the head: its `rules` are not empty at one of them. A held rule
    never counts.
    """

    location: str
    change: str
    paths: tuple[str, ...]
    ruled: bool


@dataclass(frozen=True)
class RuledAlteration:
    """The artefacts a change altered, or why they cannot be read.

    `artefacts` is every altered artefact, ruled or not. `ok` is False when
    `error` is set; `artefacts` is then empty and means nothing — a consumer
    reads `error` first.
    """

    artefacts: tuple[AlteredArtefact, ...] = ()
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error

    @property
    def locations(self) -> tuple[str, ...]:
        """The altered artefacts an accepted rule binds on, at either state."""
        return tuple(artefact.location for artefact in self.artefacts if artefact.ruled)

    @property
    def altered(self) -> tuple[str, ...]:
        """Every altered artefact, ruled or not."""
        return tuple(artefact.location for artefact in self.artefacts)


# `(base, head) -> RuledAlteration`, as `ruled_altered`.
RuledFn = Callable[..., RuledAlteration]


def ruled_altered(
    base: str,
    head: str,
    *,
    cwd: str | Path | None = None,
    run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> RuledAlteration:
    """The artefacts the change from `base` to `head` altered, each with
    whether an accepted rule binds on it at either state.

    `base` is compared as the backbone compares a base: the change is the one
    from where `head` left it. See the module docstring for what is read
    locally, and for each reason the answer cannot be read.
    """
    if not base or not head:
        return RuledAlteration(error="the base or the head to compare is unknown")
    missing = local_commits(((head, "the head"), (base, "the base")), cwd=cwd, run=run)
    if missing:
        return RuledAlteration(error=missing)
    argv = [*PKIT, *COMMAND, "--base", base, "--head", head]
    command = f"`pkit {' '.join(COMMAND)} --base {base[:7]} --head {head[:7]}`"
    try:
        proc = run(
            argv,
            cwd=cwd,
            env={**os.environ, **UNROUTED},
            capture_output=True,
            text=True,
            check=False,
            timeout=TIMEOUT,
        )
    except FileNotFoundError as exc:
        return RuledAlteration(error=f"{command}: `pkit` is not on PATH ({exc})")
    except subprocess.TimeoutExpired:
        return RuledAlteration(error=f"{command}: it did not answer within {TIMEOUT}s")
    except OSError as exc:
        return RuledAlteration(error=f"{command}: it could not be run ({exc})")
    stderr = proc.stderr or ""
    if proc.returncode != 0:
        if _NO_SUCH_COMMAND in stderr:
            return RuledAlteration(error=_backbone_lacks_the_command())
        said = [line.strip() for line in stderr.splitlines() if line.strip()]
        return RuledAlteration(
            error=f"{command}: it exited {proc.returncode}" + (f": {said[-1]}" if said else "")
        )
    entries = _entries(proc.stdout or "")
    if isinstance(entries, str):
        return RuledAlteration(error=f"{command}: {entries}")
    return RuledAlteration(
        artefacts=tuple(
            AlteredArtefact(
                location=str(sides[-1]["location"]),
                change=change,
                paths=tuple(dict.fromkeys(str(side["path"]) for side in sides)),
                ruled=any(side["rules"] for side in sides),
            )
            for change, sides in entries
        )
    )


def _entries(stdout: str) -> list[tuple[str, list[Mapping[str, Any]]]] | str:
    """Each altered artefact's change and states — the base's, the head's,
    those that hold it — from the command's document, or why the document
    cannot be read."""
    try:
        document = json.loads(stdout)
    except ValueError:
        return "its answer is not JSON"
    if not isinstance(document, dict):
        return "its answer is not a document"
    version = document.get("schema_version")
    if version != SCHEMA_VERSION:
        return f"it answered schema_version {version!r}; this reads {SCHEMA_VERSION}"
    artefacts = document.get("artefacts")
    if not isinstance(artefacts, list):
        return "its document lists no artefacts"
    out: list[tuple[str, list[Mapping[str, Any]]]] = []
    for entry in artefacts:
        if not isinstance(entry, dict):
            return "it lists an artefact that is not a mapping"
        change = entry.get("change")
        if change not in CHANGES:
            return f"it lists an artefact altered as {change!r}, which this does not read"
        sides = [entry.get("base"), entry.get("head")]
        present = [side for side in sides if side is not None]
        if not present or not all(_side_reads(side) for side in present):
            return "it lists an artefact without a readable location, path and rules"
        out.append((str(change), present))
    return out


def _side_reads(side: Any) -> bool:
    return (
        isinstance(side, dict)
        and isinstance(side.get("location"), str)
        and isinstance(side.get("path"), str)
        and isinstance(side.get("rules"), list)
    )


def _backbone_lacks_the_command() -> str:
    """Why a backbone without the command cannot answer, naming the backbone
    this capability requires."""
    required = _required_backbone()
    needs = (
        f"a backbone {required} (project-management's `requires_backbone`)"
        if required
        else "a backbone that ships it"
    )
    return (
        "the backbone's `pkit` has no `pkit rule-sets altered` command, which the "
        f"touches-ruled-artefact floor reads. project-management needs {needs}: upgrade pkit"
    )


def _required_backbone() -> str:
    """The `requires_backbone` range of this capability's package metadata, or
    '' when it cannot be read: a detail of a message, never a decision."""
    try:
        data = YAML(typ="safe").load(PACKAGE.read_text(encoding="utf-8"))
    except (OSError, YAMLError):
        return ""
    found = data.get("requires_backbone") if isinstance(data, dict) else None
    return f"`{found}`" if isinstance(found, str) and found else ""
