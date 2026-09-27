---
id: ADR-003
title: The permission decision core lives as propagated neutral code shared by hook and CLI
status: accepted
date: 2026-05-29
author: Ales Kalfas <kalfas.ales@gmail.com>
---

## Context

[COR-028](../../../.pkit/decisions/core/COR-028-permission-model-realization.md) establishes permissions as a harness-neutral model the methodology owns, realized by each harness's adapter. [ADR-002](ADR-002-permission-realizer-ownership.md) records the first realizer's *ownership* boundary — who owns which region of `.claude/settings.json`. This ADR records the sibling boundary ADR-002 does not touch: the *code-home* boundary — where the shared decision logic physically lives in the source tree. Ownership and code-home are distinct questions; ADR-002 settles the former, ADR-003 the latter. It was raised and resolved in the architect review of the `2026-05-29-permission-system-implementation.md` implementation plan, named there as ADR-worthy.

The decisive fact is a split in how project-kit's own code propagates. `src/project_kit/` is the Python runtime — the `pkit` CLI. It is installed globally (a single install operates *on* a target `.pkit/` tree) and is **not** propagated into adopters. By contrast, scripts under `.pkit/adapters/` **are** propagated: `pkit sync` copies them into the adopter's tree, where they run in-tree. The claude-code PreToolUse hook is one such propagated script — it runs in the adopter's tree at decision time, in a process where the global `pkit` runtime is not importable.

This collides with ADR-002's **same-code invariant**: the hook and `pkit permissions diff` must reach *identical* decisions from the *same* `decide()` and the *same* realized-state projection — the property shared conformance fixtures exist to prove. The hook runs in-tree without `pkit`; `diff` runs in the global runtime. If the decision core lived in `src/project_kit/`, the hook could only reach it by shelling out to the global `pkit` or by duplicating the logic — and both break the invariant. So the same-code invariant *forbids* the decision core living in `src/`. The core must be code that both the global runtime and an in-tree propagated script can import.

The proposed status is the acceptance-gate gesture per [PRJ-005](../../../.pkit/decisions/project/PRJ-005-adopt-adrs.md). As project-kit's own architecture-decision record, concrete paths and the src-vs-propagated runtime split are in scope here — unlike the harness-neutral COR.

## Decision

The permission **decision core** — `decide()`, the recognizer matcher engine, and the shared realized-state projection — lives as **propagated neutral code in a new `.pkit/permissions/` directory**. This is a *propagated code home*, not a [COR-011](../../../.pkit/decisions/core/COR-011-areas-first-class.md) area: it has no content layout, schema, or area README of its own — it holds neutral Python that `pkit sync` copies into adopters, the same way `.pkit/adapters/` holds propagated adapter code. This is consistent with COR-028's own "not a new area" framing.

**Dependency direction.** Imports point inward, toward the neutral core, and never outward:

- The `pkit permissions` CLI (`src/project_kit/permissions.py`, a thin orchestrator on `cli.py`) imports the core via the resolved `.pkit/` path.
- The PreToolUse hook (`.pkit/adapters/claude-code/`) imports the core via a relative in-tree path.
- **Neither the neutral core nor `src/` ever imports from the adapter.** The arrows are: CLI → core, hook → core. There is no core → adapter or src → adapter edge.

This is what makes the same-code invariant mechanical rather than aspirational: there is exactly one `decide()`, in one place, and both callers import that one definition.

**Recognizers compose as data, not as code.** The matcher engine in the neutral core reads recognizers from the privilege-catalog YAML — they are catalog data the engine interprets, never adapter code the core imports. This is how a harness-neutral core matches harness-shaped commands without acquiring a dependency on any adapter: the harness-shaped knowledge enters as data the adapter (or the baseline catalog) supplies, flowing along the import direction rather than against it.

**Tier assignment of the catalog.** The baseline catalog content — privilege identities plus shell recognizers — is **neutral**: shell command shapes are portable across harnesses, so they ship with the neutral core's data, not with any one adapter. Only the **per-adapter enforcement-capability declaration** (which model dimensions a given harness can natively enforce) is adapter-tier, living under `.pkit/adapters/claude-code/`.

## Rationale

