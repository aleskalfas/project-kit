---
id: COR-038
title: A process declares its cross-process connections as inert, visible metadata; the position engine stays pull-only
status: accepted
date: 2026-06-26
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

*A process may write down its connections to other processes as **inert metadata** — a label the engine never evaluates, only a rendering tool reads — so a project's whole configured cross-process wiring becomes visible and machine-readable. This adds no engine capability. The record also confirms the position-finding engine is **pull-only** (it finds where a subject is by detection over reality, never by events), scoped to position-finding, leaving any future reaction/automation layer a separate open question.*

## Context

The process substrate ([COR-033](COR-033-process-substrate.md)) lets capabilities author processes that **connect**: composition embeds one process in another and reads its terminal outcome ([COR-036](COR-036-process-composition.md)); cascade folds a child's subjects into a parent gate ([COR-037](COR-037-process-cascade.md)); and an ordinary gate predicate can read another process's reality. As capabilities compose in a real project — an issue-lifecycle, a design ladder, a delivery process, each shipped by its own capability and wired together for *this* project — the resulting topology is the load-bearing fact about how work actually flows. Yet it is **only partly visible**.

Two of those connection kinds are **declared and engine-visible** (the `subprocess` and `cascade` blocks the engine resolves and can narrate). Two are **invisible**: a gate predicate's dependency on another process lives inside opaque predicate code the engine treats as a black box, and a purely-advisory or externally-mediated coupling is declared nowhere at all. So a project cannot mechanically answer "show me the whole configured workflow" — the enforced edges are seeable, the rest are buried or tribal.

This record settles how to make *all* cross-process connections visible, after a design review ruled out the tempting wrong answers:

- **An engine gate kind that reads another process and enforces the dependency itself** — rejected. It narrates only *that* a dependency exists, never the *condition* (which stays in an opaque predicate), so its "first-classness" is largely illusory; and its safety rests on an **unenforceable** promise that the predicate reads a stable marker rather than a peer's flapping mid-flight position — the engine cannot tell the difference, so it would silently re-open the very thing the substrate forbids (reading a non-terminal peer position, which flaps; COR-033 P3).
- **A project-level "process-graph" manifest** that capabilities contribute edges to — rejected. It is a *second* wiring mechanism competing with COR-036/037's coupling-in-the-definition, and it re-opens the edge-ownership question the substrate already closed (an edge lives in the definition that owns the coupling).

A second question surfaced and needed settling: **is the substrate ever event-driven?** Its foundational guarantee is live detection — position is always re-derived by running predicates against current reality (COR-033 P3), the journal *records* moves but has no dispatch channel, and every cross-process read happens on the reader's own turn. The substrate is a **pull** machine. Whether to add a **push** channel (a transition firing into another process at the instant it happens) had not been decided.

## Decision

**In plain terms:** a process may *write down* its connections to other processes as a **label the engine never acts on** — pure declared metadata, shape-checked so it is uniform and machine-readable, that a rendering tool reads to draw the project's whole configured wiring. It adds **no engine capability**: the engine never resolves it, never gates on it. And the position-finding engine is confirmed **pull-only** — it answers "where is this subject, may it move?" by detection over reality, never by events — scoped to position-finding, leaving any future reaction/automation layer a separate, open question.

### 1. A process declares `depends_on` — inert, schema-validated connection metadata

A process **state** may carry a `depends_on` list. Each entry declares a connection to an `upstream` process (by `<capability>:<process-id>` address — the same address grammar composition and cascade use), a `relation` from a closed set (point 2), a `mode` (point 3), and a required `why` (the human-readable reason the render surfaces). The field is **additive and optional** — absent on every existing process, which validate byte-unchanged.

