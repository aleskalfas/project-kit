"""The check of a text smaller than its medium allows (visual-communication DEC-055).

- **The smallest size of each medium the shipped tops declare.** A text a step below it fails,
  at its trace in the piece's own file, and a text at it passes (points 4 and 6).
- **Each statement, with what it covers:** a piece that names no medium, a medium its top
  declares nothing for, in a list and in a mapping, a size no medium shows, and a page where
  a share of the page gives no smallest size, in each of the three ways (point 10).
- **Where a share's fault lies:** at the top's file for `:page-height` at the top's own page,
  and at the lock in every other case (point 7).
- **The media and their sizes:** a run below the declared medium's smallest size is still
  reported beside the statement on another; a deck shown in a room that names no size is
  held to the room at `desktop`; a deck drawn at `desktop` and `projector` is held at each
  size to the medium that shows it (points 1 and 4).
- **What the check refuses,** in a piece's `media` and in a top's `smallest-text` (point 7).
- **Scene by scene:** each finding comes with its scene's language and key, and its page, and
  a statement that holds in every language or at every key says so (points 6 and 10).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from tests import test_visual_communication_poster as poster
from tests.in_process import load
from tests.visual_communication_project import (
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

checks, pl, text_size, findings = load(
    "visual-communication", "checks", "pipeline", "text_size", "findings"
)

PIECE = "sized"
PIECE_FILE = f"visual/pieces/{PIECE}/piece.yaml"
#: The version of the foundations being built the tests hold, which declares the shipped
#: tops' smallest sizes.
BUILT = "1.2.0"
TOP_FILE = "visual/libraries/foundations/{version}/components/{top}.yaml"

#: The labels of the check, and the formula's findings a share of the page may give.
TOO_SMALL = text_size.TEXT_TOO_SMALL
UNMEASURED = text_size.TEXT_SIZE_UNMEASURED
SHARE_FAULTS = ("formula-reach", "division-by-zero", "component-shape")

#: A piece's own block of two texts, one under the other: `small` in code's type and `kept`
#: in the body's, so a test sizes each apart through the brand.
PAIR = bound(
    "component",
    status="experimental",
    about="Two lines of text, one under the other.",
    fields={
        "type": "object",
        "properties": {
            "small": {"type": "string", "x-pkit-prose": True},
            "kept": {"type": "string", "x-pkit-prose": True},
        },
    },
    parts={
        "small": {
            "text": {"content": "small", "style": "type.code", "fill": "text-primary"},
            "width": "=:width",
        },
        "kept": {
            "text": {"content": "kept", "style": "type.body", "fill": "text-primary"},
            "y": "=small.bottom",
            "width": "=:width",
        },
    },
    preferred={"height": "=kept.bottom"},
)

BODY = {"use": "piece/pair", "small": "Small.", "kept": "Kept."}

#: The content of a piece of each shipped top, its one page holding the pair, and the trace
#: of that page and of the pair on it.
CONTENT: dict[str, dict[str, Any]] = {
    "figure": {"body": BODY},
    "deck": {"slides": [{"id": "one", "layout": "slide", "title": "One.", "visual": BODY}]},
    "site": {"pages": [{"id": "home", "layout": "standard", "main": BODY}]},
}
PAGE = {"figure": "figure", "deck": "deck/slides[one]", "site": "site/pages[home]"}
PAIR_AT = {
    "figure": "figure/body",
    "deck": "deck/slides[one]/visual",
    "site": "site/pages[home]/main",
}

#: The statement on a piece that names no medium.
NO_MEDIUM = (
    "the piece names no medium it is shown in under `media`, so no text's size was measured, "
    "in any language or at any size"
)

#: Kept as it is, where a test leaves a top's declaration as the foundations ship it.
SHIPPED = object()


def px(value: float) -> dict[str, Any]:
    return {"value": value, "unit": "px"}


def sized_project(
    tmp_path: Path,
    *,
    top: str = "figure",
    media: Any = None,
    smallest: Any = SHIPPED,
    code: float = 14,
    body: float = 16,
    device: Mapping[str, Mapping[str, float]] | None = None,
    top_keys: Mapping[str, Any] | None = None,
) -> Path:
    """The foundations being built, the test brand and the piece `sized`, a draft of the top
    `top` whose one page holds the pair, its `small` text set in code's type at `code` px and
    its `kept` in the body's at `body` px, its `media` as `media` gives them, if any. The top
    declares `smallest` in place of what the foundations ship, or none where it is None, and
    takes `top_keys` beside it. `device` gives the brand the size axis `device`, each mode it
    names with the sizes of code and the body it holds, the piece drawn at each."""
    root = project(tmp_path)
    folder = copy_library(root, FOUNDATIONS, "foundations", BUILT)
    path = folder / "components" / f"{top}.yaml"
    declared = dict(YAML(typ="safe").load(path.read_text(encoding="utf-8")))
    if smallest is None:
        declared.pop("smallest-text", None)
    elif smallest is not SHIPPED:
        declared["smallest-text"] = smallest
    declared.update(top_keys or {})
    write(path, yaml_text(declared))
    brand = copy_library(root, TEST_BRAND, "test-brand", "1.0.0")
    _type_sizes(brand / "tokens" / "base.tokens.json", code, body)
    if device:
        _devices(brand, device)
    write_list(
        root,
        {
            "foundations": {
                "source": {"kind": "shipped"},
                "versions": {BUILT: {"released": False}},
            },
            "test-brand": {
                "source": {"kind": "project"},
                "versions": {"1.0.0": {"released": False}},
            },
        },
    )
    fields: dict[str, Any] = {
        "top": f"foundations/{top}",
        "lock": {"foundations": BUILT, "test-brand": "1.0.0"},
    }
    if device:
        fields["modes"] = {"device": ["desktop", *device]}
    if media is not None:
        fields["media"] = media
    write_piece(root, PIECE, **fields)
    pieces = root / "visual" / "pieces" / PIECE
    write(pieces / "components" / "pair.yaml", yaml_text(PAIR))
    write(pieces / "content.en.yaml", yaml_text(bound("content", **CONTENT[top])))
    return root


def _type_sizes(tokens: Path, code: float, body: float) -> None:
    held = json.loads(tokens.read_text(encoding="utf-8"))
    held["type"]["code"]["$value"]["fontSize"] = px(code)
    held["type"]["body"]["$value"]["fontSize"] = px(body)
    tokens.write_text(json.dumps(held, indent=2), encoding="utf-8")


def _devices(brand: Path, device: Mapping[str, Mapping[str, float]]) -> None:
    """The test brand varies `device`: each mode `device` names takes its own sizes of code
    and the body, from a token file of its own, beside the default `desktop`."""
    resolver = brand / "test-brand.resolver.json"
    data = json.loads(resolver.read_text(encoding="utf-8"))
    contexts: dict[str, Any] = {"desktop": []}
    for mode, sizes in device.items():
        tokens = {
            "type": {
                "$type": "typography",
                **{
                    role: {"$value": {**_typography(brand, role), "fontSize": px(size)}}
                    for role, size in sizes.items()
                },
            }
        }
        write(brand / "tokens" / f"{mode}.tokens.json", json.dumps(tokens, indent=2))
        contexts[mode] = [{"$ref": f"tokens/{mode}.tokens.json"}]
    data["modifiers"]["device"] = {"contexts": contexts, "default": "desktop"}
    data["resolutionOrder"].append({"$ref": "#/modifiers/device"})
    resolver.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _typography(brand: Path, role: str) -> dict[str, Any]:
    held = json.loads((brand / "tokens" / "base.tokens.json").read_text(encoding="utf-8"))
    return dict(held["type"][role]["$value"])


def drawn(root: Path, name: str = PIECE) -> Any:
    piece = pl.read_piece(root, "visual", name)
    return pl.Project(piece, piece.lock, pl.Held(root, "visual"))


def computed(root: Path, name: str = PIECE) -> list[Any]:
    """The findings of the piece's scenes that the check of a text's size gives, and those a
    share of the page gives, as the render merges them, each file from the project root."""
    project_ = drawn(root, name)
    return [
        checks.rooted(finding, project_.piece)
        for finding in checks.computed(project_)
        if finding.code in (TOO_SMALL, UNMEASURED, *SHARE_FAULTS)
    ]


def given(root: Path) -> list[Any]:
    """What the check gives scene by scene, before the render's merges."""
    project_ = drawn(root)
    found = checks.found_in(project_, project_.scenes(facts=project_.piece.stand_ins))
    return [each for each in found if each.check is text_size.CHECK]


