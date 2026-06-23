"""Read-view output renderer (per ADR-006). Tool-internal; NOT propagated.

The executable, mechanical half of the CLI output conventions (the
`cli-output-conventions` / `cli-design-conventions` scratchpad notes): a
title + optional status line, CAPS-headed sections of computed-width table
rows with constant-column suppression, a Legend block, a Commands block, and
the Header / Body / Reference zone rhythm — separated by blank lines, never
horizontal rules.

Option A' (per ADR-006): plain string/tuple/dict *semantic-data* parts feed a
single ``view()`` assembler that owns all layout. Parts carry data, not
pre-formatted strings, so the same data can later feed a ``--json`` dump. The
typed ``Document`` model (Option B) is deferred behind ADR-006's trigger.

The TTY-aware semantic styling layer (per ADR-011) lives here: authors tag
text with closed *semantic roles* via ``style(role, text)``; this module owns
the role→ANSI map. The colour decision is resolved **once per process at the
command boundary** (``resolve_color``) and read by ``style()`` — never sniffed
per-call, which would inspect the wrong stream for commands that build a string
and let the caller print. Styling is provably never load-bearing:
``strip_ansi(style(...)) == <plain text>`` for every role, so the plain
rendering always carries the full structure (scriptable, accessible). v1 is
monochrome (bold/dim); colour is a deferred change to the map alone.
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import textwrap
from collections.abc import Mapping, Sequence
from typing import IO

INDENT = "  "
SEP = "  "


# --- semantic styling layer (ADR-011) ---------------------------------------

# Closed semantic-role enum (ADR-011 §1). Authors tag meaning, never
# presentation. The role→style map below is policy and lives here.
ROLES = ("title", "heading", "strong", "muted", "command",
         "success", "warn", "danger")

_BOLD = "\033[1m"
_DIM = "\033[2m"
_RESET = "\033[0m"

# v1 monochrome map (ADR-011 §5): bold/dim only, theme-independent. The
# colour-oriented roles render conservatively (plain) in v1 — the existing
# ✓/⚠/✗ symbols and backticks remain the load-bearing signal. Adding colour
# later is a one-line change *here*, never a re-tagging of call sites.
_ROLE_SGR: dict[str, str] = {
    "title": _BOLD,
    "heading": _BOLD,
    "strong": _BOLD,
    "muted": _DIM,
    "command": "",
    "success": "",
    "warn": "",
    "danger": "",
}

_ANSI_RE = re.compile(r"\033\[[0-9;]*m")

# Process-wide resolved colour decision (ADR-011 §2). Resolved once at the
# command boundary; read by every style() call. Default off → plain unless a
# boundary explicitly resolves it (keeps library/test imports plain).
_color_enabled = False


def resolve_color(flag: str = "auto", *, stream: IO[str] | None = None) -> bool:
    """Resolve the process-wide colour decision once, at the command boundary.

    Precedence (ADR-011 §2): an explicit ``--color always|never`` wins over
    everything (including ``NO_COLOR``); otherwise ``auto`` defers to
    ``NO_COLOR`` (its presence disables colour) and then to ``isatty()`` /
    ``TERM=dumb``. Sets and returns the decision."""
    if flag == "always":
        decision = True
    elif flag == "never":
        decision = False
    else:  # auto
        if os.environ.get("NO_COLOR") is not None:
            decision = False
        else:
            st = stream if stream is not None else sys.stdout
            decision = bool(getattr(st, "isatty", lambda: False)()) \
                and os.environ.get("TERM") != "dumb"
    set_color(decision)
    return decision


def set_color(enabled: bool) -> None:
    """Set the resolved colour decision directly (boundary / test use)."""
    global _color_enabled
    _color_enabled = enabled


def style(role: str, text: str) -> str:
    """Wrap ``text`` in the SGR codes for ``role`` when colour is on; else
    return it unchanged. The one gate that emits SGR bytes (ADR-011 §2).

    Never load-bearing: ``strip_ansi(style(r, t)) == t`` for every role."""
    if role not in _ROLE_SGR:
        raise ValueError(f"unknown style role: {role!r} (roles: {', '.join(ROLES)})")
    if not _color_enabled:
        return text
    sgr = _ROLE_SGR[role]
    return f"{sgr}{text}{_RESET}" if sgr else text


def strip_ansi(text: str) -> str:
    """Remove SGR escape sequences — the inverse used by the never-load-bearing
    invariant test (``strip_ansi(render(color)) == render(plain)``)."""
    return _ANSI_RE.sub("", text)


# --- prose-wrapping leaf (ADR-024) ------------------------------------------

# The no-hard-wrap sentinel (ADR-024 §3): a resolved width of 0 means
# "hanging-indent only, never reflow a long line". Piped / non-TTY /
# indeterminable streams resolve to this *regardless of COLUMNS* — the
# deliberate divergence from ADR-011's override precedence (a stray COLUMNS must
# not inject width-driven breaks into piped output).
NO_WRAP = 0

# The content minimum below which a resolved width is treated as no-wrap
# (ADR-024 §3 "minimum-width floor"): there is no sane reflow into a column
# narrower than the indentation plus a few characters, so a degenerate narrow
# width degrades to the readable piped form instead of one-char-per-line output.
_MIN_CONTENT_WIDTH = 20

# Process-wide resolved wrap width (ADR-024 §3). Resolved once at the command
# boundary (the same factoring as the colour decision — the (report, str) return
# pattern means a string-builder cannot see the print stream); read by wrap(),
# which never sniffs isatty() itself. Default off → no-wrap unless a boundary
# explicitly resolves it (keeps library/test imports inert).
_wrap_width = NO_WRAP


def resolve_width(flag: int | None = None, *, stream: IO[str] | None = None) -> int:
    """Resolve the process-wide wrap width once, at the command boundary.

    Policy (ADR-024 §3), the deliberate divergence from ADR-011's colour
    precedence: **piped / non-TTY / indeterminable is always no-wrap, regardless
    of COLUMNS** — a stray COLUMNS in the environment must never inject
    width-driven breaks into piped output. On a TTY the width is an explicit
    ``flag`` (a future ``--width``) if given, else ``COLUMNS`` if set and valid,
    else ``shutil.get_terminal_size((80, …)).columns``; a zero / nonsensical
    reading (below the floor) is treated as indeterminate → no-wrap rather than
    pathological one-char-per-line output. Sets and returns the decision."""
    st = stream if stream is not None else sys.stdout
    on_tty = bool(getattr(st, "isatty", lambda: False)())
    if not on_tty:
        # Piped wins over COLUMNS (ADR-024 §3) — unconditionally no-wrap.
        set_wrap_width(NO_WRAP)
        return NO_WRAP

    if flag is not None and flag > 0:
        width = flag
    else:
        env_columns = _columns_from_env()
        width = (
            env_columns
            if env_columns is not None
            else shutil.get_terminal_size((80, 24)).columns
        )

    # Guard a zero / nonsensical reading (ADR-024 §3): any value below the floor
    # (a 0-column get_terminal_size, a degenerate COLUMNS) is indeterminate →
    # no-wrap, never pathological one-char-per-line output.
    decision = width if width >= _MIN_CONTENT_WIDTH else NO_WRAP
    set_wrap_width(decision)
    return decision


def _columns_from_env() -> int | None:
    """Read an integer COLUMNS from the environment, or None when unset or
    unparseable. A parsed value (even 0 / negative) is returned and left to the
    minimum-width floor to reject — so a degenerate COLUMNS degrades to no-wrap
    rather than silently falling back to the terminal size (ADR-024 §3:
    COLUMNS sets the width only when on a TTY)."""
    raw = os.environ.get("COLUMNS")
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def set_wrap_width(width: int) -> None:
    """Set the resolved wrap width directly (boundary / test use). Mirrors
    ``set_color`` for the width axis (ADR-024 §3)."""
    global _wrap_width
    _wrap_width = width


def wrap(text: str, *, indent: str, hang: str = "", width: int | None = None,
         first_line_indent: int = 0) -> list[str]:
    """Lay out one author-supplied prose field into indented lines (ADR-024).

    The one place prose breaks. Two transformations, split by ADR-024 §2:

    - **Hanging-indent is unconditional.** Author newlines (``\\n``) always
      produce continuation lines: the first line is ``indent + <text>``, every
      continuation is ``indent + hang + <text>``. Applied even when no width is
      resolved, because a multi-line field flush at column 0 is unreadable on the
      human (porcelain) surface regardless of terminal width.
    - **Width hard-wrap is TTY-gated.** When the resolved width is a positive
      column count, an over-long single line is additionally reflowed to that
      width, measured on **visible** width (``strip_ansi`` length). Long tokens
      *overflow* the column rather than break mid-token
      (``break_long_words=False``) — a path / URL / command-role string stays
      copy-pasteable (ADR-024 §3). The text passed here must be **plain** (wrap
      *before* ``style()``); the caller styles the returned lines.

    ``first_line_indent`` is the visible width **already consumed on line 1** by a
    caller-built prefix sitting before the prose tail — the inline-suffix case
    (ADR-024 follow-up): ``Where: <state> — <meaning>`` and
    ``<marker> <to> [<trigger>] — <why>``, where the prefix is a runtime-variable,
    already-styled string this leaf must not re-derive. To keep ``wrap`` style-free
    and its return contract intact, the caller passes only the prefix's **visible
    width** (not the styled prefix itself), so:

    - ``out[0]`` carries the line-1 prose tail with **no leading indent** — the
      caller concatenates its own styled prefix + ``out[0]``. The line-1 prose
      budget reserves the prefix: ``width - first_line_indent`` (``first_line_indent``
      already counts every leading visible column of line 1, so ``len(indent)`` is
      NOT subtracted again — ``out[0]`` carries no ``indent``).
    - ``out[1:]`` are continuation lines indented at ``indent + hang`` verbatim,
      ready to append as-is.

    With ``first_line_indent=0`` (the default) the prefix reservation is zero and
    line 1 is ``indent + <text>`` exactly as before — byte-for-byte identical to
    the pre-follow-up behaviour for the own-line callers.

    ``width=None`` reads the module-resolved ``_wrap_width``; ``NO_WRAP`` (the
    sentinel, or a width below the indent+hang+floor) means hanging-indent only.
    """
    resolved = _wrap_width if width is None else width
    author_lines = str(text).split("\n")
    cont_prefix = indent + hang
    inline_suffix = first_line_indent > 0

    # Minimum-width floor (ADR-024 §3): a width that leaves less than the content
    # minimum after the deepest indentation is treated as no-wrap.
    if resolved > 0 and resolved - len(cont_prefix) < _MIN_CONTENT_WIDTH:
        resolved = NO_WRAP

    out: list[str] = []
    for i, line in enumerate(author_lines):
        # Only the very first emitted line (first author-line, first width-piece)
        # wears the inline-suffix line-1 treatment: empty emitted prefix + the
        # caller's prefix width reserved. Every other line — a later author-line,
        # OR a width-wrap continuation of any author-line — hangs at the
        # continuation prefix, the established sub-line rhythm. When NOT an
        # inline suffix (first_line_indent=0), line 1 is the own-line indent and
        # this collapses to the original single-budget behaviour exactly.
        if i == 0 and inline_suffix:
            emit_prefix, line1_consume = "", first_line_indent
        elif i == 0:
            emit_prefix, line1_consume = indent, len(indent)
        else:
            emit_prefix, line1_consume = cont_prefix, len(cont_prefix)

        if resolved <= 0:
            out.append(emit_prefix + line)
            continue

        # Hard-wrap this author-line to the visible column. textwrap measures the
        # plain text (we never pass styled text here, per ADR-024 §4), so its
        # character count is the visible width.
        if not (i == 0 and inline_suffix):
            # Own-line author-line: a single budget for all its width-pieces,
            # exactly as before — preserves byte-identity for first_line_indent=0.
            avail = max(resolved - line1_consume, 1)
            pieces = textwrap.wrap(
                line, width=avail, break_long_words=False, break_on_hyphens=False
            ) or [""]
            out.extend(emit_prefix + piece for piece in pieces)
            continue

        # Inline-suffix line 1: piece 0 reserves the caller's prefix width; the
        # remainder reflows at the continuation budget (the sub-line rhythm), so a
        # long state-id / trigger does not collapse the continuation width.
        # line 1's budget is deliberately NOT floored (only cont_prefix is, above):
        # break_long_words=False bounds the degradation — a tiny line1_avail emits
        # one whole word and reflows the rest at cont_avail, never one char per line.
        line1_avail = max(resolved - line1_consume, 1)
        cont_avail = max(resolved - len(cont_prefix), 1)
        pieces = textwrap.wrap(
            line, width=line1_avail, break_long_words=False, break_on_hyphens=False
        ) or [""]
        out.append(emit_prefix + pieces[0])
        if len(pieces) > 1:
            remainder = " ".join(pieces[1:])
            cont_pieces = textwrap.wrap(
                remainder, width=cont_avail,
                break_long_words=False, break_on_hyphens=False,
            ) or [""]
            out.extend(cont_prefix + piece for piece in cont_pieces)
    return out


# --- semantic-data part constructors (A': dicts, not types) ------------------

def title(noun: str, count: str | int | None = None, gloss: str | None = None) -> dict:
    """A title part: ``<noun> — <count>   (<gloss>)``. ``count`` is the
    caller-composed qualifier string (e.g. ``"3 available"``)."""
    return {"noun": noun, "count": count, "gloss": gloss}


def status(label: str = "", value: str | None = None, gloss: str | None = None,
           placement: str = "footer", extra: Sequence[str] = (),
           warn: str | None = None) -> dict:
    """A status line: ``<label>: <value>   (<gloss>)`` with optional indented
    ``extra`` sub-lines and a ``warn`` line. ``placement`` is ``"header"`` (a
    framing precondition, leads) or ``"footer"`` (a summary of the body)."""
    return {"label": label, "value": value, "gloss": gloss,
            "placement": placement, "extra": list(extra), "warn": warn}


def section(rows: Sequence[Mapping[str, str]] = (), columns: Sequence[str] = (),
            header: str | None = None, gloss: str | None = None,
            marker: str | None = None, empty: str | None = None) -> dict:
    """A body section. ``rows`` are dicts keyed by column name; ``columns`` is
    the ordered key list. A column whose value is empty in every row is
    suppressed. ``marker`` names a column rendered as a one-char row prefix
    (itself suppressed when empty in every row). ``header`` (+ ``gloss``) is the
    CAPS section header; ``empty`` is the one-line empty-state."""
    return {"rows": [dict(r) for r in rows], "columns": list(columns),
            "header": header, "gloss": gloss, "marker": marker, "empty": empty}


# --- rendering --------------------------------------------------------------

def _fmt_title(t: Mapping) -> str:
    head = style("title", t["noun"])
    if t.get("count") is not None:
        head += f" — {t['count']}"
    if t.get("gloss"):
        head += style("muted", f"   ({t['gloss']})")
    return head


def _fmt_status(s: Mapping) -> list[str]:
    out: list[str] = []
    if s.get("label") or s.get("value") is not None:
        line = s.get("label") or ""
        if s.get("value") is not None:
            line += f": {s['value']}"
        line = style("strong", line)
        if s.get("gloss"):
            line += style("muted", f"   ({s['gloss']})")
        out.append(line)
    out += [INDENT + e for e in s.get("extra", [])]
    if s.get("warn"):
        out.append(INDENT + f"⚠ {s['warn']}")  # ⚠ is the load-bearing signal (warn role plain in v1)
    return out


def _shown_columns(sections: Sequence[Mapping]) -> dict[str, bool]:
    shown: dict[str, bool] = {}
    for sec in sections:
        for col in sec["columns"]:
            shown.setdefault(col, False)
            if any(str(r.get(col, "")).strip() for r in sec["rows"]):
                shown[col] = True
    return shown


def _widths(sections: Sequence[Mapping], shown: Mapping[str, bool]) -> dict[str, int]:
    """Column widths computed across ALL sections' rows, so sections sharing a
    column set align with each other."""
    w: dict[str, int] = {}
    for sec in sections:
        for r in sec["rows"]:
            for col in sec["columns"]:
                if shown.get(col):
                    w[col] = max(w.get(col, 0), len(str(r.get(col, ""))))
    return w


def _marker_on(sections: Sequence[Mapping]) -> bool:
    for sec in sections:
        m = sec.get("marker")
        if m and any(str(r.get(m, "")).strip() for r in sec["rows"]):
            return True
    return False


def _fmt_row(r: Mapping, sec: Mapping, widths: Mapping[str, int],
             shown: Mapping[str, bool], marker_on: bool) -> str:
    cells: list[str] = []
    if marker_on:
        m = sec.get("marker")
        cells.append((str(r.get(m, " "))[:1] or " ") if m else " ")
    for col in sec["columns"]:
        if shown.get(col):
            cells.append(f"{str(r.get(col, '')):{widths[col]}}")
    return (INDENT + SEP.join(cells)).rstrip()


def _pairs(items: Sequence[tuple[str, str]]) -> list[str]:
    if not items:
        return []
    w = max(len(a) for a, _ in items)
    return [f"{INDENT}{a:{w}}{SEP}{b}" for a, b in items]


def view(*, title: Mapping, sections: Sequence[Mapping] = (),
         status: Mapping | None = None,
         legend: Sequence[tuple[str, str]] = (),
         commands: Sequence[tuple[str, str]] = ()) -> str:
    """Assemble the parts into the read-view layout and return a string."""
    sections = list(sections)
    lines = [_fmt_title(title)]

    if status and status.get("placement") == "header":
        lines += [""] + _fmt_status(status)

    shown = _shown_columns(sections)
    widths = _widths(sections, shown)
    marker_on = _marker_on(sections)
    for sec in sections:
        lines.append("")
        if sec.get("header"):
            h = style("heading", sec["header"])
            if sec.get("gloss"):
                h += style("muted", f" — {sec['gloss']}")
            lines.append(h)
        if sec["rows"]:
            lines += [_fmt_row(r, sec, widths, shown, marker_on) for r in sec["rows"]]
        elif sec.get("empty"):
            lines.append(INDENT + sec["empty"])

    if status and status.get("placement") != "header":
        lines += [""] + _fmt_status(status)

    if legend:
        lines += ["", style("heading", "Legend")] + _pairs(list(legend))
    if commands:
        lines += ["", style("heading", "Commands")] + _pairs(list(commands))

    return "\n".join(lines) + "\n"
