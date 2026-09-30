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
  never an unclassified document — and by the held claim, which a page's field
  written into it names (living-docs DEC-001 point 1);
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


@pytest.fixture
def project(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    """Both capabilities, the analysis seeded, one planned revalidation recorded, and
    one page with no anchors beside them — all committed on `main`."""
    monkeypatch.delenv(BASE_ENV, raising=False)
    repo = prepare(make_adopter_repo(capabilities=("software-analysis", "living-docs")))
    seed(repo)
    stamped = run_script(
        repo,
        NEW,
        "revalidation",
        "report-redesign",
        "--change",
        "#50",
        "--trigger",
        "planned",
        "--outcome",
        "UC-002=holds",
        "--because",
        "UC-002=The redesign keeps the report's content; only its layout changes.",
    )
    assert stamped.returncode == 0, stamped.stderr
    repo.write({UNANCHORED_PAGE: "---\nreader: maintainer\nkind: signpost\n---\n\n# Guide\n"})
    repo.commit("the analysis, a revalidation record and a page", None)
    return repo


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

    # Which claim it is: the held one, named when a page's field is written into it.
    record = project.root / _record(project)
    record.write_text(
        record.read_text(encoding="utf-8").replace("---\n", "---\nreader: user\n", 1),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [sys.executable, str(project.root / LD_VALIDATE), "--json"],
        cwd=project.root,
        capture_output=True,
        text=True,
        check=False,
    )
    (finding,) = [f for f in json.loads(completed.stdout)["findings"] if f["severity"] == "error"]
    assert finding["location"] == f"{_record(project)}:/reader"
    assert (
        "is a document software-analysis holds in a folder it declares (COR-050 point 1)"
        in (finding["message"])
    )


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