def places(found: list[Any]) -> list[tuple[str, str, str, str]]:
    return [(f.code, f.level, f.file, f.where) for f in found]


def declared() -> list[tuple[str, str, float]]:
    """Each fixed smallest size a shipped top declares, by the top and the medium."""
    found = []
    for path in sorted((FOUNDATIONS / "components").glob("*.yaml")):
        data = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
        for medium, value in (data.get("smallest-text") or {}).items():
            found.append((path.stem, medium, float(value)))
    return found


# --- the smallest size of each medium the shipped tops declare -----------------------------------


def test_the_shipped_tops_declare_a_screen_s_and_a_figure_s_paper_and_no_room() -> None:
    assert declared() == [
        ("deck", "screen", 11.0),
        ("figure", "screen", 11.0),
        ("figure", "paper", 10.67),
        ("site", "screen", 11.0),
    ]


@pytest.mark.parametrize(
    ("top", "medium", "smallest"), declared(), ids=lambda each: str(each).replace(".", "_")
)
def test_a_text_below_the_smallest_size_fails_and_one_at_it_passes(
    tmp_path: Path, top: str, medium: str, smallest: float
) -> None:
    below = round(smallest - 0.01, 2)
    root = sized_project(tmp_path, top=top, media=[medium], code=below, body=smallest)
    [finding] = computed(root)
    assert places([finding]) == [(TOO_SMALL, "fails", PIECE_FILE, f"{PAIR_AT[top]}/small")]
    assert f"is set in `type.code` at {below:g} px, below the smallest size of `{medium}`, " in (
        finding.message
    )
    assert f"`{medium}`, {smallest:g} px" in finding.message
    assert f"which `foundations/{top}` declares" in finding.message
    assert "Only where the piece is in fact shown so" in finding.fix


