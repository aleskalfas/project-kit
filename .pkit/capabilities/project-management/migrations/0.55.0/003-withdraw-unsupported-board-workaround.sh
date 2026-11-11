#!/usr/bin/env bash
# project-management 0.55.0 — resource: report the label-bound-under-a-board
# shape after DEC-051, whose corpus may need repair.
#
# Until DEC-051 nothing decided which declaration won where a configured board
# (`has_projects_v2_board: true`) and a `label:` binding in
# `project/substrate-map.yaml` both spoke to one axis. The writers honoured the
# board flag and wrote no label, nothing wrote the board field, and the readers
# looked for a label that was never written: issues filed then may carry a value
# on neither substrate. This migration tells the adopters holding that shape,
# who will never re-read the remediation that would have told them.
#
# DISCRETIONARY, and honestly so. `pkit migrations check-diff` reports NO
# migration is required for the DEC-051 change-set: nothing is renamed or removed
# in a kit-owned tree, no schema_version moves, no CLI signature breaks. The
# justification is not COR-010's trigger but a narrower one: the corpus may be
# damaged, and the adopter should hear where to look. Do not read this script as
# evidence that the change-set owed a migration.
#
# REPORT ONLY. This script prints what it found and edits nothing. It reports
# one condition: the map binds `priority`, `workstream` or `state` with a
# `label:` arm under a configured board. It names `pkit pm back-fill` as the way
# to find out, and says plainly that this script has not looked — that means
# reading issues, and a migration makes no network calls.
#
# The withdrawn `unsupported: true`-means-board guidance, which this migration
# also reported as written for DEC-051, is not reported here: DEC-062 ends the
# board flag's carriage, and the migration after this one in the same release
# (`005-board-flag-carries-no-axis.sh`) writes `board: true` in place of
# `unsupported: true` for priority and workstream under a set flag, as
# project-management DEC-062 point 6 decides.
#
# Idempotent: it writes nothing, so a re-run reports the same. A project with no
# configured board matches nothing at all. Every path exits 0 — this is a report,
# not a gate, and it must not break an upgrade; the scan is guarded so that even
# a missing `python3` reports rather than aborting the run.
#
# Run via the upgrade runtime with ROOT=<adopter root>.

set -euo pipefail

# ROOT is the adopter's project root, provided by the runtime.
: "${ROOT:?ROOT must be set by the upgrade runtime}"

CAP_DIR="$ROOT/.pkit/capabilities/project-management"
CONFIG_FILE="$CAP_DIR/project/config.yaml"
SUBSTRATE_MAP="$CAP_DIR/project/substrate-map.yaml"

if [ ! -d "$CAP_DIR" ]; then
    echo "  [skip] project-management capability not installed at $CAP_DIR"
    exit 0
fi

# No map means greenfield: every axis reads the kit's own labels, and no axis is
# bound to the adopter's own labels.
if [ ! -f "$SUBSTRATE_MAP" ]; then
    echo "  [ok] no project/substrate-map.yaml (greenfield); nothing to report"
    exit 0
fi

# The scan is stdlib Python, no ruamel: a migration must not acquire a runtime
# dependency at upgrade time (the same call the 0.5.0 config-workstreams
# migration made). Block-style YAML only — that is what hand-authored maps and
# every `adopt-existing` draft use. A flow-style map is simply not detected: this
# report UNDER-reports rather than mis-reports, which is the right direction for
# a heuristic that ends in advice.
detection=$(python3 - "$CONFIG_FILE" "$SUBSTRATE_MAP" <<'PYEOF'
import re
import sys
from pathlib import Path

config_path, map_path = (Path(a) for a in sys.argv[1:3])

# The axes a board could carry while the map bound them to labels.
BOARD_CLAIMED = ("priority", "workstream", "state")


def read(path):
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


config_text = read(config_path)
if config_text is None:
    print("NONE no project/config.yaml")
    raise SystemExit(0)
if not re.search(r"^has_projects_v2_board:\s*true\s*(#.*)?$", config_text, re.M):
    print("NONE no configured Projects-v2 board")
    raise SystemExit(0)

map_text = read(map_path)
if map_text is None:
    print("NONE project/substrate-map.yaml unreadable")
    raise SystemExit(0)


def indent_of(line):
    return len(line) - len(line.lstrip(" "))


# Indentation walk over the `axes:` block: find the top-level `axes:` key, then
# each axis key one level in, then the arm inside that axis's block.
axes_indent = None
axis_indent = None
current_axis = None
label_bound = []
for line in map_text.splitlines():
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
        current_axis in BOARD_CLAIMED
        and re.match(r"^label:\s*(#.*)?$", stripped)
        and current_axis not in label_bound
    ):
        label_bound.append(current_axis)

if not label_bound:
    print("NONE no board-claimed axis is bound to labels")
    raise SystemExit(0)

print("MATCH|" + " ".join(label_bound))
PYEOF
) || detection="NONE the scan could not run (python3 unavailable or the scan failed)"
# `|| …` rather than letting `set -e` propagate: this script's contract is that
# every path exits 0, because a REPORT must never break an upgrade. Without the
# guard a missing python3 aborts the whole run for the sake of advice.

if [ "${detection%%|*}" != "MATCH" ]; then
    echo "  [ok] no action needed — ${detection#NONE }"
    exit 0
fi

label_axes=${detection#MATCH|}

cat <<EOF
  [warn] issues filed before this upgrade may carry no value for an axis your
         map binds to labels, on EITHER substrate:

    File:  $SUBSTRATE_MAP
    Axes:  $label_axes

  project/config.yaml configures a Projects-v2 board while your map binds those
  axes to your own labels. Until DEC-051 nothing decided which declaration won,
  so the writers honoured the board flag and wrote no label, nothing wrote the
  board field, and the readers looked for a label that was never written. The
  value landed NOWHERE, and no gate reported it.

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

exit 0
