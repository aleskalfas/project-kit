"""The friction writers write a change's answers into answer files of its own (COR-062
points 1, 4 and 10; ADR-068 point 3; #1873).

`revalidate`, `defer` and `revisit` write their answer in the one answer file in
the working tree that no commit holds, a new one where there is none. Its entry
names every other answer file present that answers the artefact in `read`. An
artefact whose block still holds an answer is refused, naming the move (#2032).
Every test stands up a real adopter repository, its install committed once per
session (`committed_adopter`); the ones the checks read commit real history.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from ruamel.yaml import YAML

from project_kit import answer_files as af
from project_kit import friction_check as fc
from project_kit import friction_repository as fr
from project_kit import friction_write as fw
from project_kit.cli import main
from project_kit.friction_discovery import Anchor
from project_kit.friction_validate import validate_friction
from tests.adopter_repo import AdopterRepo
from tests.friction_documents import CONFIG, SOURCE, T1, friction_config, guide
from tests.test_answer_files import GUIDE, answer_path, answers, bare_guide, entry

NOW = datetime(2026, 10, 5, 10, 0, 0, tzinfo=UTC)
LATER = datetime(2026, 10, 6, 11, 30, 0, tzinfo=UTC)
FOLDER = af.FOLDER

#: The name a writer gives a file it adds: its UTC time, then eight hexadecimal digits.
NAME = re.compile(r"^\d{8}T\d{6}Z-[0-9a-f]{8}\.yaml$")

_safe = YAML(typ="safe")


@pytest.fixture
def repo(committed_adopter: AdopterRepo) -> AdopterRepo:
    committed_adopter.write({CONFIG: friction_config(), **SOURCE, GUIDE: bare_guide()})
    return committed_adopter


def _answer_files(repo: AdopterRepo) -> dict[str, str]:
    """The answer files on disk, by name, with their text."""
    folder = repo.root / FOLDER
    if not folder.is_dir():
        return {}
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(folder.glob("*.yaml"))}


def _entries(text: str) -> list[dict[str, Any]]:
    return _safe.load(text)["answers"]


def _errors(repo: AdopterRepo) -> list[str]:
    return [f"{f.where}: {f.message}" for f in validate_friction(repo.root).errors]


# --- where an answer is written -----------------------------------------------------------


def test_a_revalidation_of_an_artefact_whose_block_holds_none_adds_an_answer_file(
    repo: AdopterRepo,
) -> None:
    before = (repo.root / GUIDE).read_text(encoding="utf-8")
    plan = fw.plan_revalidate(
        repo.root, "guide", outcome="unchanged", because="the CLI still holds", now=NOW
    )
    assert plan.answer_file and plan.creates and plan.before == ""
    assert plan.rel.startswith(f"{FOLDER}/") and NAME.match(af.name_of(plan.rel))
    assert af.name_of(plan.rel).startswith("20261005T100000Z-")
    assert plan.after == (
        "answers:\n"
        "  - artefact: docs/guide.md\n"
        "    revalidated:\n"
        "      at: 2026-10-05T10:00:00Z\n"
        "      outcome: unchanged\n"
        "      unchanged-because: the CLI still holds\n"
    )
    assert (plan.first_line, plan.last_line) == (2, 6)
    assert plan.target == "answers[docs/guide.md].revalidated"
    assert "read: no other answer file answers it" in plan.items
    fw.write(plan)
    assert (repo.root / GUIDE).read_text(encoding="utf-8") == before
    assert list(_answer_files(repo)) == [af.name_of(plan.rel)]
    assert _errors(repo) == []


def test_later_answers_of_the_change_go_into_the_same_uncommitted_file(
    repo: AdopterRepo,
) -> None:
    fw.write(fw.plan_revalidate(repo.root, "guide", outcome="updated", now=NOW))
    fw.write(fw.plan_defer(repo.root, "guide", anchor="src/core/**", reason="#12 rewrites it"))
    (name,) = _answer_files(repo)
    (only,) = _entries(_answer_files(repo)[name])
    assert only == {
        "artefact": GUIDE,
        "revalidated": {
            "at": datetime(2026, 10, 5, 10, 0, tzinfo=UTC),
            "outcome": "updated",
            "deferred": [
                {"anchor": {"kind": "path", "value": "src/core/**"}, "reason": "#12 rewrites it"}
            ],
        },
    }
    assert _errors(repo) == []


def test_a_committed_answer_file_is_never_written_into_and_the_next_answer_names_it(
    repo: AdopterRepo,
) -> None:
    fw.write(fw.plan_revalidate(repo.root, "guide", outcome="updated", now=NOW))
    repo.commit("answer", files=None)
    (first,) = _answer_files(repo)
    committed = _answer_files(repo)[first]
    plan = fw.plan_revalidate(
        repo.root, "guide", outcome="unchanged", because="a second look", now=LATER
    )
    assert plan.creates and af.name_of(plan.rel) != first
    fw.write(plan)
    assert _answer_files(repo)[first] == committed
    (second,) = _entries(plan.after)
    assert second["read"] == [first]
    assert f"read: {first}" in plan.items


def test_two_uncommitted_files_answering_one_artefact_refuse_naming_both(
    repo: AdopterRepo,
) -> None:
    repo.write(
        {
            answer_path("20261001T000000Z-aaaaaaaa"): answers(entry(at=T1)),
            answer_path("20261002T000000Z-bbbbbbbb"): answers(entry(at="2026-10-02T00:00:00Z")),
        }
    )
    for plan in (
        lambda: fw.plan_revalidate(repo.root, "guide", outcome="updated", now=NOW),
        lambda: fw.plan_defer(repo.root, "guide", anchor="src/cli/**", reason="later"),
    ):
        with pytest.raises(fw.FrictionWriteError) as refused:
            plan()
        message = str(refused.value)
        assert "20261001T000000Z-aaaaaaaa.yaml" in message
        assert "20261002T000000Z-bbbbbbbb.yaml" in message
        assert "COR-062 point 10" in message


def test_an_uncommitted_file_answering_other_artefacts_takes_the_entry(
    repo: AdopterRepo,
) -> None:
    repo.write(
        {
            "docs/notes.md": bare_guide().replace('"guide"', '"notes"'),
            answer_path("20261001T000000Z-cccccccc"): answers(entry("docs/notes.md", at=T1)),
        }
    )
    plan = fw.plan_revalidate(repo.root, "guide", outcome="updated", now=NOW)
    assert not plan.creates and plan.rel == answer_path("20261001T000000Z-cccccccc")
    fw.write(plan)
    assert [e["artefact"] for e in _entries(plan.after)] == ["docs/notes.md", GUIDE]
    assert (plan.first_line, plan.last_line) == (7, 10)
    assert _errors(repo) == []


@pytest.mark.parametrize("ref", ["MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "REBASE_HEAD"])
def test_a_merge_or_rebase_in_progress_brings_files_that_are_not_the_writers_own(
    repo: AdopterRepo, ref: str
) -> None:
    """A file another line added, staged by a merge, a cherry-pick, a revert or a rebase
    stopped before its commit, is that line's: the writer adds a file of its own (COR-062
    point 10)."""
    repo.commit("base", files=None)
    repo.checkout("other", create=True)
    theirs = answer_path("20261001T000000Z-dddddddd")
    repo.commit("their answer", {theirs: answers(entry("docs/notes.md", at=T1))})
    other = repo.head()
    repo.checkout("main")
    repo.write({theirs: answers(entry("docs/notes.md", at=T1))})
    (repo.root / ".git" / ref).write_text(f"{other}\n", encoding="utf-8")
    plan = fw.plan_revalidate(repo.root, "guide", outcome="updated", now=NOW)
    assert plan.creates and plan.rel != theirs


def test_a_file_the_move_wrote_is_never_the_writers_own(repo: AdopterRepo) -> None:
    """A file the move writes is named for its content (ADR-068 point 1), and sorts after a
    writer's by name. A writer run while it is uncommitted reads it and never writes into
    it. The newest file of the writer's own, by the time in its name, takes the entry."""
    moved, moved_text = answer_path("moved-0123456789ab"), answers(entry(at=T1))
    notes = answers(entry("docs/notes.md", at=T1))
    later = answer_path("20261002T000000Z-aaaaaaaa")
    repo.write({"docs/notes.md": bare_guide().replace('"guide"', '"notes"'), moved: moved_text})
    alone = fw.plan_revalidate(repo.root, "guide", outcome="unchanged", because="a look", now=NOW)
    assert alone.creates and NAME.match(af.name_of(alone.rel))
    assert _entries(alone.after)[0]["read"] == ["moved-0123456789ab.yaml"]
    repo.write({answer_path("20261001T000000Z-ffffffff"): notes, later: notes})
    plan = fw.plan_revalidate(repo.root, "guide", outcome="unchanged", because="a look", now=NOW)
    assert not plan.creates and plan.rel == later
    fw.write(plan)
    assert (repo.root / moved).read_text(encoding="utf-8") == moved_text
    assert _entries(plan.after)[-1]["read"] == ["moved-0123456789ab.yaml"]


