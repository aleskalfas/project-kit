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
2. The system finds each edit, and traces it to the field of the content, or the library, that the edited object came from.
3. The system writes each edit that has exactly one field to go to into that field, such as a title into its slide's title.
4. The system lists each edit that has no such field, and writes nothing for it. Examples are a colour picked by hand, and a box moved where the layout sets its position.
5. The developer reads what the system wrote as a diff, and commits it or reverts it.
6. For each listed edit, the developer makes it an option of the piece, alters the brand or a library, or drops it.

**Variants:**

- **2a.** A field was edited both where the piece is drawn and in the content since the last drawing. The system writes neither edit, and lists the conflict.
- **3a.** The edit belongs to a library the project took from another repository. The system writes nothing into that library. It lists the edit with the repository the library comes from, or offers to make it a local component of the piece.

**Postconditions:** The content holds each edit that had exactly one field to go to, and the developer knows each other edit.

**Minimal guarantees:**

- The system never writes an edit that has no field of its own, or one that conflicts with an edit in the content.

## Sources

- **The goal:** use case 5 of the planning note `2026-10-30-visual-work-capability`, which the maintainer asked for on 30 October, in its point 3.
- **The steps and the guarantee:** the decisions the note records in its points 3 and 4i.
- **Left open:** what the system does with an edit to a delivered piece. The note's architect's review asks that it refuse, or first copy the piece as an adapted one, and nothing decides it yet.
- **No accepted record decides them yet.** The capability's records, written under #2427, will decide them. The use case then anchors each record, and its steps follow them.
