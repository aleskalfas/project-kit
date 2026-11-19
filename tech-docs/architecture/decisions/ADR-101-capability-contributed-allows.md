---
id: ADR-101
title: A capability may allow a privilege it defines to an agent it ships, reported as a widening
status: proposed
date: 2026-11-19
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** [ADR-016](ADR-016-capability-contributed-intent-grants.md) lets an installed capability ship grants that the permission model composes for it, and [ADR-021](ADR-021-capability-contributed-privilege-definitions.md) lets it define privileges of its own. Both records treat a capability's grant as a deny, which only narrows an agent's reach and so applies on install. The model's loader never checked that stance: it composes a capability's grant of any effect, to any subject. This record lets a capability's grant also allow a privilege, on these terms:

- **Only named tools of its own, only to its own agent.** The privilege is one the capability defines itself, and recognises named harness tools alone, which no other privilege recognises. The agent is one the capability ships, and the allow carries no scope. The model's loader refuses any other allow of a capability's: that grant composes nothing and is named as rejected, and the fragment's other grants still compose.
- **Composed on install, binding only through a bound.** The allow is composed into the model on install, as a deny is. It widens the agent's reach, so it binds only through a bound: a model a person realized, or, in a working run, the model the runner reads from the default branch. Any deny still wins over it.
- **Reported as a widening.** The permissions overview reports it as a widening the capability contributes, so no agent's reach changes silently.

So a capability whose agent needs a tool that a strict posture would deny carries the grant with it, and no project copies it by hand. This record overturns ADR-016 in part, where a capability's grants apply on install, and ADR-021 in part, where a capability shapes its agents' reach through its deny alone. It completes in place the passages of ADR-016 and ADR-021 whose words stay true, such as those that speak of a capability's deny alone.

**Why an ADR.** What a capability's grant may carry, and how the model's loader composes, refuses and reports it, is a boundary of the backbone's permission model that binds every capability, an architecture record's question ([COR-025](../../../.pkit/decisions/core/COR-025-adr-decision-space.md), "Distinct from PRJ"). A capability that allows a privilege reads the rule here, not in the record of the capability that first did, and the permissions README, which every project receives, carries it once built (Implications).

## Context

**Before this record.**

- **A capability's grants.** An installed capability may ship a grants fragment, which the model's loader composes, found through the installed components, before the active profile and the project's own grants (ADR-016 points 1 and 2). The operator's profile choice and manual grants win on the allow side, and a capability's deny survives by deny-wins (ADR-016's Decision). ADR-016 and ADR-021 treat what a capability grants as a deny, which narrows an agent's reach, so it applies on install under [ADR-008](ADR-008-confinement-allowances.md)'s narrowing class, and the overview reports which capability contributed it (ADR-016 point 7). The loader never checked that stance: it composes a capability's grant of any effect, to any subject.
- **A capability's privileges.** A capability may define privileges of its own, each scoped to the capability, adding to the catalog and overwriting nothing. ADR-021 gives its reach as over its own agents through its own deny grant, and the loader refuses a privilege fragment past its bounds (ADR-021 points 2 to 4).
- **How a privilege recognises a call.** By a shell command's words, by a named harness tool, whatever its input, or by a file tool whose target lies in named folders (the permissions README, "Privileges and how they are recognized"). A named tool matches by its name alone, so whether two privileges recognise one tool is a question of set membership.
- **The posture.** The posture decides a call no grant covers: a strict posture denies it, and a lenient one leaves it to the harness's own rules, which may ask a person (the permissions README, "Grants and verdicts").
- **A widening waits for a bound.** The permission hook allows no more than its bound: a model a person realized, or, in a working run, the model the runner reads from the default branch. A change in the checkout that widens the model binds only once a person realizes it, and realizing shows each widening before it writes ([ADR-095](ADR-095-hook-out-of-reach.md) point 3).

**The forcing case.** The project-management capability has its agent hold a harness's tools for messaging other sessions and listing them, under every posture ([project-management:DEC-081-delegation-between-seats] point 2). A capability's deny cannot grant them.

