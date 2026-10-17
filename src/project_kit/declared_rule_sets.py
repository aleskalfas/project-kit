"""The one project rule set a capability declares, and its creation (COR-017).

A capability that ships a method rule set may declare, in its package metadata
under `project_rule_set`, one project rule set for its install to create: the
set's name, a title, its scope by the capability's own artefact types, and the
name of the capability's own method set that the set inherits (the lifecycle
README, "Field layout and casing"). A method set takes no scope, so its rules
bind only through a set of the project's own that inherits it (COR-051 point 7).
The declared set is that set.

This module is the one home of what install decides about it, read by the two
operations COR-017 and COR-051 point 6 name as its writers, and by a person:

- `plan` decides, for one project, whether the set would be created and why
  not. It is created only where no set of the project's own inherits the
  method set, directly or not (`rule_sets.inheritors`, the backbone's one
  answer, never a walk of this module's). Nothing is created over a file, under
  a name another rule set declares (COR-051 point 3), through a link, or while
  a project rule-set file cannot be read, since that file might inherit it.
  It pins the method set's major as the capability's copy has it.
- `create` writes the planned set, and never over a file.
- `pkit capabilities install` plans and creates it once for each install
  (`cli.install_capability_cmd`). A migration of the capability, for a project
  that installed it before it declared one, reads the plan through
  `pkit capabilities project-rule-set <name> --json` and writes its text
  (ADR-057 point 1: a migration reads the backbone's answer, and never
  computes it again). Sync and an upgrade never create it, and it is no seed
  path (ADR-065 point 11).

The file it writes lies in `rule-sets/` under the internal documentation root,
the project's own rule-set place by the location rule (ADR-056 point 2), so the
backbone finds it with no configuration.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, cast

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from project_kit import friction_discovery as fd
from project_kit import rule_sets as rs
from project_kit.package_validate import PROJECT_RULE_SET_KEY

#: The package-metadata key a capability declares its project rule set under,
#: whose shape and repository checks the packages check owns.
KEY = PROJECT_RULE_SET_KEY

#: The created set's own version: a new set, with no rule of its own yet.
VERSION = "1.0.0"

#: The version of the reading document `to_json` prints.
SCHEMA_VERSION = 1

_yaml: Any = YAML(typ="safe")

#: A component's type as a scope names it, `<component>:<type>`: the package
#: schema's pattern for a declared type, so a declaration the packages check
#: refuses is never written into a scope.
_TYPE = re.compile(rf"{rs.COMPONENT_PATTERN}:[a-z][a-z0-9]*(?:-[a-z0-9]+)*")


@dataclass(frozen=True)
class Declaration:
    """The project rule set a capability declares, as its package metadata gives it."""

    capability: str
    name: str  # the set's name, `[A-Z][A-Z0-9]*`
    inherits: str  # the name of one of the capability's own method sets
    types: tuple[str, ...]  # the scope: the capability's own types, `<capability>:<type>`
    title: str

    @property
    def method_set(self) -> str:
        """The inherited method set as cited: `<capability>:<SET>`."""
        return f"{self.capability}:{self.inherits}"


@dataclass(frozen=True)
class Plan:
    """What install would do with a declared set in one project.

    `creates` is true where no set of the project's own inherits the method set
    and nothing stops the creation. `inherited_by` names the project sets that
    inherit it, directly or not: there the project has already chosen, and
    nothing is created. `blocked` says why nothing can be created otherwise.
    `text` is what would be written, where the set would be created.
    """

    declaration: Declaration
    path: str  # where the set is created, relative to the project root
    pin: str | None  # `<capability>:<SET>@<major>`, or None when the major cannot be read
    inherited_by: tuple[str, ...]
    blocked: str | None
    text: str | None

    @property
    def creates(self) -> bool:
        return not self.inherited_by and self.blocked is None and self.text is not None


def read_declaration(capability: str, component_dir: Path) -> Declaration | None:
    """The capability's declared project rule set, read forgivingly from its
    `package.yaml`: None where it declares none, or one not in the declared shape,
    which the packages check of `pkit validate` reports."""
    try:
        data = _yaml.load((component_dir / "package.yaml").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, YAMLError):
        return None
    if not isinstance(data, Mapping):
        return None
    raw: Any = cast("Mapping[str, Any]", data).get(KEY)
    if not isinstance(raw, Mapping):
        return None
    declared = cast("Mapping[str, Any]", raw)
    name, inherits, title = declared.get("name"), declared.get("inherits"), declared.get("title")
    scope: Any = declared.get("scope")
    types: Any = (
        cast("Mapping[str, Any]", scope).get("types") if isinstance(scope, Mapping) else None
    )
    set_name = re.compile(rs.SET_NAME_PATTERN)
    if not (
        isinstance(name, str)
        and set_name.fullmatch(name)
        and isinstance(inherits, str)
        and set_name.fullmatch(inherits)
        and isinstance(title, str)
        and title.strip()
        and "\n" not in title
        and isinstance(types, list)
        and types
        and all(isinstance(t, str) and _TYPE.fullmatch(t) for t in cast("list[Any]", types))
    ):
        return None
    return Declaration(
        capability=capability,
        name=name,
        inherits=inherits,
        types=tuple(cast("list[str]", types)),
        title=title.strip(),
    )


def target_path(target_root: Path, name: str) -> str:
    """Where the set is created: `<internal root>/rule-sets/<name in lower case>.md`,
    the project's own rule-set place by the location rule (ADR-056 point 2)."""
    internal = fd.read_friction_settings(target_root).internal_root
    return (PurePosixPath(internal) / fd.RULE_SETS_SEGMENT / f"{name.lower()}.md").as_posix()


