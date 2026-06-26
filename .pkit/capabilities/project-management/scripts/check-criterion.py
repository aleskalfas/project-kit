#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — check-criterion (verb-subject per DEC-020).

Tick one or more acceptance-criterion checkboxes on a GitHub issue, addressed
by 1-based index with an optional expected-text guard, per
[project-management:DEC-038-criterion-addressing]. Replaces the whole-body
fetch-edit-resend that edit-issue forces for a single checkbox flip.

Signature (batch-capable — tick N criteria in one call):
  check-criterion <issue> <index> [expected-text] [<index> [expected-text]] ...

  - <index>          1-based position in the acceptance-criteria list, matching
                     `show-issue --field criteria`'s numbering.
  - [expected-text]  optional guard: the verb refuses to tick unless the line at
                     that index still equals this text (DEC-038 D1). Equality on
                     the checkbox-marker-stripped, trimmed text. An argument that
                     parses as an integer starts the next target; a non-integer
                     argument is the preceding index's guard.

Failure + recovery (DEC-038 D4): the WHOLE batch is validated up front and a
hard inconsistency (out-of-range / text-mismatch / ambiguous guard / non-checkbox
target) refuses the batch before any mutation. Application is idempotent — ticking
an already-ticked box is a no-op success, so a half-applied batch recovers by
re-running.

Membership gate per DEC-021 runs at startup. Reuses show-issue's criterion
extraction (via _lib.criteria) for index parity and edit-issue's
`gh issue edit --body-file` write-back.

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/check-criterion.py 239 1 3
Or via the dispatcher (per COR-021):
  pkit project-management check-criterion 239 1 "docs updated"

Exit codes:
  0  applied (or no-op idempotent success; or dry-run reported)
  1  membership refusal / batch hard-reject (nothing mutated)
  2  usage error (issue not found; bad target syntax)
  3  gh write failure
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib.criterion_cli import run_criterion_verb  # noqa: E402


def main() -> int:
    return run_criterion_verb(verb="check-criterion", target_checked=True)


if __name__ == "__main__":
    sys.exit(main())
