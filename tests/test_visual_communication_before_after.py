"""`pkit visual before-after <piece>` (visual-communication DEC-019 point 5): a look ahead at a
published piece, a draft and a final piece, a look back at a change, and what both draw from.
Run in this process, the SVG renderer standing in for the import a run makes when it draws,
and `pkit` answered in this process. A look back runs in a git repository of the test's own."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tests import visual_communication_producer as producer
from tests.in_process import load, route_pkit, run_main
from tests.test_visual_communication_pipeline import (
    PIECE,
    PIECE_FOLDER,
    changed_tests,
    drawing_project,
    every_file,
    stamped,
    write_picture,
)
from tests.visual_communication_project import (
    CAPABILITY,
    CONFIG,
    TEST_BRAND,
    copy_library,
    importable,
    write,
    write_list,
    write_piece,
    yaml_text,
)

script, export_script, svg, seam, framing, backbone, before_after, libraries, looks, reading = load(
    "visual-communication",
    "before-after.py",
    "export.py",
    "plugins.svg",
    "plugins.seam",
    "framing",
    "backbone",
    "before_after",
    "libraries",
    "looks",
    "reading",
)

FOLDER = f"{before_after.FOLDER}/{PIECE}"
RECORD = f"{PIECE_FOLDER}/exports.yaml"
FILES = [f"{PIECE}.en.colour-scheme.dark.svg", f"{PIECE}.en.default.svg"]
OLD = "foundations 1.0.0, test-brand 1.0.0, tests 1.0.0"
NEW = "foundations 1.0.0, test-brand 1.0.0, tests 1.1.0"
WROTE = "the lock of version 1, which wrote the current copy"
DIFFER = [f"drawn both ways in {FOLDER}/: 2 of 2 files differ"] + [f"differs: {f}" for f in FILES]
SAME = [f"drawn both ways in {FOLDER}/: 0 of 2 files differ"]


@pytest.fixture(autouse=True)
def plugins(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The renderer stands in for the import a run makes when it draws, the test producer is
    registered, and `pkit` is answered in this process, for the length of the test."""
    importable(monkeypatch, svg)
    producer.register(seam)
    route_pkit(monkeypatch, backbone)
    yield
    seam.unregister(producer.NAME)


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run_main(script, *args, cwd=root)


def lines(shown: subprocess.CompletedProcess[str]) -> list[str]:
    assert shown.returncode == 0, shown.stderr
    return shown.stdout.splitlines()


def listed(root: Path, released: bool = True) -> None:
    """Each version of each library the location holds, listed released or not."""
    folder = root / "visual" / "libraries"
    write_list(
        root,
        {
            library.name: {
                "source": {"kind": "project"},
                "versions": {
                    version.name: {"released": released}
                    for version in library.iterdir()
                    if version.is_dir()
                },
            }
            for library in folder.iterdir()
            if library.is_dir()
        },
    )


def not_released(root: Path, version: str) -> None:
    """The list marks the `tests` library's `version` not released."""
    path = root / "visual/libraries/libraries.yaml"
    data = reading.read_yaml(path)
    data["libraries"]["tests"]["versions"][version] = {"released": False}
    path.write_text(yaml_text(data), encoding="utf-8")


def other_tests(root: Path, version: str = "1.1.0") -> Path:
    """The `tests` library at `version` too, which draws a step's head otherwise."""
    return changed_tests(root / "visual/libraries/tests" / version, version)


def other_brand(root: Path, file: str = "", old: str = "", new: str = "") -> None:
    """The test brand at 1.1.0 too, listed released, the first `old` of its tokens' `file`
    replaced by `new` where a file is named."""
    folder = copy_library(root, TEST_BRAND, "test-brand", "1.1.0")
    library = folder / "library.yaml"
    text = library.read_text(encoding="utf-8")
    library.write_text(text.replace("version: 1.0.0", "version: 1.1.0"), encoding="utf-8")
    if file:
        tokens = folder / "tokens" / file
        text = tokens.read_text(encoding="utf-8")
        assert old in text
        tokens.write_text(text.replace(old, new, 1), encoding="utf-8")
    listed(root)


def edit(root: Path, old: str, new: str) -> None:
    """Replace `old` in the piece's own file, which must hold it."""
    path = root / PIECE_FOLDER / "piece.yaml"
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new), encoding="utf-8")


