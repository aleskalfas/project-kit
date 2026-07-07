---
id: COR-041
title: Externally-sourced content is pulled whole, pinned, and reconciled against its source
status: accepted
date: 2026-07-06
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

*An organisation can keep private methodology — a whole proprietary capability, or a company house-style shipped as one — in a single repository and pull it into its other repositories, each pinned to a version and used as-is, without forking the methodology. This record defines how such **externally-sourced** content is distributed and reconciled; the concrete fetch and authentication mechanism is a separate realising ADR.*

## Context

COR-031 established the capability-origin axis and **reserved** the `externally-sourced` origin, deferring its mechanism until a grounded consumer arrived (the extract-on-recurrence discipline, COR-007). That consumer now exists: an organisation that wants to **privately share adopter-owned content across its own repositories** — either a whole proprietary capability, or a company house-style shipped as one — maintained in one place and consumed everywhere internal, without publishing it to the public methodology core and without forking the methodology.

This record realises the **distribution and reconciliation semantics** of the `externally-sourced` origin. The project-specific fetch and authentication write-path is delegated to a realising ADR (COR-025); this principle carries only what is universal to any adopter's lifecycle.

## Decision

- **Pulled whole, pinned.** Content from an `externally-sourced` origin is pulled **whole** from an external source **pinned to a ref**. The pin is the single source of truth for what the consumer holds; an **upgrade is a repointing of the pin**, nothing more.
- **Reconcile = match-the-pin.** On sync, the consumer's copy is brought to exactly the pinned ref's content. This is a **third reconciliation case** beside COR-010's reconcile-against-kit-canonical and skip-because-adopter-owned. It is **not a merge**: the no-shared-files invariant (COR-001) forbids merge/conflict machinery, and consumed-whole content lands in its **own subtree with a single owner** (the pinned source), so no conflict can arise.
- **Excluded from kit-source reconciliation** (as incubated content is), but **reconciled against its own external source**.
- **Participates in every other lifecycle concern** — dependency gating, compatibility resolution, deploy — identically to any other origin. Compatibility resolution (COR-010's `requires_backbone` gate) evaluates the **fetched** content's declared range against the **consumer's** backbone, before the content is activated.
- **The author owns the compatibility claim.** `requires_backbone` on externally-sourced content is **declared against the backbone lineage the author tests on**; the consumer's gate validates it at fetch time. The author repo's own backbone version is irrelevant to consumers — only the declared range is.
- **Cross-source name collisions surface.** Two external sources, or an external source and a kit-shipped or incubated capability, claiming the same name **surfaces** rather than silently clobbering — extending COR-031's collision rule to this origin.
- **Origin is a per-repo relationship.** The **same content is `incubated-in-repo` in its authoring repo and `externally-sourced` in a consumer**. There is **no fork**: the author layers on the framework through the capability mechanism, and consumers pull the result whole.
- **Channel, authentication, and fetch mechanics are not part of this principle.** They are fixed by the realising ADR (COR-025) and inherit the adopter's **existing distribution channel** — the same channel the whole methodology is distributed through, one altitude down (a source/capability rather than the whole core).

## Rationale

- COR-031 pre-authorised the origin and deferred only its mechanism, gated by COR-007 on a grounded consumer. That consumer has arrived, so building it now **honours** extract-on-recurrence rather than violating it.
- **Consumed-whole + match-the-pin is the only reconcile shape consistent with COR-001.** The alternative — merging shared content into a region the consumer also owns — is exactly the merge/conflict machinery the methodology structurally refuses; where shared defaults must yield to local values, the sanctioned tool is suspension/precedence (whole-value replacement by layer), not a merge.
- Shipping a company house-style **as a capability consumed whole** reuses the existing capability primitive and its version axis, inventing **no new artifact type** (the role-discrimination discipline COR-006, the anti-speculation discipline COR-007).
- The design inherits **registry-free, pin-by-ref minimalism** — the same bias the whole-methodology distribution channel takes, one altitude down. Pinning by ref with no registry layer is the lightest mechanism that still gives reproducible, private sharing.

## Implications

- **COR-010** gains a third reconciliation case (match-the-pin) and records that externally-sourced content is excluded from kit-source reconciliation while reconciled against its source; compatibility resolution now evaluates a **fetched** manifest. (A forward-pointer is added there on acceptance.)
- **COR-031**'s reserved `externally-sourced` origin is **realised here** (a forward-pointer is added there on acceptance).
- The **fetch/auth/reconcile write-path** — how the pinned ref is fetched and authenticated, where it lands, how the pin is recorded in install state, the fetch → read-manifest → compatibility-gate → activate-or-refuse ordering, and the unreachable-source degradation posture (warn loudly, never brick mid-command) — is fixed by the **realising ADR** (COR-025), authored alongside this record.
- Because the author maintains the compatibility claim, **tooling that keeps `requires_backbone` current on a capability release** is a natural implementation follow-up, so honouring the claim costs one command rather than manual edits.
- **Deferred, in sequence** — none load-bearing for the consumed-whole case, but the first is the next record the grounded consumer will need:
  1. Composing a company house-style's config with a consumer's **same-key** local values — a capability-level decision using suspension/precedence (COR-001), never merge.
  2. **Unattended CI authentication** to a private source — deferred to a project-level distribution decision (as the whole-methodology channel deferred cross-repo CI authentication).
  3. The **seam-gap vocabulary** (adding an extension seam upstream rather than overriding locally) — orthogonal to distribution, its own record.
