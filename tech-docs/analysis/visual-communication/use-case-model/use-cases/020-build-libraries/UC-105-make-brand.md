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
5. For each axis, the developer says whether its modes alter only colours, or also sizes and spacing, such as a device.
6. The developer adds how the brand draws each layout of each kind of piece it serves.
7. The system checks that the brand draws each layout of each kind of piece it serves, with the slots that kind names.

**Variants:**

- **2a.** A renderer lacks the brand's fonts, such as an online board. The developer names the fonts the brand uses in that renderer, and a font to use instead of a monospace font.
- **3a.** Other brands are meant to build on this one, such as an online platform's brand that each of its games restyles. The developer lists which of its named values a brand built on it may alter ([UC-106](UC-106-build-brand-on-brand.md)).
- **6a.** A part of the look has a form of the brand's own, unlike any library component of the starter library. The brand keeps it as a library component of its own. Otherwise the brand gives values to a library component of the starter library, and never copies it.

**Postconditions:** A piece that names the brand is drawn in its look, in each mode of each of its axes.

**Minimal guarantees:** None.

## Open for the design

What the developer needs here that no accepted record decides yet:

- **What a mode may alter.** Where the developer marks an axis whose modes alter sizes, and what such a mode may alter, such as spacing or the sizes of text.

## Sources

- **The goal:** none of the note's thirteen candidates makes a brand. This use case writes point 27 of the planning note `2026-10-30-visual-work-capability`, on modes on several axes, for whoever makes the brand. On 1 November the maintainer named a colour scheme, a device, an audience and a contrast as axes, for an online game platform.
- **Its approval:** point 27 was decided under the maintainer's delegation, and he approved it with the plan of #2423 the same day.
- **The steps:** the decisions the note records in its points 4g, 8, 18b, 18d and 27.
- **No accepted record decides them yet.** The capability's records, written under #2427, will decide them. The use case then anchors each record, and its steps follow them.
