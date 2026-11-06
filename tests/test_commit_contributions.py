"""What a change's commits contribute, and git's merge of two commits (ADR-057 point 2).

Each test builds a real history: the module reads git and judges nothing, so what it
gives is what git gives for these commits.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from project_kit import commit_contributions as contributions
from project_kit.friction_git import FrictionCheckError
from tests.adopter_repo import GitRepo

A = "a.txt"
B = "b.txt"

#: What `str.splitlines` breaks on besides a newline, each of which a subject may hold.
LINE_SEPARATORS = ("\r", "\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029")


def _settled(_parent: str) -> bool:
    return True


@pytest.fixture
def repo(tmp_path: Path) -> GitRepo:
    made = GitRepo.init(tmp_path / "work")
    made.commit("start", {A: "one\n", B: "two\n"})
    return made


def _tree_of(repo: GitRepo, tree: str, rel: str) -> str:
    return repo.git("show", f"{tree}:{rel}").stdout


def _sides(repo: GitRepo, first: str, second: str) -> tuple[str, str]:
    """Two branches that each set `a.txt`, the text in conflict."""
    repo.checkout("left", create=True)
    left = repo.commit("left", {A: first})
    repo.checkout("main")
    repo.checkout("right", create=True)
    right = repo.commit("right", {A: second})
    return left, right


# --- git's merge -----------------------------------------------------------------------


def test_a_clean_merge_gives_the_merged_tree(repo: GitRepo) -> None:
    repo.checkout("left", create=True)
    left = repo.commit("left", {A: "left\n"})
    repo.checkout("main")
    right = repo.commit("right", {B: "right\n"})

    merged = contributions.merge(repo.root, left, right)

    assert merged.clean and merged.conflicted == ()
    assert _tree_of(repo, merged.tree, A) == "left\n"
    assert _tree_of(repo, merged.tree, B) == "right\n"


def test_a_conflict_names_each_path_in_it(repo: GitRepo) -> None:
    left, right = _sides(repo, "left\n", "right\n")

    merged = contributions.merge(repo.root, left, right)

    assert not merged.clean
    assert merged.conflicted == (A,)


def test_a_git_that_cannot_merge_raises_and_never_reads_as_clean(repo: GitRepo) -> None:
    with pytest.raises(FrictionCheckError, match="merge-tree"):
        contributions.merge(repo.root, "no-such-commit", repo.head())


def test_a_failed_merge_gives_gits_last_line_whole(repo: GitRepo) -> None:
    with pytest.raises(FrictionCheckError, match="no-such\u2028commit"):
        contributions.merge(repo.root, "no-such\u2028commit", repo.head())


# --- the state before a commit ---------------------------------------------------------


def test_a_commit_with_no_parent_has_no_state_before_it(repo: GitRepo) -> None:
    assert contributions.prior_state(repo.root, (), settled=_settled).states == ()


def test_a_commit_with_one_parent_is_read_against_it(repo: GitRepo) -> None:
    head = repo.head()

    found = contributions.prior_state(repo.root, (head,), settled=_settled)

    assert found.states == (head,) and not found.merged


def test_a_merge_is_read_against_gits_merge_of_its_parents(repo: GitRepo) -> None:
    repo.checkout("left", create=True)
    left = repo.commit("left", {A: "left\n"})
    repo.checkout("main")
    right = repo.commit("right", {B: "right\n"})

    found = contributions.prior_state(repo.root, (right, left), settled=_settled)

    assert found.merged
    assert found.states == (contributions.merge(repo.root, right, left).tree,)


def test_a_merge_with_a_parent_not_settled_is_read_against_its_first_parent(
    repo: GitRepo,
) -> None:
    repo.checkout("left", create=True)
    left = repo.commit("left", {A: "left\n"})
    repo.checkout("main")
    right = repo.commit("right", {B: "right\n"})

    found = contributions.prior_state(repo.root, (right, left), settled=lambda _parent: False)

    assert found.states == (right,) and not found.merged


def test_a_merge_of_three_parents_is_folded(repo: GitRepo) -> None:
    repo.checkout("one", create=True)
    one = repo.commit("one", {"one.txt": "1\n"})
    repo.checkout("main")
    repo.checkout("two", create=True)
    two = repo.commit("two", {"two.txt": "2\n"})
    repo.checkout("main")
    three = repo.commit("three", {"three.txt": "3\n"})

    found = contributions.prior_state(repo.root, (three, one, two), settled=_settled)

    (tree,) = found.states
    listed = repo.git("ls-tree", "-r", "--name-only", tree).stdout.split()
    assert {"one.txt", "two.txt", "three.txt"} <= set(listed)


def test_a_conflicted_merge_is_read_against_each_side_taken(repo: GitRepo) -> None:
    left, right = _sides(repo, "left\n", "right\n")

    found = contributions.prior_state(repo.root, (left, right), settled=_settled)

    assert found.merged and found.off_text == ()
    assert [_tree_of(repo, state, A) for state in found.states] == ["left\n", "right\n"]


def test_a_conflict_outside_the_text_is_read_against_the_parents(repo: GitRepo) -> None:
    repo.checkout("left", create=True)
    left = repo.commit("left", {A: "left\n"})
    repo.checkout("main")
    repo.checkout("right", create=True)
    right = repo.commit("right", {A: None})

    found = contributions.prior_state(repo.root, (left, right), settled=_settled)

    assert found.states == (left, right)
    assert found.off_text == (A,)


# --- what a commit contributes ---------------------------------------------------------


def test_a_commit_contributes_what_it_holds_otherwise(repo: GitRepo) -> None:
    before = repo.head()
    after = repo.commit("edit", {A: "edited\n"})

    prior = contributions.prior_state(repo.root, (before,), settled=_settled)

    assert contributions.contributed(repo.root, prior, after) == {A}


def test_a_root_commit_contributes_every_file(repo: GitRepo) -> None:
    root = repo.head()

    found = contributions.contributed(repo.root, contributions.PriorState(()), root)

    assert found == {A, B}


def test_what_matches_one_side_of_a_conflict_is_not_the_merges_own(repo: GitRepo) -> None:
    left, right = _sides(repo, "left\n", "right\n")
    repo.checkout("left")
    repo.git("merge", "-q", "--no-commit", "right", check=False)
    merge = repo.commit("settled", {A: "left\n"})

    prior = contributions.prior_state(repo.root, (left, right), settled=_settled)

    assert contributions.contributed(repo.root, prior, merge) == frozenset()


def test_what_differs_from_both_sides_is_the_merges_own(repo: GitRepo) -> None:
    left, right = _sides(repo, "left\n", "right\n")
    repo.checkout("left")
    repo.git("merge", "-q", "--no-commit", "right", check=False)
    merge = repo.commit("settled", {A: "both\n"})

    prior = contributions.prior_state(repo.root, (left, right), settled=_settled)

    assert contributions.contributed(repo.root, prior, merge) == {A}


def test_a_raw_diff_gives_each_side_of_a_path(repo: GitRepo) -> None:
    before = repo.head()
    after = repo.commit("add", {"new.txt": "new\n"})

    ((path, (was, now)),) = contributions.raw_diff(repo.root, before, after)

    assert path == "new.txt"
    assert was[0] == contributions.ABSENT and now[0] != contributions.ABSENT


# --- which commits ---------------------------------------------------------------------


def test_a_change_is_what_the_head_reaches_and_the_tip_does_not(repo: GitRepo) -> None:
    tip = repo.head()
    repo.checkout("change", create=True)
    first = repo.commit("first", {A: "1\n"})
    second = repo.commit("second", {A: "2\n"})

    found = contributions.change_commits(repo.root, tip, second)

    assert [commit.commit for commit in found] == [first, second]
    assert [commit.subject for commit in found] == ["first", "second"]
    assert found[1].parents == (first,)


@pytest.mark.parametrize("separator", LINE_SEPARATORS, ids=ascii)
def test_a_subject_holding_a_line_separator_stays_one_commit(repo: GitRepo, separator: str) -> None:
    tip = repo.head()
    repo.checkout("change", create=True)
    subject = f"accept{separator}it"
    first = repo.commit(subject, {A: "1\n"})
    second = repo.commit("second", {A: "2\n"})

    found = contributions.change_commits(repo.root, tip, second)

    assert [commit.commit for commit in found] == [first, second]
    assert found[0].subject == subject


def test_a_change_holds_a_parallel_line_parents_before_children(repo: GitRepo) -> None:
    tip = repo.head()
    repo.checkout("line", create=True)
    line = repo.commit("line", {A: "line\n"})
    repo.checkout("main")
    repo.checkout("change", create=True)
    own = repo.commit("own", {B: "own\n"})
    merge = repo.merge("line")

    found = [commit.commit for commit in contributions.change_commits(repo.root, tip, merge)]

    assert set(found) == {line, own, merge}
    assert found[-1] == merge


def test_descendants_leave_a_parallel_line_out(repo: GitRepo) -> None:
    tip = repo.head()
    repo.checkout("line", create=True)
    repo.commit("line", {A: "line\n"})
    repo.checkout("main")
    repo.checkout("change", create=True)
    own = repo.commit("own", {B: "own\n"})
    merge = repo.merge("line")
    commits = contributions.change_commits(repo.root, tip, merge)

    assert contributions.descendants(commits, own) == {merge}
    assert contributions.descendants(commits, merge) == frozenset()


def test_the_first_parent_line_runs_newest_first(repo: GitRepo) -> None:
    since = repo.head()
    first = repo.commit("first", {A: "1\n"})
    second = repo.commit("second", {A: "2\n"})

    found = contributions.first_parent_line(repo.root, since, second)

    assert found == [(second, [first]), (first, [since])]


def test_a_name_that_names_no_commit_raises(repo: GitRepo) -> None:
    with pytest.raises(FrictionCheckError, match="--head 'nope' names no commit"):
        contributions.commit_named(repo.root, "nope", "--head")


def test_a_branch_named_like_a_commits_id_is_refused(repo: GitRepo) -> None:
    other = repo.head()
    moved = repo.commit("moved", {A: "moved\n"})
    name = moved[:12]
    repo.git("branch", name, other)

    with pytest.raises(FrictionCheckError, match="reads as a commit's id"):
        contributions.commit_named(repo.root, name, "--head")
