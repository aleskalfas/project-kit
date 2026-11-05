"""Tests for the answers a change wrote, read from the change check
(`_lib/friction_answers.py`, project-management DEC-055 and DEC-065).

The answers are the change check's: `derive` runs the real `pkit friction check
--head` in fixture repositories — from a checkout at another commit, and, where a
registered anchor kind's resolver must run, from a temporary checkout of the head.
What the person who authorises the merge is told, the author's sentences, and the
stripping of a list an earlier run wrote into a description are tested on the
check's document shape.

Where a test runs the change check, its `pkit` is answered by the backbone's CLI in
the test's own process, the argument lists unchanged (`tests/in_process.py`). The
check at a merge names the change's own head in its environment, which the
in-process `pkit` does not model, so a test that reaches it stands the check in.
Six tests keep a real process, each marked with why.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import signal
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from ruamel.yaml import YAML

from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.anchor_kind_capabilities import RESOLVING, register_kinds
from tests.friction_documents import (
    CONFIG,
    SOURCE,
    T1,
    blocks_in_history,
    document,
    friction_config,
    guide,
)
from tests.in_process import MODELLED, InProcessPkit, Runner
from tests.shipped_rule_sets import without_shipped_rule_sets
from tests.test_friction_revisit import (
    DECISION,
    SOURCE_DOC,
    TEST_FILE,
    declare_linker,
    requirement,
)
from tests.test_friction_revisit import entry as revisit_entry
from tests.test_pm_backbone import route_every_backbone

#: The documents here say each artefact's answers beside its anchors, and each write
#: takes them into answer files, as a change writes them (COR-062 point 1).
pytestmark = pytest.mark.usefixtures("answers_in_files")

REPO_ROOT = Path(__file__).resolve().parent.parent
CAP_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
LIB_DIR = CAP_ROOT / "scripts" / "_lib"

HEAD = "1a2b3c4d5e6f708192a3b4c5d6e7f8091a2b3c4d"
MERGE_BASE = "0" * 40


@pytest.fixture(scope="module")
def fa() -> Iterator[ModuleType]:
    sys.path.insert(0, str(LIB_DIR))
    spec = importlib.util.spec_from_file_location(
        "pm_friction_answers_under_test", LIB_DIR / "friction_answers.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_friction_answers_under_test"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(LIB_DIR))


@pytest.fixture
def pkit_here(fa: ModuleType, monkeypatch: pytest.MonkeyPatch) -> Runner:
    """Every `pkit` call of the module answered by the backbone's CLI in this process,
    through each copy of `_lib/backbone.py` it may reach (`route_every_backbone`)."""
    return route_every_backbone(monkeypatch)


def _entry(
    location: str,
    answer: str | None,
    reason: str | None = None,
    *,
    anchor: tuple[str, str] | None = None,
    asked: bool = True,
    status: str = "stands",
    new: bool = False,
    kept: list[tuple[tuple[str, str], str | None]] | None = None,
    changed: list[tuple[str, str]] | None = None,
    put_back: bool = False,
) -> dict[str, Any]:
    """One entry of the change check's `answers`, as `--json` gives it."""
    return {
        "artefact": location.split("/")[-1].removesuffix(".md"),
        "location": location,
        "answer": answer,
        "anchor": None if anchor is None else {"kind": anchor[0], "value": anchor[1]},
        "reason": reason,
        "kept": [
            {"anchor": {"kind": kind, "value": value}, "reason": words}
            for (kind, value), words in (kept or [])
        ],
        "asked": asked,
        "status": status,
        "new": new,
        "put_back": put_back,
        "changed": [{"kind": kind, "value": value} for kind, value in (changed or [])],
    }


def _document(*answers: dict[str, Any], unreadable: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "check": "change",
        "base": {"ref": "origin/main", "commit": MERGE_BASE, "tip": MERGE_BASE, "outdated": False},
        "answers": list(answers),
        "unreadable": unreadable or [],
    }


# ---- the markers -------------------------------------------------------------


def test_the_markers_are_the_schemas(fa: ModuleType) -> None:
    schema = YAML(typ="safe").load((CAP_ROOT / "schemas" / "body-format.yaml").read_text("utf-8"))
    marker = schema["friction_answers_marker"]
    assert marker["heading"] == fa.HEADING
    assert marker["start_marker"] == fa.MARKER_START
    assert marker["end_marker"] == fa.MARKER_END


# ---- what the person is told (DEC-065 point 4) ------------------------------------


def test_each_answer_reads_in_the_change_check_s_own_words(fa: ModuleType) -> None:
    """What the person is told names each answer, and each anchor of a core kind, as
    the change check's own list does (#1468)."""
    from project_kit import friction_check as fc

    assert fa.LABELS == fc.OUTCOME_WORDS
    assert fa.NO_OUTCOME == fc.NO_OUTCOME
    assert fa._ANCHOR_NOUNS == fc._ANCHOR_NOUNS


@pytest.mark.parametrize(
    ("anchor", "said"),
    [
        (("path", "src/cli/**"), "src/cli/**"),
        (("record", "COR-050"), "decision record COR-050"),
        (("artefact", "ACT-clone"), "document ACT-clone"),
        (("symbol", "pkg.run"), "symbol:pkg.run"),
    ],
)
def test_an_anchor_is_named_in_plain_words(
    fa: ModuleType, anchor: tuple[str, str], said: str
) -> None:
    """An anchor of a core kind in plain words; one of a kind a capability
    registers as the change check names it, its kind too."""
    document = _document(_entry("docs/a.md", "deferred", "Later.", anchor=anchor, changed=[anchor]))
    assert fa.told(document) == [f'Left out of date: docs/a.md, for changes to {said}: "Later."']


def test_documents_counts_each_document_once(fa: ModuleType) -> None:
    """A page that defers two anchors is one document the change affects."""
    answers = [
        _entry("docs/a.md", "deferred", "Later.", anchor=("path", "x/**")),
        _entry("docs/a.md", "deferred", "Later.", anchor=("path", "y/**")),
        _entry("docs/b.md", "updated"),
    ]
    assert fa.documents(answers) == 2
    assert fa.documents([]) == 0
    assert fa.affected(2, settings=False) == "2"
    assert fa.affected(2, settings=True) == "2, plus a change to which documents are checked"
    assert fa.affected(0, settings=True) == "none, but a change to which documents are checked"
    assert fa.affected(0, settings=False) == "none"


def test_what_the_person_is_told_is_the_sentences_and_what_is_left_out_of_date(
    fa: ModuleType,
) -> None:
    """As information, not a gate (DEC-065 point 4): what changed in each updated
    document, each document left out of date with the deferral's words — one the
    change wrote, or one a revalidation kept — and each setting changed. An answer
    that holds is the reviewer's to check, and is not told."""
    document = _document(
        _entry("docs/a.md", "updated"),
        _entry("docs/c.md", "updated"),
        _entry("docs/b.md", "unchanged", "Holds.", kept=[(("path", "x/**"), "Later, #12.")]),
        _entry("docs/d.md", "deferred", "With the redesign, #13.", anchor=("record", "COR-1")),
        _entry("docs/e.md", "unchanged", "Holds."),
    )
    settings = [
        fa.Setting(fa.PLACES, ("docs",), ("docs", "guides")),
        fa.Setting(fa.EXCLUDED, (), ("docs/guide.md",)),
    ]
    told = fa.told(document, settings, {"docs/a.md": "Now says X."})
    assert told == [
        'What changed in docs/a.md: "Now says X."',
        "What changed in docs/c.md: the pull request's author has not said",
        'Left out of date: docs/b.md, for changes to x/**: "Later, #12."',
        'Left out of date: docs/d.md, for changes to decision record COR-1: "With the '
        'redesign, #13."',
        "Checked locations: docs → docs, guides",
        "Documents excluded from checking: none → docs/guide.md",
    ]
    assert fa.counted_told(document) == (2, 2, 0, 0)
    assert fa.told(_document(_entry("docs/e.md", "unchanged", "Holds."))) == []


def test_a_change_that_wrote_no_answers_tells_nothing(fa: ModuleType) -> None:
    assert fa.told(_document()) == []
    assert fa.counted_told(_document()) == (0, 0, 0, 0)


def test_each_answer_a_person_decided_is_told_with_its_words(fa: ModuleType) -> None:
    """An answer the change check did not ask for, and a reason for having no anchors,
    were each a person's to decide, or their delegate's, before it was written
    (COR-064): each is told with its outcome and words, after what is left out of
    date. A deferral among them is left out of date too, so it is told twice."""
    document = _document(
        _entry("docs/a.md", "unchanged", "Holds.", asked=False),
        _entry("docs/b.md", "deferred", "In #9.", anchor=("path", "src/**"), asked=False),
        _entry("docs/c.md", "unanchored", "A rule of the method.", asked=False, new=True),
        _entry("docs/d.md", None, "Reworded.", asked=False, status="edited"),
        _entry("docs/e.md", "unanchored", "Asked, yet a person's.", asked=True),
        _entry("docs/f.md", "unchanged", "Asked, so no person's."),
    )
    assert fa.told(document) == [
        'Left out of date: docs/b.md, for changes to src/**: "In #9."',
        'Not asked for by this change: docs/a.md, still accurate: "Holds."',
        "Not asked for by this change: docs/b.md, for changes to src/**, out of date, fixed "
        'later: "In #9."',
        'Not asked for by this change: docs/c.md, not tied to anything: "A rule of the method."',
        'Not asked for by this change: docs/d.md, no decision recorded: "Reworded."',
        'Not asked for by this change: docs/e.md, not tied to anything: "Asked, yet a person\'s."',
    ]
    assert fa.counted_told(document) == (0, 1, 0, 5)


def test_the_check_s_terms_stay_out_of_what_the_person_is_told(fa: ModuleType) -> None:
    """The change check's own terms are its machine-readable list's: what a person
    is told names each answer in plain words."""
    told = fa.told(
        _document(
            _entry("a.md", "unchanged", "Holds.", asked=False),
            _entry("b.md", "deferred", "Later.", anchor=("path", "x/**"), asked=False, new=True),
            _entry("c.md", "unanchored", "A rule.", status="bump"),
            _entry("d.md", "updated"),
            *(
                _revisit(f"r{n}.md", outcome, "Why.", asked=False)
                for n, outcome in enumerate(OUTCOMES)
            ),
        )
    )
    shown = "\n".join(told).lower()
    for term in ("unchanged", "deferred", "unanchored", "revisited", "friction", "artefact"):
        assert term not in shown, term


