#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
#   "jsonschema>=4.20",
# ]
# ///
"""Project-management capability — fix-drift (DEC-056 points 3 to 6).

Starts each granted fixer on what the default branch left out of date, where a
person started the command at a terminal and watches it, and gathers its
proposals for the person. A fixer only proposes: nothing it returns is applied
until the person accepts it.

    pkit pm fix-drift [--dry-run] [--force] [--cap N] [--parallel N]
                      [--timeout SECONDS] [--effort LEVEL]

A person started it when standard input and standard output are both
terminals, the test the fixers question uses (`fixer_cli.at_a_terminal`). An
agent's session, such as the project manager's after a merge, has no terminal,
so no fixer starts there: the command lists what went stale, with the fixer
that would take it, and the command a person runs at a terminal (DEC-056
point 3). No flag stands in for the terminal, since an agent passes a flag as
easily as a person does.

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
          every run. With nobody at a terminal the run ends here, having
          started and written nothing.
  run     Each fixer watched (DEC-056 point 5): through the backbone's run
          command in the runner's unconfined form, as `review-pr` runs its
          reviewers, in a working copy of the commit made for that fixer, under
          the person's settings and the project's, with one brief. At most
          --parallel at once, each within --timeout. A start that failed for a
          cause outside the fixer's work, and wrote nothing, is retried once;
          failing again, no further fixer starts. An interrupt at the terminal
          stops the run.
  gather  Each fixer's result lines and answers, read by the run's contract.
          A link or a special file in its workspace sets the fixer's files
          aside. The queue's index in the main working tree's agent workspace
          records each artefact's state.

One run at a time, held by a lock in the queue's folder, which a run with
nobody at a terminal does not take, since it writes nothing. The command refuses
to start inside an agent run, since a fixer starts no other agent.

Exit codes:
  0  the run completed, whatever each fixer returned; a run that started no
     fixer, since nobody was at a terminal; or a dry run
  1  the run could not start: inside an agent run, no main working tree, the
     lock held, the default branch or the fixers point unreadable, or the
     rules of a fixer's run that cannot be held
  2  usage error, or the capability is not found
"""

from __future__ import annotations

import argparse
import functools
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
            "watched by the person who started this at a terminal, and gather its proposals "
            "(DEC-056 points 3 to 6). With nobody at a terminal, list them and start no fixer."
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
    if not fixer_cli.at_a_terminal():
        # Nobody to watch: no fixer starts and the queue is only read, so no lock
        # is taken, and a person's run never stops this one (DEC-056 point 3).
        return _run(args, bounds, capability_root, repo_root, queue, contract, watched=False)
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
    *,
    watched: bool | None = None,
) -> int:
    """One run. `watched` is whether a person started it at a terminal: None
    tells it from this process's standard streams (`fixer_cli.at_a_terminal`)."""
    if watched is None:
        watched = fixer_cli.at_a_terminal()
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
    _print_plan(plan, watched=watched)
    if not watched and not plan.empty:
        _print_not_started()
    if args.dry_run:
        print("dry run: nothing was started, and nothing was written.")
        return 0
    if plan.empty:
        print("done: no fixer to start.")
        _print_waiting(index, queue)
        return 0
    if not watched:
        _print_waiting(index, queue)
        return 0
    print(
        f"watched: you started this at a terminal, so each fixer runs under your settings and "
        f"the project's, in a working copy at {reading.commit[:12]}. Ctrl-C stops the run."
    )
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
            watched=True,
        )
        for agent, candidates in plan.dispatch.items()
    }
    fixers_run = drift.run_all(
        plan,
        briefs,
        commit=reading.commit,
        runs_folder=queue / drift_queue.RUNS / run,
        bounds=bounds,
        start=functools.partial(drift.run_watched, repo_root=repo_root),
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


def _print_plan(plan: drift.Plan, *, watched: bool) -> None:
    """What the run dispatches, or, with nobody at a terminal, what went stale
    and the fixer that would take it; then every artefact it lists."""
    for agent, candidates in plan.dispatch.items():
        names = ", ".join(f"`{c.name}`" for c in candidates)
        if watched:
            _say(f"dispatch: {agent} on {len(candidates)} artefact(s): {names}")
        else:
            _say(f"stale: {agent} would take {len(candidates)} artefact(s): {names}")
    for listed in plan.listed:
        label = "standing" if listed.standing else "listed"
        _say(f"{label}: `{listed.name}` — {listed.why}")


def _print_not_started() -> None:
    """Why no fixer starts with nobody at a terminal, and the command a person
    runs to start them (DEC-056 point 3)."""
    print(
        "no fixer started: nobody is at a terminal to watch the fixers (DEC-056 point 3).\n"
        f"  To start them, run at a terminal: {fixers.COMMAND} {drift.VERB}"
    )


def _print_runs(fixers_run: list[drift.FixerRun], gathered: list[drift.Gathered]) -> None:
    for fixer, each in zip(fixers_run, gathered, strict=True):
        run = fixer.run
        if run is None:
            _say(f"ran: {fixer.agent} did not start — {fixer.skipped}")
        else:
            said = f"finished, exit {run.exit_code}" if run.ending == "finished" else run.ending
            retried = ", started twice" if fixer.retried else ""
            checked = f"; check {run.check}" if run.check != drift.agent_runs.NOT_RUN else ""
            _say(f"ran: {fixer.agent} — {said}{retried}{checked}")
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
