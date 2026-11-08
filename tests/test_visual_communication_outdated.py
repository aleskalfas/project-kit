"""`pkit visual outdated` (visual-communication DEC-019 points 8 and 11): each lock a person
moves, a published piece's, a pinned draft's and written code's, with the newest version that
fits within its major and each other newer version with why; an unpinned draft and a final
piece left out; a version not yet released; a later major; a clash and a lost end, which the
check's fact names still; a version the installed capability cannot read; a lock it cannot
judge; none behind; and nothing written. Run in this process, the SVG renderer standing in for
the import an export makes when it draws."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tests import visual_communication_producer as producer
from tests.in_process import load, run_main
from tests.test_visual_communication_pipeline import (
    BLOCKS,
    LOCK,
    NET,
    PATTERNS,
    PIECE,
    PIECE_FOLDER,
    ROW,
    changed_tests,
    drawing_project,
    every_file,
    lab_lock,
    lab_project,
    list_drawing_libraries,
    released_entry,
)
from tests.test_visual_communication_render import CLASH, LOST
from tests.visual_communication_project import (
    CONFIG,
    bound,
    capability_version,
    importable,
    write,
    write_list,
    yaml_text,
)

script, check_script, export_script, svg, seam, reading = load(
    "visual-communication",
    "outdated.py",
    "check.py",
    "export.py",
    "plugins.svg",
    "plugins.seam",
    "reading",
)

PIECE_FILE = f"{PIECE_FOLDER}/piece.yaml"
LIST = "visual/libraries/libraries.yaml"
DECLARATION = "visual/code/css.yaml"

#: What the run says of the published piece `flow`, and of the pinned draft `flow`.
PUBLISHED = (
    f"the published piece `{PIECE}`, in {PIECE_FILE}: `pkit visual upgrade {PIECE}` proposes a "
    "move within its majors, and a later major where you name it"
)
PINNED = (
    f"the pinned draft `{PIECE}`, in {PIECE_FILE}: a hand moves its lock, or a render once it "
    "is unpinned"
)
LATER = "    tests@2.0.0: it is of major 2, and the move stays within major 1"
NOTHING_NEWER = "  tests 1.0.0: no newer version fits within major 1"


@pytest.fixture(autouse=True)
def plugins(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The renderer stands in for the import an export makes when it draws, and the test
    producer is registered, for the length of the test."""
    importable(monkeypatch, svg)
    producer.register(seam)
    yield
    seam.unregister(producer.NAME)


def run(root: Path) -> subprocess.CompletedProcess[str]:
    return run_main(script, cwd=root)


def lines(root: Path) -> list[str]:
    """What a run prints, a line each, having changed no file."""
    before = every_file(root)
    shown = run(root)
    assert shown.returncode == 0, shown.stderr
    assert every_file(root) == before
    return shown.stdout.splitlines()


def behind_facts(root: Path) -> list[str]:
    """The message of each fact the check states that a lock is behind, with its fix."""
    shown = run_main(check_script, "--json", cwd=root, env={"PKIT_COMMAND_DEADLINE": None})
    assert shown.returncode == 0, shown.stderr
    found = json.loads(shown.stdout)["findings"]
    return [each["message"] for each in found if each["label"] == "lock-behind"]


def published(tmp_path: Path, **fields: Any) -> Path:
    """The skeleton piece, published and exported once, under a lock of released versions."""
    root = drawing_project(tmp_path, state="published", picture=False, **fields)
    done = run_main(export_script, PIECE, cwd=root)
    assert done.returncode == 0, done.stderr
    return root


def newer(root: Path, version: str, *, released: bool = True, needs: str = "") -> None:
    """The `tests` library at `version` too, every version listed released with its hash, but
    `version` where `released` is false; `needs` is the release it needs, where given."""
    folder = changed_tests(root / "visual/libraries/tests" / version, version)
    if needs:
        library = folder / "library.yaml"
        text = library.read_text(encoding="utf-8")
        library.write_text(text.replace("needs-release: 0.1.0", f"needs-release: {needs}"))
    list_drawing_libraries(root, released=True)
    if not released:
        data = reading.read_yaml(root / LIST)
        data["libraries"]["tests"]["versions"][version] = {"released": False}
        write(root / LIST, yaml_text(data))


