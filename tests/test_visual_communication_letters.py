"""Letters that touch across a text's lines (visual-communication DEC-053).

- **Which letters touch** (point 1). Each line of a text and the next, across its
  paragraphs, as the engine sets them: the outlines of their letters, each read from the
  face that shaped it, at its run's size and where the engine places it, and a run's sign,
  meet at the text's step, each curve flattened within 0.001 em. They touch at any step at
  or below their reach, and at none above it, so letters that come near without meeting do
  not. The characters drawn to join the next line's never count; a character of Symbols for
  Legacy Computing does. Two texts' lines are never compared.
- **The finding** (point 2) asks for attention at the text, in the piece, naming the lines,
  the letters that meet, their reach and the step, with the role it comes from, the file
  and the field that give it, and the owner of that version. The engine keeps the step
  (point 3).
- **The word** (point 4). A typography role's token says `tight-lines: true` alone, else
  format 1 refuses it, and on a group it says nothing and asks for attention. Where the
  version whose file holds it gives the step, is released and is still as released,
  validation states the letters as the fact `letters-touch-meant`; anywhere else, and in
  the viewing step's report always, they are `letters-touch`. A word on a role whose line
  height another version gives counts for nothing, and a brand that gives a role its base
  opens drops the base's word.
- **Where it measures nothing** (point 5): a letter with no outline, measured otherwise
  than from a font file or drawn from an SVG of its face's own, gives a statement at the
  text.

The pieces the tests check are written in `tmp_path`, as the piece's own component: the
repository's validation reads every bound file under `tests/`.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib.tables.S_V_G_ import SVGDocument, table_S_V_G_

from tests.in_process import load
from tests.test_visual_communication_checks import LOCAL, local
from tests.test_visual_communication_layout import RUNS
from tests.test_visual_communication_look import (  # noqa: F401
    plugins,
    report_of,
    reports_hold_their_schema,
    run_look,
)
from tests.test_visual_communication_meant_overlaps import ELSEWHERE, OWN, release
from tests.test_visual_communication_pipeline import PIECE, PIECE_FOLDER, drawing_project
from tests.test_visual_communication_pipeline import write_content as write_body
from tests.test_visual_communication_tokens import chain_copy, edit_json, replace_in, setting
from tests.visual_communication_project import FOUNDATIONS, write
from tests.visual_engine import (
    FAMILY,
    FIXTURES,
    FONT,
    ROLES,
    SEMIBOLD,
    SEMIBOLD_FONT,
    draw,
    text,
    top,
)

letters, checks, findings, rendering, tokens = load(
    "visual-communication", "letters", "checks", "findings", "rendering", "tokens"
)

CODE_FAMILY = "Source Code Pro"
CODE_FONT = FIXTURES / "test-brand" / "1.0.0" / "fonts" / "SourceCodePro-Regular.ttf"
FONTS = {FAMILY: FONT, SEMIBOLD: SEMIBOLD_FONT, CODE_FAMILY: CODE_FONT}
#: The family of the font of bars `bars` builds.
BARS = "Bars"
#: The text the tests draw, in the figure.
TRACE = "top/t"
#: The test brand's file of typography, as findings name it, in the project.
BRAND = "visual/libraries/test-brand/1.0.0"
BASE = f"{BRAND}/tokens/base.tokens.json"
#: The word, in the capability's extension key.
WORD = {"$extensions": {"pkit.visual-communication": {"tight-lines": True}}}
#: What the fact adds to the message of `letters-touch`, in the test brand's version.
MEANT = (
    "; the role's token carries `tight-lines` in test-brand@1.0.0, released, which says the "
    "letters are meant"
)
LABELS = (letters.LETTERS_TOUCH, letters.LETTERS_TOUCH_MEANT)
#: The characters the bars font draws, each a bar that reaches 0.3 em below the baseline
#: and 0.9 em above it, so two of them meet across lines at any step up to 1.2 em: a letter,
#: one of each range of the characters drawn to join, a character of Symbols for Legacy
#: Computing, and a star its face draws from an SVG of its own.
JOINING = ("│", "█", "⌠", "⎜")
LEGACY, STAR = "\U0001fb00", "★"


@pytest.fixture(scope="module")
def bars(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A TrueType font of bars, `x`, each character of `JOINING`, `LEGACY` and `STAR`, the
    star also drawn from an SVG of the face's own."""
    path = tmp_path_factory.mktemp("bars") / "Bars.ttf"
    characters = {"x": "x", **{f"u{ord(c):04X}": c for c in (*JOINING, LEGACY, STAR)}}
    builder = FontBuilder(1000, isTTF=True)
    builder.setupGlyphOrder([".notdef", "space", *characters])
    builder.setupCharacterMap({ord(" "): "space", **{ord(c): g for g, c in characters.items()}})
    glyphs = {"space": TTGlyphPen(None).glyph()}
    for glyph in (".notdef", *characters):
        pen = TTGlyphPen(None)
        pen.moveTo((100, -300))
        pen.lineTo((100, 900))
        pen.lineTo((500, 900))
        pen.lineTo((500, -300))
        pen.closePath()
        glyphs[glyph] = pen.glyph()
    builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics({glyph: (600, 100) for glyph in glyphs})
    builder.setupHorizontalHeader(ascent=900, descent=-300)
    builder.setupNameTable({"familyName": BARS, "styleName": "Regular"})
    builder.setupOS2(sTypoAscender=900, usWinAscent=900, usWinDescent=300)
    builder.setupPost()
    star = builder.font.getGlyphID(f"u{ord(STAR):04X}")
    svg = table_S_V_G_()
    document = f'<svg xmlns="http://www.w3.org/2000/svg" id="glyph{star}"/>'
    svg.docList = [SVGDocument(document, star, star, False)]
    builder.font["SVG "] = svg
    builder.save(str(path))
    return path


