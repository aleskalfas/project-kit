---
id: REQ-051
title: An id, once settled, names one artefact for good, save a freed id
status: active
statement: Once settled on the default branch, a use case's, journey's or requirement's id names one artefact for good, save a freed id.
measure: The stamp numbers past every number the working tree, the default branch and the default branch's history hold, save a freed id. `pkit analysis check-numbers` fails on a number the default branch took since the branch left it.
applies-to: "Every id of a use case, a journey or a requirement across the repository's analyses, as the stamp gives it and `pkit analysis check-numbers` compares it."
actors:
  - core:ACT-developer
refines: []
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/software-analysis/scripts/_lib/numbering.py
        - .pkit/capabilities/software-analysis/scripts/_lib/numbers.py
        - tests/test_software_analysis_numbering.py
        - tests/test_software_analysis_numbers.py
      record:
        - software-analysis:DEC-001#3
---

# REQ-051 · Functional · An id, once settled, names one artefact for good, save a freed id

**Verified by:** Tests find that a number the [default branch](../../../core/glossary.md#term-default-branch--default-branch) took since the branch left it fails the number check, a number removed since included. Tests find that only the ids a named commit removed are freed, and that an entry the tools cannot honour fails both. A number written by hand that the default branch gave before the branch left it is caught by neither.

**Rationale:** Journeys, evidence, records and issues cite an [artefact](../../../core/glossary.md#term-artefact--artefact) by its id. An id given again would point each of them at another artefact ([DEC-001 point 3](../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#3-identifiers)). Where two lines of work give one number, the first to reach the [default branch](../../../core/glossary.md#term-default-branch--default-branch) keeps it (DEC-001 point 3). Ids that nothing cites carry no such promise, so the [project](../../../core/glossary.md#term-project--project) may free them, and only the project.
