---
id: UC-017
title: Give my capability roles, data points and processes others connect to
status: active
actor: ACT-component-author
other-actors:
  - ACT-ai-agent
after:
  - [UC-016]
requirements: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/connections.py
        - src/project_kit/data_points.py
        - src/project_kit/wiring_graph.py
        - src/project_kit/process_graph.py
        - src/project_kit/process_authoring.py
        - src/project_kit/process_dependencies.py
        - src/project_kit/process.py
        - src/project_kit/package_validate.py
        - src/project_kit/validators.py
        - src/project_kit/cli.py
        - .pkit/agents/core/process-author.md
        - .pkit/skills/core/process/process.md
      record:
        - COR-033
        - COR-038
        - COR-042
        - COR-044
        - COR-052
        - COR-053
        - ADR-051
      artefact:
        - ACT-component-author
        - ACT-ai-agent
---

# UC-017 — Give my capability roles, data points and processes others connect to

**Goal:** Give my capability roles, data points and processes that other components can connect to without naming it, and have the engine run and check them.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): runs the commands of steps 3, 6 and 7 for the author through the `process` skill. As the `process-author` agent, it writes the scripts behind a process's states and conditions. It writes only in the files the project grants it (COR-044 point 2 and ADR-051).

**Preconditions:**

- **From UC-016:** The capability is recorded in the project's manifest, so the backbone reads its package metadata and its processes.

**Assumptions:** None.

**Trigger:** The author wants other components to use what the capability knows or does, without depending on the capability by name.

**Main path:**

1. Under `connections` in the capability's package metadata, the author declares each role the capability provides, addressed `<publisher>::<role>` (COR-053 point 1).
2. Under `extension-points.accepts`, the author declares each data point the capability accepts, addressed `<publisher>::<role>:<point>`. Each gives its `schema_version`, its companion `schema`, its `description` and its `combination` policy (COR-052 and COR-053 point 2).
3. The author runs `pkit process new <capability>:<id> --state <id>=<meaning> … --transition <from>:<to>:<trigger>`, or has an AI agent run it through the `process` skill.
4. The system writes the process's definition, `schemas/<id>.yaml` in the capability. It writes one script for each state and each condition the process declares, and registers each in the package metadata's `commands`. Each script fails until someone writes it, so the process fails closed (COR-044 point 3).
5. The system prints `Stamped: <path>` and one `stub:` line for each script.
6. Where the process waits on another, the author runs `pkit process couple <capability>:<id> --upstream <address> …` (COR-038). Then the author runs `pkit capabilities refresh <capability>`, which regenerates the package metadata's `depends-on` list from the definitions (COR-053 point 4).
7. Where the wait is to be checked, the author also runs `pkit process hand-off …` (COR-042).
8. The author writes the script behind each state and condition. Where the project grants it the files, the `process-author` agent writes them (COR-044 points 1 and 2).
9. The author offers the process to other components, under `extension-points.offers` with `kind: process` and `process: <id>` (COR-053 point 2).
10. The author runs `pkit validate`. Its members `packages`, `connections` and `process` read what the capability declares. Each connection point lies under a role the capability provides, each companion schema is present, and each offered process has a definition.
11. The author runs `pkit connections graph`. The system draws each role, each connection point and what connects to each, such as `◇ accepts pkit::documentation:readers  [accepts · active]`.
12. The author runs `pkit process status <capability>:<id>`, with `--subject <key>` where the process keeps one subject for each key. The backbone's engine runs the script behind each state. It says which state the subject, the thing the process follows, is in, and which moves it may make (COR-033).

**Variants:**

- **1a.** Another installed capability provides one of the capability's roles. At step 10, `pkit validate` fails with ``role '<role>' is provided by <capabilities> and no provider is selected``, and names `pkit connections providers set` (COR-053 point 1).
- **4a.** A process of that id exists in the capability. The system refuses, since `process new` writes a process only once, and writes nothing. The path rejoins at step 3.
- **6a.** The author skips `pkit capabilities refresh`. At step 10, `pkit validate` fails with ``the generated `depends-on` list is stale``, and names the command. The path rejoins at step 6.
- **8a.** The project grants the `process-author` agent no file, since `process-authoring-targets` ships empty in `.pkit/agents/project/overlay.yaml`. The agent then proposes each script, and the author writes it (ADR-051 point 1).
- **8b.** The overlay has no key `process-authoring-targets`, as in a project that upgraded from before it. The adapter deploys no `process-author` agent, and the author writes each script (ADR-051 point 1).
- **10a.** A connection point lies under a role the capability does not provide, or its companion schema is missing. `pkit validate` fails on it, and the path rejoins at step 1.
- **12a.** The script behind a state still fails as stamped, or cannot run. The system prints ``couldn't evaluate <kind> predicate '<command>'``. It refuses each move with `position is indeterminate — a detection predicate could not be evaluated; refusing to move (fail-closed)` (COR-033).
- **12b.** The script behind a move's condition still fails as stamped. The system refuses that move with `gate refused:` and the script's reason, and allows the others (COR-033 P4).

**Postconditions:** The capability's package metadata declares its roles and its connection points. Each of its processes has a definition, with a script behind each state and condition. `pkit validate` passes them. `pkit connections graph` shows what connects to each connection point, and a component that connects through a role's address names no capability.

**Minimal guarantees:**

- Where the script behind a state fails, or cannot run, no subject moves from where it stands (COR-044 point 2 and `process.py`).
- A role that two installed capabilities provide fails validation until the project selects one (COR-053 point 1 and `connections.py`).
- A process stamp that fails leaves nothing written (`process_authoring.py`).
