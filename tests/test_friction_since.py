"""Tests for `pkit friction since` (#1689, #1728, #2031; COR-062 point 3; ADR-068 point 5;
project-management DEC-055 point 3).

Every test stands up a real adopter repository: a page on `main`, a branch
whose head was authorised, and later commits on that branch — answers given
again in answer files of the change's own, merges of `main`, other edits — so
the command reads real commits and git's own merges. Version 2 of its document
counts the answer files the change adds, and nothing in an artefact's block.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from types import ModuleType

import pytest
from click.testing import CliRunner, Result

from project_kit import answer_files as af
from project_kit import default_branch as db
from project_kit import friction_since as fs
from project_kit.cli import main
from project_kit.friction_git import FrictionCheckError
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.friction_documents import CONFIG, SOURCE, friction_config

REPO_ROOT = Path(__file__).resolve().parent.parent
PAGE = "docs/guide.md"
OTHER = "docs/other.md"
T0 = "2026-09-01T09:00:00Z"
T1 = "2026-10-01T09:00:00Z"
T2 = "2026-10-02T09:40:12Z"
BODY = "The CLI takes one flag.\n"


def _page(*, body: str = BODY, title: str = "The guide", at: str | None = None) -> str:
    """The page: anchored to the CLI, its block holding a revalidation only where `at` is
    given."""
    block = (
        f"    revalidated:\n      at: {at}\n      outcome: unchanged\n"
        f"      unchanged-because: the CLI is as described\n"
        if at is not None
        else ""
    )
    return (
        f"---\nid: guide\npkit:\n  friction:\n    anchors:\n      path: [src/cli/**]\n"
        f"{block}status: draft\n---\n\n# {title}\n\n{body}"
    )


def _answer(name: str) -> str:
    return af.path_of(f"{name}.yaml")


def _answers(at: str, *read: str, because: str = "the CLI is as described") -> str:
    """An answer file revalidating the page at `at`, naming `read`."""
    named = "".join(f"\n      - {name}.yaml" for name in read)
    return (
        f"answers:\n  - artefact: {PAGE}\n"
        + (f"    read:{named}\n" if read else "")
        + f"    revalidated:\n      at: {at}\n      outcome: unchanged\n"
        f"      unchanged-because: {because}\n"
    )


@pytest.fixture
def repo(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    adopter = make_adopter_repo()
    adopter.git("config", "core.autocrlf", "false")
    adopter.write({CONFIG: friction_config(), **SOURCE, PAGE: _page()})
    adopter.commit("start", files=None)
    return adopter


@pytest.fixture(autouse=True)
def no_check_base_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """A developer's own `$PKIT_CHECK_BASE` must not decide which base is set apart."""
    monkeypatch.delenv(db.CHECK_BASE_ENV, raising=False)


def _authorised(repo: AdopterRepo, files: dict[str, str | None] | None = None) -> str:
    """Branch `topic` off `main`, commit the change its authorisation was given on."""
    repo.checkout("topic", create=True)
    return repo.commit("the change", files or {"src/cli/main.py": "print('cli, renamed')\n"})


def _since(repo: AdopterRepo, since: str, head: str | None = None) -> fs.Since:
    return fs.run_since(repo.root, since, head_rev=head, base_ref="main")


def _cli(*args: str) -> Result:
    return CliRunner().invoke(main, ["friction", "since", *args])


def _whys(found: fs.Since) -> list[tuple[str | None, str, str]]:
    return [(o.path, o.commit, o.why) for o in found.outside]


# ---- the author's own commits --------------------------------------------------------


def test_an_answer_file_the_change_adds_lies_inside(repo: AdopterRepo) -> None:
    since = _authorised(repo)
    head = repo.commit("answer", {_answer("one"): _answers(T1)})
    found = _since(repo, since)
    assert found.all_inside
    assert found.inside == (_answer("one"),)
    assert found.outside == ()
    assert found.steps == (fs.Step(head, merges_base=False),)


