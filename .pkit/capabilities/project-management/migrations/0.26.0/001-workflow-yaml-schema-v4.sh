#!/usr/bin/env bash
# project-management 0.26.0 — workflow.yaml schema_version 3 → 4.
#
# DEC-034 rebinds pm's CLOSURE cascade onto the shared cascade slot
# (COR-037). The schema bump adds a SHARED-shape `cascade` declaration
# INSIDE the `process:` block (`process.cascade`) — child = the issue
# process, reducer `all` over the terminal `done`, `on_empty: satisfied`,
# with `members` + `membership` predicates — and MOVES the old `closure`
# sub-block OUT of the top-level pm-local `cascade:` block (which now
# carries only `forward` / `downward`). The engine reads ONLY
# `process.cascade`; the top-level `cascade:` sibling stays wrapper-driven.
#
# The kit-shipped `workflow.yaml` under `.pkit/capabilities/project-
# management/schemas/` is delivered by sync (it lives in the kit-owned
# tree). Adopters who haven't customised the file get the v4 version
# directly from sync — no migration action needed on their part.
#
# WARN-ON-OVERRIDE ONLY (DEC-034, reusing DEC-033 D6's posture): this
# migration's only job is to detect the case where an adopter has
# overridden the kit-shipped `workflow.yaml` (a `project/schema-overrides/
# workflow.yaml`) still at schema_version < 4 and surface a warning so they
# can hand-update it. It NEVER rewrites the kit-shipped file (sync owns it)
# and NEVER auto-edits a project-owned override (that would silently clobber
# adopter intent — the no-shared-files invariant + the COR-010 discipline).
#
# Idempotent: no override, or an override already at schema_version 4 →
# exit clean. Re-runs are no-ops.
#
# Run via the upgrade runtime with ROOT=<adopter root>.

set -euo pipefail

: "${ROOT:?ROOT must be set by the upgrade runtime}"

CAP_DIR="$ROOT/.pkit/capabilities/project-management"
PROJECT_OVERRIDES_DIR="$CAP_DIR/project/schema-overrides"
WORKFLOW_OVERRIDE="$PROJECT_OVERRIDES_DIR/workflow.yaml"
KIT_WORKFLOW="$CAP_DIR/schemas/workflow.yaml"

if [ ! -d "$CAP_DIR" ]; then
    echo "  [skip] project-management capability not installed at $CAP_DIR"
    exit 0
fi

# Kit-shipped workflow.yaml is updated by sync; we only verify the bump landed.
if [ ! -f "$KIT_WORKFLOW" ]; then
    echo "  [warn] kit-shipped workflow.yaml not found at $KIT_WORKFLOW; sync may not have completed"
    exit 0
fi

current_kit_version=$(grep -E '^schema_version:' "$KIT_WORKFLOW" | head -1 | awk '{print $2}')
if [ "$current_kit_version" != "4" ]; then
    echo "  [warn] kit-shipped workflow.yaml schema_version is $current_kit_version (expected 4); sync may not have completed"
    exit 0
fi

# Detect an adopter override (the only place project-owned customisation
# lives is the schema-overrides subdir; absent on adopters who haven't
# customised — the dominant case).
if [ ! -f "$WORKFLOW_OVERRIDE" ]; then
    echo "  [ok] no adopter override of workflow.yaml; nothing to migrate"
    exit 0
fi

override_version=$(grep -E '^schema_version:' "$WORKFLOW_OVERRIDE" | head -1 | awk '{print $2}')
if [ "$override_version" = "4" ]; then
    echo "  [ok] adopter override at $WORKFLOW_OVERRIDE already at schema_version 4"
    exit 0
fi

# Print a structured warning. The adopter must hand-edit their override to
# the v4 shape. We do NOT auto-edit project-owned overrides (no-shared-files
# invariant + COR-010 discipline).
cat <<EOF
  [warn] adopter override of workflow.yaml needs manual migration:

    File: $WORKFLOW_OVERRIDE
    Current schema_version: $override_version
    Required schema_version: 4

  Required changes per DEC-034 (rebind the CLOSURE cascade onto the shared
  cascade slot, COR-037). NOTE: if your override is still at schema_version 2,
  apply the DEC-033 v3 changes first (see the 0.24.0 migration), then these:

    1. Bump \`schema_version\` to 4.

    2. Add the SHARED \`cascade\` declaration INSIDE the \`process:\` block
       (a sibling of \`states\` / \`transitions\` — this is the one the engine
       reads, \`process.cascade\`):

         process:
           # ... id / version / subject / states / transitions ...
           cascade:
             runs: project-management:issue-lifecycle
             members:    { run: cascade-members }
             membership: { run: cascade-membership }
             reducer:    { op: all, outcome: done }
             on_empty:   satisfied

       Bump \`process.version\` to 4 to match.

    3. In the TOP-LEVEL pm-local \`cascade:\` block (the sibling of \`process:\`),
       REMOVE the \`closure:\` sub-block — closure now lives in the shared
       \`process.cascade\` above. Keep \`forward:\` and \`downward:\` as they were.

    4. Keep \`closure_triggers\` and all pm-local state/transition fields exactly
       where they are (the engine ignores them).

  The two same-named \`cascade\` constructs are disambiguated by NESTING:
  \`process.cascade\` (engine-read, the closure fold) vs the top-level
  \`cascade:\` sibling (wrapper-only, forward/downward).

  See:
    - $CAP_DIR/decisions/DEC-034-cascade-slot-binding.md
    - $KIT_WORKFLOW (the kit-shipped v4 reference)
    - $ROOT/.pkit/process/README.md (the substrate shape + cascade contract)

  Migration cannot auto-edit project-owned overrides without risking
  silently clobbering adopter intent. Re-run \`pkit upgrade\` after editing
  the file; this migration becomes a no-op once your override declares
  schema_version: 4.
EOF

exit 0
