"""What each scene check states of itself (visual-communication DEC-063 point 1, DEC-062
points 1 and 2): its reach, in its entry in `checks.md` and in its code, joined on its id,
and a planted case for each clause of each reach.

- **Entry and code.** Each check that states a reach shows its id in one entry, whose words
  are the code's, and the entry carries each label the check's findings take.
- **A planted case for each clause.** A place of the kind the clause names, with a fault
  there: where the reach measures the kind, the check reports the fault; where it leaves it
  out, the check gives no finding; where a statement covers it, the check states so. Each
  clause of each reach has a case, so a clause the code does not keep fails one.
- **Scene by scene.** Each check gives its findings scene by scene, tagged with its scene,
  before the render's merges, and the findings record keeps the statement of the check of
  edges that nearly line up as any other scene finding.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from ruamel.yaml import YAML

from tests import test_visual_communication_site as site
from tests.in_process import load
from tests.test_visual_communication_boxes import (
    STEP,
    element,
    filling,
    group,
    items,
    line,
    node,
    on_page,
    px,
    scene,
    text,
    tied,
)
from tests.test_visual_communication_checks import COLOURS, colour, page, project_of, run, runs
from tests.test_visual_communication_checks import box as filled
from tests.test_visual_communication_checks import text as painted
from tests.test_visual_communication_letters import (
    CODE_FAMILY,
    drawn,
    element_of,
    found,
    touching,
)
from tests.test_visual_communication_pipeline import NARROW, add_device, drawing_project, flipping
from tests.visual_communication_project import project, write, yaml_text

checks, boxes, scene_checks, findings, rendering, pl, text_size, layout, formula = load(
    "visual-communication",
    "checks",
    "boxes",
    "scene_checks",
    "findings",
    "rendering",
    "pipeline",
    "text_size",
    "layout",
    "formula",
)

CAPABILITY = Path(__file__).parents[1] / ".pkit" / "capabilities" / "visual-communication"

#: The checks that state a reach, by their ids.
REACHING = {check.id: check for check in checks.SCENE_CHECKS if check.reach is not None}

_REACH = re.compile(r"\*\*Its reach\*\*, `(?P<id>[a-z-]+)`\.")


def _entries() -> dict[str, str]:
    """Each row of `checks.md` that shows a check's reach, by the check's id."""
    found: dict[str, str] = {}
    for row in (CAPABILITY / "checks.md").read_text(encoding="utf-8").splitlines():
        for each in _REACH.finditer(row):
            assert each["id"] not in found, each["id"]
            found[each["id"]] = row
    return found


def test_the_checks_the_reviewer_leans_on_state_a_reach() -> None:
    assert set(REACHING) == {
        "content-a-size-hides",
        "contrast-as-drawn",
        "edges-nearly-in-line",
        "boxes-that-overlap",
        "letters-across-lines",
        "text-size-by-medium",
    }
    assert len({check.id for check in checks.SCENE_CHECKS if check.id}) == len(REACHING)


@pytest.mark.parametrize("id_", sorted(REACHING))
def test_an_entry_states_its_check_s_reach_in_the_code_s_words(id_: str) -> None:
    check = REACHING[id_]
    assert check.reach is not None
    row = _entries()[id_]
    assert check.reach.said(id_) in row
    labels = row.split("|")[1]
    for label in check.labels:
        assert f"`{label}`" in labels, label


def test_every_reach_the_page_shows_is_one_the_code_states() -> None:
    assert set(_entries()) == set(REACHING)


def test_the_page_says_a_reach_s_words_are_in_the_code() -> None:
    page_text = (CAPABILITY / "checks.md").read_text(encoding="utf-8")
    assert "A reach's words are in the check's code" in page_text


def test_a_reach_comes_beside_an_id_and_only_with_one() -> None:
    reach = scene_checks.Reach(measures=("a",), leaves_out=("b",))
    with pytest.raises(ValueError, match="beside its id"):
        scene_checks.SceneCheck("one", reach=reach)
    with pytest.raises(ValueError, match="beside its id"):
        scene_checks.SceneCheck("one", id="one")
    with pytest.raises(ValueError, match="sizes and languages"):
        scene_checks.SceneCheck("one", frozenset({"pages"}))


# --- the planted cases --------------------------------------------------------------------------


def near(*children: dict[str, Any], step: Any = STEP) -> list[str]:
    return [f.code for f in boxes.near_alignment(scene(*children), step)]


def overlap(*children: dict[str, Any]) -> list[str]:
    return [f.code for f in boxes.overlaps(scene(*children))]


def pages(*children: dict[str, Any]) -> dict[str, Any]:
    """A scene of two pages side by side, each a group marked a page."""
    return {
        "pages": [child["id"] for child in children],
        "children": [{**child, "page": True} for child in children],
    }


A = element("figure/a")


def _near_pair() -> None:
    assert near(A, element("figure/b", x=2.5, y=60)) == [boxes.NEAR_ALIGNMENT]


def _near_insets() -> None:
    outer = element("figure/card", width=100, height=100)
    inner = element("figure/head", x=10, y=10, width=78, height=80)
    assert near(outer, inner) == [boxes.NEAR_ALIGNMENT]


def _near_spacings() -> None:
    row = (A, element("figure/b", x=50), element("figure/c", x=102.5))
    assert [f.message.split(":")[0] for f in boxes.near_alignment(scene(*row), STEP)] == [
        "the gaps across in `figure` nearly agree"
    ]


def _apart_in_groups(check: Callable[..., list[str]], offset: float) -> None:
    first = group("figure/one", element("figure/one/a"), width=50, height=50)
    second = group("figure/two", element("figure/two/b", x=offset), y=100, width=50, height=50)
    assert check(first, second) == []


def _lines_and_ties(check: Callable[..., list[str]]) -> None:
    across = line("figure/l", 2.5, 20, 42.5, 60)
    tie = group("figure/tie", line("figure/tie/l", 0, 0, 40, 40), x=2.5, y=20, width=40, height=40)
    assert check(A, across) == []
    assert check(A, tie) == []


def _of_no_area(check: Callable[..., list[str]]) -> None:
    assert check(A, element("figure/b", x=2.5, y=10, width=0)) == []
    assert check(A, element("figure/b", x=2.5, y=10, height=0)) == []


def _pages_beside(measure: Callable[[dict[str, Any]], list[Any]]) -> None:
    first = group("one", element("one/a"), width=400, height=200)
    second = group("two", element("two/a"), x=2.5, y=20, width=400, height=200)
    assert measure(pages(first, second)) == []


def _near_other_lines() -> None:
    assert near(A, element("figure/b", y=60, width=43)) == []
    _between_other_lines()


def _near_held_edges() -> None:
    outer = element("figure/card", width=100, height=100)
    assert near(outer, element("figure/head", x=2.5, y=2.5, width=95, height=95)) == []
    _between_held_edges()


def _near_inset_on_an_edge() -> None:
    outer = element("figure/card", width=100, height=100)
    assert near(outer, element("figure/head", x=0.5, y=10, width=96.5, height=80)) == []
    _between_inset_on_an_edge()


def _near_gap_not_beside() -> None:
    row = (A, element("figure/b", x=50, y=39.5), element("figure/c", x=102.5))
    assert near(*row) == []


def _near_states_no_step() -> None:
    pair = (A, element("figure/b", x=2.5, y=60))
    assert near(*pair, step=None) == [boxes.NEAR_ALIGNMENT_UNMEASURED]
    assert near(*pair, step=boxes.Step("space.1", 1.0)) == [boxes.NEAR_ALIGNMENT_UNMEASURED]
    [stated] = boxes.near_alignment(scene(*pair), None)
    assert (stated.level, stated.who) == (findings.FACT, "")
    one = group("figure/one", element("figure/one/a"), width=200, height=200)
    two = group("figure/two", element("figure/two/b", x=2.5, y=60), width=200, height=200)
    assert near(one, two, step=None) == [boxes.NEAR_ALIGNMENT_UNMEASURED]
    lists = on_page(items("page/a", 20, 12), items("page/b", 400, 14))
    assert [f.code for f in boxes.near_alignment(lists, None)] == [boxes.NEAR_ALIGNMENT_UNMEASURED]


BETWEEN = boxes.NEAR_ALIGNMENT_BETWEEN_GROUPS


def in_two_groups(first: dict[str, Any], second: dict[str, Any]) -> list[str]:
    """The labels the check of edges that nearly line up gives `first`, in the group
    `figure/one`, and `second`, in the group `figure/two`, the two groups' frames alike."""
    one = group("figure/one", first, width=200, height=200)
    two = group("figure/two", second, width=200, height=200)
    return near(one, two)


