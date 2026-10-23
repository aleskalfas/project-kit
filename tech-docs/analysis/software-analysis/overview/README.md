# Overview of the analysis of software-analysis

<!-- pkit:overview reads=4 fingerprint=sha256:8f2451039533c9cbd6b4a77cbea034e72007c94e8e29600bdf85ae5c84483b49 -->

No record states what software-analysis is for yet. Write one with `pkit new decision`, and name it as `purpose` in the entry of software-analysis under `analyses` in `.pkit/capabilities/software-analysis/project/config.yaml`.

This analysis describes what software-analysis does: who uses it, what they do with it, and what it must meet. It builds on the analyses of core and project-management (optional).

## Reference

### Who takes part

| Actor | Who they are | Areas they act in |
| --- | --- | --- |
| core:ACT-adopter — Adopter | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | No use case names it yet. |
| core:ACT-developer — Developer | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | No use case names it yet. |

### Concepts

The [glossary](../glossary.md) defines each term.

### Diagrams

`pkit analysis diagram --analysis software-analysis` prints this analysis's diagrams from the working tree. Its subjects are `use-cases`, `journeys`, `requirements` and `chain`, or a journey's or a requirement's id.

---

The command `pkit analysis overview` writes this page from the analysis. Change the analysis, never this page (software-analysis DEC-003 point 8).
