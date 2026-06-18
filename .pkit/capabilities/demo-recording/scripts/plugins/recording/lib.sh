#!/usr/bin/env bash
# demo-cli-recorder/lib.sh — primitives for driving CLI demo recordings.
#
# Generic typing-into-focused-pane helpers for screen-recorded terminal
# demos.  Project-agnostic — knows nothing about IGW, tmux topologies,
# or which apps are being recorded.  Project layers (e.g. IGW's
# storyboards/) source this and add their own narration / step
# sequences on top.
#
# Source from a sibling .sh script via:
#     source "<path-to>/demo-cli-recorder/lib.sh"
#
# Public API:
#   type_text "..."               — type at human pace into the focused pane
#   press_enter                   — send a Return keystroke
#   press_ctrl_u                  — wipe the current line (Ctrl-U)
#   type_narration "..."          — type text + Enter (no wipe), for panes
#                                   that accumulate (chat input, comments,
#                                   thoughts panel)
#   type_narrate_wipe_run "N" "C" — type narration N, wipe with Ctrl-U,
#                                   type command C, submit.  Shell-prompt
#                                   pattern for the audience to "read" the
#                                   narration before the real command runs.
#   wait_for_focus PANE [HINT]    — prompt the operator to focus a pane,
#                                   wait for their Enter in the controlling
#                                   terminal, then sleep FOCUS_DELAY before
#                                   typing resumes
#   wait_only PROMPT              — pure pause; no typing
#
# macOS-only (uses osascript → System Events for keystroke injection).
# First-time use requires Accessibility permission for the controlling
# terminal in System Settings → Privacy & Security → Accessibility.
#
# Tunables (override via env BEFORE sourcing):
#   FOCUS_DELAY    seconds between Enter-here and typing-starts   (default 3)
#   MIN_MS         min ms between typing chunks                    (default 15)
#   MAX_MS         max ms between typing chunks                    (default 40)
#   CHUNK_SIZE     chars per osascript call (higher = faster)      (default 4)
#   REVIEW_PAUSE   seconds the narration sits before being wiped   (default 0.6)
#   PRE_RUN_PAUSE  seconds between Ctrl-U and command typing       (default 0.2)

# Guard against double-sourcing.
if [[ -n "${_DCR_LIB_LOADED:-}" ]]; then
    return 0
fi
_DCR_LIB_LOADED=1

FOCUS_DELAY="${FOCUS_DELAY:-3}"
MIN_MS="${MIN_MS:-15}"
MAX_MS="${MAX_MS:-40}"
CHUNK_SIZE="${CHUNK_SIZE:-4}"
REVIEW_PAUSE="${REVIEW_PAUSE:-0.6}"
PRE_RUN_PAUSE="${PRE_RUN_PAUSE:-0.2}"

# --- Diagnostic logging ------------------------------------------------------
#
# When DCR_LOG is set to a file path, every instrumented function appends a
# tab-separated record of what it just did.  No effect on behavior — purely
# observational.  Intended for diagnosing "the take did X but I don't know
# why" cases without resorting to bash -x (which fires real osascript
# keystrokes and snatches focus).
#
# Usage:
#   DCR_LOG=/tmp/dcr.log ./demo/<bundle>/record.sh human
#   tail -f /tmp/dcr.log   # in another terminal during the take
#
# DCR_DEBUG=1 is a shortcut that sets DCR_LOG=${TMPDIR}/dcr-debug.log if
# DCR_LOG itself isn't set.  Both record.sh and _session.sh honor it; lib.sh
# functions check the resolved DCR_LOG path.
if [[ -z "${DCR_LOG:-}" && "${DCR_DEBUG:-0}" == "1" ]]; then
    DCR_LOG="${TMPDIR:-/tmp}/dcr-debug.log"
fi

_dcr_log() {
    [[ -n "${DCR_LOG:-}" ]] || return 0
    # Subsecond timestamps where possible; fall back to second resolution.
    local ts
    ts=$(date +%Y-%m-%dT%H:%M:%S 2>/dev/null) || ts="?"
    printf '%s\t[%s]\t%s\n' "$ts" "${BASH_SOURCE[1]##*/}:${BASH_LINENO[0]}" "$*" >> "$DCR_LOG"
}

# --- Primitive: typing one chunk at a time -----------------------------------

