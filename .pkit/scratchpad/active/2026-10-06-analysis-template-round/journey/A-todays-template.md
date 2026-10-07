---
id: JRN-xxx
title: Adopt the methodology in a project
status: active
actor: ACT-adopter
steps: [UC-xx1, UC-xx2, UC-xx3, UC-xx2, UC-xx4, UC-xx5]
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/install.py
        - src/project_kit/visibility.py
        - src/project_kit/status.py
        - src/project_kit/capabilities.py
        - src/project_kit/capability_plans.py
        - src/project_kit/provisioning.py
        - src/project_kit/sync.py
        - src/project_kit/validate.py
        - src/project_kit/friction_check.py
        - src/project_kit/default_branch.py
      record: [COR-030, COR-050, COR-053, COR-054, ADR-009, ADR-049]
      artefact: [UC-xx1, UC-xx2, UC-xx3, UC-xx4, UC-xx5, ACT-adopter]
---

# JRN-xxx — Adopt the methodology in a project

**Starts:** the adopter has a project in a git repository, with no methodology installed. By the end, they want the project's merges to wait on the methodology's checks.

**Steps:**

1. UC-xx1 — The adopter installs the methodology into the project with `pkit init`.
2. UC-xx2 — The adopter sees how the methodology is wired into the project, with `pkit status`.
3. UC-xx3 — The adopter installs a capability the project needs, with `pkit capabilities install <name>`.
4. UC-xx2 — The adopter sees the wiring again, now with the capability's roles and points.
5. UC-xx4 — The adopter declares the project's settings in `.pkit/project/config.yaml`, and `pkit validate` passes.
6. UC-xx5 — The adopter has the project's pipeline run the methodology's checks, and makes them a required status.

**Seams to watch:** where the path passes from one use case to the next — what must carry over, and how it could break.

- **UC-xx1 → UC-xx2:** the install carries over as `.pkit/` at the project root, which `pkit status` resolves as `pkit init` did. It misleads where the adopter keeps the install private, as `init`'s closing steps offer. Status shows this clone's wiring and never its visibility, which only `pkit visibility` reports (ADR-009 and `status.py`). A private install is in this clone alone, so no other clone holds it, the pipeline's included (ADR-009 point 3).
- **UC-xx2 → UC-xx3:** status lists the capabilities available by name, and none installed. Status does not say what each capability requires. A capability that requires another, not yet installed, is refused at install (COR-030 and `capabilities.py`). `pkit capabilities install <name> --plan` shows that requirement, and each connection the install would make, before anything is written (COR-053 point 8).
- **UC-xx3 → UC-xx2:** the capability carries over as an entry in `.pkit/manifest.yaml`, with its skills and agents deployed and its query commands provisioned. Two things can follow:
  - **Offline:** the install only warns that it could not provision a query command. Until `pkit sync` runs online, each such command gives no answer, and `pkit validate` says "environment not provisioned — run `pkit sync`" (`provisioning.py`).
  - **A suggestion:** the new capability may target a role that nothing installed provides. Status then suggests a capability that would provide it, and installing that one repeats steps 3 and 4 (COR-053 point 8).
- **UC-xx2 → UC-xx4:** status shows the settings the next step changes: the documentation roots and the friction mode, each with its source, and the declared places. Status does not show the default branch (`status.py`). So an adopter whose pull requests merge into another branch than `main` sees nothing to declare, and the default stays `main` (COR-054 point 1).
- **UC-xx4 → UC-xx5:** the pipeline checks each pull request with the install and the settings that pull request carries. Six things decide whether its checks hold:
  - **The landing:** later pull requests start from the default branch. So the pipeline gates them only once the install, the settings and its own job are there. They get there by the developer's use case `UC-xx6 — Land a change on the default branch`, which is no step of the adopter's journey.
  - **A private install:** it is never committed, so the pipeline's checkout holds no `.pkit/`. Its first pkit command fails with "`.pkit/ does not exist. Run 'pkit init' first.`" (ADR-009 point 3, with `sync.py` and `validate.py`).
  - **No pin:** `init` writes none, so the pipeline runs whatever pkit it installs (ADR-049). An older one makes `pkit sync` refuse, and a newer one syncs its own content over the project's (#1212 and `sync.py`). `pkit pin` runs every command at the project's version.
  - **No `pkit sync` on checkout:** the capability's query commands are not provisioned. `pkit validate` then fails with "environment not provisioned — run `pkit sync`".
  - **The friction mode:** it defaults to `warning`, so the change check reports what it finds and passes (COR-050 point 12). It stays dormant until something in a declared place carries the methodology's container (COR-050 point 15 and `friction_check.py`).
  - **The base:** once an artefact is anchored, the change check compares with the default branch, `main` unless declared. A project that merges into another branch then compares with the wrong base. Where no `main` resolves, the check refuses, unless the pipeline names the base (COR-054 points 3 and 4).

**Done when:** the project's pull requests merge only once the pipeline's run of the methodology's checks passes, under the settings the project declared.