def _near_between_groups() -> None:
    assert in_two_groups(element("figure/one/a"), element("figure/two/b", x=2.5, y=60)) == [BETWEEN]
    outer = element("figure/one/card", width=100, height=100)
    assert in_two_groups(outer, element("figure/two/head", x=10, y=10, width=78, height=80)) == [
        BETWEEN
    ]


def _near_lists() -> None:
    found = boxes.near_alignment(on_page(items("page/a", 20, 12), items("page/b", 400, 14)), STEP)
    assert [(f.code, f.message.split(" `")[0]) for f in found] == [
        (BETWEEN, "the spacings of the lists")
    ]


def _between_pages() -> None:
    _pages_beside(lambda given: boxes.near_alignment(given, STEP))
    one = group("figure/one", element("figure/one/a"), width=50, height=50)
    two = group("figure/two", element("figure/two/b", x=2.5), y=100, width=50, height=50)
    assert boxes.near_alignment({"pages": [], "children": [one, two]}, STEP) == []


def _group_with_no_sibling() -> None:
    one = group("figure/one", element("figure/one/a", x=10), width=50, height=50)
    two = group("figure/two", element("figure/two/b", x=2.5), y=100, width=100, height=50)
    assert near(one, two) == []


def _tie_s_part() -> None:
    assert boxes.near_alignment(tied(), STEP) == []
    assert [f.code for f in boxes.near_alignment(tied(connector=False), STEP)] == [BETWEEN]


