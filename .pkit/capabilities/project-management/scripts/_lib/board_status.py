"""The board's Status: the state's source, or the state's projection (DEC-006, DEC-062).

Which it is, the substrate map decides
([project-management:DEC-062-axes-chosen-in-the-map] point 5):

* **The source**, where the map binds `state` to the board (`board: true`). An
  open issue stands where its card's Status places it, and a closed issue is
  Done whatever its card says. A move writes the Status, and so do the forward
  cascade and `create-issue`'s first Status: the write IS the move.
* **The projection**, where a board is configured and the map carries the state
  off it: with no map, or where the map binds `state` to another substrate.
  [project-management:DEC-006-state-machine-and-cascade]: "its Status field is a
  projection the agent maintains. When the board and native primitives disagree,
  native wins." The same writers write it, and `sync-board` writes it again.
* **Neither**, where a present map leaves `state` out or marks it `unsupported`:
  the state degrades, and nothing here writes a Status, so the board's Status
  stays with the people who move it.

:func:`role` answers with no I/O, so a project with no board, or one whose state
degrades, makes no `gh` call for it ([pkit:ADR-053] point 3).

Reading a board-carried state
-----------------------------
[project-management:DEC-051-axis-carriage-activation] point 6. :class:`StatusBoard`
reads one issue's card at a time, for a command that moves or checks one issue;
:func:`read_snapshot` reads every card's Status once, for a command that lists,
joined to the one read of issues by the issue's node id. A board read in part is
never taken for the whole. Each read comes out as a
`lifecycle_inference.StatusRead`, one of four outcomes beside a placed one: the
board could not be read, no card, no Status, a Status naming no open state. What
each means is the command's, never this module's: `lifecycle_inference` places
none of them, and nothing falls back to the labels or the milestone.

The three layers
----------------
ADR-053's, in its order. Carriage is asked first and cannot fail. The board read
seam, `_lib/board_fields`, gives the project, the Status field and the issue's
card, the board found under its owner (`board_fields.board_owner`). The write
goes through ADR-031's sole constructor, `substrate_writes.write_field_value`.
What a failure means is the caller's: a write that cannot be made comes back as
one line, never an error.

The option a state takes is its display name in workflow.yaml (`Todo`,
`Backlog`, `In Progress`, `Review`, `Done`), matched against the Status options
exactly first, then case-insensitively (`board_fields.option_id`); an option is
read back to the state whose display name it bears, matched the same way.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from _lib import axis_carriage, axis_labels, board_fields, substrate_writes
from _lib import lifecycle_inference as infer
from _lib.gh import gh_run

#: The single-select field the state is read from and written to, Projects v2's own.
STATUS_FIELD = "Status"

#: What the board's Status is to a project: the state's source, its projection,
#: or nothing the capability writes.
Role = Literal["source", "projection"]


def role(config: dict[str, Any], substrate_map: axis_labels.SubstrateMap | None) -> Role | None:
    """What the board's Status is to this project (DEC-062 point 5). No I/O.

    ``source`` where the map binds state to the board; ``projection`` where a
    board is configured and the state is carried off it; None where no board is
    configured, or where a present map omits state or marks it `unsupported`."""
    carried = axis_carriage.carriage("state", config, substrate_map)
    if carried == "board":
        return "source"
    if board_fields.board_number(config) is None or carried == "degrade":
        return None
    return "projection"


def maintained(config: dict[str, Any], substrate_map: axis_labels.SubstrateMap | None) -> bool:
    """Whether the board's Status is a projection this project keeps: a board is
    configured, and the state is carried off it — with no map, or where the map
    binds state to a substrate other than the board. Where a present map omits
    state or marks it `unsupported`, the state degrades and no Status is written,
    so the board's Status stays with the people who move it
    ([project-management:DEC-062-axes-chosen-in-the-map] point 5). No I/O."""
    return role(config, substrate_map) == "projection"


def option_name(workflow: dict, state: str) -> str | None:
    """The Status option ``state`` takes: its display name, for each of the five
    states, and None for a state outside them, such as the `open` a `derive`
    binding reads."""
    if state not in infer.STATE_ORDER:
        return None
    return infer.state_display_name(workflow, state)


def state_of_option(workflow: dict, name: str) -> str | None:
    """The state whose display name the Status option ``name`` bears, matched
    exactly first, then case-insensitively, as an option is matched to a state
    on a write; None for an option that names none of the five states."""
    names = {state: option_name(workflow, state) for state in infer.STATE_ORDER}
    for state, display in names.items():
        if display == name:
            return state
    lowered = name.lower()
    for state, display in names.items():
        if display is not None and display.lower() == lowered:
            return state
    return None


def reading(workflow: dict, option: str | None, *, board: str) -> infer.StatusRead:
    """What a card holding ``option`` in its Status says of an open issue: the
    open state it names, no Status, or a Status naming no open state."""
    if option is None:
        return infer.StatusRead("unset", board=board)
    state = state_of_option(workflow, option)
    if state in infer.OPEN_STATES:
        return infer.StatusRead("placed", state=state, said=option, board=board)
    return infer.StatusRead("not-open", said=option, board=board)


@dataclass(frozen=True)
class StatusField:
    """The board's Status field as one run reads it: the project it belongs to,
    and the field with its options, as `board_fields.read_fields` gives it."""

    project_id: str
    field: dict[str, Any]

    @property
    def field_id(self) -> str:
        return str(self.field.get("id") or "")

    @property
    def name(self) -> str:
        """The field's own name on the board, by which its value is read."""
        return str(self.field.get("name") or STATUS_FIELD)


