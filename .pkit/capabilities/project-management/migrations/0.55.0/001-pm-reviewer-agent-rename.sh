#!/usr/bin/env bash
# project-management 0.55.0 — structural: default local reviewer agent renamed
# `reviewer` → `pm-reviewer` (#770).
#
# The capability's shipped default local-path reviewer agent (DEC-028) was
# named with the single token `reviewer`, colliding with the English role-noun
# "reviewer" that saturates this capability. It is renamed to `pm-reviewer`:
#   .pkit/capabilities/project-management/agents/reviewer.md → …/pm-reviewer.md
# The verdict-line GRAMMAR is unchanged (`Reviewer agent (local, <name>): …`);
# only the bound `<name>` moves from `reviewer` to `pm-reviewer`.
#
# What sync handles vs. what this migration handles:
#   - Sync renames the kit-shipped agent file under .pkit/ and (via the
#     claude-code adapter's deploy-agents.sh) deploys …/pm-reviewer.md and
#     stale-removes the old kit-deployed reviewer.md copy.
#   - This migration handles the two pieces sync cannot: (1) rewriting the
#     adopter's project-owned `project/config.yaml` `local_registered` entry
#     `reviewer` → `pm-reviewer` (a project-owned file sync never touches, per
#     the no-shared-files invariant), and (2) belt-and-suspenders removal of a
#     stale kit-deployed `.claude/agents/reviewer.md` for orderings where
#     deploy-agents.sh has not yet run.
#
# Provenance keying (the load-bearing part). The config entry `name: reviewer`
# is IDENTICAL whether it registers the kit default or an adopter's OWN agent
# literally named `reviewer`, so the string alone never licenses a rewrite. Both
# the config rewrite and the file removal require a POSITIVE kit signal; any
# doubt leaves the config and every file alone. Checked in this order:
#   1. An adopter-owned `reviewer` agent SOURCE exists in the project agent
#      namespace (`.pkit/agents/project/reviewer.md`, or the folder form
#      `.pkit/agents/project/reviewer/reviewer.md`) ⇒ the registration is the
#      adopter's, whether or not it is deployed. Project wins name collisions at
#      deploy time, so even a marker-carrying deployed `reviewer.md` is then a
#      deploy of the adopter's agent. Leave everything alone.
#   2. `.claude/agents/reviewer.md` is a symlink (older installs) ⇒ kit default
#      only if it points into pm's canonical agents/ tree (valid or dangling).
#   3. `.claude/agents/reviewer.md` is a regular file ⇒ kit default only if it
#      carries the deploy marker in its first 5 lines. This is exactly the
#      adapter's own test (deploy-agents.sh: same full marker string, same
#      `head -n 5` window), so a file that merely quotes the marker further
#      down is adopter content, as the adapter itself would class it.
#   4. `.claude/agents/reviewer.md` absent is ambiguous (never deployed, OR
#      already stale-removed post-sync) ⇒ kit default only if the renamed
#      `.claude/agents/pm-reviewer.md` is present AND passes the same marker
#      test (deploy-agents.sh laid it down post-sync).
#   Otherwise there is no kit signal and nothing is touched.
#
# Both sync orderings are handled:
#   - sync-not-yet: deployed reviewer.md is a marker-carrying copy (or a kit
#     symlink). Rewrite the config and remove the stale file.
#   - sync-has-run: deploy-agents.sh already stale-removed reviewer.md and
#     deployed pm-reviewer.md (signal 4). Rewrite the config only.
#
# Config shapes. The config schema makes `review.agents.local_registered` a
# list of mappings whose only permitted key is `name`. The rewrite is scoped to
# that list — located by walking the block-mapping path `review:` → `agents:` →
# `local_registered:` by indentation — so a `name: reviewer` anywhere else in the
# config is never touched. Within the list it rewrites the value token
# `reviewer` of a `name` key in every shape that list takes in practice:
#   - block items, compact (`- name: reviewer`) or with the dash on its own line
#     (`-` then `  name: reviewer`), and `name` as a non-first key of an item;
#   - the sequence indented under its key or level with it;
#   - flow style (`[{name: reviewer}]`, `- {name: reviewer}`), including a flow
#     sequence continued over several lines;
#   - bare, double- or single-quoted values and keys; inline `# comments` and
#     CRLF line endings are preserved. Commented-out lines are ignored.
# `pm-reviewer` (or any name merely containing `reviewer`) is never matched.
#
# Shapes it does not rewrite, and how it reports them. After the rewrite, any
# standalone `reviewer` token still left in the list's code (not its comments)
# is a shape too exotic to edit safely here — a value on the line after
# `name:`, an anchor/alias or `!!str` tag, a block scalar, a complex `? name`
# key. Likewise, when `local_registered` sits inside a flow-style parent
# (`review: {agents: {...}}`) the list cannot be scoped, so the whole file is
# only inspected, never edited. In both cases, with a kit signal, the migration
# prints a `[warn]` naming the config file and line(s) and telling the operator
# to change `reviewer` to `pm-reviewer` by hand; it never leaves one silently
# unmigrated.
#
# Output reflects what happened: `[rewrite]` / `[remove]` per action; the
# stale-verdict `[note]` only when the config was actually rewritten; a final
# `[ok] … reconciled` only when something was rewritten or removed, a `[warn]`
# when a manual edit remains, and a `[skip] … nothing to reconcile` otherwise.
#
# Idempotent: on already-migrated state no `reviewer` entry remains and no stale
# kit file exists, so a re-run changes nothing and reports the no-op.
#
# Run via the upgrade runtime with ROOT=<adopter root>.

