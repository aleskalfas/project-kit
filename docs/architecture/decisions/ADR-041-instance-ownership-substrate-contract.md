---
id: ADR-041
title: Fold the instance-ownership comment log through one read seam and regenerate the description mirror through one write point — comment-log authoritative, mirror derived, comment-wins over a lingering label
status: accepted
date: 2026-07-07
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** an issue's instance-owner can be recorded two ways — DEC-035's
`instance:N` label where the repo can create labels, and DEC-043's label-free
substrate where it cannot: an **append-only log of ownership events**
(claim / handoff / abandon / release) posted as issue comments, with a
plain-language **mirror of the *current* owner regenerated into the issue
description** so a human sees who owns an issue without reading the log. This
contract says: there is **one place** that reads that comment log and folds it to
"who owns this issue now" (every consumer asks it — the clash guard, the signed
listing, the mirror renderer — none re-scans comments itself), and **one place**
each that constructs an ownership-event comment write and regenerates the
description mirror. The comment log is **authoritative**; the description mirror
is a **derived** view the read seam regenerates by full overwrite, never a source
of truth. Where a repo carries both a lingering `instance:N` label and a
comment-log marker, the seam resolves **comment-log-wins**, once, for every
consumer. That is the whole decision; everything below is the rigor behind it.

[project-management:DEC-043](../../../.pkit/capabilities/project-management/decisions/DEC-043-ownership-substrate-selection.md)
decided the *rule* — the instance-ownership marker binds to a **selectable
substrate** ("substrate-where-available"): the `instance:N` label
([project-management:DEC-035](../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md))
where labels are creatable, an append-only comment log (source of truth) plus a
derived, regenerable owner-mirror in the issue description where they are not; the
selector lives in instance-ownership's own schema home (not `substrate-map.yaml`),
default `comment`. This ADR records the *comment-substrate contract* DEC-043 named
as its ADR follow-up (DEC-043 D5) — the **fourth sibling** to
[ADR-026](ADR-026-substrate-map-read-path-contract.md) (the label
read-path/sole-constructor seam),
[ADR-031](ADR-031-substrate-write-path-contract.md) (the field/milestone
write-path sole-constructor), and
[ADR-035](ADR-035-containment-resolution-contract.md) (the containment
read-seam + write-constructor): **how** ownership resolves on read and constructs
on write in `comment` mode, and the one invariant each side must never violate. It
pins the contract, not the selector schema, the comment-stamp format, or the
mirror-region UX (those land with the Feature, citing DEC-043).

**The contract, in one breath:** instance ownership in `comment` mode has **one
read seam** — a single fold point answering "who owns this issue now, and via
which substrate," folding the per-instance append-only event log to current
ownership, with **comment-log-wins as a seam invariant** over a lingering label —
and **one write construction point per side** (the ownership-event comment write;
the description-mirror full-overwrite regenerator), each under the grep/AST
sole-constructor guard the sibling ADRs established. No consumer re-derives
ownership by scanning comments itself (ADR-026's one-reader discipline, applied to
the ownership axis); no script string-builds an ownership-event comment or a
mirror region inline (ADR-031/ADR-035's sole-constructor discipline, applied to a
fourth substrate).

**The load-bearing invariants — one read seam with comment-log-wins, one write
constructor per side, the mirror derived.** Three parts, structural only together:
(i) **every ownership consumer resolves the current owner only by asking the
seam** — the clash guard (DEC-035 D6), the signed listing (DEC-035 D7), and the
description-mirror renderer all route through the fold; none re-scans comments
directly, so there is one place ownership is resolved and one place authenticity
(`author.login`) and comment-log-wins are enforced; (ii) **the seam folds the
append-only log to current ownership and, over a mixed repo, comment-log-wins** —
a claim followed by a handoff followed by an abandon folds to the last authentic
event's owner (or unclaimed), and where a lingering `instance:N` label coexists
with a comment-log marker the fold resolves to the comment-log owner, the label
treated as residual; this is DEC-035's lowest-wins tie-break preserved atop
per-object-atomic comment writes, lifted to a **mixed-mode reconciliation**
invariant (a repo forward-switched from label to comment may hold both; the seam
resolves it deterministically); and (iii) **each write is constructed in exactly
one point** — the ownership-event comment via one writer, the description mirror
via one full-overwrite regenerator (**never an append**) — under one grep/AST
guard, the same discipline ADR-031/ADR-035 hold for their substrates. The
description mirror is a **derived view** whose regeneration spine is the comment
log: a stray human edit or a racing write is regenerated by the seam, so no
ownership record is lost.

