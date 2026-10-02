"""Tests for the backbone's cross-repository guard, `project_kit.session_guard` (#1254).

The comparison itself is held to the capability's by
`test_session_guard_parity.py`; here is the gate (`clear`): how a change
passes — the session's own repository, no anchor, a git fault, the flag, a
terminal — or is refused, what it says and where, what a document states of
it, and `require`, which keeps a change to the directory the guard looked at.
"""

from __future__ import annotations

import io
import subprocess
from pathlib import Path
from typing import Any

import pytest

from project_kit import session_guard
from tests.sessions import repository


class _Stdin(io.StringIO):
    """Standard input, a terminal or not, answering `answer`; counts the reads."""

    def __init__(self, answer: str, *, terminal: bool) -> None:
        super().__init__(answer)
        self.terminal = terminal
        self.reads = 0

    def isatty(self) -> bool:
        return self.terminal

    def readline(self, size: int | None = -1) -> str:
        self.reads += 1
        return super().readline()


@pytest.fixture
def session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """A session rooted in one repository, and another repository: (anchor, other)."""
    anchor = repository(tmp_path / "anchor", "https://github.com/octo/project.git")
    other = repository(tmp_path / "other", "https://github.com/octo/other.git")
    monkeypatch.setenv(session_guard.CLAUDE_CODE_ANCHOR, str(anchor))
    return anchor, other


class _Stderr(io.StringIO):
    """Standard error, a terminal or not, keeping what is written to it."""

    def __init__(self, *, terminal: bool) -> None:
        super().__init__()
        self.terminal = terminal

    def isatty(self) -> bool:
        return self.terminal


def _stdin(monkeypatch: pytest.MonkeyPatch, answer: str = "", *, terminal: bool) -> _Stdin:
    stdin = _Stdin(answer, terminal=terminal)
    monkeypatch.setattr("sys.stdin", stdin)
    return stdin


def _stderr(monkeypatch: pytest.MonkeyPatch, *, terminal: bool) -> _Stderr:
    stderr = _Stderr(terminal=terminal)
    monkeypatch.setattr("sys.stderr", stderr)
    return stderr


def _at_a_terminal(monkeypatch: pytest.MonkeyPatch, answer: str) -> tuple[_Stdin, _Stderr]:
    """A person at a terminal — standard input and standard error both one —
    who answers `answer`."""
    return _stdin(monkeypatch, answer, terminal=True), _stderr(monkeypatch, terminal=True)


