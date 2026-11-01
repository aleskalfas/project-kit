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
        - visual-communication:DEC-001#7
        - visual-communication:DEC-001#11
        - visual-communication:DEC-003#4
        - visual-communication:DEC-003#6
        - visual-communication:DEC-003#7
        - visual-communication:DEC-003#8
        - visual-communication:DEC-003#9
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

- **1a.** The library is one another project shares, so the project's copy is never edited. Its library owner improves the library component there, and the developer takes in the newer library version ([UC-109](UC-109-take-in-shared-library.md), variants 1a and 6a). The use case ends.
- **2a.** The improvement breaks a stable library component, such as by removing a field, and the new library version keeps the major number. The system refuses the library version and names each break.
- **2b.** The library component is experimental, so any library version may alter it. The system says so when it draws a piece that uses the library component.
- **4a.** A piece is published, such as a figure in a page. The system proposes the move as a change of its own, with the piece before and after ([UC-094](../010-make/UC-094-put-figure-in-page.md), variant 6b).
- **4b.** A piece is final. The system leaves it at the library versions it was handed out with, and draws no before and after.
- **4c.** A piece is a draft whose lock is not pinned. Its lock moves to the new library version at the piece's next drawing, within the major number it names. The system draws no before and after for it.

**Postconditions:** Each piece the developer moved uses the improved library component. Every other piece still uses the library versions it used before.

**Minimal guarantees:**

- A final piece never moves to a new library version.
- A stable library component breaks only in a library version whose major number rose.

## Sources

- **The goal:** the maintainer asked for it on 30 October, in planning the capability (#2423). It rests on a library's release, which never changes a piece others rely on until a person moves its lock ([DEC-001 point 7](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#7-a-pieces-libraries-change-only-when-a-person-moves-its-lock)).
- **The steps and the guarantees:**
  - **Steps 1 to 3, and step 6:** a released library version never changes, so a change is a new one. Each is kept whole in a folder of its own while a lock names it (DEC-003 points [4](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#4-the-library-folder-keeps-each-version-whole-as-released) and [6](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#6-a-released-version-never-changes)).
  - **Steps 4 and 5:** a person moves a piece's lock after a before-and-after of what the move changes ([DEC-001 point 7](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#7-a-pieces-libraries-change-only-when-a-person-moves-its-lock) and [DEC-003 point 8](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#8-a-pieces-state-says-who-moves-its-lock)).
  - **Variant 1a:** a copy of a library another project shares is never rewritten, and its library owner releases each change ([DEC-001 point 11](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#11-shipped-with-the-methodology-and-a-projects-work-stays-the-projects) and DEC-003 point 4).
  - **Variants 2a and 2b, and the second guarantee:** a library owner marks each library component's status, and a release refuses to break a stable one outside a new major number. A piece that uses an experimental one is told so as a fact (DEC-003 points [7](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#7-a-components-status-says-what-its-library-promises) and [9](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#9-the-severities-of-these-checks)).
  - **Variants 4a, 4b and 4c, and the first guarantee:** a piece's state says who moves its lock (DEC-003 point 8).
