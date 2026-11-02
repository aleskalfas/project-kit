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
from tests.visual_communication_project import write

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


# --- each input ---------------------------------------------------------------------------------


def test_each_input_has_its_identity_and_the_hash_of_what_was_read(tmp_path: Path) -> None:
    piece = write(tmp_path / "piece.yaml", PIECE_YAML)
    font = write(tmp_path / "font.otf", "font bytes")
    cases = [
        (fingerprint.file_input("piece.yaml", piece), {"file": "piece.yaml"}, sha(PIECE_CANONICAL)),
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
