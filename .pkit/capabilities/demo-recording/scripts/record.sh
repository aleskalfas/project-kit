#!/usr/bin/env bash
# demo-cli-recorder/record.sh — screen-recorded CLI demo launcher.
#
# Reads a small YAML config (cwd + window bounds + recordings dir),
# starts a screen recording in the background, opens RECORDING +
# CONTROL iTerm2 windows at the configured bounds, and dispatches a
# demo driver script into the CONTROL window.  Stop the recording
# afterwards with `record.sh stop`.
#
# Generic & project-agnostic — knows about iTerm, screencapture, and
# the YAML schema, but nothing about IGW / AUJ / specific demos.
#
# Usage:
#   record.sh <demo>                     # start: record + windows + dispatch (AUTONOMOUS by default)
#   record.sh <demo> --interactive       # add start + stop Enter prompts for inspection / safety
#   record.sh <demo> --no-recording      # skip the video capture
#   record.sh <demo> --validate          # parse + print the storyboard, do nothing else
#   record.sh windows                    # just open the two windows
#   record.sh stop                       # stop the active recording
#
# Flags:
#   --config <path>                       YAML config (default: <demo-dir>/record.yaml)
#   --interactive                         Enable the start + stop Enter prompts (operator can read
#                                         the dispatch summary and Ctrl-C to abort).  Without this
#                                         flag, recording starts on dispatch and stops immediately
#                                         when the storyboard finishes — the right default for
#                                         AI / REPLAY storyboards (no human-in-the-loop premise)
#                                         and for CI runs.
#   --no-recording                        Skip screen capture
#   --validate                            Validate storyboard syntax only (no windows / no recording)
#   --help                                Show this help
#
# The demo arg is either:
#   - a path to a storyboard .md file (relative or absolute), or
#   - a bare name (e.g. `human`) resolved as <config-dir>/<name>.md
#
# YAML schema:
#   cwd: <absolute path>
#   windows:
#     recording: [L, T, R, B]
#     control:   [L, T, R, B]
#   recordings_dir: <path, relative-to-config-or-absolute>   # optional

set -euo pipefail

STATE_FILE="${TMPDIR:-/tmp}/dcr-recording.state"

# The single platform gate for the recording plugin (Layer 3), per
# [demo-recording:DEC-004-platform-coupling-and-gate-placement]. Sourced
# here; `dcr_require_macos` is CALLED only at the executing actions
# below (start after the --validate short-circuit, windows, stop), never
# on the validate path.
# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/plugins/recording/platform-guard.sh"

usage() {
    sed -n '3,/^set -euo/p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//;/^set -euo/d'
}

# --- Arg parsing -------------------------------------------------------------

CONFIG=""
RECORDING=1
VALIDATE_ONLY=0
INTERACTIVE=0   # default: autonomous (no Enter gates).  --interactive opts in.
POS_ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h)        usage; exit 0 ;;
        --config)         CONFIG="$2"; shift 2 ;;
        --no-recording)   RECORDING=0; shift ;;
        --interactive)    INTERACTIVE=1; shift ;;
        --validate)       VALIDATE_ONLY=1; shift ;;
        --)               shift; POS_ARGS+=("$@"); break ;;
        -*)               echo "record.sh: unknown flag '$1'" >&2; usage >&2; exit 2 ;;
        *)                POS_ARGS+=("$1"); shift ;;
    esac
done

if [[ ${#POS_ARGS[@]} -lt 1 ]]; then
    echo "record.sh: missing argument" >&2
    usage >&2
    exit 2
fi

FIRST="${POS_ARGS[0]}"
case "$FIRST" in
    stop)    ACTION="stop";    DEMO="" ;;
    windows) ACTION="windows"; DEMO="" ;;
    *)       ACTION="start";   DEMO="$FIRST" ;;
esac

# --- YAML parsing helpers ----------------------------------------------------

