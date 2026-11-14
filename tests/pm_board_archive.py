"""Which cards a Projects v2 board gives a walk of its cards (#3191).

The board's card list, `ProjectV2.items`, leaves archived cards out unless the
walk asks for them: its `archivedStates` argument defaults to `[NOT_ARCHIVED]`.
The fakes of a board answer a walk as GitHub does, so a walk that does not ask
misses an archived card in a test as it would on a real board.
"""

from __future__ import annotations

import re

_ARCHIVED_STATES = re.compile(r"archivedStates:\s*\[([^\]]*)\]")


def reads_archived(query: str) -> bool:
    """Whether the board gives the walk `query` its archived cards: only where
    the walk's `archivedStates` names `ARCHIVED`."""
    asked = _ARCHIVED_STATES.search(query)
    states = asked.group(1).split(",") if asked else ["NOT_ARCHIVED"]
    return "ARCHIVED" in (state.strip() for state in states)
