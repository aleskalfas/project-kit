"""software-analysis: the forms a kind's structure gives a part or a field (#1365).

`pkit analysis validate` holds each part and front-matter field to the form its
kind's structure names in `schemas/artefact-kinds.yaml` (software-analysis
DEC-001 point 1, RS-SAN-001), at the format rule's status, as the parts are:

- **a part's list is read as CommonMark reads one**, so a wrapped line stays in its
  item, an item may not interrupt a paragraph unless it is a bullet or `1.`, and
  fenced code opens no item;
- **a list form judges only the part's list items**, so a line a writer adds outside
  them passes;
- **`numbered-steps`**, **`variants`**, **`steps-match-front-matter`**,
  **`outcomes-match-front-matter`**, **`gaps-match-outcomes`** and **`definition`**,
  each passing and failing;
- **a withdrawn artefact** is never failed for a form, and a placeholder still in a
  field is the placeholder check's;
- **while the rule is proposed** the normal check reports none of it, and
  `--preview` lists each breach.

The reader and the forms are tested on their own first, then through the check's
structure step, then end to end in an adopter.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import (
    ANALYSIS_SET,
    ANALYSIS_SET_TEXT,
    GLOSSARY,
    USE_CASES,
    VALIDATE,
    actor_at,
    installed,
    load_lib,
    proposing_san,
    run_script,
)

_CHECK, _MODEL, _STRUCTURE, _FORMS = load_lib("check", "model", "structure", "forms")
C: Any = _CHECK
M: Any = _MODEL
S: Any = _STRUCTURE
F: Any = _FORMS

KINDS: dict[str, Any] = S.read_kinds()

USE_CASE = """\
# UC-007 — Export the report as a file

**Goal:** Export my report as a file.

**Other actors:** None.

**Preconditions:** The analyst is signed in.

**Assumptions:** None.

**Trigger:** The analyst asks to export the report on screen.

**Main path:**

1. The analyst chooses `Export`.
2. The system writes the report to a file.

**Variants:**

- **2a.** The disk is full. The system says so and writes nothing.

**Postconditions:** The file holds the whole report.

**Minimal guarantees:** None."""

#: The lines of USE_CASE's *Main path* and *Variants*, as a test replaces them.
MAIN_PATH = "1. The analyst chooses `Export`.\n2. The system writes the report to a file."
VARIANT = "- **2a.** The disk is full. The system says so and writes nothing."

JOURNEY = """\
# JRN-003 — Build and export the first report

**Goal:** Build my first report and export it as a file.

**Steps:**

1. UC-005 — Build the report
2. UC-007 — Export the report as a file
   - **Needs from step 1 (UC-005):** the report the analyst saved. An unsaved one is not offered.
   - **Needs from UC-009 (outside this journey):** the template an administrator published.

**Variants:**

- **2a.** The analyst wants a second report, and the path rejoins at step 1.

**Postconditions:** The analyst holds a file with their first report.

**Minimal guarantees:** None."""

JOURNEY_FIELDS = {"steps": ["UC-005", "UC-007"], "relies-on": ["UC-009"]}
TITLES = {"UC-005": "Build the report", "UC-007": "Export the report as a file"}
NEED_1 = (
    "   - **Needs from step 1 (UC-005):** the report the analyst saved. "
    "An unsaved one is not offered."
)
NEED_OUT = (
    "   - **Needs from UC-009 (outside this journey):** the template an administrator published."
)

RECORD = """\
# 2026-01-05 — Export to a chosen folder

## Outcomes

- **UC-007 — gap-found.** The redesign lets the analyst choose the folder.
- **JRN-003 — holds.** The journey still ends with the export.

## Gaps

