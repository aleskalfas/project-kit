"""The fixers' proposals brought to the person, and what the person decides (#1747).

project-management DEC-056 point 6: the project manager brings the queue's
proposals to the person in one batch, each checked again at the default branch,
and applies what the person accepts through an ordinary pull request. A refusal
is remembered against the artefact's friction, and an answer to a held question
goes with the next brief. `_lib/proposals.py` holds the work, and
`show-proposals`, `apply-proposals`, `refuse-proposals` and `answer-question`
are its commands. No test starts an agent, and no writer runs: the writer is a
stub, and every reading at the default branch is stubbed.
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
COMMIT = "a" * 40


@pytest.fixture(scope="module")
def lib() -> tuple[ModuleType, ModuleType, ModuleType, ModuleType]:
    sys.path.insert(0, str(SCRIPTS_DIR))
    from _lib import drift, drift_queue, fixer_contract, proposals

    return proposals, drift, drift_queue, fixer_contract


def _script(name: str) -> ModuleType:
    sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(
        f"{name.replace('-', '_')}_under_test", SCRIPTS_DIR / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- a queue to work on ----------------------------------------------------------------------


def _explained(state: str = "stale", commit: str = "c" * 40) -> dict[str, Any]:
    return {
        "state": state,
        "revalidation_point": {"commit": "b" * 40},
        "findings": [
            {
                "kind": "stale",
                "anchor": {"kind": "path", "value": "src/x.py"},
                "commits": [{"commit": commit}],
            }
        ],
    }


def _answer(name: str, *, outcome: str = "updated", **fields: Any) -> dict[str, Any]:
    answer = {
        "artefact": name,
        "outcome": outcome,
        "justification": None if outcome == "updated" else "It still holds.",
        "sentence": "The page names the new flag." if outcome == "updated" else None,
        "keep": [],
        "diff": f"{name}/page.diff" if outcome == "updated" else None,
        "first": [],
    }
    answer.update(fields)
    return answer


DIFF = """--- a/{name}
+++ b/{name}
@@ -1,2 +1,2 @@
 # A page
-The flag is --old.
+The flag is --new.
"""


class Queue:
    """A queue in the test's folder, written as the drift command writes one."""

    def __init__(self, drift: ModuleType, drift_queue: ModuleType, folder: Path) -> None:
        self.drift = drift
        self.dq = drift_queue
        self.folder = folder
        self.index: dict[str, Any] = drift_queue.empty_index()
        self.index["contract_version"] = 1
        self.friction = drift.friction_fingerprint(_explained())

    def propose(
        self,
        name: str,
        *,
        run: str = "20261020T120000Z-aaaaaa",
        fixer: str = "living-docs",
        answer: dict[str, Any] | None = None,
        **entry: Any,
    ) -> None:
        answer = answer if answer is not None else _answer(name)
        files = self.folder / "runs" / run / fixer / name
        files.mkdir(parents=True, exist_ok=True)
        (files / "answer.json").write_text(json.dumps(answer), encoding="utf-8")
        (files / "evidence.md").write_text("PR #3 renamed the flag on purpose.\n")
        if answer.get("diff"):
            (self.folder / "runs" / run / fixer / answer["diff"]).write_text(
                DIFF.format(name=name), encoding="utf-8"
            )
        self._entry(name, "proposed", run, fixer, **entry)

    def hold(self, name: str, *, run: str = "20261020T120000Z-aaaaaa", **entry: Any) -> None:
        files = self.folder / "runs" / run / "living-docs" / name
        files.mkdir(parents=True, exist_ok=True)
        (files / "evidence.md").write_text("Two readings of the flag.\n")
        self._entry(name, "held", run, "living-docs", words="Was the flag renamed?", **entry)

    def _entry(self, name: str, state: str, run: str, fixer: str, **entry: Any) -> None:
        self.index["artefacts"][name] = {
            "type": "living-docs:page",
            "fixer": fixer,
            "state": state,
            "reason": None,
            "words": entry.pop("words", None),
            "proposal": None,
            "evidence": None,
            "diff": None,
            "commit": COMMIT,
            "friction": entry.pop("friction", self.friction),
            "setup": "setup-1",
            "run": run,
            "contract_version": entry.pop("contract_version", 1),
            "failures": 0,
            "answer": entry.pop("answer", None),
            "answered_by": None,
        }
        runs = self.index["runs"].setdefault(run, {"fixers": {}})
        runs["fixers"].setdefault(fixer, {"artefacts": []})["artefacts"].append(name)

    def write(self) -> None:
        self.dq.write_index(self.folder, self.index)

    def read(self) -> dict[str, Any]:
        return self.dq.read_index(self.folder)


