#!/usr/bin/env bash
# project-management 0.55.0 — resource: default-branch-to-backbone.
#
# The default branch is declared once, for every reader, in the backbone
# configuration: `repository.default-branch` in `.pkit/project/config.yaml`,
# `main` when absent (COR-054 point 1). project-management kept its own
# `default_branch` in its project config, required until now; this migration
# retires it — the upgrade writer COR-054 point 1 names, the upgrade being the
# consent (COR-048 point 5):
#
#   - a value other than `main`, while the backbone declares no default branch,
#     is carried over to `repository.default-branch`;
#   - `main` is the backbone's default, so nothing is written for it;
#   - a default branch the backbone already declares wins: nothing is written;
#   - project-management's key is removed in each of those cases.
#
# Never a guess: where the value cannot be carried over — the backbone's file is
# one flow-style mapping, or declares `repository` without `default-branch`, so
# a block cannot be appended; or the value is not a branch name the backbone
# takes — nothing is written and the key is kept, so project-management keeps
# reading it (with a warning) until it is declared by hand; the migration says
# how. Read without a YAML parser because the runtime guarantees only bash; any
# doubt leans towards leaving a file as it is.
#
# Idempotent: once the key is gone, every later run finds nothing to do.

set -euo pipefail

# ROOT is the adopter's project root, provided by the runtime.
: "${ROOT:?ROOT must be set by the upgrade runtime}"

PM_CONFIG="$ROOT/.pkit/capabilities/project-management/project/config.yaml"
CONFIG="$ROOT/.pkit/project/config.yaml"
# project-management's key as a block key at column 0, plain or quoted.
ALIAS_KEY_RE="^[\"']?default_branch[\"']?[[:space:]]*:"

if [ ! -f "$PM_CONFIG" ]; then
    echo "  exists  no project-management project config — no default_branch to retire"
    exit 0
fi

alias_line="$(grep -m 1 -E "$ALIAS_KEY_RE" "$PM_CONFIG" || true)"
if [ -z "$alias_line" ]; then
    if sed -e 's/^[[:space:]]*#.*$//' -e 's/[[:space:]]#.*$//' "$PM_CONFIG" \
        | grep -E "default_branch[\"']?[[:space:]]*:" >/dev/null; then
        echo "  [warn] project-management's project/config.yaml names default_branch in a form this migration does not edit"
        echo "         remove it by hand; declare the default branch once instead: pkit config set repository.default-branch <name> --yes"
        exit 0
    fi
    echo "  exists  project-management's default_branch is retired already"
    exit 0
fi

# The value: after the key, less a trailing comment and one pair of quotes.
value="$(printf '%s\n' "$alias_line" | sed -E \
    -e "s/$ALIAS_KEY_RE[[:space:]]*//" \
    -e 's/[[:space:]]+#.*$//' \
    -e 's/[[:space:]]+$//' \
    -e "s/^\"(.*)\"$/\\1/" \
    -e "s/^'(.*)'$/\\1/")"

remove_alias() {
    local tmp="$PM_CONFIG.tmp.$$"
    grep -vE "$ALIAS_KEY_RE" "$PM_CONFIG" > "$tmp" || true
    mv "$tmp" "$PM_CONFIG"
}

# The configuration with its comments blanked, so a commented-out key does not count.
config_without_comments() {
    sed -e 's/^[[:space:]]*#.*$//' -e 's/[[:space:]]#.*$//' "$CONFIG"
}

# Whether the configuration names a key, in block style or inside a flow mapping.
# (No `grep -q` or `head` in these pipelines: under `pipefail` a reader that
# stops early can kill the writer with SIGPIPE and fail the whole condition.)
declares() {
    local key="$1" text
    [ -f "$CONFIG" ] || return 1
    text="$(config_without_comments)"
    printf '%s\n' "$text" | grep -E "^[[:space:]]*[\"']?${key}[\"']?[[:space:]]*:" >/dev/null && return 0
    printf '%s\n' "$text" | tr '\n' ' ' \
        | grep -E "[{,][[:space:]]*[\"']?${key}[\"']?[[:space:]]*:" >/dev/null
}

# Whether the document's root is one flow mapping (`{...}`), after which a block
# key cannot be appended.
root_is_flow_mapping() {
    [ -f "$CONFIG" ] || return 1
    config_without_comments \
        | grep -vE '^[[:space:]]*$|^%|^---[[:space:]]*$' \
        | sed -n '1p' \
        | grep -E '^(---[[:space:]]+)?[[:space:]]*\{' >/dev/null
}

# A branch name the backbone takes (its configuration schema's pattern, in the
# shell's terms): no whitespace or control character, none of ~^:?*[\, no `..`,
# `@{` or `//`, not an option, not `HEAD` or `@`, no component opening with `.`
# or closing with `.lock`, not ending with `/` or `.`, and not a reference
# (`origin/…`, `refs/…`).
is_branch_name() {
    local name="$1"
    [ -n "$name" ] || return 1
    case "$name" in
        -* | /* | .* | origin/* | refs/* | HEAD | @ | */ | *. ) return 1 ;;
        *..* | *@\{* | *//* | */.* | *.lock | *.lock/* ) return 1 ;;
    esac
    printf '%s' "$name" | LC_ALL=C grep -E '^[^][[:space:][:cntrl:]~^:?*\\]+$' >/dev/null
}

keep_and_say() {
    echo "  [warn] project-management's default_branch ($value) is kept: $1"
    echo "         project-management reads it, with a warning, until the default branch is declared once for every reader:"
    echo "         pkit config set repository.default-branch $value --yes   — then remove default_branch from $PM_CONFIG"
    exit 0
}

if [ -z "$value" ] || [ "$value" = "main" ]; then
    remove_alias
    echo "  [ok] removed project-management's default_branch${value:+ ($value)}: main is the backbone's default (repository.default-branch, COR-054)"
    exit 0
fi

if declares "default-branch"; then
    remove_alias
    echo "  [ok] removed project-management's default_branch ($value): .pkit/project/config.yaml declares repository.default-branch, which every reader reads (COR-054)"
    exit 0
fi

if declares "repository"; then
    keep_and_say ".pkit/project/config.yaml declares repository without default-branch, so a block cannot be appended to it"
fi
if root_is_flow_mapping; then
    keep_and_say ".pkit/project/config.yaml is one flow-style mapping ({...}), so a block cannot be appended to it"
fi
if ! is_branch_name "$value"; then
    keep_and_say "it is not a branch name the backbone takes"
fi

mkdir -p "$(dirname "$CONFIG")"
if [ ! -s "$CONFIG" ]; then
    # A file the backbone creates opens with the editor directive (ADR-056).
    printf '%s\n' '# yaml-language-server: $schema=../schemas/backbone/config.schema.json' > "$CONFIG"
elif [ -n "$(tail -c 1 "$CONFIG")" ]; then
    # Appending a top-level key needs the file to end with a newline.
    printf '\n' >> "$CONFIG"
fi

quoted="'${value//\'/\'\'}'"
cat >> "$CONFIG" <<EOF

# \`repository.default-branch\` — the branch the project's pull requests merge
# into (COR-054). Carried over by the project-management 0.55.0 upgrade from
# that capability's retired \`default_branch\`.
repository:
  default-branch: $quoted
EOF
remove_alias

echo "  [ok] recorded repository.default-branch: $value in .pkit/project/config.yaml, and removed project-management's default_branch (COR-054)"
