---
id: UC-097
title: Put a picture that a program makes in a piece
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
requirements: []
after:
  - [UC-093, UC-094]
pkit:
  friction:
    anchors:
      record:
        - COR-017
        - COR-013
---

# UC-097 — Put a picture that a program makes in a piece

**Goal:** Put a picture that a program makes, such as a 3D render, in any piece, in the colours of its brand.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): does the work for the developer, and may run any step the developer runs.

**Preconditions:** **From [UC-093](UC-093-build-presentation.md), or [UC-094](UC-094-put-figure-in-page.md):** The piece the picture goes in exists.

**Assumptions:**

- The project has visual-communication installed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).

**Trigger:** A piece needs a picture that no library component can draw, such as the board of a game, drawn in 3D.

**Main path:**

1. The developer describes what the program draws, such as its models, its camera and its lights. Each colour is named by the value the brand gives it, never written as a fixed value.
2. The developer has the program run while the piece is prepared. The system gives the program the brand's values, and the program makes the picture.
3. The program marks the spots where labels go, and the developer writes each label in the piece's content.
4. The system puts the picture in the piece, with each label at its spot, measured and translated like any text of the piece.
5. The developer commits the picture with the piece.

**Variants:**

- **2a.** The program is not on the machine. The system names it and makes nothing, and the use case ends.
- **2b.** The brand gives other values in another mode, such as dark. The program makes one picture for each set of values it reads, and the piece shows the picture of the mode it is drawn in.
- **4a.** An input of the picture was edited since the picture was made, such as a value of the brand or the program's version. The system says the picture is out of date, and the path rejoins at step 2.

**Postconditions:** The piece shows the picture in its brand's colours, in each mode, with its labels in each of the piece's languages.

**Minimal guarantees:**

- The system never runs the program while it draws a piece. It only puts in the picture made before.

## Sources

- **The goal:** point 29 of the planning note `2026-10-30-visual-work-capability`. On 1 November the maintainer asked for "some mechanism how to do 3d renders and include them into any visual". It was decided under his delegation, and he approved it with the plan of #2423 the same day.
- **An example only:** the game platform the maintainer described. Nothing of a game is built.
- **The steps and the guarantee:** the decisions the note records in its points 21 and 29.
- **No accepted record decides them yet.** The capability's records, written under #2427, will decide them. The use case then anchors each record, and its steps follow them.
