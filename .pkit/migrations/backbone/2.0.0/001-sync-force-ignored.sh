#!/usr/bin/env bash
# Backbone migration 2.0.0 — resource: sync-force-ignored.
#
# `pkit sync` now works at the version a project records and moves no version
# (COR-059, ADR-065). Its `--force` had one effect: copying an older capability
# over a newer one, which moved a recorded version down. So sync accepts the
# flag for this release, ignores it and says so, and a later release removes it
# (ADR-065 point 10). A flag whose meaning changes is one of COR-010's triggers,
# so the change ships this migration in the same change-set, as 1.140.0/001 did
# for the router shim.
#
# What this migration is (and is NOT):
#   - A GUIDANCE migration. The flag lives in the project's own files — a CI
#     workflow, a script, a task runner — never in state pkit records, so there
#     is nothing for pkit to rewrite. It looks for a file of the project's that
#     runs `pkit sync` with `--force` and says what the flag now does. It edits
#     nothing: the project's files are the project's to change.
#   - Its positive sign is such a file. It reads the files git tracks, or, outside
#     a git repository, the files under ROOT, leaving out the methodology's own
#     tree (`.pkit/`), whose documentation names the flag, and the agent
#     workspace.
#
# Idempotent and safe over any state (COR-010): it writes nothing, so running it
# again, over any state, prints the same guidance or the same clean line.

set -euo pipefail

# ROOT is the adopter's project root, provided by the runtime.
: "${ROOT:?ROOT must be set by the upgrade runtime}"

# `pkit sync`, then anything but a comment, then `--force`, on one line.
pattern='pkit[[:space:]]+sync[^#]*--force'

if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    found=$(git -C "$ROOT" grep -I -l -E "$pattern" -- . ':!.pkit' ':!.agent-workspace' || true)
else
    found=$(cd "$ROOT" && grep -rIlE "$pattern" \
        --exclude-dir=.git --exclude-dir=.pkit --exclude-dir=.agent-workspace \
        --exclude-dir=node_modules . || true)
fi

if [ -z "$found" ]; then
    echo "  [skip] no project file runs \`pkit sync --force\`; nothing to change"
    exit 0
fi

echo "  [warn] these files run \`pkit sync --force\`:" >&2
while IFS= read -r file; do
    echo "           ${file#./}" >&2
done <<<"$found"
echo "         Sync now ignores \`--force\` and says so, and a later release removes the" >&2
echo "         flag. It no longer copies a capability over a newer one: it copies each" >&2
echo "         capability only at the version the project records, and \`pkit upgrade\`" >&2
echo "         moves a capability, with its migrations. Drop \`--force\` from these lines." >&2
echo "         Sync also stops now under a pkit at another version than the project's:" >&2
echo "         a pipeline commits a pin, or installs the project's version of pkit." >&2

# Guidance delivered: editing the project's own files is the project's to do,
# so this is not a failure. Exit clean so `pkit upgrade` proceeds.
exit 0
