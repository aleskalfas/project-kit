#!/usr/bin/env bash
#
# Deploy each agent's definition as a resolved copy under
# .claude/agents/<name>.md so Claude Code can load it.
#
# Part of the Claude Code adapter (.pkit/adapters/claude-code/) per
# COR-005's adapter pattern. Sibling to deploy-skills.sh; differs in
# two ways:
#
#   1. Copies (not symlinks) — agent templates contain `<category-name>`
#      placeholders resolved at deploy time against
#      `.pkit/agents/project/overlay.yaml`. The resolved file is what
#      Claude Code loads; the source template is what authors edit.
#
#   2. Flat destination layout — Claude Code expects one `.md` file per
#      agent at `.claude/agents/<name>.md`, not a per-agent directory.
#
# Behavior:
# - Which definition of a name is the agent is the agents area's picker's
#   answer (.pkit/agents/definition_source.py; COR-013 point 8, ADR-087), which
#   the resolver's `--plan` entry writes, a line for each name some place ships.
#   The project's definition wins, then an installed capability's (the one the
#   project chose, else the first by name, by code points, so every locale
#   takes the same one), then core's. This script keeps no order of its own.
# - Each run names each suspension it applies (COR-074): a `suspended` line for
#   each file of a definition core or an installed capability ships that a file
#   of the project's keeps out — the project's own definition, which is the
#   agent whether it deploys or is refused, or a file at the agent's place
#   without the mark — naming both files, and a closing note with their count.
#   The plan names each definition's files, so one the picker does not count,
#   such as one the project skipped, is not named.
# - Overlay placeholders (`<category-name>`) are resolved from
#   `overlay.yaml`'s top-level categories, with per-agent values in
#   `overrides.<name>` taking precedence per COR-013.
# - Idempotent: if the resolved content matches the destination,
#   reports "exists"; otherwise overwrites.
# - The mark: each copy's front matter opens with the mark line, then the
#   definition it was written from (its place), the digest of the text read and
#   the tool access read from it (ADR-087 point 4). The resolver writes them.
# - Unresolved overlay placeholder in a *hard* channel (a category an agent
#   references through a list key or `reads.paths` / `reads.records` but the
#   project's overlay.yaml doesn't define) → skipped loudly with remediation,
#   the rest deploy, the run exits 0 (an adopter-config gap, not fatal). A
#   category referenced *only* via `reads.patterns` is an optional read
#   (ADR-052): undefined, its item is dropped and the agent still deploys.
# - The agent's `model:` / `effort:` (#1047) are carried into the resolved
#   file — an overlay `overrides.<name>.model` / `.effort` wins over the front
#   matter; absent or `inherit` writes no key (the harness default applies).
#   A value the harness does not accept is not written: the agent deploys,
#   inherits, and a `warning` status line names the value.
# - A storyboard the source declares by its bare sibling filename
#   (`storyboard.md`, COR-016) is rewritten to its project-root-relative source
#   path in the resolved file — in `storyboards:` and where the body cites it —
#   so the deployed copy, which lives in `.claude/agents/`, still resolves it.
# - Every resolved body ends with the adapter's workspace sentence (#2026):
#   the session scratch directory the harness's environment note names is
#   replaced by `.agent-workspace/`. The resolver adds it.
# - The agent's tool access is written from the agents area's reader
#   (.pkit/agents/tool_access.py): a grant as `tools`, a withheld list as
#   Claude Code's `disallowedTools` (ADR-085, ADR-086).
# - A refused agent stays the agent, and no other definition stands in
#   (COR-013 point 8). Refused for its tool access, its earlier copy is
#   removed. Refused for another cause, the earlier copy written from the same
#   definition stays only where the tool access its mark records gives nothing
#   the current text's does not, and the deploy says it is not of the current
#   text; otherwise it is removed. A winning place holding both layouts of a
#   name has no one current text, so its earlier copy is removed.
# - Every marked copy that is not the agent's goes: one written from another
#   definition, or of a name with no agent or that no place ships.
# - A name whose records the picker cannot read is told in an `error` line,
#   and nothing is written or removed for it; the run still exits 0, so the
#   lifecycle command that ran it goes on, and `pkit validate` holds the error.
# - A file with no mark is never written over. Where it takes a name a place
#   ships, the harness may run it in the agent's place, and the run says so.
# - Tagged status lines: created, updated, exists, skipped, removed, kept,
#   warning, error, suspended.
#
# Deferred:
# - Disable mechanism (adopter wants a kit agent not deployed) — same
#   deferral rationale as deploy-skills.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
KIT_AGENTS="$ROOT/.pkit/agents"
CLAUDE_AGENTS="$ROOT/.claude/agents"
OVERLAY="$KIT_AGENTS/project/overlay.yaml"
RESOLVER="$SCRIPT_DIR/_resolve_agent.py"

