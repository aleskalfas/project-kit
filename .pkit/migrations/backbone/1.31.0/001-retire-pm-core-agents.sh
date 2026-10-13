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
# Post-propagation + post-migration state:
#   .pkit/agents/core/product-manager.md  → removed by the copy (no longer in kit)
#   .pkit/agents/core/orchestrator.md     → removed by the copy
#   .claude/agents/product-manager.md     → dangling symlink (cleaned here)
#   .claude/agents/orchestrator.md        → dangling symlink (cleaned here)
#
# The kit-shipped tree under .pkit/agents/core/ is reconciled by the copy (it
# walks the kit content vs adopter content). What this migration handles is
# the cleanup of the stale .claude/agents/ symlinks that deploy-agents.sh left
# from the prior version. The deploy's own stale pass skips them: it reads
# only files it can open, and a dangling link opens nothing.
#
# Safe over any state (COR-010): a version transition may run it again over a
# project whose migration history is unknown. So it acts only on a positive
# sign that the path is that stale link, never on the name alone:
#   - the path is a symbolic link,
#   - its target names the retired core agent, `.pkit/agents/core/<name>`,
#   - and that target no longer exists.
# A regular file of that name, the project's own agent, and a link to any
# other agent of that name are left in place.
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
    if [ ! -L "$path" ]; then
        if [ -e "$path" ]; then
            echo "  [keep] $path (not a link the deploy left: the project's own)"
        fi
        continue
    fi
    target="$(readlink "$path")"
    case "$target" in
        */.pkit/agents/core/"$stale" | .pkit/agents/core/"$stale") ;;
        *)
            echo "  [keep] $path (links to $target, not the retired core agent)"
            continue
            ;;
    esac
    if [ -e "$path" ]; then
        echo "  [keep] $path (the core agent it links to still exists)"
        continue
    fi
    rm -f "$path"
    echo "  [remove] $path (stale link to the retired core agent; retired per COR-026)"
    removed=$((removed + 1))
done

if [ "$removed" -eq 0 ]; then
    echo "  [skip] no stale pm-coordinator links found; already migrated or never deployed"
    exit 0
fi

echo "  [ok] retired $removed stale pm-coordinator link(s); fulfills COR-017 Retroactive reclassification for agents"
