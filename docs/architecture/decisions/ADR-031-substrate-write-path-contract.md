---
id: ADR-031
title: Construct every non-label substrate write through one sole-constructor module
status: accepted
date: 2026-06-25
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** four scattered places in the code today hand-build a GitHub command to write a Projects-v2 field or a milestone onto an issue. This contract says they all stop doing that and instead call **one shared module** that builds the write. That module just builds-and-runs the command and reports what happened — it takes no view on what to do if the write fails or whether to skip; that view belongs to whoever called it (a per-event hook keeps its own behaviour; the bulk back-fill keeps its own, stricter behaviour). A guard test then checks that nobody hand-builds those commands anywhere except the one module. That is the whole decision; everything below is the rigor behind it.

[project-management:DEC-037](../../../.pkit/capabilities/project-management/decisions/DEC-037-adoption-ceremony.md)
decided the *write side of brownfield adoption* — the one-time corpus back-fill,
the per-create adopter default, and the `adopt-existing` ceremony that drafts
them. Two of those write **non-label substrates**: a Projects-v2 single-select
field value (AUJ's `workstream=Spyre`) and a milestone assignment. This ADR
records the **write-path contract** DEC-037 named as its ADR follow-up — the
non-label, write-side twin of [ADR-026](ADR-026-substrate-map-read-path-contract.md)'s
label read-path/sole-constructor contract: **how** those substrate writes are
constructed, and the one structural invariant that construction must never
violate. It is the on-call/maintainer reference for the write primitive that
lands ahead of the trunk back-fill Feature; it pins the contract, not the
back-fill UX or the `adopt-existing` inventory shape (those land with the
Feature, citing DEC-037).

**The contract, in one breath:** each covered non-label substrate has **exactly
one construction point** — a single `_lib` module function builds the Projects-v2
field-value write (`gh project item-edit`) and the milestone write
(`gh issue edit --milestone` *and* `gh issue create --milestone`), and **every**
write of those substrates routes through it. This is **convergence, not
greenfield**: the substrate is already constructed inline in *four* scattered
sites today (DEC-024's `set-board-field` and `assign-milestone` hook handlers;
`create-issue.py`'s own milestone write; the `_gh_add_to_board` board-*membership*
write — which is **named out**). The two DEC-024 hook handlers route *through*
the new primitive, the per-create default and the one-time back-fill drive the
*same* primitive, and a grep/AST guard analogous to ADR-026's holds "no script
string-builds these `gh` substrate calls inline except the sole-constructor
module."

**The load-bearing invariant — one constructor per substrate, and it is
failure-posture-neutral.** Two halves, structural only together: (i) **a script
writes a covered substrate only by asking the primitive** — it never string-builds
the `gh project item-edit` / `gh issue …--milestone` argv inline, so the primitive
is the *sole constructor* of that substrate write (parallel to ADR-026 part (i),
for labels); and (ii) **the primitive itself imposes no failure posture** — it
constructs and executes the write and reports the outcome, and **each driver
imposes its own posture on top**. The per-event DEC-024 hooks keep their
report-and-continue (DEC-024's "primary op already succeeded; log the partial,
exit 0"); the one-time bulk back-fill imposes the stricter audited posture of
DEC-037 (re-validate per-issue at apply, skip-and-report on drift). Half (ii) is
what lets DEC-024's per-event semantics and the back-fill's bulk semantics coexist
behind one constructor without either inheriting the other's posture — the
posture is the *driver's* decision, the *construction* is the primitive's. This
is ADR-026's sole-constructor instinct at a new, non-label boundary; ADR-026's
own invariant stays **label-scoped** and untouched, and **DEC-024 is not
superseded** — its hooks engine and kind taxonomy stand; this pins only *how*
its field/milestone kinds construct their write.

## Context

DEC-037 settled the brownfield write-side ceremonies and explicitly deferred the
write primitive's contract to a sibling ADR at implementation time: *"the
write-path contract for non-label substrates (sole-constructor pin + guard + the
four back-fill safety properties as write-path invariants) lands as a sibling ADR
to ADR-026, authored by the architect at implementation time once this record is
accepted … Its Context enumerates the existing construction sites the way ADR-026
enumerated its label sites."* DEC-037 is now `accepted`; this is that ADR, and
its three precision notes (supplied in the DEC-037 amendment review) are the
spine of this Context.

The grounding case is the same `agentic-user-journey` (AUJ) brownfield repo
ADR-026 served: every existing issue's Projects-v2 `workstream` field set to
`Spyre` (an adopter-specific value, not a kit vocabulary), and a time-based
milestone assigned across the corpus — plus every *new* issue seeding the same
`workstream=Spyre` default going forward. `workstream` here is **not** a label;
it is a Projects-v2 single-select field. Milestones are a third substrate again.
ADR-026's label seam constructs **labels only** — a `default:` on a field-bound
or milestone axis fail-closes through `resolve_write` to a dropped label and
never reaches the corpus through the label path (DEC-037 §3). So the field and
milestone writes are a genuinely distinct substrate path, and this ADR is its
construction contract.

**The existing construction sites — the convergence surface.** Exactly as ADR-026
enumerated ~26 inline label-literal sites, this Context enumerates the non-label
substrate sites that exist *today*, scattered, each string-building `gh` argv
inline. As project-kit's own capability-architecture record, concrete site names
are in scope (per
[PRJ-005](../../../.pkit/decisions/project/PRJ-005-adopt-adrs.md)); the back-fill
UX, the `adopt-existing` inventory shape, and the `substrate-map.yaml` field
layout are not — they land with the trunk Feature, citing DEC-037. The sites:

1. **`_hook_set_board_field`** (`_lib/hooks.py`, ~L300-321) — builds the
   Projects-v2 field-value write `gh project item-edit --id … --field-id …
   [--single-select-option-id … | --text …]` inline. The DEC-024 `set-board-field`
   kind handler. **Covered — routes through the primitive.**
2. **`_hook_assign_milestone`** (`_lib/hooks.py`, ~L439-453) — builds the milestone
   write `gh issue edit <n> --milestone <title>` inline. The DEC-024
   `assign-milestone` kind handler. **Covered — routes through the primitive.**
3. **`create-issue.py`'s own milestone write** (`gh issue create --milestone`,
   L787-788) — the **fourth site the "~3" tally in DEC-037's earlier prose
   understated**: `create-issue` sets a milestone *at create time* via a
   `--milestone` flag on the create call itself, a milestone-assignment
   construction distinct from the hook handler's post-hoc `gh issue edit`. Same
   substrate (milestone), different `gh` verb and call site. **Covered — routes
   through the primitive** (the primitive must therefore express milestone
   assignment in both its at-create and post-hoc forms, or `create-issue` calls
   the primitive after create rather than via the flag; the Feature picks the
   mechanic, the contract requires the routing).
4. **`_gh_add_to_board`** (`create-issue.py`, ~L805, `gh project item-add`) —
   adds an issue *to* a board: **placement / membership**, per
   [project-management:DEC-019](../../../.pkit/capabilities/project-management/decisions/DEC-019-mandatory-issue-state.md).
   This is **named OUT** of the contract (DEC-037 §3 provisional read, confirmed
   here): item-*add* is a distinct operation from item-*edit*-a-field-value — it
   establishes board membership, it does not write an attribute *value* onto an
   existing item. The two covered substrates are **field-value** and
   **milestone**; board-membership is its own operation with its own (single) site
   and is not subsumed. The guard's allow-list must name this boundary precisely
   (Implications, guard half (b)).

The architecturally-significant pins, each carrying an alternative DEC-037 already
rejected or this ADR holds against:

1. **One sole-constructor module per covered substrate** vs. the present scatter
   (four inline sites) vs. a *second* allow-listed inline constructor in
   `hooks.py` (the very thing ADR-026 forbids for labels — DEC-037 §3).
2. **Convergence, not greenfield** — the existing sites route *through* the
   primitive; this is a refactor over the DEC-024 engine with that blast radius,
   not a leaf add (DEC-037 Implications sizes it so).
3. **Failure-posture neutrality** — the primitive imposes no posture; each driver
   imposes its own (DEC-024 report-and-continue per-event; the back-fill's audited
   skip/report bulk) vs. baking one posture into the constructor (which would force
   the other driver to inherit a wrong posture).
4. **The four DEC-037 back-fill safety properties as write-path invariants** —
   re-validate-at-apply, value-equality idempotency, residual-pre-check gate,
   `--emit-script` draft-not-apply — recast as this ADR's write-path analogue of
   ADR-026's read-path fail-closed posture.

## Decision

**In plain terms:** the four scattered places that string-build a `gh` field or
milestone write today stop doing that and start calling *one module* that
constructs the write. The module just constructs-and-runs and reports what
happened — it takes no opinion on what to do when the write fails or whether to
skip; that opinion belongs to whoever called it (a per-event hook, or the bulk
back-fill), each of which keeps its own. A guard then checks that nobody builds
these `gh` calls inline except that one module.

### 1. Sole-constructor invariant for non-label substrate writes

Each covered non-label substrate — **a Projects-v2 single-select/text field
value** (`gh project item-edit`) and **a milestone assignment** (`gh issue edit
--milestone` *and* `gh issue create --milestone`) — has **exactly one construction
point**: a single `_lib` module function builds and executes the `gh` write. A
mutating script obtains that write **only by asking the primitive**; it **never**
string-builds the `gh project item-edit` / `gh issue …--milestone` argv inline.

This is the direct parallel of ADR-026's label sole-constructor (part (i)): there,
the seam is the only place an axis label is constructed on a write path; here, the
primitive is the only place a field-value or milestone write is constructed. The
substrate differs (Projects-v2 field / milestone, not a label), so this is a
*separate* construction point with its own guard — **ADR-026's invariant stays
label-scoped and is not violated** (a field write is a different substrate path,
not a label the seam should construct, exactly as DEC-037 §3 holds). Milestone
spans two `gh` verbs (`issue edit` post-hoc, `issue create --milestone` at create
time); both are the *same substrate* and both route through the one milestone
construction point — the primitive expresses milestone assignment, and the call
site chooses when it fires, not whether it constructs inline.

### 2. Convergence, not greenfield

This is **not** a fresh constructor added onto a clean substrate. The substrate is
**already constructed in four scattered sites** (Context above) — the pre-ADR-026
condition for labels (~26 sites), now standing for fields/milestones. ADR-026
learned that "single construction point" *stated but unenforced* is provisioned,
not structural; here it is worse — the substrate is *already scattered* across
DEC-024's two hook handlers, `create-issue`'s own milestone write, and (for the
named-out membership operation) `_gh_add_to_board`. So the requirement is
convergence:

- **DEC-024's two kind handlers route THROUGH the primitive.** `_hook_set_board_field`
  and `_hook_assign_milestone` stop string-building `gh` inline and call the
  primitive instead. A *second* allow-listed inline constructor living in
  `hooks.py` is precisely what ADR-026 forbids for labels — the guard cannot hold
  the invariant honestly while a sanctioned inline site persists.
- **`create-issue`'s own milestone write routes through it too** (the fourth site).
- **Both new drive sites route through it** — the per-create adopter default
  (DEC-037 §3) and the one-time corpus back-fill (DEC-037 §2) construct their
  writes via the same primitive, the back-fill driving it bulk over the corpus
  where DEC-024 fires it per-event.

This makes the write-primitive task a **refactor over the DEC-024 engine**, not a
leaf add — sized with the regression surface that implies (DEC-037 Implications).
The guard (point 4) is its regression net, continuously verifying the convergence
stays done.

### 3. Board-membership is named OUT

`_gh_add_to_board` (`gh project item-add`, per DEC-019) is **outside this
contract**. Adding an issue *to* a board is **placement / membership** — it
establishes that an item exists on the board; it does **not** write an attribute
*value* onto an existing item. The two covered substrates are field-value and
milestone (the attribute writes); board-membership is a distinct operation with
its own single site, neither subsumed by nor in tension with the field-value
constructor it sits near in `create-issue.py`.

The boundary matters for the guard: the allow-list must distinguish
`gh project item-edit` (field-value write — covered, sole-constructor-only) from
`gh project item-add` (membership — out of scope, its own site). A guard that
keyed on `gh project` broadly would either wrongly flag the legitimate
`_gh_add_to_board` membership site or wrongly allow a stray inline field-value
write. The guard keys on the *operation* (`item-edit` field-value; `issue
…--milestone`), not the `gh project` prefix.

### 4. The guard — sole-constructor, enforced by a grep/AST check

The invariant is a **tested property**, not a convention — the same two-half shape
as ADR-026's guard. State both halves:

**The premise (half a — the construction test).** The primitive is the only place
a covered substrate write is constructed: a test asserts the primitive constructs
and executes the `gh project item-edit` field-value write and the `gh issue
…--milestone` write, and that the converged call sites (the two DEC-024 handlers,
`create-issue`'s milestone write, the back-fill driver, the per-create default)
obtain their write *from* the primitive rather than string-building it.

**The enforcing test (half b — the grep/AST guard).** A grep/AST check asserts
**no script string-builds these substrate writes inline except the
sole-constructor module** — no `gh project item-edit … --field-id` argv and no
`gh issue … --milestone` argv constructed as a list/format-string anywhere but the
primitive. This is the analogue of ADR-026's "no inline `<axis>:<value>` literal"
and of ADR-024's "`render_status_json` never calls `wrap()`": the structural half
that makes the invariant real. Without half (b), half (a) passes while a stray
inline `gh issue edit --milestone` in some future handler bypasses the primitive
entirely — exactly the four-site scatter this ADR converges, re-growing
unnoticed.

**The allow-list is precise about board-membership (point 3).** `_gh_add_to_board`'s
`gh project item-add` is *not* a covered write and must not trip the guard; the
guard keys on `item-edit` field-value and `issue …--milestone`, leaving `item-add`
membership alone. The sole-constructor module is the one allow-listed exception for
the covered writes; `_gh_add_to_board` is out of scope, not allow-listed-as-exception.

### 5. The four back-fill safety properties as WRITE-PATH invariants

ADR-026 expressed its safety as a read-path posture (fail closed to a *read*, never
open to a *write*). The write-path analogue is DEC-037 §2's four properties, recast
here as invariants the write primitive's *bulk driver* must satisfy — the write-side
twin of ADR-026's fail-closed:

- **Re-validate at apply (skip + report drift).** The back-fill enumerates each
  issue's state at plan time, but the human reviews for minutes-to-hours during
  which issues may be edited concurrently. Each per-issue write **re-reads that
  issue's current state immediately before applying** and, if it has drifted from
  the enumerated plan, **skips and reports the skip** rather than overwriting against
  stale enumeration. The plan is a proposal, not a committed write set. This is the
  write-path fail-closed: an indeterminate/drifted issue fails closed to *skip*,
  never open to a blind overwrite.
- **Per-issue value-equality idempotency.** "Already done" is detected by
  **value-equality on the target attribute** (this issue's field already equals the
  target value; this issue's milestone already equals the target), not mere presence.
  A re-run after a partial apply (an interrupted bulk loop) is a no-op for the
  already-applied issues and completes the rest. Per-issue grain — finer than
  DEC-017's manifest-entry-grain tracking — because the unit of human-owned state is
  the individual issue. (DEC-024's per-event kinds already declare idempotency; the
  bulk driver lifts it to value-equality across the corpus.)
- **Residual-pre-check gate.** The back-fill refuses on the subset of `pre-check`
  that still hard-fails in brownfield (DEC-036 made `pre-check` degrade to a
  capability matrix rather than hard-refuse): `gh` auth invalid, repo inaccessible,
  or `substrate-map.yaml` fails to parse. Those break the plan's assumptions; a
  merely-degraded axis does not.
- **`--emit-script` draft-not-apply.** The bulk driver supports emitting the reviewed
  mutations as an idempotent script the adopter runs themselves, the symmetric
  draft-not-apply form (parallel to `adopt-existing`'s draft-not-apply). This hands
  apply-timing to the human and closes the report→apply window for adopters who use
  it.

These are invariants of the **bulk back-fill driver**, not of the primitive itself
(point 6) — the primitive constructs-and-runs one write; the bulk driver wraps it in
re-validate/idempotency/gate/draft. They are the write-side expression of DEC-037's
"bulk-mutating real human-owned issues is the highest-blast-radius operation pm
performs."

### 6. Failure-posture neutrality

The shared constructor is **failure-posture-neutral.** It constructs the `gh` write,
executes it, and reports the outcome (success / the failure detail). It does **not**
decide what happens on failure, whether to skip, whether to roll back, or what exit
code to surface — **each driver imposes its own posture on top**:

- **The per-event DEC-024 hooks keep report-and-continue.** When a hook's write fails
  *after* the primary operation succeeded, the hook reports to stderr, exits 0, logs
  the partial — DEC-024's failure semantics, unchanged. The primitive hands the hook
  a failure result; the hook applies DEC-024's posture to it.
- **The bulk back-fill imposes the stricter audited posture** of point 5 —
  re-validate-at-apply, skip-and-report on drift, value-equality idempotency. The
  primitive hands the bulk driver the same kind of result; the driver applies the
  back-fill's posture (skip, report, continue the loop).

This is what lets DEC-024's per-event semantics and the back-fill's bulk semantics
**coexist cleanly behind one constructor.** If the primitive baked in a posture, the
other driver would inherit a wrong one — a back-fill built on a report-and-continue
constructor would silently swallow per-issue failures the audit must surface; a
per-event hook built on a skip-and-report-bulk constructor would mis-handle a
single-write failure. Neutrality keeps construction (the primitive's job) orthogonal
to posture (the driver's job) — the same separation DEC-024 already draws between the
*engine* firing a hook and the *hook kind* deciding its own idempotency. Construction
is one concern, failure-handling is another, and they live at different layers.

### Boundaries — what this contract is NOT

- **Not the back-fill UX or the `adopt-existing` inventory shape.** How the report
  enumerates, how `adopt-existing` inventories the live repo and drafts the map —
  those land with the trunk Feature (DEC-037), not here. This ADR pins the write
  *primitive* and the safety *invariants*, not the ceremony surface.
- **Not the `substrate-map.yaml` field layout.** How the map spells a per-axis
  `default:` or a field binding is DEC-036/DEC-037 schema work; this ADR pins only
  that the default's *non-label* emission routes through the primitive.
- **Not a board-membership redesign.** `_gh_add_to_board` is named out (point 3); its
  shape is unchanged. This contract neither subsumes nor re-founds membership.
- **Not a DEC-024 supersession.** DEC-024's hooks engine, kind taxonomy, lifecycle
  events, and `custom-script` escape hatch all stand. This pins only how the
  `set-board-field` / `assign-milestone` kinds *construct* their write (routing them
  through the primitive) — the engine fires them exactly as before.
- **Not a label-contract change.** ADR-026's sole-constructor invariant stays
  label-scoped. This is the non-label, write-side twin, with its own substrate, its
  own constructor, and its own guard.

## Rationale

**Why one constructor per substrate, not the four inline sites.** "Construct the
non-label substrate write in exactly one place" is the same architectural property
ADR-026 made load-bearing for labels: a single auditable point makes the invariant
*structural* (there is no other way to build the write) rather than *remembered* (do
not string-build the wrong `gh` argv at each site). With four inline sites today and
two new drivers incoming, the un-converged world has six places the substrate write
can be built — six places for the guard to fail to cover, six places for a future
author to mis-spell the `gh` call. Convergence collapses that to one constructor and
one guard. This is the COR-007 "extract the shared shape" move ADR-026 already
applied to labels, applied now to fields/milestones — and DEC-037 §3 already named it
the convergence half of what ADR-026 did, not a fresh add.

**Why convergence is a refactor, not a leaf add — and why that sizing matters.** A
leaf add (a new module nothing yet calls) is cheap and low-risk; a convergence routes
*existing, live* call sites — DEC-024's two shipped hook handlers and `create-issue`'s
milestone write — through the new primitive, which is a refactor over a running engine
with a real regression surface (every adopter with a `set-board-field` /
`assign-milestone` hook exercises those paths today). ADR-026 paid the same cost for
its ~26 label sites and stated it honestly; this ADR states it for the four non-label
sites. Under-sizing it as a leaf add would mis-budget the work and risk regressing
DEC-024 adopters mid-refactor.

**Why failure-posture neutrality.** The two drivers have *genuinely different* correct
postures, settled by their own records. DEC-024 decided report-and-continue for
per-event hooks (rollback produces worse partial states; failing the exit code
discourages hooks entirely). DEC-037 decided audited skip-and-report for the bulk
back-fill (the corpus is hundreds of concurrently-editable human-owned issues; a blind
overwrite against stale enumeration is the failure mode to rule out). Neither posture
is wrong; they are right *for their driver*. A constructor that imposed either would
force the other driver to wear a posture its record rejected. Making the constructor
neutral — construct, run, report; the caller decides what the report means — is what
lets both records' postures hold simultaneously behind one construction point. It is
the separation-of-concerns that keeps "how the write is built" orthogonal to "what
happens when it fails," each owned by the layer that should own it.

**Why the four properties bind the bulk driver, not the primitive.** They are
properties of *mutating a live corpus* — re-validate against concurrent edits, detect
already-done by value, gate on the residual hard-fails, offer a draft-script form.
None is a property of constructing a single `gh` write; all are properties of driving
that construction *in bulk over human-owned state*. Placing them on the bulk driver
(not the primitive) is what keeps the primitive reusable by the per-event hook path
(which needs none of them — it writes one item, fired by one event) while the
high-blast-radius bulk path carries the full audit contract. This mirrors DEC-037's
own split: pm guarantees the *shape* properties (non-silent, re-validate, idempotent,
gated); value-*correctness* is the adopter hook's job.

**Why board-membership is out.** item-*add* (membership) and item-*edit*-field-value
(attribute) are different operations on the board substrate: one establishes that an
item is *on* the board, the other writes a *value* onto an item already there. The
back-fill and the default both write *values* onto existing items; neither
establishes membership. Folding membership into the field-value constructor would
overload it with an operation its two drivers never invoke, and would force the guard
to allow `gh project item-add` — re-opening exactly the inline-construction surface the
guard exists to close. Keeping membership as its own named-out operation keeps both the
constructor and the guard precise.

### Alternatives considered

- **Leave the four sites inline; add the back-fill/default as fresh constructors.**
  Rejected — re-grows the scatter ADR-026 spent ~26-site convergence to eliminate for
  labels; gives the invariant six places to drift and the guard six shapes to chase.
  Convergence behind one constructor is the whole point (DEC-037 §3).
- **A second allow-listed inline constructor in `hooks.py`** (let the DEC-024 handlers
  keep building `gh` inline, allow-list them). Rejected — a second sanctioned inline
  site is exactly what ADR-026 forbids for labels; the guard cannot hold the invariant
  honestly with a standing inline exception, and a future handler copies the pattern.
- **Bake a failure posture into the constructor** (e.g. report-and-continue, since
  DEC-024 is the existing caller). Rejected — forces the bulk back-fill to inherit a
  posture DEC-037 rejected for it (a report-and-continue back-fill silently swallows
  per-issue failures the audit must surface). Neutrality is what lets both postures
  coexist.
- **Bake the audited skip/report posture into the constructor.** Rejected — symmetric
  failure: the per-event DEC-024 hook would mis-handle a single-write failure under a
  bulk posture, and re-validate-at-apply is meaningless for a one-shot per-event write.
- **Subsume board-membership (`_gh_add_to_board`) into the contract.** Rejected —
  membership is a distinct operation (placement, not attribute-value); folding it in
  overloads the field-value constructor and forces the guard to allow `gh project
  item-add`, re-opening inline-construction surface. Named out (point 3).
- **Treat the milestone-at-create write (`gh issue create --milestone`) as separate
  from the post-hoc milestone write.** Rejected — same substrate (milestone), so same
  construction point; the `gh` verb differs but the substrate does not. Both route
  through the one milestone constructor; the call site chooses *when*, not *whether to
  construct inline*. (This is the fourth site DEC-037's "~3" tally understated.)
- **Put the four safety properties on the primitive.** Rejected — they are properties
  of bulk-mutating live state, not of constructing one write; placing them on the
  primitive would burden the per-event hook path (which needs none of them) and blur
  the construction/posture separation. They bind the bulk driver.

## Implications

- **One sole-constructor `_lib` module function per covered substrate** — the
  Projects-v2 field-value write (`gh project item-edit`) and the milestone write
  (`gh issue edit --milestone` + `gh issue create --milestone`). Its *placement and
  signature* land with the trunk Feature (DEC-037), citing this contract for the
  invariant and the neutrality posture.
- **The convergence is a refactor over the DEC-024 engine, in-scope for the Feature.**
  Routing `_hook_set_board_field`, `_hook_assign_milestone`, and `create-issue`'s
  milestone write through the primitive (retiring their inline `gh` argv construction),
  plus driving it from the per-create default and the one-time back-fill, is the work
  that makes sole-constructor real. Sized as a refactor over a live engine, not a leaf
  add (DEC-037 Implications).
- **The invariant is a tested property with two halves** (sole-constructor +
  emit-through-primitive), the same shape as ADR-026's guard: (a) a **construction
  test** — the primitive constructs/executes the covered writes and the converged sites
  obtain their write *from* it; **and** (b) a **grep/AST guard** — no script
  string-builds `gh project item-edit … --field-id` or `gh issue …--milestone` argv
  inline except the sole-constructor module. Without half (b) the construction test
  passes while a stray inline write bypasses the primitive — the four-site scatter
  re-growing unnoticed. Half (b) is what makes it structural and continuously verifies
  the convergence stays done.
- **Guard allow-list boundary — board-membership is out.** The guard keys on the
  *operation* (`item-edit` field-value write; `issue …--milestone`), not the `gh
  project` prefix, so `_gh_add_to_board`'s `gh project item-add` membership write is
  left alone (point 3). The sole-constructor module is the one allow-listed exception
  for the covered writes; membership is out of scope, not an allow-listed inline
  exception. Flagged so a future author does not widen the guard to `gh project` and
  either mis-flag membership or mis-allow a stray field-value write.
- **The four back-fill safety properties bind the bulk driver** — re-validate-at-apply
  (skip+report drift), per-issue value-equality idempotency, residual-pre-check gate
  (auth / repo-access / map-parse), `--emit-script` draft-not-apply. They are the
  write-path analogue of ADR-026's read-path fail-closed; they are properties of the
  *bulk driver* over a live corpus, not of the construction primitive (which the
  per-event hook path reuses without them). Value-*correctness* stays the adopter
  hook's responsibility (DEC-037); pm guarantees the shape/audit properties.
- **The constructor is failure-posture-neutral; each driver imposes its own.** The
  per-event DEC-024 hooks keep report-and-continue (DEC-024 unchanged); the bulk
  back-fill imposes the audited skip/report posture (DEC-037 §2). Construction and
  failure-handling live at different layers — this is what lets the two postures coexist
  behind one constructor. Confirm at impl that the primitive's result type carries
  enough detail (success / failure reason / drift) for both postures to act on.
- **No new DEC-024 hook kind or lifecycle event.** The convergence routes the existing
  `set-board-field` / `assign-milestone` kinds through the primitive; it adds no kind
  and no event. The per-create default is substantially a DEC-024 `after_create_issue`
  hook already (DEC-037 §4); the only genuinely new surface is the bulk back-fill driver
  over the same kinds. Confirm the kinds' declared idempotency composes with the bulk
  driver's value-equality idempotency (the bulk grain is finer; no conflict expected).
- **Relationship to records — no DEC-024 or DEC-036/DEC-037 amendment needed.** Records
  the write-path contract DEC-037 named as its ADR follow-up (the sibling to ADR-026).
  **DEC-024 is not superseded** — its hooks engine and kind taxonomy stand; this pins
  *how* its field/milestone kinds construct their write. **ADR-026's invariant stays
  label-scoped** and intact; this is its non-label write-side twin, with a separate
  substrate, constructor, and guard. Inherits ADR-026's sole-constructor + grep/AST
  guard discipline at a new boundary (non-label substrate writes) and recasts ADR-026's
  read-path fail-closed as DEC-037's four bulk-write invariants. Does not restate
  DEC-037; cites it as the decision.
- **Acceptance gate.** Accepted by the maintainer before the trunk implementation builds
  against it (per PRJ-005) — a forward design contract, not self-accepted. The primitive,
  the converged call sites, the guard, and the bulk driver land with the Feature, citing
  this ADR for the invariant.
