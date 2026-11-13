"""A release candidate is cut from a commit that has taken in the default branch's head.

`pkit release plan --pre` and `apply --pre` plan from the commit they run at, and
refuse before writing anything where the default branch's head, read from the remote,
is not in its history (ADR-092 point 2). A cut's number is one past the highest any
candidate tag on the remote carries, whatever its version (point 3), and the cut
records its base in the candidate's tree (point 9). Each test builds the
methodology's source repository on `main`, pushed to a bare remote `origin`, with a
backbone and a capability changeset pending.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import click
import pytest
from click.testing import CliRunner

from project_kit import release, release_candidate
from project_kit.cli import main
from project_kit.default_branch import CHECK_BASE_ENV
from tests.adopter_repo import GitRepo, sign_nothing

HOUSEWARE = ".pkit/capabilities/houseware/package.yaml"
BASE = release_candidate.BASE_PATH.as_posix()

CHANGELOG = "# Changelog\n\n## 1.0.0 — 2026-01-01\n\n### Added\n- The first release.\n"


def _package(version: str, requires: str) -> str:
    return (
        "schema_version: 1\ncomponent:\n  kind: capability\n  name: houseware\n"
        f'  version: {version}\nrequires_backbone: "{requires}"\n'
    )


def _changeset(component: str, kind: str, body: str, *extra: str) -> str:
    return "\n".join([f"component: {component}", f"kind: {kind}", f"body: {body}", *extra, ""])


def _project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> GitRepo:
    """The source repository, its `main` pushed to `origin`: backbone 1.0.0 and the
    capability houseware 0.3.0, with a backbone minor and a houseware patch pending,
    the patch declaring that houseware needs the backbone the release ships."""
    monkeypatch.delenv(CHECK_BASE_ENV, raising=False)
    repo = GitRepo.init(tmp_path / "work")
    repo.commit(
        "first",
        {
            ".pkit/VERSION": "1.0.0\n",
            ".pkit/manifest.yaml": (
                "schema_version: 1\nbackbone_version: 1.0.0\ncompleted_version: 1.0.0\n"
            ),
            HOUSEWARE: _package("0.3.0", ">=1.0.0,<1.1.0"),
            "src/project_kit/__init__.py": "",
            "CHANGELOG.md": CHANGELOG,
            ".changes/unreleased/backbone-minor.yaml": _changeset(
                "backbone", "minor", "A new command."
            ),
            ".changes/unreleased/houseware-patch.yaml": _changeset(
                "houseware", "patch", "Uses the new command.", "requires_backbone: release"
            ),
        },
    )
    remote = tmp_path / "origin.git"
    subprocess.run(
        ["git", "init", "-q", "--bare", "--initial-branch=main", str(remote)],
        check=True,
        capture_output=True,
    )
    repo.git("remote", "add", "origin", str(remote))
    repo.git("push", "-q", "origin", "main")
    monkeypatch.chdir(repo.root)
    return repo


def _clone(tmp_path: Path, repo: GitRepo) -> GitRepo:
    remote = repo.git("remote", "get-url", "origin").stdout.strip()
    target = tmp_path / "elsewhere"
    subprocess.run(
        ["git", "clone", "-q", f"file://{remote}", str(target)], check=True, capture_output=True
    )
    clone = GitRepo(target)
    clone.git("config", "user.name", "Tester")
    clone.git("config", "user.email", "tester@example.com")
    sign_nothing(target)
    return clone


def _tag(repo: GitRepo, *names: str) -> None:
    """Tag HEAD with each of `names`, annotated, and push them to `origin`."""
    for name in names:
        repo.git("tag", "-a", name, "-m", name)
    repo.git("push", "-q", "origin", *(f"refs/tags/{name}" for name in names))


def _run(*args: str) -> Any:
    return CliRunner().invoke(main, ["release", *args])


def _said(result: Any) -> str:
    return " ".join(str(result.output).split())


def _refused(result: Any) -> str:
    assert result.exit_code == 1, result.output
    said = _said(result)
    assert "Error: refusing to cut a candidate:" in said, said
    assert "Nothing was written" in said
    return said


def _status(repo: GitRepo) -> str:
    return repo.git("status", "--porcelain", "--untracked-files=all").stdout


def _at(repo: GitRepo, rev: str, path: str) -> str:
    return repo.git("show", f"{rev}:{path}").stdout


# --- the plan, and the history check ------------------------------------------------------


def test_the_plan_names_the_candidate_its_number_and_its_base(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch)

    result = _run("plan", "--pre")

    assert result.exit_code == 0, result.output
    said = _said(result)
    assert "backbone: 1.0.0 -> 1.1.0rc1 (minor)" in said
    assert "houseware: 0.3.0 -> 0.3.1rc1 (patch)" in said
    assert "changesets to consume: 0" in said
    assert "Candidate: v1.1.0rc1, number 1," in said
    assert f"Base: {repo.head()[:12]}, backbone 1.0.0," in said
    assert _status(repo) == ""


def test_a_branch_that_has_taken_in_the_default_branch_s_head_is_cut_from_its_own_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch)
    repo.checkout("feature", create=True)
    repo.commit("the branch's change", {"notes.md": "on the branch\n"})
    repo.checkout("main")
    repo.commit("main moves on", {"later.md": "later\n"})
    repo.git("push", "-q", "origin", "main")
    repo.checkout("feature")
    repo.merge("main")

    result = _run("plan", "--pre", "--json")

    assert result.exit_code == 0, result.output
    assert f'"commit": "{repo.head()}"' in result.output


def test_a_commit_without_the_default_branch_s_head_in_its_history_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch)
    repo.checkout("feature", create=True)
    repo.checkout("main")
    tip = repo.commit("main moves on", {"later.md": "later\n"})
    repo.git("push", "-q", "origin", "main")
    repo.checkout("feature")
    before = repo.head()

    said = _refused(_run("apply", "--pre", "--tag", "--yes"))

    assert (
        f"the head of main on origin, {tip[:12]}, is not in the history of {before[:12]}, "
        "the commit the cut is planned from (ADR-092 point 2). Merge origin/main into this "
        "branch, and run again."
    ) in said
    assert repo.head() == before
    assert _status(repo) == ""
    assert repo.git("tag", "--list").stdout == ""


def test_the_default_branch_s_head_is_read_from_the_remote_not_the_clone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch)
    elsewhere = _clone(tmp_path, repo)
    tip = elsewhere.commit("main moves on elsewhere", {"later.md": "later\n"})
    elsewhere.git("push", "-q", "origin", "main")

    said = _refused(_run("plan", "--pre"))

    assert (
        f"the head of main on origin, {tip[:12]}, is a commit this clone does not hold, so "
        f"it is not in the history of {repo.head()[:12]}"
    ) in said
    assert "Fetch main, merge it into this branch, and run again." in said


def test_a_working_tree_that_differs_from_the_commit_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch)
    (repo.root / ".changes/unreleased/stray.yaml").write_text(
        _changeset("backbone", "major", "Not committed."), encoding="utf-8"
    )

    said = _refused(_run("plan", "--pre"))

    assert f"the working tree differs from {repo.head()[:12]}" in said
    assert "?? .changes/unreleased/stray.yaml" in said


def test_a_release_that_moves_no_backbone_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch)
    repo.commit("only houseware", {".changes/unreleased/backbone-minor.yaml": None})
    repo.git("push", "-q", "origin", "main")

    said = _refused(_run("plan", "--pre"))

    assert "the release would move no backbone version" in said


def test_a_project_that_is_not_the_methodology_s_source_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch)
    repo.commit("an adopter's shape", {"src/project_kit/__init__.py": None})
    repo.git("push", "-q", "origin", "main")

    said = _refused(_run("plan", "--pre"))

    assert "a candidate is cut only in the methodology's source repository" in said


# --- the counter ----------------------------------------------------------------------------


def test_the_number_is_one_past_the_highest_any_candidate_tag_on_the_remote_carries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch)
    # Candidates of other versions count; a withdrawal, a final release and `latest` do not.
    _tag(repo, "v0.9.0rc4", "v1.1.0rc2", "withdrawn/v2.0.0rc9", "v3.0.0", "latest")
    # A tag this clone holds and the remote does not counts for nothing either.
    repo.git("tag", "v5.0.0rc7")

    result = _run("plan", "--pre")

    assert result.exit_code == 0, result.output
    assert "Candidate: v1.1.0rc5, number 5," in _said(result)


def test_the_number_counts_a_candidate_tag_this_clone_lacks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch)
    elsewhere = _clone(tmp_path, repo)
    _tag(elsewhere, "v1.1.0rc3")

    assert release_candidate.next_number(repo.root) == 4


def test_the_counter_refuses_where_it_cannot_read_the_remote_s_tags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch)
    repo.git("remote", "set-url", "origin", str(tmp_path / "gone.git"))

    with pytest.raises(click.ClickException) as refused:
        release_candidate.next_number(repo.root)

    said = " ".join(refused.value.message.split())
    assert said.startswith(
        "refusing to cut a candidate: the cut cannot be numbered (ADR-092 point 3): the "
        "remote's tags cannot be read: `git ls-remote --tags origin` failed (git says:"
    )
    assert said.endswith("Nothing was written.")


# --- the cut, and the base it records -------------------------------------------------------


def test_the_cut_records_its_base_and_is_held_by_its_tag_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch)
    before = repo.head()

    result = _run("apply", "--pre", "--tag", "--yes")

    assert result.exit_code == 0, result.output
    commit = repo.git("rev-parse", "v1.1.0rc1^{commit}").stdout.strip()
    assert repo.head() == commit
    assert repo.git("rev-parse", "main").stdout.strip() == before
    assert repo.git("rev-parse", f"{commit}^").stdout.strip() == before
    assert repo.git("branch", "--contains", commit).stdout.strip().startswith("* (HEAD")
    assert repo.git("ls-remote", "--tags", "origin").stdout == ""
    assert _status(repo) == ""

    base = release_candidate.parse_base(_at(repo, commit, BASE))
    assert base == release_candidate.Base(before, "1.0.0", {"houseware": "0.3.0"})
    assert _at(repo, commit, ".pkit/VERSION") == "1.1.0rc1\n"
    assert "backbone_version: 1.1.0rc1\ncompleted_version: 1.1.0rc1\n" in _at(
        repo, commit, ".pkit/manifest.yaml"
    )
    # The candidate raises no floor, and widens the upper bound as the final release does.
    assert _at(repo, commit, HOUSEWARE) == _package("0.3.1rc1", ">=1.0.0,<1.2.0")
    changelog = _at(repo, commit, "CHANGELOG.md")
    assert changelog.startswith("# Changelog\n\n## 1.1.0rc1 — ")
    assert "- **houseware 0.3.1rc1** — Uses the new command.\n" in changelog
    assert "Requires backbone" not in changelog
    assert release.lint_changelog(changelog) == []
    # No changeset is consumed.
    listed = repo.git("ls-tree", "--name-only", f"{commit}:.changes/unreleased").stdout
    assert listed.split() == ["backbone-minor.yaml", "houseware-patch.yaml"]
    assert _at(repo, "v1.1.0rc1", ".pkit/VERSION") == "1.1.0rc1\n"
    message = repo.git("tag", "--list", "--format=%(contents)", "v1.1.0rc1").stdout
    assert message.startswith("v1.1.0rc1\n\nchore(release): v1.1.0rc1")


def test_without_tag_the_cut_is_committed_and_tagged_by_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch)

    result = _run("apply", "--pre", "--yes")

    assert result.exit_code == 0, result.output
    assert repo.git("tag", "--list").stdout == ""
    assert _at(repo, "HEAD", ".pkit/VERSION") == "1.1.0rc1\n"
    assert "only a tag would hold" in _said(result)


def test_push_is_refused_with_pre(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _project(tmp_path, monkeypatch)
    before = repo.head()

    result = _run("apply", "--pre", "--tag", "--push", "--yes")

    assert result.exit_code == 1, result.output
    assert "refusing `--push` with `--pre`" in _said(result)
    assert repo.head() == before
    assert _status(repo) == ""


def test_a_tag_this_clone_holds_already_is_refused_before_anything_is_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch)
    repo.git("tag", "v1.1.0rc1")

    said = _refused(_run("apply", "--pre", "--tag", "--yes"))

    assert "this clone holds the tag v1.1.0rc1 already" in said
    assert _status(repo) == ""


def test_release_check_passes_the_candidate_s_own_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`pkit release check` refuses no candidate's own commit, the one its tag names,
    though its tree records pre-release versions (ADR-089 point 3). The cut's writes
    touch the backbone's surface with no changeset of the diff's own, so `--skip`
    waives the surface check here."""
    repo = _project(tmp_path, monkeypatch)
    assert _run("apply", "--pre", "--tag", "--yes").exit_code == 0

    result = _run("check", "--base", "main", "--skip")

    assert result.exit_code == 0, result.output
    assert release.pre_releases_bound_for_the_default_branch(repo.root / ".pkit") == []


def test_release_check_refuses_a_branch_that_took_in_a_candidate_s_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch)
    assert _run("apply", "--pre", "--tag", "--yes").exit_code == 0
    repo.checkout("main")
    repo.checkout("feature", create=True)
    repo.merge("v1.1.0rc1")

    result = _run("check", "--base", "main", "--skip")

    assert result.exit_code == 1, result.output
    said = _said(result)
    assert ".pkit/VERSION: backbone at 1.1.0rc1" in said
    assert ".pkit/capabilities/houseware/package.yaml: houseware at 0.3.1rc1" in said


def test_a_base_that_is_not_one_is_refused() -> None:
    with pytest.raises(ValueError, match="no JSON object"):
        release_candidate.parse_base("[]")
    with pytest.raises(ValueError, match="lacks its commit"):
        release_candidate.parse_base('{"commit": "abc", "components": {}}')
    with pytest.raises(ValueError, match="no version for the component"):
        release_candidate.parse_base('{"commit": "a", "backbone": "1.0.0", "components": {"x": 1}}')
