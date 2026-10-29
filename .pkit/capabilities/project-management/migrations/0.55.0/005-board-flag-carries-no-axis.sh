#!/usr/bin/env bash
# project-management 0.55.0 — structural: the board flag carries no axis.
#
# [project-management:DEC-062-axes-chosen-in-the-map] ends the carriage of
# `has_projects_v2_board`: the flag now says only that the project has a
# Projects v2 board, and an axis lives on the board only where
# `project/substrate-map.yaml` binds it there with `board: true` (point 1). An
# axis the map does not bind reads as it does with no board: the kit's own labels
# with no map, and degraded in a present map (point 2). The version of the
# configuration's schema, `schema_version` in `project/config.yaml`, moves from 1
# to 2 with it, and marks this migration as run (point 6).
#
# It acts only where `project/config.yaml` is at version 1, and writes version 2
# there, in every project. Where the flag is set, it keeps what the flag carried
# on the board, and keeps the state as it is read:
#
#   - priority and workstream stay on the board: each the map omits or marks
#     `unsupported: true` gets `board: true`, and its `default:` is kept;
#   - state gets no binding, in a present map or in one this writes: it is read
#     from the native primitives as it was, and the board's Status stays with the
#     project's people (point 5);
#   - with no map, it writes one: `board: true` on priority and workstream,
#     `kit-label: true` on type, and state left out, which behaves as no map but
#     for those board bindings and the state left out (point 4);
#   - in a present map, it keeps the comments and every other key, and changes
#     only priority and workstream.
#
# Its report names each binding it wrote, and each comment of the map that
# speaks of the board, which this change may leave false: the map is the
# adopter's to change, now and later. Where the flag is not set, only the version
# moves.
#
# A map whose `axes:` or an axis to change is written as a one-line flow mapping
# (`{...}`) is not edited: nothing is written, the version stays 1, and the
# migration stops the upgrade, naming the edit to make by hand, so the flag's
# carriage is never dropped unsaid. Block style is what hand-written maps and
# every `adopt-existing` draft use. The map is read line by line, with no YAML
# parser: the runtime guarantees only bash, and stdlib python3.
#
# Idempotent: once the configuration is at version 2, every later run changes
# nothing. A run stopped between its two writes finds the map's bindings already
# written, writes none again, and moves the version.
#
# Run via the upgrade runtime with ROOT=<adopter root>.

set -euo pipefail

# ROOT is the adopter's project root, provided by the runtime.
: "${ROOT:?ROOT must be set by the upgrade runtime}"

CAP_DIR="$ROOT/.pkit/capabilities/project-management"
CONFIG="$CAP_DIR/project/config.yaml"
SUBSTRATE_MAP="$CAP_DIR/project/substrate-map.yaml"

if [ ! -d "$CAP_DIR" ]; then
    echo "  [skip] project-management capability not installed at $CAP_DIR"
    exit 0
fi
if [ ! -f "$CONFIG" ]; then
    echo "  [skip] no project/config.yaml: no configuration to carry to version 2"
    exit 0
fi
if ! command -v python3 >/dev/null 2>&1; then
    echo "  [error] python3 is needed to carry project/config.yaml to version 2, and none is on PATH" >&2
    exit 1
fi

python3 - "$CONFIG" "$SUBSTRATE_MAP" <<'PYEOF'
import os
import re
import sys
from pathlib import Path

config_path, map_path = Path(sys.argv[1]), Path(sys.argv[2])
BOARD_AXES = ("priority", "workstream")
TRUE = ("true", "True", "TRUE")

VERSION_RE = re.compile(r"^schema_version[ \t]*:[ \t]*(?P<value>[^#\s]+)(?P<rest>.*)$")
FLAG_RE = re.compile(r"^has_projects_v2_board[ \t]*:[ \t]*(?P<value>[^#\s]+)")
KEY_RE = re.compile(r"^(?P<indent>[ ]*)(?P<key>[A-Za-z0-9_-]+)[ \t]*:(?P<value>.*)$")

CREATED_MAP = """\
# project/substrate-map.yaml — written by the project-management 0.55.0 upgrade
# (DEC-062 point 6). The board flag, `has_projects_v2_board`, no longer puts any
# axis on the board: an axis lives there only where this map binds it with
# `board: true`. This map keeps priority and workstream on the board, where the
# flag carried them, and type on the kit's own labels, as with no map.
#
# State is left out, so it degrades: it is read from the issues themselves as it
# was, and the capability writes no board Status for it. Bind it here once you
# have chosen where it lives (DEC-062 point 5). This file is yours to change.
schema_version: 1
pkit_schema: project-management:substrate-map
axes:
  type:
    kit-label: true
  priority:
    board: true
  workstream:
    board: true
"""


def strip_comment(text):
    return text.split("#", 1)[0].strip()


def write(path, text):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


config_lines = config_path.read_text(encoding="utf-8").splitlines(keepends=True)
version_at = None
version = None
flag = False
for index, line in enumerate(config_lines):
    body = line.rstrip("\r\n")
    match = VERSION_RE.match(body)
    if match and version_at is None:
        version_at, version = index, match.group("value").strip("'\"")
    match = FLAG_RE.match(body)
    if match and match.group("value") in TRUE:
        flag = True

if version_at is None:
    print("  [warn] project/config.yaml declares no schema_version, so it was left as it is;")
    print("         add `schema_version: 1` and run the upgrade again, or declare the axes by hand")
    sys.exit(0)
if version == "2":
    print("  exists  project/config.yaml is at version 2: the board flag carries no axis already")
    sys.exit(0)
