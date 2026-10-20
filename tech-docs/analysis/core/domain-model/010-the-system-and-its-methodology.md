---
id: VIEW-the-system-and-its-methodology
title: The system and its methodology
status: active
explains:
  - TERM-system
  - TERM-harness
  - TERM-decision-record
  - TERM-point
  - TERM-rule
  - TERM-acceptance-gate
  - TERM-operational-rule
  - TERM-methodology
pkit:
  friction:
    anchors:
      record:
        - COR-006
        - COR-014
        - COR-047#1
        - COR-047#3
        - COR-051#1
        - COR-051#3
        - COR-051#4
        - COR-051#5
        - COR-058#1
        - COR-058#3
        - COR-058#4
        - COR-058#5
        - COR-058#9
      artefact:
        - TERM-system
        - TERM-harness
        - TERM-decision-record
        - TERM-point
        - TERM-rule
        - TERM-acceptance-gate
        - TERM-operational-rule
        - TERM-methodology
---

# VIEW-the-system-and-its-methodology — The system and its methodology

What the system is, the methodology it ships and enforces, and the harness that hosts the sessions where the methodology is used. The methodology is made of decision records with their points, rules, operational rules and conventions. The acceptance gate says which records and rules work may build on.

```mermaid
classDiagram
  accTitle: The system and its methodology
  accDescr: The system ships and enforces the methodology. The methodology is made of decision records, rules, operational rules and conventions. A decision record holds points. Work builds only on accepted decision records and rules, as the acceptance gate says. A harness loads the operational rules through its include.
  class System["system"]
  class Harness["harness"]
  class Methodology["methodology"]
  class DecisionRecord["decision record"]
  DecisionRecord : id
  DecisionRecord : status
  class Point["point"]
  Point : id
  class Rule["rule"]
  Rule : id
  Rule : origin
  Rule : status
  class AcceptanceGate["acceptance gate"]
  class OperationalRule["operational rule"]
  OperationalRule : number
  System --> Methodology : ships and enforces
  Methodology o-- DecisionRecord
  Methodology o-- Rule
  Methodology o-- OperationalRule
  DecisionRecord "1" *-- "*" Point : holds
  AcceptanceGate ..> DecisionRecord : admits only accepted
  AcceptanceGate ..> Rule : admits only accepted
  Harness ..> OperationalRule : loads
```

## system

The system is the software this analysis describes: the one you install, run and extend. The analysis calls it *the system*, and keeps the product's name, pkit, for prose about the product and for commands.

**Attributes:** None.

**Relations:**

- It ships the methodology, and enforces it.
- Other software it meets, such as a harness or the hosting service, is no part of it. The analysis names each for what it is.

**States:** None.

**Always true:** None.

## harness

A harness is an external tool that hosts working sessions and runs the tool calls made in them. Claude Code is one. The methodology depends on how the harness behaves, which the methodology cannot set.

**Attributes:**

- its include: the line in its instruction file that pulls another file into each session, as `@.pkit/rules/core.md` does

**Relations:**

- Its include loads the operational rules into each session it hosts.
- It is no part of the system.

**States:** None.

**Always true:**

- What the methodology needs of a harness is stated as behaviour one can observe, never in any harness's own vocabulary (COR-047 point 1).
- A need that no declaration covers for the harness in use is unknown, never met (COR-047 point 3).

## decision record

A decision record is a document that states one choice among alternatives, with the context that called for it and the reasons for it. It binds only once it is accepted, so work builds on it only from then.

**Attributes:**

- an id: its namespace's prefix and a number, such as COR-050
- a status: `proposed`, `accepted` or `superseded`
- its sections: the context, the decision, the reasons and what follows from it

**Relations:**

- It belongs to one namespace, which numbers its records on its own. COR, the namespace of the core records, is one.
- Its decision may hold points (COR-058 point 1).
- A rule's origin may cite it. The record says what was chosen and why, and the rule says what must hold (COR-051 point 1).

**States:** A record is `proposed` until it is accepted in review, and `accepted` until a newer record supersedes it. It never moves back, and a superseded record is kept.

```mermaid
stateDiagram-v2
  accTitle: The states of a decision record
  accDescr: A decision record is proposed, then accepted in review, then superseded by a newer record. It never moves back.
  [*] --> proposed
  proposed --> accepted : it is accepted in review
  accepted --> superseded : a newer record supersedes it
```

