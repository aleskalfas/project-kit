"""Agent stamping (per COR-013 + COR-015).

The deterministic part of `pkit new agent`: file stamping with the
unified frontmatter shape and canonical body sections. The conversational
layer (slug judgement, role-vs-procedure framing, reads/owns/needs
discipline) is the `agent-author` skill's job per COR-005's "Skill /
command pairing".

Layout per COR-015: a new agent stamps flat as `<name>.md`. If helpers
materialise later, the author migrates to folder form (`<name>/<name>.md`
+ siblings) as a separate gesture.

Namespaces: `core` and `project` stamp under `.pkit/agents/<namespace>/`; any
other namespace names a capability (COR-017, COR-026) and stamps under
`.pkit/capabilities/<capability>/agents/` — the capability must exist, the
`agents/` folder is created on first use, the same shape as
`pkit new decision <capability>`.
"""

from __future__ import annotations

import re
from pathlib import Path

import click

from project_kit.capability_namespace import (
    CAPABILITIES_DIR,
    capability_names,
    resolve_capability_dir,
)

# The namespaces under `.pkit/agents/`. Any other namespace is a capability name.
AREA_NAMESPACES: tuple[str, ...] = ("core", "project")
# `Namespace` widens to `str` because a capability name is also accepted.
Namespace = str

_AGENTS_DIR = Path(".pkit") / "agents"

_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


# The storyboard `--with-storyboard` stamps beside the agent (COR-016). The
# agent declares it by this bare sibling filename — the portable form the
# agents README prescribes — and its body cites the same name, so the fresh
# pair is mutually declared and passes `pkit refs validate` as stamped.
STORYBOARD_FILE = "storyboard.md"
_STORYBOARDS_KEY = f"storyboards:\n  - {STORYBOARD_FILE}\n"
_STORYBOARD_LOAD = (
    f"Load your storyboard from `{STORYBOARD_FILE}` with the Read tool at session "
    "start and follow it for the scripted scenarios.\n\n"
)

# Per COR-013's frontmatter schema + agents/README's body conventions.
# Lists are empty placeholders the author fills in; description is a
# single-line placeholder the author rewrites. Tools default to a
# read-oriented set; the author narrows or widens per the agent's role.
# `{storyboards}` and `{storyboard_load}` are empty for a flat stamp.
AGENT_TEMPLATE = """\
---
name: {name}
description: One-line summary of what this agent does and when to invoke it.
tools: [Read, Glob, Grep, Bash]
{storyboards}reads:
  paths: []
  records: []
  patterns: []
owns: []
needs: []
---

# {title}

You are the **{name}** for this project. <one paragraph: role, scope, what makes you distinct from other agents>.

## When to invoke this agent

- <trigger 1>
- <trigger 2>

## Files you own

<List the paths this agent has write authority over. Use `<category-name>` placeholders — the categories of the project's agent overlay — for adopter-specific paths; declare them in frontmatter `reads.patterns` and `owns` as well. A reviewer owns none; if it can execute, add the `## What read-only covers` section every such reviewer carries, word for word, before `## Intermediate files` (the agents README's "Reviewers" paragraph).>

## Key documents to read

<List the paths, records (COR-NNN / PRJ-NNN), and hook contracts this agent consults at task time. Each must also appear in frontmatter `reads`.>

## How you work

{storyboard_load}<Procedural body: numbered steps if the agent follows a fixed sequence; principles if the role is more judgement-bearing. Cite records by ID where authority is invoked.>

## Intermediate files

Keep intermediate files — drafts, scripts, captured output, notes — in the agent workspace, `.agent-workspace/` at the repository root (a worktree's own root in a worktree), and nowhere else outside the repository; it is excluded from version control and granted to every agent, so write intermediate files there with the file tools — a shell redirect into it is judged like any other shell write (the workspace rule in the core rules).
"""  # noqa: E501 — each paragraph of the generated agent is one line


