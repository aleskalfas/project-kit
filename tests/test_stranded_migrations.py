"""No release ships a stranded migration script (ADR-092 point 8).

`pkit release plan` and `apply` refuse, before writing anything, where a tier holds
a migration script in a folder at or below its fixed version that the fixed
version's commit did not hold. Each test builds a project on `main`, pushed to a
bare remote `origin`, of one of the two kinds the marker test tells apart:

- the methodology's source repository, where a tier's version is fixed at the
  first final release tag that carries the version the newest one records
- any other project, where it is fixed at the first commit of the default branch's
  first-parent history that records the version its head records
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit import changesets
from project_kit.cli import main
from project_kit.default_branch import CHECK_BASE_ENV
from project_kit.friction_git import SHORT
from tests.adopter_repo import GitRepo, sign_nothing

OWNERSHIP = Path(__file__).resolve().parents[1] / ".pkit" / "lifecycle" / "ownership.py"

BACKBONE = ".pkit/migrations/backbone"
HOUSEWARE = ".pkit/capabilities/houseware"
LENT = ".pkit/capabilities/lent"

# The project's own capability, and one it receives by a capability's install.
MANIFEST = (
    "components:\n"
    "  - kind: capability\n    name: houseware\n    origin: incubated-in-repo\n"
    "  - kind: capability\n    name: lent\n    origin: externally-sourced\n"
)


def _script(path: str) -> str:
    """A script's text, its own: no two scripts of a test share their content."""
    return f"#!/usr/bin/env bash\n# {path}\nset -euo pipefail\n"


def _scripts(*paths: str) -> dict[str, str | None]:
    return {path: _script(path) for path in paths}


def _package(name: str, version: str, *, description: str = "") -> str:
    said = f"description: {description}\n" if description else ""
    return (
        f"schema_version: 1\ncomponent:\n  kind: capability\n  name: {name}\n"
        f"  version: {version}\n{said}"
    )


def _project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, source: bool) -> GitRepo:
    """A project whose `main`, pushed to `origin`, records backbone 1.0.0, its own
    capability houseware at 0.3.0 and the capability lent, which it receives, at 0.1.0,
    each with a script in its version's folder. In the methodology's source repository
    when `source`, by the marker test: the package source beside `.pkit/`."""
    monkeypatch.delenv(CHECK_BASE_ENV, raising=False)
    repo = GitRepo.init(tmp_path / "work")
    files: dict[str, str | None] = {
        ".pkit/VERSION": "1.0.0\n",
        ".pkit/manifest.yaml": MANIFEST,
        ".pkit/lifecycle/ownership.py": OWNERSHIP.read_text(encoding="utf-8"),
        f"{HOUSEWARE}/package.yaml": _package("houseware", "0.3.0"),
        f"{LENT}/package.yaml": _package("lent", "0.1.0"),
        **_scripts(
            f"{BACKBONE}/1.0.0/001-first.sh",
            f"{HOUSEWARE}/migrations/0.3.0/001-first.sh",
            f"{LENT}/migrations/0.1.0/001-first.sh",
        ),
    }
    if source:
        files["src/project_kit/__init__.py"] = ""
    repo.commit("first", files)
    remote = tmp_path / "origin.git"
    subprocess.run(
        ["git", "init", "-q", "--bare", "--initial-branch=main", str(remote)],
        check=True,
        capture_output=True,
    )
    repo.git("remote", "add", "origin", str(remote))
    _push(repo)
    monkeypatch.chdir(repo.root)
    return repo


def _push(repo: GitRepo, *tags: str) -> None:
    """Push `main`, and each tag named, to `origin`."""
    repo.git("push", "-q", "origin", "main", *(f"refs/tags/{tag}" for tag in tags))


def _tag(repo: GitRepo, name: str, *, annotated: bool = True) -> None:
    """Tag HEAD `name` and push it with `main`: annotated, as a release tag is, or not."""
    if annotated:
        repo.git("tag", "-a", name, "-m", name)
    else:
        repo.git("tag", name)
    _push(repo, name)


def _clone(tmp_path: Path, repo: GitRepo, *args: str) -> GitRepo:
    """A clone of `repo`'s remote, made with `args`."""
    remote = repo.git("remote", "get-url", "origin").stdout.strip()
    target = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", "-q", *args, f"file://{remote}", str(target)],
        check=True,
        capture_output=True,
    )
    clone = GitRepo(target)
    clone.git("config", "user.name", "Tester")
    clone.git("config", "user.email", "tester@example.com")
    sign_nothing(target)
    return clone


