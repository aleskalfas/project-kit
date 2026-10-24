---
id: UC-025
title: Choose which installed capability provides a role
status: active
actor: ACT-adopter
other-actors:
  - ACT-operator
after:
  - [UC-023, UC-016]
requirements:
  - REQ-002
  - REQ-012
shortfalls:
  - at: 3
    issue: "#1765"
    record: ADR-034#1
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/cli.py
        - src/project_kit/connections_config.py
        - src/project_kit/connections.py
        - src/project_kit/status.py
        - src/project_kit/project_config.py
      record:
        - COR-053#1
        - COR-053#7
        - COR-048#5
        - ADR-034#1
      artefact:
        - ACT-adopter
        - ACT-operator
        - REQ-002
        - REQ-012
    revalidated:
      at: 2026-10-24T10:39:40Z
      outcome: unchanged
      unchanged-because: ACT-adopter's need says "Upgrade the system" for "Upgrade it", and "a version the whole project pins" for "a version pinned for the whole project". The need is the same, so this artefact holds.
---

# UC-025 — Choose which installed capability provides a role

**Goal:** Choose which installed capability provides a role.

**Other actors:**

- **Operator** (`ACT-operator`): is asked before `pkit connections providers set` writes in a repository other than the session's own, so no such write happens silently (REQ-012).

**Preconditions:** **From UC-023 or UC-016:** Two or more installed [capabilities](../../../glossary.md#term-capability--capability) provide one [role](../../../glossary.md#term-role--role). So the role has no provider until the [project](../../../glossary.md#term-project--project) selects one (COR-053 [point](../../../glossary.md#term-point--point) 1).

**Assumptions:** None.

**Trigger:** [Validation](../../../glossary.md#term-validation--validation) or `pkit status` names a [role](../../../glossary.md#term-role--role) that two installed [capabilities](../../../glossary.md#term-capability--capability) provide, or the adopter prefers another of its providers.

**Main path:**

1. The adopter runs `pkit status`. For the [role](../../../glossary.md#term-role--role), the [system](../../../glossary.md#term-system--system) prints `<role> — conflict: <providers> provide it and none is selected`, then `fix: pkit connections providers set <role> <capability>` for each provider.
2. The adopter runs `pkit connections providers set <role> <capability>`.
3. At its entry, before it reads anything, the system checks that the repository it would write in is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses (REQ-012).

> [!WARNING]
> **Not built yet:** `pkit connections providers set` runs no such check, and writes in whatever repository holds its working directory. ADR-034 [point](../../../glossary.md#term-point--point) 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

4. The system checks that the [capability](../../../glossary.md#term-capability--capability) is installed, and that it provides the role (COR-053 point 7).
5. The system shows the edit it would make to the [backbone configuration](../../../glossary.md#term-backbone-configuration--backbone-configuration): the entry `connections.providers.<role>` in `.pkit/project/config.yaml`. It asks `Set connections.providers.<role> = '<capability>' in .pkit/project/config.yaml?` (COR-048 point 5).
6. On a yes, the system writes the entry, and prints `set connections.providers.<role> = <capability>  (.pkit/project/config.yaml)`.
7. The adopter runs `pkit validate`. The role has its provider, so [validation](../../../glossary.md#term-validation--validation) passes it, and the [backbone](../../../glossary.md#term-backbone--backbone) resolves the role's [connection points](../../../glossary.md#term-connection-point--connection-point) through the selected capability.

**Variants:**

- **1a.** The adopter runs `pkit validate` first. It fails with `role '<role>' is provided by <providers> and no provider is selected`, naming the command that writes the selection (COR-053 [point](../../../glossary.md#term-point--point) 1).
- **2a.** The adopter passes `--dry-run`. The [system](../../../glossary.md#term-system--system) shows the edit it would make, prints `Dry run: nothing written.`, and writes nothing.
- **2b.** The adopter passes `--yes` with `--dry-run`. The system refuses with `--yes and --dry-run exclude each other: one writes, the other never does.`, and writes nothing.
- **4a.** The [capability](../../../glossary.md#term-capability--capability) is not installed. The system refuses, naming `pkit capabilities install <capability>` and the installed providers of the [role](../../../glossary.md#term-role--role), and writes nothing. The path rejoins at step 2.
- **4b.** The capability does not provide the role. The system refuses, naming the roles it provides and the installed providers of the role, and writes nothing. The path rejoins at step 2.
- **4c.** The entry names the capability already. The system prints `connections.providers.<role> is already <capability>; nothing to write.`, and the use case ends.
- **5a.** Standard input is no terminal, and the adopter gave no `--yes`. The system refuses, naming the command to run with `--yes`, and writes nothing (COR-048 point 5).
- **5b.** The adopter passes `--yes`. The system asks nothing, and the path goes on at step 6.
- **5c.** The adopter declines. The system writes nothing, and the use case ends.

**Postconditions:** The [backbone configuration](../../../glossary.md#term-backbone-configuration--backbone-configuration) names the [role](../../../glossary.md#term-role--role)'s provider. [Validation](../../../glossary.md#term-validation--validation) passes the role, and every [component](../../../glossary.md#term-component--component) that connects through the role's address reaches the selected [capability](../../../glossary.md#term-capability--capability) without naming it.

**Minimal guarantees:**

- A selection names only an installed [capability](../../../glossary.md#term-capability--capability) that provides the [role](../../../glossary.md#term-role--role) (COR-053 [point](../../../glossary.md#term-point--point) 7 and `connections_config.py`).
- With nobody to ask and no `--yes`, nothing is written (COR-048 point 5 and `project_config.py`).
- A role that two installed capabilities provide fails [validation](../../../glossary.md#term-validation--validation) until the [project](../../../glossary.md#term-project--project) selects one (COR-053 point 1 and `connections.py`).
