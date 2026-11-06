"""A published piece's current copy (visual-communication DEC-006 point 7, DEC-017 points 5
and 7): the one function that gives a copy's file its name and its hash, whose copy a record
names, and the lock read from the version that wrote it. What an export writes and refuses
is tested in `test_visual_communication_export.py`."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load
from tests.test_visual_communication_pipeline import PIECE, PIECE_FOLDER, drawing_project
from tests.visual_communication_project import SCHEMAS, write_piece

current_copy, files, fingerprint, reading, pl = load(
    "visual-communication", "current_copy", "files", "fingerprint", "reading", "pipeline"
)


# --- a file's name and hash ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "copy"),
    [
        ("flow.v3.en.default.svg", "flow.en.default.svg"),
        ("flow.v12.en.colour-scheme.dark.svg", "flow.en.colour-scheme.dark.svg"),
        (
            "flow.v1.cs.colour-scheme.dark+contrast.high.svg",
            "flow.cs.colour-scheme.dark+contrast.high.svg",
        ),
        ("deck.v1.en.default.2.svg", "deck.en.default.2.svg"),
        ("deck.v1.pt-br.default.pdf", "deck.pt-br.default.pdf"),
        ("release-notes.v2.en.default.pdf", "release-notes.en.default.pdf"),
        ("v1.v2.en.default.svg", "v1.en.default.svg"),
    ],
)
def test_a_copys_name_is_its_versions_with_the_number_left_out(name: str, copy: str) -> None:
    assert current_copy.file_of(name, b"held").name == copy


def test_a_copys_hash_is_the_sha_256_of_the_whole_file() -> None:
    data = b"<svg>\n  a file's whole bytes\n</svg>\n"
    assert current_copy.file_of("flow.v1.en.default.svg", data).sha256 == (
        hashlib.sha256(data).hexdigest()
    )


@pytest.mark.parametrize("name", ["flow.en.default.svg", "flow.v0.en.default.svg", "flow.svg"])
def test_a_name_that_carries_no_number_gives_no_copy(name: str) -> None:
    with pytest.raises(ValueError, match="carries no version's number"):
        current_copy.file_of(name, b"held")


# --- what an export makes -----------------------------------------------------------------------

#: A version's files, by name.
VERSION = {"flow.v2.en.default.svg": b"light", "flow.v2.en.colour-scheme.dark.svg": b"dark"}


def piece_in(root: Path, name: str = PIECE) -> Any:
    return pl.read_piece(root, "visual", name)


def test_a_published_piece_makes_a_copy_of_each_file_of_the_version(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, state="published", picture=False)
    made = current_copy.made(piece_in(root), 2, VERSION)
    assert made.files == {
        "flow.en.default.svg": b"light",
        "flow.en.colour-scheme.dark.svg": b"dark",
    }
    assert made.entry == {
        "piece": PIECE,
        "version": 2,
        "files": {
            "current-copy/flow.en.default.svg": reading.sha256(b"light"),
            "current-copy/flow.en.colour-scheme.dark.svg": reading.sha256(b"dark"),
        },
    }


@pytest.mark.parametrize("state", ["draft", "final"])
def test_a_piece_in_any_other_state_makes_none(tmp_path: Path, state: str) -> None:
    root = drawing_project(tmp_path, state=state, picture=False)
    assert current_copy.made(piece_in(root), 2, VERSION) is None


# --- whose copy it is ---------------------------------------------------------------------------


def entry_of(piece: str) -> dict[str, Any]:
    return {"piece": piece, "version": 1, "files": {"current-copy/x.en.default.svg": "0" * 64}}


def record_naming(piece: str) -> dict[str, Any]:
    return {current_copy.FIELD: entry_of(piece)}


def test_a_copy_is_the_piece_the_record_names(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    assert current_copy.own(piece_in(root), record_naming(PIECE)) == entry_of(PIECE)


def test_a_copy_of_a_piece_the_location_no_longer_holds_is_the_pieces_own(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    assert current_copy.own(piece_in(root), record_naming("flow-before")) == entry_of("flow-before")


def test_a_copy_of_a_piece_that_stands_is_none_of_this_pieces(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    write_piece(root, "flow-before")
    assert current_copy.own(piece_in(root), record_naming("flow-before")) is None


def test_a_folder_copied_by_hand_brings_a_copy_once_the_original_goes(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    shutil.copytree(root / PIECE_FOLDER, root / "visual" / "pieces" / "flow-two")
    copy = piece_in(root, "flow-two")
    assert current_copy.own(copy, record_naming(PIECE)) is None
    shutil.rmtree(root / PIECE_FOLDER)
    assert current_copy.own(copy, record_naming(PIECE)) == entry_of(PIECE)


def test_a_record_that_names_no_copy_holds_none_of_the_pieces(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    assert current_copy.own(piece_in(root), {}) is None


def test_a_record_that_names_no_copy_reads_as_none(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    assert current_copy.recorded(piece_in(root), {}) is None


def test_an_entry_is_read_whichever_piece_it_names(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    write_piece(root, "flow-before")
    assert current_copy.recorded(piece_in(root), record_naming("flow-before")) == (
        entry_of("flow-before")
    )


@pytest.mark.parametrize(
    "name",
    [
        "flow.en.default.svg",
        "flow.en.colour-scheme.dark+contrast.high.2.svg",
        "flow.pt-br.default.pdf",
    ],
)
def test_an_entry_the_schema_takes_is_read_as_it_stands(tmp_path: Path, name: str) -> None:
    root = drawing_project(tmp_path, picture=False)
    entry = {**entry_of(PIECE), "files": {f"current-copy/{name}": "0" * 64}}
    record = {**reading.read_yaml(SCHEMAS / "exports.yaml"), current_copy.FIELD: entry}
    assert files.shape_problems(record, "exports") == []
    assert current_copy.recorded(piece_in(root), record) == entry


@pytest.mark.parametrize(
    "entry",
    [
        pytest.param(None, id="nothing"),
        pytest.param("flow", id="no-mapping"),
        pytest.param({"version": 1, "files": {}}, id="no-piece"),
        pytest.param(entry_of("../outside"), id="a-path-for-a-piece"),
        pytest.param(entry_of("yes"), id="a-word-yaml-reads-for-a-piece"),
        pytest.param({**entry_of(PIECE), "version": "1"}, id="no-number"),
        pytest.param({**entry_of(PIECE), "version": True}, id="a-yes-for-a-number"),
        pytest.param({**entry_of(PIECE), "version": 0}, id="a-number-before-1"),
        pytest.param({"piece": PIECE, "version": 1}, id="no-files"),
        pytest.param({**entry_of(PIECE), "files": []}, id="no-mapping-of-files"),
        pytest.param({**entry_of(PIECE), "files": {}}, id="no-file"),
        pytest.param({**entry_of(PIECE), "written": "2026"}, id="another-field"),
        pytest.param(
            {**entry_of(PIECE), "files": {"current-copy/../x.en.default.svg": "0" * 64}},
            id="a-path-outside-the-folder",
        ),
        pytest.param(
            {**entry_of(PIECE), "files": {"current-copy/x.v1.en.default.svg": "0" * 64}},
            id="a-path-that-carries-a-number",
        ),
        pytest.param(
            {**entry_of(PIECE), "files": {"current-copy/x.en.default.svg": "0" * 63}},
            id="no-hash",
        ),
    ],
)
def test_an_entry_the_schema_refuses_is_refused(tmp_path: Path, entry: Any) -> None:
    root = drawing_project(tmp_path, picture=False)
    record = {**reading.read_yaml(SCHEMAS / "exports.yaml"), current_copy.FIELD: entry}
    assert files.shape_problems(record, "exports") != []
    said = f"{PIECE_FOLDER}/exports.yaml keeps a `current-copy`"
    with pytest.raises(pl.Refused, match=said):
        current_copy.recorded(piece_in(root), record)
    with pytest.raises(pl.Refused, match=said):
        current_copy.own(piece_in(root), record)


# --- the lock of the version that wrote it ------------------------------------------------------


def kept(library: str, version: str) -> dict[str, Any]:
    """A fingerprint of form 1 that names one library version, its value its inputs' hash."""
    entries = [{"library": library, "version": version, "path": "a.yaml", "sha256": "0" * 64}]
    return {
        "form": 1,
        "hash": "sha256",
        "format": 1,
        "value": reading.sha256(fingerprint.canonical_bytes(entries)),
        "inputs": entries,
    }


