#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — sync-board (verb-subject per DEC-020).

Writes the board's Status again from every issue's state, the projection
[project-management:DEC-006-state-machine-and-cascade] has the agent maintain:
"When a Projects v2 board exists, its Status field is a projection the agent
maintains. When the board and native primitives disagree, native wins."
`move-issue`, its cascade and `create-issue` keep the Status as they write; this
command brings a whole board level after a write that failed, a card a person
dragged by hand, or a board set up after the issues were filed.

It runs where a board is configured and the state is not carried on it
(`_lib/board_status`). Where the board carries the state, its Status is the
state's source, and the command refuses.

What it does:

  * reads every card on the board with its Status, and every open issue of
    this repository, through the capability's one read of its issues (state
    issues are left out, DEC-058 point 3);
  * reads each issue's state as `_lib/lifecycle_inference` does: closed is
    Done; else its state label, its milestone (Backlog) or neither (Todo);
  * names each card whose Status differs, the issue's state winning, and each
    open issue with no card;
  * writes the Status on those cards only, and adds a card for each open issue
    that has none, then sets its Status.

A card for another repository's issue, a pull request or a draft is left alone.
So is a card whose issue's state has no Status option: the options missing from
the board's Status field are named first, with the remedy.

`--dry-run` prints the plan and writes nothing. Otherwise the plan is printed
and consent is asked before the first write; `--yes` skips the prompt, and a
run with no terminal and no `--yes` refuses. The membership gate (DEC-021) runs
at startup, and the foreign-repo guard (COR-039) before the first write.

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/sync-board.py --dry-run

Or via the dispatcher (per COR-021):
  pkit pm sync-board --dry-run

Exit codes:
  0  written, nothing to write, a dry run, or declined at the prompt
  1  membership or foreign-repo refusal
  2  usage: no board configured, the board carries the state, the board has
     no single-select Status field, an un-bootstrapped project, or a run with
     no terminal and no --yes
  3  gh failure: the repository, the issues or the board could not be read, or
     a Status or a card could not be written (the others are still written)
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import axis_labels, board_fields, board_status, bootstrap_gate, containment, session_guard
from _lib import lifecycle_inference as infer
from _lib.gh import gh_project_run, gh_run, load_adopter_config
from _lib.membership import (
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)

VERB = "sync-board"

# The fields the read of open issues asks for: what the state is read from, and
# the url a card is added by.
_ISSUE_FIELDS = "number,state,labels,milestone,url"


@dataclass(frozen=True)
class Write:
    """One card to set: the issue, the state it is in, the option that state
    takes, the card (None for one still to add, by ``url``), and the option the
    card holds now (None for no Status)."""

    number: int
    state: str
    name: str
    item_id: str | None
    was: str | None = None
    url: str = ""


@dataclass(frozen=True)
class Plan:
    """What the run writes: the cards that differ, the open issues with no card,
    the cards left as they are with why, and how many cards already agree."""

    changes: tuple[Write, ...]
    adds: tuple[Write, ...]
    left: tuple[tuple[int, str], ...]
    agree: int


def main() -> int:
    args = _build_parser().parse_args()

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return 2
    # Prerequisite gate (#747): refuse on an un-bootstrapped project.
    if not bootstrap_gate.enforce("sync-board", capability_root=capability_root):
        return 2

    yaml_loader = YAML(typ="safe")
    config = load_adopter_config(capability_root)
    members = _read_members(capability_root, yaml_loader)
    membership = check_membership(members, resolve_invoker_identity(config=config))
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return 1

    substrate_map = axis_labels.load_substrate_map(capability_root)
    if board_fields.board_number(config) is None:
        print(
            "error: no Projects v2 board is configured: project/config.yaml needs "
            "`has_projects_v2_board: true` and `projects_v2_board_id: <number>`. "
            "Nothing was read or written.",
            file=sys.stderr,
        )
        return 2
    if not board_status.maintained(config, substrate_map):
        print(
            "error: the board carries the state here, so the Status is the state's source, "
            "not a projection of it (DEC-006); sync-board writes only the projection. "
            "Nothing was read or written.",
            file=sys.stderr,
        )
        return 2

    workflow = _read_yaml(capability_root / "schemas" / "workflow.yaml", yaml_loader)
    status = board_status.Projector(config, workflow)
    read = status.field()
    if read.field is None:
        print(f"error: the board's Status could not be read: {read.error}", file=sys.stderr)
        return 2 if read.answered else 3
    for name in board_status.missing_options(read.field, workflow):
        print(
            f"[warn] the board's Status field has no option for {name}: add it to the field "
            "on the board, then run sync-board again",
            file=sys.stderr,
        )

    repository, failure = _repository(config)
    if repository is None:
        print(f"error: this repository could not be read: {failure}", file=sys.stderr)
        return 3
    corpus = containment.fetch_issue_corpus(config, fields=_ISSUE_FIELDS, state="open")
    if corpus is None:
        print("error: the open issues could not be read (gh failed).", file=sys.stderr)
        return 3
    if not corpus.complete:
        print(
            "[warn] the open issues were not read in full: a card whose issue was not "
            "read is left as it is, and no card is added for it.",
            file=sys.stderr,
        )
    cards = board_fields.read_items(
        config, project_node_id=read.field.project_id, field_name=board_status.STATUS_FIELD
    )
    if not cards.ok:
        print(f"error: the board's cards could not be read: {cards.error}", file=sys.stderr)
        return 3

    plan = plan_sync(
        cards.items,
        corpus.rows,
        repository=repository,
        field=read.field,
        workflow=workflow,
        substrate_map=substrate_map,
    )
    _print_plan(plan, board=status.board, cards=len(cards.items), issues=len(corpus.rows))

    if args.dry_run:
        print("\n[dry-run] nothing written.")
        return 0
    if not plan.changes and not plan.adds:
        print("\nevery card's Status matches its issue's state; nothing to write.")
        return 0

    # Foreign-repo mutation guard (COR-039 / ADR-034): everything above only
    # read; this is the first write.
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1
    count = len(plan.changes) + len(plan.adds)
    stop = _consent(yes=args.yes, prompt=f"Write {count} card(s)? [y/N] ", rerun=_rerun(args))
    if stop is not None:
        return stop

    return _apply(plan, status, config)


