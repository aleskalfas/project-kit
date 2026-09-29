#!/usr/bin/env bash
# Backbone migration 1.150.0 — resource: keep-process-journal-logging.
#
# Process journal logging became opt-in (COR-033 point 7): the engine now keeps
# a per-subject journal only when `.pkit/project/config.yaml` says
# `process.journal.enabled: true`, and the default is off. Before this version
# every engine kept one. Without this migration a project that relied on its
# journals would silently stop getting them on upgrade — `pm history` would go
# quiet and the drift check would stop running.
#
# The rule (the upgrade is the consent, COR-048 point 5, as COR-033 point 7
# specifies):
#   - The project already declares `process` in its configuration, as a block
#     key or inside a flow mapping → it has made its own choice; leave it alone.
#   - No journal file exists under `.pkit/capabilities/*/project/process/` →
#     nothing relied on logging; write nothing, so the new default (off) applies.
#   - Journals exist → record `enabled: true`, with `committed` following what
#     the project did with them: `true` when any journal is tracked by git,
#     `false` when they were all clone-local (git-ignored, the previous default).
#     When the whole configuration is one flow mapping (`{...}`), a block key
#     cannot be appended to it: write nothing, and say how to turn logging on.
#
# Journals were clone-local by default, so the decision is made from the clone
# the upgrade runs in; a project whose journals live only in other clones can
# turn logging on itself (`pkit config set process.journal.enabled true --yes`).
#
# `.pkit/.gitignore` is rendered by the sync step that runs before migrations,
# i.e. before this setting existed, so it ignores journals. When the journals
# are committed, the backbone's journal ignore line is removed here so it does
# not wait for the next render (which would drop it anyway). A component still
# declaring its own journal line keeps its journals ignored; the migration says
# so, and `pkit validate` names the component.
#
# Idempotent: the first run writes the `process:` block, so every later run takes
# the first branch and changes nothing; the ignore-line removal is a no-op once
# the line is gone. A flow-style configuration is never written, so a re-run
# only repeats the advice.

set -euo pipefail

# ROOT is the adopter's project root, provided by the runtime.
: "${ROOT:?ROOT must be set by the upgrade runtime}"

CONFIG="$ROOT/.pkit/project/config.yaml"
GITIGNORE="$ROOT/.pkit/.gitignore"
CAPABILITIES="$ROOT/.pkit/capabilities"
# The journal pattern as the backbone renders it into `.pkit/.gitignore`
# (repo-root-relative `.pkit/capabilities/*/project/process/**/*.journal.jsonl`,
# rebased onto `.pkit/`).
RENDERED_IGNORE_LINE='capabilities/*/project/process/**/*.journal.jsonl'
TRACKED_PATHSPEC=':(glob).pkit/capabilities/*/project/process/**/*.journal.jsonl'

# The configuration with its comments blanked, so a commented-out key does not
# count. A `#` starts a comment at the start of a line or after whitespace.
config_without_comments() {
    sed -e 's/^[[:space:]]*#.*$//' -e 's/[[:space:]]#.*$//' "$CONFIG"
}

# Whether the configuration declares `process`, in either YAML style: a block
# key at column 0 (`process:`, plain or quoted), or a key inside a flow mapping
# (`{process: {...}}`), which may span lines. The schema has no other key of
# that name, so a flow-style match is the top-level key. Read without a YAML
# parser because the runtime guarantees only bash; any doubt leans towards
# "declared", which leaves the file alone rather than risk a duplicate key.
# (No `grep -q` or `head` in these pipelines: under `pipefail` a reader that
# stops early can kill the writer with SIGPIPE and fail the whole condition.)
declares_process() {
    local text
    text="$(config_without_comments)"
    printf '%s\n' "$text" | grep -E "^[\"']?process[\"']?[[:space:]]*:" >/dev/null && return 0
    printf '%s\n' "$text" | tr '\n' ' ' \
        | grep -E "[{,][[:space:]]*[\"']?process[\"']?[[:space:]]*:" >/dev/null
}

# Whether the document's root is a flow mapping (`{...}`): its first line with
# content, after blank lines, directives and a bare document marker, opens one.
# A block key cannot be appended after it.
root_is_flow_mapping() {
    config_without_comments \
        | grep -vE '^[[:space:]]*$|^%|^---[[:space:]]*$' \
        | sed -n '1p' \
        | grep -E '^(---[[:space:]]+)?[[:space:]]*\{' >/dev/null
}

if [ -f "$CONFIG" ] && declares_process; then
    echo "  [skip] .pkit/project/config.yaml already declares process settings; left as the project set them"
    exit 0
fi

journal_count=0
if [ -d "$CAPABILITIES" ]; then
    journal_count=$(find "$CAPABILITIES" -type f -path '*/project/process/*' -name '*.journal.jsonl' | wc -l | tr -d ' ')
fi

if [ "$journal_count" -eq 0 ]; then
    echo "  [skip] no process journals in this clone; journal logging stays off (the new default)"
    exit 0
fi

committed=false
if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    tracked=$(git -C "$ROOT" ls-files -- "$TRACKED_PATHSPEC" 2>/dev/null | head -n 1 || true)
    if [ -n "$tracked" ]; then
        committed=true
    fi
fi

if [ -f "$CONFIG" ] && root_is_flow_mapping; then
    # Leave a valid file valid: journal logging is off from here, and the
    # operator is told how to keep it on.
    echo "  [warn] .pkit/project/config.yaml is one flow-style mapping ({...}), so the setting cannot be appended to it; journal logging is now off"
    echo "         $journal_count journal file(s) found. To keep logging on: pkit config set process.journal.enabled true --yes"
    if [ "$committed" = true ]; then
        echo "         They are tracked by git, so also: pkit config set process.journal.committed true --yes"
    fi
    exit 0
fi

mkdir -p "$(dirname "$CONFIG")"
if [ ! -s "$CONFIG" ]; then
    # A file the backbone creates opens with the editor directive (ADR-056).
    printf '%s\n' '# yaml-language-server: $schema=../schemas/backbone/config.schema.json' > "$CONFIG"
elif [ -n "$(tail -c 1 "$CONFIG")" ]; then
    # Appending a top-level key needs the file to end with a newline.
    printf '\n' >> "$CONFIG"
fi

cat >> "$CONFIG" <<EOF

# \`process.journal\` — process journal logging (COR-033 point 7). Recorded by
# the 1.150.0 upgrade because this project already kept journals, so logging
# stays on; \`committed\` follows whether those journals were tracked by git.
process:
  journal:
    enabled: true
    committed: $committed
EOF

echo "  [ok] recorded process.journal (enabled: true, committed: $committed): $journal_count journal file(s) found, so logging stays on"

if [ "$committed" = true ] && [ -f "$GITIGNORE" ] && grep -qxF "$RENDERED_IGNORE_LINE" "$GITIGNORE"; then
    tmp="$GITIGNORE.tmp"
    grep -vxF "$RENDERED_IGNORE_LINE" "$GITIGNORE" > "$tmp" || true
    mv "$tmp" "$GITIGNORE"
    # A component older than this backbone may still declare its own journal
    # line, which the render keeps; say so rather than claim journals are free.
    if grep -E '^[^#].*\.journal\.jsonl$' "$GITIGNORE" >/dev/null; then
        echo "  [warn] removed the backbone's process-journal line from .pkit/.gitignore, but a component still declares its own, so its journals stay ignored"
        echo "         pkit validate names the component; upgrade it together with the backbone"
    else
        echo "  [ok] .pkit/.gitignore no longer ignores process journals (they are committed)"
    fi
fi
