---
id: UC-015
title: Package a recurring discipline as a capability
status: active
actor: ACT-component-author
other-actors:
  - ACT-ai-agent
after:
  - [UC-014]
requirements: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/scaffolds.py
        - src/project_kit/capabilities.py
        - src/project_kit/cli.py
        - .pkit/skills/core/capability-author.md
      record:
        - COR-017
        - COR-018
        - COR-007
        - COR-005
      artefact:
        - ACT-component-author
        - ACT-ai-agent
---

# UC-015 — Package a recurring discipline as a capability

**Goal:** Package a recurring discipline as a capability from the methodology's primitives, without forking the methodology.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): runs the stamp of step 1 for the author through the `capability-author` skill, which pairs with it (COR-005). It writes the capability's files as the author directs.

**Preconditions:**

- **From UC-014:** The project runs the system: it is the methodology's source repository, or the system is installed in it.

**Assumptions:** None.

**Trigger:** A discipline has recurred in the project's work, and suits only some projects. So the author decides to package it as a capability of its own (COR-007 and COR-017).

**Main path:**

1. The author runs `pkit new capability <name>`, or has an AI agent run it through the `capability-author` skill.
2. The system checks the name. It must be kebab-case, and neither a reserved word, such as `core` or `backbone`, nor a backbone command's name. No adapter may hold it, and no capability folder of the project may have it.
3. The system writes the capability's subtree, `.pkit/capabilities/<name>/`. It holds `package.yaml`, a `README.md`, and the empty folders `decisions/`, `skills/`, `agents/`, `scripts/`, `schemas/` and `migrations/` (COR-017).
4. The package metadata gives `version: 0.1.0`, and a range on the backbone from the version the project records, such as `requires_backbone: ">=1.149.0,<2.0.0"`.
5. The system prints `Stamped: .pkit/capabilities/<name>/`, and registers nothing.
6. The author writes the discipline into the subtree, from the methodology's primitives. Its decision records come from `pkit new decision <name> <slug>`, and its agent definitions from `pkit new agent <name> <agent>`. Its skills, its schemas and its scripts sit in their folders (COR-017 and COR-018).
7. The author writes the capability's description in `package.yaml` and in its README, and edits no file outside the subtree.

**Variants:**

- **2a.** The name is no kebab-case word, such as `My_Cap`. The system refuses with `capability name 'My_Cap' must be kebab-case (lowercase letters, digits, single hyphens).`, and writes nothing. The path rejoins at step 1.
- **2b.** The name is reserved, such as `backbone`. The system refuses with `capability name 'backbone' is reserved: <reason>. Choose another name.`, and writes nothing. The path rejoins at step 1.
- **2c.** The name is a backbone command's, such as `sync`, or an adapter holds it. The system refuses, saying which, and writes nothing. The path rejoins at step 1.
- **2d.** A capability of that name exists. The system refuses with `capability '<name>' already exists at .pkit/capabilities/<name>.`, and writes nothing. The path rejoins at step 1.

**Postconditions:** The project holds the capability's subtree, `.pkit/capabilities/<name>/`, beside the methodology's files, and none of those files is edited. Its package metadata gives its version and its range on the backbone. The capability is not registered yet, so none of its skills or agent definitions is deployed.

**Minimal guarantees:**

- A refused name leaves nothing written, since the system checks the name before it writes the subtree (`scaffolds.py`).
- A capability never takes a reserved name, a backbone command's name or a name an adapter holds (`capabilities.py` and `scaffolds.py`).
