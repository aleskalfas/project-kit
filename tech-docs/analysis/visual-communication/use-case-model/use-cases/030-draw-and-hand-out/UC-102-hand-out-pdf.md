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

1. The developer asks for the piece as a PDF.
2. The system writes one PDF for each language of the piece. It holds a page for each page of the piece, such as each slide, in order.
3. The system gives this export a new number, one number for all its languages. It records the export's date, the piece's state then, and the library versions it used.
4. The developer hands out the PDF of each language.

**Variants:**

- **2a.** The piece is also drawn on a board. The system still writes the PDF from the piece itself, never from the board.
- **2b.** A program the system writes PDFs with is not on the machine. The system names it and writes nothing, and the use case ends.
- **2c.** The developer asks for a PDF that screen readers follow. The system writes it with headings, a reading order and a text for each picture.
- **4a.** The piece has done its job, such as a talk that was given, and the developer marks it final. This export is kept with the piece as the one handed out. From then on, no new library version alters the piece's look.

**Postconditions:** The developer holds a PDF for each language, all under one export number, and knows what each export holds.

**Minimal guarantees:**

- An export never overwrites an earlier one.

## Sources

- **The goal:** drawn in planning the capability (#2423), from the Friday talk. That talk needed a script of its own to cut a board's export into one PDF for each language.
- **The steps and the guarantee:** the capability's shared choices (#2424) on outputs and their versions, and on outside programs, which the capability checks for. The maintainer asked on 31 October that every export be kept and numbered.
- **Not among the shared choices:** the final state of variant 4a, in which the piece keeps the export that was handed out. It rests on the maintainer's decisions of 30 and 31 October, made in planning the capability (#2423).
- **No accepted record decides them yet.** The capability's records, written under #2427, will decide them. The use case then anchors each record, and its steps follow them.
