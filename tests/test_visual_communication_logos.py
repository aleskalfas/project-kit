"""A brand's logo, the picture role `picture.logo`, which a part shows by `role` (visual-
communication DEC-025 points 1, 4, 7 and 9; #2858).

First drawn by the engine from components written as mappings in memory and read through
the in-memory `Env` (`tests/visual_engine.py`), whose picture roles `logos` gives:

- an image of a picture role: what the scene holds of it, the role as its role and its
  source the brand's value; no file, no variants and no points;
- its height its file's proportions where none is given, and any frame drawing it whole;
- a role the brand gives no file: the part not drawn, at zero size, and no finding;
- a role that names no role, and one of another type, each a finding in the component.

Then one piece of a project of its own, `masthead`, under the brand `test-logo`, which gives a
light logo and a dark one (`tests/visual_communication_logo.py`), and shows it beside a
picture file of the piece and a produced picture (`logo_project`):

- what a renderer is handed for each image in each combination, from one scene;
- the logo of each colour scheme drawn in a preview, in an SVG and an HTML export, and in a
  look; a page file of both schemes drawing the light one and reporting the dark one;
- a phone's own logo, at its own proportions;
- a brand that gives none, a base's logo kept, and an edition's own where the base opens it;
- what the check finds of a brand's logo, and where: in the brand's version, or at the lock
  where only the lock's combination shows it; a formula and a paint that read the role;
- an export refused over a logo missing or unreadable, writing nothing;
- the logo drawn in a before-and-after, whose location git ignores.
"""

from __future__ import annotations

import base64
import json
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tests import visual_communication_logo as logo
from tests import visual_communication_producer as producer
from tests.in_process import load, run_main
from tests.test_visual_communication_pipeline import DEVICE, NARROW, TESTS, every_file
from tests.visual_communication_project import (
    FOUNDATIONS,
    TEST_EDITION,
    TEST_PICTURES,
    bound,
    copy_library,
    importable,
    project,
    write,
    write_list,
    write_piece,
    yaml_text,
)
from tests.visual_engine import codes, draw, frame, top
from tests.visual_engine import findings as engine_findings

(
    export_script,
    render_script,
    check_script,
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
    before_after,
    code,
    css_writer,
    json_writer,
    files,
) = load(
    "visual-communication",
    "export.py",
    "render.py",
    "check.py",
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
    "before_after",
    "code",
    "plugins.css",
    "plugins.json",
    "files",
)


def image(source: dict[str, Any], **geometry: Any) -> dict[str, Any]:
    """An image part of `source`, as wide as its component."""
    return {"image": source, "width": "=:width", **geometry}


def shown(tmp_path: Path, file: bytes | None, parts: dict[str, Any] | None = None) -> Any:
    """The scene of a top whose parts are `parts`, by default an image of `picture.logo`,
    the brand giving it `file`, or none where None."""
    given = None
    if file is not None:
        given = tmp_path / "logo.png"
        given.write_bytes(file)
    parts = parts if parts is not None else {"i": image({"role": "picture.logo"})}
    return draw(components={"lab/top": top(parts)}, logos={"picture.logo": given})


# --- an image of a picture role -----------------------------------------------------------------


def test_the_scene_keeps_the_role_as_its_role_and_holds_no_file(tmp_path: Path) -> None:
    result = shown(tmp_path, logo.logo())

    assert result.findings == []
    element = result.scene.find("top/i")
    assert element is not None
    assert element.properties["role"] == "picture.logo"
    assert element.sources["role"] == "role:picture.logo"
    assert element.properties["preserveAspectRatio"] == "xMidYMid meet"
    for held in ("file", "library", "output", "variants", "points"):
        assert held not in element.properties


def test_its_height_is_its_files_proportions_and_any_frame_draws_it_whole(tmp_path: Path) -> None:
    # The light logo is 160 × 48 pixels, so 640 across makes 192 down; twice the pixels
    # at the same proportion makes the same.
    assert frame(shown(tmp_path, logo.logo()), "top/i")[3] == 192
    assert frame(shown(tmp_path, logo.logo(2, dark=True)), "top/i")[3] == 192
    framed = shown(
        tmp_path, logo.logo(), {"i": image({"role": "picture.logo"}, height="=@space.4")}
    )
    assert framed.findings == []
    assert frame(framed, "top/i")[2:] == (640, 32)


