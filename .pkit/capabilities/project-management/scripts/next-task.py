#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — next-task (DEC-059 point 7).

A worker takes its next task from one pool that every seat shares:

    next-task [--dry-run] [--yes] [--limit N]

It picks the next ready Task, the highest in priority first (DEC-012), within
the scope of the seat this clone holds, and starts it, claimed, through
`start-work`. A ready Task is an open Task in Backlog with no owner whose
`## Dependencies` section names no open issue (DEC-005), or, in a project with a
topology, a Task In Progress whose claim no longer counts (DEC-059 point 9).
A Task in Backlog that this clone's instance owns, as a lead owns what it files,
is its own work, outside the pool: with its dependencies closed and within the
scope, it comes before every pool Task. `_lib/task_pool` reckons readiness, and
its docstring says which references the section is read for.

Steps:
  - The gates `start-work` runs: the bootstrap gate, membership (DEC-021) and
    the foreign-repo guard, whose confirmation is handed on to `start-work`.
  - Who takes: in a project with a topology, the clone's seat, confirmed on
    its state issue, whose scope the topology gives and which narrows the pool.
    A note names the commit of the default branch the topology was read at, and
    the `start-work` this command runs does not name it again (DEC-059 point 1).
    A clone that holds no seat, holds a planner's seat or whose seat cannot be
    confirmed takes nothing. Outside a topology a clone takes with no scope.
  - One listing of the open issues of work (`_lib/issue_list`), which leaves
    state issues out. The ready Tasks are ranked from it. A ready Task the
    seat's scope leaves out is skipped: a line names those Tasks for each
    reason, such as a Task in no milestone the scope names (DEC-059 point 2).
    A milestone is shown by its number, with the title the listing gives it
    beside the number where the listing returned an issue in it.
  - Where the clone takes part in instance ownership, the owner of each Task in
    Backlog assigned to its account is read first and folded
    (`_lib/instance_claims.read_owner`). The Tasks this clone owns come first,
    then the pool. The owner of each other Task is read in turn, and a Task
    another instance holds is skipped, as is one that cannot be read.
  - `start-work <N> --yes` starts the first free Task. Where it fails and the
    Task is now another instance's, the first claim held: this clone backs off
    and takes the next ready Task. Any other failure stops the run.

Exit codes:
  0  a Task was started, or a dry run said which it would start
  1  membership refusal / foreign-repo refusal
  2  usage error / a clone that holds no seat, or a planner's seat / this
     clone's seat could not be confirmed / the listing reached its limit, so
     an open dependency could be missed
  3  the open issues could not be read, or a ready Task's owner could not be
     read and no other Task was free
  5  no Task is ready for this clone, so nothing was started
  *  a failed `start-work` passes its exit code through
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path

from ruamel.yaml import YAML

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import (
    axis_labels,
    bootstrap_gate,
    instance_claims,
    instance_ownership,
    issue_list,
    session_guard,
    task_pool,
    topology,
)
from _lib.gh import gh_run, load_adopter_config
from _lib.membership import (
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)

#: No Task is ready for this clone: nothing was started.
EXIT_NONE_READY = 5

