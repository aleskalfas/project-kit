---
id: JRN-001
title: Adopt the system
status: active
actor: ACT-adopter
steps:
  - UC-049
  - UC-021
  - UC-023
  - UC-006
relies-on:
  - UC-048
requirements: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/install.py
        - src/project_kit/visibility.py
        - src/project_kit/sync.py
        - src/project_kit/declared_rule_sets.py
        - src/project_kit/friction_check.py
        - src/project_kit/provisioning.py
      record:
        - COR-001
        - COR-017
        - COR-048#4
        - COR-050#12
        - COR-050#15
        - COR-051#6
        - COR-059#6
        - COR-059#9
        - PRJ-004
        - ADR-009#3
        - ADR-065#11
        - ADR-065#12
      artefact:
        - ACT-adopter
        - UC-049
        - UC-021
        - UC-023
        - UC-006
        - UC-048
---

# JRN-001 — Adopt the system

**Goal:** Install the system into my project with my backbone configuration and capabilities, and make my merges wait on its checks.

**Steps:**

1. UC-049 — Install the system into my project with one command
   - **Needs from UC-048 (outside this journey):** the CLI on the adopter's machine, at a release. A CLI installed from a branch or from main's head names the last release as its version, while its files may be newer. The project then records a version that vouches for no content (PRJ-004 and ADR-065 point 12).
2. UC-021 — Declare my project's backbone configuration once, and have it validated
   - **Needs from step 1 (UC-049):** the system installed in the project, with `.pkit/` to hold the backbone configuration. Where the adopter keeps the system out of the shared repository (UC-049 variant 12a), `.pkit/` is excluded whole. The team's clones then never hold the backbone configuration the adopter declares (ADR-009 point 3).
3. UC-023 — Add or remove a capability, and be told of a name collision
   - **Needs from step 1 (UC-049):** the version the project records, and the adapters that deploy the capability's skills and agent definitions. Outside the methodology's source repository, the capability is copied from the running CLI's distribution (UC-023 variant 6a). Under a CLI at another release than the project records, the capability's install stops before it reads anything (COR-059 point 9).
   - **Needs from step 2 (UC-021):** the internal documentation root, under which the capability's install creates a rule set of the project's own. A root changed by hand afterwards leaves that set where no place finds it, and validation fails on it (COR-051 point 6).
4. UC-006 — Make my merges wait on the system's checks
   - **Needs from step 1 (UC-049):** the system committed for the team, so each checkout the CI pipeline makes holds it. A checkout holds nothing of a system kept out of the shared repository (ADR-009 point 3). Under a CLI at another release than the project records, the CI job's `pkit sync` stops, and the job fails (COR-059 point 9).
   - **Needs from step 2 (UC-021):** the places the backbone configuration declares, which the change check reads beside those an installed capability declares. Where none is declared, or no artefact in them carries anchors, the change check is dormant and passes (COR-050 point 15). The merges then wait on validation and the project's other checks alone.
   - **Needs from step 3 (UC-023):** the capability, committed with its places and the commands it registers. A checkout holds nothing the capability's install provisioned, so the job runs `pkit sync` first (ADR-065 point 11). Otherwise a validator the capability registers finds its environment not provisioned, and validation fails (UC-006 variant 3a).

**Variants:**

- **1a.** The adopter keeps the system out of the shared repository (UC-049 variant 12a). No checkout the CI pipeline makes holds what the adopter sets up, so the path ends after step 3 (ADR-009 point 3).
- **2a.** The adopter keeps the default of every key of the backbone configuration. The path goes on at step 3, and the change check reads only the places the capabilities declare.
- **3a.** The project needs no capability yet. The path goes on at step 4, and the change check reads only the places the backbone configuration declares.

**Postconditions:** The project holds the system and the capabilities the adopter chose, committed for the team, and validation passes its backbone configuration. No pull request merges into the default branch through the hosting service's protection while a check of the required job fails on it.

**Minimal guarantees:**

- An install cut short reads as incomplete, and the next version transition finishes it (COR-059 point 6).
- Wherever the path stops, `pkit config set` has written no value that breaks the schema of the backbone configuration (COR-048 point 4).
- No name collision of a capability is settled silently. The adopter chooses for each one, and with nobody to answer nothing is copied (COR-017).
