---
id: ADR-026
title: Resolve methodology axes through one substrate-map read seam, ternary and fail-closed — never write the kit's own label
status: accepted
date: 2026-06-24
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

[project-management:DEC-036](../../../.pkit/capabilities/project-management/decisions/DEC-036-substrate-pluggable-adoption.md)
decided the *rule* — a brownfield adopter binds each methodology axis (type,
priority, workstream, lifecycle-state, hierarchy) onto whatever their immutable
tracker already encodes, via a dedicated `substrate-map.yaml`, and a feature
whose substrate is genuinely absent **degrades** rather than refusing wholesale.
This ADR records the *read-path contract* DEC-036 named as its ADR follow-up:
**how** the axis consumers (`classification.yaml`, `issue-types.yaml`,
`git-conventions.yaml`, and the lifecycle detector) resolve a conceptual axis
to a concrete substrate value, and the one safety property that resolution must
never violate. It is the on-call/maintainer reference for the resolution layer
that lands ahead of the trunk Feature; it pins the contract, not the schema
field layout or the engine code (those land with the Feature, citing DEC-036).

**The contract, in one breath:** axis resolution lives behind **one read seam**
the consumers call — not scattered into each schema as a `binds_to` field — and
that seam answers a **ternary**, never a binary. No `substrate-map.yaml` present
→ every axis resolves to the kit's own labels directly (greenfield,
byte-unchanged; the seam is inert). A map present → **per axis**: *bound*
(resolve through the declared binding — a `label` value-remap, a `title-prefix`,
or a `derive` predicate), *`unsupported`* (the feature needing it degrades to
advisory/disabled), or **absent-from-a-present-map** — which the seam treats as
**`unsupported`, NOT greenfield**. That last rule is the load-bearing one: an
adopter who omits an axis they cannot serve must get degradation, not a silent
fall-back to writing a label they cannot create.

**The load-bearing invariant — the read-path fails closed to a *read*, never
open to a *write*.** It is **two-part**, and only both parts together make it
structural: (i) **a mutating script obtains an axis label to write only by asking
the seam** — it never string-formats `<axis>:<value>` inline, so the seam is the
*sole constructor* of any axis label on a write path; and (ii) **when an axis is
`unsupported`, absent, or indeterminate, the seam emits no write-label** — it
resolves to "degrade" (advisory / disabled) and the consumer reads accordingly.
Part (ii) alone guarantees nothing about a writer that never asks the seam — and
today every axis-label is built by inline string-formatting that routes *around*
any seam (`create-issue.py` builds `type:`/`priority:`/`workstream:` as string
literals; `bootstrap.py` builds `state:*`; ~26 such write-path sites). Part (i)
is what closes that gap: with sole-constructor, the seam *is* the structural
guarantee — there is no second path by which a write-label can come into being,
so "the seam emits no unmanaged write-label" actually entails "no unmanaged
write-label is ever written." This is what makes DEC-036's "never write an
unmanaged label" (EPIC #217 constraint 1) hold *at the resolution layer* rather
than only at each mutating call site — the same shape as
[ADR-022](ADR-022-subprocess-resolution-strategy.md)'s
fail-closed-on-indeterminate-inner and [ADR-024](ADR-024-cli-prose-wrapping.md)'s
`--json` byte-stability (where `render_status_json` *never calls* `wrap()`, so no
presentation decision can reach the parsed surface): a single auditable point
where the unsafe direction is structurally unreachable. An unresolvable axis
fails closed to degrade; it cannot fail open to a greenfield write — because no
write-label exists except the one the seam constructed.

## Context

DEC-036 settled the substrate-axis binding and degradation model and explicitly
deferred the read-path mechanics to an ADR at implementation time: *"the
read-path contract over schema consumers (how the indirection resolves; the
fail-closed posture that must never fall through to a greenfield write) is
capability-architecture worth an ADR … the architect offered to author it once
this DEC settles."* DEC-036 is now `accepted` and merged; this is that ADR.

