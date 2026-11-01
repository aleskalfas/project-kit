---
id: UC-106
title: Build a brand on another brand
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
requirements: []
after:
  - [UC-105]
pkit:
  friction:
    anchors:
      record:
        - COR-017
        - COR-013
---

# UC-106 — Build a brand on another brand

**Goal:** Build a brand on another brand, changing only what that brand lets me change, and give my brand versions of its own.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): does the work for the developer, and may run any step the developer runs.

**Preconditions:** **From [UC-105](UC-105-make-brand.md):** The brand to build on exists, and lists what a brand built on it may alter.

**Assumptions:**

- The project has visual-communication installed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).

**Trigger:** A look must differ from another look and stay inside it, such as a game restyling the controls of its platform.

**Main path:**

1. The developer starts a brand that names the brand it builds on, and the major version of that brand it fits.
2. The developer gives new values to what the brand it builds on lets it alter.
3. The system checks the new brand, and names each value it gives that the brand it builds on does not list.
4. The developer gives the new brand versions of its own, apart from the brand it builds on.
5. A piece that names the new brand is drawn in its values, with the layouts and library components of the brand it builds on.

**Variants:**

- **3a.** The new brand gives a value that the brand it builds on does not list. The developer removes the value, or asks the owner of that brand to list it, and the path rejoins at step 3.
- **5a.** A piece uses two libraries that fit different major versions of one brand. The system says that the two cannot be used in one piece.

**Postconditions:** The new brand differs from the brand it builds on only in what that brand lets it alter.

**Minimal guarantees:**

- A brand built on another never replaces that brand's layouts or library components.

## Open for the design

What the developer needs here that no accepted record decides yet:

- **Longer chains.** Whether a brand may build on a brand that itself builds on another, or on two brands at once.
- **What a brand built on another adds.** Whether it may add layouts, axes or parts of its own.

## Sources

- **The goal:** point 26 of the planning note `2026-10-30-visual-work-capability`, from the online game platform the maintainer described on 1 November. The platform is an example only, and nothing of a game is built.
- **Its approval:** point 26 was decided under the maintainer's delegation, and he approved it with the plan of #2423 the same day: "ok go ahead".
- **The steps and the guarantee:** the decisions the note records in its points 4g, 4i and 26.
- **No accepted record decides them yet.** The capability's records, written under #2427, will decide them. The use case then anchors each record, and its steps follow them.
