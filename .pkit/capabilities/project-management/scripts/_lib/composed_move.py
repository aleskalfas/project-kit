"""What start-work and review-work share as verbs that compose over move-issue.

Each makes one lifecycle move through `move-issue` after a change of its own:
start-work cuts a branch and writes an assignee, review-work opens or readies a
pull request and requests reviewers (DEC-026). So each:

* asks, before it changes anything, whether that move is legal from where the
  issue is — the state read as `move-issue` reads it (`_lib/issue_position`,
  #1242), the legal moves from the table `move-issue` refuses on
  (`lifecycle_inference.legal_targets`) — and refuses with the moves to make
  first (#942, #947), or with why the state cannot be read;
* runs `move-issue`, handing it the status it judged from, so the move is made
  from the state the check passed;
* and when that move still fails after its own changes, ends on a failure that
  names what the run left behind and how to undo each (#942, #947).

A verb supplies only what differs: its name, the target state, and what it
changes.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from _lib import issue_position
from _lib import lifecycle_inference as infer
from _lib.structural_type import infer_structural_type

_SCRIPTS = Path(__file__).resolve().parent.parent


def transition_refusal(
    verb: str,
    issue_number: int,
    issue: dict[str, Any],
    labels: list[str],
    position: issue_position.Position,
    *,
    target: str,
    untouched: str,
    workflow: dict[str, Any],
    issue_types: dict[str, Any],
    classification: dict[str, Any],
) -> str | None:
    """Why `verb`'s composed `move-issue --to <target>` would refuse, or None.

    The structural type comes from `infer_structural_type` (the reader
    move-issue uses), the state from `position`, and the legal moves from
    `lifecycle_inference.legal_targets`. An issue already at `target` passes:
    move-issue treats that as an idempotent no-op, so a re-run still works. A
    `position` whose state is only a stand-in refuses with why. When legal moves
    lead on to `target` the refusal names each of them, else it lists the legal
    targets. `untouched` says what the verb left unchanged, e.g. "no branch, no
    assignee"."""
    title = str(issue.get("title", ""))
    structural_type = infer_structural_type(
        title, issue_types, classification=classification, labels=labels
    )
    if structural_type is None:
        return (
            f"error: cannot determine structural type for issue #{issue_number}: "
            f"title {title!r} matches no known [Type] prefix and no `type:*` "
            "kind label is present. Nothing was changed.\n"
            "  → Restore the issue's title prefix (e.g. [Task]) and re-run."
        )
    nothing_changed = f"Nothing was changed ({untouched})."
    if position.unread is not None:
        return (
            f"[refused] {verb} #{issue_number}: cannot read the issue's state: "
            f"{position.unread}. {nothing_changed}\n"
            f"  → make `pkit process status {issue_position.PROCESS_ADDRESS} "
            f"--subject {issue_number}` answer, then re-run `{verb} {issue_number}`."
        )
    current = position.state
    if current == target:
        return None
    targets = infer.legal_targets(workflow, current, structural_type)
    if target in targets:
        return None
    lines = [
        f"[refused] {verb} #{issue_number}: the issue is in {current!r}, and "
        f"workflow.yaml declares no move {current!r} → {target!r} for "
        f"{structural_type!r}. {nothing_changed}",
    ]
    steps = moves_before(workflow, current, target, structural_type)
    if steps:
        moves = ", then ".join(f"`move-issue {issue_number} --to {step}`" for step in steps)
        lines.append(f"  → move it first: {moves}, then re-run `{verb} {issue_number}`.")
    else:
        lines.append(
            f"  legal targets from {current!r}: {', '.join(targets) if targets else '<none>'}"
        )
    return "\n".join(lines)


def moves_before(
    workflow: dict[str, Any], current: str, target: str, structural_type: str
) -> list[str]:
    """The states to move through, in order, on the shortest legal path from
    `current` to `target`, or [] when workflow.yaml declares no such path.

    Walks `lifecycle_inference.legal_targets` breadth-first, so it names only
    moves move-issue would make. Review is two moves away from Todo, so looking
    a single move ahead would name nothing there."""
    came_from: dict[str, str] = {current: current}
    frontier = [current]
    while frontier and target not in came_from:
        next_frontier: list[str] = []
        for state in frontier:
            for following in infer.legal_targets(workflow, state, structural_type):
                if following not in came_from:
                    came_from[following] = state
                    next_frontier.append(following)
        frontier = next_frontier
    if target not in came_from:
        return []
    steps: list[str] = []
    state = came_from[target]
    while state != current:
        steps.append(state)
        state = came_from[state]
    return steps[::-1]


def invoke_move_issue(
    issue_number: int,
    target: str,
    position: issue_position.Position,
    *,
    capability_root_arg: Path | None,
    allow_foreign_repo: bool,
) -> int:
    """Run `move-issue <N> --to <target> --yes` and return its exit code.

    The engine status `position` was read from is handed down, so move-issue
    moves from the state the early check judged and asks the engine nothing
    again. A confirmed foreign-repo override is threaded through, so that gate
    is confirmed once."""
    cmd = [
        sys.executable,
        str(_SCRIPTS / "move-issue.py"),
        str(issue_number),
        "--to",
        target,
        "--yes",
    ]
    if allow_foreign_repo:
        cmd.append("--allow-foreign-repo")
    if capability_root_arg is not None:
        cmd += ["--capability-root", str(capability_root_arg)]
    env = {**os.environ, **issue_position.handed_down(issue_number, position.status)}
    return subprocess.run(cmd, check=False, env=env).returncode


def late_failure_message(
    verb: str,
    issue_number: int,
    target: str,
    rc: int,
    *,
    left: list[tuple[str, str]],
    nothing_left: str,
    reuses: str,
) -> str:
    """The closing failure when the composed move-issue fails after `verb`'s
    own changes.

    `left` names each thing this run left behind as (what, undo command), so
    the caller can retry or undo; `nothing_left` is the line for a run that left
    nothing, and `reuses` what a re-run picks up again. The output must not end
    on the verb's progress lines as if the run had succeeded (#942, #947)."""
    lines = [
        f"\n[failed] {verb} #{issue_number}: move-issue --to {target} "
        f"failed (exit {rc}); the issue did not move.",
    ]
    if left:
        lines.append("  Left behind by this run:")
        lines.extend(f"  - {what}. Undo: `{undo}`" for what, undo in left)
    else:
        lines.append(f"  {nothing_left}")
    lines.append(f"  Fix the cause above and re-run `{verb} {issue_number}` (it reuses {reuses}).")
    return "\n".join(lines)
