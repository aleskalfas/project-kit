#!/usr/bin/env bash
# demo-cli-recorder/run-storyboard.sh — drive a CLI demo from its markdown
# storyboard file.  No separate driver script needed; the storyboard IS
# the executable form.
#
# Usage:
#   run-storyboard.sh <path-to-storyboard.md>             # run the demo
#   run-storyboard.sh <path-to-storyboard.md> --validate  # parse-and-print
#
# The storyboard format is documented in
#   demo-cli-recorder/storyboards/README.md
# (H1 title + ## Step N headings + fenced directive blocks).
#
# Architecture:
#   storyboards/runner.py emits tab-separated dispatch lines on stdout
#   (one action per line, fields tab-separated).  This script reads them
#   on FD 3 (so stdin stays connected to the terminal for lib.sh's
#   read-Enter prompts) and dispatches each to the corresponding lib.sh
#   helper.
#
# Action vocabulary emitted by runner.py:
#   wait_for_focus  <hint>   <verb>  — (compat shim) re-assert focus + sleep
#   narrate_wipe_run <text>  <cmd>   — type narration, wipe, run command
#   select_pane     <N>              — send C-b q N to tmux
#   narrate         <text>           — type text + Enter
#   shell_run       <text>           — type text + Enter (bash command)
#   wait_only       <message>        — pure operator-coordination pause
#   ready_wait      <pattern> <to>   — poll RECORDING text for pattern (timeout)
#   send_key        <chord>          — send one modifier-key chord via osascript
#   sleep_pause     <seconds>        — fixed wall-clock pause with countdown
#   warn_unknown_directive <lang>    — print warning, continue

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "${SCRIPT_DIR}/plugins/recording/lib.sh"
# The single platform gate (Layer 3), per
# [demo-recording:DEC-004-platform-coupling-and-gate-placement]. Sourced
# here (lib.sh runs no macOS commands at load); CALLED only on the run
# path below, after the --validate short-circuit, so validation stays
# platform-neutral.
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/plugins/recording/platform-guard.sh"

if [[ $# -lt 1 ]]; then
    echo "run-storyboard: missing storyboard path" >&2
    echo "  usage: $(basename "$0") <storyboard.md> [--validate]" >&2
    exit 2
fi

STORYBOARD="$1"
VALIDATE=0
shift
while [[ $# -gt 0 ]]; do
    case "$1" in
        --validate) VALIDATE=1; shift ;;
        --help|-h)
            sed -n '3,/^set -euo/p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//;/^set -euo/d'
            exit 0
            ;;
        *) echo "run-storyboard: unknown flag '$1'" >&2; exit 2 ;;
    esac
done

if [[ ! -f "$STORYBOARD" ]]; then
    echo "run-storyboard: storyboard not found: $STORYBOARD" >&2
    exit 1
fi

RUNNER="${SCRIPT_DIR}/storyboards/runner.py"

if (( VALIDATE )); then
    exec python3 "$RUNNER" "$STORYBOARD" --validate
fi

# Run mode drives keystrokes via lib.sh (osascript / System Events) —
# macOS-only.  Gate per DEC-004 (validate above is platform-neutral).
dcr_require_macos || exit 1

# Run mode: parse + plugin dispatch, then drive each action via lib.sh.
# Capture runner output in memory before iterating so the runner can
# return a clean exit code (and so the loop body's stdin stays connected
# to the terminal — lib.sh helpers use `read -p` to wait for operator Enter).
if ! parsed=$(python3 "$RUNNER" "$STORYBOARD"); then
    echo "run-storyboard: storyboard has errors (run with --validate for details)" >&2
    exit 1
fi

# Loop on FD 3 so stdin remains the controlling terminal.
#
# `set -e` is disabled for the loop body so a single action's nonzero
# return (e.g. ready_wait timeout) doesn't silently kill the whole
# storyboard.  Each action's exit code is logged via _dcr_log so a
# post-mortem can see exactly where things went wrong.  Re-enabled
# after the loop.
set +e
_action_idx=0
while IFS=$'\t' read -r -u 3 action arg1 arg2; do
    _action_idx=$((_action_idx + 1))
    _dcr_log "dispatch[$_action_idx] action=$action arg1_len=${#arg1} arg2='${arg2:-}'"
    case "$action" in
        wait_for_focus)
            wait_for_focus "$arg1" "${arg2:-}"
            ;;
        narrate_wipe_run)
            type_narrate_wipe_run "$arg1" "$arg2"
            ;;
        select_pane)
            select_tmux_pane "$arg1"
            ;;
        narrate)
            type_narration "$arg1"
            ;;
        shell_run)
            type_narration "$arg1"
            ;;
        wait_only)
            wait_only "$arg1"
            ;;
        ready_wait)
            ready_wait "$arg1" "${arg2:-30}"
            ;;
        send_key)
            send_key "$arg1"
            ;;
        sleep_pause)
            sleep_pause "$arg1"
            ;;
        warn_unknown_directive)
            echo "  ⚠ storyboard contains unknown directive '${arg1:-}' — skipping" >&2
            ;;
        "")
            ;;  # blank line from runner — skip
        *)
            echo "run-storyboard: unknown action '$action'" >&2
            _dcr_log "dispatch[$_action_idx] UNKNOWN_ACTION='$action' — exiting"
            exit 1
            ;;
    esac
    _exit=$?
    _dcr_log "dispatch[$_action_idx] action=$action exit=$_exit"
done 3<<<"$parsed"
set -e

echo
echo "=== Storyboard complete ===" >&2
