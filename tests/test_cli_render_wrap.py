"""The prose-wrapping leaf (ADR-024): hanging-indent always, width-wrap
TTY-only, resolved once at the boundary; long tokens overflow, never break.

These cover `wrap()` and `resolve_width()` in isolation. The load-bearing
`--json` byte-stability invariant lives with the process status tests (the
machine surface that must never call `wrap()`).
"""
from __future__ import annotations

import pytest

from project_kit import cli_render
from project_kit.cli_render import NO_WRAP, resolve_width, set_wrap_width, strip_ansi, wrap


@pytest.fixture(autouse=True)
def _reset_wrap_width():
    """Each test owns the process-wide wrap width; restore the default (no-wrap)
    afterwards so import order can't leak a wrapped state."""
    cli_render.set_wrap_width(NO_WRAP)
    yield
    cli_render.set_wrap_width(NO_WRAP)


class _FakeStream:
    def __init__(self, tty: bool):
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


# --- hanging-indent (unconditional, ADR-024 §2) ------------------------------

def test_single_line_gets_only_the_indent():
    set_wrap_width(NO_WRAP)
    assert wrap("hello", indent="    ") == ["    hello"]


def test_author_newlines_hang_under_the_indent_without_width():
    set_wrap_width(NO_WRAP)
    out = wrap("first\nsecond\nthird", indent="    ", hang="  ")
    assert out == ["    first", "      second", "      third"]


def test_hanging_indent_applies_even_when_no_width_resolved():
    # The #215 bug class: continuation lines must never dump flush at column 0.
    set_wrap_width(NO_WRAP)
    out = wrap("line one\nline two", indent="        ")
    assert out[0] == "        line one"
    assert out[1] == "        line two"
    assert not out[1].startswith("line two")  # not flush-left


# --- width hard-wrap (TTY-gated, measured on visible width, ADR-024 §3) ------

def test_long_single_line_hard_wraps_to_resolved_width():
    set_wrap_width(40)
    text = "the quick brown fox jumps over the lazy dog again and again"
    out = wrap(text, indent="  ")
    assert len(out) > 1
    for line in out:
        assert line.startswith("  ")
        assert len(line) <= 40


def test_width_measured_on_visible_not_styled_length():
    # wrap() takes PLAIN text (ADR-024 §4); strip_ansi of each returned line must
    # equal the line itself (no SGR leaks in), and width is the visible count.
    set_wrap_width(30)
    out = wrap("alpha beta gamma delta epsilon zeta", indent="  ")
    for line in out:
        assert strip_ansi(line) == line
        assert len(line) <= 30


def test_long_token_overflows_rather_than_breaking_mid_token():
    # break_long_words=False: a too-long path/command stays copy-pasteable — it
    # overflows past the width on its own line rather than being chopped.
    # Width 50, indent 2 → avail 48 is comfortably above the floor (20), so
    # textwrap actually runs (a width below the floor would no-wrap and mask this).
    set_wrap_width(50)
    token = "/srv/app/data/cache/intermediate/snapshots/region/payload.bin"
    assert len(token) > 48  # genuinely exceeds the available width
    out = wrap(token, indent="  ")
    assert out == ["  " + token]  # one over-long line, token intact (NOT mid-broken)
    assert len(out[0]) > 50  # proves it overflowed the width rather than wrapping


def test_long_token_with_surrounding_words_still_keeps_the_token_whole():
    set_wrap_width(50)
    token = "/srv/app/data/cache/intermediate/snapshots/region/payload.bin"
    out = wrap(f"run {token} now", indent="  ")
    assert len(out) > 1  # it DID wrap (above the floor), not no-wrap
    assert any(token in line for line in out)  # the token survives intact in one line
    # and no line contains a broken fragment of it
    assert not any((token[:20] in line and token not in line) for line in out)


def test_hyphenated_token_not_split_at_hyphens():
    # break_on_hyphens=False: a hyphenated path/identifier is not split at its hyphens.
    set_wrap_width(50)
    token = "alpha-beta-gamma-delta-epsilon-zeta-eta-theta-iota-kappa"
    assert len(token) > 48
    out = wrap(token, indent="  ")
    assert out == ["  " + token]  # whole, not split at a hyphen


# --- minimum-width floor (ADR-024 §3) ----------------------------------------

def test_width_below_floor_degrades_to_no_wrap():
    # A width that leaves less than the content minimum after the indent is
    # treated as no-wrap (no pathological one-char-per-line output).
    set_wrap_width(NO_WRAP)
    long_line = "this is a single long line that would otherwise wrap"
    out = wrap(long_line, indent="          ", hang="", width=15)
    assert out == ["          " + long_line]


def test_explicit_width_argument_overrides_module_global():
    set_wrap_width(NO_WRAP)  # module says no-wrap...
    # width=25 is above the content floor (no indent), so the arg wins and wraps.
    out = wrap("alpha beta gamma delta epsilon zeta eta", indent="", width=25)
    assert len(out) > 1


# --- resolve_width (boundary policy, ADR-024 §3) -----------------------------

def test_piped_is_no_wrap_regardless_of_columns(monkeypatch):
    # The deliberate divergence from ADR-011: COLUMNS never forces wrap onto a pipe.
    monkeypatch.setenv("COLUMNS", "120")
    assert resolve_width(stream=_FakeStream(False)) == NO_WRAP


def test_tty_uses_columns_env_when_set(monkeypatch):
    monkeypatch.setenv("COLUMNS", "100")
    assert resolve_width(stream=_FakeStream(True)) == 100


def test_tty_falls_back_to_terminal_size_when_columns_unset(monkeypatch):
    monkeypatch.delenv("COLUMNS", raising=False)
    width = resolve_width(stream=_FakeStream(True))
    # get_terminal_size's (80, 24) fallback, or the real terminal — either way a
    # sane positive width at or above the floor (never the no-wrap sentinel here,
    # since the fallback default 80 is well above it).
    assert width >= 20


def test_tty_zero_columns_reading_degrades_to_no_wrap(monkeypatch):
    # Guard a nonsensical reading: COLUMNS=0 is below the floor → no-wrap, never
    # one-char-per-line output.
    monkeypatch.setenv("COLUMNS", "0")
    assert resolve_width(stream=_FakeStream(True)) == NO_WRAP


def test_tty_below_floor_columns_degrades_to_no_wrap(monkeypatch):
    monkeypatch.setenv("COLUMNS", "5")
    assert resolve_width(stream=_FakeStream(True)) == NO_WRAP


def test_explicit_flag_wins_on_a_tty(monkeypatch):
    monkeypatch.setenv("COLUMNS", "200")
    assert resolve_width(80, stream=_FakeStream(True)) == 80


def test_explicit_flag_does_not_force_wrap_onto_a_pipe(monkeypatch):
    monkeypatch.delenv("COLUMNS", raising=False)
    assert resolve_width(80, stream=_FakeStream(False)) == NO_WRAP


def test_resolve_sets_the_module_global(monkeypatch):
    monkeypatch.setenv("COLUMNS", "90")
    resolve_width(stream=_FakeStream(True))
    # wrap() with width=None reads the freshly-resolved module global.
    out = wrap("a b c d e f g h i j k l m n o p q r s t u v", indent="")
    assert all(len(line) <= 90 for line in out)
