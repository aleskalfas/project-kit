#!/usr/bin/env bash
#
# Deploy .pkit/skills/{core,project}/ skills as symlinks under
# .claude/skills/<name>/SKILL.md so Claude Code can load them.
#
# Part of the Claude Code adapter (.pkit/adapters/claude-code/) per
# COR-005's adapter pattern. Sibling scripts for other harnesses (Codex,
# Cursor) would live alongside under their own .pkit/adapters/<harness>/
# directory.
#
# Source layout (per COR-015 + COR-020):
# - Flat (atomic skill): .pkit/skills/<ns>/<name>.md
# - Folder (composite skill): .pkit/skills/<ns>/<name>/<name>.md
#   plus sibling supporting files (sub-procedure walkthroughs per
#   COR-020, scripts, templates, reference docs per COR-015).
#
# Destination layout (Claude Code's expectation):
# - .claude/skills/<name>/SKILL.md   (symlink to the source's canonical file)
# - .claude/skills/<name>/<sibling>  (symlink to each supporting sibling, for
#                                    composite skills per COR-020)
#
# The destination is always the per-name directory + SKILL.md file
# symlink for the canonical; composite skills additionally get one
# symlink per sibling file so the harness can read the sub-procedure
# walkthroughs the dispatcher delegates to.
#
# Behavior:
# - Project namespace wins on collision (per COR-005).
# - Capability skills deploy only for the capabilities registered in the
#   backbone manifest (.pkit/manifest.yaml), not for every directory under
#   .pkit/capabilities/: a capability unregistered in place keeps its subtree
#   on disk, and its skills must stop deploying all the same.
# - Idempotent: correct symlinks report "exists"; mismatched kit-managed
#   symlinks are updated; stale kit-managed symlinks (a skill no longer
#   shipped by core, project or a registered capability — its source gone, or
#   its capability unregistered) are removed.
# - Legacy `.claude/skills/<name>` directory-symlinks (the pre-COR-015
#   form pointing to the source folder) are detected and replaced with
#   the new structure.
# - Adopter content (non-symlink files/dirs, or symlinks pointing
#   outside .pkit/skills/) is left untouched and reported "skipped".
# - A listed skill whose canonical file doesn't resolve (e.g. a composite
#   folder mid-build with sub-procedures but no <name>/<name>.md dispatcher
#   per COR-020) is skipped loudly with remediation — it does NOT abort the
#   run (#537). Valid skills still deploy; the run exits 0 with a summary.
# - Output uses tagged status lines: created, updated, exists, removed,
#   skipped, error.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
KIT_SKILLS="$ROOT/.pkit/skills"
KIT_CAPABILITIES="$ROOT/.pkit/capabilities"
CLAUDE_SKILLS="$ROOT/.claude/skills"

mkdir -p "$CLAUDE_SKILLS"

status() { printf "  %-10s %s\n" "$1" "$2"; }

# The capability names registered in the backbone manifest, one per line.
# Empty if the manifest is missing or registers no capability. The same parser
# as merge-settings.sh's list_installed_capabilities: it depends on the
# manifest's documented field ordering (kind: before name:), which is
# core-generated and stable.
list_registered_capabilities() {
    local manifest="$ROOT/.pkit/manifest.yaml"
    [ -f "$manifest" ] || return 0
    awk '
        /^[[:space:]]*-[[:space:]]*kind:[[:space:]]*capability[[:space:]]*$/ {
            in_capability = 1
            next
        }
        /^[[:space:]]*-[[:space:]]*kind:/ {
            in_capability = 0
            next
        }
        in_capability && match($0, /^[[:space:]]+name:[[:space:]]*[^[:space:]]+/) {
            sub(/^[[:space:]]+name:[[:space:]]*/, "")
            print
            in_capability = 0
        }
    ' "$manifest"
}

REGISTERED_CAPABILITIES="$(list_registered_capabilities | sort -u)"

# Every folder skills ship from, one per line, in precedence order: project
# (wins on collision), core, then the skills/ folder of each *registered*
# capability by name — capability skills after core/project per COR-017's
# collision rules (already-installed project skills win over capability
# skills, surfaced at install time). The one place the registered-only rule
# applies; every resolver below walks this list.
skill_locations() {
    echo "$KIT_SKILLS/project"
    echo "$KIT_SKILLS/core"
    local cap
    while IFS= read -r cap; do
        if [ -n "$cap" ] && [ -d "$KIT_CAPABILITIES/$cap/skills" ]; then
            echo "$KIT_CAPABILITIES/$cap/skills"
        fi
    done <<<"$REGISTERED_CAPABILITIES"
}

