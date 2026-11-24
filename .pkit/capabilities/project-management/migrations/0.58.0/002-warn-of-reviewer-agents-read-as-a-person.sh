#!/usr/bin/env bash
# project-management 0.58.0 — resource: warn of reviewer agents read as a person.
#
# [project-management:DEC-079-bots-are-no-person] point 3 counts, in human
# mode, no approval from an account the project registers as a reviewer
# agent's, `review.agents.remote_registered` in `project/config.yaml`, and asks
# no such account for a review. Each approver and each member is compared with
# the registered entries as the backbone's spelling of accounts has it
# ([pkit:ADR-094] point 3). This migration warns of each entry whose reading
# changes what the project's gate and its reviewer assignment do, in open mode
# as behind a closed gate:
#
#   - an entry with no spelling, such as `@bot`: the comparison cannot tell any
#     account from it, so until a person mends it no approval counts as a
#     person's in human mode, and human mode asks no member for a review;
#   - an entry the spelling reads as a user's account, a bare login: an App's
#     account is written `<name>[bot]`, so a bare entry meant for an App names
#     another account, and the App's approvals are no longer told from a
#     person's by it.
#
# It never warns of an entry read as a bot's, `<name>[bot]` or `app/<name>`.
# It writes nothing: which account an entry means is the project's to decide.
# Idempotent: a second run says the same, and where it finds nothing to warn
# of it says so and exits clean.
#
# Run via the upgrade runtime with ROOT=<adopter root>.

set -euo pipefail

# ROOT is the adopter's project root, provided by the runtime.
: "${ROOT:?ROOT must be set by the upgrade runtime}"

CAP_DIR="$ROOT/.pkit/capabilities/project-management"
CONFIG="$CAP_DIR/project/config.yaml"

if [ ! -d "$CAP_DIR" ]; then
    echo "  [skip] project-management capability not installed at $CAP_DIR"
    exit 0
fi
if [ ! -f "$CONFIG" ]; then
    echo "  [skip] no project/config.yaml: no reviewer agent is registered"
    exit 0
fi
if ! command -v python3 >/dev/null 2>&1; then
    echo "  [warn] python3 is not on PATH, so review.agents.remote_registered in $CONFIG was not read" >&2
    exit 0
fi

python3 - "$CONFIG" <<'PYEOF'
import re
import sys

# The entries of `review.agents.remote_registered`, read line by line: the
# runtime guarantees only bash and stdlib python3, so no YAML parser is used.
KEY = re.compile(r"^(?P<indent>[ ]*)(?P<key>[A-Za-z0-9_-]+)[ \t]*:(?P<value>.*)$")
LOGIN = re.compile(r"""^[ ]*-?[ ]*github_login[ \t]*:[ \t]*(?P<value>.*?)[ \t]*(?:#.*)?$""")
BOT = re.compile(r"^(?:[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?\[bot\]|app/[A-Za-z0-9][A-Za-z0-9-]*)$", re.I)
BARE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$")

path = []  # (indent, key) of each block the line lies in
entries = []
for raw in open(sys.argv[1], encoding="utf-8"):
    line = raw.rstrip("\n")
    if not line.strip() or line.lstrip().startswith("#"):
        continue
    indent = len(line) - len(line.lstrip(" "))
    stripped = line.lstrip(" ")
    key = KEY.match(stripped if not stripped.startswith("- ") else stripped[2:])
    while path and path[-1][0] >= indent and not stripped.startswith("- "):
        path.pop()
    keys = [k for _, k in path]
    if keys[-3:] == ["review", "agents", "remote_registered"]:
        found = LOGIN.match(line)
        if found:
            entries.append(found.group("value").strip().strip("'\""))
            continue
    if key and not stripped.startswith("- ") and not key.group("value").strip():
        path.append((indent, key.group("key")))

warned = False
for entry in entries:
    text = entry.strip()
    if BOT.fullmatch(text):
        continue
    warned = True
    if BARE.fullmatch(text):
        print(
            f"  [warn] config.yaml: review.agents.remote_registered names {text}, which reads as "
            f"a user's account. An App's account is written {text}[bot]: where the entry means "
            "the App, respell it, or its approvals are not told from a person's in human mode "
            "(DEC-079 point 3).",
            file=sys.stderr,
        )
    else:
        print(
            f"  [warn] config.yaml: review.agents.remote_registered names {text!r}, which names "
            "no account, so no account can be told from it: until it is mended, no approval "
            "counts as a person's in human mode, and human mode asks no member for a review "
            "(DEC-079 point 3).",
            file=sys.stderr,
        )
if not warned:
    print("  [ok] no registered reviewer agent whose reading changes what the gate counts")
PYEOF
exit 0