#: How many open issues one listing reads, unless `--limit` says otherwise.
DEFAULT_LIMIT = 1000


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Take the next ready Task from the shared pool, the highest in priority "
            "first, within this clone's seat's scope, and start it, claimed, through "
            "start-work (DEC-059 point 7)."
        ),
    )
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=f"Default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Say which Task would be started, and run start-work --dry-run on it.",
    )
    parser.add_argument("--yes", action="store_true", help="Start the Task without asking.")
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=(
            f"How many open issues to read (default {DEFAULT_LIMIT}). A listing that "
            "reaches it refuses, since a dependency it did not return could be open."
        ),
    )
    session_guard.add_override_argument(parser)
    args = parser.parse_args()
    if args.limit < 1:
        print("error: --limit must be a positive number.", file=sys.stderr)
        return 2

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return 2
    if not bootstrap_gate.enforce("next-task", capability_root=capability_root):
        return 2

    yaml_loader = YAML(typ="safe")
    config = load_adopter_config(capability_root)
    invoker = resolve_invoker_identity(config=config)
    membership = check_membership(_read_members(capability_root, yaml_loader), invoker)
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return 1
    passage = session_guard.enforce(override=args.allow_foreign_repo)
    if not passage:
        return 1

    # The seat is confirmed on its state issue before the pool is read.
    try:
        taker = task_pool.taker(capability_root, invoker.github_login, config, dry_run=args.dry_run)
    except instance_claims.Unconfirmed as exc:
        instance_claims.say_unconfirmed("next-task", None, exc)
        return 2
    if taker.refusal is not None:
        print(f"[refused] next-task: {taker.refusal}", file=sys.stderr)
        return 2

    listing = _list_open(config, args.limit)
    if listing is None:
        return 3
    if listing.returned >= args.limit:
        print(
            f"[refused] next-task: the listing reached its limit of {args.limit} open issues, "
            "so a dependency it did not return could be open. Pass a higher --limit.",
            file=sys.stderr,
        )
        return 2
    readers = task_pool.Readers(
        issue_types=_read_schema(capability_root, "issue-types.yaml", yaml_loader),
        classification=_read_schema(capability_root, "classification.yaml", yaml_loader),
        substrate_map=axis_labels.load_substrate_map(capability_root),
    )
    found = task_pool.pool(
        listing.rows or (),
        open_numbers=_numbers(listing),
        login=invoker.github_login,
        scope=taker.scope,
        takes_over=taker.takes_over,
        readers=readers,
    )
    ready = found.ready
    print(f"next-task: {_pool_line(len(ready), taker, found.titles)}")
    for line in _outside_lines(found.outside):
        print(line)

    clone = taker.clone
    # This clone's own Tasks come before the pool: only a Task assigned to its
    # account may be its own, so only those owners are read before the first start.
    read: dict[int, instance_ownership.OwnershipResolution | None] = {}
    own: set[int] = set()
    if clone is not None:
        for candidate in filter(task_pool.may_be_own, ready):
            resolution = instance_claims.read_owner(candidate.number, clone, config)
            read[candidate.number] = resolution
            if resolution is not None and task_pool.owned_by(
                resolution, clone.instance, candidate.state
            ):
                own.add(candidate.number)
    unread = 0
    for candidate in task_pool.ordered(ready, own):
        mine = False
        if clone is not None:
            if candidate.number in read:
                resolution = read.pop(candidate.number)
            else:
                resolution = instance_claims.read_owner(candidate.number, clone, config)
            if resolution is None:
                unread += 1
                print(
                    f"[warn] next-task: #{candidate.number} could not be read, so whose it is "
                    "cannot be told. Skipped.",
                    file=sys.stderr,
                )
                continue
            mine = task_pool.owned_by(resolution, clone.instance, candidate.state)
            if not mine and not task_pool.in_pool(resolution, candidate.state):
                print(f"  skipped #{candidate.number}: {_held(resolution)}")
                continue
        print(f"next-task: {candidate.describe(own=mine)}")
        if not args.dry_run and not args.yes and sys.stdin.isatty():
            reply = input(f"Start #{candidate.number}? [y/N] ").strip().lower()
            if reply not in ("y", "yes"):
                print("aborted.", file=sys.stderr)
                return 0
        rc = _start_work(
            candidate.number,
            dry_run=args.dry_run,
            capability_root_arg=args.capability_root,
            allow_foreign_repo=session_guard.confirmed(passage),
        )
        if rc == 0:
            if not args.dry_run:
                print(f"\n[ok] next-task: started #{candidate.number}")
            return 0
        if clone is not None and task_pool.taken_by_another(
            instance_claims.read_owner(candidate.number, clone, config), clone.instance
        ):
            print(
                f"[note] next-task: another instance claimed #{candidate.number} first, and the "
                "first claim holds, so this clone takes the next ready Task."
            )
            continue
        print(
            f"[failed] next-task: start-work #{candidate.number} failed (exit {rc}), and no "
            "other instance holds it, so this run stops there.",
            file=sys.stderr,
        )
        return rc
    if unread:
        print(
            f"[failed] next-task: {unread} ready Task(s) could not be read, and no other Task "
            "is free for this clone. Nothing was started.",
            file=sys.stderr,
        )
        return 3
    print("[ok] next-task: no Task is ready for this clone, so nothing was started.")
    return EXIT_NONE_READY


# ---- helpers -----------------------------------------------------------------


