---
id: UC-093
title: Build a presentation from library components
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
requirements: []
pkit:
  friction:
    anchors:
      record:
        - COR-017
        - COR-013
---

# UC-093 — Build a presentation from library components

**Goal:** Build a presentation from library components that exist, filled with my own content, so nothing made once is made again.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): does the work for the developer, and may run any step the developer runs.

**Preconditions:** None.

**Assumptions:**

- The project has visual-communication installed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).
- The capability ships a starter library of library components, and a neutral brand. So a presentation can be drawn before the project has a library of its own ("Sources", below).

**Trigger:** The developer has a talk to give, such as a talk that shows the project to its users.

**Main path:**

1. The developer starts a piece for the presentation. The developer names the brand that draws it, and the notation of the subject it is about.
2. The developer writes the presentation's content: its title, and for each slide the layout it takes and what fills each slot of that layout.
3. For each slide's picture, the developer chooses a library component that does its job, such as one that shows layers or one that shows steps. The developer fills it with the slide's own content.
4. The system draws the presentation in the brand, with the library components the content names.
5. The system says which texts do not fit where they go, and which library components are still experimental.
6. The developer has the drawn presentation read as its audience would read it, and mends the content where the reading asks.

**Variants:**

- **1a.** The presentation is about several subjects, such as two projects. The developer names the notation of each. Where two notations name one concept differently, the system says so, and the developer settles the name for this piece.
- **1b.** The developer starts from a delivered presentation, to give it to a new audience. The system copies it as an adapted piece. The copy keeps the delivered look until the developer moves it to newer versions of its libraries ([UC-103](../030-build-libraries/UC-103-improve-library-component.md)). The path goes on at step 2.
- **3a.** No library component fits a slide's picture. The developer makes a local component for it, inside this piece ([UC-096](UC-096-add-visual-as-data.md)). The path goes on at step 4.
- **4a.** The content does not fit what a library component declares, such as a field the library component does not have. The system names each fault and draws nothing. The developer mends the content, and the path rejoins at step 4.
- **5a.** A text does not fit. The developer shortens it, or chooses another option the library component declares, and the path rejoins at step 4.
- **5b.** A library component is experimental. The system still draws it, and says only that it may be altered in any version of its library.

**Postconditions:** The presentation is drawn in the brand it names, from library components filled with its own content.

**Minimal guarantees:**

- An experimental library component is drawn with a note, and never refused.

## Sources

- **The goal:** use case 1 of the planning note `2026-10-30-visual-work-capability`, which the maintainer asked for on 30 October. Variant 1a takes in the note's use case 12, "Work about several subjects, under any brand", proposed on 31 October.
- **The steps and the guarantee:** the decisions the note records in its points 4b, 4c, 4d, 4f, 4g, 8 and 9, and in its naming pass.
- **No accepted record decides them yet.** The capability's records, written under #2427, will decide them. The use case then anchors each record, and its steps follow them.