def _text_s_lines() -> None:
    box = element("figure/box", width=100, height=20)
    assert near(box, text("figure/lead", x=-97.5, y=60, width=200, lines=(80,))) == []
    assert near(box, filling("figure/lead", x=2.5, y=60, width=100)) == [boxes.NEAR_ALIGNMENT]
    first = text("figure/first", width=200, lines=(80,))
    second = text("figure/second", x=-97.5, y=40, width=200, lines=(80,), anchor="middle")
    assert near(first, second) == []


def _text_s_insets() -> None:
    box = element("figure/box", width=100, height=30)
    assert near(box, text("figure/label", x=8, y=4, width=82, height=22)) == []
    assert near(box, filling("figure/label", x=8, y=4, width=82, height=22)) == [
        boxes.NEAR_ALIGNMENT
    ]
    room = text("figure/text", width=100, height=40, lines=(60,))
    assert near(room, element("figure/box", x=10, y=10, width=78, height=20)) == []


def _text_s_gaps() -> None:
    row = [text(f"figure/{n}", x=x, width=100, lines=(60,)) for n, x in enumerate((0, 116, 235))]
    assert near(*row) == []
    filled = [filling(f"figure/{n}", x=x, width=100) for n, x in enumerate((0, 116, 235))]
    assert near(*filled) == [boxes.NEAR_ALIGNMENT]


def _spacings(found: list[Any]) -> list[Any]:
    return [f for f in found if f.message.startswith("the spacings of the lists")]


def _other_groups_spacings() -> None:
    def rows(trace: str, x: float, gap: float) -> dict[str, Any]:
        parts = [element(f"{trace}/{n}", y=n * (40 + gap), width=200) for n in range(4)]
        return group(trace, *parts, x=x, y=40, width=200, height=300)

    assert (
        _spacings(
            boxes.near_alignment(on_page(rows("page/a", 20, 12), rows("page/b", 400, 14)), STEP)
        )
        == []
    )
    unlike = on_page(items("page/a", 20, 12), items("page/b", 400, 14, drawn_by="tests/tag"))
    assert _spacings(boxes.near_alignment(unlike, STEP)) == []
    first, tall = node("page/tree#1", 0, 300, (14, 16))
    second, other = node("page/tree#2", tall + 12, 300, (14, 16))
    tree = group("page/tree", first, second, x=20, y=20, width=300, height=tall + 12 + other)
    assert boxes.near_alignment(on_page(tree), STEP) == []


def _gap_between_groups() -> None:
    one = group("page/one", element("page/one/a"), element("page/one/b", x=48), width=88)
    two = group("page/two", element("page/two/c", x=10, width=40), x=88, width=50)
    assert boxes.near_alignment(on_page(one, two), STEP) == []


def _list_s_own_spacing() -> None:
    first = items("page/a", 20, 12)
    for n, entry in enumerate(first["children"][2:], start=3):
        entry["y"] = (n - 1) * 42 + 2
    found = boxes.near_alignment(on_page(first, items("page/b", 400, 14)), STEP)
    assert [f.code for f in found].count(boxes.NEAR_ALIGNMENT) == 1
    assert _spacings(found) == []


def _between_other_lines() -> None:
    assert in_two_groups(element("figure/one/a"), element("figure/two/b", y=60, width=43)) == []


def _between_held_edges() -> None:
    outer = element("figure/one/card", width=100, height=100)
    held = element("figure/two/head", x=2.5, y=2.5, width=95, height=95)
    assert in_two_groups(outer, held) == []


def _between_inset_on_an_edge() -> None:
    outer = element("figure/one/card", width=100, height=100)
    held = element("figure/two/head", x=0.5, y=10, width=96.5, height=80)
    assert in_two_groups(outer, held) == []


def _overlap_pair() -> None:
    assert overlap(A, element("figure/b", x=20, y=20)) == [boxes.BOX_OVERLAP]


def _overlap_held() -> None:
    assert overlap(element("figure/card", width=100, height=100), element("figure/b", x=10)) == []


def _hidden(shown: dict[tuple[str, str], set[str]]) -> list[str]:
    return [f.where for f in checks._hidden("en", "device.phone", shown)]


def _hidden_content() -> None:
    shown = {("en", "default"): {"body.note", "body.note.text"}, ("en", "device.phone"): set()}
    assert _hidden(shown) == ["body.note"]


def _hidden_nowhere() -> None:
    shown = {("en", "default"): {"body.head"}, ("en", "device.phone"): {"body.head"}}
    assert _hidden(shown) == []


def _hidden_not_content() -> None:
    own = {"type": "text", "id": "figure/label", "sources": {"text": "component:label"}}
    at_default = checks._content_shown({"children": [own]})
    assert at_default == set()
    assert _hidden({("en", "default"): at_default, ("en", "device.phone"): set()}) == []


