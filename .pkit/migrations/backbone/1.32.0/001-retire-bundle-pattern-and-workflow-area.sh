#!/usr/bin/env bash
# Backbone migration — retire the bundle pattern and the workflow area per COR-027.
#
# COR-027 supersedes COR-005's bundle half: capabilities (COR-017) subsumed the
# alternative-implementations use case; alternative variants now live as
# capability-internal data, not as filesystem-level bundles. This migration
# handles the adopter-state side of the retirement.
#
# What sync handles (no migration action needed):
#   .pkit/workflow/                                  → removed from kit content
#   .pkit/skills/core/bundle-author.md               → removed
#
# What this migration handles (adopter-owned state outside the sync surface):
#
#   1. .pkit/workflow/project/<bundle>/             — project-owned per-bundle
#      config + manifest. Sync doesn't touch it. Migration removes it (and the
#      parent .pkit/workflow/project/ if empty after).
#
#   2. .pkit/manifests/components/github-issues.yaml — per-component manifest
#      stamped by the legacy `pkit bundle install github-issues` flow. Sync
#      doesn't touch it. Migration removes it if it exists.
#
#   3. .pkit/manifest.yaml's `components:` registry — the legacy
#      `kind: bundle` entry (typically `github-issues`). The backbone manifest
#      lives in the kit-shipped surface and IS updated by sync from upstream,
#      but adopters who have customised it locally won't see the upstream
#      delete via sync (manifests use the merge primitive, not blind
#      overwrite). Migration removes any `kind: bundle` component entries.
#
# Idempotent: re-runs on already-migrated state are no-ops.
#
# Run via the upgrade runtime with ROOT=<adopter root>.

set -euo pipefail

: "${ROOT:?ROOT must be set by the upgrade runtime}"

PKIT_DIR="$ROOT/.pkit"
WORKFLOW_PROJECT_DIR="$PKIT_DIR/workflow/project"
WORKFLOW_DIR="$PKIT_DIR/workflow"
MANIFESTS_DIR="$PKIT_DIR/manifests/components"
BACKBONE_MANIFEST="$PKIT_DIR/manifest.yaml"

removed=0

# Step 1: Remove .pkit/workflow/project/<bundle>/ subtrees + the parent if empty.
if [ -d "$WORKFLOW_PROJECT_DIR" ]; then
    for entry in "$WORKFLOW_PROJECT_DIR"/*/; do
        if [ -d "$entry" ]; then
            echo "  [remove] $entry (project-owned bundle config; retired per COR-027)"
            rm -rf "$entry"
            removed=$((removed + 1))
        fi
    done
    # Remove the empty workflow/project dir (and workflow/ if also empty).
    rmdir "$WORKFLOW_PROJECT_DIR" 2>/dev/null || true
    rmdir "$WORKFLOW_DIR" 2>/dev/null || true
fi

# Step 2: Remove any per-bundle component manifests left from `pkit bundle install`.
if [ -d "$MANIFESTS_DIR" ]; then
    for mf in "$MANIFESTS_DIR"/github-issues.yaml; do
        if [ -f "$mf" ]; then
            echo "  [remove] $mf (legacy bundle component manifest)"
            rm -f "$mf"
            removed=$((removed + 1))
        fi
    done
fi

# Step 3: Drop any `kind: bundle` entries from the backbone manifest.
# Awk-based filter — removes 3-line YAML blocks starting with `- kind: bundle`.
if [ -f "$BACKBONE_MANIFEST" ]; then
    if grep -q "kind: bundle" "$BACKBONE_MANIFEST"; then
        awk '
            BEGIN { skip = 0 }
            /^  - kind: bundle/ { skip = 3; next }
            skip > 0 { skip--; next }
            { print }
        ' "$BACKBONE_MANIFEST" > "$BACKBONE_MANIFEST.tmp" && mv "$BACKBONE_MANIFEST.tmp" "$BACKBONE_MANIFEST"
        echo "  [edit] $BACKBONE_MANIFEST (dropped bundle component entries)"
        removed=$((removed + 1))
    fi
fi

if [ "$removed" -eq 0 ]; then
    echo "  [skip] no bundle / workflow state found; already migrated or never present"
    exit 0
fi

echo "  [ok] retired $removed bundle/workflow artifact(s); COR-027 fulfilled"
