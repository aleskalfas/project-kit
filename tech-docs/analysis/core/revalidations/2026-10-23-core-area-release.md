---
change: '#1914'
trigger: planned
reviewed-against:
  - title: "#1914's body"
    url: https://github.com/aleskalfas/project-kit/issues/1914
    version: '2026-10-23T18:20:15Z'
  - title: the core's code and records
    version: 2501563ef4aa5c702683afcc89e9d8195520d9a6
date: '2026-10-23'
by: 'builder agent for #1914'
confirmed-by: Aleš Kalfas
outcomes:
  UC-008: gap-found
  UC-009: gap-found
---

# 2026-10-23 — The core's area 040-release brought to the standard

## Outcomes

- **UC-008 — gap-found.** Its changesets had no producer, and it listed no check before another repository. A variant named a capability's command, and its release by hand had no dry run.
- **UC-009 — gap-found.** It wrote no `after`, and its changesets had no producer. Its release step listed no check before another repository and no dry run, both of which the code lacks.

## Gaps

- **UC-008, UC-009:** no precondition named the use cases that make the changesets wait on the default branch. **Resolution:** each names UC-003, which declares them, and UC-034, which lands them.
- **UC-008, UC-009:** their commands that write listed no check before another repository. **Resolution:** each lists REQ-012. UC-008's step 14 and variant 14a state the check `pkit release merge` runs. A box names #1765 where `pkit release apply` runs none.
- **UC-008, UC-009:** `pkit release apply` offered no dry run, and no variant said so. **Resolution:** variants 1c and 3h state it, each boxed to #1884.
- **UC-008, UC-009:** no listed requirement said that `pkit release plan` writes nothing. **Resolution:** each lists REQ-005.
- **UC-008:** variant 9a named a capability's command. **Resolution:** it is reworded to the core's part under its letter.
