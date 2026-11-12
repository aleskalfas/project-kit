"""A published piece's current copy: the unnumbered files a page links to (DEC-006 point 7,
DEC-017 points 5, 7 and 8).

- **Where it lies.** In the folder `current-copy/` of the piece's folder, which no
  fingerprint reads (DEC-016 point 3), or at the place the piece names (`copy-place`). An
  export of a published piece writes it (`made`), and in the piece's folder replaces the
  folder whole, so a file the new version does not write goes with it. A piece in any other
  state writes none, so a copy is always made while its piece is published (DEC-016,
  Implications), and one it holds already stays.
- **A place** (`writable`) is a rule on where a command may write, and a plain path: this
  module reads no configuration of the documentation, and does not judge whether it suits
  a page. It lies inside the repository where version control keeps it, outside the location
  and the methodology's own folder, and no path through a link reaches it (DEC-017 point 8).
  An export writes over only a file of the piece's own copy, with the hash the record keeps,
  and any other file at a path it writes refuses the run.
- **Left behind** (`left_behind`). No export removes a file at a place, or one in the
  piece's folder once the piece names a place: it names each file of the last copy it did
  not write again, and a person removes it (DEC-017 point 7).
- **A file of the copy** (`file_of`). The name of its version's file with the number left
  out, in every format, and the bytes of that file, so the two keep one hash (`hash_of`):
  the SHA-256 of the whole file, with every mode a switching file holds (DEC-018 points 2
  and 3). These functions alone work out either.
- **The record.** `exports.yaml` names, under `current-copy`, the piece and the version
  that wrote the copy, and each file's path and hash (DEC-017 point 7). A path in the
  piece's folder is read from that folder, so a rename or a move of the location leaves it
  true, and a path at a place from the repository's root (`rooted`). A place of the folder's
  own name is refused, so the two never read alike. An entry is read one way (`recorded`),
  which refuses what the schema refuses, since an export in another state writes it back.
  The commands that read it run with no `jsonschema`, so the shape is held here, and the
  tests hold it to the schema.
- **Whose it is** (`own`). A piece's own where the record names that piece, or a piece the
  location no longer holds. So a rename keeps it, and a folder copied by hand brings none
  while the original stands. Every rule on a piece's current copy reads it so.
- **The lock it was made under** (`written_lock`) is read from the fingerprint of the
  version that wrote it, as any version's is (`version_lock`), each library and version
  held to its shape, since a record may be written by hand. The release that version
  recorded lies beside it (`written_release`), and so does each number or date it let
  through (`written_let_through`, DEC-016 point 6), and each element of a switching file it
  let through (`written_differing`, DEC-018 point 1).
"""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _lib import fingerprint
from _lib import location as loc
from _lib import pipeline as pl
from _lib.copies import PUBLISHED
from _lib.files import Change
from _lib.fingerprint import COPY_PLACE, CURRENT_COPY
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

#: The folder a file of that entry lies in, as the schemas' `repository-path` holds a path:
#: `current-copy`, or the place the piece names.
_A_FOLDER = r"[^/.\\][^/\\]*(/[^/.\\][^/\\]*)*"