**Terms.**

- **A capability's allow** is any grant in a capability's grants fragment that is not a deny: one whose effect is allow, or that names no effect, since a grant's effect is allow by default.
- **An agent the capability ships** is the agent of a name whose definition, as the name-collision precedence picks it, is the capability's own (the agents README, "Name-collision precedence").
- **A named harness tool** is a recogniser that names one of the harness's tools, matched whatever its input.
- *Realizing*, *a widening* and *a bound* are ADR-095's, and *the posture* is the permission model's.

## Decision

**A capability's grant may allow a privilege, but only one the capability defines itself, whose every recogniser is a named harness tool that no other privilege recognises, only to an agent the capability ships, and with no scope. The allow is composed into the model on install, as a deny is, binds only through a bound, and is reported as a widening the capability contributes. The model's loader refuses any other allow of a capability's, which then composes nothing and is named as rejected.**

### 1. A capability allows only named tools of its own, and only to an agent it ships

- **What it may allow.** A capability's allow may name only a privilege that meets four conditions:
  1. the capability defines it itself (ADR-021);
  2. every recogniser it has is a named harness tool;
  3. it has no shell-command recogniser, no file tool scoped to folders and no pattern;
  4. no other privilege recognises any tool it names, as a named tool or as a file tool scoped to folders, whether the backbone's, another capability's or the project's.
- **To whom, and how far.** It allows that privilege only to an agent the capability ships, and carries no scope. An allow covers a call outside its scope with a deny, so a capability's scoped allow would deny there what the operator allows.
- **Checked exactly, at each load.** A named tool matches by set membership, so the loader checks the bound exactly. It checks it each time it loads the model, so where a privilege installed later, by the backbone or another capability, comes to recognise a tool the capability's privilege names, the loader refuses the allow from then on (point 4).
- **Its reach.** So a capability's allow reaches only those tools, for that agent. This record decides no bound on a capability's deny.

### 2. The allow is composed on install, and binds only through a bound

- **Composed as a deny is.** The allow is composed into the model on install, in the capability's fragment, as a deny is (ADR-016 points 1 and 2).
- **A widening.** The allow widens the agent's reach, so ADR-008's narrowing class, by which ADR-016 point 7 applies a deny on install, does not cover it. ADR-008 governs confinement, and here the person's gesture is ADR-095's realizing, which shows each widening. The allow binds only through a bound: a model a person realized, realizing having shown it as a widening, or, in a working run, the model the runner reads from the default branch (ADR-095 point 3). So a capability's denies apply on install, and its allows only through a bound.
- **What it decides.** Once it binds, the allow decides a call that no grant of the operator's covers, which the posture would otherwise deny or leave to ask a person. Any deny still wins over it by deny-wins, whether a guardrail's, a lock's, the capability's own or the operator's.
- **Withdrawn by a deny.** The operator withdraws a capability's allow by a deny of the privilege to that agent. Revoking removes only the project's own grants, and so none of a capability's.

### 3. The read surface reports it as a widening the capability contributes

The model's read surface, the permissions overview among it, reports a capability's allow as a widening, with the capability that contributed it, as it reports a capability's deny (ADR-016 point 7).

### 4. The loader refuses any other allow of a capability's

- **The refusal.** The model's loader refuses a capability's allow that names a privilege outside point 1's bound or a subject other than an agent the capability ships, and one that carries a scope. It judges a grant for each privilege it names, and refuses the grant where any of them falls outside the bound.
- **Only that grant.** A refused allow composes nothing, and the model's read surface names it as rejected, with its capability. The fragment's other grants, its denies among them, still compose.
- **Where another definition wins.** Where the name-collision precedence picks, for the agent's name, the project's own definition, another capability's or core's, the agent is not one the capability ships, and the loader refuses the allow.
- **Within the loader's limits.** The check runs where the loader runs: on the standard library alone, from the copy (ADR-016 point 3). What it reads must be among the inputs the model's bound holds (ADR-095 point 3). This record decides the test, and the build decides how to read what it needs within those limits.
- **Where the check does not run.** An installed release older than the build that brings this check composes a capability's allow unchecked. Where that release holds ADR-095's bound, only realizing's report of the widening shows such an allow, and where it does not, the allow binds as the model loads, as any capability's grant does before this record.

