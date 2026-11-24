#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — sync-board (verb-subject per DEC-020).

Brings the configured board in line with the issues: it gives each open issue with
no card its card, in every project with a board, and keeps the board's Status where
the Status is the state's projection
([project-management:DEC-072-sync-gives-missing-cards]). `move-issue`, its cascade
and `create-issue` keep the board as they write; this command brings a whole board
level after a write that failed, an issue filed outside the capability, a card
removed, a card a person dragged by hand, or a board set up after the issues were
filed. It never guesses an issue's position.

What the board's Status is decides what it writes ([project-management:
DEC-062-axes-chosen-in-the-map] point 5, `_lib/board_status.role`):

  * **The state's projection,** where the state is carried off the board: with no
    substrate map, or where the map binds `state` elsewhere. It writes the Status
    from each issue's state on each card that differs, the issue's state winning
    (DEC-006), and adds a card for each open issue that has none, then sets its
    Status. A closed issue is Done; an open one is read as `_lib/lifecycle_inference`
    reads it: its state label, its milestone (Backlog) or neither (Todo).
  * **The state's source,** where the map binds `state` to the board. It adds a
    card for each open issue that has none, and writes no Status, on that card or
    any other: the issue's position stays undetermined until a person sets its
    card's Status on the board (DEC-051 point 6). Its plan and its report name each
    open issue whose card does not place it, as the state's reader sorts it from
    the walk of the board, and each whose only card is archived, which the board's
    views hide. A board's own automation may set a Status when a card is added,
    which every command would read as the issue's position. So it adds cards there
    only in a run at a terminal, or where the project's switch
    `sync_board.adds_with_no_terminal` is on (`_lib/sync_switch`), and reads each
    card it added back, naming each that shows a Status it did not write.
  * **Neither,** where a present map leaves `state` out or marks it `unsupported`:
    the state degrades. It adds a card for each open issue that has none, and
    writes no Status, which stays with the people who move it.

Where no board is configured, it refuses, whatever the map says. On a card it
adds it writes no other field: a field filing's hooks seed on a new card is the
corpus back-fill's to seed, which the report names.

What it reads: every card on the board, an archived card included, with its Status
where it reads one, and every open issue of this repository, through the
capability's one read of its issues (state issues are left out, DEC-058 point 3).
A card for another repository's issue, a pull request or a draft is left alone, and
so is a card the board withheld, whose issue lies in a repository the credential
may not read: the credential reads this repository, so no such card holds one of
its issues ([pkit:ADR-096] point 2). A card is added only where the board answers
with the issue's card (point 3).

Issues named after the command limit its writes, its plan and its report to them.
A named issue it has nothing to do for is listed with why: on the board already,
with nothing to write; a state issue; or not among the open issues it read, with
no card on the board, which does not tell a closed issue from a number no issue
holds. Such an issue changes no exit code.

`--dry-run` prints the plan and writes nothing. Otherwise the plan is printed and,
in a run at a terminal (standard input), consent is asked before the first write;
`--yes` skips the question, and a run with no terminal and no `--yes` refuses.
Where the board holds the state, a run with no terminal adds cards only with the
project's switch on, whatever option it passes. The membership gate (DEC-021) runs
at startup, and the foreign-repo guard (COR-039) before the first write.

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/sync-board.py --dry-run

Or via the dispatcher (per COR-021):
  pkit pm sync-board --dry-run
  pkit pm sync-board 12 14

Exit codes:
  0  written, nothing to write, a dry run, or declined at the prompt
  1  membership or foreign-repo refusal
  2  usage: no board configured, an un-bootstrapped project, or a run with no
     terminal and no --yes; where the board holds the state, a run with cards to
     add that is neither at a terminal nor has the project's switch on; a board
     with no single-select Status field, where the Status is the state's
     projection, or, where the board holds the state, where the run added no card
  3  gh failure: the repository, the issues or the board could not be read, or
     a Status or a card could not be written (the others are still written)
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import (
    axis_labels,
    board_answer,
    board_fields,
    board_status,
    bootstrap_gate,
    containment,
    hooks,
    session_guard,
    sync_switch,
)
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

