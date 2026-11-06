"""The fingerprint, form 1 (DEC-006 points 5 and 6).

A fingerprint says when an output is stale. It keeps a hash of each thing a program read,
its *inputs*, and its value is the hash of them all:

    {form: 1, hash: sha256, format: 1, value: <hex>, inputs: [{<identity>, sha256}, ...]}

- **One reading.** A YAML file of the capability's format is read as its value, at the
  format number the fingerprint names; a JSON file as its value; any other file as its
  bytes. A value's text is its canonical JSON (RFC 8785, `reading.canonical_json`), so
  where and how a file writes a value changes nothing.
- **An input's identity** says what was read, apart from where the work lies, so moving
  the location or copying a piece makes nothing stale:
  - a piece's file, by its path within the piece folder: `{file}`;
  - a piece's file read without some of its fields, each named: `{file, without}`;
  - a part of a piece's or a content file, by the keys that lead to it: `{file, keys}`;
  - a library's file: `{library, version, path}`, its path within the version folder;
  - a font in the location's `fonts/`, by its hash: `{font}`;
  - a plugin's version: `{plugin, version}`;
  - a value of a brand: `{value: <token path>, key: <combination key>}`;
  - a measured frame: `{frame: <trace id>}`;
  - a variant's pixel size: `{pixels: <variant key>, width, height}`;
  - a declaration of written code, by its name: `{code}`.
- **An input's `sha256`** is the hash of what was read: the file's reading, the part's or
  the value's canonical text. For a plugin's version and a variant's pixels, which their
  identity holds whole, it is the hash of the identity's canonical text.
- **The value** is the hash of the canonical text of the inputs, each with its `sha256`,
  sorted by their identity's canonical text, in the order of its characters.

**The input set of each kind of fingerprint** is fixed by the form (`INPUT_SETS`), apart
from the fields an input names:

- `findings-key`, the key of a piece's findings record: the piece's own files, each locked
  library version's files, and each font of the location's `fonts/` the piece's scenes
  read. A piece's own files are every file of its folder but `findings.yaml`,
  `exports.yaml` and any file under `handed-out/` or `current-copy/`; under `produced/`,
  only each output's `record.yaml` is one, since it holds the hash of each of its pictures.
- `produced-record`, a produced output's record: its declaration, the part of `piece.yaml`
  at `[produced, <output>]`; each value it read, in each combination it serves; each
  variant's pixel size; and the producer's version.
- `code-record`, written code's record: its declaration file, each value it wrote in each
  combination, and the code writer's version.
- `export`: as `findings-key`, and the part of `piece.yaml` at `[exports]`, its formats.
  It reads `piece.yaml` without the fields that pass DEC-016 point 1's test, and each
  output's `record.yaml` without what it only records (`export_fields`). No other kind
  leaves a field out.
- `library-version`, a released version in the list: every file of its folder.

The check verifies a fingerprint by working out its input set from the current files under
the form the fingerprint names (`verify`), never under the current engine's idea of it. It
reads a file without the fields the kept input names, whatever the list holds today, and
reads the whole file where the input names none. So a change of the list takes no new form
(DEC-016 point 4). Any other new input is a new form, and every form the capability shipped
is kept.

**A version's lock** is read back from its fingerprint (`lock_of`, DEC-017 point 1): each
input of a library version names its library and that version, and those pairs are the
lock.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _lib.files import FORMAT, is_of_format
from _lib.reading import (
    ReadError,
    canonical_bytes,
    canonical_json,
    load_json,
    load_yaml,
    sha256,
)

#: The form this module writes, and the hash it takes.
FORM = 1
HASH = "sha256"

#: The files of a piece's folder that are no input of its scenes: what a render and an
#: export rewrite.
_PIECE_RECORDS = ("findings.yaml", "exports.yaml")

#: The folder of a piece that holds the files of the version handed out, and the one that
#: holds a published piece's current copy (DEC-016 point 3).
HANDED_OUT = "handed-out"
CURRENT_COPY = "current-copy"

#: The field of `piece.yaml` that names the place of a published piece's current copy.
COPY_PLACE = "copy-place"

#: The fields of `piece.yaml` an export's fingerprint leaves out, which `checks.md` lists:
#: each can change no exported file, or changes one only as a fact of that export (DEC-016
#: point 1). Any other field counts until a change adds it here.
PIECE_FIELDS_LEFT_OUT = (
    "accept-losses",
    "audience",
    COPY_PLACE,
    "explains",
    "pinned",
    "shown",
    "state",
)

#: The field of a produced output's record an export's fingerprint leaves out: what the
#: record only records (DEC-006 point 5).
RECORD_FIELDS_LEFT_OUT = ("recorded",)


class FingerprintError(Exception):
    """An input that cannot be read under the form, or a fingerprint not of its shape."""


class UnreadableFingerprint(FingerprintError):
    """A fingerprint no lock can be read from (`lock_of`). A caller names the record that
    keeps it, and refuses."""


@dataclass(frozen=True)
class Input:
    """One thing a program read: its identity, and the hash of what was read."""

    identity: Mapping[str, Any]
    sha256: str

    @property
    def text(self) -> str:
        """The identity's canonical text, by which inputs are sorted and compared."""
        return canonical_json(self.identity)

    def entry(self) -> dict[str, Any]:
        """The input as a fingerprint keeps it."""
        return {**self.identity, "sha256": self.sha256}


