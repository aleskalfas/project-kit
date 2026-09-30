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

import importlib
import json
import re
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from click.testing import CliRunner
from jsonschema import Draft202012Validator

from project_kit import default_branch as db
from project_kit import friction_check as fc
from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, GitRepo, MakeAdopterRepo
from tests.analysis_repo import CONFIG, NUMBERS, installed, run_script, seed

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


# --- all three readers agree ----------------------------------------------------------------


_PM_READING = """
import json, sys
sys.path.insert(0, sys.argv[1])
from _lib import default_branch, lifecycle_inference
print(json.dumps({
    "name": lifecycle_inference.resolve_base_branch({}, "EPIC: #1"),
    "check_base": default_branch.check_base()[0],
}))
"""


def _pm(repo: AdopterRepo) -> dict[str, Any]:
    """project-management's reading, run in the repository as its scripts run."""
    completed = subprocess.run(
        [sys.executable, "-c", _PM_READING, str(PM / "scripts")],
        cwd=repo.root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def _friction_base(repo: AdopterRepo) -> dict[str, Any]:
    completed = subprocess.run(
        ["pkit", "friction", "check", "--json"],
        cwd=repo.root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.stdout, completed.stderr
    return json.loads(completed.stdout)["base"]


def _numbers_base(repo: AdopterRepo) -> dict[str, Any]:
    completed = run_script(repo, NUMBERS, "--json")
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)["base"]


def _settled(repo: AdopterRepo) -> dict[str, Any]:
    completed = subprocess.run(
        ["pkit", "friction", "artefacts", "--json"],
        cwd=repo.root,
        capture_output=True,
        text=True,
        check=True,
    )
    document = json.loads(completed.stdout)
    return {"default_branch": document["default_branch"], "base": document["base"]}


@pytest.fixture
def project(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[AdopterRepo]:
    """software-analysis seeded on `main`, which then becomes `trunk`, declared the
    default branch; work goes on on `topic`, and `trunk` moves on after it left."""
    repo = installed(make_adopter_repo, monkeypatch)
    seed(repo)
    repo.commit("seeded")
    repo.git("branch", "-m", "main", TRUNK)
    _declare(repo, TRUNK, extra="docs:\n  internal: tech-docs\n")
    repo.commit("the default branch is trunk")
    repo.checkout("topic", create=True)
    repo.commit("work on topic", {"src/topic.py": "print('topic')\n"})
    repo.checkout(TRUNK)
    repo.commit("trunk moves on", {"src/trunk.py": "print('trunk')\n"})
    repo.checkout("topic")
    yield repo


def test_all_three_readers_agree_on_a_default_branch_that_is_not_main(
    project: AdopterRepo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    trunk = project.git("rev-parse", TRUNK).stdout.strip()
    fork = project.git("merge-base", TRUNK, "HEAD").stdout.strip()
    expected = {"ref": TRUNK, "tip": trunk, "commit": fork, "outdated": True}

    # No remote: the local branch, the same commit for every reader.
    assert _friction_base(project) == expected
    assert _numbers_base(project) == expected
    settled = _settled(project)
    assert settled["default_branch"] == {
        "name": TRUNK,
        "source": db.DECLARED,
        "ref": TRUNK,
        "commit": trunk,
    }
    assert (settled["base"]["ref"], settled["base"]["tip"], settled["base"]["fork"]) == (
        TRUNK,
        trunk,
        fork,
    )
    assert _pm(project) == {"name": TRUNK, "check_base": TRUNK}

    # A remote holding it: its tracking reference first, for every reader — even when
    # the local branch has moved on past it.
    _with_origin(project, tmp_path)
    project.checkout(TRUNK)
    project.commit("unpushed", {"src/unpushed.py": "print('u')\n"})
    project.checkout("topic")
    remote = {**expected, "ref": f"origin/{TRUNK}"}
    assert _friction_base(project) == remote
    assert _numbers_base(project) == remote
    assert _settled(project)["default_branch"]["ref"] == f"origin/{TRUNK}"
    assert _pm(project) == {"name": TRUNK, "check_base": f"origin/{TRUNK}"}

    # The override: the diff-scoped readers compare with it; the default branch is
    # still the declaration, for pm and for the document alike.
    monkeypatch.setenv(db.CHECK_BASE_ENV, TRUNK)
    local = {
        "ref": TRUNK,
        "tip": project.git("rev-parse", TRUNK).stdout.strip(),
        "commit": fork,
        "outdated": True,
    }
    assert _friction_base(project) == local
    assert _numbers_base(project) == local
    settled = _settled(project)
    assert (settled["base"]["ref"], settled["base"]["source"]) == (TRUNK, db.ENVIRONMENT)
    assert settled["default_branch"]["ref"] == f"origin/{TRUNK}"
    assert _pm(project) == {"name": TRUNK, "check_base": TRUNK}


# --- pm's own key, a deprecated alias --------------------------------------------------------


def _load_pm_default_branch() -> ModuleType:
    """pm's `_lib.default_branch`, imported as its scripts import it: `_lib` is on the path
    only while it loads, since another capability's `_lib` is not importable beside it."""
    scripts = str(PM / "scripts")

    def ours() -> list[str]:
        return [k for k in sys.modules if k == "_lib" or k.startswith("_lib.")]

    saved = {k: sys.modules.pop(k) for k in ours()}
    sys.path.insert(0, scripts)
    try:
        return importlib.import_module("_lib.default_branch")
    finally:
        sys.path.remove(scripts)
        for key in ours():
            del sys.modules[key]
        sys.modules.update(saved)


PM_BRANCH: Any = _load_pm_default_branch()


def _answering(name: str | None, source: str = "default") -> Any:
    """A runner standing in for `pkit friction artefacts --json`: `None` answers nothing."""

    def run(argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert argv == list(PM_BRANCH.ARGV)
        if name is None:
            return subprocess.CompletedProcess(argv, 1, "", "error: no")
        document = {
            "default_branch": {"name": name, "source": source, "ref": name, "commit": "c"},
            "base": {"ref": name, "tip": "c", "fork": "c", "problem": None},
        }
        return subprocess.CompletedProcess(argv, 0, json.dumps(document), "")

    return run


@pytest.fixture
def fresh_pm(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setattr(PM_BRANCH, "_read", {})
    monkeypatch.setattr(PM_BRANCH, "_warned", set[str]())
    return PM_BRANCH


@pytest.mark.parametrize(
    ("backbone", "alias", "expected", "warning"),
    [
        ((TRUNK, db.DECLARED), None, TRUNK, None),
        (("main", db.DEFAULTED), None, "main", None),
        (("main", db.DEFAULTED), "develop", "develop", "is deprecated: declare the default"),
        ((TRUNK, db.DECLARED), "develop", TRUNK, "is deprecated and ignored"),
        ((TRUNK, db.DECLARED), TRUNK, TRUNK, "is deprecated and redundant"),
        ((None, db.DEFAULTED), "develop", "develop", None),
        ((None, db.DEFAULTED), None, "main", None),
    ],
    ids=[
        "declared",
        "defaulted",
        "alias-while-undeclared",
        "alias-never-overrides",
        "alias-redundant",
        "unanswered-alias",
        "unanswered",
    ],
)
def test_pm_s_default_branch_is_the_backbone_s_its_own_key_an_alias(
    fresh_pm: Any,
    capsys: pytest.CaptureFixture[str],
    backbone: tuple[str | None, str],
    alias: str | None,
    expected: str,
    warning: str | None,
) -> None:
    config = {} if alias is None else {"default_branch": alias}
    run = _answering(*backbone)
    assert fresh_pm.name(config, run=run) == expected
    assert fresh_pm.name(config, run=run) == expected
    err = capsys.readouterr().err
    if warning is None:
        assert err == ""
    else:
        assert err.count("warn: ") == 1 and warning in err


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


def test_pm_reads_its_default_branch_key_in_one_place() -> None:
    """Every pm reading of `default_branch` goes through `_lib/default_branch.py`, which
    reads the backbone's first (COR-054 point 1)."""
    read = re.compile(r"\.get\(\s*['\"]default_branch['\"]")
    scripts = sorted((PM / "scripts").rglob("*.py"))
    found = [
        path.relative_to(PM).as_posix()
        for path in scripts
        if read.search(_code(path.read_text(encoding="utf-8")))
    ]
    assert found == []