#: Why a named issue gets nothing from the run (DEC-072 point 1).
NOTHING = "on the board already, with nothing to write"
STATE_ISSUE = "a state issue, which holds no work and takes no card (DEC-058 point 3)"
NOT_READ = (
    "not among this repository's open issues this run read, and no card on the board "
    "holds it: a closed issue, or a number no issue holds"
)

#: What the board's Status is to the run: the state's projection, its source, or
#: neither, where the state degrades.
PROJECTION = "projection"
SOURCE = "source"
DEGRADE = "degrade"


@dataclass(frozen=True)
class Write:
    """One card to set or add: the issue, the state it is in and the option that
    state takes, empty where the run writes no Status, the card (None for one
    still to add, by ``url``), and the option the card holds now (None for no
    Status)."""

    number: int
    state: str
    name: str
    item_id: str | None
    was: str | None = None
    url: str = ""


@dataclass(frozen=True)
class Plan:
    """What the run writes and reports: the cards whose Status differs, the open
    issues with no card, the cards left as they are with why, and how many cards
    already agree, or already hold their open issue where no Status is written.
    Where the board holds the state, also each open issue whose card does not
    place it, with the reader's words (``unplaced``); where no Status is written,
    each open issue whose only card is archived (``archived``); and each issue
    the run was named that it does nothing for, with why (``passed``)."""

    changes: tuple[Write, ...]
    adds: tuple[Write, ...]
    left: tuple[tuple[int, str], ...]
    agree: int
    unplaced: tuple[tuple[int, str], ...] = ()
    archived: tuple[int, ...] = ()
    passed: tuple[tuple[int, str], ...] = ()


