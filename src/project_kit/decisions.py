"""Decision-record authoring (the deterministic part of `pkit new decision`).

Python port of the bash dispatcher's `cmd_new_decision`. Behaviour
preserved exactly for the `core` and `project` namespaces: same
namespace/slug validation, same next-number computation per namespace,
same frontmatter shape, same four section headers, same
git-config-derived author resolution, same "Stamped: ..." output line.
The conversational layer (drafting the body, discipline self-checks) is
the `decision-author` skill's job per COR-005's "Skill / command pairing".

The `adr` namespace (per COR-025) extends this surface: ADR records live
outside `.pkit/` at the adopter-declared `<adr-records>` overlay location
(`.pkit/agents/project/overlay.yaml` → `adr-records[0]`). The stamping
command resolves the path from the overlay; refuses if missing, points
inside `.pkit/`, or doesn't exist on disk.

Beyond the three fixed namespaces, the command accepts a **capability
name** (Feature #162): `pkit new decision <capability> <slug>` stamps a
`DEC-NNN` record under `.pkit/capabilities/<capability>/decisions/`, with
the next number scoped to that capability (each capability is its own
DEC id-space). The capability must exist; the command refuses otherwise.
"""

from __future__ import annotations

import datetime as _dt
import re
import subprocess
from pathlib import Path
from typing import Literal

import click
from ruamel.yaml import YAML

# The three fixed namespaces. A `new decision` namespace argument that is none
# of these is interpreted as a capability name (DEC id-space).
FixedNamespace = Literal["core", "project", "adr"]
# `Namespace` widens to `str` because a capability name is also accepted.
Namespace = str

_FIXED_NAMESPACES: frozenset[str] = frozenset({"core", "project", "adr"})

_OVERLAY_PATH = Path(".pkit") / "agents" / "project" / "overlay.yaml"

_SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


# Stamped on every new decision record. Matches the bash dispatcher's heredoc.
DECISION_TEMPLATE = """\
---
id: {prefix}-{nnn}
title: <short imperative title>
status: proposed
date: {today}
author: {author}
---

## Context

## Decision

## Rationale

## Implications
"""


def stamp_decision(target_root: Path, namespace: Namespace, slug: str) -> Path:
    """Stamp a new decision-record stub.

    `core`/`project` namespaces stamp under `<target>/.pkit/decisions/<namespace>/`
    with `COR`/`PRJ` prefix. `adr` namespace resolves the target directory via
    `resolve_adr_records_dir(target_root)` and stamps with `ADR` prefix. Any
    other `namespace` value is treated as a **capability name** (Feature #162):
    the record stamps under `.pkit/capabilities/<namespace>/decisions/` with the
    `DEC` prefix, numbered independently within that capability.

    Returns the stamped file path. Raises `click.ClickException` for any
    user-facing precondition failure (invalid slug, missing decisions dir,
    duplicate slug, overlay misconfiguration, unknown capability). Writes the
    file synchronously.
    """
    if not _SLUG_RE.match(slug):
        raise click.ClickException(
            "slug must be kebab-case (lowercase letters, digits, single hyphens)."
        )

    if namespace == "adr":
        prefix = "ADR"
        decisions_dir = resolve_adr_records_dir(target_root)
    elif namespace in ("core", "project"):
        prefix = "COR" if namespace == "core" else "PRJ"
        decisions_dir = target_root / ".pkit" / "decisions" / namespace
        if not decisions_dir.is_dir():
            raise click.ClickException(f"{decisions_dir} does not exist.")
    else:
        prefix = "DEC"
        decisions_dir = _resolve_capability_decisions_dir(target_root, namespace)

    if any(decisions_dir.glob(f"{prefix}-*-{slug}.md")):
        raise click.ClickException(
            f"a record with slug {slug!r} already exists in the {namespace} namespace."
        )

    next_num = _next_number(decisions_dir, prefix)
    nnn = f"{next_num:03d}"

    target = decisions_dir / f"{prefix}-{nnn}-{slug}.md"
    today = _today()
    author = _resolve_author()

    target.write_text(
        DECISION_TEMPLATE.format(prefix=prefix, nnn=nnn, today=today, author=author),
        encoding="utf-8",
    )
    return target


