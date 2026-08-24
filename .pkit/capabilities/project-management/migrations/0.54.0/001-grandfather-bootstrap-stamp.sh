#!/usr/bin/env bash
# project-management 0.54.0 — resource: grandfather an existing install's bootstrap stamp.
#
# WHY THIS MIGRATION EXISTS. At 0.54.0 the prerequisite gate (#747) becomes
# code: every pm verb except `bootstrap` / `pre-check` / `migrate` /
# `adopt-existing` / `self-test` refuses unless a bootstrap STAMP exists at
# `project/bootstrap-stamp.yaml`. Installs that predate 0.54.0 have no stamp —
# they were bootstrapped before the stamp existed — so without this migration a
# routine upgrade would make every previously-working command start refusing.
# That is exactly the adopter-breaking surface change COR-010 requires a
# same-change-set migration for.
#
# WHAT IT ATTESTS, HONESTLY. It writes `by: migration-grandfather`, which means
# "this install predates the gate and was in use, so bootstrap is PRESUMED to
# have run" — not "a bootstrap was observed". No local, network-free evidence
# can distinguish "installed and bootstrapped" from "installed but never
# bootstrapped", and inventing one would be the fail-open shape #747 closes.
# The honest trade is stated rather than hidden: an upgrade preserves the
# behaviour the adopter already had, and `pre-check` remains the surface that
# answers "is my setup actually healthy?".
#
# The grandfathered stamp deliberately carries NO `repo:` binding. A stamp
# written by `bootstrap` / `migrate` records the repository it was written for
# (so a copied stamp is inert); this one attests a presumption, so claiming a
# binding it never verified would over-claim. The next `bootstrap` or `migrate`
# replaces it with a bound stamp.
#
# Idempotent: an existing stamp (however written) is left completely untouched.
#
# Run via the upgrade runtime with ROOT=<adopter root>.

set -euo pipefail

# ROOT is the adopter's project root, provided by the runtime.
: "${ROOT:?ROOT must be set by the upgrade runtime}"

CAP_DIR="$ROOT/.pkit/capabilities/project-management"
STAMP="$CAP_DIR/project/bootstrap-stamp.yaml"
PACKAGE="$CAP_DIR/package.yaml"

if [ ! -d "$CAP_DIR" ]; then
    echo "  [skip] project-management capability not installed at $CAP_DIR"
    exit 0
fi

if [ -f "$STAMP" ]; then
    echo "  [ok] bootstrap stamp already present at $STAMP; left untouched"
    exit 0
fi

# The version to record: what is installed right now. Read from package.yaml's
# `component.version` — the same field the gate compares against for staleness,
# so a grandfathered stamp does not immediately read as stale.
version=$(awk '/^component:/{c=1;next} c&&/^  version:/{print $2;exit} /^[^ ]/{c=0}' "$PACKAGE" 2>/dev/null || true)
if [ -z "$version" ]; then
    version="unknown"
fi

completed_at=$(date -u +"%Y-%m-%dT%H:%M:%S+00:00")

mkdir -p "$CAP_DIR/project"
cat > "$STAMP" <<EOF
# Bootstrap completion stamp — machine-written, do NOT hand-edit.
# Written by the project-management 0.54.0 migration, which carried this
# pre-gate install forward so previously-working pm commands keep working
# (#747). \`by: migration-grandfather\` records that bootstrap is PRESUMED to
# have run here, not observed — run \`pkit project-management bootstrap\` (it is
# additive and idempotent) to replace this with a stamp that attests the real
# event, and \`pkit project-management pre-check\` to verify the state itself.
schema_version: 1
pkit_schema: project-management:bootstrap-stamp
bootstrap:
  completed_at: '$completed_at'
  capability_version: '$version'
  by: migration-grandfather
  repo:
EOF

echo "  [created] $STAMP (grandfathered pre-0.54.0 install at v$version)"
