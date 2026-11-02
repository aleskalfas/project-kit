"""Text measured from committed font files, and broken into lines by the engine
(visual-communication DEC-005 point 4, DEC-004 point 9; #2428).

- each run shaped with HarfBuzz from the file a family names, the next family measuring
  what the first lacks; a missing file or an unmeasured character refused, naming it;
- lines broken at Unicode's break opportunities and the language's own rules (Czech: a
  one-letter word never ends a line), against the planned width less 2 % of the em, and
  placed in the planned width;
- never shrunk: a long word breaks after a `/`, else the text overflows.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest
from fontTools import subset

from tests.visual_engine import FAMILY, FONT, ROLES, env, text

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


def test_the_language_rules_are_data_by_primary_subtag() -> None:
    assert text.ONE_LETTER_WORD in text.LANGUAGE_RULES["cs"]
    assert "en" not in text.LANGUAGE_RULES


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
