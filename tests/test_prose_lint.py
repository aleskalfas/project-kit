"""The prose lint, `scripts/prose_lint.py` (#1415).

- **Each type is an entry:** a test covers each of the five types with an
  entry and no code of its own: `count`, `forbid`, `substitute`, `link-resolves`
  and `nesting`, and `forbid` reading the whole file.
- **The reading:** words and sentences as RS-WRITE-005's *How* reads them, and
  a list's levels as RS-WRITE-017's *How* counts them, each choice where a
  *How* is silent pinned here.
- **The change:** the lint reports a break in the text a change adds or moves,
  in an artefact a rule declaring the lint reaches. It leaves alone a break the
  change only sits beside. It reads reach and base from `pkit rule-sets altered`.
- **The data file and `WRITE` agree:** every entry names a rule whose set
  declares the lint, and every declaration has an entry.

The change tests run on the shared adopter-repository fixture. A rule set named
`WRITE`, scoped to `docs/guides/`, declares the lint for RS-WRITE-005,
RS-WRITE-008, RS-WRITE-017 and RS-WRITE-018, so the project's own entries apply
there.

No test here writes a control or bidirectional character as an escape in its
source: each is built with `chr`, so the source holds none (RS-WRITE-018).
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest
from scripts import prose_lint as pl

from project_kit import rule_sets as rs
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.friction_documents import CONFIG, friction_config
from tests.test_rule_sets import rule_set_text, rules

REPO = Path(__file__).resolve().parents[1]
GUIDES = "docs/guides"
A = f"{GUIDES}/a.md"
SET = "docs/rule-sets/write.md"

#: A sentence of 27 words.
LONG = (
    "This sentence holds many words on purpose so that the lint can count them all "
    "and find that it runs over the limit of twenty five words."
)


def found(text: str, entries: Sequence[pl.Entry] | None = None, **kwargs: Any) -> list[str]:
    """`<line> <rule>: <message>` for each finding in a given text."""
    return [f"{f.line} {f.rule}: {f.message}" for f in pl.lint_text(text, entries, **kwargs)]


def counted(text: str) -> list[int]:
    """The word count of each sentence of a text's body, as RS-WRITE-005 reads it."""
    sentences: list[int] = []
    for block in pl.markdown_blocks(text):
        sentences += [unit.words for unit in pl.sentences(block, block.text)]
    return sentences


# --- each type is an entry --------------------------------------------------------------


def test_the_data_file_holds_its_entries() -> None:
    entries = pl.load_entries()
    assert [(e.rule, e.type, e.whole_file) for e in entries] == [
        ("RS-WRITE-005", "count", False),
        ("RS-WRITE-008", "forbid", False),
        ("RS-WRITE-017", "nesting", False),
        ("RS-WRITE-018", "forbid", True),
    ]


def test_count_words_in_a_sentence_is_an_entry() -> None:
    """RS-WRITE-005: a sentence over 25 words, named with its line and the rule's id."""
    text = f"# Title\n\nA short one. {LONG}\n"
    assert found(text) == [
        '3 RS-WRITE-005: a sentence of 27 words, over 25: "This sentence holds many words on '
        'purpose so …"'
    ]


def test_count_sentences_in_a_paragraph_is_an_entry() -> None:
    """RS-WRITE-007's count, an entry alone: a list item counts as a paragraph, and table
    cells are exempt."""
    four = pl.entry(
        {
            "rule": "RS-WRITE-007",
            "type": "count",
            "count": "sentences",
            "in": "paragraph",
            "max": 4,
            "except": ["cells"],
        }
    )
    text = "One. Two. Three. Four.\n\n- One. Two. Three. Four. Five.\n\n| A. B. C. D. E. |\n"
    assert found(text, [four]) == [
        '3 RS-WRITE-007: a paragraph of 5 sentences, over 4: "One. Two. Three. Four. Five."'
    ]


def test_forbid_is_an_entry() -> None:
    """RS-WRITE-008: a semicolon in prose, never in code or in quotation marks."""
    text = 'One; two.\n\nCode `a; b` and a quote, "one; two", are exempt.\n\n```\nx; y\n```\n'
    assert found(text) == ['1 RS-WRITE-008: a semicolon: "One; two."']


def test_substitute_is_an_entry() -> None:
    """RS-WRITE-011's kind of part: a word the glossary replaces, as a whole word."""
    term = pl.entry(
        {"rule": "RS-WRITE-011", "type": "substitute", "replace": {"unit of work": "task"}}
    )
    text = "Each Unit of work lands. A unit-of-work-ish word is another word.\n"
    assert found(text, [term]) == ['1 RS-WRITE-011: "Unit of work": write "task"']


