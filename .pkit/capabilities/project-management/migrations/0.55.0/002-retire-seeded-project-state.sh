#!/usr/bin/env bash
# project-management 0.55.0 — resource: retire state seeded from the SOURCE
# project's `project/` tree into this adopter (#814, under the #811 epic).
#
# Until #812, a capability install and every subsequent `pkit sync` copied the
# *source* project's adopter-owned `project/` tree into the adopter, because
# seed-once treats an absent destination as an invitation to copy. So adopters
# received another project's instance data: its default-agent activation file,
# its bootstrap stamp, its per-issue lifecycle journals, its config and its
# workstream taxonomy. #812 stopped the copying. It removed nothing already on
# disk — `refresh_owned_tree` never prunes adopter-owned paths, by design — so
# without this migration a pre-#812 adopter keeps every seeded file and behaves
# differently from a fresh install of the same version.
#
# PROVENANCE DISCIPLINE (the load-bearing part), following the precedent set by
# 001-pm-reviewer-agent-rename.sh in this same directory: act only on a
# POSITIVE signal of kit provenance; where no positive signal exists, leave the
# file alone and report it. A migration that guesses wrong here deletes an
# adopter's own audit history or silently disables a feature they chose.
#
# REMOVED — provably foreign:
#   * a lifecycle journal byte-identical to one this version shipped. An
#     adopter's own journal for the same issue number is not byte-identical to
#     another project's; equality is proof of origin. A foreign journal is also
#     actively harmful — `pm history <N>` reads it as this project's history.
#
# REPORTED, NEVER REMOVED — no positive signal, or removal would harm:
#   * `adapter-overlays/claude-code.json` — ambiguous BY CONSTRUCTION. It is
#     byte-identical whether the source seeded it or the adopter deliberately
#     ran `enable-default-agent` (that command copies the same template and
#     leaves no record that it ran). There is no signal to key on, so removing
#     it would silently disable a feature an adopter may have chosen. Reported
#     with the remediation instead.
#   * `config.yaml` / `workstreams.yaml` — may have been EDITED on top of the
#     seed, and their seeded values are frequently correct anyway
#     (`default_branch: main`, `gh.host: github.com`). Deleting an adopter's
#     only working config to purify its provenance would be actively harmful.
#   * `bootstrap-stamp.yaml`. A seeded stamp is genuinely harmful — it reads as
#     "already bootstrapped", so gated verbs would run against foreign defaults
#     — but deciding whether one is foreign requires the SAME normaliser that
#     wrote it (`session_guard.normalize_origin_url`: case-folding, userinfo,
#     host:port, ssh:// forms). A migration is shell-only by convention here, and
#     a divergent re-implementation would delete stamps that are legitimately
#     the adopter's. Reported instead — and the adopter is not unprotected,
#     because `bootstrap_gate._repo_binding_problem` already refuses a
#     foreign-repo stamp at every gated verb using that canonical normaliser.
#     Removing it here would be tidiness, not protection, and tidiness does not
#     justify a data-loss risk.
#   * any journal that does NOT match this version's shipped set — either the
#     adopter's own, or seeded by an older version whose content this migration
#     cannot know. Reported so it is a visible decision rather than a silent
#     residue.
#
# KNOWN LIMIT, stated rather than hidden: the embedded hashes are this version's
# shipped set. Because the leak was continuous through `sync`, an adopter who
# synced recently holds exactly this set and is fully cleaned; one who installed
# long ago and never synced may hold an older set, which is reported, not
# removed. Hashes are embedded rather than compared against the live kit source
# because #813 removes these files from the distribution entirely — after that
# there is no source copy left to compare against.
#
# Idempotent: re-running finds nothing to remove and reports only what remains.

set -euo pipefail

# ROOT is the adopter's project root, provided by the runtime.
: "${ROOT:?ROOT must be set by the upgrade runtime}"

PROJECT_DIR="$ROOT/.pkit/capabilities/project-management/project"

if [ ! -d "$PROJECT_DIR" ]; then
    echo "  exists  no project-management project/ tree — nothing seeded"
    exit 0
fi

# SHA-256 of every file this version seeded, as shipped. A match is proof the
# file came from the source project rather than this adopter.
SEEDED_JOURNAL_HASHES="
2b8aad08b2e61ea80c3641814ca4a07105e4fff5d194c1ef8d4cb311eedc2943
eec5b5a3e75cc72d026c41f7db4cbc4e8ec908604f10195c24771c5ef44c144d
caf6c9ef7d759be4f4722774db0b4f4106ae7bbd840c29bca9f10a0759fea2ea
747b2c394cd1bd0e94b8a732e871f09ee2113f4475e790e58e63a6ada520e4ef
5b0ad3a11627dabf147627238ece83ea3170f59229593488f26ddca4804f7322
edce5c6f02b563922f4e9b798e5f2ca36d33f4f3091d49cd88059fdf79b3aed6
208c004b22ebbb0fbeb8f2d7847cb4e95295eac7e38952a9f533b08720e7028b
c7a0cfd42106e7f0f3e02188fe486f5ef86ea74a15be6b2113176e322c182aa1
934f11de9be81ba160ed170da56bf57dbc603fd0d46bb4f66745fe20674fd623
368ff4019aad8497478d2187570b132c1e5a0efdb84e197c7a2ad2bce9030b5a
b2782f228b02a057b672df5c6471aecf9fde78dbbfba8d9839bf182bb908764c
5419abbef1112deac822c7fcc383ae8b0b734ca5b3f80e797c2188c762cdf824
d160979f62999b03bf3a3afb55d1c72f97ba9f61fcd5c6f1784568cab8565b87
ae07a406fe586ac3d792970f3c0cf4eab91b2d094d65ac4fbc2e16debf7c04cd
"

