#!/usr/bin/env bash
# _session.sh — orchestrate one demo session inside the CONTROL window.
#
# This script is what record.sh dispatches into CONTROL (instead of
# calling run-storyboard.sh directly).  It owns the recording lifecycle
# for the duration of one session:
#
#   1. Sets a SIGINT trap so Ctrl-C anywhere stops the recording
#      cleanly (instead of leaving screencapture running in the background).
#   2. Prompts the operator to press Enter before recording starts, so
#      the .mov doesn't capture the windows-opening choreography.
#   3. Starts screen capture (after the Enter) + writes the state file
#      that record.sh stop uses to find the screencapture PID.
#   4. Runs the storyboard.
#   5. Runs post-demo.sh (the one-keypress stop prompt).
#
# Usage:
#   _session.sh <storyboard.md> [--rect <x,y,w,h> --output <path>]
#
# --rect + --output trigger the recording flow; without them, the
# storyboard runs without recording (matches record.sh --no-recording).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_FILE="${TMPDIR:-/tmp}/dcr-recording.state"

# Source lib.sh for focus_recording_window — used once at session
# start, then we trust the operator with focus state thereafter.
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib.sh"
_dcr_log "_session.sh start argv: $*"

if [[ $# -lt 1 ]]; then
    echo "_session.sh: usage: $0 <storyboard.md> [--rect <x,y,w,h> --output <path>]" >&2
    exit 2
fi

STORYBOARD="$1"
shift

RECT=""
OUTPUT=""
CONFIG=""
INTERACTIVE=0   # default: autonomous — skip the start/stop Enter gates.
while [[ $# -gt 0 ]]; do
    case "$1" in
        --rect)        RECT="$2";   shift 2 ;;
        --output)      OUTPUT="$2"; shift 2 ;;
        --config)      CONFIG="$2"; shift 2 ;;
        --interactive) INTERACTIVE=1; shift ;;
        *) echo "_session.sh: unknown arg: $1" >&2; exit 2 ;;
    esac
done

WANT_RECORDING=0
if [[ -n "$RECT" && -n "$OUTPUT" ]]; then
    WANT_RECORDING=1
fi

# SIGINT cleanup — fires on any Ctrl-C inside this session.  record.sh
# stop is a silent no-op if no recording was started yet, so this is
# safe to set before the prompt.
on_interrupt() {
    echo  # newline after the ^C
    if [[ -f "$STATE_FILE" ]]; then
        echo "Ctrl-C — stopping recording..."
        "$SCRIPT_DIR/../../record.sh" stop || true
    fi
    exit 130
}
trap on_interrupt INT

if (( WANT_RECORDING )); then
    echo
    if (( INTERACTIVE )); then
        read -r -p "Press Enter HERE to start recording and begin the storyboard.  Ctrl-C to abort. " _
    else
        echo "Autonomous mode (default): starting recording immediately.  Pass --interactive for the start Enter gate."
    fi

    # One-shot: bring the RECORDING iTerm window to the front so all
    # subsequent keystrokes (boot, pane select, narrate, etc.) land
    # there.  We do NOT re-focus between steps; if the operator clicks
    # into CONTROL to abort, they can Ctrl-C without us snatching
    # focus back.
    focus_recording_window

    # Try window-tracking capture first (screencapture -v -l <CGWindowID>)
    # if setup-windows.sh extracted the AXWindowID.  If that variant
    # isn't supported (process dies within 0.5s), fall back to fixed-
    # rect capture (-R<x,y,w,h>).
    AX_WIN_ID=""
    WIN_STATE_FILE="${TMPDIR:-/tmp}/dcr-windows.state"
    if [[ -f "$WIN_STATE_FILE" ]]; then
        # shellcheck disable=SC1090
        source "$WIN_STATE_FILE"
    fi

    pid=""
    mode=""
    if [[ -n "$AX_WIN_ID" ]]; then
        SCRC_ERR="$(mktemp -t dcr-scrc.XXXXXX)"
        screencapture -v -l "$AX_WIN_ID" "$OUTPUT" 2>"$SCRC_ERR" &
        pid=$!
        sleep 0.5
        if kill -0 "$pid" 2>/dev/null; then
            mode="window (AXWindowID=$AX_WIN_ID)"
            rm -f "$SCRC_ERR"
        else
            echo "  ⚠ screencapture -v -l failed:" >&2
            cat "$SCRC_ERR" >&2
            echo "  ⚠ falling back to fixed-rect capture (don't cover RECORDING)." >&2
            rm -f "$SCRC_ERR"
            pid=""
        fi
    fi
    if [[ -z "$pid" ]]; then
        screencapture -v -R"$RECT" "$OUTPUT" &
        pid=$!
        sleep 0.5
        mode="rect ($RECT)"
    fi

    cat > "$STATE_FILE" <<STATE
PID=$pid
OUTPUT=$OUTPUT
DEMO=$(basename "${STORYBOARD%.md}")
STORYBOARD=$STORYBOARD
CONFIG=$CONFIG
STARTED=$(date +%Y-%m-%dT%H%M%S)
STATE
    echo "Recording started [$mode] → $OUTPUT (PID $pid)"
    _dcr_log "screencapture started mode=$mode pid=$pid output=$OUTPUT"
fi

_dcr_log "dispatching run-storyboard.sh"
"$SCRIPT_DIR/../../run-storyboard.sh" "$STORYBOARD"
_dcr_log "run-storyboard.sh returned exit=$?"

if (( WANT_RECORDING )); then
    _dcr_log "dispatching post-demo.sh (interactive=${INTERACTIVE})"
    if (( INTERACTIVE )); then
        "$SCRIPT_DIR/post-demo.sh" --interactive
    else
        "$SCRIPT_DIR/post-demo.sh"
    fi
    _dcr_log "post-demo.sh returned exit=$?"
fi