def _plan(*args: str) -> Any:
    return CliRunner().invoke(main, ["release", "plan", *args])


def _refused(result: Any) -> str:
    """The refusal's text, one line per script, with what the result says it is."""
    assert result.exit_code == 1, result.output
    return " ".join(str(result.output).split())


# --- the methodology's source repository --------------------------------------------------


def test_in_the_source_a_script_added_below_the_newest_tag_s_version_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch, source=True)
    _tag(repo, "v1.0.0")
    tagged = repo.head()
    repo.commit("late", _scripts(f"{BACKBONE}/1.0.0/002-late.sh", f"{BACKBONE}/0.9.0/001-old.sh"))
    _push(repo)

    said = _refused(_plan())

    for path in (f"{BACKBONE}/1.0.0/002-late.sh", f"{BACKBONE}/0.9.0/001-old.sh"):
        folder = Path(path).parent.name
        assert (
            f"[backbone] {path}: targets {folder}, at or below backbone 1.0.0, whose scripts are "
            f"fixed at the tag v1.0.0 ({tagged[:SHORT]}). That commit does not hold the script, "
            "so no project that took 1.0.0 runs it. Move it to 1.1.0/ or a later folder."
        ) in said
    assert "refusing to release: a migration script sits in a folder at or below" in said
    assert "Nothing was written" in said
    assert "001-first.sh" not in said


def test_in_the_source_the_first_tag_that_carries_a_version_fixes_its_scripts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A script the tag v1.1.0 holds is still stranded where v1.0.0 already carried its
    tier's version: those who took the version took it there."""
    repo = _project(tmp_path, monkeypatch, source=True)
    _tag(repo, "v1.0.0")
    first = repo.head()
    repo.commit(
        "a backbone release",
        {
            ".pkit/VERSION": "1.1.0\n",
            **_scripts(
                f"{HOUSEWARE}/migrations/0.3.0/002-late.sh", f"{BACKBONE}/1.1.0/001-next.sh"
            ),
        },
    )
    _tag(repo, "v1.1.0")

    said = _refused(_plan())

    assert (
        f"[capability:houseware] {HOUSEWARE}/migrations/0.3.0/002-late.sh: targets 0.3.0, at or "
        "below capability houseware 0.3.0, whose scripts are fixed at the tag v1.0.0 "
        f"({first[:SHORT]}). That commit does not hold the script, so no project that took "
        "0.3.0 runs it. Move it to 0.4.0/ or a later folder."
    ) in said
    assert "1.1.0/001-next.sh" not in said


def test_in_the_source_a_version_no_tag_carries_fixes_nothing_and_the_move_passes_the_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A release that moved only a component reaches projects with the next tag, so the
    folder of its version is not fixed yet. The folder a refusal names is past the
    version the default branch records, which `check-diff` reads, not past the tag's."""
    repo = _project(tmp_path, monkeypatch, source=True)
    _tag(repo, "v1.0.0")
    repo.commit(
        "a component release", {f"{HOUSEWARE}/package.yaml": _package("houseware", "0.4.0")}
    )
    repo.commit("next", _scripts(f"{HOUSEWARE}/migrations/0.4.0/001-next.sh"))
    _push(repo)

    result = _plan()
    assert result.exit_code == 0, result.output

    repo.commit("late", _scripts(f"{HOUSEWARE}/migrations/0.3.0/002-late.sh"))
    _push(repo)
    said = _refused(_plan())
    assert "0.3.0/002-late.sh: targets 0.3.0, at or below capability houseware 0.3.0" in said
    assert "Move it to 0.5.0/ or a later folder." in said
    assert "0.4.0/001-next.sh" not in said