def resolve_adr_records_dir(target_root: Path) -> Path:
    """Resolve the ADR-records directory from the agents overlay (per COR-024/COR-025).

    Reads `.pkit/agents/project/overlay.yaml`, takes the first entry of the
    top-level `adr-records:` list, validates that the resolved path is
    outside `.pkit/` (per COR-025's location rationale), and confirms the
    directory exists on disk. Refuses with a helpful message at each gate
    — never auto-creates the directory (typos shouldn't become directories;
    path placement is a deliberate decision).

    Per-agent overrides for `adr-records` are not consulted here; the
    canonical write target is the top-level overlay key. Adopters who
    set conflicting per-agent overrides should reconcile them by hand.
    """
    overlay_path = target_root / _OVERLAY_PATH
    if not overlay_path.is_file():
        raise click.ClickException(
            f"{_OVERLAY_PATH} not found. ADR support requires the agents overlay; see COR-024."
        )

    yaml = YAML(typ="safe")
    try:
        data = yaml.load(overlay_path)
    except Exception as exc:  # noqa: BLE001 — surface any YAML error as a click message
        raise click.ClickException(f"failed to parse {_OVERLAY_PATH}: {exc}") from exc
    if not isinstance(data, dict):
        raise click.ClickException(f"{_OVERLAY_PATH}: expected a mapping at top level.")

    adr_records = data.get("adr-records")
    if not adr_records:
        raise click.ClickException(
            f"overlay key 'adr-records' is missing or empty in {_OVERLAY_PATH}. "
            "Add a path like:\n\n"
            "  adr-records:\n"
            "    - docs/architecture/decisions/\n\n"
            "See COR-024 (overlay placeholder) and COR-025 (ADR decision space)."
        )
    if not isinstance(adr_records, list) or not isinstance(adr_records[0], str):
        raise click.ClickException(
            f"overlay key 'adr-records' must be a non-empty list of path strings "
            f"in {_OVERLAY_PATH}. See COR-024 / COR-025."
        )

    first_path = adr_records[0].rstrip("/")
    candidate = (target_root / first_path).resolve()
    pkit_root = (target_root / ".pkit").resolve()
    if candidate == pkit_root or pkit_root in candidate.parents:
        raise click.ClickException(
            f"adr-records path {first_path!r} is inside .pkit/. ADR records must live "
            "outside .pkit/ — they describe the adopter's project, not the methodology "
            "(per COR-025)."
        )

    if not candidate.is_dir():
        raise click.ClickException(
            f"adr-records directory {first_path!r} does not exist. "
            f"Create it first: mkdir -p {first_path}"
        )

    return candidate


def _resolve_capability_decisions_dir(target_root: Path, capability: str) -> Path:
    """Resolve a capability's `decisions/` directory, refusing if the capability is absent.

    A capability lives at `.pkit/capabilities/<capability>/` and is valid
    when it carries a `package.yaml` (the same existence contract the
    capability lifecycle uses). The `decisions/` subdirectory is created if
    the capability exists but hasn't held a DEC record yet — stamping the
    first DEC into a capability is a normal first step, not an error. An
    absent or non-capability directory is refused with a clear message so a
    typo'd capability name doesn't silently create a stray tree.
    """
    cap_dir = target_root / ".pkit" / "capabilities" / capability
    if not (cap_dir / "package.yaml").is_file():
        available = _list_capability_names(target_root)
        avail_note = (
            f" Available capabilities: {', '.join(available)}."
            if available
            else " No capabilities are present under .pkit/capabilities/."
        )
        raise click.ClickException(
            f"unknown namespace {capability!r}: not one of core/project/adr and "
            f"no capability at .pkit/capabilities/{capability}/.{avail_note}"
        )
    decisions_dir = cap_dir / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    return decisions_dir


def _list_capability_names(target_root: Path) -> list[str]:
    """Sorted names of capabilities present under `.pkit/capabilities/` (each has a package.yaml)."""
    caps_dir = target_root / ".pkit" / "capabilities"
    if not caps_dir.is_dir():
        return []
    return sorted(
        entry.name
        for entry in caps_dir.iterdir()
        if entry.is_dir() and (entry / "package.yaml").is_file()
    )


def _next_number(decisions_dir: Path, prefix: str) -> int:
    """Highest NNN in `<prefix>-NNN-*.md` filenames + 1, defaulting to 1."""
    highest = 0
    for path in decisions_dir.glob(f"{prefix}-*.md"):
        if not path.is_file():
            continue
        # Filename: <prefix>-NNN-<slug>.md → NNN is the digits between the
        # prefix and the next hyphen.
        stem = path.name.removeprefix(f"{prefix}-")
        num_str = stem.split("-", 1)[0]
        try:
            num = int(num_str, base=10)
        except ValueError:
            continue
        if num > highest:
            highest = num
    return highest + 1


def _resolve_author() -> str:
    """Read `git config user.name` and `user.email`; format as `Name <email>`.

    Falls back to `Name` (no email), then `<unknown>` if neither available.
    Mirrors the bash dispatcher's resolution order.
    """
    name = _git_config("user.name")
    email = _git_config("user.email")
    if name and email:
        return f"{name} <{email}>"
    if name:
        return name
    return "<unknown>"


def _today() -> str:
    """Today's date as ISO 8601 (`YYYY-MM-DD`). Indirected for test pinning."""
    return _dt.date.today().isoformat()


def _git_config(key: str) -> str:
    try:
        result = subprocess.run(["git", "config", key], capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()
