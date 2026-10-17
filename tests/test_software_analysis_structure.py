"""software-analysis: each analysis body against its kind's declared structure (#1364).

`pkit analysis validate` holds each body to the structure its kind declares in
`schemas/artefact-kinds.yaml`, at the status of the format rule, RS-SAN-001
(software-analysis DEC-001 point 1):

- it reports a declared part **missing, out of order or empty**, `None.` where the
  part may not read it, and text of the **`sentence` form** that is not one
  sentence, each message giving the part's **hint and example**;
- **only declared labels delimit**, and a part runs to the next declared label or
  to a heading of its level or above, so **a writer's labels and sections pass**;
- **a withdrawn artefact** is never failed for a part it lacks;
- **a collection entry** is read only within the span the artefacts document gives
  (#1361), and the collection file's head is read above the first entry;
- **while the rule is proposed** the normal check reports nothing of it, and
  **`--preview`** lists what would break at the severity `report`, labelled
  `preview`, leaving the exit status unchanged. `pkit validate` runs the normal
  check.

The reader and the gate are tested on their own first, then end to end in an
adopter, where the backbone's reading gives the rule's status and each entry's span.
"""

from __future__ import annotations

import dataclasses
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import (
    ANALYSIS,
    ANALYSIS_SET,
    ANALYSIS_SET_TEXT,
    GLOSSARY,
    NEW,
    RECORDS,
    SA,
    SAN_REL,
    VALIDATE,
    accepting_san,
    actor_at,
    field_hint,
    installed,
    load_lib,
    run_script,
    stamped,
)

_CHECK, _MODEL, _STRUCTURE, _FORMS = load_lib("check", "model", "structure", "forms")
C: Any = _CHECK
M: Any = _MODEL
S: Any = _STRUCTURE
F: Any = _FORMS

KINDS: dict[str, Any] = S.read_kinds()
RULE = "RS-SAN-001"

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

ACTOR_BODY = """\
# ACT-tester — Tester

Whoever writes and runs the project's tests.

- **Occasions:** with every change.
- **Context:** the suite, and a sandbox to run it in."""

RECORD_BODY = """\
# 2026-10-01 — Export to a chosen folder

## Outcomes

- **UC-001 — holds.** The export still writes the whole report.

## Gaps

None."""


def _lines(body: str, first: int = 1) -> list[tuple[int, str]]:
    return [(first + i, line) for i, line in enumerate(body.split("\n"))]


def _found(body: str, kind: str = "use-case", **options: Any) -> list[tuple[str, str, int | None]]:
    return [
        (d.element.id, d.how, d.line) for d in S.departures(_lines(body), KINDS[kind], **options)
    ]


# --- the reader: what departs -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "body"),
    [("use-case", USE_CASE), ("actor", ACTOR_BODY), ("revalidation-record", RECORD_BODY)],
)
def test_a_body_with_every_part_passes(kind: str, body: str) -> None:
    assert _found(body, kind) == []


def test_a_part_missing_out_of_order_or_empty_is_found() -> None:
    no_trigger = USE_CASE.replace(
        "**Trigger:** The analyst asks to export the report on screen.", ""
    )
    assert _found(no_trigger) == [("trigger", "missing", None)]
    guarantees = "**Minimal guarantees:** None."
    early = USE_CASE.replace(f"\n\n{guarantees}", "").replace(
        "**Other actors:**", f"{guarantees}\n\n**Other actors:**"
    )
    assert _found(early) == [("minimal-guarantees", "out-of-order", 5)]
    empty = USE_CASE.replace(
        "**Postconditions:** The file holds the whole report.", "**Postconditions:**"
    )
    assert _found(empty) == [("postconditions", "empty", 22)]


def test_none_passes_only_where_the_part_allows_it() -> None:
    """*Assumptions* may read `None.`, and *Trigger* may not: a use case always has an
    event that starts it (the round's rule for every kind)."""
    trigger = USE_CASE.replace("The analyst asks to export the report on screen.", "None.")
    assert _found(trigger) == [("trigger", "none-refused", 11)]
    assert _found(USE_CASE.replace("**Assumptions:** None.", "**Assumptions:**\n\nNone.\n")) == []


@pytest.mark.parametrize(
    ("text", "one"),
    [
        ("Export my report as a file.", True),
        ("Export my report as a file", True),
        ("Never export a draft!", True),
        ("Export `report.v2` as a file.", True),
        ("Export my report.\n", True),
        ("Export my report (as a file).", True),
        ("Export my report. Then share it.", False),
        ("Export my report. Then email it.", False),
        ("Why export? To share it.", False),
        ("Export my report.\nShare it.", False),
        # A mark followed by a lowercase letter ends no sentence (#1370).
        ("Export it, e.g. for the auditor.", True),
        ("Export it on 3. října.", True),
        ("Export it, e.g. Then share it.", False),
        # A capital after a mark ends one, an abbreviation's too: such a text is reworded.
        ("Dr. Smith exports it.", False),
        ("Export z. B. Rechnungen.", False),
        # Several spaces, or a no-break space, count as a space; a zero-width space as
        # nothing: no character a reader cannot see moves a sentence's end.
        ("Export my report.  Then email it.", False),
        ("Export my report.\u00a0Then email it.", False),
        ("Export my report.\u200b Then email it.", False),
        ("Export my report.\u200bThen email it.", True),
        ("Export my report. \ufe0fThen email it.", False),  # a variation selector
        ("Export my report.\u034f Then email it.", False),  # the grapheme joiner
        # Only a capital letter after the space ends one: a digit or a quote does not.
        ("Export my report. 2 files follow.", True),
        ('Export my report. "Then" email it.', True),
        # A script without capital letters is never split.
        ("レポートを書く。それを送る。", True),
        ("تصدير التقرير. ثم إرساله.", True),
        # A mark before a letter of such a script ends none; before a capital, one ends.
        ("导出报告. 文件", True),
        ("导出报告. Excel 文件", False),
        # A mark inside a code span ends none.
        ("Run `make. Then` now.", True),
    ],
)
def test_where_a_sentence_ends_is_rs_san_001_s_how(text: str, one: bool) -> None:
    assert F.one_sentence(text) is one