# The mark the resolver writes as each copy's first front-matter line. The kit
# uses it to tell its own deployed copies from adopter-authored agents that
# happen to share a name. YAML comments are ignored by every frontmatter
# parser, including Claude Code's, so the mark is invisible at load time but
# trivial to grep for here. `_resolve_agent.py` holds the same value; a test
# holds the two equal.
MARKER="# managed-by: project-kit (deploy-agents.sh) — do not edit; regenerated on sync"
# The line beside the mark naming the definition a copy was written from.
MARK_DEFINITION="# pkit-definition: "

# The resolver's exit statuses (`_resolve_agent.py`): refused for a cause other
# than its tool access, refused for its tool access, refused where the earlier
# copy may stay, and cannot tell.
REFUSED=1
TOOL_ACCESS_REFUSED=3
KEEP_EARLIER=4
CANNOT_TELL=5

mkdir -p "$CLAUDE_AGENTS"

status() { printf "  %-10s %s\n" "$1" "$2"; }

# A path under the project root, as the root-relative path a person types.
relative() { printf "%s" "${1#"$ROOT"/}"; }

# A place in words: the project, core, or capability <name>.
describe_place() {
    case "$1" in
        capability:*) printf "capability %s" "${1#capability:}" ;;
        project) printf "the project" ;;
        *) printf "%s" "$1" ;;
    esac
}

# True when the file's first five lines carry the mark.
carries_marker() { head -n 5 "$1" | grep -qF "$MARKER"; }

# The place the mark of the copy at $1 records it was written from; empty for
# a copy whose mark records none.
recorded_definition() {
    head -n 5 "$1" | sed -n "s/^${MARK_DEFINITION}//p" | head -n 1
}

# Remove the marked copy of agent $1, naming why ($2). Adopter content stays.
remove_copy() {
    local dest="$CLAUDE_AGENTS/$1.md"
    if [ -e "$dest" ] && carries_marker "$dest"; then
        rm -f "$dest"
        status "removed" ".claude/agents/$1.md ($2)"
    fi
}

# Name a suspension the deploy applies (COR-074): the file $1 of a definition
# core or an installed capability ships, which $2, a file of the project's,
# keeps out. Each run names it again, for as long as it holds. Counts the lines
# in `suspended`.
name_suspension() {
    status "suspended" "$(relative "$1") (replaced by $2)"
    suspended=$((suspended + 1))
}

# Resolve placeholders in the source file using the overlay, write to stdout.
# Delegates to the sibling Python helper (self-contained via PEP 723 inline
# metadata; uv installs `ruamel.yaml` transparently on first invocation,
# regardless of whether the adopter's tree has a host pyproject.toml).
resolve_agent() {
    "$RESOLVER" "$@"
}

