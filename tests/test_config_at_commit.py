"""A backbone configuration key at a commit, read forgivingly (ADR-057 point 2).

The reading is the commit's, never the working tree's, and it never fails: a file that
does not parse or a value the key does not take gives a warning and the default.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from project_kit.config_at_commit import KeyAtCommit, key_at
from project_kit.friction_git import CommitTree
from tests.adopter_repo import GitRepo

CONFIG = ".pkit/project/config.yaml"
KEY = "decisions.refuse-proposals"


@pytest.fixture
def repo(tmp_path: Path) -> GitRepo:
    made = GitRepo.init(tmp_path / "work")
    made.commit("start", {"a.txt": "a\n"})
    return made


def _boolean(value: object) -> bool:
    return isinstance(value, bool)


def _read(repo: GitRepo, commit: str | None = None) -> KeyAtCommit:
    tree = CommitTree(repo.root, commit or repo.head())
    return key_at(repo.root, tree, KEY, default=False, accepts=_boolean, expected="a boolean")


def test_the_key_is_read_at_the_commit_not_the_working_tree(repo: GitRepo) -> None:
    commit = repo.commit("on", {CONFIG: "decisions:\n  refuse-proposals: true\n"})
    repo.write({CONFIG: "decisions:\n  refuse-proposals: false\n"})

    found = _read(repo, commit)

    assert found.value is True and found.written and found.warning is None
    assert found.commit == commit


@pytest.mark.parametrize(
    "files",
    [
        {},
        {CONFIG: "name: x\n"},
        {CONFIG: "decisions: {}\n"},
        {CONFIG: "decisions:\n  refuse-proposal: true\n"},
    ],
    ids=["no file", "no block", "no key", "a misspelt key"],
)
def test_an_absent_key_gives_the_default_with_nothing_to_say(
    repo: GitRepo, files: dict[str, str]
) -> None:
    if files:
        repo.commit("config", files)

    found = _read(repo)

    assert found.value is False and not found.written and found.warning is None


@pytest.mark.parametrize(
    ("text", "said"),
    [
        ("decisions:\n  refuse-proposals: yes-please\n", "'yes-please' is not a boolean"),
        ("decisions: true\n", "`decisions` is not a mapping"),
        ("decisions: [\n", "reads as False"),
        ("- a\n- b\n", "reads as False"),
    ],
    ids=["a value it does not take", "a block that is no mapping", "broken YAML", "no mapping"],
)
def test_what_does_not_read_warns_and_gives_the_default(
    repo: GitRepo, text: str, said: str
) -> None:
    repo.commit("config", {CONFIG: text})

    found = _read(repo)

    assert found.value is False and not found.written
    assert found.warning is not None and said in found.warning
    assert "`pkit validate` fails on it" in found.warning