@dataclass(frozen=True)
class Applied:
    """What a run wrote: the Status set, the cards added, each with its id, and
    the writes that failed."""

    written: int
    added: tuple[tuple[int, str], ...]
    failed: int


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
    role = _role(config, substrate_map)

    # The repository tells its cards from others', and its owner is the board's
    # where `gh.default_owner` is unset (`board_fields.board_owner`).
    repository, failure = _repository(config)
    if repository is None:
        print(f"error: this repository could not be read: {failure}", file=sys.stderr)
        return 3
    repository_owner = repository.split("/", 1)[0]
    workflow = _read_yaml(capability_root / "schemas" / "workflow.yaml", yaml_loader)
    status = board_status.StatusBoard(config, workflow, repository_owner=repository_owner)
    read = status.field()
    # Where the run writes no Status, a board that answered with no single-select
    # Status field does not stop the adds (DEC-072 point 1).
    fault: str | None = None
    if read.field is None:
        if role == PROJECTION or not read.answered or not read.project_id:
            print(f"error: the board's Status could not be read: {read.error}", file=sys.stderr)
            return 2 if read.named else 3
        if role == SOURCE:
            fault = read.error
    project_id = read.field.project_id if read.field is not None else str(read.project_id)
    # The owner the board was found under, else the repository's, under which
    # each later read resolves the board's as the first read did.
    owner = (read.field.owner if read.field is not None else None) or repository_owner
    if role == PROJECTION and read.field is not None:
        for name in board_status.missing_options(read.field, workflow):
            print(
                f"[warn] the board's Status field has no option for {name}: add it to the "
                "field on the board, then run sync-board again",
                file=sys.stderr,
            )

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
    # The Status is read from the walk where the run writes it, and where the
    # board holds the state, for the position of each open issue it reports.
    reads_status = read.field is not None and role != DEGRADE
    cards = board_fields.read_items(
        config,
        project_node_id=project_id,
        field_name=read.field.name if reads_status and read.field is not None else None,
        owner=owner,
    )
    if not cards.ok:
        print(f"error: the board's cards could not be read: {cards.error}", file=sys.stderr)
        return 3

    named = frozenset(args.issues) if args.issues else None
    state_issues = corpus.state_issues | {
        card.number
        for card in cards.set_aside
        if card.number is not None and card.repository.lower() == repository.lower()
    }
    if role == PROJECTION:
        assert read.field is not None
        plan = plan_sync(
            cards.items,
            corpus.rows,
            repository=repository,
            field=read.field,
            workflow=workflow,
            substrate_map=substrate_map,
            named=named,
            state_issues=state_issues,
        )
    else:
        plan = plan_adds(
            cards.items,
            corpus.rows,
            repository=repository,
            workflow=workflow,
            board=status.board,
            named=named,
            state_issues=state_issues,
            holds_state=role == SOURCE,
            positions=role == SOURCE and read.field is not None,
        )
    _print_plan(
        plan,
        role=role,
        board=status.board,
        cards=len(cards.items),
        issues=len(corpus.rows),
        fault=fault,
        named=named,
    )
    # Where the board holds the state and has no Status field, a run that adds no
    # card takes the code that board takes where the Status is the projection.
    none_added = 2 if fault is not None else 0

    if args.dry_run:
        if role == SOURCE and plan.adds:
            print(
                f"\n[dry-run] {_cards(len(plan.adds))} to add would need a run at a terminal, "
                f"or the project's switch `{sync_switch.NAME}` on."
            )
        print("\n[dry-run] nothing written.")
        return none_added
    if not plan.changes and not plan.adds:
        print(f"\n{_nothing_to_write(role)}")
        return none_added

    # Foreign-repo mutation guard (COR-039 / ADR-034): everything above only
    # read; this is the first write.
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1
    interactive = sys.stdin.isatty()
    if role == SOURCE and not interactive:
        switch = sync_switch.read(config, capability_root)
        if not switch.on:
            _refuse_adds(args, switch)
            return 2
        print(f"\nswitch: {switch.said}, so a run with no terminal adds the cards above.")
    count = len(plan.changes) + len(plan.adds)
    stop = _consent(
        yes=args.yes,
        interactive=interactive,
        prompt=f"Write {_cards(count)}? [y/N] ",
        rerun=_rerun(args, yes=True),
    )
    if stop is not None:
        return none_added if stop == 0 else stop

    applied = _apply(plan, status, config, writes_status=role == PROJECTION)
    if role == SOURCE and applied.added and read.field is not None:
        _read_back(applied.added, config, project_id=project_id, field=read.field, owner=owner)
    if applied.added and hooks.seeds_board_field(capability_root):
        _name_back_fill()
    if applied.failed:
        return 3
    return 0 if applied.added or applied.written else none_added


def _role(config: dict, substrate_map: axis_labels.SubstrateMap | None) -> str:
    """What the board's Status is to this run, where a board is configured: the
    state's projection, its source, or neither, where the state degrades
    ([project-management:DEC-062-axes-chosen-in-the-map] point 5)."""
    role = board_status.role(config, substrate_map)
    return role if role is not None else DEGRADE


# ---- the plan ----------------------------------------------------------


