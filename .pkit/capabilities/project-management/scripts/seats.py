#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — seats (DEC-059 point 3).

Lists the seats of the project's topology, as the default branch holds it at
the commit the backbone resolves it to, and says which commit it read (point
1). For each seat it shows its number, its name, its role, the agent definition
it names, its scope, whether it is the organizer seat or retired, its state
issue and its holder. The holder is read from the seat's state issue through
the state-issue seam (`_lib/state_issues`, ADR-071): an account and a clone's
key, with where the clone lies, or free. The seat this clone holds is marked.

It then names each open state issue of a seat that no seat of the topology
names, such as one a change closed unmerged left, for a person to close on
GitHub (point 3). The open state issues come from the one read of issues, never
GitHub's search.

Last, it names each Task in Review that a released seat left, with its pull
request, for a person to land or to hand over (points 5 and 9). Such a Task's
claim stopped counting because its seat was released, by its clone or by force.
The claim names the seat and the clone's key (point 9), and that clone opened
the pull request: the clone that holds a Task's claim builds the Task, and
`review-work`, which makes the pull request ready and moves the Task to Review,
refuses another seat's clone short of a bypass whose reason it posts on the
Task. No worker's loop takes such a Task up, since the pool holds only Tasks in
Backlog and In Progress (point 7).

The Tasks come from the same listing of open issues. Each Task's owner comes
from the ownership seam's fold of its whole log (`_lib/instance_ownership`,
ADR-041 point 7), judged against the seats' holders this run read. A Task's
log is read only once a seat's state issue logs a release. The pull request is
the open one from the Task's branch, `<type>/<N>-<slug>` (DEC-013), read in one
listing.

A read of a state issue restores a marker a hand removed from its description,
the one write a read makes (ADR-071 point 5), so the foreign-repo guard runs
first, after the membership gate (DEC-021) and the bootstrap gate.

Usage:
  pkit pm seats

Exit codes:
  0  listed, or the default branch declares no topology
  1  refused: membership, or the default branch cannot be resolved
  2  usage error: the capability is not found, or not bootstrapped
  3  a seat's state issue, the listing of open issues, a Task's log or the
     listing of open pull requests could not be read
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import (
    axis_labels,
    bootstrap_gate,
    instance_claims,
    instance_identity,
    issue_branch,
    issue_list,
    issue_position,
    session_guard,
    state_issues,
    topology,
)
from _lib import instance_ownership as ownership
from _lib.gh import load_adopter_config
from _lib.membership import (
    CAPABILITY_NAME,
    check_membership,
    members_path,
    resolve_capability_root,
    resolve_invoker_identity,
)

VERB = "seats"

#: The fields of the one listing of open issues: the state issues no seat names,
#: and the Tasks in Review a released seat left.
LIST_FIELDS = "number,title,labels,assignees,milestone,state"

#: How many open issues, and open pull requests, one listing reads.
LIST_LIMIT = state_issues.OPEN_LIMIT

#: The state a Task waits in for its reviewers and a person (DEC-059 point 9).
REVIEW = "review"

#: Why a claim stopped counting, where its seat was released after it was made
#: (ADR-041 point 7).
RELEASED_SEAT = frozenset({ownership.SEAT_RELEASED, ownership.SEAT_RELEASED_SINCE})


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "List the topology's seats, each with its role and its holder, then the Tasks "
            "in Review a released seat left, with their pull requests (DEC-059)."
        ),
    )
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=f"Default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/.",
    )
    session_guard.add_override_argument(parser)
    args = parser.parse_args()

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return 2
    if not bootstrap_gate.enforce("seats", capability_root=capability_root):
        return 2
    config = load_adopter_config(capability_root)
    invoker = resolve_invoker_identity(config=config)
    membership = check_membership(read_members(capability_root), invoker)
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return 1
    # A read restores a missing marker on a state issue of this repository.
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1
    return list_seats(capability_root, login=invoker.github_login, gh=state_issues.runner(config))


