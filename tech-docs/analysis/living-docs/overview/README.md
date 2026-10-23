# Overview of the analysis of living-docs

<!-- pkit:overview reads=4 fingerprint=sha256:338beef6577578c78b970761783fd07591c61f42a969964971ed08079aaaca5d -->

No record states what living-docs is for yet. Write one with `pkit new decision`, and name it as `purpose` in the entry of living-docs under `analyses` in `.pkit/capabilities/software-analysis/project/config.yaml`.

This analysis describes what living-docs does: who uses it, what they do with it, and what it must meet. It builds on the analyses of core and project-management (optional).

## Reference

### Who takes part

| Actor | Who they are | Areas they act in |
| --- | --- | --- |
| core:ACT-adopter — Adopter | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | No use case names it yet. |
| core:ACT-developer — Developer | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | No use case names it yet. |

### Concepts

The [glossary](../glossary.md) defines each term.

### Diagrams

`pkit analysis diagram --analysis living-docs` prints this analysis's diagrams from the working tree. Its subjects are `use-cases`, `journeys`, `requirements` and `chain`, or a journey's or a requirement's id.

---

The command `pkit analysis overview` writes this page from the analysis. Change the analysis, never this page (software-analysis DEC-003 point 8).
