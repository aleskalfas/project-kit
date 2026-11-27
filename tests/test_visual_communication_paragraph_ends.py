"""A paragraph that ends on a word kept off a line's end (visual-communication DEC-075).

- **Which paragraphs and words** (point 1). Each paragraph a line feed ends, every one of a
  text's paragraphs but its last, whose last word, with nothing after it but spaces, is one
  the rules of the scene's language keep off a line's end: in Czech, a one-letter word and
  each short preposition, in any case. Its runs' texts are read joined, so a word whose
  letters lie in two runs is one word, and a line feed in a later run ends its paragraph.
  A kept word that ends the text, one a full stop follows, a word that holds a kept word,
  the same words in a language with no rules, and a line feed before the word give nothing.
- **The finding** (point 2) asks the piece's author for attention, in the content file of the
  scene's language, at the key path of the run that holds the word's first letter, naming
  the paragraph and the word, and its fix. A field drawn twice is one finding. Through the
  check, it lies in the piece's content file, on the page its text lies on.
- **The engine keeps the paragraphs** the content writes (point 3).

The pieces the tests check are written in `tmp_path`, as the piece's own component: the
repository's validation reads every bound file under `tests/`.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load
from tests.test_visual_communication_checks import LOCAL, local
from tests.test_visual_communication_layout import RUNS
from tests.test_visual_communication_meant_overlaps import OWN
from tests.test_visual_communication_pipeline import PIECE, PIECE_FOLDER, drawing_project
from tests.test_visual_communication_pipeline import write_content as write_body
from tests.test_visual_communication_text import CZECH_PREPOSITIONS
from tests.visual_communication_project import write
from tests.visual_engine import draw, top

paragraph_ends, checks, findings, pl = load(
    "visual-communication", "paragraph_ends", "checks", "findings", "pipeline"
)

LABEL = paragraph_ends.KEPT_WORD_ENDS_PARAGRAPH
#: The content file of the Czech scene, as a scene's findings name it.
CONTENT = "content.cs.yaml"
#: The text the tests draw, in the figure.
TRACE = "top/t"

#: A field of runs, each run in the body's role.
WORDS = {"type": "string", RUNS: ["plain"]}
#: A figure whose text `t` shows the field `words`, of runs.
FIGURE = top(
    {"t": {"text": {"content": "words", "style": "type.body", "fill": "text-primary"}}},
    fields={"words": WORDS},
)

#: The one-letter words the tests plant, in lower and upper case.
ONE_LETTER = ("s", "v", "a", "K", "V")
#: Each short preposition, in lower case, capitalised and in upper case.
PREPOSITIONS = tuple(
    variant
    for preposition in CZECH_PREPOSITIONS
    for variant in (preposition, preposition.capitalize(), preposition.upper())
)


def scene_of(words: Any, language: str = "cs", component: Any = FIGURE) -> dict[str, Any]:
    """The scene of a figure whose text shows `words`, drawn in `language`."""
    result = draw({"words": words}, language=language, components={"lab/top": component})
    assert [f.code for f in result.findings if f.level == findings.FAILS] == []
    return result.scene.to_dict()


def found(words: Any, language: str = "cs", **given: Any) -> list[Any]:
    return paragraph_ends.kept_word_ends(scene_of(words, language, **given), CONTENT)


def named(words: Any, language: str = "cs") -> list[tuple[str, str]]:
    """Where each finding of the check lies in `words`, and its message."""
    return [(f.where, f.message) for f in found(words, language)]


def said(place: int, word: str) -> str:
    """The message on paragraph `place`, which ends on the Czech kept word `word`."""
    return (
        f"paragraph {place} ends on `{word}`, a word the rules of `cs` keep off a line's end, "
        "and the line feed after it ends the line, so no break carries the word on to the word "
        "after it"
    )


def element_of(scene: dict[str, Any], trace: str = TRACE) -> dict[str, Any]:
    stack = list(scene["children"])
    while stack:
        each = stack.pop()
        if each["id"] == trace:
            return each
        stack.extend(each.get("children") or [])
    raise AssertionError(f"no element {trace}")


# --- which paragraphs and words -----------------------------------------------------------------


@pytest.mark.parametrize("word", ONE_LETTER + PREPOSITIONS)
def test_each_kept_word_before_a_line_feed_is_named(word: str) -> None:
    [finding] = found(f"Spojení {word}\ndatabází")

    assert (finding.code, finding.level) == (LABEL, findings.ATTENTION)
    assert (finding.file, finding.where, finding.who) == (CONTENT, "words", findings.AUTHOR)
    assert finding.message == said(1, word)
    assert finding.fix == (
        "move the line feed before the word, so that the word opens the next paragraph with "
        "the word after it, or reword the paragraph's end"
    )


def test_a_kept_word_that_opens_its_paragraph_is_named_too() -> None:
    assert named("na\ndatabází") == [("words", said(1, "na"))]


def test_spaces_between_the_word_and_the_line_feed_change_nothing() -> None:
    assert named("Spojení s  \ndatabází") == [("words", said(1, "s"))]


def test_each_paragraph_a_line_feed_ends_is_read_and_the_last_is_not() -> None:
    assert named("Varianta A\nVarianta B\nVarianta C") == [
        ("words", said(1, "A")),
        ("words", said(2, "B")),
    ]


@pytest.mark.parametrize(
    "words",
    [
        pytest.param("Spojení s", id="the-text-s-end"),
        pytest.param("Spojení s.\ndatabází", id="a-full-stop"),
        pytest.param("Spojení s:\ndatabází", id="a-colon"),
        pytest.param("Spojení\ns databází", id="the-line-feed-before-the-word"),
        pytest.param("nadace\nzana\npodle\ndatabází", id="words-that-hold-a-kept-word"),
        pytest.param("Spojení 7\ndatabází", id="a-digit"),
    ],
)
def test_a_paragraph_that_ends_on_no_kept_word_before_a_line_feed_is_not_named(
    words: str,
) -> None:
    assert found(words) == []


def test_a_line_feed_that_ends_the_text_ends_the_paragraph_before_it() -> None:
    assert named("Spojení s\n") == [("words", said(1, "s"))]
    assert named("Spojení s\n\n") == [("words", said(1, "s"))]


def test_a_language_with_no_rules_of_its_own_keeps_no_word() -> None:
    assert found("Spojení s\ndatabází", "en") == []
    assert found("Spojení s\ndatabází", "cs-CZ") != []


# --- across runs --------------------------------------------------------------------------------


def test_a_kept_word_whose_letters_lie_in_two_runs_is_one_word() -> None:
    assert named(["Spojení n", "a\ndatabází"]) == [("words#1", said(1, "na"))]
    assert named(["Spojení na", "še\ndatabází"]) == []


def test_a_line_feed_in_a_later_run_than_the_word_ends_its_paragraph() -> None:
    assert named(["Spojení s", " ", {"text": "\ndatabází"}]) == [("words#1", said(1, "s"))]


def test_the_finding_lies_at_the_run_that_holds_the_word_s_first_letter() -> None:
    assert named(["Spojení ", "s\ndatabází"]) == [("words#2", said(1, "s"))]
    assert named(["Spojení\n", "jen s\ndatabází"]) == [("words#2", said(2, "s"))]


# --- the finding --------------------------------------------------------------------------------


def test_a_field_two_texts_show_lies_at_one_place_with_one_message() -> None:
    body = {"text": {"content": "words", "style": "type.body", "fill": "text-primary"}}
    twice = top({"t": body, "u": {**body, "y": "=t.bottom"}}, fields={"words": WORDS})

    [first, second] = found("Spojení s\ndatabází", component=twice)

    assert (first.where, first.message) == (second.where, second.message)
    assert (first.extra["place"], second.extra["place"]) == (TRACE, "top/u")


def test_a_run_whose_source_is_no_content_s_lies_at_its_text() -> None:
    scene = scene_of("Spojení s\ndatabází")
    edited = copy.deepcopy(scene)
    element_of(edited)["paragraphs"][0][0]["sources"]["text"] = "fact:state"

    [finding] = paragraph_ends.kept_word_ends(edited, CONTENT)

    assert (finding.file, finding.where) == (CONTENT, TRACE)


# --- the engine keeps the paragraphs ------------------------------------------------------------


def test_the_engine_keeps_the_paragraphs_the_content_writes() -> None:
    element = element_of(scene_of("Spojení s\ndatabází"))

    assert [[run["text"] for run in paragraph] for paragraph in element["paragraphs"]] == [
        ["Spojení s"],
        ["databází"],
    ]
    assert [line["text"] for line in element["lines"]] == ["Spojení s", "databází"]


# --- the finding in a piece ---------------------------------------------------------------------

#: The piece's text, the body's part `t`.
BODY = "figure/body/t"


def written(tmp_path: Path, words: Any) -> Path:
    """A piece in English and Czech whose body is a component of its own that shows `words`,
    in a field of runs, in both languages."""
    root = drawing_project(tmp_path, picture=False, languages=["en", "cs"])
    component = local(
        about="A text whose paragraphs may end on a kept word.",
        fields={"type": "object", "required": ["words"], "properties": {"words": WORDS}},
        parts={
            "t": {
                "text": {"content": "words", "style": "type.body", "fill": "text-primary"},
                "width": "=:width",
            }
        },
        preferred={"height": "=t.bottom"},
    )
    write(root / LOCAL / "words.yaml", component)
    for language in ("en", "cs"):
        write_body(root, language, body={"use": f"{OWN}/words", "words": words})
    return root


def test_a_piece_names_the_paragraph_in_its_czech_content_for_its_author(tmp_path: Path) -> None:
    root = written(tmp_path, ["Spojení ", {"text": "s\ndatabází"}])

    report = checks.check(root, only=PIECE)
    judged = [(f, level) for f, level in report.judged if f.code == LABEL]

    [(finding, level)] = judged
    assert level == findings.ATTENTION
    assert (finding.file, finding.where) == (f"{PIECE_FOLDER}/{CONTENT}", "body.words#2")
    assert (finding.who, finding.message) == (findings.AUTHOR, said(1, "s"))
    assert not report.failed()


def test_a_piece_s_finding_comes_from_its_czech_scene_on_the_text_s_page(tmp_path: Path) -> None:
    root = written(tmp_path, "Spojení s\ndatabází")
    piece = pl.read_piece(root, "visual", PIECE)
    project = pl.Project(piece, piece.lock, pl.Held(root, "visual"))
    results = project.scenes(facts=project.piece.stand_ins)

    [each] = [f for f in checks.found_in(project, results) if f.finding.code == LABEL]

    assert each.check is paragraph_ends.CHECK
    assert (each.language, each.page) == ("cs", "figure")
    assert each.finding.extra["place"] == BODY
    assert not paragraph_ends.CHECK.compares
    assert paragraph_ends.CHECK.reach is None
    assert paragraph_ends.CHECK in checks.SCENE_CHECKS