def test_link_resolves_is_an_entry() -> None:
    """RS-USER-001's kind of part: a link's target exists, read from the linking file."""
    links = pl.entry({"rule": "RS-USER-001", "type": "link-resolves"})
    text = (
        "See [the guide](guide.md#top), [the folder](../ref/), [the site](https://example.org)"
        " and [a section](#here).\n\n"
        "Not [this one](gone.md), not [above the root](../../../x.md), and `[code](no.md)`.\n"
    )
    exists = pl.tree_exists(["docs/guides/guide.md", "docs/ref/index.md"])
    assert found(text, [links], path="docs/guides/a.md", exists=exists) == [
        '3 RS-USER-001: the link target "gone.md" does not exist',
        '3 RS-USER-001: the link target "../../../x.md" does not exist',
    ]


def test_a_link_target_is_read_as_written() -> None:
    """Bold marks are never removed from a target, a link definition is read, the root
    resolves, and a protocol-relative URL is not checked."""
    links = pl.entry({"rule": "RS-USER-001", "type": "link-resolves"})
    text = (
        "See [init](../src/pkg/__init__.py), [the root](../), [a host](//example.org/x)"
        " and [a ref][r].\n\n"
        "[r]: ../src/pkg/__main__.py\n"
    )
    exists = pl.tree_exists(["src/pkg/__init__.py"])
    assert found(text, [links], path="docs/a.md", exists=exists) == [
        '3 RS-USER-001: the link target "../src/pkg/__main__.py" does not exist'
    ]


def test_a_nested_item_is_reported_once_whatever_it_holds() -> None:
    """Once for an item with a later block, and an item that opens with a fence is
    reported with no quote."""
    text = (
        "- one\n"
        "  - two\n"
        "    - three\n"
        "      - four\n\n"
        "        More of four.\n"
        "      - ```\n"
        "        code\n"
        "        ```\n"
    )
    assert found(text) == [
        '4 RS-WRITE-017: a list item 4 levels deep, over 3: "four"',
        "7 RS-WRITE-017: a list item 4 levels deep, over 3",
    ]


def test_a_finding_shows_a_control_character_as_its_code_point() -> None:
    """In every finding, so the report itself is never reordered: a context, a match a
    finding quotes, a word to replace and a link's target. No pattern searches a link's
    target, so the forbid finds the one in the prose alone."""
    rlo = chr(0x202E)
    assert found(f"Plain{rlo}; one.\n", [pl.load_entries()[1]]) == [
        '1 RS-WRITE-008: a semicolon: "Plain<U+202E>; one."'
    ]
    unnamed = pl.entry({"rule": "RS-X-001", "type": "forbid", "pattern": rlo})
    term = pl.entry({"rule": "RS-X-002", "type": "substitute", "replace": {f"a{rlo}b": "c"}})
    links = pl.entry({"rule": "RS-X-003", "type": "link-resolves"})
    text = f"One a{rlo}b and [x](gone{rlo}.md).\n"
    assert found(text, [unnamed, term, links], exists=lambda _rel: False) == [
        '1 RS-X-001: "<U+202E>": "One a<U+202E>b and [x](gone<U+202E>.md)."',
        '1 RS-X-002: "a<U+202E>b": write "c"',
        '1 RS-X-003: the link target "gone<U+202E>.md" does not exist',
    ]


def test_nesting_is_an_entry() -> None:
    """RS-WRITE-017: each list item past level three, named with its marker's line. A
    label-only item is an item too, and an ordered list nests like any other."""
    text = (
        "- one\n"
        "  - two\n"
        "    - three\n"
        "      - four\n"
        "      - **Label:**\n"
        "    - three again\n"
        "- one again\n"
        "  1. two\n"
        "     1) three\n"
        "        * four, in an ordered list\n"
    )
    assert found(text) == [
        '4 RS-WRITE-017: a list item 4 levels deep, over 3: "four"',
        "5 RS-WRITE-017: a list item 4 levels deep, over 3",
        '10 RS-WRITE-017: a list item 4 levels deep, over 3: "four, in an ordered list"',
    ]


