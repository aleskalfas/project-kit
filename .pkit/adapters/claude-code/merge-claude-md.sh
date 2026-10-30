#!/usr/bin/env bash
#
# Keep the adopter's root CLAUDE.md including the rules every session loads:
# core's @.pkit/rules/core.md, then the capabilities' rules index
# @.pkit/rules/capabilities.md, then the project's @.pkit/rules/project.md, in
# the order of their layers (COR-070 point 4; ADR-076 points 2 and 3).
#
# Per the COR-002 merge contract (insert-if-absent / create-if-none). Its entry
# classes: core's include and the index's line are auto-add entries, each
# inserted wherever it is absent; the project's include is inserted only
# together with core's, so a project that removed it does not find it back.
#   - CLAUDE.md doesn't exist: creates a minimal host with the three lines.
#   - CLAUDE.md holds core's include but not the index's line: inserts the
#     index's line directly after core's include.
#   - CLAUDE.md lacks core's include: inserts core's, the index's and the
#     project's lines after the first H1, or prepends a minimal header with them
#     if there is no H1. The existing content is NEVER clobbered.
#   - core's include sits only in fenced code or a code span, where Claude Code
#     imports nothing: inserts nothing and reports it. Only the project can say
#     where its include belongs, so the project's own edit mends it.
#   - CLAUDE.md holds both: no-op (idempotent).
#
# "Holds the line": a line of the file that is exactly the line once the spaces
# and tabs around it are trimmed and a CRLF ending is read as \n, outside a
# fenced code block (a line opening with ``` or ~~~, indented at most three
# spaces, opens or closes one, and lies inside it). A mention in a code span, in
# a fence, or as part of a longer token does not hold it. The backbone's check
# (`project_kit.loaded_rules.holds_line`) uses the same definition, and one set
# of test cases holds the two to it.
#
# Writes through the file on every write path: the new content is written into
# the existing CLAUDE.md, never moved over it, so a CLAUDE.md that is a link
# keeps its link and the line reaches the file it links to, and its mode stays.
# A file whose lines end in CRLF gets its inserted lines with CRLF too.
#
# It reads CLAUDE.md alone: a project that moved core's include into a file
# CLAUDE.md imports, such as AGENTS.md, finds the lines added to CLAUDE.md too.
#
# Per core.md rule 13 (the @-include authoring convention): the included
# sections start at H2, so the @-include lines come after the host's H1, not at
# line 1, so the sections nest naturally under the host.
#
# Output uses tagged status lines: created, insert, prepend, exists, refused.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

CLAUDE_MD="$ROOT/CLAUDE.md"
CORE_INCLUDE="@.pkit/rules/core.md"
# The line `loaded_rules.line` renders in package.yaml, kept here since a
# primitive is given no `pkit` to ask (ADR-065 point 14); a test holds the two
# equal.
INDEX_INCLUDE="@.pkit/rules/capabilities.md"
PROJECT_INCLUDE="@.pkit/rules/project.md"

status() { printf "  %-10s %s\n" "$1" "$2"; }

# The one reading of a line's place: awk functions every program below shares.
# `fence_marker` gives ``` or ~~~ for a line that opens or closes fenced code,
# else ""; `trimmed` gives the line without the spaces and tabs around it.
AWK_LIB='
function fence_marker(line,    s, n) {
    s = line; n = 0
    while (n < 3 && (substr(s, 1, 1) == " " || substr(s, 1, 1) == "\t")) { s = substr(s, 2); n++ }
    if (substr(s, 1, 3) == "```") return "```"
    if (substr(s, 1, 3) == "~~~") return "~~~"
    return ""
}
function trimmed(line) {
    sub(/^[ \t]+/, "", line); sub(/[ \t]+$/, "", line)
    return line
}
'

# holds FILE LINE — exit 0 where FILE holds LINE, 1 where it does not.
holds() {
    awk -v want="$2" "$AWK_LIB"'
        { sub(/\r$/, "") }
        {
            marker = fence_marker($0)
            if (marker != "") {
                if (fence == marker) fence = ""; else if (fence == "") fence = marker
                next
            }
            if (fence == "" && trimmed($0) == want) { found = 1; exit }
        }
        END { exit (found ? 0 : 1) }
    ' "$1"
}

