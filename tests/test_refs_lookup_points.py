"""The record lookup's points and anchors (software-analysis DEC-001 point 13; COR-058).

`pkit refs lookup` resolves a point of a record, `COR-050#14`, to its record's file and
the anchor a repository host gives its heading, reading the record's points as
validation reads them (`record_points`). A rule resolves to its place and its heading's
anchor. Several citations are answered in one call, and `--json` answers each as data,
which a capability's script reads instead of looking for a record itself.

The host's anchor (`document_parts.host_anchors`) is GitHub's: the heading's text as it
renders, in lower case, every character but letters, digits, underscores, spaces and
hyphens dropped, each space a hyphen, and a repeat numbered.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import document_parts, refs
from project_kit.cli import main

REPO = Path(__file__).resolve().parents[1]


# --- the host's anchor ------------------------------------------------------------------------


def _anchors(*titles: str) -> tuple[str, ...]:
    body = "\n\n".join(f"### {title}" for title in titles) + "\n"
    return document_parts.host_anchors(document_parts.Body.read(body).headings)


@pytest.mark.parametrize(
    ("title", "anchor"),
    [
        # A numbered point: its full stop dropped, each space a hyphen.
        ("14. Project settings", "14-project-settings"),
        # A labelled point: the em dash dropped, the spaces around it two hyphens.
        ("D1 — Surface changes are declared", "d1--surface-changes-are-declared"),
        # A code span's text kept as written, its underscore with it.
        ("3. The `run_rules` table", "3-the-run_rules-table"),
        # Emphasis dropped; an underscore inside a word kept.
        (
            "2. Enforced edges are *derived*, _not_ annotated",
            "2-enforced-edges-are-derived-not-annotated",
        ),
        ("5. A snake_case name", "5-a-snake_case-name"),
        # A link's text kept, its target dropped; a bracketed citation's text kept.
        ("4. Deferred ([COR-007](../COR-007.md))", "4-deferred-cor-007"),
        ("2. Per [demo:DEC-002-three-layers]", "2-per-demodec-002-three-layers"),
        # Symbols and other punctuation dropped; letters of any script kept, lowered.
        ("2. Pins ≠ me → re-exec `uvx`", "2-pins--me--re-exec-uvx"),
        ("7. Žluťoučký kůň", "7-žluťoučký-kůň"),
        # An HTML tag dropped, an entity read, then dropped as a symbol.
        ("1. A <code>tag</code> &amp; more", "1-a-tag--more"),
    ],
)
def test_the_host_anchor_is_the_rendered_text_slugged_as_github_does(
    title: str, anchor: str
) -> None:
    assert _anchors(title) == (anchor,)


def test_a_repeated_anchor_takes_a_number_and_differs_from_the_slug() -> None:
    """GitHub numbers a heading whose anchor an earlier heading gives, from 1; the
    backbone's own slug numbers none and drops an underscore (COR-050 point 2)."""
    assert _anchors("Notes", "Notes", "Other", "Notes") == ("notes", "notes-1", "other", "notes-2")
    assert document_parts.heading_slug("3. The `run_rules` table") == "3-the-runrules-table"


# --- the lookup -------------------------------------------------------------------------------

FRONT = "---\nid: {id}\ntitle: A record\nstatus: accepted\ndate: 2026-10-21\n{extra}---\n\n"


def _record(root: Path, rel: str, decision: str, *, extra: str = "") -> None:
    record_id = Path(rel).name.split("-", 2)
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        FRONT.format(id="-".join(record_id[:2]), extra=extra)
        + "## Context\n\nWhy.\n\n## Decision\n\n**The choice.**\n\n"
        + decision
        + "\n## Rationale\n\n### 2. Not a point\n\nA heading outside the Decision.\n",
        encoding="utf-8",
    )


