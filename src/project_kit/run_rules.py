"""The rules of an agent run: read, filled in and projected (ADR-066 point 5).

A capability whose command starts agents through the adapter's runner declares,
for each such command, the rules of the runs it starts, in a file of its own:
`.pkit/capabilities/<capability>/permissions/runs.yaml`, shaped by
`.pkit/schemas/permission-runs.schema.json`. No session's model composes that
file. This module is how the backbone reads it, for one run:

- **At the pinned commit.** Every read is from the root it is given, which the
  run command makes the run's clone. The file, its schema, the session
  catalog and model whose denies come along, and the shared decision core that
  projects them are all the commit's (ADR-066 point 3).
- **Filled in.** `{working-copy}` and `{workspace}` become the run's folders.
  `kit: reading` becomes the backbone's reading commands (`READING_COMMANDS`),
  and `kit: queries` each command another installed capability declares a
  query, as `pkit <its name or alias> <command>`, the declaring capability left
  out.
- **Projected through the shared decision core.** `.pkit/permissions/
  projection.py`'s `project_run` turns the rules, and the session model's
  denies that bind on the run's agent, into the forms a runner renders as native
  rules, or refuses the run with why.

`forms` says, in words for a brief, which command forms the rules allow, the
run's folders as the brief's markers (`MARKERS`), so a brief names no form the
rules refuse (DEC-056 point 5). `pkit agents rules` prints all of it.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from ruamel.yaml import YAML

#: Where a capability declares the rules of its runs, from its own folder.
RULES_FILE = Path("permissions") / "runs.yaml"
#: The schema that shapes it, from the root.
SCHEMA_FILE = Path(".pkit") / "schemas" / "permission-runs.schema.json"

#: The run's folders, as the rules write them, and as a brief names them: the
#: backbone's run command replaces each marker with the folder's path.
FOLDERS = ("{working-copy}", "{workspace}")
MARKERS = {
    "{working-copy}": "{{pkit:working-copy}}",
    "{workspace}": "{{pkit:workspace}}",
}

#: The backbone's reading commands (DEC-056 point 5): each writes nothing, and a
#: run may call it as `pkit <command>` with any arguments. A command that
#: writes, or one whose words a reading one starts with, is never listed.
READING_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("friction", "check"),
    ("friction", "debt"),
    ("friction", "explain"),
    ("friction", "artefacts"),
    ("friction", "since"),
    ("connections", "resolve"),
    ("connections", "graph"),
    ("connections", "providers"),
    ("decisions", "validate"),
    ("decisions", "check-diff"),
    ("repository", "base"),
    ("rule-sets", "reach"),
    ("rule-sets", "altered"),
    ("refs", "lookup"),
    ("refs", "show"),
    ("refs", "who-references"),
    ("refs", "rot"),
    ("status",),
    ("validate",),
)

#: What a capability's name looks like, and a command's.
_NAME = re.compile(r"[a-z][a-z0-9-]*")

_yaml: Any = YAML(typ="safe")


@dataclass(frozen=True)
class Query:
    """A command another capability declares a query: the words that run it,
    and whether its work starts `uv` (ADR-066 point 6)."""

    words: tuple[str, ...]
    starts_uv: bool


@dataclass(frozen=True)
class RunProjection:
    """One run's rules, projected (plan I4): the allow list and the denies in a
    runner's forms, the allowed command prefixes whose work starts `uv`, the
    forms a brief names, and how each deny is held."""

    allow: tuple[dict[str, Any], ...]
    deny: tuple[dict[str, Any], ...]
    excluded_candidates: tuple[tuple[str, ...], ...]
    forms: tuple[str, ...]
    held: tuple[dict[str, str], ...] = field(default=())


@dataclass(frozen=True)
class RunRules:
    """A run's rules as one capability declares them, read but not filled in."""

    capability: str
    command: str
    description: str
    rules: tuple[dict[str, Any], ...]
    privileges: Mapping[str, Any]  # scoped `<capability>:<id>` → entry, as written


