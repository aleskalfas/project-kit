---
id: UC-027
title: Find my agent definition deployed, with the project's paths and my grants
status: active
actor: ACT-ai-agent
other-actors:
  - ACT-operator
  - ACT-adopter
after:
  - [UC-014, UC-049]
  - [UC-014, UC-019, UC-049]
  - [UC-022]
requirements:
  - REQ-002
  - REQ-005
  - REQ-009
  - REQ-010
  - REQ-012
  - REQ-013
  - REQ-016
shortfalls:
  - at: 2
    issue: "#1765"
    record: ADR-034#1
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/agents_overlay.py
        - src/project_kit/agent_policy.py
        - src/project_kit/install.py
        - src/project_kit/sync.py
        - src/project_kit/cli.py
        - .pkit/adapters/README.md
        - .pkit/agents/README.md
        - .pkit/lifecycle/ownership.py
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
        - ADR-034#1
      artefact:
        - ACT-ai-agent
        - ACT-operator
        - ACT-adopter
        - REQ-002
        - REQ-005
        - REQ-009
        - REQ-010
        - REQ-012
        - REQ-013
        - REQ-016
    revalidated:
      at: 2026-10-24T19:01:51Z
      outcome: unchanged
      unchanged-because: "As #2003 asks, the confirmations of release, reports, uninstall, visibility and collisions now refuse an answer piped in off a terminal. No step here asks one of them."
---

# UC-027 — Find my agent definition deployed, with the project's paths and my grants

**Goal:** Find my agent definition deployed, with the project's own paths filled in and my own permission grants applied.

**Other actors:**

