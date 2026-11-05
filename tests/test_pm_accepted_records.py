"""Tests for the accepted records a change alters, as the landing shows them
(`_lib/accepted_records.py`, #2161).

`derive` runs the real `pkit decisions check-diff --json --head` in a fixture
repository, from a checkout at another commit. Reading the backbone's document,
a backbone that cannot answer, and the lines for a terminal are tested on the
document's shape.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tests.adopter_repo import GitRepo

REPO_ROOT = Path(__file__).resolve().parent.parent
LIB_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts" / "_lib"

RECORD = ".pkit/decisions/project/PRJ-001-a.md"
HEAD = "1a2b3c4d5e6f708192a3b4c5d6e7f8091a2b3c4d"
COMMAND = "`pkit decisions check-diff --json`"


@pytest.fixture(scope="module")
def ar() -> Iterator[ModuleType]:
    sys.path.insert(0, str(LIB_DIR))
    spec = importlib.util.spec_from_file_location(
        "pm_accepted_records_under_test", LIB_DIR / "accepted_records.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_accepted_records_under_test"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(LIB_DIR))


def _record(decision: str, *, status: str = "accepted") -> str:
    return (
        f"---\nid: PRJ-001\ntitle: A record\nstatus: {status}\ndate: 2026-10-26\nauthor: t\n"
        f"---\n\n## Context\n\nWhy.\n\n## Decision\n\nWhat.\n\n{decision}## Rationale\n\n"
        "Because.\n"
    )


_ONE_TWO = "### 1. One\n\nOne.\n\n### 2. Two\n\nTwo words.\n\n"


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, pkit_on_path: Path) -> GitRepo:
    """A repository whose `main` holds an accepted record, the working directory."""
    made = GitRepo.init(tmp_path / "work")
    monkeypatch.chdir(made.root)
    monkeypatch.delenv("PKIT_CHECK_BASE", raising=False)
    made.commit("records", {RECORD: _record(_ONE_TWO)})
    made.checkout("change", create=True)
    return made


# ---- deriving, through the real backbone ---------------------------------------------


def test_the_records_a_head_alters_are_derived_from_another_checkout(
    ar: ModuleType, repo: GitRepo
) -> None:
    edited = _ONE_TWO.replace("One.", "One, narrowed.") + "### 3. Three\n\nThree.\n\n"
    head = repo.commit("narrow and add", {RECORD: _record(edited)})
    repo.checkout("main")  # the working tree holds the branch point's record

    found = ar.derive(head, "main")

    assert found.problem is None, found.problem
    points = (ar.Point("1", "altered", "One"), ar.Point("3", "added", "Three"))
    assert found.records == (ar.Altered(RECORD, "PRJ-001", points),)


def test_a_status_flip_and_the_other_text_are_told_apart(ar: ModuleType, repo: GitRepo) -> None:
    flipped = _record(_ONE_TWO, status="superseded").replace("Because.", "Because, still.")
    head = repo.commit("supersede", {RECORD: flipped})
    found = ar.derive(head, "main")
    assert found.records == (ar.Altered(RECORD, "PRJ-001", fields=("status",), other=True),)


def test_a_head_that_alters_no_accepted_record_derives_an_empty_list(
    ar: ModuleType, repo: GitRepo
) -> None:
    added = ".pkit/decisions/project/PRJ-002-b.md"
    head = repo.commit(
        "a new record and a reflow",
        {
            added: _record(_ONE_TWO, status="proposed").replace("PRJ-001", "PRJ-002"),
            RECORD: _record(_ONE_TWO.replace("Two words.", "Two\nwords.")),
        },
    )
    found = ar.derive(head, "main")
    assert (found.problem, found.records) == (None, ())


def test_an_error_in_the_numbering_still_gives_the_list(ar: ModuleType, repo: GitRepo) -> None:
    """The backbone exits 1 on a point dropped without being retired, and still prints its
    document: the list is read from it."""
    head = repo.commit("drop", {RECORD: _record("### 1. One\n\nOne.\n\n")})
    found = ar.derive(head, "main")
    assert found.problem is None, found.problem
    assert found.records == (ar.Altered(RECORD, "PRJ-001", (ar.Point("2", "removed", "Two"),)),)


# ---- a backbone that cannot answer ----------------------------------------------------


def _answering(
    ar: ModuleType, monkeypatch: pytest.MonkeyPatch, code: int, out: str, err: str = ""
) -> list[list[str]]:
    asked: list[list[str]] = []

    def run(argv: list[str], **_: Any) -> Any:
        asked.append(argv)
        return subprocess.CompletedProcess(argv, code, out, err)

    monkeypatch.setattr(ar.friction_answers, "refresh_base", lambda base: None)
    monkeypatch.setattr(ar.subprocess, "run", run)
    return asked


def test_it_asks_the_backbone_for_the_head_against_the_base_named(
    ar: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    asked = _answering(ar, monkeypatch, 0, '{"schema_version": 1, "accepted_changes": []}')
    assert ar.derive(HEAD, "integration/7-x").records == ()
    assert asked == [
        ["pkit", "decisions", "check-diff", "--json", "--base", "integration/7-x", "--head", HEAD]
    ]


@pytest.mark.parametrize(
    ("code", "out", "err", "said"),
    [
        (2, "", "Error: the base 'main' does not resolve\n", "it exited 2: Error: the base"),
        (1, "", "Error: --head names no commit\n", "it exited 1: Error: --head names no commit"),
        (0, "not json", "", "with no JSON document"),
    ],
)
def test_an_answer_that_is_no_document_is_never_an_empty_list(
    ar: ModuleType, monkeypatch: pytest.MonkeyPatch, code: int, out: str, err: str, said: str
) -> None:
    _answering(ar, monkeypatch, code, out, err)
    found = ar.derive(HEAD, "main")
    assert found.records == ()
    assert found.problem is not None and said in found.problem


def test_a_base_that_cannot_be_fetched_is_no_list(
    ar: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ar.friction_answers, "refresh_base", lambda base: "the base is gone")
    assert ar.derive(HEAD, "main").problem == "the base is gone"


@pytest.mark.parametrize(
    ("document", "said"),
    [
        ({"schema_version": 2, "accepted_changes": []}, "not a document of version 1"),
        ({"schema_version": 1}, "predates the list"),
        ({"schema_version": 1, "accepted_changes": [{"path": RECORD}]}, "lacks what it needs"),
        (
            {
                "schema_version": 1,
                "accepted_changes": [
                    {
                        "path": RECORD,
                        "record": "PRJ-001",
                        "points": [{"id": 1, "change": "altered", "title": ""}],
                        "fields": [],
                        "shared_text": False,
                        "other_text": False,
                        "list_form": False,
                        "removed": False,
                    }
                ],
            },
            "lacks what it needs",
        ),
    ],
)
def test_a_document_missing_what_the_list_rests_on_is_no_list(
    ar: ModuleType, document: dict[str, Any], said: str
) -> None:
    found = ar.read(document, COMMAND)
    assert found.records == ()
    assert found.problem is not None and said in found.problem


# ---- the lines for a terminal -----------------------------------------------------------


def test_each_record_is_a_line_saying_what_the_change_does_and_what_to_judge(
    ar: ModuleType,
) -> None:
    point = ar.Point("1", "altered", "Scope")
    records = (
        ar.Altered(RECORD, "PRJ-001", (point,), ("status", "title"), shared=True, other=True),
        ar.Altered("docs/adr/ADR-002-b.md", "ADR-002", list_form=True),
        ar.Altered("docs/adr/ADR-003-c.md", "ADR-003", removed=True),
    )
    ask = "Judge whether each edit changes what the record decides."
    assert ar.lines(records) == [
        f"[accepted record] PRJ-001, `{RECORD}`: point 1 (Scope) altered, its status and title "
        f"altered, the text its points stand on altered and its other text altered. {ask}",
        "[accepted record] ADR-002, `docs/adr/ADR-002-b.md`: altered as a whole, since its "
        f"points are a list. {ask}",
        f"[accepted record] ADR-003, `docs/adr/ADR-003-c.md`: removed. {ask}",
    ]


def test_what_a_terminal_would_act_on_is_escaped(ar: ModuleType) -> None:
    point = ar.Point("1", "altered", "A\x07 title")
    (line,) = ar.lines((ar.Altered("a\x1b[31m.md", "PRJ-001", (point,)),))
    assert "\x1b" not in line and "\x07" not in line