def published(tmp_path: Path, **fields: Any) -> Path:
    """The skeleton piece, published and exported once, under a lock of released versions,
    and the `tests` library at 1.1.0 too, which draws it otherwise."""
    root = drawing_project(tmp_path, state="published", picture=False, **fields)
    assert run_main(export_script, PIECE, cwd=root).returncode == 0
    other_tests(root)
    listed(root)
    return root


def drawn(root: Path, side: str) -> dict[str, bytes]:
    return every_file(root / FOLDER / side)


# --- a look ahead at a published piece ----------------------------------------------------------


def test_a_look_ahead_draws_the_writers_lock_against_what_a_run_would_propose(
    tmp_path: Path,
) -> None:
    root = published(tmp_path)
    assert lines(run(root, PIECE, "--ahead")) == [
        f"before: {WROTE}: {OLD}",
        f"after: what a run would propose: {NEW}",
        *DIFFER,
    ]
    assert sorted(drawn(root, "before")) == sorted(drawn(root, "after")) == FILES
    assert drawn(root, "before") != drawn(root, "after")


def test_its_before_is_the_writers_lock_whatever_lock_the_piece_holds_now(tmp_path: Path) -> None:
    root = published(tmp_path)
    edit(root, "tests: 1.0.0", "tests: 1.1.0")
    said = lines(run(root, PIECE, "--ahead"))
    assert said[:2] == [f"before: {WROTE}: {OLD}", f"after: what a run would propose: {NEW}"]
    assert said[2:] == DIFFER


def test_a_published_piece_no_version_wrote_a_copy_of_has_the_lock_it_holds_for_a_before(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path, state="published", picture=False)
    other_tests(root)
    listed(root)
    assert lines(run(root, PIECE, "--ahead"))[:2] == [
        f"before: the lock the piece holds: {OLD}",
        f"after: what a run would propose: {NEW}",
    ]


def test_the_versions_named_take_the_place_of_what_a_run_would_propose(tmp_path: Path) -> None:
    root = published(tmp_path)
    other_tests(root, "1.2.0")
    listed(root)
    assert lines(run(root, PIECE, "--ahead", "tests@1.1.0")) == [
        f"before: {WROTE}: {OLD}",
        f"after: the versions named: {NEW}",
        *DIFFER,
    ]


def test_a_published_pieces_look_ahead_refuses_a_version_named_that_is_not_released(
    tmp_path: Path,
) -> None:
    root = published(tmp_path)
    other_tests(root, "1.2.0")
    listed(root)
    not_released(root, "1.2.0")
    shown = run(root, PIECE, "--ahead", "tests@1.2.0")
    assert shown.returncode == 1
    assert shown.stderr == (
        f"error: {PIECE_FOLDER}/piece.yaml: tests@1.2.0 is not released, and this move takes "
        "released versions\n"
    )
    assert not (root / before_after.FOLDER).exists()


def test_a_look_ahead_names_each_newer_version_it_did_not_take_with_why(tmp_path: Path) -> None:
    """Not only a clash or a lost end: each reason a default move holds a version back
    (DEC-019 point 7)."""
    root = published(tmp_path)
    other_tests(root, "1.2.0")
    other_tests(root, "2.0.0")
    listed(root)
    not_released(root, "1.2.0")
    said = lines(run(root, PIECE, "--ahead"))
    assert said[2:4] == [
        "held back: tests@2.0.0: it is of major 2, and the move stays within major 1",
        "held back: tests@1.2.0: it is not released",
    ]


def test_what_the_search_states_of_a_name_is_each_clash_and_lost_end_it_goes_past() -> None:
    misfits = (
        libraries.Misfit("clash", "the item `a` carries `b`", frozenset()),
        libraries.Misfit("end", "the end `c` of the tie `d` would not be found", frozenset()),
    )
    moved = libraries.Moved({}, below=("`tests` moves below 1.1.0",), kept="kept", past=misfits)
    assert looks._stated(moved) == (
        "`tests` moves below 1.1.0",
        "kept",
        "goes past a clash: the item `a` carries `b`",
        "goes past a lost end: the end `c` of the tie `d` would not be found",
    )


def test_a_record_it_cannot_read_leaves_no_before_and_stops_nothing(tmp_path: Path) -> None:
    root = published(tmp_path)
    write(root / RECORD, "not: [a record\n")
    said = lines(run(root, PIECE, "--ahead"))
    assert said[0] == f"after: what a run would propose: {NEW}"
    assert said[1].startswith(f"no before: {root / RECORD}: does not parse as YAML")
    assert said[2] == f"drawn in {FOLDER}/after/: 2 files, and nothing to compare them with"
    assert sorted(drawn(root, "after")) == FILES
    assert drawn(root, "before") == {}