@pytest.fixture
def queue(lib, tmp_path: Path) -> Queue:
    _proposals, drift, drift_queue, _contract = lib
    return Queue(drift, drift_queue, tmp_path / "queue")


# --- what waits, in the queue's order ----------------------------------------------------------


def test_what_waits_is_each_proposal_and_question_upstream_first(lib, queue) -> None:
    proposals, _drift, _dq, contract = lib
    queue.propose("docs/b.md", run="20261020T130000Z-bbbbbb")
    queue.propose("docs/a.md")
    queue.hold("docs/c.md")
    queue.index["artefacts"]["docs/gone.md"] = {
        **queue.index["artefacts"]["docs/a.md"],
        "state": "none",
    }
    found = proposals.waiting(queue.index, queue.folder, contract.load())
    assert [(w.name, w.state) for w in found] == [
        ("docs/a.md", "proposed"),
        ("docs/c.md", "held"),
        ("docs/b.md", "proposed"),
    ]
    first = found[0]
    assert first.answer is not None and first.answer.fields["outcome"] == "updated"
    assert first.evidence == "PR #3 renamed the flag on purpose.\n"
    assert found[1].answer is None and not found[1].answered


def test_a_proposal_whose_files_no_longer_read_says_why(lib, queue) -> None:
    proposals, _drift, _dq, contract = lib
    queue.propose("docs/a.md", answer=_answer("docs/a.md", outcome="sideways"))
    [item] = proposals.waiting(queue.index, queue.folder, contract.load())
    assert item.answer is None and "refused by the schema" in item.unread
    why = proposals.recheck(item, _explained(), 1)
    assert why is not None and why.startswith("its proposal no longer reads")


@pytest.mark.parametrize(
    ("explained", "version", "why"),
    [
        (_explained(), 1, None),
        (
            _explained(state="current"),
            1,
            "it is no longer stale at the default branch: it is current",
        ),
        (_explained(commit="d" * 40), 1, "its friction at the default branch differs"),
        (_explained(), 2, "it was judged under version 1 of the run's contract"),
    ],
)
def test_each_proposal_is_checked_again_at_the_default_branch(
    lib, queue, explained, version, why
) -> None:
    proposals, _drift, _dq, contract = lib
    queue.propose("docs/a.md")
    [item] = proposals.waiting(queue.index, queue.folder, contract.load())
    said = proposals.recheck(item, explained, version)
    assert said == why if why is None else said is not None and said.startswith(why)


# --- what the person decides, kept in the queue ---------------------------------------------


def test_set_aside_dispatches_the_artefact_again(lib, queue) -> None:
    proposals, _drift, dq, _contract = lib
    queue.propose("docs/a.md")
    index = proposals.set_aside(queue.index, "docs/a.md", "it is no longer stale")
    entry = index["artefacts"]["docs/a.md"]
    assert (entry["state"], entry["words"], entry["proposal"]) == (
        "set-aside",
        "it is no longer stale",
        None,
    )
    assert dq.waiting(index) == 0


def test_a_refusal_is_remembered_against_the_friction(lib, queue) -> None:
    proposals, _drift, dq, _contract = lib
    queue.propose("docs/a.md")
    queue.hold("docs/c.md")
    index = proposals.refuse(queue.index, "docs/a.md", at="2026-10-20T12:00:00Z")
    index = proposals.refuse(index, "docs/c.md", at="2026-10-20T12:00:00Z")
    assert set(index["artefacts"]) == set()
    refusal = index["refusals"]["docs/a.md"]
    assert refusal["friction"] == queue.friction and refusal["fixer"] == "living-docs"
    assert dq.waiting(index) == 0


def test_an_answer_goes_with_the_next_brief_and_names_who_gave_it(lib, queue) -> None:
    proposals, _drift, dq, _contract = lib
    queue.hold("docs/c.md")
    index = proposals.answer(queue.index, "docs/c.md", words="Yes, on purpose.", by="Octo Cat")
    entry = index["artefacts"]["docs/c.md"]
    assert (entry["state"], entry["answer"], entry["answered_by"]) == (
        "held",
        "Yes, on purpose.",
        "Octo Cat",
    )
    assert dq.waiting(index) == 0


