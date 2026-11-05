---
id: REQ-053
title: Validation holds a body to its declared structure only where the format rule binds, and holds a revalidation record's body always
status: active
statement: Validation holds an artefact's body to its declared structure only where the accepted format rule binds, and holds a revalidation record's body always.
measure: Where the format rule does not bind on an artefact, validation holds no part or checked form of its body to its declared structure. Validation's summary counts that artefact. A revalidation record's body is held to its declared structure in every project. A preview reports what a proposed rule would find as `preview:`, and never changes the exit status.
applies-to: "`pkit analysis validate`, and `pkit validate`, which runs it, on every artefact and every revalidation record of each analysis."
obligation: v1:sha256:608270861bdf25a3653633b7cb5b739011db63e8ecfd5ee05307ff5a6a9ea14f
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
        - COR-009
        - ADR-061#3
        - PRJ-002#D1
        - PRJ-002#D2
        - COR-050#3
        - COR-050#6
        - COR-050#9
        - COR-051#4
        - COR-066#1
        - COR-066#2
        - COR-001
        - COR-010
        - COR-053#8
        - COR-059#3
---

# REQ-053 · Functional · Validation holds a body to its declared structure only where the format rule binds, and holds a revalidation record's body always

**Verified by:** Tests find that [validation](../../../core/glossary.md#term-validation--validation) holds no [artefact](../../../core/glossary.md#term-artefact--artefact) to its [declared structure](../../glossary.md#term-declared-structure--declared-structure) where no [rule set](../../../core/glossary.md#term-rule-set--rule-set) selects it, and reports where no [rule](../../../core/glossary.md#term-rule--rule) of `SAN` binds. They find that a [revalidation record](../../glossary.md#term-revalidation-record--revalidation-record) is held to its structure while the format rule is proposed. They also find that a preview never changes the exit status.

**Rationale:** A shipped [rule](../../../core/glossary.md#term-rule--rule) binds only through a [rule set](../../../core/glossary.md#term-rule-set--rule-set) of the [project](../../../core/glossary.md#term-project--project)'s own, which decides where it binds ([DEC-001 point 1](../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#1-what-it-keeps-and-in-what-shape) and [COR-051 point 7](../../../../../.pkit/decisions/core/COR-051-rule-sets.md#7-inheritance-and-where-rules-bind)). A rule binds only on an [artefact](../../../core/glossary.md#term-artefact--artefact), and a [revalidation record](../../glossary.md#term-revalidation-record--revalidation-record) is none. So the [capability](../../../core/glossary.md#term-capability--capability) checks a revalidation record's [declared structure](../../glossary.md#term-declared-structure--declared-structure) itself (DEC-001 point 1).
