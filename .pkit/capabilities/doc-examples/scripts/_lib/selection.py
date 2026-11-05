"""The run's configuration and its pages, as the CLI reads them (doc-examples DEC-001).

The project configures the run in `.pkit/capabilities/doc-examples/project/config.yaml`
(points 3 to 5): the types whose documents are its pages, the setup step, the folders
put before the caller's `PATH`, the variables and the project's placeholders. The
pages are the documents of those types, read from the backbone's one answer, `pkit
friction artefacts --json` (COR-056 point 6). This module reads both, and finds what
would stop the run before any command runs, so that the run, which reads them through
`pkit doc-examples pages --json`, and validation agree.

It runs no command of the project's: a setup step, a placeholder's command and a
page's commands run only in the program outside the CLI (point 11).
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

#: This capability's name, as installed under `.pkit/capabilities/`.
CAPABILITY = "doc-examples"
#: The project configuration, relative to the project root.
CONFIG = f".pkit/capabilities/{CAPABILITY}/project/config.yaml"
#: The type whose documents are the pages when the project names none (point 3).
DEFAULT_TYPE = "living-docs:page"
#: The backbone's read command this module reads the artefacts and types through.
ARTEFACTS = ("pkit", "friction", "artefacts", "--json")
#: The version of that document this module reads.
ARTEFACTS_VERSION = 1
#: The version of the pages document this module writes, which the run reads.
SCHEMA_VERSION = 1

#: A variable's name, as a POSIX shell reads one.
VARIABLE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
#: A project placeholder's name: upper case (point 5).
PROJECT_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")

ERROR, WARNING = "error", "warning"

Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class Problem:
    """A finding: its severity, where it lies and what it says."""

    severity: str
    location: str
    message: str

    def as_json(self) -> dict[str, str]:
        return {"severity": self.severity, "location": self.location, "message": self.message}


@dataclass
class Config:
    """The project's configuration of the run. `types` is None when the project names
    none, so the default applies. `read` is False when the file could not be read at
    all, so nothing it names is known."""

    types: tuple[str, ...] | None = None
    setup: tuple[str, ...] = ()
    path: tuple[str, ...] = ()
    environment: dict[str, str | None] = field(default_factory=dict[str, "str | None"])
    placeholders: dict[str, str] = field(default_factory=dict[str, str])
    read: bool = True


def runner_module() -> ModuleType:
    """The run's own program, `run-examples.py`, loaded under a name of its own, for
    the one reading of a fence it holds."""
    name = "doc_examples_run_examples"
    if name in sys.modules:
        return sys.modules[name]
    path = Path(__file__).resolve().parents[1] / "run-examples.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def project_root() -> Path:
    """The project a command runs in: the nearest folder, from the working directory up,
    where this capability is installed, else the working directory."""
    start = Path.cwd()
    for folder in (start, *start.parents):
        if (folder / ".pkit" / "capabilities" / CAPABILITY).is_dir():
            return folder
    return start


# --- the configuration ---------------------------------------------------------------


def _pointer(*parts: str) -> str:
    escaped = (part.replace("~", "~0").replace("/", "~1") for part in parts)
    return f"{CONFIG}:/" + "/".join(escaped)


def read_config(root: Path) -> tuple[Config, list[Problem]]:
    """The configuration at `root`, and each problem that keeps it from being read. No
    file is the default configuration."""
    path = root / CONFIG
    if not path.exists():
        return Config(), []
    try:
        from ruamel.yaml import YAML
        from ruamel.yaml.error import YAMLError

        data = YAML(typ="rt").load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, YAMLError) as exc:
        return Config(read=False), [Problem(ERROR, CONFIG, f"cannot be read: {exc}")]
    if data is None:
        return Config(), []
    if not isinstance(data, Mapping):
        return Config(read=False), [Problem(ERROR, CONFIG, "is no mapping")]
    problems: list[Problem] = []
    config = Config(
        types=_texts(data, "types", problems) if "types" in data else None,
        setup=_texts(data, "setup", problems),
        path=_texts(data, "path", problems),
        environment=_environment(data, problems),
        placeholders=_placeholders(data, problems),
    )
    problems.extend(_names(config))
    return config, problems


def _texts(data: Mapping[str, Any], key: str, problems: list[Problem]) -> tuple[str, ...]:
    value = data.get(key)
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        problems.append(Problem(ERROR, _pointer(key), "is no list of texts"))
        return ()
    return tuple(value)


def _environment(data: Mapping[str, Any], problems: list[Problem]) -> dict[str, str | None]:
    value = data.get("environment")
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        problems.append(Problem(ERROR, _pointer("environment"), "is no mapping"))
        return {}
    found: dict[str, str | None] = {}
    for name, given in value.items():
        if not isinstance(name, str) or not VARIABLE.match(name):
            problems.append(
                Problem(ERROR, _pointer("environment", str(name)), "is no variable's name")
            )
        elif given is not None and not isinstance(given, str):
            problems.append(
                Problem(
                    ERROR,
                    _pointer("environment", name),
                    "takes a text, or nothing for the caller's value; quote a number",
                )
            )
        else:
            found[name] = given
    return found


def _placeholders(data: Mapping[str, Any], problems: list[Problem]) -> dict[str, str]:
    value = data.get("placeholders")
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        problems.append(Problem(ERROR, _pointer("placeholders"), "is no mapping"))
        return {}
    found: dict[str, str] = {}
    for name, command in value.items():
        where = _pointer("placeholders", str(name))
        if not isinstance(command, str) or not command.strip():
            problems.append(Problem(ERROR, where, "takes the command that prints its text"))
        elif not isinstance(name, str) or not PROJECT_NAME.match(name):
            problems.append(
                Problem(
                    ERROR,
                    where,
                    f"a project's placeholder takes a name in upper case, such as "
                    f"`{str(name).upper() or 'VERSION'}`, apart from the capability's own",
                )
            )
        else:
            found[name] = command
    return found


def _names(config: Config) -> list[Problem]:
    """Two placeholders of the project's form with one name: a variable that takes the
    caller's value is written as its name in upper case (point 4)."""
    problems: list[Problem] = []
    taken: dict[str, str] = {name: f"the placeholder `<{name}>`" for name in config.placeholders}
    for name, value in config.environment.items():
        if value is not None:
            continue
        upper = name.upper()
        if upper in taken:
            problems.append(
                Problem(
                    ERROR,
                    _pointer("environment", name),
                    f"takes the caller's value, which the run writes as `<{upper}>`, "
                    f"the name {taken[upper]} has",
                )
            )
        else:
            taken[upper] = f"the variable `{name}`"
    return problems


