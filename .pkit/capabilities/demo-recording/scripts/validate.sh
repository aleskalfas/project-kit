#!/usr/bin/env bash
# validate.sh — validate a storyboard markdown file's syntax and print
# the resolved step plan. This is the `validate` command leaf declared in
# the capability's package.yaml.
#
# Platform-neutral by design (per [demo-recording:DEC-004-platform-coupling
# -and-gate-placement]): it touches only the parser + runner (Layers 1+2),
# never the macOS recording machinery, so it runs anywhere Python 3 runs.
#
# Usage:
#   validate.sh <path-to-storyboard.md>
#
# Thin wrapper over run-storyboard.sh --validate (which execs
# storyboards/runner.py --validate). Kept as its own command leaf so
# `pkit demo-recording validate <md>` reads naturally and stays a
# read-only, platform-neutral surface.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -lt 1 || "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "usage: $(basename "$0") <storyboard.md>" >&2
    echo "  Validate a storyboard's syntax and print the resolved step plan." >&2
    [[ $# -lt 1 ]] && exit 2 || exit 0
fi

exec "${SCRIPT_DIR}/run-storyboard.sh" "$1" --validate
