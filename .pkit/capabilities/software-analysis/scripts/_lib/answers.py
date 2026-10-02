"""What the person runs for a verdict: the writer commands, word for word.

The resolving agent never runs a writer; it hands the person the commands
that record each outcome on its artefact. For a verdict that comes to an
outcome — a proposal (`_lib/resolve.py`), or a reading with the outcome it
leans to — this gives what the person does first — an edit, a defect to
report — and the commands, each as the person types it and with no consent
flag: every writer asks once, as it is built to. The commands follow the capability README's
table of four outcomes onto the core's two answers (DEC-001 point 5).

Where the words are the agent's to draft or the person's to supply, a
placeholder stands (`_lib/placeholder.py`), and the writers refuse it until it
is filled: the agent drafts `<why it still holds against this change>` and
`<why it is still wanted>` from what it read; `<the defect reference>` is the
person's alone — the defect is theirs to report and to name.

An ambiguous verdict has no commands, only its question; nor has one that
finds nothing to resolve, or a reading that leans nowhere.

Pure, as the rules are: no git, no files, no backbone.
"""

from __future__ import annotations

import shlex
from collections.abc import Sequence
from dataclasses import dataclass

from _lib.resolve import (
    ANCHOR_MOVED,
    DEAD,
    DELIBERATE,
    HOLDS,
    MOVED,
    REGRESSED,
    STALE,
    Anchor,
    Proposal,
    Read,
    Verdict,
    moved_sentence,
)

#: The words the agent drafts from what it read.
WHY_HOLDS = "<why it still holds against this change>"
WHY_WANTED = "<why it is still wanted>"

#: The words only the person supplies: the defect they reported.
DEFECT = "<the defect reference>"


@dataclass(frozen=True)
class Answer:
    """How a person records one outcome: what they do first, then the commands."""

    outcome: str
    first: tuple[str, ...]
    commands: tuple[str, ...]


def answer(location: str, verdict: Verdict, anchors: Sequence[Anchor]) -> Answer | None:
    """The answer to `verdict` on the artefact at `location`; `None` when it has none."""
    if isinstance(verdict, Proposal):
        outcome = verdict.outcome
    elif isinstance(verdict, Read) and verdict.hint is not None:
        outcome = verdict.hint
    else:
        return None
    changed = [a for a in anchors if a.changed]
    moved = [a for a in changed if a.shape == MOVED]
    fixes = tuple(_fix(a) for a in moved) + tuple(_dead(a) for a in changed if _dead_ground(a))
    if outcome == HOLDS:
        because = (
            "; ".join(moved_sentence(a) for a in moved) + "."
            if verdict.rule == ANCHOR_MOVED
            else WHY_HOLDS
        )
        return Answer(HOLDS, fixes, (revalidate(location, "unchanged", because),))
    if outcome == STALE:
        content = f"edit {location} to describe what the change made true, and nothing more"
        return Answer(STALE, (content, *fixes), (revalidate(location, "updated"),))
    if outcome != REGRESSED:
        return None  # `gap-found` is the reader's, and never proposed
    commits = [c.commit[:12] for a in changed if a.shape != DELIBERATE for c in a.commits]
    broke = ", ".join(dict.fromkeys(commits)) or "the change"
    because = f"The description stands: {WHY_WANTED}; {broke} broke it — defect {DEFECT} reported."
    report = f"report the defect, and write its reference in place of {DEFECT}"
    return Answer(REGRESSED, (report, *fixes), (revalidate(location, "unchanged", because),))


def revalidate(location: str, outcome: str, because: str | None = None) -> str:
    """`pkit friction revalidate`, as the person types it — no `--yes`."""
    words = ["pkit", "friction", "revalidate", location, "--outcome", outcome]
    if because is not None:
        words += ["--because", because]
    return shlex.join(words)


def _fix(anchor: Anchor) -> str:
    where = ", ".join(anchor.moved_to)
    if anchor.repointed:
        return f"re-point {anchor.label} to {where} in the artefact's anchors"
    return f"add {where} to the artefact's path anchors, beside {anchor.value}"


def _dead_ground(anchor: Anchor) -> bool:
    return anchor.state == DEAD and anchor.shape != MOVED


def _dead(anchor: Anchor) -> str:
    return (
        f"{anchor.label} resolves to nothing: a revalidation does not answer a dead anchor — "
        f"correct it or remove it (`pkit friction explain` names the edit)"
    )
