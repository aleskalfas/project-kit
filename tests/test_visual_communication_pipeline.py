"""The pipeline from a project's files to the engine (visual-communication DEC-002 point 5,
DEC-003 point 9, DEC-004 point 10, DEC-005 point 13): a piece read with its content, the
lock written into `piece.yaml` with every other byte kept, the `Env` over the locked
libraries, the notations the piece names and its produced pictures, and the scenes of each
language.

It also holds the projects the render, check and export tests draw: `drawing_project`, the
piece `flow`, a figure of the `tests` library's steps whose last step is a callout over the
produced picture `square`; and `system_project`, the piece `system`, a figure of a pattern
whose nodes take their colour family by concept, by the pattern's and by state.
"""

from __future__ import annotations

import hashlib
import json
import shutil
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
    TEST_NOTATION,
    TEST_PARTS,
    add_library,
    bound,
    copy_library,
    importable,
    project,
    write,
    write_list,
    write_piece,
    yaml_text,
)

pl, framing, seam, reading, fingerprint, before_after, copies, svg = load(
    "visual-communication",
    "pipeline",
    "framing",
    "plugins.seam",
    "reading",
    "fingerprint",
    "before_after",
    "copies",
    "plugins.svg",
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
        pytest.param(
            {"notations": "test-notation"},
            "`notations` is not a list of libraries' names",
            id="notations",
        ),
    ],
)
def test_a_piece_that_cannot_be_read_is_refused_naming_the_file(
    tmp_path: Path, fields: dict[str, Any], said: str
) -> None:
    root = drawing_project(tmp_path, **fields)
    with pytest.raises(pl.Refused) as refused:
        piece_of(root)
    assert said in str(refused.value)


@pytest.mark.parametrize(
    "lock",
    [
        pytest.param({**LOCK, "foundations": "../../x"}, id="version"),
        pytest.param({**LOCK, "../x": "1.0.0"}, id="name"),
    ],
)
def test_a_lock_that_would_lead_out_of_the_library_folder_is_refused_before_any_read(
    tmp_path: Path, lock: dict[str, str]
) -> None:
    root = drawing_project(tmp_path, picture=False)
    piece = piece_of(root)
    with pytest.raises(pl.Refused, match="which is no library at a version"):
        pl.Project(piece, lock, pl.Held(root, "visual"))


@pytest.mark.parametrize(
    ("state", "pinned"), [("draft", True), ("final", False), ("published", False)]
)
def test_a_pin_is_read_of_a_draft_alone(tmp_path: Path, state: str, pinned: bool) -> None:
    assert piece_of(drawing_project(tmp_path, state=state, pinned=True)).pinned is pinned


def test_a_piece_the_location_lacks_is_refused(tmp_path: Path) -> None:
    root = drawing_project(tmp_path)
    with pytest.raises(pl.Refused, match="holds no piece `other`"):
        pl.read_piece(root, "visual", "other")


def test_a_piece_needs_its_brand_its_top_and_each_library_its_content_uses(
    tmp_path: Path,
) -> None:
    assert pl.needed(piece_of(drawing_project(tmp_path))) == ["foundations", "test-brand", "tests"]


def test_a_piece_always_needs_the_foundations_whose_roles_every_piece_reads(
    tmp_path: Path,
) -> None:
    piece = piece_of(drawing_project(tmp_path, top="tests/steps", picture=False))
    assert pl.needed(piece) == ["foundations", "test-brand", "tests"]


def test_a_piece_needs_each_notation_it_names(tmp_path: Path) -> None:
    piece = pl.read_piece(system_project(tmp_path), "visual", "system")
    assert piece.notations == ["test-notation"]
    assert pl.needed(piece) == ["foundations", "test-brand", "test-notation"]


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


# --- a notation's concepts ----------------------------------------------------------------------

