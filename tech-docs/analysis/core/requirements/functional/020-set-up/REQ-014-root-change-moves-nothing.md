---
id: REQ-014
title: A later edit of a documentation root moves no document
status: active
statement: A later edit of a documentation root moves no document, and changes no documentation location already recorded.
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
---

# REQ-014 · Functional · A later edit of a documentation root moves no document

**Verified by:** A test records a documentation location, changes the internal root, and finds the recorded location unchanged and its folder still there. A test of `pkit status` finds that it lists each recorded location inside the internal root, then those outside it.

**Rationale:** The adopter may declare the roots at any time, and the [system](../../../glossary.md#term-system--system) must never move a document of theirs for it. [COR-049 point 6](../../../../../../.pkit/decisions/core/COR-049-documentation-roots.md#6-no-document-moves-no-location-changes-silently) decides that an edit of a root affects only locations chosen afterwards, and that "moving documents is always an explicit, reviewable operation". A [component](../../../glossary.md#term-component--component) records a location as explicit when it first places a document there. So a later edit of a root leaves that location ([COR-049 point 5](../../../../../../.pkit/decisions/core/COR-049-documentation-roots.md#5-a-derived-location-is-recorded-when-it-is-first-used)).
