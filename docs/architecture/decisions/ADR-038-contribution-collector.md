---
id: ADR-038
title: One orphan-safe contribution-collector core; each contribution kind instantiates it
status: accepted
date: 2026-07-02
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

The project-management (pm) capability now has **three** places where an installed capability contributes into a pm-owned surface — settings-overlay/skill grants ([project-management:DEC-030-capability-contributed-adapter-overlays]), required reviewers ([project-management:DEC-032-conditional-reviewer-requirements]), and required labels ([project-management:DEC-042-label-contributions]). Each walks `.pkit/manifest.yaml`'s `components:`, reads a per-capability declaration, and handles malformed/parse errors, so each re-implements the same **orphan-safety invariant**: a half-removed capability directory must never inject a contribution. This ADR extracts that shared machinery into **one collector core** in pm's `_lib/`, on which each contribution kind is a thin instantiation, so the safety invariant lives in one auditable place instead of drifting across three copies. It also fixes the **rule each instantiation follows to choose its severity and malformed-disposition**, so a fourth contribution kind does not re-derive it.

## Context

The manifest-walked contribution pattern appeared once (DEC-030), recurred (DEC-032), and is now at a third instance (DEC-042, label-contributions) — past [COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md)'s extraction threshold, and, critically, with a *stable, visible* shape: the first instance could not be generalised without guessing; the third can. Reading the existing `review_contributions.py` collector, the shared core is already factored into reusable pieces — list the manifest-registered capabilities, read each one's declaration, classify parse/malformed errors, and expose a fail-disposition predicate — while what *varies* per kind is equally clear: the declaration filename, the per-entry schema, the resolution step (is the referenced agent deployed? does the label exist? none), and the severity/malformed posture.

The cost of not extracting is not mere duplication: the orphan-safety invariant is a **safety property**, and three hand-maintained copies is three places for it to drift — the same "N places to audit instead of one" that [ADR-026](ADR-026-substrate-map-read-path-contract.md) rejected for the axis-label seam. Extracting now, while a third instance is being written, is cheapest: the third consumer is authored as an instantiation rather than a copy.

## Decision

**One contribution-collector core; each contribution kind instantiates it; the core owns the orphan-safe walk, the third kind is not hand-rolled.**

1. **The core lives in the pm capability's `_lib/`**, not in the backbone or a core (COR-level) pattern. All three consumers are pm surfaces; there is no non-pm consumer, so promoting to backbone would be speculative generality. The manifest walked is backbone-owned *data*, but reading it *for a pm contribution* is a pm idiom; the seam stays with its consumers. A cross-capability promotion waits for a genuinely non-pm contribution consumer (the defer-until-second-instance discipline, one altitude up).

2. **The core owns the shared shape**: iterate `.pkit/manifest.yaml`'s `components:` (never the filesystem), read each registered capability's declaration file if present, validate its `schema_version`, and classify errors into a small taxonomy (parse / malformed / resolution). The orphan-safety invariant — collection keys on manifest registration, not directory presence — is realised **once**, here.

3. **Each contribution kind is a thin instantiation** parameterised over: the declaration filename, the per-entry parser/schema, an optional resolution function (reviewer → deployed-agent-file check; label → none at collect time), and a **severity + malformed-disposition policy** (see rule 4). `review_contributions` and `label_contributions` are the first two instantiations; DEC-030's overlay/skill walker is a **later** refactor target — it composes over the same core plus overlay-specific reads, so it is not swallowed whole in v1.

4. **The severity/malformed-disposition rule is fixed, not re-derived per author.** An instantiation gates **fail-closed (blocking)** when a dropped contribution would silently weaken a control the contribution exists to enforce (a required reviewer — DEC-032). It gates **skip-and-warn** when a dropped contribution is self-healing or independently fail-closed downstream (a required label — DEC-042: bootstrap re-provisions it and the consumer's own predicate refuses without it). The discriminator a future kind applies: *does dropping this contribution fail open on a control, or degrade to a benign, downstream-caught state?*

## Rationale

**Why extract now, not flag-and-defer.** The extraction is at the *late* edge of COR-007's window (third instance) and its shape is proven, not speculative. Deferring ships a third divergent copy of a safety invariant that the eventual extraction must then reconcile — strictly more work and more risk than writing the third consumer as an instantiation now, at roughly the cost of the copy.

**Why in pm `_lib/`, not backbone.** COR-007 warns equally against premature *breadth*. Every consumer today is a pm surface; a backbone/COR-level "capability contribution" abstraction with no non-pm consumer would be speculative. ADR-026 made the same call when it declined to name a cross-capability bootstrap shape and left it promotable on a second, non-pm instance. Keep the core where its consumers are; promote only when a non-pm consumer appears.

**Why fix the severity rule in one place.** Divergent per-kind severity (DEC-032 hard-gates, DEC-042 warns) is *correct* and stakes-driven — but if the rule for *choosing* it lives only in each DEC's prose, a fourth author re-derives it and the family drifts. Pinning the discriminator here makes the divergence a governed decision, not an accident — the same "don't let each author re-decide" motivation as [COR-026](../../../.pkit/decisions/core/COR-026-agent-placement-by-discipline.md) one level up.

**Why not swallow DEC-030's walker in v1.** DEC-030's collector reads harness-overlay JSON and skill grants in addition to a per-capability declaration — more than the shared core. Over-reaching the abstraction to absorb it now would be the inverse error (a leaky generalisation). Extract the proven declaration-collector core, instantiate the two YAML-declaration consumers, and note DEC-030's walker as a candidate to refactor onto the core later.

### Alternatives considered

- **Flag the recurrence, extract on the fourth instance.** Rejected: the shape is already stable and the third instance is being written now; deferring pays more later (reconcile three divergent copies) for no benefit.
- **Promote to a backbone/COR-level contribution pattern now.** Rejected: no non-pm consumer exists; speculative breadth (COR-007), against ADR-026's own defer-until-second-instance precedent.
- **Leave the severity choice to each DEC's prose.** Rejected: a governed family needs one recorded discriminator, or it drifts.
- **Swallow DEC-030's overlay/skill walker into the core in v1.** Rejected: it does more than the shared shape; over-reach. Refactor it onto the core later.

## Implications

- **A new `_lib/` collector core** in the pm capability realises the manifest-walk + orphan-safe read + `schema_version` validation + error taxonomy + fail-disposition, once.
- **`review_contributions` is refactored onto the core** — behaviour-preserving; it realises DEC-032, so the refactor must preserve its fail-closed collection and public collection types (a pm-capability surface touch, covered by the label-contributions Feature's bump/migration check).
- **`label_contributions` is built on the core** as the second instantiation (skip-and-warn disposition), per DEC-042.
- **DEC-030's overlay/skill walker** is recorded as a later refactor target, not changed here.
- **The severity/malformed-disposition discriminator (rule 4)** is the rule future contribution kinds follow; a new kind cites this ADR rather than re-deriving it.
- **Scope authorisation.** Extracting widens the label-contributions PR to touch DEC-032's realization (behaviour-preserving). This is a deliberate, authorised scope expansion, not incidental.
- **Stands on** COR-007, COR-026, ADR-026, and DEC-030 / DEC-032 / DEC-042 (the three instances) — all accepted or authored alongside.