def test_a_role_the_brand_gives_no_file_is_not_drawn_and_takes_no_finding(tmp_path: Path) -> None:
    parts = {
        "i": image({"role": "picture.logo"}),
        "after": {"box": {}, "y": "=i.bottom", "width": "=@space.2", "height": "=@space.2"},
    }
    result = shown(tmp_path, None, parts)

    assert result.findings == []
    assert result.scene.find("top/i") is None
    assert frame(result, "top/after")[1] == 0


@pytest.mark.parametrize(
    ("role", "code", "said"),
    [
        ("picture.mark", "unknown-role", "declares the role @picture.mark"),
        ("type.body", "role-type", "the role @type.body is not a picture"),
    ],
    ids=["no-role", "of-another-type"],
)
def test_a_role_that_names_no_picture_role_is_a_finding_in_the_component(
    tmp_path: Path, role: str, code: str, said: str
) -> None:
    result = shown(tmp_path, logo.logo(), {"i": image({"role": role})})

    assert codes(result) == [code]
    [found] = result.findings
    assert found.level == engine_findings.FAILS
    assert found.where == "parts.i.image.role"
    assert said in found.message
    assert result.scene.find("top/i") is None


# --- a piece of a project -----------------------------------------------------------------------


#: The piece, and the libraries its lock names.
PIECE = "masthead"
PIECE_FOLDER = f"visual/pieces/{PIECE}"
BRAND_FOLDER = f"visual/libraries/{logo.NAME}/{logo.VERSION}"
LOCK = {"foundations": "1.0.0", logo.NAME: logo.VERSION, "tests": "1.0.0"}
OUTPUT = "square"
#: Where the piece's exports and previews lie, local to the clone.
LOCAL = ".pkit/capabilities/visual-communication/project/local"
EXPORTS = f"{LOCAL}/exports/{PIECE}"
PREVIEWS = f"{LOCAL}/previews/{PIECE}"

#: Each image of the piece, by its trace id.
LOGO = "figure/body/steps[logo]/image"
SHOT = "figure/body/steps[shot]/image"
NOTE = "figure/body/steps[note]/pictures[square]/image"


def component(about: str, source: dict[str, str], **fields: Any) -> dict[str, Any]:
    """A component of one image as wide as it is given, which takes `fields`."""
    return bound(
        "component",
        status="experimental",
        about=about,
        fields={"type": "object", "required": sorted(fields), "properties": fields},
        parts={"image": {"image": source, "width": "=:width"}},
        preferred={"height": "=image.height"},
    )


#: The piece's own component that shows the brand's logo.
LOGO_COMPONENT = component("The brand's logo.", {"role": "picture.logo"})
#: The piece's own component that shows the picture file of the piece the content names.
SHOT_COMPONENT = component(
    "A picture file of the piece, which the content names.",
    {"content": "photo"},
    photo={"type": "string", "description": "The bare name of a picture file of the piece."},
)

#: The piece's content: the logo, a picture file of the piece, and a callout over the
#: produced picture.
CONTENT = {
    "body": {
        "use": "tests/steps",
        "steps": [
            {"id": "logo", "use": "piece/logo"},
            {"id": "shot", "use": "piece/shot", "photo": "photo.png"},
            {
                "id": "note",
                "use": "tests/callout",
                "pictures": [{"id": OUTPUT, "output": OUTPUT}],
                "label": "Here",
                "at": {"item": OUTPUT, "point": "tip"},
            },
        ],
    },
    "caption": "The masthead.",
}


def list_libraries(root: Path, **more: str) -> None:
    """The list of the shipped foundations, the `tests` library, and the brands the location
    holds, each version unreleased."""
    sources = {"foundations": "shipped", "tests": "project", logo.NAME: "project", **more}
    write_list(
        root,
        {
            name: {
                "source": {"kind": kind},
                "versions": {
                    folder.name: {"released": False}
                    for folder in sorted((root / "visual" / "libraries" / name).iterdir())
                },
            }
            for name, kind in sources.items()
        },
    )