type_text() {
    local text="$1"
    local len=${#text}
    _dcr_log "type_text begin len=$len preview=$(printf '%.40s' "$text")…"
    local i chunk esc ms
    for ((i = 0; i < len; i += CHUNK_SIZE)); do
        chunk="${text:$i:$CHUNK_SIZE}"
        # AppleScript string-literal escaping: backslash and double-quote.
        esc="${chunk//\\/\\\\}"
        esc="${esc//\"/\\\"}"
        osascript -e "tell application \"System Events\" to keystroke \"$esc\""
        ms=$(( MIN_MS + RANDOM % (MAX_MS - MIN_MS + 1) ))
        # Occasional post-space "thinking" pause for human-like cadence.
        if [[ "${chunk: -1}" == " " ]] && (( RANDOM % 10 == 0 )); then
            ms=$(( ms + 70 + RANDOM % 100 ))
        fi
        sleep "$(awk -v m="$ms" 'BEGIN { printf "%.3f", m/1000 }')"
    done
    _dcr_log "type_text end"
}

press_enter() {
    osascript -e 'tell application "System Events" to key code 36'
}

press_ctrl_u() {
    osascript -e 'tell application "System Events" to keystroke "u" using control down'
}

# Send one modifier-key chord to whatever has focus.  Spec is one of:
#
#   ctrl+b          modifier+key
#   cmd+shift+t     multiple modifiers chain with +
#   Enter           bare key name → emits the corresponding key code
#   k               single character → plain keystroke
#
# Recognised modifiers: ctrl/control, alt/option, cmd/command, shift.
# Recognised key names: Enter/Return, Escape/Esc, Tab.
#
# Used by the storyboard's `keys` directive.  Trails with a 0.2s sleep so
# back-to-back chords aren't coalesced by the receiving app.
send_key() {
    local spec="$1"
    [[ -z "$spec" ]] && return 0

    local key="$spec"
    local using=""
    if [[ "$spec" == *+* ]]; then
        local mod_part="${spec%+*}"
        key="${spec##*+}"
        local using_parts=()
        local IFS_OLD="$IFS"
        IFS='+'
        local mods=($mod_part)
        IFS="$IFS_OLD"
        local m
        for m in "${mods[@]}"; do
            local m_lower
            m_lower=$(echo "$m" | tr '[:upper:]' '[:lower:]')
            case "$m_lower" in
                ctrl|control) using_parts+=("control down") ;;
                alt|option)   using_parts+=("option down")  ;;
                cmd|command)  using_parts+=("command down") ;;
                shift)        using_parts+=("shift down")   ;;
                *) echo "  ⚠ send_key: unknown modifier '$m' in '$spec'" >&2 ;;
            esac
        done
        if [[ ${#using_parts[@]} -gt 0 ]]; then
            local joined
            joined=$(IFS=, ; echo "${using_parts[*]}")
            using=" using {${joined}}"
        fi
    fi

    local key_lower
    key_lower=$(echo "$key" | tr '[:upper:]' '[:lower:]')
    case "$key_lower" in
        enter|return) osascript -e "tell application \"System Events\" to key code 36${using}" ;;
        escape|esc)   osascript -e "tell application \"System Events\" to key code 53${using}" ;;
        tab)          osascript -e "tell application \"System Events\" to key code 48${using}" ;;
        *)
            # AppleScript string-literal escaping for the key character.
            local esc="${key//\\/\\\\}"
            esc="${esc//\"/\\\"}"
            osascript -e "tell application \"System Events\" to keystroke \"$esc\"${using}"
            ;;
    esac
    sleep 0.2
}

# --- Composed actions --------------------------------------------------------

# Type the text and submit with Enter.  No wipe.
# Use for panes that accumulate text (thoughts panel, chat input,
# bash where the typed text IS the command you want to run).
#
# NOTE: assumes RECORDING is the frontmost app.  We trust focus state
# instead of re-asserting it, so the operator can switch to CONTROL
# mid-take (e.g. to Ctrl-C and abort) without us snatching focus back.
type_narration() {
    local text="$1"
    type_text "$text"
    press_enter
}

# Shell-prompt narration pattern:
#   1. Type the narration (so the audience can read the spoken story).
#   2. Pause briefly so they can finish reading.
#   3. Ctrl-U wipes the line.
#   4. Type the actual command and submit.
#
# Same focus contract as type_narration.
type_narrate_wipe_run() {
    local narration="$1"
    local command="$2"
    type_text "$narration"
    sleep "$REVIEW_PAUSE"
    press_ctrl_u
    sleep "$PRE_RUN_PAUSE"
    type_text "$command"
    press_enter
}

# --- User-coordination prompts in the controlling terminal -------------------