def test_a_part_of_the_sentence_form_holds_one_sentence() -> None:
    two = USE_CASE.replace("Export my report as a file.", "Export my report. Then share it.")
    assert _found(two) == [("goal", "not-a-sentence", 3)]
    needs = {"needs": ["Run the suite.", "Run the suite. Then read the report."], "name": "x"}
    (departure,) = S.field_departures(needs, KINDS["actor"])
    assert (departure.pointer, departure.how, departure.field.name) == (
        "/needs/1",
        "not-a-sentence",
        "needs",
    )


def test_a_sentence_part_is_one_text_and_holds_no_list() -> None:
    """A `sentence` part is one text, the whole of what it holds, and holds no list, not
    even inside a block quote, as RS-SAN-001's *How* says (#1370). The list breaks the
    form at its first item's line. A list's markers are no text, so a part with a list is
    not judged as a sentence too."""
    goal = "**Goal:** Export my report as a file."
    # A two-bullet goal: two needs written as one goal.
    listed = "**Goal:**\n\n- Export my report.\n- Email it."
    assert _found(USE_CASE.replace(goal, listed)) == [("goal", "breaks-its-form", 5)]
    (departure,) = S.departures(_lines(USE_CASE.replace(goal, listed)), KINDS["use-case"])
    assert departure.detail.startswith("it holds a list, where a part of this form is one")
    numbered = "**Goal:**\n\n1. Export my report.\n2. Email it."
    assert _found(USE_CASE.replace(goal, numbered)) == [("goal", "breaks-its-form", 5)]
    one = "**Goal:**\n\n- Export my report."
    assert _found(USE_CASE.replace(goal, one)) == [("goal", "breaks-its-form", 5)]
    lead = "**Goal:** Two things:\n\n- Export my report.\n- Share it."
    assert _found(USE_CASE.replace(goal, lead)) == [("goal", "breaks-its-form", 5)]
    nested = "- **Goal:**\n  - Export my report.\n    - As a file."
    assert _found(USE_CASE.replace(goal, nested)) == [("goal", "breaks-its-form", 4)]
    # The item the label opens is no list the part holds.
    labelled = "- **Goal:** Export my report as a file."
    assert _found(USE_CASE.replace(goal, labelled)) == []
    # Inside a block quote, a list is still one: refused, at its first item.
    quoted = "**Goal:**\n\n> - Export my report.\n> - Share it."
    assert _found(USE_CASE.replace(goal, quoted)) == [("goal", "breaks-its-form", 5)]
    deeper = "**Goal:**\n\n> Two of them:\n> > 1. Export my report."
    assert _found(USE_CASE.replace(goal, deeper)) == [("goal", "breaks-its-form", 6)]
    # A quote with no list, and fenced code that looks like a list, hold none.
    said = "**Goal:**\n\n> Export my report as a file."
    assert _found(USE_CASE.replace(goal, said)) == []
    fenced = "**Goal:** Export my report as a file.\n\n```\n> - not a list\n- nor this\n```"
    assert _found(USE_CASE.replace(goal, fenced)) == []
    # A mark inside a fenced block ends no sentence, whatever its fence.
    tilde = "**Goal:** Export my report as a file.\n\n~~~\nmake. Then\n~~~"
    assert _found(USE_CASE.replace(goal, tilde)) == []
    # Without a list the part is one text, and a wrapped `2026` continues it.
    paragraph = "**Goal:** Export my report by the end of\n2026 as a file."
    assert _found(USE_CASE.replace(goal, paragraph)) == []
    # A line right below the label that opens with `2.` continues the label's paragraph,
    # so it is no list; its capital after the full stop ends a sentence.
    continued = "**Goal:** Export my report.\n2. Then share it."
    assert _found(USE_CASE.replace(goal, continued)) == [("goal", "not-a-sentence", 3)]
    wrapped = "**Goal:** Export my report.\nThen email it."
    assert _found(USE_CASE.replace(goal, wrapped)) == [("goal", "not-a-sentence", 3)]


def test_a_front_matter_list_of_the_sentence_form_is_one_text_per_item() -> None:
    """An actor's `needs` stays a list, each item one text (#1370): a need of two
    sentences breaks it at its own pointer, and "e.g. for" or "3. října" in a need
    ends none."""
    needs = {
        "needs": [
            "Run the suite, e.g. for a release.",
            "Run it on 3. října.",
            "Run the suite. Then email the report.",
        ],
        "name": "x",
    }
    (departure,) = S.field_departures(needs, KINDS["actor"])
    assert (departure.pointer, departure.how) == ("/needs/2", "not-a-sentence")


def test_what_a_writer_adds_inside_a_sentence_part_counts_toward_it() -> None:
    """A writer's label is content of the part it falls in, so under *Goal* it counts
    toward the one sentence; after the next declared label it is that part's."""
    note = "\n\n**Note:** asked by sales. Twice."
    goal = "**Goal:** Export my report as a file."
    assert _found(USE_CASE.replace(goal, goal + note)) == [("goal", "not-a-sentence", 3)]
    other = "**Other actors:** None."
    assert _found(USE_CASE.replace(other, other + note)) == []