def test_forbid_in_the_whole_file_is_an_entry() -> None:
    """RS-WRITE-018: a control or bidirectional character anywhere in the file, code,
    headings, front matter, comments and the container included. A tab and a line
    break are none, and a finding shows the character as its code point. YAML refuses
    most controls, so the front matter holds bidirectional ones here."""
    rlo, esc, lrm, lri, nel = chr(0x202E), chr(0x1B), chr(0x200E), chr(0x2066), chr(0x85)
    text = (
        "---\n"
        f"title: A{lrm} title\n"
        f'pkit: {{friction: {{unanchored-because: "No{lri} code."}}}}\n'
        "---\n\n"
        f"# Heading {rlo}\n\n"
        "Tabs\tand line ends are fine.\n\n"
        f"```\ncode{nel}here\n```\n\n"
        f"<!-- a comment {esc}[2K -->\n"
    )
    assert found(text) == [
        '2 RS-WRITE-018: a control or bidirectional character: "title: A<U+200E> title"',
        "3 RS-WRITE-018: a control or bidirectional character: "
        '"pkit: {friction: {unanchored-because: "No<U+2066> code."}}"',
        '6 RS-WRITE-018: a control or bidirectional character: "# Heading <U+202E>"',
        '11 RS-WRITE-018: a control or bidirectional character: "code<U+0085>here"',
        '14 RS-WRITE-018: a control or bidirectional character: "<!-- a comment <U+001B>[2K -->"',
    ]


def test_a_whole_file_entry_reads_no_prose_and_a_prose_one_no_whole_file() -> None:
    """A prose `forbid` leaves a code block alone, and a whole-file one reads it; each is
    checked once."""
    prose = pl.entry({"rule": "RS-X-001", "type": "forbid", "pattern": "x"})
    whole = pl.entry({"rule": "RS-X-002", "type": "forbid", "pattern": "x", "in": "file"})
    text = "```\nx\n```\n"
    assert found(text, [prose, whole]) == ['2 RS-X-002: "x": "x"']


@pytest.mark.parametrize(
    ("data", "says"),
    [
        ({"rule": "WRITE-5", "type": "count"}, "is not a rule id"),
        ({"rule": "RS-WRITE-005", "type": "occurrence"}, "`type` is not one of"),
        ({"rule": "RS-WRITE-008", "type": "forbid", "pattern": ";", "max": 1}, "takes no max"),
        ({"rule": "RS-WRITE-008", "type": "forbid", "pattern": "("}, "does not compile"),
        (
            {"rule": "RS-WRITE-008", "type": "forbid", "pattern": ";", "except": ["tables"]},
            "`except` lists only",
        ),
        (
            {"rule": "RS-WRITE-005", "type": "count", "count": "sentences", "in": "sentence"},
            "a sentence holds one sentence",
        ),
        (
            {"rule": "RS-WRITE-005", "type": "count", "count": "words", "in": "sentence"},
            "`max` is a whole number",
        ),
        ({"rule": "RS-WRITE-011", "type": "substitute", "replace": {}}, "`replace` maps"),
        ({"rule": "RS-WRITE-011", "type": "substitute", "replace": {" ": "x"}}, "`replace` maps"),
        ({"rule": "RS-WRITE-008", "type": "forbid", "pattern": ";", 3: "x"}, "takes no 3"),
        ({"rule": "RS-WRITE-017", "type": "nesting"}, "`max` is a whole number"),
        ({"rule": "RS-WRITE-017", "type": "nesting", "max": 3, "in": "list"}, "takes no in"),
        (
            {"rule": "RS-WRITE-017", "type": "nesting", "max": 3, "except": ["code"]},
            "takes no `except`",
        ),
        ({"rule": "RS-WRITE-018", "type": "forbid", "pattern": "x", "in": "code"}, "`in` is"),
        (
            {"rule": "RS-WRITE-018", "type": "forbid", "pattern": "x", "in": "file", "except": []},
            None,
        ),
        (
            {
                "rule": "RS-WRITE-018",
                "type": "forbid",
                "pattern": "x",
                "in": "file",
                "except": ["quotes"],
            },
            "takes no `except`",
        ),
    ],
)
def test_a_malformed_entry_is_refused(data: Mapping[str, Any], says: str | None) -> None:
    """`None`: the entry is well formed, as an empty `except` is."""
    if says is None:
        pl.entry(data)
        return
    with pytest.raises(pl.LintError, match=says):
        pl.entry(data)


# --- the reading, as RS-WRITE-005's How reads it -----------------------------------------


def test_a_word_holds_a_letter_or_a_digit_once_bold_marks_and_backticks_are_removed() -> None:
    """An id, a file name, a hyphenated word and a code span's token are each one word. A
    dash and a lone mark are none, and words in parentheses count."""
    assert counted("**Bold** `CLAUDE.md` and COR-050 — a well-known (aside 3) | + x.\n") == [9]


