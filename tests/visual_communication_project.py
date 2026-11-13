"""A project with visual work, built in a test's own folder, for the visual-communication tests.

`project(tmp_path)` makes a project root where the capability is installed: its folder
under `.pkit/capabilities/`, which is how a command finds the root. The other helpers lay
the location's files in it: a library version copied from the shipped foundations or the
test brand, held as `pkit visual add` takes a library the capability ships, read from the
tree, or written from fields; the list of libraries; a piece. No helper runs git,
so the location's files are listed by walking the folder, as outside a repository.

A command imports a plugin when it runs it, and `importable` lets it find the one a test
loaded.
"""

from __future__ import annotations

import io
import json
import shutil
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from ruamel.yaml import YAML

REPO = Path(__file__).resolve().parent.parent
CAPABILITY = REPO / ".pkit" / "capabilities" / "visual-communication"
SCHEMAS = CAPABILITY / "schemas"
#: The foundations' version being built, which every change to them goes into, whatever
#: number it carries (DEC-013 point 2).
FOUNDATIONS = CAPABILITY / "libraries" / "foundations"
#: The released versions of each library the capability ships, each in a place of its own
#: beside the library's record, `releases/<library>/releases.yaml` (DEC-013 point 2).
RELEASES = CAPABILITY / "releases"
#: The foundations' released version 1.0.0, which never changes (DEC-013 point 2): what a
#: test copies where it holds the foundations at 1.0.0, as `pkit visual add
#: foundations@1.0.0` takes them, whatever the version being built carries since.
RELEASED_FOUNDATIONS = RELEASES / "foundations" / "1.0.0"
FIXTURES = REPO / "tests" / "fixtures" / "visual-communication"
TEST_BRAND = FIXTURES / "libraries" / "test-brand" / "1.0.0"
#: A brand built on the test brand, its base (DEC-004 point 6).
TEST_EDITION = FIXTURES / "libraries" / "test-edition" / "1.0.0"
#: A notation the tests name concepts from (DEC-004 point 10).
TEST_NOTATION = FIXTURES / "libraries" / "test-notation" / "1.0.0"
#: A component library with roles of its own, one without a default (DEC-008).
TEST_PARTS = FIXTURES / "libraries" / "test-parts" / "1.0.0"
#: A small picture file of each encoding the capability reads, and of each it refuses
#: (DEC-025 point 5), each named for what it is.
TEST_PICTURES = FIXTURES / "pictures"

#: The capability's project configuration, relative to the project root.
CONFIG = ".pkit/capabilities/visual-communication/project/config.yaml"

#: The agents overlay, relative to the project root, where the designer's grant lies.
OVERLAY = ".pkit/agents/project/overlay.yaml"

#: What a command prints where it records the default location, the designer's grant set
#: at the overlay's top level or not at all (DEC-030 point 5).
RECORDED_DEFAULT = (
    f"recorded the location `visual` (the default, at the repository's top) in {CONFIG}; "
    "to move the work, move the folder, change the `location:` line there, and move the "
    f"designer's grant, the `visual-communication.work:` line of {OVERLAY}, which "
    "`pkit agents reconcile --write` moves while it stays as pkit wrote it"
)


def capability_version() -> str:
    """The capability's version, as its `package.yaml` carries it: the release a run
    records, and the one a library's needed release is read against as installed."""
    package = YAML(typ="safe").load((CAPABILITY / "package.yaml").read_text(encoding="utf-8"))
    return str(package["component"]["version"])


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


def built_as_released(target: Path) -> Path:
    """The foundations' version being built as it stood when 1.0.0 was released, copied to
    `target`, for a capability's folder a test builds: the files of the released version,
    naming release 0.1.0 as the release they need, as the version being built named it
    until that release wrote the capability's version (DEC-013 point 2)."""
    shutil.copytree(RELEASED_FOUNDATIONS, target)
    library = target / "library.yaml"
    text = library.read_text(encoding="utf-8")
    assert "\nneeds-release: 0.3.0\n" in text
    needs = text.replace("\nneeds-release: 0.3.0\n", "\nneeds-release: 0.1.0\n")
    library.write_text(needs, encoding="utf-8")
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


@dataclass(frozen=True)
class Taken:
    """A version of a library the capability ships, as `pkit visual add` takes it: its
    number, the folder of the capability it copies, and the list's entry for it."""

    version: str
    folder: Path
    entry: dict[str, Any]


