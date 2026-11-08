"""A picture file a piece shows (visual-communication DEC-025 points 1 to 3, 6, 7 and 9;
#2856), drawn by the engine from components written as mappings in memory and read through
the in-memory `Env` (`tests/visual_engine.py`), whose picture files are the test pictures
(`PICTURES`):

- an image's sources: exactly one of `produced`, `content`, `file` and `role` (a picture
  role, which `test_visual_communication_logos.py` shows);
- a field's picture file of the piece, whichever component draws it, and a field the
  content leaves empty, which draws nothing at zero size; a library's own file by
  `file`, and a local component's, which lies in the piece;
- a picture drawn whole, centred, as large as its frame allows, its height its
  proportions' where none is given; another file at a phone's size, by a `when` by the
  size;
- what the scene holds of such an image: its name, where it lies, their sources, and no
  variants and no points, so a formula that reads a point of it, and a tie's end that
  names one, is a finding;
- each finding on a name or a file, where the engine places it.

Then one piece of a project, in two languages, that shows a picture file of its own the
content names, its own component's file, a library's file and a produced picture
(`pictured_project`):

- what a renderer is handed for each image, in each language and combination, whatever its
  source; a library's file the same in every mode and under two brands;
- each language's file drawn in a preview, in an SVG, an HTML and a PDF export, and in a
  look, whose report names the picture with a colour profile; a PDF draws each picture,
  the produced one from the variant that serves each combination, and loses none;
- what the check finds of a file a field or a component names, and of a file nothing
  names;
- an export refused over a picture file missing or unreadable, writing nothing;
- a changed or added picture file: the findings record stale, the change since the last
  export, and a published piece's current copy out of date.
"""

from __future__ import annotations

import base64
import json
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tests import visual_communication_producer as producer
from tests.in_process import load, run_main
from tests.test_visual_communication_export import drawn_pictures
from tests.test_visual_communication_pipeline import (
    LOCK,
    PIECE,
    PIECE_FOLDER,
    content,
    drawing_project,
    every_file,
    list_drawing_libraries,
    stand_in_scenes,
    write_content,
    write_picture,
)
from tests.test_visual_communication_sizes import DEVICE, ON_DESKTOP, ON_PHONE
from tests.test_visual_communication_ties import pictured, to_a_point
from tests.visual_communication_project import (
    FOUNDATIONS,
    TEST_EDITION,
    TEST_PICTURES,
    add_library,
    bound,
    copy_library,
    importable,
    project,
    write,
    yaml_text,
)
from tests.visual_engine import (
    PICTURES,
    VERSIONS,
    FakeEnv,
    block,
    codes,
    draw,
    frame,
    layout,
    scene,
    top,
)
from tests.visual_engine import findings as engine_findings
from tests.visual_engine import seam as engine_seam

(
    export_script,
    render_script,
    check_script,
    mark_final_script,
    look_script,
    svg,
    html,
    pdf,
    seam,
    framing,
    pl,
    checks,
    reading,
    viewing,
    full_read,
    libraries,
    png,
) = load(
    "visual-communication",
    "export.py",
    "render.py",
    "check.py",
    "mark-final.py",
    "look.py",
    "plugins.svg",
    "plugins.html",
    "plugins.pdf",
    "plugins.seam",
    "framing",
    "pipeline",
    "checks",
    "reading",
    "viewing",
    "full_read",
    "libraries",
    "png",
)

#: The field a content names a picture file of the piece by.
FIELDS = {"photo": {"type": "string"}}

#: A list of items, each an object.
LISTED = {"type": "array", "items": {"type": "object"}}

#: The picture files the tests' environment holds, by holder and bare name: each a test
#: picture of 4 × 3 pixels.
FILES = {
    "piece/photo.jpg": PICTURES / "colour.jpg",
    "piece/photo.png": PICTURES / "palette.png",
    "piece/deep.png": PICTURES / "deep.png",
    "lab/logo.png": PICTURES / "alpha.png",
    "lab/tall.jpg": PICTURES / "grey.jpg",
}


