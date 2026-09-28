---
id: ADR-057
title: The engines that keep artefacts true ship in the binary, one home per computation; commands they run for a capability declare the query contract
status: proposed
date: 2026-09-28
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** the machinery that keeps analysis and documentation true — artefact discovery and the friction checks, the wiring resolver of connection points, and the rule-set validator — ships inside the `pkit` tool, and each computation it performs has exactly one home that every reader calls. Commands a capability supplies for these engines to *query* — a resolver for a new anchor kind, a filler for a data point — must declare that they honour the query contract the records set: bounded in time, deterministic, read-only, and needing no network. The engine enforces what it can — the time bound and the shape of the answer, failing closed — and states plainly what it cannot: no layer of this distribution stops a command from reaching the network, on any platform.

## Context

The core records of this milestone ask the backbone for engines: artefact discovery and friction ([COR-050](../../../.pkit/decisions/core/COR-050-anchors-and-friction.md)), the resolver of connection points ([COR-053](../../../.pkit/decisions/core/COR-053-connection-points.md), whose Implications ask that its placement be recorded "in the project's architecture decisions, as for the other resolvers"), and rule-set validation ([COR-051](../../../.pkit/decisions/core/COR-051-rule-sets.md)). The validators of the backbone file schemas are already placed ([ADR-056](ADR-056-backbone-file-schemas-home.md)). The process engine set the test for such engines: code ships in the binary unless something below the tool layer must import it ([ADR-020](ADR-020-process-engine-code-home.md)); the permission core is the counter-example that propagates because the hook imports it ([ADR-003](ADR-003-permission-core-code-home.md)).

The records also let capabilities supply commands the engines run: a resolver for an anchor kind (COR-050 point 2) and a command filler for a data point ([COR-052](../../../.pkit/decisions/core/COR-052-slots.md) point 6) are *queries*, to run "with a bounded time, no network access, and deterministic output", failing closed; a subscriber to an event (COR-053 point 9) is an *action* that writes. A runner of capability commands already exists: the process engine's predicate runner, which bounds and parses the predicates a capability registers — and those may reach the network, as the work tracker's gates reach its tracker.

What this distribution can do about network access is limited, and the limit shapes the decision. Confinement is delegated to the harness's operating-system sandbox, which pkit manages but does not implement ([ADR-004](ADR-004-autonomy-intent-confinement.md)). Where that sandbox is on, it holds a whole session to one list of allowed hosts — every host any confinement toolkit opened — and is explicitly not a security boundary ([ADR-015](ADR-015-command-declared-network-egress.md)). On macOS the `pkit` and `uv` process tree runs outside the box, because `uv` cannot run inside it ([ADR-014](ADR-014-macos-sandbox-platform-stance.md), [ADR-027](ADR-027-required-sandbox-exclusion-auto-apply.md)). In a pipeline or a plain terminal there is no sandbox at all.

## Decision

1. **The engines ship in the binary.** Artefact discovery and its validation findings, the change check, the whole-repository check and the debt listing, the wiring resolver, and the rule-set validator are part of the `pkit` tool, alongside the validators ADR-056 places. Nothing below the tool layer imports them. Their consumers reach them as commands: people, agents and the check gate directly; capability scripts and migrations through the engines' machine-readable reading commands, never by importing the engine or re-walking the places themselves.