def write_produced(root: Path) -> None:
    """The callout's picture as `pkit visual produce` keeps it, written directly: a red PNG
    for each variant, exposing `tip`, and its record."""
    plan = framing.plan(root, "visual", PIECE, OUTPUT)
    folder = root / PIECE_FOLDER / "produced" / OUTPUT
    folder.mkdir(parents=True, exist_ok=True)
    data = producer.png(100, 100, (200, 30, 30, 255))
    digests = {}
    for key in plan.variants:
        (folder / f"{key}.png").write_bytes(data)
        digests[key] = reading.sha256(data)
    tip = {key: {"x": 75, "y": 25} for key in plan.variants}
    checked = framing.Checked(digests=digests, points={"tip": tip}, programs={})
    record = folder / "record.yaml"
    record.write_text(framing.record_text(framing.record_of(plan, checked)), encoding="utf-8")


def logo_project(
    tmp_path: Path,
    *,
    light: bool = True,
    dark: bool = True,
    device: bool = False,
    **fields: Any,
) -> Path:
    """The piece `masthead` under the brand `test-logo` (`logo.logo_brand`), in both colour
    schemes, exported as SVG unless `fields` say otherwise: its steps the brand's logo, a
    picture file of the piece, a PNG, and a callout over the produced picture `square`.
    With `device`, the foundations hold the size axis `device`, and the brand gives a
    phone its own logo (`add_device`)."""
    root = project(tmp_path)
    copy_library(root, FOUNDATIONS, "foundations", "1.0.0")
    copy_library(root, TESTS, "tests", "1.0.0")
    logo.logo_brand(root, light=light, dark=dark)
    if device:
        add_device(root)
    list_libraries(root)
    piece = {
        "brand": logo.NAME,
        "lock": dict(LOCK),
        "modes": {"colour-scheme": ["light", "dark"]},
        "exports": ["svg"],
        "produced": {
            OUTPUT: {
                "producer": producer.NAME,
                "inputs": {"fill": "accent"},
                "pixels": {"width": 100, "height": 100},
            }
        },
        **fields,
    }
    write_piece(root, PIECE, **piece)
    folder = root / PIECE_FOLDER
    write(folder / "components" / "logo.yaml", yaml_text(LOGO_COMPONENT))
    write(folder / "components" / "shot.yaml", yaml_text(SHOT_COMPONENT))
    logo.hold(folder, "photo.png", (TEST_PICTURES / "palette.png").read_bytes())
    write(folder / "content.en.yaml", yaml_text(bound("content", **CONTENT)))
    write_produced(root)
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
    piece = pl.read_piece(root, "visual", PIECE)
    return pl.Project(piece, piece.lock, pl.Held(root, "visual"))


def scenes_of(project: Any) -> list[tuple[str, Any]]:
    return project.scenes(facts=project.piece.stand_ins)


def data_of(path: Path) -> str:
    """The data a renderer embeds of the PNG at `path`."""
    return f"data:image/png;base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def failing(found: list[Any]) -> list[Any]:
    return [finding for finding in found if finding.level == engine_findings.FAILS]


def check_document(root: Path) -> dict[str, Any]:
    shown = run_main(check_script, "--json", cwd=root, env={"PKIT_COMMAND_DEADLINE": None})
    assert shown.returncode == 0, shown.stderr
    return json.loads(shown.stdout)


def located(root: Path, label: str) -> list[tuple[str, str]]:
    """The severity and location of each finding of `label` the check gives."""
    return [
        (each["severity"], each["location"])
        for each in check_document(root)["findings"]
        if each["label"] == label
    ]