def test_the_sessions_own_repository_passes_silently(
    session: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    anchor, _ = session
    passage = session_guard.clear(anchor, confirmed=False)
    assert isinstance(passage, session_guard.Clearance)
    assert passage.passed == session_guard.SAME_REPO
    assert passage.as_json()["verdict"] == "same-repo"
    assert capsys.readouterr() == ("", "")


def test_with_no_anchor_it_does_not_fire_and_never_says_same_repo(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Outside any session there is no session to compare with: the change
    goes ahead, silently, and the verdict is undetermined — a pipeline needs no
    flag."""
    target = repository(tmp_path / "target", "https://github.com/octo/project.git")
    passage = session_guard.clear(target, confirmed=False, interactive=False)
    assert isinstance(passage, session_guard.Clearance)
    assert passage.passed == session_guard.UNDETERMINED
    assert passage.as_json() == {
        "verdict": "undetermined",
        "undetermined_kind": "noncoverage",
        "anchor": None,
        "target": None,
        "cleared": "undetermined",
    }
    assert capsys.readouterr() == ("", "")


def test_a_git_fault_warns_and_proceeds(
    session: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _, other = session

    def hanging(argv: Any, *args: Any, **kwargs: Any) -> Any:
        raise subprocess.TimeoutExpired(argv, 5)

    monkeypatch.setattr(subprocess, "run", hanging)
    passage = session_guard.clear(other, confirmed=False, interactive=False)
    assert isinstance(passage, session_guard.Clearance)
    assert (passage.passed, passage.comparison.undetermined_kind) == ("undetermined", "fault")
    out, err = capsys.readouterr()
    assert out == "" and err.startswith("[warn] the cross-repository guard could not compare")


def test_another_repository_with_the_flag_passes_with_an_advisory(
    session: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """The verdict is the comparison's alone, `diverged`; how the guard let
    the change through is `cleared`."""
    anchor, other = session
    passage = session_guard.clear(other, confirmed=True, interactive=False)
    assert isinstance(passage, session_guard.Clearance)
    assert passage.passed == session_guard.FLAG
    assert passage.as_json() == {
        "verdict": "diverged",
        "undetermined_kind": None,
        "anchor": str(anchor.resolve()),
        "target": str(other.resolve()),
        "cleared": "flag",
    }
    out, err = capsys.readouterr()
    assert out == "" and "[advisory]" in err and "--allow-foreign-repo" in err


def test_another_repository_with_no_terminal_and_no_flag_is_refused_unasked(
    session: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    anchor, other = session
    stdin = _stdin(monkeypatch, "y\n", terminal=False)
    passage = session_guard.clear(other, confirmed=False)
    assert isinstance(passage, session_guard.Refusal)
    assert stdin.reads == 0
    assert passage.as_json() == {
        "verdict": "diverged",
        "undetermined_kind": None,
        "anchor": str(anchor.resolve()),
        "target": str(other.resolve()),
        "cleared": None,
    }
    assert "no terminal to ask" in passage.reason and "--allow-foreign-repo" in passage.reason
    assert capsys.readouterr() == ("", "")


def test_at_a_terminal_it_asks_on_standard_error_and_a_yes_passes(
    session: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _, other = session
    stdin, stderr = _at_a_terminal(monkeypatch, "y\n")
    passage = session_guard.clear(other, confirmed=False)
    assert isinstance(passage, session_guard.Clearance)
    assert passage.passed == session_guard.TERMINAL
    assert stdin.reads == 1
    assert capsys.readouterr().out == ""
    assert "Make the change there anyway? [y/N]" in stderr.getvalue()


def test_with_standard_error_redirected_it_does_not_ask(
    session: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The question is written to standard error: with that redirected, a
    terminal on standard input alone is nobody to ask, so nothing is asked and
    the change is refused, as with no terminal."""
    _, other = session
    stdin = _stdin(monkeypatch, "y\n", terminal=True)
    stderr = _stderr(monkeypatch, terminal=False)
    passage = session_guard.clear(other, confirmed=False)
    assert isinstance(passage, session_guard.Refusal)
    assert stdin.reads == 0
    assert "Make the change there anyway?" not in stderr.getvalue()
    assert "no terminal to ask" in passage.reason


@pytest.mark.parametrize("answer", ["n\n", "\n", ""], ids=["no", "empty", "end-of-input"])
def test_at_a_terminal_anything_but_yes_refuses(
    session: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch, answer: str
) -> None:
    _, other = session
    _at_a_terminal(monkeypatch, answer)
    passage = session_guard.clear(other, confirmed=False)
    assert isinstance(passage, session_guard.Refusal)
    assert "not confirmed at the terminal" in passage.reason


def test_a_dry_run_never_asks_and_says_so_truthfully_at_a_terminal(
    session: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A dry run at a terminal ends as a run with nobody to ask would — refused
    — without asking, and does not claim there is no terminal; with the flag it
    passes as the confirmed run would."""
    _, other = session
    stdin, stderr = _at_a_terminal(monkeypatch, "y\n")
    refused = session_guard.clear(other, confirmed=False, dry_run=True)
    assert isinstance(refused, session_guard.Refusal)
    assert stdin.reads == 0 and "Make the change" not in stderr.getvalue()
    assert "no terminal" not in refused.reason
    assert "A dry run does not ask" in refused.reason
    assert "a run at a terminal would ask, and a run without one refuses" in refused.reason
    assert "--allow-foreign-repo to preview the confirmed run" in refused.reason
    flagged = session_guard.clear(other, confirmed=True, dry_run=True)
    assert isinstance(flagged, session_guard.Clearance) and flagged.passed == session_guard.FLAG


def test_the_words_name_the_anchor_and_the_target_never_the_harness_variable(
    session: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    _, other = session
    _, stderr = _at_a_terminal(monkeypatch, "n\n")
    refused = session_guard.clear(other, confirmed=False)
    assert isinstance(refused, session_guard.Refusal)
    said = refused.reason + stderr.getvalue()
    assert "the session's anchor" in said and "the target" in said
    assert session_guard.CLAUDE_CODE_ANCHOR not in said


def test_require_keeps_a_change_where_the_guard_looked(
    session: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    anchor, other = session
    cleared = session_guard.clear(anchor, confirmed=False)
    assert isinstance(cleared, session_guard.Clearance)
    assert session_guard.require(cleared, anchor) == anchor.resolve()
    with pytest.raises(ValueError, match="the clearance is for"):
        session_guard.require(cleared, other)
    with pytest.raises(TypeError, match="needs a clearance"):
        session_guard.require(None, anchor)
    _stdin(monkeypatch, terminal=False)
    refused = session_guard.clear(other, confirmed=False)
    with pytest.raises(TypeError, match="needs a clearance"):
        session_guard.require(refused, other)  # pyright: ignore[reportArgumentType] -- a refusal passed where a clearance is required is what this checks


@pytest.mark.parametrize("where", ["own", "other"])
def test_a_comparison_asks_git_no_more_than_the_questions_its_longest_run_counts(
    session: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch, where: str
) -> None:
    """The longest the guard can take is its git questions, each at its bound
    (`LONGEST_SECONDS`), which `pull_request_landing.longest_seconds` counts
    in every subcommand that runs the guard: a comparison asks git at most
    `GIT_QUESTIONS` times."""
    anchor, other = session
    asked: list[tuple[str, ...]] = []
    git = session_guard._git

    def counted(directory: Path | str, *args: str) -> subprocess.CompletedProcess[str]:
        asked.append(args)
        return git(directory, *args)

    monkeypatch.setattr(session_guard, "_git", counted)
    session_guard.evaluate(anchor if where == "own" else other, anchor)
    assert len(asked) == session_guard.GIT_QUESTIONS
    assert session_guard.GIT_QUESTIONS * session_guard._GIT_TIMEOUT_SECONDS == (
        session_guard.LONGEST_SECONDS
    )
