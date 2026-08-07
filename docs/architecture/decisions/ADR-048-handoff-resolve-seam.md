---
id: ADR-048
title: Hand-off downstream resolution is a binding-supplied resolve predicate; health is a sibling reader beside the engine
status: accepted
date: 2026-08-07
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

*How the missed-hand-off check ([COR-042](../../../.pkit/decisions/core/COR-042-process-health.md)) answers "is there a downstream subject for this upstream one?" without the engine enumerating anything: a **two-predicate seam** — a binding-supplied **upstream candidate source** plus a binding-supplied **`resolve` predicate** (upstream id → downstream id(s) / absence) — with the three mechanism candidates from the demanding adopter's request (reverse index, naming convention, declared-root read) all expressible as implementations of that one seam. The health surface itself is a **sibling module beside the engine**, consuming the engine's per-subject position resolution, never inside the runtime paths.*

## Context

COR-042 fixes the rules of the missed-hand-off check — including the contract's field set (trigger state + two seam predicates) — but defers the mechanism: given an upstream subject at its trigger state, the check must determine whether a downstream subject picks it up, without an engine subject-listing API (COR-032) and without the report drifting from reality. The demanding adopter's request (the trip-planner adopter's scratchpad note `2026-08-06-missed-handoff-detection.md`, relayed via issues #608/#609) named three candidate mechanisms and left the choice to this project: a **reverse index** (upstream → downstream ids, maintained somewhere), a **naming convention** (the downstream id derived from the upstream id), or a **read of a declared adopter root** (scan the downstream's artifact root for a binding marker, e.g. a unit file's `screens:` list).

The engine already has one worked answer to "read across a crowd without owning it": cascade's two-predicate seam (COR-037 / ADR-023) — a `members` source yields candidate ids, a per-candidate test confirms each one, both binding-supplied registered commands run through the predicate runner. The question is whether hand-off resolution gets its own rival mechanism or reuses that shape.

## Decision

**Reuse the seam shape; don't pick a mechanism.** The hand-off contract's two predicates are binding-supplied registered commands under the existing predicate-runner contract:

1. **`candidates`** — threaded with the contract's upstream process address and trigger state; yields the upstream candidate subject ids (the analogue of cascade's `members`). Each candidate's position at the trigger is then confirmed **one subject at a time** through the **engine's existing single-subject position resolution** — the source proposes, live detection disposes.
2. **`resolve`** — threaded with one upstream subject id; returns the corresponding **downstream subject id(s)**, or an explicit **absence**, or errors (= indeterminate, fail-closed into the report and exit code per COR-042). The health surface never interprets *how* the binding found the answer.

All three candidate mechanisms become implementations a binding chooses inside its `resolve`: a naming template (derive the downstream id and check existence), a scan of the binding's own declared artifact root (e.g. grep unit files for the screen binding), or a maintained mapping if a binding insists on one — the seam is indifferent, and the engine stays content-free.

**Note on the seam analogy's limit.** This is the *shape* of cascade's seam, not the same seam. Cascade's per-candidate confirm is a **binding-supplied** `membership` test; health's confirm is the **engine's own** at-exact-state position read. That choice is what hard-codes COR-042's live at-the-trigger snapshot (and its ephemeral-trigger consequence) at the mechanism level — deliberately: it keeps confirmation deterministic and engine-owned, and one seam predicate fewer for bindings to write. The rejected symmetric alternative is below. The crossing this machinery constitutes is sanctioned by COR-042 (its "second bounded cross-subject read" section); the discipline — binding-supplied sources, per-subject confirmation, point-to-point resolution, no listing API — holds in the same form COR-037's seam established.

**Placement: `health` is a sibling reader module beside the engine**, in the process area's code home next to the render — not inside the engine's runtime paths. It reads process definitions for `depends_on` contracts, calls the two seam predicates, and calls the engine's public per-subject position resolution for confirmation. The runtime operations' code paths (`status` / `can-move` / `move` / `validate`) import nothing from it and never read `depends_on` — keeping COR-042's re-scoped reader-set claim structurally true by module boundary, not by convention.