def test_an_answer_file_the_change_added_before_lies_inside_when_written_again(
    repo: AdopterRepo,
) -> None:
    """The base does not hold a file the change added before its authorised head, so a
    later rewrite of it is the change's own answer, as a writer's next round is."""
    since = _authorised(repo, {_answer("one"): _answers(T1)})
    repo.commit("answer again", {_answer("one"): _answers(T2, because="the rename holds")})
    found = _since(repo, since)
    assert found.all_inside, found.outside
    assert found.inside == (_answer("one"),)


def test_an_answer_file_removed_lies_outside(repo: AdopterRepo) -> None:
    """A removed file takes its answers away, as a revert does (COR-062 point 8)."""
    since = _authorised(repo, {_answer("one"): _answers(T1)})
    removed = repo.commit("drop the answer", {_answer("one"): None})
    assert _whys(_since(repo, since)) == [
        (_answer("one"), removed, "an answer file removed, which takes its answers away")
    ]


def test_an_answer_file_the_base_holds_lies_outside(repo: AdopterRepo) -> None:
    """No change rewrites an answer file its base holds (COR-062 point 3)."""
    repo.commit("main answers", {_answer("landed"): _answers(T0)})
    since = _authorised(repo)
    rewritten = repo.commit("rewrite it", {_answer("landed"): _answers(T1)})
    assert _whys(_since(repo, since)) == [
        (_answer("landed"), rewritten, "an answer file the base holds, which no change rewrites")
    ]


def test_an_answer_in_an_artefact_s_block_lies_outside(repo: AdopterRepo) -> None:
    """Version 2 counts no block: an answer written there lies outside, where version 1
    counted it inside."""
    since = _authorised(repo)
    written = repo.commit("answer in the block", {PAGE: _page(at=T1)})
    assert _whys(_since(repo, since)) == [(PAGE, written, "not an answer file")]


@pytest.mark.parametrize(
    "path",
    [f"{af.FOLDER}/README.md", f"{af.FOLDER}/nested/one.yaml", f"{af.FOLDER}/one.yml"],
)
def test_a_file_in_the_folder_that_is_no_answer_file_lies_outside(
    repo: AdopterRepo, path: str
) -> None:
    since = _authorised(repo)
    head = repo.commit("a stray file", {path: _answers(T1)})
    assert _whys(_since(repo, since)) == [(path, head, "not an answer file")]


def test_a_link_in_the_folder_lies_outside(repo: AdopterRepo) -> None:
    since = _authorised(repo)
    link = repo.root / _answer("link")
    link.parent.mkdir(parents=True, exist_ok=True)
    os.symlink("../../../../docs/guide.md", link)
    head = repo.commit("a link", files=None)
    assert _whys(_since(repo, since)) == [(_answer("link"), head, "not a regular file")]


def test_a_hidden_name_in_the_folder_is_no_answer_file(repo: AdopterRepo) -> None:
    since = _authorised(repo)
    head = repo.commit("a hidden file", {f"{af.FOLDER}/.one.yaml": _answers(T1)})
    assert _whys(_since(repo, since)) == [(f"{af.FOLDER}/.one.yaml", head, "not an answer file")]


def test_a_path_is_judged_as_the_tree_writes_it() -> None:
    """A tree entry such as `<folder>/./x.yaml` reads as an answer file once cleaned up,
    so the path is compared as written."""
    assert fs._is_answer_path(f"{af.FOLDER}/x.yaml")
    assert not fs._is_answer_path(f"{af.FOLDER}/./x.yaml")
    assert not fs._is_answer_path(f"{af.FOLDER}//x.yaml")


