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
      at: 2026-10-24T04:34:26Z
      outcome: unchanged
      unchanged-because: The agent and storyboard stamps now refuse a core or capability folder the project receives as synced copies. The use case stamps in the project namespace, which they never refuse, so its steps hold.
---

# UC-020 — Turn recurring work into my project's own skill or agent definition

**Goal:** Turn recurring work into my project's own skill or agent definition, designing its dialogue as a storyboard first.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): runs the stamp of step 2 for the developer through the `agent-author` skill, and drafts the storyboard through the `storyboard-author` skill. Later, its sessions load the new skill, or delegate to the new agent definition.

**Preconditions:**

- **From UC-014 or UC-049:** The project runs the system: it is the methodology's source repository, or the system is installed in it.
- **From UC-014, UC-019 or UC-049:** An adapter for the project's harness deploys skills and agent definitions where that harness reads them.

**Assumptions:** None.

**Trigger:** The same work has come up two or three times, and the developer decides to give it tooling of its own (COR-007).

**Main path:**

1. The developer chooses what carries the work. A procedure for one kind of task becomes a skill, and a standing remit with boundaries becomes an agent definition (COR-006). Here it is an agent definition, whose dialogue with a person follows a script.
2. The developer runs `pkit new agent project <name> --with-storyboard`, or has an AI agent run it through the `agent-author` skill.
3. The system checks the name, and that no agent definition of the project, of a capability or of the core has it.
4. The system writes the agent definition, `.pkit/agents/project/<name>/<name>.md`, and its storyboard, `storyboard.md`, beside it. The agent definition lists the storyboard in `storyboards:`, and the storyboard names the agent definition in `consumers:` (COR-016).
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
9. Each adapter's `deploy-agents.sh` deploys the agent definition where its harness reads it, with each placeholder filled from `.pkit/agents/project/overlay.yaml` (COR-013 point 5). The `claude-code` adapter, for one, writes `.claude/agents/<name>.md`.
10. The developer runs `pkit validate`. Its `refs` member checks that the agent definition's body cites what its front matter declares (COR-013 point 3). It also checks that the agent definition and its storyboard declare each other (COR-016).

**Variants:**

- **1a.** A skill carries the work. No stamp writes one: the developer writes `.pkit/skills/project/<name>.md`, with the front matter `name` and `description` and the procedure (`.pkit/skills/README.md`). At step 9, each adapter's `deploy-skills.sh` deploys it where its harness reads skills, such as `.claude/skills/<name>/SKILL.md` for the `claude-code` adapter. The path goes on at step 10.
- **1b.** The agent definition's work rests on judgement, with no scripted dialogue. The developer runs `pkit new agent project <name>`, and the system writes `.pkit/agents/project/<name>.md` alone, with no storyboard (COR-016). The path goes on at step 7.
- **3a.** The name is no kebab-case word. The system refuses with ``agent name must be kebab-case …``, and writes nothing. The path rejoins at step 2.
- **3b.** An agent definition of that name exists. The system refuses with `agent '<name>' already exists at <path>.`, and writes nothing. The path rejoins at step 2.
- **6a.** The developer adds the storyboard later, with `pkit new storyboard agent <name>`. The system writes it beside the agent definition, but adds nothing to the agent definition's `storyboards:`. So at step 10 `pkit validate` fails until the developer lists it there, since `Mutual declaration is required (per COR-016).`
- **9a.** The agent definition names a placeholder that `.pkit/agents/project/overlay.yaml` leaves unset. The adapter skips it and deploys the rest, and the system names `pkit agents adopt <agent>` to deploy it (ADR-052).

**Postconditions:** The project's own skill or agent definition lies in the project's own folder, `.pkit/skills/project/` or `.pkit/agents/project/`. An agent definition whose dialogue follows a script has its storyboard beside it. The skill or agent definition is deployed where the harness reads it, and no sync writes over it.

**Minimal guarantees:**

- A refused name leaves nothing written (`agents.py`).
- Sync writes the methodology's skills and agent definitions only into their `core/` folders, never over the project's own (COR-001 and `install.py`).
- An adapter's scripts drop only what they deployed themselves, recognised by the adapter's own deploy mark, and never the project's own content (`.pkit/adapters/README.md`).
