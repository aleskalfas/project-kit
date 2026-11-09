"""The reader of an agent's tool access, the Claude Code adapter's terms for it, and the
command's loader of the reader (COR-013 point 7, ADR-085, ADR-086).

- the reader reads the two keys from the front matter's text: a list on one line or one
  entry to a line, or one string split at commas outside parentheses; a key with no value
  holds no entries, and anything else is refused, as are both keys, a front-matter line it
  cannot read as a key and a key written twice;
- its two readings: a check that an agent holds a tool, and one that it lacks a tool,
  which only a grant answers;
- the adapter refuses a withheld name it does not know, a withheld entry Claude Code was
  not measured to withhold, a name in a form Claude Code does not take, and Claude Code's
  own key beside `withheld`;
- the command loads the reader from the tree, names which side is behind where it cannot,
  and writes no bytecode;
- the reader and the adapter's module run under the system's Python 3.9, standard library
  only.
"""

from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

from project_kit import agent_tool_access

REPO = Path(__file__).resolve().parents[1]
READER = REPO / ".pkit" / "agents" / "tool_access.py"
HARNESS_TOOLS = REPO / ".pkit" / "adapters" / "claude-code" / "_harness_tools.py"


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def reader() -> ModuleType:
    return _load(READER, "tool_access_under_test")


@pytest.fixture(scope="module")
def harness() -> ModuleType:
    return _load(HARNESS_TOOLS, "harness_tools_under_test")


def _definition(front_matter: str) -> str:
    return f"---\nname: a\ndescription: An agent.\n{front_matter}---\n\nThe body.\n"


def _read(reader: ModuleType, front_matter: str) -> tuple[str | None, list[str]]:
    access = reader.tool_access(_definition(front_matter))
    return access.form, [str(entry) for entry in access.entries]


# --- what the reader reads ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("front_matter", "form", "entries"),
    [
        ("tools: [Read, Glob, Grep]\n", "tools", ["Read", "Glob", "Grep"]),
        ("tools: [Read, Grep]  # a comment\n", "tools", ["Read", "Grep"]),
        ("tools: [Read, ]\n", "tools", ["Read"]),
        (
            "tools: ['Agent(a, b)', \"Bash(git log:*)\"]\n",
            "tools",
            ["Agent(a, b)", "Bash(git log:*)"],
        ),
        (
            "tools: [\"Bash(echo \\\"x\\\")\", 'Bash(echo ''y'')']\n",
            "tools",
            ['Bash(echo "x")', "Bash(echo 'y')"],
        ),
        (
            "tools: Read, Agent(worker, reviewer), Grep\n",
            "tools",
            ["Read", "Agent(worker, reviewer)", "Grep"],
        ),
        ("tools: 'Read, Grep'  # a comment\n", "tools", ["Read", "Grep"]),
        ("tools: Read\n", "tools", ["Read"]),
        ("tools: []\n", "tools", []),
        ("tools:\n", "tools", []),
        ("tools: ''\n", "tools", []),
        ("tools:  # none\n", "tools", []),
        (
            "withheld:\n  - Workflow  # starts work outside the session\n\n  # a comment\n"
            "  - SendMessage\n",
            "withheld",
            ["Workflow", "SendMessage"],
        ),
        ("withheld:\n- Workflow\n- 'Monitor'\n", "withheld", ["Workflow", "Monitor"]),
        ("withheld: []\n", "withheld", []),
        ("", None, []),
        ("# tools: [Read]\nmodel: sonnet\n", None, []),
    ],
)
def test_a_tool_access_reads_in_each_form(
    reader: ModuleType, front_matter: str, form: str | None, entries: list[str]
) -> None:
    assert _read(reader, front_matter) == (form, entries)


def test_an_entry_keeps_its_argument_apart_from_its_tools_name(reader: ModuleType) -> None:
    access = reader.tool_access(_definition("tools: [Read, Bash(git log:*)]\n"))
    assert [(entry.tool, entry.argument) for entry in access.entries] == [
        ("Read", None),
        ("Bash", "git log:*"),
    ]