def test_a_run_s_folder_goes_once_none_of_its_proposals_waits(lib, queue) -> None:
    proposals, _drift, _dq, _contract = lib
    queue.propose("docs/a.md", run="r-old")
    queue.propose("docs/b.md", run="r-new")
    (queue.folder / "runs" / "r-crashed").mkdir()
    index = proposals.consume(queue.index, "docs/a.md")
    assert proposals.prune(queue.folder, index) == ["r-crashed", "r-old"]
    assert [p.name for p in (queue.folder / "runs").iterdir()] == ["r-new"]


# --- the writer's command ------------------------------------------------------------------


def test_the_writer_is_built_from_the_answer_s_fields(lib) -> None:
    proposals, *_ = lib
    updated = _answer("docs/a.md", keep=["path:src/y.py"])
    assert proposals.writer_argv("docs/a.md", updated) == [
        "pkit",
        "friction",
        "revalidate",
        "--outcome",
        "updated",
        "--keep",
        "path:src/y.py",
        "--yes",
        "--",
        "docs/a.md",
    ]
    unchanged = _answer("-odd.md", outcome="unchanged", justification="It holds; $(rm -rf /)")
    argv = proposals.writer_argv("-odd.md", unchanged)
    assert argv[4:7] == ["unchanged", "--because", "It holds; $(rm -rf /)"]
    assert argv[-2:] == ["--", "-odd.md"]
    assert proposals.shown(argv).endswith("--because 'It holds; $(rm -rf /)' --yes -- -odd.md")
    reworded = proposals.writer_argv("-odd.md", unchanged, because="The person's words.")
    assert "The person's words." in reworded and "It holds; $(rm -rf /)" not in reworded


def test_a_placeholder_and_words_that_cannot_stand_are_found(lib) -> None:
    proposals, *_ = lib
    assert proposals.placeholder("Held by <the defect reference>.") == "<the defect reference>"
    assert proposals.placeholder("It still holds.") is None
    assert proposals.line_problem("One plain line.") is None
    for bad in ("two\nlines", "  ", "hidden ‮ words"):
        assert proposals.line_problem(bad) is not None


def test_upstream_first_whatever_order_they_are_named_in(lib) -> None:
    proposals, *_ = lib
    upstreams = {"docs/page.md": ["g.md#term"], "g.md#term": [], "other.md": ["docs/page.md"]}
    names = ["other.md", "docs/page.md", "g.md#term", "free.md"]
    assert proposals.upstream_first(names, upstreams) == [
        "g.md#term",
        "docs/page.md",
        "other.md",
        "free.md",
    ]
    cycle = {"x.md": ["y.md"], "y.md": ["x.md"]}
    assert set(proposals.upstream_first(["x.md", "y.md"], cycle)) == {"x.md", "y.md"}


# --- the checkout the change is made in --------------------------------------------------


def _runner(answers: dict[tuple[str, ...], tuple[int, str]]):
    def run(argv, **_kw):
        code, out = answers[tuple(argv[1:4])]
        return subprocess.CompletedProcess(argv, code, out, "fatal: said" if code > 1 else "")

    return run


def test_what_is_accepted_is_applied_on_a_branch_of_its_own(lib, tmp_path) -> None:
    proposals, *_ = lib
    on = lambda branch: _runner({("symbolic-ref", "--quiet", "--short"): (0, f"{branch}\n")})  # noqa: E731
    assert "the default branch, main" in (
        proposals.branch_problem(tmp_path, "main", on("main")) or ""
    )
    assert proposals.branch_problem(tmp_path, "main", on("docs/1800-fix")) is None
    detached = _runner({("symbolic-ref", "--quiet", "--short"): (1, "")})
    assert "on no branch" in (proposals.branch_problem(tmp_path, "main", detached) or "")


@pytest.mark.parametrize(
    ("code", "why"), [(0, None), (1, "differs from"), (128, "cannot be compared")]
)
def test_the_checkout_s_file_must_be_the_default_branch_s(lib, tmp_path, code, why) -> None:
    proposals, *_ = lib
    run = _runner({("diff", "--quiet", COMMIT): (code, "")})
    said = proposals.file_problem(tmp_path, COMMIT, "docs/a.md", run)
    assert said is None if why is None else why in (said or "")