#: The top the cases of a text's size declare their smallest sizes in.
TOP = "lib/top"


def run_of(size: float, family: str = "Source Sans Pro") -> dict[str, Any]:
    return {"font-size": size, "style": "type.body", "font-family": [family]}


def sized_text(
    trace: str, *sizes: float, lines: bool = True, family: str = "Source Sans Pro"
) -> dict[str, Any]:
    """A text of one paragraph, a run at each of `sizes`, each drawn on a line of its own
    unless `lines` is false, so the text draws nothing."""
    runs = [
        {**run_of(size, family), "sources": {"text": f"content:{trace}.runs[{index}]"}}
        for index, size in enumerate(sizes)
    ]
    drawn = [{"paragraph": 0, "spans": [{"run": index}]} for index in range(len(sizes))]
    return {"type": "text", "id": trace, "paragraphs": [runs], "lines": drawn if lines else []}


def sized_page(
    *children: dict[str, Any], width: float = 400, height: float = 300
) -> dict[str, Any]:
    """A scene of one page, `children` on it."""
    page_ = {"type": "group", "id": "page", "width": width, "height": height}
    return {"pages": ["page"], "children": [{**page_, "children": list(children)}]}


def by_medium(
    scene_: dict[str, Any],
    *,
    media: Any = ("screen",),
    smallest: dict[str, Any] | None = None,
    asks: bool = True,
    size: str | None = "desktop",
) -> list[tuple[str, str]]:
    """What the check of a text's size gives on `scene_`, the scene of a piece whose `media`
    are `media`, a list or a mapping, drawn at the size `size`, under a top that declares
    `smallest`, a fixed 12 px for a screen unless it says otherwise, each value a formula's
    text or a length; each label with where it lies."""
    named: dict[str, Any] | None = None
    if isinstance(media, dict):
        named = {medium: tuple(sizes) for medium, sizes in media.items()}
    elif media is not None:
        named = {medium: None for medium in media}
    given = {
        medium: formula.parse(value) if isinstance(value, str) else value
        for medium, value in (smallest if smallest is not None else {"screen": 12}).items()
    }
    project_ = SimpleNamespace(
        piece=SimpleNamespace(media=named, top=TOP),
        size_of=lambda _key: size,
    )
    result = SimpleNamespace(
        scene=SimpleNamespace(size_key="default"),
        smallest=layout.SmallestText(TOP, "lib@1.0.0", given),
        heights={"page": layout.PageHeight(asks=asks, own=True)},
    )
    found = text_size.found(project_, "en", result, scene_, checks.ENGINE)
    return [(each.finding.code, each.finding.where) for each in found]


SMALL = [(text_size.TEXT_TOO_SMALL, "page/t")]
UNMEASURED_AT_MEDIA = [(text_size.TEXT_SIZE_UNMEASURED, "media")]


def _sized_runs() -> None:
    assert by_medium(sized_page(sized_text("page/t", 11.99))) == SMALL
    assert by_medium(sized_page(sized_text("page/t", 12, 14))) == []
    assert by_medium(sized_page(sized_text("page/t", 9, 8))) == SMALL * 2


def _sized_pages() -> None:
    share = {"screen": "=:page-height / 25"}
    assert by_medium(sized_page(sized_text("page/t", 11.99)), smallest=share) == SMALL
    smaller = sized_page(sized_text("page/t", 11.99), height=250)
    assert by_medium(smaller, smallest=share) == []


def _sized_pictures() -> None:
    picture = {"type": "image", "id": "page/picture", "width": 100, "height": 100}
    assert by_medium(sized_page(picture)) == []


def _sized_faces() -> None:
    narrow = sized_text("page/t", 12, family="A Face Whose Letters Stand Small")
    assert by_medium(sized_page(narrow)) == []


def _sized_viewers() -> None:
    for width in (320, 2560):
        assert by_medium(sized_page(sized_text("page/t", 12), width=width)) == []


def _sized_no_lines() -> None:
    assert by_medium(sized_page(sized_text("page/t", 4, lines=False))) == []


def _sized_off_pages() -> None:
    off = {"pages": ["page"], "children": [sized_text("top/t", 4), {"type": "group", "id": "page"}]}
    assert by_medium(off) == []


def _sized_no_medium() -> None:
    assert by_medium(sized_page(sized_text("page/t", 4)), media=None) == UNMEASURED_AT_MEDIA


def _sized_undeclared() -> None:
    small = sized_page(sized_text("page/t", 4))
    assert by_medium(small, media=("room",)) == UNMEASURED_AT_MEDIA
    assert by_medium(small, media={"room": ["desktop"]}) == UNMEASURED_AT_MEDIA


def _sized_unshown() -> None:
    small = sized_page(sized_text("page/t", 4))
    assert by_medium(small, media={"screen": ["phone"]}) == UNMEASURED_AT_MEDIA


