# Overview of the analysis of evidence

<!-- pkit:overview reads=4 fingerprint=sha256:c0618587a84efd5392e1ac6c474ea167fea3a76f124000ce80827f4fced5c953 -->

No record states what evidence is for yet. Write one with `pkit new decision`, and name it as `purpose` in the entry of evidence under `analyses` in `.pkit/capabilities/software-analysis/project/config.yaml`.

This analysis describes what evidence does: who uses it, what they do with it, and what it must meet. It builds on the analysis of core.

## Use cases

- [UC-036 — Ground a claim in its source](../use-case-model/use-cases/UC-036-ground-claim.md)

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

### Diagrams

`pkit analysis diagram --analysis evidence` prints this analysis's diagrams from the working tree. Its subjects are `use-cases`, `journeys`, `requirements` and `chain`, or a journey's or a requirement's id.

---

The command `pkit analysis overview` writes this page from the analysis. Change the analysis, never this page (software-analysis DEC-003 point 8).
