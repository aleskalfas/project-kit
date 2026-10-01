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


def _repository(path: Path, origin: str) -> Path:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", origin], cwd=path, check=True, capture_output=True
    )
    return path


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
    anchor = _repository(tmp_path / "anchor", "https://github.com/octo/project.git")
    other = _repository(tmp_path / "other", "https://github.com/octo/other.git")
    monkeypatch.setenv(session_guard.CLAUDE_CODE_ANCHOR, str(anchor))
    return anchor, other


def _stdin(monkeypatch: pytest.MonkeyPatch, answer: str = "", *, terminal: bool) -> _Stdin:
    stdin = _Stdin(answer, terminal=terminal)
    monkeypatch.setattr("sys.stdin", stdin)
    return stdin


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
    target = _repository(tmp_path / "target", "https://github.com/octo/project.git")
    passage = session_guard.clear(target, confirmed=False, interactive=False)
    assert isinstance(passage, session_guard.Clearance)
    assert passage.passed == session_guard.UNDETERMINED
    assert passage.as_json() == {
        "verdict": "undetermined",
        "passed": "undetermined",
        "undetermined_kind": "noncoverage",
        "anchor": None,
        "target": None,
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
    anchor, other = session
    passage = session_guard.clear(other, confirmed=True, interactive=False)
    assert isinstance(passage, session_guard.Clearance)
    assert passage.passed == session_guard.FLAG
    assert passage.as_json() == {
        "verdict": "overridden",
        "passed": "flag",
        "undetermined_kind": None,
        "anchor": str(anchor.resolve()),
        "target": str(other.resolve()),
    }
    out, err = capsys.readouterr()
    assert out == "" and "[advisory]" in err and "--allow-foreign-repo" in err


def test_another_repository_with_no_terminal_and_no_flag_is_refused_unasked(
    session: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _, other = session
    stdin = _stdin(monkeypatch, "y\n", terminal=False)
    passage = session_guard.clear(other, confirmed=False)
    assert isinstance(passage, session_guard.Refusal)
    assert stdin.reads == 0
    assert passage.as_json()["verdict"] == "diverged"
    assert passage.as_json()["passed"] is None
    assert "no terminal to ask" in passage.reason and "--allow-foreign-repo" in passage.reason
    assert capsys.readouterr() == ("", "")


def test_at_a_terminal_it_asks_on_standard_error_and_a_yes_passes(
    session: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _, other = session
    stdin = _stdin(monkeypatch, "y\n", terminal=True)
    passage = session_guard.clear(other, confirmed=False)
    assert isinstance(passage, session_guard.Clearance)
    assert passage.passed == session_guard.TERMINAL
    assert stdin.reads == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert "Make the change there anyway? [y/N]" in err


@pytest.mark.parametrize("answer", ["n\n", "\n", ""], ids=["no", "empty", "end-of-input"])
def test_at_a_terminal_anything_but_yes_refuses(
    session: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch, answer: str
) -> None:
    _, other = session
    _stdin(monkeypatch, answer, terminal=True)
    passage = session_guard.clear(other, confirmed=False)
    assert isinstance(passage, session_guard.Refusal)
    assert "not confirmed at the terminal" in passage.reason


def test_the_words_name_the_anchor_and_the_target_never_the_harness_variable(
    session: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _, other = session
    _stdin(monkeypatch, "n\n", terminal=True)
    refused = session_guard.clear(other, confirmed=False)
    assert isinstance(refused, session_guard.Refusal)
    said = refused.reason + capsys.readouterr().err
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
    _stdin(monkeypatch, terminal=False)
    refused = session_guard.clear(other, confirmed=False)
    with pytest.raises(TypeError, match="needs a clearance"):
        session_guard.require(refused, other)  # pyright: ignore[reportArgumentType] -- a refusal passed where a clearance is required is what this checks