def _sized_no_share() -> None:
    small = sized_page(sized_text("page/t", 4))
    height = {"screen": "=:page-height / 25"}
    assert by_medium(small, smallest=height, asks=False) == [
        ("formula-reach", f"{layout.SMALLEST_TEXT}.screen"),
        (text_size.TEXT_SIZE_UNMEASURED, "page"),
    ]
    zero = {"screen": "=:page-width - :page-width"}
    assert by_medium(small, smallest=zero) == [
        ("component-shape", "lock"),
        (text_size.TEXT_SIZE_UNMEASURED, "page"),
    ]


#: The colours of the contrast cases: `faded` has no colour in the dark, and `haze` is half
#: of white.
COLOURED = {
    **COLOURS,
    "faded": {"default": colour(0.9), "colour-scheme.dark": None},
    "haze": {"default": colour(1, 0.5), "colour-scheme.dark": colour(1, 0.5)},
}
BOTH = ["default", "colour-scheme.dark"]


def contrast(*children: dict[str, Any], keys: list[str] = BOTH) -> list[tuple[str, ...]]:
    """Each finding of contrast on a page of `children`, as the combinations it names."""
    found = checks.drawn_contrast(page(*children), COLOURED, keys)
    return [tuple(f.extra.get("combinations", ())) for f in found]


PICTURE = {"type": "image", "id": "figure/pic", "x": 0, "y": 0, "width": 400, "height": 100}
PAPER = filled("figure/back", "paper")


def path(trace: str, **paints: Any) -> dict[str, Any]:
    """A path of an outline 20 px square at the page's corner, painted as `paints` says."""
    shape = {"type": "path", "id": trace, "x": 0, "y": 0, "width": 20, "height": 20}
    return {**shape, "d": "M0 0H20V20H0Z", "stroke-width": 1, **paints}


def cover(trace: str, fill: str, d: str = "M0 0H400V100H0Z") -> dict[str, Any]:
    """A path in the page's whole frame, filled `fill` within its outline `d`, unstroked."""
    return {**path(trace, fill=fill), "width": 400, "height": 100, "d": d, "stroke-width": 0}


def ground(fill: str, under: str | None) -> dict[str, Any]:
    """A text of one run painted `fill`, on a ground painted `under`, if any."""
    held = painted("figure/t", fill)
    held["paragraphs"][0][0] = {**held["paragraphs"][0][0], "ground": under}
    held["lines"][0]["spans"][0]["ground"] = {"start": 2, "end": 2}
    return held


def signed(fill: str) -> dict[str, Any]:
    """A text of one run painted `fill`, its sign, 10 px square, before its span."""
    held = painted("figure/t", fill)
    held["lines"][0]["spans"][0]["sign"] = {"size": 10, "top": 5, "gap": 2}
    return held


def _contrast_runs() -> None:
    assert contrast(PAPER, painted("figure/t", "pale")) == [("default",), ("colour-scheme.dark",)]
    unpainted = runs("figure/t", [{**run("ink"), "fill": None}])
    found = checks.drawn_contrast(page(filled("figure/back", "ink"), unpainted), COLOURED, BOTH)
    assert [f.message.split(" has ")[0] for f in found] == ["`black` on `ink`"]
    # A span over a picture leaves the text's other spans measured.
    under_the_first = {**PICTURE, "width": 40}
    two = runs("figure/t", [run("ink"), run("pale")])
    assert contrast(PAPER, under_the_first, two) == [("default",), ("colour-scheme.dark",)]


def _contrast_signs() -> None:
    assert contrast(PAPER, path("figure/sign", fill="pale", stroke="pale")) == [
        ("default",),
        ("colour-scheme.dark",),
    ]
    assert contrast(PAPER, path("figure/sign")) == [()]
    marked = checks.drawn_contrast(
        page(PAPER, filled("figure/dot", "ink", width=10), signed("ink")), COLOURED, ["default"]
    )
    assert ["the sign of a run" in f.message for f in marked] == [True]


def _contrast_fills() -> None:
    veiled = (PAPER, filled("figure/veil", "veil"), painted("figure/t", "mist"))
    assert contrast(*veiled, keys=["default"]) == [("default",)]
    ellipse = {**filled("figure/round", "paper"), "type": "ellipse"}
    within = painted("figure/t", "pale", x=150)
    assert contrast(filled("figure/back", "ink"), ellipse, within, keys=["default"]) == [
        ("default",)
    ]
    assert contrast(filled("figure/back", "ink"), ellipse, painted("figure/t", "pale")) == []
    assert contrast(filled("figure/back", "ink"), ground("pale", "paper"), keys=["default"]) == [
        ("default",)
    ]
    # A run's ground lies over a picture as over any fill.
    assert contrast(PICTURE, ground("pale", "paper"), keys=["default"]) == [("default",)]
    # A path's fill lies under a span and a sign drawn after it, where its outline, by its
    # rule, fills their middle, whatever its frame holds.
    ink, pale = filled("figure/back", "ink"), painted("figure/t", "pale")
    sign = path("figure/sign", fill="pale", stroke="pale")
    assert contrast(ink, cover("figure/cover", "paper"), pale, keys=["default"]) == [("default",)]
    assert contrast(ink, cover("figure/cover", "paper"), sign, keys=["default"]) == [("default",)]
    assert contrast(ink, cover("figure/corner", "paper", "M400 0V100H0Z"), pale) == []
    holed = cover("figure/holed", "paper", "M0 0H400V100H0Z M10 5H30V15H10Z")
    assert contrast(ink, holed, pale, keys=["default"]) == [("default",)]
    assert contrast(ink, {**holed, "fill-rule": "evenodd"}, pale) == []


