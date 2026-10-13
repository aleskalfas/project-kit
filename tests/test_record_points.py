"""A decision record's points: the one reading of them (COR-058; ADR-057 point 2; #1414).

The home reads a record's Decision with the reading of where a part of a
document lies. It gives the Decision's extent, its points and stubs, its
misspelt headings, its retired ids with their successors, its points in list
form while it has no point heading, and what each point stands on. It holds
each stub to its entry in `retired-points`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from project_kit import record_points as rp

REPO = Path(__file__).resolve().parents[1]

FRONT = "---\nid: COR-900\ntitle: A record\nstatus: accepted\ndate: 2026-10-13\n{extra}---\n\n"


def _record(decision: str, *, extra: str = "", before: str = "", after: str = "") -> str:
    """A record whose Decision is `decision`, with `before` ahead of its Context and
    `after` after its Decision."""
    rationale = "## Rationale\n\n### 6. Not a point\n\nRationale's own numbered heading.\n"
    return (
        FRONT.format(extra=extra)
        + before
        + "## Context\n\nWhy.\n\n## Decision\n\n"
        + decision
        + "\n"
        + (after or rationale)
    )


def _ids(read: rp.RecordPoints) -> list[str]:
    return [point.id for point in read.points]


def _text(read: rp.RecordPoints, point: rp.PointHeading) -> str:
    return read.body.text_of(point.extent)


# --- each point form -------------------------------------------------------------------


def test_a_numbered_point_heading_is_a_point_found_in_the_decision_only() -> None:
    """`### 5. Title`: its id is the number, its section runs to the next heading of the
    same or a higher level. A `### 6.` heading in Rationale is never point 6."""
    read = rp.read_points(
        _record(
            "The lead.\n\n### 1. First\n\nOne.\n\n### 2. Second\n\nTwo.\n\n#### Detail\n\nMore.\n"
        )
    )
    assert read.decision is not None and read.decision.heading is not None
    assert read.decision.heading.title == "Decision"
    assert read.level == 3
    assert _ids(read) == ["1", "2"]
    assert [p.title for p in read.points] == ["First", "Second"]
    assert _text(read, read.points[1]) == "### 2. Second\n\nTwo.\n\n#### Detail\n\nMore.\n"
    assert read.point("6") is None
    assert read.list_points == () and not read.in_list_form


def test_a_labelled_point_heading_is_a_point() -> None:
    """`### D1 — Title`: a label is letters then a number."""
    read = rp.read_points(
        _record("### D1 — Declared\n\nOne.\n\n### D2 — Kept\n\nTwo.\n\n### p3 — Lower\n\n3.\n")
    )
    assert _ids(read) == ["D1", "D2", "p3"]
    assert [p.title for p in read.points] == ["Declared", "Kept", "Lower"]


@pytest.mark.parametrize(
    ("decision", "ids", "forms", "titles"),
    [
        # A numbered list at the Decision's top level, each item with a bold lead.
        (
            "**The decision.**\n\n1. **Artefacts.** What they are.\n2. **Anchors.** What they\n"
            "   name, over two lines.\n\n3. **The revalidation.** When.\n",
            ["1", "2", "3"],
            {rp.ListForm.ITEM},
            ["Artefacts", "Anchors", "The revalidation"],
        ),
        # Markdown shows a list's numbers from its first item, whatever the others write.
        (
            "1. **One.** a\n1. **Two.** b\n1. **Three.** c\n",
            ["1", "2", "3"],
            {rp.ListForm.ITEM},
            ["One", "Two", "Three"],
        ),
        # Paragraphs that open with a bold number; a bold lead may wrap.
        (
            "**1. Intra-file ownership\npartition.** In managed mode.\n\n"
            "**2. The hook boundary.** The hook.\n",
            ["1", "2"],
            {rp.ListForm.BOLD_NUMBER},
            ["Intra-file ownership partition", "The hook boundary"],
        ),
        # Paragraphs that open with a bold label.
        (
            "**D1 — Surface changes are declared.** A changeset.\n\n"
            "**D2 — The segment is a judgment.** Which segment.\n",
            ["D1", "D2"],
            {rp.ListForm.BOLD_LABEL},
            ["Surface changes are declared", "The segment is a judgment"],
        ),
        # A bold number or label holding only the id: the point has no title yet.
        (
            "**1.** Intra-file ownership.\n\n**2.** The hook.\n",
            ["1", "2"],
            {rp.ListForm.BOLD_NUMBER},
            [None, None],
        ),
        (
            "**D1** — Declared, not applied.\n\n**D2** — A judgment.\n",
            ["D1", "D2"],
            {rp.ListForm.BOLD_LABEL},
            [None, None],
        ),
        # Items written with a closing parenthesis.
        ("1) **One.** a\n2) **Two.** b\n", ["1", "2"], {rp.ListForm.ITEM}, ["One", "Two"]),
        # A list at the top level, then labelled paragraphs: two id spaces, both points.
        (
            "**The router.**\n\n1. **Source checkout.** Exec it.\n2. **A pin.** Re-exec.\n\n"
            "**D1 — Soundness.** It rests on ADR-033.\n",
            ["1", "2", "D1"],
            {rp.ListForm.ITEM, rp.ListForm.BOLD_LABEL},
            ["Source checkout", "A pin", "Soundness"],
        ),
    ],
)
def test_each_point_form_of_a_record_in_list_form(
    decision: str, ids: list[str], forms: set[rp.ListForm], titles: list[str | None]
) -> None:
    """COR-058 point 2: a record not yet converted writes its points as numbered items,
    or as paragraphs that open with a bold number or a bold label."""
    read = rp.read_points(_record(decision))
    assert read.points == () and read.in_list_form
    assert [p.id for p in read.list_points] == ids
    assert {p.form for p in read.list_points} == forms
    assert [p.title for p in read.list_points] == titles


def test_a_list_point_keeps_the_number_it_is_written_with() -> None:
    read = rp.read_points(_record("1. **One.** a\n1. **Two.** b\n"))
    assert [(p.id, p.written) for p in read.list_points] == [("1", "1"), ("2", "1")]
    assert read.body.text[read.list_points[1].start :].startswith("1. **Two.**")


# --- a group heading -------------------------------------------------------------------


def test_points_under_group_headings_sit_one_level_below_them() -> None:
    """COR-058 point 1: `#### 11. Title` under a group heading; the group's own text and
    heading are no point's."""
    read = rp.read_points(
        _record(
            "The lead.\n\n### What it carries\n\nGroup text.\n\n#### 1. Artefacts\n\nOne.\n\n"
            "#### 2. Anchors\n\nTwo.\n\n### What it computes\n\n#### 3. Changes\n\nThree.\n"
        )
    )
    assert read.level == 4
    assert _ids(read) == ["1", "2", "3"]
    groups = [p.group.title if p.group else None for p in read.points]
    assert groups == ["What it carries", "What it carries", "What it computes"]
    assert _text(read, read.points[1]) == "#### 2. Anchors\n\nTwo.\n"


