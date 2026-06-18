#!/usr/bin/env bash
# Backbone migration 1.93.0 — resource: propagate-rules-area.
#
# The rules area (.pkit/rules/core.md) was not in PROPAGATED_AREAS before
# backbone 1.93.0, so adopters installed before this version have no
# .pkit/rules/ directory and the hard rules / communication rules / hygiene
# conventions never reach their agents (issue #96 / COR-014 gap).
#
# The upgrade flow runs `pkit sync` (step 2) before migrations (step 3), so
# .pkit/rules/core.md should already be present by the time this script runs
# on a normal upgrade. This script is the safety net: if the directory still
# doesn't exist it attempts a copy from the source kit; otherwise it exits
# cleanly (idempotent).
#
# What is NOT migrated here:
#   - project.md — adopter-owned; never overwritten by sync or migrations.
#   - The host CLAUDE.md @-include — that is the adapter-tier migration at
#     .pkit/adapters/claude-code/migrations/0.5.0/001-wire-claude-md-rules-include.sh
#
# Idempotent — re-running on already-migrated state is a no-op.

set -euo pipefail

: "${ROOT:?ROOT must be set by the upgrade runtime}"

RULES_DIR="$ROOT/.pkit/rules"
CORE_MD="$RULES_DIR/core.md"

# Already present? (normal case: sync ran first and propagated the area)
if [ -f "$CORE_MD" ]; then
    echo "  [skip] .pkit/rules/core.md already present; already migrated"
    exit 0
fi

# Not present. Try to find the source kit via the pkit dispatcher on PATH.
# The dispatcher resolves the source from its own location; running it with
# a version query gives us the source directory as a by-product.
SOURCE_KIT=""
if command -v pkit >/dev/null 2>&1; then
    PKIT_BIN="$(command -v pkit)"
    # The pkit dispatcher lives at <source>/.pkit/cli/pkit; resolve the
    # source kit by going three directories up.
    MAYBE_SOURCE="$(cd "$(dirname "$PKIT_BIN")/../../.." 2>/dev/null && pwd)"
    if [ -f "$MAYBE_SOURCE/.pkit/rules/core.md" ]; then
        SOURCE_KIT="$MAYBE_SOURCE/.pkit"
    fi
fi

# Also try the uv-installed shim path if the global pkit wasn't found.
if [ -z "$SOURCE_KIT" ] && command -v uv >/dev/null 2>&1; then
    MAYBE_UV="$(uv run python -c "import project_kit; import pathlib; print(pathlib.Path(project_kit.__file__).resolve().parents[2] / '.pkit')" 2>/dev/null || true)"
    if [ -n "$MAYBE_UV" ] && [ -f "$MAYBE_UV/rules/core.md" ]; then
        SOURCE_KIT="$MAYBE_UV"
    fi
fi

if [ -z "$SOURCE_KIT" ]; then
    echo "  [warn] .pkit/rules/core.md not found and source kit not locatable." >&2
    echo "         Run 'pkit sync' or 'pkit upgrade' to propagate the rules area." >&2
    exit 1
fi

mkdir -p "$RULES_DIR"
cp "$SOURCE_KIT/rules/README.md" "$RULES_DIR/README.md" 2>/dev/null || true
cp "$SOURCE_KIT/rules/core.md"   "$CORE_MD"
echo "  [ok] .pkit/rules/core.md propagated from source kit"
