#!/usr/bin/env bash
# Backbone migration 1.140.0 — structural: retire-pkit-router-shim.
#
# ADR-039 folded the `scripts/pkit-router` shim's CWD-aware routing into the
# installed `pkit` binary itself: the entry point now routes per CWD and pin
# natively, so the separate shim is retired. Removing `scripts/pkit-router` and
# changing the install procedure is a surface change that must ship a migration
# in the same change-set (COR-010 / rules/core.md rule 7).
#
# What this migration is (and is NOT):
#   - The shim was only ever a DEV-MACHINE PATH artifact — a copy at
#     `~/.pkit/shim/pkit` installed by the former `mise run pkit:router-install`
#     task, sitting ahead of the pinned binary on PATH. It was NEVER adopter
#     project state, so there is nothing to rewrite inside ROOT.
#   - This is therefore a GUIDANCE migration: if a stale shim copy is on this
#     machine, tell the operator to remove it (the binary routes natively now,
#     so the shim is redundant and shadows the native router). It does not, and
#     must not, delete the operator's files for them — removing something on a
#     user's PATH is their gesture to make.
#
# Idempotent: a no-op when no stale shim is present (the common case, incl. every
# adopter that never had the dev shim), and re-running after the operator has
# removed the shim reports the same clean "nothing to do".

set -euo pipefail

# ROOT is the adopter's project root, provided by the runtime.
: "${ROOT:?ROOT must be set by the upgrade runtime}"

# The former install location. Honour the same override the retired task used
# (PKIT_ROUTER_DIR), defaulting to ~/.pkit/shim, so a non-default install is
# still detected.
shim_dir="${PKIT_ROUTER_DIR:-$HOME/.pkit/shim}"
shim="$shim_dir/pkit"

if [ ! -e "$shim" ]; then
    echo "  [skip] no stale pkit-router shim at $shim; the binary routes natively"
    exit 0
fi

# A stale shim is present. Warn loudly and instruct removal — do not delete it.
echo "  [warn] a stale pkit-router shim is on this machine:" >&2
echo "           $shim" >&2
echo "         The pkit binary now routes per CWD and pin natively (ADR-039), so this" >&2
echo "         shim is redundant and shadows the native router. Remove it and drop the" >&2
echo "         PATH line that put it ahead of the pinned binary:" >&2
echo "           rm \"$shim\"" >&2
echo "           # then remove 'export PATH=\"$shim_dir:\$PATH\"' from your shell profile" >&2
echo "         Re-run this migration after removing it to confirm it is gone." >&2

# Guidance delivered — removing a file on the operator's PATH is theirs to do,
# so this is not a failure: exit clean so `pkit upgrade` proceeds.
exit 0