## Context

DEC-043 settled the ownership substrate-selection rule and explicitly deferred the
formal contract to a sibling ADR: *"The write path is a sole-constructor pinned by
a sibling ADR … one read seam, one construction point, a grep/AST guard,
failure-posture-neutral. The ADR is authored by the architect once this record
settles."* (DEC-043 D5, and its Implications naming "a fourth sibling ADR" that
pins the comment-log read seam, the description-mirror sole-constructor, the
grep/AST guard, and mixed-mode precedence). DEC-043 is now `accepted`; this is that
ADR.

The comment-log substrate is a **fourth substrate**, distinct from the label axis
ADR-026 covers, the Projects-v2 field-value / milestone writes ADR-031 covers, and
the containment edge ADR-035 covers. It is a *different operation* again — reading
`gh issue view --json comments` and folding hidden-stamped event comments, writing
a new ownership-event comment, and full-overwriting a derived region of the issue
*body* — so it lives in its own module with its own sole-constructor guard, the
same discipline as the three prior seams, **not a widening of any of them.**
ADR-026's label invariant, ADR-031's field/milestone invariant, and ADR-035's
containment invariant all stay scoped to their own substrates and untouched.

[project-management:DEC-035](../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md)
is where the ownership semantics originate — the `(assignee, instance:N)` owner,
the clash guard that refuses an ordinary verb on another instance's work
(`[validation-severity:bypassable-with-audit]` per
[project-management:DEC-014](../../../.pkit/capabilities/project-management/decisions/DEC-014-validation-severity-model.md)),
and the same-instant lowest-wins tie-break both clones compute identically. DEC-043
refined DEC-035 to substrate-*where-available* and added the comment substrate,
preserving those semantics atop per-object-atomic comment writes. This ADR pins how
that refined rule resolves at the seam in `comment` mode.

