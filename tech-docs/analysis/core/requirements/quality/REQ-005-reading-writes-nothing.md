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

**Verified by:** A test runs `pkit friction debt` and `pkit friction explain` over a tree with uncommitted edits. It finds every file's bytes and mode as they were, those under `.git` included. Tests find that `pkit capabilities install --plan` and `pkit process health` write nothing. No test covers most of these commands, the [change check](../../glossary.md#term-change-check--change-check) and [validation](../../glossary.md#term-validation--validation) among them.

**Rationale:** [COR-004](../../../../../.pkit/decisions/core/COR-004-cli-surface.md) gives each command one operation, [validation](../../glossary.md#term-validation--validation) and read-only introspection among them, and never two in one command. [COR-050](../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md) keeps every write out of checking: "No writing happens as a side effect of checking". Writing is always "a separate, explicit command that names what it writes" ([COR-050 point 13](../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#13-commands)). Each command validation runs "changes nothing in the [project](../../glossary.md#term-project--project)", under the limits [COR-050 point 2](../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#2-anchors) sets ([COR-055 point 3](../../../../../.pkit/decisions/core/COR-055-validation.md#3-a-component-joins-by-naming-a-command)).
