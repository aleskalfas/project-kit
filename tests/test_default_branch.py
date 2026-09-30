"""One meaning of the default branch for every reader of settled state (COR-054, #1128).

The default branch is declared once — `repository.default-branch` in the
backbone configuration, `main` when absent — resolved one way, remote-tracking
reference first, and never guessed (`project_kit.default_branch`). A base named
for one run — `--base`, else `$PKIT_CHECK_BASE` — replaces it as a comparison's
base and nothing else. The readers agree because they read the one answer:

- the friction change check (`pkit friction check`), through `resolve_base`;
- software-analysis' number check and stamp, through `pkit friction artefacts
  --json`'s `base`;
- project-management's default branch and its documentation check's default
  base, through the same document, pm's own `default_branch` a deprecated alias.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from jsonschema import Draft202012Validator

from project_kit import default_branch as db
from project_kit import friction_check as fc
from project_kit.cli import main
from tests.adopter_repo import GitRepo
from tests.analysis_repo import CONFIG

# The guard's reading of a script's code, shared rather than copied.
from tests.test_living_docs_spaces import _code  # pyright: ignore[reportPrivateUsage]

REPO = Path(__file__).resolve().parent.parent
SCHEMA = REPO / ".pkit" / "schemas" / "backbone" / "config.schema.json"
PM = REPO / ".pkit" / "capabilities" / "project-management"
SA = REPO / ".pkit" / "capabilities" / "software-analysis"

#: A default branch that is not `main`, so nothing hard-coded can pass.
TRUNK = "trunk"


@pytest.fixture(autouse=True)
def no_check_base_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """A developer's own `$PKIT_CHECK_BASE` must not decide what these repositories answer."""
    monkeypatch.delenv(db.CHECK_BASE_ENV, raising=False)


def _declare(repo: GitRepo, name: str, *, extra: str = "") -> None:
    repo.write({CONFIG: f"{extra}repository:\n  default-branch: {name}\n"})


def _repo(tmp_path: Path, branch: str = "main") -> GitRepo:
    repo = GitRepo.init(tmp_path / "work", branch=branch)
    repo.commit("first", {"README.md": "one\n"})
    return repo


def _with_origin(repo: GitRepo, tmp_path: Path) -> Path:
    """A remote `origin` holding the repository as it stands, fetched."""
    remote = tmp_path / "origin.git"
    subprocess.run(
        ["git", "clone", "-q", "--bare", str(repo.root), str(remote)],
        check=True,
        capture_output=True,
    )
    repo.git("remote", "add", "origin", str(remote))
    repo.git("fetch", "-q", "origin")
    return remote


# --- the declaration (point 1) -------------------------------------------------------------