- **UC-007:** a read-only folder writes nothing. **Resolution:** variant 2b written."""

OUTCOMES = {"outcomes": {"UC-007": "gap-found", "JRN-003": "holds"}}
GAP = "- **UC-007:** a read-only folder writes nothing. **Resolution:** variant 2b written."


def _lines(body: str) -> list[tuple[int, str]]:
    return [(i + 1, line) for i, line in enumerate(body.split("\n"))]


def _departures(body: str, kind: str, **context: Any) -> list[Any]:
    return S.departures(_lines(body), KINDS[kind], **context)


def _found(body: str, kind: str = "use-case", **context: Any) -> list[tuple[str, str, int | None]]:
    return [(d.element.id, d.how, d.line) for d in _departures(body, kind, **context)]


def _details(body: str, kind: str = "use-case", **context: Any) -> list[str]:
    return [d.detail for d in _departures(body, kind, **context)]


def _journey(body: str = JOURNEY, **fields: Any) -> list[tuple[str, str, int | None]]:
    return _found(body, "journey", fields={**JOURNEY_FIELDS, **fields}, titles=TITLES)


def _record(body: str = RECORD, **outcomes: str) -> list[tuple[str, str, int | None]]:
    fields = {"outcomes": outcomes} if outcomes else OUTCOMES
    return _found(body, "revalidation-record", fields=fields)


def _items(text: str, *, after_paragraph: bool = False) -> list[tuple[int, int | None, str]]:
    """Each top-level item of `text` read as a list: its line, its marker's number, and
    its text with white space runs as one space. Fenced code is marked as the body
    reader marks it."""
    body = S._read(_lines(text), frozenset())
    rows = [
        F.Row(n, line, fence)
        for n, line, fence in zip(body.numbers, body.content, body.fences, strict=True)
    ]
    listed = F.read_list(rows, after_paragraph=after_paragraph)
    return [(item.line, item.number, " ".join(item.text.split())) for item in listed.items]


WRAPPED = "Export it by the end of 2026. Then share it."


# --- reading a part's list ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "items"),
    [
        # A wrapped line indented under its item's text stays in it, `2026.` and all.
        ("- Export it by the end of\n  2026. Then share it.", [(1, None, WRAPPED)]),
        # Not indented, a line that opens with a number opens an item, as a reader sees it.
        (
            "- Export it by the end of\n2026. Then share it.",
            [(1, None, "Export it by the end of"), (2, 2026, "Then share it.")],
        ),
        # A line right below an item's text continues it, and after a blank line ends the list.
        ("- Export it\nas a file.", [(1, None, "Export it as a file.")]),
        ("- Export it\n\nas a file.", [(1, None, "Export it")]),
        # Indented past a blank line, a second paragraph stays in the item.
        (
            "1. Export it.\n\n   Then share it.\n2. Keep it.",
            [(1, 1, "Export it. Then share it."), (4, 2, "Keep it.")],
        ),
        # Numbers need not run in sequence, and `1)` is a marker too.
        ("1) a\n3) b\n2) c", [(1, 1, "a"), (2, 3, "b"), (3, 2, "c")]),
        # No line inside fenced code opens an item.
        ("- a\n```\n- not an item\n```\n- b", [(1, None, "a"), (5, None, "b")]),
        # A thematic break is no item, and an item opened empty ends at a blank line.
        ("- - -\n- a", [(2, None, "a")]),
        ("-\n\n  a", [(1, None, "")]),
        # Five spaces after a marker make the rest code, which no later line continues.
        ("-      code\nx", [(1, None, "code")]),
    ],
)
def test_a_part_s_list_is_read_as_commonmark_reads_one(
    text: str, items: list[tuple[int, int | None, str]]
) -> None:
    assert _items(text) == items


def test_fenced_code_goes_with_its_opening_line_as_the_body_reader_reads_it() -> None:
    """The body reader hides every line of fenced code from the marks, to its closing
    line, so the list reader keeps the fence whole with the item it opens in. CommonMark
    would end the item at a less indented line inside the fence."""
    text = "- a\n  ```\n- in the fence\n  ```\n- b"
    assert _items(text) == [(1, None, "a ``` - in the fence ```"), (5, None, "b")]


def test_below_a_label_an_item_interrupts_its_line_only_as_a_bullet_or_1() -> None:
    """A label's line is paragraph text, so a list right below it opens with a bullet or
    `1.`; a line that opens `2.` continues the label's paragraph."""
    assert _items("2. a\n3. b", after_paragraph=True) == []
    assert _items("1. a\n2. b", after_paragraph=True) == [(1, 1, "a"), (2, 2, "b")]
    assert _items("- a", after_paragraph=True) == [(1, None, "a")]
    assert _items("\n2. a", after_paragraph=True) == [(2, 2, "a")]