It is **inert by design — the first layer the engine never *evaluates*.** The engine's runtime operations (`status`, `can-move`, `move`, `validate`-of-position) **never read `depends_on`.** Its only two readers are static or out-of-engine: the **schema** reads it to *shape*-validate it (well-formed address, `relation`/`mode` from their closed sets, `why` present), and a future render — a tool outside the engine — reads it to draw the topology. Inert does **not** mean unschema'd: shape-validation is a *static* authoring concern (is this well-formed?), runtime resolution is a *dynamic* concern (what does it evaluate to now?) — they are independent. This is one level *more* inert than [COR-035](COR-035-process-invariants.md)'s invariants, which the engine *does* evaluate (it runs each check and surfaces violations on `status`) but does not act on at the move gate; `depends_on` the engine does not evaluate **at all**. Because the engine never evaluates it, a **malformed `depends_on` is a lint error at definition-authoring time, never a fail-closed gate** — it cannot affect whether any subject may move.

### 2. The relation set annotates only edges the engine cannot already see — enforced edges are *derived*, not annotated

`relation` is a closed set of exactly the connections that are otherwise **invisible**:

- **`informational`** — an advisory connection with no runtime effect (documentation of how processes relate).
- **`gates-on-readiness`** — a gate predicate enforces a condition on the upstream, but nothing *declares* the cross-process edge (the predicate is opaque); the annotation names the edge the predicate's code hides.
- **`triggered-by`** — an externally/connector-mediated coupling the engine never sees (point 3, `push`).
- **`constrained-with`** — a cross-subject invariant ("these two processes' subjects must satisfy a relation"), a distinct effect from a gate (a gate blocks one move; a constraint asserts an always-true relation across a crowd). Named now for visibility; its **enforcement stays deferred** behind COR-035's deferred cross-subject invariants slot.

**Composition and aggregation are deliberately *not* relation values.** A `composed-subprocess` or `aggregates` edge is already fully declared by the `subprocess`/`cascade` block the engine owns and resolves. Re-stating it as an annotation would be a *second copy of a fact* whose primary home is that block — and the two **will drift** (someone edits the wiring, forgets the annotation), leaving the inert copy to lie to the render, the one view people trust. This is forbidden by single-source-of-truth ([COR-006](COR-006-artifact-roles.md)) and is the derive-don't-store discipline applied to the config surface. So the render computes the composite as **derived edges** (read from the existing `subprocess`/`cascade` declarations) **∪ annotated edges** (`depends_on`) — every edge expressible exactly one way, no edge both. `depends_on` is precisely *the visibility layer for the edges the engine cannot see.*

### 3. The position engine is pull-only — a substrate invariant, scoped to position

Position is always re-derived live by detection over current reality (COR-033 P3); the engine has **no event/dispatch channel and gains none.** A connection's `mode` is `pull` or `push`, but `push` introduces **no eventing into the engine** — it means only "this edge is mediated outside the engine (by an external tool or out-of-engine binding glue); the engine does not pull it, and records it solely for visibility." A subject is never created, advanced, or notified by a fired event inside the engine.

