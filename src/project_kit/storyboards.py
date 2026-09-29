"""Storyboard stamping for scripted interaction scenarios (per COR-016).

The deterministic half of `pkit new storyboard <artifact-kind> <name>`:
file stamping with the canonical three-layer template (Framing / Tone /
Scenarios). The conversational layer (Trigger/Preconditions/Walkthrough/
Behind-the-scenes drafting, discipline checks) is the `storyboard-author`
skill's job per COR-005's "Skill / command pairing".

Today's only supported artifact-kind is `agent`. Future application
classes (`cli`, `migration`, `tutorial`, ...) slot in here as additional
handlers without renaming the command — per COR-016, the command name
is class-agnostic by design.

Stamping a storyboard alongside an agent makes the agent composite per
COR-015. If the named agent is currently flat (`<ns>/<name>.md`), the
module converts it to folder form (`<ns>/<name>/<name>.md`) before
writing the storyboard sibling.

The agent is found wherever agents ship from — `.pkit/agents/{core,project}/`
or a capability's `agents/` folder — in the deploy's resolution order; a
namespace (`core`, `project` or a capability name) pins the lookup to one
location.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import click

from project_kit.agents import (
    Namespace,
    agent_locations,
    agents_dir_for,
    find_agent_file,
)

ArtifactKind = Literal["agent"]

_SLUG_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


STORYBOARD_TEMPLATE = """\
---
consumers:
  - kind: {kind}
    name: {name}
    namespace: {namespace}
---

# Storyboard: {title}

<!-- This storyboard describes scripted interaction scenarios per COR-016.
     The consumer ({kind}: {namespace}/{name}) drives its scenarios at
     runtime. Edit this file as the design source; the consumer's body
     declares this storyboard in its `storyboards:` frontmatter and
     loads it via the Read tool at session start. -->

## Framing

<What set of scenarios does this storyboard cover? What global state do
the scenarios operate on? What are the user-facing entry points?>

## Tone

- One thought per turn. The actor never dumps a whole section at once
  if it can be staged.
- Turns are 1–3 sentences. Italics inside an actor turn indicate a
  behind-the-scenes action narrated to the user (e.g. *reads git config*).
- Confirmation prompts are short and direct.
- When the actor acts on a user request, it confirms what it did in
  one sentence and offers the next step.

---

## Scenario 1: <name>

**Trigger.** <What activates this scenario.>

**Preconditions.** <State that must hold for the scenario to apply.>

### Walkthrough

> **Actor:** <opening turn>
>
> **User:** <user response>
>
> **Actor:** <next turn>

### Behind the scenes

- <File mutation, state check, or side effect 1>
- <Mutation 2>
- <Edge cases handled here, not elided>

---

<!-- Add more scenarios below. Edge cases (the actor refusing to act,
     the user trying to bypass a gate, returning users) are first-class
     scenarios, not afterthoughts. -->
"""


def stamp_new_storyboard(
    target_root: Path,
    kind: ArtifactKind,
    name: str,
    *,
    namespace: Namespace | None = None,
    scenario: str | None = None,
    dry_run: bool = False,
) -> Path:
    """Stamp a storyboard sibling to the named implementing artifact.

    `kind` selects the handler; today only `agent` is supported. `name`
    is the implementing artifact's name (kebab-case). `namespace`, if
    given, is where the agent lives — `core`, `project` or a capability
    name; otherwise the agent is looked up in the deploy's resolution
    order. `scenario`, if given, produces `<scenario>.storyboard.md` for
    the multi-scenario case; otherwise the file is `storyboard.md`.

    Returns the absolute path written. In dry-run mode, returns the
    path that would be written without writing it.
    """
    _validate_name(name)
    if scenario is not None:
        _validate_name(scenario)

    if kind == "agent":
        return _stamp_agent_storyboard(target_root, name, namespace, scenario, dry_run)
    raise click.ClickException(
        f"unknown artifact-kind {kind!r}. Supported kinds today: agent. "
        f"Other classes (cli, migration, tutorial) are recognized by COR-016 "
        f"but not yet handled here."
    )


def _stamp_agent_storyboard(
    target_root: Path,
    agent_name: str,
    namespace: Namespace | None,
    scenario: str | None,
    dry_run: bool,
) -> Path:
    """Find the agent (in either layout) and stamp a sibling.

    If the agent is in flat form, convert to folder form first per COR-015
    (an agent gaining its first helper migrates to folder layout).
    """
    agents_area = target_root / ".pkit" / "agents"
    if not agents_area.is_dir():
        raise click.ClickException(
            f"{agents_area.relative_to(target_root)} does not exist. "
            f"Run 'pkit init' from this project's root first."
        )

    ns, ns_dir, agent_file = _locate_agent(target_root, agent_name, namespace)

    # Convert flat → folder form if needed (COR-015 — agent gaining its
    # first sibling helper migrates from atomic to composite layout).
    if agent_file.parent == ns_dir:
        folder_dir = ns_dir / agent_name
        new_agent_file = folder_dir / f"{agent_name}.md"
        if not dry_run:
            folder_dir.mkdir(parents=True, exist_ok=True)
            agent_file.rename(new_agent_file)
        agent_file = new_agent_file

    agent_dir = agent_file.parent
    storyboard_name = (
        f"{scenario}.storyboard.md" if scenario is not None else "storyboard.md"
    )
    target = agent_dir / storyboard_name
    if target.exists():
        raise click.ClickException(
            f"storyboard already exists at "
            f"{target.relative_to(target_root)}."
        )

    title = _name_to_title(scenario if scenario is not None else agent_name)
    content = STORYBOARD_TEMPLATE.format(
        title=title, kind="agent", name=agent_name, namespace=ns
    )
    if not dry_run:
        target.write_text(content, encoding="utf-8")
    return target


def _locate_agent(
    target_root: Path, agent_name: str, namespace: Namespace | None
) -> tuple[Namespace, Path, Path]:
    """The agent's (namespace, agents folder, canonical file), or refuse.

    With `namespace`, only that namespace's folder is searched (an unknown
    namespace gets the shared refusal). Without it, every location agents ship
    from is searched in the deploy's order — project, core, then capabilities
    by name — so the agent found is the one that deploys.
    """
    if namespace is not None:
        ns_dir = agents_dir_for(target_root, namespace)
        agent_file = find_agent_file(ns_dir, agent_name)
        if agent_file is None:
            raise click.ClickException(
                f"no agent named {agent_name!r} in {ns_dir.relative_to(target_root)}/. "
                f"Stamp the agent first with `pkit new agent {namespace} {agent_name}`."
            )
        return namespace, ns_dir, agent_file

    for ns, ns_dir in agent_locations(target_root):
        agent_file = find_agent_file(ns_dir, agent_name)
        if agent_file is not None:
            return ns, ns_dir, agent_file
    raise click.ClickException(
        f"no agent named {agent_name!r} found in .pkit/agents/{{core,project}}/ "
        f"or any capability's agents/ folder. "
        f"Stamp the agent first with `pkit new agent <namespace> {agent_name}`."
    )


def _validate_name(name: str) -> None:
    if not _SLUG_RE.match(name):
        raise click.ClickException(
            "name must be kebab-case (lowercase letters, digits, single hyphens; "
            "starts with a letter, doesn't end with a hyphen)."
        )


def _name_to_title(name: str) -> str:
    return " ".join(word.capitalize() for word in name.split("-"))
