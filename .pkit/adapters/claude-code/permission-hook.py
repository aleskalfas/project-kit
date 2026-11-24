#!/usr/bin/env python3
"""Claude Code PreToolUse permission hook (per COR-028 / ADR-002 / ADR-003).

A propagated adapter script registered by `pkit permissions enable` via the
top-level `hooks` key in `.claude/settings.json`. On every matched tool call
Claude Code pipes a PreToolUse payload to this script's stdin; the script
decides via the shared, harness-neutral decision core
(`.pkit/permissions/decide.py`) and prints a `permissionDecision`, or abstains.
Where the core abstains on a call that may hide a form of a guardrail, or a
locked command behind a runner it cannot read, the hook asks the person
instead, except in auto or bypass mode, where the person chose not to be asked
(ADR-025 point 7). In every mode it gives the core's own verdicts on the locked
commands, a deny on naming a folder where it puts no ask and the interlock's
ask on a command that changes what judges later calls (ADR-095 point 3,
ADR-099 point 1); it asks before a shell call that asks to leave the sandbox
(ADR-095 point 4); and it asks on an Edit/Write to a foreign path.

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

Fail-OPEN (ADR-002), each judgement apart (ADR-095 point 4): a *decision*
fault — a malformed payload, a core or catalog that cannot load — drops only
what rests on it, never a silent block. A model that will not load leaves the
catalog's guardrail denies and the core's own verdicts; a core or catalog that
cannot load leaves the adapter's own asks. Where none stands, the hook abstains
(exit 0, no stdout). The non-negotiable guardrail denies, and the native locks
on the commands the core locks, are double-locked in the harness's fail-closed
native `settings.json` rules, so failing open here can never bypass them.

Enforcement-runtime faults (hook can't start at all) are a DISTINCT fault class
(ADR-002 point 4): they surface loudly via the startup self-check wired into
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


# The harness's tools that run a command: its shell tool, its PowerShell tool
# and its tool that monitors a command (ADR-095 point 3, "A shell call").
_SHELL_TOOLS = frozenset({"Bash", "PowerShell", "Monitor"})

# The session's permission modes in which the person chose not to be asked, as
# Claude Code's hook input names them in `permission_mode` (the hooks
# reference, "Common input fields"): auto mode and bypass mode. A hook's `ask`
# forces a prompt even there, so the hidden-guardrail ask defers in them.
_UNASKED_MODES = frozenset({"auto", "bypassPermissions"})


def _person_chose_not_to_be_asked(payload: object) -> bool:
    """Does the payload name auto mode or bypass mode? A missing field, a value
    of another type or a value not named above reads as False, so the hook
    keeps its ask: an unknown mode is never taken for an unattended one."""
    if not isinstance(payload, dict):
        return False
    mode = payload.get("permission_mode")
    return isinstance(mode, str) and mode in _UNASKED_MODES


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


def _sandbox_escape(payload: object) -> str | None:
    """The hook's ask before leaving the sandbox (ADR-095 point 4): a reason
    where a call of a tool that runs a command asks to run outside the sandbox,
    or where the hook cannot read whether it does; None otherwise, and for any
    other tool."""
    if not isinstance(payload, dict) or payload.get("tool_name") not in _SHELL_TOOLS:
        return None
    tool_input = payload.get("tool_input")
    flag = (
        tool_input.get("dangerouslyDisableSandbox", False) if isinstance(tool_input, dict) else None
    )
    if flag is False:
        return None
    asked = (
        "asks to run outside the sandbox"
        if flag is True
        else "may ask to run outside the sandbox, which the hook cannot read"
    )
    return (
        f"this shell call {asked}, where it can write what judges every later call, "
        f"in every project on this machine: confirm it in every mode (ADR-095 point 4)"
    )


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception as exc:  # malformed/empty stdin → fail open
        _debug(f"unreadable payload → abstain: {exc!r}")
        return 0

    # Each judgement runs on its own, so a fault in one drops neither the
    # others nor a model's verdict (ADR-095 point 4, "Apart from one
    # another"): a decision core that cannot be imported, a catalog or a model
    # that will not load, takes away only what rests on it. The adapter's own
    # asks below rest on none of them.
    decide = None
    catalog = None
    try:
        root = _target_root()
    except Exception as exc:  # no root → nothing to judge by
        _debug(f"project root fault → abstain: {exc!r}")
        return 0
    try:
        sys.path.insert(0, str(root / ".pkit" / "permissions"))
        import decide  # the shared decision core

        catalog = decide.load_catalog(str(root))
    except Exception as exc:  # no core or no catalog → the adapter's own asks alone
        _debug(f"decision core or catalog fault → no verdict of the core: {exc!r}")

    # The core's own verdicts, given with no model (ADR-095 point 3, ADR-099
    # point 1): a deny on a shell call it reads as naming a folder where the
    # hook puts no ask, the interlock's ask on one it reads as a command that
    # changes what judges later calls, and ADR-025 point 7's verdict where a
    # runner runs a command it cannot read that may be one of them.
    own = ("abstain", None, "", [])
    if decide is not None and catalog is not None:
        try:
            own = decide.hook_own_verdict(catalog, payload)
        except Exception as exc:  # a core that predates the locks → none of its own
            _debug(f"locked commands' check fault → no verdict of its own: {exc!r}")

    # The model's judgement, the guardrail denies among it. Where the model
    # will not load, the hook judges by the catalog's guardrails alone, so the
    # guardrail deny holds and nothing is allowed by a model it cannot read
    # (ADR-095 point 3, "When the checkout's model fails").
    model = None
    decision, reason = "abstain", "no decision core"
    if decide is not None and catalog is not None:
        try:
            model = decide.load_model(str(root), catalog)
        except Exception as exc:
            _debug(f"model will not load → the guardrails alone: {exc!r}")
        try:
            if model is None:
                model = {"posture": "lenient", "grants": decide.guardrail_denies(catalog)}
            decision, reason = decide.hook_decide(model, catalog, payload, project_root=str(root))
        except Exception as exc:  # any decision fault → fail open
            _debug(f"decision fault → abstain: {exc!r}")
            model, decision, reason = None, "abstain", "decision fault"

    # The stricter verdict stands: deny, then the interlock's ask, which
    # holds in every mode, then abstain, then allow (ADR-095 point 3). The
    # runner's verdict is an abstain the adapter asks on below.
    own_verdict, own_kind, own_reason, _ = own
    if own_verdict == "deny":
        decision, reason = "deny", own_reason
    elif own_verdict == "ask" and decision != "deny":
        decision, reason = "ask", own_reason
    elif own_kind == "runner" and decision == "allow":
        decision, reason = "abstain", own_reason

    # Diagnostic capture (PRJ-006 sub-decision 2): AFTER the decision is computed,
    # gated on the deferred (abstain) verdict inside `capture`, and fail-safe-
    # wrapped so a capture fault can NEVER change the decision or break fail-open.
    # The decision core (`decide.py`) above stays PURE — capture is a harness-side
    # side-effect only. While a diagnostic session is off (the default), `capture`
    # is one cheap marker read and a no-op; while armed it appends a redacted,
    # size-capped log entry. `diagnose_capture` carries its own internal guard
    # (the first belt); this try is the second.
    if decide is not None:
        try:
            import diagnose_capture  # propagated beside decide.py, on sys.path above

            diagnose_capture.capture(str(root), payload, decision, reason)
        except Exception as exc:  # inert: capture must never affect enforcement
            _debug(f"diagnostic capture fault (inert): {exc!r}")

    # A guardrail or a locked command the core cannot rule out (ADR-025 point
    # 7, #1982, #1990): where the core abstained on a Bash call that may hide a
    # form of a guardrail, such as `git push origin --forc[e]`, git
    # configuration the call sets, or a command a runner runs that the core
    # cannot read, Claude Code's own rules, such as the baseline's
    # `Bash(git:*)` or `Bash(find:*)`, would run it unasked. So the hook asks
    # the person, and so it does where a runner the core cannot read may run a
    # locked command, through any tool that runs a command. A strict posture
    # has denied a guardrail's such call already. The reason names the
    # guardrails or the locks and the kinds of form, never the command's text.
    # A fault keeps the abstain. The `pkit permissions probe` drives
    # `hook_decide` alone, so it reports the abstain.
    # In auto or bypass mode the person chose not to be asked, and a hook's
    # ask would prompt them all the same, so the hook defers there and the
    # harness's own mode decides (#2004); the call is then the core's abstain,
    # so the asks that follow an abstain still apply (ADR-095 point 2). It
    # reads the mode from the payload alone, and a missing or unknown mode
    # keeps the ask. The core's verdict is the same in every mode (ADR-002's
    # same-code invariant).
    if decision == "abstain" and decide is not None and catalog is not None:
        try:
            hidden = {}
            if isinstance(payload, dict) and payload.get("tool_name") == "Bash" and model:
                hidden = decide.hook_hidden_guardrails(
                    model, catalog, payload, project_root=str(root)
                )
            locked = own_reason if own_kind == "runner" else ""
            if (hidden or locked) and _person_chose_not_to_be_asked(payload):
                _debug(
                    f"hidden guardrail {sorted(hidden)} or locked command in "
                    f"{payload['permission_mode']} mode → defer, not ask"
                )
            elif hidden:
                kinds = " / ".join(sorted({kind for found in hidden.values() for kind in found}))
                decision, reason = (
                    "ask",
                    f"the guardrail {sorted(hidden)} may bind on what the shell runs ({kinds}), "
                    f"which the permission code cannot see: confirm the command "
                    f"(ADR-025 point 7: the core defers, and the harness's own rules may allow it)",
                )
            elif locked:
                decision, reason = "ask", locked
        except Exception as exc:  # the ask must never break fail-open
            _debug(f"hidden-guardrail check fault → ignore: {exc!r}")

    # The ask before leaving the sandbox (ADR-095 point 4): a shell call that
    # asks to run outside the sandbox, or whose request the hook cannot read,
    # can write what judges every later call, so the hook asks in every mode,
    # whatever the model or the harness's own rules allow. Only a deny stands
    # above it.
    if decision != "deny":
        try:
            escape = _sandbox_escape(payload)
        except Exception as exc:  # the ask must never break fail-open
            _debug(f"sandbox-escape check fault → ignore: {exc!r}")
            escape = None
        if escape is not None:
            decision, reason = "ask", escape

    # Additive foreign-repo corner (ADR-034 point 2): when the decision core
    # abstained (deferred), an Edit/Write to an absolute foreign path is
    # upgraded to a PROMPT (`ask`) — the one honestly-inspectable cross-repo
    # corner at the intent layer. This never overrides an allow/deny from the
    # core (decide.py is authoritative for what it decides) and never denies —
    # it only asks. The self-guard in the mutating program (point 1) is the
    # lever; this is a small catch on the Edit/Write surface only. It asks in
    # every permission mode, auto and bypass mode included: it is the one
    # prompt at the project's boundary (#2004).
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
