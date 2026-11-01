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

- **The goal:** drawn on 30 October, in planning the capability (#2423), from the maintainer's choice that a kind of visual is data only. The Friday talk needed 19 kinds of visual for its 24 slides.
- **The steps and the guarantee:** the capability's shared choices (#2424) on components, and on the formula language and the layout operators. Variant 1a follows the shared choice on helpers run while a piece is prepared. Variant 4b follows the one on a fingerprint of inputs. How variant 4c moves a local component into a library follows from these choices and from a piece's lock.
- **No accepted record decides them yet.** The capability's records, written under #2427, will decide them. The use case then anchors each record, and its steps follow them.
