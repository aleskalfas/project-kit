# software-analysis capability

Analysis discipline: the artifacts a project uses to decide **what** is needed before building it. Install it when your designs routinely span several parts of the system — a command, a guard in another command, a CI check, an agent's behaviour — and you want a durable way to check that a design is complete before its work is filed, and to re-check it when that work lands.

Its first discipline is **use-case validation** ([software-analysis:DEC-001-use-case-validation]): when getting from a situation to an outcome crosses more than one part of the system, walk numbered use cases through the design *before* filing its work, keep them, cite them from the work's success criteria, and re-walk them when the work closes. Walks find what reviews miss — the command that doesn't exist, the state two rules disagree about — because reviews judge the parts and a walk runs them.

Named as future scope, not yet shipped: **requirements**, **user stories** (who uses the system and what they're trying to achieve — a use case's actor will cite one), and **traceability** between them.

## What this capability ships

- `decisions/DEC-001-use-case-validation.md` — the use-case artifact and the walk-before-filing rule.
- The use-case template and location convention (below).
- *Coming with the next increments:* a command that stamps a numbered use-case set, a validate command for the check gate, a paired authoring skill, and use-case citation resolution.

## Adopter setup

Install from kit source:

```
pkit capabilities install software-analysis
```

No configuration is required to start. Use-case sets are your project's own design documents: they live **outside** this capability, default `docs/use-cases/`, so neither sync nor uninstalling the capability touches them. Choosing a different location becomes a configuration setting when the stamp command ships.

## Use-case sets at a glance

- Files: `docs/use-cases/UC-NNN-<slug>.md`, numbered `UC-001`, `UC-002`, … within the project.
- Inside a set, use cases are numbered `1, 2, …` — **append-only**: add, revise, or mark withdrawn; never renumber.
- Cite a set as `UC-003`, one use case in it as `UC-003/5`. Only your project's content cites use cases; capability-shipped content never does.
- **When you need one, and the rule:** see [software-analysis:DEC-001-use-case-validation] — the *seams crossed* test (point 2) and walk-before-filing / re-walk-on-close (point 3).

## The use-case set template

```markdown
---
id: UC-NNN
title: <the design this set validates>
---

# <title>

<One paragraph: which design this validates, and where that design is recorded.>

## Use cases

### 1. <short name>

- **Actor:** <a named role>
- **Situation:** <the state the actor is in>
- **Does:** <what the actor does, step by step>
- **Observable:** <what must be true / visible afterwards>
- **Exercises:** <the commands, records, checks and roles the design uses to get there>
- **Last walked against:** <design state, commit, or release — and date>

### 3. ~~<short name>~~ — withdrawn <date>: <why>

<!-- A withdrawn use case keeps its number and its text struck through; it is never deleted or reused. -->

### 2. …

## Gap log

Append at every walk; never delete entries. Write "No gaps found" if a walk finds none.

- <date> — use case <n>: <what the walk found missing or contradictory> → <what changed in response>
```

## Walking a set — the steps

1. Stamp a set, fill one use case per situation the design must serve, and walk each one against the design. Write every stall into the gap log with what you changed.
2. Merge the set before filing the design's work. Each work item names the use cases it satisfies.
3. When an item closes, re-walk its use cases against the real system, update *Last walked against*, and append to the gap log.

## Citing this capability's decisions

Cite decisions by filename stem: `[software-analysis:DEC-001-use-case-validation]`. Other capabilities and adopter content use the same form.

## Dependencies

None. A component that files work (for example the project-management capability) may adopt the walk-before-filing rule when this capability is installed; that adoption is recorded on its side.