- **Operator** (`ACT-operator`): runs `pkit sync`, which deploys the [agent definitions](../../../glossary.md#term-agent-definition--agent-definition) into the clone. The operator is asked before [sync](../../../glossary.md#term-sync--sync) writes in another repository than the session's own (REQ-012).
- **Adopter** (`ACT-adopter`): names the [project](../../../glossary.md#term-project--project)'s paths for each category in the [overlay](../../../glossary.md#term-overlay--overlay), and grants each agent its privileges (UC-022). The deploy never writes over an agent definition the adopter wrote under the same name.

**Preconditions:**

- **From UC-014 or UC-049:** The [project](../../../glossary.md#term-project--project) runs the [system](../../../glossary.md#term-system--system): it is the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository), or the system is installed in it.
- **From UC-014, UC-019 or UC-049:** An [adapter](../../../glossary.md#term-adapter--adapter) for the project's [harness](../../../glossary.md#term-harness--harness) deploys [skills](../../../glossary.md#term-skill--skill) and [agent definitions](../../../glossary.md#term-agent-definition--agent-definition) where that harness reads them.
- **From UC-022:** The [overlay](../../../glossary.md#term-overlay--overlay), `.pkit/agents/project/overlay.yaml`, holds the project's own paths for the categories it sets. The project's own grants lie beside the methodology's.

**Assumptions:**

- The [harness](../../../glossary.md#term-harness--harness) loads a deployed [agent definition](../../../glossary.md#term-agent-definition--agent-definition) when a session dispatches the agent. It limits the agent to the tools its `tools:` list names (ADR-004 [point](../../../glossary.md#term-point--point) 1). Claude Code, for one, reads `.claude/agents/<name>.md`.
- The harness names the dispatched agent in each tool call it hands the [permission hook](../../../glossary.md#term-permission-hook--permission-hook), as Claude Code's `agent_type` does (`decide.py`).
- The running agent finds the [project](../../../glossary.md#term-project--project)'s paths in its agent definition's front matter. The deploy fills no placeholder in the body, which keeps each `<category>` as written, and nothing shows that the agent reads the front matter (#1731).
- The agent changes only the paths its agent definition owns. Its `owns:` is metadata, not a permission, so nothing at run time holds the agent to it (ADR-051 point 6).

**Trigger:** The operator runs `pkit sync` in a clone, such as after pulling a [change](../../../glossary.md#term-change--change).

**Main path:**

1. The operator runs `pkit sync`.
2. At its entry, before it reads anything, [sync](../../../glossary.md#term-sync--sync) checks that the repository it would [change](../../../glossary.md#term-change--change) is the session's own. Where it is another, the [system](../../../glossary.md#term-system--system) asks the operator, and with nobody to ask it refuses (REQ-012).

> [!WARNING]
> **Not built yet:** `pkit sync` runs no such check, and writes in whatever repository holds its working directory. ADR-034 [point](../../../glossary.md#term-point--point) 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

3. The system checks that the running CLI is at the [version](../../../glossary.md#term-version--version) the [project](../../../glossary.md#term-project--project) records, and that no [version transition](../../../glossary.md#term-version-transition--version-transition) is incomplete (REQ-010).
4. The system runs each [adapter](../../../glossary.md#term-adapter--adapter)'s deploy primitives (`.pkit/adapters/README.md`). The fourth, `deploy-agents.sh`, deploys each [agent definition](../../../glossary.md#term-agent-definition--agent-definition) where its [harness](../../../glossary.md#term-harness--harness) reads it (COR-013 point 1).
5. Where several places ship an agent definition of one name, the adapter deploys the project's. Otherwise it deploys the one of the [capability](../../../glossary.md#term-capability--capability) whose name sorts first, and else the core's (COR-026 and `.pkit/agents/README.md`).
6. The adapter replaces each placeholder `<category>` in the agent definition's front matter with the paths the [overlay](../../../glossary.md#term-overlay--overlay) gives that category. A value under `overrides.<name>` replaces the top-level one for that agent definition, and is never merged with it (COR-013 point 5).
7. The adapter carries the agent definition's model and its effort into what it deploys, each from the overlay's override, or else from the front matter. It writes none whose value is `inherit` or absent (`agent_policy.py`).
8. The adapter writes the deployed agent definition with its own deploy mark, so a later run tells its own files from the adopter's (`.pkit/adapters/README.md`).
9. A session dispatches the agent for its [role](../../../glossary.md#term-role--role).
10. The harness loads the deployed agent definition. The agent finds the project's own paths in its front matter, and only the tools its `tools:` list names (ADR-004 point 1).
11. Where the adapter's [permission hook](../../../glossary.md#term-permission-hook--permission-hook) is registered, it hands each of the agent's tool calls to the [backbone](../../../glossary.md#term-backbone--backbone)'s permission code, for the subject `agent:<name>`. That code needs only the system `python3` (REQ-016). It applies the grants to `all` and the agent's own, and a deny wins over an allow (REQ-013).

**Variants:**

- **1a.** The adopter first runs `pkit agents`, which writes nothing (REQ-005). It lists each [agent definition](../../../glossary.md#term-agent-definition--agent-definition) as `deployable` or `SKIPPED`, with the categories the [overlay](../../../glossary.md#term-overlay--overlay) leaves unset and the effective model and effort.
- **1b.** The operator passes `--dry-run`. The [system](../../../glossary.md#term-system--system) names each script it would run with `would run`, runs none of them, and deploys nothing (REQ-009). The use case ends.
- **3a.** The [project](../../../glossary.md#term-project--project) is not the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository). The running CLI is at another [version](../../../glossary.md#term-version--version) than the project records, or a [version transition](../../../glossary.md#term-version-transition--version-transition) is incomplete. [Sync](../../../glossary.md#term-sync--sync) stops before it writes, names the remedy, and the use case ends (REQ-010).
- **6a.** The overlay leaves unset a category that the agent definition names under `owns`, `needs`, `answers`, `reads.paths` or `reads.records`. The [adapter](../../../glossary.md#term-adapter--adapter) skips that agent definition and deploys the rest (ADR-052). It names the remedy, `pkit agents adopt <name>`, or `pkit agents reconcile --write` for a category that carries writes. A copy deployed earlier stays as it was, and the use case ends for that agent definition.
- **6b.** The overlay leaves unset a category that the agent definition reads only through `reads.patterns`. The adapter drops that item, and deploys the agent definition without it (ADR-052).
- **6c.** A category that carries writes names a path that sync manages. The adapter skips the agent definition, saying that the category names sync-managed paths, so no agent owns a path that sync writes over (`.pkit/lifecycle/ownership.py`).
- **7a.** The model or the effort is a value the [harness](../../../glossary.md#term-harness--harness) does not accept. The adapter carries no value for it, so the agent takes the harness's default, and the system reports a `warning` line naming the value (`agent_policy.py`).
- **8a.** A file without the deploy mark stands where the adapter would deploy, such as an agent definition the adopter wrote there. The adapter leaves the file untouched, and reports it `skipped`.
- **8b.** A deployed agent definition carries the deploy mark, and no [place](../../../glossary.md#term-place--place) ships its agent definition any more. The adapter removes it, and reports it `removed`.
- **11a.** The [permission hook](../../../glossary.md#term-permission-hook--permission-hook) is not registered. Only the `tools:` list and the harness's own settings apply. Those settings are one set for the whole session, never one for each agent (ADR-004 [point](../../../glossary.md#term-point--point) 1).
- **11b.** The harness names no agent in the call, as for the main session. The permission code takes the default agent from the `agent` key of Claude Code's `.claude/settings.json`, the one harness's settings it reads. With none, the subject is `operator` (`decide.py`).
- **11c.** An installed [capability](../../../glossary.md#term-capability--capability) contributes a deny [grant](../../../glossary.md#term-grant--grant) for the agent in a grants file of its own. The deny holds for that agent, whatever its other grants allow (ADR-016 and REQ-013).

**Postconditions:** The [agent definition](../../../glossary.md#term-agent-definition--agent-definition) is deployed where the [harness](../../../glossary.md#term-harness--harness) reads it, with the [project](../../../glossary.md#term-project--project)'s paths in [place](../../../glossary.md#term-place--place) of the placeholders of its front matter. Where the [permission hook](../../../glossary.md#term-permission-hook--permission-hook) is registered, each of the agent's tool calls is decided under its own grants and those to `all`.

**Minimal guarantees:**

- An [adapter](../../../glossary.md#term-adapter--adapter) never writes over a file without its deploy mark, as an [agent definition](../../../glossary.md#term-agent-definition--agent-definition) the adopter wrote (`.pkit/adapters/README.md`).
- A placeholder resolves only from a value the [overlay](../../../glossary.md#term-overlay--overlay) holds. So an agent definition whose required category is unset is skipped, never deployed with the placeholder in it (COR-013 [point](../../../glossary.md#term-point--point) 5 and ADR-052).
- One skipped agent definition never stops the others deploying (ADR-052).
- A deny granted to an agent wins over any allow it holds (COR-028 point 1 and `decide.py`).
