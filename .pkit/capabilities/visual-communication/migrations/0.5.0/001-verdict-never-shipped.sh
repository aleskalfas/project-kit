#!/usr/bin/env bash
# visual-communication 0.5.0 — resource: verdict-never-shipped.
#
# The person makes the ship call on a piece, and no grade, bar, verdict, hold
# or calibration ends the designer's loop (visual-communication DEC-070,
# #3476). So the change that ships this version removes, from the
# capability's own tree:
#
#   scripts/verdict.py, scripts/_lib/verdicts.py,
#   scripts/_lib/calibration.py, scripts/_lib/bar.py    the verdict's command
#   schemas/calibration.schema.json, calibration.yaml   the calibration's data
#
# and, from the configuration's schema, `bar` and `bounds`.
#
# This migration does nothing, by design, and says nothing:
#
# - None of it shipped in a release. It came after 0.4.0, and this version is
#   the first release since, so no project holds a file of it, and no
#   project's configuration holds a bar or bounds the capability ever read.
# - The files are the capability's own. The upgrade's copy of the
#   capability's tree leaves none of them behind.
#
# It stands so that the removals have the migration the change check asks of
# them (COR-010).
#
# Idempotent: it changes nothing, so running it again changes nothing.

set -euo pipefail

# ROOT is the adopter's project root, provided by the runtime.
: "${ROOT:?ROOT must be set by the upgrade runtime}"