def image(source: dict[str, Any], **geometry: Any) -> dict[str, Any]:
    """An image part of `source`, as wide as its component."""
    return {"image": source, "width": "=:width", **geometry}


def box(**geometry: Any) -> dict[str, Any]:
    return {"box": {"fill": "surface"}, "width": "=@space.4", "height": "=@space.4", **geometry}


def lab(**components: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {f"lab/{name}": component for name, component in components.items()}


def finding(result: Any, code: str) -> Any:
    found = [f for f in result.findings if f.code == code]
    assert found, f"no finding {code} in {codes(result)}"
    return found[0]


def shown(content: dict[str, Any], parts: dict[str, Any] | None = None) -> Any:
    """The scene of a top whose parts are `parts`, by default an image of the content's
    `photo`, drawn from `content` with `FILES`."""
    parts = parts if parts is not None else {"i": image({"content": "photo"})}
    return draw(content, components=lab(top=top(parts, fields=FIELDS)), files=FILES)


# --- an image's sources -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        {},
        {"produced": "photo", "content": "photo"},
        {"content": "photo", "file": "logo.png"},
        {"produced": "photo", "content": "photo", "file": "logo.png"},
        {"file": "logo.png", "role": "picture.logo"},
    ],
    ids=["none", "produced-and-content", "content-and-file", "all-three", "file-and-role"],
)
def test_an_image_names_exactly_one_source(source: dict[str, Any]) -> None:
    result = shown({"photo": "photo.png"}, {"i": image(source, height="=@space.4")})

    refused = finding(result, "component-shape")
    assert refused.message.endswith("names exactly one of `produced`, `content`, `file`, `role`")
    assert refused.where == "parts.i.image"


# --- a field's picture file ---------------------------------------------------------------------


def test_a_field_shows_the_pieces_picture_file_by_its_bare_name() -> None:
    result = shown({"photo": "photo.jpg"})

    assert result.findings == []
    element = result.scene.find("top/i")
    assert element is not None
    assert (element.properties["file"], element.properties["library"]) == ("photo.jpg", "piece")
    assert element.sources["file"] == "content:photo"
    for held in ("output", "variants", "points"):
        assert held not in element.properties


def test_a_picture_with_no_height_takes_its_proportions_and_any_frame_draws_it_whole() -> None:
    # The test pictures are 4 × 3 pixels, so 640 across makes 480 down.
    free = shown({"photo": "photo.jpg"})
    framed = shown({"photo": "photo.jpg"}, {"i": image({"content": "photo"}, height="=@space.4")})

    assert frame(free, "top/i") == (0.0, 0.0, 640.0, 480.0)
    assert frame(framed, "top/i") == (0.0, 0.0, 640.0, 32.0)
    for result in (free, framed):
        element = result.scene.find("top/i")
        assert element is not None
        assert element.properties["preserveAspectRatio"] == "xMidYMid meet"


@pytest.mark.parametrize("content", [{}, {"photo": ""}], ids=["left-out", "empty"])
def test_a_field_the_content_leaves_empty_draws_nothing_at_zero_size(
    content: dict[str, Any],
) -> None:
    parts = {"i": image({"content": "photo"}, x="=@space.2"), "b": box(y="=i.bottom + i.height")}

    result = shown(content, parts)

    assert result.findings == []
    assert result.scene.find("top/i") is None
    assert frame(result, "top/b")[1] == 0.0


