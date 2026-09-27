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

1. **Roots.** Internal root `docs/`, which matches today's layout, so architecture decisions stay where they are. User root: **open question 1**.
2. **Spaces.**
   - The **technical space** is `docs/` plus declared places `CONTRIBUTING.md`, `CLAUDE.md` and the core decision corpus.
   - The **user space** is the top-level `README.md` plus the adopter-facing area READMEs under `.pkit/`, as declared places.
   - Because project-kit *authors* `.pkit/`, it treats those READMEs as its own pages. This is a self-hosting exception to "sync-managed trees are never places", recorded here and never shipped to adopters. **Open question 2** is whether the scratchpad joins the technical space or stays outside documentation altogether, since it is exploratory and its notes retire.
3. **Analysis.** project-kit's analysis lives at `docs/analysis/` (the default sub-path under the internal root). Its first artefacts are the multi-clone coordination use cases that validate EPIC #943 (#890).
4. **Continuous integration.** The core friction check runs on every pull request in **warning** mode. Sweeps run with full history. A source moves to enforcing only after a period of clean warnings, by a later decision. The code-to-doc mapping stays active until onboarding converts it to anchors (project-management DEC-053).

## Rationale

Keeping `docs/` as the internal root changes nothing that exists. Declaring the scattered files as places, instead of moving them, follows the "record, never move" principle of the documentation-roots record. Warning mode first follows the adoption path the anchors-and-friction record describes: the check becomes binding only when the project chooses to make it so.

### Alternatives considered

- **Move all user-facing material into a new user root.** Deferred to open question 1. It would move adopter-facing READMEs out of the areas they describe.
- **Exclude `.pkit/` READMEs from documentation.** Rejected. They are project-kit's primary user-facing documentation.

## Implications

- Adopting the capabilities here means onboarding project-kit's documentation: anchoring pages, converting the mapping, and proposing splits, all through reviewed changes.
- The first use cases are written into `docs/analysis/use-case-model/`.

## Open questions for the maintainer

1. **User root.** Keep it equal to `docs/` for now, with the split reported as an onboarding finding, or create a separate user root now? If separate, what should it be called?
2. **Scratchpad.** Should it be part of the technical space (anchored, friction-checked), or stay outside documentation?
3. **Enforcement horizon.** How long a clean warning period before friction is enforced in continuous integration?
