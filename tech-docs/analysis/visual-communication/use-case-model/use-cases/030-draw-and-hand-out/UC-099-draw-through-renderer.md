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
  - [UC-093, UC-094, UC-095, UC-104]
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

**Preconditions:** **From [UC-093](../010-make/UC-093-build-presentation.md), [UC-094](../010-make/UC-094-put-figure-in-page.md), [UC-095](../010-make/UC-095-draw-views-of-system.md), or [UC-104](../020-build-libraries/UC-104-add-kind-of-piece.md):** The piece exists.

**Assumptions:**

- The project has visual-communication installed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).
- A renderer that draws on a service reaches it only where the project's permission model lets it ([COR-028](../../../../../../.pkit/decisions/core/COR-028-permission-model-realization.md)).

**Trigger:** The piece must be shown somewhere else, such as on an online board for a workshop, or as a page in a browser.

**Main path:**

1. The developer names the renderer the piece is drawn through.
2. The system draws the same content, with the same layouts, through that renderer. It measures each text in the fonts the brand sets for that renderer.
3. The system says which texts do not fit in those fonts. It also says what the renderer could not draw as the piece asks, and how it drew it instead.
4. The developer opens what the renderer drew.

**Variants:**

- **2a.** The renderer draws on a service, such as an online board, and the operator has signed in to it. The system draws there, and keeps a record of what it drew, so another clone of the project updates the same board.
- **2b.** The operator has not signed in to the service. The system says so and draws nothing, and the use case ends.
- **2c.** The service fails a request after it made an object. The system tries again, and leaves no second copy of the object.
- **2d.** The renderer lacks a font a text needs, such as a board with no monospace font. The system draws the text in the font the brand sets for it instead, or as a picture.

**Postconditions:** The piece is drawn through the renderer, with the same content and layouts, and the developer knows each difference.

**Minimal guarantees:**

- A request the service fails leaves no second copy of an object.

## Open for the design

What the operator needs here that no accepted record decides yet:

- **How the operator signs in to a service.** Feature #2418 plans one sign-in for each service, kept for each person outside every repository. The core is to decide it, under #2418 and #2419.

## Sources

- **The goal:** drawn on 30 October, in planning the capability (#2423), from what the capability is for. The maintainer asked then whether drawing on a board will still matter: "who needs the Mural at the end".
- **The steps and the guarantee:** the capability's shared choices (#2424) on the scene, and on renderers as plugins that report what they could not draw. Steps 2 and 3 also follow the shared choices on font profiles, on text measured from committed fonts and on the layout operators.
- **Not among the shared choices:** the renderer's record of what it drew, and a retry that first finds what a failed request made. They are the maintainer's decisions of 31 October, made in planning the capability (#2423). The sign-in is planned under Feature #2418.
- **No accepted record decides them yet.** The capability's records, written under #2427, will decide them. The use case then anchors each record, and its steps follow them.