if version != "1":
    print(f"  [warn] project/config.yaml is at version {version}, not 1, so it was left as it is")
    sys.exit(0)

reports = []
if flag and not map_path.exists():
    write(map_path, CREATED_MAP)
    reports.append(
        "  [ok] wrote project/substrate-map.yaml: `board: true` on priority and workstream, "
        "which the board flag carried, `kit-label: true` on type, and state left out"
    )
elif flag:
    lines = map_path.read_text(encoding="utf-8").splitlines(keepends=True)
    axes_at = None
    for index, line in enumerate(lines):
        match = KEY_RE.match(line.rstrip("\r\n"))
        if match and not match.group("indent") and match.group("key") == "axes":
            if strip_comment(match.group("value")):
                print(
                    "  [error] project/substrate-map.yaml writes `axes:` as a one-line flow "
                    "mapping, which this migration does not edit. Nothing was written.",
                    file=sys.stderr,
                )
                print(
                    "          Write `axes:` in block style, then run the upgrade again; or "
                    "give priority and workstream `board: true` by hand, as the board flag "
                    "carried them, and set `schema_version: 2` in project/config.yaml.",
                    file=sys.stderr,
                )
                sys.exit(1)
            axes_at = index
            break
    axes = {}
    axis_indent = None
    child_indent = None
    last = None
    if axes_at is not None:
        current = None
        last = axes_at
        for index in range(axes_at + 1, len(lines)):
            body = lines[index].rstrip("\r\n")
            if not body.strip() or body.lstrip().startswith("#"):
                continue
            indent = len(body) - len(body.lstrip(" "))
            if indent == 0:
                break
            last = index
            if axis_indent is None:
                axis_indent = indent
            match = KEY_RE.match(body)
            if indent == axis_indent and match:
                current = match.group("key")
                axes[current] = {"at": index, "value": strip_comment(match.group("value")), "arms": {}}
            elif current is not None and match:
                if child_indent is None:
                    child_indent = indent
                if indent == child_indent:
                    axes[current]["arms"][match.group("key")] = (index, strip_comment(match.group("value")))
    axis_indent = axis_indent or 2
    child_indent = child_indent or axis_indent * 2

    edits = {}
    inserts = []
    flow = []
    for axis in BOARD_AXES:
        found = axes.get(axis)
        if found is None:
            inserts.append(f"{' ' * axis_indent}{axis}:\n{' ' * child_indent}board: true\n")
            reports.append(
                f"  [ok] wrote `{axis}: {{board: true}}` in project/substrate-map.yaml: the "
                "map left it out, and the board flag carried it"
            )
            continue
        if found["value"]:
            if "unsupported" in found["value"]:
                flow.append(axis)
            continue
        unsupported = found["arms"].get("unsupported")
        if unsupported is not None and unsupported[1] in TRUE:
            index = unsupported[0]
            body = lines[index]
            edits[index] = re.sub(r"unsupported([ \t]*):[ \t]*(true|True|TRUE)", r"board\1: true", body, count=1)
            reports.append(
                f"  [ok] wrote `board: true` for `{axis}` in project/substrate-map.yaml, in "
                "place of `unsupported: true`: the board flag carried it"
                + (", and its `default:` is kept" if "default" in found["arms"] else "")
            )
    if flow:
        names = " and ".join(flow)
        print(
            f"  [error] project/substrate-map.yaml writes {names} as a one-line flow mapping "
            "marked `unsupported`, which this migration does not edit. Nothing was written.",
            file=sys.stderr,
        )
        print(
            f"          Write {names} in block style, then run the upgrade again; or give "
            "each `board: true` by hand, as the board flag carried it, and set "
            "`schema_version: 2` in project/config.yaml.",
            file=sys.stderr,
        )
        sys.exit(1)
    for index, text in edits.items():
        lines[index] = text
    if inserts:
        if axes_at is None:
            if lines and not lines[-1].endswith("\n"):
                lines[-1] += "\n"
            lines.append("axes:\n")
            lines.extend(inserts)
        else:
            if not lines[last].endswith("\n"):
                lines[last] += "\n"
            lines[last + 1 : last + 1] = inserts
    if edits or inserts:
        write(map_path, "".join(lines))
    else:
        reports.append(
            "  exists  project/substrate-map.yaml binds priority and workstream already: no "
            "binding written"
        )
    spoken = [
        (number, line.strip())
        for number, line in enumerate(lines, start=1)
        if "#" in line and re.search(r"board|flag", line.split("#", 1)[1], re.IGNORECASE)
    ]
    if spoken:
        reports.append(
            "  [warn] these comments in project/substrate-map.yaml speak of the board, and the "
            "board flag no longer carries any axis (DEC-062), so check each still says what "
            "you mean; the map is yours to change:"
        )
        reports.extend(f"           line {number}: {text}" for number, text in spoken)

match = VERSION_RE.match(config_lines[version_at].rstrip("\r\n"))
ending = config_lines[version_at][len(config_lines[version_at].rstrip("\r\n")) :]
config_lines[version_at] = f"schema_version: 2{match.group('rest')}{ending}"
write(config_path, "".join(config_lines))

for line in reports:
    print(line)
if flag:
    print(
        "  [ok] project/config.yaml schema_version 1 → 2: the board flag says only that a "
        "board exists, and your map now says which axes live on it (DEC-062)"
    )
    print(
        "       state stays as it was read, and the board's Status stays with your people; "
        "bind state in the map once you choose where it lives (DEC-062 point 5)"
    )
else:
    print(
        "  [ok] project/config.yaml schema_version 1 → 2: no board flag is set, so no axis "
        "moved (DEC-062)"
    )
PYEOF
