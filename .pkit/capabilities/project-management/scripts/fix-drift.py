#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
#   "jsonschema>=4.20",
# ]
# ///
"""Project-management capability — fix-drift (DEC-056 points 3 to 6).

Starts each granted fixer on what the default branch left out of date, and
gathers its proposals for the person. A fixer only proposes: nothing it returns
is applied until the person accepts it.

    pkit pm fix-drift [--dry-run] [--force] [--cap N] [--parallel N]
                      [--timeout SECONDS] [--effort LEVEL]

What a run does, in order (`_lib/drift.py` holds each step):

  pin     The default branch's commit, as the backbone resolves it. Everything
          that decides a dispatch is read at it, in a detached copy of it:
          the whole-repository check, each artefact's type, the fixers point,
          the grant list and the forms the run's rules allow. A grant counts
          once its change merged.
  ask     The fixers question, at a terminal, for each fixer type nobody was
          asked about (DEC-056 point 2). Each answer is recorded in this
          checkout's grant list, and counts once its change merges. With
          nobody at a terminal, each question is printed with the command that
          grants its fixer. Not under --dry-run.
  plan    Stale artefacts whose type's fixer is granted, upstream first, at
          most --cap for each fixer. Every other artefact the check reports is
          listed with its reason, and each `none` that stands is listed at
          every run.
  run     Each fixer through the backbone's run command, confined to a clone at
          the commit under `permissions/runs.yaml`'s rules (ADR-066), with one
          brief. At most --parallel at once, each within --timeout. A start
          that failed for a cause outside the fixer's work, and wrote nothing,
          is retried once; failing again, no further fixer starts.
  gather  Each fixer's result lines and answers, read by the run's contract.
          A breach sets the fixer's files aside. The queue's index in the main
          working tree's agent workspace records each artefact's state.

One run at a time, held by a lock in the queue's folder. The command refuses
to start inside an agent run, since a fixer starts no other agent.

Exit codes:
  0  the run completed, whatever each fixer returned; or a dry run
  1  the run could not start: inside an agent run, no main working tree, the
     lock held, the default branch or the fixers point unreadable, or nothing
     can be confined
  2  usage error, or the capability is not found
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import (
    bootstrap_gate,
    drift,
    drift_queue,
    fixer_cli,
    fixer_contract,
    fixers,
    session_guard,
)
from _lib.gh import gh_run, load_adopter_config
from _lib.membership import CAPABILITY_NAME, resolve_capability_root


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=f"{fixers.COMMAND} {drift.VERB}",
        description=(
            "Start each granted fixer on the artefacts the default branch left out of date, "
            "confined, and gather its proposals (DEC-056 points 3 to 6)."
        ),
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Say what would start, and start nothing."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Dispatch an artefact whose proposal, question or `none` still stands.",
    )
    parser.add_argument(
        "--cap",
        default=None,
        help=f"Artefacts for each fixer (${drift.CAP_ENV}, {drift.DEFAULT_CAP}).",
    )
    parser.add_argument(
        "--parallel", default=None, help=f"Fixers at once (${drift.PARALLEL_ENV}, all)."
    )
    parser.add_argument(
        "--timeout",
        default=None,
        help=(
            f"Each fixer's wall-clock limit in seconds (${drift.TIMEOUT_ENV}, "
            f"{drift.DEFAULT_TIMEOUT})."
        ),
    )
    parser.add_argument(
        "--effort",
        default=None,
        help=f"The effort each fixer reasons at (${drift.EFFORT_ENV}; else its own).",
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
    parser = _parser()
    args = parser.parse_args(argv)
    if drift.RUN_MARKER in os.environ:
        print(
            f"error: refusing to run `{fixers.COMMAND} {drift.VERB}` inside an agent run "
            f"({drift.RUN_MARKER} is set): a fixer starts no other agent (DEC-056 point 5). "
            "Nothing was started.",
            file=sys.stderr,
        )
        return 1
    try:
        bounds = drift.resolve_bounds(
            cap=args.cap,
            parallel=args.parallel,
            timeout=args.timeout,
            effort=args.effort,
            env=os.environ,
        )
    except ValueError as exc:
        parser.error(str(exc))
    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return 2
    if not bootstrap_gate.enforce("fix-drift", capability_root=capability_root):
        return 1
    repo_root = capability_root.parents[2]
    queue = drift_queue.folder(repo_root)
    if isinstance(queue, str):
        print(
            f"error: {queue}, so a run would gather nothing. Nothing was started.", file=sys.stderr
        )
        return 1
    try:
        contract = fixer_contract.load()
    except fixer_contract.ContractError as exc:
        print(f"error: the run's contract cannot be read: {exc}", file=sys.stderr)
        return 1
    if args.dry_run:
        return _run(args, bounds, capability_root, repo_root, queue, contract)
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1
    try:
        with drift_queue.lock(queue):
            return _run(args, bounds, capability_root, repo_root, queue, contract)
    except drift_queue.Held as exc:
        print(f"error: one run at a time: {exc}. Nothing was started.", file=sys.stderr)
        return 1


def _run(
    args: argparse.Namespace,
    bounds: drift.Bounds,
    capability_root: Path,
    repo_root: Path,
    queue: Path,
    contract: Any,
) -> int:
    try:
        index = drift_queue.read_index(queue)
    except drift_queue.Unreadable as exc:
        print(f"error: the queue cannot be read: {exc}. Nothing was started.", file=sys.stderr)
        return 1
    config = load_adopter_config(capability_root)

    def gh(argv: list[str], **kwargs: Any) -> Any:
        return gh_run(argv, config, check=False, **kwargs)

    try:
        commit = drift.pin_commit(repo_root)
        print(f"pin: the default branch at {commit}")
        with drift.copy_at(repo_root, commit) as copy:
            reading = drift.read_at(copy, commit, checkout=repo_root)
            _ask(args, reading, copy, capability_root)
            plan = drift.plan(
                reading,
                index,
                bounds=bounds,
                force=args.force,
                contract_version=contract.contract_version,
                changed_by_open_prs=drift.gh_open_pr_files(repo_root, gh),
                explained=lambda name: drift.explain(copy, name),
                classes=contract.reasons,
            )
    except drift.Stop as stop:
        print(f"error: {stop}. Nothing was started.", file=sys.stderr)
        return 1
    _print_plan(plan)
    if args.dry_run:
        print("dry run: nothing was started, and nothing was written.")
        return 0
    if plan.empty:
        print("done: no fixer to start.")
        _print_waiting(index, queue)
        return 0
    run = drift.run_id()
    started = drift.now()
    pulls_of = drift.gh_pulls_of(repo_root, gh)
    briefs = {
        agent: drift.brief(
            agent,
            candidates,
            commit=reading.commit,
            forms=reading.forms,
            contract={"forms": dict(contract.forms), "reasons": dict(contract.reasons)},
            quotes=[*drift.answered_quotes(candidates), *drift.pr_quotes(candidates, pulls_of)],
        )
        for agent, candidates in plan.dispatch.items()
    }
    fixers_run = drift.run_all(
        plan,
        briefs,
        commit=reading.commit,
        runs_folder=queue / drift_queue.RUNS / run,
        bounds=bounds,
    )
    gathered = [
        drift.gather(
            fixer,
            queue=queue,
            run=run,
            contract=contract,
            read_results=fixer_contract.read_results,
            settle=fixer_contract.settle,
        )
        for fixer in fixers_run
    ]
    index = drift.record(
        index,
        gathered,
        fixers_run,
        run=run,
        reading=reading,
        contract_version=contract.contract_version,
        bounds=bounds,
        started=started,
    )
    drift_queue.write_index(queue, index)
    _print_runs(fixers_run, gathered)
    _print_waiting(index, queue)
    return 0


def _ask(
    args: argparse.Namespace, reading: drift.Reading, copy: Path, capability_root: Path
) -> None:
    """The fixers question for each fixer type nobody here was asked about
    (DEC-056 point 2), from the declaration read at the pinned commit. Each
    answer goes into this checkout's grant list. A dry run asks nothing."""
    declared = reading.artefacts.get("types") or {}
    registered = {
        str(name): str(entry.get("component") or "")
        for name, entry in declared.items()
        if isinstance(entry, dict)
    }
    fixer_cli.ask_pending(
        point=reading.point,
        repo_root=copy,
        config_path=capability_root / fixers.CONFIG_RELATIVE,
        interactive=False if args.dry_run else None,
        types=lambda: registered,
    )


