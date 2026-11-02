"""The pipeline from a project's files to the engine (visual-communication DEC-002 point 5,
DEC-003 point 9, DEC-005 point 13): a piece read with its content, the lock written into
`piece.yaml` with every other byte kept, the `Env` over the locked libraries and the
piece's produced pictures, and the scenes of each language.

It also holds the project the render, check and export tests draw: `drawing_project`, the
piece `flow`, a figure of the `tests` library's steps whose last step is a callout over the
produced picture `square`.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tests import visual_communication_producer as producer
from tests.in_process import load
from tests.visual_communication_project import (
    FIXTURES,
    FOUNDATIONS,
    TEST_BRAND,
    bound,
    copy_library,
    project,
    write,
    write_list,
    write_piece,
    yaml_text,
)

pl, framing, seam, reading, fingerprint = load(
    "visual-communication", "pipeline", "framing", "plugins.seam", "reading", "fingerprint"
)

TESTS = FIXTURES / "libraries" / "tests" / "1.0.0"

PIECE = "flow"
OUTPUT = "square"
LOCK = {"foundations": "1.0.0", "test-brand": "1.0.0", "tests": "1.0.0"}
PIECE_FOLDER = f"visual/pieces/{PIECE}"

#: The red the callout's picture is painted, as 8-bit RGBA.
RED = (200, 30, 30, 255)

#: A step's text long enough to wrap over many lines in a third of the figure.
LONG = "a long step text that wraps over many lines of its card " * 12


def content(head: str = "Plan the work.", **fields: Any) -> dict[str, Any]:
    """The piece's content: three steps, the last a callout over `square`, and a caption."""
    data = {
        "body": {
            "use": "tests/steps",
            "steps": [
                {"id": "plan", "head": head},
                {"id": "build", "head": "Build it."},
                {
                    "id": "note",
                    "use": "tests/callout",
                    "pictures": [{"id": OUTPUT, "output": OUTPUT}],
                    "label": "Here",
                    "at": {"item": OUTPUT, "point": "tip"},
                },
            ],
        },
        "caption": "The flow.",
    }
    data.update(fields)
    return bound("content", **data)


def write_content(root: Path, language: str = "en", **fields: Any) -> Path:
    return write(root / PIECE_FOLDER / f"content.{language}.yaml", yaml_text(content(**fields)))


def drawing_project(tmp_path: Path, **given: Any) -> Path:
    """`lay_out_drawing` in a project root of its own, in `tmp_path`."""
    return lay_out_drawing(project(tmp_path), **given)


def lay_out_drawing(
    root: Path,
    *,
    lock: Mapping[str, str] | None = LOCK,
    modes: Mapping[str, list[str]] | None = None,
    head: str = "Plan the work.",
    picture: bool = True,
    **fields: Any,
) -> Path:
    """The shipped foundations, the test brand and the `tests` library, listed unreleased,
    and the draft `flow` laid out in the project at `root`: the figure of `content`, in
    both colour schemes, exported as SVG, which declares the produced output `square`
    (made by the test producer from `accent`, 100 × 100 pixels). Its picture is not
    written yet (`write_picture`). With `picture` false, the piece declares no produced
    output and its steps hold no callout, so no producer is needed to check it."""
    copy_library(root, FOUNDATIONS, "foundations", "1.0.0")
    copy_library(root, TEST_BRAND, "test-brand", "1.0.0")
    copy_library(root, TESTS, "tests", "1.0.0")
    unreleased = {"1.0.0": {"released": False}}
    write_list(
        root,
        {
            "foundations": {"source": {"kind": "shipped"}, "versions": unreleased},
            "test-brand": {"source": {"kind": "project"}, "versions": unreleased},
            "tests": {"source": {"kind": "project"}, "versions": unreleased},
        },
    )
    piece: dict[str, Any] = {
        "modes": dict(modes if modes is not None else {"colour-scheme": ["light", "dark"]}),
        "exports": ["svg"],
    }
    if picture:
        piece["produced"] = {
            OUTPUT: {
                "producer": producer.NAME,
                "inputs": {"fill": "accent"},
                "pixels": {"width": 100, "height": 100},
            }
        }
    if lock is not None:
        piece["lock"] = dict(lock)
    piece.update(fields)
    write_piece(root, PIECE, **piece)
    if picture:
        write_content(root, head=head)
    else:
        steps = content(head=head)["body"]["steps"][:2]
        write_content(root, body={"use": "tests/steps", "steps": steps})
    return root