def test_one_scene_hands_each_mode_its_own_logo_beside_a_picture_file_and_a_produced_one(
    tmp_path: Path,
) -> None:
    root = logo_project(tmp_path)
    project = project_of(root)

    [(_, result)] = scenes_of(project)

    assert failing(result.findings) == []
    scene = result.scene.to_dict()
    brand = root / BRAND_FOLDER / "pictures"
    photo = root / PIECE_FOLDER / "pictures" / "photo.png"
    produced = root / PIECE_FOLDER / "produced" / OUTPUT
    assert project.env.handed(scene, "default") == {
        LOGO: seam.Shown(brand / logo.LIGHT, seam.PNG),
        SHOT: seam.Shown(photo, seam.PNG),
        NOTE: seam.Shown(produced / "default.png", seam.PNG),
    }
    assert project.env.handed(scene, "colour-scheme.dark") == {
        LOGO: seam.Shown(brand / logo.DARK, seam.PNG),
        SHOT: seam.Shown(photo, seam.PNG),
        NOTE: seam.Shown(produced / "colour-scheme.dark.png", seam.PNG),
    }
    [element] = [each for each in pl._images(scene["children"]) if each["id"] == LOGO]
    assert element["role"] == "picture.logo"
    assert element["sources"]["role"] == "role:picture.logo"


def test_the_document_of_values_gives_the_engine_each_modes_logo(tmp_path: Path) -> None:
    held = project_of(logo_project(tmp_path)).values()

    assert held["version"] == 2
    assert held["tokens"]["picture.logo"] == {
        "type": "picture",
        "values": {
            "default": {"file": logo.LIGHT, "library": logo.NAME},
            "colour-scheme.dark": {"file": logo.DARK, "library": logo.NAME},
        },
    }


def logos_of(root: Path) -> tuple[Path, Path]:
    """The brand's light logo and its dark one."""
    folder = root / BRAND_FOLDER / "pictures"
    return folder / logo.LIGHT, folder / logo.DARK


def test_each_modes_logo_draws_in_a_preview_and_an_svg_and_an_html_export(tmp_path: Path) -> None:
    root = logo_project(tmp_path, exports=["svg", "html"])
    light, dark = logos_of(root)
    assert run_main(render_script, PIECE, cwd=root).returncode == 0
    exported = run_main(export_script, PIECE, cwd=root)
    assert exported.returncode == 0, exported.stderr

    for key, own, other in (("default", light, dark), ("colour-scheme.dark", dark, light)):
        drawn = [
            (root / PREVIEWS / f"{PIECE}.en.{key}.svg").read_text(encoding="utf-8"),
            (root / EXPORTS / f"{PIECE}.v1.en.{key}.svg").read_text(encoding="utf-8"),
        ]
        for text in drawn:
            assert data_of(own) in text
            assert data_of(other) not in text
            assert data_of(root / PIECE_FOLDER / "pictures" / "photo.png") in text
    page = (root / EXPORTS / f"{PIECE}.v1.en.default.html").read_text(encoding="utf-8")
    assert data_of(light) in page and data_of(dark) not in page


def test_a_look_draws_each_modes_logo_and_loses_none(tmp_path: Path) -> None:
    """A renderer handed no file for the logo in a key reports it as a loss, so a look of
    each key that reports none drew each key's logo."""
    root = logo_project(tmp_path)

    looked = run_main(look_script, PIECE, "--every-key", cwd=root)

    assert looked.returncode == 0, looked.stderr
    folder = root / viewing.FOLDER / PIECE
    report = json.loads((folder / viewing.REPORT).read_text(encoding="utf-8"))
    assert [image["key"] for image in report["images"]] == ["default", "colour-scheme.dark"]
    assert report["losses"] == []
    for image in report["images"]:
        frames = json.loads((folder / image["frames"]).read_text(encoding="utf-8"))
        assert LOGO in json.dumps(frames)


