"""Tests for a person's authorisation asked only at a terminal (_lib/consent.py, #2015).

Off a terminal, without `--yes`, a step that is the person's is refused and no
answer is read, so `echo y | pkit pm …` authorises nothing. At a terminal the
person is asked, and `--yes` authorises the step anywhere.
"""

from __future__ import annotations

import builtins
import importlib.util
import io
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
LIB_PATH = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts" / "_lib" / "consent.py"
)


@pytest.fixture(scope="module")
def consent():
    module_name = "pm_consent_lib_under_test"
    spec = importlib.util.spec_from_file_location(module_name, LIB_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class _Terminal(io.StringIO):
    """A standard input a person types at."""

    def isatty(self) -> bool:
        return True


class _Pipe(io.StringIO):
    """A standard input with an answer piped into it, as `echo y | …` gives."""

    def isatty(self) -> bool:
        return False


def _never_asked(question: str) -> str:
    raise AssertionError(f"asked off a terminal: {question!r}")


@pytest.fixture
def argv(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["close-milestone.py", "6", "--target", "Sprint 7"])


# --- off a terminal ------------------------------------------------------


def test_a_piped_yes_is_refused_and_never_read(consent, monkeypatch, capsys, argv) -> None:
    monkeypatch.setattr(sys, "stdin", _Pipe("y\n"))
    monkeypatch.setattr(builtins, "input", _never_asked)
    rc = consent.authorise("Close? [y/N] ", yes=False, step="Closing milestone #6", verb="close")
    assert rc == consent.REFUSED == 1
    err = capsys.readouterr().err
    assert "[refused] Closing milestone #6 is the person's to authorise" in err
    assert "Nothing was changed." in err


def test_the_refusal_names_the_command_with_yes(consent, monkeypatch, capsys, argv) -> None:
    monkeypatch.setattr(sys, "stdin", _Pipe(""))
    consent.authorise("Close? [y/N] ", yes=False, step="Closing", verb="close-milestone")
    assert "pkit pm close-milestone 6 --target 'Sprint 7' --yes" in capsys.readouterr().err


@pytest.mark.parametrize("stdin", [None, "closed", "no-isatty"])
def test_an_absent_or_closed_stdin_is_no_terminal(consent, monkeypatch, stdin) -> None:
    if stdin == "closed":
        stream = io.StringIO()
        stream.close()  # its isatty raises ValueError, as a closed stdin's does
        monkeypatch.setattr(sys, "stdin", stream)
    elif stdin == "no-isatty":
        monkeypatch.setattr(sys, "stdin", object())
    else:
        monkeypatch.setattr(sys, "stdin", None)
    monkeypatch.setattr(builtins, "input", _never_asked)
    assert consent.at_a_terminal() is False
    assert consent.authorise("?", yes=False, step="Closing", verb="close") == consent.REFUSED


def test_the_re_run_line_escapes_what_a_terminal_would_act_on(consent, monkeypatch) -> None:
    """A newline or an escape in an argument is shown as its escape, so the
    printed command stays one line and holds what it shows."""
    monkeypatch.setattr(sys, "argv", ["add-member.py", "--name", "a\nb\x1b[2Jc", "Aleš"])
    line = consent.rerun_with_yes("add-member")
    assert line == "pkit pm add-member --name 'a\\nb\\x1b[2Jc' 'Aleš' --yes"
    assert line.isprintable()


def test_refuse_alone_says_the_same_and_returns_refused(consent, capsys, argv) -> None:
    assert consent.refuse("Removing workstream 'cli'", "remove-workstream") == consent.REFUSED
    err = capsys.readouterr().err
    assert "[refused] Removing workstream 'cli' is the person's to authorise" in err
    assert "pkit pm remove-workstream 6 --target 'Sprint 7' --yes" in err


# --- --yes and a terminal, as before ----------------------------------------


def test_yes_authorises_off_a_terminal_without_asking(consent, monkeypatch) -> None:
    monkeypatch.setattr(sys, "stdin", _Pipe(""))
    monkeypatch.setattr(builtins, "input", _never_asked)
    assert consent.authorise("?", yes=True, step="Closing", verb="close") is None


@pytest.mark.parametrize("reply", ["y", "yes", " Y "])
def test_a_yes_at_the_terminal_goes_on(consent, monkeypatch, reply) -> None:
    monkeypatch.setattr(sys, "stdin", _Terminal())
    asked: list[str] = []
    monkeypatch.setattr(builtins, "input", lambda q: asked.append(q) or reply)
    assert consent.authorise("Close? [y/N] ", yes=False, step="Closing", verb="close") is None
    assert asked == ["Close? [y/N] "]


@pytest.mark.parametrize("reply", ["", "n", "no", "maybe"])
def test_anything_else_at_the_terminal_declines(consent, monkeypatch, capsys, reply) -> None:
    monkeypatch.setattr(sys, "stdin", _Terminal())
    monkeypatch.setattr(builtins, "input", lambda q: reply)
    assert consent.authorise("?", yes=False, step="Closing", verb="close") == 0
    assert "aborted." in capsys.readouterr().err


def test_an_input_ended_at_the_terminal_declines(consent, monkeypatch) -> None:
    monkeypatch.setattr(sys, "stdin", _Terminal())

    def ended(question: str) -> str:
        raise EOFError

    monkeypatch.setattr(builtins, "input", ended)
    assert consent.authorise("?", yes=False, step="Closing", verb="close") == 0