set -euo pipefail

: "${ROOT:?ROOT must be set by the upgrade runtime}"

CAP_DIR="$ROOT/.pkit/capabilities/project-management"
CONFIG="$CAP_DIR/project/config.yaml"
DEPLOYED_OLD="$ROOT/.claude/agents/reviewer.md"
DEPLOYED_NEW="$ROOT/.claude/agents/pm-reviewer.md"
PROJECT_AGENTS="$ROOT/.pkit/agents/project"
CANONICAL_OLD_SUFFIX="capabilities/project-management/agents/reviewer.md"
# Must stay byte-identical to MARKER in .pkit/adapters/claude-code/deploy-agents.sh.
MARKER="# managed-by: project-kit (deploy-agents.sh) — do not edit; regenerated on sync"
MARKER_WINDOW=5

if [ ! -d "$CAP_DIR" ]; then
    echo "  [skip] project-management capability not installed at $CAP_DIR"
    exit 0
fi

# The adapter's provenance test: the full marker within the first 5 lines.
# The header is captured first (not piped) so `pipefail` cannot turn an early
# `grep -q` exit into a spurious failure.
has_kit_marker() {
    local header
    header="$(head -n "$MARKER_WINDOW" "$1" 2>/dev/null)" || return 1
    grep -qF -- "$MARKER" <<<"$header"
}

# --- Provenance: does the `reviewer` registration belong to the kit? ---------
kit_default=false
no_signal_reason="no kit signal (no kit-deployed reviewer.md or pm-reviewer.md)"
if [ -f "$PROJECT_AGENTS/reviewer.md" ] || [ -f "$PROJECT_AGENTS/reviewer/reviewer.md" ]; then
    no_signal_reason="adopter-owned reviewer agent source in $PROJECT_AGENTS"
elif [ -L "$DEPLOYED_OLD" ]; then
    case "$(readlink "$DEPLOYED_OLD")" in
        *"$CANONICAL_OLD_SUFFIX") kit_default=true ;;  # kit symlink (valid or dangling)
        *) no_signal_reason="$DEPLOYED_OLD is a symlink to the adopter's own agent" ;;
    esac
elif [ -f "$DEPLOYED_OLD" ]; then
    if has_kit_marker "$DEPLOYED_OLD"; then
        kit_default=true
    else
        no_signal_reason="$DEPLOYED_OLD carries no kit marker in its header (adopter content)"
    fi
elif [ -f "$DEPLOYED_NEW" ] && has_kit_marker "$DEPLOYED_NEW"; then
    kit_default=true    # post-sync: reviewer.md stale-removed, pm-reviewer.md deployed
fi

