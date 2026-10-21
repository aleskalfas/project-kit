"""software-analysis: what a use case says the system does not do yet (#1855).

Held to software-analysis DEC-001 point 1 and DEC-003 point 8:

- **the box** — a callout whose first line is `[!WARNING]` and whose text opens with
  `**Not built yet:**`, at the top level of *Main path* or *Variants*, right below the
  item of its step or variant: the steps and variants keep their words and their forms;
- **the entry** — the use case's optional `shortfalls`, `{at, issue, record}`, whose
  shape the schema holds whatever any rule's status;
- **the check** — whatever any rule's status, each box is matched to an entry and each
  entry to a box, each entry's step or variant is one the body numbers, and each entry's
  record is one of the use case's record anchors, and accepted;
- **the overview** — a last section, "Not built yet", lists each entry of a use case in
  force, and the fingerprint reads them.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import (
    OVERVIEW_FILE,
    SA,
    SETTINGS,
    USE_CASES,
    VALIDATE,
    fill,
    installed,
    load_lib,
    prepare,
    run_script,
    stamped,
)

forms: Any
shortfalls: Any
structure: Any
overview: Any
forms, shortfalls, structure, overview = load_lib("forms", "shortfalls", "structure", "overview")

OVERVIEW = SA / "scripts" / "overview.py"
EXPORT = f"{USE_CASES}/UC-001-export.md"

#: The records the fixture's use case may rest on: one accepted, one proposed.
ACCEPTED = ".pkit/decisions/project/PRJ-001-sign-exports.md"
PROPOSED = ".pkit/decisions/project/PRJ-002-compress-exports.md"


def _record(number: str, title: str, status: str) -> str:
    return (
        f"---\nid: PRJ-{number}\ntitle: {title}\nstatus: {status}\ndate: 2026-10-21\n"
        f"author: Someone <someone@example.com>\n---\n\n## Context\n\nWhy.\n\n## Decision\n\n"
        f"{title}.\n"
    )


def _case(repo: AdopterRepo) -> None:
    """`prepare`, an actor stamped and filled, and two project records, one accepted and
    one proposed, committed."""
    prepare(repo)
    stamped(repo, "actor", "analyst", "--path", "src/**")
    fill(repo)
    repo.write(
        {
            ACCEPTED: _record("001", "Sign each export", "accepted"),
            PROPOSED: _record("002", "Compress each export", "proposed"),
        }
    )
    repo.commit("records")


@pytest.fixture
def project(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch, then=_case)


#: A use case's body, its *Main path* and *Variants* given, each box in its place.
BODY = """# UC-001 — Export the report

**Goal:** Export my report as a file.

**Other actors:** None.

**Preconditions:** None.

**Assumptions:** None.

**Trigger:** The analyst asks to export the report on screen.

**Main path:**

{main_path}

**Variants:**

{variants}

**Postconditions:** The file holds the whole report.

**Minimal guarantees:** A failed export leaves no partial file.
"""

#: Three steps, the second carrying a box.
MAIN_PATH = """1. The analyst chooses `Export`.
2. The system writes the report to a file, and signs it.