def test_the_finding_names_the_run_its_role_its_size_the_medium_and_the_top(
    tmp_path: Path,
) -> None:
    root = sized_project(tmp_path, media=["screen"], code=9)
    [finding] = computed(root)
    assert finding.message == (
        "the run of `content:body.small` is set in `type.code` at 9 px, below the smallest size "
        "of `screen`, 11 px, which `foundations/figure` declares"
    )
    assert finding.fix.startswith("set the run in a larger role")
    assert "such as `projector` for a room" in finding.fix
    assert "clear the finding with no text made larger" in finding.fix


# --- the statements ----------------------------------------------------------------------------


def test_a_piece_that_names_no_medium_is_stated_once_for_every_language_and_key(
    tmp_path: Path,
) -> None:
    root = sized_project(tmp_path, code=5)
    [each] = given(root)
    assert (each.language, each.size, each.page) == (None, None, None)
    assert places(computed(root)) == [(UNMEASURED, "fact", PIECE_FILE, "media")]
    assert computed(root)[0].message == NO_MEDIUM


@pytest.mark.parametrize(
    "media",
    [["screen", "room"], {"screen": ["desktop"], "room": ["desktop"]}],
    ids=["list", "mapping"],
)
def test_a_medium_its_top_declares_nothing_for_is_stated_beside_a_run_too_small_elsewhere(
    tmp_path: Path, media: Any
) -> None:
    """The figure declares no room: the room is stated, at the key it shows, and the run
    too small for the screen is reported beside it (DEC-055 points 10 and 12)."""
    root = sized_project(tmp_path, media=media, code=9)
    found = computed(root)
    assert places(found) == [
        (TOO_SMALL, "fails", PIECE_FILE, "figure/body/small"),
        (UNMEASURED, "fact", PIECE_FILE, "media"),
    ]
    sizes = ", at the sizes the piece shows in it: `desktop`" if isinstance(media, dict) else ""
    assert found[1].message == (
        "the top `foundations/figure` declares no smallest text size for `room`, so no text's "
        f"size was measured in `room`{sizes}"
    )
    stated = [each for each in given(root) if each.finding.code == UNMEASURED]
    assert [(each.language, each.size) for each in stated] == [(None, "default")]


