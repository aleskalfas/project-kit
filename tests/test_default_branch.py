"""One meaning of the default branch for every reader of settled state (COR-054, #1128).

The default branch is declared once — `repository.default-branch` in the
backbone configuration, `main` when absent — and resolved one way
(`project_kit.default_branch`): the remote-tracking reference of the branch's
upstream, else `origin/<name>`, and the local branch only when there is no
remote, which every reader says. Nothing is guessed. A base named for one run —
`--base`, else `$PKIT_CHECK_BASE` — replaces it as a comparison's base and
nothing else; any branch named as a base resolves the same way. The readers
agree because they read the one answer:

- the friction change check (`pkit friction check`), through `resolve_base`,
  and the migration and changeset checks, through the CLI's base;
- software-analysis' number check and stamp, through `pkit repository base
  --json`;
- project-management's default branch, the bases its verbs cut from and count
  from, and its documentation check's base, through the same command.
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
from tests.test_living_docs_spaces import _code

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


def _bare(tmp_path: Path, repo: GitRepo, name: str = "origin.git") -> Path:
    """A bare copy of the repository as it stands."""
    remote = tmp_path / name
    subprocess.run(
        ["git", "clone", "-q", "--bare", str(repo.root), str(remote)],
        check=True,
        capture_output=True,
    )
    return remote


def _with_remote(repo: GitRepo, tmp_path: Path, name: str = "origin") -> Path:
    """A remote `name` holding the repository as it stands, fetched."""
    remote = _bare(tmp_path, repo, f"{name}.git")
    repo.git("remote", "add", name, str(remote))
    repo.git("fetch", "-q", name)
    return remote


def _clone(tmp_path: Path, source: Path | str, *args: str, name: str = "clone") -> GitRepo:
    target = tmp_path / name
    subprocess.run(
        ["git", "clone", "-q", *args, str(source), str(target)],
        check=True,
        capture_output=True,
    )
    clone = GitRepo(target)
    clone.git("config", "user.name", "Tester")
    clone.git("config", "user.email", "tester@example.com")
    clone.git("config", "commit.gpgsign", "false")
    return clone


def _rev(repo: GitRepo, name: str) -> str:
    return repo.git("rev-parse", name).stdout.strip()


# --- the declaration (point 1) -------------------------------------------------------------


def test_absent_the_default_branch_is_main(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    branch = db.resolve(repo.root)
    assert (branch.name, branch.source, branch.ref, branch.resolved, branch.warning) == (
        "main",
        db.DEFAULTED,
        "main",
        db.RESOLVED_LOCAL,
        None,
    )
    assert branch.commit == repo.head()


def test_a_declared_name_is_read(tmp_path: Path) -> None:
    repo = _repo(tmp_path, TRUNK)
    _declare(repo, TRUNK)
    branch = db.resolve(repo.root)
    assert (branch.name, branch.source, branch.ref) == (TRUNK, db.DECLARED, TRUNK)


#: Values the declaration never takes: no branch name git accepts, or a reference.
NOT_BRANCH_NAMES = [
    '"-x"',
    "two words",
    '""',
    "7",
    "[main]",
    "origin/main",
    "refs/heads/main",
    "HEAD",
    "a..b",
    "a.lock",
    "release/",
    "'x:y'",
    "'x~1'",
]


@pytest.mark.parametrize("written", NOT_BRANCH_NAMES)
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
    names = ("main", "trunk", "release/2", "integration/508-x", "upstream/main", "v1.2")
    for name in names:
        assert db.is_branch_name(name)
        assert list(validator.iter_errors({"repository": {"default-branch": name}})) == []
    refused = ("-x", "two words", "", "origin/main", "refs/heads/x", "HEAD", "a..b", "a/.b")
    for name in (*refused, "a.lock", "a/", "a.", "a~b", "a^b", "a:b", "a?b", "a*b", "a[b", "/a"):
        assert not db.is_branch_name(name), name
        assert list(validator.iter_errors({"repository": {"default-branch": name}})), name
    assert list(validator.iter_errors({"repository": {"default-branch": 7}}))
    assert list(validator.iter_errors({"repository": {"default_branch": "main"}}))


# --- the resolution (points 2 and 4) --------------------------------------------------------


def test_the_remote_tracking_reference_comes_first(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _with_remote(repo, tmp_path)
    pushed = repo.head()
    repo.commit("local only", {"README.md": "two\n"})
    branch = db.resolve(repo.root)
    assert (branch.ref, branch.commit, branch.resolved) == (
        "origin/main",
        pushed,
        db.RESOLVED_REMOTE,
    )
    assert db.warnings(repo.root) == []


def test_the_upstream_names_a_remote_not_called_origin(tmp_path: Path) -> None:
    """The remote the shared work is pushed to, whatever it is called: the branch's upstream."""
    source = _repo(tmp_path)
    clone = _clone(tmp_path, source.root)
    clone.git("remote", "rename", "origin", "shared")
    pushed = clone.head()
    clone.commit("local only", {"README.md": "two\n"})
    branch = db.resolve(clone.root)
    assert (branch.ref, branch.commit, branch.resolved) == (
        "shared/main",
        pushed,
        db.RESOLVED_REMOTE,
    )


