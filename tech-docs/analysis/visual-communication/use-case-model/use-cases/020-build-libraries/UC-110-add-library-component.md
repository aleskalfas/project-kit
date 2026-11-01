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
        - visual-communication:DEC-001#4
        - visual-communication:DEC-001#5
        - visual-communication:DEC-001#6
        - visual-communication:DEC-001#11
        - visual-communication:DEC-002#7
        - visual-communication:DEC-003#6
        - visual-communication:DEC-003#7
        - visual-communication:DEC-003#8
        - visual-communication:DEC-006#1
        - visual-communication:DEC-007#3
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
- **4a.** The library component came from a local component (variant 1a). The system draws the piece it came from with the library component, and with the local component. Once the developer has seen the two, the developer moves the piece to the library component, and removes the local component. A final piece keeps its local component.

**Postconditions:** The library component is in the library, marked stable, and only a library version whose major number rose may break it.

**Minimal guarantees:**

- No count of the pieces that use a library component, and no check, marks it stable.

## Open for the design

What the developer needs here that no accepted record decides yet:

- **The review.** Who reviews a library component: a person, or an AI agent. In the starter library, its library owner judges each library component in review ([DEC-007 point 3](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-007-starter-library.md#3-each-component-enters-as-experimental)). The founding record leaves the capability's agents, which review pieces, to later records ([DEC-001 point 1](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#1-what-the-capability-is-for)). A later slice of EPIC #2423 decides them.
- **Whether a library owner brings an actor of its own.** A library owner's needs, such as promises to other projects' pieces, may set whoever acts for it apart from the developer. Until a person decides, the developer of the project that owns the library acts for it.

## Sources

- **The goal:** on 1 November, in planning the capability (#2423), the maintainer decided that a library component becomes stable when its library owner marks it so. No count of its uses decides it. The goal rests on a library component's status, which its library owner marks ([DEC-003 point 7](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#7-a-components-status-says-what-its-library-promises)).
- **The actor:** the same decision says "a project's own library's owner is that project". The developer of that project acts for it here.
- **The steps and the guarantee:**
  - **Steps 1 to 3:** the bar a library component of the starter library meets ([DEC-007 point 3](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-007-starter-library.md#3-each-component-enters-as-experimental)). A project's own library may follow that bar, which binds only the starter library ([DEC-007](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-007-starter-library.md), Implications). The bar asks for:
    - the component's job, and the form it follows with that form's source
    - its fields and options
    - a drawing of each option's value
    - a review
  - **Steps 4 to 6 and the guarantee:** a library owner marks each library component's status, and no count of uses decides it. A stable one breaks only in a library version with a new major number ([DEC-003 point 7](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#7-a-components-status-says-what-its-library-promises)).
  - **Variant 1a:** a library component's options are declared, and its colours are roles a brand gives values to (DEC-001 points [5](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#5-libraries-hold-values-structure-or-meaning) and [6](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#6-a-pattern-arranges-items-and-an-item-says-what-it-is)).
  - **Variant 1b:** a helper script stays the project's code, and never goes into a library. A need that recurs becomes a tool of the engine ([DEC-006 point 1](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-006-work-outside-the-engine-and-outputs.md#1-a-program-run-while-preparing-may-write-a-picture) and [DEC-001 point 4](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#4-components-are-data-and-the-engine-knows-none-by-name)).
  - **Variant 1c:** a library copy that a lock names is never rewritten, and a released library version never changes ([DEC-001 point 11](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#11-shipped-with-the-methodology-and-a-projects-work-stays-the-projects) and [DEC-003 point 6](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#6-a-released-version-never-changes)).
  - **Variant 2a:** a library component holds no raw value. A broken invariant in a file the project can correct fails the check (DEC-001 point 5 and [DEC-002 point 7](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-002-files-and-validation.md#7-one-severity-policy-for-every-finding)).
  - **Variant 4a:** a person moves a piece's lock after a before-and-after, and a final piece's lock never moves ([DEC-003 point 8](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#8-a-pieces-state-says-who-moves-its-lock)).
