# Overview of the analysis of living-docs

<!-- pkit:overview reads=4 fingerprint=sha256:a65125e8c19a314ae5b197b61c43ba14189682e07c8a18a3ef5773eff05b5de9 -->

No record states what living-docs is for yet. Write one with `pkit new decision`, and name it as `purpose` in the entry of living-docs under `analyses` in `.pkit/capabilities/software-analysis/project/config.yaml`.

This analysis describes what living-docs does: who uses it, what they do with it, and what it must meet. It builds on the analyses of core and project-management (optional).

## Use cases

- [UC-043 — Set up a documentation space for one audience](../use-case-model/use-cases/UC-043-set-up-space.md) ([not built yet](#not-built-yet): variant 1b, step 2, step 6)
- [UC-044 — Write a page for the reader it names](../use-case-model/use-cases/UC-044-write-page.md) ([not built yet](#not-built-yet): step 5, variant 10a)
- [UC-045 — Have the fix for a stale page proposed, and review it before it is applied](../use-case-model/use-cases/UC-045-propose-page-fix.md) ([not built yet](#not-built-yet): variant 4c, variant 4e)
- [UC-046 — Have a page read as its declared reader would read it](../use-case-model/use-cases/UC-046-review-page-as-reader.md) ([not built yet](#not-built-yet): step 3, variant 4a)
- [UC-047 — Bring my existing documents into documentation spaces](../use-case-model/use-cases/UC-047-onboard-documents.md)

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

- [010 — Spaces and pages](../domain-model/010-spaces-and-pages.md)
- [020 — Proposals and reviews](../domain-model/020-proposals-and-reviews.md)

### Requirements

- [REQ-022 · Functional · The living-docs agent proposes each change, and applies none](../requirements/functional/REQ-022-agent-proposes-only.md)
- [REQ-023 · Quality · A refused stamp puts back what it wrote, or names what it could not](../requirements/quality/REQ-023-refused-stamp-writes-nothing.md)
- [REQ-024 · Functional · Validation checks a part of an LDOC rule only where the rule binds](../requirements/functional/REQ-024-checks-where-rule-binds.md)
- [REQ-025 · Constraint · Nothing in living-docs fetches the text a captured source names](../requirements/constraints/REQ-025-never-fetch-source.md)

### Not built yet

What the use cases describe and the system does not do yet, each with the record that decides it and the issue that tracks it (software-analysis DEC-001 point 1):

- [UC-043 — Set up a documentation space for one audience](../use-case-model/use-cases/UC-043-set-up-space.md): variant 1b, decided by `living-docs:DEC-001#1`, tracked in `#1922`
- [UC-043 — Set up a documentation space for one audience](../use-case-model/use-cases/UC-043-set-up-space.md): step 2, decided by `living-docs:DEC-001#1`, tracked in `#1922`
- [UC-043 — Set up a documentation space for one audience](../use-case-model/use-cases/UC-043-set-up-space.md): step 6, decided by `ADR-034#1`, tracked in `#1765`
- [UC-044 — Write a page for the reader it names](../use-case-model/use-cases/UC-044-write-page.md): step 5, decided by `ADR-034#1`, tracked in `#1765`
- [UC-044 — Write a page for the reader it names](../use-case-model/use-cases/UC-044-write-page.md): variant 10a, decided by `living-docs:DEC-002`, tracked in `#1803`
- [UC-045 — Have the fix for a stale page proposed, and review it before it is applied](../use-case-model/use-cases/UC-045-propose-page-fix.md): variant 4c, decided by `living-docs:DEC-002#5`, tracked in `#1812`
- [UC-045 — Have the fix for a stale page proposed, and review it before it is applied](../use-case-model/use-cases/UC-045-propose-page-fix.md): variant 4e, decided by `living-docs:DEC-002#6`, tracked in `#1812`
- [UC-046 — Have a page read as its declared reader would read it](../use-case-model/use-cases/UC-046-review-page-as-reader.md): step 3, decided by `living-docs:DEC-001#7`, tracked in `#1921`
- [UC-046 — Have a page read as its declared reader would read it](../use-case-model/use-cases/UC-046-review-page-as-reader.md): variant 4a, decided by `living-docs:DEC-002#8`, tracked in `#1812`

### Diagrams

`pkit analysis diagram --analysis living-docs` prints this analysis's diagrams from the working tree. Its subjects are `use-cases`, `journeys`, `requirements` and `chain`, or a journey's or a requirement's id.

---

The command `pkit analysis overview` writes this page from the analysis. Change the analysis, never this page (software-analysis DEC-003 point 8).
