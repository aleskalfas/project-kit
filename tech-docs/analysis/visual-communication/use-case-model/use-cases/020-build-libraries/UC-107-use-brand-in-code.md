---
id: UC-107
title: Use a brand's values in code
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
requirements: []
after:
  - [UC-105, UC-106, UC-109]
pkit:
  friction:
    anchors:
      record:
        - visual-communication:DEC-001#9
        - visual-communication:DEC-002#1
        - visual-communication:DEC-004#3
        - visual-communication:DEC-004#4
        - visual-communication:DEC-004#5
        - visual-communication:DEC-005#7
        - visual-communication:DEC-005#9
        - visual-communication:DEC-006#4
        - COR-017
        - COR-013
---

# UC-107 — Use a brand's values in code

**Goal:** Use a brand's values in the code of a web page, a game or an app that must look like my project's pieces.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): does the work for the developer, and may run any step the developer runs.

**Preconditions:** **From [UC-105](UC-105-make-brand.md), [UC-106](UC-106-build-brand-on-brand.md), or [UC-109](UC-109-take-in-shared-library.md):** The brand is in the project.

**Assumptions:**

- The project has visual-communication installed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).

**Trigger:** Code outside the pieces must look like them, such as a web page, or a game board drawn live in 3D.

**Main path:**

1. The developer declares that the brand be written out as code, in a form the target reads, such as CSS variables for a web page. The declaration names where the code goes, and locks the brand's library version.
2. The system writes each value the brand exports, in each mode, under the name that one naming rule gives it in code. It writes the code where the declaration names, with no number, since the declaration's lock says what the code holds.
3. The system names each value it could not write in that form.
4. The developer uses the written code in the page, the game or the app.

**Variants:**

- **1a.** The target is a program that reads data, such as a game's runtime. The developer declares the values as data, each set named by the key of the modes it holds.
- **2a.** The project commits no written code, as it commits no other output of its own build. On a clone without it, the system states that the code is missing, and names the command that writes it.

**Postconditions:** The code holds the values the brand exports, in each mode, named by the same rule for every target.

**Minimal guarantees:** None.

## Sources

- **The goal:** a brand written out as code, from the online game platform the maintainer described on 1 November. The platform is an example only, and nothing of a game is built. The goal rests on code outside the capability, such as a game's, which reads a brand's values written out as code ([DEC-001 point 9](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#9-what-is-outside-the-capability)).
- **Its approval:** a brand written out as code was decided under the maintainer's delegation, and he approved it with the plan of #2423 the same day.
- **The steps:**
  - **Step 1:** a brand written out as code is declared like a piece, in a file of the capability's location. The declaration names the code writer, where the code goes and a lock ([DEC-005 point 7](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-005-engine-and-plugins.md#7-the-engine-owns-one-document-of-a-brands-resolved-values) and [DEC-002 point 1](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-002-files-and-validation.md#1-the-capabilitys-files-and-the-projects-work-lie-apart)).
  - **Step 2:** the names a brand exports are public, and one naming rule turns them into names in code. The code follows its declaration's lock, and takes no number (DEC-004 points [4](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-004-brands-and-notations.md#4-one-naming-rule-turns-a-brands-names-into-names-in-code) and [5](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-004-brands-and-notations.md#5-the-names-a-brand-exports-are-public), and [DEC-006 point 4](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-006-work-outside-the-engine-and-outputs.md#4-where-produced-output-and-written-code-live)).
  - **Step 3:** a code writer declares the kinds of value it has a form for, and reports what it lost in one form ([DEC-005 point 9](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-005-engine-and-plugins.md#9-three-kinds-of-plugin-share-one-pattern-and-one-loss-report)).
  - **Variant 1a:** the code writer for JSON writes the brand's resolved values, each combination of modes named by its key (DEC-005 point 7 and [DEC-004 point 3](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-004-brands-and-notations.md#3-one-key-names-a-combination-of-modes)).
  - **Variant 2a:** whether written code is committed is the project's choice. Where it is missing, the check states that as a fact, and names the command that writes it (DEC-006 point 4).