def test_a_librarys_part_shows_the_file_the_content_names_of_the_piece() -> None:
    """Whichever component draws the image, a field's file lies in the piece, and its name's
    source is the key the content writes."""
    shot = block({"pic": image({"content": "photo"})}, fields=FIELDS)
    parts = {"shots": {"repeat": "shots", "draw": "lab/shot", "width": "=:width", "column": {}}}
    components = lab(top=top(parts, fields={"shots": LISTED}), shot=shot)

    result = draw(
        {"shots": [{"id": "a", "photo": "photo.png"}]}, components=components, files=FILES
    )

    assert result.findings == []
    element = result.scene.find("top/shots[a]/pic")
    assert element is not None
    assert (element.properties["file"], element.properties["library"]) == ("photo.png", "piece")
    assert element.sources["file"] == "content:shots[a].photo"


# --- a component's own file ---------------------------------------------------------------------


def test_a_library_components_file_lies_in_its_own_version() -> None:
    result = draw(components=lab(top=top({"i": image({"file": "logo.png"})})), files=FILES)

    assert result.findings == []
    element = result.scene.find("top/i")
    assert element is not None
    assert element.properties["file"] == "logo.png"
    assert element.properties["library"] == "lab@1.0.0"
    assert element.sources["file"] == "default:lab/top"


def test_a_local_components_file_lies_in_the_piece() -> None:
    components = {"piece/top": top({"i": image({"file": "photo.png"})})}

    result = draw(use="piece/top", components=components, files=FILES)

    assert result.findings == []
    element = result.scene.find("top/i")
    assert element is not None
    assert (element.properties["file"], element.properties["library"]) == ("photo.png", "piece")
    assert element.sources["file"] == "default:piece/top"


def test_a_when_by_the_size_shows_another_file_at_a_phones_size() -> None:
    parts = {
        "wide": image({"file": "logo.png"}, when=ON_DESKTOP),
        "tall": image({"file": "tall.jpg"}, when=ON_PHONE, width="=:width / 2"),
    }

    def at(mode: str) -> Any:
        return scene.compute_scene(
            piece="test-piece",
            top="lab/top",
            content={},
            language="en",
            lock=dict(VERSIONS),
            size_key="default" if mode == "desktop" else f"device.{mode}",
            seam_version=engine_seam.SEAM_VERSION,
            env=FakeEnv(components=lab(top=top(parts)), files=FILES),
            facts=layout.stand_ins("draft"),
            sizes=layout.Sizes({"device": DEVICE}, {"device": mode}),
        )

    desktop, phone = at("desktop"), at("phone")

    assert desktop.findings == phone.findings == []
    assert desktop.scene.find("top/tall") is None and phone.scene.find("top/wide") is None
    assert frame(desktop, "top/wide")[2:] == (640.0, 480.0)
    assert frame(phone, "top/tall")[2:] == (320.0, 240.0)
    tall = phone.scene.find("top/tall")
    assert tall is not None and tall.properties["file"] == "tall.jpg"


# --- no points ----------------------------------------------------------------------------------


def test_a_formula_that_reads_a_point_of_a_picture_file_finds_it_exposes_none() -> None:
    shot = block(
        {"pic": image({"content": "photo"})},
        fields=FIELDS,
        exposes=["pic"],
        preferred={"height": "=pic.height"},
    )
    callout = top(
        {
            "shots": {"repeat": "shots", "draw": "lab/shot", "width": "=:width", "column": {}},
            "mark": box(x="={at}.x", y="={at}.y"),
        },
        fields={"shots": LISTED},
        options={"at": {"item": "shots", "point": True}},
    )
    content = {"shots": [{"id": "p", "photo": "photo.png"}], "at": {"item": "p", "point": "tip"}}

    result = draw(content, components=lab(top=callout, shot=shot), files=FILES)

    assert "exposes no part or point `tip`" in finding(result, "missing-exposed").message
    assert result.scene.find("top/shots[p]/pic") is not None


