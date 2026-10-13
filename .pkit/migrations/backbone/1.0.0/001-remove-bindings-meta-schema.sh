#!/usr/bin/env bash
# Backbone migration — structural: retire COR-022's bindings.yaml mechanism.
#
# Per COR-023 (superseding COR-022), the adopter-data binding mechanism
# uses an inline `binds_to:` field on each schema YAML rather than a
# separate `schemas/bindings.yaml` registry. Three artefacts shipped under
# the v1.28.0 (COR-022) shape:
#
#   1. The kit-shipped meta-schema:
#        .pkit/schemas/_defs/bindings.schema.json
#   2. The kit-shipped skill sub-procedure:
#        .pkit/skills/core/schema/bindings.md
#   3. A `schemas/bindings.yaml` a project wrote under an installed
#      capability, if it experimented with the v1.28.0 shape.
#
# The copy removes the first two: both sit in trees it refreshes, and it
# prunes a file there the methodology no longer ships, before any migration
# runs. The third is the project's own file, which nothing reads since
# COR-023. This migration removes nothing: it names each such file, so the
# project can delete it.
#
# Safe over any state (COR-010): a version transition may run it again over a
# project whose migration history is unknown. A file's name or place is no
# sign that the project no longer wants it, so a `bindings.yaml` under a
# capability's `project/`, or in a capability the project authored, stays.
#
# Idempotent: re-running changes nothing.

set -euo pipefail

: "${ROOT:?ROOT must be set by the upgrade runtime}"

CAPS_DIR="$ROOT/.pkit/capabilities"
found=0

if [ -d "$CAPS_DIR" ]; then
    while IFS= read -r -d '' bp; do
        rel="${bp#"$ROOT"/}"
        echo "  [note] $rel is unused since COR-023 (inline binds_to:); remove it if the project no longer needs it"
        found=$((found + 1))
    done < <(find "$CAPS_DIR" -type f -path "*/schemas/bindings.yaml" -print0 2>/dev/null | sort -z)
fi

if [ "$found" -eq 0 ]; then
    echo "  [skip] no bindings.yaml under .pkit/capabilities/; nothing to report"
fi

exit 0