def write_picture(root: Path, framing: ModuleType, colour: tuple[int, ...] = RED) -> Path:
    """The callout's picture as `pkit visual produce` keeps it, written directly: a PNG of
    `colour` for each variant, exposing `tip` at (75, 25), and its record, with the
    fingerprint of the files as they are now (the test producer registered with the
    `seam` beside `framing`)."""
    plan = framing.plan(root, "visual", PIECE, OUTPUT)
    folder = root / PIECE_FOLDER / "produced" / OUTPUT
    folder.mkdir(parents=True, exist_ok=True)
    data = producer.png(100, 100, (colour[0], colour[1], colour[2], colour[3]))
    digests = {}
    for key in plan.variants:
        (folder / f"{key}.png").write_bytes(data)
        digests[key] = reading.sha256(data)
    tip = {key: {"x": 75, "y": 25} for key in plan.variants}
    checked = framing.Checked(digests=digests, points={"tip": tip}, programs={})
    record = folder / "record.yaml"
    record.write_text(framing.record_text(framing.record_of(plan, checked)), encoding="utf-8")
    return record


@pytest.fixture(autouse=True)
def square() -> Any:
    producer.register(seam)
    yield
    seam.unregister(producer.NAME)


def piece_of(root: Path) -> Any:
    return pl.read_piece(root, "visual", PIECE)


def project_of(root: Path) -> Any:
    piece = piece_of(root)
    held = pl.Held(root, "visual")
    return pl.Project(piece, piece.lock, held)


# --- reading a piece ----------------------------------------------------------------------------


def test_a_piece_is_read_with_its_content_in_each_language(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, languages=["en", "cs"])
    write_content(root, "cs", head="Naplánovat.")
    piece = piece_of(root)
    assert piece.top == "foundations/figure"
    assert piece.languages == ["en", "cs"]
    assert piece.lock == LOCK
    assert piece.contents["cs"]["body"]["steps"][0]["head"] == "Naplánovat."
    assert "pkit_schema" not in piece.contents["en"]
    assert piece.exports == ["svg"]
    assert pl.piece_names(root, "visual") == [PIECE]


@pytest.mark.parametrize(
    ("fields", "said"),
    [
        pytest.param(
            {"languages": ["en", "de"]},
            f"{PIECE_FOLDER}/content.de.yaml does not exist: the piece lists the language `de`",
            id="no-content",
        ),
        pytest.param({"top": "figure"}, "`top` is not a use", id="top"),
        pytest.param({"lock": {"foundations": 1}}, "`lock` is not a mapping", id="lock"),
    ],
)
def test_a_piece_that_cannot_be_read_is_refused_naming_the_file(
    tmp_path: Path, fields: dict[str, Any], said: str
) -> None:
    root = drawing_project(tmp_path, **fields)
    with pytest.raises(pl.Refused) as refused:
        piece_of(root)
    assert said in str(refused.value)


def test_a_piece_the_location_lacks_is_refused(tmp_path: Path) -> None:
    root = drawing_project(tmp_path)
    with pytest.raises(pl.Refused, match="holds no piece `other`"):
        pl.read_piece(root, "visual", "other")


def test_a_piece_needs_its_brand_its_top_and_each_library_its_content_uses(
    tmp_path: Path,
) -> None:
    assert pl.needed(piece_of(drawing_project(tmp_path))) == ["foundations", "test-brand", "tests"]


# --- writing the lock ---------------------------------------------------------------------------


PIECE_TEXT = (
    "# A piece.\n"
    "top: foundations/figure  # the top\n"
    "lock:\n"
    "  # moved by render\n"
    "  foundations: 1.0.0\n"
    "\n"
    "state: draft\n"
)


def test_the_lock_replaces_the_block_and_keeps_every_other_byte() -> None:
    written = pl.lock_text(PIECE_TEXT, {"tests": "1.0.0", "foundations": "1.1.0"})
    assert written == (
        "# A piece.\n"
        "top: foundations/figure  # the top\n"
        "lock:\n"
        "  foundations: 1.1.0\n"
        "  tests: 1.0.0\n"
        "\n"
        "state: draft\n"
    )


def test_the_lock_is_added_at_the_end_with_the_files_line_endings_and_mark() -> None:
    text = pl.BOM + "top: foundations/figure\r\nstate: draft"
    assert pl.lock_text(text, {"foundations": "1.0.0"}) == (
        pl.BOM + "top: foundations/figure\r\nstate: draft\r\nlock:\r\n  foundations: 1.0.0\r\n"
    )