def test_a_remote_not_called_origin_that_nothing_tracks_is_the_stated_limit(
    tmp_path: Path,
) -> None:
    """With no upstream and no `origin`, the reader cannot find the shared remote: it takes
    the local branch, and says so (COR-054, Implications)."""
    repo = _repo(tmp_path)
    _with_remote(repo, tmp_path, name="shared")
    branch = db.resolve(repo.root)
    assert (branch.ref, branch.resolved) == ("main", db.RESOLVED_LOCAL)
    assert any("is read from the local branch 'main'" in w for w in db.warnings(repo.root))


def test_in_a_fork_layout_the_tracked_remote_wins_over_origin(tmp_path: Path) -> None:
    """`origin` is your fork, whose `main` lags; `upstream` is the shared repository, and
    your `main` tracks it: the shared work is `upstream/main`."""
    canonical = _repo(tmp_path)
    upstream = _bare(tmp_path, canonical, "canonical.git")
    fork = _bare(tmp_path, canonical, "fork.git")
    clone = _clone(tmp_path, fork)
    clone.git("remote", "add", "upstream", str(upstream))
    canonical.commit("landed upstream", {"up.md": "u\n"})
    canonical.git("push", "-q", str(upstream), "main")
    clone.git("fetch", "-q", "upstream")
    clone.git("branch", "-q", "--set-upstream-to=upstream/main", "main")
    branch = db.resolve(clone.root)
    assert (branch.ref, branch.commit) == ("upstream/main", canonical.head())
    assert _rev(clone, "origin/main") != canonical.head()


