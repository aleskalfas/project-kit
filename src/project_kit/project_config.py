"""The backbone configuration file: forgiving reads, one consent-gated write (COR-048).

`.pkit/project/config.yaml` holds the project's declarations to the backbone
(COR-048 point 1). Two access paths, one each way:

- **Reading is forgiving** (point 4): `read_config` returns the file's mapping,
  or an empty mapping when the file is absent, empty, unparsable or not a
  mapping. A reader never fails because of the file; `pkit validate` is the
  strict side (`config_validate`).
- **Writing is consent-gated** (point 5): every writer of the file goes through
  `write_config`, which re-reads the file, applies the caller's mutation,
  validates the result against the backbone-shipped schema (refusing to write
  an invalid file), asks for consent once, and writes atomically while keeping
  the file's header (the editor directive stamped on a file the backbone
  creates, ADR-056). Consent is an interactive confirmation, an explicit
  `--yes`, or a refusal naming the exact command to run — a non-interactive run
  without `--yes` never writes silently.
"""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.error import YAMLError

from project_kit import backbone_schemas

#: The adopter-owned backbone project config, relative to the target root.
PROJECT_CONFIG_RELPATH = Path(".pkit") / "project" / "config.yaml"

#: The editor directive stamped at the top of a config file the backbone
#: creates, pointing at the backbone-shipped schema relative to the file
#: (`.pkit/schemas/backbone/config.schema.json`, ADR-056 point 1). The
#: validate pass (`config_validate`) is the strict reader; this is for editors.
EDITOR_DIRECTIVE = "# yaml-language-server: $schema=../schemas/backbone/config.schema.json"

# The schema kind under `.pkit/schemas/backbone/` (ADR-056 point 1).
CONFIG_SCHEMA_KIND = "config"


def project_config_path(target_root: Path) -> Path:
    return target_root / PROJECT_CONFIG_RELPATH


# --- reading -----------------------------------------------------------------


def read_config(target_root: Path) -> dict[str, Any]:
    """The configuration file's mapping, or `{}` for every zero-config state.

    Absent, empty, unreadable, unparsable or non-mapping files all yield the
    empty mapping (COR-048 points 3 and 4); the validate pass reports the
    broken ones separately.
    """
    path = project_config_path(target_root)
    if not path.is_file():
        return {}
    try:
        data = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    except (OSError, YAMLError):
        return {}
    return dict(data) if isinstance(data, Mapping) else {}


# --- consent -----------------------------------------------------------------


class ConsentRefused(click.ClickException):
    """Nobody could consent to the write: non-interactive without `--yes` (COR-048 point 5)."""


@dataclass(frozen=True)
class Consent:
    """How a write to the configuration file may be authorised.

    `yes` is the explicit confirmation flag; `interactive` says whether a
    prompt can be shown (`None` detects a terminal on stdin); `rerun` is the
    exact command the refusal names, so a non-interactive caller learns what
    to run rather than what went wrong.
    """

    yes: bool = False
    interactive: bool | None = None
    rerun: str = "the same command with --yes"

    def confirm(self, description: str) -> None:
        """Return when the write is consented to; raise otherwise.

        `description` names what would be written, for the prompt and the
        refusal. Declining the prompt aborts (`click.Abort`, non-zero), so a
        chained next step never runs as if the write had happened.
        """
        if self.yes:
            return
        interactive = stdin_is_tty() if self.interactive is None else self.interactive
        if not interactive:
            raise ConsentRefused(
                f"refusing to write {PROJECT_CONFIG_RELPATH.as_posix()} without consent: "
                f"stdin is not a terminal and --yes was not given (COR-048 point 5).\n"
                f"Nothing was written. To consent non-interactively, run:\n"
                f"  {self.rerun}"
            )
        click.confirm(
            f"{description} in {PROJECT_CONFIG_RELPATH.as_posix()}?", default=True, abort=True
        )


def stdin_is_tty() -> bool:
    """Whether stdin is an interactive terminal; an absent or closed stdin is not."""
    stdin = sys.stdin
    if stdin is None:
        return False
    try:
        return stdin.isatty()
    except (ValueError, OSError):  # ValueError: I/O operation on a closed file
        return False


# --- writing -----------------------------------------------------------------


class InvalidConfigWrite(click.ClickException):
    """The mutated configuration would not validate; nothing was written."""


