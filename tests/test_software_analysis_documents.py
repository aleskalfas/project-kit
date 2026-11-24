"""Each document a software-analysis command prints for a program holds its contract
(ADR-097 point 7).

Each test runs the command's script in the test's own process, its `pkit` calls answered
there too (`tests/analysis_repo.py`, `run_in_process`), from the repositories the command's
own tests build, and holds what it prints to the contract pinned here with
`tests/document_contracts.py`. A key or a value that goes, or comes back, fails until the
same change updates the pin, beside the changeset that declares the break.
`tests/test_capability_documents.py` holds the ratchet over every capability's commands.

The commands' validator, `validate`, and their fillers print for the backbone's engines,
whose records set those documents (ADR-097 point 1), so they are not here.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from project_kit.friction_check import BASE_ENV
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo, Prepare
from tests.analysis_repo import (
    CONSTRAINTS,
    GLOSSARY,
    MAIN,
    NUMBERS,
    OBLIGATION,
    QUALITY,
    SA,
    fingerprint,
    load_lib,
    prepare,
    prepare_seeded,
    requirement,
    run_in_process,
)
from tests.document_contracts import Contract, Form, check
from tests.test_software_analysis_numbering import _piloted, free, pilot_freed
from tests.test_software_analysis_numbers import _main_took_ours
from tests.test_software_analysis_obligation import QUICK, TEXTS
from tests.test_software_analysis_pointers import NEW, _designed, record, sha
from tests.test_software_analysis_requirement_lists import (
    FIRST_RUN,
    READ_REPORT,
    RUN_SUITE,
    _lists,
    _with_requirements,
)
from tests.test_software_analysis_resolver import RUN, _flag
from tests.test_software_analysis_uses import USES, _terms, _two

CHECK_POINTERS = SA / "scripts" / "check-pointers.py"
DIAGRAM = SA / "scripts" / "diagram.py"
MET_BY = SA / "scripts" / "met-by.py"
PROPOSE = SA / "scripts" / "propose.py"

resolve, findings = load_lib("resolve", "findings")


@pytest.fixture(autouse=True)
def no_check_base_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """A developer's own `$PKIT_CHECK_BASE` must not decide what a document holds."""
    monkeypatch.delenv(BASE_ENV, raising=False)


def _printed(repo: AdopterRepo, script: Path, *args: str) -> dict[str, Any]:
    """The document `script` prints with `args` and `--json`, whatever its exit code: a
    check that fails prints its document too."""
    done = run_in_process(repo, script, *args, "--json")
    assert done.stdout, done.stderr
    document = json.loads(done.stdout)
    assert isinstance(document, dict), done.stdout
    return document


def _repo(make_adopter_repo: MakeAdopterRepo, root: Path, then: Prepare = prepare) -> AdopterRepo:
    """A copy, at `root`, of the adopter `then` builds once per session, as the command's
    own tests' fixtures give it (`installed`)."""
    return make_adopter_repo(capabilities=("software-analysis",), prepare=then, root=root)


#: A finding, as the checks' findings document gives it (ADR-058 point 1).
_FINDING = Form(keys={"severity": "str", "location": "str", "message": "str"})
_SEVERITIES = frozenset({"error", "warning", "report"})


def _findings_keys() -> dict[str, str]:
    return {
        "summary": "list",
        "summary[]": "str",
        "findings": "list",
        "findings[]": "object",
    }


# --- `pkit analysis check-numbers --json` --------------------------------------------------

CHECK_NUMBERS = Contract(
    name="pkit analysis check-numbers --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "base": "object|null",
                "base.ref": "str",
                "base.tip": "str",
                "base.commit": "str",
                "base.outdated": "bool",
                "freed": "list",
                "freed[]": "object",
                "freed[].id": "str",
                "freed[].path": "str",
                "freed[].added_by": "str",
                "freed[].freed_by": "str",
                **_findings_keys(),
            }
        )
    },
    shapes={"finding": _FINDING},
    refs={"findings[]": "finding"},
    sets={"finding:severity": _SEVERITIES},
)