def test_under_a_label_that_opens_a_list_item_the_nested_list_is_the_part_s() -> None:
    labelled = "**Main path:**\n\n" + MAIN_PATH
    assert _found(USE_CASE.replace(labelled, "- **Main path:**\n  1. a\n  2. b\n")) == []
    repeated = USE_CASE.replace(labelled, "- **Main path:**\n  1. a\n  1. b\n  2. c")
    assert _found(repeated) == [("main-path", "breaks-its-form", 15)]


def test_a_writer_s_item_beside_a_label_s_item_is_no_item_of_its_list() -> None:
    """A `- **Note:**` at the label's own indentation is the outer list's next item, as
    Markdown reads it, so no list form judges it."""
    labelled = "**Main path:**\n\n" + MAIN_PATH
    noted = "- **Main path:**\n  1. a\n  2. b\n- **Note:** export is rare."
    assert _found(USE_CASE.replace(labelled, noted)) == []
    variants = "- **Variants:**\n  - **2a.** The disk is full.\n- **Why:** disks fill up."
    assert _found(USE_CASE.replace("**Variants:**\n\n" + VARIANT, variants)) == []
    # The `sentence` form refuses such an item: a list the part holds (#1370).
    goal = "**Goal:** Export my report as a file."
    beside = "- **Goal:** Export my report as a file.\n- **Note:** asked by sales."
    assert _found(USE_CASE.replace(goal, beside)) == [("goal", "breaks-its-form", 4)]


def test_a_part_with_no_list_is_told_where_its_list_must_stand() -> None:
    """A list beside the label's own list item is no part of it, as Markdown reads it, so
    the message says to indent the list under that item. A list that opens `2.` right
    below a paragraph continues it, so the message says how to start one. `None.` with
    more after it reads more than `None.`."""
    labelled = "**Main path:**\n\n" + MAIN_PATH
    beside = USE_CASE.replace(labelled, "- **Main path:**\n\n" + MAIN_PATH)
    (detail,) = _details(beside)
    assert detail.startswith("it holds no numbered step")
    assert "indent the list under the label's own list item" in detail
    under = USE_CASE.replace(labelled, "- **Main path:**\n  2. a\n  3. b")
    (detail,) = _details(under)
    assert detail.endswith(
        "start the list with `1.` or a bullet, or after a blank line, since a line that "
        "opens `2.` right below a paragraph continues it"
    )
    noted = USE_CASE.replace(
        "**Variants:**\n\n" + VARIANT, "- **Variants:** None.\n- **Note:** none yet."
    )
    (detail,) = _details(noted)
    assert detail.startswith("it holds no variant, and reads more than `None.`, which stands")
    prose = USE_CASE.replace(VARIANT, "The disk may be full.")
    (detail,) = _details(prose)
    assert detail.startswith("it holds no variant, and does not read `None.`: write each")
    gaps = RECORD.replace(GAP, "None.\n\nNo gap this time.")
    (detail,) = _details(gaps, "revalidation-record", fields=OUTCOMES)
    assert detail.startswith("it holds no gap, and reads more than `None.`")


def test_a_line_a_quote_in_an_item_runs_on_to_stays_its_text() -> None:
    (item,) = F.read_list([F.Row(1, "  1) "), F.Row(2, "     > q"), F.Row(3, "    2026. y")]).items
    assert " ".join(item.text.split()) == "> q 2026. y"
    assert F.nested(item).items == ()


# --- numbered-steps -------------------------------------------------------------------------


def test_numbered_steps_each_open_with_a_number_and_none_repeats() -> None:
    assert _found(USE_CASE) == []
    # Steps are append-only, so the numbers need not run in sequence (DEC-001 point 3).
    assert _found(USE_CASE.replace(MAIN_PATH, "1. a\n3. b\n2. c")) == []
    # A step may carry its number in its text, plain or bold, as a variant does.
    assert _found(USE_CASE.replace(MAIN_PATH, "- **1.** a\n- 2. b")) == []
    repeated = USE_CASE.replace(MAIN_PATH, "1. a\n2. b\n2. c")
    assert _found(repeated) == [("main-path", "breaks-its-form", 17)]
    assert _details(repeated) == ["step 2 is numbered twice, at lines 16 and 17: no number repeats"]
    unnumbered = USE_CASE.replace(MAIN_PATH, "1. a\n2. b\n- c")
    assert _details(unnumbered) == ["the item opens with no step's number, such as `2.`"]


