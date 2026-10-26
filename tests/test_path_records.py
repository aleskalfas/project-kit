"""The accepted records a path's anchors lead to (#2165).

`pkit refs records-for PATH...` goes from a path to the accepted records the anchors tie
to it, the other way from `pkit refs lookup`, which goes from an id to its file. It reads
the one artefact discovery (COR-050 point 1) and declares nothing new. Its ties, each read
from anchors COR-050 point 2 already decides, come in two kinds:

- **direct**: a record a place holds whose own path anchor matches the path, which ties
  itself whole; and each record the artefact at the path anchors, whole or by point;
- **through an artefact** whose path anchor matches the path: each record it anchors. An
  artefact's path anchors and record anchors are not paired, so these are listed under
  the artefact, the one resting on the fewest records first.

A path anchor matches as both friction checks match it, and a path under
`friction.exclude` is one no path anchor stands on (COR-050 point 7). An artefact the
project receives by sync ties nothing, and neither does a path anchor of a record that is
not accepted. Only accepted records are listed, a superseded one by the records that
replace it, the project's own first. Core rule 22 tells an agent to run it before it
changes files, and the rules README lists the rule's section.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit import path_records as pr
from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.friction_documents import (
    ADR,
    ADR_DECISION,
    ADR_OVERLAY,
    CONFIG,
    POINTED,
    SOURCE,
    document,
    friction_config,
    pointed_record,
)

REPO = Path(__file__).resolve().parent.parent

ENGINE = "src/core/engine.py"
CLI = "src/cli/main.py"
NOTES = "docs/notes.md"
GUIDE = "docs/guide.md"
PAGE = "docs/page.md"
DRAFT = "docs/architecture/decisions/ADR-008-draft.md"
PROPOSED = ".pkit/decisions/project/PRJ-901-proposed.md"
SUPERSEDED = ".pkit/decisions/project/PRJ-902-superseded.md"
SUCCESSOR = ".pkit/decisions/project/PRJ-903-successor.md"
COR_050 = ".pkit/decisions/core/COR-050-anchors-and-friction.md"
COR_004 = ".pkit/decisions/core/COR-004-cli-surface.md"
EVIDENCE_DEC = ".pkit/capabilities/evidence/decisions/DEC-003-validation-model.md"
COR_050_TITLE = "Artefacts declare what makes them true, and drift is detected as friction"

#: A method rule set, which arrives in an adopter by sync: its rule anchors the engine and
#: COR-004, and ties nothing, since it was written for the methodology's own tree.
RECEIVED_RULES = """---
rule-set: XS
version: 1.0.0
rules:
  RS-XS-001:
    status: accepted
    pkit:
      friction:
        anchors:
          path: [src/core/**]
          record: [COR-004]
---

# Rules

## RS-XS-001 — Rule one

The statement of RS-XS-001.
"""


def _record(record_id: str, status: str, *, supersedes: str | None = None) -> str:
    text = pointed_record(status=status, title=f"A {status} record").replace("PRJ-900", record_id)
    if supersedes is None:
        return text
    return text.replace(
        f'"status": "{status}",', f'"status": "{status}",\n  "supersedes": "{supersedes}",'
    )


@pytest.fixture
def adopter(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    """A project place `docs` holding an ADR that anchors the engine, a proposed ADR that
    does too, two documents that anchor code and records, and a page that anchors records
    and no path."""
    repo = make_adopter_repo(capabilities=("evidence",))
    repo.write(
        {
            CONFIG: friction_config(places=("docs",), exclude=["src/vendor/**"]),
            **SOURCE,
            **ADR_OVERLAY,
            POINTED: pointed_record(),
            PROPOSED: _record("PRJ-901", "proposed"),
            SUPERSEDED: _record("PRJ-902", "superseded"),
            SUCCESSOR: _record("PRJ-903", "accepted", supersedes="PRJ-902"),
            ADR: document(
                "ADR-007",
                anchors={"path": ["src/core/**"], "record": ["PRJ-900#2"]},
                title="A recorded decision",
                status="accepted",
                body=ADR_DECISION,
            ),
            DRAFT: document(
                "ADR-008",
                anchors={"path": ["src/core/**"], "record": ["COR-004"]},
                title="A drafted decision",
                status="proposed",
                body=ADR_DECISION,
            ),
            NOTES: document(
                "notes",
                anchors={
                    "path": ["src/core/**", ENGINE],
                    "record": [
                        "PRJ-900#3",
                        "PRJ-900#1",
                        "COR-050",
                        "PRJ-901",
                        "PRJ-902",
                        "PRJ-999",
                    ],
                },
            ),
            GUIDE: document(
                "guide",
                anchors={
                    "path": ["src/**"],
                    "record": ["PRJ-900", "evidence:DEC-003-validation-model#1"],
                },
            ),
            PAGE: document("page", anchors={"record": ["COR-004#2", "PRJ-900#3"]}),
            ".pkit/rule-sets/xs.md": RECEIVED_RULES,
        }
    )
    return repo


def _one(root: Path, path: str) -> pr.PathRecords:
    (found,) = pr.records_for(root, [path]).paths
    return found


Named = tuple[str, tuple[str, ...], str | None]


def _direct(found: pr.PathRecords) -> dict[str, list[tuple[str, str, str | None, tuple[str, ...]]]]:
    return {
        record.id: [(t.how, t.artefact, t.anchor, t.points) for t in ties]
        for record, ties in found.direct
    }


def _through(found: pr.PathRecords) -> list[tuple[str, str, list[Named]]]:
    return [
        (each.artefact, each.anchor, [(t.record.id, t.points, t.in_place_of) for t in each.ties])
        for each in found.through
    ]


# --- the ties ---------------------------------------------------------------------------------


def test_a_record_that_anchors_the_path_is_tied_to_it_directly(adopter: AdopterRepo) -> None:
    """ADR-007 anchors the engine, so it ties itself, whole. The proposed ADR-008 anchors
    it too and ties nothing: a draft's anchors bind nothing."""
    assert _direct(_one(adopter.root, ENGINE)) == {
        "ADR-007": [("record", ADR, "src/core/**", ())],
    }


def test_the_artefacts_that_anchor_the_path_list_the_records_they_rest_on(
    adopter: AdopterRepo,
) -> None:
    """Each artefact whose path anchor matches, by the first such anchor, with the accepted
    records it anchors, whole or by point: the one resting on the fewest records first.
    The proposed, the missing and the received rule's records are left out, and the
    superseded PRJ-902 is listed by PRJ-903, which replaces it."""
    assert _through(_one(adopter.root, ENGINE)) == [
        (ADR, "src/core/**", [("PRJ-900", ("2",), None)]),
        (GUIDE, "src/**", [("PRJ-900", (), None), ("evidence:DEC-003", ("1",), None)]),
        (
            NOTES,
            "src/core/**",
            [("PRJ-900", ("1", "3"), None), ("PRJ-903", (), "PRJ-902"), ("COR-050", (), None)],
        ),
    ]


def test_the_artefact_at_the_path_ties_the_records_it_anchors_directly(
    adopter: AdopterRepo,
) -> None:
    """The page anchors no path, so only a change to the page itself reaches its records."""
    found = _one(adopter.root, PAGE)
    assert _direct(found) == {
        "PRJ-900": [("artefact", PAGE, None, ("3",))],
        "COR-004": [("artefact", PAGE, None, ("2",))],
    }
    assert found.through == ()


def test_a_record_s_own_file_leads_to_the_records_it_anchors(adopter: AdopterRepo) -> None:
    assert _direct(_one(adopter.root, ADR)) == {"PRJ-900": [("artefact", ADR, None, ("2",))]}


def test_each_record_gives_its_title_its_file_and_whether_it_arrives_by_sync(
    adopter: AdopterRepo,
) -> None:
    """In an adopter, the core records and a kit-shipped capability's arrive by sync."""
    records = {
        t.record.id: t.record for each in _one(adopter.root, ENGINE).through for t in each.ties
    }
    assert records["PRJ-900"] == pr.Record("PRJ-900", "A pointed record", POINTED, False)
    assert records["PRJ-903"] == pr.Record("PRJ-903", "A accepted record", SUCCESSOR, False)
    assert records["evidence:DEC-003"] == pr.Record(
        "evidence:DEC-003",
        "Validation rules — what the validator checks and when it fails",
        EVIDENCE_DEC,
        True,
    )
    assert records["COR-050"] == pr.Record("COR-050", COR_050_TITLE, COR_050, True)


# --- what the anchors cannot reach ------------------------------------------------------------


def test_a_path_under_an_excluded_path_is_reached_by_no_path_anchor(adopter: AdopterRepo) -> None:
    """COR-050 point 7: an excluded path is ignored for anchoring, so the guide's `src/**`
    stands on nothing in it."""
    found = _one(adopter.root, "src/vendor/lib.py")
    assert found.excluded_by == "src/vendor/**"
    assert found.ties == ()


def test_a_file_not_yet_written_is_reached_by_the_globs_that_cover_it(
    adopter: AdopterRepo,
) -> None:
    assert not (adopter.root / "src/core/new.py").exists()
    found = _one(adopter.root, "src/core/new.py")
    assert [r.id for r, _ties in found.direct] == ["ADR-007"]
    assert [t.artefact for t in found.through] == [ADR, GUIDE, NOTES]


def test_a_path_no_anchor_reaches_finds_nothing(adopter: AdopterRepo) -> None:
    assert _one(adopter.root, "README.md").ties == ()


def test_several_paths_are_answered_in_the_order_given(adopter: AdopterRepo) -> None:
    answer = pr.records_for(adopter.root, [CLI, ENGINE])
    assert [f.path for f in answer.paths] == [CLI, ENGINE]
    assert _through(answer.paths[0]) == [
        (GUIDE, "src/**", [("PRJ-900", (), None), ("evidence:DEC-003", ("1",), None)])
    ]


def test_the_answer_counts_the_anchored_artefacts_and_names_the_unreadable(
    adopter: AdopterRepo,
) -> None:
    """ADR-007, ADR-008, the notes, the guide and the page carry anchors; the received rule
    is not counted. A file whose front matter does not parse is named, since its anchors
    were not read."""
    adopter.write({"docs/broken.md": "---\nid: [broken\n---\n\nBody.\n"})
    answer = pr.records_for(adopter.root, [ENGINE])
    assert answer.anchored == 5
    assert answer.unreadable == ("docs/broken.md",)


def test_a_project_that_anchors_nothing_says_so(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    repo.write({CONFIG: friction_config(places=("docs",)), **SOURCE})
    result = CliRunner().invoke(main, ["refs", "records-for", ENGINE])
    assert result.exit_code == 0, result.output
    assert result.output.splitlines()[0] == (
        "No artefact in this project carries anchors, so no path leads to a record."
    )


# --- the path given ---------------------------------------------------------------------------


@pytest.mark.parametrize("given", [ENGINE, f"./{ENGINE}", "src//core/engine.py"])
def test_a_path_is_read_from_the_repository_root(adopter: AdopterRepo, given: str) -> None:
    assert pr.repository_path(adopter.root, given, adopter.root) == ENGINE


def test_a_relative_path_is_read_from_where_the_command_runs(adopter: AdopterRepo) -> None:
    assert pr.repository_path(adopter.root, "engine.py", adopter.root / "src" / "core") == ENGINE
    assert pr.repository_path(adopter.root, str(adopter.root / ENGINE), adopter.root) == ENGINE


@pytest.mark.parametrize(
    ("given", "problem"),
    [
        ("src/core", "names a folder"),
        ("src/new_pkg/", "names a folder"),
        (".", "names a folder"),
        ("../elsewhere.py", "lies outside the repository"),
        ("/elsewhere.py", "lies outside the repository"),
    ],
)
def test_a_folder_or_a_path_outside_the_repository_is_refused(
    adopter: AdopterRepo, given: str, problem: str
) -> None:
    with pytest.raises(ValueError, match=problem):
        pr.repository_path(adopter.root, given, adopter.root)


# --- the command ------------------------------------------------------------------------------


def _run(*args: str) -> Any:
    return CliRunner().invoke(main, ["refs", "records-for", *args])


def test_the_command_lists_the_direct_ties_then_the_artefacts(adopter: AdopterRepo) -> None:
    result = _run(ENGINE)
    assert result.exit_code == 0, result.output
    assert result.output.splitlines() == [
        f"{ENGINE}: 1 record tied directly, 3 artefacts anchoring it",
        "  Tied directly:",
        f"    ADR-007  A recorded decision  ({ADR})",
        "      whole, by its own anchor src/core/**",
        "  Through the artefacts that anchor it, the narrowest first:",
        f"    {ADR}, by src/core/**, rests on 1 record:",
        "      PRJ-900 point 2",
        f"    {GUIDE}, by src/**, rests on 2 records:",
        "      PRJ-900; evidence:DEC-003 point 1",
        f"    {NOTES}, by src/core/**, rests on 3 records:",
        "      PRJ-900 points 1 and 3; PRJ-903 (in place of PRJ-902); COR-050",
    ]


def test_the_command_names_the_artefact_at_the_path(adopter: AdopterRepo) -> None:
    result = _run(PAGE)
    assert result.exit_code == 0, result.output
    assert result.output.splitlines() == [
        f"{PAGE}: 2 records tied directly, 0 artefacts anchoring it",
        "  Tied directly:",
        f"    PRJ-900  A pointed record  ({POINTED})",
        f"      point 3, by {PAGE}, the artefact at this path",
        f"    COR-004  CLI command surface  ({COR_004}, received by sync)",
        f"      point 2, by {PAGE}, the artefact at this path",
    ]


def test_the_command_says_what_an_empty_answer_means(adopter: AdopterRepo) -> None:
    result = _run(CLI, "README.md", "src/vendor/lib.py")
    assert result.exit_code == 0, result.output
    assert result.output.splitlines() == [
        f"{CLI}: 0 records tied directly, 1 artefact anchoring it",
        "  No record is tied to it directly.",
        "  Through the artefacts that anchor it, the narrowest first:",
        f"    {GUIDE}, by src/**, rests on 2 records:",
        "      PRJ-900; evidence:DEC-003 point 1",
        "README.md: 0 records tied directly, 0 artefacts anchoring it",
        "  No anchor ties an accepted record to this path. That is no sign that none governs it.",
        "src/vendor/lib.py: 0 records tied directly, 0 artefacts anchoring it",
        "  It lies under src/vendor/**, which friction.exclude leaves out, so no path anchor"
        " stands on it.",
        "  No anchor ties an accepted record to this path. That is no sign that none governs it.",
    ]


def test_the_command_answers_as_data(adopter: AdopterRepo) -> None:
    result = _run("--json", PAGE, CLI, "src/vendor/lib.py")
    assert result.exit_code == 0, result.output
    page_tie = {"how": "artefact", "artefact": PAGE, "anchor": None, "in_place_of": None}
    assert json.loads(result.output) == {
        "schema_version": 1,
        "anchored": 5,
        "unreadable": [],
        "paths": [
            {
                "path": PAGE,
                "excluded_by": None,
                "direct": [
                    {
                        "id": "PRJ-900",
                        "title": "A pointed record",
                        "path": POINTED,
                        "received": False,
                        "ties": [{**page_tie, "points": ["3"]}],
                    },
                    {
                        "id": "COR-004",
                        "title": "CLI command surface",
                        "path": COR_004,
                        "received": True,
                        "ties": [{**page_tie, "points": ["2"]}],
                    },
                ],
                "through": [],
            },
            {
                "path": CLI,
                "excluded_by": None,
                "direct": [],
                "through": [
                    {
                        "artefact": GUIDE,
                        "anchor": "src/**",
                        "records": [
                            {
                                "id": "PRJ-900",
                                "title": "A pointed record",
                                "path": POINTED,
                                "received": False,
                                "points": [],
                                "in_place_of": None,
                            },
                            {
                                "id": "evidence:DEC-003",
                                "title": "Validation rules — what the validator checks and when"
                                " it fails",
                                "path": EVIDENCE_DEC,
                                "received": True,
                                "points": ["1"],
                                "in_place_of": None,
                            },
                        ],
                    }
                ],
            },
            {
                "path": "src/vendor/lib.py",
                "excluded_by": "src/vendor/**",
                "direct": [],
                "through": [],
            },
        ],
    }


@pytest.mark.parametrize("given", ["src/core", "../elsewhere.py"])
def test_the_command_refuses_a_folder_or_a_path_outside_with_a_usage_error(
    adopter: AdopterRepo, given: str
) -> None:
    result = _run(given)
    assert result.exit_code == 2
    assert repr(given) in result.output


def test_the_command_needs_a_path(adopter: AdopterRepo) -> None:
    assert _run().exit_code == 2


def test_outside_a_project_it_exits_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = _run(ENGINE)
    assert result.exit_code == 1
    assert "not in a project tree" in result.output


def test_a_configuration_that_cannot_be_read_exits_1(adopter: AdopterRepo) -> None:
    adopter.write({CONFIG: "friction: [places\n"})
    result = _run(ENGINE)
    assert result.exit_code == 1
    assert "the configuration .pkit/project/config.yaml" in result.output


# --- in this repository -----------------------------------------------------------------------


def test_in_this_repository_a_module_leads_to_the_page_that_anchors_it() -> None:
    """The decisions README anchors this module, so a change here leads to it, with COR-050's
    points 1, 2 and 7 among the records it rests on. Where the methodology is authored, no
    record arrives by sync."""
    module = "src/project_kit/path_records.py"
    found = _one(REPO, module)
    (readme,) = [t for t in found.through if t.artefact == ".pkit/decisions/README.md"]
    assert readme.anchor == module
    assert ("COR-050", ("1", "2", "7")) in [(t.record.id, t.points) for t in readme.ties]
    assert not any(t.record.received for t in found.ties)


# --- the rule ---------------------------------------------------------------------------------

CORE_RULES = REPO / ".pkit" / "rules" / "core.md"
RULES_README = REPO / ".pkit" / "rules" / "README.md"
DECISIONS_README = REPO / ".pkit" / "decisions" / "README.md"
SECTION = "## Before changing files"
README_SECTION = "## Finding the records a path leads to"


def _rule_22() -> str:
    text = CORE_RULES.read_text(encoding="utf-8")
    section = text.split(f"\n{SECTION}\n", 1)[1].split("\n## ", 1)[0]
    paragraphs = [p.strip() for p in section.split("\n\n") if p.strip().startswith("22. ")]
    assert len(paragraphs) == 1, "rule 22 is not the one numbered rule of its section"
    return paragraphs[0]


def test_rule_22_tells_an_agent_to_run_the_lookup_before_changing_files() -> None:
    rule = _rule_22()
    assert rule.startswith(
        "22. **When you change the system, read first the accepted records its files lead to.**"
    )
    assert "`pkit refs records-for`" in rule
    assert "tied to them directly" in rule
    assert "read that artefact" in rule


def test_rule_22_cites_the_readme_that_holds_its_rationale_and_the_issue() -> None:
    rule = _rule_22()
    assert '"Finding the records a path leads to"' in rule
    assert "https://github.com/aleskalfas/project-kit/issues/2165" in rule
    assert README_SECTION in DECISIONS_README.read_text(encoding="utf-8")


def test_rule_22_stands_after_rule_21_and_before_the_rationale() -> None:
    text = CORE_RULES.read_text(encoding="utf-8")
    assert text.index("\n21. ") < text.index(f"\n{SECTION}\n") < text.index("\n## Where rationale")


def test_the_rules_readme_lists_the_section() -> None:
    text = RULES_README.read_text(encoding="utf-8")
    section = text.split("\n## What goes in `core.md`\n", 1)[1].split("\n## ", 1)[0]
    assert "Seven categories:" in section
    assert "- **Before changing files** — " in section