def plan_sync(
    cards: tuple[board_fields.BoardItem, ...],
    rows: tuple[Any, ...],
    *,
    repository: str,
    field: board_status.StatusField,
    workflow: dict,
    substrate_map: axis_labels.SubstrateMap | None,
    named: frozenset[int] | None = None,
    state_issues: frozenset[int] | set[int] = frozenset(),
) -> Plan:
    """Compare each of this repository's cards with its issue's state, where the
    Status is the state's projection.

    A closed issue is Done. An open one is read from its row of the open issues,
    and one with no row was not read, so its card is left as it is. Pull
    requests, drafts and other repositories' issues are not this command's.
    Where ``named`` names issues, only theirs are planned, and each named issue
    the plan does nothing for is passed, with why."""
    open_rows = _open_rows(rows)
    own = _own_cards(cards, repository)
    changes: list[Write] = []
    left: list[tuple[int, str]] = []
    agree = 0
    for number, held in sorted(own.items()):
        if named is not None and number not in named:
            continue
        for card in held:
            if card.closed:
                state = "done"
            elif number in open_rows:
                state = _state_of(open_rows[number], substrate_map)
            else:
                left.append((number, "its state was not read"))
                continue
            target = _target(state, field, workflow)
            if isinstance(target, _Unplaced):
                left.append((number, target.why))
            elif card.option_id == target.option:
                agree += 1
            else:
                changes.append(Write(number, state, target.name, card.item_id, card.option_name))
    adds: list[Write] = []
    for number in _missing(open_rows, own, named):
        state = _state_of(open_rows[number], substrate_map)
        target = _target(state, field, workflow)
        if isinstance(target, _Unplaced):
            left.append((number, f"no card, and {target.why}"))
        else:
            url = str(open_rows[number].get("url") or "")
            adds.append(Write(number, state, target.name, None, url=url))
    passed = _passed(
        named,
        acted={w.number for w in changes} | {w.number for w in adds} | {n for n, _ in left},
        own=own,
        state_issues=state_issues,
    )
    return Plan(tuple(changes), tuple(adds), tuple(left), agree, passed=passed)


def plan_adds(
    cards: tuple[board_fields.BoardItem, ...],
    rows: tuple[Any, ...],
    *,
    repository: str,
    workflow: dict,
    board: str,
    named: frozenset[int] | None = None,
    state_issues: frozenset[int] | set[int] = frozenset(),
    holds_state: bool,
    positions: bool,
) -> Plan:
    """The cards to add where the run writes no Status: the board holds the state
    (``holds_state``), or the state degrades.

    Each open issue of this repository with no card is added, and every other is
    left as it is. Where ``positions`` is set, the board holds the state and the
    walk read each card's Status, so each open issue whose card does not place it
    is named, as the state's reader sorts it (`board_status.reading`, ADR-074
    point 2), with no classifier of the sync's own. Each open issue whose only
    card is archived is named where the board holds the state, and, where the
    state degrades, where the run names it. Where ``named`` names issues, only
    theirs are planned, and each named issue the plan does nothing for is
    passed, with why."""
    open_rows = _open_rows(rows)
    own = _own_cards(cards, repository)
    unplaced: list[tuple[int, str]] = []
    archived: list[int] = []
    carded = 0
    for number, held in sorted(own.items()):
        if number not in open_rows or (named is not None and number not in named):
            continue
        carded += 1
        if all(card.archived for card in held) and (holds_state or named is not None):
            archived.append(number)
        if not positions:
            continue
        reading = _position(held, workflow, board)
        if reading.outcome != "placed":
            unplaced.append((number, reading.finding(number)))
    adds = tuple(
        Write(number, "", "", None, url=str(open_rows[number].get("url") or ""))
        for number in _missing(open_rows, own, named)
    )
    passed = _passed(
        named,
        acted={w.number for w in adds} | {n for n, _ in unplaced} | set(archived),
        own=own,
        state_issues=state_issues,
    )
    return Plan((), adds, (), carded, tuple(unplaced), tuple(archived), passed)


def _position(held: list[board_fields.BoardItem], workflow: dict, board: str) -> infer.StatusRead:
    """Where an open issue's cards place it: the first card whose Status places
    it, else the first card's reading, by the state's reader."""
    readings = [board_status.reading(workflow, card.option_name, board=board) for card in held]
    return next((r for r in readings if r.outcome == "placed"), readings[0])


def _open_rows(rows: tuple[Any, ...]) -> dict[int, dict]:
    return {row["number"]: row for row in rows if isinstance(row.get("number"), int)}


