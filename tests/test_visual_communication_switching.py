"""The SVG renderer's switching file, the format `svg-modes` (visual-communication DEC-018 points
1 and 4), and the reading that holds it to the one-key file of each combination it holds
(`_lib/switching.py`): what the renderer declares, what a switching file draws and loses, what
the reading compares and what it refuses, and a real browser drawing the file in each mode
as the one-key file of that mode.

The renderer's version is the one-key file's, 1.3.0 since it draws a run's sign and ground, as
it is pinned in `test_visual_communication_svg`.
"""

from __future__ import annotations

import base64
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import pytest

from tests.in_process import load
from tests.test_visual_communication_html import foundations_majors
from tests.test_visual_communication_svg import (
    COLOURS,
    FONT,
    HEAD,
    SHAPES,
    TIES,
    TITLE,
    element,
    scene,
)
from tests.test_visual_communication_viewing_browser import found_browser, real_browser
from tests.visual_communication_producer import png

svg, svg_declaration, seam, switching, reading, viewing_browser = load(
    "visual-communication",
    "plugins.svg",
    "plugins.svg_declaration",
    "plugins.seam",
    "switching",
    "reading",
    "viewing_browser",
)

MODES = "svg-modes"
DARK = "colour-scheme.dark"

#: The colours of the dark scheme: the surface black, the ink white and translucent, the
#: shade white, and no accent.
DARK_COLOURS = {
    "surface": {"components": [0, 0, 0], "alpha": 1},
    "border": {"components": [0.5, 0.5, 0.5], "alpha": 1},
    "shade": {"components": [1, 1, 1], "alpha": 1},
    "ink": {"components": [1, 1, 1], "alpha": 0.5},
}

#: Each key's combination, light first, and its colours.
COMBINATIONS = {"default": {"colour-scheme": "light"}, DARK: {"colour-scheme": "dark"}}
COLOURS_OF = {"default": COLOURS, DARK: DARK_COLOURS}

#: What a reader's signal holds in each key.
SIGNALS = {"default": {"prefers-color-scheme": "light"}, DARK: {"prefers-color-scheme": "dark"}}


def switched(
    drawn: Mapping[str, Any],
    keys: Mapping[str, Mapping[str, str]] = COMBINATIONS,
    pictures: Mapping[str, Mapping[str, Any]] | None = None,
) -> Any:
    """`drawn` as switching files that hold `keys`, in their order."""
    return svg.render(
        drawn,
        form=MODES,
        keys=keys,
        colours={key: COLOURS_OF[key] for key in keys},
        font_file=lambda _family: FONT,
        pictures={key: (pictures or {}).get(key, {}) for key in keys},
    )


def one_key(
    drawn: Mapping[str, Any], key: str, pictures: Mapping[str, Mapping[str, Any]] | None = None
) -> Any:
    """`drawn` as the one-key file of `key`."""
    return svg.render(
        drawn,
        key=key,
        colours=COLOURS_OF[key],
        font_file=lambda _family: FONT,
        pictures=(pictures or {}).get(key, {}),
    )


def picture_file(folder: Path, name: str, colour: tuple[int, int, int, int]) -> Any:
    """A picture of 2 × 2 pixels of `colour`, as a renderer is handed it."""
    path = folder / f"{name}.png"
    path.write_bytes(png(2, 2, colour))
    return seam.Shown(path, seam.PNG)


IMAGE = element(
    "image",
    "figure/picture",
    x=140,
    y=10,
    width=50,
    height=50,
    output="square",
    preserveAspectRatio="xMidYMid meet",
    variants={},
    points={},
)


def shown_apart(folder: Path) -> dict[str, dict[str, Any]]:
    """A picture for each key, of a colour of its own."""
    return {
        "default": {"figure/picture": picture_file(folder, "light", (200, 30, 30, 255))},
        DARK: {"figure/picture": picture_file(folder, "dark", (30, 60, 200, 128))},
    }


# --- what it declares ---------------------------------------------------------------------------


def test_it_declares_svg_modes_with_the_colour_schemes_pairs_and_no_contrast_pair() -> None:
    assert svg_declaration.DECLARATION["holds-modes"] == {
        MODES: {
            "colour-scheme": {
                "signal": "prefers-color-scheme",
                "pairs": {"light": "light", "dark": "dark"},
            }
        }
    }
    assert svg.VERSION == "1.3.0"


