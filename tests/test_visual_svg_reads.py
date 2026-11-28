"""`scripts/visual_svg_reads.py`: the maintainer's measure of the SVG renderer's reads of cover
and cut (visual-communication DEC-045). It draws the plants the look's tests draw, judges each
rule DEC-045 weighs on what they lose, what the reads as built name, and each setting of the
measure of whole islands, sets a mark past the page's edge, steps a box's edge across a dot,
hides an ogonek, lays a mark by geometry, and reads a look's profile for what each read costs.
Each test here runs the reads in this process; none starts a look."""

from __future__ import annotations

import cProfile
import pstats
import tempfile
import time
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from scripts import visual_svg_reads as reads

from tests import test_visual_communication_look as look_tests

viewing_tool = look_tests.viewing_tool
islands = look_tests.islands


def loss(pixels: int, em: float = 10.0, *, at_an_edge: bool = False) -> reads.Loss:
    return reads.Loss(em, pixels, 1, at_an_edge)


def test_the_rule_as_built_is_the_module_s_own_threshold() -> None:
    [built, *_] = reads.rules(viewing_tool._least)
    assert built.fewest is viewing_tool._least
    assert built.names(loss(1, 10.2))
    assert not built.names(loss(15, 40.0))
    assert built.names(loss(16, 40.0))


def test_the_alternatives_are_judged_as_the_record_states_them() -> None:
    weighed = {rule.name: rule for rule in reads.rules(viewing_tool._least)}
    assert not weighed["0.0125 in whole pixels"].names(loss(19, 40.0))
    assert weighed["0.0125 in whole pixels"].names(loss(20, 40.0))
    assert not weighed["a floor of two"].names(loss(1, 10.2))
    assert not weighed["0.0125 as an area"].names(loss(2, 14.3))
    assert weighed["0.0095 as an area"].names(loss(10, 30.0))
    assert weighed["0.0095 as an area"].names(loss(1, 10.25))
    assert not weighed["0.0095 as an area"].names(loss(1, 10.3))
    assert weighed["two pixels or more"].names(loss(14, 40.0))
    geometric = weighed["the geometric test: two pixels or more, but not in an edge"]
    assert not geometric.names(loss(2, at_an_edge=True))
    assert geometric.names(loss(2))


def test_a_loss_in_one_outermost_row_or_column_of_the_ink_lies_in_an_edge() -> None:
    ink = [(row, column) for row in range(5) for column in range(4)]
    strong = SimpleNamespace(em=10.0, on_page=ink, found=len(ink))
    assert reads.loss_of(strong, [(0, 1), (0, 2)]).at_an_edge
    assert reads.loss_of(strong, [(4, 0)]).at_an_edge
    assert reads.loss_of(strong, [(1, 3), (2, 3)]).at_an_edge
    assert not reads.loss_of(strong, [(0, 1), (1, 1)]).at_an_edge
    assert not reads.loss_of(strong, [(2, 1)]).at_an_edge
    assert not reads.loss_of(strong, []).at_an_edge


def test_the_first_levels_are_the_tool_s_and_the_last_any_ink() -> None:
    assert reads.STRONG_INK == viewing_tool.STRONG
    assert reads.LEVELS[: len(islands.LEVELS)] == islands.LEVELS
    assert reads.ANY_INK == 254
    assert list(reads.LEVELS) == sorted(reads.LEVELS)


def test_the_setting_as_built_names_what_the_tool_s_measure_names() -> None:
    """The tool finds islands at its levels, joined by sides and corners, and gone when all of
    it is hidden: the probe's setting of the same names the same."""
    built = reads.BUILT
    assert built == reads.Measure(islands.LEVELS, len(islands.NEIGHBOURS), "all of it")
    assert built in reads.MEASURES
    ink = {**STROKE, **SPECK, **FAINT}
    for hidden in ([(4, 1)], [(4, 0)], [(4, 0), (4, 1)], list(STROKE), list(ink)):
        named = built in reads.gone_islands(ink, hidden)
        assert islands.takes_an_island(ink, hidden) == named, hidden
        assert reads.takes(ink, hidden, reads.TAKEN[0]) == named, hidden


