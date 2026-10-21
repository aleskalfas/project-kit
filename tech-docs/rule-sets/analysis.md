---
rule-set: ANA
version: 4.0.0
inherits: [WRITE@2, software-analysis:SAN@1]
scope:
  types: [software-analysis:actor, software-analysis:term, software-analysis:domain-model-view, software-analysis:use-case, software-analysis:journey]
rules:
  RS-ANA-001:
    status: proposed
    origin: {why: "A need or a goal in its actor's own voice reads as that actor speaking, as a user story states one (software-analysis DEC-001). In the trial, the ASD-STE100 rewrite kept no need's first person, and repeated the role's noun instead (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
    pkit:
      friction:
        anchors:
          record: ["software-analysis:DEC-001#1", "software-analysis:DEC-001#2"]
        revalidated:
          at: 2026-10-21T12:12:22Z
          outcome: unchanged
          unchanged-because: DEC-001 point 1 gains the Not built yet box and a use case's shortfalls. Needs and goals, and the voice they speak in, are untouched.
  RS-ANA-002:
    status: proposed
    origin: {why: "A kind's labels already have one home, which the check reads: its declared structure, with project-kit's additions to it as data (software-analysis DEC-001 point 1). A copy of the list here would drift from them."}
    fills: [RS-WRITE-002#labels]
    pkit:
      friction:
        anchors:
          artefact: [RS-WRITE-002]
  RS-ANA-003:
    status: proposed
    origin: {why: "A file listing shows the order in which areas build on each other only where their names carry it. Steps of 10 leave room for a new area between two, so no folder is renamed. The maintainer chose this form on 19 October (the design note on analysis concepts and order, PR #1808)."}
    pkit:
      friction:
        anchors:
          record: ["software-analysis:DEC-001#2", "software-analysis:DEC-001#12"]
        revalidated:
          at: 2026-10-20T22:11:43Z
          outcome: unchanged
          unchanged-because: DEC-001 point 2 changes only how it names the overview's folder. An area's folder name and its number are untouched, and an area's goal sits beside that name in the configuration.
  RS-ANA-007:
    status: proposed
    origin: {why: "A file listing shows the order in which the views build on each other only where their names carry it. Steps of 10 leave room for a new view between two, so no file is renamed. software-analysis leaves the number's form to each project (software-analysis DEC-004 point 4). The maintainer chose this form for project-kit's views on 19 October, with the areas' (the design note on analysis concepts and order, PR #1808)."}
    pkit:
      friction:
        anchors:
          record: ["software-analysis:DEC-004#4", "software-analysis:DEC-004#6"]
        revalidated:
          at: 2026-10-20T21:11:19Z
          outcome: unchanged
          unchanged-because: The change adds a flow to a view's opening. The number a view's file opens with, and what it means, are as before.
  RS-ANA-004:
    status: proposed
    origin: {why: "Each component owns its analysis, as it owns its decision records. A capability may move to a repository of its own (software-analysis DEC-001 point 2). On 19 October the maintainer decided that project-kit keeps one analysis for its core and one for each capability. The maintainer's delegate decided that an adapter keeps one once it needs one. The design note on analysis concepts and order records both (PR #1808)."}
    pkit:
      friction:
        anchors:
          record: ["software-analysis:DEC-001#2"]
        revalidated:
          at: 2026-10-20T22:11:45Z
          outcome: unchanged
          unchanged-because: DEC-001 point 2 calls the overview the reader's entry point. Each analysis keeps its own overview in its own folder, so where an artefact lies is untouched.
  RS-ANA-005:
    status: proposed
    origin: {why: "On 19 October, a map of project-kit's chain of use cases on main found five stages, each building on the ones before it. The maintainer took them as the core's areas (the design note on analysis concepts and order, PR #1808)."}
    pkit:
      friction:
        anchors:
          record: ["software-analysis:DEC-001#2", "software-analysis:DEC-001#12"]
        revalidated:
          at: 2026-10-20T22:11:47Z
          outcome: unchanged
          unchanged-because: DEC-001 point 2's change names the overview's folder as the reader's entry point. The core's five areas, and where its use cases lie, are untouched.
  RS-ANA-006:
    status: proposed
    origin: {why: "A link at the version a capability requires of another component names the definitions the capability was written against. software-analysis leaves the links' version to each project (software-analysis DEC-001 point 2). A floor is project-kit's mechanism, raised only when a change declares it (PRJ-002 D4). The maintainer's delegate chose the floor on 19 October, under the maintainer's standing delegation (the design note on analysis concepts and order, PR #1808)."}
    pkit:
      friction:
        anchors:
          record: ["software-analysis:DEC-001#2", "PRJ-002#D4"]
        revalidated:
          at: 2026-10-20T22:11:48Z
          outcome: unchanged
          unchanged-because: DEC-001 point 2 changes only its line on the overview's folder. The version a glossary head's links to another analysis name is untouched.
---

# ANA — project-kit's rules for its analysis

These are the rules project-kit's analysis follows: seven rules of its own, and the rules of the two sets it inherits.

- **What it selects:** every actor, glossary term, domain-model view, use case and journey, by the five types software-analysis declares (software-analysis DEC-001 point 2, DEC-004 point 4). The scope names no paths, so it selects the analysis wherever software-analysis places it.
- **What it does not select:** a revalidation record. A revalidation record is a held document, never an artefact, so no scope selects it. Whoever writes one still follows `WRITE`, through project-kit's operational rules (`.pkit/rules/project.md`).
- **What it inherits:** the accepted rules of both sets bind on the analysis through this set (COR-051 point 7).
  - `WRITE`, project-kit's general writing rules, pinned at `WRITE@2`.
  - `software-analysis:SAN`, the software-analysis method, pinned at `SAN@1`. `SAN` takes no scope, so its rules bind on project-kit's analysis only through this set (software-analysis DEC-001 point 1).
  - **The pins:** a rule accepted in an inherited set gives that set a new major. The same change re-pins this set, which gives it a new major too (COR-051 point 7).
- **The set's own rules:** the actor's voice in needs and goals (RS-ANA-001), and each kind's list of labels (RS-ANA-002), which fills `RS-WRITE-002#labels`. Then the analyses project-kit keeps, their areas and the numbers of its domain-model views (RS-ANA-003, RS-ANA-007, RS-ANA-004 and RS-ANA-005), and the version a capability's links to the analyses it builds on name (RS-ANA-006).
  - RS-ANA-003 to RS-ANA-007 are project-kit's choices where software-analysis leaves them to each project (software-analysis DEC-001 points 2 and 12, DEC-004 point 4). They are the form of an area's number and of a view's, which analyses it keeps, the core's five areas, and which version its links name.
  - The maintainer decided the design on 19 October. The maintainer's delegate answered its open questions the same day, under the maintainer's standing delegation. Among them are the adapters and the links' version (the design note on analysis concepts and order, PR #1808).
  - That a need or a goal is one sentence is the method's, through the `sentence` form of RS-SAN-001. So RS-ANA-001 leaves it out.
  - software-analysis asks for the actor's voice only in its hints, and a hint binds nothing (software-analysis DEC-001 point 1). A project that wants the voice to bind adds a rule of its own, as the maintainer decided on 9 October (PR #1391). RS-ANA-001 is that rule.
  - RS-WRITE-002 lets a section leave out a label it has nothing for. Where RS-SAN-001 binds, every part a kind ships is still present, so only an addition is left out.
- **The labels as data:** the labels project-kit adds to a kind, and a closed list of a kind's labels, are data in project-kit's own structures (`.pkit/capabilities/software-analysis/project/structures.yaml`). RS-ANA-002 authorises both. When they bind is software-analysis's (DEC-001 point 1).
- **How a rule reads:** as in `WRITE`, a statement, then *How*, then examples. A rule's reason is the `why` of its origin (COR-051 point 5).
  - Each example names its source in brackets after the quote.
  - RS-ANA-002 has no examples of its own, since RS-WRITE-002's quote the list it fills. RS-ANA-006 and RS-ANA-007 have none, since no analysis of project-kit's holds what they govern.
- **What binds:** a rule's statement and its *How*, as in `WRITE`.
- **Note:** how rules are named, accepted and inherited is the rule-set record's (COR-051). A rule binds only once it is accepted.

## Needs and goals

This rule is for an actor's needs, and for the goal of a use case or a journey.

### RS-ANA-001 — A need or a goal speaks in its actor's voice

Write each need and each goal as an imperative that starts with its verb, in its actor's voice. The actor refers to itself with *I*, *me*, *my* and *myself*.

- **How:**
  - A need is an item of an actor's `needs`. A goal is the *Goal* of a use case or a journey, and its actor is the use case's or the journey's `actor`.
  - A need is also one that a glossary's head states beside an actor it lists from another analysis. This holds wherever this rule binds on a term of that glossary.
  - *Never* may come before the verb.
- **Breaks the rule:** "Find the agent's role definition deployed, …" (the first ASD-STE100 run, where the AI agent names itself)
- **Keeps the rule:** "Find my role definition deployed, …" (the original)

## Labels

This rule says which labels each kind of analysis artefact gives its parallel sections.

### RS-ANA-002 — Each kind's list of labels

A kind's list of labels is that of its declared structure, with project-kit's additions to it, in the order they give.

- **How:**
  - **No copy:** the list stays in the data the check reads, the kind's declared structure and project-kit's own structures. This rule holds no copy of it.
  - **Authorised tightenings:** two tightenings of a kind in project-kit's own structures. They are labels added to the kind, each optional, and a closed list of the kind's labels.
  - This rule fills `RS-WRITE-002#labels`, and the rest of RS-WRITE-002 holds as written.

## Analyses and areas

These rules say which analyses project-kit keeps, how their areas and their domain-model views are numbered, and which version a capability's links to the core's analysis name.

### RS-ANA-003 — An area's folder opens with a number of three digits, in steps of 10

Open the name of each use-case area's folder with a number of three digits and a hyphen, in steps of 10, such as `010-develop`.

- **How:**
  - **Where it binds.** On each use case, through the folder of its area. A use case in no area meets nothing of this rule.
  - **The width.** Every area's number takes three digits, in every analysis.
  - **A new area** between two takes a free number between theirs, so no folder is renamed.
  - **What the number means** is software-analysis's: one valid order in which the areas build on each other (software-analysis DEC-001 points 2 and 12). It is no part of an id, so a use case keeps its `UC-NNN` id, whatever its area's number.
  - **No other folder** of the analysis takes such a number.
- **Breaks the rule:** "`change/` and `release/`", the core's areas without numbers (`tech-docs/analysis/use-case-model/use-cases/` on main, 19 October)
- **Keeps the rule:** "`030-change/` and `040-release/`" (the design note on analysis concepts and order)

### RS-ANA-007 — A domain-model view's file opens with a number of three digits, in steps of 10

Open the name of each domain-model view's file with a number of three digits and a hyphen, in steps of 10, such as `010-orders-and-payments.md`.

- **How:**
  - **Where it binds.** On each domain-model view, through its file's name.
  - **The width.** Every view's number takes three digits, in every analysis.
  - **A new view** between two takes a free number between theirs, so no file is renamed.
  - **What the number means** is software-analysis's: one valid order of the views, in which each uses only the views before it (software-analysis DEC-004 points 4 and 6). It is no part of the id, so a view keeps its `VIEW-` id, whatever its number.

### RS-ANA-004 — An artefact lies in its component's analysis

Keep each artefact in the analysis of the component it describes, in a folder of the analysis's location named after that component.

- **How:**
  - **The analyses.** project-kit keeps one analysis for its core, in `core/`, and one for each capability, in a folder named after the capability. An adapter keeps one on a capability's terms once it needs one (COR-007).
  - **Which component.** The component whose behaviour the artefact states. So a use case that a capability carries out lies in that capability's analysis, even where its actor is the core's.
  - **What it builds on.** A capability's analysis builds on the core's, and on the analysis of each capability its own depends on (software-analysis DEC-001 point 2).
- **Breaks the rule:** "`tech-docs/analysis/use-case-model/actors/ACT-developer.md`", the core's actor at the analysis's root (main, 19 October)
- **Keeps the rule:** "`tech-docs/analysis/core/use-case-model/actors/`" (the design note on analysis concepts and order)

### RS-ANA-005 — The core's use cases lie in its five areas

Keep each use case of the core's analysis in one of its five areas: `010-develop`, `020-set-up`, `030-change`, `040-release` and `050-adopt`.

- **How:**
  - **The stages.** The areas are the five stages of the chain of use cases, in the order in which they build on each other.
  - **A new area** needs a change to this rule, since the five are the maintainer's choice.
- **Breaks the rule:** "`change/` and `release/`", the core's two areas (`tech-docs/analysis/use-case-model/use-cases/` on main, 19 October)
- **Keeps the rule:** "`010-develop`, `020-set-up`, `030-change`, `040-release` and `050-adopt`" (the design note on analysis concepts and order)

### RS-ANA-006 — A capability's links to another analysis name the floor it requires

Link each term and actor a capability's glossary head lists to its home analysis at the floor the capability requires of that analysis's component. Name each floor once in the head.

- **How:**
  - **Where it binds.** On the head of a capability's glossary, wherever this rule binds on one of its terms.
  - **The floor.** For the core's analysis, it is the lowest backbone version the capability's package metadata admits, its `requires_backbone`. For another capability's, it is the lowest version its entry for that capability admits.
  - **Before an analysis exists at the floor,** the head names the first release that holds it, and says why.
  - **When a floor rises,** a release raises it and leaves the head as it is (PRJ-002 D4). A change then brings the head to the floor.
