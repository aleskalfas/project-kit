"""The default branch pm works against — the backbone's, read through it (COR-054).

The backbone declares the default branch once — `repository.default-branch` in
`.pkit/project/config.yaml`, `main` when absent — and resolves it for every
reader (COR-054 points 1 and 5). pm reads it through the backbone's reading
command, `pkit friction artefacts --json`, and never reads the declaration,
`$PKIT_CHECK_BASE` or a remote's reference itself:

- `name` is the branch pm cuts work from, targets pull requests at, switches
  to after a merge and holds the hosting service's default to:
  `lifecycle_inference.resolve_base_branch`, `pr_merge.cleanup_local` and
  pre-check's default-branch check all read it here;
- `check_base` is the base a diff-scoped check of pm compares with when none
  is named: `$PKIT_CHECK_BASE`, else the default branch's resolved reference,
  as the backbone names it — the base the core change check reads.

**pm's own `default_branch` is a deprecated alias** of the backbone's key
(COR-054 point 1). While the backbone declares none, a value there still names
the branch, so a project on another branch keeps working — with a warning to
declare it once. Once the backbone declares one, pm's key never overrides it:
it is ignored, with a warning when the two differ. A value equal to the
backbone's is only redundant, and says so. Nothing is migrated: the
backbone's default is `main`, as pm's was.

Reading is forgiving: when the backbone cannot answer — `pkit` absent, a
backbone that names no default branch, a configuration it cannot read — pm
reads its own key, else `main`, as it did before, and warns about nothing.
The backbone is asked once per run, and each warning is given once.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: The backbone's key (COR-054 point 1), and pm's deprecated alias of it.
BACKBONE_KEY = "repository.default-branch"
ALIAS_KEY = "default_branch"

#: The name read when neither the backbone nor the alias can say.
DEFAULT = "main"

#: The backbone's reading command, and the keys pm reads from its document.
ARGV = ("pkit", "friction", "artefacts", "--json")
BRANCH = "default_branch"
BASE = "base"

#: The backbone's source for a declared name (`default_branch.source`).
DECLARED = "configuration"

Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class Reading:
    """What the backbone answered: the default branch's name and whether it was
    declared, and the base a comparison reads (`None` when it names none it can
    compare with). `name` is `None` when the backbone did not answer."""

    name: str | None
    declared: bool
    check_base: str | None
    problem: str | None


_UNANSWERED = Reading(None, False, None, None)

#: One reading per working directory and run; one warning per text.
_read: dict[Path, Reading] = {}
_warned: set[str] = set()


def read(run: Runner = subprocess.run) -> Reading:
    """The backbone's answer for the working directory, asked once per run."""
    here = Path.cwd()
    if here not in _read:
        _read[here] = _ask(run)
    return _read[here]


def name(config: Mapping[str, Any], *, run: Runner = subprocess.run) -> str:
    """The default branch: the backbone's; pm's `default_branch` an alias of it."""
    reading = read(run)
    alias = _alias(config)
    if reading.name is None:
        return alias or DEFAULT
    if alias is None:
        return reading.name
    if alias == reading.name:
        _warn(
            f"project-management's `{ALIAS_KEY}: {alias}` is deprecated and redundant: the "
            f"default branch is the backbone's `{BACKBONE_KEY}` (COR-054) — remove it from "
            f"project-management's project/config.yaml"
        )
        return reading.name
    if reading.declared:
        _warn(
            f"project-management's `{ALIAS_KEY}: {alias}` is deprecated and ignored: the "
            f"backbone declares `{BACKBONE_KEY}: {reading.name}` (COR-054) — remove it from "
            f"project-management's project/config.yaml"
        )
        return reading.name
    _warn(
        f"project-management's `{ALIAS_KEY}: {alias}` is deprecated: declare the default "
        f"branch once, for every reader — `pkit config set {BACKBONE_KEY} {alias} --yes` — "
        f"and remove it from project-management's project/config.yaml; until then the "
        f"backbone's checks read `{reading.name}` (COR-054)"
    )
    return alias


def check_base(*, run: Runner = subprocess.run) -> tuple[str | None, str | None]:
    """The base a diff-scoped check compares with when none is named, and why there is
    none when there is not: `(ref, None)` or `(None, problem)`."""
    reading = read(run)
    if reading.check_base is not None:
        return reading.check_base, None
    return None, reading.problem or f"`{' '.join(ARGV)}` named no base; name one with --base"


def _alias(config: Mapping[str, Any]) -> str | None:
    value = config.get(ALIAS_KEY)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _ask(run: Runner) -> Reading:
    try:
        proc = run(list(ARGV), capture_output=True, text=True, check=False, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return _UNANSWERED
    try:
        document = json.loads(proc.stdout or "") if proc.returncode == 0 else None
    except ValueError:
        document = None
    if not isinstance(document, Mapping):
        return _UNANSWERED
    branch = document.get(BRANCH)
    if not isinstance(branch, Mapping) or not isinstance(branch.get("name"), str):
        return _UNANSWERED
    base = document.get(BASE)
    base = base if isinstance(base, Mapping) else {}
    problem = base.get("problem")
    ref = base.get("ref") if base.get("tip") else None
    return Reading(
        name=branch["name"],
        declared=branch.get("source") == DECLARED,
        check_base=ref if isinstance(ref, str) else None,
        problem=problem if isinstance(problem, str) else None,
    )


def _warn(text: str) -> None:
    if text not in _warned:
        _warned.add(text)
        print(f"warn: {text}", file=sys.stderr)
