"""Permission-prompt diagnostic capture (per PRJ-006, sub-decision 2).

Propagated into every adopter tree beside the decision core (`decide.py`), and
imported by the Claude-Code PreToolUse hook AFTER the decision is computed. This
is the harness-side half of the diagnostic loop: it observes the hook's own
*deferred* (abstain) verdict and, only while a bounded diagnostic session is
armed, appends a redacted record to a local log.

It is deliberately separate from `decide.py`:

  - `decide.py` is the PURE, same-code decision core shared by the hook and the
    CLI; it must decide identically and have no side effects. Capture is a
    side-effect that lives ONLY on the harness boundary (a "prompt" is a harness
    behaviour — PRJ-006), so it must not touch the decision core.

  - This module runs under the hook's bare `python3` (no uv, no third-party deps,
    ADR-014), so it is stdlib-only — same runtime constraint as `decide.py`.

Inert-on-failure contract (PRJ-006 sub-decision 2): the single entry point
``capture(...)`` is wrapped so that ANY exception — unreadable marker, unwritable
log, a clock fault — is swallowed and turned into a no-op. A capture failure can
never change a decision (the decision is already computed before this is called)
and can never break the hook's fail-open guarantee. The hook still wraps the call
in its own try/except as a second belt; this module's internal guard is the first.

The captured signal is a SUPERSET of real prompts: the hook sees only its own
abstain (defer-to-harness), not whether the harness ultimately prompted. The
report states this as *coverage*, never as a predicted prompt-count decrement.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

# Same project-relative locations the CLI half (`permissions.py`) reads. Both
# sides resolve these from the project root; if you move them, move both. The CLI
# mirrors the paths via its own `_diagnose_*` helpers (it cannot import this
# module — it runs under uv, this runs under the bare-python3 hook).
_MARKER_REL = (".pkit", "permissions", "project", "diagnose.yaml")
_LOG_REL = (".pkit", "permissions", "project", "diagnose-log.jsonl")

# Fallbacks for a marker that predates a field (forward-compatible reads); the
# authoritative defaults are the CLI's `diagnose on`, which writes them in.
_DEFAULT_MAX_ENTRIES = 2000
_DEFAULT_REDACT = True
# Redaction keeps the program token and any immediately following SUBCOMMAND-like
# tokens (bare words: `npm run build`, `gh pr list`), stopping at the first token
# that could carry data — a flag (`-x` / `--y`), an assignment (`k=v`), or a
# path/URL. Secrets and paths live past that boundary, so they are dropped. This
# is stricter than "keep the first N tokens" (which can leak a secret in token N).
_REDACT_MAX_SUBCOMMANDS = 4


def _marker_path(root: Path) -> Path:
    return root.joinpath(*_MARKER_REL)


def _log_path(root: Path) -> Path:
    return root.joinpath(*_LOG_REL)


def _read_marker(root: Path) -> dict | None:
    """Read the armed marker as a tiny dict, or None when absent/unreadable.

    The marker is a flat YAML of scalar `key: value` lines (armed_at, ttl_seconds,
    max_entries, redact). We parse it with a deliberately minimal stdlib reader
    rather than importing a YAML library — this runs under the bare-python3 hook
    (ADR-014) and the marker shape is fixed and trivial."""
    path = _marker_path(root)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    out: dict[str, object] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        out[key.strip()] = _coerce(value.strip())
    return out


def _coerce(value: str) -> object:
    if value in ("true", "True"):
        return True
    if value in ("false", "False"):
        return False
    try:
        return int(value)
    except ValueError:
        return value


def _armed(marker: dict, now: float) -> bool:
    """Is the session armed AND unexpired? A marker with no/zero ttl is treated
    as expired (fail-safe: a malformed marker captures nothing)."""
    armed_at = marker.get("armed_at")
    ttl = marker.get("ttl_seconds")
    if not isinstance(armed_at, int) or not isinstance(ttl, int) or ttl <= 0:
        return False
    return now < armed_at + ttl


# Structural shell operators carry no data (they are syntax, not arguments), so
# redaction preserves them — they are the signal the classifier uses to spot the
# "shell-shape the matcher can't vet" group. Dropping them would silently demote
# a `cd … && …` into the wrong group.
_SHELL_OPERATORS = frozenset({"&&", "||", "|", ";", "&", "(", ")"})


def _is_subcommand_token(tok: str) -> bool:
    """A bare subcommand word (`run`, `build`, `pr`, `list`) — safe to keep for
    classification. Anything with a flag dash, an assignment, a path/URL slash,
    or a non-word character could carry data, so it is NOT a subcommand token and
    everything from it onward is redacted."""
    if not tok or tok[0] == "-" or "=" in tok or "/" in tok or ":" in tok:
        return False
    return tok.replace("-", "").replace("_", "").isalnum()


def _redact(command: str) -> str:
    """Keep the program token and the run of subcommand-like tokens after it (and
    any structural shell operators, which carry no data); replace each run of
    data-carrying tokens with a single redaction marker. The kept head + operators
    are what the classifier groups on; the dropped tail is where paths and secrets
    live."""
    tokens = command.split()
    if not tokens:
        return command
    out: list[str] = []
    kept_words = 0  # subcommand-like words kept since the last operator/program
    redacting = False
    for i, tok in enumerate(tokens):
        if tok in _SHELL_OPERATORS:
            out.append(tok)
            kept_words = 0  # a new command segment begins after an operator
            redacting = False
            continue
        # A leading env-assignment prefix (`FOO=bar`) before the first word is
        # structural noise we drop quietly (it can carry data) without a marker.
        is_env_prefix = "=" in tok and not tok.startswith("-") and kept_words == 0 and not redacting
        if is_env_prefix:
            continue
        keepable = kept_words == 0 or _is_subcommand_token(tok)
        # The very first token of a segment (the program) is always kept, even if
        # it isn't "subcommand-like" by the strict test (e.g. an absolute path).
        if kept_words == 0:
            keepable = True
        if keepable and kept_words <= _REDACT_MAX_SUBCOMMANDS:
            out.append(tok)
            kept_words += 1
            redacting = False
        elif not redacting:
            out.append("…[redacted]")
            redacting = True
        # else: already redacting this segment → collapse into the one marker
    return " ".join(out)


def _entry(payload: dict, reason: str, redact: bool, now: float) -> dict:
    tool = payload.get("tool_name", "")
    command = ""
    if tool == "Bash":
        command = str(payload.get("tool_input", {}).get("command", ""))
        if redact:
            command = _redact(command)
    return {
        "ts": int(now),
        "subject": _subject(payload),
        "tool": tool,
        "command": command,
        "reason": reason,
    }


def _subject(payload: dict) -> str:
    agent = payload.get("agent_type")
    return f"agent:{agent}" if agent else "operator"


def _append_capped(path: Path, entry: dict, max_entries: int) -> None:
    """Append one JSONL record, then enforce the size cap by dropping oldest
    lines. Drop-oldest is a read-rewrite of the file — fine at the bounded sizes
    a diagnostic session produces, and keeps the format a plain appendable JSONL.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    if max_entries <= 0:
        return
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) > max_entries:
        kept = lines[-max_entries:]
        path.write_text("\n".join(kept) + "\n", encoding="utf-8")