#: A pattern of the piece's own: the parts of a system in a row, each drawn by a node in
#: the family `orange` unless its concept or its state says otherwise.
PATTERN = bound(
    "component",
    status="experimental",
    about="The parts of a system in a row, each drawn by a node.",
    fields={
        "type": "object",
        "required": ["items"],
        "properties": {"items": {"type": "array", "items": {"type": "object"}}},
    },
    parts={
        "items": {
            "repeat": "items",
            "draw": "piece/node",
            "colour": "orange",
            "width": "=:width",
            "row": {"gap": "=@space.2", "sizes": "equal", "align-items": "stretch"},
        }
    },
    preferred={"height": "=items.height"},
)

#: One part of a system: its name on a box, both painted from its colour family.
NODE = bound(
    "component",
    status="experimental",
    about="One part of a system, its name on a box of its colour family.",
    fields={
        "type": "object",
        "required": ["name"],
        "properties": {"name": {"type": "string", "x-pkit-prose": True}},
    },
    states={"failing": {"colour": "red"}},
    parts={
        "box": {
            "box": {"fill": ":colour.fill", "stroke": ":colour.line"},
            "width": "=:width",
            "height": "=:height",
        },
        "name": {
            "text": {"content": "name", "style": "type.body", "fill": ":colour.text"},
            "x": "=@space.2",
            "y": "=@space.2",
            "width": "=:width - 2 * @space.2",
        },
    },
    preferred={"height": "=name.bottom + @space.2"},
)

#: The nodes of the pattern: a person by its concept, a service by the pattern's family, a
#: queue by its state, and a store whose state changes its concept's family.
NODES = [
    {"id": "user", "name": "User", "concept": "test-notation/person"},
    {"id": "api", "name": "API"},
    {"id": "queue", "name": "Queue", "state": "failing"},
    {"id": "store", "name": "Store", "concept": "test-notation/store", "state": "failing"},
]


def system_project(tmp_path: Path) -> Path:
    """The foundations, the test brand and the test notation, listed unreleased, and the
    draft `system`: a figure of the pattern over `NODES`, in both colour schemes."""
    root = project(tmp_path)
    copy_library(root, FOUNDATIONS, "foundations", "1.0.0")
    copy_library(root, TEST_BRAND, "test-brand", "1.0.0")
    copy_library(root, TEST_NOTATION, "test-notation", "1.0.0")
    unreleased = {"1.0.0": {"released": False}}
    write_list(
        root,
        {
            "foundations": {"source": {"kind": "shipped"}, "versions": unreleased},
            "test-brand": {"source": {"kind": "project"}, "versions": unreleased},
            "test-notation": {"source": {"kind": "project"}, "versions": unreleased},
        },
    )
    write_piece(
        root,
        "system",
        notations=["test-notation"],
        modes={"colour-scheme": ["light", "dark"]},
        lock={"foundations": "1.0.0", "test-brand": "1.0.0", "test-notation": "1.0.0"},
    )
    folder = root / "visual" / "pieces" / "system"
    write(folder / "components" / "pattern.yaml", yaml_text(PATTERN))
    write(folder / "components" / "node.yaml", yaml_text(NODE))
    body = {"use": "piece/pattern", "items": NODES}
    write(folder / "content.en.yaml", yaml_text(bound("content", body=body, caption="A system.")))
    return root


def hex_of(colour: Mapping[str, Any]) -> str:
    """An sRGB colour of the values document, as its hex code."""
    return "#" + "".join(f"{round(c * 255):02x}" for c in colour["components"])


