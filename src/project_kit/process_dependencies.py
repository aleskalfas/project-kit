"""The generated `depends-on` list in package metadata (COR-053 point 4).

A capability's process definitions declare, on their states, the processes they
depend on (`depends_on`, COR-038). Its package metadata carries the same fact as
one list, `connections.extensions.depends-on`, so that a reader — and a plan for
a capability not yet installed — sees it without opening a definition, and so
the capability lifecycle can read the mandatory marks from package metadata
alone (COR-053 point 6). The definitions are the single source; the list is a
machine-written copy marked `generated: true`.

This module is that copy's whole life:

- `generated_entries` — what the definitions generate: one entry per distinct
  upstream and targeted interface version, sorted, carrying `process`, the
  `schema_version` the definition's `version` targets, and the `mandatory` mark
  when any declaring entry carries one (distinct reasons joined in declaration
  order). An entry not yet written (`pending`) counts as declared, so an
  authoring preview can tell whether its write would leave the list stale.
- `staleness` — whether the package's list says the same. A stale copy is a
  validation error (`package_validate`'s repository pass) naming the refresh
  command as the fix; the definition always wins. `package_staleness` reads the
  package file itself, for the authoring stamp that names the refresh after
  coupling (`pkit process couple`).
- `refresh` — rewrite the list from the definitions, round-tripping the rest of
  the package file untouched. It is an authoring-time operation run where the
  capability is authored: in an adopting project a kit-shipped package file is
  core-owned, and the command refuses there (`pkit capabilities refresh`).

The walk over a capability's definitions is shared with the one other package
check that reads them: an offered process point's `schema_version` against its
definition's `interface.version` (`offered_definition`, `interface_version`).

It reads the definitions' YAML directly and nothing else of them: it never
loads a definition through the engine and never resolves an upstream — whether
an upstream exists is the wiring resolver's question (`connections`).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import Any, cast

from ruamel.yaml import YAML

# The package file, relative to a capability's root.
PACKAGE_FILE = "package.yaml"

# Where the list sits in package metadata, and its two keys (the package schema,
# `$defs/depends-on`; COR-053 point 3 names the block, point 4 the mark).
CONNECTIONS_KEY = "connections"
EXTENSIONS_KEY = "extensions"
DEPENDS_ON_KEY = "depends-on"
GENERATED_KEY = "generated"
ENTRIES_KEY = "entries"
BLOCK_PATH = (CONNECTIONS_KEY, EXTENSIONS_KEY, DEPENDS_ON_KEY)

# The keys of one generated entry, and the definition keys each is copied from.
PROCESS_KEY = "process"  # ← `depends_on[].upstream`
VERSION_KEY = "schema_version"  # ← `depends_on[].version`
MANDATORY_KEY = "mandatory"  # ← `depends_on[].mandatory`
REASON_KEY = "reason"

# Where a capability's process definitions live, relative to its root: its
# `schemas/*.yaml` files carrying a top-level `process:` block (the process
# area README, "Binding a process").
SCHEMAS_DIR = "schemas"
PROCESS_BLOCK_KEY = "process"

# A definition's public contract and the version it carries (COR-036 as refined
# by COR-053 point 5).
INTERFACE_KEY = "interface"
INTERFACE_VERSION_KEY = "version"

# The separator of several reasons merged onto one generated mark.
REASON_SEPARATOR = "; "

_safe = YAML(typ="safe")


class RefreshError(Exception):
    """The package file cannot be refreshed: absent, unreadable, or not a mapping."""


def refresh_command(capability: str) -> str:
    """The command that regenerates `capability`'s list — named by the stale-copy
    error and by the coupling stamp, one spelling for both."""
    return f"pkit capabilities refresh {capability}"


@dataclass(frozen=True)
class Entry:
    """One `depends-on` entry, compared by what it says, not how it is written."""

    process: str
    version: int | None = None
    reason: str | None = None  # the mandatory mark's reason; None when not marked

    def as_yaml(self) -> dict[str, Any]:
        """The entry as the package file writes it."""
        out: dict[str, Any] = {PROCESS_KEY: self.process}
        if self.version is not None:
            out[VERSION_KEY] = self.version
        if self.reason is not None:
            out[MANDATORY_KEY] = {REASON_KEY: self.reason}
        return out

    def text(self) -> str:
        """`'<process>'`, with ` v<N>` and `(mandatory: <reason>)` when present."""
        version = f" v{self.version}" if self.version is not None else ""
        mark = f" (mandatory: {self.reason})" if self.reason is not None else ""
        return f"{self.process!r}{version}{mark}"


@dataclass(frozen=True)
class Staleness:
    """How a package's `depends-on` list differs from what its definitions generate."""

    pointer: str  # the list, or its nearest present ancestor when the list is absent
    generated: tuple[Entry, ...]
    listed: tuple[Entry, ...]

    @property
    def missing(self) -> tuple[Entry, ...]:
        """Generated by the definitions, absent from the list."""
        return tuple(e for e in self.generated if e not in self.listed)

    @property
    def extra(self) -> tuple[Entry, ...]:
        """In the list, generated by no definition."""
        return tuple(e for e in self.listed if e not in self.generated)

    def message(self, capability: str) -> str:
        """The validation error: what differs, and the command that fixes it."""
        differences: list[str] = []
        if self.missing:
            differences.append("missing " + ", ".join(e.text() for e in self.missing))
        if self.extra:
            differences.append(
                "declared by no definition " + ", ".join(e.text() for e in self.extra)
            )
        if not differences:
            differences.append(f"the list is not marked `{GENERATED_KEY}: true`")
        return (
            f"the generated `{DEPENDS_ON_KEY}` list is stale: the process definitions' "
            f"`depends_on` generate {len(self.generated)} entry(ies), the list holds "
            f"{len(self.listed)} — {'; '.join(differences)}. Regenerate it with "
            f"`{refresh_command(capability)}` where the capability is authored; "
            f"the definitions always win (COR-053 point 4)."
        )