# --- applying -------------------------------------------------------------------------------


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    """A working tree with the page the diffs edit. `git apply` needs no commit."""
    root = tmp_path / "checkout"
    (root / "docs").mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    (root / "docs" / "a.md").write_text("# A page\nThe flag is --old.\n", encoding="utf-8")
    return root


class Writer:
    """A stub of the writer: records each command, and answers as told."""

    def __init__(self, code: int = 0, touch: Path | None = None) -> None:
        self.code = code
        self.touch = touch
        self.seen: list[list[str]] = []

    def __call__(self, argv, **kw):
        self.seen.append(list(argv))
        if self.touch is not None:
            self.touch.write_text("written by a writer that then failed\n")
        return subprocess.CompletedProcess(argv, self.code, "", "error: the writer refused")


def _item(lib, queue, name: str = "docs/a.md", **kw):
    proposals, _drift, _dq, contract = lib
    queue.propose(name, **kw)
    return next(
        w for w in proposals.waiting(queue.index, queue.folder, contract.load()) if w.name == name
    )


def test_an_accepted_proposal_is_applied_diff_then_writer(lib, queue, checkout) -> None:
    proposals, *_ = lib
    writer = Writer()
    done = proposals.apply_one(
        _item(lib, queue), root=checkout, because=None, sentence=None, write=writer
    )
    assert done.applied and done.sentence == "The page names the new flag."
    assert (checkout / "docs" / "a.md").read_text() == "# A page\nThe flag is --new.\n"
    assert writer.seen == [list(done.argv)]
    assert writer.seen[0][-2:] == ["--", "docs/a.md"]


def test_a_diff_that_no_longer_applies_is_set_aside(lib, queue, checkout) -> None:
    proposals, *_ = lib
    (checkout / "docs" / "a.md").write_text("# A page\nSomething else.\n")
    writer = Writer()
    done = proposals.apply_one(
        _item(lib, queue), root=checkout, because=None, sentence=None, write=writer
    )
    assert not done.applied and done.set_aside and done.why.startswith("its diff no longer applies")
    assert writer.seen == []
    assert (checkout / "docs" / "a.md").read_text() == "# A page\nSomething else.\n"


def test_a_writer_that_fails_leaves_the_file_as_it_was(lib, queue, checkout) -> None:
    proposals, *_ = lib
    page = checkout / "docs" / "a.md"
    writer = Writer(code=1, touch=page)
    done = proposals.apply_one(
        _item(lib, queue), root=checkout, because=None, sentence=None, write=writer
    )
    assert not done.applied and not done.set_aside
    assert "its writer exited 1: error: the writer refused" in done.why
    assert page.read_text() == "# A page\nThe flag is --old.\n"


def test_a_dry_run_checks_the_diff_and_writes_nothing(lib, queue, checkout) -> None:
    proposals, *_ = lib
    writer = Writer()
    done = proposals.apply_one(
        _item(lib, queue), root=checkout, because=None, sentence=None, write=writer, dry_run=True
    )
    assert done.applied and writer.seen == []
    assert (checkout / "docs" / "a.md").read_text() == "# A page\nThe flag is --old.\n"


def test_an_unchanged_answer_runs_the_person_s_words(lib, queue, checkout) -> None:
    proposals, *_ = lib
    writer = Writer()
    item = _item(lib, queue, answer=_answer("docs/a.md", outcome="unchanged"))
    done = proposals.apply_one(
        item, root=checkout, because="Held by #12.", sentence=None, write=writer
    )
    assert done.applied and done.sentence is None
    assert writer.seen[0][4:7] == ["unchanged", "--because", "Held by #12."]
    assert (checkout / "docs" / "a.md").read_text() == "# A page\nThe flag is --old.\n"


# --- the commands ---------------------------------------------------------------------------


@pytest.fixture
def world(lib, queue, checkout, monkeypatch):
    """The commands' readings stubbed: the queue in the test's folder, the
    default branch `main` at COMMIT, a copy of it, and each artefact's friction."""
    proposals, drift, _dq, _contract = lib
    monkeypatch.delenv("PKIT_AGENT_RUN", raising=False)
    started = proposals.Started(checkout / ".pkit" / "cap", checkout, queue.folder)
    monkeypatch.setattr(proposals, "start", lambda verb, root: started)
    monkeypatch.setattr(proposals, "pin", lambda root: ("main", COMMIT))
    friction: dict[str, dict[str, Any]] = {}

    @contextlib.contextmanager
    def copy_at(root, commit):
        assert commit == COMMIT
        yield checkout

    monkeypatch.setattr(drift, "copy_at", copy_at)
    monkeypatch.setattr(drift, "explain", lambda copy, name: friction.get(name, _explained()))
    monkeypatch.setattr(drift, "upstreams_at", lambda copy: {})
    return friction


