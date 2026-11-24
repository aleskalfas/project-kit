"""The lean coach's tool access ([lean-business:DEC-004-lean-business-coach] point 5).

The coach is granted its tools, so a tool its grant does not name is not given, one a
later harness release adds among them (COR-013 point 7). Its definition is read through
the agents area's reader, `.pkit/agents/tool_access.py`, as the deploy and the runner read
it, and held to the grant DEC-004 decides:

- its tool access is a grant, never a withheld list, which would give every tool it
  leaves out;
- the grant is the tool that reads a file, the shell, the tool that loads a skill and the
  tools that search files, each whole, with no argument;
- it lacks every tool that edits a file, every web tool, every tool of a connected
  server and every tool that starts another agent;
- it lacks every other tool Claude Code's adapter knows, so a tool that fits none of
  those kinds is not given either.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
READER = REPO / ".pkit" / "agents" / "tool_access.py"
CLAUDE_CODE = REPO / ".pkit" / "adapters" / "claude-code"
COACH = REPO / ".pkit" / "capabilities" / "lean-business" / "agents" / "lean-coach.md"

#: The grant DEC-004 point 5 decides, by Claude Code's names.
GRANTED = frozenset({"Read", "Bash", "Skill", "Glob", "Grep"})

#: The tools the grant withholds, by the kind DEC-004 point 5 names, in Claude Code's names.
WITHHELD = {
    "edits a file": ("Edit", "MultiEdit", "Write", "NotebookEdit"),
    "reaches the web": ("WebFetch", "WebSearch"),
    "starts another agent": ("Agent", "Task"),
}


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def reader() -> ModuleType:
    return _load(READER, "tool_access_of_the_lean_coach")


@pytest.fixture(scope="module")
def access(reader: ModuleType) -> Any:
    """The coach's tool access, as the reader reads it."""
    return reader.tool_access(COACH.read_text(encoding="utf-8"))


def test_the_coach_is_granted_its_tools(reader: ModuleType, access: Any) -> None:
    assert access.form == reader.GRANT


def test_the_grant_is_the_one_its_record_decides(access: Any) -> None:
    assert {entry.tool for entry in access.entries} == GRANTED
    assert all(entry.argument is None for entry in access.entries)


@pytest.mark.parametrize(
    "tool",
    [tool for tools in WITHHELD.values() for tool in tools],
)
def test_the_coach_lacks_each_tool_it_is_withheld(
    reader: ModuleType, access: Any, tool: str
) -> None:
    assert reader.lacks(access, tool)


def test_the_coach_lacks_every_tool_of_a_connected_server(access: Any) -> None:
    assert not [entry for entry in access.entries if entry.tool.startswith("mcp__")]


def test_the_coach_lacks_every_other_tool_the_adapter_knows(
    reader: ModuleType, access: Any
) -> None:
    declaration = reader.read_declaration(CLAUDE_CODE)
    assert declaration is not None
    held = sorted(
        tool for tool in declaration.known_tools - GRANTED if not reader.lacks(access, tool)
    )
    assert held == []


def test_each_withheld_tool_is_one_the_adapter_knows(reader: ModuleType) -> None:
    """A withheld name the adapter does not know would hold nothing in the test above."""
    declaration = reader.read_declaration(CLAUDE_CODE)
    assert declaration is not None
    unknown = sorted(
        tool for tools in WITHHELD.values() for tool in tools if tool not in declaration.known_tools
    )
    assert unknown == []