def _list_open(config: dict, limit: int) -> issue_list.IssueListing | None:
    """The open issues of work, through the one read of issues, or None after
    saying why it failed."""
    try:
        listing = issue_list.list_issues(
            config,
            ["--state", "open", "--limit", str(limit)],
            fields=task_pool.LIST_FIELDS,
            gh_call=_gh,
        )
    except FileNotFoundError:
        print("error: `gh` is not on PATH. Install GitHub CLI.", file=sys.stderr)
        return None
    if listing.rows is None:
        said = listing.stderr.strip() or "`gh issue list` returned no JSON list"
        print(f"error: the open issues could not be read: {said}", file=sys.stderr)
        return None
    return listing


def _gh(argv: list[str], config: dict, **kwargs: object) -> subprocess.CompletedProcess[str]:
    """Every `gh` call of the listing, through the gh helper (DEC-023)."""
    return gh_run(argv, config, check=False)


def _numbers(listing: issue_list.IssueListing) -> set[int]:
    """The number of every open issue the listing returned, state issues among
    them, so a dependency on any of them holds a Task back."""
    rows = [*(listing.rows or ()), *listing.state_rows]
    return {r["number"] for r in rows if isinstance(r, dict) and isinstance(r.get("number"), int)}


def _pool_line(count: int, taker: task_pool.Taker, titles: Mapping[int, str]) -> str:
    """The line that says how many Tasks are ready, and for whom. Each milestone
    the scope names is shown by its number, with its title from ``titles``
    beside it where the listing gave one."""
    who = "this clone" if taker.clone is None else taker.clone.named()
    scope = taker.scope
    if scope is None:
        within = "with no scope"
    else:
        parts = []
        if scope.workstreams:
            parts.append("workstreams " + ", ".join(scope.workstreams))
        if scope.types:
            parts.append("types " + ", ".join(scope.types))
        if scope.milestones:
            shown = (topology.milestone_shown(n, titles.get(n)) for n in scope.milestones)
            parts.append("milestones " + ", ".join(shown))
        within = "within the scope of " + " and ".join(parts)
    noun = "Task is" if count == 1 else "Tasks are"
    order = (
        "the highest in priority first"
        if taker.clone is None
        else "its own first, then the highest in priority"
    )
    return f"{count} {noun} ready for {who}, {within}, {order}."


def _outside_lines(outside: Iterable[task_pool.Outside]) -> list[str]:
    """One line for each reason the seat's scope leaves ready Tasks out, naming
    those Tasks by number, so a long backlog outside the scope costs a line for
    each reason rather than one for each Task."""
    numbers: dict[str, list[str]] = {}
    for skipped in outside:
        numbers.setdefault(skipped.reason, []).append(f"#{skipped.candidate.number}")
    return [
        f"  skipped {', '.join(named)}: outside the scope, {reason}"
        for reason, named in numbers.items()
    ]


def _held(resolution: instance_ownership.OwnershipResolution) -> str:
    """Why a Task is neither this clone's own nor in the pool: who holds it."""
    if not resolution.claimants:
        return "In Progress with no claim ever made on it, so it is nobody's to take over"
    return f"held by {instance_claims.owner_named(resolution, min(resolution.claimants))}"


def _start_work(
    number: int, *, dry_run: bool, capability_root_arg: Path | None, allow_foreign_repo: bool
) -> int:
    """Run `start-work <N> --yes` and return its exit code. A confirmed
    foreign-repo override is handed on, so that gate is confirmed once."""
    cmd = [sys.executable, str(_HERE / "start-work.py"), str(number), "--yes"]
    if dry_run:
        cmd.append("--dry-run")
    if allow_foreign_repo:
        cmd.append("--allow-foreign-repo")
    if capability_root_arg is not None:
        cmd += ["--capability-root", str(capability_root_arg)]
    # The lines above come before start-work's own, even where output is piped.
    sys.stdout.flush()
    sys.stderr.flush()
    return subprocess.run(cmd, check=False).returncode


def _read_members(capability_root: Path, yaml_loader: YAML) -> list[dict]:
    path = capability_root / "project" / "members.yaml"
    if not path.is_file():
        return []
    try:
        data = yaml_loader.load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    members = data.get("members") if isinstance(data, dict) else None
    return members if isinstance(members, list) else []


def _read_schema(capability_root: Path, name: str, yaml_loader: YAML) -> dict:
    """A parsed capability schema (`schemas/<name>`), or {} when absent or
    unparseable: no Task's type can then be told, and none is ready."""
    path = capability_root / "schemas" / name
    if not path.is_file():
        return {}
    try:
        data = yaml_loader.load(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


if __name__ == "__main__":
    sys.exit(main())
