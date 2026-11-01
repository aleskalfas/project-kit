---
id: UC-108
title: Have another capability's diagrams drawn in my libraries' look
status: active
actor: core:ACT-adopter
other-actors:
  - core:ACT-developer
requirements: []
pkit:
  friction:
    anchors:
      record:
        - COR-017
        - COR-053
---

# UC-108 — Have another capability's diagrams drawn in my libraries' look

**Goal:** Have another capability's diagrams drawn in my libraries' look, the rest drawn that capability's own way, and see how much my libraries cover.

**Other actors:**

- **Developer** (`core:ACT-developer`): adds to a library the project owns a library component for each kind of diagram the other capability needs drawn.

**Preconditions:** None.

**Assumptions:**

- The project has visual-communication and the other capability installed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).
- The other capability declares each kind of diagram it needs drawn, with the data it gives and its limits ("Open for the design", below).

**Trigger:** The project's documentation shows another capability's diagrams, such as the diagrams of its analysis, in a look unlike the project's pieces.

**Main path:**

1. The adopter connects visual-communication to the other capability.
2. The developer adds a library component for each kind of diagram to draw first, to a library the project owns.
3. The system draws each diagram whose kind a library covers, from the data the other capability gives, in the project's brand.
4. The system draws each other diagram the other capability's own way, and fails none.
5. The system says how many kinds the libraries cover, such as "the analysis needs 4 kinds, your libraries draw 2".

**Variants:**

- **2a.** Later, the developer adds a library component for another kind. From then on, the diagrams of that kind are drawn in the libraries' look, and the system counts the kind as covered.

**Postconditions:** Each diagram of the other capability is drawn, in the libraries' look where they cover its kind, and the adopter knows how much they cover.

**Minimal guarantees:**

- A kind that no library covers never fails a diagram. The diagram is drawn the other capability's own way.

## Open for the design

What the adopter needs here that no accepted record decides yet:

- **How the two capabilities connect.** A connection point carries data, a process or an event, and none carries a request with input, such as "draw this from that data" ([COR-053](../../../../../../.pkit/decisions/core/COR-053-connection-points.md)). So the connection may need a decision of the core's.
- **How the other capability declares its kinds.** That is each kind's data and its limits, and the drawing it falls back to.

## Sources

- **The goal:** use case 13 of the planning note `2026-10-30-visual-work-capability`, which the maintainer asked for on 31 October, with software-analysis as the first other capability.
- **The steps and the guarantee:** the decisions the note records in its point 22. Its point 24 keeps the connection open, and nothing of it is built now.
- **No accepted record decides them yet.** The capability's records, written under #2427, will decide them. The use case then anchors each record, and its steps follow them.
