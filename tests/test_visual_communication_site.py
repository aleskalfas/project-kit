"""The site, a top of the foundations whose pages are web pages (visual-communication
DEC-022): its pages, its shared header and footer, a page's width from the size it is drawn
at and its height from its content, the role `size.site` and the sizes the neutral brand
and the test brand give, the findings DEC-022 point 8 lists, what the renderers draw of a site
at two sizes, and what `pkit visual export` writes of it.

The engine's cases are drawn in this process through `tests/visual_engine.py`, each in a
component of the tests' own, the site's file changed in memory. The pieces are the sites
under `tests/fixtures/visual-communication/site/`: `page`, a site of one page at each size
the neutral brand gives, and `portal`, a site of three pages on a desktop and on a phone.
A location holds them with the foundations, the starter and the neutral brand being built.
It starts no `pkit`: the export command's script runs in this process."""

from __future__ import annotations

import copy
import json
import re
import shutil
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from tests import test_visual_communication_starter as starter
from tests.in_process import load, run_main
from tests.visual_communication_project import (
    CAPABILITY,
    FIXTURES,
    FOUNDATIONS,
    TEST_BRAND,
    bound,
    copy_library,
    hold_shipped,
    importable,
    locked_at,
    project,
    write,
    write_list,
    write_piece,
    yaml_text,
)
from tests.visual_engine import COMPONENTS, _px, block, codes, draw, frame

export_script, checks, keys, pl, tokens, svg, pdf, html = load(
    "visual-communication",
    "export.py",
    "checks",
    "keys",
    "pipeline",
    "tokens",
    "plugins.svg",
    "plugins.pdf",
    "plugins.html",
)

PIECES = FIXTURES / "site" / "pieces"
NEUTRAL = CAPABILITY / "libraries" / "neutral"
#: The test brand that gives the sizes of `device`, built on the foundations being built.
SIZED_BRAND = FIXTURES / "libraries" / "test-brand" / "1.1.0"
SITE = COMPONENTS["foundations/site"]
#: Each px is this many PDF points (`pdf.SCALE`).
POINT = 0.75


def band(height: str) -> dict[str, Any]:
    """A component that paints a box over all it is given and sets no inset, as tall as
    `height` and as wide as it is given."""
    fill = {"box": {"fill": "surface"}, "width": "=:width", "height": "=:height"}
    component = block({"fill": fill}, preferred={"height": height})
    return component


#: The tests' components a page places, and the site's width they draw it at.
BANDS = {"lab/band": band("=@space.4"), "lab/tall": band("=@space.4 * 10")}
WIDTH = 390
SIZED = {"size.site": _px(WIDTH)}


def site(**changes: Any) -> dict[str, Any]:
    """The site's file, its layout `standard` changed by `changes`: each a part's key and
    its new value, or the layout's `preferred`."""
    changed = copy.deepcopy(SITE)
    standard = changed["layouts"]["standard"]
    for key, value in changes.items():
        if key == "preferred":
            standard["preferred"] = value
        else:
            part, _, prop = key.partition("__")
            standard["parts"][part][prop] = value
    return changed


def drawn_site(content: Mapping[str, Any], top: Mapping[str, Any] | None = None) -> Any:
    """The scene of a site of `content`, drawn by the site's file or by `top`."""
    components = {**BANDS, "lab/site": top or SITE}
    return draw(content, use="lab/site", components=components, roles=SIZED)


def page(id_: str, main: str = "lab/band") -> dict[str, Any]:
    return {"id": id_, "layout": "standard", "main": {"use": main}}


SHARED = {"header": {"use": "lab/band"}, "footer": {"use": "lab/band"}}


# --- the top ----------------------------------------------------------------------------------


