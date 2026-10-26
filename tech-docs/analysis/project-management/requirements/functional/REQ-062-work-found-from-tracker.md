---
id: REQ-062
title: An instance's work in flight is found again from GitHub and the instance's number alone
status: active
statement: "The issues an instance owns, and each one's branch, are found from GitHub and the instance's number, with nothing an ended session kept."
measure: "After every earlier session died, a new session in the instance lists the issues the instance owns, and finds each one's branch."
applies-to: "Every instance that has set a number, whichever way the project writes the owner of an issue."
actors:
  - ACT-worker-agent
  - ACT-lead-agent
  - ACT-director
refines: []
pkit:
  friction:
    anchors:
      record:
        - project-management:DEC-035#1
        - project-management:DEC-035#7
        - project-management:DEC-043#4
        - project-management:DEC-013
      artefact:
        - ACT-worker-agent
        - ACT-lead-agent
        - ACT-director
---

# REQ-062 · Functional · An instance's work in flight is found again from GitHub and the instance's number alone

**Verified by:** None.

**Rationale:** Clones coordinate through GitHub, so the only state they keep is each clone's number and the marks on the issues (DEC-035). [EPIC](../../glossary.md#term-epic--epic) #943 sets the outcome this serves: with every session killed, each clone finds where it was from GitHub and the clone's number. The [owner](../../glossary.md#term-owner--owner) is written on the [issue](../../glossary.md#term-issue--issue) itself, so it survives a session that died (DEC-043 point 4). Each [Task](../../glossary.md#term-task--task)'s branch is named after the Task, so the branch is found from the issue (DEC-013).

## Open for the design

Where the work was heading beyond its branch is decided by no record yet, as `UC-086` says. #2096 asks that an agent's direction be found from GitHub alone. This requirement holds what the records decide: what an [instance](../../glossary.md#term-instance--instance) owns, and each [Task](../../glossary.md#term-task--task)'s branch.