**The realization surface — a forward design contract.** Unlike ADR-026/ADR-031
(convergence over shipped inline sites) and ADR-035 (seam-first, merged
#344/#345), the instance-ownership feature (DEC-035) and its comment substrate
(DEC-043) are **gated, not yet built** (DEC-043 Implications: "Implementation is
gated … bumps the capability version on landing"). This ADR is therefore a
**forward contract** in the class of ADR-031's acceptance-gate posture: the seam,
the two constructors, the guard, and the drivers land with the Feature, citing
this ADR for the invariant. As project-kit's own capability-architecture record,
concrete module/site names are in scope once they exist (per
[PRJ-005](../../../.pkit/decisions/project/PRJ-005-adopt-adrs.md)); until the
Feature builds them this Context names the participants conceptually rather than by
line number. The participants:

1. **The ownership fold** (a single ownership-substrate `_lib` seam) — the one read
   point. Reads the issue's comments (returned inline by the existing corpus read,
   DEC-043 Implications "read cost stays one call"), keeps only comments carrying
   the hidden ownership stamp **authored by the expected assignee account**
   (`author.login` authenticity, DEC-043 D3), folds the append-only claim / handoff
   / abandon / release sequence to current ownership, and — over a mixed repo —
   applies comment-log-wins against any lingering `instance:N` label. **The sole
   resolver — consumers route through it.**
2. **The clash guard** (DEC-035 D6) — the ordinary-verb refusal and the same-instant
   lowest-wins back-off. **Resolves current ownership through the fold.**
3. **The signed listing** (DEC-035 D7) — `mine` / `other instance` / `unclaimed`.
   **Resolves through the fold.**
4. **The description-mirror renderer** — folds the log and full-overwrites the
   derived owner-mirror region in the issue body. **Resolves through the fold; is
   itself the sole constructor of the mirror region (site 6).**
5. **The ownership-event comment writer** — the one construction point for a
   claim / handoff / abandon / release comment (hidden stamp + human text). Every
   ownership mutation (`create-issue` claim, `start-work` commons-claim,
   `handoff-issue` push/pull, terminal release) obtains its event write **only by
   asking this writer**. **The sole constructor of the ownership-event comment.**
6. **The description-mirror regenerator** — the one construction point that writes
   the derived owner-mirror region by **full overwrite** from the folded log.
   **The sole constructor of the mirror region; never an append.**

The architecturally-significant pins, each carrying an alternative DEC-043 already
rejected or this ADR holds against:

1. **One ownership read seam** (consumers ask the fold) vs. each consumer
   re-scanning comments itself — the re-derivation ADR-026's one-reader discipline
   forbids, applied to the ownership axis; it would give authenticity-filtering and
   the fold N places to drift.
2. **Comment-log-wins as a seam invariant** over a mixed repo (lingering label +
   comment marker) vs. a per-consumer tie-break that could disagree across the
   guard, the listing, and the mirror — analogous to ADR-035's native-wins lifted
   to mixed-mode reconciliation.
3. **One construction point per side** (event comment; mirror region) vs. inline
   comment/body construction at each ownership-mutation site — the scatter
   ADR-031/ADR-035 converge for their substrates.
4. **Mirror render is a derived full-overwrite** (comment log the spine) vs. an
   authoritative body region (DEC-043 rejected the latter as a whole-object
   read-modify-write with no CAS; recorded here as a write-construction invariant,
   not re-litigated).

## Decision

**In plain terms:** ownership consumers stop scanning comments themselves and start
asking *one seam* "who owns this issue now?" The seam folds the append-only event
log — trusting only comments the expected account authored — to current ownership,
and over a repo that still carries an old `instance:N` label resolves
comment-log-wins. Every ownership *write* — the event comment, the description
mirror — is constructed in *one place*, the mirror always by full overwrite, never
appended. The mirror is a derived view; the comment log is the truth.

### 1. One ownership read seam — resolution lives in exactly one auditable place

"Who owns this issue now, and via which substrate?" is answered by a **single fold
seam**, not re-derived per consumer. The clash guard (DEC-035 D6), the signed
listing (DEC-035 D7), and the description-mirror renderer all resolve through it;
none re-scans comments directly. The seam takes an issue's already-fetched comment
set (plus any lingering label) and returns the resolved current owner, the
substrate it came from, and the authenticated event history.

This is ADR-026's one-reader discipline applied to the ownership axis: the
indirection — comment scan, `author.login` authenticity filter (DEC-043 D3),
append-only fold, comment-log-wins dedup — sits in one place where it can be
audited, tested, and reasoned about as a unit, and no second consumer re-derives
what one seam already resolves. A consumer re-scanning comments itself would (a)
duplicate the authenticity filter and the fold, and (b) give comment-log-wins and
the authenticity rule N places to drift instead of one to audit — exactly the
scatter the single seam exists to prevent. The seam owns the authenticity filter
too, so a consumer routing through it never trusts a forged marker.

### 2. Comment-log-wins as a seam invariant — and mixed-mode reconciliation

The seam folds the append-only log to current ownership, and over a mixed repo
resolves by a single rule: *a comment-log marker present for an issue is
authoritative; a coexisting lingering `instance:N` label is residual and does not
win.* This preserves DEC-035's ownership semantics under DEC-043's forward switch:

- **The fold is over an append-only sequence.** Claim, then handoff to another
  instance, then abandon, then a fresh claim — the seam folds to the *last
  authentic event's* owner (or unclaimed after an abandon/release), so history is
  preserved (DEC-043 D3) while a single current owner resolves. The same-instant
  clash (DEC-035 D6) holds unchanged: two clones each post their own event
  (per-object-atomic, no whole-object race), the re-read sees both, the
  higher-numbered instance backs off — lowest-wins computed identically by both
  clones from the folded log, exactly as it was from the labels.
- **Authenticity rides `author.login`.** A marker is trusted only if authored by the
  expected assignee account (DEC-043 D3) — stronger than the label substrate, where
  a label carries no actor. The seam is the one place this filter runs.
- **A repo may hold both substrates.** DEC-043's selector defaults to `comment`; a
  repo forward-switched from `label` (DEC-035's original mechanism) leaves lingering
  `instance:N` labels alongside new comment-log markers. **The seam resolves
  comment-log-wins** — the folded comment-log owner is authoritative, the lingering
  label is residual (to be stripped on the next ownership mutation, the same way
  DEC-035 D4 strips on terminal transitions). This is ADR-035's native-wins
  instinct at a new substrate boundary: the newer/authoritative substrate wins over
  the residual one, enforced **once, at the seam, over the union** — so the guard,
  the listing, and the mirror never disagree about a mixed repo.

State the invariant precisely: **comment-log-wins is enforced once, at the seam,
over the union of the comment log and any lingering label — so a mixed-substrate
repo resolves deterministically regardless of which consumer asks.** (The symmetric
case — selector `label` with a stray comment marker — resolves to the label per the
selector; that is not the motivating forward switch and the label mechanism stands
untouched per DEC-035. The seam reads per the selector; comment-log-wins is the
tie-break *within* the `comment`-mode union that the forward switch actually
produces.)

### 3. One write construction point per side — sole-constructor

Each ownership write has **exactly one construction point**, and every write routes
through it — ADR-031/ADR-035's sole-constructor discipline applied to a fourth
substrate:

- **The ownership-event comment** (claim / handoff / abandon / release, hidden
  stamp + human text) is constructed in one writer. A mutating script obtains an
  ownership event **only by asking it** — `create-issue`'s claim-at-birth (DEC-035
  D3), `start-work`'s commons-claim, `handoff-issue`'s push/pull/recursive modes
  (DEC-035 D4), and the terminal release all reuse the same construction point;
  none string-builds the stamped comment inline. The event log aligns with, and
  does not duplicate, the handoff audit comment
  [project-management:DEC-026](../../../.pkit/capabilities/project-management/decisions/DEC-026-work-ownership-lifecycle.md)
  already posts (DEC-043 D3).
- **The description-mirror region** is constructed in one regenerator that writes
  the region by **full overwrite** from the folded log — never a second writer, and
  **never an append** (point 4).

This is ADR-031/ADR-035's instinct at a new substrate boundary: a single auditable
construction point makes "no script string-builds an ownership write inline" a
*structural* property (there is no other way to build the write) rather than a
*remembered* one. The ownership writes are distinct operations from the three prior
seams' (a stamped `gh issue comment` and a body-region overwrite, not a label, a
`gh project item-edit` / `--milestone`, or a `gh api …/sub_issues`), so they get
**their own** construction points and **their own** grep/AST guard — **not a
widening of ADR-026/ADR-031/ADR-035's covered sets.** All three prior invariants
stay scoped to their own substrates.

