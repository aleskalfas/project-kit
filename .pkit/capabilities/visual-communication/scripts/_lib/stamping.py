"""Stamping a new piece: its first files, written from what a person chooses, so that its
first render writes the lock as for a piece written by hand (visual-communication DEC-002
points 3 and 5, DEC-029 point 4).

- **`piece.yaml`** (`_piece_text`): its binding, then the fields a person chooses, as
  `piece.md` of the `visual-author` skill has them chosen, and `state: draft`. It holds no
  lock: the first render writes it.
- **A content file for each language** (`_content`): its binding, then each field of the
  piece's top, empty. A field that holds the top's pages holds one page, in the top's first
  layout, with each of that layout's slots empty, the page's id being the layout's name. A
  field of a type it cannot leave empty is left out. The top is read from the newest version
  of its library the location holds that the installed capability reads, as a first lock
  takes it.
- **A brief** that holds its binding and says nothing yet. No command changes what a brief
  says (DEC-029 point 4), so the stamp gives it no word.
- **Refused before any write** (`plan`): a name taken or not a piece's name, a choice the
  piece's schema refuses, a library the location lacks, or holds no version of that the
  installed capability reads, a top its library lacks, and a file reached through a link.
- **Written as one change** (`write`): the new folder is staged whole beside its place, then
  moved in at once, so it never writes over a file and a write that fails leaves no part of
  it.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from _lib import libraries, records
from _lib import pipeline as pl
from _lib.config_text import scalar
from _lib.files import FORMAT, SCHEMA_FIELD, VERSION_FIELD, Change, schema_of, shape_problems
from _lib.fingerprint import BRIEF
from _lib.layout import PAGES
from _lib.names import split_use

#: The state a new piece starts in. A draft's lock moves at each render, so its first
#: render writes it (DEC-003 point 8).
STATE = "draft"

#: What an empty field holds, for each type a stamp leaves empty.
_EMPTY: dict[str, Callable[[], Any]] = {"object": dict, "string": str, "array": list}


@dataclass(frozen=True)
class Chosen:
    """What a person chooses of a new piece: the fields of its `piece.yaml`, each as
    `piece.md` has it chosen. `modes` holds the modes of each axis it names, in the order
    given."""

    top: str
    brand: str
    languages: tuple[str, ...]
    audience: str
    shown: str
    explains: bool
    exports: tuple[str, ...] = ()
    notations: tuple[str, ...] = ()
    modes: Mapping[str, Sequence[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class Planned:
    """A new piece checked and not yet written: where it lies, the version its top was read
    from, and each of its files by its name within its folder."""

    root: Path
    location: str
    name: str
    top: libraries.Library
    files: dict[str, bytes]

    @property
    def rel(self) -> str:
        """The new piece's folder, relative to the project root."""
        return f"{self.location}/{pl.PIECES}/{self.name}"

    @property
    def folder(self) -> Path:
        return self.root / self.rel


def plan(root: Path, location: str, name: str, chosen: Chosen) -> Planned:
    """The new piece `name` in `location`, from what `chosen` holds, every file it writes
    checked. Raises Refused, naming what stops it, so `write` refuses nothing."""
    target = pl.new_piece_folder(root, location, name)
    piece = _piece(chosen)
    _refuse_shape(piece, "piece", pl.PIECE_FILE)
    held = libraries.Held(root, location)
    library, component = split_use(chosen.top)
    top = _held(held, location, library)
    for each in (chosen.brand, *chosen.notations):
        _held(held, location, each)
    content = _content(_top(top, component, chosen.top))
    _refuse_shape(content, "content", pl.content_file(chosen.languages[0]))
    for written in (pl.PIECE_FILE, BRIEF, *map(pl.content_file, chosen.languages)):
        pl.writable(root, target / written)
    content_text = records.text(content, (), apart=False).encode("utf-8")
    files = {pl.PIECE_FILE: _piece_text(piece).encode("utf-8")}
    files.update({pl.content_file(language): content_text for language in chosen.languages})
    files[BRIEF] = records.text(_binding("brief"), (), apart=False).encode("utf-8")
    return Planned(root, location, name, top, files)


def write(planned: Planned, change: Change) -> None:
    """Write a planned piece as the next step of `change`, and take it: the new folder,
    whole. Raises WriteFailed where a write fails, every file then as it was before the run,
    or named."""
    change.add_folder(planned.folder, planned.files)
    change.commit()


def report(planned: Planned) -> list[str]:
    """What a stamp says, a line each: the files it wrote, and what to do next."""
    written = ", ".join(planned.files)
    return [
        f"stamped: `{planned.name}`, a draft, in {planned.rel}: {written}. Its content holds "
        f"the fields of its top, read from {planned.top.label}",
        f"fill its content and its brief, then run `pkit visual render {planned.name}`, which "
        f"writes its lock",
    ]


