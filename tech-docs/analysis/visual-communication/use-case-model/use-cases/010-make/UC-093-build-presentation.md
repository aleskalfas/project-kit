---
id: UC-093
title: Build a presentation from library components
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
        - visual-communication:DEC-001#2
        - visual-communication:DEC-001#3
        - visual-communication:DEC-001#4
        - visual-communication:DEC-001#6
        - visual-communication:DEC-002#3
        - visual-communication:DEC-003#5
        - visual-communication:DEC-003#7
        - visual-communication:DEC-003#8
        - visual-communication:DEC-003#9
        - visual-communication:DEC-004#10
        - visual-communication:DEC-005#4
        - visual-communication:DEC-007#2
        - COR-017
        - COR-013
---

# UC-093 — Build a presentation from library components

**Goal:** Build a presentation from library components that exist, filled with my own content, so nothing made once is made again.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): does the work for the developer, and may run any step the developer runs.

**Preconditions:** None.

**Assumptions:**

- The project has visual-communication installed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).

**Trigger:** The developer has a talk to give, such as a talk that shows the project to its users.

**Main path:**

1. The developer starts a piece for the presentation. The developer names the brand that draws it, and the notation of the subject it is about.
2. The developer writes the presentation's content: its title, and for each slide the layout it takes and what fills each content slot of that layout.
3. For each slide's picture, the developer chooses a library component that does its job, such as one that shows layers or one that shows steps. The developer fills it with the slide's own content.
4. The system draws the presentation in the brand, with the library components the content names.
5. The system says which texts do not fit where they go, and which library components are still experimental.
6. The developer reads the drawn presentation as its audience would, and mends the content where the reading asks.

**Variants:**

- **1a.** The presentation is about several subjects, such as two projects. The developer names the notation of each. Where two notations name one concept differently, the system says so, and the developer settles the name for this piece.
- **1b.** The developer starts from a final presentation, to give it to a new audience. The system copies it as a draft with its lock pinned. The copy keeps the library versions the final presentation used, until the developer moves the copy's lock ([UC-103](../020-build-libraries/UC-103-improve-library-component.md)). The path goes on at step 2.
- **3a.** No library component fits a slide's picture. The developer makes a local component for it, inside this piece ([UC-096](UC-096-add-visual-as-data.md)). The path goes on at step 4.
- **3b.** The project holds no copy of the starter library yet. Before choosing, the developer runs the command that copies the version the capability ships into the project. The copy is the project's file, and the path rejoins at step 3.
- **4a.** The content does not fit what a library component declares, such as a field the library component does not have. The system names each fault and draws nothing. The developer mends the content, and the path rejoins at step 4.
- **5a.** A text does not fit. The developer shortens it, or chooses another option the library component declares, and the path rejoins at step 4.
- **5b.** A library component is experimental. The system still draws it, and says only that it may be altered in any library version.

**Postconditions:** The presentation is drawn in the brand it names, from library components filled with its own content.

**Minimal guarantees:**

- An experimental library component is drawn with a note, and never refused.

## Open for the design

What the developer needs here that no accepted record decides yet:

- **A brand to start from.** The starter library holds no values, so a presentation needs a brand. Whether the capability ships a brand that a project may lock, such as a neutral one, is left to a later change ([DEC-004](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-004-brands-and-notations.md), Implications).

## Sources

- **The goal:** the maintainer asked for it on 30 October, in planning the capability (#2423). Variant 1a, a piece about several subjects, was proposed in the same planning on 31 October. The goal rests on what the capability is for: pieces built from shared library components ([DEC-001 point 1](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#1-what-the-capability-is-for)).
- **The steps and the guarantee:**
  - **Steps 1 and 2:** a piece names its brand and its notations. Its content fills the content slots of the layouts its kind of piece declares (DEC-001 points [3](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#3-a-piece-and-its-content) and [4](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#4-components-are-data-and-the-engine-knows-none-by-name)).
  - **Step 3 and variant 3a:** the starter library holds a library component for each job a visual does. A visual beyond them is a local component ([DEC-001 point 6](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#6-a-pattern-arranges-items-and-an-item-says-what-it-is) and [DEC-007 point 2](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-007-starter-library.md#2-organised-by-the-job-a-visual-does)).
  - **Variant 3b:** a library the capability ships reaches a project only through a command a person runs, and its copy is the project's file ([DEC-003 point 5](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#5-a-shipped-library-reaches-the-project-only-through-a-command-a-person-runs)).
  - **Step 4:** the engine computes the drawing from the content and the libraries. A new draft's first lock takes the newest library versions the project holds ([DEC-001 point 2](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#2-the-logical-layer-is-the-source-and-renderers-only-project-it) and [DEC-003 point 8](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#8-a-pieces-state-says-who-moves-its-lock)).
  - **Step 5, variants 5a and 5b, and the guarantee:** the engine measures each text from committed fonts, and never shrinks it to fit. An experimental library component is drawn, and stated as a fact ([DEC-005 point 4](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-005-engine-and-plugins.md#4-the-engine-measures-text-from-committed-fonts-and-breaks-its-lines) and DEC-003 points [7](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#7-a-components-status-says-what-its-library-promises) and [9](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#9-the-severities-of-these-checks)).
  - **Variant 1a:** a piece may name several notations, and a concept is read with its notation's name (DEC-001 point 3 and [DEC-004 point 10](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-004-brands-and-notations.md#10-a-notation-maps-concepts-to-roles-read-with-its-name)).
  - **Variant 1b:** a copy of a final piece, taken up again for a new audience, starts as a draft with its lock pinned (DEC-003 point 8).
  - **Variant 4a:** a key is refused where neither a file's schema nor the library or local component it fills declares it. The nearest known key is named ([DEC-002 point 3](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-002-files-and-validation.md#3-each-file-names-its-schema)).
- **Left to a later slice:** in variant 1a, how the system finds that two notations name one concept differently, and how the developer settles the name. It rests on the maintainer's decisions of 30 and 31 October on the capability's layered glossary (#2423). A later slice of EPIC #2423 decides it with translation, which also decides the words a notation gives ([DEC-004 point 10](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-004-brands-and-notations.md#10-a-notation-maps-concepts-to-roles-read-with-its-name)).