def list_seats(
    capability_root: Path,
    *,
    login: str | None,
    gh: state_issues.Gh,
    run: Callable[..., Any] = subprocess.run,
    git: topology.Git | None = None,
    versions: Any = None,
) -> int:
    """Print each seat with its role and its holder, then the state issues no
    seat names, then the Tasks in Review a released seat left. Returns the exit
    code."""
    try:
        snap = topology.snapshot(
            capability_root,
            gh=gh,
            account=login,
            key=instance_identity.read_clone_key(capability_root),
            run=run,
            git=git,
            versions=versions,
        )
    except topology.Unresolved as exc:
        print(
            f"[refused] {VERB}: the topology could not be read from the default branch ({exc}).",
            file=sys.stderr,
        )
        return 1
    if snap is None:
        print(f"{VERB}: the default branch declares no topology ({topology.TOPOLOGY_RELATIVE}).")
        return 0
    tree = snap.topology
    retired = len(tree.seats) - len(tree.active)
    print(
        f"{VERB}: the topology of {tree.where()}, {len(tree.seats)} seat(s)"
        + (f", {retired} retired" if retired else "")
    )
    for problem in tree.problems:
        print(f"warn: {topology.TOPOLOGY_RELATIVE}: {problem.message}", file=sys.stderr)
    code = 0
    for state in snap.states():
        print(seat_line(state, mine=state.held_by(snap.clone)))
        if state.state == topology.UNREAD and state.seat.state_issue is not None:
            code = 3
    listing, cause = list_open(snap.run.gh)
    if listing is None:
        print(
            f"[error] the open issues could not be listed: {cause}, so no stray state issue, "
            "and no Task in Review a released seat left, is named.",
            file=sys.stderr,
        )
        return 3
    if listing.returned >= LIST_LIMIT:
        print(
            f"warn: the listing reached {LIST_LIMIT} open issues, so a state issue or a Task "
            "past it is not named below.",
            file=sys.stderr,
        )
    strays = stray_state_issues(tree, listing.state_rows)
    if strays:
        print("\nState issues no seat names, for a person to close (DEC-059 point 3):")
        for number, key in strays:
            print(f"  #{number}  seat {key}")
    left = left_in_review(
        snap, listing.rows or (), substrate_map=axis_labels.load_substrate_map(capability_root)
    )
    show_left(left)
    return 3 if left.unread else code


# ---- the Tasks in Review a released seat left (DEC-059 points 5 and 9) ---------------


@dataclass(frozen=True)
class LeftTask:
    """A Task in Review whose claim a released seat's clone made: the claim's
    seat, the clone's key and its account, and the open pull requests from the
    Task's branch, or None where they could not be read."""

    number: int
    title: str
    seat: str
    clone: str
    account: str
    pull_requests: tuple[int, ...] | None = None


@dataclass(frozen=True)
class Left:
    """What the listing found of the Tasks in Review a released seat left, and
    what it could not read, one cause to each."""

    tasks: tuple[LeftTask, ...] = ()
    unread: tuple[str, ...] = ()


def list_open(gh: state_issues.Gh) -> tuple[issue_list.IssueListing | None, str | None]:
    """The open issues, through the one read of issues, which keeps the state
    issues apart; or None, and why."""

    def gh_call(argv: list[str], _config: Any, **_kwargs: Any) -> Any:
        return gh(argv)

    try:
        listing = issue_list.list_issues(
            {}, ["--state", "open", "--limit", str(LIST_LIMIT)], fields=LIST_FIELDS, gh_call=gh_call
        )
    except FileNotFoundError:
        return None, "`gh` is not on PATH"
    if listing.rows is None:
        said = listing.stderr.strip().splitlines()
        return None, said[-1] if said else "no list"
    return listing, None


def ever_released(states: Iterable[topology.SeatState]) -> bool:
    """Whether a seat's state issue logs a release that freed the seat, by its
    clone or by force. Until one does, no claim has stopped counting for its
    seat's release, so no Task's log is read."""
    released = (state_issues.RELEASE, state_issues.FORCE_RELEASE)
    return any(
        event.type in released and not event.void
        for state in states
        if state.read is not None and state.read.fold is not None
        for event in state.read.fold.events
    )