def test_a_lock_written_in_flow_style_is_replaced_whole() -> None:
    text = "lock: {foundations: 1.0.0}\nstate: draft\n"
    assert pl.lock_text(text, {"foundations": "1.0.1"}) == (
        "lock:\n  foundations: 1.0.1\nstate: draft\n"
    )


def test_a_lock_that_cannot_be_spliced_as_text_is_refused() -> None:
    text = "? lock\n: {foundations: 1.0.0}\nstate: draft\n"
    with pytest.raises(pl.Refused, match="cannot take the lock as text"):
        pl.lock_text(text, {"foundations": "1.0.0"})


def test_writing_the_lock_it_holds_writes_nothing(tmp_path: Path) -> None:
    root = drawing_project(tmp_path)
    path = root / PIECE_FOLDER / "piece.yaml"
    before = path.stat().st_mtime_ns
    assert pl.write_lock(piece_of(root), LOCK) is False
    assert path.stat().st_mtime_ns == before
    assert pl.write_lock(piece_of(root), {**LOCK, "tests": "1.0.0"}) is False


# --- the Env ------------------------------------------------------------------------------------


def test_the_env_reads_the_produced_picture_from_its_record(tmp_path: Path) -> None:
    root = drawing_project(tmp_path)
    write_picture(root, framing)
    project = project_of(root)
    picture = project.env.picture(OUTPUT)
    assert sorted(picture.variants) == ["colour-scheme.dark", "default"]
    assert picture.variants["default"] == {
        "file": "default.png",
        "pixels": {"width": 100, "height": 100},
    }
    assert picture.points == {
        "tip": {"colour-scheme.dark": {"x": 75, "y": 25}, "default": {"x": 75, "y": 25}}
    }
    assert project.env.pictures_at("colour-scheme.dark") == {
        OUTPUT: root / PIECE_FOLDER / "produced" / OUTPUT / "colour-scheme.dark.png"
    }


def test_a_missing_picture_is_kept_with_why_and_never_a_crash(tmp_path: Path) -> None:
    root = drawing_project(tmp_path)
    project = project_of(root)
    with pytest.raises(KeyError):
        project.env.picture(OUTPUT)
    assert project.env.missing == {
        OUTPUT: f"{PIECE_FOLDER}/produced/{OUTPUT}/record.yaml does not exist: the picture "
        f"was never produced"
    }
    [(_, result)] = project.scenes()
    assert [f.code for f in result.findings if f.code == "missing-picture"] == ["missing-picture"]


def test_a_record_naming_a_missing_variant_file_is_a_missing_picture(tmp_path: Path) -> None:
    root = drawing_project(tmp_path)
    write_picture(root, framing)
    (root / PIECE_FOLDER / "produced" / OUTPUT / "default.png").unlink()
    project = project_of(root)
    with pytest.raises(KeyError):
        project.env.picture(OUTPUT)
    assert (
        "names the variant `default` file `default.png`, which is missing"
        in (project.env.missing[OUTPUT])
    )


def test_a_project_has_a_scene_per_language_and_a_key_per_combination(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, languages=["en", "cs"])
    write_content(root, "cs")
    write_picture(root, framing)
    project = project_of(root)
    assert project.keys == ["default", "colour-scheme.dark"]
    scenes = project.scenes()
    assert [language for language, _ in scenes] == ["en", "cs"]
    assert all(result.scene.to_dict()["size-key"] == "default" for _, result in scenes)
    assert all(result.findings == [] for _, result in scenes)


def test_a_lock_naming_a_version_not_held_is_refused(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, lock={**LOCK, "test-brand": "2.0.0"})
    with pytest.raises(pl.Refused, match=r"names test-brand@2\.0\.0, which the project does not"):
        project_of(root)


# --- the findings record's key and the YAML a command writes ------------------------------------


def test_the_findings_key_changes_with_the_content_and_not_with_other_files(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path)

    def key() -> dict[str, Any]:
        piece = piece_of(root)
        sources = pl.findings_key_sources(root, pl.Held(root, "visual"), piece, piece.lock, [])
        return fingerprint.fingerprint(fingerprint.findings_key_inputs(**sources))

    first = key()
    write(root / "README.md", "Unrelated.\n")
    assert key() == first
    write_content(root, head="Plan the work again.")
    assert key() != first


def test_yaml_text_writes_a_header_and_no_alias() -> None:
    shared = {"x": 1}
    text = pl.yaml_text({"a": shared, "b": shared}, "One.\nTwo.")
    assert text == "# One.\n# Two.\n\na:\n  x: 1\nb:\n  x: 1\n"
    assert reading.load_yaml(text) == {"a": {"x": 1}, "b": {"x": 1}}
