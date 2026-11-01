---
id: UC-106
title: Build a brand on another brand
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
requirements: []
after:
  - [UC-105, UC-109]
pkit:
  friction:
    anchors:
      record:
        - visual-communication:DEC-001#5
        - visual-communication:DEC-003#1
        - visual-communication:DEC-003#6
        - visual-communication:DEC-003#8
        - visual-communication:DEC-004#6
        - visual-communication:DEC-004#11
        - COR-017
        - COR-013
---

# UC-106 — Build a brand on another brand

**Goal:** Build a brand on another brand, changing only what that brand lets me change, and give my brand its own library versions.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): does the work for the developer, and may run any step the developer runs.

**Preconditions:** **From [UC-105](UC-105-make-brand.md), or [UC-109](UC-109-take-in-shared-library.md):** The brand to build on exists, and lists what a brand built on it may alter.

**Assumptions:**

- The project has visual-communication installed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).

**Trigger:** A look must differ from another look and stay inside it, such as a game restyling the controls of its platform.

**Main path:**

1. The developer starts a brand that names the brand it builds on, and the major number of that brand's library versions it fits.
2. The developer gives new values to what the brand it builds on lets it alter.
3. The system checks the new brand, and names each value it gives that the brand it builds on does not list.
4. The developer gives the new brand its own library versions, apart from the brand it builds on.
5. A piece that names the new brand is drawn in its values, with the layouts and library components of the brand it builds on.

**Variants:**

- **1a.** The brand to build on builds on a brand in turn, such as a game's brand on its platform's. The new brand alters only what is open to it along the chain, since each brand narrows what the one before it opens.
- **1b.** The look would build on two brands at once. A brand builds on one brand at most, so the developer chooses one.
- **2a.** The look needs a part, or the layouts of a kind of piece, that the brand it builds on lacks. The new brand adds them as its own, and never replaces a layout or a part that brand has.
- **2b.** The look needs an axis or a mode that the brand it builds on lacks, such as a high contrast. The new brand adds none, so the developer asks that brand's library owner to add it.
- **3a.** The new brand gives a value that the brand it builds on does not list. The developer removes the value, or asks that brand's library owner to list it, and the path rejoins at step 3.
- **5a.** A piece uses two libraries that fit different major numbers of one brand. The system says that the two cannot be used in one piece.

**Postconditions:** The new brand changes only the values that the brand it builds on opens to it, and adds no axis and no mode.

**Minimal guarantees:**

- A brand built on another never replaces that brand's layouts or library components.

## Sources

- **The goal:** a brand built on another brand, from the online game platform the maintainer described on 1 November. The platform is an example only, and nothing of a game is built. The goal rests on a brand built on another, within the roles that brand opens to it ([DEC-004 point 6](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-004-brands-and-notations.md#6-a-brand-may-build-on-one-other-brand-within-the-roles-its-base-declares-open)).
- **Its approval:** the brand built on another was decided under the maintainer's delegation. He approved it with the plan of #2423 the same day: "ok go ahead".
- **The steps and the guarantee:**
  - **Steps 1, 2 and 5, variants 1a, 1b, 2a and 2b, and the guarantee:** a brand builds on one brand at most, named by its major number, and gives values only to the roles that brand opens. It adds no axis and no mode, and keeps that brand's layouts and parts ([DEC-004 point 6](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-004-brands-and-notations.md#6-a-brand-may-build-on-one-other-brand-within-the-roles-its-base-declares-open) and [DEC-001 point 5](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#5-libraries-hold-values-structure-or-meaning)).
  - **Step 3 and variant 3a:** a value given to a role that the brand it builds on does not open fails validation ([DEC-004 point 11](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-004-brands-and-notations.md#11-what-the-checks-report-and-how-severely)).
  - **Step 4:** a library takes library versions of its own, and a released one never changes (DEC-003 points [1](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#1-three-numbers-each-with-one-job) and [6](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#6-a-released-version-never-changes)).
  - **Variant 5a:** no lock fits two major numbers of one library, so a piece cannot use such libraries together ([DEC-003 point 8](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#8-a-pieces-state-says-who-moves-its-lock)).
