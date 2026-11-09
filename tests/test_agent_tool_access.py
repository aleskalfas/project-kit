"""The reader of an agent's tool access, an adapter's declaration of it, and the
command's loader of the reader (COR-013 point 7, ADR-085, ADR-086).

- the reader reads the two keys from the front matter's text: a list on one line or one
  entry to a line, or one string split at commas outside parentheses; a key with no value
  holds no entries, and anything else is refused, as are both keys, a front-matter line it
  cannot read as a key and a key written twice;
- its two readings: a check that an agent holds a tool, and one that it lacks a tool,
  which only a grant answers;
- it reads an adapter's declaration of tool access, and refuses one whose version, keys or
  values it does not read; the Claude Code adapter's agrees with its schema;
- by the Claude Code adapter's declaration it refuses a withheld name the adapter does not
  know, a withheld entry Claude Code was not measured to withhold, a name in a form Claude
  Code does not take, and Claude Code's own key beside `withheld`;
- the command loads the reader from the tree, names which side is behind where it cannot,
  and writes no bytecode, and it names each registered adapter that deploys agents;
- the reader runs under the system's Python 3.9, standard library only.
"""

from __future__ import annotations

import ast
import copy
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import jsonschema
import pytest

from project_kit import agent_tool_access

REPO = Path(__file__).resolve().parents[1]
READER = REPO / ".pkit" / "agents" / "tool_access.py"
CLAUDE_CODE = REPO / ".pkit" / "adapters" / "claude-code"
SCHEMA = REPO / ".pkit" / "schemas" / "tool-access.schema.json"
EMPTIEST = REPO / ".pkit" / "schemas" / "tool-access.yaml"


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
def harness(reader: ModuleType) -> Any:
    """The Claude Code adapter's declaration of tool access, as the reader reads it."""
    declaration = reader.read_declaration(CLAUDE_CODE)
    assert declaration is not None
    return declaration


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


# --- the Claude Code adapter's declaration (ADR-086 point 4) ------------------------------------


def _refusal(reader: ModuleType, harness: Any, front_matter: str) -> str | None:
    access = reader.tool_access(_definition(front_matter))
    return reader.harness_refusal(access, ["name", "description", *_keys(front_matter)], harness)


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
    reader: ModuleType, harness: Any, front_matter: str
) -> None:
    assert _refusal(reader, harness, front_matter) is None


@pytest.mark.parametrize(
    ("front_matter", "cause"),
    [
        ("withheld: [Wrokflow]\n", "`withheld` names `Wrokflow`, which this adapter does not know"),
        ("withheld: [read]\n", "`withheld` names `read`, which this adapter does not know"),
        ("withheld: [mcp__github]\n", "does not know as one of Claude Code's built-in tools"),
        (
            "withheld: ['Bash(rm:*)']\n",
            "measured to withhold only a whole built-in tool, named without an argument: "
            "withhold `Bash` whole",
        ),
        ("tools: [read-file]\n", "a name in a form Claude Code does not take"),
        ("tools: ['mcp__github(x)']\n", "takes no argument after an MCP server's or tool's name"),
        (
            "withheld: [Workflow]\ndisallowedTools: [Monitor]\n",
            "holds Claude Code's own key `disallowedTools` beside `withheld`",
        ),
    ],
)
def test_what_claude_code_cannot_enforce_or_translate_is_refused(
    reader: ModuleType, harness: Any, front_matter: str, cause: str
) -> None:
    refusal = _refusal(reader, harness, front_matter)
    assert refusal is not None
    assert cause in refusal


def test_each_form_is_written_under_claude_codes_key(reader: ModuleType, harness: Any) -> None:
    assert harness.keys == {reader.GRANT: "tools", reader.WITHHOLD: "disallowedTools"}
    assert set(harness.keys) == set(reader.KEYS)


def test_every_tool_withheld_by_a_shipped_definition_is_known(harness: Any) -> None:
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
        assert reader.harness_refusal(access, [], harness) is None, path


# --- reading a declaration (ADR-086 point 4) ---------------------------------------------------


def _claude_codes() -> dict[str, Any]:
    return json.loads((CLAUDE_CODE / "tool-access.json").read_text(encoding="utf-8"))


def _declared(root: Path, document: object) -> Path:
    """An adapter folder under *root* whose declaration is *document*, written as JSON."""
    folder = root / "adapter"
    folder.mkdir(exist_ok=True)
    (folder / "tool-access.json").write_text(json.dumps(document), encoding="utf-8")
    return folder


def _with(change: dict[str, Any]) -> dict[str, Any]:
    document = copy.deepcopy(_claude_codes())
    document.update(change)
    return document


