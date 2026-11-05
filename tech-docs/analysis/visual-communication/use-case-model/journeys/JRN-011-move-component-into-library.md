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
        - visual-communication:DEC-001#4
        - visual-communication:DEC-003#8
        - visual-communication:DEC-006#1
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
   - **Needs from step 2 (UC-110):** the library component, in a new library version of the library. A copied presentation is a draft with its lock pinned (UC-093, variant 1b). It keeps the library versions it was copied with, so it lacks the library component until a person moves its lock.

**Variants:**

None.

**Postconditions:** The library holds the library component, and another presentation is drawn with it. The piece the local component came from uses the library component too, unless that piece is final.

**Minimal guarantees:** None.

## Sources

- **The goal:** the promotion of a local component. The maintainer asked how it works on 31 October, in planning the capability (#2423). An example from that planning is a third talk that needs the Friday talk's pyramid, and moves it into a library.
- **The hand-overs:**
  - **Step 2:** a local component and a library component are the same kind of data. A helper script stays the project's code, so the local component it writes stays in its piece ([DEC-001 point 4](../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#4-components-are-data-and-the-engine-knows-none-by-name) and [DEC-006 point 1](../../../../../.pkit/capabilities/visual-communication/decisions/DEC-006-work-outside-the-engine-and-outputs.md#1-a-program-run-while-preparing-may-write-a-picture)).
  - **Step 3:** a copy of a final piece starts as a draft with its lock pinned, which moves only when a person moves it ([DEC-003 point 8](../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#8-a-pieces-state-says-who-moves-its-lock)).
