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
4. The system lists each other edit, and writes nothing for it. Examples are a colour picked by hand, a box moved where the layout sets its position, and an edit to what a library draws.
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

- **Edits to a delivered piece.** Whether the system refuses to take them back, or first copies the piece as an adapted one. The architect's review in the planning note asks for one of the two.

## Sources

- **The goal:** use case 5 of the planning note `2026-10-30-visual-work-capability`, which the maintainer asked for on 30 October, in its point 3.
- **The steps and the guarantees:** the decisions the note records in its points 3, 4h and 4i. Point 4h says the system writes only to the content and to the piece's own local components.
- **No accepted record decides them yet.** The capability's records, written under #2427, will decide them. The use case then anchors each record, and its steps follow them.