def test_a_fingerprint_it_cannot_read_leaves_no_before_and_names_the_record(tmp_path: Path) -> None:
    root = published(tmp_path)
    record = reading.read_yaml(root / RECORD)
    del record["versions"][0]["fingerprint"]
    write(root / RECORD, yaml_text(record))
    assert lines(run(root, PIECE, "--ahead"))[1] == (
        f"no before: {RECORD} gives no lock of version 1, which wrote the current copy: no "
        "fingerprint is kept"
    )


# --- a look ahead at a draft --------------------------------------------------------------------


def pinned(tmp_path: Path) -> Path:
    root = drawing_project(tmp_path, picture=False, pinned=True)
    other_tests(root)
    listed(root, released=False)
    return root


NO_RUN = (
    "error: no run proposes a draft's lock, so a look ahead at `flow` takes the versions you "
    "name: `<library>@<version>`, as `pkit visual add` takes one\n"
)


def test_a_pinned_draft_takes_a_look_ahead_only_with_versions_named(tmp_path: Path) -> None:
    root = pinned(tmp_path)
    shown = run(root, PIECE, "--ahead")
    assert (shown.returncode, shown.stderr) == (1, NO_RUN)
    assert not (root / before_after.FOLDER).exists()


def test_a_pinned_drafts_names_may_take_a_version_not_yet_released(tmp_path: Path) -> None:
    root = pinned(tmp_path)
    assert lines(run(root, PIECE, "--ahead", "tests@1.1.0")) == [
        f"before: the lock the piece holds: {OLD}",
        f"after: the versions named: {NEW}",
        *DIFFER,
    ]


def test_a_library_a_name_leaves_alone_keeps_the_version_a_pinned_lock_names(
    tmp_path: Path,
) -> None:
    root = pinned(tmp_path)
    other_brand(root)
    listed(root, released=False)
    said = lines(run(root, PIECE, "--ahead", "tests@1.1.0"))
    assert said[1] == f"after: the versions named: {NEW}"


def test_a_draft_that_is_not_pinned_takes_one_as_a_pinned_draft_does(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    other_tests(root)
    listed(root, released=False)
    assert run(root, PIECE, "--ahead").stderr == NO_RUN
    assert lines(run(root, PIECE, "--ahead", "tests@1.1.0"))[1] == (
        f"after: the versions named: {NEW}"
    )


# --- a look ahead at a final piece --------------------------------------------------------------


def test_a_final_piece_takes_a_look_ahead_and_its_two_locks_are_one(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, state="final", picture=False)
    other_tests(root)
    listed(root)
    assert lines(run(root, PIECE, "--ahead")) == [
        f"before: the lock the piece holds: {OLD}",
        f"after: the lock the piece holds: {OLD}",
        "the two locks are one",
        *SAME,
    ]
    assert drawn(root, "before") == drawn(root, "after")


def test_a_final_piece_refuses_a_version_named(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, state="final", picture=False)
    other_tests(root)
    listed(root)
    shown = run(root, PIECE, "--ahead", "tests@1.1.0")
    assert shown.returncode == 1
    assert shown.stderr == (
        "error: the piece `flow` is final, so no version moves its lock: take the look ahead "
        "with none named\n"
    )


# --- a look back at a change --------------------------------------------------------------------


def git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
        cwd=root,
        check=True,
        capture_output=True,
    )


def committed(root: Path, folder: str = "visual") -> None:
    """`folder` committed on `main`, and a branch `change` cut from it."""
    git(root, "init", "-q", "-b", "main")
    git(root, "add", folder)
    git(root, "commit", "-q", "-m", "the base")
    git(root, "checkout", "-q", "-b", "change")


def head(root: Path) -> str:
    found = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    )
    return found.stdout.strip()[: looks.SHORT]


def test_a_look_back_draws_the_lock_of_the_version_that_wrote_the_copy_at_the_base(
    tmp_path: Path,
) -> None:
    root = published(tmp_path)
    committed(root)
    base = head(root)
    edit(root, "tests: 1.0.0", "tests: 1.1.0")
    assert lines(run(root, PIECE, "--back")) == [
        f"before: {WROTE}, at the base {base}: {OLD}",
        f"after: the lock the piece holds now: {NEW}",
        *DIFFER,
    ]


