#!/usr/bin/env bash
# demo-cli-recorder/setup-windows.sh — open two iTerm2 windows for a
# screen-recorded CLI demo, at fixed coordinates so video frames are
# consistent across re-takes.
#
# RECORDING window: visible in the video; the operator types here
#   (via the demo-driver script).
# CONTROL window:   off the recording region; the operator runs the
#   demo-driver script here and presses Enter to advance steps.
#
# Both windows cd to a project-specified directory and clear their
# screen, so the first thing the recording captures is a clean prompt.
#
# Tunables (env vars; iTerm bounds use macOS {left, top, right, bottom}
# pixel coordinates, NOT {x, y, w, h}):
#
#   DCR_RECORDING_LEFT     left edge of recording window     (default 50)
#   DCR_RECORDING_TOP      top edge                          (default 50)
#   DCR_RECORDING_RIGHT    right edge                        (default 1330)
#   DCR_RECORDING_BOTTOM   bottom edge                       (default 850)
#                          → defaults give an 1280×800 inner window
#
#   DCR_CONTROL_LEFT       left edge of control window       (default 50)
#   DCR_CONTROL_TOP        top edge                          (default 880)
#   DCR_CONTROL_RIGHT      right edge                        (default 750)
#   DCR_CONTROL_BOTTOM     bottom edge                       (default 1150)
#                          → defaults give a 700×270 small terminal
#                            below the recording window
#
#   DCR_CWD                cwd for both windows.  REQUIRED — no default.
#                          (Project-specific path, e.g. AUJ sandbox dir.)
#
#   DCR_FONT_SIZE          font size for the iTerm windows.  Default 18,
#                          which is comfortable for terminal demo videos
#                          (readable on phone screens, not too wasteful
#                          of horizontal space).  Recommend 16-20 for
#                          recording; 12-14 for everyday iTerm.
#   DCR_FONT_NAME          font family (Core Text PostScript name).
#                          Default "Menlo-Regular" (macOS-shipped monospace).
#
# Optional positional args (override the bounds env vars in one shot):
#   $1  recording bounds as "left,top,right,bottom"
#   $2  control bounds as "left,top,right,bottom"
#
# macOS only.  First run: macOS may prompt for Accessibility +
# automation permissions for the shell / Terminal / iTerm.

set -euo pipefail

