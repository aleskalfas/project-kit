"""The lean coach's definition ([lean-business:DEC-004-lean-business-coach]).

**Its tool access (point 5).** The coach is granted its tools, so a tool its grant does
not name is not given, one a later harness release adds among them (COR-013 point 7). Its
definition is read through the agents area's reader, `.pkit/agents/tool_access.py`, as the
deploy and the runner read it, and held to the grant DEC-004 decides:

- its tool access is a grant, never a withheld list, which would give every tool it
  leaves out;
- the grant is the tool that reads a file, the shell, the tool that loads a skill and the
  tools that search files, each whole, with no argument;
- it lacks every tool that edits a file, the web tools, any connected server's tools and
  the tool that starts another agent;
- it lacks every other tool Claude Code's adapter knows, so a tool that fits none of
  those kinds is not given either.

**The skill's sections it cites (point 1).** The definition cites the skill and never
restates it, naming the sections it follows by their titles, in double quotes. Each
quoted title is held to a heading of the skill, so a section the skill renames or
removes fails here rather than leaving the coach pointed at nothing.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
READER = REPO / ".pkit" / "agents" / "tool_access.py"
CLAUDE_CODE = REPO / ".pkit" / "adapters" / "claude-code"
CAPABILITY = REPO / ".pkit" / "capabilities" / "lean-business"
COACH = CAPABILITY / "agents" / "lean-coach.md"
SKILL = CAPABILITY / "skills" / "lean-business" / "lean-business.md"

#: The grant DEC-004 point 5 decides, by Claude Code's names.
GRANTED = frozenset({"Read", "Bash", "Skill", "Glob", "Grep"})

#: The tools the grant withholds, in DEC-004 point 5's words, by Claude Code's names.
WITHHELD = {
    "every tool that edits a file": ("Edit", "MultiEdit", "Write", "NotebookEdit"),
    "the web tools": ("WebFetch", "WebSearch"),
    "the tool that starts another agent": ("Agent", "Task"),
}

#: A title the definition quotes, in straight or curly double quotes.
QUOTED = re.compile(r"[\"“]([^\"“”]+)[\"”]")

#: A Markdown heading, its title captured.
HEADING = re.compile(r"#{1,6}\s+(.+?)\s*")

FENCE = "```"


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _body(path: Path) -> str:
    """The text of `path` below its front matter."""
    text = path.read_text(encoding="utf-8")
    if text.startswith("---\n"):
        _, _, text = text[len("---\n") :].partition("\n---\n")
    return text


def _headings(path: Path) -> set[str]:
    """The titles of the headings of `path`, outside fenced code."""
    titles: set[str] = set()
    fenced = False
    for line in _body(path).splitlines():
        if line.startswith(FENCE):
            fenced = not fenced
        elif not fenced and (heading := HEADING.fullmatch(line)):
            titles.add(heading.group(1))
    return titles


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


def test_each_section_the_definition_cites_is_a_heading_of_the_skill() -> None:
    cited = set(QUOTED.findall(_body(COACH)))
    assert cited, "the definition quotes no section of the skill"
    assert sorted(cited - _headings(SKILL)) == []