class UnwritableConfig(click.ClickException):
    """The existing file cannot be preserved through a write (unparsable or not a mapping)."""


def write_config(
    target_root: Path,
    mutate: Callable[[CommentedMap], None],
    *,
    consent: Consent,
    description: str = "Write the configuration",
) -> Path:
    """The one write path for `.pkit/project/config.yaml` (COR-048 point 5).

    Re-reads the file round-trip (comments and key order kept), applies
    `mutate` to the mapping in place, validates the result against the
    backbone-shipped config schema (an invalid result is refused, nothing
    written; a tree without the schema is not validated — ADR-056 point 1),
    asks `consent`, then writes atomically. A file the write creates, or an
    empty one, opens with the editor directive; an existing file keeps its
    header. Returns the file's path.
    """
    path = project_config_path(target_root)
    yaml = YAML()  # round-trip: keep an existing file's other keys + comments
    data, fresh = _load_round_trip(path, yaml)
    mutate(data)
    _refuse_unless_valid(target_root, data)
    consent.confirm(description)

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        with tmp.open("w", encoding="utf-8") as stream:
            if fresh:
                stream.write(EDITOR_DIRECTIVE + "\n")
            yaml.dump(data, stream)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
    return path


def _load_round_trip(path: Path, yaml: YAML) -> tuple[CommentedMap, bool]:
    """The file as a round-trip mapping, and whether it needs the header stamped
    (absent or empty). An unparsable or non-mapping file is refused: a write
    that cannot keep the project's content is not one to make silently."""
    if not path.is_file():
        return CommentedMap(), True
    try:
        loaded = yaml.load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise UnwritableConfig(f"cannot read {PROJECT_CONFIG_RELPATH.as_posix()}: {exc}") from exc
    except YAMLError as exc:
        raise UnwritableConfig(
            f"{PROJECT_CONFIG_RELPATH.as_posix()} does not parse as YAML "
            f"({str(exc).splitlines()[0]}); fix it before writing to it "
            f"(`pkit validate` reports the details)."
        ) from exc
    if loaded is None:
        return CommentedMap(), True
    if not isinstance(loaded, CommentedMap):
        raise UnwritableConfig(
            f"{PROJECT_CONFIG_RELPATH.as_posix()} is not a mapping of keys to values; "
            f"fix it before writing to it."
        )
    return loaded, False


def _refuse_unless_valid(target_root: Path, data: Mapping[str, Any]) -> None:
    try:
        schema = load_config_schema(target_root)
    except backbone_schemas.BackboneSchemaMissing:
        return  # a tree recorded before the schema landed: nothing to check against
    errors = sorted(
        schema_validator(schema).iter_errors(_plain(data)),
        key=lambda e: (list(e.absolute_path), e.message),
    )
    if not errors:
        return
    lines = [
        f"refusing to write {PROJECT_CONFIG_RELPATH.as_posix()}: the result would not validate "
        f"against the backbone configuration schema. Nothing was written."
    ]
    for error in errors:
        pointer = "/".join(str(p) for p in error.absolute_path)
        where = f"/{pointer}" if pointer else "(file)"
        lines.append(f"  {where}: {error.message}")
    raise InvalidConfigWrite("\n".join(lines))


def load_config_schema(target_root: Path) -> dict[str, Any]:
    """The backbone configuration schema from the project's tree (ADR-056 point 1)."""
    return backbone_schemas.load_backbone_schema(target_root, CONFIG_SCHEMA_KIND)


def schema_validator(schema: Mapping[str, Any]) -> Draft202012Validator:
    """A validator whose `$ref`s resolve within the schema itself."""
    registry = Registry().with_resource(
        uri=schema.get("$id", f"{CONFIG_SCHEMA_KIND}.schema.json"),
        resource=Resource.from_contents(schema, default_specification=DRAFT202012),
    )
    return Draft202012Validator(schema, registry=registry)


def _plain(obj: Any) -> Any:
    """Round-trip containers as plain dicts/lists with text keys, as JSON Schema sees them."""
    if isinstance(obj, Mapping):
        return {str(k): _plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_plain(x) for x in obj]
    return obj


# --- `pkit config set` -------------------------------------------------------

#: The block owned by the project's own records (COR-048 point 2): the backbone
#: never writes into it, so the configuration command refuses it.
PROJECT_BLOCK = "project"


class UnknownConfigKey(click.ClickException):
    """The dotted key names nothing the schema knows, or something it cannot set."""