_sha() { shasum -a 256 "$1" 2>/dev/null | cut -d' ' -f1; }

removed=0
actions=()      # things the adopter must decide — printed FIRST
notes=()        # things kept for information
removals=()     # what this migration took, as supporting detail

# --- Ambiguous / possibly-useful: report, never remove -----------------------
# Measured against real adopters (mockingbird, interaction-gateway): this is the
# ONLY seeded artifact that reached them, and it is the one no signal can judge.
# So it leads the report rather than trailing a cleanup that often finds nothing.
OVERLAY="$PROJECT_DIR/adapter-overlays/claude-code.json"
if [ -f "$OVERLAY" ]; then
    actions+=("the project-manager default agent is ACTIVE for this project (the adapter activates on the mere presence of adapter-overlays/claude-code.json).
          That file is byte-identical whether it was seeded from the source project or you ran \`enable-default-agent\` yourself, and enabling leaves no
          record — so this migration cannot tell, and will not guess.
            -> If you did NOT enable it, you did not choose this: run \`pkit pm disable-default-agent\`.
            -> If you did, nothing to do.")
fi

for f in config.yaml workstreams.yaml; do
    if [ -f "$PROJECT_DIR/$f" ]; then
        notes+=("$f kept — it may carry the source project's values (branch, host, doc mappings, taxonomy), but it may equally be yours or edited on top. Worth a look; not safe to remove for you.")
    fi
done

# --- Provably foreign: remove --------------------------------------------------
JOURNAL_DIR="$PROJECT_DIR/process/issue-lifecycle"
if [ -d "$JOURNAL_DIR" ]; then
    while IFS= read -r journal; do
        [ -n "$journal" ] || continue
        h="$(_sha "$journal")"
        if [ -n "$h" ] && printf '%s\n' "$SEEDED_JOURNAL_HASHES" | grep -qxF "$h"; then
            rm -f "$journal"
            removals+=("$(basename "$journal") — byte-identical to the source project's, so provably not yours")
            removed=$((removed + 1))
        else
            notes+=("journal $(basename "$journal") kept — not from this version's shipped set, so yours or seeded by an older version")
        fi
    done < <(find "$JOURNAL_DIR" -name '*.journal.jsonl' -type f 2>/dev/null | sort)
fi

STAMP="$PROJECT_DIR/bootstrap-stamp.yaml"
if [ -f "$STAMP" ]; then
    # Read only, for an informative message. `repo` is nested under the
    # `bootstrap:` block by `bootstrap_gate.write_stamp`, so it is INDENTED —
    # anchoring at column 0 matches nothing a real stamp contains.
    stamp_repo="$(grep -m1 -E '^[[:space:]]*repo:' "$STAMP" 2>/dev/null \
        | sed -E 's/^[[:space:]]*repo:[[:space:]]*//' | tr -d '"' || true)"
    notes+=("bootstrap-stamp.yaml is present${stamp_repo:+, attesting setup for '$stamp_repo'}. Kept deliberately: comparing repo identity correctly requires the same
          normaliser that WROTE the value (\`session_guard.normalize_origin_url\` — case-folding, userinfo, ports, ssh:// forms), and a shell re-implementation
          that disagreed with it would delete a stamp that is legitimately yours. You are not unprotected meanwhile: the gate refuses a stamp naming a different
          repo on every gated verb, using that same normaliser. If it names a project that is not yours, deleting it is safe and \`pkit pm bootstrap\` will re-stamp.")
fi

# --- Print: what needs YOUR decision, then what to look at, then what moved ---
if [ ${#actions[@]} -eq 0 ] && [ ${#notes[@]} -eq 0 ] && [ "$removed" -eq 0 ]; then
    echo "  exists  no state seeded from the source project — nothing to retire"
    exit 0
fi

for a in ${actions[@]+"${actions[@]}"}; do
    echo "  ACTION  $a"
done
for n in ${notes[@]+"${notes[@]}"}; do
    echo "  check   $n"
done
for r in ${removals[@]+"${removals[@]}"}; do
    echo "  removed $r"
done

echo "  retire-seeded-project-state: ${#actions[@]} needing your decision, ${#notes[@]} to review, $removed removed"