def test_an_adapter_with_no_declaration_declares_none(reader: ModuleType, tmp_path: Path) -> None:
    assert reader.read_declaration(tmp_path) is None
    assert reader.declaration_path(tmp_path) == tmp_path / "tool-access.json"


@pytest.mark.parametrize(
    ("document", "cause"),
    [
        (_with({"schema_version": 2}), "its schema version is 2, and this reader reads version 1"),
        (_with({"schema_version": True}), "its schema version is true"),
        (_with({"aliases": {}, "groups": []}), "keys this reader does not know: aliases, groups"),
        ({"schema_version": 1, "harness": "H"}, "it lacks keys, name_forms, known_tools"),
        (_with({"harness": " "}), "its `harness` is not a harness's name"),
        (_with({"keys": {"tools": "tools"}}), "its `keys` gives no key for withheld"),
        (_with({"keys": {"tools": "a", "withheld": "a", "x": "b"}}), "names forms the reader"),
        (_with({"keys": {"tools": "a b", "withheld": "c"}}), "which is not a key a front matter"),
        (_with({"keys": {"tools": "a", "withheld": "a"}}), "gives one key for both forms"),
        (_with({"known_tools": ["Read", "Read"]}), "names Read twice"),
        (_with({"known_tools": ["Read file"]}), "which is not a tool's name the reader reads"),
        (_with({"name_forms": {}}), "its `name_forms` is not a list"),
        (_with({"name_forms": ["[A-Z]+"]}), "which is not an object"),
        (
            _with({"name_forms": [{"pattern": "(", "argument": True, "description": "d"}]}),
            "which is not a regular expression",
        ),
        (
            _with({"name_forms": [{"pattern": "a", "argument": "yes", "description": "d"}]}),
            "an `argument` that is not true or false",
        ),
        (_with({"withheld_admits": [{"pattern": "a"}]}), "a shape that lacks argument, descr"),
        (
            _with({"withheld_admits": [{"pattern": "a", "argument": False, "description": ""}]}),
            "a shape with no description",
        ),
        ([], "it is not a JSON object"),
    ],
)
def test_a_declaration_the_reader_does_not_read_is_refused(
    reader: ModuleType, tmp_path: Path, document: object, cause: str
) -> None:
    with pytest.raises(reader.BadDeclaration) as refused:
        reader.read_declaration(_declared(tmp_path, document))
    assert cause in str(refused.value)


@pytest.mark.parametrize(
    ("text", "cause"),
    [
        ('{"schema_version": 1, "schema_version": 1}', "writes the key 'schema_version' twice"),
        ("{not json", "it is not JSON"),
    ],
)
def test_a_declaration_that_is_not_one_json_object_is_refused(
    reader: ModuleType, tmp_path: Path, text: str, cause: str
) -> None:
    (tmp_path / "tool-access.json").write_text(text, encoding="utf-8")
    with pytest.raises(reader.BadDeclaration, match=cause):
        reader.read_declaration(tmp_path)


def test_a_declaration_admitting_no_withheld_entry_refuses_every_withheld_tool(
    reader: ModuleType, tmp_path: Path
) -> None:
    declaration = reader.read_declaration(_declared(tmp_path, _with({"withheld_admits": []})))
    access = reader.tool_access(_definition("withheld: [Workflow]\n"))
    refusal = reader.harness_refusal(access, [], declaration)
    assert refusal is not None
    assert "was not measured to withhold any tool, so its adapter admits no withheld entry" in (
        refusal
    )
    empty = reader.tool_access(_definition("withheld: []\n"))
    assert reader.harness_refusal(empty, [], declaration) is None


def test_a_declaration_with_no_name_forms_refuses_every_granted_tool(
    reader: ModuleType, tmp_path: Path
) -> None:
    declaration = reader.read_declaration(_declared(tmp_path, _with({"name_forms": []})))
    access = reader.tool_access(_definition("tools: [Read]\n"))
    refusal = reader.harness_refusal(access, [], declaration)
    assert refusal is not None
    assert "its adapter declares no form a name takes" in refusal


def test_a_declarations_patterns_never_widen_the_readers_grammar(
    reader: ModuleType, tmp_path: Path
) -> None:
    """A name outside the reader's grammar is refused before any declaration is read."""
    reader.read_declaration(
        _declared(
            tmp_path,
            _with({"name_forms": [{"pattern": ".*", "argument": True, "description": "any"}]}),
        )
    )
    with pytest.raises(reader.Refused, match="which is not a tool's name"):
        reader.tool_access(_definition("tools: [read file]\n"))