@dataclass(frozen=True)
class FieldRead:
    """The Status field, or why it could not be read, on one line. ``answered``
    tells a board that answered with no single-select Status field from one that
    did not answer."""

    field: StatusField | None
    error: str | None = None
    answered: bool = False


def read_status_field(config: dict[str, Any], *, repository_owner: str | None = None) -> FieldRead:
    """Read the project and its Status field, through the board read seam, under
    the board's owner as `board_fields.board_owner` resolves it.

    ``repository_owner`` is the repository's owner where the caller holds it, by
    which the board is found where `gh.default_owner` is unset."""
    owner = board_fields.board_owner(config, repository_owner=repository_owner)
    project = board_fields.read_project_node_id(config, owner=owner)
    if not project.ok or not project.node_id:
        return FieldRead(None, _one_line(project.error or "the board resolved to no project"))
    fields = board_fields.read_fields(config, owner=owner)
    if not fields.ok:
        return FieldRead(None, _one_line(fields.error or "the board's fields could not be read"))
    found = board_fields.find_field(fields.fields, STATUS_FIELD)
    if found is None:
        names = ", ".join(board_fields.field_names(fields.fields)) or "none"
        return FieldRead(
            None, f"the board has no `{STATUS_FIELD}` field (its fields: {names})", answered=True
        )
    if not board_fields.is_single_select(found):
        return FieldRead(
            None,
            f"the board's `{STATUS_FIELD}` field is a {board_fields.field_type(found)}, "
            "not a single-select",
            answered=True,
        )
    return FieldRead(StatusField(project.node_id, found))


def missing_options(status_field: StatusField, workflow: dict) -> list[str]:
    """The options of the five states the Status field does not offer, in the
    lifecycle's order."""
    names = (option_name(workflow, state) for state in infer.STATE_ORDER)
    return [
        name for name in names if name and board_fields.option_id(status_field.field, name) is None
    ]


def board_name(config: dict[str, Any]) -> str:
    """The board as a line names it: `board #4`."""
    return f"board #{board_fields.board_number(config)}"


@dataclass(frozen=True)
class Written:
    """What became of one Status write: written, or why not, on one line."""

    number: int
    name: str | None
    failure: str | None = None

    @property
    def ok(self) -> bool:
        return self.failure is None

    def line(self) -> str:
        """The write as the commands print it: done, or not done and why."""
        if self.ok:
            return f"[board] #{self.number}: Status set to {self.name!r}"
        meant = f" to {self.name!r}" if self.name else ""
        return f"[warn] #{self.number}: the board's Status was not set{meant}: {self.failure}"


def report(written: Written, *, stands: str = "the move stands") -> None:
    """Print a projection's write as the lifecycle commands do: one line on
    standard output where it was made, and one on standard error where it was
    not, saying what ``stands`` all the same and what sets the Status later."""
    if written.ok:
        print(written.line())
    else:
        print(f"{written.line()}; {stands}, and `sync-board` sets it", file=sys.stderr)


