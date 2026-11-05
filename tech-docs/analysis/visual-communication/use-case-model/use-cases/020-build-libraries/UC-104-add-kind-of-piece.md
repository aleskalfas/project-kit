---
id: UC-104
title: Add a kind of piece the capability does not ship
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
requirements: []
pkit:
  friction:
    anchors:
      record:
        - visual-communication:DEC-001#1
        - visual-communication:DEC-001#4
        - visual-communication:DEC-001#5
        - visual-communication:DEC-001#11
        - visual-communication:DEC-002#1
        - visual-communication:DEC-004#1
        - visual-communication:DEC-004#6
        - COR-017
        - COR-013
        - COR-001
---

# UC-104 — Add a kind of piece the capability does not ship

**Goal:** Add a kind of piece that the capability does not ship, such as a poster, without changing the capability.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): does the work for the developer, and may run any step the developer runs.

**Preconditions:** None.

**Assumptions:**

- The project has visual-communication installed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).
- What the project adds stays in files of its own, apart from the capability's files ([COR-001](../../../../../../.pkit/decisions/core/COR-001-content-mechanisms.md)).

**Trigger:** The project needs a kind of piece that no library offers, such as a poster for a conference.

**Main path:**

1. The developer adds the top library component of the new kind of piece to a library the project owns. It names the layouts such a piece has, and the content slots of each layout.
2. For each brand the project uses, the developer adds how that brand draws each new layout.
3. The developer starts a piece of the new kind, and fills the content slots of its layouts.
4. The system draws the piece in its brand, as it draws any other kind of piece.

**Variants:**

- **2a.** A brand the project uses is one another project shares, so the project's copy is never edited. The developer builds a brand on it that adds the new layouts ([UC-106](UC-106-build-brand-on-brand.md)), or asks its library owner to add them.
- **4a.** The brand lacks a layout the new kind names, or draws it with other content slots. The system names what is missing. The developer adds it, and the path rejoins at step 4.

**Postconditions:** Pieces of the new kind are made and drawn like any other, and the capability's own files are as they were.

**Minimal guarantees:** None.

## Sources

- **The goal:** proposed on 31 October, in planning the capability (#2423), to test its design beyond presentations. It rests on an engine with no kind of work built in, so a project adds its own ([DEC-001 point 1](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#1-what-the-capability-is-for)).
- **The steps and the postconditions:**
  - **Step 1:** a piece's top library component declares its layouts and their content slots, and the engine knows no kind of piece (DEC-001 points [4](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#4-components-are-data-and-the-engine-knows-none-by-name) and [5](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#5-libraries-hold-values-structure-or-meaning)).
  - **Step 2 and variant 4a:** a brand holds how it draws the layouts of the kinds of piece it serves. What it lacks is reported (DEC-001 point 5 and [DEC-004 point 1](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-004-brands-and-notations.md#1-a-brands-values-are-design-tokens-in-the-dtcg-format)).
  - **Variant 2a:** a library copy that a lock names is never rewritten. A brand built on another may add layouts for a kind of piece that brand lacks ([DEC-001 point 11](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#11-shipped-with-the-methodology-and-a-projects-work-stays-the-projects) and [DEC-004 point 6](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-004-brands-and-notations.md#6-a-brand-may-build-on-one-other-brand-within-the-roles-its-base-declares-open)).
  - **The postconditions:** a project's work lies in its own files, never in the capability's folder ([DEC-002 point 1](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-002-files-and-validation.md#1-the-capabilitys-files-and-the-projects-work-lie-apart)).