def capture(root: str, payload: dict, decision: str, reason: str) -> None:
    """Append a redacted record for a DEFERRED (abstain) decision, but only while
    a diagnostic session is armed and unexpired. A no-op otherwise.

    Inert-on-failure (PRJ-006 sub-decision 2): the whole body is guarded so any
    exception becomes a silent no-op. This is called AFTER the decision is fixed,
    so it can never change a verdict; the guard ensures it can never break the
    hook either. The hook also wraps this call in its own try/except.
    """
    try:
        if decision != "abstain":
            return  # we capture only the deferred/prompted verdict
        root_path = Path(root)
        marker = _read_marker(root_path)
        if marker is None:
            return
        now = time.time()
        if not _armed(marker, now):
            return
        redact = marker.get("redact", _DEFAULT_REDACT)
        max_entries = marker.get("max_entries", _DEFAULT_MAX_ENTRIES)
        if not isinstance(max_entries, int):
            max_entries = _DEFAULT_MAX_ENTRIES
        entry = _entry(payload, reason, bool(redact), now)
        _append_capped(_log_path(root_path), entry, max_entries)
    except Exception:  # inert on ANY failure — never change a decision / break the hook
        if os.environ.get("PKIT_PERMISSIONS_DEBUG"):
            import sys
            import traceback
            print("pkit-permissions-diagnose: capture failed (inert):", file=sys.stderr)
            traceback.print_exc()
        return
