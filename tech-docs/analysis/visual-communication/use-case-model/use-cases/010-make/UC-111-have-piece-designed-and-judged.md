---
id: UC-111
title: Have a piece designed and judged by the principles of visual communication
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
requirements: []
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/visual-communication/agents/graphic-design-reviewer.md
        - .pkit/capabilities/visual-communication/agents/graphic-designer.md
        - .pkit/capabilities/visual-communication/agents/graphic-sketcher.md
        - .pkit/capabilities/visual-communication/scripts/look.py
        - .pkit/capabilities/visual-communication/scripts/render.py
        - .pkit/capabilities/visual-communication/skills/visual-author/build-loop.md
        - .pkit/capabilities/visual-communication/schemas/piece.schema.json
      record:
        - visual-communication:DEC-001#1
        - visual-communication:DEC-001#3
        - visual-communication:DEC-015#1
        - visual-communication:DEC-015#4
        - visual-communication:DEC-015#7
        - visual-communication:DEC-028#2
        - visual-communication:DEC-028#3
        - visual-communication:DEC-028#4
        - visual-communication:DEC-028#5
        - visual-communication:DEC-030#2
        - visual-communication:DEC-030#3
        - visual-communication:DEC-070#1
        - visual-communication:DEC-070#2
        - visual-communication:DEC-070#3
        - visual-communication:DEC-070#4
        - visual-communication:DEC-071#1
        - visual-communication:DEC-071#2
        - visual-communication:DEC-071#3
        - visual-communication:DEC-071#4
        - visual-communication:DEC-071#5
        - visual-communication:DEC-071#6
        - COR-017
---

# UC-111 — Have a piece designed and judged by the principles of visual communication

**Goal:** Have a piece designed and judged by the principles of visual communication, so it says the right thing and looks right without my project writing those principles again.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): designs the piece for the developer, and reviews it.

**Preconditions:** None.

**Assumptions:**

- The project has visual-communication installed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).

**Trigger:** The developer has a piece to make, such as a talk, and wants each page to make its point to the audience.

**Main path:**

1. The developer asks the AI agent for a piece. The developer says who the piece is for, where it is shown, and whether it explains.
7. For a presentation, the AI agent has a session of its own draw a sketch of every page, outside the engine. The session has only the developer's words, the takeaways and where the piece is shown. It has no method, no design knowledge, no library and no brand.
2. The AI agent designs the piece by the rules of visual communication: what each page says, and how it looks. For a presentation, it rebuilds the sketch as the piece by its method, with the brand and the libraries. Where they cannot carry a part, it draws the nearest that keeps the part's meaning, and where nothing near keeps it, it stops on that part and says what is missing. It writes what each page must show into the piece's brief, and the reason for each choice of its design.
3. The system renders the piece, and draws each of its pages as an image, with `pkit visual render` and `pkit visual look`.
4. A reviewer reads every drawn page, and reports each break of a rule as a finding that names the rule and the page.
5. The AI agent mends once each fault, each brief finding, each break a rule's text settles, each fact its source contradicts, and each thing the reviewer says a reader cannot make out where the piece is shown, such as a difference told by colour alone. The system draws the piece again, and the reviewer reads every page again.
6. The developer reads the piece beside its sketch, where it has one, and the reviewer's second report, and decides whether the piece ships.

**Variants:**

- **1a.** The piece does not explain, such as a map of a system or a board people fill in. A rule for pieces that explain does not judge it.
- **4a.** The harness cannot read images. The reviewer stops and says so, and judges nothing on the drawn pages.
- **5a.** The AI agent judges a finding wrong, such as a fault it reads as meant. It leaves the finding and says why, and the reviewer reads that page again.
- **6a.** The developer asks the AI agent for mends, rather than ship the piece. The AI agent mends what the developer names, the system draws the piece again, and the reviewer reads every page again. The path rejoins at step 6.
- **7a.** The developer has the AI agent skip the sketch. The path goes on at step 2, and the AI agent designs the piece in the engine from the start.
- **7b.** The piece is of another kind of work, such as a figure or a poster, and the developer asks for a sketch on it. The piece starts with a sketch, as a presentation does.