def test_a_page_file_of_both_schemes_draws_the_light_logo_and_reports_the_dark_one(
    tmp_path: Path,
) -> None:
    """The page draws the first key's picture, until a page holds each mode's (DEC-023
    point 8)."""
    project = project_of(logo_project(tmp_path, exports=["html"]))

    [(_, held, drawn)] = list(pl.drawn(project, scenes_of(project), "html"))

    assert held == ("default", "colour-scheme.dark")
    assert [loss.as_dict() for loss in drawn.losses if loss.what == LOGO] == [
        {
            "plugin": "html",
            "what": LOGO,
            "did": "approximated",
            "why": "the page draws the picture of `default` of the picture role `picture.logo`, "
            "and `colour-scheme.dark` takes another",
            "key": "colour-scheme.dark",
        }
    ]


# --- by size, and by brand ----------------------------------------------------------------------


def add_device(root: Path) -> Path:
    """The size axis `device` on the foundations the project holds, which the brand
    `test-logo` varies: its mode `phone` gives the tokens of a phone's own file, a narrower
    figure and a phone's own logo, the mark alone (`logo.give_phone`). The brand's folder."""
    roles = root / "visual/libraries/foundations/1.0.0/roles.yaml"
    text = roles.read_text(encoding="utf-8")
    roles.write_text(text.replace("axes:\n", f"axes:\n  {DEVICE}\n", 1), encoding="utf-8")
    brand = root / BRAND_FOLDER
    write(brand / logo.PHONE_FILE, json.dumps(NARROW, indent=2))
    resolver = brand / "test-brand.resolver.json"
    data = json.loads(resolver.read_text(encoding="utf-8"))
    data["modifiers"]["device"] = {
        "contexts": {"desktop": [], "phone": [{"$ref": logo.PHONE_FILE}]},
        "default": "desktop",
    }
    data["resolutionOrder"].append({"$ref": "#/modifiers/device"})
    resolver.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logo.give_phone(brand)
    return brand


def logo_of(result: Any) -> Any:
    element = result.scene.find(LOGO)
    assert element is not None, f"no {LOGO}"
    return element


def test_a_phone_takes_its_own_logo_at_its_own_proportions(tmp_path: Path) -> None:
    root = logo_project(
        tmp_path,
        device=True,
        modes={"colour-scheme": ["light", "dark"], "device": ["desktop", "phone"]},
    )
    brand = root / BRAND_FOLDER / "pictures"
    project = project_of(root)

    results = dict((result.scene.size_key, result) for _, result in scenes_of(project))

    assert sorted(results) == ["default", "device.phone"]
    assert [failing(result.findings) for result in results.values()] == [[], []]
    phone = results["device.phone"].scene.to_dict()
    for key in ("device.phone", "colour-scheme.dark+device.phone"):
        assert project.env.handed(phone, key)[LOGO] == seam.Shown(brand / logo.PHONE, seam.PNG)
    desktop = logo_of(results["default"]).properties
    assert desktop["height"] == desktop["width"] * 48 / 160
    small = logo_of(results["device.phone"]).properties
    assert small["height"] == small["width"]


def test_under_a_brand_that_gives_no_logo_the_part_is_not_drawn_and_no_piece_takes_a_finding(
    tmp_path: Path,
) -> None:
    root = logo_project(tmp_path, light=False, dark=False)
    project = project_of(root)

    [(_, result)] = scenes_of(project)

    assert result.scene.find(LOGO) is None
    shot = result.scene.find(SHOT)
    assert shot is not None
    piece = [each for each in check_document(root)["findings"] if each["severity"] != "info"]
    assert [each for each in piece if each["location"].startswith(PIECE_FOLDER)] == []
    assert [
        each["label"]
        for each in check_document(root)["findings"]
        if each["label"].startswith("picture-")
    ] == ["picture-role-unvalued"]


#: The edition the tests build on the brand `test-logo`.
EDITION = "test-logo-edition"
EDITION_FOLDER = f"visual/libraries/{EDITION}/1.0.0"