> [!WARNING]
> **Not built yet:** the system writes the file unsigned. PRJ-001 decides that
> each export is signed, and [#12](https://example.com/issues/12) tracks it.

3. The system says where the file is."""

#: One variant of step 2 carrying a box, then another.
VARIANTS = """- **2a.** The disk is full. The system says so, and the use case ends.

> [!WARNING]
> **Not built yet:** the system does not say how much room is missing (software-analysis
> DEC-001 point 1, tracked in #13).

- **3a.** The folder is gone. The system says so, and the use case ends."""

#: The entries that match the boxes above.
ENTRIES = [
    {"at": 2, "issue": "#12", "record": "PRJ-001"},
    {"at": "2a", "issue": "#13", "record": "software-analysis:DEC-001#1"},
]

#: The records the use case anchors, those its entries name among them.
RECORDS = ["PRJ-001", "PRJ-002", "software-analysis:DEC-001#1"]


def _use_case(
    *,
    main_path: str = MAIN_PATH,
    variants: str = VARIANTS,
    entries: Any = ENTRIES,
    records: list[str] | None = None,
    status: str = "active",
) -> str:
    """The fixture's use case, its `shortfalls` left out where `entries` is `None`."""
    written = "" if entries is None else f"shortfalls: {json.dumps(entries)}\n"
    anchored = json.dumps(RECORDS if records is None else records)
    return (
        f"---\nid: UC-001\ntitle: Export the report\nstatus: {status}\nactor: ACT-analyst\n"
        f"{written}pkit:\n  friction:\n    anchors:\n      record: {anchored}\n"
        f"      artefact: [ACT-analyst]\n---\n\n"
        + BODY.format(main_path=main_path, variants=variants)
    )


def _validate(repo: AdopterRepo) -> dict[str, Any]:
    completed = run_script(repo, VALIDATE, "--json")
    assert completed.returncode in (0, 1), completed.stderr
    return json.loads(completed.stdout)


def _about(document: dict[str, Any]) -> list[tuple[str, str, str]]:
    """The findings on the fixture's use case that concern its shortfalls: severity,
    location and message."""
    return [
        (f["severity"], f["location"], f["message"])
        for f in document["findings"]
        if f["location"].startswith(EXPORT)
        and ("shortfalls" in f["location"] or "Not built yet" in f["message"])
    ]


def _kind() -> Any:
    return structure.read_kinds()["use-case"]


def _line_of(text: str, needle: str) -> int:
    """The number of the first line of `text` that holds `needle`, counted from 1."""
    return next(n for n, line in enumerate(text.split("\n"), 1) if needle in line)


# --- the box, read --------------------------------------------------------------------------


def test_a_box_stands_right_below_its_step_or_variant() -> None:
    """Each box is read with the step or the variant whose item stands right above it, at
    the top level of its part, and its text after its `[!WARNING]` line, white space
    folded (DEC-001 point 1)."""
    reading = shortfalls.read(_use_case(), _kind())
    assert [(b.at, b.misplaced) for b in reading.boxes] == [("2", None), ("2a", None)]
    assert reading.boxes[0].text.startswith("**Not built yet:** the system writes the file")
    assert reading.boxes[0].holds("#12") and reading.boxes[0].names("PRJ-001")
    assert reading.numbered == {"1", "2", "3", "2a", "3a"}


def test_a_box_leaves_its_step_s_words_and_the_forms_as_they_are() -> None:
    """A box at the top level of its part is no part of the step above it, so the step's
    words, which journeys and evidence cite, stay as they are (DEC-001 point 3). The
    steps and variants keep their forms, and the body its structure."""
    text = _use_case()
    lines = structure.body_lines(text)
    parts = dict((e.id, p) for e, p in structure.parts(lines, _kind()))
    steps = [(n, words) for n, _item, words in forms.steps(parts["main-path"])]
    assert steps == [
        (1, "The analyst chooses `Export`."),
        (2, "The system writes the report to a file, and signs it."),
        (3, "The system says where the file is."),
    ]
    variants = [label for label, _item, _words in forms.variants(parts["variants"])]
    assert variants == ["2a", "3a"]
    assert structure.departures(lines, _kind()) == []


@pytest.mark.parametrize(
    ("main_path", "why"),
    [
        (
            "1. The analyst chooses `Export`.\n\n"
            "   > [!WARNING]\n   > **Not built yet:** #12 PRJ-001.\n",
            "it stands inside an item, indented under it",
        ),
        (
            "> [!WARNING]\n> **Not built yet:** #12 PRJ-001.\n\n1. The analyst chooses `Export`.",
            "it stands above the part's first item",
        ),
        (
            "1. The analyst chooses `Export`.\n- A note of the writer's.\n\n"
            "> [!WARNING]\n> **Not built yet:** #12 PRJ-001.",
            "the item above it opens with no step's number",
        ),
    ],
)
def test_a_box_anywhere_else_in_the_steps_is_misplaced(main_path: str, why: str) -> None:
    """A box inside an item, above the first, or below an item that names no step, stands
    where no box may (DEC-001 point 1)."""
    reading = shortfalls.read(_use_case(main_path=main_path, variants="None."), _kind())
    assert [(b.at, b.misplaced) for b in reading.boxes] == [(None, why)]


def test_a_box_outside_the_steps_and_variants_is_misplaced_and_code_holds_none() -> None:
    """A box in another part stands where no box may. One in fenced code, or a callout
    whose text does not open with "Not built yet", is no box."""
    text = _use_case(variants="None.").replace(
        "**Postconditions:** The file holds the whole report.",
        "**Postconditions:** The file holds the whole report.\n\n"
        "> [!WARNING]\n> **Not built yet:** #12 PRJ-001.\n\n"
        "```markdown\n> [!WARNING]\n> **Not built yet:** #12 PRJ-001.\n```\n\n"
        "> [!WARNING]\n> The disk may fill up.",
    )
    reading = shortfalls.read(text, _kind())
    assert [(b.at, b.misplaced) for b in reading.boxes] == [
        ("2", None),
        (None, "it stands outside the use case's steps and variants"),
    ]


@pytest.mark.parametrize(
    ("box", "why"),
    [
        ("> [!NOTE]\n> **Not built yet:** #12 PRJ-001.", shortfalls.OUT_OF_FORM),
        ("> [!WARNING]\n> **Not built yet**: #12 PRJ-001.", shortfalls.OUT_OF_FORM),
        ("> Not built yet: #12 PRJ-001.", shortfalls.OUT_OF_FORM),
        (
            "> [!WARNING]\n> **Not built yet:** #12 PRJ-001.\n3. The system says where.",
            shortfalls.NO_BLANK_BELOW,
        ),
    ],
)
def test_a_box_out_of_its_form_or_with_no_blank_line_below_fails(box: str, why: str) -> None:
    """A block quote that reads like a box in another form is no box a reader can trust,
    and a line right below a box shows inside it, so the next step would vanish into it."""
    main_path = f"1. The analyst chooses `Export`.\n2. The system writes the file.\n\n{box}"
    reading = shortfalls.read(_use_case(main_path=main_path, variants="None."), _kind())
    assert [(b.at, b.misplaced) for b in reading.boxes] == [(None, why)]


def test_an_entry_takes_the_box_that_holds_its_issue_and_names_its_record() -> None:
    """The issue is held as written, as a word of its own, and the record's id is named,
    a capability's decision by its `DEC-NNN`. An entry takes only a box it fits."""
    box = shortfalls.Box(9, "**Not built yet:** see #123 and org/repo#12 (COR-0470).", at="2")
    assert not box.holds("#12") and not box.names("COR-047")
    box = shortfalls.Box(9, "**Not built yet:** [#12](https://x/12), PRJ-001 decides it.", at="2")
    entry = shortfalls.Entry(0, "2", "#12", "PRJ-001")
    other = shortfalls.Entry(1, "2", "#12", "project-management:DEC-054#5")
    assert other.record_named == "project-management:DEC-054" and other.record_id == "DEC-054"
    taken, untaken = shortfalls.matched([other, entry], [box])
    assert taken == {0: box}
    assert untaken == []


def test_as_many_entries_as_can_be_take_a_box_each() -> None:
    """Where one box fits two entries, and another fits only the first, each entry takes a
    box: the matching is a maximum one, never the first fit."""
    both = shortfalls.Box(9, "**Not built yet:** #10, COR-047 and COR-050.", at="4")
    one = shortfalls.Box(14, "**Not built yet:** #10, COR-047.", at="4")
    first = shortfalls.Entry(0, "4", "#10", "COR-047")
    second = shortfalls.Entry(1, "4", "#10", "COR-050")
    taken, untaken = shortfalls.matched([first, second], [both, one])
    assert taken == {0: one, 1: both} and untaken == []


# --- the entry, and the check -----------------------------------------------------------------


def test_boxes_and_entries_that_match_pass(project: AdopterRepo) -> None:
    """Each box with its entry, each entry's record anchored and accepted, a capability's
    decision among them: nothing to report. A use case with neither passes too."""
    project.write({EXPORT: _use_case()})
    assert _about(_validate(project)) == []
    plain = _use_case(main_path="1. The analyst chooses `Export`.", variants="None.", entries=None)
    project.write({EXPORT: plain})
    assert _about(_validate(project)) == []


def test_the_schema_holds_the_entries_shape_whatever_any_rule_s_status(
    project: AdopterRepo,
) -> None:
    """Each entry names its step or variant, its issue in one word and a record as an
    anchor writes it, and nothing else."""
    for entries in (
        [],
        [{"at": 2, "issue": "#12"}],
        [{"at": "2A", "issue": "#12", "record": "PRJ-001"}],
        [{"at": 0, "issue": "#12", "record": "PRJ-001"}],
        [{"at": 2, "issue": "issue 12", "record": "PRJ-001"}],
        [{"at": 2, "issue": "#12", "record": "a decision"}],
        [{"at": 2, "issue": "#12", "record": "PRJ-001", "note": "x"}],
    ):
        project.write({EXPORT: _use_case(entries=entries)})
        located = [
            f
            for f in _validate(project)["findings"]
            if f["location"].startswith(f"{EXPORT}:/shortfalls")
        ]
        assert located and {f["severity"] for f in located} == {"error"}, entries


def test_an_entry_with_no_box_and_a_box_with_no_entry_fail(project: AdopterRepo) -> None:
    """The check holds each box to an entry and each entry to a box, whatever any rule's
    status: SAN binds through no set of the project's here (DEC-001 point 1)."""
    text = _use_case(entries=[ENTRIES[1], {**ENTRIES[0], "at": 3}])
    project.write({EXPORT: text})
    found = _about(_validate(project))
    line = _line_of(text, "[!WARNING]")
    assert [(s, where) for s, where, _ in found] == [
        ("error", f"{EXPORT}:/shortfalls/1"),
        ("error", EXPORT),
    ]
    assert found[0][2].startswith("no `Not built yet` box stands below step 3: each step or")
    assert found[1][2].startswith(
        f"the `Not built yet` box at line {line}, below step 2, has no entry in `shortfalls` "
        "that names step 2, an issue the box holds and a record whose id it names"
    )


def test_a_box_that_names_another_issue_or_record_is_no_entry_s(project: AdopterRepo) -> None:
    """An entry takes only a box that holds its issue and names its record's id."""
    project.write({EXPORT: _use_case(entries=[{**ENTRIES[0], "issue": "#14"}, ENTRIES[1]])})
    found = _about(_validate(project))
    assert [where for _s, where, _m in found] == [f"{EXPORT}:/shortfalls/0", EXPORT]
    assert found[0][2].startswith(
        "no box below step 2 that another entry does not take holds both its issue, `#14`, and "
        "its record's id, PRJ-001:"
    )


def test_an_entry_names_a_step_or_variant_the_body_numbers(project: AdopterRepo) -> None:
    project.write(
        {EXPORT: _use_case(entries=[*ENTRIES, {"at": "9b", "issue": "#15", "record": "PRJ-001"}])}
    )
    assert _about(_validate(project)) == [
        (
            "error",
            f"{EXPORT}:/shortfalls/2/at",
            "variant 9b is no step or variant the use case's body numbers: an entry names the "
            "step or the variant its box stands below (DEC-001 point 1)",
        )
    ]


def test_a_misplaced_box_fails(project: AdopterRepo) -> None:
    """A box indented into its step's item would change the step's words, so it stands
    where no box may (DEC-001 point 1)."""
    text = _use_case(main_path=MAIN_PATH.replace("> ", "   > "), entries=[ENTRIES[1]])
    project.write({EXPORT: text})
    found = _about(_validate(project))
    line = _line_of(text, "[!WARNING]")
    assert [(where, message.split(":", 1)[0]) for _s, where, message in found] == [
        (EXPORT, f"the `Not built yet` box at line {line} is out of its place or form")
    ]
    assert "it stands inside an item, indented under it" in found[0][2]


def test_an_entry_s_record_is_anchored_and_accepted(project: AdopterRepo) -> None:
    """A shortfall rests on its record, so the use case anchors it as written, and only an
    accepted record grounds a step the system does not carry out (DEC-001 point 1)."""
    entries = [
        {"at": 2, "issue": "#12", "record": "PRJ-002"},
        {"at": "2a", "issue": "#13", "record": "software-analysis:DEC-001#1"},
    ]
    main_path = MAIN_PATH.replace("PRJ-001", "PRJ-002")
    project.write({EXPORT: _use_case(main_path=main_path, entries=entries, records=["PRJ-002"])})
    found = _about(_validate(project))
    assert found == [
        (
            "error",
            f"{EXPORT}:/shortfalls/0/record",
            "PRJ-002 is proposed, not accepted: only an accepted record grounds a step or a "
            "variant the system does not carry out yet. Name the accepted record that decides "
            "step 2, or describe it as the code does (DEC-001 point 1)",
        ),
        (
            "error",
            f"{EXPORT}:/shortfalls/1/record",
            "`software-analysis:DEC-001#1` is no record anchor of the use case: a shortfall "
            "rests on its record, so the use case anchors it as the entry writes it, and a "
            "change to the record flags the use case (DEC-001 points 1 and 11)",
        ),
    ]


def test_an_entry_s_record_names_a_record_the_repository_holds(project: AdopterRepo) -> None:
    entries = [{"at": 2, "issue": "#12", "record": "PRJ-009"}, ENTRIES[1]]
    main_path = MAIN_PATH.replace("PRJ-001", "PRJ-009")
    project.write(
        {EXPORT: _use_case(main_path=main_path, entries=entries, records=[*RECORDS, "PRJ-009"])}
    )
    found = _about(_validate(project))
    assert [(where, message.split(":", 1)[0]) for _s, where, message in found] == [
        (f"{EXPORT}:/shortfalls/0/record", "`PRJ-009` names no record the repository holds")
    ]


def test_a_withdrawn_use_case_is_history(project: AdopterRepo) -> None:
    """A withdrawn use case's boxes and entries are not read: its records may have been
    superseded since."""
    project.write(
        {EXPORT: _use_case(entries=[ENTRIES[0]], records=["PRJ-002"], status="withdrawn")}
    )
    assert _about(_validate(project)) == []


# --- the overview -----------------------------------------------------------------------------


def _section(text: str, heading: str) -> str:
    lines = text.split("\n")
    start = lines.index(heading) + 1
    stop = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start:stop]).strip("\n")


