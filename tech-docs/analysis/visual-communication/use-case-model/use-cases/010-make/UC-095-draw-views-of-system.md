---
id: UC-095
title: Draw several views of one system from one model
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
---

# UC-095 — Draw several views of one system from one model

**Goal:** Draw several views of one system from one model, so each fact is written once and a look changed once changes every view.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): does the work for the developer, and may run any step the developer runs.

**Preconditions:** None.

**Assumptions:**

- The project has visual-communication installed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).
- The project lands each change as it chose to land changes: through a pull request, or directly when one person works alone ([COR-009](../../../../../../.pkit/decisions/core/COR-009-pr-workflow.md)).

**Trigger:** The developer needs more than one picture of one system, such as an overview for newcomers and a closer view of one of its parts.

**Main path:**

1. The developer writes the system's elements and the relations between them once, in a model the project keeps.
2. For each view, the developer starts a piece that names, from the model, the elements it shows.
3. The developer lays out each view's elements by hand, or has a graph laid out automatically and keeps the positions it gets.
4. The system draws each view, each element in the look that the notation gives to what the element is.
5. The developer gives one kind of element a new look in the notation, and the system draws every view with it.

**Variants:**

- **2a.** A view needs a fact the model lacks. The developer adds the fact to the model, never to the view, and the path rejoins at step 2.
- **3a.** The model gained or lost an element or a relation since the view's positions were laid out. The system says the positions are out of date, and the developer lays the view out again.
- **4a.** The model was edited, such as by a new relation. Each view that shows both ends of the relation draws it at its next drawing, once the change that edits the model lands.

**Postconditions:** Each view shows the elements it names from the model, in the notation's look, and each fact is written only in the model.

**Minimal guarantees:** None.

## Sources

- **The goal:** use case 10 of the planning note `2026-10-30-visual-work-capability`, proposed on 31 October after the practice of one model with many views.
- **The steps:** the decisions the note records in its points 4g and 22. Point 22 leaves this out of the first slice, and keeps room for it.
- **No accepted record decides them yet.** The capability's records, written under #2427, will decide them. The use case then anchors each record, and its steps follow them.
