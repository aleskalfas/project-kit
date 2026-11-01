---
id: UC-099
title: Draw a piece through another renderer
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
  - core:ACT-operator
requirements: []
after:
  - [UC-093, UC-094]
pkit:
  friction:
    anchors:
      record:
        - COR-017
        - COR-013
        - COR-028
---

# UC-099 — Draw a piece through another renderer

**Goal:** Draw a piece through another renderer, such as a web page instead of a board, and learn what that renderer could not draw.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): does the work for the developer, and may run any step the developer runs.
- **Operator** (`core:ACT-operator`): signs in once to each service a renderer draws on, outside every repository. No agent reads that sign-in.

**Preconditions:** **From [UC-093](../010-make/UC-093-build-presentation.md), or [UC-094](../010-make/UC-094-put-figure-in-page.md):** The piece exists.

**Assumptions:**

- The project has visual-communication installed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).
- A renderer that draws on a service reaches it only where the project's permission model lets it ([COR-028](../../../../../../.pkit/decisions/core/COR-028-permission-model-realization.md)).

**Trigger:** The piece must be shown somewhere else, such as on an online board for a workshop, or as a page in a browser.

**Main path:**

1. The developer names the renderer the piece is drawn through.
2. The system draws the same piece through that renderer. Every renderer gets the same positions and sizes, and the fonts each text was measured with.
3. The system says what the renderer could not draw as the piece asks, and how it drew it instead. An example is a text in a font the renderer lacks, drawn as a picture.
4. The developer opens what the renderer drew.

**Variants:**

- **2a.** The renderer draws on a service, such as an online board, and the operator has signed in to it. The system draws there, and keeps a record of what it drew, so another clone of the project updates the same board.
- **2b.** The operator has not signed in to the service. The system says so and draws nothing, and the use case ends.
- **2c.** The service fails a request after it made an object. Before the system tries again, it finds that object, so no second copy is left behind.
- **2d.** The renderer offers fewer fonts, such as a board with no monospace font. The system lays the piece out again in the fonts that renderer has, so each text still fits.

**Postconditions:** The piece is drawn through the renderer, with the same content and look, and the developer knows each difference.

**Minimal guarantees:**

- A request the service fails leaves no second copy of an object.

## Sources

- **The goal:** use case 4 of the planning note `2026-10-30-visual-work-capability`, drawn on 30 October from its point 1. There the maintainer asked whether drawing on a board will still matter: "who needs the Mural at the end".
- **The steps and the guarantee:** the decisions the note records in its points 1, 2, 5, 12, 14, 18c and 18d.
- **No accepted record decides them yet.** The capability's records, written under #2427, will decide them. The use case then anchors each record, and its steps follow them.
