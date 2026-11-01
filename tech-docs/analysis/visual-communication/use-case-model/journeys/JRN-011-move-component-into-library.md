---
id: JRN-011
title: Move a local component into a library
status: active
actor: core:ACT-developer
steps:
  - UC-096
  - UC-110
  - UC-093
relies-on: []
requirements: []
pkit:
  friction:
    anchors:
      record:
        - COR-017
        - COR-013
      artefact:
        - UC-096
        - UC-110
        - UC-093
---

# JRN-011 — Move a local component into a library

**Goal:** Move a local component of one of my pieces into a library my project owns, so my other pieces can use it.

**Steps:**

1. [UC-096](../use-cases/010-make/UC-096-add-visual-as-data.md) — Add a new kind of visual to a piece as data
2. [UC-110](../use-cases/020-build-libraries/UC-110-add-library-component.md) — Add a library component and mark it stable
   - **Needs from step 1 (UC-096):** the local component, written as data in the piece. One that a helper script wrote stays in its piece (UC-110, variant 1b).
3. [UC-093](../use-cases/010-make/UC-093-build-presentation.md) — Build a presentation from library components
   - **Needs from step 2 (UC-110):** the library component, in a new library version of the library. An adapted presentation keeps the library versions it was copied with, so it lacks the library component until its lock moves (UC-093, variant 1b).

**Variants:**

None.

**Postconditions:** The library holds the library component, and another presentation is drawn with it. The piece the local component came from uses it too, unless that piece is delivered.

**Minimal guarantees:** None.

## Sources

- **The goal:** the promotion of a local component, as the planning note `2026-10-30-visual-work-capability` describes it in its naming pass. The maintainer asked on 31 October how it works. The note's point 4c gives the example of a third talk, which moves the Friday talk's pyramid into a library.
- **No accepted record decides the steps yet.** The capability's records, written under #2427, will decide them. The journey then anchors each record, and its hand-overs follow them.
