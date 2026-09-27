---
id: ADR-055
title: project-kit adopts software-analysis and living-docs as their first adopter
status: proposed
date: 2026-09-28
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

project-kit ships the two capabilities that keep analysis and documentation true (software-analysis DEC-001, living-docs DEC-001), on core pieces accepted alongside them: backbone configuration, documentation roots, anchors and friction, rule sets and slots (COR-048 to COR-052). The maintainer chose project-kit as their first adopter, ahead of the downstream projects that asked for them, so that rough edges are found here first.

project-kit's documentation does not sit in one place. Its user-facing material is the top-level README plus the adopter-facing area READMEs under `.pkit/`. Its technical material is scattered: `docs/architecture/` (architecture decisions), `CONTRIBUTING.md`, `CLAUDE.md`, the core decision corpus under `.pkit/decisions/`, and the scratchpad. Two things follow. First, the living-docs rule that a sync-managed tree is never a place collides with project-kit's self-hosting: `.pkit/` is sync-managed for every adopter, but here it is the source being authored. Second, the core rule that roots lie outside the methodology tree means the READMEs under `.pkit/` can join a space only as declared places, never through a root.

## Decision

*Proposed — the specifics below were not settled in the design discussion and await the maintainer.*

1. **Roots.** User root `docs/`, internal root `tech-docs/`. This is decided by the maintainer on 2026-09-28, following the split planned in the design.
   - Today `docs/` holds only technical material: the architecture decisions. Their location is already an explicit overlay value, so changing the internal root moves nothing (COR-049).
   - Their relocation to `tech-docs/` is proposed during onboarding, as a reviewed change that rewrites references. Until then, the misplacement is reported as an onboarding finding.
2. **Spaces.**
   - The **technical space** is `tech-docs/`, plus declared places: `CONTRIBUTING.md`, `CLAUDE.md`, the core decision corpus, and the architecture decisions until they are relocated.
   - The **user space** is `docs/`, plus declared places: the top-level `README.md` and the adopter-facing area READMEs under `.pkit/`.
   - Because project-kit *authors* `.pkit/`, it treats those READMEs as its own pages. This is a self-hosting exception to "sync-managed trees are never places", recorded here and never shipped to adopters. The **scratchpad stays outside documentation** (maintainer decision, 2026-09-28). Its notes are non-normative working drafts that retire once their question resolves, so they are neither anchored nor friction-checked. The records and documents they produce are.
3. **Analysis.** project-kit's analysis lives at `tech-docs/analysis/` (the default sub-path under the internal root). Its first artefacts are the multi-clone coordination use cases that validate EPIC #943 (#890).
4. **Continuous integration.** The core friction check runs on every pull request in **warning** mode. Sweeps run with full history. A source moves to enforcing only after a period of clean warnings, by a later decision. The code-to-doc mapping stays active until onboarding converts it to anchors (project-management DEC-053).

## Rationale

Splitting the roots now gives project-kit the layout the living-docs separation rule asks for, and the same layout as the downstream adopter that motivated the capabilities. Nothing moves on the split, because existing locations are explicit. Declaring the scattered files as places, instead of moving them, follows the "record, never move" principle of the documentation-roots record. Warning mode first follows the adoption path the anchors-and-friction record describes: the check becomes binding only when the project chooses to make it so.

### Alternatives considered

- **Keep both roots at `docs/` for now.** Rejected by the maintainer: the split is the intended layout, and doing it first avoids a second transition later.
- **Move the adopter-facing READMEs into the user root.** Rejected. They stay beside the areas they describe, as declared places.
- **Exclude `.pkit/` READMEs from documentation.** Rejected. They are project-kit's primary user-facing documentation.

## Implications

- Adopting the capabilities here means onboarding project-kit's documentation: anchoring pages, converting the mapping, and proposing splits, all through reviewed changes.
- The first use cases are written into `tech-docs/analysis/use-case-model/`.
- The backbone configuration gains the documentation block (`user: docs/`, `internal: tech-docs/`) when the documentation-roots key is implemented.

## Open questions for the maintainer

1. ~~User root~~: decided 2026-09-28, user `docs/`, internal `tech-docs/`.
2. ~~Scratchpad~~: decided 2026-09-28, it stays outside documentation.
3. **Enforcement horizon.** How long a clean warning period before friction is enforced in continuous integration?