def edition_of(root: Path, *, opened: bool) -> Path:
    """The edition `test-logo-edition` 1.0.0, a copy of the test edition built on the brand
    `test-logo` in place of the test brand, and the piece drawn under it; the base opening
    `picture.logo` to it where `opened`. The edition's folder."""
    folder = copy_library(root, TEST_EDITION, EDITION, "1.0.0")
    library = folder / "library.yaml"
    text = library.read_text(encoding="utf-8").replace("name: test-edition", f"name: {EDITION}")
    library.write_text(text.replace("name: test-brand,", f"name: {logo.NAME},"), encoding="utf-8")
    if opened:
        base = root / BRAND_FOLDER / "library.yaml"
        text = base.read_text(encoding="utf-8")
        base.write_text(
            text.replace("open: [accent, space]", "open: [accent, space, picture.logo]"),
            encoding="utf-8",
        )
    list_libraries(root, **{EDITION: "project"})
    piece = root / PIECE_FOLDER / "piece.yaml"
    data = reading.read_yaml(piece)
    data.update(brand=EDITION, lock={**LOCK, EDITION: "1.0.0"})
    write(piece, yaml_text(data))
    return folder


def handed_logos(root: Path) -> list[Any]:
    """The file each combination's scene hands a renderer for the logo, in key order."""
    project = project_of(root)
    [(_, result)] = scenes_of(project)
    scene = result.scene.to_dict()
    return [project.env.handed(scene, key).get(LOGO) for key in project.keys]


def test_a_brand_built_on_a_base_keeps_its_bases_logo(tmp_path: Path) -> None:
    root = logo_project(tmp_path)
    edition_of(root, opened=False)
    light, dark = logos_of(root)

    assert handed_logos(root) == [seam.Shown(light, seam.PNG), seam.Shown(dark, seam.PNG)]


def test_where_the_base_opens_the_logo_the_editions_own_draws(tmp_path: Path) -> None:
    root = logo_project(tmp_path)
    edition = edition_of(root, opened=True)
    logo.giving(edition, "tokens/edition.tokens.json", "edition.png")
    own = logo.hold(edition, "edition.png", logo.logo())

    assert handed_logos(root) == [seam.Shown(own, seam.PNG)] * 2
    assert [f for f in failing(checks.computed(project_of(root)))] == []


# --- what the check finds -----------------------------------------------------------------------


def test_a_dark_logo_at_twice_the_pixels_takes_no_finding(tmp_path: Path) -> None:
    root = logo_project(tmp_path)

    found = check_document(root)["findings"]

    assert [each for each in found if each["severity"] == "error"] == []
    assert [each for each in found if each["label"].startswith("picture-")] == []


@pytest.mark.parametrize(
    ("change", "label", "said"),
    [
        (
            lambda root: logo.giving(root / BRAND_FOLDER, logo.BASE_FILE, None),
            "picture-role-modes",
            "a file in `colour-scheme.dark`, `colour-scheme.dark+contrast.high`, and none in "
            "`default`, `contrast.high`",
        ),
        (
            lambda root: logo.hold(root / BRAND_FOLDER, logo.DARK, logo.mark(96, dark=True)),
            "picture-role-proportion",
            "`logo.png`, 160 × 48 pixels, in `default`; `logo-dark.png`, 96 × 96 pixels, in "
            "`colour-scheme.dark`",
        ),
    ],
    ids=["in-some-value-modes", "of-two-proportions"],
)
def test_a_logo_given_in_some_value_modes_or_at_two_proportions_fails_in_the_brand(
    tmp_path: Path, change: Any, label: str, said: str
) -> None:
    root = logo_project(tmp_path)
    change(root)

    [found] = [each for each in check_document(root)["findings"] if each["label"] == label]

    assert (found["severity"], found["location"]) == ("error", f"{BRAND_FOLDER}/#picture.logo")
    assert said in found["message"]


def opening(folder: Path) -> None:
    """The brand at `folder` opening `picture.logo` to a brand built on it."""
    library = folder / "library.yaml"
    text = library.read_text(encoding="utf-8")
    library.write_text(
        text.replace("open: [accent, space]", "open: [accent, space, picture.logo]"),
        encoding="utf-8",
    )