def test_a_code_span_is_at_most_one_word() -> None:
    """One word where it holds a letter or a digit, and none otherwise. Its spaces split
    no token, so the text joined to it up to a space is part of its word. An entry that
    leaves code out reads its spaces as spaces."""
    assert counted("Takes `--path <glob>` and `--record <id>` here.\n") == [5]
    assert counted("A `;` and a `--` and `` ` `` count none.\n") == [6]
    assert counted("The `pkit`'s own `a b`/`c d` words.\n") == [5]
    blank = pl.entry(
        {"rule": "RS-X-001", "type": "count", "count": "words", "in": "sentence", "max": 1}
    )
    assert found("foo`a b`baz", [dataclasses.replace(blank, exceptions=frozenset({"code"}))]) == [
        '1 RS-X-001: a sentence of 2 words, over 1: "fooa bbaz"'
    ]


def test_write_s_page_example_of_a_long_sentence_counts_30() -> None:
    """RS-WRITE-005's *Breaks the rule on a page*, the software-analysis README's sentence:
    two code spans of two tokens each are a word each."""
    sentence = (
        "Every artefact form also takes `--path <glob>` and `--record <id>`, each repeatable: "
        "the code that makes the artefact true and the decisions it relies on, written as its "
        "path and record anchors.\n"
    )
    assert counted(sentence) == [30]


@pytest.mark.parametrize(
    ("text", "levels"),
    [
        # A sibling closes the item before it, and a paragraph at the margin closes all.
        ("- a\n  - b\n- c\n\nText.\n\n  - d\n", [1, 2, 1, 0, 1]),
        # An item is inside another while it is indented to that item's text, not only
        # past its marker.
        ("1.  a\n    - b\n   - c\n", [1, 2, 1]),
        # A lazy line closes nothing, and a fence's lines close nothing.
        ("- a\n  - b\nlazy\n    - c\n", [1, 2, 3]),
        ("- a\n  ```\ncode\n  ```\n  - b\n", [1, 2]),
        # A paragraph indented to an item's text stays in it, at its level.
        ("- a\n\n  More of a.\n\n  - b\n", [1, 1, 2]),
        # A tab reaches the next multiple of four, after a marker too.
        ("- a\n\t- b\n\t\t- c\n", [1, 2, 3]),
        ("-\tfoo\n  - b\n", [1, 1]),
        # A marker with nothing after it starts its text one column on.
        ("-   \n  - b\n", [1, 2]),
        # A block quote counts afresh. The items it sits in stay open past it, and a
        # quote at the margin closes every item.
        ("- a\n  - b\n\n> - c\n>   - d\n", [1, 2, 1, 2]),
        ("- a\n  > note\n  - b\n    - c\n      - d\n", [1, 0, 2, 3, 4]),
        ("- a\n  - b\n> q\n- c\n", [1, 2, 0, 1]),
        # A number other than 1 opens no list inside a block's text, as in CommonMark.
        ("- a\n  - b ends in\n    2026. Then more.\n", [1, 2]),
        ("Text in\n2026. Then more.\n\n1. one\n2. two\n", [0, 1, 1]),
        # A heading, a table and a fence at the margin close every item.
        ("- a\n  - b\n# H\n- c\n", [1, 2, 1]),
        ("- a\n  - b\n| x |\n- c\n", [1, 2, 0, 1]),
    ],
)
def test_the_level_of_each_list_item(text: str, levels: list[int]) -> None:
    assert [block.level for block in pl.markdown_blocks(text)] == levels


@pytest.mark.parametrize(
    ("text", "sentences"),
    [
        ("One two. Three four? Five six! Seven.\n", [2, 2, 2, 1]),
        ("A lead-in: with a colon; and a semicolon ends none.\n", [10]),
        ("Ends at a line end.\nThen goes on\nacross a line.\n", [5, 6]),
        # The How read literally: a full stop before a space ends a sentence, after an
        # abbreviation or an initial too.
        ("Such as e.g. this, by A. Person.\n", [3, 3, 1]),
        # A full stop before a closing quotation mark or bracket ends nothing.
        ('He said "go." Then (it ended.) Then more.\n', [8]),
        # Bold marks are removed, so a full stop inside them ends a sentence.
        ("**Bold.** Then more.\n", [1, 2]),
        # A full stop inside a code span ends nothing, and the span is one word.
        ("Run `a. b` now. Then stop.\n", [3, 2]),
    ],
)
def test_where_a_sentence_ends(text: str, sentences: list[int]) -> None:
    assert counted(text) == sentences


