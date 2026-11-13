"""`pkit version tag` tags the commit a final release landed (ADR-092 point 6).

The commit is the newest at or before HEAD on the default branch's first-parent
history that changed `.pkit/VERSION`, and the tag is named by the version that
commit records. It refuses, tagging nothing, where HEAD is off that history, where
that commit records no final release version, where the tag exists here or, with
`--push`, on `origin`, and where a shallow clone's history stops at the commit it
found. The tests of the tag's annotation, its push and the cross-repository guard
are in `test_versioning.py`.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from project_kit import cli, session_guard, versioning
from tests.adopter_repo import GitRepo, sign_nothing

VERSION = ".pkit/VERSION"

#: The subject of the commit a release PR lands, as the release workflow names it.
RELEASE_SUBJECT = "chore(release): v1.1.0 (#7)"


def _land_release(repo: GitRepo, version: str, *, landing: str) -> str:
    """Land a release of `version` on `main` from its release branch, by a merge
    commit or a squash commit, after another change landed on `main` meanwhile.
    Returns the commit the release landed."""
    branch = f"release/v{version}"
    repo.checkout(branch, create=True)
    repo.commit(f"chore(release): v{version}", {VERSION: f"{version}\n"})
    repo.checkout("main")
    repo.commit("feat: a change that landed while the release PR was open", {"a.md": "a\n"})
    subject = f"chore(release): v{version} (#7)"
    if landing == "merge":
        return repo.merge(branch, subject)
    return repo.squash_merge(branch, subject)


@pytest.fixture
def released(tmp_path: Path) -> tuple[GitRepo, str]:
    """A project whose release 1.1.0 landed on `main` by a merge commit, with a
    change landed after it, so HEAD is not the release: (repo, the landed commit)."""
    repo = GitRepo.init(tmp_path / "project")
    repo.commit("seed", {VERSION: "1.0.0\n"})
    landed = _land_release(repo, "1.1.0", landing="merge")
    repo.commit("fix: a change that landed after the release", {"b.md": "b\n"})
    return repo, landed


def _kit(repo: GitRepo) -> Path:
    return repo.root / ".pkit"


def _tags(repo: GitRepo) -> list[str]:
    return repo.git("tag", "-l").stdout.split()


def _tagged_commit(repo: GitRepo, tag: str) -> str:
    return repo.git("rev-parse", f"{tag}^{{commit}}").stdout.strip()


def _with_origin(repo: GitRepo, tmp_path: Path) -> Path:
    """A bare repository as the project's `origin`, holding `main` as it stands."""
    bare = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-q", str(bare)], check=True)
    repo.git("remote", "add", "origin", str(bare))
    repo.git("push", "-q", "origin", "main")
    return bare


def _cleared(repo: GitRepo) -> session_guard.Clearance:
    cleared = session_guard.clear(repo.root, confirmed=False, interactive=False)
    assert isinstance(cleared, session_guard.Clearance)
    return cleared


# --- the commit the tag names ---------------------------------------------------------------


@pytest.mark.parametrize("landing", ["merge", "squash"])
def test_the_tag_names_the_commit_the_release_landed_not_head(landing: str, tmp_path: Path) -> None:
    """A push may carry more than the release: the tag goes on the commit the
    release PR landed, named by the version it records, whatever came after it and
    whatever the working tree's `.pkit/VERSION` holds."""
    repo = GitRepo.init(tmp_path / "project")
    repo.commit("seed", {VERSION: "1.0.0\n"})
    landed = _land_release(repo, "1.1.0", landing=landing)
    head = repo.commit("fix: a change that landed after the release", {"b.md": "b\n"})
    repo.write({VERSION: "9.9.9\n"})

    tag = versioning.tag_version(_kit(repo))

    assert tag == "v1.1.0"
    assert _tags(repo) == ["v1.1.0"]
    assert _tagged_commit(repo, "v1.1.0") == landed != head
    annotation = repo.git("tag", "-n100", "v1.1.0").stdout
    assert RELEASE_SUBJECT in annotation


