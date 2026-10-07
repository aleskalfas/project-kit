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

**Goal in context:** Adopt the methodology in my project, and make my merges wait on its checks. It happens once for each project, on its first day, and steps 3 and 4 come again for each capability added later.

**Scope:** pkit's backbone, with the project's pipeline and its hosting service at step 6.

**Level:** summary. Each step is a user-goal use case.

**Stakeholders and interests:**

- **Adopter:** wants the methodology working within a day, with the project's own files left alone (`ACT-adopter`).
- **Developer:** lands the install, the settings and the pipeline's job on the default branch. They want each later change to pass the same checks in their clone as in the pipeline (`ACT-developer`).
- **CI pipeline:** runs the checks with no person to answer, at the project's version, against the base its run names (`ACT-ci-pipeline`).

**Precondition:** none. `pkit init` checks its target itself (1a).

**Minimal guarantees:**

- Until the pipeline requires the methodology's checks, a merge made through the hosting service waits on none of them. So a project that stops at any step merges as before (COR-050 point 12 and `ACT-ci-pipeline`).
- `pkit init` refuses an existing install before it writes anything, and points at `pkit sync` (the CLI reference).
- The install merges into the project's harness settings, never removing an entry, and keeps a `.pre-pkit` backup (COR-002 and the CLI reference).

**Success guarantees:** the project's pull requests merge only once the pipeline's run of the methodology's checks passes, under the settings the project declared.

**Trigger:** the adopter decides that the project will follow the methodology.

**Main success scenario:**

1. The adopter installs the methodology into the project (UC-xx1).
2. The adopter sees how the methodology is wired into the project (UC-xx2).
3. The adopter installs a capability the project needs (UC-xx3).
4. The adopter sees the wiring again, with the capability's roles and points (UC-xx2).
5. The adopter declares the project's settings, and they validate (UC-xx4).
6. The adopter makes the project's merges wait on the methodology's checks (UC-xx5). The developer lands the install, the settings and the pipeline's job on the default branch (UC-xx7).

**Extensions:**

- **1a.** The project already holds an install:
  - **1a1.** `pkit init` refuses before writing anything, and points at `pkit sync`.
  - **1a2.** The journey resumes at step 2.
- **1b.** The adopter keeps the install private with `pkit visibility private`:
  - **1b1.** At step 2, status shows the wiring, and only `pkit visibility` shows that it is private (ADR-009 and `status.py`).
  - **1b2.** At step 6, the pipeline's checkout holds no `.pkit/`, since the install was never committed. Its first pkit command fails (ADR-009 point 3 and `validate.py`).
  - **1b3.** The adopter runs `pkit visibility shared` and commits the install, and the journey resumes at step 6.
- **3a.** The capability requires another capability, not yet installed:
  - **3a1.** The install refuses, as its `--plan` showed (COR-030).
  - **3a2.** The adopter installs the required one first, and repeats step 3.
- **3b.** The install runs offline:
  - **3b1.** It warns that it could not provision the capability's query commands (`provisioning.py`).
  - **3b2.** Each gives no answer until `pkit sync` runs online, and the journey resumes at step 4.
- **4a.** Status suggests another capability, one that would provide a role the new one targets (COR-053 point 8):
  - **4a1.** The adopter reads it with `pkit capabilities show <name>`.
  - **4a2.** The adopter installs it, and the journey resumes at step 3.
- **5a.** The project's pull requests merge into another branch than `main`:
  - **5a1.** At step 4, status did not show the default branch (`status.py`).
  - **5a2.** The adopter declares `repository.default-branch`. Otherwise the change check later compares with the wrong base, or refuses where no `main` resolves (COR-054 points 1 and 4).
- **6a.** The pipeline installs another pkit than the project's version:
  - **6a1.** An older one makes `pkit sync` refuse, and a newer one syncs its own content over the project's (#1212 and `sync.py`).
  - **6a2.** The adopter pins the project with `pkit pin` (ADR-049), and the pipeline runs again.
- **6b.** The pipeline skips `pkit sync`:
  - **6b1.** `pkit validate` fails with "environment not provisioned — run `pkit sync`".
  - **6b2.** The adopter puts `pkit sync` before the checks, and the pipeline runs again.
- **6c.** The friction mode is still `warning`:
  - **6c1.** The change check reports what it finds and passes (COR-050 point 12).
  - **6c2.** The adopter sets `friction.mode` to `enforcing`, or leaves the check to report. Until something in a declared place carries the methodology's container, the check is dormant either way (COR-050 point 15).

**Technology and data variations:**

- **6.** The pipeline and its required statuses are the hosting service's, such as a GitHub workflow and a branch rule. The backbone ships no workflow (`ACT-ci-pipeline`).

**Related information:**

- **Frequency:** once for each project, and steps 3 and 4 again for each capability added.
- **Open issues:** none filed. `init`'s closing next steps and the CLI reference recommend different ways to put `pkit` on the path (PRJ-004).
