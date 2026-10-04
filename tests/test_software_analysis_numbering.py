"""software-analysis: the numbering setting frees a named commit's removed files' numbers (#1342).

Held to software-analysis DEC-001 point 3: an artefact's id is never reused,
and a project may name a commit whose removed files' numbers are free again —
nothing else frees a number. The setting is `numbering.freed-by` in the
capability's project configuration; the stamp (`pkit analysis new`) and the
number check (`pkit analysis check-numbers`) read it from one home, so they
agree on every number:

- a number the default branch's history gave a file a named commit deleted is
  free again — for use cases and journeys alike;
- a file another commit removed, and a file a named commit renamed rather than
  deleted, still holds its number;
- an entry naming no commit here, an ambiguous one, one off the default
  branch's history, or one that is not a commit id refuses the stamp and fails
  the number check, numbered there or not.

Each test runs in a real repository: `main` holds a pilot — an actor, UC-001 to
UC-003 and JRN-001 — whose UC-003 one commit removed and whose other use cases
and journey the next did, and `topic` left `main` before the pilot.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import subprocess
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import (
    JOURNEYS,
    MAIN,
    NUMBERS,
    SA,
    USE_CASES,
    installed,
    new,
    prepare,
    run_script,
    stamped,
)

#: The capability's project configuration, where the setting lies.
SETTING = f"{SA.as_posix()}/project/config.yaml"

#: The pilot's files: the use case one commit removed, and those the next did.
UC_ONE = f"{USE_CASES}/UC-001-one.md"
UC_TWO = f"{USE_CASES}/UC-002-two.md"
UC_THREE = f"{USE_CASES}/UC-003-three.md"
JRN_TRIP = f"{JOURNEYS}/JRN-001-trip.md"

#: The two removals, by where `main` stands: UC-003's, then the rest of the pilot's.
THREE_REMOVED = f"{MAIN}~1"
PILOT_REMOVED = MAIN

#: How many characters of a commit a message shows.
SHORT = 12


# Slow: five stamps, built once per session; the first test to ask pays it in its setup.
def _piloted(repo: AdopterRepo) -> None:
    """`prepare`, `topic` leaving main there; then on main the pilot — the actor
    ACT-tester, UC-001 to UC-003 and JRN-001 through UC-001 and UC-002 — then UC-003
    removed, then UC-001, UC-002 and JRN-001; the actor is kept."""
    prepare(repo)
    repo.checkout("topic", create=True)
    repo.checkout(MAIN)
    stamped(repo, "actor", "tester")
    for slug in ("one", "two", "three"):
        stamped(repo, "use-case", slug, "--actor", "ACT-tester")
    steps = ("--step", "UC-001", "--step", "UC-002")
    stamped(repo, "journey", "trip", "--actor", "ACT-tester", *steps)
    repo.commit("the pilot")
    repo.commit("UC-003 removed", {UC_THREE: None})
    repo.commit("the pilot removed", {UC_ONE: None, UC_TWO: None, JRN_TRIP: None})


@pytest.fixture
def piloted(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    """The project with the pilot added and removed on main (`_piloted`)."""
    return installed(make_adopter_repo, monkeypatch, then=_piloted)


def commit_of(repo: AdopterRepo, name: str) -> str:
    return repo.git("rev-parse", name).stdout.strip()


def free(repo: AdopterRepo, *commits: str) -> None:
    """The setting naming `commits`, written in the working tree; none, no setting."""
    if not commits:
        repo.write({SETTING: None})
        return
    entries = "".join(f'    - "{commit}"\n' for commit in commits)
    repo.write({SETTING: f"schema_version: 1\nnumbering:\n  freed-by:\n{entries}"})


def stamp(repo: AdopterRepo, *args: str) -> tuple[str, list[str]]:
    """A stamp's id and its notes, the file it wrote removed again."""
    completed = new(repo, *args)
    assert completed.returncode == 0, completed.stderr
    *notes, done = completed.stdout.strip().splitlines()
    _stamped, new_id, _at, location = done.split()
    repo.write({location: None})
    return new_id, notes


def numbers(repo: AdopterRepo) -> subprocess.CompletedProcess[str]:
    """`pkit analysis check-numbers --json` against main, as the dispatcher runs it."""
    return run_script(repo, NUMBERS, "--base", MAIN, "--json")


def collisions(repo: AdopterRepo) -> list[str]:
    """The files `pkit analysis check-numbers` finds a number of colliding."""
    completed = numbers(repo)
    findings = json.loads(completed.stdout)["findings"]
    errors = sorted(f["location"] for f in findings if f["severity"] == "error")
    assert completed.returncode == (1 if errors else 0), completed.stderr
    return errors


