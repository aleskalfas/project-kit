---
id: UC-020
title: Turn recurring work into my project's own skill or agent definition
status: active
actor: ACT-developer
other-actors:
  - ACT-ai-agent
after:
  - [UC-014, UC-049]
  - [UC-014, UC-019, UC-049]
requirements:
  - REQ-002
  - REQ-009
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/agents.py
        - src/project_kit/storyboards.py
        - src/project_kit/refs.py
        - src/project_kit/cli.py
        - src/project_kit/install.py
        - src/project_kit/agents_overlay.py
        - .pkit/adapters/README.md
        - .pkit/skills/README.md
      record:
        - COR-001
        - COR-005
        - COR-006
        - COR-007
        - COR-013
        - COR-015
        - COR-016
        - ADR-052
      artefact:
        - ACT-developer
        - ACT-ai-agent
        - REQ-002
        - REQ-009
    revalidated:
      at: 2026-10-24T21:20:22Z
      outcome: unchanged
      unchanged-because: ACT-ai-agent keeps its words and drops only its links on role, and ACT-developer names the developer. Their needs are the same, so this use case holds.
---

# UC-020 — Turn recurring work into my project's own skill or agent definition

**Goal:** Turn recurring work into my project's own skill or agent definition, designing its dialogue as a storyboard first.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): runs the [stamp](../../../glossary.md#term-stamp--stamp) of step 2 for the developer through the `agent-author` [skill](../../../glossary.md#term-skill--skill), and drafts the [storyboard](../../../glossary.md#term-storyboard--storyboard) through the `storyboard-author` skill. Later, its sessions load the new skill, or delegate to the new [agent definition](../../../glossary.md#term-agent-definition--agent-definition).

**Preconditions:**

- **From UC-014 or UC-049:** The [project](../../../glossary.md#term-project--project) runs the [system](../../../glossary.md#term-system--system): it is the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository), or the system is installed in it.
- **From UC-014, UC-019 or UC-049:** An [adapter](../../../glossary.md#term-adapter--adapter) for the project's [harness](../../../glossary.md#term-harness--harness) deploys [skills](../../../glossary.md#term-skill--skill) and [agent definitions](../../../glossary.md#term-agent-definition--agent-definition) where that harness reads them.

**Assumptions:** None.

**Trigger:** The same work has come up two or three times, and the developer decides to give it tooling of its own (COR-007).

**Main path:**

1. The developer chooses what carries the work. A procedure for one kind of task becomes a [skill](../../../glossary.md#term-skill--skill), and a standing remit with boundaries becomes an [agent definition](../../../glossary.md#term-agent-definition--agent-definition) (COR-006). Here it is an agent definition, whose dialogue with a person follows a script.
2. The developer runs `pkit new agent project <name> --with-storyboard`, or has an AI agent run it through the `agent-author` skill.
3. The [system](../../../glossary.md#term-system--system) checks the name, and that no agent definition of the [project](../../../glossary.md#term-project--project), of a [capability](../../../glossary.md#term-capability--capability) or of the core has it.
4. The system writes the agent definition, `.pkit/agents/project/<name>/<name>.md`, and its [storyboard](../../../glossary.md#term-storyboard--storyboard), `storyboard.md`, beside it. The agent definition lists the storyboard in `storyboards:`, and the storyboard names the agent definition in `consumers:` (COR-016).
5. The system prints `Stamped: .pkit/agents/project/<name>/<name>.md` and `Stamped: .pkit/agents/project/<name>/storyboard.md`.
6. The developer writes the storyboard first, through the `storyboard-author` skill (COR-016). It gives the framing and the tone, and for each scenario:
   - its trigger
   - its preconditions
   - a walkthrough
   - what happens behind the scenes
7. The developer writes the agent definition's body from the storyboard (COR-013). The body says:
   - when to delegate work to the agent definition
   - what it reads
   - which paths it owns
8. The developer runs `pkit sync`.
9. Each [adapter](../../../glossary.md#term-adapter--adapter)'s `deploy-agents.sh` deploys the agent definition where its [harness](../../../glossary.md#term-harness--harness) reads it, with each placeholder filled from `.pkit/agents/project/overlay.yaml` (COR-013 [point](../../../glossary.md#term-point--point) 5). The `claude-code` adapter, for one, writes `.claude/agents/<name>.md`.
10. The developer runs `pkit validate`. Its `refs` member checks that the agent definition's body cites what its front matter declares (COR-013 point 3). It also checks that the agent definition and its storyboard declare each other (COR-016).

**Variants:**

- **1a.** A [skill](../../../glossary.md#term-skill--skill) carries the work. No [stamp](../../../glossary.md#term-stamp--stamp) writes one: the developer writes `.pkit/skills/project/<name>.md`, with the front matter `name` and `description` and the procedure (`.pkit/skills/README.md`). At step 9, each [adapter](../../../glossary.md#term-adapter--adapter)'s `deploy-skills.sh` deploys it where its [harness](../../../glossary.md#term-harness--harness) reads skills, such as `.claude/skills/<name>/SKILL.md` for the `claude-code` adapter. The path goes on at step 10.
- **1b.** The [agent definition](../../../glossary.md#term-agent-definition--agent-definition)'s work rests on judgement, with no scripted dialogue. The developer runs `pkit new agent project <name>`, and the [system](../../../glossary.md#term-system--system) writes `.pkit/agents/project/<name>.md` alone, with no [storyboard](../../../glossary.md#term-storyboard--storyboard) (COR-016). The path goes on at step 7.
- **3a.** The name is no kebab-case word. The system refuses with ``agent name must be kebab-case …``, and writes nothing. The path rejoins at step 2.
- **3b.** An agent definition of that name exists. The system refuses with `agent '<name>' already exists at <path>.`, and writes nothing. The path rejoins at step 2.
- **6a.** The developer adds the storyboard later, with `pkit new storyboard agent <name>`. The system writes it beside the agent definition, but adds nothing to the agent definition's `storyboards:`. So at step 10 `pkit validate` fails until the developer lists it there, since `Mutual declaration is required (per COR-016).`
- **9a.** The agent definition names a placeholder that `.pkit/agents/project/overlay.yaml` leaves unset. The adapter skips it and deploys the rest, and the system names `pkit agents adopt <agent>` to deploy it (ADR-052).

**Postconditions:** The [project](../../../glossary.md#term-project--project)'s own [skill](../../../glossary.md#term-skill--skill) or [agent definition](../../../glossary.md#term-agent-definition--agent-definition) lies in the project's own folder, `.pkit/skills/project/` or `.pkit/agents/project/`. An agent definition whose dialogue follows a script has its [storyboard](../../../glossary.md#term-storyboard--storyboard) beside it. The skill or agent definition is deployed where the [harness](../../../glossary.md#term-harness--harness) reads it, and no [sync](../../../glossary.md#term-sync--sync) writes over it.

**Minimal guarantees:**

- A refused name leaves nothing written (`agents.py`).
- [Sync](../../../glossary.md#term-sync--sync) writes the [methodology](../../../glossary.md#term-methodology--methodology)'s [skills](../../../glossary.md#term-skill--skill) and [agent definitions](../../../glossary.md#term-agent-definition--agent-definition) only into their `core/` folders, never over the [project](../../../glossary.md#term-project--project)'s own (COR-001 and `install.py`).
- An [adapter](../../../glossary.md#term-adapter--adapter)'s scripts drop only what they deployed themselves, recognised by the adapter's own deploy mark, and never the project's own content (`.pkit/adapters/README.md`).
