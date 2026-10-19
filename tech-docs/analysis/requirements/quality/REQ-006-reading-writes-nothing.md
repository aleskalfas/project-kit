---
id: REQ-006
title: A reading command changes nothing in the project
status: active
statement: A reading command changes no file that the project tracks or owns.
measure: After a reading command, each file the project tracks, and each project-owned file, holds the bytes and the mode it held before. What the command, or the tool that runs it, keeps for itself, such as compiled bytecode, is no change to the project.
applies-to: Every reading command of the backbone and of the components.
actors: []
refines: []
pkit:
  friction:
    anchors:
      path:
        - tests/test_friction_report.py
        - tests/test_capability_plans.py
        - tests/test_process_health.py
      record:
        - COR-004
        - COR-050#2
        - COR-050#13
        - COR-053#2
---

# REQ-006 · Quality · A reading command changes nothing in the project

**Verified by:** A test runs `pkit friction debt` and `pkit friction explain` over a tree with uncommitted edits. It finds every file's bytes and mode as they were, those under `.git` included. Tests find that `pkit capabilities install --plan` and `pkit process health` write nothing. No test covers most reading commands, the change check and validation among them.

**Rationale:** COR-050 keeps every write out of checking: "No writing happens as a side effect of checking". COR-004 gives each command one operation, read-only introspection among them, so a reading command takes no consent a write would need. A capability signals others only from commands that write, "so reading commands emit nothing" (COR-053 point 2).
