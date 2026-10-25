---
id: ACT-methodology-maintainer
name: Methodology maintainer
status: active
summary: "Whoever maintains a distribution of the methodology."
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
---

# ACT-methodology-maintainer — Methodology maintainer

Whoever maintains a distribution of the methodology.

- **Role holders:** project-kit's maintainers, or a fork's.
- **Activities:** work in the [distribution](../../glossary.md#term-distribution--distribution)'s [source repository](../../glossary.md#term-source-repository--source-repository), on the core records, the [backbone](../../glossary.md#term-backbone--backbone) and the releases adopters upgrade to.
- **Occasions:** for every [change](../../glossary.md#term-change--change) to the [methodology](../../glossary.md#term-methodology--methodology) and every [backbone](../../glossary.md#term-backbone--backbone) [release](../../glossary.md#term-release--release).
- **Context:** the [methodology](../../glossary.md#term-methodology--methodology)'s disciplines (CONTRIBUTING.md). They are the first adopter of what they ship.
- **Core:** the [source repository](../../glossary.md#term-source-repository--source-repository), its [release](../../glossary.md#term-release--release) policy and its [report](../../glossary.md#term-report--report) inbox exist for the methodology maintainer.
