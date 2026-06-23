---
id: DEC-034
title: Bind pm's closure cascade to the shared cascade slot
status: accepted
date: 2026-06-23
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

pm's upward-only closure cascade — a parent container becomes eligible to close once every child is closed — was decided in [DEC-006](DEC-006-state-machine-and-cascade.md). When the issue lifecycle was rebound onto the shared process substrate ([DEC-033](DEC-033-rebind-issue-lifecycle-onto-process-substrate.md)), its **D3** kept pm's `cascade` (along with `closure_triggers`, `pr_state_effect`, `source`, `display_name`) **capability-local** — the engine ignored them and pm's wrappers ran the cascade semantics. That was the right call *at the time*: cross-subject breadth was a deferred substrate slot ([COR-033](../../../decisions/core/COR-033-process-substrate.md) P5), so there was no shared mechanism to bind to, and pulling a containment tree into the engine would have broken the content-free boundary the rebind depended on.

That slot has now shipped: [COR-037](../../../decisions/core/COR-037-process-cascade.md) added the shared **cascade** declaration — a parent folds one named child process's many subjects' outcomes into a parent gate, with the **binding** supplying the subject set through a content-free membership predicate (the engine never holds a containment tree). COR-037's own Implications name this rebind as the follow-on: *"pm's capability-local closure cascade moves onto the shared cascade shape — a COR-010 migration, pre-budgeted by COR-033's acceptance gate."* This record is that pm-side binding decision (per COR-033's acceptance gate: *each binding is its own capability decision*).

## Decision

**In plain terms:** pm's "a parent issue can close once every child is done" rule stops being bespoke wrapper logic and becomes a declaration that reads the **shared** cascade slot — same behaviour, now expressed through the substrate everyone else uses.

- **Closure cascade binds to the shared slot.** pm's parent-eligible-to-close-when-all-children-done becomes a `cascade` declaration: the child is the issue process, the `members` predicate yields a parent's child issues (parent-scoped), the `membership` predicate is the parent-of check (one issue at a time), the reducer is `all` over the terminal *done* state, with **`on_empty: satisfied`**. The fold supplies only the **children half** of close-eligibility.
- **Close-eligibility is the conjunction of two engine mechanisms, not the fold alone.** A container closes only when *both* (a) its own acceptance checkboxes are ticked — the existing `gate-checkboxes-ticked` deterministic gate on the `in-progress → done` transition, already engine-side per DEC-033, a DEC-007 hard-reject — *and* (b) the cascade fold over children resolves open. The cascade supplies (b); the checkbox gate (a) is unchanged and stays a separate per-transition gate. The fold is not the whole close rule.
- **`on_empty: satisfied` is what makes the binding behaviour-preserving.** pm closes a *childless* container today (its `_find_open_children` treats an empty list as "all closed / none"), whereas the shared slot's default empty-set is fail-closed. pm therefore declares `on_empty: satisfied` (the policy [COR-037](../../../decisions/core/COR-037-process-cascade.md) added for exactly this divergence): a childless container's children-half is satisfied, so eligibility reduces to the checkbox gate — identical to today. By COR-037's precedence rule, a broken membership read still holds the fold (does not fail-open), so this does not weaken the gate on a *populated* container.
- **The `done` state, not a "completed-only" outcome, is the fold target.** pm's `done` terminal is reached by both PR-merge completion *and* won't-do; a won't-do child counts toward closure today (it is closed). The reducer folds over the terminal *state* `done`, preserving that — not a completed-only predicate (which would change behaviour by making won't-do children stop counting).
- **DEC-033 D3 is amended (superseded in part).** `cascade` no longer "stays capability-local"; the *closure* cascade binds to the shared slot. D3's other named fields (`closure_triggers`, `pr_state_effect`, `source`, `display_name`) and pm's **forward** cascade (the position reduction that drags a parent up to match its furthest child — a different machine, named-deferred by COR-037) **remain capability-local**. D3's content-free-boundary rationale is preserved, not overturned: the shared slot is itself content-free, so binding to it does not pollute the substrate. On acceptance, a reciprocal note lands on DEC-033 D3 pointing here.
- **Migration posture unchanged from DEC-033 D6.** `workflow.yaml` is kit-owned and delivered by `sync`, so the COR-010 migration only **detects an adopter override** still at the old `schema_version` and **warns** them to hand-update — it never rewrites the kit-shipped file or auto-edits project-owned content. Idempotent.

