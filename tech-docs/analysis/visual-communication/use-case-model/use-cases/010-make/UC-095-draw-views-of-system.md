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

**Goal:** Draw several views of one system from one model, so each fact is written once and every view shows it the same way.

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
5. Later, the developer edits a fact in the model, such as by adding a relation. Once that change lands, the system draws again each view that shows the fact.

**Variants:**

- **2a.** A view needs a fact the model lacks. The developer adds the fact to the model, never to the view, and the path rejoins at step 2.
- **3a.** The model gained or lost an element or a relation since the view's positions were laid out. The system says the positions are out of date, and the developer lays the view out again.
- **5a.** A view is final. The system leaves it as it was handed out.
- **5b.** The developer gives a kind of element a new look in a new library version of the notation, not in the model. Each view moves to that library version only as any piece moves to a new library version ([UC-103](../020-build-libraries/UC-103-improve-library-component.md)).

**Postconditions:** Each view shows the elements it names from the model, in the notation's look, and each fact is written only in the model.

**Minimal guarantees:** None.

## Sources

- **The goal:** proposed on 31 October, in planning the capability (#2423), after the practice of one model with many views.
- **The steps:** the capability's shared choices (#2424) on what a library and a notation are, and on a piece's lock.
- **Not among the shared choices:** one model for several views, graphs laid out by a helper, and the states of a piece. They are the maintainer's decisions of 30 and 31 October, made in planning the capability (#2423). The first slice leaves out the model and the graphs, and keeps room for them. A later slice of the plan builds them.
- **No accepted record decides them yet.** The capability's records, written under #2427, will decide them. The use case then anchors each record, and its steps follow them.