@pytest.mark.parametrize(
    "path",
    [CLAUDE_CODE / "tool-access.json", EMPTIEST],
    ids=["claude-code", "the emptiest"],
)
def test_a_declaration_the_methodology_ships_agrees_with_its_schema_and_its_reader(
    reader: ModuleType, tmp_path: Path, path: Path
) -> None:
    from ruamel.yaml import YAML

    text = path.read_text(encoding="utf-8")
    document = json.loads(text) if path.suffix == ".json" else YAML(typ="safe").load(text)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    assert list(jsonschema.Draft202012Validator(schema).iter_errors(document)) == []
    assert reader.read_declaration(_declared(tmp_path, document)) is not None


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": 2},
        {"aliases": {}},
        {"keys": {"tools": "tools"}},
        {"known_tools": ["Read", "Read"]},
        {"name_forms": [{"pattern": "a", "argument": True}]},
        {"withheld_admits": [{"pattern": "a", "argument": False, "description": ""}]},
    ],
)
def test_the_schema_refuses_what_the_reader_refuses(
    reader: ModuleType, tmp_path: Path, change: dict[str, Any]
) -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert list(jsonschema.Draft202012Validator(schema).iter_errors(_with(change)))
    with pytest.raises(reader.BadDeclaration):
        reader.read_declaration(_declared(tmp_path, _with(change)))


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


def _adapter(root: Path, name: str, *, deploy: bool = False, runner: bool = False) -> None:
    folder = root / ".pkit" / "adapters" / name
    folder.mkdir(parents=True)
    if deploy:
        (folder / "deploy-agents.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    commands = "commands:\n  run-agent:\n    script: run-agent.py\n    help: Run.\n"
    (folder / "package.yaml").write_text(
        f"schema_version: 1\ncomponent:\n  kind: adapter\n  name: {name}\n  version: 0.1.0\n"
        + (commands if runner else ""),
        encoding="utf-8",
    )
    if runner:
        (folder / "run-agent.py").write_text("", encoding="utf-8")


def test_the_adapters_that_deploy_agents_are_the_registered_ones_with_a_deploy_or_a_runner(
    tmp_path: Path,
) -> None:
    root = _tree(tmp_path)
    _adapter(root, "deploys", deploy=True)
    _adapter(root, "runs", runner=True)
    _adapter(root, "neither")
    _adapter(root, "unregistered", deploy=True)
    names = ["runs", "neither", "deploys", "../outside"]
    (root / ".pkit" / "manifest.yaml").write_text(
        "schema_version: 1\nbackbone_version: 2.1.0\ncomponents:\n"
        + "".join(f"  - kind: adapter\n    name: {name}\n    manifest: m.yaml\n" for name in names),
        encoding="utf-8",
    )
    assert agent_tool_access.agent_adapters(root) == ["runs", "deploys"]


def test_the_shipped_adapter_deploys_agents() -> None:
    assert agent_tool_access.agent_adapters(REPO) == ["claude-code"]


# --- where they run ------------------------------------------------------------------------------


def test_it_parses_as_python_3_9_and_imports_only_the_standard_library() -> None:
    """The agent runner loads the reader under the system's Python, with nothing installed."""
    tree = ast.parse(READER.read_text(encoding="utf-8"), feature_version=(3, 9))
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
    """Loaded by path and not registered among the modules, as the runner loads it, and
    reading the adapter's declaration there too."""
    python = Path("/usr/bin/python3")
    if not python.exists():
        pytest.skip("no system Python")
    adapter = tmp_path / "adapter"
    adapter.mkdir()
    shutil.copy2(CLAUDE_CODE / "tool-access.json", adapter / "tool-access.json")
    script = (
        "import importlib.util, sys\n"
        "spec = importlib.util.spec_from_file_location('r', sys.argv[1])\n"
        "module = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(module)\n"
        "access = module.tool_access('---\\nwithheld: [Workflow, Wrokflow]\\n---\\n')\n"
        "declaration = module.read_declaration(sys.argv[2])\n"
        "print(access.form, [str(entry) for entry in access.entries])\n"
        "print(declaration.keys[access.form])\n"
        "print(module.harness_refusal(access, [], declaration).split(',')[0])\n"
    )
    done = subprocess.run(
        [str(python), "-B", "-I", "-c", script, str(READER), str(adapter)],
        capture_output=True,
        text=True,
        check=True,
        cwd=tmp_path,
    )
    assert done.stdout.splitlines() == [
        "withheld ['Workflow', 'Wrokflow']",
        "disallowedTools",
        "`withheld` names `Wrokflow`",
    ]
