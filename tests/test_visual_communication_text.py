"""Text measured from committed font files, and broken into lines by the engine
(visual-communication DEC-005 point 4, DEC-004 point 9; #2428).

- each run shaped with HarfBuzz from the file a family names, the next family measuring
  what the first lacks; a missing file or an unmeasured character refused, naming it;
- lines broken at Unicode's break opportunities and the language's own rules (Czech: a
  one-letter word and a short preposition never end a line; #3084), against the planned
  width less 2 % of the em, and placed in the planned width;
- never shrunk: a long word breaks after a `/`, else the text overflows;
- runs (DEC-012 point 4): each part of a line measured in its own run's role, lines
  broken across runs by Unicode's rules and the language's, against a margin at the
  greatest font size among the runs' roles; one line height for the text, the greatest,
  and one baseline on each line; a text of one run broken as format 1 breaks it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from fontTools import subset
from fontTools.ttLib import TTFont

from tests.visual_engine import (
    FAMILY,
    FIXTURES,
    FONT,
    ROLES,
    RUN_FONTS,
    RUN_ROLES,
    SEMIBOLD,
    SEMIBOLD_FONT,
    env,
    text,
)

TYPE = ROLES["type.body"]


def faces(**files: Path) -> Any:
    known = {FAMILY: FONT, **files}
    return text.Faces(lambda family: known.get(family, Path("/nowhere") / family))


def style(**changes: Any) -> Any:
    return text.Style.of_role("type.body", {**TYPE, **changes}, faces())


BODY = style()
MARGIN = text.BREAK_MARGIN * 16


def lines(words: str, width: float | None, language: str = "en", face: Any = BODY) -> list[str]:
    return list(text.break_lines(words, width, face, language).lines)


# --- measuring ----------------------------------------------------------------------------


def test_a_text_is_measured_from_its_font_file_and_scales_with_its_size() -> None:
    small, large = (
        BODY.width("Measure me"),
        style(fontSize={"value": 32, "unit": "px"}).width("Measure me"),
    )

    assert 60 < small < 90
    assert large == pytest.approx(2 * small)
    assert BODY.width("Measure me   ") == small


def test_a_face_records_its_file_and_its_hash() -> None:
    face = BODY.faces[0]

    assert (face.family, face.path) == (FAMILY, FONT)
    assert face.sha256 == hashlib.sha256(FONT.read_bytes()).hexdigest()


def test_a_style_takes_its_size_line_height_and_baseline_from_the_role() -> None:
    assert (BODY.size, BODY.line_height, BODY.weight, BODY.families) == (16.0, 22.4, 400, (FAMILY,))
    assert 0 < BODY.baseline < BODY.line_height
    assert style(fontFamily=FAMILY).families == (FAMILY,)


@pytest.mark.parametrize(
    ("value", "why"),
    [
        ("16px", "is not a typography"),
        ({**TYPE, "fontFamily": []}, "names no font family"),
        ({**TYPE, "fontSize": {"value": 1, "unit": "rem"}}, "gives no font size in px"),
        ({**TYPE, "lineHeight": "1.4"}, "gives no line height as a number"),
        ({**TYPE, "lineHeight": True}, "gives no line height as a number"),
        (
            {**TYPE, "letterSpacing": {"value": 0.5, "unit": "px"}},
            "spaces its letters, which format 1 does not measure",
        ),
    ],
)
def test_a_role_the_engine_cannot_measure_is_refused(value: object, why: str) -> None:
    with pytest.raises(ValueError, match=why):
        text.Style.of_role("type.body", value, faces())


def test_a_family_with_no_committed_file_is_refused_naming_it() -> None:
    with pytest.raises(env.MissingFont, match="'Absent Sans' has no file at /nowhere/Absent Sans"):
        style(fontFamily=["Absent Sans"])


def test_a_file_that_is_no_font_is_refused_naming_it(tmp_path: Path) -> None:
    broken = tmp_path / "Broken.otf"
    broken.write_bytes(b"not a font")

    with pytest.raises(env.UnreadableFont) as raised:
        text.Faces(lambda _family: broken).face(FAMILY)

    assert str(raised.value).startswith(f"the font file {broken} cannot be read: ")
    assert isinstance(raised.value, env.MissingFont)


def test_a_font_the_reader_stops_on_with_an_error_of_another_kind_is_refused_too(
    tmp_path: Path,
) -> None:
    lacking = tmp_path / "Lacking.otf"
    font = TTFont(str(FONT))
    del font["hmtx"], font["hhea"]
    font.save(str(lacking))

    with pytest.raises(env.UnreadableFont, match="hhea"):
        text.Faces(lambda _family: lacking).face(FAMILY)


def test_an_error_with_no_words_of_its_own_is_said_by_its_kind() -> None:
    said = env.UnreadableFont(Path("Broken.otf"), AssertionError())

    assert str(said) == "the font file Broken.otf cannot be read: AssertionError"


def test_a_character_no_family_measures_is_refused_naming_it_and_where() -> None:
    BODY.check("Přes čtyři řeky\n", "the caption")

    with pytest.raises(text.MissingGlyph) as raised:
        BODY.check("A 中 B", "figure/caption")

    assert str(raised.value) == (
        f"no font family of @type.body ({FAMILY}) measures '中' (U+4E2D) in figure/caption"
    )
    assert isinstance(raised.value, env.MissingFont)


def test_the_next_family_measures_what_the_first_lacks(tmp_path: Path) -> None:
    letters = tmp_path / "Letters.otf"
    options = subset.Options()
    font = subset.load_font(str(FONT), options)
    subsetter = subset.Subsetter(options)
    subsetter.populate(text="ab ")
    subsetter.subset(font)
    subset.save_font(font, str(letters), options)
    both = text.Style.of_role(
        "type.body", {**TYPE, "fontFamily": ["Letters", FAMILY]}, faces(Letters=letters)
    )

    both.check("ab z", "here")
    assert [face.family for face in both.faces_used("ab")] == ["Letters"]
    assert [face.family for face in both.faces_used("ab z")] == ["Letters", FAMILY]
    assert both.width("ab z") == pytest.approx(BODY.width("ab z"), abs=0.5)
    with pytest.raises(text.MissingGlyph, match="U\\+4E2D"):
        both.check("中", "here")


# --- breaking -----------------------------------------------------------------------------


def test_with_no_width_each_paragraph_is_one_line() -> None:
    broken = text.break_lines("One line here\nand a second ", None, BODY, "en")

    assert broken.lines == ("One line here", "and a second")
    assert broken.natural == BODY.width("One line here")
    assert not broken.overflow


def test_an_empty_text_has_no_lines() -> None:
    broken = text.break_lines("", 100, BODY, "en")

    assert (broken.lines, broken.natural, broken.overflow) == ((), 0.0, False)


def test_a_line_feed_starts_a_paragraph_whatever_the_width() -> None:
    assert lines("one\ntwo", 1000) == ["one", "two"]


def test_lines_fill_greedily_against_the_width_less_two_percent_of_the_em() -> None:
    both = BODY.width("word word")

    assert lines("word word", both + MARGIN) == ["word word"]
    assert lines("word word", both + MARGIN / 2) == ["word", "word"]


def test_a_line_is_placed_in_the_planned_width_so_the_margin_overflows_nothing() -> None:
    word = BODY.width("word")

    within = text.break_lines("word", word + MARGIN / 2, BODY, "en")
    beyond = text.break_lines("word", word - 0.01, BODY, "en")

    assert (within.lines, within.overflow) == (("word",), False)
    assert beyond.overflow


def test_a_long_word_is_never_shrunk_and_overflows() -> None:
    long = "Pneumonoultramicroscopicsilicovolcanoconiosis"

    broken = text.break_lines(f"a {long} b", 100, BODY, "en")

    assert broken.lines == ("a", long, "b")
    assert broken.overflow and broken.natural == BODY.width(long)


def test_a_long_word_breaks_after_a_slash() -> None:
    path = "visual/communication/libraries"
    width = BODY.width("visual/communication/") + MARGIN + 1

    broken = text.break_lines(path, width, BODY, "en")

    assert broken.lines == ("visual/communication/", "libraries")
    assert not broken.overflow


def test_a_word_that_fits_is_not_broken_at_its_slash() -> None:
    assert lines("and/or", 1000) == ["and/or"]


# --- the language's rules -----------------------------------------------------------------


#: The short prepositions that never end a Czech line (#3084).
CZECH_PREPOSITIONS = ("před", "nad", "pod", "přes", "za", "na", "do", "od", "ve")


def test_the_language_rules_are_data_by_primary_subtag() -> None:
    czech = text.LANGUAGE_RULES["cs"]

    assert czech.one_letter_word
    assert czech.short_prepositions == frozenset(CZECH_PREPOSITIONS)
    assert "en" not in text.LANGUAGE_RULES
    assert text.rules_of("cs-CZ") is czech
    assert text.rules_of("en") == text.LanguageRules()


def test_a_czech_one_letter_word_does_not_end_a_line() -> None:
    # Wide enough for "aaaa v", not for the three words.
    width = BODY.width("aaaa v") + MARGIN + 1

    assert lines("aaaa v bbbb", width, "en") == ["aaaa v", "bbbb"]
    assert lines("aaaa v bbbb", width, "cs") == ["aaaa", "v bbbb"]
    assert lines("aaaa v bbbb", width, "cs-CZ") == ["aaaa", "v bbbb"]


CZECH = "Šel jsem s bratrem k řece a v lese u cesty jsme viděli o samotě i srnu"


def ends_with_one_letter(broken: list[str]) -> bool:
    return any(len(line.split(" ")[-1]) == 1 for line in broken[:-1])


def test_no_czech_line_of_any_width_ends_in_a_one_letter_word() -> None:
    widths = range(60, 400, 7)

    assert any(ends_with_one_letter(lines(CZECH, width, "en")) for width in widths)
    for width in widths:
        broken = lines(CZECH, width, "cs")
        assert not ends_with_one_letter(broken), (width, broken)
        assert " ".join(broken) == CZECH


@pytest.mark.parametrize("preposition", CZECH_PREPOSITIONS)
def test_a_czech_short_preposition_moves_on_with_the_word_it_opens(preposition: str) -> None:
    words = f"aaaa {preposition} bbbb"
    # Wide enough for "aaaa <preposition>", not for the three words.
    width = BODY.width(f"aaaa {preposition}") + MARGIN + 1

    assert lines(words, width, "en") == [f"aaaa {preposition}", "bbbb"]
    assert lines(words, width, "cs") == ["aaaa", f"{preposition} bbbb"]


def test_a_czech_short_preposition_is_kept_off_a_line_end_in_any_case() -> None:
    for preposition in ("Na", "PŘED"):
        width = BODY.width(f"aaaa {preposition}") + MARGIN + 1

        assert lines(f"aaaa {preposition} bbbb", width, "cs") == ["aaaa", f"{preposition} bbbb"]


@pytest.mark.parametrize("word", ["nadace", "zana"])
def test_a_word_that_holds_a_preposition_is_no_preposition(word: str) -> None:
    width = BODY.width(f"aaaa {word}") + MARGIN + 1

    assert lines(f"aaaa {word} bbbb", width, "cs") == [f"aaaa {word}", "bbbb"]


CZECH_PREPOSITIONED = (
    "Šli jsme přes most nad řekou a pod skálou do lesa, od chaty za vodou ve stínu "
    "na louku před domem"
)


def ends_with_preposition(broken: list[str]) -> bool:
    return any(line.split(" ")[-1].lower() in CZECH_PREPOSITIONS for line in broken[:-1])


def test_no_czech_line_of_any_width_ends_in_a_short_preposition() -> None:
    widths = range(60, 400, 7)

    assert any(ends_with_preposition(lines(CZECH_PREPOSITIONED, width, "en")) for width in widths)
    for width in widths:
        broken = lines(CZECH_PREPOSITIONED, width, "cs")
        assert not ends_with_preposition(broken), (width, broken)
        assert " ".join(broken) == CZECH_PREPOSITIONED


# --- runs ---------------------------------------------------------------------------------

#: The heading, in its own semibold family: 24 px, a line height of 1.2.
HEADING = text.Style.of_role(
    "type.heading", RUN_ROLES["type.heading"], text.Faces(lambda family: RUN_FONTS[family])
)
#: The margin at the heading's size, the greatest of the runs below.
WIDE_MARGIN = text.BREAK_MARGIN * 24


def runs(*given: tuple[str, Any]) -> list[Any]:
    return [text.Run(words, face) for words, face in given]


def test_each_weight_a_run_is_drawn_in_is_a_family_of_its_own() -> None:
    """The test brand gives its heading's weight a family and a file of its own, and the
    tests of runs do too, so no run is measured from another weight's file (DEC-012 point 4,
    "A weight's own file")."""
    tokens = json.loads(
        (FIXTURES / "test-brand" / "1.0.0" / "tokens" / "base.tokens.json").read_text()
    )
    heading = tokens["font"]["heading"]
    assert heading["$value"] == [SEMIBOLD]
    files = heading["$extensions"]["pkit.visual-communication"]["files"]
    assert files == {SEMIBOLD: f"fonts/{SEMIBOLD_FONT.name}"}
    weights: dict[str, set[int]] = {}
    for role in RUN_ROLES.values():
        for family in role["fontFamily"]:
            weights.setdefault(family, set()).add(role["fontWeight"])
    assert weights == {FAMILY: {400}, SEMIBOLD: {600}}
    assert HEADING.faces[0].path == SEMIBOLD_FONT
    assert HEADING.width("Wide") != style(fontSize={"value": 24, "unit": "px"}).width("Wide")


def test_a_text_of_one_run_is_broken_as_format_1_breaks_it() -> None:
    for words, width in (("word word word", 80.0), ("One line\nand two", None), ("", 50.0)):
        broken = text.break_runs(runs((words, BODY)), width, "en")
        assert (broken.lines, broken.widths, broken.overflow) == (
            text.break_lines(words, width, BODY, "en").lines,
            text.break_lines(words, width, BODY, "en").widths,
            text.break_lines(words, width, BODY, "en").overflow,
        )
        assert broken.line_height == BODY.line_height
        assert all(line.baseline == BODY.baseline for line in broken.placed)


def test_runs_are_joined_as_written_and_each_part_is_measured_in_its_own_role() -> None:
    broken = text.break_runs(runs(("Plan ", BODY), ("the", HEADING), (" work", BODY)), None, "en")

    [line] = broken.placed
    assert line.text == "Plan the work"
    assert [(span.run, span.text) for span in line.spans] == [
        (0, "Plan "),
        (1, "the"),
        (2, " work"),
    ]
    assert [span.width for span in line.spans] == [
        BODY.advance("Plan "),
        HEADING.advance("the"),
        BODY.advance(" work"),
    ]
    assert line.width == pytest.approx(sum(span.width for span in line.spans))
    assert HEADING.advance("the") > BODY.advance("the")


def test_a_word_whose_letters_lie_in_two_runs_stays_one_word() -> None:
    # Wide enough for "aaaa bb" in the body, not for "aaaa bbbb" with "bb" in the heading.
    width = BODY.advance("aaaa bb") + WIDE_MARGIN + 1
    given = runs(("aaaa bb", BODY), ("bb cccc", HEADING))

    broken = text.break_runs(given, width, "en")

    assert broken.lines == ("aaaa", "bbbb", "cccc")
    assert [[(span.run, span.text) for span in line.spans] for line in broken.placed] == [
        [(0, "aaaa")],
        [(0, "bb"), (1, "bb")],
        [(1, "cccc")],
    ]


def test_a_czech_one_letter_word_moves_on_with_the_next_word_whichever_runs_hold_them() -> None:
    # Wide enough for "aaaa v", not for "aaaa v bbbb".
    width = BODY.advance("aaaa ") + HEADING.advance("v") + WIDE_MARGIN + 1
    given = runs(("aaaa ", BODY), ("v", HEADING), (" bbbb", BODY))

    assert list(text.break_runs(given, width, "en").lines) == ["aaaa v", "bbbb"]
    assert list(text.break_runs(given, width, "cs").lines) == ["aaaa", "v bbbb"]


def test_a_czech_short_preposition_moves_on_with_its_word_whichever_runs_hold_them() -> None:
    # Wide enough for "aaaa přes", not for "aaaa přes bbbb", the preposition and its space
    # in a run of their own.
    width = BODY.advance("aaaa ") + HEADING.advance("přes") + WIDE_MARGIN + 1
    given = runs(("aaaa ", BODY), ("přes ", HEADING), ("bbbb", BODY))

    assert list(text.break_runs(given, width, "en").lines) == ["aaaa přes", "bbbb"]
    assert list(text.break_runs(given, width, "cs").lines) == ["aaaa", "přes bbbb"]


def test_the_margin_is_taken_at_the_greatest_font_size_among_the_runs() -> None:
    given = runs(("word ", HEADING), ("word", BODY))
    both = HEADING.advance("word ") + BODY.advance("word")

    # The body's margin alone would keep both words on one line at the narrower width.
    assert MARGIN < WIDE_MARGIN - 0.1
    assert list(text.break_runs(given, both + WIDE_MARGIN, "en").lines) == ["word word"]
    assert list(text.break_runs(given, both + WIDE_MARGIN - 0.1, "en").lines) == ["word", "word"]


def test_a_text_takes_one_line_height_and_each_line_one_baseline() -> None:
    given = runs(("Small\nand ", BODY), ("Large", HEADING))

    broken = text.break_runs(given, None, "en")

    tall = HEADING.line_height
    assert broken.line_height == tall == pytest.approx(28.8)
    small, mixed = broken.placed
    assert (small.paragraph, mixed.paragraph) == (0, 1)
    assert [(span.run, span.text) for span in mixed.spans] == [(0, "and "), (1, "Large")]
    # A line of one role stands where that role would place it in the text's line height.
    assert small.baseline == BODY.baseline_in(tall)
    # A line of two roles splits the leading around the greatest ascent and descent.
    ascent, descent = max(BODY.ascent, HEADING.ascent), max(BODY.descent, HEADING.descent)
    assert mixed.baseline == pytest.approx((tall - (ascent + descent)) / 2 + ascent)
    assert 0 < mixed.baseline < tall
    assert broken.paragraphs == (((0, "Small"),), ((0, "and "), (1, "Large")))
