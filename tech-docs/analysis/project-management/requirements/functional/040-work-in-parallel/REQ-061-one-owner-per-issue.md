---
id: REQ-061
title: No two instances keep working on one issue
status: active
statement: "No instance starts, moves, edits or lands an issue that another of the same person's instances owns, and a same-instant clash ends with one owner."
measure: "An ordinary command on another instance's issue refuses, unless a person sets the refusal aside with a reason. After a clash at the same instant, the higher-numbered instance gives the issue up and says so."
applies-to: "The ordinary commands that act on an issue as its owner, `start-work`, `done-work`, `edit-issue` and `move-issue`, wherever the issue's assignee has set instances."
actors:
  - ACT-worker-agent
  - ACT-lead-agent
refines: []
pkit:
  friction:
    anchors:
      record:
        - project-management:DEC-035#3
        - project-management:DEC-035#6
        - project-management:DEC-043#3
      artefact:
        - ACT-worker-agent
        - ACT-lead-agent
---

# REQ-061 · Functional · No two instances keep working on one issue

**Verified by:** None.

**Rationale:** Two [instances](../../../glossary.md#term-instance--instance) that work on one [issue](../../../glossary.md#term-issue--issue) step on each other, and the work is done twice (DEC-035). GitHub offers no atomic claim, so a clash can only be caught and resolved, never prevented (DEC-035 point 6). The lower number wins, since both instances work it out from the marks alone, and either may keep the issue (DEC-035). The comment log keeps that tie-break where no label can be created (DEC-043 point 3).
