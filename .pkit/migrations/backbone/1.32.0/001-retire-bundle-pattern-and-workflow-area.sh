#!/usr/bin/env bash
# Backbone migration — retire the bundle pattern and the workflow area per COR-027.
#
# COR-027 supersedes COR-005's bundle half: capabilities (COR-017) subsumed the
# alternative-implementations use case; alternative variants now live as
# capability-internal data, not as filesystem-level bundles. This migration
# handles the adopter-state side of the retirement.
#
# What the copy handles (no migration action needed):
#   .pkit/workflow/ (kit-shipped)                    → removed from kit content
#   .pkit/skills/core/bundle-author.md               → removed
#
# What this migration handles, each only on a positive sign that it is the
# retired bundle's (COR-010), never by a path's name or position alone:
#
#   1. The `kind: bundle` entries of .pkit/manifest.yaml's `components:`
#      registry, which `pkit bundle install` wrote. Such an entry is the sign
#      for what follows: it names the bundle and its component manifest. The
#      entry is dropped whole, its own lines only, so the entry after it stays.
#
#   2. The bundle's component manifest under .pkit/manifests/components/, which
#      the same install stamped: a file a `kind: bundle` entry names, or one
#      that records `kind: bundle` itself. Removed. Any other file there stays.
#
#   3. .pkit/workflow/project/<bundle>/, the project-side folder of a bundle
#      the project recorded as installed. It is project-owned, and the copy
#      removes nothing the project wrote (COR-059 point 2), so this migration
#      removes it, and asks first (COR-027, "Migration"): only where standard
#      input and output are both terminals, and only on a yes. With nobody to
#      answer, or on any other answer, the folder stays, and the migration
#      says how to remove it by hand. Anything else under
#      .pkit/workflow/project/ is the project's and stays.
#
# A version transition may run this again over a project whose migration
# history is unknown (COR-059 point 6). With no `kind: bundle` record left, it
# finds no sign and changes nothing.
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

# The registry's entries, one block each: a `  - <key>: <value>` line and the
# `    <key>: <value>` lines below it. MODE `names` and `manifests` print that
# value of each `kind: bundle` entry. MODE `filter` prints the manifest with
# those entries dropped, every other line kept byte for byte.
bundle_entries() {
    awk -v mode="$1" '
        function value(line) {
            sub(/^ *(- )?[a-z_]+:[ \t]*/, "", line)
            sub(/[ \t]+$/, "", line)
            return line
        }
        function flush(   i) {
            if (n == 0) return
            if (bundle) {
                if (mode == "names" && name != "") print name
                if (mode == "manifests" && manifest != "") print manifest
            } else if (mode == "filter") {
                for (i = 1; i <= n; i++) print buf[i]
            }
            n = 0; bundle = 0; name = ""; manifest = ""
        }
        function take(line) {
            buf[++n] = line
            if (line ~ /^ *(- )?kind:[ \t]*bundle[ \t]*$/) bundle = 1
            if (line ~ /^ *(- )?name:/) name = value(line)
            if (line ~ /^ *(- )?manifest:/) manifest = value(line)
        }
        /^components:/ { flush(); inside = 1; if (mode == "filter") print; next }
        inside && /^  - / { flush(); take($0); next }
        inside && n > 0 && /^    [^ -]/ { take($0); next }
        {
            flush()
            if ($0 ~ /^[^ #]/) inside = 0
            if (mode == "filter") print
        }
        END { flush() }
    ' "$BACKBONE_MANIFEST"
}

# Whether standard input and output are both terminals, where a person can answer.
at_a_terminal() {
    [ -t 0 ] && [ -t 1 ]
}

changed=0
names=()
manifests=()
if [ -f "$BACKBONE_MANIFEST" ]; then
    while IFS= read -r name; do
        [ -n "$name" ] && names+=("$name")
    done < <(bundle_entries names)
    while IFS= read -r manifest; do
        [ -n "$manifest" ] && manifests+=("$manifest")
    done < <(bundle_entries manifests)
fi
registry_entries=${#names[@]}

# Step 2's second sign: a component manifest that records `kind: bundle`.
if [ -d "$MANIFESTS_DIR" ]; then
    for mf in "$MANIFESTS_DIR"/*.yaml; do
        [ -f "$mf" ] || continue
        if grep -qE '^[[:space:]]*kind:[[:space:]]*bundle[[:space:]]*$' "$mf"; then
            manifests+=("${mf#"$ROOT"/}")
            names+=("$(basename "$mf" .yaml)")
        fi
    done
fi

# Step 3: the project-side folder of each bundle the project recorded.
removed_folder=0
seen=" "
for name in ${names[@]+"${names[@]}"}; do
    case "$name" in */* | . | .. | "") continue ;; esac
    case "$seen" in *" $name "*) continue ;; esac
    seen="$seen$name "
    folder="$WORKFLOW_PROJECT_DIR/$name"
    [ -d "$folder" ] || continue
    rel=".pkit/workflow/project/$name/"
    answer=""
    if at_a_terminal; then
        printf '  Remove %s, the project-side folder of the retired bundle %s (COR-027)? Git keeps what it holds. [y/N] ' "$rel" "$name"
        read -r answer || answer=""
    fi
    case "$answer" in
        y | Y | yes | YES)
            rm -rf "$folder"
            echo "  [remove] $rel (the retired bundle's project-side folder)"
            removed_folder=$((removed_folder + 1))
            changed=$((changed + 1))
            ;;
        *)
            if at_a_terminal; then
                echo "  [keep] $rel (kept, as answered)"
            else
                echo "  [keep] $rel (the retired bundle's project-side folder; nobody here to ask)"
            fi
            echo "         It is unused since COR-027. To remove it: rm -rf $rel"
            ;;
    esac
done
if [ "$removed_folder" -gt 0 ]; then
    # Only a folder left empty goes: anything else the project put there stays.
    rmdir "$WORKFLOW_PROJECT_DIR" 2>/dev/null || true
    rmdir "$WORKFLOW_DIR" 2>/dev/null || true
fi

# Step 2: the bundle's component manifests.
for manifest in ${manifests[@]+"${manifests[@]}"}; do
    case "$manifest" in
        .pkit/manifests/components/*.yaml) ;;
        *) continue ;;
    esac
    path="$ROOT/$manifest"
    if [ -f "$path" ]; then
        rm -f "$path"
        echo "  [remove] $manifest (legacy bundle component manifest)"
        changed=$((changed + 1))
    fi
done
if [ -d "$MANIFESTS_DIR" ]; then
    rmdir "$MANIFESTS_DIR" 2>/dev/null || true
    rmdir "$PKIT_DIR/manifests" 2>/dev/null || true
fi

# Step 1: drop the `kind: bundle` registry entries, each block whole.
if [ "$registry_entries" -gt 0 ]; then
    bundle_entries filter > "$BACKBONE_MANIFEST.tmp"
    mv "$BACKBONE_MANIFEST.tmp" "$BACKBONE_MANIFEST"
    echo "  [edit] .pkit/manifest.yaml (dropped $registry_entries bundle component entr(ies))"
    changed=$((changed + 1))
fi

if [ "$changed" -eq 0 ]; then
    echo "  [skip] no bundle state recorded; already migrated or never present"
    exit 0
fi

echo "  [ok] retired $changed bundle/workflow artifact(s); COR-027 fulfilled"
