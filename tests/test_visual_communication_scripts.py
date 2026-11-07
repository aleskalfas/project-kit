"""Each visual-communication script runs as its own `uv run --script` program: executable,
with the shebang that runs it, and a PEP 723 header whose every dependency is pinned with
`==` to the version `uv.lock` holds, so the scripts and the tests read files with one set
of libraries (DEC-006 point 6: one reading of every file on every machine). And what `look`
draws with reaches a machine through a query command (DEC-015 point 2)."""

from __future__ import annotations

import os
import re
import tomllib
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from tests.visual_communication_project import CAPABILITY, REPO

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