### 4. The description mirror is derived full-overwrite, never append, never authoritative

The description mirror is a **derived view the read seam regenerates by full
overwrite** from the folded log — the comment log is its regeneration spine
(DEC-043 D4). It is therefore safe to full-overwrite: if a human edits or deletes
the region, or a write races, the seam regenerates it from the log and **no
ownership record is lost**, because the mirror was never the truth. The one
construction point (point 3) writes by **overwrite**, never by append — a
per-instance append to a shared body region would be the whole-object
read-modify-write with no compare-and-set that DEC-043 rejected for an
authoritative body substrate (concurrent claims clobber; lowest-wins degrades to
last-writer-wins).

This is the [project-management:DEC-039](../../../.pkit/capabilities/project-management/decisions/DEC-039-containment-substrate-selection.md)
D4 / ADR-035 point 4 pattern — a generated, regenerable view whose truth lives
elsewhere — with the roles swapped from ADR-035: there the *comments* are the
render-on-demand view and the native panel / child-side ref is the spine; here the
*comments* are authoritative and the *body region* is the view. The direction
differs; the invariant (derived view, single-source full-overwrite, spine
elsewhere) is the same.

### 5. Failure-posture neutrality — the constructors report, the caller decides

Both construction points and the fold are **failure-posture-neutral**, in the same
spirit as ADR-031 point 6 and ADR-035 point 3. They construct/execute/fold and
report a neutral outcome; **each caller imposes its own posture**:

- **The ownership-event comment writer** reports `WROTE` / `FAILED`. The
  **claim path** re-reads after writing (DEC-035 D6) and, on seeing a
  lower-numbered instance's event, reads `RACED-LOST` from the fold and **backs
  off** (posts an abandon event, notifies); a **handoff** treats `WROTE` as success
  and moves on; a **durability-check** path treats `FAILED` as a retryable
  substrate error. The writer takes no view on which — the posture is the caller's.
