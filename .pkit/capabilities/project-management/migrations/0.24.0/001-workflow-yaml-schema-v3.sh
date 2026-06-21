#!/usr/bin/env bash
# project-management 0.24.0 — workflow.yaml schema_version 2 → 3.
#
# DEC-033 rebinds the issue lifecycle onto the shared process substrate
# (COR-033) as a keyed process (COR-032). The schema bump restructures
# `workflow.yaml`: `states` + `transitions` move under a top-level
# `process:` block (with `id`, `version`, `subject: {cardinality: keyed,
# key: issue-number}`); each state's `inferred_from` prose becomes
# `detection: {mode: inferred, predicate: {run: <detector>}}`; each gated
# transition gains `gate: {kind, predicate: {run: <check>}}` (checkbox
# close-gate → deterministic; PR-merge → authorisation-artifact). The
# pm-local blocks (`cascade`, `closure_triggers`) and pm-local fields
# stay.
#
# The kit-shipped `workflow.yaml` under `.pkit/capabilities/project-
# management/schemas/` is delivered by sync (it lives in the kit-owned
# tree). Adopters who haven't customised the file get the v3 version
# directly from sync — no migration action needed on their part.
#
# WARN-ON-OVERRIDE ONLY (DEC-033 D6): this migration's only job is to
# detect the case where an adopter has overridden the kit-shipped
# `workflow.yaml` (a `project/schema-overrides/workflow.yaml`) still at
# schema_version 2 and surface a warning so they can hand-update it. It
# NEVER rewrites the kit-shipped file (sync owns it) and NEVER auto-edits
# a project-owned override (that would silently clobber adopter intent —
# the no-shared-files invariant + the COR-010 discipline).
#
# Idempotent: no override, or an override already at schema_version 3 →
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
if [ "$current_kit_version" != "3" ]; then
    echo "  [warn] kit-shipped workflow.yaml schema_version is $current_kit_version (expected 3); sync may not have completed"
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
if [ "$override_version" = "3" ]; then
    echo "  [ok] adopter override at $WORKFLOW_OVERRIDE already at schema_version 3"
    exit 0
fi

# Print a structured warning. The adopter must hand-edit their override to
# the v3 process-substrate shape. We do NOT auto-edit project-owned
# overrides (no-shared-files invariant + COR-010 discipline).
cat <<EOF
  [warn] adopter override of workflow.yaml needs manual migration:

    File: $WORKFLOW_OVERRIDE
    Current schema_version: $override_version
    Required schema_version: 3

  Required changes per DEC-033 (rebind onto the process substrate):

    1. Bump \`schema_version\` to 3.

    2. Move \`states\` + \`transitions\` under a new top-level \`process:\` block,
       and add the process header:

         process:
           id: issue-lifecycle
           version: 3
           subject:
             cardinality: keyed
             key: issue-number
           states: [ ... ]        # moved from top level
           transitions: [ ... ]   # moved from top level

    3. On EACH state, replace the \`inferred_from:\` prose with a \`detection:\`
       predicate (the detector reproduces the same inference):

         detection:
           mode: inferred
           predicate:
             run: detect-<state-id>      # detect-todo / detect-backlog / ...

       Keep \`done\` ordered first and \`todo\` last (state order is load-bearing:
       the engine returns the first matching detection). Mark \`todo\` with
       \`entry: true\` and \`done\` with \`terminal: true\`.

    4. On each GATED transition, add a \`gate:\`:

         review → done           gate: {kind: authorisation-artifact, predicate: {run: gate-pr-merged}}
         {todo,backlog,in-progress} → done   gate: {kind: deterministic, predicate: {run: gate-checkboxes-ticked}}

       Rename each transition's \`command:\` value into a \`trigger:\` field too
       (keep \`command\` as the pm-local owner). Keep the pm-local fields
       (\`pr_state_effect\`, \`authorisation\`, \`executor\`, \`applies_to\`,
       \`severity\`, \`notes\`, \`display_name\`).

    5. Keep \`cascade\` and \`closure_triggers\` exactly where they are
       (top-level, pm-local; the engine ignores them).

  See:
    - $CAP_DIR/decisions/DEC-033-rebind-issue-lifecycle-onto-process-substrate.md
    - $KIT_WORKFLOW (the kit-shipped v3 reference)
    - $ROOT/.pkit/process/README.md (the substrate shape + engine contract)

  Migration cannot auto-edit project-owned overrides without risking
  silently clobbering adopter intent. Re-run \`pkit upgrade\` after editing
  the file; this migration becomes a no-op once your override declares
  schema_version: 3.
EOF

exit 0
