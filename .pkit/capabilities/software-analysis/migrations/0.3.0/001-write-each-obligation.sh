#!/usr/bin/env bash
# software-analysis 0.3.0 — resource: write-each-obligation.
#
# From 0.3.0 each requirement, of each of the three kinds and withdrawn or not,
# carries `obligation`, a fingerprint of its statement, its measure and where it
# holds, and `pkit analysis validate` fails a requirement without it, whatever
# any rule's status (software-analysis DEC-006 point 6). A project's
# requirements written before 0.3.0 hold none. This migration writes it on each,
# so no requirement fails validation for lacking it (COR-010; DEC-006,
# Implications).
#
# The value is the capability's to compute, in one place: the migration reads
# the plan `pkit analysis obligation --dry-run --json` prints, which writes
# nothing, and writes each file as the plan gives it. The `pkit` it runs is the
# running pkit, which the migration runner puts first on the `PATH` (ADR-065
# point 14), and the command is the capability's own, at the version the
# upgrade copied.
#
# The positive sign it acts on: the plan names a requirement that holds no
# `obligation` (`was` is null), and the file still reads as the plan read it,
# with only the field's line to add. A requirement whose value no longer
# matches its texts is the project's to write anew, as validation names it, and
# the migration leaves it. A requirement it cannot read is named, with the
# command that writes it.
#
# Adding the field changes each requirement's content, so the change that
# commits this upgrade flags what anchors each requirement, such as the use
# cases and journeys that list it, and answers each, as COR-050 point 5 asks.
#
# Never fails the upgrade: where pkit or python3 is missing, or the plan cannot
# be read (the command failed, or this script runs by hand under another pkit),
# it writes nothing, warns, and names the command that writes the field.
#
# Idempotent: once every requirement carries `obligation`, the plan names none
# that holds no value, and nothing is written.

set -euo pipefail

# ROOT is the adopter's project root, provided by the runtime.
: "${ROOT:?ROOT must be set by the upgrade runtime}"

COMMAND="pkit analysis obligation"

warn_and_stop() {
    echo "  [warn] no requirement's obligation written: $1"
    echo "         after the upgrade, \`$COMMAND\` writes each, and \`pkit analysis validate\` names any left"
    exit 0
}

if ! command -v pkit >/dev/null 2>&1; then
    warn_and_stop "no pkit on PATH, so the capability's plan cannot be read"
fi
if ! command -v python3 >/dev/null 2>&1; then
    warn_and_stop "no python3 on PATH to read the capability's plan"
fi

# The command exits 1 where it names a requirement it cannot read, and still
# prints its plan, so the plan decides, never the exit code.
plan="$(cd "$ROOT" && pkit analysis obligation --dry-run --json 2>/dev/null)" || true

# The plan is read with the standard library only: a migration acquires no
# runtime dependency at upgrade time. `-I` keeps the project's root, the working
# folder, off the import path, so no file there shadows a standard module.
result="$(PLAN="$plan" python3 -I - "$ROOT" <<'PYEOF'
import json
import os
import sys
import tempfile
from pathlib import Path, PurePosixPath

root = Path(sys.argv[1])
try:
    document = json.loads(os.environ.get("PLAN", ""))
except ValueError:
    document = None
if (
    not isinstance(document, dict)
    or document.get("schema_version") != 1
    or document.get("dry_run") is not True
    or not isinstance(document.get("written"), list)
):
    print("UNREADABLE")
    raise SystemExit(0)


def write_whole(target: Path, text: str) -> None:
    mode = target.stat().st_mode & 0o7777
    handle, temporary = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.")
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(text.encode("utf-8"))
        os.chmod(temporary, mode)
        os.replace(temporary, target)
    except BaseException:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


lines = []
for entry in document["written"]:
    if not isinstance(entry, dict):
        continue
    path, value, text = entry.get("path"), entry.get("value"), entry.get("text")
    named = entry.get("id") or path
    if entry.get("was") is not None:
        lines.append(f"STALE {named}")
        continue
    relative = PurePosixPath(path) if isinstance(path, str) and path else None
    if (
        relative is None
        or relative.is_absolute()
        or ".." in relative.parts
        or not isinstance(value, str)
        or not isinstance(text, str)
    ):
        lines.append(f"SKIPPED {named} the plan gives no file to write")
        continue
    target = root / relative
    if target.is_symlink() or not target.is_file():
        lines.append(f"SKIPPED {named} {path} is no file the analysis holds")
        continue
    try:
        current = target.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        lines.append(f"SKIPPED {named} {path} cannot be read ({exc})")
        continue
    end = "\r\n" if "\r\n" in text else "\n"
    if text.replace(f"obligation: {value}{end}", "", 1) != current:
        lines.append(f"SKIPPED {named} {path} changed since the plan read it")
        continue
    write_whole(target, text)
    lines.append(f"WROTE {named} {path}")
for problem in document.get("problems") or []:
    if isinstance(problem, dict):
        lines.append(f"PROBLEM {problem.get('path')} {problem.get('why')}")
print("\n".join(lines) if lines else "NONE")
PYEOF
)" || result="UNREADABLE"

if [ "$result" = "UNREADABLE" ]; then
    warn_and_stop "the capability's plan could not be read: the command failed, or this script runs by hand under another pkit"
fi
if [ "$result" = "NONE" ]; then
    echo "  exists  every requirement carries its obligation: nothing written"
    exit 0
fi

while IFS= read -r line; do
    case "$line" in
        WROTE\ *)
            rest="${line#WROTE }"
            echo "  [ok] wrote the obligation of ${rest%% *} at ${rest#* } (DEC-006 point 6)"
            ;;
        STALE\ *)
            echo "  exists  ${line#STALE } carries an obligation already, which no longer matches its texts: \`$COMMAND\` writes it anew"
            ;;
        SKIPPED\ *)
            rest="${line#SKIPPED }"
            echo "  [warn] ${rest%% *}'s obligation not written: ${rest#* }; \`$COMMAND\` writes it"
            ;;
        PROBLEM\ *)
            echo "  [warn] ${line#PROBLEM }; \`$COMMAND\` writes the obligation once it can read the requirement"
            ;;
    esac
done <<< "$result"
