---
id: ADR-043
title: The substrate seam supplies disposition; severity belongs to the consumer
status: accepted
date: 2026-07-30
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

The substrate-map read-path seam ([ADR-026](ADR-026-substrate-map-read-path-contract.md)) tells every consumer **what substrate an axis resolves to** — a `type:*` label, a title prefix, a derived state, or nothing. That *disposition* is shared and drift-proof: all consumers read it through the same seam functions. But **how severely a consumer reacts** when a required value is absent is the **consumer's own decision**, keyed to its role and phase — a bulk health check may degrade a finding to advisory, while a pre-transition close-gate must hold the authored severity on a *served* axis. The two must never be collapsed: "mirror the other consumer's posture" is a legitimate claim about *disposition*, never about *severity*. This record exists because a careful change to `validate-issue` (the close-gate) copied `pre-check`'s (the health check's) advisory severity while citing the degrade principle — producing a live false-accept on the close-gate.

## Context

[ADR-026] pins the read-path seam and its four-arm disposition (label / title-prefix / derive / unsupported), and [project-management:DEC-036-substrate-pluggable-adoption] pins that a *present* substrate-map **degrades, never refuses** — but scopes that degradation to `unsupported`/absent axes, explicitly keeping a *served* rule (its worked example: a declared title-prefix) "as authored." Two consumers read the same `type`-axis disposition: `pre-check` (a bulk, sampling **health report**) and `validate-issue` (the [project-management:DEC-007-checkbox-validation] **pre-transition close-gate** and the CI `--json` hard-exit gate).

While making `validate-issue` substrate-aware (#553), the natural instinct was "mirror `pre-check`, which already handles brownfield." `pre-check` degrades a title-prefix mismatch to advisory — correct for a health report that need not bracket-prefix every sampled issue. Copied into `validate-issue`, that same degrade turned an issue with an **undeterminable structural type** (a title matching none of the adopter's declared prefixes) into a *warning* that passes the close-gate — the exact false-accept class the same change had just closed on the label-remap arm. The disposition was shared correctly; the severity was not the seam's to share.

## Decision

**Disposition is a seam property, shared across consumers; severity is a consumer property, set by the consumer's role and phase. A consumer may never adopt another consumer's severity by appeal to shared disposition.** Three rules.

- **D1 — The seam supplies disposition, not severity.** The `axis_labels` seam functions (`axis_disposition`, `axis_expects_kit_labels`, `axis_title_prefix_remap`, `resolve_read`, `resolve_title_prefix_read`, `derive_state`, `axis_is_title_carried`, `axis_is_label_bound`) answer *what substrate an axis resolves to and how to read it*. They return no severity. Every consumer that gates on an axis reads disposition from these functions and no other source (no inline `substrate_map.axes` shape-dives), so the disposition cannot drift between consumers.

- **D2 — Severity is keyed to the consumer's role and phase, not to the other consumer.** A **health check** (`pre-check`) may degrade a per-axis finding to advisory. A **close-gate** (`validate-issue`, DEC-007 + CI `--json`) holds authored severity on a **served** axis: an axis-*presence* failure (no resolvable value in the axis's own substrate — no `type:*` label greenfield, no declared prefix under a title-prefix binding, no remapped label under a label binding) is a hard-reject, uniformly across all served arms. This is consistent with DEC-036 (degradation is scoped to `unsupported`/absent axes; a *served* rule stays as authored) and with the [project-management:DEC-011-title-formats] precedent that severity is phase-keyed, not substrate-keyed.

- **D3 — "Mirror the other consumer" is a disposition claim only.** When a consumer's author reasons "consumer X already handles this substrate, do as X does," that borrowing is valid for *which substrate to read and how* (D1) and invalid for *how hard to react* (D2). A degrade in a health check is never evidence that a gate should degrade. If a *uniform* extras-degrade across all served arms is ever wanted, it is a deliberate decision made once for the gate, not smuggled into one arm by copying a health check's posture.

## Rationale

**Why disposition and severity split at the consumer boundary.** Disposition answers a question about the *adopter's configuration* — objectively the same for everyone reading that repo's substrate-map, so it belongs in one shared seam (ADR-026's whole reason to exist). Severity answers a question about *what this consumer is for* — a report that samples vs a gate that must not pass a malformed issue. Forcing them to share would either make health checks refuse (noisy, wrong for sampling) or make gates degrade (false-accepts, wrong for a close-gate). Keeping severity local lets each consumer be correct for its own job over one shared, drift-proof disposition.

**Why this is worth an ADR though it is one incident.** The rule is non-obvious: a careful producer, *citing DEC-036's degrade principle*, still produced a false-accept, because DEC-036 and ADR-026 are silent on the disposition/severity split — they pin the seam and the degrade scope, not "severity is the consumer's, not shared." The rule composes on top of ADR-026 rather than restating it, the same way [ADR-042](ADR-042-verdict-selector-strict-gate.md) (permissive read primitive / strict gate wrapper) and [ADR-038](ADR-038-contribution-collector.md) (one collector core) pin cross-consumer boundary rules over an existing seam. Recording it turns a bug someone already hit into a rule the next consumer author reads.

### Alternatives considered

- **Leave it to DEC-036 / ADR-026.** Rejected — both are silent on the severity split; their degrade principle is precisely what was mis-cited to justify the false-accept.
- **Make severity a seam property too (the seam returns a severity).** Rejected — severity depends on the consumer's role (report vs gate) and phase, which the seam does not and should not know; it would force one severity on consumers with different jobs.
- **A general "gate agreement" ADR.** Rejected as the framing — disposition agreement is already ADR-026's; the load-bearing, non-obvious rule is specifically that severity does *not* agree by role.

## Implications

- **Consumers gating on a substrate axis** read disposition through the `axis_labels` seam functions only; a `type`-axis presence failure is a hard-reject in the close-gate across all served arms, and may be advisory in a health check.
- **`validate-issue`** (close-gate) hard-rejects an undeterminable type in every served arm (missing `type:*` greenfield; no declared prefix under a title-prefix binding; no remapped label under a label binding). **`pre-check`** (health check) may degrade the corresponding finding to advisory. Their *disposition* agrees (shared predicates + a gate-agreement test); their *severity* differs by role, by design.
- **A future consumer** that gates on a substrate axis inherits this rule: borrow disposition from the seam, decide severity from its own role/phase; do not copy another consumer's severity.
- **Latent extraction (COR-007, not now).** The per-arm dispatch ladder ("which binding am I in → what to demand") is still hand-written in each gating consumer; a *third* such consumer is the trigger to extract a single disposition→(read, presence-demand) resolver — the shape-reading predicates already prevent read-drift, but not ladder-drift. Do not extract on two.
- **No adopter migration.** This records an existing seam's consumer discipline; it changes no adopter-facing contract. Realized by #553 (the `validate-issue` severity correction that motivated it).
- **Stands on** ADR-026, DEC-036, DEC-007, DEC-011, COR-007, and the ADR-042 / ADR-038 sibling pattern — all accepted.