def test_a_numbering_that_runs_across_group_headings_holds_points() -> None:
    """COR-058 point 2: in list form, one numbering across the Decision's group headings."""
    read = rp.read_points(
        _record(
            "**The decision.**\n\n### What it carries\n\n1. **Artefacts.** a\n2. **Anchors.** b\n\n"
            "### What it computes\n\n3. **Changes.** c\n\n### Commands\n\n4. **Commands.** d\n"
        )
    )
    assert [p.id for p in read.list_points] == ["1", "2", "3", "4"]


def test_a_numbering_that_continues_the_lead_s_list_in_a_group_holds_points() -> None:
    read = rp.read_points(_record("1. **One.** a\n2. **Two.** b\n\n### More\n\n3. **Three.** c\n"))
    assert [p.id for p in read.list_points] == ["1", "2", "3"]


# --- a list inside a sub-section --------------------------------------------------------


def test_a_numbered_list_inside_a_sub_section_holds_no_points() -> None:
    """COR-058 point 2: its numbers are steps or an order, and it stays a list."""
    read = rp.read_points(
        _record(
            "1. **One.** a\n2. **Two.** b\n\n### Gate algorithm\n\n1. Find the comments.\n"
            "2. Take the latest.\n3. Decide.\n"
        )
    )
    assert [p.id for p in read.list_points] == ["1", "2"]


