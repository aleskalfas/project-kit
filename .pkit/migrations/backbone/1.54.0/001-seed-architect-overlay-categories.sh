#!/usr/bin/env bash
# Backbone migration 1.54.0 — resource: seed-architect-overlay-categories.
#
# The `architect` agent (COR-024/COR-025) references the overlay categories
# `<architecture-docs>` and `<adr-records>`. The install seed template was
# updated to declare them, but it only writes when no overlay.yaml exists
# (`if not overlay.exists()`), so adopters whose overlay was seeded BEFORE the
# architect agent landed never gained the categories. On the next sync,
# deploy-agents.sh then cannot resolve `<architecture-docs>` for the architect
# agent. This migration seeds the missing categories into an existing overlay,
# with the same safe defaults as the install seed, preserving every other
# entry the adopter already has.
#
# Idempotent — re-running on already-migrated state is a no-op (each category
# is appended only when absent). Adopter customisations are never touched: we
# only ever ADD a missing top-level category, never rewrite an existing one.

set -euo pipefail

# ROOT is the adopter's project root, provided by the runtime.
: "${ROOT:?ROOT must be set by the upgrade runtime}"

OVERLAY="$ROOT/.pkit/agents/project/overlay.yaml"

if [ ! -f "$OVERLAY" ]; then
    # No overlay at all → install/sync seeds a complete one (with these
    # categories) on its own; nothing to migrate.
    echo "  [skip] no .pkit/agents/project/overlay.yaml; install seeds a complete one"
    exit 0
fi

added=0

# Append a top-level category block only when the key is absent. Top-level
# keys may appear in any order in YAML, so appending is valid and preserves
# all existing content. Match `^<key>:` to detect an existing definition.
ensure_category() {
    local key="$1"
    local block="$2"
    if grep -qE "^${key}:" "$OVERLAY"; then
        return 0
    fi
    printf '\n%s\n' "$block" >> "$OVERLAY"
    echo "  [add] $key (seeded per COR-024/COR-025 — the architect agent requires it)"
    added=$((added + 1))
}

ensure_category "architecture-docs" "# Architecture documentation roots (per COR-024) — seeded by the 1.54.0
# migration. The architect agent reads these; repoint at your real
# architectural docs (e.g. docs/architecture/) when you have them.
architecture-docs:
  - README.md"

ensure_category "adr-records" "# ADR records location (per COR-024 + COR-025) — seeded by the 1.54.0
# migration. The architect agent owns this; \`pkit new decision adr <slug>\`
# stamps records here (the directory is created on first use).
adr-records:
  - docs/architecture/decisions/"

if [ "$added" -eq 0 ]; then
    echo "  [skip] overlay already defines the architect categories; already migrated"
    exit 0
fi

echo "  [ok] seeded $added overlay categor(ies) the architect agent requires"
