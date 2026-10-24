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
      at: 2026-10-24T02:12:43Z
      outcome: unchanged
      unchanged-because: The change moves the read of a record's status into backbone.record_status, its behaviour kept. Where an artefact's structure binds, which REQ-053 states, is untouched.
---

# REQ-053 · Functional · The check holds a body to its declared structure only where the format rule binds, and holds a record's body always

**Verified by:** Tests find that an artefact outside every scope is not held to its structure, and that the check reports where no rule of `SAN` binds. They find that a record is held to its structure while the format rule is proposed, and that a preview never changes the exit status.

**Rationale:** A shipped rule binds only through a rule set of the project's own, which decides where it binds (DEC-001 point 1 and COR-051 point 7). No route leads from a held document, so the capability checks a record's structure itself (DEC-001 point 1).