# --- reading ------------------------------------------------------------------------------------


def reading(
    path: Path,
    format: int = FORMAT,
    data: bytes | None = None,
    without: Sequence[str] = (),
) -> bytes:
    """The bytes a file's hash is taken of: a YAML file of the capability's format as the
    canonical text of its value, at `format`, the fields `without` names left out; a JSON
    file as the canonical text of its value; any other file, one that does not parse
    included, as its bytes. `data`, where given, is what the file holds once a command
    writes it, read in place of the file."""
    if data is None:
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise FingerprintError(f"{path} cannot be read: {exc.strerror or exc}") from exc
    if path.suffix == ".yaml":
        try:
            value = load_yaml(data.decode("utf-8"), str(path))
        except (ReadError, UnicodeDecodeError):
            return data
        if not is_of_format(value):
            return data
        _at_format(path, value, format)
        return canonical_bytes({k: v for k, v in value.items() if k not in without})
    if path.suffix == ".json":
        try:
            return canonical_bytes(load_json(data.decode("utf-8"), str(path)))
        except (ReadError, UnicodeDecodeError):
            return data
    return data


def part_of(
    path: Path, keys: Sequence[str], format: int = FORMAT, data: bytes | None = None
) -> Any:
    """The value at `keys` within the YAML file of the capability's format at `path`, read
    at `format`, or None where nothing lies. `data`, where given, is what the file holds
    once a command writes it, read in place of the file."""
    try:
        held = path.read_bytes() if data is None else data
        value = load_yaml(held.decode("utf-8"), str(path))
    except (OSError, UnicodeDecodeError, ReadError) as exc:
        raise FingerprintError(f"{path} cannot be read: {exc}") from exc
    if is_of_format(value):
        _at_format(path, value, format)
    for key in keys:
        value = value.get(key) if isinstance(value, Mapping) else None
    return value


def _at_format(path: Path, value: Mapping[str, Any], format: int) -> None:
    """Refuse a file of the capability's format at another number than `format`: format 1
    has no converter."""
    number = value.get("schema_version")
    if number != format or isinstance(number, bool):
        raise FingerprintError(
            f"{path} is at format {number!r}, which no converter brings to format {format}"
        )


# --- inputs -------------------------------------------------------------------------------------


def file_input(
    rel: str,
    path: Path,
    format: int = FORMAT,
    data: bytes | None = None,
    without: Sequence[str] = (),
) -> Input:
    """A piece's file, by its path within the piece folder; `data`, where given, read in
    place of the file (`reading`). An input read `without` fields names each of them,
    whether the file holds it or not, so a field set later stays left out."""
    identity: dict[str, Any] = {"file": rel}
    if without:
        identity["without"] = sorted(without)
    return Input(identity, sha256(reading(path, format, data, without)))


def part_input(rel: str, keys: Sequence[str], value: Any) -> Input:
    """The part of a piece's or a content file at `keys`, whose value is `value`."""
    return Input({"file": rel, "keys": list(keys)}, sha256(canonical_bytes(value)))


def library_file_input(
    library: str,
    version: str,
    rel: str,
    path: Path,
    format: int = FORMAT,
    data: bytes | None = None,
) -> Input:
    """A file of a library version, by its path within the version folder; `data`, where
    given, read in place of the file (`reading`)."""
    return Input(
        {"library": library, "version": version, "path": rel},
        sha256(reading(path, format, data)),
    )


def font_input(path: Path) -> Input:
    """A font of the location's `fonts/`, by its hash."""
    digest = sha256(path.read_bytes())
    return Input({"font": digest}, digest)


