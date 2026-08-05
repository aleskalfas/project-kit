#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — comment-issue (verb-subject per DEC-020).

Post a freeform comment on a GitHub issue through the capability's validated
path (per [project-management:DEC-047-freeform-comment-verb]). The comment
mutates no lifecycle state, so it carries no validation-severity gate; it runs
the membership gate (DEC-021) and the foreign-repo session interlock (COR-039)
like every mutating verb, and the body must be non-empty.

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/comment-issue.py 42 --body "…"

Or via the dispatcher (per COR-021):
  pkit project-management comment-issue 42 --body "triage: reproduced on …"

Exit codes:
  0  commented (or dry-run reported)
  1  membership refusal / foreign-repo refusal
  2  usage error (missing/empty body, capability not found)
  3  gh failure
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib.comment import run_comment_verb  # noqa: E402

if __name__ == "__main__":
    sys.exit(run_comment_verb("issue"))
