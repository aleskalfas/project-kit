"""The default branch pm works against, and every base it names — the backbone's (COR-054).

The backbone declares the default branch once — `repository.default-branch` in
`.pkit/project/config.yaml`, `main` when absent — and resolves it, and any
branch named as a base, one way for every reader (COR-054 points 1, 2 and 5).
pm reads both through the backbone's reading command, `pkit repository base
--json`, and never reads the declaration, `$PKIT_CHECK_BASE` or a remote's
reference itself, nor computes where a branch left its base:

- `name(config)` is the branch pm targets pull requests at, switches to after
  a merge and holds the hosting service's default to:
  `lifecycle_inference.resolve_base_branch`, `pr_merge.cleanup_local` and
  pre-check's default-branch check read it here;
- `branch(name)` is a branch named as a base — the default branch, or a
  DEC-013 integration branch — resolved as the backbone resolves every one:
  the commit start-work cuts from and create-draft counts commits beyond;
- `check_base(explicit)` is a diff-scoped check's base and where HEAD left it:
  `explicit`, else `$PKIT_CHECK_BASE`, else the default branch.

**pm never guesses** (COR-054 point 4). When the backbone cannot answer — no
`pkit`, a timeout, a failed run, a backbone that predates the command —
`Unanswered` names the cause: a verb that acts on the branch refuses, and a
reader that only reports warns with it. What the backbone says on standard
error — a branch read from the local branch, say — is passed on, once.

**pm's own `default_branch` is transitional.** The 0.55.0 upgrade migration
carries a value other than `main` over to the backbone's key and removes pm's
in every case (COR-054 point 1). Until a project runs it, a value that differs
from the backbone's names the branch only while the backbone declares none,
with a warning to upgrade; a declared value always wins, and pm's is ignored
with a warning. A value equal to the backbone's says nothing.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: The backbone's key (COR-054 point 1), and pm's transitional one.
BACKBONE_KEY = "repository.default-branch"
ALIAS_KEY = "default_branch"

#: The backbone's reading command, how long pm waits for it, and the version of its
#: document pm reads — another is refused rather than misread.
ARGV = ("pkit", "repository", "base", "--json")
TIMEOUT = 60
VERSION = 1

#: The backbone's source for a declared name (`default_branch.source`).
DECLARED = "configuration"

Runner = Callable[..., subprocess.CompletedProcess[str]]


class Unanswered(Exception):
    """The backbone did not answer; the message names the cause and what to do."""


@dataclass(frozen=True)
class Branch:
    """The default branch as the backbone declares and resolves it."""

    name: str
    declared: bool
    ref: str | None
    commit: str | None
    problem: str | None


@dataclass(frozen=True)
class Base:
    """A base as the backbone resolves it: the reference read, its commit (`tip`),
    where HEAD left it (`fork`) — or why not (`problem`); `tip` may name a commit
    even then, when only the fork is missing. `resolved` is `remote` for a
    remote-tracking reference, `local` for a local branch, None for a revision
    read as named."""

    ref: str
    tip: str | None
    fork: str | None
    problem: str | None
    resolved: str | None = None


@dataclass(frozen=True)
class Reading:
    """One answer of the backbone's reading command."""

    default_branch: Branch
    base: Base


#: One answer per working directory and base named, per run; one warning per text.
_read: dict[tuple[Path, str | None], Reading | Unanswered] = {}
_warned: set[str] = set()


def read(explicit: str | None = None, *, run: Runner = subprocess.run) -> Reading:
    """The backbone's answer for the working directory — with `explicit` the base it
    reads — asked once per run. Raises Unanswered."""
    key = (Path.cwd(), explicit)
    if key not in _read:
        try:
            _read[key] = _ask(explicit, run)
        except Unanswered as exc:
            _read[key] = exc
    answer = _read[key]
    if isinstance(answer, Unanswered):
        raise answer
    return answer