def test_the_check_numbers_document_holds_its_contract(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, tmp_path: Path
) -> None:
    nothing = _repo(make_adopter_repo, tmp_path / "nothing")
    took = _repo(make_adopter_repo, tmp_path / "took")
    _main_took_ours(took)
    piloted = _repo(make_adopter_repo, tmp_path / "piloted", _piloted)
    piloted.checkout("topic")
    free(piloted, *pilot_freed(piloted))
    printed = [_printed(repo, NUMBERS, "--base", MAIN) for repo in (nothing, took, piloted)]
    check(
        CHECK_NUMBERS,
        {"answer": printed},
        enumerations={"finding:severity": (findings.ERROR, findings.WARNING, findings.REPORT)},
    )


# --- `pkit analysis check-pointers --json` -------------------------------------------------

CHECK_POINTERS_CONTRACT = Contract(
    name="pkit analysis check-pointers --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "default_branch": "object|null",
                "default_branch.name": "str",
                "default_branch.ref": "str",
                "default_branch.commit": "str",
                "base": "object|null",
                "base.ref": "str",
                "base.tip": "str",
                "base.commit": "str",
                **_findings_keys(),
                "pointers": "list",
                "pointers[]": "object",
                "pointers[].record": "str",
                "pointers[].source": "int",
                "pointers[].title": "str",
                "pointers[].commit": "str",
                "pointers[].added": "bool",
                "pointers[].placement": "str",
            }
        )
    },
    shapes={"finding": _FINDING},
    refs={"findings[]": "finding"},
    sets={
        "finding:severity": _SEVERITIES,
        "pointers[].placement": frozenset({"held", "not-held", "unknown"}),
    },
)


def test_the_check_pointers_document_holds_its_contract(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, tmp_path: Path
) -> None:
    nothing = _repo(make_adopter_repo, tmp_path / "nothing")
    designed = _repo(make_adopter_repo, tmp_path / "designed", _designed)
    designed.write(
        {
            NEW: record(
                {"title": "the design", "version": sha(designed, "landed")},
                {"title": "the design's branch", "version": sha(designed, "design")},
            )
        }
    )
    printed = [
        _printed(nothing, CHECK_POINTERS, "--base", "nowhere"),
        _printed(designed, CHECK_POINTERS),
    ]
    pointers = load_lib("pointers")[0]
    check(
        CHECK_POINTERS_CONTRACT,
        {"answer": printed},
        enumerations={
            "finding:severity": (findings.ERROR, findings.WARNING, findings.REPORT),
            "pointers[].placement": (pointers.HELD, pointers.NOT_HELD, pointers.UNKNOWN),
        },
    )


# --- `pkit analysis diagram --json` --------------------------------------------------------

DIAGRAM_CONTRACT = Contract(
    name="pkit analysis diagram --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "diagrams": "list",
                "diagrams[]": "object",
                "diagrams[].id": "str",
                "diagrams[].title": "str",
                "diagrams[].description": "str",
                "diagrams[].mermaid": "str",
            }
        )
    },
)


def test_the_diagram_document_holds_its_contract(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, tmp_path: Path
) -> None:
    seeded = _repo(make_adopter_repo, tmp_path / "seeded", prepare_seeded)
    check(DIAGRAM_CONTRACT, {"answer": [_printed(seeded, DIAGRAM)]})


# --- `pkit analysis met-by --json` ---------------------------------------------------------

_ARTEFACT = {"id": "str", "kind": "str", "title": "str|null", "path": "str"}

MET_BY_CONTRACT = Contract(
    name="pkit analysis met-by --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "requirements": "list",
                "requirements[]": "object",
                **{f"requirements[].{key}": kind for key, kind in _ARTEFACT.items()},
                "requirements[].shown_as": "str|null",
                "requirements[].status": "str|null",
                "requirements[].met_by": "list",
                "requirements[].met_by[]": "object",
                **{f"requirements[].met_by[].{key}": kind for key, kind in _ARTEFACT.items()},
            }
        )
    },
)


