---
id: UC-013
title: Find my role deployed, with the project's paths and my grants
status: active
actor: ACT-ai-agent
other-actors:
  - ACT-operator
  - ACT-adopter
pkit:
  friction:
    anchors:
      path:
        - .pkit/adapters/claude-code/deploy-agents.sh
        - .pkit/adapters/claude-code/_resolve_agent.py
        - src/project_kit/agents_overlay.py
        - src/project_kit/agent_policy.py
        - .pkit/permissions/decide.py
      record:
        - COR-013#1
        - COR-013#5
        - COR-026
        - COR-028#1
        - ADR-004#1
        - ADR-016
        - ADR-051#6
        - ADR-052
      artefact:
        - ACT-ai-agent
        - ACT-operator
        - ACT-adopter
---

# UC-013 — Find my role deployed, with the project's paths and my grants

**Goal:** Find my role definition deployed, with the project's own paths filled in and my own permission grants applied.

**Other actors:**

- **Operator** (`ACT-operator`): runs `pkit sync`, which deploys the agents into the clone.
- **Adopter** (`ACT-adopter`): names the project's paths for each category in `.pkit/agents/project/overlay.yaml`, and grants each agent its privileges. The deploy never overwrites an agent's definition the adopter wrote under the same name.

**Preconditions:** The claude-code adapter is installed in the project.

**Assumptions:**

- The harness loads an agent's definition from `.claude/agents/<name>.md` when a session dispatches the agent. The harness limits the agent to the tools its `tools:` list names (ADR-004 point 1).
- The harness names the dispatched agent as `agent_type` in each tool call it hands the permission hook (`decide.py`).
- The running agent finds the project's paths in its definition's front matter. The deploy fills no placeholder in the body, which keeps each `<category>` as written (`_resolve_agent.py`).
- The agent changes only the paths its role owns. Its `owns:` is metadata, not a permission, so nothing at run time holds the agent to it (ADR-051 point 6).

**Trigger:** The operator runs `pkit sync` in a clone, such as after cloning the project or pulling a change.

**Main path:**

1. The operator runs `pkit sync`.
2. The system runs the adapter's `deploy-agents.sh`. Where several places ship an agent of one name, the script takes the project's, then the capability's whose name sorts first, then the core's (COR-026).
3. The system replaces each `<category>` placeholder in the front matter of the agent's source with the paths the overlay gives that category. A value under `overrides.<name>` wins over the top-level one (COR-013 point 5).
4. The system carries the agent's model and its effort into the definition, each from the overlay's override, or else from the agent's front matter. It writes no key whose value is `inherit` or absent.
5. The system writes the resolved definition to `.claude/agents/<name>.md` with its marker, and reports `created`, `updated` or `exists`.
6. A session dispatches the agent for its role.
7. The harness loads the definition. The agent finds the project's own paths in the definition's front matter, and only the tools its `tools:` list names.
8. With the permission hook registered, the system decides each of the agent's tool calls for `agent:<name>`. It applies the grants to `all` and the agent's own grants, and a deny wins over an allow (COR-028 point 1).

**Variants:**

- **1a.** The adopter checks the deploy first with `pkit agents`. The command lists each agent as deployable or `SKIPPED`, with the categories the agent misses and its effective model and effort.
- **3a.** The overlay does not define a category the agent names in `owns`, `needs`, `answers`, `reads.paths` or `reads.records`. The system skips that agent, and gives the reason and the remedy, such as `pkit agents adopt <agent>`. It deploys the rest, and the use case ends for that agent.
- **3b.** The overlay does not define a category the agent reads only through `reads.patterns`. The system drops that item, and deploys the agent without it (ADR-052).
- **4a.** The model or the effort is a value the harness does not accept. The system writes no key for that value, so the agent takes the harness's default for it. It reports a `warning` line naming the value.
- **5a.** `.claude/agents/<name>.md` exists without the marker, as a definition the adopter wrote. The system leaves the file untouched, and reports `skipped`.
- **5b.** A deployed definition carries the marker, and no source ships its agent any more. The system removes the definition, and reports `removed`.
- **8a.** The permission hook is not registered. Only the `tools:` list and the settings' rules apply. Those rules are one set for the whole session, never one per agent (ADR-004 point 1).
- **8b.** The main session runs as a default agent, which `agent` names in `.claude/settings.json`. The hook decides the main session's calls for that agent too.
- **8c.** An installed capability contributes a deny for the agent, such as project-management's deny of raw `gh` mutations for `project-manager`. The deny holds for that agent, whatever its other grants allow (ADR-016).

**Postconditions:** The agent's definition is deployed in `.claude/agents/`, with the project's paths in place of the placeholders of its front matter. With the permission hook registered, each of the agent's tool calls is decided under its own grants.

**Minimal guarantees:**

- The deploy never overwrites a definition the adopter wrote, which it tells by the missing marker (`deploy-agents.sh`).
- An agent whose required category is missing is skipped by name, never deployed with a placeholder left in its front matter (`deploy-agents.sh`).
- One skipped agent never stops the others deploying (`deploy-agents.sh`).
- A deny granted to an agent wins over any allow it holds (COR-028 point 1).