# Deploy the agent $1, whose definition $2 ships at $4, where $3 places ship
# the name.
deploy_one() {
    local name="$1" place="$2" shipped="$3" source_file="$4"
    local dest="$CLAUDE_AGENTS/$name.md"

    # The copy deployed before is the agent's where its mark records the agent's
    # place, or, recording none, where one place alone ships the name (ADR-087
    # point 4). Only the agent's may stay on a refusal for another cause.
    local earlier=()
    if [ -e "$dest" ]; then
        local recorded
        recorded="$(recorded_definition "$dest")"
        if { [ -n "$recorded" ] && [ "$recorded" = "$place" ]; } \
            || { [ -z "$recorded" ] && [ "$shipped" = "1" ]; }; then
            earlier=(--earlier "$dest")
        fi
    fi

    local tmpfile tmperr resolve_status
    tmpfile="$(mktemp)"
    tmperr="$(mktemp)"
    resolve_status=0
    resolve_agent "$source_file" "$name" "$OVERLAY" --mark "$place" \
        ${earlier[@]+"${earlier[@]}"} >"$tmpfile" 2>"$tmperr" || resolve_status=$?
    if [ "$resolve_status" -eq "$CANNOT_TELL" ]; then
        # A module or the adapter's declaration the resolution needs cannot be
        # read: change nothing for the name (COR-013 point 8).
        status "error" "$name — $(head -n 1 "$tmperr"); its deployed copy is left as it is."
        while IFS= read -r line; do
            printf "  %s\n" "         $line"
        done < <(tail -n +2 "$tmperr")
        rm -f "$tmpfile" "$tmperr"
        untold=$((untold + 1))
        return 0
    fi
    if [ "$resolve_status" -eq "$TOOL_ACCESS_REFUSED" ]; then
        # Refused for its tool access (COR-013 point 7, ADR-086 point 3): not
        # deployed, and the copy deployed before is removed, since it may give
        # tools the definition no longer gives.
        status "skipped" "$name — $(head -n 1 "$tmperr")."
        remove_copy "$name" "the copy deployed before its tool access was refused"
        printf "  %s\n" "         Mend its tool access in $(relative "$source_file"), then rerun the deploy."
        rm -f "$tmpfile" "$tmperr"
        refused=$((refused + 1))
        return 0
    fi
    if [ "$resolve_status" -ne 0 ]; then
        # Refused for another cause, such as an unresolved overlay category — an
        # adopter-config gap (a category this agent references but the project's
        # overlay.yaml doesn't define, common when a kit agent like `architect`
        # is newer than the adopter's overlay). It is NON-FATAL: skip this one
        # agent loudly with remediation, deploy the rest, and don't abort the
        # whole sync/upgrade over an unrelated capability. The deploy is
        # idempotent — once the overlay defines the category, the next sync
        # deploys the agent.
        #
        # The resolver's stderr is "reason on line 1, optional remediation
        # after". When it supplies remediation of its own, print that verbatim:
        # the generic `adopt` advice below is wrong for a category with no
        # conventional folder, since `adopt` has no folder to create for it and
        # refuses (#2469). That covers a project's own categories and the
        # write-carrying ones, which name paths only the adopter can enumerate
        # (ADR-051). The resolver knows which categories have a conventional
        # folder because the shared ownership module declares them; this script
        # stays dumb about it.
        local skip_reason remediation
        skip_reason="$(head -n 1 "$tmperr")"
        remediation="$(tail -n +2 "$tmperr")"
        status "skipped" "$name — $skip_reason."
        if [ -n "$remediation" ]; then
            while IFS= read -r line; do
                printf "  %s\n" "         $line"
            done <<<"$remediation"
        else
            printf "  %s\n"    "         Deploy it:  pkit agents adopt $name"
            printf "  %s\n"    "         (custom doc layout? run \`pkit agents reconcile --write\`, set the"
            printf "  %s\n"    "          paths in overlay.yaml, then \`pkit sync\`)"
            adoptable=$((adoptable + 1))
        fi
        if [ "$resolve_status" -eq "$KEEP_EARLIER" ]; then
            # The earlier copy gives no tool the current text does not, so it
            # stays, and runs (COR-013 point 8).
            status "kept" ".claude/agents/$name.md — written from an earlier text of its definition, so it is not of the current text; it gives no tool the current text does not"
        else
            remove_copy "$name" "its definition's current text is refused, and the copy deployed before gives a tool it does not, or records none"
        fi
        rm -f "$tmpfile" "$tmperr"
        unresolved=$((unresolved + 1))
        return 0
    fi
    # The agent resolved, but the resolver may still have something to report —
    # e.g. an optional category set with no value, which deploys without it.
    # Only `warning:`-prefixed lines are the resolver's; other stderr stays hidden.
    local warning
    while IFS= read -r warning; do
        status "warning" "$name — ${warning#warning: }"
    done < <(grep '^warning: ' "$tmperr" || true)
    rm -f "$tmperr"

    if [ -e "$dest" ]; then
        if cmp -s "$tmpfile" "$dest"; then
            status "exists" ".claude/agents/$name.md"
        else
            cp "$tmpfile" "$dest"
            chmod 644 "$dest"
            status "updated" ".claude/agents/$name.md"
        fi
    else
        cp "$tmpfile" "$dest"
        chmod 644 "$dest"
        status "created" ".claude/agents/$name.md"
    fi
    rm -f "$tmpfile"
}

# The plan: which definition of each name some place ships is the agent, as the
# picker answers it. Where the picker cannot be reached, nothing is decided, so
# nothing is written or removed.
exit_code=0
unresolved=0
adoptable=0
refused=0
doubled=0
untold=0
suspended=0
plan_file="$(mktemp)"
plan_err="$(mktemp)"
plan_status=0
resolve_agent --plan >"$plan_file" 2>"$plan_err" || plan_status=$?
if [ "$plan_status" -ne 0 ]; then
    status "error" "cannot tell which definition of any agent is the agent: $(head -n 1 "$plan_err")"
    while IFS= read -r line; do
        printf "  %s\n" "         $line"
    done < <(tail -n +2 "$plan_err")
    rm -f "$plan_file" "$plan_err"
    echo "Done. Nothing was deployed or removed."
    exit 0
