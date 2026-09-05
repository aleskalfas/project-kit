#!/usr/bin/env bash
# project-management 0.55.0 — resource: retract the `unsupported: true`-means-
# board-carriage guidance where an adopter acted on it (DEC-051 decision point 2).
#
# Until the `board:` binding arm existed, `substrate-map.yaml` had no way to say
# "this axis lives on a field of my Projects-v2 board". So `pre-check`'s own
# remediation told adopters to write `unsupported: true` for a board-backed axis
# — a declaration the schema defines as the axis having NO encoding at all, with
# every rule needing it degrading. The kit instructed adopters to declare the
# opposite of what they meant, and at least one live map records exactly that on
# both affected axes, annotated in the adopter's own comments.
#
# The guidance is corrected at its source in this same change-set (pre-check's
# docstring + live remediation text, and the `adopt-existing` ceremony that
# manufactured the shape). This migration exists so the retraction also reaches
# the adopters who ALREADY followed the old advice and will never re-read the
# remediation that produced their map.
#
# DISCRETIONARY, and honestly so. `pkit migrations check-diff` reports NO
# migration is required for this change-set: nothing is renamed or removed in a
# kit-owned tree, no schema_version moves, no CLI signature breaks, and no
# adopter file changes meaning (the `board:` arm is purely additive — every
# existing map still validates and still behaves identically). The justification
# is not COR-010's trigger but a narrower one: the kit gave bad advice, and it
# should retract that advice where the adopter will actually see it. Do not read
# this script as evidence that the change-set owed a migration.
#
# WARN-ON-DETECT ONLY. This script PRINTS the one-line change and edits nothing.
# `project/substrate-map.yaml` is adopter-owned, hand-authored intent, and the
# capability already refuses to auto-edit files of that kind — the same posture
# as the 0.26.0 workflow.yaml override migration (`migrations/0.26.0/
# 001-workflow-yaml-schema-v4.sh`), for the same reason: auto-editing would risk
# silently clobbering adopter intent (the no-shared-files invariant + the COR-010
# discipline). DEC-051 requires it here for a second reason as well — the
# detection signature is NOT sound enough to apply silently:
#
#   * a `set-board-field` hook declares an opaque `field_id`, never an axis name,
#     so a hook writing a DIFFERENTLY-named field satisfies the signature while
#     having nothing to do with the axis; and
#   * an adopter can genuinely mean "this axis is disabled for the kit" while
#     separately running their own board hook — in which case `unsupported: true`
#     is exactly right and rewriting it would be the regression.
#
# The three-way signature it reports:
#   1. project/config.yaml declares `has_projects_v2_board: true`;
#   2. project/substrate-map.yaml marks `priority` and/or `workstream`
#      `unsupported: true` (the two axes the `board:` arm is admissible on —
#      `type` is label-carried by functional dependency and a board-carried
#      `state` awaits a detector kind, so neither can take the repair); and
#   3. project/hooks.yaml declares at least one `set-board-field` hook — the
#      corroborating signal that a board field is in fact being written.
#
# All three must hold. Any one missing and the state is not the workaround.
#
# Idempotent: a map already carrying `board: true` matches nothing (the axis is
# no longer `unsupported`), as does a map with no board, no hook, or no
# `unsupported` board-claimable axis. Every path exits 0 — this is a report, not
# a gate, and it must not break an upgrade.
#
# Run via the upgrade runtime with ROOT=<adopter root>.

set -euo pipefail

# ROOT is the adopter's project root, provided by the runtime.
: "${ROOT:?ROOT must be set by the upgrade runtime}"

CAP_DIR="$ROOT/.pkit/capabilities/project-management"
CONFIG_FILE="$CAP_DIR/project/config.yaml"
SUBSTRATE_MAP="$CAP_DIR/project/substrate-map.yaml"
HOOKS_FILE="$CAP_DIR/project/hooks.yaml"

if [ ! -d "$CAP_DIR" ]; then
    echo "  [skip] project-management capability not installed at $CAP_DIR"
    exit 0
fi

# Signal 2 first — it is the cheapest and the most selective. No map means
# greenfield: every axis reads the kit's own labels and the workaround cannot
# exist.
if [ ! -f "$SUBSTRATE_MAP" ]; then
    echo "  [ok] no project/substrate-map.yaml (greenfield); nothing to retract"
    exit 0
fi