**Why not `src/project_kit/`.** The hook runs in the adopter tree where the global runtime is not importable. Reaching `src/` from the hook would mean either shelling out to global `pkit` — which is fragile (PATH assumptions, version skew, subprocess latency on a hot path) and breaks the hook's fail-open contract, since a missing or broken global `pkit` would turn every decision into an error — or duplicating the logic into the hook, which violates the same-code invariant by construction. Propagated neutral code both callers import is the only home that keeps one `decide()`.

**Why not under `adapters/claude-code/`.** The decision core is harness-neutral; a second harness adapter will realize the same model and must reuse the same core and the same neutral recognizers. Housing the core inside the claude-code adapter would force the second adapter to either depend on the first adapter or duplicate the core — the same invariant violation, one layer over. The core sits above all adapters precisely so every adapter imports it.

**Why a propagated code home, not a COR-011 area.** An area earns its keep when it has a content layout, a schema, and authoring discipline of its own. `.pkit/permissions/` has none of these — it is just neutral Python that needs to be propagated so an in-tree script can import it. Minting an area for it would be ceremony the content does not justify, and would contradict COR-028's explicit "not a new area." A propagated code home (the category `adapters/` already occupies) is the right-sized carrier.

**Why data-composition over code-import for recognizers.** Composing recognizers as catalog data keeps the dependency direction clean — the core never reaches outward for harness knowledge — and lets a second adapter reuse the neutral shell recognizers unchanged while contributing only its own harness-specific declarations. Code-import would invert the arrow, coupling the neutral core to whichever adapter defined a recognizer.

**Alternative rejected — a general `.pkit/lib/` for all neutral propagated code.** Tempting as the "obviously general" home, but it is speculative generality per [COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md): there is exactly one neutral propagated consumer today (the permission core). A purpose-named `.pkit/permissions/` reads more clearly and commits to nothing premature. Revisit and extract a shared `.pkit/lib/` only if a second, unrelated neutral propagated library appears — the recurrence test, not the first instance, earns the abstraction.

## Implications

- **`.pkit/permissions/` is propagated and therefore core-owned under the no-shared-files invariant.** It is synced into adopters; adopters do not edit it (edits are overwritten on the next `pkit sync`), exactly as for any other propagated kit-owned tree. Adopters extend the *model* (their grants and config), never the core.
- **The CLI module stays a thin orchestrator.** `src/project_kit/permissions.py` parses arguments, does IO, and formats output; it delegates every decision to the imported core. The decision logic does not live in two places, and the CLI carries no copy of `decide()`.
- **The precedent for adapter-tier propagated Python is `_resolve_agent.py`** (`.pkit/adapters/claude-code/_resolve_agent.py`) — propagated Python that runs in the adopter tree. ADR-003 extends that precedent from the adapter tier to a new *neutral* tier: code propagated for in-tree execution that belongs to no single adapter.
- **This establishes "neutral propagated shared code" as a category project-kit did not previously have.** Adapter code was propagated (adapter-tier); the runtime was global (`src/`); schemas and decisions were propagated data. Propagated *neutral executable code* shared across adapters is new. A future second instance is the trigger to consider generalising the home (the `.pkit/lib/` revisit above); until then the category has exactly one member.
- **Creating `.pkit/permissions/` is a pure addition, not a rename or removal**, so it carries no COR-010 migration on its own. The adopter-breaking surface change in this arc is the hook deploy/registration (folded into the implementation plan's Task 3), where the migration lands.

  > **Update (#247) — there is no adopter-breaking surface change in this arc; no migration lands.** The implemented design (issue #247, "Option B") makes live enforcement *opt-in*: the hook script is a propagated adapter file owned by `pkit sync`, and the PreToolUse hook is registered only when the adopter runs `pkit permissions enable` (stripped by `pkit permissions disable`), mirroring the DEC-030 default-agent toggle precedent. The hook deploy is therefore a **pure addition** and registration is the adopter's explicit action, so the second sentence above is **superseded** — there is no adopter-breaking surface change in this arc and no migration lands. `pkit migrations check-diff` confirms COVERED with no migration script. The first sentence stands: `.pkit/permissions/` remains a pure addition carrying no migration of its own.
