---
id: DEC-068
title: project-manager keeps the session's tools, less those it is withheld
status: proposed
date: 2026-11-09
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** `project-manager` often runs as a whole session's agent, through the default-agent switch this capability ships. A grant of tools then gives the session's agent only the tools it names. So a grant strips every such session of the web tools, tool search, and every tool of each MCP server connected to it.

So the agent is granted no list. It has every tool the session gives it, less a short list it is withheld, and the harness removes a withheld tool from its view. A built-in tool is withheld where the agent's own denies cannot follow it, or where it starts work or opens a channel outside the methodology's rules. Finer limits, such as a command the agent may not run, stay in pkit's permission model. The agent gains a wider reach, and a tool a later harness release adds reaches it until the list names it. This record accepts both costs.

## Context

This capability ships a switch that makes `project-manager` the default agent of every session in a project ([project-management:DEC-030-capability-contributed-adapter-overlays]), and that is the pattern meant for adopters ([project-management:DEC-029-project-manager-agent-shape], "Invocation pattern"). An agent's definition names the tools it is granted, those it is withheld, or neither ([COR-013](../../../decisions/core/COR-013-agent-architecture.md) point 7). Measured with Claude Code 2.1.319 on macOS, from the init message a session reports at its start:

- Under a grant of eight tools, the grant the agent held before this record, a session's agent has 6, where under no grant it has 34. On macOS this version offers no `Glob` or `Grep`. The tools of a connected MCP server are all gone, with the web tools and tool search.
- An agent withheld some tools keeps all the others, the MCP tools included, and the withheld tools are absent. This holds for an agent named by the `agent` setting, as the switch names it.
- A grant may name one MCP server, which admits all of that server's tools, but a pattern for every server admits none. So a grant admits only the servers its author knew of.
- The built-in tools Claude Code offers vary between runs of one version, so a grant also goes stale.

pkit limits this agent by command, in the permission model: its grants deny the raw `gh` writes and three raw reads that this capability's commands replace. Those denies are a speed bump, not a boundary. The permission hook reads a call as a command only when it comes through the shell tool ([project-kit#2948](https://github.com/aleskalfas/project-kit/issues/2948)).

## Decision

**`project-manager` is granted no list of tools. It has every tool the session gives an agent, less a list it is withheld. A built-in tool is withheld where the agent's own denies cannot follow it, or where it starts work or opens a channel outside the methodology's rules, each with its reason in the agent's definition. A limit on some uses of a tool stays in the permission model or the agent's body. The agent's wider reach, a new tool reaching it until it is withheld, and the tools it may see and not use, are accepted.**

### 1. The agent has the session's tools

Its definition names no grant, so as a session's agent it has the session's tools, every connected server's included. As a subagent it has those the session gives a subagent. Connecting a server gives the agent its tools with no change to this capability.

### 2. A built-in tool is withheld where the agent's rules cannot follow it

The agent's definition withholds each built-in tool of one of three kinds, with the tool's kind and reason beside it:

- **A tool that runs a command past the permission hook's reading.** The agent's own command denies would not bind on it. It stays withheld until the hook reads it.
- **A tool that starts work outside the session's checks,** such as a run on a remote service with nobody watching, or helpers started other than through the agent tool. The agent's dispatch discipline covers the agent tool only.
- **A tool that opens or lists a channel to other sessions.** Work reaches seats through one shared pool ([project-management:DEC-059-topology-of-seats] point 7), not through messages between sessions.

The harness removes a withheld tool from the agent's view, so the agent never tries one. The definition holds the list, and a tool joins or leaves it only by an edit there, with its reason.

The kinds apply to the harness's built-in tools only. An MCP tool comes unjudged, since no list here can know which servers a session connects. The hook sees its calls only as plain tool requests, so an MCP tool that runs a command or writes a file passes the agent's command denies and the hook's path checks. That gap is declared, not closed.

### 3. A limit on some uses stays in the permission model or the agent's body