#: A letter's stroke, and a speck beside it: a pixel joined to the stroke by a corner alone,
#: and a faint pixel between them that joins it by a side at the weakest level.
STROKE = {(row, 0): 0 for row in range(4)}
SPECK = {(4, 1): 100}
FAINT = {(4, 0): 230}


def test_pixels_join_into_an_island_by_a_side_or_by_a_corner_too_at_their_level() -> None:
    ink = {**STROKE, **SPECK}
    by_sides = sorted(sorted(island) for island in reads.islands_of(ink, 127, 4, ink))
    assert by_sides == [sorted(STROKE), sorted(SPECK)]
    assert [sorted(island) for island in reads.islands_of(ink, 127, 8, ink)] == [sorted(ink)]
    faint = {**ink, **FAINT}
    assert len(reads.islands_of(faint, 127, 4, faint)) == 2
    assert len(reads.islands_of(faint, 254, 4, faint)) == 1
    assert reads.islands_of({(0, 0): 254}, 223, 8, [(0, 0)]) == []


def test_only_the_islands_that_hold_a_pixel_asked_for_are_walked() -> None:
    ink = {**STROKE, **SPECK}
    assert reads.islands_of(ink, 127, 4, [(4, 1)]) == [[(4, 1)]]
    assert reads.islands_of(ink, 127, 4, [(9, 9)]) == []


def test_an_island_is_gone_as_the_setting_says() -> None:
    island = [(0, 0), (0, 1), (0, 2)]
    ink = {(0, 0): 0, (0, 1): 0, (0, 2): 230}
    strong_only = {(0, 0), (0, 1)}
    assert not reads.is_gone(island, strong_only, ink, "all of it")
    assert reads.is_gone(island, strong_only, ink, "its strong ink")
    assert reads.is_gone(island, strong_only, ink, "most of it")
    assert not reads.is_gone(island, {(0, 0)}, ink, "most of it")
    faint = {(0, 0): 230, (0, 1): 230}
    assert not reads.is_gone([(0, 0), (0, 1)], {(0, 0)}, faint, "its strong ink")
    assert reads.is_gone([(0, 0), (0, 1)], {(0, 0), (0, 1)}, faint, "its strong ink")


def test_a_cover_is_named_by_the_settings_under_which_it_takes_a_whole_island() -> None:
    ink = {**STROKE, **SPECK}
    named = reads.gone_islands(ink, [(4, 1)])
    assert reads.Measure((127,), 4, "all of it") in named
    assert reads.Measure((127,), 8, "all of it") not in named
    assert reads.gone_islands(ink, [(0, 0), (1, 0)]) == frozenset()
    assert reads.gone_islands(ink, []) == frozenset()


def test_a_setting_of_several_levels_names_a_cover_that_takes_an_island_at_any_of_them() -> None:
    """The speck is an island of its own at strong ink alone; at any ink it joins the stroke by
    a side."""
    ink = {**STROKE, **SPECK, **FAINT}
    settings = [reads.Measure(levels, 4, "all of it") for levels in ((127,), (254,), (127, 254))]
    assert reads.gone_islands(ink, [(4, 1)], settings) == {settings[0], settings[2]}
    stands = {(127, 4): "no ink", (191, 4): "merged", (254, 4): "own"}
    assert reads._best(stands, reads.Measure((127, 191), 4, "all of it")) == "merged"
    assert reads._best(stands, reads.Measure((127, 191, 254), 4, "all of it")) == "own"
    assert reads._best({}, reads.Measure((127,), 4, "all of it")) == reads.NOT_FOUND


def test_a_dot_is_the_part_of_its_run_s_ink_set_apart_at_the_weakest_level_that_parts_it() -> None:
    dot = {(0, 2): 100, (1, 2): 120}
    touching = {(2, 2): 230}
    letter = {(3, column): 0 for column in range(4)}
    over = reads.Dot("dot", ("ż",), 0, "rows", 2, 0)
    assert reads.dot_pixels(over, {**dot, **letter}) == (list(dot), list(letter), 254)
    mine, rest, level = reads.dot_pixels(over, {**dot, **touching, **letter})
    assert (mine, rest, level) == (list(dot), list(letter), 223)
    assert reads.dot_pixels(over, letter) == ([], [], 0)
    beside = reads.Dot("point", ("3.5",), 0, "columns", 3, 1)
    figures = {(0, 0): 0, (0, 2): 0, (0, 4): 0}
    assert reads.dot_pixels(beside, figures)[0] == [(0, 2)]
    whole = reads.Dot("point", ("3", ".", "5"), 1)
    assert reads.dot_pixels(whole, dot) == (list(dot), [], 254)


