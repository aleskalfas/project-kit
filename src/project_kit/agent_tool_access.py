"""The command's one loader of the tree's reader of an agent's tool access (ADR-086).

An agent's tool access is read by one module, `.pkit/agents/tool_access.py`,
propagated neutral code at the root of the agents area (ADR-086 point 1). The
adapters' deploy and runner load it in the project's tree, where this package
is not importable, so the command loads the same file from the tree it works on
rather than keeping a reader of its own (ADR-003).

A command loads the reader only where it has a definition to read. Where the
tree holds no reader, or not the function the command calls, `load_reader`
raises `Unreachable`, and the command refuses that step: the validator records
it as an error finding (ADR-086 point 5). The message names which side is
behind, read from the project's backbone version and the one this command
bundles: a project at an older or the same version needs a sync, and one at a
newer version needs this command upgraded.

The validator also refuses what each adapter that deploys agents refuses, by
that adapter's declaration of tool access, which the reader reads and applies
(ADR-086 point 6). `agent_adapters` names those adapters.
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType

#: Where the agents area puts the reader, relative to the project root.
READER = Path(".pkit") / "agents" / "tool_access.py"

#: The harness requirement an adapter's support declaration answers as achievable
#: before its declaration of tool access admits a withheld entry (ADR-085 point 3,
#: ADR-086 point 6).
SESSION_AGENT_WITHHELD = "session-agent-withheld-tools"


class Unreachable(Exception):
    """The tree holds no reader the command can call; the message names the fix."""


def load_reader(target_root: Path, functions: Sequence[str]) -> ModuleType:
    """The reader of the tree at *target_root*, holding each of *functions*.

    Loading writes nothing into the tree: no bytecode is left beside the module,
    since the commands that read it, validation among them, write nothing.
    Raises `Unreachable` where the tree holds no reader, where it cannot load,
    or where it lacks one of *functions*.
    """
    path = target_root / READER
    if not path.is_file():
        raise Unreachable(
            f"the project's tree holds no reader of an agent's tool access at {READER}, "
            f"so no definition's tool access can be read; {behind(target_root)}"
        )
    spec = importlib.util.spec_from_file_location("pkit_agents_tool_access", path)
    if spec is None or spec.loader is None:
        raise Unreachable(f"{READER} cannot be loaded; {behind(target_root)}")
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise Unreachable(f"{READER} cannot be loaded ({exc}); {behind(target_root)}") from None
    finally:
        sys.dont_write_bytecode = previous
    missing = [name for name in functions if not callable(getattr(module, name, None))]
    if missing:
        raise Unreachable(
            f"the reader of an agent's tool access at {READER} has no {', '.join(missing)}, "
            f"which this command calls; {behind(target_root)}"
        )
    return module


def agent_adapters(target_root: Path) -> list[str]:
    """Each adapter the backbone manifest registers that deploys agents, in its order
    (ADR-086 point 6).

    An adapter deploys agents where it ships a deploy of them, found by its name in
    the adapter's folder as the lifecycle finds it, or registers an agent runner, as
    the run command finds it. A registered name that is no plain name is never read
    as a path.
    """
    from project_kit import agent_runs, harness_support
    from project_kit.install import AGENT_DEPLOY_PRIMITIVE

    runners, _ = agent_runs.find_runners(target_root)
    with_runner = {runner.adapter for runner in runners}
    found: list[str] = []
    for name in harness_support.registered_adapters(target_root):
        deploys = (
            harness_support.is_adapter(target_root, name)
            and (target_root / ".pkit" / "adapters" / name / AGENT_DEPLOY_PRIMITIVE).is_file()
        )
        if (deploys or name in with_runner) and name not in found:
            found.append(name)
    return found


def behind(target_root: Path) -> str:
    """Which side is behind, the project's tree or this command, and its fix."""
    from project_kit import __version__
    from project_kit.manifest import read_backbone_manifest
    from project_kit.versioning import is_at_or_below, is_version

    manifest = read_backbone_manifest(target_root)
    project = manifest.backbone_version if manifest is not None else ""
    if is_version(project) and is_version(__version__) and not is_at_or_below(project, __version__):
        return (
            f"the project's backbone, {project}, is newer than this pkit's, {__version__}: "
            "upgrade pkit"
        )
    recorded = project or "not recorded"
    return (
        f"the project's backbone ({recorded}) is not newer than this pkit's, {__version__}: "
        "run `pkit sync`"
    )