def test_the_site_holds_its_pages_a_header_a_footer_and_the_layout_standard() -> None:
    """Its field `pages` holds its pages, and `header` and `footer` are optional. Its one
    layout, `standard`, has one slot, `main` (`files.md`, *The foundations*). It asks for
    its width alone (DEC-022 points 1 and 3). The foundations being built pass the check
    alone with it, which the shipped libraries' tests read."""
    fields = SITE["fields"]
    assert fields["required"] == ["pages"]
    assert fields["properties"]["pages"]["x-pkit-pages"] is True
    assert {"header", "footer"} <= set(fields["properties"])
    assert list(SITE["layouts"]) == ["standard"]
    standard = SITE["layouts"]["standard"]
    assert (list(standard["slots"]), standard["required"]) == (["main"], ["main"])
    assert SITE["preferred"] == {"width": "=@size.site"}
    assert set(standard["preferred"]) == {"height"}


def test_a_page_lays_its_header_main_part_and_footer_one_under_another_each_its_whole_width() -> (
    None
):
    """On the page's background, each part as tall as it asks (`files.md`, *The foundations*)."""
    result = drawn_site({**SHARED, "pages": [page("home", "lab/tall")]})
    assert codes(result) == []
    assert frame(result, "site/pages[home]") == (0, 0, WIDTH, 32 + 320 + 32)
    assert frame(result, "site/pages[home]/background") == (0, 0, WIDTH, 384)
    assert frame(result, "site/pages[home]/header") == (0, 0, WIDTH, 32)
    assert frame(result, "site/pages[home]/main") == (0, 32, WIDTH, 320)
    assert frame(result, "site/pages[home]/footer") == (0, 352, WIDTH, 32)


def test_a_component_that_sets_no_inset_touches_the_pages_edge() -> None:
    result = drawn_site({**SHARED, "pages": [page("home")]})
    for part in ("header", "main", "footer"):
        x, _, width, _ = frame(result, f"site/pages[home]/{part}/fill")
        assert (x, width) == (0, WIDTH), part


def test_a_page_with_no_header_or_footer_starts_at_its_top_with_its_main_part() -> None:
    result = drawn_site({"pages": [page("home")]})
    assert codes(result) == []
    assert frame(result, "site/pages[home]/main") == (0, 0, WIDTH, 32)
    assert frame(result, "site/pages[home]") == (0, 0, WIDTH, 32)


def test_a_page_drawn_by_its_own_component_draws_no_header_and_no_footer() -> None:
    result = drawn_site({**SHARED, "pages": [page("home"), {"id": "alone", "use": "lab/tall"}]})
    assert codes(result) == []
    alone = result.scene.find("site/pages[alone]")
    assert alone is not None
    assert [child.id for child in alone.children] == ["site/pages[alone]/fill"]
    assert frame(result, "site/pages[alone]") == (0, 0, WIDTH, 320)
    assert result.scene.find("site/pages[home]/header") is not None


def test_each_page_takes_its_own_height_and_the_sites_frame_its_tallest() -> None:
    """Each page is as wide as `size.site` and as tall as its content. The site's own frame
    is as wide, and as tall as its tallest page (DEC-022 point 3)."""
    pages = [page("short"), page("long", "lab/tall"), page("again")]
    result = drawn_site({**SHARED, "pages": pages})
    assert codes(result) == []
    assert result.scene.pages == [f"site/pages[{id_}]" for id_ in ("short", "long", "again")]
    heights = {id_: frame(result, f"site/pages[{id_}]")[3] for id_ in ("short", "long", "again")}
    assert heights == {"short": 96, "long": 384, "again": 96}
    assert frame(result, "site") == (0, 0, WIDTH, 384)
    top = result.scene.find("site")
    assert top is not None
    assert top.sources["width"] == "role:size.site"
    assert top.sources["height"] == "engine"


def test_a_part_placed_from_its_pages_foot_is_a_loop() -> None:
    """The page is as tall as its lowest part, so a part placed from its foot reads its own
    place (DEC-005 point 4)."""
    looped = site(footer__y="=:height - footer.height")
    result = drawn_site({**SHARED, "pages": [page("home")]}, looped)
    assert codes(result) == ["loop"]
    assert "site/pages[home]/footer.y" in result.findings[0].message


