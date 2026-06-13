---
id: PRJ-005
title: Adopt ADRs for project-kit's architectural decisions
status: accepted
date: 2026-05-27
author: Ales Kalfas <kalfas.ales@gmail.com>
---

## Context

[COR-025](../core/COR-025-adr-decision-space.md) established the ADR namespace as a third decision-record context, adopter-scoped, for project-architectural decisions. Adoption is opt-in per adopter. COR-025's Implications section explicitly commissions a separate PRJ record on the project-kit side: *"whether project-kit's own architecture warrants ADRs is a separate question for a PRJ record to settle."* This record is that settlement.

Project-kit-the-project — the methodology framework's source tree — has architectural decisions that don't fit cleanly as CORs (universal methodology principles, project-neutral by discipline). PRJs already cover project-side decisions of any kind per [COR-025](../core/COR-025-adr-decision-space.md), including architecture-flavoured choices that touch tooling. The question for project-kit is whether to *also* use the ADR carve-out for architecturally-significant decisions whose rationale needs to be findable by someone orienting in the codebase, not only by people already working on it.

The overlay at `.pkit/agents/project/overlay.yaml` declares `adr-records: [docs/architecture/decisions/]` and `architecture-docs:` already pointing at CONTRIBUTING.md / `.pkit/decisions/core/`. The infrastructure is in place; what remains is the decision to use it.

## Decision

Project-kit adopts the ADR namespace defined in [COR-025](../core/COR-025-adr-decision-space.md). ADRs land at the overlay-resolved path `docs/architecture/decisions/`.

The classifier between PRJ and ADR, for project-kit:

| Namespace | Scope (per COR-025) | When to choose, for project-kit |
|---|---|---|
| **PRJ** | Project-specific decisions of any kind (workflow, tooling, distribution, conventions, architecture-flavoured choices that touch tooling). | Default for project-side decisions. Workflow conventions, branch naming, tooling choices contained within the kit's existing surface, distribution policy. |
| **ADR** | Architectural decisions about the adopter's project — system boundaries, technology choices, integration patterns, key abstractions, deployment topology. | When the rationale needs to be findable by a future maintainer or new contributor orienting in the codebase, not only by people already working on it. Decisions whose consequences propagate to system shape, integration patterns, or contributor mental models. |

The boundary is fuzzy at the edges. PRJ-003 (Python as implementation language) is architecture-flavoured but stays as PRJ — grandfathered, and per COR-025's no-retroactive-backfill stance (line 132). A similar decision authored today would also reasonably land as PRJ if its consequences are bounded to a single tooling axis. Authors lean PRJ for kit-internal mechanism choices, ADR for decisions whose rationale outlives the people who made them.

No retroactive backfill of existing PRJ records. Records authored as PRJs stay as PRJs.

## Rationale

ADRs as a methodology affordance ship in COR-025; self-hosting validates the affordance and makes the COR/PRJ/ADR boundary concrete in the project that authored COR-025 itself. Rough edges in the affordance surface during use rather than during a future adopter rollout — a feedback loop that wouldn't exist if project-kit deferred.

Project-kit has candidates already surfaced in `CLAUDE.md` and area READMEs (the dispatcher's CWD-resolution model, the sync pipeline's mechanism, the merge primitive's semantics, the schema-driven validation architecture) — architectural facts captured today only as scattered prose and code comments. These will be authored forward as the corresponding ADRs land; this record doesn't promise a specific backfill schedule.

### Alternatives considered

- **Defer ADR adoption until a specific architectural decision demands it.** Rejected — the architect agent gains a real corpus to operate on now, the COR/PRJ/ADR boundary becomes concrete, and the affordance gets exercised in its source repo. Deferring means a future adopter is the first user of an untested affordance.

- **Retroactively reclassify architecturally-flavoured PRJs (notably PRJ-003) as ADRs.** Rejected — COR-025 line 132 establishes the no-retroactive-backfill stance; this project follows it. Reclassification across namespaces is not blocked methodologically (the `supersedes:` field accepts any record ID), but spending the convention now on one inconsistency isn't worth the cost.

- **Use a `kind:` field on existing PRJ records to mark architecturally-flavoured ones.** Rejected for the same reason COR-025 rejected the equivalent for adopters: a soft field doesn't solve the audience-separation problem; the architect agent and human readers still have to filter the PRJ corpus.

- **Ship PRJ-005 and ADR-001 (the first concrete ADR) in the same PR.** Worth naming. Authoring the first ADR alongside the namespace declaration pressure-tests the discriminator before PRJ-005 is accepted — the classification rules might need revision after the first lived application. Chosen path: separate but adjacent. PRJ-005 lands first; ADR-001 follows as the immediate next deliverable. If ADR-001 surfaces a discriminator problem, PRJ-005 gets refined before acceptance.

- **Amend COR-025 to cap PRJ at workflow/convention only, routing all architecture-flavoured choices to ADR.** Rejected — would widen the methodology surface to address a project-kit-specific question; the discriminator at the adopter level (the classifier table above) carries the same load without amending the upstream COR.

## Implications

- A `docs/architecture/decisions/` tree appears in project-kit's source repo, project-owned and outside `.pkit/` (never propagated to adopters who install the methodology — per COR-025's propagation-isolation property).
- The architect agent — already operating read-only on `<architecture-docs>` (CONTRIBUTING.md, `.pkit/decisions/core/`) per COR-024 — gains write authority over the new ADR corpus as it grows.
- Future architectural decisions about project-kit-as-product land as ADRs; future workflow / convention / kit-internal-tooling decisions land as PRJs. The classifier above carries the boundary; edge cases default to author judgement leaning PRJ for kit-internal mechanism choices.
- COR-025's affordance is now exercised in the source repo. The first ADR (dispatcher CWD-resolution model) follows immediately as a separate record.
- The deferring comments in `.pkit/agents/project/overlay.yaml` (on `architecture-docs:` and `adr-records:`) are removed in the same PR that accepts PRJ-005, so the overlay state matches the record state.
- Existing PRJ records stay as authored. No cross-namespace supersession chain.