def test_a_medium_a_mapping_gives_one_size_is_stated_at_that_size_alone(tmp_path: Path) -> None:
    root = sized_project(
        tmp_path,
        media={"screen": ["desktop"], "room": ["phone"]},
        device={"phone": {"code": 12, "body": 14}},
    )
    found = computed(root)
    assert places(found) == [(UNMEASURED, "fact", PIECE_FILE, "media")]
    assert found[0].message == (
        "`device.phone`: the top `foundations/figure` declares no smallest text size for "
        "`room`, so no text's size was measured in `room`, at the sizes the piece shows in it: "
        "`phone`"
    )


def test_a_size_no_medium_shows_is_stated_at_that_size(tmp_path: Path) -> None:
    root = sized_project(
        tmp_path, media={"screen": ["desktop"]}, device={"phone": {"code": 5, "body": 5}}
    )
    found = computed(root)
    assert places(found) == [(UNMEASURED, "fact", PIECE_FILE, "media")]
    assert found[0].message == (
        "`device.phone`: no medium the piece names under `media` shows the size `phone`, so no "
        "text's size was measured at it"
    )
    [stated] = given(root)
    assert (stated.language, stated.size) == (None, "device.phone")


def test_a_share_that_reads_the_height_of_the_top_s_own_page_lies_at_the_top(
    tmp_path: Path,
) -> None:
    """The figure is as tall as its content, so it asks for no height (DEC-055 point 7)."""
    root = sized_project(tmp_path, media=["screen"], smallest={"screen": "=:page-height / 40"})
    found = computed(root)
    assert places(found) == [
        (
            "formula-reach",
            "fails",
            TOP_FILE.format(version=BUILT, top="figure"),
            "smallest-text.screen",
        ),
        (UNMEASURED, "fact", PIECE_FILE, "figure"),
    ]
    assert found[0].library == f"foundations@{BUILT}"
    assert "reads `:page-height` at the page `figure`, which asks for no height" in found[0].message
    assert found[1].message == (
        "the smallest size of `screen` that `foundations/figure` declares, "
        "`=:page-height / 40`, gives none at the page `figure`, so no text's size on it was "
        "measured in `screen`"
    )
    [stated] = given(root)
    assert (stated.language, stated.size, stated.page) == ("en", "default", "figure")


def test_a_share_that_reads_the_height_of_a_page_a_component_draws_lies_at_the_lock(
    tmp_path: Path,
) -> None:
    """A site's page drawn by the piece's own component is no page of the site's own drawing,
    so the site's file alone does not show the fault."""
    root = sized_project(tmp_path, top="site", media=["screen"])
    content = {"pages": [{"id": "home", "use": "piece/pair", "small": "Small.", "kept": "Kept."}]}
    write(
        root / "visual/pieces" / PIECE / "content.en.yaml", yaml_text(bound("content", **content))
    )
    path = root / TOP_FILE.format(version=BUILT, top="site")
    data = dict(YAML(typ="safe").load(path.read_text(encoding="utf-8")))
    data["smallest-text"] = {"screen": "=:page-height / 40"}
    write(path, yaml_text(data))
    found = computed(root)
    assert places(found) == [
        ("formula-reach", "fails", PIECE_FILE, "lock"),
        (UNMEASURED, "fact", PIECE_FILE, "site/pages[home]"),
    ]
    assert found[0].message.startswith(
        f"under this lock, `foundations/site` of foundations@{BUILT}"
    )


