"""Recording a lifecycle move with the process engine — the one journaling path.

Every pm verb that moves an issue in the lifecycle hands the completed move to
the process engine the same way: `move-issue` for the move it was asked for and
for each parent its forward cascade moves, and `close-issue` for each close
(#1231). One entry per governed move, where the project keeps a journal
([project-management:DEC-049-audit-journal-model]).

The engine is invoked by subprocess, never imported (ADR-020), and only after
the caller has applied the move's domain side-effect — the label write, the
close — per the seam-ordering contract in `.pkit/process/README.md`. Whether
the move is recorded is the engine's decision: it appends to the journal where
the project keeps one (COR-033 point 7) and validates without recording where
it does not, so a caller makes the same call in both modes.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any

from _lib import backbone

#: The issue lifecycle's process address: `<capability>:<process-id>`.
PROCESS_ADDRESS = "project-management:issue-lifecycle"

# What a move the engine did not record costs, in each of DEC-049's two modes:
# with journal logging on the journal is the canonical audit trail and now lacks
# the move; with it off the tracker is, and the engine keeps no record to miss.
JOURNAL_GAP_CLAUSE = (
    "If this project keeps a journal (journal logging on), the journal is the "
    "canonical audit trail (DEC-049) and now lacks this move:"
)
TRACKER_TRAIL_CLAUSE = (
    "If it does not, the tracker is the audit trail and the engine keeps no record to miss."
)

#: What the reason of a move to done a merged pull request made starts with.
PR_MERGE_CLOSE = "pr-merge close"


def pr_merge_close_reason(pr_number: int, *, closed_by_merge: bool) -> str:
    """The reason a move to done that merged pull request ``pr_number`` made is
    journaled with — by close-issue for each issue the pull request closed, and
    by move-issue for the one done-work lands — worded once, so `history` reads
    the same for each.

    ``closed_by_merge`` is whether GitHub had closed the issue as the pull
    request merged (``closed by``), through its `Closes #N`. An issue it left
    open — on a base GitHub does not close issues on, say — was completed by the
    pull request and is closed by pkit through it (``completed by``).
    """
    how = "closed" if closed_by_merge else "completed"
    return f"{PR_MERGE_CLOSE}: {how} by merged PR #{pr_number}"


def journal_move(
    issue_number: int,
    from_state: str,
    target_state: str,
    actor: str | None,
    reason: str | None = None,
) -> bool:
    """Hand the completed move to the engine via `pkit process move` (best-effort).

    Per the seam-ordering contract: the domain side-effect (the label/board
    edit, the close) has ALREADY been applied by the caller; this only records
    the move, which the engine appends to its journal where the project keeps
    one (COR-033 point 7) and validates without recording where it does not. A
    refusal or a missing `pkit` is logged as a warning and never fails the move —
    live detection stays authoritative, so the next `status` reflects the real
    position regardless.

    `from_state` is the position read before the side-effect, passed as
    `--from`. Live detection already reads the side-effect just applied, so
    without it the engine would take the target for the origin: it refused a
    move into a state with no transition to itself (todo → backlog read as
    backlog → backlog, #1183) and journaled one into a state with such a
    transition as that self-loop (backlog → in-progress as create-draft).

    `actor` is the invoker's resolved GitHub login. The engine compares it
    against an authorisation artifact's `produced_by` login for the
    cross-authority gate (COR-033 P4). When it is None (login unresolved), we
    omit `--actor` and let the engine apply its own resolved-identity default.

    `reason`, when given, is recorded on the journal entry (`--reason`): the
    forward cascade names the child move that caused a parent's, a close names
    the mode it closed through, and a move to done a merged pull request made
    names that pull request (`pr_merge_close_reason`). A move the invoker asked
    for directly passes none, and its argv is unchanged.

    True when the engine took the move — recorded it, or validated it where no
    journal is kept — and False when it refused or could not be reached, after
    the warning; the forward cascade reports each ancestor step that came back
    False.
    """
    argv = [
        "pkit",
        "process",
        "move",
        PROCESS_ADDRESS,
        "--to",
        target_state,
        "--from",
        from_state,
        "--subject",
        str(issue_number),
    ]
    if actor:
        argv += ["--actor", actor]
    if reason:
        argv += ["--reason", reason]
    try:
        proc = backbone.run(
            argv,
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, FileNotFoundError):
        print(
            "  [warn] `pkit` not on PATH — the process engine did not record this "
            f"move. {JOURNAL_GAP_CLAUSE} re-run under `pkit` to journal it. "
            f"{TRACKER_TRAIL_CLAUSE} The label/position is unaffected (live "
            "detection stays authoritative).",
            file=sys.stderr,
        )
        return False
    if proc.returncode != 0:
        detail = (proc.stdout or proc.stderr or "").strip()
        report_unrecorded(issue_number, f"the process engine refused this move: {detail}")
        return False
    return True


def report_unrecorded(issue_number: int, why: str) -> None:
    """Warn that a move made on the tracker was not recorded, `why`, and what that
    leaves: a journal gap `history --check-drift` shows, where a journal is kept.

    The warning an engine refusal prints, and the one a caller prints for a
    move it does not hand the engine — a close the workflow declares no
    transition for, say (#1231) — so the two read alike.

    `why` may run over several lines: an engine refusal on a predicate it could
    not evaluate names, on the lines after its first, each cause and what the
    predicate said, under "the predicate said:". Those lines follow the
    warning as the engine laid them out, so nothing of the warning's own runs
    on into the predicate's words.
    """
    first, *rest = why.splitlines() or [""]
    print(
        f"  [warn] {first}. {JOURNAL_GAP_CLAUSE} `pkit pm history {issue_number} "
        f"--check-drift` will show the gap. {TRACKER_TRAIL_CLAUSE} The "
        "label/position is unaffected.",
        file=sys.stderr,
    )
    for line in rest:
        print(line, file=sys.stderr)


# ---- what the journal already holds (#2307) -----------------------------


@dataclass(frozen=True)
class Journal:
    """An issue's engine journal as `pkit process status --json` reports it:
    whether the project keeps one (COR-033 point 7), and its entries, oldest
    first, none where it keeps none."""

    kept: bool
    entries: tuple[dict[str, Any], ...] = ()

    @classmethod
    def of(cls, status: Any) -> Journal | None:
        """The journal a status payload carries, or None for no payload. Only an
        explicit `journal_logging.enabled: false` says no journal is kept: a
        payload without the field comes from an engine that always kept one."""
        if not isinstance(status, dict):
            return None
        logging = status.get("journal_logging")
        kept = not (isinstance(logging, dict) and logging.get("enabled", True) is False)
        journal = status.get("journal")
        entries = (
            tuple(entry for entry in journal if isinstance(entry, dict))
            if isinstance(journal, list)
            else ()
        )
        return cls(kept, entries)

    def last_move_to(self, state: str) -> bool:
        """Whether the last move the journal records ends at ``state``."""
        moves = [entry for entry in self.entries if "to" in entry]
        return bool(moves) and moves[-1].get("to") == state


def read_journal(issue_number: int) -> Journal | None:
    """The issue's engine journal, read through `pkit process status --json`
    (ADR-020), or None where the engine cannot be reached or answers with no
    status."""
    try:
        proc = backbone.run(
            [
                "pkit",
                "process",
                "status",
                PROCESS_ADDRESS,
                "--subject",
                str(issue_number),
                "--json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, FileNotFoundError):
        return None
    if proc.returncode != 0:
        return None
    try:
        return Journal.of(json.loads(proc.stdout or ""))
    except ValueError:
        return None


def owes_board_close(journal: Journal | None, done: str) -> bool:
    """Whether a close still owes the journal its move to ``done``, where the
    map binds the state to the board.

    There the board's Status is the only record of where the work stood, and the
    card at Done cannot tell a close already recorded from one a person or the
    board itself set there. So the journal says it: a close is owed where the
    project keeps a journal and the last move it records is not to ``done``. A
    close `move-issue` recorded as it set the card to Done, or an earlier run
    recorded, is not recorded again. Where no journal is kept, nothing is
    recorded, and nothing is missed. Where the journal could not be read, the
    close is owed, and the engine says whether it can take it.

    An issue reopened since its last recorded close and closed again with no
    move recorded in between reads as recorded: the journal holds no reopen."""
    if journal is None:
        return True
    return journal.kept and not journal.last_move_to(done)
