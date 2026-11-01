---
id: UC-096
title: Add a new kind of visual to a piece as data
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
requirements: []
after:
  - [UC-093, UC-094, UC-095, UC-104]
pkit:
  friction:
    anchors:
      record:
        - visual-communication:DEC-001#4
        - visual-communication:DEC-001#5
        - visual-communication:DEC-001#6
        - visual-communication:DEC-001#7
        - visual-communication:DEC-001#8
        - visual-communication:DEC-002#6
        - visual-communication:DEC-003#8
        - visual-communication:DEC-005#1
        - visual-communication:DEC-005#2
        - visual-communication:DEC-005#3
        - visual-communication:DEC-006#1
        - visual-communication:DEC-006#5
        - visual-communication:DEC-006#8
        - COR-017
        - COR-013
---

# UC-096 — Add a new kind of visual to a piece as data

**Goal:** Add a new kind of visual to a piece as data, without code, where no library component fits.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): does the work for the developer, and may run any step the developer runs.

**Preconditions:** **From [UC-093](UC-093-build-presentation.md), [UC-094](UC-094-put-figure-in-page.md), [UC-095](UC-095-draw-views-of-system.md), or [UC-104](../020-build-libraries/UC-104-add-kind-of-piece.md):** The piece the visual is for exists.

**Assumptions:**

- The project has visual-communication installed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).

**Trigger:** A slide or a figure needs a picture that no library component draws, such as a pyramid of layers whose widths step down.

**Main path:**

1. The developer makes a local component inside the piece. It says, as data, which parts the visual has, and how they repeat, line up and take their sizes from the content.
2. The developer takes each part's colour, font and text size from a name the brand gives a value to, never from a fixed value. So another brand still reaches every part.
3. The developer uses the local component in the piece's content, filled as a library component is.
4. The system checks the local component, and draws the piece with it.

**Variants:**

- **1a.** The visual needs what data cannot say, such as items set around a circle. The developer writes a helper script, which runs while the piece is prepared, never while it is drawn. The script writes the local component as data, with every text taken from the content. The path goes on at step 3.
- **4a.** The local component holds a fixed colour, or a helper script wrote a text that is not in the content. The system refuses it and names each spot. The developer mends it, and the path rejoins at step 4.
- **4b.** An input of a helper script was edited since the script wrote the local component. The system says the local component is out of date, and the developer runs the script again.
- **4c.** The same visual is needed in other pieces. The developer moves it into a library the project owns. Its fixed texts become content fields, and its one-time choices become options. Each piece then moves to it after the developer sees the piece before and after ([UC-110](../020-build-libraries/UC-110-add-library-component.md), variants 1a and 4a).

**Postconditions:** The system draws the new visual in the piece from data, in the piece's brand and in each of its languages.

**Minimal guarantees:**

- No code runs while the piece is drawn.

## Sources

- **The goal:** drawn on 30 October, in planning the capability (#2423), from the maintainer's choice that a kind of visual is data only. The Friday talk needed 19 kinds of visual for its 24 slides. The goal rests on components being data, with a local component made inside one piece for that piece alone ([DEC-001 point 4](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#4-components-are-data-and-the-engine-knows-none-by-name)).
- **The steps and the guarantee:**
  - **Steps 1 and 3:** a local component is the same kind of data as a library component. It repeats, lines up and sizes its parts with the engine's tools ([DEC-001 point 4](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#4-components-are-data-and-the-engine-knows-none-by-name) and DEC-005 points [1](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-005-engine-and-plugins.md#1-a-formula-is-arithmetic-and-stays-arithmetic), [2](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-005-engine-and-plugins.md#2-layout-operators-arrange-and-connectors-route-simply) and [3](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-005-engine-and-plugins.md#3-an-element-asks-for-a-size-and-gets-one-and-references-never-loop)).
  - **Step 2 and variant 4a:** a component names roles, and only a brand holds a raw value ([DEC-001 point 5](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#5-libraries-hold-values-structure-or-meaning)).
  - **Step 4:** the capability's check is one validator of the project's validation ([DEC-002 point 6](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-002-files-and-validation.md#6-the-check-is-one-validator-of-the-projects-validation)).
  - **Variant 1a, variant 4a and the guarantee:** a helper script runs while the piece is prepared, never inside the engine. The local component it writes takes its text from the content ([DEC-001 point 8](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#8-what-the-engine-cannot-compute-is-computed-while-preparing) and [DEC-006 point 1](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-006-work-outside-the-engine-and-outputs.md#1-a-program-run-while-preparing-may-write-a-picture)).
  - **Variant 4b:** a fingerprint says when such output is stale, and a stale local component asks for attention (DEC-006 points [5](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-006-work-outside-the-engine-and-outputs.md#5-a-fingerprint-says-when-output-is-stale-and-the-rest-is-only-recorded) and [8](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-006-work-outside-the-engine-and-outputs.md#8-what-the-check-reports-and-how-seriously)).
  - **Variant 4c:** a library component's options are declared, and a person moves a piece's lock after a before-and-after (DEC-001 points [6](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#6-a-pattern-arranges-items-and-an-item-says-what-it-is) and [7](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#7-a-pieces-libraries-change-only-when-a-person-moves-its-lock), and [DEC-003 point 8](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md#8-a-pieces-state-says-who-moves-its-lock)).
