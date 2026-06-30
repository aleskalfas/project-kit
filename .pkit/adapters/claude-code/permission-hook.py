#!/usr/bin/env python3
"""Claude Code PreToolUse permission hook (per COR-028 / ADR-002 / ADR-003).

A propagated adapter script registered by `pkit permissions enable` via the
top-level `hooks` key in `.claude/settings.json`. On every matched tool call
Claude Code pipes a PreToolUse payload to this script's stdin; the script
decides via the shared, harness-neutral decision core
(`.pkit/permissions/decide.py`) and prints a `permissionDecision`, or abstains.

Runtime: bare system `python3` — NO uv, no PEP-723 metadata, no third-party
deps at startup. Running under bare python3 is required so the hook can start
inside macOS Seatbelt, where uv panics on the fixed SCDynamicStore denial
(ADR-014). The shared `decide.py` loader handles ruamel.yaml when available,
falling back to a stdlib-only YAML-subset parser when not (ADR-014 pt.1).

Same-code invariant (ADR-002): this hook and the `pkit permissions` CLI must
decide identically. The mechanism is ADR-003's code-home + dependency direction
— both import the *same* in-tree `decide.py` and build the model via the *same*
`load_model` / `load_yaml`, so they can never diverge. The stdlib fallback lives
in the SHARED loader (decide.py), not here, for exactly this reason.

Fail-OPEN (ADR-002): any *decision* fault — unreadable model, malformed payload
— yields a silent abstain (exit 0, no stdout), never a silent block. The
non-negotiable guardrail denies are double-locked in the harness's fail-closed
native `settings.json` denies, so failing open here can never bypass them.

Enforcement-runtime faults (hook can't start at all) are a DISTINCT fault class
(ADR-002 amendment): they surface loudly via the startup self-check wired into
`pkit permissions enable` and `pkit permissions sandbox enable` — not via this
hook itself, which never runs when its runtime is dead.

Set PKIT_PERMISSIONS_DEBUG=1 to surface decision fault reasons on stderr
(otherwise a broken config degrades to a silent no-op).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _debug(msg: str) -> None:
    if os.environ.get("PKIT_PERMISSIONS_DEBUG"):
        print(f"pkit-permissions-hook: {msg}", file=sys.stderr)


def _target_root() -> Path:
    # Prefer the harness's own contract for the project location; fall back to
    # this script's known position at <root>/.pkit/adapters/claude-code/.
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[3]


def _foreign_edit_write_prompt(payload: dict) -> str | None:
    """The one honest intent-layer catch (ADR-034 point 2): an Edit/Write whose
    target file path is an ABSOLUTE path OUTSIDE the session anchor's tree.

    Edit/Write carry the literal target path in `tool_input` (unlike a bash
    command, whose target is buried in argv the dumb segmenter does not parse —
    ADR-025), so this one tool surface is honestly inspectable. Returns a reason
    string when the path is foreign (the caller emits an `ask`/prompt), or None
    when it is in-tree, relative, anchor-undetermined, or not an Edit/Write.

    This is a small catch on the Edit/Write surface only — it is explicitly NOT
    the foreign-repo lever (that is the pkit self-guard in the mutating program,
    which covers bash / uv / gh). It does not DENY — only PROMPTs — and it never
    touches decide.py's bash-path decision core (ADR-034 point 6).

    Honest residual gap: when CLAUDE_PROJECT_DIR is unset the anchor cannot be
    determined, so this corner does not fire (it does not claim coverage it
    cannot back). A relative path is left to the harness's normal cwd-relative
    handling.
    """
    tool = payload.get("tool_name")
    if tool not in ("Edit", "Write"):
        return None
    anchor_env = os.environ.get("CLAUDE_PROJECT_DIR")
    if not anchor_env:
        return None  # residual gap: no anchor → cannot compare → do not fire.
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    raw_path = tool_input.get("file_path") or tool_input.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        return None
    target = Path(raw_path)
    if not target.is_absolute():
        return None  # relative paths resolve under cwd — left to normal flow.
    try:
        anchor = Path(anchor_env).resolve()
        resolved = target.resolve()
    except OSError:
        return None
    if resolved == anchor or anchor in resolved.parents:
        return None  # in-tree — no prompt.
    return (
        f"Edit/Write targets an absolute path outside this session's repo "
        f"(anchor: {anchor}; target: {resolved}). Confirm this cross-repo "
        f"write is intended (COR-039 / ADR-034 interlock against accidental "
        f"cross-repo handoff — a prompt, not a wall)."
    )


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception as exc:  # malformed/empty stdin → fail open
        _debug(f"unreadable payload → abstain: {exc!r}")
        return 0

    try:
        root = _target_root()
        sys.path.insert(0, str(root / ".pkit" / "permissions"))
        import decide  # the shared decision core

        catalog = decide.load_catalog(str(root))
        model = decide.load_model(str(root), catalog)
        decision, reason = decide.hook_decide(model, catalog, payload, project_root=str(root))
    except Exception as exc:  # any load/decision fault → fail open
        _debug(f"decision fault → abstain: {exc!r}")
        return 0

    # Diagnostic capture (PRJ-006 sub-decision 2): AFTER the decision is computed,
    # gated on the deferred (abstain) verdict inside `capture`, and fail-safe-
    # wrapped so a capture fault can NEVER change the decision or break fail-open.
    # The decision core (`decide.py`) above stays PURE — capture is a harness-side
    # side-effect only. While a diagnostic session is off (the default), `capture`
    # is one cheap marker read and a no-op; while armed it appends a redacted,
    # size-capped log entry. `diagnose_capture` carries its own internal guard
    # (the first belt); this try is the second.
    try:
        import diagnose_capture  # propagated beside decide.py, on sys.path above

        diagnose_capture.capture(str(root), payload, decision, reason)
    except Exception as exc:  # inert: capture must never affect enforcement
        _debug(f"diagnostic capture fault (inert): {exc!r}")

    # Additive foreign-repo corner (ADR-034 point 2): when the decision core
    # abstained (deferred), an Edit/Write to an absolute foreign path is
    # upgraded to a PROMPT (`ask`) — the one honestly-inspectable cross-repo
    # corner at the intent layer. This never overrides an allow/deny from the
    # core (decide.py is authoritative for what it decides) and never denies —
    # it only asks. The self-guard in the mutating program (point 1) is the
    # lever; this is a small catch on the Edit/Write surface only.
    if decision == "abstain":
        try:
            foreign_reason = _foreign_edit_write_prompt(payload)
        except Exception as exc:  # additive corner must never break fail-open
            _debug(f"foreign-path check fault → ignore: {exc!r}")
            foreign_reason = None
        if foreign_reason is not None:
            decision, reason = "ask", foreign_reason

    if decision in ("allow", "deny", "ask"):
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": decision,
                        "permissionDecisionReason": reason,
                    }
                }
            )
        )
    # abstain → exit 0 with no stdout: defer to the harness's normal flow.
    return 0


if __name__ == "__main__":
    sys.exit(main())