yaml_get_scalar() {
    local key="$1"
    grep -E "^${key}:[[:space:]]+" "$CONFIG" 2>/dev/null | head -1 | sed -E "s/^${key}:[[:space:]]+//; s/[[:space:]]*\$//"
}

yaml_get_window_bounds() {
    local win="$1"
    awk -v win="$win" '
        /^windows:/ { in_windows=1; next }
        /^[^[:space:]]/ { in_windows=0 }
        in_windows && $0 ~ "^[[:space:]]+" win ":" {
            sub(/^[[:space:]]+[^:]+:[[:space:]]*\[/, "")
            sub(/\][[:space:]]*$/, "")
            gsub(/[[:space:]]/, "")
            print
            exit
        }
    ' "$CONFIG"
}

yaml_get_hook_scripts() {
    # Extract `hooks.after_record:` list entries from CONFIG.  Each list
    # entry is one line of the form `  - <path>`.  Emits one path per
    # line; empty output when no hooks are configured.
    awk '
        /^hooks:/ { in_hooks=1; next }
        /^[^[:space:]]/ { in_hooks=0 }
        in_hooks && /^[[:space:]]+after_record:/ { in_after=1; next }
        in_after && /^[[:space:]]+[a-zA-Z_]+:/ { in_after=0 }
        in_after && /^[[:space:]]+-[[:space:]]+/ {
            sub(/^[[:space:]]+-[[:space:]]+/, "")
            sub(/[[:space:]]+#.*$/, "")
            sub(/[[:space:]]*$/, "")
            print
        }
    ' "$CONFIG"
}

# --- Storyboard front-matter parsing -----------------------------------------

storyboard_frontmatter() {
    # Parse YAML front-matter (delimited by `---` on lines 1 and N at the
    # top of the file) from a storyboard markdown file.  Emits one
    # `KEY=VALUE` line per scalar key found.  Skips nested structures /
    # lists / quoted values (caller can extend if needed).  Empty output
    # when the storyboard has no front-matter.
    local storyboard="$1"
    awk '
        NR == 1 && /^---[[:space:]]*$/ { in_fm=1; next }
        in_fm && /^---[[:space:]]*$/ { exit }
        in_fm && /^[a-zA-Z_][a-zA-Z0-9_]*:[[:space:]]+/ {
            split($0, kv, ":")
            key = kv[1]
            value = $0
            sub(/^[^:]+:[[:space:]]+/, "", value)
            sub(/[[:space:]]+#.*$/, "", value)
            sub(/[[:space:]]*$/, "", value)
            print key "=" value
        }
    ' "$storyboard"
}

# --- Stop action -------------------------------------------------------------

do_stop() {
    dcr_require_macos || exit 1
    if [[ ! -f "$STATE_FILE" ]]; then
        echo "record.sh: no active recording (no state file at $STATE_FILE)" >&2
        exit 1
    fi
    # shellcheck disable=SC1090
    source "$STATE_FILE"
    if [[ -n "${PID:-}" ]] && kill -0 "$PID" 2>/dev/null; then
        kill -INT "$PID"
        # Give screencapture a moment to flush and close the file.
        local i=0
        while kill -0 "$PID" 2>/dev/null && (( i < 20 )); do
            sleep 0.2
            i=$((i + 1))
        done
        echo "Recording stopped (PID $PID)."
    else
        echo "record.sh: recording PID ${PID:-?} not running; cleaning state."
    fi
    rm -f "$STATE_FILE"
    if [[ -n "${OUTPUT:-}" && -f "$OUTPUT" ]]; then
        echo "Video saved: $OUTPUT"
        # Optional .mov → .mp4 + colour-tag re-mux.  Silent no-op if
        # ffmpeg isn't installed or DCR_NO_POSTPROCESS=1.
        "$(dirname "${BASH_SOURCE[0]}")/plugins/recording/ffmpeg_post.sh" "$OUTPUT" || true
    fi

    # Run after_record hooks.  These are project-specific scripts declared
    # in record.yaml under `hooks.after_record`.  Each runs sequentially
    # with these env vars:
    #
    #   DCR_SCENARIO       basename of the storyboard (e.g. "ai", "human")
    #   DCR_STORYBOARD     absolute path to the storyboard .md
    #   DCR_VIDEO_PATH     final video path (.mp4 if ffmpeg ran, .mov otherwise);
    #                      empty when --no-recording was passed
    #   DCR_CONFIG         absolute path to record.yaml
    #   DCR_REPO_ROOT      directory containing record.yaml (cwd for the hook)
    #   DCR_META_<KEY>     every scalar key from the storyboard's YAML
    #                      front-matter, upcased.  e.g.:
    #                          ---
    #                          mode: ai
    #                          ---
    #                      → DCR_META_MODE=ai
    #
    # Hook failures log a warning but do not fail the overall recording
    # — by this point the .mov / .mp4 is on disk; hooks are sugar on top.
    if [[ -n "${CONFIG:-}" && -f "$CONFIG" && -n "${STORYBOARD:-}" ]]; then
        local final_video="${OUTPUT:-}"
        if [[ -n "$final_video" && -f "${final_video%.mov}.mp4" ]]; then
            final_video="${final_video%.mov}.mp4"
        fi
        local repo_root
        repo_root="$(cd "$(dirname "$CONFIG")" && pwd)"
        local hook_scripts
        hook_scripts="$(yaml_get_hook_scripts)"
        if [[ -n "$hook_scripts" ]]; then
            # Read front-matter once → DCR_META_<KEY> env vars.
            local meta_env=()
            local line key value upcased
            while IFS= read -r line; do
                [[ -z "$line" ]] && continue
                key="${line%%=*}"
                value="${line#*=}"
                upcased="$(echo "$key" | tr '[:lower:]' '[:upper:]')"
                meta_env+=("DCR_META_${upcased}=${value}")
            done < <(storyboard_frontmatter "$STORYBOARD")

            echo "record.sh: running after_record hooks"
            while IFS= read -r hook_script; do
                [[ -z "$hook_script" ]] && continue
                # Resolve relative paths against the config's dir.
                if [[ "$hook_script" != /* ]]; then
                    hook_script="${repo_root}/${hook_script}"
                fi
                if [[ ! -x "$hook_script" ]]; then
                    echo "record.sh: WARNING: hook not executable: $hook_script" >&2
                    continue
                fi
                echo "  → $hook_script"
                (
                    cd "$repo_root"
                    env \
                        DCR_SCENARIO="$DEMO" \
                        DCR_STORYBOARD="$STORYBOARD" \
                        DCR_VIDEO_PATH="$final_video" \
                        DCR_CONFIG="$CONFIG" \
                        DCR_REPO_ROOT="$repo_root" \
                        "${meta_env[@]}" \
                        "$hook_script"
                ) || {
                    echo "record.sh: WARNING: hook exited non-zero: $hook_script" >&2
                }
            done <<< "$hook_scripts"
        fi
    fi

    # Close the iTerm windows we created (RECORDING + CONTROL), unless
    # the operator wants them kept.  Order matters: close RECORDING
    # first; CONTROL last because the shell that runs `record.sh stop`
    # is typically inside CONTROL (post-demo's exec, or _session.sh's
    # SIGINT trap).  Closing CONTROL kills that shell, so anything that
    # needs to print to the operator must happen before this point.
    close_demo_windows
    exit 0
}

# Close the RECORDING and CONTROL iTerm windows by id.  IDs come from
# the windows state file (written by setup-windows.sh).  Silent no-op
# if the state file is missing, DCR_KEEP_WINDOWS=1, or the ids don't
# match any current iTerm window.
close_demo_windows() {
    if [[ "${DCR_KEEP_WINDOWS:-0}" == "1" ]]; then
        return 0
    fi
    local win_state="${TMPDIR:-/tmp}/dcr-windows.state"
    [[ -f "$win_state" ]] || return 0
    # shellcheck disable=SC1090
    source "$win_state"
    # Brief grace period so the operator can read the "Video saved"
    # and post-process messages before the windows disappear.
    sleep 1
    local id
    for id in "${REC_WIN_ID:-}" "${CTRL_WIN_ID:-}"; do
        [[ -n "$id" ]] || continue
        osascript >/dev/null 2>&1 <<APPLESCRIPT
tell application "iTerm"
    try
        repeat with w in windows
            if (id of w as text) is "$id" then
                close w
                exit repeat
            end if
        end repeat
    end try
end tell
APPLESCRIPT
    done
    rm -f "$win_state"
}

# --- Resolve config + demo ---------------------------------------------------

resolve_demo_and_config() {
    # The demo arg now points at a STORYBOARD (markdown file), not a driver
    # script.  The runner reads the storyboard directly — see
    # storyboards/runner.py / run-storyboard.sh.

    # If config is explicit, the demo arg may be a bare name relative to it.
    if [[ -n "$CONFIG" ]]; then
        if [[ -z "$DEMO" ]]; then return; fi
        if [[ -f "$DEMO" ]]; then
            DEMO_PATH="$DEMO"
        else
            local config_dir="$(cd "$(dirname "$CONFIG")" && pwd)"
            # Search order: $config_dir/<name>.md, $config_dir/storyboards/<name>.md,
            # then literal $config_dir/<name>.  Supports both flat layouts (config
            # and storyboards in one folder) and grouped layouts (config beside a
            # storyboards/ subfolder).
            local found=""
            for cand in \
                "$config_dir/${DEMO}.md" \
                "$config_dir/storyboards/${DEMO}.md" \
                "$config_dir/$DEMO"; do
                if [[ -f "$cand" ]]; then
                    found="$cand"
                    break
                fi
            done
            if [[ -z "$found" ]]; then
                echo "record.sh: cannot find storyboard '$DEMO' (looked in $config_dir for $DEMO.md, storyboards/$DEMO.md, $DEMO)" >&2
                exit 1
            fi
            DEMO_PATH="$found"
        fi
        return
    fi

    # Config not provided.  Try to resolve from the demo arg.
    if [[ -z "$DEMO" ]]; then
        echo "record.sh: --config is required for the '$ACTION' subcommand without a demo argument" >&2
        exit 2
    fi

    if [[ -f "$DEMO" ]]; then
        DEMO_PATH="$(cd "$(dirname "$DEMO")" && pwd)/$(basename "$DEMO")"
    else
        # Look in conventional locations relative to CWD.  Each bundle's
        # record.sh wrapper passes --config explicitly, so these fallbacks
        # only fire for ad-hoc invocations from inside a bundle directory.
        local candidate=""
        for dir in \
            "$(pwd)/storyboards" \
            "$(dirname "${BASH_SOURCE[0]}")/../storyboards"; do
            if [[ -f "$dir/${DEMO}.md" ]]; then
                candidate="$(cd "$dir" && pwd)/${DEMO}.md"
                break
            fi
        done
        if [[ -z "$candidate" ]]; then
            echo "record.sh: cannot find storyboard for '$DEMO' (pass a path, or --config <bundle>/record.yaml)" >&2
            exit 1
        fi
        DEMO_PATH="$candidate"
    fi
    CONFIG="$(dirname "$DEMO_PATH")/record.yaml"
}

# --- Start action ------------------------------------------------------------

do_start() {
    resolve_demo_and_config
    if [[ ! -f "$CONFIG" ]]; then
        echo "record.sh: config not found: $CONFIG" >&2
        echo "  Create record.yaml next to the storyboard, or pass --config <path>" >&2
        exit 2
    fi

    # --validate short-circuits everything else: just parse + print the
    # storyboard, don't open windows or start recording.  Platform-neutral,
    # so it runs BEFORE the macOS gate below.
    if (( VALIDATE_ONLY )); then
        exec "$(dirname "${BASH_SOURCE[0]}")/run-storyboard.sh" \
            "$DEMO_PATH" --validate
    fi

    # Everything past here drives iTerm2 + screencapture + osascript —
    # the macOS-only recording machinery.  Gate per DEC-004.
    dcr_require_macos || exit 1

    local cwd rec_bounds ctrl_bounds recordings_dir
    cwd=$(yaml_get_scalar cwd)
    rec_bounds=$(yaml_get_window_bounds recording)
    ctrl_bounds=$(yaml_get_window_bounds control)
    recordings_dir=$(yaml_get_scalar recordings_dir)
    if [[ -z "$cwd" || -z "$rec_bounds" || -z "$ctrl_bounds" ]]; then
        echo "record.sh: config missing required fields (cwd / windows.recording / windows.control)" >&2
        echo "  see $CONFIG" >&2
        exit 2
    fi

    # Sanity check the storyboard parses BEFORE opening windows or starting
    # recording — saves the operator from "windows opened, then nothing
    # happened" when the storyboard has a typo.
    local parser_path="$(dirname "${BASH_SOURCE[0]}")/storyboards/runner.py"
    if ! python3 "$parser_path" "$DEMO_PATH" >/dev/null 2>&1; then
        echo "record.sh: storyboard has parse errors.  Run with --validate to see them." >&2
        exit 1
    fi

    # Pre-compute the rect + output path for the recording.  Recording
    # itself is started later (by _session.sh, after the operator presses
    # Enter inside CONTROL) — see the dispatch below.
    local rect="" output=""
    # Resolve recordings_dir regardless of --no-recording, so the
    # per-take log path below has a home even when video capture is off.
    if [[ -z "$recordings_dir" ]]; then
        recordings_dir="./recordings"
    fi
    if [[ "$recordings_dir" != /* ]]; then
        recordings_dir="$(cd "$(dirname "$CONFIG")" && pwd)/$recordings_dir"
    fi
    mkdir -p "$recordings_dir"
    local demo_name="$(basename "${DEMO_PATH%.md}")"
    local timestamp="$(date +%Y-%m-%dT%H%M%S)"

    # Per-take diagnostic log.  Default-on; landed alongside the recording
    # so it's discoverable from the bundle.  Caller can override DCR_LOG
    # in the invoking shell to redirect (e.g. /tmp/dcr.log).
    local log_dir="${recordings_dir}/.logs"
    mkdir -p "$log_dir"
    local default_log="$log_dir/${timestamp}-${demo_name}.log"
    : "${DCR_LOG:=$default_log}"
    : > "$DCR_LOG"  # truncate so each take starts clean

    if (( RECORDING )); then
        output="$recordings_dir/${timestamp}-${demo_name}.mov"

        # -R wants [x,y,w,h]; YAML stores [left,top,right,bottom].
        local l t r b
        IFS=, read -r l t r b <<<"$rec_bounds"
        rect="${l},${t},$((r - l)),$((b - t))"
    fi

    # Open the two windows.  Forward optional font knobs from record.yaml.
    # ``|| true`` so a missing key (commented out / absent in the yaml)
    # doesn't trip ``set -euo pipefail``: yaml_get_scalar's underlying
    # grep returns 1 on no-match, which would otherwise kill the script.
    local font_size font_name
    font_size=$(yaml_get_scalar font_size) || font_size=""
    font_name=$(yaml_get_scalar font_name) || font_name=""
    DCR_CWD="$cwd" \
    DCR_FONT_SIZE="${font_size:-18}" \
    DCR_FONT_NAME="${font_name:-Menlo-Regular}" \
        "$(dirname "${BASH_SOURCE[0]}")/plugins/recording/setup-windows.sh" \
        "$rec_bounds" "$ctrl_bounds"

    # Dispatch _session.sh into CONTROL.  CONTROL was the last window
    # created → frontmost → keystrokes target it.  _session.sh owns the
    # recording lifecycle: prompts for the first Enter, starts capture,
    # runs the storyboard, runs post-demo, and stops the recording on
    # SIGINT.
    sleep 1
    local session_path="$(dirname "${BASH_SOURCE[0]}")/plugins/recording/_session.sh"
    local dispatched_cmd="$session_path $DEMO_PATH --config $CONFIG"
    if (( RECORDING )); then
        dispatched_cmd="$session_path $DEMO_PATH --rect $rect --output $output --config $CONFIG"
    fi
    if (( INTERACTIVE )); then
        dispatched_cmd="$dispatched_cmd --interactive"
    fi
    # Prefix DCR_LOG so it survives the osascript → iTerm shell hop.
    # The new shell inherits the user's env, not the wrapper's; inline
    # env-prefix is the simplest way to propagate.
    dispatched_cmd="DCR_LOG=$(printf %q "$DCR_LOG") $dispatched_cmd"
    local cmd_escaped="$(printf '%s' "$dispatched_cmd" | sed 's/"/\\"/g')"
    osascript <<APPLESCRIPT
tell application "iTerm"
    tell current window
        tell current session
            write text "$cmd_escaped"
        end tell
    end tell
end tell
APPLESCRIPT

    cat <<EOF

=== Storyboard dispatched ===

  ▸ CONTROL is running '$(basename "$DEMO_PATH")'.
  ▸ Diagnostic log: $DCR_LOG
      (per-take; truncated on each invocation.  Tail it in another
       terminal — \`tail -f $DCR_LOG\` — if a take goes sideways.)
EOF
    if (( INTERACTIVE )) && (( RECORDING )); then
        cat <<EOF
  ▸ Click CONTROL.  It will prompt you to press Enter to start the
    recording (--interactive) — recording only begins once you do.
EOF
    elif (( RECORDING )); then
        cat <<EOF
  ▸ Autonomous mode (default): recording starts immediately and
    stops automatically when the storyboard finishes.  No operator
    keystrokes needed.  Pass --interactive for the inspection-friendly
    Enter gates if you want them.
EOF
    else
        cat <<EOF
  ▸ Click CONTROL.  The storyboard will start immediately (no recording).
EOF
    fi
    cat <<EOF
  ▸ Then for each step, the runner prints a 'NEXT STEP' prompt;
    press Enter HERE in CONTROL and the typing fires into RECORDING.
  ▸ Ctrl-C in CONTROL stops the recording cleanly at any point.
EOF
    if (( INTERACTIVE )) && (( RECORDING )); then
        cat <<EOF
  ▸ When the storyboard finishes, CONTROL will prompt:
      "Press Enter to stop recording, Ctrl-C to keep recording."
    Enter → stops + saves video, Ctrl-C → keeps it going.
EOF
    fi
}

# --- Windows-only action -----------------------------------------------------

do_windows() {
    dcr_require_macos || exit 1
    if [[ -z "$CONFIG" ]]; then
        echo "record.sh: 'windows' subcommand needs --config <path>" >&2
        exit 2
    fi
    if [[ ! -f "$CONFIG" ]]; then
        echo "record.sh: config not found: $CONFIG" >&2
        exit 2
    fi
    local cwd rec_bounds ctrl_bounds
    cwd=$(yaml_get_scalar cwd)
    rec_bounds=$(yaml_get_window_bounds recording)
    ctrl_bounds=$(yaml_get_window_bounds control)
    if [[ -z "$cwd" || -z "$rec_bounds" || -z "$ctrl_bounds" ]]; then
        echo "record.sh: config missing required fields" >&2
        exit 2
    fi
    DCR_CWD="$cwd" "$(dirname "${BASH_SOURCE[0]}")/plugins/recording/setup-windows.sh" \
        "$rec_bounds" "$ctrl_bounds"
}

# --- Dispatch ----------------------------------------------------------------

case "$ACTION" in
    start)   do_start ;;
    windows) do_windows ;;
    stop)    do_stop ;;
esac
