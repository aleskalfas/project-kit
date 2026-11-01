---
id: UC-098
title: Give a piece another brand or another mode
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
requirements: []
after:
  - [UC-093, UC-094, UC-095, UC-104]
  - [UC-105, UC-106, UC-109]
pkit:
  friction:
    anchors:
      record:
        - visual-communication:DEC-001#3
        - visual-communication:DEC-001#5
        - visual-communication:DEC-004#2
        - visual-communication:DEC-005#4
        - visual-communication:DEC-005#6
        - COR-017
        - COR-013
---

# UC-098 — Give a piece another brand or another mode

**Goal:** Give a piece another brand or another mode, and see its look change while its content stays the same.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): does the work for the developer, and may run any step the developer runs.

**Preconditions:**

- **From [UC-093](../010-make/UC-093-build-presentation.md), [UC-094](../010-make/UC-094-put-figure-in-page.md), [UC-095](../010-make/UC-095-draw-views-of-system.md), or [UC-104](../020-build-libraries/UC-104-add-kind-of-piece.md):** The piece exists, drawn in one brand.
- **From [UC-105](../020-build-libraries/UC-105-make-brand.md), [UC-106](../020-build-libraries/UC-106-build-brand-on-brand.md), or [UC-109](../020-build-libraries/UC-109-take-in-shared-library.md):** The other brand is in the project.

**Assumptions:**

- The project has visual-communication installed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).

**Trigger:** The piece must be shown in another look, such as a talk about the developer's own project, given in a client's brand.

**Main path:**

1. The developer names another brand for the piece.
2. The system draws the piece in the new brand: its colours, fonts, sizes and layouts. The content, the library components and the notations stay as they were.
3. The system names each layout or library component the piece uses that the new brand lacks.
4. The developer compares the piece in the two brands, and keeps the new one.

**Variants:**

- **1a.** The developer names another mode of the same brand, on one of its axes, such as dark on the colour scheme. A warm palette beside a calm one of the same brand is a mode too. The system draws the piece with that mode's values, and the use case ends.
- **1b.** The mode lies on an axis whose modes alter sizes, such as a device. The system lays the piece out again for that mode, and says which texts do not fit. The use case ends.
- **1c.** The developer names several modes on one axis, such as light and dark. The system draws and checks the piece in each combination of the modes it names, and its exports hold each. An axis the piece names no mode for takes its default mode. The use case ends.
- **3a.** The piece holds a picture made outside the system, such as a photo. It does not follow the brand, so the system names it.
- **3b.** The new brand lacks what the piece uses. The developer chooses another layout or library component the new brand has, or keeps the earlier brand, and the use case ends.

**Postconditions:** The piece is drawn in the new brand or mode, from the same content.

**Minimal guarantees:**

- Giving a piece another brand or mode alters none of its content.

## Sources

- **The goal:** drawn on 30 October, in planning the capability (#2423), from the maintainer's choice of where a piece's layout and look live. It also takes in a piece drawn under any brand, proposed on 31 October. It takes in the piece's side of modes on several axes too, added on 1 November. The goal rests on switching the brand, which changes how a piece looks and leaves its content as it is ([DEC-001 point 5](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#5-libraries-hold-values-structure-or-meaning)).
- **The steps and the guarantee:**
  - **Steps 1 to 3 and the guarantee:** switching the brand changes how a piece looks, and leaves its content and its library components as they are. What the new brand lacks is reported ([DEC-001 point 5](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#5-libraries-hold-values-structure-or-meaning)).
  - **Variants 1a and 1c:** a piece names the modes it is drawn in, on each axis of its brand ([DEC-005 point 6](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-005-engine-and-plugins.md#6-a-piece-names-the-modes-it-is-drawn-in)). Looks of one owner that share every layout are modes of one axis, not brands ([DEC-004 point 2](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-004-brands-and-notations.md#2-modes-lie-on-axes-and-each-axis-changes-values-or-sizes)).
  - **Variant 1b:** an axis whose modes alter sizes needs a drawing for each mode. Each text is measured in it (DEC-004 point 2 and [DEC-005 point 4](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-005-engine-and-plugins.md#4-the-engine-measures-text-from-committed-fonts-and-breaks-its-lines)).
  - **Variant 3a:** a picture made elsewhere is content that follows no brand, and switching the brand reports it ([DEC-001 point 3](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#3-a-piece-and-its-content)).