**Note on the render pairing's asymmetry.** COR-042 pairs `health` with the graph render as out-of-runtime readers, but they are different kinds of reader: the render reads *declarations only* — never a live position, never a predicate, never the engine (its safety pin, asserted by its tests). `health` **does** read live reality — positions via the engine, plus two binding predicates — and is safe by **report-only**, not by never-reading. The module-boundary claim above gets the same pinned treatment the render got: a test asserting the runtime operation paths import nothing from the health module.

## Rationale

- **One seam subsumes three mechanisms.** Choosing any single mechanism would either bake drift in (a **stored reverse index** is derived data that goes stale — the derive-don't-store discipline; a drifted index makes the one report people trust lie, the exact failure COR-038 built the inert layer to avoid), or bake rigidity in (a **naming convention** couples two processes' id spaces and collapses on fan-in / fan-out, which COR-042 explicitly admits). The **declared-root read** is sound but binding-specific. Making resolution a predicate turns all three into private implementation details of the binding that owns the domain knowledge anyway — the same reasoning that made cascade's membership binding-supplied (ADR-023).
- **COR-032's discipline holds by construction.** The engine gains no listing API and holds no cross-process mapping; candidate sets originate in binding code; every engine touch is per one supplied subject id. The read-across-a-crowd itself is a new, second crossing — sanctioned and bounded in COR-042, not borrowed from COR-037's fold-scoped sanction.
- **Module-boundary honesty.** COR-042 re-scopes COR-038's "never evaluated" to "never evaluated by the runtime operations." Housing health inside the engine would make that claim a prose promise; housing it as a sibling consumer of the engine's public resolution makes it checkable by import graph — and pinned by test.
- **Fail-closed uniformity.** `resolve`'s error/absence distinction mirrors cascade's indeterminate-vs-determinate-empty split (COR-037): absence is a determinate answer ("no downstream — a miss"); an error is indeterminate and can never be read as "no miss". One discipline across both cross-subject machines, extended by COR-042's uninterpretable-contract rule (unresolvable upstream address or phantom trigger state = indeterminate, evaluated health-side).

### Alternatives considered

- **Stored reverse index as the mechanism** — rejected (drift; lying report; contradicts derive-don't-store).
- **Naming convention as the mechanism** — rejected as *the* mechanism (id-space coupling; fan-in/fan-out); fine as one binding's `resolve` implementation.
- **Engine-side declared-root scan** (the engine reads a configured downstream root directly) — rejected: an engine-owned listing over adopter artifacts is precisely the subject-listing shape COR-032 forbids, and it drags artifact-layout knowledge into the content-free engine.
- **Single predicate (resolve only, no candidates source)** — rejected: without a candidate source the health surface cannot find the upstream side at all without enumerating; the two-predicate split is what cascade already proved out.
- **Binding-supplied confirmation predicate (full cascade symmetry)** — a third seam predicate confirming each candidate binding-side could express richer trigger semantics (at-or-beyond, state sets). Rejected for the narrow ship: engine-side at-state confirmation is simpler, deterministic, and one less predicate per binding; the richer trigger form is named-deferred in COR-042, and un-deferring it would revisit this choice.
- **Health inside the engine runtime** — rejected per module-boundary honesty above.

## Implications

- Implementation lands the two seam fields in the hand-off contract sub-block (shape reference + `process.schema.json`), the sibling `health` module beside the render in the process area's code home, and the CLI verb wiring — all gated on COR-042's acceptance (this record's acceptance follows the COR's, never precedes it).
- The predicate-runner contract is reused unchanged; no new execution mechanism.
- A **pinned boundary test** asserts the runtime operation code paths import nothing from the health module (the mirror of the render's never-invokes-the-engine pin).
- Tests exercise the seam with fixture bindings covering the cases COR-042 fixes: fan-in / fan-out resolution, absence vs error, uninterpretable contracts (phantom trigger, unresolvable address), determinate-empty vs broken-empty candidate sources, singleton endpoints, the ephemeral-trigger authoring smell, and a fixture mirroring the demanding adopter's seven-unpicked-upstreams case.
- The grounding adopter's binding implements `resolve` as a scan of its own delivery-unit root (its units declare their upstream bindings), and `candidates` from its screens root — both inside its capability, no engine change.