def test_a_fault_only_the_locks_combination_of_a_base_and_an_edition_shows_lies_at_the_lock(
    tmp_path: Path,
) -> None:
    """The edition gives its own dark logo over its base's light one. Checked alone, with
    the newest base, whose logo is of the dark one's proportion, it holds. Under the lock's
    older base, whose logo is the square mark, the two proportions differ (DEC-025 point 9,
    DEC-008 point 9)."""
    root = logo_project(tmp_path)
    old = root / BRAND_FOLDER
    logo.giving(old, logo.BASE_FILE, "mark.png")
    logo.hold(old, "mark.png", logo.mark())
    logo.giving(old, logo.DARK_FILE, None)
    newer = logo.logo_brand(root, dark=False, version="1.1.0")
    for base in (old, newer):
        opening(base)
    edition = edition_of(root, opened=True)
    logo.giving(edition, "tokens/dark.tokens.json", "edition-dark.png")
    logo.hold(edition, "edition-dark.png", logo.logo(2, dark=True))
    list_libraries(root, **{EDITION: "project"})

    found = [
        each for each in check_document(root)["findings"] if each["label"].startswith("picture-")
    ]

    assert [(each["label"], each["severity"], each["location"]) for each in found] == [
        ("picture-role-proportion", "error", f"{PIECE_FOLDER}/piece.yaml#lock")
    ]
    assert "`mark.png`, 48 × 48 pixels, in `default`" in found[0]["message"]


@pytest.mark.parametrize("given", [True, False], ids=["given", "not-given"])
def test_a_formula_and_a_paint_that_read_the_logo_take_a_finding_whether_given_or_not(
    tmp_path: Path, given: bool
) -> None:
    """A part reads no value from a picture role (`components.md`, "Errors"): a formula
    takes `unknown-role`, and a paint, which reads no colour from it, `unknown-colour`."""
    root = logo_project(tmp_path, light=given, dark=given)
    reading_it = bound(
        "component",
        status="experimental",
        about="A box that reads the logo.",
        fields={"type": "object", "properties": {}},
        parts={
            "sized": {"box": {"fill": "surface"}, "width": "=@picture.logo", "height": "=@space.1"},
            "painted": {
                "box": {"fill": "picture.logo"},
                "width": "=@space.1",
                "height": "=@space.1",
            },
        },
        preferred={"height": "=@space.1"},
    )
    write(root / PIECE_FOLDER / "components" / "logo.yaml", yaml_text(reading_it))

    found = failing(checks.computed(project_of(root)))

    assert sorted((f.code, f.where) for f in found) == [
        ("unknown-colour", "figure/body/steps[logo]/painted"),
        ("unknown-role", "@picture.logo"),
    ]
    assert all("picture.logo" in f.message for f in found)


# --- what refuses an export ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("change", "said"),
    [
        (lambda root: (root / BRAND_FOLDER / "pictures" / logo.DARK).unlink(), "`logo-dark.png`"),
        (
            lambda root: logo.hold(
                root / BRAND_FOLDER, logo.LIGHT, (TEST_PICTURES / "deep.png").read_bytes()
            ),
            "16 bits",
        ),
    ],
    ids=["missing", "unreadable"],
)
def test_an_export_refuses_a_logo_missing_or_unreadable_and_writes_nothing(
    tmp_path: Path, change: Any, said: str
) -> None:
    root = logo_project(tmp_path)
    change(root)
    before = every_file(root)

    shown = run_main(export_script, PIECE, cwd=root)

    assert shown.returncode == 1
    assert "a picture file the piece shows is missing or cannot be read: " in shown.stderr
    assert said in shown.stderr
    assert every_file(root) == before
    assert not (root / EXPORTS).exists()


# --- a before-and-after -------------------------------------------------------------------------


