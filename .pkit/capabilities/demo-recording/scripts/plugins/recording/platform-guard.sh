#!/usr/bin/env bash
# platform-guard.sh — the single platform gate for the recording plugin
# (Layer 3), per [demo-recording:DEC-004-platform-coupling-and-gate-placement].
#
# v1 of the recording plugin assumes macOS: it injects keystrokes via
# osascript + System Events, controls iTerm2 windows via AppleScript, and
# captures the screen via screencapture. Those primitives exist only on
# darwin. This guard is the one place that refuses to run the recording
# MACHINERY off macOS.
#
# Placement (per DEC-004): the gate sits at the recording-plugin
# execution boundary, NOT at the capability or storyboard-format entry.
# The parser, plugin interface, runner, and validator (Layers 1+2) stay
# platform-neutral and run anywhere — so a storyboard can still be
# VALIDATED on Linux. Only the executing entry points (record.sh's
# start/windows/stop actions and run-storyboard.sh's run mode) call
# `dcr_require_macos`; the --validate paths never do.

# Refuse cleanly with a clear message when not on darwin. Idempotent and
# side-effect-free on macOS (returns 0).
dcr_require_macos() {
    local os
    os="$(uname -s 2>/dev/null || echo unknown)"
    if [[ "$os" != "Darwin" ]]; then
        echo "demo-recording: this action requires macOS (darwin); detected '${os}'." >&2
        echo "  The recording plugin drives iTerm2 + osascript + screencapture, which are macOS-only in v1." >&2
        echo "  Storyboard VALIDATION is platform-neutral: 'validate' / '--validate' work anywhere." >&2
        echo "  Linux support would be a second recording backend behind the plugin seam (deferred per DEC-004)." >&2
        return 1
    fi
    return 0
}
