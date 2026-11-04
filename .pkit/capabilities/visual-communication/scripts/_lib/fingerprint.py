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

**The input set of each kind of fingerprint** is fixed by the form (`INPUT_SETS`):

- `findings-key`, the key of a piece's findings record: the piece's own files, each locked
  library version's files, and each font of the location's `fonts/` the piece's scenes
  read. A piece's own files are every file of its folder but `findings.yaml` and
  `exports.yaml`; under `produced/`, only each output's `record.yaml` is one, since it
  holds the hash of each of its pictures.
- `produced-record`, a produced output's record: its declaration, the part of `piece.yaml`
  at `[produced, <output>]`; each value it read, in each combination it serves; each
  variant's pixel size; and the producer's version.
- `code-record`, written code's record: its declaration file, each value it wrote in each
  combination, and the code writer's version.
- `export`: as `findings-key`, and the part of `piece.yaml` at `[exports]`, its formats.
- `library-version`, a released version in the list: every file of its folder.

The check verifies a fingerprint by working out its input set from the current files under
the form the fingerprint names (`verify`), never under the current engine's idea of it. A
new input is a new form, and every form the capability shipped is kept.
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


class FingerprintError(Exception):
    """An input that cannot be read under the form, or a fingerprint not of its shape."""


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


def reading(path: Path, format: int = FORMAT, data: bytes | None = None) -> bytes:
    """The bytes a file's hash is taken of: a YAML file of the capability's format as the
    canonical text of its value, at `format`; a JSON file as the canonical text of its
    value; any other file, one that does not parse included, as its bytes. `data`, where
    given, is what the file holds once a command writes it, read in place of the file."""
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
        return canonical_bytes(value)
    if path.suffix == ".json":
        try:
            return canonical_bytes(load_json(data.decode("utf-8"), str(path)))
        except (ReadError, UnicodeDecodeError):
            return data
    return data


def part_of(path: Path, keys: Sequence[str], format: int = FORMAT) -> Any:
    """The value at `keys` within the YAML file of the capability's format at `path`, read
    at `format`, or None where nothing lies."""
    try:
        value = load_yaml(path.read_bytes().decode("utf-8"), str(path))
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


def file_input(rel: str, path: Path, format: int = FORMAT, data: bytes | None = None) -> Input:
    """A piece's file, by its path within the piece folder; `data`, where given, read in
    place of the file (`reading`)."""
    return Input({"file": rel}, sha256(reading(path, format, data)))


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
    entries = recorded.get("inputs")
    if not isinstance(entries, list) or not all(
        isinstance(entry, Mapping) and isinstance(entry.get("sha256"), str) for entry in entries
    ):
        return ["the fingerprint keeps no list of inputs"]
    if recorded.get("value") != sha256(canonical_bytes(entries)):
        return ["the fingerprint's value does not match its own inputs: it was edited"]
    then = {canonical_json(_identity(entry)): entry["sha256"] for entry in entries}
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
    exports records; and, under `produced/`, only each output's `record.yaml`, which holds
    the hash of each of its pictures."""
    own = []
    for path in files:
        parts = path.relative_to(piece).parts
        if len(parts) == 1 and parts[0] in _PIECE_RECORDS:
            continue
        if parts[0] == "produced" and not (len(parts) == 3 and parts[2] == "record.yaml"):
            continue
        own.append(path)
    return own


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
    render takes the key before its first write."""
    written = written or {}
    inputs = [
        file_input(path.relative_to(piece).as_posix(), path, format, written.get(path))
        for path in piece_files(piece, files)
    ]
    for library, (version, folder, held) in sorted(versions.items()):
        inputs.extend(
            library_version_inputs(
                library=library, version=version, folder=folder, files=held, format=format
            )
        )
    inputs.extend(font_input(path) for path in fonts)
    return inputs


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
) -> list[Input]:
    """An export: as the key of the findings record, and the piece's formats of export."""
    inputs = findings_key_inputs(
        piece=piece, files=files, versions=versions, fonts=fonts, format=format
    )
    exports = part_of(piece / "piece.yaml", ["exports"], format)
    inputs.append(part_input("piece.yaml", ["exports"], exports))
    return inputs


#: The input set of each kind of fingerprint, by form.
INPUT_SETS: Mapping[int, Mapping[str, Callable[..., list[Input]]]] = {
    1: {
        "findings-key": findings_key_inputs,
        "produced-record": produced_record_inputs,
        "code-record": code_record_inputs,
        "export": export_inputs,
        "library-version": library_version_inputs,
    },
}


def verify(recorded: Mapping[str, Any], kind: str, **sources: Any) -> list[str]:
    """What no longer matches a fingerprint of `kind`, its input set worked out from
    `sources` under the form the fingerprint names; empty when it verifies."""
    form = recorded.get("form")
    if isinstance(form, bool) or form not in INPUT_SETS:
        return [f"the fingerprint's form {form!r} is not one this capability reads"]
    if recorded.get("hash") != HASH:
        return [f"the fingerprint's hash {recorded.get('hash')!r} is not one this form takes"]
    format = recorded.get("format")
    if isinstance(format, bool) or format != FORMAT:
        return [f"the fingerprint read at format {format!r}, which no converter reaches"]
    try:
        inputs = INPUT_SETS[form][kind](format=format, **sources)
    except FingerprintError as exc:
        return [str(exc)]
    return changes(recorded, inputs)
