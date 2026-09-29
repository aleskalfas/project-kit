#!/usr/bin/env bash
#
# Undeploy one capability's skills and agents from .claude/ — the inverse of
# deploy-skills.sh and deploy-agents.sh, for a single named capability.
#
# Usage: undeploy-capability.sh <capability-name>
#
# Part of the Claude Code adapter (.pkit/adapters/claude-code/) per COR-005's
# adapter pattern. The lifecycle calls it, by this name and with the
# capability's name as its one argument, when it unregisters a capability whose
# subtree stays on disk — an incubated capability's uninstall, or any
# capability's uninstall in the methodology's source repository. The skills
# deploy reads the registry and drops an unregistered capability's skills on a
# re-run, but the agents deploy keys its stale-removal on whether a source file
# still exists, and there it does, so a re-run alone cannot drop the capability. Where the
# harness keeps skills and agents is this adapter's knowledge, not the
# lifecycle's (COR-013): the lifecycle knows the script's name and argument only.
#
# What it removes — only what the deploy primitives created for this
# capability, recognised by the mark each leaves:
# - a skill: a .claude/skills/<skill>/ whose SKILL.md is a symlink
#   deploy-skills.sh wrote into the capability (its target starts
#   ../../../.pkit/capabilities/<name>/). Every symlink in that directory that
#   points into the capability goes; the directory goes once nothing is left.
# - an agent: a .claude/agents/<agent>.md carrying deploy-agents.sh's marker,
#   for an agent the capability ships under .pkit/capabilities/<name>/agents/ —
#   unless the project namespace ships an agent of that name: project agents
#   outrank every other source (the agents README, "Name-collision
#   precedence"), so that deployed copy is the project's.
#
# What it never touches: adopter content (a file or directory that is not such
# a symlink, a symlink pointing anywhere else, an agent file without the
# marker) and the capability's own subtree.
#
# It removes what exists for the named capability whatever the capability's
# registration, so it runs the same before or after the capability is
# unregistered. Agents are found through the capability's agents/ directory; a
# capability whose subtree is gone has its agents dropped by deploy-agents.sh's
# stale-removal pass instead.
#
# Idempotent: nothing deployed for the capability → nothing removed, exit 0.
# Exit status: 0 on success; 2 on a usage error (no name, or not a capability
# name). Tagged status lines: removed, kept.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
KIT_AGENTS="$ROOT/.pkit/agents"
CLAUDE_SKILLS="$ROOT/.claude/skills"
CLAUDE_AGENTS="$ROOT/.claude/agents"

# The marker deploy-agents.sh writes into each resolved agent's frontmatter —
# the same string, so a copy it wrote is recognised here. A test holds the two
# scripts to one value.
MARKER="# managed-by: project-kit (deploy-agents.sh) — do not edit; regenerated on sync"

status() { printf "  %-10s %s\n" "$1" "$2"; }

if [ "$#" -ne 1 ]; then
    echo "usage: $(basename "$0") <capability-name>" >&2
    exit 2
fi
NAME="$1"
# A capability name (the lifecycle's own rule): lower-case, digits and hyphens,
# starting with a letter — so the name can never reach outside the capabilities
# tree as a path.
if ! [[ "$NAME" =~ ^[a-z]([a-z0-9-]*[a-z0-9])?$ ]]; then
    echo "error: '$NAME' is not a capability name." >&2
    exit 2
fi
CAP_DIR="$ROOT/.pkit/capabilities/$NAME"
# The relative-link prefix deploy-skills.sh writes for this capability's
# skills, from .claude/skills/<skill>/.
CAP_LINK_PREFIX="../../../.pkit/capabilities/$NAME/"

removed=0

# True when the file's frontmatter carries deploy-agents.sh's marker (it is
# written as line 2; the first five lines are read, as deploy-agents.sh does).
carries_marker() {
    local top
    top="$(head -n 5 "$1")"
    [[ "$top" == *"$MARKER"* ]]
}

# True when the project namespace ships an agent of this name — the one source
# that outranks a capability's whatever else deploy's precedence says.
project_ships_agent() {
    local name="$1"
    [ -f "$KIT_AGENTS/project/$name.md" ] || [ -f "$KIT_AGENTS/project/$name/$name.md" ]
}

# The agent names the capability ships, flat or folder form (as
# deploy-agents.sh lists them).
capability_agent_names() {
    local entry name
    [ -d "$CAP_DIR/agents" ] || return 0
    for entry in "$CAP_DIR/agents"/*; do
        [ -e "$entry" ] || continue
        name="$(basename "$entry")"
        if [ -f "$entry" ] && [[ "$name" == *.md ]]; then
            echo "${name%.md}"
        elif [ -d "$entry" ]; then
            echo "$name"
        fi
    done
}

shopt -s nullglob

# Skills: a deployed skill is this capability's when its SKILL.md links into it.
if [ -d "$CLAUDE_SKILLS" ]; then
    for skill_dir in "$CLAUDE_SKILLS"/*; do
        [ -d "$skill_dir" ] && [ ! -L "$skill_dir" ] || continue
        inner="$skill_dir/SKILL.md"
        [ -L "$inner" ] || continue
        [[ "$(readlink "$inner")" == "$CAP_LINK_PREFIX"* ]] || continue
        skill="$(basename "$skill_dir")"
        for entry in "$skill_dir"/*; do
            [ -L "$entry" ] || continue
            [[ "$(readlink "$entry")" == "$CAP_LINK_PREFIX"* ]] || continue
            rm "$entry"
        done
        if rmdir "$skill_dir" 2>/dev/null; then
            status "removed" ".claude/skills/$skill (capability $NAME)"
        else
            status "kept" ".claude/skills/$skill/ — its links into capability $NAME removed; other content left in place"
        fi
        removed=$((removed + 1))
    done
fi

# Agents: resolved copies carry no link back, so match the capability's agent
# names against the marked copies.
if [ -d "$CLAUDE_AGENTS" ]; then
    while IFS= read -r agent; do
        [ -n "$agent" ] || continue
        dest="$CLAUDE_AGENTS/$agent.md"
        [ -f "$dest" ] && [ ! -L "$dest" ] || continue
        carries_marker "$dest" || continue
        if project_ships_agent "$agent"; then
            status "kept" ".claude/agents/$agent.md (deployed from the project agent of that name)"
            continue
        fi
        rm "$dest"
        status "removed" ".claude/agents/$agent.md (capability $NAME)"
        removed=$((removed + 1))
    done < <(capability_agent_names)
fi

shopt -u nullglob

if [ "$removed" -eq 0 ]; then
    echo "Done. Nothing deployed for capability $NAME."
else
    echo "Done."
fi