def test_a_look_back_reads_the_lock_held_at_the_base_where_no_version_wrote_a_copy(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path, picture=False)
    other_tests(root)
    listed(root, released=False)
    committed(root)
    base = head(root)
    edit(root, "tests: 1.0.0", "tests: 1.1.0")
    assert lines(run(root, PIECE, "--back"))[:2] == [
        f"before: the lock held at the base {base}: {OLD}",
        f"after: the lock the piece holds now: {NEW}",
    ]


def test_a_look_back_draws_both_sides_from_the_content_as_it_lies(tmp_path: Path) -> None:
    """An edit in the change shows on neither side alone, so a look back separates it from
    the move (DEC-019 point 3)."""
    root = drawing_project(tmp_path, picture=False)
    committed(root)
    content = root / PIECE_FOLDER / "content.en.yaml"
    content.write_text(
        content.read_text(encoding="utf-8").replace("Plan the work.", "Plan it again."),
        encoding="utf-8",
    )
    assert lines(run(root, PIECE, "--back"))[2:] == ["the two locks are one", *SAME]
    assert all(b"Plan it again." in data for data in drawn(root, "before").values())


def test_a_copy_of_another_piece_that_stood_at_the_base_is_no_copy_of_this_one(
    tmp_path: Path,
) -> None:
    """A folder copied by hand brings no copy while the original stands, there as here
    (DEC-017 point 7)."""
    root = published(tmp_path)
    record = reading.read_yaml(root / RECORD)
    record["current-copy"]["piece"] = "other"
    write(root / RECORD, yaml_text(record))
    write_piece(root, "other")
    committed(root)
    base = head(root)
    assert lines(run(root, PIECE, "--back"))[0] == (
        f"before: the lock held at the base {base}: {OLD}"
    )


