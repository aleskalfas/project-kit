"""Revalidation records under the internal root are claimed, not counted (#1130).

software-analysis declares its records' folder as a folder of held documents
(COR-050 point 1; software-analysis DEC-001 point 2). In a repository with both
software-analysis and living-docs installed — living-docs' internal-root place
enclosing the analysis — one committed record is:

- **no artefact of any place**: the whole-repository check, `pkit friction
  check --all` (the report `pkit friction debt` names), lists it neither as
  unanchored — while it does list the seeded use case that has no anchors —
  nor anywhere else, and the debt listing never names it;
- **claimed by its owner** in living-docs' summary — "of another component",
  never an unclassified document — whose fields living-docs never reads, so a
  page's field written into it fails nothing (living-docs DEC-001 point 1);
- **found by software-analysis' check** from the declaration of its held
  folder in the artefacts document, never by listing the folder.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit.cli import main
from project_kit.friction_check import BASE_ENV
from project_kit.friction_validate import validate_friction
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import ANALYSIS, NEW, RECORDS, prepare, run_script, seed
from tests.test_software_analysis_check import check, errors

LD_VALIDATE = Path(".pkit") / "capabilities" / "living-docs" / "scripts" / "validate.py"

#: A page under the internal root with no anchors: the unanchored measure's one entry.
UNANCHORED_PAGE = "tech-docs/guide.md"


# Slow: the seed and a record stamped, once per session; the first test to ask pays it.
def _record_a_revalidation(repo: AdopterRepo) -> None:
    """The analysis prepared and seeded, one revalidation recorded — an artefact a person
    decided was stale — and one page with no anchors beside them, all committed on
    `main`."""
    prepare(repo)
    seed(repo)
    stamped = run_script(
        repo,
        NEW,
        "revalidation",
        "report-redesign",
        "--change",
        "#50",
        "--trigger",
        "drift",
        "--outcome",
        "UC-002=analysis-stale",
        "--because",
        "UC-002=The redesign moved the report's layout on purpose, and step 2 now says so.",
        "--confirmed-by",
        "Sam",
    )
    assert stamped.returncode == 0, stamped.stderr
    repo.write({UNANCHORED_PAGE: "---\nreader: maintainer\nkind: signpost\n---\n\n# Guide\n"})
    repo.commit("the analysis, a revalidation record and a page", None)


@pytest.fixture
def project(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    """Both capabilities installed, and what `_record_a_revalidation` lays down."""
    monkeypatch.delenv(BASE_ENV, raising=False)
    return make_adopter_repo(
        capabilities=("software-analysis", "living-docs"), prepare=_record_a_revalidation
    )


def _json(*args: str) -> dict[str, Any]:
    result = CliRunner().invoke(main, [*args, "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def _record(repo: AdopterRepo) -> str:
    (record,) = sorted(p.relative_to(repo.root).as_posix() for p in (repo.root / RECORDS).iterdir())
    return record


def test_a_record_is_held_by_its_owner_and_walked_by_no_place(project: AdopterRepo) -> None:
    record = _record(project)
    document = _json("friction", "artefacts")
    (folder,) = document["held"]
    assert (folder["source"], folder["path"], folder["files"], folder["skipped"]) == (
        "capability:software-analysis",
        RECORDS,
        [record],
        None,
    )
    (held,) = document["held_files"]
    assert (held["path"], held["held"]) == (record, 0)
    # living-docs' internal-root place matches the record, and left it out of its walk.
    (place,) = [document["places"][i] for i in held["places"]]
    assert (place["source"], place["location"]["name"]) == (
        "capability:living-docs",
        "internal-root",
    )
    assert record not in [f["path"] for f in document["files"]]
    assert record not in [a["path"] for a in document["artefacts"]]
    assert validate_friction(project.root).errors == ()


def test_the_whole_repository_check_and_the_debt_never_name_a_record(
    project: AdopterRepo,
) -> None:
    record = _record(project)
    report = _json("friction", "check", "--all")
    # The measure is read: the page the fixture keeps without anchors is listed.
    unanchored = report["measures"]["unanchored"]
    assert unanchored == [UNANCHORED_PAGE]
    assert record not in unanchored
    assert all(record not in json.dumps(a) for a in report["artefacts"])
    debt = _json("friction", "debt")
    assert record not in json.dumps(debt)


def test_living_docs_counts_a_record_as_another_component_s(project: AdopterRepo) -> None:
    completed = subprocess.run(
        [sys.executable, str(project.root / LD_VALIDATE), "--json"],
        cwd=project.root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    (not_pages,) = [
        line for line in json.loads(completed.stdout)["summary"] if line.startswith("not pages:")
    ]
    # The seeded analysis — the actors, two use cases and a journey — and the record.
    assert len(list((project.root / ANALYSIS).rglob("*.md"))) == 5
    assert "5 of another component" in not_pages
    assert "0 unclassified document(s)" in not_pages

    # Its fields are its holder's: a page's fields written into it are never read.
    record = project.root / _record(project)
    record.write_text(
        record.read_text(encoding="utf-8").replace(
            "---\n", "---\nreader: user\nkind: signpost\n", 1
        ),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [sys.executable, str(project.root / LD_VALIDATE), "--json"],
        cwd=project.root,
        capture_output=True,
        text=True,
        check=False,
    )
    document = json.loads(completed.stdout)
    assert [f for f in document["findings"] if f["severity"] == "error"] == []
    (not_pages,) = [line for line in document["summary"] if line.startswith("not pages:")]
    assert "5 of another component" in not_pages


def test_software_analysis_finds_its_records_from_the_artefacts_document(
    project: AdopterRepo,
) -> None:
    document = check(project)
    assert document["summary"][0].endswith("; 1 revalidation record(s).")
    assert errors(document) == []


@pytest.mark.parametrize(
    ("args", "tail"),
    [
        (("revalidate", "{record}", "--outcome", "updated", "--yes"), " Nothing was written."),
        (
            ("defer", "{record}", "--anchor", "path:src", "--reason", "later", "--yes"),
            " Nothing was written.",
        ),
        (("record-status", "{record}", "--yes"), " Nothing was written."),
        (("explain", "{record}"), " There is nothing to explain."),
    ],
)
def test_a_writer_or_explain_named_a_record_says_which_capability_holds_it(
    project: AdopterRepo, args: tuple[str, ...], tail: str
) -> None:
    """A record is no artefact, so there is no block to write or friction to explain;
    the command says whose document it is and where that is declared, rather than
    that no artefact in the places is named so (COR-050 point 1)."""
    record = _record(project)
    result = CliRunner().invoke(main, ["friction", *(a.format(record=record) for a in args)])
    assert result.exit_code == 1, result.output
    assert result.output == (
        f"Error: {record} is held by software-analysis — in its held folder 'revalidations', "
        f".pkit/capabilities/software-analysis/package.yaml:/friction/held/0 — and is not an "
        f"artefact: a held document carries no friction block (COR-050 point 1).{tail}\n"
    )