def test_each_block_ends_a_sentence() -> None:
    """A list item, a nested item, a table cell and a paragraph each end one."""
    text = "Lead-in:\n\n- one item\n  wraps here\n  - nested\n\n| a cell | another |\n|---|---|\n"
    assert counted(text) == [1, 4, 1, 2, 1]


def test_headings_bold_labels_and_code_blocks_are_not_read() -> None:
    """A list item that is only a label is no sentence."""
    text = (
        "# A heading of several words\n\n"
        "- **Can be:**\n"
        "- **A label:** two words.\n"
        "- **A bold opening** is read.\n\n"
        "```\nnot read at all\n```\n\n"
        "<!-- nor a comment -->\n"
    )
    assert counted(text) == [2, 5]


def test_markup_and_markdown_that_holds_no_prose_are_not_read() -> None:
    """A fence closes only on a bare fence at least as long, a list item may open one, a
    setext heading's text is a heading, an inline comment is not read, and no pattern
    searches an entity or a URL."""
    text = (
        "````markdown\n```python\nx; y\n```\nstill code; here\n````\n\n"
        "- ```yaml\n  a: b; c\n  ```\n\n"
        "A setext heading; of words\n===\n\n"
        "Text <!-- a; b --> and&nbsp;more at https://example.org/a;b here.\n"
    )
    assert found(text) == []
    assert counted("Text <!-- a b --> and&nbsp;more at https://example.org/a;b here.\n") == [5]


def test_a_bare_url_ends_before_the_punctuation_after_it() -> None:
    """The sentence's own full stop or semicolon after a URL is prose, a URL is a word for a
    count, and an `&` that opens no entity is text."""
    fourteen = " ".join(["word"] * 14)
    assert counted(f"Read {fourteen} at https://example.org. {fourteen} here.\n") == [17, 15]
    assert counted(f"{' '.join(['word'] * 25)} https://example.org/a;b\n") == [26]
    assert found("See https://example.org; then go.\n\nWe fund R&D; and caf&eacute;s.\n") == [
        '1 RS-WRITE-008: a semicolon: "See https://example.org; then go."',
        '3 RS-WRITE-008: a semicolon: "We fund R&D; and caf&eacute;s."',
    ]


def test_a_block_quote_starts_a_block_and_its_fence_holds_code() -> None:
    """A quoted line after a paragraph starts a block of its own, and a fence inside a
    block quote holds code that is not read."""
    assert found(f"Plain; one.\n> Quoted; two.\n\n> ```\n> {LONG}\n> ```\n") == [
        '1 RS-WRITE-008: a semicolon: "Plain; one."'
    ]


def test_a_fence_remembers_whether_a_block_quote_opened_it() -> None:
    """A quoted fence line inside a fence is code, and the end of a block quote closes a
    fence opened in it."""
    inside = "```text\n> ```\n```\n\nAfter; this.\n"
    ended = "> ```\n> code; here\n\nAfter; this.\n"
    assert found(inside) == ['5 RS-WRITE-008: a semicolon: "After; this."']
    assert found(ended) == ['4 RS-WRITE-008: a semicolon: "After; this."']


def test_a_count_reads_a_url_as_a_word_through_its_entry() -> None:
    """25 words and a URL are 26 for RS-WRITE-005, and a quoted paragraph under an unquoted
    rule keeps its words."""
    twenty_five = " ".join(["word"] * 25)
    assert found(f"{twenty_five} https://example.org.\n") == [
        '1 RS-WRITE-005: a sentence of 26 words, over 25: "word word word word word word word '
        'word …"'
    ]
    assert counted("> One; two.\n---\n") == [2]


def test_only_a_link_definition_is_read_as_one() -> None:
    """A footnote, a label line with no quoted title and a list item are not definitions."""
    links = pl.entry({"rule": "RS-USER-001", "type": "link-resolves"})
    text = '[^1]: The note.\n\n[Optional]: the field is.\n\n- [x]: done\n\n[r]: gone.md "T"\n'
    assert found(text, [links], path="a.md", exists=lambda _rel: False) == [
        '7 RS-USER-001: the link target "gone.md" does not exist'
    ]


def test_a_block_quote_is_quoted() -> None:
    """Its words count, and a semicolon in it is quoted text, exempt from RS-WRITE-008."""
    text = f"> {LONG}\n> One; two.\n\nOne; two.\n"
    assert found(text) == [
        '1 RS-WRITE-005: a sentence of 27 words, over 25: "This sentence holds many words on '
        'purpose so …"',
        '4 RS-WRITE-008: a semicolon: "One; two."',
    ]