def test_a_node_takes_its_concept_s_family_else_its_list_s_and_its_state_changes_either(
    tmp_path: Path,
) -> None:
    root = system_project(tmp_path)
    piece = pl.read_piece(root, "visual", "system")
    project = pl.Project(piece, piece.lock, pl.Held(root, "visual"))

    [(_, result)] = project.scenes()

    assert result.findings == []
    painted = {}
    for node in NODES:
        trace = f"figure/body/items[{node['id']}]"
        box, name = result.scene.find(f"{trace}/box"), result.scene.find(f"{trace}/name")
        assert box is not None and name is not None
        [[run]] = name.properties["paragraphs"]
        assert box.sources["fill"] == box.sources["stroke"] == run["sources"]["fill"]
        painted[node["id"]] = (box.properties["fill"], box.sources["fill"])
    assert painted == {
        "user": ("family.purple.fill", "content:body.items[user].concept"),
        "api": ("family.orange.fill", "default:piece/pattern"),
        "queue": ("family.red.fill", "content:body.items[queue].state"),
        "store": ("family.red.fill", "content:body.items[store].state"),
    }
    document = project.values()
    resolved = {
        key: {
            family: [hex_of(pl.colours_at(document, key)[f"family.{family}.{member}"])
                     for member in ("fill", "line", "text")]
            for family in ("purple", "orange", "red")
        }
        for key in project.keys
    }  # fmt: skip
    assert resolved == {
        "default": {
            "purple": ["#fbefff", "#8250df", "#512a97"],
            "orange": ["#fff1e5", "#bc4c00", "#762c00"],
            "red": ["#ffebe9", "#cf222e", "#82071e"],
        },
        "colour-scheme.dark": {
            "purple": ["#3c1e70", "#a371f7", "#e2c5ff"],
            "orange": ["#5a1e02", "#db6d28", "#ffc680"],
            "red": ["#67060c", "#f85149", "#ffc1ba"],
        },
    }


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


# --- a library's own roles (DEC-008) -----------------------------------------------------------


def parts_project(tmp_path: Path, warning: bool = False) -> Path:
    """The foundations, the test brand and the test library with roles of its own, listed
    unreleased, and the draft `tags`: a figure of the library's tag, under a lock of the
    three; with `warning`, the tag paints its label with the library's warning, which has
    no default and which the test brand, naming no library, leaves with no value."""
    root = project(tmp_path)
    copy_library(root, FOUNDATIONS, "foundations", "1.0.0")
    copy_library(root, TEST_BRAND, "test-brand", "1.0.0")
    parts = copy_library(root, TEST_PARTS, "test-parts", "1.0.0")
    if warning:
        tag = parts / "components" / "tag.yaml"
        tag.write_text(
            tag.read_text(encoding="utf-8").replace(
                "fill: test-parts.note", "fill: test-parts.warning"
            ),
            encoding="utf-8",
        )
    unreleased = {"1.0.0": {"released": False}}
    write_list(
        root,
        {
            "foundations": {"source": {"kind": "shipped"}, "versions": unreleased},
            "test-brand": {"source": {"kind": "project"}, "versions": unreleased},
            "test-parts": {"source": {"kind": "project"}, "versions": unreleased},
        },
    )
    write_piece(
        root,
        "tags",
        modes={"colour-scheme": ["light", "dark"]},
        lock={"foundations": "1.0.0", "test-brand": "1.0.0", "test-parts": "1.0.0"},
    )
    body = {"use": "test-parts/tag", "label": "Ready"}
    content = bound("content", body=body, caption="A tag.")
    write(root / "visual" / "pieces" / "tags" / "content.en.yaml", yaml_text(content))
    return root


def tags_project(root: Path) -> Any:
    piece = pl.read_piece(root, "visual", "tags")
    return pl.Project(piece, piece.lock, pl.Held(root, "visual"))


def test_a_project_reads_the_own_roles_of_each_library_it_locks(tmp_path: Path) -> None:
    project = tags_project(parts_project(tmp_path))
    assert set(project.scope.libraries) == {"test-parts"}
    assert project.foundations is project.scope.foundations
    assert project.brand.scope is project.scope
    assert [finding.code for finding in project.scope.findings] == ["role-brand-only"]


def test_a_part_reading_a_librarys_roles_draws_them_at_their_defaults(tmp_path: Path) -> None:
    project = tags_project(parts_project(tmp_path))
    [(_, result)] = project.scenes()
    assert result.findings == []
    box = result.scene.find("figure/body/box")
    label = result.scene.find("figure/body/label")
    assert box is not None and label is not None
    assert box.properties["fill"] == "test-parts.paper"
    [[run]] = label.properties["paragraphs"]  # a text's paint lies in its runs
    assert run["fill"] == "test-parts.note"
    assert project.env.role("test-parts.gap") == project.env.role("space.2")