def test_non_printable_characters_are_shown_escaped_as_the_human_view_shows_them(
    fa: ModuleType,
) -> None:
    words = "fine\x1b[1A\x1b[2Kgone ‮esrever\nnext"
    document = _document(
        _entry("docs/a​.md", "deferred", words, anchor=("path", "src/\x1b/**")),
        _entry("docs/b.md", "updated"),
    )
    told = fa.told(document, (), {"docs/b.md": "Now\x1b[2J says X."})
    assert told == [
        'What changed in docs/b.md: "Now\\x1b[2J says X."',
        "Left out of date: docs/a\\u200b.md, for changes to src/\\x1b/**: "
        '"fine\\x1b[1A\\x1b[2Kgone \\u202eesrever\\nnext"',
    ]
    assert all(ch.isprintable() for line in told for ch in line)


# ---- the answers as the backbone gives them (COR-062, DEC-055 point 3) ------------

#: Answer files, in the folder the backbone gives (COR-062 point 2).
ANSWERS = ".pkit/project/friction/answers"
ANSWER_FILE = f"{ANSWERS}/20261022T090000Z-1a2b3c4d.yaml"
TIP_FILE = f"{ANSWERS}/20261023T090000Z-5e6f7a8b.yaml"


def test_the_answers_words_are_in_the_file_the_check_names_for_each_answer(
    fa: ModuleType,
) -> None:
    """The firm stop's files are those the change check names for each answer: an
    answer file the change adds, or the artefact's own file for an answer in its block
    (COR-062 point 1). An answer it names no file for, such as a target revisited by
    changing it, counts its artefact's file. With every answer in a block these are
    the artefacts' files, as before the answers moved."""
    in_file = {**_entry("docs/a.md", "unchanged", "Holds."), "file": ANSWER_FILE}
    in_block = {**_entry("docs/b.md", "unchanged", "Holds."), "file": "docs/b.md"}
    entry = {**_entry("docs/terms.md#TERM-x", "deferred", "In #9."), "file": "docs/terms.md"}
    by_change = _entry("docs/c.md", "revisited")
    document = _document(in_file, in_block, entry, by_change)
    assert fa.listed_paths(document) == {ANSWER_FILE, "docs/b.md", "docs/terms.md", "docs/c.md"}
    assert fa.listed_paths(_document(_entry("docs/a.md#X", "unchanged", "Holds."))) == {"docs/a.md"}


def _apart(*revalidations: dict[str, Any]) -> dict[str, Any]:
    """A change check's document whose answer on `docs/a.md` did not read
    `revalidations`, live on the base's tip (`answered_apart_at_tip`)."""
    answer = {**_entry("docs/a.md", "unchanged", "Holds."), "file": ANSWER_FILE}
    return {
        **_document(answer),
        "answered_apart_at_tip": [
            {"artefact": "a", "location": "docs/a.md", "revalidations": list(revalidations)}
        ],
    }


def test_each_revalidation_a_merge_would_leave_answered_apart_is_a_line(fa: ModuleType) -> None:
    """Each live revalidation on the base's tip that the change's answer did not read
    is a line, its words shown escaped, told after the rest (DEC-055 point 3, DEC-065
    point 4)."""
    document = _apart(
        {
            "file": TIP_FILE,
            "at": "2026-10-23T09:00:00Z",
            "outcome": "unchanged",
            "unchanged_because": "Still\x1b[2K holds.",
        },
        {"file": ANSWER_FILE, "at": None, "outcome": "updated", "unchanged_because": None},
    )
    assert fa.apart(document) == [
        f"Answered apart once merged: docs/a.md — the base's revalidation in {TIP_FILE} of "
        "2026-10-23T09:00:00Z, which this change's answer did not read. Still accurate: "
        '"Still\\x1b[2K holds."',
        f"Answered apart once merged: docs/a.md — the base's revalidation in {ANSWER_FILE}, "
        "which this change's answer did not read. Updated in this change",
    ]
    assert fa.told(document) == fa.apart(document)
    assert fa.apart(_document()) == []  # none reported, as with answers only in blocks


def test_what_is_told_ends_with_the_files_unread_the_revalidations_apart_and_the_callers(
    fa: ModuleType,
) -> None:
    """One composition of what the person is told, so the landing command and
    `show-pr --field answers` cannot differ (DEC-065 point 2). The count of files the
    check could not read is a line of it (DEC-065 point 4)."""
    document = _apart(
        {"file": TIP_FILE, "at": None, "outcome": "updated", "unchanged_because": None}
    )
    document["unreadable"] = ["docs/a.md", "docs/b.md"]
    assert fa.told(document, also=["Fixer grant added: a"]) == [
        f"{fa.UNREAD}: 2",
        *fa.apart(document),
        "Fixer grant added: a",
    ]


def test_what_is_left_out_of_date_is_the_lines_told_of_it(fa: ModuleType) -> None:
    """`left_out` gives the lines a later head is compared by, as `told` gives them:
    a deferral's and a kept deferral's, never any other answer's (DEC-065 point 4)."""
    document = _document(
        _entry("docs/a.md", "deferred", "Until #1.", anchor=("path", "src/**")),
        _entry("docs/b.md", "unchanged", "Holds.", kept=[(("path", "x"), "Until #2.")]),
        _entry("docs/c.md", "unchanged", "Holds."),
    )
    assert fa.left_out(document) == [
        'Left out of date: docs/a.md, for changes to src/**: "Until #1."',
        'Left out of date: docs/b.md, for changes to x: "Until #2."',
    ]
    assert fa.told(document) == fa.left_out(document)


def _folder_answering(proc: Any, asked: list[Any]) -> Any:
    """A stand-in for `subprocess.run` answering the whole-repository check with `proc`:
    a document, an exit code and a document, or an exception to raise."""

    def run(argv: list[str], **kw: Any) -> subprocess.CompletedProcess[str]:
        asked.append((argv, kw.get("cwd"), (kw.get("env") or {}).get("PKIT_NO_ROUTE")))
        if isinstance(proc, Exception):
            raise proc
        code, document = proc if isinstance(proc, tuple) else (0, proc)
        text = document if isinstance(document, str) else json.dumps(document)
        return subprocess.CompletedProcess(argv, code, text, "")

    return run


def test_where_the_backbone_keeps_the_answers_is_read_once_from_its_check(
    fa: ModuleType, tmp_path: Path
) -> None:
    """The folder is the backbone's to give, in its whole-repository check's document
    (`answers.folder`); this capability never names it. It is read once for a run,
    unrouted, at the repository root."""
    asked: list[Any] = []
    whole = {"schema_version": 1, "answers": {"folder": ANSWERS, "files": 0, "prunable": []}}
    run = _folder_answering(whole, asked)
    assert fa.answers_folder(tmp_path, run) == ANSWERS
    assert fa.answers_folder(tmp_path, run) == ANSWERS
    assert asked == [(["pkit", "friction", "check", "--all", "--json"], tmp_path, "1")]


@pytest.mark.parametrize(
    "proc",
    [
        OSError("no pkit"),
        subprocess.TimeoutExpired("pkit", 600),
        (1, {"schema_version": 1, "answers": {"folder": ANSWERS}}),
        "not json",
        {"schema_version": 2, "answers": {"folder": ANSWERS}},
        {"schema_version": 1},
        {"schema_version": 1, "answers": {"folder": ""}},
        {"schema_version": 1, "answers": {"folder": "/etc"}},
    ],
)
def test_a_backbone_that_gives_no_folder_is_read_as_none(
    fa: ModuleType, tmp_path: Path, proc: Any
) -> None:
    """Whatever stops the backbone giving the folder, there is none: a reader then sets
    no path apart, which errs toward more review (DEC-032 D5)."""
    assert fa.answers_folder(tmp_path, _folder_answering(proc, [])) is None


# ---- revisit entries (COR-050 point 16) ------------------------------------------

SOURCE_REQ = "reqs/latency.md"
TEST_TARGET = ("path", "tests/test_latency.py")
#: The outcomes a revisit entry gives.
OUTCOMES = ("updated", "unchanged", "deferred")


def _revisit(
    location: str,
    outcome: str | None,
    reason: str | None = None,
    *,
    target: tuple[str, str] | None = TEST_TARGET,
    links: list[str] | None = None,
    fields: list[str] | None = None,
    asked: bool = True,
    status: str = "stands",
    new: bool = False,
) -> dict[str, Any]:
    """One revisit entry of the change check's `answers`, as `--json` gives it: the
    source's answer for one target, through `verified-by` by default, the change
    having modified the source's `threshold`."""
    revisit = _entry(location, "revisited", reason, asked=asked, status=status, new=new)
    revisit["changed"] = []
    revisit.update(
        outcome=outcome,
        target=None if target is None else {"kind": target[0], "value": target[1]},
        links=["verified-by"] if links is None else links,
        fields=["threshold"] if fields is None else fields,
    )
    return revisit


def test_a_deferred_revisit_entry_is_told_and_counted_with_what_is_left_out_of_date(
    fa: ModuleType,
) -> None:
    """The person who authorises the merge is told each target a `deferred` revisit
    entry leaves out of date, with the source that names it and the words that name
    its follow-up, beside the documents left out of date (COR-050 points 3 and 16).
    A target is counted once, however many sources leave it out of date; one that
    still stands, or that the change revisited by changing it, is not told."""
    deferred = "The cache decision is revisited in #9999."
    document = _document(
        _entry("docs/d.md", "deferred", "With the redesign, #13.", anchor=("record", "COR-1")),
        _revisit(SOURCE_REQ, "updated"),
        _revisit(SOURCE_REQ, "unchanged", "Holds.", target=("artefact", "UC-status")),
        _revisit(SOURCE_REQ, "deferred", deferred, target=("record", "DEC-7")),
        _revisit("reqs/other.md", "deferred", "Also #9999.", target=("record", "DEC-7"), links=[]),
    )
    assert fa.told(document) == [
        'Left out of date: docs/d.md, for changes to decision record COR-1: "With the '
        'redesign, #13."',
        f"Left out of date: decision record DEC-7, which {SOURCE_REQ} names through "
        f'verified-by: "{deferred}"',
        'Left out of date: decision record DEC-7, which reqs/other.md names: "Also #9999."',
    ]
    counted = fa.counted_told(document)
    assert (counted.updated, counted.left, counted.targets, counted.unasked) == (0, 1, 1, 0)
    # A revisit entry whose words or target are not there is told all the same, and
    # each such entry counts as a target of its own, as it has a line of its own.
    unnamed = _revisit(SOURCE_REQ, "deferred", None, target=None, links=[])
    bare = _document(unnamed, unnamed)
    told = f"Left out of date: a target, which {SOURCE_REQ} names"
    assert fa.told(bare) == [told, told]
    assert fa.counted_told(bare) == (0, 0, 2, 0)


