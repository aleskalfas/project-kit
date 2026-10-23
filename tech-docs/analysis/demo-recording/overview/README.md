# Overview of the analysis of demo-recording

<!-- pkit:overview reads=4 fingerprint=sha256:58d43677fd1a7887161f2809be20dab0ac6df6874dd693157b3977b5a0091dac -->

No record states what demo-recording is for yet. Write one with `pkit new decision`, and name it as `purpose` in the entry of demo-recording under `analyses` in `.pkit/capabilities/software-analysis/project/config.yaml`.

This analysis describes what demo-recording does: who uses it, what they do with it, and what it must meet. It builds on the analysis of core.

## Use cases

- [UC-035 — Record a demo of my command line](../use-case-model/use-cases/UC-035-record-demo.md) ([not built yet](#not-built-yet): variant 3b)

## Reference

### Who takes part

| Actor | Who they are | Areas they act in |
| --- | --- | --- |
| core:ACT-ai-agent — AI agent | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | [the use cases](#use-cases) |
| core:ACT-developer — Developer | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | [the use cases](#use-cases) |

### Concepts

The [glossary](../glossary.md) defines each term.

### Not built yet

What the use cases describe and the system does not do yet, each with the record that decides it and the issue that tracks it (software-analysis DEC-001 point 1):

- [UC-035 — Record a demo of my command line](../use-case-model/use-cases/UC-035-record-demo.md): variant 3b, decided by `demo-recording:DEC-001`, tracked in `#1904`

### Diagrams

`pkit analysis diagram --analysis demo-recording` prints this analysis's diagrams from the working tree. Its subjects are `use-cases`, `journeys`, `requirements` and `chain`, or a journey's or a requirement's id.

---

The command `pkit analysis overview` writes this page from the analysis. Change the analysis, never this page (software-analysis DEC-003 point 8).