def faces(**more: Path) -> Any:
    known = {**FONTS, **more}
    return text.Faces(lambda family: known[family])


def drawn(
    words: Any,
    ratio: float = 1.0,
    *,
    families: list[str] | None = None,
    width: str = "=:width",
    fonts: dict[str, Path] | None = None,
    parts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The scene of a figure whose text `t` shows `words` in the body's role, its line height
    `ratio`, in `families` where they are given."""
    held = {"text": {"content": "words", "style": "type.body", "fill": "text-primary"}}
    component = top(parts or {"t": {**held, "width": width}}, fields={"words": {}})
    value = {**ROLES["type.body"], "lineHeight": ratio}
    if families:
        value["fontFamily"] = families
    result = draw(
        {"words": words},
        components={"lab/top": component},
        roles={"type.body": value},
        fonts={**FONTS, **(fonts or {})},
    )
    assert [f.code for f in result.findings if f.level == findings.FAILS] == []
    return result.scene.to_dict()


def given(element: dict[str, Any]) -> Any:
    """The step of `element` as the brand would give it from the body's role."""
    step = float(element["line-height"])
    return letters.Given("type.body", step, 16.0, BASE, "the field", "test-brand@1.0.0", "who")


def found(scene: dict[str, Any], **more: Path) -> list[Any]:
    return letters.letters_touch(scene, faces(**more), given)


def touching(scene: dict[str, Any], **more: Path) -> list[str]:
    """The message of each `letters-touch` the check gives in `scene`."""
    return [f.message for f in found(scene, **more) if f.code == letters.LETTERS_TOUCH]


def element_of(scene: dict[str, Any], trace: str = TRACE) -> dict[str, Any]:
    stack = list(scene["children"])
    while stack:
        each = stack.pop()
        if each["id"] == trace:
            return each
        stack.extend(each.get("children") or [])
    raise AssertionError(f"no element {trace}")


# --- which letters touch ------------------------------------------------------------------------


def test_letters_whose_outlines_meet_across_lines_are_named_with_their_reach() -> None:
    [said] = found(drawn("g\nÁ"))
    assert (said.code, said.level, said.where) == (letters.LETTERS_TOUCH, findings.ATTENTION, TRACE)
    assert said.message == (
        f"`{TRACE}`: letters of its lines touch across them at its line step of 16 px, 1 em of "
        f"the 16 px of `type.body`, which the field in {BASE} gives: lines 1 and 2, `g` over "
        "`Á`, their reach 17.19 px, 1.074 em. Two lines part at a step above their reach"
    )
    assert said.fix.startswith("a wider line step for `type.body`, above 1.074 em, at the field")
    assert said.who == "who"


def test_letters_touch_at_any_step_at_or_below_their_reach_and_at_none_above_it() -> None:
    assert len(touching(drawn("g\nÁ", 1.074))) == 1  # a step of 17.18 px
    assert touching(drawn("g\nÁ", 1.075)) == []  # 17.2 px, 0.01 px above the reach
    assert touching(drawn("g\nÁ", 0.5)) != []


def test_letters_that_come_near_without_meeting_do_not_touch() -> None:
    assert touching(drawn("a\nn")) == []
    assert touching(drawn("g\nÁ", 1.08)) == []


def test_the_lines_a_text_breaks_into_are_compared_as_its_paragraphs_are() -> None:
    assert len(touching(drawn("gg ÁÁ", width="=@space.4"))) == 1
    assert len(touching(drawn("a\ng\nÁ\na"))) == 1


def test_each_two_lines_that_touch_are_named_in_the_one_finding_of_their_text() -> None:
    [said] = touching(drawn("g\nÁ\ng\nÉ"))
    assert "lines 1 and 2, `g` over `Á`" in said
    assert "lines 3 and 4, `g` over `É`" in said
    assert "lines 2 and 3" not in said


def test_only_letters_drawn_over_each_other_along_the_line_touch() -> None:
    assert touching(drawn("g\naaaaÁ")) == []


def test_a_letter_is_read_from_the_face_of_the_family_that_measures_it(bars: Path) -> None:
    """A later family draws what the first lacks: Source Sans Pro has no bar, so the bars
    font draws it, at the run's size."""
    families = [FAMILY, BARS]
    assert touching(drawn("x\nx", families=families, fonts={BARS: bars}), Bars=bars) == []
    [said] = touching(drawn(f"g\n{LEGACY}", families=families, fonts={BARS: bars}), Bars=bars)
    assert f"`g` over `{LEGACY}`" in said


def test_a_run_s_sign_counts_with_its_letters() -> None:
    scene = drawn("g\na")
    assert touching(scene) == []
    lower = element_of(scene)["lines"][1]["spans"][0]
    lower["sign"] = {"d": "M0 0L16 0L16 16L0 16Z", "fill-rule": "nonzero", "size": 16}
    lower["sign"].update(top=0, gap=2)
    [said] = touching(scene)
    assert "`g` over `a run's sign`" in said


def test_the_characters_drawn_to_join_never_count(bars: Path) -> None:
    families = [BARS]
    assert len(touching(drawn("x\nx", families=families, fonts={BARS: bars}), Bars=bars)) == 1
    for joining in JOINING:
        for words in (f"{joining}\n{joining}", f"x\n{joining}", f"{joining}\nx"):
            scene = drawn(words, families=families, fonts={BARS: bars})
            assert touching(scene, Bars=bars) == [], words


def test_box_drawing_in_a_code_font_meets_across_lines_and_is_left_out() -> None:
    assert touching(drawn("│\n│", 0.5, families=[CODE_FAMILY])) == []
    assert touching(drawn("┌┐\n└┘", 0.5, families=[CODE_FAMILY])) == []


def test_a_character_of_symbols_for_legacy_computing_counts_as_a_letter(bars: Path) -> None:
    scene = drawn(f"{LEGACY}\n{LEGACY}", families=[BARS], fonts={BARS: bars})
    [said] = touching(scene, Bars=bars)
    assert f"`{LEGACY}` over `{LEGACY}`" in said
    assert "their reach 19.2 px, 1.2 em" in said


def test_the_lines_of_two_texts_are_never_compared() -> None:
    body = {"text": {"content": "words", "style": "type.body", "fill": "text-primary"}}
    parts = {
        "t": {**body, "width": "=:width"},
        "u": {**body, "y": "=t.bottom - @space.2", "width": "=:width"},
    }
    assert touching(drawn("g", parts=parts)) == []


def test_the_engine_keeps_the_line_step_the_brand_gives() -> None:
    held = element_of(drawn("g\nÁ"))
    assert held["line-height"] == 16
    assert held["sources"]["line-height"] == "role:type.body"
    assert held["height"] == 32


# --- where it measures nothing ------------------------------------------------------------------


def test_a_letter_its_face_draws_from_an_svg_is_stated_unmeasured(bars: Path) -> None:
    scene = drawn(f"x\n{STAR}\nx\nx", families=[BARS], fonts={BARS: bars})
    said = {f.code: f for f in found(scene, Bars=bars)}
    assert set(said) == {letters.LETTERS_TOUCH, letters.LETTERS_UNMEASURED}
    assert "lines 3 and 4" in said[letters.LETTERS_TOUCH].message
    stated = said[letters.LETTERS_UNMEASURED]
    assert (stated.level, stated.where, stated.who, stated.fix) == (findings.FACT, TRACE, "", "")
    assert stated.message == (
        f"`{TRACE}`: the check of letters across lines measured nothing at lines 1 and 2 and "
        "lines 2 and 3, which hold a letter the engine has no outline of: the face of `Bars` "
        f"draws `{STAR}` from a bitmap or an SVG of its own"
    )


def test_a_letter_measured_otherwise_than_from_a_font_file_is_stated_unmeasured() -> None:
    scene = drawn("g\nÁ")
    held = element_of(scene)
    held["paragraphs"][1][0]["measured"] = "widths"
    [stated] = found(scene)
    assert (stated.code, stated.level) == (letters.LETTERS_UNMEASURED, findings.FACT)
    assert stated.message.endswith(
        "the letters of `type.body` are measured `widths`, from no font file"
    )


# --- the finding in a piece ---------------------------------------------------------------------


def tall(root: Path, words: Any = "g\nÁ", *, runs: bool = False) -> None:
    """The piece's body a component of its own that shows `words` in the body's role, or, with
    `runs`, in the runs of a sentence whose strong phrase takes the strong role."""
    style: Any = "type.body"
    field: dict[str, Any] = {"type": "string"}
    if runs:
        style = {"by": "words", "plain": "type.body", "strong": "type.strong"}
        field = {"type": "string", RUNS: ["plain", "strong"]}
    component = local(
        about="A text that may touch across its lines.",
        fields={"type": "object", "required": ["words"], "properties": {"words": field}},
        parts={
            "t": {
                "text": {"content": "words", "style": style, "fill": "text-primary"},
                "width": "=:width",
            }
        },
        preferred={"height": "=t.bottom"},
    )
    write(root / LOCAL / "tall.yaml", component)
    write_body(root, body={"use": f"{OWN}/tall", "words": words})


def tight(root: Path, *roles: str, ratio: float = 1.0, word: bool = True) -> None:
    """The test brand's roles `roles` set at the line height `ratio`, each token carrying the
    word where `word` says so."""

    def change(data: dict[str, Any]) -> None:
        for role in roles:
            token = data["type"][role.removeprefix("type.")]
            token["$value"]["lineHeight"] = ratio
            if word:
                token.update(copy.deepcopy(WORD))

    edit_json(root / BASE, change)


def piece_with(tmp_path: Path, *roles: str, word: bool = True, **given: Any) -> Path:
    root = drawing_project(tmp_path, picture=False)
    tight(root, *(roles or ("type.body",)), word=word)
    tall(root, **given)
    return root


def judged(root: Path) -> list[tuple[str, str, str, str, str, str]]:
    """Each finding of letters validation reads in the piece: its label, its level, its file,
    where it lies, who acts and its message."""
    report = checks.check(root, only=PIECE)
    return sorted(
        (f.code, level, f.file, f.where, f.who, f.message)
        for f, level in report.judged
        if f.code in LABELS
    )


BODY = "figure/body/t"
#: The piece's file, where the finding lies.
PIECE_FILE = f"{PIECE_FOLDER}/piece.yaml"


def test_a_piece_names_letters_that_touch_with_the_field_that_gives_the_step_and_its_owner(
    tmp_path: Path,
) -> None:
    [(label, level, file, where, who, message)] = judged(piece_with(tmp_path, word=False))
    assert (label, level, file, where) == (
        letters.LETTERS_TOUCH,
        findings.ATTENTION,
        PIECE_FILE,
        BODY,
    )
    assert who == findings.PROJECT
    assert f"which the `lineHeight` of `type.body` in {BASE} gives" in message


def test_a_role_whose_step_an_alias_gives_names_the_token_that_holds_the_number(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path, picture=False)
    tight(root, "type.body", word=False)
    edit_json(root / BASE, setting("type|strong|$value", "{type.body}"))
    tall(root, ["g\n", {"text": "Á", "style": "strong"}], runs=True)
    [(_, _, _, _, _, message)] = judged(root)
    assert f"the `lineHeight` of `type.body` in {BASE} gives" in message


def test_the_owner_of_a_version_from_another_repository_is_asked(tmp_path: Path) -> None:
    root = piece_with(tmp_path, word=False)
    release(root, "test-brand", **ELSEWHERE)
    [(_, _, _, _, who, _)] = judged(root)
    assert who == findings.owner_of("test-brand@1.0.0")


def test_a_word_in_a_released_version_that_gives_the_step_makes_the_letters_a_fact(
    tmp_path: Path,
) -> None:
    [plain] = judged(piece_with(tmp_path / "plain", word=False))
    root = piece_with(tmp_path / "meant")
    release(root, "test-brand")
    [(label, level, file, where, who, message)] = judged(root)
    assert (label, level, file, where, who) == (
        letters.LETTERS_TOUCH_MEANT,
        findings.FACT,
        PIECE_FILE,
        BODY,
        "",
    )
    assert message == plain[5] + MEANT


@pytest.mark.parametrize("changed", [False, True], ids=["not-yet-released", "changed-since"])
def test_a_word_in_a_version_not_released_as_it_is_gives_the_check_nothing(
    tmp_path: Path, changed: bool
) -> None:
    [plain] = judged(piece_with(tmp_path / "plain", word=False))
    root = piece_with(tmp_path / "named")
    if changed:
        release(root, "test-brand")
        edit_json(root / BASE, setting("$description", "The test brand, changed."))
    [named] = judged(root)
    assert named == plain
    assert "tight-lines" not in named[5]


def test_where_two_roles_give_a_text_its_step_each_must_carry_the_word(tmp_path: Path) -> None:
    sentence = ["g\n", {"text": "Á", "style": "strong"}]
    one = piece_with(tmp_path / "one", "type.body", runs=True, words=sentence)
    tight(one, "type.strong", word=False)
    release(one, "test-brand")
    assert [label for label, *_ in judged(one)] == [letters.LETTERS_TOUCH]
    both = piece_with(tmp_path / "both", "type.body", "type.strong", runs=True, words=sentence)
    release(both, "test-brand")
    assert [label for label, *_ in judged(both)] == [letters.LETTERS_TOUCH_MEANT]


def test_the_findings_record_keeps_the_word_s_version_and_a_release_turns_it_into_the_fact(
    tmp_path: Path,
) -> None:
    root = piece_with(tmp_path)
    piece = checks.pl.read_piece(root, "visual", PIECE)
    project = checks.pl.Project(piece, piece.lock, checks.Held(root, "visual"))
    record = rendering.record_text(rendering.record(project, checks.computed(project), None))
    (root / PIECE_FOLDER / "findings.yaml").write_bytes(record)
    assert "lies-over-in: test-brand@1.0.0" in record.decode("utf-8")
    assert [label for label, *_ in judged(root)] == [letters.LETTERS_TOUCH]
    release(root, "test-brand")
    assert [label for label, *_ in judged(root)] == [letters.LETTERS_TOUCH_MEANT]


@pytest.mark.parametrize("released", [True, False], ids=["released", "not-yet-released"])
def test_the_viewing_step_s_report_gives_every_such_finding_as_letters_touch(
    tmp_path: Path, released: bool
) -> None:
    root = piece_with(tmp_path)
    if released:
        release(root, "test-brand")
    done = run_look(root, PIECE)
    assert done.returncode == 0, done.stderr
    [image] = report_of(root)["images"]
    said = [each for each in image["findings"] if each["label"] in LABELS]
    assert [(each["label"], each["level"]) for each in said] == [
        (letters.LETTERS_TOUCH, findings.ATTENTION)
    ]
    assert "tight-lines" not in json.dumps(report_of(root))


# --- the word in the brand's files --------------------------------------------------------------


@pytest.fixture(scope="module")
def foundations() -> Any:
    return tokens.read_declarations(FOUNDATIONS / "roles.yaml")


def read(folder: Path, foundations: Any, **locked: Path) -> Any:
    return tokens.read_brand(folder, foundations, locked=locked)


def brand_with(tmp_path: Path, change: Callable[[dict[str, Any]], None]) -> Path:
    base, _ = chain_copy(tmp_path)
    edit_json(base / "tokens" / "base.tokens.json", change)
    return base


def on_body(extension: Any) -> Callable[[dict[str, Any]], None]:
    return setting("type|body|$extensions", {"pkit.visual-communication": extension})


@pytest.mark.parametrize(
    "extension",
    [{"tight-lines": False}, {"tight-lines": "yes"}, {"tight-lines": True, "files": {}}, {}],
    ids=["false", "a-string", "another-key", "empty"],
)
def test_a_typography_token_s_extension_holds_tight_lines_true_alone(
    tmp_path: Path, foundations: Any, extension: Any
) -> None:
    with pytest.raises(tokens.TokenError) as raised:
        read(brand_with(tmp_path, on_body(extension)), foundations)
    [refused] = raised.value.findings
    assert (refused.code, refused.level, refused.where) == (
        "tokens-shape",
        findings.FAILS,
        "type.body",
    )
    assert "`tight-lines: true`" in refused.message


def test_a_typography_token_takes_the_word_and_reads_as_before(
    tmp_path: Path, foundations: Any
) -> None:
    plain = read(chain_copy(tmp_path / "plain")[0], foundations)
    held = read(brand_with(tmp_path / "word", on_body({"tight-lines": True})), foundations)
    assert held.findings == ()
    for combination in held.combinations():
        assert held.resolve("type.body", combination) == plain.resolve("type.body", combination)
    assert held.families() == plain.families()
    step = held.step_of("type.body", {})
    assert step == tokens.StepGiven(
        "test-brand@1.0.0",
        True,
        step.file,
        "the `lineHeight` of `type.body`",
        "test-brand@1.0.0",
    )
    assert step.file.endswith("tokens/base.tokens.json")
    assert plain.step_of("type.body", {}).word is False


def test_tight_lines_on_a_token_of_another_type_is_refused(
    tmp_path: Path, foundations: Any
) -> None:
    word = {"pkit.visual-communication": {"tight-lines": True}}
    for role in ("accent", "font|body"):
        with pytest.raises(tokens.TokenError) as raised:
            read(brand_with(tmp_path / role, setting(f"{role}|$extensions", word)), foundations)
        [refused] = raised.value.findings
        assert refused.code == "tokens-shape", role
        assert "tight-lines" in refused.message


def test_tight_lines_on_a_group_says_nothing_and_asks_for_attention(
    tmp_path: Path, foundations: Any
) -> None:
    word = {"pkit.visual-communication": {"tight-lines": True}}
    held = read(brand_with(tmp_path, setting("type|$extensions", word)), foundations)
    [refused] = held.findings
    assert (refused.code, refused.level, refused.where) == (
        tokens.TIGHT_LINES_REFUSED,
        findings.ATTENTION,
        "type",
    )
    assert refused.who == "the owner of the brand test-brand"
    assert "token of each role" in refused.fix
    assert held.step_of("type.body", {}).word is False


def edition_with(
    tmp_path: Path,
    base_change: Callable[[dict[str, Any]], None],
    edition_change: Callable[[dict[str, Any]], None] | None = None,
    opens: str = "",
) -> tuple[Path, Path]:
    """The test brand changed by `base_change`, opening `opens` too, and the edition built on
    it, changed by `edition_change`."""
    base, edition = chain_copy(tmp_path)
    edit_json(base / "tokens" / "base.tokens.json", base_change)
    if opens:
        replace_in(
            base / "library.yaml", "open: [accent, space]", f"open: [accent, space, {opens}]"
        )
    if edition_change is not None:
        edit_json(edition / "tokens" / "edition.tokens.json", edition_change)
    return base, edition


def both(*changes: Callable[[dict[str, Any]], None]) -> Callable[[dict[str, Any]], None]:
    def change(data: dict[str, Any]) -> None:
        for each in changes:
            each(data)

    return change


def typography(ratio: float) -> dict[str, Any]:
    return {"$type": "typography", "$value": {**ROLES["type.body"], "lineHeight": ratio}}


def test_a_word_on_a_role_whose_number_another_version_gives_counts_for_nothing(
    tmp_path: Path, foundations: Any
) -> None:
    """The edition's word on the heading, whose value aliases the base's body; and the base's
    word on the heading, whose value aliases the body the base opens, which the edition
    gives."""
    word = {"pkit.visual-communication": {"tight-lines": True}}
    plain_body = typography(1.0)
    plain_body["$value"]["fontFamily"] = "{font.body}"
    base, edition = edition_with(
        tmp_path / "aliased",
        lambda data: None,
        lambda data: data.setdefault("type", {}).update(
            heading={"$type": "typography", "$value": "{type.body}", "$extensions": word}
        ),
        opens="type.heading",
    )
    held = read(edition, foundations, **{"test-brand": base})
    assert held.findings == ()
    step = held.step_of("type.heading", {})
    assert (step.token_version, step.word, step.version) == (
        "test-edition@1.0.0",
        True,
        "test-brand@1.0.0",
    )
    assert step.field == "the `lineHeight` of `type.body`"
    base, edition = edition_with(
        tmp_path / "opened",
        both(
            setting("type|heading|$value", "{type.body}"),
            setting("type|heading|$extensions", word),
        ),
        lambda data: data.setdefault("type", {}).update(body=plain_body),
        opens="type.body",
    )
    held = read(edition, foundations, **{"test-brand": base})
    assert held.findings == ()
    step = held.step_of("type.heading", {})
    assert (step.token_version, step.word, step.version) == (
        "test-brand@1.0.0",
        True,
        "test-edition@1.0.0",
    )


def test_a_brand_that_gives_an_open_role_a_value_drops_its_base_s_word(
    tmp_path: Path, foundations: Any
) -> None:
    body = typography(1.0)
    body["$value"]["fontFamily"] = "{font.body}"
    base, edition = edition_with(
        tmp_path,
        on_body({"tight-lines": True}),
        lambda data: data.setdefault("type", {}).update(body=body),
        opens="type.body",
    )
    held = read(edition, foundations, **{"test-brand": base})
    assert held.findings == ()
    assert read(base, foundations).step_of("type.body", {}).word is True
    step = held.step_of("type.body", {})
    assert (step.token_version, step.word, step.version) == (
        "test-edition@1.0.0",
        False,
        "test-edition@1.0.0",
    )


def test_a_default_leads_to_the_token_of_the_role_it_aliases(
    tmp_path: Path, foundations: Any
) -> None:
    """The deck's title, which the test brand gives no value, takes the heading its default
    aliases, and the word on the heading's token."""
    held = read(
        brand_with(tmp_path, setting("type|heading|$extensions", WORD["$extensions"])), foundations
    )
    step = held.step_of("type.title", {})
    assert (step.token_version, step.word, step.field) == (
        "test-brand@1.0.0",
        True,
        "the `lineHeight` of `type.heading`",
    )