@dataclass(frozen=True)
class RefreshResult:
    """What `refresh` wrote, or would write."""

    package_file: Path
    entries: tuple[Entry, ...]
    changed: bool


# --- what the definitions generate --------------------------------------------


def generated_entries(
    component_dir: Path, *, pending: Iterable[Mapping[Any, Any]] = ()
) -> tuple[Entry, ...]:
    """The `depends-on` entries the capability's process definitions generate.

    Every `depends_on` entry on every state of every definition under the
    capability's `schemas/`, reduced to one entry per distinct (upstream,
    targeted version) and sorted by them, so the list does not move when states
    or files are reordered. A connection is mandatory when any declaring entry
    marks it; several distinct reasons are joined in declaration order. A file
    that does not parse, or holds no `process:` block, generates nothing — the
    definitions check (`pkit validate`'s `process` member) reports it.

    `pending` are `depends_on` entries not yet written to any definition; they
    count as declared after every written one.
    """
    reasons: dict[tuple[str, int | None], list[str]] = {}
    for entry in chain(_declared_depends_on(component_dir), pending):
        upstream = entry.get("upstream")
        if not isinstance(upstream, str) or not upstream:
            continue  # the shape lint reports it
        key = (upstream, _version(entry.get("version")))
        found = reasons.setdefault(key, [])
        reason = _reason(entry.get(MANDATORY_KEY))
        if reason is not None and reason not in found:
            found.append(reason)
    return tuple(
        Entry(process, version, REASON_SEPARATOR.join(found) if found else None)
        for (process, version), found in sorted(reasons.items(), key=_entry_order)
    )


def _declared_depends_on(component_dir: Path) -> Iterable[Mapping[Any, Any]]:
    """Every `depends_on` entry the capability's definitions declare, in file,
    state and entry order."""
    for _path, process in process_definitions(component_dir):
        for state in _list(process.get("states")):
            state_block = _mapping(state)
            if state_block is None:
                continue
            for entry in _list(state_block.get("depends_on")):
                block = _mapping(entry)
                if block is not None:
                    yield block


# --- the capability's definitions -------------------------------------------------


