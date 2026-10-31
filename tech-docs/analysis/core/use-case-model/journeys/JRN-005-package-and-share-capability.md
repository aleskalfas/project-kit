---
id: JRN-005
title: Package a discipline as a capability, and make it ready to share
status: active
actor: ACT-component-author
steps:
  - UC-015
  - UC-016
  - UC-017
  - UC-018
relies-on:
  - UC-049
requirements: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/scaffolds.py
        - src/project_kit/cli.py
        - src/project_kit/capabilities.py
        - src/project_kit/manifest.py
        - src/project_kit/connections.py
        - src/project_kit/release.py
        - src/project_kit/sync.py
      record:
        - COR-017
        - COR-030
        - COR-031#D1
        - COR-031#D4
        - COR-053#1
        - COR-044#2
        - ADR-040#4
      artefact:
        - ACT-component-author
        - UC-015
        - UC-016
        - UC-017
        - UC-018
        - UC-049
---

# JRN-005 — Package a discipline as a capability, and make it ready to share

**Goal:** Package a recurring discipline as a capability my repository runs, and know it is ready for my other repositories to pull.

**Steps:**

1. [UC-015](../use-cases/010-develop/UC-015-package-capability.md) — Package a recurring discipline as a capability
   - **Needs from [UC-049](../use-cases/050-adopt/UC-049-install-system.md) (outside this journey):** the [system](../../glossary.md#term-system--system) installed in the [project](../../glossary.md#term-project--project), its [manifest](../../glossary.md#term-manifest--manifest) recording the [backbone](../../glossary.md#term-backbone--backbone)'s [version](../../glossary.md#term-version--version). The [stamp](../../glossary.md#term-stamp--stamp) writes the [capability](../../glossary.md#term-capability--capability)'s [range](../../glossary.md#term-range--range) on the backbone from that version, up to the next major (`scaffolds.py`).
2. [UC-016](../use-cases/010-develop/UC-016-keep-capability.md) — Keep a capability I wrote in my own repository
   - **Needs from step 1 (UC-015):** the capability's subtree, with its [package metadata](../../glossary.md#term-package-metadata--package-metadata). The stamp registers nothing, so none of the capability's [skills](../../glossary.md#term-skill--skill) or [agent definitions](../../glossary.md#term-agent-definition--agent-definition) is deployed before this step. The registration refuses a tree that breaks its own package metadata, README or schemas ([COR-031 point D1](../../../../../.pkit/decisions/core/COR-031-capability-origin.md#d1--the-lifecycle-excludes-incubated-capabilities-from-source-reconciliation-but-not-from-self-consistency-checks)). It also refuses a range the recorded backbone lies outside, and a skill or agent definition whose name the project holds already ([COR-030](../../../../../.pkit/decisions/core/COR-030-capability-dependencies.md) and `cli.py`).
   - **Needs from UC-049 (outside this journey):** an [adapter](../../glossary.md#term-adapter--adapter) for the project's [harness](../../glossary.md#term-harness--harness). Once the capability is registered, the adapter's scripts deploy its skills and agent definitions where the harness reads them.
3. [UC-017](../use-cases/010-develop/UC-017-connect-capability.md) — Give my capability roles, data points and processes others connect to
   - **Needs from step 2 (UC-016):** the capability recorded in the manifest, with the [component origin](../../glossary.md#term-component-origin--component-origin) `incubated-in-repo`. The backbone reads the package metadata and the [processes](../../glossary.md#term-process--process) only of a capability the manifest records. A [role](../../glossary.md#term-role--role) the capability provides that another installed capability provides too fails [validation](../../glossary.md#term-validation--validation), until the project selects one ([COR-053 point 1](../../../../../.pkit/decisions/core/COR-053-connection-points.md#1-roles)).
4. [UC-018](../use-cases/010-develop/UC-018-check-shareable.md) — Know my capability is ready to share
   - **Needs from step 1 (UC-015):** the package metadata's `component.version`, and its range on the backbone. The stamp writes `0.1.0`, and a range bounded on both sides. The check passes only such a range, so it fails an edit that drops the upper bound ([ADR-040 point 4](../../../../architecture/decisions/ADR-040-external-source-write-path.md#4-ordering-load-bearing-fetch--read-fetched-manifest--compatibility-gate--activate-or-refuse) and `release.py`).

**Variants:**

- **2a.** The author shares the [capability](../../glossary.md#term-capability--capability) without running it in this repository. The path goes on at step 4.
- **3a.** The capability offers nothing that other [components](../../glossary.md#term-component--component) connect to. The path goes on at step 4.
- **4a.** The author keeps the capability for this repository alone. The path ends after step 3.

**Postconditions:** The [capability](../../glossary.md#term-capability--capability) lies in its own subtree in the [project](../../glossary.md#term-project--project), recorded as `incubated-in-repo`, with its [skills](../../glossary.md#term-skill--skill) and [agent definitions](../../glossary.md#term-agent-definition--agent-definition) deployed. `pkit validate` passes the capability's [roles](../../glossary.md#term-role--role), [connection points](../../glossary.md#term-connection-point--connection-point) and [processes](../../glossary.md#term-process--process). The capability's [package metadata](../../glossary.md#term-package-metadata--package-metadata) declares a [version](../../glossary.md#term-version--version), and a [range](../../glossary.md#term-range--range) on the [backbone](../../glossary.md#term-backbone--backbone) bounded on both sides. So a project that pulls the capability can pin it by version, and gate it against its own backbone.

**Minimal guarantees:**

- Wherever the path stops, [sync](../../glossary.md#term-sync--sync) never copies over the [capability](../../glossary.md#term-capability--capability)'s subtree. Uninstall deletes the subtree only on `--purge` (COR-031 points [D1](../../../../../.pkit/decisions/core/COR-031-capability-origin.md#d1--the-lifecycle-excludes-incubated-capabilities-from-source-reconciliation-but-not-from-self-consistency-checks) and [D4](../../../../../.pkit/decisions/core/COR-031-capability-origin.md#d4--every-lifecycle-verb-honours-origin-removal-never-destroys-adopter-owned-source)).
- A [stamp](../../glossary.md#term-stamp--stamp) or a registration that refuses writes nothing, since each checks before its first write (`scaffolds.py` and `cli.py`).
- Where the script behind a [process](../../glossary.md#term-process--process)'s state fails, or cannot run, no subject moves from where it stands ([COR-044 point 2](../../../../../.pkit/decisions/core/COR-044-process-authoring-layer.md#2-the-teeth-actor-is-a-new-core-agent-owner-scoped)).