def test_a_before_and_after_draws_the_logo_from_a_location_git_ignores(tmp_path: Path) -> None:
    """A before-and-after builds each side's location in the clone's local folder, which git
    ignores, so it finds the brand's logo as it lies there (`before_after`)."""
    root = logo_project(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    write(root / ".pkit" / ".gitignore", "capabilities/visual-communication/project/local/\n")
    light, dark = logos_of(root)
    piece = pl.read_piece(root, "visual", PIECE)

    side = before_after.drawing(root, "visual", PIECE, LOCK, facts=piece.stand_ins)

    assert side.why == ""
    assert data_of(light) in side.files[f"{PIECE}.en.default.svg"]
    assert data_of(dark) in side.files[f"{PIECE}.en.colour-scheme.dark.svg"]


# --- written code -------------------------------------------------------------------------------


#: The declaration the tests run.
DECLARED = "brand-code"


def code_project(
    tmp_path: Path,
    writer: str,
    form: int = 1,
    *,
    given: bool = True,
    accepted: list[dict[str, str]] | None = None,
) -> Path:
    """A project holding the foundations and the brand `test-logo`, giving its logos unless
    `given` is false, and the declaration of `writer` in `form` under it, accepting the
    losses `accepted` where given."""
    root = project(tmp_path)
    copy_library(root, FOUNDATIONS, "foundations", "1.0.0")
    logo.logo_brand(root, light=given, dark=given)
    out = "web/brand.css" if writer == "css" else "web/brand.json"
    lock = {"foundations": "1.0.0", logo.NAME: logo.VERSION}
    declared: dict[str, Any] = {
        "writer": writer,
        "form": form,
        "brand": logo.NAME,
        "lock": lock,
        "out": out,
    }
    if accepted is not None:
        declared["accept-losses"] = accepted
    write(
        root / "visual" / "code" / f"{DECLARED}.yaml",
        yaml_text(bound("code", **declared)),
    )
    return root


@pytest.fixture
def writers(monkeypatch: pytest.MonkeyPatch) -> None:
    """The code writers stand in for the import a run makes, for the length of the test."""
    importable(monkeypatch, css_writer, json_writer)


@pytest.mark.parametrize(
    ("writer", "said"),
    [
        ("css", "form 1 of the css writer has no form for a picture value"),
        ("json", "form 1 of the json writer has no form for a picture value"),
    ],
)
def test_the_css_writer_and_the_json_writers_form_1_report_the_logo_as_a_loss_known_before(
    tmp_path: Path, writers: None, writer: str, said: str
) -> None:
    root = code_project(tmp_path, writer)

    planned = code.plan(root, "visual", code.read(root, "visual", DECLARED))

    assert "picture.logo" not in planned.document["tokens"]
    [lost] = [loss for loss in planned.losses if loss.what == "picture.logo"]
    assert (lost.plugin, lost.did, lost.why) == (writer, seam.LEFT_OUT, said)
    written = code.write(root, "visual", DECLARED)
    text = (root / written.code).read_text(encoding="utf-8")
    unpictured = code_project(tmp_path / "unpictured", writer, given=False)
    code.write(unpictured, "visual", DECLARED)
    assert text == (unpictured / written.code).read_text(encoding="utf-8")
    [finding] = [f for f in code.findings(root, "visual") if f.where == "picture.logo"]
    assert (finding.code, finding.level) == ("code-loss", "attention")
    accepted = [{"plugin": writer, "what": "picture.logo", "reason": "Pages show no logo."}]
    root = code_project(tmp_path / "accepted", writer, accepted=accepted)
    code.write(root, "visual", DECLARED)
    assert [f for f in code.findings(root, "visual") if f.where == "picture.logo"] == []


def test_the_json_writers_form_2_writes_the_logo_of_each_mode(
    tmp_path: Path, writers: None
) -> None:
    root = code_project(tmp_path, "json", form=2)

    written = code.write(root, "visual", DECLARED)

    assert [loss for loss in written.losses if loss.what == "picture.logo"] == []
    held = json.loads((root / written.code).read_bytes())
    assert held["version"] == 2
    assert held["tokens"]["picture.logo"]["values"] == {
        "default": {"file": logo.LIGHT, "library": logo.NAME},
        "colour-scheme.dark": {"file": logo.DARK, "library": logo.NAME},
        "contrast.high": {"file": logo.LIGHT, "library": logo.NAME},
        "colour-scheme.dark+contrast.high": {"file": logo.DARK, "library": logo.NAME},
    }
    assert files.shape_problems(held, "values-2") == []
    assert [f for f in code.findings(root, "visual") if f.where == "picture.logo"] == []
