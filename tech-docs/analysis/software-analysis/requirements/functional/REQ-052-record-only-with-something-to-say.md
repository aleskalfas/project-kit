---
id: REQ-052
title: A revalidation record is written only where its revalidation has something to say
status: active
statement: A revalidation record is written only for a planned revalidation, one that found a regression or a gap, or a stale artefact a person confirmed.
measure: "`pkit analysis new revalidation` refuses any other revalidation record, and one whose regression or gap no gap names, and writes nothing."
applies-to: "Every revalidation record of each analysis, whatever its trigger, and the stamp that writes it."
obligation: v1:sha256:8e6f16e34f410688758cb2f85d718cd13e4c739099a5d064747a0f652a1542fe
actors:
  - core:ACT-developer
refines: []
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/software-analysis/scripts/_lib/revalidation.py
        - tests/test_software_analysis_records.py
      record:
        - software-analysis:DEC-001#5
        - software-analysis:DEC-001#6
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
---

# REQ-052 · Functional · A revalidation record is written only where its revalidation has something to say

**Verified by:** Tests find that the [stamp](../../../core/glossary.md#term-stamp--stamp) refuses a [revalidation record](../../glossary.md#term-revalidation-record--revalidation-record) with nothing to say, and one whose regression or gap no gap names. They find that it records a stale [artefact](../../../core/glossary.md#term-artefact--artefact) a person confirmed. Nothing checks a record written by hand for something to say.

**Rationale:** Most [revalidations](../../glossary.md#term-revalidation--revalidation) find that everything holds, and a file for each would bury the few that matter ([DEC-001 point 6](../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#6-records-only-when-there-is-something-to-say)). Git already records the routine ones, through each [artefact](../../../core/glossary.md#term-artefact--artefact)'s own [answer](../../../core/glossary.md#term-answer--answer). Where a person decided that an artefact was stale, the [revalidation record](../../glossary.md#term-revalidation-record--revalidation-record) keeps the decision [software-analysis DEC-001 point 5](../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#5-revalidation) leaves to a person.
