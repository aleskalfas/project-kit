"""The one listing of the working tree (ADR-057 point 2).

Validation, the friction writers and the change check's head read the working
tree through one listing, so from one state of the repository they find the
same artefacts. Outside a git work tree the listing is the filesystem's, and
the only difference is that git's own rules do not apply. These tests pin both.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from project_kit import friction_check as fc
from project_kit import friction_discovery as fd
from project_kit import friction_validate as fv
from project_kit import validators
from project_kit import working_tree as wt
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

CONFIG = ".pkit/project/config.yaml"


def _document(artefact_id: str, newline: str = "\n") -> str:
    lines = [
        "---",
        f"id: {artefact_id}",
        "pkit:",
        "  friction:",
        "    anchors: {path: [src/**]}",
        "---",
        "",
        f"Body of {artefact_id}.",
        "",
    ]
    return newline.join(lines)


def _stage(root: Path) -> None:
    """One working tree holding every case the two listings once read differently."""
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "guide.md").write_text(_document("guide"), encoding="utf-8")
    (root / "docs" / "ignored.md").write_text(_document("ignored"), encoding="utf-8")
    (root / "docs" / "crlf.md").write_bytes(_document("crlf", newline="\r\n").encode())
    (root / "docs" / "alias.md").symlink_to(root / "docs" / "guide.md")
    (root / "other").mkdir()
    (root / "other" / "beyond.md").write_text(_document("beyond"), encoding="utf-8")
    (root / "docs" / "linked").symlink_to(root / "other", target_is_directory=True)
    (root / ".gitignore").write_text("docs/ignored.md\n", encoding="utf-8")
    nested = root / "docs" / "nested"
    nested.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=nested, check=True)
    (nested / "inner.md").write_text(_document("inner"), encoding="utf-8")


@pytest.fixture
def adopter(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    repo = make_adopter_repo()
    _stage(repo.root)
    repo.write({CONFIG: "friction:\n  places: [docs, 'docs/**.md']\n"})
    return repo


def test_validation_and_the_change_check_find_the_same_artefacts(adopter: AdopterRepo) -> None:
    """The change check's head is `WorkingTree`; validation reads the same listing.

    An ignored file, a link to a document, a link to a folder, a nested repository:
    none is an artefact in either. A file with Windows line endings is one in both.
    A `**` inside a segment reads as pathlib 3.13 reads it, on every interpreter.
    """
    validated = fv.validate_friction(adopter.root).discovery
    checked = fd.discover_artefacts(adopter.root, tree=fc.WorkingTree(adopter.root))

    locations = [a.location for a in validated.artefacts]
    assert locations == ["docs/crlf.md", "docs/guide.md"]
    assert [a.location for a in checked.artefacts] == locations
    assert [a.place.pattern for a in checked.artefacts] == [
        a.place.pattern for a in validated.artefacts
    ]
    assert validated.unreadable == checked.unreadable == ()


def test_inside_a_git_work_tree_the_listing_is_gits(adopter: AdopterRepo) -> None:
    tree = wt.working_tree(adopter.root)
    assert type(tree) is wt.WorkingTree
    files = set(tree.files())
    assert {"docs/guide.md", "docs/crlf.md", "docs/alias.md", "docs/linked"} <= files
    assert "docs/ignored.md" not in files
    assert not any(f.startswith(("docs/nested/", "docs/linked/")) for f in files)
    assert tree.read_file("docs/alias.md") is None  # a link is never read
    assert tree.read_file("docs/linked") is None


def test_outside_a_git_work_tree_only_gits_own_rules_are_missing(tmp_path: Path) -> None:
    """The one documented difference between the two listings: without git's view,
    its ignore rules and its refusal to look inside a nested repository do not apply."""
    root = tmp_path / "plain"
    root.mkdir()
    _stage(root)
    tree = wt.working_tree(root)
    assert type(tree) is wt.FilesystemTree
    everything = set(tree.files())

    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    seen_by_git = set(wt.WorkingTree(root).files())

    assert seen_by_git <= everything
    left_out_by_git = everything - seen_by_git
    assert left_out_by_git == {"docs/ignored.md"} | {
        f for f in everything if f.startswith("docs/nested/")
    }
    assert "docs/nested/inner.md" in left_out_by_git
    # Links are listed alike, and nothing beneath a linked folder is listed by either.
    assert {"docs/alias.md", "docs/linked"} <= seen_by_git
    assert not any(f.startswith("docs/linked/") for f in everything)
    assert ".git/HEAD" not in everything


def test_an_unreadable_file_is_reported_by_both_readers(adopter: AdopterRepo) -> None:
    if os.geteuid() == 0:
        pytest.skip("root reads a file whatever its mode")
    locked = adopter.root / "docs" / "locked.md"
    locked.write_text(_document("locked"), encoding="utf-8")
    locked.chmod(0)
    try:
        validated = fv.validate_friction(adopter.root).discovery
        checked = fd.discover_artefacts(adopter.root, tree=fc.WorkingTree(adopter.root))
    finally:
        locked.chmod(0o644)
    assert [u.path for u in validated.unreadable] == ["docs/locked.md"]
    assert [u.path for u in checked.unreadable] == ["docs/locked.md"]


def test_the_listing_is_taken_once_per_validate_run(adopter: AdopterRepo) -> None:
    seen: list[wt.WorkingTree] = []

    def member(root: Path) -> validators.Outcome:
        seen.append(wt.working_tree(root))
        return validators.Outcome((), ())

    runs = [validators.Validator(name, member, index) for index, name in enumerate("ab")]
    validators.run_all(adopter.root, runs)
    assert len(seen) == 2 and seen[0] is seen[1]
    assert wt.working_tree(adopter.root) is not seen[0]  # outside a run, taken afresh