def test_a_literal_block_names_the_line_of_its_finding() -> None:
    """A literal block's lines keep their file lines; a folded block opens on the line
    after its marker."""
    text = "---\nnotes: |\n  One line.\n  Two; lines.\nmore: >\n  A; folded\n  value.\n---\n"
    assert found(text) == [
        '4 RS-WRITE-008: a semicolon: "One line. Two; lines."',
        '6 RS-WRITE-008: a semicolon: "A; folded value."',
    ]


def test_the_quoted_example_of_a_broken_rule_is_not_read() -> None:
    """Under a "Breaks the rule" label, from the first quotation mark to the last; the
    words around the quote are read."""
    text = (
        f'- **Breaks the rule:** a sentence of 27 words, "{LONG}"\n'
        f'- **Breaks the rule on a page:** "a nested "quote" inside; {LONG}"\n'
        f'- **Keeps the rule:** "{LONG}"\n'
    )
    assert counted(text) == [5, 27]


#: RS-WRITE-005's own *Keeps the rule* example, as `WRITE` writes it.
KEEPS_THE_RULE = (
    '- **Keeps the rule:** "the backbone ships no workflow. It ships only checks made to run '
    "unattended, and one base a pipeline names for all of them (COR-054 point 3). The checks "
    'bind once the project makes them a required status (COR-050 point 12)." Unlike the plain '
    "rewrite, this keeps the two items in the sentence (RS-WRITE-003).\n"
)


def test_write_s_own_keeps_the_rule_example_counts_27_by_the_literal_how() -> None:
    """A full stop before a closing quotation mark ends nothing, so RS-WRITE-005's own
    *Keeps the rule* example runs on into the sentence after it. WRITE reaches no rule set,
    so nothing reports it."""
    assert counted(KEEPS_THE_RULE) == [5, 21, 27]


def test_front_matter_values_are_read_and_the_container_is_not() -> None:
    """Each string value, a list item or not, is a block; the `pkit` container's answers
    are never read as prose (RS-WRITE-013)."""
    text = (
        "---\n"
        "title: One; two\n"
        "needs:\n"
        f"  - {LONG}\n"
        "  - A short need.\n"
        "status: 3\n"
        "pkit:\n"
        f'  friction: {{unanchored-because: "{LONG} One; two."}}\n'
        "---\n\n"
        "Body.\n"
    )
    assert found(text) == [
        '2 RS-WRITE-008: a semicolon: "One; two"',
        '4 RS-WRITE-005: a sentence of 27 words, over 25: "This sentence holds many words on '
        'purpose so …"',
    ]


# --- the text a change adds -----------------------------------------------------------------


def _added(base: str | None, head: str) -> str:
    mask = pl.added_mask(base, head)
    return "".join(char if mask[i] else "." for i, char in enumerate(head))


def test_a_change_adds_the_tokens_the_diff_inserts_word_by_word() -> None:
    assert _added("One two three.\n", "One two and three.\n") == "........and........"
    assert _added("One two\nthree.", "One\ntwo three.") == ".............."  # rewrapped
    assert _added(None, "ab") == "ab"


# --- the change ------------------------------------------------------------------------------


#: The rules the project's own entries name, each declaring the lint in `write_set`.
LINTED = ("RS-WRITE-005", "RS-WRITE-008", "RS-WRITE-017", "RS-WRITE-018")


def write_set(*, checks: bool = True) -> str:
    """A rule set `WRITE` scoped to the guides, declaring the lint for each rule of
    `LINTED` when `checks`."""
    front: dict[str, Any] = {
        "rule-set": "WRITE",
        "version": "1.0.0",
        "scope": {"paths": [f"{GUIDES}/**"]},
        "rules": rules(*LINTED),
    }
    if checks:
        front["checks"] = {
            rule: [{"check": "prose-lint", "part": "The mechanical part."}] for rule in LINTED
        }
    return rule_set_text(front)


def page(body: str) -> str:
    return f"---\ntitle: A guide\n---\n\n# A guide\n\n{body}\n"


ACTORS = f"{GUIDES}/actors.md"


def actors(need: str = "A need.", section: str = "The first actor.") -> str:
    return (
        "---\n"
        "ACT-one:\n"
        "  name: One\n"
        "  needs:\n"
        f"    - {need}\n"
        "  pkit:\n"
        f'    friction: {{unanchored-because: "{LONG}"}}\n'
        "ACT-two:\n"
        "  name: Two\n"
        "  pkit:\n"
        "    friction: {unanchored-because: No code holds it.}\n"
        "---\n\n"
        "# Actors\n\n"
        f"## ACT-one — One\n\n{section}\n\n"
        "## ACT-two — Two\n\nThe second actor.\n"
    )