def left_in_review(
    snap: topology.Snapshot,
    rows: Iterable[Any],
    *,
    substrate_map: axis_labels.SubstrateMap | None,
) -> Left:
    """The Tasks in Review among ``rows``, the open issues of work, that a
    released seat left, each with the open pull requests from its branch.

    A Task is left where a claim on it stopped counting because its seat was
    released, and no claim counts or stands unjudged (DEC-059 points 5 and 9).
    Each Task's whole log is folded by the ownership seam for each of its
    assignees, since a claim counts only from the account it is assigned to
    (DEC-043 point 3)."""
    if not ever_released(snap.states()):
        return Left()
    holders = instance_claims.SeatHolders(snap)
    tasks: list[LeftTask] = []
    unread: list[str] = []
    for row in rows:
        if not _in_review(row, substrate_map):
            continue
        number = row["number"]
        log = ownership.read_log(number, snap.run.gh)
        if not log.complete:
            unread.append(
                f"the log of #{number}, in Review, could not be read ({log.cause}), so whether "
                "a released seat left it cannot be told."
            )
            continue
        folds = {
            account: ownership.resolve_owner(
                comments=log.comments, labels=(), assignee_login=account, holders=holders
            )
            for account in _assignees(row)
        }
        if any(resolution.claimants for resolution in folds.values()):
            continue
        title = str(row.get("title") or "")
        for account, resolution in folds.items():
            tasks.extend(
                LeftTask(number, title, judged.seat, judged.clone or "", account)
                for judged in resolution.judgements
                if judged.reason in RELEASED_SEAT and judged.seat
            )
    if not tasks:
        return Left(unread=tuple(unread))
    tasks.sort(key=lambda task: (_place(snap, task.seat), task.clone, task.account, task.number))
    heads, cause = open_pull_requests(snap.run.gh)
    if heads is None:
        unread.append(
            f"the open pull requests could not be listed ({cause}), so no Task above names "
            "its pull request."
        )
        return Left(tuple(tasks), tuple(unread))
    found = tuple(
        replace(task, pull_requests=pull_requests_of(task.number, heads)) for task in tasks
    )
    return Left(found, tuple(unread))


def _place(snap: topology.Snapshot, name: str) -> int:
    """The seat's number, its place in the topology, for the listing's order."""
    seat = snap.topology.seat(name)
    return seat.number if seat is not None else 0


def pull_requests_of(number: int, heads: Mapping[int, str]) -> tuple[int, ...]:
    """The open pull requests, by number, whose head branch is the Task
    ``number``'s by its name, `<type>/<N>-<slug>` (DEC-013)."""
    return tuple(
        sorted(pr for pr, head in heads.items() if issue_branch.is_issue_branch(head, number))
    )


def open_pull_requests(gh: state_issues.Gh) -> tuple[dict[int, str] | None, str | None]:
    """The head branch of each open pull request, by its number, in one
    listing; or None, and why."""
    argv = ["gh", "pr", "list", "--state", "open", "--limit", str(LIST_LIMIT)]
    argv += ["--json", "number,headRefName"]
    try:
        proc = gh(argv)
    except FileNotFoundError:
        return None, "`gh` is not on PATH"
    if getattr(proc, "returncode", 1) != 0:
        said = str(getattr(proc, "stderr", "") or "").strip().splitlines()
        return None, said[-1] if said else f"gh exited {getattr(proc, 'returncode', '?')}"
    try:
        rows = json.loads(getattr(proc, "stdout", "") or "")
    except (TypeError, ValueError):
        return None, "gh's answer is not JSON"
    if not isinstance(rows, list):
        return None, "gh's answer is no list"
    if len(rows) >= LIST_LIMIT:
        print(
            f"warn: the listing reached {LIST_LIMIT} open pull requests, so a pull request "
            "past it is not named below.",
            file=sys.stderr,
        )
    return {
        row["number"]: str(row.get("headRefName") or "")
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("number"), int)
    }, None