def _gates(module: ModuleType, monkeypatch) -> None:
    monkeypatch.setattr(module.bootstrap_gate, "enforce", lambda verb, **kw: True)
    monkeypatch.setattr(module.session_guard, "enforce", lambda **kw: True)


@pytest.mark.parametrize(
    "argv",
    [
        ["show-proposals"],
        ["apply-proposals", "docs/a.md"],
        ["refuse-proposals", "docs/a.md"],
        ["answer-question", "docs/a.md", "yes"],
    ],
)
def test_no_command_of_the_batch_runs_inside_an_agent_run(argv, monkeypatch, capsys) -> None:
    command = _script(argv[0])
    monkeypatch.setenv("PKIT_AGENT_RUN", "1")
    assert command.main(argv[1:]) == 1
    assert "inside an agent run" in capsys.readouterr().err


def test_show_brings_the_batch_and_sets_aside_what_no_longer_holds(
    lib, queue, world, monkeypatch, capsys
) -> None:
    _proposals, _drift, _dq, _contract = lib
    queue.propose("docs/a.md")
    queue.propose(
        "docs/u.md",
        answer=_answer(
            "docs/u.md",
            outcome="unchanged",
            justification="Held by <the defect reference>.",
            first=["Report the defect, and write its reference into the reason."],
        ),
    )
    queue.propose("docs/stale.md")
    queue.hold("docs/q.md")
    queue.hold("docs/answered.md", answer="Yes.")
    queue.write()
    world["docs/stale.md"] = _explained(state="current")
    command = _script("show-proposals")
    _gates(command, monkeypatch)
    assert command.main([]) == 0
    out = capsys.readouterr().out
    assert "proposal 1 of 2: `docs/a.md` — living-docs:page, from living-docs" in out
    assert "  what changed: The page names the new flag." in out
    assert (
        "the writer, word for word: pkit friction revalidate --outcome updated --yes -- docs/a.md"
        in out
    )
    assert "    | PR #3 renamed the flag on purpose." in out
    assert "    | -The flag is --old." in out
    assert "  because: Held by <the defect reference>." in out
    assert "it holds a placeholder for you to fill, <the defect reference>" in out
    assert "    - Report the defect, and write its reference into the reason." in out
    assert "question 1 of 1: `docs/q.md`" in out and "  asks: Was the flag renamed?" in out
    assert "answer it: pkit pm answer-question docs/q.md '<your answer>'" in out
    assert "answered: `docs/answered.md` — Yes., by None" in out
    assert "set aside: `docs/stale.md` — it is no longer stale at the default branch" in out
    entry = queue.read()["artefacts"]["docs/stale.md"]
    assert entry["state"] == "set-aside"
    assert "fixers: 3 proposals wait for you" in out


def test_show_with_nothing_waiting_says_so(lib, queue, world, monkeypatch, capsys) -> None:
    command = _script("show-proposals")
    _gates(command, monkeypatch)
    assert command.main([]) == 0
    assert "nothing waits for you" in capsys.readouterr().out


def _apply(
    monkeypatch, lib, writer: Writer, *, branch: str | None = None, differs: str | None = None
):
    proposals, *_ = lib
    command = _script("apply-proposals")
    _gates(command, monkeypatch)
    monkeypatch.setattr(proposals, "branch_problem", lambda root, default: branch)
    monkeypatch.setattr(proposals, "file_problem", lambda root, commit, path: differs)
    real = proposals.apply_one
    monkeypatch.setattr(proposals, "apply_one", lambda item, **kw: real(item, write=writer, **kw))
    return command


def test_apply_applies_what_was_accepted_and_prints_the_sentences(
    lib, queue, world, checkout, monkeypatch, capsys
) -> None:
    queue.propose("docs/a.md")
    queue.propose("docs/b.md", run="r-other")
    queue.write()
    writer = Writer()
    command = _apply(monkeypatch, lib, writer)
    assert command.main(["docs/a.md"]) == 0
    out = capsys.readouterr().out
    assert (
        "applied: `docs/a.md` — pkit friction revalidate --outcome updated --yes -- docs/a.md"
        in out
    )
    assert "## What changed in each updated document" in out
    assert "- `docs/a.md`: The page names the new flag." in out
    assert (checkout / "docs" / "a.md").read_text().endswith("--new.\n")
    index = queue.read()
    assert set(index["artefacts"]) == {"docs/b.md"}
    assert sorted(p.name for p in (queue.folder / "runs").iterdir()) == ["r-other"]


