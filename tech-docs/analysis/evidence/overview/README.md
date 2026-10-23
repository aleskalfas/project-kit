# Overview of the analysis of evidence

<!-- pkit:overview reads=4 fingerprint=sha256:89d6ba9f5d987f7ddb13ab48e72b3e24715bd02b6634280e833a27c13018b0c8 -->

No record states what evidence is for yet. Write one with `pkit new decision`, and name it as `purpose` in the entry of evidence under `analyses` in `.pkit/capabilities/software-analysis/project/config.yaml`.

This analysis describes what evidence does: who uses it, what they do with it, and what it must meet. It builds on the analysis of core.

## Use cases

- [UC-021 — Ground a claim in its source](../use-case-model/use-cases/UC-021-ground-claim.md) ([not built yet](#not-built-yet): step 7, variant 6b, variant 7a)

## Reference

### Who takes part

| Actor | Who they are | Areas they act in |
| --- | --- | --- |
| core:ACT-ai-agent — AI agent | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | [the use cases](#use-cases) |
| core:ACT-developer — Developer | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | [the use cases](#use-cases) |

### Concepts

The [glossary](../glossary.md) defines each term.

Each view of the domain model explains a group of related concepts:

- [010 — Outside facts and citations](../domain-model/010-outside-facts-and-citations.md)

### Not built yet

What the use cases describe and the system does not do yet, each with the record that decides it and the issue that tracks it (software-analysis DEC-001 point 1):

- [UC-021 — Ground a claim in its source](../use-case-model/use-cases/UC-021-ground-claim.md): step 7, decided by `evidence:DEC-003`, tracked in `#1910`
- [UC-021 — Ground a claim in its source](../use-case-model/use-cases/UC-021-ground-claim.md): variant 6b, decided by `evidence:DEC-003`, tracked in `#1910`
- [UC-021 — Ground a claim in its source](../use-case-model/use-cases/UC-021-ground-claim.md): variant 7a, decided by `evidence:DEC-002`, tracked in `#1910`

### Diagrams

`pkit analysis diagram --analysis evidence` prints this analysis's diagrams from the working tree. Its subjects are `use-cases`, `journeys`, `requirements` and `chain`, or a journey's or a requirement's id.

---

The command `pkit analysis overview` writes this page from the analysis. Change the analysis, never this page (software-analysis DEC-003 point 8).