# Bring the RECORDING iTerm window to the front so keystrokes land there.
# Looks up the window by id (captured by setup-windows.sh into the state
# file).  Falls back to manual focus with a visible warning if the state
# file is missing or the lookup fails — silent no-ops are how the last
# version landed typing into CONTROL.
focus_recording_window() {
    _dcr_log "focus_recording_window begin"
    local state_file="${TMPDIR:-/tmp}/dcr-windows.state"
    if [[ ! -f "$state_file" ]]; then
        _dcr_log "focus_recording_window NO_STATE_FILE"
        echo "  ⚠ no window-state file at $state_file — click the RECORDING window manually." >&2
        return 0
    fi
    # shellcheck disable=SC1090
    source "$state_file"
    if [[ -z "${REC_WIN_ID:-}" ]]; then
        _dcr_log "focus_recording_window NO_REC_WIN_ID"
        echo "  ⚠ window-state missing REC_WIN_ID — click the RECORDING window manually." >&2
        return 0
    fi
    local err
    err=$(osascript 2>&1 <<APPLESCRIPT
tell application "iTerm"
    activate
    repeat with w in windows
        if (id of w as text) is "${REC_WIN_ID}" then
            select w
            return "ok"
        end if
    end repeat
    return "no-match"
end tell
APPLESCRIPT
)
    if [[ "$err" != "ok" ]]; then
        _dcr_log "focus_recording_window FAILED id=$REC_WIN_ID result=$err"
        echo "  ⚠ failed to raise RECORDING window (id=$REC_WIN_ID): $err" >&2
    else
        _dcr_log "focus_recording_window OK id=$REC_WIN_ID"
    fi
    # osascript returns before macOS finishes the visual window-raise.
    # Wait a beat so subsequent keystrokes land in RECORDING, not CONTROL.
    sleep 0.3
}

# Select tmux pane N inside the RECORDING window by sending Ctrl-b q <N>.
# This is the numeric-pane-select binding (show-pane-numbers → type the number
# to focus it).  After selection, a brief sleep lets tmux register the switch
# before keystroke injection begins.
#
# Usage:
#   select_tmux_pane 3     # switch to tmux pane index 3
#
# Requires:
#   - The RECORDING window must be frontmost (call focus_recording_window first
#     or use select_tmux_pane after wait_for_focus so the window is already up).
#   - Accessibility permission for the running terminal app.
select_tmux_pane() {
    local pane_num="$1"
    _dcr_log "select_tmux_pane N=$pane_num"
    # Uses IGW's custom Ctrl-b <N> binding (layouts.py:1062-1067) which
    # maps Ctrl-b 1 → tmux pane index 0 (P1), Ctrl-b 2 → index 1 (P2), …
    # This is 1-based and matches the P-labels in pane titles, so a
    # `panes: { shell: 1 }` declaration in a storyboard targets the
    # pane displayed as P1.
    #
    # NOTE: requires the RECORDING iTerm window to be frontmost (the
    # keystroke goes to whatever app has focus).  _session.sh activates
    # it once at the start of a take; we trust focus thereafter to
    # leave the operator able to switch to CONTROL and Ctrl-C if they
    # want to abort.
    osascript <<APPLESCRIPT
tell application "System Events"
    key code 11 using control down   -- Ctrl-b (tmux prefix)
    delay 0.1
    keystroke "${pane_num}"          -- maps to IGW's "select pane N" binding
end tell
APPLESCRIPT
    sleep 0.3
}

# wait_for_focus used to print a NEXT STEP box and block on operator
# Enter, then re-focus.  No directive currently emits it; kept only as
# a dispatch-handler shim so an unknown stale action doesn't error.
# Pure sleep — does NOT re-focus.  Focus is owned by _session.sh
# (one-shot at the start of a take) so the operator can switch to
# CONTROL freely to abort.
wait_for_focus() {
    sleep "$FOCUS_DELAY"
}

wait_only() {
    local prompt="$1"
    echo "" >&2
    echo "  ┌─ WAIT" >&2
    echo "  │  $prompt" >&2
    echo "  └─" >&2
    read -r -p "  Press Enter HERE when ready to continue. " _
    # The operator just pressed Enter in CONTROL — focus is on CONTROL
    # now.  Re-assert RECORDING before the next step's keystrokes fire
    # (otherwise they'd land in the wrong window).  This is the one
    # known focus-transition we explicitly handle, since `wait` is the
    # only directive that requires the operator to touch the keyboard
    # mid-take.
    focus_recording_window
}

# Fixed-duration pause — sleeps N seconds and advances.  Prints a
# one-line countdown so CONTROL doesn't look frozen.
sleep_pause() {
    local seconds="${1:-0}"
    if (( seconds <= 0 )); then
        return 0
    fi
    local remaining=$seconds
    while (( remaining > 0 )); do
        printf '\r  • sleep_pause: %ds remaining…' "$remaining" >&2
        sleep 1
        remaining=$((remaining - 1))
    done
    printf '\r  • sleep_pause: done (%ds elapsed).        \n' "$seconds" >&2
}

