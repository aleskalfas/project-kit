"""The change check reads answer files, against the change's own head (COR-062; ADR-068
point 6; #1871).

Nothing writes an answer file yet, so every answer file here is written by hand,
as in `test_answer_files.py`, whose helpers build them. Each test stands up a real
adopter repository, commits a base on `main`, branches `feature` off it and runs
the change check against `main`, as `test_friction_check.py` does. The guide's
block holds no answer, so its answers are read from the answer files.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit import answer_files as af
from project_kit import friction_check as fc
from project_kit.cli import main
from project_kit.friction_discovery import Anchor
from project_kit.friction_git import DiffEntry, FrictionCheckError
from tests.adopter_repo import AdopterRepo
from tests.friction_documents import CONFIG, SOURCE, T1, T2, document, friction_config, guide
from tests.test_answer_files import CLI, GUIDE, T3, answer_path, answers, bare_guide, entry
from tests.test_friction_revisit import DECISION, SOURCE_DOC, TEST_FILE, declare_linker, requirement


@pytest.fixture
def repo(committed_adopter: AdopterRepo) -> AdopterRepo:
    return committed_adopter


def _start(adopter: AdopterRepo, files: dict[str, str], mode: str = "warning") -> None:
    """Commit the base state on `main`, on the install the template committed, and branch
    `feature` off it."""
    adopter.write({CONFIG: friction_config(mode=mode), **SOURCE, **files})
    adopter.commit("base", files=None)
    adopter.checkout("feature", create=True)


def _run(adopter: AdopterRepo, base: str = "main", **kwargs: Any) -> fc.ChangeCheck:
    return fc.run_change_check(adopter.root, base, **kwargs)


def _kinds(result: fc.ChangeCheck) -> list[tuple[str, str | None, str | None]]:
    """(kind, location, answer) per finding, in report order."""
    return [
        (f.kind.value, f.location, None if f.answer is None else f.answer.value)
        for f in result.findings
    ]


#: The guide answered at T1 in the base's answer file `a0`.
ANSWERED = {GUIDE: bare_guide(), answer_path("a0"): answers(entry(at=T1))}

#: A change to the CLI the guide stands on.
CLI_CHANGE = {"src/cli/main.py": "print('cli v2')\n"}


# --- the three answers, read from answer files -----------------------------------------


def test_an_update_in_an_answer_file_answers_and_is_listed_with_its_file(
    repo: AdopterRepo,
) -> None:
    _start(repo, ANSWERED)
    repo.commit(
        "change the CLI, update the guide",
        {
            **CLI_CHANGE,
            GUIDE: bare_guide(body="Body, v2."),
            answer_path("x"): answers(entry(at=T2, outcome="updated", read=("a0",))),
        },
    )
    result = _run(repo)
    assert _kinds(result) == [("answered", GUIDE, "updated")]
    (answer,) = result.answers
    assert (answer.file, answer.answer, answer.status, answer.asked) == (
        answer_path("x"),
        "updated",
        fc.AnswerStatus.STANDS,
        True,
    )


def test_unchanged_with_a_reason_of_its_own_answers(repo: AdopterRepo) -> None:
    _start(repo, ANSWERED)
    repo.commit(
        "change the CLI; the guide holds",
        {**CLI_CHANGE, answer_path("x"): answers(entry(at=T2, because="a refactor", read=("a0",)))},
    )
    result = _run(repo)
    assert _kinds(result) == [("answered", GUIDE, "unchanged")]
    assert "a refactor" in result.findings[0].message


def test_unchanged_repeating_the_reason_it_read_is_a_bump(repo: AdopterRepo) -> None:
    """`unchanged-because` must differ from that of each revalidation it read (COR-062
    point 5): `a0` says the CLI still holds, and so does the new answer."""
    _start(repo, ANSWERED)
    repo.commit(
        "change the CLI; stamp the guide",
        {**CLI_CHANGE, answer_path("x"): answers(entry(at=T2, read=("a0",)))},
    )
    result = _run(repo)
    assert [kind for kind, *_ in _kinds(result)] == ["friction", "bump"]
    (answer,) = result.answers
    assert answer.status is fc.AnswerStatus.BUMP


def test_a_deferral_in_an_answer_file_covers_its_anchor(repo: AdopterRepo) -> None:
    _start(repo, ANSWERED)
    repo.commit(
        "change the CLI; defer the guide",
        {
            **CLI_CHANGE,
            answer_path("x"): answers(entry(read=("a0",), deferred=((CLI, "rewrite in #9"),))),
        },
    )
    result = _run(repo)
    assert _kinds(result) == [("answered", GUIDE, "deferred")]
    (answer,) = result.answers
    assert (answer.answer, answer.reason, answer.asked, answer.file) == (
        "deferred",
        "rewrite in #9",
        True,
        answer_path("x"),
    )


def test_a_deferral_replacing_one_it_read_keeps_its_point(repo: AdopterRepo) -> None:
    """A reworded deferral keeps the point of the one it replaces (COR-062 point 6), so it
    covers no change made since: the CLI's change is friction, and it is listed edited."""
    _start(
        repo,
        {GUIDE: bare_guide(), answer_path("a0"): answers(entry(deferred=((CLI, "until #1"),)))},
    )
    repo.commit(
        "change the CLI; reword the deferral",
        {
            **CLI_CHANGE,
            answer_path("x"): answers(entry(read=("a0",), deferred=((CLI, "until #2"),))),
        },
    )
    result = _run(repo)
    assert [kind for kind, *_ in _kinds(result)] == ["friction"]
    (answer,) = result.answers
    assert (answer.reason, answer.status) == ("until #2", fc.AnswerStatus.EDITED)