def test_a_dot_is_an_island_of_its_own_merged_split_or_without_ink_at_each_level() -> None:
    dot = {(0, 2): 100, (1, 2): 200}
    touching = {(2, 2): 230}
    letter = {(3, column): 0 for column in range(4)}
    ink = {**dot, **touching, **letter}
    stands = reads.standing(list(dot), list(letter), ink)
    assert stands[127, 8] == "own"
    assert stands[223, 8] == "own"
    assert stands[254, 8] == "merged"
    corner = {(0, 0): 100, (1, 1): 100}
    split = reads.standing(list(corner), [], corner)
    assert (split[127, 4], split[127, 8]) == ("split", "own")
    assert reads.standing([(0, 0)], [], {(0, 0): 200})[127, 4] == "no ink"


def test_the_box_over_a_dot_reaches_a_pixel_past_it_on_each_side() -> None:
    """A swath of 40 rows over 20 px from a top of 10 px, on a page of 100 px drawn in 50
    columns: a row is half a px, and a column two."""
    strong = SimpleNamespace(columns=50, top=10.0, reach=10.0, rows=40)
    box = look_tests.box_over([(4, 7), (5, 8)], strong, 100.0)(0.0, 0.0)
    assert box == {"x": 12.0, "y": 11.5, "width": 8.0, "height": 2.0}


def strong_of_each_span(words: tuple[str, ...], em: float) -> list[Any]:
    """The strong ink the reads hand the look of each span of `words`, set `em` image pixels
    high at a scale of 1."""
    found: list[Any] = []
    page = viewing_tool._Page
    held = page._partly

    def partly(_page: Any, _span: Any, strong: Any, _element: str) -> Any:
        found.append(strong)
        return iter(())

    page._partly = partly
    try:
        with tempfile.TemporaryDirectory() as folder:
            look_tests.set_at(Path(folder), words, em, 1.0)
    finally:
        page._partly = held
    return found


def test_with_any_ink_taken_the_reads_hand_the_look_the_strong_ink_they_find_unpatched() -> None:
    words = ("Typo", "graphy", "ż")
    unpatched = strong_of_each_span(words, 11.0)
    with reads.any_ink(viewing_tool) as ink_of:
        patched = strong_of_each_span(words, 11.0)
        inks = [ink_of(each) for each in patched[-1:]]
    assert [(each.found, each.past, each.on_page) for each in patched] == [
        (each.found, each.past, each.on_page) for each in unpatched
    ]
    [ink] = inks
    assert set(patched[-1].on_page) < set(ink)
    assert all(
        dark <= reads.STRONG_INK for pixel, dark in ink.items() if pixel in patched[-1].on_page
    )


def test_the_probe_leaves_the_reads_and_the_face_as_they_were() -> None:
    page = viewing_tool._Page
    held = page._partly, page._strong, viewing_tool.STRONG, viewing_tool.FAINT, look_tests.FONT
    with reads.hidden_pixels(look_tests, Path("elsewhere.otf")):
        assert Path("elsewhere.otf") == look_tests.FONT
        assert page._partly is not held[0]
        assert viewing_tool.FAINT == reads.ANY_INK
    with reads.strong_found(viewing_tool), reads.set_in(look_tests, Path("elsewhere.otf")):
        assert page._strong is not held[1]
        assert Path("elsewhere.otf") == look_tests.FONT
    after = page._partly, page._strong, viewing_tool.STRONG, viewing_tool.FAINT, look_tests.FONT
    assert after == held