@pytest.mark.parametrize("roles", foundations_majors(), ids=lambda path: path.parent.name)
def test_each_pair_holds_to_an_axis_of_kind_value_and_its_modes_in_each_major_of_the_foundations(
    roles: Path,
) -> None:
    axes = reading.read_yaml(roles)["axes"]
    for axis, pair in svg_declaration.DECLARATION["holds-modes"][MODES].items():
        assert axes[axis]["kind"] == "value"
        assert sorted(pair["pairs"]) == sorted(axes[axis]["modes"])
        assert len(set(pair["pairs"].values())) == len(pair["pairs"])


# --- what a switching file draws ----------------------------------------------------------------

#: What a switching file writes only so a rule can reach it: a paint's mark, a picture's, and
#: the second style, which holds the rules.
MARKED = re.compile(r' data-(?:fill|stroke|shown-in)="[^"]*"|<style>@media [^<]*</style>')


def test_shapes_are_drawn_as_a_switching_file_as_pinned_for_version_1_1_0() -> None:
    [page] = switched(SHAPES).pages
    assert page.svg == (
        HEAD + "<defs><style>text{white-space:pre}</style>"
        "<style>@media (prefers-color-scheme:dark){"
        '[data-fill="accent"]{fill:none}'
        '[data-fill="surface"]{fill:#000000;fill-opacity:1}'
        '[data-stroke="border"]{stroke:#808080;stroke-opacity:1}'
        '[data-stroke="shade"]{stroke:#ffffff;stroke-opacity:1}'
        "}</style></defs>"
        '<g data-id="figure" data-component="foundations/figure" data-version="1.0.0">'
        '<rect data-id="figure/back" x="1" y="1" width="198" height="98" rx="4" '
        'fill="#ffffff" data-fill="surface" stroke="#808080" data-stroke="border" '
        'stroke-width="2"/>'
        '<g data-id="figure/mark" data-component="tests/card" data-version="1.0.0" '
        'transform="translate(10.5,20)">'
        '<ellipse data-id="figure/mark/dot" cx="25" cy="15" rx="25" ry="15" fill="#4080bf" '
        'data-fill="accent"/>'
        '<line data-id="figure/mark/rule" x1="0" y1="40" x2="50" y2="40" stroke="#000000" '
        'stroke-opacity="0.25" data-stroke="shade" stroke-width="1.5"/>'
        "</g></g></svg>\n"
    )


def test_arrowheads_are_drawn_in_a_switching_file_as_pinned_for_version_1_1_0() -> None:
    [page] = switched(TIES).pages
    assert page.svg == (
        HEAD + "<defs><style>text{white-space:pre}</style>"
        "<style>@media (prefers-color-scheme:dark){"
        '[data-fill="ink"]{fill:#ffffff;fill-opacity:0.5}'
        '[data-fill="shade"]{fill:#ffffff;fill-opacity:1}'
        '[data-stroke="ink"]{stroke:#ffffff;stroke-opacity:0.5}'
        '[data-stroke="shade"]{stroke:#ffffff;stroke-opacity:1}'
        "}</style>"
        '<marker id="pkit-arrow-end--ink" viewBox="0 0 10 10" refX="10" refY="5" '
        'markerWidth="5" markerHeight="5" orient="auto">'
        '<path d="M0,0L10,5L0,10z" fill="#000000" data-fill="ink"/></marker>'
        '<marker id="pkit-arrow-end--shade" viewBox="0 0 10 10" refX="10" refY="5" '
        'markerWidth="5" markerHeight="5" orient="auto">'
        '<path d="M0,0L10,5L0,10z" fill="#000000" fill-opacity="0.25" data-fill="shade"/>'
        "</marker>"
        '<marker id="pkit-arrow-start--shade" viewBox="0 0 10 10" refX="0" refY="5" '
        'markerWidth="5" markerHeight="5" orient="auto">'
        '<path d="M10,0L0,5L10,10z" fill="#000000" fill-opacity="0.25" data-fill="shade"/>'
        "</marker></defs>"
        '<g data-id="figure" data-component="foundations/figure" data-version="1.0.0">'
        '<polyline data-id="figure/links[ab]/l" data-start="figure/steps[a]" '
        'data-end="figure/steps[b]" points="10,20 60,20 60,60 110,60" fill="none" '
        'stroke="#000000" data-stroke="ink" stroke-width="2" '
        'marker-end="url(#pkit-arrow-end--ink)"/>'
        '<line data-id="figure/rule" x1="0" y1="90" x2="200" y2="90" stroke="#000000" '
        'stroke-opacity="0.25" data-stroke="shade" marker-start="url(#pkit-arrow-start--shade)" '
        'marker-end="url(#pkit-arrow-end--shade)"/>'
        "</g></svg>\n"
    )


