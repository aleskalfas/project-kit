---
id: JRN-xxx
title: Adopt the methodology in a project
status: active
actor: ACT-adopter
involves: [ACT-developer, ACT-ci-pipeline]
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
      artefact: [UC-xx1, UC-xx2, UC-xx3, UC-xx4, UC-xx5, ACT-adopter, ACT-developer, ACT-ci-pipeline]
---

# JRN-xxx — Adopt the methodology in a project

**Goal:** Adopt the methodology in my project, and make my merges wait on its checks.

**Other actors:**

- **Developer** (`ACT-developer`): lands the install, the settings and the pipeline's job on the default branch, so later pull requests carry them. Each later change of theirs must pass the same checks in their clone as in the pipeline.
- **CI pipeline** (`ACT-ci-pipeline`): runs the checks with no person to answer, at the project's version once the project is pinned (ADR-049).

**Preconditions:** None.

**Assumptions:**

- The hosting service lets a project require a check's status before a merge. The checks bind only through it (COR-050 point 12).
- The pipeline reaches the network on checkout, so `pkit sync` can provision the query commands (`provisioning.py`).

**Trigger:** the adopter decides that the project will follow the methodology.

**Steps:**

1. UC-xx1 — The adopter installs the methodology into the project with `pkit init`.
2. UC-xx2 — The adopter sees how the methodology is wired into the project, with `pkit status`.
3. UC-xx3 — The adopter installs a capability the project needs, with `pkit capabilities install <name>`.
4. UC-xx2 — The adopter sees the wiring again, now with the capability's roles and points.
5. UC-xx4 — The adopter declares the project's settings in `.pkit/project/config.yaml`, and `pkit validate` passes.
6. UC-xx5 — The adopter has the project's pipeline run the methodology's checks, and makes them a required status.

**Seams:**

- **UC-xx1 → UC-xx2:**
  - **Postconditions:** the methodology is installed in `.pkit/` at the project root, with its version in `.pkit/manifest.yaml` (UC-xx1).
  - **Preconditions:** none. Status runs in any project, and says so where nothing is installed (UC-xx2).
  - **Risk:** a private install shows as any other, since status never shows the visibility. Only `pkit visibility` reports it (ADR-009 and `status.py`).
- **UC-xx2 → UC-xx3:**
  - **Postconditions:** the adopter has seen the backbone's version and the capabilities available, with none installed (UC-xx2).
  - **Preconditions:** none. The install checks for `.pkit/manifest.yaml` itself, and refuses without it (UC-xx3 and `capabilities.py`).
  - **Risk:** a capability that requires another, not yet installed, is refused (COR-030). `pkit capabilities install <name> --plan` shows the requirement first (COR-053 point 8).
- **UC-xx3 → UC-xx2:**
  - **Postconditions:** the capability is registered in `.pkit/manifest.yaml`, with its skills and agents deployed and its query commands provisioned (UC-xx3).
  - **Preconditions:** none (UC-xx2).
  - **Risk:**
    - Installed offline, the capability's query commands give no answer until `pkit sync` runs online (`provisioning.py`).
    - Status may suggest another capability, one that would provide a role the new one targets (COR-053 point 8). Installing it repeats steps 3 and 4.
- **UC-xx2 → UC-xx4:**
  - **Postconditions:** the adopter has seen the documentation roots, the friction mode and the declared places, each with its source (UC-xx2).
  - **Preconditions:** none. `pkit validate` checks for `.pkit/` itself, and refuses without it (UC-xx4 and `validate.py`).
  - **Risk:** status does not show the default branch (`status.py`). A project that merges into another branch than `main` may leave it undeclared (COR-054 point 1).
- **UC-xx4 → UC-xx5:**
  - **Postconditions:** `.pkit/project/config.yaml` holds the settings, and `pkit validate` reports no error in them, in the adopter's clone (UC-xx4).
  - **Preconditions:** none. The pipeline's first pkit command checks for `.pkit/` itself, and refuses without it (UC-xx5 and `validate.py`).
  - **Risk:**
    - Later pull requests carry the install, the settings and the pipeline's job only once they are on the default branch. The developer's `UC-xx7 — Land a change on the default branch` puts them there.
    - A private install is never committed, so the pipeline's `pkit sync` and `pkit validate` fail on a missing `.pkit/` (ADR-009 point 3 and `validate.py`).
    - Without a pin, the pipeline runs whatever pkit it installs. An older one makes `pkit sync` refuse, and a newer one syncs its own content (ADR-049, #1212 and `sync.py`).
    - A pipeline that skips `pkit sync` fails `pkit validate` with "environment not provisioned — run `pkit sync`".
    - In `warning` mode the change check passes whatever it finds (COR-050 point 12). It stays dormant until something in a declared place carries the methodology's container (COR-050 point 15).
    - Once an artefact is anchored, an undeclared default branch gives the change check a wrong base, or none (COR-054 points 1 and 4).

**Postconditions:** the project's pull requests merge only once the pipeline's run of the methodology's checks passes, under the settings the project declared.

**Minimal guarantees:**

- Until the pipeline requires the methodology's checks, a merge made through the hosting service waits on none of them. So a project that stops at any step merges as before (COR-050 point 12 and `ACT-ci-pipeline`).
- A step that fails keeps its own use case's minimal guarantees, such as `pkit init` refusing an existing install before it writes anything (UC-xx1).
