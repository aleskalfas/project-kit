#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
#   "jsonschema>=4.20",
# ]
# ///
"""Project-management capability — show-proposals (DEC-056 point 6).

Brings the fixers' proposals to the person in one batch: each with its
evidence, its diff and the writer's command word for word, and each question a
fixer held. The person accepts, rewords or refuses each.

    pkit pm show-proposals

Each artefact that waits is checked again at the default branch's commit first.
One whose artefact is no longer stale, whose friction differs from what it was
judged against, which was judged under another version of the run's contract,
or whose files no longer read is set aside and never shown: the next run of
`pkit pm fix-drift` dispatches it again. One whose friction cannot be read now
is not shown, and keeps waiting. A question the person answered is listed, and
waits for the next run.

What the person decides goes through the other commands of the batch:
`apply-proposals` on the change's branch for what they accept, with their
words for a reworded answer; `refuse-proposals` for what they refuse; and
`answer-question` for a held question.

Exit codes:
  0  shown, or nothing waits
  1  the batch could not be shown: inside an agent run, no queue, the lock
     held, the queue or the default branch unreadable
  2  usage error
"""

from __future__ import annotations

import argparse
import shlex
import sys
from collections.abc import Sequence
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import bootstrap_gate, drift, drift_queue, fixer_contract, proposals, session_guard
from _lib.membership import CAPABILITY_NAME

say = proposals.say


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=f"pkit pm {proposals.SHOW}",
        description=(
            "Bring the fixers' proposals and held questions in one batch, each checked again "
            "at the default branch (DEC-056 point 6)."
        ),
    )
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
    try:
        started = proposals.start(proposals.SHOW, args.capability_root)
    except proposals.Refused as exc:
        proposals.error(f"{exc}. Nothing was shown.")
        return 1
    if not bootstrap_gate.enforce("show-proposals", capability_root=started.capability_root):
        return 1
    try:
        contract = fixer_contract.load()
        index = drift_queue.read_index(started.queue)
    except (fixer_contract.ContractError, drift_queue.Unreadable) as exc:
        proposals.error(f"{exc}. Nothing was shown.")
        return 1
    if not proposals.waiting(index, started.queue, contract):
        print("nothing waits for you: the queue holds no fixer's proposal or question.")
        return 0
    # Showing sets aside what no longer holds, a write to the queue.
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1
    try:
        with drift_queue.lock(started.queue):
            return _show(started, contract)
    except drift_queue.Held as exc:
        proposals.error(f"one command at a time works on the queue: {exc}. Nothing was shown.")
        return 1


def _show(started: proposals.Started, contract: fixer_contract.Contract) -> int:
    queue = started.queue
    try:
        index = drift_queue.read_index(queue)
        name, commit = proposals.pin(started.repo_root)
    except (drift_queue.Unreadable, proposals.Refused) as exc:
        proposals.error(f"{exc}. Nothing was shown.")
        return 1
    print(f"pin: the default branch, {name}, at {commit}")
    items = proposals.waiting(index, queue, contract)
    shown: list[proposals.Waiting] = []
    answered: list[proposals.Waiting] = []
    aside: list[tuple[str, str]] = []
    unchecked: list[tuple[str, str]] = []
    try:
        with drift.copy_at(started.repo_root, commit) as copy:
            for item in items:
                if item.answered:
                    answered.append(item)
                    continue
                try:
                    explained = drift.explain(copy, item.name)
                except drift.Stop as stop:
                    unchecked.append((item.name, str(stop)))
                    continue
                why = proposals.recheck(item, explained, contract.contract_version)
                if why is None:
                    shown.append(item)
                else:
                    index = proposals.set_aside(index, item.name, why)
                    aside.append((item.name, why))
    except drift.Stop as stop:
        proposals.error(f"{stop}. Nothing was shown.")
        return 1
    if aside:
        proposals.prune(queue, index)
        drift_queue.write_index(queue, index)
    _print(shown, answered, aside, unchecked)
    line = drift_queue.count_line(drift_queue.waiting(index), queue)
    if line:
        print(line)
    return 0


