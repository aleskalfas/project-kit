---
id: REQ-020
title: A dead anchor is an error, never silence
status: active
statement: An anchor that resolves to nothing is reported as an error, and never read as an anchor on something that did not change.
measure: "A path that matches no file, or only excluded or answer files, is a `dead-anchor`. So is an identifier that does not resolve, and a value its resolver names no file for. The whole-repository check reports every one. The change check fails in enforcing mode on each the change made."
applies-to: Every anchor of every artefact in the declared places, one under an excluded path included, wherever either friction check or validation reads it.
actors:
  - ACT-developer
refines: []
pkit:
  friction:
    anchors:
      path:
        - tests/test_friction_check.py
        - tests/test_friction_repository.py
        - tests/test_friction_validate.py
      record:
        - COR-050#7
        - COR-050#12
      artefact:
        - ACT-developer
    revalidated:
      at: 2026-10-24T04:58:17Z
      outcome: unchanged
      unchanged-because: The tests of the whole-repository check gain one for derived links across a rename. The tests of dead anchors are as they were.
---

# REQ-020 · Functional · A dead anchor is an error, never silence

**Verified by:** Tests of the [change check](../../../glossary.md#term-change-check--change-check) find an [anchor](../../../glossary.md#term-anchor--anchor) the [change](../../../glossary.md#term-change--change) added dead, or turned dead by removing its target, reported as `dead-anchor`. They find an anchor dead before the change left to the [whole-repository check](../../../glossary.md#term-whole-repository-check--whole-repository-check). Tests of the whole-repository check find every dead anchor reported, the [artefact](../../../glossary.md#term-artefact--artefact) judged on its other anchors. Tests of [validation](../../../glossary.md#term-validation--validation) find a dead anchor on a record's [point](../../../glossary.md#term-point--point), or on a document's section, failed.

**Rationale:** An [anchor](../../../glossary.md#term-anchor--anchor) says what to ask the [artefact](../../../glossary.md#term-artefact--artefact) about. A mistyped one that read as standing on nothing changed would tell its reader that the artefact holds, whatever happened to what it rests on. So COR-050 [point](../../../glossary.md#term-point--point) 7 makes a dead anchor an error, and point 12 gives each check the dead anchors it reports or fails on.
