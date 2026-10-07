---
id: JRN-xxx
title: Adopt the methodology in a project
status: active
actor: ACT-adopter
steps: [UC-xx1, UC-xx2, UC-xx3, UC-xx2, UC-xx4, UC-xx5]
relies-on: [UC-xx6]
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
      artefact: [UC-xx1, UC-xx2, UC-xx3, UC-xx4, UC-xx5, UC-xx6, ACT-adopter]
---

# JRN-xxx — Adopt the methodology in a project

**Goal:** Adopt the methodology in my project, and make my merges wait on its checks.

**Steps:**

1. UC-xx1 — Install the methodology into a project
2. UC-xx2 — See how the methodology is wired into the project
   - **Needs from step 1 (UC-xx1):** the install at `.pkit/` in the project root, which `pkit status` resolves as `pkit init` did. A private install shows as any other, since status never shows the visibility. Only `pkit visibility` reports it (ADR-009 and `status.py`).
3. UC-xx3 — Install a capability
   - **Needs from step 2 (UC-xx2):** the name of a capability available, as status lists it. Status does not say what each capability requires. A capability that requires another, not yet installed, is refused (COR-030 and `capabilities.py`). `pkit capabilities install <name> --plan` shows the requirement before anything is written (COR-053 point 8).
4. UC-xx2 — See how the methodology is wired into the project
   - **Needs from step 3 (UC-xx3):** the capability registered in `.pkit/manifest.yaml`, with its skills and agents deployed and its query commands provisioned. Installed offline, the capability's query commands give no answer until `pkit sync` runs online (`provisioning.py`).
5. UC-xx4 — Declare the project's settings
   - **Needs from step 4 (UC-xx2):** the documentation roots and the friction mode, each with its source, and the declared places, as status shows them. Status does not show the default branch (`status.py`). So an adopter whose pull requests merge into another branch than `main` sees nothing to declare (COR-054 point 1).
6. UC-xx5 — Make the project's merges wait on the methodology's checks
   - **Needs from step 1 (UC-xx1):** the install, committed with the project. A private install is never committed, as in 1a. `init` writes no pin, so the pipeline runs whatever pkit it installs (ADR-049). An older one makes `pkit sync` refuse, and a newer one syncs its own content over the project's (#1212 and `sync.py`).
   - **Needs from step 3 (UC-xx3):** the capability's query commands, provisioned on the pipeline's checkout. A pipeline that skips `pkit sync` fails `pkit validate` with "environment not provisioned — run `pkit sync`".
   - **Needs from step 5 (UC-xx4):** the settings in `.pkit/project/config.yaml`, as each pull request carries them. In `warning` mode the change check passes whatever it finds (COR-050 point 12). It stays dormant until something in a declared place carries the methodology's container (COR-050 point 15). Once an artefact is anchored, an undeclared default branch gives the change check a wrong base, or none (COR-054 points 1 and 4).
   - **Needs from UC-xx6 (outside this journey):** the install, the settings and the pipeline's job on the default branch, where later pull requests start. The developer's landing puts them there, and the pipeline gates later pull requests only once they are there.

**Variants:**

- **1a.** The adopter keeps the install private with `pkit visibility private`. At step 6 the pipeline's checkout holds no `.pkit/`, so its first pkit command fails (ADR-009 point 3 and `validate.py`). The adopter runs `pkit visibility shared` and commits the install, and the path rejoins at step 6.
- **4a.** Status suggests another capability, one that would provide a role the new one targets (COR-053 point 8). The adopter installs it, and the path rejoins at step 3.

**Postconditions:** the project's pull requests merge only once the pipeline's run of the methodology's checks passes, under the settings the project declared.

**Minimal guarantees:**

- Until the pipeline requires the methodology's checks, a merge made through the hosting service waits on none of them. So a project that stops at any step merges as before (COR-050 point 12 and `ACT-ci-pipeline`).
- A step that fails keeps its own use case's minimal guarantees, such as `pkit init` refusing an existing install before it writes anything (UC-xx1).