class StatusBoard:
    """Reads and writes the Status of one card at a time, reading the board's ids
    once a run.

    ``config`` names the board, as `board_fields` reads it. The project and its
    Status field are read at the first read or write and kept for the run, so a
    move and its cascade read them once. ``repository_owner`` is the repository's
    owner where the caller holds it, as :func:`read_status_field` takes it."""

    def __init__(
        self, config: dict[str, Any], workflow: dict, *, repository_owner: str | None = None
    ) -> None:
        self._config = config
        self._workflow = workflow
        self._repository_owner = repository_owner
        self._field: FieldRead | None = None

    @property
    def board(self) -> str:
        return board_name(self._config)

    def field(self) -> FieldRead:
        """The Status field, read once."""
        if self._field is None:
            self._field = read_status_field(self._config, repository_owner=self._repository_owner)
        return self._field

    def read(self, number: int, *, issue_node_id: str | None = None) -> infer.StatusRead:
        """Where issue ``number``'s card's Status places it, an open issue, as one
        of the outcomes `lifecycle_inference.StatusRead` names (DEC-051 point 6).

        ``issue_node_id`` is the issue's node id, where the caller holds it;
        otherwise it is read. Nothing is raised: a read that fails is the
        `unreadable` outcome, with what was said."""
        read = self.field()
        if read.field is None:
            return infer.StatusRead("unreadable", said=read.error or "", board=self.board)
        if issue_node_id is None:
            issue_node_id, failure = _issue_node_id(number, self._config)
            if issue_node_id is None:
                return infer.StatusRead("unreadable", said=failure, board=self.board)
        card = board_fields.read_item_value(
            self._config,
            issue_node_id=issue_node_id,
            project_node_id=read.field.project_id,
            field_name=read.field.name,
        )
        if not card.ok:
            said = _one_line(card.error or "the card could not be read")
            return infer.StatusRead("unreadable", said=said, board=self.board)
        if card.item_id is None:
            return infer.StatusRead("no-card", board=self.board)
        return reading(self._workflow, card.option_name, board=self.board)

    def write(self, number: int, state: str, *, item_id: str | None = None) -> Written:
        """Set issue ``number``'s card to the option ``state`` takes.

        ``item_id`` is the card, where the caller holds it; otherwise it is looked
        up from the issue. Nothing is raised: a write that cannot be made says
        why."""
        name = option_name(self._workflow, state)
        if name is None:
            return Written(number, None, f"the state {state!r} has no Status option")
        read = self.field()
        if read.field is None:
            return Written(number, name, read.error)
        option = board_fields.option_id(read.field.field, name)
        if option is None:
            return Written(number, name, f"the board's Status field has no {name!r} option")
        if item_id is None:
            item_id, failure = self._card(number, read.field.project_id)
            if item_id is None:
                return Written(number, name, failure)
        result = substrate_writes.write_field_value(
            self._config,
            item_id=item_id,
            field_id=read.field.field_id,
            project_id=read.field.project_id,
            single_select_option_id=option,
        )
        return Written(number, name, None if result.ok else _one_line(result.detail))

    def _card(self, number: int, project_id: str) -> tuple[str | None, str]:
        """Issue ``number``'s card on the board, or None and why not."""
        node_id, failure = _issue_node_id(number, self._config)
        if node_id is None:
            return None, failure
        lookup = board_fields.resolve_item_id(
            self._config, issue_node_id=node_id, project_node_id=project_id
        )
        if not lookup.ok:
            return None, _one_line(lookup.error or "the card could not be looked up")
        if lookup.item_id is None:
            return None, f"#{number} has no card on {self.board}"
        return lookup.item_id, ""


@dataclass(frozen=True)
class Snapshot:
    """Every card's Status on the board, read once, by the node id of the issue
    each card holds: the read a listing joins to its one read of issues.

    ``options`` maps an issue's node id to the option its card holds, None for a
    card with no Status. An issue the map does not hold has no card."""

    board: str
    workflow: Mapping[str, Any]
    options: Mapping[str, str | None] = field(default_factory=dict)

    def read(self, issue_node_id: str | None) -> infer.StatusRead:
        """Where the card of the issue with node id ``issue_node_id`` places it,
        an open issue: as :meth:`StatusBoard.read` would, from the one read."""
        if not issue_node_id or issue_node_id not in self.options:
            return infer.StatusRead("no-card", board=self.board)
        return reading(dict(self.workflow), self.options[issue_node_id], board=self.board)


def read_snapshot(
    config: dict[str, Any], workflow: dict, *, repository_owner: str | None = None
) -> tuple[Snapshot | None, str]:
    """Every card's Status on the board, in one paginated read of its cards, or
    None and why the board could not be read. The whole board or nothing: a
    board read in part is never returned as the whole (`board_fields.read_items`)."""
    read = read_status_field(config, repository_owner=repository_owner)
    if read.field is None:
        return None, read.error or "the board's Status could not be read"
    cards = board_fields.read_items(
        config, project_node_id=read.field.project_id, field_name=read.field.name
    )
    if not cards.ok:
        return None, _one_line(cards.error or "the board's cards could not be read")
    options = {card.issue_id: card.option_name for card in cards.items if card.issue_id}
    return Snapshot(board_name(config), workflow, options), ""


def _issue_node_id(number: int, config: dict[str, Any]) -> tuple[str | None, str]:
    """The issue's GraphQL node id, by which its card is looked up, or None and why."""
    try:
        proc = gh_run(["gh", "issue", "view", str(number), "--json", "id"], config, check=False)
    except FileNotFoundError:
        return None, "`gh` is not on PATH"
    if proc.returncode != 0:
        said = _one_line(proc.stderr or "")
        return None, f"`gh issue view {number}` failed" + (f": {said}" if said else "")
    try:
        payload = json.loads(proc.stdout or "")
    except ValueError:
        payload = None
    node_id = payload.get("id") if isinstance(payload, dict) else None
    if not isinstance(node_id, str) or not node_id:
        return None, f"`gh issue view {number}` returned no node id"
    return node_id, ""


def _one_line(text: str) -> str:
    """``text`` on one line, as `gh` said it."""
    return " ".join(text.split())
