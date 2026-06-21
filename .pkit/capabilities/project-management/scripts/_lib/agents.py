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
"""

from __future__ import annotations

from pathlib import Path


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