def test_a_submodule_repointed_lies_outside_whatever_gitmodules_says(repo: AdopterRepo) -> None:
    """A `.gitmodules` that ignores a submodule's changes must not hide one: a submodule
    repointed after the authorised head lies outside."""
    repo.write(
        {".gitmodules": '[submodule "vendor"]\n\tpath = vendor\n\turl = ./v\n\tignore = all\n'}
    )
    repo.git("update-index", "--add", "--cacheinfo", f"160000,{'1' * 40},vendor")
    repo.commit(
        "vendor a submodule", {".gitmodules": repo.root.joinpath(".gitmodules").read_text()}
    )
    since = _authorised(repo)
    repo.git("update-index", "--cacheinfo", f"160000,{'3' * 40},vendor")
    repo.write({_answer("one"): _answers(T1)})
    repo.git("add", _answer("one"))
    repo.git("commit", "-q", "-m", "answer, and repoint the submodule")
    found = _since(repo, since)
    assert not found.all_inside
    assert [o.path for o in found.outside] == ["vendor"]


def test_a_base_whose_answer_files_cannot_be_listed_gives_no_answer(repo: AdopterRepo) -> None:
    """The answer files the base holds are what a change may not rewrite: a listing git
    cannot give fails the run, never reads as a base holding none."""
    tip = repo.head()
    _authorised(repo)
    head = repo.commit("answer", {_answer("one"): _answers(T1)})
    repo.lose_object(repo.git("rev-parse", f"{tip}^{{tree}}").stdout.strip())
    with pytest.raises(FrictionCheckError, match="ls-tree"):
        fs._base_answer_files(repo.root, head, tip)


def test_an_answer_file_whose_mode_changed_lies_outside(repo: AdopterRepo) -> None:
    since = _authorised(repo, {_answer("one"): _answers(T1)})
    (repo.root / _answer("one")).chmod(0o755)
    head = repo.commit("make it runnable", files=None)
    assert _whys(_since(repo, since)) == [
        (_answer("one"), head, "its mode changed (100644 to 100755)")
    ]


@pytest.mark.parametrize(
    "files",
    [
        {PAGE: _page(body="The CLI takes two flags.\n")},
        {PAGE: _page(title="The new guide")},
        {"src/cli/main.py": "print('changed again')\n"},
        {"docs/new.md": _page()},
        {PAGE: None},
    ],
    ids=["body", "field", "code", "added", "removed"],
)
def test_any_other_change_lies_outside(repo: AdopterRepo, files: dict[str, str | None]) -> None:
    since = _authorised(repo)
    head = repo.commit("another change", files)
    found = _since(repo, since)
    assert not found.all_inside
    (outside,) = found.outside
    assert (outside.commit, outside.why) == (head, "not an answer file")


def test_a_change_inside_and_one_outside_names_only_the_one_outside(repo: AdopterRepo) -> None:
    since = _authorised(repo)
    repo.commit("answer", {_answer("one"): _answers(T1)})
    repo.commit("and a fix", {"src/core/engine.py": "ENGINE = 2\n"})
    found = _since(repo, since)
    assert not found.all_inside
    assert found.inside == (_answer("one"),)
    assert [o.path for o in found.outside] == ["src/core/engine.py"]


def test_the_same_commit_has_nothing_outside(repo: AdopterRepo) -> None:
    since = _authorised(repo)
    found = _since(repo, since, since)
    assert found.all_inside and found.steps == ()


# ---- merges of the base --------------------------------------------------------------


def test_a_clean_merge_of_the_base_counts_for_nothing(repo: AdopterRepo) -> None:
    """The base's own changes — code, another page, an answer file it landed — are not the
    author's: a merge that takes them cleanly contributes nothing, and an answer the
    change then adds lies inside."""
    repo.checkout("main")
    repo.commit("base", {OTHER: _page(), "src/core/engine.py": "ENGINE = 3\n"})
    repo.checkout("topic", create=True)
    since = repo.commit("the change", {"src/cli/main.py": "print('cli, renamed')\n"})
    repo.checkout("main")
    repo.commit("base moves", {OTHER: _page(body="Other.\n"), _answer("landed"): _answers(T0)})
    repo.checkout("topic")
    merge = repo.merge("main")
    head = repo.commit("answer again", {_answer("mine"): _answers(T1, "landed")})
    found = _since(repo, since)
    assert found.all_inside, found.outside
    assert found.steps == (fs.Step(merge, merges_base=True), fs.Step(head, merges_base=False))
    assert found.inside == (_answer("mine"),)


