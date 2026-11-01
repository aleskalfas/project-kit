---
id: UC-102
title: Hand out a piece as a PDF for each language
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
        - visual-communication:DEC-001#3
        - visual-communication:DEC-002#8
        - visual-communication:DEC-003#8
        - visual-communication:DEC-005#5
        - visual-communication:DEC-006#7
        - COR-017
        - COR-013
---

# UC-102 — Hand out a piece as a PDF for each language

**Goal:** Hand out a piece as a PDF, one for each language, with the piece's pages in order, such as its slides.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): does the work for the developer, and may run any step the developer runs.

**Preconditions:** **From [UC-093](../010-make/UC-093-build-presentation.md), [UC-094](../010-make/UC-094-put-figure-in-page.md), [UC-095](../010-make/UC-095-draw-views-of-system.md), or [UC-104](../020-build-libraries/UC-104-add-kind-of-piece.md):** The piece exists.

**Assumptions:**

- The project has visual-communication installed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).

**Trigger:** The audience asks for the slides, such as after a talk.

**Main path:**

1. The developer asks for the piece's exports. The piece names a PDF among the files it is handed out as.
2. The system writes one PDF for each language of the piece. It holds a page for each page of the piece, such as each slide, in order.
3. The system gives the exports of this run a new number, one number for all its languages. It records when the run was made and the piece's state then. It also records the library versions the run used.
4. The developer hands out the PDF of each language.

**Variants:**

- **2a.** The piece is also drawn on a board. The system still writes the PDF from the piece itself, never from the board.
- **2b.** A program the system writes PDFs with is not on the machine. The system names it and writes nothing, and the use case ends.
- **2c.** A reader of the PDF uses a screen reader. The PDF holds headings, a reading order and a text for each picture, so the screen reader follows it.
- **4a.** The piece has done its job, such as a talk that was given. The developer marks it final, and names the exports of this run as those handed out. They are kept with the piece, and from then on no new library version alters the piece's look.

**Postconditions:** The developer holds a PDF for each language, all under one export number, and knows what each export holds.

**Minimal guarantees:**

- An export never overwrites an earlier one.

## Sources

- **The goal:** drawn in planning the capability (#2423), from the Friday talk. That talk needed a script of its own to cut what a board exported into one PDF for each language. The goal rests on every export keeping its number ([DEC-006 point 7](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-006-work-outside-the-engine-and-outputs.md#7-every-export-keeps-its-number)).
- **The steps and the guarantee:**
  - **Steps 1 to 3 and the guarantee:** a piece declares the files it is handed out as. An export run makes each, in each language, under one number, and no export overwrites another ([DEC-001 point 3](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#3-a-piece-and-its-content) and [DEC-006 point 7](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-006-work-outside-the-engine-and-outputs.md#7-every-export-keeps-its-number)). The maintainer asked on 31 October that every export be kept and numbered.
  - **Step 2 and variant 2c:** a content slot of the piece's kind says that its items are pages. A PDF gets a text for each picture, a reading order and structure such as headings ([DEC-005 point 5](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-005-engine-and-plugins.md#5-the-scene-holds-every-elements-final-frame-values-and-source)).
  - **Variant 2a:** an export is drawn from the piece, never fetched from a board (DEC-006 point 7).
  - **Variant 2b:** a command that needs an outside program checks for it, and names what is missing ([DEC-002 point 8](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-002-files-and-validation.md#8-python-run-as-the-methodologys-own-code-and-no-network-to-draw)).
  - **Variant 4a:** a person marks a piece final, and names which of its exports were handed out. The piece's folder keeps them as its freeze ([DEC-003 point 8](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#8-a-pieces-state-says-who-moves-its-lock) and DEC-006 point 7).
