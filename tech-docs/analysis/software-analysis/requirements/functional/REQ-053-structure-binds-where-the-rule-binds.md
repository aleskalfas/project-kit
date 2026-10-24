---
id: REQ-053
title: The check holds a body to its declared structure only where the format rule binds, and holds a record's body always
status: active
statement: The check holds an artefact's body to its declared structure only where the accepted format rule binds, and holds a revalidation record's body always.
measure: Where the format rule does not bind on an artefact, the check fails nothing in its body, and its summary counts the artefact. A revalidation record's body is held to its declared structure in every project. A preview reports what a proposed rule would find as `preview:`, and never changes the exit status.
applies-to: "`pkit analysis validate`, and `pkit validate`, which runs it, on every artefact and every revalidation record of each analysis."
actors:
  - core:ACT-developer
  - core:ACT-adopter
refines: []
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/software-analysis/scripts/_lib/check.py
        - tests/test_software_analysis_structure.py
      record:
        - software-analysis:DEC-001#1
        - COR-051#7
    revalidated:
      at: 2026-10-24T21:24:50Z
      outcome: unchanged
      unchanged-because: check.py now reads an open regression's revalidations through the backbone's explanation at HEAD. Where a body is held to its declared structure is as it was.
---

# REQ-053 · Functional · The check holds a body to its declared structure only where the format rule binds, and holds a record's body always

**Verified by:** Tests find that an [artefact](../../../core/glossary.md#term-artefact--artefact) outside every scope is not held to its structure, and that the check reports where no [rule](../../../core/glossary.md#term-rule--rule) of `SAN` binds. They find that a record is held to its structure while the format rule is proposed, and that a preview never changes the exit status.

**Rationale:** A shipped [rule](../../../core/glossary.md#term-rule--rule) binds only through a [rule set](../../../core/glossary.md#term-rule-set--rule-set) of the [project](../../../core/glossary.md#term-project--project)'s own, which decides where it binds (DEC-001 point 1 and COR-051 point 7). No route leads from a held document, so the [capability](../../../core/glossary.md#term-capability--capability) checks a record's structure itself (DEC-001 point 1).