# only_in_code FILE TEXT — exit 0 where TEXT appears in FILE only inside fenced
# code or a code span, 1 where it appears outside code too, or not at all.
only_in_code() {
    awk -v want="$2" "$AWK_LIB"'
        { sub(/\r$/, "") }
        {
            marker = fence_marker($0)
            if (marker != "") {
                if (index($0, want)) in_code = 1
                if (fence == marker) fence = ""; else if (fence == "") fence = marker
                next
            }
            if (!index($0, want)) next
            if (fence != "") { in_code = 1; next }
            rest = $0; before = ""
            while ((at = index(rest, want)) > 0) {
                before = before substr(rest, 1, at - 1)
                ticks = gsub(/`/, "`", before)
                if (ticks % 2 == 1) in_code = 1; else outside = 1
                before = before want
                rest = substr(rest, at + length(want))
            }
        }
        END { exit (in_code && !outside) ? 0 : 1 }
    ' "$1"
}

# write_through FILE CONTENT_FILE — write the new content into the existing file,
# keeping a link and the file's mode.
write_through() {
    cat "$2" > "$1"
    rm -f "$2"
}

# ── CLAUDE.md doesn't exist — create a minimal one ────────────────────────
if [ ! -f "$CLAUDE_MD" ]; then
    cat > "$CLAUDE_MD" <<'HEREDOC'
# Claude Code instructions

This file is loaded by Claude Code at session start. The kit-shipped rules
and tool-hygiene conventions are included below; add project-specific
instructions after the includes.

@.pkit/rules/core.md
@.pkit/rules/capabilities.md
@.pkit/rules/project.md
HEREDOC
    status "created" "CLAUDE.md (minimal host with @-includes)"
    exit 0
fi

# ── Holds core's include: keep the index's line directly after it ─────────
if holds "$CLAUDE_MD" "$CORE_INCLUDE"; then
    if holds "$CLAUDE_MD" "$INDEX_INCLUDE"; then
        status "exists" "CLAUDE.md (already includes $CORE_INCLUDE)"
        exit 0
    fi
    TMP=$(mktemp)
    awk -v core="$CORE_INCLUDE" -v line="$INDEX_INCLUDE" "$AWK_LIB"'
        {
            raw = $0; text = raw; cr = sub(/\r$/, "", text)
            print raw
            marker = fence_marker(text)
            if (marker != "") {
                if (fence == marker) fence = ""; else if (fence == "") fence = marker
                next
            }
            if (!done && fence == "" && trimmed(text) == core) {
                printf "%s%s\n", line, (cr ? "\r" : "")
                done = 1
            }
        }
    ' "$CLAUDE_MD" > "$TMP"
    write_through "$CLAUDE_MD" "$TMP"
    status "insert" "CLAUDE.md ($INDEX_INCLUDE added after $CORE_INCLUDE)"
    exit 0
fi

# ── Core's include only in code — the project's own edit mends it ─────────
if only_in_code "$CLAUDE_MD" "$CORE_INCLUDE"; then
    status "refused" "CLAUDE.md ($CORE_INCLUDE sits only in fenced code or a code span, where Claude Code imports nothing; move it out of the code, then run \`pkit sync\`)"
    exit 0
fi

# ── CLAUDE.md lacks core's include — insert after the first H1 ────────────
# Strategy:
#   1. Find the line number of the first `# ` heading (Markdown H1) outside
#      fenced code.
#   2. If found, insert the include block after that line (with a blank line
#      separator so the includes don't run into the H1 inline).
#   3. If no H1, prepend a minimal header + includes above the existing content
#      (never clobbers; prepend is the safe posture when we can't determine where
#      the includes belong).
#
# The three lines are written together: core.md (always), the index, then
# project.md (always — the file may not exist yet, but Claude Code silently
# ignores missing @-includes, so wiring it is harmless and future-proof).

EOL=$'\n'
if awk 'NR == 1 { exit ($0 ~ /\r$/) ? 0 : 1 } END { if (NR == 0) exit 1 }' "$CLAUDE_MD"; then
    EOL=$'\r\n'
fi

H1_LINE=$(awk "$AWK_LIB"'
    { sub(/\r$/, "") }
    {
        marker = fence_marker($0)
        if (marker != "") {
            if (fence == marker) fence = ""; else if (fence == "") fence = marker
            next
        }
        if (fence == "" && $0 ~ /^# /) { print NR; exit }
    }
' "$CLAUDE_MD")

TMP=$(mktemp)
INCLUDE_TMP=$(mktemp)

# Write the include block to a temp file to avoid newline-in-variable issues
# with awk's -v flag. The block has a leading blank line so the @-include
# lines are visually separated from the H1.
printf '%s%s%s%s%s%s%s' "$EOL" "$CORE_INCLUDE" "$EOL" "$INDEX_INCLUDE" "$EOL" "$PROJECT_INCLUDE" "$EOL" > "$INCLUDE_TMP"

if [ -n "$H1_LINE" ]; then
    # Insert the include block immediately after the H1 line.
    awk -v h1="$H1_LINE" -v inc="$INCLUDE_TMP" '
        NR == h1 { print; while ((getline line < inc) > 0) print line; next }
        { print }
    ' "$CLAUDE_MD" > "$TMP"
    rm -f "$INCLUDE_TMP"
    write_through "$CLAUDE_MD" "$TMP"
    status "insert" "CLAUDE.md (@-includes added after line $H1_LINE)"
else
    rm -f "$INCLUDE_TMP"
    {
        printf '# Claude Code instructions%s' "$EOL"
        printf '%s' "$EOL"
        printf '%s%s' "$CORE_INCLUDE" "$EOL"
        printf '%s%s' "$INDEX_INCLUDE" "$EOL"
        printf '%s%s' "$PROJECT_INCLUDE" "$EOL"
        printf '%s' "$EOL"
        cat "$CLAUDE_MD"
    } > "$TMP"
    write_through "$CLAUDE_MD" "$TMP"
    status "prepend" "CLAUDE.md (@-includes prepended; no H1 found)"
fi
