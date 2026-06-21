---
id: COR-031
title: Capabilities bind process definitions to a shared, content-free process substrate
status: proposed
date: 2026-06-21
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

Several disciplines run **staged, gated processes** — work that moves through ordered states with guarded moves between them: the project-management issue lifecycle, a design-maturity process, a trip-planning pipeline, a documentation-adoption process. The methodology already ships one such state machine fully realised (the project-management issue lifecycle). The shape recurs, and re-hand-rolling a bespoke engine per discipline duplicates the hardest part — the guarded state machine — and lets the copies drift. Per extract-on-recurrence (COR-007), it is time to lift the shared shape into a reusable substrate.

Two constraints shape how. First, only one instance is *shipped* today, so the extraction must be **grounded** — proven by rebinding the shipped instance plus one new concrete binding — not abstracted speculatively from a single case (COR-007's named failure mode). Second, the substrate must serve two demanding consumers: an automated agent using it as **durable memory** of where a process stands, and the same agent (or a human with no manual) relying on it to **validate** that each move is legal. A process engine an actor can talk its way past is worthless for both.

## Decision

The methodology adopts a shared, **content-free process substrate** — a state machine of states + guarded transitions + a per-subject position + an append-only journal + a self-explaining status view — that capability-owned **process definitions** bind to. The backbone owns the shape and the engine; each capability owns its own process definition.

**P1 — Vocabulary (one substrate, two altitudes).** *State machine* is the content-free substrate. A *process* is one discipline's substrate-bound journey over its own subjects (the depth altitude). An *orchestration* is a system of interacting processes (the breadth altitude). A discipline's existing lifecycle artifact is, under this scheme, a process definition and need not be renamed.

**P2 — Ownership.** The backbone owns the process *shape contract* (a shared schema fragment) and the engine. Each capability ships its **own** process definition as an instance that conforms to the shape and binds via the existing grammar (COR-023), addressable as `<capability>:<process-id>`. The substrate adds no new binding mechanism; capabilities stay independent, self-describing peers.

**P3 — The engine is a deterministic validator and a self-explaining memory.** Given a definition and observable reality, "where is this subject", "may it move from here to there", and "is it valid" are *definite* answers. The status view renders where the subject is, why, how it got there, and what it may do next — each with a **live** check, and the live check is authoritative over any prose label.

**P4 — Gates must be checkable.** Every transition gate reduces to either a deterministic predicate the engine evaluates, or a recorded authorisation artifact the engine confirms exists **and that was produced by a different authority than the actor being gated**. An actor's own assertion that a gate passed is never sufficient — a judgment gate must leave a cross-authority, checkable trace.

**P5 — Name broad, ship narrow.** The shape *names* the full design space; the engine *ships* only the minimal core — a single subject, state inferred from reality, guarded transitions, position, journal, and the status view. Richer capabilities — multiple keyed subjects, stored or hybrid state detection, transition side-effects, position-independent invariants, cross-subject breadth, dynamic (data-resolved or open) structure, and composition of one process inside another — are **named extension points that stay unbuilt until a real binding needs one** (COR-016). The full shape lives in the process area's reference, not in this record.

**P6 — Determinism survives dynamic structure.** A process may enumerate its transitions statically, resolve them at runtime from data over a *known* set of blocks, or declare an *open region* bounded only by invariants and an exit gate. In every case the engine stays a deterministic validator — a resolver returns a definite set; an open region reduces to a definite boundary check.

## Rationale

The shape genuinely recurs across more than one real discipline — exactly the recurrence extract-on-recurrence calls for (COR-007). Continuing to hand-roll a separate engine per discipline duplicates the subtle part and lets the copies drift; lifting it once, with the engine owned in a single place, removes that.

Backbone-owns-the-shape, capability-owns-the-instance (P2) is chosen over two alternatives. Generalising one capability's existing schema *in place* and having others borrow it would couple the shared shape to that capability's release cadence and bleed its domain-specific fields into the shared form. A single central content-bearing schema that every process binds to would force a change to the binding grammar and make every process depend on one shared namespace. Owning only the *shape* leaves the binding grammar untouched (COR-023), keeps capabilities as independent peers, and makes each process self-contained yet addressable — which is also what lets one process embed another as a reusable, caller-agnostic block.

Checkable, cross-authority gates (P4) are the substrate's load-bearing guarantee. Its whole value to an automated agent is being an honest referee and a trustworthy memory; a gate the gated actor can satisfy by asserting it — or by writing its own sign-off — is theatre, and silently turns "validated" into "claimed".

Name-broad / ship-narrow (P5–P6) follows directly from the grounding constraint: with one shipped instance, designing every variation axis now would lock in guesses about variation that has not yet appeared — the precise failure extract-on-recurrence warns against. Naming the space preserves the general vision; shipping only the grounded core keeps the substrate honest. Each deferred capability becomes real when a second binding actually disagrees with the first.

### Alternatives considered

- **Generalise the shipped capability's schema in place.** Rejected — couples the shared shape to one capability's cadence and bleeds its domain-specific fields into the shared form.
- **A central content-bearing process schema everything binds to.** Rejected — needs a change to the binding grammar (COR-023) and weakens capability independence.
- **Leave each discipline to hand-roll its own engine.** Rejected — the shape recurs across instances; duplicated engines drift (COR-007).

## Implications

- **A new backbone responsibility.** The backbone hosts a process shape contract (a shared schema fragment) and the engine (operations to resolve a subject's position, validate a move, execute a move, run invariants, and render the status view). This is a surface change; the affected component's version bumps per the project's version policy.
- **Grounding (the acceptance-gate of COR-007).** The substrate ships with the project-management process **rebound** onto it — proving the shape against the one shipped instance, with that capability's breadth, closure, and PR-sub-lifecycle fields kept capability-local — plus **one new concrete binding** as the grounded second instance.
- **Migration.** The rebind is an adopter-breaking schema-shape change, so it ships a migration at the capability tier in the same change-set (COR-010): idempotent and value-preserving (a shape transform that detects already-migrated state). A second migration is budgeted for when the breadth/orchestration layer later moves a capability's cross-subject fields into the shared shape.
- **Deferred extension points.** Each named-but-unbuilt capability in P5 is its own future decision when a binding demands it — not pre-authorised here.
- **Acceptance gate.** This record must be **accepted** before any capability is rebound or newly bound to the substrate; downstream capability records cite it.
- **Relationship to existing decisions.** The binding grammar (COR-023) is confirmed sufficient and left unchanged; this record is a worked application of extract-on-recurrence (COR-007) and of name-broad / ship-narrow (COR-016).
