#!/usr/bin/env bash
#
# Undeploy one capability's skills from .claude/ — the inverse of
# deploy-skills.sh, for a single named capability.
#
# Usage: undeploy-capability.sh <capability-name>
#
# Part of the Claude Code adapter (.pkit/adapters/claude-code/) per COR-005's
# adapter pattern. The lifecycle calls it, by this name and with the
# capability's name as its one argument, when it unregisters a capability whose
# subtree stays on disk — an incubated capability's uninstall, or any
# capability's uninstall in the methodology's source repository. Where the
# harness keeps skills is this adapter's knowledge, not the lifecycle's
# (COR-013): the lifecycle knows the script's name and argument only.
#
# It removes no agent (ADR-087 point 4). Which definition of a name is the
# agent is the picker's to say (.pkit/agents/definition_source.py), and it
# counts a capability's definitions only while the component registry records
# the capability. So once the capability is unregistered, the deploy the
# lifecycle runs after it (deploy-agents.sh) removes each copy it wrote from the
# capability's definitions, and writes the definition that now wins for each
# name another place ships. Skills keep this step until project-kit#2956
# decides their rules.
#
# What it removes — only what deploy-skills.sh created for this capability,
# recognised by its mark: a .claude/skills/<skill>/ whose SKILL.md is a symlink
# deploy-skills.sh wrote into the capability (its target starts
# ../../../.pkit/capabilities/<name>/). Every symlink in that directory that
# points into the capability goes; the directory goes once nothing is left.
#
# What it never touches: adopter content (a file or directory that is not such
# a symlink, a symlink pointing anywhere else), any agent, and the capability's
# own subtree.
#
# It removes what exists for the named capability whatever the capability's
# registration, so it runs the same before or after the capability is
# unregistered.
#
# Idempotent: nothing deployed for the capability → nothing removed, exit 0.
# Exit status: 0 on success; 2 on a usage error (no name, or not a capability
# name). Tagged status lines: removed, kept.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
CLAUDE_SKILLS="$ROOT/.claude/skills"

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
# The relative-link prefix deploy-skills.sh writes for this capability's
# skills, from .claude/skills/<skill>/.
CAP_LINK_PREFIX="../../../.pkit/capabilities/$NAME/"

removed=0

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

shopt -u nullglob

if [ "$removed" -eq 0 ]; then
    echo "Done. Nothing deployed for capability $NAME."
else
    echo "Done."
fi
