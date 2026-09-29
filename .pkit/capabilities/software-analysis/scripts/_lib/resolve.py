"""What the evidence of a flagged artefact's change decides (DEC-001 point 5).

A revalidation ends, for each artefact, in one of four outcomes — it holds, the
analysis was stale, the code regressed, or a gap was found — and telling *stale*
from *regressed* is a question of intent: was the change meant? An agent may
propose it from the change's context; where intent is unclear, a person
decides before anything is recorded, and the analysis is never rewritten to
match broken code.

This module is the part of that judgment that needs no judgment: it classifies
the shapes the evidence takes and says which outcome they decide, or that they
decide none. Reading the change — whether a step still describes the code,
whether the change's context says it was meant — is the resolving agent's; it
passes what it read in as `Intent`, each part a quote of where it read it. So
the stop is one rule, here, and the agent writes nothing unless this says so.

Each anchor that changed since the artefact's revalidation point — or that
resolves to nothing any more, which the checks report as a dead anchor rather
than as a change — has a shape:

- **kept** — a path anchor whose files still hold every piece of code the
  artefact quotes from them (what it writes in backticks and those files held
  at its revalidation point, each as a whole word), and it quotes something;
- **gone** — a path anchor that now resolves to nothing, or whose files no longer
  hold a piece of code the artefact quotes from them: the description and the
  code disagree;
- **deliberate** — a record or another artefact changed: a decision or an
  analysis artefact is only ever changed on purpose;
- **unread** — a path anchor the artefact quotes nothing from, or an anchor of a
  kind no component resolves: nothing mechanical reads it.

And the rules, in the order they apply:

1. **nothing-to-resolve** — the artefact is current, or unanchored, and no
   anchor of it is dead. (Stale with no such anchor, it moved: read it.)
2. **ground-gone** — a *gone* anchor, or a contradiction the agent read (or
   evidence of one, `unintended`) where code changed: stale or regressed,
   decided by intent. Intent cited and none against → `analysis-stale`;
   unintent cited and none for → `code-regressed`; neither, or both →
   **ambiguous**, and the agent stops.
3. **deliberate-change** — a contradiction where only records or artefacts
   changed → `analysis-stale`; with unintent cited against it → ambiguous.
4. **quoted-code-kept** — every changed anchor *kept* → `holds`.
5. **nothing-decides** — otherwise: the agent reads the change, and proposes
   `holds` or `gap-found` itself — or reads a contradiction, and asks again.

`gap-found` is never proposed here: behaviour nothing describes is found by
reading, not by comparing what an artefact quotes.

Pure: no git, no files, no backbone — the command that reads the evidence is
`scripts/propose.py`, so this table can be held to its rules on its own.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

#: The outcomes this module can propose (DEC-001 point 5); `gap-found` is the reader's.
HOLDS, STALE, REGRESSED = "holds", "analysis-stale", "code-regressed"

#: The shapes of a changed anchor.
KEPT, GONE, DELIBERATE, UNREAD = "kept", "gone", "deliberate", "unread"

#: The rules, by name, as the verdicts cite them.
NOTHING_TO_RESOLVE = "nothing-to-resolve"
GROUND_GONE = "ground-gone"
DELIBERATE_CHANGE = "deliberate-change"
QUOTED_CODE_KEPT = "quoted-code-kept"
NOTHING_DECIDES = "nothing-decides"

#: The artefact states, from `pkit friction explain`, with nothing to resolve.
SETTLED = frozenset({"current", "unanchored"})

#: The anchor states that are a change to judge; the rest are current. A dead anchor
#: counts whatever the artefact's state: the checks report it apart from staleness.
CHANGED = frozenset({"stale", "deferred", "dead-anchor"})

#: The anchor kinds whose change is deliberate by nature.
DELIBERATE_KINDS = frozenset({"record", "artefact"})


@dataclass(frozen=True)
class Commit:
    commit: str
    change: str  # its subject


@dataclass(frozen=True)
class Anchor:
    """One anchor of the artefact, as the evidence reads it: its kind and value, its
    state (`pkit friction explain`'s), the commits behind its change, oldest first,
    and — for a path — what the artefact quotes from its files and what of that is
    gone at HEAD."""

    kind: str
    value: str
    state: str
    commits: tuple[Commit, ...] = ()
    quoted: tuple[str, ...] = ()
    gone: tuple[str, ...] = ()

    @property
    def changed(self) -> bool:
        return self.state in CHANGED

    @property
    def shape(self) -> str:
        if self.kind in DELIBERATE_KINDS:
            return DELIBERATE
        if self.kind != "path":
            return UNREAD
        if self.state == "dead-anchor" or self.gone:
            return GONE
        return KEPT if self.quoted else UNREAD

    @property
    def label(self) -> str:
        return f"{self.kind}:{self.value}"


@dataclass(frozen=True)
class Intent:
    """What the agent read, each part a quote of where it read it: `contradicted` —
    the change contradicts what the artefact says; `intended` — the change's context
    says the change was meant; `unintended` — it says it was not (a failing result on
    the artefact, a report of the defect)."""

    contradicted: str | None = None
    intended: str | None = None
    unintended: str | None = None


@dataclass(frozen=True)
class Proposal:
    """An outcome the evidence decides; the agent confirms it by reading the change."""

    outcome: str
    rule: str
    reason: str


@dataclass(frozen=True)
class Read:
    """Nothing mechanical decides: the agent reads the change."""

    rule: str
    reason: str


@dataclass(frozen=True)
class Ambiguous:
    """Stale or regressed, and the evidence does not say which: a person decides."""

    rule: str
    reason: str
    question: str


@dataclass(frozen=True)
class Nothing:
    """Nothing to resolve."""

    rule: str
    reason: str


Verdict = Proposal | Read | Ambiguous | Nothing


def propose(artefact: str, state: str, anchors: Sequence[Anchor], intent: Intent) -> Verdict:
    """The verdict on `artefact`, in `state`, from its anchors and what the agent read."""
    changed = [a for a in anchors if a.changed]
    if not changed and state in SETTLED:
        return Nothing(NOTHING_TO_RESOLVE, f"{artefact} is {state}: nothing changed under it")
    if not changed:
        return Read(
            NOTHING_DECIDES,
            f"{artefact} is {state} with no changed anchor — it moved, or its finding needs an "
            f"edit rather than an outcome: `pkit friction explain` says which",
        )

    gone = [a for a in changed if a.shape == GONE]
    code = [a for a in changed if a.shape != DELIBERATE]
    contradicted = bool(gone) or intent.contradicted is not None or intent.unintended is not None
    if contradicted and code:
        return _stale_or_regressed(artefact, gone or code, intent)
    if contradicted:
        if intent.unintended is not None:
            return Ambiguous(
                DELIBERATE_CHANGE,
                f"only {_labels(changed)} changed, which is only ever changed on purpose, yet "
                f"{intent.unintended!r} says the change was not meant",
                f"{artefact}: only {_labels(changed)} changed. Is {artefact} out of date with "
                f"it, or does the evidence show a defect elsewhere?",
            )
        return Proposal(
            STALE,
            DELIBERATE_CHANGE,
            f"{_labels(changed)} changed on purpose and contradicts {artefact}: "
            f"{intent.contradicted}",
        )
    if all(a.shape == KEPT for a in changed):
        quoted = sorted({q for a in changed for q in a.quoted})
        return Proposal(
            HOLDS,
            QUOTED_CODE_KEPT,
            f"the change to {_labels(changed)} leaves in place everything {artefact} quotes "
            f"from it: {_quotes(quoted)}",
        )
    unread = [a for a in changed if a.shape != KEPT]
    return Read(
        NOTHING_DECIDES,
        f"nothing mechanical reads the change to {_labels(unread)}: read it against "
        f"{artefact} — holds or gap-found, or a contradiction to ask about again",
    )


def _stale_or_regressed(artefact: str, grounds: Sequence[Anchor], intent: Intent) -> Verdict:
    what = "; ".join(_disagreement(a) for a in grounds)
    if intent.contradicted is not None:
        what = f"{what}; read: {intent.contradicted}" if what else f"read: {intent.contradicted}"
    if intent.intended is not None and intent.unintended is None:
        return Proposal(STALE, GROUND_GONE, f"{what} — and it was meant: {intent.intended}")
    if intent.unintended is not None and intent.intended is None:
        return Proposal(
            REGRESSED, GROUND_GONE, f"{what} — and it was not meant: {intent.unintended}"
        )
    if intent.intended is not None:
        reason = (
            f"{what} — and the change's context says both that it was meant "
            f"({intent.intended}) and that it was not ({intent.unintended})"
        )
    else:
        reason = f"{what} — and nothing in the change's context says whether it was meant"
    commits = _commits(grounds)
    return Ambiguous(
        GROUND_GONE,
        reason,
        f"{artefact} and the code disagree: {what}{f' ({commits})' if commits else ''}. Was that "
        f"meant — the analysis is stale and {artefact} is updated — or not — the code "
        f"regressed, a defect is reported and {artefact} stays as it is?",
    )


def _disagreement(anchor: Anchor) -> str:
    if anchor.state == "dead-anchor":
        return f"{anchor.label} resolves to nothing any more"
    if anchor.gone:
        return f"{anchor.label} no longer holds {_quotes(anchor.gone)}, which it quotes"
    return f"{anchor.label} changed"


def _commits(anchors: Sequence[Anchor]) -> str:
    seen = dict.fromkeys(f"{c.commit[:12]} {c.change!r}" for a in anchors for c in a.commits)
    return ", ".join(seen)


def _labels(anchors: Sequence[Anchor]) -> str:
    return ", ".join(a.label for a in anchors)


def _quotes(quotes: Sequence[str]) -> str:
    return ", ".join(f"`{q}`" for q in quotes)
