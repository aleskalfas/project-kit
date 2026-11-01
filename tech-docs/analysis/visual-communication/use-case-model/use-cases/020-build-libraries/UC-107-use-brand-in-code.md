---
id: UC-107
title: Use a brand's values in code
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
requirements: []
after:
  - [UC-105, UC-106]
pkit:
  friction:
    anchors:
      record:
        - COR-017
        - COR-013
---

# UC-107 — Use a brand's values in code

**Goal:** Use a brand's values in the code of a web page, a game or an app that must look like my project's pieces.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): does the work for the developer, and may run any step the developer runs.

**Preconditions:** **From [UC-105](UC-105-make-brand.md), or [UC-106](UC-106-build-brand-on-brand.md):** The brand is in the project.

**Assumptions:**

- The project has visual-communication installed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).

**Trigger:** Code outside the pieces must look like them, such as a web page, or a game board drawn live in 3D.

**Main path:**

1. The developer asks for the brand's values as code, in a form the target reads, such as CSS variables for a web page.
2. The system writes each value of the brand, in each mode, under the name that one naming rule gives it in code.
3. The system names each value it could not write in that form.
4. The developer uses the written code in the page, the game or the app.

**Variants:**

- **1a.** The target is a program that reads data, such as a game's runtime. The developer asks for the values as data, each set named by the modes it holds.

**Postconditions:** The code holds the brand's values in each mode, named by the same rule for every target.

**Minimal guarantees:** None.

## Open for the design

What the developer needs here that no accepted record decides yet:

- **The naming rule.** The one rule that names each value in code.
- **Where the written code goes.** Whether it is committed, and whether it is numbered as an export is.

## Sources

- **The goal:** point 28 of the planning note `2026-10-30-visual-work-capability`, from the online game platform the maintainer described on 1 November. The platform is an example only, and nothing of a game is built.
- **Its approval:** point 28 was decided under the maintainer's delegation, and he approved it with the plan of #2423 the same day.
- **The steps:** the decisions the note records in its point 28.
- **No accepted record decides them yet.** The capability's records, written under #2427, will decide them. The use case then anchors each record, and its steps follow them.
