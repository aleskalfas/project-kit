---
id: UC-110
title: Add a library component and mark it stable
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
---

# UC-110 — Add a library component and mark it stable

**Goal:** Add a library component to a library my project owns, and mark it stable once I judge that pieces can rely on it.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): does the work for the developer, and may run any step the developer runs.

**Preconditions:** None.

**Assumptions:**

- The project has visual-communication installed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).

**Trigger:** The developer finds a job that no library component does, such as showing a timeline, whether pieces need it now or later. Or a local component is needed in other pieces too.

**Main path:**

1. The developer writes the library component in a library the project owns. The library component states the job it does, the established form it follows with that form's source, and its fields and options.
2. The system checks the library component, and draws it once with each value of each of its options.
3. The developer has the library component reviewed against its job and its form, with the drawings of step 2.
4. The developer gives the library a new library version, in which the library component is experimental.
5. Later, the developer judges that pieces can rely on the library component, and marks it stable in its file.
6. The developer gives the library a new library version, in which the library component is stable.

**Variants:**

- **1a.** The library component comes from a local component of a piece ([UC-096](../010-make/UC-096-add-visual-as-data.md)). The developer generalises it. Its fixed texts become fields the content fills, and its one-time choices become options. Each of its colours becomes a name the brand gives a value to.
- **1b.** A helper script wrote the local component. The local component stays in its piece until visual-communication can do the script's work itself, and the use case ends.
- **1c.** The library is one another project shares, so the project's copy is never edited. The developer asks its library owner to add the library component, and the use case ends. Once the library owner gives the library a new library version, the project takes it in ([UC-109](UC-109-take-in-shared-library.md), variant 1a).
- **2a.** A check fails, such as on a fixed colour. The system names each fault. The developer mends it, and the path rejoins at step 2.
- **4a.** The library component came from a local component (variant 1a). The system draws the piece it came from with the library component, and with the local component. Once the developer has seen the two, the developer moves the piece to the library component, and removes the local component. A delivered piece keeps its local component.

**Postconditions:** The library component is in the library, marked stable, and only a library version whose major number rose may break it.

**Minimal guarantees:**

- No count of the pieces that use a library component, and no check, marks it stable.

## Open for the design

What the developer needs here that no accepted record decides yet:

- **The review.** Who reviews a library component: a person, or an AI agent.
- **Whether a library owner brings an actor of its own.** A library owner's needs, such as promises to other projects' pieces, may set whoever acts for it apart from the developer. Until a person decides, the developer of the project that owns the library acts for it.

## Sources

- **The goal:** on 1 November, in planning the capability (#2423), the maintainer decided that a library component becomes stable when its library owner marks it so. No count of its uses decides it.
- **The actor:** the same decision says "a project's own library's owner is that project". The developer of that project acts for it here.
- **The steps and the guarantee:** the capability's shared choices (#2424) on a component's status and its promise, and on a pattern's options. Variant 1b follows the shared choice on helpers run while a piece is prepared. How a local component becomes a library component follows from these choices and from a piece's lock. The maintainer asked on 31 October how it works.
- **No accepted record decides them yet.** The capability's records, written under #2427, will decide them. The use case then anchors each record, and its steps follow them.
