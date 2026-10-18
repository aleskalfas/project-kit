"""Tests for `pkit friction since` (#1689, #1728; COR-050 points 3 and 16; project-management
DEC-055 point 3).

Every test stands up a real adopter repository: a page on `main`, a branch
whose head was authorised, and later commits on that branch — answers given
again, `revisited` entries written again, merges of `main`, other edits — so
the command reads real commits and git's own merges.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from types import ModuleType

import pytest
from click.testing import CliRunner, Result

from project_kit import default_branch as db
from project_kit import friction_since as fs
from project_kit.cli import main
from project_kit.friction_git import FrictionCheckError
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.friction_documents import CONFIG, SOURCE, document, friction_config

REPO_ROOT = Path(__file__).resolve().parent.parent
PAGE = "docs/guide.md"
OTHER = "docs/other.md"
T0 = "2026-09-01T09:00:00Z"
T1 = "2026-10-01T09:00:00Z"
T2 = "2026-10-02T09:40:12Z"
T3 = "2026-10-03T08:00:00Z"
BODY = "The CLI takes one flag.\n"


def _page(
    at: str | None = T0,
    because: str = "the CLI is as described",
    *,
    body: str = BODY,
    deferred: str = "",
    title: str = "The guide",
    revisited: str = "",
) -> str:
    """The page in block style: its block, its `revisited` list, its own field after
    them, and a body."""
    block = (
        f"    revalidated:\n      at: {at}\n      outcome: unchanged\n"
        f"      unchanged-because: {because}\n{deferred}"
        if at is not None
        else ""
    )
    return (
        f"---\nid: guide\npkit:\n  friction:\n    anchors:\n      path: [src/cli/**]\n"
        f"{block}{revisited}status: draft\n---\n\n# {title}\n\n{body}"
    )


TEST_CLI = "tests/test_cli.py"
TEST_CORE = "tests/test_core.py"


def _revisited(*entries: tuple[str, str, str]) -> str:
    """A `revisited` list in block style, as `pkit friction revisit` writes it: one entry
    per target, `(value, outcome, reason)`. `friction since` reads the entries whether
    or not a link lists their targets."""
    lines = "    revisited:\n"
    for value, outcome, reason in entries:
        lines += (
            f"      - anchor:\n          kind: path\n          value: {value}\n"
            f"        outcome: {outcome}\n        reason: {reason}\n"
        )
    return lines


def _flow_page(*entries: tuple[str, str, str], at: str = T0, empty: bool = False) -> str:
    """The page in flow style (JSON front matter), with a `revisited` list of `entries`
    — none written where there are none, unless `empty` writes it as `[]`."""
    text = document("flow", anchors={"path": ["src/**"]}, at=at)
    if not entries and not empty:
        return text
    front, body = text.split("\n---\n", 1)
    data = json.loads(front.removeprefix("---\n"))
    data["pkit"]["friction"]["revisited"] = [
        {"anchor": {"kind": "path", "value": value}, "outcome": outcome, "reason": reason}
        for value, outcome, reason in entries
    ]
    return f"---\n{json.dumps(data, indent=2)}\n---\n{body}"


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


# ---- the author's own commits --------------------------------------------------------


def test_an_answer_given_again_lies_inside_the_blocks(repo: AdopterRepo) -> None:
    since = _authorised(repo)
    head = repo.commit("answer again", {PAGE: _page(T1, "the rename keeps every flag")})
    found = _since(repo, since)
    assert found.all_inside
    assert found.inside == (PAGE,)
    assert found.outside == ()
    assert found.steps == (fs.Step(head, merges_base=False),)


def test_a_block_added_whole_lies_inside_and_one_removed_does_not(repo: AdopterRepo) -> None:
    """In block style the key's lines are taken out: a block a revalidation adds where
    there was none leaves the rest of the file as it was. A block removed drops an
    answer, so it lies outside."""
    since = _authorised(repo, {PAGE: _page(None)})
    repo.commit("revalidate it", {PAGE: _page(T1)})
    assert _since(repo, since).all_inside
    removed = repo.commit("take the block out", {PAGE: _page(None)})
    found = _since(repo, since)
    assert [(o.path, o.commit, o.why) for o in found.outside] == [
        (PAGE, removed, "a `revalidated` block was removed from it, which drops an answer")
    ]


@pytest.mark.parametrize(
    "emptied", ["    revalidated:\n", "    revalidated: {}\n", "    revalidated: nonsense\n"]
)
def test_a_block_emptied_lies_outside_as_one_removed(repo: AdopterRepo, emptied: str) -> None:
    """An emptied block drops its answer as a block removed does, and so does one turned
    to a value that is no mapping."""
    since = _authorised(repo)
    block = "    revalidated:\n      at: 2026-09-01T09:00:00Z\n      outcome: unchanged\n"
    block += "      unchanged-because: the CLI is as described\n"
    assert block in _page(T0)
    repo.commit("empty the block", {PAGE: _page(T0).replace(block, emptied)})
    (outside,) = _since(repo, since).outside
    assert outside.why == "a `revalidated` block was removed from it, which drops an answer"


def test_front_matter_with_a_yaml_anchor_lies_outside(repo: AdopterRepo) -> None:
    """An anchor inside the block, repeated by an alias outside it, would let the
    block's text change a field outside it while the text outside stays the same."""
    aliased = (
        _page(T0)
        .replace("      at: ", "      at: &when ")
        .replace("status: draft", "status: *when")
    )
    since = _authorised(repo, {PAGE: aliased})
    repo.commit("move the anchor's value", {PAGE: aliased.replace(T0, T1)})
    (outside,) = _since(repo, since).outside
    assert outside.path == PAGE and "YAML anchor" in outside.why