def test_the_plain_drawing_is_the_first_keys_file_its_paints_marked_and_its_rules_added() -> None:
    [page] = switched(SHAPES).pages
    [plain] = one_key(SHAPES, "default").pages
    assert page.id == plain.id
    assert MARKED.sub("", page.svg) == plain.svg


def test_a_rule_repaints_each_role_the_page_paints_under_the_signal_of_its_key() -> None:
    """The accent has no colour in the dark scheme, so its rule paints no fill there."""
    [page] = switched(SHAPES).pages
    [rules] = re.findall(r"<style>@media [^<]*</style>", page.svg)
    assert rules == (
        "<style>@media (prefers-color-scheme:dark){"
        '[data-fill="accent"]{fill:none}'
        '[data-fill="surface"]{fill:#000000;fill-opacity:1}'
        '[data-stroke="border"]{stroke:#808080;stroke-opacity:1}'
        '[data-stroke="shade"]{stroke:#ffffff;stroke-opacity:1}'
        "}</style>"
    )
    assert (
        '<ellipse data-id="figure/mark/dot" cx="25" cy="15" rx="25" ry="15" fill="#4080bf" '
        'data-fill="accent"/>'
    ) in page.svg


def test_a_role_with_no_colour_in_one_key_is_a_loss_that_names_that_key() -> None:
    assert switched(SHAPES).losses == [
        seam.Loss(
            "svg",
            "figure/mark/dot",
            seam.LEFT_OUT,
            f"the brand gives the role `accent` of its fill no colour in `{DARK}`",
            DARK,
        )
    ]


def test_a_paint_the_first_key_leaves_out_is_marked_and_a_rule_paints_it() -> None:
    dark_first = {DARK: COMBINATIONS[DARK], "default": COMBINATIONS["default"]}
    [page] = switched(SHAPES, dark_first).pages
    dot = ElementTree.fromstring(page.svg).find(".//*[@data-id='figure/mark/dot']")
    assert dot is not None
    assert (dot.get("fill"), dot.get("data-fill")) == ("none", "accent")
    assert '@media (prefers-color-scheme:light){[data-fill="accent"]{fill:#4080bf;' in page.svg
    assert 'data-key="colour-scheme.dark"' in page.svg


def test_each_arrowhead_is_drawn_for_its_end_and_role_marked_with_that_role() -> None:
    [page] = switched(TIES).pages
    root = ElementTree.fromstring(page.svg)
    markers = {
        marker.get("id"): marker[0].get("data-fill")
        for marker in root.iter("{http://www.w3.org/2000/svg}marker")
    }
    assert markers == {
        "pkit-arrow-end--ink": "ink",
        "pkit-arrow-end--shade": "shade",
        "pkit-arrow-start--shade": "shade",
    }
    assert '[data-fill="ink"]{fill:#ffffff;fill-opacity:0.5}' in page.svg


def test_a_picture_every_key_shows_alike_is_drawn_once(tmp_path: Path) -> None:
    alike = picture_file(tmp_path, "alike", (200, 30, 30, 255))
    pictures = {key: {"figure/picture": alike} for key in COMBINATIONS}
    drawn = switched(scene(IMAGE), pictures=pictures)
    [page] = drawn.pages
    assert page.svg.count("<image ") == 1
    assert "data-shown-in" not in page.svg
    assert "@media" not in page.svg
    assert drawn.losses == []


def test_a_picture_shown_otherwise_is_drawn_for_each_key_and_a_rule_shows_its_own(
    tmp_path: Path,
) -> None:
    [page] = switched(scene(IMAGE), pictures=shown_apart(tmp_path)).pages
    images = list(ElementTree.fromstring(page.svg).iter("{http://www.w3.org/2000/svg}image"))
    assert [(image.get("data-shown-in"), image.get("display")) for image in images] == [
        ("default", None),
        (DARK, "none"),
    ]
    assert page.svg.endswith("</svg>\n")
    assert (
        "@media (prefers-color-scheme:dark){[data-shown-in]{display:none}"
        '[data-shown-in~="colour-scheme.dark"]{display:inline}}'
    ) in page.svg


