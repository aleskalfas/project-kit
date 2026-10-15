"""A clash of area names, and the hold on new core areas and adapters (ADR-065 point 13).

One clash can happen today: a project's own area at `.pkit/lifecycle/`, made
before v1.149.0 first shipped the core area of that name. The core area holds
`ownership.py`, and a project's own does not. A transition and sync's copy stop
on it before they write (`tests/test_upgrade.py` and `tests/test_sync.py` run
both commands). Until #1600 builds the full check, no release adds a core area
or a core adapter, and the hold's test below fails on any change to either.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path, PurePath

import click
import pytest

from project_kit import install, router, sync, treecopy
from project_kit.manifest import read_kit_version
from tests.adopter_repo import MakeAdopterRepo

# The areas a release propagates, and the core adapters it ships, as #1572 left
# them. The hold (ADR-065 point 13) keeps both until #1600 builds the full check.
HELD_AREAS = frozenset(
    {
        "decisions",
        "skills",
        "cli",
        "adapters",
        "scratchpad",
        "agents",
        "schemas",
        "permissions",
        "rules",
        "process",
        "lifecycle",
        "migrations",
    }
)
HELD_ADAPTERS = frozenset({"claude-code"})

HOLD_MESSAGE = (
    "No release adds, removes or changes a core area or a core adapter, or moves the core "
    "lifecycle area's ownership.py, until #1600 builds the full check of a clash of area "
    "names (ADR-065 point 13). A project's own area or adapter of the same name would be "
    "copied over. Build #1600 first, then lift this hold there."
)


def _bundled_adapters(source_kit: Path) -> frozenset[str]:
    """The adapters the bundle ships, as first install and the copy walk them."""
    adapters = source_kit / "adapters"
    return frozenset(
        p.name
        for p in adapters.iterdir()
        if p.is_dir() and not treecopy.is_python_cache(PurePath(p.name))
    )


def test_the_hold_no_release_changes_the_core_areas_until_1600() -> None:
    assert frozenset(install.PROPAGATED_AREAS) == HELD_AREAS, HOLD_MESSAGE


def test_the_hold_no_release_changes_the_core_adapters_until_1600() -> None:
    assert _bundled_adapters(install.find_source_kit()) == HELD_ADAPTERS, HOLD_MESSAGE


def test_the_hold_the_core_lifecycle_area_keeps_its_mark_until_1600() -> None:
    """The test tells the core area apart by the file it has held since it first
    shipped. A release that moved it would stop every project on its own core area."""
    source = install.find_source_kit()
    assert install.LIFECYCLE_AREA in install.PROPAGATED_AREAS, HOLD_MESSAGE
    assert (source / install.LIFECYCLE_AREA / install.LIFECYCLE_MARK).is_file(), HOLD_MESSAGE


# --- Telling a project's own area from the core one ----------------------------


@pytest.fixture
def target(make_adopter_repo: MakeAdopterRepo) -> Path:
    """An installed project, its `lifecycle` area the core one."""
    return make_adopter_repo().root


def _own_area(target: Path) -> Path:
    """Replace the core `lifecycle` area with a project's own, as one made before v1.149.0."""
    area = target / ".pkit" / install.LIFECYCLE_AREA
    shutil.rmtree(area)
    area.mkdir()
    (area / "README.md").write_text(
        "# Our lifecycle\n\nThe project's own area.\n", encoding="utf-8"
    )
    (area / "stages.md").write_text("- design\n- build\n", encoding="utf-8")
    return area


def test_the_core_area_is_no_clash(target: Path) -> None:
    assert sync.area_name_clash(target, install.find_source_kit()) is None


def test_a_project_without_the_area_meets_no_clash(target: Path) -> None:
    shutil.rmtree(target / ".pkit" / install.LIFECYCLE_AREA)
    assert sync.area_name_clash(target, install.find_source_kit()) is None


def test_the_projects_own_area_is_a_clash(target: Path) -> None:
    area = _own_area(target)
    assert sync.area_name_clash(target, install.find_source_kit()) == area


def test_an_empty_folder_is_no_clash(target: Path) -> None:
    area = target / ".pkit" / install.LIFECYCLE_AREA
    shutil.rmtree(area)
    area.mkdir()
    assert sync.area_name_clash(target, install.find_source_kit()) is None