def test_only_declared_labels_delimit_so_a_writer_s_labels_and_sections_pass() -> None:
    """A variant's `**2a.**` and a writer's `**Note:**` are content, and a writer's own
    section ends the part above it without being reported."""
    added = USE_CASE.replace(
        "2. The system writes the report to a file.",
        "2. The system writes the report to a file.\n\n**Note:** the file is never sent.",
    )
    assert _found(f"{added}\n\n## Open questions\n\n**Why:** none yet.") == []


def test_a_heading_ends_a_label_s_part_at_the_label_s_level_or_above() -> None:
    """A label sits one level below the heading it follows, so under a use case's `#`
    heading a `##` section ends the part, and a `###` one stays inside it."""
    detail = "**Goal:**\n\n### Detail\n\nExport my report as a file."
    assert _found(USE_CASE.replace("**Goal:** Export my report as a file.", detail)) == []
    section = "**Goal:**\n\n## Detail\n\nExport my report as a file."
    assert _found(USE_CASE.replace("**Goal:** Export my report as a file.", section)) == [
        ("goal", "empty", 3)
    ]


def test_code_and_comments_hide_marks_and_a_hint_left_alone_is_no_content() -> None:
    trigger = "**Trigger:** The analyst asks to export the report on screen."
    fenced = USE_CASE.replace(trigger, f"```\n{trigger}\n```")
    commented = USE_CASE.replace(trigger, f"<!--\n{trigger}\n-->")
    assert _found(fenced) == _found(commented) == [("trigger", "missing", None)]
    quoted = USE_CASE.replace(
        "**Preconditions:** The analyst is signed in.",
        "**Preconditions:** The analyst sees `<!--` in a hint.",
    )
    assert _found(quoted) == []  # a code span's text is literal, so it opens no comment
    # Comments are found line by line, so a code span that runs on to the next line is
    # not seen, and the `<!--` in it opens a comment that hides the rest of the body.
    wrapped = quoted.replace("sees `<!--` in", "sees `a\n<!--` in")
    assert ("trigger", "missing", None) in _found(wrapped)
    hinted = USE_CASE.replace(
        "**Goal:** Export my report as a file.",
        "**Goal:** <!-- pkit:hint What the actor wants. -->",
    )
    assert _found(hinted) == [("goal", "empty", 3)]


def test_a_hint_left_in_is_found_outside_code_and_other_comments() -> None:
    """A hint is a comment that opens with its mark, found as a comment is: outside fenced
    code and outside a code span that closes on its line, and never inside another
    comment. Each is found at the line it opens on, with what it says (#1366)."""
    body = "\n".join(
        [
            "# UC-007 — Export the report as a file",
            "",
            "**Goal:** <!-- pkit:hint What the actor wants. Example: Export it. -->",
            "",
            "**Trigger:** The analyst quotes `<!-- pkit:hint quoted -->` in a code span.",
            "",
            "```markdown",
            "**Postconditions:** <!-- pkit:hint fenced -->",
            "```",
            "",
            "<!-- a note of the writer's, <!-- pkit:hint inside it --> -->",
            "",
            "<!--pkit:hint spaced",
            "over two lines -->",
            "",
            "Text <!-- an aside --> then <!-- pkit:hint after an aside -->",
        ]
    )
    assert S.hints(_lines(body, first=10)) == [
        (12, "What the actor wants. Example: Export it."),
        (22, "spaced"),
        (25, "after an aside"),
    ]
    assert S.hints(_lines(USE_CASE)) == []


def test_a_label_opens_a_line_or_a_top_level_list_item_only() -> None:
    indented = ACTOR_BODY.replace("- **Context:**", "  - **Context:**")
    assert _found(indented, "actor") == [("context", "missing", None)]
    mid_line = ACTOR_BODY.replace("- **Context:**", "- and **Context:**")
    assert _found(mid_line, "actor") == [("context", "missing", None)]


def test_an_actor_s_opening_is_the_text_before_its_first_label() -> None:
    bare = ACTOR_BODY.replace("Whoever writes and runs the project's tests.\n\n", "")
    assert _found(bare, "actor") == [("opening", "missing", None)]
    assert _found(ACTOR_BODY.replace("Whoever", "None.\n\nWhoever", 1), "actor") == []
    refused = ACTOR_BODY.replace("Whoever writes and runs the project's tests.", "None.")
    assert _found(refused, "actor") == [("opening", "none-refused", 3)]


def test_a_record_s_parts_are_its_headings() -> None:
    outcomes = RECORD_BODY.replace(
        "- **UC-001 — holds.** The export still writes the whole report.", "None."
    )
    assert _found(outcomes, "revalidation-record") == [("outcomes", "none-refused", 3)]
    no_gaps = RECORD_BODY.replace("\n\n## Gaps\n\nNone.", "")
    assert _found(no_gaps, "revalidation-record") == [("gaps", "missing", None)]


def test_a_collection_file_s_head_is_its_heading_and_its_opening() -> None:
    head = "# Glossary\n\nThe words of the domain and what each means."
    assert _found(head, "term", head=True) == []
    assert _found("# Glossary\n", "term", head=True) == [("file-opening", "missing", None)]
    assert _found("The words.", "term", head=True) == [("file-heading", "missing", None)]


def test_an_unordered_kind_takes_its_parts_in_any_order() -> None:
    kind = KINDS["actor"]
    swapped = ACTOR_BODY.replace("- **Occasions:** with every change.\n", "") + (
        "\n- **Occasions:** with every change."
    )
    assert _found(swapped, "actor") == [("context", "out-of-order", 5)]
    unordered = S.Kind(kind.name, kind.sections, ordered=False)
    assert [d.how for d in S.departures(_lines(swapped), unordered)] == []