def test_in_the_source_a_candidate_s_tag_a_withdrawal_and_latest_count_for_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Read as final releases, these tags would fix 1.1.0 at the commit they name, which
    does not hold the later script."""
    repo = _project(tmp_path, monkeypatch, source=True)
    _tag(repo, "v1.0.0")
    repo.commit(
        "a candidate",
        {".pkit/VERSION": "1.1.0\n", **_scripts(f"{BACKBONE}/1.1.0/001-next.sh")},
    )
    _tag(repo, "v1.1.0rc1")
    _tag(repo, "withdrawn/v1.1.0rc1")
    _tag(repo, "latest", annotated=False)
    repo.commit("later", _scripts(f"{BACKBONE}/1.1.0/002-later.sh"))
    _push(repo)

    result = _plan()

    assert result.exit_code == 0, result.output


def test_in_the_source_a_tag_s_commit_the_clone_does_not_hold_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch, source=True)
    _tag(repo, "v1.0.0")
    elsewhere = _clone(tmp_path, repo)
    elsewhere.commit("a release made elsewhere", {".pkit/VERSION": "1.1.0\n"})
    elsewhere.git("tag", "-a", "v1.1.0", "-m", "v1.1.0")
    elsewhere.git("push", "-q", "origin", "main", "refs/tags/v1.1.0")

    said = _refused(_plan())

    assert (
        "refusing to release: whether a migration script sits in a folder at or below its "
        "tier's fixed version cannot be told (ADR-092 point 8): the remote's tag v1.1.0 names "
        f"{elsewhere.head()[:SHORT]}, a commit this clone does not hold. Fetch the tags (`git "
        "fetch --tags origin`), and run again. Nothing was written."
    ) in said


def test_in_the_source_a_shallow_clone_refuses_for_the_commit_its_history_lacks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The newest tag carries the version v1.0.0 carried first, which the clone's short
    history does not reach."""
    repo = _project(tmp_path, monkeypatch, source=True)
    _tag(repo, "v1.0.0")
    first = repo.head()
    repo.commit("a backbone release", {".pkit/VERSION": "1.1.0\n"})
    _tag(repo, "v1.1.0")
    shallow = _clone(tmp_path, repo, "--depth", "1")
    monkeypatch.chdir(shallow.root)

    said = _refused(_plan())

    assert f"the remote's tag v1.0.0 names {first[:SHORT]}, a commit this clone does not" in said


def test_in_the_source_unread_tags_refuse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _project(tmp_path, monkeypatch, source=True)
    repo.git("remote", "remove", "origin")

    said = _refused(_plan())

    assert (
        "cannot be told (ADR-092 point 8): the remote's tags cannot be read: `git ls-remote "
        "--tags origin` failed (git says:"
    ) in said


def test_in_the_source_with_no_final_tag_nothing_is_fixed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch, source=True)
    repo.commit("late", _scripts(f"{BACKBONE}/1.0.0/002-late.sh"))
    _push(repo)

    result = _plan()

    assert result.exit_code == 0, result.output


# --- every other project -------------------------------------------------------------------


def test_elsewhere_a_script_added_to_the_folder_the_default_branch_records_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch, source=False)
    first = repo.head()
    repo.commit("late", _scripts(f"{HOUSEWARE}/migrations/0.3.0/002-late.sh"))
    _push(repo)

    said = _refused(_plan())

    assert (
        f"[capability:houseware] {HOUSEWARE}/migrations/0.3.0/002-late.sh: targets 0.3.0, at or "
        f"below capability houseware 0.3.0, whose scripts are fixed at {first[:SHORT]}, the "
        "first commit of origin/main's first-parent history that records 0.3.0. That commit "
        "does not hold the script, so no project that took 0.3.0 runs it. Move it to 0.4.0/ "
        "or a later folder."
    ) in said


def test_elsewhere_a_script_not_yet_committed_is_judged_too(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch, source=False)
    repo.write(_scripts(f"{HOUSEWARE}/migrations/0.3.0/002-late.sh"))

    said = _refused(_plan())

    assert f"{HOUSEWARE}/migrations/0.3.0/002-late.sh: targets 0.3.0" in said


def test_elsewhere_the_first_commit_that_records_the_version_fixes_its_scripts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An edit to the tier's package that keeps its version moves nothing."""
    repo = _project(tmp_path, monkeypatch, source=False)
    released = repo.commit(
        "a release",
        {
            f"{HOUSEWARE}/package.yaml": _package("houseware", "0.4.0"),
            **_scripts(f"{HOUSEWARE}/migrations/0.4.0/001-next.sh"),
        },
    )
    repo.commit(
        "described",
        {f"{HOUSEWARE}/package.yaml": _package("houseware", "0.4.0", description="Houses.")},
    )
    repo.commit("late", _scripts(f"{HOUSEWARE}/migrations/0.4.0/002-late.sh"))
    _push(repo)

    said = _refused(_plan())

    assert (
        f"whose scripts are fixed at {released[:SHORT]}, the first commit of origin/main's "
        "first-parent history that records 0.4.0"
    ) in said
    assert "0.4.0/002-late.sh: targets 0.4.0" in said
    assert "Move it to 0.5.0/ or a later folder." in said
    assert "001-next.sh" not in said


