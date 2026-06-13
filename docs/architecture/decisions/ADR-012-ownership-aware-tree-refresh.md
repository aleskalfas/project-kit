---
id: ADR-012
title: An ownership-aware tree-refresh primitive — one destructive-copy mechanic that never clobbers adopter-owned content
status: accepted
date: 2026-06-12
author: Ales Kalfas <kalfas.ales@gmail.com>
---

## Context

[COR-001](../../../.pkit/decisions/core/COR-001-content-mechanisms.md) defines the propagation / extension / install-time-seeding contracts and the **no-shared-files invariant**: every file has exactly one owner — kit propagates and overwrites kit-owned files, while adopter-owned `project/` files are *seeded once* and thereafter never overwritten or removed. The *destructive* half of that contract — refreshing a destination tree from a source while preserving adopter-owned paths — was being re-derived ad-hoc at each copy site. `_copy_tree` (install.py) and `_copy_capability_tree` (capabilities.py) each implemented their own copy-and-prune logic.

The forcing case: the #332 clobber. `_copy_capability_tree` reimplemented its copy as a blanket `rmtree` + recopy and **forgot the rule** — wiping an adopter's customised `project/` files on every sync. The #333 cross-path preservation test pinned the corrected behaviour. The lesson is a [COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md) recurrence: the same seed-once / never-overwrite / prune mechanic appeared at two copy sites and drifted at one, so the mechanic has earned a single extracted home rather than a third hand-reimplementation. A `critic` + `architect` consult settled the seam (mechanism-vs-convention split) and the module placement. Proposed status is the acceptance-gate gesture per [PRJ-005](../../../.pkit/decisions/project/PRJ-005-adopt-adrs.md).

## Decision

**The destructive half of the no-shared-files invariant is extracted into one stdlib-only primitive, `treecopy.refresh_owned_tree`, that every destructive copy path routes through. The primitive owns the *mechanism* — kit-owned files overwrite, kit-owned orphans prune, adopter-owned files seed-once and are never overwritten or removed; each caller injects the *convention* (which paths are adopter-owned) as a pure `is_owned` predicate. The init / first-write path is deliberately left on `copytree`'s raise-on-existing.**

1. **One primitive, the mechanism only.** `refresh_owned_tree(source, dest, *, is_owned, exclude=frozenset(), dry_run=False)` in a new `src/project_kit/treecopy.py` refreshes `dest` from `source`: a kit-owned source file is copied with `shutil.copy2` (preserving mode/executable bit + mtime), overwriting; a kit-owned dest file with no live source counterpart is pruned; an adopter-owned file (`is_owned(rel)` True) is copied only when the destination is absent (seed-once) and is otherwise never overwritten or pruned; an emptied kit-owned *orphan* directory is removed, while a directory the source still ships is kept even when empty (matching `copytree`). `dry_run` short-circuits to a no-op.

2. **Ownership is injected per caller, never centralised.** `is_owned` is a pure function of the *copy-root-relative* path. The primitive knows nothing of the `project/` convention; each caller expresses its own. `_copy_capability_tree` passes a predicate keyed on `rel.parts[0] == "project"` (top-level `project/`, positional — matching the `.pkit/<area>/project/` rule `_is_kit_propagated_path` enforces); kit-only callers pass the shipped `nothing_owned` predicate, which makes the refresh a plain overwrite-and-prune. The primitive owns the *mechanism*; the caller owns the *convention*.

3. **Both destructive copy paths route through it — one mechanic.** `_copy_capability_tree` (capabilities.py) and `_copy_tree`'s overwrite / sync path (install.py) both call `refresh_owned_tree`. A copy path can no longer silently reimplement-and-forget the seed-once rule (the #332 failure mode), because there is one place the mechanic lives.

4. **The init / `overwrite=False` path is unchanged — `copytree`'s raise is load-bearing.** `_copy_tree`'s init path keeps `shutil.copytree`'s raise-on-existing behaviour: re-running `init` over an existing tree is the structural error [COR-004](../../../.pkit/decisions/core/COR-004-cli-surface.md) specifies, so the raise is preserved untouched. Only the destructive (overwrite / refresh) path routes through the primitive.

