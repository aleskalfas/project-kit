#!/usr/bin/env bash
# software-analysis 0.2.0 — resource: create-the-analysis-rule-set.
#
# From 0.2.0 the capability declares one project rule set, ANALYSIS, which its
# install creates: a set of the project's own that selects the analysis by the
# capability's types and inherits software-analysis:SAN at SAN's major (COR-017;
# DEC-001, Implications). SAN takes no scope, so its rules bind only through
# such a set (COR-051 point 7). A project that installed the capability before
# 0.2.0 got no set from its install. This migration creates the set for it, on
# install's conditions, as COR-017 and COR-051 point 6 let a migration of the
# capability do. Choosing the upgrade's target is the consent (COR-059 point 4).
#
# The positive sign it acts on: the backbone's answer says install would create
# the set here, and the file is still missing. That answer is install's own:
# no set of the project's own inherits SAN, directly or not, no project rule-set
# file is unreadable, no rule set takes the name, and nothing lies at the path.
# The migration reads it through `pkit capabilities project-rule-set
# software-analysis --json` and writes the text it gives, never walking the
# rule sets itself (ADR-057 point 1). The nested pkit runs unrouted
# (PKIT_NO_ROUTE), so it never fetches another version.
#
# It creates a set a project may have chosen not to have: the release's notes
# say so, and the project may remove it. A capability's migrations run from the
# version its manifest records, so this one does not run again once the upgrade
# completes.
#
# Never fails the upgrade: where pkit or python3 is missing, or the answer cannot
# be read (a pkit too old to give it, say), it creates nothing, warns, and names
# the command that shows the set to write.
#
# Idempotent: once a set of the project's own inherits SAN, the answer creates
# nothing, and a file at the path is never written over.

set -euo pipefail

# ROOT is the adopter's project root, provided by the runtime.
: "${ROOT:?ROOT must be set by the upgrade runtime}"

CAPABILITY="software-analysis"
SHOW="pkit capabilities project-rule-set $CAPABILITY"

warn_and_stop() {
    echo "  [warn] no project rule set created: $1"
    echo "         after the upgrade, \`$SHOW\` shows the set install declares and whether to write it"
    exit 0
}

if ! command -v pkit >/dev/null 2>&1; then
    warn_and_stop "no pkit on PATH, so the backbone's answer cannot be read"
fi
if ! command -v python3 >/dev/null 2>&1; then
    warn_and_stop "no python3 on PATH to read the backbone's answer"
fi

answer="$(cd "$ROOT" && PKIT_NO_ROUTE=1 pkit capabilities project-rule-set "$CAPABILITY" --json 2>/dev/null)" || answer=""

# The answer is read with the standard library only: a migration acquires no
# runtime dependency at upgrade time.
result="$(ANSWER="$answer" python3 - "$ROOT" <<'PYEOF'
import json
import os
import sys
from pathlib import Path, PurePosixPath

root = Path(sys.argv[1])
try:
    document = json.loads(os.environ.get("ANSWER", ""))
except ValueError:
    document = None
if not isinstance(document, dict) or document.get("schema_version") != 1:
    print("UNREADABLE")
    raise SystemExit(0)
if not document.get("declared"):
    print("NONE")
    raise SystemExit(0)
inherited = document.get("inherited_by") or []
if inherited:
    print("INHERITED " + ", ".join(str(path) for path in inherited))
    raise SystemExit(0)
if not document.get("creates"):
    print("BLOCKED " + str(document.get("blocked")))
    raise SystemExit(0)
path, text, pin = document.get("path"), document.get("text"), document.get("pin")
relative = PurePosixPath(path) if isinstance(path, str) and path else None
if relative is None or relative.is_absolute() or ".." in relative.parts or not isinstance(text, str):
    print("UNREADABLE")
    raise SystemExit(0)
target = root / relative
if target.exists() or target.is_symlink():
    print(f"BLOCKED {path} exists already, and nothing is written over a file")
    raise SystemExit(0)
target.parent.mkdir(parents=True, exist_ok=True)
try:
    with target.open("x", encoding="utf-8") as handle:
        handle.write(text)
except FileExistsError:
    print(f"BLOCKED {path} exists already, and nothing is written over a file")
    raise SystemExit(0)
print(f"CREATED {path} {pin}")
PYEOF
)" || result="UNREADABLE"

case "$result" in
    CREATED\ *)
        rest="${result#CREATED }"
        path="${rest% *}"
        pin="${rest##* }"
        echo "  [ok] created the project rule set ANALYSIS at $path, inheriting $pin (COR-017)"
        echo "       It is the project's own, to edit or remove. Run \`pkit validate\` to see what SAN's rules find."
        ;;
    INHERITED\ *)
        echo "  exists  ${result#INHERITED } inherits software-analysis:SAN already: no set created"
        ;;
    NONE)
        echo "  exists  $CAPABILITY declares no project rule set here: nothing to create"
        ;;
    BLOCKED\ *)
        warn_and_stop "${result#BLOCKED }"
        ;;
    *)
        warn_and_stop "the backbone's answer could not be read (a pkit older than this release gives none)"
        ;;
esac
