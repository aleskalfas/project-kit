"""Each capability's and adapter's command that prints a document for a program has its
contracts pinned, or waits in a baseline that only shrinks (ADR-097 point 7).

The contracts live beside the tests that check them against a real run, one module for
each capability, and each module's `CONTRACTS` names them by the command's words: the
component's name, then the command's path through its `commands:` tree, such as
`visual-communication pages`. This module holds the ratchet over them all.

**Which commands print a document.** Each command a capability or an adapter of this
checkout registers whose script takes `--json`, or a `--format` with the choice `json`,
as the backbone's ratchet finds a backbone command by its `--json`
(`tests/test_backbone_documents.py`). A script is read for its parser's options, never
run: an option its script does not declare in its own text, such as one a `_lib` module
adds, is not found.

**What an engine runs is not one** (ADR-097 point 1, "Not covered"). A command a backbone
engine runs under the runner's policies prints its document for that engine, and the
record that sets the engine's contract with the command sets its shape (ADR-057 point 5).
Such a command is one its component names where an engine finds it:

- a validator, under `validators.<name>.command` (ADR-058);
- a data point's filler, under `connections.extensions.contributes[].command` (COR-052
  point 5);
- an artefact kind's resolver, under `friction.kinds.<kind>.command` (COR-050);
- a write category's default query, under `write_categories.<name>.default-query`
  (COR-073);
- a process's predicate, as the `run` of a process definition in the component's
  `schemas/` (COR-033).

A predicate a capability registers for a process definition to name, where none it ships
names it, prints the same predicate document for the process engine, so it is not one
either. No declaration says so, so `PREDICATES` names each.

Every other command found has its contracts in a module's `CONTRACTS`, or stands in
`tests/capability_documents_baseline.txt` until a change pins them. Nothing is ever added
to the baseline.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from project_kit.command_runner import registered_commands
from tests import test_doc_examples_documents as doc_examples
from tests import test_lean_business_documents as lean_business
from tests import test_pm_documents as project_management
from tests import test_software_analysis_documents as software_analysis
from tests import test_visual_communication_documents as visual_communication
from tests.document_contracts import Contract
from tests.in_process import REPO

BASELINE = Path(__file__).with_name("capability_documents_baseline.txt")

#: Where the components this checkout ships lie: each capability, then each adapter.
COMPONENT_FOLDERS = (REPO / ".pkit" / "capabilities", REPO / ".pkit" / "adapters")

#: The option by which a command prints its document for a program, and the choice of
#: `FORMAT_OPTION` that does.
JSON_OPTION = "--json"
FORMAT_OPTION = "--format"
JSON_CHOICE = "json"

#: The contracts of each capability's and adapter's command that prints a document for a
#: program, by the command's words.
CONTRACTS: Mapping[str, tuple[Contract, ...]] = {
    **doc_examples.CONTRACTS,
    **lean_business.CONTRACTS,
    **project_management.CONTRACTS,
    **software_analysis.CONTRACTS,
    **visual_communication.CONTRACTS,
}

#: The process predicates a capability registers for direct use, which no process
#: definition it ships names: each answers the process engine's predicate contract
#: (COR-033), as project-management's lifecycle predicates do (DEC-033). A command joins
#: only where its document is that contract's and nothing else.
PREDICATES = frozenset(
    {
        "project-management detect-backlog",
        "project-management detect-done",
        "project-management detect-in-progress",
        "project-management detect-review",
        "project-management detect-todo",
        "project-management parent-active-descendant",
    }
)

#: Where a component's package file names a command a backbone engine runs: a path of
#: keys, `*` for each value of a mapping and `[]` for each item of a list.
EACH_VALUE = "*"
EACH_ITEM = "[]"
ENGINE_NAMED: tuple[tuple[str, ...], ...] = (
    ("validators", EACH_VALUE, "command"),
    ("connections", "extensions", "contributes", EACH_ITEM, "command"),
    ("friction", "kinds", EACH_VALUE, "command"),
    ("write_categories", EACH_VALUE, "default-query"),
)

_yaml = YAML(typ="safe")


def components(folders: tuple[Path, ...] = COMPONENT_FOLDERS) -> Iterator[Path]:
    """Each component's folder in `folders`, by name within each: by default each
    capability and each adapter this checkout ships."""
    for folder in folders:
        yield from sorted(path.parent for path in folder.glob("*/package.yaml"))


def prints_a_document(script: Path) -> bool:
    """Whether `script` takes `--json`, or a `--format` with the choice `json`. A script
    that is not Python is read for the word `--json`."""
    text = script.read_text(encoding="utf-8")
    if script.suffix != ".py":
        return JSON_OPTION in text.split()
    for node in ast.walk(ast.parse(text)):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr != "add_argument":
            continue
        options = {arg.value for arg in node.args if isinstance(arg, ast.Constant)}
        if JSON_OPTION in options:
            return True
        if FORMAT_OPTION in options and JSON_CHOICE in _choices(node):
            return True
    return False


def _choices(node: ast.Call) -> list[Any]:
    for keyword in node.keywords:
        if keyword.arg == "choices":
            try:
                return list(ast.literal_eval(keyword.value))
            except ValueError:
                return []
    return []


def engine_run(component: Path) -> set[str]:
    """The commands of `component` a backbone engine runs, by their path through its
    `commands:` tree."""
    package = _yaml.load((component / "package.yaml").read_text(encoding="utf-8"))
    named = [reference for where in ENGINE_NAMED for reference in _at(package, where)]
    for definition in sorted((component / "schemas").glob("*.yaml")):
        held = _yaml.load(definition.read_text(encoding="utf-8"))
        if isinstance(held, dict):
            named += list(_runs(held.get("process")))
    return {reference for reference in named if isinstance(reference, str)}


def _at(node: Any, where: tuple[str, ...]) -> Iterator[Any]:
    """Each value at `where` in `node`: `*` steps into each value of a mapping, and `[]`
    into each item of a list."""
    if not where:
        yield node
        return
    step, rest = where[0], where[1:]
    if step == EACH_VALUE and isinstance(node, dict):
        children: list[Any] = list(node.values())
    elif step == EACH_ITEM and isinstance(node, list):
        children = list(node)
    elif isinstance(node, dict) and step in node:
        children = [node[step]]
    else:
        children = []
    for child in children:
        yield from _at(child, rest)


def _runs(node: Any) -> Iterator[Any]:
    """Each `run` a process definition holds, at any depth."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "run":
                yield value
            yield from _runs(value)
    elif isinstance(node, list):
        for item in node:
            yield from _runs(item)