def test_the_declaration_is_read_whole_or_not_at_all(tmp_path: Path) -> None:
    assert sorted(KINDS) == ["actor", "journey", "revalidation-record", "term", "use-case"]
    assert KINDS["use-case"].labels >= {"goal", "main path", "minimal guarantees"}
    broken = tmp_path / "kinds.yaml"
    broken.write_text("kinds: [\n", encoding="utf-8")
    with pytest.raises(S.Unreadable, match="it is not YAML"):
        S.read_kinds(broken)
    broken.write_text("schema_version: 1\nkinds: {}\nextra: true\n", encoding="utf-8")
    with pytest.raises(S.Unreadable, match=r"does not fit artefact-kinds\.schema\.json"):
        S.read_kinds(broken)


# --- the gate and the preview, on the check's own ------------------------------------------


def _analysis(root: Path, status: str | None, *artefacts: Any) -> Any:
    files = {a.path: a.kind for a in artefacts}
    rules = None if status is None else {RULE: status}
    return M.Analysis(
        location="docs/analysis",
        places={},
        artefacts=tuple(artefacts),
        strays=(),
        unreadable={},
        files=files,
        records=(),
        method_rules=rules,
    )


def _artefact(
    root: Path,
    rel: str,
    kind: str,
    text: str,
    *,
    entry: str | None = None,
    span: tuple[int, int] | None = None,
    **fields: Any,
) -> Any:
    """An artefact as the backbone's reading gives it, its file written under `root`:
    a document, or with `entry` the collection entry of that id, its section `span`."""
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(text, encoding="utf-8")
    return M.Artefact(
        kind=kind,
        id=entry,
        path=rel,
        location=f"{rel}#{entry}" if entry else rel,
        entry=entry is not None,
        fields=fields,
        anchors={},
        span=span,
        span_read=True,
    )


ACTOR_REL = "docs/analysis/use-case-model/actors/ACT-tester.md"
WITHOUT_CONTEXT = ACTOR_BODY.replace("\n- **Context:** the suite, and a sandbox to run it in.", "")


def _everywhere(analysis: Any) -> Any:
    """The backbone's reading of where rules bind, as a set of the project's own that
    selects every artefact and inherits `SAN` gives it: the format rule binds on each once
    accepted, and the preview places it on each while it is proposed."""
    status = (analysis.method_rules or {}).get(RULE)

    def reach(_root: Path, *, preview: bool = False) -> dict[str, dict[str, bool]]:
        if status == "accepted" or (preview and status == "proposed"):
            cited = f"software-analysis:{RULE}"
            return {a.location: {cited: status != "accepted"} for a in analysis.artefacts}
        return {}

    return reach


#: What opens the finding that says no rule of `SAN` binds on the analysis (DEC-001
#: point 1), said whenever none is accepted.
UNBOUND = "no rule of software-analysis:SAN binds on any of the analysis's"


def _structure(
    root: Path, status: str | None, *artefacts: Any, preview: bool = False, reach: Any = None
) -> Any:
    """The structure check's summary and findings, `SAN` bound on every artefact unless
    `reach` says otherwise, the finding that says it binds on none left out."""
    analysis = _analysis(root, status, *artefacts)
    summary, found = C._structure(
        root, analysis, preview=preview, reach=reach or _everywhere(analysis)
    )
    return summary, [
        (f.severity, f.location, f.message) for f in found if not f.message.startswith(UNBOUND)
    ]


def test_only_an_accepted_rule_binds_and_a_preview_shows_only_a_proposed_one(
    tmp_path: Path,
) -> None:
    actor = _artefact(tmp_path, ACTOR_REL, "actor", f"---\nid: ACT-tester\n---\n{WITHOUT_CONTEXT}")
    summary, found = _structure(tmp_path, "proposed", actor)
    assert found == []
    assert summary.startswith("structure (RS-SAN-001, proposed): not checked")
    assert "`pkit analysis validate --preview` shows what it would report" in summary
    summary, found = _structure(tmp_path, "proposed", actor, preview=True)
    ((severity, location, message),) = found
    assert (severity, location) == ("report", ACTOR_REL)
    assert message.startswith("preview: `**Context:**` is missing")
    assert "previewed as accepted" in summary and "reported and never failing" in summary
    summary, found = _structure(tmp_path, "accepted", actor)
    assert [(s, m) for s, _l, m in found] == [("error", message.removeprefix("preview: "))]
    for status in ("superseded", "withdrawn"):
        summary, found = _structure(tmp_path, status, actor, preview=True)
        assert found == []
        assert summary.startswith(
            f"structure (RS-SAN-001, {status}): not checked — the rule binds nothing "
            f"(COR-051 point 4). A preview shows only a proposed rule."
        )
    summary, found = _structure(tmp_path, None, actor, preview=True)
    assert found == []
    assert "the backbone's reading holds no software-analysis:SAN" in summary


def test_a_declaration_that_cannot_be_read_is_one_finding_at_the_rule_s_severity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No body is checked against a declaration that cannot be read: the check says so
    once, where the declaration lies, as an error under an accepted rule and as a
    preview's report under a proposed one."""

    def unreadable() -> dict[str, Any]:
        raise S.Unreadable("it is not YAML (found a tab, at line 3)")

    monkeypatch.setattr(S, "read_kinds", unreadable)
    actor = _artefact(tmp_path, ACTOR_REL, "actor", f"---\nid: ACT-tester\n---\n{WITHOUT_CONTEXT}")
    summary, [(severity, location, message)] = _structure(tmp_path, "accepted", actor)
    assert severity == "error"
    assert location == S.KINDS_FILE.as_posix()
    assert message.startswith("the kinds' structures cannot be read: it is not YAML")
    assert summary.endswith("not checked — the declaration cannot be read.")
    _summary, [(severity, _location, message)] = _structure(
        tmp_path, "proposed", actor, preview=True
    )
    assert (severity, message.split(":")[0]) == ("report", "preview")


