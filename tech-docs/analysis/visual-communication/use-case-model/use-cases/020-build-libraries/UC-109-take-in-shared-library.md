---
id: UC-109
title: Take in a library another project shares
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

# UC-109 — Take in a library another project shares

**Goal:** Take in a library that another project shares, by its link, and take in its newer library versions when I choose.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): does the work for the developer, and may run any step the developer runs.

**Preconditions:** None.

**Assumptions:**

- The project has visual-communication installed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).

**Trigger:** Another project shares a library that the project's pieces need, such as a client's brand, and gives the developer its link.

**Main path:**

1. The developer adds the library by its link.
2. The system fetches one library version of the library whole, at the tag its library owner gave it, into a folder of its own.
3. The system checks that the library fits the format the project's visual-communication reads.
4. The system lists the library in the project's list of libraries, with its link and the library version present. It keeps a hash of the copy.
5. The developer commits the copy with the project, so drawing a piece needs no network and no sign-in.
6. The developer names the library in a piece, and the piece's lock names its library version.

**Variants:**

- **1a.** The library is in the project already, and the developer asks which libraries have newer library versions. The system lists each, and changes nothing. The developer takes in a newer one, and the path rejoins at step 2.
- **2a.** The link cannot be reached. The system says so and writes nothing, and the use case ends.
- **3a.** The library fits a format that the project's visual-communication does not read. The system names the format and takes nothing in, and the use case ends.
- **5a.** The copy was edited in the project. It no longer matches its hash, so the system's check fails on it until the developer fetches it again.
- **6a.** The library was in the project already (variant 1a). The system draws each piece whose lock names the library with both library versions, and shows the developer the piece before and after. The developer moves the lock of each piece the newer library version improves, and leaves each other piece where it is. A delivered piece's lock stays.
- **6b.** A piece is living. The system proposes the move of its lock as a change of its own, with the piece before and after ([UC-094](../010-make/UC-094-put-figure-in-page.md), variant 6b).
- **6c.** The newer library version breaks what a piece uses, such as by renaming a library component. Its library owner gives a note on the break. On the developer's request, the system rewrites the piece's content to follow it, and the developer reviews that change like any other.
- **6d.** No lock names an earlier library version any more. The developer removes it.

**Postconditions:** The library is in the project at the library version taken in. Each piece is drawn at the library version its lock names.

**Minimal guarantees:**

- The system never writes into a library version it took in.
- A delivered piece's lock never moves to a newer library version.

## Open for the design

What the developer needs here that no accepted record decides yet:

- **Which library version is taken in first.** The newest that the link offers, or one the developer names.
- **What a library builds on.** Whether taking in a library checks that each library it builds on is in the project, at the major number it needs. What the developer does when one is missing. How such a check reports is one of the capability's shared choices (#2424).
- **A draft piece.** By the glossary's definition of draft, its lock moves to the newest library version present each time the piece is drawn. Variant 6a shows each piece before and after. Which of the two holds for a draft piece.
- **A library that needs a sign-in.** Whether the operator signs in to reach a library kept in a private repository, as to a renderer's service ([UC-099](../030-draw-and-hand-out/UC-099-draw-through-renderer.md)).

## Sources

- **The goal:** the maintainer's view of 31 October, in planning the capability (#2423). Another project gives a link to its library, and taking in its new versions must be easy.
- **The steps and the guarantees:** the capability's shared choices (#2424) on the library folder, on a piece's lock, and on compatibility by major version.
- **Not among the shared choices:** the maintainer's decisions of 30 and 31 October, made in planning the capability (#2423).
  - Taking in a library by its link.
  - Moving a piece to a newer library version only after showing it before and after.
  - The states of a piece.
- **No accepted record decides them yet.** The capability's records, written under #2427, will decide them. The use case then anchors each record, and its steps follow them.