# Resolve a skill name to the source that deploys: the first location in
# skill_locations shipping it, flat form preferred over folder form within a
# location per COR-015's atomic-is-flat bias. Prints "<form> <canonical file>",
# form `flat` or `folder`. Returns 1 if the name is in no location.
resolve_skill() {
    local name="$1"
    local dir
    while IFS= read -r dir; do
        if [ -f "$dir/$name.md" ]; then
            echo "flat $dir/$name.md"
            return 0
        elif [ -f "$dir/$name/$name.md" ]; then
            echo "folder $dir/$name/$name.md"
            return 0
        fi
    done < <(skill_locations)
    return 1
}

# Compute the relative path from .claude/skills/<name>/ to a source
# file inside .pkit/{skills|capabilities}/. The destination directory
# is 3 levels deep (.claude/skills/<name>/), so the prefix is `../../../`.
relative_source_path() {
    local absolute="$1"
    local rel="${absolute#"$ROOT"/}"
    echo "../../../$rel"
}

# The skill's expected source path, in the relative form the
# .claude/skills/<name>/SKILL.md symlink carries. Returns 1 if the name
# resolves to no source.
expected_for() {
    local form canonical
    read -r form canonical < <(resolve_skill "$1") || return 1
    relative_source_path "$canonical"
}

# The skill's source folder when the source that deploys is folder-form (e.g.,
# /repo/.pkit/skills/core/schema) — the folder whose siblings deploy beside its
# SKILL.md. Returns 1 for a flat source, or a name that resolves to none.
source_folder_for() {
    local form canonical
    read -r form canonical < <(resolve_skill "$1") || return 1
    [ "$form" = "folder" ] || return 1
    dirname "$canonical"
}