def test_an_image_with_no_picture_in_one_key_is_a_loss_there_and_hidden_by_its_rule(
    tmp_path: Path,
) -> None:
    pictures = {"default": shown_apart(tmp_path)["default"]}
    drawn = switched(scene(IMAGE), pictures=pictures)
    [page] = drawn.pages
    assert re.findall(r'data-shown-in="([^"]*)"', page.svg) == ["default"]
    assert [loss.key for loss in drawn.losses] == [DARK]
    assert "[data-shown-in]{display:none}" in page.svg


def test_a_file_of_one_key_holds_no_rule_and_its_loss_names_no_key() -> None:
    drawn = switched(SHAPES, {DARK: COMBINATIONS[DARK]})
    [page] = drawn.pages
    assert "@media" not in page.svg
    assert 'data-fill="surface"' in page.svg
    assert [loss.key for loss in drawn.losses] == [None]


@pytest.mark.parametrize(
    ("form", "keys", "said"),
    [
        ("svg-pages", COMBINATIONS, "the svg renderer writes no format `svg-pages`"),
        (MODES, {}, "a switching file holds at least one key"),
        (
            MODES,
            {"default": {"contrast": "standard"}, "contrast.high": {"contrast": "high"}},
            "`contrast.high` and `default` differ in `contrast`, whose mode `high` pairs with no "
            "signal, so no file holds both",
        ),
    ],
    ids=["a-format-it-does-not-declare", "no-key", "a-mode-of-no-pair"],
)
def test_it_refuses_what_no_switching_file_can_hold(
    form: str, keys: Mapping[str, Any], said: str
) -> None:
    with pytest.raises(ValueError) as raised:
        svg.render(
            SHAPES,
            form=form,
            keys=keys,
            colours=dict.fromkeys(keys, COLOURS),
            font_file=lambda _family: FONT,
            pictures={key: {} for key in keys},
        )
    assert str(raised.value) == said


def test_one_key_and_no_format_is_refused() -> None:
    with pytest.raises(ValueError):
        svg.render(SHAPES, colours=COLOURS, font_file=lambda _family: FONT, pictures={})


def test_the_same_scene_and_values_give_the_same_switching_file() -> None:
    drawn = scene(TITLE, *TIES["children"][0]["children"])
    assert switched(drawn).pages == switched(drawn).pages


# --- a switching file read in a mode ------------------------------------------------------------


def every_way(folder: Path) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    """A scene for each way a rule repaints a file, with the pictures each key shows."""
    apart = shown_apart(folder)
    return {
        "shapes": (SHAPES, {}),
        "ties": (TIES, {}),
        "text": (scene(TITLE), {}),
        "pictures-apart": (scene(IMAGE), apart),
        "a-picture-in-one-key": (scene(IMAGE), {"default": apart["default"]}),
    }


@pytest.mark.parametrize(
    "way", ["shapes", "ties", "text", "pictures-apart", "a-picture-in-one-key"]
)
@pytest.mark.parametrize("first", ["default", DARK])
def test_a_switching_file_read_in_each_key_draws_as_its_one_key_file(
    tmp_path: Path, way: str, first: str
) -> None:
    drawn, pictures = every_way(tmp_path)[way]
    keys = {first: COMBINATIONS[first], **COMBINATIONS}
    [page] = switched(drawn, keys, pictures).pages
    for key in COMBINATIONS:
        [expected] = one_key(drawn, key, pictures).pages
        assert switching.differences(page.svg, expected.svg, SIGNALS[key]) == []


def test_read_in_another_key_it_names_each_element_painted_otherwise() -> None:
    [page] = switched(SHAPES).pages
    [dark] = one_key(SHAPES, DARK).pages
    assert switching.differences(page.svg, dark.svg, SIGNALS["default"]) == [
        switching.Difference(
            "figure/back",
            "its fill is #ffffff at an opacity of 1, and the one-key file's #000000 at an "
            "opacity of 1",
        ),
        switching.Difference(
            "figure/mark/dot", "its fill is #4080bf at an opacity of 1, and the one-key file's none"
        ),
        switching.Difference(
            "figure/mark/rule",
            "its stroke is #000000 at an opacity of 0.25, 1.5 px wide, and the one-key file's "
            "#ffffff at an opacity of 1, 1.5 px wide",
        ),
    ]