def test_a_value_the_answers_carried_before_is_written_back(repo: AdopterRepo) -> None:
    """`a1` replaced `a0` after the CLI changed; the change answers with `a0`'s value,
    which answers nothing, and is judged against `a0`'s point (COR-050 point 3) — a
    commit that added an answer file alone, and not the guide's."""
    _start(repo, {GUIDE: bare_guide()})
    repo.checkout("main")
    repo.commit("answer", {answer_path("a0"): answers(entry(at=T1))})
    repo.commit(
        "change the CLI; the guide holds",
        {
            **CLI_CHANGE,
            answer_path("a1"): answers(entry(at=T2, because="the CLI moved", read=("a0",))),
        },
    )
    repo.git("branch", "-f", "feature", "main")
    repo.checkout("feature")
    repo.commit(
        "write the old value back",
        {answer_path("x"): answers(entry(at=T1, because="as before", read=("a0", "a1")))},
    )
    result = _run(repo)
    assert [kind for kind, *_ in _kinds(result)] == ["friction"]
    assert "since its revalidation point" in result.findings[0].message
    (answer,) = result.answers
    assert answer.status is fc.AnswerStatus.WRITTEN_BACK


def test_removing_a_live_answer_judges_against_the_answer_it_brings_back(
    repo: AdopterRepo,
) -> None:
    """Removing `a1` makes `a0` live again: the guide is judged against `a0`'s point, and
    the CLI changed since (COR-062 point 8)."""
    _start(repo, ANSWERED)
    repo.checkout("main")
    repo.commit(
        "change the CLI; the guide holds",
        {
            **CLI_CHANGE,
            answer_path("a1"): answers(entry(at=T2, because="the CLI moved", read=("a0",))),
        },
    )
    repo.git("branch", "-f", "feature", "main")
    repo.checkout("feature")
    repo.commit("take the answer away", {answer_path("a1"): None})
    result = _run(repo)
    assert [kind for kind, *_ in _kinds(result)] == ["friction"]
    assert "since its revalidation point" in result.findings[0].message
    assert result.answers == ()