# --- Config scan/rewrite, scoped to review.agents.local_registered -----------
# Reads the config, writes the rewritten config to stdout, and appends one
# status record per finding to the file named by `status`:
#   rewritten <count>      entries rewritten reviewer -> pm-reviewer
#   manual <line>          a `reviewer` left in the list that could not be rewritten
#   unscoped <line>        list not locatable (flow-style parent); `reviewer` on <line>
read -r -d '' SCAN_AWK <<'AWK' || true
function split_comment(s,    i, c, q) {
    q = ""
    for (i = 1; i <= length(s); i++) {
        c = substr(s, i, 1)
        if (q != "") {
            if (q == "\"" && c == "\\") { i++; continue }
            if (c == q) q = ""
            continue
        }
        if (c == "\"" || c == "'") { q = c; continue }
        if (c == "#" && (i == 1 || substr(s, i - 1, 1) ~ /[ \t]/)) {
            CODE = substr(s, 1, i - 1); CMT = substr(s, i); return
        }
    }
    CODE = s; CMT = ""
}
function has_token(s) {
    return s ~ /(^|[^A-Za-z0-9_.-])reviewer([^A-Za-z0-9_.-]|$)/
}
function last_index(s, t,    p, q) {
    p = 0
    while ((q = index(substr(s, p + 1), t)) > 0) p += q
    return p
}
# Rewrite every `name: reviewer` value in s. The block-item form can only occur
# at the start of the line, so later iterations look for the flow form only.
function rewrite(s,    out, re, m, pos) {
    out = ""; re = RE_ANY
    while (match(s, re)) {
        m = substr(s, RSTART, RLENGTH)
        pos = last_index(m, "reviewer")
        out = out substr(s, 1, RSTART - 1) substr(m, 1, pos - 1) "pm-reviewer"
        s = substr(m, pos + 8) substr(s, RSTART + RLENGTH)
        rewritten++
        re = RE_FLOW
    }
    return out s
}
function depth_delta(s,    t) {
    t = s
    return gsub(/[[{]/, "", t) - gsub(/[]}]/, "", s)
}
function region_line(code,    new) {
    new = rewrite(code)
    if (has_token(new)) print "manual " NR > status
    depth += depth_delta(code)
    return new
}
BEGIN {
    VAL = "(\"reviewer\"|'reviewer'|reviewer)"
    KV = "(name[ \t]*:[ \t]+|(\"name\"|'name')[ \t]*:[ \t]*)" VAL "[ \t]*($|[,}])"
    RE_ANY = "(^[ \t]*(-[ \t]+)*|[{,][ \t]*)" KV
    RE_FLOW = "[{,][ \t]*" KV
    KEY_RE = "^ *([A-Za-z0-9_][A-Za-z0-9_.-]*|\"[^\"]*\"|'[^']*')[ \t]*:([ \t]|$)"
    sp = 0; in_region = 0; seen_region = 0; unscoped = 0; depth = 0
    rewritten = 0; token_lines = ""
}
{
    raw = $0; cr = ""
    if (raw ~ /\r$/) { cr = "\r"; raw = substr(raw, 1, length(raw) - 1) }
    split_comment(raw); code = CODE; cmt = CMT
    if (code ~ /^[ \t]*$/) { print raw cr; next }
    if (code ~ /^(---|\.\.\.)([ \t]|$)/) { sp = 0; in_region = 0; depth = 0; print raw cr; next }
    match(code, /^ */); ind = RLENGTH

    if (in_region) {
        if (depth > 0 || ind > L || (ind == L && code ~ /^ *-([ \t]|$)/)) {
            print region_line(code) cmt cr; next
        }
        in_region = 0
    }

    if (code !~ /^ *-/ && match(code, KEY_RE)) {
        key = substr(code, ind + 1)
        sub(/[ \t]*:([ \t].*)?$/, "", key)
        if (key ~ /^["'].*["']$/) key = substr(key, 2, length(key) - 2)
        while (sp > 0 && sind[sp] >= ind) sp--
        sp++; sind[sp] = ind; skey[sp] = key
        if (sp == 3 && skey[1] == "review" && skey[2] == "agents" && skey[3] == "local_registered") {
            in_region = 1; seen_region = 1; L = ind; depth = 0
            print region_line(code) cmt cr; next
        }
    }
    if (code ~ /local_registered/) unscoped = 1
    if (has_token(code)) token_lines = token_lines " " NR
    print raw cr
}
END {
    print "rewritten " rewritten > status
    if (unscoped && !seen_region && token_lines != "") {
        n = split(token_lines, tl, " ")
        for (i = 1; i <= n; i++) print "unscoped " tl[i] > status
    }
}
AWK

did_rewrite=false
did_remove=false
manual_pending=false

if [ ! -f "$CONFIG" ]; then
    echo "  [skip] no $CONFIG; no config registration to rewrite"
else
    scan_out="$(mktemp "${TMPDIR:-/tmp}/pm-reviewer-rename.XXXXXX")"
    scan_status="$(mktemp "${TMPDIR:-/tmp}/pm-reviewer-rename-status.XXXXXX")"
    trap 'rm -f "$scan_out" "$scan_status"' EXIT
    awk -v status="$scan_status" "$SCAN_AWK" "$CONFIG" > "$scan_out"

    rewritten="$(awk '$1 == "rewritten" { print $2 }' "$scan_status")"
    manual_lines="$(awk '$1 == "manual" { printf "%s%s", sep, $2; sep = ", " }' "$scan_status")"
    unscoped_lines="$(awk '$1 == "unscoped" { printf "%s%s", sep, $2; sep = ", " }' "$scan_status")"

    if [ "${rewritten:-0}" -eq 0 ] && [ -z "$manual_lines" ] && [ -z "$unscoped_lines" ]; then
        echo "  [skip] no default reviewer in local_registered (already migrated, custom-named, or remote-only)"
    elif [ "$kit_default" != true ]; then
        echo "  [skip] local_registered reviewer left untouched: $no_signal_reason"
    else
        if [ "${rewritten:-0}" -gt 0 ]; then
            cat "$scan_out" > "$CONFIG"    # in place: keeps the file's mode and ownership
            did_rewrite=true
            echo "  [rewrite] $CONFIG: local_registered reviewer -> pm-reviewer"
        fi
        if [ -n "$manual_lines" ]; then
            manual_pending=true
            cat <<EOF
  [warn] $CONFIG line(s) $manual_lines: review.agents.local_registered still
         names 'reviewer' in a YAML shape this migration does not rewrite
         safely. Edit it by hand: change the agent name 'reviewer' to
         'pm-reviewer', leaving any other registration as it is.
EOF
        fi
        if [ -n "$unscoped_lines" ]; then
            manual_pending=true
            cat <<EOF
  [warn] $CONFIG: review.agents.local_registered is written in a flow-style
         parent mapping this migration cannot scope, so the file was not
         edited. 'reviewer' appears on line(s) $unscoped_lines. Edit by hand:
         in review.agents.local_registered, change the agent name 'reviewer'
         to 'pm-reviewer'; leave any other 'reviewer' in the file alone.
EOF
        fi
    fi
fi

# --- Remove the stale kit-deployed reviewer.md -------------------------------
if [ "$kit_default" != true ]; then
    :   # adopter content or no kit signal — never remove
elif [ -L "$DEPLOYED_OLD" ]; then
    echo "  [remove] $DEPLOYED_OLD (stale kit symlink; pm-reviewer.md deploys on next sync)"
    rm -f "$DEPLOYED_OLD"
    did_remove=true
elif [ -f "$DEPLOYED_OLD" ]; then
    echo "  [remove] $DEPLOYED_OLD (stale kit-deployed copy; pm-reviewer.md deploys on next sync)"
    rm -f "$DEPLOYED_OLD"
    did_remove=true
fi

# --- Operator note: in-flight verdicts go stale ------------------------------
if [ "$did_rewrite" = true ]; then
    echo "  [note] any OPEN PR carrying a 'Reviewer agent (local, reviewer):' verdict"
    echo "         goes stale after this rename — the gate now matches 'pm-reviewer'."
    echo "         It self-heals on the next 'review-pr <N>' run (a fresh pm-reviewer"
    echo "         verdict is posted); no manual cleanup of the old comment is needed."
fi

if [ "$manual_pending" = true ]; then
    echo "  [warn] reviewer -> pm-reviewer rename needs the manual config edit above"
elif [ "$did_rewrite" = true ] || [ "$did_remove" = true ]; then
    echo "  [ok] reviewer -> pm-reviewer rename reconciled"
else
    echo "  [skip] reviewer -> pm-reviewer rename: nothing to reconcile"
fi
exit 0
