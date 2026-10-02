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

import subprocess
import sys

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
    forward cascade names the child move that caused a parent's, and a close
    names the mode it closed through. A move the invoker asked for directly
    passes none, and its argv is unchanged.

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
        proc = subprocess.run(
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
