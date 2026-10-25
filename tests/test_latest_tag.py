"""`scripts/latest_tag.py` keeps the tag `latest` on the newest release's commit (#2052).

Each test builds a repository fixture: a bare `origin` and a clone that cuts
annotated release tags and pushes them, as the release-tag workflow does. The
script then reads `origin`'s tags and points `latest` at the commit of the
highest release tag: it creates the tag where it is missing, moves it where it
lags, and pushes nothing where it already points there (PRJ-004).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML
from scripts import latest_tag

from project_kit import install, upgrade
from tests.adopter_repo import GitRepo

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "release-tag.yml"
LATEST = latest_tag.LATEST


@pytest.fixture
def clone(tmp_path: Path) -> GitRepo:
    """A clone whose `origin` is a bare repository holding its first commit."""
    origin = tmp_path / "origin.git"
    GitRepo(tmp_path).git("init", "--bare", "-q", str(origin))
    repo = GitRepo.init(tmp_path / "clone")
    repo.git("remote", "add", "origin", str(origin))
    repo.commit("Start", {"README.md": "start\n"})
    repo.git("push", "-q", "origin", "main")
    return repo


@pytest.fixture
def in_a_workflow(monkeypatch: pytest.MonkeyPatch) -> None:
    """The run counts as a GitHub Actions run, where `--push` is allowed."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")


def _release(repo: GitRepo, tag: str) -> str:
    """Commit, cut `tag` as the release step does (annotated), push both; return
    the commit's SHA."""
    sha = repo.commit(f"Release {tag}", {"VERSION": f"{tag}\n"})
    repo.git("tag", "-a", tag, "-m", tag)
    repo.git("push", "-q", "origin", "main", tag)
    return sha


def _point_latest_on_origin(repo: GitRepo, sha: str) -> None:
    """Put `origin`'s `latest` on `sha`, as an earlier run of the workflow did."""
    repo.git("push", "-q", "--force", "origin", f"{sha}:refs/tags/latest")


def _latest_on_origin(repo: GitRepo) -> str | None:
    """The commit `origin`'s `latest` points at, or None where it has none."""
    listed = repo.git("ls-remote", "--tags", "origin", "latest").stdout.split()
    return listed[0] if listed else None


# --- Missing, lagging, current ---------------------------------------------


def test_it_creates_latest_where_origin_has_none(clone: GitRepo, in_a_workflow: None) -> None:
    _release(clone, "v1.0.0")
    newest = _release(clone, "v1.1.0")

    assert latest_tag.run(clone.root, push=True) == 0

    assert _latest_on_origin(clone) == newest


def test_it_moves_latest_where_it_lags(clone: GitRepo, in_a_workflow: None) -> None:
    older = _release(clone, "v1.0.0")
    _point_latest_on_origin(clone, older)
    newest = _release(clone, "v1.1.0")

    assert latest_tag.run(clone.root, push=True) == 0

    assert _latest_on_origin(clone) == newest


def test_it_pushes_nothing_where_latest_already_points_there(
    clone: GitRepo, in_a_workflow: None, capsys: pytest.CaptureFixture[str]
) -> None:
    newest = _release(clone, "v1.1.0")
    _point_latest_on_origin(clone, newest)

    plan = latest_tag.read(clone.root)

    assert plan.release == "v1.1.0"
    assert not plan.needed
    assert latest_tag.run(clone.root, push=True) == 0
    assert "already points at v1.1.0" in capsys.readouterr().out
    assert _latest_on_origin(clone) == newest


def test_a_second_run_finds_nothing_to_do(clone: GitRepo, in_a_workflow: None) -> None:
    """Idempotent: the run after a move reads `latest` where the move left it."""
    _release(clone, "v1.0.0")
    latest_tag.run(clone.root, push=True)

    assert not latest_tag.read(clone.root).needed


# --- Which tag is the newest release ---------------------------------------


def test_it_skips_pre_releases_and_tags_that_are_no_release(
    clone: GitRepo, in_a_workflow: None
) -> None:
    """A pre-release above the newest release, a padded version and a tag of
    another name never count: `latest` goes to the newest release."""
    release = _release(clone, "v1.0.0")
    _release(clone, "v1.1.0rc1")
    _release(clone, "v01.2.0")
    _release(clone, "nightly")

    assert latest_tag.run(clone.root, push=True) == 0

    assert _latest_on_origin(clone) == release


def test_the_highest_version_wins_whatever_order_it_was_tagged_in(
    clone: GitRepo, in_a_workflow: None
) -> None:
    """`v1.10.0` is above `v1.9.0` though cut first and sorted after it as text."""
    highest = _release(clone, "v1.10.0")
    _release(clone, "v1.9.0")

    latest_tag.run(clone.root, push=True)

    assert _latest_on_origin(clone) == highest


def test_with_no_release_tag_it_pushes_nothing(
    clone: GitRepo, in_a_workflow: None, capsys: pytest.CaptureFixture[str]
) -> None:
    _release(clone, "v1.0.0rc1")

    assert latest_tag.run(clone.root, push=True) == 0

    assert "no release tag" in capsys.readouterr().out
    assert _latest_on_origin(clone) is None