def _own_cards(
    cards: tuple[board_fields.BoardItem, ...], repository: str
) -> dict[int, list[board_fields.BoardItem]]:
    """This repository's issues' cards, by issue number. Pull requests, drafts and
    other repositories' issues are not this command's."""
    own: dict[int, list[board_fields.BoardItem]] = {}
    for card in cards:
        if card.kind != "Issue" or card.number is None:
            continue
        if card.repository.lower() != repository.lower():
            continue
        own.setdefault(card.number, []).append(card)
    return own


def _missing(
    open_rows: dict[int, dict], own: dict[int, list[Any]], named: frozenset[int] | None
) -> list[int]:
    """The open issues with no card on the board, those named where any are."""
    return sorted(
        number for number in set(open_rows) - set(own) if named is None or number in named
    )


def _passed(
    named: frozenset[int] | None,
    *,
    acted: set[int],
    own: dict[int, list[Any]],
    state_issues: frozenset[int] | set[int],
) -> tuple[tuple[int, str], ...]:
    """Each named issue the plan neither acts on nor lists, with why."""
    if named is None:
        return ()
    passed: list[tuple[int, str]] = []
    for number in sorted(named - acted):
        if number in state_issues:
            passed.append((number, STATE_ISSUE))
        elif number in own:
            passed.append((number, NOTHING))
        else:
            passed.append((number, NOT_READ))
    return tuple(passed)


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


def _apply(
    plan: Plan, status: board_status.StatusBoard, config: dict, *, writes_status: bool
) -> Applied:
    """Write the plan: the cards that differ, then the cards to add, each added
    card's Status set where ``writes_status``. Each failure is one line, with the
    board's words, and the rest are still written."""
    print()
    written = failed = 0
    added: list[tuple[int, str]] = []
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
        added.append((add.number, item_id))
        if not writes_status:
            print(f"  [board] #{add.number}: card added, with no Status")
            continue
        result = status.write(add.number, add.state, item_id=item_id)
        if result.ok:
            written += 1
            print(f"  {result.line()}")
        else:
            failed += 1
            print(
                f"  [fail] #{add.number}: its card was added, its Status not set: {result.failure}"
            )
    status_set = f"{written} Status set, " if writes_status else ""
    print(f"done: {status_set}{_cards(len(added))} added, {failed} failed")
    return Applied(written, tuple(added), failed)


def _read_back(
    added: Iterable[tuple[int, str]],
    config: dict,
    *,
    project_id: str,
    field: board_status.StatusField,
    owner: str | None,
) -> None:
    """Read each card the run added again, by the card the add answered with,
    through the board read seam, and say what each shows (DEC-072 point 3). It
    names a Status it finds as one the sync did not write, claims nothing of who
    set it, and suggests clearing none. It is a note on the act: what it finds,
    or fails to read, changes no exit code."""
    print(
        "\nRead back, each card added, for a Status the sync did not write, such as one "
        "the board's own automation set when the card was added:"
    )
    for number, item_id in added:
        card = board_fields.read_card(
            config, item_id=item_id, project_node_id=project_id, field_name=field.name, owner=owner
        )
        if not card.ok:
            print(f"  #{number}: the board did not answer the read of its card: {card.error}")
        elif not card.found:
            print(f"  #{number}: its card was not found when read again, so it is not confirmed")
        elif card.option_name is not None:
            print(
                f"  #{number}: its card shows the Status {card.option_name!r}, which the sync "
                "did not write, and every command now reads it as the issue's position: check "
                "it on the board"
            )
        else:
            print(
                f"  #{number}: its card showed no Status when read, and the board's automation "
                "may set one later"
            )
    print(
        "  The read sees only what the board had set when it read, so check each card added "
        "on the board, and set its Status to where the issue stands."
    )