def plan(target_root: Path, capability: str, component_dir: Path) -> Plan | None:
    """Whether installing `capability` would create its declared set in this project,
    and what it would write. None where the capability declares no set.

    `component_dir` holds the capability whose declaration and method set are read:
    the copy being installed, or the project's installed copy. The project's rule
    sets are read as the backbone discovers them in the working tree.
    """
    declaration = read_declaration(capability, component_dir)
    if declaration is None:
        return None
    path = target_path(target_root, declaration.name)
    discovery = rs.discover_rule_sets(target_root)
    inherited_by = tuple(
        rule_set.path for rule_set in rs.inheritors(discovery, capability, declaration.inherits)
    )
    method = next(
        (
            rule_set
            for rule_set in rs.component_rule_sets(capability, component_dir).rule_sets
            if rule_set.name == declaration.inherits
        ),
        None,
    )
    pin = (
        None
        if method is None or method.major is None
        else f"{declaration.method_set}@{method.major}"
    )
    blocked = (
        None if inherited_by else _blocked(target_root, declaration, discovery, path, method, pin)
    )
    text = (
        render(declaration, pin)
        if pin is not None and blocked is None and not inherited_by
        else None
    )
    return Plan(
        declaration=declaration,
        path=path,
        pin=pin,
        inherited_by=inherited_by,
        blocked=blocked,
        text=text,
    )


def _blocked(
    target_root: Path,
    declaration: Declaration,
    discovery: rs.RuleSetDiscovery,
    path: str,
    method: rs.RuleSet | None,
    pin: str | None,
) -> str | None:
    """Why the set cannot be created, the first reason found; None where it can."""
    if method is None:
        return (
            f"{declaration.capability} ships no method rule set named {declaration.inherits}, "
            f"which its declared set inherits"
        )
    if pin is None:
        return f"the version of {declaration.method_set}, in {method.path}, cannot be read"
    unreadable = sorted(u.path for u in discovery.unreadable if u.place.component is None)
    if unreadable:
        return (
            f"{unreadable[0]} cannot be read as a rule set, so whether it inherits "
            f"{declaration.method_set} cannot be told"
        )
    taken = discovery.sets_named(declaration.name)
    if taken:
        return (
            f"rule set {declaration.name} is declared already, by {taken[0].path}: "
            f"rule-set names are unique (COR-051 point 3)"
        )
    target = target_root / path
    if target.exists() or target.is_symlink():
        return f"{path} exists already, and install never writes over a file"
    for parent in reversed(PurePosixPath(path).parents):
        folder = target_root / parent
        if parent == PurePosixPath("."):
            continue
        if folder.is_symlink():
            return f"{parent.as_posix()} is a link, and install writes nothing through one"
        if folder.exists() and not folder.is_dir():
            return f"{parent.as_posix()} is a file, where the set's folder would be"
    return None


