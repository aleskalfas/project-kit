"""software-analysis: the numbering setting frees the ids an entry lists for its commit (#1342).

Held to software-analysis DEC-001 point 3: an artefact's id is never reused,
and the one exception is the project's to declare — artefacts a commit removed
from the default branch that nothing cites, whose ids are free again; nothing
else frees an id. The setting is `numbering.freed-by` in the capability's
settings file: each entry names a commit and lists the ids it frees. The stamp
(`pkit analysis new`) and the number check (`pkit analysis check-numbers`) read
it from one home, so they agree on every number:

- a listed id the default branch's history gave only files the entry's commit
  deleted, and by which the default branch lost them last, is free again — for
  use cases and journeys alike, whether the commit lies on the default branch's
  line or reached it by a merge;
- a listed id the commit does not free so is an error naming the id and why:
  one it deleted no file of, or renamed rather than deleted; one whose file a
  merge kept or brought back and another commit removed since; one whose path
  was added more than once before the commit; one the history gave another file
  too, under the name it had before a move;
- an id the commit would free that no entry lists stays taken, and is reported;
- an entry that is no commit's full id here, one off the default branch's
  history, one listing no id, a root commit, and a configuration that does not
  parse refuse the stamp and fail the number check, numbered there or not;
- a clone too shallow to hold the commit's parent, and a git too old to read
  where the default branch lost a path, are said as such;
- the number check lists the ids each entry frees.

Each test runs in a real repository: `main` holds a pilot — an actor, UC-001 to
UC-003 and JRN-001 — whose UC-003 one commit removed and whose other use cases
and journey the next did, and `topic` left `main` before the pilot.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import (
    JOURNEYS,
    MAIN,
    NEW,
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

#: The pilot and its two removals — UC-003's, then the rest of the pilot's — by the tags
#: `_piloted` names them with, which stay put as a test commits on main.
PILOT = "pilot"
THREE_REMOVED = "three-removed"
PILOT_REMOVED = "pilot-removed"

#: The ids each removal frees, by its tag.
FREES = {PILOT_REMOVED: ("UC-001", "UC-002", "JRN-001"), THREE_REMOVED: ("UC-003",)}

#: An entry of the setting: a commit and the ids it lists.
Entry = tuple[str, tuple[str, ...]]

#: How many characters of a commit a message shows.
SHORT = 12

#: Where the setting's first entry lies, as a finding locates it.
FIRST = f"{SETTING}:/numbering/freed-by/0"


# Slow: five stamps, built once per session; the first test to ask pays it in its setup.
def _piloted(repo: AdopterRepo) -> None:
    """`prepare`, `topic` leaving main there; then on main the pilot — the actor
    ACT-tester, UC-001 to UC-003 and JRN-001 through UC-001 and UC-002 — then UC-003
    removed, then UC-001, UC-002 and JRN-001; the actor is kept. The three commits are
    tagged."""
    prepare(repo)
    repo.checkout("topic", create=True)
    repo.checkout(MAIN)
    stamped(repo, "actor", "tester")
    for slug in ("one", "two", "three"):
        stamped(repo, "use-case", slug, "--actor", "ACT-tester")
    steps = ("--step", "UC-001", "--step", "UC-002")
    stamped(repo, "journey", "trip", "--actor", "ACT-tester", *steps)
    repo.git("tag", PILOT, repo.commit("the pilot"))
    repo.git("tag", THREE_REMOVED, repo.commit("UC-003 removed", {UC_THREE: None}))
    removed = repo.commit("the pilot removed", {UC_ONE: None, UC_TWO: None, JRN_TRIP: None})
    repo.git("tag", PILOT_REMOVED, removed)


@pytest.fixture
def piloted(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    """The project with the pilot added and removed on main (`_piloted`)."""
    return installed(make_adopter_repo, monkeypatch, then=_piloted)


def commit_of(repo: AdopterRepo, name: str) -> str:
    return repo.git("rev-parse", name).stdout.strip()


def removals(repo: AdopterRepo) -> tuple[str, str]:
    """The pilot's two removals, by their full ids: the rest of the pilot's, then UC-003's."""
    return commit_of(repo, PILOT_REMOVED), commit_of(repo, THREE_REMOVED)


