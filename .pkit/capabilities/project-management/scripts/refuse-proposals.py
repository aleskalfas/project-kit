#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
#   "jsonschema>=4.20",
# ]
# ///
"""Project-management capability — refuse-proposals (DEC-056 point 6).

Records the person's refusal of a fixer's proposal, or of a question it held.
The refusal is remembered in the queue against the artefact's friction, so
`pkit pm fix-drift` does not dispatch the artefact again until its friction
changes. Run it only on what the person refused.

    pkit pm refuse-proposals <artefact>... [--dry-run]

A refusal goes with the queue, which is the clone's. Its lasting form is a
deferral, which the person may give instead, as their own answer, with
`pkit friction defer`. Each run's folder whose proposals were all accepted or
refused is removed.

Exit codes:
  0  refused, or would be under --dry-run
  1  refused nothing: an artefact has nothing waiting, the queue cannot be
     read or its lock is held, or the command runs inside an agent run
  2  usage error
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import bootstrap_gate, drift, drift_queue, proposals, session_guard
from _lib.membership import CAPABILITY_NAME


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=f"pkit pm {proposals.REFUSE}",
        description=(
            "Remember the person's refusal of a fixer's proposal or question, against the "
            "artefact's friction (DEC-056 point 6)."
        ),
    )
    parser.add_argument("artefacts", nargs="+", metavar="ARTEFACT", help="A refused proposal.")
    parser.add_argument("--dry-run", action="store_true", help="Write nothing.")
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=f"Default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/.",
    )
    session_guard.add_override_argument(parser)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    names = list(dict.fromkeys(args.artefacts))
    try:
        started = proposals.start(proposals.REFUSE, args.capability_root)
    except proposals.Refused as exc:
        proposals.error(f"{exc}. Nothing was written.")
        return 1
    if not bootstrap_gate.enforce("refuse-proposals", capability_root=started.capability_root):
        return 1
    if not args.dry_run and not session_guard.enforce(override=args.allow_foreign_repo):
        return 1
    try:
        with drift_queue.lock(started.queue):
            index = drift_queue.read_index(started.queue)
            entries = index.get("artefacts") or {}
            for name in names:
                state = (entries.get(name) or {}).get("state")
                if state not in (proposals.PROPOSED, proposals.HELD):
                    said = f"it is {state}" if state else "the queue holds nothing for it"
                    raise proposals.Refused(f"`{name}` has nothing waiting to refuse: {said}")
            at = drift.now()
            for name in names:
                index = proposals.refuse(index, name, at=at)
            if not args.dry_run:
                proposals.prune(started.queue, index)
                drift_queue.write_index(started.queue, index)
    except drift_queue.Held as exc:
        proposals.error(f"one command at a time works on the queue: {exc}. Nothing was written.")
        return 1
    except (proposals.Refused, drift_queue.Unreadable) as exc:
        proposals.error(f"{exc}. Nothing was written.")
        return 1
    done = "would refuse" if args.dry_run else "refused"
    for name in names:
        proposals.say(
            f"{done}: `{name}` — `pkit pm fix-drift` dispatches it again only once its "
            "friction changes"
        )
    line = drift_queue.count_line(drift_queue.waiting(index), started.queue)
    if line and not args.dry_run:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