# --- what an answer reads, keeps and refuses ------------------------------------------------


def test_a_revalidation_keeps_named_deferrals_and_drops_the_rest(repo: AdopterRepo) -> None:
    repo.write(
        {
            answer_path("a0"): answers(
                entry(at=T1, deferred=((Anchor("path", "src/core/**"), "#12 rewrites it"),))
            ),
            answer_path("a1"): answers(
                entry(deferred=((Anchor("path", "src/cli/**"), "#13 renames it"),), read=("a0",))
            ),
        }
    )
    repo.commit("answers", files=None)
    plan = fw.plan_revalidate(repo.root, "guide", outcome="updated", keep=["src/core/**"], now=NOW)
    assert "keeps deferral path:src/core/**   (#12 rewrites it)" in plan.items
    assert "drops deferral path:src/cli/**   (#13 renames it)" in plan.items
    (written,) = _entries(plan.after)
    assert written["read"] == ["a0.yaml", "a1.yaml"]
    assert written["revalidated"]["deferred"] == [
        {"anchor": {"kind": "path", "value": "src/core/**"}, "reason": "#12 rewrites it"}
    ]
    with pytest.raises(fw.FrictionWriteError, match="no live deferral of 'src/web/\\*\\*'"):
        fw.plan_revalidate(repo.root, "guide", outcome="updated", keep=["src/web/**"], now=NOW)


