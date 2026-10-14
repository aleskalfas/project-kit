#!/usr/bin/env bash
# software-analysis 0.2.0 — resource: retire-actors-collection-template.
#
# Each actor is a file of its own from 0.2.0 (software-analysis DEC-001
# points 2 and 3, #1346):
#
#   Before (0.1.0):
#     .pkit/capabilities/software-analysis/templates/actors.md   the collection
#     <analysis>/use-case-model/actors.md                        one entry per actor
#
#   After (0.2.0):
#     .pkit/capabilities/software-analysis/templates/actor.md    one actor
#     <analysis>/use-case-model/actors/ACT-<slug>.md             one file per actor
#
# This migration does nothing, by design, and says why:
#
# - The template is the capability's own file. The upgrade's copy of the
#   capability's tree brings `actor.md` and leaves no `actors.md` behind, so
#   nothing here needs removing.
# - The actors are the project's files, outside the capability's tree. Moving
#   one changes its content, and the move needs a revalidation a person
#   answers (COR-050 point 3), which no script can write. A migration would
#   also edit files the project owns.
# - software-analysis is installed only in project-kit's own clones (the
#   maintainer's decision for #1346). project-kit moves its own actors in the
#   change that ships this version, each with its revalidation.
#
# Idempotent: it changes nothing, so running it again changes nothing.

set -euo pipefail

: "${ROOT:?ROOT must be set by the upgrade runtime}"

echo "  note     actors.md template retired: actors are one file each, under use-case-model/actors/; project-owned actors move by hand, each with its revalidation (#1346)"