- **The description-mirror regenerator** reports `WROTE` / `CLOBBERED` (the region
  had drifted — a human edit, a deletion, or a racing write — and was regenerated
  by full overwrite) / `FAILED`. The **routine render** treats `CLOBBERED` as
  *expected and benign* (the mirror is derived; regeneration is its whole job) and
  does not alarm; a **reconcile/durability report** may surface the `CLOBBERED`
  count as drift observed-and-healed. Same construction, different posture per
  caller.

This is what lets the claim / back-off / handoff / reconcile callers coexist behind
one set of constructors without any inheriting another's posture — construction and
fold are one concern (the seam's), failure-handling is another (the caller's), and
they live at different layers. If a constructor baked in a posture, the back-off
path would inherit the claim path's, or the reconcile report would inherit the
routine render's — the exact miscoupling neutrality prevents.

### 6. Realm-blindness — the seam feeds only the pm-layer guard, never the fold

The ownership fold is a **pm-domain read** with **pm-domain consumers only** — the
clash guard, the signed listing, the mirror renderer. Instance ownership remains,
per DEC-035 D8 and DEC-043 D6, **never an input to a gate, a transition, or the
cascade fold**
([project-management:DEC-034](../../../.pkit/capabilities/project-management/decisions/DEC-034-cascade-slot-binding.md),
COR-037's process-cascade). This is the deliberate *inverse* of ADR-035, where the
DEC-034 closure-fold child-walk is one of the containment seam's consumers: there,
membership is engine-relevant and the fold reads it through the seam; here,
ownership is **not** engine-relevant and the cascade fold must **not** read it. The
ownership seam's consumer set is closed to the pm layer; wiring it into the engine
fold would cross the content-free boundary COR-037 holds and require its own
authorisation (DEC-035 Implications). The engine and its cascade predicates stay
realm-blind.

### Boundaries — what this contract is NOT

- **Not the selector schema.** How instance-ownership's schema home spells the
  `label | comment` selector (default `comment`) is DEC-043 D2 schema work that
  lands with the Feature — explicitly **not** a slot in `substrate-map.yaml`
  (DEC-043 D2), so an ownership-only opt-in does not trip DEC-036's emergent
  activation. This ADR pins the resolution + construction contract, not the
  selector field.
- **Not the comment-stamp or mirror-region format.** The hidden-stamp syntax and
  the mirror region's rendered shape are carried by the shared audit-log facility's
  own DEC ([project-management:DEC-044-audit-log-facility]; DEC-043 Implications: "the
  ownership event log is that facility specialised") and land with the Feature. This ADR pins only that the event write
  and the mirror render each have one constructor and that the mirror is
  overwrite-not-append.
- **Not the DEC-009 refinement note.** The description-mirror region is a
  capability-owned, do-not-edit, **derived** class of body content that
  [project-management:DEC-009](../../../.pkit/capabilities/project-management/decisions/DEC-009-living-documents.md)
  does not yet model (its wording-free / scope-gated / ticks-sticky rules assume
  human-or-PM-authored body content; a *derived, regenerated* region is a lighter,
  distinct class — a human edit to it is not a gated scope edit, it is simply
  overwritten on next render, safely, because the region is derived). DEC-043
  Implications names the reciprocal DEC-009 refinement note as a **separate
  change-set item**; this ADR references the boundary and does **not** author that
  note.
- **Not a DEC-035 supersession.** DEC-035's label mechanism, the
  `(assignee, instance:N)` owner, and the clash-guard semantics all stand; DEC-043
  *refined* DEC-035 to substrate-*where-available* (refinement-in-place, reciprocal
  note on DEC-035) and this ADR pins how the comment substrate resolves.
  Comment-log-wins is DEC-035's lowest-wins tie-break preserved atop per-object
  atomic writes and lifted to a mixed-mode invariant, not a replacement.
- **Not auto-selection.** The selector is a manual operator declaration defaulting
  to `comment` (DEC-043 D2); this ADR pins no auto-detection of label-creatability.
  The seam resolves comment-log-wins over the mixed union the forward switch
  produces regardless.
- **Not a label / field / containment contract change.** ADR-026's label invariant,
  ADR-031's field/milestone invariant, and ADR-035's containment invariant stay
  scoped to their own substrates. This is a fourth substrate with its own seam,
  its own two constructors, and its own guard.

## Rationale

**Why one read seam, not per-consumer comment scans.** Resolving the current owner
is a cross-cutting concern — three consumers need it (clash guard, signed listing,
mirror renderer) and the *same* logic (authenticity filter + append-only fold +
comment-log-wins dedup) must behave identically across all of them. A concern that
must be uniform across many consumers belongs at one boundary, not copied into
each. Three consumers each scanning comments would give the `author.login`
authenticity rule and comment-log-wins three places to drift and triplicate the
fold — the exact scatter ADR-026's one-reader discipline exists to prevent, here on
the ownership axis. One seam is the COR-007 "extract the shared shape" move applied
to ownership resolution; the third consumer arriving (the mirror renderer, after
the guard and the listing) earns the extraction under COR-007's recurrence test
rather than speculative generality.

**Why comment-log-wins as a seam invariant, and why mixed-mode matters.** DEC-043's
selector is a forward switch, so a real repo can carry both a lingering `instance:N`
label and a comment-log marker at once — the switch is not atomic, and a
label-mode repo that adopts the comment default leaves its old labels in place.
If the tie-break were per-consumer, the clash guard could refuse on the stale label
while the signed listing reads the comment-log owner and the mirror renders a third
answer, during the mixed window. Enforcing comment-log-wins **once at the seam over
the union** makes the mixed repo resolve deterministically for every consumer — the
property that makes the forward switch safe. Comment-log-wins (not label-wins) is
the right direction because the comment log is the authenticity-bearing,
per-object-atomic, history-preserving substrate DEC-043 chose as source of truth;
the label is the residual DEC-035 artifact the switch is leaving behind.

**Why one construction point per side.** "Construct the ownership write in exactly
one place" is the same architectural property ADR-031 made load-bearing for
field/milestone writes and ADR-035 for containment: a single auditable point makes
the invariant *structural* rather than *remembered*. With `create-issue`,
`start-work`, `handoff-issue`'s three modes, and terminal release all writing
ownership events, and every read regenerating the mirror, the un-converged world
would have an event comment buildable at every mutation site and a mirror writable
at every render — N places for the guard to fail to cover, N for a future author to
mis-stamp the comment or mis-overwrite the region. One constructor per side and one
guard collapse that. Giving ownership its *own* construction points and guard
(rather than widening a prior seam) keeps each substrate's invariant precise: an
ownership write is a stamped comment / a body-region overwrite, not any of the
three prior substrates' operations, and folding it into a prior seam would overload
that seam with an operation its drivers never invoke.

**Why the mirror is derived full-overwrite, not an authoritative or appended body
region.** DEC-043 pressure-tested and rejected an authoritative body region: a
whole-object read-modify-write with no compare-and-set, so concurrent claims
clobber and lowest-wins degrades to last-writer-wins — the silent double-work the
guard exists to prevent. A per-instance *append* to a shared region has the same
whole-object race. The only thing the body region should add beyond the comment log
is at-a-glance visibility of the current owner (DEC-043 Rationale) — and rendering
it on demand by full overwrite from the log delivers exactly that with none of the
concurrency failure modes, precisely *because* it is not the source of truth. This
is DEC-039 D4 / ADR-035 point 4's separation of the visibility goal from the
storage decision; only visibility is wanted.

**Why failure-posture neutrality.** The callers have genuinely different correct
postures — the claim path must back off on `RACED-LOST` (DEC-035 D6), the handoff
path must not, the routine render must treat a `CLOBBERED` mirror as benign, and a
reconcile report may surface it as healed drift. Baking any one posture into a
constructor would force another caller to wear a posture its path rejects — a
claim writer that swallowed the race would break lowest-wins; a mirror renderer
that alarmed on every regeneration would make the derived region look broken.
Neutrality keeps construction/fold (the seam's job) orthogonal to failure-handling
(the caller's job), the same separation ADR-031 and ADR-035 draw for their
substrates.

**Why realm-blindness, stated as a non-consumer.** ADR-035's containment seam feeds
the cascade fold because membership *is* engine state; ownership is deliberately
*not* (DEC-035 D8, COR-037's content-free substrate). Naming the engine fold as an
explicit **non-consumer** of the ownership seam is what keeps the boundary from
eroding the way a convenient "close only my realm's children" feature would erode
it — that would feed ownership into the fold and cross the content-free boundary,
requiring its own authorisation. The pm-layer-only consumer set is the boundary,
enforced by the seam having no engine-side caller.

### Alternatives considered

- **Each consumer re-scans comments itself** (no read seam). Rejected — triplicates
  the `author.login` authenticity filter and the append-only fold, gives
  comment-log-wins three places to drift, and lets the guard, listing, and mirror
  disagree about a mixed repo. The one-reader discipline (ADR-026) on the ownership
  axis is the fix.
- **Comment-log-wins as a per-consumer tie-break** rather than a seam invariant.
  Rejected — during the forward-switch mixed window the guard could refuse on the
  stale label while the listing and mirror read the comment-log owner. Enforcing it
  once at the seam over the union resolves the repo deterministically for every
  consumer.
- **Label-wins over the comment log** in mixed mode. Rejected — the label is the
  residual substrate the forward switch is leaving; the comment log is the
  authenticity-bearing, per-object-atomic, history-preserving source of truth
  DEC-043 chose. Comment-log-wins is the only direction consistent with the switch.
- **Authoritative body region as the source of truth** (no comment log). Rejected
  by DEC-043 — whole-object read-modify-write with no CAS; concurrent claims clobber
  and lowest-wins degrades to last-writer-wins. Kept only as a *derived* mirror
  (point 4).
- **Per-instance append to the mirror region** instead of full overwrite. Rejected
  — the same whole-object race as the authoritative region, on every claim.
  Full-overwrite of a derived region regenerated from the log carries no such race.
- **Inline event-comment / mirror construction at each ownership-mutation site** (no
  sole-constructor). Rejected — re-grows the scatter ADR-031/ADR-035 converge for
  their substrates; gives the invariant N places to drift and the guard N shapes to
  chase.
- **Widen a prior seam** (ADR-031's write seam or ADR-035's containment seam) to
  cover ownership. Rejected — an ownership write is a distinct operation (stamped
  comment / body-region overwrite); folding it in overloads that seam with an
  operation its drivers never invoke and forces its guard to allow a fourth shape.
  Ownership gets its own constructors and guard; the prior invariants stay scoped.
- **Feed the ownership fold into the cascade closure fold** (a "close only my
  realm's children" convenience). Rejected — crosses the content-free engine
  boundary COR-037 holds (DEC-035 D8); if ever wanted it needs its own
  authorisation, not a quiet widening of this seam's consumer set.

## Implications

- **One ownership read seam** (an ownership-substrate `_lib` fold) that the clash
  guard (DEC-035 D6), the signed listing (DEC-035 D7), and the description-mirror
  renderer resolve through; no consumer re-scans comments directly. Reads the
  issue's comments (returned inline by the one corpus read, DEC-043 Implications),
  filters by `author.login` authenticity (DEC-043 D3), and folds the append-only
  claim/handoff/abandon/release sequence to current ownership. Lands with the
  Feature (DEC-043-gated), citing this ADR.
- **Comment-log-wins is a seam invariant over the union of both substrates** — a
  comment-log marker is authoritative; a coexisting lingering `instance:N` label is
  residual and does not win, and is stripped on the next ownership mutation (DEC-035
  D4). This makes a **forward-switched (label→comment) repo** resolve
  deterministically for every consumer. It is DEC-035's lowest-wins tie-break
  preserved atop per-object-atomic comment writes and lifted to a mixed-mode
  reconciliation invariant.
- **One write construction point per side, under one grep/AST guard** — the
  ownership-event comment writer (claim/handoff/abandon/release, hidden stamp +
  human text; reused by `create-issue`, `start-work`, `handoff-issue`, terminal
  release) and the description-mirror regenerator (full overwrite from the folded
  log). The guard is the two-half shape ADR-031/ADR-035 hold: (a) a **construction
  test** — the writers construct/execute the covered writes and the ownership
  mutation sites obtain their write *from* them; **and** (b) a **grep/AST scan-all**
  — no script string-builds a stamped ownership-event comment or a mirror-region
  overwrite inline except the two constructors. Its own module and its own guard —
  **not a widening of ADR-026 / ADR-031 / ADR-035's covered sets.**
- **The description mirror is a derived, single-source full-overwrite, never an
  append, never authoritative** (DEC-043 D4) — the comment log is its regeneration
  spine, so a stray human edit, deletion, or racing write is regenerated with no
  ownership record lost. This is DEC-039 D4 / ADR-035 point 4 with the comment/body
  roles swapped.
- **The constructors and fold are failure-posture-neutral** (ADR-031 point 6 /
  ADR-035 point 3 spirit): the event writer reports `WROTE` / `FAILED` (the claim
  path reads `RACED-LOST` from the re-read fold and backs off, DEC-035 D6; handoff
  and durability-check paths impose their own posture); the mirror regenerator
  reports `WROTE` / `CLOBBERED-regenerated` / `FAILED` (routine render treats
  `CLOBBERED` as benign; a reconcile report may surface it as healed drift).
  Construction/fold and failure-handling live at different layers. Confirm at impl
  that the result types carry enough detail for every caller's posture.
- **Realm-blindness — the seam has pm-layer consumers only.** The clash guard, the
  signed listing, and the mirror renderer consume the fold; the engine and its
  cascade predicates (DEC-034, COR-037) explicitly **do not** — the inverse of
  ADR-035, where the closure fold *is* a containment-seam consumer. Wiring
  ownership into the engine fold would cross the content-free boundary and require
  its own authorisation (DEC-035 D8 / DEC-035 Implications).
- **DEC-009 boundary — reciprocal note is a separate change-set item.** The
  description-mirror region is a capability-owned, do-not-edit, **derived** class of
  body content DEC-009 does not yet model (lighter than the authoritative,
  scope-gated body content DEC-009 governs — a human edit is overwritten on next
  render, not gated). DEC-043 Implications names the reciprocal DEC-009 refinement
  note as a separate change-set item; this ADR references the boundary and does not
  author it.
- **The selector schema, comment-stamp format, and mirror-region UX are Feature
  work** (DEC-043-gated), citing DEC-043 — the `label | comment` selector in
  instance-ownership's own schema home (default `comment`, **not** in
  `substrate-map.yaml`, DEC-043 D2), the hidden-stamp syntax and the mirror region's
  rendered shape (carried by the shared audit-log facility's DEC). This ADR pins the
  resolution + construction contract, not the schema or the UX.
- **Relationship to records — no DEC-035 or DEC-043 amendment needed.** Records the
  comment-substrate contract DEC-043 named as its ADR follow-up (the fourth sibling
  to ADR-026 read-path / ADR-031 write-path / ADR-035 containment). **DEC-035 is not
  superseded** — its label mechanism and clash-guard semantics stand; DEC-043
  refined it to substrate-*where-available* and this ADR pins how the comment
  substrate resolves; comment-log-wins is DEC-035's lowest-wins tie-break lifted to
  a mixed-mode invariant. Inherits ADR-026's one-reader discipline at a new boundary
  (the ownership fold), ADR-031/ADR-035's sole-constructor + grep/AST guard
  discipline at a fourth substrate (the event comment and the mirror region), and
  DEC-039 D4 / ADR-035 point 4's derived-view pattern (roles swapped) — with all
  three prior seam invariants staying scoped to their own substrates. Composes with
  DEC-014 (the guard's severity token) and DEC-026 (the event log aligns with the
  handoff audit comment). Does not restate DEC-043; cites it as the decision.
- **Acceptance.** Because this ADR pins the contract for a substrate that **refines
  the foundational DEC-035** (via DEC-043), it required **explicit maintainer
  sign-off** rather than architect self-acceptance — the same class as DEC-035's own
  handoff-contract sign-off, DEC-039's DEC-005 refinement, and DEC-043's DEC-035
  refinement. That sign-off was given in-session by the maintainer, and this record
  was accepted alongside DEC-043 / DEC-044 / DEC-045 in the same change-set. The seam,
  the two constructors, the guard, and the drivers land with the DEC-043-gated
  Feature, citing this ADR for the invariant.
