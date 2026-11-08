"""What a command that moves a piece's lock onto another brand names (visual-communication
DEC-025 point 8; #2859).

One piece, in English and Czech, under one of two brands: the test brand, which gives no logo,
or `test-logo`, which gives one (`tests/visual_communication_logo.py`). Its steps show a picture
file of the piece its content names, another in each language; the piece's own badge, which a
local component names by `file`; the brand's logo, `picture.logo`; the mark of the library
`frames`, a file of its own version; and the produced picture `square` (`branded_project`).

- **A move onto another brand** names each picture file of the piece a scene shows, in each
  language, and each picture role a part shows that the new brand gives no file, each with its
  image's trace id. It names neither the library's own file nor the produced picture.
- **Who says it.** The render of a draft that is not pinned, `pkit visual upgrade`, and
  `pkit visual mark-final` where the lock it puts back names another brand. The before-and-after
  says the same, looking ahead or back, wherever its two locks name different brands.
- **A move that keeps the brand** says none of it. No record keeps what a move says, and the
  check is silent on it.

Run in this process, the SVG renderer standing in for the import a run makes when it draws, the
test producer registered, and `pkit` answered in this process. A look back runs in a git
repository of the test's own.
"""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tests import visual_communication_logo as logo
from tests import visual_communication_producer as producer
from tests.in_process import load, route_pkit, run_main
from tests.test_visual_communication_before_after import git
from tests.test_visual_communication_logos import LOGO_COMPONENT
from tests.test_visual_communication_picture_files import (
    BADGE_COMPONENT,
    FRAMES,
    MARK_COMPONENT,
    SHOT_COMPONENT,
)
from tests.test_visual_communication_pipeline import (
    PIECE,
    PIECE_FOLDER,
    content,
    drawing_project,
    list_drawing_libraries,
    write_content,
    write_picture,
)
from tests.visual_communication_project import (
    TEST_PICTURES,
    add_library,
    importable,
    write,
    yaml_text,
)

(
    render_script,
    upgrade_script,
    before_after_script,
    mark_final_script,
    export_script,
    check_script,
    svg,
    seam,
    framing,
    backbone,
    reading,
    rebranding,
    scene,
    pl,
) = load(
    "visual-communication",
    "render.py",
    "upgrade.py",
    "before-after.py",
    "mark-final.py",
    "export.py",
    "check.py",
    "plugins.svg",
    "plugins.seam",
    "framing",
    "backbone",
    "reading",
    "rebranding",
    "scene",
    "pipeline",
)

#: The two brands: the test brand gives no logo, and `test-logo` gives one.
PLAIN = "test-brand"
LOGO_BRAND = logo.NAME

PIECE_FILE = f"{PIECE_FOLDER}/piece.yaml"
FINDINGS = f"{PIECE_FOLDER}/findings.yaml"

#: Each image of the piece, by its trace id.
SHOT = "figure/body/steps[shot]/image"
BADGE = "figure/body/steps[badge]/image"
LOGO = "figure/body/steps[logo]/image"
MARK = "figure/body/steps[mark]/image"
NOTE = "figure/body/steps[note]/pictures[square]/image"

#: The picture file of the piece each language's content names.
PHOTOS = {"en": "photo.png", "cs": "photo.jpg"}


def lock_of(brand: str) -> dict[str, str]:
    """The piece's lock under `brand`."""
    return {"foundations": "1.0.0", brand: "1.0.0", "tests": "1.0.0", FRAMES: "1.0.0"}


def versions(lock: dict[str, str]) -> str:
    """A lock in words, as a run says it."""
    return ", ".join(f"{library} {lock[library]}" for library in sorted(lock))


def steps(photo: str) -> list[dict[str, Any]]:
    """The piece's steps: a card, the content's picture file `photo`, the piece's badge, the
    brand's logo, the library's mark, and the callout over the produced picture."""
    return [
        {"id": "plan", "head": "Plan the work."},
        {"id": "shot", "use": "piece/shot", "photo": photo},
        {"id": "badge", "use": "piece/badge"},
        {"id": "logo", "use": "piece/logo"},
        {"id": "mark", "use": f"{FRAMES}/mark"},
        content()["body"]["steps"][2],
    ]


def held(folder: Path, name: str, source: str) -> None:
    """The test picture `source` held in `folder`'s `pictures/` as `name`."""
    target = folder / "pictures" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(TEST_PICTURES / source, target)


def listed(root: Path, released: bool) -> None:
    """The list of every library the project holds, released or not."""
    list_drawing_libraries(root, released=released, **{FRAMES: "project", LOGO_BRAND: "project"})