def _binding(kind: str) -> dict[str, Any]:
    """The fields that bind a file of `kind`, which open it."""
    return {SCHEMA_FIELD: schema_of(kind), VERSION_FIELD: FORMAT}


def _piece(chosen: Chosen) -> dict[str, Any]:
    """The value of the new piece's `piece.yaml`, its fields in the order `piece.md` shows
    them, those a person leaves out left out."""
    piece: dict[str, Any] = {**_binding("piece"), "top": chosen.top, "brand": chosen.brand}
    if chosen.notations:
        piece["notations"] = list(chosen.notations)
    piece.update(
        languages=list(chosen.languages),
        audience=chosen.audience,
        shown=chosen.shown,
        explains=chosen.explains,
        exports=list(chosen.exports),
        state=STATE,
    )
    if chosen.modes:
        piece["modes"] = {axis: list(modes) for axis, modes in chosen.modes.items()}
    return piece


def _piece_text(piece: Mapping[str, Any]) -> str:
    """`piece` as the text of its file: a line for each field, its schema's name plain, a
    list in flow, as `piece.md` writes one, and `modes` a block mapping of such lists."""
    lines = []
    for key, value in piece.items():
        if key == SCHEMA_FIELD:
            lines.append(f"{key}: {value}")
        elif isinstance(value, Mapping):
            lines.append(f"{key}:")
            lines.extend(f"  {scalar(axis)}: {_flow(modes)}" for axis, modes in value.items())
        else:
            lines.append(f"{key}: {_value(value)}")
    return "".join(f"{line}\n" for line in lines)


def _value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list):
        return _flow(value)
    return scalar(value)


def _flow(values: Sequence[str]) -> str:
    return "[" + ", ".join(scalar(value) for value in values) + "]"


def _refuse_shape(data: Mapping[str, Any], kind: str, name: str) -> None:
    """Raise Refused where the schema of `kind` refuses `data`, naming each problem as the
    file `name` would carry it."""
    problems = shape_problems(data, kind)
    if problems:
        raise pl.Refused(f"{name} would not hold its schema: {'; '.join(problems)}")


def _held(held: libraries.Held, location: str, library: str) -> libraries.Library:
    """The newest version of `library` the location holds that the installed capability
    reads. Raises Refused where it holds none, naming how to bring one."""
    found, unread = libraries.readable(held, library)
    if found:
        return found[0]
    if unread:
        raise pl.Refused(
            f"the location holds no version of `{library}` the installed capability reads: "
            f"{'; '.join(unread)}"
        )
    if library in libraries.shipped_names():
        bring = f"bring it with `pkit visual add {library}`"
    else:
        bring = f"put a version of it in {location}/{libraries.FOLDER}/ and list it"
    raise pl.Refused(
        f"the location holds no version of `{library}`: {bring}, or name a library it holds"
    )


def _top(library: libraries.Library, component: str, use: str) -> Mapping[str, Any]:
    """The top `use`, component `component` of `library`. Raises Refused where the version
    holds no such component, or it cannot be read."""
    data, why = pl.read_component(library.folder / pl.COMPONENTS / f"{component}.yaml")
    if why is not None:
        raise pl.Refused(f"the top `{use}` in {library.label} cannot be read: {why}")
    if data is None:
        raise pl.Refused(f"{library.label} holds no component `{component}`: name a top it holds")
    return data


def _content(top: Mapping[str, Any]) -> dict[str, Any]:
    """A content file holding each field of `top`, empty, its pages one page in the top's
    first layout."""
    content = _binding("content")
    fields = (top.get("fields") or {}).get("properties") or {}
    for name, schema in fields.items():
        if schema.get(PAGES) is True:
            content[name] = _pages(top)
        elif (empty := _empty(schema)) is not None:
            content[name] = empty()
    return content


def _pages(top: Mapping[str, Any]) -> list[dict[str, Any]]:
    """One page in the top's first layout, each of its slots empty; none where the top has
    no layout."""
    layouts = top.get("layouts") or {}
    if not layouts:
        return []
    layout = next(iter(layouts))
    page: dict[str, Any] = {"id": layout, "layout": layout}
    for slot, schema in (layouts[layout].get("slots") or {}).items():
        if isinstance(schema, Mapping) and (empty := _empty(schema)) is not None:
            page[slot] = empty()
    return [page]


def _empty(schema: Mapping[str, Any]) -> Callable[[], Any] | None:
    """What makes the empty value of a field of `schema`, or None where a stamp leaves the
    field out: its type is one a stamp does not leave empty, or a list of types, as a
    component's schema lets a field declare."""
    kind = schema.get("type")
    return _EMPTY.get(kind) if isinstance(kind, str) else None