def plugin_input(plugin: str, version: str) -> Input:
    """A producer's or a code writer's version."""
    identity = {"plugin": plugin, "version": version}
    return Input(identity, sha256(canonical_bytes(identity)))


def value_input(token_path: str, key: str, value: Any) -> Input:
    """A brand's value at `token_path` in the combination `key`, in canonical form."""
    return Input({"value": token_path, "key": key}, sha256(canonical_bytes(value)))


def frame_input(trace_id: str, frame: Mapping[str, Any]) -> Input:
    """An element's measured frame."""
    return Input({"frame": trace_id}, sha256(canonical_bytes(frame)))


def pixels_input(key: str, width: int, height: int) -> Input:
    """A variant's pixel size."""
    identity = {"pixels": key, "width": width, "height": height}
    return Input(identity, sha256(canonical_bytes(identity)))


def code_input(name: str, path: Path, format: int = FORMAT) -> Input:
    """A declaration of written code, by its name."""
    return Input({"code": name}, sha256(reading(path, format)))


# --- the fingerprint ----------------------------------------------------------------------------


def fingerprint(inputs: Iterable[Input], format: int = FORMAT) -> dict[str, Any]:
    """The fingerprint of `inputs`, form 1. Raises FingerprintError when two inputs have
    one identity."""
    ordered = sorted(inputs, key=lambda item: item.text)
    for one, two in itertools.pairwise(ordered):
        if one.text == two.text:
            raise FingerprintError(f"the input {one.text} is read twice")
    entries = [item.entry() for item in ordered]
    return {
        "form": FORM,
        "hash": HASH,
        "format": format,
        "value": sha256(canonical_bytes(entries)),
        "inputs": entries,
    }


def changes(recorded: Mapping[str, Any], inputs: Iterable[Input]) -> list[str]:
    """What differs between a fingerprint and the inputs read now, each named; empty when
    it verifies. A fingerprint whose value does not match its own inputs is refused too."""
    fault = _inputs_fault(recorded)
    if fault is not None:
        return [fault]
    then = {canonical_json(_identity(entry)): entry["sha256"] for entry in recorded["inputs"]}
    now = {item.text: item.sha256 for item in inputs}
    found = []
    for text in sorted(set(then) | set(now)):
        if text not in now:
            found.append(f"{describe(text)} is no longer read")
        elif text not in then:
            found.append(f"{describe(text)} is read now")
        elif then[text] != now[text]:
            found.append(f"{describe(text)} changed")
    return found


def _inputs_fault(recorded: Mapping[str, Any]) -> str | None:
    """Why a fingerprint's own inputs cannot be trusted, or None where they can."""
    entries = recorded.get("inputs")
    if not isinstance(entries, list) or not all(
        isinstance(entry, Mapping) and isinstance(entry.get("sha256"), str) for entry in entries
    ):
        return "the fingerprint keeps no list of inputs"
    try:
        value = sha256(canonical_bytes(entries))
    except ReadError as exc:
        return f"the fingerprint's inputs cannot be read: {exc}"
    if recorded.get("value") != value:
        return "the fingerprint's value does not match its own inputs: it was edited"
    return None


def describe(text: str) -> str:
    """An input's identity, from its canonical text, in words."""
    identity = load_json(text)
    if "keys" in identity:
        return f"`{identity['file']}` at `{'.'.join(identity['keys'])}`"
    if "file" in identity:
        return f"`{identity['file']}`"
    if "library" in identity:
        return f"`{identity['path']}` of {identity['library']}@{identity['version']}"
    if "font" in identity:
        return f"the font {identity['font'][:12]}"
    if "plugin" in identity:
        return f"the plugin `{identity['plugin']}` {identity['version']}"
    if "value" in identity:
        return f"the value of `{identity['value']}` in `{identity['key']}`"
    if "frame" in identity:
        return f"the frame of `{identity['frame']}`"
    if "pixels" in identity:
        return f"the pixel size of the variant `{identity['pixels']}`"
    if "code" in identity:
        return f"the declaration `{identity['code']}`"
    return text


def _identity(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in entry.items() if key != "sha256"}


# --- the input sets of form 1 -------------------------------------------------------------------


def library_version_inputs(
    *,
    library: str,
    version: str,
    folder: Path,
    files: Iterable[Path],
    format: int = FORMAT,
    data: Mapping[str, bytes] | None = None,
) -> list[Input]:
    """Every file of a library version's folder. `data` gives, by its path within the
    folder, what a file holds once a command writes it, read in place of the file: so a
    release works out the hash of a version before it writes the release it needs."""
    written = data or {}
    inputs = []
    for path in files:
        rel = path.relative_to(folder).as_posix()
        inputs.append(library_file_input(library, version, rel, path, format, written.get(rel)))
    return inputs


