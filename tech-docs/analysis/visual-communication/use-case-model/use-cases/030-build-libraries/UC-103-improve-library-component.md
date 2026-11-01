---
id: UC-103
title: Improve a library component without breaking a piece
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
requirements: []
after:
  - [UC-093, UC-094]
pkit:
  friction:
    anchors:
      record:
        - COR-017
        - COR-013
        - COR-009
---

# UC-103 — Improve a library component without breaking a piece

**Goal:** Improve a library component so the pieces that use it can benefit, without an improvement for one piece breaking another.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): does the work for the developer, and may run any step the developer runs.

**Preconditions:** **From [UC-093](../010-make/UC-093-build-presentation.md), or [UC-094](../010-make/UC-094-put-figure-in-page.md):** Pieces use the library component.

**Assumptions:**

- The project has visual-communication installed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).
- The developer can edit the library: it is the project's own, or kept in a repository the developer can edit.
- The project lands each change as it chose to land changes: through a pull request, or directly when one person works alone ([COR-009](../../../../../../.pkit/decisions/core/COR-009-pr-workflow.md)).

**Trigger:** The developer sees how a library component could work better, such as a card whose heading wraps badly.

**Main path:**

1. The developer improves the library component in its library.
2. The developer gives the library a new version.
3. The project takes in the new version, beside the version its pieces use now.
4. For each piece that uses the library component, the system draws the piece with both versions, and shows the developer the piece before and after.
5. The developer moves each piece that the new version improves to it, and leaves each other piece where it is.
6. The developer removes each version that no piece uses any more.

**Variants:**

- **2a.** The improvement breaks a stable library component, such as by removing a field, and the new version is no new major version. The system refuses the version and names each break.
- **2b.** The library component is experimental. It may be altered in any version, and each piece that uses it is told so when it is drawn.
- **3a.** The developer asks which libraries have newer versions. The system lists them, and writes nothing.
- **4a.** A piece is a draft. It takes the newest version at its next drawing, with no before and after.
- **4b.** A piece is living, such as a figure in a page. The system proposes the move as a change of its own, with the piece before and after ([UC-094](../010-make/UC-094-put-figure-in-page.md), variant 6b).
- **4c.** A piece is delivered. The system leaves it at the versions it was delivered with.
- **4d.** A piece is adapted. It moves only when the developer moves it, as in step 5.

**Postconditions:** Each piece the developer moved uses the improved library component, and every other piece looks as it did.

**Minimal guarantees:**

- A delivered piece never moves to a new version of a library.
- A stable library component breaks only in a new major version of its library.

## Sources

- **The goal:** use case 2 of the planning note `2026-10-30-visual-work-capability`, which the maintainer asked for on 30 October.
- **The steps and the guarantees:** the decisions the note records in its points 4c, 4d, 4i, 4j, 8 and 18a.
- **No accepted record decides them yet.** The capability's records, written under #2427, will decide them. The use case then anchors each record, and its steps follow them.