def test_the_local_branch_when_there_is_no_remote_and_it_says_so(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    branch = db.resolve(repo.root)
    assert (branch.ref, branch.commit, branch.resolved, branch.problem) == (
        "main",
        repo.head(),
        db.RESOLVED_LOCAL,
        None,
    )
    assert db.warnings(repo.root) == [
        "the default branch 'main' is read from the local branch 'main': this repository has "
        "no remote to read the shared one from, and a local branch can lag it or carry work "
        "nobody pushed (COR-054 point 2)"
    ]


def test_a_tag_of_the_same_name_never_stands_in_for_the_branch(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    repo.git("tag", TRUNK)
    _declare(repo, TRUNK)
    assert (db.resolve(repo.root).ref, db.resolve(repo.root).commit) == (None, None)


def test_a_stale_main_after_the_host_renamed_the_branch_is_never_read(tmp_path: Path) -> None:
    """The host renamed `main` to `trunk`; a fetch pruned `origin/main`. The clone's own
    `main` still tracks it, stale: the reader reports, with the fetch and the declaration
    to fix it, and never reads the local branch while a remote holds the shared one."""
    source = _repo(tmp_path)
    remote = _bare(tmp_path, source)
    clone = _clone(tmp_path, remote)
    stale = clone.head()
    subprocess.run(
        ["git", "branch", "-m", "main", TRUNK], cwd=remote, check=True, capture_output=True
    )
    clone.git("fetch", "-q", "--prune", "origin")
    branch = db.resolve(clone.root)
    assert (branch.ref, branch.commit, branch.resolved) == (None, None, None)
    assert branch.problem == (
        "the default branch 'main' resolves to no commit here: 'origin/main' names none — fetch "
        "it (`git fetch origin main`), declare the right one (`repository.default-branch` in "
        ".pkit/project/config.yaml), or name a base with --base or PKIT_CHECK_BASE. The local "
        "branch 'main' is not read while a remote holds the shared one — it can lag it or carry "
        "work nobody pushed; to compare with it anyway, name `refs/heads/main` as the base."
    )
    assert _rev(clone, "refs/heads/main") == stale
    found = db.base(clone.root)
    assert (found.tip, found.problem) == (None, branch.problem)
    _declare(clone, TRUNK)
    assert (db.resolve(clone.root).ref, db.resolve(clone.root).commit) == (
        f"origin/{TRUNK}",
        _rev(clone, f"origin/{TRUNK}"),
    )


def test_a_remote_without_its_copy_is_reported_not_read_locally(tmp_path: Path) -> None:
    """`origin` is configured but never fetched; the local `main` is there and may lag."""
    repo = _repo(tmp_path)
    remote = _bare(tmp_path, repo)
    repo.git("remote", "add", "origin", str(remote))
    branch = db.resolve(repo.root)
    assert branch.commit is None
    assert branch.problem is not None and "fetch it (`git fetch origin main`)" in branch.problem
    assert "is not read while a remote holds the shared one" in branch.problem
    repo.git("fetch", "-q", "origin")
    assert db.resolve(repo.root).ref == "origin/main"


def test_a_narrow_clone_names_the_fetch_that_brings_the_default_branch(tmp_path: Path) -> None:
    """A clone of one branch — what a pipeline often checks out — holds no `origin/main`."""
    source = _repo(tmp_path)
    source.checkout("topic", create=True)
    source.commit("topic", {"topic.md": "t\n"})
    clone = _clone(tmp_path, source.root, "--single-branch", "--branch", "topic")
    branch = db.resolve(clone.root)
    assert branch.commit is None
    assert branch.problem is not None
    assert "'origin/main' names none — fetch it (`git fetch origin main`)" in branch.problem
    clone.git("fetch", "-q", "origin", "main:refs/remotes/origin/main")
    found = db.base(clone.root)
    assert (found.ref, found.tip, found.fork, found.outdated) == (
        "origin/main",
        _rev(clone, "origin/main"),
        _rev(clone, "origin/main"),
        False,
    )


def test_before_the_first_commit_it_says_commit_first(tmp_path: Path) -> None:
    repo = GitRepo.init(tmp_path / "work")
    branch = db.resolve(repo.root)
    assert branch.problem == "the default branch 'main' has no commit yet: commit first."


def test_a_declared_branch_this_repository_lacks_is_reported(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _declare(repo, TRUNK)
    branch = db.resolve(repo.root)
    assert (branch.ref, branch.commit) == (None, None)
    assert branch.problem == (
        "the default branch 'trunk' resolves to no commit here: there is no remote and no "
        "local branch 'trunk' — declare the right one (`repository.default-branch` in "
        ".pkit/project/config.yaml), or name a base with --base or PKIT_CHECK_BASE."
    )
    found = db.base(repo.root)
    assert (found.ref, found.source, found.tip, found.problem) == (
        TRUNK,
        db.DEFAULT_BRANCH,
        None,
        branch.problem,
    )
    with pytest.raises(fc.FrictionCheckError, match="resolves to no commit here"):
        fc.resolve_base(repo.root)


def test_no_git_is_an_answer_without_commits(tmp_path: Path) -> None:
    branch = db.resolve(tmp_path)
    assert (branch.name, branch.commit) == ("main", None)
    assert db.base(tmp_path).problem is not None


# --- the base of a comparison (point 3) --------------------------------------------------------


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


def test_working_on_main_the_base_is_the_remote_s_copy_never_head(tmp_path: Path) -> None:
    """Solo on `main` with unpushed commits: comparing with the local `main` would compare
    HEAD with itself and see nothing; the base is `origin/main`, where the work left it."""
    repo = _repo(tmp_path)
    _with_remote(repo, tmp_path)
    pushed = repo.head()
    repo.commit("unpushed one", {"one.md": "1\n"})
    repo.commit("unpushed two", {"two.md": "2\n"})
    base = db.base(repo.root)
    assert (base.ref, base.tip, base.fork, base.outdated) == ("origin/main", pushed, pushed, False)
    assert base.tip != repo.head()


def test_a_detached_head_is_compared_like_a_branch(tmp_path: Path) -> None:
    """A pipeline's checkout is often a detached commit: the default branch still resolves,
    and the fork is where that commit left it."""
    repo = _repo(tmp_path)
    _with_remote(repo, tmp_path)
    fork = repo.head()
    repo.checkout("topic", create=True)
    work = repo.commit("topic", {"topic.md": "t\n"})
    repo.git("checkout", "-q", "--detach", work)
    base = db.base(repo.root)
    assert (base.ref, base.tip, base.fork, base.outdated, base.problem) == (
        "origin/main",
        fork,
        fork,
        False,
        None,
    )


def test_a_branch_named_as_a_base_resolves_as_the_default_branch_does(tmp_path: Path) -> None:
    """`--base develop` reads the remote's `develop`, not a local one that ran ahead; a
    remote-tracking reference, or `refs/heads/develop`, is read as named."""
    repo = _repo(tmp_path)
    repo.git("branch", "develop")
    _with_remote(repo, tmp_path)
    shared = repo.head()
    repo.checkout("develop")
    ahead = repo.commit("develop, unpushed", {"dev.md": "d\n"})
    repo.checkout("main")
    named = db.base(repo.root, "develop")
    assert (named.ref, named.tip, named.resolved) == ("origin/develop", shared, db.RESOLVED_REMOTE)
    assert db.base(repo.root, "origin/develop").tip == shared
    local = db.base(repo.root, "refs/heads/develop")
    assert (local.ref, local.tip, local.resolved) == ("refs/heads/develop", ahead, None)


@pytest.mark.parametrize(
    ("named", "hint"),
    [
        ("origin/nope", "git fetch origin nope"),
        ("feature/x", "git fetch origin feature/x"),
        ("0123abc", "git fetch origin 0123abc"),
    ],
)
def test_the_fetch_hint_names_the_branch_asked_for(tmp_path: Path, named: str, hint: str) -> None:
    repo = _repo(tmp_path)
    _with_remote(repo, tmp_path)
    found = db.base(repo.root, named)
    assert found.problem is not None and f"(e.g. `{hint}`)" in found.problem


def test_a_shallow_clone_names_the_history_to_fetch(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    repo.checkout("topic", create=True)
    repo.commit("topic", {"topic.md": "t\n"})
    repo.checkout("main")
    repo.commit("main moved on", {"main.md": "m\n"})
    shallow = _clone(  # from a URL: a local path is cloned whole, whatever the depth
        tmp_path,
        f"file://{repo.root}",
        "--depth=1",
        "--no-single-branch",
        "--branch",
        "topic",
        name="shallow",
    )
    found = db.base(shallow.root)
    assert found.tip == _rev(shallow, "origin/main")
    assert found.problem is not None and "share no history" in found.problem


# --- the reading command (point 5) ---------------------------------------------------------


def _repository_base(*args: str) -> Any:
    return CliRunner().invoke(main, ["repository", "base", *args])


def test_the_reading_command_names_the_default_branch_and_the_base(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    _with_remote(repo, tmp_path)
    monkeypatch.chdir(repo.root)
    result = _repository_base("--json")
    assert result.exit_code == 0, result.output
    document = json.loads(result.stdout)
    assert document == {
        "schema_version": 1,
        "default_branch": {
            "name": "main",
            "source": db.DEFAULTED,
            "ref": "origin/main",
            "commit": repo.head(),
            "resolved": db.RESOLVED_REMOTE,
            "problem": None,
        },
        "base": {
            "ref": "origin/main",
            "source": db.DEFAULT_BRANCH,
            "tip": repo.head(),
            "fork": repo.head(),
            "outdated": False,
            "resolved": db.RESOLVED_REMOTE,
            "problem": None,
        },
    }
    refused = json.loads(_repository_base("--json", "--base=-x").stdout)
    assert refused["base"]["problem"] == "the base '-x' is not a revision name."
    assert refused["default_branch"] == document["default_branch"]


def test_the_human_view_says_which_branch_and_which_base(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    monkeypatch.chdir(repo.root)
    result = _repository_base()
    assert result.exit_code == 0, result.output
    short = repo.head()[:12]
    assert f"Default branch: main (default) → main at {short} (local)" in result.stdout
    assert f"Base: main (the default branch) at {short}; HEAD left it at {short}" in result.stdout
    assert "warning: the default branch 'main' is read from the local branch 'main'" in (
        result.stderr
    )


def test_the_artefacts_document_names_no_base(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Discovery and what is settled are two readings: `friction artefacts` runs discovery
    only, and `repository base` runs none."""
    repo = _repo(tmp_path)
    monkeypatch.chdir(repo.root)
    result = CliRunner().invoke(main, ["friction", "artefacts", "--json"])
    assert result.exit_code == 0, result.output
    assert not {"default_branch", "base"} & set(json.loads(result.stdout))


def test_a_value_read_as_the_default_is_warned_about_by_every_reader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    repo.write({CONFIG: "repository:\n  default-branch: two words\n"})
    monkeypatch.chdir(repo.root)
    said = "warning: repository.default-branch 'two words' is not a branch name"
    assert said in CliRunner().invoke(main, ["friction", "check", "--json"]).stderr
    assert said in _repository_base("--json").stderr


# --- the migration and changeset checks read the same base ---------------------------------------


def test_the_migration_check_compares_with_the_default_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """From where the branch left the declared default branch: its removal is found, and
    what the default branch gained since is not read as one."""
    repo = _repo(tmp_path, TRUNK)
    _declare(repo, TRUNK)
    repo.commit("declared", {".pkit/skills/core/old.md": "x\n"})
    repo.checkout("topic", create=True)
    repo.git("rm", "-q", ".pkit/skills/core/old.md")
    repo.commit("a skill goes")
    repo.checkout(TRUNK)
    repo.commit("trunk moves on", {".pkit/skills/core/new.md": "n\n"})
    repo.checkout("topic")
    monkeypatch.chdir(repo.root)
    result = CliRunner().invoke(main, ["migrations", "check-diff"])
    assert result.exit_code == 1, result.output
    assert "UNCOVERED" in result.output and ".pkit/skills/core/old.md" in result.output
    assert ".pkit/skills/core/new.md" not in result.output
    _declare(repo, "nowhere")
    refused = CliRunner().invoke(main, ["migrations", "check-diff"])
    assert refused.exit_code == 1
    assert "the default branch 'nowhere' resolves to no commit here" in refused.output
    refused = CliRunner().invoke(main, ["release", "check"])
    assert refused.exit_code == 1
    assert "the default branch 'nowhere' resolves to no commit here" in refused.output


# --- all three readers agree ----------------------------------------------------------------


_PM_READING = """
import json, sys
sys.path.insert(0, sys.argv[1])
from _lib import default_branch, lifecycle_inference
try:
    base = default_branch.check_base()
except default_branch.Unanswered as exc:
    print(json.dumps({"unanswered": str(exc)}))
    raise SystemExit(0)
print(json.dumps({
    "name": lifecycle_inference.resolve_base_branch({}, "EPIC: #1"),
    "check_base": base.ref,
    "tip": base.tip,
    "fork": base.fork,
    "problem": base.problem,
}))
"""


def _pm(repo: GitRepo) -> dict[str, Any]:
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


def _friction(repo: GitRepo) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["pkit", "friction", "check", "--json"],
        cwd=repo.root,
        capture_output=True,
        text=True,
        check=False,
    )


def _friction_base(repo: GitRepo) -> dict[str, Any]:
    completed = _friction(repo)
    assert completed.stdout, completed.stderr
    return json.loads(completed.stdout)["base"]


def _numbers_base(repo: AdopterRepo) -> dict[str, Any]:
    completed = run_script(repo, NUMBERS, "--json")
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)["base"]


def _settled(repo: GitRepo) -> dict[str, Any]:
    completed = subprocess.run(
        ["pkit", "repository", "base", "--json"],
        cwd=repo.root,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(completed.stdout)


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
    trunk = _rev(project, TRUNK)
    fork = project.git("merge-base", TRUNK, "HEAD").stdout.strip()
    expected = {"ref": TRUNK, "tip": trunk, "commit": fork, "outdated": True}

    # No remote: the local branch, the same commit for every reader — and each says so.
    assert _friction_base(project) == expected
    assert "is read from the local branch 'trunk'" in _friction(project).stderr
    assert _numbers_base(project) == expected
    numbers = run_script(project, NUMBERS, "--json")
    assert "warning: the default branch 'trunk' is read from the local branch" in numbers.stderr
    settled = _settled(project)
    assert settled["default_branch"] == {
        "name": TRUNK,
        "source": db.DECLARED,
        "ref": TRUNK,
        "commit": trunk,
        "resolved": db.RESOLVED_LOCAL,
        "problem": None,
    }
    assert (settled["base"]["ref"], settled["base"]["tip"], settled["base"]["fork"]) == (
        TRUNK,
        trunk,
        fork,
    )
    pm = _pm(project)
    assert (pm["name"], pm["check_base"], pm["tip"], pm["fork"]) == (TRUNK, TRUNK, trunk, fork)

    # A remote holding it: its tracking reference first, for every reader — even when
    # the local branch has moved on past it.
    _with_remote(project, tmp_path)
    project.checkout(TRUNK)
    project.commit("unpushed", {"src/unpushed.py": "print('u')\n"})
    project.checkout("topic")
    remote = {**expected, "ref": f"origin/{TRUNK}"}
    assert _friction_base(project) == remote
    assert _numbers_base(project) == remote
    assert _settled(project)["default_branch"]["ref"] == f"origin/{TRUNK}"
    assert _pm(project)["check_base"] == f"origin/{TRUNK}"

    # The override: the diff-scoped readers compare with it; the default branch is
    # still the declaration, for pm and for the reading command alike.
    monkeypatch.setenv(db.CHECK_BASE_ENV, f"refs/heads/{TRUNK}")
    local = {
        "ref": f"refs/heads/{TRUNK}",
        "tip": _rev(project, TRUNK),
        "commit": fork,
        "outdated": True,
    }
    assert _friction_base(project) == local
    assert _numbers_base(project) == local
    settled = _settled(project)
    assert (settled["base"]["ref"], settled["base"]["source"]) == (
        f"refs/heads/{TRUNK}",
        db.ENVIRONMENT,
    )
    assert settled["default_branch"]["ref"] == f"origin/{TRUNK}"
    pm = _pm(project)
    assert (pm["name"], pm["check_base"]) == (TRUNK, f"refs/heads/{TRUNK}")


def test_in_a_shallow_clone_the_three_readers_refuse_alike(
    project: AdopterRepo, tmp_path: Path
) -> None:
    """A depth-1 clone holds the default branch's tip but no merge-base: every reader
    reports the same problem, with the same fix, and none compares without it."""
    shallow = _clone(
        tmp_path,
        f"file://{project.root}",
        "--depth=1",
        "--no-single-branch",
        "--branch",
        "topic",
        name="shallow",
    )
    problem = (
        f"HEAD and the base 'origin/{TRUNK}' share no history to compare; in a shallow "
        f"clone, fetch the history back to where the branch left the base (e.g. `git fetch "
        f"--unshallow`)."
    )
    friction = _friction(shallow)
    assert friction.returncode == 1
    assert problem in friction.stderr
    numbers = subprocess.run(
        [sys.executable, str(shallow.root / NUMBERS)],
        cwd=shallow.root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert numbers.returncode == 1
    assert f"error: {problem}" in numbers.stderr
    assert _pm(shallow)["problem"] == problem


# --- the stamp allocates past settled state, never past a pipeline's base -----------------------


def test_the_variable_a_pipeline_sets_never_moves_where_the_stamp_numbers_from(
    project: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`$PKIT_CHECK_BASE` names a base with fewer numbers than the default branch: the
    stamp still numbers past the default branch (COR-054 point 3)."""
    project.checkout(TRUNK)
    project.git("branch", "early", "HEAD~2")  # before trunk's `UC-003`
    project.commit(
        "trunk numbers a third use case",
        {"tech-docs/analysis/use-case-model/use-cases/UC-003-third.md": _use_case("UC-003")},
    )
    project.checkout("topic")
    monkeypatch.setenv(db.CHECK_BASE_ENV, "refs/heads/early")
    from tests.analysis_repo import NEW

    completed = run_script(project, NEW, "use-case", "fourth", "--actor", "ACT-tester")
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip().splitlines()[-1].split()[1] == "UC-004"


def _use_case(number: str) -> str:
    return (
        f"---\nid: {number}\ntitle: Third\nstatus: draft\nactor: ACT-tester\n---\n\n"
        f"# {number} — Third\n"
    )


# --- pm reads through the backbone, never guessing ------------------------------------------


def _load_lib(capability: Path, module: str) -> ModuleType:
    """A capability's `_lib` module, imported as its scripts import it: `_lib` is on the
    path only while it loads, since another capability's `_lib` is not importable beside
    it."""
    scripts = str(capability / "scripts")

    def ours() -> list[str]:
        return [k for k in sys.modules if k == "_lib" or k.startswith("_lib.")]

    saved = {k: sys.modules.pop(k) for k in ours()}
    sys.path.insert(0, scripts)
    try:
        return importlib.import_module(module)
    finally:
        sys.path.remove(scripts)
        for key in ours():
            del sys.modules[key]
        sys.modules.update(saved)


PM_BRANCH: Any = _load_lib(PM, "_lib.default_branch")
SA_BACKBONE: Any = _load_lib(SA, "_lib.backbone")


def _answering(name: str | None, source: str = "default", stderr: str = "") -> Any:
    """A runner standing in for `pkit repository base --json`: `None` answers nothing."""

    def run(argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert argv[: len(PM_BRANCH.ARGV)] == list(PM_BRANCH.ARGV)
        if name is None:
            return subprocess.CompletedProcess(argv, 1, "", "Error: no")
        document = {
            "schema_version": 1,
            "default_branch": {"name": name, "source": source, "ref": name, "commit": "c"},
            "base": {"ref": name, "tip": "c", "fork": "c", "problem": None},
        }
        return subprocess.CompletedProcess(argv, 0, json.dumps(document), stderr)

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
        (("main", db.DEFAULTED), "main", "main", None),
        (("main", db.DEFAULTED), "develop", "develop", "until the upgrade carries it over"),
        ((TRUNK, db.DECLARED), "develop", TRUNK, "is ignored: the backbone declares"),
        ((TRUNK, db.DECLARED), TRUNK, TRUNK, None),
    ],
    ids=[
        "declared",
        "defaulted",
        "old-key-on-main-says-nothing",
        "old-key-while-undeclared",
        "old-key-never-overrides",
        "old-key-equal",
    ],
)
def test_pm_s_default_branch_is_the_backbone_s(
    fresh_pm: Any,
    capsys: pytest.CaptureFixture[str],
    backbone: tuple[str, str],
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


def _raising(exc: BaseException) -> Any:
    def run(argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise exc

    return run


def _exiting(code: int, stdout: str, stderr: str = "") -> Any:
    def run(argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, code, stdout, stderr)

    return run


@pytest.mark.parametrize(
    ("run", "cause"),
    [
        (_raising(FileNotFoundError("pkit")), "`pkit` is not on PATH"),
        (_raising(subprocess.TimeoutExpired("pkit", 60)), "did not answer within 60s"),
        (_answering(None), "it exited 1: Error: no"),
        (
            _exiting(2, "", "Usage: pkit\nError: No such command 'repository'.\n"),
            "the installed backbone predates it — upgrade it",
        ),
        (_exiting(0, '{"schema_version": 1}'), "names no default"),
        (_exiting(0, '{"schema_version": 2}'), "it answered schema_version 2; pm reads 1"),
    ],
    ids=["no-pkit", "timeout", "failed", "older-backbone", "no-answer", "another-version"],
)
def test_pm_never_guesses_when_the_backbone_cannot_answer(
    fresh_pm: Any, run: Any, cause: str
) -> None:
    """No silent `main`: the reading raises, naming the cause; the verbs refuse on it."""
    for _ in range(2):  # asked once; the second reading raises the same
        with pytest.raises(PM_BRANCH.Unanswered) as raised:
            fresh_pm.name({"default_branch": "develop"}, run=run)
        assert cause in str(raised.value)
        assert "pm does not guess it (COR-054 point 4)" in str(raised.value)


def test_pm_passes_on_what_the_backbone_says(
    fresh_pm: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    run = _answering("main", stderr="warning: the default branch 'main' is read from the local\n")
    assert fresh_pm.name({}, run=run) == "main"
    assert capsys.readouterr().err == "warn: the default branch 'main' is read from the local\n"


@pytest.mark.parametrize(
    ("code", "stdout", "stderr", "said"),
    [
        (
            0,
            '{"schema_version": 2, "default_branch": {}, "base": {}}',
            "",
            "answered schema_version 2; this capability reads 1",
        ),
        (2, "", "Error: No such command 'repository'.\n", "predates it — upgrade it"),
        (1, "", "Error: no\n", "exited 1: Error: no"),
    ],
    ids=["another-version", "older-backbone", "failed"],
)
def test_software_analysis_refuses_a_reading_it_cannot_read(
    tmp_path: Path, code: int, stdout: str, stderr: str, said: str
) -> None:
    """Like pm, software-analysis reads what is settled at the version it knows, or not at
    all: the stamp and the number check refuse on it rather than guess (COR-054 point 4)."""

    def run(argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, code, stdout, stderr)

    with pytest.raises(SA_BACKBONE.Unreadable, match=re.escape(said)):
        SA_BACKBONE.settled(tmp_path, run=run)


# --- no reader resolves on its own -----------------------------------------------------------

#: What resolving a base by hand takes, in a script's code.
_BASE_TOKENS = {
    r"environ\b[^\n]*CHECK_BASE|getenv\(": "reading $PKIT_CHECK_BASE",
    r"['\"]merge-base['\"]": "computing a merge-base",
    r"\.\.\.HEAD": "diffing from a merge-base git computes",
    r"f?['\"]origin/": "naming a remote-tracking reference",
    r"['\"]\.pkit/project/config\.yaml['\"]|\.get\(\s*['\"]default-branch['\"]": (
        "reading the declaration"
    ),
}


def _base_tokens(text: str) -> list[str]:
    code = _code(text)
    return [meaning for token, meaning in _BASE_TOKENS.items() if re.search(token, code)]


def test_the_guard_recognises_a_base_resolved_by_hand() -> None:
    ported = (
        "import os\n"
        "base = os.environ.get('PKIT_CHECK_BASE') or 'origin/main'\n"
        "fork = git('merge-base', base, 'HEAD')\n"
        "changed = git('diff', f'{base}...HEAD')\n"
    )
    assert _base_tokens(ported) == [
        "reading $PKIT_CHECK_BASE",
        "computing a merge-base",
        "diffing from a merge-base git computes",
        "naming a remote-tracking reference",
    ]
    assert _base_tokens('"""PKIT_CHECK_BASE, merge-base and origin/main, in prose."""\n') == []


@pytest.mark.parametrize("capability", [SA, PM], ids=["software-analysis", "project-management"])
def test_no_capability_script_resolves_a_base_of_its_own(capability: Path) -> None:
    """Their scripts read the base in `pkit repository base --json` (COR-054 point 5)."""
    scripts = sorted((capability / "scripts").rglob("*.py"))
    assert scripts
    found = {
        path.relative_to(capability).as_posix(): tokens
        for path in scripts
        if (tokens := _base_tokens(path.read_text(encoding="utf-8")))
    }
    assert found == {}


def test_pm_reads_the_default_branch_in_one_place() -> None:
    """Every pm reading of the default branch goes through `_lib/default_branch.py`, the one
    script that asks the backbone for it (COR-054 point 5) — and there only its answer's
    `default_branch`, never the old key by name."""
    read = re.compile(r"\.get\(\s*['\"]default_branch['\"]|['\"]repository['\"],\s*['\"]base['\"]")
    lib = "scripts/_lib/default_branch.py"
    scripts = sorted((PM / "scripts").rglob("*.py"))
    found = [
        path.relative_to(PM).as_posix()
        for path in scripts
        if read.search(_code(path.read_text(encoding="utf-8")))
    ]
    assert found == [lib]
    assert "ALIAS_KEY)" in (PM / lib).read_text(encoding="utf-8")
