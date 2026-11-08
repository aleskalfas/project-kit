---
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/refs.py
        - src/project_kit/cli.py
        - src/project_kit/install.py
        - src/project_kit/sync.py
      record:
        - COR-013#4
      artefact:
        - .pkit/adapters/claude-code/README.md#deploy-skillssh
---

# Hooks

A hook is a named operation an agent invokes, which a skill, a command or a script provides ([COR-013](../decisions/core/COR-013-agent-architecture.md) point 4). The agent names the hook, never its provider, so the provider can change while the agent stays as it is.

## Contents

<!-- pkit:contents -->
- [Declaration](#declaration)
- [Provider value syntax](#provider-value-syntax)
- [Hook signature](#hook-signature)
- [Naming](#naming)
- [Provider precedence](#provider-precedence)
- [Unsatisfied needs](#unsatisfied-needs)
- [Invoking a hook](#invoking-a-hook)
- [Commands](#commands)
<!-- /pkit:contents -->

## Declaration

Three kinds of file declare a hook:

- **The consumer,** an agent, lists it under `needs:` in its front matter.
- **A skill that provides it** lists it under `answers:` in its front matter.
- **A capability or an adapter that provides it** maps it to an implementation under `provides:` in its `package.yaml`.

## Provider value syntax

The implementation in a `provides:` entry is read by its prefix:

- **`/<skill-name>`** invokes that skill, through the harness's skill mechanism.
- **Anything else** runs as a shell command.

```yaml
# a capability's package.yaml
provides:
  tracker.create-issue: /tracker-create-issue   # a skill
  tracker.move-issue:   scripts/move-issue.py   # a shell script
```

A skill's `answers:` entry is provided by the skill itself.

## Hook signature

A hook takes positional string arguments, and writes text to standard output. Its exit code signals success (0) or failure. Each hook's own contract, its arguments and the form of its output, is in its provider's body or README.

## Naming

A hook's name says whether any provider of its topic may answer it, or one provider alone:

- **`<topic>.<operation>`,** two segments, names a contract hook, which several providers of one topic are expected to implement. The topic is usually a capability's name. An agent that needs only such hooks stays portable across capability variants.
- **`<topic>.<provider>.<operation>`,** three segments, names an extension that one provider implements. An agent that needs one is tied to that provider, and the name says so.
- **The form:** lowercase kebab-case segments joined by dots, matching `^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*){1,2}$`.
- **The project's own hooks** use the reserved `project.*` topic.

## Provider precedence

One provider binds each hook, taken by tier in this order:

```
project > capability > adapter > core
```

The order mirrors the skill-deploy precedence, where the project's skill wins over core's ([the Claude Code adapter's README, `deploy-skills.sh`](../adapters/claude-code/README.md#deploy-skillssh)).

- **The tiers:** a skill in `.pkit/skills/project/` is of the `project` tier. A capability's `provides:` is of the `capability` tier, and an adapter's is of the `adapter` tier. Every other skill is of the `core` tier, a skill a capability ships among them.
- **Two providers at one tier:** where the highest tier that holds a provider of a hook holds two, neither binds. COR-013 point 4 decides that the collision is refused, never settled by picking one:
  - `pkit validate` and `pkit refs validate` fail the collision, naming both providers.
  - `pkit hooks resolve` refuses the hook, naming both, and `pkit hooks list` marks it.
- **Settling a collision:** a provider at a higher tier binds the hook, so a collision below it no longer fails. The project adds a provider of its own, or uninstalls one of the two. Where two of the project's own skills collide, it keeps the hook in the `answers:` of one.

## Unsatisfied needs

Every `needs:` entry is required by default (COR-013 point 4). The two validations that fail a same-tier collision also fail a need that no skill answers and no package provides. COR-013 point 4 has install and sync check it too, and today neither does.

- **Listed:** `pkit hooks list` shows such a hook as `(no provider)`.
- **Resolved:** `pkit hooks resolve` refuses it, and says that no provider declares it.

## Invoking a hook

An agent invokes a hook it needs by running the hook's provider, as the provider's value says ("Provider value syntax" above). `pkit hooks resolve` names that provider and its value. No command runs a hook for an agent.

## Commands

Four commands query hooks. `list`, `resolve` and `who-provides` read the precedence above.

### `pkit hooks list`

Lists every hook that is declared or needed, with the provider it binds to, or `(no provider)`. A same-tier collision is listed with both its providers, and binds to neither.

### `pkit hooks resolve <hook>`

Names the provider the hook binds to, the first by precedence, and its implementation. It exits 1 where no provider declares the hook, and where two collide at the tier it binds by, naming both.

### `pkit hooks who-provides <hook>`

Lists every provider of the hook, skills and packages alike, in precedence order.

### `pkit hooks who-needs <hook>`

Lists each agent and skill whose `needs:` names the hook.
