---
id: DEC-043
title: Instance-ownership substrate is selectable — comment-log source of truth, derived description mirror
status: accepted
date: 2026-07-07
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** [project-management:DEC-035-instance-ownership] records which clone owns
an issue with a GitHub *label* (`instance:N`). Many real repos cannot create labels — org
policy locks label creation to admins, or the token lacks the scope. This record makes the
ownership marker's substrate **selectable**: keep the label where labels are creatable, and
add a **label-free** substrate that works everywhere. The label-free substrate is a small
**append-only log of ownership events posted as issue comments** (claim / handoff / abandon /
release), with a **derived, always-regenerable mirror of the current owner written into the
issue description** so a human sees who owns an issue at a glance without reading the log.
This refines DEC-035 to "ownership-substrate-*where-available*", exactly as
[project-management:DEC-039-containment-substrate-selection] refined
[project-management:DEC-005-linking-and-containment] to "native-*where-available*".

## Context

[project-management:DEC-035-instance-ownership] carries the ownership marker on an
`instance:N` GitHub label paired with the assignee, and its clash guard resolves a same-instant
collision by having the higher-numbered instance back off (lowest number wins), a tie-break both
clones compute from the labels alone. That design assumes the adopter can *create labels*.

A large class of repos cannot. Label creation is frequently an admin-only capability, and
fine-grained tokens routinely lack label-write scope. In such a repo DEC-035 is unusable end to
end: lazy `instance:N` creation is exactly the unmanaged-label write
[project-management:DEC-036-substrate-pluggable-adoption] forbids (its "never write an unmanaged
label" posture). So the label-locked repo — the one that most needs a way to tell its clones
apart — is the one where DEC-035 cannot run.

This is the substrate-availability problem DEC-036 exists for, applied to the ownership marker.
DEC-036's own axis map is the wrong home for the fix, though: its activation is *emergent by file
presence* — the mere existence of `substrate-map.yaml` flips every axis absent from it to
degraded. A greenfield repo that wants only label-free ownership must not thereby degrade its
classification axes. DEC-035 already reserved the ownership marker "its own schema home, not a
slot in the axes map"; that reservation is where the selector belongs.

The design was pressure-tested against two alternatives that both failed. A **single upserted
comment** cannot represent the coexistence DEC-035's tie-break needs — a third clone silently
overwrites it, no collision is ever detected. An **authoritative body region** is a whole-object
read-modify-write with no compare-and-set on GitHub issue edits: two clones each read an empty
body and the second clobbers the first, so the deterministic lowest-wins tie-break degrades to
last-writer-wins — the exact silent double-work the guard exists to prevent. Both failures point
the same way: the authoritative substrate must be made of **discrete, per-object-atomic writes**,
which is what labels are and what per-instance comments can be.

## Decision

**The instance-ownership marker binds to a selectable substrate: the `instance:N` label where
labels are creatable, a comment-log-plus-derived-mirror where they are not.** DEC-035's label
mechanism is kept as one option; this adds the label-free option and the selector.

**1. Refine DEC-035 to substrate-*where-available*.** DEC-035's marker is no longer
unconditionally a label. It resolves through a selector; the label is one binding among two.
This refines DEC-035 in place (reciprocal note, same change-set), it does not supersede it —
the label mechanism and the clash-guard semantics stand.

**2. A selector in instance-ownership's own schema home.** Values `label` and `comment`, in
the schema home DEC-035 reserved for the ownership marker — **not** in `substrate-map.yaml`, so
that a repo opting into label-free ownership does not trip DEC-036's emergent-activation and
degrade its unlisted axes. **The default is `comment`** (the universally-safe substrate); `label`
is the opt-in for repos whose operator knows labels are creatable. The default is deliberately
*not* keyed off the presence of a substrate-map, because the motivating repo — label-locked but
otherwise greenfield — has no substrate-map at all yet still cannot use labels.

**3. In `comment` mode the source of truth is a per-instance, append-only ownership event
log.** Each ownership event (claim / handoff / abandon / release) is a discrete GitHub issue
comment carrying a hidden machine stamp plus visible human text. Comment-create is per-object
atomic, so the substrate faithfully preserves DEC-035's guarantees:

- **Same-instant coexistence and the lowest-wins tie-break hold as written** — two clones each
  post their own event, the re-read sees both, the higher instance backs off. No whole-object
  race, because no clone writes another clone's object.
- **Authenticity rides `author.login`** — a marker is trusted only if authored by the expected
  assignee account; a pasted forgery from another account is ignored. (This is *stronger* than
  the label substrate, where a label carries no actor.)
- **History is preserved** — handoffs between a person's clones and abandonments of control are
  first-class log entries, not just current state. The log aligns with, and does not duplicate,
  the handoff audit comment [project-management:DEC-026-work-ownership-lifecycle] already posts.

**4. The current owner is mirrored into the issue description as a derived, regenerable view.**
Because "nobody wants to read the log," the read seam folds the event log to a current-owner
summary and writes it into a capability-owned region of the issue description. This region is
**derived, never authoritative** — the comment log is its regeneration spine. It is therefore
safe to full-overwrite: if a human edits or deletes it, or a write races, the read seam
regenerates it from the log; no ownership record is lost. This is the
[project-management:DEC-039-containment-substrate-selection] D4 pattern (a generated,
regenerable view whose truth lives elsewhere), with the roles of comment and body swapped —
here the *comments* are authoritative and the *body* is the view.

**5. The write path is a sole-constructor pinned by a sibling ADR.** The comment-log write and
the description-mirror render join the substrate seam family (label read-path, field/milestone
write-path, containment resolution) as a fourth sibling: one read seam, one construction point,
a grep/AST guard, failure-posture-neutral. The ADR is authored by the architect once this
record settles.

**6. Realm-blindness is preserved.** The selector and both substrates are pm-layer
side-effects; instance ownership remains, per DEC-035, never an input to a gate, a transition,
or the cascade fold. The engine stays content-free.

## Rationale

**Why comments, not a body region, for the source of truth.** Both are label-free and both bulk-read
cheaply (`gh issue list --json comments` returns comment bodies inline, just as `--json body`
returns the body). The decider is *atomicity*: a body region is a whole-object read-modify-write
with no CAS, so concurrent claims clobber and the clash tie-break silently degrades to
last-writer-wins; per-instance comments are discrete atomic objects, so the tie-break holds
exactly as the label set's does. Correctness under concurrency, not read cost, chose the
substrate.

**Why a derived mirror rather than either substrate alone.** Comments give atomicity, authenticity,
and history but bury the current owner in a thread. A description mirror gives at-a-glance
visibility but, if authoritative, has no regeneration spine and is destroyed by a stray edit.
Composed — comments authoritative, description derived — each covers the other's weakness, and
the mirror is safe *precisely because* it is not the source of truth.

**Why the selector lives outside `substrate-map.yaml`.** That file's presence degrades every
unlisted axis (DEC-036 emergent activation). Ownership is explicitly not a classification axis
(DEC-035), so folding its selector into the axis map would make an ownership-only opt-in
silently degrade a greenfield repo's type/priority/workstream/state. DEC-035 already reserved a
separate home; using it keeps the two concerns independent.

**Why `comment` is the default.** The feature exists for repos that cannot create labels. Keying
the default off greenfield-ness (label) would pick the unsafe substrate for exactly the
motivating case — a label-locked repo with no substrate-map. Defaulting to the universally-safe
substrate and making `label` the opt-in fails safe.

### Alternatives considered

- **Single upserted comment.** Rejected — one mutable comment cannot represent the coexistence
  the tie-break needs; a later clone silently overwrites it and no collision is detected.
- **Authoritative body region.** Rejected — whole-object read-modify-write with no CAS; concurrent
  claims clobber and lowest-wins degrades to last-writer-wins, reintroducing the silent
  double-work DEC-035's guard prevents. Kept only as a *derived* view (point 4).
- **Selector inside `substrate-map.yaml`.** Rejected — DEC-036 emergent activation would degrade
  a greenfield repo's other axes on an ownership-only opt-in.
- **Projects-v2 field / external committed registry / reactions.** Deferred or rejected: the
  board field is not universal (its own permission gate) and is named-not-built per [pkit:COR-007];
  a committed registry is what DEC-035 explicitly rejected (and concurrent clones would need
  push/pull to see each other); reactions are per-user single-valued and cannot encode
  `(assignee, instance)`.

## Implications

- **DEC-035 gains a reciprocal refinement note** (marker substrate is selectable; label is one
  binding). Both stay `accepted`/live. **This record refines an accepted foundational decision,
  so promotion `proposed → accepted` requires explicit maintainer sign-off**, same class as
  DEC-035's own handoff-contract sign-off and DEC-039's DEC-005 refinement.
- **A new schema home** for the ownership marker declares the selector (`label` | `comment`,
  default `comment`) and the comment-stamp + description-region formats, referencing the
  [project-management:DEC-014-validation-severity-model] tokens for the guard. It is *not* a slot
  in `classification.yaml`.
- **A fourth sibling ADR** (architect-owned per [pkit:COR-025]) pins the comment-log read seam,
  the description-mirror sole-constructor, the grep/AST guard, and mixed-mode precedence (a repo
  holding both a lingering `instance:N` label and a comment-log marker resolves at the seam).
- **DEC-009 reciprocal note** — the derived description-mirror region is a capability-owned,
  do-not-edit class of body content that [project-management:DEC-009-living-documents] does not
  yet model; it needs an explicit refinement note (authored in the same change-set). The region
  is *derived*, which is a lighter interaction than authoritative body state.
- **The shared audit-log facility** (its own DEC) carries the comment-stamp + render spec; the
  ownership event log is that facility specialised with ownership event types, and the existing
  promote / bypass / handoff audit strings migrate onto it rather than running parallel.
- **Read cost stays one call** — the description mirror is returned inline by
  `gh issue list --json body`; the comment log is read only to reconcile or show history.
- **Implementation is gated** — this is a surface change (new selector, new substrate, new schema
  home, schema formats) and bumps the capability version on landing per [pkit:PRJ-002]; a
  migration is unnecessary because greenfield (label) behaviour is byte-unchanged and the new
  default applies only to repos newly opting into instance ownership.
