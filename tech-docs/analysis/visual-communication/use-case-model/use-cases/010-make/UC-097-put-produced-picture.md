---
id: UC-097
title: Put a picture that a program makes in a piece
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
requirements: []
after:
  - [UC-093, UC-094, UC-095, UC-104]
pkit:
  friction:
    anchors:
      record:
        - visual-communication:DEC-001#8
        - visual-communication:DEC-002#8
        - visual-communication:DEC-004#3
        - visual-communication:DEC-005#7
        - visual-communication:DEC-006#1
        - visual-communication:DEC-006#2
        - visual-communication:DEC-006#3
        - visual-communication:DEC-006#4
        - visual-communication:DEC-006#5
        - COR-017
        - COR-013
---

# UC-097 — Put a picture that a program makes in a piece

**Goal:** Put a picture that a program makes, such as a 3D render, in any piece, in the colours of its brand.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): does the work for the developer, and may run any step the developer runs.

**Preconditions:** **From [UC-093](UC-093-build-presentation.md), [UC-094](UC-094-put-figure-in-page.md), [UC-095](UC-095-draw-views-of-system.md), or [UC-104](../020-build-libraries/UC-104-add-kind-of-piece.md):** The piece the picture goes in exists.

**Assumptions:**

- The project has visual-communication installed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).

**Trigger:** A piece needs a picture that no library component can draw, such as the board of a game, drawn in 3D.

**Main path:**

1. The developer describes what the program draws, such as the shapes of a game board. Each colour is taken from a name the brand gives a value to, never from a fixed value.
2. The developer runs the program while the piece is prepared. The system gives the program the brand's values and a pixel size fixed before it runs, and the program makes the picture at that size.
3. The program marks the spots where labels go, and the developer writes each label in the piece's content.
4. The system puts the picture in the piece, with each label at its spot, measured and translated like any text of the piece.
5. The developer commits the picture with the piece.

**Variants:**

- **2a.** The program is not on the machine. The system names it and makes nothing, and the use case ends.
- **2b.** The brand gives other values in another mode, such as dark. The program makes one picture for each set of values it reads, and the piece shows the picture of the mode it is drawn in. A mode that alters the picture's size, such as one of a device, gives a picture of its own too.
- **4a.** An input of the picture changed since the picture was made, such as a value of the brand, or the program itself. The system says the picture is out of date, and the path rejoins at step 2.

**Postconditions:** The piece shows the picture in its brand's colours, in each mode, with its labels in each of the piece's languages.

**Minimal guarantees:**

- The system never runs the program while it draws a piece. It only puts in the picture made before.

## Sources

- **The goal:** the maintainer asked on 1 November for "some mechanism how to do 3d renders and include them into any visual". It was decided under his delegation, and he approved it with the plan of #2423 the same day. It rests on a program run while preparing, which may write a picture in the brand ([DEC-001 point 8](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#8-what-the-engine-cannot-compute-is-computed-while-preparing) and [DEC-006 point 1](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-006-work-outside-the-engine-and-outputs.md#1-a-program-run-while-preparing-may-write-a-picture)).
- **An example only:** the game platform the maintainer described. Nothing of a game is built.
- **The steps and the guarantee:**
  - **Step 1:** what is written for the picture names roles, never raw values ([DEC-006 point 2](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-006-work-outside-the-engine-and-outputs.md#2-a-picture-takes-its-values-from-the-brand-alone-and-holds-none-of-the-pieces-words)).
  - **Step 2 and the guarantee:** a person or an agent runs the program, never the engine. Commands of the capability frame the run, and hand the program the brand's resolved values ([DEC-006 point 1](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-006-work-outside-the-engine-and-outputs.md#1-a-program-run-while-preparing-may-write-a-picture) and [DEC-005 point 7](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-005-engine-and-plugins.md#7-the-engine-owns-one-document-of-a-brands-resolved-values)).
  - **Steps 3 and 4:** the picture holds none of the piece's words. The piece places each label at a point the picture exposes, as text of its own (DEC-006 point 2).
  - **Step 5:** what a program makes lies in the folder of the piece that uses it, and is committed ([DEC-006 point 4](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-006-work-outside-the-engine-and-outputs.md#4-where-produced-output-and-written-code-live)).
  - **Variant 2a:** a command that needs an outside program checks for it, and names what is missing ([DEC-002 point 8](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-002-files-and-validation.md#8-python-run-as-the-methodologys-own-code-and-no-network-to-draw)).
  - **Variant 2b, and the size in step 2:** a picture is made once for each set of values it reads, at a pixel size fixed before the program runs. Each is named by the brand's key ([DEC-006 point 3](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-006-work-outside-the-engine-and-outputs.md#3-one-picture-for-each-set-of-values-it-reads-at-a-fixed-pixel-size) and [DEC-004 point 3](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-004-brands-and-notations.md#3-one-key-names-a-combination-of-modes)).
  - **Variant 4a:** a fingerprint of what the program read says when the picture is stale ([DEC-006 point 5](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-006-work-outside-the-engine-and-outputs.md#5-a-fingerprint-says-when-output-is-stale-and-the-rest-is-only-recorded)).
- **Left to a later slice:** the form in which step 1 describes a 3D scene. The change that builds the first real producer decides it, a later slice of EPIC #2423 ([DEC-006](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-006-work-outside-the-engine-and-outputs.md), Implications).