def test_a_revisit_entry_a_person_decided_is_told_by_its_target(fa: ModuleType) -> None:
    """A revisit entry the change check did not ask for names its target and the
    source that names it, with its outcome and words (COR-064)."""
    document = _document(
        _revisit(SOURCE_REQ, "unchanged", "Holds.", target=("record", "DEC-7"), asked=False)
    )
    assert fa.told(document) == [
        f"Not asked for by this change: decision record DEC-7, which {SOURCE_REQ} names "
        'through verified-by, still accurate: "Holds."'
    ]
    assert fa.counted_told(document) == (0, 0, 0, 1)


def test_a_revisit_entry_s_texts_are_shown_escaped(fa: ModuleType) -> None:
    """The target and the links are the artefact's texts: each is shown escaped."""
    document = _document(
        _revisit(
            SOURCE_REQ,
            "deferred",
            "Later.",
            target=("path", "tests/*bold*\x1b.py"),
            links=["verified‮by"],
        )
    )
    told = fa.told(document)
    assert told == [
        f"Left out of date: tests/*bold*\\x1b.py, which {SOURCE_REQ} names through "
        'verified\\u202eby: "Later."'
    ]
    assert all(ch.isprintable() for line in told for ch in line)


def test_a_target_revisited_by_its_own_change_asks_for_no_sentence(fa: ModuleType) -> None:
    """A target the change revisited by changing it is for the reviewer who checks
    that its change meets the change to the source (COR-050 points 3 and 16). It is
    no revalidation, so it asks its author for no sentence, and marks its source
    updated nowhere."""
    only = _document(_revisit(SOURCE_REQ, "updated"))
    said = {SOURCE_REQ: "The threshold is 10 s."}
    assert fa.updated_in(only) == []
    assert fa.unsaid(only, said) == []
    assert fa.unlisted(only, said) == [SOURCE_REQ]
    assert fa.told(only, (), said) == []
    assert fa.counted_told(only) == (0, 0, 0, 0)
    # A source the change also revalidated as updated gives its sentence once, beside
    # its revalidation.
    both = _document(_entry(SOURCE_REQ, "updated"), _revisit(SOURCE_REQ, "updated"))
    assert fa.updated_in(both) == [SOURCE_REQ]
    assert fa.unsaid(both, said) == [] and fa.unlisted(both, said) == []
    assert fa.told(both, (), said) == [f'What changed in {SOURCE_REQ}: "The threshold is 10 s."']
    assert fa.documents(both["answers"]) == 1


# ---- a list an earlier run wrote into a description (DEC-065 point 1) -------------

FOOTER = (
    "<!-- pkit-provenance:start -->\n\n---\n<sub>🧰 pkit · tree `1` · pm `2`</sub>\n"
    "<!-- pkit-provenance:end -->"
)
BODY = "Closes #42\n\n## Summary\n\nDone.\n\n## Doc impact\n\nThe README.\n"


def _section(fa: ModuleType, *lines: str, head: str = HEAD, heading: str | None = None) -> str:
    """A list as an earlier run wrote it (DEC-055 point 1): under its heading, between
    its markers, the head it was derived for named in the start marker."""
    return "\n".join(
        [
            heading or fa.HEADING,
            "",
            f"{fa.MARKER_START} head={head} base={MERGE_BASE} -->",
            "These documents rely on something this change modifies, and each answer says "
            "whether the document is still true.",
            "",
            *(lines or ['1. `docs/a.md` — **still accurate**: "``fixes #9``"']),
            fa.MARKER_END,
        ]
    )


def test_stripping_leaves_the_rest_of_the_body_as_it_was(fa: ModuleType) -> None:
    section = _section(fa)
    assert fa.has_list(f"{BODY}\n{section}\n")
    assert fa.strip(f"{BODY}\n{section}\n") == BODY
    assert fa.strip(f"{BODY}\n{section}\n\n{FOOTER}\n") == f"{BODY}\n{FOOTER}\n"
    assert fa.strip(BODY) == BODY
    assert not fa.has_list(BODY) and not fa.orphaned(BODY)


def test_a_start_marker_with_no_end_is_named_and_nothing_is_removed(fa: ModuleType) -> None:
    """What follows it may be the author's: a quoted marker, or one whose end was
    lost, removes nothing, and every reader reads the text as the body's own (DEC-065
    point 1)."""
    orphan = f"{BODY}\n{fa.HEADING}\n\n{fa.MARKER_START} head=x base=y -->\nleft\n"
    assert fa.strip(orphan) == orphan
    assert fa.orphaned(orphan) and not fa.has_list(orphan)


def test_a_quoted_start_marker_keeps_what_follows_it(fa: ModuleType) -> None:
    """A start marker quoted in a fence, above the sentences and the closing line:
    all of it stays, and the sentences read."""
    quoted = f"```\n{fa.MARKER_START} head=x base=y -->\n```\n"
    said = f"{fa.SENTENCES_HEADING}\n\n- `docs/a.md`: The page says so.\n\nCloses #42\n"
    body = f"{quoted}\n{said}"
    assert fa.strip(body) == body and fa.orphaned(body)
    assert fa.sentences(body) == {"docs/a.md": "The page says so."}


def test_a_region_goes_and_a_start_marker_with_no_end_stays(fa: ModuleType) -> None:
    orphan = f"{fa.MARKER_START} head=x base=y -->\nleft\n"
    body = f"{BODY}\n{_section(fa)}\n\n{orphan}"
    assert fa.has_list(body) and fa.orphaned(body)
    assert fa.strip(body) == f"{BODY}\n{orphan}"


def test_an_end_marker_with_no_start_is_left(fa: ModuleType) -> None:
    orphan = f"{BODY}\nkept\n{fa.MARKER_END}\nafter\n"
    assert fa.strip(orphan) == orphan
    assert not fa.has_list(orphan) and not fa.orphaned(orphan)


def test_markers_count_only_as_whole_lines(fa: ModuleType) -> None:
    """A sentence that mentions a marker is body text: no section, nothing stripped."""
    body = f"{BODY}\nThe list opens with `{fa.MARKER_START} head=… -->` and ends.\n"
    assert not fa.has_list(body) and fa.strip(body) == body


def test_a_reason_quoting_the_provenance_marker_cuts_nothing(fa: ModuleType) -> None:
    """The footer starts only at a line that is its marker: a body quoting one, in
    a sentence, keeps every line, and the list before the footer is still stripped."""
    quoting = f"{BODY}\nThe footer opens with <!-- pkit-provenance:start --> as a line.\n"
    body = f"{quoting}\n{_section(fa)}\n\n{FOOTER}\n"
    assert fa.strip(body) == f"{quoting}\n{FOOTER}\n"


def _hand(heading: str) -> str:
    """A section typed under `heading`, with no markers."""
    return f"{heading}\n\nThe author's own words, which close nothing else: Closes #9\n"


#: The region's heading, and the one a still earlier run wrote above it.
HEADINGS = ("## Documentation this change affects", "## Friction answers")


@pytest.mark.parametrize("heading", HEADINGS, ids=["the heading", "the former heading"])
def test_a_section_under_the_heading_with_no_markers_is_the_author_s(
    fa: ModuleType, heading: str
) -> None:
    """No list remains for such a section to be mistaken for: it is left, and every
    reader reads it, so a closing reference in it counts, as the host counts it
    (DEC-065 point 1)."""
    assert heading in (fa.HEADING, fa.FORMER_HEADING)
    body = f"{BODY}\n{_hand(heading)}\n{FOOTER}\n"
    assert fa.strip(body) == body
    assert not fa.has_list(body) and not fa.orphaned(body)


def test_a_section_an_earlier_run_wrote_under_the_former_heading_is_stripped_whole(
    fa: ModuleType,
) -> None:
    """The markers identify the region; the former heading directly above it goes
    with it, so no stray heading of the old one is left."""
    earlier = _section(fa, head="e" * 40, heading=fa.FORMER_HEADING)
    body = f"{BODY}\n{earlier}\n\n{FOOTER}\n"
    assert fa.has_list(body)
    stripped = fa.strip(body)
    assert stripped == f"{BODY}\n{FOOTER}\n"
    assert fa.FORMER_HEADING not in stripped and fa.HEADING not in stripped


def test_the_former_heading_inside_a_region_goes_with_the_region(fa: ModuleType) -> None:
    """A region is its start marker's line through its end marker's, whatever it
    holds: the former heading inside one is the region's."""
    region = f"{fa.MARKER_START} head={HEAD} base={MERGE_BASE} -->\n{fa.FORMER_HEADING}\n\nold\n"
    body = f"{BODY}\n{fa.HEADING}\n\n{region}{fa.MARKER_END}\n"
    assert fa.has_list(body)
    assert fa.strip(body) == BODY


def test_two_regions_are_both_stripped(fa: ModuleType) -> None:
    old = _section(fa, head="e" * 40)
    new = _section(fa)
    body = f"{BODY}\n{old}\n\n{new}\n"
    assert fa.has_list(body)
    assert fa.strip(body) == BODY


def test_a_description_whose_line_ends_the_host_changed_is_stripped(fa: ModuleType) -> None:
    body = f"{BODY}\n{_section(fa)}\n"
    hosted = "\r\n".join(line + ("  " if line else "") for line in body.split("\n"))
    assert fa.has_list(hosted)
    assert fa.MARKER_START not in fa.strip(hosted) and fa.HEADING not in fa.strip(hosted)


# ---- closing references in the author's sentences ---------------------------------


@pytest.mark.parametrize(
    ("words", "found"),
    [
        ("This fixes #12 for good.", "fixes #12"),
        ("Closes: owner/repo#3", "Closes: owner/repo#3"),
        ("resolved https://github.com/o/r/issues/4", "resolved https://github.com/o/r/issues/4"),
        ("FIXED #1", "FIXED #1"),
        ("close #9", "close #9"),
        ("it resolves:#7", "resolves:#7"),
    ],
)
def test_a_sentence_that_reads_as_a_closing_reference_is_named(
    fa: ModuleType, words: str, found: str
) -> None:
    """Wider than the closing references this capability reads: the host closes
    `fixed #1` and `owner/repo#3`, and the checkbox gate would never see them (DEC-065
    point 5)."""
    assert fa.closing_references({"docs/ok.md": "Holds.", "docs/a.md": words}) == [
        ("docs/a.md", found)
    ]


