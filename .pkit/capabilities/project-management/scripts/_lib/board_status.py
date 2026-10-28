"""The board's Status, kept as the projection of each issue's state (DEC-006).

[project-management:DEC-006-state-machine-and-cascade]: "When a Projects v2
board exists, its Status field is a projection the agent maintains. When the
board and native primitives disagree, native wins." This module writes that
projection for every writer of it: `move-issue`, and so each wrapper over it,
the forward cascade, `create-issue` and `sync-board`.

Where it applies
----------------
Where a board is configured, `board_fields.board_number`, and the issue's state
is not carried on it, `axis_carriage.is_board_carried`. Where the board carries
the state, its Status is the state's source rather than a projection, and
nothing here writes it. :func:`maintained` answers with no I/O, so a project with
no board, or one whose board carries the state, makes no `gh` call for it
([pkit:ADR-053] point 3).

The three layers
----------------
ADR-053's, in its order. Carriage is asked first and cannot fail. The board read
seam, `_lib/board_fields`, gives the project, the Status field and the issue's
card, the board found under its owner (`board_fields.board_owner`). The write
goes through ADR-031's sole constructor, `substrate_writes.write_field_value`.
What a failure means is the caller's: a write that cannot be made comes back as
one line, never an error, since the native state is the source and `sync-board`
writes the projection again.

The option a state takes is its display name in workflow.yaml (`Todo`,
`Backlog`, `In Progress`, `Review`, `Done`), matched against the Status
options exactly first, then case-insensitively (`board_fields.option_id`).
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any

from _lib import axis_carriage, axis_labels, board_fields, substrate_writes
from _lib import lifecycle_inference as infer
from _lib.gh import gh_run

#: The single-select field the projection is written to, Projects v2's own.
STATUS_FIELD = "Status"


def maintained(config: dict[str, Any], substrate_map: axis_labels.SubstrateMap | None) -> bool:
    """Whether the board's Status is a projection this project keeps: a board is
    configured, and the state is not carried on it. No I/O."""
    return board_fields.board_number(config) is not None and not axis_carriage.is_board_carried(
        "state", config, substrate_map
    )


def option_name(workflow: dict, state: str) -> str | None:
    """The Status option ``state`` takes: its display name, for each of the five
    states, and None for a state outside them, such as the `open` a `derive`
    binding reads."""
    if state not in infer.STATE_ORDER:
        return None
    return infer.state_display_name(workflow, state)


@dataclass(frozen=True)
class StatusField:
    """The board's Status field as one run reads it: the project it belongs to,
    and the field with its options, as `board_fields.read_fields` gives it."""

    project_id: str
    field: dict[str, Any]

    @property
    def field_id(self) -> str:
        return str(self.field.get("id") or "")


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
    field = board_fields.find_field(fields.fields, STATUS_FIELD)
    if field is None:
        names = ", ".join(board_fields.field_names(fields.fields)) or "none"
        return FieldRead(
            None, f"the board has no `{STATUS_FIELD}` field (its fields: {names})", answered=True
        )
    if not board_fields.is_single_select(field):
        return FieldRead(
            None,
            f"the board's `{STATUS_FIELD}` field is a {board_fields.field_type(field)}, "
            "not a single-select",
            answered=True,
        )
    return FieldRead(StatusField(project.node_id, field))


def missing_options(field: StatusField, workflow: dict) -> list[str]:
    """The options of the five states the Status field does not offer, in the
    lifecycle's order."""
    names = (option_name(workflow, state) for state in infer.STATE_ORDER)
    return [name for name in names if name and board_fields.option_id(field.field, name) is None]


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
    """Print a write as the lifecycle commands do: one line on standard output
    where it was made, and one on standard error where it was not, saying what
    ``stands`` all the same and what sets the Status later."""
    if written.ok:
        print(written.line())
    else:
        print(f"{written.line()}; {stands}, and `sync-board` sets it", file=sys.stderr)


class Projector:
    """Writes the Status of one card at a time, reading the board's ids once a run.

    ``config`` names the board, as `board_fields` reads it. The project and its
    Status field are read at the first write and kept for the run, so a move and
    its cascade read them once. ``repository_owner`` is the repository's owner
    where the caller holds it, as :func:`read_status_field` takes it."""

    def __init__(
        self, config: dict[str, Any], workflow: dict, *, repository_owner: str | None = None
    ) -> None:
        self._config = config
        self._workflow = workflow
        self._repository_owner = repository_owner
        self._field: FieldRead | None = None

    @property
    def board(self) -> str:
        return f"board #{board_fields.board_number(self._config)}"

    def field(self) -> FieldRead:
        """The Status field, read once."""
        if self._field is None:
            self._field = read_status_field(self._config, repository_owner=self._repository_owner)
        return self._field

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