def test_the_values_document_holds_each_role_of_a_locked_library_at_its_default(
    tmp_path: Path,
) -> None:
    project = tags_project(parts_project(tmp_path))
    document = project.values()
    held = document["tokens"]
    assert held["test-parts.note"] == {**held["text-primary"]}
    assert held["test-parts.gap"]["type"] == "dimension"
    assert "test-parts.warning" not in held
    assert document["lock"]["test-parts"] == "1.0.0"
    assert (
        pl.colours_at(document, "colour-scheme.dark")["test-parts.paper"]
        == (pl.colours_at(document, "colour-scheme.dark")["background"])
    )


def test_a_role_with_no_value_under_the_brand_is_none_to_the_engine_or_the_document(
    tmp_path: Path,
) -> None:
    project = tags_project(parts_project(tmp_path, warning=True))
    with pytest.raises(KeyError) as raised:
        project.env.role("test-parts.warning")
    assert type(raised.value).__name__ == "RoleWithoutValue"
    with pytest.raises(KeyError) as raised:
        project.env.role("test-parts.nothing")
    assert type(raised.value).__name__ == "UnknownRole"
    [(_, result)] = project.scenes()
    label = result.scene.find("figure/body/label")
    assert label is not None
    [[run]] = label.properties["paragraphs"]
    assert run["fill"] == "test-parts.warning"
    assert "test-parts.warning" not in project.values()["tokens"]


# --- whether versions fit the piece as its lock does (DEC-003 point 8, DEC-010 point 2, DEC-011
# --- point 4) -----------------------------------------------------------------------------------

#: The two libraries the fit of a draft's versions is judged with: blocks, and the patterns
#: that draw them, each built on the foundations.
BLOCKS, PATTERNS = "lab-blocks", "lab-patterns"
LISTED = {"type": "array", "items": {"type": "object"}}
V = pl.Version.parse


def component_text(**fields: Any) -> str:
    return yaml_text(bound("component", status="experimental", **fields))


def block(**more: Any) -> str:
    """A block that shows its `head`, with what `more` declares beside."""
    head = {"text": {"content": "head", "style": "type.body", "fill": "text-primary"}}
    return component_text(
        about="A head.",
        fields={"type": "object", "required": ["head"], "properties": {"head": {"type": "string"}}},
        parts={"head": {**head, "width": "=:width"}},
        preferred={"height": "=head.bottom"},
        **more,
    )


def write_blocks(root: Path, version: str, *, twice: bool = False) -> None:
    """A version of the blocks: a card; a card that declares the option `size`; an arrow,
    which takes ends; and a frame, which draws its `cards` where `twice`, so that a list a
    pattern draws and passes on to it is drawn twice."""
    components = add_library(root, BLOCKS, version, builds_on={"foundations": 1}) / "components"
    write(components / "card.yaml", block())
    write(components / "sized.yaml", block(options={"size": ["small", "large"]}))
    arrow = {"l": {"line": {"stroke": "line"}, "connect": "straight"}}
    write(components / "arrow.yaml", component_text(about="An arrow.", ends=True, parts=arrow))
    cards = {"repeat": "cards", "draw": f"{BLOCKS}/card", "width": "=:width", "column": {}}
    box = {"box": {"fill": "surface"}, "width": "=:width", "height": "=:height"}
    frame = component_text(
        about="A frame of cards.",
        fields={"type": "object", "properties": {"cards": LISTED}},
        parts={"cards": cards} if twice else {"box": box},
        preferred={"height": "=@space.4"},
    )
    write(components / "frame.yaml", frame)


