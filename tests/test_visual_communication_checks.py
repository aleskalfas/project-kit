"""The check's findings (visual-communication DEC-002 point 4, DEC-003 point 9, DEC-004
points 8, 9 and 11, DEC-005 points 9 and 14): the lock, the ids and fields of the content,
an item of a list a part passes on under another name read against the component that
draws it, a page read against the layout or the component it names (DEC-010 point 5),
contrast as drawn, the losses the declaration of each renderer that draws the piece
predicts, the document the validator reads, a component it cannot read, a top that names
no component, the notations
a piece names and the concepts its content names (DEC-004 point 10), a list's component
field and arrangement fields, a key both an item's component and its list declare at the
lock, a pattern's clash with its default component checked alone (DEC-010 points 1 to 4
and 9), an error it does not expect on one piece, and a field's list of runs: read
against its run styles, skipped by the check of ids, each run measured against the fill
under it (DEC-012 points 1, 3 and 8). A tie's component, the shape of its ends and their
key paths, read in the content; an end the scene does not find, reported at its tie; a
list of ties whose default takes no ends, or declares an end field, checked alone
(DEC-011 point 8). A brand's logo, judged as any picture file is, by git's listing and
its encoding (DEC-025 points 2, 5 and 9). A failing finding in a copy of a library the
capability ships, released or not, and in a released one whose files changed (DEC-013
point 6). A final piece, read by
its files and its lock alone, each finding at a lock sorted by the piece's state, and a
version not yet released (DEC-002 point 7, DEC-003 point 9, DEC-017 point 4). The command
around it is `test_visual_communication_check.py`."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest

from tests import visual_communication_producer as producer
from tests.in_process import load
from tests.test_visual_communication_add import release
from tests.test_visual_communication_pipeline import (
    EVERY_WIDE,
    LOCK,
    NARROW,
    PHONE,
    PHONE_WIDE,
    PIECE,
    PIECE_FOLDER,
    TESTS,
    add_device,
    changed_tests,
    drawing_project,
    exported_up_to,
    filled,
    flipping,
    list_drawing_libraries,
    on_devices,
    parts_project,
    released_entry,
    system_project,
    write_content,
    write_picture,
)
from tests.visual_communication_project import (
    FOUNDATIONS,
    TEST_PARTS,
    TEST_PICTURES,
    add_library,
    bound,
    copy_library,
    hold_shipped,
    write,
    write_list,
    yaml_text,
)

(
    checks,
    pl,
    framing,
    seam,
    findings_,
    svg_declaration,
    pdf_declaration,
    fingerprint,
    copies,
    reading,
) = load(
    "visual-communication",
    "checks",
    "pipeline",
    "framing",
    "plugins.seam",
    "findings",
    "plugins.svg_declaration",
    "plugins.pdf_declaration",
    "fingerprint",
    "copies",
    "reading",
)

PIECE_FILE = f"{PIECE_FOLDER}/piece.yaml"
CONTENT = f"{PIECE_FOLDER}/content.en.yaml"

#: A component's file the reader refuses: a flow sequence that never closes.
UNPARSED = "parts: [\n"


@pytest.fixture(autouse=True)
def square() -> Any:
    producer.register(seam)
    yield
    seam.unregister(producer.NAME)


def piece_of(root: Path) -> Any:
    return pl.read_piece(root, "visual", PIECE)


def project_of(root: Path) -> Any:
    piece = piece_of(root)
    return pl.Project(piece, piece.lock, pl.Held(root, "visual"))


def codes(found: list[Any]) -> list[str]:
    return [finding.code for finding in found]


# --- the lock -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("lock", "code", "message"),
    [
        pytest.param(
            None,
            "lock-missing",
            "the piece has no lock yet, so its scenes cannot be drawn",
            id="missing",
        ),
        pytest.param(
            {"foundations": "1.0.0", "test-brand": "1.0.0"},
            "lock-incomplete",
            "the lock does not name `tests`, which the piece uses",
            id="incomplete",
        ),
        pytest.param(
            {**LOCK, "tests": "1.2.0"},
            "lock-not-held",
            "the lock names tests@1.2.0, which the project does not hold",
            id="not-held",
        ),
        pytest.param(
            {**LOCK, "tests": "one"},
            "lock-version",
            "the lock names `tests: one`, which is no version",
            id="no-version",
        ),
    ],
)
def test_a_lock_that_cannot_draw_the_piece_fails_naming_render(
    tmp_path: Path, lock: dict[str, str] | None, code: str, message: str
) -> None:
    root = drawing_project(tmp_path, lock=lock)
    [finding] = checks.lock_findings(pl.Held(root, "visual"), piece_of(root))
    assert (finding.code, finding.message) == (code, message)
    assert (finding.file, finding.where, finding.level) == (PIECE_FILE, "lock", "fails")
    assert finding.fix == "run `pkit visual render flow`, which moves a draft's lock"


def test_a_pinned_pieces_lock_is_mended_by_hand(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, lock={**LOCK, "tests": "1.2.0"}, pinned=True)
    [finding] = checks.lock_findings(pl.Held(root, "visual"), piece_of(root))
    assert finding.fix == (
        "change the lock by hand, or unpin the piece and run `pkit visual render flow`"
    )


@pytest.mark.parametrize("pinned", [True, False], ids=["pinned", "unpinned"])
@pytest.mark.parametrize("lock", [{**LOCK, "tests": "1.2.0"}, None], ids=["fault", "no-lock"])
def test_a_published_lock_is_mended_by_its_state_and_reads_no_pin(
    tmp_path: Path, pinned: bool, lock: dict[str, str] | None
) -> None:
    root = drawing_project(tmp_path, lock=lock, state="published", pinned=pinned)
    [finding] = checks.lock_findings(pl.Held(root, "visual"), piece_of(root))
    assert finding.fix == PUBLISHED_FIX


def test_a_whole_lock_has_no_finding(tmp_path: Path) -> None:
    root = drawing_project(tmp_path)
    assert checks.lock_findings(pl.Held(root, "visual"), piece_of(root)) == []


# --- the lock, by the piece's state -------------------------------------------------------------

DRAFT_FIX = "run `pkit visual render flow`, which moves a draft's lock"
PINNED_FIX = "change the lock by hand, or unpin the piece and run `pkit visual render flow`"
PUBLISHED_FIX = (
    "the piece is published, so no render moves its lock: set it back to a draft and run "
    "`pkit visual render flow`"
)

#: The lock's findings that need no library of their own to show, in a piece's own file.
FAULTS = [
    pytest.param(None, "lock-missing", id="no-lock"),
    pytest.param({**LOCK, "tests": "one"}, "lock-version", id="no-version"),
    pytest.param({**LOCK, "tests": "1.2.0"}, "lock-not-held", id="not-held"),
    pytest.param({"foundations": "1.0.0", "tests": "1.0.0"}, "lock-incomplete", id="left-out"),
]

#: Each state a lock's finding fails in whatever mends it, with what it names as its fix.
STATES = [
    pytest.param({}, DRAFT_FIX, id="draft"),
    pytest.param({"pinned": True}, PINNED_FIX, id="pinned"),
    pytest.param({"state": "published"}, PUBLISHED_FIX, id="published"),
]


def lock_found(root: Path, name: str = PIECE) -> list[tuple[str, str, str]]:
    """What the check of the piece alone says at its lock: each label, level and fix."""
    report = checks.check(root, only=name)
    return [(f.code, level, f.fix) for f, level in report.judged if f.where == "lock"]


@pytest.mark.parametrize(("lock", "code"), FAULTS)
@pytest.mark.parametrize(("fields", "fix"), STATES)
def test_a_lock_finding_fails_on_a_piece_that_is_not_final_and_names_its_states_fix(
    tmp_path: Path, lock: dict[str, str] | None, code: str, fields: dict[str, Any], fix: str
) -> None:
    root = drawing_project(tmp_path, lock=lock, picture=False, **fields)
    assert lock_found(root) == [(code, "fails", fix)]


@pytest.mark.parametrize(
    ("lock", "code", "level", "fix"),
    [
        pytest.param(None, "lock-missing", "fails", copies.WRITE_BACK, id="no-lock"),
        pytest.param(
            {**LOCK, "tests": "one"}, "lock-version", "fails", copies.WRITE_BACK, id="text"
        ),
        pytest.param(
            {**LOCK, "tests": "1.2.0"},
            "lock-not-held",
            "fails",
            "restore tests@1.2.0 in the library folder",
            id="not-held",
        ),
        pytest.param(
            {"foundations": "1.0.0", "tests": "1.0.0"},
            "lock-incomplete",
            "fact",
            checks.no_move(PIECE),
            id="left-out",
        ),
    ],
)
def test_on_a_final_piece_a_lock_finding_fails_only_where_more_than_a_move_mends_it(
    tmp_path: Path, lock: dict[str, str] | None, code: str, level: str, fix: str
) -> None:
    root = drawing_project(tmp_path, lock=lock, state="final", picture=False)
    assert lock_found(root) == [(code, level, fix)]


def test_a_library_a_locked_version_builds_on_is_a_fact_on_a_final_piece(tmp_path: Path) -> None:
    lock = {"test-brand": "1.0.0", "tests": "1.0.0"}
    root = drawing_project(tmp_path, lock=lock, state="final", picture=False)
    found = lock_found(root)
    assert {code for code, _, _ in found} == {"lock-incomplete"}
    assert {(level, fix) for _, level, fix in found} == {("fact", checks.no_move(PIECE))}


def extra_library(root: Path, *, released: bool, **fields: Any) -> dict[str, str]:
    """The library `extra` at 1.0.0 too, written from `fields` and listed as `released` says
    with the rest, and the lock that names it."""
    add_library(root, "extra", "1.0.0", **fields)
    list_drawing_libraries(root, released=released, extra="project")
    return {**LOCK, "extra": "1.0.0"}


def locked(root: Path, lock: dict[str, str]) -> None:
    """Write `lock` into the piece's own file, in place of the one it holds."""
    path = root / PIECE_FILE
    data = reading.read_yaml(path)
    data["lock"] = lock
    write(path, yaml_text(data))


@pytest.mark.parametrize(
    ("fields", "level", "fix"),
    [
        pytest.param({"state": "final"}, "fact", checks.no_move(PIECE), id="final"),
        pytest.param({"state": "published"}, "fails", PUBLISHED_FIX, id="published"),
        pytest.param({}, "fails", DRAFT_FIX, id="draft"),
        pytest.param({"pinned": True}, "fails", PINNED_FIX, id="pinned"),
    ],
)
def test_a_major_that_does_not_fit_only_a_move_mends(
    tmp_path: Path, fields: dict[str, Any], level: str, fix: str
) -> None:
    root = drawing_project(tmp_path, picture=False, **fields)
    released = fields.get("state") is not None
    locked(root, extra_library(root, released=released, builds_on={"foundations": 2}))
    assert lock_found(root) == [("lock-majors", level, fix)]


NEWER = "an upgrade mends it, with no move of the lock"


@pytest.mark.parametrize(
    ("fields", "level", "fix"),
    [
        pytest.param({"state": "final"}, "fails", NEWER, id="final"),
        pytest.param({"state": "published"}, "fails", PUBLISHED_FIX, id="published"),
        pytest.param({}, "fails", DRAFT_FIX, id="draft"),
        pytest.param({"pinned": True}, "fails", PINNED_FIX, id="pinned"),
    ],
)
def test_a_version_that_needs_a_newer_release_an_upgrade_mends(
    tmp_path: Path, fields: dict[str, Any], level: str, fix: str
) -> None:
    root = drawing_project(tmp_path, picture=False, **fields)
    released = fields.get("state") is not None
    locked(root, extra_library(root, released=released, needs_release="99.0.0"))
    assert lock_found(root) == [("lock-unreadable", level, fix)]


def faulty_library(root: Path, *, released: bool) -> None:
    """The library `extra` at 1.0.0 too, whose `library.yaml` names another version, under
    the piece's lock."""
    lock = extra_library(root, released=False)
    path = root / "visual/libraries/extra/1.0.0/library.yaml"
    write(path, path.read_text(encoding="utf-8").replace("version: 1.0.0", "version: 1.0.1"))
    list_drawing_libraries(root, released=released, extra="project")
    locked(root, lock)


def test_a_fault_in_a_version_the_project_holds_as_released_is_a_fact_on_a_final_piece(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path, state="final", picture=False)
    faulty_library(root, released=True)
    assert lock_found(root) == [("lock-unreadable", "fact", checks.no_move(PIECE))]


def test_a_fault_in_a_released_version_that_changed_fails_on_a_final_piece(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, state="final", picture=False)
    faulty_library(root, released=True)
    write(root / "visual/libraries/extra/1.0.0/notes.txt", "Added after the release.\n")
    assert lock_found(root) == [
        ("lock-unreadable", "fails", "mend or restore the `library.yaml` of extra@1.0.0"),
    ]


def test_a_fault_in_a_version_not_yet_released_fails_on_a_final_piece(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, state="final", picture=False)
    faulty_library(root, released=True)
    not_released(root, "extra", extra="project")
    assert lock_found(root) == [
        ("lock-unreadable", "fails", "mend or restore the `library.yaml` of extra@1.0.0"),
    ]


# --- a version not yet released under a lock ----------------------------------------------------


def not_released(root: Path, name: str, **more: str) -> None:
    """Every version the list names released, but `name`'s."""
    list_drawing_libraries(root, released=True, **more)
    path = root / "visual/libraries/libraries.yaml"
    data = reading.read_yaml(path)
    data["libraries"][name]["versions"]["1.0.0"] = {"released": False}
    write(path, yaml_text(data))


@pytest.fixture
def capability(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A capability's folder the test controls, building a copy of the foundations and
    releasing none, in place of the capability's own for the length of the test."""
    folder = tmp_path / "capability"
    shutil.copytree(FOUNDATIONS, folder / "libraries" / "foundations")
    monkeypatch.setattr(copies, "SHIPPED", folder)
    monkeypatch.setattr(checks, "SHIPPED", folder)
    return folder


def building(folder: Path, version: str) -> None:
    """The version being built in the capability's folder `folder` moved on to `version`."""
    path = folder / "libraries" / "foundations" / "library.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace("version: 1.0.0", f"version: {version}"),
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    "fields",
    [pytest.param({}, id="draft"), pytest.param({"pinned": True}, id="pinned")],
)
@pytest.mark.parametrize("name", ["tests", "foundations"], ids=["own", "shipped"])
def test_a_drafts_lock_on_a_version_not_yet_released_does_not_fail(
    tmp_path: Path, fields: dict[str, Any], name: str
) -> None:
    root = drawing_project(tmp_path, picture=False, **fields)
    not_released(root, name)
    assert lock_found(root) == []


