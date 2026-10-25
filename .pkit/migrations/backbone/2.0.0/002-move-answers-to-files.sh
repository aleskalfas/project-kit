#!/usr/bin/env bash
# Backbone migration 2.0.0 — resource: move-answers-to-files.
#
# A change's answers to friction live in answer files of its own, in
# `.pkit/project/friction/answers/`, no longer in the artefacts' front matter
# (COR-062; ADR-068). A project's existing answers move out of the blocks once
# (COR-062 point 11). This migration makes that move.
#
# What it reads, and what it writes:
#   - The plan is the backbone's: `pkit friction move-plan --json`, a reading
#     command (the lifecycle README, "Script contract"). It names each answer
#     file the move adds, `moved-<hash>.yaml` with its content, and each
#     artefact file's new text, its blocks' answers taken out. The script writes
#     those bytes with python3's standard library and imports no backbone.
#   - The plan leaves out every file the project receives by sync: those answers
#     are their source's (COR-062 point 9). It leaves any artefact whose answers
#     would not read back in the answer files' shape, and says why.
#
# Safe over any state (COR-010). Its positive sign is a block that holds an
# answer, which the plan names with the artefact file's bytes as it read them.
#   - An artefact file is rewritten only while it still holds those bytes.
#   - An answer file is only ever created, never written over. One already there
#     with the plan's content was written by an earlier run, and counts as
#     written. One there with other content leaves its artefact file as it is.
#   - Answer files go first and the artefact file last, so a run stopped midway
#     leaves the answers in the block, and the next run finishes the move.
#
# Idempotent: once moved, no block holds an answer, so the plan is empty and a
# second run writes nothing. It deletes no file.
#
# Never fails the upgrade: where pkit or python3 is missing, or the plan cannot
# be read, it moves nothing and warns. A backbone that reads answer files says
# so again over a project whose answers have not moved (COR-062 point 11).

set -euo pipefail

# ROOT is the adopter's project root, provided by the runtime.
: "${ROOT:?ROOT must be set by the upgrade runtime}"

PLAN_COMMAND="pkit friction move-plan"

warn_and_stop() {
    echo "  [warn] no answers moved: $1"
    echo "         \`$PLAN_COMMAND\` shows the move; run this migration again to make it"
    exit 0
}

if ! command -v pkit >/dev/null 2>&1; then
    warn_and_stop "no pkit on PATH, so the backbone's plan cannot be read"
fi
if ! command -v python3 >/dev/null 2>&1; then
    warn_and_stop "no python3 on PATH to read the backbone's plan"
fi

plan="$(cd "$ROOT" && pkit friction move-plan --json 2>/dev/null)" || plan=""

# The plan is read from standard input, with the standard library only: a
# migration acquires no runtime dependency at upgrade time. `-I` keeps the
# project's root, the working folder, off the import path, so no file there
# shadows a standard module.
APPLY=$(cat <<'PYEOF'
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path, PurePosixPath

FOLDER = ".pkit/project/friction/answers"
MOVED = re.compile(r"^moved-[0-9a-f]{12}\.yaml$")

root = Path(sys.argv[1])
try:
    document = json.loads(sys.stdin.read())
except ValueError:
    document = None
if (
    not isinstance(document, dict)
    or document.get("schema_version") != 1
    or document.get("report") != "move-plan"
    or document.get("folder") != FOLDER
    or not isinstance(document.get("files"), list)
):
    print("UNREADABLE")
    raise SystemExit(0)


def relative(path):
    """`path` as a path inside the project, or None: relative, no `..`."""
    if not isinstance(path, str) or not path:
        return None
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts or "." in pure.parts:
        return None
    return pure


def inside(pure):
    """Whether every folder from the root to `pure`'s is a folder of the project's own,
    or not there yet: never a link, which would write elsewhere."""
    current = root
    for part in pure.parts[:-1]:
        current = current / part
        if current.is_symlink() or (current.exists() and not current.is_dir()):
            return False
    return True


moved = 0
written = 0
for file in document["files"]:
    rel = relative(file.get("path"))
    answers = file.get("answers") or []
    text = file.get("text")
    if rel is None or not isinstance(text, str) or not isinstance(answers, list):
        print(f"SKIP {file.get('path')!r}: the plan's entry for it cannot be read")
        continue
    target = root / rel
    if not inside(rel) or target.is_symlink() or not target.is_file():
        print(f"SKIP {rel}: not a file of the project's own")
        continue
    if hashlib.sha256(target.read_bytes()).hexdigest() != file.get("sha256"):
        print(f"SKIP {rel}: it changed since the plan read it; run the migration again")
        continue
    # Every answer file first: each created, or there already as the plan gives it.
    pending = []
    blocked = None
    for answer in answers:
        arel = relative(answer.get("path") if isinstance(answer, dict) else None)
        data = answer.get("text") if isinstance(answer, dict) else None
        if (
            arel is None
            or str(arel.parent) != FOLDER
            or not MOVED.match(arel.name)
            or not isinstance(data, str)
        ):
            blocked = "the plan names an answer file outside the answer folder"
            break
        apath = root / arel
        if not inside(arel):
            blocked = f"{FOLDER} is a link or a file, not a folder of the project's own"
            break
        if apath.is_symlink() or apath.exists():
            if not apath.is_symlink() and apath.is_file() and apath.read_bytes() == data.encode("utf-8"):
                continue
            blocked = f"{arel} holds other content, and an answer file is never written over"
            break
        pending.append((apath, data.encode("utf-8")))
    if blocked is not None:
        print(f"SKIP {rel}: {blocked}")
        continue
    try:
        for apath, data in pending:
            apath.parent.mkdir(parents=True, exist_ok=True)
            with open(apath, "xb") as handle:
                handle.write(data)
            written += 1
        # Then the artefact file, atomically, keeping its mode.
        mode = target.stat().st_mode & 0o7777
        descriptor, temporary = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.")
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(text.encode("utf-8"))
            os.chmod(temporary, mode)
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    except OSError as error:
        print(f"SKIP {rel}: it could not be written ({error}); run the migration again")
        continue
    moved += 1
    print(f"MOVED {rel}")
for left in document.get("left") or []:
    if isinstance(left, dict):
        print(f"LEFT {left.get('artefact')}: {left.get('reason')}")
print(f"DONE {moved} {written}")
PYEOF
)

result="$(printf '%s' "$plan" | python3 -I -c "$APPLY" "$ROOT")" || result="UNREADABLE"

case "$result" in
    UNREADABLE*)
        warn_and_stop "the backbone's plan could not be read: the command failed, or this script runs by hand under another pkit"
        ;;
esac

while IFS= read -r line; do
    case "$line" in
        MOVED\ *) echo "  [ok] moved the answers out of ${line#MOVED }" ;;
        SKIP\ *) echo "  [warn] left as it is: ${line#SKIP }" ;;
        LEFT\ *) echo "  [skip] ${line#LEFT }" ;;
        DONE\ *)
            counts="${line#DONE }"
            files="${counts% *}"
            answers="${counts#* }"
            if [ "$files" = "0" ] && [ "$answers" = "0" ]; then
                echo "  [skip] no block holds an answer to move; nothing to change"
            else
                echo "  [ok] moved the answers of $files artefact file(s) into $answers new answer file(s) in .pkit/project/friction/answers/ (COR-062 point 11)"
            fi
            ;;
    esac
done <<<"$result"
