---
id: REQ-061
title: No two instances keep working on one issue
status: active
statement: "No instance starts, moves, edits or lands an issue that another of the same person's instances owns, and a same-instant clash ends with one owner."
measure: "An ordinary command on another instance's issue refuses, unless a person makes a bypass, with its reason. After a clash at the same instant, the higher-numbered instance gives the issue up and says so."
applies-to: "The ordinary commands that act on an issue as its owner, `start-work`, `done-work`, `edit-issue` and `move-issue`, wherever the issue's assignee has instances."
obligation: v1:sha256:3412cd2453ad8580edd30fb0b093ae2c64166fe04b14333fbfd8fa23ecde9f13
actors:
  - ACT-worker-agent
  - ACT-lead-agent
refines: []
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/_lib/instance_claims.py
        - .pkit/capabilities/project-management/scripts/_lib/instance_ownership.py
      record:
        - project-management:DEC-035
        - project-management:DEC-035#3
        - project-management:DEC-035#6
        - project-management:DEC-043#3
      artefact:
        - ACT-worker-agent
        - ACT-lead-agent
---

# REQ-061 · Functional · No two instances keep working on one issue

**Verified by:** None.

**Rationale:** Two [instances](../../../glossary.md#term-instance--instance) that work on one [issue](../../../glossary.md#term-issue--issue) step on each other, and the work is done twice ([DEC-035](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md)). GitHub offers no lock, so a clash can only be caught and resolved, never prevented ([DEC-035 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#6-the-clash-guard-catches-and-resolves-it-does-not-lock)). The lower number wins, since both instances work the winner out from the ownerships alone, and either may keep the issue (DEC-035). Comments on the issue keep that tie-break where no label can be created ([DEC-043 point 3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-043-ownership-substrate-selection.md#3-in-comment-mode-the-source-of-truth-is-a-per-instance-append-only-ownership-event-log)).
