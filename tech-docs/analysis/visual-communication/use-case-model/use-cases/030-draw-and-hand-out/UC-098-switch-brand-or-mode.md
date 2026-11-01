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

- **1a.** The developer names another mode of the same brand, on one of its axes, such as dark on the colour scheme. The system draws the piece with that mode's values, and the use case ends.
- **1b.** The mode lies on an axis whose modes alter sizes, such as a device. The system lays the piece out again for that mode, and says which texts do not fit. The use case ends.
- **3a.** The piece holds a picture made outside the system, such as a photo. It does not follow the brand, so the system names it.
- **3b.** The new brand lacks what the piece uses. The developer chooses another layout or library component the new brand has, or keeps the earlier brand, and the use case ends.

**Postconditions:** The piece is drawn in the new brand or mode, from the same content.

**Minimal guarantees:**

- Giving a piece another brand or mode alters none of its content.

## Open for the design

What the developer needs here that no accepted record decides yet:

- **Which modes a piece is drawn in.** Whether the system draws, shows and hands out a piece in every combination of the modes of its brand's axes, or only in some.
- **Themes inside one brand.** Whether the looks a brand offers side by side, such as a calm theme and a warm one, are modes on one more axis.

## Sources

- **The goal:** use case 3 of the planning note `2026-10-30-visual-work-capability`, drawn on 30 October from its point 2. It takes in the brand half of the note's use case 12, and the piece's side of its point 27, on modes on several axes.
- **The steps and the guarantee:** the decisions the note records in its points 1, 2, 4g, 21 and 27.
- **No accepted record decides them yet.** The capability's records, written under #2427, will decide them. The use case then anchors each record, and its steps follow them.