def test_numbered_steps_written_inline_hold_no_step() -> None:
    """Steps on the label's line are one paragraph, not a list, so the part holds none,
    and no variant is held to steps the part does not number."""
    inline = USE_CASE.replace("**Main path:**\n\n" + MAIN_PATH, "**Main path:** 1. a. 2. b.")
    assert _found(inline) == [("main-path", "breaks-its-form", 13)]
    assert _details(inline)[0].startswith("it holds no numbered step")


def test_a_list_form_judges_only_the_part_s_items() -> None:
    """A lead line, a note after the list and a writer's own label pass."""
    noted = USE_CASE.replace(
        "**Main path:**\n\n" + MAIN_PATH,
        "**Main path:** from the report on screen.\n\n" + MAIN_PATH + "\n\n**Note:** never sent.",
    ).replace(VARIANT, "Each is rare.\n\n" + VARIANT + "\n\nSee step 2.")
    assert _found(noted) == []


# --- variants -------------------------------------------------------------------------------


def test_variants_open_with_a_step_of_the_main_path_and_a_letter() -> None:
    assert _found(USE_CASE.replace(VARIANT, "None.")) == []
    plain = USE_CASE.replace(VARIANT, "- 1a. The analyst cancels.\n- 2b. The disk is gone.")
    assert _found(plain) == []
    beyond = USE_CASE.replace(VARIANT, "- **3a.** Nothing.")
    assert _found(beyond) == [("variants", "breaks-its-form", 20)]
    assert _details(beyond) == [
        "variant 3a branches from step 3, which `**Main path:**` does not hold"
    ]
    unlettered = USE_CASE.replace(VARIANT, "- The disk is full.")
    assert _details(unlettered) == [
        "the item opens with no step's number and letter, such as `2a.`"
    ]
    prose = USE_CASE.replace(VARIANT, "The disk may be full.")
    assert _found(prose) == [("variants", "breaks-its-form", 18)]


def test_a_journey_s_variants_are_read_against_its_steps() -> None:
    assert _journey() == []
    beyond = JOURNEY.replace("**2a.**", "**3a.**")
    assert _journey(beyond) == [("variants", "breaks-its-form", 14)]
    assert (
        "which `**Steps:**` does not hold"
        in _details(beyond, "journey", fields=JOURNEY_FIELDS, titles=TITLES)[0]
    )


# --- steps-match-front-matter ---------------------------------------------------------------


def test_a_journey_s_step_lines_match_its_steps_and_their_titles() -> None:
    assert _journey(JOURNEY.replace("Build the report", "Build my report", 1)) == [
        ("steps", "breaks-its-form", 7)
    ]
    swapped = JOURNEY.replace("1. UC-005", "2. UC-005", 1)
    assert _journey(swapped) == [("steps", "breaks-its-form", 7)]
    short = JOURNEY.replace("\n" + NEED_1, "").replace("\n" + NEED_OUT, "")
    assert _journey(short, steps=["UC-005", "UC-007", "UC-005"], **{"relies-on": []}) == [
        ("steps", "breaks-its-form", 5)
    ]
    assert _details(
        short, "journey", fields={"steps": ["UC-005", "UC-007", "UC-005"]}, titles=TITLES
    ) == [
        "it holds 2 step(s), and `steps` lists 3: step 3, `3. UC-005 — Build the report`, "
        "has no line"
    ]
    extra = JOURNEY.replace(NEED_OUT, NEED_OUT + "\n3. UC-005 — Build the report")
    assert _journey(extra) == [("steps", "breaks-its-form", 11)]
    # A use case the analysis does not hold has no title to match: its id and text do.
    assert _found(JOURNEY, "journey", fields=JOURNEY_FIELDS, titles={}) == []
    # A lead line, outside the list, passes.
    led = JOURNEY.replace("**Steps:**\n", "**Steps:** the first day.\n")
    assert _journey(led) == []


