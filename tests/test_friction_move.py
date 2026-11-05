"""The move of a project's answers out of the artefacts' blocks: its plan, and the backbone
migration that writes it (COR-062 points 3, 6 and 11; ADR-068 points 1 and 7; #1873).

`pkit friction move-plan --json` plans the move and writes nothing. The migration
`2.0.0/002-move-answers-to-files.sh` writes the plan's bytes. Each test stands up a
real adopter repository with block answers, committed on the install the template
committed (`committed_adopter`), so the checks read them. Validation fails an answer
left in a block, and names the move (#2031). A test of the migration runs it as an
upgrade does, a shell script. One of them has it start the real `pkit`; the others
give it a `pkit` that prints the plan the real code made in the test's own process.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit import answer_files as af
from project_kit import friction_check as fc
from project_kit import friction_move as fm
from project_kit import friction_repository as fr
from project_kit import friction_validate as fv
from project_kit.cli import main
from project_kit.friction_validate import validate_friction
from tests.adopter_repo import AdopterRepo
from tests.friction_documents import CONFIG, SOURCE, T1, T2, document, friction_config, guide

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    REPO_ROOT / ".pkit" / "migrations" / "backbone" / "2.0.0" / "002-move-answers-to-files.sh"
)

GUIDE = "docs/guide.md"
TERMS = "docs/terms.md"
PLAIN = "docs/plain.md"

#: The guide, its block holding a revalidation that keeps one deferral.
GUIDE_TEXT = guide(
    anchors={"path": ["src/cli/**", "src/core/**"]},
    deferred=[("path", "src/core/**", "the engine rewrite in issue 12")],
)

#: A collection in block style: `TERM-a` revalidated, `TERM-b` holding no answer.
TERMS_TEXT = f"""\
---
TERM-a:
  title: A
  pkit:
    friction:
      anchors: {{path: [src/core/**]}}
      revalidated:
        at: {T2}
        outcome: unchanged
        unchanged-because: the engine is still one module
      last-check: {{state: current, as-of: abc123}}
TERM-b:
  title: B
  pkit:
    friction:
      anchors: {{path: [src/cli/**]}}
---

## TERM-a

A.

## TERM-b

B.
"""

#: The guide's block, moved: what its answer file holds.
GUIDE_MOVED = (
    "answers:\n"
    "  - artefact: docs/guide.md\n"
    "    revalidated:\n"
    f"      at: {T1}\n"
    "      outcome: unchanged\n"
    "      unchanged-because: the CLI surface is as described\n"
    "      deferred:\n"
    "        - anchor:\n"
    "            kind: path\n"
    "            value: src/core/**\n"
    "          reason: the engine rewrite in issue 12\n"
)


@pytest.fixture
def repo(committed_adopter: AdopterRepo) -> AdopterRepo:
    adopter = committed_adopter
    adopter.write(
        {
            CONFIG: friction_config(),
            **SOURCE,
            GUIDE: GUIDE_TEXT,
            TERMS: TERMS_TEXT,
            PLAIN: document("plain", anchors={"path": ["src/cli/**"]}),
        }
    )
    adopter.commit("base", files=None)
    return adopter


def _apply(repo: AdopterRepo, plan: fm.MovePlan) -> None:
    """Write the plan's bytes, as the migration does: the answer files, then each file."""
    for moved in plan.files:
        for answer in moved.answers:
            path = repo.root / answer.path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(answer.text.encode("utf-8"))
        (repo.root / moved.path).write_bytes(moved.text.encode("utf-8"))


def _run(root: Path, path: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(MIGRATION)],
        env={
            "ROOT": str(root),
            "PATH": os.environ["PATH"] if path is None else path,
            "HOME": os.environ.get("HOME", ""),
            "PKIT_MIGRATION": "1",
        },
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def _printing(plan: fm.MovePlan, tmp_path_factory: pytest.TempPathFactory) -> str:
    """A `PATH` whose `pkit` prints `plan` as `pkit friction move-plan --json` prints it,
    the plan made by the real code in this process, so the migration runs on it without a
    process of `pkit`."""
    bin_dir = tmp_path_factory.mktemp("bin")
    plan_file = bin_dir / "plan.json"
    plan_file.write_text(fm.render_json(plan), encoding="utf-8")
    fake = bin_dir / "pkit"
    fake.write_text(f"#!/bin/sh\ncat '{plan_file}'\n", encoding="utf-8")
    fake.chmod(0o755)
    return f"{bin_dir}{os.pathsep}{os.environ['PATH']}"


def _points(repo: AdopterRepo) -> dict[str, Any]:
    """Each artefact's state and points, as the whole-repository check reads them."""
    result = fr.run_repository_check(repo.root)
    return {
        r.location: (r.state, [c.sha for c in r.revalidation_points])
        for r in result.artefact_reports
    }


# --- the plan -------------------------------------------------------------------------------


def test_the_plan_moves_each_block_s_answers_into_a_file_of_their_own(repo: AdopterRepo) -> None:
    plan = fm.plan_move(repo.root)
    assert [f.path for f in plan.files] == [GUIDE, TERMS]
    assert plan.left == ()
    guide_file, terms_file = plan.files
    (moved,) = guide_file.answers
    assert moved.artefact == GUIDE and moved.text == GUIDE_MOVED
    assert moved.path == f"{af.FOLDER}/{af.moved_name(GUIDE_MOVED)}"
    assert af.name_of(moved.path).startswith("moved-") and len(af.name_of(moved.path)) == 23
    assert guide_file.sha256 == hashlib.sha256((repo.root / GUIDE).read_bytes()).hexdigest()
    # The guide's block keeps its anchors and loses its answer, every other byte kept.
    assert '"revalidated"' not in guide_file.text and '"anchors"' in guide_file.text
    # A collection: only the entry holding an answer moves, and `last-check` stays.
    (term,) = terms_file.answers
    assert term.artefact == f"{TERMS}#TERM-a"
    assert terms_file.text == TERMS_TEXT.replace(
        f"      revalidated:\n        at: {T2}\n        outcome: unchanged\n"
        "        unchanged-because: the engine is still one module\n",
        "",
    )


def test_the_plan_writes_nothing_and_is_the_same_twice(repo: AdopterRepo) -> None:
    before = {p: (repo.root / p).read_bytes() for p in (GUIDE, TERMS, PLAIN)}
    first, second = fm.plan_move(repo.root), fm.plan_move(repo.root)
    assert first == second
    assert {p: (repo.root / p).read_bytes() for p in before} == before
    assert not (repo.root / af.FOLDER).exists()


def test_after_the_move_every_value_keeps_its_point_and_nothing_is_asked(
    repo: AdopterRepo,
) -> None:
    """Moving every answer out of the blocks moves no point (COR-062 point 6), and each
    answer the move adds is listed apart as moved, asking nobody (point 3)."""
    base = repo.head()
    repo.commit("change the CLI", {"src/cli/main.py": "print('v2')\n"})
    repo.checkout("move", create=True)
    _apply(repo, fm.plan_move(repo.root))
    assert validate_friction(repo.root).errors == ()
    repo.commit("move the answers", files=None)
    # Each value's point is still the commit whose block first carried it, read in history.
    assert _points(repo) == {
        GUIDE: (fr.ArtefactState.STALE, [base]),
        f"{TERMS}#TERM-a": (fr.ArtefactState.CURRENT, [base]),
        f"{TERMS}#TERM-b": (fr.ArtefactState.STALE, [base]),
        PLAIN: (fr.ArtefactState.STALE, [base]),
    }
    result = fc.run_change_check(repo.root, "main")
    assert result.answers == ()
    assert {m.location for m in result.moved} == {GUIDE, f"{TERMS}#TERM-a"}
    assert fm.plan_move(repo.root).files == ()


def test_a_flow_style_block_and_a_crlf_file_are_edited_exactly(repo: AdopterRepo) -> None:
    flow = (
        "---\r\nid: flow\r\npkit: {friction: {anchors: {path: [src/cli/**]}, "
        f"revalidated: {{at: {T1}, outcome: updated}}, last-check: {{state: current}}}}}}\r\n"
        "---\r\n\r\nBody.\r\n"
    )
    repo.write({"docs/flow.md": flow})
    (moved,) = [f for f in fm.plan_move(repo.root).files if f.path == "docs/flow.md"]
    assert moved.text == flow.replace(f"revalidated: {{at: {T1}, outcome: updated}}, ", "")


def test_what_cannot_move_exactly_is_left_with_why(repo: AdopterRepo) -> None:
    only = document("only", at=T1, outcome="updated")  # no anchors: the block's only key
    odd = guide().replace('"outcome": "unchanged"', '"outcome": "unchanged", "extra": 1')
    repo.write({"docs/only.md": only, "docs/odd.md": odd.replace('"guide"', '"odd"')})
    left = {x.artefact: x.reason for x in fm.plan_move(repo.root).left}
    assert "the block's only key" in left["docs/only.md"]
    assert "depart from the answer files' schema" in left["docs/odd.md"]


def test_an_artefact_left_changes_nothing_its_file_s_other_artefacts_are_judged_against(
    repo: AdopterRepo,
) -> None:
    """`TERM-a`'s `revalidated` comes out, then its `revisited` cannot, being the block's
    only key: `TERM-a` is left whole, and `TERM-b` beside it still moves."""
    terms = f"""\
---
TERM-a:
  title: A
  pkit:
    friction:
      revalidated:
        at: {T1}
        outcome: updated
      revisited:
        - anchor: {{kind: path, value: src/cli/**}}
          outcome: unchanged
          reason: the CLI is as it was
TERM-b:
  title: B
  pkit:
    friction:
      anchors: {{path: [src/cli/**]}}
      revalidated:
        at: {T2}
        outcome: updated
---

## TERM-a

A.

## TERM-b

B.
"""
    repo.write({TERMS: terms})
    plan = fm.plan_move(repo.root)
    left = {x.artefact: x.reason for x in plan.left}
    assert "the block's only key" in left[f"{TERMS}#TERM-a"]
    assert f"{TERMS}#TERM-b" not in left
    (moved,) = [f for f in plan.files if f.path == TERMS]
    assert [a.artefact for a in moved.answers] == [f"{TERMS}#TERM-b"]
    assert moved.text == terms.replace(
        f"      revalidated:\n        at: {T2}\n        outcome: updated\n---", "---"
    )


def test_the_command_prints_the_plan(repo: AdopterRepo) -> None:
    result = CliRunner().invoke(main, ["friction", "move-plan", "--json"])
    assert result.exit_code == 0, result.output
    document_ = json.loads(result.output)
    assert (document_["schema_version"], document_["report"], document_["folder"]) == (
        1,
        "move-plan",
        af.FOLDER,
    )
    assert [f["path"] for f in document_["files"]] == [GUIDE, TERMS]
    human = CliRunner().invoke(main, ["friction", "move-plan"])
    assert human.exit_code == 0 and "would add 2 answer file(s)" in human.output


# --- the migration --------------------------------------------------------------------------


@pytest.mark.process(
    "the migration's end-to-end test, as an upgrade runs it: a shell script that starts "
    "`pkit friction move-plan --json` and writes the bytes it prints"
)
def test_the_migration_writes_the_plan_and_a_second_run_writes_nothing(
    repo: AdopterRepo, pkit_on_path: Path
) -> None:
    planned = fm.plan_move(repo.root)
    result = _run(repo.root)
    assert result.returncode == 0, result.stderr
    assert "moved the answers of 2 artefact file(s) into 2 new answer file(s)" in result.stdout
    for moved in planned.files:
        assert (repo.root / moved.path).read_bytes() == moved.text.encode("utf-8")
        for answer in moved.answers:
            assert (repo.root / answer.path).read_bytes() == answer.text.encode("utf-8")
    assert validate_friction(repo.root).errors == ()
    state = {
        p: p.read_bytes() for p in repo.root.rglob("*") if p.is_file() and ".git" not in p.parts
    }

    again = _run(repo.root)
    assert again.returncode == 0, again.stderr
    assert "no block holds an answer to move" in again.stdout
    after = {
        p: p.read_bytes() for p in repo.root.rglob("*") if p.is_file() and ".git" not in p.parts
    }
    assert after == state


def test_the_migration_never_writes_over_an_answer_file(
    repo: AdopterRepo, tmp_path_factory: pytest.TempPathFactory
) -> None:
    planned = fm.plan_move(repo.root)
    taken = repo.root / planned.files[0].answers[0].path
    taken.parent.mkdir(parents=True)
    taken.write_text("answers: []\n", encoding="utf-8")
    result = _run(repo.root, _printing(fm.plan_move(repo.root), tmp_path_factory))
    assert result.returncode == 0, result.stderr
    assert "never written over" in result.stdout
    assert taken.read_text(encoding="utf-8") == "answers: []\n"
    assert (repo.root / GUIDE).read_text(encoding="utf-8") == GUIDE_TEXT
    assert (repo.root / TERMS).read_bytes() == planned.files[1].text.encode("utf-8")


def test_the_migration_finishes_a_move_an_earlier_run_left_halfway(
    repo: AdopterRepo, tmp_path_factory: pytest.TempPathFactory
) -> None:
    planned = fm.plan_move(repo.root)
    answer = planned.files[0].answers[0]
    (repo.root / answer.path).parent.mkdir(parents=True)
    (repo.root / answer.path).write_text(answer.text, encoding="utf-8")
    result = _run(repo.root, _printing(fm.plan_move(repo.root), tmp_path_factory))
    assert result.returncode == 0, result.stderr
    assert (repo.root / GUIDE).read_bytes() == planned.files[0].text.encode("utf-8")


@pytest.mark.parametrize("unreadable", ["artefact", "answer"])
def test_an_unreadable_file_is_reported_and_the_rest_of_the_run_kept(
    repo: AdopterRepo, tmp_path_factory: pytest.TempPathFactory, unreadable: str
) -> None:
    """The guide moves first. Then the terms' file, or an answer file already where the
    terms' answers go, cannot be read: that file is reported and left, and the guide's
    move is still reported."""
    if os.geteuid() == 0:
        pytest.skip("root reads a file whatever its mode")
    planned = fm.plan_move(repo.root)
    path = _printing(planned, tmp_path_factory)
    guide_file, terms_file = planned.files
    locked = repo.root / terms_file.path
    if unreadable == "answer":
        locked = repo.root / terms_file.answers[0].path
        locked.parent.mkdir(parents=True)
        locked.write_text("answers: []\n", encoding="utf-8")
    locked.chmod(0)
    try:
        result = _run(repo.root, path)
    finally:
        locked.chmod(0o644)
    assert result.returncode == 0, result.stderr
    assert "no answers moved" not in result.stdout
    assert f"[ok] moved the answers out of {GUIDE}" in result.stdout
    assert f"[warn] left as it is: {TERMS}: " in result.stdout
    assert "cannot be read" in result.stdout
    assert (repo.root / GUIDE).read_bytes() == guide_file.text.encode("utf-8")
    assert (repo.root / TERMS).read_text(encoding="utf-8") == TERMS_TEXT


def test_the_migration_escapes_the_project_s_text_in_its_report(
    repo: AdopterRepo, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """A reason or a path is the project's text: a line break in it cannot forge a line
    of the report."""
    plan = {
        "schema_version": 1,
        "report": "move-plan",
        "folder": af.FOLDER,
        "files": [],
        "left": [{"artefact": "evil\nDONE 9 9", "path": "evil", "reason": "\x1b[2Kgone"}],
    }
    bin_dir = tmp_path_factory.mktemp("bin")
    fake = bin_dir / "pkit"
    fake.write_text(f"#!/bin/sh\ncat <<'EOF'\n{json.dumps(plan)}\nEOF\n", encoding="utf-8")
    fake.chmod(0o755)
    result = _run(repo.root, f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    assert result.returncode == 0, result.stderr
    assert "moved the answers of 9" not in result.stdout
    assert "no block holds an answer to move" in result.stdout
    assert "evil\\nDONE 9 9" in result.stdout and "\\x1b[2K" in result.stdout


def test_the_migration_imports_no_backbone() -> None:
    script = MIGRATION.read_text(encoding="utf-8")
    assert "project_kit" not in script and "python3 -I" in script
    assert "pkit friction move-plan --json" in script


# --- validation, before the move and after it ------------------------------------------------

_BLOCK_KINDS = (fv.FrictionFindingKind.ANSWER_IN_BLOCK, fv.FrictionFindingKind.ANSWERS_NOT_MOVED)


def _block_findings(root: Path) -> list[fv.FrictionFinding]:
    return [f for f in validate_friction(root).findings if f.kind in _BLOCK_KINDS]


def test_validation_names_the_move_once_where_no_answer_file_exists(repo: AdopterRepo) -> None:
    """The guide and `TERM-a` hold answers in their blocks and no answer file exists: the
    project's answers have not moved. One error says so and names the move, never one per
    artefact (COR-062 point 11)."""
    (finding,) = _block_findings(repo.root)
    assert (finding.location, finding.kind.value, finding.severity) == (
        af.FOLDER,
        "answers-not-moved",
        fv.Severity.ERROR,
    )
    assert "2 artefacts hold answers in their own block" in finding.message
    assert af.MOVE_COMMAND in finding.message and "pkit friction move-plan" in finding.message
    assert REPO_ROOT / af.MOVE_MIGRATION == MIGRATION


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(("check", "--base", "HEAD"), id="change-check"),
        pytest.param(("check", "--all"), id="whole-repository-check"),
        pytest.param(("debt",), id="debt"),
        pytest.param(("explain", GUIDE), id="explain"),
    ],
)
def test_a_reader_refuses_once_where_the_answers_have_not_moved(
    repo: AdopterRepo, command: tuple[str, ...]
) -> None:
    """Every reader reads answers from answer files alone, and none exists: it says so once
    and names the move, never reporting each answer as missing (COR-062 point 11)."""
    result = CliRunner().invoke(main, ["friction", *command])
    assert result.exit_code != 0
    assert "2 artefacts hold answers in their own block" in result.output
    assert af.MOVE_COMMAND in result.output
    assert "the move has run" not in result.output
    assert "stale" not in result.output


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(("check", "--all"), id="whole-repository-check"),
        pytest.param(("debt",), id="debt"),
        pytest.param(("explain", GUIDE), id="explain"),
    ],
)
def test_a_reader_over_an_uncommitted_move_says_to_commit_it(
    repo: AdopterRepo, command: tuple[str, ...]
) -> None:
    """An upgrade ran the move and is not committed yet. The last commit, which these readers
    read, still holds the answers in their blocks and no answer file, and the working tree
    holds the files the move wrote. The reader says the move has run and the upgrade is to
    be committed, never to run the move again, and reads the answers once it is (#2186)."""
    _apply(repo, fm.plan_move(repo.root))
    result = CliRunner().invoke(main, ["friction", *command])
    assert result.exit_code != 0
    assert "2 artefacts hold answers in their own block at the last commit" in result.output
    assert "2 answer files the move wrote" in result.output
    assert "the move has run" in result.output and "`git commit`" in result.output
    assert af.MOVE_COMMAND not in result.output and "run the move" not in result.output
    assert "pkit validate" not in result.output

    repo.commit("upgrade", files=None)
    after = CliRunner().invoke(main, ["friction", *command])
    assert "the move has run" not in after.output
    assert "have not moved" not in after.output


def test_a_writer_s_uncommitted_file_is_no_move_that_has_run(repo: AdopterRepo) -> None:
    """Only a file the move wrote, `moved-…`, says the move has run: an uncommitted answer
    file of another name leaves the reader naming the move (#2186)."""
    folder = repo.root / af.FOLDER
    folder.mkdir(parents=True)
    (folder / "20261021T093000Z-3f9a2c1d.yaml").write_text("answers: []\n", encoding="utf-8")
    result = CliRunner().invoke(main, ["friction", "check", "--all"])
    assert result.exit_code != 0
    assert af.MOVE_COMMAND in result.output
    assert "the move has run" not in result.output


def test_a_reader_reads_no_answer_left_in_a_block_once_the_answers_moved(repo: AdopterRepo) -> None:
    """After the move a block's answer is read only in history: the plain page's answer,
    written in its block and never moved, answers nothing at HEAD, so the page is judged
    by the answer files alone (COR-062 point 1)."""
    _apply(repo, fm.plan_move(repo.root))
    repo.commit("move the answers", files=None)
    repo.commit("change the CLI", {"src/cli/main.py": "print('v2')\n"})
    answered = document("plain", anchors={"path": ["src/cli/**"]}, at=T2, outcome="updated")
    repo.commit("answer the plain page in its block", {PLAIN: answered})
    states = {r.location: r.state for r in fr.run_repository_check(repo.root).artefact_reports}
    assert states[PLAIN] is fr.ArtefactState.STALE
    check = fr.run_artefact_check(
        repo.root, lambda found: next(a for a in found.artefacts if a.location == PLAIN)
    )
    assert check is not None and check.answers is not None
    assert check.answers.revalidations == ()


def test_an_answer_written_in_a_block_beside_the_move_fails_until_the_move_runs_again(
    repo: AdopterRepo,
) -> None:
    """A line of work open at the move gives the plain page its first answer in its block,
    which held none, so it merges cleanly with the move. Validation then fails the answer
    left in the block, naming the move. The move, run again, takes it out into a new answer
    file and leaves every earlier one as it was (COR-062 points 10 and 11)."""
    repo.checkout("open", create=True)
    answered = document("plain", anchors={"path": ["src/cli/**"]}, at=T2, outcome="updated")
    repo.commit("answer the plain page in its block", {PLAIN: answered})
    repo.checkout("main")
    _apply(repo, fm.plan_move(repo.root))
    repo.commit("move the answers", files=None)
    folder = repo.root / af.FOLDER
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    repo.merge("open")

    (finding,) = _block_findings(repo.root)
    assert (finding.location, finding.pointer, finding.severity) == (
        PLAIN,
        "/pkit/friction/revalidated",
        fv.Severity.ERROR,
    )
    assert af.MOVE_COMMAND in finding.message

    again = fm.plan_move(repo.root)
    assert [f.path for f in again.files] == [PLAIN]
    _apply(repo, again)
    assert _block_findings(repo.root) == []
    assert validate_friction(repo.root).errors == ()
    after = {p.name: p.read_bytes() for p in folder.iterdir()}
    assert {name: after[name] for name in before} == before
    assert len(after) == len(before) + 1


@pytest.mark.parametrize("with_pkit", [False, True], ids=["no-pkit", "no-plan"])
def test_the_migration_never_fails_the_upgrade_when_the_plan_cannot_be_read(
    repo: AdopterRepo, tmp_path_factory: pytest.TempPathFactory, with_pkit: bool
) -> None:
    bin_dir = tmp_path_factory.mktemp("bin")
    if with_pkit:
        old = bin_dir / "pkit"
        old.write_text("#!/bin/sh\necho 'No such command' >&2\nexit 2\n", encoding="utf-8")
        old.chmod(0o755)
    result = _run(repo.root, f"{bin_dir}{os.pathsep}/usr/bin{os.pathsep}/bin")
    assert result.returncode == 0, result.stderr
    assert "[warn] no answers moved" in result.stdout
    assert (repo.root / GUIDE).read_text(encoding="utf-8") == GUIDE_TEXT
