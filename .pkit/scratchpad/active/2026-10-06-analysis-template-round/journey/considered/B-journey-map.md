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

**Scenario and expectations:** the adopter brings the methodology to an existing project in a git repository, on its first day. They expect one command to install it, a report of how it is wired, and checks the project's merges can wait on. They expect their own files to be left alone (`ACT-adopter`).

## Install

- **Doing:**
  1. UC-xx1 — The adopter runs `pkit init`, confirms the install target, and reads the closing next steps.
  2. UC-xx2 — The adopter runs `pkit status`, and reads the install, its version, the harness and the capabilities available.
- **Touchpoints:** `pkit init` and its confirmation, its closing next steps, `.claude/settings.json` with its `.pre-pkit` backup, and `pkit status`.
- **Thinking:** one command should set the project up, committed for the team or kept out of the shared repository (`ACT-adopter`).
- **Feeling:** wary, since the install writes into the project's harness settings. Reassured by the backup and by the status report.
- **Pain points:**
  - The closing next steps recommend symlinking a source checkout's `pkit`. The CLI reference recommends `uv tool install` (PRJ-004).
  - Status never shows that an install is private. Only `pkit visibility` reports the mode (ADR-009 and `status.py`).

## Add a discipline

- **Doing:**
  3. UC-xx3 — The adopter picks a capability from those available, reads `pkit capabilities install <name> --plan`, and installs it.
  4. UC-xx2 — The adopter runs `pkit status` again, and reads the capability's roles and points.
- **Touchpoints:** status's list of capabilities, `pkit capabilities show <name>`, the install's plan and its provisioning lines, and status's suggestions and *Connections*.
- **Thinking:** adding a capability should overwrite nothing of theirs, and should say first what it will connect to (`ACT-adopter`).
- **Feeling:** in control while the plan shows the change. Uneasy at a refusal or a warning they did not expect.
- **Pain points:**
  - Status lists what is available, not what each capability requires. One that requires another, not yet installed, is refused at install (COR-030).
  - Installed offline, the capability's query commands give no answer until `pkit sync` runs online (`provisioning.py`).
  - Status may then suggest another capability, one that would provide a role the new one targets (COR-053 point 8). The phase starts again.

## Gate the merges

- **Doing:**
  5. UC-xx4 — The adopter declares the settings in `.pkit/project/config.yaml`, and runs `pkit validate`.
  6. UC-xx5 — The adopter adds a pipeline job that runs `pkit sync`, `pkit validate` and `pkit friction check`, and makes it a required status.
- **Touchpoints:** `.pkit/project/config.yaml`, `pkit config set`, `pkit validate`, the pipeline's configuration and the hosting service's required statuses.
- **Thinking:** the settings should be declared once and validated, and the checks bind only once the pipeline requires them (`ACT-adopter`).
- **Feeling:** done, once the first pull request waits on the checks. Puzzled where the pipeline fails on what passed in their clone.
- **Pain points:**
  - Status never shows the default branch, so a project that merges into another branch than `main` may leave it undeclared (COR-054 point 1).
  - Later pull requests carry the install and the settings only once the developer's landing puts them on the default branch. The landing is no phase of this journey.
  - A private install, a missing pin or a skipped `pkit sync` fails the pipeline where the adopter's clone passed (ADR-009, ADR-049 and `provisioning.py`).
  - The change check passes in `warning` mode (COR-050 point 12). It stays dormant until something in a declared place carries the methodology's container (COR-050 point 15).

**Opportunities:**

- `pkit status` shows the install's visibility, its pin and the default branch.
- `init`'s closing next steps recommend `uv tool install`, as the CLI reference does, and `pkit pin`.
- The CLI reference gives one pipeline job that a project copies, with `pkit sync` first and the base named for the checks.