**Scope of the pull-only ruling.** It governs **position detection** — where a subject is and whether it may move. It does **not** foreclose a future, *separate* reactive/automation layer — reactions, spawns, notifications, or fan-out invalidation that *act* when a transition happens (a different job at a different altitude, the substrate's deferred hooks/orchestration shape). What is permanently closed is narrow and load-bearing: **the position engine never becomes event-driven.** A reactive layer, if a binding ever needs one, is decided on its own merits and reads the substrate by polling, never by making detection event-sourced. Anyone who later wants the position engine itself to be event-driven must explicitly supersede this record.

This is **not a fifth engine extension point** (COR-033 P5): it adds no engine capability. It is the substrate's first **declaration the engine never evaluates** — distinct from COR-035's invariants, which the engine evaluates-and-surfaces but does not gate on — sitting *beside* the slots and making their wiring, and the wiring they cannot see, visible.

## Rationale

**Why inert-but-schema'd rather than an enforcing engine kind.** The goal is *visibility* of connections, and visibility needs uniform, parseable declarations so a render is a mechanical derivation, not a best-effort scrape — hence the schema. But making the engine *act* on the declaration re-introduces the enforcement the design review rejected: the engine can narrate the edge but not the condition (illusory first-classness), and it cannot enforce that a readiness check reads a stable marker rather than a peer's flapping position (COR-033 P3). Keeping the layer inert gets all of the visibility and none of that hazard; the actual enforcement stays where it honestly lives — a gate predicate the binding owns — which the annotation merely *names*. COR-035's report-only invariants are the precedent: declared and surfaced, but the engine does not act at the move gate.

**Why derive-don't-annotate.** Single source of truth (COR-006): an enforced edge's primary home is its `subprocess`/`cascade` block; an annotation copy is a restatement that drifts and, because the render is the trusted "whole workflow" view, drifts into a *lie*. Restricting `depends_on` to the edges with no enforcing declaration gives it a clean, non-overlapping role and makes the composite render trustworthy by construction.

**Why pull-only, and why scoped.** The substrate's whole determinism rests on live detection (COR-033 P3): the journal is an intent log, never the source of truth, and the live re-derivation is authoritative over it. A push channel would bring delivery, ordering, and retry semantics — an entire concurrency model the substrate consciously declined. But "position is found by pulling" does not imply "pkit may never react to a transition": reacting, spawning, and notifying are a *different job* (acting on a move, not finding a position) at the deferred orchestration altitude. Scoping the invariant to position keeps the determinism guarantee absolute while not foreclosing a legitimate future reaction layer by accident.

### Alternatives considered

- **An engine gate kind that resolves the cross-process dependency itself** (`upstream-gate`). Rejected — narrates the edge but not the condition (the condition stays in an opaque predicate); its "reads a stable marker, not a flapping position" guarantee is unenforceable, so it can silently read the forbidden peer position; and inert metadata delivers the real visibility at a fraction of the cost.
- **A project-level process-graph manifest** capabilities contribute edges to. Rejected — a second wiring mechanism rivalling coupling-in-the-definition; re-opens edge ownership; and for the enforced edges it would duplicate, it drifts.
- **A uniform annotation covering *every* connection** (including `composed-subprocess` / `aggregates`). Rejected — duplicates the enforced declarations and drifts; the render derives those instead.
- **A push/event channel in the engine.** Rejected — foreign to live detection (COR-033 P3); the genuine push use-cases (fan-out invalidation, spawn, external-tool reactions, notifications) are *actions on a transition*, a separate reactive layer, not position-finding — deferred to their own decision, not built into the position engine.

## Implications

- **The process schema gains an optional per-state `depends_on` list** — additive, absent on existing processes (no migration). The exact field layout lands in the process-area shape reference and `process.schema.json` (reference, not this record), per the COR-034/035/036/037 pattern of deferring field layout to the shape reference.
- **Shape-validation, not runtime.** A malformed `depends_on` surfaces as a definition-authoring lint failure (`decisions/schema validate`), never a runtime fail-closed gate. The substrate's correctness boundary (what may move) is untouched.
- **A future `pkit process graph` render** (named-deferred per [COR-016](COR-016-scripted-scenario-storyboards.md)'s ship-narrow discipline, built when it has a consumer) draws the configured composite as derived edges (from `subprocess`/`cascade`) ∪ annotated edges (`depends_on`), each labelled with its relation and mode.
- **The `constrained-with` relation is named now, enforced never** — until COR-035's deferred cross-subject invariants slot ships. Visibility costs nothing; enforcement waits for a binding.
- **Trigger/instantiate (the "kick off" connection) stays connector-mediated** — `mode: push`, engine-invisible; the substrate carries only the `triggered-by` annotation for visibility.
- **A capability binding carries the concrete edge.** Illustratively, a design capability's process may declare a `gates-on-readiness` `depends_on` toward a project-management issue process, with the actual readiness enforced by its own gate predicate and any kickoff handled by a connector — all authored in the *consuming* capability's own decision, the upstream untouched (the coupling-in-the-subscriber direction, the dual of COR-036's coupling-in-the-parent).
- **Pull-only is now a closed invariant of the position engine.** Future extension points inherit it; a reaction/automation layer, if ever pursued, is a separate decision that polls the substrate and may not make position detection event-sourced.
- **Surface change** — a new principle plus a schema field — bumps the backbone version on acceptance (per the project's versioning policy). Acceptance carries the two-maintainer sign-off the foundational rulings warrant: (i) pull-only as a closed invariant of the position engine, and (ii) the inert-declaration layer with the derive-don't-annotate rule as its load-bearing discipline.