def name(config: Mapping[str, Any], *, run: Runner = subprocess.run) -> str:
    """The default branch: the backbone's; pm's own `default_branch` only until the
    upgrade carries it over. Raises Unanswered."""
    backbone = read(run=run).default_branch
    alias = _alias(config)
    if alias is None or alias == backbone.name:
        return backbone.name
    if backbone.declared:
        warn(
            f"project-management's `{ALIAS_KEY}: {alias}` is ignored: the backbone declares "
            f"`{BACKBONE_KEY}: {backbone.name}` (COR-054) — remove it from "
            f"project-management's project/config.yaml"
        )
        return backbone.name
    warn(
        f"project-management's `{ALIAS_KEY}: {alias}` names the default branch until the "
        f"upgrade carries it over (`pkit upgrade`), while the backbone's checks read "
        f"`{backbone.name}`: declare it once, for every reader — `pkit config set "
        f"{BACKBONE_KEY} {alias} --yes` — and remove it from project-management's "
        f"project/config.yaml (COR-054)"
    )
    return alias


def branch(named: str, *, run: Runner = subprocess.run) -> Base:
    """The branch `named` resolved as the backbone resolves every branch named as a
    base (COR-054 point 2) — asked afresh, since a fetch may just have moved it.
    Raises Unanswered."""
    _read.pop((Path.cwd(), named), None)
    return read(named, run=run).base


def check_base(explicit: str | None = None, *, run: Runner = subprocess.run) -> Base:
    """A diff-scoped check's base: `explicit`, else `$PKIT_CHECK_BASE`, else the default
    branch, with where HEAD left it (COR-054 point 3). Raises Unanswered."""
    return read(explicit, run=run).base


def warn(text: str) -> None:
    """Say `text` on standard error, once per run."""
    if text not in _warned:
        _warned.add(text)
        print(f"warn: {text}", file=sys.stderr)


def _alias(config: Mapping[str, Any]) -> str | None:
    value = config.get(ALIAS_KEY)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _ask(explicit: str | None, run: Runner) -> Reading:
    argv = [*ARGV, *([f"--base={explicit}"] if explicit is not None else [])]
    command = f"`{' '.join(argv)}`"
    try:
        proc = run(argv, capture_output=True, text=True, check=False, timeout=TIMEOUT)
    except FileNotFoundError as exc:
        raise _unanswered(command, f"`pkit` is not on PATH ({exc})") from exc
    except subprocess.TimeoutExpired as exc:
        raise _unanswered(command, f"it did not answer within {TIMEOUT}s") from exc
    except OSError as exc:
        raise _unanswered(command, f"it could not be run ({exc})") from exc
    for line in (proc.stderr or "").splitlines():
        if line.startswith("warning: "):
            warn(line.removeprefix("warning: "))
    if proc.returncode != 0:
        said = [line for line in (proc.stderr or "").splitlines() if line.strip()]
        if "No such command" in (proc.stderr or ""):
            raise _unanswered(
                command, "the installed backbone predates it — upgrade it (`pkit upgrade`)"
            )
        raise _unanswered(
            command, f"it exited {proc.returncode}" + (f": {said[-1].strip()}" if said else "")
        )
    try:
        document = json.loads(proc.stdout or "")
    except ValueError as exc:
        raise _unanswered(command, "its answer is not JSON") from exc
    version = document.get("schema_version") if isinstance(document, Mapping) else None
    if version != VERSION:
        raise _unanswered(command, f"it answered schema_version {version!r}; pm reads {VERSION}")
    found = _reading(document)
    if found is None:
        raise _unanswered(command, "its answer names no default branch or base")
    return found


def _reading(document: Any) -> Reading | None:
    if not isinstance(document, Mapping):
        return None
    branch_doc = document.get("default_branch")
    base_doc = document.get("base")
    if not isinstance(branch_doc, Mapping) or not isinstance(base_doc, Mapping):
        return None
    named = branch_doc.get("name")
    ref = base_doc.get("ref")
    if not isinstance(named, str) or not isinstance(ref, str):
        return None
    return Reading(
        Branch(
            name=named,
            declared=branch_doc.get("source") == DECLARED,
            ref=_text(branch_doc.get("ref")),
            commit=_text(branch_doc.get("commit")),
            problem=_text(branch_doc.get("problem")),
        ),
        Base(
            ref=ref,
            tip=_text(base_doc.get("tip")),
            fork=_text(base_doc.get("fork")),
            problem=_text(base_doc.get("problem")),
            resolved=_text(base_doc.get("resolved")),
        ),
    )


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _unanswered(command: str, cause: str) -> Unanswered:
    return Unanswered(
        f"the backbone did not say which branch is settled — {command}: {cause}; pm does not "
        f"guess it (COR-054 point 4)"
    )