@pytest.mark.parametrize("state", ["final", "published"])
def test_a_version_of_the_projects_own_not_yet_released_fails_and_its_release_mends_it(
    tmp_path: Path, state: str
) -> None:
    root = drawing_project(tmp_path, state=state, picture=False)
    not_released(root, "tests")
    report = checks.check(root, only=PIECE)
    [(finding, level)] = [(f, lv) for f, lv in report.judged if f.where == "lock"]
    assert (finding.code, level) == ("lock-not-released", "fails")
    assert finding.message == (
        f"the {state} piece `flow` locks tests@1.0.0, which is not yet released"
    )
    assert (finding.file, finding.fix) == (PIECE_FILE, "release it: `pkit visual release tests`")
    assert report.failed()


def test_a_shipped_copy_of_a_released_number_fails_on_a_final_piece_and_add_mends_it(
    tmp_path: Path, capability: Path
) -> None:
    release(capability)
    root = drawing_project(tmp_path, state="final", picture=False)
    not_released(root, "foundations")
    assert lock_found(root) == [
        (
            "lock-not-released",
            "fails",
            "run `pkit visual add foundations`, which replaces the copy as released",
        )
    ]


def test_a_shipped_copy_of_a_released_number_fails_on_a_published_piece_and_add_names_it(
    tmp_path: Path, capability: Path
) -> None:
    release(capability)
    root = drawing_project(tmp_path, state="published", picture=False)
    not_released(root, "foundations")
    assert lock_found(root) == [
        (
            "lock-not-released",
            "fails",
            "run `pkit visual add foundations --piece flow`, which replaces the copy as released",
        )
    ]


def test_a_shipped_copy_of_a_number_being_built_asks_for_attention_on_a_final_piece(
    tmp_path: Path, capability: Path
) -> None:
    root = drawing_project(tmp_path, state="final", picture=False)
    not_released(root, "foundations")
    report = checks.check(root, only=PIECE)
    [(finding, level)] = [(f, lv) for f, lv in report.judged if f.where == "lock"]
    assert (finding.code, level) == ("lock-not-released", "attention")
    assert finding.who == "whoever maintains the capability, who releases foundations@1.0.0"
    assert finding.fix == (
        "once the capability releases foundations@1.0.0, run `pkit visual add foundations`"
    )
    assert [f.code for f, lv in report.judged if lv == "fails"] == [checks.HANDED_OUT_NONE]


def test_a_shipped_copy_of_a_number_no_longer_shipped_states_a_fact_on_a_final_piece(
    tmp_path: Path, capability: Path
) -> None:
    building(capability, "1.1.0")
    root = drawing_project(tmp_path, state="final", picture=False)
    not_released(root, "foundations")
    assert lock_found(root) == [("lock-not-released", "fact", checks.no_move(PIECE))]


@pytest.mark.parametrize("version", ["1.0.0", "1.1.0"], ids=["being-built", "not-shipped"])
def test_a_shipped_copy_no_release_of_it_mends_fails_on_a_published_piece(
    tmp_path: Path, capability: Path, version: str
) -> None:
    building(capability, version)
    root = drawing_project(tmp_path, state="published", picture=False)
    not_released(root, "foundations")
    assert lock_found(root) == [("lock-not-released", "fails", PUBLISHED_FIX)]


def test_a_version_the_project_does_not_list_is_not_yet_released(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, state="published", picture=False)
    locked(root, extra_library(root, released=True))
    list_drawing_libraries(root, released=True)
    assert [code for code, _, _ in lock_found(root)] == ["lock-not-released"]


# --- a published lock behind a newer released version (DEC-003 point 9) -------------------------

OUTDATED = "`pkit visual outdated` says whether a move takes it, and why not"
WITHIN = (
    "the published piece `flow` locks tests@1.0.0, behind tests@1.1.0, a released version of "
    "its major",
    f"run `pkit visual upgrade flow`, which proposes the move; {OUTDATED}",
)
LATER = (
    "the published piece `flow` locks tests@1.0.0, behind tests@2.0.0, a released version of a "
    "later major",
    f"a later major is taken on purpose, by naming it: `pkit visual upgrade flow tests@2.0.0`; "
    f"{OUTDATED}",
)


def with_tests_at(root: Path, *versions: str, released: bool = True, needs: str = "") -> None:
    """The `tests` library at each of `versions` too, every version listed released with its
    hash, but each of `versions` where `released` is false; `needs` is the release each needs,
    where given."""
    for version in versions:
        library = changed_tests(root / "visual/libraries/tests" / version, version) / "library.yaml"
        if needs:
            text = library.read_text(encoding="utf-8")
            library.write_text(text.replace("needs-release: 0.1.0", f"needs-release: {needs}"))
    list_drawing_libraries(root, released=True)
    if not released:
        path = root / "visual/libraries/libraries.yaml"
        data = reading.read_yaml(path)
        for version in versions:
            data["libraries"]["tests"]["versions"][version] = {"released": False}
        write(path, yaml_text(data))


def behind(root: Path) -> list[tuple[str, str, str, str, str]]:
    """Each fact the check of the piece states that its lock is behind: the label, the level,
    the file, the message and the fix."""
    report = checks.check(root, only=PIECE)
    return [
        (f.code, level, f.file, f.message, f.fix)
        for f, level in report.judged
        if f.code == checks.LOCK_BEHIND
    ]


@pytest.mark.parametrize(
    ("versions", "said"),
    [
        pytest.param(("1.1.0",), [WITHIN], id="its-major"),
        pytest.param(("2.0.0",), [LATER], id="a-later-major"),
        pytest.param(("1.0.1", "1.1.0", "2.0.0"), [WITHIN, LATER], id="the-newest-of-each"),
    ],
)
def test_a_published_lock_behind_states_a_fact_naming_the_move_and_fails_nothing(
    tmp_path: Path, versions: tuple[str, ...], said: list[tuple[str, str]]
) -> None:
    root = drawing_project(tmp_path, state="published", picture=False)
    with_tests_at(root, *versions)
    assert behind(root) == [
        (checks.LOCK_BEHIND, "fact", PIECE_FILE, message, fix) for message, fix in said
    ]
    assert [
        f.where for f, _ in checks.check(root, only=PIECE).judged if f.code == checks.LOCK_BEHIND
    ] == ["lock"] * len(said)


@pytest.mark.parametrize(
    ("fields", "versions", "given"),
    [
        pytest.param({"state": "published"}, (), {}, id="at-the-newest"),
        pytest.param({"state": "published"}, ("1.1.0",), {"released": False}, id="not-released"),
        pytest.param({"state": "published"}, ("1.1.0",), {"needs": "9.0.0"}, id="unreadable"),
        pytest.param({}, ("1.1.0", "2.0.0"), {}, id="draft"),
        pytest.param({"pinned": True}, ("1.1.0", "2.0.0"), {}, id="pinned"),
        pytest.param({"state": "final"}, ("1.1.0", "2.0.0"), {}, id="final"),
    ],
)
def test_no_fact_of_a_lock_behind_where_none_is_or_the_state_moves_its_lock_otherwise(
    tmp_path: Path, fields: dict[str, Any], versions: tuple[str, ...], given: dict[str, Any]
) -> None:
    root = drawing_project(tmp_path, picture=False, **fields)
    with_tests_at(root, *versions, **given)
    assert behind(root) == []


def test_the_fact_of_a_lock_behind_stands_beside_a_lock_finding(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, state="published", picture=False)
    with_tests_at(root, "1.1.0")
    data = reading.read_yaml(root / "visual/libraries/libraries.yaml")
    data["libraries"]["test-brand"]["versions"]["1.0.0"] = {"released": False}
    write(root / "visual/libraries/libraries.yaml", yaml_text(data))
    found = [(f.code, level) for f, level in checks.check(root, only=PIECE).judged]
    assert ("lock-not-released", "fails") in found
    assert (checks.LOCK_BEHIND, "fact") in found


# --- a final piece ------------------------------------------------------------------------------


def made_final(root: Path) -> Path:
    """The drawing project's piece set final, each library it locks listed released."""
    path = root / PIECE_FILE
    path.write_text(
        path.read_text(encoding="utf-8").replace("state: draft", "state: final"), encoding="utf-8"
    )
    list_drawing_libraries(root, released=True)
    return root


def piece_labels(root: Path, *, only: str | None = None) -> set[str]:
    """Each label the check raises in the piece's folder, but the one a piece set final by hand
    takes for its version handed out, which `test_visual_communication_check.py` holds."""
    report = checks.check(root, only=only)
    found = {f.code for f, _ in report.judged if f.file.startswith(f"{PIECE_FOLDER}/")}
    return found - {checks.HANDED_OUT_NONE}


FINAL_SUMMARY = (
    "the piece `flow` in `visual`: the scenes of 0 read from their findings record, of 0 "
    "computed now, of 0 not checked, of 1 left out as final."
)