def freed_note(new_id: str, path: str, added: str, removed: str) -> str:
    return (
        f"{new_id} is free again, freed by {removed[:SHORT]}, as the project's numbering "
        f"setting names: main's history gave it {path} (commit {added[:SHORT]}), which "
        f"{removed[:SHORT]} removed (DEC-001 point 3)"
    )


# --- what it frees, and what it does not (DEC-001 point 3) -------------------------------------


MINE_ONE = f"{USE_CASES}/UC-001-mine.md"
MINE_THREE = f"{USE_CASES}/UC-003-mine.md"


# Slow by design: four stamps and four number checks, each starting `pkit` processes.
@pytest.mark.parametrize(
    ("named", "next_use_case", "colliding"),
    [
        ((), "UC-004", [MINE_ONE, MINE_THREE]),
        ((PILOT_REMOVED, THREE_REMOVED), "UC-001", []),
        ((PILOT_REMOVED,), "UC-004", [MINE_THREE]),
        ((THREE_REMOVED,), "UC-003", [MINE_ONE]),
    ],
    ids=["no-setting", "both-removals", "the-pilot-s-removal", "uc-003-s-removal"],
)
def test_the_stamp_and_the_number_check_free_only_what_a_named_commit_removed(
    piloted: AdopterRepo, named: tuple[str, ...], next_use_case: str, colliding: list[str]
) -> None:
    """The stamp on main numbers past what the history counts, and the number check on
    `topic` — holding UC-001 and UC-003 of its own, numbered before main's pilot — fails
    on exactly the numbers the stamp counts: a number the history gave a file a named
    commit removed is free; a file another commit removed still holds its number."""
    commits = [commit_of(piloted, name) for name in named]
    free(piloted, *commits)
    assert stamp(piloted, "use-case", "next", "--actor", "ACT-tester")[0] == next_use_case
    piloted.checkout("topic")
    piloted.commit("topic's own", {MINE_ONE: "# Mine\n", MINE_THREE: "# Mine too\n"})
    free(piloted, *commits)
    assert collisions(piloted) == colliding


# Slow by design: five stamps, each starting `pkit` processes.
def test_use_cases_and_journeys_restart_after_a_named_removal(piloted: AdopterRepo) -> None:
    """With both removals named, the next use case is UC-001 and the next journey
    JRN-001, and the stamp says why each is free; without the setting, the journey
    numbers past the pilot's, as it does today."""
    pilot = commit_of(piloted, f"{MAIN}~2")
    three_removed = commit_of(piloted, THREE_REMOVED)
    pilot_removed = commit_of(piloted, PILOT_REMOVED)
    # An abbreviated id names the commit as well as its full one.
    free(piloted, pilot_removed, three_removed[:7])
    completed = new(piloted, "use-case", "first", "--actor", "ACT-tester")
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines() == [
        freed_note("UC-003", UC_THREE, pilot, three_removed),
        f"stamped UC-001 at {USE_CASES}/UC-001-first.md",
    ]
    completed = new(piloted, "use-case", "second", "--actor", "ACT-tester")
    assert completed.stdout.splitlines() == [
        freed_note("UC-003", UC_THREE, pilot, three_removed),
        f"stamped UC-002 at {USE_CASES}/UC-002-second.md",
    ]
    steps = ("--step", "UC-001", "--step", "UC-002")
    journey, notes = stamp(piloted, "journey", "again", "--actor", "ACT-tester", *steps)
    assert (journey, notes) == ("JRN-001", [freed_note("JRN-001", JRN_TRIP, pilot, pilot_removed)])
    free(piloted)
    journey, notes = stamp(piloted, "journey", "again", "--actor", "ACT-tester", *steps)
    assert journey == "JRN-002"
    assert notes[0].startswith(
        f"JRN-002 follows JRN-001, the number main's history gave {JRN_TRIP}"
    )