def test_a_ties_end_at_a_point_of_a_picture_file_is_a_finding_and_the_picture_drawn() -> None:
    found = pictured()
    found["lab/pictured"]["parts"]["pic"]["image"] = {"content": "art"}
    content = to_a_point()
    content["pics"][0]["art"] = "photo.png"

    result = draw(content, components=found, files=FILES)

    point = finding(result, "end-point")
    assert point.where == "links[ap].to.point"
    assert "`tip`" in point.message
    assert result.scene.find("top/links[ap]") is None
    assert result.scene.find("top/pics[p]/pic") is not None


def test_a_ties_end_at_the_item_of_a_picture_file_meets_it() -> None:
    found = pictured()
    found["lab/pictured"]["parts"]["pic"]["image"] = {"content": "art"}
    content = to_a_point()
    content["pics"][0]["art"] = "photo.png"
    del content["links"][0]["to"]["point"]

    result = draw(content, components=found, files=FILES)

    assert result.findings == []
    assert result.scene.find("top/links[ap]/l") is not None


# --- where a finding lies -----------------------------------------------------------------------


def test_a_field_naming_no_file_of_the_piece_is_a_finding_in_the_content() -> None:
    result = shown({"photo": "gone.jpg"})

    [missing] = result.findings
    assert (missing.code, missing.file, missing.where) == ("picture-missing", "", "photo")
    assert "component" not in missing.extra
    assert result.scene.find("top/i") is None


def test_a_component_naming_no_file_of_its_own_is_a_finding_at_its_part() -> None:
    result = draw(components=lab(top=top({"i": image({"file": "gone.png"})})), files=FILES)

    [missing] = result.findings
    assert (missing.code, missing.where) == ("picture-missing", "parts.i.image.file")
    assert missing.extra["component"] == "lab/top"
    assert result.scene.find("top/i") is None


def test_a_file_of_an_encoding_refused_is_a_finding_at_the_file_and_is_not_drawn() -> None:
    result = shown({"photo": "deep.png"})

    [refused] = result.findings
    assert (refused.code, refused.file) == ("picture-encoding", "pictures/deep.png")
    assert result.scene.find("top/i") is None


# --- a piece of a project -----------------------------------------------------------------------


#: The component library whose component shows a picture file of its own version.
FRAMES = "frames"
FRAMES_FOLDER = f"visual/libraries/{FRAMES}/1.0.0"
#: The piece's own picture files, and the library's.
PIECE_PICTURES = f"{PIECE_FOLDER}/pictures"
FRAMES_PICTURES = f"{FRAMES_FOLDER}/pictures"
#: Where the piece's exports lie, local to the clone.
EXPORTS = f".pkit/capabilities/visual-communication/project/local/exports/{PIECE}"

#: Each image of the piece, by its trace id.
SHOT = "figure/body/steps[shot]/image"
BADGE = "figure/body/steps[badge]/image"
MARK = "figure/body/steps[mark]/image"
NOTE = "figure/body/steps[note]/pictures[square]/image"


def component(about: str, image: dict[str, str], **fields: Any) -> dict[str, Any]:
    """A component of one image as wide as it is given, which takes `fields`."""
    return bound(
        "component",
        status="experimental",
        about=about,
        fields={"type": "object", "required": sorted(fields), "properties": fields},
        parts={"image": {"image": image, "width": "=:width"}},
        preferred={"height": "=image.height"},
    )


#: The piece's own component that shows the picture file of the piece the content names.
SHOT_COMPONENT = component(
    "A picture file of the piece, which the content names.",
    {"content": "photo"},
    photo={"type": "string", "description": "The bare name of a picture file of the piece."},
)
#: The piece's own component that shows one picture file of the piece.
BADGE_COMPONENT = component("The piece's badge.", {"file": "badge.jpg"})
#: The library's component that shows a picture file of its own version.
MARK_COMPONENT = component("The library's mark.", {"file": "mark.png"})


