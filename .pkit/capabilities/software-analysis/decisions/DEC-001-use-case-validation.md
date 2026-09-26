---
id: DEC-001
title: Validate a design by walking numbered use cases before filing its work
status: proposed
date: 2026-09-26
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

Before a design becomes work items, someone has to answer "do we have everything we need?" Today that is answered from memory and by review. Reviewers judge the design as described; the author trusts the description is complete. Both catch what is *wrong*. Neither reliably catches what is *missing*, because a missing piece leaves no text to review.

The gap shows when a user has to cross several parts of a system to get something done — a command, a guard in a second command, a check in continuous integration, a behaviour of an agent. Each part can be reviewed and found sound while the path through them is broken. Walking a concrete situation through the parts finds that: the walk stops where the path does. In practice such walks find holes review passes missed, because the reviewers judged the parts and the walk *ran* them.

The walks themselves are not kept. They happen in conversation, get used once, and are lost. Work items carry per-item acceptance criteria, not the cross-item story. Decision records carry the *why*, not *what it looks like when it works*. Scratchpad notes explore and then retire. The next person asking "how do I do X with this?" or "did we ever handle situation Y?" has to reconstruct the walk.

This capability exists to hold the analysis artifacts a project uses to decide *what* is needed before building it. This record establishes its first: the **use case**, and the rule that uses it.

## Decision

**When getting from a situation to an outcome crosses more than one part of the system, the design is validated by walking numbered use cases through it before its work is filed. The use cases are kept, cited by the work's success criteria, and re-walked when that work closes.**

1. **The artifact.** A **use-case set** holds one design's use cases, numbered `UC-NNN-<slug>` within the project, so a citation survives a retitle. Each use case inside carries a short number that is **append-only**: use cases may be added, revised, or marked withdrawn, never renumbered — a check against the set's history enforces it. A use case states the **actor** (a named role), the **situation** they are in, **what they do**, **what must be observable** afterwards, and **what the design exercises** to get there. Each use case records the state it was **last walked against**. The set carries a **gap log** — what walks found missing or contradictory and what changed in response. The gap log is never empty: "no gaps found" is written out, so the absence of findings is a claim, not a silence. It is appended to at every walk, not only the first. The template lives in this capability's README.

2. **When the rule applies — seams crossed.** The test is not files touched but seams crossed: does the actor cross more than one boundary between parts — a command, a check, a record, a role — to get from the situation to the outcome? A change touching three files behind one command crosses one seam and is exempt; its acceptance criteria already are its use case. A change adding one command plus a guard another command must honour crosses two and is not.

3. **The rule.** For a design the test catches, the use-case set is written, walked, and merged to the default branch **before** its work items are filed. Each work item names the use cases it satisfies; the design's success criteria are stated as use cases passing. That gives two completeness readings. *Every use case is claimed by some work item* is a **check** — an unclaimed use case is a hole. *Every work item serves some use case* is a **review prompt** — an item serving none is suspect, but the judgment stays human. When a work item closes, its owner **re-walks** the use cases it claims against the real system, updates their *last walked against*, and appends to the gap log wherever the walk and the set disagree — either the set was wrong and is edited, or the work was wrong and is fixed.

4. **Normative within this capability; enforcement is the filer's.** A project that installs this capability adopts the rule. Refusing to file until a set exists belongs to whatever component files work in that project, and is that component's decision. Without such a component the rule still binds; it is just not checked mechanically.

5. **A use case is not a decision.** A use-case set has no status, is never accepted or superseded, and is edited in place as its design evolves. It borrows the decision records' numbering discipline and uniqueness check, not their statuses or acceptance gate (both defined in the decision-record specification, `.pkit/decisions/README.md`). Citing a use case commits the citer to nothing but the story.

6. **Where sets live.** Use-case sets are **project-owned** design documents, kept at a project-configurable location **outside this capability's subtree** — by default alongside the project's other design documentation. They are never touched by sync, and uninstalling the capability leaves them in place: the capability owns the discipline, not the project's designs. This capability ships no sets of its own and defines no home for other capabilities to ship sets in; that waits for a concrete need.

7. **Citations.** A set is cited bare, `UC-003`; a trailing `/<n>` cites one use case in it, `UC-003/5`. Only the project's own content cites use cases — content shipped by any capability never does, since it cannot know an adopter's sets. The core reference checks do not know this token; this capability's own checks resolve both halves and report a set or use case that does not exist.

8. **Relation to neighbouring artifacts.** A **storyboard** (COR-016) scripts one agent's turns through a scripted interaction; a use case is the level above — it says what must be true across commands, checks, records and roles, and does not care who says what. A storyboard may implement the agent-facing part of a use case and cites it when it does. A **scratchpad note** (COR-012) explores an open question and retires; a use-case set validates a design and persists as its living description. A work item's **acceptance criteria** stay per-item and cite use cases rather than restate them. A **decision record** carries the choice and its reasons, and may state which use cases it was validated against.