def test_the_lock_comes_from_the_version_that_wrote_the_copy() -> None:
    versions = [
        {"version": 1, "fingerprint": kept("tests", "1.0.0")},
        {"version": 2, "fingerprint": kept("tests", "1.1.0")},
    ]
    assert current_copy.written_lock(entry_of(PIECE), versions) == {"tests": "1.0.0"}


def test_a_version_the_record_does_not_hold_gives_no_lock() -> None:
    with pytest.raises(fingerprint.UnreadableFingerprint, match="no fingerprint is kept"):
        current_copy.written_lock(entry_of(PIECE), [])


@pytest.mark.parametrize(
    ("library", "version"),
    [
        pytest.param("../../outside", "1.0.0", id="a-path-for-a-library"),
        pytest.param("Tests", "1.0.0", id="a-library-of-no-name"),
        pytest.param("tests", "../../outside", id="a-path-for-a-version"),
        pytest.param("tests", "1.0", id="a-version-of-no-shape"),
        pytest.param("tests", "0.1.0", id="a-major-of-0"),
    ],
)
def test_a_lock_no_library_folder_could_hold_is_read_as_no_lock(library: str, version: str) -> None:
    versions = [{"version": 1, "fingerprint": kept(library, version)}]
    with pytest.raises(fingerprint.UnreadableFingerprint, match="is no library version"):
        current_copy.written_lock(entry_of(PIECE), versions)