# --- what the change does to the folder ------------------------------------------------


def test_rewriting_an_answer_file_the_base_holds_fails_in_enforcing_mode(
    repo: AdopterRepo,
) -> None:
    _start(repo, ANSWERED, mode="enforcing")
    repo.commit("rewrite", {answer_path("a0"): answers(entry(at=T2, because="reworded"))})
    result = _run(repo)
    assert ("answer-file-rewritten", answer_path("a0"), None) in _kinds(result)
    assert result.failed


def test_a_prune_mixed_with_answers_fails_and_a_prune_alone_passes(repo: AdopterRepo) -> None:
    _start(
        repo,
        {**ANSWERED, answer_path("a1"): answers(entry(at=T2, because="later", read=("a0",)))},
        mode="enforcing",
    )
    repo.commit("prune", {answer_path("a0"): None})
    assert not _run(repo).failed  # `a0` holds no live answer: a prune alone owes nothing
    repo.commit(
        "and answer",
        {
            **CLI_CHANGE,
            answer_path("x"): answers(entry(at=T3, because="a refactor", read=("a1",))),
        },
    )
    result = _run(repo)
    assert ("prune-mixed", answer_path("a0"), None) in _kinds(result)
    assert result.failed


def test_a_file_put_back_writes_no_answer(repo: AdopterRepo) -> None:
    """A file with a path and a content the base's history held puts back an answer as it
    was: it is not listed, its value keeps its point, and it asks nothing of its `read`
    (COR-062 point 3). Written anew, the same answer would be listed as written back."""
    _start(repo, ANSWERED)
    repo.checkout("main")
    repo.commit("take the answer away", {answer_path("a0"): None})
    repo.git("branch", "-f", "feature", "main")
    repo.checkout("feature")
    repo.commit("put it back", {answer_path("a0"): answers(entry(at=T1))})
    result = _run(repo)
    assert result.findings == () and result.answers == ()
    repo.commit("and write it anew", {answer_path("x"): answers(entry(at=T1))})
    (anew,) = _run(repo).answers
    assert (anew.file, anew.status) == (answer_path("x"), fc.AnswerStatus.WRITTEN_BACK)


def test_a_file_paired_as_a_rename_is_one_removed_and_one_added() -> None:
    """Git may pair a removed answer file with an added one: the check reads the two
    apart, so a rename is a removal beside an addition (COR-062 point 3)."""
    found = af.changed_files(
        [
            DiffEntry("R", answer_path("x"), answer_path("a0"), 100),
            DiffEntry("M", answer_path("a1")),
            DiffEntry("D", answer_path("a2")),
            DiffEntry("A", answer_path("y")),
            DiffEntry("M", GUIDE),
        ]
    )
    assert (found.added, found.rewritten, found.removed) == (
        ("x.yaml", "y.yaml"),
        ("a1.yaml",),
        ("a0.yaml", "a2.yaml"),
    )


# --- what each answer read -------------------------------------------------------------


def test_an_answer_that_leaves_out_a_file_on_its_artefact_fails(repo: AdopterRepo) -> None:
    _start(repo, ANSWERED, mode="enforcing")
    repo.commit(
        "answer without reading",
        {**CLI_CHANGE, answer_path("x"): answers(entry(at=T2, because="a refactor"))},
    )
    result = _run(repo)
    (read,) = [f for f in result.findings if f.kind is fc.FindingKind.READ_INCOMPLETE]
    assert "a0.yaml" in read.message and fc.HEAD_ENV not in read.message
    assert result.failed


def test_an_answer_replaced_by_a_later_one_of_the_change_is_not_asked(repo: AdopterRepo) -> None:
    _start(repo, ANSWERED, mode="enforcing")
    repo.commit("first", {**CLI_CHANGE, answer_path("x"): answers(entry(at=T2, because="one"))})
    repo.commit(
        "second", {answer_path("y"): answers(entry(at=T3, because="two", read=("a0", "x")))}
    )
    result = _run(repo)
    assert not [f for f in result.findings if f.kind is fc.FindingKind.READ_INCOMPLETE]
    assert [a.file for a in result.answers] == [answer_path("y")]


