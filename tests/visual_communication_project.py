"""A project with visual work, built in a test's own folder, for the visual-communication tests.

`project(tmp_path)` makes a project root where the capability is installed: its folder
under `.pkit/capabilities/`, which is how a command finds the root. The other helpers lay
the location's files in it: a library version copied from the shipped foundations or the
test brand, or written from fields; the list of libraries; a piece. No helper runs git,
so the location's files are listed by walking the folder, as outside a repository.

A command imports a plugin when it runs it, and `importable` lets it find the one a test
loaded.
"""

from __future__ import annotations

import io
import shutil
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from ruamel.yaml import YAML

REPO = Path(__file__).resolve().parent.parent
CAPABILITY = REPO / ".pkit" / "capabilities" / "visual-communication"
SCHEMAS = CAPABILITY / "schemas"
FOUNDATIONS = CAPABILITY / "libraries" / "foundations"
FIXTURES = REPO / "tests" / "fixtures" / "visual-communication"
TEST_BRAND = FIXTURES / "libraries" / "test-brand" / "1.0.0"
#: A brand built on the test brand, its base (DEC-004 point 6).
TEST_EDITION = FIXTURES / "libraries" / "test-edition" / "1.0.0"

#: The capability's project configuration, relative to the project root.
CONFIG = ".pkit/capabilities/visual-communication/project/config.yaml"


def yaml_text(data: Any) -> str:
    """`data` as block YAML."""
    yaml = YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)
    stream = io.StringIO()
    yaml.dump(data, stream)
    return stream.getvalue()


def bound(schema: str, /, **fields: Any) -> dict[str, Any]:
    """A file of the capability's format bound to `schema`, then `fields`."""
    return {"pkit_schema": f"visual-communication:{schema}", "schema_version": 1, **fields}


def write(path: Path, text: str) -> Path:
    """Write `text` at `path`, making its folders."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def project(tmp_path: Path) -> Path:
    """A project root where the capability is installed."""
    root = tmp_path / "project"
    (root / ".pkit" / "capabilities" / "visual-communication").mkdir(parents=True)
    return root


def importable(monkeypatch: pytest.MonkeyPatch, *plugins: ModuleType) -> None:
    """Each plugin a test loaded (`tests.in_process.load`), found by the import a command
    makes when it runs it (`seam.implementation`), for the length of the test: `load`
    keeps no `_lib` in `sys.modules` once it returns."""
    for plugin in plugins:
        monkeypatch.setitem(sys.modules, plugin.__name__, plugin)


def version_folder(root: Path, name: str, version: str, location: str = "visual") -> Path:
    return root / location / "libraries" / name / version


def copy_library(
    root: Path, source: Path, name: str, version: str, location: str = "visual"
) -> Path:
    """A library version copied whole into the location's library folder."""
    target = version_folder(root, name, version, location)
    shutil.copytree(source, target)
    return target


def add_library(
    root: Path,
    name: str,
    version: str,
    *,
    builds_on: Mapping[str, int] | None = None,
    needs_release: str = "0.1.0",
    kind: str = "components",
    location: str = "visual",
) -> Path:
    """A component library version written from its fields alone."""
    folder = version_folder(root, name, version, location)
    library = bound(
        "library",
        name=name,
        version=version,
        kind=kind,
        **{
            "needs-release": needs_release,
            "builds-on": [{"name": n, "major": m} for n, m in (builds_on or {}).items()],
        },
    )
    write(folder / "library.yaml", yaml_text(library))
    return folder


def write_list(root: Path, libraries: Mapping[str, Any], location: str = "visual") -> Path:
    """The location's list of libraries."""
    return write(
        root / location / "libraries" / "libraries.yaml",
        yaml_text(bound("libraries", libraries=dict(libraries))),
    )


def write_piece(root: Path, name: str, location: str = "visual", **fields: Any) -> Path:
    """A piece's `piece.yaml`, a draft of the test brand unless `fields` say otherwise."""
    piece = bound(
        "piece",
        top="foundations/figure",
        brand="test-brand",
        languages=["en"],
        audience="Tests.",
        shown="Nowhere.",
        explains=False,
        exports=[],
        state="draft",
    )
    piece.update(fields)
    return write(root / location / "pieces" / name / "piece.yaml", yaml_text(piece))