# ---- the plan ----------------------------------------------------------


def plan_sync(
    cards: tuple[board_fields.BoardItem, ...],
    rows: tuple[Any, ...],
    *,
    repository: str,
    field: board_status.StatusField,
    workflow: dict,
    substrate_map: axis_labels.SubstrateMap | None,
) -> Plan:
    """Compare each of this repository's cards with its issue's state.

    A closed issue is Done. An open one is read from its row of the open issues,
    and one with no row was not read, so its card is left as it is. Pull
    requests, drafts and other repositories' issues are not this command's."""
    open_rows = {row["number"]: row for row in rows if isinstance(row.get("number"), int)}
    changes: list[Write] = []
    left: list[tuple[int, str]] = []
    agree = 0
    carded: set[int] = set()
    for card in cards:
        if card.kind != "Issue" or card.number is None:
            continue
        if card.repository.lower() != repository.lower():
            continue
        carded.add(card.number)
        if card.closed:
            state = "done"
        elif card.number in open_rows:
            state = _state_of(open_rows[card.number], substrate_map)
        else:
            left.append((card.number, "its state was not read"))
            continue
        target = _target(state, field, workflow)
        if isinstance(target, _Unplaced):
            left.append((card.number, target.why))
        elif card.option_id == target.option:
            agree += 1
        else:
            changes.append(Write(card.number, state, target.name, card.item_id, card.option_name))
    adds: list[Write] = []
    for number in sorted(set(open_rows) - carded):
        state = _state_of(open_rows[number], substrate_map)
        target = _target(state, field, workflow)
        if isinstance(target, _Unplaced):
            left.append((number, f"no card, and {target.why}"))
        else:
            url = str(open_rows[number].get("url") or "")
            adds.append(Write(number, state, target.name, None, url=url))
    return Plan(tuple(changes), tuple(adds), tuple(left), agree)


@dataclass(frozen=True)
class _Placed:
    name: str
    option: str


@dataclass(frozen=True)
class _Unplaced:
    why: str


def _target(state: str, field: board_status.StatusField, workflow: dict) -> _Placed | _Unplaced:
    """The option the state takes on this board, or why it takes none."""
    name = board_status.option_name(workflow, state)
    if name is None:
        return _Unplaced(f"the state {state!r} has no Status option")
    option = board_fields.option_id(field.field, name)
    if option is None:
        return _Unplaced(f"the board's Status field has no {name!r} option")
    return _Placed(name, option)


def _state_of(row: dict, substrate_map: axis_labels.SubstrateMap | None) -> str:
    """An open issue's state, as `_lib/lifecycle_inference` reads it."""
    labels = [
        label.get("name", "") if isinstance(label, dict) else str(label)
        for label in (row.get("labels") or [])
    ]
    return infer.infer_current_state(
        state="open",
        milestone=row.get("milestone") or None,
        labels=labels,
        substrate_map=substrate_map,
    )


# ---- the run -----------------------------------------------------------


def _apply(plan: Plan, status: board_status.Projector, config: dict) -> int:
    """Write the plan: the cards that differ, then the cards to add. Each failure
    is one line, and the rest are still written."""
    print()
    written = added = failed = 0
    for change in plan.changes:
        result = status.write(change.number, change.state, item_id=change.item_id)
        if result.ok:
            written += 1
            print(f"  {result.line()}")
        else:
            failed += 1
            print(f"  [fail] #{change.number}: the board's Status was not set: {result.failure}")
    for add in plan.adds:
        item_id, failure = _add_card(add.url, config)
        if item_id is None:
            failed += 1
            print(f"  [fail] #{add.number}: its card could not be added: {failure}")
            continue
        added += 1
        result = status.write(add.number, add.state, item_id=item_id)
        if result.ok:
            written += 1
            print(f"  {result.line()}")
        else:
            failed += 1
            print(
                f"  [fail] #{add.number}: its card was added, its Status not set: {result.failure}"
            )
    print(f"done: {written} Status set, {_cards(added)} added, {failed} failed")
    return 3 if failed else 0


