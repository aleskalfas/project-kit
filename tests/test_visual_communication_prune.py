"""`pkit visual prune` (visual-communication DEC-019 points 9 to 11): each rule of what lies
behind and what is spared, with why; a final piece's lock, a published piece's writer's lock, a
piece with no lock yet, a kept export; each stop, removing nothing; the list, a dry run, the
question, consent up front and a run with no terminal; a failed removal put back or named; the
working tree alone; and the check after a run. The rules are judged on locks and libraries
written from their fields, and the runs on the drawing project, in this process."""

from __future__ import annotations

import errno
import os
import subprocess
from collections.abc import Collection, Iterator, Mapping
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load, run_main
from tests.test_visual_communication_pipeline import (
    LOCK,
    PIECE,
    PIECE_FOLDER,
    changed_tests,
    drawing_project,
    every_file,
    list_drawing_libraries,
)
from tests.visual_communication_project import (
    CONFIG,
    RECORDED_DEFAULT,
    add_library,
    bound,
    importable,
    project,
    write,
    write_list,
    write_piece,
    yaml_text,
)
from tests.visual_communication_writes import FULL, failing

script, export_script, render_script, check_script, svg, pruning, reading = load(
    "visual-communication",
    "prune.py",
    "export.py",
    "render.py",
    "check.py",
    "plugins.svg",
    "pruning",
    "reading",
)

LIST = "visual/libraries/libraries.yaml"
RECORD = f"{PIECE_FOLDER}/exports.yaml"
PIECE_FILE = f"{PIECE_FOLDER}/piece.yaml"
TESTS = "visual/libraries/tests"
#: A source of another repository, which the list names with its place.
ELSEWHERE = {"kind": "repository", "url": "https://example.org/parts.git", "ref": "main"}
SHA = "0" * 64