def test_each_message_gives_the_part_s_hint_and_example(tmp_path: Path) -> None:
    actor = _artefact(tmp_path, ACTOR_REL, "actor", f"---\nid: ACT-tester\n---\n{WITHOUT_CONTEXT}")
    _summary, [(_severity, _location, message)] = _structure(tmp_path, "accepted", actor)
    (context,) = [e for e in KINDS["actor"].sections if e.id == "context"]
    assert message == (
        "`**Context:**` is missing, and it comes after `**Occasions:**`: an actor carries "
        f"every part its kind ships (RS-SAN-001). What goes there: {context.hint} "
        f"Example: {context.example}"
    )


def test_a_withdrawn_artefact_is_never_failed_for_a_part_it_lacks(tmp_path: Path) -> None:
    withdrawn = _artefact(
        tmp_path,
        ACTOR_REL,
        "actor",
        f"---\nid: ACT-tester\n---\n{WITHOUT_CONTEXT}",
        status="withdrawn",
    )
    assert _structure(tmp_path, "accepted", withdrawn)[1] == []
    # What it carries is still held: its opening, here, reads `None.`.
    refused = WITHOUT_CONTEXT.replace("Whoever writes and runs the project's tests.", "None.")
    withdrawn = _artefact(tmp_path, ACTOR_REL, "actor", refused, status="withdrawn")
    [(_s, _l, message)] = _structure(tmp_path, "accepted", withdrawn)[1]
    assert message.startswith("the opening text before `**Occasions:**`, at line 3, reads")


def test_a_document_s_missing_heading_is_left_to_the_heading_check(tmp_path: Path) -> None:
    """The heading check reports a document with no heading whatever the rule's status,
    so the structure does not report it twice."""
    headless = WITHOUT_CONTEXT.replace("# ACT-tester — Tester\n\n", "")
    actor = _artefact(tmp_path, ACTOR_REL, "actor", headless)
    [(_s, _l, message)] = _structure(tmp_path, "accepted", actor)[1]
    assert message.startswith("`**Context:**` is missing")


def test_an_entry_is_read_within_its_span_and_the_file_s_head_above_the_first(
    tmp_path: Path,
) -> None:
    glossary = "docs/analysis/glossary.md"
    text = (
        "---\nTERM-a: {}\nTERM-b: {}\n---\n\n# Glossary\n\n"  # lines 1 to 6
        "## TERM-a — a\n\n**Example:** None.\n\n"  # lines 8 to 11: no *Distinctions*
        "## TERM-b — b\n\n**Example:** None.\n\n**Distinctions:** None.\n"  # lines 12 to 16
    )
    a = _artefact(tmp_path, glossary, "term", text, entry="TERM-a", span=(8, 10))
    b = _artefact(tmp_path, glossary, "term", text, entry="TERM-b", span=(12, 16))
    summary, found = _structure(tmp_path, "accepted", a, b)
    assert [(location, message.split(",")[0]) for _s, location, message in found] == [
        (f"{glossary}#TERM-a", "`**Distinctions:**` is missing"),
        (glossary, "its opening text is missing"),
    ]
    assert "3 artefact(s) and file head(s) checked" in summary
    assert "2 of them departing" in summary
    # A glossary already failed as unreadable or as no collection has no head checked.
    unreadable = dataclasses.replace(
        _analysis(tmp_path, "accepted", a, b), unreadable={glossary: "it does not parse"}
    )
    summary, found = C._structure(
        tmp_path, unreadable, preview=False, reach=_everywhere(unreadable)
    )
    assert [f.location for f in found] == [f"{glossary}#TERM-a"]
    assert "2 artefact(s) and file head(s) checked" in summary
    stray = dataclasses.replace(
        _analysis(tmp_path, "accepted", a, b),
        strays=(M.Stray("term", glossary, "it is no collection"),),
    )
    found = C._structure(tmp_path, stray, preview=False, reach=_everywhere(stray))[1]
    assert [f.location for f in found] == [f"{glossary}#TERM-a"]
    no_section = _artefact(tmp_path, glossary, "term", text, entry="TERM-a")
    [(_s, location, message)] = _structure(tmp_path, "accepted", no_section)[1][:1]
    assert (location, message.split(":")[0]) == (
        f"{glossary}#TERM-a",
        "its `## ` heading is missing, and it comes first",
    )


# --- where the format rule binds, and never silent (DEC-001 point 1, #1475) -----------------

OTHER_REL = "docs/analysis/use-case-model/actors/ACT-other.md"


def _bound_on(*locations: str) -> Any:
    """The backbone's reading where a set of the project's own that inherits `SAN` selects
    only the artefacts at `locations`: the format rule binds there and nowhere else."""

    def reach(_root: Path, *, preview: bool = False) -> dict[str, dict[str, bool]]:
        return {location: {f"software-analysis:{RULE}": False} for location in locations}

    return reach


def _all(root: Path, status: str, *artefacts: Any, reach: Any, preview: bool = False) -> Any:
    """The structure check's summary and every finding, the never-silent one included."""
    summary, found = C._structure(
        root, _analysis(root, status, *artefacts), preview=preview, reach=reach
    )
    return summary, [(f.severity, f.location, f.message) for f in found]