**Always true:**

- It says why a choice was made, and holds no procedure (COR-006).

## point

A point is one numbered or labelled part of a decision record's Decision. Once the record writes it as a heading, its id names it for good, so a citation such as COR-050 point 3 stays true. A record that writes its points as a numbered list still works, but its numbers may move until it is converted (COR-058 point 9).

**Attributes:**

- an id: a number, such as `3`, or a label, such as `D1`
- a title of a few words, and its text, which runs to the next heading of the same or a higher level (COR-058 point 1)

**Relations:**

- It belongs to one decision record, inside that record's Decision (COR-058 point 1).
- A retired point names the points that took its text, where any did (COR-058 points 4 and 5).

**States:** A point written as a heading is live until it is retired, by being dropped, split or merged. A stub then stays where it stood, and its id stays in the record's front matter (COR-058 point 4).

```mermaid
stateDiagram-v2
  accTitle: The states of a point written as a heading
  accDescr: A point is live until it is dropped, split or merged, and then retired. A retired point never returns.
  [*] --> live
  live --> retired : it is dropped, split or merged
```

**Always true:**

- In a record whose points are headings, no point is renumbered, and no id is used again, a retired one included (COR-058 point 3).
- In such a record, a new point takes the next unused number (COR-058 point 3).

## rule

A rule is a statement that every document or collection entry it binds on must satisfy, once it is accepted. It has a permanent id, such as RS-WRITE-005, and a recorded origin that says when, by whom and why it was decided.

**Attributes:**

- an id, such as `RS-WRITE-005` (COR-051 point 3)
- its statement
- an origin: when, by whom and why it was decided, or the decision record it cites (COR-051 point 5)
- a status: proposed, accepted, superseded or withdrawn (COR-051 point 4)

**Relations:**

- Its origin may cite a decision record, which must be accepted whenever the rule is (COR-051 point 5).
- A superseded rule names the rule that succeeds it (COR-051 point 4).

**States:** A rule is proposed until it is accepted in review. Where a person takes part, that person's review accepts it. An accepted rule may be superseded, naming its successor, or withdrawn, naming none. Either way it stays where it is, under its id (COR-051 point 4).

```mermaid
stateDiagram-v2
  accTitle: The states of a rule
  accDescr: A rule is proposed, then accepted in review. An accepted rule is later superseded by a successor, or withdrawn.
  [*] --> proposed
  proposed --> accepted : it is accepted in review
  accepted --> superseded : a successor replaces it
  accepted --> withdrawn : it is withdrawn with no successor
```

**Always true:**

- Only an accepted rule binds. A proposed, superseded or withdrawn one binds nothing (COR-051 point 4).
- Its id is never renumbered, and a retired id is never used again (COR-051 point 3).
- An accepted rule has a complete origin (COR-051 point 5).

## acceptance gate

The acceptance gate is the condition that work builds only on what is already accepted. A decision record or a rule that is still proposed is a draft. Work that would rest on it waits, or has it accepted first.

**Attributes:** None.

**Relations:**

- It holds for decision records and for rules alike, a repository's own as well as the methodology's.

**States:** None.

**Always true:**

- An accepted rule whose origin cites a decision record cites an accepted one (COR-051 point 5).

## operational rule

An operational rule is an instruction that every session loads through the harness's include. It is cited by its number in its file, such as core rule 8, and carries no id, origin or status.

**Attributes:**

- its number in its file
- its statement, mostly with a pointer to where its reasons are

**Relations:**

- The harness's include loads it into each session.
- It shares only the word with a rule: it has none of a rule's id, origin or status (COR-051 point 1).

**States:** None.

**Always true:**

- An operational rule that fits any repository is in the file the system ships. One that fits only one repository is in that repository's own file (COR-014).

## methodology

The methodology is the body of decision records, rules, operational rules and conventions that the system ships and enforces. Its conventions are agreed ways of working, such as how a commit's message is written. A repository keeps its own records, rules and operational rules beside the methodology's. They are no part of it, yet the acceptance gate holds for them too.

**Attributes:** None.

**Relations:**

- It is made of decision records, rules, operational rules and conventions.
- The system ships it and enforces it.

**States:** None.

**Always true:** None.