def test_a_site_placed_in_a_slide_is_a_page_inside_a_page() -> None:
    slide = {"id": "a", "layout": "slide", "title": "A site", "visual": {"use": "lab/site"}}
    content = {"slides": [{**slide, "visual": {"use": "lab/site", "pages": [page("home")]}}]}
    components = {**BANDS, "lab/site": SITE}
    result = draw(content, use="foundations/deck", components=components, roles=SIZED)
    assert codes(result) == ["page-in-page"]
    assert result.findings[0].where == "deck/slides[a]/visual/pages[home]"


# --- a layout's height ------------------------------------------------------------------------


def test_a_layout_that_says_a_width_fails() -> None:
    """A page gets the top's width (DEC-022 points 3 and 8)."""
    wide = site(preferred={"height": "=footer.bottom", "width": "=@space.4"})
    result = drawn_site({"pages": [page("home")]}, wide)
    assert codes(result) == ["component-shape"]
    assert result.findings[0].where == "layouts.standard.preferred.width"


def test_a_layout_of_a_top_that_asks_for_no_height_says_its_pages_height() -> None:
    result = drawn_site({"pages": [page("home")]}, site(preferred=None))
    shape = [finding for finding in result.findings if finding.code == "component-shape"]
    assert [finding.where for finding in shape] == ["layouts.standard.preferred"]


def test_a_page_whose_layout_asks_for_more_than_its_tops_height_gets_less() -> None:
    """A page gets the height of a top that asks for one, whatever its layout says
    (DEC-022 point 3, DEC-005 point 14)."""
    short = site(preferred={"height": "=@space.4 * 20"})
    short["preferred"] = {"width": "=@size.site", "height": "=@space.4 * 3"}
    result = drawn_site({"pages": [page("home")]}, short)
    assert codes(result) == ["gets-less"]
    assert result.findings[0].where == "site/pages[home]"
    assert frame(result, "site/pages[home]") == (0, 0, WIDTH, 96)


def test_a_layout_of_a_top_of_one_page_says_no_height() -> None:
    """Only a layout that is a page's form says its page's height: a top of one page says
    its own under its `preferred`."""
    figure = copy.deepcopy(COMPONENTS["foundations/figure"])
    figure["layouts"]["frame"]["preferred"] = {"height": "=@space.4"}
    result = draw({"body": {"use": "lab/band"}}, use="lab/figure", components={
        **BANDS, "lab/figure": figure
    })  # fmt: skip
    shape = [finding for finding in result.findings if finding.code == "component-shape"]
    assert [finding.where for finding in shape] == ["layouts.frame.preferred"]


# --- the sites under the neutral brand --------------------------------------------------------

UNRELEASED = {"1.1.0": {"released": False}}


def site_location(root: Path) -> Path:
    """A location that holds the foundations, the starter and the neutral brand being built,
    the test brand that gives sizes, and the site pieces, each locked at the versions being
    built."""
    copy_library(root, SIZED_BRAND, "test-brand", "1.1.0")
    write_list(root, {"test-brand": {"source": {"kind": "project"}, "versions": UNRELEASED}})
    built = {
        name: hold_shipped(root, name).version for name in ("foundations", "starter", "neutral")
    }
    shutil.copytree(PIECES, root / "visual" / "pieces")
    for folder in (root / "visual" / "pieces").iterdir():
        locked_at(folder, built)
    return root