@pytest.fixture
def repo(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    return make_adopter_repo()


def start(repo: AdopterRepo, files: Mapping[str, str], *, checks: bool = True) -> None:
    """The base on `main`, holding `files`, then branch `feature`."""
    repo.write({CONFIG: friction_config(places=(GUIDES,)), SET: write_set(checks=checks)})
    repo.write(files)
    repo.commit("base", files=None)
    repo.checkout("feature", create=True)


def lint(repo: AdopterRepo) -> list[str]:
    """`<location>:<line> <rule>` for each finding of the change against `main`."""
    return [f"{f.location}:{f.line} {f.rule}" for f in pl.lint_change(repo.root, "main").findings]


def test_it_reports_a_long_sentence_and_a_semicolon_the_change_adds(repo: AdopterRepo) -> None:
    start(repo, {A: page("Short.")})
    repo.write({A: page(f"Short. {LONG}\n\nOne; two.")})
    result = pl.lint_change(repo.root, "main")
    assert [f.render() for f in result.findings] == [
        f'{A}:7  RS-WRITE-005: a sentence of 27 words, over 25: "This sentence holds many '
        'words on purpose so …"',
        f'{A}:9  RS-WRITE-008: a semicolon: "One; two."',
    ]
    assert result.base["ref"] == "main" and result.checked == (A,)
    assert pl.render(result).splitlines()[-1] == (
        "2 finding(s) in the text the change adds or moves, 1 artefact(s) checked."
    )


def test_it_leaves_alone_a_break_the_change_only_sits_beside(repo: AdopterRepo) -> None:
    """A word added after the long sentence, and a sentence beside the semicolon, leave
    both breaks the base's."""
    start(repo, {A: page(f"{LONG}\n\nOne; two.")})
    repo.write({A: page(f"{LONG} Then more.\n\nOne; two. Three.")})
    assert lint(repo) == []


def test_it_reports_a_counted_unit_that_holds_text_the_change_adds(repo: AdopterRepo) -> None:
    """A word added inside the long sentence makes it the change's. A semicolon is its own
    unit, so an edit beside one leaves it alone."""
    start(repo, {A: page(f"{LONG}\n\nOne; two.")})
    repo.write({A: page(f"{LONG.replace('many', 'very many')}\n\nOne; two and three.")})
    assert lint(repo) == [f"{A}:7 RS-WRITE-005"]


def test_text_moved_into_a_reached_artefact_is_the_change_s(repo: AdopterRepo) -> None:
    """Moved from another file, or past the paragraphs around it, the diff inserts it."""
    b = f"{GUIDES}/b.md"
    start(repo, {A: page(f"{LONG}\n\nFirst.\n\nSecond."), b: page("One; two.")})
    repo.write({A: page(f"First.\n\nSecond.\n\n{LONG}\n\nOne; two."), b: page("Gone.")})
    assert lint(repo) == [f"{A}:11 RS-WRITE-005", f"{A}:13 RS-WRITE-008"]


def test_a_moved_file_alters_nothing(repo: AdopterRepo) -> None:
    """`pkit rule-sets altered` follows a move that keeps the content."""
    start(repo, {A: page(LONG)})
    repo.rename(A, f"{GUIDES}/moved.md")
    result = pl.lint_change(repo.root, "main")
    assert result.findings == () and result.checked == ()


#: A list three levels deep, and an item at level four under it.
THREE = "- one\n  - two\n    - three\n"
FOUR = "      - four\n"


def test_text_added_to_a_later_block_of_an_item_makes_it_the_change_s(
    repo: AdopterRepo,
) -> None:
    """The finding names the item's marker, not the block the text went to."""
    start(repo, {A: page(f"{THREE}{FOUR}")})
    repo.write({A: page(f"{THREE}{FOUR}\n        More of four, added.")})
    assert lint(repo) == [f"{A}:10 RS-WRITE-017"]


def test_an_item_is_the_change_s_when_it_holds_added_text_or_its_line_changed(
    repo: AdopterRepo,
) -> None:
    """An item indented to level four, its words unchanged, and an item whose words
    change are the change's. A level-four item the change only sits beside is not."""
    start(repo, {A: page(f"{THREE}    - three b\n\nGap.\n\n{THREE}{FOUR}")})
    repo.write({A: page(f"{THREE}      - three b\n\nGap.\n\n{THREE}{FOUR}\nThen more.")})
    assert lint(repo) == [f"{A}:10 RS-WRITE-017"]
    repo.write({A: page(f"{THREE}    - three b\n\nGap.\n\n{THREE}      - four words\n")})
    assert lint(repo) == [f"{A}:17 RS-WRITE-017"]


def test_a_control_character_the_change_adds_anywhere_is_the_change_s(
    repo: AdopterRepo,
) -> None:
    """In a code block, in the front matter and between two words; one the base held
    stays the base's, and a whitespace-like control is added like any character."""
    esc, rlo, lrm, form_feed = chr(0x1B), chr(0x202E), chr(0x200E), chr(0x0C)
    base = f"---\ntitle: A guide{lrm}\n---\n\nKept{esc} here.\n"
    start(repo, {A: base})
    head = (
        f"---\ntitle: A guide{lrm}\nnote: new{rlo}\n---\n\nKept{esc} here.\n\n"
        f"```\ncode{esc}\n```\n\nOne {form_feed} two.\n"
    )
    repo.write({A: head})
    assert lint(repo) == [f"{A}:3 RS-WRITE-018", f"{A}:9 RS-WRITE-018", f"{A}:12 RS-WRITE-018"]


def test_an_entry_s_whole_text_is_its_data_and_its_section(repo: AdopterRepo) -> None:
    """The lines of its data in the front matter, not the next entry's, and its
    section; each finding names the entry."""
    rlo = chr(0x202E)
    start(repo, {ACTORS: actors()})
    repo.write({ACTORS: actors(need=f"A need{rlo}.", section=f"The first{rlo} actor.")})
    assert lint(repo) == [f"{ACTORS}#ACT-one:5 RS-WRITE-018", f"{ACTORS}#ACT-one:18 RS-WRITE-018"]


def test_an_entry_s_whole_text_stops_before_a_comment_and_the_next_entry(
    repo: AdopterRepo,
) -> None:
    """A comment between two entries belongs to neither, and a character in the next
    entry's data is that entry's alone."""
    rlo = chr(0x202E)
    start(repo, {ACTORS: actors()})
    head = actors().replace(
        "ACT-two:\n  name: Two\n", f"# A note{rlo} between them\nACT-two:\n  name: Two{rlo}\n"
    )
    repo.write({ACTORS: head})
    assert lint(repo) == [f"{ACTORS}#ACT-two:10 RS-WRITE-018"]


def test_only_a_rule_declaring_the_lint_brings_its_entries(repo: AdopterRepo) -> None:
    """The rules bind, but their set declares no part checked by the lint."""
    start(repo, {A: page("Short.")}, checks=False)
    repo.write({A: page(f"{LONG}\n\nOne; two.")})
    assert lint(repo) == []


def test_an_artefact_no_rule_reaches_is_not_checked(repo: AdopterRepo) -> None:
    start(repo, {A: page("Short.")})
    repo.write({"docs/elsewhere.md": page(f"{LONG}\n\nOne; two.")})
    assert lint(repo) == []


def test_an_entry_is_read_in_its_values_and_its_section(repo: AdopterRepo) -> None:
    """Its values from its file's front matter, which the span does not hold; its container
    is never read."""
    start(repo, {ACTORS: actors()})
    repo.write({ACTORS: actors(need="A need; and more.", section=f"The first actor. {LONG}")})
    assert lint(repo) == [
        f"{ACTORS}#ACT-one:5 RS-WRITE-008",
        f"{ACTORS}#ACT-one:18 RS-WRITE-005",
    ]
    (finding, _) = pl.lint_change(repo.root, "main").findings
    assert finding.render().startswith(f"{ACTORS}:5  RS-WRITE-008 in ACT-one: a semicolon")


def test_the_command_exits_on_what_it_finds(
    repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """0 when nothing is found, 1 on a finding, 2 when the base cannot be compared."""
    monkeypatch.setattr(pl, "ROOT", repo.root)
    start(repo, {A: page("Short.")})
    assert pl.main(["--base", "main"]) == 0
    repo.write({A: page(LONG)})
    assert pl.main(["--base", "main"]) == 1
    assert f"{A}:7  RS-WRITE-005" in capsys.readouterr().out
    assert pl.main(["--base", "no-such-ref"]) == 2
    assert "prose lint:" in capsys.readouterr().err


# --- the data file and WRITE agree ------------------------------------------------------


def test_every_entry_names_a_rule_whose_set_declares_the_lint_and_back() -> None:
    """An entry whose rule declares no part would never apply, and a declared part with no
    entry would go unchecked."""
    _discovery, sets, _answer = rs.reach_at(REPO)
    declared = {rule.id for rule in sets.rules for part in rule.checks if part.check == pl.CHECK}
    assert declared
    assert {e.rule for e in pl.load_entries()} == declared
