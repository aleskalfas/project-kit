"""project-management's scripts use no standard-library name newer than they declare (#2600).

A script runs on every Python its PEP 723 header declares, while the suite and
the linter run it on a newer one. So a name only the newer Python has passes them
both, and fails where a project runs the declared Python.

pyright reads the standard library from typeshed, which says which Pythons have
each name. What it finds at the declared Python and not at the newest it knows is
a name newer than the one declared. Anything else it finds stands at both, and is
left to the type check (#2512).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
DECLARED_PYTHON = re.compile(r'^# requires-python = ">=(\d+)\.(\d+)"$', re.MULTILINE)

Finding = tuple[str, int, str]


def lowest_declared_python() -> str:
    """The lowest Python the scripts declare, which the `_lib` they share runs on too."""
    sources = "".join(script.read_text(encoding="utf-8") for script in SCRIPTS_DIR.glob("*.py"))
    lowest = min((int(major), int(minor)) for major, minor in DECLARED_PYTHON.findall(sources))
    return f"{lowest[0]}.{lowest[1]}"


def pyright_findings(folder: Path, workspace: Path, python: str | None = None) -> set[Finding]:
    """What pyright finds in `folder`, at `python` or else at the newest Python it knows.

    Its `PATH` holds no `python`: pyright would read that interpreter's standard
    library as well as typeshed, and so resolve a module the declared Python lacks.
    """
    config = workspace / "pyrightconfig.json"
    settings = {"include": [os.path.relpath(folder, workspace)], "extraPaths": [str(folder)]}
    config.write_text(json.dumps(settings), encoding="utf-8")
    version = ["--pythonversion", python] if python else []
    run = subprocess.run(
        [sys.executable, "-m", "pyright", "--outputjson", "--project", str(config), *version],
        capture_output=True,
        text=True,
        timeout=300,
        env={**os.environ, "PATH": ""},
    )
    report = json.loads(run.stdout)
    assert report["summary"]["filesAnalyzed"], f"pyright read nothing in {folder}: {run.stderr}"
    return {
        (finding["file"], finding["range"]["start"]["line"], finding["message"])
        for finding in report["generalDiagnostics"]
    }


def names_newer_than(python: str, folder: Path, workspace: Path) -> set[Finding]:
    """What `folder` uses of the standard library that `python` lacks."""
    return pyright_findings(folder, workspace, python) - pyright_findings(folder, workspace)


def test_no_script_uses_a_name_newer_than_the_python_it_declares(tmp_path: Path) -> None:
    assert names_newer_than(lowest_declared_python(), SCRIPTS_DIR, tmp_path) == set()


def test_a_module_a_name_and_a_method_newer_than_a_python_are_found(tmp_path: Path) -> None:
    folder = tmp_path / "scripts"
    folder.mkdir()
    (folder / "probe.py").write_text(
        "import tomllib\n"
        "from datetime import UTC\n"
        "from pathlib import Path\n"
        "print(tomllib, UTC, Path().walk())\n",
        encoding="utf-8",
    )

    found = names_newer_than("3.10", folder, tmp_path)

    assert {line for _, line, _ in found} == {0, 1, 3}
