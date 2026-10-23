---
change: '#1718'
trigger: planned
reviewed-against:
  - title: "#1718's body"
    url: https://github.com/aleskalfas/project-kit/issues/1718
    version: '2026-10-23T08:30:58Z'
  - title: the core's code and records
    version: a5573cd00bbd251a10fe83a884ee3f1766c0b1b7
date: '2026-10-23'
by: 'builder agent for #1718'
confirmed-by: Aleš Kalfas
outcomes:
  UC-016: gap-found
  UC-017: gap-found
---

# 2026-10-23 — The core's area 020-set-up, its backbone configuration and capabilities

## Outcomes

- **UC-016 — gap-found.** Its precondition that the project holds the capability's subtree named UC-015 alone. The install copies a shipped capability's subtree too, which its variant 2c adopts. It now names UC-023.
- **UC-017 — gap-found.** Its precondition that the manifest records the capability named UC-016 alone. The install records it too, in the source repository and elsewhere. It now names UC-023.

## Gaps

- **UC-016, UC-017:** no use case added a capability, so neither precondition named the install as a producer. **Resolution:** UC-023 writes it in 020-set-up, and each precondition names it beside its producer in 010-develop.