def write_patterns(root: Path, version: str, *, size: bool = False, frame: bool = False) -> None:
    """A version of the patterns: a row of items, which declares the arrangement field
    `size` for them where `size`; and cards tied to each other, which also pass their cards
    on to the blocks' frame where `frame`."""
    builds_on = {"foundations": 1, BLOCKS: 1}
    components = add_library(root, PATTERNS, version, builds_on=builds_on) / "components"
    items = {"repeat": "items", "draw": f"{BLOCKS}/card", "width": "=:width", "row": {}}
    arranged = {"items": {"arrangement": {"size": {"words": ["one", "two"]}}}}
    write(
        components / "row.yaml",
        component_text(
            about="A row of items.",
            fields={"type": "object", "properties": {"items": LISTED}},
            parts={"items": items},
            preferred={"height": "=items.height"},
            **({"lists": arranged} if size else {}),
        ),
    )
    cards = {"repeat": "cards", "draw": f"{BLOCKS}/card", "width": "=@space.4 * 4", "column": {}}
    parts: dict[str, Any] = {
        "cards": cards,
        "links": {"repeat": "links", "draw": f"{BLOCKS}/arrow"},
    }
    if frame:
        parts["frame"] = {
            "use": f"{BLOCKS}/frame",
            "fields": {"cards": "cards"},
            "x": "=@space.4 * 5",
            "width": "=@space.4 * 4",
        }
    write(
        components / "net.yaml",
        component_text(
            about="Cards tied to each other.",
            fields={"type": "object", "properties": {"cards": LISTED, "links": LISTED}},
            lists={"links": {"ends": ["from", "to"]}},
            parts=parts,
            preferred={"height": "=@space.4 * 6"},
        ),
    )


#: A row whose first item names the sized card and gives `size`.
ROW = {
    "use": f"{PATTERNS}/row",
    "items": [
        {"id": "a", "use": f"{BLOCKS}/sized", "head": "A", "size": "large"},
        {"id": "b", "head": "B"},
    ],
}

#: Two cards and a tie between them.
NET = {
    "use": f"{PATTERNS}/net",
    "cards": [{"id": "a", "head": "A"}, {"id": "b", "head": "B"}],
    "links": [{"id": "ab", "from": {"item": "cards[a]"}, "to": {"item": "cards[b]"}}],
}


def lab_project(
    tmp_path: Path,
    body: Mapping[str, Any],
    lock: Mapping[str, str] | None,
    blocks: Mapping[str, bool],
    patterns: Mapping[str, Mapping[str, bool]],
    **fields: Any,
) -> Path:
    """The draft `flow` of `body` under `lock`, in a project that holds the foundations, the
    test brand, and each version of the blocks (`write_blocks`, whether its frame draws its
    cards) and of the patterns (`write_patterns`, with its options) given, all listed."""
    root = drawing_project(tmp_path, lock=lock, picture=False, **fields)
    for version, twice in blocks.items():
        write_blocks(root, version, twice=twice)
    for version, given in patterns.items():
        write_patterns(root, version, **given)
    unreleased = {"released": False}
    listed = {
        name: {"source": {"kind": "project"}, "versions": {v: unreleased for v in versions}}
        for name, versions in ((BLOCKS, blocks), (PATTERNS, patterns))
    }
    write_list(
        root,
        {
            "foundations": {"source": {"kind": "shipped"}, "versions": {"1.0.0": unreleased}},
            "test-brand": {"source": {"kind": "project"}, "versions": {"1.0.0": unreleased}},
            "tests": {"source": {"kind": "project"}, "versions": {"1.0.0": unreleased}},
            **listed,
        },
    )
    write_content(root, body=dict(body))
    return root


def lab_lock(blocks: str | None, patterns: str) -> dict[str, str]:
    """The lock of the lab piece: the foundations, the test brand, and the versions given."""
    lock = {"foundations": "1.0.0", "test-brand": "1.0.0", PATTERNS: patterns}
    return lock if blocks is None else {**lock, BLOCKS: blocks}


def judged(root: Path, blocks: str, patterns: str, fit: Any = None) -> list[Any]:
    """What the fit of the piece finds in the combination of its lock's foundations and
    brand with the versions given."""
    held = pl.Held(root, "visual")
    fit = fit or pl.fit(piece_of(root), held)
    versions = lab_lock(blocks, patterns)
    return fit({name: held.library(name, V(text)) for name, text in versions.items()})


