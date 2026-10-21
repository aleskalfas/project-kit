#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
#   "jsonschema>=4.20",
# ]
# ///
"""Project-management capability — answer-question (DEC-056 points 3 and 6).

Records the person's answer to a question a fixer held, and who gave it. The
next run of `pkit pm fix-drift` dispatches the artefact again, while its
friction is the one the question was asked on, and its brief quotes the
question, the answer and who gave it, as data. Run it only with the person's
own answer.

    pkit pm answer-question <artefact> <answer> [--by NAME] [--dry-run]

`--by` names who answered; it defaults to the checkout's `git config
user.name`. The answer is held to an answer's own words: one line, with no
control, separator or hiding character.

Exit codes:
  0  recorded, or would be under --dry-run
  1  recorded nothing: no question waits on the artefact, the answer cannot
     stand, nobody is named, the queue cannot be read or its lock is held,
     or the command runs inside an agent run
  2  usage error
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import bootstrap_gate, drift_queue, proposals, session_guard
from _lib.membership import CAPABILITY_NAME


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=f"pkit pm {proposals.ANSWER}",
        description=(
            "Record the person's answer to a question a fixer held, for the artefact's next "
            "brief (DEC-056 points 3 and 6)."
        ),
    )
    parser.add_argument("artefact", help="The artefact the question was held on.")
    parser.add_argument("answer", help="The person's answer, in their words.")
    parser.add_argument("--by", default=None, help="Who answered. Default: git's user.name.")
    parser.add_argument("--dry-run", action="store_true", help="Write nothing.")
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=f"Default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/.",
    )
    session_guard.add_override_argument(parser)
    return parser


def _git_user(root: Path) -> str:
    try:
        proc = subprocess.run(
            ["git", "config", "user.name"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return ""
    return (proc.stdout or "").strip() if proc.returncode == 0 else ""


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    name = args.artefact
    try:
        started = proposals.start(proposals.ANSWER, args.capability_root)
    except proposals.Refused as exc:
        proposals.error(f"{exc}. Nothing was written.")
        return 1
    if not bootstrap_gate.enforce("answer-question", capability_root=started.capability_root):
        return 1
    if not args.dry_run and not session_guard.enforce(override=args.allow_foreign_repo):
        return 1
    try:
        problem = proposals.line_problem(args.answer)
        if problem:
            raise proposals.Refused(f"the answer cannot stand: {problem}")
        by = args.by if args.by is not None else _git_user(started.repo_root)
        if proposals.line_problem(by):
            raise proposals.Refused("nobody is named as the one who answered: give --by")
        with drift_queue.lock(started.queue):
            index = drift_queue.read_index(started.queue)
            state = ((index.get("artefacts") or {}).get(name) or {}).get("state")
            if state != proposals.HELD:
                said = f"it is {state}" if state else "the queue holds nothing for it"
                raise proposals.Refused(f"no question waits on `{name}`: {said}")
            index = proposals.answer(index, name, words=args.answer, by=by)
            if not args.dry_run:
                drift_queue.write_index(started.queue, index)
    except drift_queue.Held as exc:
        proposals.error(f"one command at a time works on the queue: {exc}. Nothing was written.")
        return 1
    except (proposals.Refused, drift_queue.Unreadable) as exc:
        proposals.error(f"{exc}. Nothing was written.")
        return 1
    done = "would record" if args.dry_run else "recorded"
    proposals.say(
        f"{done}: your answer on `{name}`, by {by}; the next run of `pkit pm fix-drift` gives "
        "its fixer the question and your answer, as data"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
