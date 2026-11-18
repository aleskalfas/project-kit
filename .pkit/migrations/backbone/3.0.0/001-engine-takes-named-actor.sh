#!/usr/bin/env bash
# Backbone migration 3.0.0 — resource: engine-takes-named-actor.
#
# The process engine takes only the actor its caller names (ADR-098). Its move
# no longer asks `gh` for the login, nor its status view and its move check take
# `operator`, where the caller names no actor. With none named, a cross-authority
# gate (`authorisation-artifact`) whose authorisation names its producer is not
# judged: a move through it is refused, and the status view marks it `?`. The
# flag's meaning changes where it is left out, one of COR-010's triggers, so the
# change ships this migration in the same change-set.
#
# What this migration is (and is NOT):
#   - A GUIDANCE migration. The call that leaves the actor out is a binding's
#     code, which names its actor by its own records, and no migration can know
#     which authority a binding's moves are made by. So it updates nothing.
#   - Its positive sign is a process definition whose callers the release does
#     not bring and that holds an `authorisation-artifact` gate: one of a
#     capability the manifest records as incubated in the repository or as
#     sourced from another repository (COR-031 D2, COR-041). A capability recorded
#     with neither origin is one the methodology ships, and the same release
#     brings its callers, so it gets no warning.
#   - It reads the manifest and each such capability's `schemas/*.yaml` with
#     python3's standard library, line by line, and imports no backbone.
#
# Idempotent and safe over any state (COR-010): it writes nothing, so running it
# again, over any state, prints the same guidance or the same clean line. Where
# python3 is missing it says what it could not read, and exits clean.

set -euo pipefail

# ROOT is the adopter's project root, provided by the runtime.
: "${ROOT:?ROOT must be set by the upgrade runtime}"

if ! command -v python3 >/dev/null 2>&1; then
    echo "  [warn] no python3 on PATH, so the process definitions were not read. A caller" >&2
    echo "         of \`pkit process status\`, \`can-move\` or \`move\` now names the actor," >&2
    echo "         in its binding's terms, for a cross-authority gate to be judged." >&2
    exit 0
fi

FIND='
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
manifest = root / ".pkit" / "manifest.yaml"
CALLERS_ELSEWHERE = {"incubated-in-repo", "externally-sourced"}


def capabilities(text):
    """Each capability the manifest registers, with its origin ("" where none)."""
    found, current = [], None
    for line in text.splitlines():
        item = re.match(r"^\s*-\s+kind:\s*[\"\x27]?(\w+)", line)
        if item:
            current = {"kind": item.group(1), "name": None, "origin": ""}
            found.append(current)
            continue
        field = re.match(r"^\s+(name|origin):\s*[\"\x27]?([^\"\x27#\s]+)", line)
        if field and current is not None:
            current[field.group(1)] = field.group(2)
    return [c for c in found if c["kind"] == "capability" and c["name"]]


def gates(text):
    """The process id, and the `from`, `to` and `trigger` of each transition
    whose gate is an `authorisation-artifact`, as far as the item names them."""
    process_id, found, item = None, [], {}
    in_process = False
    item_indent = None
    for line in text.splitlines():
        if re.match(r"^process:\s*$", line):
            in_process = True
            continue
        if in_process and re.match(r"^\S", line):
            in_process = False
        if not in_process:
            continue
        ident = re.match(r"^  id:\s*[\"\x27]?([^\"\x27#\s]+)", line)
        if ident:
            process_id = ident.group(1)
        if re.match(r"^\s*transitions:\s*$", line):
            item_indent = None
            item = {}
            continue
        entry = re.match(r"^(\s*)-\s", line)
        if entry and (item_indent is None or len(entry.group(1)) == item_indent):
            if item_indent is None:
                item_indent = len(entry.group(1))
            item = {}
        key = re.match(r"^\s*-?\s*(from|to|trigger):\s*[\"\x27]?([^\"\x27#\s]+)", line)
        if key and key.group(1) not in item:
            item[key.group(1)] = key.group(2)
        if re.search(r"kind:\s*[\"\x27]?authorisation-artifact", line):
            found.append(dict(item))
    return process_id, found


if not manifest.is_file():
    sys.exit(0)
for capability in capabilities(manifest.read_text(encoding="utf-8")):
    if capability["origin"] not in CALLERS_ELSEWHERE:
        continue
    schemas = root / ".pkit" / "capabilities" / capability["name"] / "schemas"
    if not schemas.is_dir():
        continue
    for path in sorted(schemas.glob("*.yaml")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "authorisation-artifact" not in text:
            continue
        process_id, found = gates(text)
        if process_id is None:
            continue
        where = path.relative_to(root)
        for gate in found or [{}]:
            move = " -> ".join(gate[k] for k in ("from", "to") if k in gate)
            trigger = " [" + gate["trigger"] + "]" if "trigger" in gate else ""
            named = "the move " + move + trigger if move or trigger else "a transition"
            print("%s:%s (%s): %s" % (capability["name"], process_id, where, named))
'

found="$(python3 -I -c "$FIND" "$ROOT")" || found=""

if [ -z "$found" ]; then
    echo "  [skip] no process definition whose callers this release does not bring holds a"
    echo "         cross-authority gate; nothing to change"
    exit 0
fi

echo "  [warn] these process definitions hold a cross-authority (\`authorisation-artifact\`)" >&2
echo "         gate, and their callers are the project's own code:" >&2
while IFS= read -r line; do
    echo "           ${line}" >&2
done <<<"$found"
echo "         The engine now takes only the actor its caller names (ADR-098): \`pkit" >&2
echo "         process move\` no longer takes the \`gh\` login, nor \`status\` and \`can-move\`" >&2
echo "         take \`operator\`. A caller of the status view, the move check and the move" >&2
echo "         names the actor with \`--actor\`, in the binding's terms, for such a gate to" >&2
echo "         be judged. With none named, a gate whose authorisation names its producer" >&2
echo "         refuses the move, and the status view marks it \`?\`." >&2

# Guidance delivered: the binding's code is the project's to change, so this is
# not a failure. Exit clean so `pkit upgrade` proceeds.
exit 0