def test_a_hand_over_names_an_earlier_step_or_a_use_case_the_journey_relies_on() -> None:
    def details(body: str, **fields: Any) -> list[str]:
        merged = {**JOURNEY_FIELDS, **fields}
        return _details(body, "journey", fields=merged, titles=TITLES)

    later = JOURNEY.replace("step 1 (UC-005)", "step 2 (UC-007)")
    assert details(later) == [
        "a hand-over under step 2 needs from step 2, which is no earlier step of the journey"
    ]
    other = JOURNEY.replace("step 1 (UC-005)", "step 1 (UC-007)")
    assert details(other) == [
        "a hand-over under step 2 names step 1 as UC-007, where step 1 is UC-005"
    ]
    assert details(JOURNEY, **{"relies-on": []}) == [
        "a hand-over under step 2 names UC-009 outside this journey, and `relies-on` does "
        "not list it"
    ]
    step = JOURNEY.replace("UC-009 (outside", "UC-005 (outside")
    assert details(step, **{"relies-on": ["UC-005"]})[0].startswith(
        "a hand-over under step 2 names UC-005 outside this journey, though it is a step"
    )
    unnamed = JOURNEY.replace("\n" + NEED_OUT, "")
    assert details(unnamed) == [
        "`relies-on` lists UC-009, and no hand-over names it: write `**Needs from UC-009 "
        "(outside this journey):**` under the step that needs it"
    ]
    malformed = JOURNEY.replace("step 1 (UC-005)", "UC-005")
    assert details(malformed)[0].startswith(
        "a hand-over under step 2 opens `**Needs from UC-005:**"
    )
    silent = JOURNEY.replace(
        "the template an administrator published.", "<!-- what it receives -->"
    )
    assert details(silent) == [
        "a hand-over under step 2 says nothing after its label: say what it receives, and "
        "how that can break"
    ]


def test_a_hand_over_written_below_its_step_line_without_a_bullet_counts() -> None:
    """The step's line ends where a hand-over opens a line, bullet or not."""
    bare = JOURNEY.replace("   - **Needs from step 1", "   **Needs from step 1")
    assert _journey(bare) == []


def test_a_step_s_line_runs_on_over_a_wrapped_line_that_opens_no_item() -> None:
    """A wrapped line that starts `*final*` or `-based` opens no item, so it is still the
    step's line, which matches the title it completes."""
    titles = {**TITLES, "UC-007": "Export the *final* report as a file"}
    wrapped = JOURNEY.replace(
        "2. UC-007 — Export the report as a file",
        "2. UC-007 — Export the\n   *final* report as a file",
    )
    assert _found(wrapped, "journey", fields=JOURNEY_FIELDS, titles=titles) == []


# --- outcomes-match-front-matter ------------------------------------------------------------


def test_a_record_s_outcomes_follow_its_front_matter_in_order() -> None:
    assert _record() == []
    swapped = RECORD.replace("UC-007 — gap-found", "UC-007 — holds", 1)
    assert _record(swapped) == [("outcomes", "breaks-its-form", 5)]
    assert _details(swapped, "revalidation-record", fields=OUTCOMES) == [
        "item 1 opens `**UC-007 — holds.** The redesign lets the analyst choose th…`, "
        "where the 1st entry of `outcomes` gives `**UC-007 — gap-found.**`: one item for "
        "each entry, in its order"
    ]
    missing = RECORD.replace("\n- **JRN-003 — holds.** The journey still ends with the export.", "")
    assert _record(missing) == [("outcomes", "breaks-its-form", 3)]
    extra = RECORD.replace("export.\n", "export.\n- **UC-001 — holds.** Still true.\n")
    assert _record(extra) == [("outcomes", "breaks-its-form", 7)]
    bare = RECORD.replace(" The redesign lets the analyst choose the folder.", "")
    assert _details(bare, "revalidation-record", fields=OUTCOMES) == [
        "item 1 gives no reason after `**UC-007 — gap-found.**`"
    ]
    noted = RECORD.replace("## Outcomes\n", "## Outcomes\n\nBoth were read on the redesign.\n")
    assert _record(noted) == []


