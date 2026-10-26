#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — create-seats (DEC-059 point 3).

Run on the change that adds seats to the topology, `project/topology.yaml`. For
each seat that names no state issue and is not retired, it creates the seat's
state issue through the state-issue seam (`_lib/state_issues`, ADR-071) and
writes its number into the topology file in the working tree. The change then
lands with its state issues, and every clone finds a seat's state issue by its
number, with no search and no race to create it.

It is idempotent:

- a seat that names a state issue is left as it is
- a seat whose state issue an earlier run created, with no number written, is
  found by the issue's marker among the open issues, through the one read of
  issues, and its number is written
- a creation left half done, an issue whose description holds the marker and
  whose log holds no marker comment, is finished, and its number written

Each number is written as soon as its state issue exists, so a run that stops
keeps what it wrote, and the next run goes on from there.

Who may write on a state issue comes from the members the default branch holds,
at the commit the backbone resolves it to (ADR-071 point 3). A run that cannot
resolve the default branch creates nothing (COR-054 point 4).

It refuses, creating nothing, a topology whose file is wrong otherwise: a shape
the schema refuses, a seat name used twice, more than one organizer seat, or
two seats naming one state issue. `check-topology` reports each of them.

The membership gate (DEC-021), the bootstrap gate and the foreign-repo guard run
first. Creating the state issues is the person's step: the command asks at a
terminal, `--yes` authorises it, and off a terminal without `--yes` it refuses.

Usage:
  pkit pm create-seats [--dry-run] [--yes]

Exit codes:
  0  every seat names its state issue, or a dry run printed its plan
  1  refused: membership, the file's problems, the default branch, or no authorisation
  2  usage error: the capability is not found, or not bootstrapped
  3  GitHub failed, or the file could not be written; each number written stays
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import bootstrap_gate, consent, provenance, session_guard, state_issues, topology
from _lib.gh import load_adopter_config
from _lib.membership import (
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)

VERB = "create-seats"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create the state issue of each seat the topology adds, and write its number "
            "into project/topology.yaml (DEC-059 point 3)."
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the plan; create nothing.")
    parser.add_argument("--yes", action="store_true", help="Authorise creating the state issues.")
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
    if not bootstrap_gate.enforce("create-seats", capability_root=capability_root):
        return 2

    config = load_adopter_config(capability_root)
    membership = check_membership(
        _members(capability_root), resolve_invoker_identity(config=config)
    )
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return 1
    # The state issues and the file are this repository's: refuse a cd into another.
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1
    return create_seats(
        capability_root,
        gh=state_issues.runner(config),
        dry_run=args.dry_run,
        yes=args.yes,
    )


def create_seats(
    capability_root: Path,
    *,
    gh: state_issues.Gh,
    dry_run: bool = False,
    yes: bool = False,
    run: Callable[..., Any] = subprocess.run,
    git: topology.Git | None = None,
    versions: provenance.Versions | None = None,
) -> int:
    """Create the state issue of each seat that names none, and write its number.

    ``gh`` runs each `gh` call, ``run`` the backbone's reading of the default
    branch, and ``git`` the read of the members at its commit. Returns the exit
    code.
    """
    tree = topology.read_working_tree(capability_root)
    if tree is None:
        print(f"{VERB}: no topology at {topology.TOPOLOGY_RELATIVE}, so no seat to create.")
        return 0
    blocking = [p for p in tree.problems if p.code != topology.NO_STATE_ISSUE]
    if blocking:
        for problem in blocking:
            print(f"[refused] {topology.TOPOLOGY_RELATIVE}: {problem.message}", file=sys.stderr)
        print("  → nothing was created: mend the file, then run this again.", file=sys.stderr)
        return 1
    pending = [seat for seat in tree.active if seat.state_issue is None]
    if not pending:
        print(f"{VERB}: every seat of {topology.TOPOLOGY_RELATIVE} names its state issue.")
        return 0

    try:
        at = topology.settled(capability_root, run=run)
        writers = topology.writers_at(capability_root, at, git=git)
    except topology.Unresolved as exc:
        print(
            f"[refused] who may write on a state issue is read from the default branch, and "
            f"it could not be read: {exc}. Nothing was created.",
            file=sys.stderr,
        )
        return 1

    print(f"{VERB}: {len(pending)} seat(s) of {topology.TOPOLOGY_RELATIVE} name no state issue")
    for seat in pending:
        print(f"  seat {seat.number} ({seat.name}, {seat.role}): find or create its state issue")
    print(f"  who may write: {_writers_line(writers, at)}")
    if dry_run:
        print("\n[dry-run] nothing created, and the file is unchanged.")
        return 0
    stop = consent.authorise(
        "Proceed? [y/N] ",
        yes=yes,
        step="Creating the state issues of the seats",
        verb=VERB,
    )
    if stop is not None:
        return stop

    state_run = state_issues.StateRun(
        gh, writers, versions or provenance.read_versions(capability_root)
    )
    listed = state_issues.list_open(state_run)
    if listed.rows is None:
        print(f"[error] {listed.cause}. Nothing was created.", file=sys.stderr)
        return 3
    if listed.cut:
        print(
            f"warn: the listing reached {state_issues.OPEN_LIMIT} open issues, so a state issue "
            "past it was not seen, and its seat may get a second one. The first one holds the "
            "seat (DEC-058 point 2).",
            file=sys.stderr,
        )
    for seat in pending:
        number, said = state_issue_for(seat, listed.rows, state_run)
        if number is None:
            print(f"[error] seat {seat.name}: {said}. Each number written stays.", file=sys.stderr)
            return 3
        problem = write_number(capability_root, seat.name, number)
        if problem is not None:
            print(
                f"[error] seat {seat.name}: its state issue is #{number}, and {problem}. "
                "Run this again: it finds the issue by its marker.",
                file=sys.stderr,
            )
            return 3
        print(f"  seat {seat.name}: {said}, and its number is written")
    print(
        f"\n[ok] every seat of {topology.TOPOLOGY_RELATIVE} names its state issue: commit the file."
    )
    return 0