5. **The `exclude` seam is generic.** `exclude` is a set of copy-root-relative POSIX path strings treated as *not shipped* — neither copied nor preserved as kit-owned (so a prior install's copy of a now-excluded artifact is pruned). It is the generic seam capability skip-state rides on; the primitive knows nothing of "skipped artifacts."

6. **Orchestration stays out of the primitive.** Area / adapter seeding orchestration — the `project/` stub, scratchpad stubs, overlay / settings seeds — remains in the callers. The primitive is the copy mechanic, not the install choreography.

## Rationale

**Why a mechanism / convention split rather than a centralised ownership concept.** Centralising *which paths are owned* would couple the primitive to the `.pkit/<area>/project/` convention and force every caller's notion of ownership through one definition. Injecting `is_owned` keeps the primitive convention-agnostic: it owns only seed-once / never-overwrite / prune, and each caller keeps the truth about its own root. This is the [COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md)-correct extraction — the *recurring mechanic* is extracted; the *per-caller policy* stays where it belongs.

**Why a single declared ownership concept is deliberately not built.** Today there are two predicate shapes: `nothing_owned` (kit-only trees) and top-level-`project/`-owned (capabilities). A single *declared* ownership model — ownership as data the primitive reads — would be premature generality (COR-007): two consumers expressing the same positional `project/` rule do not yet justify a declaration mechanism. Recorded here as a future seam: if a third copy-time caller appears with another root-relative `project/` expression, the declaration is the move to make then.

**Why a neutral stdlib-only module.** Placing the primitive in its own dependency-free module lets both `install` and `capabilities` import *down* into it, avoiding a `capabilities -> install` edge and keeping the dependency graph a clean DAG. A stdlib-only leaf has no upward coupling to either caller's concerns.

**Why the non-transactional failure contract is acceptable — and safer.** The refresh is **not transactional**: a crash or permission error mid-refresh can leave kit-owned content partially written, recoverable simply by re-running the refresh. Crucially, adopter-owned content is *never* deleted before a copy and is never the target of an overwrite, so a partial failure cannot destroy adopter data. This is strictly safer than the prior `rmtree`-first posture, which could leave the adopter with neither old nor new content — the exact shape of the #332 clobber.

**Why an ADR and not a new COR.** This composes only existing principles — COR-001's seed-once / never-overwrite contract, COR-007's recurrence-driven extraction, COR-004's init-raise — into project-kit's architectural realization. It introduces no new universal principle; one extracted mechanic with an injected convention is not a methodology axiom. It matches the ADR-002…011 hybrid.

### Alternatives considered

- **Leave the two copy paths separate, fix only the #332 site.** Rejected — the same mechanic at two sites already drifted once; nothing prevents the next reimplement-and-forget. The recurrence test (COR-007) says extract.
- **A centralised / declared ownership model the primitive reads.** Deferred (COR-007) — two consumers expressing one positional `project/` rule do not justify a declaration mechanism; revisit on a third caller with a different root-relative expression.
- **Route the init / `overwrite=False` path through the primitive too.** Rejected — `copytree`'s raise-on-existing is the load-bearing structural error COR-004 assigns to re-running `init`; folding it into the refresh would silently swallow that signal.
- **A transactional (stage-then-swap) refresh.** Rejected for v1 — the non-transactional refresh already guarantees adopter data is never destroyed (no delete-before-copy, no overwrite of adopter files), and re-running recovers a partial kit-side write. Staging adds complexity for a failure mode that is already non-destructive to the data that matters.
- **Put the primitive in `install.py` and have `capabilities` import it.** Rejected — creates a `capabilities -> install` edge. A neutral stdlib leaf both import *down* into keeps the graph a DAG.

## Implications

- **New module (tool-internal, not propagated).** `src/project_kit/treecopy.py` is pkit-internal code, not adopter-shipped content; it changes no adopter surface directly. Its behaviour change (capability refresh no longer clobbers `project/`) is the user-observable effect.
- **Behaviour fix, not a breaking surface change.** The capability-refresh clobber (#332) is corrected; the #333 cross-path preservation test pins it. No file rename / removal in a kit-owned tree, no schema_version bump, no CLI signature change → confirm via `pkit migrations check-diff` it trips no [COR-010](../../../.pkit/decisions/core/COR-010-migrations-mandatory.md) migration. Whether it bumps `.pkit/VERSION` per PRJ-002 follows from whether the corrected refresh semantics count as an adopter-observable surface change.
- **The failure contract is recorded, not just coded.** The non-transactional / never-destroys-adopter-data property is pinned here so it cannot silently regress to an `rmtree`-first posture again.
- **Future seam noted.** A declared ownership concept is the move if a third copy-time caller appears with another root-relative `project/` expression — pinned so the deferral is a recorded choice, not an oversight.