def test_a_justification_one_read_revalidation_gives_is_refused(repo: AdopterRepo) -> None:
    repo.write({answer_path("a0"): answers(entry(at=T1, because="the CLI still holds"))})
    repo.commit("answer", files=None)
    with pytest.raises(fw.FrictionWriteError, match="must differ from that of each revalidation"):
        fw.plan_revalidate(
            repo.root, "guide", outcome="unchanged", because=" the CLI  still holds", now=NOW
        )


def test_at_moves_past_a_value_a_read_revalidation_carries(repo: AdopterRepo) -> None:
    repo.write({answer_path("a0"): answers(entry(at="2026-10-05T10:00:00Z"))})
    repo.commit("answer", files=None)
    plan = fw.plan_revalidate(repo.root, "guide", outcome="updated", now=NOW)
    assert "at: 2026-10-05T10:00:01Z" in plan.items


def test_a_deferral_replaces_the_one_it_reads_and_the_same_reason_writes_nothing(
    repo: AdopterRepo,
) -> None:
    repo.write(
        {answer_path("a0"): answers(entry(deferred=((Anchor("path", "src/cli/**"), "#13"),)))}
    )
    repo.commit("answer", files=None)
    same = fw.plan_defer(repo.root, "guide", anchor="src/cli/**", reason=" #13 ")
    assert not same.changes and "already deferred with this reason" in (same.unchanged or "")
    reworded = fw.plan_defer(repo.root, "guide", anchor="src/cli/**", reason="#14 instead")
    assert any("replaces the deferral it reads" in item for item in reworded.items)
    (written,) = _entries(reworded.after)
    assert written["read"] == ["a0.yaml"] and "at" not in written["revalidated"]


