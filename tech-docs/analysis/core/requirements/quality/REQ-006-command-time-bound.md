---
id: REQ-006
title: The backbone stops a command it runs for an anchor, a data point, validation, a capability's default or a process after thirty seconds
status: active
statement: The backbone never waits past a fixed time bound on the commands it runs for anchors, data points, validation, capabilities' defaults or processes.
measure: Thirty seconds after such a command starts, the backbone kills it and reads it as giving no result. A command started inside another such run has at most the time that run has left.
applies-to: "Every command the backbone runs to resolve an anchor, fill a data point, join validation or answer the default paths of a capability. It also covers every command a process's definition declares. An agent run, `pkit agents run`, is outside it: its bound is the limit its caller sets, and thirty seconds more."
obligation: v1:sha256:6c9759d5d6238dad16b018ee7a56766a68f1394e7b02073527eec8aba5e4d37a
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
        - tests/test_write_categories.py
      record:
        - COR-050#2
        - COR-052#6
        - ADR-057#3
        - ADR-057#5
        - COR-055#3
        - ADR-058#4
        - COR-073#3
        - ADR-088#2
      artefact:
        - ACT-ci-pipeline
---

# REQ-006 · Quality · The backbone stops a command it runs for an anchor, a data point, validation, a capability's default or a process after thirty seconds

**Verified by:** Tests lower the bound to one second, and run a command that outlives it in each of the five uses. They find that:

- each run ends within the bound, and gives no result
- where the command started a program of its own, that program is stopped too
- a run's own bound is thirty seconds
- a run inside another has no more than the time its caller has left

No test covers a program the command starts outside the command's own group, which the kill does not reach.

**Rationale:** The CI pipeline runs every check with no person to reply, and gates the merge on its exit status. A check that waited on a command for ever would never exit. [COR-050 point 2](../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#2-anchors) bounds the time of a command that resolves an [anchor](../../glossary.md#term-anchor--anchor), so that a check "never hangs". [COR-052 point 6](../../../../../.pkit/decisions/core/COR-052-slots.md#6-command-fillers-and-failure) puts a command that fills a [data point](../../glossary.md#term-data-point--data-point) under the same limits, and [COR-055 point 3](../../../../../.pkit/decisions/core/COR-055-validation.md#3-a-component-joins-by-naming-a-command) puts one that joins [validation](../../glossary.md#term-validation--validation) there.

[ADR-057 point 3](../../../../architecture/decisions/ADR-057-backbone-engines-and-command-limits.md#3-query-commands-declare-the-query-contract-the-engine-that-runs-one-enforces-the-bound-and-reads-the-answer-failing-closed) fixes the bound at thirty seconds, "the same thirty seconds the predicate runner uses", so a [process](../../glossary.md#term-process--process)'s commands share it. [ADR-058 point 4](../../../../architecture/decisions/ADR-058-validator-registry.md#4-an-installed-component-registers-its-validators-in-package-metadata) applies it to validation unchanged, and [ADR-088 point 2](../../../../architecture/decisions/ADR-088-capability-default-write-paths.md#2-the-default-query-prints-one-document-of-paths) to the query that answers a [capability](../../glossary.md#term-capability--capability)'s default ([COR-073 point 3](../../../../../.pkit/decisions/core/COR-073-capability-grant-defaults.md#3-a-capability-may-name-a-default-which-its-own-query-answers)). The [backbone](../../glossary.md#term-backbone--backbone) enforces the bound itself, so this is a quality it reaches, not a limit it trusts. A command that overruns gives no result, which [REQ-004](REQ-004-missing-answer-never-clean.md) keeps from reading as a clean one.