def _name_back_fill() -> None:
    """Name the corpus back-fill as the way to seed a board field filing's hooks
    seed on a new card, which a card the sync adds does not get (DEC-072 points 2
    and 4)."""
    print(
        "\nThe project's hooks seed a board field on a card filing adds, and the sync "
        "writes no other field on a card it adds: `pkit pm back-fill` seeds it. The "
        "back-fill reads each such hook as an intent for the whole corpus, so it seeds "
        "the field on every issue that lacks it, not only on the cards this run added "
        "(DEC-037 point 2)."
    )


def _add_card(url: str, config: dict) -> tuple[str | None, str]:
    """Add the issue at ``url`` to the configured board: its card's id, or None
    and why. Board membership (DEC-019), which ADR-031 point 3 names out of the
    substrate writes, so it is constructed here, as `create-issue` does: on the
    board of `gh.default_owner`, else of the issue's owner, the repository's. It
    is made only where the board answers with the issue's card
    (`board_answer.added_card`, [pkit:ADR-096] point 3)."""
    number = board_fields.board_number(config)
    owner = board_fields.url_owner(url)
    cmd = ["gh", "project", "item-add", str(number), "--url", url, "--format", "json"]
    try:
        proc = gh_project_run(cmd, config, fallback_owner=owner, check=False)
    except FileNotFoundError:
        return None, "`gh` is not on PATH"
    if proc.returncode != 0:
        return None, " ".join((proc.stderr or "no stderr").split())
    return board_answer.added_card(proc.stdout, url)


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


def _print_plan(
    plan: Plan,
    *,
    role: str,
    board: str,
    cards: int,
    issues: int,
    fault: str | None,
    named: frozenset[int] | None,
) -> None:
    print(f"{VERB}: {board}, {_what_it_writes(role)}")
    scope = f", {_issues(len(named))} named" if named is not None else ""
    print(f"  read: {_cards(cards)} on the board, {issues} open issue(s) here{scope}")
    if plan.changes:
        print("\nThe cards whose Status differs from their issue's state, which wins (DEC-006):")
        for change in plan.changes:
            print(f"  #{change.number}: {change.was or 'no Status'} → {change.name}")
    if plan.adds:
        print("\nThe open issues with no card, to be added:")
        for add in plan.adds:
            print(f"  #{add.number}: → {add.name}" if add.name else f"  #{add.number}")
        if role != PROJECTION:
            print(
                "  The sync writes no Status on a card it adds, and the board's own "
                "automation may set one when the card is added."
            )
        if role == SOURCE:
            print(
                "  Each added issue's position stays undetermined until a person sets its "
                "card's Status on the board, and every command would read a Status the "
                "automation set as the issue's position (DEC-051 point 6)."
            )
    if plan.left:
        print("\nThe cards left as they are:")
        for number, why in plan.left:
            print(f"  #{number}: {why}")
    if fault is not None:
        print(
            f"\n[warn] the board can place no issue: {fault}. It holds the state, so its "
            "position cannot be read until the board has one (ADR-074 point 1): give the "
            f"board a single-select `{board_status.STATUS_FIELD}` field, with the five "
            "states as its options."
        )
    elif plan.unplaced:
        print(
            "\nThe open issues whose card does not place them, each undetermined until a "
            "person sets its card's Status on the board (DEC-051 point 6):"
        )
        for _number, finding in plan.unplaced:
            print(f"  {finding}")
    if plan.archived:
        print("\nThe open issues whose only card is archived, which the board's views hide:")
        for number in plan.archived:
            print(f"  #{number}: restore its card on the board to see it there")
    if plan.passed:
        print("\nThe issues named that this run does nothing for:")
        for number, why in plan.passed:
            print(f"  #{number}: {why}")
    if role == PROJECTION:
        print(
            f"\nplan: {_cards(len(plan.changes))} to set, {_cards(len(plan.adds))} to add, "
            f"{_cards(plan.agree)} already right"
        )
    else:
        print(
            f"\nplan: {_cards(len(plan.adds))} to add, {_issues(plan.agree)} already on the board"
        )


