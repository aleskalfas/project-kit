---
id: REQ-007
title: A query command is offline, read-only and deterministic
status: active
statement: A query command needs no network, changes nothing in the project and is deterministic.
measure: Once the checkout is provisioned, a query command gives a result with the network cut off, and leaves each tracked file as it was. Run twice over the same state of the repository, and the same anchor where it resolves one, it prints the same output.
applies-to: Every query command a component registers to resolve an anchor, fill a data point, join validation or give the default paths of a capability. The constraint holds whichever command of the backbone runs the query.
obligation: v1:sha256:7e462c907138802caa0600b3779f503cba0dcaefe0eaddfcbc7be80a39b875d5
actors:
  - ACT-ci-pipeline
  - ACT-developer
refines: []
pkit:
  friction:
    anchors:
      path:
        - tests/test_package_validate.py
        - tests/test_friction_anchor_kinds.py
        - tests/test_data_points.py
        - tests/test_validators.py
        - tests/test_write_categories.py
        - src/project_kit/package_validate.py
        - src/project_kit/command_runner.py
        - src/project_kit/write_categories.py
      record:
        - COR-050#2
        - COR-052#6
        - ADR-057#3
        - ADR-057#4
        - COR-055#3
        - ADR-058#4
        - COR-073#3
        - ADR-088#2
      artefact:
        - ACT-ci-pipeline
        - ACT-developer
---

# REQ-007 · Constraint · A query command is offline, read-only and deterministic

**Verified by:** A [component](../../glossary.md#term-component--component) declares the three obligations on each [query command](../../glossary.md#term-query-command--query-command), as `query-contract: true`. [Validation](../../glossary.md#term-validation--validation) reports a command registered for one of the four uses without it, and the [backbone](../../glossary.md#term-backbone--backbone) refuses to start one. Tests find both, for each use. Tests also find that each run is marked offline, so the command can tell, and that a [base](../../glossary.md#term-base--base) a pipeline names never reaches it.

Nothing holds a running command to the obligations. No layer stops its use of the network, and [ADR-057 point 4](../../../../architecture/decisions/ADR-057-backbone-engines-and-command-limits.md#4-what-nothing-here-confines-stated) leaves the rest to review, naming no [reviewer](../../glossary.md#term-reviewer--reviewer).

**Imposed by:** [COR-050 point 2](../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#2-anchors) lays the three obligations on a command that resolves an [anchor](../../glossary.md#term-anchor--anchor). [COR-052 point 6](../../../../../.pkit/decisions/core/COR-052-slots.md#6-command-fillers-and-failure) lays them on one that fills a [data point](../../glossary.md#term-data-point--data-point). [COR-055 point 3](../../../../../.pkit/decisions/core/COR-055-validation.md#3-a-component-joins-by-naming-a-command) runs a command that joins [validation](../../glossary.md#term-validation--validation) under the same limits, and [ADR-058 point 4](../../../../architecture/decisions/ADR-058-validator-registry.md#4-an-installed-component-registers-its-validators-in-package-metadata) asks the same declaration of it. [COR-073 point 3](../../../../../.pkit/decisions/core/COR-073-capability-grant-defaults.md#3-a-capability-may-name-a-default-which-its-own-query-answers) and [ADR-088 point 2](../../../../architecture/decisions/ADR-088-capability-default-write-paths.md#2-the-default-query-prints-one-document-of-paths) run a [capability](../../glossary.md#term-capability--capability)'s query for the default of an [overlay category](../../glossary.md#term-overlay-category--overlay-category) under the same limits.

Each such command is code a [component](../../glossary.md#term-component--component) ships, which the [backbone](../../glossary.md#term-backbone--backbone) runs but cannot confine. So the backbone requires the component to declare the obligations, and trusts the declaration ([ADR-057 point 4](../../../../architecture/decisions/ADR-057-backbone-engines-and-command-limits.md#4-what-nothing-here-confines-stated)).

The obligations exist so that a check gives the same result wherever and whenever it runs (COR-050 point 2). Once its checkout is provisioned, the CI pipeline runs the checks offline. A developer who runs them before pushing gets the result the CI pipeline will. A command that writes a capability's default asks its query afresh, so the same state of the repository writes the same default anywhere.

The backbone cannot enforce the obligations, so they are a constraint it takes as given, unlike the time bound of [REQ-006](../quality/REQ-006-command-time-bound.md), which it enforces.