def test_versions_under_which_an_item_carries_a_key_both_declare_do_not_fit(
    tmp_path: Path,
) -> None:
    root = lab_project(
        tmp_path,
        ROW,
        lab_lock("1.0.0", "1.0.0"),
        {"1.0.0": False},
        {"1.0.0": {}, "1.1.0": {"size": True}},
    )

    [misfit] = judged(root, "1.0.0", "1.1.0")

    assert misfit.rule == "clash"
    assert misfit.said == (
        f"the item `body.items[a]` carries `size`, which both its component `{BLOCKS}/sized` "
        f"and its list declare"
    )
    assert misfit.implicates == {"foundations", BLOCKS, PATTERNS}
    assert judged(root, "1.0.0", "1.0.0") == []


@pytest.mark.parametrize(
    "lock",
    [
        pytest.param(lab_lock("1.0.0", "1.1.0"), id="the-lock-shows-it"),
        pytest.param(lab_lock(None, "1.1.0"), id="a-library-named-for-the-first-time"),
    ],
)
def test_a_clash_the_lock_shows_or_cannot_show_holds_nothing_back(
    tmp_path: Path, lock: dict[str, str]
) -> None:
    root = lab_project(
        tmp_path,
        ROW,
        lock,
        {"1.0.0": False},
        {"1.1.0": {"size": True}, "1.2.0": {"size": True}},
    )
    assert judged(root, "1.0.0", "1.2.0") == []


def test_versions_under_which_a_component_draws_an_ends_list_twice_do_not_fit(
    tmp_path: Path,
) -> None:
    root = lab_project(
        tmp_path,
        NET,
        lab_lock("1.0.0", "1.0.0"),
        {"1.0.0": False, "1.1.0": True},
        {"1.0.0": {"frame": True}},
    )

    found = judged(root, "1.1.0", "1.0.0")

    assert [(misfit.rule, misfit.said) for misfit in found] == [
        ("end", "the end `from` of the tie `body.links[ab]` would not be found"),
        ("end", "the end `to` of the tie `body.links[ab]` would not be found"),
    ]
    assert found[0].implicates == {"foundations", BLOCKS, PATTERNS}
    assert judged(root, "1.0.0", "1.0.0") == []


def test_an_end_the_lock_does_not_find_holds_nothing_back(tmp_path: Path) -> None:
    root = lab_project(
        tmp_path,
        NET,
        lab_lock("1.0.0", "1.0.0"),
        {"1.0.0": True, "1.1.0": True},
        {"1.0.0": {"frame": True}},
    )
    assert judged(root, "1.1.0", "1.0.0") == []


def test_a_loss_only_both_newest_versions_show_is_found_in_that_combination_alone(
    tmp_path: Path,
) -> None:
    root = lab_project(
        tmp_path,
        NET,
        lab_lock("1.0.0", "1.0.0"),
        {"1.0.0": False, "1.1.0": True},
        {"1.0.0": {}, "1.1.0": {"frame": True}},
    )
    fit = pl.fit(piece_of(root), pl.Held(root, "visual"))
    lost = {
        (blocks, patterns): [misfit.rule for misfit in judged(root, blocks, patterns, fit)]
        for blocks in ("1.0.0", "1.1.0")
        for patterns in ("1.0.0", "1.1.0")
    }
    assert lost == {
        ("1.0.0", "1.0.0"): [],
        ("1.0.0", "1.1.0"): [],
        ("1.1.0", "1.0.0"): [],
        ("1.1.0", "1.1.0"): ["end", "end"],
    }