def process_definitions(component_dir: Path) -> Iterator[tuple[Path, Mapping[Any, Any]]]:
    """Every definition under the capability's `schemas/`, as `(file, process
    block)`, in file order. A file that does not parse, or holds no `process:`
    mapping, is not a definition here — the definitions check reports it."""
    schemas = component_dir / SCHEMAS_DIR
    if not schemas.is_dir():
        return
    for path in sorted(schemas.glob("*.yaml")):
        try:
            document: Any = _safe.load(path.read_text(encoding="utf-8"))
        except Exception:  # unreadable, or ruamel's own hierarchy
            continue
        root = _mapping(document)
        process = _mapping(root.get(PROCESS_BLOCK_KEY)) if root is not None else None
        if process is not None:
            yield path, process


def offered_definition(
    component_dir: Path, process_id: str
) -> tuple[Path, Mapping[Any, Any]] | None:
    """The definition whose `id` is `process_id` — the one an offered process point
    names — as `(file, process block)`; None when none declares it. The file named
    after the id wins over another declaring the same id, the order the engine
    loads a definition in (`process.load_definition`)."""
    found = [
        (path, block)
        for path, block in process_definitions(component_dir)
        if block.get("id") == process_id
    ]
    for path, block in found:
        if path.stem == process_id:
            return path, block
    return found[0] if found else None


def interface_version(process: Mapping[Any, Any]) -> int | None:
    """The definition's `interface.version`; None when it declares none."""
    interface = _mapping(process.get(INTERFACE_KEY))
    return _version(interface.get(INTERFACE_VERSION_KEY)) if interface is not None else None


# --- what the package lists -----------------------------------------------------


def listed_entries(package: Mapping[Any, Any]) -> tuple[Entry, ...]:
    """The entries the package's `depends-on` list holds, as written; none when the
    list is absent. An entry without a `process` is the shape pass's error."""
    block = _block(package)
    if block is None:
        return ()
    out: list[Entry] = []
    for value in _list(block.get(ENTRIES_KEY)):
        entry = _mapping(value)
        if entry is None:
            continue
        process = entry.get(PROCESS_KEY)
        if isinstance(process, str) and process:
            out.append(
                Entry(process, _version(entry.get(VERSION_KEY)), _reason(entry.get(MANDATORY_KEY)))
            )
    return tuple(out)


def staleness(
    package: Mapping[Any, Any],
    component_dir: Path,
    *,
    pending: Iterable[Mapping[Any, Any]] = (),
) -> Staleness | None:
    """How the package's `depends-on` list differs from what the definitions under
    `component_dir` generate; None when it is fresh. An absent list and an empty
    one are the same list, and the order entries are written in does not count;
    a present list must carry `generated: true`. `pending` as `generated_entries`
    takes it."""
    generated = generated_entries(component_dir, pending=pending)
    listed = listed_entries(package)
    block = _block(package)
    marked = block is None or block.get(GENERATED_KEY) is True
    if marked and sorted(listed, key=_order) == list(generated):
        return None
    return Staleness(pointer=_pointer(package), generated=generated, listed=listed)


def package_staleness(
    component_dir: Path, *, pending: Iterable[Mapping[Any, Any]] = ()
) -> Staleness | None:
    """`staleness` of the capability's own package file, read from disk; None when
    the list is fresh, and None when the file is absent, does not parse or is not a
    mapping — the packages pass reports that, and a stale list cannot be told from
    a file that does not read."""
    try:
        document: Any = _safe.load((component_dir / PACKAGE_FILE).read_text(encoding="utf-8"))
    except Exception:  # absent, unreadable, or ruamel's own hierarchy
        return None
    package = _mapping(document)
    return staleness(package, component_dir, pending=pending) if package is not None else None


# --- refresh --------------------------------------------------------------------


