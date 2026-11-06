"""The fingerprint, form 1 (DEC-006 points 5 and 6): each input's identity and hash, worked
out here again from the canonical text by hand, so a change to the form shows; the value;
what `verify` names; and that moving or copying the work makes nothing stale."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load
from tests.visual_communication_project import CAPABILITY, write

(fingerprint,) = load("visual-communication", "fingerprint")

PIECE_YAML = "pkit_schema: visual-communication:piece\nschema_version: 1\nstate: draft\n"
PIECE_CANONICAL = b'{"pkit_schema":"visual-communication:piece","schema_version":1,"state":"draft"}'
WHITE = {"colorSpace": "srgb", "components": [1, 1, 1], "alpha": 1}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --- the reading of a file ----------------------------------------------------------------------


def test_a_yaml_file_of_the_format_is_read_as_its_value_however_written(tmp_path: Path) -> None:
    plain = write(tmp_path / "a.yaml", PIECE_YAML)
    other = write(
        tmp_path / "b.yaml",
        "# a comment\nstate: 'draft'\nschema_version: 1\n"
        'pkit_schema: "visual-communication:piece"\n',
    )
    assert fingerprint.reading(plain) == PIECE_CANONICAL
    assert fingerprint.reading(other) == PIECE_CANONICAL


def test_a_file_of_the_format_at_another_number_is_refused(tmp_path: Path) -> None:
    path = write(tmp_path / "a.yaml", PIECE_YAML.replace("schema_version: 1", "schema_version: 2"))
    with pytest.raises(fingerprint.FingerprintError, match="no converter"):
        fingerprint.reading(path)


def test_a_json_file_is_read_as_its_value(tmp_path: Path) -> None:
    path = write(tmp_path / "a.json", '{ "b": 1.0,\n  "a": [true] }\n')
    assert fingerprint.reading(path) == b'{"a":[true],"b":1}'


@pytest.mark.parametrize(
    ("name", "text"),
    [
        ("notes.yaml", "a: 1\n"),
        ("broken.yaml", "a: [\n"),
        ("broken.json", "{"),
        ("scene.svg", "<svg/>\n"),
    ],
)
def test_any_other_file_is_read_as_its_bytes(tmp_path: Path, name: str, text: str) -> None:
    path = write(tmp_path / name, text)
    assert fingerprint.reading(path) == text.encode()


def test_a_part_of_a_file_is_the_value_at_its_keys(tmp_path: Path) -> None:
    path = write(tmp_path / "piece.yaml", PIECE_YAML + "produced:\n  diagram: {producer: svg}\n")
    assert fingerprint.part_of(path, ["produced", "diagram"]) == {"producer": "svg"}
    assert fingerprint.part_of(path, ["produced", "chart"]) is None
    assert fingerprint.part_of(path, ["state", "deeper"]) is None


def test_a_part_of_a_file_a_command_writes_is_read_from_what_it_will_hold(tmp_path: Path) -> None:
    path = write(tmp_path / "piece.yaml", PIECE_YAML + "exports: [svg]\n")
    data = (PIECE_YAML + "exports: [pdf]\n").encode()
    assert fingerprint.part_of(path, ["exports"], data=data) == ["pdf"]


def test_a_file_of_the_format_is_read_without_the_fields_named(tmp_path: Path) -> None:
    path = write(tmp_path / "piece.yaml", PIECE_YAML + "pinned: true\n")
    assert fingerprint.reading(path, without=("pinned", "audience")) == PIECE_CANONICAL


@pytest.mark.parametrize(
    ("name", "text", "read"),
    [
        ("notes.yaml", "state: draft\n", b"state: draft\n"),
        ("broken.yaml", "state: [\n", b"state: [\n"),
        ("a.json", '{"state": 1}', b'{"state":1}'),
        ("scene.svg", "<svg/>\n", b"<svg/>\n"),
    ],
)
def test_only_a_file_of_the_format_loses_a_field(
    tmp_path: Path, name: str, text: str, read: bytes
) -> None:
    assert fingerprint.reading(write(tmp_path / name, text), without=("state",)) == read


# --- each input ---------------------------------------------------------------------------------


def test_each_input_has_its_identity_and_the_hash_of_what_was_read(tmp_path: Path) -> None:
    piece = write(tmp_path / "piece.yaml", PIECE_YAML)
    font = write(tmp_path / "font.otf", "font bytes")
    cases = [
        (fingerprint.file_input("piece.yaml", piece), {"file": "piece.yaml"}, sha(PIECE_CANONICAL)),
        (
            fingerprint.file_input("piece.yaml", piece, without=("state", "audience")),
            {"file": "piece.yaml", "without": ["audience", "state"]},
            sha(b'{"pkit_schema":"visual-communication:piece","schema_version":1}'),
        ),
        (
            fingerprint.part_input("piece.yaml", ["exports"], ["svg"]),
            {"file": "piece.yaml", "keys": ["exports"]},
            sha(b'["svg"]'),
        ),
        (
            fingerprint.library_file_input("brand", "1.0.0", "piece.yaml", piece),
            {"library": "brand", "version": "1.0.0", "path": "piece.yaml"},
            sha(PIECE_CANONICAL),
        ),
        (fingerprint.font_input(font), {"font": sha(b"font bytes")}, sha(b"font bytes")),
        (
            fingerprint.plugin_input("svg", "1.0.0"),
            {"plugin": "svg", "version": "1.0.0"},
            sha(b'{"plugin":"svg","version":"1.0.0"}'),
        ),
        (
            fingerprint.value_input("background", "default", WHITE),
            {"value": "background", "key": "default"},
            sha(b'{"alpha":1,"colorSpace":"srgb","components":[1,1,1]}'),
        ),
        (
            fingerprint.frame_input("t1", {"x": 0.5, "y": 2.0}),
            {"frame": "t1"},
            sha(b'{"x":0.5,"y":2}'),
        ),
        (
            fingerprint.pixels_input("default", 640, 480),
            {"pixels": "default", "width": 640, "height": 480},
            sha(b'{"height":480,"pixels":"default","width":640}'),
        ),
        (fingerprint.code_input("tokens-css", piece), {"code": "tokens-css"}, sha(PIECE_CANONICAL)),
    ]
    for made, identity, digest in cases:
        assert dict(made.identity) == identity
        assert made.sha256 == digest, identity


# --- the fingerprint ----------------------------------------------------------------------------


def test_the_value_is_the_hash_of_the_inputs_sorted_by_their_identity() -> None:
    plugin = fingerprint.plugin_input("svg", "1.0.0")
    value = fingerprint.value_input("background", "default", WHITE)
    made = fingerprint.fingerprint([value, plugin])
    entries = (
        b'[{"key":"default","sha256":"' + value.sha256.encode() + b'","value":"background"},'
        b'{"plugin":"svg","sha256":"' + plugin.sha256.encode() + b'","version":"1.0.0"}]'
    )
    assert made == {
        "form": 1,
        "hash": "sha256",
        "format": 1,
        "value": sha(entries),
        "inputs": [value.entry(), plugin.entry()],
    }
    assert fingerprint.fingerprint([plugin, value]) == made


def test_an_input_read_twice_is_refused() -> None:
    plugin = fingerprint.plugin_input("svg", "1.0.0")
    with pytest.raises(fingerprint.FingerprintError, match="read twice"):
        fingerprint.fingerprint([plugin, plugin])


def test_changes_name_what_was_changed_added_and_dropped() -> None:
    old = fingerprint.value_input("background", "default", WHITE)
    kept = fingerprint.plugin_input("svg", "1.0.0")
    dropped = fingerprint.frame_input("t1", {"x": 1})
    recorded = fingerprint.fingerprint([old, kept, dropped])
    now = [
        fingerprint.value_input("background", "default", {**WHITE, "alpha": 0.5}),
        kept,
        fingerprint.pixels_input("default", 10, 10),
    ]
    # In the order of the identities' canonical text: `{"frame"`, `{"height"`, `{"key"`.
    assert fingerprint.changes(recorded, now) == [
        "the frame of `t1` is no longer read",
        "the pixel size of the variant `default` is read now",
        "the value of `background` in `default` changed",
    ]
    assert fingerprint.changes(recorded, [old, kept, dropped]) == []


def test_a_fingerprint_whose_value_does_not_match_its_inputs_was_edited() -> None:
    plugin = fingerprint.plugin_input("svg", "1.0.0")
    recorded = fingerprint.fingerprint([plugin])
    recorded["inputs"][0]["sha256"] = "0" * 64
    assert fingerprint.changes(recorded, [plugin]) == [
        "the fingerprint's value does not match its own inputs: it was edited"
    ]
    assert fingerprint.changes({"inputs": "x"}, [plugin]) == [
        "the fingerprint keeps no list of inputs"
    ]


# --- verify, under the form the fingerprint names -----------------------------------------------


def library(tmp_path: Path) -> dict[str, Any]:
    folder = tmp_path / "libraries" / "brand" / "1.0.0"
    held = [
        write(
            folder / "library.yaml",
            "pkit_schema: visual-communication:library\nschema_version: 1\nname: brand\n",
        ),
        write(folder / "fonts" / "a.otf", "font"),
    ]
    return {"library": "brand", "version": "1.0.0", "folder": folder, "files": held}


def test_a_library_version_verifies_until_a_file_changes(tmp_path: Path) -> None:
    sources = library(tmp_path)
    recorded = fingerprint.fingerprint(fingerprint.library_version_inputs(**sources))
    assert fingerprint.verify(recorded, "library-version", **sources) == []
    (sources["folder"] / "fonts" / "a.otf").write_text("other", encoding="utf-8")
    assert fingerprint.verify(recorded, "library-version", **sources) == [
        "`fonts/a.otf` of brand@1.0.0 changed"
    ]


@pytest.mark.parametrize(
    ("field", "value", "said"),
    [
        ("form", 2, "form 2 is not one"),
        ("form", True, "form True is not one"),
        ("hash", "md5", "hash 'md5'"),
        ("format", 2, "at format 2"),
    ],
)
def test_a_fingerprint_of_another_form_hash_or_format_is_not_verified(
    tmp_path: Path, field: str, value: Any, said: str
) -> None:
    sources = library(tmp_path)
    recorded = fingerprint.fingerprint(fingerprint.library_version_inputs(**sources))
    recorded[field] = value
    (problem,) = fingerprint.verify(recorded, "library-version", **sources)
    assert said in problem


def lay_piece(location: Path) -> dict[str, Any]:
    """A piece with its records and a produced output, a locked library and a font, in
    `location`: the sources of its findings key."""
    piece = location / "pieces" / "flow"
    write(
        piece / "piece.yaml",
        PIECE_YAML + "exports: [svg]\nproduced:\n  diagram: {producer: svg}\n",
    )
    write(
        piece / "scenes" / "main.yaml",
        "pkit_schema: visual-communication:content\nschema_version: 1\n",
    )
    write(piece / "findings.yaml", "rewritten by a render\n")
    write(piece / "exports.yaml", "rewritten by an export\n")
    write(piece / "produced" / "diagram" / "record.yaml", "kept\n")
    write(piece / "produced" / "diagram" / "default.svg", "<svg/>\n")
    font = write(location / "fonts" / "a.otf", "font")
    folder = location / "libraries" / "brand" / "1.0.0"
    held = [
        write(
            folder / "library.yaml",
            "pkit_schema: visual-communication:library\nschema_version: 1\n",
        )
    ]
    files = sorted(path for path in piece.rglob("*") if path.is_file())
    return {
        "piece": piece,
        "files": files,
        "versions": {"brand": ("1.0.0", folder, held)},
        "fonts": [font],
    }


def test_a_pieces_own_files_leave_out_what_a_render_and_an_export_rewrite(tmp_path: Path) -> None:
    sources = lay_piece(tmp_path / "visual")
    own = fingerprint.piece_files(sources["piece"], sources["files"])
    assert [path.relative_to(sources["piece"]).as_posix() for path in own] == [
        "piece.yaml",
        "produced/diagram/record.yaml",
        "scenes/main.yaml",
    ]


def test_moving_or_copying_the_work_makes_nothing_stale(tmp_path: Path) -> None:
    sources = lay_piece(tmp_path / "visual")
    recorded = {
        kind: fingerprint.fingerprint(fingerprint.INPUT_SETS[1][kind](**sources))
        for kind in ("findings-key", "export")
    }
    shutil.copytree(tmp_path / "visual", tmp_path / "elsewhere" / "art")
    location = tmp_path / "elsewhere" / "art"
    piece = location / "pieces" / "flow"
    copied = {
        "piece": piece,
        "files": sorted(path for path in piece.rglob("*") if path.is_file()),
        "versions": {
            "brand": (
                "1.0.0",
                location / "libraries" / "brand" / "1.0.0",
                [location / "libraries" / "brand" / "1.0.0" / "library.yaml"],
            )
        },
        "fonts": [location / "fonts" / "a.otf"],
    }
    for kind, made in recorded.items():
        assert fingerprint.verify(made, kind, **copied) == [], kind


def test_a_findings_key_goes_stale_when_a_scene_changes_but_not_when_a_record_does(
    tmp_path: Path,
) -> None:
    sources = lay_piece(tmp_path / "visual")
    recorded = fingerprint.fingerprint(fingerprint.findings_key_inputs(**sources))
    piece = sources["piece"]
    (piece / "findings.yaml").write_text("rewritten again\n", encoding="utf-8")
    (piece / "produced" / "diagram" / "default.svg").write_text("<svg></svg>\n", encoding="utf-8")
    assert fingerprint.verify(recorded, "findings-key", **sources) == []
    scene = piece / "scenes" / "main.yaml"
    scene.write_text(scene.read_text(encoding="utf-8") + "# a comment changes no value\n")
    assert fingerprint.verify(recorded, "findings-key", **sources) == []
    scene.write_text(scene.read_text(encoding="utf-8") + "top: piece/chart\n")
    assert fingerprint.verify(recorded, "findings-key", **sources) == ["`scenes/main.yaml` changed"]


def test_an_export_goes_stale_when_its_formats_change(tmp_path: Path) -> None:
    sources = lay_piece(tmp_path / "visual")
    recorded = fingerprint.fingerprint(fingerprint.export_inputs(**sources))
    piece_yaml = sources["piece"] / "piece.yaml"
    piece_yaml.write_text(
        piece_yaml.read_text(encoding="utf-8").replace("[svg]", "[svg, png]"), encoding="utf-8"
    )
    assert fingerprint.verify(recorded, "export", **sources) == [
        "`piece.yaml` at `exports` changed",
        "`piece.yaml` changed",
    ]


# --- what an export reads (DEC-016) --------------------------------------------------------------

#: A listed field of a piece, as a person sets it, each in its form in `piece.yaml`.
LISTED = {
    "accept-losses": "accept-losses:\n  - {plugin: svg, what: blur, reason: Seen.}\n",
    "audience": "audience: Tests.\n",
    "copy-place": "copy-place: docs/images\n",
    "explains": "explains: true\n",
    "pinned": "pinned: true\n",
    "shown": "shown: Nowhere.\n",
    "state": "state: published\n",
}

RECORD_YAML = (
    "pkit_schema: visual-communication:produced-record\nschema_version: 1\n"
    "points: {}\nrecorded: {time: '2026-01-01T00:00:00Z'}\n"
)


def rewrite(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new), encoding="utf-8")


def add_field(piece: Path, text: str) -> None:
    """`text` in the piece's `piece.yaml`, in place of the field's value where it holds one."""
    path = piece / "piece.yaml"
    field = text.split(":")[0]
    held = [
        line
        for line in path.read_text(encoding="utf-8").splitlines(keepends=True)
        if not line.startswith(f"{field}:")
    ]
    path.write_text("".join(held) + text, encoding="utf-8")


def input_of(inputs: list[Any], file: str) -> Any:
    """The input that reads `file` itself, apart from any part of it."""
    (found,) = [
        item for item in inputs if item.identity.get("file") == file and "keys" not in item.identity
    ]
    return found


def test_an_export_names_each_listed_field_it_applied_whether_the_file_holds_it_or_not(
    tmp_path: Path,
) -> None:
    sources = lay_piece(tmp_path / "visual")
    read = input_of(fingerprint.export_inputs(**sources), "piece.yaml")
    assert dict(read.identity) == {
        "file": "piece.yaml",
        "without": [
            "accept-losses",
            "audience",
            "copy-place",
            "explains",
            "pinned",
            "shown",
            "state",
        ],
    }
    assert read.sha256 == sha(
        b'{"exports":["svg"],"pkit_schema":"visual-communication:piece",'
        b'"produced":{"diagram":{"producer":"svg"}},"schema_version":1}'
    )


@pytest.mark.parametrize("field", LISTED)
def test_a_listed_field_leaves_an_exports_fingerprint_verifying(tmp_path: Path, field: str) -> None:
    sources = lay_piece(tmp_path / "visual")
    recorded = fingerprint.fingerprint(fingerprint.export_inputs(**sources))
    add_field(sources["piece"], LISTED[field])
    assert fingerprint.verify(recorded, "export", **sources) == []


@pytest.mark.parametrize(
    ("field", "said"),
    [
        ("lock: {brand: 1.0.1}\n", ["`piece.yaml` changed"]),
        ("exports: [pdf]\n", ["`piece.yaml` at `exports` changed", "`piece.yaml` changed"]),
        ("a-later-field: 1\n", ["`piece.yaml` changed"]),
    ],
    ids=["the lock", "the formats", "a field added later"],
)
def test_a_field_not_listed_fails_an_exports_fingerprint(
    tmp_path: Path, field: str, said: list[str]
) -> None:
    sources = lay_piece(tmp_path / "visual")
    recorded = fingerprint.fingerprint(fingerprint.export_inputs(**sources))
    add_field(sources["piece"], field)
    assert fingerprint.verify(recorded, "export", **sources) == said


def test_a_produced_outputs_record_is_read_without_what_it_only_records(tmp_path: Path) -> None:
    sources = lay_piece(tmp_path / "visual")
    record = write(sources["piece"] / "produced" / "diagram" / "record.yaml", RECORD_YAML)
    made = fingerprint.export_inputs(**sources)
    read = input_of(made, "produced/diagram/record.yaml")
    assert dict(read.identity) == {"file": "produced/diagram/record.yaml", "without": ["recorded"]}
    assert read.sha256 == sha(
        b'{"pkit_schema":"visual-communication:produced-record","points":{},"schema_version":1}'
    )
    recorded = fingerprint.fingerprint(made)
    rewrite(record, "2026-01-01", "2026-02-02")
    assert fingerprint.verify(recorded, "export", **sources) == []
    rewrite(record, "points: {}", "points: {a: 1}")
    assert fingerprint.verify(recorded, "export", **sources) == [
        "`produced/diagram/record.yaml` changed"
    ]


def test_a_kept_fingerprint_of_the_whole_file_verifies_as_it_was_written(tmp_path: Path) -> None:
    sources = lay_piece(tmp_path / "visual")
    write(sources["piece"] / "produced" / "diagram" / "record.yaml", RECORD_YAML)
    # What an export read before DEC-016: the key's inputs, then its formats.
    whole = [
        *fingerprint.findings_key_inputs(**sources),
        fingerprint.part_input("piece.yaml", ["exports"], ["svg"]),
    ]
    recorded = fingerprint.fingerprint(whole)
    assert fingerprint.verify(recorded, "export", **sources) == []
    add_field(sources["piece"], LISTED["pinned"])
    assert fingerprint.verify(recorded, "export", **sources) == ["`piece.yaml` changed"]


def test_a_kept_input_reads_as_it_says_whatever_the_list_holds_today(tmp_path: Path) -> None:
    sources = lay_piece(tmp_path / "visual")
    piece = sources["piece"]
    made = fingerprint.export_inputs(
        **sources, kept={"piece.yaml": ["retired", "state"], "produced/diagram/record.yaml": []}
    )
    assert dict(input_of(made, "piece.yaml").identity) == {
        "file": "piece.yaml",
        "without": ["retired", "state"],
    }
    recorded = fingerprint.fingerprint(made)
    assert fingerprint.verify(recorded, "export", **sources) == []
    # A field the input names stays left out, though no list holds it now.
    add_field(piece, "retired: 1\n")
    assert fingerprint.verify(recorded, "export", **sources) == []
    # A field today's list holds counts where the input does not name it.
    add_field(piece, LISTED["pinned"])
    assert fingerprint.verify(recorded, "export", **sources) == ["`piece.yaml` changed"]


def test_an_input_that_names_fields_in_no_list_does_not_verify(tmp_path: Path) -> None:
    sources = lay_piece(tmp_path / "visual")
    recorded = fingerprint.fingerprint(fingerprint.export_inputs(**sources))
    entries = [
        {**entry, "without": "state"} if "without" in entry and "file" in entry else entry
        for entry in recorded["inputs"]
    ]
    recorded = {**recorded, "inputs": entries, "value": sha(fingerprint.canonical_bytes(entries))}
    problems = fingerprint.verify(recorded, "export", **sources)
    assert "`piece.yaml` is no longer read" in problems
    assert "`piece.yaml` is read now" in problems


@pytest.mark.parametrize("folder", ["handed-out", "current-copy"])
@pytest.mark.parametrize("kind", ["export", "findings-key"])
def test_no_file_under_the_folders_of_files_handed_out_and_a_copy_is_read(
    tmp_path: Path, folder: str, kind: str
) -> None:
    sources = lay_piece(tmp_path / "visual")
    reads = fingerprint.INPUT_SETS[1][kind]
    without = fingerprint.fingerprint(reads(**sources))
    piece = sources["piece"]
    laid = [
        write(piece / folder / "flow.v1.en.default.pdf", "%PDF"),
        write(piece / folder / "deep" / "piece.yaml", PIECE_YAML),
    ]
    assert fingerprint.fingerprint(reads(**{**sources, "files": sources["files"] + laid})) == (
        without
    )


@pytest.mark.parametrize("name", ["handed-out", "current-copy"])
def test_a_file_named_as_such_a_folder_is_a_pieces_own_file(tmp_path: Path, name: str) -> None:
    sources = lay_piece(tmp_path / "visual")
    file = write(sources["piece"] / name, "a person's file\n")
    assert file in fingerprint.piece_files(sources["piece"], [*sources["files"], file])


def test_an_export_takes_what_a_run_writes_in_place_of_the_file(tmp_path: Path) -> None:
    sources = lay_piece(tmp_path / "visual")
    path = sources["piece"] / "piece.yaml"
    moved = path.read_text(encoding="utf-8").replace("[svg]", "[pdf]") + "lock: {brand: 1.0.0}\n"
    taken = fingerprint.fingerprint(
        fingerprint.export_inputs(**sources, written={path: moved.encode()})
    )
    path.write_text(moved, encoding="utf-8")
    assert taken == fingerprint.fingerprint(fingerprint.export_inputs(**sources))


def test_only_an_export_leaves_a_field_out(tmp_path: Path) -> None:
    sources = lay_piece(tmp_path / "visual")
    key = fingerprint.fingerprint(fingerprint.findings_key_inputs(**sources))
    assert all("without" not in entry for entry in key["inputs"])
    add_field(sources["piece"], LISTED["pinned"])
    assert fingerprint.verify(key, "findings-key", **sources) == ["`piece.yaml` changed"]


def test_a_produced_output_written_code_and_a_library_read_their_listed_names_whole(
    tmp_path: Path,
) -> None:
    piece = lay_piece(tmp_path / "visual")["piece"]
    produced: dict[str, Any] = {
        "piece": piece,
        "output": "diagram",
        "values": {},
        "pixels": {},
        "producer": ("svg", "1.0.0"),
    }
    kept = fingerprint.fingerprint(fingerprint.produced_record_inputs(**produced))
    rewrite(piece / "piece.yaml", "{producer: svg}", "{producer: svg, state: on}")
    assert fingerprint.verify(kept, "produced-record", **produced) == [
        "`piece.yaml` at `produced.diagram` changed"
    ]
    declaration = write(
        tmp_path / "code.yaml",
        "pkit_schema: visual-communication:code\nschema_version: 1\nrecorded: 1\n",
    )
    code: dict[str, Any] = {
        "name": "css",
        "declaration": declaration,
        "values": {},
        "writer": ("css", "1.0.0"),
    }
    kept = fingerprint.fingerprint(fingerprint.code_record_inputs(**code))
    rewrite(declaration, "recorded: 1", "recorded: 2")
    assert fingerprint.verify(kept, "code-record", **code) == ["the declaration `css` changed"]
    version = library(tmp_path)
    kept = fingerprint.fingerprint(fingerprint.library_version_inputs(**version))
    assert all("without" not in entry for entry in kept["inputs"])
    rewrite(version["folder"] / "library.yaml", "name: brand", "name: brand\nstate: draft")
    assert fingerprint.verify(kept, "library-version", **version) == [
        "`library.yaml` of brand@1.0.0 changed"
    ]


def test_the_reference_names_the_fields_an_export_leaves_out() -> None:
    page = (CAPABILITY / "checks.md").read_text(encoding="utf-8")
    section = page.split("### What an export leaves out\n")[1].split("\n#")[0]
    for field in [*fingerprint.PIECE_FIELDS_LEFT_OUT, *fingerprint.RECORD_FIELDS_LEFT_OUT]:
        assert f"`{field}`" in section, field
    assert f"`{fingerprint.HANDED_OUT}/`" in page
    assert f"`{fingerprint.CURRENT_COPY}/`" in page


# --- a version's lock, read back (DEC-017 point 1) ------------------------------------------------


def test_a_versions_lock_is_read_from_its_fingerprint(tmp_path: Path) -> None:
    sources = lay_piece(tmp_path / "visual")
    folder = tmp_path / "visual" / "libraries" / "foundations" / "2.1.0"
    held = [write(folder / "library.yaml", "name: foundations\n"), write(folder / "a.yaml", "a\n")]
    sources["versions"]["foundations"] = ("2.1.0", folder, held)
    recorded = fingerprint.fingerprint(fingerprint.export_inputs(**sources))
    assert fingerprint.lock_of(recorded) == {"brand": "1.0.0", "foundations": "2.1.0"}


def test_a_lock_reads_the_same_from_a_kept_fingerprint_of_the_whole_file(tmp_path: Path) -> None:
    sources = lay_piece(tmp_path / "visual")
    recorded = fingerprint.fingerprint(fingerprint.findings_key_inputs(**sources))
    assert fingerprint.lock_of(recorded) == {"brand": "1.0.0"}


def sealed(inputs: list[dict[str, Any]]) -> dict[str, Any]:
    """A fingerprint of form 1 that holds `inputs`, its value their hash."""
    return {
        "form": 1,
        "hash": "sha256",
        "format": 1,
        "value": sha(fingerprint.canonical_bytes(inputs)),
        "inputs": inputs,
    }


FILE_OF_BRAND = {"library": "brand", "version": "1.0.0", "path": "a.yaml", "sha256": "0" * 64}


@pytest.mark.parametrize(
    ("recorded", "said"),
    [
        pytest.param(None, "no fingerprint is kept", id="missing"),
        pytest.param({**sealed([FILE_OF_BRAND]), "form": 2}, "form 2", id="another-form"),
        pytest.param({**sealed([FILE_OF_BRAND]), "hash": "md5"}, "hash 'md5'", id="another-hash"),
        pytest.param({**sealed([]), "inputs": "x"}, "no list of inputs", id="no-inputs"),
        pytest.param({**sealed([FILE_OF_BRAND]), "value": "0"}, "was edited", id="edited"),
        pytest.param(sealed([]), "names no library version", id="no-library"),
        pytest.param(
            sealed([{**FILE_OF_BRAND, "version": 1}]), "names no library version", id="no-version"
        ),
        pytest.param(
            sealed([FILE_OF_BRAND, {**FILE_OF_BRAND, "version": "2.0.0"}]),
            "two versions of `brand`: 1.0.0 and 2.0.0",
            id="two-versions",
        ),
    ],
)
def test_a_fingerprint_no_lock_can_be_read_from_raises_a_fault_that_says_why(
    recorded: Any, said: str
) -> None:
    with pytest.raises(fingerprint.UnreadableFingerprint, match=said) as raised:
        fingerprint.lock_of(recorded)
    assert isinstance(raised.value, fingerprint.FingerprintError)


# --- the other kinds ------------------------------------------------------------------------------


def test_a_produced_record_goes_stale_when_its_producer_changes(tmp_path: Path) -> None:
    piece = lay_piece(tmp_path / "visual")["piece"]
    sources: dict[str, Any] = {
        "piece": piece,
        "output": "diagram",
        "values": {("background", "default"): WHITE},
        "pixels": {"default": (640, 480)},
        "producer": ("svg", "1.0.0"),
    }
    recorded = fingerprint.fingerprint(fingerprint.produced_record_inputs(**sources))
    assert fingerprint.verify(recorded, "produced-record", **sources) == []
    newer = {**sources, "producer": ("svg", "1.1.0")}
    assert fingerprint.verify(recorded, "produced-record", **newer) == [
        "the plugin `svg` 1.0.0 is no longer read",
        "the plugin `svg` 1.1.0 is read now",
    ]


def test_a_code_record_goes_stale_when_a_value_it_wrote_changes(tmp_path: Path) -> None:
    declaration = write(
        tmp_path / "code" / "tokens-css.yaml",
        "pkit_schema: visual-communication:code\nschema_version: 1\n",
    )
    sources: dict[str, Any] = {
        "name": "tokens-css",
        "declaration": declaration,
        "values": {("background", "default"): WHITE},
        "writer": ("css", "1.0.0"),
    }
    recorded = fingerprint.fingerprint(fingerprint.code_record_inputs(**sources))
    assert fingerprint.verify(recorded, "code-record", **sources) == []
    darker = {**sources, "values": {("background", "default"): {**WHITE, "components": [0, 0, 0]}}}
    assert fingerprint.verify(recorded, "code-record", **darker) == [
        "the value of `background` in `default` changed"
    ]