def printing_documents(folders: tuple[Path, ...] = COMPONENT_FOLDERS) -> set[str]:
    """Each command of a component in `folders` that prints a document for a program, by
    its words: by default each capability's and each adapter's this checkout ships, less
    the `PREDICATES`."""
    return taking_json(folders) - PREDICATES


def taking_json(folders: tuple[Path, ...] = COMPONENT_FOLDERS) -> set[str]:
    """Each command of a component in `folders` that takes `--json`, or a `--format` with
    the choice `json`, and that no engine runs by its component's declaration."""
    found: set[str] = set()
    for component in components(folders):
        run_by_an_engine = engine_run(component)
        for tokens, command in registered_commands(component).items():
            reference = " ".join(tokens)
            if reference in run_by_an_engine or not command.script.is_file():
                continue
            if prints_a_document(command.script):
                found.add(f"{component.name} {reference}")
    return found


def baseline() -> set[str]:
    """The commands whose documents no contract pins yet."""
    lines = BASELINE.read_text(encoding="utf-8").splitlines()
    return {line.strip() for line in lines if line.strip() and not line.startswith("#")}


def test_every_command_that_prints_a_document_has_its_contracts() -> None:
    missing = printing_documents() - set(CONTRACTS) - baseline()
    assert not missing, (
        f"{sorted(missing)} print a document for a program, and no contract pins it: pin "
        f"each document's contract beside its capability's tests (ADR-097 point 7)"
    )


def test_the_baseline_names_only_commands_no_contract_pins() -> None:
    assert not baseline() & set(CONTRACTS), "a command with its contracts leaves the baseline"
    assert baseline() <= printing_documents(), (
        "the baseline names a command that prints no document"
    )


def test_each_predicate_named_takes_json_and_has_no_contract() -> None:
    assert taking_json() >= PREDICATES, (
        f"{sorted(PREDICATES - taking_json())} are named as predicates, and are no command "
        f"that takes --json, or are one a process definition names"
    )
    assert not PREDICATES & (set(CONTRACTS) | baseline())


def test_a_contract_names_only_a_command_that_prints_a_document() -> None:
    assert set(CONTRACTS) <= printing_documents(), (
        f"{sorted(set(CONTRACTS) - printing_documents())} print no document for a program "
        f"that this ratchet finds"
    )


def test_the_ratchet_finds_a_command_by_its_option_and_leaves_what_an_engine_runs(
    tmp_path: Path,
) -> None:
    component = tmp_path / "capabilities" / "acme"
    scripts = {
        "listed.py": 'parser.add_argument("--json", action="store_true")\n',
        "formatted.py": 'parser.add_argument("--format", choices=["text", "json"])\n',
        "plain.py": 'parser.add_argument("--format", choices=["text", "markdown"])\n',
        "shell.sh": "#!/bin/sh\n[ \"$1\" = --json ] && echo '{}'\n",
        "validator.py": 'parser.add_argument("--json", action="store_true")\n',
        "filler.py": 'parser.add_argument("--json", action="store_true")\n',
        "resolver.py": 'parser.add_argument("--json", action="store_true")\n',
        "query.py": 'parser.add_argument("--json", action="store_true")\n',
        "predicate.py": 'parser.add_argument("--json", action="store_true")\n',
    }
    for name, text in scripts.items():
        (component / "scripts").mkdir(parents=True, exist_ok=True)
        (component / "scripts" / name).write_text(text, encoding="utf-8")
    commands = "".join(f"  {Path(name).stem}:\n    script: scripts/{name}\n" for name in scripts)
    (component / "package.yaml").write_text(
        f"commands:\n{commands}"
        "validators:\n  checks:\n    command: validator\n"
        "connections:\n  extensions:\n    contributes:\n      - point: x\n        command: filler\n"
        "friction:\n  kinds:\n    source:\n      command: resolver\n"
        "write_categories:\n  acme.work:\n    default-query: query\n",
        encoding="utf-8",
    )
    (component / "schemas").mkdir()
    (component / "schemas" / "flow.yaml").write_text(
        "process:\n  id: flow\n  states:\n    - gate:\n        run: predicate\n",
        encoding="utf-8",
    )
    assert printing_documents((tmp_path / "capabilities",)) == {
        "acme listed",
        "acme formatted",
        "acme shell",
    }
