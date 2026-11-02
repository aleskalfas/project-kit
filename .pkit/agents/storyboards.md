---
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/storyboards.py
        - src/project_kit/refs.py
        - .pkit/adapters/claude-code/_resolve_agent.py
      record:
        - COR-015
        - COR-016
---

# Storyboards

A storyboard designs the dialogue of an agent's scripted scenario before the agent's body is written ([COR-016](../decisions/core/COR-016-scripted-scenario-storyboards.md)). It sits beside the agent's definition, which declares it and reads it at the start of each session.

## Contents

<!-- pkit:contents -->
- [When a definition takes one](#when-a-definition-takes-one)
- [Structure](#structure)
- [Location and lifecycle](#location-and-lifecycle)
- [Front matter](#front-matter)
- [Authoring](#authoring)
<!-- /pkit:contents -->

## When a definition takes one

A definition takes a storyboard where its author finds themselves writing scripted dialogue in the agent's body (COR-016). A scripted scenario is a sequence of turns whose prompts, gates and writes are designed in advance.

- **It fits** a review agent walking a person through accepting a methodology record, an onboarding flow, or a coordinator confirming the scope before it delegates.
- **It does not fit** work from judgement, such as a code reviewer answering any diff, a research assistant, or an expert improvising findings. A script would make these worse.
- **Mixed:** one agent may do both. Storyboard the scripted scenario, such as a security review of a sensitive pull request, and leave the rest to judgement.
- **Recommended, never enforced:** no command refuses a definition without a storyboard.

## Structure

A storyboard has three layers (COR-016):

1. **Framing:** the scenarios the storyboard covers, the state they work on, and how a user enters them.
2. **Tone rules:** the norms every scenario follows, such as the cadence, the length of a turn and how to confirm.
3. **Scenarios,** each with its *Trigger*, *Preconditions*, *Walkthrough* of example dialogue, and *Behind the scenes*: the writes and side effects. An edge case is a scenario of its own.

One `storyboard.md` may hold several scenarios that share their framing and tone. Scenarios that diverge go in files of their own beside the agent, each named `<scenario-slug>.storyboard.md`.

## Location and lifecycle

A storyboard is a helper beside its agent's definition, so the definition takes the folder form (COR-015):

```
.pkit/agents/<namespace>/<agent>/            # or .pkit/capabilities/<capability>/agents/<agent>/
├── <agent>.md                         # the definition: declares its storyboards, reads them at session start
├── storyboard.md                      # one storyboard, of one or more scenarios
└── <scenario-slug>.storyboard.md      # one scenario's own, where scenarios diverge
```

- **Source only.** The deploy copies no storyboard. The agent reads it at its source path with its `Read` tool. That path resolves, since the session runs at the project's root and `.pkit/` is committed with the project.
- **The body's reference carries weight.** The definition declares the storyboard, and its body tells the agent to read and follow it.
- **One source of truth.** No deployed copy exists to drift from the storyboard.

<a id="frontmatter-declaration"></a>
## Front matter

The agent and the storyboard each declare the other (COR-016). The agent's side:

```markdown
---
name: review-agent
description: ...
tools: [Read, Edit]           # Read is required where storyboards are declared
storyboards:
  - storyboard.md
---

Load your storyboard from `storyboard.md` with the Read tool at session start and follow it.
```

- **`storyboards:`** lists each storyboard by its bare file name beside the definition, `storyboard.md` or `<scenario-slug>.storyboard.md`. It resolves against the agent's own folder, so it stays right wherever the folder lives, and when the folder moves. A path from the project's root is accepted too.
- **The body** cites each entry as the entry is written.
- **`tools:`** includes `Read`, so the agent can read the storyboard.
- **The deployed copy** lives elsewhere, such as `.claude/agents/<name>.md`, where a bare name resolves to nothing. So the deploy rewrites each such entry to the storyboard's path from the project's root, in `storyboards:` and in the body. An example is `.pkit/agents/project/review-agent/storyboard.md`. An entry already written from the root deploys as written.

The storyboard's side:

```yaml
---
consumers:
  - kind: agent
    name: review-agent
    namespace: project
---

# Storyboard: ...
```

- **`consumers:`** is a non-empty list, each entry one artefact that drives the storyboard's scenarios. Today each is an agent, `kind: agent`, with its `name` and its `namespace`: `core`, `project`, or a capability's name.
- **A list, not one value,** so a storyboard that two consumers share needs no new shape. Today each storyboard has one consumer.

What the reference graph's check, `refs validate`, checks, failing on each finding:

- **The agent's side:** each storyboard it declares exists, its body cites each one, and its `tools:` hold `Read`.
- **The storyboard's side:** its `consumers:` is a non-empty list, and each consumer exists and declares the storyboard back.
- **An orphan:** a storyboard in an agent's folder that no agent declares.
- **Where it looks:** in every agent folder, this area's and each capability's. It compares an entry with a file by the file the entry resolves to, so both forms of an entry name one storyboard.

## Authoring

Stamp a storyboard for an agent that exists:

```
pkit new storyboard agent <agent-name>                     # one storyboard for the agent
pkit new storyboard agent <agent-name> --scenario <slug>   # one scenario's own file
pkit new storyboard agent <agent-name> --namespace <ns>    # where the agent lives
```

- **Which agent.** The command finds the agent in the deploy's order: the project, the capabilities by name, then core. So it stamps beside the agent that deploys. `--namespace`, `core`, `project` or a capability's name, looks in that one place instead.
- **An unknown capability** gets the refusal a new agent's stamp gives.
- **A synced copy is refused.** The command stamps nothing beside an agent the project receives by sync, and says where such an agent is authored.
- **A flat definition** moves into a folder of its own, named after it, first.
- **Not listed for you.** The command fills the storyboard's `consumers:`, but adds nothing to the agent's `storyboards:`. List the entry there, and cite it in the body, or `refs validate` fails.
- **The skill.** The paired `storyboard-author` skill walks the author through the framing, the tone and each scenario.
- **Both at once.** For an agent that drives a scripted scenario from the start, a new agent's stamp with `--with-storyboard` writes both. The storyboard sits beside the definition, and each declares the other.
