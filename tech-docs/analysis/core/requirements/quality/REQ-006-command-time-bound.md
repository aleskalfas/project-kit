---
id: REQ-006
title: The backbone stops a command it runs for an anchor, a data point, validation or a process after thirty seconds
status: active
statement: The backbone never waits past a fixed time bound on a command it runs for an anchor, a data point, validation or a process.
measure: Thirty seconds after such a command starts, the backbone kills it and reads it as giving no result. A command started inside another such run has at most the time that run has left.
applies-to: "Every command the backbone runs to resolve an anchor, fill a data point or join validation, and every command a process's definition declares. An agent run, `pkit agents run`, is outside it: its bound is the limit its caller sets, and thirty seconds more."
actors:
  - ACT-ci-pipeline
refines: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/command_runner.py
        - tests/test_command_runner.py
        - tests/test_friction_anchor_kinds.py
        - tests/test_data_points.py
        - tests/test_validators.py
      record:
        - COR-050#2
        - COR-052#6
        - ADR-057#3
        - ADR-057#5
        - COR-055#3
        - ADR-058#4
      artefact:
        - ACT-ci-pipeline
---

# REQ-006 · Quality · The backbone stops a command it runs for an anchor, a data point, validation or a process after thirty seconds

**Verified by:** Tests lower the bound to one second, and run a command that outlives it in each of the four uses. They find that:

- each run ends within the bound, and gives no result
- where the command started a program of its own, that program is stopped too
- a run's own bound is thirty seconds
- a run inside another has no more than the time its caller has left

No test covers a program the command starts outside the command's own group, which the kill does not reach.

**Rationale:** The CI pipeline runs every check with no person to reply, and gates the merge on its exit status. A check that waited on a command for ever would never exit. COR-050 [point](../../glossary.md#term-point--point) 2 bounds the time of a command that resolves an [anchor](../../glossary.md#term-anchor--anchor), so that a check "never hangs". COR-052 point 6 puts a command that fills a [data point](../../glossary.md#term-data-point--data-point) under the same limits, and COR-055 point 3 puts one that joins [validation](../../glossary.md#term-validation--validation) there.

ADR-057 point 3 fixes the bound at thirty seconds, "the same thirty seconds the predicate runner uses", so a [process](../../glossary.md#term-process--process)'s commands share it. ADR-058 point 4 applies it to validation unchanged. The [backbone](../../glossary.md#term-backbone--backbone) enforces the bound itself, so this is a quality it reaches, not a limit it trusts. A command that overruns gives no result, which REQ-004 keeps from reading as a clean one.