def test_an_answer_file_the_base_landed_is_its_own_after_a_merge(repo: AdopterRepo) -> None:
    """Once the head has merged the base, the base where the head left it holds what it
    landed: a rewrite of such a file lies outside."""
    since = _authorised(repo)
    repo.checkout("main")
    repo.commit("main answers", {_answer("landed"): _answers(T0)})
    repo.checkout("topic")
    repo.merge("main")
    rewritten = repo.commit("rewrite it", {_answer("landed"): _answers(T1)})
    assert _whys(_since(repo, since)) == [
        (_answer("landed"), rewritten, "an answer file the base holds, which no change rewrites")
    ]


def _conflicting_merge(repo: AdopterRepo, this: str, base: str) -> str:
    """`topic` authorised at a commit writing `this` to the page, `main` writing `base`,
    then `main` merged into `topic`, which leaves the conflict. Returns the authorised
    commit."""
    repo.checkout("topic", create=True)
    since = repo.commit("the change", {PAGE: this, "src/cli/main.py": "print('renamed')\n"})
    repo.checkout("main")
    repo.commit("base edits", {PAGE: base})
    repo.checkout("topic")
    merged = repo.git("merge", "-q", "--no-edit", "main", check=False)
    assert merged.returncode == 1, merged.stdout + merged.stderr
    return since


def _commit_merge(repo: AdopterRepo, page: str) -> str:
    repo.write({PAGE: page})
    repo.git("add", PAGE)
    repo.git("commit", "-q", "--no-edit")
    return repo.head()


def test_a_conflict_resolved_by_hand_lies_outside(repo: AdopterRepo) -> None:
    """The body conflicts: how the author resolved it is the author's change."""
    since = _conflicting_merge(repo, _page(body="This branch's body.\n"), _page(body="Base.\n"))
    merge = _commit_merge(repo, _page(body="Both, combined.\n"))
    found = _since(repo, since)
    assert not found.all_inside
    assert [(o.path, o.commit) for o in found.outside] == [(PAGE, merge)]


def test_a_conflict_taken_from_one_side_lies_outside(repo: AdopterRepo) -> None:
    """Taking this branch's body over the base's is a choice, held against git's merge
    taking the other side."""
    since = _conflicting_merge(repo, _page(body="This branch's body.\n"), _page(body="Base.\n"))
    _commit_merge(repo, _page(body="This branch's body.\n"))
    assert not _since(repo, since).all_inside


def test_an_edit_made_inside_a_clean_merge_is_not(repo: AdopterRepo) -> None:
    since = _authorised(repo)
    repo.checkout("main")
    repo.commit("base", {"src/x.py": "X = 1\n"})
    repo.checkout("topic")
    repo.git("merge", "-q", "--no-ff", "--no-commit", "main")
    repo.write({"src/core/engine.py": "ENGINE = 9\n", _answer("mine"): _answers(T1)})
    repo.git("add", "-A")
    repo.git("commit", "-q", "--no-edit")
    found = _since(repo, since)
    assert [o.path for o in found.outside] == ["src/core/engine.py"]
    assert found.inside == (_answer("mine"),)


def test_a_merge_of_another_branch_counts_whole(repo: AdopterRepo) -> None:
    """Only a merge of the base is set apart: what another branch brings is the
    author's change."""
    since = _authorised(repo)
    repo.checkout("main")
    repo.checkout("other", create=True)
    repo.commit("other work", {"src/other.py": "OTHER = 1\n"})
    repo.checkout("topic")
    merge = repo.merge("other")
    found = _since(repo, since)
    assert found.steps == (fs.Step(merge, merges_base=False),)
    assert [o.path for o in found.outside] == ["src/other.py"]


# ---- a line the changes cannot be read along ---------------------------------------