# --- gaps-match-outcomes --------------------------------------------------------------------


def test_a_record_s_gaps_name_its_regressed_and_gap_found_outcomes() -> None:
    none = RECORD.replace(GAP, "None.")
    holding = none.replace("UC-007 — gap-found", "UC-007 — holds")
    assert _record(holding, **{"UC-007": "holds", "JRN-003": "holds"}) == []
    assert _record(none) == [("gaps", "breaks-its-form", 8)]
    assert _details(none, "revalidation-record", fields=OUTCOMES) == [
        "it reads `None.`, though UC-007's outcome is `gap-found`: each `code-regressed` or "
        "`gap-found` artefact is named by a gap"
    ]
    several = RECORD.replace("**UC-007:**", "**UC-007, JRN-003:**")
    assert _record(several) == []
    hollow = RECORD.replace("**UC-007:**", "**UC-007,:**")
    assert _details(hollow, "revalidation-record", fields=OUTCOMES) == [
        "the gap's label, `**UC-007,:**`, leaves an id out between its commas: name each "
        "id once, separated by commas"
    ]
    blank = RECORD.replace("**UC-007:**", "** :**")
    assert _details(blank, "revalidation-record", fields=OUTCOMES)[0] == (
        "the gap's label names no id: name each id"
    )
    unknown = RECORD.replace("**UC-007:**", "**UC-007, UC-001:**")
    assert _details(unknown, "revalidation-record", fields=OUTCOMES) == [
        "the gap names `UC-001`, which `outcomes` does not list: a gap names artefacts the "
        "record covers"
    ]
    unlabelled = RECORD.replace("**UC-007:** a", "A")
    assert _details(unlabelled, "revalidation-record", fields=OUTCOMES) == [
        "the gap opens with no bold label of the ids it affects, such as `**UC-007, JRN-001:**`",
        "UC-007's outcome is `gap-found`, and no gap names it",
    ]
    unresolved = RECORD.replace(" **Resolution:** variant 2b written.", " **Resolution:**")
    assert _record(unresolved) == [("gaps", "breaks-its-form", 10)]
    regressed = RECORD.replace("**UC-007:**", "**JRN-003:**").replace(
        "JRN-003 — holds", "JRN-003 — code-regressed"
    )
    assert _record(regressed, **{"UC-007": "gap-found", "JRN-003": "code-regressed"}) == [
        ("gaps", "breaks-its-form", 8)
    ]


# --- definition -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("definition", "name", "problems"),
    [
        (KINDS["term"].fields[1].example, "template", []),
        ("The layout an administrator publishes", "template", ["it opens with an article, `The`"]),
        ("a layout", "template", ["it opens with an article, `a`"]),
        ("layout an administrator publishes.", "template", ["it ends with a full stop"]),
        ("layout a Template holds", "template", ["it holds `Template`, a word of the term's name"]),
        (
            "queue of changes waiting to merge",
            "merge queue",
            ["it holds `queue`, `merge`, a word of the term's name"],
        ),
        # Only a whole word counts, and an article inside the phrase is fine.
        ("layout of the templates kind", "template", []),
    ],
)
def test_a_definition_is_a_phrase_that_never_repeats_the_term(
    definition: str, name: str, problems: list[str]
) -> None:
    assert F.definition_problems(definition, name) == problems


def test_the_definition_form_is_a_term_s_front_matter_field() -> None:
    fields = {"name": "template", "definition": "The template."}
    (departure,) = S.field_departures(fields, KINDS["term"])
    assert (departure.pointer, departure.how, departure.field.name) == (
        "/definition",
        "breaks-its-form",
        "definition",
    )
    assert departure.detail == (
        "it opens with an article, `The`, and it ends with a full stop, and it holds "
        "`template`, a word of the term's name"
    )


# --- through the check ----------------------------------------------------------------------


def _analysis(*artefacts: Any) -> Any:
    return M.Analysis(
        location="docs/analysis",
        places={},
        artefacts=tuple(artefacts),
        strays=(),
        unreadable={},
        files={a.path: a.kind for a in artefacts},
        records=(),
        method_rules={"RS-SAN-001": "accepted"},
    )


