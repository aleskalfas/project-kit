---
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/refs.py
        - src/project_kit/cli.py
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
- **Two providers at one tier** fail `refs validate` and the whole validation, which name both ("Commands" below). Disambiguate them: uninstall one, or add a provider of the project's. Until then, `hooks resolve` names the first it reads.
- **The `hooks` commands** read the same order.

## Unsatisfied needs

Every `needs:` entry is required. `refs validate` and the whole validation fail a need that no skill answers and no package provides. Neither install nor sync checks it.

- **Listed:** `hooks list` shows such a hook as `(no provider)`.
- **Resolved:** `hooks resolve` refuses it, and says that no provider declares it.

## Commands

The commands that check and query hooks, as the CLI reference lists them:

```
pkit refs validate               # fails on a same-tier collision or an unsatisfied need
pkit hooks list                  # each hook, with the provider it binds to
pkit hooks resolve <hook>        # one hook's provider, the first by precedence
pkit hooks who-provides <hook>   # every provider of a hook, in precedence order
pkit hooks who-needs <hook>      # each agent and skill that needs the hook
```
