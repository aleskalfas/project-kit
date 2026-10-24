# Overview of the analysis of software-analysis

<!-- pkit:overview reads=4 fingerprint=sha256:5f6230a01dda0a43ac4faedf6c240718eba11286858e80ebad25e881df308203 -->

[Software analysis keeps actors, use cases, journeys and terms true as the software changes](../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md).

This analysis describes what software-analysis does: who uses it, what they do with it, and what it must meet. It builds on the analyses of core and project-management (optional).

## Use cases

- [UC-070 — Choose the parts of each kind of analysis artefact as I adopt software analysis](../use-case-model/use-cases/UC-070-choose-parts.md) ([not built yet](#not-built-yet): step 5)
- [UC-071 — Describe my existing project from its code, documents and decisions](../use-case-model/use-cases/UC-071-describe-existing-project.md) ([not built yet](#not-built-yet): step 5, variant 3b, variant 3c, variant 4b)
- [UC-072 — Revise the analysis before a proposed change is built](../use-case-model/use-cases/UC-072-revise-before-change.md) ([not built yet](#not-built-yet): step 7)
- [UC-073 — Revalidate the analysis after a change from an agent's proposed outcomes](../use-case-model/use-cases/UC-073-revalidate-after-change.md) ([not built yet](#not-built-yet): step 13, variant 7c)
- [UC-074 — Free the ids of artefacts nothing cites](../use-case-model/use-cases/UC-074-free-uncited-ids.md)

## Reference

### Who takes part

| Actor | Who they are | Areas they act in |
| --- | --- | --- |
| core:ACT-adopter — Adopter | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | [the use cases](#use-cases) |
| core:ACT-ai-agent — AI agent | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | [the use cases](#use-cases) |
| core:ACT-developer — Developer | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | [the use cases](#use-cases) |
| core:ACT-operator — Operator | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | [the use cases](#use-cases) |

### Concepts

The [glossary](../glossary.md) defines each term.

Each view of the domain model explains a group of related concepts:

- [010 — Analyses, use cases and their ids](../domain-model/010-analyses-and-use-cases.md)
- [020 — Revalidations and what they find](../domain-model/020-revalidations.md)
- [030 — Kinds and their structures](../domain-model/030-kinds-and-structures.md)

### Requirements

- [REQ-050 · Functional · An agent proposes what the analysis records, and a person decides it](../requirements/functional/REQ-050-agent-proposes.md)
- [REQ-051 · Functional · An id, once settled, names one artefact for good, save a freed id](../requirements/functional/REQ-051-id-names-one-artefact.md)
- [REQ-052 · Functional · A revalidation record is written only where its revalidation has something to say](../requirements/functional/REQ-052-record-only-with-something-to-say.md)
- [REQ-053 · Functional · The check holds a body to its declared structure only where the format rule binds, and holds a record's body always](../requirements/functional/REQ-053-structure-binds-where-the-rule-binds.md)

### Not built yet

What the use cases describe and the system does not do yet, each with the record that decides it and the issue that tracks it (software-analysis DEC-001 point 1):

- [UC-070 — Choose the parts of each kind of analysis artefact as I adopt software analysis](../use-case-model/use-cases/UC-070-choose-parts.md): step 5, decided by `ADR-034#1`, tracked in `#1765`
- [UC-071 — Describe my existing project from its code, documents and decisions](../use-case-model/use-cases/UC-071-describe-existing-project.md): step 5, decided by `ADR-034#1`, tracked in `#1765`
- [UC-071 — Describe my existing project from its code, documents and decisions](../use-case-model/use-cases/UC-071-describe-existing-project.md): variant 3b, decided by `ADR-034#1`, tracked in `#1765`
- [UC-071 — Describe my existing project from its code, documents and decisions](../use-case-model/use-cases/UC-071-describe-existing-project.md): variant 3c, decided by `COR-004`, tracked in `#1884`
- [UC-071 — Describe my existing project from its code, documents and decisions](../use-case-model/use-cases/UC-071-describe-existing-project.md): variant 4b, decided by `COR-004`, tracked in `#1884`
- [UC-072 — Revise the analysis before a proposed change is built](../use-case-model/use-cases/UC-072-revise-before-change.md): step 7, decided by `ADR-034#1`, tracked in `#1765`
- [UC-073 — Revalidate the analysis after a change from an agent's proposed outcomes](../use-case-model/use-cases/UC-073-revalidate-after-change.md): step 13, decided by `ADR-034#1`, tracked in `#1765`
- [UC-073 — Revalidate the analysis after a change from an agent's proposed outcomes](../use-case-model/use-cases/UC-073-revalidate-after-change.md): variant 7c, decided by `software-analysis:DEC-001#5`, tracked in `#1929`

### Diagrams

`pkit analysis diagram --analysis software-analysis` prints this analysis's diagrams from the working tree. Its subjects are `use-cases`, `journeys`, `requirements` and `chain`, or a journey's or a requirement's id.

---

The command `pkit analysis overview` writes this page from the analysis. Change the analysis, never this page (software-analysis DEC-003 point 8).