def test_an_object_that_cannot_be_read_is_never_read_as_empty(
    repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A partial clone that cannot fetch an object gives no answer, never two empty
    texts judged equal."""
    since = _authorised(repo)
    repo.commit("answer again", {PAGE: _page(T1)})
    monkeypatch.setattr(fs.BlobReader, "read_object", lambda self, obj: None)
    with pytest.raises(FrictionCheckError, match="could not be read"):
        _since(repo, since)


def test_deferrals_lie_inside_the_block(repo: AdopterRepo) -> None:
    since = _authorised(repo)
    deferred = (
        "      deferred:\n      - anchor: {kind: path, value: src/cli/**}\n        reason: x\n"
    )
    repo.commit("defer", {PAGE: _page(T1, deferred=deferred)})
    assert _since(repo, since).all_inside


def test_a_block_in_flow_style_changed_lies_inside_and_one_added_does_not(
    repo: AdopterRepo,
) -> None:
    """JSON front matter is YAML in flow style: there the key's characters are replaced
    by one marker, so a block changed lies inside, and a block added lies outside."""
    flow = "docs/flow.md"
    since = _authorised(repo, {flow: document("flow", anchors={"path": ["src/**"]}, at=T0)})
    repo.commit("again", {flow: document("flow", anchors={"path": ["src/**"]}, at=T1)})
    assert _since(repo, since).all_inside

    since = repo.commit("no block", {flow: document("flow", anchors={"path": ["src/**"]})})
    repo.commit("a block", {flow: document("flow", anchors={"path": ["src/**"]}, at=T2)})
    found = _since(repo, since)
    assert not found.all_inside
    assert [(o.path, o.why) for o in found.outside] == [
        (flow, "it changed outside its `revalidated` blocks and `revisited` lists")
    ]


# ---- `revisited` lists, read as blocks are (COR-050 point 16) ------------------------


def test_a_revisit_entry_rewritten_or_added_lies_inside(repo: AdopterRepo) -> None:
    """An entry written again with a new reason, and one added beside it, are answers
    given again: they lie inside the list, as a block given again lies inside."""
    first = (TEST_CLI, "unchanged", "the test asserts the old bound")
    since = _authorised(repo, {PAGE: _page(revisited=_revisited(first))})
    head = repo.commit(
        "write the entries again",
        {
            PAGE: _page(
                revisited=_revisited(
                    (TEST_CLI, "deferred", "the bound is revisited in issue 9999"),
                    (TEST_CORE, "unchanged", "the core test meets the new bound"),
                )
            )
        },
    )
    found = _since(repo, since)
    assert found.all_inside, found.outside
    assert found.inside == (PAGE,)
    assert found.steps == (fs.Step(head, merges_base=False),)


def test_a_revisited_list_added_whole_lies_inside_in_block_style(repo: AdopterRepo) -> None:
    """In block style the key's lines are taken out, so a list `pkit friction revisit`
    adds whole leaves the rest of the file as it was."""
    since = _authorised(repo)
    repo.commit("revisit", {PAGE: _page(revisited=_revisited((TEST_CLI, "unchanged", "why")))})
    found = _since(repo, since)
    assert found.all_inside, found.outside
    assert found.inside == (PAGE,)


BOTH = _revisited(
    (TEST_CLI, "unchanged", "the test asserts the old bound"),
    (TEST_CORE, "unchanged", "the core test still holds"),
)


def test_a_revisit_entry_removed_lies_inside_the_list(repo: AdopterRepo) -> None:
    """The list is the unit, as the block is: an entry removed from it, as a deferral
    removed from a block, is a change inside it."""
    since = _authorised(repo, {PAGE: _page(revisited=BOTH)})
    repo.commit(
        "drop an entry",
        {PAGE: _page(revisited=_revisited((TEST_CORE, "unchanged", "the core test still holds")))},
    )
    found = _since(repo, since)
    assert found.all_inside, found.outside
    assert found.inside == (PAGE,)


@pytest.mark.parametrize(
    "after",
    [
        _page(),
        _page(revisited="    revisited: []\n"),
        _page(revisited="    revisited:\n"),
        _page(revisited="    revisited: nonsense\n"),
    ],
    ids=["removed", "emptied", "no value", "no list"],
)
def test_a_revisited_list_removed_lies_outside(repo: AdopterRepo, after: str) -> None:
    """A list removed whole, emptied, or turned to a value that is no list, drops its
    answers, so it lies outside, as a block removed does."""
    since = _authorised(repo, {PAGE: _page(revisited=BOTH)})
    removed = repo.commit("drop the list", {PAGE: after})
    found = _since(repo, since)
    assert [(o.path, o.commit, o.why) for o in found.outside] == [
        (PAGE, removed, "a `revisited` list was removed from it, which drops its answers")
    ]


def test_a_revisited_list_in_flow_style(repo: AdopterRepo) -> None:
    """In flow style the list's characters are replaced by a marker: an entry rewritten,
    added or removed lies inside, and a list added where there was none lies outside, as
    a block added there does. A list emptied lies outside."""
    flow = "docs/flow.md"
    first = (TEST_CLI, "unchanged", "the test asserts the old bound")
    since = _authorised(repo, {flow: _flow_page(first)})
    repo.commit(
        "again",
        {
            flow: _flow_page(
                (TEST_CLI, "unchanged", "the test asserts a bound the change keeps"),
                (TEST_CORE, "deferred", "the core test is revisited in #9999"),
            )
        },
    )
    assert _since(repo, since).all_inside
    repo.commit("drop one", {flow: _flow_page(first)})
    assert _since(repo, since).all_inside

    emptied = repo.commit("empty the list", {flow: _flow_page(empty=True)})
    (outside,) = _since(repo, since).outside
    assert (outside.commit, outside.why) == (
        emptied,
        "a `revisited` list was removed from it, which drops its answers",
    )

    since = repo.commit("drop the list", {flow: _flow_page()})
    repo.commit("a list", {flow: _flow_page(first)})
    found = _since(repo, since)
    assert [(o.path, o.why) for o in found.outside] == [
        (flow, "it changed outside its `revalidated` blocks and `revisited` lists")
    ]


TERMS = "docs/terms.md"


def _terms(alpha: str | None, beta: str | None) -> str:
    """A collection of two entries, each with its own block and, given a reason, its own
    `revisited` list of one entry."""

    def entry(name: str, reason: str | None) -> str:
        lines = (
            f"{name}:\n  term: {name.title()}\n  pkit:\n    friction:\n"
            f"      anchors: {{path: [src/cli/**]}}\n      revalidated:\n"
            f"        at: {T0}\n        outcome: unchanged\n        unchanged-because: first\n"
        )
        if reason is not None:
            lines += (
                f"      revisited:\n      - anchor: {{kind: path, value: {TEST_CLI}}}\n"
                f"        outcome: unchanged\n        reason: {reason}\n"
            )
        return lines

    return f"---\n{entry('alpha', alpha)}{entry('beta', beta)}---\n\n## alpha\n\nAlpha.\n"


def test_the_lists_of_a_collections_entries(repo: AdopterRepo) -> None:
    """Each entry of a collection carries its own list: one rewritten lies inside, and one
    removed lies outside, as an entry's block does."""
    since = _authorised(repo, {TERMS: _terms("alpha's reason", "beta's reason")})
    repo.commit("rewrite alpha's", {TERMS: _terms("alpha's new reason", "beta's reason")})
    assert _since(repo, since).all_inside
    removed = repo.commit("drop beta's list", {TERMS: _terms("alpha's new reason", None)})
    found = _since(repo, since)
    assert [(o.path, o.commit, o.why) for o in found.outside] == [
        (TERMS, removed, "a `revisited` list was removed from it, which drops its answers")
    ]


def test_a_change_beside_a_revisit_entry_lies_outside(repo: AdopterRepo) -> None:
    """Only the entries are taken out: a field changed beside them is the author's
    change."""
    entries = _revisited((TEST_CLI, "unchanged", "the test asserts the old bound"))
    since = _authorised(repo, {PAGE: _page(revisited=entries)})
    changed = _page(revisited=entries.replace("old bound", "new bound")).replace(
        "status: draft", "status: final"
    )
    repo.commit("an entry and a field", {PAGE: changed})
    (outside,) = _since(repo, since).outside
    assert outside.why == "it changed outside its `revalidated` blocks and `revisited` lists"


@pytest.mark.parametrize(
    ("files", "why"),
    [
        ({PAGE: _page(T1, body="The CLI takes two flags.\n")}, "it changed outside"),
        ({PAGE: _page(T0, title="The new guide")}, "it changed outside"),
        ({"src/cli/main.py": "print('changed again')\n"}, "not an artefact's file"),
        ({"docs/new.md": _page(T1)}, "added"),
        ({PAGE: None}, "removed"),
    ],
)
def test_any_other_change_lies_outside(
    repo: AdopterRepo, files: dict[str, str | None], why: str
) -> None:
    since = _authorised(repo)
    head = repo.commit("another change", files)
    found = _since(repo, since)
    assert not found.all_inside
    (outside,) = found.outside
    assert outside.commit == head and why in outside.why


def test_a_change_of_line_endings_lies_outside(repo: AdopterRepo) -> None:
    since = _authorised(repo)
    repo.commit("CRLF", {PAGE: _page(T1).replace("\n", "\r\n")})
    (outside,) = _since(repo, since).outside
    assert outside.why == "its line endings changed"


def test_a_change_inside_and_one_outside_names_only_the_one_outside(repo: AdopterRepo) -> None:
    since = _authorised(repo)
    repo.commit("answer", {PAGE: _page(T1)})
    repo.commit("and a fix", {"src/core/engine.py": "ENGINE = 2\n"})
    found = _since(repo, since)
    assert not found.all_inside
    assert found.inside == (PAGE,)
    assert [o.path for o in found.outside] == ["src/core/engine.py"]


def test_the_same_commit_has_nothing_outside(repo: AdopterRepo) -> None:
    since = _authorised(repo)
    found = _since(repo, since, since)
    assert found.all_inside and found.steps == ()


# ---- merges of the base --------------------------------------------------------------


def test_a_clean_merge_of_the_base_counts_for_nothing(repo: AdopterRepo) -> None:
    """The base's own changes — code, another page, the page's body — are not the
    author's: a merge that takes them cleanly contributes nothing."""
    repo.checkout("main")
    repo.commit("base", {OTHER: _page(T2), "src/core/engine.py": "ENGINE = 3\n"})
    repo.checkout("topic", create=True)
    since = repo.commit("the change", {"src/cli/main.py": "print('cli, renamed')\n"})
    repo.checkout("main")
    repo.commit("base moves", {OTHER: _page(T3, body="Other.\n"), "src/x.py": "X = 1\n"})
    repo.checkout("topic")
    merge = repo.merge("main")
    head = repo.commit("answer again", {PAGE: _page(T1)})
    found = _since(repo, since)
    assert found.all_inside, found.outside
    assert found.steps == (fs.Step(merge, merges_base=True), fs.Step(head, merges_base=False))
    assert found.inside == (PAGE,)


def _conflicting_merge(repo: AdopterRepo, this: str, base: str) -> str:
    """`topic` authorised at a commit writing `this` to the page, `main` writing `base`,
    then `main` merged into `topic`, which leaves the conflict. Returns the authorised
    commit."""
    repo.checkout("topic", create=True)
    since = repo.commit("the change", {PAGE: this, "src/cli/main.py": "print('renamed')\n"})
    repo.checkout("main")
    repo.commit("base answers", {PAGE: base})
    repo.checkout("topic")
    merged = repo.git("merge", "-q", "--no-edit", "main", check=False)
    assert merged.returncode == 1, merged.stdout + merged.stderr
    return since


def _commit_merge(repo: AdopterRepo, page: str) -> str:
    repo.write({PAGE: page})
    repo.git("add", PAGE)
    repo.git("commit", "-q", "--no-edit")
    return repo.head()


def test_a_conflict_resolved_inside_the_blocks_lies_inside(repo: AdopterRepo) -> None:
    """Both sides answered on the page: the merge's conflict lies inside the block,
    and the answer given again there lies inside it too."""
    since = _conflicting_merge(repo, _page(T1, "this branch's reason"), _page(T2, "the base's"))
    merge = _commit_merge(repo, _page(T2, "the base's"))
    head = repo.commit("answer the combined state", {PAGE: _page(T3, "both changes hold")})
    found = _since(repo, since)
    assert found.all_inside, found.outside
    assert found.steps == (fs.Step(merge, merges_base=True), fs.Step(head, merges_base=False))


def test_a_conflict_resolved_inside_a_revisited_list_lies_inside(repo: AdopterRepo) -> None:
    """Both sides wrote the entry of one target: the merge's conflict lies inside the
    `revisited` list, taking the base side's entry lies inside it, and so does the
    entry written again for the combined state (COR-050 point 16)."""

    def entry(reason: str) -> str:
        return _page(revisited=_revisited((TEST_CLI, "unchanged", reason)))

    since = _conflicting_merge(repo, entry("this branch's reason"), entry("the base's reason"))
    merge = _commit_merge(repo, entry("the base's reason"))
    head = repo.commit("write the entry again", {PAGE: entry("both changes keep the bound")})
    found = _since(repo, since)
    assert found.all_inside, found.outside
    assert found.steps == (fs.Step(merge, merges_base=True), fs.Step(head, merges_base=False))
    assert found.inside == (PAGE,)


def test_an_entry_the_base_removed_through_a_conflict_lies_inside(repo: AdopterRepo) -> None:
    """The base removed the entry of a target this branch wrote again, as a change to
    the link's field makes it do. Resolving the conflict as the base did removes the
    entry inside the list, so the authorisation still covers the head."""
    repo.commit("both entries", {PAGE: _page(revisited=BOTH)})
    core = (TEST_CORE, "unchanged", "the core test still holds")
    rewritten = _revisited((TEST_CLI, "unchanged", "this branch's reason"), core)
    only_core = _page(revisited=_revisited(core))
    since = _conflicting_merge(repo, _page(revisited=rewritten), only_core)
    merge = _commit_merge(repo, only_core)
    found = _since(repo, since)
    assert found.all_inside, found.outside
    assert found.steps == (fs.Step(merge, merges_base=True),)


def test_a_conflict_resolved_outside_the_blocks_is_not(repo: AdopterRepo) -> None:
    """The body conflicts too: how the author resolved it is the author's change."""
    since = _conflicting_merge(
        repo, _page(T1, "this", body="This branch's body.\n"), _page(T2, "base", body="Base.\n")
    )
    merge = _commit_merge(repo, _page(T2, "base", body="Both, combined.\n"))
    found = _since(repo, since)
    assert not found.all_inside
    assert [(o.path, o.commit) for o in found.outside] == [(PAGE, merge)]


def test_a_conflict_taken_from_one_side_outside_the_blocks_is_not(repo: AdopterRepo) -> None:
    """Taking this branch's body over the base's is a choice outside the blocks, held
    against git's merge taking the other side."""
    since = _conflicting_merge(
        repo, _page(T1, "this", body="This branch's body.\n"), _page(T2, "base", body="Base.\n")
    )
    _commit_merge(repo, _page(T2, "base", body="This branch's body.\n"))
    assert not _since(repo, since).all_inside


def test_an_edit_made_inside_a_clean_merge_is_not(repo: AdopterRepo) -> None:
    since = _authorised(repo)
    repo.checkout("main")
    repo.commit("base", {"src/x.py": "X = 1\n"})
    repo.checkout("topic")
    repo.git("merge", "-q", "--no-ff", "--no-commit", "main")
    repo.write({"src/core/engine.py": "ENGINE = 9\n"})
    repo.git("add", "-A")
    repo.git("commit", "-q", "--no-edit")
    found = _since(repo, since)
    assert [o.path for o in found.outside] == ["src/core/engine.py"]


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
    head = repo.commit("answer again", {PAGE: _page(T1)})
    result = _cli(since[:10], "--head", head, "--base", "main", "--json")
    assert result.exit_code == 0, result.output
    document = json.loads(result.stdout)
    assert document == {
        "schema_version": 1,
        "report": "since",
        "since": since,
        "head": head,
        "base": {"ref": "main", "tip": repo.git("rev-parse", "main").stdout.strip()},
        "all_inside": True,
        "reason": None,
        "commits": [{"commit": head, "merges_base": False}],
        "inside": [PAGE],
        "outside": [],
    }


def test_a_change_outside_still_exits_0_and_says_why(repo: AdopterRepo) -> None:
    since = _authorised(repo)
    head = repo.commit("a fix", {"src/core/engine.py": "ENGINE = 2\n"})
    result = _cli(since, "--base", "main")
    assert result.exit_code == 0, result.output
    assert (
        f"  src/core/engine.py — outside, in {head[:12]}: not an artefact's file: no declared "
        "place holds it" in result.stdout.splitlines()
    )
    assert result.stdout.splitlines()[-1] == (
        "  Not all inside the blocks and lists: a change lies outside them."
    )


def test_a_name_that_is_no_commit_cannot_be_answered(repo: AdopterRepo) -> None:
    result = _cli("no-such-commit", "--base", "main")
    assert result.exit_code == 1
    assert "names no commit" in result.output


def test_a_tag_named_like_a_commit_id_is_refused(repo: AdopterRepo) -> None:
    """git reads a tag before a short id: a tag named like the authorised commit's id
    must not stand in for it."""
    since = _authorised(repo)
    repo.commit("answer again", {PAGE: _page(T1)})
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
    repo.commit("answer again", {PAGE: _page(T1)})
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
    repo.commit("base moves", {OTHER: _page(T3), "src/x.py": "X = 1\n"})
    repo.checkout("topic")
    repo.merge("main")
    repo.commit("answer again", {PAGE: _page(T1)})
    return since


def _resolved_inside(repo: AdopterRepo) -> str:
    since = _conflicting_merge(repo, _page(T1, "this branch's"), _page(T2, "the base's"))
    _commit_merge(repo, _page(T2, "the base's"))
    repo.commit("answer the combined state", {PAGE: _page(T3, "both hold")})
    return since


def _revisit_resolved_inside(repo: AdopterRepo) -> str:
    def entry(reason: str) -> str:
        return _page(revisited=_revisited((TEST_CLI, "unchanged", reason)))

    since = _conflicting_merge(repo, entry("this branch's"), entry("the base's"))
    _commit_merge(repo, entry("the base's"))
    repo.commit("write the entry again", {PAGE: entry("both hold")})
    return since


def _resolved_outside(repo: AdopterRepo) -> str:
    since = _conflicting_merge(
        repo, _page(T1, "this", body="This branch's.\n"), _page(T2, "base", body="Base.\n")
    )
    _commit_merge(repo, _page(T2, "base", body="Both.\n"))
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
        _resolved_inside,
        _revisit_resolved_inside,
        _resolved_outside,
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