# Deduped list of skill names across every location in skill_locations, in
# either flat or folder form.
list_kit_names() {
    local dir entry name
    while IFS= read -r dir; do
        [ -d "$dir" ] || continue
        for entry in "$dir"/*; do
            [ -e "$entry" ] || continue
            name="$(basename "$entry")"
            if [ -f "$entry" ] && [[ "$name" == *.md ]]; then
                echo "${name%.md}"
            elif [ -d "$entry" ]; then
                echo "$name"
            fi
        done
    done < <(skill_locations) | sort -u
}

# Pass 0: clean up legacy `.claude/skills/<name>` directory-symlinks
# (the pre-COR-015 form pointing at a kit source directory). The new
# structure replaces these with `.claude/skills/<name>/SKILL.md` file
# symlinks.
shopt -s nullglob
for entry in "$CLAUDE_SKILLS"/*; do
    [ -L "$entry" ] || continue
    current="$(readlink "$entry")"
    [[ "$current" == ../../.pkit/skills/* ]] || continue
    # Legacy directory-symlink: remove it so the new structure can be created.
    rm "$entry"
    status "migrated" ".claude/skills/$(basename "$entry") (legacy dir-symlink removed)"
done
shopt -u nullglob

# Pass 1: ensure every kit skill has the right .claude/skills/<name>/SKILL.md symlink,
# plus per-sibling symlinks for composite skills (folder-form with supporting siblings).
skipped=0
while IFS= read -r name; do
    [ -n "$name" ] || continue
    # Guard the resolution: expected_for returns 1 when a name resolves to
    # no canonical file, and under `set -e` an unguarded command
    # substitution would abort the whole run on that benign non-zero — with
    # no diagnostic and no `Done.` (#537). Capture-or-empty, then branch.
    expected="$(expected_for "$name")" || expected=""
    if [ -z "$expected" ]; then
        # The name was listed (a folder exists) but no canonical file
        # resolved. The normal cause is a composite skill folder mid-build
        # (COR-020): sub-procedures present, but no <name>/<name>.md
        # dispatcher yet. Skip THIS skill loudly with remediation and
        # deploy the rest — one half-built incubated skill must not brick a
        # whole-project sync/upgrade.
        status "skipped" "$name — composite skill folder skills/$name/ has sub-procedures but no canonical skills/$name/$name.md dispatcher (COR-020)."
        printf "  %s\n" "         Add the dispatcher:  create .pkit/skills/<ns>/$name/$name.md"
        skipped=$((skipped + 1))
        continue
    fi
    target_dir="$CLAUDE_SKILLS/$name"
    target="$target_dir/SKILL.md"

    mkdir -p "$target_dir"

    if [ -L "$target" ]; then
        current="$(readlink "$target")"
        if [ "$current" = "$expected" ]; then
            status "exists" ".claude/skills/$name/SKILL.md"
        elif [[ "$current" == ../../../.pkit/skills/* ]] || [[ "$current" == ../../../.pkit/capabilities/* ]]; then
            rm "$target"
            ln -s "$expected" "$target"
            status "updated" ".claude/skills/$name/SKILL.md -> $expected"
        else
            status "skipped" ".claude/skills/$name/SKILL.md (user symlink -> $current)"
        fi
    elif [ -e "$target" ]; then
        status "skipped" ".claude/skills/$name/SKILL.md (user content)"
    else
        ln -s "$expected" "$target"
        status "created" ".claude/skills/$name/SKILL.md -> $expected"
    fi

    # For composite skills (folder-form with supporting siblings per
    # COR-020), symlink each sibling into the destination so the
    # harness can read sub-procedure walkthroughs / scripts / templates
    # the dispatcher delegates to.
    source_folder="$(source_folder_for "$name" 2>/dev/null || true)"
    if [ -n "$source_folder" ]; then
        canonical_name="$name.md"
        shopt -s nullglob
        for entry in "$source_folder"/*; do
            entry_name="$(basename "$entry")"
            # Skip the canonical file — already handled above as SKILL.md.
            [ "$entry_name" = "$canonical_name" ] && continue
            sibling_target="$target_dir/$entry_name"
            sibling_expected="$(relative_source_path "$entry")"

            if [ -L "$sibling_target" ]; then
                current="$(readlink "$sibling_target")"
                if [ "$current" = "$sibling_expected" ]; then
                    status "exists" ".claude/skills/$name/$entry_name"
                elif [[ "$current" == ../../../.pkit/skills/* ]] || [[ "$current" == ../../../.pkit/capabilities/* ]]; then
                    rm "$sibling_target"
                    ln -s "$sibling_expected" "$sibling_target"
                    status "updated" ".claude/skills/$name/$entry_name -> $sibling_expected"
                else
                    status "skipped" ".claude/skills/$name/$entry_name (user symlink -> $current)"
                fi
            elif [ -e "$sibling_target" ]; then
                status "skipped" ".claude/skills/$name/$entry_name (user content)"
            else
                ln -s "$sibling_expected" "$sibling_target"
                status "created" ".claude/skills/$name/$entry_name -> $sibling_expected"
            fi
        done
        shopt -u nullglob
    fi
done < <(list_kit_names)

# Pass 2: remove stale kit-managed deploys.
# - For each .claude/skills/<name>/ directory containing a kit-managed
#   SKILL.md symlink: if the name no longer resolves — its source is gone, or
#   the capability shipping it is no longer registered — remove the whole
#   deployed skill (SKILL.md + any kit-managed sibling symlinks).
# - For skills that still resolve: remove any kit-managed sibling symlink
#   the source no longer has (e.g., a sub-procedure file removed by a skill
#   refactor; or every sibling, when the name now resolves to a flat skill —
#   say an unregistered capability's composite skill giving way to a
#   same-named flat one).
# Adopter content — a real file or directory, or a symlink pointing anywhere
# but into .pkit/skills/ or .pkit/capabilities/ — is never touched.
shopt -s nullglob
for skill_dir in "$CLAUDE_SKILLS"/*; do
    [ -d "$skill_dir" ] || continue
    name="$(basename "$skill_dir")"
    inner="$skill_dir/SKILL.md"
    [ -L "$inner" ] || continue
    current="$(readlink "$inner")"
    [[ "$current" == ../../../.pkit/skills/* ]] || [[ "$current" == ../../../.pkit/capabilities/* ]] || continue

    if ! expected_for "$name" >/dev/null 2>&1; then
        # Source skill is gone — remove every kit-managed symlink in
        # this skill's directory, then drop the directory if empty.
        for entry in "$skill_dir"/*; do
            [ -L "$entry" ] || continue
            entry_link="$(readlink "$entry")"
            if [[ "$entry_link" == ../../../.pkit/skills/* ]] || [[ "$entry_link" == ../../../.pkit/capabilities/* ]]; then
                rm "$entry"
            fi
        done
        rmdir "$skill_dir" 2>/dev/null || true
        status "removed" ".claude/skills/$name (no longer shipped by core, project or a registered capability)"
    else
        # The skill still resolves. Check each kit-managed sibling symlink
        # against its source folder and remove any the source no longer has —
        # every one, when the source is flat and so has no siblings.
        source_folder="$(source_folder_for "$name" 2>/dev/null || true)"
        for entry in "$skill_dir"/*; do
            [ -L "$entry" ] || continue
            entry_name="$(basename "$entry")"
            [ "$entry_name" = "SKILL.md" ] && continue
            entry_link="$(readlink "$entry")"
            if [[ "$entry_link" == ../../../.pkit/skills/* ]] || [[ "$entry_link" == ../../../.pkit/capabilities/* ]]; then
                if [ -z "$source_folder" ] || [ ! -e "$source_folder/$entry_name" ]; then
                    rm "$entry"
                    status "removed" ".claude/skills/$name/$entry_name (source sibling gone)"
                fi
            fi
        done
    fi
done
shopt -u nullglob

echo "Done."
if [ "$skipped" -gt 0 ]; then
    echo "  note: $skipped skill(s) skipped — unresolved canonical file; the rest deployed."
    echo "        → A composite skill folder needs a <name>/<name>.md dispatcher (COR-020)."
fi
