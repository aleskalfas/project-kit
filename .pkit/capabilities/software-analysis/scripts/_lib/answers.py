"""What the person runs for a verdict: the writer commands, word for word.

The resolving agent never runs a writer; it hands the person the commands
that record each outcome on its artefact. For a verdict that comes to an
outcome — a proposal (`_lib/resolve.py`), or a reading with the outcome it
leans to — this gives what the person does first — an edit, a defect to
report — and the commands, each as the person types it and with no consent
flag: the friction writers each ask once, as they are built to, and the record
stamp has no prompt and writes what its command line says. The commands follow
the capability README's table of four outcomes onto the core's two answers
(DEC-001 point 5).

Where the words are the agent's to draft or the person's to supply, a
placeholder stands (`_lib/placeholder.py`), and the writers refuse it until it
is filled: the agent drafts `<why it still holds against this change>` and
`<why it is still wanted>` from what it read; `<the defect reference>` is the
person's alone — the defect is theirs to report and to name.

An ambiguous verdict has no commands, only its question; nor has one that
finds nothing to resolve, or a reading that leans nowhere.

**A regression takes one of two answers** (DEC-001 points 1 and 5). Where an
accepted record the use case anchors decides the regressed step or variant,
the step keeps its words and takes its `Not built yet` box and its entry in
`shortfalls`, which name that record and the defect's issue. The answer is
then `updated`, since the box changes the use case. Otherwise the answer is
`unchanged`, its justification naming the defect. Which record decides which
step is the agent's reading, not a rule:

- **no box can stand** — the artefact is no use case, or anchors no accepted
  record (`deciders` is empty): the rules read it, and the answer is
  `unchanged`;
- **the agent read it** — the step and the record that decides it (`Box`), or
  that no record decides it (`no_box`): the answer follows;
- **otherwise** — no command yet, only what the agent reads first (`which`), so
  `unchanged` is never the only answer for a step a record decides.

Pure, as the rules are: no git, no files, no backbone.
"""

from __future__ import annotations

import shlex
from collections.abc import Sequence
from dataclasses import dataclass

from _lib import shortfalls
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
    """How a person records one outcome: what they do first, then the commands. Where a
    regression's answer waits for the agent's reading, `which` says what it reads, and
    there are no commands yet."""

    outcome: str
    first: tuple[str, ...]
    commands: tuple[str, ...]
    which: str | None = None


@dataclass(frozen=True)
class Box:
    """The agent's reading of a regressed use case: the step or variant the change
    regressed, as the body numbers it (`2`, or `2a` for a variant), and the accepted
    record that decides it, as a record anchor of the use case writes it."""

    at: str
    record: str


def outcome_of(verdict: Verdict) -> str | None:
    """The outcome a verdict comes to: a proposal's, or the one a reading leans to."""
    if isinstance(verdict, Proposal):
        return verdict.outcome
    if isinstance(verdict, Read):
        return verdict.hint
    return None


def box_refused(artefact: str, use_case: bool, deciders: Sequence[str], box: Box) -> str | None:
    """Why `box` cannot stand on `artefact`, or `None` where it can: only a use case's
    step or variant takes a box, and only an accepted record it anchors grounds one, as
    its record anchor writes it (DEC-001 point 1)."""
    if not use_case:
        return (
            f"{artefact} is no use case: only a use case's step or variant takes a box "
            f"(DEC-001 point 1)"
        )
    if box.record in deciders:
        return None
    anchored = ", ".join(deciders) or "none"
    return (
        f"{box.record} is no accepted record {artefact} anchors, as its record anchors write "
        f"them (accepted: {anchored}): only such a record grounds a box (DEC-001 point 1)"
    )


def answer(
    location: str,
    verdict: Verdict,
    anchors: Sequence[Anchor],
    deciders: Sequence[str] = (),
    box: Box | None = None,
    no_box: bool = False,
) -> Answer | None:
    """The answer to `verdict` on the artefact at `location`; `None` when it has none.
    `deciders` are the accepted records the artefact anchors, as its record anchors
    write them, where it is a use case, and none otherwise. `box` and `no_box` are the
    agent's reading of a regression: the step and the record that decides it, or that
    no record decides it."""
    outcome = outcome_of(verdict)
    if outcome is None:
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
    report = f"report the defect, and write its reference in place of {DEFECT}"
    if box is not None:
        return Answer(REGRESSED, (report, _boxed(box), *fixes), (revalidate(location, "updated"),))
    if deciders and not no_box:
        return Answer(REGRESSED, (report, *fixes), (), _which(deciders))
    commits = [c.commit[:12] for a in changed if a.shape != DELIBERATE for c in a.commits]
    broke = ", ".join(dict.fromkeys(commits)) or "the change"
    because = f"The description stands: {WHY_WANTED}; {broke} broke it — defect {DEFECT} reported."
    return Answer(REGRESSED, (report, *fixes), (revalidate(location, "unchanged", because),))


def revalidate(location: str, outcome: str, because: str | None = None) -> str:
    """`pkit friction revalidate`, as the person types it — no `--yes`."""
    words = ["pkit", "friction", "revalidate", location, "--outcome", outcome]
    if because is not None:
        words += ["--because", because]
    return shlex.join(words)


def _boxed(box: Box) -> str:
    """The box and the entry a regressed step takes, in the words the check matches: the
    box names the record's id and holds the issue, as the entry writes them."""
    entry = shortfalls.Entry(0, box.at, DEFECT, box.record)
    return (
        f"add below {entry.place} its `Not built yet` box, which names {entry.record_id} and "
        f"the defect {DEFECT}, and its entry in `shortfalls`: at `{box.at}`, issue {DEFECT}, "
        f"record `{box.record}`. The {entry.place} keeps its words (DEC-001 points 1 and 5)"
    )


def _which(deciders: Sequence[str]) -> str:
    return (
        f"the use case anchors accepted records, and one may decide the step the change "
        f"regressed: {', '.join(deciders)}. Read which step or variant regressed, and whether "
        f"one of them decides it. Then ask again, with `--box <step> --decided-by <record>` "
        f"where one does, so the step takes its box and the answer is `updated`, or with "
        f"`--no-box` where none does, so the answer is `unchanged` (DEC-001 points 1 and 5)"
    )


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