def test_a_head_that_does_not_descend_answers_no(repo: AdopterRepo) -> None:
    since = _authorised(repo)
    repo.git("reset", "-q", "--hard", "main")
    repo.commit("rewritten", {"src/cli/main.py": "print('cli, renamed')\n"})
    found = _since(repo, since)
    assert not found.all_inside
    assert found.reason is not None and "does not descend" in found.reason


def test_a_commit_reached_only_through_a_merge_answers_no(repo: AdopterRepo) -> None:
    repo.checkout("side", create=True)
    since = repo.commit("side", {"src/side.py": "SIDE = 1\n"})
    repo.checkout("main")
    repo.checkout("topic", create=True)
    repo.commit("topic", {"src/cli/main.py": "print('t')\n"})
    repo.merge("side")
    found = _since(repo, since)
    assert found.reason is not None and "only through a merge" in found.reason


# ---- the command ---------------------------------------------------------------------


def test_the_json_document(repo: AdopterRepo) -> None:
    since = _authorised(repo)
    head = repo.commit("answer", {_answer("one"): _answers(T1)})
    result = _cli(since[:10], "--head", head, "--base", "main", "--json")
    assert result.exit_code == 0, result.output
    document = json.loads(result.stdout)
    assert document == {
        "schema_version": 2,
        "report": "since",
        "since": since,
        "head": head,
        "base": {"ref": "main", "tip": repo.git("rev-parse", "main").stdout.strip()},
        "all_inside": True,
        "reason": None,
        "commits": [{"commit": head, "merges_base": False}],
        "inside": [_answer("one")],
        "outside": [],
    }


def test_the_human_view(repo: AdopterRepo) -> None:
    since = _authorised(repo)
    repo.commit("answer", {_answer("one"): _answers(T1)})
    head = repo.commit("a fix", {"src/core/engine.py": "ENGINE = 2\n"})
    result = _cli(since, "--base", "main")
    assert result.exit_code == 0, result.output
    lines = result.stdout.splitlines()
    assert f"  {_answer('one')} — an answer file this change adds" in lines
    assert f"  src/core/engine.py — outside, in {head[:12]}: not an answer file" in lines
    assert lines[-1] == "  Not all inside the change's answer files: a change lies outside them."


def test_a_name_that_is_no_commit_cannot_be_answered(repo: AdopterRepo) -> None:
    result = _cli("no-such-commit", "--base", "main")
    assert result.exit_code == 1
    assert "names no commit" in result.output


def test_a_tag_named_like_a_commit_id_is_refused(repo: AdopterRepo) -> None:
    """git reads a tag before a short id: a tag named like the authorised commit's id
    must not stand in for it."""
    since = _authorised(repo)
    repo.commit("answer", {_answer("one"): _answers(T1)})
    repo.git("tag", since[:7], "main")
    with pytest.raises(FrictionCheckError, match="reads as a commit's id"):
        _since(repo, since[:7])


def test_the_human_view_escapes_what_the_author_named(repo: AdopterRepo) -> None:
    """A path is the author's: a control character in it is printed escaped, so it
    cannot rewrite what the terminal shows."""
    since = _authorised(repo)
    repo.commit("a strange name", {"src/x\x1b[8m.py": "X = 1\n"})
    result = _cli(since, "--base", "main")
    assert result.exit_code == 0, result.output
    assert "\x1b[8m" not in result.stdout
    assert "src/x\\x1b[8m.py — outside" in result.stdout