9. **Executable use cases are deferred.** Use cases are walked by a person. Making them executable — a file that reads as the story and runs as a check — waits until hand-walking has shown, across more than one design, which parts of a use case can be checked mechanically at all.

## Rationale

**Why a walk, and why before filing.** Review finds errors of reasoning; a walk finds *absences* — the command that does not exist, the state two rules disagree about, the gesture nobody wrote down. Absences are cheapest to fix before work is filed and most expensive when half-built, so the walk sits where a design turns into work, not at delivery. Merging the set first is what lets work items cite it without predicting an id.

**Why a rule and not a recommendation.** A missing storyboard is visible — the agent body reads thin and a reviewer can say so. A missing use case is invisible *by construction*: the author believes the design complete, which is exactly why no one walks it, and nothing on the page shows the hole. A recommendation is declined in precisely the case it exists for. The seams-crossed test keeps the rule from biting where a walk has nothing to find.

**Why keep them.** The walk's output is what the next reader needs, whether checking delivered work, extending the design, or asking how to do the thing. Inside the design's record it would swamp the decision; spread across work items it would fragment and scroll away as items close. A persistent artifact keeps the story whole.

**Why numbered, and why append-only inside.** Use cases are cited from success criteria and records that outlive any one filing; a title can change, a number cannot drift. Use case 5 must mean the same thing in the filing that cited it and in the re-walk a month later — renumbering to tidy a set would silently retarget every citation. Concurrent authors can collide on a set number; sets are rare, one per design, and the uniqueness check catches it.

**Why the gap log is mandatory and living.** It is the evidence the walk happened and had teeth. A set with no findings either validated a design already complete, or was written after the fact to match what got built; requiring "no gaps found" makes the second a false statement instead of a silence. Appending at every re-walk gives close-time findings a home, and *last walked against* makes staleness readable.

**Why no status.** A use case describes what should be true; it does not choose among alternatives, and nothing downstream is gated on accepting it. A status would let the acceptance gate block a walk on ceremony.

**Why "use case".** The term names this shape in established practice — actor, situation, path, observable outcome, and the extensions where the path fails. "Scripted scenario" already belongs to storyboards, and "user story" is commonly read as a backlog item, which work items already are.

**Why a capability.** The rule fails universal applicability (COR-014): a small project whose changes rarely cross more than one seam gains nothing from it and should not carry it. An opt-in discipline that some projects need and others do not is what a capability is (COR-017).

**Why outside the capability's subtree.** Uninstalling a capability removes its directory. Configuration kept there is cheap to lose; a project's design documents are not. Keeping the sets with the project's own documentation makes them survive any lifecycle operation on the capability, and keeps "the discipline" and "the designs it produced" owned by different parties, as they are.

### Alternatives considered

- **Walk in conversation and file the results as acceptance criteria.** Rejected — the status quo; the cross-item story is lost when the conversation ends, and completeness cannot be read off criteria scattered across items.
- **Extend storyboards to cross-artifact walks.** Rejected — a storyboard is bound to one implementing artifact and scripts its dialogue; stretched across commands, checks and records it loses what makes it useful and still gives the design-level story no home.
- **Bind the set to the design's record or tracking work item.** Rejected — a design often spans several records, and work items close; the set must outlive both.
- **Keep use cases as scratchpad notes.** Rejected — scratchpad notes retire when their question resolves; use cases must outlive delivery to be re-walked.
- **A core methodology record and area instead of a capability.** Rejected — a universal rule would bind every adopter to a practice many do not need.
- **Keep sets in the capability's project-owned subdirectory.** Rejected — uninstalling the capability removes that directory with everything in it, and nothing in the uninstall path protects the sets.
- **Let capabilities ship use-case sets validating their own design.** Deferred — no capability needs it yet, and it would add an undeclared dependency and a second citation form.
- **Slug-only sets.** Rejected — rename safety would rest on every citer maintaining a list; numbers give it on machinery the project already runs.
- **Name it "scenario" or "user story".** Rejected — both already mean something else (see Rationale).
- **Ship executable use cases now.** Rejected — which parts are mechanically checkable is unknown until several have been walked by hand.

## Implications

- **Tooling.** This capability's README documents the template, the default location, and the commands that stamp, check and resolve use-case sets; the pairing of an authoring command with a skill follows the methodology's skill-and-command rule (COR-005).
- **Filing components may adopt the rule.** A component that turns designs into work items may walk or have authored the set before slicing, name per item which use cases it satisfies, and reject a citation to a use case not present on the default branch. If it does, it records that adoption in its own decisions; this record does not impose it.