def _artefact(root: Path, rel: str, kind: str, text: str, **fields: Any) -> Any:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(text, encoding="utf-8")
    return M.Artefact(
        kind=kind,
        id=fields.get("id"),
        path=rel,
        location=rel,
        entry=False,
        fields=fields,
        anchors={},
        span_read=True,
    )


def _messages(root: Path, *artefacts: Any, records: list[Any] | None = None) -> list[str]:
    """What the check says of `artefacts`, the format rule accepted and binding on each, as
    through a set of the project's own that selects them all and inherits `SAN`, and of
    `records`, which the capability holds always."""
    bound = {a.location: {"software-analysis:RS-SAN-001": False} for a in artefacts}
    _summary, found = C._structure(
        root, _analysis(*artefacts), preview=False, reach=lambda _root, **_kw: bound
    )
    _said, held = C._record_structure(root, records or [])
    return [f.message for f in found + held]


UC_REL = "docs/analysis/use-case-model/use-cases/UC-007-export.md"
JRN_REL = "docs/analysis/use-case-model/journeys/JRN-003-first.md"


def test_a_breach_s_message_says_what_breaks_with_the_part_s_hint_and_example(
    tmp_path: Path,
) -> None:
    repeated = USE_CASE.replace(MAIN_PATH, "1. a\n2. b\n2. c")
    use_case = _artefact(tmp_path, UC_REL, "use-case", repeated, id="UC-007")
    (main_path,) = [e for e in KINDS["use-case"].sections if e.id == "main-path"]
    assert _messages(tmp_path, use_case) == [
        "`**Main path:**`, at line 17, does not hold its form, `numbered-steps`: step 2 is "
        "numbered twice, at lines 16 and 17: no number repeats (RS-SAN-001). What goes "
        f"there: {main_path.hint} Example: {main_path.example}"
    ]


def test_a_journey_s_steps_read_the_titles_its_use_cases_give(tmp_path: Path) -> None:
    build = _artefact(tmp_path, "uc5.md", "use-case", "", id="UC-005", title="Build the report")
    export = _artefact(tmp_path, "uc7.md", "use-case", "", id="UC-007", title="Export it")
    journey = _artefact(tmp_path, JRN_REL, "journey", JOURNEY, id="JRN-003", **JOURNEY_FIELDS)
    messages = [m for m in _messages(tmp_path, build, export, journey) if "`**Steps:**`" in m]
    assert len(messages) == 1
    assert (
        "step 2 reads `UC-007 — Export the report as a file`, where it is `UC-007 — "
        "Export it`" in messages[0]
    )


def test_a_record_s_forms_read_its_front_matter(tmp_path: Path) -> None:
    rel = "docs/analysis/revalidations/2026-01-05-folder.md"
    (tmp_path / rel).parent.mkdir(parents=True)
    (tmp_path / rel).write_text(RECORD.replace(GAP, "None."), encoding="utf-8")
    [message] = _messages(tmp_path, records=[(rel, OUTCOMES)])
    assert message.startswith("the section `## Gaps`, at line 8, does not hold its form")
    assert "(DEC-001 point 1)" in message  # no rule binds on a record, a held document


def test_a_withdrawn_artefact_is_never_failed_for_a_form(tmp_path: Path) -> None:
    """A form may have come after the artefact's withdrawal (DEC-001 point 1), in its body
    or in its front matter. What it carries is still held: an empty part is reported."""
    broken = USE_CASE.replace(MAIN_PATH, "1. a\n1. b").replace(VARIANT, "- Nothing.")
    use_case = _artefact(tmp_path, UC_REL, "use-case", broken, id="UC-007", status="withdrawn")
    assert _messages(tmp_path, use_case) == []
    actor_text = (
        "# ACT-tester — Tester\n\nWhoever tests.\n\n- **Occasions:** None.\n- **Context:** None."
    )
    needs = ["Run the suite. Then read it."]
    withdrawn = _artefact(
        tmp_path, "act.md", "actor", actor_text, id="ACT-tester", status="withdrawn", needs=needs
    )
    assert _messages(tmp_path, withdrawn) == []
    active = _artefact(tmp_path, "act.md", "actor", actor_text, id="ACT-tester", needs=needs)
    assert len(_messages(tmp_path, active)) == 1
    empty = USE_CASE.replace(
        "**Postconditions:** The file holds the whole report.", "**Postconditions:**"
    )
    use_case = _artefact(tmp_path, UC_REL, "use-case", empty, id="UC-007", status="withdrawn")
    [message] = _messages(tmp_path, use_case)
    assert message.startswith("`**Postconditions:**`, at line 22, is empty")