def entry(repo: AdopterRepo, tag: str) -> Entry:
    """The entry freeing every id the removal `tag` names removed."""
    return commit_of(repo, tag), FREES[tag]


def pilot_freed(repo: AdopterRepo) -> tuple[Entry, Entry]:
    """The entries freeing the whole pilot: the rest of the pilot's removal, then UC-003's."""
    return entry(repo, PILOT_REMOVED), entry(repo, THREE_REMOVED)


def free(repo: AdopterRepo, *entries: Entry) -> None:
    """The setting of `entries`, written in the working tree; none, no setting."""
    if not entries:
        repo.write({SETTING: None})
        return
    written = "".join(
        f'    - commit: "{commit}"\n      ids: [{", ".join(ids)}]\n' for commit, ids in entries
    )
    repo.write({SETTING: f"schema_version: 1\nnumbering:\n  freed-by:\n{written}"})


def where(index: int, *pointer: str | int) -> str:
    """The location of the setting's entry `index`, and of `pointer` inside it."""
    return "/".join([f"{SETTING}:/numbering/freed-by/{index}", *map(str, pointer)])


def stamp(repo: AdopterRepo, *args: str) -> tuple[str, list[str]]:
    """A stamp's id and its notes, the file it wrote removed again."""
    completed = new(repo, *args)
    assert completed.returncode == 0, completed.stderr
    *notes, done = completed.stdout.strip().splitlines()
    _stamped, new_id, _at, location = done.split()
    repo.write({location: None})
    return new_id, notes


def next_use_case(repo: AdopterRepo) -> tuple[str, list[str]]:
    return stamp(repo, "use-case", "next", "--actor", "ACT-tester")


def numbers(repo: AdopterRepo) -> subprocess.CompletedProcess[str]:
    """`pkit analysis check-numbers --json` against main, as the dispatcher runs it."""
    return run_script(repo, NUMBERS, "--base", MAIN, "--json")


def checked(repo: AdopterRepo) -> dict[str, Any]:
    """The number check's document; it fails exactly when it reports an error."""
    completed = numbers(repo)
    answer: dict[str, Any] = json.loads(completed.stdout)
    errors = [f for f in answer["findings"] if f["severity"] == "error"]
    assert completed.returncode == (1 if errors else 0), completed.stderr
    return answer


def collisions(answer: dict[str, Any]) -> list[str]:
    """The files the number check finds a number of colliding."""
    return sorted(
        f["location"]
        for f in answer["findings"]
        if f["severity"] == "error" and not f["location"].startswith(SETTING)
    )


def freed_ids(answer: dict[str, Any]) -> list[str]:
    """The numbers the number check lists as freed, in its order."""
    return [freed["id"] for freed in answer["freed"]]


def freed_note(new_id: str, path: str, added: str, removed: str, on: str = MAIN) -> str:
    return (
        f"{new_id} is free again, freed by {removed[:SHORT]}, as the project's numbering "
        f"setting names: {on}'s history gave it {path} (commit {added[:SHORT]}), which "
        f"{removed[:SHORT]} removed (DEC-001 point 3)"
    )


def follows_note(new_id: str, past: str, path: str, added: str) -> str:
    return (
        f"{new_id} follows {past}, the number {MAIN}'s history gave {path} (commit "
        f"{added[:SHORT]}), which neither {MAIN} nor the working tree holds now: a number is "
        f"never used again (DEC-001 point 3)"
    )


def not_freed(listed: str, commit: str, reason: str) -> str:
    return (
        f"{listed} is not freed by {commit[:SHORT]}: {reason} — remove it from the entry, or "
        f"list it under the commit that frees it (DEC-001 point 3)"
    )


def setting_error(answer: dict[str, Any]) -> tuple[str, str]:
    """The number check's one finding on the setting, an error: its location and its
    message."""
    ((finding,),) = [[f for f in answer["findings"] if f["location"].startswith(SETTING)]]
    assert finding["severity"] == "error"
    return finding["location"], finding["message"]


