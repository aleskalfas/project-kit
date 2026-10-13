"""The deployed agents' check (#1559): each tracked copy is what the deploy writes.

project-kit tracks `.claude/agents/<name>.md`, and the Claude Code adapter's
`deploy-agents.sh` writes each one from its agent's source. A change that alters
a source and does not run the deploy leaves the tracked copy stale, and the
reviewers a landing dispatches run the old body. This check fails that change.

It runs the deploy over git's index of `.pkit/` and `.claude/agents/`, checked
out into a temporary directory, so it writes nothing in the checkout. It reads
the index, not the working tree: CI's `pkit sync` redeploys the working tree's
copies before the aggregator runs, and only what git tracks still shows the
drift there.

A finding names the agent and one of four things:

- the tracked copy is not what the deploy writes from the source;
- the deploy writes a copy that git does not track;
- the deploy removes a tracked copy, as its agent no longer ships;
- the deploy skips the agent, for the reason it prints.

From the repository root:

    uv run python scripts/check_deployed_agents.py

Exit 0 when nothing is found, 1 on a finding, and 2 when the check cannot run.
"""

from __future__ import annotations

import argparse
import difflib
import re
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]

#: Where the deploy writes each agent's copy, relative to the repository root.
AGENTS = ".claude/agents"

#: The deploy, relative to the repository root. It is the command that fixes a finding.
DEPLOY = ".pkit/adapters/claude-code/deploy-agents.sh"

#: The tracked trees the deploy reads and writes.
TRACKED = (".pkit", AGENTS)

#: A status line in which the deploy says it skipped an agent.
SKIPPED = re.compile(r"^\s*skipped\s+(?P<what>\S.*)$")

#: The most lines of a copy's diff a finding shows.
DIFF_LINES = 40


class CheckError(Exception):
    """The check cannot run: git or the deploy failed."""


@dataclass(frozen=True)
class Finding:
    """One agent whose tracked copy is not what the deploy writes."""

    agent: str
    problem: str
    diff: tuple[str, ...] = ()


def _run(args: Sequence[str], cwd: Path, stdin: bytes | None = None) -> bytes:
    proc = subprocess.run(list(args), cwd=cwd, input=stdin, capture_output=True, check=False)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).decode(errors="replace").strip()
        raise CheckError(f"`{' '.join(args)}` exited {proc.returncode}: {detail}")
    return proc.stdout


def stage(root: Path, into: Path) -> None:
    """Check out git's index of the tracked trees under *into*, as the deploy reads them."""
    paths = _run(["git", "ls-files", "-z", "--", *TRACKED], root)
    if not paths:
        raise CheckError(f"git tracks nothing under {' or '.join(TRACKED)}")
    _run(["git", "checkout-index", "-z", "--stdin", f"--prefix={into}/"], root, paths)


def copies(root: Path) -> dict[str, bytes]:
    """Each agent's copy under *root*, by agent name."""
    folder = root / AGENTS
    if not folder.is_dir():
        return {}
    return {path.stem: path.read_bytes() for path in sorted(folder.glob("*.md"))}


def deploy(root: Path) -> str:
    """Run the deploy in *root* and give its status lines."""
    script = root / DEPLOY
    if not script.is_file():
        raise CheckError(f"git tracks no {DEPLOY}")
    return _run(["bash", str(script)], root).decode(errors="replace")


def _diff(agent: str, tracked: bytes, deployed: bytes) -> tuple[str, ...]:
    path = f"{AGENTS}/{agent}.md"
    lines = list(
        difflib.unified_diff(
            tracked.decode(errors="replace").splitlines(),
            deployed.decode(errors="replace").splitlines(),
            fromfile=f"{path} (tracked)",
            tofile=f"{path} (deployed)",
            n=1,
            lineterm="",
        )
    )
    if len(lines) > DIFF_LINES:
        lines = [*lines[:DIFF_LINES], f"... {len(lines) - DIFF_LINES} more lines"]
    return tuple(lines)


def _skipped_agent(what: str) -> str:
    """The agent a `skipped` status line names: its first word, or the copy it names."""
    return PurePosixPath(what.split(" ", 1)[0]).stem


def compare(tracked: dict[str, bytes], deployed: dict[str, bytes], output: str) -> list[Finding]:
    """The findings, from the tracked copies, the deploy's copies and its status lines."""
    findings: list[Finding] = []
    for agent in sorted(tracked.keys() | deployed.keys()):
        path = f"{AGENTS}/{agent}.md"
        if agent not in deployed:
            problem = f"the deploy removes {path}, as its agent no longer ships"
            findings.append(Finding(agent, problem))
        elif agent not in tracked:
            findings.append(Finding(agent, f"the deploy writes {path}, which git does not track"))
        elif tracked[agent] != deployed[agent]:
            problem = f"{path} is not what the deploy writes from its source"
            findings.append(Finding(agent, problem, _diff(agent, tracked[agent], deployed[agent])))
    for line in output.splitlines():
        if match := SKIPPED.match(line):
            what = match["what"]
            findings.append(Finding(_skipped_agent(what), f"the deploy skips it: {what}"))
    return findings


def check(root: Path) -> tuple[int, list[Finding]]:
    """The number of tracked copies and the findings, for the repository at *root*."""
    with tempfile.TemporaryDirectory(prefix="pkit-deployed-agents-") as tmp:
        staged = Path(tmp)
        stage(root, staged)
        tracked = copies(staged)
        output = deploy(staged)
        return len(tracked), compare(tracked, copies(staged), output)


def render(count: int, findings: Sequence[Finding]) -> str:
    if not findings:
        return f"deployed agents: each of the {count} tracked copies is what the deploy writes\n"
    lines = [f"deployed agents: {len(findings)} finding(s) in the tracked copies"]
    for finding in findings:
        lines.append(f"- {finding.agent}: {finding.problem}")
        lines.extend(f"    {line}" for line in finding.diff)
    lines.append(f"To fix: run {DEPLOY}, then commit what it changes in {AGENTS}/.")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(
        prog="check_deployed_agents.py",
        description="Each tracked deployed agent copy is what the deploy writes from its source.",
    )
    parser.parse_args(argv)
    try:
        count, findings = check(root)
    except (CheckError, OSError) as exc:
        print(f"deployed agents: {exc}", file=sys.stderr)
        return 2
    print(render(count, findings), end="")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