def _mapping(value: Any) -> dict[str, Any]:
    """`value` as a mapping with text keys, or an empty one."""
    if not isinstance(value, Mapping):
        return {}
    return {str(key): item for key, item in cast("Mapping[Any, Any]", value).items()}


def _items(value: Any) -> list[Any]:
    """`value` as a list, or an empty one."""
    return list(cast("list[Any]", value)) if isinstance(value, list) else []


def split(rules_of: str) -> tuple[str, str] | None:
    """`<capability>:<command>` as its two names, or None when it is not that."""
    capability, colon, command = rules_of.partition(":")
    if not colon or not _NAME.fullmatch(capability) or not _NAME.fullmatch(command):
        return None
    return capability, command


def read(root: Path, rules_of: str) -> RunRules | str:
    """The rules of the run `rules_of` names, read at `root`, or why there are
    none to read. The file is checked against its schema: a run's rules that do
    not hold their shape are no rules to start a run under."""
    named = split(rules_of)
    if named is None:
        return f"{rules_of!r} names no run: write it `<capability>:<command>`"
    capability, command = named
    path = root / ".pkit" / "capabilities" / capability / RULES_FILE
    shown = f".pkit/capabilities/{capability}/{RULES_FILE.as_posix()}"
    if not path.is_file():
        return f"{capability} declares no rules of agent runs ({shown} does not exist)"
    schema_path = root / SCHEMA_FILE
    if not schema_path.is_file():
        return (
            f"{SCHEMA_FILE.as_posix()} does not exist, so the rules of agent runs cannot be "
            "checked: upgrade the backbone"
        )
    try:
        document: Any = _yaml.load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # ruamel's own hierarchy, or the file cannot be read
        return f"{shown} cannot be read: {exc}"
    problem = _shape_problem(document, schema_path)
    if problem is not None:
        return f"{shown} does not hold its shape: {problem}"
    run = _mapping(_mapping(_mapping(document).get("runs")).get(command))
    if not run:
        return f"{shown} declares no run of `{command}`"
    privileges = {
        f"{capability}:{pid}": entry
        for pid, entry in _mapping(_mapping(document).get("privileges")).items()
    }
    return RunRules(
        capability=capability,
        command=command,
        description=" ".join(str(run.get("description") or "").split()),
        rules=tuple(_mapping(rule) for rule in _items(run.get("rules"))),
        privileges=privileges,
    )


def _shape_problem(document: Any, schema_path: Path) -> str | None:
    """Why `document` fails the schema at `schema_path`, or None."""
    import json

    import jsonschema

    try:
        schema: Any = json.loads(schema_path.read_text(encoding="utf-8"))
        validator: Any = jsonschema.Draft202012Validator(schema)
    except (OSError, ValueError, jsonschema.SchemaError) as exc:
        return f"its schema cannot be read ({exc})"
    errors: list[Any] = sorted(
        validator.iter_errors(document), key=lambda error: list(error.absolute_path)
    )
    if not errors:
        return None
    first = errors[0]
    where = "/".join(str(part) for part in first.absolute_path) or "(the document)"
    return f"{where}: {first.message}"


# --- filling in --------------------------------------------------------------


def reading_rules() -> list[dict[str, Any]]:
    """The backbone's reading commands as shell recognizers."""
    return [{"cmd": "pkit", "args": list(words)} for words in READING_COMMANDS]


def queries(root: Path, *, leaving_out: str) -> list[Query]:
    """Each command an installed capability other than `leaving_out` declares a
    query (`query-contract: true`), once for its name and once for each alias
    that reaches it, as the dispatcher binds them."""
    from project_kit import command_runner, dispatcher

    static = dispatcher.static_command_names()
    table = dispatcher.installed_alias_table(root, static)
    found: list[Query] = []
    for capability in dispatcher.namespace_capabilities(root):
        if capability.name == leaving_out:
            continue
        names = [capability.name] if capability.name not in static else []
        names += [alias for alias, owner in table.bound.items() if owner == capability.name]
        leaves = command_runner.commands_of(capability.cap_dir, capability.commands)
        for tokens, leaf in leaves.items():
            if leaf.entry.get("query-contract") is not True:
                continue
            starts_uv = _starts_uv(leaf.script)
            found += [Query((name, *tokens), starts_uv) for name in names]
    return found


