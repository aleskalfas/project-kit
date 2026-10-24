# Overview of the analysis of software-engineering

<!-- pkit:overview reads=4 fingerprint=sha256:9fc5add8a911801d9ed875b4498bd8421d3a9489af629c8f6ba5aa61d317f51b -->

[software-engineering exists so code that agents write follows a project's own conventions, and code is reviewed before it merges](../../../../.pkit/capabilities/software-engineering/decisions/DEC-003-purpose.md).

This analysis describes what software-engineering does: who uses it, what they do with it, and what it must meet. It builds on the analyses of core and project-management.

## Use cases

- [UC-001 — Build my change under my project's conventions](../use-case-model/use-cases/UC-001-build-under-conventions.md)
- [UC-080 — Have a change's answers checked by a reviewer other than their writer](../use-case-model/use-cases/UC-080-check-answers.md) ([not built yet](#not-built-yet): variant 1b)
- [UC-081 — Decide each answer my change was not asked for](../use-case-model/use-cases/UC-081-decide-unasked-answers.md)

## Reference

### Who takes part

| Actor | Who they are | Areas they act in |
| --- | --- | --- |
| core:ACT-ai-agent — AI agent | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | [the use cases](#use-cases) |
| core:ACT-developer — Developer | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | [the use cases](#use-cases) |
| core:ACT-merge-authoriser — Merge authoriser | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | [the use cases](#use-cases) |

### Concepts

The [glossary](../glossary.md) defines each term.

### Requirements

- [REQ-060 · Quality · A secret never goes on a command line](../requirements/quality/REQ-060-secret-off-command-line.md)

### Not built yet

What the use cases describe and the system does not do yet, each with the record that decides it and the issue that tracks it (software-analysis DEC-001 point 1):

- [UC-080 — Have a change's answers checked by a reviewer other than their writer](../use-case-model/use-cases/UC-080-check-answers.md): variant 1b, decided by `COR-050#3`, tracked in `#1966`

### Diagrams

`pkit analysis diagram --analysis software-engineering` prints this analysis's diagrams from the working tree. Its subjects are `use-cases`, `journeys`, `requirements` and `chain`, or a journey's or a requirement's id.

---

The command `pkit analysis overview` writes this page from the analysis. Change the analysis, never this page (software-analysis DEC-003 point 8).