def _contrast_over_a_picture() -> None:
    assert contrast(PICTURE, painted("figure/t", "pale")) == []
    assert contrast(PAPER, PICTURE, painted("figure/t", "pale")) == []
    assert contrast(PICTURE, path("figure/sign", fill="pale", stroke="pale")) == []
    assert contrast(PICTURE, PAPER, painted("figure/t", "pale")) != []
    assert contrast(PICTURE, cover("figure/cover", "paper"), painted("figure/t", "pale")) != []
    # Only the span over the picture is left out.
    under_the_first = {**PICTURE, "width": 40}
    assert contrast(PAPER, under_the_first, runs("figure/t", [run("pale"), run("ink")])) == []


def _contrast_over_nothing() -> None:
    assert contrast(painted("figure/t", "pale")) == []
    assert contrast(path("figure/sign", fill="pale", stroke="pale")) == []
    # A path that only strokes its outline draws no fill under the text.
    unfilled = {**cover("figure/outline", "paper"), "fill": None}
    stroked = {**unfilled, "stroke": "paper", "stroke-width": 1}
    assert contrast(stroked, painted("figure/t", "pale")) == []
    assert contrast(ground("pale", "paper"), keys=["default"]) == [("default",)]


def _contrast_unknown_role() -> None:
    assert contrast(PAPER, painted("figure/t", "nowhere")) == []
    assert contrast(filled("figure/back", "nowhere"), painted("figure/t", "pale")) == []
    assert contrast(PAPER, path("figure/sign", fill="pale", stroke="nowhere")) == []


def _contrast_no_ink() -> None:
    assert contrast(PAPER, painted("figure/t", "faded")) == [("default",)]
    assert contrast(PAPER, path("figure/sign", fill="faded", stroke="faded")) == [("default",)]


def _contrast_no_opaque_fill() -> None:
    assert contrast(filled("figure/veil", "veil"), painted("figure/t", "pale")) == []
    hazes = [filled(f"figure/haze-{n}", "haze") for n in range(9)]
    assert contrast(PAPER, *hazes, painted("figure/t", "pale"), keys=["default"]) == []
    assert contrast(PAPER, *hazes[1:], painted("figure/t", "pale"), keys=["default"]) == [
        ("default",)
    ]


def _contrast_off_the_middle() -> None:
    corner = filled("figure/corner", "ink", width=10)
    assert contrast(PAPER, corner, painted("figure/t", "ink")) == []


def _contrast_draws_nothing() -> None:
    lineless = {**painted("figure/t", "pale"), "lines": []}
    assert contrast(PAPER, lineless) == []
    assert contrast(PAPER, path("figure/sign", fill="pale", stroke="pale", d="")) == []


def _letters_across_lines() -> None:
    [said] = touching(drawn("a\ng\nÁ"))
    assert "lines 2 and 3, `g` over `Á`" in said
    signed = drawn("g\na")
    assert touching(signed) == []
    sign = {"d": "M0 0L16 0L16 16L0 16Z", "fill-rule": "nonzero", "size": 16, "top": 0, "gap": 2}
    element_of(signed)["lines"][1]["spans"][0]["sign"] = sign
    assert len(touching(signed)) == 1


def _letters_of_two_texts() -> None:
    body = {"text": {"content": "words", "style": "type.body", "fill": "text-primary"}}
    parts = {
        "t": {**body, "width": "=:width"},
        "u": {**body, "y": "=t.bottom - @space.2", "width": "=:width"},
    }
    assert touching(drawn("g", parts=parts)) == []
    assert len(touching(drawn("g\ng\nÁ"))) == 1


def _letters_drawn_to_join() -> None:
    assert touching(drawn("│\n│", 0.5, families=[CODE_FAMILY])) == []
    assert touching(drawn("▀\n▄", 0.5, families=[CODE_FAMILY])) == []
    assert touching(drawn("⌠\n⌡", 0.5, families=[CODE_FAMILY])) == []
    assert len(touching(drawn("g\nÁ", 0.5, families=[CODE_FAMILY]))) == 1


def _letters_a_renderer_wraps() -> None:
    """The engine sets the text on one line, which a renderer that wraps text itself might
    break between the two letters: the check reads the engine's line alone."""
    scene = drawn("g Á")
    assert len(element_of(scene)["lines"]) == 1
    assert found(scene) == []