# --- answers on nothing ----------------------------------------------------------------


def test_a_deferral_of_an_undeclared_anchor_and_an_entry_naming_nothing_fail(
    repo: AdopterRepo,
) -> None:
    _start(repo, ANSWERED, mode="enforcing")
    gone = fc.Anchor("path", "src/gone/**")
    repo.commit(
        "answer on nothing",
        {
            answer_path("x"): answers(entry(read=("a0",), deferred=((gone, "until #3"),))),
            answer_path("y"): answers(entry("docs/nothing.md", at=T2)),
        },
    )
    result = _run(repo)
    assert ("answers-nothing", GUIDE, None) in _kinds(result)
    assert ("answer-on-what-is-gone", answer_path("y"), None) in _kinds(result)
    assert result.failed


def test_a_revisit_entry_on_a_target_no_link_takes_fails(repo: AdopterRepo) -> None:
    """The guide declares no link, so a revisit entry on it names no target: it answers
    nothing, and fails in enforcing mode (COR-062 point 10)."""
    _start(repo, ANSWERED, mode="enforcing")
    repo.commit(
        "revisit nothing",
        {answer_path("x"): answers(entry(read=("a0",), revisited=((CLI, "unchanged", "holds"),)))},
    )
    result = _run(repo)
    (nothing,) = [f for f in result.findings if f.kind is fc.FindingKind.ANSWERS_NOTHING]
    assert (nothing.location, nothing.anchor) == (GUIDE, CLI)
    assert result.failed


def test_a_revisit_entry_answers_where_its_reason_differs_from_the_one_it_replaces(
    committed_adopter: AdopterRepo,
) -> None:
    """A changed statement asks the requirement to revisit both targets. In an answer
    file, an entry answers its target where its reason differs from that of each entry
    it replaces (COR-062 point 5): the decision's does, and the test's, repeating `a0`'s
    words, writes nothing, so its target is not revisited."""
    adopter = committed_adopter
    declare_linker(adopter.root)
    test, decision = Anchor("path", TEST_FILE), Anchor("path", DECISION)
    adopter.write(
        {
            CONFIG: friction_config(places=("docs",)),
            **SOURCE,
            TEST_FILE: "def test_latency():\n    assert answer_time() < 2\n",
            DECISION: "Cache the status.\n",
            SOURCE_DOC: requirement(at=None, outcome=None, because=None),
            answer_path("a0"): answers(
                entry(SOURCE_DOC, at=T1, revisited=((test, "unchanged", "the test checks it"),))
            ),
        }
    )
    adopter.commit("base", files=None)
    adopter.checkout("feature", create=True)
    adopter.commit(
        "tighten the statement",
        {
            SOURCE_DOC: requirement(
                statement="Status answers in 1 second.", at=None, outcome=None, because=None
            ),
            answer_path("x"): answers(
                entry(
                    SOURCE_DOC,
                    read=("a0",),
                    revisited=(
                        (test, "unchanged", "the test checks it"),
                        (decision, "unchanged", "the cache still meets one second"),
                    ),
                )
            ),
        },
    )
    result = _run(adopter)
    revisits = {
        (f.kind.value, f.anchor)
        for f in result.findings
        if f.kind in {fc.FindingKind.REVISITED, fc.FindingKind.UNREVISITED}
    }
    assert revisits == {("unrevisited", test), ("revisited", decision)}
    (listed,) = [a for a in result.answers if a.answer == fc.REVISITED]
    assert (listed.target, listed.file, listed.asked) == (decision, answer_path("x"), True)