def _what_it_writes(role: str) -> str:
    """What the run writes on the board, as its first line says it."""
    if role == PROJECTION:
        return "its Status kept as the projection of each issue's state (DEC-006)"
    if role == SOURCE:
        return (
            "which holds the state: it gives each open issue its card, and writes no "
            "Status (DEC-072)"
        )
    return (
        "where the state degrades: it gives each open issue its card, and writes no "
        "Status, which stays with the people who move it (DEC-072)"
    )


def _nothing_to_write(role: str) -> str:
    if role == PROJECTION:
        return "every card's Status matches its issue's state; nothing to write."
    return "every open issue has its card; nothing to write."


def _refuse_adds(args: argparse.Namespace, switch: sync_switch.Switch) -> None:
    """Refuse the adds of a run with no terminal where the board holds the state,
    the switch off, with the command to run at a terminal (DEC-072 point 3)."""
    print(
        "error: refusing to add cards: the board holds the state, and a card the sync "
        "adds there is added only in a run at a terminal, or with the project's switch "
        f"`{sync_switch.NAME}` on, whatever option the run passes. This run has no "
        f"terminal, and the switch is off: {switch.said}. Nothing was written. Review the "
        f"plan above, then run this at a terminal:\n  {_rerun(args, yes=False)}",
        file=sys.stderr,
    )


def _cards(count: int) -> str:
    return f"{count} card" if count == 1 else f"{count} cards"


def _issues(count: int) -> str:
    return f"{count} issue" if count == 1 else f"{count} issues"


def _consent(*, yes: bool, interactive: bool, prompt: str, rerun: str) -> int | None:
    """Ask before writing, only in a run at a terminal. None to proceed;
    otherwise the exit code to stop with.

    A run with no terminal cannot be asked, so without ``--yes`` it refuses and
    names the command that carries the consent."""
    if yes:
        return None
    if not interactive:
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


def _rerun(args: argparse.Namespace, *, yes: bool) -> str:
    """The same invocation, carrying consent where ``yes``."""
    parts = ["pkit", "pm", VERB, *(str(number) for number in args.issues)]
    if args.capability_root is not None:
        parts += ["--capability-root", str(args.capability_root)]
    if args.allow_foreign_repo:
        parts.append("--allow-foreign-repo")
    if yes:
        parts.append("--yes")
    return shlex.join(parts)


# ---- helpers -----------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Bring the configured board in line with the issues: give each open issue "
            "with no card its card, wherever a board is configured, and, where the "
            "board's Status is the projection of each issue's state, write the Status on "
            "each card that differs (the issue's state wins, DEC-006). Where the board "
            "holds the state, or the state degrades, it writes no Status: where the board "
            "holds it, each added issue's position stays undetermined until a person sets "
            "its card's Status on the board, and a run with no terminal adds cards only "
            f"with the project's switch `{sync_switch.NAME}` on, whatever option it "
            "passes (DEC-072)."
        ),
    )
    parser.add_argument(
        "issues",
        nargs="*",
        type=_issue_number,
        metavar="ISSUE",
        help=(
            "Issue numbers to limit the run's writes, plan and report to. A named issue "
            "the run does nothing for is listed with why."
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
        help=(
            "Write without the confirmation question. Required in a run with no terminal. "
            "Where the board holds the state, a run with no terminal adds cards only with "
            f"the project's switch `{sync_switch.NAME}` on, whatever option it passes: "
            "this option is no consent to the board's own automation setting a Status on "
            "a card the sync adds."
        ),
    )
    session_guard.add_override_argument(parser)
    return parser


def _issue_number(text: str) -> int:
    try:
        number = int(text.lstrip("#"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{text!r} is not an issue number") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError(f"{text!r} is not an issue number")
    return number


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