# Optional positional bound overrides (comma-separated, 4 numbers each).
if [[ $# -ge 1 ]]; then
    IFS=, read -r DCR_RECORDING_LEFT DCR_RECORDING_TOP DCR_RECORDING_RIGHT DCR_RECORDING_BOTTOM <<<"$1"
fi
if [[ $# -ge 2 ]]; then
    IFS=, read -r DCR_CONTROL_LEFT DCR_CONTROL_TOP DCR_CONTROL_RIGHT DCR_CONTROL_BOTTOM <<<"$2"
fi

REC_L="${DCR_RECORDING_LEFT:-50}"
REC_T="${DCR_RECORDING_TOP:-50}"
REC_R="${DCR_RECORDING_RIGHT:-1330}"
REC_B="${DCR_RECORDING_BOTTOM:-850}"

CTRL_L="${DCR_CONTROL_LEFT:-50}"
CTRL_T="${DCR_CONTROL_TOP:-880}"
CTRL_R="${DCR_CONTROL_RIGHT:-750}"
CTRL_B="${DCR_CONTROL_BOTTOM:-1150}"

CWD="${DCR_CWD:-}"
if [[ -z "$CWD" ]]; then
    echo "setup-windows: DCR_CWD is required.  Set it to the project's working dir." >&2
    echo "  e.g. DCR_CWD=/path/to/project $0" >&2
    exit 2
fi
if [[ ! -d "$CWD" ]]; then
    echo "setup-windows: DCR_CWD does not exist: $CWD" >&2
    exit 1
fi

# Escape the cwd for AppleScript: single quotes don't need escaping inside
# AppleScript double-quoted strings, but the path could contain double quotes
# (rare but worth being safe).
CWD_ESC=$(printf '%s' "$CWD" | sed 's/"/\\"/g')

# ----------------------------------------------------------------------------
# iTerm dynamic profile — set font size for the recording windows.
#
# iTerm watches ~/Library/Application Support/iTerm2/DynamicProfiles/ for JSON
# files and reloads them live.  Writing a profile here lets us open windows
# with a specific font size WITHOUT touching the user's default profile
# (their everyday iTerm windows stay at whatever size they prefer).
#
# Fixed Guid so re-runs UPDATE the same profile rather than accumulating.
# Profile name "DCR Recording" — what `create window with profile "<name>"`
# matches against in the AppleScript below.
# ----------------------------------------------------------------------------

FONT_SIZE="${DCR_FONT_SIZE:-18}"
FONT_NAME="${DCR_FONT_NAME:-Menlo-Regular}"
ITERM_PROFILE_NAME="DCR Recording"
ITERM_PROFILE_GUID="A1B2C3D4-DCRR-DCRR-DCRR-DCRRDCRRDCRR"
ITERM_PROFILE_DIR="${HOME}/Library/Application Support/iTerm2/DynamicProfiles"
ITERM_PROFILE_FILE="${ITERM_PROFILE_DIR}/dcr-recording.json"

mkdir -p "$ITERM_PROFILE_DIR"
cat > "$ITERM_PROFILE_FILE" <<JSON
{
    "Profiles": [
        {
            "Name": "${ITERM_PROFILE_NAME}",
            "Guid": "${ITERM_PROFILE_GUID}",
            "Normal Font": "${FONT_NAME} ${FONT_SIZE}",
            "Non Ascii Font": "${FONT_NAME} ${FONT_SIZE}",
            "Use Non-ASCII Font": false
        }
    ]
}
JSON

# Brief sleep so iTerm's dynamic-profile reloader picks up the file before
# we ask it to open a window with that profile.  iTerm watches the directory
# but reload latency varies; 0.5s is plenty in practice.
sleep 0.5

# Wrapped in a function because macOS ships bash 3.2, which mis-parses
# heredocs inside $(...) command substitution.  Putting the heredoc
# inside a function body sidesteps the bug.
_create_windows() {
    osascript <<APPLESCRIPT
tell application "iTerm"
    activate

    -- RECORDING window — uses the dynamic "DCR Recording" profile we
    -- just wrote (font size from DCR_FONT_SIZE).  Falls back to the
    -- default profile if the dynamic one isn't visible yet (very rare).
    try
        set rec_window to (create window with profile "${ITERM_PROFILE_NAME}")
    on error
        set rec_window to (create window with default profile)
    end try
    delay 0.2
    set bounds of rec_window to {${REC_L}, ${REC_T}, ${REC_R}, ${REC_B}}
    tell current session of rec_window
        set name to "RECORDING"
        write text "cd \"${CWD_ESC}\" && clear"
    end tell

    -- CONTROL window — same dynamic profile, same big font so the
    -- operator can read it comfortably while driving the take.
    try
        set ctrl_window to (create window with profile "${ITERM_PROFILE_NAME}")
    on error
        set ctrl_window to (create window with default profile)
    end try
    delay 0.2
    set bounds of ctrl_window to {${CTRL_L}, ${CTRL_T}, ${CTRL_R}, ${CTRL_B}}
    tell current session of ctrl_window
        set name to "CONTROL"
        write text "cd \"${CWD_ESC}\" && clear"
    end tell

    -- Emit the window IDs so the parent shell can persist them for
    -- later focus-by-id lookups (lib.sh's focus_recording_window).
    set rec_id to id of rec_window
    set ctrl_id to id of ctrl_window
    return (rec_id as text) & " " & (ctrl_id as text)
end tell
APPLESCRIPT
}

WINDOW_IDS=$(_create_windows)

# Persist window IDs so the storyboard runner can raise the RECORDING
# window automatically before typing.  Matched against the iTerm window
# id (immune to renames or multiple windows).
read -r REC_WIN_ID CTRL_WIN_ID <<<"$WINDOW_IDS"

# Resolve the CGWindowID (AXWindowID) of the RECORDING window via the
# macOS accessibility API.  Used by _session.sh for true window-
# tracking capture (screencapture -v -l <id>) instead of fixed-rect.
# Falls back to "" on permission denial or lookup miss; _session.sh
# then drops back to -R<rect>.  Brief sleep first so System Events
# sees the just-created iTerm windows.
sleep 0.5
_get_recording_ax_window_id() {
    osascript 2>/dev/null <<APPLESCRIPT
try
    tell application "System Events"
        tell process "iTerm2"
            repeat with w in every window
                try
                    set p to position of w
                    set px to item 1 of p
                    set py to item 2 of p
                    if (px >= ${REC_L} - 3) and (px <= ${REC_L} + 3) and (py >= ${REC_T} - 3) and (py <= ${REC_T} + 3) then
                        return (value of attribute "AXWindowID" of w) as text
                    end if
                end try
            end repeat
        end tell
    end tell
end try
return ""
APPLESCRIPT
}
AX_WIN_ID="$(_get_recording_ax_window_id)"

WIN_STATE_FILE="${TMPDIR:-/tmp}/dcr-windows.state"
cat > "$WIN_STATE_FILE" <<STATE
REC_WIN_ID=$REC_WIN_ID
CTRL_WIN_ID=$CTRL_WIN_ID
AX_WIN_ID=$AX_WIN_ID
STATE

cat <<EOF

=== demo-cli-recorder: windows ready ===

  ┌─ RECORDING  ── ${REC_L},${REC_T} → ${REC_R},${REC_B}
  │   • Visible in the video.  iTerm profile: ${ITERM_PROFILE_NAME} (${FONT_NAME} ${FONT_SIZE}pt)
  │
  └─ CONTROL    ── ${CTRL_L},${CTRL_T} → ${CTRL_R},${CTRL_B}
      • Run your demo-driver script here.

Both windows cd'd to: ${CWD}

Start your screen recorder (or use ffmpeg / screencapture) cropped to
the RECORDING window's bounds and you're ready to record.
EOF