def test_an_entry_naming_nothing_is_reported_never_failed(repo: AdopterRepo) -> None:
    """An answer whose location holds no artefact answers nothing, reported in every mode
    (COR-062 point 10)."""
    _start(repo, ANSWERED, mode="enforcing")
    repo.commit("answer on nothing", {answer_path("y"): answers(entry("docs/nothing.md", at=T2))})
    result = _run(repo)
    assert _kinds(result) == [("answer-on-what-is-gone", answer_path("y"), None)]
    assert not result.failed


def test_an_answer_file_is_read_beside_a_block_still_holding_answers(repo: AdopterRepo) -> None:
    """At head an artefact's answers are read from the answer files alone, its block's
    left to validation, which fails them (COR-062 points 1 and 10). The base is history, so
    its block is read there: the file's revalidation is a new value against it."""
    _start(repo, {GUIDE: guide()}, mode="enforcing")
    repo.commit("answer beside the block", {answer_path("x"): answers(entry(at=T2))})
    result = _run(repo)
    assert _kinds(result) == [("revalidated", GUIDE, "unchanged")]
    assert not result.failed
    assert [(a.answer, a.file) for a in result.answers] == [("unchanged", answer_path("x"))]


# --- moved out of the block ------------------------------------------------------------


def test_an_answer_moved_out_of_the_block_is_listed_apart_and_asks_nothing(
    repo: AdopterRepo,
) -> None:
    held = "the CLI surface is as described"
    _start(repo, {GUIDE: guide(anchors={"path": ["src/cli/**", "src/core/**"]})})
    repo.commit(
        "move the answers",
        {
            GUIDE: bare_guide(),
            answer_path("moved-0123456789ab"): answers(entry(at=T1, because=held)),
        },
    )
    result = _run(repo)
    assert result.findings == () and result.answers == ()
    (moved,) = result.moved
    assert (moved.moved, moved.reason, moved.file, moved.asked) == (
        True,
        held,
        answer_path("moved-0123456789ab"),
        False,
    )
    document = json.loads(fc.render_json(result))
    assert document["answers"] == [] and document["moved"][0]["moved"] is True


# --- answered apart --------------------------------------------------------------------


def test_a_revalidation_replacing_two_made_apart_is_flagged(repo: AdopterRepo) -> None:
    _start(
        repo,
        {
            GUIDE: bare_guide(),
            answer_path("a1"): answers(entry(at=T1, because="one")),
            answer_path("a2"): answers(entry(at=T2, because="two")),
        },
    )
    repo.commit(
        "judge both",
        {
            **CLI_CHANGE,
            answer_path("x"): answers(entry(at=T3, because="both, together", read=("a1", "a2"))),
        },
    )
    result = _run(repo)
    (answer,) = result.answers
    assert answer.replaces_apart == ("a1.yaml", "a2.yaml")
    assert "judges them together" in fc.render_human(result)


# --- the change's own head -------------------------------------------------------------