def test_a_sub_section_s_steps_never_join_the_lead_s_numbering() -> None:
    """The steps restart, so they stay a list, though a later group continues the lead."""
    read = rp.read_points(
        _record(
            "1. **One.** a\n2. **Two.** b\n\n### Steps\n\n1. Find.\n2. Take.\n\n"
            "### More\n\n3. **Three.** c\n"
        )
    )
    assert [p.id for p in read.list_points] == ["1", "2", "3"]
    assert [p.title for p in read.list_points] == ["One", "Two", "Three"]


def test_a_sub_section_s_list_alone_holds_no_points() -> None:
    read = rp.read_points(
        _record("The decision, in prose.\n\n### Invocation\n\n1. Start.\n2. Review.\n3. Merge.\n")
    )
    assert read.list_points == () and not read.in_list_form


@pytest.mark.parametrize("word", ["S3", "IPv6", "OAuth2", "v2"])
def test_a_bold_word_ending_in_a_digit_is_no_point(word: str) -> None:
    """A bold label holds a point only with its em dash, so the list after a bold word
    that ends in a digit still holds the record's points."""
    read = rp.read_points(_record(f"**{word}** holds the blobs.\n\n1. **One.** a\n2. **Two.** b\n"))
    assert [p.id for p in read.list_points] == ["1", "2"]


def test_a_numbered_list_inside_a_bold_point_holds_no_points() -> None:
    read = rp.read_points(
        _record("**1. First.** It runs:\n\n1. a step\n2. another\n\n**2. Second.** More.\n")
    )
    assert [p.id for p in read.list_points] == ["1", "2"]
    assert {p.form for p in read.list_points} == {rp.ListForm.BOLD_NUMBER}


def test_once_a_record_has_point_headings_every_numbered_list_is_a_list() -> None:
    """COR-058 point 2; a numbered heading at another level than the points' is no point,
    and is not warned of (point 1)."""
    read = rp.read_points(
        _record(
            "### 1. First\n\n1. a step\n2. another\n\n"
            "#### 1. A numbered sub-heading\n\nIts own.\n\n### 2. Second\n\nTwo.\n"
        )
    )
    assert _ids(read) == ["1", "2"]
    assert read.list_points == ()
    assert read.misspelt == ()
    assert "1. a step" in _text(read, read.points[0])


# --- a stub and a retired id ------------------------------------------------------------

RETIRED = 'retired-points:\n  "3": ["4", "16"]\n  "5": []\n'


def _with_stubs(stub_three: str = "Its content is in points 4 and 16.") -> str:
    return _record(
        "### 1. First\n\nOne.\n\n### 3. Retired\n"
        f"{stub_three}\n\n### 4. Fourth\n\nFour.\n\n### 16. Sixteenth\n\nSixteen.\n\n"
        "### 5. Retired\nIts content is in no other point.\n",
        extra=RETIRED,
    )


def test_a_stub_is_no_point_and_a_retired_id_is_read_with_its_successors() -> None:
    read = rp.read_points(_with_stubs())
    assert _ids(read) == ["1", "4", "16"]  # the order on the page, numbers out of order
    assert [s.id for s in read.stubs] == ["3", "5"]
    assert all(stub.is_stub for stub in read.stubs)
    assert read.retired == {"3": ("4", "16"), "5": ()}
    assert read.retired_problems == ()
    assert read.ground("3") is None  # a retired id stands on nothing, whatever its stub says
    assert rp.hold_stubs(read) == ()


@pytest.mark.parametrize(
    ("successors", "sentence"),
    [
        ([], "Its content is in no other point."),
        (["7"], "Its content is in point 7."),
        (["7", "16"], "Its content is in points 7 and 16."),
        (["7", "12", "16"], "Its content is in points 7, 12 and 16."),
        (["D6"], "Its content is in point D6."),
    ],
)
def test_the_stub_sentence_is_written_from_the_entry(successors: list[str], sentence: str) -> None:
    assert rp.stub_sentence(successors) == sentence