@pytest.fixture(scope="module")
def location(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return site_location(project(tmp_path_factory.mktemp("site")))


def project_of(root: Path, name: str, **lock: str) -> Any:
    """The piece `name` of the location at `root`, under its lock, `lock` changing it."""
    piece = pl.read_piece(root, "visual", name)
    return pl.Project(piece, {**piece.lock, **lock}, pl.Held(root, "visual"))


def scenes_of(drawn: Any) -> dict[str, Any]:
    """The scene of a piece at each key over the size axes, in its one language."""
    found = {}
    for _, result in drawn.scenes(facts=drawn.piece.stand_ins):
        assert result.findings == [], result.findings
        found[result.scene.size_key] = result.scene
    return found


def page_frames(scene: Any) -> dict[str, tuple[float, float]]:
    """Each page of a site's scene, by its id, as its width and its height."""
    top = scene.children[0]
    return {
        child.id: (child.properties["width"], child.properties["height"]) for child in top.children
    }


def test_a_site_of_one_page_and_one_of_three_pass_the_check_under_neutral(location: Path) -> None:
    """Each brand's version states, once, that it gives `picture.logo` no value, and no piece
    states it (DEC-025 point 9)."""
    report = checks.check(location)
    built = hold_shipped(project(location.parent / "listed"), "neutral").version
    found = [
        (level, finding.code, finding.file, finding.where)
        for finding, level in report.judged
        if finding.code != "component-experimental"
    ]
    assert sorted(found) == [
        ("fact", "picture-role-unvalued", f"visual/libraries/{name}/", "picture.logo")
        for name in (f"neutral/{built}", "test-brand/1.1.0")
    ]
    assert not report.failed()


def test_each_page_is_as_wide_as_its_size_and_as_tall_as_its_content(location: Path) -> None:
    """At each size the neutral brand gives, the page is `size.site` wide: a narrower page
    lays its text in more lines, so it is taller (DEC-022 point 3)."""
    scenes = scenes_of(project_of(location, "page"))
    assert sorted(scenes) == ["default", "device.phone", "device.tablet"]
    frames = {key: page_frames(scene)["site/pages[home]"] for key, scene in scenes.items()}
    assert {key: width for key, (width, _) in frames.items()} == {
        "default": 1280,
        "device.tablet": 768,
        "device.phone": 390,
    }
    heights = [frames[key][1] for key in ("default", "device.tablet", "device.phone")]
    assert heights == sorted(heights) and len(set(heights)) == 3


def test_with_more_content_a_page_is_taller_at_each_size_and_each_takes_its_own(
    location: Path,
) -> None:
    """The portal's guide holds more than its home, at each size; its notice, drawn by its
    own component, is as tall as that component asks. The site's frame is as tall as its
    tallest page."""
    for key, scene in scenes_of(project_of(location, "portal")).items():
        frames = page_frames(scene)
        home, guide, notice = (frames[f"site/pages[{id_}]"] for id_ in ("home", "guide", "notice"))
        assert guide[1] > home[1] > notice[1], key
        top = scene.children[0].properties
        assert (top["width"], top["height"]) == (home[0], guide[1]), key


def test_the_header_and_footer_lie_on_every_page_in_a_layout_from_edge_to_edge(
    location: Path,
) -> None:
    """The header's card sets its own inset, so its box reaches the page's edges; the
    notice, drawn by its own component, holds neither (`files.md`, *The foundations*)."""
    for key, scene in scenes_of(project_of(location, "portal")).items():
        width = scene.children[0].properties["width"]
        for id_ in ("home", "guide"):
            for part in ("header", "main", "footer"):
                element = scene.find(f"site/pages[{id_}]/{part}")
                assert element is not None, (key, id_, part)
                assert (element.properties["x"], element.properties["width"]) == (0, width)
            box = scene.find(f"site/pages[{id_}]/header/box")
            assert box is not None
            assert (box.properties["x"], box.properties["width"]) == (0, width), key
        assert scene.find("site/pages[notice]/header") is None
        assert scene.find("site/pages[notice]/footer") is None


# --- the role and the sizes -------------------------------------------------------------------


def resolver(folder: Path) -> dict[str, Any]:
    return json.loads(next(folder.glob("*.resolver.json")).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "folder,widths",
    [(NEUTRAL, (1280, 768, 390)), (SIZED_BRAND, (1440, 768, 320))],
    ids=["neutral", "test-brand"],
)
def test_each_brand_gives_three_sizes_each_from_its_own_file_with_its_sites_width(
    folder: Path, widths: tuple[int, int, int]
) -> None:
    """Each mode of `device` but the default takes a token file of its own, and each gives
    `size.site`: so the two brands prove a part at six widths (DEC-022 point 5)."""
    contexts = resolver(folder)["modifiers"]["device"]["contexts"]
    assert contexts["desktop"] == []
    assert contexts["tablet"] == [{"$ref": "tokens/tablet.tokens.json"}]
    assert contexts["phone"] == [{"$ref": "tokens/phone.tokens.json"}]
    brand = tokens.read_brand(folder, tokens.read_scope({"foundations": FOUNDATIONS}))
    assert brand.findings == ()
    assert brand.axes["device"].modes == ("desktop", "tablet", "phone")
    found = tuple(
        brand.resolve("size.site", {"device": mode})["value"]
        for mode in ("desktop", "tablet", "phone")
    )
    assert found == widths


def test_a_brand_that_gives_size_site_no_value_draws_a_site_as_wide_as_its_slide(
    tmp_path: Path,
) -> None:
    """The test brand 1.0.0 gives no size and no `size.site`, which takes `size.slide`
    (DEC-004 point 7)."""
    root = project(tmp_path)
    copy_library(root, TEST_BRAND, "test-brand", "1.0.0")
    write_list(
        root, {"test-brand": {"source": {"kind": "project"}, "versions": {"1.0.0": {}}}}
    )  # fmt: skip
    built = {name: hold_shipped(root, name).version for name in ("foundations", "starter")}
    write_piece(
        root,
        "site",
        top="foundations/site",
        lock={**built, "test-brand": "1.0.0"},
    )
    content = {"pages": [{"id": "home", "layout": "standard", "main": {"use": "starter/card"}}]}
    write(root / "visual/pieces/site/content.en.yaml", yaml_text(bound("content", **content)))
    drawn = project_of(root, "site")
    (scene,) = scenes_of(drawn).values()
    slide = drawn.brand.resolve("size.slide", {})["value"]
    assert scene.children[0].properties["width"] == slide == 1280


# --- what the check reports -------------------------------------------------------------------


def narrowing_nothing(folder: Path) -> None:
    """The brand at `folder` made to give `size.site` no value on a phone: its phone file
    gives a narrower `space.3` alone."""
    narrow = {"space": {"$type": "dimension", "3": {"$value": {"value": 8, "unit": "px"}}}}
    write(folder / "tokens" / "phone.tokens.json", json.dumps(narrow))


def sized_location(root: Path, devices: tuple[str, ...] = ("desktop", "phone")) -> Path:
    """The site location with the test brand that gives sizes, its phone giving no site's
    width, and a site `wide` in it, the portal drawn on `devices`."""
    site_location(root)
    narrowing_nothing(root / "visual" / "libraries" / "test-brand" / "1.1.0")
    portal = pl.read_piece(root, "visual", "portal")
    write_piece(
        root,
        "wide",
        top="foundations/site",
        modes={"device": list(devices)},
        lock={**portal.lock, "test-brand": "1.1.0"},
    )
    shutil.copy(PIECES / "portal" / "content.en.yaml", root / "visual/pieces/wide")
    return root


def judged(report: Any, code: str) -> list[tuple[str, str, str, str]]:
    return [
        (level, finding.file, finding.where, finding.message)
        for finding, level in report.judged
        if finding.code == code
    ]


def test_a_size_at_which_the_top_is_as_wide_as_on_a_desktop_asks_for_attention(
    tmp_path: Path,
) -> None:
    """Its shape follows the size and its width does not (DEC-022 point 3). The finding lies
    at the piece and names the brand, which gives the widths, and no component (point 8)."""
    root = sized_location(project(tmp_path))
    report = checks.check(root)
    (found,) = judged(report, checks.SIZE_WIDTH)
    level, file, where, message = found
    assert (level, file, where) == ("attention", "visual/pieces/wide/piece.yaml", "brand")
    assert message.startswith("`device.phone`: the top is 1440 px wide, as at the default size")
    assert "test-brand@1.1.0" in message
    assert "foundations/" not in message
    assert not report.failed()


def test_a_piece_drawn_at_no_default_size_is_measured_against_the_default(
    tmp_path: Path,
) -> None:
    """The top's width at the default is computed where the piece names no scene there."""
    root = sized_location(project(tmp_path), ("phone",))
    (found,) = judged(checks.check(root), checks.SIZE_WIDTH)
    assert found[3].startswith("`device.phone`: the top is 1440 px wide")


def test_a_top_whose_width_follows_the_size_asks_for_nothing(location: Path) -> None:
    assert judged(checks.check(location), checks.SIZE_WIDTH) == []


def test_a_finding_in_the_shared_header_read_alike_on_several_pages_is_reported_once(
    tmp_path: Path,
) -> None:
    """The header is written once, so a word too long for it on a phone is one finding,
    which names the pages it is read on (DEC-022 point 8). A finding in a page's own main
    part is that page's alone."""
    root = site_location(project(tmp_path))
    path = root / "visual/pieces/portal/content.en.yaml"
    content = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    content["header"]["head"] = "Pneumonoultramicroscopicsilicovolcanoconiosis"
    write(path, yaml_text(content))
    found = judged(checks.check(root), "text-overflow")
    assert len(found) == 1, found
    level, _, where, message = found[0]
    assert (level, where) == ("fails", "site/pages[home]/header/head")
    assert message.startswith("`device.phone`: ")
    assert "a word of content:header.head is wider" in message
    assert message.endswith("; read the same on the pages `site/pages[home]`, `site/pages[guide]`")


# --- the outputs ------------------------------------------------------------------------------


def media_boxes(document: bytes) -> list[tuple[float, float]]:
    """The width and the height of each page of a PDF file, in points, in its pages' order."""
    return [
        (float(box[2]), float(box[3]))
        for box in (found.split() for found in re.findall(rb"/MediaBox \[([^\]]*)\]", document))
    ]


def test_a_site_at_two_sizes_renders_a_file_for_each_size_in_svg_and_pdf(
    location: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each PDF page measures what the scene gives its page, at 0.75 pt to the px."""
    importable(monkeypatch, svg, pdf)
    drawn = project_of(location, "portal")
    results = drawn.scenes(facts=drawn.piece.stand_ins)
    sizes = {result.scene.size_key: page_frames(result.scene) for _, result in results}
    assert sorted(sizes) == ["default", "device.phone"]
    previews = {group: made for _, group, made in pl.drawn(drawn, results, "svg")}
    documents = {group: made for _, group, made in pl.drawn(drawn, results, "pdf")}
    assert sorted(previews) == sorted(documents) == [("default",), ("device.phone",)]
    for (key,), made in previews.items():
        assert [page.id for page in made.pages] == list(sizes[key]), key
        for page, (width, height) in zip(made.pages, sizes[key].values(), strict=True):
            assert f'width="{width:g}"' in page.svg and f'height="{height:g}"' in page.svg
    for (key,), made in documents.items():
        expected = [
            (round(width * POINT, 2), round(height * POINT, 2))
            for width, height in sizes[key].values()
        ]
        found = [
            (round(width, 2), round(height, 2)) for width, height in media_boxes(made.document)
        ]
        assert found == expected, key
    assert sizes["default"] != sizes["device.phone"]


#: The folder the export command writes the portal's files to, in the clone's local folder
#: (DEC-006 point 7), and the width of the site at each size the portal names.
EXPORTED = ".pkit/capabilities/visual-communication/project/local/exports/portal"
WIDTHS = {"default": 1280, "device.phone": 390}


def page_sizes(drawn: str) -> dict[str, tuple[float, float]]:
    """Each page of a page file, by its trace id, in its order, as the width and the height
    its style gives it: as wide as its frame, in the frame's proportions (DEC-020 point 4)."""
    found = re.findall(
        r'<div data-page="([^"]+)" style="width:min\(100%,([0-9.]+)px\);'
        r'aspect-ratio:([0-9.]+)/([0-9.]+)"',
        drawn,
    )
    assert found and all(width == wide for _, width, wide, _ in found), found
    return {id_: (float(width), float(tall)) for id_, width, _, tall in found}


def scaled(sizes: Iterable[tuple[float, float]], scale: float = 1.0) -> list[tuple[float, float]]:
    """Each width and height of `sizes` times `scale`, to the 1/100 a file writes."""
    return [(round(width * scale, 2), round(height * scale, 2)) for width, height in sizes]


def test_a_site_at_two_sizes_exports_a_page_file_and_a_pdf_file_for_each_size(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`pkit visual export` writes the portal, which declares `html` and `pdf`, as one page
    file and one PDF file at each size, under one number (DEC-023 point 1). Each holds the
    three pages in order, each as wide as the site at that size and as tall as its scene
    gives it from its own content, a PDF page at 0.75 pt to the px (DEC-022 point 3)."""
    importable(monkeypatch, pdf, html)
    root = site_location(project(tmp_path))
    drawn = project_of(root, "portal")
    results = drawn.scenes(facts=drawn.piece.stand_ins)
    sizes = {result.scene.size_key: page_frames(result.scene) for _, result in results}
    assert {key: {width for width, _ in pages.values()} for key, pages in sizes.items()} == {
        key: {width} for key, width in WIDTHS.items()
    }
    assert [len({height for _, height in pages.values()}) for pages in sizes.values()] == [3, 3]
    shown = run_main(export_script, "portal", cwd=root)
    assert shown.returncode == 0, shown.stderr
    folder = root / EXPORTED
    names = {key: (f"portal.v1.en.{key}.html", f"portal.v1.en.{key}.pdf") for key in WIDTHS}
    assert sorted(path.name for path in folder.iterdir()) == sorted(
        name for pair in names.values() for name in pair
    )
    for key, (page_file, document) in names.items():
        pages = page_sizes((folder / page_file).read_text(encoding="utf-8"))
        assert list(pages) == list(sizes[key]), key
        assert scaled(pages.values()) == scaled(sizes[key].values()), key
        boxes = media_boxes((folder / document).read_bytes())
        assert scaled(boxes) == scaled(sizes[key].values(), POINT), key


# --- what draws as before ---------------------------------------------------------------------

#: A figure of the starter's card, drawn under the test brand.
FIGURE = {
    "body": {"use": "starter/card", "head": "A figure", "text": "Its body, and a caption."},
    "caption": "A figure draws as it did.",
}


def renders(drawn: Any) -> Iterator[tuple[str, str, Any]]:
    """What each renderer draws of a piece: its name, the file's keys, and its files' text,
    with the version a trace gives each component of the foundations left out."""
    results = drawn.scenes(facts=drawn.piece.stand_ins)
    traced = re.compile(r'(data-component="foundations/[^"]*" data-version=")[^"]*"')
    for renderer in ("svg", "pdf", "html"):
        for language, group, made in pl.drawn(drawn, results, renderer):
            if renderer == "svg":
                files = [page.svg for page in made.pages]
            else:
                files = [made.document.decode("latin-1")]
            yield renderer, f"{language}.{'+'.join(group)}", [traced.sub(r'\1"', f) for f in files]


def as_released_location(root: Path) -> Path:
    """The starter's reference location, with the foundations' release 1.0.0, the test brand
    that gives sizes, and a figure, each piece locked at the versions being built."""
    starter.reference_location(root)
    hold_shipped(root, "foundations", being_built=False)
    built = {name: hold_shipped(root, name).version for name in ("foundations", "starter")}
    write_piece(
        root,
        "figure",
        exports=["svg"],
        lock={**built, "test-brand": "1.0.0"},
    )
    write(root / "visual/pieces/figure/content.en.yaml", yaml_text(bound("content", **FIGURE)))
    return root


def test_the_deck_and_the_figure_draw_as_before_in_every_renderer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """On the foundations being built as on their release 1.0.0, and under the test brand
    that gives sizes as under its version that gives none, a piece that names no size draws
    byte for byte the same, in each renderer (DEC-022 point 3, DEC-021 point 2): the deck of
    the card's reference piece, in two languages and four combinations, and a figure. The
    starter's and the neutral brand's tests draw every reference piece so in SVG."""
    importable(monkeypatch, svg, pdf, html)
    root = as_released_location(project(tmp_path))
    for name in ("card", "figure"):
        drawn = list(renders(project_of(root, name)))
        assert drawn, name
        assert list(renders(project_of(root, name, foundations="1.0.0"))) == drawn, name
        assert list(renders(project_of(root, name, **{"test-brand": "1.1.0"}))) == drawn, name
