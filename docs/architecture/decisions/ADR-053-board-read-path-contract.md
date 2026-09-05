---
id: ADR-053
title: An unreadable board raises where a value was expected; carriage, the board read, and failure posture stay three layers
status: proposed
date: 2026-09-05
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** when an adopter's substrate map says an axis lives on their
Projects-v2 board, a gate that needs that axis has to go and read the board. This
record says what happens when the board will not answer: **the gate raises.** A
board that refuses to answer is a broken tool, not an issue that is missing a
value — and reporting it as a missing value would mean a check passing judgement
on something it never read. The raise is **narrowly scoped**: it can only happen
for an axis the map (or the flag) actually places on the board, so a project with
no board never performs the read and never acquires the failure.

The rest of the record is the layering that makes that ruling implementable.
Three things stay separate: **where an axis lives** (a pure question, answered
with no network access), **what the board currently holds** (a read that reports
what happened and takes no view on it), and **what a failure means** (the
caller's decision). Fusing the first two is the tempting shortcut and it is
refused here, for three reasons — a board outage would become a filing outage on
paths that never touch a board, the layering would run backwards, and the scoping
rule above would become impossible to express.

**The contract, in one breath:** carriage is asked first and cannot fail; the
board read seam answers neutrally; the gate composes them and raises when the
read did not succeed — and only where carriage said `board`.

## Context

The rule that decides which substrate carries an axis is settled: where the
adopter's map binds an axis, that binding governs, and the board flag governs
only where the map is silent
([project-management:DEC-051-axis-carriage-activation]). That record deliberately
does **not** settle the read path's failure semantics — it names them as a
read-path contract belonging architecture-side rather than a precedence rule.
This is that record.

**The surfaces this contract governs, as they stand.**

1. **`_lib/axis_carriage.py`** answers *where does this axis live*. It is pure —
   no I/O, `config` arrives as an injected dict — and it returns a **closed set**
   (`kit-label` / `adopter-label` / `title` / `derived` / `board` / `degrade`)
   rather than a board/not-board boolean, so a consumer cannot satisfy the type
   while still having to ask a second question to be correct. It reads binding
   shape through the label seam (`_lib/axis_labels`); it calls no board code.
2. **`_lib/board_fields.py`** is the board read seam: board identity (board
   number → project node id), the board's live field definitions and their
   options, and the per-issue card (item) lookup. Every read returns a result
   object carrying `ok` plus `gh`'s stderr **verbatim** on failure, and the
   module's posture is that the caller decides what a failure means.
3. **The gates** that need a classification value. The classification presence
   gate in `validate-issue.py` is the first and the forcing case.

**What exists on the board arm.** The map's `board:` arm is parameterless
(`board: true`), admissible on `priority` and `workstream` only, with the field's
identity staying a write parameter on the `after_create_issue` hook
([project-management:DEC-051-axis-carriage-activation], decision point 2). The
label seam already carries its accessors: `axis_is_board_carried` reports the
arm, and `resolve_write` returns `DEGRADE` for a board-carried axis because there
is no label to write.

**What does not exist yet.** There is no board **field-value** read in the seam.
One exists in `back-fill.py` (`_read_current_field_value`, over
`back_fill_apply.FIELD_REREAD_QUERY`), plumbed to a single caller, and its
contract *is* that caller's posture: `read_ok=False` means "back-fill must skip",
and a `None` current value covers both "the field is unset" and "we could not
read it".

The architecturally-significant pins, each against a plausible alternative:

1. **Whether carriage and the board read are one layer or two** — one call that
   answers "what is this axis's current value" versus a pure carriage answer the
   gate composes with a separate read.
2. **What an unreadable board means** — a broken tool (raise) versus a missing
   value (a finding at some severity) versus a satisfied check (fail open).
3. **How far that meaning reaches** — every board read anywhere, versus only
   where a value was genuinely expected from the board.
4. **Where the field-value read lives** — the board read seam, neutral, versus
   back-fill's private copy, versus a second copy grown by the gate.
5. **What the `board:` arm obliges of a reader** — the read-path contract for
   that arm, in the sense [pkit:ADR-026] is the contract for the label arms.

## Decision

**In plain terms:** ask *where does this live* first, with a question that cannot
fail. Only if the answer is "the board" do you read the board. If that read does
not succeed, raise — you were told to expect a value and the tool will not give
you one. Everything else stays as it is.

### 1. Three layers, one direction

**Layer 1 — carriage.** `axis_carriage.carriage(axis, config, substrate_map)`
answers *where does this axis live*, purely, from an injected `config` dict and an
already-loaded map. It performs **no I/O** and returns a member of the closed
`Carriage` set. It calls the label seam to read binding shape; it never calls the
board read seam. The one-way layering [pkit:ADR-026] pins holds in both
directions: **carriage calls the seams; no seam calls carriage.**

**Layer 2 — the board read seam.** `_lib/board_fields` owns every read of the
board: identity, field definitions, item lookup, and — per point 5 — the field
**value** read. It is posture-neutral: it returns a result object saying whether
the board answered and what it said, with `gh`'s stderr verbatim on failure, and
it decides nothing about what that means.

**Layer 3 — the gate composes them.** A consumer that needs a classification
value asks carriage; if the answer is `board`, it asks the seam; if the read did
not succeed, it **raises** (point 2).

**Fusing layers 1 and 2 is refused.** A single "what is this axis's current
value" call is the obvious simplification and it is wrong on three counts:

- **A board outage would become a filing outage.** Rewiring the flag reads across
  the verb family is only safe because asking *where does this live* cannot fail.
  Every verb asks that question; only a few ever need a board value. Fusing makes
  the unfailing question fail, on code paths that never touch a board.
- **It breaks the one-way layering.** The pure layer would depend on the network
  layer, and the composition ordering [pkit:ADR-026] pins — adopter-binding
  first, board-versus-label only underneath — would run backwards again, which is
  the shape of the failure the carriage rule exists to end.
- **The scoping rule becomes unimplementable.** Point 3 fires the error *only*
  where a value was expected from the board. Expressing that requires answering
  "does this project expect a board value for this axis?" **without performing a
  board read** — otherwise the condition depends on the very operation it gates,
  and there is no way to be silent for a project that has no board.

### 2. An unreadable board raises

When a gate performs a board read because carriage said `board`, and that read
does not succeed, the gate **raises an error**. It does not report a missing
value, does not soften to a warning, and does not pass.

**A board that will not answer is a broken tool, not a missing value.** The two
are different facts about the world and the adopter's remedy differs: an
unreadable board is repaired by fixing the tool (most commonly a token missing
the `read:project` scope, whose remedy `gh` prints in the stderr the seam carries
verbatim); a missing value is repaired by classifying the issue. A gate that
reports the first as the second sends the adopter to fix the wrong thing.

**This is explicitly distinct from a board that answers *unset*.** A board that
responds and reports no value for the field is a genuine missing value — and what
a gate should do about a missing value, where that demand is placed, and who pays
when a predecessor omitted it, is a separate methodology question that this
record does **not** settle.

**One edge that composes rather than surprises.** Carriage keys on the board flag
alone, not on the board id, deliberately: treating "flag set, id unset" as *no
board* would hand the axis back to kit labels the adopter may not have. So that
misconfiguration resolves to `board` carriage, the seam then refuses with "no
Projects v2 board configured" and **no network call**, and the gate raises for the
same reason it raises on a network failure — it was told to expect a value from a
board that cannot be reached. An unsatisfiable `board: true` under a config
declaring no board is refused upstream by validation; if one reaches a gate, it
raises on the same footing.

### 3. The error fires only where a value was genuinely expected

The raise is scoped by carriage: it can occur **only** when
`axis_carriage.carriage(...)` returns `board` for the axis being read.
`is_board_carried` is the narrow predicate for a gate that only needs that split.

**A project with no board is unaffected in every path** — no board read, no `gh`
call, no new failure mode, no new latency. This holds structurally in the code
today: `board_fields.board_number(config)` returns `None` when the flag is falsey
or the id is unset, and every read short-circuits on that `None` before invoking
`gh`. That property is load-bearing for this contract and **must be preserved by
test, not by inspection**: a no-board fixture exercised through a composing gate
asserts that **zero** `gh` invocations occur. Inspection does not survive the next
author.

### 4. Reconciliation with back-fill — different drivers, not a conflict

`back-fill --apply` fails **closed to a DRIFTED skip** when it cannot read a
field's current value. **That is correct for back-fill and it stays.** It is not
contradicted, softened, or superseded by point 2.

The postures differ because the drivers differ, and the difference is precisely
the availability of a no-op. **Skipping a write costs nothing and can be
retried**: the corpus is unchanged, the skip is audited, and a re-run completes
the work. **A gate has no equivalent no-op** — a gate that "skips" its check still
has to return a verdict, and a verdict it did not compute is indistinguishable, in
the adopter's repo, from a check that does not exist. Both drivers refuse to act
on a value they could not read; for back-fill that refusal is "do not write", for
a gate it can only be "raise".

**A known defect, not a blessed posture.** Back-fill's *emitted-script* path fails
**OPEN**: a failed re-read reads empty and the write proceeds, overwriting a value
it never read (`_field_guarded_fragment` in `_lib/back_fill_apply.py`, whose
generated comment says so). That is filed as
[#816](https://github.com/aleskalfas/project-kit/issues/816) with a ruling that it
should raise. It is cited here so no reader mistakes it for a third sanctioned
posture; this contract neither depends on it nor endorses it.

### 5. The field-value read moves into the board read seam, and moves neutral

The board field-value read belongs in **`_lib/board_fields`**, alongside the
identity, field-definition and item reads — the module that is already the single
home for board reads on COR-007's third-copy grounds. A gate that needs a board
value asks the seam, exactly as it asks for the item id.

**The promoted read is neutral. It must not carry back-fill's posture across.** It
returns the seam's shape — whether the board answered, what it said, and `gh`'s
stderr verbatim when it did not — and back-fill maps that onto its own posture at
its own boundary, where the DRIFTED-skip decision belongs. This is the easiest
thing in this record to get wrong, because the existing function's contract *is*
the posture: its `read_ok` conflates "the board answered" with "back-fill may
proceed", and its `None` current conflates *unset* with *unread*. The promoted
read separates both. Collapsing them would be worse than untidy: point 2 rules on
unreadable and deliberately leaves *unset* open, so a seam that cannot **say**
"the board answered, and the field is unset" makes the deferred question
unanswerable later without re-plumbing the read.

The re-read query stays a **single source of truth** shared by back-fill's
`--apply` read and its emitted guard, so the two read surfaces cannot silently
desync; the constant travels with the read rather than being copied.

### 6. The `board:` binding arm's read-path contract

For the label arms, [pkit:ADR-026] is the read-path contract. This is the same for
the `board:` arm.

- **The arm is parameterless** (`board: true`); the field's identity remains a
  write parameter on the `after_create_issue` hook. The read path needs no
  parameter because the seam resolves the field **by name** against the live
  board — the Title-cased axis name, matched exact-first then case-insensitively,
  with the option matched the same way. Nothing in the map has to name a field.
- **Admissible on `priority` and `workstream` only.** `type` is excluded
  permanently (PR-title alignment reads the type label, and a board field is
  invisible from a PR); `state` is excluded for now (reading a board Status field
  needs a detector kind that does not exist). The schema is the gate; the seam
  does not re-check admissibility, because a second copy of the rule is a source
  of truth that can disagree.
- **A board-carried axis is SERVED, not degraded.** `resolve_write` returns
  `DEGRADE` for it — correctly, since there is no label to write — so a consumer
  that keys only on the resolver reports "unsupported under your substrate-map"
  for an axis that is fully served, and softens every rule that needs it.
  **Consumers consult `axis_is_board_carried` (or carriage) BEFORE resolving**,
  exactly as they already consult `axis_is_title_carried` for the title arm. For a
  presence gate this means: demand no label for the axis, and ask the board.

### Boundaries — what this contract is NOT

- **Not the missing-value question.** A board that answers *unset* is a value
  question, deliberately open (point 2).
- **Not gate placement.** When an axis's presence is demanded, and who pays when a
  predecessor omitted it, is open and tracked separately.
- **Not the board-membership check.** Membership stays with the flag and must not
  route through carriage; a membership that cannot be determined is reported as a
  finding at DEC-019's own drift severity, over a payload the gate already
  fetched. That is a different question (is this issue *on* a board) resolved from
  incidental data, not a value read the gate performed *because* carriage said the
  value lives there. Both stand; neither is the model for the other.
- **Not a change to the label read path or the substrate write path.**
  [pkit:ADR-026]'s ternary, fail-closed posture and sole-constructor invariant are
  untouched — its composition ordering is what layer 1 realises. [pkit:ADR-031]'s
  write primitive and its failure-posture neutrality are untouched; this inherits
  that neutrality at the read boundary.
- **Not a parameterised `board:` arm.** A field name in the map is refused; the
  read resolves by name through the seam.
- **Not the repair of back-fill's emitted-script fail-open** (#816).

## Rationale

**Why three layers rather than one call.** The three concerns fail differently and
are needed by different populations. Every verb needs carriage; only some need a
value; only the caller knows what a failure costs it. A single fused call would
give the most-used question the failure profile of the least-used one, and would
make the scoping rule circular — you would have to read the board to learn whether
reading the board was expected. Keeping them apart is what lets the carriage
rewiring proceed across the whole verb family without any of those verbs acquiring
a network dependency.

**Why raise rather than report a missing value.** A finding is a judgement about
the *issue*; an unreadable board is a fact about the *repo's tooling*. Filing the
second as the first mis-attributes the fault, sends the adopter to classify an
issue that may already be classified, and — because findings are one line in a
stream — lets the issue proceed on a check that computed nothing. The failure this
whole line of work exists to end was silent; a warning that passes is the same
failure with better prose. Raising is also cheap to get right: the seam carries
`gh`'s stderr verbatim, so the raise arrives with its own remedy attached rather
than a paraphrase.

**Why not fail open.** Treating an unread value as satisfied writes the silent
miss back into the gate — a check that passes on a value it could not read is
indistinguishable, in the adopter's repo, from a check that does not exist.

**Why the scope is exactly "carriage said board".** An adopter who uses no board
must not inherit a failure mode from a feature they do not use; a feature that can
break a project which never opted into it is not optional. The scope is
expressible only because layer 1 is pure — which is the practical payoff of the
layering, not a coincidence of it.

**Why the value read promotes into the seam.** It is the third instance of the
same shape (the seam already absorbed the project-node-id and field-list copies on
exactly these grounds), and the alternative is worse than a duplicate: two copies
would drift on the one thing that must not drift — what counts as a
positively-confirmed read. Promoting also concentrates the widened blast radius of
a scope-deficient token into a single auditable place, which is a reason to move
the read rather than a reason to leave it scattered.

**Why the promoted read must be neutral.** This is [pkit:ADR-031]'s
failure-posture neutrality at the read boundary, and for the same reason: a
posture baked into the shared primitive forces the other driver to wear a posture
its own record rejected. Back-fill's skip is right for back-fill and wrong for a
gate; a gate's raise is right for a gate and would abort a bulk loop mid-corpus.
Neutral read, posture at the boundary, keeps both correct behind one
implementation.

### Alternatives considered

- **One fused "resolve the axis's current value" call.** Rejected — makes the
  unfailing question fail (a board outage becomes a filing outage on paths that
  never touch a board), inverts the pinned layering, and makes the scoping rule
  circular.
- **Treat an unreadable board as a missing value** (a finding at some severity).
  Rejected — passes judgement on a value never read, mis-diagnoses a tooling fault
  as an issue defect, and lets the issue proceed on an uncomputed check.
- **Treat an unreadable board as satisfied** (fail open). Rejected — reinstates
  the silent-miss class the carriage work exists to end.
- **Raise on any board read failure anywhere.** Rejected — a project with no
  board, or an axis that does not live on one, would acquire a failure mode from a
  feature it does not use. The scoping predicate exists precisely to prevent this.
- **Promote the read with its fail-closed-to-skip contract intact.** Rejected —
  the posture is the caller's. A gate handed a skip-shaped result has to invent a
  meaning for it, and the conflation of *unset* with *unread* inside that contract
  would foreclose the missing-value question this record deliberately leaves open.
- **Leave the read in back-fill; let the gate grow its own.** Rejected — a third
  copy of a board read, which is the exact scatter the seam exists to end, and the
  two copies would disagree about what counts as a confirmed read.
- **Adopt the emitted script's fail-open re-read as the general posture.**
  Rejected — it overwrites a value it never read; filed as #816 with a ruling that
  it should raise.
- **Give the `board:` arm a field name so the read can address the field.**
  Rejected already, by the carriage rule — the read resolves by name through the
  seam, and a second declaration point for the write parameters is the
  second-source-of-truth failure the arm was designed to avoid.

## Implications

- **Carriage stays pure and injected.** `_lib/axis_carriage` takes `config` as a
  dict and performs no I/O; it calls the label seam and never the board seam, and
  no seam calls it. A consumer needing a board value composes the two itself.
- **The no-board silence is a tested property.** A no-board fixture driven through
  a composing gate asserts **zero** `gh` invocations. Without that test the scoping
  rule is an inspection result, and inspection does not survive the next author.
- **The field-value read lands in `_lib/board_fields`** with the seam's neutral
  result shape, able to distinguish *the board answered and the field is unset*
  from *the board did not answer*, carrying `gh`'s stderr verbatim on the latter.
- **Back-fill's observable behaviour is unchanged.** Its wrapper maps the neutral
  result onto its own fresh-state shape, and an unreadable field value still
  produces a DRIFTED skip. A regression test pins that, since the promotion's whole
  risk is the posture leaking or being lost in transit.
- **The re-read query keeps one source of truth**, shared by the `--apply` read and
  the emitted guard, so the two surfaces cannot silently desync.
- **The gate's failure path is a raise, not a finding**, and its message carries
  the seam's verbatim error so the remedy reaches the adopter unparaphrased.
- **The prerequisite check should report the `read:project` scope.** Promoting this
  read widens the blast radius of a token missing that scope: today it breaks
  back-fill's drift check only; once a gate reads field values it breaks the gate
  for every adopter with a `board:` binding. `pre-check` verifies authentication
  but not this scope. It should carry a finding — scoped the same way, fired when
  any axis resolves to `board` — so the adopter learns at prerequisite time rather
  than discovering it at gate time on a real issue. Recommended as part of this
  work; the check's exact shape is implementation scope.
- **Consumers consult the board predicate before resolving.** `resolve_write`
  returning `DEGRADE` for a board-carried axis is correct and is **not** a report
  that the axis is unsupported; a consumer that keys only on the resolver lies
  about a served axis and softens the rules that need it.
- **Relationship to records.** No amendment to
  [project-management:DEC-051-axis-carriage-activation] is needed — that record
  names these semantics as belonging to a read-path contract recorded
  architecture-side, and this is it. **[pkit:ADR-026] is not superseded**: its
  label read path, ternary and fail-closed posture stand, and its composition
  ordering is what the carriage layer realises. **[pkit:ADR-031] is not
  superseded**: this is the read-side sibling to its write path, inheriting its
  failure-posture neutrality at a new boundary. DEC-019's membership requirement is
  untouched.
- **No migration owed.** No adopter-visible path is renamed or removed and no
  `schema_version` moves; the read's promotion is internal and behaviour-preserving
  for its existing caller.
- **Surface change.** Adopters with a `board:` binding gain a new failure mode on
  the gate, so the change-set declares a changeset; version numbers are written by
  the release step.
- **Acceptance gate.** Accepted by the maintainer before implementation is built
  against it — a forward design contract, **not self-accepted**.
