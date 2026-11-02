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
- **Anything else** runs as a shell command, through bash.

```yaml
# a capability's package.yaml
provides:
  tracker.create-issue: /tracker-create-issue   # a skill
  tracker.move-issue:   scripts/move-issue.py   # a shell script
```

A skill's `answers:` entry is provided by the skill itself.

## Hook signature

A hook takes positional string arguments, and writes text to standard output. Exit code 0 is success, and standard error carries errors and warnings. Each hook's own contract, its arguments and the form of its output, is in its provider's body or README.

## Naming

A hook's name says whether any provider of its topic may answer it, or one provider alone:

- **`<topic>.<operation>`,** two segments, names a contract hook, which several providers of one topic are expected to implement. The topic is usually a capability's name. An agent that needs only such hooks works with any provider of the topic.
- **`<topic>.<provider>.<operation>`,** three segments, names an extension that one provider implements. An agent that needs one is tied to that provider, and the name says so.
- **The form:** lowercase kebab-case segments joined by dots, matching `^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*){1,2}$`.
- **The project's own hooks** use the topic `project`, which is kept for them.

## Provider precedence

One provider binds each hook, taken by tier in this order:

```
project > capability > adapter > core
```

- **The tiers:** a skill in `.pkit/skills/project/` is of the `project` tier. A capability's `provides:` is of the `capability` tier, and an adapter's of the `adapter` tier. Every other skill is of the `core` tier, a skill a capability ships among them.
- **Two providers at one tier:** COR-013 point 4 decides that the collision is refused, never settled by picking one. The project disambiguates them by uninstalling one, or by adding a provider of its own. What the code does today:
  - `pkit validate` and `pkit refs validate` fail the collision, naming both providers.
  - Uninstalling one clears the finding. A provider of the project's binds the hook, but the finding stays.
  - `pkit hooks resolve` names the first provider it reads, rather than refuse.

## Unsatisfied needs

Every `needs:` entry is required (COR-013 point 4). The two validations that fail a same-tier collision also fail a need that no skill answers and no package provides. COR-013 point 4 has install and sync check it too, and today neither does.

- **Listed:** `pkit hooks list` shows such a hook as `(no provider)`.
- **Resolved:** `pkit hooks resolve` refuses it, and says that no provider declares it.

## Invoking a hook

An agent invokes a hook it needs by running the hook's provider, as the provider's value says ("Provider value syntax" above). `pkit hooks resolve` names that provider and its value. No command runs a hook for an agent.

## Commands

The commands that query hooks. `list`, `resolve` and `who-provides` read the precedence above.

### `pkit hooks list`

Lists every hook that is declared or needed, with the provider it binds to, or `(no provider)`.

### `pkit hooks resolve <hook>`

Names the provider the hook binds to, the first by precedence, and its implementation. It exits 1 where no provider declares the hook.

### `pkit hooks who-provides <hook>`

Lists every provider of the hook, skills and packages alike, in precedence order.

### `pkit hooks who-needs <hook>`

Lists each agent and skill whose `needs:` names the hook.
