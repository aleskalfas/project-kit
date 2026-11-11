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
        - visual-communication:DEC-001#10
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

**Trigger:** The project's documentation shows another capability's diagrams, such as the diagrams of its analysis, in a look unlike the project's pieces.

**Main path:**

1. The adopter connects visual-communication to the other capability.
2. The developer adds a library component for each kind of diagram to draw first, to a library the project owns.
3. The system draws each diagram whose kind a library covers, from the data the other capability gives, in the project's brand.
4. The system leaves each other diagram to the other capability, which draws it its own way. No diagram is left undrawn.
5. The system says how many kinds the libraries cover, such as "the analysis needs 4 kinds, your libraries draw 2".

**Variants:**

- **2a.** Later, the developer adds a library component for another kind. From then on, the diagrams of that kind are drawn in the libraries' look, and the system counts the kind as covered.

**Postconditions:** Each diagram of the other capability is drawn, in the libraries' look where they cover its kind, and the adopter knows how much they cover.

**Minimal guarantees:**

- A kind that no library covers never leaves a diagram undrawn. The other capability draws it its own way.

## Open for the design

What the adopter needs here that no accepted record decides yet:

- **How the two capabilities connect.** The founding record leaves it to be decided with the other capability ([DEC-001 point 10](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#10-independent-and-connected-to-others-later)). A connection point carries data, a process or an event, and none carries a request with input, such as "draw this from that data" ([COR-053](../../../../../../.pkit/decisions/core/COR-053-connection-points.md)). So the connection may need a new decision of the core.
- **How the other capability declares its kinds.** It names each kind of diagram it needs drawn, the data it gives and its limits, and the drawing it falls back to.

## Sources

- **The goal:** the maintainer asked for it on 31 October, in planning the capability (#2423), with software-analysis as the first other capability. It rests on another capability's visuals, which this one may later draw through a contract that names what is to be drawn ([DEC-001 point 10](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#10-independent-and-connected-to-others-later)).
- **The steps and the guarantee, in part:** this capability reports what it cannot draw, and works with no other capability installed ([DEC-001 point 10](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#10-independent-and-connected-to-others-later)).
- **Left to a later slice:** the contract, the coverage reported and the other capability's own drawing for any kind not covered. They are the maintainer's decision of 31 October (#2423), and not among the capability's shared choices (#2424). How the two capabilities connect is decided with the other capability, in a later slice of EPIC #2423 ([DEC-001 point 10](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#10-independent-and-connected-to-others-later)).