def branded_project(tmp_path: Path, brand: str, **fields: Any) -> Path:
    """The drawing project in English and Czech under `brand`, its picture made: its steps
    show the content's picture file, a PNG in English and a JPEG in Czech; the piece's own
    badge, a JPEG its local component names; the brand's logo; the mark of the library
    `frames`, a PNG of its own version; and the produced picture. It holds both brands, and
    lists every library released where the piece is published."""
    released = fields.get("state") == "published"
    root = drawing_project(
        tmp_path, languages=["en", "cs"], brand=brand, lock=lock_of(brand), **fields
    )
    logo.logo_brand(root)
    frames = add_library(root, FRAMES, "1.0.0", builds_on={"foundations": 1})
    write(frames / "components" / "mark.yaml", yaml_text(MARK_COMPONENT))
    held(frames, "mark.png", "palette.png")
    listed(root, released)
    piece = root / PIECE_FOLDER
    write(piece / "components" / "shot.yaml", yaml_text(SHOT_COMPONENT))
    write(piece / "components" / "badge.yaml", yaml_text(BADGE_COMPONENT))
    write(piece / "components" / "logo.yaml", yaml_text(LOGO_COMPONENT))
    held(piece, "photo.png", "palette.png")
    held(piece, "photo.jpg", "progressive.jpg")
    held(piece, "badge.jpg", "colour.jpg")
    for language, photo in PHOTOS.items():
        write_content(root, language, body={"use": "tests/steps", "steps": steps(photo)})
    write_picture(root, framing)
    return root


