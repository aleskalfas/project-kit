"""What the process engine says of a predicate it could not evaluate, as a pm verb
passes it on — the one rendering.

The engine's JSON views carry, beside each `reason` naming why a predicate could
not be evaluated, what that predicate wrote on standard error as `stderr_tail`:
its last lines, bounded, every escape sequence and control character removed;
null when it said nothing (the process README, "The predicate runner"). A verb
that reports the engine's reason shows those words under it, attributed to the
predicate as the engine's own narrative views attribute them, so the operator
reads the cause and the predicate's own words — a refusal's hint among them —
wherever pm says the engine could not evaluate something: `close-issue`'s held
fold, and an ancestor the forward cascade of `move-issue` cannot place.
"""

from __future__ import annotations

from typing import Any

#: The line the engine's narrative views put above a predicate's own words.
SAID = "the predicate said:"


def said_lines(stderr_tail: Any, indent: str) -> list[str]:
    """What a predicate said (`stderr_tail` from an engine JSON view), under a line
    attributing it to the predicate, at `indent` and kept as the predicate laid it
    out. Nothing when it said nothing, or the field is absent (an engine that
    predates it)."""
    if not isinstance(stderr_tail, str) or not stderr_tail:
        return []
    return [f"{indent}{SAID}", *(f"{indent}  {line}" for line in stderr_tail.splitlines())]


def unplaced_lines(status: Any, indent: str) -> list[str]:
    """Why the engine places a subject in no state, from its `pkit process status
    --json` payload: each cause in `position.unevaluated` once — the reason naming
    the predicate and how its run ended, with what the predicate said beneath it
    (a classifier's one failure leaves all its states unevaluated, and is said
    once) — then each classifier's reasoned "none" in `position.placed_nowhere`,
    as the engine's own status view words it. Nothing when the payload names no
    cause."""
    position = status.get("position") if isinstance(status, dict) else None
    if not isinstance(position, dict):
        return []
    lines: list[str] = []
    seen: set[tuple[str, Any]] = set()
    for entry in _entries(position.get("unevaluated")):
        reason, tail = entry.get("reason"), entry.get("stderr_tail")
        if not isinstance(reason, str) or (reason, tail) in seen:
            continue
        seen.add((reason, tail))
        lines.append(f"{indent}{reason}")
        lines.extend(said_lines(tail, indent + "  "))
    for entry in _entries(position.get("placed_nowhere")):
        predicate, reason = entry.get("predicate"), entry.get("reason")
        if isinstance(predicate, str) and isinstance(reason, str):
            lines.append(
                f"{indent}{predicate!r} places the subject in none of its states: {reason}"
            )
    return lines


def _entries(value: Any) -> list[dict]:
    return [entry for entry in value if isinstance(entry, dict)] if isinstance(value, list) else []
