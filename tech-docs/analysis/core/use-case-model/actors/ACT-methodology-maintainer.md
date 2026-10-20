---
id: ACT-methodology-maintainer
name: Methodology maintainer
status: active
needs:
  - Develop the methodology in its source repository, where no sync copies over my work, and run what I ship there before any adopter does.
  - Keep each core record true for any project that adopts it.
  - Release the backbone so adopters can upgrade and pin to it, and know what each change since the last release means for them.
  - Never ship a backbone change that breaks installed projects without the migration that carries them across.
  - Receive adopters' reports with their versions attached, and link each one to the issue that fixes it.
pkit:
  friction:
    anchors:
      record:
        - ADR-059
        - PRJ-002
      artefact:
        - CONTRIBUTING.md#adding-a-core-record-cor
    revalidated:
      at: 2026-10-20T01:36:57Z
      outcome: unchanged
      unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/use-case-model/actors/, with no word changed, so the role and its needs still hold.
---

# ACT-methodology-maintainer — Methodology maintainer

Whoever maintains a distribution of the methodology.

- **Role holders:** project-kit's maintainers, or a fork's.
- **Activities:** work in the distribution's source repository, on the core records, the backbone and the releases adopters upgrade to.
- **Occasions:** for every change to the methodology and every backbone release.
- **Context:** the methodology's disciplines (CONTRIBUTING.md). They are the first adopter of what they ship.
- **Core:** the source repository, its release policy and its report inbox exist for this role.
