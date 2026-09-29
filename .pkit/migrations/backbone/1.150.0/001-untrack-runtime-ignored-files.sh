#!/usr/bin/env bash
# Backbone migration 1.150.0 — resource: untrack-runtime-ignored-files (#288).
#
# Each installed component's `runtime_ignore:` declaration is rendered into the
# pkit-owned `.pkit/.gitignore` (ADR-009 rule 7). An ignore rule does not untrack
# a file git already tracks, so an adopter who committed a runtime-local file —
# `sandbox-provenance.yaml`, a diagnose log, a `__pycache__/` — before its
# declaration shipped keeps it tracked for good. This migration removes every
# such file from the index, so the rendered ignore rule finally applies.
#
# Rules:
#   - INDEX ONLY. The only mutation is `git rm --cached`, which never touches the
#     working tree: these files are per-machine state (a provenance ledger, an
#     active profile), and a working-tree delete would destroy it. The removal is
#     staged for the operator to commit; nothing is committed here.
#   - DECLARED FILES ONLY. The set is exactly the tracked files the rendered
#     `.pkit/.gitignore` ignores — the whole aggregated declaration, and nothing
#     else. Git's own matcher decides, in a scratch repository whose only ignore
#     rules are that file: the adopter's root `.gitignore`, `.git/info/exclude`
#     (where private visibility hides all of `.pkit/`) and global excludes
#     cannot widen or hide the set. A tracked file no component declares, such
#     as a capability's shared `config.yaml`, is never touched. No path is
#     named here; the backbone owns the aggregation, each component its paths.
#   - The upgrade runs sync, which re-renders `.pkit/.gitignore` from the
#     current declarations, before backbone migrations, so the file read here is
#     current.
#   - BOUNDED like `pkit visibility untrack` (ADR-009 rule 5): skipped while a
#     merge, rebase, cherry-pick or revert is in progress, and a path git
#     refuses to untrack (staged content matching neither HEAD nor the working
#     copy, which forcing would drop; or a locked index) is left tracked. Both
#     are reported with the command to finish by hand, and never fail the
#     upgrade: sync has already recorded the new version, so a halted migration
#     would not run again. Unlike that verb it asks no confirmation: a declared
#     file is one its component says must not be tracked, and the removal is
#     only staged, so the operator's commit is the point of decision.
#
# OTHER CLONES. The staged removal, once committed, reaches other clones as a
# deletion. A clone that pulls it while the file is still tracked there has git
# delete its own copy (#284); a clone that untracks the same paths first keeps
# its copy. No migration runs in the clone that pulls, so the report says so.
#
# Idempotent: once nothing declared is tracked, a re-run reports that and
# changes nothing.

set -euo pipefail

# ROOT is the adopter's project root, provided by the runtime.
: "${ROOT:?ROOT must be set by the upgrade runtime}"

# Resolve every repository from its directory, never from an inherited git
# environment (e.g. a hook's GIT_DIR), which would redirect both the adopter
# commands and the scratch repository below.
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_COMMON_DIR

RENDERED="$ROOT/.pkit/.gitignore"
LIST_LIMIT=20

if ! command -v git >/dev/null 2>&1 \
    || ! git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "  [skip] $ROOT is not a git work tree — nothing is tracked"
    exit 0
fi

if [ ! -f "$RENDERED" ]; then
    echo "  [skip] no .pkit/.gitignore is rendered — no runtime-ignore declaration to apply"
    exit 0
fi

scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT

# The scratch repository: the rendered file at the same place, and no other
# ignore source. Its case-sensitivity follows the adopter's repository.
git -c init.defaultBranch=scratch init -q "$scratch/repo"
mkdir -p "$scratch/repo/.git/info" "$scratch/repo/.pkit"
: > "$scratch/repo/.git/info/exclude"
cp "$RENDERED" "$scratch/repo/.pkit/.gitignore"
ignore_case="$(git -C "$ROOT" config --bool core.ignoreCase 2>/dev/null || echo false)"