def steps(photo: str) -> list[dict[str, Any]]:
    """The piece's steps: a card, the content's picture file `photo`, the piece's badge, the
    library's mark, and the callout over the produced picture."""
    return [
        {"id": "plan", "head": "Plan the work."},
        {"id": "shot", "use": "piece/shot", "photo": photo},
        {"id": "badge", "use": "piece/badge"},
        {"id": "mark", "use": f"{FRAMES}/mark"},
        content()["body"]["steps"][2],
    ]


def held(folder: Path, name: str, source: str) -> Path:
    """The test picture `source` held in `folder`'s `pictures/` as `name`."""
    target = folder / "pictures" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(TEST_PICTURES / source, target)
    return target


def pictured_project(tmp_path: Path, **fields: Any) -> Path:
    """The drawing project in English and Czech, its picture made, whose steps show a picture
    file of the piece the content names in each language, a PNG with a colour profile in
    English and a JPEG in Czech; the piece's own badge, a JPEG; the mark of the library
    `frames`, a PNG of its own version; and the produced picture."""
    stays = fields.get("state") in ("final", "published")
    root = drawing_project(
        tmp_path, languages=["en", "cs"], lock={**LOCK, FRAMES: "1.0.0"}, **fields
    )
    write_picture(root, framing)
    frames = add_library(root, FRAMES, "1.0.0", builds_on={"foundations": 1})
    write(frames / "components" / "mark.yaml", yaml_text(MARK_COMPONENT))
    held(frames, "mark.png", "palette.png")
    list_drawing_libraries(root, released=stays, **{FRAMES: "project"})
    piece = root / PIECE_FOLDER
    write(piece / "components" / "shot.yaml", yaml_text(SHOT_COMPONENT))
    write(piece / "components" / "badge.yaml", yaml_text(BADGE_COMPONENT))
    held(piece, "photo.png", "profile.png")
    held(piece, "photo.jpg", "progressive.jpg")
    held(piece, "badge.jpg", "colour.jpg")
    write_content(root, "en", body={"use": "tests/steps", "steps": steps("photo.png")})
    write_content(root, "cs", body={"use": "tests/steps", "steps": steps("photo.jpg")})
    return root