## Rationale

The shared cascade slot exists precisely so capabilities stop carrying duplicated cross-subject fold logic; pm is the first binding named in COR-033's acceptance gate and the one that grounds the slot against a real, shipped instance. Binding now is the COR-007 recurrence discipline closing its loop — the slot was shipped *because* pm (and trip-planning) demanded it, so leaving pm on bespoke wrapper logic would defeat the generalisation.

Keeping the closure cascade behaviour-preserving is the acceptance bar (mirroring DEC-033's parity bar): the rebind is structural, not behavioural. Only the **closure** fold moves — the forward cascade stays local because it is a genuinely different shape (a reduction over non-terminal positions firing on every child move, not a terminal-outcome fold feeding a gate), which COR-037 explicitly named-deferred; bundling it would over-ship past what the shared slot expresses.

### Alternatives considered

- **Amend DEC-033 D3 in place rather than a new DEC.** Rejected — COR-033's acceptance gate frames each binding as its own capability decision, and a fresh DEC carries the binding's own rationale (behaviour-parity bar, migration posture) without rewriting the historical rebind record; D3 is reconciled by a note, not mutated wholesale.
- **Move pm's forward cascade onto the shared slot too.** Rejected — it is a different machine (position reduction, not outcome fold); COR-037 named it deferred, and binding it now would build past a real need ([COR-033](../../../decisions/core/COR-033-process-substrate.md) P5 name-broad / ship-narrow).
- **Leave the closure cascade capability-local.** Rejected — that keeps the duplication the shared slot exists to remove and leaves the COR-033 grounding binding unfulfilled.

## Implications

- **`workflow.yaml`** gains the shared-shape `cascade` declaration for the closure fold (`on_empty: satisfied`); pm's closure-eligibility wrapper reads the engine's cascade resolution instead of computing the fold itself. pm ships the `members` + `membership` predicate commands (registered in `package.yaml`, the DEC-033 D4 pattern). Forward cascade and the other D3 fields stay wrapper-side.
- **Name disambiguation.** After this binding `workflow.yaml` carries both the shared-shape top-level `cascade` declaration (closure) and pm's capability-local `cascade:` block (forward / downward). These are structurally separate — moving the closure sub-block out does not disturb the local block — but the two same-named constructs must be disambiguated so the engine reads only the shared declaration; the impl pins how (the exact key/layout is impl detail).
- **Milestone roll-forward preserved.** For date/hybrid milestones, open children roll forward and only *closed* children count for eligibility ([DEC-016](DEC-016-time-bound-containers.md)). The `members`/`membership` predicates must walk the *same* hierarchy source pm uses today (the body parent-ref, as `_find_open_children` does), so an open rolled-forward child is an unresolved member that holds the fold — matching today's "open child blocks eligibility."
- **COR-010 migration** ships in the same change-set as the binding (warn-on-override, per D6); `schema_version` on `workflow.yaml` bumps; surface change → `.pkit/VERSION` bumps with the impl PR.
- **Behaviour parity is the acceptance bar:** existing pm cascade/closure tests stay green; a parent closes iff (checkboxes ticked AND all children done), pre/post identical — and the parity suite explicitly covers the **childless-container** case (closes via `on_empty: satisfied`, not blocked).
- **Relationship to records:** binds pm onto COR-037's shared slot; amends DEC-033 D3 (closure cascade → shared slot; forward cascade + other fields stay local); reuses D6's migration posture and D4's predicate pattern; fulfils COR-033's acceptance-gate grounding per [COR-007](../../../decisions/core/COR-007-pattern-extraction.md).
