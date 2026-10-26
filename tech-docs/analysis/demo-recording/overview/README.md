# Overview of the analysis of demo-recording

<!-- pkit:overview reads=5 fingerprint=sha256:c610ab23138593d6603b2c068f628f61998111aba6b00626486759c9a4eb072c -->

No record states what demo-recording is for yet. Write one with `pkit new decision`, and name it as `purpose` in the entry of demo-recording under `analyses` in `.pkit/capabilities/software-analysis/project/config.yaml`.

This analysis describes what demo-recording does: who uses it, what they do with it, and what it must meet. It builds on the analysis of core.

## Use cases

- [UC-035 — Record a demo of my command line](../use-case-model/use-cases/UC-035-record-demo.md)

## Reference

### Who takes part

| Actor | Who they are | Areas they act in |
| --- | --- | --- |
| core:ACT-ai-agent — AI agent | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | [the use cases](#use-cases) |
| core:ACT-developer — Developer | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | [the use cases](#use-cases) |

### Concepts

The [glossary](../glossary.md) defines each term.

### Diagrams

`pkit analysis diagram --analysis demo-recording` prints this analysis's diagrams from the working tree. Its subjects are `use-cases`, `journeys`, `requirements` and `chain`, or a journey's or a requirement's id.

---

The command `pkit analysis overview` writes this page from the analysis. Change the analysis, never this page (software-analysis DEC-003 point 8).