@pytest.mark.parametrize(
    ("share", "code", "said"),
    [
        (
            "=:page-width * :page-width / (:page-height - :page-height)",
            "division-by-zero",
            "divides by zero",
        ),
        ("=:page-height - :page-width", "component-shape", "gives -560 px at the page"),
    ],
    ids=["division-by-zero", "not-above-zero"],
)
def test_a_share_that_gives_no_length_above_zero_lies_at_the_lock(
    tmp_path: Path, share: str, code: str, said: str
) -> None:
    root = sized_project(tmp_path, top="deck", media=["room"], smallest={"room": share})
    found = computed(root)
    assert places(found) == [
        (UNMEASURED, "fact", PIECE_FILE, "deck/slides[one]"),
        (code, "fails", PIECE_FILE, "lock"),
    ]
    assert said in found[1].message


# --- the media and their sizes -----------------------------------------------------------------

#: A room's smallest size planted on the deck, a share of its slide's height: 18 px on the
#: test brand's slide, 1,280 by 720 px.
ROOM = {"screen": 11, "room": "=:page-height / 40"}


def test_a_deck_shown_in_a_room_that_names_no_size_is_held_to_the_room_at_desktop(
    tmp_path: Path,
) -> None:
    root = sized_project(tmp_path, top="deck", media=["room"], smallest=ROOM, code=17.99, body=18)
    [finding] = computed(root)
    assert places([finding]) == [(TOO_SMALL, "fails", PIECE_FILE, "deck/slides[one]/visual/small")]
    assert (
        "below the smallest size of `room`, 18 px, `=:page-height / 40` of the page "
        "1280 × 720 px" in finding.message
    )


@pytest.mark.parametrize(
    ("media", "expected"),
    [
        ({"screen": ["desktop"], "room": ["projector"]}, []),
        (
            {"room": ["projector"]},
            [
                "`default`: no medium the piece names under `media` shows the size `desktop`, "
                "so no text's size was measured at it"
            ],
        ),
    ],
    ids=["each-size-its-medium", "desktop-unshown"],
)
def test_a_deck_drawn_for_a_laptop_and_a_room_holds_each_size_to_the_medium_that_shows_it(
    tmp_path: Path, media: Any, expected: list[str]
) -> None:
    """The desktop's type is below the room's smallest size and at the screen's, and the
    projector's at the room's (DEC-055 point 1)."""
    root = sized_project(
        tmp_path,
        top="deck",
        media=media,
        smallest=ROOM,
        code=11,
        body=16,
        device={"projector": {"code": 18, "body": 24}},
    )
    assert [f.message for f in computed(root)] == expected


# --- what the check refuses --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("media", "said"),
    [
        ([], "names no medium: name one at least"),
        ({}, "names no medium: name one at least"),
        (["screen", "tv"], "names `tv`, which is no medium the capability names"),
        (["screen", "screen"], "names `screen` twice"),
        ({"screen": []}, "`screen` names no size"),
        ({"screen": ["desktop", "desktop"]}, "`screen` names the size `desktop` twice"),
        ("screen", "is neither a list of media nor a mapping"),
    ],
    ids=["no-medium", "empty-mapping", "unknown", "twice", "no-size", "size-twice", "a-word"],
)
def test_a_piece_s_media_of_the_wrong_shape_is_refused(
    tmp_path: Path, media: Any, said: str
) -> None:
    root = sized_project(tmp_path, media=media)
    with pytest.raises(pl.Refused, match="`media`") as refused:
        pl.read_piece(root, "visual", PIECE)
    assert said in str(refused.value)
    report = checks.check(root, only=PIECE)
    [unreadable] = [f for f, _ in report.judged if f.code == "piece-unreadable"]
    assert said in unreadable.message


