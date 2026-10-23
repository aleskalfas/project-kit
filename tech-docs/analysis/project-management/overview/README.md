# Overview of the analysis of project-management

<!-- pkit:overview reads=4 fingerprint=sha256:59ee0b25f06ec3d0bcde13c5d61ad04f8031731fb893320faca334178a41aacf -->

No record states what project-management is for yet. Write one with `pkit new decision`, and name it as `purpose` in the entry of project-management under `analyses` in `.pkit/capabilities/software-analysis/project/config.yaml`.

This analysis describes what project-management does: who uses it, what they do with it, and what it must meet. It builds on the analysis of core.

## Reference

### Who takes part

| Actor | Who they are | Areas they act in |
| --- | --- | --- |
| [ACT-planner — Planner](../use-case-model/actors/ACT-planner.md) | The person who plans a project's work at the level of its outcomes. | No use case names it yet. |
| core:ACT-developer — Developer | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | No use case names it yet. |

### Concepts

The [glossary](../glossary.md) defines each term.

### Diagrams

`pkit analysis diagram --analysis project-management` prints this analysis's diagrams from the working tree. Its subjects are `use-cases`, `journeys`, `requirements` and `chain`, or a journey's or a requirement's id.

---

The command `pkit analysis overview` writes this page from the analysis. Change the analysis, never this page (software-analysis DEC-003 point 8).