def test_elsewhere_a_version_merged_from_a_branch_is_fixed_at_the_merge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Those who pin the default branch take the version at the merge, which holds every
    script its branch wrote, the one written after the version moved too."""
    repo = _project(tmp_path, monkeypatch, source=False)
    repo.git("checkout", "-q", "-b", "topic")
    repo.commit(
        "a release",
        {
            f"{HOUSEWARE}/package.yaml": _package("houseware", "0.4.0"),
            **_scripts(f"{HOUSEWARE}/migrations/0.4.0/001-next.sh"),
        },
    )
    repo.commit("later", _scripts(f"{HOUSEWARE}/migrations/0.4.0/002-later.sh"))
    repo.git("checkout", "-q", "main")
    repo.git("merge", "-q", "--no-ff", "-m", "merge topic", "topic")
    _push(repo)

    result = _plan()

    assert result.exit_code == 0, result.output


def test_elsewhere_a_script_above_the_recorded_version_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch, source=False)
    repo.commit("next", _scripts(f"{HOUSEWARE}/migrations/0.4.0/001-next.sh"))
    _push(repo)

    result = _plan()

    assert result.exit_code == 0, result.output


def test_elsewhere_an_unresolved_default_branch_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch, source=False)
    repo.git("update-ref", "-d", "refs/remotes/origin/main")

    said = _refused(_plan())

    assert (
        "cannot be told (ADR-092 point 8): the default branch 'main' resolves to no commit here"
    ) in said


def test_elsewhere_a_shallow_clone_refuses(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _project(tmp_path, monkeypatch, source=False)
    repo.commit("next", _scripts(f"{HOUSEWARE}/migrations/0.4.0/001-next.sh"))
    _push(repo)
    shallow = _clone(tmp_path, repo, "--depth", "1")
    monkeypatch.chdir(shallow.root)

    said = _refused(_plan())

    assert (
        "cannot be told (ADR-092 point 8): this clone is shallow, so the first commit of the "
        "default branch's history that records a tier's version may not be here. Fetch the "
        "whole history (`git fetch --unshallow`), and run again. Nothing was written."
    ) in said


# --- what the guard passes by --------------------------------------------------------------


@pytest.mark.parametrize("source", [True, False], ids=["source", "elsewhere"])
def test_a_script_the_project_receives_is_passed_by(
    source: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The capability the project receives by its install, and elsewhere the backbone it
    receives by sync, are judged where they are authored."""
    repo = _project(tmp_path, monkeypatch, source=source)
    _tag(repo, "v1.0.0")
    received = [f"{LENT}/migrations/0.1.0/002-late.sh"]
    if not source:
        received.append(f"{BACKBONE}/1.0.0/002-late.sh")
    repo.commit("late", _scripts(*received))
    _push(repo)

    result = _plan()

    assert result.exit_code == 0, result.output


@pytest.mark.parametrize("source", [True, False], ids=["source", "elsewhere"])
def test_a_project_without_scripts_of_its_own_reads_neither_tags_nor_history(
    source: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no remote and no default branch, a read of either would refuse."""
    repo = _project(tmp_path, monkeypatch, source=source)
    repo.git("rm", "-q", "-r", f"{HOUSEWARE}/migrations", f"{BACKBONE}")
    repo.commit("only received scripts")
    repo.git("remote", "remove", "origin")
    repo.git("branch", "-q", "-m", "main", "other")

    result = _plan()

    assert result.exit_code == 0, result.output


# --- the commands ---------------------------------------------------------------------------


def test_plan_its_json_and_apply_each_refuse_before_anything_is_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch, source=False)
    repo.commit("late", _scripts(f"{HOUSEWARE}/migrations/0.3.0/002-late.sh"))
    _push(repo)
    pending = changesets.unreleased_dir(repo.root) / "a.yaml"
    pending.parent.mkdir(parents=True)
    pending.write_text("component: houseware\nkind: minor\nbody: A change.\n", encoding="utf-8")
    package = (repo.root / HOUSEWARE / "package.yaml").read_text(encoding="utf-8")

    for args in (["release", "plan"], ["release", "plan", "--json"], ["release", "apply", "--yes"]):
        said = _refused(CliRunner().invoke(main, args))
        assert f"{HOUSEWARE}/migrations/0.3.0/002-late.sh: targets 0.3.0" in said
        assert "Release plan" not in said

    assert (repo.root / HOUSEWARE / "package.yaml").read_text(encoding="utf-8") == package
    assert pending.is_file()
    assert not (repo.root / "CHANGELOG.md").exists()
