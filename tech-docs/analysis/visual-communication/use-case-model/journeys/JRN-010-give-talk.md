---
id: JRN-010
title: Give a talk in two languages and hand out its slides
status: active
actor: core:ACT-developer
steps:
  - UC-093
  - UC-101
  - UC-099
  - UC-100
  - UC-102
relies-on: []
requirements: []
pkit:
  friction:
    anchors:
      record:
        - visual-communication:DEC-001#3
        - visual-communication:DEC-005#4
        - visual-communication:DEC-005#10
        - visual-communication:DEC-005#11
        - visual-communication:DEC-006#7
        - COR-017
        - COR-013
      artefact:
        - UC-093
        - UC-101
        - UC-099
        - UC-100
        - UC-102
---

# JRN-010 — Give a talk in two languages and hand out its slides

**Goal:** Give my talk in two languages from one presentation, and hand out its slides in each language.

**Steps:**

1. [UC-093](../use-cases/010-make/UC-093-build-presentation.md) — Build a presentation from library components
2. [UC-101](../use-cases/030-draw-and-hand-out/UC-101-give-second-language.md) — Give a piece in a second language
   - **Needs from step 1 (UC-093):** the presentation, its content written in the source language. A source page edited after it was translated is flagged in each translation (UC-101, variant 6b).
3. [UC-099](../use-cases/030-draw-and-hand-out/UC-099-draw-through-renderer.md) — Draw a piece through another renderer
   - **Needs from step 2 (UC-101):** the presentation in both languages. A text that fits in one language may not fit in the other in the board's fonts, and the system says so (UC-099, step 3).
4. [UC-100](../use-cases/030-draw-and-hand-out/UC-100-take-back-edits.md) — Take back what people changed where a piece is drawn
   - **Needs from step 3 (UC-099):** the presentation drawn on a board people can edit. Where a field was edited both on the board and in the content since then, the system writes neither edit (UC-100, variant 2a).
5. [UC-102](../use-cases/030-draw-and-hand-out/UC-102-hand-out-pdf.md) — Hand out a piece as a PDF for each language
   - **Needs from step 4 (UC-100):** the content, with the edits made on the board taken back. An edit left on the board is missing from the PDF, which the system writes from the content, never from the board (UC-102, variant 2a).

**Variants:**

- **1a.** The talk is given in one language only. The path goes on at step 3.
- **2a.** The talk is shown from a web page or from its PDF, never on a board. The path goes on at step 5.
- **3a.** Nobody edited the board. The path goes on at step 5.

**Postconditions:** The developer gave the talk in both languages from one presentation, and holds a PDF of it for each language, under one export number.

**Minimal guarantees:** None.

## Sources

- **The goal:** the path the Friday talk took, project-kit's own talk of 30 October. The talk was built from data, and given in English and in Czech. It was drawn on a board the maintainer edited, and handed out as one PDF for each language. Drawn with the capability, it is to become the showcase deck on the default branch (#2423).
- **The hand-overs:**
  - **Step 2:** a second language is a second content of the same shape, with the same ids ([DEC-001 point 3](../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#3-a-piece-and-its-content)).
  - **Step 3:** each text is measured in its own language, by the font profile the renderer draws in (DEC-005 points [4](../../../../../.pkit/capabilities/visual-communication/decisions/DEC-005-engine-and-plugins.md#4-the-engine-measures-text-from-committed-fonts-and-breaks-its-lines) and [10](../../../../../.pkit/capabilities/visual-communication/decisions/DEC-005-engine-and-plugins.md#10-a-renderer-names-its-font-profile-with-a-default)).
  - **Step 4:** the renderer commits a record of what it last drew on the board, against which the edits are found ([DEC-005 point 11](../../../../../.pkit/capabilities/visual-communication/decisions/DEC-005-engine-and-plugins.md#11-a-renderer-that-draws-into-a-lasting-medium-commits-a-record-of-what-it-last-drew)).
  - **Step 5:** an export is drawn from the piece, never fetched from a board ([DEC-006 point 7](../../../../../.pkit/capabilities/visual-communication/decisions/DEC-006-work-outside-the-engine-and-outputs.md#7-every-export-keeps-its-number)).
- **Left to a later slice:** the flags on a translation in step 2's hand-over, and taking edits back in step 4's. The founding record leaves translation and taking edits back to later records ([DEC-001](../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md), Implications), and a later slice of EPIC #2423 decides both.
