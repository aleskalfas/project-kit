"""What a message of this capability that reports a missing card says of the sync
([project-management:DEC-072-sync-gives-missing-cards] point 4).

An open issue with no card on the configured board is given it by `sync-board`,
in every project with a board. So every message that reports a missing card names
the sync, run for the issue it reports, in the words :func:`remedy` gives. A
message that knows no number for the issue names the sync run for the whole
board, which gives the issue its card with every other open issue's that lacks
one. Where the
board holds the state, they also say that the sync adds a card only in a run at a
terminal or with the project's switch on, and that the card's Status is set on
the board, since the card the sync adds carries none. `sync-board` itself is the
one command that does not use them: it is the sync.
"""

from __future__ import annotations

from _lib import sync_switch

#: The sync, as a message names it.
SYNC = "pkit pm sync-board"


def sync_command(number: int) -> str:
    """The sync, run for issue ``number``."""
    return f"{SYNC} {number}"


def remedy(number: int | None, *, board_holds_state: bool) -> str:
    """What gives issue ``number`` its card, as a clause a message ends on: the
    sync, run for it, and, where the board holds the state, what it takes to add
    the card there and who sets its Status. Where the message knows no number for
    the issue, ``number`` is None, and the clause names the sync run for the whole
    board, which adds the issue's card with every other open issue's that lacks
    one."""
    command = (
        f"`{SYNC}`, run for the whole board, adds its card and the card of every other "
        "open issue that lacks one"
        if number is None
        else f"`{sync_command(number)}` adds its card"
    )
    if not board_holds_state:
        return command
    return (
        f"{command}, only in a run at a terminal or with the project's switch "
        f"`{sync_switch.NAME}` on, and its Status is then set on the board, since the card "
        "the sync adds carries none"
    )