@pytest.mark.parametrize(
    ("front_matter", "cause"),
    [
        ("tools: [Read]\nwithheld: [Workflow]\n", "names both `tools` and `withheld`"),
        ("tools:\nwithheld:\n", "names both `tools` and `withheld`"),
        ("tools: [Read]\ntools: [Grep]\n", "writes `tools` twice"),
        ("[flow]: x\n", "cannot read as a key"),
        ('"tools": [Read]\n', "cannot read as a key"),
        ("tools:[Read]\n", "cannot read as a key"),
        ("tools: [Read,\n  Grep]\n", "goes on over more than one line"),
        ("tools: Read,\n  Grep\n", "goes on over more than one line"),
        ("tools: [Read\n", "is not a closed list"),
        ("tools: [Read] Grep\n", "goes on after its list closes"),
        ("tools: [Read, [Grep]]\n", "nests a collection"),
        ("tools: {a: b}\n", "neither a list nor one string"),
        ("tools: |\n  Read\n", "neither a list nor one string"),
        ("tools: &anchor [Read]\n", "neither a list nor one string"),
        ("tools: null\n", "is written as null"),
        ("tools: ~\n", "is written as null"),
        ("tools:\n  a: b\n", "in a list, which is not an entry"),
        ("tools:\n  - Read\n    Grep\n", "in a list, which is not an entry"),
        ("tools:\n  -\n", "holds an empty entry"),
        ("tools: [Read,, Grep]\n", "holds an empty entry"),
        ("tools: [Bash()]\n", "whose parentheses hold no argument"),
        ("tools: [Bash(a]\n", "leaves a parenthesis open"),
        ("tools: [Bash)]\n", "closes a parenthesis it never opened"),
        ("tools: ['Read]\n", "has no closing quote"),
        ('tools: ["a\\tb"]\n', "holds the escape \\t"),
        ("tools: ['Read' x]\n", "goes on after an entry's closing quote"),
        ("tools: [read file]\n", "which is not a tool's name"),
        ("tools: [Bash(a)b]\n", "which is not a tool's name"),
    ],
)
def test_a_tool_access_the_reader_does_not_read_is_refused(
    reader: ModuleType, front_matter: str, cause: str
) -> None:
    with pytest.raises(reader.Refused) as refused:
        reader.tool_access(_definition(front_matter))
    assert cause in str(refused.value)


def test_a_definition_with_no_front_matter_is_refused(reader: ModuleType) -> None:
    with pytest.raises(reader.Refused, match="has no front matter"):
        reader.tool_access("Only a body.\n")


def test_a_front_matter_opening_with_an_indented_line_is_refused(reader: ModuleType) -> None:
    with pytest.raises(reader.Refused, match="opens with"):
        reader.tool_access("---\n  indented: x\n---\n")


def test_other_keys_hold_what_they_hold_unread(reader: ModuleType) -> None:
    """Only the two keys of tool access are read; another key's value is never parsed."""
    text = _definition("reads:\n  paths:\n    - a\nowns: [<x>]\ntools: [Read]\n")
    assert reader.tool_access(text).form == "tools"


# --- the two readings (ADR-085 point 2) -------------------------------------------------------


@pytest.mark.parametrize(
    ("front_matter", "tool", "holds", "lacks"),
    [
        ("tools: [Read, Edit]\n", "Read", True, False),
        ("tools: [Edit]\n", "Read", False, True),
        ("tools: [Read(src/**)]\n", "Read", True, False),
        ("tools: []\n", "Read", False, True),
        ("withheld: [Workflow]\n", "Read", True, False),
        ("withheld: [Read]\n", "Read", False, False),
        ("withheld: [Bash(rm:*)]\n", "Bash", False, False),
        ("", "Read", True, False),
    ],
)
def test_holding_and_lacking_a_tool(
    reader: ModuleType, front_matter: str, tool: str, holds: bool, lacks: bool
) -> None:
    """A tool counts as held or withheld whatever its argument, and only a grant shows that
    an agent lacks a tool, since a withheld list gives every tool it does not name."""
    access = reader.tool_access(_definition(front_matter))
    assert reader.holds(access, tool) is holds
    assert reader.lacks(access, tool) is lacks


# --- the adapter's terms (ADR-086 point 4) ------------------------------------------------------


def _refusal(reader: ModuleType, harness: ModuleType, front_matter: str) -> str | None:
    access = reader.tool_access(_definition(front_matter))
    return harness.refusal(access, ["name", "description", *_keys(front_matter)])


def _keys(front_matter: str) -> list[str]:
    return [line.split(":")[0] for line in front_matter.splitlines() if line[:1].isalpha()]


@pytest.mark.parametrize(
    "front_matter",
    [
        "",
        "tools: [Read, Agent(worker, reviewer), mcp__github, mcp__github__create_issue]\n",
        "tools: [Bash(git log:*)]\n",
        "withheld: [Workflow, RemoteTrigger, Monitor, PowerShell, SendMessage, ListAgents]\n",
        "withheld: []\n",
        "tools: [Read]\ndisallowedTools: [Workflow]\n",
    ],
)
def test_what_claude_code_can_enforce_and_translate_is_admitted(
    reader: ModuleType, harness: ModuleType, front_matter: str
) -> None:
    assert _refusal(reader, harness, front_matter) is None


@pytest.mark.parametrize(
    ("front_matter", "cause"),
    [
        ("withheld: [Wrokflow]\n", "`withheld` names `Wrokflow`, which this adapter does not know"),
        ("withheld: [read]\n", "`withheld` names `read`, which this adapter does not know"),
        ("withheld: [mcp__github]\n", "does not know as one of Claude Code's built-in tools"),
        ("withheld: ['Bash(rm:*)']\n", "measured to withhold only a whole built-in tool"),
        ("tools: [read-file]\n", "a name in a form Claude Code does not take"),
        ("tools: ['mcp__github(x)']\n", "takes no argument after an MCP tool's name"),
        (
            "withheld: [Workflow]\ndisallowedTools: [Monitor]\n",
            "holds Claude Code's own key `disallowedTools` beside `withheld`",
        ),
    ],
)
def test_what_claude_code_cannot_enforce_or_translate_is_refused(
    reader: ModuleType, harness: ModuleType, front_matter: str, cause: str
) -> None:
    refusal = _refusal(reader, harness, front_matter)
    assert refusal is not None
    assert cause in refusal


