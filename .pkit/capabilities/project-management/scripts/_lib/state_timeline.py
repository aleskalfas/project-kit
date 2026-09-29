"""An issue's state-label events on the GitHub timeline — the one reader.

Two consumers ask the timeline the same question, which state labels were put
on or taken off an issue:

* `history --check-drift` compares the labels put on against the engine journal,
  to find state changes pkit did not govern
  ([project-management:DEC-049-audit-journal-model]);
* `move-issue` counts both kinds to key its transition audit comment where the
  project keeps no journal: a landed move changes the issue's state label, and a
  failed label write changes nothing (#954).

Which label names count is `axis_labels.carried_labels`: the kit's `state:`
prefix, or the adopter's own vocabulary under a `label` binding. The union is
deliberate and is that seam's own rule — a repository mid-adoption can hold a
stale `state:todo` beside the adopter's `Ready`, and both are state changes.

Whether the timeline's label events can observe state at all is
:func:`label_carries_state`, asked of `_lib/axis_carriage`. Where a board or a
derivation carries state, the reader would find nothing, and a consumer that
counted that nothing would be reporting on a record that was never kept.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from _lib import axis_carriage, axis_labels

#: The timeline events that put a label on an issue and take one off.
LABELED = "labeled"
UNLABELED = "unlabeled"

#: The carriages under which a label holds the issue's state.
_LABEL_CARRIAGES = ("kit-label", "adopter-label")


def label_carries_state(
    config: dict[str, Any] | None,
    substrate_map: axis_labels.SubstrateMap | None,
) -> bool:
    """Whether a label carries this project's `state` — the kit's own label or an
    adopter's `label` binding — so its timeline events record state changes."""
    return axis_carriage.carriage("state", config, substrate_map) in _LABEL_CARRIAGES


def state_label_events(
    issue_number: int,
    config: dict[str, Any],
    substrate_map: axis_labels.SubstrateMap | None = None,
    *,
    run: Callable[..., Any],
) -> list[dict[str, str]] | None:
    """The issue's `labeled` and `unlabeled` timeline events for state labels,
    oldest first, or None when the timeline cannot be read.

    Each item is ``{event, created_at, actor, label}``. `run` is the `gh` runner
    (the caller's `gh_run`); the whole timeline is read, every page of it.
    """
    try:
        proc = run(
            [
                "gh",
                "api",
                "--paginate",
                f"repos/{{owner}}/{{repo}}/issues/{issue_number}/timeline",
            ],
            config,
            check=False,
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    try:
        events = json.loads(proc.stdout)
    except (TypeError, ValueError):
        return None
    out: list[dict[str, str]] = []
    for ev in events if isinstance(events, list) else []:
        if not isinstance(ev, dict) or ev.get("event") not in (LABELED, UNLABELED):
            continue
        label = (ev.get("label") or {}).get("name", "")
        if not axis_labels.carried_labels("state", [label], substrate_map):
            continue
        out.append(
            {
                "event": ev["event"],
                "created_at": ev.get("created_at", "?"),
                "actor": (ev.get("actor") or {}).get("login", "?"),
                "label": label,
            }
        )
    return out
