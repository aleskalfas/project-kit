#!/usr/bin/env bash
# project-management 0.55.0 — resource: report the two carriage states an adopter
# may be holding after DEC-051 — the withdrawn `unsupported: true`-means-board
# guidance, and the label-bound-under-a-board shape whose corpus may need repair.
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
# TWO conditions are reported, out of one walk of the map. Both require a
# configured board (`has_projects_v2_board: true` in project/config.yaml);
# neither is reported without one.
#
# CONDITION A — the withdrawn guidance. project/substrate-map.yaml marks
#   `priority` and/or `workstream` `unsupported: true` (the two axes the
#   `board:` arm is admissible on — `type` is label-carried by functional
#   dependency and a board-carried `state` awaits a detector kind, so neither
#   can take the repair), AND project/hooks.yaml declares at least one
#   `set-board-field` hook. The hook is required here and that is deliberate:
#   without one, an axis marked `unsupported: true` is most likely what it says
#   — disabled — rather than the workaround. Reports the one-line edit to
#   `board: true`.
#
# CONDITION B — the reported failure's own shape. The map binds `priority`,
#   `workstream` or `state` with a `label:` arm. NO hook is required: a label
#   binding under a board IS the two-claimant state on its own. Until DEC-051
#   nothing decided which declaration won, so issues filed before this release
#   may carry a value on neither substrate. Reports `pkit pm back-fill` as the
#   way to find out, and says plainly that this script has not looked — that
#   means reading issues, and a migration makes no network calls.
#
#   Condition B was added because the original signature missed the adopter who
#   needed it most: the reported configuration has no hook, so it matched
#   nothing and saw nothing on upgrade, while its corpus was the damaged one.
#
# Either condition may fire alone, or both together on different axes — a map
# carrying `board: true` on one axis and a `label:` binding on another reports B
# for the second while matching nothing for the first.
#
# Idempotent: an axis moved to `board: true` is no longer `unsupported` and no
# longer `label`-bound, so it matches neither condition on a re-run. A project
# with no configured board matches nothing at all. Every path exits 0 — this is
# a report, not a gate, and it must not break an upgrade; the scan is guarded so
# that even a missing `python3` reports rather than aborting the run.
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

# The axes a configured board claims when the map is silent. Wider than the
# declarable set: `state` cannot take a `board:` arm yet, but a board DOES carry
# it absent a binding — so a `label:` binding on it is the same two-claimant
# shape, and its corpus is damaged the same way.
BOARD_CLAIMED = ("priority", "workstream", "state")


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

# --- read the map once; two conditions are scanned out of it ------------
map_text = read(map_path)
if map_text is None:
    print("NONE project/substrate-map.yaml unreadable")
    raise SystemExit(0)

lines = map_text.splitlines()


def indent_of(line):
    return len(line) - len(line.lstrip(" "))


# Indentation walk over the `axes:` block: find the top-level `axes:` key, then
# each axis key one level in, then the arm inside that axis's block.
axes_indent = None
axis_indent = None
current_axis = None
unsupported = []   # condition A — the withdrawn guidance
label_bound = []   # condition B — the reported failure's own shape
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
        and current_axis not in unsupported
    ):
        unsupported.append(current_axis)
    if (
        current_axis in BOARD_CLAIMED
        and re.match(r"^label:\s*(#.*)?$", stripped)
        and current_axis not in label_bound
    ):
        label_bound.append(current_axis)

# Condition A additionally requires a board-writing hook: without one, an axis
# marked `unsupported: true` is most likely what it says — disabled — rather
# than the withdrawn workaround. Condition B needs no hook; a `label:` binding
# under a board IS the reported shape on its own.
hooks_text = read(hooks_path)
has_hook = bool(hooks_text) and bool(re.search(
    r"^\s*-?\s*kind:\s*[\"']?set-board-field[\"']?\s*(#.*)?$", hooks_text, re.M
))
if not has_hook:
    unsupported = []

if not unsupported and not label_bound:
    print("NONE no board-claimed axis is bound to labels or marked `unsupported: true`")
    raise SystemExit(0)

print("MATCH|" + " ".join(unsupported) + "|" + " ".join(label_bound))
PYEOF
) || detection="NONE the scan could not run (python3 unavailable or the scan failed)"
# `|| …` rather than letting `set -e` propagate: this script's contract is that
# every path exits 0, because a REPORT must never break an upgrade. Without the
# guard a missing python3 aborts the whole run for the sake of advice.

if [ "${detection%%|*}" != "MATCH" ]; then
    echo "  [ok] no action needed — ${detection#NONE }"
    exit 0
fi

rest=${detection#MATCH|}
matched_axes=${rest%%|*}
label_axes=${rest#*|}

if [ -n "$matched_axes" ]; then
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
    [ -n "$label_axes" ] && echo
fi

if [ -n "$label_axes" ]; then
cat <<EOF
  [warn] issues filed before this upgrade may carry no value for an axis your
         map binds to labels, on EITHER substrate:

    File:  $SUBSTRATE_MAP
    Axes:  $label_axes

  project/config.yaml configures a Projects-v2 board while your map binds those
  axes to your own labels. Until this release nothing decided which declaration
  won, so the writers honoured the board flag and wrote no label, nothing wrote
  the board field, and the readers looked for a label that was never written.
  The value landed NOWHERE, and no gate reported it — that is the failure this
  release fixes.

  Newly filed issues are correct from now on: the binding governs, so the label
  your remap names is written and read. What this cannot fix retroactively is
  the issues already filed. Those carry no value, and the gates now ask for one.

  This migration does NOT know whether your corpus is affected — answering that
  means reading your issues, and a migration makes no network calls. To find out:

    pkit pm back-fill

  It reports what is missing and writes nothing. Every proposal cites where its
  value came from, and you decide before anything is applied. It only fills a
  confirmed gap — an issue that already carries a value is left alone — and the
  value it writes comes from the axis's \`default:\` in your map, or from
  \`--set <axis>=<value>\` if you would rather choose one for the run.

  If your corpus is clean, it proposes nothing and exits.
EOF
fi

exit 0