def point_hidden(em: float) -> Mapping[str, Any]:
    """The box over all the ink of the decimal point of "3.5", each a run of its own, set `em`
    image pixels high at a scale of 1, as the probe lays it."""
    with reads.hidden_pixels(look_tests, None) as kept, tempfile.TemporaryDirectory() as folder:
        look_tests.set_at(Path(folder), ("3", ".", "5"), em, 1.0)
        [point] = [each for each in kept if each.text == "."]
    return look_tests.box_over(list(point.ink), point.strong, point.width)(0.0, 0.0)


def test_the_probe_s_verdict_as_built_is_what_the_tool_names(tmp_path: Path) -> None:
    """At an em of 22.5 the point holds 4 strong pixels, fewer than the threshold's 5, so the
    threshold leaves it, and the measure of islands names it when a box hides all of it. The
    probe reads the same draw as the tool does, and says the tool names it."""
    box = point_hidden(22.5)
    runs = ("3", ".", "5")

    def over(_base: float, _size: float) -> dict[str, Any]:
        return dict(box)

    assert look_tests.set_at(tmp_path, runs, 22.5, 1.0, over) == [(viewing_tool.COVERED, 1.0)]
    with reads.hidden_pixels(look_tests, None) as kept:
        look_tests.set_at(tmp_path, runs, 22.5, 1.0, over)
    [point] = [each for each in kept if each.text == "."]
    loss = reads.measured(point, viewing_tool)
    assert loss.built
    assert not reads.rules(viewing_tool._least)[0].names(loss)
    assert not reads.measured(replace(point, hidden=[]), viewing_tool).built


