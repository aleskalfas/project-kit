"""Agent stamping (per COR-013 + COR-015).

The deterministic part of `pkit new agent`: file stamping with the
unified frontmatter shape and canonical body sections. The conversational
layer (slug judgement, role-vs-procedure framing, reads/owns/needs
discipline) is the `agent-author` skill's job per COR-005's "Skill /
command pairing".

Layout per COR-015: a new agent stamps flat as `<name>.md`. If helpers
materialise later, the author migrates to folder form (`<name>/<name>.md`
+ siblings) as a separate gesture.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import click

Namespace = Literal["core", "project"]

_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


# Per COR-013's frontmatter schema + agents/README's body conventions.
# Lists are empty placeholders the author fills in; description is a
# single-line placeholder the author rewrites. Tools default to a
# read-oriented set; the author narrows or widens per the agent's role.
AGENT_TEMPLATE = """\
---
name: {name}
description: One-line summary of what this agent does and when to invoke it.
tools: [Read, Glob, Grep, Bash]
reads:
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

<List the paths this agent has write authority over. Use `<category-name>` placeholders from `.pkit/agents/project/overlay.yaml` for adopter-specific paths; declare them in frontmatter `reads.patterns` and `owns` as well.>

## Key documents to read

<List the paths, records (COR-NNN / PRJ-NNN), and hook contracts this agent consults at task time. Each must also appear in frontmatter `reads`.>

## How you work

<Procedural body: numbered steps if the agent follows a fixed sequence; principles if the role is more judgement-bearing. Cite records by ID where authority is invoked.>
"""


def stamp_new_agent(
    target_root: Path,
    name: str,
    namespace: Namespace,
    *,
    with_storyboard: bool = False,
    dry_run: bool = False,
) -> Path:
    """Stamp a new agent file at `.pkit/agents/<namespace>/<name>.md`.

    Default: flat layout (`<name>.md`). When `with_storyboard=True`,
    stamps folder layout per COR-015 (`<name>/<name>.md`) plus a sibling
    `storyboard.md` scaffold per COR-016 — for agents that drive
    scripted interaction scenarios.

    Refuses if the name is already taken in either namespace (project >
    core resolution means a colliding name would mask the existing core
    agent — surface the collision instead of silently shadowing).

    Returns the agent file path (not the storyboard). When stamping
    folder-form, that's `<ns>/<name>/<name>.md`.
    """
    _validate_name(name)
    agents_dir = target_root / ".pkit" / "agents"
    ns_dir = agents_dir / namespace
    if not ns_dir.is_dir():
        raise click.ClickException(
            f"{ns_dir.relative_to(target_root)} does not exist. "
            f"Run 'pkit init' from this project's root first."
        )

    # Refuse if the name is already taken in EITHER namespace, in either
    # the flat or folder layout (per COR-015 either is valid).
    for ns in ("core", "project"):
        for candidate in (
            agents_dir / ns / f"{name}.md",
            agents_dir / ns / name / f"{name}.md",
        ):
            if candidate.exists():
                raise click.ClickException(
                    f"agent {name!r} already exists at "
                    f"{candidate.relative_to(target_root)}."
                )

    title = _name_to_title(name)
    content = AGENT_TEMPLATE.format(name=name, title=title)

    if with_storyboard:
        # Folder layout per COR-015 + sibling storyboard per COR-016.
        folder_dir = ns_dir / name
        agent_target = folder_dir / f"{name}.md"
        storyboard_target = folder_dir / "storyboard.md"
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
        target.write_text(content, encoding="utf-8")
    return target


def _validate_name(name: str) -> None:
    if not _NAME_RE.match(name):
        raise click.ClickException(
            "agent name must be kebab-case (lowercase letters, digits, "
            "single hyphens; starts with a letter, doesn't end with a hyphen)."
        )


def _name_to_title(name: str) -> str:
    """Convert kebab-case name to Title Case for the H1 seed."""
    return " ".join(word.capitalize() for word in name.split("-"))
