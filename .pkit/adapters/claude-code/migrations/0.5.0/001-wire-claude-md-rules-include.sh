#!/usr/bin/env bash
# claude-code adapter migration 0.5.0 — resource: wire-claude-md-rules-include.
#
# The rules area (`.pkit/rules/core.md`) ships hard rules and tool-hygiene
# conventions that every adopter's agent must receive. Even when core.md
# lands in `.pkit/rules/` (backbone migration 1.93.0), it is inert unless
# the host CLAUDE.md loads it via an @-include.
#
# This migration (COR-002 merge contract / insert-if-absent posture):
#   - If CLAUDE.md doesn't exist: creates a minimal one with the @-include
#     and a placeholder for project-specific content.
#   - If CLAUDE.md exists without the @-include: inserts the @-include line
#     after the first H1 or, if there is no H1, prepends a minimal header
#     block and the @-include before the existing content.
#   - If CLAUDE.md already contains the @-include: no-op (idempotent).
#
# Per core.md rule 13 (the @-include authoring convention): the @-include
# line goes after the host's intro paragraph or H1, not at line 1, so the
# included sections nest naturally under the host's structure.
#
# NEVER clobbers adopter content: the insert is surgical (awk-based);
# everything already in CLAUDE.md is preserved verbatim.
#
# Idempotent — re-running on already-migrated state is a no-op.

set -euo pipefail

: "${ROOT:?ROOT must be set by the upgrade runtime}"

CLAUDE_MD="$ROOT/CLAUDE.md"
CORE_INCLUDE="@.pkit/rules/core.md"
PROJECT_INCLUDE="@.pkit/rules/project.md"

status() { printf "  [%-6s] %s\n" "$1" "$2"; }

# ── Already contains the core.md include? ─────────────────────────────────
if [ -f "$CLAUDE_MD" ] && grep -qF "$CORE_INCLUDE" "$CLAUDE_MD"; then
    status "skip" "CLAUDE.md already includes $CORE_INCLUDE; already migrated"
    exit 0
fi

# ── CLAUDE.md doesn't exist — create a minimal one ────────────────────────
if [ ! -f "$CLAUDE_MD" ]; then
    cat > "$CLAUDE_MD" <<'HEREDOC'
# Claude Code instructions

This file is loaded by Claude Code at session start. The kit-shipped rules
and tool-hygiene conventions are included below; add project-specific
instructions after the includes.

@.pkit/rules/core.md
@.pkit/rules/project.md
HEREDOC
    status "create" "CLAUDE.md (minimal host with @-includes)"
    exit 0
fi

# ── CLAUDE.md exists but lacks the include — insert after the first H1 ────
# Strategy:
#   1. Find the line number of the first `# ` heading (Markdown H1).
#   2. If found, insert the @-include block after that line.
#   3. If no H1, prepend a minimal header + @-includes above the existing
#      content (COR-002: never clobbers; prepend is the safe posture when
#      we can't determine where the includes belong).
#
# The @-include block: core.md first (always), project.md second (always —
# the file may not exist yet, but Claude Code silently ignores missing
# @-includes, so wiring it now is harmless and future-proof).

# Find the line number of the first H1 (line starting with exactly "# ").
H1_LINE=$(grep -n "^# " "$CLAUDE_MD" | head -1 | cut -d: -f1 || true)

TMP=$(mktemp)
INCLUDE_TMP=$(mktemp)

# Write the include block to a temp file to avoid newline-in-variable issues
# with awk's -v flag. The block has a leading blank line so the @-include
# lines are visually separated from the H1.
printf '\n%s\n%s\n' "$CORE_INCLUDE" "$PROJECT_INCLUDE" > "$INCLUDE_TMP"

if [ -n "$H1_LINE" ]; then
    # Insert the include block after the H1 line.
    awk -v h1="$H1_LINE" -v inc="$INCLUDE_TMP" '
        NR == h1 { print; while ((getline line < inc) > 0) print line; next }
        { print }
    ' "$CLAUDE_MD" > "$TMP"
    rm -f "$INCLUDE_TMP"
    mv "$TMP" "$CLAUDE_MD"
    status "insert" "CLAUDE.md — @-includes added after line $H1_LINE (first H1)"
else
    rm -f "$INCLUDE_TMP"
    # No H1 — prepend a minimal header + @-includes above the existing content.
    {
        printf '# Claude Code instructions\n'
        printf '\n'
        printf '%s\n' "$CORE_INCLUDE"
        printf '%s\n' "$PROJECT_INCLUDE"
        printf '\n'
        cat "$CLAUDE_MD"
    } > "$TMP"
    mv "$TMP" "$CLAUDE_MD"
    status "prepend" "CLAUDE.md — @-includes prepended (no H1 found in existing file)"
fi