def refresh(component_dir: Path, *, dry_run: bool = False) -> RefreshResult:
    """Rewrite `connections.extensions.depends-on` in the capability's package file
    from its process definitions, marked `generated: true`.

    Everything else in the file is round-tripped untouched — comments, key order,
    quoting. With nothing to generate the list is removed, and a `extensions` or
    `connections` block left empty by the removal goes with it. A fresh list is
    not rewritten. `dry_run` computes the same result and writes nothing.
    """
    package_file = component_dir / PACKAGE_FILE
    if not package_file.is_file():
        raise RefreshError(f"{package_file} does not exist.")
    rt = _round_trip_yaml()
    try:
        data: Any = rt.load(package_file.read_text(encoding="utf-8"))
    except Exception as exc:  # unreadable, or ruamel's own hierarchy
        raise RefreshError(f"{package_file} does not parse as YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise RefreshError(f"{package_file} is not a YAML mapping.")
    package = cast("dict[Any, Any]", data)
    entries = generated_entries(component_dir)
    if staleness(package, component_dir) is None:
        return RefreshResult(package_file, entries, changed=False)
    if entries:
        _set_block(package, entries)
    else:
        _drop_block(package)
    if not dry_run:
        with package_file.open("w", encoding="utf-8") as handle:
            rt.dump(package, handle)
    return RefreshResult(package_file, entries, changed=True)


def _set_block(package: dict[Any, Any], entries: tuple[Entry, ...]) -> None:
    """Write the list, creating `connections` and `extensions` when absent. A
    parent that is present but not a mapping is the shape pass's error; refresh
    replaces nothing it cannot read as a mapping."""
    parent = package
    for key in BLOCK_PATH[:-1]:
        child = parent.get(key)
        if child is None:
            child = parent[key] = {}
        if not isinstance(child, dict):
            raise RefreshError(
                f"`{'.'.join(BLOCK_PATH[: BLOCK_PATH.index(key) + 1])}` is not a mapping; "
                "fix the package file by hand, then refresh."
            )
        parent = cast("dict[Any, Any]", child)
    parent[DEPENDS_ON_KEY] = {
        GENERATED_KEY: True,
        ENTRIES_KEY: [entry.as_yaml() for entry in entries],
    }


def _drop_block(package: dict[Any, Any]) -> None:
    """Remove the list, then each ancestor the removal leaves empty."""
    chain: list[dict[Any, Any]] = [package]
    for key in BLOCK_PATH[:-1]:
        child = chain[-1].get(key)
        if not isinstance(child, dict):
            return
        chain.append(cast("dict[Any, Any]", child))
    chain[-1].pop(DEPENDS_ON_KEY, None)
    for parent, key in zip(reversed(chain[:-1]), reversed(BLOCK_PATH[:-1]), strict=True):
        if parent.get(key) == {}:
            parent.pop(key)


# --- helpers --------------------------------------------------------------------


def _block(package: Mapping[Any, Any]) -> Mapping[Any, Any] | None:
    """The `depends-on` mapping, or None when it (or a parent) is absent or not a mapping."""
    node: Mapping[Any, Any] | None = package
    for key in BLOCK_PATH:
        node = _mapping(node.get(key)) if node is not None else None
    return node


def _pointer(package: Mapping[Any, Any]) -> str:
    """JSON Pointer to the list, or to its deepest present ancestor."""
    pointer = ""
    node: Mapping[Any, Any] | None = package
    for key in BLOCK_PATH:
        if node is None or key not in node:
            break
        pointer += f"/{key}"
        node = _mapping(node.get(key))
    return pointer


def _round_trip_yaml() -> YAML:
    """Round-trip mode (comments, key order, quoting preserved), the house indent
    the shipped package files use, no line-folding."""
    rt = YAML(typ="rt")
    rt.preserve_quotes = True
    rt.indent(mapping=2, sequence=4, offset=2)
    rt.width = 100_000
    return rt


def _version(value: Any) -> int | None:
    """An interface version: an integer, never a boolean."""
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _reason(mark: Any) -> str | None:
    """A mark's reason; a mark without one is no mark (the shape lint refuses it)."""
    block = _mapping(mark)
    reason = block.get(REASON_KEY) if block is not None else None
    return reason if isinstance(reason, str) and reason else None


def _order(entry: Entry) -> tuple[str, int]:
    return (entry.process, entry.version or 0)


def _entry_order(item: tuple[tuple[str, int | None], list[str]]) -> tuple[str, int]:
    (process, version), _reasons = item
    return (process, version or 0)


def _mapping(value: Any) -> Mapping[Any, Any] | None:
    return cast("Mapping[Any, Any]", value) if isinstance(value, Mapping) else None


def _list(value: Any) -> list[Any]:
    return cast("list[Any]", value) if isinstance(value, list) else []