def _print(
    shown: list[proposals.Waiting],
    answered: list[proposals.Waiting],
    aside: list[tuple[str, str]],
    unchecked: list[tuple[str, str]],
) -> None:
    offered = [item for item in shown if item.state == proposals.PROPOSED]
    held = [item for item in shown if item.state == proposals.HELD]
    for number, item in enumerate(offered, start=1):
        say()
        _proposal(item, number, len(offered))
    for number, item in enumerate(held, start=1):
        say()
        _question(item, number, len(held))
    if answered or aside or unchecked:
        say()
    for item in answered:
        say(
            f"answered: `{item.name}` — {item.entry.get('answer')}, by "
            f"{item.entry.get('answered_by')}; the next run of `pkit pm fix-drift` gives its "
            "fixer your answer"
        )
    for name, why in aside:
        say(f"set aside: `{name}` — {why}; the next run of `pkit pm fix-drift` dispatches it again")
    for name, why in unchecked:
        say(f"not shown: `{name}` — it could not be checked again at the default branch: {why}")
    if offered or held:
        say()
        say("decide each, and run only what the person decides:")
    if offered:
        say(
            f"  accept: `pkit pm {proposals.APPLY} <artefact>...` on the change's branch, with "
            "`--because <artefact> <words>` for a reworded justification"
        )
        say(f"  refuse: `pkit pm {proposals.REFUSE} <artefact>...`")
    if held:
        say(f"  answer: `pkit pm {proposals.ANSWER} <artefact> <answer>`")


def _proposal(item: proposals.Waiting, number: int, total: int) -> None:
    entry = item.entry
    assert item.answer is not None
    fields = item.answer.fields
    say(
        f"proposal {number} of {total}: `{item.name}` — {entry.get('type')}, from "
        f"{entry.get('fixer')}, judged at {str(entry.get('commit') or '')[:12]}"
    )
    say(f"  outcome: {fields['outcome']}")
    if fields["outcome"] == "unchanged":
        say(f"  because: {fields['justification']}")
        mark = proposals.placeholder(fields["justification"])
        if mark:
            say(
                f"  it holds a placeholder for you to fill, {mark}: accept it only with your "
                "words, `--because`"
            )
    else:
        say(f"  what changed: {fields['sentence']}")
    keep = fields.get("keep") or []
    say(f"  deferrals kept: {', '.join(keep) if keep else 'none; every deferral is removed'}")
    first = fields.get("first") or []
    if first:
        say("  before it is recorded, you:")
        for step in first:
            say(f"    - {step}")
    say(f"  the writer, word for word: {proposals.shown(proposals.writer_argv(item.name, fields))}")
    evidence = item.evidence
    say(f"  evidence ({item.answer.path.parent / proposals.EVIDENCE}):")
    proposals.say_block(evidence if evidence is not None else "(the fixer wrote none)")
    if item.answer.diff is not None:
        say(f"  diff ({item.answer.diff}):")
        proposals.say_block(item.answer.diff.read_text(encoding="utf-8"))
    else:
        say("  diff: none; the artefact's text stays as it is")


def _question(item: proposals.Waiting, number: int, total: int) -> None:
    entry = item.entry
    say(
        f"question {number} of {total}: `{item.name}` — {entry.get('type')}, from "
        f"{entry.get('fixer')}, judged at {str(entry.get('commit') or '')[:12]}"
    )
    say(f"  asks: {entry.get('words')}")
    say(f"  answer it: pkit pm {proposals.ANSWER} {shlex.quote(item.name)} '<your answer>'")
    evidence = item.evidence
    if evidence is not None:
        say("  evidence:")
        proposals.say_block(evidence)


if __name__ == "__main__":
    sys.exit(main())