2. **One home per computation.** Where artefacts are and what they declare, how the wiring resolves, and how a version relation compares are each computed in exactly one module, and every reader calls it — the plans COR-053 promises are exact only because they run the live resolver. The code that predates this record still computes some of these twice: artefact discovery reads two file sources (the working tree for validation, git's listing for the change check, with their differences documented); the configuration pass reads friction patterns and checks a contributor selection on its own; container validation does not yet ask the resolver which roles are active; and version ranges are compared in several older places besides the resolver. That is recorded debt, consolidated by its own Task; new code adds none.

3. **Query commands declare the query contract; the engine enforces what it can.** A command a capability registers as an anchor-kind resolver or a data-point filler carries, on its own entry in the capability's command registry, one constant declaration that it honours the query contract — bounded, deterministic, read-only, needing no network. The declaration grants nothing and writes nothing to the sandbox; egress stays on the confinement-toolkit path (ADR-015). Validation of package metadata reports a registered query command without it, when the author can still fix it; the engine refuses to run one, as the backstop. When it runs one:
   - **time** is bounded by a fixed backbone constant, the same thirty seconds the predicate runner uses, and exceeding it kills the whole process group — the house script shape starts its interpreter as a grandchild;
   - **the answer** is parsed and validated against the shape the backbone defines for what was asked; an abnormal exit, a timeout, or an unparsable or invalid answer is *no answer* — which is never an empty answer — and each caller applies its own record's rule to it: an anchor stays unresolved, a data point follows its inert policy;
   - **the environment** is marked offline, so a well-behaved command can tell.

   The literal of the declaration, the marker, the answer shapes and how a script's dependencies are made available before an offline run belong to the reference and are specified with the first query command that runs; until then the refusal is a tested function and no capability command is run.

4. **What is not enforced, stated.** No layer of this distribution holds a single command to "no network". A sandbox, where one applies, admits every host the session allowed; on macOS the commands the engine starts run outside it; in a pipeline or a terminal nothing bounds them. Determinism and read-only are likewise declared and judged in review. The engine is an honest interlock — checked at validation, trusted at run time — not a boundary.

5. **Predicates stay on their own runner.** The process engine's predicates are not queries in this sense: they may reach the network, and the gate that reads them decides what their output means. They keep their runner and its policy. The two runners should share one command lookup and one start, bound, capture and parse primitive — one mechanism with two policies — and that extraction is its own Task, since walking the command registry now happens in three places.

6. **What this record does not place.** Of the placements COR-053 asks for, this record places the resolver. Data-point resolution (combining fillers, precedence, the inert policy), the refresh of generated dependency lists, the event runner with its loop guard and chain report, and the source of each edge in the wiring graph are placed by the Tasks that build them, in their own records. Subscribers are actions, not queries, and nothing here binds them.

## Rationale

**Why the binary.** ADR-020's test is whether a consumer below the tool layer must import the code. None does: every reader of friction, wiring or rules is a `pkit` command, capability scripts already call `pkit` as a subprocess, and the check gate invokes the CLI. Shipping the engines in the tree would add a copy to version and a third version axis for nothing.

**Why one home each.** The value of a plan, a graph or a status line is that it agrees with what validation and the checks conclude. Two computations drift, and the one people trust — the plan before an install — would be the one that lies. Naming the existing duplicates keeps the rule true the day it is accepted.

**Why a declaration of the whole contract, on the command.** The records ask four things of a query command; stating only one of them would imply the others need no thought. A declaration on the command's own entry is literally per command, and a command used by two registrations is declared once. Reporting it at validation puts the requirement in front of the author; refusing at run time keeps a missed report from becoming a silent run.

**Why not decide from egress.** Refusing the commands of a capability that "holds egress" was considered and cannot work: confinement toolkits are per tool, not per capability, and egress is session-wide, so a grant is neither necessary nor sufficient for a given command to reach the network.

**Why the rest waits.** No capability registers a query command yet. The answer shapes, the dependency question and the event runner are best decided against the first real consumer, and the Tasks that bring those consumers are filed.

**Why an ADR.** The core records fix the limits and leave where the engines live and how the limits are realised to the project; this is project-kit's realisation, at the altitude of ADR-020 and ADR-056 ([COR-025](../../../.pkit/decisions/core/COR-025-adr-decision-space.md)).

### Alternatives considered

- **Propagate the engines into the tree.** Rejected: no consumer below the tool layer; a second version axis for nothing (ADR-020).
- **Refuse commands by their capability's egress.** Rejected: toolkits are per tool and egress is session-wide (ADR-015); a grant says nothing about a command.
- **Start query commands under an operating-system sandbox from the engine.** Rejected: a second, per-command confinement mechanism beside the one ADR-004 delegates to, which on macOS cannot run `uv` at all (ADR-014).
- **Declare only "no network".** Rejected: the records ask four things of a query command, and declaring one implies the rest need no thought.
- **A configurable time bound.** Rejected for this record: a project setting would be a backbone configuration key, which only a core record may own (COR-048 point 2).
- **Put subscribers under the same contract.** Rejected: subscribers write; "never a partial answer" cannot hold for effects, and their obligations — the effect report, the opt-out, the loop guard — are COR-053 point 9's, decided with the first subscriber.

## Implications

- The friction checks, the wiring resolver and the rule-set validator are modules of the binary; each computation has one home.
- A Task consolidates the duplicates named in point 2, and another extracts the command primitive both runners share (point 5).
- The package-metadata reference gains the declaration's literal, the offline marker and the answer shapes when the first query command is specified; the package schema then requires the declaration on registered query commands.
- The CLI reference's resolver-limits paragraph states the gap as point 4 does, including macOS, and cites this record.
- **Raised for a core decision.** COR-050, COR-052 and COR-053 require query commands to run with no network access. No distribution can hold a single command to that portably; reading the requirement as a declaration that is required, reported and trusted is a universal reading, not project-kit's alone, and may deserve a refinement of those records.
- **Recorded trigger to revisit.** If a consumer below the tool layer ever needs one of these engines in-process, ADR-020's test is reopened for that engine.