@pytest.fixture(autouse=True)
def plugins(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The renderers stand in for the import a run makes when it draws, and the test
    producer is registered, for the length of the test."""
    importable(monkeypatch, svg, html, pdf)
    producer.register(seam)
    yield
    seam.unregister(producer.NAME)


def project_of(root: Path) -> Any:
    """The piece's project, read by this module's pipeline, whose seam's pictures the tests
    compare."""
    piece = pl.read_piece(root, "visual", PIECE)
    return pl.Project(piece, piece.lock, pl.Held(root, "visual"))


def data_of(path: Path) -> str:
    """The data a renderer embeds of the picture file at `path`, of its kind."""
    kind = "jpeg" if path.suffix == ".jpg" else "png"
    return f"data:image/{kind};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def failing(found: list[Any]) -> list[Any]:
    return [finding for finding in found if finding.level == engine_findings.FAILS]


def check_document(root: Path, *args: str) -> dict[str, Any]:
    shown = run_main(check_script, "--json", *args, cwd=root, env={"PKIT_COMMAND_DEADLINE": None})
    assert shown.returncode == 0, shown.stderr
    return json.loads(shown.stdout)


def located(root: Path, label: str) -> list[tuple[str, str]]:
    """The severity and location of each finding of `label` the check gives."""
    return [
        (each["severity"], each["location"])
        for each in check_document(root)["findings"]
        if each["label"] == label
    ]


def test_one_piece_shows_its_own_picture_files_a_librarys_and_a_produced_picture(
    tmp_path: Path,
) -> None:
    root = pictured_project(tmp_path)
    project = project_of(root)

    results = stand_in_scenes(project)

    assert [language for language, _ in results] == ["en", "cs"]
    assert [failing(result.findings) for _, result in results] == [[], []]
    en, cs = (result.scene.to_dict() for _, result in results)
    pictures, frames = root / PIECE_PICTURES, root / FRAMES_PICTURES
    produced = root / PIECE_FOLDER / "produced" / "square"
    assert project.env.handed(en, "default") == {
        SHOT: seam.Shown(pictures / "photo.png", seam.PNG),
        BADGE: seam.Shown(pictures / "badge.jpg", seam.JPEG),
        MARK: seam.Shown(frames / "mark.png", seam.PNG),
        NOTE: seam.Shown(produced / "default.png", seam.PNG),
    }
    assert project.env.handed(cs, "colour-scheme.dark") == {
        SHOT: seam.Shown(pictures / "photo.jpg", seam.JPEG),
        BADGE: seam.Shown(pictures / "badge.jpg", seam.JPEG),
        MARK: seam.Shown(frames / "mark.png", seam.PNG),
        NOTE: seam.Shown(produced / "colour-scheme.dark.png", seam.PNG),
    }
    [mark] = [element for element in pl._images(en["children"]) if element["id"] == MARK]
    assert (mark["file"], mark["library"]) == ("mark.png", "frames@1.0.0")


def test_a_librarys_file_is_the_same_in_every_mode_and_under_two_brands(tmp_path: Path) -> None:
    root = pictured_project(tmp_path)
    copy_library(root, TEST_EDITION, "test-edition", "1.0.0")
    list_drawing_libraries(root, released=False, **{FRAMES: "project", "test-edition": "project"})
    path = root / PIECE_FOLDER / "piece.yaml"
    piece = reading.read_yaml(path)
    shown = []
    for brand in ("test-brand", "test-edition"):
        piece.update(brand=brand, lock={**LOCK, FRAMES: "1.0.0", "test-edition": "1.0.0"})
        write(path, yaml_text(piece))
        project = project_of(root)
        for _, result in stand_in_scenes(project):
            scene_ = result.scene.to_dict()
            shown.extend(project.env.handed(scene_, key)[MARK] for key in project.keys)

    assert len(shown) == 2 * 2 * 2
    assert set(shown) == {seam.Shown(root / FRAMES_PICTURES / "mark.png", seam.PNG)}


def test_each_language_previews_and_exports_its_own_file_in_svg_and_html(tmp_path: Path) -> None:
    root = pictured_project(tmp_path, exports=["svg", "html"])
    pictures, frames = root / PIECE_PICTURES, root / FRAMES_PICTURES
    previewed = run_main(render_script, PIECE, cwd=root)
    assert previewed.returncode == 0, previewed.stderr
    exported = run_main(export_script, PIECE, cwd=root)
    assert exported.returncode == 0, exported.stderr

    previews = root / ".pkit/capabilities/visual-communication/project/local/previews" / PIECE
    for language, own, other in (
        ("en", "photo.png", "photo.jpg"),
        ("cs", "photo.jpg", "photo.png"),
    ):
        drawn = [
            (previews / f"{PIECE}.{language}.default.svg").read_text(encoding="utf-8"),
            (root / EXPORTS / f"{PIECE}.v1.{language}.colour-scheme.dark.svg").read_text(
                encoding="utf-8"
            ),
            (root / EXPORTS / f"{PIECE}.v1.{language}.default.html").read_text(encoding="utf-8"),
        ]
        for text in drawn:
            assert data_of(pictures / own) in text
            assert data_of(pictures / other) not in text
            assert data_of(pictures / "badge.jpg") in text
            assert data_of(frames / "mark.png") in text


def test_a_look_draws_each_picture_and_names_the_one_with_a_colour_profile(
    tmp_path: Path,
) -> None:
    root = pictured_project(tmp_path)

    shown = run_main(look_script, PIECE, "--every-language", cwd=root)

    assert shown.returncode == 0, shown.stderr
    report = json.loads(
        (root / viewing.FOLDER / PIECE / viewing.REPORT).read_text(encoding="utf-8")
    )
    assert report["losses"] == []
    assert report["profiles"] == [
        {
            "language": "en",
            "key": "default",
            "page": "figure",
            "element": SHOT,
            "picture": "photo.png",
            "why": viewing.WITHOUT_PROFILE,
        }
    ]
    assert f"profile: figure (en, default): `{SHOT}` shows `photo.png`: " in shown.stdout


# --- what the check finds -----------------------------------------------------------------------


def test_a_16_bit_png_a_field_names_fails_at_the_piece(tmp_path: Path) -> None:
    root = pictured_project(tmp_path)
    held(root / PIECE_FOLDER, "photo.png", "deep.png")

    assert located(root, "picture-encoding") == [("error", f"{PIECE_PICTURES}/photo.png")]


def test_a_file_of_pictures_that_nothing_names_takes_no_finding(tmp_path: Path) -> None:
    root = pictured_project(tmp_path)
    held(root / PIECE_FOLDER, "spare.png", "deep.png")
    held(root / PIECE_FOLDER, "Not Bare.PNG", "cmyk.jpg")

    found = check_document(root)["findings"]

    assert [each for each in found if each["location"].startswith(PIECE_PICTURES)] == []
    assert [
        each
        for each in found
        if each["label"].startswith("picture-") and each["severity"] != "info"
    ] == []


def test_a_name_a_field_gives_that_the_piece_lacks_fails_in_the_content(tmp_path: Path) -> None:
    root = pictured_project(tmp_path)
    (root / PIECE_PICTURES / "photo.jpg").unlink()

    assert located(root, "picture-missing") == [
        ("error", f"{PIECE_FOLDER}/content.cs.yaml#body.steps[shot].photo")
    ]


def test_a_name_a_librarys_component_gives_that_its_version_lacks_fails_in_the_component(
    tmp_path: Path,
) -> None:
    root = pictured_project(tmp_path)
    (root / FRAMES_PICTURES / "mark.png").unlink()

    assert located(root, "picture-missing") == [
        ("error", f"{FRAMES_FOLDER}/components/mark.yaml#parts.image.image.file")
    ]


def test_a_version_read_in_full_judges_each_name_its_components_give(tmp_path: Path) -> None:
    """As the engine judges a name where it draws the image, and each file the version holds
    once, though a component names it."""
    root = project(tmp_path)
    copy_library(root, FOUNDATIONS, "foundations", "1.0.0")
    frames = add_library(root, FRAMES, "1.0.0", builds_on={"foundations": 1})
    mark = dict(MARK_COMPONENT)
    mark["parts"] = {**mark["parts"], "gone": {"image": {"file": "gone.png"}, "width": "=:width"}}
    write(frames / "components" / "mark.yaml", yaml_text(mark))
    held(frames, "mark.png", "deep.png")

    read = full_read.read(libraries.Held(root, "visual"), FRAMES, libraries.Version(1, 0, 0))

    assert [(f.code, f.file, f.where) for f in read.findings if f.code.startswith("picture-")] == [
        ("picture-encoding", f"{FRAMES_PICTURES}/mark.png", ""),
        ("picture-missing", f"{FRAMES_FOLDER}/components/mark.yaml", "parts.gone.image.file"),
    ]
    assert {f.library for f in read.findings if f.code.startswith("picture-")} == {"frames@1.0.0"}


def test_each_language_exports_its_own_file_and_every_other_picture_in_a_pdf(
    tmp_path: Path,
) -> None:
    """Each PDF draws, in the scene's order, the content's own file in its language, a PNG with
    a colour profile in English and a progressive JPEG in Czech; the piece's badge, a JPEG; the
    library's mark, a palette's PNG with a transparent colour; and the produced picture, from
    the variant that serves its combination. No image is a loss."""
    root = pictured_project(tmp_path, exports=["pdf"])
    variants = {"default": (200, 30, 30, 255), "colour-scheme.dark": (30, 60, 200, 128)}
    write_picture(root, framing, by_variant=variants)
    assert [f for f in checks.computed(project_of(root)) if f.code == "loss"] == []

    exported = run_main(export_script, PIECE, cwd=root)

    assert exported.returncode == 0, exported.stderr
    pictures, frames = root / PIECE_PICTURES, root / FRAMES_PICTURES
    mark = png.read((frames / "mark.png").read_bytes())
    own = {
        "en": (png.read((pictures / "photo.png").read_bytes()).data, None),
        "cs": ((pictures / "photo.jpg").read_bytes(), None),
    }
    for language in ("en", "cs"):
        for key, (red, green, blue, alpha) in variants.items():
            path = root / EXPORTS / f"{PIECE}.v1.{language}.{key}.pdf"
            produced = (bytes([red, green, blue]) * 100 * 100, bytes([alpha]) * 100 * 100)
            assert drawn_pictures(path) == [
                own[language],
                ((pictures / "badge.jpg").read_bytes(), None),
                (mark.data, png.palette_alpha(mark, png.samples(mark))),
                produced,
            ]
            assert (b"/ICCBased" in path.read_bytes()) == (language == "en")


# --- what refuses an export ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("change", "said"),
    [
        (lambda root: (root / PIECE_PICTURES / "badge.jpg").unlink(), "`badge.jpg`"),
        (lambda root: held(root / FRAMES_FOLDER, "mark.png", "deep.png"), "16 bits"),
    ],
    ids=["the-pieces-missing", "the-librarys-unreadable"],
)
def test_an_export_refuses_a_picture_file_missing_or_unreadable_and_writes_nothing(
    tmp_path: Path, change: Any, said: str
) -> None:
    root = pictured_project(tmp_path)
    change(root)
    before = every_file(root)

    shown = run_main(export_script, PIECE, cwd=root)

    assert shown.returncode == 1
    assert "a picture file the piece shows is missing or cannot be read: " in shown.stderr
    assert said in shown.stderr
    assert every_file(root) == before
    assert not (root / EXPORTS).exists()


# --- what a picture file changes ----------------------------------------------------------------


def test_a_changed_picture_file_makes_the_findings_record_stale(tmp_path: Path) -> None:
    root = pictured_project(tmp_path)
    assert run_main(render_script, PIECE, cwd=root).returncode == 0
    assert "the scenes of 1 read from their findings record" in check_document(root)["summary"][0]

    held(root / PIECE_FOLDER, "photo.png", "alpha.png")

    assert "the scenes of 0 read from their findings record" in check_document(root)["summary"][0]


def test_a_changed_picture_file_is_a_change_since_the_last_export(tmp_path: Path) -> None:
    root = pictured_project(tmp_path, released=True)
    assert run_main(export_script, PIECE, cwd=root).returncode == 0
    held(root / FRAMES_FOLDER, "mark.png", "grey.png")
    held(root / PIECE_FOLDER, "photo.png", "alpha.png")

    marked = run_main(mark_final_script, PIECE, "1", cwd=root)

    assert marked.returncode == 0, marked.stderr
    changed = [line for line in marked.stdout.splitlines() if line.startswith("changed since")]
    assert "changed since version 1: `pictures/photo.png` changed" in changed


def test_a_file_added_to_a_published_pieces_pictures_puts_its_copy_out_of_date(
    tmp_path: Path,
) -> None:
    root = pictured_project(tmp_path, state="published")
    assert run_main(export_script, PIECE, cwd=root).returncode == 0
    assert located(root, "current-copy-stale") == []

    held(root / PIECE_FOLDER, "spare.png", "alpha.png")

    [stale] = [
        each for each in check_document(root)["findings"] if each["label"] == "current-copy-stale"
    ]
    assert stale["severity"] == "error"
    assert "`pictures/spare.png`" in stale["message"]