def piece_files(piece: Path, files: Iterable[Path]) -> list[Path]:
    """A piece's own files, among every file of its folder: all but its findings and
    exports records, and any file under the folders of the version handed out and the
    current copy, whatever its name; and, under `produced/`, only each output's
    `record.yaml`, which holds the hash of each of its pictures."""
    own = []
    for path in files:
        parts = path.relative_to(piece).parts
        if len(parts) == 1 and parts[0] in _PIECE_RECORDS:
            continue
        if len(parts) > 1 and parts[0] in (HANDED_OUT, CURRENT_COPY):
            continue
        if parts[0] == "produced" and not _is_output_record(parts):
            continue
        own.append(path)
    return own


def _is_output_record(parts: Sequence[str]) -> bool:
    """Whether the path of `parts`, within a piece's folder, is an output's record."""
    return len(parts) == 3 and parts[0] == "produced" and parts[2] == "record.yaml"


def export_fields(rel: str) -> tuple[str, ...]:
    """The fields an export leaves out of the piece's file at `rel`, its path within the
    piece's folder, by the list today (DEC-016 point 1)."""
    if rel == "piece.yaml":
        return PIECE_FIELDS_LEFT_OUT
    if _is_output_record(rel.split("/")):
        return RECORD_FIELDS_LEFT_OUT
    return ()


def _own_and_locked_inputs(
    *,
    piece: Path,
    files: Iterable[Path],
    versions: Mapping[str, tuple[str, Path, Iterable[Path]]],
    fonts: Iterable[Path],
    format: int,
    written: Mapping[Path, bytes] | None,
    fields: Callable[[str], Sequence[str]],
) -> list[Input]:
    """The piece's own files among `files`, each read without the `fields` of its path;
    every file of each locked version; and each font read."""
    written = written or {}
    inputs = []
    for path in piece_files(piece, files):
        rel = path.relative_to(piece).as_posix()
        inputs.append(file_input(rel, path, format, written.get(path), fields(rel)))
    for library, (version, folder, held) in sorted(versions.items()):
        inputs.extend(
            library_version_inputs(
                library=library, version=version, folder=folder, files=held, format=format
            )
        )
    inputs.extend(font_input(path) for path in fonts)
    return inputs


def findings_key_inputs(
    *,
    piece: Path,
    files: Iterable[Path],
    versions: Mapping[str, tuple[str, Path, Iterable[Path]]],
    fonts: Iterable[Path],
    format: int = FORMAT,
    written: Mapping[Path, bytes] | None = None,
) -> list[Input]:
    """The key of a piece's findings record: the piece's own files among `files`, every
    file of each locked version (`versions`: library -> version, folder, files), and each
    font of the location's `fonts/` read. `written` gives the bytes of each file a render
    writes, such as `piece.yaml` with its lock moved, read in place of the file, so the
    render takes the key before its first write. Every file is read whole (DEC-016 point
    2)."""
    return _own_and_locked_inputs(
        piece=piece,
        files=files,
        versions=versions,
        fonts=fonts,
        format=format,
        written=written,
        fields=lambda _: (),
    )


def produced_record_inputs(
    *,
    piece: Path,
    output: str,
    values: Mapping[tuple[str, str], Any],
    pixels: Mapping[str, tuple[int, int]],
    producer: tuple[str, str],
    format: int = FORMAT,
) -> list[Input]:
    """A produced output's record: its declaration in `piece.yaml`, each value it read
    (`values`: (token path, combination key) -> value), each variant's pixel size, and the
    producer's version (name, version)."""
    keys = ["produced", output]
    inputs = [part_input("piece.yaml", keys, part_of(piece / "piece.yaml", keys, format))]
    inputs.extend(value_input(path, key, value) for (path, key), value in values.items())
    inputs.extend(pixels_input(key, width, height) for key, (width, height) in pixels.items())
    inputs.append(plugin_input(*producer))
    return inputs


def code_record_inputs(
    *,
    name: str,
    declaration: Path,
    values: Mapping[tuple[str, str], Any],
    writer: tuple[str, str],
    format: int = FORMAT,
) -> list[Input]:
    """Written code's record: its declaration file, each value it wrote, and the code
    writer's version."""
    inputs = [code_input(name, declaration, format)]
    inputs.extend(value_input(path, key, value) for (path, key), value in values.items())
    inputs.append(plugin_input(*writer))
    return inputs


