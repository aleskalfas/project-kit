"""Tests for the shared adopter-repository fixture (#980): backbone installed,
chosen capabilities installed, and a scripted history whose shape later
consumers (validators, the friction engine per COR-050) rely on."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from project_kit import capabilities as caps
from project_kit.manifest import read_backbone_manifest
from tests.adopter_repo import (
    HISTORY_EPOCH,
    SEED_CONTENT,
    SEED_CONTENT_REVIEWED,
    AdopterRepo,
    Author,
    GitRepo,
    MakeAdopterRepo,
)

# --- bare adopter ---------------------------------------------------------------


def test_bare_adopter_has_backbone_and_no_commits(
    make_adopter_repo: MakeAdopterRepo, tmp_path: Path
) -> None:
    adopter = make_adopter_repo()
    assert adopter.root == tmp_path
    assert (adopter.pkit / "manifest.yaml").is_file()
    assert read_backbone_manifest(adopter.root) is not None
    assert adopter.history is None
    assert adopter.git("rev-parse", "--verify", "HEAD", check=False).returncode != 0
    assert Path.cwd() == tmp_path


def test_chdir_can_be_declined(make_adopter_repo: MakeAdopterRepo, tmp_path: Path) -> None:
    before = Path.cwd()
    make_adopter_repo(chdir=False)
    assert Path.cwd() == before


def test_capabilities_install_in_order(make_adopter_repo: MakeAdopterRepo) -> None:
    adopter = make_adopter_repo(capabilities=("project-management", "software-engineering"))
    assert caps.is_installed(adopter.root, "project-management")
    assert caps.is_installed(adopter.root, "software-engineering")
    manifest = read_backbone_manifest(adopter.root)
    assert manifest is not None
    assert {c.name for c in manifest.components} >= {"project-management", "software-engineering"}


def test_dependent_before_dependency_is_refused(make_adopter_repo: MakeAdopterRepo) -> None:
    adopter = make_adopter_repo()
    try:
        adopter.install_capabilities("software-engineering")
    except ValueError as exc:
        assert "project-management" in str(exc)
    else:
        raise AssertionError("expected a dependency refusal")


def test_unknown_capability_is_refused(make_adopter_repo: MakeAdopterRepo) -> None:
    adopter = make_adopter_repo()
    try:
        adopter.install_capabilities("no-such-capability")
    except ValueError as exc:
        assert "no-such-capability" in str(exc)
    else:
        raise AssertionError("expected an unknown-capability refusal")


# --- scripted history -------------------------------------------------------------


def test_history_main_line_is_initial_rename_squash(adopter_repo: AdopterRepo) -> None:
    h = adopter_repo.history
    assert h is not None
    assert adopter_repo.current_branch() == "main"
    assert adopter_repo.shas() == [h.squash_merge, h.rename, h.initial]
    # The install went into the initial commit.
    assert ".pkit/manifest.yaml" in adopter_repo.git(
        "show", "--name-only", "--format=", h.initial
    ).stdout.split()


def test_history_rename_is_followable(adopter_repo: AdopterRepo) -> None:
    h = adopter_repo.history
    assert h is not None
    assert not (adopter_repo.root / h.seed_path).exists()
    assert (adopter_repo.root / h.renamed_path).read_text(encoding="utf-8") == SEED_CONTENT_REVIEWED
    # Without --follow the renamed path's history stops at the rename;
    # with it, the initial commit is reachable.
    assert adopter_repo.shas(h.renamed_path) == [h.squash_merge, h.rename]
    assert adopter_repo.shas(h.renamed_path, follow=True) == [h.squash_merge, h.rename, h.initial]
    rename_status = adopter_repo.git(
        "show", "--name-status", "--format=", "-M", h.rename
    ).stdout.strip()
    assert rename_status.startswith("R100")


def test_history_squash_merge_has_one_parent_and_side_branch_survives(
    adopter_repo: AdopterRepo,
) -> None:
    h = adopter_repo.history
    assert h is not None
    parents = adopter_repo.git("rev-list", "--parents", "-n", "1", h.squash_merge).stdout.split()
    assert parents == [h.squash_merge, h.rename]
    # Side commits are not on main but remain reachable through the branch.
    assert h.side[0] not in adopter_repo.shas()
    assert adopter_repo.shas(rev=h.side_branch) == [h.side[1], h.side[0], h.rename, h.initial]
    # The squash landed both side edits.
    landed = adopter_repo.git("show", "--name-only", "--format=", h.squash_merge).stdout.split()
    assert set(landed) == {h.renamed_path, h.side_path}


def test_history_field_change_provenance(adopter_repo: AdopterRepo) -> None:
    """The property the friction engine will derive: `status` last changed in
    the squash commit, `title` last changed at the initial commit (visible from
    the renamed path only by following the rename)."""
    h = adopter_repo.history
    assert h is not None
    squash_diff = adopter_repo.git("show", "--format=", h.squash_merge, "--", h.renamed_path).stdout
    assert "-status: draft" in squash_diff and "+status: review" in squash_diff
    assert "+title:" not in squash_diff and "-title:" not in squash_diff
    rename_diff = adopter_repo.git("show", "--format=", "-M", h.rename).stdout
    assert "+title:" not in rename_diff and "+status:" not in rename_diff
    initial_diff = adopter_repo.git("show", "--format=", h.initial, "--", h.seed_path).stdout
    assert "+title: Alpha" in initial_diff
    assert SEED_CONTENT.startswith("---\ntitle: Alpha")


def test_history_dates_are_deterministic_and_ordered(adopter_repo: AdopterRepo) -> None:
    stamps = adopter_repo.git("log", "--format=%aI", "main").stdout.split()
    dates = [datetime.fromisoformat(s) for s in stamps]
    assert dates == sorted(dates, reverse=True)
    assert dates[-1] == HISTORY_EPOCH


# --- commit helpers ---------------------------------------------------------------


def test_commit_returns_sha_and_honours_author_and_date(adopter_repo: AdopterRepo) -> None:
    when = datetime(2026, 3, 4, 5, 6, 7, tzinfo=UTC)
    sha = adopter_repo.commit(
        "edit gamma",
        {"docs/gamma.md": "---\ntitle: Gamma\n---\n"},
        author=Author("Ada", "ada@example.com"),
        date=when,
    )
    assert sha == adopter_repo.head()
    name, email, committer, authored, committed = (
        adopter_repo.git("log", "-1", "--format=%an|%ae|%cn|%aI|%cI", sha).stdout.strip().split("|")
    )
    assert (name, email, committer) == ("Ada", "ada@example.com", "Ada")
    assert datetime.fromisoformat(authored) == when
    assert datetime.fromisoformat(committed) == when
    assert adopter_repo.git("show", "--name-only", "--format=", sha).stdout.split() == [
        "docs/gamma.md"
    ]


def test_commit_with_none_deletes(adopter_repo: AdopterRepo) -> None:
    h = adopter_repo.history
    assert h is not None
    sha = adopter_repo.commit("drop beta", {h.side_path: None})
    assert not (adopter_repo.root / h.side_path).exists()
    status = adopter_repo.git("show", "--name-status", "--format=", sha).stdout.strip()
    assert status == f"D\t{h.side_path}"


def test_gitrepo_stands_alone(tmp_path: Path) -> None:
    """`GitRepo` serves non-adopter repos too (e.g. a synthetic source kit)."""
    repo = GitRepo.init(tmp_path / "plain")
    first = repo.commit("seed", {"README.md": "hi\n"})
    second = repo.commit("more", {"README.md": "hi again\n"})
    assert repo.shas() == [second, first]
    assert repo.current_branch() == "main"