def taken(name: str, *, being_built: bool = False, version: str | None = None) -> Taken:
    """What `pkit visual add <name>` takes of a library the capability ships, read from the
    tree (DEC-013 point 5): the newest released version, with the entry its record keeps,
    or with `being_built` the released version of the number the version being built
    carries. Where no such version is released, the version being built, not released.
    With `version`, the released version of that number, as `pkit visual add
    <name>@<version>` takes it, which the capability must have released."""
    built = CAPABILITY / "libraries" / name
    safe = YAML(typ="safe")
    number = str(safe.load((built / "library.yaml").read_text(encoding="utf-8"))["version"])
    record = RELEASES / name / "releases.yaml"
    released: dict[str, Any] = {}
    if record.is_file():
        versions = safe.load(record.read_text(encoding="utf-8"))["libraries"][name]["versions"]
        released = {str(each): entry for each, entry in versions.items()}
    if version is not None:
        assert version in released, f"the capability released no {name}@{version}"
    elif being_built:
        version = number if number in released else None
    else:
        version = max(released, key=lambda v: tuple(int(p) for p in v.split(".")), default=None)
    if version is None:
        return Taken(number, built, {"released": False})
    return Taken(version, RELEASES / name / version, dict(released[version]))


def hold_shipped(
    root: Path,
    name: str,
    location: str = "visual",
    *,
    being_built: bool = True,
    version: str | None = None,
) -> Taken:
    """A version of `name`, a library the capability ships, held as `pkit visual add <name>`
    takes it from the tree: the version being built, as `--being-built` takes it, or where
    `being_built` is false the newest released version, or the released version `version`
    names, as `<name>@<version>` takes it. Copied whole in place of any copy of its number,
    and listed from the source `shipped` with its entry, every other entry of the list
    kept."""
    held = taken(name, being_built=being_built, version=version)
    target = version_folder(root, name, held.version, location)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(held.folder, target)
    path = root / location / "libraries" / "libraries.yaml"
    listed = YAML(typ="safe").load(path.read_text(encoding="utf-8")) if path.is_file() else {}
    libraries = dict((listed or {}).get("libraries") or {})
    versions = dict((libraries.get(name) or {}).get("versions") or {})
    versions[held.version] = held.entry
    libraries[name] = {"source": {"kind": "shipped"}, "versions": versions}
    write_list(root, libraries, location)
    return held


def locked_at(folder: Path, versions: Mapping[str, str]) -> Path:
    """The piece in `folder` locked at `versions`, for each library its lock names among
    them, every other field and library of its lock kept: a reference piece drawn on the
    versions a location holds. Returns its `piece.yaml`."""
    path = folder / "piece.yaml"
    piece = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    lock = dict(piece["lock"])
    lock.update({name: version for name, version in versions.items() if name in lock})
    return write(path, yaml_text({**piece, "lock": lock}))


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


#: A colour and a dimension that no mode of the test brand gives, for an axis of a brand's own.
WINTER_ACCENT = {"colorSpace": "srgb", "components": [0.2, 0.4, 0.6], "alpha": 1}
COMPACT_SPACE = {"value": 6, "unit": "px"}


def giving_own_axis(
    folder: Path,
    name: str = "season",
    kind: str = "value",
    contexts: Mapping[str, Any] | None = None,
    default: str | None = None,
) -> Path:
    """The brand at `folder`, made to declare an axis of its own, `name`, of `kind`, as a
    modifier of its Resolver document whose kind lies in the capability's extension point
    (visual-communication DEC-004 points 1 and 2). By default, a value axis `season` gives
    `summer`, its default, as the brand is, and `winter` with another accent; a size axis
    gives its first mode as the brand is and its second with a smaller `space.3`. `contexts`
    and `default` replace those."""
    resolver = next(folder.glob("*.resolver.json"))
    if contexts is None:
        if kind == "value":
            given = {"accent": {"$type": "color", "$value": WINTER_ACCENT}}
            modes = ("summer", "winter")
        else:
            given = {"space": {"$type": "dimension", "3": {"$value": COMPACT_SPACE}}}
            modes = ("roomy", "compact")
        source = f"tokens/{name}.tokens.json"
        write(folder / source, json.dumps(given))
        contexts = {modes[0]: [], modes[1]: [{"$ref": source}]}
    data = json.loads(resolver.read_text(encoding="utf-8"))
    data["modifiers"][name] = {
        "contexts": dict(contexts),
        "default": next(iter(contexts)) if default is None else default,
        "$extensions": {"pkit.visual-communication": {"kind": kind}},
    }
    data["resolutionOrder"].append({"$ref": f"#/modifiers/{name}"})
    resolver.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return folder
