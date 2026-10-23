# Overview of the analysis of evidence

<!-- pkit:overview reads=4 fingerprint=sha256:e235fadf60e364af2d4fa50685deb09e8d1eaeb7b33e6ecc484ad340c44a14e0 -->

No record states what evidence is for yet. Write one with `pkit new decision`, and name it as `purpose` in the entry of evidence under `analyses` in `.pkit/capabilities/software-analysis/project/config.yaml`.

This analysis describes what evidence does: who uses it, what they do with it, and what it must meet. It builds on the analysis of core.

## Reference

### Who takes part

| Actor | Who they are | Areas they act in |
| --- | --- | --- |
| core:ACT-developer — Developer | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | No use case names it yet. |

### Concepts

The [glossary](../glossary.md) defines each term.

### Diagrams

`pkit analysis diagram --analysis evidence` prints this analysis's diagrams from the working tree. Its subjects are `use-cases`, `journeys`, `requirements` and `chain`, or a journey's or a requirement's id.

---

The command `pkit analysis overview` writes this page from the analysis. Change the analysis, never this page (software-analysis DEC-003 point 8).