def _starts_uv(script: Path) -> bool:
    """Whether a script's first line runs it through `uv`."""
    try:
        with script.open(encoding="utf-8", errors="replace") as handle:
            first = handle.readline()
    except OSError:
        return False
    return first.startswith("#!") and re.search(r"\buv\b", first) is not None


def filled(
    rules: RunRules,
    catalog: Mapping[str, Any],
    queries_found: Sequence[Query],
    folders: Mapping[str, str],
) -> dict[str, Any]:
    """Every privilege a run's rules may name, with `kit` expanded and the
    run's folders filled in: the run's file's, scoped, and the session
    catalog's."""
    privileges: dict[str, Any] = dict(catalog)
    for pid, raw in rules.privileges.items():
        entry = _mapping(raw)
        recognize = _mapping(entry.get("recognize"))
        kit = recognize.pop("kit", None)
        bash = _items(recognize.get("bash"))
        if kit == "reading":
            recognize["bash"] = [*bash, *reading_rules()]
        elif kit == "queries":
            recognize["bash"] = [
                *bash,
                *({"cmd": "pkit", "args": list(q.words)} for q in queries_found),
            ]
        privileges[pid] = {**entry, "recognize": _fill(recognize, folders)}
    return privileges


def _fill(value: Any, folders: Mapping[str, str]) -> Any:
    """`value` with each run folder replaced, wherever a string is exactly one."""
    if isinstance(value, str):
        return folders.get(value, value)
    if isinstance(value, list):
        return [_fill(item, folders) for item in _items(value)]
    if isinstance(value, Mapping):
        return {key: _fill(item, folders) for key, item in _mapping(value).items()}
    return value


