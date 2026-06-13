#!/usr/bin/env bash
# Backbone migration — retire core pm-coordinator agents per COR-026.
#
# COR-026 establishes the universal rule: discipline-implying agents live in
# the capability that ships the discipline, not in core. COR-017's Retroactive
# reclassification implication named `product-manager` and `orchestrator`
# (shipped in COR-013 as universal core) as candidates. This migration is the
# fulfillment for the agent cases.
#
# Pre-migration state in an installed adopter:
#   .pkit/agents/core/product-manager.md  (synced from kit)
#   .pkit/agents/core/orchestrator.md     (synced from kit)
#   .claude/agents/product-manager.md     (symlink deployed by deploy-agents.sh)
#   .claude/agents/orchestrator.md        (symlink deployed by deploy-agents.sh)
#
# Post-sync + post-migration state:
#   .pkit/agents/core/product-manager.md  → removed by sync (file no longer in kit)
#   .pkit/agents/core/orchestrator.md     → removed by sync
#   .claude/agents/product-manager.md     → stale symlink (cleaned here)
#   .claude/agents/orchestrator.md        → stale symlink (cleaned here)
#
# The kit-shipped tree under .pkit/agents/core/ is reconciled by sync (it
# walks the kit content vs adopter content). What this migration handles is
# the cleanup of the stale .claude/agents/ symlinks that deploy-agents.sh
# left from the prior version.
#
# Idempotent: re-runs on already-migrated state are no-ops.
#
# Run via the upgrade runtime with ROOT=<adopter root>.

set -euo pipefail

: "${ROOT:?ROOT must be set by the upgrade runtime}"

CLAUDE_AGENTS_DIR="$ROOT/.claude/agents"

if [ ! -d "$CLAUDE_AGENTS_DIR" ]; then
    echo "  [skip] no .claude/agents/ dir; no claude-code adapter state to migrate"
    exit 0
fi

removed=0

for stale in product-manager.md orchestrator.md; do
    path="$CLAUDE_AGENTS_DIR/$stale"
    if [ -L "$path" ] || [ -e "$path" ]; then
        rm -f "$path"
        echo "  [remove] $path (retired per COR-026)"
        removed=$((removed + 1))
    fi
done

if [ "$removed" -eq 0 ]; then
    echo "  [skip] no stale pm-coordinator symlinks found; already migrated or never deployed"
    exit 0
fi

echo "  [ok] retired $removed stale pm-coordinator symlink(s); fulfills COR-017 Retroactive reclassification for agents"
