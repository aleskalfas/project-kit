---
id: UC-012
title: Start every session with the project's rules loaded
status: active
actor: ACT-ai-agent
other-actors:
  - ACT-operator
  - ACT-adopter
pkit:
  friction:
    anchors:
      path:
        - .pkit/adapters/claude-code/merge-claude-md.sh
        - src/project_kit/install.py
        - src/project_kit/sync.py
      record:
        - COR-001
        - COR-002
        - COR-014
      artefact:
        - ACT-ai-agent
        - ACT-operator
        - ACT-adopter
---

# UC-012 — Start every session with the project's rules loaded

**Goal:** Start every session with the project's rules and conventions loaded.

**Other actors:**

- **Operator** (`ACT-operator`): runs `pkit sync` in the clone, which wires the rules into the root `CLAUDE.md`. The wiring never removes what `CLAUDE.md` already holds (COR-002).
- **Adopter** (`ACT-adopter`): writes the project's own rules in `.pkit/rules/project.md`, which sync never overwrites (COR-001).

**Preconditions:** The claude-code adapter is installed in the project.

**Assumptions:**

- The harness reads the root `CLAUDE.md` when a session starts, and follows each `@` include in it. `CLAUDE.md` relies on that include mechanism for the rules it delegates to (COR-001). Nothing in the system checks that the harness loads them.

**Trigger:** The operator runs `pkit sync` in a clone, such as after cloning the project or pulling a change.

**Main path:**

1. The operator runs `pkit sync`.
2. The system refreshes `.pkit/rules/core.md`, which the methodology owns. It leaves `.pkit/rules/project.md`, which the project owns, as it is (COR-001 and COR-014).
3. The system runs the adapter's `merge-claude-md.sh`. The script finds that the root `CLAUDE.md` includes `@.pkit/rules/core.md`, and reports `exists`.
4. A session starts in the project.
5. The harness loads `CLAUDE.md`, and with it the core rules and the project's rules that its `@` includes name (COR-001).
6. The agent starts its work with both sets of rules in its context, inside the project's own instructions. The core rules carry the conventions of tool hygiene that every agent follows.

**Variants:**

- **1a.** The adopter installs the system with `pkit init`, which runs the same script. The path goes on at step 3.
- **2a.** In project-kit, `.pkit/rules/core.md` is the methodology's own source, so sync copies nothing over it. The path goes on at step 3.
- **3a.** The project has no root `CLAUDE.md`. The script creates one with a heading and both includes, and reports `created`. The path goes on at step 4.
- **3b.** `CLAUDE.md` does not include `.pkit/rules/core.md`. The script inserts both includes after the first level-one heading of `CLAUDE.md`, and reports `insert`. Where `CLAUDE.md` has no such heading, the script puts a heading and the includes above the existing text, and reports `prepend`. The path goes on at step 4.
- **3c.** `CLAUDE.md` includes `.pkit/rules/core.md`, and not `.pkit/rules/project.md`. The script changes nothing. So a session starts without the project's own rules, until someone adds that include.
- **3d.** `CLAUDE.md` names `@.pkit/rules/core.md` in its text but does not include it, such as in a sentence about it. The script reads the name as the include, and changes nothing.

**Postconditions:** Each session the harness starts in the project begins with the core rules, their conventions included, and the project's own rules in its context.

**Minimal guarantees:**

- The script never removes or rewrites what `CLAUDE.md` already holds. It adds only the includes, with a heading where `CLAUDE.md` has none (COR-002 and `merge-claude-md.sh`).
- Sync never overwrites `.pkit/rules/project.md` (COR-001 and `install.py`).
- A second run changes nothing, and reports `exists` (COR-002).
