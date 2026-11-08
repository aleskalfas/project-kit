"""Each visual-communication script runs as its own `uv run --script` program: executable,
with the shebang that runs it, and a PEP 723 header whose every dependency is pinned with
`==` to the version `uv.lock` holds, so the scripts and the tests read files with one set
of libraries (DEC-006 point 6: one reading of every file on every machine). The header
declares every module the script imports, itself or through `_lib`, since the script runs
where nothing else is installed. And what `look` draws with reaches a machine through a
query command (DEC-015 point 2)."""

from __future__ import annotations

import ast
import functools
import importlib.metadata
import os
import re
import sys
import tomllib
from collections.abc import Iterator
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from tests.in_process import load
from tests.visual_communication_project import CAPABILITY, REPO

(seam,) = load("visual-communication", "plugins.seam")

SCRIPTS = sorted((CAPABILITY / "scripts").glob("*.py"))
SHEBANG = "#!/usr/bin/env -S uv run --script"

#: `look` runs from uv's cache alone, so its first run on a machine asks no index.
SHEBANGS = {"look.py": "#!/usr/bin/env -S uv run --offline --script"}

#: The wheel of the viewing step's tool.
TOOL = "resvg-py"

#: A PEP 723 metadata block, as the specification's reference regular expression reads it.
_BLOCK = re.compile(r"(?m)^# /// (?P<type>[a-zA-Z0-9-]+)$\s(?P<content>(^#(| .*)$\s)+)^# ///$")
_PIN = re.compile(r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)==(?P<version>[^\s;,]+)$")


def _normalised(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _locked() -> dict[str, str]:
    lock = tomllib.loads((REPO / "uv.lock").read_text(encoding="utf-8"))
    return {
        _normalised(package["name"]): package["version"]
        for package in lock["package"]
        if "version" in package
    }


def _metadata(path: Path) -> dict[str, object]:
    blocks = [m for m in _BLOCK.finditer(path.read_text(encoding="utf-8")) if m["type"] == "script"]
    assert len(blocks) == 1, f"{path.name} has {len(blocks)} `script` metadata blocks"
    content = "".join(
        line[2:] if line.startswith("# ") else line[1:]
        for line in blocks[0]["content"].splitlines(keepends=True)
    )
    return tomllib.loads(content)


def test_the_capability_has_scripts() -> None:
    assert [path.name for path in SCRIPTS] != []


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda path: path.name)
def test_each_script_is_executable_and_runs_by_uv(path: Path) -> None:
    assert path.read_text(encoding="utf-8").splitlines()[0] == SHEBANGS.get(path.name, SHEBANG)
    assert os.access(path, os.X_OK), f"{path.name} is not executable"


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda path: path.name)
def test_each_scripts_dependencies_are_pinned_to_the_lock(path: Path) -> None:
    metadata = _metadata(path)
    assert metadata.get("requires-python") == ">=3.10"
    dependencies = metadata.get("dependencies", [])
    assert isinstance(dependencies, list)
    locked = _locked()
    for dependency in dependencies:
        pin = _PIN.match(str(dependency))
        assert pin is not None, f"{path.name}: `{dependency}` is not pinned with `==`"
        name = _normalised(pin["name"])
        assert name in locked, f"{path.name}: `{pin['name']}` is not in uv.lock"
        assert pin["version"] == locked[name], (
            f"{path.name} pins {pin['name']} {pin['version']}, uv.lock holds {locked[name]}"
        )


def _pinned(name: str) -> set[str]:
    return {str(each) for each in _dependencies(CAPABILITY / "scripts" / name)}


def _dependencies(path: Path) -> list[object]:
    dependencies = _metadata(path).get("dependencies", [])
    assert isinstance(dependencies, list)
    return dependencies


# --- what a script imports ----------------------------------------------------------------------

#: The unit of a module's own statements, which run when it is imported. Every other unit
#: is a function or a class at the module's top, whole.
_TOP = "<module>"

_DEFS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)

#: Each function that runs a plugin, by its module and name, with the kind of plugin it
#: runs. The seam imports the implementation by the module its declaration names
#: (`seam.implementation`), so no import statement names it.
RUNS_A_PLUGIN = {
    ("_lib.code", "text_of"): seam.CODE_WRITER,
    ("_lib.framing", "run"): seam.PRODUCER,
    ("_lib.pipeline", "drawn"): seam.RENDERER,
}

