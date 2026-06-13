"""Tests for the ownership-aware tree-refresh primitive (COR-001).

`refresh_owned_tree` is the single destructive-copy mechanic the capability
refresh and the area/adapter sync both route through. These exercise its
contract directly — both ownership modes (kit-owned refresh, adopter-owned
seed-once), orphan pruning, exclusion, empty-dir cleanup, mode preservation,
and dry-run — so the safety property is tested at the primitive, not only
through one caller.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path, PurePath

from project_kit import treecopy


def _project_owned(rel: PurePath) -> bool:
    """Top-level `project/` is adopter-owned (the capability convention)."""
    return bool(rel.parts) and rel.parts[0] == "project"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# --- kit-owned refresh -------------------------------------------------


def test_kit_owned_files_copied_and_overwritten(tmp_path: Path) -> None:
    src, dst = tmp_path / "src", tmp_path / "dst"
    _write(src / "core" / "a.txt", "new")
    _write(dst / "core" / "a.txt", "old")

    treecopy.refresh_owned_tree(src, dst, is_owned=treecopy.nothing_owned)

    assert (dst / "core" / "a.txt").read_text(encoding="utf-8") == "new"


def test_kit_owned_orphans_pruned(tmp_path: Path) -> None:
    src, dst = tmp_path / "src", tmp_path / "dst"
    _write(src / "a.txt", "a")
    _write(dst / "a.txt", "a")
    _write(dst / "gone.txt", "removed upstream")

    treecopy.refresh_owned_tree(src, dst, is_owned=treecopy.nothing_owned)

    assert (dst / "a.txt").is_file()
    assert not (dst / "gone.txt").exists()


def test_emptied_kit_owned_dir_removed(tmp_path: Path) -> None:
    src, dst = tmp_path / "src", tmp_path / "dst"
    _write(src / "keep.txt", "k")
    _write(dst / "keep.txt", "k")
    _write(dst / "stale" / "old.txt", "orphan in a now-removed dir")

    treecopy.refresh_owned_tree(src, dst, is_owned=treecopy.nothing_owned)

    assert not (dst / "stale").exists(), "emptied kit-owned dir should be pruned"


def test_empty_source_dir_reproduced(tmp_path: Path) -> None:
    src, dst = tmp_path / "src", tmp_path / "dst"
    (src / "empty").mkdir(parents=True)
    _write(src / "a.txt", "a")

    treecopy.refresh_owned_tree(src, dst, is_owned=treecopy.nothing_owned)

    assert (dst / "empty").is_dir()


# --- adopter-owned seed-once / preserve --------------------------------


def test_adopter_owned_seeded_when_absent(tmp_path: Path) -> None:
    src, dst = tmp_path / "src", tmp_path / "dst"
    _write(src / "project" / "config.yaml", "seed")

    treecopy.refresh_owned_tree(src, dst, is_owned=_project_owned)

    assert (dst / "project" / "config.yaml").read_text(encoding="utf-8") == "seed"


def test_adopter_owned_preserved_when_present(tmp_path: Path) -> None:
    src, dst = tmp_path / "src", tmp_path / "dst"
    _write(src / "project" / "config.yaml", "seed")
    _write(dst / "project" / "config.yaml", "adopter customisation")

    treecopy.refresh_owned_tree(src, dst, is_owned=_project_owned)

    assert (
        (dst / "project" / "config.yaml").read_text(encoding="utf-8")
        == "adopter customisation"
    ), "adopter-owned file must never be overwritten"


def test_adopter_owned_orphan_never_pruned(tmp_path: Path) -> None:
    src, dst = tmp_path / "src", tmp_path / "dst"
    _write(src / "core.txt", "k")
    # An adopter file with no source counterpart must survive.
    _write(dst / "project" / "mine.yaml", "adopter-authored, not in source")

    treecopy.refresh_owned_tree(src, dst, is_owned=_project_owned)

    assert (dst / "project" / "mine.yaml").is_file()


def test_nested_project_below_kit_dir_is_not_adopter_owned(tmp_path: Path) -> None:
    """Only top-level project/ is adopter-owned; a nested `project` segment
    under a kit-owned dir refreshes (positional convention)."""
    src, dst = tmp_path / "src", tmp_path / "dst"
    _write(src / "templates" / "project" / "t.txt", "new")
    _write(dst / "templates" / "project" / "t.txt", "old")

    treecopy.refresh_owned_tree(src, dst, is_owned=_project_owned)

    assert (dst / "templates" / "project" / "t.txt").read_text(encoding="utf-8") == "new"


# --- exclude -----------------------------------------------------------


def test_excluded_artifact_not_copied_and_pruned(tmp_path: Path) -> None:
    src, dst = tmp_path / "src", tmp_path / "dst"
    _write(src / "skills" / "foo.md", "shipped")
    _write(dst / "skills" / "foo.md", "from a prior install")

    treecopy.refresh_owned_tree(
        src, dst, is_owned=treecopy.nothing_owned, exclude=frozenset({"skills/foo.md"})
    )

    assert not (dst / "skills" / "foo.md").exists()


# --- mode preservation (capabilities ship executable *.sh / *.py) ------


def test_executable_bit_preserved(tmp_path: Path) -> None:
    src, dst = tmp_path / "src", tmp_path / "dst"
    script = src / "scripts" / "run.sh"
    _write(script, "#!/usr/bin/env bash\necho hi\n")
    script.chmod(0o755)

    treecopy.refresh_owned_tree(src, dst, is_owned=treecopy.nothing_owned)

    mode = (dst / "scripts" / "run.sh").stat().st_mode
    assert mode & stat.S_IXUSR, "executable bit must survive the refresh (copy2)"


# --- dry-run -----------------------------------------------------------


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    src, dst = tmp_path / "src", tmp_path / "dst"
    _write(src / "a.txt", "a")
    _write(dst / "orphan.txt", "should-not-be-pruned-in-dry-run")

    treecopy.refresh_owned_tree(
        src, dst, is_owned=treecopy.nothing_owned, dry_run=True
    )

    assert not (dst / "a.txt").exists(), "dry-run must not copy"
    assert (dst / "orphan.txt").is_file(), "dry-run must not prune"