def test_an_artefact_outside_every_scope_is_not_held_to_its_structure(tmp_path: Path) -> None:
    """`SAN` takes no scope, so the format rule binds only where a set of the project's own
    makes it bind, as the backbone answers (COR-051 point 7). An actor no such set selects
    is not checked, whatever it breaks, and the summary counts it."""
    tester = _artefact(tmp_path, ACTOR_REL, "actor", f"---\nid: ACT-tester\n---\n{WITHOUT_CONTEXT}")
    other = _artefact(tmp_path, OTHER_REL, "actor", f"---\nid: ACT-other\n---\n{WITHOUT_CONTEXT}")
    summary, found = _all(tmp_path, "accepted", tester, other, reach=_bound_on(ACTOR_REL))
    assert [(s, loc) for s, loc, _m in found] == [("error", ACTOR_REL)]
    assert "1 artefact(s) and file head(s) checked, where the rule binds" in summary
    assert summary.endswith("No rule of software-analysis:SAN binds on 1 of the 2 artefact(s).")
    # Outside every scope, it is not checked at all, and neither is it in a preview of a
    # proposed rule the preview does not place on it.
    summary, found = _all(tmp_path, "accepted", tester, other, reach=_bound_on())
    assert [(s, loc) for s, loc, _m in found] == [("warning", "docs/analysis")]
    assert "0 artefact(s) and file head(s) checked" in summary
    _summary, found = _all(
        tmp_path, "proposed", tester, other, reach=_bound_on(OTHER_REL), preview=True
    )
    assert [(s, loc, m.split(":")[0]) for s, loc, m in found] == [
        ("report", "docs/analysis", "no rule of software-analysis"),
        ("report", OTHER_REL, "preview"),
    ]


def test_a_glossary_s_head_is_held_where_the_rule_binds_on_a_term_of_its_file(
    tmp_path: Path,
) -> None:
    """The head belongs to no term but is part of the term kind's structure, so it is held
    where the format rule binds on a term of its file, and nowhere else (DEC-001 point
    1)."""
    glossary = "docs/analysis/glossary.md"
    text = (
        "---\nTERM-a: {}\n---\n\n"  # lines 1 to 3; no heading and no opening above the entry
        "## TERM-a — a\n\n**Example:** None.\n\n**Distinctions:** None.\n"  # lines 5 to 9
    )
    a = _artefact(tmp_path, glossary, "term", text, entry="TERM-a", span=(5, 9))
    _summary, found = _all(tmp_path, "accepted", a, reach=_bound_on(f"{glossary}#TERM-a"))
    assert [(loc, m.split(",")[0]) for _s, loc, m in found] == [
        (glossary, "its `# ` heading is missing"),
        (glossary, "its opening text is missing"),
    ]
    summary, found = _all(tmp_path, "accepted", a, reach=_bound_on())
    assert [s for s, _loc, _m in found] == ["warning"]
    assert "0 artefact(s) and file head(s) checked" in summary


def test_where_no_rule_of_san_binds_the_check_reports_it_and_once_one_is_accepted_warns(
    tmp_path: Path,
) -> None:
    """Never silent (DEC-001 point 1): where `SAN` binds on none of the analysis, the check
    says so, at the analysis, and why. While no rule of `SAN` is accepted, none could bind,
    so it reports it; once one is, it warns, naming the set that would make it bind."""
    actor = _artefact(tmp_path, ACTOR_REL, "actor", f"---\nid: ACT-tester\n---\n{WITHOUT_CONTEXT}")
    asked: list[bool] = []

    def nowhere(_root: Path, *, preview: bool = False) -> dict[str, dict[str, bool]]:
        asked.append(preview)
        return {}

    summary, [(severity, location, message)] = _all(tmp_path, "proposed", actor, reach=nowhere)
    assert (severity, location) == ("report", "docs/analysis")
    assert message.startswith(
        "no rule of software-analysis:SAN binds on any of the analysis's 1 artefact(s): none is "
        "accepted, so none binds whatever the project's rule sets say (COR-051 point 4)"
    )
    assert summary.endswith(
        "No rule of software-analysis:SAN binds on any of the 1 artefact(s), since none is "
        "accepted."
    )
    assert asked == []  # nothing is read while no rule of `SAN` could bind
    summary, [(severity, location, message)] = _all(tmp_path, "accepted", actor, reach=nowhere)
    assert (severity, location) == ("warning", "docs/analysis")
    assert message.startswith(
        "no rule of software-analysis:SAN binds on any of the analysis's 1 artefact(s), as "
        "`pkit rule-sets reach` reads it, so none is held to its structure: no set of the "
        "project's own whose scope selects them inherits software-analysis:SAN, or a pin "
        "behind its set holds it back (COR-051 point 7)"
    )
    assert "inherits software-analysis:SAN at its current major" in message
    assert asked == [False]  # read once, for the warning and the format rule alike
    # Bound on every artefact, nothing is said; with no artefact, nothing either.
    assert _all(tmp_path, "accepted", actor, reach=_bound_on(ACTOR_REL))[1][0][0] == "error"
    assert C._structure(tmp_path, _analysis(tmp_path, "accepted"), preview=False)[1] == []


# --- end to end, in an adopter ---------------------------------------------------------------


@pytest.fixture
def project(make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch)


def _validate(repo: AdopterRepo, *args: str) -> tuple[int, Any]:
    completed = run_script(repo, VALIDATE, *args)
    return completed.returncode, (
        json.loads(completed.stdout) if "--json" in args else completed.stdout
    )