#: The seam's function that imports a plugin's implementation.
_IMPLEMENTATION = ("_lib.plugins.seam", "implementation")


class _Source:
    """A module of the scripts' folder, read as source: its functions and classes at its
    top, by name, and what each name its imports bind stands for, a module or a name in
    one."""

    def __init__(self, name: str, path: Path) -> None:
        self.name = name
        self.package = name if path.name == "__init__.py" else name.rpartition(".")[0]
        self.tree = ast.parse(path.read_text(encoding="utf-8"))
        self.defs = {node.name: node for node in self.tree.body if isinstance(node, _DEFS)}
        self.bound: dict[str, tuple[str, str | None]] = {}
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.asname:
                        self.bound[alias.asname] = (alias.name, None)
                    else:
                        top = alias.name.partition(".")[0]
                        self.bound[top] = (top, None)
            elif isinstance(node, ast.ImportFrom):
                module = self.absolute(node)
                for alias in node.names:
                    self.bound[alias.asname or alias.name] = (module, alias.name)

    def absolute(self, node: ast.ImportFrom) -> str:
        """The module a `from` import names, a relative one read from the module's package."""
        if not node.level:
            return node.module or ""
        parts = self.package.split(".")
        return ".".join([*parts[: len(parts) - node.level + 1], *filter(None, [node.module])])

    def nodes(self, unit: str) -> list[ast.AST]:
        """The code of `unit`: a function or a class, or the module's own statements with the
        decorators they run."""
        if unit != _TOP:
            return [self.defs[unit]]
        own: list[ast.AST] = [node for node in self.tree.body if not isinstance(node, _DEFS)]
        return own + [each for node in self.defs.values() for each in node.decorator_list]

    def third_party(self, unit: str) -> Iterator[str]:
        """The top-level name of each module `unit` imports that neither the standard library
        nor the scripts' folder holds."""
        for root in self.nodes(unit):
            for node in ast.walk(root):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [self.absolute(node)]
                else:
                    continue
                for name in names:
                    top = name.partition(".")[0]
                    if top not in sys.stdlib_module_names and top not in _sources():
                        yield top


@functools.cache
def _sources() -> dict[str, _Source]:
    """Every module of the scripts' folder by its name: a script by its file's stem, and a
    module of `_lib` as the scripts import it."""
    folder = CAPABILITY / "scripts"
    found = {}
    for path in sorted(folder.rglob("*.py")):
        parts = path.relative_to(folder).with_suffix("").parts
        name = ".".join(parts[:-1] if parts[-1] == "__init__" else parts)
        found[name] = _Source(name, path)
    return found


def _imported(module: str) -> list[tuple[str, str]]:
    """The units an import of `module` runs: the own statements of it and of each package
    above it that the scripts' folder holds."""
    parts = module.split(".")
    names = (".".join(parts[:count]) for count in range(1, len(parts) + 1))
    return [(name, _TOP) for name in names if name in _sources()]


def _referred(source: _Source, parts: list[str]) -> list[tuple[str, str]]:
    """The units a dotted name in `source` stands for, such as `files.shape_problems`: the
    function or class it names, with the own statements of each module on the way."""
    first, *rest = parts
    if first in source.defs:
        return [(source.name, first)]
    if first not in source.bound:
        return []
    module, name = source.bound[first]
    if name is not None and f"{module}.{name}" not in _sources():
        if module not in _sources():
            return []
        return _imported(module) + _referred(_sources()[module], [name])
    module = module if name is None else f"{module}.{name}"
    if module not in _sources():
        return []
    reached = _imported(module)
    for attribute in rest:
        if f"{module}.{attribute}" not in _sources():
            return reached + _referred(_sources()[module], [attribute])
        module = f"{module}.{attribute}"
        reached += _imported(module)
    return reached