def test_each_stub_is_held_to_its_entry_both_ways() -> None:
    """COR-058 point 6: a retired id with no stub, a stub whose id is not retired, and a
    stub whose sentence differs from its entry's."""
    text = _record(
        "### 1. First\n\nOne.\n\n### 3. Retired\nIts content is in point 4.\n\n"
        "### 7. Retired\nIts content is in no other point.\n\n### 4. Fourth\n\nFour.\n",
        extra=RETIRED,
    )
    read = rp.read_points(text)
    found = [(m.kind, m.id, m.expected, m.found) for m in rp.hold_stubs(read)]
    assert found == [
        (
            rp.StubMismatchKind.SENTENCE,
            "3",
            "Its content is in points 4 and 16.",
            "Its content is in point 4.",
        ),
        (rp.StubMismatchKind.NO_STUB, "5", None, None),
        (rp.StubMismatchKind.NOT_RETIRED, "7", None, "Its content is in no other point."),
    ]


def test_a_stub_s_sentence_is_compared_with_whitespace_folded() -> None:
    read = rp.read_points(_with_stubs("Its content is in\npoints 4  and 16."))
    assert rp.hold_stubs(read) == ()


@pytest.mark.parametrize(
    ("entry", "retired", "problems"),
    [
        ("retired-points:\n  6: [7, 16]\n", {"6": ("7", "16")}, ()),
        ('retired-points:\n  "D3": ["D7"]\n', {"D3": ("D7",)}, ()),
        ("retired-points: [6]\n", {}, ("is not a mapping",)),
        ('retired-points:\n  "6": "7"\n', {"6": ("7",)}, ("are not a list",)),
        ('retired-points:\n  "6": ["7", "x y"]\n', {"6": ("7",)}, ("are not a list",)),
        ('retired-points:\n  "six": []\n', {}, ("is no point id",)),
    ],
)
def test_retired_points_are_read_forgivingly(
    entry: str, retired: dict[str, tuple[str, ...]], problems: tuple[str, ...]
) -> None:
    """What cannot be read is named, for validation to fail on (COR-058 point 7)."""
    read = rp.read_points(_record("### 1. First\n\nOne.\n", extra=entry))
    assert read.retired == retired
    assert len(read.retired_problems) == len(problems)
    for found, expected in zip(read.retired_problems, problems, strict=True):
        assert expected in found


# --- misspelt headings ------------------------------------------------------------------


def test_a_heading_in_another_point_form_is_misspelt() -> None:
    """COR-058 point 1: a heading in the Decision that opens with a number or a label in
    another form, at the points' level. A label is letters then a number, so `v1` opens
    with one too."""
    read = rp.read_points(
        _record(
            "### 1. First\n\nOne.\n\n### 16 - Dashed\n\n### 5.1 Sub-numbered\n\n### D2: Colon\n\n"
            "### v1 scope: a label in another form\n\n### Lifecycle\n\n#### 7) Deeper\n"
        )
    )
    assert _ids(read) == ["1"]
    assert [h.title for h in read.misspelt] == [
        "16 - Dashed",
        "5.1 Sub-numbered",
        "D2: Colon",
        "v1 scope: a label in another form",
    ]


def test_without_a_point_heading_a_misspelt_heading_is_found_at_any_level() -> None:
    read = rp.read_points(_record("Prose.\n\n### 16 - Dashed\n\nText.\n"))
    assert read.points == () and read.level is None
    assert [h.title for h in read.misspelt] == ["16 - Dashed"]


def test_a_heading_in_fenced_code_is_no_point() -> None:
    read = rp.read_points(
        _record("### 1. First\n\n```markdown\n### 6. Retired\nIts content is in point 7.\n```\n")
    )
    assert _ids(read) == ["1"] and read.stubs == ()
    assert "### 6. Retired" in _text(read, read.points[0])


