---
id: ADR-020
title: Ship the process engine in the binary, not propagated in-tree
status: accepted
date: 2026-06-21
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

The process substrate ([COR-031](../../../.pkit/decisions/core/COR-031-process-substrate.md)) has three parts: a **shape contract** (a `_defs` JSON-Schema fragment), per-discipline **process definitions** (capability-owned instance schemas), and a content-free **engine** that interprets them and is invoked as `pkit process …`. COR-031 settled that the backbone *owns* the engine; it did not settle *where the engine code physically lives*. Two homes were on the table, and the choice sets the precedent for where every future substrate engine lives:

- **In the binary** — `src/project_kit/process.py`, shipped with the installed `pkit` tool (like `schemas.py`, the `permissions` CLI).
- **Propagated in-tree** — engine code synced into each adopter's `.pkit/` tree, the path the permission core took with `decide.py`.

The permission precedent (ADR-002 / ADR-003) made the propagated path look like the established pattern for "neutral shared logic", so the choice needed deciding on the merits rather than by surface analogy.

## Decision

**In plain terms:** the engine ships inside the `pkit` tool, not copied into each adopter's tree — because nothing below the tool layer needs to import it (unlike the permission core).

The process engine ships **in the `pkit` binary** (`src/project_kit/process.py`), registered as a static `pkit process` command group, and is invoked only as a CLI subprocess. What propagates to adopters is the **shape contract** (`_defs/process.schema.json`), the **`.pkit/process/` README spec**, and the per-subject **journal's adopter-owned `project/` home** — **not the engine code**.

## Rationale

Two arguments for propagating the engine were weighed; neither overcomes a principled difference between the engine and the permission core.

**Engine/schema drift is real but bounded — and propagation does not remove it.** Shipping the engine in the binary while the schema and process definitions sync in-tree means the two can sit at different versions. But this is the project's *existing, deliberate* design: the binary already interprets propagated schema'd data everywhere — decision records, manifests, capability `package.yaml` command trees, the privilege catalog. If this split were dangerous it would already be dangerous for the dispatcher. And the lockstep is already enforced at the tier where the binding lives: a capability's process definition pins `requires_backbone`, and `pkit upgrade` refuses to install it against an incompatible engine. Propagating the engine would not buy lockstep-by-construction — a thin `src/` CLI wrapper remains either way, so it *adds* a third version axis (in-tree engine + in-tree schema + wrapper) rather than removing drift.

**The permission precedent is import-constraint-driven, and the engine has no such constraint — so it cuts against propagation, not for it.** ADR-003 is explicit that `decide.py` is propagated for one load-bearing reason: the PreToolUse hook runs below the tool layer in a process where `pkit` is **not importable**, and the same-code invariant requires the hook and the CLI to run identical code. Version-pinning and in-PR auditability are *consequences* of that propagation, never its cited cause. The process engine has exactly **one consumer and one invocation mode** — `pkit process …` as a CLI subprocess (COR-031 P3). There is no below-the-tool-layer caller, no import-constrained context. ADR-003 already rejected generalising a propagated shared library on the first instance (its `.pkit/lib/` deferral), naming it speculative generality per [COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md): extract only when a *second* instance sharing the *triggering constraint* appears. Propagating the engine because permissions did — on purpose-symmetry ("both enforce gates") rather than constraint-symmetry ("both have a consumer that cannot import `src/`") — is precisely the failure that discipline guards against.

### Alternatives considered

- **Propagate the engine code (or a "same-code core" + thin `src/` wrapper), mirroring the permission core.** Rejected: it adopts the permission precedent on purpose-symmetry rather than the import constraint that actually drove it; it adds a version axis without removing drift; and it is the speculative generality COR-007 and ADR-003 explicitly defer until a real recurrence.

## Implications

- **Placement.** The engine lives at `src/project_kit/process.py`, registered as a static `pkit process` group in `cli.py` (precedence over dispatched capability commands). Only the `_defs` schema + the `.pkit/process/` README spec (+ the journal `project/` home) propagate; add `process` to `PROPAGATED_AREAS` so the spec lands in adopter trees — carrying spec + journal home, **not** engine code.
- **Gate-honesty (fail-closed on drift).** Because the engine and definitions *can* version-skew, the engine must treat an unrecognised or schema-future gate as **fail-closed**: refuse the move and surface the version mismatch, never silently pass. This mirrors the fail-loud amendment forced on the permission hook (ADR-002) and ensures drift, if it occurs, fails safe.
- **Recorded trigger to revisit.** If a second engine consumer ever appears that *cannot* be a subprocess — e.g. a harness hook checking "may this subject move here?" live at tool-call time — the import constraint that drove permission propagation would then apply to the engine too. At that point propagate, and the home becomes the shared `.pkit/lib/` that ADR-003 deferred (two neutral propagated libraries = the recurrence test finally met).
- **Precedent.** This sets where future substrate engines (COR-031's deferred breadth/orchestration layer; the next staged-process consumer) are homed: in the binary, unless a non-subprocess consumer forces propagation.
- **Relationship to records.** Implements COR-031 (engine ownership); consciously declines the ADR-003 propagated-code path, with the import-constraint distinction as the reason; applies COR-007's recurrence test.
