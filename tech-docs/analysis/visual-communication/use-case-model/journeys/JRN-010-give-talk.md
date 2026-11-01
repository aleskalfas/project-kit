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

- **The goal:** the path the Friday talk took, as the planning note `2026-10-30-visual-work-capability` tells it. The talk was built from data, and given in English and in Czech. It was drawn on a board the maintainer edited, and handed out as one PDF for each language.
- **No accepted record decides the steps yet.** The capability's records, written under #2427, will decide them. The journey then anchors each record, and its hand-overs follow them.