def test_a_placeholder_left_in_a_field_is_the_placeholder_check_s(tmp_path: Path) -> None:
    """The glossary template's definition repeats its `<Term>` name, and the placeholder
    check already reports it, so no form reports it too."""
    term = M.Artefact(
        kind="term",
        id="TERM-term",
        path="glossary.md",
        location="glossary.md#TERM-term",
        entry=True,
        fields={"name": "<Term>", "definition": "<what the term means, in one sentence>"},
        anchors={},
        span=None,
        span_read=True,
    )
    assert C._field_findings(term.location, term.fields, KINDS["term"], "a term") == []


# --- end to end, in an adopter ---------------------------------------------------------------


@pytest.fixture
def project(make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch)


def _said(repo: AdopterRepo, *args: str) -> tuple[int, list[tuple[str, str, str]]]:
    completed = run_script(repo, VALIDATE, "--json", *args)
    document = json.loads(completed.stdout)
    found = [(f["severity"], f["location"], f["message"]) for f in document["findings"]]
    return completed.returncode, found


def test_proposed_the_forms_report_nothing_and_the_preview_lists_each_breach(
    project: AdopterRepo, pkit_on_path: Path
) -> None:
    actor = (
        "---\nid: ACT-tester\nname: Tester\nstatus: active\nneeds:\n  - Run the suite.\n"
        "pkit:\n  friction:\n    unanchored-because: No code embodies it.\n---\n\n"
        "# ACT-tester — Tester\n\nWhoever tests.\n\n- **Occasions:** None.\n"
        "- **Context:** None.\n"
    )
    use_case = (
        "---\nid: UC-007\ntitle: Export the report as a file\nstatus: active\n"
        "actor: ACT-tester\npkit:\n  friction:\n    anchors:\n      artefact: [ACT-tester]\n"
        "---\n\n" + USE_CASE.replace(MAIN_PATH, "1. a\n2. b\n2. c") + "\n"
    )
    glossary = (
        "---\nTERM-template:\n  name: template\n  status: active\n"
        "  definition: The template.\n  pkit:\n    friction:\n"
        "      unanchored-because: No code embodies it.\n---\n\n"
        "# Glossary\n\nThe words of the domain.\n\n"
        "## TERM-template — template\n\n**Example:** None.\n\n**Distinctions:** None.\n"
    )
    uc_rel = f"{USE_CASES}/UC-007-export.md"
    project.write(
        {
            actor_at("ACT-tester"): actor,
            uc_rel: use_case,
            GLOSSARY: glossary,
            ANALYSIS_SET: ANALYSIS_SET_TEXT,
            # `SAN` ships its rules accepted: a proposed copy is this test's point.
            **proposing_san(project),
        }
    )
    code, found = _said(project)
    # No rule of `SAN` is accepted, so none binds, which the check reports (DEC-001 point 1).
    assert (code, [(s, m.split(":")[0]) for s, _l, m in found]) == (
        0,
        [("report", "no rule of software-analysis")],
    )
    code, found = _said(project, "--preview")
    assert code == 0
    # The report that no rule of `SAN` binds stands in the preview too; the rest is the
    # preview's.
    unbound = [f for f in found if f[2].startswith("no rule of software-analysis:SAN binds")]
    assert [severity for severity, _l, _m in unbound] == ["report"]
    found = [f for f in found if f not in unbound]
    assert sorted((severity, location) for severity, location, _m in found) == [
        ("report", f"{GLOSSARY}#TERM-template:/definition"),
        ("report", uc_rel),
    ]
    assert all(message.startswith("preview: ") for _s, _l, message in found)
