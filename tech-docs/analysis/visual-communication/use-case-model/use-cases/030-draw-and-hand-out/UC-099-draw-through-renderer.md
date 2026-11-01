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
        - visual-communication:DEC-001#1
        - visual-communication:DEC-001#2
        - visual-communication:DEC-002#2
        - visual-communication:DEC-002#8
        - visual-communication:DEC-004#9
        - visual-communication:DEC-005#4
        - visual-communication:DEC-005#9
        - visual-communication:DEC-005#10
        - visual-communication:DEC-005#11
        - visual-communication:DEC-005#14
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
- **2e.** The renderer reaches a service that the project has not turned on in its configuration. The system says so and draws nothing, and the use case ends.

**Postconditions:** The piece is drawn through the renderer, with the same content and layouts, and the developer knows each difference.

**Minimal guarantees:**

- A request the service fails leaves no second copy of an object.

## Open for the design

What the operator needs here that no accepted record decides yet:

- **How the operator signs in to a service.** A renderer that reaches a service signs in through the methodology's shared sign-in, decided apart ([DEC-002 point 8](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-002-files-and-validation.md#8-python-run-as-the-methodologys-own-code-and-no-network-to-draw)). Feature #2418 plans one sign-in for each service, kept for each person outside every repository. The core is to decide it, under #2418 and #2419.

## Sources

- **The goal:** drawn on 30 October, in planning the capability (#2423), from what the capability is for. The maintainer asked then whether drawing on a board will still matter: "who needs the Mural at the end". The goal rests on one piece drawn by several renderers, each within what its medium can draw ([DEC-001 point 1](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#1-what-the-capability-is-for)).
- **The steps:**
  - **Steps 1 to 3:** a renderer draws what the engine computed, and adds no design of its own. It reports what it could not draw, in one form of report ([DEC-001 point 2](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#2-the-logical-layer-is-the-source-and-renderers-only-project-it) and [DEC-005 point 9](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-005-engine-and-plugins.md#9-three-kinds-of-plugin-share-one-pattern-and-one-loss-report)).
  - **Step 2 and variant 2d:** a renderer names the font profile it draws in, and the engine measures each text by that profile (DEC-005 points [4](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-005-engine-and-plugins.md#4-the-engine-measures-text-from-committed-fonts-and-breaks-its-lines) and [10](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-005-engine-and-plugins.md#10-a-renderer-names-its-font-profile-with-a-default)). A profile may measure a font the medium holds itself by a table of widths ([DEC-004 point 9](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-004-brands-and-notations.md#9-fonts-come-from-committed-files-and-a-missing-font-refuses-the-render)).
  - **Step 3:** a text that overflows its box fails where it was measured from a font file, and asks for attention otherwise ([DEC-005 point 14](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-005-engine-and-plugins.md#14-what-the-checks-report-and-how-severely)).
  - **Variant 2a:** a renderer that draws into a lasting medium commits a record of what it last drew. Any clone's next drawing then updates it in place ([DEC-005 point 11](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-005-engine-and-plugins.md#11-a-renderer-that-draws-into-a-lasting-medium-commits-a-record-of-what-it-last-drew)).
  - **Variants 2b and 2e:** a plugin that reaches a service runs only where the project's configuration turns it on. It signs in through the methodology's shared sign-in (DEC-002 points [2](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-002-files-and-validation.md#2-the-configuration-holds-only-the-projects-choices-as-a-whole) and [8](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-002-files-and-validation.md#8-python-run-as-the-methodologys-own-code-and-no-network-to-draw)).
- **Left to a later slice:** variant 2c's retry, and the guarantee that a failed request leaves no second copy. The maintainer decided on 31 October that a retry first finds what a failed request made (#2423). A later slice of EPIC #2423 decides it, with the renderer for a whiteboard service ([DEC-005](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-005-engine-and-plugins.md), Implications). The sign-in is planned under Feature #2418.
