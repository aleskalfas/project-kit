"""A published piece's current copy: the unnumbered files a page links to (DEC-006 point 7,
DEC-017 points 5, 7 and 8).

- **Where it lies.** In the folder `current-copy/` of the piece's folder, which no
  fingerprint reads (DEC-016 point 3). An export of a published piece writes it (`made`),
  and replaces the folder whole, so a file the new version does not write goes with it. A
  piece in any other state writes none, so a copy is always made while its piece is
  published (DEC-016, Implications), and one it holds already stays.
- **A file of the copy** (`file_of`). The name of its version's file with the number left
  out, and the bytes of that file, so the two keep one hash: the SHA-256 of the whole file.
  The accepted records leave what a name must hold and what the hash is taken of to the
  record of a copy's form, project-kit#2700 (DEC-019 point 5, DEC-017, Implications). So
  this function alone works out either, and another answer changes it alone.
- **The record.** `exports.yaml` names, under `current-copy`, the piece and the version
  that wrote the copy, and each file's path and hash (DEC-017 point 7). A path is read
  from the piece's folder, so a rename or a move of the location leaves it true. An entry
  is read one way (`recorded`), which refuses what the schema refuses, since an export in
  another state writes it back. The commands that read it run with no `jsonschema`, so
  the shape is held here, and the tests hold it to the schema.
- **Whose it is** (`own`). A piece's own where the record names that piece, or a piece the
  location no longer holds. So a rename keeps it, and a folder copied by hand brings none
  while the original stands. Every rule on a piece's current copy reads it so.
- **The lock it was made under** (`written_lock`) is read from the fingerprint of the
  version that wrote it, each library and version held to its shape, since a record may
  be written by hand. The release that version recorded lies beside it (`written_release`).
"""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from _lib import fingerprint
from _lib import pipeline as pl
from _lib.copies import PUBLISHED
from _lib.files import Change
from _lib.fingerprint import CURRENT_COPY
from _lib.libraries import Version
from _lib.names import LANGUAGE, NAME, is_name
from _lib.reading import is_sha256, sha256

#: The field of `exports.yaml` that names the current copy.
FIELD = "current-copy"

#: The fields of that entry, and no others (DEC-017 point 7).
_FIELDS = {"piece", "version", "files"}

#: A name and a language, as parts of a longer pattern.
_A_NAME = NAME.strip("^$")
_A_LANGUAGE = LANGUAGE.strip("^$")

#: A segment of a key, which names a mode: `<axis>.<mode>` (DEC-004 point 3).
_A_MODE = rf"{_A_NAME}\.{_A_NAME}"

#: A file's path in that entry, the pattern the schema of the record of exports holds.
PATH = (
    rf"^{CURRENT_COPY}/{_A_NAME}\.{_A_LANGUAGE}\.(default|{_A_MODE}(\+{_A_MODE})*)"
    r"((\.[1-9][0-9]*)?\.svg|\.pdf)$"
)

_PATH = re.compile(PATH)

#: The start of a version's file name: the piece, which holds no `.`, then the number.
_NUMBERED = re.compile(r"^([^.]+)\.v[1-9][0-9]*\.")


@dataclass(frozen=True)
class CopiedFile:
    """A file of a current copy: its name, and its hash."""

    name: str
    sha256: str


@dataclass(frozen=True)
class Copy:
    """A current copy an export writes: each file's bytes, by its name in the folder, and
    the entry that names the copy in the record of exports."""

    files: dict[str, bytes]
    entry: dict[str, Any]


def file_of(name: str, data: bytes) -> CopiedFile:
    """The file of a current copy that comes of a version's file `name`, which holds `data`:
    the name with the number left out, and the SHA-256 of the whole file. Raises ValueError
    for a name that carries no number. Nothing else works out either."""
    unnumbered, found = _NUMBERED.subn(r"\1.", name)
    if not found:
        raise ValueError(f"`{name}` carries no version's number")
    return CopiedFile(unnumbered, sha256(data))


def keeps(piece: pl.Piece) -> bool:
    """Whether the piece's state keeps a current copy."""
    return piece.state == PUBLISHED


def made(piece: pl.Piece, number: int, files: Mapping[str, bytes]) -> Copy | None:
    """The current copy the export `number` of the piece writes, from each file of the
    version by its name; None where its state keeps no copy."""
    if not keeps(piece):
        return None
    held: dict[str, bytes] = {}
    hashes: dict[str, str] = {}
    for name, data in files.items():
        copied = file_of(name, data)
        held[copied.name] = data
        hashes[f"{CURRENT_COPY}/{copied.name}"] = copied.sha256
    return Copy(held, {"piece": piece.name, "version": number, "files": hashes})


