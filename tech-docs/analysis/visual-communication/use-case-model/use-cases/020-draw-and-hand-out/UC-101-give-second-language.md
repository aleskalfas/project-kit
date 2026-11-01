---
id: UC-101
title: Give a piece in a second language
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

# UC-101 — Give a piece in a second language

**Goal:** Give a piece in a second language, from content of the same structure, and learn which pages to translate again when the source changes.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): translates each page for the developer, and returns the text with notes on its length. It never accepts its own translation.

**Preconditions:** **From [UC-093](../010-make/UC-093-build-presentation.md), or [UC-094](../010-make/UC-094-put-figure-in-page.md):** The piece exists in its source language.

**Assumptions:**

- The project has visual-communication installed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).

**Trigger:** The piece must reach people who read another language, such as a talk given in Czech as well as in English.

**Main path:**

1. The developer adds a language to the piece.
2. The system adds content for that language, with the same structure as the source language's content, page by page, such as slide by slide.
3. The AI agent translates each page from its meaning, never word for word. It uses the words that the piece's notations, its brand and the piece itself fix for that language.
4. A person who speaks the language natively reads each translated page, and accepts it, rewords it or refuses it.
5. The system draws the piece in each language, with the same library components, and measures each text in its own language.
6. The system says which texts do not fit, in which language.

**Variants:**

- **3a.** A text uses a word that a notation says never to use in that language, such as "add-on" where the notation says "capability". The system names each spot, and the translation takes the notation's word.
- **3b.** Two notations give one concept different words in the language. The system says so, and the developer settles the word for this piece.
- **6a.** A text does not fit. The developer or the AI agent shortens it in that language, and the path rejoins at step 5.
- **6b.** Later, a page of the source language is edited. The system flags that page in each translation. The AI agent proposes the new translation, and the person accepts, rewords or refuses it, as in step 4.

**Postconditions:** The piece exists in each of its languages, with the same structure and look. Each translated page matches its source page.

**Minimal guarantees:**

- An edited source page never leaves its translations out of date without a sign.

## Sources

- **The goal:** use case 7 of the planning note `2026-10-30-visual-work-capability`, from the Czech version of the Friday talk.
- **The steps and the guarantee:** the decisions the note records in its points 9 and 13, with what the Czech version taught. Variant 6b also waits on #2416, so that content can carry what it rests on.
- **No accepted record decides them yet.** The capability's records, written under #2427, will decide them. The use case then anchors each record, and its steps follow them.