def test_each_form_is_written_under_claude_codes_key(
    reader: ModuleType, harness: ModuleType
) -> None:
    assert harness.HARNESS_KEYS == {reader.GRANT: "tools", reader.WITHHOLD: "disallowedTools"}
    assert set(harness.HARNESS_KEYS) == set(reader.KEYS)


def test_every_tool_withheld_by_a_shipped_definition_is_known(harness: ModuleType) -> None:
    """No definition the methodology ships is refused by the deploy for a withheld name."""
    reader = _load(READER, "tool_access_for_shipped")
    for path in sorted((REPO / ".pkit").rglob("agents/**/*.md")):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        try:
            access = reader.tool_access(text)
        except reader.Refused:
            continue
        assert harness.refusal(access, []) is None, path


# --- the command's loader (ADR-086 points 1 and 5) ----------------------------------------------


def _tree(root: Path, version: str | None = None) -> Path:
    (root / ".pkit" / "agents").mkdir(parents=True)
    if version is not None:
        (root / ".pkit" / "manifest.yaml").write_text(
            f"schema_version: 1\nbackbone_version: {version}\n", encoding="utf-8"
        )
    return root


def test_the_command_loads_the_trees_reader_and_writes_no_bytecode(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / ".pkit" / "agents" / "tool_access.py").write_text(
        READER.read_text(encoding="utf-8"), encoding="utf-8"
    )
    module = agent_tool_access.load_reader(root, ("tool_access", "holds"))
    assert module.tool_access(_definition("tools: [Read]\n")).form == "tools"
    assert not list(root.rglob("__pycache__"))


def test_a_tree_with_no_reader_needs_a_sync_where_the_project_is_not_newer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("project_kit.__version__", "2.2.0")
    root = _tree(tmp_path, "2.1.0")
    with pytest.raises(agent_tool_access.Unreachable) as unreachable:
        agent_tool_access.load_reader(root, ("tool_access",))
    message = str(unreachable.value)
    assert "holds no reader of an agent's tool access at .pkit/agents/tool_access.py" in message
    assert "(2.1.0) is not newer than this pkit's, 2.2.0: run `pkit sync`" in message


def test_a_reader_lacking_a_function_needs_pkit_upgraded_where_the_project_is_newer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("project_kit.__version__", "2.1.0")
    root = _tree(tmp_path, "2.3.0")
    (root / ".pkit" / "agents" / "tool_access.py").write_text(
        "def tool_access(text):\n    return None\n", encoding="utf-8"
    )
    with pytest.raises(agent_tool_access.Unreachable) as unreachable:
        agent_tool_access.load_reader(root, ("tool_access", "holds_v2"))
    message = str(unreachable.value)
    assert "has no holds_v2, which this command calls" in message
    assert "2.3.0, is newer than this pkit's, 2.1.0: upgrade pkit" in message


def test_a_reader_that_cannot_load_is_unreachable(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / ".pkit" / "agents" / "tool_access.py").write_text("raise ImportError('x')\n")
    with pytest.raises(agent_tool_access.Unreachable, match="cannot be loaded"):
        agent_tool_access.load_reader(root, ("tool_access",))


# --- where they run ------------------------------------------------------------------------------


@pytest.mark.parametrize("path", [READER, HARNESS_TOOLS], ids=lambda path: path.name)
def test_it_parses_as_python_3_9_and_imports_only_the_standard_library(path: Path) -> None:
    """The agent runner loads both under the system's Python, with nothing installed."""
    tree = ast.parse(path.read_text(encoding="utf-8"), feature_version=(3, 9))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert imported <= set(sys.stdlib_module_names) | {"__future__"}


def test_the_reader_loads_from_its_file_under_the_system_python(tmp_path: Path) -> None:
    """Loaded by path and not registered among the modules, as the runner loads it."""
    python = Path("/usr/bin/python3")
    if not python.exists():
        pytest.skip("no system Python")
    script = (
        "import importlib.util, sys\n"
        "spec = importlib.util.spec_from_file_location('r', sys.argv[1])\n"
        "module = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(module)\n"
        "access = module.tool_access('---\\nwithheld: [Workflow]\\n---\\n')\n"
        "print(access.form, [str(entry) for entry in access.entries])\n"
    )
    done = subprocess.run(
        [str(python), "-B", "-I", "-c", script, str(READER)],
        capture_output=True,
        text=True,
        check=True,
        cwd=tmp_path,
    )
    assert done.stdout.strip() == "withheld ['Workflow']"