def test_the_overview_lists_each_open_shortfall_last(project: AdopterRepo) -> None:
    """Under "Not built yet", the last section, each entry of a use case in force: its use
    case, linked, its step or variant, its record and its issue. The fingerprint reads
    the entries, so a changed entry leaves the overview stale until it is rewritten
    (DEC-003 point 8)."""
    project.write({SETTINGS: "pkit_schema: software-analysis:config\nschema_version: 1\n"})
    project.write({EXPORT: _use_case()})
    assert run_script(project, OVERVIEW).returncode == 0
    text = (project.root / OVERVIEW_FILE).read_text(encoding="utf-8")
    assert re.findall(r"^## .*$", text, re.M)[-1] == "## Not built yet"
    link = "[UC-001 — Export the report](../use-case-model/use-cases/UC-001-export.md)"
    assert _section(text, "## Not built yet") == (
        "What the use cases describe and the system does not do yet, each with the record "
        "that decides it and the issue that tracks it (software-analysis DEC-001 point 1):\n\n"
        f"- {link}: step 2, decided by `PRJ-001`, tracked in `#12`\n"
        f"- {link}: variant 2a, decided by `software-analysis:DEC-001#1`, tracked in `#13`"
    )
    assert f"reads={overview.VERSION} " in text and overview.VERSION == 3

    entries = [ENTRIES[0], {**ENTRIES[1], "issue": "https://example.com/issues/13"}]
    project.write(
        {
            EXPORT: _use_case(
                variants=VARIANTS.replace("#13", "https://example.com/issues/13"), entries=entries
            )
        }
    )
    stale = [f for f in _validate(project)["findings"] if f["location"] == OVERVIEW_FILE]
    assert [f["severity"] for f in stale] == ["error"]
    assert run_script(project, OVERVIEW).returncode == 0
    text = (project.root / OVERVIEW_FILE).read_text(encoding="utf-8")
    assert text.rstrip("\n").endswith("tracked in <https://example.com/issues/13>")

    plain = _use_case(main_path="1. The analyst chooses `Export`.", variants="None.", entries=None)
    project.write({EXPORT: plain})
    assert run_script(project, OVERVIEW).returncode == 0
    assert "## Not built yet" not in (project.root / OVERVIEW_FILE).read_text(encoding="utf-8")