Where only some uses of a tool are refused, the tool stays in the session. The permission model refuses the uses it can see, such as closing an issue through `gh` rather than through this capability's command. The agent's body states those it cannot:

- The tracker changes only through this capability's commands, never through a connector's or an MCP server's tools.
- A prompt the session scheduled for itself is no person's authorisation, and neither is a message another agent session sends it.

### 4. The costs are accepted

- **A wider reach.** The agent gains the web tools, every MCP tool the session holds, and the built-in tools that send content out or feed it messages from the network. Those run outside the operating system's sandbox, and the agent reads untrusted text from issues and pull requests. pkit never claims to confine outbound traffic: the adapter's enforcement declaration states network egress as a gap.
- **A new tool reaches the agent.** A withheld list gives every tool it does not name. A tool a later harness release adds, or one the harness offers in some runs only, reaches the agent until someone judges it and withholds it if it is of one of the three kinds. A probe of the adapter's names each built-in tool nobody has classified ([project-kit#2949](https://github.com/aleskalfas/project-kit/issues/2949)).
- **Some tools stay in view, though a call to them is refused or waits.** Under a strict posture, the permission model refuses a call no grant covers, an MCP tool's included. Under a lenient posture, a tool the settings do not allow asks a person, and with nobody there the ask is a refusal. A project can remove such a tool from its sessions through its own settings, as the adapter's documentation says.
- **No deploy where the harness cannot withhold.** An adapter refuses to deploy a definition whose withheld list its harness cannot enforce (COR-013 point 7), so on such a harness this agent does not deploy.

## Rationale

**The session's tools follow the session.** The switch strips every adopter's own servers and web tools from every session it applies to. A grant has to foresee the servers each person and project connect, since no pattern admits them all, and each server it leaves out disappears without a word. Withholding instead serves every session the same, with no setup.

**A withheld tool leaves the agent's view.** A per-agent deny in pkit's permission model would leave a tool in the agent's view, and the agent would try it and be refused. Withholding it in the definition removes it before the agent sees it.

**Withheld where the agent's rules cannot follow, not where nobody has judged.** A built-in tool whose commands the hook does not read is one the agent's own denies cannot follow. A tool that starts work outside the session's checks, or reaches other sessions, would act outside the rules that route dispatch and work. Any other tool keeps its uses, and the limits on them stay where the methodology already puts them.

**The reach is worth its cost.** The tools this record admits are the ones the agent's work uses: the documentation it reads by its address, and the servers a person or a project connects for it. pkit's denies were never a boundary on what the agent reaches.

### Alternatives considered

- **Withhold nothing.** It needs no new release of the backbone. Rejected: the agent would see tools its own denies cannot follow, and tools that start work or reach sessions outside the methodology's rules.
- **Grant the built-in tools the agent may use, and name each server to admit.** It fails closed: a tool a new release adds stays out until someone admits it. But each server must be named, from the project's overlay or from a profile per kind of setup, since no pattern admits every server. A server a person adds is lost until someone names it. A profile that writes other servers in one setup than in another changes the committed agent each time the project syncs in the other.
- **Turn the default agent off where its tools are needed.** The project then loses the agent it chose.

## Implications

- **The agent's definition** names no grant, and withholds each built-in tool of the three kinds, with its kind and reason. Its body gains the two limits of point 3. The deployed copy is written again at the next sync, so no migration is needed. It lands after the backbone admits the withheld list.
- **project-management DEC-029's dispatch paragraph,** refined in place in the change that proposes this record, says the messaging tool is one the agent's definition withholds, where it said the agent's grant does not include it.
- **The fixers' check** counts the workflow tool and the remote schedule tool among the tools that start agents, beside the agent tool, which a fixer's run is denied ([project-management:DEC-056-drift-fixers] point 5). It reads a fixer's tools from its definition.
- **Changesets:** project-management declares a `minor` change, since the deployed agent's tools change for every adopter with the default agent on. Its definition names a withheld list, which needs the backbone release that admits one. The changeset says `requires_backbone: release` where both ship in one release, and that release's version otherwise.