def test_a_base_may_be_named_for_a_look_back(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    other_tests(root)
    listed(root, released=False)
    committed(root)
    edit(root, "tests: 1.0.0", "tests: 1.1.0")
    git(root, "add", "visual")
    git(root, "commit", "-q", "-m", "the lock moves")
    git(root, "branch", "named")
    named = head(root)
    assert lines(run(root, PIECE, "--back", "--base", "named"))[:3] == [
        f"before: the lock held at the base {named}: {NEW}",
        f"after: the lock the piece holds now: {NEW}",
        "the two locks are one",
    ]


def test_what_the_backbone_says_of_the_base_is_passed_on(tmp_path: Path) -> None:
    root = published(tmp_path)
    committed(root)
    shown = run(root, PIECE, "--back")
    assert shown.returncode == 0, shown.stderr
    assert "local branch" in shown.stderr


def test_a_base_that_resolves_to_nothing_refuses(tmp_path: Path) -> None:
    root = published(tmp_path)
    committed(root)
    shown = run(root, PIECE, "--back", "--base", "no-such-branch")
    assert shown.returncode == 1
    assert shown.stderr.startswith("error: the base 'no-such-branch' does not resolve to a commit")
    assert not (root / before_after.FOLDER).exists()


def test_a_reading_that_gives_no_document_refuses(tmp_path: Path) -> None:
    root = published(tmp_path)
    shown = run(root, PIECE, "--back")
    assert shown.returncode == 1
    assert shown.stderr.endswith(
        "error: `pkit repository base --json` exited 1 without its document\n"
    )
    assert not (root / before_after.FOLDER).exists()


def test_a_reading_of_a_version_it_does_not_know_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def newer(argv: Any, **_: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 0, '{"schema_version": 2}', "")

    route_pkit(monkeypatch, backbone, newer)
    root = published(tmp_path)
    shown = run(root, PIECE, "--back")
    assert shown.returncode == 1
    assert shown.stderr == (
        "error: `pkit repository base --json` answered schema_version 2; this capability reads 1\n"
    )


def test_a_piece_the_base_does_not_hold_has_no_before_and_the_command_says_so(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path, picture=False)
    committed(root, "visual/libraries")
    assert lines(run(root, PIECE, "--back")) == [
        f"after: the lock the piece holds now: {OLD}",
        f"no before: the base {head(root)} does not hold the piece `flow`",
        f"drawn in {FOLDER}/after/: 2 files, and nothing to compare them with",
    ]
    assert drawn(root, "before") == {}


def test_a_file_at_the_base_at_a_format_no_converter_reaches_leaves_no_before(
    tmp_path: Path,
) -> None:
    """The base's files are read as a file on disk is, and format 1 has no converter
    (DEC-003 point 2)."""
    root = published(tmp_path)
    edit(root, "schema_version: 1", "schema_version: 2")
    committed(root)
    base = head(root)
    edit(root, "schema_version: 2", "schema_version: 1")
    said = lines(run(root, PIECE, "--back"))
    assert said[1] == (
        f"no before: at the base {base}: {PIECE_FOLDER}/piece.yaml: is at format 2; the installed "
        "capability reads format 1"
    )
    assert sorted(drawn(root, "after")) == FILES


def test_a_piece_the_base_holds_with_no_lock_has_no_before(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False, lock=None)
    committed(root)
    base = head(root)
    path = root / PIECE_FOLDER / "piece.yaml"
    path.write_text(
        path.read_text(encoding="utf-8") + "lock:\n"
        "  foundations: 1.0.0\n  test-brand: 1.0.0\n  tests: 1.0.0\n",
        encoding="utf-8",
    )
    assert lines(run(root, PIECE, "--back"))[1] == (
        f"no before: the base {base} holds the piece `flow` with no lock"
    )


# --- what both drawings take --------------------------------------------------------------------


def test_where_the_two_locks_are_one_it_says_so_and_stops_nothing(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, state="published", picture=False)
    assert run_main(export_script, PIECE, cwd=root).returncode == 0
    listed(root)
    assert lines(run(root, PIECE, "--ahead")) == [
        f"before: {WROTE}: {OLD}",
        f"after: what a run would propose: {OLD}",
        "the two locks are one",
        *SAME,
    ]
    assert sorted(drawn(root, "before")) == FILES


def test_a_number_the_piece_shows_drops_out_of_what_differs(tmp_path: Path) -> None:
    """Both drawings take one filling of an export's facts, so two locks that draw alike
    differ in no page, though the piece shows its version and its date."""
    root = stamped(tmp_path, "number", state="published")
    other_brand(root)
    said = lines(run(root, PIECE, "--ahead"))
    assert said[1] == (
        "after: what a run would propose: foundations 1.0.0, test-brand 1.1.0, tests 1.0.0"
    )
    assert said[2:] == SAME
    assert all(b"v88" in data for data in drawn(root, "before").values())


def test_a_page_that_does_not_differ_is_not_printed(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, state="published", picture=False)
    other_brand(root, "dark.tokens.json", "{palette.night.900}", "{palette.night.800}")
    assert lines(run(root, PIECE, "--ahead"))[2:] == [
        f"drawn both ways in {FOLDER}/: 1 of 2 files differs",
        f"differs: {PIECE}.en.colour-scheme.dark.svg",
    ]


def test_where_the_engines_release_differs_from_the_copys_version_it_says_so(
    tmp_path: Path,
) -> None:
    root = published(tmp_path)
    record = reading.read_yaml(root / RECORD)
    record["versions"][0]["recorded"]["capability"] = "0.0.1"
    write(root / RECORD, yaml_text(record))
    now = ".".join(map(str, libraries.installed_release()))
    assert lines(run(root, PIECE, "--ahead"))[2] == (
        f"the engine is release {now}, and version 1, which wrote the copy, recorded 0.0.1: the "
        "copy's two sides hold more than the move"
    )


def test_a_look_back_compares_the_release_with_the_copys_version_at_the_base(
    tmp_path: Path,
) -> None:
    root = published(tmp_path)
    record = reading.read_yaml(root / RECORD)
    record["versions"][0]["recorded"]["capability"] = "0.0.1"
    write(root / RECORD, yaml_text(record))
    committed(root)
    assert "recorded 0.0.1" in lines(run(root, PIECE, "--back"))[3]


def test_a_copys_version_of_the_engines_release_says_nothing_of_it(tmp_path: Path) -> None:
    root = published(tmp_path)
    assert not any("the engine is release" in line for line in lines(run(root, PIECE, "--ahead")))


def pictured(tmp_path: Path) -> Path:
    """The piece with its picture, published, under a lock of released versions."""
    root = drawing_project(tmp_path, state="published")
    write_picture(root, framing)
    listed(root)
    return root


def test_it_draws_from_the_committed_pictures_and_reports_a_stale_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = pictured(tmp_path)
    edit(root, "width: 100", "width: 120")
    monkeypatch.setattr(framing, "run", lambda *_: pytest.fail("no program runs"))
    said = lines(run(root, PIECE, "--ahead"))
    assert said[2] == "the two locks are one" and said[3].startswith(
        "stale, before and after: `square`: "
    )
    assert all(b"data:image/png" in data for data in drawn(root, "after").values())


def test_a_picture_is_read_as_stale_under_each_sides_own_lock(tmp_path: Path) -> None:
    """Under the new lock an output may read other values, and go stale there alone
    (DEC-019 point 4)."""
    root = pictured(tmp_path)
    other_brand(root, "base.tokens.json", "{palette.blue.600}", "{palette.blue.800}")
    said = [line for line in lines(run(root, PIECE, "--ahead")) if line.startswith("stale")]
    assert len(said) == 1 and said[0].startswith("stale, after: `square`: ")


def test_a_picture_that_is_missing_is_reported_with_why(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, state="published")
    listed(root)
    said = lines(run(root, PIECE, "--ahead"))
    assert said[3].startswith("stale, before and after: `square`: ")
    assert "the picture was never produced" in said[3]


def test_a_library_version_gone_stops_nothing(tmp_path: Path) -> None:
    root = published(tmp_path)
    shutil.rmtree(root / "visual/libraries/tests/1.0.0")
    said = lines(run(root, PIECE, "--ahead"))
    assert said[2:] == [
        "no before: the lock names tests@1.0.0, which the project does not hold: restore it",
        f"drawn in {FOLDER}/after/: 2 files, and nothing to compare them with",
    ]
    assert sorted(drawn(root, "after")) == FILES


def test_a_drawing_neither_side_can_make_is_said_once_and_stops_nothing(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, state="final", picture=False)
    shutil.rmtree(root / "visual/libraries/tests/1.0.0")
    assert lines(run(root, PIECE, "--ahead"))[3:] == [
        "no drawing: the lock names tests@1.0.0, which the project does not hold: restore it"
    ]


# --- what it writes, and what it refuses --------------------------------------------------------


def test_it_writes_only_its_drawing_and_records_no_location(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    other_tests(root)
    listed(root, released=False)
    before = every_file(root)
    lines(run(root, PIECE, "--ahead", "tests@1.1.0"))
    after = every_file(root)
    assert sorted(set(after) - set(before)) == [
        f"{FOLDER}/{side}/{file}" for side in ("after", "before") for file in FILES
    ]
    assert {file: after[file] for file in before} == before
    assert not (root / CONFIG).exists()


def test_a_run_replaces_what_an_earlier_run_left(tmp_path: Path) -> None:
    root = published(tmp_path)
    lines(run(root, PIECE, "--ahead"))
    left = root / FOLDER / "after" / f"{PIECE}.en.default.2.svg"
    left.write_text("<svg/>", encoding="utf-8")
    shutil.rmtree(root / "visual/libraries/tests/1.0.0")
    lines(run(root, PIECE, "--ahead"))
    assert not left.exists()
    assert drawn(root, "before") == {}


def test_no_validator_runs_it_and_it_is_no_query() -> None:
    package = reading.read_yaml(CAPABILITY / "package.yaml")
    command = package["commands"]["before-after"]
    assert command["script"] == "scripts/before-after.py"
    assert "query-contract" not in command
    assert [each["command"] for each in package["validators"].values()] == ["check"]


def test_a_piece_with_no_lock_refuses_naming_what_writes_one(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False, lock=None)
    shown = run(root, PIECE, "--ahead", "tests@1.0.0")
    assert shown.returncode == 1
    assert shown.stderr == (
        "error: the piece `flow` has no lock yet, so no look draws it: run `pkit visual render "
        "flow` first\n"
    )


def test_a_published_piece_with_no_lock_refuses_naming_the_way_to_one(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False, lock=None, state="published")
    assert run(root, PIECE, "--ahead").stderr == (
        "error: the piece `flow` has no lock yet, so no look draws it: set it back to a draft for "
        "its first render\n"
    )


def test_a_project_with_no_visual_work_refuses(tmp_path: Path) -> None:
    root = tmp_path / "project"
    (root / ".pkit/capabilities/visual-communication").mkdir(parents=True)
    shown = run(root, PIECE, "--ahead")
    assert shown.returncode == 1
    assert shown.stderr == "error: the project holds no visual work, so no piece `flow`\n"


@pytest.mark.parametrize(
    "args",
    [
        (PIECE,),
        (PIECE, "--ahead", "--back"),
        (PIECE, "--ahead", "--base", "main"),
        (PIECE, "--back", "tests@1.1.0"),
    ],
    ids=["no-look", "both-looks", "base-ahead", "versions-back"],
)
def test_a_usage_error_exits_2(tmp_path: Path, args: tuple[str, ...]) -> None:
    assert run(drawing_project(tmp_path, picture=False), *args).returncode == 2