**Postconditions:** The piece is drawn, and the developer holds it with the reviewer's second report. Each finding the round mends is mended, or left with the AI agent's reason, and each other finding waits for the developer.

**Minimal guarantees:**

- The reviewer's report says which pages, languages and modes it looked at, so a page it did not read never reads as clean ([DEC-015 point 7](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-015-viewing-step-and-reviewer.md#7-the-reviewers-first-form)).
- The reviewer's findings join no validation and hold no merge, until a record gives them a place there (DEC-015 point 7).
- The AI agent never makes the ship call, and never changes the developer's words without the developer's word (DEC-070 points [1](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-070-ship-call-and-one-round.md#1-the-person-makes-the-ship-call-and-the-review-informs-it) and [4](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-070-ship-call-and-one-round.md#4-whose-words-the-designer-changes-alone-and-what-it-asks)).

## Open for the design

What the developer needs here that no accepted record decides yet:

- **Rules that bind on a piece's content,** so that a change to a page's words is judged against them. That needs the content to be an artefact first ([project-kit#2416](https://github.com/aleskalfas/project-kit/issues/2416)).
- **The review at the merge,** where a finding of a rule could hold a change ([project-kit#2676](https://github.com/aleskalfas/project-kit/issues/2676)).

## Sources

- **The goal:** the maintainer decided on 31 October, in planning the capability (#2423), that these rules are no project's taste but known principles of good design. In his words as the planning recorded them, nobody wants the opposite, and no adopter should have to write them again. So the capability ships them, each with its source, and adopters add their own on top. The goal rests on the capability carrying its view of good visual communication as rules a reviewer judges ([DEC-001 point 1](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#1-what-the-capability-is-for)).
- **The steps and the guarantees:**
  - **Step 1:** a piece declares who it is for, where it is shown and whether it explains ([DEC-001 point 3](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#3-a-piece-and-its-content)).
  - **Step 7:** a new presentation, or one redesigned whole, starts with a sketch of every page. A session the designer starts draws it outside the engine, from only the piece's words, its takeaways and where it is shown. The session has no method, no design knowledge, no library and no brand ([DEC-071 point 1](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-071-sketch-and-rebuild.md#1-a-new-presentation-starts-with-a-sketch-which-the-sketch-session-draws)). The session's agent is `graphic-sketcher` (`.pkit/capabilities/visual-communication/agents/graphic-sketcher.md`). The sketch draws the words as given, with the takeaways the asker's text states ([DEC-071 point 2](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-071-sketch-and-rebuild.md#2-the-sketch-draws-the-pieces-words-as-given-and-the-rebuild-puts-them-in-the-content)). It is kept in the agent workspace, and never committed ([DEC-071 point 3](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-071-sketch-and-rebuild.md#3-the-sketch-is-kept-in-the-agent-workspace-never-committed)).
  - **Variants 7a and 7b:** the person may have the designer skip the sketch on any piece. A piece of another kind of work starts with a sketch only on the person's word (DEC-071 point 1).
  - **Step 2:** the capability's designer turns a piece's brief into a piece. It writes the brief's goals and relations from what whoever asked for the piece says, and shows them to that person before it designs against them. It writes a reason for each choice as it designs ([DEC-030 point 2](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-030-design-agents.md#2-the-designer-turns-a-brief-into-a-piece)). It names the content's structure before it chooses a form, and makes its choices in the order of the brief's aspects ([DEC-030 point 3](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-030-design-agents.md#3-the-designers-method)). The agent is `graphic-designer` (`.pkit/capabilities/visual-communication/agents/graphic-designer.md`).
  - **Step 2, for a presentation:** the designer rebuilds the sketch at once as the piece, by its method, with the piece's brand and the project's libraries. The form is the sketch's, which the rebuild keeps unless it bends the content's meaning ([DEC-071 point 4](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-071-sketch-and-rebuild.md#4-the-designer-rebuilds-the-sketch-at-once-by-its-method)). Where nothing the designer may use draws a part as the sketch does, the rebuild draws the nearest that keeps the part's meaning. What was lacking goes to its owner, as a request or a need ([DEC-071 point 5](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-071-sketch-and-rebuild.md#5-what-the-rebuild-cannot-carry-is-drawn-as-a-stand-in-and-reaches-its-owner)).
  - **Steps 2 and 4:** the capability carries its view of good visual communication as rules a reviewer judges, and agents that make, review and translate pieces ([DEC-001 point 1](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md#1-what-the-capability-is-for)). Two rule sets hold the rules: `COMM` on what a piece says, and `GRAPHIC` on how it looks ([DEC-028 point 2](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-028-principles-of-visual-communication.md#2-two-sets-by-the-kind-of-failure)). Each rule says apart what the content's text shows and what only the drawn page shows ([DEC-028 point 4](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-028-principles-of-visual-communication.md#4-each-rule-says-apart-what-the-text-shows-and-what-the-drawing-shows)). Until a piece's content is an artefact, the rules bind on no piece, and guide whoever designs or judges it ([DEC-028 point 5](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-028-principles-of-visual-communication.md#5-where-the-rules-bind-and-how-they-guide-meanwhile)). The reviewer reports a break of a rule as a rule finding, which cites the rule and names the page ([DEC-015 point 7](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-015-viewing-step-and-reviewer.md#7-the-reviewers-first-form)).
  - **Step 3:** the viewing step draws what a renderer drew for each page as an image ([DEC-015 point 1](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-015-viewing-step-and-reviewer.md#1-the-viewing-step-draws-a-renderers-output-and-adds-nothing-to-the-seam)), under the lock a render wrote ([DEC-015 point 4](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-015-viewing-step-and-reviewer.md#4-it-reads-under-the-lock-and-writes-nothing-committed)).
  - **Variant 4a and the guarantees on the reviewer:** the reviewer advises, reads images and stops where the harness reads none, and says which pages it looked at (DEC-015 point 7).
  - **Steps 5 and 6, variants 5a and 6a, and the guarantee on the ship call:** the designer's loop is one round. The reviewer reads every page, the designer mends once each fault, each brief finding, each settled break, each fact its source contradicts and each thing a reader cannot make out where the piece is shown, and the reviewer reads every page again ([DEC-070 points 2](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-070-ship-call-and-one-round.md#2-the-designers-loop-is-one-round) and 3). The person makes the ship call at every level, and the review informs it with findings alone, with no grade and no verdict ([DEC-070 point 1](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-070-ship-call-and-one-round.md#1-the-person-makes-the-ship-call-and-the-review-informs-it)). The designer changes alone every word that is not the asker's, whatever the delegation setting says ([DEC-070 point 4](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-070-ship-call-and-one-round.md#4-whose-words-the-designer-changes-alone-and-what-it-asks)).
  - **Step 6, for a sketched piece:** the round runs on the rebuilt piece, and the review is not handed the sketch. At the ship call the person sees the sketch beside the piece, and may ask for mends toward it ([DEC-071 point 6](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-071-sketch-and-rebuild.md#6-the-round-runs-on-the-rebuilt-piece-and-the-person-sees-the-sketch-beside-it-at-the-ship-call)).
  - **Variant 1a:** a rule says in its wording which pieces it judges, as a rule for pieces that explain does, and a reviewer reads that from the piece's fields ([DEC-001](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md), "Why a piece declares what it is selected by"). `COMM` judges only a piece that explains, and `GRAPHIC` every piece ([DEC-028 point 3](../../../../../../.pkit/capabilities/visual-communication/decisions/DEC-028-principles-of-visual-communication.md#3-which-pieces-each-set-judges)).