@pytest.fixture(autouse=True)
def plugins(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The renderer stands in for the import a run makes when it draws, the test producer is
    registered, and `pkit` is answered in this process, for the length of the test."""
    importable(monkeypatch, svg)
    producer.register(seam)
    route_pkit(monkeypatch, backbone)
    yield
    seam.unregister(producer.NAME)


def lines(script: Any, root: Path, *args: str) -> list[str]:
    """What a run of `script` that succeeds prints, a line each."""
    done = run_main(script, *args, cwd=root)
    assert done.returncode == 0, done.stderr
    return done.stdout.splitlines()


def said(shown: list[str]) -> list[str]:
    """What a run says of a move onto another brand, a line each."""
    return [line for line in shown if line.startswith(("another brand:", "not following"))]


def rebrand(root: Path, brand: str) -> None:
    """The piece's `brand` set to `brand`, as a person edits it."""
    path = root / PIECE_FILE
    data = reading.read_yaml(path)
    data["brand"] = brand
    path.write_text(yaml_text(data), encoding="utf-8")


def files_and_logo(brand: str) -> list[str]:
    """What a move onto `brand`, which gives no logo, names in each language: the content's
    picture file and the badge, then the logo."""
    return [
        line
        for language, photo in PHOTOS.items()
        for line in (
            f"not following `{brand}`: `{language}`: `{SHOT}`: the picture file `{photo}` of the "
            f"piece, which stays as it was",
            f"not following `{brand}`: `{language}`: `{BADGE}`: the picture file `badge.jpg` of "
            f"the piece, which stays as it was",
            f"not following `{brand}`: `{language}`: `{LOGO}`: the picture role `picture.logo`, "
            f"which `{brand}` gives no file, so it is not drawn",
        )
    ]


def files_alone(brand: str) -> list[str]:
    """What a move onto `brand`, which gives a logo, names in each language: the content's
    picture file and the badge."""
    return [line for line in files_and_logo(brand) if LOGO not in line]


#: What a move from the brand with a logo onto the test brand says, and back.
ONTO_PLAIN = [f"another brand: `{LOGO_BRAND}` to `{PLAIN}`", *files_and_logo(PLAIN)]
ONTO_LOGO = [f"another brand: `{PLAIN}` to `{LOGO_BRAND}`", *files_alone(LOGO_BRAND)]


# --- what a move names --------------------------------------------------------------------------


def test_a_render_onto_a_brand_with_no_logo_names_each_picture_file_and_the_logo(
    tmp_path: Path,
) -> None:
    root = branded_project(tmp_path, LOGO_BRAND)
    rebrand(root, PLAIN)

    shown = lines(render_script, root, PIECE)

    assert said(shown) == ONTO_PLAIN
    assert shown[shown.index(ONTO_PLAIN[0]) - 1].startswith("lock: ")  # after the lock written
    assert reading.read_yaml(root / PIECE_FILE)["lock"] == lock_of(PLAIN)


def test_a_render_onto_a_brand_with_a_logo_names_each_picture_file_alone(tmp_path: Path) -> None:
    root = branded_project(tmp_path, PLAIN)
    rebrand(root, LOGO_BRAND)

    assert said(lines(render_script, root, PIECE)) == ONTO_LOGO


def test_neither_a_librarys_own_file_nor_a_produced_picture_is_named(tmp_path: Path) -> None:
    """The library's mark is part of the form its owner chose for every brand, and the
    produced picture is no picture file, though the scene shows both."""
    root = branded_project(tmp_path, LOGO_BRAND)
    rebrand(root, PLAIN)

    shown = said(lines(render_script, root, PIECE))

    for _, result in scenes_of(root):
        assert result.scene.find(MARK) is not None and result.scene.find(NOTE) is not None
    assert shown == ONTO_PLAIN
    assert not any(MARK in line or NOTE in line or "mark.png" in line for line in shown)


def scenes_of(root: Path) -> list[tuple[str, Any]]:
    """The piece's scenes under the lock it holds."""
    piece = pl.read_piece(root, "visual", PIECE)
    project = pl.Project(piece, piece.lock, pl.Held(root, "visual"))
    return project.scenes(facts=piece.stand_ins)


def test_a_picture_at_some_size_keys_alone_names_them() -> None:
    """A picture file shown at every key names none. One a switch by the size shows at a
    phone's size alone, and a logo the brand gives no file there alone, each name that key."""

    def result(key: str, *images: tuple[str, str], unvalued: dict[str, str] | None = None) -> Any:
        children = [
            scene.Element("image", trace, {"file": name, "library": "piece"})
            for trace, name in images
        ]
        top = scene.Element("group", "figure", children=children)
        shown = scene.Scene(PIECE, {}, "en", key, 5, [], [top])
        return scene.SceneResult(shown, [], {}, unvalued or {})

    phone = "device.phone"
    found = rebranding.unfollowed(
        [
            ("en", result("default", (SHOT, "photo.png"))),
            (
                "en",
                result(
                    phone,
                    (SHOT, "photo.png"),
                    (BADGE, "badge.jpg"),
                    unvalued={LOGO: "picture.logo"},
                ),
            ),
        ]
    )

    assert found == (
        rebranding.Unfollowed("en", SHOT, file="photo.png"),
        rebranding.Unfollowed("en", BADGE, file="badge.jpg", keys=(phone,)),
        rebranding.Unfollowed("en", LOGO, role="picture.logo", keys=(phone,)),
    )
    assert rebranding.said(LOGO_BRAND, PLAIN, found)[2:] == [
        f"not following `{PLAIN}`: `en`: `{BADGE}`: the picture file `badge.jpg` of the piece, "
        f"which stays as it was, at `{phone}`",
        f"not following `{PLAIN}`: `en`: `{LOGO}`: the picture role `picture.logo`, which "
        f"`{PLAIN}` gives no file, so it is not drawn, at `{phone}`",
    ]


def test_a_move_with_nothing_that_does_not_follow_says_so() -> None:
    assert rebranding.said(LOGO_BRAND, PLAIN, ()) == [
        f"another brand: `{LOGO_BRAND}` to `{PLAIN}`: no picture file of the piece shows, and "
        f"`{PLAIN}` gives each picture role a part shows"
    ]


# --- a move that keeps the brand, and what keeps none of it -------------------------------------


def test_a_move_that_keeps_the_brand_says_none_of_it(tmp_path: Path) -> None:
    """A render that moves the brand's version, one that keeps the lock, and a piece's first
    lock name nothing."""
    root = branded_project(tmp_path, LOGO_BRAND)
    logo.logo_brand(root, version="1.1.0")
    listed(root, released=False)

    shown = lines(render_script, root, PIECE)

    assert reading.read_yaml(root / PIECE_FILE)["lock"][LOGO_BRAND] == "1.1.0"
    assert said(shown) == []
    assert said(lines(render_script, root, PIECE)) == []
    first = branded_project(tmp_path / "first", PLAIN)
    data = reading.read_yaml(first / PIECE_FILE)
    del data["lock"]
    (first / PIECE_FILE).write_text(yaml_text(data), encoding="utf-8")
    assert said(lines(render_script, first, PIECE)) == []


def test_no_record_keeps_what_a_move_says_and_the_check_is_silent_on_it(tmp_path: Path) -> None:
    root = branded_project(tmp_path, LOGO_BRAND)
    rebrand(root, PLAIN)
    lines(render_script, root, PIECE)

    kept = (root / FINDINGS).read_text(encoding="utf-8")
    checked = run_main(check_script, PIECE, cwd=root)

    for text in (kept, checked.stdout, checked.stderr):
        assert "another brand" not in text and "not following" not in text
        assert LOGO not in text


# --- an upgrade, a before-and-after and a mark --------------------------------------------------


def exported(tmp_path: Path, brand: str, **fields: Any) -> Path:
    """`branded_project` under `brand`, exported once."""
    root = branded_project(tmp_path, brand, **fields)
    lines(export_script, root, PIECE)
    return root


def test_an_upgrade_onto_another_brand_says_it_once(tmp_path: Path) -> None:
    root = exported(tmp_path, LOGO_BRAND, state="published")
    rebrand(root, PLAIN)

    shown = lines(upgrade_script, root, PIECE, "--edited", "piece.yaml")

    assert said(shown) == ONTO_PLAIN
    assert reading.read_yaml(root / PIECE_FILE)["lock"] == lock_of(PLAIN)


def test_an_upgrade_off_a_lock_written_by_hand_onto_the_copys_brand_says_it(
    tmp_path: Path,
) -> None:
    """The look ahead's two locks name one brand, the copy's, but the run moves the lock a
    hand wrote onto the test brand, so the run says it of that move."""
    root = exported(tmp_path, LOGO_BRAND, state="published")
    data = reading.read_yaml(root / PIECE_FILE)
    data["lock"] = lock_of(PLAIN)
    (root / PIECE_FILE).write_text(yaml_text(data), encoding="utf-8")

    shown = lines(upgrade_script, root, PIECE)

    assert said(shown) == [f"another brand: `{PLAIN}` to `{LOGO_BRAND}`", *files_alone(LOGO_BRAND)]
    assert reading.read_yaml(root / PIECE_FILE)["lock"] == lock_of(LOGO_BRAND)


def test_a_look_ahead_whose_locks_name_two_brands_says_it(tmp_path: Path) -> None:
    root = exported(tmp_path, LOGO_BRAND, state="published")
    rebrand(root, PLAIN)

    shown = lines(before_after_script, root, PIECE, "--ahead")

    assert said(shown) == ONTO_PLAIN
    assert reading.read_yaml(root / PIECE_FILE)["lock"] == lock_of(LOGO_BRAND)


def test_a_look_back_at_a_lock_written_by_hand_onto_another_brand_says_it(tmp_path: Path) -> None:
    """No command moves a lock a person writes, and the look back says it to a reviewer of
    the change."""
    root = branded_project(tmp_path, PLAIN, state="published")
    git(root, "init", "-q", "-b", "main")
    git(root, "add", "visual")
    git(root, "commit", "-q", "-m", "the base")
    git(root, "checkout", "-q", "-b", "change")
    data = reading.read_yaml(root / PIECE_FILE)
    data.update(brand=LOGO_BRAND, lock=lock_of(LOGO_BRAND))
    (root / PIECE_FILE).write_text(yaml_text(data), encoding="utf-8")

    shown = lines(before_after_script, root, PIECE, "--back")

    assert said(shown) == ONTO_LOGO


def test_a_look_whose_locks_name_one_brand_says_none_of_it(tmp_path: Path) -> None:
    root = exported(tmp_path, LOGO_BRAND, state="published")
    logo.logo_brand(root, version="1.1.0")
    listed(root, released=True)

    shown = lines(before_after_script, root, PIECE, "--ahead")

    newer = {**lock_of(LOGO_BRAND), LOGO_BRAND: "1.1.0"}
    assert f"after: what a run would propose: {versions(newer)}" in shown
    assert said(shown) == []


def test_marking_final_a_version_of_another_brand_says_it(tmp_path: Path) -> None:
    """Version 1 was made under the test brand. The piece then moved onto the brand with a
    logo, and marking version 1 final puts the test brand's lock back."""
    root = exported(tmp_path, PLAIN)
    rebrand(root, LOGO_BRAND)
    assert said(lines(render_script, root, PIECE)) == ONTO_LOGO

    shown = lines(mark_final_script, root, PIECE, "1")

    assert said(shown) == [f"another brand: `{LOGO_BRAND}` to `{PLAIN}`", *files_and_logo(PLAIN)]
    put_back = f"lock of version 1 put back: {versions(lock_of(PLAIN))}"
    assert shown.index(put_back) + 1 == shown.index(said(shown)[0])
    assert reading.read_yaml(root / PIECE_FILE)["lock"] == lock_of(PLAIN)


def test_marking_final_a_version_of_the_brand_the_lock_names_says_none_of_it(
    tmp_path: Path,
) -> None:
    root = exported(tmp_path, LOGO_BRAND)
    assert said(lines(mark_final_script, root, PIECE, "1")) == []


def test_a_mark_whose_scenes_cannot_be_computed_says_why_and_marks(tmp_path: Path) -> None:
    root = exported(tmp_path, PLAIN)
    rebrand(root, LOGO_BRAND)
    lines(render_script, root, PIECE)
    (root / PIECE_FOLDER / "content.cs.yaml").unlink()

    shown = lines(mark_final_script, root, PIECE, "1")

    assert said(shown) == [
        f"another brand: `{LOGO_BRAND}` to `{PLAIN}`, and what does not follow it cannot be told: "
        f"{PIECE_FOLDER}/content.cs.yaml does not exist: the piece lists the language `cs`, so "
        f"write its content there"
    ]
    assert reading.read_yaml(root / PIECE_FILE)["state"] == "final"
