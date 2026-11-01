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

1. The developer starts a piece for the figure, and names its brand and its notation. The piece is living: it lasts as long as the page that shows it.
2. The developer writes the figure's content, and chooses the library component that does its job.
3. The system draws the figure in each mode of the brand's colour scheme, such as light and dark.
4. The developer shows the figure in the page, from a copy that always holds the figure's current drawing.
5. The system shows the figure in the mode the reader's site uses, and follows the reader's switch to another mode.
6. The developer lands the page and the figure in one change.

**Variants:**

- **2a.** The figure was first drawn for a slide. The developer takes its content out of the presentation unaltered, as a piece of its own.
- **6a.** The figure's content was edited, and the figure was not drawn again. The system's check fails on the figure until it is drawn again.
- **6b.** The developer takes in a new library version of a library the figure uses. The system proposes to move the figure to it, as a change of its own, with the figure before and after. The figure moves only once that change lands.

**Postconditions:** The page shows the figure, drawn from its current content, in the mode its reader uses.

**Minimal guarantees:**

- A figure never moves to a new library version unless a change that shows it before and after lands.
- An earlier state of the documentation, such as one a tag names, shows the figure as it was then.

## Sources

- **The goal:** proposed on 31 October, in planning the capability (#2423), to test its design beyond presentations.
- **The steps and the guarantees:** the capability's shared choices (#2424) on a piece, its content and its lock, and on a brand's modes. Step 4 and variant 6a also follow the shared choices on outputs and their versions, and on how `check` reports.
- **Not among the shared choices:** the living state, whose lock moves only through a change that shows the piece before and after. It is the maintainer's decision of 31 October, made in planning the capability (#2423).
- **No accepted record decides them yet.** The capability's records, written under #2427, will decide them. The use case then anchors each record, and its steps follow them.