@pytest.mark.parametrize(
    "words",
    ["see #12", "the fix-up #12", "close to #3", "fixtures #2", "fixes the layout #2 section"],
)
def test_other_words_are_no_closing_reference(fa: ModuleType, words: str) -> None:
    assert fa.closing_references({"docs/a.md": words}) == []


def test_each_sentence_that_reads_so_is_named_with_what_to_do(fa: ModuleType) -> None:
    said = {"docs/a.md": "It fixes #1.", "docs/b.md": "It closes #2."}
    assert fa.closing_references(said) == [("docs/a.md", "fixes #1"), ("docs/b.md", "closes #2")]
    assert fa.closing_message("docs/a.md", "fixes #1") == (
        f"the sentence on what changed in docs/a.md, under `{fa.SENTENCES_HEADING}`, reads as a "
        "closing reference (fixes #1): the host would close an issue with it at merge — reword it"
    )


# ---- deriving, through the real change check --------------------------------------

BECAUSE = "the CLI change is internal: every command the guide shows is as described"


def _branch_with_an_answer(make_adopter_repo: MakeAdopterRepo) -> tuple[AdopterRepo, str]:
    repo = make_adopter_repo()
    repo.write({CONFIG: friction_config(mode="enforcing"), **SOURCE, "docs/guide.md": guide()})
    repo.commit("base", files=None)
    repo.checkout("feature", create=True)
    repo.commit("change the CLI", {"src/cli/main.py": "print('cli v2')\n"})
    revalidated = guide(at="2026-10-03T10:00:00Z", because=BECAUSE)
    repo.commit("revalidate the guide", {"docs/guide.md": revalidated})
    return repo, repo.head()


@pytest.mark.process(
    "derive's end-to-end test: the real `pkit friction check --head` from another "
    "checkout, uncommitted work not read, the merge base carried"
)
def test_the_list_is_derived_at_the_head_from_another_checkout(
    fa: ModuleType, make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path
) -> None:
    repo, head = _branch_with_an_answer(make_adopter_repo)
    repo.checkout("main")
    repo.write({"notes.txt": "uncommitted, and not the head's\n"})
    found = fa.derive(head, "main")
    assert found.problem is None, found.problem
    assert [(a["location"], a["answer"], a["reason"], a["asked"]) for a in found.answers] == [
        ("docs/guide.md", "unchanged", BECAUSE, True)
    ]
    assert found.merge_base == repo.git("rev-parse", "main").stdout.strip()
    assert (found.outdated, found.unreadable) == (False, ())


def test_a_revisit_entry_derived_from_the_check_is_told_in_words(
    fa: ModuleType, make_adopter_repo: MakeAdopterRepo, pkit_here: Runner
) -> None:
    """The real change check's revisit entries (#1703): a source whose trigger field
    changed, one target it revisits by changing it and one it leaves out of date. The
    person is told the one left out of date, in words, and not the one it changed."""
    deferral = "the cache decision is revisited in #9999"
    repo = make_adopter_repo()
    declare_linker(repo.root)
    repo.write(
        {
            CONFIG: friction_config(places=("docs",)),
            **SOURCE,
            TEST_FILE: "def test_latency():\n    assert answer_time() < 2\n",
            DECISION: "Cache the status.\n",
            SOURCE_DOC: requirement(),
        }
    )
    repo.commit("base", files=None)
    repo.checkout("feature", create=True)
    source = requirement(
        threshold="10 s", revisited=[revisit_entry("deferred", deferral, DECISION)]
    )
    test = "def test_latency():\n    assert answer_time() < 10\n"
    repo.commit("relax the threshold", {SOURCE_DOC: source, TEST_FILE: test})
    found = fa.derive(repo.head(), "main")
    assert found.problem is None, found.problem
    assert [(a["answer"], a["outcome"]) for a in found.answers] == [
        ("revisited", "deferred"),
        ("revisited", "updated"),
    ]
    assert fa.told(found.document) == [
        f'Left out of date: {DECISION}, which {SOURCE_DOC} names through verified-by: "{deferral}"'
    ]
    assert fa.counted_told(found.document) == (0, 0, 1, 0)


def test_a_base_that_moved_on_is_outdated(
    fa: ModuleType, make_adopter_repo: MakeAdopterRepo, pkit_here: Runner
) -> None:
    repo, head = _branch_with_an_answer(make_adopter_repo)
    repo.checkout("main")
    repo.commit("main moves on", {"src/core/engine.py": "ENGINE = 2\n"})
    found = fa.derive(head, "main")
    assert found.problem is None and found.outdated


def test_checked_reads_the_answers_and_no_friction_settings(
    fa: ModuleType, make_adopter_repo: MakeAdopterRepo, pkit_here: Runner, monkeypatch
) -> None:
    """The narrower run, for a reader that needs only the answers: the change check
    alone, with no reading of the friction settings at either end of the change."""
    _repo, head = _branch_with_an_answer(make_adopter_repo)

    def settings_read(*_args: Any) -> Any:
        raise AssertionError("checked read the friction settings")

    monkeypatch.setattr(fa, "settings_change", settings_read)
    found = fa.checked(head, "main")
    assert found.problem is None, found.problem
    assert [(a["location"], a["answer"]) for a in found.answers] == [("docs/guide.md", "unchanged")]
    assert found.settings == ()


HEAD_OID = "c" * 40


def _clone_git(monkeypatch, fa: ModuleType, *, holds: bool, fetch_brings: bool) -> list[tuple]:
    """`git` as a clone answers it, recorded: whether it holds `HEAD_OID`, and
    whether a fetch brings it."""
    held = {HEAD_OID} if holds else set()
    calls: list[tuple] = []

    def git(*argv: str) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        if argv[0] == "cat-file":
            return subprocess.CompletedProcess(argv, 0 if HEAD_OID in held else 1, "", "")
        if argv[0] == "fetch":
            if not fetch_brings:
                return subprocess.CompletedProcess(argv, 128, "", "fatal: couldn't find ref\n")
            held.add(HEAD_OID)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(fa, "_git", git)
    return calls


def _base_resolved(fa: ModuleType, monkeypatch, ref: str, resolved: str | None) -> None:
    """The backbone resolves every base named to `ref`, `resolved` as it says."""
    base = fa.default_branch.Base(ref, "e" * 40, None, None, resolved)
    monkeypatch.setattr(fa.default_branch, "check_base", lambda _named=None: base)


@pytest.mark.parametrize(
    ("cross_repository", "remote", "ref"),
    [(False, "fork", "refs/heads/feat/7-x"), (True, "upstream", "refs/pull/7/head")],
    ids=["same-repository", "fork"],
)
def test_a_head_this_clone_lacks_is_fetched_from_its_source(
    fa: ModuleType, monkeypatch, cross_repository: bool, remote: str, ref: str
) -> None:
    """A PR from the base's own repository is fetched from its branch, on the remote
    the branch is pushed to. One from a fork is fetched by the ref the base repository
    keeps for it, on the base's remote as the base is fetched, never the branch's."""
    calls = _clone_git(monkeypatch, fa, holds=False, fetch_brings=True)
    _base_resolved(fa, monkeypatch, "upstream/main", "remote")
    source = fa.pull_request_source(
        "feat/7-x", 7, cross_repository=cross_repository, base="main", remote="fork"
    )
    assert source == fa.Source(remote, ref)
    assert fa.fetch_head(HEAD_OID, source) is None
    assert ("fetch", "--quiet", remote, ref) in calls


@pytest.mark.parametrize("resolved", ["local", None], ids=["local-branch", "revision"])
def test_a_base_that_names_no_remote_s_branch_is_fetched_from_origin(
    fa: ModuleType, monkeypatch, resolved: str | None
) -> None:
    _base_resolved(fa, monkeypatch, "main", resolved)
    assert fa.base_remote("main") == "origin"


def test_a_head_this_clone_holds_is_not_fetched(fa: ModuleType, monkeypatch) -> None:
    calls = _clone_git(monkeypatch, fa, holds=True, fetch_brings=True)
    assert fa.fetch_head(HEAD_OID, fa.Source("origin", "refs/heads/feat/7-x")) is None
    assert [argv for argv in calls if argv[0] == "fetch"] == []