# --- what it frees, and what it does not (DEC-001 point 3) -------------------------------------


MINE_ONE = f"{USE_CASES}/UC-001-mine.md"
MINE_TWO = f"{USE_CASES}/UC-002-mine.md"
MINE_THREE = f"{USE_CASES}/UC-003-mine.md"


# Slow by design: four stamps and four number checks, each starting `pkit` processes.
@pytest.mark.parametrize(
    ("named", "next_id", "colliding", "freed"),
    [
        ((), "UC-004", [MINE_ONE, MINE_THREE], []),
        (
            (PILOT_REMOVED, THREE_REMOVED),
            "UC-001",
            [],
            ["JRN-001", "UC-001", "UC-002", "UC-003"],
        ),
        ((PILOT_REMOVED,), "UC-004", [MINE_THREE], ["JRN-001", "UC-001", "UC-002"]),
        ((THREE_REMOVED,), "UC-003", [MINE_ONE], ["UC-003"]),
    ],
    ids=["no-setting", "both-removals", "the-pilot-s-removal", "uc-003-s-removal"],
)
def test_the_stamp_and_the_number_check_free_only_what_a_named_commit_removed(
    piloted: AdopterRepo,
    named: tuple[str, ...],
    next_id: str,
    colliding: list[str],
    freed: list[str],
) -> None:
    """The stamp on main numbers past what the history counts, and the number check on
    `topic` — holding UC-001 and UC-003 of its own, numbered before main's pilot — fails
    on exactly the numbers the stamp counts, and lists those it does not: an id an entry
    lists, whose file its commit removed on the default branch's own line, is free; a
    file another commit removed still holds its number."""
    entries = [entry(piloted, tag) for tag in named]
    free(piloted, *entries)
    assert next_use_case(piloted)[0] == next_id
    piloted.checkout("topic")
    piloted.commit("topic's own", {MINE_ONE: "# Mine\n", MINE_THREE: "# Mine too\n"})
    free(piloted, *entries)
    answer = checked(piloted)
    assert collisions(answer) == colliding
    assert freed_ids(answer) == freed