#: A file's path in that entry, the pattern the schema of the record of exports holds.
PATH = (
    rf"^{_A_FOLDER}/{_A_NAME}\.{_A_LANGUAGE}\.(default|{_A_MODE}(\+{_A_MODE})*)"
    r"((\.[1-9][0-9]*)?\.svg|\.pdf|\.html)$"
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
    the name with the number left out, and its hash (`hash_of`). Raises ValueError for a name
    that carries no number. Nothing else works out a name."""
    unnumbered, found = _NUMBERED.subn(r"\1.", name)
    if not found:
        raise ValueError(f"`{name}` carries no version's number")
    return CopiedFile(unnumbered, hash_of(data))


def hash_of(data: bytes) -> str:
    """The hash of a file of a current copy that holds `data`: the SHA-256 of the whole file.
    Nothing else works it out."""
    return sha256(data)


def keeps(piece: pl.Piece) -> bool:
    """Whether the piece's state keeps a current copy."""
    return piece.state == PUBLISHED


def made(piece: pl.Piece, number: int, files: Mapping[str, bytes]) -> Copy | None:
    """The current copy the export `number` of the piece writes, from each file of the
    version by its name; None where its state keeps no copy."""
    if not keeps(piece):
        return None
    folder = CURRENT_COPY if piece.copy_place is None else piece.copy_place
    held: dict[str, bytes] = {}
    hashes: dict[str, str] = {}
    for name, data in files.items():
        copied = file_of(name, data)
        held[copied.name] = data
        hashes[f"{folder}/{copied.name}"] = copied.sha256
    return Copy(held, {"piece": piece.name, "version": number, "files": hashes})


def rooted(piece: pl.Piece, path: str) -> str:
    """The path from the repository's root of the file a record names by `path`."""
    return piece.file(path) if _in_folder(path) else path


def _in_folder(path: str) -> bool:
    """Whether a record's `path` lies in the piece's folder, and is read from it."""
    return path.rpartition("/")[0] == CURRENT_COPY


def left_behind(
    piece: pl.Piece, own_copy: Mapping[str, Any] | None, copy: Copy | None
) -> list[str]:
    """Each file of `own_copy`, the piece's own copy before the run, that an export writing
    `copy` leaves where it lies, by its path from the repository's root. A folder replaced
    whole takes its files along, and a file a person removed lies nowhere to name."""
    if own_copy is None or copy is None:
        return []
    written = {rooted(piece, path) for path in copy.entry["files"]}
    replaced = piece.copy_place is None
    stayed = (path for path in own_copy["files"] if not (replaced and _in_folder(path)))
    kept = (rooted(piece, path) for path in stayed)
    return [path for path in kept if path not in written and (piece.root / path).exists()]


def writable(piece: pl.Piece, copy: Copy, own_copy: Mapping[str, Any] | None) -> None:
    """Raise Refused where `copy` could not be written: a file of it is reached through a
    link, a file lies where its folder goes, or it could not lie at the place the piece
    names, where `own_copy` is the piece's own copy before the run."""
    if piece.copy_place is not None:
        _writable_at_place(piece, piece.copy_place, copy, own_copy)
        return
    folder = piece.folder / CURRENT_COPY
    for name in copy.files:
        pl.writable(piece.root, folder / name)
    if folder.exists() and not folder.is_dir():
        raise pl.Refused(
            f"{piece.file(CURRENT_COPY)} is a file, and the piece's current copy lies in a "
            f"folder of that name: move the file"
        )


def _writable_at_place(
    piece: pl.Piece, place: str, copy: Copy, own_copy: Mapping[str, Any] | None
) -> None:
    """Raise Refused, naming what stops it, where the piece's current copy cannot lie at
    `place`, or a path of `copy` holds anything but a file of `own_copy` with the hash the
    record keeps (DEC-017 point 8)."""
    said = f"{piece.file(pl.PIECE_FILE)}: `{COPY_PLACE}: {place}`"
    found = _place_problem(piece, place)
    if found is not None:
        raise pl.Refused(f"{said} {found}")
    paths = list(copy.entry["files"])
    for path in paths:
        pl.writable(piece.root, piece.root / path)
    found = _file_in_the_way(piece.root, place) or _unkept(piece.root, paths)
    if found is not None:
        raise pl.Refused(f"{said} {found}")
    kept = {} if own_copy is None else own_copy["files"]
    taken = [
        path
        for path in paths
        if (piece.root / path).exists() and not _holds(piece.root / path, kept.get(path))
    ]
    if taken:
        raise pl.Refused(
            f"the export would write over {', '.join(taken)}, and writes over only a file of "
            f"the piece's current copy with the hash the record keeps: name another place "
            f"under `{COPY_PLACE}`, or remove a file you mean to replace"
        )


def _place_problem(piece: pl.Piece, place: str) -> str | None:
    """Why `place` cannot hold the piece's current copy, read from its text alone, or None:
    the rules of a path in the repository, and the location."""
    found = loc.shape_problem(place)
    if found is not None:
        return found
    if place == piece.location or place.startswith(f"{piece.location}/"):
        return f"lies in the location `{piece.location}`: name a folder outside it"
    if place == CURRENT_COPY:
        return f"reads as the piece's own `{CURRENT_COPY}/` in the record: name another folder"
    return None


def _file_in_the_way(root: Path, place: str) -> str | None:
    """What says a file lies where `place`, or a folder above it, goes, or None."""
    target = root / place
    for path in (target, *target.parents):
        if path == root:
            break
        if path.exists() and not path.is_dir():
            return f"is no folder: {path.relative_to(root).as_posix()} is a file"
    return None


def _unkept(root: Path, paths: Sequence[str]) -> str | None:
    """What says version control does not keep one of `paths`, or None."""
    try:
        unkept = loc.ignored(root, paths)
    except loc.GitFailed as exc:
        return f"is no place git can say it keeps: {exc}"
    return f"is no place version control keeps: git ignores {', '.join(unkept)}" if unkept else None


def _holds(path: Path, hashed: str | None) -> bool:
    """Whether `path` is a file whose hash is `hashed`, which None never is."""
    try:
        return hashed is not None and hash_of(path.read_bytes()) == hashed
    except OSError:
        return False


def write(piece: pl.Piece, copy: Copy, change: Change) -> None:
    """Add to `change`, as its next steps, each file of `copy` at the place the piece names,
    or as its next step the folder that holds them, in place of the whole folder where one
    stands."""
    if piece.copy_place is not None:
        for name, data in copy.files.items():
            change.write(piece.root / piece.copy_place / name, data)
        return
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
    `versions` (`version_lock`, DEC-017 point 5). Raises fingerprint.UnreadableFingerprint
    where none can be read, as where no version of that number keeps a fingerprint."""
    return version_lock(_writer(entry, versions))


def version_lock(kept: Mapping[str, Any]) -> dict[str, str]:
    """The lock of a version the record of exports `kept`, read from its fingerprint (DEC-017
    point 1), each library and version held to its shape. Raises
    fingerprint.UnreadableFingerprint where none can be read: it keeps none, or it names a
    library or a version of no such shape, which a lock never holds."""
    lock = fingerprint.lock_of(kept.get("fingerprint"))
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


def written_fingerprint(
    entry: Mapping[str, Any], versions: Sequence[Mapping[str, Any]]
) -> Mapping[str, Any]:
    """The fingerprint of the version that wrote the current copy `entry` names, among the
    record's `versions`. `written_lock` says first whether one can be read."""
    return _writer(entry, versions)["fingerprint"]


def written_over_stale(
    entry: Mapping[str, Any], versions: Sequence[Mapping[str, Any]]
) -> list[str]:
    """The produced outputs the version that wrote the current copy `entry` names used while
    stale, among the record's `versions`; none where it keeps no such list."""
    kept = _writer(entry, versions).get("recorded")
    stale = kept.get("used-stale") if isinstance(kept, Mapping) else None
    return [str(output) for output in stale] if isinstance(stale, list) else []


def written_let_through(
    entry: Mapping[str, Any], versions: Sequence[Mapping[str, Any]]
) -> list[Mapping[str, Any]]:
    """Each number or date the version that wrote the current copy `entry` names let through,
    among the record's `versions` (`let_through`)."""
    return let_through(_writer(entry, versions))


#: The fields of a text a version let through that each entry holds: the fact, its text, the
#: element and its component. A component in a library adds its `version`.
_LET_THROUGH = ("fact", "text", "element", "component")


def let_through(kept: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Each number or date a version the record of exports `kept` let through, though it
    overflows (DEC-016 point 6), each entry that holds its fields as text; none where it
    keeps no such list, as a version that let none through."""
    recorded = kept.get("recorded")
    through = recorded.get("let-through") if isinstance(recorded, Mapping) else None
    if not isinstance(through, list):
        return []
    return [
        each
        for each in through
        if isinstance(each, Mapping)
        and all(isinstance(each.get(name), str) for name in _LET_THROUGH)
        and isinstance(each.get("version", ""), str)
    ]


def let_through_said(each: Mapping[str, Any]) -> str:
    """A text a version let through, in words: the fact, its text, the element and its
    component (`let_through`)."""
    return f"`{each['fact']}` as `{each['text']}` at `{each['element']}` in `{each['component']}`"


def written_differing(
    entry: Mapping[str, Any], versions: Sequence[Mapping[str, Any]]
) -> list[Mapping[str, Any]]:
    """Each element of a switching file the version that wrote the current copy `entry` names
    let through, among the record's `versions` (`differing`)."""
    return differing(_writer(entry, versions))


#: The fields of an element of a switching file a version let through: the file, the key of
#: the combination it paints otherwise, and the element.
_DIFFERING = ("file", "key", "element")


def differing(kept: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Each element of a switching file a version the record of exports `kept` let through,
    though it paints a combination otherwise than the one-key file of it (DEC-018 point 1),
    each entry that holds its fields as text; none where it keeps no such list."""
    recorded = kept.get("recorded")
    through = recorded.get("differing") if isinstance(recorded, Mapping) else None
    if not isinstance(through, list):
        return []
    return [
        each
        for each in through
        if isinstance(each, Mapping) and all(isinstance(each.get(name), str) for name in _DIFFERING)
    ]


def differing_said(each: Mapping[str, Any]) -> str:
    """An element of a switching file a version let through, in words: the element, its file
    and the key (`differing`)."""
    return f"`{each['element']}` of `{each['file']}` in `{each['key']}`"


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