def test_a_size_the_piece_is_not_drawn_at_is_refused(tmp_path: Path) -> None:
    root = sized_project(tmp_path, media={"screen": ["phone"]})
    with pytest.raises(pl.Refused) as refused:
        drawn(root)
    assert str(refused.value) == (
        f"{PIECE_FILE}: `media`: `screen` names the size `phone`, which the piece is not drawn "
        "at: it is drawn at `desktop`"
    )


def test_a_medium_a_mapping_names_twice_is_a_key_written_twice(tmp_path: Path) -> None:
    root = sized_project(tmp_path)
    path = root / PIECE_FILE
    path.write_text(
        path.read_text(encoding="utf-8") + "media:\n  screen: [desktop]\n  screen: [desktop]\n",
        encoding="utf-8",
    )
    report = checks.check(root, only=PIECE)
    assert "file-unreadable" in {f.code for f, _ in report.judged}


def component_findings(root: Path) -> list[tuple[str, str, str]]:
    """The findings of the check of the location on its components' files."""
    report = checks.check(root, only=PIECE)
    return [
        (f.code, f.file.rsplit("/", 1)[-1], f.where)
        for f, _ in report.judged
        if f.code in ("component-shape", "formula-reach", "formula-dimension", "formula-unreadable")
    ]


@pytest.mark.parametrize(
    ("smallest", "where", "said"),
    [
        ({"tv": 11}, "smallest-text.tv", "names no medium `tv`"),
        ({"screen": 0}, "smallest-text.screen", "it takes a positive number"),
        ({"screen": -2}, "smallest-text.screen", "it takes a positive number"),
        ({"screen": "large"}, "smallest-text.screen", "it takes a positive number"),
        (
            {"screen": {"switch": ":device", "desktop": 11, "phone": 12}},
            "smallest-text.screen",
            "is a value, never a switch",
        ),
        ([11], "smallest-text", "takes a value for each medium"),
    ],
    ids=["unknown-medium", "zero", "negative", "a-word", "a-switch", "a-list"],
)
def test_a_smallest_size_of_the_wrong_shape_is_refused(
    tmp_path: Path, smallest: Any, where: str, said: str
) -> None:
    root = sized_project(tmp_path, media=["screen"], smallest=smallest)
    report = checks.check(root, only=PIECE)
    [refused] = [f for f, _ in report.judged if f.code == "component-shape" and f.where == where]
    assert said in refused.message


def test_a_fixed_length_for_paper_on_a_top_with_a_physical_size_is_refused(tmp_path: Path) -> None:
    root = sized_project(
        tmp_path,
        media=["paper"],
        smallest={"paper": 10},
        top_keys={"physical-size": {"width": 210, "height": 297}},
    )
    found = [f for f, _ in checks.check(root, only=PIECE).judged if f.code == "component-shape"]
    [refused] = [f for f in found if f.where == "smallest-text.paper"]
    assert "declares a physical size" in refused.message
    assert "give a share of the page" in refused.message


def test_a_smallest_size_on_a_component_that_is_no_top_is_refused(tmp_path: Path) -> None:
    root = sized_project(tmp_path, media=["screen"])
    path = root / "visual/pieces" / PIECE / "components" / "pair.yaml"
    write(path, yaml_text({**PAIR, "smallest-text": {"screen": 11}}))
    found = [f for f, _ in checks.check(root, only=PIECE).judged if f.code == "component-shape"]
    [refused] = [f for f in found if f.where == "smallest-text"]
    assert refused.file.endswith("components/pair.yaml")
    assert "is no top component" in refused.message