@pytest.fixture(autouse=True)
def plugins(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The renderer stands in for the import a run makes when it draws, for the length of the
    test."""
    importable(monkeypatch, svg)
    yield


# --- the rules, on locks and libraries written from their fields --------------------------------


def hold(
    root: Path,
    versions: Mapping[str, Collection[str]],
    *,
    unreleased: Collection[str] = (),
    sources: Mapping[str, str] | None = None,
    builds_on: Mapping[str, Mapping[str, int]] | None = None,
    needs: Mapping[str, str] | None = None,
) -> None:
    """Each version of each library written from its fields, and listed: released but those
    `unreleased` names, by label, from another repository unless `sources` names its kind.
    `builds_on` and `needs` give a version's `builds-on` and the release it needs, by label."""
    sources, builds_on, needs = sources or {}, builds_on or {}, needs or {}
    listed: dict[str, Any] = {}
    for name, numbers in versions.items():
        kind = sources.get(name, "repository")
        source = ELSEWHERE if kind == "repository" else {"kind": kind}
        entries = {}
        for number in numbers:
            label = f"{name}@{number}"
            add_library(
                root,
                name,
                number,
                builds_on=builds_on.get(label),
                needs_release=needs.get(label, "0.1.0"),
            )
            entries[number] = {"released": label not in unreleased}
        listed[name] = {"source": source, "versions": entries}
    write_list(root, listed)


def piece(root: Path, name: str, lock: Mapping[str, str] | None, **fields: Any) -> None:
    """A piece's own file alone, a draft unless `fields` say otherwise, with `lock` where one is
    given."""
    if lock is not None:
        fields["lock"] = dict(lock)
    write_piece(root, name, **fields)


def judged(root: Path) -> tuple[list[str], dict[str, str]]:
    """What a run would remove, by label, and what it spares, with why."""
    planned = pruning.plan(root, "visual")
    return [each.label for each in planned.removed], {
        each.label: each.why for each in planned.spared
    }


def test_a_version_no_lock_can_reach_goes_and_a_lock_keeps_what_it_names(tmp_path: Path) -> None:
    root = project(tmp_path)
    hold(root, {"a": ["1.0.0", "1.1.0", "1.2.0"]})
    piece(root, "p", {"a": "1.2.0"})
    removed, spared = judged(root)
    assert removed == ["a@1.1.0", "a@1.0.0"]
    assert spared == {"a@1.2.0": "the draft `p` locks it"}


@pytest.mark.parametrize(
    ("fields", "called"),
    [
        pytest.param({}, "the draft `p`", id="draft"),
        pytest.param({"pinned": True}, "the pinned draft `p`", id="pinned"),
        pytest.param({"state": "published"}, "the published piece `p`", id="published"),
    ],
)
def test_a_lock_that_moves_spares_each_version_above_it_in_its_major(
    tmp_path: Path, fields: dict[str, Any], called: str
) -> None:
    root = project(tmp_path)
    hold(root, {"a": ["1.0.0", "1.1.0", "1.2.0", "2.0.0"]})
    piece(root, "p", {"a": "1.0.0"}, **fields)
    removed, spared = judged(root)
    assert removed == []
    assert spared == {
        "a@2.0.0": "it is the last version of `a`: nothing newer stands",
        "a@1.2.0": f"{called} locks a@1.0.0, below it in its major, and may still move to it",
        "a@1.1.0": f"{called} locks a@1.0.0, below it in its major, and may still move to it",
        "a@1.0.0": f"{called} locks it",
    }


def test_a_final_pieces_lock_keeps_what_it_names_and_no_more(tmp_path: Path) -> None:
    root = project(tmp_path)
    hold(root, {"a": ["1.0.0", "1.1.0", "1.2.0"]})
    piece(root, "p", {"a": "1.0.0"}, state="final")
    removed, spared = judged(root)
    assert removed == ["a@1.1.0"]
    assert spared == {
        "a@1.2.0": "it is the last version of `a`: nothing newer stands",
        "a@1.0.0": "the final piece `p` locks it",
    }


def test_a_declarations_lock_of_written_code_keeps_what_it_names_and_moves(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    hold(root, {"a": ["1.0.0", "1.1.0", "1.2.0"]})
    declaration = bound("code", writer="json", brand="a", lock={"a": "1.0.0"}, out="out.json")
    write(root / "visual/code/web.yaml", yaml_text(declaration))
    removed, spared = judged(root)
    assert removed == []
    assert spared["a@1.0.0"] == "the declaration `web` of written code locks it"
    assert spared["a@1.1.0"] == (
        "the declaration `web` of written code locks a@1.0.0, below it in its major, and may "
        "still move to it"
    )


def test_a_piece_with_no_lock_yet_is_served_by_the_newest_of_each_major(tmp_path: Path) -> None:
    root = project(tmp_path)
    hold(root, {"a": ["1.0.0", "1.1.0", "2.0.0", "2.1.0"]})
    piece(root, "p", None)
    removed, spared = judged(root)
    assert removed == ["a@2.0.0", "a@1.0.0"]
    assert spared == {
        "a@2.1.0": "it is the last version of `a`: nothing newer stands",
        "a@1.1.0": (
            "it is the newest version of `a` 1 that the installed capability reads, which a "
            "first lock takes"
        ),
    }


def test_in_a_major_no_lock_that_moves_names_only_the_newest_stays(tmp_path: Path) -> None:
    root = project(tmp_path)
    hold(root, {"a": ["1.0.0", "1.1.0", "1.2.0", "2.0.0"]})
    piece(root, "p", {"a": "2.0.0"})
    removed, spared = judged(root)
    assert removed == ["a@1.1.0", "a@1.0.0"]
    assert set(spared) == {"a@2.0.0", "a@1.2.0"}


def test_a_projects_own_version_not_yet_released_is_spared(tmp_path: Path) -> None:
    root = project(tmp_path)
    hold(root, {"a": ["1.0.0", "1.1.0"]}, unreleased={"a@1.0.0"}, sources={"a": "project"})
    piece(root, "p", {"a": "1.1.0"})
    removed, spared = judged(root)
    assert removed == []
    assert spared["a@1.0.0"] == (
        "it is the project's own, not yet released, and holds work that lies nowhere else"
    )


@pytest.mark.parametrize("source", ["shipped", "repository"])
def test_a_copy_not_yet_released_of_another_source_goes_where_it_lies_behind(
    tmp_path: Path, source: str
) -> None:
    root = project(tmp_path)
    hold(root, {"a": ["1.0.0", "1.1.0"]}, unreleased={"a@1.0.0", "a@1.1.0"}, sources={"a": source})
    piece(root, "p", {"a": "1.1.0"})
    assert judged(root)[0] == ["a@1.0.0"]


def test_the_newest_release_of_each_major_stays_for_a_release_to_be_compared_with(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    hold(root, {"a": ["1.0.0", "1.1.0", "1.2.0"]}, unreleased={"a@1.2.0"})
    piece(root, "p", {"a": "1.2.0"})
    removed, spared = judged(root)
    assert removed == ["a@1.0.0"]
    assert spared["a@1.1.0"] == (
        "it is the newest release of `a` 1, which the library's next release is compared with"
    )


def test_a_newer_version_the_installed_capability_cannot_read_serves_in_no_place(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    hold(root, {"a": ["1.0.0", "1.1.0"]}, needs={"a@1.1.0": "9.0.0"})
    removed, spared = judged(root)
    assert removed == []
    assert spared["a@1.0.0"] == (
        "it is the newest version of `a` 1 that the installed capability reads, which a first "
        "lock takes"
    )


def test_what_a_librarys_builds_on_needs_stays_and_says_who_names_it(tmp_path: Path) -> None:
    root = project(tmp_path)
    hold(
        root,
        {"a": ["1.0.0", "1.1.0", "2.0.0"], "b": ["1.0.0"]},
        builds_on={"b@1.0.0": {"a": 1}},
    )
    piece(root, "p", {"a": "2.0.0"})
    removed, spared = judged(root)
    assert removed == ["a@1.0.0"]
    assert spared["a@1.1.0"] == (
        "it is the newest version of `a` 1 that the installed capability reads, which a first "
        "lock takes, and `builds-on` names that major in b@1.0.0"
    )
    assert spared["b@1.0.0"] == "it is the last version of `b`: nothing newer stands"


def test_a_version_the_list_does_not_name_is_spared(tmp_path: Path) -> None:
    root = project(tmp_path)
    hold(root, {"a": ["1.1.0"]})
    add_library(root, "a", "1.0.0")
    removed, spared = judged(root)
    assert removed == []
    assert spared["a@1.0.0"] == "the list does not name it, so the run cannot tell what it holds"


def test_a_location_with_no_library_has_nothing_to_judge(tmp_path: Path) -> None:
    assert judged(project(tmp_path)) == ([], {})


# --- the runs ------------------------------------------------------------------------------------


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run_main(script, *args, cwd=root)


def check(root: Path) -> subprocess.CompletedProcess[str]:
    return run_main(check_script, cwd=root, env={"PKIT_COMMAND_DEADLINE": None})


def newer(root: Path, *versions: str) -> None:
    """The `tests` library at each of `versions` too, every version listed released."""
    for version in versions:
        changed_tests(root / TESTS / version, version)
    list_drawing_libraries(root, released=True)


def behind(tmp_path: Path, **fields: Any) -> Path:
    """The drawing project with the `tests` library at 1.1.0 and 1.2.0 too, all released, and the
    draft `flow` locking 1.2.0, so `tests@1.0.0` and `tests@1.1.0` lie behind."""
    root = drawing_project(tmp_path, picture=False, lock={**LOCK, "tests": "1.2.0"}, **fields)
    newer(root, "1.1.0", "1.2.0")
    return root


def edit(root: Path, file: str, old: str, new: str) -> None:
    """Replace `old` in `file`, which must hold it."""
    path = root / file
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new), encoding="utf-8")


#: The list `behind` leads to.
BEHIND_LIST = [
    "lies behind, to remove with its entry in the list:",
    f"  tests@1.1.0: {TESTS}/1.1.0; tests@1.2.0 serves in its place",
    f"  tests@1.0.0: {TESTS}/1.0.0; tests@1.2.0 serves in its place",
    "spared:",
    "  foundations@1.0.0: the draft `flow` locks it",
    "  test-brand@1.0.0: the draft `flow` locks it",
    "  tests@1.2.0: the draft `flow` locks it",
]


def test_a_run_consented_up_front_removes_each_version_with_its_entry_from_the_working_tree(
    tmp_path: Path,
) -> None:
    root = behind(tmp_path)
    path = root / LIST
    path.write_text("# Kept.\n" + path.read_text(encoding="utf-8"), encoding="utf-8")
    listed = reading.read_yaml(path)
    done = run(root, "--yes")
    assert done.returncode == 0, done.stderr
    assert done.stdout.splitlines() == [
        *BEHIND_LIST,
        RECORDED_DEFAULT,
        f"removed tests@1.1.0: {TESTS}/1.1.0, and its entry in {LIST}",
        f"removed tests@1.0.0: {TESTS}/1.0.0, and its entry in {LIST}",
        script.LEFT,
        script.WAY_BACK,
    ]
    assert sorted(path.name for path in (root / TESTS).iterdir()) == ["1.2.0"]
    versions = listed["libraries"]["tests"]["versions"]
    listed["libraries"]["tests"]["versions"] = {"1.2.0": versions["1.2.0"]}
    assert reading.read_yaml(path) == listed
    assert path.read_text(encoding="utf-8").startswith("# Kept.\n")


def git(root: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout


def test_in_a_repository_it_removes_from_the_working_tree_and_stages_nothing(
    tmp_path: Path,
) -> None:
    root = behind(tmp_path)
    git(root, "init", "-q")
    git(root, "add", ".")
    git(root, "commit", "-qm", "the libraries")
    assert run(root, "--yes").returncode == 0
    assert git(root, "diff", "--cached", "--name-only") == ""
    shown = git(root, "status", "--porcelain", "--untracked-files=no").splitlines()
    assert {line[:3] for line in shown} == {" D ", " M "}
    assert {line[3:] for line in shown if line.startswith(" M ")} == {LIST}
    removed = {line[3:].split("/")[3] for line in shown if line.startswith(" D ")}
    assert removed == {"1.0.0", "1.1.0"}


def test_where_nothing_lies_behind_it_says_so_and_exits_0(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    before = every_file(root)
    done = run(root)
    assert done.returncode == 0, done.stderr
    assert done.stdout.splitlines() == [
        "spared:",
        "  foundations@1.0.0: the draft `flow` locks it",
        "  test-brand@1.0.0: the draft `flow` locks it",
        "  tests@1.0.0: the draft `flow` locks it",
        script.NOTHING,
    ]
    assert every_file(root) == before


def test_a_dry_run_shows_the_list_and_removes_nothing(tmp_path: Path) -> None:
    root = behind(tmp_path)
    before = every_file(root)
    done = run(root, "--dry-run", "--yes")
    assert done.returncode == 0, done.stderr
    assert done.stdout.splitlines() == [*BEHIND_LIST, script.DRY_RUN]
    assert every_file(root) == before


def test_with_nobody_to_ask_and_no_consent_it_refuses_and_removes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = behind(tmp_path)
    before = every_file(root)
    monkeypatch.setattr(script, "_terminal", lambda: False)
    done = run(root)
    assert done.returncode == 1
    assert done.stdout.splitlines() == BEHIND_LIST
    assert done.stderr == f"error: {script.NOBODY}\n"
    assert every_file(root) == before


@pytest.mark.parametrize(
    ("answer", "removes"), [("y", True), ("yes", True), ("n", False), ("", False)]
)
def test_a_terminal_is_asked_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, answer: str, removes: bool
) -> None:
    root = behind(tmp_path)
    before = every_file(root)
    asked: list[str] = []
    monkeypatch.setattr(script, "_terminal", lambda: True)
    monkeypatch.setattr("builtins.input", lambda question: asked.append(question) or answer)
    done = run(root)
    assert done.returncode == 0, done.stderr
    assert asked == ["remove the 2 versions listed? [y/N] "]
    if removes:
        assert sorted(path.name for path in (root / TESTS).iterdir()) == ["1.2.0"]
    else:
        assert done.stdout.splitlines() == [*BEHIND_LIST, script.DECLINED]
        assert every_file(root) == before


def test_a_check_passes_after_a_run_on_a_library_that_builds_on_another_included(
    tmp_path: Path,
) -> None:
    """`tests` and the test brand build on the foundations, and `parts` on `tests` 1: the run
    removes `tests@1.0.0`, and the check reads the newest of that major."""
    root = drawing_project(tmp_path, picture=False, released=True)
    add_library(root, "parts", "1.0.0", builds_on={"tests": 1})
    changed_tests(root / TESTS / "1.1.0", "1.1.0")
    list_drawing_libraries(root, released=True, parts="project")
    rendered = run_main(render_script, PIECE, cwd=root)
    assert rendered.returncode == 0, rendered.stderr
    done = run(root, "--yes")
    assert done.returncode == 0, done.stderr
    assert f"removed tests@1.0.0: {TESTS}/1.0.0, and its entry in {LIST}" in done.stdout
    assert "  parts@1.0.0: it is the last version of `parts`: nothing newer stands" in (
        done.stdout.splitlines()
    )
    checked = check(root)
    assert checked.returncode == 0, checked.stdout


# --- the locks of exports ------------------------------------------------------------------------


def export(root: Path) -> None:
    done = run_main(export_script, PIECE, cwd=root)
    assert done.returncode == 0, done.stderr


def test_a_published_pieces_lock_and_its_writers_lock_each_keep_what_they_name(
    tmp_path: Path,
) -> None:
    """The copy was written under `tests@1.0.0`, and the lock was written by hand since."""
    root = drawing_project(tmp_path, picture=False, state="published")
    export(root)
    newer(root, "1.1.0", "1.2.0")
    edit(root, PIECE_FILE, "tests: 1.0.0", "tests: 1.2.0")
    removed, spared = judged(root)
    assert removed == ["tests@1.1.0"]
    assert spared["tests@1.0.0"] == (
        "version 1 of `flow`, which wrote its current copy, was made under it"
    )
    assert spared["tests@1.2.0"] == "the published piece `flow` locks it"


def test_a_version_only_a_kept_export_names_goes_and_the_run_names_the_export(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path, picture=False, released=True)
    export(root)
    newer(root, "1.1.0")
    edit(root, PIECE_FILE, "tests: 1.0.0", "tests: 1.1.0")
    done = run(root, "--dry-run")
    assert done.returncode == 0, done.stderr
    assert done.stdout.splitlines() == [
        "lies behind, to remove with its entry in the list:",
        f"  tests@1.0.0: {TESTS}/1.0.0; tests@1.1.0 serves in its place",
        "spared:",
        "  foundations@1.0.0: the draft `flow` locks it",
        "  test-brand@1.0.0: the draft `flow` locks it",
        "  tests@1.1.0: the draft `flow` locks it",
        "kept exports made under a version to remove, which marking one final leaves a finding "
        "on until that version is back:",
        "  version 1 of `flow`, made under tests@1.0.0",
        script.DRY_RUN,
    ]


def test_a_kept_export_whose_fingerprint_gives_no_lock_is_named(tmp_path: Path) -> None:
    root = behind(tmp_path)
    write(root / RECORD, yaml_text(bound("exports", versions=[{"version": 1}])))
    done = run(root, "--dry-run")
    assert done.returncode == 0, done.stderr
    assert done.stdout.splitlines()[-3:] == [
        "kept exports whose fingerprint gives no lock, so the run cannot say what they were "
        "made under:",
        "  version 1 of `flow`: no fingerprint is kept",
        script.DRY_RUN,
    ]


# --- what stops it ------------------------------------------------------------------------------


def stopped(root: Path, *args: str) -> str:
    """What a stopped run says on standard error, having printed no list and changed no file."""
    before = every_file(root)
    done = run(root, "--yes", *args)
    assert done.returncode == 1
    assert done.stdout == ""
    assert every_file(root) == before
    return done.stderr


#: A current copy the record names, of the piece `flow`, written by its version 1.
COPY = {"piece": PIECE, "version": 1, "files": {f"current-copy/{PIECE}.en.default.svg": SHA}}


@pytest.mark.parametrize(
    ("file", "text", "said"),
    [
        pytest.param(
            PIECE_FILE,
            yaml_text(bound("piece", state="draft", lock={"tests": "latest"})),
            f"error: the lock of {PIECE_FILE} cannot be read: its lock names `tests: latest`, "
            f"which is no version. It may name any version, so the run removes nothing: mend it\n",
            id="lock",
        ),
        pytest.param(
            PIECE_FILE,
            "lock: [\n",
            f"error: the lock of {PIECE_FILE} cannot be read: ",
            id="piece-file",
        ),
        pytest.param(
            RECORD,
            "versions: [\n",
            f"error: {RECORD} cannot be read: ",
            id="record",
        ),
        pytest.param(
            RECORD,
            yaml_text(bound("exports", versions={})),
            f"error: {RECORD} cannot be read: it keeps no list of numbered versions. The run "
            f"cannot tell whether the lock of `flow` moves, so it removes nothing: mend the "
            f"record, or restore it as version control last held it\n",
            id="versions",
        ),
        pytest.param(
            RECORD,
            yaml_text(bound("exports", versions=[], **{"handed-out": "one"})),
            f"error: {RECORD} cannot be read: `handed-out` holds no version's number. ",
            id="handed-out",
        ),
        pytest.param(
            RECORD,
            yaml_text(bound("exports", versions=[], **{"current-copy": {"piece": PIECE}})),
            f"error: {RECORD} cannot be read: its `current-copy` names no piece, version and "
            f"files as its schema asks. ",
            id="current-copy",
        ),
        pytest.param(
            RECORD,
            yaml_text(bound("exports", versions=[{"version": 1}], **{"current-copy": COPY})),
            f"error: {RECORD} gives no lock of version 1, which wrote the current copy of `flow`: "
            f"no fingerprint is kept. That lock keeps what it names, so the run removes nothing: "
            f"restore the record as version control last held it\n",
            id="writer",
        ),
        pytest.param(
            LIST,
            "libraries: [\n",
            "error: the list of libraries cannot be read: ",
            id="list",
        ),
    ],
)
def test_what_the_run_cannot_read_stops_it_naming_the_file(
    tmp_path: Path, file: str, text: str, said: str
) -> None:
    root = behind(tmp_path)
    write(root / file, text)
    shown = stopped(root)
    assert shown.startswith(said), shown
    if not said.endswith("\n"):
        assert "removes nothing" in shown


def test_a_list_whose_text_cannot_lose_an_entry_stops_the_run(tmp_path: Path) -> None:
    root = behind(tmp_path)
    listed = reading.read_yaml(root / LIST)
    tests = listed["libraries"].pop("tests")
    text = yaml_text(listed) + "  tests:\n    source: {kind: project}\n    versions: {"
    text += ", ".join(f"{v}: {{released: true}}" for v in tests["versions"]) + "}\n"
    write(root / LIST, text)
    assert stopped(root) == (
        f"error: {LIST} cannot lose the entry of tests@1.1.0 as text: write "
        f"`libraries.tests.versions` as a block mapping, one version an entry. The run removes "
        f"nothing\n"
    )


# --- a failed removal ---------------------------------------------------------------------------


def test_a_removal_that_fails_leaves_every_file_as_it_was(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = behind(tmp_path)
    before = every_file(root)
    failing(monkeypatch, write={"libraries.yaml"})
    done = run(root, "--yes")
    assert done.returncode == 1
    assert done.stderr == f"error: {LIST} could not be written: {FULL}\n"
    assert every_file(root) == before
    assert sorted(path.name for path in (root / TESTS).iterdir()) == ["1.0.0", "1.1.0", "1.2.0"]
    assert not (root / CONFIG).exists()


def test_a_folder_that_cannot_be_removed_is_named_and_every_file_stays(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`tests@1.1.0` goes first, then `tests@1.0.0` cannot be moved aside."""
    root = behind(tmp_path)
    before = every_file(root)
    rename = os.rename

    def held(source: Any, target: Any) -> None:
        if Path(source).name == "1.0.0":
            raise OSError(errno.EBUSY, os.strerror(errno.EBUSY), str(source))
        rename(source, target)

    monkeypatch.setattr(os, "rename", held)
    done = run(root, "--yes")
    assert done.returncode == 1
    assert done.stderr == (
        f"error: {TESTS}/1.0.0 could not be removed: {os.strerror(errno.EBUSY)}\n"
    )
    assert every_file(root) == before
    assert sorted(path.name for path in (root / TESTS).iterdir()) == ["1.0.0", "1.1.0", "1.2.0"]


def test_a_folder_that_cannot_be_moved_back_is_named(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = behind(tmp_path)
    failing(monkeypatch, write={"libraries.yaml", "1.0.0"})
    done = run(root, "--yes")
    assert done.returncode == 1
    assert done.stderr == (
        f"error: {LIST} could not be written: {FULL}; these could not be put back as they were "
        f"before the run: {TESTS}/1.0.0\n"
    )
    assert (root / TESTS / "1.1.0").is_dir()
