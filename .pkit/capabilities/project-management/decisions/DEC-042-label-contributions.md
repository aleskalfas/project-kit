---
id: DEC-042
title: Label-contributions — an installed capability declares the labels it needs; pm provisions and advises
status: accepted
date: 2026-07-02
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

An installed capability can declare a **custom label it needs** (e.g. ux-ui-design's `needs-design` marker on UI Features), and pm **provisions it at bootstrap** and **advises at pre-check** if it is missing. A GitHub label is pm's substrate — pm owns the idempotent label seam and the pre-check readiness gate, and a raw `gh label create` from an agent is correctly denied by the permission layer — so today a capability's required label is a manual step an adopter must remember, with no idempotent setup and no signal when it is absent. This DEC gives capabilities the same manifest-walked contribution path [project-management:DEC-032-conditional-reviewer-requirements] gave reviewers, **one tier down (labels, not reviewers) and softer** (advise, not hard-gate). It is deliberately a **new** decision, not a DEC-032 amendment: the two share only the collection *shape*, and differ on substrate, provisioner, and severity.

## Context

[project-management:DEC-030-capability-contributed-adapter-overlays] established that a capability may contribute into a pm-owned surface, collected **orphan-safely** by walking `.pkit/manifest.yaml`'s `components:` (not the filesystem), so a half-removed capability directory can never silently inject anything. DEC-032 composed that pattern onto the review gate (a capability contributes a required reviewer). The `ux-ui-design` capability — incubated in an adopter's own repo per [COR-031](../../../decisions/core/COR-031-capability-origin.md), not present in project-kit — needs a `needs-design` **label** on UI Features for its pm→design binding. A label is pm's substrate: pm's `bootstrap` is the sanctioned, idempotent label constructor, and pm's `pre-check` is the readiness gate. There is no way today for another capability to say "I need this label" and have it created and its absence surfaced; the adopter creates it by hand, a fresh install silently lacks it, and the downstream readiness predicate just fail-closes with no hint that setup is missing.

Unlike DEC-032's reviewer case, ux-ui-design deliberately declares **no hard dependency** on pm ([ux-ui-design:DEC-007-cross-capability-read-seams] §D4 — the coupling is usage-conditional): a design-capability adopter who never files a UI Feature should not have pm gate on the capability's presence.

## Decision

A capability contributes label requirements; pm **creates them at bootstrap** and **warns (not refuses) at pre-check** when one is missing. Five rules.

### D1 — Capabilities declare label-contributions; pm collects by walking the manifest

A capability declares its labels in its own subtree — a `label-contributions.yaml` with a companion JSON Schema — carrying a top-level `schema_version` (mirroring the review-contributions declaration), each entry pairing a stable `id` with a `default_name`, `color`, and `description`. pm builds the map with a collector that **iterates capabilities registered in `.pkit/manifest.yaml`'s `components:`** — not arbitrary directories — exactly as DEC-030's `collect_capability_overlays` and DEC-032's reviewer collector do, so an orphaned capability directory can never silently inject a label or a warning. **pm never names a contributor** — it reads whatever declarations the installed capabilities ship.

### D2 — Soft collection; version-compat by declared `schema_version`, not a hard dependency edge

pm collects a capability's label-contribution purely on the declaration being present in a manifest-registered component — it does **not** require the contributor to declare `requires_capabilities: project-management`. (This is not new: pm's existing contribution collector already reads declarations without consulting that field.) The declaration's `schema_version` is validated at collection. This is honestly a **narrower, read-time-only** compatibility check — it catches pm's declaration schema evolving out from under a pinned contributor at the moment pm reads it — **not** the lifecycle-boundary, bidirectional protection a [COR-030](../../../decisions/core/COR-030-capability-dependencies.md) versioned dependency edge gives. That narrower check is accepted deliberately, because the failure mode is benign and self-healing: a mis-read label-contribution degrades to "the label is missing → run bootstrap", never to a silently compromised gate. A hard pm edge is rejected because it would force every design-capability adopter to couple to pm even when they never file the work the label marks (§D4 of the contributor's own coupling decision).

### D3 — Bootstrap is the provisioner, through a per-label create path outside the axis seam

pm's `bootstrap` creates any missing contributed label through a **per-label create path** carrying that contribution's own `color` and `description`, parallel to the existing axis-grouped label creation. It reuses bootstrap's idempotency plan (the existing missing-vs-present label diff), is additive and re-runnable, and never issues a raw agent `gh label create` (which the permission layer denies). A contributed label is **not** a classification-axis label: it does **not** route through the axis-label sole-constructor ([ADR-026](../../../../docs/architecture/decisions/ADR-026-substrate-map-read-path-contract.md)), whose guard keys on the four axis *shapes* (`type:`/`priority:`/`workstream:`/`state:`) and therefore cannot fire on a bare label — no carve-out is needed, and none is added (adding one would falsely imply a contributed label is in the axis family).

### D4 — pre-check warns on a missing contributed label; it does not refuse

Because bootstrap is the provisioner, a missing contributed label means "run bootstrap" — remediation, not a design error. pm's `pre-check` reports a missing contributed label as a **warning** with that remediation, conditional on the contributing capability being manifest-registered (a pm-only adopter sees nothing). This is a **deliberate severity divergence from DEC-032**, which hard-gates a missing reviewer: a missing reviewer silently weakens a merge gate (fail-open on a control), whereas a missing label has a provisioner *and* its downstream consumer fail-closes on its own predicate — so the label case's stakes are lower and already covered downstream. The set is recomputed from the current manifest on each run.

### D5 — Remap deferred, but the resolution seam ships inert in v1

An adopter renaming a contributed label is a **v2 follow-up**: the existing substrate-map is keyed on the four methodology axes and structurally cannot hold a bare label, so v1 does not claim it does. What v1 **does** ship is the resolution seam it defers the *storage* behind: a `resolve_contributed_label(id)` accessor that returns the `default_name` in v1, which the consuming capability **must** call rather than hard-coding the label text. Introducing the seam before any consumer can bypass it means a future adopter-override (keyed by the contribution `id`) can relocate the name without touching the contributor — the same discipline ADR-026 applies to axis labels.

### Lifecycle

- **Contributing capability uninstalled** → its declaration leaves the manifest walk → pre-check stops warning on its labels. The label itself is **not** deleted (additive, the disposition DEC-030 gives an uninstalled contribution).
- **Malformed declaration** → **skip that contribution and warn**, not fail-closed pm-wide. This diverges from DEC-032's fail-closed collection deliberately: a dropped label-contribution is lower-stakes (the consumer fail-closes downstream), so one capability's malformed file must not block pm's entire pre-check.
- The resolved set is **recomputed each run** from the current manifest — never frozen.

## Rationale

**Why manifest-walked, contributor-anonymous collection.** Identical reasoning to DEC-030 and DEC-032: the manifest is the source of truth for installed-ness; walking it (not the filesystem) stops a half-removed capability from silently imposing a label or a warning, and keeps pm universal — pm offers the provisioning mechanism, capabilities supply the labels, pm stays ignorant of who contributes (COR-026, [COR-014](../../../decisions/core/COR-014-universal-applicability.md)).

**Why soft, and why `schema_version` rather than a hard edge.** A hard `requires_capabilities: project-management` edge buys COR-030's lifecycle-boundary contract-drift protection, but at the cost of forcing usage-conditional adopters into a coupling they explicitly rejected (§D4). The label case does not need the stronger guarantee because its failure is self-healing: the worst a drifted declaration produces is a missing label, which bootstrap re-provisions. The `schema_version` read-time check is the proportionate protection; the DEC states the narrower claim honestly rather than overselling it as COR-030-equivalent.

**Why warn, not gate (the DEC-032 divergence).** DEC-032 hard-gates because a dropped reviewer silently weakens a merge control — fail-closed is the only safe posture. A contributed label has two properties the reviewer case lacks: a provisioner (bootstrap creates it) and a downstream fail-close (the consuming capability's own predicate refuses when the label is absent). So a hard pm-side gate would only ever fire on "you didn't run the adjacent bootstrap command," and would double-count a failure the consumer already catches. Warning with a "run bootstrap" remediation matches the actual stakes.

**Why a new DEC, not a DEC-032 amendment.** The two mechanisms share the manifest-walk collection *shape* but differ on substrate (a `gh` label vs a deployed agent file), on satisfier (labels have a bootstrap provisioner; reviewers do not), and on severity (warn vs hard-gate). Folding would bloat DEC-032's tightly-argued record with a second mechanism. The genuinely shared thing — the orphan-safe manifest-walked contribution collector — is now at its **third** instance (DEC-030, DEC-032, this), which is the [COR-007](../../../decisions/core/COR-007-pattern-extraction.md) recurrence to *extract*, not to fold; that extraction is pinned in sibling [ADR-038](../../../../docs/architecture/decisions/ADR-038-contribution-collector.md), authored alongside this work, and this DEC's implementation instantiates the extracted collector.

**Why the contribution surface is attestation, not security.** As in DEC-032: anyone who can land a capability install can shape what pm provisions. The manifest-walk and schema-version checks prevent honest mistakes (orphan dirs, drifted schemas), not a motivated actor with write access — the enforcement floor is GitHub branch protection, unchanged. Because this DEC's gate is a *warning*, the widened attestation surface costs even less than DEC-032's.

### Alternatives considered

- **Hard `requires_capabilities: project-management` edge (COR-030), as DEC-032 documents for reviewers.** Rejected: it forces usage-conditional adopters into a coupling they declined; the self-healing failure mode does not warrant it.
- **Hard-gate at pre-check (mirror DEC-032 severity).** Rejected: redundant with bootstrap-provisioning and the downstream consumer's own fail-close; it would fire only on "run bootstrap."
- **Fold into DEC-032 as a second contribution kind.** Rejected: different substrate, provisioner, and severity; the shared collector is extracted instead (COR-007).
- **Reuse the substrate-map for remap.** Rejected: it is axis-keyed and cannot hold a bare label. v1 defers the override storage and ships only the inert resolution accessor.
- **Ship v1 with the label name hard-coded by the consumer.** Rejected: it bakes in a name the pm→design binding could not later relocate; the inert `resolve_contributed_label(id)` accessor prevents the bypass becoming load-bearing.

## Implications

- **The pm capability gains a label-contribution declaration schema** (`schema_version` + `{ id, default_name, color, description }` entries) and a **collector** that walks `.pkit/manifest.yaml`'s `components:`, validates each declaration's `schema_version`, and skips-and-warns on a malformed one.
- **`bootstrap`** gains a per-label create path (per-contribution `color`/`description`), reusing its existing idempotency diff; contributed labels do not pass through the axis sole-constructor.
- **`pre-check`** warns on a missing contributed label (conditional on the contributor being manifest-registered), with a "run bootstrap" remediation.
- **A `resolve_contributed_label(id)` accessor** ships inert (returns `default_name`); the consumer calls it rather than hard-coding the name.
- **Extraction (COR-007).** The shared manifest-walked, orphan-safe contribution-collector core is extracted into pm's `_lib/`, with review-contributions reinstantiated on it and label-contributions built on it; DEC-030's walker is noted as a later refactor target. The extraction and its severity/malformed-disposition rule are pinned in sibling [ADR-038](../../../../docs/architecture/decisions/ADR-038-contribution-collector.md) (authored with this work). Refactoring review-contributions' realization is behaviour-preserving.
- **Surface change, migration-free.** New declaration schema + collector + create path + warning → a **pm-capability** surface bump per [PRJ-002]; no backbone-level refusal changes. No migration: additive; a pm-only or non-contributing install behaves identically ([COR-010](../../../decisions/core/COR-010-resource-lifecycle.md)).
- **First consumer (illustrative, deferred).** `ux-ui-design` ships a `label-contributions.yaml` declaring `needs-design` and calls `resolve_contributed_label` in its readiness predicate — authored as its own half once this contract ships (the acceptance gate; authoring it now would be against a non-existent schema).
- **Stands on** DEC-030, DEC-032, COR-007, COR-014, COR-026, COR-030, ADR-026 — all accepted — and sibling [ADR-038](../../../../docs/architecture/decisions/ADR-038-contribution-collector.md) extracting the collector, authored alongside.
