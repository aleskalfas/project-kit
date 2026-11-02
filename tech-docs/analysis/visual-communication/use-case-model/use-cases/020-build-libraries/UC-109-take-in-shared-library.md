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
        - visual-communication:DEC-001#7
        - visual-communication:DEC-001#11
        - visual-communication:DEC-002#3
        - visual-communication:DEC-003#1
        - visual-communication:DEC-003#4
        - visual-communication:DEC-003#8
        - visual-communication:DEC-003#9
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
- **2b.** The library lies in a private repository. The system fetches it over the channel the project already uses for that repository, with the methodology's shared sign-in.
- **3a.** The library needs a newer release of visual-communication than the project has installed. The system names the release it needs and takes nothing in, and the use case ends.
- **5a.** The copy was edited in the project. It no longer matches its hash, so the system's check fails on it until the developer fetches it again.
- **6a.** The library was in the project already (variant 1a). The system draws each piece whose lock names the library with both library versions, and shows the developer the piece before and after. The developer moves the lock of each piece the newer library version improves, and leaves each other piece where it is. A final piece's lock stays.
- **6b.** A piece is published. The system proposes the move of its lock as a change of its own, with the piece before and after ([UC-094](../010-make/UC-094-put-figure-in-page.md), variant 6b).
- **6c.** The newer library version breaks what a piece uses, such as by renaming a library component. Its library owner gives a note on the break. On the developer's request, the system rewrites the piece's content to follow the note, and the developer reviews that change like any other.
- **6d.** No lock names an earlier library version any more. The developer removes it.
- **6e.** A piece is a draft whose lock is not pinned. Its lock moves to the newer library version at the piece's next drawing, within the major number it names. The system draws no before and after for it.

**Postconditions:** The library is in the project at the library version taken in. Each piece is drawn at the library version its lock names.

**Minimal guarantees:**

- The system never writes into a library version it took in.
- A final piece's lock never moves to a newer library version.

## Open for the design

What the developer needs here that no accepted record decides yet:

- **Which library version is taken in first.** The newest that the link offers, or one the developer names.
- **What a library builds on.** Whether taking in a library checks that each library it builds on is in the project, at the major number it needs. What the developer does when one is missing. Once a piece locks it, a lock that names a library version the project does not hold fails the check ([DEC-003 point 9](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#9-the-severities-of-these-checks)).

## Sources

- **The goal:** the maintainer's view of 31 October, in planning the capability (#2423). Another project gives a link to its library, and taking in its new library versions must be easy. The goal rests on a library version from another repository, fetched whole at its release, with no registry ([DEC-003 point 4](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#4-the-library-folder-keeps-each-version-whole-as-released)).
- **The steps and the guarantees:**
  - **Steps 1, 2, 4 and 5, and variants 1a, 2b and 6d:** the project keeps each library version whole, as released, committed and kept while a lock names it. One list holds each library's source, its library versions and a hash of each released one ([DEC-003 point 4](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#4-the-library-folder-keeps-each-version-whole-as-released)).
  - **Step 3 and variant 3a:** a library names the oldest release of the capability it needs. The commands that bring in a library version refuse one the installed capability cannot read ([DEC-003 point 1](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#1-three-numbers-each-with-one-job) and [DEC-002 point 3](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-002-files-and-validation.md#3-each-file-names-its-schema)).
  - **Step 6, variants 6a, 6b and 6e, and the second guarantee:** a piece's lock names one library version of each library, and the piece's state says who moves it ([DEC-001 point 7](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#7-a-pieces-libraries-change-only-when-a-person-moves-its-lock) and [DEC-003 point 8](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#8-a-pieces-state-says-who-moves-its-lock)).
  - **Variant 5a:** a library version that no longer matches its released hash fails the check ([DEC-003 point 9](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#9-the-severities-of-these-checks)).
  - **The first guarantee:** a library copy that a lock names is never rewritten ([DEC-001 point 11](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#11-shipped-with-the-methodology-and-a-projects-work-stays-the-projects)).
- **Left to a later slice:** variant 6c, in which the system rewrites a piece's content to follow a break in a newer library version. A new major number is taken only on purpose, since it may rename what the content names ([DEC-003 point 8](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#8-a-pieces-state-says-who-moves-its-lock)). How content then follows the break is decided by a later slice of EPIC #2423.
