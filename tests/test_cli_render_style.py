"""The TTY-aware semantic styling layer (ADR-011): the gate, the precedence,
and the load-bearing invariant — styling is *never* load-bearing.

The golden test (``test_never_load_bearing_*``) is the net ADR-011 §3 pins:
``strip_ansi(render(color=on)) == render(color=off)``. If it holds, style can
never carry information the plain text doesn't.
"""
from __future__ import annotations

import pytest

from project_kit import cli_render
from project_kit.cli_render import ROLES, section, status, style, title, view


@pytest.fixture(autouse=True)
def _reset_color():
    """Each test owns the process-wide colour decision; restore the default
    (off) afterwards so import order can't leak a styled state."""
    cli_render.set_color(False)
    yield
    cli_render.set_color(False)


# --- the gate ----------------------------------------------------------------

def test_style_plain_when_disabled():
    cli_render.set_color(False)
    for role in ROLES:
        assert style(role, "x") == "x"


def test_style_wraps_emphasis_roles_when_enabled():
    cli_render.set_color(True)
    # The v1 monochrome roles that actually emit bytes.
    for role in ("title", "heading", "strong", "muted"):
        out = style(role, "x")
        assert out != "x"
        assert out.startswith("\033[")
        assert out.endswith("\033[0m")


def test_style_conservative_roles_stay_plain_in_v1():
    # ADR-011 §5: colour-oriented roles render plain in monochrome v1 — the
    # ✓/⚠/✗ symbols and backticks remain the load-bearing signal.
    cli_render.set_color(True)
    for role in ("command", "success", "warn", "danger"):
        assert style(role, "x") == "x"


def test_unknown_role_is_a_hard_error():
    with pytest.raises(ValueError):
        style("bold_red", "x")  # presentation, not a semantic role


# --- the never-load-bearing invariant (ADR-011 §3) ---------------------------

def test_never_load_bearing_per_role():
    for role in ROLES:
        cli_render.set_color(True)
        styled = style(role, "the structure")
        cli_render.set_color(False)
        plain = style(role, "the structure")
        assert cli_render.strip_ansi(styled) == plain == "the structure"


def _representative_view() -> str:
    return view(
        title=title("permissions", "3 grants", gloss="operator"),
        sections=[section(
            rows=[{"name": "fs.read", "scope": "./src"},
                  {"name": "fs.write", "scope": ""}],
            columns=["name", "scope"],
            header="GRANTS", gloss="active",
        )],
        status=status("Result", "autonomy reached", gloss="probe passed"),
        legend=[("✓", "allowed")],
        commands=[("pkit permissions probe", "prove it")],
    )


def test_never_load_bearing_full_view():
    cli_render.set_color(True)
    styled = _representative_view()
    cli_render.set_color(False)
    plain = _representative_view()
    assert cli_render.strip_ansi(styled) == plain


def test_styled_view_actually_emits_codes():
    # Guard against the invariant passing vacuously (nothing ever styled).
    cli_render.set_color(True)
    assert "\033[" in _representative_view()


# --- precedence resolution (ADR-011 §2) --------------------------------------

class _FakeStream:
    def __init__(self, tty: bool):
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


def test_always_wins_over_no_color(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    assert cli_render.resolve_color("always") is True


def test_never_with_no_color(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert cli_render.resolve_color("never", stream=_FakeStream(True)) is False


def test_auto_defers_to_no_color(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "")  # presence, even empty, disables
    assert cli_render.resolve_color("auto", stream=_FakeStream(True)) is False


def test_auto_on_tty(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    assert cli_render.resolve_color("auto", stream=_FakeStream(True)) is True


def test_auto_off_when_piped(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert cli_render.resolve_color("auto", stream=_FakeStream(False)) is False


def test_auto_off_on_dumb_terminal(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "dumb")
    assert cli_render.resolve_color("auto", stream=_FakeStream(True)) is False
