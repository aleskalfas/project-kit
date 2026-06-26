#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — uncheck-criterion (verb-subject per DEC-020).

Untick one or more acceptance-criterion checkboxes on a GitHub issue — the
symmetric counterpart to check-criterion, addressed by 1-based index with an
optional expected-text guard, per [project-management:DEC-038-criterion-
addressing].

Signature (batch-capable):
  uncheck-criterion <issue> <index> [expected-text] [<index> [expected-text]] ...

Addressing, the optional text guard, the validate-up-front whole-batch
hard-reject, and idempotent recovery are identical to check-criterion — the only
difference is the target state (unticked). Unticking an already-unticked box is a
no-op success. See check-criterion's header and DEC-038 D4 for the full model.

Membership gate per DEC-021 runs at startup. Reuses show-issue's criterion
extraction (via _lib.criteria) and edit-issue's `gh issue edit --body-file`
write-back.

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/uncheck-criterion.py 239 1 3
Or via the dispatcher (per COR-021):
  pkit project-management uncheck-criterion 239 2

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
    return run_criterion_verb(verb="uncheck-criterion", target_checked=False)


if __name__ == "__main__":
    sys.exit(main())
