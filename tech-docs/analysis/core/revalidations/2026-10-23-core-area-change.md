---
change: '#1896'
trigger: planned
reviewed-against:
  - title: "#1896's body"
    url: https://github.com/aleskalfas/project-kit/issues/1896
    version: '2026-10-22T23:34:23Z'
  - title: the core's code and records
    version: a5573cd00bbd251a10fe83a884ee3f1766c0b1b7
date: '2026-10-23'
by: 'builder agent for #1896'
confirmed-by: Aleš Kalfas
outcomes:
  UC-002: gap-found
  UC-003: gap-found
  UC-004: gap-found
  UC-005: gap-found
  UC-006: gap-found
  UC-007: gap-found
  UC-010: gap-found
  UC-011: gap-found
---

# 2026-10-23 — The core's area 030-change, its requirements and the landing

## Outcomes

- **UC-002 — gap-found.** Its answers went in the artefact's block, which COR-062 moves to answer files, and nothing described the change check's reading of them. Its writers listed no check before another repository, and two variants and a step named capabilities.
- **UC-003 — gap-found.** It listed none of the requirements its checks must meet, such as that a check never reads a missing base as clean.
- **UC-004 — gap-found.** It did not list that a missing documentation root warns, nor the two requirements on the friction group's documents.
- **UC-005 — gap-found.** Its places had no producer, and it listed none of the requirements its steps must meet, the dead anchor among them. Variant 1d named a capability's stamp.
- **UC-006 — gap-found.** Its findings and its merge queue predated COR-062, and its `config set` listed no check before another repository. It listed REQ-009 with no variant for the dry run that command lacks.
- **UC-007 — gap-found.** Its precondition named no producer, its answers went in the block, and three variants named capabilities' agents and records.
- **UC-010 — gap-found.** Its stamp listed no check before another repository, and no requirement said a backbone migration is safe over any state.
- **UC-011 — gap-found.** Its stamp listed no check before another repository, and its check did not list the requirements of a check.

## Gaps

- **UC-007:** no use case landed a change, so its precondition that the default branch holds debt named no producer. **Resolution:** UC-034 writes the landing in 030-change, and the precondition names it.
- **UC-002, UC-007:** their answers went in the artefact's block, which COR-062 moves to answer files. **Resolution:** each step says where answers go, boxed to #1873 where unbuilt.
- **UC-002, UC-006:** the change check's reading of answer files, which #1871 built, went undescribed. **Resolution:** UC-002's variants 7b to 7d and UC-006's step 6 say what it finds.
- **UC-006:** its merge queue's run did not judge each change's own head, as COR-062 point 4 asks, and its dry run had no variant. **Resolution:** variant 3d says the first, boxed to #1867, and variant 1d the second, boxed to #1884.
- **UC-002, UC-006, UC-007, UC-010, UC-011:** their commands that write listed no check before another repository. **Resolution:** each lists REQ-012, and a step states the check, boxed to #1765.
- **UC-002, UC-005, UC-007:** six variants, a step and an actor's part named a capability's agents, records or stamp, and eight anchors stood on capabilities. Two of the variants are #1856's, UC-002's 5b and UC-007's 4a. **Resolution:** each is reworded to the core's part under its own number or letter, and the anchors are removed.
- **UC-005:** its places had no producer. **Resolution:** its precondition names UC-021, UC-023 and UC-016.
- **UC-003, UC-004, UC-005, UC-006, UC-010, UC-011:** they listed few or none of the requirements their steps must meet. **Resolution:** each lists them, 030-change's new REQ-017 to REQ-021 among them.