def test_each_file_a_version_holds_is_read_once_across_the_combinations_judged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = lab_project(
        tmp_path,
        NET,
        lab_lock("1.0.0", "1.0.0"),
        {"1.0.0": False, "1.1.0": True},
        {"1.0.0": {}, "1.1.0": {"frame": True}},
    )
    read: list[Path | None] = []
    reader = pl.read_component

    def counted(path: Path | None) -> Any:
        read.append(path)
        return reader(path)

    monkeypatch.setattr(pl, "read_component", counted)
    fit = pl.fit(piece_of(root), pl.Held(root, "visual"))
    for blocks in ("1.0.0", "1.1.0"):
        for patterns in ("1.0.0", "1.1.0"):
            judged(root, blocks, patterns, fit)

    assert len(read) == len(set(read)) > 0
    assert root / f"visual/libraries/{BLOCKS}/1.1.0/components/frame.yaml" in read


def test_a_piece_with_no_lock_yet_has_no_fit_to_judge(tmp_path: Path) -> None:
    root = lab_project(tmp_path, ROW, None, {"1.0.0": False}, {"1.0.0": {}})
    assert pl.fit(piece_of(root), pl.Held(root, "visual")) is None


# --- a side of a before-and-after (DEC-003 point 8, DEC-013 point 5) ----------------------------

#: The text a step's card draws, as the `tests` library ships it, and in another style.
HEAD = "text: {content: head, style: type.body, fill: text-primary}"
CHANGED_HEAD = "text: {content: head, style: type.heading, fill: text-primary}"


def every_file(folder: Path) -> dict[str, bytes]:
    return {
        path.relative_to(folder).as_posix(): path.read_bytes()
        for path in sorted(folder.rglob("*"))
        if path.is_file()
    }


def previews_of(root: Path) -> dict[str, str]:
    """The previews of the piece as its own location draws them."""
    drawn_project = project_of(root)
    found: dict[str, str] = {}
    for language, key, drawn in pl.drawn(drawn_project, drawn_project.scenes(), "svg"):
        found.update(pl.preview_files(PIECE, language, key, drawn.pages))
    return found


def changed_tests(folder: Path, version: str = "1.0.0") -> Path:
    """The `tests` library copied to `folder` at `version`, its card's head in another style."""
    shutil.copytree(TESTS, folder)
    card = folder / "components" / "card.yaml"
    card.write_text(card.read_text(encoding="utf-8").replace(HEAD, CHANGED_HEAD), encoding="utf-8")
    library = folder / "library.yaml"
    library.write_text(
        library.read_text(encoding="utf-8").replace("version: 1.0.0", f"version: {version}"),
        encoding="utf-8",
    )
    return folder


def shipped_tests(folder: Path) -> Any:
    """What a capability ships under the `tests` library's number, from `folder`."""
    files = tuple(every_file(folder))
    number = copies.Version.parse("1.0.0")
    return copies.Source("tests", number, folder, files, {"released": False}, None)