def test_the_own_head_may_be_head_or_a_parent_of_it(
    repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    _start(repo, ANSWERED)
    first = repo.commit("one", CLI_CHANGE)
    repo.commit("two", {"src/core/engine.py": "ENGINE = 2\n"})
    monkeypatch.setenv(fc.HEAD_ENV, first)
    named = _run(repo).head
    assert named is not None and (named.own, named.own_source) == (first, fc.HEAD_ENV)
    monkeypatch.setenv(fc.HEAD_ENV, "")
    result = _run(repo)
    assert result.head is not None and result.head.own == result.head.commit
    assert result.head.own_source is None


def test_an_own_head_neither_head_nor_its_parent_is_refused(
    repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    _start(repo, ANSWERED)
    root = repo.head()
    repo.commit("one", CLI_CHANGE)
    repo.commit("two", {"src/core/engine.py": "ENGINE = 2\n"})
    monkeypatch.setenv(fc.HEAD_ENV, root)
    with pytest.raises(FrictionCheckError, match="neither HEAD"):
        _run(repo)
    monkeypatch.setenv(fc.HEAD_ENV, "no-such-commit")
    with pytest.raises(FrictionCheckError, match="names no commit"):
        _run(repo)


def test_a_named_head_is_its_own_head_and_the_variable_is_not_read(
    repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    _start(repo, ANSWERED)
    head = repo.commit("one", CLI_CHANGE)
    monkeypatch.setenv(fc.HEAD_ENV, "no-such-commit")
    result = _run(repo, named=fc.named_head(repo.root, head))
    assert result.head is not None and result.head.own == head


def _host_merge(repo: AdopterRepo) -> str:
    """`main` gains an answer on the guide after the branch answered; a host's merge of
    the branch with `main` is checked out, detached. Returns the branch's head."""
    _start(repo, ANSWERED, mode="enforcing")
    branch = repo.commit(
        "change the CLI; the guide holds",
        {**CLI_CHANGE, answer_path("x"): answers(entry(at=T2, because="a refactor", read=("a0",)))},
    )
    repo.checkout("main")
    repo.commit(
        "an answer lands on main",
        {
            "src/core/engine.py": "ENGINE = 2\n",
            answer_path("z"): answers(entry(at=T3, because="the engine moved", read=("a0",))),
        },
    )
    repo.git("checkout", "-q", "--detach", "main")
    repo.git("merge", "-q", "--no-ff", "-m", "the host's merge", "feature")
    return branch


def test_a_host_merge_passes_against_the_own_head_and_reports_answered_apart(
    repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    branch = _host_merge(repo)
    monkeypatch.setenv(fc.HEAD_ENV, branch)
    result = _run(repo)
    assert not result.failed, _kinds(result)
    assert ("answered", GUIDE, "unchanged") in _kinds(result)
    assert ("answered-apart", GUIDE, None) in _kinds(result)
    (apart,) = result.apart_at_tip
    assert [r.file for r in apart.revalidations] == ["z.yaml"]
    document = json.loads(fc.render_json(result))
    assert document["answered_apart_at_tip"][0]["revalidations"][0]["file"] == answer_path("z")
    assert document["head"]["own"] == branch


def test_a_host_merge_fails_without_the_own_head_and_names_the_variable(
    repo: AdopterRepo,
) -> None:
    _host_merge(repo)
    result = _run(repo)
    assert result.failed
    (read,) = [f for f in result.findings if f.kind is fc.FindingKind.READ_INCOMPLETE]
    assert "z.yaml" in read.message and fc.HEAD_ENV in read.message


def test_the_command_reads_the_own_head_from_the_environment(
    repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    branch = _host_merge(repo)
    monkeypatch.chdir(repo.root)
    monkeypatch.setenv(fc.HEAD_ENV, branch)
    result = CliRunner().invoke(main, ["friction", "check", "--base", "main"])
    assert result.exit_code == 0, result.output
    assert f"Own head: {branch[:7]}" in result.output


# --- dormant -------------------------------------------------------------------------------


def test_without_answer_files_a_block_still_holding_answers_is_refused(
    repo: AdopterRepo,
) -> None:
    """The project's answers have not moved: the change check reads no block at head, so it
    says so once and names the move, never reporting the answer as missing (COR-062 point
    11)."""
    _start(repo, {GUIDE: guide()})
    repo.commit("change the CLI only", CLI_CHANGE)
    with pytest.raises(FrictionCheckError, match="have not moved into answer files"):
        _run(repo)


def test_a_document_without_a_block_answer_and_no_answer_file_reads_as_before(
    repo: AdopterRepo,
) -> None:
    _start(repo, {GUIDE: document("guide", anchors={"path": ["src/cli/**"]})})
    repo.commit("change the CLI only", CLI_CHANGE)
    assert [kind for kind, *_ in _kinds(_run(repo))] == ["friction"]
