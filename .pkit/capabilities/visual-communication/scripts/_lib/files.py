"""A file of the capability's format: its binding, its shape, the nearest known key, and
writing one whole (DEC-002 points 3 and 4, DEC-003 point 1).

Each file of the format names its schema and the format number at its top, in the fields
by which the core binds a data file: `pkit_schema: visual-communication:<kind>` and
`schema_version: 1`. No path binds one. The core's data validation checks a bound file's
shape against its schema; the capability's check fails a file of the format whose binding
is missing or names another schema, and names the nearest known key where content holds
one no component declares.
"""

from __future__ import annotations

import contextlib
import difflib
import os
import stat
import tempfile
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from _lib.reading import read_yaml
from _lib.root import CAPABILITY, SHIPPED

#: The format number, shared by every schema of the capability (DEC-003 point 1).
FORMAT = 1

#: The capability's schemas, one pair for each kind of file.
SCHEMAS = SHIPPED / "schemas"

#: The kinds of file of format 1, each a schema of the capability.
KINDS = (
    "config",
    "piece",
    "content",
    "library",
    "component",
    "roles",
    "notation",
    "libraries",
    "produced-record",
    "code-record",
    "findings",
    "exports",
    "code",
)

SCHEMA_FIELD = "pkit_schema"
VERSION_FIELD = "schema_version"


class FileError(Exception):
    """A file of the format the capability cannot read as the kind asked for."""


def schema_of(kind: str) -> str:
    """The value of `pkit_schema` that binds a file of `kind`."""
    return f"{CAPABILITY}:{kind}"


def is_of_format(data: Any) -> bool:
    """Whether `data` names one of the capability's schemas, at whatever number."""
    return (
        isinstance(data, Mapping)
        and isinstance(data.get(SCHEMA_FIELD), str)
        and data[SCHEMA_FIELD].startswith(f"{CAPABILITY}:")
    )


def binding_problem(data: Any, kind: str) -> str | None:
    """Why `data` is not a file of `kind` at format 1, or None."""
    wanted = schema_of(kind)
    fix = f"`{SCHEMA_FIELD}: {wanted}` and `{VERSION_FIELD}: {FORMAT}` at its top"
    if not isinstance(data, Mapping):
        return f"is not a mapping, so it names no schema: write {fix}"
    named = data.get(SCHEMA_FIELD)
    if named is None:
        return f"names no schema: add {fix}"
    if named != wanted:
        return f"names the schema `{named}`, not `{wanted}`"
    number = data.get(VERSION_FIELD)
    if number is None:
        return f"names no format number: add `{VERSION_FIELD}: {FORMAT}`"
    if isinstance(number, bool) or number != FORMAT:
        return f"is at format {number!r}; the installed capability reads format {FORMAT}"
    return None


def without_binding(data: Mapping[str, Any]) -> dict[str, Any]:
    """`data` with the fields that bind it removed."""
    return {key: value for key, value in data.items() if key not in (SCHEMA_FIELD, VERSION_FIELD)}


def read_bound(path: Path, kind: str) -> dict[str, Any]:
    """The value of the file of `kind` at `path`. Raises FileError when it cannot be read
    or is not bound to `kind` at format 1; ReadError from reading passes through."""
    data = read_yaml(path)
    problem = binding_problem(data, kind)
    if problem is not None:
        raise FileError(f"{path}: {problem}")
    return dict(data)


def nearest(key: str, known: Iterable[str]) -> str | None:
    """The known key nearest to `key`, where one is near enough to be a likely slip."""
    found = difflib.get_close_matches(key, sorted(known), n=1, cutoff=0.6)
    return found[0] if found else None


def unknown_keys(data: Mapping[str, Any], known: Iterable[str]) -> list[tuple[str, str | None]]:
    """Each key of `data` that `known` does not hold, with the nearest known key or None."""
    known = tuple(known)
    return [(key, nearest(key, known)) for key in data if key not in known]


def shape_problems(data: Any, kind: str) -> list[str]:
    """What the schema of `kind` refuses in `data`, each `<JSON pointer>: <message>`;
    empty when it holds. Needs `jsonschema`, imported only here."""
    import json

    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012

    resources = []
    for companion in sorted(SCHEMAS.glob("*.schema.json")):
        contents = json.loads(companion.read_text(encoding="utf-8"))
        resource = Resource.from_contents(contents, default_specification=DRAFT202012)
        resources.append((contents.get("$id", companion.name), resource))
    registry = Registry().with_resources(resources)
    schema = json.loads((SCHEMAS / f"{kind}.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, registry=registry)
    problems = []
    for error in sorted(validator.iter_errors(data), key=lambda e: list(map(str, e.absolute_path))):
        pointer = "/" + "/".join(str(part) for part in error.absolute_path)
        problems.append(f"{pointer}: {error.message}")
    return problems


# --- writing ------------------------------------------------------------------------------------


def refuse_links(root: Path, target: Path) -> None:
    """Raise FileError when `target`, or a folder between it and `root`, is a link: a file
    written whole would replace the link it was reached by."""
    for path in (target, *target.parents):
        if path == root:
            return
        if path.is_symlink():
            raise FileError(
                f"{target.relative_to(root).as_posix()} is reached through the link "
                f"{path.relative_to(root).as_posix()}: put the file or folder itself in the "
                f"link's place"
            )


def write_whole(target: Path, data: bytes) -> None:
    """Write `data` to `target` whole or not at all: to a temporary file beside it, then
    moved over it. A file keeps its mode; a new one takes what the umask gives."""
    mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else 0o666 & ~_umask()
    handle, temporary = tempfile.mkstemp(
        dir=target.parent, prefix=f".{target.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, target)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporary)
        raise


def _umask() -> int:
    mask = os.umask(0)
    os.umask(mask)
    return mask