def test_a_clone_holding_an_old_latest_moves_it_only_by_a_forced_fetch(
    clone: GitRepo, in_a_workflow: None, tmp_path: Path
) -> None:
    """git moves no tag a clone already holds: the command reference's
    `git fetch --force origin tag latest` is what brings a moved one in."""
    _release(clone, "v1.0.0")
    latest_tag.run(clone.root, push=True)
    other = GitRepo(tmp_path / "other")
    GitRepo(tmp_path).git("clone", "-q", str(tmp_path / "origin.git"), str(other.root))
    newest = _release(clone, "v1.1.0")
    latest_tag.run(clone.root, push=True)

    assert other.git("fetch", "-q", "origin", "tag", LATEST, check=False).returncode != 0
    other.git("fetch", "-q", "--force", "origin", "tag", LATEST)

    assert other.git("rev-parse", f"{LATEST}^{{commit}}").stdout.strip() == newest


# --- Only the workflow pushes ----------------------------------------------


def test_without_push_it_says_what_it_would_do_and_changes_nothing(
    clone: GitRepo, capsys: pytest.CaptureFixture[str]
) -> None:
    older = _release(clone, "v1.0.0")
    _point_latest_on_origin(clone, older)
    _release(clone, "v1.1.0")

    assert latest_tag.run(clone.root, push=False) == 0

    assert "Would move `latest` on origin to v1.1.0" in capsys.readouterr().out
    assert _latest_on_origin(clone) == older


def test_push_outside_github_actions_is_refused(
    clone: GitRepo, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.chdir(clone.root)
    _release(clone, "v1.0.0")

    assert latest_tag.main(["--push"]) == 1

    assert "only the workflow" in capsys.readouterr().err
    assert _latest_on_origin(clone) is None


def test_a_run_that_read_an_older_state_never_moves_latest_back(
    clone: GitRepo, in_a_workflow: None
) -> None:
    """The push is leased on the value the run read. Where another run moved
    `latest` in between, this run's push is refused and `latest` stays."""
    _point_latest_on_origin(clone, _release(clone, "v1.0.0"))
    _release(clone, "v1.1.0")
    plan = latest_tag.read(clone.root)
    assert plan.needed
    newer = _release(clone, "v1.2.0")
    _point_latest_on_origin(clone, newer)

    with pytest.raises(latest_tag.Refused):
        latest_tag.apply(clone.root, plan)

    assert _latest_on_origin(clone) == newer


def test_a_run_that_found_latest_missing_never_overwrites_one_made_since(
    clone: GitRepo, in_a_workflow: None
) -> None:
    _release(clone, "v1.0.0")
    plan = latest_tag.read(clone.root)
    newer = _release(clone, "v1.1.0")
    _point_latest_on_origin(clone, newer)

    with pytest.raises(latest_tag.Refused):
        latest_tag.apply(clone.root, plan)

    assert _latest_on_origin(clone) == newer


# --- The same judgement as `pkit upgrade` -----------------------------------

_TAGS = (
    "v1.0.0",
    "v1.9.0",
    "v1.10.0",
    "v2.0.0rc1",
    "v2.0.0.dev1",
    "v2.0.0.post1",
    "v2.0.0+build",
    "v02.0.0",
    "v2.0",
    "v-broken",
    "not-a-version",
    "latest",
)


def _ls_remote(*tags: str) -> str:
    sha = "0" * 40
    return "".join(f"{sha}\trefs/tags/{tag}\n{sha}\trefs/tags/{tag}^{{}}\n" for tag in tags)


@pytest.mark.parametrize("tag", _TAGS)
def test_a_tag_is_a_release_here_exactly_where_pkit_upgrade_takes_it_for_one(tag: str) -> None:
    """`pkit upgrade` finds the latest release with `_max_released_tag`; this
    script, which needs the standard library alone, judges each tag the same."""
    found = upgrade._max_released_tag(_ls_remote(tag))
    assert latest_tag.newest_release([tag]) == (None if found is None else f"v{found}")


def test_the_newest_release_is_the_one_pkit_upgrade_finds() -> None:
    found = upgrade._max_released_tag(_ls_remote(*_TAGS))
    assert latest_tag.newest_release(_TAGS) == f"v{found}" == "v1.10.0"


def test_the_tag_is_the_one_init_recommends() -> None:
    assert install.recommended_install_command().endswith(f"@{latest_tag.LATEST}")


# --- The workflow ------------------------------------------------------------


def _steps() -> list[dict[str, Any]]:
    workflow = YAML(typ="safe").load(WORKFLOW.read_text(encoding="utf-8"))
    return workflow["jobs"]["tag"]["steps"]


def _index(steps: list[dict[str, Any]], runs: str) -> int:
    (index,) = [i for i, step in enumerate(steps) if runs in step.get("run", "")]
    return index


def test_the_release_tag_workflow_points_latest_on_every_run() -> None:
    """The step has no condition, so a push that cut no tag still mends a
    `latest` an earlier run failed to move, and it comes after the tag is cut."""
    steps = _steps()
    point = _index(steps, "python scripts/latest_tag.py --push")

    assert "if" not in steps[point]
    assert point > _index(steps, "pkit version tag --push")


def test_the_python_the_step_runs_on_is_set_up_on_every_run() -> None:
    steps = _steps()
    (setup,) = [s for s in steps if s.get("uses", "").startswith("actions/setup-python@")]

    assert "if" not in setup
    assert steps.index(setup) < _index(steps, "python scripts/latest_tag.py --push")
