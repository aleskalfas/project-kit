"""The prose lint, `scripts/prose_lint.py` (#1415).

- **Each type is an entry:** a test covers each of the four types with an
  entry and no code of its own: `count`, `forbid`, `substitute`, `link-resolves`.
- **The reading:** words and sentences as RS-WRITE-005's *How* reads them, each
  choice where the *How* is silent pinned here.
- **The change:** the lint reports a break in the text a change adds or moves,
  in an artefact a rule declaring the lint reaches. It leaves alone a break the
  change only sits beside. It reads reach and base from `pkit rule-sets altered`.
- **The data file and `WRITE` agree:** every entry names a rule whose set
  declares the lint, and every declaration has an entry.

The change tests run on the shared adopter-repository fixture. A rule set named
`WRITE`, scoped to `docs/guides/`, declares the lint for RS-WRITE-005 and
RS-WRITE-008, so the project's own entries apply there.
"""

from __future__ import annotations

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


def test_the_data_file_holds_the_first_entries() -> None:
    entries = pl.load_entries()
    assert [(e.rule, e.type) for e in entries] == [
        ("RS-WRITE-005", "count"),
        ("RS-WRITE-008", "forbid"),
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
    ],
)
def test_a_malformed_entry_is_refused(data: Mapping[str, Any], says: str) -> None:
    with pytest.raises(pl.LintError, match=says):
        pl.entry(data)


# --- the reading, as RS-WRITE-005's How reads it -----------------------------------------


def test_a_word_holds_a_letter_or_a_digit_once_bold_marks_and_backticks_are_removed() -> None:
    """An id, a file name, a hyphenated word and a code span's token are each one word. A
    dash and a lone mark are none, and words in parentheses count."""
    assert counted("**Bold** `CLAUDE.md` and COR-050 — a well-known (aside 3) | + x.\n") == [9]


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
        # A full stop inside a code span ends nothing.
        ("Run `a. b` now. Then stop.\n", [4, 2]),
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
    setext heading's text is a heading, and an inline comment, an entity and a URL are
    no prose."""
    text = (
        "````markdown\n```python\nx; y\n```\nstill code; here\n````\n\n"
        "- ```yaml\n  a: b; c\n  ```\n\n"
        "A setext heading; of words\n===\n\n"
        "Text <!-- a; b --> and&nbsp;more at https://example.org/a;b here.\n"
    )
    assert found(text) == []
    assert counted("Text <!-- a b --> and&nbsp;more at https://example.org/a;b here.\n") == [5]


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


#: RS-WRITE-005's own *Keeps the rule* example, as `WRITE` 1.1.0 writes it.
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


def write_set(*, checks: bool = True) -> str:
    """A rule set `WRITE` scoped to the guides, declaring the lint for RS-WRITE-005 and
    RS-WRITE-008 when `checks`."""
    front: dict[str, Any] = {
        "rule-set": "WRITE",
        "version": "1.0.0",
        "scope": {"paths": [f"{GUIDES}/**"]},
        "rules": rules("RS-WRITE-005", "RS-WRITE-008"),
    }
    if checks:
        front["checks"] = {
            rule: [{"check": "prose-lint", "part": "The mechanical part."}]
            for rule in ("RS-WRITE-005", "RS-WRITE-008")
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
