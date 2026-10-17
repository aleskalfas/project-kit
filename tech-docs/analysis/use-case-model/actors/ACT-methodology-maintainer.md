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
      at: 2026-10-17T13:57:08Z
      outcome: unchanged
      unchanged-because: PRJ-002 now lets a changeset declare a capability's floor and upper bound on another capability, and has the release refuse a range that excludes a dependency. The maintainer still releases the backbone from the source repository under that release policy, and adopters still learn what each change means from the changelog, so the actor's needs and its Core hold.
---

# ACT-methodology-maintainer — Methodology maintainer

Whoever maintains a distribution of the methodology.

- **Role holders:** project-kit's maintainers, or a fork's.
- **Activities:** work in the distribution's source repository, on the core records, the backbone and the releases adopters upgrade to.
- **Occasions:** for every change to the methodology and every backbone release.
- **Context:** the methodology's disciplines (CONTRIBUTING.md). They are the first adopter of what they ship.
- **Core:** the source repository, its release policy and its report inbox exist for this role.