def errors(problems: Sequence[Problem]) -> list[Problem]:
    return [problem for problem in problems if problem.severity == ERROR]


# --- the pages -----------------------------------------------------------------------


class Unreadable(Exception):
    """The backbone's read command gave no document this module reads."""


def read_artefacts(root: Path, run: Runner = subprocess.run) -> Mapping[str, Any]:
    """The backbone's one answer, `pkit friction artefacts --json`, from `root`."""
    shown = " ".join(ARTEFACTS)
    try:
        done = run(list(ARTEFACTS), cwd=root, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise Unreadable(f"`{shown}` could not be run ({exc})") from exc
    try:
        document = json.loads(done.stdout or "") if done.returncode == 0 else None
    except ValueError:
        document = None
    if not isinstance(document, Mapping):
        said = (done.stderr or "").strip().splitlines()
        raise Unreadable(
            f"`{shown}` exited {done.returncode} without its document"
            + (f": {said[-1]}" if said else "")
        )
    if document.get("schema_version") != ARTEFACTS_VERSION or "types" not in document:
        raise Unreadable(
            f"`{shown}` answered no document of schema_version {ARTEFACTS_VERSION} with "
            "every declared type; this capability reads types (COR-056 point 6), so the "
            "backbone needs upgrading"
        )
    return document


@dataclass(frozen=True)
class Pages:
    """The types the pages are documents of, and the pages, or the problems that keep
    the selection from being read."""

    types: tuple[str, ...] = ()
    paths: tuple[str, ...] = ()
    problems: tuple[Problem, ...] = ()


def select(config: Config, document: Mapping[str, Any]) -> Pages:
    """The pages: the documents of the types the configuration names, or of living-docs'
    page type when it names none and living-docs declares it (point 3)."""
    declared = set(_mapping(document.get("types")))
    project_types = {
        place.get("type")
        for place in _mappings(document.get("places"))
        if place.get("source") == "project" and isinstance(place.get("type"), str)
    }
    if config.types is None:
        if DEFAULT_TYPE not in declared:
            return Pages(
                problems=(
                    Problem(
                        ERROR,
                        CONFIG,
                        "names no types, and no installed component declares living-docs' "
                        f"page type, `{DEFAULT_TYPE}`, the default: name the types of your "
                        "pages under `types`, or install living-docs",
                    ),
                )
            )
        types: tuple[str, ...] = (DEFAULT_TYPE,)
    else:
        types = config.types
    problems: list[Problem] = []
    if not types:
        problems.append(
            Problem(ERROR, _pointer("types"), "names no type, so the run would read no page")
        )
    for name in types:
        if ":" in name and name not in declared:
            problems.append(
                Problem(
                    ERROR,
                    _pointer("types"),
                    f"names `{name}`, which no installed component declares: install the "
                    "component, or name a type that `pkit friction artefacts` lists",
                )
            )
        elif ":" not in name and name not in project_types:
            problems.append(
                Problem(
                    ERROR,
                    _pointer("types"),
                    f"names `{name}`, a type of the project's own that no place in "
                    "`friction.places` gives: give it on the place that holds your pages",
                )
            )
    if problems:
        return Pages(types=types, problems=tuple(problems))
    paths = sorted(
        {
            str(artefact.get("path"))
            for artefact in _mappings(document.get("artefacts"))
            if artefact.get("kind") == "document" and set(_types_of(artefact)) & set(types)
        }
    )
    return Pages(types=types, paths=tuple(paths))


def _types_of(artefact: Mapping[str, Any]) -> list[str]:
    """The type an artefact takes, or each it counts as while a tie stands."""
    if isinstance(artefact.get("type"), str):
        return [artefact["type"]]
    return [
        tied["type"]
        for tied in _mappings(artefact.get("type_conflict"))
        if isinstance(tied.get("type"), str)
    ]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _mappings(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


def document(root: Path, config: Config, pages: Pages) -> dict[str, Any]:
    """The pages document the run reads (`pkit doc-examples pages --json`)."""
    return {
        "schema_version": SCHEMA_VERSION,
        "root": str(root),
        "types": list(pages.types),
        "pages": list(pages.paths),
        "setup": list(config.setup),
        "path": list(config.path),
        "environment": dict(config.environment),
        "placeholders": dict(config.placeholders),
    }