def _add_card(url: str, config: dict) -> tuple[str | None, str]:
    """Add the issue at ``url`` to the configured board: its card's id, or None
    and why. Board membership (DEC-019), which ADR-031 point 3 names out of the
    substrate writes, so it is constructed here, as `create-issue` does."""
    number = board_fields.board_number(config)
    owner = url.split("/")[3] if url.count("/") >= 4 else None
    cmd = ["gh", "project", "item-add", str(number), "--url", url, "--format", "json"]
    try:
        proc = gh_project_run(cmd, config, fallback_owner=owner, check=False)
    except FileNotFoundError:
        return None, "`gh` is not on PATH"
    if proc.returncode != 0:
        return None, " ".join((proc.stderr or "no stderr").split())
    try:
        payload = json.loads(proc.stdout or "")
    except ValueError:
        payload = None
    item_id = payload.get("id") if isinstance(payload, dict) else None
    if not isinstance(item_id, str) or not item_id:
        return None, "`gh project item-add` returned no card id"
    return item_id, ""


def _repository(config: dict) -> tuple[str | None, str]:
    """This repository's `owner/name`, which tells its cards from others'."""
    try:
        proc = gh_run(["gh", "repo", "view", "--json", "nameWithOwner"], config, check=False)
    except FileNotFoundError:
        return None, "`gh` is not on PATH"
    if proc.returncode != 0:
        return None, " ".join((proc.stderr or "no stderr").split())
    try:
        name = json.loads(proc.stdout or "").get("nameWithOwner")
    except (ValueError, AttributeError):
        name = None
    if not isinstance(name, str) or not name:
        return None, "`gh repo view` returned no name"
    return name, ""


# ---- reporting ---------------------------------------------------------


def _print_plan(plan: Plan, *, board: str, cards: int, issues: int) -> None:
    print(f"{VERB}: {board}, its Status kept as the projection of each issue's state (DEC-006)")
    print(f"  read: {_cards(cards)} on the board, {issues} open issue(s) here")
    if plan.changes:
        print("\nThe cards whose Status differs from their issue's state, which wins (DEC-006):")
        for change in plan.changes:
            print(f"  #{change.number}: {change.was or 'no Status'} → {change.name}")
    if plan.adds:
        print("\nThe open issues with no card, to be added:")
        for add in plan.adds:
            print(f"  #{add.number}: → {add.name}")
    if plan.left:
        print("\nThe cards left as they are:")
        for number, why in plan.left:
            print(f"  #{number}: {why}")
    print(
        f"\nplan: {_cards(len(plan.changes))} to set, {_cards(len(plan.adds))} to add, "
        f"{_cards(plan.agree)} already right"
    )


def _cards(count: int) -> str:
    return f"{count} card" if count == 1 else f"{count} cards"


def _consent(*, yes: bool, prompt: str, rerun: str) -> int | None:
    """Ask before writing. None to proceed; otherwise the exit code to stop with.

    A run with no terminal cannot be asked, so without ``--yes`` it refuses and
    names the command that carries the consent."""
    if yes:
        return None
    if not sys.stdin.isatty():
        print(
            "error: refusing to write without consent: this run is not interactive. "
            f"Review the plan above, then run again with --yes:\n  {rerun}",
            file=sys.stderr,
        )
        return 2
    try:
        reply = input(prompt).strip().lower()
    except EOFError:
        reply = ""
    if reply in ("y", "yes"):
        return None
    print("aborted.", file=sys.stderr)
    return 0


def _rerun(args: argparse.Namespace) -> str:
    """The same invocation, carrying consent."""
    parts = ["pkit", "pm", VERB]
    if args.capability_root is not None:
        parts += ["--capability-root", str(args.capability_root)]
    if args.allow_foreign_repo:
        parts.append("--allow-foreign-repo")
    parts.append("--yes")
    return shlex.join(parts)


# ---- helpers -----------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Write the board's Status again from every issue's state, the projection "
            "DEC-006 has the agent maintain: only the cards that differ, a card added "
            "for each open issue that has none, and each card that disagreed named. "
            "The issue's state wins."
        ),
    )
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=(
            "Path to the installed capability's directory "
            f"(default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/)."
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the plan; write nothing.")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Write without the confirmation prompt. Required in a run with no terminal.",
    )
    session_guard.add_override_argument(parser)
    return parser


def _read_yaml(path: Path, yaml_loader: YAML) -> dict:
    if not path.is_file():
        return {}
    try:
        data = yaml_loader.load(path.read_text(encoding="utf-8"))
    except (OSError, YAMLError):
        return {}
    return data if isinstance(data, dict) else {}


def _read_members(capability_root: Path, yaml_loader: YAML) -> list[dict]:
    data = _read_yaml(capability_root / "project" / "members.yaml", yaml_loader)
    members = data.get("members") or []
    return members if isinstance(members, list) else []


if __name__ == "__main__":
    sys.exit(main())