def _dotted(node: ast.expr) -> list[str] | None:
    """The parts of a dotted name, such as `pl.LibraryEnv`; None for any other expression."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    return [node.id, *reversed(parts)] if isinstance(node, ast.Name) else None


def _runs(source: _Source, unit: str) -> Iterator[tuple[str, str]]:
    """Each unit that `unit` of `source` may run: what its imports run, each function or
    class it names, and each shipped plugin of the kind it runs."""
    for root in source.nodes(unit):
        for node in ast.walk(root):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    yield from _imported(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = source.absolute(node)
                yield from _imported(module)
                for alias in node.names:
                    yield from _imported(f"{module}.{alias.name}")
            elif isinstance(node, (ast.Name, ast.Attribute)):
                parts = _dotted(node)
                if parts is not None:
                    yield from _referred(source, parts)
    kind = RUNS_A_PLUGIN.get((source.name, unit))
    for plugin in seam.names(kind) if kind else []:
        yield from _imported(f"_lib.plugins.{seam.declaration(plugin)['module']}")


def _reached(script: str) -> set[tuple[str, str]]:
    """Each unit a run of `script` may run: the script's own code, and what that runs in
    turn. A name stands for the code it names wherever it is called, and a class for every
    method it holds, so the reach errs toward more."""
    todo = [(script, _TOP), *((script, name) for name in _sources()[script].defs)]
    reached: set[tuple[str, str]] = set()
    while todo:
        unit = todo.pop()
        if unit not in reached:
            reached.add(unit)
            todo.extend(_runs(_sources()[unit[0]], unit[1]))
    return reached


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda path: path.name)
def test_each_script_declares_every_module_it_imports(path: Path) -> None:
    """A script runs where only what its header declares is installed, so it stops where it
    imports any other module (#2869). Read from the source: a module's own imports run once
    it is imported, a function's once the script may run it, and a plugin's once a
    function that runs a plugin of its kind may run."""
    declared = {
        _normalised(pin["name"]) for each in _dependencies(path) if (pin := _PIN.match(str(each)))
    }
    providers = importlib.metadata.packages_distributions()
    missing: dict[str, set[str]] = {}
    for module, unit in _reached(path.stem):
        for name in _sources()[module].third_party(unit):
            if not {_normalised(each) for each in providers.get(name, [])} & declared:
                missing.setdefault(name, set()).add(module if unit == _TOP else f"{module}.{unit}")
    assert missing == {}, f"{path.name}'s header does not declare what it imports: " + "; ".join(
        f"`{name}`, of {' or '.join(providers.get(name, ['no installed distribution']))}, "
        f"imported in {', '.join(sorted(where))}"
        for name, where in sorted(missing.items())
    )


def test_each_function_that_runs_a_plugin_names_the_kind_it_runs() -> None:
    """The functions that ask the seam for a plugin's implementation are the ones
    `RUNS_A_PLUGIN` names, so the test above reaches each plugin a script may run."""
    asking = {
        (name, unit)
        for name, source in _sources().items()
        if name != _IMPLEMENTATION[0]
        for unit in source.defs
        if _IMPLEMENTATION in set(_runs(source, unit))
    }
    assert asking == set(RUNS_A_PLUGIN)


def test_what_look_draws_with_reaches_a_machine_through_the_query_command_that_pins_it() -> None:
    """`pkit sync` provisions a query command alone, and `look` writes, so it is none. So
    `pages` pins every package `look` does: its pins are what puts them in uv's cache."""
    commands = YAML(typ="safe").load(CAPABILITY / "package.yaml")["commands"]
    assert "query-contract" not in commands["look"]
    assert commands["pages"]["query-contract"] is True
    assert _pinned("look.py") <= _pinned("pages.py")
    assert any(each.startswith(f"{TOOL}==") for each in _pinned("look.py"))


def test_only_the_scripts_that_draw_pin_the_tool() -> None:
    """Every other command runs on a machine that never draws."""
    pinning = [path.name for path in SCRIPTS if f"{TOOL}==" in path.read_text(encoding="utf-8")]
    assert pinning == ["look.py", "pages.py"]


def test_looks_stop_is_an_exit_of_its_own_named_in_its_header_and_its_help() -> None:
    """A stop leaves the page files and a report, where a refusal leaves the folder as it was
    (DEC-020 point 8), so neither 1 nor argparse's 2 says it."""
    header = (CAPABILITY / "scripts" / "look.py").read_text(encoding="utf-8")
    assert "\n  3  stopped: " in header
    commands = YAML(typ="safe").load(CAPABILITY / "package.yaml")["commands"]
    assert "; 3 when it stopped, " in commands["look"]["help"]