def test_a_side_with_no_version_given_is_what_the_pieces_own_location_draws(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    importable(monkeypatch, svg)
    root = drawing_project(tmp_path, picture=False)
    side = before_after.drawing(root, "visual", PIECE, LOCK)
    assert side.why == ""
    assert side.files == previews_of(root)
    assert sorted(side.files) == [f"{PIECE}.en.colour-scheme.dark.svg", f"{PIECE}.en.default.svg"]


def test_a_version_given_stands_in_for_the_copy_and_no_file_of_the_project_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    importable(monkeypatch, svg)
    root = drawing_project(tmp_path, picture=False)
    source = shipped_tests(changed_tests(tmp_path / "shipped"))
    before = every_file(root)
    side = before_after.drawing(root, "visual", PIECE, LOCK, [source])
    other = before_after.drawing(root, "visual", PIECE, LOCK)
    assert side.why == ""
    assert sorted(before_after.differing(other, side)) == sorted(other.files)
    assert every_file(root) == before
    assert list((root / before_after.FOLDER).iterdir()) == []


def test_a_side_under_another_lock_draws_the_versions_it_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    importable(monkeypatch, svg)
    root = drawing_project(tmp_path, picture=False)
    changed_tests(root / "visual/libraries/tests/1.1.0", "1.1.0")
    side = before_after.drawing(root, "visual", PIECE, {**LOCK, "tests": "1.1.0"})
    other = before_after.drawing(root, "visual", PIECE, LOCK)
    assert (side.why, other.why) == ("", "")
    assert sorted(before_after.differing(other, side)) == sorted(other.files)


def test_a_side_holds_the_pieces_own_files_and_the_locations_fonts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    importable(monkeypatch, svg)
    root = drawing_project(tmp_path)
    write_picture(root, framing)
    brand = root / "visual/libraries/test-brand/1.0.0"
    regular = brand / "fonts" / "SourceSansPro-Regular.otf"
    digest = f"sha256:{hashlib.sha256(regular.read_bytes()).hexdigest()}"
    base = brand / "tokens" / "base.tokens.json"
    data = json.loads(base.read_text(encoding="utf-8"))
    font = data["font"]["body"]["$extensions"]["pkit.visual-communication"]
    font["files"] = {"Source Sans Pro": {"hash": digest}}
    base.write_text(json.dumps(data, indent=2), encoding="utf-8")
    (root / "visual" / "fonts").mkdir()
    regular.rename(root / "visual" / "fonts" / "any-name.otf")
    side = before_after.drawing(root, "visual", PIECE, LOCK)
    assert side.why == ""
    assert side.files == previews_of(root)
    assert all("data:image/png" in text for text in side.files.values())


def test_a_side_that_cannot_be_drawn_says_why_and_names_the_projects_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    importable(monkeypatch, svg)
    root = drawing_project(tmp_path, picture=False)
    write(root / PIECE_FOLDER / "content.en.yaml", "not: [content\n")
    side = before_after.drawing(root, "visual", PIECE, LOCK)
    assert side.files == {}
    assert side.why.startswith(f"{PIECE_FOLDER}/content.en.yaml: ")
    assert list((root / before_after.FOLDER).iterdir()) == []


def test_a_side_whose_scenes_hold_no_page_says_why_once_for_every_language(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    importable(monkeypatch, svg)
    root = drawing_project(
        tmp_path, top="foundations/nothing", picture=False, languages=["en", "cs"]
    )
    write_content(root, "cs")
    side = before_after.drawing(root, "visual", PIECE, LOCK)
    assert side.files == {}
    assert side.why == (
        "the piece draws no page in `en`, `cs`: the piece's top names no component "
        "`foundations/nothing`"
    )
    assert list((root / before_after.FOLDER).iterdir()) == []


def test_a_top_that_cannot_be_read_names_the_component_and_no_path_of_the_side(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    importable(monkeypatch, svg)
    root = drawing_project(tmp_path, picture=False)
    write(root / "visual/libraries/foundations/1.0.0/components/figure.yaml", "not: [yaml\n")
    side = before_after.drawing(root, "visual", PIECE, LOCK)
    assert side.files == {}
    assert side.why.startswith(
        "the piece draws no page in `en`: the component `foundations/figure` cannot be read: "
    )
    assert ".location." not in side.why


def test_a_language_with_no_page_and_nothing_found_is_a_side_that_cannot_be_drawn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    importable(monkeypatch, svg)
    root = drawing_project(tmp_path, top="foundations/deck", picture=False, languages=["en", "cs"])
    write_content(root, slides=[{"id": "first", "layout": "slide", "title": "The flow"}])
    write_content(root, "cs", slides=[])
    side = before_after.drawing(root, "visual", PIECE, LOCK)
    assert side.files == {}
    assert side.why == "the piece draws no page in `cs`"


@pytest.mark.parametrize(
    ("library", "version"), [("../../..", "1.0.0"), ("tests", "../../../.."), ("tests", "2.0")]
)
def test_a_lock_entry_that_spells_no_version_reads_nothing_outside_the_library_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, library: str, version: str
) -> None:
    importable(monkeypatch, svg)
    root = drawing_project(tmp_path, picture=False)
    side = before_after.drawing(root, "visual", PIECE, {**LOCK, library: version})
    assert side.why.startswith(f"the lock of {PIECE_FOLDER}/piece.yaml names `{library}: ")