def state_issue_for(
    seat: topology.Seat, rows: Iterable[dict[str, Any]], run: state_issues.StateRun
) -> tuple[int | None, str]:
    """The number of the seat's state issue, found, finished or created, and
    what was done; or None, and why not.

    An issue finished or created is read back, so a number is written only for
    an issue every clone reads as the seat's state issue. A marker comment from
    an author who may not write counts for nothing (ADR-071 point 3)."""
    found = state_issues.find(topology.SEAT_KIND, seat.name, rows, run)
    if found.outcome == state_issues.READ and found.read is not None:
        return found.read.number, f"found #{found.read.number}, which an earlier run created"
    if found.outcome != state_issues.NO_STATE_ISSUE:
        return None, f"its state issue could not be looked for: {found.cause}"
    for number in found.half_done:
        done = state_issues.finish(number, topology.SEAT_KIND, seat.name, run)
        if done.outcome == state_issues.FINISHED:
            said = _with_note(f"finished #{number}, a creation left half done", done.cause)
            return _read_back(number, seat, run, said)
        if done.outcome != state_issues.NO_STATE_ISSUE:
            return (
                None,
                f"#{number}, a creation left half done, could not be finished: {done.cause}",
            )
        print(f"  warn: seat {seat.name}: {done.cause}, and it is left alone", file=sys.stderr)
    created = state_issues.create(topology.SEAT_KIND, seat.name, title(seat), run)
    if created.outcome == state_issues.CREATED and created.number is not None:
        said = _with_note(f"created #{created.number}", created.cause)
        return _read_back(created.number, seat, run, said)
    if created.number is not None:
        return None, (
            f"#{created.number} was created and not finished ({created.cause}): run this "
            "again, and it finishes it"
        )
    return None, f"its state issue could not be created: {created.cause}"


def _read_back(
    number: int, seat: topology.Seat, run: state_issues.StateRun, said: str
) -> tuple[int | None, str]:
    back = state_issues.read(number, topology.SEAT_KIND, seat.name, run)
    if back.outcome == state_issues.READ:
        return number, said
    return None, (
        f"{said}, and it does not read as the seat's state issue ({back.cause}). Its marker "
        "comment counts only from an author who may write, as the default branch holds the "
        "members"
    )


def title(seat: topology.Seat) -> str:
    """The title of a seat's state issue, for people."""
    return f"Seat {seat.name}"


def write_number(capability_root: Path, name: str, number: int) -> str | None:
    """Write ``number`` as the state issue of the seat ``name`` in the working
    tree's topology, keeping the file's comments. None once written, or where
    the file already says so; else what went wrong."""
    file = topology.path(capability_root)
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    try:
        data = yaml.load(file.read_text(encoding="utf-8"))
    except (OSError, YAMLError) as exc:
        return f"the file could not be read: {exc}"
    seats = data.get("seats") if isinstance(data, dict) else None
    entry = next(
        (
            s
            for s in (seats if isinstance(seats, list) else [])
            if isinstance(s, dict) and s.get("name") == name
        ),
        None,
    )
    if entry is None:
        return "the file no longer holds the seat"
    if entry.get("state_issue") == number:
        return None
    entry["state_issue"] = number
    try:
        with file.open("w", encoding="utf-8") as f:
            yaml.dump(data, f)
    except OSError as exc:
        return f"the file could not be written: {exc}"
    return None


def _with_note(said: str, note: str | None) -> str:
    return f"{said} ({note})" if note else said


def _writers_line(writers: state_issues.Writers, at: topology.Settled) -> str:
    where = f"{at.ref} at {at.commit}" if at.commit else f"{at.ref}, which has no commit yet"
    if writers.gate_open:
        return f"anyone with write access, since {where} names no member"
    return f"the {len(writers.logins)} member(s) {where} names"


def _members(capability_root: Path) -> list[dict]:
    """The members the working tree holds, as DEC-021's check of who runs a
    command reads them."""
    file = capability_root / topology.MEMBERS_RELATIVE
    try:
        data = YAML(typ="safe").load(file.read_text(encoding="utf-8")) if file.is_file() else None
    except (OSError, YAMLError):
        data = None
    members = data.get("members") if isinstance(data, dict) else None
    return members if isinstance(members, list) else []


if __name__ == "__main__":
    sys.exit(main())