def model_denies(root: Path, agent: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """The session catalog at `root`, and the session model's denies that bind
    on `agent`: those for every agent, the guardrails among them, and the
    agent's own (ADR-066 point 3)."""
    from project_kit import permissions

    decide = permissions.decision_core(root)
    catalog: Any = decide.load_catalog(str(root))
    model: Any = decide.load_model(str(root), catalog)
    subjects = {"all", f"agent:{agent}"}
    denies = [
        grant
        for grant in (_mapping(item) for item in _items(_mapping(model).get("grants")))
        if grant.get("effect", "allow") == "deny" and grant.get("subject") in subjects
    ]
    return _mapping(_mapping(catalog).get("privileges")), denies


def _catalog_only(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """The session catalog at `root`, and no denies of the model's."""
    from project_kit import permissions

    catalog: Any = permissions.decision_core(root).load_catalog(str(root))
    return _mapping(_mapping(catalog).get("privileges")), []


# --- the projection ----------------------------------------------------------


def project_run(
    root: Path, rules_of: str, agent: str, *, working_copy: Path, workspace: Path
) -> RunProjection | str:
    """The run's rules, read at `root`, filled in with the run's folders and
    projected, or why the run is refused (plan I4)."""
    folders = {"{working-copy}": str(working_copy), "{workspace}": str(workspace)}
    return _projected(root, rules_of, agent, folders)


def view(root: Path, rules_of: str, agent: str = "") -> RunProjection | str:
    """The run's rules as `project_run` gives them, each folder named by the
    brief's marker for it: what `pkit agents rules` shows."""
    return _projected(root, rules_of, agent, dict(MARKERS))


def _projected(
    root: Path, rules_of: str, agent: str, folders: Mapping[str, str]
) -> RunProjection | str:
    rules = read(root, rules_of)
    if isinstance(rules, str):
        return rules
    from project_kit import permissions

    try:
        catalog, denies = model_denies(root, agent) if agent else _catalog_only(root)
        projection = permissions.projection_core(root)
    except permissions.PermissionsError as exc:
        return f"the permission core cannot be read: {exc}"
    found = queries(root, leaving_out=rules.capability)
    privileges = filled(rules, catalog, found, folders)
    projected = _mapping(projection.project_run(privileges, list(rules.rules), denies))
    if projected.get("refused"):
        return str(projected["refused"])
    allow = tuple(_mapping(rule) for rule in _items(projected.get("allow")))
    candidates = tuple(("pkit", *q.words) for q in found if q.starts_uv)
    allowed_commands = {
        tuple(str(token) for token in _items(rule.get("command"))) for rule in allow
    }
    return RunProjection(
        allow=allow,
        deny=tuple(_mapping(rule) for rule in _items(projected.get("deny"))),
        excluded_candidates=tuple(c for c in candidates if c in allowed_commands),
        forms=tuple(forms(allow, folders)),
        held=tuple(
            {str(k): str(v) for k, v in _mapping(held).items()}
            for held in _items(projected.get("held"))
        ),
    )


def forms(allow: Sequence[Mapping[str, Any]], folders: Mapping[str, str]) -> list[str]:
    """The forms the allow list allows, in words a brief names: each folder by
    the brief's marker, so the frame names no path the run did not make."""
    markers = {path: MARKERS[name] for name, path in folders.items()}
    lines: list[str] = []
    by_folder: dict[str, list[str]] = {}
    for rule in allow:
        folder = rule.get("folder")
        if isinstance(folder, str):
            by_folder.setdefault(markers.get(folder, folder), []).append(str(rule.get("tool")))
    for folder, tools in by_folder.items():
        lines.append(f"{_joined(tools)} on files in `{folder}`")
    for rule in allow:
        command = _items(rule.get("command"))
        if command:
            words = [markers.get(str(token), str(token)) for token in command]
            lines.append(f"`{' '.join(words)} …`")
        elif "folder" not in rule:
            lines.append(f"{rule.get('tool')}, anywhere")
    return lines


def _joined(parts: Sequence[str]) -> str:
    if len(parts) <= 1:
        return "".join(parts)
    return f"{', '.join(parts[:-1])} and {parts[-1]}"


# --- what the overview shows -------------------------------------------------


@dataclass(frozen=True)
class DeclaredRun:
    """One run an installed capability declares rules for."""

    capability: str
    command: str
    description: str
    rules: tuple[dict[str, Any], ...]
    problem: str = ""


def declared_runs(root: Path) -> list[DeclaredRun]:
    """Every run each installed capability declares rules for, in manifest
    order, as the permissions overview lists them (ADR-066 point 5, "Shown,
    not hidden")."""
    from project_kit.manifest import read_backbone_manifest

    try:
        backbone = read_backbone_manifest(root)
    except Exception:  # a manifest the views cannot read: they list no runs
        return []
    if backbone is None:
        return []
    out: list[DeclaredRun] = []
    for entry in backbone.components:
        if entry.kind != "capability":
            continue
        path = root / ".pkit" / "capabilities" / entry.name / RULES_FILE
        if not path.is_file():
            continue
        try:
            document: Any = _yaml.load(path.read_text(encoding="utf-8"))
        except Exception as exc:  # ruamel's own hierarchy, or unreadable
            out.append(DeclaredRun(entry.name, "", "", (), problem=f"cannot be read: {exc}"))
            continue
        for command, raw in _mapping(_mapping(document).get("runs")).items():
            run = _mapping(raw)
            if not run:
                continue
            read_back = read(root, f"{entry.name}:{command}")
            out.append(
                DeclaredRun(
                    capability=entry.name,
                    command=command,
                    description=" ".join(str(run.get("description") or "").split()),
                    rules=tuple(_mapping(rule) for rule in _items(run.get("rules"))),
                    problem=read_back if isinstance(read_back, str) else "",
                )
            )
    return out