def test_a_shallow_clone_cannot_be_answered(
    repo: AdopterRepo, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """The history between the two commits may not be here: no answer, never a pass."""
    _authorised(repo)
    repo.commit("answer", {_answer("one"): _answers(T1)})
    shallow = tmp_path_factory.mktemp("shallow") / "clone"
    repo.git(
        "clone", "-q", "--depth", "1", "--branch", "topic", f"file://{repo.root}", str(shallow)
    )
    with pytest.raises(FrictionCheckError, match="shallow"):
        fs.run_since(shallow, "HEAD", base_ref="origin/topic")


# ---- one reading of the author's changes, in two homes -------------------------------
#
# project-management DEC-055 point 3 reads the changes since an authorised head as the
# freshness rule reads the author's changes (DEC-028), whose home is the capability's
# `_lib/author_delta.py`. The backbone cannot import it, nor it the backbone: this table
# of histories holds the two readings together. Each names the same files, and each
# refuses the same lines.


@pytest.fixture(scope="module")
def author_delta() -> Iterator[ModuleType]:
    scripts = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
    sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location(
        "pm_author_delta_beside_friction_since", scripts / "_lib" / "author_delta.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # a dataclass reads its own module while it is made
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(scripts))


def _answered_after_a_clean_merge(repo: AdopterRepo) -> str:
    since = _authorised(repo)
    repo.checkout("main")
    repo.commit("base moves", {OTHER: _page(), _answer("landed"): _answers(T0)})
    repo.checkout("topic")
    repo.merge("main")
    repo.commit("answer again", {_answer("mine"): _answers(T1, "landed")})
    return since


def _answered_and_fixed(repo: AdopterRepo) -> str:
    since = _authorised(repo)
    repo.commit("answer", {_answer("one"): _answers(T1)})
    repo.commit("and a fix", {"src/core/engine.py": "ENGINE = 2\n"})
    return since


def _resolved_by_hand(repo: AdopterRepo) -> str:
    since = _conflicting_merge(repo, _page(body="This branch's.\n"), _page(body="Base.\n"))
    _commit_merge(repo, _page(body="Both.\n"))
    return since


def _edited_inside_a_clean_merge(repo: AdopterRepo) -> str:
    since = _authorised(repo)
    repo.checkout("main")
    repo.commit("base", {"src/x.py": "X = 1\n"})
    repo.checkout("topic")
    repo.git("merge", "-q", "--no-ff", "--no-commit", "main")
    repo.write({"src/core/engine.py": "ENGINE = 9\n"})
    repo.git("add", "-A")
    repo.git("commit", "-q", "--no-edit")
    return since


def _merged_another_branch(repo: AdopterRepo) -> str:
    since = _authorised(repo)
    repo.checkout("main")
    repo.checkout("other", create=True)
    repo.commit("other work", {"src/other.py": "OTHER = 1\n"})
    repo.checkout("topic")
    repo.merge("other")
    return since


def _rebased(repo: AdopterRepo) -> str:
    since = _authorised(repo)
    repo.git("reset", "-q", "--hard", "main")
    repo.commit("rewritten", {"src/cli/main.py": "print('cli, renamed')\n"})
    return since


def _reached_through_a_merge(repo: AdopterRepo) -> str:
    repo.checkout("side", create=True)
    since = repo.commit("side", {"src/side.py": "SIDE = 1\n"})
    repo.checkout("main")
    repo.checkout("topic", create=True)
    repo.commit("topic", {"src/cli/main.py": "print('t')\n"})
    repo.merge("side")
    return since


@pytest.mark.parametrize(
    "history",
    [
        _answered_after_a_clean_merge,
        _answered_and_fixed,
        _resolved_by_hand,
        _edited_inside_a_clean_merge,
        _merged_another_branch,
        _rebased,
        _reached_through_a_merge,
    ],
)
def test_the_files_named_are_the_author_s_changes_as_the_freshness_rule_reads_them(
    repo: AdopterRepo, author_delta: ModuleType, history: Callable[[AdopterRepo], str]
) -> None:
    since = history(repo)
    found = _since(repo, since)
    tip = repo.git("rev-parse", "main").stdout.strip()
    delta = author_delta.author_delta(since, repo.head(), base_tip=tip, cwd=repo.root)
    assert (found.reason is not None) == (not delta.ok), (found.reason, delta.error)
    if delta.ok:
        named = set(found.inside) | {o.path for o in found.outside if o.path is not None}
        assert named == set(delta.paths)