def _letters_with_no_outline() -> None:
    scene = drawn("g\nÁ")
    element_of(scene)["paragraphs"][0][0]["measured"] = "widths"
    [stated] = found(scene)
    assert (stated.code, stated.level) == ("letters-touch-unmeasured", findings.FACT)
    assert "measured nothing at lines 1 and 2" in stated.message


#: The planted case of each clause of each reach, by the check's id, the part of its reach
#: and the clause's place in it.
PLANTED: dict[tuple[str, str, int], Callable[[], None]] = {
    ("edges-nearly-in-line", "measures", 0): _near_pair,
    ("edges-nearly-in-line", "measures", 1): _near_insets,
    ("edges-nearly-in-line", "measures", 2): _near_spacings,
    ("edges-nearly-in-line", "measures", 3): _near_between_groups,
    ("edges-nearly-in-line", "measures", 4): _near_lists,
    ("edges-nearly-in-line", "leaves-out", 0): lambda: _lines_and_ties(near),
    ("edges-nearly-in-line", "leaves-out", 1): lambda: _of_no_area(near),
    ("edges-nearly-in-line", "leaves-out", 2): lambda: _pages_beside(
        lambda given: boxes.near_alignment(given, STEP)
    ),
    ("edges-nearly-in-line", "leaves-out", 3): _between_pages,
    ("edges-nearly-in-line", "leaves-out", 4): _group_with_no_sibling,
    ("edges-nearly-in-line", "leaves-out", 5): _tie_s_part,
    ("edges-nearly-in-line", "leaves-out", 6): _text_s_lines,
    ("edges-nearly-in-line", "leaves-out", 7): _text_s_insets,
    ("edges-nearly-in-line", "leaves-out", 8): _text_s_gaps,
    ("edges-nearly-in-line", "leaves-out", 9): _other_groups_spacings,
    ("edges-nearly-in-line", "leaves-out", 10): _gap_between_groups,
    ("edges-nearly-in-line", "leaves-out", 11): _list_s_own_spacing,
    ("edges-nearly-in-line", "leaves-out", 12): _near_other_lines,
    ("edges-nearly-in-line", "leaves-out", 13): _near_held_edges,
    ("edges-nearly-in-line", "leaves-out", 14): _near_inset_on_an_edge,
    ("edges-nearly-in-line", "leaves-out", 15): _near_gap_not_beside,
    ("edges-nearly-in-line", "states", 0): _near_states_no_step,
    ("boxes-that-overlap", "measures", 0): _overlap_pair,
    ("boxes-that-overlap", "leaves-out", 0): lambda: _apart_in_groups(overlap, -20),
    ("boxes-that-overlap", "leaves-out", 1): lambda: _lines_and_ties(overlap),
    ("boxes-that-overlap", "leaves-out", 2): lambda: _of_no_area(overlap),
    ("boxes-that-overlap", "leaves-out", 3): lambda: _pages_beside(boxes.overlaps),
    ("boxes-that-overlap", "leaves-out", 4): _overlap_held,
    ("content-a-size-hides", "measures", 0): _hidden_content,
    ("content-a-size-hides", "leaves-out", 0): _hidden_nowhere,
    ("content-a-size-hides", "leaves-out", 1): _hidden_not_content,
    ("contrast-as-drawn", "measures", 0): _contrast_runs,
    ("contrast-as-drawn", "measures", 1): _contrast_signs,
    ("contrast-as-drawn", "measures", 2): _contrast_fills,
    ("contrast-as-drawn", "leaves-out", 0): _contrast_over_a_picture,
    ("contrast-as-drawn", "leaves-out", 1): _contrast_over_nothing,
    ("contrast-as-drawn", "leaves-out", 2): _contrast_unknown_role,
    ("contrast-as-drawn", "leaves-out", 3): _contrast_no_ink,
    ("contrast-as-drawn", "leaves-out", 4): _contrast_no_opaque_fill,
    ("contrast-as-drawn", "leaves-out", 5): _contrast_off_the_middle,
    ("contrast-as-drawn", "leaves-out", 6): _contrast_draws_nothing,
    ("letters-across-lines", "measures", 0): _letters_across_lines,
    ("letters-across-lines", "leaves-out", 0): _letters_of_two_texts,
    ("letters-across-lines", "leaves-out", 1): _letters_drawn_to_join,
    ("letters-across-lines", "leaves-out", 2): _letters_a_renderer_wraps,
    ("letters-across-lines", "states", 0): _letters_with_no_outline,
    ("text-size-by-medium", "measures", 0): _sized_runs,
    ("text-size-by-medium", "measures", 1): _sized_pages,
    ("text-size-by-medium", "leaves-out", 0): _sized_pictures,
    ("text-size-by-medium", "leaves-out", 1): _sized_faces,
    ("text-size-by-medium", "leaves-out", 2): _sized_viewers,
    ("text-size-by-medium", "leaves-out", 3): _sized_no_lines,
    ("text-size-by-medium", "leaves-out", 4): _sized_off_pages,
    ("text-size-by-medium", "states", 0): _sized_no_medium,
    ("text-size-by-medium", "states", 1): _sized_undeclared,
    ("text-size-by-medium", "states", 2): _sized_unshown,
    ("text-size-by-medium", "states", 3): _sized_no_share,
}