def show_left(left: Left) -> None:
    """Print the Tasks in Review a released seat left, under the seat and the
    clone whose claims stopped counting, then what could not be read."""
    if left.tasks:
        print(
            "\nTasks in Review that a released seat left, each for a person to land or to hand "
            "over to a worker (DEC-059 points 5 and 9):"
        )
        groups: dict[tuple[str, str, str], list[LeftTask]] = {}
        for task in left.tasks:
            groups.setdefault((task.seat, task.clone, task.account), []).append(task)
        for (seat, clone, account), tasks in groups.items():
            print(f"  seat {seat}, clone {topology.shown(clone)} of @{topology.shown(account)}:")
            for task in tasks:
                print(f"    #{task.number} {topology.shown(task.title)}: {_said_prs(task)}")
    for problem in left.unread:
        print(f"[error] {problem}", file=sys.stderr)


def _said_prs(task: LeftTask) -> str:
    """The Task's open pull requests, in words a line can carry."""
    if task.pull_requests is None:
        return "its pull request could not be read"
    if not task.pull_requests:
        return "no open pull request from its branch"
    noun = "pull request" if len(task.pull_requests) == 1 else "pull requests"
    return f"{noun} " + ", ".join(f"#{n}" for n in task.pull_requests)


def _in_review(row: Any, substrate_map: axis_labels.SubstrateMap | None) -> bool:
    """Whether ``row``, an open issue of work, is in Review. Review is a Task's
    state alone (DEC-006), so no type is read."""
    if not isinstance(row, dict) or not isinstance(row.get("number"), int):
        return False
    labels = [
        str(label.get("name", "")) if isinstance(label, dict) else str(label)
        for label in row.get("labels") or []
    ]
    return issue_position.current_state(row, labels, substrate_map) == REVIEW


def _assignees(row: Mapping[str, Any]) -> list[str]:
    return [
        str(a.get("login"))
        for a in row.get("assignees") or []
        if isinstance(a, dict) and a.get("login")
    ]


def seat_line(state: topology.SeatState, *, mine: bool) -> str:
    """One seat as the listing shows it."""
    seat = state.seat
    marks = [seat.role, f"agent {seat.agent}"]
    if seat.organizer:
        marks.append("organizer")
    if seat.retired:
        marks.append("retired")
    if seat.scope is not None:
        parts = [
            f"{label} {' and '.join(names)}"
            for label, names in (
                ("workstreams", seat.scope.workstreams),
                ("types", seat.scope.types),
            )
            if names
        ]
        marks.append("scope: " + " with ".join(parts))
    issue = f"#{seat.state_issue}" if seat.state_issue is not None else "no state issue"
    holder = "no state issue named" if seat.state_issue is None else state.said()
    line = f"  {seat.number}. {seat.name} ({', '.join(marks)}), {issue}: {holder}"
    return line + ("  ← this clone" if mine else "")


def stray_state_issues(
    tree: topology.Topology, rows: Iterable[dict[str, Any]]
) -> list[tuple[int, str]]:
    """The open state issues of a seat that no seat of ``tree`` names, by their
    description's marker, in number order.

    Anyone who may open an issue may write such a marker, so a key that is no
    seat's name is shown quoted, with each character a terminal acts on
    escaped."""
    named = {seat.state_issue for seat in tree.seats if seat.state_issue is not None}
    out: list[tuple[int, str]] = []
    for row in rows:
        number = row.get("number")
        if not isinstance(number, int) or number in named:
            continue
        marker = state_issues.read_marker(str(row.get("body") or ""))
        if marker is not None and marker.kind == topology.SEAT_KIND and marker.key:
            key = marker.key
            out.append((number, key if topology.NAME_PATTERN.fullmatch(key) else repr(key)))
    return sorted(out)


def read_members(capability_root: Path) -> list[dict]:
    """The members the working tree holds, as DEC-021's check of who runs a
    command reads them."""
    file = members_path(capability_root)
    try:
        data = YAML(typ="safe").load(file.read_text(encoding="utf-8")) if file.is_file() else None
    except (OSError, YAMLError):
        data = None
    members = data.get("members") if isinstance(data, dict) else None
    return members if isinstance(members, list) else []


if __name__ == "__main__":
    sys.exit(main())