def writable(piece: pl.Piece, copy: Copy) -> None:
    """Raise Refused where `copy` could not be written: a file of it is reached through a
    link, or a file lies where its folder goes."""
    folder = piece.folder / CURRENT_COPY
    for name in copy.files:
        pl.writable(piece.root, folder / name)
    if folder.exists() and not folder.is_dir():
        raise pl.Refused(
            f"{piece.file(CURRENT_COPY)} is a file, and the piece's current copy lies in a "
            f"folder of that name: move the file"
        )


def write(piece: pl.Piece, copy: Copy, change: Change) -> None:
    """Add to `change`, as its next step, the folder that holds `copy`, in place of the
    whole folder where one stands."""
    folder = piece.folder / CURRENT_COPY
    place = change.replace_folder if folder.exists() else change.add_folder
    place(folder, copy.files)


def recorded(piece: pl.Piece, record: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """The entry of the record of exports `record` that names a current copy, whichever
    piece it names, or None where the record holds none. Raises Refused where the schema
    refuses the entry, so no export of the piece, in any state, writes it back."""
    if FIELD not in record:
        return None
    entry = record[FIELD]
    if not _is_entry(entry):
        raise pl.Refused(
            f"{piece.file(pl.EXPORTS_FILE)} keeps a `{FIELD}` that names no piece, version and "
            f"files as its schema asks: mend it before the next export"
        )
    return entry


def own(
    piece: pl.Piece, record: Mapping[str, Any], pieces: Collection[str] | None = None
) -> Mapping[str, Any] | None:
    """The entry of the record of exports `record` that names the piece's own current copy
    (DEC-017 point 7), or None: the record names no copy, or one of a piece the location
    still holds. `pieces` gives the pieces of the location, for a record read as it stood
    at a commit, and otherwise they are those it holds now. Every rule on a piece's current
    copy reads it. Raises Refused where the schema refuses the entry (`recorded`)."""
    entry = recorded(piece, record)
    if entry is None:
        return None
    named = entry["piece"]
    held = pl.piece_names(piece.root, piece.location) if pieces is None else pieces
    if named == piece.name or named not in held:
        return entry
    return None


def _is_entry(entry: Any) -> bool:
    """Whether `entry` takes the shape the schema of the record of exports gives a current
    copy."""
    return (
        isinstance(entry, Mapping)
        and entry.keys() == _FIELDS
        and is_name(entry["piece"])
        and _is_number(entry["version"])
        and _are_files(entry["files"])
    )


def _is_number(version: Any) -> bool:
    """Whether `version` is a version's number, from 1."""
    return isinstance(version, int) and not isinstance(version, bool) and version >= 1


def _are_files(held: Any) -> bool:
    """Whether `held` names at least one file of a copy, each by its path, with its hash."""
    return (
        isinstance(held, Mapping)
        and len(held) > 0
        and all(_PATH.match(path) and is_sha256(hashed) for path, hashed in held.items())
    )


def written_lock(entry: Mapping[str, Any], versions: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    """The lock of the version that wrote the current copy `entry` names, among the record's
    `versions`, read from its fingerprint (DEC-017 point 5). Raises
    fingerprint.UnreadableFingerprint where none can be read: no version of that number
    keeps one, or it names a library or a version of no such shape, which a lock never
    holds."""
    lock = fingerprint.lock_of(_writer(entry, versions).get("fingerprint"))
    for library, version in lock.items():
        if not is_name(library) or not _is_version(version):
            raise fingerprint.UnreadableFingerprint(
                f"the fingerprint names {library!r} at {version!r}, which is no library version"
            )
    return lock


def written_release(entry: Mapping[str, Any], versions: Sequence[Mapping[str, Any]]) -> str:
    """The capability's release the version that wrote the current copy `entry` names
    recorded, among the record's `versions`; empty where it keeps none."""
    kept = _writer(entry, versions).get("recorded")
    release = kept.get("capability") if isinstance(kept, Mapping) else None
    return release if isinstance(release, str) else ""


def _writer(entry: Mapping[str, Any], versions: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    """What the record's `versions` keep of the version that wrote the current copy `entry`
    names; nothing where none is of that number."""
    return next((kept for kept in versions if kept["version"] == entry["version"]), {})


def _is_version(text: str) -> bool:
    try:
        Version.parse(text)
    except ValueError:
        return False
    return True
