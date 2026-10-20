"""The queue of the fixers' proposals (#1744; project-management DEC-056 point 6).

The drift command gathers each run's proposals into the agent workspace of the
repository's main working tree, and the landing command counts what waits.
`_lib/drift_queue.py` is where the queue lies, how its index is read and written,
its one-run-at-a-time lock, and the count. These tests hold each against real git
repositories built under the test's own folder.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "scripts"
    / "_lib"
    / "drift_queue.py"
)


def _load() -> ModuleType:
    """The module, loaded by its path under a name of its own."""
    name = "pm_drift_queue_under_test"
    spec = importlib.util.spec_from_file_location(name, MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


dq = _load()


def _git(cwd: Path, *argv: str) -> str:
    proc = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *argv],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repository with one commit, its main working tree at `tmp_path/main`."""
    main = tmp_path / "main"
    main.mkdir()
    _git(main, "init", "-q", "-b", "main")
    _git(main, "config", "user.email", "octocat@example.com")
    _git(main, "config", "user.name", "Octo Cat")
    _git(main, "commit", "-q", "--allow-empty", "-m", "start")
    return main


def _entry(state: str) -> dict[str, Any]:
    return {"type": "living-docs:page", "fixer": "living-docs", "state": state}


def _index(*states: str) -> dict[str, Any]:
    index = dq.empty_index()
    index["contract_version"] = 1
    index["artefacts"] = {f"docs/{n}.md": _entry(state) for n, state in enumerate(states)}
    return index


# --- where the queue lies ------------------------------------------------------------------


def test_the_queue_lies_in_the_main_working_tree_s_workspace(repo: Path) -> None:
    assert dq.main_working_tree(repo) == repo.resolve()
    assert dq.folder(repo) == repo.resolve() / ".agent-workspace" / "project-management" / "drift"


def test_a_linked_worktree_s_queue_is_the_main_working_tree_s(repo: Path, tmp_path: Path) -> None:
    """Removing a worktree removes no proposal: its queue is the main tree's."""
    linked = tmp_path / "linked"
    _git(repo, "worktree", "add", "-q", "-b", "other", str(linked))
    assert dq.folder(linked) == dq.folder(repo)
    assert dq.folder(linked) != linked.resolve() / dq.FOLDER


def test_a_bare_repository_keeps_no_queue_and_says_why(repo: Path, tmp_path: Path) -> None:
    bare = tmp_path / "bare.git"
    _git(tmp_path, "clone", "-q", "--bare", str(repo), str(bare))
    linked = tmp_path / "of-bare"
    _git(bare, "worktree", "add", "-q", str(linked), "main")
    for where in (bare, linked):
        found = dq.folder(where)
        assert isinstance(found, str)
        assert "is bare, so it has no main working tree" in found


def test_a_folder_outside_any_repository_keeps_no_queue(tmp_path: Path) -> None:
    alone = tmp_path / "alone"
    alone.mkdir()
    found = dq.folder(alone)
    assert isinstance(found, str)
    assert found.startswith("no queue can be kept: no git repository is here")


def test_git_that_cannot_run_keeps_no_queue(tmp_path: Path) -> None:
    def missing(*_args: Any, **_kwargs: Any) -> Any:
        raise FileNotFoundError("git")

    assert dq.folder(tmp_path, run=missing) == "no queue can be kept: git cannot be run"


# --- the index -----------------------------------------------------------------------------


def test_an_absent_index_is_an_empty_queue(tmp_path: Path) -> None:
    index = dq.read_index(tmp_path / "nowhere")
    assert index == dq.empty_index()
    assert dq.waiting(index) == 0


def test_an_index_is_written_whole_and_read_back(tmp_path: Path) -> None:
    queue = tmp_path / "queue"
    written = _index("proposed", "none")
    dq.write_index(queue, written)
    assert dq.read_index(queue) == written
    # Only the index is left: the file it was first written to replaced it.
    assert sorted(p.name for p in queue.iterdir()) == [dq.INDEX]
    assert (queue / dq.INDEX).read_text(encoding="utf-8").endswith("}\n")


def test_a_write_that_fails_leaves_the_index_as_it_was(tmp_path: Path, monkeypatch) -> None:
    queue = tmp_path / "queue"
    dq.write_index(queue, _index("held"))

    def broken(*_args: Any) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(dq.os, "replace", broken)
    with pytest.raises(OSError):
        dq.write_index(queue, _index("proposed", "proposed"))
    assert dq.read_index(queue) == _index("held")
    assert sorted(p.name for p in queue.iterdir()) == [dq.INDEX]


