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
check needs no `pkit process status` run of its own. When a reader of a
board-carried state exists (#726), it goes here and in the classifier.

`move-issue` reads the state itself when it moves: the engine's position, else
the same inference. So a state that changed after the verb's check is judged
there, and a move that stopped being legal is refused there.
"""

from __future__ import annotations

from typing import Any

from _lib import axis_labels
from _lib import lifecycle_inference as infer


def current_state(
    issue: dict[str, Any],
    labels: list[str],
    substrate_map: axis_labels.SubstrateMap | None,
) -> str:
    """The issue's current state, from `issue` as `gh issue view` gives it
    (`state`, `milestone`) and `labels`, its label names. `substrate_map`
    threads the adopter's binding, as the detectors do. Performs no I/O."""
    return infer.infer_current_state(
        state=str(issue.get("state", "")).lower(),
        milestone=issue.get("milestone") or {},
        labels=labels,
        substrate_map=substrate_map,
    )
