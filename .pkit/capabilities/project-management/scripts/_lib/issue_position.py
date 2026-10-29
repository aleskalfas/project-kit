"""Where an issue stands, for the early check of `start-work` and `review-work`.

Each verb makes one lifecycle move through `move-issue` after a change of its
own, and checks first that the move is legal from where the issue is, so a
refused move changes nothing (#942, #947). Both read that state through
`current_state` here (#1242).

The reading is the inference from the issue's own fields,
`lifecycle_inference.infer_current_state`: closed reads Done, else the first
state label, else a milestone reads Backlog, else Todo. The process engine's
shipped detection, the lifecycle's classifier
(`lifecycle_predicates.classify_state`), applies that same inference to the same
fields, so the early check and the engine agree by construction today, and the
check needs no `pkit process status` run of its own.

Where the substrate map binds the state to the board, an open issue stands where
its card's Status places it ([project-management:DEC-062-axes-chosen-in-the-map]
point 5). :func:`read_status` reads that Status through `_lib/board_status`, as
the classifier does, and :func:`current_state` takes it beside the labels and the
milestone. A Status that does not place the issue leaves its position
undetermined, and :func:`unplaced_refusal` says which of the outcomes it is
([project-management:DEC-051-axis-carriage-activation] point 6).

`move-issue` reads the state itself when it moves: the engine's position, else
the same inference. So a state that changed after the verb's check is judged
there, and a move that stopped being legal is refused there.
"""

from __future__ import annotations

from typing import Any

from _lib import axis_labels, board_fields, board_status
from _lib import lifecycle_inference as infer

#: The fields of the issue read that :func:`read_status` needs beside the state:
#: the issue's node id, by which its card is found, and its url, whose owner owns
#: the board.
ISSUE_FIELDS = "id,url"


def current_state(
    issue: dict[str, Any],
    labels: list[str],
    substrate_map: axis_labels.SubstrateMap | None,
    status: infer.StatusRead | None = None,
) -> str:
    """The issue's current state, from `issue` as `gh issue view` gives it
    (`state`, `milestone`) and `labels`, its label names. `substrate_map`
    threads the adopter's binding, as the detectors do, and `status` the card's
    Status where the board carries the state. Performs no I/O."""
    return infer.infer_current_state(
        state=str(issue.get("state", "")).lower(),
        milestone=issue.get("milestone") or {},
        labels=labels,
        substrate_map=substrate_map,
        status=status,
    )


def read_status(
    number: int,
    issue: dict[str, Any],
    config: dict[str, Any],
    substrate_map: axis_labels.SubstrateMap | None,
    workflow: dict[str, Any],
) -> infer.StatusRead | None:
    """The card's Status of open issue ``number``, where the map binds the state
    to the board; None where it does not, or where the issue is closed, which is
    Done with no board read. ``issue`` is as `gh issue view` gives it with
    :data:`ISSUE_FIELDS` among its fields: its `id` finds its card, and its `url`
    names the repository whose owner owns the board."""
    if not infer.state_is_board_carried(substrate_map):
        return None
    if str(issue.get("state", "")).lower() == "closed":
        return None
    owner = board_fields.url_owner(str(issue.get("url") or ""))
    board = board_status.StatusBoard(config, workflow, repository_owner=owner)
    return board.read(number, issue_node_id=str(issue.get("id") or ""))


def unplaced_refusal(
    verb: str, number: int, status: infer.StatusRead | None, *, untouched: str
) -> str:
    """The refusal of ``verb`` for an issue whose card's Status does not place it,
    naming which outcome it is and what lets the verb go on. `untouched` says
    what the verb left unchanged."""
    reading = status or infer.StatusRead("unreadable", said="no board to read it from")
    return (
        f"[refused] {verb} #{number}: {reading.finding(number)}. The board carries the "
        "state, and its position is never guessed from the labels or the milestone "
        f"(DEC-051 point 6). Nothing was changed ({untouched}).\n"
        f"  → {reading.remedy(number)}."
    )