@pytest.mark.parametrize(
    ("text", "said"),
    [
        ("{", "is not JSON"),
        ("[]", "is not an object"),
        (json.dumps({"schema_version": 2}), "is at schema_version 2; this reads 1"),
        (json.dumps({"artefacts": {}}), "is at schema_version None"),
        (json.dumps({"schema_version": 1, "artefacts": []}), "`artefacts` does not map"),
        (json.dumps({"schema_version": 1, "runs": {"r": 1}}), "`runs` does not map"),
        (
            json.dumps({"schema_version": 1, "artefacts": {"a": {"state": "done"}}}),
            "artefact 'a' is in state 'done'",
        ),
    ],
)
def test_an_index_it_cannot_read_raises_never_guesses(tmp_path: Path, text: str, said: str) -> None:
    (tmp_path / dq.INDEX).write_text(text, encoding="utf-8")
    with pytest.raises(dq.Unreadable, match=said.replace("(", r"\(")):
        dq.read_index(tmp_path)


def test_an_index_that_is_not_utf8_raises(tmp_path: Path) -> None:
    (tmp_path / dq.INDEX).write_bytes(b"\xff\xfe{}")
    with pytest.raises(dq.Unreadable, match="cannot be read"):
        dq.read_index(tmp_path)


def test_an_index_it_would_not_read_back_is_never_written(tmp_path: Path) -> None:
    bad = {**_index("proposed"), "schema_version": 2}
    with pytest.raises(dq.Unreadable):
        dq.write_index(tmp_path / "queue", bad)
    assert not (tmp_path / "queue" / dq.INDEX).exists()


# --- the lock --------------------------------------------------------------------------------


def test_one_run_at_a_time_holds_the_lock_and_another_is_refused(tmp_path: Path) -> None:
    queue = tmp_path / "queue"
    with dq.lock(queue) as held:
        assert held == queue / dq.LOCK
        assert held.read_text(encoding="utf-8").strip().isdigit()
        held_by = r"another run holds .*drift\.lock \(process \d+\)"
        with pytest.raises(dq.Held, match=held_by), dq.lock(queue):
            pass  # pragma: no cover — never reached
    # Released when the block ends, so the next run takes it.
    with dq.lock(queue):
        pass


def test_the_lock_is_released_when_the_block_raises(tmp_path: Path) -> None:
    queue = tmp_path / "queue"
    with pytest.raises(RuntimeError), dq.lock(queue):
        raise RuntimeError("the run failed")
    with dq.lock(queue):
        pass


def test_a_lock_held_by_another_process_is_refused(tmp_path: Path) -> None:
    queue = tmp_path / "queue"
    holder = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import importlib.util, sys, time\n"
            f"spec = importlib.util.spec_from_file_location('dq', {str(MODULE)!r})\n"
            "dq = importlib.util.module_from_spec(spec); spec.loader.exec_module(dq)\n"
            f"with dq.lock(__import__('pathlib').Path({str(queue)!r})):\n"
            "    print('held', flush=True); sys.stdin.read()\n",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert holder.stdout is not None
        assert holder.stdout.readline().strip() == "held"
        with pytest.raises(dq.Held, match=f"process {holder.pid}"), dq.lock(queue):
            pass  # pragma: no cover — never reached
    finally:
        holder.communicate("", timeout=30)
    with dq.lock(queue):
        pass


# --- what waits ------------------------------------------------------------------------------


def test_what_waits_is_each_proposed_or_held_artefact() -> None:
    index = _index("proposed", "held", "none", "failed", "set-aside", "proposed")
    assert dq.waiting(index) == 3
    assert dq.waiting(dq.empty_index()) == 0


def test_an_answered_question_waits_for_the_next_run_not_for_the_person() -> None:
    """The person answered it (`answer-question`), so the count leaves it out
    until the next run gives the fixer the answer (#1747)."""
    index = _index("held", "held", "proposed")
    index["artefacts"]["docs/0.md"]["answer"] = "Yes, it was renamed on purpose."
    assert dq.waiting(index) == 2


@pytest.mark.parametrize(
    ("count", "line"),
    [
        (0, None),
        (1, "fixers: 1 proposal waits for you — pkit pm fix-drift gathered them in /q"),
        (3, "fixers: 3 proposals wait for you — pkit pm fix-drift gathered them in /q"),
    ],
)
def test_the_count_line_names_how_many_wait_and_where(count: int, line: str | None) -> None:
    assert dq.count_line(count, Path("/q")) == line
