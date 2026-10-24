---
change: '#1717'
trigger: planned
reviewed-against:
  - title: "#1717's body"
    url: https://github.com/aleskalfas/project-kit/issues/1717
    version: '2026-10-23T22:41:17Z'
  - title: the core's code and records
    version: 26ab0cba1bc217f6ef3828bd2a2d6d8f60d96cf2
date: '2026-10-23'
by: 'builder agent for #1717'
confirmed-by: Aleš Kalfas
outcomes:
  ACT-adopter: gap-found
  ACT-operator: gap-found
  UC-012: gap-found
  UC-013: gap-found
---

# 2026-10-23 — The core's area 050-adopt

## Outcomes

- **ACT-adopter — gap-found.** Four of its needs had no use case: install the system, upgrade it like a dependency, re-pin an inherited rule set, and upgrade one capability on its own. UC-049, UC-051, UC-053 and UC-054 now meet them, and the actor holds as written.
- **ACT-operator — gap-found.** Three of its needs had no use case: put the system's tool on the machine, run each project at its pin, and get a fresh clone ready with one sync. UC-048, UC-052 and UC-050 now meet them, and the actor holds as written.
- **UC-012 — gap-found.** It wrote no `after`, and listed no requirement.
- **UC-013 — gap-found.** It listed no requirement.

## Gaps

- **ACT-adopter, ACT-operator:** seven needs had no use case. **Resolution:** UC-048 to UC-054 describe them, with a "Not built yet" box below each step that an accepted record decides and the code does not do yet.
- **UC-012:** no precondition named the use case that puts the tool on the machine. **Resolution:** it names UC-048 in `after`.
- **UC-012, UC-013:** no requirement was listed. **Resolution:** UC-012 lists REQ-002 and REQ-005. UC-013 lists REQ-005 and REQ-012, with a box naming #1765 below each step whose command does not yet check the session's own repository.
