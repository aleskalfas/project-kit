---
id: REQ-014
title: A later change of documentation root moves no document
status: active
statement: A later change of a documentation root moves no document, and changes no documentation location already recorded.
measure: After a root changes, every document lies where it lay, and every recorded location reads as it did. Only a location chosen afterwards derives from the new root.
applies-to: Every write of a documentation root to the backbone configuration, by a command or by hand. It binds every component that derives a documentation location from a root.
actors:
  - ACT-adopter
refines: []
pkit:
  friction:
    anchors:
      path:
        - tests/test_docs_roots.py
      record:
        - COR-049#6
        - COR-049#5
      artefact:
        - ACT-adopter
    revalidated:
      at: 2026-10-24T10:39:17Z
      outcome: unchanged
      unchanged-because: ACT-adopter's need says "Upgrade the system" for "Upgrade it", and "a version the whole project pins" for "a version pinned for the whole project". The need is the same, so this artefact holds.
---

# REQ-014 · Functional · A later change of documentation root moves no document

**Verified by:** A test records a documentation location, changes the internal root, and finds the recorded location unchanged and its folder still there. A test of the status [report](../../../glossary.md#term-report--report) finds that it lists each recorded location inside the internal root, then those outside it.

**Rationale:** The adopter may declare the roots at any time, and the [system](../../../glossary.md#term-system--system) must never move a document of theirs for it. COR-049 [point](../../../glossary.md#term-point--point) 6 decides that a later [change](../../../glossary.md#term-change--change) of root affects only locations chosen afterwards, and that "moving documents is always an explicit, reviewable operation". A [component](../../../glossary.md#term-component--component) records a location as explicit when it first places a document there. So a later change of root leaves that location (COR-049 point 5).
