---
id: COR-037
title: A parent process may fold one child process's subject outcomes into a gate
status: accepted
date: 2026-06-23
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

The process substrate ([COR-033](COR-033-process-substrate.md)) named **breadth** — reasoning across more than the one subject the engine is acting on — as a deferred extension point (P5), to be shipped by its own decision when a real binding demands it. Three of the four P5 slots have since shipped narrow: human-pause ([COR-034](COR-034-human-pause-gate.md)), invariants ([COR-035](COR-035-process-invariants.md)), and composition ([COR-036](COR-036-process-composition.md)).

Each held the line [COR-032](COR-032-keyed-process-subjects.md) drew explicitly: *the engine never enumerates a keyed process's subjects — it only ever acts on the one it is given.* COR-036 then **named this slot** as its own deferred consumer: it ships resolving **one** determinate inner outcome, and points at "the enumerate-and-fold aggregate across a keyed inner's subjects (cascade) — it consumes this single-inner resolution as its per-subject step" as the follow-on.

Two independent bindings now demand the same fold — the recurrence signal ([COR-007](COR-007-pattern-extraction.md)) that un-defers a named slot:

- **project-management** carries a *closure cascade* capability-local: a parent container becomes eligible to close once **every** child is done.
- **trip-planning** (an adopter binding) needs the same shape one altitude down: an area's discovery closes only once **every** one of its points-of-interest reaches `verified`.

Both are the same shape: read across the many subjects of *one* child process that belong to a parent, and fold their outcomes into a single answer that gates the parent. This is the fourth and last P5 slot, and the one that most stretches the substrate — it is where the engine **first** reads across a crowd of subjects, crossing the line COR-032 drew.

## Decision

**In plain terms:** a parent process may look across **all** the subjects of **one named child process** that belong to it, and ask one question — "did *every* one reach outcome X?" — then let that answer open a parent gate. Picture an area whose discovery closes only once every point-of-interest in it has been verified: the parent reads its children's outcomes and folds them into one yes/no. This is the **one** sanctioned, tightly-bounded place where the engine reads across many subjects; it is **not** a general re-opening of enumeration.

The fold ships narrow:

- **Direction is child → parent, coupling in the parent.** A parent declares the fold over one named child process; the child references nothing upward and stays reusable and parent-agnostic — the discipline COR-036 set for composition.
- **The binding supplies the set; the engine folds.** The set folded over is the keyed subjects of the **one** named child process that belong to the given parent subject. The engine does **not** hold or discover a containment tree — it obtains the set from a **capability-supplied membership predicate** evaluated per candidate by the existing single-subject predicate runner ("does this subject belong to this parent?"), the same content-free seam COR-033 uses for detection. The set is whatever that predicate returns **at each evaluation**, re-read live — determinate at the instant, never a stored or open-ended listing.
- **Two fold operations: `all` and `count`.** `all` = every member of the set reached a named outcome (grounded twice — pm closure + trip-planning all-verified). `count` = how many members reached an outcome, compared against a threshold (a *saturation floor* — "≥ N places verified is enough", anticipated by trip-planning's coverage rule). Both are the **same** enumerate-and-fold machine differing only in the reducer, so they ship together at near-zero marginal surface. Richer reducers (ratios, weighted, custom) stay **named-deferred** — they land when a binding demonstrably needs one, the COR-036 pattern.
- **Fold semantics are fail-closed.** A member whose outcome is not yet resolved (still moving, parked, indeterminate) holds the fold **unresolved** — the parent stays blocked, never reads a false "all reached X."
- **The empty set is a binding-supplied policy** *(amended — see note below)*. A **determinately-empty** set — the membership evaluation completed without error and confirmed *no* candidate in the relation's pool is a member — resolves the fold by the binding's declared `on_empty` policy: **`fail-closed` (the default)** keeps the gate shut — an area with zero points-of-interest is not "fully discovered"; **`satisfied`** opens it — "nothing to wait on" (project-management's childless-container closure). Either way the answer is **determinate**; the policy only chooses which way the determinate answer points, and the default is `fail-closed`, so a binding that says nothing keeps the original, conservative behaviour.
  - **`on_empty` applies only to a *determinate*-empty set, and indeterminate membership overrides it.** If candidate enumeration or any membership evaluation errors / is indeterminate, the fold is held **unresolved** regardless of `on_empty` — including under `satisfied`. A wholesale membership-read failure that confirms zero members is *not* an empty set; it is indeterminate, and the gate stays shut. This precedence (indeterminate membership ≻ `on_empty`) is what keeps `satisfied` from fail-*opening* on a broken read.
  - **`on_empty` governs the empty-set answer for *both* reducers.** On an empty set the reducer is not evaluated — so it also forecloses a `count` threshold of `0` opening the gate by its own vacuous arithmetic; `on_empty` decides the empty case for `all` and `count` alike.

> **Amendment (driven by the project-management closure-cascade binding, [COR-007](COR-007-pattern-extraction.md) recurrence).** This record originally fixed the empty set as unconditionally `fail-closed`. A second binding — pm's "a childless container may close" — needs the opposite, and the empty-set direction is a legitimate per-binding difference (an empty area is *not-yet-started*; an empty container has *nothing outstanding*). The rule above is therefore widened to the binding-supplied `on_empty` policy — a **closed two-value enumeration** (`fail-closed` | `satisfied`), exactly two because two grounded bindings split this edge; it is not an open policy hook. `fail-closed` stays the default, so existing cascade declarations and trip-planning's grounding behaviour are unchanged (additive; the impl field is optional, defaulting to `fail-closed`). The new `satisfied` mode is opt-in; its empty answer stays determinate *because* indeterminate membership overrides it (above). The non-empty fold semantics (unresolved member / indeterminate membership hold the fold) are unchanged.
- **The fold feeds a parent gate**, and the parent's **aggregate wait** — COR-036's deferred "many-inner wait" — is un-deferred here for this one declared relation: the parent stays blocked until the fold resolves (reusing COR-034's auto-clearing overlay, no `resume_when`).

### The COR-032 line — crossed once, by declaration

This is the slot that crosses COR-032's *the engine never enumerates*. It crosses it **minimally**: the engine reads across subjects only via **one declared child relation scoped to one parent subject**, and only through a capability-supplied membership predicate run one subject at a time — never a general subject-listing capability the engine exposes, never a containment tree the engine holds. Everywhere else COR-032's discipline is unchanged.

The mechanism is **designed once, here, for cross-subject *fold* needs** — so future aggregation routes through this declared relation rather than growing a rival fold path. It is *not* the home for every cross-subject concern: peer-subject wait cycles (`deadlock`, COR-034) and cross-subject invariants (COR-035) are **different** cross-subject shapes that stay separately deferred.

### Scope — outcome-fold, child → parent only

Three things stay deferred, each its own future decision when a binding needs it:

- **Forward / position cascade.** pm *also* has a forward cascade — "bump a parent up to match its furthest child", firing on every child move, over *non-terminal positions*. That is a different shape (a position reduction, not a terminal-outcome fold) and is **not** shipped here; pm keeps it capability-local until a binding demands the shared form.
- **`count` and richer folds** — named above.
- **Overflow / hand-off** (a terminal state spawning or unblocking a *concurrent* sibling process — altitude-2 orchestration).

The **deadlock** reason COR-034 deferred also stays deferred — and here that is *safe by construction*, not by hope: the parent waits only on its children's **already-resolved terminal outcomes**, and a terminal subject waits on nothing, so the aggregate wait cannot participate in a wait cycle. Termination rests on the same **single-level bounded depth** as COR-036's per-subject resolution (ADR-022) — cascade adds breadth across a finite set, not depth.

## Rationale

Breadth has been named-deferred since COR-033 P5, held through COR-032, re-named as composition's consumer in COR-036. Two independent bindings demanding the same child→parent `all`-fold is COR-007's recurrence test, and COR-016's name-broad / ship-narrow applied: un-defer the named slot, narrow to exactly what the bindings demand — `all`, child→parent, one declared relation, fail-closed.

Shipping `all` and `count` together is the disciplined cut drawn at the right boundary — at *machine* boundaries, not reducer variants. `all` and `count` are one enumerate-and-fold machine with two reducers (every-member vs count-against-threshold), so adding `count` beside `all` is near-zero marginal surface and well within reach of the bindings (closure + a saturation floor). What stays deferred is every genuinely *different* cross-subject machine — forward / position cascade, peer-cycle deadlock, cross-subject invariants — because each needs a real binding to fix its shape before it is built; building a machine one can only imagine is what COR-016's name-broad / ship-narrow guards against.

The mechanism reuses COR-036's single-inner resolution as its per-subject step rather than inventing a parallel cross-process path — which is why composition was built as the foundational unit and cascade as its consumer.

**P3 / P6 consistency (the foundational-line argument).** A cascade gate's answer is a **composed definite answer over reality**, consistent with COR-033 P3, not an exception. Each child outcome is itself inferred-from-reality by COR-036's resolution; the membership set is a live re-read of a deterministic predicate (determinate at each evaluation, even as the underlying set grows); and `all` is a deterministic reduction over that finite set, fail-closed on any unresolved member. So the parent's cascade-gate position is composed from deterministic, terminating parts and the engine stays a deterministic validator (P6). The new axis is *breadth* (set size), not *depth* (resolution nesting) — the engine stays single-level.

### Alternatives considered

- **Keep cascade capability-local forever** (pm and trip-planning each carry their own). Rejected — two independent bindings is COR-007's recurrence signal; duplicated cross-subject fold logic in every binding is the cost the substrate exists to remove. pm's *closure* cascade rebinds onto the shared shape (a pre-budgeted COR-010 migration); pm's *forward* cascade is a different shape and stays capability-local for now.
- **Capability folds its own subjects; the engine never enumerates.** A capability could enumerate its own children and call single-inner resolution N times, folding entirely capability-side — leaving COR-032's line fully intact. Rejected because the fold result must open a **parent gate**, and gates are engine-evaluated: a fold the engine cannot read cannot gate a parent's position. That is the load-bearing reason the line must be crossed — the crossing is *necessary*, not convenient — and it is why the crossing is held to the minimal, declared, predicate-fed form above.
- **Ship a general cross-subject enumeration API.** Rejected — over-ships past COR-032 and re-opens arbitrary cross-subject reading. The declared, bounded, predicate-fed one-relation fold crosses the line without dissolving it.
- **Ship richer reducers (ratios / weighted / custom) now.** Rejected — `all` and `count` cover both bindings (every-member and count-against-threshold); ratios and custom reducers are speculative and land when a binding needs one.
- **Ship the *other* cross-subject machines now** (forward / position cascade, deadlock, cross-subject invariants). Rejected — these are not bigger versions of the fold; they are separate machines with their own timing, direction, and failure shape. Each is **named** as a future slot routed through its own decision, built when a real binding fixes its shape — not designed speculatively here.

## Implications

- The shape contract widens: a process gains a **cascade** declaration (the named child relation + its membership predicate + the `all` / `count` fold + the parent gate it feeds) plus the cascade gate kind, and `blocked_on` admits the aggregate wait. Surface change; the affected backbone component's version bumps per the project's version policy. Field-layout is deferred to the process-area shape reference and the implementation task — this record fixes the **rules** (child→parent, binding-supplied membership predicate, `all` / `count` reducers, fail-closed on unresolved members, binding-supplied `on_empty` policy on the empty set with `fail-closed` the default), not the field names.
- **project-management rebind.** pm's capability-local **closure** cascade moves onto the shared shape — a COR-010 migration, pre-budgeted by COR-033's acceptance gate for the substrate rebind. pm's **forward** cascade is a different shape and is **not** ported here; the migration is scoped to closure.
- **trip-planning** binds the POI → area-coverage closure as the grounded second instance, in its own capability decision with its area-discovery process.
- **Relationship to COR-032.** The single sanctioned, bounded exception to *the engine never enumerates* — predicate-fed, one relation, fail-closed; the discipline holds everywhere else. Future cross-subject **fold** needs route here.
- **Relationship to COR-034 / COR-035.** `deadlock` (peer-subject cycles) and cross-subject **invariants** are separate cross-subject shapes, each separately deferred — this slot does not pretend to be their home. The aggregate wait is acyclic by construction (parent waits only on terminal outcomes).
- **ADR follow-up (at implementation time).** Cascade extends ADR-022's single-level resolution with its own architecturally-significant choices — which side enumerates (settled here: the binding, via predicate), how the fold is engine-computed, and the partial-indeterminacy fail-closed semantics — and warrants a sibling ADR authored when engine work begins, not now.
- This is the **last** of the four COR-033 P5 slots; with it, blocked (COR-034), invariants (COR-035), composition (COR-036), and cascade (this record) are all shipped.
- **Acceptance requires two maintainer sign-offs**, by the foundational nature of the slot: (1) the COR-032 *never-enumerate*-line crossing is sanctioned and bounded as stated, and (2) the cross-subject **fold** mechanism is authorised to be designed once here (scoped to folds — not peer-cycles or invariants).
