---
id: UC-111
title: Have a piece designed and judged by the principles of visual communication
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
requirements: []
shortfalls:
  - at: 2
    issue: "#2584"
    record: visual-communication:DEC-001#1
  - at: 4
    issue: "#2584"
    record: visual-communication:DEC-001#1
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/visual-communication/agents/graphic-design-reviewer.md
        - .pkit/capabilities/visual-communication/scripts/look.py
        - .pkit/capabilities/visual-communication/schemas/piece.schema.json
      record:
        - visual-communication:DEC-001#1
        - visual-communication:DEC-001#3
        - visual-communication:DEC-015#1
        - visual-communication:DEC-015#7
        - COR-017
---

# UC-111 — Have a piece designed and judged by the principles of visual communication

**Goal:** Have a piece designed and judged by the principles of visual communication, so it says the right thing and looks right without my project writing those principles again.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): designs the piece for the developer, and reviews it. A rule it judges by must be one the capability ships, so the developer can see what it judged by.

**Preconditions:** None.

**Assumptions:**

- The project has visual-communication installed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).

**Trigger:** The developer has a piece to make, such as a talk, and wants each page to make its point to the audience.

**Main path:**

1. The developer asks the AI agent for a piece. The developer says who the piece is for, where it is shown, and whether it explains.
2. The AI agent designs the piece by the rules of visual communication that the capability ships: what each page says, and how it looks.

> [!WARNING]
> **Not built yet:** no agent or skill of the capability designs a piece by such rules. [DEC-001 point 1](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#1-what-the-capability-is-for) decides that the capability carries its view of good visual communication as rules, with agents that make and review pieces, and #2584 tracks the agents.

3. The system draws each page of the piece as an image, with `pkit visual look`.
4. A reviewer reads the drawn pages as the piece's audience would. It reports each break of a rule as a finding that names the rule and the page.

> [!WARNING]
> **Not built yet:** the reviewer reports faults and notes on the drawn pages, and judges no rule. DEC-001 point 1 decides that a reviewer judges the rules, and #2584 tracks the reviewer that does.

5. The developer reads the piece and the findings, and decides which to mend.

**Variants:**

- **1a.** The piece does not explain, such as a map of a system or a board people fill in. A rule for pieces that explain does not judge it, and every other rule still does.
- **4a.** The harness cannot read images. The reviewer stops and says so, and judges nothing.
- **4b.** The reviewer reports a break. The AI agent mends the piece, and the path rejoins at step 3.

**Postconditions:** The piece is drawn, and each break of a rule the reviewer found is mended or left to the developer with its finding.

**Minimal guarantees:**

- The reviewer's report says which pages, languages and modes it looked at, so a page it did not read never reads as clean ([DEC-015 point 7](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-015-viewing-step-and-reviewer.md#7-the-reviewers-first-form)).
- The reviewer's findings join no validation and hold no merge, until a record gives them a place there (DEC-015 point 7).

## Open for the design

What the developer needs here that no accepted record decides yet:

- **The rules themselves,** and the reasons each rests on. A record of the capability decides them, and two rule sets hold them ([project-kit#2884](https://github.com/aleskalfas/project-kit/issues/2884)).
- **How the agents divide the work:** the agent that designs a piece, and what the reviewer judges beside its faults ([project-kit#2584](https://github.com/aleskalfas/project-kit/issues/2584)).
- **Rules that bind on a piece's content,** so that a change to a page's words is judged against them. That needs the content to be an artefact first ([project-kit#2416](https://github.com/aleskalfas/project-kit/issues/2416)).
- **The review at the merge,** where a finding of a rule could hold a change ([project-kit#2676](https://github.com/aleskalfas/project-kit/issues/2676)).

## Sources

- **The goal:** the maintainer decided on 31 October, in planning the capability (#2423), that these rules are no project's taste but known principles of good design. In his words as the planning recorded them, nobody wants the opposite, and no adopter should have to write them again. So the capability ships them, each with its source, and adopters add their own on top. The goal rests on the capability carrying its view of good visual communication as rules a reviewer judges ([DEC-001 point 1](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#1-what-the-capability-is-for)).
- **The steps and the guarantees:**
  - **Step 1:** a piece declares who it is for, where it is shown and whether it explains ([DEC-001 point 3](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#3-a-piece-and-its-content)).
  - **Steps 2 and 4:** the capability carries its view of good visual communication as rules a reviewer judges, and agents that make, review and translate pieces ([DEC-001 point 1](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#1-what-the-capability-is-for)).
  - **Step 3:** the viewing step draws what a renderer drew for each page as an image ([DEC-015 point 1](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-015-viewing-step-and-reviewer.md#1-the-viewing-step-draws-a-renderers-output-and-adds-nothing-to-the-seam)).
  - **Step 5, variants 4a and 4b, and the guarantees:** the reviewer advises, reads images and stops where the harness reads none, and says which pages it looked at ([DEC-015 point 7](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-015-viewing-step-and-reviewer.md#7-the-reviewers-first-form)).
  - **Variant 1a:** a rule says in its wording which pieces it judges, as a rule for pieces that explain does, and a reviewer reads that from the piece's fields ([DEC-001](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md), "Why a piece declares what it is selected by").
