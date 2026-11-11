---
id: UC-101
title: Give a piece in a second language
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
        - visual-communication:DEC-001#1
        - visual-communication:DEC-001#3
        - visual-communication:DEC-004#10
        - visual-communication:DEC-005#4
        - visual-communication:DEC-005#6
        - visual-communication:DEC-005#14
        - COR-017
        - COR-013
---

# UC-101 — Give a piece in a second language

**Goal:** Give a piece in a second language, from content of the same structure, and learn which pages to translate again when the source changes.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): translates each page for the developer, and returns the text with notes on its length. It never accepts its own translation.

**Preconditions:** **From [UC-093](../010-make/UC-093-build-presentation.md), [UC-094](../010-make/UC-094-put-figure-in-page.md), [UC-095](../010-make/UC-095-draw-views-of-system.md), or [UC-104](../020-build-libraries/UC-104-add-kind-of-piece.md):** The piece exists in its source language.

**Assumptions:**

- The project has visual-communication installed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).

**Trigger:** The piece must reach people who read another language, such as a talk given in Czech as well as in English.

**Main path:**

1. The developer adds a language to the piece.
2. The system adds content for that language, with the same structure as the source language's content, page by page, such as slide by slide.
3. The AI agent translates each page from its meaning, never word for word. It uses the words that the piece's notations, its brand and the piece itself fix for that language.
4. The developer reads each translated page, or asks a native speaker of the language to read it. The developer then accepts, rewords or refuses each page.
5. The system draws the piece in each language, with the same library components, and measures each text in its own language.
6. The system says which texts do not fit, in which language.

**Variants:**

- **3a.** A text uses a word that a notation says never to use in that language, such as "add-on" where the notation says "capability". The system names each spot, and the translation takes the notation's word.
- **3b.** Two notations give one concept different words in the language. The system says so, and the developer settles the word for this piece.
- **6a.** A text does not fit. The developer or the AI agent shortens it in that language, and the path rejoins at step 5.
- **6b.** Later, a page of the source language is edited. The system flags that page in each translation. The AI agent proposes the new translation, and the developer accepts, rewords or refuses it, as in step 4.

**Postconditions:** The piece exists in each of its languages, with the same structure and look. Each translated page matches its source page.

**Minimal guarantees:**

- An edited source page never leaves its translations out of date without a sign.

## Sources

- **The goal:** drawn in planning the capability (#2423), from the Friday talk, which was also translated into Czech. It rests on a second language being a second content of the same shape, with the same ids ([DEC-001 point 3](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#3-a-piece-and-its-content)).
- **The steps:**
  - **Steps 1 and 2:** a piece holds its content in each of its languages, and declares the language it is first written in ([DEC-001 point 3](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#3-a-piece-and-its-content)).
  - **Steps 5 and 6, and variant 6a:** each language gets a drawing of its own. The engine measures each text from committed fonts, breaks its lines by its language's rules, and never shrinks it. A text that overflows is reported (DEC-005 points [4](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-005-engine-and-plugins.md#4-the-engine-measures-text-from-committed-fonts-and-breaks-its-lines), [6](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-005-engine-and-plugins.md#6-a-piece-names-the-modes-it-is-drawn-in) and [14](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-005-engine-and-plugins.md#14-what-the-checks-report-and-how-severely)).
- **Left to a later slice:** steps 3 and 4, variants 3a, 3b and 6b, and the guarantee. A later slice of EPIC #2423 decides them.
  - **What they rest on:** the translator agent, the layered glossary and translations anchored to their source page by page. They are the maintainer's decisions of 31 October, with what translating the Friday talk into Czech taught (#2423).
  - **What the records leave:** the founding record leaves the agents and translation to later records ([DEC-001 point 1](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#1-what-the-capability-is-for), and Implications). The words a notation gives translators wait for translation too ([DEC-004 point 10](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-004-brands-and-notations.md#10-a-notation-maps-concepts-to-roles-read-with-its-name)).
  - **Variant 6b** also waits on #2416, so that content can carry what it rests on.
