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
# Provenance keying (the load-bearing part). The config string
# `- name: reviewer` is IDENTICAL whether it registers the kit default or an
# adopter's OWN agent literally named `reviewer`. Keying on the string alone
# would wrongly rewrite a custom agent's registration. So the rewrite is gated
# on provenance of the DEPLOYED agent at `.claude/agents/reviewer.md`:
#   - deploy-agents.sh deploys agents as COPIES carrying a marker
#     (`managed-by: project-kit (deploy-agents.sh) …`); an adopter-authored
#     agent has NO marker. Older installs may carry a symlink instead — a
#     kit-deployed one points into pm's canonical agents/ tree, an adopter's
#     points elsewhere. Both signals are covered below.
#   - Marker-less copy, or a symlink pointing outside pm's canonical tree ⇒
#     adopter-authored `reviewer` ⇒ leave config AND the file entirely alone.
#   - Marker-carrying copy, or a symlink into pm's tree (valid or dangling) ⇒
#     the kit default ⇒ rewrite config and remove the stale kit-deployed file.
#   - Absent reviewer.md is ambiguous on its own (never deployed, OR already
#     stale-removed post-sync). Disambiguate with a POSITIVE kit signal: only
#     treat it as the kit default when the renamed `.claude/agents/pm-reviewer.md`
#     is present (deploy-agents.sh laid it down post-sync). Absent + no
#     pm-reviewer.md ⇒ no kit signal ⇒ leave the config `reviewer` alone (it may
#     be an adopter's undeployed/custom agent we must not silently take over).
#
# Both sync orderings are handled:
#   - sync-not-yet: canonical reviewer.md still ships; deployed reviewer.md is a
#     marker-carrying copy (or valid kit symlink). Rewrite + remove.
#   - sync-has-run: canonical is now pm-reviewer.md; deploy-agents.sh already
#     stale-removed the deployed reviewer.md copy (absent) and deployed
#     pm-reviewer.md. The pm-reviewer.md presence is the positive signal that
#     lets the absent-reviewer.md case rewrite. Rewrite only.
#
# Config-shape breadth. The default entry is detected/rewritten across every
# shape valid YAML permits for `name: reviewer` — block or flow style, bare or
# quoted (`"reviewer"` / `'reviewer'`), with an optional inline `# comment` or
# trailing flow punctuation (`[{name: reviewer}]`). The value must be the token
# `reviewer` sitting immediately after the `name:` key, so `pm-reviewer` is
# never matched.
#
# Idempotent: re-runs on already-migrated state are no-ops (the rewrite gate is
# "a default `reviewer` entry still present"; removals are "file still exists").
#
# Run via the upgrade runtime with ROOT=<adopter root>.

set -euo pipefail

: "${ROOT:?ROOT must be set by the upgrade runtime}"

CAP_DIR="$ROOT/.pkit/capabilities/project-management"
CONFIG="$CAP_DIR/project/config.yaml"
DEPLOYED_OLD="$ROOT/.claude/agents/reviewer.md"
DEPLOYED_NEW="$ROOT/.claude/agents/pm-reviewer.md"
CANONICAL_OLD_SUFFIX="capabilities/project-management/agents/reviewer.md"
MARKER="managed-by: project-kit (deploy-agents.sh)"

if [ ! -d "$CAP_DIR" ]; then
    echo "  [skip] project-management capability not installed at $CAP_DIR"
    exit 0
fi

# --- Provenance: does the deployed reviewer registration belong to the kit? ---
# The default `reviewer` registration is only the kit's to rename when the
# DEPLOYED agent carries a positive kit signal. Absence of a signal (adopter
# content, or no kit deployment at all) leaves the config untouched.
kit_default=false
if [ -L "$DEPLOYED_OLD" ]; then
    target="$(readlink "$DEPLOYED_OLD")"
    case "$target" in
        *"$CANONICAL_OLD_SUFFIX") kit_default=true ;;  # kit symlink (valid or dangling)
        *) : ;;                                        # symlink to the adopter's own agent
    esac
elif [ -f "$DEPLOYED_OLD" ]; then
    if grep -q "$MARKER" "$DEPLOYED_OLD" 2>/dev/null; then
        kit_default=true                 # marker-carrying copy = kit output
    fi                                   # marker-less regular file = adopter content
elif [ -f "$DEPLOYED_NEW" ]; then
    kit_default=true                     # reviewer.md absent + pm-reviewer.md present
                                         # = post-sync kit default (positive signal)
fi
# reviewer.md absent AND pm-reviewer.md absent ⇒ kit_default stays false: no kit
# signal, so an adopter's undeployed/custom `reviewer` is not silently taken over.

# --- Step 1: rewrite the config's default `reviewer` registration ------------
# DETECT_RE matches a `name:` entry whose value is the bare token `reviewer`
# across block/flow, bare/quoted, and inline-comment/trailing-punctuation
# shapes; it deliberately does NOT match `pm-reviewer`.
DETECT_RE='(^[[:space:]]*-|[{,])[[:space:]]*name:[[:space:]]*("reviewer"|'"'"'reviewer'"'"'|reviewer)[[:space:]]*($|[#,}])'
if [ ! -f "$CONFIG" ]; then
    echo "  [skip] no $CONFIG; no config registration to rewrite"
elif ! grep -Eq "$DETECT_RE" "$CONFIG"; then
    echo "  [skip] no default reviewer in local_registered (already migrated, custom-named, or remote-only)"
elif [ "$kit_default" != true ]; then
    echo "  [skip] local_registered reviewer shows no kit-default provenance (adopter-authored, or undeployed/custom) — config left untouched"
else
    # Preserve the entry's prefix (\1), quoting (\3 open, \4 close), and any
    # inline comment / trailing flow punctuation (\5); rewrite only the token.
    sed -i.bak -E 's/((^[[:space:]]*-|[{,])[[:space:]]*name:[[:space:]]*)(["'"'"']?)reviewer(["'"'"']?)([[:space:]]*($|[#,}]))/\1\3pm-reviewer\4\5/g' "$CONFIG"
    rm -f "$CONFIG.bak"
    echo "  [rewrite] $CONFIG: local_registered reviewer -> pm-reviewer"
fi

# --- Step 2: remove the stale kit-deployed reviewer.md -----------------------
if [ "$kit_default" != true ]; then
    :   # adopter content or no kit signal — never remove
elif [ -L "$DEPLOYED_OLD" ]; then
    echo "  [remove] $DEPLOYED_OLD (stale kit symlink; pm-reviewer.md deploys on next sync)"
    rm -f "$DEPLOYED_OLD"
elif [ -f "$DEPLOYED_OLD" ]; then
    echo "  [remove] $DEPLOYED_OLD (stale kit-deployed copy; pm-reviewer.md deploys on next sync)"
    rm -f "$DEPLOYED_OLD"
fi

# --- Operator note: in-flight verdicts go stale ------------------------------
echo "  [note] any OPEN PR carrying a 'Reviewer agent (local, reviewer):' verdict"
echo "         goes stale after this rename — the gate now matches 'pm-reviewer'."
echo "         It self-heals on the next 'review-pr <N>' run (a fresh pm-reviewer"
echo "         verdict is posted); no manual cleanup of the old comment is needed."

echo "  [ok] reviewer -> pm-reviewer rename reconciled"
exit 0