@pytest.fixture
def records(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A core record with numbered points and a stub, a project record with labelled
    points, and a core record whose points are still a list."""
    for ns in ("core", "project"):
        (tmp_path / ".pkit" / "decisions" / ns).mkdir(parents=True)
    _record(
        tmp_path,
        ".pkit/decisions/core/COR-900-anchors.md",
        "### 1. Anchors name parts\n\nText.\n\n### 2. Retired\nIts content is in point 3.\n\n"
        "### 3. The `run_rules` *table*\n\nText.\n",
        extra='retired-points:\n  "2": ["3"]\n',
    )
    _record(
        tmp_path,
        ".pkit/decisions/project/PRJ-002-versions.md",
        "### D1 — Surface changes are declared, not applied\n\nText.\n\n"
        "### D3 — Release-driven\n\nText.\n",
    )
    _record(
        tmp_path, ".pkit/decisions/core/COR-901-listed.md", "1. **First.** Text.\n2. **Second.**\n"
    )
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _found(root: Path, *citations: str) -> list[tuple[str | None, str | None, str | None]]:
    return [(f.path, f.anchor, f.problem) for f in refs.lookup_citations(root, citations)]


def test_a_point_resolves_to_its_record_and_its_heading_s_anchor(records: Path) -> None:
    core = ".pkit/decisions/core/COR-900-anchors.md"
    assert _found(records, "COR-900", "COR-900#1", "COR-900#3", "PRJ-002#D1") == [
        (core, None, None),
        (core, "1-anchors-name-parts", None),
        (core, "3-the-run_rules-table", None),
        (
            ".pkit/decisions/project/PRJ-002-versions.md",
            "d1--surface-changes-are-declared-not-applied",
            None,
        ),
    ]


def test_a_retired_point_leads_to_its_stub_and_a_listed_one_to_its_record(records: Path) -> None:
    """A retired id's stub says where its content went (COR-058 point 4); a record whose
    points are a list gives a point no heading, so no anchor and no problem."""
    assert _found(records, "COR-900#2", "COR-901#1") == [
        (".pkit/decisions/core/COR-900-anchors.md", "2-retired", None),
        (".pkit/decisions/core/COR-901-listed.md", None, None),
    ]


def test_what_resolves_to_nothing_says_why(records: Path) -> None:
    """A point its record neither holds nor retires names its record and a problem; a
    record the lookup does not find names none. A heading outside the Decision is no
    point."""
    assert _found(records, "COR-900#9", "PRJ-002#2", "COR-999#1") == [
        (".pkit/decisions/core/COR-900-anchors.md", None, "COR-900 holds no point 9"),
        (".pkit/decisions/project/PRJ-002-versions.md", None, "PRJ-002 holds no point 2"),
        (None, None, "no record matches 'COR-999'"),
    ]


def test_a_rule_resolves_to_its_place_and_its_heading_s_anchor() -> None:
    """In this repository, a rule of a project set and a method rule cited with its
    component: each its set's file and the anchor of its heading, `### RS-… — Title`."""
    found = refs.lookup_citations(REPO, ["RS-WRITE-005", "software-analysis:RS-SAN-001"])
    assert [f.path for f in found] == [
        "tech-docs/rule-sets/writing.md",
        ".pkit/capabilities/software-analysis/rule-sets/san.md",
    ]
    assert found[0].anchor is not None and found[0].anchor.startswith("rs-write-005--")
    assert found[1].anchor is not None and found[1].anchor.startswith("rs-san-001--")
    assert found[0].locations == ("tech-docs/rule-sets/writing.md#RS-WRITE-005",)


def test_the_command_answers_several_citations_and_as_data(records: Path) -> None:
    """Plain, each location on a line, and exit 1 naming what does not resolve; with
    `--json`, one object for each citation, in order, and exit 0."""
    runner = CliRunner()
    plain = runner.invoke(main, ["refs", "lookup", "COR-900", "PRJ-002#D3"])
    assert plain.exit_code == 0, plain.output
    assert plain.output.splitlines() == [
        ".pkit/decisions/core/COR-900-anchors.md",
        ".pkit/decisions/project/PRJ-002-versions.md#d3--release-driven",
    ]
    failed = runner.invoke(main, ["refs", "lookup", "COR-900", "COR-900#9"])
    assert failed.exit_code == 1
    assert "COR-900 holds no point 9." in failed.output
    as_json = runner.invoke(main, ["refs", "lookup", "--json", "COR-900#1", "COR-999"])
    assert as_json.exit_code == 0, as_json.output
    assert json.loads(as_json.output) == [
        {
            "citation": "COR-900#1",
            "locations": [".pkit/decisions/core/COR-900-anchors.md#1-anchors-name-parts"],
            "path": ".pkit/decisions/core/COR-900-anchors.md",
            "anchor": "1-anchors-name-parts",
            "problem": None,
            "received": False,
        },
        {
            "citation": "COR-999",
            "locations": [],
            "path": None,
            "anchor": None,
            "problem": "no record matches 'COR-999'",
            "received": False,
        },
    ]
