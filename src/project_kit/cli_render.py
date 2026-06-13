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
import sys
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