def test_a_file_at_the_path_is_a_clash(target: Path) -> None:
    area = target / ".pkit" / install.LIFECYCLE_AREA
    shutil.rmtree(area)
    area.write_text("not a folder\n", encoding="utf-8")
    assert sync.area_name_clash(target, install.find_source_kit()) == area


def test_a_folder_named_like_the_mark_is_a_clash(target: Path) -> None:
    area = _own_area(target)
    (area / install.LIFECYCLE_MARK).mkdir()
    assert sync.area_name_clash(target, install.find_source_kit()) == area


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="needs symlinks")
def test_a_symlink_at_the_path_is_a_clash(target: Path, tmp_path: Path) -> None:
    area = target / ".pkit" / install.LIFECYCLE_AREA
    elsewhere = tmp_path / "elsewhere"
    shutil.move(area, elsewhere)
    area.symlink_to(elsewhere, target_is_directory=True)
    assert sync.area_name_clash(target, install.find_source_kit()) == area


def test_a_pkit_that_ships_no_lifecycle_area_meets_no_clash(target: Path, tmp_path: Path) -> None:
    """A release before v1.149.0 ships no core `lifecycle` area, so it writes none over
    the project's."""
    _own_area(target)
    source = tmp_path / "older" / ".pkit"
    source.mkdir(parents=True)
    assert sync.area_name_clash(target, source) is None


# --- The message --------------------------------------------------------------


def _message(target: Path, command: str = "sync") -> str:
    with pytest.raises(click.ClickException) as excinfo:
        sync.refuse_area_name_clash(target, install.find_source_kit(), command=command)
    return " ".join(excinfo.value.message.split())


def test_the_upgrades_message_names_the_path_the_release_and_the_ways_on(target: Path) -> None:
    _own_area(target)
    recorded = read_kit_version(install.find_source_kit())

    message = _message(target, command="upgrade")

    assert "refusing to run `pkit upgrade`: .pkit/lifecycle/ is the project's own area" in message
    assert f"pkit {recorded} ships a core area of that name" in message
    assert "no flag overrides this refusal" in message
    assert "move the project's area to another name" in message
    assert f"To stay at {recorded}: run `pkit pin`" in message
    assert "git checkout -- .pkit/lifecycle/ownership.py" in message
    assert "Where git holds no copy of it, remove the folder" in message


def test_a_pinned_project_stays_by_doing_nothing(target: Path) -> None:
    _own_area(target)
    recorded = read_kit_version(install.find_source_kit())
    router.pin_file_path(target).write_text(f"{recorded}\n", encoding="utf-8")

    message = _message(target, command="upgrade")

    assert f"To stay at {recorded}: do nothing. This upgrade moved no pin" in message
    assert "run `pkit pin`" not in message


def test_syncs_message_names_no_way_to_stay(target: Path) -> None:
    """Sync already runs the release the project records, so staying is no way on."""
    _own_area(target)

    message = _message(target, command="sync")

    assert "refusing to run `pkit sync`" in message
    assert "move the project's area to another name" in message
    assert "To stay" not in message
    assert "git checkout -- .pkit/lifecycle/ownership.py" in message


def test_the_core_area_passes_the_refusal(target: Path) -> None:
    sync.refuse_area_name_clash(target, install.find_source_kit(), command="sync")


# --- The copy keeps the test true ---------------------------------------------


def test_the_copy_writes_the_mark_first(target: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An interrupted copy leaves the area empty, or holding its mark: never a clash."""
    area = target / ".pkit" / install.LIFECYCLE_AREA
    shutil.rmtree(area)
    real_copy = install._copy_file
    written: list[Path] = []

    def copy_then_stop(src: Path, dst: Path, ctx: install.InstallContext, **kwargs: bool) -> None:
        if area in dst.parents:
            written.append(dst)
            real_copy(src, dst, ctx, **kwargs)
            raise KeyboardInterrupt
        real_copy(src, dst, ctx, **kwargs)

    monkeypatch.setattr(install, "_copy_file", copy_then_stop)
    source = install.find_source_kit()
    ctx = install.InstallContext(target_root=target, source_kit=source, dry_run=False)

    with pytest.raises(KeyboardInterrupt):
        install._install_area(source / install.LIFECYCLE_AREA, area, ctx, overwrite=True)

    assert written == [area / install.LIFECYCLE_MARK]
    assert sync.area_name_clash(target, source) is None
