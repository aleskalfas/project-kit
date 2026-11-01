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
        - visual-communication:DEC-001#3
        - visual-communication:DEC-001#6
        - visual-communication:DEC-003#8
        - visual-communication:DEC-004#10
        - visual-communication:DEC-006#1
        - visual-communication:DEC-006#5
        - visual-communication:DEC-006#7
        - visual-communication:DEC-006#8
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
5. Later, the developer edits a fact in the model, such as by adding a relation. The developer draws again each view that reads the model, and lands them with the edit.

**Variants:**

- **2a.** A view needs a fact the model lacks. The developer adds the fact to the model, never to the view, and the path rejoins at step 2.
- **3a.** The model gained or lost an element or a relation since the view's positions were laid out. The system says the positions are out of date, and the developer lays the view out again.
- **5a.** A view is final. The system leaves it as it was handed out.
- **5b.** The developer gives a kind of element a new look in a new library version of the notation, not in the model. Each view moves to that library version only as any piece moves to a new library version ([UC-103](../020-build-libraries/UC-103-improve-library-component.md)).

**Postconditions:** Each view shows the elements it names from the model, in the notation's look, and each fact is written only in the model.

**Minimal guarantees:** None.

## Sources

- **The goal:** proposed on 31 October, in planning the capability (#2423), after the practice of one model with many views. It rests on shared content, which a piece reads from a source it names, such as a model several views read ([DEC-001 point 3](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#3-a-piece-and-its-content)).
- **The steps:**
  - **Steps 1 and 2, and variant 2a:** what a piece reads from shared content stays where it lives, and an element a view names carries a stable id ([DEC-001 point 3](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#3-a-piece-and-its-content)).
  - **Step 3:** a helper script may lay out a graph while the piece is prepared ([DEC-006 point 1](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-006-work-outside-the-engine-and-outputs.md#1-a-program-run-while-preparing-may-write-a-picture)).
  - **Step 4 and variant 5b:** a notation maps each concept to roles, never to values. An element takes its colour from the concept it names ([DEC-004 point 10](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-004-brands-and-notations.md#10-a-notation-maps-concepts-to-roles-read-with-its-name) and [DEC-001 point 6](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#6-a-pattern-arranges-items-and-an-item-says-what-it-is)).
  - **Step 5:** the record of exports fingerprints the shared content a piece reads. A published piece's stale copy fails the check (DEC-006 points [7](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-006-work-outside-the-engine-and-outputs.md#7-every-export-keeps-its-number) and [8](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-006-work-outside-the-engine-and-outputs.md#8-what-the-check-reports-and-how-seriously)).
  - **Variant 3a:** a fingerprint of what a helper script read says when its output is stale ([DEC-006 point 5](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-006-work-outside-the-engine-and-outputs.md#5-a-fingerprint-says-when-output-is-stale-and-the-rest-is-only-recorded)).
  - **Variant 5a:** a final piece's lock never moves, and its outputs are never reported stale ([DEC-003 point 8](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#8-a-pieces-state-says-who-moves-its-lock) and DEC-006 point 8).
- **Left to a later slice:** how several views share one model, and how a graph's positions are kept, are decided by the change that builds them ([DEC-006 point 1](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-006-work-outside-the-engine-and-outputs.md#1-a-program-run-while-preparing-may-write-a-picture)). So steps 1, 2, 3 and 5, and variant 3a, take their form from a later slice of EPIC #2423. The maintainer decided on 30 and 31 October that the first slice leaves them out, and keeps room for them (#2423).
