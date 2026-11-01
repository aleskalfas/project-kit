---
id: UC-103
title: Improve a library component without breaking a piece
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
requirements: []
after:
  - [UC-093, UC-094, UC-095, UC-096, UC-104]
pkit:
  friction:
    anchors:
      record:
        - COR-017
        - COR-013
        - COR-009
---

# UC-103 — Improve a library component without breaking a piece

**Goal:** Improve a library component so the pieces that use it can benefit, without an improvement for one piece breaking another.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): does the work for the developer, and may run any step the developer runs.

**Preconditions:** **From [UC-093](../010-make/UC-093-build-presentation.md), [UC-094](../010-make/UC-094-put-figure-in-page.md), [UC-095](../010-make/UC-095-draw-views-of-system.md), [UC-096](../010-make/UC-096-add-visual-as-data.md), or [UC-104](UC-104-add-kind-of-piece.md):** Pieces use the library component, from a library the project owns.

**Assumptions:**

- The project has visual-communication installed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).
- The project lands each change as it chose to land changes: through a pull request, or directly when one person works alone ([COR-009](../../../../../../.pkit/decisions/core/COR-009-pr-workflow.md)).

**Trigger:** The developer sees how a library component could work better, such as a card whose heading wraps badly.

**Main path:**

1. The developer improves the library component in its library.
2. The developer gives the library a new library version.
3. The system keeps the new library version beside the one the pieces use now.
4. For each piece using the library component, the system draws the piece with both library versions, and shows the developer the piece before and after.
5. The developer moves each piece that the new library version improves to it, and leaves each other piece where it is.
6. The developer removes each library version that no piece uses any more.

**Variants:**

- **2a.** The improvement breaks a stable library component, such as by removing a field, and the new library version keeps the major number. The system refuses the library version and names each break.
- **2b.** The library component is experimental, so any library version may alter it. The system says so when it draws a piece that uses the component.
- **4a.** A piece is living, such as a figure in a page. The system proposes the move as a change of its own, with the piece before and after ([UC-094](../010-make/UC-094-put-figure-in-page.md), variant 6b).
- **4b.** A piece is delivered. The system leaves it at the library versions it was delivered with, and draws no before and after.

**Postconditions:** Each piece the developer moved uses the improved library component. Every other piece still uses the library versions it used before.

**Minimal guarantees:**

- A delivered piece never moves to a new library version.
- A stable library component breaks only in a library version whose major number rose.

## Open for the design

What the developer needs here that no accepted record decides yet:

- **A library another project shares.** Its library owner improves it there. This project asks which of its libraries have newer library versions, and takes in a new one as from step 3. No use case yet tells how a project takes in a library by its link.
- **A draft piece.** Point 4j of the planning note moves its lock to the newest library version present at each drawing. Step 4 shows it before and after. Which of the two holds for a draft piece.

## Sources

- **The goal:** use case 2 of the planning note `2026-10-30-visual-work-capability`, which the maintainer asked for on 30 October.
- **The steps and the guarantees:** the decisions the note records in its points 4c, 4d, 4i, 4j, 8 and 18a.
- **No accepted record decides them yet.** The capability's records, written under #2427, will decide them. The use case then anchors each record, and its steps follow them.
