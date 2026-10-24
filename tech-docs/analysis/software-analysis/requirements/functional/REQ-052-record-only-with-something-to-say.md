---
id: REQ-052
title: A revalidation record is written only where its revalidation has something to say
status: active
statement: A revalidation record is written only for a planned revalidation, one that found a regression or a gap, or a stale artefact a person confirmed.
measure: "`pkit analysis new revalidation` refuses any other record, and a record whose regression or gap no gap names, and writes nothing."
applies-to: "Every revalidation record of each analysis, whatever its trigger, and the stamp that writes it."
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
    revalidated:
      at: 2026-10-24T21:25:09Z
      outcome: unchanged
      unchanged-because: The tests this change adds or alters read an open regression's revalidations at HEAD through the backbone. The tests of what the stamp records and refuses are as they were, so the requirement holds.
---

# REQ-052 · Functional · A revalidation record is written only where its revalidation has something to say

**Verified by:** Tests find that the [stamp](../../../core/glossary.md#term-stamp--stamp) refuses a record with nothing to say, and one whose regression or gap no gap names. They find that it records a stale [artefact](../../../core/glossary.md#term-artefact--artefact) a person confirmed. Nothing checks a record written by hand for something to say.

**Rationale:** Most [revalidations](../../glossary.md#term-revalidation--revalidation) find that everything holds, and a file for each would bury the few that matter (DEC-001 point 6). Git already records the routine ones, through each [artefact](../../../core/glossary.md#term-artefact--artefact)'s own [answer](../../../core/glossary.md#term-answer--answer). Where a person decided that an artefact was stale, the record keeps the decision DEC-001 point 5 leaves to a person.