# Helper for ready_wait: capture the current contents of the RECORDING
# iTerm session.  Wrapped in a function (rather than inlined) because
# macOS ships bash 3.2 which mis-parses heredocs inside $(...) command
# substitution.
_dcr_recording_contents() {
    osascript 2>/dev/null <<APPLESCRIPT
tell application "iTerm"
    try
        repeat with w in windows
            if (id of w as text) is "${REC_WIN_ID}" then
                return contents of current session of w
            end if
        end repeat
    end try
    return ""
end tell
APPLESCRIPT
}

# Poll the RECORDING iTerm session's visible text for a given pattern,
# advancing once a NEW occurrence (beyond what was already visible
# when polling started) appears.  Counts occurrences with `grep -F -c`
# and waits for the count to strictly increase.
#
# Why "new occurrence" not "any occurrence"?  The chat directive types
# its request text into a pane just before `ready` runs.  If the
# pattern is something we asked the assistant to print (e.g. an
# explicit sentinel token), the request text itself contains the
# substring and "any occurrence" matches immediately.  By comparing
# against the initial count we wait for the *assistant's emission*,
# not our own request echo.
#
# Edge cases covered:
#   - Pattern not in the request (e.g. tmux's `HUMAN` status bar):
#       initial_count = 0, response brings it to 1 → match.
#   - Pattern is in the request (e.g. `STATS-READY` sentinel):
#       initial_count = 1, response brings it to 2 → match.
#   - Pattern from previous turn already in scrollback:
#       initial_count = N, current turn brings it to N+1 → match.
#
# Args:
#   $1 — pattern (literal substring, case-sensitive)
#   $2 — timeout in seconds (default 30)
#
# Exit code:
#   0 — count strictly increased within timeout
#   1 — timeout, or no window state file
ready_wait() {
    local pattern="$1"
    local timeout_s="${2:-30}"
    _dcr_log "ready_wait begin pattern='$pattern' timeout=$timeout_s"
    local state_file="${TMPDIR:-/tmp}/dcr-windows.state"
    if [[ ! -f "$state_file" ]]; then
        _dcr_log "ready_wait NO_STATE_FILE"
        echo "  ⚠ ready_wait: no window-state file at $state_file — can't poll RECORDING" >&2
        return 1
    fi
    # shellcheck disable=SC1090
    source "$state_file"
    if [[ -z "${REC_WIN_ID:-}" ]]; then
        _dcr_log "ready_wait NO_REC_WIN_ID"
        echo "  ⚠ ready_wait: REC_WIN_ID not set in $state_file" >&2
        return 1
    fi

    # Brief settle delay so any chat-request keystrokes that just fired
    # have time to fully render in the chat pane before we snapshot
    # the initial occurrence count.
    sleep 1
    # grep -F -c always prints a single number (including "0" on no
    # match) — so we DON'T add `|| echo 0`: that fallback fires when
    # grep exits 1 (= no matches), appending a second "0" to stdout
    # and giving us a "0\n0" multi-line string that breaks `((`
    # arithmetic.  Empty (only if grep itself fails to run) falls back
    # to 0 via the parameter expansion.
    local initial_count
    initial_count=$(_dcr_recording_contents | grep -F -c -- "$pattern" 2>/dev/null)
    initial_count=${initial_count:-0}
    _dcr_log "ready_wait initial_count=$initial_count"

    echo "  • waiting for NEW '${pattern}' occurrence (currently visible: ${initial_count}; timeout ${timeout_s}s)…" >&2
    local max_iter=$(( timeout_s * 2 ))
    local i=0
    local current_count
    while (( i < max_iter )); do
        current_count=$(_dcr_recording_contents | grep -F -c -- "$pattern" 2>/dev/null)
        current_count=${current_count:-0}
        # Log every 5th poll (~every 2.5s) to trace progress without spamming.
        if (( i % 5 == 0 )); then
            _dcr_log "ready_wait poll i=$i count=$current_count (initial=$initial_count)"
        fi
        if (( current_count > initial_count )); then
            _dcr_log "ready_wait MATCHED at i=$i (count $initial_count → $current_count)"
            echo "  • ready (after $(awk "BEGIN { printf \"%.1f\", $i * 0.5 }")s, occurrences ${initial_count} → ${current_count})" >&2
            return 0
        fi
        sleep 0.5
        i=$((i + 1))
    done

    _dcr_log "ready_wait TIMEOUT final_count=$current_count"

    echo "  ⚠ ready_wait: timeout after ${timeout_s}s — no new '$pattern' occurrence (stayed at ${initial_count})" >&2
    return 1
}
