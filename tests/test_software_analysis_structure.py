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
    GLOSSARY,
    NEW,
    RECORDS,
    SA,
    VALIDATE,
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
SAN_REL = f"{SA.as_posix()}/rule-sets/san.md"

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
        ("Why export? To share it.", False),
        ("Export it, e.g. as a file.", False),  # a space after "e.g." ends a sentence
        ("Export my report.\nShare it.", False),
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


def test_in_a_list_each_item_of_a_sentence_part_holds_one_sentence() -> None:
    """A `sentence` part written as a list holds the form in each item, as RS-SAN-001's
    *How* says of a list: each item, a nested one apart from the item it sits in, and
    the rest of the part taken as one text, each found at its own line (#1365)."""
    goal = "**Goal:** Export my report as a file."
    listed = "**Goal:**\n\n- Export my report.\n- Share it."
    assert _found(USE_CASE.replace(goal, listed)) == []
    two = "**Goal:**\n\n- Export my report. Then share it.\n- Keep it."
    assert _found(USE_CASE.replace(goal, two)) == [("goal", "not-a-sentence", 5)]
    lead = "**Goal:** Two things. Both today.\n\n- Export my report.\n- Share it."
    assert _found(USE_CASE.replace(goal, lead)) == [("goal", "not-a-sentence", 3)]
    nested = "- **Goal:**\n  - Export my report.\n    - As a file.\n  - Share it."
    assert _found(USE_CASE.replace(goal, nested)) == []
    # A line wrapped under its item's text stays in the item, `2026.` and all.
    wrapped = "**Goal:**\n\n- Export my report by the end of\n  2026. Then share it."
    assert _found(USE_CASE.replace(goal, wrapped)) == [("goal", "not-a-sentence", 5)]
    # Without a list the part is one text, and a wrapped `2026` continues it.
    paragraph = "**Goal:** Export my report by the end of\n2026 as a file."
    assert _found(USE_CASE.replace(goal, paragraph)) == []
    # A line right below the label that opens with `2.` continues the label's paragraph.
    continued = "**Goal:** Export my report.\n2. Then share it."
    assert _found(USE_CASE.replace(goal, continued)) == [("goal", "not-a-sentence", 3)]


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


def _structure(root: Path, status: str | None, *artefacts: Any, preview: bool = False) -> Any:
    summary, found = C._structure(root, _analysis(root, status, *artefacts), [], preview=preview)
    return summary, [(f.severity, f.location, f.message) for f in found]


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
        assert summary == (
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
    assert "3 artefact(s), record(s) and file head(s) checked" in summary
    assert "2 of them departing" in summary
    # A glossary already failed as unreadable or as no collection has no head checked.
    unreadable = dataclasses.replace(
        _analysis(tmp_path, "accepted", a, b), unreadable={glossary: "it does not parse"}
    )
    summary, found = C._structure(tmp_path, unreadable, [], preview=False)
    assert [f.location for f in found] == [f"{glossary}#TERM-a"]
    assert "2 artefact(s), record(s) and file head(s) checked" in summary
    stray = dataclasses.replace(
        _analysis(tmp_path, "accepted", a, b),
        strays=(M.Stray("term", glossary, "it is no collection"),),
    )
    assert [f.location for f in C._structure(tmp_path, stray, [], preview=False)[1]] == [
        f"{glossary}#TERM-a"
    ]
    no_section = _artefact(tmp_path, glossary, "term", text, entry="TERM-a")
    [(_s, location, message)] = _structure(tmp_path, "accepted", no_section)[1][:1]
    assert (location, message.split(":")[0]) == (
        f"{glossary}#TERM-a",
        "its `## ` heading is missing, and it comes first",
    )


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
    project.write({actor_at("ACT-tester"): ACTOR_FRONT + WITHOUT_CONTEXT + "\n"})
    code, document = _validate(project, "--json")
    assert (code, _said(document)) == (0, [])
    assert any(
        line.startswith("structure (RS-SAN-001, proposed): not checked")
        for line in document["summary"]
    )
    code, document = _validate(project, "--json", "--preview")
    assert code == 0
    assert [(s, loc, m.split(":")[0]) for s, loc, m in _said(document)] == [
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
    text = (project.root / SAN_REL).read_text(encoding="utf-8")
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
            SAN_REL: text.replace("status: proposed", "status: accepted", 1),
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
    text = (project.root / SAN_REL).read_text(encoding="utf-8")
    project.write({SAN_REL: text.replace("status: proposed", "status: accepted", 1)})
    code, document = _validate(project, "--json")
    assert (code, _said(document)) == (0, [])
    assert any(
        "7 artefact(s), record(s) and file head(s) checked" in line
        and "0 of them departing" in line
        for line in document["summary"]
    ), document["summary"]