def test_a_record_without_a_decision_has_no_points() -> None:
    read = rp.read_points("---\nid: X\n---\n\n## Context\n\n### 1. Not a point\n")
    assert read.decision is None and read.points == () and read.list_points == ()


# --- what a point stands on -------------------------------------------------------------


def test_a_point_stands_on_its_section_and_what_makes_its_record_bind() -> None:
    """Its section; the record's status, supersession and title fields; its preamble and
    Summary; and the Decision's text outside every point and stub."""
    text = _record(
        "The lead every point refines.\n\n### What it carries\n\nGroup text.\n\n"
        "#### 1. First\n\nOne.\n\n#### 3. Retired\nIts content is in point 2.\n\n"
        "#### 2. Second\n\nTwo.\n\n### Lifecycle\n\nNeither a point nor a stub.\n",
        extra='supersedes: COR-001\nretired-points:\n  "3": ["2"]\n',
        before="Partially superseded by COR-999.\n\n## Summary\n\nIn plain terms.\n\n",
    )
    read = rp.read_points(text)
    ground = read.ground("2")
    assert ground is not None and ground.point.id == "2"
    assert ground.fields == {"status": "accepted", "supersedes": "COR-001", "title": "A record"}
    parts = [read.body.text_of(extent) for extent in ground.extents]
    assert parts == [
        "#### 2. Second\n\nTwo.\n",
        "Partially superseded by COR-999.\n",
        "## Summary\n\nIn plain terms.\n",
        "## Decision\n\nThe lead every point refines.\n\n### What it carries\n\nGroup text.\n",
        "### Lifecycle\n\nNeither a point nor a stub.\n",
    ]
    # Not the stub, not another point, not Context or Rationale, not `retired-points`.
    assert not any("Retired" in part or "One." in part or "Why." in part for part in parts)
    assert read.ground("9") is None


def test_a_record_with_first_level_sections_stands_no_point_on_its_context() -> None:
    """The preamble is the text before the record's first section, at the Decision's
    level; a body opening with its Decision has none."""
    text = "---\nid: X\n---\n\nPreamble.\n\n# Context\n\nWhy.\n\n# Decision\n\n## 1. One\n\nIt.\n"
    read = rp.read_points(text)
    ground = read.ground("1")
    assert ground is not None
    parts = [read.body.text_of(extent) for extent in ground.extents]
    assert parts == ["## 1. One\n\nIt.\n", "Preamble.\n", "# Decision\n"]
    opening = rp.read_points("---\nid: X\n---\n\n# Decision\n\nThe lead.\n\n## 1. One\n\nIt.\n")
    ground = opening.ground("1")
    assert ground is not None
    texts = [opening.body.text_of(extent) for extent in ground.extents]
    assert texts == ["## 1. One\n\nIt.\n", "# Decision\n\nThe lead.\n"]


def test_a_title_heading_opening_the_body_is_part_of_the_preamble() -> None:
    text = "---\nid: X\n---\n\n# COR-900: A record\n\nPreamble.\n\n## Decision\n\n### 1. One\n"
    read = rp.read_points(text)
    ground = read.ground("1")
    assert ground is not None
    assert read.body.text_of(ground.extents[1]) == "# COR-900: A record\n\nPreamble.\n"


def test_the_records_of_this_repository_read_with_no_finding_that_fails() -> None:
    """Every decision record here reads, every stub holds to its entry, and every
    `retired-points` reads. A misspelt heading is only warned of (COR-058 point 7)."""
    paths = [
        *REPO.glob(".pkit/decisions/core/*.md"),
        *REPO.glob(".pkit/decisions/project/*.md"),
        *REPO.glob("tech-docs/architecture/decisions/ADR-*.md"),
        *REPO.glob(".pkit/capabilities/*/decisions/DEC-*.md"),
    ]
    assert paths
    for path in paths:
        read = rp.read_points(path.read_text(encoding="utf-8"))
        assert read.front_matter_problem is None, path
        assert read.retired_problems == (), path
        assert rp.hold_stubs(read) == (), path
