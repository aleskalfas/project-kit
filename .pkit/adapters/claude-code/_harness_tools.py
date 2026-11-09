"""Claude Code's terms for an agent's tool access (ADR-085, ADR-086 point 4).

The reader of an agent's tool access, `.pkit/agents/tool_access.py`, gives a
definition's form and its entries in the methodology's terms (COR-013 point 7).
This module holds what is Claude Code's own: the key each form is written
under, the built-in tools this adapter knows, and which withheld entries
Claude Code was measured to withhold. The deploy's resolver and the agent
runner both load it, so the two write and refuse alike.

**What it refuses** (`refusal`), as what Claude Code cannot enforce or
translate:

- a withheld name it does not know as one of Claude Code's built-in tools, since
  a misspelt name fails open;
- a withheld entry Claude Code was not measured to withhold: only a whole
  built-in tool, named without an argument, was measured to leave an agent's
  view (the adapter's support declaration, `session-agent-withheld-tools`);
- a tool's name in a form Claude Code does not take;
- Claude Code's own key for a withheld list, `disallowedTools`, held beside
  `withheld`.

Standard library only, and readable by Python 3.9: the runner loads it under
the system's Python. A caller loads it from its file, without writing bytecode
into the tree.
"""

from __future__ import annotations

import re
from collections.abc import Collection
from typing import Any

#: The methodology's form of tool access, by its key, to the key Claude Code
#: reads it under: a grant as `tools`, a withheld list as `disallowedTools`
#: (ADR-085 point 1).
HARNESS_KEYS = {"tools": "tools", "withheld": "disallowedTools"}

#: The methodology's key for a withheld list.
WITHHELD = "withheld"

#: The built-in tools of Claude Code this adapter knows: those Claude Code
#: 2.1.319 offered an agent in the runs measured for project-management
#: DEC-068, and those an earlier release or a session with nobody attending
#: offers under another name. A withheld name outside this set is refused. The
#: table of project-kit#2949 replaces this set.
KNOWN_TOOLS = frozenset(
    {
        "Agent",
        "Artifact",
        "AskUserQuestion",
        "Bash",
        "BashOutput",
        "CronCreate",
        "CronDelete",
        "CronList",
        "DesignSync",
        "Edit",
        "EnterPlanMode",
        "EnterWorktree",
        "ExitPlanMode",
        "ExitWorktree",
        "Glob",
        "Grep",
        "KillShell",
        "LSP",
        "ListAgents",
        "ListMcpResourcesTool",
        "Monitor",
        "MultiEdit",
        "NotebookEdit",
        "PowerShell",
        "PublishPlugin",
        "PushNotification",
        "Read",
        "ReadMcpResourceTool",
        "RemoteTrigger",
        "ReportFindings",
        "ScheduleWakeup",
        "SendMessage",
        "SendUserFile",
        "ShareOnboardingGuide",
        "Skill",
        "Task",
        "TaskCreate",
        "TaskGet",
        "TaskList",
        "TaskOutput",
        "TaskStop",
        "TaskUpdate",
        "TeamCreate",
        "TeamDelete",
        "TodoWrite",
        "ToolSearch",
        "WebFetch",
        "WebSearch",
        "Workflow",
        "Write",
    }
)

#: A tool's name in the form Claude Code takes: a built-in tool's, or an MCP
#: server's, `mcp__<server>`, or one of its tools, `mcp__<server>__<tool>`.
BUILT_IN_NAME = re.compile(r"[A-Z][A-Za-z0-9]*")
MCP_NAME = re.compile(r"mcp__[A-Za-z0-9_-]+")


def refusal(access: Any, keys: Collection[str]) -> str | None:
    """Why Claude Code cannot enforce or translate *access*, or None where it can.

    *access* is the reader's answer for a definition, and *keys* are the
    top-level keys of the definition's front matter.
    """
    if access.form == WITHHELD and HARNESS_KEYS[WITHHELD] in keys:
        return (
            f"it holds Claude Code's own key `{HARNESS_KEYS[WITHHELD]}` beside `{WITHHELD}`: "
            f"name the tools it is withheld in `{WITHHELD}` alone"
        )
    check = _withheld_problem if access.form == WITHHELD else _granted_problem
    for entry in access.entries:
        problem = check(entry)
        if problem is not None:
            return f"`{access.form}` names `{entry}`, {problem}"
    return None


def _withheld_problem(entry: Any) -> str | None:
    if entry.tool not in KNOWN_TOOLS:
        return (
            "which this adapter does not know as one of Claude Code's built-in tools, and a "
            "withheld name it does not know would withhold nothing: check its spelling, or "
            'grant the tools instead (the adapter\'s README, "Tool access", says where it '
            "keeps the names it knows)"
        )
    if entry.argument is not None:
        return (
            "and Claude Code was measured to withhold only a whole built-in tool, named "
            f"without an argument: withhold `{entry.tool}` whole, or grant the tools instead"
        )
    return None


def _granted_problem(entry: Any) -> str | None:
    if BUILT_IN_NAME.fullmatch(entry.tool):
        return None
    if MCP_NAME.fullmatch(entry.tool):
        if entry.argument is None:
            return None
        return "and Claude Code takes no argument after an MCP tool's name"
    return (
        "a name in a form Claude Code does not take: a built-in tool's name, such as "
        "`Read`, or an MCP server's or tool's, `mcp__<server>` or `mcp__<server>__<tool>`"
    )
