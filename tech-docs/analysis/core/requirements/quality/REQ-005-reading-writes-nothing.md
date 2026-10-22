---
id: REQ-005
title: A command that only reads or validates changes nothing in the project
status: active
statement: A command whose one operation is validation or read-only introspection, such as a check or a listing, changes no file of the project.
measure: After such a command, each file that git tracks in the project holds the bytes and the mode it held before. So does each file of project-owned content.
applies-to: Every command of the backbone and of the components whose one operation is validation or read-only introspection, the change check among them.
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
        - COR-055#3
---

# REQ-005 · Quality · A command that only reads or validates changes nothing in the project

**Verified by:** A test runs `pkit friction debt` and `pkit friction explain` over a tree with uncommitted edits. It finds every file's bytes and mode as they were, those under `.git` included. Tests find that `pkit capabilities install --plan` and `pkit process health` write nothing. No test covers most of these commands, the change check and validation among them.

**Rationale:** COR-004 gives each command one operation, validation and read-only introspection among them, and never two in one command. COR-050 keeps every write out of checking: "No writing happens as a side effect of checking". Writing is always "a separate, explicit command that names what it writes" (COR-050 point 13). Each command validation runs "changes nothing in the project", under the limits COR-050 point 2 sets (COR-055 point 3).
