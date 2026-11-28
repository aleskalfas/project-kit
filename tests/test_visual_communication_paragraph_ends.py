"""A paragraph that ends on a word kept off a line's end (visual-communication DEC-075).

- **Which paragraphs and words** (point 1). Each paragraph that a line feed written in the
  text ends, where the text goes on after it, whose last word, with nothing after it but
  spaces, is one the rules of the scene's language keep off a line's end. The words are the
  engine's own: the tests read them from its data. Its runs' texts are read joined, so a
  word whose letters lie in two runs is one word, and a line feed in a later run ends its
  paragraph. A kept word with nothing after it but spaces and line feeds, one a full stop
  follows, a longer word whose last letters spell a kept word, the same words in a language
  with no rules, a line feed before the word and a line feed the engine adds give nothing.
- **The finding** (point 2) asks for attention where the text is written: in the content
  file of the scene's language, at the key path of the run that holds the word's first
  letter, for the piece's author; for a text no content gives, in the file of the component
  that shows it. It names the paragraph and the word, and its fix. A field drawn twice is
  one finding. Through the check, it lies in the piece's content file, on the page its text
  lies on.
- **The engine keeps the paragraphs** the text writes (point 3).

The pieces the tests check are written in `tmp_path`, as the piece's own component: the
repository's validation reads every bound file under `tests/`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load
from tests.test_visual_communication_checks import LOCAL, local
from tests.test_visual_communication_layout import PATH_LIST, RUNS
from tests.test_visual_communication_meant_overlaps import OWN
from tests.test_visual_communication_pipeline import PIECE, PIECE_FOLDER, drawing_project
from tests.test_visual_communication_pipeline import write_content as write_body
from tests.visual_communication_project import write
from tests.visual_engine import draw, layout, top

paragraph_ends, checks, findings, pl, text = load(
    "visual-communication", "paragraph_ends", "checks", "findings", "pipeline", "text"
)

LABEL = paragraph_ends.KEPT_WORD_ENDS_PARAGRAPH
#: The language whose rules the tests plant words of, and its content file, as a scene's
#: findings name it.
LANGUAGE = "cs"
CONTENT = "content.cs.yaml"
#: The text the tests draw, in the figure.
TRACE = "top/t"
#: The fix every finding names.
FIX = (
    "move the word past the line feeds after it, so that it opens the paragraph the text goes "
    "on in, or reword the paragraph's end"
)

#: A field of runs, each run in the body's role.
WORDS = {"type": "string", RUNS: ["plain"]}
#: A text part in the body's role.
BODY = {"style": "type.body", "fill": "text-primary"}
#: A figure whose text `t` shows the field `words`, of runs.
FIGURE = top({"t": {"text": {"content": "words", **BODY}}}, fields={"words": WORDS})
#: A figure whose text `t` shows the field `say`, given as text.
SAYING = top({"t": {"text": {"content": "say", **BODY}}}, fields={"say": {"type": "string"}})
#: A figure whose text `t` shows the field `docs`, a list of paths, a path to a paragraph.
DOCUMENTS = top({"t": {"text": {"content": "docs", **BODY}}}, fields={"docs": PATH_LIST})
#: A figure whose text `t` shows the piece's state, a text no content gives.
STATE = top({"t": {"text": {"fact": "state", **BODY}}})

#: The rules the tests plant words of, the engine's own.
RULES = text.LANGUAGE_RULES[LANGUAGE]
#: One-letter words, in lower and upper case, where the rules keep one.
ONE_LETTER = ("s", "v", "a", "K", "V") if RULES.one_letter_word else ()
#: Each other word the rules keep, in lower case, capitalised and in upper case.
OTHER_WORDS = tuple(
    variant
    for word in sorted(RULES.short_prepositions)
    for variant in (word, word.capitalize(), word.upper())
)


def owner(version: str) -> str:
    """Who the tests say corrects the library version `version`."""
    return f"the owner of {version}"


def scene_of(given: Any, language: str = LANGUAGE, component: Any = FIGURE, **drawn: Any) -> Any:
    """The result of drawing a figure, `component`, whose content is `given`, in
    `language`."""
    result = draw(given, language=language, components={"lab/top": component}, **drawn)
    assert [f.code for f in result.findings if f.level == findings.FAILS] == []
    return result


def found(words: Any, language: str = LANGUAGE, **drawn: Any) -> list[Any]:
    """What the check finds in a figure whose text shows `words`, a field of runs."""
    result = scene_of({"words": words}, language, **drawn)
    return paragraph_ends.kept_word_ends(result.scene.to_dict(), result.added, owner)


def named(words: Any, language: str = LANGUAGE) -> list[tuple[str, str]]:
    """Where each finding of the check lies in `words`, and its message."""
    return [(f.where, f.message) for f in found(words, language)]


def said(place: int, word: str, language: str = LANGUAGE) -> str:
    """The message on paragraph `place`, which ends on the kept word `word`."""
    return (
        f"paragraph {place} ends on `{word}`, a word the rules of `{language}` keep off a "
        "line's end, and the line feed after it ends the line, so no break carries the word on "
        "to what follows it"
    )


# --- which paragraphs and words -----------------------------------------------------------------


def test_the_tests_plant_words_the_rules_keep() -> None:
    assert ONE_LETTER or OTHER_WORDS


@pytest.mark.parametrize("word", ONE_LETTER + OTHER_WORDS)
def test_each_kept_word_before_a_line_feed_the_text_goes_on_after_is_named(word: str) -> None:
    [finding] = found(f"Spojení {word}\ndatabází")

    assert (finding.code, finding.level) == (LABEL, findings.ATTENTION)
    assert (finding.file, finding.where, finding.library) == (CONTENT, "words", "")
    assert (finding.who, finding.message, finding.fix) == (findings.AUTHOR, said(1, word), FIX)
    assert finding.extra["place"] == TRACE


def test_a_kept_word_that_opens_its_paragraph_is_named_too() -> None:
    assert named("s\ndatabází") == [("words", said(1, "s"))]


def test_spaces_after_the_kept_word_change_nothing() -> None:
    assert named("Spojení s  \ndatabází") == [("words", said(1, "s"))]


def test_a_kept_word_before_two_line_feeds_is_named() -> None:
    assert named("Spojení s\n\ndatabází") == [("words", said(1, "s"))]


def test_a_kept_word_whose_next_paragraph_opens_with_a_dash_is_named() -> None:
    assert named("Spojení s\n- databází") == [("words", said(1, "s"))]


def test_each_paragraph_a_line_feed_ends_is_read_while_the_text_goes_on() -> None:
    assert named("Varianta A\nVarianta B\nVarianta C") == [
        ("words", said(1, "A")),
        ("words", said(2, "B")),
    ]


def test_a_language_s_rules_are_read_by_its_primary_subtag() -> None:
    assert named("Spojení s\ndatabází", "cs-CZ") == [("words", said(1, "s", "cs-CZ"))]


@pytest.mark.parametrize(
    "words",
    [
        pytest.param("Spojení s", id="the-text-s-end"),
        pytest.param("Spojení s\n", id="a-line-feed-then-the-text-s-end"),
        pytest.param("Spojení s \n \n\n  ", id="spaces-and-line-feeds-to-the-text-s-end"),
        pytest.param("Spojení s.\ndatabází", id="a-full-stop"),
        pytest.param("Spojení s:\ndatabází", id="a-colon"),
        pytest.param("Spojení\ns databází", id="the-line-feed-before-the-word"),
        pytest.param("nadace\nzana\npodle\ndatabází", id="longer-words-that-end-on-a-kept-word"),
        pytest.param("Spojení 7\ndatabází", id="a-digit"),
    ],
)
def test_a_paragraph_that_ends_on_no_kept_word_where_the_text_goes_on_is_not_named(
    words: str,
) -> None:
    assert found(words) == []


def test_a_language_with_no_rules_of_its_own_keeps_no_word() -> None:
    assert "en" not in text.LANGUAGE_RULES
    assert found("Spojení s\ndatabází", "en") == []


# --- a line feed the engine adds ----------------------------------------------------------------


def test_a_path_ending_on_a_kept_word_before_another_path_is_not_named() -> None:
    result = scene_of({"docs": ["docs/s", "docs/b.md"]}, component=DOCUMENTS)

    assert result.added == {TRACE: frozenset({0})}
    assert paragraph_ends.kept_word_ends(result.scene.to_dict(), result.added, owner) == []


def test_the_same_paragraphs_written_in_the_text_are_named() -> None:
    result = scene_of({"say": "docs/s\ndocs/b.md"}, component=SAYING)

    assert result.added == {}
    [finding] = paragraph_ends.kept_word_ends(result.scene.to_dict(), result.added, owner)
    assert (finding.file, finding.where, finding.message) == (CONTENT, "say", said(1, "s"))


def test_the_engine_marks_the_line_feed_after_each_path_but_the_last() -> None:
    result = scene_of({"docs": ["a.md", "b/s", "c.md"]}, component=DOCUMENTS)

    assert result.added == {TRACE: frozenset({0, 1})}


# --- across runs --------------------------------------------------------------------------------


def test_a_kept_word_whose_letters_lie_in_two_runs_is_one_word() -> None:
    assert named(["Spojení n", "a\ndatabází"]) == [("words#1", said(1, "na"))]
    assert named(["Spojení na", "še\ndatabází"]) == []


def test_a_kept_word_in_a_run_before_the_run_that_holds_the_line_feed_is_named() -> None:
    assert named(["Spojení s", " ", {"text": "\ndatabází"}]) == [("words#1", said(1, "s"))]


def test_the_finding_lies_at_the_run_that_holds_the_word_s_first_letter() -> None:
    assert named(["Spojení ", "s\ndatabází"]) == [("words#2", said(1, "s"))]
    assert named(["Spojení\n", "jen s\ndatabází"]) == [("words#2", said(2, "s"))]


# --- the finding --------------------------------------------------------------------------------


def test_a_field_two_texts_show_lies_at_one_place_with_one_message() -> None:
    twice = top(
        {
            "t": {"text": {"content": "words", **BODY}},
            "u": {"text": {"content": "words", **BODY}, "y": "=t.bottom"},
        },
        fields={"words": WORDS},
    )

    [first, second] = found("Spojení s\ndatabází", component=twice)

    assert (first.where, first.message) == (second.where, second.message)
    assert (first.extra["place"], second.extra["place"]) == (TRACE, "top/u")


def test_a_text_no_content_gives_lies_at_the_library_component_that_shows_it() -> None:
    facts = layout.Facts("v88", "2088-08-28", "Spojení s\ndatabází")
    result = scene_of({}, component=STATE, facts=facts)

    [finding] = paragraph_ends.kept_word_ends(result.scene.to_dict(), result.added, owner)

    assert (finding.code, finding.level, finding.message) == (
        LABEL,
        findings.ATTENTION,
        said(1, "s"),
    )
    assert (finding.file, finding.where, finding.library) == (
        "components/top.yaml",
        TRACE,
        "lab@1.0.0",
    )
    assert (finding.who, finding.fix) == ("the owner of lab@1.0.0", FIX)


def test_a_text_no_content_gives_lies_at_the_piece_s_own_component_for_its_author() -> None:
    facts = layout.Facts("v88", "2088-08-28", "Spojení s\ndatabází")
    result = draw(
        {}, use="piece/top", language=LANGUAGE, components={"piece/top": STATE}, facts=facts
    )

    [finding] = paragraph_ends.kept_word_ends(result.scene.to_dict(), result.added, owner)

    assert (finding.file, finding.where, finding.library) == ("components/top.yaml", TRACE, "")
    assert finding.who == findings.AUTHOR


# --- the engine keeps the paragraphs ------------------------------------------------------------


def test_the_engine_keeps_the_paragraphs_the_text_writes() -> None:
    element = scene_of({"words": "Spojení s\ndatabází"}).scene.find(TRACE)

    assert element is not None
    paragraphs = element.properties["paragraphs"]
    assert [[run["text"] for run in paragraph] for paragraph in paragraphs] == [
        ["Spojení s"],
        ["databází"],
    ]
    assert [line["text"] for line in element.properties["lines"]] == ["Spojení s", "databází"]


# --- the finding in a piece ---------------------------------------------------------------------

#: The piece's text, the body's part `t`.
PIECE_TEXT = "figure/body/t"


def written(tmp_path: Path, words: Any) -> Path:
    """A piece in English and Czech whose body is a component of its own that shows `words`,
    in a field of runs, in both languages."""
    root = drawing_project(tmp_path, picture=False, languages=["en", LANGUAGE])
    component = local(
        about="A text whose paragraphs may end on a kept word.",
        fields={"type": "object", "required": ["words"], "properties": {"words": WORDS}},
        parts={"t": {"text": {"content": "words", **BODY}, "width": "=:width"}},
        preferred={"height": "=t.bottom"},
    )
    write(root / LOCAL / "words.yaml", component)
    for language in ("en", LANGUAGE):
        write_body(root, language, body={"use": f"{OWN}/words", "words": words})
    return root


def test_a_piece_names_the_paragraph_in_its_content_for_its_author(tmp_path: Path) -> None:
    root = written(tmp_path, ["Spojení ", {"text": "s\ndatabází"}])

    report = checks.check(root, only=PIECE)
    judged = [(f, level) for f, level in report.judged if f.code == LABEL]

    [(finding, level)] = judged
    assert level == findings.ATTENTION
    assert (finding.file, finding.where) == (f"{PIECE_FOLDER}/{CONTENT}", "body.words#2")
    assert (finding.who, finding.message) == (findings.AUTHOR, said(1, "s"))
    assert not report.failed()


def test_a_piece_s_finding_comes_from_its_scene_on_the_text_s_page(tmp_path: Path) -> None:
    root = written(tmp_path, "Spojení s\ndatabází")
    piece = pl.read_piece(root, "visual", PIECE)
    project = pl.Project(piece, piece.lock, pl.Held(root, "visual"))
    results = project.scenes(facts=project.piece.stand_ins)

    [each] = [f for f in checks.found_in(project, results) if f.finding.code == LABEL]

    assert each.check is paragraph_ends.CHECK
    assert (each.language, each.page) == (LANGUAGE, "figure")
    assert each.finding.extra["place"] == PIECE_TEXT
    assert not paragraph_ends.CHECK.compares
    assert paragraph_ends.CHECK.reach is None
    assert paragraph_ends.CHECK in checks.SCENE_CHECKS
