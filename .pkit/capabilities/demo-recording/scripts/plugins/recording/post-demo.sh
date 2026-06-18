#!/usr/bin/env bash
# demo-cli-recorder/post-demo.sh — runs after a recorded demo finishes
# (or is interrupted) to give the operator a one-keypress way to stop
# the recording.
#
# Dispatched automatically by record.sh's `start` action when recording
# is enabled.  Pattern:
#     <demo-script-path>; <this-script>
# Using `;` (not `&&`) so post-demo runs even if the demo Ctrl-C's.
#
# Behaviour:
#   - No active recording (no state file)  → exit silently.
#   - Active recording                     → prompt:
#         "Press Enter to stop recording, Ctrl-C to keep recording."
#     Enter   → calls `record.sh stop`, recording ends.
#     Ctrl-C  → leaves recording running; prints how to stop manually.

set -euo pipefail

STATE_FILE="${TMPDIR:-/tmp}/dcr-recording.state"
RECORD_SH="$(dirname "${BASH_SOURCE[0]}")/../../record.sh"

INTERACTIVE=0   # default: stop the recording immediately — no operator Enter required.
while [[ $# -gt 0 ]]; do
    case "$1" in
        --interactive) INTERACTIVE=1; shift ;;
        *) echo "post-demo.sh: unknown arg: $1" >&2; exit 2 ;;
    esac
done

echo ""
echo "=== Demo finished ==="

if [[ -n "${DCR_LOG:-}" && -f "$DCR_LOG" ]]; then
    echo "(diagnostic log: $DCR_LOG)"
fi

if [[ ! -f "$STATE_FILE" ]]; then
    echo "(No active recording — nothing to stop.)"
    exit 0
fi

# Default (autonomous): no operator around to press Enter — stop the
# recording immediately.  This is what makes ``./record.sh ai`` produce
# a finished MP4 without any human interaction.  Pass --interactive on
# the record.sh invocation to get the old "Enter to stop / Ctrl-C to
# keep" inspection-friendly behaviour.
if ! (( INTERACTIVE )); then
    echo "Autonomous mode (default): stopping recording.  Pass --interactive for the inspection-friendly stop gate."
    exec "$RECORD_SH" stop
fi

# Trap Ctrl-C so we can print a helpful message instead of dying silently.
on_interrupt() {
    echo ""
    echo "Recording continues.  Stop it later with: $(realpath --relative-to=. "$RECORD_SH" 2>/dev/null || echo "$RECORD_SH") stop"
    exit 0
}
trap on_interrupt INT

read -r -p "Press Enter to stop recording, Ctrl-C to keep recording. " _

exec "$RECORD_SH" stop