fi
rm -f "$plan_err"

# Pass: each name some place ships. A skip never aborts the run — see
# deploy_one. `exit_code` is reserved for genuinely catastrophic failures.
#
# The `definition` lines after a name's line name the files of its definitions
# that count, the project's first (COR-074). `holder` is the file of the
# project's that keeps out the name's shipped ones, if any. `project_holds` is
# set where the project's definition is the agent, whether it deploys or is
# refused, so its files are the holder.
shipped_names=""
holder_name=""
holder=""
project_holds=""
while IFS=$'\t' read -r kind name first second third; do
    [ -n "$name" ] || continue
    if [ "$kind" = "definition" ]; then
        [ "$name" = "$holder_name" ] || continue
        if [ "$first" = "project" ]; then
            [ -z "$project_holds" ] || holder="${holder:+$holder and }$(relative "$second")"
        elif [ -n "$holder" ]; then
            name_suspension "$second" "$holder"
        fi
        continue
    fi
    holder_name="$name"
    holder=""
    project_holds=""
    shipped_names="$shipped_names$name"$'\n'
    dest="$CLAUDE_AGENTS/$name.md"
    # A file without the mark is never written over: it is the project's own,
    # or a copy from before the mark. The harness may run it in the agent's place.
    if [ -e "$dest" ] && ! carries_marker "$dest"; then
        status "skipped" ".claude/agents/$name.md carries no deploy mark, so the deploy leaves it; the harness may run it in place of the agent $name a place ships (to have the deploy write its copy, delete it and rerun this script)"
        holder=".claude/agents/$name.md, a file the deploy did not make"
        continue
    fi
    case "$kind" in
        agent)
            [ "$first" != "project" ] || project_holds=1
            deploy_one "$name" "$first" "$third" "$second" || exit_code=$?
            ;;
        refused)
            [ "$first" != "project" ] || project_holds=1
            status "skipped" "$name — $second."
            remove_copy "$name" "its definition is refused, and has no one current text"
            doubled=$((doubled + 1))
            ;;
        none)
            status "skipped" "$name — no agent: $first."
            remove_copy "$name" "$name has no agent"
            ;;
        untold)
            status "error" "$name — $first; nothing is written or removed for it."
            untold=$((untold + 1))
            ;;
    esac
done <"$plan_file"
rm -f "$plan_file"

# Stale-removal pass: drop deployed copies that carry the mark, of a name no
# place ships any longer. Marked-less files (adopter content) are left
# untouched — strip the mark to keep a no-longer-shipped agent.
if [ -d "$CLAUDE_AGENTS" ]; then
    for dep in "$CLAUDE_AGENTS"/*.md; do
        [ -e "$dep" ] || continue
        dep_name="$(basename "$dep" .md)"
        carries_marker "$dep" || continue        # not ours → leave
        if ! grep -qxF "$dep_name" <<<"$shipped_names"; then
            rm -f "$dep"
            status "removed" ".claude/agents/$dep_name.md (stale — no longer shipped)"
        fi
    done
fi

echo "Done."
if [ "$unresolved" -gt 0 ]; then
    echo "  note: $unresolved agent(s) skipped — overlay category not set; the rest deployed."
    echo "        → Per-agent remediation is printed above; it differs by category."
    if [ "$adoptable" -gt 0 ]; then
        echo "        → Conventional doc layout:      pkit agents adopt <agent>"
        echo "        → Anything else:                pkit agents reconcile --write → set paths → pkit sync"
    else
        echo "        → Set the paths in overlay.yaml, or stub them: pkit agents reconcile --write; then pkit sync"
    fi
fi
if [ "$refused" -gt 0 ]; then
    echo "  note: $refused agent(s) refused for their tool access, and not deployed; each cause is printed above."
fi
if [ "$doubled" -gt 0 ]; then
    echo "  note: $doubled agent(s) refused, and not deployed: the place that wins ships two texts of each."
fi
if [ "$untold" -gt 0 ]; then
    echo "  note: $untold agent(s) left as they were: what decides them cannot be read; each cause is printed above."
fi
if [ "$suspended" -gt 0 ]; then
    echo "  note: $suspended shipped agent(s) suspended — a file of the project's takes each one's name, so no session reaches it."
    echo "        → To deploy one again, rename or remove the file its line names as replacing it, then run pkit sync."
fi
exit $exit_code
