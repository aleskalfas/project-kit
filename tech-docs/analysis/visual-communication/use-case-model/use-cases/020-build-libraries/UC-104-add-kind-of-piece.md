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

- **4a.** The brand lacks a layout the new kind names, or draws it with other content slots. The system names what is missing. The developer adds it, and the path rejoins at step 4.

**Postconditions:** Pieces of the new kind are made and drawn like any other, and the capability's own files are as they were.

**Minimal guarantees:** None.

## Sources

- **The goal:** use case 11 of the planning note `2026-10-30-visual-work-capability`, proposed on 31 October to test the note's decisions beyond presentations.
- **The steps:** the decisions the note records in its points 4f and 4g. In point 4f, the maintainer added that the capability's code knows no kind of piece.
- **No accepted record decides them yet.** The capability's records, written under #2427, will decide them. The use case then anchors each record, and its steps follow them.