def released_lab(root: Path) -> Path:
    """Each version a lab project holds, listed released with its hash."""
    listed = reading.read_yaml(root / LIST)["libraries"]
    for name, library in listed.items():
        folder = root / "visual" / "libraries" / name
        library["versions"] = {
            version: released_entry(folder / version, name) for version in library["versions"]
        }
    write_list(root, listed)
    return root


def declare(root: Path, lock: dict[str, str]) -> None:
    """The declaration `css` of written code, under `lock`."""
    declaration = bound(
        "code", writer="css", form=1, brand="test-brand", lock=lock, out="docs/brand.css"
    )
    write(root / DECLARATION, yaml_text(declaration))


# --- a lock behind, and one at the newest -------------------------------------------------------


def test_a_published_piece_behind_names_the_newest_that_fits_and_what_moves_it(
    tmp_path: Path,
) -> None:
    root = published(tmp_path)
    newer(root, "1.1.0")
    assert lines(root) == [
        "behind: 1 of 1 lock a person moves",
        PUBLISHED,
        "  tests 1.0.0: 1.1.0 is the newest released version that fits within major 1",
    ]


def test_a_lock_at_the_newest_is_behind_nothing_and_it_says_so(tmp_path: Path) -> None:
    root = published(tmp_path)
    assert lines(root) == ["behind: none, of 1 lock a person moves"]


def test_with_no_visual_work_it_says_so(tmp_path: Path) -> None:
    root = tmp_path / "project"
    (root / ".pkit" / "capabilities" / "visual-communication").mkdir(parents=True)
    assert lines(root) == [
        f"No visual work: {CONFIG} records no location, and `visual/` holds none."
    ]


# --- each kind of lock --------------------------------------------------------------------------


def test_a_pinned_drafts_lock_is_judged_among_every_version(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False, pinned=True)
    newer(root, "1.1.0", released=False)
    assert lines(root) == [
        "behind: 1 of 1 lock a person moves",
        PINNED,
        "  tests 1.0.0: 1.1.0 is the newest version that fits within major 1",
    ]