def _said(document: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    return [(f["severity"], f["location"], f["message"]) for f in document["findings"]]


ACTOR_FRONT = (
    "---\nid: ACT-tester\nname: Tester\nstatus: active\nneeds:\n  - Run the suite.\n"
    "  - Run the suite. Then read the report.\npkit:\n  friction:\n"
    "    unanchored-because: No code embodies it.\n---\n\n"
)


def test_proposed_the_check_reports_nothing_and_the_preview_never_changes_the_exit(
    project: AdopterRepo, pkit_on_path: Path
) -> None:
    project.write(
        {
            actor_at("ACT-tester"): ACTOR_FRONT + WITHOUT_CONTEXT + "\n",
            ANALYSIS_SET: ANALYSIS_SET_TEXT,
        }
    )
    code, document = _validate(project, "--json")
    # No rule of `SAN` is accepted, so none binds, and the check reports it (DEC-001 point 1).
    unbound = ("report", ANALYSIS, "no rule of software-analysis")
    assert (code, [(s, loc, m.split(":")[0]) for s, loc, m in _said(document)]) == (0, [unbound])
    assert any(
        line.startswith("structure (RS-SAN-001, proposed): not checked")
        for line in document["summary"]
    )
    # The preview places the rule where `pkit rule-sets reach --preview` says it would bind:
    # through the set of the project's own that inherits `SAN`.
    code, document = _validate(project, "--json", "--preview")
    assert code == 0
    assert [(s, loc, m.split(":")[0]) for s, loc, m in _said(document)] == [
        unbound,
        ("report", actor_at("ACT-tester"), "preview"),
        ("report", f"{actor_at('ACT-tester')}:/needs/1", "preview"),
    ]
    code, output = _validate(project, "--preview")
    assert code == 0
    assert "preview: `**Context:**` is missing" in output
    # `pkit validate` runs the normal check, so the proposed rule shows nothing there.
    result = CliRunner().invoke(
        main, ["--color", "never", "validate", "--only", "software-analysis:artefacts"]
    )
    assert result.exit_code == 0, result.output
    assert "preview:" not in result.output


def test_accepted_a_departure_fails_and_an_entry_is_read_within_its_span(
    project: AdopterRepo, pkit_on_path: Path
) -> None:
    """The rule's status and each entry's span come from the backbone's reading: the
    adopter's copy of `SAN` flipped to accepted, as a fixture, and a glossary whose
    first entry lacks *Distinctions* that the second entry carries."""
    glossary = (
        "---\nTERM-a:\n  name: a\n  status: active\n  definition: first word\n"
        "  pkit:\n    friction:\n      unanchored-because: No code embodies it.\n"
        "TERM-b:\n  name: b\n  status: active\n  definition: second word\n"
        "  pkit:\n    friction:\n      unanchored-because: No code embodies it.\n---\n\n"
        "# Glossary\n\nThe words of the domain.\n\n"
        "## TERM-a — a\n\n**Example:** None.\n\n"
        "## TERM-b — b\n\n**Example:** None.\n\n**Distinctions:** None.\n"
    )
    project.write(
        {
            **accepting_san(project),
            actor_at("ACT-tester"): ACTOR_FRONT + ACTOR_BODY + "\n\n## Notes\n\n**Seen:** daily.\n",
            GLOSSARY: glossary,
        }
    )
    code, document = _validate(project, "--json")
    found = {location: (severity, message) for severity, location, message in _said(document)}
    assert sorted(found) == [GLOSSARY + "#TERM-a", actor_at("ACT-tester") + ":/needs/1"]
    assert {severity for severity, _message in found.values()} == {"error"}
    assert found[GLOSSARY + "#TERM-a"][1].startswith("`**Distinctions:**` is missing")
    assert found[actor_at("ACT-tester") + ":/needs/1"][1].startswith(
        "'Run the suite. Then read the report.' is more than one sentence: an actor's "
        "`needs` holds one sentence in each item"
    )
    assert any("(RS-SAN-001, accepted)" in line for line in document["summary"])
    code, _output = _validate(project)
    assert code == 1


def test_pkit_validate_reports_where_san_binds_on_none_and_warns_once_a_rule_is_accepted(
    project: AdopterRepo, pkit_on_path: Path
) -> None:
    """Never silent, end to end (DEC-001 point 1): `pkit validate` reports that no rule of
    `SAN` binds on the analysis while none is accepted. Once one is, and no set of the
    project's own makes it bind there, it warns. A set that inherits `SAN` and selects the
    analysis by its types makes the rule bind, and the check holds the actor to its
    structure. Neither the report nor the warning fails validation."""
    project.write({actor_at("ACT-tester"): ACTOR_FRONT + WITHOUT_CONTEXT + "\n"})
    only = ["--color", "never", "validate", "--only", "software-analysis:artefacts"]
    result = CliRunner().invoke(main, only)
    assert result.exit_code == 0, result.output
    assert "0 error(s), 0 warning(s), 0 info(s), 1 report(s)." in result.output
    unbound = "no rule of software-analysis:SAN binds on any of the analysis's 1 artefact(s)"
    assert f"{unbound}: none is accepted" in result.output
    accepted = accepting_san(project)
    project.write({SAN_REL: accepted[SAN_REL]})  # accepted, with no set of the project's own
    result = CliRunner().invoke(main, only)
    assert result.exit_code == 0, result.output
    assert "0 error(s), 1 warning(s), 0 info(s), 0 report(s)." in result.output
    assert "as `pkit rule-sets reach` reads it, so none is held to its structure" in result.output
    project.write({ANALYSIS_SET: ANALYSIS_SET_TEXT})
    result = CliRunner().invoke(main, only)
    assert result.exit_code == 1, result.output
    assert "`**Context:**` is missing" in result.output
    assert "no rule of software-analysis:SAN binds" not in result.output


def test_a_record_is_held_to_its_structure_while_the_format_rule_is_proposed(
    project: AdopterRepo, pkit_on_path: Path
) -> None:
    """A record is a held document, which no rule binds on, so the capability checks its
    structure itself, always: a record missing a part fails `pkit analysis validate` while
    `RS-SAN-001` is proposed, and with no set of the project's own (DEC-001 point 1)."""
    stamped(project, "actor", "tester", "--unanchored-because", "No code embodies it.")
    record = run_script(
        project,
        NEW,
        "revalidation",
        "suite",
        "--change",
        "#45",
        "--trigger",
        "planned",
        "--outcome",
        "ACT-tester=holds",
        "--because",
        "ACT-tester=The role is as described.",
        "--reviewed-against",
        "the design @ this change",
    )
    assert record.returncode == 0, record.stderr
    [written] = (project.root / RECORDS).glob("*.md")
    rel = written.relative_to(project.root).as_posix()
    code, document = _validate(project, "--json")
    # The actor still holds the stamp's hints, which are not this test's.
    on_records = [f for f in _said(document) if f[0] == "error" and f[1].startswith(RECORDS)]
    assert (code, on_records) == (0, [])
    assert any(
        line.startswith("records' structure, held always: 1 revalidation record(s) checked")
        for line in document["summary"]
    ), document["summary"]
    text = written.read_text(encoding="utf-8")
    written.write_text(text.split("\n## Gaps\n", 1)[0] + "\n", encoding="utf-8")
    _code, document = _validate(project, "--json")
    [(severity, location, message)] = [
        f for f in _said(document) if f[0] == "error" and f[1].startswith(RECORDS)
    ]
    assert (severity, location) == ("error", rel)
    assert message.startswith("the section `## Gaps` is missing")
    assert "(DEC-001 point 1)" in message
    assert any("(RS-SAN-001, proposed): not checked" in line for line in document["summary"])


def test_the_stamp_refuses_a_declaration_whose_hint_is_no_one_line_comment(
    project: AdopterRepo, pkit_on_path: Path
) -> None:
    """A hint is written as one comment on one line, so a hint that would close its comment
    early leaves the stamp nothing to render: it refuses, writing nothing, and says the
    declaration is the capability's own to restore (DEC-001 point 1)."""
    declaration = f"{SA.as_posix()}/schemas/artefact-kinds.yaml"
    stamped(project, "actor", "tester")
    text = (project.root / declaration).read_text(encoding="utf-8")
    broken = text.replace("hint: The event that starts", "hint: The event --> that starts", 1)
    assert broken != text
    project.write({declaration: broken})
    completed = run_script(project, NEW, "use-case", "run-suite", "--actor", "ACT-tester")
    assert completed.returncode == 1, completed.stdout
    assert "\nrefused: the kinds' structures cannot be read: " in f"\n{completed.stderr}"
    assert "restore it as the capability ships it" in completed.stderr
    assert not (project.root / ANALYSIS / "use-case-model" / "use-cases").exists()


#: What a person writes in place of each part's hint, by the part's label: a list, below
#: its label, starts on a line of its own. A journey's step lines are the stamp's, so its
#: *Steps* take nothing more. An actor's opening has no label.
WRITTEN = {
    "Goal": "Run my suite.",
    "Other actors": "None.",
    "Preconditions": "None.",
    "Assumptions": "None.",
    "Trigger": "The tester asks to run the suite.",
    "Main path": "\n\n1. The tester runs the suite.\n2. The system shows the result.",
    "Variants": "None.",
    "Postconditions": "The tester holds the result.",
    "Minimal guarantees": "None.",
    "Steps": "",
    "Occasions": "With every change.",
    "Context": "None.",
    "Example": "None.",
    "Distinctions": "None.",
}
OPENING = "Whoever runs the project's tests."


#: The front-matter fields' hints a person writes over, and what with (#1593).
FIELDS = {
    field_hint("actor", "needs"): "Run the suite.",
    field_hint("term", "definition"): "set of tests run together",
}

_HINTED = re.compile(r"(?:\*\*(?P<label>[^*\n]+):\*\* )?<!-- pkit:hint .*? -->")


def _written(text: str) -> str:
    """`text` with each hint written over as a person writes the part it holds."""

    def part(found: re.Match[str]) -> str:
        label = found["label"]
        if label is None:
            return OPENING
        content = WRITTEN[label]
        return f"**{label}:**" + (content if not content or content[0] == "\n" else f" {content}")

    for placeholder, words in FIELDS.items():
        text = text.replace(placeholder, words)
    return _HINTED.sub(part, text)


def test_every_kind_stamped_and_filled_carries_its_structure(
    project: AdopterRepo, pkit_on_path: Path
) -> None:
    """Each kind the stamp writes — an actor, a term, a use case, a journey and a record —
    once its hints are written over, departs from nothing of its structure, with the format
    rule accepted: every part present and in order, and each of its form (#1366)."""
    stamped(project, "actor", "tester", "--path", "src/**")
    stamped(project, "term", "suite", "--unanchored-because", "No code names it.")
    stamped(project, "use-case", "run-suite", "--actor", "ACT-tester", "--path", "src/run.py")
    stamped(project, "use-case", "read-report", "--actor", "ACT-tester")
    stamped(
        project,
        "journey",
        "first-run",
        "--actor",
        "ACT-tester",
        "--step",
        "UC-001",
        "--step",
        "UC-002",
    )
    record = run_script(
        project,
        NEW,
        "revalidation",
        "report-gap",
        "--change",
        "#45",
        "--trigger",
        "scheduled",
        "--outcome",
        "UC-002=gap-found",
        "--because",
        "UC-002=The report shows a total that no step describes.",
        "--gap",
        "UC-002: No step shows the total => step 2 written",
    )
    assert record.returncode == 0, record.stderr
    for path in sorted((project.root / ANALYSIS).rglob("*.md")):
        if (project.root / RECORDS) not in path.parents:
            path.write_text(_written(path.read_text(encoding="utf-8")), encoding="utf-8")
    project.write(accepting_san(project))
    code, document = _validate(project, "--json")
    assert (code, _said(document)) == (0, [])
    assert any(
        "6 artefact(s) and file head(s) checked" in line and "0 of them departing" in line
        for line in document["summary"]
    ), document["summary"]
    assert any(
        "1 revalidation record(s) checked" in line and "0 of them departing" in line
        for line in document["summary"]
    ), document["summary"]