def test_each_clause_of_each_reach_has_a_planted_case() -> None:
    clauses = set()
    for id_, check in REACHING.items():
        assert check.reach is not None
        for part, said in (
            ("measures", check.reach.measures),
            ("leaves-out", check.reach.leaves_out),
            ("states", check.reach.states),
        ):
            clauses.update((id_, part, index) for index in range(len(said)))
    assert set(PLANTED) == clauses


@pytest.mark.parametrize("clause", sorted(PLANTED), ids=lambda clause: "-".join(map(str, clause)))
def test_the_check_keeps_each_clause_of_its_reach(clause: tuple[str, str, int]) -> None:
    PLANTED[clause]()


# --- scene by scene -----------------------------------------------------------------------------


def test_each_finding_is_given_with_its_scene_before_the_render_s_merges(tmp_path: Path) -> None:
    drawn = project_of(flipping(tmp_path))
    results = drawn.scenes(facts=drawn.piece.stand_ins)
    found = checks.found_in(drawn, results)
    hidden = [each for each in found if each.check is checks.CONTENT_HIDDEN]
    assert [(each.language, each.size, each.page) for each in hidden] == [
        ("en", "device.phone", None)
    ]
    assert checks.merged(results, found) == checks.scene_findings(drawn, results)
    assert {each.check for each in found} <= set(checks.SCENE_CHECKS)


def _record(root: Path, name: str) -> list[tuple[str, str, str, str]]:
    piece = pl.read_piece(root, "visual", name)
    found = checks.computed(pl.Project(piece, piece.lock, pl.Held(root, "visual")))
    return [(f.code, f.file, f.where, f.message) for f in found]


EXPERIMENTAL = "which is experimental: its library may still change it in any release"

#: The statement on a piece that names no medium, once for every language and key.
NO_MEDIUM = (
    "the piece names no medium it is shown in under `media`, so no text's size was measured, "
    "in any language or at any size"
)


def test_the_findings_record_keeps_the_render_s_merges(tmp_path: Path) -> None:
    """The render's merges of the findings given scene by scene, as the findings record kept
    them before they were given so: a finding at every key once, as it reads, any other once
    for each key that finds it, opening with that key, and one read alike on several pages
    once, naming them (DEC-062 point 1)."""
    assert _record(flipping(tmp_path / "hidden"), "flow") == [
        (
            "size-hidden",
            "content.en.yaml",
            "body.note",
            "`device.phone`: `body.note` is drawn at `default`, and not at this size",
        ),
        (
            "component-experimental",
            "piece.yaml",
            "figure",
            f"the piece uses `foundations/figure`, {EXPERIMENTAL}",
        ),
        (
            "component-experimental",
            "piece.yaml",
            "figure/body",
            f"the piece uses `piece/flip`, {EXPERIMENTAL}",
        ),
        (
            "component-experimental",
            "piece.yaml",
            "figure/body/across[plan]",
            f"`default`: the piece uses `tests/card`, {EXPERIMENTAL}",
        ),
        (
            "component-experimental",
            "piece.yaml",
            "figure/body/down[plan]",
            f"`device.phone`: the piece uses `tests/card`, {EXPERIMENTAL}",
        ),
        ("text-size-unmeasured", "piece.yaml", "media", NO_MEDIUM),
    ]
    sites = site.site_location(project(tmp_path / "site"))
    portal = sites / "visual/pieces/portal/content.en.yaml"
    content = YAML(typ="safe").load(portal.read_text(encoding="utf-8"))
    content["header"]["head"] = "Pneumonoultramicroscopicsilicovolcanoconiosis"
    write(portal, yaml_text(content))
    [overflow, *_] = _record(sites, "portal")
    assert overflow == (
        "text-overflow",
        "content.en.yaml",
        "site/pages[home]/header/head",
        "`device.phone`: site/pages[home]/header/head: a word of content:header.head is wider "
        "than the text's width 358.0 px: 504.22 px; read the same on the pages "
        "`site/pages[home]`, `site/pages[guide]`",
    )


def test_a_key_with_no_step_of_space_is_stated_and_the_findings_record_keeps_it(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path, picture=False, modes={"device": ["desktop", "phone"]})
    add_device(root, {**NARROW, "space": {"$type": "dimension", "1": {"$value": px(1)}}})
    drawn = project_of(root)
    found = checks.computed(drawn)
    stated = [f for f in found if f.code == boxes.NEAR_ALIGNMENT_UNMEASURED]
    assert [(f.level, f.file, f.where) for f in stated] == [(findings.FACT, "piece.yaml", "brand")]
    assert stated[0].message.startswith("`device.phone`: the brand's smallest step of space")
    record = rendering.record_text(rendering.record(drawn, found, None)).decode("utf-8")
    assert boxes.NEAR_ALIGNMENT_UNMEASURED in record