def test_the_cover_probe_prints_each_em_and_scale_and_judges_each_rule_and_setting(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert reads.main(["cover", "--em", "40", "--scale", "1"]) == 0
    printed = capsys.readouterr().out
    [drawn] = [each for each in printed.splitlines() if each.startswith("em ")]
    assert "threshold  16" in drawn
    assert "least graze" in drawn
    assert "dots hidden: full stop 16 of 16, ink whole of" in drawn
    for dot in reads.DOTS:
        assert f"{dot.name}: hidden whole at 1 of 1 draws, 0 with no strong ink" in printed
    assert "the threshold as built\n  háček draws unnamed: 0 of 1\n" in printed
    assert "the least graze at 40: spared, the row above named" in printed
    assert "as built: the threshold, or an island taken at 127, 159, 191," in printed
    dot = "  dot of ż: named 1 of 1, taken by the measure 1, by the measure alone 1, unnamed 0;"
    assert dot in printed
    assert "; a pixel from unnamed by 0.0125 in whole pixels " in printed
    assert "0.007 in whole pixels\n" in printed
    assert "  graze steps the measure alone names: 0 of 13\n" in printed
    setting = "islands at 191, joined by sides and corners, gone when all of it is hidden\n"
    assert setting + "  háček: both 1," in printed
    assert "  full stop: both 1, the threshold alone 0, the islands alone 0, neither 0\n" in printed
    assert "dot of ż, its run's ink in its parts: from 254: 1 (ems 40 to 40)" in printed


def test_the_cut_probe_sets_each_mark_past_its_edge_and_reads_it_as_built(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert reads.main(["cut", "--em", "40", "--scale", "1"]) == 0
    printed = capsys.readouterr().out
    [drawn] = [each for each in printed.splitlines() if each.startswith("em ")]
    assert "dot of ż: named cut, an island, strong past " in drawn
    assert "full stop: named off the page," in drawn
    for edge in reads.EDGES:
        assert f"{edge.dot.name}, past the {edge.edge} edge: placed 1 of 1, named 1 " in printed
    assert ", the rest named 0\n" in printed


def test_an_island_is_taken_as_each_way_of_taking_one_says() -> None:
    """Of a strong pixel and two at 150, joined by sides: at strong ink the strong pixel is an
    island of its own, and at 159 and 191 the three are one."""
    ink = {(0, 0): 0, (0, 1): 150, (0, 2): 150}
    all_of_it, but_one, mostly, *_ = reads.TAKEN
    first = (all_of_it, but_one, mostly)
    assert all(reads.takes(ink, [(0, 0)], taken) for taken in first)
    light = [(0, 1), (0, 2)]
    assert not reads.takes(ink, light, all_of_it)
    assert reads.takes(ink, light, but_one)
    assert reads.takes(ink, light, mostly)
    assert not any(reads.takes(ink, [(0, 2)], taken) for taken in first)


def test_an_island_is_unseen_where_none_of_it_still_shows_at_its_level() -> None:
    ink = {(0, 0): 0, (0, 1): 0, (5, 5): 0}
    shows = {(0, 0): 100, (0, 1): 0, (5, 5): 255}
    assert reads.unseen(ink, shows)
    assert not reads.unseen(ink, {**shows, (0, 1): 200})
    assert reads.unseen({(0, 0): 180}, {(0, 0): 50})
    assert not reads.unseen({(0, 0): 180}, {(0, 0): 70})
    assert reads.unseen(ink, shows, [(0, 1)])
    assert not reads.unseen(ink, shows, [(5, 5)])
    assert not reads.unseen(ink, {**shows, (0, 1): 100}, [(5, 5)])


def test_the_ways_that_read_what_still_shows_take_an_island_as_each_says() -> None:
    """A dot of three strong pixels beside a stroke of three. A box's edge across the dot hides
    one pixel wholly and leaves the others showing under half their ink; a translucent box over
    the dot hides none wholly and leaves all faded; and the same box with a part that hides one
    pixel of the stroke wholly. The tool's measure takes the island as the sixth way does, and
    the last case is the fifth's alone."""
    dot = {(0, 0): 0, (0, 1): 0, (0, 2): 0}
    stroke = {(3, 3): 0, (4, 3): 0, (5, 3): 0}
    ink = {**dot, **stroke}
    shown = {pixel: 255 for pixel in ink}
    edge = {**shown, (0, 0): 0, (0, 1): 100, (0, 2): 100}
    faded = {**shown, (0, 0): 100, (0, 1): 100, (0, 2): 100}
    (_, _, _, unseen, any_hit, island_hit, either) = reads.TAKEN
    across = reads.cause_of(ink, [(0, 0)], 20.0, edge)
    assert across.taking == {unseen, any_hit, island_hit, either}
    under = reads.cause_of(ink, [], 20.0, faded)
    assert under.taking == {unseen}
    elsewhere = reads.cause_of(ink, [(3, 3)], 20.0, {**faded, (3, 3): 0})
    assert elsewhere.taking == {unseen, any_hit}
    assert island_hit == reads.AS_BUILT
    for hidden, shows in (([(0, 0)], edge), ([], faded), ([(3, 3)], {**faded, (3, 3): 0})):
        taken = reads.AS_BUILT in reads.cause_of(ink, hidden, 20.0, shows).taking
        assert islands.takes_an_island(ink, hidden, shows) == taken


def test_a_cause_is_named_by_the_threshold_at_its_share_or_by_the_island_it_takes() -> None:
    assert reads.Cause(40.0, 16).named((0.01, reads.TAKEN[0]))
    assert not reads.Cause(40.0, 16).named((0.0125, reads.TAKEN[0]))
    assert reads.Cause(10.2, 1).by_threshold(0.0125)
    taking = reads.Cause(40.0, 16, frozenset({reads.TAKEN[1]}))
    assert taking.named((0.0125, reads.TAKEN[1]))
    assert taking.by_island_alone((0.0125, reads.TAKEN[1]))
    assert not taking.by_island_alone((0.01, reads.TAKEN[1]))
    assert not taking.by_island_alone((0.0125, reads.TAKEN[0]))
    ink = {(0, 0): 0, (0, 1): 150, (0, 2): 150}
    assert reads.cause_of(ink, [(0, 0)], 20.0).taking == set(reads.TAKEN)
    light = reads.cause_of(ink, [(0, 1), (0, 2)], 20.0)
    assert light == reads.Cause(20.0, 0, frozenset({*reads.TAKEN[1:3], reads.TAKEN[6]}))
    gone = reads.cause_of(ink, [], 20.0, {(0, 0): 0, (0, 1): 0, (0, 2): 0})
    assert gone == reads.Cause(20.0, 0, frozenset({reads.TAKEN[3]}))


def test_the_partial_probe_steps_a_box_s_edge_across_each_dot_and_judges_each_rule(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """At an em of 20 the full stop holds as many strong pixels as the threshold at 0.01, so an
    edge that leaves a strong pixel of it uncovered leaves it unnamed under "all of it" though
    none of it still shows strong; the ways that read what still shows name it at every such
    step, the tool's among them."""
    assert reads.main(["partial", "--em", "20", "--scale", "1"]) == 0
    printed = capsys.readouterr().out
    [drawn] = [each for each in printed.splitlines() if each.startswith("em ")]
    unnamed = "unnamed 14,14,8,0,0,0,0,14,14,8,0,0,0,0;"
    assert f"full stop: level 127, gone 46 of 116, {unnamed}" in drawn
    assert drawn.endswith("; grazes by the island alone 0,0,0,0,0,0,0,0,0,0,0,0,0,0")
    assert "steps at which the tool's measure judged otherwise than the probe's: 0\n" in printed
    unnamed = "    0.01 and all of it: gone and unnamed at 14 steps, of 1 draws (ems 20 to 20),"
    assert unnamed in printed
    built = f"    0.01 and {reads.AS_BUILT}: gone and unnamed at 0 steps,"
    assert built in printed
    assert "  0.01 and all of it: steps the island alone names 0 of 13;" in printed


def test_the_ogonek_probe_hides_each_ogonek_from_the_baseline_down(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """In Source Code Pro at an em of 10 the ogonek of ą holds no strong pixel below the
    baseline and is no island of its own, so no rule names it hidden."""
    argv = ["ogonek", "--em", "10", "--scale", "1", "--face", str(look_tests.CODE)]
    assert reads.main(argv) == 0
    printed = capsys.readouterr().out
    [drawn] = [each for each in printed.splitlines() if each.startswith("em ")]
    assert "ą: strong below the baseline 0, hidden 0, above it 0, islands none;" in drawn
    assert "ą: 1 draws, strong below the baseline 0 to 0, hidden above it at most 0\n" in printed
    for rule in reads.WEIGHED:
        assert f"  {reads._rule(rule)}: unnamed 1 (ems 10 to 10)\n" in printed


def test_the_geometry_probe_lays_a_mark_its_pixels_cannot_place(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """At an em of 10 and a scale of 1.225 the full stop of "end." holds no strong ink and
    touches its word at every level, and drawn finer it stands apart."""
    argv = ["geometry", "--em", "10", "--scale", "1.225", "--mark", "full stop in its word"]
    assert reads.main(argv) == 0
    printed = capsys.readouterr().out
    [drawn] = [each for each in printed.splitlines() if each.startswith("em ")]
    assert "full stop in its word: not placed by its pixels; under a box strong hidden 0," in drawn
    assert drawn.endswith("named cut, an island")
    assert "full stop in its word: 1 draws, not placed by its pixels 1 (ems 10 to 10)\n" in printed
    assert "  0.01 and all of it, cover: named 1, by the threshold 0\n" in printed
    assert "  0.01 and all of it, cut: named 1, by the threshold 0\n" in printed


def test_the_cost_names_each_read_from_a_profile_of_the_reads(tmp_path: Path) -> None:
    """The functions `cost` reads a profile for are the module's: a page with a covered text,
    drawn through the reads under the profiler, names each, the measure of islands among
    them."""
    said = look_tests.text_element("figure/said", look_tests.run("Under a box", fill="ink"), y=30)
    over = look_tests.element("box", "figure/over", x=0, y=0, width=60, height=100, fill="surface")
    profile = cProfile.Profile(time.process_time, builtins=False)
    profile.runcall(look_tests.tool, tmp_path, said, over)
    printed = "\n".join(reads.cost_lines(pstats.Stats(profile), 1.0))
    for what in (
        "the cut read, a span drawn alone on its swath: ",
        "the cover read, the page drawn twice on a span's ink: ",
        "  of which, one draw of the page: ",
        "the check for ink: ",
        "a page drawn whole: ",
        "the cut read's walk over its pixels: ",
        "the measure of islands, of the cut and the cover: ",
    ):
        assert what in printed
