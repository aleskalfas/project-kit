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
        - src/project_kit/capability_plans.py
        - src/project_kit/provisioning.py
        - src/project_kit/sync.py
        - src/project_kit/validate.py
        - src/project_kit/default_branch.py
      record: [COR-050, COR-053, COR-054, ADR-009, ADR-049]
      artefact: [UC-xx1, UC-xx2, UC-xx3, UC-xx4, UC-xx5, ACT-developer, ACT-ci-pipeline]
---

# JRN-xxx — Adopt the methodology in a project

**Goal:** Adopt the methodology in my project, and make my merges wait on its checks.

**Other actors:**

- **Developer** (`ACT-developer`): lands the install and the settings on the default branch, between steps 5 and 6. Each later change of theirs must pass the same checks in their clone as in the pipeline.
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
  - **Risk:** a private install shows as any other, since status never shows the visibility (ADR-009 point 3 and `status.py`).
- **UC-xx2 → UC-xx3:**
  - **Postconditions:** the adopter has seen the backbone's version, the capabilities installed and the suggestions (UC-xx2).
  - **Preconditions:** the methodology is installed in the project. UC-xx1 made that true, not UC-xx2 (UC-xx3).
  - **Risk:** the backbone may miss the capability's `requires_backbone` range, which status does not show. `pkit capabilities install <name> --plan` shows it before the install (COR-053 point 8).
- **UC-xx3 → UC-xx2:**
  - **Postconditions:** the capability is registered in `.pkit/manifest.yaml`, with its skills and agents deployed and its query commands provisioned (UC-xx3).
  - **Preconditions:** none (UC-xx2).
  - **Risk:**
    - Installed offline, the capability's query commands give no answer until `pkit sync` runs online (`provisioning.py`).
    - A role that another installed capability provides conflicts until the adopter selects one (COR-053 points 1 and 7). The adopter does that in `UC-xx6 — Choose which installed capability provides a role`.
- **UC-xx2 → UC-xx4:**
  - **Postconditions:** the adopter has seen the documentation roots, the friction mode and the declared places, each with its source (UC-xx2).
  - **Preconditions:** the methodology is installed in the project. UC-xx1 made that true (UC-xx4).
  - **Risk:** status does not show the default branch (`status.py`). A project that merges into another branch than `main` may leave it undeclared (COR-054 point 1).
- **UC-xx4 → UC-xx5:**
  - **Postconditions:** `.pkit/project/config.yaml` holds the settings, and `pkit validate` reports no error in them, in the adopter's clone (UC-xx4).
  - **Preconditions:** the install and the settings are on the default branch. The developer's `UC-xx7 — Land a change on the default branch` made that true, not UC-xx4 (UC-xx5).
  - **Risk:**
    - A private install never lands, so the pipeline's `pkit validate` fails on a missing `.pkit/` (ADR-009 point 3 and `validate.py`).
    - Without a pin, the pipeline runs whatever pkit it installs. An older one makes `pkit sync` refuse, and a newer one syncs its own content (ADR-049, #1212 and `sync.py`).
    - A pipeline that skips `pkit sync` fails `pkit validate` with "environment not provisioned — run `pkit sync`".
    - In `warning` mode the change check passes whatever it finds, and it stays dormant until a place is declared (COR-050 points 12 and 15).
    - Once an artefact is anchored, an undeclared default branch gives the change check a wrong base, or none (COR-054 points 1 and 4).

**Postconditions:** the project's pull requests merge only once the pipeline's run of the methodology's checks passes, under the settings the project declared.

**Minimal guarantees:**

- Until the pipeline requires the checks, no merge waits on them. So a project that stops at any step merges as before (COR-050 point 12).
- A step that fails keeps its own use case's minimal guarantees, such as `pkit init` refusing an existing install before it writes anything (UC-xx1).