@dataclass(frozen=True)
class ResolvedKey:
    """A dotted key resolved against the schema to a settable scalar leaf."""

    segments: tuple[str, ...]
    leaf: Mapping[str, Any]  # the leaf's schema, `$ref`s followed

    @property
    def dotted(self) -> str:
        return ".".join(self.segments)


def resolve_key(schema: Mapping[str, Any], dotted: str) -> ResolvedKey:
    """Walk `dotted` through the schema's `properties` / `patternProperties`.

    Refuses an empty segment, the reserved `project` block and anything under
    it, an unknown key (naming the nearest known one), and a key whose leaf is a
    mapping or a list — those are edited in the file, not set from a command.
    """
    segments = tuple(dotted.split("."))
    if not dotted or any(not s for s in segments):
        raise UnknownConfigKey(f"key {dotted!r} is not a dotted path of non-empty segments.")
    if segments[0] == PROJECT_BLOCK:
        raise UnknownConfigKey(
            f"key {dotted!r} is under the reserved `{PROJECT_BLOCK}` block, which the project's "
            f"own records own (COR-048 point 2); the backbone never writes it. Edit the file "
            f"directly."
        )
    node: Mapping[str, Any] = _deref(schema, schema)
    for depth, segment in enumerate(segments):
        properties = node.get("properties") or {}
        patterns = node.get("patternProperties") or {}
        if segment in properties:
            child = properties[segment]
        else:
            matched = [p for p in patterns if re.search(p, segment)]
            if not matched:
                where = ".".join(segments[:depth]) or "the top level"
                if properties:
                    reason = backbone_schemas.render_unknown_key(segment, tuple(properties))
                else:
                    reason = f"key {segment!r} does not match the address form this block expects."
                raise UnknownConfigKey(f"at {where}: {reason}")
            child = patterns[matched[0]]
        node = _deref(schema, child)
    kind = node.get("type")
    if kind in ("object", "array") or "properties" in node or "items" in node:
        raise UnknownConfigKey(
            f"key {dotted!r} holds {'a list' if kind == 'array' else 'a mapping'}, not a single "
            f"value; `config set` sets scalars only. Edit the file directly "
            f"({PROJECT_CONFIG_RELPATH.as_posix()})."
        )
    return ResolvedKey(segments=segments, leaf=node)


def coerce_value(key: ResolvedKey, raw: str) -> Any:
    """Turn the command-line text into the leaf's declared type; the schema
    validation in `write_config` then judges enum, pattern and length."""
    kind = key.leaf.get("type", "string")
    if kind == "integer":
        try:
            return int(raw)
        except ValueError:
            raise UnknownConfigKey(f"key {key.dotted!r} takes an integer, not {raw!r}.") from None
    if kind == "number":
        try:
            return float(raw)
        except ValueError:
            raise UnknownConfigKey(f"key {key.dotted!r} takes a number, not {raw!r}.") from None
    if kind == "boolean":
        lowered = raw.strip().lower()
        if lowered in ("true", "yes", "on", "1"):
            return True
        if lowered in ("false", "no", "off", "0"):
            return False
        raise UnknownConfigKey(f"key {key.dotted!r} takes true or false, not {raw!r}.")
    return raw


def set_value(data: CommentedMap, key: ResolvedKey, value: Any) -> None:
    """Assign `value` at `key`, creating intermediate mappings; replaces a
    non-mapping intermediate (the schema pass would refuse that state anyway)."""
    node: Any = data
    for segment in key.segments[:-1]:
        child = node.get(segment)
        if not isinstance(child, Mapping):
            child = CommentedMap()
            node[segment] = child
        node = child
    node[key.segments[-1]] = value


def _deref(root: Mapping[str, Any], node: Mapping[str, Any]) -> Mapping[str, Any]:
    """Follow a local `$ref` (`#/$defs/...`) to its target, merging sibling keys."""
    seen = 0
    while "$ref" in node and seen < 16:
        ref = str(node["$ref"])
        if not ref.startswith("#/"):
            break
        target: Any = root
        for token in ref[2:].split("/"):
            token = token.replace("~1", "/").replace("~0", "~")
            target = target[token] if isinstance(target, Mapping) else None
            if target is None:
                return node
        merged = dict(target)
        merged.update({k: v for k, v in node.items() if k != "$ref"})
        node = merged
        seen += 1
    return node