@pytest.mark.parametrize(
    ("share", "code", "said"),
    [
        ("=:width / 40", "formula-reach", "reads `:width`"),
        ("=@space.1", "formula-reach", "reads `@space.1`"),
        ("=:page-width / :page-height", "formula-dimension", "where a length belongs"),
        ("=:page-width *", "formula-unreadable", ""),
    ],
    ids=["the-top-s-size", "a-role", "a-number", "unreadable"],
)
def test_a_share_that_reads_beyond_the_page_or_gives_no_length_is_refused(
    tmp_path: Path, share: str, code: str, said: str
) -> None:
    root = sized_project(tmp_path, top="deck", media=["room"], smallest={"room": share})
    report = checks.check(root, only=PIECE)
    [refused] = [f for f, _ in report.judged if f.code == code]
    assert refused.where == "smallest-text.room"
    assert said in refused.message


def test_the_page_s_size_is_read_by_no_other_formula(tmp_path: Path) -> None:
    root = sized_project(tmp_path, media=["screen"])
    path = root / "visual/pieces" / PIECE / "components" / "pair.yaml"
    write(path, yaml_text({**PAIR, "preferred": {"height": "=:page-height"}}))
    found = [f for f, _ in checks.check(root, only=PIECE).judged if f.code == "formula-reach"]
    [refused] = [f for f in found if f.where == "preferred.height"]
    assert "which only a top's `smallest-text` reads" in refused.message


def test_a_brand_s_drawing_that_declares_a_smallest_size_is_refused(tmp_path: Path) -> None:
    root = poster.poster_project(tmp_path)
    path = root / poster.BRAND / "components" / "poster.yaml"
    drawing = dict(YAML(typ="safe").load(path.read_text(encoding="utf-8")))
    write(path, yaml_text({**drawing, "smallest-text": {"paper": "=:page-height / 50"}}))
    report = checks.check(root, only=poster.PIECE)
    [refused] = [
        f for f, _ in report.judged if f.code == "component-shape" and f.where == "smallest-text"
    ]
    assert refused.file.endswith("test-brand/1.1.0/components/poster.yaml")
    assert "is a drawing: the piece's top alone declares it" in refused.message


def test_a_share_on_paper_reads_the_height_a_physical_size_gives_a_page(tmp_path: Path) -> None:
    """The poster prints at A1, so its page asks for a height, and a share of it is read
    where the brand's drawing draws the page (DEC-055 points 3 and 7)."""
    root = poster.poster_project(tmp_path)
    path = root / "visual/libraries/test-print/1.0.0/components/poster.yaml"
    top = dict(YAML(typ="safe").load(path.read_text(encoding="utf-8")))
    write(path, yaml_text({**top, "smallest-text": {"paper": "=:page-height / 10"}}))
    piece = root / poster.PIECE_FOLDER / "piece.yaml"
    data = YAML(typ="safe").load(piece.read_text(encoding="utf-8"))
    write(piece, yaml_text({**data, "media": ["paper"]}))
    found = computed(root, poster.PIECE)
    assert found and {f.code for f in found} == {TOO_SMALL}
    assert all(
        "135.92 px, `=:page-height / 10` of the page 960 × 1359.19 px" in f.message for f in found
    )


# --- scene by scene ----------------------------------------------------------------------------


def test_each_finding_comes_with_its_scene_s_language_key_and_page(tmp_path: Path) -> None:
    root = sized_project(
        tmp_path, media=["screen"], code=9, device={"phone": {"code": 9, "body": 16}}
    )
    found = given(root)
    assert [(f.finding.code, f.language, f.size, f.page) for f in found] == [
        (TOO_SMALL, "en", "default", "figure"),
        (TOO_SMALL, "en", "device.phone", "figure"),
    ]
    [merged] = computed(root)
    assert merged.message.startswith("the run of `content:body.small`")


def test_the_check_states_its_reach_and_compares_scenes_across_no_axis() -> None:
    check = text_size.CHECK
    assert check.id == "text-size-by-medium"
    assert check.labels == (TOO_SMALL, UNMEASURED)
    assert check.compares == frozenset()
    assert check.reach is not None and check.reach.statements == (UNMEASURED,)
    assert check in checks.SCENE_CHECKS
    assert findings.FAILS == "fails"