def stamp_new_agent(
    target_root: Path,
    name: str,
    namespace: Namespace,
    *,
    with_storyboard: bool = False,
    dry_run: bool = False,
) -> Path:
    """Stamp a new agent file in `namespace`'s agents folder.

    `core` / `project` stamp under `.pkit/agents/<namespace>/`; a capability
    name stamps under `.pkit/capabilities/<capability>/agents/` (see
    `agents_dir_for`).

    Default: flat layout (`<name>.md`). When `with_storyboard=True`,
    stamps folder layout per COR-015 (`<name>/<name>.md`) plus a sibling
    `storyboard.md` scaffold per COR-016 — for agents that drive
    scripted interaction scenarios. Both sides are declared as stamped: the
    agent's `storyboards:` names the sibling and its body cites it, and the
    storyboard's `consumers:` names the agent.

    Refuses if the name is already taken anywhere agents ship from — core,
    project, or any capability — since the deploy resolves one agent per
    name and a colliding one would mask the other. Surface the collision
    instead of silently shadowing.

    Returns the agent file path (not the storyboard). When stamping
    folder-form, that's `<agents folder>/<name>/<name>.md`.
    """
    _validate_name(name)
    ns_dir = agents_dir_for(target_root, namespace)

    for _, location in agent_locations(target_root):
        existing = find_agent_file(location, name)
        if existing is not None:
            raise click.ClickException(
                f"agent {name!r} already exists at {existing.relative_to(target_root)}."
            )

    title = _name_to_title(name)
    content = AGENT_TEMPLATE.format(
        name=name,
        title=title,
        storyboards=_STORYBOARDS_KEY if with_storyboard else "",
        storyboard_load=_STORYBOARD_LOAD if with_storyboard else "",
    )

    if with_storyboard:
        # Folder layout per COR-015 + sibling storyboard per COR-016.
        folder_dir = ns_dir / name
        agent_target = folder_dir / f"{name}.md"
        storyboard_target = folder_dir / STORYBOARD_FILE
        if not dry_run:
            folder_dir.mkdir(parents=True, exist_ok=True)
            agent_target.write_text(content, encoding="utf-8")
            # Stamp the storyboard scaffold via the storyboards module so
            # the template stays in one place.
            from project_kit.storyboards import STORYBOARD_TEMPLATE

            storyboard_target.write_text(
                STORYBOARD_TEMPLATE.format(
                    title=title, kind="agent", name=name, namespace=namespace
                ),
                encoding="utf-8",
            )
        return agent_target

    # Default: flat layout.
    target = ns_dir / f"{name}.md"
    if not dry_run:
        ns_dir.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return target


def agents_dir_for(target_root: Path, namespace: Namespace) -> Path:
    """The folder `namespace`'s agents live in, refusing an unknown namespace.

    `core` and `project` resolve to `.pkit/agents/<namespace>/`, which must
    exist (`pkit init` creates both). Any other namespace names a capability,
    which must exist — the shared capability-namespace refusal otherwise; its
    `agents/` folder is returned whether or not it exists yet, so the first
    stamp creates it.
    """
    if namespace in AREA_NAMESPACES:
        ns_dir = target_root / _AGENTS_DIR / namespace
        if not ns_dir.is_dir():
            raise click.ClickException(
                f"{ns_dir.relative_to(target_root)} does not exist. "
                f"Run 'pkit init' from this project's root first."
            )
        return ns_dir
    return resolve_capability_dir(target_root, namespace, AREA_NAMESPACES) / "agents"


def agent_locations(target_root: Path) -> list[tuple[Namespace, Path]]:
    """Every folder agents ship from, as (namespace, folder), in deploy order.

    `project`, each capability by name, then `core` — the name-collision
    precedence the Claude Code deploy (`deploy-agents.sh`) resolves a name by
    (the agents README, "Name-collision precedence"), so the first location
    holding an agent is the one that deploys. Folders need not exist.
    """
    return [
        ("project", target_root / _AGENTS_DIR / "project"),
        *(
            (cap, target_root / CAPABILITIES_DIR / cap / "agents")
            for cap in capability_names(target_root)
        ),
        ("core", target_root / _AGENTS_DIR / "core"),
    ]


def find_agent_file(agents_dir: Path, name: str) -> Path | None:
    """The agent's canonical file in `agents_dir`: `<name>.md` or `<name>/<name>.md` (COR-015)."""
    for candidate in (agents_dir / f"{name}.md", agents_dir / name / f"{name}.md"):
        if candidate.is_file():
            return candidate
    return None


def _validate_name(name: str) -> None:
    if not _NAME_RE.match(name):
        raise click.ClickException(
            "agent name must be kebab-case (lowercase letters, digits, "
            "single hyphens; starts with a letter, doesn't end with a hyphen)."
        )


def _name_to_title(name: str) -> str:
    """Convert kebab-case name to Title Case for the H1 seed."""
    return " ".join(word.capitalize() for word in name.split("-"))