The forcing case is `agentic-user-journey` (AUJ): a brownfield repo with no
`type:*` / `workstream:* `/ `state:*` labels and none creatable, priority via
native `P0`/`P1`/`P2`, type via `[Task]`/`[Epic]` title-prefix, state implicit
in open/closed plus a `Blocked` label, and a flat tracker with no
machine-checkable parent-refs. The capability's axis consumers
(`classification.yaml`'s type/priority/workstream axes, `issue-types.yaml`'s
type vocabulary + containment, `git-conventions.yaml`'s `type:*`-derived branch
names, and the lifecycle detector) all read the kit's own labels directly today.
For the brownfield adopter they must read *through* the adopter's map instead —
without polluting their own shape, and without ever silently re-entering a
greenfield write on an axis the repo can't express.

This ADR records the architecturally-significant choices in **how** that
indirection resolves. As project-kit's own capability-architecture record,
concrete consumer names are in scope (per
[PRJ-005](../../../.pkit/decisions/project/PRJ-005-adopt-adrs.md)); the
`substrate-map.yaml` *field layout* and the *engine/predicate code* are not —
they land with the trunk Wave-2 Feature (EPIC #217), citing DEC-036. The
decision space has four architecturally-significant pins, each carrying a
plausible alternative DEC-036 already rejected or this ADR holds against:

1. **Where resolution lives** — one read seam the consumers call vs. a `binds_to`
   field scattered into each schema (DEC-036 rejected the latter on the
   architect steer).
2. **What the seam answers** — an axis-level *ternary* (bound / `unsupported` /
   absent-treated-as-`unsupported`) vs. a *binary* (mapped / greenfield) that
   would let an omitted axis re-enter wholesale refusal; plus a *value-level*
   fourth arm (value-unresolvable within a bound axis) that must not collapse into
   axis-level degradation, lest a type-keyed hard invariant silently soften.
3. **Which direction is structurally unreachable, and what makes it structural** —
   the fail-closed posture (degrade, never write the kit's own label) as a
   resolution-layer invariant vs. a per-call-site guard. The pin this ADR adds:
   the seam is the *sole constructor* of any axis label on a write path (writers
   never string-format `<axis>:<value>` inline), without which "the seam fails
   closed" guarantees nothing about a writer that bypasses it.
4. **How lifecycle composes** — a detection-predicate swap over a reduced state
   set ([project-management:DEC-033](../../../.pkit/capabilities/project-management/decisions/DEC-033-rebind-issue-lifecycle-onto-process-substrate.md))
   feeding the closure fold's derived terminal
   ([project-management:DEC-034](../../../.pkit/capabilities/project-management/decisions/DEC-034-cascade-slot-binding.md))
   vs. re-deriving a brownfield-specific lifecycle path.

## Decision

**In plain terms:** the consumers stop reading the kit's own labels directly and
start asking *one seam* "what does this axis resolve to here?" The seam returns
either a concrete substrate value to read, or a "degrade" signal — and it is
built so that "degrade" can never quietly become "write the kit's own label."

### 1. One read seam — the indirection lives in exactly one auditable place

Axis resolution is a single read-path seam the consumers call; it is **not** a
`binds_to` field merged into each consumer schema. `classification.yaml`,
`issue-types.yaml`, and `git-conventions.yaml` keep their current shape
byte-for-byte; each reads its axis *through* the seam rather than reading the
kit's own label inline. The seam takes a conceptual axis (and, where relevant,
a conceptual value — e.g. priority `High`) and returns how that axis is encoded
*in this repo*: the kit's own label (greenfield), a remapped substrate value
(`label` / `title-prefix`), a derived read (`derive`), or a degrade signal.

This is the DEC-036 architect steer realised in the read path: the indirection
sits in one place where it can be audited, tested, and reasoned about as a unit,
and the schemas stay clean of adopter-substrate concerns. A `binds_to` field per
schema would scatter the same resolution logic across every consumer and
entangle each schema's shape with whether a given adopter happens to have a
board, a prefix convention, or neither — the exact scatter DEC-036 rejected.

### 2. The ternary — and why absent is not greenfield

The seam answers a **ternary per axis**, governed by a single rule: *the
presence of a map flips the default for an unlisted axis from greenfield to
degrade.*

- **No `substrate-map.yaml` at all** → every axis resolves to the kit's own
  label directly. This is greenfield, **byte-unchanged**: the seam is inert,
  the consumers read exactly what they read today, and no resolution decision
  is taken at all. Greenfield is not a special case threaded through the seam;
  it is the seam returning the identity.
- **A map present, axis bound** → resolve through the declared binding (`label`
  value→value remap, `title-prefix`, or `derive`). The consumer reads the
  adopter's substrate value in place of the kit's own.
- **A map present, axis `unsupported`** → the seam returns a degrade signal; the
  feature needing that axis softens (advisory / disabled per point 3).
- **A map present, axis *absent from the map*** → treated as **`unsupported`,
  NOT greenfield.** This is the load-bearing rule. An adopter who simply omits an
  axis they cannot serve (e.g. AUJ omitting `workstream`, which has no native
  encoding) must get degradation — not a silent fall-back to reading/writing the
  kit's own `workstream:*` labels they cannot create. One uniform consumer
  contract: once a map exists, the default for every unlisted axis is *degrade*,
  not greenfield. There is no second source of truth (no `mode` flag) that could
  disagree with the map's presence (DEC-036 D2).

The ternary collapses to the greenfield binary only in the no-map case; the
moment a map exists, "I didn't mention this axis" and "I marked this axis
`unsupported`" resolve identically. That equivalence is what stops an omission
from re-opening wholesale refusal on labels the adopter cannot create.

**The fourth arm — value-unresolvable within a *bound* axis.** The three arms
above are about the *axis*. There is a distinct fourth case the seam must answer
at the *value* level: an axis that **is bound**, but for which a **specific
methodology value has no representation in the binding.** AUJ binds `type` via
title-prefix but ships only `[Task]` / `[Epic]` prefixes — so `task` and `epic`
resolve, while `feature` and `umbrella` do **not** (no `[Feature]` / `[Umbrella]`
prefix exists). This is *value-unresolvable-within-a-bound-axis*, and it is **not**
the same as axis-`unsupported`: the axis is served, only one value is missing. The
seam must keep the two distinct, because collapsing the fourth case into
axis-level "this axis degrades to advisory" would silently soften **every rule
keyed on that axis** — including rules that depend on *other, resolvable* values
of the same axis. Concretely, the **Feature-in-Feature containment invariant** is
keyed on `type` (`issue-types.yaml`); DEC-036 D4 holds the containment invariants
**hard** even in brownfield. If an unresolvable `feature` value degraded the whole
`type` axis to advisory, that hard invariant would soften — exactly the silent
loosening D4 forbids. So the contract: **value-unresolvable triggers degradation
only for rules that depend on *that value*, never axis-level degradation of rules
that depend on other values or on the axis as a whole.** A rule that never
references the missing value stays at its authored severity.

**The fail-safe default for a degrade-signalled rule with no severity knob.** When
the seam signals "degrade" for a rule that **has no `*_severity` field to flip**,
the rule **stays at its authored severity** — it does **not** silently become
advisory. The containment invariants are the live instance: they are authored in
prose in `issue-types.yaml` with **no severity field** (DEC-036 point 3's "honest
gap"), and DEC-036 D4 says they stay hard. If "no knob" defaulted to advisory, a
hard containment invariant would soften the moment any input touching it became
indeterminate — the unsafe direction. The fail-safe rule makes the missing-knob
case fail **safe**: a rule with no severity field is held at *hard* until a knob is
explicitly added (the Feature's in-scope schema work, point in Boundaries). This
keeps the containment invariants hard as DEC-036 D4 requires, by construction
rather than by remembering. This refines *how* the seam signals degradation
(read-path / resolution mechanics — this ADR's domain); it is fully consistent
with DEC-036's *what* (D4 keeps containment hard; point 3 names the missing-knob
gap as schema work). **No DEC-036 amendment is needed** — the ADR pins the
resolution behaviour DEC-036 left to implementation, it does not change DEC-036's
decision.

### 3. The fail-closed posture — sole-constructor seam, never writes the kit's label

This is the load-bearing safety property, and it is **two-part**. Either part
alone is insufficient; together they make "never write an unmanaged label" a
property of the architecture rather than of discipline at each site.

**Part (i) — the seam is the sole constructor of any axis label on a write path.**
A mutating script obtains a label-to-write **only by asking the seam**; it
**never** string-formats `<axis>:<value>` inline. This is the premise that makes
part (ii) bite. Today it does not hold: ~26 write-path sites construct axis
labels as string literals that route *around* any seam — `create-issue.py:367-370`
builds `f"type:{...}"` / `f"priority:{...}"` / `f"workstream:{...}"`; `bootstrap.py`
builds `state:*`; the `move-issue` / `promote-issue` / workstream-mutator paths do
likewise. A writer that never asks the seam is unconstrained by anything the seam
guarantees. So part (i) is a real change with real scope: **the trunk Feature must
refactor those literal-construction sites to route every write-label through the
seam.** That refactor is precisely what converts "never write an unmanaged label"
from per-call-site discipline (remember not to format the wrong literal) into a
structural property (there is no other way to obtain a write-label at all).

**Part (ii) — when an axis is `unsupported`, absent-from-a-present-map, or
*indeterminate* (a `derive` predicate errored, a binding is malformed), the seam
emits no write-label.** It resolves to *degrade* (advisory / disabled), never to a
greenfield write. In a present-map world the seam has no code path that returns
"the kit's own label" as a *write* target; greenfield-label resolution is reachable
**only** in the no-map case (point 2), where it is an identity *read*, not a write
decision.

**Why both, and which is the structural guarantee.** Part (ii) on its own
guarantees nothing — a writer that string-formats its own label never consults the
seam, so the seam's refusal to emit a write-label is irrelevant to it. Part (i) is
what makes the seam the *only* source of write-labels, and therefore the single
auditable choke point at which part (ii) is enforced for *every* write. With
sole-constructor in place, **the seam IS the structural guarantee** — not a
"suspenders" backstop to a per-site "belt." The framing is reversed from a
seam-as-redundant-second-layer reading: the per-site write-side guard DEC-036 names
is the redundant outer check; the seam's sole-constructor + emit-no-write-label is
the structural property the architecture rests on. So a mutating consumer
(`create-issue`, `move-issue`, `bootstrap`'s additive label-creation) that asks the
seam for a binding it cannot resolve gets "degrade," and — because it has no other
way to obtain a label — degrade has no write.

It is the direct analogue of the project's other fail-closed pins:
ADR-022/ADR-023 fail an indeterminate cross-process resolution *closed* (gate
stays shut) rather than open (a false "all reached X"); ADR-024 keeps the
`--json` surface byte-stable so no presentation decision can reach a parsed
consumer. Here the indeterminate/absent axis fails closed to *degrade*, so no
resolution decision can reach an unmanaged-label *write*. Same instinct, new
boundary.

### 4. Schema-clean indirection — the consumers keep their shape

The map is **read through**, not merged into the consumers. `classification.yaml`
still declares its three axes and their methodology-fixed values;
`issue-types.yaml` still declares the four types and the containment graph;
`git-conventions.yaml` still declares branch/PR/merge conventions. None gains an
**adopter-substrate-binding** field. The seam is the only thing that knows an
adopter's `substrate-map.yaml` exists. This keeps the greenfield path *identical*
to today (the indirection is inert when no map is present — point 2) and keeps
each schema free of *this adopter's* substrate.

**Reconciling with the pre-existing in-schema substrate switch.** The
"schemas-clean" claim is **not** that the schemas are clean of *all* substrate
concerns — they are not, today. `classification.yaml` already carries a
`substrate_with_board` / `substrate_without_board` pair per axis (e.g. `priority`
reads "Projects v2 single-select field" with a board, "label (`priority:*`)"
without; `type` is "label regardless"). So the schemas **already branch on one
substrate dimension** — board-vs-label, an *intra-greenfield* choice about where
the adopter's *own* kit-managed encoding lives. The board-vs-label switch is the
**degenerate, kit-internal binding**: it chooses between two substrates the kit
*itself* manages (a board it created, or labels it created), within the greenfield
world. `substrate-map.yaml` is the **general, adopter-immutable binding**: it
remaps an axis onto a substrate the *adopter* owns and the kit cannot create.

The clean placement: the seam **composes over** the board-vs-label switch rather
than absorbing it. Board-vs-label stays an in-schema concern (it is a property of
the kit's own greenfield encoding, which the schema legitimately knows); the seam
sits *above* it, resolving the adopter-binding question first (is this axis bound
to the adopter's substrate, `unsupported`, or kit-managed?), and only in the
kit-managed (greenfield) case does the existing `substrate_with_board` /
`substrate_without_board` distinction apply underneath. Treating board-vs-label as
a *degenerate binding the seam also owns* is a plausible later unification (one
resolution surface for every substrate question) — **not pinned here**; v1 keeps
board-vs-label inline and the seam composing over it, because the two are at
different layers (kit-managed sub-choice vs. adopter-immutable remap) and folding
them now is speculative generality (COR-007). So the honest claim: **greenfield is
byte-unchanged** (the seam returns the identity, the existing board-vs-label
switch is untouched), and the schemas gain **no new adopter-substrate field** —
but they are *not* claimed clean of the kit-internal board-vs-label substrate
distinction they already carry.

### 5. Lifecycle composes with DEC-033/DEC-034 — swap the detector, not the engine

Lifecycle resolves through the seam as a **detection-predicate swap**, faithful
to DEC-033's "the engine resolves position from a predicate over reality, first
matching detection wins." Brownfield binds the lifecycle axis to a `derive`
predicate over **open/closed + a blocked label** in place of one over `state:*`.
The engine contract is **untouched** — it never cared whether the predicate read
a `state:*` label or open/closed; the seam hands it a (remapped) detector and the
engine runs unchanged.

The read-path must stay faithful to the **reduced state set** this entails: a
derive-from-open/closed predicate cannot distinguish the greenfield open-ish
states (Todo / Backlog / In-progress all read as `open`), so brownfield collapses
them to one open-ish state (plus `blocked` from the label, `done` from `closed`).
**That collapse is DEC-036's decision, not this ADR's** — DEC-036's lifecycle-state
paragraph already decided the reduced-state-set and that transitions among the
collapsed states are no-ops; this ADR cites it and pins only the **read-path
consequence** of that decision (the no-op scoping below), per the no-restate
discipline.

The read-path consequence to pin precisely: a transition *among* the collapsed
states is a **no-op scoped to the state-position change only** — the engine
resolves the *same* collapsed state pre- and post-transition and records **no
journal move**. It is **not** a no-op for the wrapper's domain side-effects. A
transition wrapper like `start-work` still creates its branch / PR, sets the
assignee, and performs its other domain actions; only the *position* it would
otherwise journal collapses to nothing because the derived state does not change.
Scoping the no-op to the position change (not the whole transition) is what keeps
`start-work` working in brownfield — a whole-transition no-op would silently
disable it.

The [project-management:DEC-034](../../../.pkit/capabilities/project-management/decisions/DEC-034-cascade-slot-binding.md)
closure cascade reads the **derived terminal**: `done` derives from `closed`,
and since GitHub `closed` does not distinguish completed from won't-do, DEC-034's
"won't-do counts toward closure" is automatically satisfied (both are `closed`)
— the fold still reads a well-defined terminal. But the fold's **membership read
is itself a degraded path on a flat repo**, and the contract must say so rather
than claim clean inheritance. DEC-034's `members` / `membership` predicates walk
the **body parent-ref** (as `_find_open_children` does). On AUJ's flat tracker the
body parent-refs are **ungated / absent** — so the membership walk cannot soundly
resolve a parent's child set, and per COR-037's fail-closed fold semantics an
**indeterminate member holds the fold unresolved** (precedence:
indeterminate-holds-the-fold). The consequence: a flat-repo parent's
**auto-close-eligibility is itself a degraded path** — the fold stays unresolved
(parent stays blocked, never reads a false "all children done") rather than
cleanly inheriting greenfield close-eligibility. The read-path's only job here is
to resolve the detector through the seam; the reduced-state-set and the no-op
position-collapse are properties of the detector the binding supplies, and the
cascade fold (ADR-023's `members`/`membership` seam) reads the derived *terminal*
exactly as it reads the greenfield one — but its membership input degrades to
indeterminate-holds-the-fold on flat-repo parent-refs (COR-037 precedence).
Brownfield swaps the *detector*; the engine and fold *contracts* are inherited
unchanged, while the fold's membership *input* is a degraded read on a flat repo.

### Boundaries — what this contract is NOT

- **Not the schema field layout.** How `substrate-map.yaml` spells a `label`
  remap vs. a `title-prefix` vs. a `derive` predicate, and what fields the seam
  reads, lands with the trunk Feature (DEC-036's Implications), not here.
- **Not the severity-field schema work.** DEC-036 flagged that some hard-rejects
  (containment invariants, parent-ref hard-rejects) lack a `*_severity` knob and
  need one *added* before degradation can flip them. That is in-scope schema work
  for the Feature; this ADR pins only that the seam *resolves to degrade* — how a
  given rule expresses "degraded" is the consumer's `*_severity` story (DEC-014).
  This ADR *does* pin the resolution mechanic for the no-knob case (point 2): a
  degrade-signalled rule **with no severity field stays at its authored severity
  (hard) until a knob is added** — never silently advisory. That keeps the
  containment invariants hard (DEC-036 D4) by construction; the knob-adding itself
  is the Feature's schema work.
- **Not the cross-capability bootstrap shape.** Per DEC-036's carrier discipline
  (DEC-022's defer-until-second-instance), the generic "greenfield-default +
  brownfield-adopt-existing" shape is **not named here**; it is COR-promotable on
  the second instance (living-docs, EPIC #234). This ADR is pm-capability
  architecture and binds pm's instance only.
- **Not a `bootstrap` redesign.** Suppressing `bootstrap`'s additive
  label-creation per-axis-where-bound is a consequence the seam enables (a bound
  axis resolves to the adopter's substrate, so there is nothing to create), but
  the `adopt-existing` inventory/scaffold UX is a deferred Wave-2 Feature
  (DEC-036), not this contract.

## Rationale

**Why one seam, not a `binds_to` field.** The indirection is a cross-cutting
concern — every axis consumer needs it, and the *same* resolution logic (the
ternary, the fail-closed posture) must behave identically across all of them.
A concern that must be uniform across many consumers belongs at one boundary, not
copied into each. Scattering it as a per-schema field would (a) entangle each
schema's shape with *adopter-immutable* substrate concerns it should not carry
(distinct from the kit-internal board-vs-label switch the schemas already and
legitimately hold — point 4), and (b) give the fail-closed posture *N* places to
drift instead of one to audit. One seam is the COR-007 "extract the shared shape"
move applied to resolution, and it is exactly the architect steer DEC-036
recorded.

**Why a ternary, and why absent ≡ `unsupported`.** A binary (mapped vs.
greenfield) has a fatal gap: an adopter who *omits* an axis they cannot serve
would fall into "greenfield" and the capability would try to read — and a
mutating path would try to *write* — the kit's own label they cannot create.
That is the exact wholesale-refusal-by-another-name DEC-036 exists to remove,
re-entered silently through an omission. Making "absent from a present map"
resolve to `unsupported` closes that gap with one rule and no second switch: the
presence of a map *is* the signal that unlisted axes degrade. Greenfield stays
the easy default precisely because it is the *no-map* case, untouched.

**Why fail-closed at the seam, not only at the call sites — and why
sole-constructor is the premise that makes it work.** "Never write an unmanaged
label" is the load-bearing safety property of the whole brownfield mode (EPIC #217
constraint 1). A property this important should be *unreachable to violate*, not
*remembered not to violate*. But "the seam fails closed" is empty unless the seam
is the **only** way a write-label comes into being — otherwise a writer that
string-formats `<axis>:<value>` inline (as all ~26 write-path sites do today)
violates the property while never touching the seam. So the seam-level invariant
has a premise: **sole-constructor** — writers obtain a write-label only by asking
the seam. With that premise, the unsafe direction (degrade → write the kit's
label) has no code path at all in a present-map world, and the seam *is* the
structural guarantee; the per-site write guard becomes the redundant outer layer,
not the structural property. This is the same architectural instinct as
ADR-022/ADR-023 (fail an indeterminate fold *closed*, never vacuously open) and
ADR-024 (the parsed surface cannot be reached by a presentation decision because
`render_status_json` *never calls* `wrap()` — the constructor analogue: the unsafe
operation has no path to the protected surface): make the safe direction the only
direction the structure permits. The cost is honest — sole-constructor is not free;
it requires refactoring the ~26 inline-literal sites to route through the seam,
which is the trunk Feature's scope.

**Why a detector swap for lifecycle, not a brownfield-specific path.** DEC-033's
engine resolves position from a predicate over reality and is deliberately
agnostic to *what* the predicate reads. Brownfield needs only a different
predicate (open/closed + blocked label) and a declared collapsed state set — not
a different engine, not a different fold. Re-deriving a brownfield lifecycle path
would fork the engine contract and force the cascade fold to learn two shapes;
swapping the detector keeps one engine, one fold, and inherits ADR-023's
fail-closed fold semantics for free over the derived state.

### Alternatives considered

- **A `binds_to` field per consumer schema** instead of one read seam. Rejected
  (DEC-036 architect steer, held here) — scatters the resolution logic and the
  fail-closed posture across every schema, entangles each schema's shape with
  adopter-substrate concerns, and gives the safety invariant N places to drift.
- **A binary mapped/greenfield resolution** (absent axis ⇒ greenfield).
  Rejected — an omitted axis silently re-enters wholesale refusal on labels the
  adopter cannot create, defeating the whole point of brownfield mode. The
  ternary's absent ≡ `unsupported` rule is the fix.
- **A global `mode: brownfield` flag** the seam keys on. Rejected (DEC-036 D2) —
  a second source of truth that can disagree with the actual presence of
  bindings; the map's presence is the one contract.
- **Fail-closed enforced only at each mutating call site** (no seam-level
  invariant). Rejected — makes "never write an unmanaged label" a discipline to
  remember at every site rather than a structural property, exactly the
  scatter-and-drift failure mode the single seam exists to prevent. The seam-level
  invariant makes the unsafe direction unreachable; the per-site guard becomes a
  redundant outer layer, not the structural property.
- **A seam-level fail-closed invariant *without* the sole-constructor premise**
  (the seam emits no write-label, but writers may still string-format labels
  inline). Rejected — this is the gap that made the invariant merely asserted: a
  writer that never asks the seam is unconstrained by the seam's refusal, so the
  ~26 inline-literal write-path sites would each remain a place the property can be
  violated. Sole-constructor (writers obtain a write-label only via the seam, the
  inline sites refactored to route through it) is what makes the seam the only
  source of write-labels and therefore the structural guarantee.
- **Collapse "value-unresolvable within a bound axis" into axis-`unsupported`**
  (one degradation path for both). Rejected — a missing *value* (AUJ's absent
  `[Feature]` / `[Umbrella]` title-prefix) would degrade the *whole* `type` axis to
  advisory, silently softening the type-keyed Feature-in-Feature containment
  invariant that DEC-036 D4 holds **hard**. The fourth arm degrades only rules
  depending on the missing value, never the axis as a whole.
- **Default a degrade-signalled rule with no severity knob to advisory.** Rejected
  — fails *open*: a hard containment invariant (prose, no `*_severity` field) would
  soften the moment any input touching it went indeterminate. The fail-safe default
  is to hold the rule at its authored (hard) severity until a knob is explicitly
  added.
- **Fold the board-vs-label switch into the seam now** (one resolution surface for
  every substrate question). Rejected *for v1* — board-vs-label is a kit-internal
  sub-choice (which kit-managed encoding) at a different layer from the
  adopter-immutable remap the seam owns; unifying them with no second demanding
  consumer is speculative generality (COR-007). The seam composes over the inline
  switch; unification stays a later option.
- **A brownfield-specific lifecycle resolution path** parallel to the
  greenfield detector. Rejected — forks DEC-033's engine contract and forces
  ADR-023's fold to handle two shapes; a detector swap over a reduced state set
  keeps one engine and one fold.

## Implications

- **A read-path seam over the axis consumers** that `classification.yaml`,
  `issue-types.yaml`, `git-conventions.yaml`, and the lifecycle detector resolve
  through; greenfield (no map) is byte-unchanged because the seam returns the
  identity. The seam's *placement and signature* land with the trunk Feature
  (DEC-036), citing this contract for the resolution semantics and the
  fail-closed invariant.
- **Fail-closed is a tested invariant of the seam — and the test has two halves,
  because the property is two-part (sole-constructor + emit-no-write-label).** The
  Feature pins it with a golden analogous to ADR-024's `--json` byte-stability —
  but ADR-024's golden works *only because* it also asserts `render_status_json`
  **never calls** `wrap()`; without that structural half the byte-test would pass
  while a presentation call leaked in. The constructor analogue is mandatory here:
  (a) a **resolution test** — *the seam never resolves an `unsupported` / absent /
  indeterminate axis to a write of the kit's own label* (the emit-no-write-label
  half); **and** (b) a **sole-constructor guard** — a grep/AST check that **no
  mutating script formats an axis-label literal** (`<axis>:<value>` string-built on
  a write path), the analogue of ADR-024's "never calls `wrap()`." Without half
  (b) the resolution test passes while the bug is live — every inline-literal
  writer bypasses the seam, exactly as a stray `wrap()` call would bypass ADR-024's
  byte-stability. Half (b) is what makes the invariant structural rather than a
  per-site convention; it also continuously verifies the ~26-site refactor stays
  done. Both halves together are the resolution-layer expression of EPIC #217
  constraint 1.
- **Known boundary of guard half (b):** the grep/AST guard keys on a *literal* axis
  prefix in source (`f"type:{v}"`, `"type:" + v`, `":".join`, `.format`) — it
  catches every construction *shape* present today (scan-all over all non-seam
  scripts), but a *variable*-prefix construction (`prefix_var + value` where
  `prefix_var == "type:"`) evades it by design — that is the seam's own shape, which
  is why the seam module is the one allow-listed exception. No call site does this
  today; flagged so a future author does not mistake the guard for total. The seam
  being the sole *named* exception is what keeps that boundary safe.
- **The ~26-site refactor is in-scope for the trunk Feature.** Routing every
  write-path label through the seam (retiring the inline `f"type:{...}"` /
  `f"state:..."` constructions in `create-issue` / `move-issue` / `bootstrap` /
  `promote-issue` / the workstream mutators) is the work that makes sole-constructor
  real. The grep/AST guard above is its regression net.
- **Severity-field coverage remains DEC-036 schema work.** How a given degraded
  rule softens (the `*_severity` knob, added where missing) is the consumer's
  story; the seam only signals "degrade." Adding the missing knobs (containment
  parent-requiredness, parent-ref hard-rejects) is the Feature's in-scope schema
  work, not this contract.
- **No `workflow.yaml` schema change for the lifecycle remap.** Per DEC-036, the
  lifecycle binding is a detector swap (a new predicate + a `substrate-map.yaml`
  binding), not a `workflow.yaml` `schema_version` bump — so it must NOT
  re-trigger DEC-033/DEC-034's warn-on-override migration. The read-path seam
  resolving a remapped detector does not touch `workflow.yaml`'s shape. Confirm
  at impl.
- **Carrier discipline held.** This ADR is pm-capability architecture; it does
  **not** name the cross-capability greenfield+brownfield bootstrap shape, which
  is COR-promotable on the second instance (living-docs, EPIC #234) per DEC-022's
  defer-until-second-instance order. Naming it here would jump that order and
  mis-place the carrier.
- **Relationship to records — no DEC-036 amendment needed.** Records the read-path
  contract for DEC-036 (the rule); composes with DEC-033 (lifecycle =
  detection-predicate swap over a reduced state set; the state-collapse and no-op
  are *DEC-036's* lifecycle decision, cited not restated) and DEC-034 (the closure
  fold reads the derived terminal — but its membership input *degrades* to
  indeterminate-holds-the-fold on flat-repo parent-refs, COR-037 precedence, rather
  than cleanly inheriting greenfield close-eligibility). Inherits ADR-022/ADR-023's
  fail-closed instinct at a new boundary (axis resolution) and ADR-024's "the
  unsafe direction is structurally unreachable" shape (with its constructor-guard
  half). The two refinements this ADR adds — the **value-unresolvable fourth arm**
  and the **no-knob-stays-hard fail-safe** — pin *how* the seam signals
  degradation; they are consistent with DEC-036's *what* (D4 keeps containment
  hard; point 3 names the missing-knob gap as in-scope schema work) and require
  **no DEC-036 amendment**. Does not restate DEC-036; cites it as the decision.
- **Acceptance gate.** This record is `proposed` — a forward design contract the
  maintainer accepts before the trunk implementation builds against it (per
  PRJ-005). It is **not** self-accepted.