### What this overturns in ADR-016 and ADR-021, and what stands

Overturned, each a passage whose words this record makes untrue for a capability's allow, and the line each record gains points here (Implications):

- ADR-016's Summary, "Install the capability → its grants apply", since a capability's allow binds only through a bound (point 2);
- in ADR-021's Summary bullet on a guardrail, the clause "through its own deny grant", where a capability "shapes only its own agents' reach, through its own deny grant (ADR-016's channel, unchanged)", since it shapes that reach through its allow too (point 1);
- ADR-021 point 3's "A capability's reach is over its own agents via its own deny grant", for "via its own deny grant", for the same reach (point 1);
- ADR-021's Rationale, "so the worst a capability can do is fence its own agents", since it can also allow them named tools of its own, reported as a widening (points 1 and 3).

Refined in place: the passages the Implications name, their words left true.

Standing: the rest of each record. Among it are ADR-016's composition, its discovery through the installed components and what it says of a capability's deny. So are ADR-021's merge of a capability's privileges, its bounds on them, the bans on a guardrail and on a lock (ADR-095 point 3) among them, and its attribution of them. ADR-021 point 4 stands too: the overlap it permits, and its honest bound on recognised commands, concern a capability's deny alone, since no privilege a capability allows shares a recogniser or recognises a command (point 1).

## Rationale

**Why a capability may allow at all.** An agent's reach is its capability's policy, and travels with the capability, as a deny of its own does (ADR-016). Left to each project, a strict posture would deny the call with no word, and every project that installs the capability would copy the same grant by hand, the hand-copy ADR-016 removed for a deny.

**Why only named tools of its own, and only to its own agent.** A named tool matches by its name, so a bound on named tools that no other privilege recognises is one the loader checks exactly, at every load. The allow then reaches only those tools, for that agent. So the worst a capability can do is fence its own agents, or allow them named tools of its own, reported as a widening. A refused allow composes nothing, so the agent keeps the reach it had without it, and the capability's denies still narrow it.

**Why reported as a widening, and binding only through a bound.** Reported with the capability that contributed it, the allow changes no agent's reach silently, as the report of a deny keeps a narrowing in view (ADR-016 point 7). It binds only through a bound (ADR-095 point 3), so a person who realizes the model sees the allow before it binds.

### Alternatives considered

- **Leave every allow to the project, and have a capability ship only the privilege's definition.** Not taken, as "Why a capability may allow at all" says.
- **Any recogniser, stated honestly.** A capability's allow may name a privilege it defines whatever its recognisers, and realizing shows each recogniser. Not taken: shell and file reach stay the operator's; what the narrow bound refuses costs a project one grant at setup; and widening the bound later takes a record for a real case, while narrowing it later breaks the capabilities that rely on it.
- **Any privilege that is neither a guardrail nor locked, to the capability's own agent.** Not taken, for the same reasons: such a privilege may recognise shell commands, file tools and tools another privilege shares.
- **A per-project opt-in on top of realizing.** Not taken: realizing is already the person's gesture, shown for each widening (point 2).

## Implications

- **Edits to accepted records,** made in this change once a person accepts this record ([COR-066](../../../.pkit/decisions/core/COR-066-accepted-before-landing.md) point 5):
  - **Overturned in part.** ADR-016 and ADR-021 each gain a line at the top of the body, before the Summary, and their words stay as they stood under it. ADR-016 gains:

    > **Partially superseded by [ADR-101](ADR-101-capability-contributed-allows.md).** A capability's grant may also allow a privilege the capability defines itself, recognising named harness tools alone that no other privilege recognises, only to an agent the capability ships and with no scope, and the loader refuses any other allow of a capability's. Overturned, for such an allow: the Summary's "Install the capability → its grants apply", since the allow binds only through a bound, a model a person realized or, in a working run, the model the runner reads from the default branch, as ADR-101's "What this overturns in ADR-016 and ADR-021, and what stands" quotes. The rest stands, each passage ADR-101 completes carrying a pointer to it.

    ADR-021 gains:

    > **Partially superseded by [ADR-101](ADR-101-capability-contributed-allows.md).** A capability's grant may also allow a privilege the capability defines itself, recognising named harness tools alone that no other privilege recognises, only to an agent the capability ships, reported as a widening. Overturned, each for that allow: the Summary's clause "through its own deny grant", point 3's "via its own deny grant", and the Rationale's "the worst a capability can do is fence its own agents", each quoted in ADR-101's "What this overturns in ADR-016 and ADR-021, and what stands". Point 3's bans on a guardrail and on a lock stand, and so does the rest, the passage ADR-101 completes carrying a pointer to it.

  - **Refined in place,** each completed with a forward refinement pointer to this record, its words left true:
    - ADR-016's Decision headline, whose "the operator's profile choice and manual grants still win on the allow side" gains "and an operator's deny wins over a capability's allow" (point 2)
    - ADR-016's Summary property "Your settings win on what's *allowed*", which gains "and your deny wins over a capability's allow" (point 2)
    - ADR-016's Summary property "It's visible", whose "shows which capability contributed a deny" gains "or an allow, marked as a widening" (point 3)
    - ADR-016's Summary property "The privilege definition stays central", in its parenthetical alone: "(deny it to this agent)" gains "or allow it to an agent the capability ships, within ADR-101's bound" (point 1). The clause on where a privilege is defined is ADR-021's to complete, and this edit leaves it as it stands.
    - ADR-016 point 1, where the operator's "manual `grant`/`revoke` are peers unioned later", which gains a last sentence: a `revoke` withdraws what the operator granted, and a deny of the privilege to the agent withdraws what a capability allowed (point 2)
    - ADR-016 point 7, which gains a last sentence: "A capability's allow is a widening, which ADR-101 governs." (point 2)
    - ADR-016's Implications bullet on the narrowing-but-reported gloss, whose "that a capability contributed a deny" gains "or an allow, marked as a widening" (point 3)
    - ADR-021's Implications bullet on the narrowing footing, completed by a sentence: a capability's allow, within ADR-101's bound, is a widening, reported as one (points 2 and 3)
  - **An edit that changes no decision:** none.
- **What is built.** Today the model's loader composes a capability's grant of any effect, to any subject, unchecked. Point 4's refusal narrows that, and fails closed, so this record needs no migration. The build's changeset and the release's notes say that an installed capability's allow outside the bound stops composing.
- **The build, a backbone Task of its own,** filed once this record is accepted: the loader's check and refusal (points 1 and 4), and the read surface's report of an allow as a widening and of a refused allow as rejected (points 3 and 4). It brings the shipped account of a capability's grants into line, where it still says a capability only denies: the permissions README, the overview's listing of what capabilities contribute, the scaffolding command's guidance, and `revoke`'s help, which with the README says that a deny withdraws a capability's allow (point 2). The check is worth having whether or not any capability allows. [project-management:DEC-081-delegation-between-seats]'s build depends on it.
- **The order.** The loader's check, and the first capability's allow, ship no earlier than ADR-095's bound. A capability that allows declares that it requires the backbone release that brings both (PRJ-002), as DEC-081's build does for project-management.
- **Acceptance.** This record overturns the accepted ADR-016 and ADR-021 in part, so accepting it needs the person's sign-off. It rests on no proposed record, and [project-management:DEC-081-delegation-between-seats] rests on it. Refusing DEC-081 leaves this record whole, since a capability's allow composes unchecked today.
- **Changesets.** This record moves nothing, so it needs none of its own. The build declares its components' changes (PRJ-002).
