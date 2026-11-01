---
id: JRN-010
title: Adopt living-docs on a project that has documentation
status: active
actor: core:ACT-adopter
steps:
  - UC-043
  - UC-047
relies-on: []
requirements: []
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/living-docs/scripts/_lib/spaces.py
        - .pkit/capabilities/living-docs/scripts/validate.py
      record:
        - living-docs:DEC-001#1
        - living-docs:DEC-001#2
        - living-docs:DEC-001#8
      artefact:
        - UC-043
        - UC-047
---

# JRN-010 — Adopt living-docs on a project that has documentation

**Goal:** Adopt living-docs on my project that has documentation already, so each existing document is a page of a documentation space whose rules bind on it.

**Steps:**

1. [UC-043](../use-cases/010-set-up/UC-043-set-up-space.md) — Set up a documentation space for one audience
2. [UC-047](../use-cases/010-set-up/UC-047-onboard-documents.md) — Bring my existing documents into documentation spaces
   - **Needs from step 1 (UC-043):** each [documentation space](../../glossary.md#term-documentation-space--documentation-space)'s [space definition](../../glossary.md#term-space-definition--space-definition), named in the [capability](../../../core/glossary.md#term-capability--capability)'s configuration, whose scope selects the pages in the space's places. [Validation](../../../core/glossary.md#term-validation--validation) reports, without failing, a space with no definition, a definition whose scope is missing, and the pages a scope leaves out (UC-043 variant 15b). The [onboarding plan](../../glossary.md#term-onboarding-plan--onboarding-plan) puts each [unclassified document](../../glossary.md#term-unclassified-document--unclassified-document) into a space. A space's rules bind only where its definition selects, so a space with no definition leaves the pages it gains outside them.

**Variants:**

- **2a.** When the agent writes the [onboarding plan](../../glossary.md#term-onboarding-plan--onboarding-plan), a [documentation space](../../glossary.md#term-documentation-space--documentation-space) has no [space definition](../../glossary.md#term-space-definition--space-definition) yet. The plan names `pkit living-docs new space`, and the path rejoins at step 1 for that space ([UC-047](../use-cases/010-set-up/UC-047-onboard-documents.md) variant 6a).
- **2b.** The adopter rejects the onboarding plan outright. The agent drafts no [proposal](../../glossary.md#term-proposal--proposal), and the path ends with each document as it was (UC-047 variant 8b).

**Postconditions:** Each [documentation space](../../glossary.md#term-documentation-space--documentation-space) has a [space definition](../../glossary.md#term-space-definition--space-definition) whose scope selects its pages, so `LDOC`'s rules and the space's own bind on them. Each document in the spaces' places is a [page](../../glossary.md#term-page--page) of a space, or left out of the spaces' rules on purpose. Each page carries anchors, or a reason for none that a person accepted (living-docs DEC-001 points [2](../../../../../.pkit/capabilities/living-docs/decisions/DEC-001-living-docs-discipline.md#2-definitions-kept-apart-from-content) and [8](../../../../../.pkit/capabilities/living-docs/decisions/DEC-001-living-docs-discipline.md#8-brownfield-onboarding-is-transformation)).

**Minimal guarantees:**

- Stopping after step 1 moves no document. The command that sets a space up writes three things, and nothing else. They are the [space definition](../../glossary.md#term-space-definition--space-definition), its path in the [capability](../../../core/glossary.md#term-capability--capability)'s configuration and the definitions location ([living-docs DEC-001 point 2](../../../../../.pkit/capabilities/living-docs/decisions/DEC-001-living-docs-discipline.md#2-definitions-kept-apart-from-content)).
- Stopping in step 2 changes no document the adopter has not accepted. Each [proposal](../../glossary.md#term-proposal--proposal) passes the adopter's review, and lands as an ordinary change ([living-docs DEC-001 point 8](../../../../../.pkit/capabilities/living-docs/decisions/DEC-001-living-docs-discipline.md#8-brownfield-onboarding-is-transformation)).