def render(declaration: Declaration, pin: str) -> str:
    """The created set: its data, then a short body saying what it is."""
    major = pin.rsplit("@", 1)[1]
    types = ", ".join(declaration.types)
    listed = ", ".join(f"`{t}`" for t in declaration.types)
    return (
        "---\n"
        f"rule-set: {declaration.name}\n"
        f"version: {VERSION}\n"
        f"inherits: [{pin}]\n"
        "scope:\n"
        f"  types: [{types}]\n"
        "rules: {}\n"
        "---\n"
        "\n"
        f"# {declaration.name} — {declaration.title}\n"
        "\n"
        f"Installing the capability `{declaration.capability}` created this rule set "
        "(COR-017). It is the project's own, to edit or remove. While the capability "
        "stays installed, nothing creates it again.\n"
        "\n"
        f"- **What it selects:** every artefact of the types {listed}.\n"
        f"- **What it inherits:** `{declaration.method_set}`, pinned at "
        f"`{declaration.inherits}@{major}`. Its accepted rules bind on what this set "
        "selects (COR-051 point 7). When it reaches a new major, review the new major "
        "and update the pin.\n"
        "- **Its own rules:** none yet. Add a rule here with its data in the front matter "
        "(COR-051 point 2).\n"
    )


def create(target_root: Path, planned: Plan) -> Path:
    """Write the planned set, creating its folder. Never over a file: one that appears
    since the plan raises `FileExistsError`, and nothing is written."""
    if not planned.creates or planned.text is None:
        raise ValueError(f"the plan for {planned.declaration.name} creates no set")
    target = target_root / planned.path
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(planned.text)
    return target


def outcome_line(planned: Plan, *, dry_run: bool, failed: str | None = None) -> str:
    """What install says of the declared set, in one line. `failed` says why the write
    of a planned set failed, where it did."""
    declaration = planned.declaration
    if planned.inherited_by:
        return (
            f"  no project rule set created: {', '.join(planned.inherited_by)} inherits "
            f"{declaration.method_set} already (COR-017)"
        )
    if planned.creates and failed is None:
        verb = "would create" if dry_run else "created"
        return (
            f"  {verb} the project rule set {declaration.name} at {planned.path}, inheriting "
            f"{planned.pin} (COR-017): it is the project's own, to edit or remove"
        )
    why = failed or planned.blocked or f"{planned.path} could not be written"
    return (
        f"  warning: no project rule set created: {why}. A set of the project's own that "
        f"inherits {planned.pin or declaration.method_set} makes its rules bind (COR-051 "
        f"point 7). `pkit capabilities project-rule-set {declaration.capability}` shows the "
        f"set install declares"
    )


def to_json(capability: str, planned: Plan | None) -> str:
    """The reading document of `pkit capabilities project-rule-set <name> --json`."""
    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "capability": capability,
        "declared": planned is not None,
        "set": None,
        "path": None,
        "pin": None,
        "inherited_by": [],
        "creates": False,
        "blocked": None,
        "text": None,
    }
    if planned is not None:
        declaration = planned.declaration
        document.update(
            {
                "set": {
                    "name": declaration.name,
                    "title": declaration.title,
                    "inherits": declaration.method_set,
                    "scope": {"types": list(declaration.types)},
                },
                "path": planned.path,
                "pin": planned.pin,
                "inherited_by": list(planned.inherited_by),
                "creates": planned.creates,
                "blocked": planned.blocked,
                "text": planned.text,
            }
        )
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def render_human(capability: str, planned: Plan | None) -> str:
    """The text form of `pkit capabilities project-rule-set <name>`."""
    if planned is None:
        return f"{capability} declares no project rule set (COR-017).\n"
    declaration = planned.declaration
    lines = [
        f"{capability} declares the project rule set {declaration.name}, inheriting "
        f"{declaration.method_set} (COR-017).",
        f"  scope: types {', '.join(declaration.types)}",
    ]
    if planned.inherited_by:
        lines.append(f"  inherited by: {', '.join(planned.inherited_by)}, so install creates none")
    elif planned.creates:
        lines.append(f"  no set of the project's own inherits {declaration.method_set}:")
        lines.append(f"  install creates {planned.path}, pinned at {planned.pin}")
    else:
        lines.append(f"  install creates none: {planned.blocked}")
    return "\n".join(lines) + "\n"
