"""Deployed-agent resolution shared across pm scripts.

A reviewer-agent name (a DEC-028 `local_registered:` entry, or a DEC-032
contributed `reviewer`) is only satisfiable when the harness has actually
deployed the agent's file. Several scripts need that same check —
`pre-check.py` validates the static `local_registered:` set, the DEC-032
contribution collector resolves contributed reviewers, and the
gate-checker (#145) will resolve the required set. Rather than each
hardcode the deploy path (COR-007 — three copies invites drift), they
call this one helper.

The deploy location is fixed to Claude Code's `.claude/agents/<name>.md`
at v1 — the only adapter shipping agent deployment (consistent with
DEC-028 and DEC-032 D2). Centralising it here means a second harness, or
a relocation of the deploy directory, is a one-line change in one place
rather than a hunt across callers.

The fixers point (DEC-056 point 1) asks two more things of an agent: whether
the capability that names it ships it (`agent_is_shipped_by`), and what its
deployed definition grants it (`deployed_definition`) — the tools and the
claimed paths of the file the harness runs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:  # ruamel is declared by every pm script's PEP 723 header.
    from ruamel.yaml import YAML
    from ruamel.yaml.error import YAMLError
except ImportError:  # pragma: no cover — ruamel is in the kit's pyproject
    YAML = None  # type: ignore[assignment, misc]
    YAMLError = Exception  # type: ignore[assignment, misc]

# The relative path, under the repo root, where the Claude Code adapter
# deploys an agent named `<name>`. The single place to widen when a
# second harness ships agent deployment.
AGENTS_DEPLOY_SUBDIR = (".claude", "agents")


def agent_deploy_path(repo_root: Path, name: str) -> Path:
    """Path where agent `name` is expected to be deployed under `repo_root`."""
    return repo_root.joinpath(*AGENTS_DEPLOY_SUBDIR, f"{name}.md")


def agent_is_deployed(repo_root: Path, name: str) -> bool:
    """True when agent `name`'s deployed file exists under `repo_root`."""
    return agent_deploy_path(repo_root, name).is_file()


# Where core ships its agents under the repo root, which a sync refreshes and
# the adapter deploys from: `<name>.md`, or `<name>/<name>.md`.
CORE_AGENTS_SUBDIR = (".pkit", "agents", "core")


def agent_is_core(repo_root: Path, name: str) -> bool:
    """True when core ships agent `name`: its canonical file is under
    `.pkit/agents/core/`. An undeployed core agent is deployed by a sync, not
    by redeploying a capability."""
    core = repo_root.joinpath(*CORE_AGENTS_SUBDIR)
    return (core / f"{name}.md").is_file() or (core / name / f"{name}.md").is_file()


def agent_is_shipped_by(repo_root: Path, capability: str, name: str) -> bool:
    """True when the installed `capability` ships agent `name`: its canonical
    file is in the capability's `agents/` folder, as `<name>.md` or
    `<name>/<name>.md` — the two layouts the deploy primitive reads."""
    agents = repo_root / ".pkit" / "capabilities" / capability / "agents"
    return (agents / f"{name}.md").is_file() or (agents / name / f"{name}.md").is_file()


@dataclass(frozen=True)
class Definition:
    """What a deployed agent's front matter declares: the tools the harness
    grants it and the paths it claims (`owns`, resolved at deploy). `problem` is
    why the front matter could not be read; the other fields are then empty.

    `tools` is None when the definition lists no tool: the key absent, null or
    empty. The harness then grants the agent every tool, so a reader takes None
    as every tool, never as none."""

    tools: tuple[str, ...] | None = ()
    owns: tuple[str, ...] = ()
    problem: str = ""

    @property
    def tool_names(self) -> tuple[str, ...]:
        """Each listed tool's name, without the parameters a harness may write
        after it in parentheses, such as `Agent(worker)`."""
        return tuple(tool.split("(", 1)[0].strip() for tool in self.tools or ())


def deployed_definition(repo_root: Path, name: str) -> Definition | None:
    """The front matter of agent `name` as deployed — what the harness runs, an
    adopter's overlay applied — or None when it is not deployed."""
    path = agent_deploy_path(repo_root, name)
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return Definition(problem=f"{path.name} cannot be read ({exc})")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return Definition(problem=f"{path.name} opens with no front matter")
    try:
        end = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration:
        return Definition(problem=f"{path.name}'s front matter never closes")
    if YAML is None:  # pragma: no cover — ruamel is in the kit's pyproject
        return Definition(problem="ruamel.yaml is not installed")
    try:
        data = YAML(typ="safe").load("\n".join(lines[1:end]))
    except YAMLError as exc:
        return Definition(problem=f"{path.name}'s front matter does not parse ({exc})")
    if not isinstance(data, dict):
        return Definition(problem=f"{path.name}'s front matter is not a mapping")
    tools = _strings(data.get("tools"))
    return Definition(tools=tools or None, owns=_strings(data.get("owns")))


def _strings(value: Any) -> tuple[str, ...]:
    """A front-matter list as its strings: a tool list may be written as a list
    or as one comma-separated string, as the harness reads it. A comma inside
    parentheses, as in `Agent(a, b)`, separates nothing."""
    if isinstance(value, str):
        parts: list[str] = []
        depth, start = 0, 0
        for index, char in enumerate(value):
            depth += {"(": 1, ")": -1}.get(char, 0)
            if char == "," and depth <= 0:
                parts.append(value[start:index])
                start = index + 1
        parts.append(value[start:])
        return tuple(part.strip() for part in parts if part.strip())
    if isinstance(value, list):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return ()
