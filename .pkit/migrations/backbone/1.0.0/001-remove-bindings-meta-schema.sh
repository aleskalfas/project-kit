#!/usr/bin/env bash
# Backbone migration — structural: remove COR-022's bindings.yaml mechanism.
#
# Per COR-023 (superseding COR-022), the adopter-data binding mechanism
# uses an inline `binds_to:` field on each schema YAML rather than a
# separate `schemas/bindings.yaml` registry. This migration removes the
# three artefacts that shipped under the v1.28.0 (COR-022) shape:
#
#   1. The kit-shipped meta-schema:
#        .pkit/schemas/_defs/bindings.schema.json
#   2. The kit-shipped skill sub-procedure:
#        .pkit/skills/core/schema/bindings.md
#   3. Defensive: any leftover `schemas/bindings.yaml` files under
#      installed capabilities (adopters who experimented with the
#      v1.28.0 shape may have created one).
#
# Idempotent: re-running on already-migrated state is a no-op.

set -euo pipefail

: "${ROOT:?ROOT must be set by the upgrade runtime}"

removed=0

META_PATH="$ROOT/.pkit/schemas/_defs/bindings.schema.json"
if [ -f "$META_PATH" ]; then
    rm "$META_PATH"
    echo "  removed  .pkit/schemas/_defs/bindings.schema.json"
    removed=$((removed + 1))
fi

SKILL_PATH="$ROOT/.pkit/skills/core/schema/bindings.md"
if [ -f "$SKILL_PATH" ]; then
    rm "$SKILL_PATH"
    echo "  removed  .pkit/skills/core/schema/bindings.md"
    removed=$((removed + 1))
fi

# Defensive: remove any capability-side bindings.yaml that linger.
CAPS_DIR="$ROOT/.pkit/capabilities"
if [ -d "$CAPS_DIR" ]; then
    while IFS= read -r -d '' bp; do
        rm "$bp"
        rel="${bp#$ROOT/}"
        echo "  removed  $rel (obsolete per COR-023)"
        removed=$((removed + 1))
    done < <(find "$CAPS_DIR" -mindepth 4 -maxdepth 4 -type f -path "*/schemas/bindings.yaml" -print0 2>/dev/null)
fi

if [ "$removed" -eq 0 ]; then
    echo "  skip     nothing to remove (already migrated or never adopted v1.28.0)"
fi

exit 0
