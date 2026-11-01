---
id: UC-094
title: Put a figure in a documentation page
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
requirements: []
pkit:
  friction:
    anchors:
      record:
        - visual-communication:DEC-001#3
        - visual-communication:DEC-001#10
        - visual-communication:DEC-003#8
        - visual-communication:DEC-003#9
        - visual-communication:DEC-004#2
        - visual-communication:DEC-005#5
        - visual-communication:DEC-005#6
        - visual-communication:DEC-006#7
        - visual-communication:DEC-006#8
        - COR-017
        - COR-013
        - COR-009
        - COR-049
---

# UC-094 — Put a figure in a documentation page

**Goal:** Put a figure in a documentation page that follows the page's light or dark mode, and stays current as the page changes.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): does the work for the developer, and may run any step the developer runs.

**Preconditions:** None.

**Assumptions:**

- The project has visual-communication installed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).
- The project keeps its documentation pages in its repository, under its documentation roots ([COR-049](../../../../../../.pkit/decisions/core/COR-049-documentation-roots.md)).
- The project lands each change as it chose to land changes: through a pull request, or directly when one person works alone ([COR-009](../../../../../../.pkit/decisions/core/COR-009-pr-workflow.md)).

**Trigger:** A documentation page needs a figure, such as a diagram of how the parts of the project connect.

**Main path:**

1. The developer starts a piece for the figure, and names its brand and its notation. The piece starts as a draft.
2. The developer writes the figure's content, and chooses the library component that does its job.
3. The system draws the figure in each mode the piece names on the brand's colour scheme, such as light and dark.
4. The developer marks the piece published, since it stays in use as long as the page that shows it. The developer shows the figure in the page, from a copy that always holds the figure's current drawing.
5. The system shows the figure in the mode the reader's site uses, and follows the reader's switch to another mode.
6. The developer lands the page and the figure in one change.

**Variants:**

- **2a.** The figure was first drawn for a slide. The developer takes its content out of the presentation unaltered, as a piece of its own.
- **6a.** The figure's content was edited, and its copy was not made again. The copy is stale, so the system's check fails on it until the copy is made again.
- **6b.** The developer takes in a new library version of a library the figure uses. The system states that the figure's lock is behind it, and names the command that proposes the move. That command proposes the move as a change of its own, with the figure before and after. The figure moves only once that change lands.

**Postconditions:** The page shows the figure, drawn from its current content, in the mode its reader uses.

**Minimal guarantees:**

- A figure never moves to a new library version unless a change that shows it before and after lands.
- An earlier state of the documentation, such as one a tag names, shows the figure as it was then.

## Sources

- **The goal:** proposed on 31 October, in planning the capability (#2423), to test its design beyond presentations. It rests on how a documentation page sees the figure: an image the capability produces from its source, the piece's content ([DEC-001 point 10](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#10-independent-and-connected-to-others-later)).
- **The steps and the guarantees:**
  - **Steps 1 and 2:** a new piece starts as a draft, and names its brand and its notations ([DEC-001 point 3](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#3-a-piece-and-its-content) and [DEC-003 point 8](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#8-a-pieces-state-says-who-moves-its-lock)).
  - **Steps 3 and 5:** a piece names the modes it is drawn in. The modes of an axis that moves nothing share one drawing, so a page switches them while open ([DEC-005 point 6](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-005-engine-and-plugins.md#6-a-piece-names-the-modes-it-is-drawn-in) and [DEC-004 point 2](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-004-brands-and-notations.md#2-modes-lie-on-axes-and-each-axis-changes-values-or-sizes)).
  - **Step 4 and variant 6a:** a published piece keeps a copy where the documentation's rules put the page's produced images. A copy that is stale fails the check (DEC-006 points [7](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-006-work-outside-the-engine-and-outputs.md#7-every-export-keeps-its-number) and [8](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-006-work-outside-the-engine-and-outputs.md#8-what-the-check-reports-and-how-seriously)).
  - **Variant 2a:** a diagram is a page alone, and part of a page inside a slide ([DEC-005 point 5](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-005-engine-and-plugins.md#5-the-scene-holds-every-elements-final-frame-values-and-source)).
  - **Variant 6b and the guarantees:** a published piece's lock moves only through a change a person reviews, with the piece before and after. A lock behind a newer released library version is stated as a fact, with the command that proposes the move (DEC-003 points 8 and [9](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#9-the-severities-of-these-checks)).
