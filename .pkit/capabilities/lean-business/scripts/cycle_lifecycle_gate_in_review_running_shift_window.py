#!/usr/bin/env python3
"""Predicate stub: deterministic gate — may the subject move 'in-review' -> 'running' on 'shift-window'? for lean-business:cycle-lifecycle.

Scaffolded by `pkit process new` (COR-044). Implementing it is the
process-author agent's territory — turn the owner's intent into a working
predicate over reality. The contract it must follow (COR-033 engine contract,
.pkit/process/README.md "The predicate runner"):

- READ-ONLY. `status` and `health` run predicates live; mutating here is a
  side-effect bug.
- argv: the subject slot first (the subject id), then `--json`;
  cwd is the repo root.
- print ONE JSON object to stdout: {"result": <bool>, "reason": "<why>"}
- FAIL-CLOSED: an error / timeout / non-zero exit / unparseable payload is
  INDETERMINATE, never a pass.

Until implemented this stub EXITS NON-ZERO (indeterminate, fail-closed) so an
unwritten predicate can never read as green.

pkit:predicate-stub-unimplemented — DELETE this line once the predicate is
implemented. `pkit process health --interpretation-only` reads it statically to
tell "seam declared but never written" from "seam written and merely failing",
so a seam no subject currently exercises still reports honestly.
"""
import json
import sys

subject = sys.argv[1] if len(sys.argv) > 1 else ""

# TODO(process-author): implement this predicate over the owner's reality,
# print the contract payload above, and exit 0.
print(json.dumps({
    "reason": "stub not implemented yet (deterministic gate — may the subject move 'in-review' -> 'running' on 'shift-window'? for lean-business:cycle-lifecycle)",
}))
sys.exit(1)
