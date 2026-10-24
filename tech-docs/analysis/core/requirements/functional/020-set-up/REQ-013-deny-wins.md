---
id: REQ-013
title: Where an allow and a deny conflict, the deny wins
status: active
statement: Where one grant allows a call and another denies it, the permission model denies the call.
measure: A call that a deny grant matches is denied, even where an allow grant matches it too. The order of the layers and their grants changes no decision.
applies-to: Every decision of the permission model, for every subject, over the guardrails, the capabilities' grants, the active profile and the project's own grants.
actors:
  - ACT-adopter
  - ACT-operator
refines: []
pkit:
  friction:
    anchors:
      path:
        - tests/test_permission_decide.py
        - .pkit/permissions/decide.py
      record:
        - COR-028#1
      artefact:
        - ACT-adopter
        - ACT-operator
    revalidated:
      at: 2026-10-24T00:58:28Z
      outcome: unchanged
      unchanged-because: The code checks every deny grant before it looks for an untrusted construct, and new tests find a deny winning behind a PATH assignment, a brace expansion and a comment. The order of the grants still changes no decision.
---

# REQ-013 · Functional · Where an allow and a deny conflict, the deny wins

**Verified by:** Tests decide calls whose grants allow and deny the same privilege, with the allow before the deny and after it, and find each call denied. A test finds that a capability's deny holds over the allow of the autonomous profile. Another finds that a forced push stays denied to an agent granted version control.

**Rationale:** COR-028 point 1 makes each agent's permissions the union of the shared baseline and its own grants. There, "where an allow and a deny conflict, deny prevails". So a grant the adopter adds beside the methodology's never widens one of its denies. The operator lets agents work on their own knowing that a deny holds, whatever profile is active.