def test_a_deferral_beside_the_changes_revalidation_keeps_what_its_read_gains(
    repo: AdopterRepo,
) -> None:
    """The change revalidated before another line's deferral landed; a deferral it writes
    after names that file, and re-states its deferral, which the revalidation never read."""
    fw.write(fw.plan_revalidate(repo.root, "guide", outcome="updated", now=NOW))
    repo.write(
        {answer_path("z0"): answers(entry(deferred=((Anchor("path", "src/core/**"), "#9"),)))}
    )
    repo.git("add", "--", answer_path("z0"))
    repo.git("commit", "-q", "-m", "their deferral", "--", answer_path("z0"))
    plan = fw.plan_defer(repo.root, "guide", anchor="src/cli/**", reason="#10")
    (written,) = _entries(plan.after)
    assert written["read"] == ["z0.yaml"]
    assert [d["anchor"]["value"] for d in written["revalidated"]["deferred"]] == [
        "src/cli/**",
        "src/core/**",
    ]


# --- a moved artefact ---------------------------------------------------------------------

#: Where the guide moves to, inside the same place.
MOVED = "docs/area/guide.md"

#: The base's answer on the guide at its old path: a revalidation and one deferral.
BASE_ANSWER = answers(
    entry(at=T1, because="the CLI still holds", deferred=((Anchor("path", "src/core/**"), "#12"),))
)


def _moved(repo: AdopterRepo, *, committed: bool) -> None:
    """`main` holds the guide at its old path, answered there in `a0`; the branch `feature`
    moves it with `git mv`, the move left uncommitted or committed."""
    repo.write({CONFIG: friction_config(mode="enforcing"), answer_path("a0"): BASE_ANSWER})
    repo.commit("base", files=None)
    repo.checkout("feature", create=True)
    (repo.root / MOVED).parent.mkdir()
    repo.git("mv", GUIDE, MOVED)
    if committed:
        repo.git("commit", "-q", "-m", "move the guide")


@pytest.mark.parametrize("committed", [False, True], ids=["uncommitted", "committed"])
@pytest.mark.parametrize(
    "write",
    [
        pytest.param(
            lambda root: fw.plan_revalidate(
                root, "guide", outcome="unchanged", because="the move keeps its words", now=NOW
            ),
            id="revalidate",
        ),
        pytest.param(
            lambda root: fw.plan_defer(root, "guide", anchor="src/cli/**", reason="#13", now=NOW),
            id="defer",
        ),
    ],
)
def test_an_answer_on_a_moved_artefact_reads_the_answers_at_its_old_path(
    repo: AdopterRepo, committed: bool, write: Callable[[Path], fw.Plan]
) -> None:
    """The writer reads an artefact's answers at every path its file had, as the history
    walk does, a move not yet committed included (COR-062 points 4 and 10; #2108)."""
    _moved(repo, committed=committed)
    plan = write(repo.root)
    (written,) = _entries(plan.after)
    assert written["artefact"] == MOVED
    assert written["read"] == ["a0.yaml"]
    assert "read: a0.yaml" in plan.items


def test_a_revalidation_of_a_moved_artefact_judges_the_answers_at_its_old_path(
    repo: AdopterRepo,
) -> None:
    """The answers at the old path are live for the moved artefact: a deferral there can be
    kept, and its revalidation's justification cannot be given again (COR-050 points 3
    and 4, COR-062 point 5)."""
    _moved(repo, committed=False)
    with pytest.raises(fw.FrictionWriteError, match="must differ from that of each revalidation"):
        fw.plan_revalidate(
            repo.root, "guide", outcome="unchanged", because="the CLI still holds", now=NOW
        )
    plan = fw.plan_revalidate(repo.root, "guide", outcome="updated", keep=["src/core/**"], now=NOW)
    assert "keeps deferral path:src/core/**   (#12)" in plan.items
    (written,) = _entries(plan.after)
    assert written["revalidated"]["deferred"] == [
        {"anchor": {"kind": "path", "value": "src/core/**"}, "reason": "#12"}
    ]


