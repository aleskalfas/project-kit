---
id: REQ-014
title: A later edit of a documentation root moves no document
status: active
statement: A later edit of a documentation root moves no document, and changes no path already recorded for documents.
measure: After a root changes, every document lies where it lay, and every path recorded for documents reads as it did. Only a path chosen afterwards derives from the new root.
applies-to: Every write of a documentation root to the backbone configuration, by a command or by hand. It binds every component that derives a path for documents from a root.
obligation: v1:sha256:23e4b8c82eb4573dd8825685e91a68c3f5e86f2275b7ecd35a2b8afc30f02d0c
actors:
  - ACT-adopter
refines: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/docs_roots.py
        - tests/test_docs_roots.py
      record:
        - COR-049#6
        - COR-049#5
      artefact:
        - ACT-adopter
---

# REQ-014 · Functional · A later edit of a documentation root moves no document

**Verified by:** A test records the path of a [component](../../../glossary.md#term-component--component)'s documents, changes the internal root, and finds the recorded path unchanged and its folder still there. A test of `pkit status` finds that it lists each path recorded for documents inside the internal root, then those outside it.

**Rationale:** The adopter may declare the roots at any time, and the [system](../../../glossary.md#term-system--system) must never move a document of theirs for it. [COR-049 point 6](../../../../../../.pkit/decisions/core/COR-049-documentation-roots.md#6-no-document-moves-no-location-changes-silently) decides that an edit of a root affects only paths chosen afterwards, and that "moving documents is always an explicit, reviewable operation". A [component](../../../glossary.md#term-component--component) records a path it derived as explicit when it first places a document there. So a later edit of a root leaves that path ([COR-049 point 5](../../../../../../.pkit/decisions/core/COR-049-documentation-roots.md#5-a-derived-location-is-recorded-when-it-is-first-used)).
