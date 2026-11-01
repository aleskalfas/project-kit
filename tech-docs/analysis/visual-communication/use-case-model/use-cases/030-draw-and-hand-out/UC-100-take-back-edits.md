---
id: UC-100
title: Take back what people changed where a piece is drawn
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
requirements: []
after:
  - [UC-099]
pkit:
  friction:
    anchors:
      record:
        - visual-communication:DEC-001#2
        - visual-communication:DEC-001#3
        - visual-communication:DEC-001#11
        - visual-communication:DEC-005#11
        - COR-017
        - COR-013
---

# UC-100 — Take back what people changed where a piece is drawn

**Goal:** Take what people changed where my piece is drawn, such as on a board, back into its content when I ask.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): does the work for the developer, and may run any step the developer runs.

**Preconditions:** **From [UC-099](UC-099-draw-through-renderer.md):** The piece is drawn through a renderer that people can edit, such as an online board.

**Assumptions:**

- The project has visual-communication installed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).

**Trigger:** People edited the drawn piece, such as a title fixed on the board during a review, and the developer wants the edit in the content.

**Main path:**

1. The developer asks the system to take back the edits made since the piece was last drawn there.
2. The system finds each edit, and traces it to where the edited object came from. That is a field of the content, a local component of the piece, or a library.
3. The system writes each edit that has exactly one field of the content or of a local component to go to into that field. An example is a title, written into its slide's title.
4. The system lists each other edit, and writes nothing for it. One example is a colour picked by hand. Another is a box moved where the layout sets its position. A third is an edit to what a library draws.
5. The developer reads what the system wrote as a diff, and commits it or reverts it.
6. For each listed edit, the developer picks another option of the library component, alters the brand or a library, or drops the edit.

**Variants:**

- **2a.** A field was edited both where the piece is drawn and in the content since the last drawing. The system writes neither edit, and lists the conflict.
- **6a.** A listed edit is to what a library taken in from another project draws ([UC-109](../020-build-libraries/UC-109-take-in-shared-library.md)). The system names that library's repository, or offers to make the edited part a local component of the piece.

**Postconditions:** The content and the piece's local components hold each edit that had exactly one field to go to. The developer knows each other edit.

**Minimal guarantees:**

- The system never writes an edit into a library. It never writes an edit that has no field of its own, or one that conflicts with an edit in the content.

## Open for the design

What the developer needs here that no accepted record decides yet:

- **Edits to a final piece.** Whether the system refuses to take them back, or first copies the piece as a draft with its lock pinned. The architect, reviewing the capability's design on 31 October, asked for one of the two (#2423).

## Sources

- **The goal:** the maintainer asked for it on 30 October, in planning the capability (#2423). It rests on an edit made where a piece is drawn, which changes the source only once taken back and reviewed ([DEC-001 point 2](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#2-the-logical-layer-is-the-source-and-renderers-only-project-it)).
- **The steps and the guarantees, in part:**
  - **Steps 2 to 4:** every part the engine draws traces back to the library or local component that drew it, and to the content field it shows. An edit that cannot be placed is reported ([DEC-001 point 3](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#3-a-piece-and-its-content)).
  - **Step 2:** an edit is found by comparing the medium with the renderer's committed record of what it last drew ([DEC-005 point 11](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-005-engine-and-plugins.md#11-a-renderer-that-draws-into-a-lasting-medium-commits-a-record-of-what-it-last-drew)).
  - **Step 5:** an edit is taken back as a change a person reviews ([DEC-001 point 2](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#2-the-logical-layer-is-the-source-and-renderers-only-project-it)).
  - **The first guarantee:** the system writes no edit into a library, since a library copy that a lock names is never rewritten ([DEC-001 point 11](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#11-shipped-with-the-methodology-and-a-projects-work-stays-the-projects)).
- **Left to a later slice:** how the system takes edits back. It writes each exact match, stops on a conflict and lists the rest, as the maintainer decided on 30 October (#2423). The founding record leaves taking edits back to later records ([DEC-001](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md), Implications), and a later slice of EPIC #2423 decides it. So the steps, the variants and the guarantees take their form from that slice.