def export_inputs(
    *,
    piece: Path,
    files: Iterable[Path],
    versions: Mapping[str, tuple[str, Path, Iterable[Path]]],
    fonts: Iterable[Path],
    format: int = FORMAT,
    written: Mapping[Path, bytes] | None = None,
    kept: Mapping[str, Sequence[str]] | None = None,
) -> list[Input]:
    """An export: as the key of the findings record, and the piece's formats of export.
    Each file is read without the fields `export_fields` lists for it. `written` is as for
    the findings key. `kept`, which `verify` gives, replaces that list: each file by its
    path, with the fields its kept input names; a file it does not name is read whole."""
    inputs = _own_and_locked_inputs(
        piece=piece,
        files=files,
        versions=versions,
        fonts=fonts,
        format=format,
        written=written,
        fields=export_fields if kept is None else lambda rel: kept.get(rel, ()),
    )
    path = piece / "piece.yaml"
    exports = part_of(path, ["exports"], format, (written or {}).get(path))
    inputs.append(part_input("piece.yaml", ["exports"], exports))
    return inputs


#: The input set of each kind of fingerprint, by form, apart from the fields an input names.
INPUT_SETS: Mapping[int, Mapping[str, Callable[..., list[Input]]]] = {
    1: {
        "findings-key": findings_key_inputs,
        "produced-record": produced_record_inputs,
        "code-record": code_record_inputs,
        "export": export_inputs,
        "library-version": library_version_inputs,
    },
}


def _form_fault(recorded: Mapping[str, Any]) -> str | None:
    """Why this capability reads no fingerprint of this form and hash, or None where it
    does."""
    form = recorded.get("form")
    if not isinstance(form, int) or isinstance(form, bool) or form not in INPUT_SETS:
        return f"the fingerprint's form {form!r} is not one this capability reads"
    if recorded.get("hash") != HASH:
        return f"the fingerprint's hash {recorded.get('hash')!r} is not one this form takes"
    return None


def _kept_fields(recorded: Mapping[str, Any]) -> dict[str, list[str]]:
    """The fields each file's kept input names, by the file's path. A file left out here
    is read whole; an input whose `without` is no list of text then does not verify."""
    kept = {}
    for entry in recorded.get("inputs") or []:
        if not isinstance(entry, Mapping) or not isinstance(entry.get("file"), str):
            continue
        without = entry.get("without")
        if isinstance(without, list) and all(isinstance(field, str) for field in without):
            kept[entry["file"]] = without
    return kept


def verify(recorded: Mapping[str, Any], kind: str, **sources: Any) -> list[str]:
    """What no longer matches a fingerprint of `kind`, its input set worked out from
    `sources` under the form the fingerprint names; empty when it verifies. An export's
    file is read without the fields its kept input names, whatever the list holds today
    (DEC-016 point 4)."""
    fault = _form_fault(recorded)
    if fault is not None:
        return [fault]
    form = recorded["form"]
    format = recorded.get("format")
    if isinstance(format, bool) or format != FORMAT:
        return [f"the fingerprint read at format {format!r}, which no converter reaches"]
    if kind == "export":
        sources = {**sources, "kept": _kept_fields(recorded)}
    try:
        inputs = INPUT_SETS[form][kind](format=format, **sources)
    except FingerprintError as exc:
        return [str(exc)]
    return changes(recorded, inputs)


def lock_of(recorded: Any) -> dict[str, str]:
    """The lock a version was made under, read from its fingerprint (DEC-017 point 1): each
    input of a library version names its library and that version, and those pairs are
    the lock. Raises UnreadableFingerprint where no lock can be read: nothing is kept, the
    form or hash is not read here, the inputs cannot be read or the value does not match
    them, or the inputs name no library version, or two of one library, which no lock
    holds."""
    if not isinstance(recorded, Mapping):
        raise UnreadableFingerprint("no fingerprint is kept")
    fault = _form_fault(recorded) or _inputs_fault(recorded)
    if fault is not None:
        raise UnreadableFingerprint(fault)
    lock: dict[str, str] = {}
    for entry in recorded["inputs"]:
        library, version = entry.get("library"), entry.get("version")
        if library is None:
            continue
        if not isinstance(library, str) or not isinstance(version, str):
            raise UnreadableFingerprint(f"the input {_identity(entry)} names no library version")
        if lock.setdefault(library, version) != version:
            raise UnreadableFingerprint(
                f"the fingerprint names two versions of `{library}`: {lock[library]} and {version}"
            )
    if not lock:
        raise UnreadableFingerprint("the fingerprint names no library version")
    return lock