def test_a_final_pieces_changed_component_raises_no_finding(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    own = root / PIECE_FOLDER / "components" / "stamp.yaml"
    write(own, (TESTS / "components" / "stamp.yaml").read_text(encoding="utf-8"))
    assert overflowing_stamp(root, "piece/stamp")
    made_final(root)
    assert piece_labels(root) == set()
    assert checks.check(root, only=PIECE).summary == [FINAL_SUMMARY]


def test_a_final_pieces_check_computes_no_scene_and_reads_no_findings_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = drawing_project(tmp_path, state="final", picture=False)

    def refused(*_given: Any, **_named: Any) -> None:
        raise AssertionError("a final piece's check reached this")

    monkeypatch.setattr(pl, "compute_scene", refused)
    monkeypatch.setattr(checks, "read_findings_record", refused)
    monkeypatch.setattr(checks, "computed", refused)
    assert piece_labels(root) == set()


def test_a_findings_record_left_in_a_final_piece_goes_unread(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, state="final", picture=False)
    record = bound("findings", key={}, findings=[{"code": "text-overflow", "level": "fails"}])
    write(root / PIECE_FOLDER / "findings.yaml", yaml_text(record))
    assert piece_labels(root) == set()


def test_a_final_pieces_stale_output_raises_no_finding(tmp_path: Path) -> None:
    root = drawing_project(tmp_path)
    write_picture(root, framing)
    assert "produced-stale" not in piece_labels(root)
    path = root / PIECE_FILE
    path.write_text(
        path.read_text(encoding="utf-8").replace("fill: accent", "fill: surface"),
        encoding="utf-8",
    )
    assert "produced-stale" in piece_labels(root)
    made_final(root)
    assert piece_labels(root) == set()


def test_a_final_pieces_output_with_no_record_raises_no_finding(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, state="final")
    assert piece_labels(root) == set()


def test_a_final_pieces_content_value_its_component_refuses_raises_no_finding(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path, picture=False)
    write_content(root, body={"use": "tests/steps", "steps": [{"id": "1 bad", "shout": True}]})
    assert {"id-shape", "content-key"} <= piece_labels(root)
    made_final(root)
    assert piece_labels(root) == set()


@pytest.mark.parametrize("only", [None, PIECE], ids=["location", "alone"])
def test_a_final_pieces_missing_content_file_raises_no_finding(
    tmp_path: Path, only: str | None
) -> None:
    root = drawing_project(tmp_path, state="final", picture=False)
    (root / CONTENT).unlink()
    assert piece_labels(root, only=only) == set()


@pytest.mark.parametrize("only", [None, PIECE], ids=["location", "alone"])
@pytest.mark.parametrize(
    ("text", "code"),
    [
        pytest.param(UNPARSED, "file-unreadable", id="unreadable"),
        pytest.param("schema_version: 1\n", "binding", id="binding"),
    ],
)
def test_a_final_pieces_broken_content_file_raises_the_bindings_finding_and_its_lock_is_read(
    tmp_path: Path, text: str, code: str, only: str | None
) -> None:
    root = drawing_project(tmp_path, state="final", picture=False, lock={**LOCK, "tests": "1.2.0"})
    write(root / CONTENT, text)
    report = checks.check(root, only=only)
    found = {(f.code, f.file) for f, _ in report.judged}
    assert (code, CONTENT) in found
    assert ("lock-not-held", PIECE_FILE) in found
    assert not any(label == "piece-unreadable" for label, _ in found)


def test_a_library_a_final_pieces_content_came_to_use_raises_no_finding(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    write_content(root, body={"use": "later/steps", "steps": []})
    assert "lock-incomplete" in piece_labels(root)
    made_final(root)
    assert piece_labels(root) == set()


def test_a_final_piece_read_whole_still_holds_its_lock_to_its_content(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, state="final", picture=False)
    write_content(root, body={"use": "later/steps", "steps": []})
    [finding] = checks.lock_findings(pl.Held(root, "visual"), piece_of(root))
    assert (finding.code, finding.level) == ("lock-incomplete", "fact")
    assert (
        checks.lock_findings(pl.Held(root, "visual"), pl.read_piece_file(root, "visual", PIECE))
        == []
    )


@pytest.mark.parametrize("only", [None, PIECE], ids=["location", "alone"])
def test_a_version_a_final_piece_locks_that_no_longer_matches_fails_once(
    tmp_path: Path, only: str | None
) -> None:
    root = drawing_project(tmp_path, state="final", picture=False)
    write(root / "visual/libraries/tests/1.0.0/notes.txt", "Added after the release.\n")
    report = checks.check(root, only=only)
    [(finding, level)] = [(f, lv) for f, lv in report.judged if f.code == "library-changed"]
    assert level == "fails"
    assert finding.library == "tests@1.0.0"
    assert finding.message.startswith("tests@1.0.0 no longer matches what was released: ")
    assert finding.fix == "restore the version folder as it was released"


@pytest.mark.parametrize("only", [None, PIECE], ids=["location", "alone"])
def test_a_final_piece_under_a_list_that_cannot_be_read_is_read_as_on_no_released_version(
    tmp_path: Path, only: str | None
) -> None:
    """No version can be read against what was released, so none is, and the piece is no
    fault of the capability: it is left out as final like any other."""
    root = drawing_project(tmp_path, state="final", picture=False)
    write(root / "visual/libraries/libraries.yaml", "libraries: [\n")
    report = checks.check(root, only=only)
    codes = [f.code for f, _ in report.judged]
    assert "unexpected-error" not in codes
    assert "library-changed" not in codes
    assert ("list-unreadable" in codes) == (only is None)
    assert {level for f, level in report.judged if f.code == "lock-not-released"} == {"fails"}
    assert report.summary[0].endswith("of 0 not checked, of 1 left out as final.")


def test_two_final_pieces_on_a_version_that_no_longer_matches_report_it_once(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path, state="final", picture=False)
    shutil.copytree(root / PIECE_FOLDER, root / "visual/pieces/also")
    write(root / "visual/libraries/tests/1.0.0/notes.txt", "Added after the release.\n")
    report = checks.check(root)
    assert [f.code for f, _ in report.judged].count("library-changed") == 1


def test_a_run_on_a_draft_alone_reads_no_version_against_what_was_released(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False, released=True)
    write(root / "visual/libraries/tests/1.0.0/notes.txt", "Added after the release.\n")
    report = checks.check(root, only=PIECE)
    assert "library-changed" not in {f.code for f, _ in report.judged}


def test_a_shipped_copy_a_final_piece_locks_names_the_command_that_restores_it(
    tmp_path: Path, capability: Path
) -> None:
    root = drawing_project(tmp_path, state="final", picture=False)
    entry = release(capability)
    copy = root / "visual/libraries/foundations/1.0.0"
    shutil.rmtree(copy)
    shutil.copytree(FOUNDATIONS, copy)
    path = root / "visual/libraries/libraries.yaml"
    data = reading.read_yaml(path)
    data["libraries"]["foundations"]["versions"]["1.0.0"] = entry
    write(path, yaml_text(data))
    write(copy / "notes.txt", "Added after the release.\n")
    report = checks.check(root, only=PIECE)
    [finding] = [f for f, _ in report.judged if f.code == "library-changed"]
    assert finding.fix == "run `pkit visual add foundations`, which restores it as released"


def test_the_summary_counts_a_final_piece_so_its_numbers_add_up(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False, released=True)
    final = root / "visual/pieces/also"
    shutil.copytree(root / PIECE_FOLDER, final)
    path = final / "piece.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace("state: draft", "state: final"), encoding="utf-8"
    )
    assert checks.check(root).summary == [
        "2 piece(s) in `visual`: the scenes of 0 read from their findings record, of 1 computed "
        "now, of 0 not checked, of 1 left out as final."
    ]


def test_a_final_pieces_own_file_that_cannot_be_read_counts_as_not_checked(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, state="final", picture=False, top="figure")
    report = checks.check(root, only=PIECE)
    assert "piece-unreadable" in {f.code for f, _ in report.judged}
    assert report.summary == [
        "the piece `flow` in `visual`: the scenes of 0 read from their findings record, of 0 "
        "computed now, of 1 not checked."
    ]


def test_an_error_the_check_does_not_expect_on_a_final_piece_counts_it_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = drawing_project(tmp_path, state="final", picture=False)

    def failing(*_given: Any) -> None:
        raise ValueError("a value it does not guard against")

    monkeypatch.setattr(checks, "lock_findings", failing)
    report = checks.check(root, only=PIECE)
    assert "unexpected-error" in {f.code for f, _ in report.judged}
    assert report.summary == [
        "the piece `flow` in `visual`: the scenes of 0 read from their findings record, of 0 "
        "computed now, of 1 not checked."
    ]


# --- library names and released versions ------------------------------------------------------


def held_as(root: Path, name: str, *, released: bool = False, source: str = "project") -> Path:
    """The drawing project without its picture, the `tests` library held, listed and used
    under `name` instead, from the source `source`; released where `released` says so."""
    folder = root / "visual" / "libraries" / name
    (root / "visual" / "libraries" / "tests").rename(folder)
    for path in folder.rglob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        path.write_text(
            text.replace("name: tests", f"name: {name}").replace("tests/", f"{name}/"),
            encoding="utf-8",
        )
    unreleased = {"1.0.0": {"released": False}}
    write_list(
        root,
        {
            "foundations": {"source": {"kind": "shipped"}, "versions": unreleased},
            "test-brand": {"source": {"kind": "project"}, "versions": unreleased},
            name: {
                "source": {"kind": source},
                "versions": {"1.0.0": released_entry(folder / "1.0.0", name)}
                if released
                else unreleased,
            },
        },
    )
    steps = [{"id": "plan", "head": "Plan."}, {"id": "build", "head": "Build."}]
    write_content(root, body={"use": f"{name}/steps", "steps": steps})
    lock = {"foundations": "1.0.0", "test-brand": "1.0.0", name: "1.0.0"}
    write(
        root / PIECE_FILE,
        (root / PIECE_FILE)
        .read_text(encoding="utf-8")
        .replace("  tests: 1.0.0\n", f"  {name}: 1.0.0\n"),
    )
    assert piece_of(root).lock == lock
    return root


def test_a_library_named_after_a_top_group_of_the_shared_roles_fails(tmp_path: Path) -> None:
    root = held_as(drawing_project(tmp_path, picture=False), "line")
    report = checks.check(root)
    [(finding, level)] = [(f, level) for f, level in report.judged if f.code == "library-name"]
    assert level == "fails"
    assert checks.place(finding) == "visual/libraries/line/1.0.0/library.yaml#name"
    assert finding.message == "`line` is a top group of the shared roles, so no library takes it"
    assert finding.library == "line@1.0.0"


def test_a_failing_finding_in_a_released_version_asks_its_owner_for_attention(
    tmp_path: Path,
) -> None:
    root = held_as(drawing_project(tmp_path, picture=False), "line", released=True)
    report = checks.check(root)
    [(finding, level)] = [(f, level) for f, level in report.judged if f.code == "library-name"]
    assert level == "attention"
    assert finding.who == "the owner of `line`, who corrects it in a new release"
    assert checks.said(finding).startswith(
        "`line` is a top group of the shared roles, so no library takes it — for the owner of "
        "`line`, who corrects it in a new release — "
    )


def test_a_released_version_that_changed_fails_as_the_projects_to_restore(
    tmp_path: Path,
) -> None:
    root = held_as(drawing_project(tmp_path, picture=False), "line", released=True)
    write(root / "visual/libraries/line/1.0.0/notes.txt", "Added after the release.\n")
    report = checks.check(root)
    levels = {f.code: (level, f.who) for f, level in report.judged}
    assert levels["library-changed"] == ("fails", "")
    assert levels["library-name"] == ("fails", "")


def test_the_checks_scenes_take_the_stand_ins_whatever_the_clone_holds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The check computes a piece with no findings record with the stand-ins, so its answer
    turns on no clone's next number and no day (DEC-016 point 5)."""
    root = drawing_project(tmp_path, picture=False)
    write_content(root, body={"use": "tests/stamp", "shows": "number"})
    exported_up_to(root, 41)
    taken = filled(monkeypatch, pl)
    checks.check(root, only=PIECE)
    assert taken == [pl.read_piece_file(root, "visual", PIECE).stand_ins]


def overflowing_stamp(root: Path, use: str) -> list[tuple[Any, str]]:
    """What the check says of the stand-in the piece's stamp shows, too wide for its text."""
    write_content(root, body={"use": use, "shows": "narrow"})
    report = checks.check(root)
    return [(f, level) for f, level in report.judged if f.code == "text-overflow"]


def test_a_stand_in_that_overflows_in_a_library_the_project_corrects_fails(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path, picture=False)
    [(finding, level)] = overflowing_stamp(root, "tests/stamp")
    assert level == "fails"
    assert finding.where == "figure/body/narrow"
    assert finding.file == "visual/libraries/tests/1.0.0/components/stamp.yaml"
    assert finding.library == "tests@1.0.0"
    assert "fact:version in `tests/stamp`" in finding.message


def test_a_stand_in_that_overflows_in_the_pieces_own_component_fails(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    own = root / PIECE_FOLDER / "components" / "stamp.yaml"
    stamp = TESTS / "components" / "stamp.yaml"
    write(own, stamp.read_text(encoding="utf-8"))
    [(finding, level)] = overflowing_stamp(root, "piece/stamp")
    assert level == "fails"
    assert finding.file == f"{PIECE_FOLDER}/components/stamp.yaml"
    assert finding.library == ""


def test_a_stand_in_that_overflows_in_a_released_library_asks_its_owner_for_attention(
    tmp_path: Path,
) -> None:
    root = held_as(drawing_project(tmp_path, picture=False), "stamps", released=True)
    [(finding, level)] = overflowing_stamp(root, "stamps/stamp")
    assert level == "attention"
    assert finding.where == "figure/body/narrow"
    assert finding.file == "visual/libraries/stamps/1.0.0/components/stamp.yaml"
    assert finding.who == "the owner of `stamps`, who corrects it in a new release"


def test_a_finding_lowered_in_a_released_version_names_the_owner_and_is_never_stored() -> None:
    finding = findings_.Finding("text-overflow", "fails", "too wide", library="tests@1.0.0")
    assert findings_.as_read(finding, released=False) == (finding, "fails")
    lowered, level = findings_.as_read(finding, released=True)
    assert (level, lowered.who) == (
        "attention",
        "the owner of `tests`, who corrects it in a new release",
    )
    assert finding.who == "" and finding.level == "fails"
    fact = findings_.Finding("component-experimental", "fact", "a fact", library="tests@1.0.0")
    assert findings_.as_read(fact, released=True) == (fact, "fact")


# --- the content --------------------------------------------------------------------------------


def steps(*entries: dict[str, Any]) -> dict[str, Any]:
    return {"use": "tests/steps", "steps": list(entries)}


def test_ids_are_of_the_id_shape_unique_in_their_list_and_the_same_in_every_language(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path, languages=["en", "cs"])
    write_content(root, body=steps({"id": "plan", "head": "A"}, {"id": "plan", "head": "B"}))
    write_content(root, "cs", body=steps({"id": "yes", "head": "A"}, {"id": "plan", "head": "B"}))
    found = checks.id_findings(piece_of(root))
    assert [(f.code, f.file, f.where) for f in found] == [
        ("id-twice", CONTENT, "body.steps"),
        ("id-shape", f"{PIECE_FOLDER}/content.cs.yaml", "body.steps"),
        ("id-languages", f"{PIECE_FOLDER}/content.cs.yaml", "body.steps"),
    ]
    assert found[0].message == (
        "the ids `plan` appear twice in one list: an id is unique in its list"
    )


def test_a_translation_may_order_a_lists_items_its_own_way(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, languages=["en", "cs"])
    write_content(root, body=steps({"id": "plan", "head": "A"}, {"id": "build", "head": "B"}))
    write_content(root, "cs", body=steps({"id": "build", "head": "B"}, {"id": "plan", "head": "A"}))
    assert checks.id_findings(piece_of(root)) == []


def test_an_id_one_language_lacks_is_named_and_a_repeated_id_still_reported(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path, languages=["en", "cs"])
    write_content(root, body=steps({"id": "plan", "head": "A"}, {"id": "build", "head": "B"}))
    write_content(root, "cs", body=steps({"id": "plan", "head": "A"}, {"id": "plan", "head": "B"}))
    found = checks.id_findings(piece_of(root))
    assert [(f.code, f.file) for f in found] == [
        ("id-twice", f"{PIECE_FOLDER}/content.cs.yaml"),
        ("id-languages", f"{PIECE_FOLDER}/content.cs.yaml"),
    ]
    assert found[1].message == (
        "`body.steps` in `cs` lacks the ids `build`, which it holds in `en`: an item keeps "
        "its id in every language"
    )


def test_content_is_checked_against_the_fields_of_each_component_it_fills(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path)
    write_content(
        root,
        caption=["not", "text"],
        body=steps(
            {"id": "plan", "haed": "A"},
            {"id": "note", "use": "tests/callout", "pictures": [{"id": "square"}]},
        ),
    )
    found = checks.content_findings(project_of(root))
    assert [(f.code, f.where, f.message) for f in found] == [
        (
            "content-key",
            "body.steps[plan].haed",
            "`tests/card` takes no field or option `haed`; did you mean `head`?",
        ),
        ("content-required", "body.steps[plan].head", "the field `head` is required"),
        ("content-required", "body.steps[note].label", "the field `label` is required"),
        (
            "content-required",
            "body.steps[note].pictures[square].output",
            "the field `output` is required",
        ),
        (
            "runs-unmarked",
            "caption",
            "the field holds a list, and takes text: only a field its component marks "
            "`x-pkit-runs` takes a list of runs",
        ),
    ]
    assert {f.file for f in found} == {CONTENT}


def test_content_that_fills_its_components_has_no_finding(tmp_path: Path) -> None:
    root = drawing_project(tmp_path)
    assert checks.content_findings(project_of(root)) == []


# --- contrast as drawn --------------------------------------------------------------------------


def colour(grey: float, alpha: float = 1) -> dict[str, Any]:
    return {"colorSpace": "srgb", "components": [grey, grey, grey], "alpha": alpha}


COLOURS = {
    "paper": {"default": colour(1), "colour-scheme.dark": colour(0)},
    "ink": {"default": colour(0), "colour-scheme.dark": colour(1)},
    "pale": {"default": colour(0.9), "colour-scheme.dark": colour(0.1)},
    "veil": {"default": colour(0, 0.5), "colour-scheme.dark": colour(0, 0.5)},
    "mist": {"default": colour(0.7)},
    "dim": {"default": colour(0.55)},
}
KEYS = ["default", "colour-scheme.dark"]


def run(fill: str, *, size: float = 16, weight: int = 400, words: str = "Word") -> Any:
    return {
        "text": words,
        "fill": fill,
        "style": "type.body",
        "font-family": ["Sans"],
        "font-size": size,
        "font-weight": weight,
    }


def text(trace: str, fill: str, *, x: float = 0, size: float = 16, weight: int = 400) -> Any:
    return runs(trace, [run(fill, size=size, weight=weight)], x=x)


def runs(trace: str, given: list[Any], *, x: float = 0) -> Any:
    """A text of one paragraph, on one line, of the runs `given`, each 40 px wide."""
    spans = [{"run": n, "text": r["text"], "width": 40} for n, r in enumerate(given)]
    return {
        "type": "text",
        "id": trace,
        "x": x,
        "y": 0,
        "width": 100,
        "height": 20,
        "line-height": 20,
        "text-anchor": "start",
        "text": "".join(r["text"] for r in given),
        "paragraphs": [given],
        "lines": [
            {
                "text": "".join(r["text"] for r in given),
                "width": 40 * len(given),
                "baseline": 15,
                "paragraph": 0,
                "spans": spans,
            }
        ],
    }


def page(*children: Any) -> dict[str, Any]:
    group = {"type": "group", "id": "figure", "x": 0, "y": 0, "width": 400, "height": 100}
    return {"pages": ["figure"], "children": [{**group, "children": list(children)}]}


def box(trace: str, fill: str, *, x: float = 0, width: float = 400) -> dict[str, Any]:
    return {"type": "box", "id": trace, "x": x, "y": 0, "width": width, "height": 100, "fill": fill}


def test_each_text_is_measured_against_the_fill_under_it_in_every_combination() -> None:
    scene = page(box("figure/back", "paper"), text("figure/low", "pale"), text("figure/ok", "ink"))
    found = checks.drawn_contrast(scene, COLOURS, KEYS)
    assert [(f.code, f.where) for f in found] == [
        ("contrast-drawn", "figure/low"),
        ("contrast-drawn", "figure/low"),
    ]
    assert found[0].message == (
        "`pale` on `paper` has the contrast 1.25 in the combination `default`, below the 4.5 a "
        "text of 16 px needs (`text`)"
    )
    assert found[0].file == "piece.yaml"


def test_large_text_needs_less_and_a_translucent_fill_is_laid_over_the_one_under_it() -> None:
    scene = page(
        box("figure/back", "paper"),
        box("figure/veil", "veil", width=200),
        text("figure/large", "mist", size=24),
        text("figure/bold", "dim", x=210, size=19, weight=700),
        text("figure/regular", "dim", x=210, size=19),
    )
    found = checks.drawn_contrast(scene, COLOURS, ["default"])
    # Mist on half-black over white, a mid grey, falls below large text's 3. Dim on white
    # passes the 3 bold text of 18.66 px needs, and fails the 4.5 the same text needs
    # unbolded.
    assert [(f.where, f.message.split(" in ")[0]) for f in found] == [
        ("figure/large", "`mist` on `veil` has the contrast 1.89"),
        ("figure/regular", "`dim` on `paper` has the contrast 3.35"),
    ]


def test_a_text_over_a_picture_or_over_nothing_is_not_measured() -> None:
    picture = {"type": "image", "id": "figure/pic", "x": 0, "y": 0, "width": 400, "height": 100}
    assert checks.drawn_contrast(page(picture, text("figure/t", "pale")), COLOURS, KEYS) == []
    assert checks.drawn_contrast(page(text("figure/t", "pale")), COLOURS, KEYS) == []


# --- a piece on a size axis ---------------------------------------------------------------------

HEAD = "figure/body/steps[plan]/head"


def test_a_text_that_overflows_at_one_size_is_one_finding_that_opens_with_its_key(
    tmp_path: Path,
) -> None:
    root = on_devices(tmp_path, head=PHONE_WIDE)
    found = checks.computed(project_of(root))
    [overflow] = [f for f in found if f.code == "text-overflow"]
    assert (overflow.file, overflow.where) == ("content.en.yaml", HEAD)
    assert overflow.message.startswith(f"`{PHONE}`: {HEAD}: a word of ")
    # A finding the same at both sizes reads as on a piece of one size.
    statuses = [f.message for f in found if f.code == "component-experimental"]
    assert statuses
    assert all(message.startswith("the piece uses `") for message in statuses)


def test_a_finding_that_reads_otherwise_at_each_size_is_reported_for_each(tmp_path: Path) -> None:
    root = on_devices(tmp_path, head=EVERY_WIDE)
    found = [f.message for f in checks.computed(project_of(root)) if f.code == "text-overflow"]
    widths = [message.split("is wider than the text's width ")[1] for message in found]
    assert [message.split(": ")[0] for message in found] == ["`default`", f"`{PHONE}`"]
    assert widths[0] != widths[1]


def test_content_a_size_hides_is_a_fact_at_that_size_alone(tmp_path: Path) -> None:
    """The note is drawn on a desktop alone, and the steps at both sizes, by another part
    at each: the note alone is stated, at the phone's key (DEC-021 point 5)."""
    found = checks.computed(project_of(flipping(tmp_path)))
    [hidden] = [f for f in found if f.code == "size-hidden"]
    assert (hidden.level, hidden.file, hidden.where) == ("fact", "content.en.yaml", "body.note")
    assert hidden.message == f"`{PHONE}`: `body.note` is drawn at `default`, and not at this size"
    assert {f.code for f in found} == {"size-hidden", "component-experimental"}


def test_a_piece_on_one_size_states_no_hidden_content(tmp_path: Path) -> None:
    project = project_of(flipping(tmp_path, modes={"device": ["phone"]}))
    assert project.size_keys == [PHONE]
    assert [f for f in checks.computed(project) if f.code == "size-hidden"] == []


def test_contrast_is_judged_in_each_combination_from_the_scene_that_serves_it(
    tmp_path: Path,
) -> None:
    dark = "colour-scheme.dark"
    root = drawing_project(
        tmp_path,
        picture=False,
        modes={"colour-scheme": ["light", "dark"], "device": ["desktop", "phone"]},
    )
    # A phone paints a step's head in the colour of a rule, too pale on its card.
    pale = {"text-primary": {"$type": "color", "$value": "{scheme.rule}"}}
    add_device(root, {**NARROW, **pale})
    found = [f for f in checks.computed(project_of(root)) if f.code == "contrast-drawn"]
    assert found
    named = {f.message.split("in the combination `")[1].split("`")[0] for f in found}
    assert named == {PHONE, f"{dark}+{PHONE}"}
    assert all(f.message.startswith(f"`{PHONE}`: `text-primary` on `") for f in found)


# --- losses -------------------------------------------------------------------------------------


def test_a_renderers_losses_are_known_from_its_declaration_before_it_runs() -> None:
    declaration = {"name": "flat", "draws": {"group": {}, "box": {"x": "draws", "fill": "draws"}}}
    scene = page(
        box("figure/back", "paper"),
        {"type": "ellipse", "id": "figure/dot", "x": 0, "y": 0, "width": 4, "height": 4},
    )
    lost = checks.losses(scene, declaration)
    assert [loss.as_dict() for loss in lost] == [
        {
            "plugin": "flat",
            "what": "figure",
            "did": "left-out",
            "why": "the flat renderer draws no `x` of a group",
        },
        {
            "plugin": "flat",
            "what": "figure",
            "did": "left-out",
            "why": "the flat renderer draws no `y` of a group",
        },
        {
            "plugin": "flat",
            "what": "figure",
            "did": "left-out",
            "why": "the flat renderer draws no `width` of a group",
        },
        {
            "plugin": "flat",
            "what": "figure",
            "did": "left-out",
            "why": "the flat renderer draws no `height` of a group",
        },
        {
            "plugin": "flat",
            "what": "figure/back",
            "did": "left-out",
            "why": "the flat renderer draws no `y` of a box",
        },
        {
            "plugin": "flat",
            "what": "figure/back",
            "did": "left-out",
            "why": "the flat renderer draws no `width` of a box",
        },
        {
            "plugin": "flat",
            "what": "figure/back",
            "did": "left-out",
            "why": "the flat renderer draws no `height` of a box",
        },
        {
            "plugin": "flat",
            "what": "figure/dot",
            "did": "refused",
            "why": "the flat renderer draws no `ellipse`",
        },
    ]


def test_the_svg_renderer_loses_nothing_of_the_skeleton_piece(tmp_path: Path) -> None:
    root = drawing_project(tmp_path)
    write_picture(root, framing)
    project = project_of(root)
    [(_, result)] = project.scenes(facts=project.piece.stand_ins)
    assert checks.losses(result.scene.to_dict(), svg_declaration.DECLARATION) == []


@pytest.mark.parametrize(
    ("exports", "renderers"),
    [
        ([], ["svg"]),
        (["svg"], ["svg"]),
        (["pdf"], ["pdf", "svg"]),
        (["svg", "pdf"], ["pdf", "svg"]),
    ],
)
def test_a_piece_is_checked_against_its_previews_renderer_and_each_it_exports_in(
    tmp_path: Path, exports: list[str], renderers: list[str]
) -> None:
    root = drawing_project(tmp_path, exports=exports)
    assert checks.renderers(piece_of(root)) == renderers


def test_a_piece_exported_as_pdf_is_told_what_the_pdf_renderer_loses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The renderer draws every image (DEC-025 point 7), so a piece of a produced picture loses
    nothing in a PDF. Its declaration, the image taken out of it for the length of the test,
    stands for one that would lose it."""
    root = drawing_project(tmp_path, exports=["svg", "pdf"])
    write_picture(root, framing)
    assert [found for found, _ in checks.check(root).judged if found.code == "loss"] == []

    monkeypatch.delitem(pdf_declaration.DECLARATION["draws"], "image")
    report = checks.check(root)
    assert not report.failed()
    [(lost, level)] = [(f, level) for f, level in report.judged if f.code == "loss"]
    assert level == "attention"
    assert (lost.file, lost.where) == (PIECE_FILE, "figure/body/steps[note]/pictures[square]/image")
    assert lost.message == (
        "the pdf renderer refuses `figure/body/steps[note]/pictures[square]/image`: the pdf "
        "renderer draws no `image`"
    )


def test_a_loss_the_piece_accepts_is_no_finding_and_one_it_does_not_asks_its_author() -> None:
    loss = seam.Loss("svg", "figure/arrow", seam.REFUSED, "the svg renderer draws no `path`")
    accepting = [{"plugin": "svg", "what": "figure/arrow", "reason": "The arrow is drawn apart."}]
    assert checks.accepted(loss, accepting)
    assert not checks.accepted(loss, [{"plugin": "css", "what": "figure/arrow"}])
    finding = checks.loss_finding(loss)
    assert (finding.code, finding.level, finding.who) == ("loss", "attention", "the piece's author")
    assert finding.message == (
        "the svg renderer refuses `figure/arrow`: the svg renderer draws no `path`"
    )
    assert finding.fix == (
        "accept it under `accept-losses` with `plugin: svg`, `what: figure/arrow` and a "
        "reason, or change what draws it"
    )


# --- the run ------------------------------------------------------------------------------------


def test_scene_findings_name_the_component_file_and_the_command_that_makes_a_picture(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path)
    report = checks.check(root)
    failing = [(f.code, checks.place(f)) for f, level in report.judged if level == "fails"]
    # The producer's check says the picture is missing, once: the scene's own note of the
    # picture it could not draw repeats it, and is left out.
    assert failing == [
        ("produced-record-missing", f"{PIECE_FOLDER}/produced/square/record.yaml#produced.square"),
        (
            "missing-exposed",
            "visual/libraries/tests/1.0.0/components/callout.yaml#figure/body/steps[note]",
        ),
        (
            "missing-exposed",
            "visual/libraries/tests/1.0.0/components/callout.yaml#figure/body/steps[note]",
        ),
    ]
    [missing] = [f for f, _ in report.judged if f.code == "produced-record-missing"]
    assert "pkit visual produce flow square" in missing.fix


def test_the_skeleton_piece_with_its_picture_fails_nothing(tmp_path: Path) -> None:
    """With the foundations held as the capability ships them, so their copy raises no
    finding of its own."""
    root = drawing_project(tmp_path)
    hold_shipped(root, "foundations")
    write_picture(root, framing)
    report = checks.check(root)
    assert not report.failed()
    assert {f.code for f, _ in report.judged} == {"component-experimental", "picture-role-unvalued"}
    assert report.summary == [
        "1 piece(s) in `visual`: the scenes of 0 read from their findings record, of 1 "
        "computed now, of 0 not checked."
    ]


def test_past_the_deadline_a_piece_without_a_record_fails_as_not_checked(tmp_path: Path) -> None:
    root = drawing_project(tmp_path)
    write_picture(root, framing)
    report = checks.check(root, deadline=time.time())
    [(finding, level)] = [(f, level) for f, level in report.judged if f.code == "not-checked"]
    assert level == "fails"
    assert checks.place(finding) == f"{PIECE_FOLDER}/findings.yaml"
    assert finding.fix == "run `pkit visual render flow` and commit its findings record"
    assert "of 0 computed now, of 1 not checked" in report.summary[0]


def test_a_file_bound_to_another_schema_fails_and_a_piece_named_alone_is_checked_alone(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path)
    write(root / PIECE_FOLDER / "exports.yaml", yaml_text(bound("findings", versions=[])))
    write(root / "visual/pieces/other/piece.yaml", "top: [\n")
    report = checks.check(root, only=PIECE)
    bindings = [(f.code, f.file) for f, _ in report.judged if f.code == "binding"]
    assert bindings == [("binding", f"{PIECE_FOLDER}/exports.yaml")]
    assert not any("other" in f.file for f, _ in report.judged)
    missing = checks.check(root, only="nowhere")
    assert [(f.code, f.message) for f, _ in missing.judged] == [
        ("piece-missing", "the location holds no piece `nowhere`")
    ]


def test_no_visual_work_is_said_and_finds_nothing(tmp_path: Path) -> None:
    root = tmp_path / "project"
    (root / ".pkit" / "capabilities" / "visual-communication").mkdir(parents=True)
    report = checks.check(root)
    assert report.judged == []
    assert report.summary[0].startswith("No visual work: ")


# --- the document -------------------------------------------------------------------------------


def test_the_document_gives_each_finding_its_severity_place_and_what_mends_it() -> None:
    finding = findings_.Finding(
        "loss", "attention", "it is lost", file="a.yaml", where="figure", fix="fix it", who="you"
    )
    plain = findings_.Finding("other", "fact", "a fact", file="b.yaml")
    report = checks.Report(["One."], [(finding, "attention"), (plain, "fact")])
    assert checks.document(report) == {
        "summary": ["One."],
        "findings": [
            {
                "severity": "warning",
                "location": "a.yaml#figure",
                "message": "it is lost — for you — fix it",
                "label": "loss",
            },
            {"severity": "info", "location": "b.yaml", "message": "a fact", "label": "other"},
        ],
    }


@pytest.mark.parametrize(
    ("value", "deadline"),
    [("1700000000.5", 1700000000.5), ("", None), ("soon", None), ("inf", None)],
)
def test_the_deadline_is_read_from_the_environment(value: str, deadline: float | None) -> None:
    assert checks.deadline_from({checks.DEADLINE: value}) == deadline


@pytest.mark.parametrize(
    ("inside", "kind"),
    [
        ("libraries/libraries.yaml", "libraries"),
        ("libraries/tests/1.0.0/library.yaml", "library"),
        ("libraries/tests/1.0.0/components/card.yaml", "component"),
        ("libraries/foundations/1.0.0/roles.yaml", "roles"),
        ("libraries/test-notation/1.0.0/notation.yaml", "notation"),
        ("pieces/flow/piece.yaml", "piece"),
        ("pieces/flow/content.en.yaml", "content"),
        ("pieces/flow/findings.yaml", "findings"),
        ("pieces/flow/exports.yaml", "exports"),
        ("pieces/flow/components/own.yaml", "component"),
        ("pieces/flow/produced/square/record.yaml", "produced-record"),
        ("code/brand-css.yaml", "code"),
        ("pieces/flow/notes.yaml", None),
        ("libraries/test-brand/1.0.0/tokens/colour.tokens.json", None),
    ],
)
def test_a_files_kind_is_read_from_its_name_and_place(inside: str, kind: str | None) -> None:
    assert checks.kind_of(inside) == kind


# --- what the check cannot read, and what it does not expect ------------------------------------


def test_an_error_on_one_piece_of_two_fails_it_and_the_next_is_checked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = drawing_project(tmp_path, picture=False)
    shutil.copytree(root / PIECE_FOLDER, root / "visual/pieces/also")
    engine = pl.compute_scene

    def failing(**given: Any) -> Any:
        if given["piece"] == "also":
            raise ValueError("a value the engine does not guard against")
        return engine(**given)

    monkeypatch.setattr(pl, "compute_scene", failing)
    report = checks.check(root)

    [(unexpected, level)] = [(f, lv) for f, lv in report.judged if f.code == "unexpected-error"]
    assert level == "fails"
    assert checks.place(unexpected) == "visual/pieces/also/piece.yaml"
    assert unexpected.message == (
        "the check of `also` stopped on an error it does not expect: ValueError: a value the "
        "engine does not guard against"
    )
    assert ("component-experimental", f"{PIECE_FOLDER}/piece.yaml") in {
        (f.code, f.file) for f, _ in report.judged
    }
    assert report.summary == [
        "2 piece(s) in `visual`: the scenes of 0 read from their findings record, of 1 "
        "computed now, of 1 not checked."
    ]
    labels = [(f["severity"], f["label"]) for f in checks.document(report)["findings"]]
    assert ("error", "unexpected-error") in labels and ("info", "component-experimental") in labels


def test_a_component_whose_file_cannot_be_read_is_reported_at_that_file(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    broken = "visual/libraries/tests/1.0.0/components/broken.yaml"
    write(root / broken, UNPARSED)
    write_content(root, body={"use": "tests/broken"})

    alone = checks.check(root, only=PIECE)
    whole = checks.check(root)

    [(unreadable, level)] = [(f, lv) for f, lv in alone.judged if f.file == broken]
    assert (unreadable.code, level, checks.place(unreadable)) == (
        "component-unreadable",
        "fails",
        broken,
    )
    assert unreadable.message.startswith(
        "the component `tests/broken` cannot be read: does not parse as YAML: "
    )
    assert str(tmp_path) not in unreadable.message
    # The whole check reads the file in its binding pass, which reports it once.
    assert [f.code for f, _ in whole.judged if f.file == broken] == ["file-unreadable"]
    for report in (alone, whole):
        assert "unknown-component" not in [f.code for f, _ in report.judged]


def test_a_top_that_names_no_component_is_reported_at_its_place_in_the_piece(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path, picture=False, top="tests/nothing")
    [(unknown, level)] = [
        (f, lv) for f, lv in checks.check(root, only=PIECE).judged if f.code == "unknown-component"
    ]
    assert (level, checks.place(unknown)) == ("fails", f"{PIECE_FILE}#top")
    assert unknown.message == "the piece's top names no component `tests/nothing`"


# --- notations and concepts ---------------------------------------------------------------------

NOTATION = "visual/libraries/test-notation/1.0.0"
SYSTEM_CONTENT = "visual/pieces/system/content.en.yaml"


def failing(report: Any) -> list[tuple[str, str, str]]:
    return [(f.code, checks.place(f), f.message) for f, level in report.judged if level == "fails"]


def write_concepts(root: Path, **concepts: Any) -> None:
    write(root / NOTATION / "notation.yaml", yaml_text(bound("notation", concepts=concepts)))


def test_the_test_notation_and_the_concepts_its_content_names_fail_nothing(
    tmp_path: Path,
) -> None:
    assert failing(checks.check(system_project(tmp_path))) == []


def test_a_concept_that_maps_to_a_value_or_no_declared_family_fails_in_the_notation(
    tmp_path: Path,
) -> None:
    root = system_project(tmp_path)
    write_concepts(
        root,
        person={"colour": "#8250df"},
        service="blue",
        store={"colour": "teal"},
    )

    found = failing(checks.check(root))

    never = "a concept maps to a colour family the foundations declare, never to a value"
    families = "`neutral`, `blue`, `green`, `orange`, `purple`, `red`"
    assert found == [
        (
            "concept-shape",
            f"{NOTATION}/notation.yaml#concepts.person",
            f"the concept `person` maps to `#8250df`, which is no colour family's name: {never}",
        ),
        (
            "concept-shape",
            f"{NOTATION}/notation.yaml#concepts.service",
            f"the concept `service` is not `{{colour: <family>}}`: {never}",
        ),
        (
            "concept-shape",
            f"{NOTATION}/notation.yaml#concepts.store",
            f"the concept `store` maps to `teal`, which is no colour family the foundations "
            f"declare: {families}",
        ),
    ]


def test_a_library_that_is_no_notation_or_holds_none_fails_once_where_it_lies(
    tmp_path: Path,
) -> None:
    kind = system_project(tmp_path / "kind")
    library = kind / NOTATION / "library.yaml"
    library.write_text(library.read_text().replace("kind: notation", "kind: components"))
    absent = system_project(tmp_path / "absent")
    (absent / NOTATION / "notation.yaml").unlink()
    unparsed = system_project(tmp_path / "unparsed")
    write(unparsed / NOTATION / "notation.yaml", "concepts: [\n")

    assert failing(checks.check(kind)) == [
        (
            "notation-kind",
            f"{NOTATION}/library.yaml#kind",
            "test-notation@1.0.0 is not a notation (`kind: components`), yet a piece names it "
            "under `notations`",
        )
    ]
    assert failing(checks.check(absent)) == [
        (
            "notation-unreadable",
            f"{NOTATION}/notation.yaml",
            "test-notation@1.0.0 holds no `notation.yaml`",
        )
    ]
    # The binding pass reads the file, and reports it once.
    assert [code for code, _, _ in failing(checks.check(unparsed))] == ["file-unreadable"]
    alone = failing(checks.check(unparsed, only="system"))
    assert [(code, place) for code, place, _ in alone] == [
        ("notation-unreadable", f"{NOTATION}/notation.yaml")
    ]


def test_a_concept_the_piece_s_notations_do_not_hold_fails_in_the_content(
    tmp_path: Path,
) -> None:
    root = system_project(tmp_path)
    content = root / SYSTEM_CONTENT
    text = content.read_text()
    content.write_text(
        text.replace("concept: test-notation/person", "concept: test-notation/actor").replace(
            "concept: test-notation/store", "concept: other/store"
        )
    )

    assert failing(checks.check(root)) == [
        (
            "unknown-concept",
            f"{SYSTEM_CONTENT}#figure/body/items[store]",
            "figure/body/items[store]: the concept `other/store` comes from `other`, a notation "
            "the piece does not name under `notations`",
        ),
        (
            "unknown-concept",
            f"{SYSTEM_CONTENT}#figure/body/items[user]",
            "figure/body/items[user]: the notation test-notation@1.0.0 holds no concept `actor`",
        ),
    ]


def test_a_lock_that_lacks_a_notation_the_piece_names_is_incomplete(tmp_path: Path) -> None:
    root = system_project(tmp_path)
    piece = root / "visual/pieces/system/piece.yaml"
    piece.write_text(piece.read_text().replace("  test-notation: 1.0.0\n", ""))

    [finding] = checks.lock_findings(
        pl.Held(root, "visual"), pl.read_piece(root, "visual", "system")
    )

    assert (finding.code, finding.message) == (
        "lock-incomplete",
        "the lock does not name `test-notation`, which the piece uses",
    )


# --- a list a part passes on under another name -------------------------------------------------

LISTED = {"type": "array", "items": {"type": "object"}}


def passing(about: str, passed: dict[str, str], fields: dict[str, Any], use: str) -> str:
    """A local component whose part `p` places `use`, passing each of its `fields` on to
    it under the name `passed` gives it."""
    return yaml_text(
        bound(
            "component",
            status="experimental",
            about=about,
            fields={"type": "object", "properties": fields},
            parts={"p": {"use": use, "fields": passed, "width": "=:width"}},
            preferred={"height": "=p.height"},
        )
    )


def test_an_item_of_a_list_passed_on_is_read_against_the_component_that_draws_it(
    tmp_path: Path,
) -> None:
    """The flow passes its `stages` on to a frame as `rows`, which passes them on to the
    steps as `steps`. A stage drawn by the shot passes its `shots` on to the callout as
    `pictures`."""
    root = drawing_project(tmp_path)
    components = root / PIECE_FOLDER / "components"
    write(
        components / "flow.yaml",
        passing("Stages.", {"rows": "stages"}, {"stages": LISTED}, "piece/frame"),
    )
    write(
        components / "frame.yaml",
        passing("Rows.", {"steps": "rows"}, {"rows": LISTED}, "tests/steps"),
    )
    point = {"type": "object", "properties": {"item": {}, "point": {}}}
    shot = {"shots": LISTED, "says": {"type": "string"}, "at": point}
    passed = {"pictures": "shots", "label": "says", "at": "at"}
    write(components / "shot.yaml", passing("A shot.", passed, shot, "tests/callout"))
    note = {
        "id": "note",
        "use": "piece/shot",
        "shots": [{"id": "square"}, {"outptu": "square"}],
        "says": "Here",
        "at": {"item": "square", "point": "tip"},
    }
    stages = [{"id": "plan", "haed": "A"}, {"head": "B", "extar": 1}, note]
    write_content(root, body={"use": "piece/flow", "stages": stages})

    found = checks.content_findings(project_of(root))

    assert [(f.code, f.where) for f in found] == [
        ("content-key", "body.stages[plan].haed"),
        ("content-required", "body.stages[plan].head"),
        ("content-key", "body.stages#2.extar"),
        ("content-required", "body.stages[note].shots[square].output"),
        ("content-key", "body.stages[note].shots#2.outptu"),
        ("content-required", "body.stages[note].shots#2.output"),
    ]
    assert found[0].message == "`tests/card` takes no field or option `haed`; did you mean `head`?"
    assert {f.file for f in found} == {CONTENT}


# --- a library's own roles, and the versions checked alone (DEC-008 points 1 and 9) ----------

BRAND_FOLDER = "visual/libraries/test-brand/1.0.0"
PARTS_FOLDER = "visual/libraries/test-parts"
TAGS_FILE = "visual/pieces/tags/piece.yaml"

#: The test library's warning, which has no default, at the brand's ink.
WARNING = {"warning": {"$type": "color", "$value": "{scheme.ink}"}}


def add_tokens(root: Path, given: dict[str, Any]) -> None:
    """`given` under `test-parts` in the project's test brand's base tokens."""
    path = root / BRAND_FOLDER / "tokens" / "base.tokens.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["test-parts"] = given
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def name_parts(root: Path, given: dict[str, Any] | None = None) -> None:
    """The project's test brand names `test-parts` 1, and gives it `given`, by default its
    warning a value."""
    library = root / BRAND_FOLDER / "library.yaml"
    library.write_text(
        library.read_text(encoding="utf-8").replace(
            "  - {name: foundations, major: 1}\n",
            "  - {name: foundations, major: 1}\n  - {name: test-parts, major: 1}\n",
        ),
        encoding="utf-8",
    )
    add_tokens(root, WARNING if given is None else given)


def parts_minor(root: Path, roles: dict[str, str]) -> None:
    """test-parts 1.1.0 beside 1.0.0, its `roles.yaml` changed by `roles` (old: new), both
    listed unreleased."""
    folder = copy_library(root, TEST_PARTS, "test-parts", "1.1.0")
    library = folder / "library.yaml"
    library.write_text(
        library.read_text(encoding="utf-8").replace("version: 1.0.0", "version: 1.1.0"),
        encoding="utf-8",
    )
    text = (folder / "roles.yaml").read_text(encoding="utf-8")
    for old, new in roles.items():
        assert old in text
        text = text.replace(old, new)
    (folder / "roles.yaml").write_text(text, encoding="utf-8")
    unreleased = {"released": False}
    write_list(
        root,
        {
            "foundations": {"source": {"kind": "shipped"}, "versions": {"1.0.0": unreleased}},
            "test-brand": {"source": {"kind": "project"}, "versions": {"1.0.0": unreleased}},
            "test-parts": {
                "source": {"kind": "project"},
                "versions": {"1.0.0": unreleased, "1.1.0": unreleased},
            },
        },
    )


def judged(report: Any, code: str) -> list[tuple[Any, str]]:
    return [(finding, level) for finding, level in report.judged if finding.code == code]


def test_a_librarys_own_roles_are_checked_alone_their_findings_in_its_version(
    tmp_path: Path,
) -> None:
    report = checks.check(parts_project(tmp_path))
    assert not report.failed()
    [(finding, level)] = judged(report, "role-brand-only")
    assert level == "fact"
    assert checks.place(finding) == f"{PARTS_FOLDER}/1.0.0/roles.yaml#roles.test-parts.warning"
    assert finding.library == "test-parts@1.0.0"


def test_a_brands_finding_against_a_library_it_names_lies_in_its_version_once(
    tmp_path: Path,
) -> None:
    root = parts_project(tmp_path)
    name_parts(root, {})
    other = root / "visual/pieces/other"
    shutil.copytree(root / "visual/pieces/tags", other)
    report = checks.check(root)
    [(finding, level)] = judged(report, "library-role-missing")
    assert level == "fails"
    assert finding.library == "test-brand@1.0.0"
    assert (finding.where, finding.file) == ("test-parts.warning", f"{BRAND_FOLDER}/")


def test_a_brand_checked_alone_is_resolved_with_the_newest_minor_of_each_major_it_names(
    tmp_path: Path,
) -> None:
    root = parts_project(tmp_path)
    name_parts(root)
    parts_minor(
        root,
        {
            "  test-parts.warning: {type: color}\n": (
                "  test-parts.warning: {type: color}\n  test-parts.mark: {type: color}\n"
            )
        },
    )
    report = checks.check(root)
    [(finding, level)] = judged(report, "library-role-missing")
    assert (finding.library, finding.where, level) == (
        "test-brand@1.0.0",
        "test-parts.mark",
        "fails",
    )
    assert {f.library for f, _ in judged(report, "role-brand-only")} == {
        "test-parts@1.0.0",
        "test-parts@1.1.0",
    }
    assert judged(checks.check(root, only="tags"), "library-role-missing") == []


def test_a_fault_only_a_lock_shows_lies_at_that_lock_and_fails(tmp_path: Path) -> None:
    root = parts_project(tmp_path)
    name_parts(root, {})
    parts_minor(
        root,
        {
            "  test-parts.warning: {type: color}\n": (
                "  test-parts.warning: {type: color, default: '{accent}'}\n"
            )
        },
    )
    for report in (checks.check(root), checks.check(root, only="tags")):
        [(finding, level)] = judged(report, "library-role-missing")
        assert level == "fails"
        assert (finding.file, finding.where, finding.library) == (TAGS_FILE, "lock", "")
        assert finding.message.startswith(
            f"under this lock, test-brand@1.0.0 shows what it does not alone ({BRAND_FOLDER}/, "
            "`test-parts.warning`): the brand names `test-parts`"
        )


def test_a_token_under_a_library_a_piece_locks_that_the_brand_does_not_name_asks_attention(
    tmp_path: Path,
) -> None:
    root = parts_project(tmp_path)
    add_tokens(root, {"ink": {"$type": "color", "$value": "{scheme.ink}"}})
    report = checks.check(root)
    assert not report.failed()
    [(finding, level)] = judged(report, "library-token-private")
    assert level == "attention"
    assert (finding.file, finding.where, finding.library) == (TAGS_FILE, "lock", "")
    assert finding.who == "the owner of the brand test-brand"


def test_a_version_that_names_majors_no_versions_fit_cannot_be_checked_alone(
    tmp_path: Path,
) -> None:
    root = parts_project(tmp_path)
    name_parts(root)
    library = root / PARTS_FOLDER / "1.0.0" / "library.yaml"
    library.write_text(
        library.read_text(encoding="utf-8").replace(
            "{name: foundations, major: 1}", "{name: foundations, major: 2}"
        ),
        encoding="utf-8",
    )
    report = checks.check(root)
    [(majors, level)] = judged(report, "alone-majors")
    assert level == "fails"
    assert checks.place(majors) == f"{BRAND_FOLDER}/library.yaml#builds-on"
    assert "test-parts@1.0.0 builds on `foundations` 2" in majors.message
    [(missing, level)] = judged(report, "alone-missing")
    assert (level, missing.library) == ("fails", "")
    assert checks.place(missing) == "visual/libraries/libraries.yaml#libraries.test-parts"


def test_a_picture_role_a_library_other_than_the_foundations_declares_fails(
    tmp_path: Path,
) -> None:
    """Only the foundations declare a picture role (DEC-025 points 4 and 9)."""
    root = parts_project(tmp_path)
    roles = root / PARTS_FOLDER / "1.0.0" / "roles.yaml"
    roles.write_text(
        roles.read_text(encoding="utf-8").replace(
            "  test-parts.warning: {type: color}\n",
            "  test-parts.warning: {type: color}\n  test-parts.logo: {type: picture}\n",
        ),
        encoding="utf-8",
    )
    report = checks.check(root)
    assert report.failed()
    [(finding, level)] = judged(report, "role-picture")
    assert level == "fails"
    assert checks.place(finding) == f"{PARTS_FOLDER}/1.0.0/roles.yaml#roles.test-parts.logo"


def giving_a_logo(root: Path) -> Path:
    """The project's test brand gives `picture.logo` the file `logo.png`, and the path where
    that file lies."""
    path = root / BRAND_FOLDER / "tokens" / "base.tokens.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["picture"] = {"logo": {"$extensions": {"pkit.visual-communication": {"file": "logo.png"}}}}
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return root / BRAND_FOLDER / "pictures" / "logo.png"


def test_a_logo_the_brand_names_its_version_does_not_hold_fails_and_one_it_holds_passes(
    tmp_path: Path,
) -> None:
    """A brand that gives `picture.logo` a value names a file of its version's `pictures/`
    (DEC-025 point 9). Giving one, it states no fact."""
    root = parts_project(tmp_path)
    logo = giving_a_logo(root)
    report = checks.check(root)
    assert report.failed()
    [(finding, level)] = judged(report, "picture-missing")
    assert level == "fails"
    assert checks.place(finding) == f"{BRAND_FOLDER}/tokens/base.tokens.json#picture.logo"
    logo.parent.mkdir()
    shutil.copyfile(TEST_PICTURES / "palette.png", logo)
    report = checks.check(root)
    assert not report.failed()
    assert judged(report, "picture-missing") == judged(report, "picture-role-unvalued") == []


def test_a_brands_logo_of_an_encoding_refused_fails_validation_once_at_the_file(
    tmp_path: Path,
) -> None:
    """Judged by its reading, its encoding and its bytes (DEC-025 points 5 and 9), checked
    alone and under the piece's lock alike, so it is reported once, in the brand's version."""
    root = drawing_project(tmp_path, picture=False)
    logo = giving_a_logo(root)
    logo.parent.mkdir()
    shutil.copyfile(TEST_PICTURES / "deep.png", logo)
    report = checks.check(root)
    assert report.failed()
    [(finding, level)] = judged(report, "picture-encoding")
    assert level == "fails"
    assert checks.place(finding) == f"{BRAND_FOLDER}/pictures/logo.png"
    assert finding.library == "test-brand@1.0.0"
    assert finding.fix == "save it at 8 bits for each sample, not interlaced"


def test_a_brands_logo_git_ignores_fails_validation(tmp_path: Path) -> None:
    """A brand's file is found as version control lists its folder (DEC-025 point 2)."""
    root = drawing_project(tmp_path, picture=False)
    logo = giving_a_logo(root)
    logo.parent.mkdir()
    shutil.copyfile(TEST_PICTURES / "alpha.png", logo)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
    assert judged(checks.check(root), "picture-missing") == []
    (root / ".gitignore").write_text("*.png\n", encoding="utf-8")
    report = checks.check(root)
    assert report.failed()
    [(finding, level)] = judged(report, "picture-missing")
    assert level == "fails"
    assert checks.place(finding) == f"{BRAND_FOLDER}/tokens/base.tokens.json#picture.logo"
    assert finding.message.endswith("git ignores it, so no clone holds it")


# --- a part that reads a library's role with no value (DEC-008 points 8 and 9) -----------------

TAG_FILE = f"{PARTS_FOLDER}/1.0.0/components/tag.yaml"


def replaced(path: Path, changes: dict[str, str]) -> None:
    """`path`, each text of `changes` replaced by its new text."""
    text = path.read_text(encoding="utf-8")
    for old, new in changes.items():
        assert old in text
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")


def tag_reads(root: Path, spacing: str, typography: str) -> None:
    """The project's test tag places its label at the spacing role `spacing`, and sets its
    text in the typography role `typography`."""
    replaced(
        root / TAG_FILE,
        {'x: "=@test-parts.gap"': f'x: "=@{spacing}"', "style: type.body": f"style: {typography}"},
    )


def reads_unvalued(root: Path) -> None:
    """The project's test library declares a spacing and a typography with no default, and
    its tag reads both, which only a brand that names the library gives values."""
    replaced(
        root / PARTS_FOLDER / "1.0.0" / "roles.yaml",
        {
            "  test-parts.warning: {type: color}\n": (
                "  test-parts.warning: {type: color}\n"
                "  test-parts.inset: {type: dimension}\n"
                "  test-parts.type: {type: typography}\n"
            )
        },
    )
    tag_reads(root, "test-parts.inset", "test-parts.type")


def test_a_part_reading_a_library_role_with_no_value_lies_at_the_lock_that_combines_them(
    tmp_path: Path,
) -> None:
    root = parts_project(tmp_path)
    reads_unvalued(root)
    for report in (checks.check(root), checks.check(root, only="tags")):
        found = judged(report, "unknown-role")
        assert [(checks.place(f), f.library, level) for f, level in found] == [
            (f"{TAGS_FILE}#lock", "", "fails")
        ] * 2
        assert sorted(f.message for f, _ in found) == [
            f"under this lock, {part} reads `@test-parts.{role}`, a role of test-parts@1.0.0 "
            "that has no value: its chain of defaults reaches none, and the brand does not "
            "name `test-parts` to give it one"
            for part, role in (
                ("`test-parts/tag`, at `parts.label.x`,", "inset"),
                ("the text `figure/body/label` of `test-parts/tag`", "type"),
            )
        ]
        assert all("lock a brand that names `test-parts`" in f.fix for f, _ in found)


def test_a_part_reading_a_library_role_with_no_value_takes_no_finding_where_the_brand_names_it(
    tmp_path: Path,
) -> None:
    root = parts_project(tmp_path)
    reads_unvalued(root)
    name_parts(root)
    report = checks.check(root)
    assert judged(report, "unknown-role") == []
    missing = judged(report, "library-role-missing")
    assert sorted((f.where, f.library, level) for f, level in missing) == [
        ("test-parts.inset", "test-brand@1.0.0", "fails"),
        ("test-parts.type", "test-brand@1.0.0", "fails"),
    ]


def test_a_role_no_library_declares_is_still_found_in_the_component(tmp_path: Path) -> None:
    root = parts_project(tmp_path)
    tag_reads(root, "test-parts.nothing", "test-parts.none")
    found = judged(checks.check(root, only="tags"), "unknown-role")
    assert sorted((checks.place(f), f.library, level) for f, level in found) == [
        (f"{TAG_FILE}#@test-parts.nothing", "test-parts@1.0.0", "fails"),
        (f"{TAG_FILE}#figure/body/label", "test-parts@1.0.0", "fails"),
    ]


# --- a top whose layouts are its pages' forms (#2558) ------------------------------------------

#: A deck's pages in each language: a cover, and two slides, one with a picture.
SLIDES = {
    "en": [
        ("Building with AI", "The way the project decided", "Where permissions come from"),
        "In project-kit.",
    ],
    "cs": [
        ("Stavíme s AI", "Tak, jak projekt rozhodl", "Odkud se berou oprávnění"),
        "V project-kitu.",
    ],
}


STEPS = {"use": "tests/steps", "steps": [{"id": "ask", "head": "Ask"}]}


def slides(language: str) -> list[dict[str, Any]]:
    (title, subtitle, rules), footer = SLIDES[language]
    return [
        {"id": "cover", "layout": "cover", "title": title, "subtitle": subtitle, "author": "A. K."},
        {
            "id": "rules",
            "layout": "slide",
            "title": rules,
            "visual": STEPS,
            "footer": footer,
        },
        {"id": "fits", "layout": "slide", "title": "AI"},
    ]


def deck_project(tmp_path: Path, **pages: list[Any]) -> Path:
    """The foundations' deck as the piece's top, in English and Czech: `slides` in each
    language, or the language's own pages where `pages` gives them."""
    root = drawing_project(tmp_path, top="foundations/deck", picture=False, languages=["en", "cs"])
    for language in ("en", "cs"):
        given = pages.get(language, slides(language))
        write(
            root / PIECE_FOLDER / f"content.{language}.yaml",
            yaml_text(bound("content", slides=given)),
        )
    return root


def test_a_deck_of_a_cover_and_slides_in_two_languages_draws_each_page_in_its_layout(
    tmp_path: Path,
) -> None:
    project = project_of(deck_project(tmp_path))

    assert checks.content_findings(project) == []
    scenes = dict(project.scenes(facts=project.piece.stand_ins))
    assert list(scenes) == ["en", "cs"]
    for language, result in scenes.items():
        assert result.findings == [], language
        assert result.scene.pages == [
            "deck/slides[cover]",
            "deck/slides[rules]",
            "deck/slides[fits]",
        ]
        title = result.scene.find("deck/slides[cover]/title")
        assert title is not None and title.sources["text"] == "content:slides[cover].title"
    shown = [scenes[language].scene.find("deck/slides[rules]/title") for language in scenes]
    assert [element.properties["text"] for element in shown if element is not None] == [
        "Where permissions come from",
        "Odkud se berou oprávnění",
    ]


def test_each_page_is_judged_against_its_layout_or_the_component_it_names(
    tmp_path: Path,
) -> None:
    pages = [
        {"id": "a", "title": "A"},
        {"id": "b", "layout": "slied", "title": "B"},
        {"id": "c", "layout": "slide", "titel": "C"},
        {"id": "d", "layout": "cover", "title": "D", "lead": "Not on a cover."},
        {"id": "e", "layout": "slide", "title": 5},
        {
            "id": "f",
            "use": "foundations/figure",
            "layout": "slide",
            "body": STEPS,
        },
        "A page.",
    ]
    root = deck_project(tmp_path, en=pages, cs=pages)

    found = [f for f in checks.content_findings(project_of(root)) if f.file == CONTENT]

    assert [(f.code, f.where, f.message) for f in found] == [
        (
            "content-layout",
            "slides[a]",
            "the page names neither a layout of `foundations/deck` with `layout` (cover, "
            "slide) nor a component with `use`",
        ),
        (
            "content-layout",
            "slides[b].layout",
            "`foundations/deck` has no layout `slied` (cover, slide); did you mean `slide`?",
        ),
        (
            "content-key",
            "slides[c].titel",
            "the layout `slide` of `foundations/deck` takes no slot `titel`; did you mean `title`?",
        ),
        ("content-required", "slides[c].title", "the field `title` is required"),
        (
            "content-key",
            "slides[d].lead",
            "the layout `cover` of `foundations/deck` takes no slot `lead`",
        ),
        ("content-type", "slides[e].title", "the field holds an integer, not string"),
        (
            "content-key",
            "slides[f].layout",
            "`foundations/figure` takes no field or option `layout`",
        ),
        ("content-type", "slides#7", "the page holds a string, not object"),
    ]


def test_a_page_carries_its_layout_the_reserved_keys_and_its_slots_alone(
    tmp_path: Path,
) -> None:
    """A field of the deck is no slot of a page, and `layout` is the page's own key."""
    pages = [{"id": "a", "layout": "slide", "title": "A", "state": "done", "slides": []}]
    root = deck_project(tmp_path, en=pages, cs=pages)

    found = [f for f in checks.content_findings(project_of(root)) if f.file == CONTENT]

    assert [(f.code, f.where) for f in found] == [("content-key", "slides[a].slides")]


# --- a list's component field and arrangement fields (#2560) ---------------------------------

LOCAL = f"{PIECE_FOLDER}/components"

#: A weight of two words, whose shares are one and two.
SIZE = {"words": ["one", "two"], "shares": {"one": 1, "two": 2}}


def local(**fields: Any) -> str:
    """A local component of `fields`, as its file holds it."""
    return yaml_text(bound("component", status="experimental", **fields))


def row(**lists: Any) -> str:
    """A pattern that draws its list `items` in a row shared by the weight `size`, each
    item drawn by the steps' card by default; `kind` is the list's component field, unless
    `lists` gives other fields."""
    return local(
        about="A row of items.",
        fields={"type": "object", "properties": {"items": LISTED, "kind": {"type": "object"}}},
        lists=lists or {"items": {"component": "kind", "arrangement": {"size": SIZE}}},
        parts={
            "items": {
                "repeat": "items",
                "draw": "tests/card",
                "width": "=:width",
                "row": {"gap": "=@space.2", "sizes": "shares", "align-items": "stretch"},
            }
        },
        preferred={"height": "=items.height"},
    )


#: A block that shows its `head`, and declares `size` as a field and `tone` as an option.
SIZED = local(
    about="A head, and the size it says.",
    fields={
        "type": "object",
        "required": ["head"],
        "properties": {"head": {"type": "string"}, "size": {"type": "string"}},
    },
    options={"tone": ["plain", "loud"]},
    parts={
        "head": {
            "text": {"content": "head", "style": "type.body", "fill": "text-primary"},
            "width": "=:width",
        }
    },
    preferred={"height": "=head.bottom"},
)


def row_project(tmp_path: Path, row_text: str | None = None, **body: Any) -> Path:
    """The drawing project with no picture, whose body is the local `piece/row` (`row()`
    unless `row_text` gives it) with `body`, beside the local `piece/sized`."""
    root = drawing_project(tmp_path, picture=False)
    write(root / LOCAL / "row.yaml", row_text or row())
    write(root / LOCAL / "sized.yaml", SIZED)
    write_content(root, body={"use": "piece/row", **body})
    return root


def test_a_list_drawn_by_its_component_field_and_shared_by_weights_fails_nothing(
    tmp_path: Path,
) -> None:
    """Two items take `piece/sized` from the field, and one names the card; the sized
    block declares `size`, which no item it draws carries, so that is a fact."""
    root = row_project(
        tmp_path,
        kind={"use": "piece/sized", "tone": "loud"},
        items=[
            {"id": "a", "head": "A"},
            {"id": "b", "head": "B", "tone": "plain"},
            {"id": "c", "use": "tests/card", "head": "C", "size": "two"},
        ],
    )

    report = checks.check(root, only=PIECE)

    assert not report.failed()
    assert {f.code for f, _ in report.judged} == {"component-experimental", "list-clash"}


def test_content_is_judged_against_a_lists_component_field_and_arrangement_fields(
    tmp_path: Path,
) -> None:
    root = row_project(
        tmp_path,
        kind={"use": "tests/card", "id": "k", "head": "H", "tone": "loud"},
        items=[
            {"id": "a", "head": "A", "size": "three"},
            {"id": "b", "head": "B", "sise": "one"},
            {"id": "c"},
        ],
    )

    found = checks.content_findings(project_of(root))

    assert [(f.code, f.where, f.message) for f in found] == [
        (
            "content-component",
            "body.kind.id",
            "the component field of the list `body.items` gives an id: it names the "
            "component of every item, and an id names one thing",
        ),
        (
            "content-component",
            "body.kind.head",
            "the component field of the list `body.items` gives `head`, a field of "
            "`tests/card`: a field holds what one item shows, so each item gives its own",
        ),
        ("content-key", "body.kind.tone", "`tests/card` takes no option `tone`"),
        (
            "content-option",
            "body.items[a].size",
            "`three` is no word of the arrangement field `size` of the list `body.items` "
            "(one, two)",
        ),
        (
            "content-key",
            "body.items[b].sise",
            "neither `tests/card` nor the list `body.items` declares a key `sise`; did you "
            "mean `size`?",
        ),
        ("content-required", "body.items[c].head", "the field `head` is required"),
    ]
    assert {f.file for f in found} == {CONTENT}


def test_a_component_field_that_names_no_component_fails_and_its_items_take_the_default(
    tmp_path: Path,
) -> None:
    root = row_project(
        tmp_path,
        kind={"tone": "loud"},
        items=[{"id": "a", "head": "A", "tone": "loud"}],
    )

    found = checks.content_findings(project_of(root))

    assert [(f.code, f.where) for f in found] == [
        ("content-component", "body.kind"),
        ("content-key", "body.items[a].tone"),
    ]
    assert found[0].message == (
        "the component field of the list `body.items` names no component: it takes "
        "`{use: <library>/<component>}`, with words for that component's options"
    )


def test_a_key_both_an_items_component_and_its_list_declare_lies_at_the_lock(
    tmp_path: Path,
) -> None:
    carried = row_project(
        tmp_path,
        kind={"use": "piece/sized"},
        items=[{"id": "a", "head": "A", "size": "two"}, {"id": "b", "head": "B"}],
    )
    free = row_project(tmp_path / "free", items=[{"id": "a", "use": "piece/sized", "head": "A"}])

    [item] = checks.content_findings(project_of(carried))
    [listed] = checks.content_findings(project_of(free))

    assert (item.code, item.level, checks.place(item)) == (
        "item-clash",
        "fails",
        f"{PIECE_FILE}#lock",
    )
    assert item.message == (
        "under this lock, `piece/sized` and the list `body.items` both declare `size`, "
        "which the item `body.items[a]` carries in content.en.yaml: neither reads it, "
        "so `piece/sized` leaves it unfilled, and the arrangement field takes its default "
        "`one`"
    )
    assert (listed.code, listed.level, checks.place(listed)) == (
        "list-clash",
        "fact",
        f"{PIECE_FILE}#lock",
    )
    assert listed.message == (
        "under this lock, `piece/sized` and the list `body.items` both declare `size`: "
        "neither would read it on an item of the list that `piece/sized` draws"
    )


def test_a_clash_at_the_lock_is_said_once_across_the_pieces_languages(tmp_path: Path) -> None:
    root = row_project(tmp_path, items=[{"id": "a", "use": "piece/sized", "head": "A"}])
    piece = root / PIECE_FILE
    piece.write_text(
        piece.read_text(encoding="utf-8").replace("- en\n", "- en\n  - cs\n"), encoding="utf-8"
    )
    carried = [{"id": "a", "use": "piece/sized", "head": "A", "size": "one"}]
    write_content(root, "cs", body={"use": "piece/row", "items": carried})

    found = checks.content_findings(project_of(root))

    assert [(f.code, f.level) for f in found] == [("item-clash", "fails")]


def test_what_a_pattern_declares_for_its_lists_fails_in_its_file(tmp_path: Path) -> None:
    lists = {"other": {"component": "kind"}, "items": {"arrangement": {"size": {"words": []}}}}
    root = row_project(tmp_path, row_text=row(**lists), items=[{"id": "a", "head": "A"}])

    report = checks.check(root, only=PIECE)

    shapes = [(checks.place(f), level) for f, level in report.judged if f.code == "component-shape"]
    assert shapes == [
        (f"{LOCAL}/row.yaml#lists.items.arrangement.size.words", "fails"),
        (f"{LOCAL}/row.yaml#lists.other", "fails"),
        (f"{LOCAL}/row.yaml#parts.items.row.sizes", "fails"),
    ]


ROWS = {
    "about": "Tags in a row.",
    "fields": {"type": "object", "properties": {"tags": LISTED}},
    "lists": {"tags": {"arrangement": {"label": {"words": ["short", "long"]}}}},
    "parts": {"tags": {"repeat": "tags", "draw": "test-parts/tag", "row": {}}},
}


def test_a_pattern_whose_newest_version_clashes_with_its_default_fails_checked_alone(
    tmp_path: Path,
) -> None:
    """The tag that draws the pattern's items declares `label` as a field."""
    root = parts_project(tmp_path)
    parts_minor(root, {})
    write(root / PARTS_FOLDER / "1.1.0" / "components" / "rows.yaml", local(**ROWS))

    report = checks.check(root)

    [(clash, level)] = judged(report, "arrangement-clash")
    assert (level, clash.library) == ("fails", "test-parts@1.1.0")
    assert checks.place(clash) == (
        f"{PARTS_FOLDER}/1.1.0/components/rows.yaml#lists.tags.arrangement.label"
    )
    assert clash.message == (
        "`label` is an arrangement field of `tags`, and `test-parts/tag`, which draws its "
        "items by default, declares it as a field: neither reads it on an item"
    )
    assert clash.fix == (
        "rename the arrangement field, or draw the list with another component, in a "
        "version of its own"
    )


# --- ties (DEC-011) -----------------------------------------------------------------------------

#: A pattern of cards, a slot and groups, which ties them with `piece/arrow` from `from` to
#: `to`; `kind` is its list of ties' component field, and `hidden` a list it draws only
#: where `shown` is given.
NET = local(
    about="Cards tied to each other.",
    fields={
        "type": "object",
        "properties": {
            "cards": LISTED,
            "side": {"type": "object"},
            "groups": LISTED,
            "hidden": LISTED,
            "shown": {"type": "string"},
            "kind": {"type": "object"},
            "links": LISTED,
        },
    },
    lists={"links": {"component": "kind", "ends": ["from", "to"]}},
    parts={
        "cards": {
            "repeat": "cards",
            "draw": "tests/card",
            "width": "=@space.4 * 4",
            "column": {"align-items": "stretch"},
        },
        "side": {"slot": "side", "x": "=@space.4 * 5", "width": "=@space.4 * 4"},
        "groups": {
            "repeat": "groups",
            "draw": "piece/column",
            "x": "=@space.4 * 10",
            "width": "=@space.4 * 4",
            "row": {"sizes": "equal"},
        },
        "hidden": {
            "repeat": "hidden",
            "draw": "tests/card",
            "when": "shown",
            "width": "=@space.4 * 4",
            "column": {"align-items": "stretch"},
        },
        "links": {"repeat": "links", "draw": "piece/arrow"},
    },
    preferred={"height": "=@space.4 * 6"},
)

#: Cards in a column, as wide as it is given.
COLUMN = local(
    about="Cards in a column.",
    fields={"type": "object", "properties": {"items": LISTED}},
    parts={
        "items": {
            "repeat": "items",
            "draw": "tests/card",
            "width": "=:width",
            "column": {"align-items": "stretch"},
        }
    },
    preferred={"height": "=items.height"},
)

#: A component that takes ends, and draws an arrow with corners between them.
ARROW = local(
    about="An arrow between two items.",
    ends=True,
    parts={"l": {"line": {"stroke": "line", "marker-end": "arrow"}, "connect": "corners"}},
)


def tie(key: str, start: Any, end: Any, **more: Any) -> dict[str, Any]:
    return {"id": key, "from": start, "to": end, **more}


def at(path: str, **more: Any) -> dict[str, Any]:
    return {"item": path, **more}


def net_project(tmp_path: Path, *links: dict[str, Any], **body: Any) -> Path:
    """The drawing project with no picture, whose body is `piece/net` with two cards, a
    column in its slot, a group of one card and `links`, and `body`."""
    root = drawing_project(tmp_path, picture=False)
    write(root / LOCAL / "net.yaml", NET)
    write(root / LOCAL / "column.yaml", COLUMN)
    write(root / LOCAL / "arrow.yaml", ARROW)
    given = {
        "use": "piece/net",
        "cards": [{"id": "a", "head": "A"}, {"id": "b", "head": "B"}],
        "side": {"use": "piece/column", "items": [{"id": "x", "head": "X"}]},
        "groups": [{"id": "g", "items": [{"id": "w", "head": "W"}]}],
        "hidden": [{"id": "h", "head": "H"}],
        "links": list(links),
        **body,
    }
    write_content(root, body=given)
    return root


def test_ties_into_the_patterns_lists_a_slot_and_a_list_a_component_draws_fail_nothing(
    tmp_path: Path,
) -> None:
    root = net_project(
        tmp_path,
        tie("ab", at("cards[a]"), at("cards[b]")),
        tie("ax", at("cards[a]"), at("side.items[x]")),
        tie("bw", at("cards[b]"), at("groups[g].items[w]")),
    )

    report = checks.check(root, only=PIECE)

    assert not report.failed()
    assert {f.code for f, _ in report.judged} == {"component-experimental"}


def test_a_ties_component_shape_and_key_paths_are_judged_in_the_content(tmp_path: Path) -> None:
    root = net_project(
        tmp_path,
        tie("t1", at("cards[a]"), at("cards[b]"), use="piece/column"),
        tie("t2", "cards[a]", at("cards[b]", via="x")),
        {"id": "t3", "to": at("cards[b]")},
        tie("t4", at("cards[z]"), at("cardz[a]")),
        tie("t5", at("cards"), at("side[x]")),
        tie("t6", at("links[t1]"), at("cards[a]")),
        tie("t7", at("cards[a]"), at("cards[a]")),
        tie("t8", at("groups[g]"), at("groups[g].items[w]")),
        tie("t9", at("cards[a]", point="Tip"), at("cards[a]..head")),
        tie("t10", at("cards[a].head[x]"), at("side"), via="x"),
    )

    found = checks.content_findings(project_of(root))

    assert sorted((f.code, f.where) for f in found) == [
        ("content-key", "body.links[t10].via"),
        ("tie-component", "body.links[t1]"),
        ("tie-ends", "body.links[t6].from.item"),
        ("tie-ends", "body.links[t7]"),
        ("tie-ends", "body.links[t8]"),
        ("tie-path", "body.links[t10].from.item"),
        ("tie-path", "body.links[t10].to.item"),
        ("tie-path", "body.links[t4].from.item"),
        ("tie-path", "body.links[t4].to.item"),
        ("tie-path", "body.links[t5].from.item"),
        ("tie-path", "body.links[t5].to.item"),
        ("tie-path", "body.links[t9].to.item"),
        ("tie-shape", "body.links[t2].from"),
        ("tie-shape", "body.links[t2].to"),
        ("tie-shape", "body.links[t3].from"),
        ("tie-shape", "body.links[t9].from"),
    ]
    said = {(f.code, f.where): f.message for f in found}
    assert said[("tie-component", "body.links[t1]")] == (
        "`piece/column` takes no ends, and draws a tie of `body`: every item of a list of "
        "ties is a tie"
    )
    assert said[("tie-shape", "body.links[t3].from")] == (
        "the end field `from` gives nothing: an end takes `{item: <key path>}`, with "
        "`point: <name>` where it ends at a point"
    )
    assert said[("tie-path", "body.links[t4].from.item")] == (
        "`cards[z]` names `[z]`, which the list `cards` does not hold"
    )
    assert said[("tie-path", "body.links[t4].to.item")] == (
        "`cardz[a]` names `cardz`, which no component on the way declares; did you mean `cards`?"
    )
    assert said[("tie-path", "body.links[t5].from.item")] == (
        "`cards` steps into the list `cards` with no id: name its item as `[<id>]`"
    )
    assert said[("tie-path", "body.links[t5].to.item")] == (
        "`side[x]` names the item `[x]` of `side`, which is no list"
    )
    assert said[("tie-path", "body.links[t10].to.item")] == (
        "`side` ends at `side`, which is no item of a list"
    )
    assert said[("tie-ends", "body.links[t6].from.item")] == (
        "`links[t1]` names a tie: a tie joins two items, never a line"
    )
    assert said[("tie-ends", "body.links[t7]")] == (
        "one of the tie's ends names one item: `cards[a]` and `cards[a]`; a tie joins two "
        "items, neither inside the other"
    )
    assert "leads through the other" in said[("tie-ends", "body.links[t8]")]
    assert {f.file for f in found} == {CONTENT}


def test_a_ties_component_its_list_names_takes_ends_and_an_end_field_it_declares_clashes(
    tmp_path: Path,
) -> None:
    """The component field names the column, which takes no ends; then an arrow that
    declares `to` as a field, which neither reads at the lock."""
    root = net_project(
        tmp_path, tie("ab", at("cards[a]"), at("cards[b]")), kind={"use": "piece/column"}
    )

    [found] = checks.content_findings(project_of(root))

    assert (found.code, found.where) == ("tie-component", "body.links[ab]")

    claiming = local(
        about="An arrow that takes a field `to`.",
        ends=True,
        fields={"type": "object", "properties": {"to": {"type": "object"}}},
        parts={"l": {"line": {"stroke": "line"}, "connect": "straight"}},
    )
    write(root / LOCAL / "claiming.yaml", claiming)
    write_content(
        root,
        body={
            "use": "piece/net",
            "cards": [{"id": "a", "head": "A"}, {"id": "b", "head": "B"}],
            "links": [tie("ab", at("cards[a]"), at("cards[b]"), use="piece/claiming")],
        },
    )

    [clash] = checks.content_findings(project_of(root))

    assert (clash.code, checks.place(clash)) == ("item-clash", f"{PIECE_FILE}#lock")
    assert clash.message.endswith("leaves it unfilled, and the tie lacks that end, and is left out")


def test_an_end_drawn_nowhere_is_reported_in_the_content_at_its_tie(tmp_path: Path) -> None:
    root = net_project(
        tmp_path,
        tie("ab", at("cards[a]"), at("cards[b]")),
        tie("ah", at("cards[a]"), at("hidden[h]")),
    )

    report = checks.check(root, only=PIECE)

    assert report.failed()
    [(lost, level)] = judged(report, "end-not-found")
    assert (level, checks.place(lost)) == ("fails", f"{CONTENT}#body.links[ah].to")
    assert lost.message == (
        "figure/body/links[ah]: the end `hidden[h]` is drawn nowhere below "
        "`figure/body`, and an end is found only once"
    )
    assert lost.fix == (
        "name an item drawn once on the tie's page, or change the content's options; or "
        "move the lock to versions under which the end is found"
    )


#: A pattern of the test library that ties its tags, which take no ends and declare `label`.
NETS = {
    "about": "Tags tied to each other.",
    "fields": {"type": "object", "properties": {"tags": LISTED, "links": LISTED}},
    "lists": {"links": {"ends": ["label", "to"]}},
    "parts": {
        "tags": {"repeat": "tags", "draw": "test-parts/tag", "row": {}},
        "links": {"repeat": "links", "draw": "test-parts/tag"},
    },
}

#: A deck of the test library whose one layout ties its tags with its tags.
BOARD = {
    "about": "A deck whose pages tie their tags.",
    "fields": {
        "type": "object",
        "properties": {"pages": {**LISTED, "x-pkit-pages": True}},
    },
    "layouts": {
        "board": {
            "slots": {"tags": LISTED, "links": LISTED},
            "lists": {"links": {"ends": ["from", "to"]}},
            "parts": {
                "tags": {"repeat": "tags", "draw": "test-parts/tag", "row": {}},
                "links": {"repeat": "links", "draw": "test-parts/tag"},
            },
        }
    },
    "preferred": {"width": "=@space.4 * 10", "height": "=@space.4 * 5"},
}


def test_a_list_of_ties_whose_default_takes_no_ends_fails_checked_alone(tmp_path: Path) -> None:
    root = parts_project(tmp_path)
    parts_minor(root, {})
    components = root / PARTS_FOLDER / "1.1.0" / "components"
    write(components / "nets.yaml", local(**NETS))
    write(components / "board.yaml", local(**BOARD))

    report = checks.check(root)

    defaults = sorted(checks.place(f) for f, _ in judged(report, "tie-default"))
    assert defaults == [
        f"{PARTS_FOLDER}/1.1.0/components/board.yaml#layouts.board.parts.links.draw",
        f"{PARTS_FOLDER}/1.1.0/components/nets.yaml#parts.links.draw",
    ]
    [(clash, level)] = judged(report, "end-clash")
    assert (level, clash.library) == ("fails", "test-parts@1.1.0")
    assert checks.place(clash) == f"{PARTS_FOLDER}/1.1.0/components/nets.yaml#lists.links.ends"
    assert clash.message == (
        "`label` is an end field of `links`, and `test-parts/tag`, which draws its ties by "
        "default, declares it as a field: neither reads it, so no tie it draws has that end"
    )


# --- a field of runs (DEC-012) ----------------------------------------------------------------

#: A local component whose `say` takes runs in two styles, and whose `note` takes text.
SAID = bound(
    "component",
    status="experimental",
    about="A said line.",
    fields={
        "type": "object",
        "properties": {
            "say": {"type": "string", "x-pkit-runs": ["plain", "strong"]},
            "note": {"type": "string"},
        },
    },
    parts={
        "say": {
            "text": {
                "content": "say",
                "style": {"by": "say", "plain": "type.body", "strong": "type.heading"},
            },
            "width": "=:width",
        }
    },
)


def said_project(tmp_path: Path, **languages: Any) -> Path:
    """The drawing project with the piece's component `said`, its body placing it with
    each language's fields."""
    root = drawing_project(tmp_path, languages=list(languages))
    write(root / PIECE_FOLDER / "components" / "said.yaml", yaml_text(SAID))
    for language, fields in languages.items():
        write_content(root, language, body={"use": "piece/said", **fields})
    return root


def test_a_list_of_runs_is_read_against_the_run_styles_of_its_field(tmp_path: Path) -> None:
    runs = [
        "Plain text, ",
        3,
        {"text": "a", "stlye": "strong"},
        {"style": "strong"},
        {"text": ["b"]},
        {"text": "c", "style": "strnog"},
        {"text": "d", "style": "strong", "concept": "flow/queue"},
    ]
    root = said_project(tmp_path, en={"say": runs, "note": ["a list"]})

    found = checks.content_findings(project_of(root))

    assert [(f.code, f.where, f.message) for f in found] == [
        (
            "run-shape",
            "body.say#2",
            "the run holds an integer, not text or a mapping of `text`, `style` and `concept`",
        ),
        (
            "run-key",
            "body.say#3.stlye",
            "a run takes no key `stlye`, only `text`, `style` and `concept`; did you mean `style`?",
        ),
        ("run-shape", "body.say#4", "the run holds no `text`"),
        ("run-shape", "body.say#5.text", "the run holds an array in `text`, not text"),
        (
            "run-style",
            "body.say#6.style",
            "`strnog` is no run style of the field (plain, strong); did you mean `strong`?",
        ),
        (
            "runs-unmarked",
            "body.note",
            "the field holds a list, and takes text: only a field its component marks "
            "`x-pkit-runs` takes a list of runs",
        ),
    ]
    assert {f.file for f in found} == {CONTENT}


def test_a_field_of_runs_given_text_or_well_formed_runs_has_no_finding(tmp_path: Path) -> None:
    runs = ["Plain, ", {"text": "strong", "style": "strong"}, {"text": " and plain"}]
    root = said_project(tmp_path, en={"say": runs}, cs={"say": "Prostý text"})

    assert checks.content_findings(project_of(root)) == []


def test_the_check_of_ids_skips_a_list_of_runs(tmp_path: Path) -> None:
    """A run carries no id, and a field's runs may differ between languages, so a list of
    runs takes neither the id rules nor their comparison across languages; a stray `id`
    on a run is a key the format does not fix on it."""
    en = {"say": ["A ", {"text": "b", "style": "strong", "id": "yes"}]}
    root = said_project(tmp_path, en=en, cs={"say": [{"text": "B", "id": "b"}, "a", "c"]})

    assert checks.id_findings(piece_of(root)) == []
    found = checks.content_findings(project_of(root))
    assert [(f.code, f.file, f.where) for f in found] == [
        ("run-key", CONTENT, "body.say#2.id"),
        ("run-key", f"{PIECE_FOLDER}/content.cs.yaml", "body.say#1.id"),
    ]


def test_each_run_is_measured_against_the_fill_under_it_in_its_own_paint() -> None:
    scene = page(
        box("figure/back", "paper"),
        box("figure/dark", "ink", x=40, width=40),
        runs("figure/said", [run("ink"), run("ink"), run("paper", size=24), run("ink")]),
    )

    found = checks.drawn_contrast(scene, COLOURS, KEYS)

    # The second run lies on the ink box, the third on the paper in the paper's own colour;
    # the first and the last, ink on paper, pass.
    assert [f.message.split(" has ")[0] + " " + f.message.split("(")[-1] for f in found] == [
        "`ink` on `ink` `text`)",
        "`ink` on `ink` `text`)",
        "`paper` on `paper` `large-text`)",
        "`paper` on `paper` `large-text`)",
    ]
    assert {f.where for f in found} == {"figure/said"}


# --- a copy of a library the capability ships (DEC-013 point 6) --------------------------------

#: Who a finding in a copy of the library `line`, listed from the source `shipped`, names.
MAINTAINER = "whoever maintains the capability, who corrects `line` where it is authored"


@pytest.mark.parametrize("released", [False, True], ids=["not-released", "released"])
def test_a_failing_finding_in_a_shipped_copy_asks_whoever_maintains_the_capability(
    tmp_path: Path, released: bool
) -> None:
    root = drawing_project(tmp_path, picture=False)
    root = held_as(root, "line", released=released, source="shipped")
    report = checks.check(root)
    [(finding, level)] = [(f, level) for f, level in report.judged if f.code == "library-name"]
    assert (level, finding.who) == ("attention", MAINTAINER)
    assert checks.said(finding) == (
        f"`line` is a top group of the shared roles, so no library takes it — for {MAINTAINER} "
        f"— rename the library, in a version of its own, and lock that version"
    )


def test_a_failing_finding_in_a_shipped_copy_that_changed_since_its_release_fails(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path, picture=False)
    root = held_as(root, "line", released=True, source="shipped")
    write(root / "visual/libraries/line/1.0.0/notes.txt", "Added after the release.\n")
    report = checks.check(root)
    levels = {f.code: (level, f.who) for f, level in report.judged}
    assert levels["library-changed"] == ("fails", "")
    assert levels["library-name"] == ("fails", "")


def test_a_finding_lowered_in_a_shipped_copy_names_its_maintainer_and_is_never_stored() -> None:
    finding = findings_.Finding("text-overflow", "fails", "too wide", library="line@1.0.0")
    for released in (False, True):
        lowered, level = findings_.as_read(finding, released, shipped=True)
        assert (level, lowered.who) == ("attention", MAINTAINER)
    assert finding.who == "" and finding.level == "fails"
    unversioned = findings_.Finding("lock-missing", "fails", "no lock")
    assert findings_.as_read(unversioned, False, shipped=True) == (unversioned, "fails")