def test_the_command_names_the_commit_it_tagged(
    released: tuple[GitRepo, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, landed = released
    monkeypatch.setattr(cli, "_target_kit", lambda: _kit(repo))

    result = CliRunner().invoke(cli.main, ["version", "tag"])

    assert result.exit_code == 0, result.output
    assert f"Tagged {landed[:12]} as v1.1.0" in result.output
    assert "main's first-parent history that changed .pkit/VERSION" in result.output


def test_the_default_branch_is_read_from_origin(
    released: tuple[GitRepo, str], tmp_path: Path
) -> None:
    """With a remote, the default branch is `origin/main` (COR-054 point 2): HEAD on
    its history tags the release it holds."""
    repo, landed = released
    bare = _with_origin(repo, tmp_path)

    versioning.tag_version(_kit(repo), push=True, clearance=_cleared(repo))

    assert _tagged_commit(repo, "v1.1.0") == landed
    remote = subprocess.run(
        ["git", "ls-remote", "--tags", str(bare)], capture_output=True, text=True, check=True
    ).stdout
    assert "refs/tags/v1.1.0" in remote


# --- the refusals ---------------------------------------------------------------------------


def _side_commit(repo: GitRepo, landed: str) -> None:
    """HEAD on the release branch's own commit, which the merge commit brought into
    `main` as its second parent."""
    repo.git("checkout", "-q", f"{landed}^2")


def _branch_commit(repo: GitRepo, _: str) -> None:
    """HEAD on a commit of a branch that has not landed."""
    repo.checkout("feature", create=True)
    repo.commit("feat: a change on a branch", {"c.md": "c\n"})


@pytest.mark.parametrize(
    "move_head", [_branch_commit, _side_commit], ids=["a-branch", "a-merged-side-commit"]
)
def test_head_off_the_default_branchs_first_parent_history_is_refused(
    move_head: Callable[[GitRepo, str], None], released: tuple[GitRepo, str]
) -> None:
    repo, landed = released
    move_head(repo, landed)

    with pytest.raises(click.ClickException) as refused:
        versioning.tag_version(_kit(repo))

    assert "is off main's first-parent history" in refused.value.message
    assert "Nothing was tagged" in refused.value.message
    assert _tags(repo) == []


def test_a_commit_not_on_origin_is_off_the_default_branch(
    released: tuple[GitRepo, str], tmp_path: Path
) -> None:
    """With a remote, `main`'s own commits that `origin` lacks are off its history."""
    repo, _ = released
    _with_origin(repo, tmp_path)
    repo.commit("chore: a commit nobody pushed", {"d.md": "d\n"})

    with pytest.raises(click.ClickException, match="is off origin/main's first-parent history"):
        versioning.tag_version(_kit(repo))
    assert _tags(repo) == []


def test_a_tag_that_exists_locally_is_refused(released: tuple[GitRepo, str]) -> None:
    repo, landed = released
    seed = repo.git("rev-parse", f"{landed}^1^1").stdout.strip()
    repo.git("tag", "-a", "v1.1.0", "-m", "v1.1.0", seed)

    with pytest.raises(
        click.ClickException, match=rf"tag v1\.1\.0 already exists locally, on {seed[:12]}"
    ):
        versioning.tag_version(_kit(repo))
    assert _tagged_commit(repo, "v1.1.0") == seed


def test_a_tag_that_exists_on_origin_is_refused_before_a_push(
    released: tuple[GitRepo, str], tmp_path: Path
) -> None:
    """A clone that has not fetched the remote's tags would otherwise make a tag its
    push cannot land."""
    repo, landed = released
    _with_origin(repo, tmp_path)
    repo.git("tag", "-a", "v1.1.0", "-m", "v1.1.0", landed)
    repo.git("push", "-q", "origin", "v1.1.0")
    repo.git("tag", "-d", "v1.1.0")

    with pytest.raises(click.ClickException, match=r"tag v1\.1\.0 already exists on origin"):
        versioning.tag_version(_kit(repo), push=True, clearance=_cleared(repo))
    assert _tags(repo) == []


@pytest.mark.parametrize("version", ["1.2.0rc1", "not-a-version"])
def test_a_version_that_names_no_final_release_is_refused(version: str, tmp_path: Path) -> None:
    """`pkit version tag` tags final releases only: a candidate's tag stays on the
    commit its cut made."""
    repo = GitRepo.init(tmp_path / "project")
    repo.commit("seed", {VERSION: "1.0.0\n"})
    recorded = repo.commit("chore: a version by hand", {VERSION: f"{version}\n"})

    with pytest.raises(click.ClickException) as refused:
        versioning.tag_version(_kit(repo))

    assert f"{recorded[:12]}, the newest commit" in refused.value.message
    assert f"records {version!r}, which is no final release version" in refused.value.message
    assert _tags(repo) == []


def test_a_shallow_clone_whose_history_stops_at_the_commit_found_is_refused(
    released: tuple[GitRepo, str], tmp_path: Path
) -> None:
    """Cut at HEAD, the clone shows HEAD as the commit that changed `.pkit/VERSION`,
    though an older one did: it cannot tell which commit the release landed."""
    repo, _ = released
    clone = tmp_path / "shallow"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", f"file://{repo.root}", str(clone)], check=True
    )
    sign_nothing(clone)

    with pytest.raises(click.ClickException, match="this clone is shallow"):
        versioning.tag_version(clone / ".pkit")
    assert GitRepo(clone).git("tag", "-l").stdout == ""