def test_an_arrowhead_painted_otherwise_is_named_at_its_line() -> None:
    [page] = switched(TIES).pages
    [dark] = one_key(TIES, DARK).pages
    slipped = page.svg.replace('[data-fill="ink"]{fill:#ffffff', '[data-fill="ink"]{fill:#fefefe')
    assert switching.differences(slipped, dark.svg, SIGNALS[DARK]) == [
        switching.Difference("figure/links[ab]/l", "its arrowheads paint otherwise")
    ]


def test_with_no_signal_a_rule_applies_nothing_so_the_plain_drawing_shows() -> None:
    [page] = switched(SHAPES).pages
    [plain] = one_key(SHAPES, "default").pages
    assert switching.differences(page.svg, plain.svg, {}) == []


#: A page of one box, with a rule for the dark scheme that the tests below fill in.
def page_with(rules: str, box: str = 'fill="#ffffff" data-fill="surface"') -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" data-page="figure"><defs><style>text{}</style>'
        f"<style>@media (prefers-color-scheme:dark){{{rules}}}</style></defs>"
        f'<g data-id="figure"><rect data-id="figure/box" {box}/></g></svg>'
    )


ONE_KEY = (
    '<svg xmlns="http://www.w3.org/2000/svg" data-page="figure"><defs><style>text{}</style>'
    '</defs><g data-id="figure"><rect data-id="figure/box" fill="#000000"/></g></svg>'
)

DARK_SIGNAL = SIGNALS[DARK]


def test_a_rule_wins_over_an_attribute_and_a_later_rule_over_an_earlier() -> None:
    rules = '[data-fill="surface"]{fill:#ff0000}[data-fill]{fill:#000000}'
    assert switching.differences(page_with(rules), ONE_KEY, DARK_SIGNAL) == []
    rules = '[data-fill]{fill:#000000}[data-fill="surface"]{fill:#ff0000}'
    [found] = switching.differences(page_with(rules), ONE_KEY, DARK_SIGNAL)
    assert found.element == "figure/box"


def test_a_selector_of_a_word_matches_one_of_an_attributes_words() -> None:
    rules = '[data-shown-in~="colour-scheme.dark"]{fill:#000000}'
    box = 'fill="#ffffff" data-shown-in="default colour-scheme.dark"'
    assert switching.differences(page_with(rules, box), ONE_KEY, DARK_SIGNAL) == []


def test_an_element_not_displayed_is_not_drawn_nor_anything_below_it() -> None:
    hidden = page_with("", 'fill="#000000"').replace(
        "</g></svg>", '<g display="none"><rect fill="#ff0000"/></g></g></svg>'
    )
    assert switching.differences(hidden, ONE_KEY, DARK_SIGNAL) == []


def test_a_paint_inherited_from_its_group_counts_as_its_own() -> None:
    held = page_with("", "").replace('<g data-id="figure">', '<g data-id="figure" fill="#000000">')
    one = ONE_KEY.replace('<g data-id="figure">', '<g data-id="figure" fill="#000000">')
    assert switching.differences(held, one, DARK_SIGNAL) == []
    assert switching.differences(held, ONE_KEY, DARK_SIGNAL) == []


def test_an_element_one_file_draws_and_the_other_does_not_is_named() -> None:
    more = ONE_KEY.replace("</g></svg>", '<rect data-id="figure/more"/></g></svg>')
    assert switching.differences(page_with("[data-fill]{fill:#000000}"), more, DARK_SIGNAL) == [
        switching.Difference("figure/more", "it is not drawn")
    ]
    assert switching.differences(page_with(""), ONE_KEY, DARK_SIGNAL)[0].element == "figure/box"


def test_styles_that_differ_outside_their_rules_are_named_at_the_page() -> None:
    other = page_with("[data-fill]{fill:#000000}").replace("text{}", "text{white-space:pre}")
    assert switching.differences(other, ONE_KEY, DARK_SIGNAL) == [
        switching.Difference("figure", "its fonts or its styles differ")
    ]


def test_a_brace_or_a_rule_inside_a_string_is_text() -> None:
    named = '@font-face{font-family:"a}@media (x:y){b"}'
    held = page_with("[data-fill]{fill:#000000}").replace("text{}", named)
    one = ONE_KEY.replace("text{}", named)
    assert switching.differences(held, one, DARK_SIGNAL) == []


