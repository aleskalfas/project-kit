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
      path:
        - CONTRIBUTING.md
      record:
        - ADR-059
        - PRJ-002
    revalidated:
      at: 2026-10-14T18:58:47Z
      outcome: unchanged
      unchanged-because: ADR-059 and PRJ-002 now write their points as headings carrying the same numbers and labels, word for word. PRJ-002's paragraph on what it leaves to the release-flow spec sits under a heading of its own, unchanged. The source repository and the release policy read as before, so the maintainer's needs to develop the methodology where no sync copies over their work, and to release the backbone, stand.
---

# ACT-methodology-maintainer — Methodology maintainer

Whoever maintains a distribution of the methodology.

- **Role holders:** project-kit's maintainers, or a fork's.
- **Activities:** work in the distribution's source repository, on the core records, the backbone and the releases adopters upgrade to.
- **Occasions:** for every change to the methodology and every backbone release.
- **Context:** the methodology's disciplines (CONTRIBUTING.md). They are the first adopter of what they ship.
- **Core:** the source repository, its release policy and its report inbox exist for this role.