git -C "$ROOT" ls-files -z -- .pkit/ > "$scratch/tracked"

# check-ignore exits 1 when nothing matches; anything above 1 is an error.
status=0
git -C "$scratch/repo" -c core.excludesFile=/dev/null -c core.ignoreCase="$ignore_case" \
    check-ignore --no-index -z --stdin < "$scratch/tracked" > "$scratch/declared" || status=$?
if [ "$status" -gt 1 ]; then
    echo "  [warn] could not match tracked files against .pkit/.gitignore (git check-ignore exited $status);" >&2
    echo "         nothing was untracked. Tracked files under .pkit/ that an ignore file matches:" >&2
    echo "           git ls-files -ci --exclude-per-directory=.gitignore -- .pkit/" >&2
    exit 0
fi

declared=()
while IFS= read -r -d '' path; do
    declared+=("$path")
done < "$scratch/declared"

if [ ${#declared[@]} -eq 0 ]; then
    echo "  exists  no runtime-ignored file is tracked — nothing to untrack"
    exit 0
fi

# The removal a caller must finish by hand, as one pasteable line: literal
# pathspecs, each path shell-quoted.
_manual_command() {
    local line="git --literal-pathspecs rm --cached --" path
    for path in "$@"; do
        line+=" $(printf '%q' "$path")"
    done
    echo "           $line"
}

busy=""
for marker in MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD rebase-merge rebase-apply; do
    marker_path="$(git -C "$ROOT" rev-parse --git-path "$marker")"
    case "$marker_path" in
        /*) ;;
        *) marker_path="$ROOT/$marker_path" ;;
    esac
    if [ -e "$marker_path" ]; then
        busy="$marker"
        break
    fi
done
if [ -n "$busy" ]; then
    echo "  [warn] ${#declared[@]} runtime-ignored file(s) are tracked, but the repository is mid-operation ($busy)." >&2
    echo "         Left tracked, so the removal does not join that operation. Once it is finished, run:" >&2
    _manual_command "${declared[@]}" >&2
    exit 0
fi

# `git rm` is all-or-nothing: one refused path aborts the whole call. Try the
# batch; on refusal, go path by path so the rest still move and the refused
# ones are named. Git's own message is not relayed: it suggests `-f`, which
# would drop the staged content.
untracked=()
refused=()
if git -C "$ROOT" --literal-pathspecs rm --cached --quiet -- "${declared[@]}" 2>/dev/null; then
    untracked=("${declared[@]}")
else
    for path in "${declared[@]}"; do
        if git -C "$ROOT" --literal-pathspecs rm --cached --quiet -- "$path" 2>/dev/null; then
            untracked+=("$path")
        else
            refused+=("$path")
        fi
    done
fi

shown=0
for path in ${untracked[@]+"${untracked[@]}"}; do
    if [ "$shown" -eq "$LIST_LIMIT" ]; then
        echo "  untracked  … and $(( ${#untracked[@]} - LIST_LIMIT )) more (see \`git status\`)"
        break
    fi
    echo "  untracked  $path (index only; working copy untouched)"
    shown=$((shown + 1))
done
if [ ${#refused[@]} -gt 0 ]; then
    echo "  [warn] left tracked — git refused to untrack (staged content that matches neither HEAD nor" >&2
    echo "         the working copy, or a locked index):" >&2
    for path in "${refused[@]}"; do
        echo "           $path" >&2
    done
    echo "         Commit or unstage that content (or let the other git process finish), then run:" >&2
    _manual_command "${refused[@]}" >&2
fi
if [ ${#untracked[@]} -gt 0 ]; then
    echo "  note    staged, not committed — commit the removal. Another clone that pulls that commit while"
    echo "          it still tracks these files has git delete its copies: run \`git rm --cached\` on them"
    echo "          there first, or copy them aside."
fi
echo "  untrack-runtime-ignored-files: ${#untracked[@]} untracked, ${#refused[@]} left tracked"