def test_a_head_no_fetch_brings_makes_the_derivation_unreadable(
    fa: ModuleType, monkeypatch
) -> None:
    """Never a pass on a guess: the check is not run on a head the clone lacks."""
    _clone_git(monkeypatch, fa, holds=False, fetch_brings=False)
    monkeypatch.setattr(fa, "_refresh_base", lambda base: None)

    def run_check(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("the check ran on a head the clone lacks")

    monkeypatch.setattr(fa, "_run_check", run_check)
    found = fa.checked(HEAD_OID, "main", source=fa.Source("origin", "refs/heads/feat/7-x"))
    assert found.document is None
    assert found.problem == (
        "the head ccccccc is not in this clone, and fetching refs/heads/feat/7-x from origin "
        "failed: fatal: couldn't find ref"
    )


def test_no_document_is_unreadable_never_a_pass(
    fa: ModuleType, make_adopter_repo: MakeAdopterRepo, pkit_here: Runner
) -> None:
    _repo, head = _branch_with_an_answer(make_adopter_repo)
    found = fa.derive(head, "no-such-base")
    assert found.document is None and found.answers == ()
    assert found.problem is not None and "no-such-base" in found.problem


@pytest.mark.parametrize(
    ("returncode", "stdout", "why"),
    [
        (0, '{"schema_version": 2, "answers": []}', "answered schema_version 2; this reads 1"),
        (0, '{"schema_version": 1, "findings": []}', "lists no answers"),
        (1, "", "it exited 1: Error: boom, with no JSON document"),
        (2, '{"schema_version": 1, "answers": []}', "it exited 2: Error: boom"),
    ],
)
def test_a_document_the_list_cannot_be_read_from_is_unreadable(
    fa: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    stdout: str,
    why: str,
) -> None:
    def run(argv: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, returncode, stdout, "Error: boom\n")

    monkeypatch.setattr(fa.subprocess, "run", run)
    found = fa._run_check(HEAD, "main", cwd=None)
    assert isinstance(found, fa._NoDocument) and why in found.why and not found.elsewhere


def test_enforcing_modes_exit_1_still_carries_the_document(
    fa: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[list[str]] = []

    def run(argv: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        seen.append(argv)
        return subprocess.CompletedProcess(argv, 1, '{"schema_version": 1, "answers": []}', "")

    monkeypatch.setattr(fa.subprocess, "run", run)
    assert fa._run_check(HEAD, "integration/7-x", cwd=None) == {"schema_version": 1, "answers": []}
    assert seen == [
        ["pkit", "friction", "check", "--json", "--base", "integration/7-x", "--head", HEAD]
    ]


def test_the_answers_as_the_gate_reads_them_name_no_head_and_fetch_nothing(
    fa: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`written` runs the change check as the project's gate runs it: the base named,
    no `--head`, so the backbone reads HEAD and `$PKIT_CHECK_HEAD` itself, routing off,
    and nothing fetched first. Enforcing mode's exit 1 still carries the answers."""
    seen: list[tuple[list[str], str | None]] = []
    document = {"schema_version": 1, "answers": [{"location": "docs/guide.md"}]}

    def run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen.append((argv, kwargs["env"].get("PKIT_NO_ROUTE")))
        return subprocess.CompletedProcess(argv, 1, json.dumps(document), "")

    monkeypatch.setattr(fa.subprocess, "run", run)
    found = fa.written("origin/main")
    assert (found.problem, found.answers) == (None, ({"location": "docs/guide.md"},))
    assert seen == [(["pkit", "friction", "check", "--json", "--base", "origin/main"], "1")]


def test_answers_the_gate_cannot_read_are_a_problem_never_an_empty_list(
    fa: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    def run(argv: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 2, "", "Error: the base main does not resolve\n")

    monkeypatch.setattr(fa.subprocess, "run", run)
    found = fa.written("main")
    assert found.answers == ()
    assert found.problem == (
        "`pkit friction check --json --base main`: it exited 2: "
        "Error: the base main does not resolve"
    )


def test_the_check_runs_unrouted_with_the_base_named_whatever_the_environment(
    fa: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Both runs — from the working directory and from a temporary checkout — run
    the same `pkit`, routing off, and the base is the one named, never the
    environment's `$PKIT_CHECK_BASE`."""
    monkeypatch.setenv("PKIT_CHECK_BASE", "elsewhere")
    seen: list[tuple[list[str], Any, str | None]] = []

    def run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen.append((argv, kwargs.get("cwd"), kwargs["env"].get("PKIT_NO_ROUTE")))
        return subprocess.CompletedProcess(argv, 0, '{"schema_version": 1, "answers": []}', "")

    monkeypatch.setattr(fa.subprocess, "run", run)
    fa._run_check(HEAD, "main", cwd=None)
    fa._run_check(HEAD, "main", cwd=tmp_path)
    assert [(argv[argv.index("--base") + 1], cwd, unrouted) for argv, cwd, unrouted in seen] == [
        ("main", None, "1"),
        ("main", tmp_path, "1"),
    ]


def test_only_the_resolver_refusal_is_answered_from_a_checkout(
    fa: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The backbone's refusal to run a resolver away from the head is told apart
    from every other failure, which is kept as the first run gave it."""
    refusal = (
        "Error: --head 1a2b3c4: the anchor source 'alpha' is resolved by its capability's "
        "command, which runs in the working tree and reads what is there — and the working\n"
        "tree is not 1a2b3c4 (HEAD is at 0000000). Run from a checkout at 1a2b3c4: HEAD at "
        "1a2b3c4, nothing uncommitted.\n"
    )
    stderr = [refusal]

    def run(argv: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 1, "", stderr[0])

    monkeypatch.setattr(fa.subprocess, "run", run)
    found = fa._run_check(HEAD, "main", cwd=None)
    assert isinstance(found, fa._NoDocument) and found.elsewhere
    stderr[0] = "Error: the base main does not resolve\n"
    found = fa._run_check(HEAD, "main", cwd=None)
    assert isinstance(found, fa._NoDocument) and not found.elsewhere


def test_a_base_that_cannot_be_fetched_is_unreadable(
    fa: ModuleType, make_adopter_repo: MakeAdopterRepo, pkit_here: Runner
) -> None:
    repo, head = _branch_with_an_answer(make_adopter_repo)
    repo.git("remote", "add", "origin", str(repo.root / "no-such-remote"))
    repo.git("update-ref", "refs/remotes/origin/main", repo.git("rev-parse", "main").stdout.strip())
    found = fa.derive(head, "main")
    assert found.document is None
    assert (
        found.problem is not None and "the base origin/main could not be fetched" in found.problem
    )


@pytest.mark.process(
    "derive's checkout path end to end: the backbone refuses a registered kind's "
    "resolver away from the head, then runs it from a temporary checkout"
)
def test_a_resolver_runs_from_a_temporary_checkout_of_the_head(
    fa: ModuleType, make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path
) -> None:
    """A registered kind's resolver runs only from a checkout at the head named; run
    from `main`, the answers are derived from a checkout of the head made for it and
    removed after."""
    repo = make_adopter_repo()
    repo.write({CONFIG: friction_config(mode="enforcing"), **SOURCE, "docs/guide.md": guide()})
    register_kinds(repo.root, "kinds", kinds={"source": "resolve"}, script_body=RESOLVING)
    repo.write({"sources/alpha.md": "alpha\n"})
    repo.write({"docs/sourced.md": document("sourced", anchors={"source": ["alpha"]}, at=T1)})
    repo.commit("base", files=None)
    repo.checkout("feature", create=True)
    repo.commit("the source changes", {"sources/alpha.md": "alpha, captured again\n"})
    deferred = document(
        "sourced",
        anchors={"source": ["alpha"]},
        at=T1,
        deferred=[("source", "alpha", "the recapture is checked with the next release")],
    )
    repo.commit("defer the source", {"docs/sourced.md": deferred})
    head = repo.head()
    repo.checkout("main")

    refused = subprocess.run(
        ["pkit", "friction", "check", "--json", "--base", "main", "--head", head],
        cwd=repo.root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert refused.returncode == 1 and "Run from a checkout at" in refused.stderr

    found = fa.derive(head, "main")
    assert found.problem is None, found.problem
    assert [(a["location"], a["answer"], a["reason"]) for a in found.answers] == [
        ("docs/sourced.md", "deferred", "the recapture is checked with the next release")
    ]
    listed = repo.git("worktree", "list", "--porcelain").stdout
    assert listed.count("worktree ") == 1, listed


def _branch_needing_its_resolver(make_adopter_repo: MakeAdopterRepo) -> tuple[AdopterRepo, str]:
    """A change whose list needs a registered kind's resolver, the clone on `main`."""
    repo = make_adopter_repo()
    repo.write({CONFIG: friction_config(mode="enforcing"), **SOURCE, "docs/guide.md": guide()})
    register_kinds(repo.root, "kinds", kinds={"source": "resolve"}, script_body=RESOLVING)
    repo.write({"sources/alpha.md": "alpha\n"})
    repo.write({"docs/sourced.md": document("sourced", anchors={"source": ["alpha"]}, at=T1)})
    repo.commit("base", files=None)
    repo.checkout("feature", create=True)
    repo.commit("the source changes", {"sources/alpha.md": "alpha, captured again\n"})
    deferred = document(
        "sourced",
        anchors={"source": ["alpha"]},
        at=T1,
        deferred=[("source", "alpha", "the recapture is checked with the next release")],
    )
    repo.commit("defer the source", {"docs/sourced.md": deferred})
    head = repo.head()
    repo.checkout("main")
    return repo, head


def test_no_checkout_is_made_when_the_first_run_answers(
    fa: ModuleType,
    make_adopter_repo: MakeAdopterRepo,
    pkit_here: Runner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, head = _branch_with_an_answer(make_adopter_repo)
    repo.checkout("main")

    def no_checkout(_head: str) -> Any:
        raise AssertionError("a temporary checkout was made")

    monkeypatch.setattr(fa, "_checkout", no_checkout)
    found = fa.derive(head, "main")
    assert found.problem is None and len(found.answers) == 1


def test_a_failure_other_than_the_resolver_refusal_is_kept_with_no_checkout(
    fa: ModuleType,
    make_adopter_repo: MakeAdopterRepo,
    pkit_here: Runner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, head = _branch_with_an_answer(make_adopter_repo)
    repo.checkout("main")
    repo.write({"notes.txt": "uncommitted\n"})
    monkeypatch.setattr(fa, "_checkout", lambda _head: pytest.fail("a checkout was made"))
    monkeypatch.setattr(fa, "_refresh_base", lambda _base: None)
    found = fa.derive(head, "no-such-base")
    assert found.document is None and found.problem is not None
    assert "--base no-such-base" in found.problem


def test_a_check_that_raises_inside_the_checkout_leaves_nothing_behind(
    fa: ModuleType,
    make_adopter_repo: MakeAdopterRepo,
    pkit_here: Runner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, head = _branch_needing_its_resolver(make_adopter_repo)
    made: list[Path] = []
    mkdtemp = fa.tempfile.mkdtemp

    def recorded(**kwargs: Any) -> str:
        made.append(Path(mkdtemp(**kwargs)))
        return str(made[-1])

    run_check = fa._run_check

    def raising_inside(head_: str, base: str, *, cwd: Path | None) -> Any:
        if cwd is not None:
            assert (cwd / ".git").is_file()  # a linked worktree, made for this run
            raise RuntimeError("the check broke")
        return run_check(head_, base, cwd=cwd)

    monkeypatch.setattr(fa.tempfile, "mkdtemp", recorded)
    monkeypatch.setattr(fa, "_run_check", raising_inside)
    with pytest.raises(RuntimeError, match="the check broke"):
        fa.derive(head, "main")
    (scratch,) = made
    assert not scratch.exists()
    listed = repo.git("worktree", "list", "--porcelain").stdout
    assert listed.count("worktree ") == 1, listed
    assert not (repo.root / ".git" / "worktrees").exists() or not any(
        (repo.root / ".git" / "worktrees").iterdir()
    )


@pytest.mark.process(
    "derive's checkout path, whose check at the head starts the fixture kind's "
    "resolver, a script with no main that only a process runs"
)
def test_only_this_runs_worktree_is_removed(
    fa: ModuleType,
    make_adopter_repo: MakeAdopterRepo,
    pkit_on_path: Path,
    tmp_path: Path,
) -> None:
    """Cleanup takes away the checkout this run added, and leaves another stale
    worktree record — one a prune would take — as it found it."""
    repo, head = _branch_needing_its_resolver(make_adopter_repo)
    other = tmp_path / "someone-elses"
    repo.git("worktree", "add", "--detach", "--quiet", str(other), head)
    shutil.rmtree(other)  # stale: what `git worktree prune` would remove
    found = fa.derive(head, "main")
    assert found.problem is None, found.problem
    listed = repo.git("worktree", "list", "--porcelain").stdout
    assert str(other) in listed and listed.count("worktree ") == 2, listed


def test_a_termination_signal_removes_the_checkout(
    make_adopter_repo: MakeAdopterRepo, tmp_path: Path
) -> None:
    """SIGTERM — a harness's timeout — while the temporary checkout exists unwinds
    through its removal."""
    repo = make_adopter_repo()
    repo.write({"a.txt": "a\n"})
    repo.commit("base", files=None)
    script = tmp_path / "terminate.py"
    script.write_text(
        "import os, signal, sys\n"
        f"sys.path.insert(0, {str(LIB_DIR)!r})\n"
        "import friction_answers as fa\n"
        f"with fa._checkout({repo.head()!r}) as (path, why):\n"
        "    assert path is not None, why\n"
        "    print(path.parent, flush=True)\n"
        "    os.kill(os.getpid(), signal.SIGTERM)\n"
        "    raise AssertionError('not terminated')\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, str(script)], cwd=repo.root, capture_output=True, text=True, check=False
    )
    assert proc.returncode == 128 + signal.SIGTERM, proc.stderr
    assert not Path(proc.stdout.strip()).exists()
    assert repo.git("worktree", "list", "--porcelain").stdout.count("worktree ") == 1


# ---- the friction settings a change alters -----------------------------------------


def test_a_change_that_sets_friction_dormant_tells_the_setting(
    fa: ModuleType, make_adopter_repo: MakeAdopterRepo, pkit_here: Runner
) -> None:
    """The settings decide what the change check asks: a change that empties the
    places makes the check dormant at its head, so it gives no answer — and the
    person is told the settings it altered instead, as they were and as they are,
    read through the backbone's discovery at each commit."""
    repo = make_adopter_repo()
    without_shipped_rule_sets(repo)  # their folder would keep the check awake
    repo.write({CONFIG: friction_config(mode="enforcing"), **SOURCE, "docs/guide.md": guide()})
    repo.commit("base", files=None)
    repo.checkout("feature", create=True)
    repo.commit("change the CLI", {"src/cli/main.py": "print('cli v2')\n"})
    repo.commit("friction off", {CONFIG: friction_config(mode="enforcing", places=())})
    head = repo.head()
    found = fa.derive(head, "main")
    assert found.problem is None, found.problem
    assert found.answers == () and found.listed
    assert [(s.key, s.before, s.after) for s in found.settings] == [(fa.PLACES, ("docs",), ())]
    assert fa.told(found.document, found.settings) == ["Checked locations: docs → none"]


@pytest.mark.process(
    "settings_change's end-to-end test: two real `pkit friction artefacts --json "
    "--at` documents, the script-to-backbone contract"
)
def test_a_change_that_excludes_an_artefact_lists_it(
    fa: ModuleType, make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path
) -> None:
    repo = make_adopter_repo()
    repo.write({CONFIG: friction_config(mode="enforcing"), **SOURCE, "docs/guide.md": guide()})
    repo.write({"docs/other.md": document("other", anchors={"path": ["src/core/**"]}, at=T1)})
    repo.commit("base", files=None)
    before = repo.head()
    excluding = friction_config(mode="enforcing", exclude=["docs/guide.md"])
    repo.commit("leave the guide out", {CONFIG: excluding})
    assert [(s.key, s.before, s.after) for s in fa.settings_change(before, repo.head())] == [
        (fa.EXCLUDED, (), ("docs/guide.md",))
    ]
    assert fa.settings_change(before, before) == ()


def test_settings_that_cannot_be_read_make_the_derivation_unreadable(
    fa: ModuleType, make_adopter_repo: MakeAdopterRepo, pkit_here: Runner
) -> None:
    repo = make_adopter_repo()
    repo.write({CONFIG: friction_config(mode="enforcing"), **SOURCE, "docs/guide.md": guide()})
    repo.commit("base", files=None)
    before = repo.head()
    repo.commit("a broken configuration", {CONFIG: "friction: [unclosed\n"})
    found = fa.settings_change(before, repo.head())
    assert isinstance(found, str) and "pkit friction artefacts --json --at" in found
    assert fa.settings_change("", repo.head()) == (
        "the change check named no commit the head left its base at"
    )


# ---- the author's sentences (DEC-055 point 1, DEC-065 point 3) ------------------

#: A description whose author says what changed in each updated document.
SAID_BODY = (
    "Closes #42\n\n## Summary\n\nDone.\n\n"
    "## What changed in each updated document\n\n"
    "- `docs/a.md`: The install steps now name the renamed flag\n"
    "  and its old spelling.\n"
    "* `tech-docs/actors.md#ACT-one` — The actor is told what changed.\n"
    "- `docs/b.md` - Second item for b.\n"
    "- not a document\n"
    "- `docs/a.md`: A second sentence for a, not read.\n\n"
    "```\n- `docs/fenced.md`: inside a fence, not read\n```\n\n"
    "## Doc impact\n\n- `docs/elsewhere.md`: under another heading, not read\n"
)


def test_the_sentences_schema_heading_is_the_module_s(fa: ModuleType) -> None:
    schema = YAML(typ="safe").load((CAP_ROOT / "schemas" / "body-format.yaml").read_text("utf-8"))
    assert schema["friction_answers_marker"]["sentences_heading"] == fa.SENTENCES_HEADING


def test_the_sentences_are_read_from_the_author_s_section(fa: ModuleType) -> None:
    """One list item per document, the document in a code span, then the sentence;
    an item runs on over the lines under it; the first for a document wins; a
    fence, another section and an item naming no document are not read."""
    assert fa.sentences(SAID_BODY) == {
        "docs/a.md": "The install steps now name the renamed flag and its old spelling.",
        "tech-docs/actors.md#ACT-one": "The actor is told what changed.",
        "docs/b.md": "Second item for b.",
    }
    assert fa.sentences(BODY) == {}


@pytest.mark.parametrize(
    ("lines", "read"),
    [
        # A numbered item is a list item too.
        (["1. `docs/a.md`: Numbered."], {"docs/a.md": "Numbered."}),
        # A line that starts with `#` but is no heading runs the item on.
        (
            ["- `docs/a.md`: Rewrote the intro, as", "#123 asked."],
            {"docs/a.md": "Rewrote the intro, as #123 asked."},
        ),
        # A nested item is no sentence, and ends the one above it.
        (
            ["- `docs/a.md`: The intro.", "  - `docs/b.md` is linked from it", "- `docs/b.md`: B."],
            {"docs/a.md": "The intro.", "docs/b.md": "B."},
        ),
        # An HTML comment and a thematic break end an item; nothing after them joins it.
        (
            ["- `docs/a.md`: The intro.", "<!-- one item per document -->"],
            {"docs/a.md": "The intro."},
        ),
        (["- `docs/a.md`: The intro.", "---", "A paragraph."], {"docs/a.md": "The intro."}),
    ],
)
def test_an_item_is_a_top_level_list_item_and_ends_where_markdown_ends_it(
    fa: ModuleType, lines: list[str], read: dict[str, str]
) -> None:
    body = "## What changed in each updated document\n\n" + "\n".join(lines) + "\n"
    assert fa.sentences(body) == read


#: The form a warning names for a sentence.
FORM = "- `path`: sentence"


@pytest.mark.parametrize(
    ("lines", "read", "unread"),
    [
        # The read form gives its sentence and draws no warning.
        (["- `docs/a.md`: The intro."], {"docs/a.md": "The intro."}, []),
        # A path in bold, as on PR #1519: no sentence, and its line is named.
        (["- **docs/a.md:** The intro."], {}, [3]),
        # A path with no code span.
        (["- docs/a.md: The intro."], {}, [3]),
        # A bold code span is no code span right after the marker either.
        (["1. **`docs/a.md`**: The intro."], {}, [3]),
        # An item that names its document but gives no words.
        (["- `docs/a.md`:", "", "- `docs/b.md`: B."], {"docs/b.md": "B."}, [3]),
        # A list indented whole: no item starts in the first column.
        (["  - `docs/a.md`: The intro.", "  - `docs/b.md`: B."], {}, [3, 4]),
        # An item nested under a document's item is not one, nor is a thematic break.
        (
            ["- `docs/a.md`: The intro.", "  - **docs/b.md** is linked from it", "* * *"],
            {"docs/a.md": "The intro."},
            [],
        ),
        # An item indented less than the content of the item above is its sibling.
        (["- `docs/a.md`: The intro.", " - **docs/b.md:** B."], {"docs/a.md": "The intro."}, [4]),
        # A paragraph after a blank line ends the list: an indented item opens another.
        (
            ["- `docs/a.md`: The intro.", "", "Also:", "", "  - **docs/b.md:** B."],
            {"docs/a.md": "The intro."},
            [7],
        ),
        # A paragraph or a heading indented less than the item's content ends the list.
        (
            ["1. `docs/a.md`: A.", "", "  para", "   - **b**", "  ### H", " - **c**"],
            {"docs/a.md": "A."},
            [6, 8],
        ),
        # A comment or a fence inside an item's content leaves the list open.
        (
            [
                "- `docs/a.md`: A.",
                "  <!-- note -->",
                "  - nested",
                "  ```",
                "  x",
                "  ```",
                "  - too",
            ],
            {"docs/a.md": "A."},
            [],
        ),
        # Nothing inside an HTML comment renders, so nothing there is read or named.
        (["<!--", "- **docs/a.md:** An example.", "- `docs/b.md`: Another. -->"], {}, []),
        # A paragraph and an item under another heading are not the section's items.
        (["One sentence each:", "", "## Notes", "", "- **x**"], {}, []),
    ],
    ids=[
        "read form",
        "bold path",
        "no code span",
        "bold code span",
        "no words",
        "indented",
        "nested",
        "sibling",
        "new list",
        "outdented",
        "inside an item",
        "comment",
        "not an item",
    ],
)
def test_an_item_the_reading_cannot_read_is_named_by_its_line(
    fa: ModuleType, lines: list[str], read: dict[str, str], unread: list[int]
) -> None:
    """Every item under the heading either gives a sentence or is named, by the line
    it is on in the description, as the line is written."""
    body = "## What changed in each updated document\n\n" + "\n".join(lines) + "\n"
    assert fa.sentences(body) == read
    found = fa.unread(body)
    assert [item.line for item in found] == unread
    assert [item.text for item in found] == [body.split("\n")[n - 1] for n in unread]


def test_the_warning_names_the_line_and_the_form(fa: ModuleType) -> None:
    (item,) = fa.unread(SAID_BODY)  # `- not a document`
    assert (item.line, item.text) == (13, "- not a document")
    assert fa.SENTENCE_FORM == FORM
    assert fa.unread_warning(item) == (
        "line 13 of the description, under `## What changed in each updated document`, is not "
        f'read as a sentence: "- not a document" — write it as "{FORM}", starting in the '
        "line's first column, the document in a code span as the change check names it"
    )


def test_each_updated_document_the_author_gives_no_sentence_is_named(
    fa: ModuleType,
) -> None:
    """For the move to review, which refuses them, and the opening of the pull request,
    which warns of them (DEC-065 point 3): each document the change check marks
    updated, in the check's order, that the author's section gives no sentence for. A
    target revisited by its own change asks for none."""
    document = _document(
        _entry("docs/c.md", "updated"),
        _entry("docs/a.md", "updated"),
        _entry("tech-docs/actors.md#ACT-one", "updated"),
        _entry("docs/b.md", "unchanged", "Holds."),
        _revisit(SOURCE_REQ, "updated"),
    )
    assert fa.unsaid(document, fa.sentences(SAID_BODY)) == ["docs/c.md"]
    assert fa.unsaid(document, fa.sentences(BODY)) == [
        "docs/c.md",
        "docs/a.md",
        "tech-docs/actors.md#ACT-one",
    ]
    assert fa.unsaid(_document(), {}) == []
    assert fa.unsaid_message("docs/c.md") == (
        "docs/c.md is updated in this change, and the description gives no sentence on what "
        "changed in it — under `## What changed in each updated document`, write one on a "
        f'line of its own as "{FORM}", starting in the line\'s first column, the document in '
        "a code span as the change check names it"
    )


def test_a_sentence_on_a_document_the_check_does_not_mark_updated_is_unlisted(
    fa: ModuleType,
) -> None:
    """The documents the change check marks updated, in its order, a target revisited
    by its own change among none of them; each sentence on any other document is
    named, in the sentences' order, with the edit that removes it."""
    document = _document(
        _entry("docs/b.md", "updated"),
        _entry("docs/a.md", "unchanged", "Holds."),
        _revisit(SOURCE_REQ, "updated"),
    )
    assert fa.updated_in(document) == ["docs/b.md"]
    said = fa.sentences(SAID_BODY)
    assert fa.unlisted(document, said) == ["docs/a.md", "tech-docs/actors.md#ACT-one"]
    assert fa.unlisted(_document(), {}) == []
    assert fa.unlisted_warning("docs/a.md", HEAD, 7) == (
        "docs/a.md has a sentence under `## What changed in each updated document`, and the "
        "change check at 1a2b3c4 does not mark it updated, so no reviewer checks the "
        "sentence — remove it from the description with `edit-pr 7 --body-file <file>`"
    )
    assert fa.unlisted_warning("docs/a.md", HEAD).endswith("with `edit-pr`")


def test_a_line_keeps_its_number_past_the_list_and_is_shown_escaped(fa: ModuleType) -> None:
    """A list an earlier run wrote is never read, yet its lines are counted, so the
    number is the line's in the description; a terminal is shown no control
    character of the author's."""
    said = "## What changed in each updated document\n\n- **docs/a.md\x1b[2J:** Done.\n"
    body = f"Closes #42\n\n{_section(fa)}\n\n{said}\n{FOOTER}\n"
    (item,) = fa.unread(body)
    assert body.split("\n")[item.line - 1].startswith("- **docs/a.md")
    assert item.text == "- **docs/a.md\\x1b[2J:** Done."
    assert fa.sentences(body) == {}


def test_a_sentence_inside_a_list_or_the_footer_is_not_read(fa: ModuleType) -> None:
    """A list an earlier run wrote is stripped first, and so is the footer: a sentence
    either gives is never read as the author's."""
    region = _section(fa, "- `docs/a.md`: Old.").split("\n", 2)[2]
    body = f"{SAID_BODY}\n{fa.SENTENCES_HEADING}\n\n{region}\n"
    assert fa.sentences(body)["docs/a.md"].startswith("The install steps")
    alone = f"{fa.SENTENCES_HEADING}\n\n{region}\n"
    assert fa.sentences(alone) == {}
    footer = FOOTER.replace("---", f"{fa.SENTENCES_HEADING}\n\n- `docs/b.md`: In the footer.")
    assert fa.sentences(f"{BODY}\n{footer}\n") == {}


def test_each_updated_document_gives_its_sentence_or_says_there_is_none(fa: ModuleType) -> None:
    """Only the sentences of documents the change check marks updated are told; any
    other sentence is unlisted."""
    document = _document(
        _entry("docs/a.md", "updated", changed=[("path", "src/cli/**")]),
        _entry("docs/c.md", "updated", status="bump"),
        _entry("docs/b.md", "unchanged", "Holds."),
    )
    said = fa.sentences(SAID_BODY)
    assert fa.unsaid(document, said) == ["docs/c.md"]
    assert fa.told(document, (), said) == [
        'What changed in docs/a.md: "The install steps now name the renamed flag and its old '
        'spelling."',
        "What changed in docs/c.md: the pull request's author has not said",
    ]


# -- a later head an authorisation covers (DEC-055 point 3) -------------------------


@pytest.mark.process(
    "covers' end-to-end test: three real `pkit friction since` runs over a real history"
)
def test_the_backbone_says_a_later_head_of_answers_is_covered(
    fa: ModuleType, make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path
) -> None:
    """The real `pkit friction since`: the head after a revalidation alone, in an answer
    file the change adds, is covered; the head after the code change is not, and the
    change outside is named. An answer written in the guide's block is not covered."""
    repo = make_adopter_repo()
    repo.write({CONFIG: friction_config(mode="enforcing"), **SOURCE, "docs/guide.md": guide()})
    repo.commit("base", files=None)
    repo.checkout("feature", create=True)
    changed = repo.commit("change the CLI", {"src/cli/main.py": "print('cli v2')\n"})
    answer = ".pkit/project/friction/answers/20261003T100000Z-0a1b2c3d.yaml"
    text = (
        "answers:\n  - artefact: docs/guide.md\n    revalidated:\n"
        f"      at: 2026-10-03T10:00:00Z\n      outcome: unchanged\n"
        f"      unchanged-because: {BECAUSE}\n"
    )
    head = repo.commit("revalidate the guide", {answer: text})
    found = fa.covers(changed[:9], head, "main")
    assert found == fa.Coverage(changed, head, True, inside=1)
    main = repo.git("rev-parse", "main").stdout.strip()
    found = fa.covers(main, head, "main")
    assert (found.covered, found.problem) == (False, None)
    assert found.outside == (f"src/cli/main.py ({changed[:7]}: not an answer file)",)
    with blocks_in_history():  # an answer left in the block, which validation fails
        in_block = repo.commit(
            "answer in the block",
            {"docs/guide.md": guide(at="2026-10-04T10:00:00Z", because=BECAUSE)},
        )
    found = fa.covers(head, in_block, "main")
    assert found.outside == (f"docs/guide.md ({in_block[:7]}: not an answer file)",)


def _answering(
    fa: ModuleType, monkeypatch: pytest.MonkeyPatch, returncode: int, stdout: str
) -> list[tuple[list[str], str | None]]:
    """The backbone stood in for: each run's argv and whether routing was off."""
    seen: list[tuple[list[str], str | None]] = []

    def run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen.append((argv, kwargs["env"].get("PKIT_NO_ROUTE")))
        return subprocess.CompletedProcess(argv, returncode, stdout, "Error: boom\n")

    monkeypatch.setattr(fa.subprocess, "run", run)
    monkeypatch.setattr(fa, "_refresh_base", lambda base: None)
    return seen


def _since_document(**fields: Any) -> str:
    document = {
        "schema_version": 2,
        "since": MERGE_BASE,
        "head": HEAD,
        "all_inside": True,
        "reason": None,
        "inside": [".pkit/project/friction/answers/one.yaml"],
        "outside": [],
        **fields,
    }
    return json.dumps(document)


def test_the_backbone_is_asked_unrouted_with_the_base_named(
    fa: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PKIT_CHECK_BASE", "elsewhere")
    seen = _answering(fa, monkeypatch, 0, _since_document())
    assert fa.covers("0000000", HEAD, "integration/7-x").covered
    argv = ["pkit", "friction", "since", "0000000", "--head", HEAD, "--base", "integration/7-x"]
    assert seen == [([*argv, "--json"], "1")]


@pytest.mark.parametrize(
    ("returncode", "stdout", "why"),
    [
        (1, "", "it exited 1: Error: boom"),
        (0, "not json", "its answer is not JSON"),
        (0, '{"schema_version": 1}', "not a document of version 2"),
        (0, '{"schema_version": 2, "since": "a", "head": "b"}', "lacks what an answer needs"),
        (0, _since_document(all_inside="yes"), "lacks what an answer needs"),
        (0, _since_document(all_inside=False), "and the changes it names disagree"),
        (
            0,
            _since_document(outside=[{"path": "a.py", "commit": HEAD, "why": "added"}]),
            "and the changes it names disagree",
        ),
        (0, _since_document(reason="it was rebased"), "and the changes it names disagree"),
    ],
)
def test_an_answer_that_cannot_be_read_is_never_covered(
    fa: ModuleType, monkeypatch: pytest.MonkeyPatch, returncode: int, stdout: str, why: str
) -> None:
    _answering(fa, monkeypatch, returncode, stdout)
    found = fa.covers("0000000", HEAD, "main")
    assert not found.covered
    assert found.problem is not None and why in found.problem


def test_a_base_that_cannot_be_fetched_is_never_covered(
    fa: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen = _answering(fa, monkeypatch, 0, _since_document())
    monkeypatch.setattr(fa, "_refresh_base", lambda base: "the base origin/main is gone")
    found = fa.covers("0000000", HEAD, "main")
    assert (found.covered, found.problem) == (False, "the base origin/main is gone")
    assert seen == []


def test_the_changes_outside_are_named_with_the_reason_first(
    fa: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = [{"path": "src/\x1b[31mx.py", "commit": HEAD, "why": "added"}]
    document = _since_document(all_inside=False, reason="it was rebased", outside=outside)
    _answering(fa, monkeypatch, 0, document)
    found = fa.covers("0000000", HEAD, "main")
    assert found.outside == ("it was rebased", f"src/\\x1b[31mx.py ({HEAD[:7]}: added)")


# ---- the merge as it would land (DEC-055 point 6, #2228) --------------------------

#: A page a change adds, anchored to the engine. New in its change, it needs no answer.
CORE_PAGE = "docs/core.md"
CORE = document("core", anchors={"path": ["src/core/**"]})


def _origin(repo: AdopterRepo) -> Path:
    """A bare origin the repository's `main` is pushed to, so the base is a remote's."""
    origin = repo.root.parent / f"{repo.root.name}-origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    repo.git("remote", "add", "origin", str(origin))
    repo.git("push", "-q", "-u", "origin", "main")
    return origin


def _race(make_adopter_repo: MakeAdopterRepo) -> tuple[AdopterRepo, str, str]:
    """A base pushed to its origin, and two branches off it that each pass alone:
    `anchor` adds a page anchored to the engine, and `engine` changes the engine.
    The clone is left on `main`."""
    repo = make_adopter_repo()
    repo.write({CONFIG: friction_config(mode="enforcing"), **SOURCE, "docs/guide.md": guide()})
    repo.commit("base", files=None)
    _origin(repo)
    repo.checkout("anchor", create=True)
    repo.commit("add a page on the engine", {CORE_PAGE: CORE})
    anchor = repo.head()
    repo.checkout("main")
    repo.checkout("engine", create=True)
    repo.commit("change the engine", {"src/core/engine.py": "ENGINE = 2\n"})
    engine = repo.head()
    repo.checkout("main")
    return repo, anchor, engine


def _land_elsewhere(repo: AdopterRepo, branch: str) -> str:
    """`branch` squash-merged into the origin's `main`, as the host lands a pull request,
    with this clone's `origin/main` left where it was: only a fetch shows the landing."""
    before = repo.git("rev-parse", "origin/main").stdout.strip()
    repo.squash_merge(branch)
    landed = repo.head()
    repo.git("push", "-q", "origin", "main")
    repo.git("reset", "-q", "--hard", before)
    repo.git("update-ref", "refs/remotes/origin/main", before)
    return landed


@pytest.mark.process(
    "merged's end-to-end test: the race shows only through a real merge, a worktree "
    "checkout and the real check at the merge, which names the change's own head"
)
def test_two_changes_that_pass_alone_are_refused_together(
    fa: ModuleType, make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path
) -> None:
    """The race of #2228: one change adds an anchor, the other changes what it stands
    on. Each passes merged with the base alone. Once the first lands, the second's
    merge with the base, fetched, fails the change check on the page."""
    repo, anchor, engine = _race(make_adopter_repo)
    for head in (anchor, engine):
        alone = fa.merged(head, "main")
        assert alone.problem is None, alone.problem
        assert (alone.failed, alone.refused, alone.conflicts) == (False, (), ())
    landed = _land_elsewhere(repo, "anchor")

    found = fa.merged(engine, "main")
    assert found.problem is None, found.problem
    assert found.tip == landed
    assert found.failed
    assert [(f["location"], f["kind"]) for f in found.refused] == [(CORE_PAGE, "friction")]
    # The merge is a commit of its own, on no branch, whose parents are the tip and
    # the head; the clone's branch, working tree and worktrees are as they were.
    parents = repo.git("rev-list", "--parents", "-n", "1", found.merge).stdout.split()
    assert parents == [found.merge, landed, engine]
    assert repo.git("branch", "--all", "--contains", found.merge).stdout == ""
    assert (repo.current_branch(), repo.git("status", "--porcelain").stdout) == ("main", "")
    listed = repo.git("worktree", "list", "--porcelain").stdout
    assert listed.count("worktree ") == 1, listed


def test_the_merge_is_built_even_where_signing_is_asked_for(
    fa: ModuleType,
    make_adopter_repo: MakeAdopterRepo,
    pkit_here: Runner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The merge reaches no branch, so it is never signed: with signing asked for, and a
    signing program that refuses (the suite's), it is built all the same. The check at
    the merge is stood in: it reads the merge only once it is built."""
    repo, _anchor, engine = _race(make_adopter_repo)
    _land_elsewhere(repo, "anchor")
    repo.git("config", "commit.gpgsign", "true")
    passing = {"schema_version": 1, "failed": False, "findings": [], "answers": []}
    monkeypatch.setattr(fa, "_run_check", lambda *_a, **_k: passing)
    found = fa.merged(engine, "main")
    assert found.problem is None, found.problem
    assert "gpgsig" not in repo.git("cat-file", "-p", found.merge).stdout


def test_a_head_that_holds_the_tip_its_own_check_read_is_not_checked_again(
    fa: ModuleType,
    make_adopter_repo: MakeAdopterRepo,
    pkit_here: Runner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Where the head's own check read the tip the fetch finds, and the head holds it,
    the merge is the head and that check is the merge's: nothing runs twice."""
    repo, _anchor, engine = _race(make_adopter_repo)
    tip = repo.git("rev-parse", "main").stdout.strip()
    checked = {"failed": False, "findings": [], "base": {"tip": tip, "outdated": False}}

    def no_run(*_: Any, **__: Any) -> Any:
        raise AssertionError("the check ran again")

    monkeypatch.setattr(fa, "_run_check", no_run)
    found = fa.merged(engine, "main", checked=checked)
    assert (found.merge, found.tip, found.document) == (engine, tip, checked)
    # A head that does not hold the tip its check read is merged and checked anew.
    moved = {**checked, "base": {"tip": tip, "outdated": True}}
    with pytest.raises(AssertionError, match="the check ran again"):
        fa.merged(engine, "main", checked=moved)


def test_the_check_runs_at_the_merge_with_the_head_as_its_own_head(
    fa: ModuleType,
    make_adopter_repo: MakeAdopterRepo,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """From a checkout of the merge, against the tip, unrouted, with the head named as
    the change's own head, as a pull request's checks run it (COR-062 point 4). The
    reading of the base is answered by the backbone's CLI in this process."""
    repo, _anchor, engine = _race(make_adopter_repo)
    landed = _land_elsewhere(repo, "anchor")
    real = subprocess.run
    pkit = InProcessPkit()
    seen: list[tuple[list[str], str, str, str | None, str | None]] = []

    def run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if argv[:3] == ["pkit", "repository", "base"]:
            return pkit(argv, **{key: kwargs[key] for key in MODELLED if key in kwargs})
        if argv[:3] != ["pkit", "friction", "check"]:
            return real(argv, **kwargs)
        cwd = str(kwargs.get("cwd"))
        at = real(["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True)
        env = kwargs.get("env") or {}
        seen.append(
            (argv, cwd, at.stdout.strip(), env.get("PKIT_CHECK_HEAD"), env.get("PKIT_NO_ROUTE"))
        )
        document = {"schema_version": 1, "failed": False, "findings": [], "answers": []}
        return subprocess.CompletedProcess(argv, 0, json.dumps(document), "")

    monkeypatch.setattr(fa.subprocess, "run", run)
    found = fa.merged(engine, "main")
    assert found.problem is None, found.problem
    ((argv, cwd, at, own, unrouted),) = seen
    assert argv == ["pkit", "friction", "check", "--json", "--base", landed]
    assert (at, own, unrouted) == (found.merge, engine, "1")
    assert cwd != str(repo.root) and not Path(cwd).exists()


def test_a_merge_that_conflicts_names_its_files_and_checks_nothing(
    fa: ModuleType, make_adopter_repo: MakeAdopterRepo, pkit_here: Runner
) -> None:
    repo, _anchor, _engine = _race(make_adopter_repo)
    repo.checkout("cli", create=True)
    repo.commit("the CLI, one way", {"src/cli/main.py": "print('cli, one way')\n"})
    head = repo.head()
    repo.checkout("main")
    repo.checkout("other", create=True)
    repo.commit("the CLI, another way", {"src/cli/main.py": "print('cli, another way')\n"})
    repo.checkout("main")
    _land_elsewhere(repo, "other")
    found = fa.merged(head, "main")
    assert found.problem is None, found.problem
    assert (found.conflicts, found.document, found.merge) == (("src/cli/main.py",), None, "")


def test_a_base_that_cannot_be_fetched_leaves_the_merge_unchecked(
    fa: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(fa, "_refresh_base", lambda base: "the base origin/main is gone")
    found = fa.merged(HEAD, "main")
    assert (found.problem, found.document, found.failed) == (
        "the base origin/main is gone",
        None,
        False,
    )


def test_a_check_with_no_document_at_the_merge_is_a_problem_never_a_pass(
    fa: ModuleType,
    make_adopter_repo: MakeAdopterRepo,
    pkit_here: Runner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _anchor, engine = _race(make_adopter_repo)
    _land_elsewhere(repo, "anchor")
    monkeypatch.setattr(fa, "_run_check", lambda *_a, **_k: fa._NoDocument("it exited 2: boom"))
    found = fa.merged(engine, "main")
    assert found.document is None
    assert found.problem is not None and "it exited 2: boom" in found.problem
    listed = repo.git("worktree", "list", "--porcelain").stdout
    assert listed.count("worktree ") == 1, listed


def test_only_the_findings_the_check_fails_on_are_refused(fa: ModuleType) -> None:
    """The kinds the check fails on in enforcing mode name the documents; what it
    only reports, such as answers made apart, refuses nothing."""
    findings = [
        {"location": "docs/a.md", "kind": "answered", "message": "updated"},
        {"location": "docs/b.md", "kind": "friction", "message": "src/** changed"},
        {"location": "docs/c.md", "kind": "answered-apart", "message": "made apart"},
        {"location": "docs/d.md", "kind": "dead-anchor", "message": "matches no file"},
    ]
    found = fa.Merged(
        HEAD, tip=MERGE_BASE, merge=HEAD, document={"failed": True, "findings": findings}
    )
    assert found.failed
    assert [f["location"] for f in found.refused] == ["docs/b.md", "docs/d.md"]
    # In warning mode the check fails nothing: the same findings are reported, refused none.
    passing = fa.Merged(HEAD, document={"failed": False, "findings": findings})
    assert (passing.failed, passing.refused) == (False, ())
    assert [f["location"] for f in passing.failing] == ["docs/b.md", "docs/d.md"]