# Slow by design: four stamps and a number check, each starting `pkit` processes.
def test_use_cases_and_journeys_restart_after_a_named_removal(piloted: AdopterRepo) -> None:
    """With both removals named, the next use case is UC-001 and the next journey
    JRN-001, and the stamp says why each is free; the number check lists, commit by
    commit, every number the setting frees. Without the setting, the journey numbers past
    the pilot's, as it does today."""
    pilot = commit_of(piloted, PILOT)
    pilot_removed, three_removed = removals(piloted)
    free(piloted, *pilot_freed(piloted))
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
    tip = commit_of(piloted, MAIN)
    human = run_script(piloted, NUMBERS, "--base", MAIN)
    assert human.returncode == 0, human.stderr
    assert human.stdout.splitlines() == [
        f"numbers: this branch contains {MAIN} ({tip[:SHORT]}); nothing to collide with.",
        f"numbering: {pilot_removed[:SHORT]} frees JRN-001, UC-001 and UC-002, as the "
        f"project's numbering setting names (DEC-001 point 3).",
        f"numbering: {three_removed[:SHORT]} frees UC-003, as the project's numbering setting "
        f"names (DEC-001 point 3).",
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


# Slow by design: two stamps and a number check, each starting `pkit` processes.
def test_a_file_a_named_commit_renamed_keeps_its_number(piloted: AdopterRepo) -> None:
    """A named commit that moved one use case out of the analysis and deleted another
    renamed the first, and removed the second: the number the first's old name was
    given still counts, for the stamp and the number check alike, and the second's is
    free. Listing the first is an error: the commit deleted no file of it."""
    free(piloted, *pilot_freed(piloted))
    stamped(piloted, "use-case", "kept", "--actor", "ACT-tester")
    stamped(piloted, "use-case", "gone", "--actor", "ACT-tester")
    free(piloted)
    piloted.commit("UC-001 and UC-002")
    kept, gone = f"{USE_CASES}/UC-001-kept.md", f"{USE_CASES}/UC-002-gone.md"
    (piloted.root / "tech-docs/archive").mkdir(parents=True)
    piloted.git("mv", kept, "tech-docs/archive/UC-001-kept.md")
    piloted.git("rm", "-q", gone)
    piloted.git("commit", "-q", "-m", "UC-001 moved out, UC-002 removed")
    moved = commit_of(piloted, MAIN)
    added = commit_of(piloted, f"{MAIN}~1")
    free(piloted, *pilot_freed(piloted), (moved, ("UC-002",)))
    # The note names the highest number freed past the one followed: the pilot's UC-003.
    pilot, three_removed = commit_of(piloted, PILOT), commit_of(piloted, THREE_REMOVED)
    assert next_use_case(piloted) == (
        "UC-002",
        [
            follows_note("UC-002", "UC-001", kept, added),
            freed_note("UC-003", UC_THREE, pilot, three_removed),
        ],
    )
    piloted.checkout("topic")
    piloted.commit("topic's own", {MINE_ONE: "# Mine\n", MINE_TWO: "# Mine too\n"})
    free(piloted, *pilot_freed(piloted), (moved, ("UC-002",)))
    answer = checked(piloted)
    assert collisions(answer) == [MINE_ONE]
    assert [f["id"] for f in answer["freed"] if f["freed_by"] == moved] == ["UC-002"]
    free(piloted, *pilot_freed(piloted), (moved, ("UC-001", "UC-002")))
    assert setting_error(checked(piloted)) == (
        where(2, "ids", 0),
        not_freed(
            "UC-001",
            moved,
            "it deleted no use case or journey numbered UC-001; a file it moved, rather than "
            "deleted, keeps its id",
        ),
    )


MOVED = f"{USE_CASES}/UC-004-moved.md"
MOVED_INTO_AN_AREA = f"{USE_CASES}/area/UC-004-moved.md"
GONE = f"{USE_CASES}/UC-005-gone.md"


# Slow by design: a stamp and a number check, each starting `pkit` processes.
def test_only_a_files_last_name_is_freed(piloted: AdopterRepo) -> None:
    """A use case moved into an area, then removed by a named commit: its number still
    counts — a number is free only when every file the history gave it is freed, and the
    name it had before the move is not — while a use case the same commit removed, never
    moved, is free."""
    added = piloted.commit("two use cases", {MOVED: "# Moved\n", GONE: "# Gone\n"})
    moved = piloted.rename(MOVED, MOVED_INTO_AN_AREA)
    removed = piloted.commit("both removed", {MOVED_INTO_AN_AREA: None, GONE: None})
    free(piloted, *pilot_freed(piloted), (removed, ("UC-005",)))
    assert next_use_case(piloted) == (
        "UC-005",
        [
            follows_note("UC-005", "UC-004", MOVED_INTO_AN_AREA, moved),
            freed_note("UC-005", GONE, added, removed),
        ],
    )
    answer = checked(piloted)
    assert [f["id"] for f in answer["freed"] if f["freed_by"] == removed] == ["UC-005"]
    free(piloted, *pilot_freed(piloted), (removed, ("UC-004", "UC-005")))
    assert setting_error(checked(piloted)) == (
        where(2, "ids", 0),
        not_freed(
            "UC-004",
            removed,
            f"the history before it gave UC-004 to {MOVED} too (commit {added[:SHORT]}), which "
            f"the setting does not free",
        ),
    )


KEPT = f"{USE_CASES}/UC-004-kept.md"


def _kept_by_a_merge(repo: AdopterRepo, *, on_side: bool) -> tuple[str, str]:
    """On main, UC-004-kept and UC-005-gone added; then both removed by one commit — on a
    side branch, or on main itself; then the side branch merged into main, the merge
    keeping UC-004-kept, or bringing it back; then UC-004-kept removed on main by a
    commit of its own. Returns the commit that added both, and the one that removed
    both."""
    added = repo.commit("two use cases", {KEPT: "# Kept\n", GONE: "# Gone\n"})
    repo.checkout("side", create=True)
    if on_side:
        removed = repo.commit("both removed", {KEPT: None, GONE: None})
        repo.checkout(MAIN)
    else:
        repo.commit("other work", {"src/side.py": "print('side')\n"})
        repo.checkout(MAIN)
        removed = repo.commit("both removed", {KEPT: None, GONE: None})
    repo.git("merge", "-q", "--no-ff", "--no-commit", "side")
    repo.git("checkout", added, "--", KEPT)
    repo.git("commit", "-q", "-m", "side merged, UC-004 kept")
    repo.commit("UC-004 removed", {KEPT: None})
    return added, removed


# Slow by design: a stamp and a number check per case, each starting `pkit` processes.
@pytest.mark.parametrize("on_side", [True, False], ids=["kept-by-the-merge", "brought-back"])
def test_a_file_a_merge_kept_and_another_commit_removed_holds_its_number(
    piloted: AdopterRepo, on_side: bool
) -> None:
    """The default branch lost UC-004-kept last by a commit the setting does not name —
    a merge kept the file the named commit removed, or brought it back after it — so its
    number still counts, and listing it is an error; UC-005-gone, which the default
    branch lost by the named commit, or by the merge that brought it onto the default
    branch's line, is free."""
    added, removed = _kept_by_a_merge(piloted, on_side=on_side)
    last = commit_of(piloted, MAIN)
    free(piloted, *pilot_freed(piloted), (removed, ("UC-005",)))
    assert next_use_case(piloted) == (
        "UC-005",
        [
            follows_note("UC-005", "UC-004", KEPT, added),
            freed_note("UC-005", GONE, added, removed),
        ],
    )
    answer = checked(piloted)
    assert [f["id"] for f in answer["freed"] if f["freed_by"] == removed] == ["UC-005"]
    free(piloted, *pilot_freed(piloted), (removed, ("UC-004", "UC-005")))
    reason = f"the default branch lost {KEPT} last by {last[:SHORT]}, not by it"
    assert setting_error(checked(piloted)) == (
        where(2, "ids", 0),
        not_freed("UC-004", removed, reason),
    )


TWICE = f"{USE_CASES}/UC-004-twice.md"


# Slow by design: a stamp and a number check, each starting `pkit` processes.
def test_a_path_added_more_than_once_before_the_named_commit_frees_none(
    piloted: AdopterRepo,
) -> None:
    """Which of two files added under one path a named commit removed cannot be told, so
    its id is not freed: listing it is an error, and both tools say why; the other file
    it removed is free."""
    first = piloted.commit("UC-004", {TWICE: "# Twice\n"})
    piloted.commit("UC-004 removed", {TWICE: None})
    again = piloted.commit("UC-004 again, and UC-005", {TWICE: "# Twice again\n", GONE: "# Gone\n"})
    removed = piloted.commit("both removed", {TWICE: None, GONE: None})
    free(piloted, (removed, ("UC-004", "UC-005")), *pilot_freed(piloted))
    reason = not_freed(
        "UC-004",
        removed,
        f"{TWICE} was added 2 times before it ({again[:SHORT]}, {first[:SHORT]}), and which "
        f"of those files it removed cannot be told",
    )
    completed = new(piloted, "use-case", "next", "--actor", "ACT-tester")
    assert completed.returncode == 1
    assert f"refused: the project's numbering setting, {where(0, 'ids', 0)}: {reason}" in (
        completed.stderr
    )
    assert setting_error(checked(piloted)) == (where(0, "ids", 0), reason)
    free(piloted, (removed, ("UC-005",)), *pilot_freed(piloted))
    assert next_use_case(piloted) == (
        "UC-005",
        [
            follows_note("UC-005", "UC-004", TWICE, again),
            freed_note("UC-005", GONE, again, removed),
        ],
    )
    answer = checked(piloted)
    assert answer["findings"] == []
    assert [f["id"] for f in answer["freed"] if f["freed_by"] == removed] == ["UC-005"]


# Slow by design: a stamp and a number check, each starting `pkit` processes.
def test_an_id_a_named_commit_frees_that_no_entry_lists_stays_taken(piloted: AdopterRepo) -> None:
    """Only a listed id is freed: UC-002, which the pilot's removal would free but its entry
    does not list, still counts — the stamp numbers past it — and both tools report it."""
    pilot = commit_of(piloted, PILOT)
    pilot_removed, three_removed = removals(piloted)
    free(piloted, (pilot_removed, ("UC-001", "JRN-001")), entry(piloted, THREE_REMOVED))
    report = (
        f"{pilot_removed[:SHORT]} also removed UC-002, which no entry lists for it: it stays "
        f"taken (DEC-001 point 3)"
    )
    assert next_use_case(piloted) == (
        "UC-003",
        [
            f"the project's numbering setting, {FIRST}: {report}",
            follows_note("UC-003", "UC-002", UC_TWO, pilot),
            freed_note("UC-003", UC_THREE, pilot, three_removed),
        ],
    )
    answer = checked(piloted)
    assert answer["findings"] == [{"severity": "report", "location": FIRST, "message": report}]
    assert freed_ids(answer) == ["JRN-001", "UC-001", "UC-003"]
    assert answer["summary"][1:] == [
        f"numbering: {pilot_removed[:SHORT]} frees JRN-001 and UC-001, as the project's "
        f"numbering setting names (DEC-001 point 3).",
        f"numbering: {three_removed[:SHORT]} frees UC-003, as the project's numbering setting "
        f"names (DEC-001 point 3).",
    ]


# Slow by design: a stamp, each starting `pkit` processes.
def test_a_stamp_given_a_base_numbers_past_it_and_frees_alike(piloted: AdopterRepo) -> None:
    """A base named on the command line holds UC-002 of its own: the stamp numbers past it,
    and the pilot's UC-003, which the base's history gave the same file main's did, is as
    free there as on main."""
    pilot, three_removed = commit_of(piloted, PILOT), commit_of(piloted, THREE_REMOVED)
    piloted.checkout("next", create=True)
    piloted.commit("UC-002 on next", {f"{USE_CASES}/UC-002-next.md": "# Next\n"})
    piloted.checkout(MAIN)
    free(piloted, *pilot_freed(piloted))
    completed = run_script(
        piloted, NEW, "use-case", "beyond", "--actor", "ACT-tester", "--base", "next"
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines() == [
        freed_note("UC-003", UC_THREE, pilot, three_removed, on=f"{MAIN} and next"),
        f"stamped UC-003 at {USE_CASES}/UC-003-beyond.md",
    ]


# --- the setting is validated where it is read -----------------------------------------------


def _unknown(_repo: AdopterRepo) -> tuple[Entry, str, str]:
    absent = "deadbeef" * 5
    return (
        (absent, ("UC-001",)),
        FIRST,
        f"{absent} is no commit's id here: name a commit of the default branch's history by "
        f"its full id",
    )


def _abbreviated(repo: AdopterRepo) -> tuple[Entry, str, str]:
    short = commit_of(repo, PILOT_REMOVED)[:SHORT]
    return (
        (short, ("UC-001",)),
        where(0, "commit"),
        f"'{short}' does not match '^([0-9a-f]{{40}}|[0-9a-f]{{64}})$'",
    )


def _off_history(repo: AdopterRepo) -> tuple[Entry, str, str]:
    repo.checkout("topic")
    off = repo.commit("on topic alone", {"src/topic.py": "print('topic')\n"})
    repo.checkout(MAIN)
    return (off, ("UC-001",)), FIRST, f"{off} is not on the history of the default branch, main"


def _not_a_commit_id(_repo: AdopterRepo) -> tuple[Entry, str, str]:
    return (
        (MAIN, ("UC-001",)),
        where(0, "commit"),
        "'main' does not match '^([0-9a-f]{40}|[0-9a-f]{64})$'",
    )


def _no_ids(repo: AdopterRepo) -> tuple[Entry, str, str]:
    # The words are jsonschema's, which differ between its versions; the value opens them.
    return (commit_of(repo, PILOT_REMOVED), ()), where(0, "ids"), "[]"


def _a_root_commit(repo: AdopterRepo) -> tuple[Entry, str, str]:
    (root,) = repo.git("rev-list", "--max-parents=0", MAIN).stdout.split()
    return (
        (root, ("UC-001",)),
        FIRST,
        f"{root} is the history's first commit: it removed nothing — name the commit by which "
        f"the default branch lost the artefacts, or remove the entry (DEC-001 point 3)",
    )


def _an_id_the_commit_deleted_no_file_of(repo: AdopterRepo) -> tuple[Entry, str, str]:
    three_removed = commit_of(repo, THREE_REMOVED)
    reason = "it deleted no use case or journey numbered UC-001; a file it moved, rather than "
    return (
        (three_removed, ("UC-003", "UC-001")),
        where(0, "ids", 1),
        not_freed("UC-001", three_removed, f"{reason}deleted, keeps its id"),
    )


def _a_merge_bringing_the_default_branch_in(repo: AdopterRepo) -> tuple[Entry, str, str]:
    """A branch that left main at the pilot merges main in — the merge deletes the
    pilot's files against its first parent — then lands on main by a merge. The default
    branch lost those files by its own two removals, not by that merge."""
    pilot_removed = commit_of(repo, PILOT_REMOVED)
    repo.git("checkout", "-q", "-b", "feature", PILOT)
    repo.commit("feature work", {"src/feature.py": "print('feature')\n"})
    back = repo.merge(MAIN)
    repo.checkout(MAIN)
    repo.merge("feature")
    reason = f"the default branch lost {UC_ONE} last by {pilot_removed[:SHORT]}, not by it"
    return (back, ("UC-001",)), where(0, "ids", 0), not_freed("UC-001", back, reason)


# Slow by design: a stamp and a number check per case, each starting `pkit` processes.
@pytest.mark.parametrize(
    "case",
    [
        _unknown,
        _abbreviated,
        _off_history,
        _not_a_commit_id,
        _no_ids,
        _a_root_commit,
        _an_id_the_commit_deleted_no_file_of,
        _a_merge_bringing_the_default_branch_in,
    ],
    ids=[
        "unknown",
        "abbreviated",
        "off-the-default-branch",
        "not-a-commit-id",
        "no-ids",
        "a-root-commit",
        "an-id-the-commit-deleted-no-file-of",
        "a-merge-bringing-the-default-branch-in",
    ],
)
def test_an_entry_the_tools_cannot_honour_fails(
    piloted: AdopterRepo, case: Callable[[AdopterRepo], tuple[Entry, str, str]]
) -> None:
    """The stamp refuses to number past an entry it cannot honour, and writes nothing;
    the number check fails on it — on main, which numbers nothing — at the entry, or at
    the id it lists that its commit does not free, which it frees not."""
    written, location, reason = case(piloted)
    free(piloted, written)
    completed = new(piloted, "use-case", "next", "--actor", "ACT-tester")
    assert completed.returncode == 1
    assert f"refused: the project's numbering setting, {location}: {reason}" in completed.stderr
    assert not list((piloted.root / USE_CASES).glob("UC-*.md"))
    answer = checked(piloted)
    assert answer["base"] is None
    # The one entry that lists an id its commit frees as well, UC-003, frees it alone.
    assert freed_ids(answer) == [listed for listed in written[1] if listed == "UC-003"]
    ((finding,),) = [answer["findings"]]
    assert (finding["severity"], finding["location"]) == ("error", location)
    assert finding["message"].startswith(reason)


OLD_GIT = """#!/bin/sh
for arg in "$@"; do
  case "$arg" in
    --diff-merges*) echo "fatal: unrecognized argument: $arg" >&2; exit 128 ;;
  esac
done
exec "{git}" "$@"
"""


# Slow by design: a stamp and a number check, each starting `pkit` processes.
def test_a_git_too_old_to_read_where_a_path_was_lost_names_the_floor(
    piloted: AdopterRepo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A git that knows no `--diff-merges` cannot say where the default branch lost a file:
    the stamp refuses and the number check fails, naming the git it needs rather than
    blaming the entry."""
    pilot_removed = commit_of(piloted, PILOT_REMOVED)
    free(piloted, entry(piloted, PILOT_REMOVED))
    git = shutil.which("git")
    assert git is not None
    old = tmp_path / "old-git"
    old.mkdir()
    (old / "git").write_text(OLD_GIT.format(git=git), encoding="utf-8")
    (old / "git").chmod(0o755)
    monkeypatch.setenv("PATH", f"{old}{os.pathsep}{os.environ['PATH']}")
    reason = (
        f"git could not read where the default branch lost the files {pilot_removed[:SHORT]} "
        f"removed — that needs git 2.31 or later: fatal: unrecognized argument: "
        f"--diff-merges=first-parent"
    )
    completed = new(piloted, "use-case", "next", "--actor", "ACT-tester")
    assert completed.returncode == 1
    assert f"refused: the project's numbering setting, {FIRST}: {reason}" in completed.stderr
    assert setting_error(checked(piloted)) == (FIRST, reason)


# Slow by design: a stamp and a number check, each starting `pkit` processes.
def test_a_clone_too_shallow_to_hold_the_commits_parent_says_so(
    piloted: AdopterRepo, tmp_path: Path
) -> None:
    """In a clone that stops at the named commit, what it removed cannot be read: the
    stamp refuses and the number check fails, saying the clone is shallow and how to
    deepen it, rather than blaming the entry."""
    pilot_removed = commit_of(piloted, PILOT_REMOVED)
    shallow = tmp_path / "shallow"
    piloted.git("clone", "-q", "--depth", "1", f"file://{piloted.root}", str(shallow))
    clone = AdopterRepo(shallow, source_kit=piloted.source_kit)
    free(clone, entry(piloted, PILOT_REMOVED))
    reason = (
        f"this clone is shallow and does not hold the parent of {pilot_removed[:SHORT]}, so "
        f"what it removed cannot be read: `git fetch --unshallow` reads the whole history"
    )
    completed = new(clone, "use-case", "next", "--actor", "ACT-tester")
    assert completed.returncode == 1
    assert f"refused: the project's numbering setting, {FIRST}: {reason}" in completed.stderr
    assert setting_error(checked(clone)) == (FIRST, reason)


# Slow by design: a stamp and a number check, each starting `pkit` processes.
def test_a_configuration_that_does_not_parse_fails(piloted: AdopterRepo) -> None:
    """The stamp refuses, saying where the file does not parse; the number check fails on
    it, numbering nothing."""
    piloted.write({SETTING: "numbering:\n  freed-by: [unclosed\n"})
    completed = new(piloted, "use-case", "next", "--actor", "ACT-tester")
    assert completed.returncode == 1
    reason = "it does not parse as YAML, line 3: expected ',' or ']'"
    assert f"refused: the project's numbering setting, {SETTING}: {reason}" in completed.stderr
    answer = checked(piloted)
    ((finding,),) = [answer["findings"]]
    assert (finding["severity"], finding["location"]) == ("error", SETTING)
    assert finding["message"].startswith(reason)


# Slow by design: a number check, starting `pkit` processes.
def test_the_number_check_compares_and_fails_on_a_setting_problem(piloted: AdopterRepo) -> None:
    """On a branch that numbers, a bad entry fails the check beside the comparison, which
    the valid entries still free numbers for: UC-001, freed by the pilot's removal, is no
    collision; UC-003, which no named commit frees, is."""
    absent = "deadbeef" * 5
    piloted.checkout("topic")
    piloted.commit("topic's own", {MINE_ONE: "# Mine\n", MINE_THREE: "# Mine too\n"})
    free(piloted, entry(piloted, PILOT_REMOVED), (absent, ("UC-003",)))
    answer = checked(piloted)
    assert answer["base"]["outdated"] is True
    assert sorted((f["severity"], f["location"]) for f in answer["findings"]) == [
        ("error", where(1)),
        ("error", MINE_THREE),
        ("report", "tech-docs/analysis"),
    ]
    assert freed_ids(answer) == ["JRN-001", "UC-001", "UC-002"]


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
