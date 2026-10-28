#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — set-pool (verb-subject per DEC-020).

Sets or clears the pool of workers an open Milestone is in, by the `Pool:` line
of its description ([project-management:DEC-061-pools-of-workers] point 2):

    set-pool <milestone> <pool> [--yes] [--dry-run]
    set-pool <milestone> --clear [--yes] [--dry-run]

Each Task in the Milestone goes with it into the pool, so a line of work starts
or finishes with no change to the topology (DEC-061 point 3).

- **The person's act** (DEC-061 point 6). Setting, changing or clearing a
  Milestone's pool asks the person: at a terminal, or `--yes`, given only on
  their word. Off a terminal without it, the command refuses before anything is
  written. An agent never gives the person's word for itself.
- **The pool** is one the topology of the default branch declares. A name it
  does not declare, or a topology that cannot be read, is refused.
- **The line is replaced, never added.** The write puts one `Pool:` line where
  the first stood, under the `Close trigger:` line where there was none, and
  removes every other. It reads the description again right before it writes,
  so a change a person made since the first read stays (DEC-061 point 3).
- **The log.** A Milestone holds no comments, so the description logs the
  change and the consent, in a line that never takes the `Pool:` form.

A closed Milestone holds no line of work (DEC-061 point 4), so it is refused.
The membership gate (DEC-021), the bootstrap gate and the foreign-repo guard
(COR-039) run first, and every `gh` call goes through the gh helper (DEC-023).

Exit codes:
  0  set or cleared, already so, a dry run, or the person declined at the prompt
  1  membership / foreign-repo refusal / off a terminal without --yes
  2  usage error: no pool and no --clear, or both / the milestone matches no
     open milestone, or is closed / a pool the topology does not declare, or
     cannot be told to declare
  3  gh failure
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import bootstrap_gate, consent, milestone, pools, session_guard
from _lib.gh import gh_run, load_adopter_config
from _lib.membership import (
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)

VERB = "set-pool"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Set or clear the pool of workers an open milestone is in, by the `Pool:` line "
            "of its description, with the person's consent, logged there (DEC-061)."
        ),
    )
    parser.add_argument("milestone", help="The open milestone, by its number or exact title.")
    parser.add_argument(
        "pool", nargs="?", default=None, help="The pool, one the topology declares."
    )
    parser.add_argument("--clear", action="store_true", help="Take the milestone out of its pool.")
    parser.add_argument("--yes", action="store_true", help="The person's consent, on their word.")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan; write nothing.")
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=f"Default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/.",
    )
    session_guard.add_override_argument(parser)
    args = parser.parse_args()
    if (args.pool is None) == (not args.clear):
        print("error: name a pool, or pass --clear, and not both.", file=sys.stderr)
        return 2

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return 2
    if not bootstrap_gate.enforce("set-pool", capability_root=capability_root):
        return 2
    config = load_adopter_config(capability_root)
    invoker = resolve_invoker_identity(config=config)
    membership = check_membership(read_members(capability_root), invoker)
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return 1
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1
    return set_pool(
        capability_root,
        args.milestone,
        None if args.clear else args.pool,
        config=config,
        yes=args.yes,
        dry_run=args.dry_run,
    )


def set_pool(
    capability_root: Path,
    target: str,
    name: str | None,
    *,
    config: dict,
    yes: bool = False,
    dry_run: bool = False,
) -> int:
    """Put the open milestone ``target`` into the pool ``name``, or take it out
    of its pool where ``name`` is None. Returns the exit code."""
    number = _number(target, config)
    if number is None:
        print(
            f"error: no open milestone matches {target!r}. Pass its number, or the exact title "
            "of an open milestone.",
            file=sys.stderr,
        )
        return 2
    found = milestone.fetch_milestone(number, config)
    if found is None:
        return 3
    if str(found.get("state") or "").lower() != "open":
        print(
            f"error: milestone #{number} is closed, and a closed milestone holds no line of "
            "work (DEC-061 point 4).",
            file=sys.stderr,
        )
        return 2
    if name is not None:
        refusal = pools.write_refusal(name, capability_root)
        if refusal is not None:
            print(f"[refused] {VERB}: {refusal} Nothing was written.", file=sys.stderr)
            return 2
    title = str(found.get("title") or "")
    line = milestone.parse_pool_line(str(found.get("description") or ""))
    before = line.name
    print(f"{VERB}: milestone #{number} {title}".rstrip())
    print(f"  pool: {before or 'none'} → {name or 'none'}")
    if line.reason == milestone.NO_POOL_LINE and name is None:
        print(f"\n[ok] milestone #{number} has no `Pool:` line, so it is in no pool already.")
        return 0
    if line.reason is None and before == name:
        print(f"\n[ok] milestone #{number} is in the pool {name} already.")
        return 0
    if dry_run:
        print("\n[dry-run] nothing written.")
        return 0
    what = f"into the pool {name}" if name is not None else "out of its pool"
    stop = consent.authorise(
        f"Put milestone #{number} {what}? [y/N] ",
        yes=yes,
        step=f"Putting milestone #{number} {what}",
        verb=VERB,
    )
    if stop is not None:
        return stop
    # Read again right before the write, so a change made since stays (DEC-061 point 3).
    fresh = milestone.fetch_milestone(number, config)
    if fresh is None:
        return 3
    current = str(fresh.get("description") or "")
    was = milestone.parse_pool_line(current).name
    description = milestone.with_log_line(
        milestone.with_pool_line(current, name),
        milestone.pool_log_line(was, name, verb=VERB, today=dt.date.today().isoformat()),
    )
    if not _write(number, description, config):
        return 3
    print(f"\n[ok] milestone #{number} is {'in the pool ' + name if name else 'in no pool'}.")
    return 0


def _number(target: str, config: dict) -> int | None:
    """The milestone's number: a number as given, else the open one titled so."""
    if target.strip().lstrip("#").isdigit():
        return int(target.strip().lstrip("#"))
    resolved = milestone.resolve_milestone(target, config)
    return resolved.number if resolved is not None else None


def _write(number: int, description: str, config: dict) -> bool:
    """PATCH the milestone's description through the gh helper (DEC-023)."""
    argv = [
        "gh",
        "api",
        "-X",
        "PATCH",
        f"repos/{{owner}}/{{repo}}/milestones/{number}",
        "-f",
        f"description={description}",
    ]
    try:
        proc = gh_run(argv, config, check=False)
    except FileNotFoundError:
        print("error: `gh` not on PATH.", file=sys.stderr)
        return False
    if proc.returncode != 0:
        print(
            f"error: gh failed writing milestone #{number}'s description "
            f"(exit {proc.returncode}): {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    return True


def read_members(capability_root: Path) -> list[dict]:
    """The members the working tree holds, as DEC-021's check reads them."""
    file = capability_root / "project" / "members.yaml"
    try:
        data = YAML(typ="safe").load(file.read_text(encoding="utf-8")) if file.is_file() else None
    except (OSError, YAMLError):
        data = None
    members = data.get("members") if isinstance(data, dict) else None
    return members if isinstance(members, list) else []


if __name__ == "__main__":
    sys.exit(main())