@pytest.mark.parametrize(
    ("rules", "said"),
    [
        ("rect{fill:#000000}", "a rule `rect{fill:#000000}` cannot be read"),
        ("[data-fill]{fill:#000000;}", "a declaration `` cannot be read"),
        ('[data-fill]{fill:url("x")}', 'a rule `[data-fill]{fill:url("x")}` cannot be read'),
    ],
    ids=["a-selector-of-a-name", "an-empty-declaration", "a-string-in-a-value"],
)
def test_a_rule_it_cannot_read_is_one_difference_at_the_page(rules: str, said: str) -> None:
    assert switching.differences(page_with(rules), ONE_KEY, DARK_SIGNAL) == [
        switching.Difference("figure", f"the switching file cannot be read: {said}")
    ]


@pytest.mark.parametrize(
    ("media", "said"),
    [
        ("@media screen{}", "an `@media` rule's conditions `screen` cannot be read"),
        ("@media (prefers-color-scheme:dark){", "an `@media` rule's block does not close"),
    ],
    ids=["conditions-of-another-form", "a-block-that-does-not-close"],
)
def test_an_at_media_rule_it_cannot_read_is_one_difference_at_the_page(
    media: str, said: str
) -> None:
    held = ONE_KEY.replace("text{}", f"text{{}}{media}")
    assert switching.differences(held, ONE_KEY, DARK_SIGNAL) == [
        switching.Difference("figure", f"the switching file cannot be read: {said}")
    ]


def test_an_arrowhead_that_names_no_marker_cannot_be_read() -> None:
    held = page_with("[data-fill]{fill:#000000}").replace(
        "data-fill=", 'marker-end="url(#nowhere)" data-fill='
    )
    [found] = switching.differences(held, ONE_KEY, DARK_SIGNAL)
    assert found.why == (
        "the switching file cannot be read: an arrowhead `url(#nowhere)` names no marker of "
        "the file"
    )


# --- a real browser (DEC-018 point 1, The same drawing) -----------------------------------------


def shown_as_an_image(folder: Path, name: str, drawn: str) -> Path:
    """A page that shows `drawn` as an image, as a Markdown page shows a figure, at its
    natural size."""
    data = base64.b64encode(drawn.encode("utf-8")).decode("ascii")
    path = folder / f"{name}.html"
    path.write_text(
        "<!doctype html><html><head><style>body{margin:0}img{display:block}</style></head>"
        f'<body><img src="data:image/svg+xml;base64,{data}" alt=""></body></html>',
        encoding="utf-8",
    )
    return path


@real_browser
def test_a_real_browser_draws_a_switching_file_in_each_mode_as_its_one_key_file(
    tmp_path: Path,
) -> None:
    """A figure of every way a rule repaints it: shapes, text, arrowheads and a picture of a
    variant for each mode. In each mode, the switching file shown as an image draws pixel for
    pixel as the one-key file of that mode, and the two modes draw apart. The two files are
    held to each other in one browser, so no pixel of either is held as a contract (DEC-015
    point 6)."""
    ties = TIES["children"][0]["children"]
    drawn = scene(*SHAPES["children"][0]["children"], TITLE, *ties, IMAGE)
    pictures = shown_apart(tmp_path)
    files = {"switching": switched(drawn, pictures=pictures).pages[0].svg}
    for key in COMBINATIONS:
        files[key] = one_key(drawn, key, pictures).pages[0].svg
    pages = {name: shown_as_an_image(tmp_path, name, text) for name, text in files.items()}
    browser = found_browser()
    assert browser is not None
    place = tmp_path / "browser"
    place.mkdir()
    started = viewing_browser._Started(browser, place, 200, 1.0)
    taken: dict[tuple[str, str], bytes] = {}
    try:
        started.call("Browser.getVersion", within=viewing_browser.START_SECONDS)
        started.open_tab()
        for key, signals in SIGNALS.items():
            started.emulate(signals)
            for name in ("switching", key):
                started.open(pages[name].resolve().as_uri())
                started.ask(viewing_browser.SETTLE)
                clip = {"x": 0, "y": 0, "width": 200, "height": 100}
                taken[name, key] = started.picture(clip)
    except viewing_browser.Stopped as stop:
        if stop.sandbox:
            pytest.skip(f"a sandbox stopped the browser: {stop}")
        raise
    finally:
        started.close()
    for key in SIGNALS:
        assert taken["switching", key] == taken[key, key]
    assert taken["default", "default"] != taken[DARK, DARK]
