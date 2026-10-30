"""Tests for the prune, `pkit friction prune` (`project_kit.friction_prune`; COR-062 point 8;
#2207).

Each test stands up a real adopter repository, its install committed once per session
(`committed_adopter`), with dated commits. It writes its answer files by hand, as
`test_answer_files.py` does, whose helpers build them, and plans or runs the prune at
HEAD. Which files a prune keeps though no answer in them is live is
`StateAnswers.prune`'s, tested in `test_answer_files.py`; here are the command's own
reading, refusals, consent and output, and what a prune owes the change check.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import friction_check as fc
from project_kit import friction_prune as fp
from project_kit import friction_repository as fr
from project_kit import friction_write
from project_kit.cli import main
from project_kit.friction_git import FrictionCheckError
from tests.adopter_repo import AdopterRepo, GitRepo, MakeAdopterRepo
from tests.friction_documents import CONFIG, T2, Timeline, document, friction_config
from tests.shipped_rule_sets import without_shipped_rule_sets
from tests.test_answer_files import GUIDE, T1, T3, answer_path, answers, bare_guide, entry

#: A second artefact, anchored to the engine, so one answer file can answer two.
OTHER = "docs/other.md"


def other() -> str:
    return document("other", anchors={"path": ["src/core/**"]})


@pytest.fixture
def timeline(committed_adopter: AdopterRepo) -> Timeline:
    """Dated commits on an adopter whose install the template committed, so a test's base
    commits only its own files."""
    return Timeline(committed_adopter)


def _replaced(timeline: Timeline, *, mode: str = "warning") -> None:
    """The guide answered in `a0`, then again in `a1`, which read `a0`: `a0` holds no live
    answer."""
    timeline.start({GUIDE: bare_guide()}, config=friction_config(mode=mode))
    timeline.commit("answer", {answer_path("a0"): answers(entry(at=T1))})
    timeline.commit(
        "answer again",
        {answer_path("a1"): answers(entry(at=T2, because="the CLI moved", read=("a0",)))},
    )


def _invoke(*args: str, input: str | None = None) -> tuple[int, str]:
    result = CliRunner().invoke(main, ["friction", "prune", *args], input=input)
    return result.exit_code, result.output


# --- what it removes ----------------------------------------------------------------------


def test_a_file_whose_answers_are_all_replaced_is_removed(timeline: Timeline) -> None:
    _replaced(timeline)
    root = timeline.adopter.root
    plan = fp.plan_prune(root)
    assert (plan.head, plan.files, plan.live) == (timeline.adopter.head(), 2, 1)
    assert (plan.remove, plan.kept) == ((answer_path("a0"),), ())

    assert fp.remove(root, plan) == (answer_path("a0"),)
    assert not (root / answer_path("a0")).exists()
    assert (root / answer_path("a1")).exists()
    # It removes from the working tree, and stages nothing.
    staged = timeline.adopter.git("diff", "--cached", "--name-only").stdout
    assert staged.strip() == ""


def test_a_file_holding_one_live_answer_stays_whole(timeline: Timeline) -> None:
    """`a0` answers the guide and `other`. `a1` replaces its answer on the guide, but its
    answer on `other` is live, so the file stays, with both entries."""
    timeline.start({GUIDE: bare_guide(), OTHER: other()})
    timeline.commit(
        "answer both",
        {answer_path("a0"): answers(entry(at=T1), entry(OTHER, at=T1, because="the engine holds"))},
    )
    timeline.commit(
        "answer the guide again",
        {answer_path("a1"): answers(entry(at=T2, because="the CLI moved", read=("a0",)))},
    )
    plan = fp.plan_prune(timeline.adopter.root)
    assert (plan.files, plan.live, plan.remove, plan.kept) == (2, 2, (), ())


def test_a_file_that_cannot_be_read_is_kept_and_named(timeline: Timeline) -> None:
    """What a file that does not parse holds cannot be judged, so the prune keeps it, says
    why, and removes the rest."""
    _replaced(timeline)
    timeline.commit("a broken file", {answer_path("bad"): "answers: [\n"})
    plan = fp.plan_prune(timeline.adopter.root)
    assert plan.remove == (answer_path("a0"),)
    (kept,) = plan.kept
    assert kept.path == answer_path("bad")
    assert "does not parse" in kept.why and "`pkit validate`" in kept.why


def test_with_no_answer_file_there_is_nothing_to_remove(timeline: Timeline) -> None:
    timeline.start({GUIDE: bare_guide()})
    plan = fp.plan_prune(timeline.adopter.root)
    assert (plan.files, plan.remove, plan.kept) == (0, (), ())
    assert "nothing to remove" in fp.render_plan(plan)


# --- what a prune owes ----------------------------------------------------------------------


def test_a_prune_owes_no_answer_in_the_change_check(timeline: Timeline) -> None:
    """A prune removes files and adds none, and changes no live answer (COR-062 point 8): in
    enforcing mode, the change check finds nothing, lists no answer and passes, and the
    whole-repository check judges the guide as before, with nothing left to prune."""
    _replaced(timeline, mode="enforcing")
    timeline.commit("change the CLI", {"src/cli/main.py": "print('cli v2')\n"})
    repo = timeline.adopter
    before = fr.run_repository_check(repo.root)
    repo.checkout("prune", create=True)
    fp.remove(repo.root, fp.plan_prune(repo.root))
    timeline.commit("prune")

    change = fc.run_change_check(repo.root, "main")
    assert (change.findings, change.answers, change.failed) == ((), (), False)

    after = fr.run_repository_check(repo.root)
    assert [(f.kind, f.location) for f in after.findings] == [
        (f.kind, f.location) for f in before.findings
    ]
    assert (after.answer_files, after.prunable) == (1, ())


# --- what it refuses --------------------------------------------------------------------------


def test_an_uncommitted_change_in_the_answer_folder_is_refused(timeline: Timeline) -> None:
    _replaced(timeline)
    timeline.adopter.write({answer_path("x"): answers(entry(at=T3, read=("a0", "a1")))})
    with pytest.raises(FrictionCheckError, match="uncommitted change"):
        fp.plan_prune(timeline.adopter.root)
    assert (timeline.adopter.root / answer_path("a0")).exists()


def test_a_repository_with_no_commit_is_refused(make_adopter_repo: MakeAdopterRepo) -> None:
    adopter = make_adopter_repo()
    adopter.write({CONFIG: friction_config(), GUIDE: bare_guide()})
    with pytest.raises(FrictionCheckError, match="commit first"):
        fp.plan_prune(adopter.root)


def test_no_place_declared_is_refused(timeline: Timeline) -> None:
    """With no place, every answer would read as one on what is gone."""
    without_shipped_rule_sets(timeline.adopter)
    _replaced(timeline)
    timeline.commit("no places", {CONFIG: friction_config(places=())})
    with pytest.raises(FrictionCheckError, match="no place is declared"):
        fp.plan_prune(timeline.adopter.root)


def test_a_shallow_clone_is_refused(timeline: Timeline, tmp_path: Path) -> None:
    _replaced(timeline)
    target = tmp_path / "shallow"
    timeline.adopter.git(
        "clone", "-q", "--depth", "1", f"file://{timeline.adopter.root}", str(target)
    )
    clone = GitRepo(target)
    with pytest.raises(FrictionCheckError, match="shallow"):
        fp.plan_prune(clone.root)


# --- the command --------------------------------------------------------------------------------


def test_the_command_removes_only_with_consent(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    _replaced(timeline)
    removed = timeline.adopter.root / answer_path("a0")

    code, output = _invoke()
    assert code == 1 and "without consent" in output and "--yes" in output
    assert removed.exists()

    code, output = _invoke("--dry-run")
    assert code == 0, output
    assert answer_path("a0") in output and "Dry run: nothing removed." in output
    assert removed.exists()

    monkeypatch.setattr(friction_write, "interactive", lambda: True)
    code, output = _invoke(input="n\n")
    assert code == 1 and removed.exists()
    code, output = _invoke(input="y\n")
    assert code == 0, output
    assert "Removed 1 answer file." in output and not removed.exists()


def test_yes_removes_and_says_what_is_left_to_do(timeline: Timeline) -> None:
    _replaced(timeline)
    code, output = _invoke("--yes")
    assert code == 0, output
    assert answer_path("a0") in output
    assert "Removed 1 answer file." in output and "change of its own" in output
    assert not (timeline.adopter.root / answer_path("a0")).exists()

    code, output = _invoke("--yes")
    assert code == 1 and "uncommitted change" in output


def test_the_json_document_needs_yes_or_a_dry_run(timeline: Timeline) -> None:
    _replaced(timeline)
    code, output = _invoke("--json")
    assert code == 2 and "--json asks nothing" in output
    code, output = _invoke("--yes", "--dry-run")
    assert code == 2 and "exclude each other" in output

    code, output = _invoke("--json", "--dry-run")
    assert code == 0, output
    document = json.loads(output)
    assert document == {
        "schema_version": fp.SCHEMA_VERSION,
        "report": "prune",
        "dry_run": True,
        "head": timeline.adopter.head(),
        "folder": ".pkit/project/friction/answers",
        "files": 2,
        "live": 1,
        "remove": [answer_path("a0")],
        "removed": [],
        "kept": [],
    }
    assert (timeline.adopter.root / answer_path("a0")).exists()

    code, output = _invoke("--json", "--yes")
    assert code == 0, output
    assert json.loads(output)["removed"] == [answer_path("a0")]
    assert not (timeline.adopter.root / answer_path("a0")).exists()


def test_the_whole_repository_check_names_the_command(timeline: Timeline) -> None:
    _replaced(timeline)
    result = fr.run_repository_check(timeline.adopter.root)
    assert result.prunable == ("a0.yaml",)
    assert "which a prune would remove (`pkit friction prune`)" in fr.render_human(result)
