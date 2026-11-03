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
        assert box.sources["fill"] == box.sources["stroke"] == name.sources["fill"]
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
    assert label.properties["fill"] == "test-parts.note"
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
    assert label.properties["fill"] == "test-parts.warning"
    assert "test-parts.warning" not in project.values()["tokens"]
