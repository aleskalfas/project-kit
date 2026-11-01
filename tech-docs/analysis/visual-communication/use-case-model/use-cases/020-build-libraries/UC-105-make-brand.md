---
id: UC-105
title: Make a brand with modes on the axes it needs
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
requirements: []
pkit:
  friction:
    anchors:
      record:
        - visual-communication:DEC-001#5
        - visual-communication:DEC-004#1
        - visual-communication:DEC-004#2
        - visual-communication:DEC-004#6
        - visual-communication:DEC-004#9
        - visual-communication:DEC-007#4
        - COR-017
        - COR-013
        - COR-001
---

# UC-105 — Make a brand with modes on the axes it needs

**Goal:** Make a brand for a look, with its values in each mode of the axes it needs, such as a colour scheme or a device.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): does the work for the developer, and may run any step the developer runs.

**Preconditions:** None.

**Assumptions:**

- The project has visual-communication installed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).
- The brand stays in files of the project's own, apart from the capability's files ([COR-001](../../../../../../.pkit/decisions/core/COR-001-content-mechanisms.md)).

**Trigger:** The project's pieces need a look of their own, such as a company's colours, fonts and slide layouts.

**Main path:**

1. The developer starts a brand, as a library the project owns.
2. The developer gives the brand its values: colours, fonts, sizes, spacing, and pictures such as a logo.
3. The developer names the brand's axes, such as a colour scheme and a contrast. For each axis, the developer names its modes, such as light and dark, and its default mode.
4. For each mode, the developer gives the values that differ in it.
5. For each axis, the developer says whether its modes alter only colours and pictures, or any value, such as sizes, spacing and fonts.
6. The developer adds how the brand draws each layout of each kind of piece it serves.
7. The system checks that the brand draws each layout of each kind of piece it serves, with the content slots that kind names.

**Variants:**

- **2a.** A renderer lacks the brand's fonts, such as an online board. The developer names the fonts the brand uses in that renderer, and a font to use instead of a monospace font.
- **3a.** Other brands are meant to build on this one, such as an online platform's brand that each of its games restyles. The developer lists which of its named values a brand built on it may alter ([UC-106](UC-106-build-brand-on-brand.md)).
- **6a.** A part of the look has a form of the brand's own, unlike any library component of the starter library. The brand keeps it as a library component of its own. Otherwise the brand gives values to a library component of the starter library, and never copies it.

**Postconditions:** A piece that names the brand is drawn in its look, in each mode of each of its axes.

**Minimal guarantees:** None.

## Sources

- **The goal:** written for whoever makes a brand, from modes on several axes, one of the capability's shared choices (#2424). On 1 November the maintainer named a colour scheme, a device, an audience and a contrast as axes, for an online game platform. The goal rests on a brand's modes, which lie on axes that vary apart ([DEC-004 point 2](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-004-brands-and-notations.md#2-modes-lie-on-axes-and-each-axis-changes-values-or-sizes)).
- **Its approval:** modes on several axes were decided under the maintainer's delegation, and he approved them with the plan of #2423 the same day.
- **The steps:**
  - **Steps 1, 2 and 4:** a brand keeps its values as design tokens, and its modes in one document, in the format design tools share ([DEC-004 point 1](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-004-brands-and-notations.md#1-a-brands-values-are-design-tokens-in-the-dtcg-format)).
  - **Steps 3 and 5:** modes lie on axes, each with its default mode. An axis alters only values that move nothing, such as colours and pictures, or any value (DEC-004 points 1 and [2](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-004-brands-and-notations.md#2-modes-lie-on-axes-and-each-axis-changes-values-or-sizes)).
  - **Steps 6 and 7:** a brand holds how it draws the layouts of the kinds of piece it serves, and what it lacks is reported ([DEC-001 point 5](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#5-libraries-hold-values-structure-or-meaning)).
  - **Variant 2a:** the fonts a brand gives a group of renderers are a mode of one axis of sizes. Each such mode says how its fonts are measured (DEC-004 points 2 and [9](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-004-brands-and-notations.md#9-fonts-come-from-committed-files-and-a-missing-font-refuses-the-render)).
  - **Variant 3a:** a brand that others build on lists the roles they may give values ([DEC-004 point 6](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-004-brands-and-notations.md#6-a-brand-may-build-on-one-other-brand-within-the-roles-its-base-declares-open)).
  - **Variant 6a:** a generic form is a library component of the starter library, which a brand styles. A form one brand alone uses is that brand's own ([DEC-007 point 4](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-007-starter-library.md#4-the-form-to-the-starter-the-values-to-the-brand)).
