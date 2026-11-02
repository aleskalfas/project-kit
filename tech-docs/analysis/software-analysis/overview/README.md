# Overview of the analysis of software-analysis

<!-- pkit:overview reads=5 fingerprint=sha256:64d17b159b3a8f73131620c3dcb4fca2af4c191a581a4e26f1277f7fd1900e96 -->

[Software analysis keeps actors, use cases, journeys and terms true as the software changes](../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md).

This analysis describes what software-analysis does: who uses it, what they do with it, and what it must meet. It builds on the analyses of core and project-management (optional).

## Areas

### 010-describe

Describe a project in its analysis, each kind of artefact in the parts the project chose, and each artefact under an id that names it alone.

**Builds on:** no other area.

**Its concepts:**

- [010 — Analyses, use cases and their ids](../domain-model/010-analyses-and-use-cases.md)
- [020 — Revalidations and what they find](../domain-model/020-revalidations.md)
- [030 — Kinds and their structures](../domain-model/030-kinds-and-structures.md)

**Its requirements:** none.

**Its use cases:**

- [UC-070 — Choose the parts of each kind of analysis artefact as I adopt software analysis](../use-case-model/use-cases/010-describe/UC-070-choose-parts.md) ([not built yet](#not-built-yet): step 5)
- [UC-071 — Describe my existing project from its code, documents and decisions](../use-case-model/use-cases/010-describe/UC-071-describe-existing-project.md) ([not built yet](#not-built-yet): step 5, variant 3b, variant 3c, variant 4b)
- [UC-074 — Free the ids of artefacts nothing cites](../use-case-model/use-cases/010-describe/UC-074-free-uncited-ids.md)

**Its journeys:** none.

### 020-revalidate

Keep the analysis true as the project changes, revised before a change is built or revalidated after it, and never rewritten to match broken code.

**Builds on:** [010-describe](#010-describe).

**Its concepts:**

- [010 — Analyses, use cases and their ids](../domain-model/010-analyses-and-use-cases.md)
- [020 — Revalidations and what they find](../domain-model/020-revalidations.md)
- [030 — Kinds and their structures](../domain-model/030-kinds-and-structures.md)

**Its requirements:** none.

**Its use cases:**

- [UC-072 — Revise the analysis before a proposed change is built](../use-case-model/use-cases/020-revalidate/UC-072-revise-before-change.md) ([not built yet](#not-built-yet): step 7)
- [UC-073 — Revalidate the analysis after a change from an agent's proposed outcomes](../use-case-model/use-cases/020-revalidate/UC-073-revalidate-after-change.md) ([not built yet](#not-built-yet): step 13)

**Its journeys:** none.

## Reference

### Who takes part

| Actor | Who they are | Areas they act in |
| --- | --- | --- |
| core:ACT-adopter — Adopter | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | [010-describe](#010-describe) |
| core:ACT-ai-agent — AI agent | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | [010-describe](#010-describe), [020-revalidate](#020-revalidate) |
| core:ACT-developer — Developer | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | [010-describe](#010-describe), [020-revalidate](#020-revalidate) |
| core:ACT-operator — Operator | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | [010-describe](#010-describe), [020-revalidate](#020-revalidate) |

### Concepts

The [glossary](../glossary.md) defines each term.

Each view of the domain model explains a group of related concepts:

- [010 — Analyses, use cases and their ids](../domain-model/010-analyses-and-use-cases.md)
- [020 — Revalidations and what they find](../domain-model/020-revalidations.md)
- [030 — Kinds and their structures](../domain-model/030-kinds-and-structures.md)

### Requirements in no area

- [REQ-050 · Functional · An agent proposes what the analysis records, and a person decides it](../requirements/functional/REQ-050-agent-proposes.md)
- [REQ-051 · Functional · An id, once settled, names one artefact for good, save a freed id](../requirements/functional/REQ-051-id-names-one-artefact.md)
- [REQ-052 · Functional · A revalidation record is written only where its revalidation has something to say](../requirements/functional/REQ-052-record-only-with-something-to-say.md)
- [REQ-053 · Functional · The check holds a body to its declared structure only where the format rule binds, and holds a record's body always](../requirements/functional/REQ-053-structure-binds-where-the-rule-binds.md)

### Not built yet

What the use cases describe and the system does not do yet, each with the record that decides it and the issue that tracks it (software-analysis DEC-001 point 1):

- [UC-070 — Choose the parts of each kind of analysis artefact as I adopt software analysis](../use-case-model/use-cases/010-describe/UC-070-choose-parts.md): step 5, decided by `ADR-034#1`, tracked in `#1765`
- [UC-071 — Describe my existing project from its code, documents and decisions](../use-case-model/use-cases/010-describe/UC-071-describe-existing-project.md): step 5, decided by `ADR-034#1`, tracked in `#1765`
- [UC-071 — Describe my existing project from its code, documents and decisions](../use-case-model/use-cases/010-describe/UC-071-describe-existing-project.md): variant 3b, decided by `ADR-034#1`, tracked in `#1765`
- [UC-071 — Describe my existing project from its code, documents and decisions](../use-case-model/use-cases/010-describe/UC-071-describe-existing-project.md): variant 3c, decided by `COR-004`, tracked in `#1884`
- [UC-071 — Describe my existing project from its code, documents and decisions](../use-case-model/use-cases/010-describe/UC-071-describe-existing-project.md): variant 4b, decided by `COR-004`, tracked in `#1884`
- [UC-072 — Revise the analysis before a proposed change is built](../use-case-model/use-cases/020-revalidate/UC-072-revise-before-change.md): step 7, decided by `ADR-034#1`, tracked in `#1765`
- [UC-073 — Revalidate the analysis after a change from an agent's proposed outcomes](../use-case-model/use-cases/020-revalidate/UC-073-revalidate-after-change.md): step 13, decided by `ADR-034#1`, tracked in `#1765`

### Diagrams

`pkit analysis diagram --analysis software-analysis` prints this analysis's diagrams from the working tree. Its subjects are `use-cases`, `journeys`, `requirements` and `chain`, or a journey's or a requirement's id.

---

The command `pkit analysis overview` writes this page from the analysis. Change the analysis, never this page (software-analysis DEC-003 point 8).