def test_the_change_check_passes_a_move_answered_through_the_writer_alone(
    repo: AdopterRepo,
) -> None:
    """A move answered through the writer, with no hand edit, names the answers at the old
    path, so the change check fails nothing once it is committed (#2108)."""
    _moved(repo, committed=False)
    fw.write(
        fw.plan_revalidate(
            repo.root, "guide", outcome="unchanged", because="the move keeps its words", now=NOW
        )
    )
    repo.commit("move the guide and answer it", files=None)
    result = fc.run_change_check(repo.root, "main")
    assert not result.failed, [(f.kind, f.message) for f in result.findings]
    assert fc.FindingKind.READ_INCOMPLETE not in [f.kind for f in result.findings]
    assert [(f.kind, f.location) for f in result.findings if f.answer is not None] == [
        (fc.FindingKind.ANSWERED, MOVED)
    ]


# --- what is refused --------------------------------------------------------------------


def test_an_answer_folder_that_is_a_link_is_refused(repo: AdopterRepo, tmp_path: Any) -> None:
    (repo.root / ".pkit" / "project" / "friction").mkdir(parents=True, exist_ok=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (repo.root / FOLDER).symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises(fw.FrictionWriteError, match="is a link or a file"):
        fw.plan_revalidate(repo.root, "guide", outcome="updated", now=NOW)
    assert list(elsewhere.iterdir()) == []


def test_an_own_file_that_does_not_read_is_refused(repo: AdopterRepo) -> None:
    repo.write({answer_path("20261001T000000Z-eeeeeeee"): "answers: [\n"})
    with pytest.raises(fw.FrictionWriteError, match="mend it or remove it first"):
        fw.plan_revalidate(repo.root, "guide", outcome="updated", now=NOW)


@pytest.mark.parametrize(
    "write",
    [
        pytest.param(
            lambda root: fw.plan_revalidate(root, "guide", outcome="updated", now=NOW),
            id="revalidate",
        ),
        pytest.param(
            lambda root: fw.plan_defer(root, "guide", anchor="src/cli/**", reason="r", now=NOW),
            id="defer",
        ),
    ],
)
def test_a_block_still_holding_an_answer_is_refused_naming_the_move(
    repo: AdopterRepo, write: Callable[[Path], fw.Plan]
) -> None:
    """No writer writes an answer in a block, nor beside one a block still holds: validation
    fails such a block, and the move takes it out (COR-062 points 1, 10 and 11)."""
    repo.write({GUIDE: guide()})
    before = (repo.root / GUIDE).read_bytes()
    with pytest.raises(fw.FrictionWriteError) as refused:
        write(repo.root)
    assert "its block still holds answers" in str(refused.value.message)
    assert af.MOVE_COMMAND in str(refused.value.message)
    assert (repo.root / GUIDE).read_bytes() == before
    assert _answer_files(repo) == {}


# --- the command, and the checks that read what it wrote ------------------------------------


def test_the_command_shows_a_new_file_as_a_diff_from_nothing(repo: AdopterRepo) -> None:
    result = CliRunner().invoke(
        main, ["friction", "revalidate", "guide", "--outcome", "updated", "--dry-run"]
    )
    assert result.exit_code == 0, result.output
    assert "a new answer file of this change" in result.output
    assert "--- /dev/null" in result.output and "Dry run: nothing written." in result.output
    assert _answer_files(repo) == {}
    done = CliRunner().invoke(
        main, ["friction", "revalidate", "guide", "--outcome", "updated", "--yes"]
    )
    assert done.exit_code == 0, done.output
    (name,) = _answer_files(repo)
    assert f"Wrote answers[docs/guide.md].revalidated in {FOLDER}/{name}." in done.output


def test_the_change_check_reads_the_answer_the_writer_wrote(repo: AdopterRepo) -> None:
    repo.write({answer_path("a0"): answers(entry(at=T1))})
    repo.commit("base", files=None)
    repo.checkout("feature", create=True)
    repo.commit("change the CLI", {"src/cli/main.py": "print('v2')\n"})
    assert [f.kind for f in fc.run_change_check(repo.root, "main").findings] == [
        fc.FindingKind.FRICTION
    ]
    fw.write(
        fw.plan_revalidate(
            repo.root, "guide", outcome="unchanged", because="a refactor of the CLI", now=NOW
        )
    )
    result = fc.run_change_check(repo.root, "main")
    assert [(f.kind, f.answer) for f in result.findings] == [
        (fc.FindingKind.ANSWERED, fc.Answer.UNCHANGED)
    ]
    repo.commit("answer", files=None)
    after = fr.run_repository_check(repo.root)
    (report,) = [r for r in after.artefact_reports if r.location == GUIDE]
    assert report.state is fr.ArtefactState.CURRENT


# --- end to end: two branches that answer on one document merge with no conflict ---------


def _changed_and_answered(
    repo: AdopterRepo, branch: str, change: dict[str, str], why: str, now: datetime
) -> str:
    """Branch `branch` off `main`: change a file the guide anchors, answer the guide
    through the writer, and commit. Returns the branch's head."""
    repo.git("checkout", "-q", "-b", branch, "main")
    repo.write(change)
    fw.write(fw.plan_revalidate(repo.root, "guide", outcome="unchanged", because=why, now=now))
    return repo.commit(f"{branch}: change and answer", files=None)


def test_two_branches_answering_one_document_merge_one_after_the_other_with_no_conflict(
    repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """COR-062's promise, through the writers: each branch adds a file of its own, so the
    second merges after the first with no conflict and no merge round, and the pair shows
    as debt until a third revalidation reads both (points 4 and 7; ADR-068 point 6)."""
    repo.write(
        {CONFIG: friction_config(mode="enforcing"), answer_path("a0"): answers(entry(at=T1))}
    )
    repo.commit("base", files=None)
    _changed_and_answered(
        repo, "one", {"src/cli/main.py": "print('v2')\n"}, "the CLI's flags are as described", NOW
    )
    assert not fc.run_change_check(repo.root, "main").failed
    two = _changed_and_answered(
        repo, "two", {"src/core/engine.py": "ENGINE = 2\n"}, "the engine is one module", LATER
    )
    assert not fc.run_change_check(repo.root, "main").failed

    # The first lands, with no conflict.
    repo.checkout("main")
    repo.merge("one")

    # The second, never updated, is checked on the host's merge against its own head.
    repo.git("checkout", "-q", "--detach", "main")
    repo.git("merge", "-q", "--no-ff", "-m", "the host's merge", "two")
    monkeypatch.setenv(fc.HEAD_ENV, two)
    hosted = fc.run_change_check(repo.root, "main")
    assert not hosted.failed, [(f.kind, f.message) for f in hosted.findings]
    assert (fc.FindingKind.ANSWERED_APART, GUIDE) in [(f.kind, f.location) for f in hosted.findings]
    monkeypatch.delenv(fc.HEAD_ENV)

    # It lands too, with no conflict; the pair is debt, never staleness.
    repo.checkout("main")
    repo.merge("two")
    landed = fr.run_repository_check(repo.root)
    apart = [f for f in landed.findings if f.kind is fr.RepositoryFindingKind.ANSWERED_APART]
    assert [f.location for f in apart] == [GUIDE]
    (report,) = [r for r in landed.artefact_reports if r.location == GUIDE]
    assert report.state is fr.ArtefactState.CURRENT
    names = sorted(_answer_files(repo))
    assert len(names) == 3 and "a0.yaml" in names  # the base's, and one of each branch's

    # A third revalidation through the writer reads both, and clears the debt.
    plan = fw.plan_revalidate(
        repo.root, "guide", outcome="unchanged", because="the CLI and the engine together", now=NOW
    )
    (third,) = _entries(plan.after)
    assert third["read"] == names
    fw.write(plan)
    repo.commit("judge the combined state", files=None)
    cleared = fr.run_repository_check(repo.root)
    assert not [f for f in cleared.findings if f.kind is fr.RepositoryFindingKind.ANSWERED_APART]