def test_written_codes_lock_is_judged_by_its_lock_alone(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    declare(root, LOCK)
    newer(root, "1.1.0")
    newer(root, "2.0.0")
    assert lines(root) == [
        "behind: 1 of 1 lock a person moves",
        f"the declaration `css` of written code, in {DECLARATION}: a hand moves its lock, then "
        "`pkit visual write-code css` writes the code",
        "  tests 1.0.0: 1.1.0 is the newest version that fits within major 1",
        LATER,
    ]


def test_each_kind_is_listed_where_a_project_holds_all_three(tmp_path: Path) -> None:
    root = published(tmp_path)
    write(
        root / "visual/pieces/copy/piece.yaml",
        (root / PIECE_FILE)
        .read_text(encoding="utf-8")
        .replace("state: published", "state: draft\npinned: true"),
    )
    write(
        root / "visual/pieces/copy/content.en.yaml",
        (root / PIECE_FOLDER / "content.en.yaml").read_text(encoding="utf-8"),
    )
    declare(root, LOCK)
    newer(root, "1.1.0")
    said = lines(root)
    assert said[0] == "behind: 3 of 3 locks a person moves"
    assert [line for line in said if not line.startswith(" ")][1:] == [
        "the pinned draft `copy`, in visual/pieces/copy/piece.yaml: a hand moves its lock, or a "
        "render once it is unpinned",
        PUBLISHED,
        f"the declaration `css` of written code, in {DECLARATION}: a hand moves its lock, then "
        "`pkit visual write-code css` writes the code",
    ]


@pytest.mark.parametrize(
    "fields",
    [
        pytest.param({}, id="unpinned-draft"),
        pytest.param({"state": "final"}, id="final"),
        pytest.param({"state": "final", "pinned": True}, id="final-pinned"),
    ],
)
def test_an_unpinned_draft_and_a_final_piece_behind_are_left_out(
    tmp_path: Path, fields: dict[str, Any]
) -> None:
    root = drawing_project(tmp_path, picture=False, **fields)
    newer(root, "1.1.0")
    newer(root, "2.0.0")
    assert lines(root) == ["behind: none, of 0 locks a person moves"]
    assert behind_facts(root) == []


# --- what holds a newer version back ------------------------------------------------------------


def test_a_version_not_yet_released_puts_no_published_lock_behind(tmp_path: Path) -> None:
    root = published(tmp_path)
    newer(root, "1.1.0", released=False)
    assert lines(root) == ["behind: none, of 1 lock a person moves"]
    assert behind_facts(root) == []


def test_a_later_major_is_named_with_why_a_move_stays_within_the_locks(tmp_path: Path) -> None:
    root = published(tmp_path)
    newer(root, "2.0.0")
    assert lines(root) == ["behind: 1 of 1 lock a person moves", PUBLISHED, NOTHING_NEWER, LATER]


def test_a_version_the_capability_cannot_read_is_named_and_states_no_fact(tmp_path: Path) -> None:
    root = published(tmp_path)
    newer(root, "1.1.0", needs="9.0.0")
    assert lines(root) == [
        "behind: 1 of 1 lock a person moves",
        PUBLISHED,
        NOTHING_NEWER,
        f"    tests@1.1.0: it needs release 9.0.0 of the capability, and {capability_version()} "
        "is installed: upgrade the capability",
    ]
    assert behind_facts(root) == []


def test_a_clash_and_a_lost_end_are_named_and_the_checks_fact_stays(tmp_path: Path) -> None:
    lock = lab_lock("1.0.0", "1.0.0")
    clashing = released_lab(
        lab_project(
            tmp_path / "clash",
            ROW,
            lock,
            {"1.0.0": False},
            {"1.0.0": {}, "1.1.0": {"size": True}},
            state="published",
        )
    )
    losing = released_lab(
        lab_project(
            tmp_path / "loss",
            NET,
            lock,
            {"1.0.0": False, "1.1.0": True},
            {"1.0.0": {"frame": True}},
            state="published",
        )
    )

    assert lines(clashing)[2:] == [
        f"  {PATTERNS} 1.0.0: no newer version fits within major 1",
        f"    {PATTERNS}@1.1.0: {CLASH}",
    ]
    assert lines(losing)[2:] == [
        f"  {BLOCKS} 1.0.0: no newer version fits within major 1",
        f"    {BLOCKS}@1.1.0: {'; '.join(LOST)}",
    ]
    assert behind_facts(clashing) == [
        f"the published piece `{PIECE}` locks {PATTERNS}@1.0.0, behind {PATTERNS}@1.1.0, a "
        f"released version of its major — run `pkit visual upgrade {PIECE}`, which proposes the "
        "move; `pkit visual outdated` says whether a move takes it, and why not"
    ]
    assert len(behind_facts(losing)) == 1


# --- a lock it cannot judge ---------------------------------------------------------------------


def test_a_lock_it_cannot_read_is_named_and_judged_no_further(tmp_path: Path) -> None:
    root = published(tmp_path)
    path = root / PIECE_FILE
    path.write_text(
        path.read_text(encoding="utf-8").replace("tests: 1.0.0", "tests: latest"), encoding="utf-8"
    )
    assert lines(root) == [
        "behind: none, of 0 locks a person moves",
        f"not judged: {PIECE_FILE}, whose lock cannot be read: its lock names `tests: latest`, "
        "which is no version",
    ]


def test_a_piece_it_cannot_read_is_named_with_why(tmp_path: Path) -> None:
    root = published(tmp_path)
    newer(root, "1.1.0")
    (root / PIECE_FOLDER / "content.en.yaml").unlink()
    assert lines(root) == [
        "behind: none, of 0 locks a person moves",
        f"not judged: the published piece `{PIECE}`, in {PIECE_FILE}: "
        f"{PIECE_FOLDER}/content.en.yaml does not exist: the piece lists the language `en`, so "
        "write its content there",
    ]