# Slow by design: two stamps and two number checks, each starting `pkit` processes.
def test_a_file_a_named_commit_renamed_keeps_its_number(piloted: AdopterRepo) -> None:
    """A named commit that moved a use case out of the analysis renamed it, and removed
    nothing: the number its old name was given still counts, for the stamp and the
    number check alike."""
    removals = (commit_of(piloted, PILOT_REMOVED), commit_of(piloted, THREE_REMOVED))
    free(piloted, *removals)
    stamped(piloted, "use-case", "kept", "--actor", "ACT-tester")
    free(piloted)
    piloted.commit("UC-001 kept")
    moved = piloted.rename(f"{USE_CASES}/UC-001-kept.md", "tech-docs/archive/UC-001-kept.md")
    free(piloted, *removals, moved)
    assert stamp(piloted, "use-case", "next", "--actor", "ACT-tester")[0] == "UC-002"
    piloted.checkout("topic")
    piloted.commit("topic's own", {MINE_ONE: "# Mine\n"})
    free(piloted, *removals, moved)
    assert collisions(piloted) == [MINE_ONE]


# --- the setting is validated where it is read -----------------------------------------------


def _unknown(repo: AdopterRepo) -> tuple[str, str]:
    absent = "deadbeefdeadbeef"
    assert repo.git("rev-parse", f"--disambiguate={absent}").stdout == ""
    return absent, f"{absent} names no commit here: name a commit of the default branch's history"


def _ambiguous(repo: AdopterRepo) -> tuple[str, str]:
    """A prefix four digits long that two blobs' ids start with, and no commit's — so git
    settles on no object as the commit meant: two contents whose ids share one are
    found by hashing them as git does, then written."""
    listed = repo.git("cat-file", "--batch-all-objects", "--batch-check=%(objectname)").stdout
    prefix, blobs = _sharing_a_prefix(Counter(name[:4] for name in listed.split()))
    for blob in blobs:
        subprocess.run(
            ["git", "hash-object", "-w", "--stdin"], cwd=repo.root, input=blob, check=True
        )
    return prefix, f"{prefix} is ambiguous: 2 objects' ids start with it"


def _sharing_a_prefix(taken: Counter[str]) -> tuple[str, tuple[bytes, bytes]]:
    """Two blobs' contents whose ids, as git hashes them, start with the same four digits,
    and no object's of `taken`; with the prefix."""
    first: dict[str, bytes] = {}
    for n in itertools.count():
        content = f"blob {n}\n".encode()
        prefix = hashlib.sha1(b"blob %d\0" % len(content) + content).hexdigest()[:4]
        if taken[prefix]:
            continue
        if prefix in first:
            return prefix, (first[prefix], content)
        first[prefix] = content
    raise AssertionError("an endless count ended")


def _off_history(repo: AdopterRepo) -> tuple[str, str]:
    repo.checkout("topic")
    off = repo.commit("on topic alone", {"src/topic.py": "print('topic')\n"})
    repo.checkout(MAIN)
    return off, f"{off} is not on the history of the default branch, main"


def _not_a_commit_id(_repo: AdopterRepo) -> tuple[str, str]:
    return MAIN, "'main' does not match '^[0-9a-f]{4,64}$'"


# Slow by design: a stamp and a number check per case, each starting `pkit` processes.
@pytest.mark.parametrize(
    "case",
    [_unknown, _ambiguous, _off_history, _not_a_commit_id],
    ids=["unknown", "ambiguous", "off-the-default-branch", "not-a-commit-id"],
)
def test_a_setting_naming_no_commit_of_the_default_branch_fails(
    piloted: AdopterRepo, case: Callable[[AdopterRepo], tuple[str, str]]
) -> None:
    """The stamp refuses to number past a setting it cannot honour, and writes nothing;
    the number check fails on it — on main, which numbers nothing — at the entry."""
    entry, reason = case(piloted)
    free(piloted, entry)
    completed = new(piloted, "use-case", "next", "--actor", "ACT-tester")
    assert completed.returncode == 1
    where = f"{SETTING}:/numbering/freed-by/0"
    assert f"refused: the project's numbering setting, {where}: {reason}" in completed.stderr
    assert not list((piloted.root / USE_CASES).glob("UC-*.md"))
    checked = numbers(piloted)
    assert checked.returncode == 1, checked.stderr
    answer: dict[str, Any] = json.loads(checked.stdout)
    assert answer["base"] is None
    ((finding,),) = [answer["findings"]]
    assert (finding["severity"], finding["location"]) == ("error", where)
    assert finding["message"].startswith(reason)


def test_without_a_setting_or_a_number_the_number_check_reads_no_base(
    piloted: AdopterRepo,
) -> None:
    """A setting naming nothing is no setting: nothing numbered, nothing read."""
    piloted.write({SETTING: "schema_version: 1\nnumbering:\n  freed-by: []\n"})
    completed = run_script(piloted, NUMBERS, "--base", "origin/main", "--json")
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["summary"] == [
        "numbers: no use case or journey is numbered here; nothing to compare, no base read."
    ]
