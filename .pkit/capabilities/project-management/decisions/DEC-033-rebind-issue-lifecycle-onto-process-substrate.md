---
id: DEC-033
title: Rebind the issue lifecycle onto the process substrate (keyed)
status: accepted
date: 2026-06-21
author: Ales Kalfas
---

## Context

The issue-lifecycle state machine (`schemas/workflow.yaml`) is the shipped instance the shared process substrate was generalised from ([COR-033](../../../decisions/core/COR-033-process-substrate.md)). COR-033's grounding (per [COR-007](../../../decisions/core/COR-007-pattern-extraction.md)) calls for rebinding this capability onto the substrate to prove the shape against a real, shipped instance.

The seam holds by inspection: `workflow.yaml`'s `states` and `transitions` map onto the substrate shape, while `cascade`, `closure_triggers`, `pr_state_effect`, `source`, and `display_name` are project-management-specific and stay capability-local (the substrate's permissive `additionalProperties` on `process`/`state`/`transition` admits them). But the issue lifecycle tracks **many** issues, each at its own position — a **keyed** process — whereas the substrate shipped `singleton`-only. This rebind is the binding that drove shipping the `keyed` slot — the substrate widening itself lives in [COR-032](../../../decisions/core/COR-032-keyed-process-subjects.md) (name-broad / ship-narrow working as intended); this record is the pm-side binding.

## Decision

**In plain terms:** restructure `workflow.yaml` so its states + transitions conform to the substrate shape, ship the `keyed` cardinality the issue lifecycle needs, move the state-machine mechanics into the engine (pm keeps its domain side-effects + cascade), and migrate installed adopters.

**D1 — Bind as a keyed process.** The issue lifecycle is keyed — many issues, each at its own position — relying on the `keyed` cardinality slot shipped by [COR-032](../../../decisions/core/COR-032-keyed-process-subjects.md) (this rebind is the binding that drove it). The substrate widening (schema enum + engine subject-threading) lives in COR-032; here pm declares `subject: { cardinality: keyed, key: issue-number }`. Cross-subject effects (the parent/child cascade) are *breadth* — altitude-2, still deferred — and stay capability-local.

**D2 — Conform the definition.** Each state replaces its `inferred_from` prose with `detection: { mode: inferred, predicate: { run: <pm-detector> } }`; each transition gains `gate: { kind, predicate }` (the checkbox close-gate → `deterministic`; the PR-merge gate → `authorisation-artifact`, cross-authority). `subject: { cardinality: keyed, key: issue-number }`; add `id` + `version`; bump `schema_version` 2 → 3.

**D3 — pm-local fields stay.** `cascade`, `closure_triggers`, `pr_state_effect`, `source`, `display_name` remain in `workflow.yaml` (the engine ignores them); pm's wrappers continue to run the cascade + closure semantics. The shared shape is not polluted with pm domain fields.

> **Amended in part by [DEC-034](DEC-034-cascade-slot-binding.md).** Once the shared cascade slot shipped ([COR-037](../../../decisions/core/COR-037-process-cascade.md)), pm's **closure** cascade was rebound onto it (the slot is itself content-free, so D3's boundary rationale is preserved). The *other* D3 fields (`closure_triggers`, `pr_state_effect`, `source`, `display_name`) and pm's **forward** cascade remain capability-local as decided here.

**D4 — Predicate commands.** pm ships read-only detector/gate commands (lifting `move-issue`'s inference: branch-exists, PR-merged + cross-authority, checkboxes-ticked) that return the structured JSON the engine's predicate runner expects, registered in `package.yaml`.

**D5 — Delegate to the engine.** `move-issue` and the verb-subject wrappers delegate the state-machine mechanics (position / validation / journal) to `pkit process`; pm retains its domain side-effects (branch/PR creation, assignment, cascade, closure).

**D6 — Migration (warn-on-override only).** `workflow.yaml` is kit-owned and delivered by `sync`, so the v3 definition is **authored source**, not a rewrite of adopter state. Per the existing v2 migration precedent, the capability-tier migration ([COR-010](../../../decisions/core/COR-010-resource-lifecycle.md)) only **detects an adopter override** (a `project/schema-overrides/workflow.yaml`) still at `schema_version` 2 and **warns** them to hand-update it — it never rewrites the kit-shipped file or auto-edits project-owned content. Idempotent (no override, or already-current → exit clean).

## Rationale

Rebinding the shipped instance is COR-033's grounding requirement — it proves the substrate shape against real, exercised content rather than a fixture, and it is the "clean subset" test (if states/transitions could not separate from the pm-local fields, the seam would be wrong; they do). `keyed` is shipped now because *this* binding demands it — the discipline is to un-defer a named slot when a real binding needs it, not before. Keeping `cascade`/`closure_triggers`/`pr_state_effect` capability-local is the boundary that keeps the substrate content-free and lets other capabilities (which have no containment tree) bind without inheriting pm's breadth. The schema-shape change is adopter-observable, so a migration ships in the same change-set (COR-010) — but because `workflow.yaml` is kit-owned, that migration only warns adopters holding an override, rather than rewriting any live file.

### Alternatives considered

- **Defer the pm rebind until `keyed` ships separately.** Rejected — pm *is* the binding that grounds `keyed`; splitting them would ship `keyed` speculatively (the COR-007 failure) with no consumer.
- **Pull `cascade`/`closure_triggers` into the shared shape.** Rejected — they are pm-domain breadth/closure semantics; the architect's boundary keeps them capability-local so the substrate stays content-free.
- **Model each issue as its own singleton process.** Rejected — the issue lifecycle is one process over many subjects; that is the definition of `keyed`, not many singletons.

## Implications

- **Surface change.** A `schema_version` bump on the kit-shipped `workflow.yaml` + delegated CLI behaviour (the `keyed` widening itself is COR-032's surface change). The `.pkit/VERSION` bump lands with the change-set's PR (per the project's version policy); the warn-on-override migration ships in the **same** change-set (COR-010).
- **Behaviour parity is the acceptance bar.** The rebind is structural, not behavioural — the issue lifecycle must behave identically post-rebind. Concretely, the producer's tests must prove: (a) a **position truth-table** — identical state resolution across every (issue-state × milestone × labels × board) input, pre/post (state *order* in `workflow.yaml` is now load-bearing, since the engine returns the first matching detection); (b) **transition legality + gate outcomes** match (checkbox close-gate, PR-merge cross-authority); (c) **bypass/audit/TTY-confirm/membership/cascade** behaviours preserved through the wrapper (these stay wrapper-side, not engine gates); (d) parent in-progress inference (a descendant walk) runs **pm-locally**, not in the engine.
- **pm is the first keyed binding** — it grounds the `keyed` slot shipped by COR-032.
- **Tooling gap noted:** capability DECs are not stampable by `pkit new decision` (only core/project/adr); this record was hand-authored. Worth filling that gap separately.
- **Acceptance gate.** This record must be `accepted` *after* COR-032 (which it cites) is accepted; it cites COR-033, COR-032, COR-010, COR-007.