def test_the_met_by_document_holds_its_contract(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, tmp_path: Path
) -> None:
    listed = _repo(make_adopter_repo, tmp_path / "listed", _with_requirements)
    _lists(listed, READ_REPORT, ["REQ-004"], ["REQ-004"])
    _lists(listed, RUN_SUITE, ["REQ-004", "REQ-001"], ["REQ-004", "REQ-001"])
    _lists(listed, FIRST_RUN, ["REQ-004"], ["REQ-004"])
    check(MET_BY_CONTRACT, {"answer": [_printed(listed, MET_BY)]})


# --- `pkit analysis uses --json` -----------------------------------------------------------

USES_CONTRACT = Contract(
    name="pkit analysis uses --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "term": "object",
                "term.id": "str",
                "term.name": "str",
                "term.status": "str|null",
                "term.location": "str",
                "term.analysis": "str|null",
                "term.listed_from": "str|null",
                "names": "list",
                "names[]": "str",
                "replaces": "list",
                "replaces[]": "str",
                "not_searched": "list",
                "not_searched[]": "object",
                "not_searched[].name": "str",
                "not_searched[].held_by": "str",
                "listed_in": "list",
                "listed_in[]": "object",
                "listed_in[].analysis": "str",
                "listed_in[].name": "str",
            }
        )
    },
)


def test_the_uses_document_holds_its_contract(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, tmp_path: Path
) -> None:
    terms = _repo(make_adopter_repo, tmp_path / "terms", _terms)
    text = (terms.root / GLOSSARY).read_text(encoding="utf-8")
    text = text.replace("  name: payment\n", "  name: payment\n  replaces: [customer]\n", 1)
    terms.write({GLOSSARY: text})
    two = _repo(make_adopter_repo, tmp_path / "two", _two)
    printed = [
        _printed(terms, USES, "TERM-order"),
        _printed(terms, USES, "TERM-payment"),
        _printed(two, USES, "TERM-suite", "--analysis", "billing"),
    ]
    check(USES_CONTRACT, {"answer": printed})


# --- `pkit analysis obligation --json` -----------------------------------------------------

OBLIGATION_CONTRACT = Contract(
    name="pkit analysis obligation --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "dry_run": "bool",
                "written": "list",
                "written[]": "object",
                "written[].id": "str",
                "written[].path": "str",
                "written[].value": "str",
                "written[].was": "str|null",
                "written[].text": "str",
                "held": "int",
                "problems": "list",
                "problems[]": "object",
                "problems[].id": "str",
                "problems[].path": "str",
                "problems[].why": "str",
            }
        )
    },
)


def test_the_obligation_document_holds_its_contract(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, tmp_path: Path
) -> None:
    project = _repo(make_adopter_repo, tmp_path / "project")
    project.write(
        {
            QUICK: requirement(obligation=None),
            f"{CONSTRAINTS}/REQ-001-local-runs.md": requirement(
                "constraint", req_id="REQ-001", obligation=fingerprint({**TEXTS, "measure": "x"})
            ),
            f"{QUALITY}/REQ-002-held.md": requirement(req_id="REQ-002"),
            f"{QUALITY}/REQ-003-later.md": requirement(req_id="REQ-003", obligation="v9:sha256:00"),
        }
    )
    check(OBLIGATION_CONTRACT, {"answer": [_printed(project, OBLIGATION, "--dry-run")]})


# --- `pkit analysis propose --json` --------------------------------------------------------


