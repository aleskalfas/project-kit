"""What the evidence of a flagged artefact's change decides (DEC-001 point 5).

A revalidation ends, for each artefact, in one of four outcomes — it holds, the
analysis was stale, the code regressed, or a gap was found — and telling *stale*
from *regressed* is a question of intent: was the change meant? An agent may
propose it from the change's context; where intent is unclear, a person
decides before anything is recorded, and the analysis is never rewritten to
match broken code.

This module is the part of that judgment that needs no judgment: it classifies
the shapes the evidence takes and says what they come to — an outcome it
proposes, a reading it leaves to the agent with the outcome the evidence leans
to, or a question for a person. Reading the change — whether a step still
describes the code, whether the change's context says it was meant — is the
resolving agent's; it passes what it read in as `Intent`, each part a `Quote`
with where it was read and, where that can be checked, whether it is there.
None of this enforces the stop: the proposal shows each quote beside its source
and its check, and the person who runs the proposed commands decides.

Each anchor that changed since the artefact's revalidation point — or that
resolves to nothing any more, which the checks report as a dead anchor rather
than as a change — has a shape:

- **kept** — a path anchor whose files — those it stands on, never one
  `friction.exclude` leaves out — still hold every piece of code the artefact
  quotes from them (what it writes in backticks and those files held at its
  revalidation point, each as a whole word), and it quotes something;
- **moved** — a path anchor that resolves to nothing any more, or no longer
  holds code the artefact quotes, where that code went somewhere the reading
  can name (`moved_to`): a file renamed, or the code carried into another file.
  The description stands; its anchor is what is out of date;
- **gone** — the same, and the code went nowhere the reading can name: the
  description and the code disagree;
- **deliberate** — a record or another artefact changed;
- **unread** — a path anchor the artefact quotes nothing from, or an anchor of a
  kind no component resolves: nothing mechanical reads it.

And the rules, in the order they apply:

1. **nothing-to-resolve** — the artefact is current, or unanchored, and no
   anchor of it is dead. (Stale with no such anchor, it moved: read it.)
2. **ground-gone** — a *gone* anchor, or a contradiction the agent read (or
   evidence of one, `unintended`) where code changed: stale or regressed,
   decided by intent. Intent cited and none against → `analysis-stale`;
   unintent cited and none for → `code-regressed`; neither, or both →
   **ambiguous**, and the agent asks.
3. **anchor-moved** — every changed anchor *moved* → `holds`, with the anchor
   re-pointed. An edit to the anchors alone changes no content, so it is
   recorded `unchanged` (COR-050 point 5: `updated` with no content change is
   a bump).
4. **deliberate-change** — a contradiction where only records or artefacts
   changed → read, leaning to `analysis-stale`: a decision or an artefact
   changes on purpose, but that alone does not say this artefact was meant to
   follow it. With unintent cited against it → ambiguous.
5. **quoted-code-kept** — every changed anchor *kept*, or *moved* → read,
   leaning to `holds`. That no quoted name vanished is all it shows: behaviour
   can change inside a name that stays, and a quote can survive in a call
   site, a comment or a test name.
6. **nothing-decides** — otherwise: the agent reads the change, and proposes
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
KEPT, MOVED, GONE, DELIBERATE, UNREAD = "kept", "moved", "gone", "deliberate", "unread"

#: The rules, by name, as the verdicts cite them.
NOTHING_TO_RESOLVE = "nothing-to-resolve"
GROUND_GONE = "ground-gone"
ANCHOR_MOVED = "anchor-moved"
DELIBERATE_CHANGE = "deliberate-change"
QUOTED_CODE_KEPT = "quoted-code-kept"
NOTHING_DECIDES = "nothing-decides"

#: The artefact states, from `pkit friction explain`, with nothing to resolve.
SETTLED = frozenset({"current", "unanchored"})

#: The anchor states that are a change to judge; the rest are current. A dead anchor
#: counts whatever the artefact's state: the checks report it apart from staleness.
CHANGED = frozenset({"stale", "deferred", "dead-anchor"})
DEAD = "dead-anchor"

#: The anchor kinds whose change is deliberate by nature.
DELIBERATE_KINDS = frozenset({"record", "artefact"})


@dataclass(frozen=True)
class Commit:
    """A commit behind an anchor's finding: its subject, and the paths behind the
    finding it touched — what a reader limits the commit to (`git show <commit> --
    <paths>`), as `pkit friction explain` names them."""

    commit: str
    change: str  # its subject
    paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class Anchor:
    """One anchor of the artefact, as the evidence reads it: its kind and value, its
    state (`pkit friction explain`'s), the commits behind its findings (for a dead
    path anchor, where its files went), and — for a path — what the artefact quotes
    from its files, what of that is gone from them at HEAD, and where it went, when
    the reading can name it."""

    kind: str
    value: str
    state: str
    commits: tuple[Commit, ...] = ()
    quoted: tuple[str, ...] = ()
    gone: tuple[str, ...] = ()
    moved_to: tuple[str, ...] = ()

    @property
    def changed(self) -> bool:
        return self.state in CHANGED

    @property
    def shape(self) -> str:
        if self.kind in DELIBERATE_KINDS:
            return DELIBERATE
        if self.kind != "path":
            return UNREAD
        if self.state == DEAD or self.gone:
            return MOVED if self.moved_to else GONE
        return KEPT if self.quoted else UNREAD

    @property
    def repointed(self) -> bool:
        """Whether a moved anchor is re-pointed — it resolves to nothing, or holds none
        of what the artefact quoted from it — rather than joined by where the code went."""
        return self.state == DEAD or set(self.gone) == set(self.quoted)

    @property
    def label(self) -> str:
        return f"{self.kind}:{self.value}"


@dataclass(frozen=True)
class Quote:
    """What the agent read, and where: `source` is a commit, a URL, or a person.
    `verified` is whether the quote is in a commit's message, word for word, when
    the source is a commit behind the change — `None` when the source is not a
    commit, and nothing here can check it."""

    text: str
    source: str
    verified: bool | None = None

    def __str__(self) -> str:
        return f"{self.text!r} ({self.source})"


@dataclass(frozen=True)
class Intent:
    """What the agent read, each part a quote with its source: `contradicted` — the
    change contradicts what the artefact says; `intended` — the change's context says
    the change was meant; `unintended` — it says it was not (a failing result on the
    artefact, a report of the defect)."""

    contradicted: Quote | None = None
    intended: Quote | None = None
    unintended: Quote | None = None


@dataclass(frozen=True)
class Proposal:
    """An outcome the evidence decides; the agent confirms it by reading the change,
    and a person runs what records it."""

    outcome: str
    rule: str
    reason: str


@dataclass(frozen=True)
class Read:
    """Nothing mechanical decides: the agent reads the change. `hint` is the outcome
    the evidence leans to, when it leans — never more than a place to start."""

    rule: str
    reason: str
    hint: str | None = None


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
    if all(a.shape == MOVED for a in changed):
        return Proposal(
            HOLDS,
            ANCHOR_MOVED,
            f"the code {artefact} rests on moved, and nothing it quotes is gone: "
            f"{'; '.join(_moved(a) for a in changed)}. Re-point the anchor and record it "
            f"unchanged — confirm by reading the diff that the code moved, not only its name",
        )
    if contradicted:
        if intent.unintended is not None:
            return Ambiguous(
                DELIBERATE_CHANGE,
                f"only {_labels(changed)} changed, which is only ever changed on purpose, yet "
                f"{intent.unintended} says the change was not meant",
                f"{artefact}: only {_labels(changed)} changed. Is {artefact} out of date with "
                f"it, or does the evidence show a defect elsewhere?",
            )
        return Read(
            DELIBERATE_CHANGE,
            f"{_labels(changed)} changed on purpose and contradicts {artefact}: "
            f"{intent.contradicted}. That the change was meant does not say {artefact} was "
            f"meant to follow it: read the change",
            STALE,
        )
    if all(a.shape in (KEPT, MOVED) for a in changed):
        quoted = sorted({q for a in changed for q in a.quoted if q not in a.gone})
        return Read(
            QUOTED_CODE_KEPT,
            f"the change to {_labels(changed)} leaves in place every name {artefact} quotes "
            f"from it: {_quotes(quoted)}. That shows only that none vanished — read the diff "
            f"for behaviour that changed inside them",
            HOLDS,
        )
    unread = [a for a in changed if a.shape not in (KEPT, MOVED)]
    return Read(
        NOTHING_DECIDES,
        f"nothing mechanical reads the change to {_labels(unread)}: read it against "
        f"{artefact} — holds or gap-found, or a contradiction to ask about again",
    )


def _stale_or_regressed(artefact: str, grounds: Sequence[Anchor], intent: Intent) -> Verdict:
    what = "; ".join(_disagreement(artefact, a) for a in grounds)
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
    commits = commit_list(grounds)
    return Ambiguous(
        GROUND_GONE,
        reason,
        f"{artefact} and the code disagree: {what}{f' ({commits})' if commits else ''}. Was that "
        f"meant — the analysis is stale and {artefact} is updated — or not — the code "
        f"regressed, a defect is reported and {artefact} stays as it is?",
    )


def _disagreement(artefact: str, anchor: Anchor) -> str:
    if anchor.shape == MOVED:
        return _moved(anchor)
    if anchor.state == DEAD:
        return f"{anchor.label} resolves to nothing any more"
    if anchor.gone:
        return f"{anchor.label} no longer holds {_quotes(anchor.gone)}, which {artefact} quotes"
    return f"{anchor.label} changed"


def moved_sentence(anchor: Anchor) -> str:
    """Where a moved anchor's code went, and what becomes of the anchor: the words a
    revalidation of it is recorded with."""
    fix = "anchor re-pointed" if anchor.repointed else "anchored there too"
    return f"{_moved(anchor)}; {fix}"


def _moved(anchor: Anchor) -> str:
    where = ", ".join(anchor.moved_to)
    if anchor.state == DEAD:
        return f"{anchor.value} moved to {where}"
    return f"{_quotes(anchor.gone)} moved from {anchor.value} to {where}"


def commit_list(anchors: Sequence[Anchor]) -> str:
    """The commits behind the anchors, each once: `<short> '<subject>'`."""
    seen = dict.fromkeys(f"{c.commit[:12]} {c.change!r}" for a in anchors for c in a.commits)
    return ", ".join(seen)


def _labels(anchors: Sequence[Anchor]) -> str:
    return ", ".join(a.label for a in anchors)


def _quotes(quotes: Sequence[str]) -> str:
    return ", ".join(f"`{q}`" for q in quotes)
