---
rule-set: ANA
version: 4.0.0
inherits: [WRITE@2, software-analysis:SAN@1]
scope:
  types: [software-analysis:actor, software-analysis:term, software-analysis:use-case, software-analysis:journey]
rules:
  RS-ANA-001:
    status: proposed
    origin: {why: "A need or a goal in its actor's own voice reads as that actor speaking, as a user story states one (software-analysis DEC-001). In the trial, the ASD-STE100 rewrite kept no need's first person, and repeated the role's noun instead (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
    pkit:
      friction:
        anchors:
          record: ["software-analysis:DEC-001#1"]
  RS-ANA-002:
    status: proposed
    origin: {why: "A kind's labels already have one home, which the check reads: its declared structure, with project-kit's additions to it as data (software-analysis DEC-001 point 1). A copy of the list here would drift from them."}
    fills: [RS-WRITE-002#labels]
    pkit:
      friction:
        anchors:
          artefact: [RS-WRITE-002]
---

# ANA — project-kit's rules for its analysis

These are the rules project-kit's analysis follows: two rules of its own, and the rules of the two sets it inherits.

- **What it selects:** every actor, glossary term, use case and journey, by the four types software-analysis declares (software-analysis DEC-001 point 2). The scope names no paths, so it selects the analysis wherever software-analysis places it.
- **What it does not select:** a revalidation record. A revalidation record is a held document, never an artefact, so no scope selects it. Whoever writes one still follows `WRITE`, through project-kit's operational rules (`.pkit/rules/project.md`).
- **What it inherits:** the accepted rules of both sets bind on the analysis through this set (COR-051 point 7).
  - `WRITE`, project-kit's general writing rules, pinned at `WRITE@2`.
  - `software-analysis:SAN`, the software-analysis method, pinned at `SAN@1`. `SAN` takes no scope, so its rules bind on project-kit's analysis only through this set (software-analysis DEC-001 point 1).
  - **The pins:** a rule accepted in an inherited set gives that set a new major. The same change re-pins this set, which gives it a new major too (COR-051 point 7).
- **The set's own rules:** the actor's voice in needs and goals (RS-ANA-001), and each kind's list of labels (RS-ANA-002), which fills `RS-WRITE-002#labels`.
  - That a need or a goal is one sentence is the method's, through the `sentence` form of RS-SAN-001. So RS-ANA-001 leaves it out.
  - software-analysis asks for the actor's voice only in its hints, and a hint binds nothing (software-analysis DEC-001 point 1). A project that wants the voice to bind adds a rule of its own, as the maintainer decided on 9 October (PR #1391). RS-ANA-001 is that rule.
  - RS-WRITE-002 lets a section leave out a label it has nothing for. Where RS-SAN-001 binds, every part a kind ships is still present, so only an addition is left out.
- **The labels as data:** the labels project-kit adds to a kind, and a closed list of a kind's labels, are data in project-kit's own structures (`.pkit/capabilities/software-analysis/project/structures.yaml`). RS-ANA-002 authorises both. When they bind is software-analysis's (DEC-001 point 1).
- **How a rule reads:** as in `WRITE`, a statement, then *How*, then examples. A rule's reason is the `why` of its origin (COR-051 point 5).
  - Each example names its source in brackets after the quote.
  - RS-ANA-002 has no examples of its own, since RS-WRITE-002's quote the list it fills.
- **What binds:** a rule's statement and its *How*, as in `WRITE`.
- **Note:** how rules are named, accepted and inherited is the rule-set record's (COR-051). A rule binds only once it is accepted.

## Needs and goals

This rule is for an actor's needs, and for the goal of a use case or a journey.

### RS-ANA-001 — A need or a goal speaks in its actor's voice

Write each need and each goal as an imperative that starts with its verb, in its actor's voice. The actor refers to itself with *I*, *me*, *my* and *myself*.

- **How:**
  - A need is an item of an actor's `needs`. A goal is the *Goal* of a use case or a journey, and its actor is the use case's or the journey's `actor`.
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
