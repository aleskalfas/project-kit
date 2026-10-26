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
`_lib/task_pool` reckons readiness, and its docstring says which references the
section is read for.

Steps:
  - The gates `start-work` runs: the bootstrap gate, membership (DEC-021) and
    the foreign-repo guard, whose confirmation is handed on to `start-work`.
  - Who takes: in a project with a topology, the clone's seat, whose scope
    narrows the pool. A clone that holds no seat, or holds a planner's seat,
    takes nothing. Outside a topology a clone takes with no scope.
  - One listing of the open issues of work (`_lib/issue_list`), which leaves
    state issues out. The ready Tasks are ranked from it.
  - Where the clone takes part in instance ownership, each Task in turn is read
    and its owner folded (`_lib/instance_claims.read_owner`). A Task in Backlog
    that any instance owns, this clone's own among them, is skipped, as is one
    that cannot be read: a Task with an owner is not in the pool.
  - `start-work <N> --yes` starts the first free Task. Where it fails and the
    Task is now another instance's, the first claim held: this clone backs off
    and takes the next ready Task. Any other failure stops the run.

Exit codes:
  0  a Task was started, or a dry run said which it would start
  1  membership refusal / foreign-repo refusal
  2  usage error / a clone that holds no seat, or a planner's seat / the
     listing reached its limit, so an open dependency could be missed
  3  the open issues, or every ready Task's owner, could not be read
  5  no Task is ready for this clone, so nothing was started
  *  a failed `start-work` passes its exit code through
"""

from __future__ import annotations

import argparse
import subprocess
import sys
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

    taker = task_pool.taker(capability_root, invoker.github_login, config)
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
    ready = task_pool.candidates(
        listing.rows or (),
        open_numbers=_numbers(listing),
        login=invoker.github_login,
        scope=taker.scope,
        takes_over=taker.takes_over,
        readers=readers,
    )
    print(f"next-task: {_pool_line(len(ready), taker)}")

    clone = taker.clone
    unread = 0
    for candidate in ready:
        if clone is not None:
            resolution = instance_claims.read_owner(candidate.number, clone, config)
            if resolution is None:
                unread += 1
                print(
                    f"[warn] next-task: #{candidate.number} could not be read, so whose it is "
                    "cannot be told. Skipped.",
                    file=sys.stderr,
                )
                continue
            if not task_pool.in_pool(resolution, candidate.state):
                held = _held(resolution, candidate.number, clone.instance)
                print(f"  skipped #{candidate.number}: {held}")
                continue
        print(f"next-task: {candidate.describe()}")
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


def _pool_line(count: int, taker: task_pool.Taker) -> str:
    """The line that says how many Tasks are ready, and for whom."""
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
        within = "within the scope of " + " and ".join(parts)
    noun = "Task is" if count == 1 else "Tasks are"
    return f"{count} {noun} ready for {who}, {within}, the highest in priority first."


def _held(resolution: instance_ownership.OwnershipResolution, number: int, instance: int) -> str:
    """Why Task ``number`` is not in the pool: who holds it. A Task this clone's
    own instance owns is named with the command that starts it."""
    if not resolution.claimants:
        return "In Progress with no claim ever made on it, so it is nobody's to take over"
    first = min(resolution.claimants)
    owner = instance_claims.owner_named(resolution, first)
    if first == instance:
        return (
            f"owned by this clone, {owner}, so it is not in the shared pool. "
            f"Start it with pkit pm start-work {number}"
        )
    return f"held by {owner}"


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
