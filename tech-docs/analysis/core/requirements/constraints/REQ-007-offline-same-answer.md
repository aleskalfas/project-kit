---
id: REQ-007
title: A command that resolves an anchor, fills a data point or joins validation is offline, read-only and deterministic
status: active
statement: A command that resolves an anchor, fills a data point or joins validation needs no network, changes nothing in the project and is deterministic.
measure: Once the checkout is provisioned, the command gives an answer with the network cut off, and leaves each file the project tracks as it was. Run twice over the same state of the repository, and the same anchor where it resolves one, it prints the same output.
applies-to: Every command a component registers to resolve an anchor, fill a data point or join validation, whichever command of the backbone runs it.
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
      record:
        - COR-050#2
        - COR-052#6
        - ADR-057#3
        - ADR-057#4
        - COR-055#3
        - ADR-058#4
      artefact:
        - ACT-ci-pipeline
        - ACT-developer
---

# REQ-007 · Constraint · A command that resolves an anchor, fills a data point or joins validation is offline, read-only and deterministic

**Verified by:** A component declares the three obligations on each such command, as `query-contract: true`. Validation reports a command registered for one of the three uses without it, and the backbone refuses to start one. Tests find both, for each use. Tests also find that each run is marked offline, so the command can tell, and that a base a pipeline names never reaches it.

Nothing holds a running command to the obligations. No layer stops its use of the network, and ADR-057 point 4 leaves the rest to review, naming no reviewer.

**Imposed by:** COR-050 point 2 lays the three obligations on a command that resolves an anchor. COR-052 point 6 lays them on one that fills a data point. COR-055 point 3 runs a command that joins validation under the same limits, and ADR-058 point 4 asks the same declaration of it.

Each such command is code a component ships, which the backbone runs but cannot confine. So the backbone requires the component to declare the obligations, and trusts the declaration (ADR-057 point 4).

The obligations exist so that a check gives the same answer wherever and whenever it runs (COR-050 point 2). Once its checkout is provisioned, the CI pipeline runs the checks offline. A developer who runs them before pushing gets the answer the CI pipeline will. The backbone cannot enforce the obligations, so they are a constraint it takes as given, unlike the time bound of REQ-006, which it enforces.