def test_apply_refuses_on_the_default_branch_and_writes_nothing(
    lib, queue, world, checkout, monkeypatch, capsys
) -> None:
    queue.propose("docs/a.md")
    queue.write()
    writer = Writer()
    command = _apply(monkeypatch, lib, writer, branch="the checkout is on the default branch, main")
    assert command.main(["docs/a.md"]) == 1
    assert "the checkout is on the default branch" in capsys.readouterr().err
    assert writer.seen == [] and queue.read()["artefacts"]["docs/a.md"]["state"] == "proposed"
    assert (checkout / "docs" / "a.md").read_text().endswith("--old.\n")


@pytest.mark.parametrize(
    ("argv", "why"),
    [
        (["docs/nothing.md"], "`docs/nothing.md` has no proposal waiting"),
        (["docs/u.md"], "holds a placeholder for the person to fill"),
        (["docs/u.md", "--because", "docs/u.md", "two\nlines"], "cannot stand"),
        (["docs/a.md", "--because", "docs/a.md", "Words."], "is for an `unchanged` answer"),
    ],
)
def test_apply_refuses_what_the_person_did_not_settle(
    lib, queue, world, monkeypatch, capsys, argv, why
) -> None:
    queue.propose("docs/a.md")
    queue.propose(
        "docs/u.md",
        answer=_answer("docs/u.md", outcome="unchanged", justification="Held by <the defect>."),
    )
    queue.write()
    writer = Writer()
    command = _apply(monkeypatch, lib, writer)
    assert command.main(argv) == 1
    assert why in capsys.readouterr().err
    assert writer.seen == []


def test_apply_sets_aside_what_no_longer_holds_and_says_so(
    lib, queue, world, checkout, monkeypatch, capsys
) -> None:
    (checkout / "docs" / "u.md").write_text("# U\n", encoding="utf-8")
    queue.propose("docs/a.md")
    queue.propose(
        "docs/u.md", answer=_answer("docs/u.md", outcome="unchanged", justification="Holds.")
    )
    queue.write()
    world["docs/a.md"] = _explained(commit="e" * 40)
    writer = Writer()
    command = _apply(monkeypatch, lib, writer)
    assert command.main(["docs/a.md", "docs/u.md"]) == command.EXIT_PARTIAL
    lines = capsys.readouterr().out.splitlines()
    assert any(
        line.startswith("set aside: `docs/a.md` — its friction at the default branch differs")
        for line in lines
    )
    assert any(line.startswith("applied: `docs/u.md`") for line in lines)
    index = queue.read()
    assert index["artefacts"]["docs/a.md"]["state"] == "set-aside"
    assert "docs/u.md" not in index["artefacts"]
    assert [argv[-1] for argv in writer.seen] == ["docs/u.md"]


def test_refuse_remembers_and_answer_records_through_the_commands(
    lib, queue, world, monkeypatch, capsys
) -> None:
    queue.propose("docs/a.md")
    queue.hold("docs/q.md")
    queue.write()
    refuse = _script("refuse-proposals")
    _gates(refuse, monkeypatch)
    assert refuse.main(["docs/a.md"]) == 0
    assert "refused: `docs/a.md`" in capsys.readouterr().out
    answer = _script("answer-question")
    _gates(answer, monkeypatch)
    assert answer.main(["docs/q.md", "Yes, on purpose.", "--by", "Octo Cat"]) == 0
    assert "recorded: your answer on `docs/q.md`, by Octo Cat" in capsys.readouterr().out
    index = queue.read()
    assert index["refusals"]["docs/a.md"]["friction"] == queue.friction
    assert index["artefacts"]["docs/q.md"]["answer"] == "Yes, on purpose."
    assert refuse.main(["docs/a.md"]) == 1
    assert "has nothing waiting to refuse" in capsys.readouterr().err
    assert answer.main(["docs/a.md", "Yes.", "--by", "Octo Cat"]) == 1
    assert "no question waits on `docs/a.md`" in capsys.readouterr().err