# The scan is stdlib Python, no ruamel: a migration must not acquire a runtime
# dependency at upgrade time (the same call the 0.5.0 config-workstreams
# migration made). Block-style YAML only — that is what hand-authored maps and
# every `adopt-existing` draft use. A flow-style map is simply not detected: this
# report UNDER-reports rather than mis-reports, which is the right direction for
# a heuristic that ends in advice.
detection=$(python3 - "$CONFIG_FILE" "$SUBSTRATE_MAP" "$HOOKS_FILE" <<'PYEOF'
import re
import sys
from pathlib import Path

config_path, map_path, hooks_path = (Path(a) for a in sys.argv[1:4])

# The axes the `board:` arm is admissible on (DEC-051 decision point 2). `type`
# and `state` are excluded in the schema, so neither can take this repair even
# when marked `unsupported: true` under a board.
BOARD_DECLARABLE = ("priority", "workstream")


def read(path):
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


# --- signal 1: a configured board ---------------------------------------
config_text = read(config_path)
if config_text is None:
    print("NONE no project/config.yaml")
    raise SystemExit(0)
if not re.search(r"^has_projects_v2_board:\s*true\s*(#.*)?$", config_text, re.M):
    print("NONE no configured Projects-v2 board")
    raise SystemExit(0)

# --- signal 3: at least one set-board-field hook -------------------------
hooks_text = read(hooks_path)
if hooks_text is None or not re.search(
    r"^\s*-?\s*kind:\s*[\"']?set-board-field[\"']?\s*(#.*)?$", hooks_text, re.M
):
    print("NONE no `set-board-field` hook declared")
    raise SystemExit(0)

# --- signal 2: a board-declarable axis marked `unsupported: true` --------
# Indentation walk over the `axes:` block: find the top-level `axes:` key, then
# each axis key one level in, then `unsupported: true` inside that axis's block.
map_text = read(map_path)
if map_text is None:
    print("NONE project/substrate-map.yaml unreadable")
    raise SystemExit(0)

lines = map_text.splitlines()


def indent_of(line):
    return len(line) - len(line.lstrip(" "))


axes_indent = None
axis_indent = None
current_axis = None
found = []
for line in lines:
    if not line.strip() or line.lstrip().startswith("#"):
        continue
    ind = indent_of(line)
    stripped = line.strip()
    if axes_indent is None:
        if ind == 0 and re.match(r"^axes:\s*(#.*)?$", stripped):
            axes_indent = ind
        continue
    if ind <= axes_indent:
        break  # left the `axes:` block entirely
    if axis_indent is None:
        axis_indent = ind
    if ind == axis_indent:
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(#.*)?$", stripped)
        current_axis = m.group(1) if m else None
        continue
    if (
        current_axis in BOARD_DECLARABLE
        and re.match(r"^unsupported:\s*true\s*(#.*)?$", stripped)
        and current_axis not in found
    ):
        found.append(current_axis)

if not found:
    print("NONE no board-declarable axis marked `unsupported: true`")
    raise SystemExit(0)

print("MATCH " + " ".join(found))
PYEOF
)

if [ "${detection%% *}" != "MATCH" ]; then
    echo "  [ok] withdrawn guidance not in use — ${detection#NONE }"
    exit 0
fi

matched_axes=${detection#MATCH }

cat <<EOF
  [warn] your substrate-map declares a board-carried axis the way the kit used to
         tell you to, and that instruction has been withdrawn:

    File:  $SUBSTRATE_MAP
    Axes:  $matched_axes

  Each of those axes is marked \`unsupported: true\` while project/config.yaml
  configures a Projects-v2 board and project/hooks.yaml declares a
  \`set-board-field\` hook — the shape pre-check's old remediation asked for when
  the map had no way to name the board.

  \`unsupported: true\` means the axis has NO encoding and every rule needing it
  DEGRADES. It is not how you say "my board carries this" — it says the opposite.

  The one-line change, per axis (project-management:DEC-051 decision point 2):

      axes:
        <axis>:
    -     unsupported: true
    +     board: true

  \`board: true\` is parameterless by design: the field's identity stays a write
  parameter on your \`after_create_issue\` \`set-board-field\` hook, which is
  already where you declared it. Nothing else moves.

  NOT APPLIED AUTOMATICALLY, deliberately, on two grounds:

    1. project/substrate-map.yaml is your hand-authored intent, and this
       capability does not auto-edit adopter-owned files.
    2. The detection is a heuristic, not a proof. A \`set-board-field\` hook names
       an opaque \`field_id\`, never an axis — so a hook writing a different
       field satisfies the signature. And "disabled for the kit, while I run my
       own board hook" is a legitimate configuration in which
       \`unsupported: true\` is exactly right. Only you can tell which you meant.

  Verify with:
    pkit schemas validate
    <root>/.pkit/capabilities/project-management/scripts/pre-check.py

  See:
    $CAP_DIR/decisions/DEC-051-axis-carriage-activation.md
    $CAP_DIR/schemas/substrate-map.schema.json  (the \`board\` property)

  Re-running this migration after the edit is a no-op: an axis carrying
  \`board: true\` is no longer \`unsupported\` and matches nothing.
EOF

exit 0