def test_absent_the_default_branch_is_main(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    branch = db.resolve(repo.root)
    assert (branch.name, branch.source, branch.ref, branch.warning) == (
        "main",
        db.DEFAULTED,
        "main",
        None,
    )
    assert branch.commit == repo.head()


def test_a_declared_name_is_read(tmp_path: Path) -> None:
    repo = _repo(tmp_path, TRUNK)
    _declare(repo, TRUNK)
    branch = db.resolve(repo.root)
    assert (branch.name, branch.source, branch.ref) == (TRUNK, db.DECLARED, TRUNK)


@pytest.mark.parametrize("written", ['"-x"', "two words", '""', "7", "[main]"])
def test_a_value_that_is_not_a_branch_name_reads_as_main_and_says_so(
    tmp_path: Path, written: str
) -> None:
    """Forgiving when read (COR-048 point 4): the default, and a warning the reading
    commands print — the schema refuses the same values, so validation fails on them."""
    repo = _repo(tmp_path)
    repo.write({CONFIG: f"repository:\n  default-branch: {written}\n"})
    branch = db.resolve(repo.root)
    assert (branch.name, branch.source) == ("main", db.DEFAULTED)
    assert branch.warning is not None and "is not a branch name; read as 'main'" in branch.warning


def test_the_schema_takes_the_names_the_reader_takes() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator: Any = Draft202012Validator(schema)
    key = schema["$defs"]["repository"]["properties"]["default-branch"]
    assert key["pattern"] == db.BRANCH_NAME.pattern
    for name in ("main", "trunk", "release/2", "integration/508-x"):
        assert list(validator.iter_errors({"repository": {"default-branch": name}})) == []
    for name in ("-x", "two words", "", 7):
        assert list(validator.iter_errors({"repository": {"default-branch": name}}))
    assert list(validator.iter_errors({"repository": {"default_branch": "main"}}))


# --- the resolution (points 2 and 4) --------------------------------------------------------


def test_the_remote_tracking_reference_comes_first(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _with_origin(repo, tmp_path)
    pushed = repo.head()
    repo.commit("local only", {"README.md": "two\n"})
    branch = db.resolve(repo.root)
    assert (branch.ref, branch.commit) == ("origin/main", pushed)


def test_the_local_branch_when_no_remote_holds_it(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    branch = db.resolve(repo.root)
    assert (branch.ref, branch.commit, branch.problem) == ("main", repo.head(), None)


def test_a_tag_of_the_same_name_never_stands_in_for_the_branch(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    repo.git("tag", TRUNK)
    _declare(repo, TRUNK)
    assert (db.resolve(repo.root).ref, db.resolve(repo.root).commit) == (None, None)


def test_neither_resolving_is_reported_never_guessed(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _declare(repo, TRUNK)
    branch = db.resolve(repo.root)
    assert (branch.ref, branch.commit) == (None, None)
    assert branch.problem is not None
    assert "the default branch 'trunk' resolves neither as 'origin/trunk' nor as 'trunk'" in (
        branch.problem
    )
    assert "`repository.default-branch`" in branch.problem
    base = db.base(repo.root)
    assert (base.ref, base.source, base.tip, base.problem) == (
        TRUNK,
        db.DEFAULT_BRANCH,
        None,
        branch.problem,
    )
    with pytest.raises(fc.FrictionCheckError, match="resolves neither as 'origin/trunk'"):
        fc.resolve_base(repo.root)


def test_no_git_is_an_answer_without_commits(tmp_path: Path) -> None:
    branch = db.resolve(tmp_path)
    assert (branch.name, branch.commit) == ("main", None)
    assert db.base(tmp_path).problem is not None


# --- the override is a base, not a declaration (point 3) --------------------------------------


def test_the_base_is_named_else_the_environment_else_the_default_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path, TRUNK)
    _declare(repo, TRUNK)
    repo.commit("declared")
    repo.git("branch", "other")
    assert (db.base(repo.root).ref, db.base(repo.root).source) == (TRUNK, db.DEFAULT_BRANCH)
    monkeypatch.setenv(db.CHECK_BASE_ENV, "other")
    assert (db.base(repo.root).ref, db.base(repo.root).source) == ("other", db.ENVIRONMENT)
    assert (db.base(repo.root, "HEAD").ref, db.base(repo.root, "HEAD").source) == (
        "HEAD",
        db.OPTION,
    )
    assert db.resolve(repo.root).name == TRUNK  # the override never redefines it


def test_the_base_names_its_tip_and_where_head_left_it(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    fork = repo.head()
    repo.checkout("topic", create=True)
    repo.commit("topic", {"topic.md": "t\n"})
    repo.checkout("main")
    tip = repo.commit("main moved on", {"main.md": "m\n"})
    repo.checkout("topic")
    base = db.base(repo.root)
    assert (base.ref, base.tip, base.fork, base.outdated, base.problem) == (
        "main",
        tip,
        fork,
        True,
        None,
    )


# --- the reading command (point 5) ---------------------------------------------------------


def _artefacts(*args: str) -> dict[str, Any]:
    result = CliRunner().invoke(main, ["friction", "artefacts", "--json", *args])
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


def test_the_artefacts_document_names_the_default_branch_and_the_base(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    monkeypatch.chdir(repo.root)
    document = _artefacts()
    assert document["default_branch"] == {
        "name": "main",
        "source": db.DEFAULTED,
        "ref": "main",
        "commit": repo.head(),
    }
    assert document["base"] == {
        "ref": "main",
        "source": db.DEFAULT_BRANCH,
        "tip": repo.head(),
        "fork": repo.head(),
        "outdated": False,
        "problem": None,
    }
    at_head = _artefacts("--at", "HEAD", "--base=-x")
    assert at_head["base"]["problem"] == "the base '-x' is not a revision name."
    assert at_head["default_branch"] == document["default_branch"]


def test_the_human_view_says_which_branch_and_which_base(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    monkeypatch.chdir(repo.root)
    result = CliRunner().invoke(main, ["friction", "artefacts"])
    assert result.exit_code == 0, result.output
    short = repo.head()[:12]
    assert f"Default branch: main (default) → main at {short}" in result.output
    assert f"Base: main (the default branch) at {short}; HEAD left it at {short}" in (result.output)


def test_a_value_read_as_the_default_is_warned_about(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    repo.write({CONFIG: "repository:\n  default-branch: two words\n"})
    monkeypatch.chdir(repo.root)
    result = CliRunner().invoke(main, ["friction", "check", "--json"])
    assert "warning: repository.default-branch 'two words' is not a branch name" in (result.stderr)


# --- no reader resolves on its own -----------------------------------------------------------

#: What resolving a base by hand takes, in a script's code.
_BASE_TOKENS = {
    r"environ\b[^\n]*CHECK_BASE|getenv\(": "reading $PKIT_CHECK_BASE",
    r"['\"]merge-base['\"]": "computing a merge-base",
    r"f?['\"]origin/": "naming a remote-tracking reference",
    r"default-branch": "reading the declaration",
}


def _base_tokens(text: str) -> list[str]:
    code = _code(text)
    return [meaning for token, meaning in _BASE_TOKENS.items() if re.search(token, code)]


def test_the_guard_recognises_a_base_resolved_by_hand() -> None:
    ported = (
        "import os\n"
        "base = os.environ.get('PKIT_CHECK_BASE') or 'origin/main'\n"
        "fork = git('merge-base', base, 'HEAD')\n"
    )
    assert _base_tokens(ported) == [
        "reading $PKIT_CHECK_BASE",
        "computing a merge-base",
        "naming a remote-tracking reference",
    ]
    assert _base_tokens('"""PKIT_CHECK_BASE, merge-base and origin/main, in prose."""\n') == []


def test_software_analysis_resolves_no_base_of_its_own() -> None:
    """Its scripts read the base in `pkit friction artefacts --json` (COR-054 point 5)."""
    scripts = sorted((SA / "scripts").rglob("*.py"))
    assert scripts
    found = {
        path.relative_to(SA).as_posix(): tokens
        for path in scripts
        if (tokens := _base_tokens(path.read_text(encoding="utf-8")))
    }
    assert found == {}
