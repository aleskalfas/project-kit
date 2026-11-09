---
id: ADR-085
title: The Claude Code adapter writes an agent's withheld tools in Claude Code's form
status: accepted
date: 2026-11-09
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** an agent's definition names the tools it is granted (`tools`), the tools it is withheld (`withheld`), or neither ([COR-013](../../../.pkit/decisions/core/COR-013-agent-architecture.md) point 7). The Claude Code adapter writes a grant as Claude Code's `tools`, and a withheld list as Claude Code's `disallowedTools`. With neither it writes no key. Claude Code removes a withheld tool from the agent's view.

The deploy, the agent runner and the reference validator admit the withheld list and refuse a definition that names both forms. A check of a definition reads its tool access, never the deployed copy's keys. The Claude Code behaviour this rests on becomes two declared harness requirements.

## Context

The definition's tool names are Claude Code's, and the adapter writes the tool access in Claude Code's form (COR-013 points 1 and 7). Until this record a definition could only grant, and a grant strips a session the agent runs to its list, every connected MCP server's tools included ([project-management:DEC-068-session-agent-tools]). Gating a whole tool is the harness's own per-agent control ([ADR-004](ADR-004-autonomy-intent-confinement.md) points 1 and 5).

Measured with Claude Code 2.1.319 on macOS, from the init message a session reports at its start, for an agent that names only `disallowedTools`:

- It keeps every other tool, a connected MCP server's included, and the withheld tools are absent.
- This holds for an agent given on the command line, as the agent runner gives one ([ADR-066](ADR-066-unattended-agent-runner.md)), for one named by the `agent` setting, as a project's default agent is, and with agent teams on, which otherwise adds its messaging tools.

A helper withheld a tool has not been measured: a helper's tools are visible only inside a session.

Some checks read an agent's tools: the reference validator's check that an agent declaring a storyboard can read it, and the fixers' check that a fixer can neither change files nor start agents ([project-management:DEC-056-drift-fixers] point 5). The fixers' check reads the deployed copy.

## Decision

**The adapter writes an agent's withheld list as Claude Code's `disallowedTools`, beside its grant as `tools`, and writes no key for an agent that names neither. The deploy, the runner and the validator admit the withheld list and refuse a definition naming both. Checks read a definition's tool access, and a check that an agent lacks a tool holds only on a grant. The Claude Code behaviour this rests on is declared as two harness requirements.**

### 1. The adapter writes the definition's tool access in Claude Code's keys

At deploy, a definition's grant is written as `tools`, and its withheld list as `disallowedTools`. A definition that names neither gets neither key. The agent runner writes the same keys into the definition it gives a run. The deploy, the runner's set of definition fields and the reference validator admit `withheld`. Each refuses a definition that names `tools` and `withheld` together: the deploy skips the agent and says why.

### 2. Checks read the definition's tool access

A check of an agent's tools reads the tool access in the agent's own definition, never the keys of its deployed copy, which are the harness's.

- **A check that an agent holds a tool,** such as `Read` for an agent that declares a storyboard, holds where the tool is granted, or where the agent names no grant and does not withhold it.
- **A check that an agent lacks a tool,** such as a fixer's, holds only where the agent's grant leaves the tool out. A withheld list never satisfies one, since it gives every tool it does not name.

No check of a definition reads the harness's own set of tools.

### 3. The Claude Code behaviour this rests on is declared

Core's harness requirements gain two, in behavioural words ([COR-047](../../../.pkit/decisions/core/COR-047-harness-requirement-declaration.md)):

- **A session's agent withheld named tools** has none of them, and keeps every other tool its session holds, a connected server's included. It is observed from outside a session, in the report a session gives at its start.
- **A helper withheld named tools** has none of them. It is observed only inside a session.

The Claude Code adapter answers each in its support declaration, from what was measured.

## Rationale

**The definition keeps the methodology's field.** Claude Code's `disallowedTools` in a definition would put one harness's key there, and the runner admits only the methodology's own fields (ADR-066 point 3). The adapter translates, as it already does for a grant.

**One form at a time.** A grant and a withheld list together say the same thing twice, and can disagree.

**A check that an agent lacks a tool needs a grant.** A withheld list gives every tool it does not name, a tool a later release adds among them, so it cannot show that an agent lacks anything else.

**Two requirements, because they are observed apart.** One is visible in a session's start report. The other only inside a session. A withheld tool that a harness still offered would bring back what the definition took away, with no sign, so each is a reported answer, not an assumption.

### Alternatives considered

- **Pass Claude Code's key through the definition.** Rejected: it puts a harness's key in the definition, and the runner would refuse it.
- **Derive a withheld list at deploy,** from a table of Claude Code's tools by kind and the permission model's denies for each agent. Deferred: it needs that table and its probe ([project-kit#2949](https://github.com/aleskalfas/project-kit/issues/2949)). A definition's withheld list is written by hand until then.

## Implications

- **COR-013,** refined in place in the change that proposes this record, gains point 7, an agent's tool access. Point 7 decides:
  - the three forms, and never both;
  - what each gives an agent run as a session's agent;
  - that a withheld list fails open, so an adapter refuses one it cannot enforce or translate.
  
  Point 1 makes a definition's tool names an exception to its harness neutrality. Each is a decision of its own, which the person who authorises the change accepts.
- **ADR-066 point 3** says the runner passes the tool access, granted or withheld, where it said the tool list. A confined run still passes its own fixed tools, so a withheld list only narrows it, and the start report's check holds.
- **ADR-004 point 1,** which names Claude Code's keys as the front matter, gains a pointer to this record once it is accepted.
- **The agents README** documents `withheld` beside `tools`, and the adapter README lists it among the fields the runner passes. The adapter README also says that a tool's name alone, as a deny rule in a project's own settings, removes it from the session for every agent.
- **The order of landing:** the deploy translates `withheld`, and the validator and the runner admit it and read a missing grant as in point 2, before any definition names a withheld list. An earlier deploy would copy `withheld` through unread, so the agent would have every tool.
- **Changesets:** the backbone and the `claude-code` adapter each declare a `minor` change. A capability whose definition names a withheld list needs the backbone release that brings this. Adapters move with the backbone, so its `requires_backbone` covers the adapter too.
- **The hand-kept tool lists,** the fixers' check of tools that start agents among them, remain until the table of project-kit#2949 replaces them.