def _say(line: str) -> None:
    """Print one line whose words may be a fixer's, its control and formatting
    characters shown as escapes, so no such word rewrites the terminal."""
    print(drift.plain(line))


def _print_plan(plan: drift.Plan) -> None:
    for agent, candidates in plan.dispatch.items():
        names = ", ".join(f"`{c.name}`" for c in candidates)
        _say(f"dispatch: {agent} on {len(candidates)} artefact(s): {names}")
    for listed in plan.listed:
        label = "standing" if listed.standing else "listed"
        _say(f"{label}: `{listed.name}` — {listed.why}")


def _print_runs(fixers_run: list[drift.FixerRun], gathered: list[drift.Gathered]) -> None:
    for fixer, each in zip(fixers_run, gathered, strict=True):
        run = fixer.run
        if run is None:
            _say(f"ran: {fixer.agent} did not start — {fixer.skipped}")
        else:
            said = f"finished, exit {run.exit_code}" if run.ending == "finished" else run.ending
            retried = ", started twice" if fixer.retried else ""
            _say(f"ran: {fixer.agent} — {said}{retried}; check {run.check}")
            if run.reason and run.ending != "finished":
                _say(f"  why: {run.reason}")
            for command in run.excluded:
                _say(f"  outside the sandbox: `{command}` (ADR-066 point 6)")
            if run.refused_calls:
                _say(f"  the harness refused {len(run.refused_calls)} call(s):")
                for call in run.refused_calls:
                    _say(f"    {call}")
        if each.set_aside:
            _say(f"  set aside: {each.set_aside}")
        for outcome in each.outcomes:
            detail = f": {outcome.reason}" if outcome.reason else ""
            words = f" — {outcome.words}" if outcome.words else ""
            where = f" ({outcome.proposal})" if outcome.proposal else ""
            _say(f"result: {fixer.agent} {outcome.state} `{outcome.name}`{detail}{words}{where}")
        for line, why in each.ignored:
            _say(f"  read for nothing: {line!r} — {why}")


def _print_waiting(index: dict[str, Any], queue: Path) -> None:
    line = drift_queue.count_line(drift_queue.waiting(index), queue)
    if line:
        print(line)


if __name__ == "__main__":
    sys.exit(main())
