#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
#   "jsonschema>=4.20",
# ]
# ///
"""Project-management capability — apply-proposals (DEC-056 point 6).

Applies the fixers' proposals the person accepted to the working tree of the
change's branch, so they reach the default branch through an ordinary pull
request. Run it only on what the person accepted, after they were shown every
word (`show-proposals`) and did what each answer lists for them to do first.

    pkit pm apply-proposals <artefact>... [--because <artefact> <words>]...
                            [--sentence <artefact> <sentence>]... [--dry-run]

What it does, in order:

  refuse  Nothing is written where an artefact has no proposal waiting, where
          the checkout is on the default branch or on no branch, where an
          artefact's file differs from the default branch's, or where an
          `unchanged` answer's justification still holds a placeholder for the
          person to fill and no `--because` gives their words.
  check   Each proposal again at the default branch's commit. One whose
          artefact is no longer stale, whose friction differs from what it was
          judged against, which was judged under another version of the run's
          contract, or whose files no longer read is set aside, and the next
          run of `pkit pm fix-drift` dispatches it again.
  apply   Upstream first: each diff, where the answer has one, then the writer,
          `pkit friction revalidate`, built from the answer's fields and run
          with `--yes`, since the person accepted it word for word. A diff
          that no longer applies is set aside. A writer that fails leaves the
          file as it was, and its proposal keeps waiting.
  record  Each applied proposal leaves the queue, and each run's folder whose
          proposals were all accepted or refused is removed.

`--because` gives the person's words for an `unchanged` answer's justification,
and `--sentence` theirs for an `updated` answer's sentence. The sentences are
printed for the pull request's description, under `## What changed in each
updated document`. `--dry-run` checks everything and writes nothing.

Exit codes:
  0  each proposal named was applied, or would be under --dry-run
  1  refused before anything was written
  2  usage error
  3  some were applied and some were not: each line says which, and why
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import bootstrap_gate, drift, drift_queue, fixer_contract, proposals, session_guard
from _lib.membership import CAPABILITY_NAME

say = proposals.say

EXIT_PARTIAL = 3


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=f"pkit pm {proposals.APPLY}",
        description=(
            "Apply the fixers' proposals the person accepted to the change's branch: each "
            "diff, then each writer, upstream first (DEC-056 point 6)."
        ),
    )
    parser.add_argument("artefacts", nargs="+", metavar="ARTEFACT", help="An accepted proposal.")
    parser.add_argument(
        "--because",
        nargs=2,
        action="append",
        default=[],
        metavar=("ARTEFACT", "WORDS"),
        help="The person's words for an `unchanged` answer's justification.",
    )
    parser.add_argument(
        "--sentence",
        nargs=2,
        action="append",
        default=[],
        metavar=("ARTEFACT", "SENTENCE"),
        help="The person's words for an `updated` answer's sentence.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Check, and write nothing.")
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
        started = proposals.start(proposals.APPLY, args.capability_root)
    except proposals.Refused as exc:
        proposals.error(f"{exc}. Nothing was written.")
        return 1
    if not bootstrap_gate.enforce("apply-proposals", capability_root=started.capability_root):
        return 1
    if not args.dry_run and not session_guard.enforce(override=args.allow_foreign_repo):
        return 1
    try:
        contract = fixer_contract.load()
        if args.dry_run:
            return _apply(args, names, started, contract)
        with drift_queue.lock(started.queue):
            return _apply(args, names, started, contract)
    except drift_queue.Held as exc:
        proposals.error(f"one command at a time works on the queue: {exc}. Nothing was written.")
        return 1
    except (
        proposals.Refused,
        fixer_contract.ContractError,
        drift_queue.Unreadable,
        drift.Stop,
    ) as exc:
        proposals.error(f"{exc}. Nothing was written.")
        return 1


def _words(
    pairs: list[list[str]], flag: str, outcome: str, fields: Mapping[str, Mapping]
) -> dict[str, str]:
    """The person's words given with `flag`, by artefact, each checked. `fields`
    holds each named artefact whose proposal reads."""
    words: dict[str, str] = {}
    for name, text in pairs:
        if name not in fields:
            raise proposals.Refused(
                f"{flag} names `{name}`, which is not among the artefacts with a proposal "
                "that reads"
            )
        if name in words:
            raise proposals.Refused(f"{flag} names `{name}` twice")
        if fields[name]["outcome"] != outcome:
            raise proposals.Refused(f"{flag} is for an `{outcome}` answer, and `{name}`'s is not")
        problem = proposals.line_problem(text)
        if problem:
            raise proposals.Refused(f"the words {flag} gives for `{name}` cannot stand: {problem}")
        words[name] = text
    return words


def _apply(
    args: argparse.Namespace,
    names: list[str],
    started: proposals.Started,
    contract: fixer_contract.Contract,
) -> int:
    queue, root = started.queue, started.repo_root
    index = drift_queue.read_index(queue)
    by_name = {item.name: item for item in proposals.waiting(index, queue, contract)}
    for name in names:
        item = by_name.get(name)
        if item is None or item.state != proposals.PROPOSED:
            entry = (index.get("artefacts") or {}).get(name)
            said = f"it is {entry.get('state')}" if entry else "the queue holds nothing for it"
            raise proposals.Refused(f"`{name}` has no proposal waiting: {said}")
    readable = {n: by_name[n] for n in names if by_name[n].answer is not None}
    fields = {n: item.answer.fields for n, item in readable.items() if item.answer}
    because = _words(args.because, "--because", "unchanged", fields)
    sentence = _words(args.sentence, "--sentence", "updated", fields)
    for name, given in fields.items():
        mark = proposals.placeholder(given.get("justification"))
        if given["outcome"] == "unchanged" and name not in because and mark:
            raise proposals.Refused(
                f"`{name}`'s justification holds a placeholder for the person to fill, {mark}: "
                "give their words with --because"
            )
    default, commit = proposals.pin(root)
    problem = proposals.branch_problem(root, default)
    if problem:
        raise proposals.Refused(problem)
    for path in dict.fromkeys(fixer_contract.own_file(name) for name in names):
        problem = proposals.file_problem(root, commit, path)
        if problem:
            raise proposals.Refused(problem)
    print(f"pin: the default branch, {default}, at {commit}")

    outcomes: list[proposals.Outcome] = []
    ready: list[str] = []
    with drift.copy_at(root, commit) as copy:
        upstreams = drift.upstreams_at(copy)
        for name in names:
            try:
                explained = drift.explain(copy, name)
            except drift.Stop as stop:
                why = f"it could not be checked again at the default branch: {stop}"
                outcomes.append(proposals.Outcome(name, False, why))
                continue
            why = proposals.recheck(by_name[name], explained, contract.contract_version)
            if why is None:
                ready.append(name)
            else:
                outcomes.append(proposals.Outcome(name, False, why, set_aside=True))
    for name in proposals.upstream_first(ready, upstreams):
        outcomes.append(
            proposals.apply_one(
                by_name[name],
                root=root,
                because=because.get(name),
                sentence=sentence.get(name),
                dry_run=args.dry_run,
            )
        )
    if not args.dry_run:
        for outcome in outcomes:
            if outcome.applied:
                index = proposals.consume(index, outcome.name)
            elif outcome.set_aside:
                index = proposals.set_aside(index, outcome.name, outcome.why)
        proposals.prune(queue, index)
        drift_queue.write_index(queue, index)
    _print(outcomes, dry_run=args.dry_run)
    line = drift_queue.count_line(drift_queue.waiting(index), queue)
    if line and not args.dry_run:
        print(line)
    return 0 if all(o.applied for o in outcomes) else EXIT_PARTIAL


def _print(outcomes: list[proposals.Outcome], *, dry_run: bool) -> None:
    done = "would apply" if dry_run else "applied"
    for outcome in outcomes:
        if outcome.applied:
            say(f"{done}: `{outcome.name}` — {proposals.shown(outcome.argv)}")
        elif outcome.set_aside:
            say(
                f"set aside: `{outcome.name}` — {outcome.why}; the next run of "
                "`pkit pm fix-drift` dispatches it again"
            )
        else:
            say(f"not applied: `{outcome.name}` — {outcome.why}; its proposal keeps waiting")
    sentences = [o for o in outcomes if o.applied and o.sentence]
    if sentences:
        say()
        say("for the pull request's description:")
        say()
        say("## What changed in each updated document")
        say()
        for outcome in sentences:
            say(f"- `{outcome.name}`: {outcome.sentence}")
    if dry_run:
        say()
        say("dry run: nothing was written.")


if __name__ == "__main__":
    sys.exit(main())