PROPOSE_CONTRACT = Contract(
    name="pkit analysis propose --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "artefact": "str",
                "location": "str",
                "state": "str",
                "head": "str",
                "revalidation_point": "str|null",
                "verdict": "str",
                "rule": "str",
                "reason": "str",
                "hint": "str|null",
                "question": "str|null",
                "anchors": "list",
                "anchors[]": "object",
                "anchors[].kind": "str",
                "anchors[].value": "str",
                "anchors[].state": "str",
                "anchors[].shape": "str",
                "anchors[].commits": "list",
                "anchors[].commits[]": "object",
                "anchors[].commits[].commit": "str",
                "anchors[].commits[].change": "str",
                "anchors[].commits[].paths": "list",
                "anchors[].commits[].paths[]": "str",
                "anchors[].quoted": "list",
                "anchors[].quoted[]": "str",
                "anchors[].gone": "list",
                "anchors[].gone[]": "str",
                "anchors[].moved_to": "list",
                "anchors[].moved_to[]": "str",
                "read": "object",
                "read.contradicted": "object|null",
                "read.intended": "object|null",
                "read.unintended": "object|null",
                "answer": "object|null",
                "answer.outcome": "str",
                "answer.first": "list",
                "answer.first[]": "str",
                "answer.commands": "list",
                "answer.commands[]": "str",
                "answer.which": "str|null",
            }
        )
    },
    shapes={
        "quote": Form(
            keys={"quote": "str", "source": "str", "source_kind": "str", "verified": "bool|null"}
        )
    },
    refs={"read.contradicted": "quote", "read.intended": "quote", "read.unintended": "quote"},
    sets={
        "verdict": frozenset(
            {"holds", "analysis-stale", "code-regressed", "ambiguous", "read", "none"}
        ),
        "rule": frozenset(
            {
                "not-judged",
                "nothing-to-resolve",
                "ground-gone",
                "anchor-moved",
                "deliberate-change",
                "quoted-code-kept",
                "nothing-decides",
            }
        ),
        "hint": frozenset({"holds", "analysis-stale"}),
        "anchors[].shape": frozenset({"kept", "moved", "gone", "deliberate", "unread"}),
        "quote:source_kind": frozenset({"commit", "other"}),
        "answer.outcome": frozenset({"holds", "analysis-stale", "code-regressed"}),
    },
)


def test_the_propose_document_holds_its_contract(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, tmp_path: Path
) -> None:
    current = _repo(make_adopter_repo, tmp_path / "current", _flag)
    moved = _repo(make_adopter_repo, tmp_path / "moved", _flag)
    moved.commit(
        "refactor: the suite runs from its own module",
        {
            RUN: "fast = False\nprint('run')\n",
            "src/suite.py": "def run_suite(fast=False):\n    print('run')\n",
        },
    )
    flagged = _repo(make_adopter_repo, tmp_path / "flagged", _flag)
    said = "run_suite becomes execute, as every other entry point is named."
    commit = flagged.commit(
        f"refactor: tidy the runner\n\n{said}",
        {RUN: "def execute(fast=False):\n    print('run')\n"},
    )
    printed = [
        _printed(current, PROPOSE, "UC-001"),
        _printed(moved, PROPOSE, "UC-001"),
        _printed(flagged, PROPOSE, "UC-001"),
        _printed(flagged, PROPOSE, "UC-001", "--intended", said, "--intended-from", commit[:7]),
        _printed(flagged, PROPOSE, "UC-001", "--unintended", "A bug.", "--unintended-from", "Sam"),
    ]
    outcomes = (resolve.HOLDS, resolve.STALE, resolve.REGRESSED)
    check(
        PROPOSE_CONTRACT,
        {"answer": printed},
        enumerations={
            "verdict": (*outcomes, "ambiguous", "read", "none"),
            "rule": (
                resolve.NOT_JUDGED,
                resolve.NOTHING_TO_RESOLVE,
                resolve.GROUND_GONE,
                resolve.ANCHOR_MOVED,
                resolve.DELIBERATE_CHANGE,
                resolve.QUOTED_CODE_KEPT,
                resolve.NOTHING_DECIDES,
            ),
            "hint": (resolve.HOLDS, resolve.STALE),
            "anchors[].shape": (
                resolve.KEPT,
                resolve.MOVED,
                resolve.GONE,
                resolve.DELIBERATE,
                resolve.UNREAD,
            ),
            "answer.outcome": outcomes,
        },
    )


#: The contracts of each software-analysis command that prints a document for a program,
#: by the command's words.
CONTRACTS: Mapping[str, tuple[Contract, ...]] = {
    "software-analysis check-numbers": (CHECK_NUMBERS,),
    "software-analysis check-pointers": (CHECK_POINTERS_CONTRACT,),
    "software-analysis diagram": (DIAGRAM_CONTRACT,),
    "software-analysis met-by": (MET_BY_CONTRACT,),
    "software-analysis uses": (USES_CONTRACT,),
    "software-analysis obligation": (OBLIGATION_CONTRACT,),
    "software-analysis propose": (PROPOSE_CONTRACT,),
}
